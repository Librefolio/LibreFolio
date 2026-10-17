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

