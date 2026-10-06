import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'main.dart' show api;
import 'theme.dart';

class Paywall extends StatefulWidget {
  final String userId;
  const Paywall({super.key, required this.userId});
  @override
  State<Paywall> createState() => _PaywallState();
}

class _PaywallState extends State<Paywall> with WidgetsBindingObserver {
  bool busy = false;
  bool opened = false;
  String? error;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && opened) checkAccess();
  }

  Future<void> checkAccess() async {
    try {
      final profile = await api.request('profile/');
      if (mounted && profile['premium'] == true) {
        Navigator.pop(context);
      }
    } catch (_) {
      if (mounted) {
        setState(
          () => error = 'Erişim kontrol edilemedi. Tekrar deneyebilirsin.',
        );
      }
    }
  }

  Future<void> openPayment() async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final data = await api.request('payments/link/', body: {});
      final url = Uri.parse(data['url'] as String);
      if (!await launchUrl(url, mode: LaunchMode.externalApplication)) {
        throw Exception('Browser unavailable');
      }
      opened = true;
    } catch (_) {
      if (mounted) {
        setState(
          () => error = 'Ödeme sayfası açılamadı. Tekrar deneyebilirsin.',
        );
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('GRC Ustası • Tam erişim')),
    body: ListView(
      padding: const EdgeInsets.all(24),
      children: [
        const Icon(
          Icons.auto_awesome_outlined,
          size: 64,
          color: AppColors.primary,
        ),
        const SizedBox(height: 28),
        Text(
          'Uzmanlığına yatırım yap.',
          style: Theme.of(context).textTheme.headlineLarge,
        ),
        const SizedBox(height: 24),
        const Text(
          'Tüm öğrenme yolları, interaktif sorular ve gerçek hayat senaryoları.',
        ),
        const SizedBox(height: 28),
        Text(
          '2.099 TL / 1 ay',
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 24),
        PrimaryButton(
          label: 'GRC Ustası websitesinden öde',
          busy: busy,
          onPressed: openPayment,
        ),
        const SizedBox(height: 16),
        const Text(
          'grcustasi.com/mobiluygulama\nÖdeme doğrulandıktan sonra hesabına 1 aylık tam erişim eklenir. Otomatik yenilenmez.',
        ),
        if (opened)
          TextButton(
            onPressed: checkAccess,
            child: const Text('Ödedim • Erişimi kontrol et'),
          ),
        if (error != null)
          Padding(padding: const EdgeInsets.only(top: 16), child: Text(error!)),
      ],
    ),
  );
}
