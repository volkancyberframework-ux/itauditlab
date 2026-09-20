from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
import reportlab
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from django.conf import settings
from django.utils import timezone
from .branding import pdf_logo,it_label

def render_findings(audit,findings):
    fonts=Path(reportlab.__file__).parent/'fonts'
    for name,file in [('GRC','Vera.ttf'),('GRC-Bold','VeraBd.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont(name,str(fonts/file)))
    pdfmetrics.registerFontFamily('GRC',normal='GRC',bold='GRC-Bold')
    out=BytesIO()
    doc=SimpleDocTemplate(out,pagesize=A4,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=48,title=f'{audit.organization.name} - Denetim Bulguları',author=audit.organization.name)
    body=ParagraphStyle('body',fontName='GRC',fontSize=9,leading=14,textColor=colors.HexColor('#243b50'),spaceAfter=8,wordWrap='CJK')
    heading=ParagraphStyle('heading',parent=body,fontName='GRC-Bold',fontSize=14,leading=20,spaceAfter=12)
    small=ParagraphStyle('small',parent=body,fontSize=8,leading=12,textColor=colors.HexColor('#60788c'))
    def para(text,style=body):return Paragraph(escape(str(text)).replace('\n','<br/>'),style)
    source=pdf_logo(audit.organization)
    logo=Image(source) if source else para(audit.organization.name,heading)
    if source:
        ratio=min(180/logo.imageWidth,90/logo.imageHeight)
        logo.drawWidth=logo.imageWidth*ratio;logo.drawHeight=logo.imageHeight*ratio
    header=Table([[logo,para('Denetim Bulguları',heading)]],colWidths=[206,305]);header.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),0)]))
    story=[header,Spacer(1,16),para(audit.organization.name,heading),para(audit.title),para(f"Oluşturulma: {timezone.localtime():%d.%m.%Y %H:%M} (İstanbul) | Faz: {audit.get_phase_display()}",small),para(f'Toplam bulgu: {len(findings)} | Açık: {sum(not f.is_terminal for f in findings)}',body)]
    if audit.is_demo:story.append(para('DEMO RAPORU - Kurum ve denetim kayıtları örnek veridir.',small))
    story.append(Spacer(1,16))
    if not findings:story.append(para('Bu erişim kapsamında henüz bulgu bulunmuyor.'))
    for index,finding in enumerate(findings,1):
        story.append(KeepTogether([para(f'{index:02d}. {finding.title}',heading),para(f'{finding.control.code if finding.control else "Genel"} | Risk: {finding.get_severity_display()} | Durum: {finding.get_status_display()}',small)]))
        story.append(para(f'Karar: {finding.get_treatment_display()} | Son tarih: {finding.due_date:%d.%m.%Y}',small))
        story.extend([para('Giderim önerisi',ParagraphStyle('bold',parent=body,fontName='GRC-Bold')),para(finding.recommendation)])
        updates=list(finding.updates.all())
        if updates:
            for update_index,update in enumerate(reversed(updates)):
                prefix=[para('İtiraz ve giderim geçmişi',ParagraphStyle('bold2',parent=body,fontName='GRC-Bold'))] if update_index==0 else []
                story.append(KeepTogether(prefix+[para(f'{timezone.localtime(update.created_at):%d.%m.%Y %H:%M} | {update.get_action_display()} | {update.actor.get_full_name() or update.actor.email}',small),para(update.explanation)]))
        story.append(Spacer(1,18))
    def footer(canvas,document):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor('#dae3ea'));canvas.line(42,38,A4[0]-42,38);canvas.setFont('GRC',8);canvas.setFillColor(colors.HexColor('#60788c'));canvas.drawString(42,24,audit.organization.name+' | Kuruma özel denetim raporu');canvas.drawRightString(A4[0]-42,24,f'Sayfa {document.page}');canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return out.getvalue()


def render_controls(audit,rows,role):
    # Inputs are already projected for this role: intern rows have no response/evaluation.
    fonts=Path(reportlab.__file__).parent/'fonts'
    for name,file in [('GRC','Vera.ttf'),('GRC-Bold','VeraBd.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont(name,str(fonts/file)))
    pdfmetrics.registerFontFamily('GRC',normal='GRC',bold='GRC-Bold')
    out=BytesIO()
    doc=SimpleDocTemplate(out,pagesize=A4,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=48,title=f'{audit.organization.name} - Denetim Kontrolleri',author=audit.organization.name)
    body=ParagraphStyle('control-body',fontName='GRC',fontSize=9,leading=14,textColor=colors.HexColor('#243b50'),spaceAfter=8,wordWrap='CJK')
    heading=ParagraphStyle('control-heading',parent=body,fontName='GRC-Bold',fontSize=14,leading=20,spaceAfter=12)
    small=ParagraphStyle('control-small',parent=body,fontSize=8,leading=12,textColor=colors.HexColor('#60788c'))
    bold=ParagraphStyle('control-bold',parent=body,fontName='GRC-Bold',keepWithNext=True)
    def para(text,style=body):return Paragraph(escape(str(text)).replace('\n','<br/>'),style)
    source=pdf_logo(audit.organization)
    logo=Image(source) if source else para(audit.organization.name,heading)
    if source:
        ratio=min(180/logo.imageWidth,90/logo.imageHeight)
        logo.drawWidth=logo.imageWidth*ratio;logo.drawHeight=logo.imageHeight*ratio
    header=Table([[logo,para('Denetim Kontrolleri',heading)]],colWidths=[206,305]);header.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),0)]))
    from .models import ROLES
    story=[header,Spacer(1,20),para(audit.organization.name,heading),para(audit.title),para(f"Oluşturulma: {timezone.localtime():%d.%m.%Y %H:%M} (İstanbul) | {audit.get_phase_display()}",small),para(f'Erişim görünümü: {dict(ROLES)[role]} | Kontrol sayısı: {len(rows)}',small)]
    if audit.is_demo:story.append(para('DEMO RAPORU - Kontroller örnek sorulardır; resmî standart metni değildir.',small))
    story.append(Spacer(1,16))
    if not rows:story.append(para('Bu erişim kapsamında kontrol bulunmuyor.'))
    for row in rows:
        story.append(KeepTogether([para(f"{row['code']} | {row['title']}",heading),para(f"{row['framework']} | {row['theme']} | Risk: {row['risk_label']}",small)]))
        story.extend([para('Kontrol sorusu',bold),para(row['description']),para('Test rehberi / beklenen kanıt',bold),para(row['evidence_guidance'])])
        if role!='intern':
            response=row.get('response')
            story.append(KeepTogether([para(it_label(audit)+' yanıtı',bold),para(row['status_label'])]))
            if response:
                story.extend([para(response.explanation),para(f"{response.actor.get_full_name() or response.actor.email} | {timezone.localtime(response.created_at):%d.%m.%Y %H:%M}",small)])
            if role in ('admin','auditor','executive'):
                ev=row.get('evaluation')
                story.append(KeepTogether([para('Denetçi görüşü',bold),para(ev['label'] if ev else 'Değerlendirilmedi')]))
                if ev:
                    story.append(para(ev['rationale']))
                    if ev.get('deficiency_label'):story.append(para('Eksiklik: '+ev['deficiency_label']))
                    story.append(para('Test edildi · Son onay' if ev.get('verified') else 'Son test onayı bekliyor',small))
        # Internal private notes intentionally never appear in downloadable controls reports.
        story.append(Spacer(1,18))
    def footer(canvas,document):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor('#dae3ea'));canvas.line(42,38,A4[0]-42,38);canvas.setFont('GRC',8);canvas.setFillColor(colors.HexColor('#60788c'));canvas.drawString(42,24,audit.organization.name+' | Denetim kontrolleri');canvas.drawRightString(A4[0]-42,24,f'Sayfa {document.page}');canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return out.getvalue()
