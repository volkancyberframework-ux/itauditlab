import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:grc_ustasi/password_reset.dart';
import 'package:grc_ustasi/account_deletion.dart';
import 'package:grc_ustasi/apple_membership.dart';
import 'package:grc_ustasi/apple_store.dart';
import 'package:grc_ustasi/api.dart';
import 'package:in_app_purchase/in_app_purchase.dart';

class UnavailableStore extends Fake implements InAppPurchase {
  @override
  Stream<List<PurchaseDetails>> get purchaseStream => const Stream.empty();
  @override
  Future<bool> isAvailable() async => false;
}

void main() {
  testWidgets('reset sends entered email and blocks duplicate requests', (
    tester,
  ) async {
    final pending = Completer<String>();
    int calls = 0;
    await tester.pumpWidget(
      MaterialApp(
        home: PasswordResetScreen(
          initialEmail: 'demo@example.com',
          onRequest: (email) {
            expect(email, 'demo@example.com');
            calls++;
            return pending.future;
          },
        ),
      ),
    );
    await tester.tap(find.text('Şifre sıfırlama e-postası gönder'));
    await tester.pump();
    expect(tester.widget<TextField>(find.byType(TextField)).enabled, isFalse);
    expect(calls, 1);
    pending.complete('Hesabın varsa e-posta gönderdik.');
    await tester.pump();
    expect(find.text('Hesabın varsa e-posta gönderdik.'), findsOneWidget);
    expect(find.textContaining('spam klasörünü'), findsOneWidget);
  });
  testWidgets('iOS offers Apple restore and no external checkout', (
    tester,
  ) async {
    debugDefaultTargetPlatformOverride = TargetPlatform.iOS;
    addTearDown(() => debugDefaultTargetPlatformOverride = null);
    await tester.pumpWidget(
      MaterialApp(
        home: AppleMembership(
          store: AppleStore(Api(), store: UnavailableStore()),
          accountId: 'demo',
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Premium ol'), findsOneWidget);
    expect(find.text('Satın alımları geri yükle'), findsOneWidget);
    expect(find.textContaining('2.099'), findsNothing);
    expect(find.text('GRC Ustası websitesinden öde'), findsNothing);
    debugDefaultTargetPlatformOverride = null;
  });
  testWidgets(
    'deletion requires explicit checkbox and explains website account loss',
    (tester) async {
      int calls = 0;
      await tester.pumpWidget(
        MaterialApp(
          home: AccountDeletionScreen(
            onRequest: (_) async {
              calls++;
              return 'Talep alındı.';
            },
          ),
        ),
      );
      expect(find.textContaining('websitesindeki hesabına'), findsOneWidget);
      await tester.enterText(find.byType(TextField), 'Secret-Pass-119');
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byType(CheckboxListTile));
      await tester.tap(find.byType(CheckboxListTile));
      await tester.pump();
      await tester.scrollUntilVisible(
        find.text('Hesap silme talebini gönder'),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.tap(find.text('Hesap silme talebini gönder'));
      await tester.pump();
      expect(calls, 1);
      expect(find.text('Talep alındı.'), findsOneWidget);
    },
  );
}
