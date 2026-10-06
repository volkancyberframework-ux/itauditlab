import 'dart:math' as math;
import 'package:confetti/confetti.dart';
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
  late final ConfettiController confetti = ConfettiController(
    duration: const Duration(milliseconds: 1800),
  );
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
        if (correct && widget.result['pending'] != true) {
          confetti.play();
        }
      } else {
        motion.value = 1;
      }
    }
  }

  @override
  void dispose() {
    motion.dispose();
    confetti.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final pending = widget.result['pending'] == true;
    final change = widget.result['xp_change'] as int;
    final scheme = Theme.of(context).colorScheme;
    final accent = correct ? const Color(0xFF20B889) : const Color(0xFFDE9B47);
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
                          const SizedBox(height: 38),
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
                                      ? '🥳'
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
                          FilledButton(
                            onPressed: widget.onContinue,
                            child: const Text('Devam Et →'),
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
        if (correct && !pending)
          IgnorePointer(
            child: Stack(
              children: [
                Align(
                  alignment: Alignment.topLeft,
                  child: ConfettiWidget(
                    confettiController: confetti,
                    blastDirection: math.pi / 3,
                    emissionFrequency: .12,
                    numberOfParticles: 16,
                    maxBlastForce: 30,
                    minBlastForce: 12,
                    gravity: .16,
                    shouldLoop: false,
                    colors: const [
                      Color(0xFF20B889),
                      Color(0xFFFFC857),
                      Color(0xFF60A5FA),
                      Color(0xFFF69DBB),
                      Colors.white,
                    ],
                  ),
                ),
                Align(
                  alignment: Alignment.topRight,
                  child: ConfettiWidget(
                    confettiController: confetti,
                    blastDirection: 2 * math.pi / 3,
                    emissionFrequency: .12,
                    numberOfParticles: 16,
                    maxBlastForce: 30,
                    minBlastForce: 12,
                    gravity: .16,
                    shouldLoop: false,
                    colors: const [
                      Color(0xFF20B889),
                      Color(0xFFFFC857),
                      Color(0xFF60A5FA),
                      Color(0xFFF69DBB),
                      Colors.white,
                    ],
                  ),
                ),
                Align(
                  alignment: Alignment.center,
                  child: ConfettiWidget(
                    confettiController: confetti,
                    blastDirectionality: BlastDirectionality.explosive,
                    emissionFrequency: .04,
                    numberOfParticles: 22,
                    maxBlastForce: 25,
                    minBlastForce: 8,
                    gravity: .18,
                    shouldLoop: false,
                    colors: const [
                      Color(0xFF20B889),
                      Color(0xFFFFC857),
                      Color(0xFF60A5FA),
                      Color(0xFFF69DBB),
                    ],
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}
