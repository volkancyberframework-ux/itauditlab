import 'dart:js_interop';

@JS('grcPwaInstall')
external JSFunction? get _install;
@JS('grcPwaInstalled')
external JSFunction? get _installed;
bool isInstalled() {
  final value = _installed?.callAsFunction();
  return value != null && value.isA<JSBoolean>() && (value as JSBoolean).toDart;
}

bool requestInstall() {
  final callback = _install;
  if (callback == null) return false;
  callback.callAsFunction();
  return true;
}
