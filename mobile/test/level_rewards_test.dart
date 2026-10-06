import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:grc_ustasi/level_rewards.dart';
import 'package:grc_ustasi/dashboard_widgets.dart';
import 'package:grc_ustasi/theme.dart';

void main() {
  testWidgets('missing level falls back to zero and goals display', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.create(Brightness.light),
        home: Scaffold(
          body: SingleChildScrollView(
            child: Column(
              children: [
                const LearningStats(profile: {'xp': 0, 'completed': 0}),
                LevelRewards(
                  profile: {
                    'xp': 0,
                    'rewards': [
                      {
                        'id': 1,
                        'level': 1,
                        'title': 'Usta adayı',
                        'description': 'Dijital rozet',
                        'kind': 'badge',
                        'unlocked': false,
                        'remaining_xp': 100,
                      },
                    ],
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
    expect(find.text('Seviye 0'), findsOneWidget);
    expect(find.textContaining('null'), findsNothing);
    expect(find.text('100 XP daha kazan → Usta adayı'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
