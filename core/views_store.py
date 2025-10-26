# core/views_store.py
from __future__ import annotations
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, FileResponse, Http404, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.urls import reverse
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.signing import Signer, BadSignature
from django.utils import timezone

from .models import DigitalProduct, PurchaseIntent
from .utils.pdf_utils import personalize_pdf, build_watermark_text

import io

def product_list_view(request):
    products = DigitalProduct.objects.filter(is_active=True)
    return render(request, "course-category.html", {"products": products})

def product_detail_json(request, slug):
    p = get_object_or_404(DigitalProduct, slug=slug, is_active=True)
    data = {
        "title": p.title,
        "description": p.description,
        "difficulty": p.difficulty,
        "duration": p.duration,
        "rating": float(p.rating),
        "reviews": p.reviews_count,
        "price_display": p.price_display(),
        "currency": p.currency,
        "ruul_pay_link": p.ruul_pay_link,
        "uploader_name": p.uploader_name,
        "image_url": p.image.url if p.image else "",
    }
    return JsonResponse({"ok": True, "product": data})

@require_POST
@csrf_protect
def create_purchase_intent(request, slug):
    p = get_object_or_404(DigitalProduct, slug=slug, is_active=True)
    email = request.POST.get("email", "").strip().lower()
    if not email:
        return JsonResponse({"ok": False, "error": "E-posta gerekli."}, status=400)
    pi = PurchaseIntent.objects.create(product=p, email=email)
    # Not: Ruul.io webhook doğrulaması geldiğinde pi.is_paid = True yap.
    success_url = request.build_absolute_uri(
        reverse("purchase_success", kwargs={"token": str(pi.token)})
    )
    # Kullanıcıyı Ruul.io'ya yönlendireceğiz; modal içinde yeni sekmede açtıracağız.
    return JsonResponse({"ok": True, "pay_url": p.ruul_pay_link, "success_url": success_url})

def purchase_success(request, token):
    """
    Demo akış: webhook yoksa kullanıcı 'Ödemeyi tamamladım' diyerek gelir.
    Üretimi burada yapıyoruz. Üretimden önce gerçekte is_paid kontrolü gerekir.
    """
    try:
        pi = PurchaseIntent.objects.get(token=token)
    except PurchaseIntent.DoesNotExist:
        raise Http404("Geçersiz işlem")

    product = pi.product
    if not product.source_pdf:
        return HttpResponseBadRequest("Kaynak PDF yok.")

    # !!! GERÇEKTE: Ruul webhook ile ödeme doğrulanmalı
    # if not pi.is_paid:
    #     return HttpResponseBadRequest("Ödeme doğrulanmadı.")

    email = pi.email
    watermark_text = build_watermark_text(email=email)
    password = product.license_password

    # Kişiselleştirilmiş PDF'i RAM'de üret
    mem_out = io.BytesIO()
    personalize_pdf(product.source_pdf.open("rb"), mem_out, watermark_text, password)
    mem_out.seek(0)

    # İndirme
    filename = f"{product.slug}-licensed-{timezone.now().strftime('%Y%m%d%H%M')}.pdf"
    response = FileResponse(mem_out, as_attachment=True, filename=filename, content_type="application/pdf")
    return response
