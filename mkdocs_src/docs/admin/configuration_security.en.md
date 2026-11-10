# 🛡️ Configuration: Checks and Protections

This page covers:

- the **startup checks**: what each finding means, where to fix it and with what value;
- the **browser protections**: the Content-Security-Policy and frame protection;
- **stopping the server**.

The options these checks look at are explained in [Configuration](configuration.md); the secrets in
[Configuration: Secrets and Plugin Settings](configuration_secrets.md).

---

## 🩺 Startup Checks {: #startup-checks }

Right after the `Starting LibreFolio` line, the server checks its own configuration without changing anything.

**Where you read them:**

| Where | How |
| --- | --- |
| The server log | One line per finding, at the matching level, with the name of the check in `check` (e.g. `platform.jwt_secret`). |
| **Settings › Administration › Security** (administrators only) | The same checks, in the language of the app; a number on the tab counts errors and warnings. Once you have fixed and restarted, click **Check again** ([Security](settings.md#security-tab)). |

**Where you fix them:** unless the table says otherwise, in LibreFolio's **`.env` file**.
Then restart LibreFolio. With Docker Compose, run `docker compose up -d`.

| Level | The log says (`check`) | Where | What to do |
| --- | --- | --- | --- |
| ℹ️ `info` | `The session key is random: every restart signs everyone out. To stay signed in, set JWT_SECRET.` | `.env` | Nothing, if signing everyone out at every restart is fine. Otherwise set `JWT_SECRET`: [Keep users signed in](index.md#session-persistence). |
| ⚠️ `warning` | `The session signing key from JWT_SECRET is … characters long: use at least 32 random characters` (or `from JWT_SECRET_FILE (<path>)`) | `.env`, or the file the line names | Generate a key of at least 32 random characters, as in [Keep users signed in](index.md#session-persistence), and put it where the line says. |
| ⚠️ `warning` | `Set both directly and through a *_FILE variable: …` | `.env` | For each secret listed, keep only one of the two: the variable itself wins, the file is ignored. |
| ❌ `error` | `The instance key cannot be used: …`, ending with `cannot be reached (Permission denied)` or `cannot be read (…)` | Command line, on the server: the `secrets/` folder and `instance.key` | They belong to another user, or their permissions keep LibreFolio out. Give both back to the user that runs LibreFolio (`chown`), then `chmod 700` on the folder and `chmod 600` on the file. Never replace the key with a new one. The server starts anyway. |
| ❌ `error` | `The instance key cannot be used: …`, with another reason, such as `is empty or blank` | The `secrets/instance.key` file | It is damaged: restore it from a backup, never replace it with a new key. The server starts anyway. |
| ⚠️ `warning` | `… is open to other users (…): the folder should be 0700 and the file 0600` | Command line, on the server | `chmod 700` on the `secrets/` folder, `chmod 600` on `instance.key`. |
| ⚠️ `warning` | `SESSION_COOKIE_SECURE=never: the session cookie is sent over plain HTTP too; prefer auto` | `.env` | Go back to `auto`, unless you really need `never`: [`SESSION_COOKIE_SECURE`](configuration.md#session-cookie-secure). |
| ℹ️ `info` | `The log level is DEBUG: the log records operational detail; …` (or `TRACE`) | `.env` | Go back to `INFO` once you are done troubleshooting. |
| ❌ `error` | `LIBREFOLIO_TEST_MODE is on outside a test lane: test-only providers are served, the data are kept in the test data directory <path> and .env is not read; unset it on a production instance` (`platform.test_mode`) | The server's environment, not `.env`: look where it comes from, for example a service unit | Remove `LIBREFOLIO_TEST_MODE`, or set it to `0`, then restart. Test mode is for LibreFolio's own tests (`./dev.py test`, `./dev.py server --test`), which turn it on and off by themselves. Until then the server works on the folder the line names, not on your [data directory](filesystem.md): what you enter meanwhile is saved there. |
| ❌ `error` | `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB cannot be used: expected a whole number of megabytes, 0 for no limit; restore uploads answer 503 until it is fixed` (`backup.upload_limit`) | `.env` | A whole number of megabytes, `0` for no limit, or remove the variable ([The Upload Limit of a Restore](backup_restore.md#restore-upload-limit)). Until then Settings › Administration › Backup cannot upload an archive to restore; the command line still restores one. The server starts anyway. |
| ❌ `error` | `LIBREFOLIO_BACKUP_MAX_RESTORE_MB cannot be used: expected a whole number of megabytes, 0 for no limit; restore checks answer 503 until it is fixed` (`backup.restore_limit`) | `.env` | As above, in the variable the line names. Until then every check of a restore is refused with `backup_restore_unavailable`, from Settings › Administration › Backup and from the command line, where `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` in front of `backup restore` lifts the limit for that command. The server starts anyway. |
| ❌ `error` | `LIBREFOLIO_BACKUP_RECIPIENTS: item 2 is not an age recipient: …; the hosting panel's backups answer 503 until it is fixed` (or `expected at most 2 recipients`, `repeats an earlier recipient`) (`backup.recipients`) | `.env` | One or two `age1…` public keys, comma-separated, as `backup keygen` gives them ([Sealed Backups](backup_sealed.md#sealed)). The server starts anyway. |
| ⚠️ `warning` | `LIBREFOLIO_LOGIN_LIMIT=off: failed sign-ins are not limited; turn it back on unless this is a test instance` (`accounts.login_limit`) | `.env` | Nothing, on an instance kept for tests. Otherwise remove the variable, or set it to `on`: [Failed Sign-ins](configuration_accounts.md#login-limit). |
| ❌ `error` | `LIBREFOLIO_SMTP_… cannot be used (SMTP_…): email stays off until it is fixed` (`email.smtp`) | `.env`, the variable the line names | Only email is off, nothing else. What each code means: [Configuration Problems](email_troubleshooting.md#configuration-problems). The server starts anyway. |
| ⚠️ `warning` | `LIBREFOLIO_SMTP_TLS=none with …: emails, their links and the SMTP password travel unencrypted; use starttls or tls` | `.env` | `LIBREFOLIO_SMTP_TLS=starttls` or `tls`, or send through a relay on your own network: [Security Notes](email_troubleshooting.md#security). |
| ℹ️ `info` | `LIBREFOLIO_PUBLIC_URL is not set: emails work, but none with a link (forgotten password, invitation, reset) can go out` (`email.links`) | `.env` | Nothing, if no link has to go out by email. Otherwise set `LIBREFOLIO_PUBLIC_URL` to the address your users open LibreFolio at ([Accounts and Sign-ups](configuration_accounts.md#accounts), [Email](email.md)). |
| ⚠️ `warning` | `LIBREFOLIO_PUBLIC_URL cannot start a link (it needs http:// or https:// and a host, with no user name, password, ? or #): no email with a link (forgotten password, invitation, reset) can go out` (`email.links`) | `.env` | Write the address with `http://` or `https://` and a host name, without user name, password, `?` or `#`, such as `https://librefolio.example.com` ([Email](email.md)). |
| ❌ `error` | `Stored plugin secrets that the instance key cannot read: <N>. Enter them again in the plugin settings, or restore the instance key they were saved with` (`platform.plugin_secrets`; this one comes later, once the database is ready) | `secrets/instance.key` or `LIBREFOLIO_INSTANCE_KEY`; only as a last resort **Settings › Plugins** | The instance key changed after these [plugin secrets](configuration_secrets.md#plugin-secrets) were saved: procedure below. The server starts anyway. |

??? note "🔑 Unreadable plugin secrets: put the old key back"

    Causes: a lost `secrets/instance.key` that LibreFolio replaced with a new one, data restored without its
    `secrets/`, or another `LIBREFOLIO_INSTANCE_KEY`.

    If the log also says `The instance key cannot be used: …`, fix that first (table above).

    1. **Do you still have the old key?** Your copy of `secrets/instance.key`, backed up together with the data
       directory as [The Instance Key](configuration_secrets.md#instance-key) says, or the old value of the
       variable. A clear archive made with **Back up the instance** leaves the key out; a
       [secure](backup_restore.md#secure) one carries the key LibreFolio generated, and its restore re-encrypts
       these secrets.
    2. **Stop LibreFolio**, put the old key in place of the new one, start again.
       The secrets are readable again.

    !!! warning "⚠️ Before anyone enters a secret again"

        A secret entered again is saved under the new key, and becomes unreadable once the old one is back in
        use.

    Only if the old key is lost: enter the secrets again in **Settings › Plugins**. From then on, the key to
    back up is the new one.

    Personal secrets are not counted: each user sees theirs in their own tab.

**Errors that stop the start.** The server does not start, and the error is in the console output (with Docker,
`docker compose logs librefolio`): it names the variable and, when there is one, the file, never the secret. Fix it, then
start again.

| Cause | Where |
| --- | --- |
| A `JWT_SECRET_FILE` or a `LIBREFOLIO_INSTANCE_KEY_FILE` that cannot give its secret | The file the variable points to ([Secrets in Files](configuration_secrets.md#secret-files)) |
| An instance key of your own shorter than 32 characters | `.env`, `LIBREFOLIO_INSTANCE_KEY` |
| A `LIBREFOLIO_LOGIN_LIMIT` other than `on` or `off` | `.env` ([Failed Sign-ins](configuration_accounts.md#login-limit)) |

---

## 🛡️ Browser Protections {: #browser-protections }

Every answer of LibreFolio carries headers that tell the browser how to protect its pages.

| Header | To set? | What it does |
| --- | --- | --- |
| `X-Content-Type-Options: nosniff` | No, always there | The browser uses the type LibreFolio sends: an uploaded file is never run as a script or shown as a page. |
| `Referrer-Policy: strict-origin-when-cross-origin` | No, always there | Another site learns at most LibreFolio's address (`https://librefolio.example.com`), never the page a request came from. |
| `Content-Security-Policy` | No, on every page in every profile, with no switch | [The Content-Security-Policy](#csp). |
| `X-Frame-Options` + `frame-ancestors` | `LIBREFOLIO_FRAME_PROTECTION` in `.env`, off on an install of your own | [Frame Protection](#frame-protection). |
| `Content-Security-Policy-Report-Only` | `LIBREFOLIO_CSP_REPORT_ONLY` in `.env`, off on an install of your own | [The Report-Only Policy](#csp-report-only). |

The two switches are read at startup: after a change, restart LibreFolio. With Docker Compose, run
`docker compose up -d`. For developers: [Response Headers](../developer/architecture/security.md#response-headers).

### 🛡️ The Content-Security-Policy {: #csp }

It tells the browser what a page may run and what it may connect to. LibreFolio **always enforces** one, in every
profile, with no setting to turn it off. In the usual case it asks nothing of you: it matters only when something between
LibreFolio and the browser adds a script to the page ([A Script You Did Not Send](#csp-blocked-script)).

| What | Policy | Effect |
|---|---|---|
| Every page of LibreFolio: the web app, the documentation (`/mkdocs`) and, where they are on, the API's own pages at `/api/v1/docs` and `/api/v1/redoc` | `object-src 'none'; base-uri 'self'; form-action 'self'` | No plugin content (`<object>`, `<embed>`), no `<base>` and no form towards another site: LibreFolio uses none of them. A PDF is not a page: it carries none of these. |
| The pages of the web app | `script-src`: only LibreFolio's own scripts; its inline scripts are allowed by their hash, worked out from the web app's files | A script written into the page by anyone else does not run. |
| The pages of the web app | `worker-src 'self' blob:` | The workers of the PDF viewer. |
| The API's own pages at `/api/v1/docs` and `/api/v1/redoc`, only where `LIBREFOLIO_API_DOCS` is on | `script-src 'self' https://cdn.jsdelivr.net`, `worker-src 'self' blob:`, `connect-src 'self'` | LibreFolio's own pages, not FastAPI's: Swagger UI and ReDoc from `cdn.jsdelivr.net` at a fixed version, with a checksum the browser verifies (Subresource Integrity). Start scripts from your instance: no inline script, no Google Fonts. The worker is ReDoc's search. With the pages off, none of this exists. |
| The scripts of the web app's build, the files under `/_app/` | `script-src 'self'`, the same `connect-src` as the pages, `worker-src 'self' blob:`, `object-src 'none'`, `base-uri 'self'` | It applies only if a browser runs one of these files as a **worker**: it loads LibreFolio's scripts and nothing else, and connects only where the pages may. Today the only worker started from a file is the one that processes prices; the PDF viewer's worker starts from a `blob:` and keeps the page's policy. |
| The pages of the web app | `connect-src 'self'`, the origin of [`LIBREFOLIO_PUBLIC_URL`](configuration_accounts.md#accounts) when it is set, and `https://api.github.com` on a self-hosted install only | Where the page may send requests. GitHub is for the check for a new release, which your browser makes when an administrator signs in (never in the `managed` profile). |
| Every response, with [Frame Protection](#frame-protection) on | `frame-ancestors 'self'` | Only LibreFolio's own pages may show it in a frame. |

It does **not** enforce `default-src`, `style-src`, `img-src`, `font-src` and `frame-src`: images (the icons of assets and
brokers are a link to any address), styles, fonts and frames stay free. Whether another page may show LibreFolio in a
frame is decided by [`LIBREFOLIO_FRAME_PROTECTION`](#frame-protection) alone.

When you rebuild the web app from the sources while LibreFolio is running, the hashes follow the new build: you do not
need to restart it.

??? note "📄 The PDF preview asks nothing of a third party"

    The viewer's engine is LibreFolio's own copy, and `connect-src` stays limited to LibreFolio's own address. If that
    copy cannot be reached, the preview shows your browser's own PDF viewer.

    The one thing the viewer downloads is Chinese, Japanese and Korean text, and it asks your instance for it
    (`/api/v1/files/pdf-fonts/…`, for signed-in users only). The first time, **the server** downloads the font from
    `cdn.jsdelivr.net` (fixed address and version), keeps it only if its checksum (sha256) matches the list shipped
    with LibreFolio, and stores it in `cache/pdf-fonts/` inside the [data directory](filesystem.md).

    - You can delete that folder: the fonts are downloaded again when a PDF needs them. It is not part of a
      backup.
    - An instance that cannot reach `cdn.jsdelivr.net` shows that PDF without those characters.
    - A file that does not match the list is thrown away, and the log has a warning naming it.

#### 🕵️ A Script You Did Not Send {: #csp-blocked-script }

A proxy, a CDN or a browser extension that **adds a script** to LibreFolio's pages is blocked, as anything else
that LibreFolio did not send.

**What you see:**

- the page works, but may lose the piece that script provided: a counter, an obfuscated address, a widget of the
  extension;
- the browser's console shows, once per page load:

    ```text
    LibreFolio blocked a script it did not send (<source>): a proxy, a CDN or a browser extension adds it. Guide: https://<your address>/mkdocs/admin/configuration_security/#csp
    ```

    `<source>` is the address the script came from, or `inline` for a script written into the page;

- in **Settings › Administration › Security** ([Security](settings.md#security-tab)), the browser that met it shows
  the warning *a script was blocked*, with the sources. The warning belongs to that browser tab and goes when you
  close it.

Nothing is sent to your server: no report, no request. The console and the tab are the only places where the
browser says it.

**What to do:** turn the addition off for LibreFolio's address. No setting widens the policy.

| Who adds the script | Where to fix it | What to do |
| --- | --- | --- |
| **Cloudflare**: Rocket Loader, Email Address Obfuscation, the automatic setup of Web Analytics | The Cloudflare dashboard, for LibreFolio's host name | Turn off Rocket Loader (*Speed › Optimization*), Email Address Obfuscation (*Scrape Shield*) and the automatic setup of Web Analytics (*Analytics & Logs › Web Analytics*). A *Configuration Rule* does it for that host alone and leaves your other sites as they are. The names of the menus change from time to time. |
| **Nginx**: a `sub_filter` that writes a `<script>` into the pages | The Nginx configuration, in the `server` or the `location` that proxies LibreFolio | Remove that `sub_filter`. |
| **A browser extension** that adds a script of its own to every page | The browser | Turn it off for LibreFolio's address, or try the page in a private window, which usually runs without extensions. |

Then reload the page: the line is gone from the console. The warning in the Security tab stays until you close that
browser tab.

#### 🔗 A Public Address That Cannot Be Used {: #csp-public-url }

`LIBREFOLIO_PUBLIC_URL` adds its origin (`scheme://host`, with the port only when it is not the default one) to
`connect-src`. A value that cannot be used (without `http://` or `https://`, or with a user name or a password) adds
nothing: the server starts and serves as usual, and the log has the warning *LIBREFOLIO_PUBLIC_URL cannot be used*.

Fix the value in **`.env`** ([Accounts and Sign-ups](configuration_accounts.md#accounts)).
Restart LibreFolio. With Docker Compose, run `docker compose up -d`.

#### 📡 The Address Check of a Share Link {: #csp-address-check }

The **Server address** field in the invitation and password-reset dialogs of the
[Users](users.md#server-address) tab does not ask the address for data: the policy would stop it. It loads a tiny
transparent image from the address you typed, `/api/v1/auth/address-probe.png`, which the policy allows, and reads its
size: one size says that **this** instance answers there, another that something else does. The messages say the
same things as before.

### 🖼️ Frame Protection {: #frame-protection }

It decides whether a page at **another address** may show LibreFolio in a frame. Another address is another host
name, or the same one on another port: a Home Assistant dashboard at `http://homeassistant.local:8123` that shows
LibreFolio from `http://homeassistant.local:6040`.

| `LIBREFOLIO_FRAME_PROTECTION` | Effect |
| --- | --- |
| `false`, the default on an install of your own | Any page may show LibreFolio in a frame. |
| `true` | Only LibreFolio's own pages may show it in a frame; anywhere else, the browser refuses to display it. |

**When to turn it on:** on an install of your own, leave it off if a page of yours shows LibreFolio in a frame, such as a
Home Assistant dashboard: with the switch on, the browser would refuse to show it there. If none of your pages does,
turn it on: no other site will be able to show LibreFolio inside its own pages.

1. **In the `.env` file**, add:

    ```env
    LIBREFOLIO_FRAME_PROTECTION=true
    ```

2. Restart LibreFolio. With Docker Compose, run `docker compose up -d`.
   Every answer now carries `X-Frame-Options: SAMEORIGIN` and `Content-Security-Policy: frame-ancestors 'self'`, the
   same rule in the older header and in the newer one.

With the switch on:

- the same `Content-Security-Policy` also carries the three rules that [LibreFolio enforces on its pages](#csp) in
  every profile (`object-src 'none'`, `base-uri 'self'`, `form-action 'self'`): they do not depend on this switch.
  A PDF keeps `frame-ancestors 'self'` alone, so that the browser can still show it;
- a `304 Not Modified` answer gets only `X-Frame-Options`, so that the browser keeps the policy of the copy it
  already has.

It is the `platform.frame_protection` check of the [startup checks](#startup-checks). It always passes, and the log says
nothing about it; **Settings › Administration › Security** lists it among the
[passed checks](settings.md#security-passed):

| Switch | The tab says |
| --- | --- |
| On | *Only LibreFolio's own pages can show it in a frame.* |
| Off, on an install of your own | *Pages at another address, such as your dashboards, can show LibreFolio in a frame: the default of an install of your own.* |

### 📋 The Report-Only Policy {: #csp-report-only }

`LIBREFOLIO_CSP_REPORT_ONLY` adds to the pages of the web app a second policy, **wider** than the enforced
[Content-Security-Policy](#csp): it also says where a page may load images, styles, fonts and frames from.
It is report-only: the browser blocks nothing and lists what falls outside it in its developer console, and nowhere
else. The enforced policy stays on whatever the value.

| `LIBREFOLIO_CSP_REPORT_ONLY` | Effect |
| --- | --- |
| `false`, the default on an install of your own | No report-only policy. |
| `true` | The pages of the web app carry `Content-Security-Policy-Report-Only`. |

**When to turn it on:** on an install of your own there is no need: your users see no difference. Turn it on to
see, in the browser's developer console, what a policy of this kind would block on your instance.

1. **In the `.env` file**, add:

    ```env
    LIBREFOLIO_CSP_REPORT_ONLY=true
    ```

2. Restart LibreFolio. With Docker Compose, run `docker compose up -d`.
   The pages of the web app now carry the `Content-Security-Policy-Report-Only` header.

With the switch on:

- the documentation (`/mkdocs`), everything under `/api/` including the API's documentation pages, the files the
  pages load, and a `304 Not Modified` answer do not carry it;
- the policy allows what comes from LibreFolio's own address and a few exceptions the app needs:
  images from any `https://` address (the icons of assets and brokers are a link), inline styles and the WebAssembly
  of the PDF viewer. For developers, directive by directive:
  [The Content-Security-Policy and Frame Protection](../developer/architecture/security.md#managed-headers);
- the web app's inline scripts are allowed by their hashes, as in the enforced policy: after you rebuild the web app
  from the sources, you do not need to restart LibreFolio;
- each line this policy adds to the console says what it **would have** blocked: nothing was blocked. A script that
  the enforced policy blocks has a line of its own: [A Script You Did Not Send](#csp-blocked-script).

It is the `platform.csp_report_only` check of the [startup checks](#startup-checks). It always passes, and the log says
nothing about it; **Settings › Administration › Security** lists it among the
[passed checks](settings.md#security-passed):

| Switch | The tab says |
| --- | --- |
| On | A line saying that the pages of the web app carry a report-only policy. |
| Off, on an install of your own | *No report-only Content-Security-Policy: the default of an install of your own.* |

---

## ⏹️ Stopping the Server {: #shutdown }

When it is asked to stop, the server must do so within the **shutdown budget**: 8 seconds unless you change it,
counted from the signal (SIGTERM from `docker stop`, `docker compose down` or a restart; SIGINT from Ctrl+C).

**Where:** in the **`.env` file**.

| Variable | Default | What it does |
| --- | --- | --- |
| `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS` | `8` | The shutdown budget, in seconds: a whole number from `2` to `600`, or `0` for no limit, as before release 1.3. A value that cannot be used does not stop the server, unlike the [main options](configuration.md#main-options): the log says `Shutdown budget setting cannot be used: the default applies`, and the budget stays at 8 seconds. |
| `UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN` | 3/8 of the budget | How many seconds uvicorn, the web server, waits for the requests in flight: `3` with the default budget. The Docker image and `./dev.py server` work it out from the budget. A value of your own wins: keep it below the budget, which still counts for the whole stop. |

The budget is spent in this order:

1. **Requests in flight**: the web server accepts no new ones and gives those already running 3/8 of the budget, 3
   seconds by default. Then it cancels those still running, such as a long broker import: what they had not saved
   yet goes back to the previous state (rollback), and they are repeated once LibreFolio is back.
2. **The server's own work**: scheduled syncs, worker processes, caches… stop one after the other, each within the
   time left. The last step ends the child processes still running (broker imports, risk simulations, Tools): none
   outlives the server.
3. **Budget exhausted**: if anything still holds the server, it ends anyway with exit status 1, and the log says what
   was still running: `Shutdown budget exhausted: ending the process`.

!!! warning "🐳 Give the container more time than the budget"

    Docker gives a container 10 seconds to stop, then kills it: the default budget of 8 seconds fits.
    If you raise `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS`, give the container at least 2 seconds more, otherwise Docker kills
    the server after 10 seconds, whatever its budget.

    **In `docker-compose.yml`**, on the `librefolio` service, leave the rest as it is and add:

    ```yaml
    services:
      librefolio:
        stop_grace_period: 32s  # for LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS=30
    ```

    Then run `docker compose up -d`.

`./dev.py server` keeps that margin by itself: after a Ctrl+C it waits up to the budget plus 2 seconds, then ends the
server ([Start the Server](cli_tools.md#start-the-server)).

---

## 🔗 Related

- 📄 **[Configuration](configuration.md)** — Create the `.env` File, Main Options, Parameters Set by the Tools, …
- 📄 **[Configuration: Secrets and Plugin Settings](configuration_secrets.md)** — Secrets, Plugin Settings
- 📄 **[Configuration: Accounts and Asset Search](configuration_accounts.md)** — Accounts and Sign-ups, The Order of the Price Providers in the Search, Optional: Web Search for New Assets
- 📄 **[Global Settings](settings.md#security-tab)** — The Security Tab
