import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:grc_ustasi/profile_actions.dart';

void main() {
  testWidgets('first login requires personal password before continuing', (
    tester,
  ) async {
    bool completed = false;
    String? savedPassword;
    await tester.pumpWidget(
      MaterialApp(
        home: PasswordChange(
          requiredAtLogin: true,
          onSave: (current, password, confirmation) async {
            expect(current, isEmpty);
            expect(password, confirmation);
            savedPassword = password;
          },
          onFinished: () => completed = true,
        ),
      ),
    );
    expect(find.text('Mevcut şifre'), findsNothing);
    expect(tester.widget<PopScope>(find.byType(PopScope)).canPop, isFalse);
    final fields = find.byType(TextField);
    expect(fields, findsNWidgets(2));
    await tester.enterText(fields.first, 'Personal-Secure-7189');
    await tester.enterText(fields.last, 'Different-Secure-7189');
    await tester.tap(find.text('Şifreyi yenile').last);
    await tester.pump();
    expect(completed, isFalse);
    expect(find.text('Yeni şifreler birbiriyle eşleşmiyor.'), findsOneWidget);
    await tester.enterText(fields.last, 'Personal-Secure-7189');
    await tester.tap(find.text('Şifreyi yenile').last);
    await tester.pump();
    expect(completed, isTrue);
    expect(savedPassword, 'Personal-Secure-7189');
  });
}
