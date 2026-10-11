import 'package:http/http.dart' as http;
import 'package:web/web.dart' as web;

Future<String> recordingPath() async => 'grc-recording.wav';
Future<void> deleteRecording(String path) async {
  if (path.startsWith('blob:')) web.URL.revokeObjectURL(path);
}

Future<http.MultipartFile> recordingUpload(String path) async {
  final response = await http.get(Uri.parse(path));
  if (response.statusCode != 200 ||
      response.bodyBytes.length > 10 * 1024 * 1024) {
    throw StateError('Ses kaydı okunamadı.');
  }
  return http.MultipartFile.fromBytes(
    'file',
    response.bodyBytes,
    filename: 'recording.wav',
  );
}
