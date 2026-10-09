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

void main() {
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
