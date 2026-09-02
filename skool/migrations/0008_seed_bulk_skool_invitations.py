import hashlib
import secrets
import unicodedata

from django.db import migrations


NAMES = (
    "Can Şafak Çakır", "Zeynep Dilara Kurnaz", "Ömer Ahmet Yılmaz", "Elmir Jafarov",
    "Batuhan Duman", "Ömer Faruk Turan", "Teoman Turhan", "Recep Yalçın", "Harun Can",
    "Burak Dirlik", "Ekrem Özer", "Nedim Kahraman", "Pirzat Türken", "Jasmine Nguyen",
    "Hasan Basri Eren", "Ali Rıza Gökçin", "Ozan Şahin", "Aziz Kaan Erkmen", "Eray Yavuz",
    "Ramazan Baştürk", "Ali Bayat", "Ozan Güncan", "Oktay Demircioğlu", "Cemrehan Kara",
    "Ezgi Baykal", "Taha Kaçuru", "Alperen Şahin", "Okan Gerdan", "Nihad Asgarov",
    "Mehmet Palak", "Barkın Kahraman", "Kemal Mustafaoglu", "Safa Sonkaya",
    "Cagri Gorkem Can", "Salih Okan", "Narmin Ali", "Furkan Uğur", "Fehmi Alper Demir",
    "Emre Aslan", "Ahmet Can Aytekin", "Ihsan Yilmaz", "Mehmet Polat", "Omer Canatan",
    "Yusuf Demir", "Eren Alphan", "Yusuf Avci", "Eren Yiğit", "Kaan Bilgiç",
    "Mahmut Kocaman", "Kuzey Ahmet", "Arda Kölemenoğlu", "Ahmet Ozturk", "Zeren Karataş",
    "Alperen Kayis", "Hasan Arı", "A. Levent Tatar", "Ruveyda Ardıç", "Fatih Karalık",
    "Ilgaz Tümer", "Çağrı Görgeç", "Yaşar Sönmez", "Selin Mansiz", "Merve Turgut",
    "Mert Solak", "Mugur Ugur", "Yasin Dağarslan", "Bunyamin Fidan", "Seher Kantar",
    "Maharram Maharramov", "Emrullah Aydin", "Onur Alemdağ", "Mustafa Anıl Türk",
    "Yusuf Balaban", "İsmail Çelik", "Fadime Karakaya", "Volkan Altınbaş", "Alican Yalçın",
    "Çağlar Durmaz", "Mehmet Karakaya", "Ali Ocakçı", "Esat Bostancioglu", "Murat Salci",
    "Fethi Ocalan", "Ali Kara", "Fatih Emre Kara", "Hido Sarı", "Hasan Şeker", "Toygar A",
    "Deniz Vural", "Gül Nihal Şimşek", "Çağdaş Ata", "Hüseyin Akyol", "Joseph Elwood",
    "Betül B", "Efe Esen", "Baris Kara", "Bekir Can", "Mirac Kaya", "Recep Güler",
    "Mürsel Ünver", "Sefer Demirtas", "Levent Ceylan", "Beyzanur Aslantepe",
    "Hasan Eren Çakıcı", "Selehattin Ozsevgec", "Emir Gülçür", "Murat Çakmak", "Emre Yazıcı",
    "Hakan Nazifoglu", "Eren Arslan", "Bedirhan Şirin", "Muhittin Akar", "Agit Baran",
    "MuhammadAli Novruzlu", "Zehra Yıldız", "Ruveyda Durmuş", "Özkan Doğan",
    "Macit Serhat Kandemir", "Tahir Komkeser", "Murat Akdogan", "Abdürrahim Türk",
    "Mehmetali Dikmen", "Öztürk Certel", "Bilal Uygur", "Koray Ulavur", "Emir Yiğit",
    "Ecem Uçar", "Esra Çifçi", "Huseyn G.", "Ahmet Batuhan", "Ulaş Aslan", "Mahsun Sezgin",
    "Oğuzhan Özkan", "Necdet Emre Bayraktar", "Eren Ergen", "Ramazan Abbasov",
    "Erkal Gultekin", "Hazar Meydan", "Efe Emir Gürbüz", "Zeynep Polat", "Murat Kabak",
    "Emir Yavuz Çankaya", "Furkan Taşkın", "Sami Çiçekli", "Metin Selayet",
    "Ayşen Çavuşoğlu", "Altay Aydın", "Ahmet Önal", "Volkan Güler",
)


def normalize_name(value):
    return unicodedata.normalize("NFC", " ".join(value.strip().split()).casefold())


def seed_invitations(apps, schema_editor):
    SkoolInvitation = apps.get_model("skool", "SkoolInvitation")
    for full_name in NAMES:
        normalized = normalize_name(full_name)
        if SkoolInvitation.objects.filter(
            normalized_name=normalized,
            status__in=("invited", "claimed"),
        ).exists():
            continue
        raw_token = secrets.token_urlsafe(32)
        SkoolInvitation.objects.create(
            full_name=full_name,
            normalized_name=normalized,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            status="invited",
        )


class Migration(migrations.Migration):
    dependencies = [("skool", "0007_skoollabprogress")]

    operations = [migrations.RunPython(seed_invitations, migrations.RunPython.noop)]
