import 'dart:async';
import 'package:flutter/foundation.dart';
import 'password_reset.dart';
import 'account_deletion.dart';
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
import 'information_card.dart';
import 'brand_welcome.dart';
import 'profile_actions.dart';
import 'learning_experience.dart';
import 'daily_activity.dart';
import 'daily_notifications.dart';
import 'package:url_launcher/url_launcher.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const GrcApp());
}

final api = Api();
final analytics = Analytics(api);
bool get externalPaymentsAllowed => defaultTargetPlatform != TargetPlatform.iOS;

Future<void> openPasswordReset(BuildContext context, [String email = '']) =>
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => PasswordResetScreen(
          initialEmail: email,
          onRequest: (address) async {
            final result = await api.request(
              'auth/password-reset/',
              body: {'email': address},
            );
            return result['detail'];
          },
        ),
      ),
    );

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
      Future<void>.delayed(const Duration(milliseconds: 2100)),
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
      return const WelcomeSplash();
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
  final name = TextEditingController();
  bool registering = false;
  final email = TextEditingController();
  final password = TextEditingController();
  bool busy = false;
  String? error;
  @override
  void dispose() {
    name.dispose();
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
      if (registering) {
        await api.save(
          await api.request(
            'auth/register/',
            body: {
              'name': name.text.trim(),
              'email': email.text.trim(),
              'password': password.text,
            },
          ),
        );
      } else {
        await api.login(email.text.trim(), password.text);
      }
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
                const BrandWelcome(),
                const SizedBox(height: 24),
                Text(
                  'Öğren. Uygula. Ustalaş.',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  registering
                      ? 'Ücretsiz hesabını oluştur, başlangıç yolunu hemen dene.'
                      : 'GRC Ustası hesabınla öğrenmeye devam et.',
                ),
                const SizedBox(height: 32),
                if (registering) ...[
                  TextField(
                    controller: name,
                    textCapitalization: TextCapitalization.words,
                    autofillHints: const [AutofillHints.name],
                    decoration: const InputDecoration(labelText: 'Ad soyad'),
                  ),
                  const SizedBox(height: 14),
                ],
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
                  autofillHints: [
                    registering
                        ? AutofillHints.newPassword
                        : AutofillHints.password,
                  ],
                  decoration: const InputDecoration(labelText: 'Şifre'),
                  onSubmitted: (_) => busy ? null : submit(),
                ),
                const SizedBox(height: 24),
                if (error != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: Text(error!),
                  ),
                if (!registering)
                  TextButton(
                    onPressed: busy
                        ? null
                        : () => openPasswordReset(context, email.text.trim()),
                    child: const Text('Şifremi sıfırla'),
                  ),
                PrimaryButton(
                  label: registering ? 'Ücretsiz Hesap Oluştur' : 'Giriş Yap',
                  busy: busy,
                  onPressed: submit,
                ),
                const SizedBox(height: 12),
                Center(
                  child: TextButton(
                    onPressed: busy
                        ? null
                        : () => setState(() {
                            registering = !registering;
                            error = null;
                            password.clear();
                          }),
                    child: Text(
                      registering
                          ? 'Zaten hesabım var • Giriş yap'
                          : 'Yeni misin? Ücretsiz hesap oluştur',
                    ),
                  ),
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

class _HomeState extends State<Home> with WidgetsBindingObserver {
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) load();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  int tab = 0;
  Map<String, dynamic>? profile;
  List<dynamic> paths = [];
  Map<String, dynamic> activity = {};
  bool paymentBusy = false;
  String? error;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    load();
  }

  Future<void> load() async {
    setState(() => error = null);
    try {
      final freshProfile = await api.request('profile/');
      if (freshProfile['must_change_password'] == true) {
        if (mounted) setState(() => profile = freshProfile);
        return;
      }
      final zone = await dailyNotifications.timezoneName();
      final values = await Future.wait([
        Future.value(freshProfile),
        api.request('paths/'),
        api
            .request('activity/?timezone=${Uri.encodeComponent(zone)}')
            .catchError((_) => <String, dynamic>{'days': <dynamic>[]}),
      ]);
      if (mounted) {
        setState(() {
          profile = values[0];
          paths = values[1];
          activity = Map<String, dynamic>.from(values[2]);
          if (externalPaymentsAllowed &&
              profile!['premium'] != true &&
              tab == 2) {
            tab = 0;
          }
        });
        unawaited(syncNotifications());
      }
    } catch (e) {
      if (mounted) {
        setState(() => error = '$e');
      }
    }
  }

  Future<void> syncNotifications() async {
    try {
      final zone = await dailyNotifications.timezoneName();
      final plan = await api.request(
        'notifications/plan/?timezone=${Uri.encodeComponent(zone)}',
      );
      if (!mounted) return;
      await dailyNotifications.sync(Map<String, dynamic>.from(plan));
      if (mounted) setState(() {});
    } catch (_) {
      // Keep the last valid phone schedule if the connection is interrupted.
    }
  }

  Future<void> openMembership() async {
    if (paymentBusy) return;
    setState(() => paymentBusy = true);
    try {
      final data = await api.request('payments/link/', body: {});
      if (!await launchUrl(
        Uri.parse(data['url']),
        mode: LaunchMode.externalApplication,
      )) {
        throw Exception('Ödeme sayfası açılamadı.');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => paymentBusy = false);
    }
  }

  Future<void> open(Map<String, dynamic> path) async {
    if (path['is_complete'] == true) {
      await restart(path);
      return;
    }
    analytics.emit('path_opened');
    await Navigator.of(
      context,
    ).push(MaterialPageRoute(builder: (_) => Session(path: path)));
    load();
  }

  Future<void> restart(Map<String, dynamic> path) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text(
          'Sıfırdan başla',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
        ),
        content: const Text(
          'Bu yolu yeniden başlatmak ister misin? XP ve seviyen korunur; doğru cevaplarla tekrar puan kazanırsın.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Vazgeç'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Sıfırdan başla'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    try {
      final fresh = await api.request('paths/${path['id']}/restart/', body: {});
      if (!mounted) return;
      await open(Map<String, dynamic>.from(fresh));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) load();
    }
  }

  @override
  Widget build(BuildContext context) => profile?['must_change_password'] == true
      ? PasswordChange(
          requiredAtLogin: true,
          onSave: (current, password, confirmation) async {
            await api.save(
              await api.request(
                'auth/change-password/',
                body: {
                  'new_password': password,
                  'confirm_password': confirmation,
                },
              ),
            );
          },
          onFinished: () {
            setState(() => profile = null);
            load();
          },
        )
      : Scaffold(
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
          bottomNavigationBar: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (externalPaymentsAllowed &&
                  profile != null &&
                  profile!['premium'] != true)
                SafeArea(
                  bottom: false,
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(20, 8, 20, 8),
                    child: SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        style: FilledButton.styleFrom(
                          backgroundColor: const Color(0xFFC9343E),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 17),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(18),
                          ),
                        ),
                        onPressed: paymentBusy ? null : openMembership,
                        icon: const Icon(Icons.workspace_premium_rounded),
                        label: Text(
                          paymentBusy
                              ? 'Ödeme sayfası açılıyor…'
                              : 'Premium’a geç • 2.099 TL / ay',
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              NavigationBar(
                selectedIndex: tab,
                onDestinationSelected: (v) {
                  if (externalPaymentsAllowed &&
                      v == 2 &&
                      profile != null &&
                      profile!['premium'] != true) {
                    openMembership();
                    return;
                  }
                  setState(() => tab = v);
                  if (v == 2 || v == 3) load();
                },
                destinations: [
                  const NavigationDestination(
                    icon: Icon(Icons.home_outlined),
                    label: 'Ana Sayfa',
                  ),
                  const NavigationDestination(
                    icon: Icon(Icons.route_outlined),
                    label: 'Yollar',
                  ),
                  if (externalPaymentsAllowed &&
                      profile != null &&
                      profile!['premium'] != true)
                    NavigationDestination(
                      icon: Container(
                        padding: const EdgeInsets.all(7),
                        decoration: BoxDecoration(
                          color: AppColors.gold,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(
                          Icons.workspace_premium_rounded,
                          color: Color(0xFF102039),
                        ),
                      ),
                      label: 'Premium ol',
                    )
                  else
                    const NavigationDestination(
                      icon: Icon(Icons.insights_outlined),
                      label: 'İlerlemem',
                    ),
                  const NavigationDestination(
                    icon: Icon(Icons.person_outline),
                    label: 'Profil',
                  ),
                ],
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
                          style: Theme.of(context).textTheme.titleLarge
                              ?.copyWith(fontWeight: FontWeight.w900),
                        ),
                        const SizedBox(height: 6),
                        const Text('Bir yol seç, ilk adımını at.'),
                        const SizedBox(height: 18),
                      ],
                      if (tab <= 1) ...[
                        if (paths.isEmpty)
                          const Text('Yeni öğrenme yolları yakında burada.'),
                        for (final p in paths)
                          PathCard(
                            path: p,
                            onTap: () => open(p),
                            onRestart: () => restart(p),
                          ),
                        const SizedBox(height: 12),
                      ],
                      if (tab == 2) ...[
                        DailyActivityChart(activity: activity),
                        const SizedBox(height: 24),
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
                          PathCard(
                            path: p,
                            onTap: () => open(p),
                            onRestart: () => restart(p),
                          ),
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
                          profile!['premium']
                              ? 'Tam erişim • tüm öğrenme yolları'
                              : 'Ücretsiz başlangıç • bir öğrenme yolu',
                        ),
                        const SizedBox(height: 24),
                        ProfileActions(
                          contact: (profile!['contact'] as Map?)
                              ?.cast<String, dynamic>(),
                          onPassword: () async {
                            final changed = await Navigator.of(context)
                                .push<bool>(
                                  MaterialPageRoute(
                                    builder: (_) => PasswordChange(
                                      onSave:
                                          (current, password, confirm) async {
                                            final result = await api.request(
                                              'auth/change-password/',
                                              body: {
                                                'current_password': current,
                                                'new_password': password,
                                                'confirm_password': confirm,
                                              },
                                            );
                                            await api.save(result);
                                          },
                                    ),
                                  ),
                                );
                            if (changed == true && context.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text('Şifren yenilendi.'),
                                ),
                              );
                            }
                          },
                        ),
                        const SizedBox(height: 24),
                        LevelRewards(profile: profile!),
                        const SizedBox(height: 20),
                        SwitchListTile.adaptive(
                          contentPadding: EdgeInsets.zero,
                          title: const Text('Günlük motivasyon bildirimi'),
                          subtitle: Text(
                            'Günde en fazla 1 bildirim${dailyNotifications.latestPlan == null ? '' : ' • saat ${dailyNotifications.latestPlan!['hour'] ?? 19}:00'}',
                          ),
                          value: dailyNotifications.enabled,
                          onChanged: (value) async {
                            try {
                              final enabled = await dailyNotifications
                                  .setEnabled(value);
                              if (!mounted) return;
                              setState(() {});
                              if (value && !enabled && context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                    content: Text(
                                      'Bildirim izni kapalı. Telefon ayarlarından GRC Ustası bildirimlerini açabilirsin.',
                                    ),
                                  ),
                                );
                              }
                            } catch (_) {
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                    content: Text(
                                      'Bildirim ayarı kaydedilemedi. Tekrar deneyebilirsin.',
                                    ),
                                  ),
                                );
                              }
                            }
                          },
                        ),
                        const SizedBox(height: 32),
                        if (profile!['paid_until'] != null)
                          Text(
                            'Ücretli erişim bitişi: ${DateTime.parse(profile!['paid_until']).toLocal().toString().substring(0, 16)}',
                          ),
                        if (externalPaymentsAllowed)
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
                            child: const Text('Tam erişim • Üyelik ve ödeme'),
                          ),
                        TextButton.icon(
                          onPressed: () => openPasswordReset(context),
                          icon: const Icon(Icons.lock_reset),
                          label: const Text('Şifremi sıfırla'),
                        ),
                        TextButton.icon(
                          onPressed: () => Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) => AccountDeletionScreen(
                                onRequest: (password) async {
                                  final result = await api.request(
                                    'auth/delete-account/',
                                    body: {
                                      'password': password,
                                      'confirm': true,
                                    },
                                  );
                                  return result['detail'];
                                },
                              ),
                            ),
                          ),
                          icon: const Icon(Icons.person_remove_outlined),
                          label: const Text('Hesabımı sil'),
                        ),
                        TextButton(
                          onPressed: () => launchUrl(
                            Uri.parse(
                              'https://www.grcustasi.com/mobiluygulama/gizlilik',
                            ),
                            mode: LaunchMode.externalApplication,
                          ),
                          child: const Text('Gizlilik politikası'),
                        ),
                        PrimaryButton(
                          label: 'Çıkış Yap',
                          onPressed: () async {
                            try {
                              await api.logout();
                              await dailyNotifications.clearForLogout();
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
  final VoidCallback? onRestart;
  const PathCard({
    super.key,
    required this.path,
    required this.onTap,
    this.onRestart,
  });
  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final completed = (path['completed'] as num?)?.toInt() ?? 0;
    final count = (path['question_count'] as num?)?.toInt() ?? 0;
    final complete = path['is_complete'] == true;
    final progress = count == 0 ? 0.0 : (completed / count).clamp(0.0, 1.0);
    return Card(
      color: scheme.surface,
      elevation: 2,
      shadowColor: scheme.outlineVariant,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(24),
        side: BorderSide(color: scheme.outlineVariant),
      ),
      margin: const EdgeInsets.only(bottom: 16),
      child: InkWell(
        borderRadius: BorderRadius.circular(24),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(
                    Icons.route_rounded,
                    color: AppColors.teal,
                    size: 32,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      path['title'],
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 19,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  if (complete && onRestart != null)
                    IconButton(
                      onPressed: onRestart,
                      tooltip: 'Sıfırdan başla',
                      iconSize: 18,
                      color: scheme.onSurfaceVariant,
                      icon: const Icon(Icons.replay_rounded),
                    )
                  else
                    const Icon(Icons.chevron_right_rounded),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                path['description'] ?? '',
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: scheme.onSurfaceVariant, height: 1.4),
              ),
              const SizedBox(height: 18),
              LinearProgressIndicator(
                value: progress,
                minHeight: 9,
                color: AppColors.teal,
                borderRadius: BorderRadius.circular(12),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      '$completed / $count soru • %${(progress * 100).round()}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 12,
                      ),
                    ),
                  ),
                  Text(
                    complete
                        ? 'TAMAMLANDI ✓'
                        : completed > 0
                        ? 'DEVAM ET →'
                        : 'BAŞLA →',
                    style: const TextStyle(
                      color: AppColors.teal,
                      fontWeight: FontWeight.w900,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
              if (!complete &&
                  completed > 0 &&
                  (path['remaining_tasks'] ?? 0) > 0) ...[
                const SizedBox(height: 8),
                Text(
                  '${path['remaining_tasks']} görev seni bekliyor',
                  style: TextStyle(color: scheme.onSurfaceVariant),
                ),
              ],
              if ((path['information_count'] ?? 0) > 0) ...[
                const SizedBox(height: 8),
                Text(
                  '${path['information_count']} bilgi kartı • kısa oturumlarla ilerle',
                  style: TextStyle(
                    color: scheme.onSurfaceVariant,
                    fontSize: 12,
                  ),
                ),
              ],
            ],
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
  bool voiceMode = false;

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
          'answer': ['text', 'fill_blank', 'voice'].contains(q['kind'])
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
          voiceMode = false;
          viewed = DateTime.now();
          if (questionScroll.hasClients) questionScroll.jumpTo(0);
        }),
      );
    }
    if (q != null && q['kind'] == 'info') {
      return InformationCard(
        key: ValueKey(q['id']),
        question: q,
        pathTitle: widget.path['title'],
        answered: session!['answered'],
        total: session!['total'],
        onContinue: () async {
          final next = await api.request(
            'sessions/${session!['id']}/continue/',
            body: {'question_id': q['id']},
          );
          if (mounted) {
            setState(() {
              session = next;
              error = null;
              viewed = DateTime.now();
            });
          }
        },
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
                'Bu oturumda en fazla ${widget.path['session_size'] ?? 8} soru ve aradaki bilgi kartları. İlerlemen kaydedilir; kaldığın yerden devam edebilirsin.',
              ),
              const SizedBox(height: 32),
              PrimaryButton(label: 'Başla', busy: busy, onPressed: start),
              const SizedBox(height: 30),
              const LearningExperience(),
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
                '${session!['question_total'] ?? session!['total']} soru tamamladın\n${session!['correct']} doğru • ${session!['pending_reviews'] ?? 0} ses kaydı incelemede\n${session!['information_read'] ?? 0} bilgi kartı\n${session!['xp_earned']} XP\nYolun %${session!['path']['progress']} tamamlandı',
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
              if (q['kind'] == 'voice') ...[
                Wrap(
                  spacing: 10,
                  children: [
                    ChoiceChip(
                      label: const Text('✍️ Yazarak yanıtla'),
                      selected: !voiceMode,
                      onSelected: busy
                          ? null
                          : (_) => setState(() => voiceMode = false),
                    ),
                    ChoiceChip(
                      label: const Text('🎙️ Sesli yanıtla'),
                      selected: voiceMode,
                      onSelected: busy
                          ? null
                          : (_) => setState(() => voiceMode = true),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                const Text(
                  'Yazılı yanıtın tek doğru cevaba göre kontrol edilir. Sesli mesaj üzerinden geri bildirim e-posta yoluyla 24 saat içinde incelenip verilecektir.',
                  style: TextStyle(height: 1.5),
                ),
                const SizedBox(height: 16),
              ],
              if (['text', 'fill_blank', 'voice'].contains(q['kind']) &&
                  !voiceMode)
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
              else if (q['kind'] == 'voice' && voiceMode)
                VoiceRecorder(
                  key: ValueKey(q['id']),
                  onSubmit: (file, duration) async {
                    setState(() => busy = true);
                    try {
                      final result = await api.uploadVoice(
                        session!['id'],
                        q['id'],
                        file,
                        duration,
                      );
                      if (mounted) {
                        setState(
                          () => feedback = {
                            'correct': true,
                            'pending': true,
                            'xp_change': 0,
                            'explanation': result['detail'],
                            'hint': '',
                            'session': result['session'],
                          },
                        );
                      }
                    } finally {
                      if (mounted) setState(() => busy = false);
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
              if (!(q['kind'] == 'voice' && voiceMode))
                PrimaryButton(
                  label: 'Yanıtı kontrol et',
                  busy: busy,
                  onPressed:
                      (q['kind'] == 'voice' && voiceMode) ||
                          busy ||
                          (['text', 'fill_blank', 'voice'].contains(q['kind'])
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
