# 🖥️ Front-Utility Tests

Frontend E2E tests for utility components and core UI flows.

## 🔍 What's Tested

These Playwright tests cover fundamental UI components that are used across the entire application:

| Test Suite | Description |
|------------|-------------|
| **Authentication** | Login, registration, logout, session persistence |
| **Account links** | The invitation and password-reset pages, `/invite` and `/reset-password` (`auth-links`) |
| **Settings** | Profile editing, preferences tabs, password change |
| **Users tab** | Settings → Users, for administrators: account actions, invitation and password-reset links with their address check, deletion after its preview (`admin-users`) |
| **Files** | File upload, file list, drag & drop, file deletion |
| **Select Components** | `SearchSelect`, `SimpleSelect`, currency pickers |
| **Image Crop** | `ImageEditModal`, crop presets, zoom, rotation, format export |

### 👥 Users Tab (`admin-users`) {: #admin-users }

`settings/admin-users.spec.ts` drives the **Users** tab of Settings on the lane's real backend.
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
│   └── admin-users.spec.ts  # The Users tab (administrators)
├── files.spec.ts         # File upload and management
├── select.spec.ts        # Dropdown and search select
└── image-crop.spec.ts    # Image editing modal
```

