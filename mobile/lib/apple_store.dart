import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'api.dart';

const appleMonthlyProduct = 'grcustasi_premium_monthly';

/// Keeps purchase updates alive when the customer closes the membership screen.
class AppleStore extends ChangeNotifier {
  AppleStore(this.api, {InAppPurchase? store})
    : store = store ?? InAppPurchase.instance;
  final Api api;
  final InAppPurchase store;
  StreamSubscription<List<PurchaseDetails>>? subscription;
  final Map<String, PurchaseDetails> pendingVerification = {};
  ProductDetails? product;
  String? accountId, error;
  bool loading = false, busy = false, premium = false;
  int accessRevision = 0;
  Future<void> updates = Future.value();

  void bind(String id) {
    accountId = id;
    subscription ??= store.purchaseStream.listen(
      (purchases) {
        updates = updates.then((_) => handle(purchases)).catchError((Object _) {
          busy = false;
          error = 'Satın alma kontrol edilemedi. Tekrar deneyebilirsin.';
          notifyListeners();
        });
      },
      onError: (Object _) {
        busy = false;
        error = 'Apple bağlantısı kesildi. Tekrar deneyebilirsin.';
        notifyListeners();
      },
    );
  }

  Future<void> load() async {
    if (loading) return;
    loading = true;
    error = null;
    notifyListeners();
    try {
      if (!await store.isAvailable().timeout(const Duration(seconds: 15))) {
        throw StateError('unavailable');
      }
      final result = await store
          .queryProductDetails({appleMonthlyProduct})
          .timeout(const Duration(seconds: 20));
      if (result.error != null || result.productDetails.isEmpty) {
        throw StateError('missing product');
      }
      product = result.productDetails.single;
    } catch (_) {
      error =
          'Apple üyelik bilgisi alınamadı. Bağlantını kontrol edip yeniden deneyebilirsin.';
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> buy() async {
    if (product == null || accountId == null || busy) return;
    busy = true;
    error = null;
    notifyListeners();
    try {
      final started = await store.buyNonConsumable(
        purchaseParam: PurchaseParam(
          productDetails: product!,
          applicationUserName: accountId,
        ),
      );
      if (!started) throw StateError('not started');
    } catch (_) {
      busy = false;
      error = 'Apple satın alma ekranı açılamadı. Tekrar deneyebilirsin.';
      notifyListeners();
    }
  }

  Future<void> restore() async {
    if (busy || accountId == null) return;
    busy = true;
    error = null;
    notifyListeners();
    try {
      await store.restorePurchases(applicationUserName: accountId);
      // No purchase updates are emitted when the Apple account has no purchases.
      await updates;
    } catch (_) {
      error = 'Satın alımlar geri yüklenemedi. Tekrar deneyebilirsin.';
    } finally {
      busy = false;
      notifyListeners();
    }
  }

  Future<void> retryVerification() async {
    if (busy || pendingVerification.isEmpty) return;
    busy = true;
    notifyListeners();
    updates = updates.then((_) => handle(pendingVerification.values.toList()));
    await updates;
  }

  Future<void> handle(List<PurchaseDetails> purchases) async {
    for (final purchase in purchases) {
      if (purchase.productID != appleMonthlyProduct) continue;
      if (purchase.status == PurchaseStatus.pending) {
        busy = true;
        error = null;
        notifyListeners();
        continue;
      }
      if (purchase.status == PurchaseStatus.error ||
          purchase.status == PurchaseStatus.canceled) {
        busy = false;
        error = purchase.status == PurchaseStatus.error
            ? 'Apple satın alma tamamlanamadı. Tekrar deneyebilirsin.'
            : null;
        notifyListeners();
        continue;
      }
      final key =
          purchase.purchaseID ??
          purchase.verificationData.serverVerificationData;
      pendingVerification[key] = purchase;
      try {
        final result = await api.request(
          'payments/apple/verify/',
          body: {
            'signed_transaction':
                purchase.verificationData.serverVerificationData,
          },
        );
        premium = result['premium'] == true;
        accessRevision++;
        // Acknowledge only after Apple's signed transaction is accepted by our server.
        if (purchase.pendingCompletePurchase) {
          await store.completePurchase(purchase);
        }
        pendingVerification.remove(key);
        error = premium
            ? null
            : 'Satın alma kontrol edildi; aktif üyelik bulunamadı.';
      } catch (_) {
        error =
            'Satın alma henüz hesabına işlenemedi. Tekrar ödemeden “Satın almayı doğrula” ile yeniden kontrol et.';
      }
      busy = false;
      notifyListeners();
    }
  }
}
