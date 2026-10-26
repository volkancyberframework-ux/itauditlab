"""Route only authenticated owner commands to the independent Siberkobi service."""
import hashlib
import hmac
import time
import requests
from django.conf import settings
from django.http import JsonResponse

DESTINATION='https://siberkobi.co/integrations/telegram/siberkobi/relay/'

def forward(request,payload):
    callback=payload.get('callback_query') or {}
    message=callback.get('message') or payload.get('message') or {}
    text=str(message.get('text') or '').strip()
    prefix=text.split(None,1)[0].casefold().lstrip('/') if text else ''
    if prefix!='siberkobi' and not str(callback.get('data') or '').startswith('sk:'):return None
    secret=getattr(settings,'GRCUSTASI_TELEGRAM_WEBHOOK_SECRET','') or getattr(settings,'TELEGRAM_WEBHOOK_SECRET','')
    if not secret or not hmac.compare_digest(request.headers.get('X-Telegram-Bot-Api-Secret-Token',''),secret):return JsonResponse({'ok':False},status=403)
    if len(request.body)>65536:return JsonResponse({'ok':False},status=413)
    owner=str(getattr(settings,'GRCUSTASI_TELEGRAM_ADMIN_CHAT_ID','') or getattr(settings,'TELEGRAM_ADMIN_CHAT_ID','') or getattr(settings,'TELEGRAM_CHAT_ID',''))
    actor=callback.get('from') or message.get('from') or {};chat=message.get('chat') or {}
    if not owner or chat.get('type')!='private' or type(actor.get('id')) is not int or actor.get('id')!=chat.get('id') or not hmac.compare_digest(str(actor['id']),owner):return JsonResponse({'ok':True})
    token=getattr(settings,'GRCUSTASI_TELEGRAM_BOT_TOKEN','') or getattr(settings,'TELEGRAM_BOT_TOKEN','')
    if not token:return JsonResponse({'ok':False},status=503)
    stamp=str(int(time.time()))
    signature=hmac.new(token.encode(),b'siberkobi-relay-v1\n'+stamp.encode()+b'\n'+request.body,hashlib.sha256).hexdigest()
    try:
        response=requests.post(DESTINATION,data=request.body,headers={'Content-Type':'application/json','X-Siberkobi-Relay-Timestamp':stamp,'X-Siberkobi-Relay-Signature':signature},timeout=8,allow_redirects=False)
        if response.status_code!=200:return JsonResponse({'ok':False},status=503)
    except requests.RequestException:return JsonResponse({'ok':False},status=503)
    return JsonResponse({'ok':True})
