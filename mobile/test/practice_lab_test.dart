import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:grc_ustasi/practice_lab.dart';

void main() {
  for (final c in practiceCases) {
    for (final correct in [true, false]) {
      testWidgets(
        '${c.id} saves ${correct ? 'correct' : 'incorrect'} decisions offline',
        (tester) async {
          SharedPreferences.setMockInitialValues({});
          await tester.pumpWidget(
            MaterialApp(home: PracticeWorkshop(scenario: c)),
          );
          for (final text in correct ? c.sentence : c.sentence.reversed) {
            await tester.ensureVisible(find.text(text).last);
            await tester.pumpAndSettle();
            await tester.tap(find.text(text).last);
            await tester.pumpAndSettle();
          }
          Future<void> tap(String text) async {
            await tester.ensureVisible(find.text(text));
            await tester.pumpAndSettle();
            await tester.tap(find.text(text));
            await tester.pumpAndSettle();
          }

          await tap('Devam et');
          await tap(c.controls[correct ? c.control : (c.control + 1) % 3]);
          await tap('Devam et');
          await tap(c.evidence[correct ? c.proof : (c.proof + 1) % 3]);
          await tap('Devam et');
          await tester.ensureVisible(find.byType(TextField));
          await tester.enterText(
            find.byType(TextField),
            'BT ekibi bu hafta kontrolü test etsin.',
          );
          await tap('Kararlarımı değerlendir ve kaydet');
          final score = correct ? 3 : 0;
          expect(find.text('$score/3 doğru karar'), findsOneWidget);
          final prefs = await SharedPreferences.getInstance();
          final saved =
              jsonDecode(prefs.getString('grc.practice.history.v1')!) as List;
          expect(saved.single['case'], c.id);
          expect(saved.single['score'], score);
          expect(saved.single['summary'], contains('BT ekibi bu hafta'));
          expect(saved.single['summary'], contains(c.evidenceReason));
          await tester.pumpWidget(const MaterialApp(home: PracticeLab()));
          await tester.pumpAndSettle();
          await tester.scrollUntilVisible(
            find.textContaining('$score/3 doğru karar'),
            300,
            scrollable: find.byType(Scrollable).first,
          );
          expect(find.textContaining('$score/3 doğru karar'), findsOneWidget);
        },
      );
    }
  }
}
