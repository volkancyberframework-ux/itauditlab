import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:grc_ustasi/practice_lab.dart';
import 'package:grc_ustasi/theme.dart';

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets('Native risk workshop works without authentication or network', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: AppTheme.create(Brightness.light),
        home: const PracticeLab(),
      ),
    );
    await tester.pumpAndSettle();
    await binding.takeScreenshot('05-native-case-library');
    await tester.tap(find.text(practiceCases.first.title).first);
    await tester.pumpAndSettle();
    final c = practiceCases.first;
    Future<void> tapText(String text) async {
      await tester.ensureVisible(find.text(text).last);
      await tester.pumpAndSettle();
      await tester.tap(find.text(text).last);
      await tester.pumpAndSettle();
    }

    for (final piece in c.sentence) {
      await tapText(piece);
    }
    await tester.drag(find.byType(Scrollable).first, const Offset(0, 1000));
    await tester.pumpAndSettle();
    await binding.takeScreenshot('06-native-risk-sentence');
    await tapText('Devam et');
    await tapText(c.controls[c.control]);
    await tapText('Devam et');
    await tapText(c.evidence[c.proof]);
    await tapText('Devam et');
    await tester.drag(find.byType(Scrollable).first, const Offset(0, 1000));
    await tester.pumpAndSettle();
    await binding.takeScreenshot('07-native-risk-matrix');
    await tapText('Kararlarımı değerlendir ve kaydet');
    expect(find.text('3/3 doğru karar'), findsOneWidget);
    await tester.drag(find.byType(Scrollable).first, const Offset(0, 1000));
    await tester.pumpAndSettle();
    await binding.takeScreenshot('08-native-case-feedback');
  });
}
