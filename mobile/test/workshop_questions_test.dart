import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:grc_ustasi/api.dart';
import 'package:grc_ustasi/workshop_questions.dart';

void main() {
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
    test('$kind works without an account and saves local result', () async {
      SharedPreferences.setMockInitialValues({});
      final q = {
        'id': 1,
        'kind': kind,
        'prompt': 'Soru',
        'answer': ['a', 'b'],
        'explanation': 'Açıklama',
        'hint': '',
      };
      final api = WorkshopQuestionApi(q);
      expect((await api.request('sessions/', body: {}))['question'], q);
      if (kind == 'info') {
        expect(
          (await api.request('sessions/id/continue/', body: {}))['complete'],
          true,
        );
      } else {
        final value = ['text', 'fill_blank', 'voice'].contains(kind)
            ? ' A '
            : ['a', 'b'];
        final response = await api.request(
          'sessions/id/answer/',
          body: {'answer': value},
        );
        expect(response['correct'], true);
        expect(response['practice'], true);
        expect(response['xp_change'], 0);
      }
      final prefs = await SharedPreferences.getInstance();
      expect(
        (jsonDecode(prefs.getString('grc.practice.history.v1')!) as List)
            .single['total'],
        1,
      );
      api.client.close();
    });
  }
  test(
    'voice upload uses public multipart endpoint through Api polymorphism',
    () async {
      SharedPreferences.setMockInitialValues({});
      final file = File(
        '${Directory.systemTemp.path}/grc-workshop-upload-test.m4a',
      );
      await file.writeAsBytes([
        0,
        0,
        0,
        24,
        102,
        116,
        121,
        112,
        77,
        52,
        65,
        32,
      ]);
      final guest = WorkshopQuestionApi(
        {'id': 9, 'kind': 'voice', 'voice_token': 'signed', 'prompt': 'Soru'},
        client: MockClient((request) async {
          expect(request.url.path, endsWith('/workshop/questions/9/voice/'));
          expect(request.headers.containsKey('Authorization'), false);
          expect(request.body, contains('learner@example.com'));
          return http.Response(
            '{"detail":"Alındı"}',
            200,
            headers: {'content-type': 'application/json; charset=utf-8'},
          );
        }),
      );
      final Api client = guest;
      await expectLater(
        client.uploadVoice('id', 9, file.path, 3),
        throwsA(isA<ApiFailure>()),
      );
      guest.email = 'learner@example.com';
      final result = await client.uploadVoice('id', 9, file.path, 3);
      expect(result['session']['pending_reviews'], 1);
      guest.client.close();
      await file.delete();
    },
  );
}
