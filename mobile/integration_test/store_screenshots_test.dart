import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:integration_test/integration_test.dart';
import 'package:grc_ustasi/main.dart';

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets('Capture real iPhone store screens without answering tasks', (
    tester,
  ) async {
    const email = String.fromEnvironment('STORE_DEMO_EMAIL');
    const password = String.fromEnvironment('STORE_DEMO_PASSWORD');
    expect(
      email.isNotEmpty && password.isNotEmpty,
      isTrue,
      reason: 'Supply private demo credentials using --dart-define-from-file.',
    );
    await const FlutterSecureStorage().write(
      key: 'grc_daily_enabled',
      value: 'false',
    );
    await api.login(email, password);
    await tester.pumpWidget(const GrcApp());
    await tester.pump(const Duration(seconds: 3));
    for (int i = 0; i < 60 && find.text('Yollar').evaluate().isEmpty; i++) {
      await tester.pump(const Duration(milliseconds: 500));
    }
    await tester.pumpAndSettle();
    await binding.takeScreenshot('01-home');
    await tester.tap(find.text('Yollar'));
    await tester.pumpAndSettle();
    await binding.takeScreenshot('02-paths');
    final workshop = find.text('Risk Atölyesi • Sürükle ve Kur');
    await tester.scrollUntilVisible(
      workshop,
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(workshop);
    await tester.pumpAndSettle();
    await binding.takeScreenshot('03-task-introduction');
    await tester.tap(find.text('Başla'));
    for (int i = 0; i < 60 && find.text('Başla').evaluate().isNotEmpty; i++) {
      await tester.pump(const Duration(milliseconds: 500));
    }
    await tester.pumpAndSettle();
    await binding.takeScreenshot('04-risk-workshop');
    // No answers, voice uploads, payment, restart or deletion is submitted.
  });
}
