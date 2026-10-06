import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'theme.dart';

class BrandWelcome extends StatefulWidget {
  final bool splash;
  const BrandWelcome({super.key, this.splash = false});
  static const features = [
    'Vakalar',
    'Lablar',
    'Sınav soruları',
    'Gerçek hayat senaryoları',
    'Birebir etkileşim',
  ];
  @override
  State<BrandWelcome> createState() => _BrandWelcomeState();
}

class _BrandWelcomeState extends State<BrandWelcome>
    with SingleTickerProviderStateMixin {
  late final motion = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 4600),
  );
  Timer? rotation;
  int feature = 0;
  bool? reduceMotion;
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final reduce = MediaQuery.of(context).disableAnimations;
    if (reduce == reduceMotion) return;
    reduceMotion = reduce;
    rotation?.cancel();
    if (reduce) {
      motion.stop();
      motion.value = 0;
    } else {
      motion.repeat();
      rotation = Timer.periodic(const Duration(milliseconds: 1800), (_) {
        if (mounted && TickerMode.valuesOf(context).enabled) {
          setState(
            () => feature = (feature + 1) % BrandWelcome.features.length,
          );
        }
      });
    }
  }

  @override
  void dispose() {
    rotation?.cancel();
    motion.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final dark =
        widget.splash || Theme.of(context).brightness == Brightness.dark;
    final foreground = dark ? Colors.white : AppColors.ink;
    final logoSize = widget.splash ? 210.0 : 166.0;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        AnimatedBuilder(
          animation: motion,
          builder: (_, _) {
            final angle = motion.value * math.pi * 2;
            return SizedBox(
              height: logoSize + 16,
              width: logoSize + 70,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  Container(
                    width: logoSize - 22,
                    height: logoSize - 22,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(
                        colors: [
                          AppColors.gold.withValues(alpha: .3),
                          AppColors.teal.withValues(alpha: .04),
                        ],
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: AppColors.teal.withValues(alpha: .10),
                          blurRadius: 35,
                          spreadRadius: 10,
                        ),
                      ],
                    ),
                  ),
                  for (var i = 0; i < 3; i++)
                    Positioned(
                      left:
                          logoSize / 2 +
                          30 +
                          math.cos(angle + i * 2.1) * (logoSize / 2 + 20),
                      top:
                          logoSize / 2 +
                          math.sin(angle + i * 2.1) * (logoSize / 2 - 12),
                      child: Icon(
                        i == 0
                            ? Icons.auto_awesome_rounded
                            : Icons.star_rounded,
                        color: i == 1 ? AppColors.teal : AppColors.gold,
                        size: i == 0 ? 20 : 12,
                      ),
                    ),
                  Transform.translate(
                    offset: Offset(0, math.sin(angle) * 6),
                    child: Transform.rotate(
                      angle: math.sin(angle) * .015,
                      child: Image.asset(
                        'assets/logo.png',
                        width: logoSize,
                        height: logoSize,
                      ),
                    ),
                  ),
                ],
              ),
            );
          },
        ),
        const SizedBox(height: 14),
        Text(
          'BİLGİDEN USTALIĞA',
          style: TextStyle(
            color: dark ? AppColors.gold : AppColors.teal,
            letterSpacing: 2.4,
            fontSize: 11,
            fontWeight: FontWeight.w900,
          ),
        ),
        const SizedBox(height: 14),
        SizedBox(
          height: 68,
          child: Center(
            child: AnimatedSwitcher(
              duration: Duration(milliseconds: reduceMotion == true ? 0 : 450),
              transitionBuilder: (child, animation) => FadeTransition(
                opacity: animation,
                child: SlideTransition(
                  position: Tween<Offset>(
                    begin: const Offset(0, .25),
                    end: Offset.zero,
                  ).animate(animation),
                  child: child,
                ),
              ),
              child: Text(
                BrandWelcome.features[feature],
                key: ValueKey(feature),
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: widget.splash ? 29 : 26,
                  height: 1.12,
                  fontWeight: FontWeight.w900,
                  color: foreground,
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 12),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 7,
          runSpacing: 8,
          children: [
            for (var i = 0; i < BrandWelcome.features.length; i++)
              TweenAnimationBuilder<double>(
                tween: Tween(begin: reduceMotion == true ? 1 : 0, end: 1),
                duration: Duration(
                  milliseconds: reduceMotion == true ? 0 : 500 + i * 110,
                ),
                builder: (_, value, child) => Opacity(
                  opacity: value,
                  child: Transform.translate(
                    offset: Offset(0, (1 - value) * 14),
                    child: child,
                  ),
                ),
                child: AnimatedContainer(
                  duration: Duration(
                    milliseconds: reduceMotion == true ? 0 : 300,
                  ),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 11,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: i == feature
                        ? AppColors.teal.withValues(alpha: .2)
                        : foreground.withValues(alpha: .055),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: i == feature
                          ? AppColors.teal
                          : foreground.withValues(alpha: .13),
                    ),
                  ),
                  child: Text(
                    BrandWelcome.features[i],
                    style: TextStyle(
                      fontSize: 11,
                      color: foreground,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
          ],
        ),
      ],
    );
  }
}

class WelcomeSplash extends StatelessWidget {
  const WelcomeSplash({super.key});
  @override
  Widget build(BuildContext context) => Scaffold(
    body: DecoratedBox(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF0D1C30), Color(0xFF173D49), Color(0xFF11273E)],
        ),
      ),
      child: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const BrandWelcome(splash: true),
                const SizedBox(height: 32),
                const Text(
                  'GRC’yi deneyerek öğren.',
                  style: TextStyle(color: Colors.white70, fontSize: 16),
                ),
                const SizedBox(height: 22),
                const SizedBox(
                  width: 70,
                  child: LinearProgressIndicator(minHeight: 3),
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}
