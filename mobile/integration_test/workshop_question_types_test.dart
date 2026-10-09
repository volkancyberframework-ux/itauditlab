import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:grc_ustasi/main.dart';
import 'package:grc_ustasi/api.dart';
import 'package:grc_ustasi/workshop_questions.dart';
import 'package:grc_ustasi/theme.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets('All eleven native question screens open before login', (
    tester,
  ) async {
    SharedPreferences.setMockInitialValues({});
    for (final kind in [
      'choice',
      'multi_select',
      'fill_blank',
      'text',
      'image',
      'audio',
      'scenario',
      'voice',
      'sentence_order',
      'drag_select',
      'info',
    ]) {
      final q = {
        'id': 1,
        'kind': kind,
        'prompt': 'Atölye $kind',
        'context': 'Vaka açıklaması',
        'options': [
          {'id': 'a', 'text': 'Birinci'},
          {'id': 'b', 'text': 'İkinci'},
        ],
        'answer': ['a'],
        'audio': kind == 'audio'
            ? ['${Api.base}workshop/questions/1/audio/1/']
            : [],
        'image': null,
        'explanation': 'Doğru karar açıklaması',
        'hint': 'İpucu',
        'card_pages': [
          {
            'title': 'Bilgi başlığı',
            'body': '**Öğrenelim**',
            'reveal': 'Detay',
          },
        ],
      };
      final guest = WorkshopQuestionApi(q);
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.create(Brightness.light),
          home: Session(
            path: {'id': 1, 'title': 'Vaka atölyesi'},
            sessionApi: guest,
            workshop: true,
          ),
        ),
      );
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.text('Başla'));
      await tester.tap(find.text('Başla'));
      await tester.pumpAndSettle();
      expect(
        find.text(kind == 'info' ? 'Bilgi başlığı' : 'Atölye $kind'),
        findsOneWidget,
      );
      if (kind == 'voice') {
        await tester.ensureVisible(find.text('🎙️ Sesli yanıtla'));
        await tester.tap(find.text('🎙️ Sesli yanıtla'));
        await tester.pumpAndSettle();
        expect(find.text('Geri bildirim e-postan'), findsOneWidget);
      }
      await tester.pumpWidget(const SizedBox());
      await tester.pumpAndSettle();
      guest.client.close();
    }
  });
}
