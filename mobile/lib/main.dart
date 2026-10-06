import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:just_audio/just_audio.dart';
import 'api.dart';
import 'theme.dart';
import 'voice.dart';
import 'paywall.dart';
import 'analytics.dart';
import 'answer_feedback.dart';
import 'dashboard_widgets.dart';
import 'interactive_questions.dart';
import 'level_rewards.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const GrcApp());
}

final api = Api();
final analytics = Analytics(api);

class GrcApp extends StatelessWidget {
  const GrcApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'GRC Ustası',
    debugShowCheckedModeBanner: false,
    theme: AppTheme.create(Brightness.light),
    darkTheme: AppTheme.create(Brightness.dark),
    home: const Entry(),
  );
}

class Entry extends StatefulWidget {
  const Entry({super.key});
  @override
  State<Entry> createState() => _EntryState();
}

class _EntryState extends State<Entry> {
  bool ready = false;
  bool authenticated = false;
  @override
  void initState() {
    super.initState();
    boot();
  }

  Future<void> boot() async {
    await Future.wait([
      api.restore(),
      Future<void>.delayed(const Duration(milliseconds: 1400)),
    ]);
    if (mounted) {
      setState(() {
        ready = true;
        authenticated = api.access != null;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!ready) {
      return Scaffold(
        body: Center(
          child: TweenAnimationBuilder<double>(
            tween: Tween(begin: 0, end: 1),
            duration: const Duration(seconds: 1),
            builder: (_, v, child) => Opacity(
              opacity: v,
              child: Transform.scale(scale: .9 + .1 * v, child: child),
            ),
            child: Image.asset('assets/logo.png', width: 200),
          ),
        ),
      );
    }
    return authenticated
        ? Home(onLogout: () => setState(() => authenticated = false))
        : Login(onLogin: () => setState(() => authenticated = true));
  }
}

class Login extends StatefulWidget {
  final VoidCallback onLogin;
  const Login({super.key, required this.onLogin});
  @override
  State<Login> createState() => _LoginState();
}

class _LoginState extends State<Login> {
  final email = TextEditingController();
  final password = TextEditingController();
  bool busy = false;
  String? error;
  @override
  void dispose() {
    email.dispose();
    password.dispose();
    super.dispose();
  }

  Future<void> submit() async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await api.login(email.text.trim(), password.text);
      password.clear();
      analytics.emit('login_completed');
      if (mounted) {
        widget.onLogin();
      }
    } catch (e) {
      if (mounted) {
        setState(() => error = '$e');
      }
    } finally {
      if (mounted) {
        setState(() => busy = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(28),
          child: AutofillGroup(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Center(
                  child: Image.asset(
                    'assets/logo.png',
                    width: 200,
                    height: 200,
                  ),
                ),
                const SizedBox(height: 16),
                const Center(
                  child: Text(
                    'UZMANLIĞA GİDEN YOL',
                    style: TextStyle(
                      color: AppColors.teal,
                      letterSpacing: 2,
                      fontWeight: FontWeight.w900,
                      fontSize: 11,
                    ),
                  ),
                ),
                const SizedBox(height: 28),
                Text(
                  'Küçük adımlar.\nGüçlü uzmanlık.',
                  style: Theme.of(context).textTheme.headlineLarge?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 14),
                const Text('GRC Ustası hesabınla öğrenmeye devam et.'),
                const SizedBox(height: 32),
                TextField(
                  controller: email,
                  keyboardType: TextInputType.emailAddress,
                  autofillHints: const [AutofillHints.username],
                  decoration: const InputDecoration(labelText: 'E-posta'),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: password,
                  obscureText: true,
                  autofillHints: const [AutofillHints.password],
                  decoration: const InputDecoration(labelText: 'Şifre'),
                  onSubmitted: (_) => busy ? null : submit(),
                ),
                const SizedBox(height: 24),
                if (error != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: Text(error!),
                  ),
                TextButton(
                  onPressed: busy
                      ? null
                      : () async {
                          try {
                            final result = await api.request(
                              'auth/password-reset/',
                              body: {'email': email.text.trim()},
                            );
                            if (mounted) {
                              setState(() => error = result['detail']);
                            }
                          } catch (e) {
                            if (mounted) {
                              setState(() => error = '$e');
                            }
                          }
                        },
                  child: const Text('Şifremi Unuttum'),
                ),
                PrimaryButton(
                  label: 'Giriş Yap',
                  busy: busy,
                  onPressed: submit,
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}

class Home extends StatefulWidget {
  final VoidCallback onLogout;
  const Home({super.key, required this.onLogout});
  @override
  State<Home> createState() => _HomeState();
}

class _HomeState extends State<Home> {
  int tab = 0;
  Map<String, dynamic>? profile;
  List<dynamic> paths = [];
  String? error;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    setState(() => error = null);
    try {
      final values = await Future.wait([
        api.request('profile/'),
        api.request('paths/'),
      ]);
      if (mounted) {
        setState(() {
          profile = values[0];
          paths = values[1];
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => error = '$e');
      }
    }
  }

  Future<void> open(Map<String, dynamic> path) async {
    analytics.emit('path_opened');
    if (path['premium'] && profile?['premium'] != true) {
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => Paywall(userId: profile!['billing_id']),
        ),
      );
    } else {
      await Navigator.of(
        context,
      ).push(MaterialPageRoute(builder: (_) => Session(path: path)));
    }
    load();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      toolbarHeight: 76,
      title: const BrandHeader(),
      actions: [
        Padding(
          padding: const EdgeInsets.only(right: 18),
          child: Icon(Icons.auto_awesome_rounded, color: AppColors.gold),
        ),
      ],
    ),
    bottomNavigationBar: NavigationBar(
      selectedIndex: tab,
      onDestinationSelected: (v) {
        setState(() => tab = v);
        if (v == 3) load();
      },
      destinations: const [
        NavigationDestination(
          icon: Icon(Icons.home_outlined),
          label: 'Ana Sayfa',
        ),
        NavigationDestination(
          icon: Icon(Icons.route_outlined),
          label: 'Yollar',
        ),
        NavigationDestination(
          icon: Icon(Icons.insights_outlined),
          label: 'İlerlemem',
        ),
        NavigationDestination(
          icon: Icon(Icons.person_outline),
          label: 'Profil',
        ),
      ],
    ),
    body: error != null
        ? ErrorState(message: error!, retry: load)
        : profile == null
        ? const Center(child: CircularProgressIndicator())
        : RefreshIndicator(
            onRefresh: load,
            child: ListView(
              padding: const EdgeInsets.all(24),
              children: [
                if (tab == 0) ...[
                  DashboardHero(name: profile!['first_name']),
                  const SizedBox(height: 22),
                  LearningStats(profile: profile!),
                  const SizedBox(height: 30),
                  Text(
                    'Bir sonraki maceran',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text('Bir yol seç, ilk adımını at.'),
                  const SizedBox(height: 18),
                ],
                if (tab <= 1) ...[
                  if (paths.isEmpty)
                    const Text('Yeni öğrenme yolları yakında burada.'),
                  for (final p in paths)
                    PathCard(path: p, onTap: () => open(p)),
                  const SizedBox(height: 12),
                  PrimaryButton(
                    label: 'Bana Özel Yol Oluştur',
                    onPressed: () async {
                      if (profile!['premium'] != true) {
                        await Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) =>
                                Paywall(userId: profile!['billing_id']),
                          ),
                        );
                        await load();
                        return;
                      }
                      await Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => Personalize(paths: paths),
                        ),
                      );
                      load();
                    },
                  ),
                ],
                if (tab == 2) ...[
                  Text(
                    'İlerlemen',
                    style: Theme.of(context).textTheme.headlineLarge,
                  ),
                  const SizedBox(height: 24),
                  Text(
                    '⚡ ${profile!['xp']} toplam XP',
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  const SizedBox(height: 24),
                  for (final p in paths)
                    PathCard(path: p, onTap: () => open(p)),
                ],
                if (tab == 3) ...[
                  Text(
                    profile!['full_name'].toString().isEmpty
                        ? profile!['first_name']
                        : profile!['full_name'],
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    profile!['premium'] ? 'Premium üyelik' : 'Ücretsiz üyelik',
                  ),
                  const SizedBox(height: 24),
                  LevelRewards(profile: profile!),
                  const SizedBox(height: 32),
                  TextButton(
                    onPressed: () async {
                      await Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) =>
                              Paywall(userId: profile!['billing_id']),
                        ),
                      );
                      load();
                    },
                    child: const Text('Üyeliğim / Satın alımları geri yükle'),
                  ),
                  PrimaryButton(
                    label: 'Çıkış Yap',
                    onPressed: () async {
                      try {
                        await api.logout();
                        if (mounted) {
                          widget.onLogout();
                        }
                      } catch (e) {
                        if (context.mounted) {
                          ScaffoldMessenger.of(
                            context,
                          ).showSnackBar(SnackBar(content: Text('$e')));
                        }
                      }
                    },
                  ),
                ],
              ],
            ),
          ),
  );
}

class PathCard extends StatelessWidget {
  final Map<String, dynamic> path;
  final VoidCallback onTap;
  const PathCard({super.key, required this.path, required this.onTap});
  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final progress = ((path['progress'] as num).toDouble() / 100).clamp(
      0.0,
      1.0,
    );
    final completed = path['completed'] as int;
    final count = path['question_count'] as int;
    return Container(
      margin: const EdgeInsets.only(bottom: 20),
      decoration: BoxDecoration(
        color: scheme.surface,
        borderRadius: BorderRadius.circular(26),
        border: Border.all(color: scheme.outlineVariant, width: 2),
        boxShadow: [
          BoxShadow(color: scheme.outlineVariant, offset: const Offset(0, 5)),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(26),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(22),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 52,
                      height: 52,
                      decoration: BoxDecoration(
                        color: AppColors.teal.withValues(alpha: .14),
                        borderRadius: BorderRadius.circular(17),
                      ),
                      child: const Icon(
                        Icons.shield_rounded,
                        color: AppColors.teal,
                        size: 30,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            path['premium'] ? 'PREMIUM YOL' : 'ÖĞRENME YOLU',
                            style: const TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w900,
                              color: AppColors.teal,
                              letterSpacing: 1,
                            ),
                          ),
                          const SizedBox(height: 5),
                          Text(
                            path['title'],
                            style: const TextStyle(
                              fontSize: 19,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ],
                      ),
                    ),
                    if (path['premium'])
                      const Icon(
                        Icons.workspace_premium_rounded,
                        color: AppColors.gold,
                      ),
                  ],
                ),
                const SizedBox(height: 14),
                Text(
                  path['description'],
                  style: TextStyle(
                    color: scheme.onSurfaceVariant,
                    height: 1.45,
                  ),
                ),
                const SizedBox(height: 18),
                Row(
                  children: [
                    for (var i = 0; i < (count < 6 ? count : 6); i++) ...[
                      if (i > 0)
                        Expanded(
                          child: Container(
                            height: 3,
                            color: i <= completed
                                ? AppColors.teal
                                : scheme.outlineVariant,
                          ),
                        ),
                      Container(
                        width: 32,
                        height: 32,
                        decoration: BoxDecoration(
                          color: i < completed
                              ? AppColors.teal
                              : i == completed
                              ? AppColors.gold
                              : scheme.surfaceContainerHighest,
                          shape: BoxShape.circle,
                        ),
                        child: Icon(
                          i < completed
                              ? Icons.check_rounded
                              : i == completed
                              ? Icons.play_arrow_rounded
                              : Icons.circle_outlined,
                          size: 18,
                          color: i <= completed
                              ? AppColors.ink
                              : scheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 16),
                LinearProgressIndicator(
                  value: progress,
                  minHeight: 10,
                  borderRadius: BorderRadius.circular(12),
                  color: AppColors.teal,
                ),
                const SizedBox(height: 14),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        '$completed / $count görev · ${path['minutes']} dk',
                        style: TextStyle(
                          fontSize: 12,
                          color: scheme.onSurfaceVariant,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    Text(
                      progress == 1
                          ? 'TAMAMLANDI ✓'
                          : completed > 0
                          ? 'DEVAM ET →'
                          : 'BAŞLA →',
                      style: const TextStyle(
                        color: AppColors.teal,
                        fontSize: 12,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class Session extends StatefulWidget {
  final Map<String, dynamic> path;
  const Session({super.key, required this.path});
  @override
  State<Session> createState() => _SessionState();
}

class _SessionState extends State<Session> {
  Map<String, dynamic>? session;
  Map<String, dynamic>? feedback;
  final input = TextEditingController();
  final selected = <String>{};
  List<String> arranged = [];
  final questionScroll = ScrollController();
  Timer? dragScrollTimer;
  Offset? dragPointer;
  bool draggingCard = false;

  void beginCardDrag() {
    dragPointer = null;
    dragScrollTimer?.cancel();
    setState(() => draggingCard = true);
    dragScrollTimer = Timer.periodic(const Duration(milliseconds: 35), (_) {
      if (!mounted || dragPointer == null || !questionScroll.hasClients) return;
      final media = MediaQuery.of(context);
      final top = media.padding.top + 130;
      final bottom = media.size.height - media.padding.bottom - 120;
      final y = dragPointer!.dy;
      final delta = y < top
          ? -14.0
          : y > bottom
          ? 14.0
          : 0.0;
      if (delta == 0) return;
      final position = questionScroll.position;
      questionScroll.jumpTo(
        (position.pixels + delta).clamp(
          position.minScrollExtent,
          position.maxScrollExtent,
        ),
      );
    });
  }

  void endCardDrag() {
    dragScrollTimer?.cancel();
    dragPointer = null;
    if (mounted) setState(() => draggingCard = false);
  }

  final player = AudioPlayer();
  int? audioQuestion;
  bool busy = false;
  String? error;
  DateTime viewed = DateTime.now();
  @override
  void dispose() {
    dragScrollTimer?.cancel();
    questionScroll.dispose();
    input.dispose();
    player.dispose();
    super.dispose();
  }

  Future<void> start() async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      analytics.emit('session_started');
      final s = await api.request(
        'sessions/',
        body: {'path_id': widget.path['id']},
      );
      if (mounted) {
        setState(() {
          session = s;
          viewed = DateTime.now();
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => error = '$e');
      }
    } finally {
      if (mounted) {
        setState(() => busy = false);
      }
    }
  }

  Future<void> submit() async {
    FocusScope.of(context).unfocus();
    final q = session!['question'];
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final result = await api.request(
        'sessions/${session!['id']}/answer/',
        body: {
          'question_id': q['id'],
          'answer': ['text', 'fill_blank'].contains(q['kind'])
              ? input.text
              : ['sentence_order', 'drag_select'].contains(q['kind'])
              ? arranged
              : selected.toList(),
          'duration_seconds': DateTime.now().difference(viewed).inSeconds,
        },
      );
      await player.stop();
      analytics.emit(result['correct'] ? 'question_correct' : 'question_wrong');
      analytics.emit('question_answered');
      if (result['correct']) {
        HapticFeedback.mediumImpact();
      } else {
        HapticFeedback.heavyImpact();
      }
      if (mounted) {
        setState(() => feedback = result);
      }
    } catch (e) {
      if (mounted) {
        setState(() => error = '$e');
      }
    } finally {
      if (mounted) {
        setState(() => busy = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final q = session?['question'];
    if (feedback != null) {
      return AnswerFeedback(
        result: feedback!,
        onContinue: () => setState(() {
          session = feedback!['session'];
          feedback = null;
          selected.clear();
          arranged = [];
          input.clear();
          viewed = DateTime.now();
        }),
      );
    }
    return Scaffold(
      bottomNavigationBar: q != null && q['kind'] == 'sentence_order'
          ? SafeArea(
              child: DragTarget<String>(
                onWillAcceptWithDetails: (d) =>
                    !busy &&
                    !arranged.contains(d.data) &&
                    (q['options'] as List).any((o) => o['id'] == d.data),
                onAcceptWithDetails: (d) =>
                    setState(() => arranged = [...arranged, d.data]),
                builder: (_, candidates, _) => Container(
                  margin: const EdgeInsets.fromLTRB(18, 8, 18, 8),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppColors.teal.withValues(
                      alpha: candidates.isNotEmpty ? .28 : .12,
                    ),
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(color: AppColors.teal, width: 2),
                  ),
                  child: const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.add_circle_outline_rounded,
                        color: AppColors.teal,
                      ),
                      SizedBox(width: 8),
                      Flexible(
                        child: Text(
                          'Cümleme ekle • kartı buraya bırak',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontWeight: FontWeight.w800,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            )
          : null,
      appBar: AppBar(
        title: Text(
          widget.path['title'],
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Image.asset('assets/logo.png', width: 42),
          ),
        ],
      ),
      body: SafeArea(
        child: ListView(
          controller: questionScroll,
          physics: draggingCard ? const NeverScrollableScrollPhysics() : null,
          padding: const EdgeInsets.all(24),
          children: [
            if (session == null) ...[
              const Icon(
                Icons.bolt_rounded,
                size: 64,
                color: AppColors.primary,
              ),
              const SizedBox(height: 32),
              Text(
                'Bugünkü görev',
                style: Theme.of(context).textTheme.headlineLarge,
              ),
              const SizedBox(height: 16),
              Text(
                'En fazla 8 soru · yaklaşık ${widget.path['minutes']} dakika',
              ),
              const SizedBox(height: 32),
              PrimaryButton(label: 'Başla', busy: busy, onPressed: start),
            ] else if (session!['complete']) ...[
              const Icon(
                Icons.emoji_events_outlined,
                size: 90,
                color: AppColors.primary,
              ),
              const SizedBox(height: 24),
              Text(
                'Harika iş! 🎉',
                style: Theme.of(context).textTheme.headlineLarge,
              ),
              const SizedBox(height: 24),
              Text(
                '${session!['total']} soru çözdün\n${session!['correct']} doğru\n${session!['xp_earned']} XP\nYolun %${session!['path']['progress']} tamamlandı',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 32),
              PrimaryButton(
                label: 'Ana Sayfa',
                onPressed: () => Navigator.pop(context),
              ),
            ] else if (q != null) ...[
              Row(
                children: [
                  const Icon(Icons.bolt_rounded, color: AppColors.gold),
                  const SizedBox(width: 8),
                  Text(
                    'GÖREV ${session!['answered'] + 1} / ${session!['total']}',
                    style: const TextStyle(
                      fontWeight: FontWeight.w900,
                      letterSpacing: 1,
                    ),
                  ),
                  const Spacer(),
                  const Text(
                    'ADIM ADIM',
                    style: TextStyle(
                      color: AppColors.teal,
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              LinearProgressIndicator(
                value: session!['answered'] / session!['total'],
                minHeight: 12,
                color: AppColors.teal,
                borderRadius: BorderRadius.circular(12),
              ),
              const SizedBox(height: 32),
              if (q['context'] != '') ...[
                Container(
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surface,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: Theme.of(context).colorScheme.outlineVariant,
                      width: 2,
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Icon(
                            Icons.description_rounded,
                            color: AppColors.teal,
                            size: 20,
                          ),
                          SizedBox(width: 8),
                          Text(
                            'SENARYO',
                            style: TextStyle(
                              fontWeight: FontWeight.w900,
                              letterSpacing: 1,
                              fontSize: 11,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Text(
                        q['context'],
                        style: const TextStyle(height: 1.6, fontSize: 15),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 22),
              ],
              Text(
                q['prompt'],
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 24),
              if (q['image'] != null)
                Image.network(
                  q['image'],
                  headers: {'Authorization': 'Bearer ${api.access}'},
                  errorBuilder: (_, _, _) =>
                      const Text('Görsel yüklenemedi. Bağlantını kontrol et.'),
                ),
              if ((q['audio'] as List).isNotEmpty)
                StreamBuilder<PlayerState>(
                  stream: player.playerStateStream,
                  builder: (_, snapshot) => OutlinedButton.icon(
                    icon: Icon(
                      snapshot.data?.playing == true
                          ? Icons.pause
                          : Icons.play_arrow,
                    ),
                    label: const Text('Senaryoyu dinle'),
                    onPressed: () async {
                      try {
                        if (player.playing) {
                          await player.pause();
                        } else {
                          if (audioQuestion != q['id'] ||
                              player.audioSource == null ||
                              player.processingState ==
                                  ProcessingState.completed) {
                            audioQuestion = q['id'];
                            await player.setAudioSources([
                              for (final url in q['audio'])
                                AudioSource.uri(
                                  Uri.parse(url),
                                  headers: {
                                    'Authorization': 'Bearer ${api.access}',
                                  },
                                ),
                            ]);
                          }
                          player.play();
                        }
                      } catch (_) {
                        if (mounted) {
                          setState(
                            () => error =
                                'Ses yüklenemedi. Tekrar deneyebilirsin.',
                          );
                        }
                      }
                    },
                  ),
                ),
              if (['text', 'fill_blank'].contains(q['kind']))
                TextField(
                  controller: input,
                  maxLength: 4000,
                  onChanged: (_) => setState(() {}),
                  decoration: const InputDecoration(labelText: 'Yanıtın'),
                )
              else if (q['kind'] == 'sentence_order')
                SentenceBuilder(
                  key: ValueKey(q['id']),
                  options: q['options'],
                  value: arranged,
                  enabled: !busy,
                  onChanged: (v) => setState(() => arranged = v),
                  onDragStart: beginCardDrag,
                  onDragEnd: endCardDrag,
                  onDragPosition: (p) => dragPointer = p,
                )
              else if (q['kind'] == 'drag_select')
                DragRiskQuestion(
                  key: ValueKey(q['id']),
                  options: q['options'],
                  value: arranged,
                  enabled: !busy,
                  onChanged: (v) => setState(() => arranged = v),
                  onDragStart: beginCardDrag,
                  onDragEnd: endCardDrag,
                  onDragPosition: (p) => dragPointer = p,
                )
              else if (q['kind'] == 'voice')
                VoiceRecorder(
                  key: ValueKey(q['id']),
                  onSubmit: (file, duration) async {
                    final result = await api.uploadVoice(
                      session!['id'],
                      q['id'],
                      file,
                      duration,
                    );
                    if (mounted) {
                      setState(() {
                        feedback = {
                          'correct': true,
                          'pending': true,
                          'xp_change': 0,
                          'explanation': result['detail'],
                          'hint': '',
                          'session': result['session'],
                        };
                      });
                    }
                  },
                )
              else
                for (final option in q['options'])
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: AnswerOption(
                      label: option['text'],
                      marker: String.fromCharCode(
                        65 + (q['options'] as List).indexOf(option),
                      ),
                      selected: selected.contains(option['id']),
                      onTap: busy
                          ? null
                          : () => setState(() {
                              if (q['kind'] != 'multi_select') {
                                selected.clear();
                              }
                              if (!selected.add(option['id'])) {
                                selected.remove(option['id']);
                              }
                            }),
                    ),
                  ),
              const SizedBox(height: 24),
              PrimaryButton(
                label: 'Yanıtı kontrol et',
                busy: busy,
                onPressed:
                    q['kind'] == 'voice' ||
                        busy ||
                        (['text', 'fill_blank'].contains(q['kind'])
                            ? input.text.trim().isEmpty
                            : [
                                'sentence_order',
                                'drag_select',
                              ].contains(q['kind'])
                            ? arranged.isEmpty
                            : selected.isEmpty)
                    ? null
                    : submit,
              ),
            ],
            if (error != null)
              Padding(
                padding: const EdgeInsets.only(top: 20),
                child: Text(error!),
              ),
          ],
        ),
      ),
    );
  }
}

class Personalize extends StatefulWidget {
  final List<dynamic> paths;
  const Personalize({super.key, required this.paths});
  @override
  State<Personalize> createState() => _PersonalizeState();
}

class _PersonalizeState extends State<Personalize> {
  int? path;
  String level = 'beginner';
  int minutes = 10;
  String goal = 'Sertifika';
  bool busy = false;
  String? error;
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Bana özel yol')),
    body: ListView(
      padding: const EdgeInsets.all(24),
      children: [
        const Text('Ne öğrenmek istiyorsun?'),
        DropdownButton<int>(
          isExpanded: true,
          value: path,
          items: [
            for (final p in widget.paths)
              DropdownMenuItem(value: p['id'], child: Text(p['title'])),
          ],
          onChanged: (v) => setState(() => path = v),
        ),
        const SizedBox(height: 24),
        const Text('Seviyen nedir?'),
        DropdownButton<String>(
          isExpanded: true,
          value: level,
          items: const [
            DropdownMenuItem(value: 'beginner', child: Text('Başlangıç')),
            DropdownMenuItem(value: 'intermediate', child: Text('Orta')),
            DropdownMenuItem(value: 'advanced', child: Text('İleri')),
          ],
          onChanged: (v) => setState(() => level = v!),
        ),
        const SizedBox(height: 24),
        const Text('Günde ne kadar zaman ayırabilirsin?'),
        DropdownButton<int>(
          isExpanded: true,
          value: minutes,
          items: [
            for (final m in [5, 10, 20])
              DropdownMenuItem(value: m, child: Text('$m dakika')),
          ],
          onChanged: (v) => setState(() => minutes = v!),
        ),
        const SizedBox(height: 24),
        const Text('Amacın nedir?'),
        DropdownButton<String>(
          isExpanded: true,
          value: goal,
          items: [
            for (final g in [
              'Yeni işe girmek',
              'Mevcut işimde gelişmek',
              'Sertifika',
              'Teknik bilgi',
              'Denetim',
              'Kariyer değişikliği',
            ])
              DropdownMenuItem(value: g, child: Text(g)),
          ],
          onChanged: (v) => setState(() => goal = v!),
        ),
        const SizedBox(height: 32),
        PrimaryButton(
          label: 'Yolumu oluştur',
          busy: busy,
          onPressed: path == null
              ? null
              : () async {
                  setState(() {
                    busy = true;
                    error = null;
                  });
                  try {
                    await api.request(
                      'paths/personalize/',
                      body: {
                        'path_id': path,
                        'level': level,
                        'minutes': minutes,
                        'goal': goal,
                      },
                    );
                    if (context.mounted) {
                      Navigator.pop(context);
                    }
                  } catch (e) {
                    if (mounted) {
                      setState(() => error = '$e');
                    }
                  } finally {
                    if (mounted) {
                      setState(() => busy = false);
                    }
                  }
                },
        ),
        if (error != null) Text(error!),
      ],
    ),
  );
}
