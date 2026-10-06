# GRC Ustası 1.0.0 (4) — App Store submission

Metadata is in metadata.json. Initial release targets portrait iPhone; iPad-specific screenshots are not required. Store review determines eligibility of account-based content access; removing external purchase calls to action is not an approval guarantee for interactive educational content.

The build uses HTTPS and OS-provided secure storage. ITSAppUsesNonExemptEncryption is false for standard exempt transport/OS cryptography. No advertising identifier, tracking SDK or ATT request is used. Microphone is optional for explicit voice recording; daily reminders are local notifications.

App Privacy: identity-linked name/email/user ID for account functionality; written answers and voice/audio for learning/review; task/product interaction for progress and first-party analytics. Membership status/payment references are linked to accounts; payment card information is handled by Stripe on the website, not collected by the app. Declare no advertising tracking or sale of data. Confirm disclosures against the actual production services when submitting.

Set reviewer contact to the publisher's actual telephone and volkan@grcustasi.com. Enter reviewer demo credentials privately; do not commit them. Choose the appropriate Apple team, confirm copyright ownership, content rights and age-rating questionnaire truthfully. Voice submissions are private to the learner/instructor, not a public social network. No unrestricted web browser is embedded.

Account deletion: Profile > Hesabımı sil requires password and explicit confirmation, informs the user of shared website-login loss, financial retention and the 7-day processing window. Mobile API > Mobil hesap silme talepleri lists requests. The administrator must remove any associated external/legacy personal records or Telegram notices before completing the deletion action. Completion removes mobile progress/XP/recordings, erases the shared login identity, invalidates access and emails a confirmation. Anonymous payment audit references remain. Failed storage cleanup or confirmation email remains retryable. Review this queue daily; no automatic administrator notification or scheduled job is configured.

Apple account owner must accept any updated Developer Program License Agreement. Distribution requires an Apple Distribution certificate and App Store provisioning profile for com.grcustasi.grcUstasi. Build/export:

    flutter build ipa --release --export-method app-store

Upload the resulting IPA through Xcode Organizer/Transporter or authenticated App Store Connect tooling. Do not upload a development/profile build. The release archive lives at build/ios/archive/Runner.xcarchive. Successful archive creation alone does not prove export, upload, review submission or publication.

## Submission status — 2026-10-06

App Store Connect record: https://appstoreconnect.apple.com/apps/6819632974/distribution

Version 1.0.0 build 4 was exported with App Store distribution signing and uploaded successfully via Xcode (Upload succeeded / EXPORT SUCCEEDED). The profile build was separately installed and launched on the connected iPhone. Production code commit 5383536 is pushed. Flutter analysis and 28 mobile tests passed; 81 backend tests passed for the verification release. A native iOS integration test downloaded, decoded and played the production scenario M4A successfully. Four actual 1206×2622 iPhone screenshots are in screenshots/.

App Store Connect status is Waiting for Review. Turkish description, contact information, subtitle, Education category, content rights (confirmed by the publisher), age rating 4+ and privacy policy URL are saved. Seven collected data types have been selected: name, email, audio, customer support, other user content, user ID and product interaction. All seven declarations are completed and the privacy label is published with explicit publisher approval. All are linked to the account and not used for tracking; user ID and product interaction also declare first-party analytics. Build 4 is processed and selected in the version. Free download pricing and availability in 175 territories are configured.

Version 1.0.0 (4) was submitted to App Review on 2026-10-06 at 20:44 GMT+7. Submission ID: 67b69d44-e052-4a9c-be59-6af7a06a5a53. App Store Connect explicitly confirmed “1 Item Submitted” and the submission detail shows Waiting for Review. Four actual 1206×2622 screenshots were uploaded to the required iPhone medium-display slot. The publisher entered and saved the reviewer password privately; Apple preflight passed. Automatic release after approval remains selected. The app is not yet approved or live in the App Store.

Review detail: https://appstoreconnect.apple.com/apps/6819632974/distribution/reviewsubmissions/details/67b69d44-e052-4a9c-be59-6af7a06a5a53

The initial agreement/certificate error and Chrome upload permission blocker were resolved. Monitor Apple review email and this submission for any reviewer questions; administrator processing of private voice feedback and account deletion requests remains operationally required.

Build 3 added email verification to public registrations and new website-payment accounts. Existing/trusted administrator-created accounts remain verified. Build 4 fixes iOS scenario playback by downloading authenticated HTTPS audio to an app-private temporary file before playback, without weakening App Transport Security. Both builds were installed on the connected iPhone. Chrome is signed into the publisher's App Store Connect account.
