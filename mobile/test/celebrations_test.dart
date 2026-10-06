import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:grc_ustasi/celebrations.dart';

void main() {
  test('celebrations vary and never repeat consecutively', () {
    final seen = <CelebrationKind>{};
    CelebrationKind? previous;
    for (var i = 0; i < 100; i++) {
      final next = CelebrationPicker.next();
      expect(next, isNot(previous));
      seen.add(next);
      previous = next;
    }
    expect(seen.length, 4);
  });
  testWidgets('all celebrations render and respect reduced motion', (
    tester,
  ) async {
    for (final reduced in [false, true]) {
      for (final kind in CelebrationKind.values) {
        await tester.pumpWidget(
          MaterialApp(
            home: MediaQuery(
              data: MediaQueryData(disableAnimations: reduced),
              child: CelebrationOverlay(
                key: ValueKey('$kind-$reduced'),
                kind: kind,
              ),
            ),
          ),
        );
        await tester.pump(const Duration(milliseconds: 500));
        expect(tester.takeException(), isNull);
        await tester.pumpWidget(const SizedBox());
      }
    }
  });
}
