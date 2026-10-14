import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'api.dart';

const appleMonthlyProduct = 'grcustasi_premium_monthly';

/// Keeps purchase updates alive when the customer closes the membership screen.
class AppleStore extends ChangeNotifier {
  AppleStore(
    this.api, {
    InAppPurchase? store,
    this.productRetryDelay = const Duration(seconds: 2),
  }) : store = store ?? InAppPurchase.instance;
  final Api api;
  final InAppPurchase store;
  final Duration productRetryDelay;
  String? productLoadDiagnostic;
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
      // Catalog lookup must not be gated by canMakePayments: that API checks
      // purchase restrictions, not whether Apple can return product metadata.
      // An empty StoreKit response can be transient while the storefront starts.
      // Keep StoreKit 2 throughout: the server verifies its signed transactions.
      for (var attempt = 1; attempt <= 3; attempt++) {
        try {
          final result = await store
              .queryProductDetails({appleMonthlyProduct})
              .timeout(const Duration(seconds: 20));
          final matches = result.productDetails.where(
            (item) => item.id == appleMonthlyProduct,
          );
          if (matches.isNotEmpty) {
            product = matches.first;
            productLoadDiagnostic = null;
            return;
          }
          productLoadDiagnostic = result.error == null
              ? 'product_not_found'
              : 'store_error:${result.error!.code}';
        } on TimeoutException {
          productLoadDiagnostic = 'store_timeout';
        } catch (_) {
          productLoadDiagnostic = 'store_request_failed';
        }
        // Only product ID, attempt and error category; no account or receipts.
        debugPrint(
          'Apple product $appleMonthlyProduct: '
          '$productLoadDiagnostic (attempt $attempt/3)',
        );
        if (attempt < 3) await Future<void>.delayed(productRetryDelay);
      }
      error = productLoadDiagnostic == 'product_not_found'
          ? 'Apple şu anda bu aboneliği sunamıyor. Biraz sonra yeniden deneyebilirsin. (Ürün: A01)'
          : 'Apple üyelik bilgisine ulaşılamadı. Biraz sonra yeniden deneyebilirsin. (Bağlantı: A02)';
    } catch (_) {
      productLoadDiagnostic = 'store_request_failed';
      error =
          'Apple üyelik bilgisine ulaşılamadı. Yeniden deneyebilirsin. (A02)';
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
