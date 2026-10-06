import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:grc_ustasi/information_card.dart';
import 'package:grc_ustasi/main.dart';
import 'package:grc_ustasi/theme.dart';

void main() {
  testWidgets('information card reveals detail and swipes before advancing', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(430, 932);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    var continued = 0;
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.create(Brightness.light),
        home: InformationCard(
          question: {
            'prompt': 'Risk',
            'card_pages': [
              {
                'title': 'Neden',
                'body': '**Kontrol** eksikliği ve *neden*.',
                'reveal': 'Biraz daha açıklama.',
              },
              {'title': 'Etki', 'body': 'Somut iş etkisi.'},
            ],
          },
          pathTitle: 'Demo',
          answered: 3,
          total: 11,
          onContinue: () async {
            continued++;
          },
        ),
      ),
    );
    expect(find.text('BİLGİ KARTI'), findsOneWidget);
    expect(continued, 0);
    await tester.tap(find.text('Biraz daha öğren'));
    await tester.pumpAndSettle();
    expect(find.text('Biraz daha açıklama.'), findsOneWidget);
    await tester.drag(find.byType(PageView), const Offset(-350, 0));
    await tester.pumpAndSettle();
    expect(find.text('Etki'), findsOneWidget);
    expect(continued, 0);
    await tester.drag(find.byType(PageView), const Offset(-350, 0));
    await tester.pumpAndSettle();
    expect(continued, 1);
    expect(tester.takeException(), isNull);
  });
  testWidgets('large paths have fixed height and accurate progress', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(430, 932);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    Widget card(int count, int completed) => MaterialApp(
      theme: AppTheme.create(Brightness.light),
      home: Scaffold(
        body: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            PathCard(
              path: {
                'title': 'GRC yolu',
                'description': 'Her gün kısa adımlarla öğren.',
                'question_count': count,
                'completed': completed,
                'information_count': 3,
              },
              onTap: () {},
            ),
          ],
        ),
      ),
    );
    await tester.pumpWidget(card(10, 4));
    final height = tester.getSize(find.byType(Card)).height;
    expect(height, lessThan(300));
    await tester.pumpWidget(card(250, 100));
    expect(tester.getSize(find.byType(Card)).height, height);
    expect(find.text('100 / 250 soru • %40'), findsOneWidget);
    expect(
      tester
          .widget<LinearProgressIndicator>(find.byType(LinearProgressIndicator))
          .value,
      .4,
    );
    expect(tester.takeException(), isNull);
  });
  testWidgets('login offers free signup with name and new password', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.create(Brightness.light),
        home: Login(onLogin: () {}),
      ),
    );
    final signup = find.text('Yeni misin? Ücretsiz hesap oluştur');
    await tester.ensureVisible(signup);
    await tester.tap(signup);
    await tester.pumpAndSettle();
    expect(find.text('Ad soyad'), findsOneWidget);
    expect(find.text('Ücretsiz Hesap Oluştur'), findsOneWidget);
    expect(
      tester.widgetList<TextField>(find.byType(TextField)).last.autofillHints,
      contains(AutofillHints.newPassword),
    );
  });
}
