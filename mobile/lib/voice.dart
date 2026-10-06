import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import 'theme.dart';

class VoiceRecorder extends StatefulWidget {
  final Future<void> Function(String, int) onSubmit;
  const VoiceRecorder({super.key, required this.onSubmit});
  @override
  State<VoiceRecorder> createState() => _VoiceRecorderState();
}

class _VoiceRecorderState extends State<VoiceRecorder> {
  final recorder = AudioRecorder();
  Timer? timer;
  String? file;
  String? error;
  int seconds = 0;
  bool recording = false;
  bool paused = false;
  bool sending = false;
  @override
  void dispose() {
    timer?.cancel();
    recorder.dispose();
    if (file != null) {
      File(file!).delete().catchError((_) => File(file!));
    }
    super.dispose();
  }

  Future<void> start() async {
    try {
      if (!await recorder.hasPermission()) {
        throw Exception('Sesli yanıt için mikrofon izni gerekli.');
      }
      final directory = await getTemporaryDirectory();
      file =
          '${directory.path}/grc_${DateTime.now().millisecondsSinceEpoch}.m4a';
      await recorder.start(
        const RecordConfig(encoder: AudioEncoder.aacLc),
        path: file!,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        recording = true;
        seconds = 0;
        error = null;
      });
      timer = Timer.periodic(const Duration(seconds: 1), (_) {
        if (!paused && mounted) {
          setState(() => seconds++);
        }
        if (seconds >= 180) {
          stop();
        }
      });
    } catch (e) {
      if (mounted) {
        setState(() => error = '$e');
      }
    }
  }

  Future<void> stop() async {
    timer?.cancel();
    await recorder.stop();
    if (mounted) {
      setState(() {
        recording = false;
        paused = false;
      });
    }
  }

  Future<void> cancel() async {
    await stop();
    if (file != null) {
      await File(file!).delete().catchError((_) => File(file!));
    }
    if (mounted) {
      setState(() {
        file = null;
        seconds = 0;
      });
    }
  }

  @override
  Widget build(BuildContext context) => Column(
    children: [
      Text('🎙️ ${seconds ~/ 60}:${(seconds % 60).toString().padLeft(2, '0')}'),
      if (recording)
        StreamBuilder<Amplitude>(
          stream: recorder.onAmplitudeChanged(
            const Duration(milliseconds: 120),
          ),
          builder: (_, s) => LinearProgressIndicator(
            value: (((s.data?.current ?? -60) + 60) / 60).clamp(0, 1),
          ),
        ),
      const SizedBox(height: 16),
      if (file == null)
        PrimaryButton(label: 'Sesli Yanıtla', onPressed: start)
      else ...[
        if (recording)
          OutlinedButton(
            onPressed: () async {
              if (paused) {
                await recorder.resume();
              } else {
                await recorder.pause();
              }
              if (mounted) {
                setState(() => paused = !paused);
              }
            },
            child: Text(paused ? 'Kayda devam et' : 'Duraklat'),
          ),
        PrimaryButton(
          label: 'Yanıtımı gönder',
          busy: sending,
          onPressed: seconds == 0
              ? null
              : () async {
                  await stop();
                  setState(() => sending = true);
                  try {
                    await widget.onSubmit(file!, seconds);
                  } catch (e) {
                    if (mounted) {
                      setState(() => error = '$e');
                    }
                  } finally {
                    if (mounted) {
                      setState(() => sending = false);
                    }
                  }
                },
        ),
        TextButton(
          onPressed: sending ? null : cancel,
          child: const Text('Kaydı iptal et'),
        ),
      ],
      if (error != null) Text(error!),
    ],
  );
}
