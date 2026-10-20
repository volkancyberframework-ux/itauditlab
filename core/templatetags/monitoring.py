from datetime import datetime
from django import template
from django.utils import timezone
from django.utils.formats import date_format
register = template.Library()

@register.filter
def monitoring_time(value):
    if not value:
        return 'Bilinmiyor'
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    return date_format(timezone.localtime(value), 'd.m.Y H:i')

@register.filter
def monitoring_status(value):
    return {'active':'Aktif', 'paused':'Duraklatıldı', 'archived':'Arşivlendi', 'completed':'Tamamlandı',
        'draft_created':'Taslak oluşturuldu', 'intervention_save':'Taslak düzenlendi', 'intervention_open':'E-posta uygulamasını açma isteği',
        'intervention_sent':'Elle gönderildi işaretlendi', 'intervention_status':'Müdahale durumu değişti', 'completion_evidence':'Tamamlanma kanıtı güncellendi',
        'enrollment_monitoring_status':'İzleme kayıt durumu değişti', 'enrollment_monitoring_lesson':'Ders muafiyeti değişti',
        'settings_changed':'İzleme ayarları değişti', 'snapshot_correction':'Günlük özet düzeltildi', 'monitoring_refreshed':'İzleme yenilendi'}.get(value, value)
