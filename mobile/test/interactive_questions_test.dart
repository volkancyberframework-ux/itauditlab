import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:grc_ustasi/interactive_questions.dart';
import 'package:grc_ustasi/theme.dart';

void main() {
  const options = [
    {'id': 'a', 'text': 'Neden parçası'},
    {'id': 'b', 'text': 'Olay parçası'},
    {'id': 'c', 'text': 'Etki parçası'},
  ];
  testWidgets('sentence pieces can be tapped, dragged and removed', (
    tester,
  ) async {
    var value = <String>[];
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.create(Brightness.light),
        home: Scaffold(
          body: SingleChildScrollView(
            child: StatefulBuilder(
              builder: (context, setState) => SentenceBuilder(
                options: options,
                value: value,
                enabled: true,
                onChanged: (v) => setState(() => value = v),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('Neden parçası'));
    await tester.pumpAndSettle();
    expect(value, ['a']);
    final gesture = await tester.startGesture(
      tester.getCenter(
        find.descendant(
          of: find
              .ancestor(
                of: find.text('Olay parçası'),
                matching: find.byType(InkWell),
              )
              .first,
          matching: find.byType(Draggable<String>),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 30));
    await gesture.moveTo(tester.getCenter(find.byType(DragTarget<String>)));
    await tester.pump();
    await gesture.up();
    await tester.pumpAndSettle();
    expect(value, ['a', 'b']);
    await tester.tap(find.byTooltip('Parçayı geri al').first);
    await tester.pumpAndSettle();
    expect(value, ['b']);
    expect(tester.takeException(), isNull);
  });
  testWidgets('risk cards swipe and drag into the risk area', (tester) async {
    var value = <String>[];
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.create(Brightness.light),
        home: Scaffold(
          body: StatefulBuilder(
            builder: (context, setState) => DragRiskQuestion(
              options: options,
              value: value,
              enabled: true,
              onChanged: (v) => setState(() => value = v),
            ),
          ),
        ),
      ),
    );
    await tester.drag(find.byType(PageView), const Offset(-600, 0));
    await tester.pumpAndSettle();
    expect(find.text('2 / 3'), findsOneWidget);
    final gesture = await tester.startGesture(
      tester.getCenter(
        find.descendant(
          of: find
              .ancestor(
                of: find.text('Olay parçası'),
                matching: find.byType(InkWell),
              )
              .first,
          matching: find.byType(Draggable<String>),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 30));
    await gesture.moveTo(tester.getCenter(find.byType(DragTarget<String>)));
    await tester.pump();
    await gesture.up();
    await tester.pumpAndSettle();
    expect(value, ['b']);
    await tester.tap(find.text('Seçimi değiştir'));
    await tester.pumpAndSettle();
    expect(value, isEmpty);
    final visibleCard = find
        .ancestor(of: find.text('Olay parçası'), matching: find.byType(InkWell))
        .first;
    await tester.tapAt(tester.getTopLeft(visibleCard) + const Offset(8, 8));
    await tester.pumpAndSettle();
    expect(value, ['b']);
    expect(tester.takeException(), isNull);
  });
}
