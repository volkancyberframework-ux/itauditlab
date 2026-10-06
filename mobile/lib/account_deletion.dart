import 'package:flutter/material.dart';
import 'theme.dart';

class AccountDeletionScreen extends StatefulWidget {
  final Future<String> Function(String) onRequest;
  const AccountDeletionScreen({super.key, required this.onRequest});
  @override
  State<AccountDeletionScreen> createState() => _AccountDeletionScreenState();
}

class _AccountDeletionScreenState extends State<AccountDeletionScreen> {
  final password = TextEditingController();
  bool busy = false, confirmed = false, sent = false;
  String? message;
  @override
  void dispose() {
    password.dispose();
    super.dispose();
  }

  Future<void> submit() async {
    setState(() {
      busy = true;
      message = null;
    });
    try {
      final result = await widget.onRequest(password.text);
      password.clear();
      if (mounted) {
        setState(() {
          sent = true;
          message = result;
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
    appBar: AppBar(title: const Text('Hesabımı sil')),
    body: SafeArea(
      child: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          const Icon(Icons.person_remove_outlined, color: Colors.red, size: 60),
          const SizedBox(height: 24),
          const Text(
            'Hesabın ve öğrenme verilerin silinecek',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 16),
          const Text(
            'Bu işlem ilerlemeni, XP kayıtlarını ve gönderdiğin sesli yanıtları kalıcı olarak siler. Ortak GRC Ustası giriş hesabın da kaldırılacağı için websitesindeki hesabına erişimini kaybedersin. Yasal olarak saklanması gereken mali kayıtlar hariçtir.',
          ),
          const SizedBox(height: 16),
          const Text(
            'Talebin en geç 7 gün içinde işlenir. İşlem tamamlanınca e-posta gönderilir. Otomatik yenilenen bir ödeme yoktur. Silme, otomatik ücret iadesi oluşturmaz.',
          ),
          if (!sent) ...[
            const SizedBox(height: 24),
            TextField(
              controller: password,
              enabled: !busy,
              obscureText: true,
              decoration: const InputDecoration(labelText: 'Mevcut şifren'),
            ),
            CheckboxListTile(
              value: confirmed,
              onChanged: busy
                  ? null
                  : (v) => setState(() => confirmed = v == true),
              contentPadding: EdgeInsets.zero,
              title: const Text(
                'Hesabımın ve verilerimin kalıcı olarak silinmesini istiyorum.',
              ),
            ),
            const SizedBox(height: 16),
            PrimaryButton(
              label: 'Hesap silme talebini gönder',
              busy: busy,
              onPressed: confirmed ? submit : null,
            ),
          ],
          if (message != null)
            Padding(
              padding: const EdgeInsets.only(top: 20),
              child: Text(message!),
            ),
        ],
      ),
    ),
  );
}
