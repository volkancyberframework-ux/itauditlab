import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'interactive_questions.dart';
import 'theme.dart';
import 'api.dart';

class PracticeCase {
  final String id, title, situation, controlReason, evidenceReason;
  final List<String> sentence, controls, evidence;
  final int control, proof, likelihood, impact;
  const PracticeCase({
    required this.id,
    required this.title,
    required this.situation,
    required this.sentence,
    required this.controls,
    required this.control,
    required this.controlReason,
    required this.evidence,
    required this.proof,
    required this.evidenceReason,
    required this.likelihood,
    required this.impact,
  });

  factory PracticeCase.fromJson(Map<String, dynamic> json) => PracticeCase(
    id: json['id'] as String,
    title: json['title'] as String,
    situation: json['situation'] as String,
    sentence: List<String>.from(json['sentence']),
    controls: List<String>.from(json['controls']),
    control: json['control'] as int,
    controlReason: json['controlReason'] as String,
    evidence: List<String>.from(json['evidence']),
    proof: json['proof'] as int,
    evidenceReason: json['evidenceReason'] as String,
    likelihood: json['likelihood'] as int,
    impact: json['impact'] as int,
  );
}

const practiceCases = [
  PracticeCase(
    id: 'leaver',
    title: 'Ayrılan çalışanın erişimi',
    situation:
        'Finans ekibinden ayrılan bir çalışanın hesabı üç haftadır aktif. Hesap müşteri verilerini dışa aktarabiliyor. İnsan kaynakları ile BT arasında otomatik bildirim yok.',
    sentence: [
      'İşten ayrılan çalışanın erişiminin kapatılmaması nedeniyle',
      'müşteri verilerine yetkisiz erişim gerçekleşebilir',
      've veri ihlali ile yasal yaptırım oluşabilir.',
    ],
    controls: [
      'Tüm çalışanlara aynı parola vermek',
      'İK ayrılış bildirimiyle erişimi kapatıp tamamlanmasını kontrol etmek',
      'Yalnızca yılda bir güvenlik sunumu yapmak',
    ],
    control: 1,
    controlReason:
        'Kontrol, riskin kaynağına müdahale eder. Ayrılış bildirimi, süre hedefi ve kapatma kanıtı birlikte izlenmelidir.',
    evidence: [
      'Bilgi güvenliği politikasının kapağı',
      'BT yöneticisinin sözlü onayı',
      'İK ayrılış listesiyle hesap kapatma kayıtlarının tarihli karşılaştırması',
    ],
    proof: 2,
    evidenceReason:
        'Politika niyeti gösterir; tarihli kayıtların karşılaştırılması kontrolün gerçekten ve zamanında işlediğini gösterir.',
    likelihood: 4,
    impact: 5,
  ),
  PracticeCase(
    id: 'backup',
    title: 'Yedek var; geri dönüş var mı?',
    situation:
        'Hastanenin hasta kayıtları her gece yedekleniyor. Son altı ayda geri yükleme hiç denenmemiş. Fidye yazılımı ana sunucuya bulaştığında yedeklerin çalışacağı varsayılıyor.',
    sentence: [
      'Yedeklerin geri yüklenebilirliği test edilmediği için',
      'bir kesintide hasta kayıtları geri getirilemeyebilir',
      've sağlık hizmeti durabilir.',
    ],
    controls: [
      'Yedek raporunun ekran görüntüsünü saklamak',
      'Sunucuları yeniden adlandırmak',
      'Düzenli geri yükleme denemesi yapıp sonuç ve kurtarma süresini kaydetmek',
    ],
    control: 2,
    controlReason:
        'Başarılı yedekleme ile başarılı kurtarma aynı şey değildir. Geri yükleme denemesi ve süre ölçümü iş sürekliliğini sınar.',
    evidence: [
      'Tarih, kapsam ve sonuç içeren geri yükleme test kaydı',
      'Yedekleme yazılımının satın alma faturası',
      'Sunucu odasının fotoğrafı',
    ],
    proof: 0,
    evidenceReason:
        'Test kaydı, seçilen kayıtların geri alınabildiğini ve hizmetin hedef süre içinde dönebildiğini göstermelidir.',
    likelihood: 3,
    impact: 5,
  ),
  PracticeCase(
    id: 'supplier',
    title: 'Tedarikçi erişiminin sınırları',
    situation:
        'Dış destek şirketi ortak bir yönetici hesabıyla sisteme bağlanıyor. Hesap 7/24 açık; hangi uzmanın hangi değişikliği yaptığı kaydedilmiyor.',
    sentence: [
      'Ortak ve sürekli açık tedarikçi yönetici hesabı nedeniyle',
      'yetkisiz değişiklikler kişiye bağlanamayabilir',
      've hizmet kesintisi ile hesap verebilirlik kaybı oluşabilir.',
    ],
    controls: [
      'Kişiye özel, süreli, onaylı ve çok faktörlü erişim ile işlem kaydı tutmak',
      'Ortak parolayı daha fazla kişiyle paylaşmak',
      'Yalnızca destek sözleşmesini yenilemek',
    ],
    control: 0,
    controlReason:
        'Kimlik, en az yetki, süre sınırı ve izlenebilirlik birlikte ele alınmalıdır. Sözleşme tek başına teknik erişimi kısıtlamaz.',
    evidence: [
      'Tedarikçinin tanıtım sunumu',
      'Onaylı erişim talepleri, kişi bazlı oturum ve değişiklik kayıtları',
      'BT ekibinin organizasyon şeması',
    ],
    proof: 1,
    evidenceReason:
        'Talep, onay, oturum ve yapılan işlem arasında ilişki kurulması kontrolün tasarımını ve işleyişini gösterir.',
    likelihood: 4,
    impact: 4,
  ),
  PracticeCase(
    id: 'invoice',
    title: 'Sahte banka hesabı değişikliği',
    situation:
        'Satın alma ekibine tedarikçi adına bir e-posta geliyor: “IBAN değişti, ödemeyi bugün yapın.” Çalışan, mesajdaki telefon numarasını arayıp onay aldıktan sonra kaydı değiştiriyor.',
    sentence: [
      'Banka hesabı değişikliğinin bağımsız kanaldan doğrulanmaması nedeniyle',
      'ödeme saldırganın hesabına gönderilebilir',
      've finansal kayıp oluşabilir.',
    ],
    controls: [
      'Mesajdaki numarayı tekrar aramak',
      'Ödemeyi hızlandırmak',
      'Önceden kayıtlı iletişim kanalıyla doğrulama ve ikinci kişi onayı almak',
    ],
    control: 2,
    controlReason:
        'Saldırganın verdiği telefon bağımsız doğrulama değildir. Bilinen kayıtlı kanal ve ikinci onay kullanılmalıdır.',
    evidence: [
      'Gönderici imzasındaki logo',
      'Kayıtlı kanal doğrulaması ve iki kişi onayını gösteren değişiklik kaydı',
      'E-postanın acil başlığı',
    ],
    proof: 1,
    evidenceReason:
        'Kanıt, doğrulamanın saldırganın sağladığı bilgilerden bağımsız yapıldığını göstermelidir.',
    likelihood: 4,
    impact: 4,
  ),
];

class PracticeLab extends StatefulWidget {
  final Api? api;
  const PracticeLab({super.key, this.api});
  @override
  State<PracticeLab> createState() => _PracticeLabState();
}

class _PracticeLabState extends State<PracticeLab> {
  List<dynamic> history = [];
  List<PracticeCase> cases = practiceCases;
  bool ready = false;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    List<dynamic> saved = [];
    try {
      saved =
          jsonDecode(prefs.getString('grc.practice.history.v1') ?? '[]')
              as List;
    } catch (_) {
      /* Ignore corrupted local history. */
    }
    List<PracticeCase> cached = practiceCases;
    try {
      final data = prefs.getString('grc.practice.cases.v1');
      if (data != null) {
        cached = (jsonDecode(data) as List)
            .map(
              (item) => PracticeCase.fromJson(Map<String, dynamic>.from(item)),
            )
            .toList();
      }
    } catch (_) {
      /* Use bundled cases if the local catalog is corrupted. */
    }
    if (mounted) {
      setState(() {
        history = saved;
        cases = cached;
        ready = true;
      });
    }
    try {
      final data = await (widget.api ?? Api()).request('practice-cases/');
      final updated = (data as List)
          .map((item) => PracticeCase.fromJson(Map<String, dynamic>.from(item)))
          .toList();
      await prefs.setString('grc.practice.cases.v1', jsonEncode(data));
      if (mounted) setState(() => cases = updated);
    } catch (_) {
      /* Keep the last downloaded catalog available offline. */
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Vaka atölyesi')),
    body: Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 800),
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Text(
              'Bir denetçi gibi düşün.',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 12),
            const Text(
              'Vakayı oku, risk cümlesini kur, kontrolü ve kanıtı seç. Olasılık ve etkiyle önceliklendir. İnternetsiz de çalışır; sonuçların yalnızca bu cihazda saklanır. Hesabındaki XP ayrı takip edilir.',
            ),
            const SizedBox(height: 24),
            if (cases.isEmpty)
              const Text(
                'Yeni vakalar hazırlanıyor. Daha sonra tekrar bakabilirsin.',
              ),
            for (final scenario in cases)
              Card(
                child: ListTile(
                  contentPadding: const EdgeInsets.all(18),
                  leading: const Icon(
                    Icons.fact_check_outlined,
                    color: AppColors.teal,
                  ),
                  title: Text(
                    scenario.title,
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  subtitle: const Text('Risk → Kontrol → Kanıt → Karar'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () async {
                    await Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => PracticeWorkshop(scenario: scenario),
                      ),
                    );
                    load();
                  },
                ),
              ),
            const SizedBox(height: 24),
            Text(
              'Çalışma kayıtların',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            if (!ready) const LinearProgressIndicator(),
            if (ready && history.isEmpty)
              const Padding(
                padding: EdgeInsets.only(top: 12),
                child: Text(
                  'İlk vakayı tamamladığında kararların ve geri bildirimlerin burada görünecek.',
                ),
              ),
            for (final result in history.reversed.take(20))
              Card(
                child: ListTile(
                  title: Text('${result['title']}'),
                  subtitle: Text(
                    '${result['score']}/3 doğru karar • ${result['date'].toString().split('T').first}',
                  ),
                  trailing: const Icon(Icons.description_outlined),
                  onTap: () => showDialog(
                    context: context,
                    builder: (_) => AlertDialog(
                      title: Text('${result['title']}'),
                      content: SingleChildScrollView(
                        child: Text('${result['summary']}'),
                      ),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.pop(context),
                          child: const Text('Kapat'),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    ),
  );
}

class PracticeWorkshop extends StatefulWidget {
  final PracticeCase scenario;
  const PracticeWorkshop({super.key, required this.scenario});
  @override
  State<PracticeWorkshop> createState() => _PracticeWorkshopState();
}

class _PracticeWorkshopState extends State<PracticeWorkshop> {
  int step = 0, likelihood = 3, impact = 3;
  int? control, proof;
  List<String> sentence = [];
  final action = TextEditingController();
  bool saving = false;
  String? error;
  PracticeCase get c => widget.scenario;
  bool get correctSentence => sentence.join(',') == '0,1,2';
  int get score =>
      (correctSentence ? 1 : 0) +
      (control == c.control ? 1 : 0) +
      (proof == c.proof ? 1 : 0);
  @override
  void dispose() {
    action.dispose();
    super.dispose();
  }

  String get summary =>
      '${c.situation}\n\nRisk cümlen: ${sentence.map((id) => c.sentence[int.parse(id)]).join(' ')}\n\nÖrnek risk: ${c.sentence.join(' ')}\n\nKontrolün: ${c.controls[control!]}\n${c.controlReason}\n\nKanıtın: ${c.evidence[proof!]}\n${c.evidenceReason}\n\nDeğerlendirmen: Olasılık $likelihood × Etki $impact = ${likelihood * impact}/25.\nÖrnek değerlendirme: ${c.likelihood} × ${c.impact} = ${c.likelihood * c.impact}/25. Kurumun risk iştahına göre değişebilir.\n\nAksiyon planın: ${action.text.trim().isEmpty ? 'Henüz eklenmedi.' : action.text.trim()}';
  Future<void> save() async {
    if (saving) return;
    setState(() {
      saving = true;
      error = null;
    });
    try {
      final prefs = await SharedPreferences.getInstance();
      List<dynamic> history;
      try {
        history =
            jsonDecode(prefs.getString('grc.practice.history.v1') ?? '[]')
                as List;
      } catch (_) {
        history = [];
      }
      history.add({
        'case': c.id,
        'title': c.title,
        'score': score,
        'date': DateTime.now().toIso8601String(),
        'summary': summary,
      });
      final stored = await prefs.setString(
        'grc.practice.history.v1',
        jsonEncode(
          history.skip(history.length > 40 ? history.length - 40 : 0).toList(),
        ),
      );
      if (!stored) throw StateError('save failed');
      if (mounted) setState(() => step = 4);
    } catch (_) {
      if (mounted) {
        setState(
          () => error = 'Çalışman kaydedilemedi. Tekrar deneyebilirsin.',
        );
      }
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(c.title)),
    body: Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 800),
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            LinearProgressIndicator(value: (step + 1) / 5),
            const SizedBox(height: 20),
            Text(
              [
                '1. Riski tanımla',
                '2. Kontrolü seç',
                '3. Kanıtı değerlendir',
                '4. Önceliklendir ve planla',
                'Çalışman tamamlandı',
              ][step],
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Text(
                  c.situation,
                  style: const TextStyle(fontSize: 17, height: 1.6),
                ),
              ),
            ),
            const SizedBox(height: 20),
            if (step == 0) ...[
              const Text(
                'Neden → Olay → Etki sırasıyla risk cümlesini kur. Parçalara dokunabilir veya sürükleyebilirsin.',
              ),
              const SizedBox(height: 16),
              SentenceBuilder(
                options: [
                  for (final i in [2, 0, 1])
                    {'id': '$i', 'text': c.sentence[i]},
                ],
                value: sentence,
                enabled: true,
                onChanged: (value) => setState(() => sentence = value),
              ),
            ],
            if (step == 1 || step == 2) ...[
              Text(
                step == 1
                    ? 'Hangi kontrol riskin kaynağına doğrudan müdahale eder?'
                    : 'Kontrolün gerçekten işlediğini hangi kanıtla test edersin?',
              ),
              const SizedBox(height: 12),
              for (final entry
                  in (step == 1 ? c.controls : c.evidence).asMap().entries)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: OutlinedButton(
                    style: OutlinedButton.styleFrom(
                      alignment: Alignment.centerLeft,
                      padding: const EdgeInsets.all(20),
                      backgroundColor:
                          (step == 1 ? control : proof) == entry.key
                          ? AppColors.teal.withValues(alpha: .15)
                          : null,
                    ),
                    onPressed: () => setState(() {
                      if (step == 1) {
                        control = entry.key;
                      } else {
                        proof = entry.key;
                      }
                    }),
                    child: Text(entry.value),
                  ),
                ),
            ],
            if (step == 3) ...[
              const Text(
                '1 = düşük, 5 = çok yüksek. Varsayımlarını düşün; risk puanı tek başına kararın yerine geçmez.',
              ),
              const SizedBox(height: 20),
              Text('Olasılık: $likelihood / 5'),
              Wrap(
                spacing: 8,
                children: [
                  for (int i = 1; i <= 5; i++)
                    ChoiceChip(
                      label: Text('$i'),
                      selected: likelihood == i,
                      onSelected: (_) => setState(() => likelihood = i),
                    ),
                ],
              ),
              const SizedBox(height: 16),
              Text('Etki: $impact / 5'),
              Wrap(
                spacing: 8,
                children: [
                  for (int i = 1; i <= 5; i++)
                    ChoiceChip(
                      label: Text('$i'),
                      selected: impact == i,
                      onSelected: (_) => setState(() => impact = i),
                    ),
                ],
              ),
              const SizedBox(height: 20),
              Text(
                'Risk puanın: ${likelihood * impact}/25',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 20),
              TextField(
                controller: action,
                minLines: 3,
                maxLines: 6,
                maxLength: 1500,
                decoration: const InputDecoration(
                  labelText: 'Aksiyon planın (isteğe bağlı)',
                  hintText: 'Kim, neyi, ne zamana kadar yapmalı?',
                ),
              ),
            ],
            if (step == 4) ...[
              Text(
                '$score/3 doğru karar',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 12),
              Text(
                correctSentence
                    ? 'Risk cümlesi: neden, olay ve etkiyi bağladın.'
                    : 'Risk cümlesi: önce nedeni, sonra olayı ve etkisini bağla.',
              ),
              const SizedBox(height: 12),
              Text(
                control == c.control
                    ? 'Kontrol seçimin doğru.'
                    : 'En güçlü kontrol: ${c.controls[c.control]}',
              ),
              Text(c.controlReason),
              const SizedBox(height: 12),
              Text(
                proof == c.proof
                    ? 'Kanıt seçimin doğru.'
                    : 'Daha güçlü kanıt: ${c.evidence[c.proof]}',
              ),
              Text(c.evidenceReason),
              const SizedBox(height: 20),
              Text(
                'Örnek risk değerlendirmesi: ${c.likelihood} × ${c.impact} = ${c.likelihood * c.impact}/25. Seçtiğin ${likelihood * impact}/25 puanı kurumun risk iştahıyla birlikte değerlendir.',
              ),
              const SizedBox(height: 16),
              const Text(
                'Sonucun ve aksiyon planın cihazındaki çalışma kayıtlarına eklendi.',
              ),
              const SizedBox(height: 20),
              FilledButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Diğer vakaları çalış'),
              ),
            ],
            if (error != null) Text(error!),
            if (step < 4) ...[
              const SizedBox(height: 24),
              FilledButton(
                onPressed:
                    saving ||
                        (step == 0 && sentence.length != 3) ||
                        (step == 1 && control == null) ||
                        (step == 2 && proof == null)
                    ? null
                    : () {
                        if (step == 3) {
                          save();
                        } else {
                          setState(() => step++);
                        }
                      },
                child: Text(
                  saving
                      ? 'Kaydediliyor…'
                      : step == 3
                      ? 'Kararlarımı değerlendir ve kaydet'
                      : 'Devam et',
                ),
              ),
              if (step > 0)
                TextButton(
                  onPressed: saving ? null : () => setState(() => step--),
                  child: const Text('Önceki adıma dön'),
                ),
            ],
          ],
        ),
      ),
    ),
  );
}

class PracticeInvitation extends StatelessWidget {
  const PracticeInvitation({super.key});
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'VAKA ATÖLYESİ',
            style: TextStyle(
              color: AppColors.teal,
              fontWeight: FontWeight.w900,
              letterSpacing: 1,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Gerçek bir riski çöz.',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          const Text(
            '4 vaka • risk cümlesi • kontrol seçimi • kanıt • risk matrisi. Hesap gerektirmez, internetsiz çalışır.',
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: () => Navigator.of(
              context,
            ).push(MaterialPageRoute(builder: (_) => const PracticeLab())),
            icon: const Icon(Icons.play_arrow_rounded),
            label: const Text('Hemen bir vaka çöz'),
          ),
        ],
      ),
    ),
  );
}
