import 'package:flutter/material.dart';
import 'theme.dart';

class LearningExperience extends StatelessWidget {
  const LearningExperience({super.key});

  Widget section(
    IconData icon,
    Color color,
    String title,
    List<InlineSpan> text,
  ) => Container(
    margin: const EdgeInsets.only(bottom: 16),
    padding: const EdgeInsets.all(20),
    decoration: BoxDecoration(
      color: color.withValues(alpha: .08),
      borderRadius: BorderRadius.circular(22),
      border: Border.all(color: color.withValues(alpha: .3)),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, color: color),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                title,
                style: TextStyle(
                  color: color,
                  fontSize: 19,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Text.rich(
          TextSpan(children: text),
          style: const TextStyle(fontSize: 15, height: 1.65),
        ),
      ],
    ),
  );

  TextSpan bold(String text) => TextSpan(
    text: text,
    style: const TextStyle(fontWeight: FontWeight.w800),
  );

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        'Sadece öğrenme. Deneyimle.',
        style: Theme.of(
          context,
        ).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w900),
      ),
      const SizedBox(height: 12),
      const Text(
        'GRC Ustası, yönetişim, risk ve uyum bilgisini günlük hayatta kullanabileceğin bir beceriye dönüştürmek için tasarlandı. Burada amaç yalnızca doğru şıkkı bulmak değil; bir uzmanın nasıl düşündüğünü adım adım deneyimlemek.',
        style: TextStyle(height: 1.6, fontSize: 16),
      ),
      const SizedBox(height: 22),
      section(
        Icons.business_center_outlined,
        AppColors.teal,
        'Bir gün vaka, bir gün senaryo',
        [
          const TextSpan(
            text:
                'Bazen bir şirketin yaşadığı olayı inceleyecek, bazen kendini bir denetçi ya da risk uzmanının yerine koyacaksın. ',
          ),
          bold(
            'Ne yanlış gidebilir? Bunun etkisi ne olur? Hangi kontrol gerçekten işe yarar? ',
          ),
          const TextSpan(
            text:
                'Sorular seni ezberden çıkarıp karar vermeye, bağlantı kurmaya ve gerekçeni düşünmeye yönlendirir.',
          ),
        ],
      ),
      section(
        Icons.touch_app_outlined,
        const Color(0xFF6E61C8),
        'Bilgiyi elinle kur, fikrini sınayarak öğren',
        [
          const TextSpan(
            text:
                'Kartları kaydır, seçenekleri taşı, risk cümlesini parçaları birleştirerek kur. Bir laboratuvar görevi, bir sınav sorusu veya gerçek hayat senaryosu seni aynı konuya farklı açılardan yaklaştırır. ',
          ),
          bold('Dinleyerek, okuyarak ve uygulayarak öğrenirsin. '),
          const TextSpan(
            text:
                'Soruların arasındaki renkli bilgi kartları, bir sonraki adımın nedenini kavramana yardımcı olur.',
          ),
        ],
      ),
      section(
        Icons.mic_none_rounded,
        const Color(0xFFC36A29),
        'Sesinle anlat, düşünceni görünür kıl',
        [
          const TextSpan(
            text:
                'Sesli görevlerde kendi açıklamanı kaydedebilir ya da sorunun yazılı yanıt seçeneğini kullanabilirsin. ',
          ),
          bold(
            'Bir riski kendi cümlelerinle anlatmak, onu gerçekten anlamanın güçlü bir yoludur. ',
          ),
          const TextSpan(
            text:
                'Gönderdiğin ses kaydı Volkan tarafından incelenir; geri bildirimin 24 saat içinde e-posta adresine gönderilir. Böylece yalnızca sonucu değil, yaklaşımını da geliştirebilirsin.',
          ),
        ],
      ),
      section(
        Icons.auto_awesome_rounded,
        const Color(0xFFB78B21),
        'Küçük oturumlar, kalıcı gelişim',
        [
          const TextSpan(
            text:
                'Bir öğrenme yolunda çok sayıda görev bulunabilir. Hepsini bir seferde bitirmen gerekmez. Kısa oturumlarla ilerle; tamamladığın görevler kaydedilir ve yeni içerikler eklendikçe yolun devam eder. ',
          ),
          bold(
            'Doğru cevaplarla XP kazan, seviyeni yükselt ve hedeflerine yaklaş. ',
          ),
          const TextSpan(
            text:
                'Hata yapmak da öğrenmenin parçasıdır: açıklamayı oku, yeniden dene ve istersen tamamladığın yolu baştan çalış.',
          ),
        ],
      ),
      Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: AppColors.teal,
          borderRadius: BorderRadius.circular(22),
        ),
        child: const Text(
          'Bugünkü hedefin mükemmel olmak değil. Bir olayı daha iyi anlamak, bir kararı daha bilinçli vermek ve dünden bir adım ileri gitmek.\n\nHazırsan, ilk görev seni bekliyor.',
          style: TextStyle(
            color: Colors.white,
            fontSize: 16,
            height: 1.6,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    ],
  );
}
