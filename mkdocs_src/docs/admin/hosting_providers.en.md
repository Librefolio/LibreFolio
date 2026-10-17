# 🏢 Hosting for Others

This page is for whoever runs LibreFolio for other people: a hosting provider with customers, an
association for its members, or a friend who hosts an instance for the family. On this page, all of
them are the **hosting provider**. A few settings exist for them:

- the **managed profile** says that the instance is run for others;
- the **initial administrator** is created by the instance at its first start, for the customer
  you name, who activates it with a single-use link;
- the **instance block** closes the app but keeps the data, for example when a subscription is not
  paid;
- the **panel token** lets your hosting panel take backups of the instance;
- the **upload limit** caps the size of the archives uploaded for a restore;
- the **legal pages** are your terms of service and privacy policy, linked by the legal notice
  every user sees.

All of them are set with plain environment variables, the same in every LibreFolio and documented
here: they are not tied to any particular provider or cloud.

!!! tip "🏠 Running LibreFolio for yourself?"

    You need nothing on this page. Leave its variables unset: your install is `selfhosted`, the
    default, and it is never blocked. To back it up, see «Back Up the Instance» in
    [CLI Admin Tools](cli_tools.md).

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

Today the profile changes eleven things:

| | `selfhosted` | `managed` |
| --- | --- | --- |
| `GET /api/v1/system/instance` answers | `{"profile": "selfhosted"}` | `{"profile": "managed"}` |
| A `JWT_SECRET` shorter than 32 characters | A warning in the startup log | The server does not start |
| `LIBREFOLIO_TEST_MODE` on, outside LibreFolio's own test runs | An error in the startup log | The server does not start |
| A plugin setting set by an environment variable | Shown read-only in **Settings › Plugins**, *Set by the server*, and listed by `GET /api/v1/settings/plugins` | Not shown in **Settings › Plugins** nor listed, and a save to it is refused as if it did not exist |
| Invitations to donate: the **Buy Me a Coffee** link in the page header, on the sign-in pages, in the **Help & Support** menu and in Settings › About, and the donation popup after a sign-in | Shown | None: Settings › About keeps its share buttons |
| The check for a newer LibreFolio release: at an administrator's sign-in, and **Check for updates** in the changelog | On | Off: you update the instance |
| **Forgot Password?** on the sign-in page | The command that resets a password on the server, under the email form in a closed panel when emails with a link can go out | No command, but *Ask your administrator for a password-reset link: they can create one for your account.* The email form stays when emails with a link can go out |
| The largest archive uploaded for a restore, while `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` is not set | No limit | 500 MB: see [The Upload Limit of a Restore](#restore-upload-limit) |
| Idle risk workers (simulations and optimizations) stop after | 600 seconds | 60 seconds |
| Frame protection: only the app's own pages may show it in a frame | Off | On |
| A report-only Content-Security-Policy on the pages of the web app | Off | On |

- The profile is public: anyone who can reach the server can read it at `/api/v1/system/instance`,
  without signing in. The web app reads it when it starts.
- The web app is the same in both profiles: it follows the profile the server sends it, as in the
  table. Until the server has answered, the places of the table show no coffee link,
  **Forgot Password?** no server command and the changelog no **Check for updates**, and the check
  at an administrator's sign-in waits for the answer: a managed instance never shows them, not even
  for a moment, and never runs that check. On a managed instance, no variable brings back what
  those three rows take away.
- Plugin settings and their variables: see «Plugin Settings» in
  [Environment Variables](configuration.md).
- **Test mode** (`LIBREFOLIO_TEST_MODE`) is for LibreFolio's own test runs, which turn it on and off by themselves. A
  server started without `./dev.py` takes it from its environment, your panel's included: it would serve data
  providers that exist only for the tests, and keep the instance's data in a test folder instead of its data
  directory. So a managed instance does not start with it, and says why:
  `In the managed profile LIBREFOLIO_TEST_MODE must not be on outside a test lane (no LIBREFOLIO_TEST_LANE_ID): …; unset LIBREFOLIO_TEST_MODE`.
  Remove the variable, then start again. See «Startup Checks» in [Configuration](configuration.md).
- Like the upload limit, the last three rows are defaults, each set on its own by its variables, in
  either profile: `RISK_SIMULATION_IDLE_TIMEOUT_SECONDS` and `RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS`
  for the idle risk workers, then `LIBREFOLIO_FRAME_PROTECTION` and `LIBREFOLIO_CSP_REPORT_ONLY` (see
  «Main Options» and «Risk engine workers» in [Environment Variables](configuration.md)). A value you
  set always wins over the profile, even one equal to the `selfhosted` default:
  `RISK_SIMULATION_IDLE_TIMEOUT_SECONDS=600` keeps 600 seconds on a managed instance. If your panel
  or your environment turns `LIBREFOLIO_FRAME_PROTECTION` or `LIBREFOLIO_CSP_REPORT_ONLY` off, the
  log says so at every start, a warning for frame protection and an `info` for the policy, and so do
  the security checks: see «Startup Checks» in [Configuration](configuration.md).
- **Frame protection** adds `X-Frame-Options: SAMEORIGIN` and
  `Content-Security-Policy: frame-ancestors 'self'` to every response: a browser then shows
  LibreFolio in a frame only inside LibreFolio's own pages, whose policy also carries
  `object-src 'none'; base-uri 'self'; form-action 'self'`, three directives that block nothing
  LibreFolio uses (see «Main Options» in [Environment Variables](configuration.md)). If your hosting
  panel, or any page at another address, shows the app in a frame, the browser refuses to display it
  there: set `LIBREFOLIO_FRAME_PROTECTION=false` for those instances.
- **The report-only Content-Security-Policy** blocks nothing. On the pages of the web app (not the
  documentation, not the API), it tells the browser where a page may load its content from; the
  browser lists what falls outside in its developer console and sends no report anywhere: LibreFolio
  has no address to collect them. Today the console shows at least the web app's own inline scripts:
  the one that applies the theme before the page appears, and the start script SvelteKit writes into
  the page. These reports are expected: listing what an enforced policy would block is what this
  report-only phase is for.

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
- Its administrator, from `LIBREFOLIO_ADMIN_EMAIL`, with a setup link your panel delivers: see
  [The Initial Administrator](#initial-admin).
- A `JWT_SECRET` of at least 32 random characters, so that sessions survive restarts. To keep it out
  of `.env`, use `JWT_SECRET_FILE`: see «Secrets» in [Environment Variables](configuration.md).
- Its own instance key: never share one key between instances. See «The Instance Key» in
  [Environment Variables](configuration.md).
- HTTPS in front of it: see [Expose Securely](service_exposure.md) and
  [HTTPS and reverse proxies](configuration.md#session-cookie-secure).
- On Fly.io, `LIBREFOLIO_CLIENT_IP_HEADER=Fly-Client-IP`, so that the limits per visitor's address
  count each visitor apart, not everyone as Fly's proxy. The managed profile does not set it, since
  the header depends on the proxy in front of the instance: see «The Visitor's Address» in
  [Checking Connection Security](connection_checks.md#reverse-proxy).
- A monitor on `GET /api/v1/system/ready`: see the monitoring tip in
  [Advanced Docker](docker_advanced.md).
- If your hosting panel takes its backups: its own `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN`, never shared
  with another instance. See [Backups for Your Hosting Panel](#panel-backups).
- Optionally, a wake-up token of its own, `LIBREFOLIO_WAKE_TOKEN`, if your panel brings the
  instance's prices and exchange rates up to date on its own schedule, for example right after it
  wakes the instance: see [Scheduled Wake-up](sleep_wake.md#wake-sync).
- If your hosting panel shows the app inside a frame: `LIBREFOLIO_FRAME_PROTECTION=false`, since the
  managed profile turns frame protection on.
- Your own support page or email address, `LIBREFOLIO_SUPPORT_URL` (`https://…` or `mailto:…`):
  where the users of the instance ask for help, such as an asset the search does not find. Without
  it, the asset search offers no **Let us know** link: the public GitHub issue a self-hosted
  instance falls back to would publish the instance's profile, its provider codes and your
  customer's asset identifiers. Other help links in the app may still point to LibreFolio's
  GitHub. See «Main Options» in [Environment Variables](configuration.md).
- Your own terms of service and privacy policy, `LIBREFOLIO_TOS_URL` and `LIBREFOLIO_PRIVACY_URL`
  (`https://…`): the legal notice links them for every user. See
  [Your Legal Pages](#legal-pages).
- A restart policy that starts LibreFolio again when it stops by itself: `restart: unless-stopped`
  in Docker Compose (the compose files LibreFolio ships use it) or `always`, `Restart=always` with
  systemd, the `always` policy on a Fly.io Machine. An administrator who confirmed a restore can stop
  the server so that its next start applies it, with **Restore and restart** in
  Settings › Administration › Backup (`POST /api/v1/backup/restore/restart`): a clean stop, which a
  policy that restarts only after a failure (`on-failure`, the default of `fly deploy`) does not
  follow with a start.

---

## 👑 The Initial Administrator {: #initial-admin }

Give each new instance its administrator from the environment. At its first start, the instance
creates the account for the address you name, not yet active, and a setup link that works once, for
72 hours. The link opens the instance's setup page, where your customer chooses the password and is
signed in ([What Your Customer Sees](#initial-admin-setup-page)). Nobody can register first and take
the administrator's place, even on an instance that is reachable from the internet from its first
minute.

### ⚙️ The Variables {: #initial-admin-variables }

| Variable | What it does |
| --- | --- |
| `LIBREFOLIO_ADMIN_EMAIL` | Your customer's email address, the administrator's. Setting it turns the initial administrator on |
| `LIBREFOLIO_ADMIN_USERNAME` | The administrator's username, `admin` when not set: 3 to 50 characters, without `@` |
| `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` | The token of the setup link, chosen by your panel: 32 to 200 characters, only letters, digits and `-` `.` `_` `~`. `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE` reads it from a file instead, as Docker mounts its secrets |

- Set them in the container's environment, or in `.env`, like the other variables of this page.
- A value LibreFolio cannot use stops the server at startup, with an error that names the variable,
  never the token. They are checked at every start, after the setup too.
- Every detail, the case without a token included, is in «The Initial Administrator» in
  [Environment Variables](configuration.md).

### 🧾 Create the Administrator {: #initial-admin-create }

1. Generate the token:

    ```bash
    openssl rand -hex 32
    ```

2. Before you start the new instance, give it the three variables:

    ```bash
    LIBREFOLIO_ADMIN_EMAIL=anna@example.com
    LIBREFOLIO_ADMIN_USERNAME=anna
    LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN=<the 64 characters printed by openssl>
    ```

3. Start the instance. Its log says `Initial administrator created, waiting for its setup link`.
4. Send your customer the link: the instance's address, then `/setup#token=` and the token, such as
   `https://librefolio.example.com/setup#token=<the token>`. LibreFolio neither logs nor emails
   this link: delivering it is up to you, for example in your own «set your password» email.

- ⏱️ The link works once, for 72 hours from that first start. A restart changes nothing: the link
  you sent keeps working until it is used or expires, unless you give the administrator a new
  address ([A New Link](#initial-admin-new-link)) or the account is set up another way
  ([Once the Account Is Active](#initial-admin-active)).
- 🔒 The token travels after the `#` of the link, a part that browsers never send to the server, so
  it stays out of the access logs of the server and of every proxy on the way. Keep it as private as
  a password until your customer has used it.
- 🚪 The first start also sets **Registration** to **By invitation**: after the administrator,
  people join with an invitation link. `LIBREFOLIO_REGISTRATION`, if you set it, still decides.
- 📏 With `LIBREFOLIO_MAX_USERS`, the administrator takes a place from the first start, while it
  waits too.
- ⛔ While the instance is [blocked](#instance-block), the setup link does not work: the setup is
  refused until you unblock the instance, and the 72 hours keep running meanwhile. If the link
  expires in the meantime, give a new one ([A New Link](#initial-admin-new-link)). The setup page
  still opens its form, then refuses the setup and says why: see
  [What Your Customer Sees](#initial-admin-setup-page).
- 🔑 Without `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`, the instance generates the token: it writes the
  link once in its log, and emails it to `LIBREFOLIO_ADMIN_EMAIL` when its [email](email.md) works
  and `LIBREFOLIO_PUBLIC_URL` is set. A token of your own lets your panel know the link before the
  instance starts, without reading its log.

### 🖥️ What Your Customer Sees {: #initial-admin-setup-page }

The setup page needs no account. When your customer opens the link:

1. The page takes the token out of the address bar at once, so that it stays out of the browser's
   history and bookmarks, then asks the instance whether the link still works.
2. A link that works opens the form: it names the account, by its username, and asks for the
   password twice. The password must meet the rules shown under the field, the instance's own: the
   form sends nothing until it does and the two passwords match. A password manager that saves the
   new password files it under that username.
3. Once the form is sent, the account is active and your customer is signed in. The app opens with
   the [Welcome setup](../user/getting-started.md#welcome-setup), as for any new account.

When the setup cannot go through, the page says why:

| The page shows | When | What to do |
| --- | --- | --- |
| *This link has expired.*, *This link has already been used.*, *This link has been withdrawn.*, *This link is not valid.* or *This link is incomplete: open it again from the message you received.*, then *Ask your hosting provider for a new link. On your own server, run `dev.py user setup-link`.* | The link is more than 72 hours old, was used, was replaced by a newer one, was withdrawn when the administrator's address changed or when the account was set up another way, is unknown to the instance, or lost its token when it was copied; also a link that stops working while the form is open | Give your customer a new link: [A New Link](#initial-admin-new-link). An account set up another way gets none: see [Once the Account Is Active](#initial-admin-active) |
| *The link could not be checked. Try again in a moment.*, with **Retry** | The instance did not answer the check | **Retry** once the instance answers |
| *Password does not meet security requirements* | The password misses one of the instance's rules | Choose a password that meets the rules shown under the field |
| That the setup is refused while the instance is blocked, and no button to send the form any more | The instance is [blocked](#instance-block): the form opens, and the setup is refused once it is sent | Unblock the instance: your customer then opens the link again, within its 72 hours |
| That the setup failed | Any other problem | Send the form again |

### 🔁 A New Link {: #initial-admin-new-link }

If your customer has not used the link within 72 hours, each start of the instance logs a warning:
`The initial administrator's setup link has expired: run ./dev.py user setup-link, or set a new LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`.
Either way gives a new link, which works for 72 hours, and ends the earlier ones:

- **A new token**: generate one, put it in `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` and restart the
  instance (with Docker Compose, `docker compose up -d`: `docker compose restart` keeps the old
  values), then send the new link. Generate a new token each time: a value the instance has already
  seen never gives a new link.
- **The command line**, from a shell on the server:
  `docker compose exec librefolio python dev.py user setup-link` prints a new link, with a token the
  instance generates. See «A New Setup Link for the Initial Administrator» in
  [CLI Admin Tools](cli_tools.md).

Both work before the link expires too, to replace a link that went astray.

To change the address or the username before your customer activates the account, change
`LIBREFOLIO_ADMIN_EMAIL` or `LIBREFOLIO_ADMIN_USERNAME` and restart: the waiting account takes the
new value. If another account already holds it, the log has an error, and the account keeps its
own; its link keeps working.

A new address always needs a new link: the link you sent went to the old address, so it stops
working at the start that gives the account its new one. Put a new token in
`LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` together with the new `LIBREFOLIO_ADMIN_EMAIL`, restart, then
send the new link to the new address. Without a new token, that start logs
`The initial administrator's address changed: the setup link handed over before no longer works; run ./dev.py user setup-link, or set a new LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`;
the starts after it log the warning of an expired link, until you give a new link in one of the two
ways above. The same address with other capitals of the letters A to Z, such as `Anna@example.com`
for `anna@example.com`, is not a new address: the account takes the new spelling and its link keeps
working, as it does when only the username changes.

### ✅ Once the Account Is Active {: #initial-admin-active }

Once your customer has chosen the password, the variables have done their work: every later start
creates nothing and logs `LIBREFOLIO_ADMIN_* ignored: this instance already has accounts`. You can
leave them set, or remove them. On an instance that already has accounts, they create nothing
either.

The setup link is not the only way to set the account up. On the server, `dev.py user activate`
and `dev.py user reset` work on the waiting account as on any other, and so does a password-reset
link made for it, by `dev.py user reset-link` or by another administrator in
[Users & Invitations](users.md#reset-links) (see «Reset a Password or Lock an Account» and «Send a
Password-Reset Link» in [CLI Admin Tools](cli_tools.md)). As soon as the account is activated, or
gets a password, this way, it no longer waits for its setup:

- every setup link it had stops working for good, the one you sent included: the setup page says
  *This link has been withdrawn.*;
- no new link replaces it: `dev.py user setup-link` stops with
  `No administrator account is waiting for its setup link`, and every later start ignores the
  variables, as above, a new token included;
- your customer signs in with the password set that way, once the account is active. Activated
  alone, the account has a password nobody knows until `dev.py user reset` or a reset link gives it
  one; given a password alone, it stays inactive until `dev.py user activate`, or **Reactivate** in
  [Users & Invitations](users.md#pending-setup).

---

## 🔒 Blocking an Instance {: #instance-block }

A hosting provider can block an instance, for example when its subscription is not paid. Users can
still sign in, follow a password-reset link already sent to them, read why the instance is blocked
and sign out, and administrators can still download a backup of the instance; the rest of the app is
closed.
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
  catches up the history sync missed in the meantime and fills the gap the block left, going back
  to each asset's and FX pair's last saved day, up to a year.
- A restore that an administrator confirmed before the block, and that still waits, is not applied
  while the instance is blocked: the first start after the unblock applies it. On the server,
  `backup pending` shows it waiting (`instance_blocked`), and `backup pending --cancel` drops it: see
  «Follow or Cancel a Restore» in [CLI Admin Tools](cli_tools.md). Two consequences:
  - its checked copy keeps its disk space in the data directory for the whole block: `backup pending
    --cancel` frees it;
  - if you update LibreFolio during the block, the first start after the unblock also migrates the
    restored database, checked at the version of then, as any update does; the data of before stays
    aside until that start completes, and if the start fails the next one puts it back.

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
- administrators also get a second card under the message, **Keep a copy of the data**: the backup
  card of **Settings › Administration › Backup**, to back up the whole instance, follow the backup,
  download the archive before the instance is gone, and delete it from the server. The other users
  do not see it: their text tells them to ask their administrator for a backup;
- **Logout** signs out.

The card makes, by default, the same archive as your [hosting panel](#panel-backups): it leaves out
the logs and the instance key, and the card says so. An administrator may choose a secure backup
instead, encrypted with a password of their own: it carries the instance key only when LibreFolio
generated it (`secrets/instance.key`), never a key you configured
([Secure Backups](backup_restore.md#secure)). Keep your copy of the instance's key, its
`secrets/instance.key` or the key you configured, with the data: without it, what LibreFolio
encrypted can no longer be read. See «The Instance Key» in [Environment Variables](configuration.md).

A user still signed in after the restart gets the page as soon as the app asks the server for data.
Once you lift the block and restart, users get the app back at their next page load.

### ✅ What Still Answers {: #what-still-answers }

On a blocked instance, only these API calls answer as usual:

| For | Endpoints |
| --- | --- |
| Signing in and out, and who is signed in | `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me` |
| Following a link already sent: checking it, and setting a new password with a reset link | `POST /api/v1/auth/tokens/inspect`, `POST /api/v1/auth/password-reset` |
| Deleting one's own account, and seeing first what it would delete | `DELETE /api/v1/auth/users/me`, `GET /api/v1/auth/users/me/deletion-preview`: the block page has no button for it yet |
| Taking the data away: a backup of the whole instance, by an administrator or by your hosting panel | For an administrator, `POST /api/v1/backup/instance`, then `GET`, `GET …/file` and `DELETE` on `/api/v1/backup/instance/jobs/{job_id}`, and `GET /api/v1/backup/instance/options`, the rules of a secure backup's password, so that the card can offer a secure backup too: the backup card of the block page calls them ([What Users See](#what-users-see)). For your panel, its [four routes](#panel-jobs), with its token |
| The outcome of a restore, for the page that asked the restart, with the one-time ticket of that request: when the block took effect at that restart, it says that the restore waits for the unblock, and starts nothing | `GET /api/v1/backup/restore/outcome` |
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

A few calls are normally open to anyone: registration (`POST /api/v1/auth/register`), the setup of
the [initial administrator](#initial-admin) (`POST /api/v1/auth/setup`), the address probe
(`GET /api/v1/auth/address-probe`), the reference lists (`GET /api/v1/utilities/*`) and the AI
Export catalogue (`GET /api/v1/ai-export/catalog`). On a blocked instance they answer `401` too. The
setup page and the invitation page then say that the instance is blocked, instead of sending their
visitor to the sign-in page, which would lose the link. The address probe
then cannot confirm a public address, and the check of your instance's address reports it as not
verifiable. From them, a caller without a session can tell that the instance is blocked, and nothing
more: they return no data.

### 📅 The Deletion Date {: #deletion-date }

`LIBREFOLIO_DELETION_DATE` is information for your users: LibreFolio shows it on the block page and
does nothing on that day. Deleting the instance and its data is up to you. The date is checked at
every start, blocked or not, but users see it only on the block page.

---

## 💾 Backups for Your Hosting Panel {: #panel-backups }

Your hosting panel can back up the whole instance and download the archive, with a token instead of
a user's session. It is the same archive as `backup create` on the [command line](cli_tools.md): the
database, the uploaded files, the broker reports and the stress scenarios of every user.

### 🔑 The Token {: #panel-token }

Generate a token:

```bash
openssl rand -hex 32
```

Give it to the instance in `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN`, in the container's environment or in
`.env`, then restart LibreFolio. With Docker Compose, run `docker compose up -d`:
`docker compose restart` keeps the old values.

```bash
LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN=<the 64 characters printed by openssl>
```

- To keep the token out of `.env` and of the container's environment, put it in a file and give the
  file's path in `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN_FILE`, as Docker mounts its secrets: see
  «Secrets in Files» in [Environment Variables](configuration.md).
- The token is at least 32 characters long, all of them visible ASCII characters: no space, no tab,
  no accented letter. A space makes it unusable, even at the end: in a file, the line breaks at its
  end are dropped, spaces are not.
- The panel sends it in one header, `Authorization: Bearer <token>`, and never in the URL, where
  access logs would keep it.
- LibreFolio checks the token at startup, and reads it again at every call: a token it cannot use does
  not stop the server. The start log has an error that names the variable, never the token
  (`check` is `backup.panel_token`: see «Startup Checks» in [Environment Variables](configuration.md)),
  and every call then answers `503` and logs an error that names the variable too:
  `The hosting panel's backup token cannot be used: its routes refuse every request`.
- Anyone who has the token can download all the data of the instance: keep it as private as the
  archives, and call the routes over HTTPS only.

### 🔄 Start, Follow, Download, Delete {: #panel-jobs }

| Step | Route | Answer |
| --- | --- | --- |
| Start a backup | `POST /api/v1/backup/panel/jobs` | `202`, and the job with its `job_id` |
| Follow it | `GET /api/v1/backup/panel/jobs/{job_id}` | The job: its `status` is `running`, then `done` or `failed` |
| Download the archive | `GET /api/v1/backup/panel/jobs/{job_id}/file` | The zip archive |
| Delete it from the server | `DELETE /api/v1/backup/panel/jobs/{job_id}` | `204` |

```bash
TOKEN='<your LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN>'
JOBS=https://librefolio.example.com/api/v1/backup/panel/jobs

# Start a backup: the answer gives its job_id
curl -sS -X POST -H "Authorization: Bearer $TOKEN" "$JOBS"

# Follow it until "status" is "done" (or "failed", with an "error_code")
curl -sS -H "Authorization: Bearer $TOKEN" "$JOBS/<job_id>"

# Download the archive
curl -fsS -H "Authorization: Bearer $TOKEN" -o librefolio-backup.zip "$JOBS/<job_id>/file"

# Delete it from the server once you have it
curl -sS -X DELETE -H "Authorization: Bearer $TOKEN" "$JOBS/<job_id>"
```

- ⏳ While the backup runs, the job gives its `phase` (`preparing`, `database`, `files`,
  `finalizing`) and its progress, `done_bytes` of `total_bytes`. Once it is `done`, `file_name` and
  `file_size` describe the archive. A `failed` job gives its `error_code`: `backup_no_space`,
  `backup_failed` (the server's log has the cause) or `backup_interrupted` (the server stopped
  during the backup).
- 🚦 One backup runs at a time on an instance, whoever started it: an administrator, the
  [command line](cli_tools.md) or your panel. While one runs, a start answers `409`: try
  again later.
- 🕐 The server keeps a finished job and its archive for one hour, then removes them: download the
  archive within the hour, and delete the job as soon as you have it.
- 👀 Your panel sees only the backups it started: any other job, such as one an administrator
  started from the app, answers as if it did not exist.
- 🏷️ The archive records that your panel made it: `backup inspect`, on the
  [command line](cli_tools.md), shows `Made by LibreFolio <version> (panel)`.
- 🗝️ Its archives never hold the instance key («The Instance Key» in
  [Environment Variables](configuration.md)). Keep the key of each
  instance with its archives, from `LIBREFOLIO_INSTANCE_KEY_FILE` or from its `secrets/` folder, and
  hand it over with them: without it, what LibreFolio encrypted can no longer be read.
- 🔒 The four routes keep answering on a [blocked instance](#instance-block): that is when you hand
  the data back to your customer.

### 🚫 When a Call Is Refused {: #panel-refusals }

| Answer | When | `code` |
| --- | --- | --- |
| `404` | `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN` is not set: every route answers as a path that does not exist | — |
| `401` | No token, or not the token of this instance | `backup_panel_unauthorized` |
| `503` | The token is set but cannot be used: shorter than 32 characters, a character that is not visible ASCII, or a `_FILE` that cannot give it. The start log names it already (`check` is `backup.panel_token`), and each call logs it | `backup_panel_unavailable` |
| `404` | A job your panel did not start, or one that does not exist, or no longer does | `backup_job_not_found` |
| `409` | A start while another backup runs | `backup_busy` |
| `409` | A download of a job that has no archive: still running, or failed | `backup_job_not_ready` |
| `409` | A delete while the job runs | `backup_job_running` |
| `507` | A start while the disk of the data directory, or a quota, is full: free some space, then start again | `backup_no_space` |
| `500` | The backup cannot start: the `backups/` folder of the data directory is a link or a file, or cannot be written for another reason. The log has the cause | `backup_folder_unusable`, `backup_failed` |

The `code` comes in the `detail` of the answer, with a `message` in English:

```json
{"detail": {"code": "backup_panel_unauthorized", "message": "A valid panel token is required"}}
```

---

## 📤 The Upload Limit of a Restore {: #restore-upload-limit }

To check an archive for a restore, an administrator uploads it to the instance from
Settings › Administration › Backup
([Restore from Settings › Administration › Backup](backup_restore.md#restore-settings)), through
`PUT /api/v1/backup/restore/upload`; the instance then checks it on a copy, as
`backup restore --dry-run` does on the [command line](cli_tools.md). On an instance you host, the
administrator is your customer: `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` is how you cap the size of the
archives they can upload.

| `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` | Largest archive accepted |
| --- | --- |
| Not set, or empty | No limit on a `selfhosted` instance; 500 MB in the [managed profile](#managed-profile) |
| `0` | No limit, in both profiles |
| A whole number, such as `2048` | That many megabytes, of 1024 × 1024 bytes each |

```bash
LIBREFOLIO_BACKUP_MAX_UPLOAD_MB=2048
```

- Set it in the container's environment or in `.env`, then restart LibreFolio, as for the token.
- An archive over the limit answers `413`, with the code `backup_too_large` and the limit in
  `limit_mb`: before anything is written when the request announces its size, otherwise as soon as
  the upload goes past the limit. Nothing of it is kept.
- A proxy in front of LibreFolio must let at least as much through: Nginx with
  `client_max_body_size`, whose default is only 1 MB (`client_max_body_size 2048m;` matches the
  example above), and your platform or CDN, if it limits the size of a request. A `413` without the
  code `backup_too_large` comes from the proxy, not from LibreFolio.
- A value other than a whole number, such as `500MB` or `-1`, does not stop the server: the start log
  already has an error, `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB cannot be used: …` (`check` is
  `backup.upload_limit`), then each upload answers `503` with the code `backup_upload_unavailable`, and
  the log has an error that names the variable: `The upload limit of a restore cannot be read`.
- The disk of the data directory needs room for the archive and, while it is checked, for its copy
  unpacked as well (how much: «Try a Restore on a Copy» in [CLI Admin Tools](cli_tools.md)): short of
  space, the upload answers `507` with the code `backup_no_space`, also when the disk reports itself
  full only at the end of the file, as a network file system or a quota may. The check answers with
  its own code, `no_space`: a `507` when it cannot even start, a refusal of the archive once it runs.
  An upload that cannot be written for another reason answers `500` with the code
  `backup_upload_failed`, and the log has the cause.
- An administrator reads the limit in force in `upload_limit_mb` of
  `GET /api/v1/backup/restore/status`: `0` for no limit, `null` when the value cannot be read.
  Settings › Administration › Backup shows it on its restore card, such as *Archives up to 500 MB.*,
  and refuses a larger file before sending it.
- On a [blocked instance](#instance-block), the upload is refused like the rest of the app, and so
  are the check and the restore: the block lets the data leave, never come in.

---

## ⚖️ Your Legal Pages {: #legal-pages }

Every LibreFolio shows its users a **legal notice**, in both profiles:

- in Settings › About, as the **Legal notice** card ([About](../user/settings/about.md));
- on the Welcome page, under its card;
- under the card of every sign-in page: the login, the registration and **Forgot Password?**, and
  the pages that open the link of an invitation, a password reset, a setup or an email
  verification;
- at the foot of the sidebar, under the version number, while the sidebar is expanded;
- in every text copied with [AI Export](../user/ai-export/index.md), near its end: the notice
  under its title, without the links.

In Settings › About, on the Welcome page and in AI Export, the notice is a disclaimer, which each
user reads in the language of the app; in English:

> LibreFolio helps you keep track of your investments; it does not give financial, tax or legal
> advice. The figures may contain errors: check them before you act on them.

Under the card of the sign-in pages and at the foot of the sidebar, a shorter version fits on one
line.

The notice also links your own pages, when you set them, everywhere but in AI Export:
**Terms of service** for `LIBREFOLIO_TOS_URL`, **Privacy policy** for `LIBREFOLIO_PRIVACY_URL`,
each opened in a new tab. LibreFolio ships no terms and no policy of its own: without the
variables, the notice shows alone.

```bash
LIBREFOLIO_TOS_URL=https://hosting.example.com/terms
LIBREFOLIO_PRIVACY_URL=https://hosting.example.com/privacy
```

- Set them in the container's environment or in `.env`, then restart LibreFolio, as for the other
  variables of this page.
- Each takes a page with `http://` or `https://` and a host name; one trailing slash is removed.
  Not a `mailto:` address, unlike `LIBREFOLIO_SUPPORT_URL`.
- They are public: anyone who can reach the server reads them in the `legal` part of
  `/api/v1/system/instance`, without signing in, as the sign-in pages do.
- A value LibreFolio cannot use, an address with a user name or a password included, does not stop
  the server: that link stays hidden, the notice shows without it, and the log has an error,
  `Invalid instance link`, the first time each server process answers `/api/v1/system/instance`.
  See «Main Options» in [Environment Variables](configuration.md).

---

## 🔗 Related

- 📝 **[Environment Variables](configuration.md)** — Every variable, those of this page included
- 🔐 **[Keep Users Signed In After a Restart](index.md#session-persistence)** — Generating
  `JWT_SECRET`
- 💾 **[CLI Admin Tools](cli_tools.md)** — «Back Up the Instance»: the same archives from the
  command line, a restore tried on a copy, and the restore itself
- 🐳 **[Advanced Docker](docker_advanced.md)** — Compose file, health check and monitoring
- 🔒 For developers: **[Instance Block](../developer/architecture/security.md#instance-block)** —
  The guard on the API and its list
- 🖼️ For developers: **[Frame Protection and the Report-Only Policy](../developer/architecture/security.md#managed-headers)** —
  The headers of the managed profile, directive by directive
- 👑 For developers: **[The Initial Administrator](../developer/architecture/access_control.md#initial-admin)** —
  The startup step, the setup link and its route; the setup page is in
  **[Account Link Pages](../developer/frontend/components/features/auth.md#link-pages)**
- ⚖️ For developers: **[Public Instance Configuration](../developer/architecture/settings.md#public-instance-configuration)** —
  `GET /api/v1/system/instance`, the profile and the `legal` part included
