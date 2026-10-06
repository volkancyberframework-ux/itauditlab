import 'dart:math' as math;
import 'celebrations.dart';
import 'theme.dart';
import 'package:flutter/material.dart';

/// Full-screen result layer. XP always comes from the confirmed server response.
class AnswerFeedback extends StatefulWidget {
  final Map<String, dynamic> result;
  final VoidCallback onContinue;
  const AnswerFeedback({
    super.key,
    required this.result,
    required this.onContinue,
  });
  @override
  State<AnswerFeedback> createState() => _AnswerFeedbackState();
}

class _AnswerFeedbackState extends State<AnswerFeedback>
    with SingleTickerProviderStateMixin {
  late final CelebrationKind celebration = CelebrationPicker.next();
  late final AnimationController motion = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 650),
  );
  bool started = false;
  bool get correct => widget.result['correct'] == true;
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!started) {
      started = true;
      if (!MediaQuery.of(context).disableAnimations) {
        motion.forward();
      } else {
        motion.value = 1;
      }
    }
  }

  @override
  void dispose() {
    motion.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final pending = widget.result['pending'] == true;
    final change = widget.result['xp_change'] as int;
    final scheme = Theme.of(context).colorScheme;
    final accent = correct ? AppColors.teal : AppColors.gold;
    return Stack(
      fit: StackFit.expand,
      children: [
        AnimatedBuilder(
          animation: motion,
          builder: (_, child) {
            final t = motion.value;
            final shake = !correct && t < 1
                ? math.sin(t * math.pi * 12) * 10 * (1 - t)
                : 0.0;
            return Transform.translate(offset: Offset(shake, 0), child: child);
          },
          child: Scaffold(
            backgroundColor: scheme.surface,
            body: SafeArea(
              child: LayoutBuilder(
                builder: (_, constraints) => SingleChildScrollView(
                  child: ConstrainedBox(
                    constraints: BoxConstraints(
                      minHeight: constraints.maxHeight,
                    ),
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(28, 36, 28, 24),
                      child: Column(
                        children: [
                          Text(
                            pending
                                ? 'YANITIN ALINDI'
                                : correct
                                ? 'HARİKA İŞ!'
                                : 'BİR SONRAKİ ADIM',
                            style: TextStyle(
                              color: accent,
                              letterSpacing: 2.5,
                              fontSize: 12,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          const SizedBox(height: 12),
                          if (correct && !pending)
                            Text(
                              [
                                'KONFETİ ZAMANI',
                                'BİLGİNLE PARLADIN',
                                'YILDIZ GİBİSİN',
                                'XP YAĞMURU',
                              ][celebration.index],
                              style: TextStyle(
                                color: scheme.onSurfaceVariant,
                                fontSize: 10,
                                letterSpacing: 1.5,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          const SizedBox(height: 30),
                          ScaleTransition(
                            scale: Tween<double>(begin: .75, end: 1).animate(
                              CurvedAnimation(
                                parent: motion,
                                curve: Curves.easeOutBack,
                              ),
                            ),
                            child: Container(
                              width: 150,
                              height: 150,
                              decoration: BoxDecoration(
                                color: accent.withValues(alpha: .12),
                                shape: BoxShape.circle,
                                border: Border.all(
                                  color: accent.withValues(alpha: .25),
                                  width: 2,
                                ),
                              ),
                              child: Center(
                                child: Text(
                                  pending
                                      ? '🎙️'
                                      : correct
                                      ? [
                                          '🥳',
                                          '🚀',
                                          '🌟',
                                          '🏆',
                                        ][celebration.index]
                                      : '🥺',
                                  style: const TextStyle(fontSize: 78),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 28),
                          Text(
                            pending
                                ? 'Sesin bize ulaştı.'
                                : correct
                                ? 'Çok iyi gidiyorsun!'
                                : 'Ah, bu sefer olmadı.',
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.headlineMedium
                                ?.copyWith(fontWeight: FontWeight.w800),
                          ),
                          const SizedBox(height: 14),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 24,
                              vertical: 14,
                            ),
                            decoration: BoxDecoration(
                              color: accent.withValues(alpha: .14),
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: TweenAnimationBuilder<double>(
                              tween: Tween(begin: 0, end: change.toDouble()),
                              duration: const Duration(milliseconds: 700),
                              builder: (_, value, _) => Text(
                                pending
                                    ? 'İnceleme bekleniyor'
                                    : correct
                                    ? '+${value.round()} XP kazandın'
                                    : change < 0
                                    ? '${value.round().abs()} XP kaybettin'
                                    : 'XP kaybetmedin',
                                style: TextStyle(
                                  fontSize: 22,
                                  fontWeight: FontWeight.w800,
                                  color: accent,
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 12),
                          if (!correct)
                            Text(
                              change < 0
                                  ? 'Moralini bozma. Bir sonraki görevde geri kazanabilirsin.'
                                  : 'Toplam XP’n sıfırın altına düşmez. Öğrenmeye devam!',
                              textAlign: TextAlign.center,
                              style: TextStyle(color: scheme.onSurfaceVariant),
                            ),
                          const SizedBox(height: 28),
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(22),
                            decoration: BoxDecoration(
                              color: scheme.surfaceContainer,
                              borderRadius: BorderRadius.circular(24),
                              border: Border.all(
                                color: scheme.outlineVariant,
                                width: 2,
                              ),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Icon(
                                      Icons.lightbulb_outline_rounded,
                                      color: accent,
                                    ),
                                    const SizedBox(width: 8),
                                    Text(
                                      pending
                                          ? 'Sıradaki adım'
                                          : 'Aklında kalsın',
                                      style: const TextStyle(
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 12),
                                Text(
                                  widget.result['explanation'] ?? '',
                                  style: const TextStyle(
                                    fontSize: 16,
                                    height: 1.5,
                                  ),
                                ),
                                if (!correct &&
                                    (widget.result['hint'] ?? '')
                                        .isNotEmpty) ...[
                                  const SizedBox(height: 12),
                                  Text(
                                    'İpucu: ${widget.result['hint']}',
                                    style: TextStyle(
                                      color: scheme.onSurfaceVariant,
                                      height: 1.5,
                                    ),
                                  ),
                                ],
                              ],
                            ),
                          ),
                          const SizedBox(height: 32),
                          PrimaryButton(
                            label: 'Devam Et →',
                            onPressed: widget.onContinue,
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
        if (correct && !pending) CelebrationOverlay(kind: celebration),
      ],
    );
  }
}
