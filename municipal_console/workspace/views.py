from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import Http404, HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django import forms
from django.urls import resolve, Resolver404, reverse
from .models import Audit, Membership, Control, ResponseRevision, Evaluation, Finding, Suggestion, Activity, ROLES, STATUSES, ControlDefinition
from .forms import ResponseForm, EvaluationForm, SuggestionForm, AppointmentForm, FindingForm, AddControlsForm
from . import services
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.utils import timezone
from collections import Counter

def ready(view):
    @login_required
    @never_cache
    @wraps(view)
    def wrapper(request,*args,**kwargs):
        if request.user.must_change_password:return redirect('change_password')
        return view(request,*args,**kwargs)
    return wrapper

def accessible_audits(request):
    audits=Audit.objects.filter(archived=False).select_related('organization')
    if getattr(request,'tenant',None):audits=audits.filter(organization=request.tenant)
    if not request.user.is_superuser:audits=audits.filter(membership__user=request.user)
    return audits

def scope(request,audit_id=None):
    audits=accessible_audits(request)
    selected=audit_id or request.GET.get('audit')
    if selected:
        try:selected=int(selected)
        except (TypeError,ValueError):raise Http404
        audit=get_object_or_404(audits,pk=selected)
        request.session['selected_audit']=audit.pk
    else:
        audit=audits.filter(pk=request.session.get('selected_audit')).first() or audits.order_by('pk').first()
    if not audit:return None,None,False
    preview=request.user.is_superuser and request.session.get('view_as','admin')!='admin'
    request.auditor_readonly=False
    if request.user.is_superuser:
        role=request.session.get('view_as','admin')
    else:
        membership=Membership.objects.get(user=request.user,audit=audit)
        role=membership.role
        if role=='intern' and membership.auditor_readonly:
            request.auditor_readonly=True
            role='auditor'
            preview=True
    if role not in dict(ROLES):raise Http404
    return audit,role,preview

def demo_write(request,audit):
    return bool(settings.DEBUG and audit and audit.is_demo and request.user.is_superuser)

def shared(request,audit,role,preview):
    from .branding import organization_brand,it_label
    label=it_label(audit) if audit else 'BT Sorumlusu'
    return {**organization_brand(audit.organization if audit else None),'audit':audit,'audit_choices':accessible_audits(request),'it_label':label,'role':role,'role_label':'Stajyer · Denetçi görünümü (salt okunur)' if getattr(request,'auditor_readonly',False) else (label if role=='it' else dict(ROLES).get(role,'')),'preview':preview,'roles':ROLES,'is_platform_admin':request.user.is_superuser,'demo_writable':demo_write(request,audit),'auditor_readonly':getattr(request,'auditor_readonly',False),'can_evaluate':role in ('admin','auditor') and not getattr(request,'auditor_readonly',False),'show_auditor_data':role in ('admin','auditor'),'show_evaluation':role in ('admin','auditor','executive'),'phase_order':[('responses','BT yanıtları'),('fieldwork','Saha denetimi'),('remediation','Bulgu giderme'),('completed','Sürekli kontrol')]}

def evaluation_form(control):
    ev=Evaluation.objects.filter(control=control).first()
    finding=Finding.objects.filter(control=control).first()
    initial={'assessment':ev.assessment,'deficiency':ev.deficiency,'rationale':ev.rationale,'private_note':ev.private_note,'verified':ev.verified} if ev else {}
    if finding:initial.update(recommendation=finding.recommendation,due_date=finding.due_date)
    return EvaluationForm(initial=initial,auto_id=f'evaluation_{control.pk}_%s')

def visible_controls(audit,role):
    qs=Control.objects.filter(audit=audit)
    return qs.filter(intern_visible=True) if role=='intern' else qs

def serialize_control(control,role):
    # Intern paths stop before querying any responses or evaluations.
    data={'id':control.pk,'code':control.code,'title':control.title,'description':control.description,'evidence_guidance':control.evidence_guidance,'framework':control.framework,'theme':control.theme,'risk':control.risk,'risk_label':control.get_risk_display()}
    if role=='intern':return data
    revision=ResponseRevision.objects.filter(control=control).select_related('actor').first()
    data.update(status=revision.status if revision else 'unanswered',status_label=revision.get_status_display() if revision else 'Başlanmadı',response=revision)
    data['evaluation']=None
    if role=='it':return data
    evaluations=Evaluation.objects.filter(control=control)
    evaluation=evaluations.values('assessment','rationale','verified','deficiency').first()
    if evaluation:
        from .models import DEFICIENCIES
        evaluation['deficiency_label']=dict(DEFICIENCIES).get(evaluation['deficiency'],'')
        evaluation['label']=dict(Evaluation._meta.get_field('assessment').choices)[evaluation['assessment']
        ]
        if role in ('admin','auditor'):evaluation['private_note']=evaluations.values_list('private_note',flat=True).first()
    data['evaluation']=evaluation
    return data

@ready
def console(request):
    audit,role,preview=scope(request)
    if not audit:return render(request,'workspace/empty.html',{'is_platform_admin':request.user.is_superuser},status=200)
    ctx=shared(request,audit,role,preview)
    controls=visible_controls(audit,role)
    if ctx['can_evaluate']:
        ctx['add_controls_form']=AddControlsForm()
        ctx['add_controls_form'].fields['controls'].queryset=ControlDefinition.objects.exclude(audit_controls__audit=audit)
    all_rows=[serialize_control(c,role) for c in controls]
    q=request.GET.get('q','').strip()[:100]
    framework=request.GET.get('framework','')
    rows=[r for r in all_rows if (not q or q.casefold() in (r['title']+' '+r['code']).casefold()) and (not framework or r['framework']==framework)]
    for row in rows:
        row['answer_form']=ResponseForm(initial={'status':row.get('status') if row.get('status')!='unanswered' else 'implemented','explanation':row['response'].explanation if row.get('response') else ''},auto_id=f"answer_{row['id']}_%s")
        if role in ('admin','auditor'):row['evaluation_form']=evaluation_form(controls.get(pk=row['id']))
        row['can_answer']=role=='it'
    ctx.update(rows=rows,total=len(all_rows),q=q,framework=framework,frameworks=sorted({r['framework'] for r in all_rows}),appointment_form=AppointmentForm(),suggestion_form=SuggestionForm())
    if role in ('intern','admin','auditor'):
        suggestions=Suggestion.objects.filter(audit=audit)
        if role=='intern' and not demo_write(request,audit):suggestions=suggestions.filter(author=request.user)
        ctx['suggestions']=suggestions.select_related('author')
    if role in ('admin','auditor'):ctx['activities']=Activity.objects.filter(audit=audit).select_related('actor')[:12]
    if role!='intern':
        answered=sum(r['status']!='unanswered' for r in all_rows)
        compliant=sum(bool(r['evaluation'] and r['evaluation']['assessment']=='compliant') for r in all_rows)
        findings=Finding.objects.filter(audit=audit).prefetch_related('updates__actor').select_related('control')
        if role not in ('admin','auditor'):findings=findings.filter(customer_visible=True)
        ctx.update(answered=answered,unanswered=len(all_rows)-answered,completion=round(answered/len(all_rows)*100) if all_rows else 0,compliant=compliant,findings=list(findings),finding_count=findings.exclude(status__in=['closed','risk_accepted']).count(),response_form=ResponseForm(),ready_for_fieldwork=bool(all_rows))
    # Chart payload is assembled from the same permission-filtered records as the page.
    risk_counts=Counter(r['risk'] for r in all_rows)
    framework_counts=Counter(r['framework'] for r in all_rows)
    charts={'risks':{'labels':['Yüksek','Orta','Düşük'],'values':[risk_counts[k] for k in ['high','medium','low']]},'frameworks':{'labels':list(framework_counts),'values':list(framework_counts.values())}}
    ctx['risk_legend']=[{'label':label,'count':risk_counts[key],'key':key} for key,label in [('high','Yüksek'),('medium','Orta'),('low','Düşük')]]
    if role!='intern':
        statuses=Counter(r['status'] for r in all_rows)
        charts['responses']={'labels':[label for _,label in STATUSES],'values':[statuses[key] for key,_ in STATUSES]}
        ctx['response_legend']=[{'key':key,'label':label,'count':statuses[key]} for key,label in STATUSES]
        finding_states=Counter(f.status for f in ctx['findings'])
        ctx['closed_findings']=finding_states['closed']
        ctx['accepted_risks']=finding_states['risk_accepted']
        if role in ('admin','auditor','executive'):
            evaluations=Counter(r['evaluation']['assessment'] if r.get('evaluation') else 'pending' for r in all_rows)
            labels=[('compliant','Uygun'),('partial','Kısmen uygun'),('noncompliant','Uygun değil'),('pending','Değerlendirilmedi')]
            charts['evaluations']={'labels':[label for _,label in labels],'values':[evaluations[key] for key,_ in labels]}
            ctx['evaluation_legend']=[{'key':key,'label':label,'count':evaluations[key]} for key,label in labels]
            ctx['reviewed']=len(all_rows)-evaluations['pending']
    ctx['charts']=charts
    return render(request,'workspace/console.html',ctx)

@ready
@require_POST
def view_as(request):
    if not request.user.is_superuser:return HttpResponseForbidden('Bu işlem yalnızca platform yöneticisine açıktır.')
    role=request.POST.get('role')
    if role not in dict(ROLES):return HttpResponseBadRequest('Geçersiz rol.')
    request.session['view_as']=role
    target=request.POST.get('next','')
    if target.startswith('/console/'):
        try:
            match=resolve(target)
            if match.url_name in ('control_detail','control_history'):
                audit,active_role,_=scope(request,match.kwargs['audit_id'])
                allowed=visible_controls(audit,active_role).filter(pk=match.kwargs['control_id']).exists()
                if allowed:
                    destination='control_detail' if active_role=='intern' else match.url_name
                    return redirect(destination,**match.kwargs)
        except (Resolver404,Http404):
            pass
    return redirect('console')

@ready
def detail(request,audit_id,control_id):
    audit,role,preview=scope(request,audit_id)
    control=get_object_or_404(visible_controls(audit,role),pk=control_id)
    row=serialize_control(control,role)
    form=ResponseForm(request.POST or None)
    if request.method=='POST':
        if form.is_valid():
            try:services.answer(audit,control,request.user,role,form.cleaned_data,preview,demo_write(request,audit))
            except ValidationError as error:form.add_error(None,error)
            else:
                messages.success(request,'BT sorumlusu yanıtı kaydedildi.')
                return redirect('control_detail',audit_id=audit.pk,control_id=control.pk)
        elif role!='it':return HttpResponseForbidden('Bu rolde yanıt kaydedilemez.')
    if request.method=='GET' and row.get('response'):
        form=ResponseForm(initial={'status':row['response'].status,'explanation':row['response'].explanation})
    ctx=shared(request,audit,role,preview)
    can_answer=role=='it'
    ctx.update(control=row,form=form,can_answer=can_answer)
    if role in ('admin','auditor'):ctx['evaluation_form']=evaluation_form(control)
    return render(request,'workspace/detail.html',ctx)

@ready
def history(request,audit_id,control_id):
    audit,role,preview=scope(request,audit_id)
    if role=='intern':raise Http404
    control=get_object_or_404(visible_controls(audit,role),pk=control_id)
    ctx=shared(request,audit,role,preview)
    ctx.update(control=serialize_control(control,role),revisions=ResponseRevision.objects.filter(control=control).select_related('actor'))
    return render(request,'workspace/history.html',ctx)


@ready
@require_POST
def workflow(request,audit_id):
    audit,role,preview=scope(request,audit_id)
    if getattr(request,'auditor_readonly',False):return HttpResponseForbidden('Stajyer denetçi görünümü salt okunurdur.')
    action=request.POST.get('action','')
    writable=demo_write(request,audit)
    try:
        if action=='add_controls':
            services.allowed(role,['admin','auditor'],preview,writable)
            form=AddControlsForm(request.POST)
            if not form.is_valid():return form_failure(request,audit,role,preview,form,action)
            with transaction.atomic():
                added=services.add_catalog_controls(audit,form.cleaned_data['controls'])
                services.log(audit,request.user,role,'Katalogdan kontrol eklendi',controls=[c.code for c in added])
        elif action=='answer':
            control=get_object_or_404(visible_controls(audit,role),pk=request.POST.get('control'))
            form=ResponseForm(request.POST)
            if not form.is_valid():return form_failure(request,audit,role,preview,form,action,control.pk)
            services.answer(audit,control,request.user,role,form.cleaned_data,preview,writable)
        elif action=='evaluate':
            services.allowed(role,['admin','auditor'],preview,writable)
            control=get_object_or_404(Control,audit=audit,pk=request.POST.get('control'))
            form=EvaluationForm(request.POST)
            if not form.is_valid():return form_failure(request,audit,role,preview,form,action,control.pk)
            services.evaluate(audit,control,request.user,role,form.cleaned_data,preview,writable)
        elif action=='phase':services.transition(audit,request.user,role,request.POST.get('target'),preview,writable)
        elif action in ['appointment','confirm_appointment']:
            services.allowed(role,['admin','auditor','it'],preview,writable)
            with transaction.atomic():
                audit=Audit.objects.select_for_update().get(pk=audit.pk)
                if audit.phase!='fieldwork':raise ValidationError('Randevu yalnızca saha denetimi fazında planlanabilir.')
                if action=='confirm_appointment':
                    expected='proposed' if role=='it' else 'counter'
                    if audit.appointment_status!=expected or not audit.appointment_at or audit.appointment_at<=timezone.now():raise ValidationError('Karşı taraftan gelen geçerli bir randevu önerisi yok.')
                    audit.appointment_status='confirmed'
                else:
                    form=AppointmentForm(request.POST)
                    if not form.is_valid():return form_failure(request,audit,role,preview,form,action)
                    audit.appointment_at=form.cleaned_data['when'];audit.appointment_note=form.cleaned_data['note']
                    audit.appointment_status='counter' if role=='it' else 'proposed'
                audit.save()
                services.log(audit,request.user,role,'Saha randevusu güncellendi',status=audit.appointment_status,when=audit.appointment_at.isoformat(),note=audit.appointment_note)
        elif action=='suggest':
            services.allowed(role,['intern'],preview,writable)
            form=SuggestionForm(request.POST)
            if not form.is_valid():return form_failure(request,audit,role,preview,form,action)
            suggestion=form.save(commit=False);suggestion.audit=audit;suggestion.author=request.user;suggestion.save()
            services.log(audit,request.user,role,'Kontrol önerildi',suggestion=suggestion.pk)
        elif action=='review_suggestion':
            suggestion=get_object_or_404(Suggestion,audit=audit,pk=request.POST.get('suggestion'))
            note=request.POST.get('note','').strip()[:2000]
            if not note:raise ValidationError('İnceleme notu gereklidir.')
            services.review_suggestion(audit,suggestion,request.user,role,request.POST.get('decision'),note,preview,writable)
        elif action=='finding':
            if role=='intern':raise Http404
            findings=Finding.objects.filter(audit=audit)
            if role not in ['admin','auditor']:findings=findings.filter(customer_visible=True)
            finding=get_object_or_404(findings,pk=request.POST.get('finding'))
            data=request.POST.copy();data['action']=request.POST.get('finding_action','')
            form=FindingForm(data)
            if not form.is_valid():return form_failure(request,audit,role,preview,form,action,finding=finding.pk)
            services.finding_action(audit,finding,request.user,role,form.cleaned_data['action'],form.cleaned_data['explanation'],preview,writable,due_date=form.cleaned_data.get('due_date'))
        else:return HttpResponseBadRequest('Geçersiz işlem.')
    except ValidationError as error:
        messages.error(request,' '.join(error.messages));return redirect('console')
    messages.success(request,'İşlem kaydedildi.')
    anchor={'answer':'controls','evaluate':'controls','finding':'findings','suggest':'suggestions','review_suggestion':'suggestions','appointment':'phases','confirm_appointment':'phases','phase':'phases'}.get(action,'')
    return redirect(reverse('console')+'#'+anchor)

def form_failure(request,audit,role,preview,form,action,control=None,finding=None):
    ctx=shared(request,audit,role,preview)
    ctx.update(form=form,action=action,control_id=control,finding_id=finding)
    return render(request,'workspace/form_error.html',ctx,status=400)

@ready
def findings_pdf(request,audit_id):
    audit,role,preview=scope(request,audit_id)
    if role=='intern':raise Http404
    findings=Finding.objects.filter(audit=audit).select_related('control').prefetch_related('updates__actor')
    if role not in ['admin','auditor']:findings=findings.filter(customer_visible=True)
    from .pdf import render_findings
    content=render_findings(audit,list(findings))
    services.log(audit,request.user,role,'Bulgular PDF indirildi',count=findings.count())
    response=HttpResponse(content,content_type='application/pdf')
    response['Content-Disposition']=f'attachment; filename="{audit.organization.slug}-bulgular-{audit.pk}.pdf"'
    return response


@ready
def controls_pdf(request,audit_id):
    audit,role,preview=scope(request,audit_id)
    rows=[serialize_control(control,role) for control in visible_controls(audit,role)]
    from .pdf import render_controls
    content=render_controls(audit,rows,role)
    services.log(audit,request.user,role,'Kontroller PDF indirildi',count=len(rows))
    response=HttpResponse(content,content_type='application/pdf')
    response['Content-Disposition']=f'attachment; filename="{audit.organization.slug}-kontroller-{audit.pk}.pdf"'
    return response
