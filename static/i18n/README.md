# Public website languages

The shared public-page middleware adds a language selector to the landing pages and sign-in page. Turkish is the original; seven local JSON catalogs cover English, French, Spanish, Japanese, Simplified Chinese, Vietnamese and Arabic. The visitor's preference is saved locally; `?lang=en` (and the other supported codes) also selects a language. Arabic sets `dir="rtl"`.

Catalogs contain automatic translations. `overrides.json` contains contextual corrections for prominent copy. Brand wordmarks, code, input values and editable content are preserved. Existing DOM elements and event listeners remain in place. A mutation observer translates subsequent public UI messages. Unknown copy falls back to the original Turkish. No visitor data or page content is submitted to a translation service at runtime.

After changing public copy, run `python3 scripts/build_site_translations.py`. This development-only script sends public source strings to Google's translation endpoint, reuses existing catalog entries, then applies overrides. Review new translations, particularly technical, commercial and legal wording. It requires network access but no additional Python packages.

Deploy with the project's usual `collectstatic` step. Catalog URLs use Django's static manifest so updated translations receive new URLs. No database migration is required. The admin dashboard, traffic dashboard, APIs and application hosts are outside this middleware's scope.

Backend regression tests: `python manage.py test landing.test_language`. Browser checks cover all seven languages, restoring Turkish, saved preferences, dynamic quiz text, RTL, desktop and narrow mobile layouts.
