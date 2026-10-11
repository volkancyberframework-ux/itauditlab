@TestOn('browser')
library;

import 'dart:js_interop';
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:web/web.dart' as web;
import 'package:grc_ustasi/api.dart';
import 'package:grc_ustasi/scenario_audio_web.dart';
import 'package:grc_ustasi/recording_file_web.dart';

void main() {
  test(
    'browser recording blob becomes multipart bytes and is revoked',
    () async {
      final bytes = Uint8List.fromList([
        82,
        73,
        70,
        70,
        0,
        0,
        0,
        0,
        87,
        65,
        86,
        69,
      ]);
      final blob = web.Blob([bytes.toJS].toJS);
      final url = web.URL.createObjectURL(blob);
      final upload = await recordingUpload(url);
      expect(upload.filename, 'recording.wav');
      expect(await upload.finalize().toBytes(), bytes);
      await deleteRecording(url);
    },
  );
  test(
    'protected audio downloads as playable data URI without exposing token',
    () async {
      final api = Api(
        client: MockClient((request) async {
          expect(request.headers['Authorization'], 'Bearer local-test');
          return http.Response.bytes(
            [0, 0, 0, 24, 102, 116, 121, 112],
            200,
            headers: {'content-type': 'audio/mp4'},
          );
        }),
      )..access = 'local-test';
      final files = ScenarioAudioFiles(api);
      final uri = await files.download('${Api.base}audio/1/');
      expect(uri.startsWith('data:audio/mp4'), isTrue);
      expect(uri.contains('local-test'), isFalse);
      await files.dispose();
    },
  );
}
