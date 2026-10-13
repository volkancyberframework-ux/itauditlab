import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:grc_ustasi/pwa_install_card.dart';
import 'package:grc_ustasi/profile_actions.dart';

void main() {
  testWidgets(
    'profile install card uses profile styling and calls installation once',
    (tester) async {
      var calls = 0;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: PwaInstallCard(
              showForTesting: true,
              onInstall: () => calls++,
            ),
          ),
        ),
      );
      expect(find.byType(Card), findsOneWidget);
      expect(find.byType(ListTile), findsOneWidget);
      await tester.tap(find.text('Uygulamayı yükle'));
      expect(calls, 1);
    },
  );
  testWidgets('installed or native app does not show installation card', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: PwaInstallCard(showForTesting: false)),
      ),
    );
    expect(find.text('Uygulamayı yükle'), findsNothing);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ProfileActions(contact: const {}, onPassword: () {}),
        ),
      ),
    );
    expect(find.text('Uygulamayı yükle'), findsNothing);
    expect(find.text('Şifreni yenile'), findsOneWidget);
  });
  testWidgets(
    'missing browser bridge shows actionable fallback, never a dead button',
    (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: PwaInstallCard(showForTesting: true)),
        ),
      );
      await tester.tap(find.text('Uygulamayı yükle'));
      await tester.pumpAndSettle();
      expect(find.text('Ana ekranına ekle'), findsOneWidget);
      await tester.tap(find.text('Tamam'));
      await tester.pumpAndSettle();
      expect(find.text('Ana ekranına ekle'), findsNothing);
    },
  );
}
