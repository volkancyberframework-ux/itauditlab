import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:grc_ustasi/answer_feedback.dart';
import 'package:grc_ustasi/theme.dart';

void main() {
  Future<void> show(
    WidgetTester tester,
    bool correct,
    int xp, {
    bool reduced = false,
  }) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.create(Brightness.light),
        home: MediaQuery(
          data: MediaQueryData(disableAnimations: reduced),
          child: AnswerFeedback(
            result: {
              'correct': correct,
              'xp_change': xp,
              'explanation': 'Kontrolün gerekçesi',
              'hint': 'İpucu',
            },
            onContinue: () {},
          ),
        ),
      ),
    );
    await tester.pump(const Duration(seconds: 3));
  }

  testWidgets(
    'wrong feedback shows actual server deduction and allows continuation',
    (tester) async {
      await show(tester, false, -5);
      expect(find.text('5 XP kaybettin'), findsOneWidget);
      expect(find.text('Ah, bu sefer olmadı.'), findsOneWidget);
      expect(find.text('Devam Et →'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets('zero XP stays truthful and reduced motion is supported', (
    tester,
  ) async {
    await show(tester, false, 0, reduced: true);
    expect(find.text('XP kaybetmedin'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
  testWidgets('success shows confirmed XP reward', (tester) async {
    await show(tester, true, 20);
    expect(find.text('+20 XP kazandın'), findsOneWidget);
    expect(find.text('Çok iyi gidiyorsun!'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
