import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:grc_ustasi/main.dart';
import 'package:grc_ustasi/theme.dart';

void main() {
  testWidgets('login exposes email and obscured password with submit action', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.create(Brightness.light),
        home: Login(onLogin: () {}),
      ),
    );
    expect(find.text('E-posta'), findsOneWidget);
    expect(find.text('Şifre'), findsOneWidget);
    expect(
      tester.widgetList<TextField>(find.byType(TextField)).last.obscureText,
      isTrue,
    );
    expect(find.text('Giriş Yap'), findsOneWidget);
  });
}
