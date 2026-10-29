from datetime import date,timedelta
from io import BytesIO,StringIO
from unittest.mock import MagicMock,patch

import requests
from django.core.management import call_command
from django.test import TestCase,override_settings
from PIL import Image

from core.program_automation import format_daily_program_summary
from .kpi_chart import render_chart,send_mobile_kpi_chart,seven_day_metrics
from .models import MobileDailyKPI


def points(report_date=date(2026,10,30)):
    return [{'date':(report_date-timedelta(days=7-i)).isoformat(),'active':10+i,'answers':50+i*10,
             'accuracy':70+i*2,'sessions_completed':5+i} for i in range(7)]


class ChartDataTests(TestCase):
    def test_exact_seven_closed_days_use_snapshots_with_raw_fallback(self):
        report=date(2026,10,30);expected=points(report)
        old=MobileDailyKPI.objects.create(report_date=report-timedelta(days=7),payload={'current':{**expected[0],'date':(report-timedelta(days=8)).isoformat(),'active':9999}})
        MobileDailyKPI.objects.create(report_date=report,payload={'current':expected[-1]})
        lookup={p['date']:p for p in expected}
        with patch('mobile_api.kpi_chart.daily_metrics',side_effect=lambda day,ids:lookup[day.isoformat()]) as metric:
            result=seven_day_metrics(report)
        self.assertEqual(result,expected)
        self.assertEqual(metric.call_count,6)
        self.assertTrue(MobileDailyKPI.objects.filter(pk=old.pk).exists())
        self.assertEqual(result[-1]['date'],'2026-10-29')
        self.assertEqual(result[0]['date'],'2026-10-23')

    def test_png_is_memory_only_and_handles_no_accuracy_data(self):
        data=points()
        for row in data:row['accuracy']=None
        with render_chart(data) as image:
            self.assertTrue(image.read(8).startswith(b'\x89PNG'))
            image.seek(0)
            with Image.open(image) as png:self.assertEqual(png.size,(2048,1344))
        self.assertTrue(image.closed)

    def test_renderer_rejects_more_than_seven_days(self):
        with self.assertRaises(ValueError):render_chart(points()+[points()[-1]])

    def test_render_failure_closes_its_memory_buffer(self):
        buffer=BytesIO()
        with patch('mobile_api.kpi_chart.BytesIO',return_value=buffer), \
             patch('matplotlib.backends.backend_agg.FigureCanvasAgg.print_png',side_effect=RuntimeError('render failed')):
            with self.assertRaises(RuntimeError):render_chart(points())
        self.assertTrue(buffer.closed)


@override_settings(TELEGRAM_BOT_TOKEN='fake-test-token',TELEGRAM_CHAT_ID='owner-test-chat')
class ChartDeliveryTests(TestCase):
    def deliver(self,mode):
        image=BytesIO(b'PNG-test')
        response=MagicMock();response.__enter__.return_value=response
        response.json.return_value={'ok':mode!='api_error'}
        if mode=='http_error':response.raise_for_status.side_effect=requests.HTTPError('failed')
        def post(*args,**kwargs):
            self.assertFalse(image.closed)
            self.assertIs(kwargs['files']['photo'][1],image)
            self.assertEqual(kwargs['data']['chat_id'],'owner-test-chat')
            self.assertIn('23.10.2026 – 29.10.2026',kwargs['data']['caption'])
            self.assertIn('↑1',kwargs['data']['caption'])
            if mode=='network_error':raise requests.Timeout('failed')
            return response
        with patch('mobile_api.kpi_chart.seven_day_metrics',return_value=points()), \
             patch('mobile_api.kpi_chart.render_chart',return_value=image), \
             patch('mobile_api.kpi_chart.requests.post',side_effect=post) as send:
            if mode=='success':self.assertTrue(send_mobile_kpi_chart(date(2026,10,30)))
            else:
                with self.assertRaises((requests.RequestException,RuntimeError)):send_mobile_kpi_chart(date(2026,10,30))
            send.assert_called_once()
        self.assertTrue(image.closed)

    def test_success_closes_image(self):self.deliver('success')
    def test_http_failure_closes_image(self):self.deliver('http_error')
    def test_api_failure_closes_image(self):self.deliver('api_error')
    def test_network_failure_closes_image(self):self.deliver('network_error')

    @override_settings(TELEGRAM_BOT_TOKEN='')
    def test_no_credentials_does_not_generate_chart(self):
        with patch('mobile_api.kpi_chart.render_chart') as render:
            self.assertFalse(send_mobile_kpi_chart(date(2026,10,30)))
        render.assert_not_called()


class ChannelSummaryTests(TestCase):
    def test_hide_details_keeps_pdf_kpis_and_does_not_claim_no_releases(self):
        stats={'students':1,'courses':1,'emails':1,'failed':0,'pdf_checked':1,
               'pdf_missing':[{'course_id':742,'course':'Firewall','reason':'Ek yok.'}],
               'mobile_kpi_report':'Mobil KPI test özeti',
               'details':[{'email':'private@example.test','course':'Firewall','mail':'gönderildi'}]}
        full=format_daily_program_summary(stats,date(2026,10,30))
        short=format_daily_program_summary(stats,date(2026,10,30),include_student_details=False)
        self.assertIn('private@example.test',full);self.assertNotIn('private@example.test',short)
        self.assertIn('Bu derste PDF yok.',short);self.assertIn('Mobil KPI test özeti',short)
        self.assertNotIn('yeni içerik bulunmuyor',short)
        self.assertEqual(len(stats['details']),1)

    @override_settings(TELEGRAM_BOT_TOKEN='',TELEGRAM_CHAT_ID='')
    def test_chart_failure_leaves_mail_and_all_other_reports_running(self):
        stats={'students':1,'courses':1,'emails':1,'failed':0,
               'details':[{'email':'student@example.test','course':'Ders','mail':'gönderildi'}]}
        report=MagicMock(payload={})
        with patch('core.management.commands.run_daily_programs.run_daily_programs',return_value=stats), \
             patch('mobile_api.daily_kpis.capture_report',return_value=(report,True)), \
             patch('mobile_api.daily_kpis.format_report',return_value='KPI summary'), \
             patch('mobile_api.kpi_chart.send_mobile_kpi_chart',side_effect=RuntimeError('plot failed')) as chart, \
             patch('core.management.commands.run_daily_programs.notify_telegram') as telegram, \
             patch('core.management.commands.run_daily_programs.send_daily_report_email') as email, \
             patch('core.management.commands.run_daily_programs.send_daily_traffic_report') as traffic, \
             patch('core.management.commands.run_daily_programs.send_daily_meeting_digest') as meetings, \
             patch('core.management.commands.run_daily_programs.send_weekly_telegram_note') as weekly, \
             patch('core.student_monitoring.capture_snapshot',return_value=(MagicMock(reporting_date=date(2026,10,30)),True)) as monitoring:
            call_command('run_daily_programs',stdout=StringIO(),stderr=StringIO())
        chart.assert_called_once();telegram.assert_called_once();email.assert_called_once()
        traffic.assert_called_once();meetings.assert_called_once();weekly.assert_called_once();monitoring.assert_called_once()
        self.assertNotIn('student@example.test',telegram.call_args.args[0])
        self.assertIn('student@example.test',email.call_args.args[0])
