# GRC Ustası 1.0.0 (2) — App Store submission

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

Version 1.0.0 build 2 was exported with App Store distribution signing and uploaded successfully via Xcode (Upload succeeded / EXPORT SUCCEEDED). The profile build was separately installed and launched on the connected iPhone. Production commit cd59e36 is live; public support/privacy pages return HTTP 200. Flutter analysis, 25 mobile tests and 77 backend tests passed. Four real iPhone screenshots are in screenshots/.

Remaining: verify/save store text (native Safari timed out during entry), upload screenshots, complete categories/subtitle, privacy disclosures and age/content-rights questionnaire, free download price/availability, enter approved demo credentials privately, select processed build, submit review. No review submission or publication has been completed. The initial agreement/certificate error was resolved before the successful export.
