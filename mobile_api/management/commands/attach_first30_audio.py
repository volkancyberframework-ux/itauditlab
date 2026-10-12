from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.core.files import File
from django.db import transaction
from mobile_api.models import LearningPath, AudioAsset, Question
class Command(BaseCommand):
    help='Attach real grc_day_01.mp3 … grc_day_10.mp3 intros; never creates placeholder audio.'
    def add_arguments(self,p):
        p.add_argument('directory');p.add_argument('--path-id',type=int,default=26);p.add_argument('--apply',action='store_true')
    def handle(self,*a,**o):
        path=LearningPath.objects.get(pk=o['path_id']);reg=(path.preferences or {}).get('first30_v1',{})
        if 'İşe Alındın! İlk 30 Günün' not in path.title or len(reg.get('questions',{}))!=100:raise CommandError('Hedef doğrulanamadı.')
        files=[Path(o['directory'])/f'grc_day_{i:02}.mp3' for i in range(1,11)]
        for file in files:
            if not file.is_file() or file.stat().st_size<1000:raise CommandError(f'Gerçek kayıt eksik: {file.name}; hiçbir DB kaydı değişmedi.')
            header=file.read_bytes()[:3]
            if not (header==b'ID3' or (header[0]==255 and header[1]&224==224)):raise CommandError('MP3 başlığı geçersiz.')
        if not o['apply']:self.stdout.write('10 gerçek MP3 hazır; --apply ile yüklenebilir.');return
        with transaction.atomic():
            for i,file in enumerate(files,1):
                key=f'grc_day_{i:02}';q=Question.objects.get(pk=reg['questions'][f'grc-first30-q-{(i-1)*10+1:03}'])
                assets=AudioAsset.objects.filter(name_key=key)
                if assets.count()>1:raise CommandError('Tekrarlayan AudioAsset; otomatik eşleme yapılmadı.')
                asset=assets.first()
                if not asset:
                    asset=AudioAsset(title=f'İlk 30 Gün · Bölüm {i}',name_key=key)
                    with file.open('rb') as f:asset.file.save(file.name,File(f),save=True)
                elif not asset.file or not asset.file.storage.exists(asset.file.name):raise CommandError('Mevcut ses kaydı bozuk; üzerine yazılmadı.')
                q.intro=asset;q.save(update_fields=['intro'])
        self.stdout.write('10 intro bağlandı. Soru türleri değişmedi.')
