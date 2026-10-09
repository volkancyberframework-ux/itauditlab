import uuid
from django.core import signing
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.throttling import AnonRateThrottle
from .models import Question, WorkshopVoice
from .views import MobileThrottle, options, private_file


class PublicView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [MobileThrottle]


def selected():
    return Question.objects.filter(published=True, in_workshop=True)


class Questions(PublicView):
    def get(self, request):
        result = []
        for q in selected().select_related('audio', 'intro'):
            opts, correct = options(q)
            base = f'/api/mobile/v1/workshop/questions/{q.pk}/'
            result.append(dict(id=q.pk, kind=q.kind, prompt=q.prompt, context=q.context,
                options=opts, answer=q.answer if q.kind in ['text', 'fill_blank', 'voice', 'sentence_order'] else correct,
                explanation=q.explanation, hint=q.hint, card_pages=q.card_pages,
                base_xp=0, image=request.build_absolute_uri(base+'image/') if q.image else None,
                audio=[request.build_absolute_uri(base+f'audio/{pk}/') for pk in [q.intro_id,q.audio_id] if pk],
                voice_token=signing.dumps({'question':q.pk}, salt='workshop-voice')))
        return Response(result)


class Audio(PublicView):
    def get(self, request, pk, audio_id):
        q = selected().filter(pk=pk).filter(Q(audio_id=audio_id)|Q(intro_id=audio_id)).first()
        if not q:
            return Response(status=404)
        asset = q.audio if q.audio_id == audio_id else q.intro
        import mimetypes
        return private_file(asset.file, mimetypes.guess_type(asset.file.name)[0] or 'audio/mp4')


class Image(PublicView):
    def get(self, request, pk):
        q = selected().filter(pk=pk).first()
        if not q or not q.image:
            return Response(status=404)
        import mimetypes
        return private_file(q.image, mimetypes.guess_type(q.image.name)[0] or 'image/png')


class VoiceThrottle(AnonRateThrottle):
    scope = 'workshop_voice'
    rate = '5/day'


class Voice(PublicView):
    throttle_classes = [VoiceThrottle]

    def post(self, request, pk):
        q = selected().filter(pk=pk, kind='voice').first()
        if not q:
            return Response(status=404)
        try:
            token = signing.loads(request.data.get('token',''), salt='workshop-voice', max_age=86400)
            if token.get('question') != q.pk:
                raise ValueError
            duration = int(request.data.get('duration',0))
            key = uuid.UUID(request.data.get('submission_id',''))
            email = str(request.data.get('email','')).strip().lower()
            validate_email(email)
            if len(email) > 254:
                raise ValueError
        except (ValueError, TypeError, signing.BadSignature, DjangoValidationError):
            raise ValidationError('Geçerli e-posta gir ve atölyeyi yeniden açıp dene.')
        upload = request.FILES.get('file')
        if not upload or not 0 < upload.size <= 10*1024*1024 or not 1 <= duration <= 180:
            raise ValidationError('En fazla 3 dakika ve 10 MB M4A kayıt gönderebilirsin.')
        head = upload.read(16); upload.seek(0)
        if len(head)<12 or head[4:8] != b'ftyp':
            raise ValidationError('M4A ses kaydı gerekli.')
        previous = WorkshopVoice.objects.filter(pk=key).first()
        if previous and (previous.email != email or previous.question_id != q.pk):
            raise ValidationError('Kayıt bilgileri geçersiz.')
        if not previous:
            upload.name = f'{uuid.uuid4()}.m4a'
            WorkshopVoice.objects.create(id=key,question=q,email=email,file=upload,duration=duration)
        return Response({'detail':'Sesli yanıtın alındı. Geri bildirimin 24 saat içinde e-posta adresine gönderilecektir.'})


def send_feedback(pk):
    from django.conf import settings
    from django.core.mail import send_mail
    with transaction.atomic():
        obj = WorkshopVoice.objects.select_for_update().select_related('question').get(pk=pk)
        if obj.feedback_sent_at:
            return
        if send_mail('GRC Ustası • Vaka atölyesi geri bildirimi',
            f'Soru: {obj.question.prompt}\n\n{obj.feedback}\n\nGRC Ustası',
            settings.DEFAULT_FROM_EMAIL,[obj.email],fail_silently=False) != 1:
            raise ValueError('E-posta gönderilemedi.')
        obj.feedback_sent_at = timezone.now()
        obj.save(update_fields=['feedback_sent_at'])
