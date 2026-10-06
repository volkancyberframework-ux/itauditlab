import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:grc_ustasi/main.dart';

void main() {
  testWidgets('completed path offers restart; newly added card reopens it', (
    tester,
  ) async {
    var restarted = false;
    Widget card(bool complete) => MaterialApp(
      home: Scaffold(
        body: PathCard(
          path: {
            'title': 'Demo',
            'question_count': 10,
            'completed': 10,
            'is_complete': complete,
            'remaining_tasks': complete ? 0 : 1,
          },
          onTap: () {},
          onRestart: () => restarted = true,
        ),
      ),
    );
    await tester.pumpWidget(card(true));
    expect(find.text('TAMAMLANDI ✓'), findsOneWidget);
    expect(find.byType(FilledButton), findsNothing);
    expect(tester.widget<IconButton>(find.byType(IconButton)).iconSize, 18);
    await tester.tap(find.byTooltip('Sıfırdan başla'));
    expect(restarted, isTrue);
    await tester.pumpWidget(card(false));
    expect(find.byTooltip('Sıfırdan başla'), findsNothing);
    expect(find.text('DEVAM ET →'), findsOneWidget);
    expect(find.text('1 görev seni bekliyor'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
