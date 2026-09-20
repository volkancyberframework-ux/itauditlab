from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from .models import Audit, Control, ResponseRevision, Evaluation, Finding, FindingUpdate, Activity, Suggestion

def log(audit,actor,role,action,**metadata):
    Activity.objects.create(audit=audit,actor=actor,role=role,action=action,metadata=metadata)

def allowed(role,roles,preview,writable):
    if role not in roles or (preview and not writable):raise PermissionDenied('Bu rolde işlem yetkiniz yok.')

@transaction.atomic
def answer(audit,control,actor,role,data,preview=False,writable=False):
    allowed(role,['it'],preview,writable)
    audit=Audit.objects.select_for_update().get(pk=audit.pk)
    if audit.phase not in ['responses','completed']:raise ValidationError('BT yanıt fazı kapalı. Yeni açıklamanızı ilgili bulgu üzerinden paylaşın.')
    control=Control.objects.select_for_update().get(pk=control.pk,audit=audit)
    latest=control.revisions.first()
    if latest and latest.actor_id!=actor.pk and not writable:raise PermissionDenied('Başka kullanıcının yanıtını değiştiremezsiniz.')
    ResponseRevision.objects.create(control=control,actor=actor,**data)
    log(audit,actor,role,'BT yanıtı kaydedildi',control=control.code,status=data['status'])

def answered_count(audit):
    return sum(c.revisions.exists() and c.revisions.first().status!='unanswered' for c in audit.controls.all())

@transaction.atomic
def transition(audit,actor,role,target,preview=False,writable=False):
    allowed(role,['admin','auditor'],preview,writable)
    audit=Audit.objects.select_for_update().get(pk=audit.pk)
    if audit.phase=='responses' and target=='fieldwork':
        if not audit.controls.exists() or answered_count(audit)!=audit.controls.count():raise ValidationError('Saha denetimine geçmeden önce tüm BT yanıtları tamamlanmalıdır.')
    elif audit.phase=='fieldwork' and target=='remediation':
        if audit.controls.exclude(evaluation__assessment__in=['compliant','partial','noncompliant']).exists():raise ValidationError('Önce tüm kontrollerin denetçi değerlendirmesini tamamlayın.')
    elif audit.phase=='remediation' and target=='completed':
        if audit.findings.exclude(status='closed').exists():raise ValidationError('Açık bulgular kapanmadan denetim tamamlanamaz.')
    else:raise ValidationError('Bu faz geçişi yapılamaz.')
    previous=audit.phase;audit.phase=target;audit.save(update_fields=['phase'])
    log(audit,actor,role,'Denetim fazı değişti',previous=previous,target=target)

@transaction.atomic
def evaluate(audit,control,actor,role,data,preview=False,writable=False):
    allowed(role,['admin','auditor'],preview,writable)
    audit=Audit.objects.select_for_update().get(pk=audit.pk)
    if audit.phase not in ['fieldwork','remediation','completed'] or (audit.phase!='completed' and audit.appointment_status!='confirmed'):raise ValidationError('Değerlendirme için saha fazı ve onaylanmış randevu gereklidir.')
    control=Control.objects.select_for_update().get(pk=control.pk,audit=audit)
    recommendation=data.pop('recommendation')
    old=Evaluation.objects.filter(control=control).values('assessment','rationale').first()
    evaluation,_=Evaluation.objects.update_or_create(control=control,defaults={**data,'customer_visible':False})
    if evaluation.assessment in ['partial','noncompliant']:
        finding,created=Finding.objects.get_or_create(control=control,defaults={'audit':audit,'title':control.title,'severity':'high' if evaluation.assessment=='noncompliant' else 'medium','recommendation':recommendation,'customer_visible':True})
        if not created:
            previous=finding.status
            finding.recommendation=recommendation;finding.severity='high' if evaluation.assessment=='noncompliant' else 'medium'
            if finding.status=='closed':
                finding.status='open';FindingUpdate.objects.create(finding=finding,actor=actor,role=role,action='reopen',explanation='Yeni denetçi değerlendirmesi nedeniyle yeniden açıldı.')
            finding.save()
        log(audit,actor,role,'Bulgu oluşturuldu/güncellendi',finding=finding.pk)
    log(audit,actor,role,'Denetçi değerlendirmesi kaydedildi',control=control.code,previous=old,current=data,recommendation=recommendation)

@transaction.atomic
def finding_action(audit,finding,actor,role,action,explanation,preview=False,writable=False):
    allowed(role,['it'] if action in ['remediate','dispute'] else ['admin','auditor'],preview,writable)
    audit=Audit.objects.select_for_update().get(pk=audit.pk)
    finding=Finding.objects.select_for_update().get(pk=finding.pk,audit=audit)
    if audit.phase not in ['fieldwork','remediation','completed']:raise ValidationError('Bu fazda bulgu işlemi yapılamaz.')
    targets={'remediate':'remediation_submitted','dispute':'disputed','close':'closed','reject':'open','reopen':'open'}
    if action not in targets:raise ValidationError('Geçersiz işlem.')
    if action in ['remediate','dispute'] and finding.status=='closed':raise ValidationError('Kapalı bulgu için yeni işlem yapılamaz.')
    if action=='close' and finding.status not in ['remediation_submitted','disputed']:raise ValidationError('Kapanıştan önce BT giderim bildirimi veya itirazı incelenmelidir.')
    if action=='reject' and finding.status not in ['remediation_submitted','disputed']:raise ValidationError('İncelenecek bir bildirim bulunmuyor.')
    if action=='reopen' and finding.status!='closed':raise ValidationError('Bu bulgu zaten açık.')
    FindingUpdate.objects.create(finding=finding,actor=actor,role=role,action=action,explanation=explanation)
    finding.status=targets[action];finding.save()
    log(audit,actor,role,'Bulgu işlemi',finding=finding.pk,action_type=action,explanation=explanation)

@transaction.atomic
def review_suggestion(audit,suggestion,actor,role,decision,note,preview=False,writable=False):
    allowed(role,['admin','auditor'],preview,writable)
    audit=Audit.objects.select_for_update().get(pk=audit.pk)
    suggestion=Suggestion.objects.select_for_update().get(pk=suggestion.pk,audit=audit)
    if suggestion.status!='pending':raise ValidationError('Öneri daha önce incelendi.')
    if decision=='accepted':
        if audit.phase not in ['responses','completed']:raise ValidationError('Kapsama yeni kontrol yalnızca BT yanıt fazında eklenebilir.')
        number=audit.controls.count()+1
        while audit.controls.filter(code=f'GRC-{number:03d}').exists():number+=1
        suggestion.control=Control.objects.create(audit=audit,code=f'GRC-{number:03d}',title=suggestion.title,description=suggestion.description,evidence_guidance=suggestion.test_steps,framework=suggestion.framework,theme='Stajyer önerisi',risk='medium',intern_visible=True)
    elif decision!='rejected':raise ValidationError('Geçersiz karar.')
    suggestion.status=decision;suggestion.review_note=note;suggestion.save()
    log(audit,actor,role,'Kontrol önerisi incelendi',suggestion=suggestion.pk,decision=decision)
