from pathlib import Path

from django.db import transaction

from .models import SkoolLab


LABS = (
    (1, "FinCore Bank - Kullanıcı Yetkileri ve Access Review Denetimi", "GRC_Ustasi_Lab_01_fincore_bank_access_review.pdf", "Kullanıcı yaşam döngüsü, ayrıcalıklı erişimler ve dönemsel erişim gözden geçirmesi."),
    (2, "NovaPay - Third Party Risk Management", "GRC_Ustasi_Lab_02_novapay_third_party_risk.pdf", "Kritik bir hizmet sağlayıcının seçimi, izlenmesi ve üçüncü taraf risklerinin değerlendirilmesi."),
    (3, "NextCorp - ISO 27001 İç Denetimi", "GRC_Ustasi_Lab_03_nextcorp_iso27001_internal_audit.pdf", "ISO 27001 iç denetiminde kapsam, kanıt, kontrol sahipliği ve bulgu geliştirme."),
    (4, "GlobalBank - Change Management Denetimi", "GRC_Ustasi_Lab_04_globalbank_change_management.pdf", "Üretim değişikliklerinde onay, test, görevler ayrılığı ve acil değişiklik kontrolleri."),
    (5, "MediCloud - IT Risk Assessment", "GRC_Ustasi_Lab_05_medicloud_it_risk_assessment.pdf", "Sağlık verisi işleyen bulut ortamında varlık, tehdit, kontrol ve artık risk değerlendirmesi."),
    (6, "ShopNow - Siber Olay Sonrası GRC İncelemesi", "GRC_Ustasi_Lab_06_shopnow_post_incident_grc_review.pdf", "Bir siber olay sonrasında yönetişim, müdahale, kök neden ve iyileştirme planı incelemesi."),
    (7, "FinTechX - Segregation of Duties", "GRC_Ustasi_Lab_07_fintechx_segregation_of_duties.pdf", "Kritik finansal süreçlerde görevler ayrılığı çatışmaları ve telafi edici kontroller."),
    (8, "DataCore - Backup, Disaster Recovery ve Business Continuity", "GRC_Ustasi_Lab_08_datacore_backup_dr_bcp.pdf", "Yedekleme, felaket kurtarma ve iş sürekliliği kontrollerinin birlikte değerlendirilmesi."),
    (9, "SecureBank - Uçtan Uca BT Denetimi", "GRC_Ustasi_Lab_09_securebank_end_to_end_it_audit.pdf", "Planlamadan raporlamaya, bir banka ortamında uçtan uca BT denetimi."),
    (10, "GlobalFinance - Yönetim Kuruluna Siber Risk Raporlama", "GRC_Ustasi_Lab_10_globalfinance_board_cyber_reporting.pdf", "Teknik bulguları karar alınabilir yönetim kurulu siber risk raporuna dönüştürme."),
)


def bundled_pdf_path(filename):
    return Path(__file__).resolve().parent / "lab_assets" / Path(filename).name


@transaction.atomic
def ensure_lab_records():
    """Ensure the built-in library exists even when a deploy hook was skipped."""
    for order, title, filename, description in LABS:
        lab, _ = SkoolLab.objects.get_or_create(
            title=title,
            defaults={
                "description": description,
                "pdf": f"skool_labs/{filename}",
                "order": order,
                "is_active": True,
            },
        )
        changed = []
        for field, value in (("description", description), ("order", order), ("is_active", True)):
            if getattr(lab, field) != value:
                setattr(lab, field, value)
                changed.append(field)
        if not lab.pdf:
            lab.pdf = f"skool_labs/{filename}"
            changed.append("pdf")
        if changed:
            lab.save(update_fields=changed)

