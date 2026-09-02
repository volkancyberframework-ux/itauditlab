import hashlib
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from skool.models import SkoolLab


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


def file_digest(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Command(BaseCommand):
    help = "GRC Ustası laboratuvar PDF'lerini medya diskine ve çalışma kütüphanesine yükler."

    def handle(self, *args, **options):
        assets = Path(__file__).resolve().parents[2] / "lab_assets"
        missing = [filename for _, _, filename, _ in LABS if not (assets / filename).is_file()]
        if missing:
            raise CommandError("Paketlenmiş laboratuvar dosyaları bulunamadı: " + ", ".join(missing))

        created = updated = unchanged = 0
        for order, title, filename, description in LABS:
            source_path = assets / filename
            lab, was_created = SkoolLab.objects.get_or_create(
                title=title,
                defaults={"description": description, "order": order, "is_active": True},
            )

            target_name = f"skool_labs/{filename}"
            stored_matches = False
            if lab.pdf and lab.pdf.name == target_name:
                try:
                    stored_matches = file_digest(source_path) == file_digest(Path(lab.pdf.path))
                except (FileNotFoundError, NotImplementedError, OSError):
                    stored_matches = False

            changed_fields = []
            if lab.description != description:
                lab.description = description
                changed_fields.append("description")
            if lab.order != order:
                lab.order = order
                changed_fields.append("order")
            if not lab.is_active:
                lab.is_active = True
                changed_fields.append("is_active")

            if not stored_matches:
                if lab.pdf:
                    lab.pdf.storage.delete(target_name)
                with source_path.open("rb") as source:
                    lab.pdf.save(filename, File(source), save=False)
                changed_fields.append("pdf")

            if changed_fields:
                lab.save(update_fields=tuple(dict.fromkeys(changed_fields)))

            if was_created:
                created += 1
            elif changed_fields:
                updated += 1
            else:
                unchanged += 1

        self.stdout.write(self.style.SUCCESS(
            f"GRC Ustası laboratuvarları hazır: {created} oluşturuldu, "
            f"{updated} güncellendi, {unchanged} değişmedi."
        ))
