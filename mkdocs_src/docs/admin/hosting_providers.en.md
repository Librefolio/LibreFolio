# 🏢 Hosting for Others

This page is for whoever runs LibreFolio for other people: a hosting provider with customers, an
association for its members, or a friend who hosts an instance for the family. On this page, all of
them are the **hosting provider**. Two switches exist for them:

- the **managed profile** says that the instance is run for others;
- the **instance block** closes the app but keeps the data, for example when a subscription is not
  paid.

Both are set with plain environment variables, the same in every LibreFolio and documented here: they
are not tied to any particular provider or cloud.

!!! tip "🏠 Running LibreFolio for yourself?"

    You need nothing on this page. Leave `LIBREFOLIO_PROFILE`, `LIBREFOLIO_BLOCKED` and
    `LIBREFOLIO_DELETION_DATE` unset: your install is `selfhosted`, the default, and it is never
    blocked.

---

## 🏷️ The Managed Profile {: #managed-profile }

`LIBREFOLIO_PROFILE` says who runs the instance:

- **`selfhosted`** (the default): an install run by its owner;
- **`managed`**: an instance a hosting provider runs for its users.

Set it in `.env` or in the container's environment, then restart LibreFolio (with Docker Compose:
`docker compose up -d`):

```bash
LIBREFOLIO_PROFILE=managed
```

Case and spaces around the value do not matter; any other value stops the server at startup.

Today the profile changes three things:

| | `selfhosted` | `managed` |
| --- | --- | --- |
| `GET /api/v1/system/instance` answers | `{"profile": "selfhosted"}` | `{"profile": "managed"}` |
| A `JWT_SECRET` shorter than 32 characters | A warning in the startup log | The server does not start |
| A plugin setting set by an environment variable | Listed read-only by `GET /api/v1/settings/plugins` | Not listed, and a save to it is refused as if it did not exist |

- The profile is public: anyone who can reach the server can read it at `/api/v1/system/instance`,
  without signing in. The web app reads it when it starts.
- The interface is the same in both profiles.
- Plugin settings and their variables: see «Plugin Settings» in
  [Environment Variables](configuration.md).

### 🔑 A Session Key of 32 Characters or More {: #managed-jwt-secret }

`JWT_SECRET` is the key that signs the login sessions. In the managed profile, a key shorter than 32
characters, set in `JWT_SECRET` or in the file of `JWT_SECRET_FILE`, stops the server at startup:

```text
In the managed profile the session signing key from JWT_SECRET must be at least 32 characters long; it is 12
```

Generate a long random key, put it in `JWT_SECRET`, and start again:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Leaving `JWT_SECRET` unset is allowed in both profiles: every start then makes a new random key, and
your users sign in again after each restart. See
[Keep Users Signed In After a Restart](index.md#session-persistence).

### 📋 For Each Instance

- `LIBREFOLIO_PROFILE=managed`.
- A `JWT_SECRET` of at least 32 random characters, so that sessions survive restarts. To keep it out
  of `.env`, use `JWT_SECRET_FILE`: see «Secrets» in [Environment Variables](configuration.md).
- Its own instance key: never share one key between instances. See «The Instance Key» in
  [Environment Variables](configuration.md).
- HTTPS in front of it: see [Expose Securely](service_exposure.md) and
  [HTTPS and reverse proxies](configuration.md#session-cookie-secure).
- A monitor on `GET /api/v1/system/ready`: see the monitoring tip in
  [Advanced Docker](docker_advanced.md).
- Optionally, a wake-up token of its own, `LIBREFOLIO_WAKE_TOKEN`, if your panel brings the
  instance's prices and exchange rates up to date on its own schedule, for example right after it
  wakes the instance: see [Scheduled Wake-up](sleep_wake.md#wake-sync).

---

## 🔒 Blocking an Instance {: #instance-block }

A hosting provider can block an instance, for example when its subscription is not paid. Users can
still sign in, follow a password-reset link already sent to them, read why the instance is blocked
and sign out; the rest of the app is closed.
LibreFolio deletes nothing: the data stays as it is. The block works in both profiles.

### ⚙️ The Variables {: #block-variables }

| Variable | Values | What it does |
| --- | --- | --- |
| `LIBREFOLIO_BLOCKED` | `1`, `true`, `yes` or `on` block; `0`, `false`, `no` or `off` do not, in any case. Not set or empty: not blocked | Blocks the instance |
| `LIBREFOLIO_DELETION_DATE` | An ISO date, such as `2026-11-14`. Not set or empty: no date | The day you will delete the instance and its data, shown to the users on the block page |

To block an instance and announce its deletion date:

```bash
LIBREFOLIO_BLOCKED=true
LIBREFOLIO_DELETION_DATE=2026-11-14
```

- LibreFolio reads both from its environment. Set them in the container's environment, or in
  `.env`: `./dev.py` and Docker Compose (`env_file: .env`) hand the values of `.env` to the server.
- A change applies when the server restarts. With Docker Compose, run `docker compose up -d`:
  `docker compose restart` keeps the old values.
- To lift the block, remove `LIBREFOLIO_BLOCKED` or set it to `false`, then restart.
- Any other value stops the server at startup, so a typo never leaves the instance blocked or open
  by chance. The error names the variable:

    ```text
    LIBREFOLIO_BLOCKED must be one of 1/0, true/false, yes/no, on/off, or unset
    LIBREFOLIO_DELETION_DATE must be an ISO date such as 2026-11-14, not '14/11/2026'
    ```

- While the instance is blocked, every start logs a warning,
  `Instance blocked by its hosting provider (LIBREFOLIO_BLOCKED): only a few API routes answer`,
  with the deletion date when there is one.
- While the instance is blocked, the [market data scheduler](settings.md#market-data-scheduler)
  runs no job: prices and exchange rates are not updated. Once you lift the block, its first run
  catches up the history sync missed in the meantime, over the **Lookback horizon** of the schedule
  (14 days by default).

### 👀 What Users See {: #what-users-see }

After signing in, users get a full page instead of the app, **This instance is blocked**:

- it says that the hosting provider has blocked the instance, for example because its subscription
  is not paid;
- administrators read that they should settle it with the provider to unblock the instance; the
  other users, that they should ask their administrator for a backup of their data;
- with `LIBREFOLIO_DELETION_DATE`, it adds the date, in the user's language: *The instance and its
  data will be deleted on …*;
- with `LIBREFOLIO_BILLING_URL` ([Environment Variables](configuration.md)),
  administrators also get a **Manage subscription** link to your subscription page, which opens in
  a new tab; the other users do not see it;
- **Logout** signs out.

A user still signed in after the restart gets the page as soon as the app asks the server for data.
Once you lift the block and restart, users get the app back at their next page load.

### ✅ What Still Answers {: #what-still-answers }

On a blocked instance, only these API calls answer as usual:

| For | Endpoints |
| --- | --- |
| Signing in and out, and who is signed in | `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me` |
| Following a link already sent: checking it, and setting a new password with a reset link | `POST /api/v1/auth/tokens/inspect`, `POST /api/v1/auth/password-reset` |
| Deleting one's own account, and seeing first what it would delete | `DELETE /api/v1/auth/users/me`, `GET /api/v1/auth/users/me/deletion-preview`: the block page has no button for it yet |
| The block page | `GET /api/v1/system/block` (signed-in users only), `GET /api/v1/system/instance` |
| Probes and version | `GET /api/v1/system/health`, `GET /api/v1/system/ready`, `GET /api/v1/system/info` |
| The [scheduled wake-up](sleep_wake.md#wake-sync), with its own token: it answers `blocked` and runs no job | `POST /api/v1/system/wake-sync` |

- Your monitoring keeps working: `/system/health` and `/system/ready` answer as on any other
  instance.
- The web app itself is still served: the block covers the API, not the pages of the app.

The list is short on purpose, and it is fixed in the code: there is no setting to change it.

### 🚫 Every Other Call {: #refused-calls }

Every other API call is refused:

- a **signed-in user** gets `423 Locked`, and the web app shows the block page on the first one:

    ```json
    {"detail": {"code": "instance_blocked", "message": "This instance is blocked by its hosting provider"}}
    ```

- a caller **without a valid session** gets `401`.

For a caller without a session, most of the API answers as on any other instance:

- the calls that always need a sign-in answer the same `401` whether or not the instance is blocked;
- the calls of the list above answer as usual: `/system/instance`, `/system/info` and
  `/system/ready` do not reveal the block.

A few calls are normally open to anyone: registration (`POST /api/v1/auth/register`), the address
probe (`GET /api/v1/auth/address-probe`), the reference lists (`GET /api/v1/utilities/*`) and the AI
Export catalogue (`GET /api/v1/ai-export/catalog`). On a blocked instance they answer `401` too. The address probe
then cannot confirm a public address, and the check of your instance's address reports it as not
verifiable. From them, a caller without a session can tell that the instance is blocked, and nothing
more: they return no data.

### 📅 The Deletion Date {: #deletion-date }

`LIBREFOLIO_DELETION_DATE` is information for your users: LibreFolio shows it on the block page and
does nothing on that day. Deleting the instance and its data is up to you. The date is checked at
every start, blocked or not, but users see it only on the block page.

---

## 🔗 Related

- 📝 **[Environment Variables](configuration.md)** — Every variable, `LIBREFOLIO_PROFILE`,
  `LIBREFOLIO_BLOCKED` and `LIBREFOLIO_DELETION_DATE` included
- 🔐 **[Keep Users Signed In After a Restart](index.md#session-persistence)** — Generating
  `JWT_SECRET`
- 🐳 **[Advanced Docker](docker_advanced.md)** — Compose file, health check and monitoring
- 🔒 For developers: **[Instance Block](../developer/architecture/security.md#instance-block)** —
  The guard on the API and its list
