import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:just_audio/just_audio.dart';
import 'package:grc_ustasi/api.dart';
import 'package:grc_ustasi/scenario_audio.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets('iOS decodes and plays the real protected scenario audio', (
    tester,
  ) async {
    final api = Api();
    await api.login(
      const String.fromEnvironment('STORE_DEMO_EMAIL'),
      const String.fromEnvironment('STORE_DEMO_PASSWORD'),
    );
    final files = ScenarioAudioFiles(api);
    final player = AudioPlayer();
    try {
      final path = await files.download('${Api.base}audio/1/');
      final duration = await player.setFilePath(path);
      expect(duration, isNotNull);
      expect(duration!.inMilliseconds, greaterThan(1000));
      final completion = player.play();
      await Future<void>.delayed(const Duration(seconds: 2));
      expect(player.position.inMilliseconds, greaterThan(0));
      await player.stop();
      await completion;
    } finally {
      await player.dispose();
      await files.dispose();
      await api.clear();
    }
  });
}
