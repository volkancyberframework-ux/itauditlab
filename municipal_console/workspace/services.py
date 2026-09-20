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
    if data.get('status') in ('implemented','na') and not data.get('explanation','').strip():raise ValidationError('Bu durum için açıklama zorunludur.')
    control=Control.objects.select_for_update().get(pk=control.pk,audit=audit)
    latest=control.revisions.first()
    if latest and latest.actor_id!=actor.pk and not writable:raise PermissionDenied('Başka kullanıcının yanıtını değiştiremezsiniz.')
    ResponseRevision.objects.create(control=control,actor=actor,**data)
    Evaluation.objects.filter(control=control,verified=True).update(verified=False)
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
        if answered_count(audit)!=audit.controls.count():raise ValidationError('Yeni kontroller dahil tüm BT yanıtları tamamlanmalıdır.')
        if audit.controls.exclude(evaluation__assessment__in=['compliant','partial','noncompliant'],evaluation__verified=True).exists():raise ValidationError('Önce tüm kontrollerin denetçi değerlendirmesini tamamlayın.')
    elif audit.phase=='remediation' and target=='completed':
        if answered_count(audit)!=audit.controls.count() or audit.controls.exclude(evaluation__verified=True).exists():raise ValidationError('Yeni kontroller dahil tüm BT yanıtları ve son test onayları tamamlanmalıdır.')
        if audit.findings.exclude(status__in=['closed','risk_accepted']).exists():raise ValidationError('Açık bulgular kapanmadan denetim tamamlanamaz.')
    else:raise ValidationError('Bu faz geçişi yapılamaz.')
    previous=audit.phase;audit.phase=target;audit.save(update_fields=['phase'])
    log(audit,actor,role,'Denetim fazı değişti',previous=previous,target=target)

@transaction.atomic
def evaluate(audit,control,actor,role,data,preview=False,writable=False):
    allowed(role,['admin','auditor'],preview,writable)
    audit=Audit.objects.select_for_update().get(pk=audit.pk)

    control=Control.objects.select_for_update().get(pk=control.pk,audit=audit)
    data=data.copy()
    recommendation=data.pop('recommendation')
    due_date=data.pop('due_date',None)
    if due_date:
        from django.utils import timezone
        if due_date<timezone.localdate():raise ValidationError('Son tarih geçmiş olamaz.')
    old=Evaluation.objects.filter(control=control).values('assessment','rationale').first()
    evaluation,_=Evaluation.objects.update_or_create(control=control,defaults={**data,'customer_visible':False})
    if evaluation.assessment in ['partial','noncompliant']:
        finding,created=Finding.objects.get_or_create(control=control,defaults={'audit':audit,'title':control.title,'severity':'high' if evaluation.assessment=='noncompliant' else 'medium','recommendation':recommendation,'customer_visible':True,**({'due_date':due_date} if due_date else {})})
        if not created:
            previous=finding.status
            finding.recommendation=recommendation;finding.severity='high' if evaluation.assessment=='noncompliant' else 'medium'
            if due_date:finding.due_date=due_date
            if finding.status in ('closed','risk_accepted'):
                finding.treatment='undecided'
                finding.status='open';FindingUpdate.objects.create(finding=finding,actor=actor,role=role,action='reopen',explanation='Yeni denetçi değerlendirmesi nedeniyle yeniden açıldı.')
            finding.save()
        log(audit,actor,role,'Bulgu oluşturuldu/güncellendi',finding=finding.pk)
    log(audit,actor,role,'Denetçi değerlendirmesi kaydedildi',control=control.code,previous=old,current=data,recommendation=recommendation,due_date=str(due_date) if due_date else None)

@transaction.atomic
def finding_action(audit,finding,actor,role,action,explanation,preview=False,writable=False,due_date=None):
    roles=['it'] if action in ('remediate','dispute','acknowledge','plan','request_risk') else (['admin','executive'] if action=='accept_risk' else ['admin','auditor'])
    allowed(role,roles,preview,writable)
    audit=Audit.objects.select_for_update().get(pk=audit.pk)
    finding=Finding.objects.select_for_update().get(pk=finding.pk,audit=audit)
    targets={'remediate':'remediation_submitted','dispute':'disputed','close':'closed','reject':'open','reopen':'open','acknowledge':'open','plan':'open','request_risk':'open','accept_risk':'risk_accepted','set_due':finding.status}
    if action not in targets:raise ValidationError('Geçersiz işlem.')
    if finding.is_terminal and action!='reopen':raise ValidationError('Sonuçlanmış bulgu önce yeniden açılmalıdır.')
    if action=='close' and finding.status not in ['remediation_submitted','disputed']:raise ValidationError('Kapanıştan önce BT giderim bildirimi veya itirazı incelenmelidir.')
    if action=='reject' and finding.status not in ['remediation_submitted','disputed'] and finding.treatment!='risk_requested':raise ValidationError('İncelenecek bir bildirim bulunmuyor.')
    if action=='reopen' and not finding.is_terminal:raise ValidationError('Bu bulgu zaten açık.')
    if action=='accept_risk' and finding.treatment!='risk_requested':raise ValidationError('Önce BT risk kabulü talebi bulunmalıdır.')
    if action in ('plan','set_due'):
        from django.utils import timezone
        if not due_date or due_date<timezone.localdate():raise ValidationError('Geçerli bir son tarih girin.')
        finding.due_date=due_date
    treatment={'acknowledge':'acknowledged','plan':'mitigate','request_risk':'risk_requested','accept_risk':'risk_accepted','reopen':'undecided','reject':'undecided'}
    if action in treatment:finding.treatment=treatment[action]
    note=explanation+(f' · Son tarih: {due_date:%d.%m.%Y}' if action in ('plan','set_due') else '')
    FindingUpdate.objects.create(finding=finding,actor=actor,role=role,action=action,explanation=note)
    finding.status=targets[action];finding.save()
    log(audit,actor,role,'Bulgu işlemi',finding=finding.pk,action_type=action,explanation=note)

@transaction.atomic
def review_suggestion(audit,suggestion,actor,role,decision,note,preview=False,writable=False):
    allowed(role,['admin','auditor'],preview,writable)
    audit=Audit.objects.select_for_update().get(pk=audit.pk)
    suggestion=Suggestion.objects.select_for_update().get(pk=suggestion.pk,audit=audit)
    if suggestion.status!='pending':raise ValidationError('Öneri daha önce incelendi.')
    if decision=='accepted':

        number=audit.controls.count()+1
        while audit.controls.filter(code=f'GRC-{number:03d}').exists():number+=1
        suggestion.control=Control.objects.create(audit=audit,code=f'GRC-{number:03d}',title=suggestion.title,description=suggestion.description,evidence_guidance=suggestion.test_steps,framework=suggestion.framework,theme='Stajyer önerisi',risk='medium',intern_visible=True)
    elif decision!='rejected':raise ValidationError('Geçersiz karar.')
    suggestion.status=decision;suggestion.review_note=note;suggestion.save()
    log(audit,actor,role,'Kontrol önerisi incelendi',suggestion=suggestion.pk,decision=decision)
