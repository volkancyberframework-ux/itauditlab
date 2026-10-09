import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

class ApiFailure implements Exception {
  final String message;
  ApiFailure(this.message);
  @override
  String toString() => message;
}

class Api {
  static const base = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://www.grcustasi.com/api/mobile/v1/',
  );
  final storage = const FlutterSecureStorage();
  final http.Client client;
  Api({http.Client? client}) : client = client ?? http.Client();
  String? access;
  Future<void>? refreshing;
  Future<void> restore() async {
    access = await storage.read(key: 'grc:$base:access');
  }

  Future<void> save(Map<String, dynamic> tokens) async {
    await storage.write(key: 'grc:$base:refresh', value: tokens['refresh']);
    await storage.write(key: 'grc:$base:access', value: tokens['access']);
    access = tokens['access'];
  }

  Future<void> refresh() async {
    final token = await storage.read(key: 'grc:$base:refresh');
    if (token == null) {
      throw ApiFailure('Tekrar giriş yapman gerekiyor.');
    }
    final response = await client
        .post(
          Uri.parse('${base}auth/refresh/'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'refresh': token}),
        )
        .timeout(const Duration(seconds: 15));
    if (response.statusCode != 200) {
      await clear();
      throw ApiFailure('Oturumun sona erdi. Tekrar giriş yapabilirsin.');
    }
    await save(jsonDecode(response.body));
  }

  Future<dynamic> request(
    String path, {
    Map<String, dynamic>? body,
    bool retry = true,
  }) async {
    try {
      final headers = {
        'Content-Type': 'application/json',
        if (access != null) 'Authorization': 'Bearer $access',
      };
      final uri = Uri.parse('$base$path');
      final response =
          await (body == null
                  ? client.get(uri, headers: headers)
                  : client.post(uri, headers: headers, body: jsonEncode(body)))
              .timeout(const Duration(seconds: 20));
      if (response.statusCode == 401 &&
          retry &&
          !['auth/login/', 'auth/register/'].contains(path)) {
        refreshing ??= refresh();
        try {
          await refreshing;
        } finally {
          refreshing = null;
        }
        return request(path, body: body, retry: false);
      }
      if (response.statusCode >= 400) {
        dynamic error;
        try {
          error = jsonDecode(response.body);
        } catch (_) {
          error = null;
        }
        String? message;
        if (error is Map && error['detail'] is String) {
          message = error['detail'];
        } else if (error is List && error.isNotEmpty && error.first is String) {
          message = error.first;
        }
        throw ApiFailure(
          message ?? 'İşlem tamamlanamadı. Tekrar deneyebilirsin.',
        );
      }
      return response.body.isEmpty ? null : jsonDecode(response.body);
    } on ApiFailure {
      rethrow;
    } catch (_) {
      throw ApiFailure('Bağlantını kontrol edip tekrar deneyebilirsin.');
    }
  }

  Future<void> login(String email, String password) async {
    await save(
      await request(
        'auth/login/',
        body: {'email': email, 'password': password},
      ),
    );
  }

  Future<void> clear() async {
    access = null;
    await storage.delete(key: 'grc:$base:access');
    await storage.delete(key: 'grc:$base:refresh');
  }

  Future<void> logout() async {
    final refresh = await storage.read(key: 'grc:$base:refresh');
    await request('auth/logout/', body: {'refresh': refresh});
    await clear();
  }

  Future<dynamic> uploadVoice(
    String session,
    int questionId,
    String file,
    int seconds,
  ) async {
    if (access == null) {
      throw ApiFailure('Tekrar giriş yapmalısın.');
    }
    refreshing ??= refresh();
    try {
      await refreshing;
    } finally {
      refreshing = null;
    }
    try {
      final upload =
          http.MultipartRequest(
              'POST',
              Uri.parse('${Api.base}sessions/$session/voice/'),
            )
            ..headers['Authorization'] = 'Bearer $access'
            ..fields['question_id'] = '$questionId'
            ..fields['duration'] = '$seconds'
            ..files.add(await http.MultipartFile.fromPath('file', file));
      final response = await http.Response.fromStream(
        await client.send(upload).timeout(const Duration(seconds: 40)),
      );
      final data = jsonDecode(response.body);
      if (response.statusCode >= 400) {
        throw ApiFailure(
          data['detail'] ?? 'Ses gönderilemedi. Tekrar deneyebilirsin.',
        );
      }
      return data;
    } on ApiFailure {
      rethrow;
    } catch (_) {
      throw ApiFailure('Ses gönderilemedi. Bağlantını kontrol et.');
    }
  }
}
