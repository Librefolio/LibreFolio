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

!!! info "📚 This guide is in several pages"

    Besides this page: [Hosting for Others: Your Instances](hosting_instances.md), [Hosting for Others: the Panel API](hosting_panel_api.md), [Hosting for Others: Backups and Restores](hosting_panel_backups.md).

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
| The largest archive uploaded for a restore, while `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` is not set | No limit | 500 MB: see [The Upload Limit of a Restore](hosting_panel_backups.md#restore-upload-limit) |
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
  [The Initial Administrator](hosting_instances.md#initial-admin). On a managed instance that administrator is protected: nobody can delete, deactivate or demote it, or reset its password or sign it out as another administrator, and it cannot delete itself or change its email address from the app (`409 ACCOUNT_PROTECTED`, a *Protected* badge in the Users tab; its address is changed from the host, with a confirmation link: [Changing the Administrator's Address](hosting_instances.md#owner-email-change)), while `./dev.py user …` on the server still can, except deleting, which that command does not do: the emergency exit.
- A `JWT_SECRET` of at least 32 random characters, so that sessions survive restarts. To keep it out
  of `.env`, use `JWT_SECRET_FILE`: see «Secrets» in [Environment Variables](configuration.md).
- Its own instance key: never share one key between instances. See «The Instance Key» in
  [Environment Variables](configuration.md).
- HTTPS in front of it: see [Expose Securely](service_exposure.md) and
  [HTTPS and reverse proxies](configuration.md#session-cookie-secure).
- On Fly.io, `LIBREFOLIO_CLIENT_IP_HEADER=Fly-Client-IP`, so that the limits per visitor's address
  count each visitor apart, not everyone as Fly's proxy. The managed profile does not set it, since
  the header depends on the proxy in front of the instance: see «The Visitor's Address» in
  [Checking Connection Security](connection_proxy.md#reverse-proxy).
- A monitor on `GET /api/v1/system/ready`: see the monitoring tip in
  [Advanced Docker](docker_advanced.md).
- If your hosting panel takes its backups: its own `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN`, never shared
  with another instance. See [Backups for Your Hosting Panel](hosting_panel_backups.md#panel-backups).
- Optionally, a wake-up token of its own, `LIBREFOLIO_WAKE_TOKEN`, if your panel brings the
  instance's prices and exchange rates up to date on its own schedule, for example right after it
  wakes the instance: see [Scheduled Wake-up](wake_sync.md#wake-sync).
- Optionally, a status token of its own, `LIBREFOLIO_PANEL_STATUS_TOKEN`, if your panel follows the
  setup of the instance's administrator: see [The Setup Status](hosting_panel_api.md#panel-status).
- If your hosting panel shows the app inside a frame: `LIBREFOLIO_FRAME_PROTECTION=false`, since the
  managed profile turns frame protection on.
- Your own support page or email address, `LIBREFOLIO_SUPPORT_URL` (`https://…` or `mailto:…`):
  where the users of the instance ask for help, such as an asset the search does not find. Without
  it, the asset search offers no **Let us know** link: the public GitHub issue a self-hosted
  instance falls back to would publish the instance's profile, its provider codes and your
  customer's asset identifiers. It is also the **Contact support** link of the page shown while
  [a restore has stopped half way](hosting_panel_backups.md#restore-interrupted). Other help links in the app may still
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

- 📄 **[Hosting for Others: Your Instances](hosting_instances.md)** — The Initial Administrator, Blocking an Instance
- 📄 **[Hosting for Others: the Panel API](hosting_panel_api.md)** — Hosting Panel API
- 📄 **[Hosting for Others: Backups and Restores](hosting_panel_backups.md)** — Backups for Your Hosting Panel, Restoring an Instance from Your Panel, The Upload Limit of a Restore
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
  How the four states of [The Setup Status](hosting_panel_api.md#panel-status) are read from the setup links
- ⚖️ For developers: **[Public Instance Configuration](../developer/architecture/settings.md#public-instance-configuration)** —
  `GET /api/v1/system/instance`, the profile and the `legal` part included
