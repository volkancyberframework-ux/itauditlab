import 'package:flutter/material.dart';
import 'theme.dart';

class PasswordResetScreen extends StatefulWidget {
  final String initialEmail;
  final Future<String> Function(String) onRequest;
  const PasswordResetScreen({
    super.key,
    this.initialEmail = '',
    required this.onRequest,
  });
  @override
  State<PasswordResetScreen> createState() => _PasswordResetScreenState();
}

class _PasswordResetScreenState extends State<PasswordResetScreen> {
  late final email = TextEditingController(text: widget.initialEmail);
  bool busy = false;
  String? message;
  bool sent = false;
  @override
  void dispose() {
    email.dispose();
    super.dispose();
  }

  Future<void> submit() async {
    setState(() {
      busy = true;
      message = null;
    });
    try {
      final result = await widget.onRequest(email.text.trim());
      if (mounted) {
        setState(() {
          message = result;
          sent = true;
        });
      }
    } catch (e) {
      if (mounted) setState(() => message = '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Şifremi sıfırla')),
    body: SafeArea(
      child: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          const Icon(
            Icons.mark_email_read_outlined,
            size: 64,
            color: AppColors.teal,
          ),
          const SizedBox(height: 24),
          const Text(
            'Yeni bir başlangıç',
            style: TextStyle(fontSize: 26, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 16),
          const Text(
            'Hesabına kayıtlı e-posta adresini yaz. Hesabın varsa yeni şifre belirlemen için güvenli bir bağlantı göndereceğiz.',
          ),
          const SizedBox(height: 24),
          TextField(
            controller: email,
            enabled: !busy,
            keyboardType: TextInputType.emailAddress,
            autofillHints: const [AutofillHints.email],
            decoration: const InputDecoration(labelText: 'E-posta'),
            onSubmitted: (_) {
              if (!busy) submit();
            },
          ),
          const SizedBox(height: 24),
          PrimaryButton(
            label: sent
                ? 'Bağlantıyı yeniden gönder'
                : 'Şifre sıfırlama e-postası gönder',
            busy: busy,
            onPressed: submit,
          ),
          if (message != null)
            Padding(
              padding: const EdgeInsets.only(top: 20),
              child: Text(
                message!,
                style: TextStyle(
                  color: sent
                      ? AppColors.teal
                      : Theme.of(context).colorScheme.error,
                ),
              ),
            ),
          if (sent)
            const Padding(
              padding: EdgeInsets.only(top: 12),
              child: Text(
                'Gelen kutunu ve spam klasörünü kontrol et. Bağlantıyı açıp yeni şifreni kaydettikten sonra uygulamaya dönebilirsin.',
              ),
            ),
        ],
      ),
    ),
  );
}
