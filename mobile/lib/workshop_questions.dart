import 'dart:convert';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'api.dart';
import 'main.dart';

class WorkshopQuestionApi extends Api {
  final Map<String, dynamic> question;
  String email = '';
  final String submissionId;
  bool complete = false;
  bool correct = false;
  bool pending = false;
  WorkshopQuestionApi(this.question, {super.client}) : submissionId = _uuid();

  static String _uuid() {
    final bytes = List<int>.generate(16, (_) => Random.secure().nextInt(256));
    bytes[6] = (bytes[6] & 15) | 64;
    bytes[8] = (bytes[8] & 63) | 128;
    final h = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    return '${h.substring(0, 8)}-${h.substring(8, 12)}-${h.substring(12, 16)}-${h.substring(16, 20)}-${h.substring(20)}';
  }

  Map<String, dynamic> state() => {
    'id': submissionId,
    'question': complete ? null : question,
    'complete': complete,
    'answered': complete ? 1 : 0,
    'total': 1,
    'question_total': question['kind'] == 'info' ? 0 : 1,
    'information_read': complete && question['kind'] == 'info' ? 1 : 0,
    'correct': correct ? 1 : 0,
    'pending_reviews': pending ? 1 : 0,
    'xp_earned': 0,
    'path': {'progress': complete ? 100 : 0},
  };

  Future<void> saveResult() async {
    final prefs = await SharedPreferences.getInstance();
    List<dynamic> history;
    try {
      history =
          jsonDecode(prefs.getString('grc.practice.history.v1') ?? '[]')
              as List;
    } catch (_) {
      history = [];
    }
    history.add({
      'case': 'question-${question['id']}',
      'title': question['prompt'],
      'score': correct ? 1 : 0,
      'total': 1,
      'summary': pending ? 'Sesli yanıt incelemede.' : question['explanation'],
      'date': DateTime.now().toIso8601String(),
    });
    await prefs.setString(
      'grc.practice.history.v1',
      jsonEncode(history.reversed.take(100).toList().reversed.toList()),
    );
  }

  @override
  Future<dynamic> request(
    String path, {
    Map<String, dynamic>? body,
    bool retry = true,
  }) async {
    if (path == 'sessions/') return state();
    if (path.endsWith('/continue/')) {
      complete = true;
      await saveResult();
      return state();
    }
    if (!path.endsWith('/answer/')) throw ApiFailure('Atölye işlemi geçersiz.');
    final answer = body!['answer'];
    final expected = List<dynamic>.from(question['answer']);
    if (['text', 'fill_blank', 'voice'].contains(question['kind'])) {
      correct = expected.any(
        (e) =>
            e.toString().trim().toLowerCase() ==
            answer.toString().trim().toLowerCase(),
      );
    } else if (question['kind'] == 'sentence_order') {
      correct = jsonEncode(answer) == jsonEncode(expected);
    } else {
      final actual = Set<String>.from(answer as List);
      final target = expected.map((e) => e.toString()).toSet();
      correct =
          actual.isNotEmpty &&
          actual.length == target.length &&
          actual.containsAll(target);
    }
    complete = true;
    await saveResult();
    return {
      'correct': correct,
      'practice': true,
      'xp_change': 0,
      'explanation': question['explanation'],
      'hint': question['hint'],
      'session': state(),
    };
  }

  @override
  Future<dynamic> uploadVoice(
    String session,
    int questionId,
    String file,
    int seconds,
  ) async {
    if (!RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$').hasMatch(email.trim())) {
      throw ApiFailure('Geri bildirim için geçerli e-posta adresini yaz.');
    }
    final upload =
        http.MultipartRequest(
            'POST',
            Uri.parse('${Api.base}workshop/questions/$questionId/voice/'),
          )
          ..fields['email'] = email.trim()
          ..fields['token'] = question['voice_token']
          ..fields['submission_id'] = submissionId
          ..fields['duration'] = '$seconds'
          ..files.add(await http.MultipartFile.fromPath('file', file));
    final response = await http.Response.fromStream(
      await client.send(upload).timeout(const Duration(seconds: 40)),
    );
    final data = jsonDecode(response.body);
    if (response.statusCode != 200) {
      throw ApiFailure(
        data['detail']?.toString() ??
            'Ses gönderilemedi. Tekrar deneyebilirsin.',
      );
    }
    complete = true;
    pending = true;
    await saveResult();
    return {'detail': data['detail'], 'session': state()};
  }
}

class WorkshopQuestionList extends StatefulWidget {
  final VoidCallback? onCompleted;
  const WorkshopQuestionList({super.key, this.onCompleted});
  @override
  State<WorkshopQuestionList> createState() => _WorkshopQuestionListState();
}

class _WorkshopQuestionListState extends State<WorkshopQuestionList> {
  List<dynamic> questions = [];
  final catalogApi = Api();
  @override
  void initState() {
    super.initState();
    load();
  }

  @override
  void dispose() {
    catalogApi.client.close();
    super.dispose();
  }

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    try {
      final cached =
          jsonDecode(prefs.getString('grc.workshop.questions.v1') ?? '[]')
              as List;
      if (mounted) setState(() => questions = cached);
    } catch (_) {
      /* Corrupt cache is ignored. */
    }
    try {
      final data = await catalogApi.request('workshop/questions/') as List;
      await prefs.setString('grc.workshop.questions.v1', jsonEncode(data));
      if (mounted) setState(() => questions = data);
    } catch (_) {
      /* Last selected questions remain usable offline. */
    }
  }

  @override
  Widget build(BuildContext context) => Column(
    children: [
      for (final q in questions)
        Card(
          child: ListTile(
            leading: Icon(
              q['kind'] == 'voice' || q['kind'] == 'audio'
                  ? Icons.mic_rounded
                  : Icons.quiz_outlined,
            ),
            title: Text(q['prompt']),
            subtitle: Text(
              q['kind'] == 'info' ? 'Bilgi kartı' : 'Alıştırmayı aç',
            ),
            trailing: const Icon(Icons.chevron_right),
            onTap: () async {
              final sessionApi = WorkshopQuestionApi(
                Map<String, dynamic>.from(q),
              );
              try {
                await Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => Session(
                      path: {
                        'id': q['id'],
                        'title': 'Vaka atölyesi',
                        'session_size': 1,
                      },
                      sessionApi: sessionApi,
                      workshop: true,
                    ),
                  ),
                );
              } finally {
                if (mounted) widget.onCompleted?.call();
                sessionApi.client.close();
              }
            },
          ),
        ),
    ],
  );
}
