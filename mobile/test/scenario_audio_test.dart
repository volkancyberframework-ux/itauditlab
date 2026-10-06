import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:grc_ustasi/api.dart';
import 'package:grc_ustasi/scenario_audio.dart';

void main() {
  test(
    'authorized audio is downloaded to a typed private file and cleaned up',
    () async {
      final root = await Directory.systemTemp.createTemp('grc-audio-test-');
      addTearDown(() => root.delete(recursive: true));
      final api = Api(
        client: MockClient((request) async {
          expect(request.headers['Authorization'], 'Bearer private-test-token');
          expect(request.followRedirects, isFalse);
          return http.Response.bytes(
            [1, 2, 3],
            200,
            headers: {'content-type': 'audio/mp4'},
          );
        }),
      )..access = 'private-test-token';
      final files = ScenarioAudioFiles(
        api,
        temporaryDirectory: () async => root,
      );
      final path = await files.download('${Api.base}audio/1/');
      expect(path.endsWith('.m4a'), isTrue);
      expect(await File(path).readAsBytes(), [1, 2, 3]);
      await files.dispose();
      expect(await File(path).exists(), isFalse);
    },
  );
  test(
    'other origins and paths never receive an authentication token',
    () async {
      int calls = 0;
      final api = Api(
        client: MockClient((_) async {
          calls++;
          return http.Response('', 200);
        }),
      );
      final files = ScenarioAudioFiles(api);
      await expectLater(
        files.download('https://example.com/audio/1/'),
        throwsA(isA<ApiFailure>()),
      );
      await expectLater(
        files.download('${Api.base}profile/'),
        throwsA(isA<ApiFailure>()),
      );
      expect(calls, 0);
    },
  );
  test('missing and HTML responses cannot be played as audio', () async {
    for (final status in [404, 200]) {
      final files = ScenarioAudioFiles(
        Api(
          client: MockClient(
            (_) async => http.Response(
              '<html/>',
              status,
              headers: {'content-type': 'text/html'},
            ),
          ),
        ),
      );
      await expectLater(
        files.download('${Api.base}audio/1/'),
        throwsA(isA<ApiFailure>()),
      );
      await files.dispose();
    }
  });
}
