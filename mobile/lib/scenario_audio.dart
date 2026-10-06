import 'dart:io';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'api.dart';

/// Private HTTPS downloads avoid the player's localhost header proxy on iOS.
class ScenarioAudioFiles {
  final Api api;
  final Future<Directory> Function() temporaryDirectory;
  Directory? _directory;
  bool _disposed = false;
  ScenarioAudioFiles(
    this.api, {
    Future<Directory> Function()? temporaryDirectory,
  }) : temporaryDirectory = temporaryDirectory ?? getTemporaryDirectory;

  Future<String> download(String url, {bool retry = true}) async {
    final uri = Uri.parse(url);
    final base = Uri.parse(Api.base);
    if (uri.origin != base.origin ||
        !uri.path.startsWith('${base.path}audio/')) {
      throw ApiFailure('Ses adresi geçersiz.');
    }
    final request = http.Request('GET', uri)..followRedirects = false;
    request.headers['Authorization'] = 'Bearer ${api.access}';
    final response = await api.client
        .send(request)
        .timeout(const Duration(seconds: 20));
    if (response.statusCode == 401 && retry) {
      await response.stream.drain();
      await api.refresh();
      return download(url, retry: false);
    }
    if (response.statusCode != 200) {
      await response.stream.drain();
      throw ApiFailure('Ses yüklenemedi. Tekrar deneyebilirsin.');
    }
    final type = response.headers['content-type']?.split(';').first.trim();
    final extension = {
      'audio/mp4': 'm4a',
      'audio/x-m4a': 'm4a',
      'audio/mpeg': 'mp3',
      'audio/wav': 'wav',
      'audio/x-wav': 'wav',
      'audio/aac': 'aac',
      'audio/ogg': 'ogg',
    }[type];
    if (extension == null) {
      await response.stream.drain();
      throw ApiFailure('Ses dosyasının biçimi desteklenmiyor.');
    }
    final bytes = BytesBuilder(copy: false);
    await for (final chunk in response.stream.timeout(
      const Duration(seconds: 20),
    )) {
      if (bytes.length + chunk.length > 20 * 1024 * 1024) {
        throw ApiFailure('Ses dosyası çok büyük.');
      }
      bytes.add(chunk);
    }
    if (bytes.isEmpty || _disposed) {
      throw ApiFailure('Ses yüklenemedi.');
    }
    if (_directory == null) {
      final root = await temporaryDirectory();
      _directory = await root.createTemp('grc-scenario-');
    }
    if (_disposed) {
      await clear();
      throw ApiFailure('Görev kapatıldı.');
    }
    final file = File(
      '${_directory!.path}/${DateTime.now().microsecondsSinceEpoch}.$extension',
    );
    await file.writeAsBytes(bytes.takeBytes(), flush: true);
    if (_disposed) {
      await clear();
      throw ApiFailure('Görev kapatıldı.');
    }
    return file.path;
  }

  Future<void> clear() async {
    final directory = _directory;
    _directory = null;
    if (directory != null && await directory.exists()) {
      await directory.delete(recursive: true);
    }
  }

  Future<void> dispose() async {
    _disposed = true;
    await clear();
  }
}
