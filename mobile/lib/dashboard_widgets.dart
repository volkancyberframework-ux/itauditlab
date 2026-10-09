import 'package:flutter/material.dart';
import 'theme.dart';

class BrandHeader extends StatelessWidget {
  const BrandHeader({super.key});
  @override
  Widget build(BuildContext context) => Row(
    children: [
      Image.asset('assets/logo.png', width: 48, height: 48),
      const SizedBox(width: 10),
      const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'GRC USTASI',
            style: TextStyle(
              fontSize: 17,
              fontWeight: FontWeight.w900,
              letterSpacing: 1,
            ),
          ),
          Text(
            'HER GÜN BİR ADIM İLERİ',
            style: TextStyle(
              fontSize: 9,
              letterSpacing: 1.2,
              color: AppColors.teal,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    ],
  );
}

class DashboardHero extends StatelessWidget {
  final String name;
  const DashboardHero({super.key, required this.name});
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(22),
    decoration: BoxDecoration(
      gradient: const LinearGradient(
        colors: [Color(0xFF183A58), Color(0xFF0E233C)],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      ),
      borderRadius: BorderRadius.circular(30),
      border: Border.all(color: const Color(0xFF365674), width: 2),
      boxShadow: const [
        BoxShadow(
          color: Color(0x20102A43),
          offset: Offset(0, 6),
          blurRadius: 0,
        ),
      ],
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'UZMANLIK YOLCULUĞUN',
                    style: TextStyle(
                      color: AppColors.gold,
                      fontSize: 10,
                      letterSpacing: 1.5,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 14),
                  Text(
                    name.trim().isEmpty ? 'Merhaba!' : 'Merhaba ${name.trim()}!',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 26,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Küçük bir görev.\nBüyük bir gelişim.',
                    style: TextStyle(
                      color: Color(0xFFCBD9E5),
                      fontSize: 15,
                      height: 1.5,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Image.asset(
              'assets/logo.png',
              width: MediaQuery.sizeOf(context).width < 360 ? 80 : 114,
              height: MediaQuery.sizeOf(context).width < 360 ? 100 : 130,
              fit: BoxFit.contain,
            ),
          ],
        ),
        const SizedBox(height: 20),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 10),
          decoration: BoxDecoration(
            color: const Color(0xFF27415C),
            borderRadius: BorderRadius.circular(14),
          ),
          child: const Row(
            children: [
              Icon(Icons.auto_awesome_rounded, color: AppColors.gold, size: 19),
              SizedBox(width: 9),
              Expanded(
                child: Text(
                  'Bilgini güçlendir. XP’leri topla.',
                  style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

class LearningStats extends StatelessWidget {
  final Map<String, dynamic> profile;
  const LearningStats({super.key, required this.profile});
  @override
  Widget build(BuildContext context) => Row(
    children: [
      Expanded(
        child: _Stat(
          icon: Icons.bolt_rounded,
          color: AppColors.gold,
          value: '${profile['xp']}',
          label: 'TOPLAM XP',
        ),
      ),
      const SizedBox(width: 10),
      Expanded(
        child: _Stat(
          icon: Icons.check_circle_rounded,
          color: AppColors.teal,
          value: '${profile['completed']}',
          label: 'TAMAMLANAN',
        ),
      ),
      const SizedBox(width: 10),
      Expanded(
        child: _Stat(
          icon: Icons.workspace_premium_rounded,
          color: const Color(0xFF9A7CF5),
          value: '${profile['level'] ?? 0}',
          label: 'SEVİYE',
        ),
      ),
    ],
  );
}

class _Stat extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String value, label;
  const _Stat({
    required this.icon,
    required this.color,
    required this.value,
    required this.label,
  });
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 16),
    decoration: BoxDecoration(
      color: Theme.of(context).colorScheme.surface,
      borderRadius: BorderRadius.circular(22),
      border: Border.all(
        color: Theme.of(context).colorScheme.outlineVariant,
        width: 2,
      ),
    ),
    child: Column(
      children: [
        Icon(icon, color: color, size: 28),
        const SizedBox(height: 6),
        Text(
          value,
          style: const TextStyle(fontSize: 23, fontWeight: FontWeight.w900),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          textAlign: TextAlign.center,
          style: const TextStyle(
            fontSize: 9,
            fontWeight: FontWeight.w800,
            letterSpacing: .4,
          ),
        ),
      ],
    ),
  );
}
