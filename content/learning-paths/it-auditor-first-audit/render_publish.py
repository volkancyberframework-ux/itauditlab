# NEXORA: 10 reviewed cases + 1 learning card. User authorized publication.
# Run inside: python manage.py shell
import base64, gzip, hashlib, json
from copy import deepcopy
from django.db import transaction
from django.db.models import Max
from mobile_api.models import LearningPath, Module, Question, UserPathProgress, LearningSession, QuestionAttempt, XPTransaction

TARGET_PATH_ID = 16
EXPECTED_TITLE = "🕵️ IT Auditor: İlk Denetimin"
REGISTRY_KEY = "nexora_first_audit_publication_v1"
PAYLOAD_SHA256 = "aa2326156957714783f0c14cf15886e879bb10227e30114ec3489c19cf4d5313"
PAYLOAD_B64 = (
    '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'
)

raw = gzip.decompress(base64.b64decode(PAYLOAD_B64))
if hashlib.sha256(raw).hexdigest() != PAYLOAD_SHA256:
    raise RuntimeError("Komut içeriği bozulmuş; hiçbir kayıt yazılmadı.")
records = json.loads(raw.decode("utf-8"))
if len(records) != 11 or sum(r["fields"]["kind"] == "info" for r in records) != 1:
    raise RuntimeError("Paket 10 soru ve 1 kart içermeli.")
if len({r["content_id"] for r in records}) != 11:
    raise RuntimeError("Paket ID'leri benzersiz değil.")
if [r["fields"]["order"] for r in records] != [10,20,30,40,50,60,70,80,90,100,101]:
    raise RuntimeError("Paket sıralaması geçersiz.")
allowed = {"kind","prompt","context","options","answer","explanation","difficulty","goals","base_xp","order","card_pages","published","in_workshop"}
model_names = {f.name for f in Question._meta.get_fields()}
if not allowed <= model_names:
    raise RuntimeError("Canlı Question şeması gerekli alanları desteklemiyor.")
for r in records:
    f = r["fields"]
    if set(f) - allowed or f["published"] is not True or f["in_workshop"] is not False:
        raise RuntimeError("Paket alanları/yayın durumu geçersiz.")
    if f["kind"] != "info":
        if not 250 <= len(f["context"].split()) <= 700:
            raise RuntimeError("Senaryo uzunluğu geçersiz.")
        keys = {o["id"] for o in f["options"]}
        if not f["answer"] or not set(f["answer"]) <= keys:
            raise RuntimeError("Cevap anahtarı seçeneklerle uyumsuz.")
        if not f["explanation"]:
            raise RuntimeError("Cevap açıklaması eksik.")
    else:
        pages = f.get("card_pages", [])
        if not pages or not 300 <= sum(len(p["body"].split()) for p in pages) <= 500:
            raise RuntimeError("Öğrenme kartı geçersiz.")

def fingerprint(r):
    return hashlib.sha256(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")).hexdigest()

def user_state(path):
    # Counts only: no private user information is printed or exported.
    progress = UserPathProgress.objects.filter(path=path)
    completion_links = UserPathProgress.completed.through.objects.filter(userpathprogress__path=path).count()
    return (progress.count(), completion_links,
            LearningSession.objects.filter(path=path).count(),
            QuestionAttempt.objects.filter(session__path=path).count(),
            XPTransaction.objects.filter(attempt__session__path=path).count())

created = []
reused = []
with transaction.atomic():
    path = LearningPath.objects.select_for_update().get(pk=TARGET_PATH_ID, owner=None)
    if path.title != EXPECTED_TITLE:
        raise RuntimeError("Hedef yol ID/başlık eşleşmiyor; işlem durduruldu: " + path.title)
    before = user_state(path)
    preferences = deepcopy(path.preferences or {})
    registry = deepcopy(preferences.get(REGISTRY_KEY, {}))
    existing_questions = list(path.questions.select_for_update().order_by("order","id"))
    by_pk = {q.pk:q for q in existing_questions}
    mappings = registry.get("records", {})
    if registry and registry.get("package_sha256") != PAYLOAD_SHA256:
        raise RuntimeError("Bu yol için farklı bir paket daha önce aktarılmış; üzerine yazılmadı.")
    if registry:
        base_order = registry["base_order"]
    else:
        # Adopt exact manual imports, if any; otherwise append after all existing items.
        manual_bases = []
        for r in records:
            matches = [q for q in existing_questions if q.prompt == r["fields"]["prompt"]]
            if len(matches) > 1:
                raise RuntimeError("Aynı başlıkla birden fazla kayıt var; otomatik çoğaltma engellendi.")
            if matches:
                q = matches[0]
                if q.context != r["fields"].get("context", ""):
                    raise RuntimeError("Başlığı eşleşen farklı bir soru var; mevcut kayıt değiştirilmedi.")
                manual_bases.append(q.order-r["fields"]["order"])
        if manual_bases:
            if len(set(manual_bases)) != 1 or manual_bases[0] < 0:
                raise RuntimeError("Elle eklenen kayıtların sırası uyumsuz; sıralama değiştirilmedi.")
            base_order = manual_bases[0]
        else:
            base_order = max((q.order for q in existing_questions),default=0)
    module, _ = Module.objects.get_or_create(
        path=path, title="NEXORA • Bölüm 1: İlk gün ve denetim kapsamı", order=1)
    for r in records:
        content_id = r["content_id"]
        fields = deepcopy(r["fields"])
        fields["order"] = base_order + fields["order"]
        stored = mappings.get(content_id)
        if stored:
            if stored.get("digest") != fingerprint(r) or stored["pk"] not in by_pk:
                raise RuntimeError(content_id + ": eşleştirme veya paket değişmiş; üzerine yazılmadı.")
            q = by_pk[stored["pk"]]
        else:
            candidates = [q for q in existing_questions if q.prompt == fields["prompt"]]
            q = candidates[0] if candidates else None
        if q is not None:
            if any(getattr(q,key) != value for key,value in fields.items()):
                raise RuntimeError(content_id + ": mevcut alanlar farklı; üzerine yazılmadı.")
            if q.answer_options.exists():
                raise RuntimeError(content_id + ": cevapları değiştiren inline seçenekler var.")
            if q.module_id != module.pk:
                raise RuntimeError(content_id + ": modül ilişkisi farklı; üzerine yazılmadı.")
            reused.append(content_id)
        else:
            if any(old.order == fields["order"] for old in existing_questions):
                raise RuntimeError(content_id + ": mevcut kayıtla sıra çakışıyor; hiçbir kayıt taşınmadı.")
            q = Question(module=module, **fields)
            q.full_clean()
            q.save()
            q.paths.add(path)
            created.append(content_id)
        mappings[content_id] = {"pk":q.pk,"digest":fingerprint(r),"audio_reference":r.get("audio_reference")}
    preferences[REGISTRY_KEY] = {"package_sha256":PAYLOAD_SHA256,"base_order":base_order,"records":mappings}
    path.preferences = preferences
    path.published = True
    path.full_clean()
    path.save(update_fields=["preferences","published"])
    after = user_state(path)
    if before != after:
        raise RuntimeError("Kullanıcı ilerleme/deneme/puan kaydı sayıları değişti; transaction geri alındı.")
    imported = path.questions.filter(pk__in=[m["pk"] for m in mappings.values()])
    if imported.count() != 11 or imported.filter(published=True,in_workshop=False).count() != 11:
        raise RuntimeError("Yayın/ilişki doğrulaması başarısız; transaction geri alındı.")
    if imported.filter(kind="audio",audio__isnull=False).exists() and created:
        raise RuntimeError("Yeni ses sorusunda beklenmeyen ses dosyası var.")

print("YAYIN TAMAMLANDI:", path.title, "| path_id=", path.pk)
print("Paket: 10 soru + 1 öğrenme kartı. Yeni:",len(created),"Tekrar kullanılan:",len(reused))
print("Kullanıcı ilerleme/deneme/puan kayıtları korundu. Ses dosyası oluşturulmadı.")
print("Toplam yayınlanmış soru:",path.questions.filter(published=True).exclude(kind="info").count())
print("Toplam yayınlanmış kart:",path.questions.filter(published=True,kind="info").count())
print("EŞLEŞTİRME:",json.dumps({key:value["pk"] for key,value in mappings.items()},ensure_ascii=False,sort_keys=True))
print("Bu paket 100 vakalık öğrenme yolunun yalnız ilk 10 vakasını içerir.")
