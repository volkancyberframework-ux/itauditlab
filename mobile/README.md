# GRC Ustası mobile

Flutter iOS/Android client and `/api/mobile/v1/` Django REST API. Uses `core.CustomUser`; no separate password/account database. Backend is the source of truth for answers, XP and progress.

## Run locally

Use Python 3.11+ (the repository's existing django-axes pin requires a newer Python than macOS system Python). From the repository root:

```sh
python3.11 -m venv .mobile-venv
.mobile-venv/bin/pip install -r requirements.txt
export SECRET_KEY='replace-with-a-long-random-local-secret'
export DEBUG=True
export DATABASE_URL=sqlite:////tmp/grc-mobile-dev.sqlite3
.mobile-venv/bin/python manage.py migrate
.mobile-venv/bin/python manage.py seed_mobile
.mobile-venv/bin/python manage.py createsuperuser
.mobile-venv/bin/python manage.py runserver
```

Mobile login only searches accounts with `Mobile` enabled in the user admin. Create a dedicated account for the app and enable this flag; website-only accounts cannot log in to the mobile API. Duplicate emails among mobile-enabled accounts fail closed, while a website-only account with the same email does not interfere. `Last date` is inclusive through that day in the site timezone (Europe/Istanbul); blank means unlimited. Login, every authenticated mobile request and refresh check the current flag/date, including already-issued tokens. The mobile password-reset route only sends mail for mobile-enabled accounts. Existing accounts default to Mobile disabled; migrations enable only the named demo accounts. The seed command preserves existing content and includes the free ten-question demo path. Other paths need authored, published content.

```sh
cd mobile
flutter pub get
flutter run --dart-define=API_BASE_URL=https://YOUR-STAGING-HOST/api/mobile/v1/
```

Use HTTPS for device/staging traffic. The production API is deployed at `https://www.grcustasi.com/api/mobile/v1/`. Apply migrations during deployment before running the new code.

## Content

In existing Django admin (`/bulamazsinki/`), author LearningPath, Module, Question and AudioAsset. Publish paths and questions explicitly. Add options using the QuestionOption inline form and tick correct answers. For text/fill_blank, `answer` contains accepted exact strings (trimmed, case insensitive); this is not semantic AI grading. Option JSON remains a compatibility fallback. The eight question types have generic renderers; image/audio/scenario can use choice answers. AudioAsset can be shared by any number of questions.

Prompt/explanation templates support `{first_name}`, `{full_name}`, `{current_path}`, `{xp}`, `{level}`. Intro and body audio are played in sequence; an AudioAsset with `name_key` matching the case-folded first name adds the name clip. Missing names fall back to intro+body. Gapless behavior needs real-device QA. Name clips should be separately recorded with appropriate pacing.

`core.TestQuestion` is an existing course-specific test model with only single/multiple choice. Mobile Question extends to scenarios, voice/media, paths and XP. Existing tests and course access are unchanged; no automatic content import bypasses legacy course permissions. Accounts share the existing user database but mobile login/access is explicitly enabled and managed independently through the Mobile fields.

Personalized paths select the requested source path and difficulty, prioritize matching `goals`, and size the pool from the daily minute target. `RecommendationProvider` allows a later AI implementation. Questions are still ordered by editorial order during a session. Goals are editorial metadata, not inferred competence.

## Private recordings

Audio, images and recordings use authenticated API downloads. Set `MOBILE_VOICE_ROOT` to a durable, private volume outside `MEDIA_ROOT`. Do not expose it through nginx, a public bucket or Django static serving. Uploads are capped at 180 seconds / 10 MB and checked for an MP4 container header; production media scanning/transcoding and duration verification are outstanding. Authorized owners/staff can stream through the API; Django admin has an authenticated audio preview. Recordings receive no XP automatically until a review policy is implemented. Admin can mark reviewed and enter feedback; automatic email delivery and review XP are not implemented yet. Configure a retention policy, backups and storage encryption before launch.

## Store subscriptions

Uses RevenueCat Flutter SDK for StoreKit/Google Play Billing and RevenueCat REST API for backend verification. The client never grants Premium from its purchase result. Existing Stripe purchases are not automatically treated as mobile subscriptions.

1. Create the apps in App Store Connect and Play Console using bundle IDs from the native projects. iOS: `com.grcustasi.grcUstasi`; Android: `com.grcustasi.grc_ustasi`. Confirm these IDs before registering production products.
2. Create auto-renewing monthly product `grcustasi_premium_monthly` (Android also needs a monthly base plan). Configure Turkey storefront target ₺2,099/month in both consoles using currently available price points. Prices/tiers must be confirmed in the consoles; no price is hardcoded in Flutter.
3. Add both apps/store credentials to RevenueCat. Create entitlement `premium` and a current offering containing the monthly product. Use **Keep with original App User ID** restore behavior; test account switching explicitly. Backend returns a random stable billing UUID per existing user.
4. Backend: set `REVENUECAT_SECRET_KEY` and a random `REVENUECAT_WEBHOOK_TOKEN`. Configure RevenueCat webhook `/api/mobile/v1/subscriptions/webhook/` with `Authorization: Bearer TOKEN`. Webhook events trigger a fresh provider lookup; event payloads cannot directly grant access. Do not put the secret in the app.
5. Build with public SDK keys: `--dart-define=REVENUECAT_IOS_KEY=...` and `--dart-define=REVENUECAT_ANDROID_KEY=...`. These public keys differ per platform.
6. Test purchase, cancellation, expiry, refund, billing retry, grace period, renewal, restore, account switching and cross-device access in both sandboxes. Cancellation retains access until expiry; the current implementation stores it as active during the paid period. Backend entitlement refresh happens after purchase/restore and provider webhook; webhook monitoring/reconciliation must be in place before production.

Reference: [RevenueCat Flutter setup](https://www.revenuecat.com/docs/getting-started/installation/flutter), [restore behavior](https://www.revenuecat.com/docs/projects/restore-behavior), [DRF authentication](https://www.django-rest-framework.org/api-guide/authentication/).

## Verification

```sh
python manage.py test mobile_api --settings=mobile_api.test_settings
python manage.py makemigrations mobile_api --check --dry-run --settings=mobile_api.test_settings
cd mobile
flutter analyze
flutter test test/widget_test.dart
flutter build apk --debug
flutter build ios --simulator --debug
```

Tests isolate the database and email backend. Do not use `mobile_api.test_settings` for production. SQLite tests do not establish PostgreSQL concurrency behavior; run transaction/load tests against staging PostgreSQL before launch. JWT access lasts 10 minutes; refresh lasts 14 days, rotates, and is blacklisted after use. Password changes invalidate old tokens. Logout revokes refresh; already issued access expires within 10 minutes. Secure storage contains tokens, never plaintext passwords.

## Release status and remaining work

This is a working first implementation, **not a store-ready release**. Flutter analysis and the login widget test pass; 21 backend security/learning tests pass with the repository dependencies under Python 3.11. iOS Debug and Profile builds succeeded with Xcode 27, and the Profile app was installed and launched on the connected iPhone 15 Pro Max. Android builds remain unverified because Java runtime is absent. A guarded `core.0022` migration reconciles the existing model/migration drift: it creates missing tables, preserves compatible pre-existing tables and stops if required columns are missing. It does not drop legacy tables on rollback.

Before shipping:

- Install/configure JDK; verify Android builds and complete both platforms’ physical-device tests. Supply release signing through the store pipeline. Android release does not silently use debug keys.
- Configure provider/store credentials and perform real sandbox purchase tests. Add terms, privacy policy, subscription disclosure and account deletion flow; paywall legal links and account deletion are not implemented.
- Finish admin feedback email delivery, verified media processing/retention, full curriculum and content preview/versioning. Module currently organizes content; a separate Challenge hierarchy is not implemented.
- Finish daily goal/streak UX, continue-session recovery, confetti, skeletons, complete design token coverage, reduced-motion behavior, image/audio disk caching and accessibility/60 FPS device QA. Network failures preserve the current question and expose retryable actions; XP is never awarded offline.
- Analytics endpoint accepts only allowlisted event names and stores no client attributes/PII payload. Some client events are wired; complete instrumentation, retention and reporting remain.
- Configure shared cache and gateway IP/login rate limiting for multi-worker deployment. DRF's default cache throttle is an application limit, not sufficient brute-force/DDoS protection.
- Run existing web regression tests, deployment security checks, PostgreSQL concurrency checks, dependency/security audit, backups and store review QA. The existing Django pin is unchanged; assess its support/security status before production.

The pasted specification ends mid-section 28. Later requirements, if any, have not been available.

## Connected iPhone device demo

A separate local backend uses the existing CustomUser model in `/tmp/grc-ustasi-device-demo/db.sqlite3`. It never connects to the production database. Start it from the repository root:

```sh
export GRC_DEMO_HOST="$(ipconfig getifaddr en0)"
/tmp/grc-mobile-py311/bin/python manage.py migrate --settings=mobile_api.dev_settings
/tmp/grc-mobile-py311/bin/python manage.py seed_device_demo --settings=mobile_api.dev_settings
/tmp/grc-mobile-py311/bin/python manage.py runserver 0.0.0.0:8765 --settings=mobile_api.dev_settings --noreload
```

The seed prints the local demo email/password; credentials are saved with mode 0600 in `/tmp/grc-ustasi-device-demo/demo_password.txt`. The account has one eight-question path and a local test entitlement. Store purchases are disabled in this backend. `seed_device_demo` refuses to run against the normal project settings.

Keep Mac and iPhone on the same Wi-Fi. Use the IP printed by `ipconfig getifaddr en0`:

```sh
cd mobile
flutter run -d YOUR_IPHONE_UDID --profile --dart-define=API_BASE_URL=http://YOUR_MAC_LAN_IP:8765/api/mobile/v1/
```

Debug/Profile configurations use `Info-Debug.plist` to allow local HTTP for this isolated test. Release uses `Info.plist` with normal transport security. Use only the demo account in the HTTP LAN build; production accounts require the HTTPS API. Current Xcode requires minimum iOS 15, so the native target has been updated. Profile mode avoids the debug LLDB startup delay observed on this iPhone and can launch from the home screen without the debugger. Mac must remain running for the local backend to respond.

If Flutter is waiting for debugger attachment after installation, the Profile app can be launched directly:

```sh
xcrun devicectl device process launch --device YOUR_IPHONE_UDID --terminate-existing com.grcustasi.grcUstasi
```

The connected-device test confirmed the login screen renders correctly in iPhone dark mode. Login/profile/paths were verified against the LAN backend over HTTP; purchase and complete device session QA remain separate tests.

## Brand logo and app icons

`assets/logo.png` is the supplied GRC Ustası logo, shared by splash/login and launcher generation. To regenerate iOS and Android icons after replacing it:

```sh
dart run flutter_launcher_icons
```

Configuration lives in `flutter_launcher_icons.yaml`. iOS icons use an opaque navy background; Android includes adaptive icons.

Answer feedback now uses a full-screen confetti layer on correct answers and a short damped shake on mistakes. Displayed XP is the confirmed backend amount, including no deduction at zero XP. Reduced-motion preferences suppress the large effects. The isolated SQLite backend begins write transactions with BEGIN IMMEDIATE to prevent analytics/answer write collisions; production PostgreSQL retains per-user transaction locks. Tokens are namespaced by API environment to keep demo credentials separate from live sessions.

Regression run: 148 of 149 existing+mobile backend tests pass; the unchanged student-meeting notification test expects an on_commit callback inside a TestCase transaction and does not execute it. Mobile tests all pass. Flutter login/feedback tests pass.

## Playful brand theme and answer celebrations

The app uses the supplied GRC Ustası logo, navy/gold hero panels, teal controls, raised answer cards/buttons, XP/level tiles and task markers. Light/dark layouts were visually checked at 430 and 320 logical pixels. Correct answers randomly choose confetti, fireworks, stars or XP coins; the previous effect cannot repeat on the next answer. Selection is stable during widget rebuilds, and reduced-motion settings suppress effects. All XP values remain server-confirmed. Celebration lifecycle tests cover leaving while an effect is playing.
