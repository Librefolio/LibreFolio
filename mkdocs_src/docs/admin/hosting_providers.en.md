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
- the **awaiting restore** mode lets your hosting panel put an instance's backup back on a new
  machine, with a signed ticket, before anyone can use that machine;
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
| A second, wider Content-Security-Policy on the pages of the web app, report-only: it blocks nothing | Off | On |

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
  LibreFolio in a frame only inside LibreFolio's own pages. (The three directives
  `object-src 'none'; base-uri 'self'; form-action 'self'` are not part of this switch: every page
  carries them in every profile, see «The Content-Security-Policy» in [Configuration](configuration.md).) If your hosting
  panel, or any page at another address, shows the app in a frame, the browser refuses to display it
  there: set `LIBREFOLIO_FRAME_PROTECTION=false` for those instances.
- **The Content-Security-Policy** is enforced in both profiles, with no switch: on the pages of the web
  app only LibreFolio's own scripts run, and the page may connect only to itself, to the origin of
  `LIBREFOLIO_PUBLIC_URL` and, on a self-hosted install, to GitHub for the check for a newer release
  («The Content-Security-Policy» in [Configuration](configuration.md)). If a proxy or a CDN in front of your
  instances adds a script to the pages (Cloudflare's Rocket Loader or automatic Web Analytics, an
  Nginx `sub_filter`), the browser blocks it: turn it off for your customers' hosts, as that page
  explains. Set `LIBREFOLIO_PUBLIC_URL` for each instance too: a page may also connect to
  that address.
- **The report-only Content-Security-Policy** is a second, wider policy that blocks nothing. On the
  pages of the web app (not the documentation, not the API), it tells the browser where a page may
  load its images, styles, fonts and frames from as well; the browser lists what falls outside in its
  developer console and sends no report anywhere: LibreFolio has no address to collect them. What
  the console lists is what a fully enforced policy would block, which is what this report-only
  phase is for.

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
  [The Initial Administrator](#initial-admin). On a managed instance that administrator is protected: nobody can delete, deactivate or demote it, or reset its password or sign it out as another administrator, and it cannot delete itself or change its email address from the app (`409 ACCOUNT_PROTECTED`, a *Protected* badge in the Users tab; its address is changed from the host, with a confirmation link: [Changing the Administrator's Address](#owner-email-change)), while `./dev.py user …` on the server still can, except deleting, which that command does not do: the emergency exit.
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
  customer's asset identifiers. It is also the **Contact support** link of the page shown while
  [a restore has stopped half way](#restore-interrupted). Other help links in the app may still
  point to LibreFolio's GitHub. See «Main Options» in [Environment Variables](configuration.md).

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

### 📬 Changing the Administrator's Address {: #owner-email-change }

The account that owns a managed instance, the one with the address of `LIBREFOLIO_ADMIN_EMAIL`, cannot
change its own address from the app: it answers `409 ACCOUNT_PROTECTED`. When your customer's contact
changes, you change it from the host, and LibreFolio asks the **new** address to confirm it before
anything moves. The instance remembers which account is its owner (a mark on the account, not
visible in the app or in the API), so changing the variable never makes it lose track of who it is.

1. Update your registry, set `LIBREFOLIO_ADMIN_EMAIL=new.contact@customer.example` and restart the
   instance.
2. At that start LibreFolio emails a confirmation link, valid for **7 days**, to the *new* address
   (it needs [email and `LIBREFOLIO_PUBLIC_URL`](email.md#public-url)). It is sent once: a restart
   while that link is still valid sends nothing more, and a link that expired is replaced at the next
   start.
3. Your customer opens it from the new address. The account moves to the new address, which counts as
   verified, every session of the account ends and the previous address gets a notice that it
   changed. The password does not change: from then on the account signs in with the new address.

Until the link is opened, **nothing changes**: the account keeps its old address, it stays protected
(nobody can delete, deactivate or demote it from the app), and your customer keeps working. If you
change the variable again before the click, the link already sent stops working and the next start
sends a new one for the latest address.

**An address that belongs to another account.** If another account of the instance already has the
new address, nothing is sent and nothing changes: the start logs an error saying that
`LIBREFOLIO_ADMIN_EMAIL` belongs to another account, the owner keeps its address and its
protection, and the other account is *not* protected (only the owner is). Free the address, for
example with `./dev.py user set-email`, or change the variable, and restart. The same applies if the
address is taken between the email and the click: the link is refused and revoked.

**Without email.** If email is off or cannot be used, or `LIBREFOLIO_PUBLIC_URL` is not set, or the
SMTP server refuses the message, LibreFolio writes the link in the startup log as a `warning`, as it
does for the `/setup` link: *Confirmation link for the instance owner's new email address*. Pass it on
to your customer, who must open it. It is written only when the email did not go; and without
`LIBREFOLIO_PUBLIC_URL` it is a path, to put after the address of your server.

**A customer who has not set the password yet.** While the first administrator still waits for its
`/setup` link, nothing of this applies: changing the variable follows
[the rules of the initial administrator](#initial-admin-variables), the waiting account takes the new
address and the links you sent to the old one stop working. The confirmation link is only for an
owner that is already active.

**A link that got lost.** There is no command to send the link again, and the instance never keeps it:
only its fingerprint is stored. If the customer never received it, or it expired, put `LIBREFOLIO_ADMIN_EMAIL`
back to the **old** address and restart (the instance sees no change and revokes the unused link), then set the
**new** address again and restart: a new link goes out. The previous link stays valid for 7 days, so a customer who
finds it can still use it; a restart with the new address in place never sends a second one while it is valid.

**The old address.** When the link is confirmed, the old address receives a short, generic notice that the
address of the account changed. It does not say the new address, so that nobody who still reads the old mailbox
learns it.

**Who counts as the owner.** At a start with no owner recorded, the instance records the account that has the address
of `LIBREFOLIO_ADMIN_EMAIL` as the owner only if it is an **active administrator**. An ordinary account, or a
deactivated administrator, that has that address is not recorded (the start logs an error that does not name the
address or the account) and is not protected as the owner. The first administrator the instance creates for
you is recorded from the start.

!!! note "State of a change"

    The instance knows whether a change is *pending* (waiting for the click, or for a new link at the next start)
    or *blocked* (another account holds the address), and never carries an address. Today this state is not shown
    anywhere in the app or in the hosting panel API: connecting it to the panel's status and to a security check is
    planned work, and until then the startup log is where to look.

### 🔁 Restoring a Backup on a Managed Instance: the Owner {: #restore-owner }

A backup can come from any instance, and whoever prepared it can write anything in it, so on a managed instance nothing in its
accounts, passwords or one-time links is trusted. When an administrator restores a backup from the app, the restore asks which
account of that backup is the owner, and then, in one step:

1. that account gets the address of `LIBREFOLIO_ADMIN_EMAIL`, becomes an active administrator and the **only** owner: the
   owner mark of every other account is removed, so the owner the backup had is no longer protected;
2. its password becomes unusable (nobody can sign in with the password the backup carried, whoever prepared it) and its
   open sessions end;
3. every one-time link of that account that the backup carried is cancelled: its password-reset links are deleted and its
   other links (email verification, setup, email change) are revoked, whatever they said;
4. one new password-reset link is emailed to the address of `LIBREFOLIO_ADMIN_EMAIL`, so the real owner chooses a password.

If the email cannot go (email off or unusable, no `LIBREFOLIO_PUBLIC_URL`, the hourly limit, a refusal by the SMTP server), the
link is written in the **log of the instance** as a `warning`, *Password-reset link for the instance owner*, and nowhere else:
the report of the restore says only that the link is in the log, and never contains it, because the report can be read by any
administrator. Pass the link to the owner. When the email went, the link is in no log.

If the first start after the restore is repeated, the step is repeated too: the previous link stops working and a new one is
sent. A restore made from the hosting panel does none of this. The whole restore is described in
[Backup & Restore](backup_restore.md).

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
- Your panel's [restore routes](#panel-restore) pass the block too, so that a call without a valid
  ticket learns nothing about it; a call with a valid ticket gets `423` with the code
  `instance_blocked`, and no restore: the block lets the data leave, never come in.
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
(`GET /api/v1/auth/address-probe` and its image, `GET /api/v1/auth/address-probe.png`), the reference lists (`GET /api/v1/utilities/*`) and the AI
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
**scope**, and each scope but the restore has a token of its own, which opens that scope and nothing
else:

| Scope | For | Routes | Token |
| --- | --- | --- | --- |
| `backup` | Back up the whole instance and download the archive: [Backups for Your Hosting Panel](#panel-backups) | `POST /api/v1/backup/panel/jobs`, then `GET`, `GET …/file` and `DELETE` on `/api/v1/backup/panel/jobs/{job_id}` | `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN` |
| `wake` | Run the price and exchange rate updates that are due, for example right after your panel wakes the instance: [Scheduled Wake-up](sleep_wake.md#wake-sync) | `POST /api/v1/system/wake-sync` | `LIBREFOLIO_WAKE_TOKEN` |
| `status` | Follow the setup of the [initial administrator](#initial-admin), the instance's mode and its restore: [The Setup Status](#panel-status) | `GET /api/v1/panel/status` | `LIBREFOLIO_PANEL_STATUS_TOKEN` |
| `backup:restore` | Put a backup back on an instance that awaits it: [Restoring an Instance from Your Panel](#panel-restore) | The seven routes under `/api/v1/backup/panel/restore` | None: a [signed ticket](#panel-api-tickets) only |

Beside the tokens, a panel that runs many instances can sign a short-lived **ticket** for each call:
see [Signed Tickets](#panel-api-tickets). A scope accepts its token, its tickets, or both; the
`backup:restore` scope accepts tickets only, so it is off while the panel's public keys are not set.

The rules of this section hold for the four scopes alike. None of your panel's calls counts as a
visit for the [idle suspension](sleep_wake.md#idle-suspend-activity): each keeps the machine awake
only while it runs.

### 🗝️ A Token per Scope {: #panel-api-tokens }

- **No token and no keys, no scope.** A scope is off when its token is not set and the panel's
  [public keys](#panel-api-tickets) are not set either: its routes answer `404`, as a path that
  does not exist, and LibreFolio writes no line of its own about them. Set only what your panel
  uses.
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

A call proves itself with its scope's token, or with a [signed ticket](#panel-api-tickets), in one
header:

```text
Authorization: Bearer <the scope's token, or a signed ticket>
```

- **Only in that header**, never in the URL, where the access logs of servers and proxies would
  keep it: a token in the query string is not read, and the call gets a `401`.
- **Compared in constant time** with the scope's token, so that how long LibreFolio takes to answer
  tells nothing about the token. What is not the token is read as a ticket, when the panel's keys
  are set.
- **Over HTTPS only**: whoever reads a token on the way can use it.

### 🎫 Signed Tickets {: #panel-api-tickets }

A panel that runs many instances does not need a token per instance and scope. It signs a short
**ticket** for each call, with one Ed25519 private key that stays in its vault. Each instance holds
only the matching **public keys**: a leaked instance gives nothing that opens another.

Tokens and tickets work together, scope by scope. A scope with a token and the panel's keys accepts
either, so a panel can migrate step by step: set the keys, make the panel sign, then remove the
tokens. A self-hosted cron job keeps its token.

| Variable | What it holds | Default |
| --- | --- | --- |
| `LIBREFOLIO_PANEL_PUBLIC_KEYS` | `kid:key`, or `kid:key,kid:key…`: 1 to 4 entries, spaces around an entry ignored. `kid` is the label of a key, 1 to 64 characters among `A-Z a-z 0-9 . _ -`, each once. `key` is the raw 32-byte Ed25519 public key in base64url without padding, 43 characters. A public key is not a secret, so there is no `_FILE` twin | Unset or blank: tickets are off |
| `LIBREFOLIO_PANEL_CLOCK_SKEW_SECONDS` | How far a ticket's times may be off the instance's clock: a whole number from 0 to 300 | `60` |
| `LIBREFOLIO_PUBLIC_URL` | The instance's address, **required with the keys**: its origin is the audience of its tickets | — |

The **audience** is the origin of `LIBREFOLIO_PUBLIC_URL`, `scheme://host[:port]`: lower case, without
the default port (80 or 443), without a path and without a trailing slash. `https://Folio.Example.com:443/app/`
gives `https://folio.example.com`. Set them in the container's environment or in `.env`, then restart
LibreFolio, as for the tokens.

**One origin per instance.** A ticket names an origin, never a path: two instances served from the same
origin under different paths (`https://host/a` and `https://host/b`) would accept each other's tickets.
Give each instance an origin of its own, for example its own host name. With the keys set, a
`LIBREFOLIO_PUBLIC_URL` that holds a path is a warning of the [startup check](#panel-api-check).

**What a ticket is.** A compact JWS, which is a JWT, of at most 2048 bytes:

| Part | Field | Value |
| --- | --- | --- |
| Header | `alg` | exactly `EdDSA` |
| Header | `typ` | exactly `lf-panel+jwt` |
| Header | `kid` | one of the configured labels |
| Claims | `aud` | the instance's audience, above |
| Claims | `scope` | `backup`, `wake`, `status` or `backup:restore`: it must be the scope of the route |
| Claims | `iat`, `exp` | Unix seconds, whole numbers; `exp − iat` is positive and at most 300 |
| Claims | `jti` | a unique id of 16 to 64 characters among `A-Z a-z 0-9 _ -`, used once |

All the claims are required; any other claim is ignored. It travels in the header of a token,
`Authorization: Bearer <ticket>`, and in no other place.

- **One ticket per call.** Following a backup job means a new ticket for each `GET`, and a retry
  gets a new `jti`. A ticket is not bound to a method or a path, only to an instance and a scope.
- **Recommended signer**: `iat` is now, `exp` is `iat + 300`, and `jti` is 16 random bytes in
  base64url.
- **Times**, with the tolerance `skew`: a ticket is expired when `exp ≤ now − skew`, and not yet
  valid when `iat > now + skew`.

```bash
curl -H "Authorization: Bearer $TICKET" https://folio.example.com/api/v1/panel/status
```

#### 🚫 Why a Ticket Is Refused {: #panel-api-ticket-refusals }

A ticket that cannot be verified (more than 2048 bytes, not a JWS, another `alg` or `typ`, a bad
signature) gets the scope's usual `401` code, with no reason: only the holder of a genuinely signed
ticket learns why a ticket is refused. A signed ticket that is refused gets `401`, the header
`WWW-Authenticate: Bearer` and its own `code`, checked in this order:

| Order | `code` | When |
| --- | --- | --- |
| 1 | the scope's `…_unauthorized` | The ticket cannot be verified, as above |
| 2 | `panel_ticket_unknown_key` | The `kid` is not in the instance's keys. It shows at once a rotation half done |
| 3 | `panel_ticket_expired` | `exp ≤ now − skew`: sign a new ticket |
| 3 | `panel_ticket_not_yet_valid` | `iat > now + skew`: the instance's clock is behind, for example right after the machine resumed. The answer carries `Retry-After: 5`: retry with a **new** ticket |
| 4 | `panel_ticket_wrong_audience` | Another instance's ticket, or no `aud` |
| 5 | `panel_ticket_wrong_scope` | The ticket is for another scope than the route's |
| 6 | `panel_ticket_invalid` | Signed but badly built: a bad `jti`, a lifetime that is not positive or over 300 seconds, a required claim missing or of the wrong type. It is a bug of the signer |
| 7 | `panel_ticket_replayed` | The `jti` was used before |

Only the first two refusals count for [the limit](#panel-api-limit), since they prove nothing.

#### 📒 The Registry of Used Tickets {: #panel-api-registry }

LibreFolio remembers each accepted `jti` in a small SQLite file, `panel_tickets.sqlite3` in the data
directory (permissions 600, created at the first ticket). A ticket is checked and recorded in one
transaction, so several worker processes, and a restart, never accept it twice. Each record removes
the entries whose ticket expired more than 10 minutes ago (the widest tolerance plus the longest life
of a ticket), so a clock that steps back, or a tolerance raised later, never makes a ticket valid twice.

- Only a regular file is used: a symbolic link in its place is refused, never followed.

- The file is not part of a backup, and a restore leaves it alone.
- If LibreFolio cannot use it, the call gets `503` with the scope's `…_unavailable` code. A call with
  the scope's token, which is checked first, still works.

#### 🔄 Rotating the Key {: #panel-api-rotation }

1. Add the new key as a second entry: `LIBREFOLIO_PANEL_PUBLIC_KEYS=old:…,new:…`, then restart the
   instance, since the environment of a process changes only at its start.
2. Make the panel sign with the new `kid`. A ticket of the new key that reaches an instance
   before step 1 is refused with `panel_ticket_unknown_key`.
3. After 5 minutes, the longest life of a ticket, remove the old entry and restart.

!!! warning "Settings that cannot be used"

    A malformed key list, a tolerance out of range, or keys without a usable `LIBREFOLIO_PUBLIC_URL`
    make **every** route of the panel answer `503` with the scope's `…_unavailable` code, tokens
    included, until you fix them. This is on purpose: a panel that fails closed is never left half
    open by a typo. The [startup check](#panel-api-check) names the variable.

### 🧪 Test Vectors {: #panel-api-test-vectors }

To test a signer, here is a published key pair and a ticket made with it. The values are for tests
only: the private key is public, so **never use it for a real instance**.

- `private_key_seed_hex` is the 32-byte Ed25519 private key seed, in hexadecimal.
- `public_key` is the matching public key, in base64url without padding, and `environment` holds
  the settings of an instance that trusts it: `LIBREFOLIO_PANEL_PUBLIC_KEYS` with the label
  `test-vector-1`, `LIBREFOLIO_PUBLIC_URL` and the tolerance, 60 seconds.
- `header` and `payload` are what the ticket signs. `ticket` is the result: the base64url of the
  header, a dot, the base64url of the payload, a dot, and the base64url of the signature.
- `verdicts` lists what an instance with that environment answers to the ticket, one row per
  try, each against an empty registry. A row has `now` (the instance's clock, in Unix seconds),
  `scope` (the scope of the route that receives the ticket) and, when given, `public_url`, which
  replaces `LIBREFOLIO_PUBLIC_URL`. `accepted` is the only success; the others are the `code` of a
  `401`.

```json
{
  "warning": "Test values only: this key is published, never use it to sign for a real instance",
  "private_key_seed_hex": "934e14faf1000ba247789b80c5ee42e56e9bcea95704f27789dbf79feb1f0d87",
  "public_key": "ZaKIp6hE1dqXQkB19O2g4x_047q1cEYL_u_S5ToghwE",
  "environment": {
    "LIBREFOLIO_PANEL_PUBLIC_KEYS": "test-vector-1:ZaKIp6hE1dqXQkB19O2g4x_047q1cEYL_u_S5ToghwE",
    "LIBREFOLIO_PUBLIC_URL": "https://folio.example.com",
    "LIBREFOLIO_PANEL_CLOCK_SKEW_SECONDS": "60"
  },
  "header": {"alg": "EdDSA", "kid": "test-vector-1", "typ": "lf-panel+jwt"},
  "payload": {"aud": "https://folio.example.com", "scope": "status", "iat": 2000000000, "exp": 2000000300, "jti": "dGVzdC12ZWN0b3ItMDAx"},
  "ticket": "eyJhbGciOiJFZERTQSIsImtpZCI6InRlc3QtdmVjdG9yLTEiLCJ0eXAiOiJsZi1wYW5lbCtqd3QifQ.eyJhdWQiOiJodHRwczovL2ZvbGlvLmV4YW1wbGUuY29tIiwic2NvcGUiOiJzdGF0dXMiLCJpYXQiOjIwMDAwMDAwMDAsImV4cCI6MjAwMDAwMDMwMCwianRpIjoiZEdWemRDMTJaV04wYjNJdE1EQXgifQ.mZTtw7BdXHfJfrI2cSf_CPsZ6piPpTmXEWtb_ZoMVtrW4uKFH3JSqOiXQ6D7dbhro0PHbNNEOlPNkdGrPYOnCA",
  "verdicts": [
    {"now": 2000000000, "scope": "status", "verdict": "accepted"},
    {"now": 1999999940, "scope": "status", "verdict": "accepted"},
    {"now": 1999999939, "scope": "status", "verdict": "panel_ticket_not_yet_valid"},
    {"now": 2000000359, "scope": "status", "verdict": "accepted"},
    {"now": 2000000360, "scope": "status", "verdict": "panel_ticket_expired"},
    {"now": 2000000000, "scope": "backup", "verdict": "panel_ticket_wrong_scope"},
    {"now": 2000000000, "scope": "status", "public_url": "https://other.example.com", "verdict": "panel_ticket_wrong_audience"}
  ]
}
```

| `now` | `scope` | Verdict | Why |
| --- | --- | --- | --- |
| 2000000000 | `status` | `accepted` | The ticket's own `iat` |
| 1999999940 | `status` | `accepted` | `iat` is exactly `now + 60`: the tolerance allows it |
| 1999999939 | `status` | `panel_ticket_not_yet_valid` | One second more than the tolerance |
| 2000000359 | `status` | `accepted` | `exp` is 59 seconds behind |
| 2000000360 | `status` | `panel_ticket_expired` | `exp ≤ now − 60` |
| 2000000000 | `backup` | `panel_ticket_wrong_scope` | The ticket is for `status` |
| 2000000000 | `status`, `public_url` `https://other.example.com` | `panel_ticket_wrong_audience` | The ticket names `https://folio.example.com` |

- Presenting the same ticket a second time after it was accepted gives `panel_ticket_replayed`.
- A signer must produce a ticket the instance accepts, but its bytes need not equal the vector's:
  Ed25519 signatures are deterministic, so the same header and payload bytes always give the same
  signature, and a signer whose JSON bytes differ (key order, spaces) gets another one.

### 🚫 Refused Calls {: #panel-api-refusals }

| Answer | When | `code` |
| --- | --- | --- |
| `404` | The scope is off: neither its token nor the panel's public keys are set (for `backup:restore`, the keys are not set). The body is `{"detail": "Not Found"}`, as for a path that does not exist | — |
| `401` | No credential, or one that is not the scope's token and not a ticket LibreFolio can verify, another scope's token included (any token, for `backup:restore`). The answer carries `WWW-Authenticate: Bearer` | `backup_panel_unauthorized`, `wake_unauthorized`, `panel_status_unauthorized` or `backup_restore_unauthorized`, by scope |
| `401` | A ticket signed by your panel, but refused: see [Why a Ticket Is Refused](#panel-api-ticket-refusals). The answer carries `WWW-Authenticate: Bearer` | `panel_ticket_…`, in every scope |
| `429` | Too many refused credentials from your panel's address: see [The Limit on Refused Credentials](#panel-api-limit). The answer carries `Retry-After`, the seconds to wait | `panel_too_many_attempts`, in every scope |
| `503` | The scope's token is set but cannot be used: shorter than 32 characters, a character that is not visible ASCII, or a `_FILE` that cannot give it. Or the [ticket settings](#panel-api-tickets) cannot be used, or the registry of used tickets. Each call logs an error that names the variable, never the token | `backup_panel_unavailable`, `wake_unavailable`, `panel_status_unavailable` or `backup_restore_unavailable`, by scope |

A scope that is off, or whose token or ticket settings cannot be used, answers before anything else:
the credential of the call is not read, and nothing is counted. The `code` comes in the `detail` of the answer, with a
`message` in English:

```json
{"detail": {"code": "panel_too_many_attempts", "message": "Too many refused panel credentials from this address"}}
```

### 🚦 The Limit on Refused Credentials {: #panel-api-limit }

LibreFolio counts the credentials it refuses, per address:

- **20 refused credentials in 10 minutes**, and every call from that address gets `429`, to every
  scope, until fewer than 20 of its refusals are less than 10 minutes old: `Retry-After` gives the
  seconds to wait. LibreFolio does not read the credential of a call it answers `429`, so the right
  token waits too.
- **A refusal counts when it proves nothing**: no credential, a wrong token, another scope's token,
  a ticket that cannot be verified, or a ticket signed with a key the instance does not hold. The
  four scopes share one count: a panel that keeps sending a wrong backup token also waits for its
  wake-up and its status calls.
- **A ticket with a valid signature is never counted**, whatever is wrong with it (expired, not
  yet valid, another instance, already used…): only the panel can sign one, so a panel whose clock
  is behind never locks itself out.
- **Nothing else counts**: not a call with the right token or an accepted ticket, not a `429`, not
  the `404` of a scope that is off, nor the `503` of a setting that cannot be used.
- **One address, one count**: an IPv6 address counts by its `/64`. Behind a reverse proxy that
  LibreFolio does not trust, every caller has the proxy's address: LibreFolio then counts nothing,
  rather than let one caller's refusals make every caller wait. See «When LibreFolio Does Not Trust
  Your Proxy» in [Checking Connection Security](connection_checks.md#reverse-proxy).
- **In memory**: each server process keeps its own count, and a restart forgets it.

### 📋 In the Log {: #panel-api-log }

Every call to a scope that is on writes one line, `Hosting panel request`:

| Level | `outcome` | When | With |
| --- | --- | --- | --- |
| ℹ️ `info` | `accepted` | The right token or an accepted ticket: the route then answers as usual | For a ticket: `kid` and `jti` |
| ⚠️ `warning` | `refused` | The `401` | `reason`: `missing`, no credential in the header; `mismatch`, a token that is not the scope's and not a ticket that can be verified. For a signed ticket, the `panel_ticket_…` code, with its `kid` |
| ⚠️ `warning` | `limited` | The `429` | `retry_after`, the seconds of `Retry-After` |
| ⚠️ `warning` | `unavailable` | The `503` | `reason`: `unusable`, or `registry` when the registry of used tickets cannot be used. Just before it, an error line names the variable and what is wrong |

- Every line also carries `scope` (`backup`, `wake`, `status` or `backup:restore`), `method`, `path` (without the
  query string), `credential`, the kind of credential the call presented (`token` or `ticket`), and
  the `request_id` of the request.
- It never carries the token, the ticket, the value sent, a header, the query string or your panel's
  address:
  uvicorn's access line, which the web server writes for every request, has the address.
- The error line before an `unavailable` one is the scope's own:
  `The hosting panel's backup token cannot be used: its routes refuse every request`
  ([The Token](#panel-token)),
  `The wake-up token cannot be used: the scheduled wake-up refuses every request`
  ([Turning It On](sleep_wake.md#wake-sync-token)), or
  `The panel status token cannot be used: the status route refuses every request`.
  For the ticket settings it is
  `The hosting panel's ticket settings cannot be used: its routes refuse every request`, with the
  variable and its code.
- A call to a scope that is off writes no such line.

### 🩺 The Startup Check {: #panel-api-check }

At every start, LibreFolio checks the tokens of the three scopes that have one and the ticket settings, in two
checks, and logs an error for each one that fails. The **Security** tab of Settings › Administration shows the same checks
(«Security» in [Global Settings](settings.md)).

| `check` | Tokens | Passed | An error |
| --- | --- | --- | --- |
| `platform.hosting_panel` | `LIBREFOLIO_WAKE_TOKEN`, `LIBREFOLIO_PANEL_STATUS_TOKEN` and, for the [tickets](#panel-api-tickets), `LIBREFOLIO_PANEL_PUBLIC_KEYS`, `LIBREFOLIO_PANEL_CLOCK_SKEW_SECONDS` and `LIBREFOLIO_PUBLIC_URL` | None is set: the scopes are off. Or each one that is set can be used | A token cannot be used: its route answers `503` to every call until you fix it. The line names the variables and why, never a token: `A hosting panel token cannot be used, and its route answers 503 to every call: LIBREFOLIO_PANEL_STATUS_TOKEN (PANEL_STATUS_TOKEN_TOO_SHORT)`. Or the ticket settings cannot be used: **every** route of the panel answers `503`, the backup's included |
| `backup.panel_token` | `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN` | Not set: the backup scope is off. Or it can be used | It cannot be used: see [The Token](#panel-token) |

- The reasons of `platform.hosting_panel` are `…_TOO_SHORT`, fewer than 32 characters;
  `…_NOT_VISIBLE_ASCII`, a space, a tab or another character outside visible ASCII; and
  `FILE_UNREADABLE`, a `_FILE` that cannot give the token.
- The reasons for the ticket settings are `PANEL_KEYS_INVALID`, `PANEL_CLOCK_SKEW_INVALID` and
  `PANEL_AUDIENCE_UNAVAILABLE`, a missing or unusable `LIBREFOLIO_PUBLIC_URL`. The line never
  carries a key.
- With usable keys, a `LIBREFOLIO_PUBLIC_URL` that holds a path, such as `https://host/app`, is a
  `warning` in every profile: serve [one instance per origin](#panel-api-tickets).
- In the [managed profile](#managed-profile), a token still set beside usable keys, the backup's
  included, is a warning: `A hosting panel token is set beside the panel's public keys: remove it
  once the panel signs tickets`.
- A check that passes writes nothing in the log.

### 📊 The Setup Status {: #panel-status }

`GET /api/v1/panel/status` tells your panel where the setup of the
[initial administrator](#initial-admin) stands: whether your customer has used the setup link, and
until when the link works. It also gives the instance's `mode` and its `restore`
([Restoring an Instance from Your Panel](#panel-restore)). Turn it on with a token of its own in
`LIBREFOLIO_PANEL_STATUS_TOKEN`, as in [A Token per Scope](#panel-api-tokens), then:

```bash
curl -sS -H "Authorization: Bearer $LIBREFOLIO_PANEL_STATUS_TOKEN" \
  https://librefolio.example.com/api/v1/panel/status
```

```json
{"admin_setup": "pending", "setup_expires_at": "2026-10-23T09:12:44.512312Z", "mode": "normal", "restore": null}
```

| `admin_setup` | What it means | `setup_expires_at` |
| --- | --- | --- |
| `none` | No setup link was ever issued, as on an instance started without `LIBREFOLIO_ADMIN_EMAIL`; or the account it was for has been deleted since | `null` |
| `pending` | The latest setup link is still valid: not used, not withdrawn and not expired | When the link stops working |
| `done` | The setup is complete: your customer chose the password through the link, or the account was set up another way ([Once the Account Is Active](#initial-admin-active)) | `null` |
| `expired` | The latest link is more than 72 hours old, or was withdrawn: cancelled, or the administrator's address changed. A new link makes it `pending` again: [A New Link](#initial-admin-new-link) | `null` |

| Key | What it holds |
| --- | --- |
| `mode` | `normal`, or `awaiting_restore` while [`LIBREFOLIO_AWAIT_RESTORE`](#await-restore) is on |
| `restore` | `null` when no restore was ever recorded on this instance; otherwise `state` (`pending`, `in_progress`, `committed`, `rolled_back`, or `unreadable` when the state of the restore cannot be read), `reason` (why a restore was rolled back: `first_start_failed`, `swap_interrupted`, `swap_failed` or `stage_missing`; for `unreadable`, why the state cannot be read: `io`, `not_a_file` or `invalid`), `waiting` (why a confirmed restore still waits: `backup_running`, `other_data_directory`, `server_running` or `instance_blocked`), `backup_created_at` and `stage_id`. Each is `null` when it does not apply. It never says who confirmed the restore |

- The answer holds these four keys and nothing else: no username, no email address, no count of
  accounts. Ignore the keys you do not know: a later version may add some.
- `setup_expires_at` is an ISO 8601 date and time in UTC, given only while the state is `pending`.
- When the state of the restore cannot be read, the answer is still `200`, never `restore: null`:
  a restore may be waiting behind it. `restore` then reads
  `{"state": "unreadable", "reason": "io", "waiting": null, "backup_created_at": null, "stage_id": null}`,
  with `reason` `io` (its owner, its permissions or a disk error), `not_a_file` (a link or a folder in
  its place) or `invalid` (content no LibreFolio wrote): see
  [When the State of a Restore Cannot Be Read](#restore-interrupted).
- It answers on a [blocked instance](#instance-block) too, as on any other. A `pending` link there
  still waits for the unblock: the setup is refused until then, and its 72 hours keep running.
- Without `LIBREFOLIO_PANEL_STATUS_TOKEN` and without the panel's keys it answers `404`. Its other
  refusals are those of every scope ([Refused Calls](#panel-api-refusals)), with the codes
  `panel_status_unauthorized` and `panel_status_unavailable`. A [signed ticket](#panel-api-tickets)
  of scope `status` opens it too.

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
| `404` | `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN` is not set, and neither are the panel's [public keys](#panel-api-tickets): every route answers as a path that does not exist | — |
| `401` | No token, or not the token of this instance. A refused ticket has its own `panel_ticket_…` code: [Why a Ticket Is Refused](#panel-api-ticket-refusals) | `backup_panel_unauthorized` |
| `429` | Too many refused credentials from your panel's address: see [The Limit on Refused Credentials](#panel-api-limit) | `panel_too_many_attempts` |
| `503` | The token is set but cannot be used: shorter than 32 characters, a character that is not visible ASCII, or a `_FILE` that cannot give it. The start log names it already (`check` is `backup.panel_token`), and each call logs it | `backup_panel_unavailable` |
| `404` | A job your panel did not start, or one that does not exist, or no longer does | `backup_job_not_found` |
| `409` | A start while another backup runs. When it is a backup your panel started, the answer adds its `job_id` and `origin` (`panel`): follow that job instead of starting another | `backup_busy` |
| `409` | A download of a job that has no archive: still running, or failed | `backup_job_not_ready` |
| `409` | A delete while the job runs | `backup_job_running` |
| `409` | A start while the instance [awaits a restore](#await-restore): a backup of its empty data never starts | `backup_awaiting_restore` |
| `409` | A start while a [restore stopped half way](#restore-interrupted): a backup of data in doubt never starts. Your panel's credential is checked first: without a valid one the answer is the `401` or `404` above | `backup_restore_interrupted` |
| `507` | A start while the disk of the data directory, or a quota, is full: free some space, then start again | `backup_no_space` |
| `500` | The backup cannot start: the `backups/` folder of the data directory is a link or a file, or cannot be written for another reason. The log has the cause | `backup_folder_unusable`, `backup_failed` |

The `code` comes in the `detail` of the answer, with a `message` in English:

```json
{"detail": {"code": "backup_panel_unauthorized", "message": "A valid panel token is required"}}
```

---

## ♻️ Restoring an Instance from Your Panel {: #panel-restore }

When the server of an instance is gone, your hosting panel can put the instance's backup back on a
new machine. The new machine starts in the **awaiting restore** mode: nobody can sign in, register or
set up an administrator there, until your panel has restored the data and ended the mode.

The restore takes the instance's [secure backup](backup_restore.md#secure), the `.lfbk` file, still
encrypted, with its password. Its routes are the `backup:restore` scope of the
[Hosting Panel API](#panel-api): they accept a [signed ticket](#panel-api-tickets) of that scope and
nothing else, never a token. Without `LIBREFOLIO_PANEL_PUBLIC_KEYS` they answer `404`.

### ⏳ The Awaiting Restore Mode {: #await-restore }

| Variable | Values | What it does |
| --- | --- | --- |
| `LIBREFOLIO_AWAIT_RESTORE` | The values of `LIBREFOLIO_BLOCKED`: `1`, `true`, `yes` or `on` turn it on; `0`, `false`, `no` or `off` do not, in any case. Not set or empty: off | The instance waits for your panel to restore its data |

Set it on the new machine, before its first start on the empty data directory:

```bash
LIBREFOLIO_AWAIT_RESTORE=true
```

- Leave it unset on every other instance. A change applies when the server restarts, as for the
  block.
- Any other value stops the server at startup, and the error names the variable:
  `LIBREFOLIO_AWAIT_RESTORE must be one of 1/0, true/false, yes/no, on/off, or unset`.
- While it is on, every start logs a warning,
  `Instance awaiting its restore by the hosting panel (LIBREFOLIO_AWAIT_RESTORE): only the panel's routes and the probes answer`.
- The start skips what would make the machine a new instance: no
  [initial administrator](#initial-admin) and no setup link, even with `LIBREFOLIO_ADMIN_EMAIL` (the
  backup brings its own accounts), no [market data scheduler](settings.md#market-data-scheduler),
  and none of the background warm-ups. The log has one `Startup step skipped` line for each, naming
  the step: `admin-bootstrap`, `stored-currencies`, `provider-prewarm`, `market-holidays`,
  `brim-parse-pool` and `scheduler`. The database, the steps of the restore and the idle monitor
  still run.

While the mode is on, only these API calls answer:

| For | Endpoints |
| --- | --- |
| Probes and version | `GET /api/v1/system/health`, `GET /api/v1/system/ready`, `GET /api/v1/system/info`. `/system/ready` adds `"mode": "awaiting_restore"`, and `ready` then means ready to receive the backup |
| The public configuration of the instance, with `"mode": "awaiting_restore"` | `GET /api/v1/system/instance` |
| The [scheduled wake-up](sleep_wake.md#wake-sync), with its own token: it answers `awaiting_restore` and runs no job | `POST /api/v1/system/wake-sync` |
| Your panel's [status](#panel-status), with `mode` and `restore` | `GET /api/v1/panel/status` |
| Your panel's [backup jobs](#panel-jobs): a start answers `409` with the code `backup_awaiting_restore`, since a backup of the empty data never starts | The four `/api/v1/backup/panel/jobs…` routes |
| Your panel's restore | The [seven routes](#panel-restore-routes) below |

Every other call answers `423 Locked`, to anyone, signed in or not, registration, the sign-in and the
setup of an administrator included:

```json
{"detail": {"code": "instance_awaiting_restore", "message": "This instance is waiting for its hosting provider to restore its data"}}
```

Users who open the instance get a full page instead of every page of the app, the sign-in page
included: **Restoring your data**, on the sign-in page's background. It asks the instance every 30
seconds whether the mode has ended, and reloads itself when it has; **Try again** reloads it at once.

### 🔄 Upload, Check, Confirm, Restart {: #panel-restore-routes }

Each call carries a new ticket of scope `backup:restore`, in `Authorization: Bearer <ticket>`. The
paths are under `/api/v1/backup/panel/restore`:

| Step | Route | Answer |
| --- | --- | --- |
| Upload the `.lfbk` file, as the raw body | `PUT …/upload` | `201`, with its `upload_id` |
| Check it on a copy, with its password | `POST …/stage`, body `{"upload_id": "…", "password": "…"}` | `202`, and the check with its `stage_id` |
| Follow the check | `GET …/stage/{stage_id}` | The check: its `status` is `running`, with `phase` and `done_bytes` of `total_bytes`, then `done`, with the report, or `failed`, with an `error_code` |
| Confirm the restore | `POST …/stage/{stage_id}/confirm` | `202`, and the restore's status, `pending` |
| Restart the server, to apply it | `POST …/restart` | `202`, and the status. The server stops once the answer is sent; your restart policy starts it again, and that start applies the restore |
| Follow the restore | `GET …/status` | Its status: `none`, `pending`, `in_progress`, `committed` or `rolled_back` |
| Drop a confirmed restore before the restart | `DELETE …/pending` | `204`, its checked copy removed |

- **Only the `.lfbk` file.** A zip or the sealed `.tar` that holds it is refused with `400` and the
  code `restore_envelope_required`, and removed: on its first bytes, or once the whole file is
  received and is no `.lfbk` after all. The [upload limit](#restore-upload-limit) and the
  limit on what an archive unpacks to apply, as for an administrator's restore.
- **A new upload replaces the previous one only once it is accepted**: received to its end, then
  found to be an `.lfbk` file. A refused upload, empty, incomplete, too large or not an `.lfbk`,
  leaves the previous one in place, for its check. An upload that a running check reads is never
  removed.
- **The report holds no personal or portfolio data.** It gives the backup's date, version, origin
  and revision, the version this instance runs, whether the restore keeps the version (`same`) or
  upgrades it (`upgrade`) and with which migrations, whether the instance key is included, the
  warnings and blockers (`no_administrator`), the control totals as a verdict (`same`, `changed`,
  `absent`, `other_version` or `unreadable`) with the number of differences, `administrators_count`,
  `restorable` and `expires_at`. Never a username, an amount, a table or a size.
- **Your panel sees only the checks it started.** A check started by an administrator or from the
  command line answers `404` with the code `restore_stage_not_found`, as an unknown id.
- **The status names who confirmed only as `confirmed_via`**: `admin`, `cli` or `panel`. A
  confirmation by your panel is `panel`, and the instance records your ticket's `kid` as who
  confirmed it.
- **Repeating a call never makes two restores.** Starting the check again with the same
  `upload_id` while its check runs answers `202` with that same check; confirming the same check
  again answers `202` with the same status; a restart while the restore is already under way, or committed, answers
  `202` with its state and stops nothing.
- **The password is never echoed**, in an answer or in a validation error.
- **What the next start does** is the restore of an administrator: see
  [What the Next Start Does](backup_restore.md#next-start).

### 🏁 Ending the Mode {: #await-restore-end }

The instance never leaves the mode by itself. When the status reads `committed`, your panel removes
`LIBREFOLIO_AWAIT_RESTORE` from the machine and restarts it: from then on it is the instance again,
with its accounts. A restore that ends `rolled_back` stays in the mode, with its `reason`.

!!! warning "Restoring a blocked instance: change the variables in one update"

    To restore an instance that was [blocked](#instance-block), start the new machine with
    `LIBREFOLIO_AWAIT_RESTORE` on and `LIBREFOLIO_BLOCKED` off: with the block on, the restore
    routes answer `423 instance_blocked`. Every user route still answers `423` while the mode is on,
    so the instance is never usable in the meantime.

    Once the status reads `committed`, change the variables in **one** update of the machine,
    followed by one restart: `LIBREFOLIO_AWAIT_RESTORE` off, `LIBREFOLIO_BLOCKED` on, and
    `LIBREFOLIO_DELETION_DATE` unchanged. The first request after that restart already gets the
    block. Two updates, the mode removed first and the block set again later, leave the instance
    running unblocked between the two restarts.

### 🚫 When a Restore Call Is Refused {: #panel-restore-refusals }

Each route checks, in this order: the ticket, then the block, then the mode. A call without a valid
ticket learns neither whether the instance is blocked nor whether it awaits a restore.

| Answer | When | `code` |
| --- | --- | --- |
| `404` | `LIBREFOLIO_PANEL_PUBLIC_KEYS` is not set: the routes answer as a path that does not exist | — |
| `401` | No credential, any token, or a ticket that cannot be verified. A refused signed ticket has its own `panel_ticket_…` code: [Why a Ticket Is Refused](#panel-api-ticket-refusals) | `backup_restore_unauthorized` |
| `429` | Too many refused credentials from your panel's address: [The Limit on Refused Credentials](#panel-api-limit) | `panel_too_many_attempts` |
| `503` | The ticket settings, or the registry of used tickets, cannot be used; or the limit on what an archive unpacks to cannot be read | `backup_restore_unavailable` |
| `423` | The instance is blocked: no restore | `instance_blocked` |
| `409` | `LIBREFOLIO_AWAIT_RESTORE` is off: a restore never writes over an instance that runs | `restore_mode_required` |
| `400` | The upload is empty, incomplete, or not an `.lfbk` file; the check has no password, a wrong one, or a damaged file (the upload stays, for another try) | `backup_upload_empty`, `backup_upload_incomplete`, `restore_envelope_required`, `password_required`, `wrong_password`, `envelope_damaged` |
| `413` | The file is larger than the [upload limit](#restore-upload-limit) | `backup_too_large` |
| `404` | No upload or no check has this id; or no restore is confirmed, for `DELETE …/pending` | `backup_upload_not_found`, `restore_stage_not_found`, `restore_not_pending` |
| `409` | Another file is being checked, a secure backup this version cannot read, a check still running or that refused the file, LibreFolio updated since the check, another restore already confirmed, or a restart with no restore confirmed | `restore_busy`, `envelope_unsupported`, `restore_stage_running`, `restore_not_restorable`, `restore_stage_outdated`, `restore_already_pending`, `restore_not_pending` |
| `410` | The check expired: check the file again | `restore_stage_expired` |
| `507` | Not enough free space in the data directory | `backup_no_space`, `no_space` |
| `500` | The data directory's restore folder cannot be used, the state of the restore cannot be read (the answer's `detail` then adds `reason`: `io`, `not_a_file` or `invalid`), or a step could not be done; the log has the cause | `restore_folder_unusable`, `restore_state_unreadable`, `backup_upload_failed`, `stage_failed`, `restore_confirm_failed`, `restore_restart_failed`, `restore_cancel_failed` |

### 🧩 When the State of a Restore Cannot Be Read {: #restore-interrupted }

Every restore, yours or an administrator's, keeps its state in the data directory, in
`.restore/restore.json`. That file can become unreadable: its owner or permissions changed, a disk
error, a link or a folder in its place, or content no LibreFolio wrote. A restore may then have
stopped half way, and LibreFolio cannot tell which data it holds. This can happen on any instance,
managed or not.

Every start checks it, right after applying a restore that waits for it. When it cannot read it,
the instance serves **no data** until its administrator chooses what to do, and the start logs one
error, with the reason (`io`, `not_a_file` or `invalid`), never the file's content:

```text
The state of the restore cannot be read: LibreFolio serves no data until the administrator runs ./dev.py backup pending --recover
```

- **The start skips** what repairs, writes or warms up the data. The log has one
  `Startup step skipped` line for each, naming the step: `post-migration-fixes`,
  `lone-transfer-legs`, `admin-bootstrap`, `stored-currencies`, `provider-prewarm`,
  `market-holidays`, `brim-parse-pool` and `scheduler`. The database, the steps of the restore and
  the idle monitor still run.
- **The same API calls answer as in the [awaiting restore mode](#await-restore)**: the probes and
  the version, `GET /api/v1/system/instance`, the
  [scheduled wake-up](sleep_wake.md#wake-sync) and your panel's routes (its status, its backup jobs
  and its restore), but a backup start. Every other call answers `423 Locked`, to anyone, signed in
  or not, the sign-in included:

    ```json
    {"detail": {"code": "instance_restore_interrupted", "message": "A restore of this instance stopped half way: it serves no data until its administrator recovers it"}}
    ```

- `GET /api/v1/system/instance` says `"restore_interrupted": true`.
- The scheduled wake-up answers the status `restore_interrupted` and runs no job.
- Your panel's [status](#panel-status) answers `200` with `restore.state` `unreadable` and its
  `reason`, as it does whenever the state of the restore cannot be read.
- Your panel's [backup jobs](#panel-jobs): a start answers `409` with the code
  `backup_restore_interrupted`, once your panel's credential is checked (without a valid one, the
  same `401` or `404` as always): a backup of data in doubt would take the place of a good one among
  those you keep. Following a job, downloading its archive and deleting it still answer.
- Users who open the instance get a full page instead of every page of the app, the sign-in page
  included: **The restore stopped half way**, on the sign-in page's background. It asks them to
  contact their administrator, links the steps to recover, asks the instance every 30 seconds
  whether it serves the data again, and reloads itself when it does; **Try again** reloads it at
  once. When `LIBREFOLIO_SUPPORT_URL` holds an address the page can use, a `mailto:` address or an
  `http://` or `https://` page (the page checks it again), it adds a **Contact support** link to it.
  Not set or not usable: no link, and no fallback to the project's GitHub.

**The way out is on the machine**, for whoever runs it: stop LibreFolio, run
`./dev.py backup pending` to see what happened, then `./dev.py backup pending --recover`, which puts
the data of before back, and start LibreFolio again: see
«An Unreadable Restore State» in [Command-Line Tools](cli_tools.md). The instance decides once,
at its start: a file made readable again while LibreFolio runs counts only at the next start.

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
- ⏳ For developers: **[Awaiting Restore](../developer/architecture/security.md#await-restore)** —
  The mode's guard and its list, the skipped startup steps and the panel's restore routes
- 🧩 For developers: **[A Restore Stopped Half Way](../developer/architecture/security.md#restore-interrupted)** —
  The probe of the restore's state at start, its guard on the API and the skipped startup steps
- 🔌 For developers: **[The Hosting Panel's Access](../developer/architecture/security.md#panel-access)** —
  The dependency of the panel's routes, its limit and its log line
- 🖼️ For developers: **[The Content-Security-Policy and Frame Protection](../developer/architecture/security.md#managed-headers)** —
  The headers of the managed profile, directive by directive
- 👑 For developers: **[The Initial Administrator](../developer/architecture/access_control.md#initial-admin)** —
  The startup step, the setup link and its route; the setup page is in
  **[Account Link Pages](../developer/frontend/components/features/auth.md#link-pages)**
- 📊 For developers: **[The Setup's Status](../developer/architecture/access_control.md#setup-status)** —
  How the four states of [The Setup Status](#panel-status) are read from the setup links
- ⚖️ For developers: **[Public Instance Configuration](../developer/architecture/settings.md#public-instance-configuration)** —
  `GET /api/v1/system/instance`, the profile and the `legal` part included
