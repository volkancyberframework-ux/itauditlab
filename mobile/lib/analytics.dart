import 'api.dart';

class Analytics {
  final Api api;
  Analytics(this.api);
  Future<void> emit(String name) async {
    try {
      await api.request('events/', body: {'name': name});
    } catch (_) {
      /* Analytics must never block learning. */
    }
  }
}
