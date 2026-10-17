# 🖥️ Front-Utility Tests

Frontend E2E tests for utility components and core UI flows.

## 🔍 What's Tested

These Playwright tests cover fundamental UI components that are used across the entire application:

| Test Suite | Description |
|------------|-------------|
| **Authentication** | Login, registration, logout, session persistence |
| **Account links** | The invitation and password-reset pages, `/invite` and `/reset-password` (`auth-links`) |
| **Settings** | Profile editing, preferences tabs, password change |
| **Users tab** | Settings → Administration → Users, for administrators: account actions, invitation and password-reset links with their address check, deletion after its preview (`admin-users`) |
| **Plugins tab** | Settings → Plugins and **Configure**, as a member and as an administrator: the two personal search preferences, `mockprov`'s settings through an asset's edit dialog, the search's «to configure» row and the 👑 legend (`plugin-settings`) |
| **Files** | File upload, file list, drag & drop, file deletion |
| **Select Components** | `SearchSelect`, `SimpleSelect`, currency pickers |
| **Image Crop** | `ImageEditModal`, crop presets, zoom, rotation, format export |
| **CSP collector** | The collector of Content-Security-Policy violations that every spec carries: its helpers and its baseline, synthetic documents under a report-only policy of their own, the sign-in page under the managed profile's (`csp-collector`) |
| **Cloud smoke** | Thirteen specs of the suite on a managed lane, desktop only, and on any lane only when named: the managed profile's frame protection and report-only policy for real, the collector failing on any violation its baseline does not know (`cloud-smoke`) |

### 👥 Users Tab (`admin-users`) {: #admin-users }

`settings/admin-users.spec.ts` drives the **Users** tab of Settings › Administration on the lane's real backend.
`e2e_test_admin` acts through the page, and only on what the test itself created: accounts it
registers and invitation addresses of its own. After each test, red or green, every invitation
still pending with one of those addresses is revoked, and every account still there deletes
itself. Each action is checked on what the page publishes (`data-*` attributes and the app events
of `notify()`), then read back on the server.

| Case | What it checks |
|------|----------------|
| AUSR-E-01 | An administrator has the tab, and it settles (`data-busy="false"`); a regular member has none, and `?tab=users` opens Profile |
| AUSR-E-02 | The administrator's own row: `data-self="true"`, a link to Profile, no action |
| AUSR-E-03 | Deactivate, confirmed, then reactivate |
| AUSR-E-04 | Promote, confirmed; **Delete** off (`demote-first`) while the account is an administrator; demote, confirmed |
| AUSR-E-05 | A password-reset link: issued from its dialog, shown with its expiry, its token live for that very account |
| AUSR-E-06 | An invitation with an e-mail: its link and live token, listed once **Done**, then revoked, confirmed, after which its token reads `revoked` |
| AUSR-E-07 | The address check of a link, once edited: `match` on the lane's other loopback origin (`localhost` for `127.0.0.1`, or the reverse), through the real CORS path; `unverifiable` on a closed port; `invalid` for an `ftp://` address, with the copy off; `mismatch` from a stubbed stranger, reached by simple `GET`s only; `idle` back on the prefilled address |
| AUSR-E-08 | A deletion: deactivating instead is offered, the preview lists the account's broker with its one transaction, only the username typed exactly enables the button; then the account and its broker are gone |
| AUSR-E-09 | Sign out everywhere, confirmed: the account's open session gets `401`, and the account stays active |
| AUSR-E-10 | Restart the guides, confirmed: every guide the account had skipped is pending again |

Prerequisites: the test users (`e2e_test_admin` an administrator, `e2e_test_user` a regular
member), and on the lane `registration_mode` open and no user limit. The usage line, the limit
banner, the billing link, the refusals with their error codes, and the copy itself are left to the
Vitest component tests: see
[Users Tab and Account Deletion Tests](../frontend/components/features/settings.md#users-tests).
Run it alone with `./dev.py test front-utility admin-users`.

### 🧩 Plugins Tab (`plugin-settings`) {: #plugin-settings }

`settings/plugin-settings.spec.ts` drives **Settings › Plugins** and **Configure** on the lane's
real backend, on desktop only: its member and administrator tests write `mockprov` fields, one
account each, which a second Playwright project would share. Each check reads test ids, `data-*`
attributes, the app events of `notify()` and the API, never a translated text. `mockprov` is
test-only, so the tab never lists it: the tests reach it the way a user reaches a provider already
assigned, from the edit dialog of an asset of their own, assigned `mockprov` over the API.

| Test | What it checks |
|------|----------------|
| Read only, as a member and as an administrator | `?tab=plugins` selects the tab and its read settles (`data-busy`); the price family lists justETF and Borsa Italiana, configured, each personal select on its default and editable, with the options the plugin declares (`preferred_currency`: `all`, `EUR`, `USD`, `CHF`, `GBP`; `preferred_language`: `all`, `it`, `en`), opened and closed with Escape, nothing saved; `mockprov` never listed |
| A member, through **Configure** | The four instance fields read only (`adminOnly`), the instance secret only set or unset; `results_limit` and a personal secret saved — the `PATCH` sends the number as a number and the secret only in `secret_value`, and `pluginSettings.saved` names the fields, never a value — then read back, the API never returning the secret; then **Use the default** and **Clear**, saved, back to the default and unset |
| An administrator, through **Configure** | `mockprov`'s instance `api_key` saved and never shown again (**Replace** opens an empty field, then cancelled), then cleared |
| Search | On a simulated stream (`page.route`), justETF reported `NOT_CONFIGURED` gets its «to configure» row and a 👑 result brings the legend; the row's **Configure** opens justETF's settings over the asset dialog, closed without saving |

Every `mockprov` field a test may write is recorded before its Save and cleared over the API by the
account that wrote it after each test, whatever happened; then the asset is deleted. Prerequisites:
the test users (`e2e_test_user` a member, `e2e_test_admin` an administrator); no environment
variable sets a `mockprov` field on the lane (`LIBREFOLIO_MOCKPROV_API_KEY`,
`LIBREFOLIO_PLUGIN_ASSET_MOCKPROV_*`); the justETF and Borsa Italiana search preferences of both
users on their default. The tab's rules without a browser are in the Vitest files listed in
[Plugin Settings › Tests](../architecture/patterns/plugin_settings.md#tests). Run it alone with
`./dev.py test front-utility plugin-settings`.

### 🛡️ CSP Collector (`csp-collector`) {: #csp-collector }

`layout/csp-collector.spec.ts` tests the [CSP collector](e2e.md#csp-collector) that every spec
carries, with service workers blocked so that every document goes through the spec's own routes.
It runs on any lane: on a self-hosted one the spec adds the managed profile's report-only policy to
the sign-in page itself; on a managed one it lets the lane's own header through and checks that it
equals its copy of `CSP_REPORT_ONLY_POLICY`.

| Test | What it checks |
|------|----------------|
| The pure logic | `cspCollectorEnabled`, `inlineScriptLines`, `isKnown` and `loadBaseline` of `e2e/fixtures/csp.ts`, on synthetic input, without a page: an inline script known by its span; an address known by its path, whole, whatever its origin and query, and a blocked URI that is no absolute URL (`inline`, `eval`) never known by a path; every entry of the baseline well formed (exactly one of `blockedURI` and `blockedPath`, a reason, an owner), every `id` its own |
| The first cloud smoke's findings | The real baseline knows them as the managed lane recorded them, cheetah-grid's global probe and three address checks of a link, each by the entry recorded for it and by no other |
| A synthetic document | Served by the spec under its own report-only `script-src 'self'`: its inline script recorded once, field for field as the page saw it, and run all the same; unknown, and the test passes (`cspFailOnUnknown: false`) |
| Two documents in a row | A navigation: the violations of both recorded, the binding and the listener back with each document |
| An unknown violation | With `cspFailOnUnknown` at its default, the test fails at teardown: an expected failure (`test.fail()`), which Playwright reports passed only if it did fail |
| The sign-in page | `/` under the managed profile's report-only policy reports exactly its two inline scripts, one violation each, both known to the baseline, and every entry naming an inline script of `index.html` matches one of them |
| The kill switch | Runs only in a run started with `E2E_CSP_COLLECTOR=0`, where the synthetic and sign-in tests skip: no binding in the page, nothing recorded, nothing failed |

Prerequisites: populated DB and test users. Run it alone with
`./dev.py test front-utility csp-collector`, and its kill-switch test with
`E2E_CSP_COLLECTOR=0 ./dev.py test front-utility csp-collector`.

### ☁️ Cloud Smoke (`cloud-smoke`) {: #cloud-smoke }

The main pages and the surfaces the managed profile's policies touch (the PDF preview, forms,
frames), on a managed lane: frame protection and the report-only policy for real, with the
[CSP collector](e2e.md#csp-collector) failing on any violation `e2e/csp-baseline.json` does not
know. Thirteen specs of the suite, `CLOUD_SMOKE_SPECS` in `scripts/test_runner/_frontend_utility.py`,
on desktop only (each `<name>.spec.ts` under `frontend/e2e/`): `auth`, `layout/page-policy`,
`layout/csp-collector`, `portfolio/dashboard`, `portfolio/risk-analysis`, `assets/asset-modal`,
`transactions/transactions-table`, `transactions/tx-brim-import`, `files`, `brokers/brokers`,
`settings/security-tab`, `settings/admin-users` and `ai-export/ai-export-panel`.
`layout/legal-and-managed` stays out until its tests of the lane's own answer (LGM-E-01, LGM-E-03)
read the lane's profile: they pin a self-hosted lane, and fail on a managed one by design.

On any lane it runs only when named: registered `named_only=True`, it is left out of
`front-utility all`, `all-frontend` and `all`, their consolidated pass included (see
[Registry Entry Shape](runner_architecture.md#registry-entry-shape)). It refuses to start unless the
lane's `LIBREFOLIO_PROFILE` is `managed`, with an error that says to add
`--lane-setting LIBREFOLIO_PROFILE=managed`, a flag of `./dev.py test` that goes before the
category (see [Lane Settings](index.md#lane-settings)). Prerequisites: that lane, a populated DB
and the test users.

## 🚀 Running

```bash
# Run all front-utility tests
./dev.py test front-utility all

# List the units (actions), each with its description
./dev.py test front-utility --help

# List the Playwright tests of every unit, without running them (Vitest files are not listed)
./dev.py test front-utility all --list

# Run a specific test file
./dev.py test front-utility auth

# Run with visible browser
./dev.py test front-utility all --headed

# The cloud smoke: on any lane only when named (no "all" runs it); it needs a managed lane, whose flag goes before the category
./dev.py test --lane-setting LIBREFOLIO_PROFILE=managed front-utility cloud-smoke
```

## 📂 Test Location

```
frontend/e2e/
├── auth.spec.ts          # Login, register, logout
├── auth-links.spec.ts    # Invitation and password-reset link pages
├── settings.spec.ts      # Settings tabs and profile
├── settings/
│   ├── admin-users.spec.ts      # The Users tab (administrators)
│   └── plugin-settings.spec.ts  # Settings › Plugins and «Configure»
├── files.spec.ts         # File upload and management
├── select.spec.ts        # Dropdown and search select
└── image-crop.spec.ts    # Image editing modal
```

