# 🛡️ Configuration: Checks and Protections

This page covers what LibreFolio checks in its configuration when it starts, with what each finding
means and what to do, the protections it asks of the browser (the **Content-Security-Policy** and
frame protection), and how it stops.

The options these checks look at are explained in [Configuration](configuration.md), the guide's
first page, and the secrets they mention in
[Configuration: Secrets and Plugin Settings](configuration_secrets.md).

---

## 🩺 Startup Checks {: #startup-checks }

Right after its `Starting LibreFolio` line, the server checks its configuration. It changes nothing:
each finding is one line of the log, at its level, with the name of the check in `check`, such as
`platform.jwt_secret`.

The same checks, on demand, are in the **Security** tab of **Settings › Administration**, for
administrators: worded in the language of the app, errors and warnings counted by a number on the
tab, and read again with **Check again** once you have fixed the configuration and restarted (see
«Security» in [Global Settings](settings.md)).

| Level | The log says | What to do |
| --- | --- | --- |
| ℹ️ `info` | `JWT_SECRET is not set: every start makes a new session signing key, …` | Nothing, if signing everyone out at every restart is fine. Otherwise see [Keep users signed in](index.md#session-persistence). |
| ⚠️ `warning` | `The session signing key from JWT_SECRET is … characters long: use at least 32 random characters` (or `from JWT_SECRET_FILE (<path>)`) | Generate a longer key, as in [Keep users signed in](index.md#session-persistence), and put it where the line says. |
| ⚠️ `warning` | `Set both directly and through a *_FILE variable: …` | For each secret listed, keep only one of the two: the variable itself wins, the file is ignored. |
| ❌ `error` | `The instance key cannot be used: …`, ending with `cannot be reached (Permission denied)` or `cannot be read (…)` | The `secrets/` folder or `instance.key` belongs to another user, or its permissions keep LibreFolio out. Give both back to the user that runs LibreFolio (`chown`), then `chmod 700` on the folder and `chmod 600` on the file. Never replace the key with a new one. The server starts anyway. |
| ❌ `error` | `The instance key cannot be used: …`, ending with another reason, such as `is empty or blank` | `instance.key` is damaged: restore it from a backup, never replace it with a new key. The server starts anyway. |
| ⚠️ `warning` | `… is open to other users (…): the folder should be 0700 and the file 0600` | Restrict them: `chmod 700` on the `secrets/` folder, `chmod 600` on `instance.key`. |
| ⚠️ `warning` | `SESSION_COOKIE_SECURE=never: the session cookie is sent over plain HTTP too; prefer auto` | Go back to `auto` unless you really need `never`: see [HTTPS and reverse proxies](configuration.md). |
| ℹ️ `info` | `The log level is DEBUG: the log records operational detail; …` (or `TRACE`) | Go back to `INFO` once you are done troubleshooting. |
| ❌ `error` | `LIBREFOLIO_TEST_MODE is on outside a test lane: test-only providers are served, the data are kept in the test data directory <path> and .env is not read; unset it on a production instance` (`check` is `platform.test_mode`) | Test mode is for LibreFolio's own test runs (`./dev.py test`, `./dev.py server --test`), which turn it on and off by themselves: remove `LIBREFOLIO_TEST_MODE` from the server's environment, or set it to `0`, then restart: look where the server's environment comes from, such as a service unit. Until then the server works on the folder the line names instead of your [data directory](filesystem.md): what is entered meanwhile is saved there, not with your data. |
| ❌ `error` | `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB cannot be used: expected a whole number of megabytes, 0 for no limit; restore uploads answer 503 until it is fixed` (`check` is `backup.upload_limit`) | Write a whole number of megabytes, `0` for no limit, or remove the variable, then restart ([The Upload Limit of a Restore](backup_restore.md#restore-upload-limit)). Until then Settings › Administration › Backup cannot upload an archive to restore it; the command line still restores one. The server starts anyway. |
| ❌ `error` | `LIBREFOLIO_BACKUP_MAX_RESTORE_MB cannot be used: expected a whole number of megabytes, 0 for no limit; restore checks answer 503 until it is fixed` (`check` is `backup.restore_limit`) | Write a whole number of megabytes, `0` for no limit, in the variable the line names, or remove it, then restart ([The Upload Limit of a Restore](backup_restore.md#restore-upload-limit)). Until then every check of a restore is refused with `backup_restore_unavailable`, from Settings › Administration › Backup and from the command line, where `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` in front of `backup restore` lifts the limit for that command. The server starts anyway. |
| ❌ `error` | `LIBREFOLIO_BACKUP_RECIPIENTS: item 2 is not an age recipient: …; the hosting panel's backups answer 503 until it is fixed` (or `expected at most 2 recipients`, `repeats an earlier recipient`) (`check` is `backup.recipients`) | Write one or two `age1…` public keys, comma-separated, as `backup keygen` gives them, then restart ([Sealed Backups](backup_sealed.md#sealed)). The server starts anyway. |
| ⚠️ `warning` | `LIBREFOLIO_LOGIN_LIMIT=off: failed sign-ins are not limited; turn it back on unless this is a test instance` (`check` is `accounts.login_limit`) | Nothing, on an instance kept for tests. Otherwise remove the variable, or set it to `on`, then restart: see [Failed Sign-ins](configuration_accounts.md#login-limit). |
| ❌ `error` | `LIBREFOLIO_SMTP_… cannot be used (SMTP_…): email stays off until it is fixed` (`check` is `email.smtp`) | Email is off, nothing else is: fix the variable the line names, then restart. What each code means: [Configuration Problems](email_troubleshooting.md#configuration-problems). The server starts anyway. |
| ⚠️ `warning` | `LIBREFOLIO_SMTP_TLS=none with …: emails, their links and the SMTP password travel unencrypted; use starttls or tls` | Set `LIBREFOLIO_SMTP_TLS` to `starttls` or `tls`, or send through a relay on your own network: see [Security Notes](email_troubleshooting.md#security). |
| ℹ️ `info` | `LIBREFOLIO_PUBLIC_URL is not set: emails work, but none with a link (forgotten password, invitation, reset) can go out` (`check` is `email.links`) | Nothing, if no link has to go out by email. Otherwise set `LIBREFOLIO_PUBLIC_URL` to the address your users open LibreFolio at ([Accounts and Sign-ups](configuration_accounts.md#accounts)), then restart: see [Email](email.md). |
| ⚠️ `warning` | `LIBREFOLIO_PUBLIC_URL cannot start a link (it needs http:// or https:// and a host, with no user name, password, ? or #): no email with a link (forgotten password, invitation, reset) can go out` (`check` is `email.links`) | Write the address with `http://` or `https://` and a host name, without user name, password, `?` or `#`, such as `https://librefolio.example.com`, then restart: see [Email](email.md). |
| ❌ `error` | `Stored plugin secrets that the instance key cannot read: <N>. Enter them again in the plugin settings, or restore the instance key they were saved with` (`check` is `platform.plugin_secrets`; this one comes later in the start, once the database is ready) | The instance key changed after these instance-wide [plugin secrets](configuration_secrets.md#plugin-secrets) were saved: a lost `secrets/instance.key` that LibreFolio replaced with a new one, data restored without its `secrets/`, or another `LIBREFOLIO_INSTANCE_KEY`. If you still have the old key (your copy of `secrets/instance.key`, backed up with the data directory as [The Instance Key](configuration_secrets.md#instance-key) says, since a clear archive of **Back up the instance** leaves the key out, while a [secure](backup_restore.md#secure) one carries the key LibreFolio generated and its restore re-encrypts these secrets; or the old value of the variable), stop LibreFolio, put it in place of the new one and start again. Do it before anyone enters a secret again: a secret entered again is saved under the new key, and becomes unreadable once the old one is back. Only if the old key is lost, enter the secrets again in **Settings › Plugins**: from then on, the new key is the one to back up. If the log also says `The instance key cannot be used: …`, fix that first: see above. Personal secrets are not counted: each user sees theirs in their own tab. The server starts anyway. |

Some secrets you configured stop the start instead when they cannot be used: a `JWT_SECRET_FILE` or a
`LIBREFOLIO_INSTANCE_KEY_FILE` that cannot give its secret (see [Secrets in Files](configuration_secrets.md#secret-files)),
or an instance key of your own shorter than 32 characters. The error is in the server's console
output (`docker compose logs librefolio` with Docker): it names the variable, and the file when there
is one, never the secret. Fix it, then start
again.

So does a `LIBREFOLIO_LOGIN_LIMIT` other than `on` or `off`
([Failed Sign-ins](configuration_accounts.md#login-limit)).

---

## 🛡️ Browser Protections {: #browser-protections }

Every answer of LibreFolio carries headers that tell the browser how to protect its pages. Three
are always there, with nothing to set:

- `X-Content-Type-Options: nosniff`: the browser uses the type LibreFolio sends and never guesses
  another, so an uploaded file is never run as a script or shown as a page.
- `Referrer-Policy: strict-origin-when-cross-origin`: another site learns at most LibreFolio's
  address, such as `https://librefolio.example.com`, never the page a request came from.
- A `Content-Security-Policy` on every page, in every profile, with no switch to turn it off: see
  [The Content-Security-Policy](#csp).

Two more are switches, each set on its own, off on an install of your own:
[Frame Protection](#frame-protection) and
[The Report-Only Policy](#csp-report-only). LibreFolio reads both when it starts: restart it after a change. For
developers: [Response Headers](../developer/architecture/security.md#response-headers).

### 🛡️ The Content-Security-Policy {: #csp }

A Content-Security-Policy tells the browser what a page may run and where it may connect to.
LibreFolio **always enforces** one, in every profile: there is no setting to turn it off. It is kept
as narrow as it can be while LibreFolio works as it always did, and widened only where LibreFolio
truly needs it. It asks nothing of you in the usual case: it matters only when something between
LibreFolio and the browser adds a script to the page ([A Script You Did Not Send](#csp-blocked-script)).

| What | Policy | Why |
|---|---|---|
| Every page of LibreFolio: the web app, the documentation (`/mkdocs`) and, where they are on, the API's own pages at `/api/v1/docs` and `/api/v1/redoc` | `object-src 'none'; base-uri 'self'; form-action 'self'` | No plugin content (`<object>`, `<embed>`); no `<base>` element sending the page's links to another site; no form sending its data to another site. LibreFolio uses none of them. A PDF is not a page: it carries none of these |
| The pages of the web app | `script-src`: only LibreFolio's own scripts. Its inline scripts are allowed by their hash, which LibreFolio works out from the web app's files, so a script written into the page by anyone else does not run | A script that LibreFolio did not send is the way a page is hijacked |
| The pages of the web app | `worker-src 'self' blob:` | The workers of the PDF viewer |
| The API's own pages at `/api/v1/docs` and `/api/v1/redoc`, only where `LIBREFOLIO_API_DOCS` is on | `script-src 'self' https://cdn.jsdelivr.net`, `worker-src 'self' blob:`, `connect-src 'self'` | The two pages are LibreFolio's own, not FastAPI's: they load Swagger UI and ReDoc from `cdn.jsdelivr.net` at an exact version, and the browser refuses a file whose checksum (Subresource Integrity) is not the one LibreFolio expects. Their start scripts come from your instance, so the pages hold no inline script, and they use no Google Fonts. The worker is ReDoc's search. Where the pages are off, none of this exists |
| The scripts of the web app's build, the files under `/_app/` | `script-src 'self'`, the same `connect-src` as the pages, `worker-src 'self' blob:`, `object-src 'none'`, `base-uri 'self'` | A policy for the case where a browser runs one of these files as a **worker**: it may load LibreFolio's own scripts and nothing else, and connect only where the pages may. A browser ignores it on any script that is not a worker. Today the only worker started from a file is the one that processes prices; the PDF viewer's worker starts from a `blob:` and keeps the page's policy |
| The pages of the web app | `connect-src 'self'`, the origin of [`LIBREFOLIO_PUBLIC_URL`](configuration_accounts.md#accounts) when it is set, and `https://api.github.com` on a self-hosted install only | Where the page may send requests to. The public address is the one you tell LibreFolio users reach it at; GitHub is the check for a newer release, which your browser makes when an administrator signs in (the `managed` profile never makes it) |
| Every response, with [Frame Protection](#frame-protection) on | `frame-ancestors 'self'` | Only LibreFolio's own pages may show it in a frame |

**The PDF preview asks nothing of a third party.** The viewer's engine is LibreFolio's own copy, and `connect-src` stays on LibreFolio's own address. If that copy cannot be reached, the preview shows your browser's own PDF viewer instead. Chinese, Japanese and Korean text is the one thing the viewer fetches, and it fetches it from your instance, not from a third party: when a PDF needs such a font, the page asks LibreFolio (`/api/v1/files/pdf-fonts/…`, for signed-in users only). The first time, **the server** downloads the file from `cdn.jsdelivr.net` (a fixed address, at a fixed version), keeps it only if its checksum (sha256) matches the list shipped with LibreFolio, and stores it in `cache/pdf-fonts/` inside the [data directory](filesystem.md). It is safe to delete that folder: the fonts are downloaded again when a PDF needs them, and it is not part of a backup. An instance that cannot reach `cdn.jsdelivr.net` shows such a PDF without those characters; a file that does not match the list is thrown away, and the log has a warning naming it.

What the policy does **not** enforce: `default-src`, `style-src`, `img-src`, `font-src` and
`frame-src`. Images (the icons of assets and brokers are set by a link to any address), styles,
fonts and frames stay free; whether another page may show LibreFolio in a frame is decided by
`LIBREFOLIO_FRAME_PROTECTION` alone, since showing LibreFolio inside a dashboard is a legitimate use
of an install of your own.

Nothing changes for what LibreFolio does by itself. When you rebuild the web app from the sources
while LibreFolio runs, the hashes follow the new build: you do not need to restart it.

#### 🕵️ A Script You Did Not Send {: #csp-blocked-script }

A proxy, a CDN or a browser extension that **adds a script** to LibreFolio's pages is blocked, as
anything else that LibreFolio did not send. Typical cases:

- Cloudflare's **Rocket Loader**, its **Email Address Obfuscation** and the automatic setup of its
  **Web Analytics**, which rewrite the page or add a script to it as it passes;
- an Nginx `sub_filter` that writes a `<script>` into the pages;
- a browser extension that adds a script of its own to every page.

What you see:

- the page works, but may lose the piece that script provided: a counter, an obfuscated address, a
  widget of the extension;
- the browser's console shows, once per page load, `LibreFolio blocked a script it did not send
  (<source>): a proxy, a CDN or a browser extension adds it. Guide:
  https://<your address>/mkdocs/admin/configuration_security/#csp`, where `<source>` is the address the script
  came from, or `inline` for a script written into the page;
- in the [Security](settings.md) tab of **Settings › Administration**, the browser
  that met it lists a warning, *a script was blocked*, naming the sources. The warning belongs to that
  browser tab, and goes when the tab closes.

Nothing is sent to your server: no report, no request. The console and the tab are the only
places the browser says it.

What to do: **turn the addition off for LibreFolio's address**. The policy is not widened by a
setting, because a script added on the way is exactly what it is there to stop.

- **Cloudflare**: for LibreFolio's host name, turn off Rocket Loader (*Speed › Optimization*), Email
  Address Obfuscation (*Scrape Shield*) and the automatic setup of Web Analytics (*Analytics & Logs ›
  Web Analytics*). A *Configuration Rule* can do it for that host alone and leave your other sites as
  they are. The names of the menus change from time to time.
- **Nginx**: remove the `sub_filter` that adds the script from the `server` or the `location` that
  proxies LibreFolio.
- **A browser extension**: turn it off for LibreFolio's address, or try the page in a private window,
  which usually runs without extensions.

Then reload the page: the line is gone from the console. The warning in the Security tab stays until
you close that browser tab.

#### 🔗 A Public Address That Cannot Be Used {: #csp-public-url }

`LIBREFOLIO_PUBLIC_URL` adds its origin (`scheme://host`, with the port only when it is not the
default one) to `connect-src`. A value that cannot be used, such as one without `http://` or
`https://`, or with a user name or a password, adds nothing: the server starts and serves as usual,
and the log has a warning, *LIBREFOLIO_PUBLIC_URL cannot be used*. Fix the value, then restart: see
[Accounts and Sign-ups](configuration_accounts.md#accounts).

#### 📡 The Address Check of a Share Link {: #csp-address-check }

The check of the **Server address** in the invitation and password-reset dialogs of the
[Users](users.md#server-address) tab does not ask the address for data any more: the policy would stop the
page from doing it. It loads a tiny, transparent image from the address you typed,
`/api/v1/auth/address-probe.png`, which the policy allows, and reads its size: one size says that
**this** instance answers there, another that something else does. What the messages say is the
same as before.

### 🖼️ Frame Protection {: #frame-protection }

`LIBREFOLIO_FRAME_PROTECTION` decides whether a page at another address may show LibreFolio in a
frame. Another address is another host name, or the same one on another port: a Home Assistant
dashboard at `http://homeassistant.local:8123` that shows LibreFolio from
`http://homeassistant.local:6040` is a page at another address.

- **Off** (`false`), the default on an install of your own: any page may show LibreFolio in a frame.
- **On** (`true`): only LibreFolio's own pages may show it in
  a frame. Anywhere else, the browser refuses to display it.

With the switch on:

- every answer carries `X-Frame-Options: SAMEORIGIN` and
  `Content-Security-Policy: frame-ancestors 'self'`, the same rule in the older header and in the
  newer one;
- the same `Content-Security-Policy` field also carries the three rules that
  [LibreFolio enforces on its pages](#csp) in every profile: `object-src 'none'`,
  `base-uri 'self'` and `form-action 'self'`. They do not depend on this switch. A PDF keeps
  `frame-ancestors 'self'` alone, so that the browser can still show it;
- a `304 Not Modified` answer gets only `X-Frame-Options`, so that the browser keeps the policy of
  the copy it already has.

When to change it:

- **On an install of your own**, leave it off if a page of yours shows LibreFolio in a frame, such
  as a Home Assistant dashboard: with the switch on, the browser would refuse to show LibreFolio
  there. If nothing of yours does, you can turn it on, so that no other site can show LibreFolio
  inside its own pages.

It is the `platform.frame_protection` check of the [startup checks](#startup-checks), also in the
[Security](settings.md) tab of **Settings › Administration**:

- The check passes, and the log says nothing about it. The tab lists it among the
  [passed checks](settings.md): *Only LibreFolio's own pages can show it in a
  frame.* with the switch on, *Pages at another address, such as your dashboards, can show
  LibreFolio in a frame: the default of an install of your own.* with the switch off on an install
  of your own.

### 📋 The Report-Only Policy {: #csp-report-only }

The [Content-Security-Policy](#csp) LibreFolio enforces is narrow on purpose: it leaves images,
styles, fonts and frames free. `LIBREFOLIO_CSP_REPORT_ONLY` adds a second, **wider** policy to the
pages of the web app: the whole policy LibreFolio aims at, which also says where a page may load
its images, styles, fonts and frames from. It is report-only: the browser checks it and blocks
nothing. It lists what falls outside it in its developer console, and nowhere else, since the policy
names no address to send a report to. The enforced policy is on whatever this switch says.

- **Off** (`false`), the default on an install of your own.
- **On** (`true`).

With the switch on:

- the pages of the web app carry a `Content-Security-Policy-Report-Only` header. The documentation
  (`/mkdocs`), everything under `/api/`, the API's documentation pages included, and the files the
  pages load do not, nor does a `304 Not Modified` answer;
- the policy allows what comes from LibreFolio's own address, and a few exceptions the app needs,
  such as images from any `https://` address (the icons of assets and brokers are set by a link),
  inline styles and the WebAssembly of the PDF viewer. For developers, the whole policy, directive
  by directive:
  [The Content-Security-Policy and Frame Protection](../developer/architecture/security.md#managed-headers);
- the web app's own inline scripts are allowed by their hashes, the same as in the enforced policy,
  which follow the web app's files: after you rebuild the web app from the sources, you do not need
  to restart LibreFolio;
- each line this policy adds to the console says what it would have blocked: nothing was. A script
  that the enforced policy blocks is a different thing, and has its own line: see
  [A Script You Did Not Send](#csp-blocked-script).

When to change it:

- **On an install of your own**, there is no need to turn it on: your users see no difference
  either way. Turn it on if you want to see, in the browser's developer console, what such a policy
  would block on your instance.

It is the `platform.csp_report_only` check of the [startup checks](#startup-checks), also in the
[Security](settings.md) tab of **Settings › Administration**:

- The check passes, and the log says nothing about it. The tab lists it among the
  [passed checks](settings.md): a line saying that the pages of the web app carry a
  report-only policy, with the switch on, *No report-only Content-Security-Policy: the default of
  an install of your own.* with the switch off on an install of your own.

---

## ⏹️ Stopping the Server {: #shutdown }

When the server is asked to stop, it must be done within a time limit, the **shutdown budget**:
8 seconds unless you change it, counted from the signal (SIGTERM from `docker stop`,
`docker compose down` or a restart; SIGINT from Ctrl+C). Most of the time users notice nothing,
except restarts that are quicker and cleaner.

| Variable | Default | What it does |
| --- | --- | --- |
| `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS` | `8` | The shutdown budget, in seconds: a whole number from `2` to `600`, or `0` for no limit, as before release 1.3. A value that cannot be used does not stop the server, unlike the [main options](configuration.md): the log says `Shutdown budget setting cannot be used: the default applies`, and the budget stays at 8 seconds. |
| `UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN` | 3/8 of the budget | How many seconds uvicorn, the web server, waits for the requests in flight: `3` with the default budget. The Docker image and `./dev.py server` work it out from the budget. A value you set yourself wins: keep it below the budget, which still counts for the whole stop. |

The budget is spent in this order:

1. **Requests in flight**: the web server accepts no new ones and gives those already running 3/8 of
   the budget, 3 seconds by default. Then it cancels those still running, such as a long broker
   import: what they had not saved yet is rolled back, so they can simply be repeated once
   LibreFolio is back.
2. **The server's own work**: the scheduled syncs, the worker processes, the caches… stop one after
   the other, each within the time left. The last step ends the child processes still running
   (broker imports, risk simulations, Tools), so none outlives the server.
3. **When the budget runs out**: if anything still holds the server, it ends anyway, with exit
   status 1, and its log says what was still running: `Shutdown budget exhausted: ending the process`.

!!! warning "🐳 Give the container more time than the budget"

    Docker gives a container 10 seconds to stop by default, then kills it: the default budget of
    8 seconds fits. If you raise `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS`, give the container at least
    2 seconds more: set `stop_grace_period` on the `librefolio` service of `docker-compose.yml`, keep
    the rest of the service as it is, then run `docker compose up -d`.

    ```yaml
    services:
      librefolio:
        stop_grace_period: 32s  # for LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS=30
    ```

    Otherwise Docker kills the server after 10 seconds, whatever its budget.

`./dev.py server` keeps that margin by itself: after a Ctrl+C it waits up to the budget plus 2 seconds
for this stop, then ends the server ([Start the Server](cli_tools.md#start-the-server)).

---

## 🔗 Related

- 📄 **[Configuration](configuration.md)** — Create the `.env` File, Main Options, Parameters Set by the Tools, …
- 📄 **[Configuration: Secrets and Plugin Settings](configuration_secrets.md)** — Secrets, Plugin Settings
- 📄 **[Configuration: Accounts and Asset Search](configuration_accounts.md)** — Accounts and Sign-ups, The Order of the Price Providers in the Search, Optional: Web Search for New Assets
