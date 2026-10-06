import 'dart:io';
import 'package:flutter/material.dart';
import 'package:purchases_flutter/purchases_flutter.dart';
import 'main.dart' show api;
import 'theme.dart';

class Paywall extends StatefulWidget {
  final String userId;
  const Paywall({super.key, required this.userId});
  @override
  State<Paywall> createState() => _PaywallState();
}

class _PaywallState extends State<Paywall> {
  Package? product;
  bool busy = false;
  String? error;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final key = Platform.isIOS
          ? const String.fromEnvironment('REVENUECAT_IOS_KEY')
          : const String.fromEnvironment('REVENUECAT_ANDROID_KEY');
      if (key.isEmpty) {
        throw Exception('Mağaza üyeliği henüz yapılandırılmadı.');
      }
      if (await Purchases.isConfigured) {
        await Purchases.logIn(widget.userId);
      } else {
        await Purchases.configure(
          PurchasesConfiguration(key)..appUserID = widget.userId,
        );
      }
      final offerings = await Purchases.getOfferings();
      final packages = offerings.current?.availablePackages ?? [];
      final matches = packages.where(
        (p) =>
            p.storeProduct.identifier == 'grcustasi_premium_monthly' ||
            p.storeProduct.identifier.startsWith('grcustasi_premium_monthly:'),
      );
      if (matches.isEmpty) {
        throw Exception('Üyelik ürünü mağazada bulunamadı.');
      }
      if (mounted) {
        setState(() => product = matches.first);
      }
    } catch (e) {
      if (mounted) {
        setState(() => error = '$e');
      }
    }
  }

  Future<void> buy(bool restore) async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      if (restore) {
        await Purchases.restorePurchases();
      } else {
        await Purchases.purchase(PurchaseParams.package(product!));
      }
      final result = await api.request('subscriptions/sync/', body: {});
      if (result['premium'] != true) {
        throw Exception(
          'Etkin üyelik bulunamadı. Biraz sonra tekrar deneyebilirsin.',
        );
      }
      if (mounted) {
        Navigator.pop(context);
      }
    } catch (_) {
      if (mounted) {
        setState(
          () => error =
              'Üyelik tamamlanamadı. Tekrar deneyebilir veya satın alımını geri yükleyebilirsin.',
        );
      }
    } finally {
      if (mounted) {
        setState(() => busy = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('GRC Ustası Premium')),
    body: ListView(
      padding: const EdgeInsets.all(24),
      children: [
        const Icon(
          Icons.auto_awesome_outlined,
          size: 64,
          color: AppColors.primary,
        ),
        const SizedBox(height: 32),
        Text(
          'Uzmanlığına yatırım yap.',
          style: Theme.of(context).textTheme.headlineLarge,
        ),
        const SizedBox(height: 24),
        const Text(
          'Tüm yollar, sesli senaryolar, kişisel öğrenme planı ve sesli yanıtlar.',
        ),
        const SizedBox(height: 32),
        if (product != null) ...[
          PrimaryButton(
            label: '${product!.storeProduct.priceString} / ay • Premium’a geç',
            busy: busy,
            onPressed: () => buy(false),
          ),
          TextButton(
            onPressed: busy ? null : () => buy(true),
            child: const Text('Satın Alımları Geri Yükle'),
          ),
          const Text(
            'Abonelik otomatik yenilenir. Mağaza hesabından yönetebilir ve iptal edebilirsin.',
          ),
        ],
        if (error != null) Text(error!),
      ],
    ),
  );
}
