import 'dart:math' as math;
import 'package:confetti/confetti.dart';
import 'package:flutter/material.dart';
import 'theme.dart';

enum CelebrationKind { confetti, fireworks, stars, xpRain }

/// Choose once per confirmed answer; the previous celebration never repeats.
class CelebrationPicker {
  static final _random = math.Random();
  static CelebrationKind? _previous;
  static CelebrationKind next() {
    final choices = CelebrationKind.values
        .where((v) => v != _previous)
        .toList();
    return _previous = choices[_random.nextInt(choices.length)];
  }
}

class CelebrationOverlay extends StatefulWidget {
  final CelebrationKind kind;
  const CelebrationOverlay({super.key, required this.kind});
  @override
  State<CelebrationOverlay> createState() => _CelebrationOverlayState();
}

class _CelebrationOverlayState extends State<CelebrationOverlay>
    with SingleTickerProviderStateMixin {
  late final AnimationController animation;
  @override
  void initState() {
    super.initState();
    animation = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2600),
    );
  }

  final confetti = ConfettiController(
    duration: const Duration(milliseconds: 1700),
  );
  bool started = false;
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!started) {
      started = true;
      if (!MediaQuery.of(context).disableAnimations) {
        animation.forward();
        if (widget.kind == CelebrationKind.confetti) confetti.play();
      }
    }
  }

  @override
  void dispose() {
    animation.dispose();
    confetti.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => ExcludeSemantics(
    child: IgnorePointer(
      child: SizedBox.expand(
        child: widget.kind == CelebrationKind.confetti
            ? Stack(
                children: [
                  for (final left in [true, false])
                    Align(
                      alignment: left ? Alignment.topLeft : Alignment.topRight,
                      child: ConfettiWidget(
                        confettiController: confetti,
                        blastDirection: left ? math.pi / 3 : 2 * math.pi / 3,
                        emissionFrequency: .12,
                        numberOfParticles: 18,
                        maxBlastForce: 35,
                        minBlastForce: 12,
                        gravity: .15,
                        colors: const [
                          AppColors.teal,
                          AppColors.gold,
                          Color(0xFF9A7CF5),
                          Color(0xFFF58AB4),
                          Colors.white,
                        ],
                      ),
                    ),
                ],
              )
            : AnimatedBuilder(
                animation: animation,
                builder: (_, _) => CustomPaint(
                  painter: _CelebrationPainter(widget.kind, animation.value),
                ),
              ),
      ),
    ),
  );
}

class _CelebrationPainter extends CustomPainter {
  final CelebrationKind kind;
  final double t;
  _CelebrationPainter(this.kind, this.t);
  static const colors = [
    AppColors.gold,
    AppColors.teal,
    Color(0xFF9A7CF5),
    Color(0xFFEC84AF),
    Color(0xFF51B9EF),
  ];
  @override
  void paint(Canvas canvas, Size size) {
    if (t == 0 || t == 1) return;
    if (kind == CelebrationKind.fireworks) {
      for (var burst = 0; burst < 7; burst++) {
        final local = ((t - burst * .065) / .5).clamp(0.0, 1.0);
        if (local == 0 || local == 1) continue;
        final center = Offset(
          size.width * (.15 + (burst * .27) % .7),
          size.height * (.15 + (burst * .19) % .6),
        );
        final paint = Paint()
          ..color = colors[burst % colors.length].withValues(alpha: 1 - local)
          ..strokeWidth = 3
          ..strokeCap = StrokeCap.round;
        for (var ray = 0; ray < 24; ray++) {
          final angle = ray * math.pi / 12;
          final direction = Offset(math.cos(angle), math.sin(angle));
          canvas.drawLine(
            center + direction * (local * 105),
            center + direction * (local * 105 + 12 * (1 - local)),
            paint,
          );
        }
        canvas.drawCircle(
          center,
          local * 85,
          Paint()
            ..color = colors[burst % colors.length].withValues(
              alpha: (1 - local) * .2,
            )
            ..style = PaintingStyle.stroke
            ..strokeWidth = 2,
        );
      }
      return;
    }
    final opacity = t < .12
        ? t / .12
        : t > .78
        ? (1 - t) / .22
        : 1.0;
    for (var i = 0; i < 44; i++) {
      final x = size.width * ((i * .6180339) % 1) + math.sin(t * 7 + i) * 18;
      final y = (size.height + 140) * ((t * 1.35 + (i * .173) % 1) % 1) - 70;
      canvas.save();
      canvas.translate(x, y);
      canvas.rotate(t * 5 + i);
      final paint = Paint()
        ..color = colors[i % colors.length].withValues(
          alpha: opacity.clamp(0.0, 1.0),
        );
      if (kind == CelebrationKind.stars) {
        final path = Path();
        for (var point = 0; point < 10; point++) {
          final angle = point * math.pi / 5 - math.pi / 2;
          final radius = point.isEven ? 10.0 + i % 6 : 5.0;
          final dx = math.cos(angle) * radius, dy = math.sin(angle) * radius;
          if (point == 0) {
            path.moveTo(dx, dy);
          } else {
            path.lineTo(dx, dy);
          }
        }
        canvas.drawPath(path..close(), paint);
      } else {
        canvas.drawCircle(
          Offset.zero,
          13,
          Paint()
            ..color = AppColors.gold.withValues(alpha: opacity.clamp(0.0, 1.0)),
        );
        canvas.drawCircle(
          Offset.zero,
          10,
          Paint()
            ..color = AppColors.ink.withValues(alpha: opacity.clamp(0.0, 1.0))
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.5,
        );
        final bolt = Path()
          ..moveTo(2, -8)
          ..lineTo(-5, 1)
          ..lineTo(0, 1)
          ..lineTo(-2, 8)
          ..lineTo(6, -2)
          ..lineTo(1, -2)
          ..close();
        canvas.drawPath(
          bolt,
          Paint()
            ..color = AppColors.ink.withValues(alpha: opacity.clamp(0.0, 1.0)),
        );
      }
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(_CelebrationPainter old) => old.t != t || old.kind != kind;
}
