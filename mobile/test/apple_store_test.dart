import 'dart:async';
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:grc_ustasi/api.dart';
import 'package:grc_ustasi/apple_store.dart';

class FakeStore extends Fake implements InAppPurchase {
  final events = StreamController<List<PurchaseDetails>>.broadcast();
  int completed = 0;
  int queries = 0;
  List<ProductDetailsResponse> responses = [];
  @override
  Future<ProductDetailsResponse> queryProductDetails(Set<String> ids) async {
    expect(ids, {appleMonthlyProduct});
    return responses[queries++];
  }

  PurchaseParam? parameter;
  @override
  Stream<List<PurchaseDetails>> get purchaseStream => events.stream;
  @override
  Future<bool> buyNonConsumable({required PurchaseParam purchaseParam}) async {
    parameter = purchaseParam;
    return true;
  }

  @override
  Future<void> completePurchase(PurchaseDetails purchase) async {
    completed++;
  }
}

ProductDetails monthly() => ProductDetails(
  id: appleMonthlyProduct,
  title: 'Premium',
  description: 'One month',
  price: '₺2.099',
  rawPrice: 2099,
  currencyCode: 'TRY',
);

void main() {
  test('empty storefront response retries and uses Apple price', () async {
    final native = FakeStore()
      ..responses = [
        ProductDetailsResponse(
          productDetails: [],
          notFoundIDs: [appleMonthlyProduct],
        ),
        ProductDetailsResponse(productDetails: [monthly()], notFoundIDs: []),
      ];
    final store = AppleStore(
      Api(),
      store: native,
      productRetryDelay: Duration.zero,
    );
    await store.load();
    expect(native.queries, 2);
    expect(store.product!.price, '₺2.099');
    expect(store.error, isNull);
    expect(store.loading, false);
    store.dispose();
    await native.events.close();
  });
  test(
    'persistent missing product stops after three requests and allows retry',
    () async {
      final missing = ProductDetailsResponse(
        productDetails: [],
        notFoundIDs: [appleMonthlyProduct],
      );
      final native = FakeStore()
        ..responses = [
          missing,
          missing,
          missing,
          ProductDetailsResponse(productDetails: [monthly()], notFoundIDs: []),
        ];
      final store = AppleStore(
        Api(),
        store: native,
        productRetryDelay: Duration.zero,
      );
      await store.load();
      expect(native.queries, 3);
      expect(store.product, isNull);
      expect(store.error, contains('A01'));
      expect(store.productLoadDiagnostic, 'product_not_found');
      expect(store.loading, false);
      await store.load();
      expect(store.product, isNotNull);
      expect(store.error, isNull);
      expect(store.productLoadDiagnostic, isNull);
      store.dispose();
      await native.events.close();
    },
  );
  test(
    'store errors have a distinct diagnostic from missing configuration',
    () async {
      final failed = ProductDetailsResponse(
        productDetails: [],
        notFoundIDs: [],
        error: IAPError(
          source: 'app_store',
          code: 'network',
          message: 'Offline',
        ),
      );
      final native = FakeStore()..responses = [failed, failed, failed];
      final store = AppleStore(
        Api(),
        store: native,
        productRetryDelay: Duration.zero,
      );
      await store.load();
      expect(store.error, contains('A02'));
      expect(store.productLoadDiagnostic, 'store_error:network');
      expect(store.loading, false);
      store.dispose();
      await native.events.close();
    },
  );

  test(
    'server failure never acknowledges; retry accepts without repurchase',
    () async {
      final native = FakeStore();
      bool accepted = false;
      final api = Api(
        client: MockClient((request) async {
          expect(request.url.path, endsWith('/payments/apple/verify/'));
          expect(jsonDecode(request.body), {
            'signed_transaction': 'apple-signed-jws',
          });
          return http.Response(
            accepted ? '{"premium":true}' : '{"detail":"Try again"}',
            accepted ? 200 : 503,
          );
        }),
      );
      final store = AppleStore(api, store: native)
        ..bind('c5d2dc7b-74dd-4e02-a672-67d3178b7083');
      final purchase = PurchaseDetails(
        productID: appleMonthlyProduct,
        purchaseID: 'transaction-1',
        verificationData: PurchaseVerificationData(
          localVerificationData: '',
          serverVerificationData: 'apple-signed-jws',
          source: 'app_store',
        ),
        transactionDate: '1000',
        status: PurchaseStatus.purchased,
      )..pendingCompletePurchase = true;
      await store.handle([purchase]);
      expect(native.completed, 0);
      expect(store.premium, false);
      expect(store.pendingVerification.length, 1);
      accepted = true;
      await store.retryVerification();
      expect(native.completed, 1);
      expect(store.premium, true);
      expect(store.pendingVerification, isEmpty);
      await store.subscription?.cancel();
      await native.events.close();
    },
  );
  test(
    'Apple receives the account UUID and cancellation clears busy state',
    () async {
      final native = FakeStore();
      final store = AppleStore(Api(), store: native)
        ..bind('c5d2dc7b-74dd-4e02-a672-67d3178b7083');
      store.product = ProductDetails(
        id: appleMonthlyProduct,
        title: 'Premium',
        description: 'One month',
        price: '₺2.099',
        rawPrice: 2099,
        currencyCode: 'TRY',
      );
      await store.buy();
      expect(native.parameter!.applicationUserName, store.accountId);
      expect(store.busy, true);
      await store.handle([
        PurchaseDetails(
          productID: appleMonthlyProduct,
          verificationData: PurchaseVerificationData(
            localVerificationData: '',
            serverVerificationData: '',
            source: 'app_store',
          ),
          transactionDate: null,
          status: PurchaseStatus.canceled,
        ),
      ]);
      expect(store.busy, false);
      expect(store.error, isNull);
      await store.subscription?.cancel();
      await native.events.close();
    },
  );
}
