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
      tester.getCenter(find.text('Olay parçası')),
    );
    await tester.pump(const Duration(milliseconds: 30));
    await gesture.moveTo(tester.getCenter(find.byType(DragTarget<String>)));
    await tester.pump();
    await gesture.up();
    await tester.pumpAndSettle();
    expect(value, ['a', 'b']);
    final fromRow = tester.getCenter(find.text('1. Neden parçası'));
    final toRow =
        tester.getCenter(find.text('2. Olay parçası')) + const Offset(0, 30);
    final reorder = await tester.startGesture(fromRow);
    for (var step = 1; step <= 10; step++) {
      await reorder.moveTo(Offset.lerp(fromRow, toRow, step / 10)!);
      await tester.pump(const Duration(milliseconds: 30));
    }
    await tester.pump(const Duration(milliseconds: 300));
    await reorder.up();
    await tester.pumpAndSettle();
    expect(value, ['b', 'a']);

    await tester.tap(find.byTooltip('Parçayı geri al').first);
    await tester.pumpAndSettle();
    expect(value, ['a']);
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
      tester.getCenter(find.text('Olay parçası')),
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
  testWidgets(
    'finger gestures on card body work inside a phone-sized scrolling page',
    (tester) async {
      tester.view.devicePixelRatio = 1;
      tester.view.physicalSize = const Size(430, 932);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final scroll = ScrollController();
      addTearDown(scroll.dispose);
      var value = <String>[];
      var dragging = false;
      var dragStarts = 0;
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.create(Brightness.light),
          home: Scaffold(
            appBar: AppBar(title: const Text('Risk senaryosu')),
            body: StatefulBuilder(
              builder: (context, setState) => ListView(
                controller: scroll,
                physics: dragging ? const NeverScrollableScrollPhysics() : null,
                padding: const EdgeInsets.all(24),
                children: [
                  const SizedBox(
                    height: 140,
                    child: Text('Senaryo ve risk açıklaması'),
                  ),
                  DragRiskQuestion(
                    options: options,
                    value: value,
                    enabled: true,
                    onChanged: (v) => setState(() => value = v),
                    onDragStart: () {
                      dragStarts++;
                      setState(() => dragging = true);
                    },
                    onDragEnd: () => setState(() => dragging = false),
                  ),
                  const SizedBox(height: 500),
                ],
              ),
            ),
          ),
        ),
      );
      final swipe = await tester.startGesture(
        tester.getCenter(find.text('Neden parçası')),
      );
      for (var step = 0; step < 12; step++) {
        await swipe.moveBy(const Offset(-20, 1));
        await tester.pump(const Duration(milliseconds: 16));
      }
      await swipe.up();
      await tester.pumpAndSettle();
      expect(find.text('2 / 3'), findsOneWidget);
      expect(dragStarts, 0);
      final from = tester.getCenter(find.text('Olay parçası'));
      final to = tester.getCenter(find.byType(DragTarget<String>));
      final gesture = await tester.startGesture(from);
      for (var step = 1; step <= 15; step++) {
        await gesture.moveTo(Offset.lerp(from, to, step / 15)!);
        await tester.pump(const Duration(milliseconds: 16));
      }
      expect(dragStarts, 1);
      expect(scroll.offset, 0);
      await gesture.up();
      await tester.pumpAndSettle();
      expect(value, ['b']);
      expect(dragging, false);
      expect(tester.takeException(), isNull);
    },
  );
}
