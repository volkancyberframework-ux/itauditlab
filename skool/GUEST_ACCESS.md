# Invited community guests

The public onboarding page links to **Misafir Girişi** at `/skooltoplulugu/misafir/`. These accounts authenticate only a `SkoolUser`; they do not grant staff access, paid course enrollment, mobile membership or a Django core login.

New guests authenticate with their invited email and assigned initial password, then must provide their name and set a new password before receiving a community session. The existing notice, introduction, questionnaire, audio, lab and meeting flow follows. Changed passwords cannot be replaced by the initial password. Names and invitation tokens cannot bypass guest authentication. Password hashes bind the session; revocation and account deactivation invalidate access. Five incorrect attempts lock an account for 15 minutes.

Deploy normally, including `python manage.py migrate --noinput`. Migration 0011 creates the account table without embedding email addresses or credentials.

Provision privately with `python manage.py provision_skool_guests --stdin`. Supply a single JSON line with an `emails` array and a `password` string through standard input. In an interactive terminal, disable terminal echo before pasting private input and restore it afterward. `--dry-run` validates and counts without creating records. Email addresses are normalized and deduplicated; existing guest passwords and progress are preserved. The command reports counts only. Never commit real email lists or initial passwords.

Administrators can search for guests under **Topluluk misafir hesapları** and disable access using `Aktif`. Password hashes are never shown in the admin.

Validation: `python manage.py test skool.test_guest_auth skool.tests --settings=mobile_api.test_settings` covers the existing onboarding flow and the guest authentication, forced password change, bypass prevention, session invalidation, lockout, CSRF and provisioning behavior. Keep the test database and mail backend isolated from production.
