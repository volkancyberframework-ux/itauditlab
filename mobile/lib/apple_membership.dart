import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'apple_store.dart';

class AppleMembership extends StatefulWidget {
  final AppleStore store;
  final String accountId;
  const AppleMembership({
    super.key,
    required this.store,
    required this.accountId,
  });
  @override
  State<AppleMembership> createState() => _AppleMembershipState();
}

class _AppleMembershipState extends State<AppleMembership> {
  @override
  void initState() {
    super.initState();
    widget.store.bind(widget.accountId);
    widget.store.load();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Premium ol')),
    body: AnimatedBuilder(
      animation: widget.store,
      builder: (context, _) {
        final store = widget.store;
        return Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 660),
            child: ListView(
              padding: const EdgeInsets.all(24),
              children: [
                const Icon(
                  Icons.workspace_premium_rounded,
                  size: 64,
                  color: Color(0xFFE7AE3B),
                ),
                const SizedBox(height: 20),
                Text(
                  'GRC Ustası • Tam erişim',
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: 16),
                const Text(
                  'Tüm öğrenme yolları, vaka ve senaryo görevleri, bilgi kartları, sesli alıştırmalar ve ilerleme takibi.',
                ),
                const SizedBox(height: 24),
                if (store.loading)
                  const Center(child: CircularProgressIndicator()),
                if (store.product != null) ...[
                  Text(
                    '${store.product!.price} / ay',
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    '1 aylık, otomatik yenilenen abonelik. Ödeme Apple hesabından alınır. İptal etmediğin sürece dönem sonunda yenilenir; aboneliğini Apple hesap ayarlarından yönetebilirsin.',
                  ),
                  const SizedBox(height: 20),
                  FilledButton.icon(
                    onPressed: store.busy ? null : store.buy,
                    icon: const Icon(Icons.apple),
                    label: Text(
                      store.busy
                          ? 'Apple işlemi bekleniyor…'
                          : 'Apple ile abone ol',
                    ),
                  ),
                ],
                if (store.error != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 16),
                    child: Text(store.error!, semanticsLabel: store.error),
                  ),
                if (store.product == null && !store.loading)
                  TextButton(
                    onPressed: store.load,
                    child: const Text('Üyelik bilgisini yeniden yükle'),
                  ),
                TextButton(
                  onPressed: store.busy ? null : store.restore,
                  child: const Text('Satın alımları geri yükle'),
                ),
                if (store.pendingVerification.isNotEmpty)
                  TextButton(
                    onPressed: store.busy ? null : store.retryVerification,
                    child: const Text('Satın almayı doğrula'),
                  ),
                if (store.premium)
                  const Text(
                    'Tam erişimin aktif. Öğrenmeye devam edebilirsin.',
                  ),
                TextButton(
                  onPressed: () => launchUrl(
                    Uri.parse('https://apps.apple.com/account/subscriptions'),
                    mode: LaunchMode.externalApplication,
                  ),
                  child: const Text('Apple aboneliğimi yönet'),
                ),
                Wrap(
                  spacing: 12,
                  children: [
                    TextButton(
                      onPressed: () => launchUrl(
                        Uri.parse(
                          'https://www.grcustasi.com/mobiluygulama/gizlilik',
                        ),
                      ),
                      child: const Text('Gizlilik'),
                    ),
                    TextButton(
                      onPressed: () => launchUrl(
                        Uri.parse(
                          'https://www.apple.com/legal/internet-services/itunes/dev/stdeula/',
                        ),
                      ),
                      child: const Text('Kullanım koşulları'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    ),
  );
}
