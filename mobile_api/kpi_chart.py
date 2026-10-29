"""Rolling seven-day Telegram chart. PNGs exist only in a closed BytesIO buffer."""
from datetime import date, timedelta
from io import BytesIO

import requests
from django.conf import settings

from .daily_kpis import daily_metrics, delta, number, students
from .models import MobileDailyKPI


def seven_day_metrics(report_date):
    last = report_date-timedelta(days=1)
    days = [last-timedelta(days=offset) for offset in range(6,-1,-1)]
    snapshots = MobileDailyKPI.objects.filter(report_date__gte=days[0]+timedelta(days=1),
                                              report_date__lte=report_date)
    saved = {}
    for row in snapshots:
        current = row.payload.get('current', {})
        if current.get('date') == (row.report_date-timedelta(days=1)).isoformat():
            saved[current['date']] = current
    user_ids = students().values('pk')
    return [saved[day.isoformat()] if day.isoformat() in saved else daily_metrics(day,user_ids) for day in days]


def comparison(current, previous, percentage=False):
    if current is None or previous is None:
        return 'veri yok' if current is None else f'{number(current)}% • kıyas yok'
    suffix = ' puan' if percentage else ''
    return f"{number(current)}{'%' if percentage else ''} • {delta(current,previous)}{suffix}"


def render_chart(points):
    """Return an open in-memory PNG; caller owns/always closes it after sending."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.ticker import MaxNLocator
    if len(points)!=7:
        raise ValueError('Grafik tam olarak yedi gün içermeli.')
    dates = [date.fromisoformat(p['date']) for p in points]
    if dates != [dates[0]+timedelta(days=i) for i in range(7)]:
        raise ValueError('Grafik günleri ardışık ve artan olmalı.')
    buffer = BytesIO()
    figure = Figure(figsize=(12.8,8.4),dpi=160,facecolor='#0b1523')
    try:
        axes = figure.subplots(2,2)
        figure.subplots_adjust(left=.065,right=.97,bottom=.10,top=.745,wspace=.18,hspace=.52)
        figure.text(.065,.935,'GRC USTASI  /  MOBİL UYGULAMA',fontsize=23,weight='bold',color='#edf4fc')
        figure.text(.065,.89,f"Son 7 tamamlanan gün · {dates[0]:%d.%m.%Y} – {dates[-1]:%d.%m.%Y} · İstanbul",fontsize=12,color='#adbed1')
        figure.text(.065,.845,'Sağdaki vurgulu gün: son gün  |  Başlıklardaki fark: bir önceki güne göre',fontsize=11,color='#adbed1')
        specifications = [
            ('active','Aktif öğrenciler','#60a5fa',False),
            ('answers','Soru yanıtları','#5eead4',False),
            ('accuracy','Otomatik değerlendirmede doğruluk','#fbbf24',True),
            ('sessions_completed','Tamamlanan çalışma oturumları','#c4b5fd',False),
        ]
        for ax,(key,title,color,is_percentage) in zip(axes.flat,specifications):
            values = [p.get(key) for p in points]
            plotted = [float('nan') if value is None else value for value in values]
            ax.set_facecolor('#122235')
            ax.axvspan(5.55,6.45,color=color,alpha=.10,zorder=0)
            ax.plot(range(7),plotted,color=color,linewidth=2.8,marker='o',markersize=6,zorder=3)
            for i,value in enumerate(values):
                if value is not None:
                    ax.annotate(number(value)+( '%' if is_percentage else ''),(i,value),
                                textcoords='offset points',xytext=(0,9),ha='center',fontsize=10,color='#edf4fc')
            ax.set_title(title+'\nSon gün: '+comparison(values[-1],values[-2],is_percentage),
                         loc='left',fontsize=12,color='#edf4fc',pad=15,fontweight='bold')
            ax.set_xticks(range(7),[day.strftime('%d.%m') for day in dates])
            ax.set_xlim(-.4,6.5)
            if is_percentage:
                ax.set_ylim(-5,115);ax.set_yticks([0,25,50,75,100],['0%','25%','50%','75%','100%'])
            else:
                ax.set_ylim(0,max(1,max(v or 0 for v in values))*1.28)
                ax.yaxis.set_major_locator(MaxNLocator(nbins=4,integer=True))
            ax.tick_params(colors='#adbed1',labelsize=10,length=0,pad=8)
            ax.grid(axis='y',color='#304357',alpha=.65,linewidth=.7)
            for spine in ax.spines.values():spine.set_visible(False)
            if all(value is None for value in values):
                ax.text(.5,.5,'Bu dönemde değerlendirilen yanıt yok',transform=ax.transAxes,ha='center',color='#adbed1',fontsize=10)
        figure.text(.065,.035,'Kayıtlı mobil + web etkinliği · Yönetici hesapları hariç · Yanıtlar tekrarları içerir · Doğrulukta sesli/serbest metin hariç',
                    color='#adbed1',fontsize=9)
        FigureCanvasAgg(figure).print_png(buffer)
        buffer.seek(0)
        return buffer
    except Exception:
        buffer.close()
        raise
    finally:
        figure.clear()


def send_mobile_kpi_chart(report_date):
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return False
    points = seven_day_metrics(report_date)
    latest,previous = points[-1],points[-2]
    first_day,last_day = date.fromisoformat(points[0]['date']),date.fromisoformat(latest['date'])
    caption = (f"📊 GRC Ustası Mobil — Son 7 gün\n{first_day:%d.%m.%Y} – {last_day:%d.%m.%Y} • İstanbul\n"
               f"Son gün / önceki güne göre:\nAktif: {comparison(latest['active'],previous['active'])}\n"
               f"Yanıt: {comparison(latest['answers'],previous['answers'])}\n"
               f"Doğruluk: {comparison(latest['accuracy'],previous['accuracy'],True)}\n"
               f"Tamamlanan oturum: {comparison(latest['sessions_completed'],previous['sessions_completed'])}")
    with render_chart(points) as image:
        with requests.post(f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendPhoto',
                           data={'chat_id':settings.TELEGRAM_CHAT_ID,'caption':caption},
                           files={'photo':('mobil-son-7-gun.png',image,'image/png')},timeout=(5,30)) as response:
            response.raise_for_status()
            if response.json().get('ok') is not True:
                raise RuntimeError('Telegram grafik gönderimini kabul etmedi.')
    return True
