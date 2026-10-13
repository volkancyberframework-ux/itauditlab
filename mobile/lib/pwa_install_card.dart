import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'pwa_install_platform.dart' as platform;
import 'theme.dart';

class PwaInstallCard extends StatelessWidget {
  final bool? showForTesting;
  final VoidCallback? onInstall;
  const PwaInstallCard({super.key, this.showForTesting, this.onInstall});
  @override
  Widget build(BuildContext context) {
    final show = showForTesting ?? (kIsWeb && !platform.isInstalled());
    if (!show) return const SizedBox.shrink();
    return Card(
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
        leading: const Icon(
          Icons.install_mobile_rounded,
          color: AppColors.teal,
        ),
        title: const Text(
          'Uygulamayı yükle',
          style: TextStyle(fontWeight: FontWeight.w800),
        ),
        subtitle: const Text('GRC Ustası’nı ana ekranına ekle'),
        trailing: const Icon(Icons.chevron_right_rounded),
        onTap:
            onInstall ??
            () {
              if (platform.requestInstall()) return;
              showModalBottomSheet<void>(
                context: context,
                showDragHandle: true,
                builder: (context) => SafeArea(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Ana ekranına ekle',
                          style: TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 16),
                        const Text(
                          'Safari’de app.grcustasi.com adresini aç. Safari menüsündeki Paylaş → Ana Ekrana Ekle adımlarını izle. Android’de tarayıcı menüsünden Uygulamayı yükle seçeneğini kullan.',
                        ),
                        const SizedBox(height: 20),
                        FilledButton(
                          onPressed: () => Navigator.of(context).pop(),
                          child: const Text('Tamam'),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            },
      ),
    );
  }
}
