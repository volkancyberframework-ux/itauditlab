# Travel Bootcamp

Six-section Django landing page: `/travelbootcamp` (also accepts a trailing slash).
Every CTA links directly to the single named route `landing:travel_checkout`. The server
creates a new $249 USD Stripe-hosted Checkout URL automatically, so no manually
supplied Payment Link is required. Price, currency and product identity are
server-owned constants in `landing/travel.py`.

## Production configuration

Use the existing Render service and database. Required environment variables:

- `STRIPE_SECRET_KEY`: existing server-only Stripe key with Checkout Session create permission.
- `TRAVEL_BOOTCAMP_WEBHOOK_SECRET`: the signing secret of this dedicated Stripe webhook endpoint.
- `PUBLIC_BASE_URL`: `https://www.grcustasi.com` (existing default).

Register `https://www.grcustasi.com/travelbootcamp/webhook` in the same Stripe
account and mode as the secret key. Subscribe to `checkout.session.completed`
and `checkout.session.async_payment_succeeded`. Save its signing secret in the
Render environment; never commit it or put it in client code.

Apply migrations using the existing Render pre-deploy command (`python manage.py
migrate --noinput`). Checkout requires the Stripe key; the signing secret is independently required for
automated registration and Telegram notifications. Missing webhook configuration
does not prevent opening Stripe Checkout. No existing checkout route is changed.

The existing Telegram helper uses `GRCUSTASI_TELEGRAM_BOT_TOKEN` and
`GRCUSTASI_TELEGRAM_ADMIN_CHAT_ID`, falling back to the existing legacy variables.
A notification is attempted after the registration transaction commits. Failure
leaves `telegram_sent_at` empty and does not fail the webhook or lose the payment.
A repeated webhook retries a pending notification. Retry independently with:

```sh
python manage.py retry_travel_notifications
```

Run that command periodically from the existing operational scheduler if automatic
retries beyond Stripe deliveries are desired. Do not change webhook secrets on
an existing integration; this uses a dedicated endpoint.

## Data and verification

`TravelRegistration` stores normalized unique email, full name, phone, product,
registration timestamp, first strictly following Monday (Europe/Istanbul), paid
status and Telegram delivery timestamp. `TravelPayment` retains each distinct
payment, amount in minor units, currency, Stripe Customer, Session, PaymentIntent
and Event IDs. Repeat purchases retain their transaction history without creating
a second participant. The admin exposes participants and payment history read-only.

Only a signature-verified webhook writes registration/payment records. It requires
paid status, Travel Bootcamp metadata, payment mode, USD 24900, and matching live/test
mode. Database uniqueness protects email, Session, PaymentIntent and Event IDs.
Transient database failures propagate so Stripe can retry.

The success URL and status endpoint only read confirmed records. While a webhook
is pending, the page polls for up to two minutes and offers a manual refresh; it
never declares a payment paid from URL parameters. No PII is returned to the browser.
Success responses disable caching, indexing and referrer transmission.

The success copy says training/contact details will arrive by email. This change
does not provision lesson content, a WhatsApp invitation or an email course sequence;
those operational details must be sent through the course's existing delivery process.

Client analytics emits `travel_bootcamp_cta_click` and
`travel_bootcamp_checkout` to `dataLayer` and as browser custom events; connect these
to the site's analytics destination if needed. No personal data is included.

## Validation

```sh
python manage.py test landing --noinput
python manage.py check
python manage.py makemigrations --check --dry-run
```

Browser verification: 390px mobile layout has no horizontal overflow, six sections,
consistent CTAs, working FAQ and recoverable checkout errors. Reduced-motion settings
disable animation. JavaScript-free checkout works with a direct GET/303 redirect.

## Current activation status (4 October 2026)

Implementation is ready for deployment. A live Stripe product creation attempt was
rejected because the existing CLI restricted key lacks Products Write permission.
No live product, Payment Link or webhook was created, and no payment was taken.
Render is not connected in this task, so the production signing secret and deployment
have not been configured. Resolve these access requirements before advertising sales.

The scoped `makemigrations landing --check --dry-run` passes. The repository-wide
migration check reports pre-existing unmigrated `core` model changes (Bootcamp,
NewsletterLead, PageVisit, BootcampInterest and DigitalProduct.difficulty); this
change deliberately does not generate or apply unrelated core migrations.

Update: the CTA now goes directly to server-generated Stripe Checkout even while webhook
configuration is pending, as requested. This does not bypass webhook verification or
create paid records from success URLs.

A persistent Stripe Payment Link can be configured through the server environment
variable `TRAVEL_BOOTCAMP_PAYMENT_LINK`. When supplied, CTAs link to that URL directly,
and the legacy checkout endpoint redirects there without trying to create a Session.
This public URL is not a credential. Configure the Payment Link's product metadata as
`travel_bootcamp` and its completion redirect to the existing success route; signed
webhooks remain the only source of paid registration records.

Production diagnosis: Stripe rejected `payment_method_types` because the current
Checkout API no longer accepts that parameter. It was removed from every Checkout
creator (landing, travel, legacy bootcamps, memberships and corporate subscription).
Payment methods now follow Stripe Dashboard settings. The local CLI restricted-key
permission issue is separate from this production API compatibility problem.
