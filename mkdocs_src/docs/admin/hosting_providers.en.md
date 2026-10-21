# 🏢 Hosting for Others

This page is for whoever runs LibreFolio for other people: a hosting provider with customers, an
association for its members, or a friend who hosts an instance for the family. On this page, all of
them are the **hosting provider**. A few settings exist for them:

- the **managed profile** says that the instance is run for others;
- the **initial administrator** is created by the instance at its first start, for the customer
  you name, who activates it with a single-use link;
- the **instance block** closes the app but keeps the data, for example when a subscription is not
  paid;
- the **panel tokens** let your hosting panel take backups of the instance, run its scheduled
  wake-up and follow the setup of its administrator, each with a token of its own;
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
| What an archive unpacks to while a restore checks it, while `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` is not set | No limit | 8 times the upload limit: 4000 MB with the 500 MB above, none when the upload limit is `0` |
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
- After you update an instance, each of its users sees once, the next time they open it, what
  changed since the version they last used: a **What's new in LibreFolio** window with those parts
  of the changelog («What's new after an update» in
  [Settings › About](../user/settings/about.md#changelog-modal)). It is the same in both profiles;
  on a managed instance, which never checks for a newer release, it is how your customers learn
  that you updated it. A new account never sees it.
- Plugin settings and their variables: see «Plugin Settings» in
  [Environment Variables](configuration.md).
- **Test mode** (`LIBREFOLIO_TEST_MODE`) is for LibreFolio's own test runs, which turn it on and off by themselves. A
  server started without `./dev.py` takes it from its environment, your panel's included: it would serve data
  providers that exist only for the tests, and keep the instance's data in a test folder instead of its data
  directory. So a managed instance does not start with it, and says why:
  `In the managed profile LIBREFOLIO_TEST_MODE must not be on outside a test lane (no LIBREFOLIO_TEST_LANE_ID of 16 to 128 characters): …; unset LIBREFOLIO_TEST_MODE`.
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
  `Content-Security-Policy: frame-ancestors 'self'` to every response (to a `304 Not Modified`
  only the first, so the browser keeps the policy of its cached copy): a browser then shows
  LibreFolio in a frame only inside LibreFolio's own pages, whose policy also carries
  `object-src 'none'; base-uri 'self'; form-action 'self'`, three directives that block nothing
  LibreFolio uses (see «Main Options» in [Environment Variables](configuration.md)). If your hosting
  panel, or any page at another address, shows the app in a frame, the browser refuses to display it
  there: set `LIBREFOLIO_FRAME_PROTECTION=false` for those instances.
- **The report-only Content-Security-Policy** blocks nothing. On the pages of the web app (not the
  documentation, not the API), it tells the browser where a page may load its content from; the
  browser lists what falls outside in its developer console and sends no report anywhere: LibreFolio
  has no address to collect them. The web app's own inline scripts are allowed by their hashes and
  report nothing: what the console lists is what an enforced policy would block, which is what this
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
- Optionally, a status token of its own, `LIBREFOLIO_PANEL_STATUS_TOKEN`, if your panel follows the
  setup of the instance's administrator: see [The Setup Status](#panel-status).
- If your hosting panel shows the app inside a frame: `LIBREFOLIO_FRAME_PROTECTION=false`, since the
  managed profile turns frame protection on.
- Your own support page or email address, `LIBREFOLIO_SUPPORT_URL` (`https://…` or `mailto:…`):
  where the users of the instance ask for help, such as an asset the search does not find. Without
  it, the asset search offers no **Let us know** link: the public GitHub issue a self-hosted
  instance falls back to would publish the instance's profile, its provider codes and your
  customer's asset identifiers. Other help links in the app may still point to LibreFolio's
  GitHub. See «Main Options» in [Environment Variables](configuration.md).

    **A support form that fills itself in.** With a page, **Let us know** opens it in a new tab
    with the report of the search added to its address, like a prefilled GitHub issue: `title`
    holds the subject, `body` the details, the same text the email would carry. Your form can read
    them with any standard query parser, such as `URLSearchParams` in the browser or
    `urllib.parse.parse_qs` in Python, and fill itself in.
    {: #support-form }

    - **Encoding**: each value goes through `encodeURIComponent`, UTF-8 percent-encoding. A space
      is `%20`, never `+`; a `+` is `%2B`; a line break is `%0A` (LF), not the CRLF of an email
      link.
    - **Placement**: your page's own query is kept, and the two parameters join it after `?` or
      `&`, `title` first, then `body`. A `#fragment` stays at the end. A `title` or `body` already
      in `LIBREFOLIO_SUPPORT_URL` is replaced. One trailing slash is removed from that address, so
      a form at `/support/` opens as `/support?title=…&body=…`: your site must accept that path, or
      keep the query string when it redirects to `/support/`.
    - **An instance reference**, such as `?i=<reference>`, is kept byte for byte: letters, digits,
      `-` `_` `.` `~` or percent-encoding only, no final `/`, not named `title` or `body`. It is
      **public** (`GET /api/v1/system/instance`): a hint for support, never proof of identity.
    - **Content**: in English, the text searched, each provider asked and its outcome (codes only),
      the currency, asset type and identifiers already in the form, and the app's version, profile
      and language. Never the user, an email address, the instance's address or any portfolio
      data.
    - **Logs and history**: unlike an email, the address, with the report in it, appears in your
      support site's access logs and in the user's browser history, like the GitHub issue link.
      The page opens with `noopener noreferrer`: it receives no `Referer`, so not the instance's
      address either.
    - **Clipboard**: the details are still copied on click, for a page that does not read them; a
      message confirms the copy or says it failed.

    For example, with `LIBREFOLIO_SUPPORT_URL=https://help.example.org/support`, on a managed
    instance in English, a search for `XYZ` from a blank form, with `yfinance` as the only provider
    and no result, opens:

    ```text
    https://help.example.org/support?title=LibreFolio%3A%20asset%20not%20found%20%E2%80%94%20XYZ&body=I%20searched%20LibreFolio%20for%20an%20asset%20and%20could%20not%20find%20it.%0A%0ASearch%3A%20XYZ%0AProviders%3A%0A-%20yfinance%3A%200%20results%0ALibreFolio%20v1.3.0%2C%20managed%2C%20language%20en%0A%0AAnything%20else%20that%20helps%20(the%20exchange%2C%20a%20link%20to%20the%20asset's%20page)%3A
    ```

    Decoding it gives exactly the report: `title` is its subject, `body` its details.

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
  address or cancel the link ([A New Link](#initial-admin-new-link)), or the account is set up
  another way ([Once the Account Is Active](#initial-admin-active)).
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
- 📊 Your panel can follow the setup without reading the log either: whether the link waits, was
  used or expired, in [The Setup Status](#panel-status).

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
| *This link has expired.*, *This link has already been used.*, *This link has been withdrawn.*, *This link is not valid.* or *This link is incomplete: open it again from the message you received.*, then *Ask your hosting provider for a new link. On your own server, run `dev.py user setup-link`.* | The link is more than 72 hours old, was used, was replaced by a newer one, was cancelled, was withdrawn when the administrator's address changed or when the account was set up another way, is unknown to the instance, or lost its token when it was copied; also a link that stops working while the form is open, and a link left over on an account already set up, which the setup refuses once the form is sent | Give your customer a new link: [A New Link](#initial-admin-new-link). An account already set up, another way or through another of its links, gets none: see [Once the Account Is Active](#initial-admin-active) |
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

To stop a link that went astray without sending a new one yet, cancel it from a shell on the
server, with the administrator's username (`admin` unless `LIBREFOLIO_ADMIN_USERNAME` names
another): `docker compose exec librefolio python dev.py user deactivate <username>`. Another
administrator of the instance can do the same with **Cancel setup link** in
[Users & Invitations](users.md#cancel-setup), but not for a protected account, whose button is off. The link you sent stops working at once, and every
other setup link of the account with it, while the account keeps waiting for its setup: when you
are ready, give a new link in one of the two ways above. Until then, each start logs the warning
`The initial administrator's setup link was withdrawn (cancelled, or its address changed): run ./dev.py user setup-link, or set a new LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`.
Restarting with the same `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` gives no new link: the instance
has already seen that token.

To change the address or the username before your customer activates the account, change
`LIBREFOLIO_ADMIN_EMAIL` or `LIBREFOLIO_ADMIN_USERNAME` and restart: the waiting account takes the
new value. If another account already holds it, the log has an error, and the account keeps its
own; its link keeps working.

A new address always needs a new link: the link you sent went to the old address, so it stops
working at the start that gives the account its new one. Put a new token in
`LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` together with the new `LIBREFOLIO_ADMIN_EMAIL`, restart, then
send the new link to the new address. Without a new token, that start logs
`The initial administrator's address changed: the setup link handed over before no longer works; run ./dev.py user setup-link, or set a new LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`;
the starts after it log the same warning as after a cancellation, that the link was withdrawn,
until you give a new link in one of the two ways above. The same address with other capitals of
the letters A to Z, such as `Anna@example.com` for `anna@example.com`, is not a new address: the
account takes the new spelling and its link keeps working, as it does when only the username
changes.

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
| Your panel's [setup status](#panel-status), with its own token | `GET /api/v1/panel/status` |

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

## 🔌 Hosting Panel API {: #panel-api }

Your hosting panel calls the instance without a user's session. Each of its calls belongs to a
**scope**, and each scope has a token of its own, which opens that scope and nothing else:

| Scope | For | Routes | Token |
| --- | --- | --- | --- |
| `backup` | Back up the whole instance and download the archive: [Backups for Your Hosting Panel](#panel-backups) | `POST /api/v1/backup/panel/jobs`, then `GET`, `GET …/file` and `DELETE` on `/api/v1/backup/panel/jobs/{job_id}` | `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN` |
| `wake` | Run the price and exchange rate updates that are due, for example right after your panel wakes the instance: [Scheduled Wake-up](sleep_wake.md#wake-sync) | `POST /api/v1/system/wake-sync` | `LIBREFOLIO_WAKE_TOKEN` |
| `status` | Follow the setup of the [initial administrator](#initial-admin): [The Setup Status](#panel-status) | `GET /api/v1/panel/status` | `LIBREFOLIO_PANEL_STATUS_TOKEN` |

The rules of this section hold for the three scopes alike. None of your panel's calls counts as a
visit for the [idle suspension](sleep_wake.md#idle-suspend-activity): each keeps the machine awake
only while it runs.

### 🗝️ A Token per Scope {: #panel-api-tokens }

- **No token, no scope.** A scope whose token is not set is off: its routes answer `404`, as a path
  that does not exist, and LibreFolio writes no line of its own about them. Set only the tokens your
  panel uses.
- **Each token opens its own scope only.** Each scope compares a call with its own token alone: sent
  to another scope, a token is a wrong one. Generate a different token for each scope and for each
  instance, so that a token that leaks opens one scope of one instance.
- **At least 32 visible ASCII characters**: letters, digits and punctuation; no space, no tab, no
  accented letter. `openssl rand -hex 32` prints 64:

    ```bash
    openssl rand -hex 32
    ```

- **In a file, if you prefer.** Each variable has its `_FILE` twin, such as
  `LIBREFOLIO_PANEL_STATUS_TOKEN_FILE`: the path of a file that holds the token, as Docker mounts
  its secrets (see «Secrets in Files» in [Environment Variables](configuration.md)).
  When both are set, the variable itself wins.
- **Set them in the container's environment or in `.env`**, then restart LibreFolio. With Docker
  Compose, run `docker compose up -d`: `docker compose restart` keeps the old values.
- **A token LibreFolio cannot use does not stop the server**: the
  [startup check](#panel-api-check) names it, and its routes answer `503` until you fix it.

### 📨 How a Call Proves Itself {: #panel-api-auth }

Today, a call proves itself with its scope's token, in one header:

```text
Authorization: Bearer <the scope's token>
```

- **Only in that header**, never in the URL, where the access logs of servers and proxies would
  keep it: a token in the query string is not read, and the call gets a `401`.
- **Compared in constant time** with the scope's token, so that how long LibreFolio takes to answer
  tells nothing about the token.
- **Over HTTPS only**: whoever reads a token on the way can use it.

### 🚫 Refused Calls {: #panel-api-refusals }

| Answer | When | `code` |
| --- | --- | --- |
| `404` | The scope is off: its token is not set. The body is `{"detail": "Not Found"}`, as for a path that does not exist | — |
| `401` | No token, or not the scope's token, another scope's token included. The answer carries `WWW-Authenticate: Bearer` | `backup_panel_unauthorized`, `wake_unauthorized` or `panel_status_unauthorized`, by scope |
| `429` | Too many refused tokens from your panel's address: see [The Limit on Refused Tokens](#panel-api-limit). The answer carries `Retry-After`, the seconds to wait | `panel_too_many_attempts`, in every scope |
| `503` | The scope's token is set but cannot be used: shorter than 32 characters, a character that is not visible ASCII, or a `_FILE` that cannot give it. Each call logs an error that names the variable, never the token | `backup_panel_unavailable`, `wake_unavailable` or `panel_status_unavailable`, by scope |

A scope that is off, or whose token cannot be used, answers before anything else: the token of the
call is not read, and nothing is counted. The `code` comes in the `detail` of the answer, with a
`message` in English:

```json
{"detail": {"code": "panel_too_many_attempts", "message": "Too many refused panel credentials from this address"}}
```

### 🚦 The Limit on Refused Tokens {: #panel-api-limit }

LibreFolio counts the tokens it refuses, per address:

- **20 refused tokens in 10 minutes**, and every call from that address gets `429`, to every scope,
  until fewer than 20 of its refusals are less than 10 minutes old: `Retry-After` gives the seconds
  to wait. LibreFolio does not read the token of a call it answers `429`, so the right token waits
  too.
- **Every `401` counts**, whatever its scope: no token, a wrong one, another scope's. The three
  scopes share one count: a panel that keeps sending a wrong backup token also waits for its
  wake-up and its status calls.
- **Nothing else counts**: not a call with the right token, not a `429`, not the `404` of a scope
  that is off, nor the `503` of a token that cannot be used.
- **One address, one count**: an IPv6 address counts by its `/64`. Behind a reverse proxy that
  LibreFolio does not trust, every caller has the proxy's address: LibreFolio then counts nothing,
  rather than let one caller's refusals make every caller wait. See «When LibreFolio Does Not Trust
  Your Proxy» in [Checking Connection Security](connection_checks.md#reverse-proxy).
- **In memory**: each server process keeps its own count, and a restart forgets it.

### 📋 In the Log {: #panel-api-log }

Every call to a scope that is on writes one line, `Hosting panel request`:

| Level | `outcome` | When | With |
| --- | --- | --- | --- |
| ℹ️ `info` | `accepted` | The right token: the route then answers as usual | — |
| ⚠️ `warning` | `refused` | The `401` | `reason`: `missing`, no token in the header; `mismatch`, another token |
| ⚠️ `warning` | `limited` | The `429` | `retry_after`, the seconds of `Retry-After` |
| ⚠️ `warning` | `unavailable` | The `503` | `reason`: `unusable`. Just before it, an error line names the variable and what is wrong |

- Every line also carries `scope` (`backup`, `wake` or `status`), `method`, `path` (without the
  query string), `credential`, the kind of credential the call presented (`token`), and the
  `request_id` of the request.
- It never carries the token, the value sent, a header, the query string or your panel's address:
  uvicorn's access line, which the web server writes for every request, has the address.
- The error line before an `unavailable` one is the scope's own:
  `The hosting panel's backup token cannot be used: its routes refuse every request`
  ([The Token](#panel-token)),
  `The wake-up token cannot be used: the scheduled wake-up refuses every request`
  ([Turning It On](sleep_wake.md#wake-sync-token)), or
  `The panel status token cannot be used: the status route refuses every request`.
- A call to a scope that is off writes no such line.

### 🩺 The Startup Check {: #panel-api-check }

At every start, LibreFolio checks the tokens of the three scopes, in two checks, and logs an error
for each one that fails. The **Security** tab of Settings › Administration shows the same checks
(«Security» in [Global Settings](settings.md)).

| `check` | Tokens | Passed | An error |
| --- | --- | --- | --- |
| `platform.hosting_panel` | `LIBREFOLIO_WAKE_TOKEN` and `LIBREFOLIO_PANEL_STATUS_TOKEN` | Neither is set: both scopes are off. Or each one that is set can be used | One or both cannot be used: their routes answer `503` to every call until you fix them. The line names the variables and why, never a token: `A hosting panel token cannot be used, and its route answers 503 to every call: LIBREFOLIO_PANEL_STATUS_TOKEN (PANEL_STATUS_TOKEN_TOO_SHORT)` |
| `backup.panel_token` | `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN` | Not set: the backup scope is off. Or it can be used | It cannot be used: see [The Token](#panel-token) |

- The reasons of `platform.hosting_panel` are `…_TOO_SHORT`, fewer than 32 characters;
  `…_NOT_VISIBLE_ASCII`, a space, a tab or another character outside visible ASCII; and
  `FILE_UNREADABLE`, a `_FILE` that cannot give the token.
- A check that passes writes nothing in the log.

### 📊 The Setup Status {: #panel-status }

`GET /api/v1/panel/status` tells your panel where the setup of the
[initial administrator](#initial-admin) stands: whether your customer has used the setup link, and
until when the link works. Turn it on with a token of its own in `LIBREFOLIO_PANEL_STATUS_TOKEN`, as
in [A Token per Scope](#panel-api-tokens), then:

```bash
curl -sS -H "Authorization: Bearer $LIBREFOLIO_PANEL_STATUS_TOKEN" \
  https://librefolio.example.com/api/v1/panel/status
```

```json
{"admin_setup": "pending", "setup_expires_at": "2026-10-23T09:12:44.512312Z"}
```

| `admin_setup` | What it means | `setup_expires_at` |
| --- | --- | --- |
| `none` | No setup link was ever issued, as on an instance started without `LIBREFOLIO_ADMIN_EMAIL`; or the account it was for has been deleted since | `null` |
| `pending` | The latest setup link is still valid: not used, not withdrawn and not expired | When the link stops working |
| `done` | The setup is complete: your customer chose the password through the link, or the account was set up another way ([Once the Account Is Active](#initial-admin-active)) | `null` |
| `expired` | The latest link is more than 72 hours old, or was withdrawn: cancelled, or the administrator's address changed. A new link makes it `pending` again: [A New Link](#initial-admin-new-link) | `null` |

- The answer holds these two keys and nothing else: no username, no email address, no count of
  accounts.
- `setup_expires_at` is an ISO 8601 date and time in UTC, given only while the state is `pending`.
- It answers on a [blocked instance](#instance-block) too, as on any other. A `pending` link there
  still waits for the unblock: the setup is refused until then, and its 72 hours keep running.
- Without `LIBREFOLIO_PANEL_STATUS_TOKEN` it answers `404`. Its other refusals are those of every
  scope ([Refused Calls](#panel-api-refusals)), with the codes `panel_status_unauthorized` and
  `panel_status_unavailable`.

---

## 💾 Backups for Your Hosting Panel {: #panel-backups }

Your hosting panel can back up the whole instance and download the archive, with a token instead of
a user's session. It is the same archive as `backup create` on the [command line](cli_tools.md): the
database, the uploaded files, the broker reports and the stress scenarios of every user.

These routes are the `backup` scope of the [Hosting Panel API](#panel-api), which holds the rules
the three scopes share: the header, the `401`, the `429` and the log line.

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
| `429` | Too many refused tokens from your panel's address: see [The Limit on Refused Tokens](#panel-api-limit) | `panel_too_many_attempts` |
| `503` | The token is set but cannot be used: shorter than 32 characters, a character that is not visible ASCII, or a `_FILE` that cannot give it. The start log names it already (`check` is `backup.panel_token`), and each call logs it | `backup_panel_unavailable` |
| `404` | A job your panel did not start, or one that does not exist, or no longer does | `backup_job_not_found` |
| `409` | A start while another backup runs. When it is a backup your panel started, the answer adds its `job_id` and `origin` (`panel`): follow that job instead of starting another | `backup_busy` |
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

The upload limit bounds the archive as it is sent, compressed: a zip can unpack to far more than its
own size, and the check unpacks it on the disk of the data directory.
`LIBREFOLIO_BACKUP_MAX_RESTORE_MB` bounds what an archive unpacks to, from the sizes its manifest
declares, before the check unpacks anything.

| `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` | Largest size an archive unpacks to |
| --- | --- |
| Not set, or empty | No limit on a `selfhosted` instance; in the [managed profile](#managed-profile), 8 times the upload limit: 4000 MB with its default 500 MB, 16384 MB with the `2048` above, none when the upload limit is `0` |
| `0` | No limit, in both profiles |
| A whole number, such as `16384` | That many megabytes, of 1024 × 1024 bytes each |

- Why 8: a database shrinks to about a quarter of its size in an archive, and uploaded images, PDF
  files and spreadsheets barely shrink. An archive heavy with its database unpacks to about four
  times its size, so 8 leaves it twice that room, and still bounds what any archive unpacks to at
  4000 MB with the default, where a zip can otherwise unpack to about a thousand times its size.
- An archive over the limit is refused before anything is unpacked: the check fails with the code
  `unpacked_too_large`, and nothing of its copy is left. A secure archive is decrypted first, which
  takes about its own size, then measured the same way.
- A value you set always wins, `0` included. `backup restore` on the command line follows the same
  limit; whoever runs the server lifts it for one command with `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0`
  in front of it («Try a Restore on a Copy» in [CLI Admin Tools](cli_tools.md)).
- A value other than a whole number does not stop the server: the start log already has an error,
  `LIBREFOLIO_BACKUP_MAX_RESTORE_MB cannot be used: …` (`check` is `backup.restore_limit`), then each
  check, `POST /api/v1/backup/restore/stage`, answers `503` with the code
  `backup_restore_unavailable`, the archive kept, and the log has an error. While this variable is
  unset in the managed profile, an upload limit that cannot be used refuses the checks the same way,
  and the start log's line names `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` instead.

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
- 🔌 For developers: **[The Hosting Panel's Access](../developer/architecture/security.md#panel-access)** —
  The dependency of the panel's routes, its limit and its log line
- 🖼️ For developers: **[Frame Protection and the Report-Only Policy](../developer/architecture/security.md#managed-headers)** —
  The headers of the managed profile, directive by directive
- 👑 For developers: **[The Initial Administrator](../developer/architecture/access_control.md#initial-admin)** —
  The startup step, the setup link and its route; the setup page is in
  **[Account Link Pages](../developer/frontend/components/features/auth.md#link-pages)**
- 📊 For developers: **[The Setup's Status](../developer/architecture/access_control.md#setup-status)** —
  How the four states of [The Setup Status](#panel-status) are read from the setup links
- ⚖️ For developers: **[Public Instance Configuration](../developer/architecture/settings.md#public-instance-configuration)** —
  `GET /api/v1/system/instance`, the profile and the `legal` part included
