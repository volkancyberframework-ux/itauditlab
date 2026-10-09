import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'api.dart';
import 'theme.dart';

typedef ExternalLauncher = Future<bool> Function(Uri);

Future<bool> _launchExternal(Uri uri) =>
    launchUrl(uri, mode: LaunchMode.externalApplication);

class ProfileActions extends StatefulWidget {
  final Map<String, dynamic>? contact;
  final VoidCallback onPassword;
  final ExternalLauncher? launcher;
  const ProfileActions({
    super.key,
    required this.contact,
    required this.onPassword,
    this.launcher,
  });
  @override
  State<ProfileActions> createState() => _ProfileActionsState();
}

class _ProfileActionsState extends State<ProfileActions> {
  bool opening = false;
  Future<void> whatsapp() async {
    final phone = widget.contact?['phone']?.toString() ?? '';
    if (!RegExp(r'^[1-9][0-9]{7,14}$').hasMatch(phone) || opening) return;
    setState(() => opening = true);
    final launcher = widget.launcher ?? _launchExternal;
    try {
      bool opened;
      try {
        opened = await launcher(Uri.parse('whatsapp://send?phone=$phone'));
      } catch (_) {
        opened = false;
      }
      if (!opened) opened = await launcher(Uri.https('wa.me', '/$phone'));
      if (!opened) throw const FormatException();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('WhatsApp açılamadı. Tekrar deneyebilirsin.'),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => opening = false);
    }
  }

  @override
  Widget build(BuildContext context) => Column(
    children: [
      if ((widget.contact?['phone'] ?? '').toString().isNotEmpty) ...[
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            style: OutlinedButton.styleFrom(
              foregroundColor: const Color(0xFF137D5E),
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 18),
            ),
            onPressed: opening ? null : whatsapp,
            icon: opening
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.chat_rounded),
            label: const Text(
              "Öğrenme desteği • WhatsApp",
              textAlign: TextAlign.center,
            ),
          ),
        ),
        const SizedBox(height: 12),
      ],
      Card(
        child: ListTile(
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 18,
            vertical: 8,
          ),
          leading: const Icon(Icons.lock_reset_rounded, color: AppColors.teal),
          title: const Text(
            'Şifreni yenile',
            style: TextStyle(fontWeight: FontWeight.w800),
          ),
          subtitle: const Text('Mevcut şifreni güvenle değiştir'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: widget.onPassword,
        ),
      ),
    ],
  );
}

class PasswordChange extends StatefulWidget {
  final Future<void> Function(String, String, String) onSave;
  final bool requiredAtLogin;
  final VoidCallback? onFinished;
  const PasswordChange({
    super.key,
    required this.onSave,
    this.requiredAtLogin = false,
    this.onFinished,
  });
  @override
  State<PasswordChange> createState() => _PasswordChangeState();
}

class _PasswordChangeState extends State<PasswordChange> {
  final current = TextEditingController(),
      password = TextEditingController(),
      confirm = TextEditingController();
  bool busy = false;
  String? error;
  @override
  void dispose() {
    current.dispose();
    password.dispose();
    confirm.dispose();
    super.dispose();
  }

  Future<void> save() async {
    FocusScope.of(context).unfocus();
    if (password.text != confirm.text) {
      setState(() => error = 'Yeni şifreler birbiriyle eşleşmiyor.');
      return;
    }
    if ([
      if (!widget.requiredAtLogin) current.text,
      password.text,
      confirm.text,
    ].any((v) => v.isEmpty)) {
      setState(() => error = 'Bütün şifre alanlarını doldur.');
      return;
    }
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await widget.onSave(current.text, password.text, confirm.text);
      current.clear();
      password.clear();
      confirm.clear();
      if (mounted) {
        if (widget.onFinished != null) {
          widget.onFinished!();
        } else {
          Navigator.pop(context, true);
        }
      }
    } on ApiFailure catch (e) {
      if (mounted) setState(() => error = e.message);
    } catch (_) {
      if (mounted) {
        setState(() => error = 'Şifre yenilenemedi. Tekrar deneyebilirsin.');
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => PopScope(
    canPop: !busy && !widget.requiredAtLogin,
    child: Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: !widget.requiredAtLogin,
        title: const Text('Şifreni yenile'),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            const Icon(
              Icons.lock_reset_rounded,
              color: AppColors.teal,
              size: 60,
            ),
            const SizedBox(height: 24),
            const Text(
              'Yeni şifreni belirle',
              style: TextStyle(fontSize: 25, fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 12),
            Text(
              widget.requiredAtLogin
                  ? 'İlk girişin için kişisel şifreni belirle. E-postayla gelen ilk giriş şifresini bundan sonra kullanmayacaksın.'
                  : 'Şifren değişince diğer cihazlardaki oturumların kapanır. Bu cihazda öğrenmeye devam edebilirsin.',
            ),
            const SizedBox(height: 24),
            AutofillGroup(
              child: Column(
                children: [
                  if (!widget.requiredAtLogin)
                    TextField(
                      controller: current,
                      obscureText: true,
                      enabled: !busy,
                      autofillHints: const [AutofillHints.password],
                      decoration: const InputDecoration(
                        labelText: 'Mevcut şifre',
                      ),
                    ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: password,
                    obscureText: true,
                    enabled: !busy,
                    autofillHints: const [AutofillHints.newPassword],
                    decoration: const InputDecoration(labelText: 'Yeni şifre'),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: confirm,
                    obscureText: true,
                    enabled: !busy,
                    autofillHints: const [AutofillHints.newPassword],
                    decoration: const InputDecoration(
                      labelText: 'Yeni şifre tekrar',
                    ),
                    onSubmitted: (_) {
                      if (!busy) save();
                    },
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            if (error != null) ...[
              Text(
                error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
              const SizedBox(height: 16),
            ],
            PrimaryButton(label: 'Şifreyi yenile', busy: busy, onPressed: save),
          ],
        ),
      ),
    ),
  );
}
