import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:grc_ustasi/brand_welcome.dart';
import 'package:grc_ustasi/profile_actions.dart';
import 'package:grc_ustasi/theme.dart';

void main() {
  testWidgets(
    'WhatsApp opens native app without a message and uses wa.me fallback',
    (tester) async {
      final launched = <Uri>[];
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.create(Brightness.light),
          home: Scaffold(
            body: ProfileActions(
              contact: {'phone': '32476073171'},
              onPassword: () {},
              launcher: (uri) async {
                launched.add(uri);
                return launched.length > 1;
              },
            ),
          ),
        ),
      );
      await tester.tap(find.text('WhatsApp’tan Volkan’a eriş'));
      await tester.pumpAndSettle();
      expect(launched.length, 2);
      expect(launched.first.scheme, 'whatsapp');
      expect(launched.first.queryParameters, {'phone': '32476073171'});
      expect(launched.last.toString(), 'https://wa.me/32476073171');
    },
  );
  testWidgets(
    'empty admin phone hides contact and keeps password change available',
    (tester) async {
      var clicked = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ProfileActions(
              contact: {'phone': ''},
              onPassword: () {
                clicked = true;
              },
            ),
          ),
        ),
      );
      expect(find.text('WhatsApp’tan Volkan’a eriş'), findsNothing);
      await tester.tap(find.text('Şifreni yenile'));
      expect(clicked, isTrue);
    },
  );
  testWidgets(
    'password mismatch is shown before submitting and fields are obscured',
    (tester) async {
      var sent = false;
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.create(Brightness.light),
          home: PasswordChange(
            onSave: (_, _, _) async {
              sent = true;
            },
          ),
        ),
      );
      final fields = find.byType(TextField);
      for (final field in tester.widgetList<TextField>(fields)) {
        expect(field.obscureText, isTrue);
      }
      await tester.enterText(fields.at(0), 'Old!Pass123');
      await tester.enterText(fields.at(1), 'New!Pass123');
      await tester.enterText(fields.at(2), 'Mismatch');
      await tester.ensureVisible(find.text('Şifreyi yenile'));
      await tester.tap(find.text('Şifreyi yenile'));
      await tester.pumpAndSettle();
      expect(find.text('Yeni şifreler birbiriyle eşleşmiyor.'), findsOneWidget);
      expect(sent, isFalse);
    },
  );
  testWidgets('welcome rotates topics and disposes its looping animation', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: BrandWelcome())),
    );
    expect(find.text('Vakalar'), findsNWidgets(2));
    await tester.pump(const Duration(milliseconds: 1800));
    await tester.pump(const Duration(milliseconds: 500));
    expect(find.text('Lablar'), findsNWidgets(2));
    for (final feature in BrandWelcome.features) {
      expect(find.text(feature), findsWidgets);
    }
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
  testWidgets('reduced motion welcome stays still', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: MediaQuery(
          data: MediaQueryData(disableAnimations: true),
          child: Scaffold(body: BrandWelcome()),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.pump(const Duration(seconds: 4));
    expect(find.text('Vakalar'), findsNWidgets(2));
    expect(find.text('Lablar'), findsOneWidget);
  });
}
