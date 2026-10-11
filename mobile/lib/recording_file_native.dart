import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';

Future<String> recordingPath() async =>
    '${(await getTemporaryDirectory()).path}/grc_${DateTime.now().millisecondsSinceEpoch}.m4a';
Future<void> deleteRecording(String path) async {
  final file = File(path);
  if (await file.exists()) await file.delete();
}

Future<http.MultipartFile> recordingUpload(String path) =>
    http.MultipartFile.fromPath('file', path);
