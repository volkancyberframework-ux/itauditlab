import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:grc_ustasi/daily_activity.dart';
import 'package:grc_ustasi/learning_experience.dart';

void main() {
  testWidgets(
    'daily chart selects real records and supports 28 days on small phone',
    (tester) async {
      tester.view.physicalSize = const Size(320, 740);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final days = List.generate(
        28,
        (i) => {
          'date': '2026-10-${(i + 1).toString().padLeft(2, '0')}',
          'tasks': i == 27 ? 3 : 0,
          'xp': i == 27 ? 30 : 0,
        },
      );
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: DailyActivityChart(
                activity: {
                  'days': days,
                  'streak': 1,
                  'active_days': 1,
                  'today_tasks': 3,
                },
              ),
            ),
          ),
        ),
      );
      expect(find.textContaining('Bugün 3 görev'), findsOneWidget);
      await tester.tap(find.byType(GestureDetector).last);
      await tester.pump();
      expect(find.text('2026-10-28 • 3 görev • 30 XP'), findsOneWidget);
      await tester.tap(find.text('28 gün'));
      await tester.pump();
      expect(find.textContaining('Bugün 3 görev'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets('learning introduction fits a small phone with enlarged text', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 740);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      MaterialApp(
        home: MediaQuery(
          data: const MediaQueryData(textScaler: TextScaler.linear(1.3)),
          child: const Scaffold(
            body: SingleChildScrollView(child: LearningExperience()),
          ),
        ),
      ),
    );
    expect(tester.takeException(), isNull);
    expect(find.byType(RichText), findsWidgets);
  });
}
