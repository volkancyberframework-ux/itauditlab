import 'package:flutter/material.dart';
import 'theme.dart';

class LevelRewards extends StatelessWidget {
  final Map<String, dynamic> profile;
  const LevelRewards({super.key, required this.profile});
  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final level = profile['level'] ?? 0;
    final xp = profile['xp'] ?? 0;
    final next = profile['next_level_xp'] ?? 100;
    final rewards = profile['rewards'] as List? ?? [];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(22),
          decoration: BoxDecoration(
            color: scheme.surface,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: scheme.outlineVariant, width: 2),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(
                    Icons.workspace_premium_rounded,
                    color: AppColors.gold,
                    size: 36,
                  ),
                  const SizedBox(width: 12),
                  Text(
                    'Seviye $level',
                    style: const TextStyle(
                      fontSize: 25,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Text(
                '$xp XP • Sonraki seviye: $next XP',
                style: TextStyle(color: scheme.onSurfaceVariant),
              ),
              const SizedBox(height: 12),
              LinearProgressIndicator(
                value: ((profile['level_progress'] as num?)?.toDouble() ?? 0)
                    .clamp(0.0, 1.0),
                minHeight: 12,
                borderRadius: BorderRadius.circular(12),
                color: AppColors.teal,
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),
        const Text(
          'Seviye hediyelerin',
          style: TextStyle(fontSize: 21, fontWeight: FontWeight.w900),
        ),
        const SizedBox(height: 6),
        const Text('Öğren, seviye atla, yeni hediyelere ulaş.'),
        const SizedBox(height: 16),
        if (rewards.isEmpty)
          const Text('Yeni seviye hediyeleri yakında burada.'),
        for (final reward in rewards)
          Container(
            margin: const EdgeInsets.only(bottom: 14),
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: scheme.surface,
              borderRadius: BorderRadius.circular(22),
              border: Border.all(
                color: reward['unlocked'] == true
                    ? AppColors.teal
                    : scheme.outlineVariant,
                width: 2,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      reward['kind'] == 'badge'
                          ? Icons.workspace_premium_rounded
                          : Icons.card_giftcard_rounded,
                      color: reward['unlocked'] == true
                          ? AppColors.gold
                          : scheme.onSurfaceVariant,
                      size: 30,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Seviye ${reward['level']} • ${reward['title']}',
                        style: const TextStyle(
                          fontWeight: FontWeight.w900,
                          fontSize: 16,
                          height: 1.4,
                        ),
                      ),
                    ),
                  ],
                ),
                if ((reward['description'] ?? '').isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Text(
                    reward['description'],
                    style: TextStyle(
                      color: scheme.onSurfaceVariant,
                      height: 1.5,
                    ),
                  ),
                ],
                const SizedBox(height: 12),
                Text(
                  reward['unlocked'] == true
                      ? (reward['kind'] == 'badge'
                            ? '✓ Rozet kazanıldı'
                            : reward['delivered'] == true
                            ? '✓ Hediye teslim edildi'
                            : '✓ Hak kazandın • yönetici teslimi bekleniyor')
                      : '${reward['remaining_xp']} XP daha kazan → ${reward['title']}',
                  style: TextStyle(
                    color: scheme.primary,
                    fontWeight: FontWeight.w800,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}
