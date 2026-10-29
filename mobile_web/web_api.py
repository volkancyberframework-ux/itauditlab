"""Web-only adapters. Existing mobile URLs and clients are untouched."""
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError,PermissionDenied
from mobile_api import views as mobile
from mobile_api.models import LearningPath,LearningSession,Question,UserPathProgress,QuestionAttempt,XPTransaction,MobileSettings
from mobile_api.ad_auditor import KEY,is_ad,feedback
from mobile_api.linux_auditor import is_linux
from mobile_api.levels import level_data

def web_paths(user):
    normal=mobile.paths(user)
    extras=LearningPath.objects.filter(owner=None,preferences__web_only=True,preferences__web_published=True,preferences__ad_auditor_v1__enabled=True)
    if not mobile.premium(user):
        free=MobileSettings.objects.filter(pk=1).values_list('free_path_id',flat=True).first();extras=extras.filter(pk=free)
    return LearningPath.objects.filter(Q(pk__in=normal.values('pk'))|Q(pk__in=extras.values('pk'))).order_by('order','id')

def web_path_data(path,user):
    value=mobile.path_data(path,user)
    value['web_has_images']=path.questions.filter(published=True).exclude(image='').exists()
    if is_ad(path):value.update(direct_start=True,session_size=15,web_only=True)
    if is_linux(path):value.update(direct_start=True,session_size=16,web_only=False)
    return value

def enrich(state,session,request):
    path=session.path;state['path']=web_path_data(path,request.user)
    q=state.get('question')
    if q and is_linux(path):
        model=Question.objects.get(pk=q['id'])
        q.update(hint=model.hint,chapter=model.module.title,number=model.order,synthetic_image=True)
    if q and is_ad(path):
        model=Question.objects.get(pk=q['id'])
        q.update(image=request.build_absolute_uri(f'/web-api/questions/{model.pk}/image/'),hint=model.hint,
                 chapter=model.module.title,number=model.order,synthetic_image=True)
        q['options']=[{'id':o['id'],'text':o['text']} for o in mobile.options(model)[0]]
    if state['complete'] and is_ad(path):
        latest={a.question_id:a for a in QuestionAttempt.objects.filter(session__user=request.user,session__path=path,session__is_archived=False).select_related('question__module').order_by('created_at','pk')}
        completed=[]
        for module in path.modules.order_by('order'):
            rows=[a for a in latest.values() if a.question.module_id==module.pk]
            if len(rows)==15:completed.append({'chapter':module.order,'title':module.title,'correct':sum(a.is_correct for a in rows),'total':15,'concepts':[a.question.goals[0] for a in rows]})
        current=next((c for c in completed if c['chapter']==Question.objects.get(pk=session.questions[0]).module.order),None)
        total_correct=sum(a.is_correct for a in latest.values());done=len(latest)==75
        text=(f'{current["title"]}\n{current["correct"]}/15 doğru · %{round(current["correct"]/15*100)}\n\nÖğrendiğin kavramlar: '+', '.join(current['concepts'])) if current else ''
        if done:
            best=max(completed,key=lambda c:c['correct']);weak=min(completed,key=lambda c:c['correct'])
            text+=f'\n\nİlk AD denetim simülasyonunu tamamladın!\n{total_correct}/75 doğru · %{round(total_correct/75*100)}\nEn güçlü alan: {best["title"]}\nYeniden çalışılabilecek alan: {weak["title"]}\nBu sonuç uzmanlık belgesi değildir. Sonraki adım, yetkili bir labda hesap ve GPO kontrollerini güvenli biçimde gözlemlemek.'
        state['evaluation']={'text':text,'complete':done,'chapters':completed,'correct':total_correct,'total':75}
    return state

class Paths(mobile.MobileView):
    def get(self,request):
        if request.headers.get('X-GRC-Web-Bridge')=='1' and not request.COOKIES.get('grc_web_refresh'):
            return Response({'detail':'Web oturumu yenilenmeli.'},status=401)
        return Response([web_path_data(p,request.user) for p in web_paths(request.user)])

class Sessions(mobile.Sessions):
    @transaction.atomic
    def post(self,request):
        path=web_paths(request.user).filter(pk=mobile.integer_id(request.data.get('path_id'))).first()
        if not path:raise PermissionDenied('Bu öğrenme yolu hesabına açık değil.')
        if not is_ad(path):
            result=super().post(request)
            if result.status_code==201:
                session=LearningSession.objects.get(pk=result.data['id'],user=request.user);result.data=enrich(result.data,session,request)
            return result
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        active=LearningSession.objects.filter(user=request.user,path=path,is_archived=False,completed_at=None).order_by('-created_at').first()
        if active:return Response(ad_state(active,request),status=201)
        # The shared serializer's accessibility check is mobile-only. Build only the
        # web AD state here; no mobile permission or global publication is widened.
        progress=UserPathProgress.objects.filter(user=request.user,path=path).first()
        qs=path.questions.filter(published=True)
        if progress:qs=qs.exclude(pk__in=progress.completed.values('pk'))
        first=qs.first()
        if not first:raise ValidationError('Bu yolun bütün görevleri tamamlandı.')
        ids=list(qs.filter(module=first.module).values_list('pk',flat=True)[:15])
        session=LearningSession.objects.create(user=request.user,path=path,questions=ids)
        return Response(ad_state(session,request),status=201)

def ad_state(session,request):
    answered=set(session.attempts.values_list('question_id',flat=True));remaining=[i for i in session.questions if i not in answered]
    q=session.path.questions.filter(pk=remaining[0],published=True).first() if remaining else None
    if remaining and not q:raise ValidationError('Görev bulunamadı; içerik güncellenmiş olabilir.')
    state={'id':str(session.pk),'total':len(session.questions),'answered':len(answered),'question':mobile.question_data(q,session,request) if q else None,'complete':not remaining,
           'correct':session.attempts.filter(is_correct=True).count(),'question_total':len(session.questions),'information_read':0,'pending_reviews':0,
           'xp_earned':sum(session.attempts.values_list('xp_change',flat=True)),'path':web_path_data(session.path,request.user),'evaluation':None}
    return enrich(state,session,request)

def grade(q,answer):
    opts,keys=mobile.options(q)
    if q.kind in ('fill_blank','text'):
        if not isinstance(answer,str) or len(answer)>4000:raise ValidationError('Geçerli bir yanıt yaz.')
        return answer.strip().casefold() in [str(a).strip().casefold() for a in q.answer]
    if not isinstance(answer,list) or not answer or len(answer)>30 or any(not isinstance(a,str) for a in answer) or len(set(answer))!=len(answer):raise ValidationError('Geçerli seçenekleri seç.')
    valid={o['id'] for o in opts}
    if not set(answer)<=valid:raise ValidationError('Seçenek bu soruya ait değil.')
    if q.kind in ('image','choice','scenario','drag_select') and len(answer)!=1:raise ValidationError('Tek seçenek seç.')
    return answer==q.answer if q.kind=='sentence_order' else set(answer)==set(keys)

class Answer(mobile.Answer):
    @transaction.atomic
    def post(self,request,pk):
        session=LearningSession.objects.filter(pk=pk,user=request.user,is_archived=False).first()
        if not session:return Response(status=404)
        if not is_ad(session.path):
            result=super().post(request,pk)
            if result.status_code==200:result.data['session']=enrich(result.data['session'],session,request)
            return result
        if not web_paths(request.user).filter(pk=session.path_id).exists():raise PermissionDenied('Bu içerik hesabına açık değil.')
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        session=LearningSession.objects.select_for_update().get(pk=pk,user=request.user,is_archived=False)
        qid=request.data.get('question_id')
        if type(qid)is not int or qid not in session.questions:raise ValidationError('Soru bu oturuma ait değil.')
        q=session.path.questions.get(pk=qid,published=True);previous=session.attempts.filter(question=q).first()
        if previous:return Response({'correct':previous.is_correct,'xp_change':previous.xp_change,'explanation':feedback(q,previous.answer,previous.is_correct),'hint':q.hint,'session':ad_state(session,request)})
        answered=set(session.attempts.values_list('question_id',flat=True))
        if qid!=next((i for i in session.questions if i not in answered),None):raise ValidationError('Önce mevcut görevi tamamla.')
        answer=request.data.get('answer');correct=grade(q,answer);duration=request.data.get('duration_seconds',0)
        if type(duration)is not int or not 0<=duration<=86400:raise ValidationError('Süre geçersiz.')
        rewarded=QuestionAttempt.objects.filter(session__user=request.user,session__path=session.path,session__is_archived=False,question=q,is_correct=True).exists()
        delta=q.base_xp if correct and not rewarded else 0
        attempt=QuestionAttempt.objects.create(session=session,question=q,answer=answer,is_correct=correct,xp_change=delta,duration_seconds=duration)
        XPTransaction.objects.create(user=request.user,attempt=attempt,amount=delta,reason='correct' if correct else 'practice')
        progress,_=UserPathProgress.objects.get_or_create(user=request.user,path=session.path);progress.completed.add(q);progress.save()
        level_data(mobile.xp(request.user),request.user)
        if session.attempts.count()==len(session.questions):session.completed_at=timezone.now();session.save(update_fields=['completed_at'])
        return Response({'correct':correct,'xp_change':delta,'explanation':feedback(q,answer,correct),'hint':q.hint,'session':ad_state(session,request)})

class Image(mobile.MobileView):
    def get(self,request,pk):
        from django.http import FileResponse
        q=Question.objects.filter(pk=pk,published=True,paths__in=web_paths(request.user)).distinct().first()
        if not q or not q.image:return Response(status=404)
        result=FileResponse(q.image.open('rb'),content_type='image/png');result['Cache-Control']='private, no-store';result['X-Content-Type-Options']='nosniff';return result

# Browser-only shared refresh cookie keeps the HTML layer and the existing web
# client's token rotation synchronized. Native authentication remains unchanged.
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from mobile_api.access import MobileTokenRefreshSerializer

def refresh_cookie(response,value):
    response.set_cookie('grc_web_refresh',value,max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),secure=True,httponly=True,samesite='Strict',path='/web-api/')
    response['Cache-Control']='no-store'
    return response

class Login(mobile.Login):
    def post(self,request):
        response=super().post(request)
        if response.status_code==200:refresh_cookie(response,response.data['refresh'])
        return response

class Refresh(mobile.Login):
    def post(self,request):
        token=request.COOKIES.get('grc_web_refresh')
        if token:
            origin=request.headers.get('Origin','')
            if origin!='https://'+request.get_host():raise PermissionDenied('Oturum yenileme yalnız uygulamanın kendi adresinden yapılabilir.')
        else:token=request.data.get('refresh')
        serializer=MobileTokenRefreshSerializer(data={'refresh':token});serializer.is_valid(raise_exception=True)
        response=Response(serializer.validated_data)
        if 'refresh' in serializer.validated_data:refresh_cookie(response,serializer.validated_data['refresh'])
        response['Cache-Control']='no-store';return response

class Logout(mobile.MobileView):
    def post(self,request):
        token=request.COOKIES.get('grc_web_refresh') or request.data.get('refresh')
        if token:
            try:
                value=RefreshToken(token)
                if str(value.get('user_id'))!=str(request.user.pk):raise PermissionDenied('Oturum bu hesaba ait değil.')
                value.blacklist()
            except PermissionDenied:raise
            except Exception:pass
        response=Response(status=204);response.delete_cookie('grc_web_refresh',path='/web-api/',samesite='Strict');return response
