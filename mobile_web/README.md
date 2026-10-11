# GRC Ustası web app

Served at https://app.grcustasi.com using the same Flutter screens, authenticated mobile API, users, learning paths, progress, question types, public workshop and private voice-review pipeline as iOS/Android. Apple in-app purchase is only available in the native iOS app; browser membership uses the existing website billing flow. Native daily scheduled notifications are disabled and explained in the web profile. Browser microphone access requires HTTPS and permission. Browser recordings use mono PCM WAV at 16 kHz; native recording retains M4A. Browser audio is downloaded with authenticated fetch and played as an in-memory data URI without exposing access tokens in media URLs.

`app` is reserved from tenant console routing and registered personal hostnames select a separate URL configuration. API calls stay on the app origin and do not require cross-origin authentication. The main marketing site and customer console retain their own routes. File serving is constrained to the generated distribution directory, including traversal and hidden-file rejection.

Build on a workstation with Flutter (Render's Python service does not include Flutter), then commit the generated distribution alongside source changes:

```
cd mobile
flutter pub get
flutter analyze
flutter test
flutter test --platform chrome test/web_media_test.dart
flutter build web --release --no-web-resources-cdn
cd ..
python3 mobile_web/package.py
```

The package script copies build/web into mobile_web/dist. No user content, tokens or secrets are bundled. Compiled JS/HTML/manifest use no-cache; immutable engine assets use one-hour caching. The bootstrap removes the initial loading panel and does not enable an obsolete generated service worker. Add-to-home-screen metadata is provided. This is a browser app, not a separate App Store submission.

Verification includes shared mobile tests, Chrome browser tests for recording blob uploads and authenticated audio data URIs, API WAV validation/private review tests, host routing and private media access tests, and local browser login/learning/audio UI checks. Physical Safari/iPhone and Android microphone recording must still be checked on devices; browser automation did not capture a real microphone. Permissions, background recording and background notifications are controlled by browsers.

Personal addresses are optional, unique lowercase labels set in Profile → Kişisel web adresin. The hostname selects the web app, never an authenticated user. Browser API requests and token storage use the current origin. Names must be 3–30 ASCII characters, start with a letter and end with a letter/digit; platform/service names are reserved. Renaming/removing releases the previous address, with a confirmation in the UI. Deleting a user cascades their address. PostgreSQL advisory locks shared with Organization.save serialize claims across the public mobile tables and municipal_console schema; both sides check existing names in the other schema. Bulk SQL/bulk_create bypassing model save must not be used to assign console subdomains.
