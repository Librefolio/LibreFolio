# 📝 Configuration

Startup options live in a `.env` file: ports, the data folder, logging, login sessions, sign-ups,
secrets and a few optional features. It sits at the root of the project, or next to
`docker-compose.yml` with Docker. The options you change from inside the app are
[Global Settings](settings.md) instead.

---

## 🔧 Create the `.env` File

In the project folder, copy the sample file, then edit the values you need:

```bash
cp .env.example .env
```

With the pre-built Docker image, the [Docker installation](../user/installation.md) guide downloads
the same sample as `.env`.

- The sample groups the options by what they do. A commented option, such as
  `# SESSION_COOKIE_SECURE=auto`, shows its default: remove the `#` only to change the value.
- LibreFolio reads `.env` when it starts: restart it after a change. With Docker Compose, run
  `docker compose up -d`, because `docker compose restart` keeps the old values.
- Names are case-sensitive. In the main options and the risk settings below, a value of the wrong
  type or out of range stops the server at startup with an error.

---

## ✏️ Main Options

| Variable | Default | What it does |
| --- | --- | --- |
| `PORT` | `6040` | Port of the web server. With Docker Compose, the port opened on the host (the container always listens on `6040`). |
| `TEST_PORT` | `6041` | Port of the test server (`./dev.py server --test`). |
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Folder of the database, uploads, broker reports and logs; a relative path starts from the project folder. Docker fixes it to `/app/backend/data/prod-docker`: to move the data on the host, change the left side of the `./LibreFolio-data` volume in `docker-compose.yml`. |
| `LOG_LEVEL` | `INFO` | How much the server logs: `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`. |
| `JWT_SECRET` | _not set_ | Key that signs login sessions. Not set, empty or only spaces: a new key at every start, so everyone logs in again after a restart. `JWT_SECRET_FILE` reads it from a file instead: see [Secrets](#secrets). See [Keep users signed in](index.md#session-persistence). |
| `SESSION_COOKIE_SECURE` | `auto` | When the login session cookie is sent over HTTPS only: `auto` (if the browser uses HTTPS), `always` or `never`. See [HTTPS and reverse proxies](#session-cookie-secure). |
| `LIBREFOLIO_CLIENT_IP_HEADER` | _not set_ | Behind a reverse proxy, the header in which it passes the visitor's address, such as `Fly-Client-IP` on Fly.io: set it only if every request crosses that proxy. See [The Visitor's Address](connection_checks.md#client-address). |
| `PREVIEW_CACHE_MAX_MB` | `50` | Memory, in MB, of the image-preview cache in each server process. |
| `LIBREFOLIO_PROFILE` | `selfhosted` | Leave it unset. `managed` is reserved for hosting providers that run LibreFolio for their customers: there, a `JWT_SECRET` shorter than 32 characters, or `LIBREFOLIO_TEST_MODE` on outside LibreFolio's own test runs, stops the server at startup, and some defaults change unless you set their variables: the archives uploaded for a restore are limited to 500 MB (`LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`), and what they unpack to while they are checked to 8 times that, 4000 MB (`LIBREFOLIO_BACKUP_MAX_RESTORE_MB`), idle risk workers stop after 60 seconds (the risk settings below), and `LIBREFOLIO_FRAME_PROTECTION` and `LIBREFOLIO_CSP_REPORT_ONLY` are on. The app changes for its users too: no **Buy Me a Coffee** link in the page header, the **Help & Support** menu, the sign-in pages or Settings › About, and no donation popup; no check for a newer release, neither at an administrator's sign-in nor with **Check for updates** in the changelog, since the hosting provider updates the instance; and **Forgot Password?** shows no server command, but tells users to ask their administrator for a password-reset link. Case and spaces around the value do not matter; any other value stops the server at startup. The profile is public: anyone who can reach the server can read it at `/api/v1/system/instance`. See [Hosting for Others](hosting_providers.md#managed-profile). |
| `LIBREFOLIO_FRAME_PROTECTION` | `false` (`true` in the `managed` profile) | Leave it unset on an install of your own: dashboards at another address, such as Home Assistant panels, can then show LibreFolio in a frame. `true` lets only LibreFolio's own pages show it in a frame: every response carries `X-Frame-Options: SAMEORIGIN` and `Content-Security-Policy: frame-ancestors 'self'` (a `304 Not Modified` answer only the first, so that the browser keeps the policy of the copy it already has), and the browser refuses to show the app in a page at another address. LibreFolio's pages (the web app, the documentation, and the API's own documentation pages at `/api/v1/docs` and `/api/v1/redoc`), and any SVG image or XML document it serves, such as the documentation's sitemap, also get `object-src 'none'; base-uri 'self'; form-action 'self'` in the same `Content-Security-Policy`, which block plugin content (`<object>`, `<embed>`), a `<base>` element sending the page's relative links to another site, and forms sending their data to another site: LibreFolio itself uses none of these, so nothing visible changes. `true` or `false`; `1`/`0`, `yes`/`no` and `on`/`off` work too, in any case; any other value stops the server at startup. A value you set wins over the profile. See [Hosting for Others](hosting_providers.md#managed-profile). |
| `LIBREFOLIO_CSP_REPORT_ONLY` | `false` (`true` in the `managed` profile) | Leave it unset on an install of your own. `true` adds a report-only Content-Security-Policy to the pages of the web app, not to the documentation or the API: it blocks nothing, and the browser lists in its developer console what the policy would block, without sending a report anywhere. Same values as `LIBREFOLIO_FRAME_PROTECTION`; a value you set wins over the profile. See [Hosting for Others](hosting_providers.md#managed-profile). |
| `LIBREFOLIO_SUPPORT_URL` | _not set_ | Where the users of the instance ask for help, such as an asset the search does not find ([Let us know](../user/assets/create-edit.md#let-us-know), under the search results): a page with `http://` or `https://`, or one email address as `mailto:help@example.org`. With an email address, the user's email app opens a message with the details of the search; with a page, the page opens in a new tab and the details are copied, to paste there. Not set: on an install of your own (the `selfhosted` profile), a new public issue on LibreFolio's GitHub opens with the details, for the user to review before sending it; in the `managed` profile the link does not appear at all, since that issue would publish the instance's profile, its provider codes and the asset's identifiers, so a hosting provider should set its own. Any other value is ignored, as if it were not set, and the server logs it once. A page whose address holds a user name or a password counts as not set too. The address is public: anyone who can reach the server can read it at `/api/v1/system/instance`. See [Hosting for Others](hosting_providers.md#managed-profile). |
| `LIBREFOLIO_TOS_URL` | _not set_ | The terms of service of the instance: a page with `http://` or `https://`. The legal notice that every user sees, in Settings › About, on the Welcome page, under the card of every sign-in page and at the foot of the sidebar, links it as **Terms of service**, opened in a new tab. Not set: no link, the notice alone. A hosting provider sets its own. Unlike `LIBREFOLIO_SUPPORT_URL`, no `mailto:`. A value LibreFolio cannot use, an address with a user name or a password included, does not stop the server: the link stays hidden, and the log has an error (see below). The address is public: anyone who can reach the server can read it at `/api/v1/system/instance`. See [Hosting for Others](hosting_providers.md#legal-pages). |
| `LIBREFOLIO_PRIVACY_URL` | _not set_ | The privacy policy of the instance, linked as **Privacy policy** next to the terms of service: the same rules as `LIBREFOLIO_TOS_URL`. |
| `LIBREFOLIO_BLOCKED` | _not set_ | Leave it unset. A hosting provider sets it to block the instance: users can still sign in and out, and see a block page instead of the app. `1`, `true`, `yes` or `on` block; `0`, `false`, `no` or `off` do not, in any case; any other value stops the server at startup. Read from the environment only, in every profile. See [Hosting for Others](hosting_providers.md#instance-block). |
| `LIBREFOLIO_DELETION_DATE` | _not set_ | Leave it unset. The day the hosting provider will delete a blocked instance and its data, as an ISO date such as `2026-11-14`, shown on the block page. Any other value stops the server at startup. Read from the environment only. See [Hosting for Others](hosting_providers.md#deletion-date). |
| `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN` | _not set_ | Leave it unset. A hosting provider sets it so that its hosting panel can back up the instance through `/api/v1/backup/panel/jobs`: at least 32 visible ASCII characters, without spaces, such as the output of `openssl rand -hex 32`. Not set: those routes answer `404`. A token LibreFolio cannot use does not stop the server: the routes answer `503`, and the log has an error, from the start already ([Startup Checks](#startup-checks)) and then at each call. `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN_FILE` reads it from a file instead: see [Secrets](#secrets). Read from the environment only. See [Hosting for Others](hosting_providers.md#panel-backups). |
| `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` | _not set_ | Leave it unset. The largest archive an administrator may upload to check it for a restore, in megabytes; `0` is no limit. Not set: no limit, or `500` in the `managed` profile. A hosting provider sets it, since there the administrator is its customer. A value that is not a whole number does not stop the server: the uploads answer `503`, and the log has an error, from the start already ([Startup Checks](#startup-checks)) and then each time the limit is read. Read from the environment only. See [Hosting for Others](hosting_providers.md#restore-upload-limit). |
| `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` | _not set_ | Leave it unset. The largest size an archive may unpack to while it is checked for a restore, in megabytes, from the sizes its manifest declares; `0` is no limit. Not set: no limit, or in the `managed` profile 8 times the upload limit, `4000` with its `500`, and no limit when the upload limit is `0`. Why 8: a database shrinks to about a quarter of its size in an archive, and uploaded files barely shrink, so an archive heavy with its database keeps twice the room it needs, while one crafted to fill the disk is refused. A value you set always wins, `0` included, and `backup restore` on the command line follows it too. An archive over the limit is refused before anything is unpacked (`unpacked_too_large`). A value that is not a whole number does not stop the server: the checks of a restore answer `503` (`backup_restore_unavailable`), the log has an error, from the start already ([Startup Checks](#startup-checks)) and then at each check, and the **Security** tab of Settings › Administration reports it (`backup.restore_limit`). Read from the environment only. See [Hosting for Others](hosting_providers.md#restore-upload-limit). |
| `LIBREFOLIO_WAKE_TOKEN` | _not set_ | Optional. The token of the [scheduled wake-up](sleep_wake.md#wake-sync), which a hosting panel or a cron job of yours calls to bring prices and exchange rates up to date without a user. Not set: the route answers `404`, as if it did not exist. At least 32 visible ASCII characters, without spaces, such as the output of `openssl rand -hex 32`: a token of its own, not another secret. `LIBREFOLIO_WAKE_TOKEN_FILE` reads it from a file instead: see [Secrets in Files](#secret-files). A token that cannot be used does not stop the server: the route answers `503`, and the log says why. |
| `LIBREFOLIO_IDLE_SUSPEND_MODE` | `none` | Optional, for Fly.io. `fly`: the machine asks Fly to suspend it after `LIBREFOLIO_IDLE_SUSPEND_MINUTES` without a user's request and with no work in progress, and Fly resumes it at the next request. `none` never suspends: on any other host, leave it unset. Case and spaces around the value do not matter. Any other value does not stop the server, unlike the main options: the log has an error at startup, and the machine is never suspended. See [Idle Suspension](sleep_wake.md#idle-suspend). |
| `LIBREFOLIO_IDLE_SUSPEND_MINUTES` | `5` | Read only with `LIBREFOLIO_IDLE_SUSPEND_MODE=fly`: the minutes without a user's request before the machine is suspended, a whole number from `1` to `1440`. A value that cannot be used does not stop the server either: the log has an error at startup, and 5 minutes apply. See [Idle Suspension](sleep_wake.md#idle-suspend). |
| `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS` | `60` | The first pause of a price provider that answers «too many requests» (HTTP 429): no request reaches it until the pause ends, and each refusal in a row doubles the next one. A whole number of seconds from `0` to `86400`; `0` turns the pauses off, as before release 1.3. On by default, by developer decision 34: an exception to the rule that a new option leaves an install as it was. A value that cannot be used does not stop the server either: the log has an error, and both defaults apply. See [Provider Pauses](sleep_wake.md#provider-pauses). |
| `LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS` | `3600` | The longest pause the doubling reaches: a whole number of seconds from `1` to `86400`, not below the first pause while the pauses are on. A provider's `Retry-After` may still ask for more, up to one day. A value that cannot be used does not stop the server either: the log has an error, and both defaults apply. See [Provider Pauses](sleep_wake.md#provider-pauses). |
| `LIBREFOLIO_PROBE_RATE_LIMIT` | `30` | How many times a minute one user may test a price provider's settings (**Test Configuration** in the asset form), which may call the provider. A whole number from `0` to `10000`; `0` turns the limit off, for a test instance only (`./dev.py server --test` does it), and the log has a warning at every start. Read at every test: a change applies without a restart. A value that cannot be used does not stop the server: the log has an error, and `30` applies. |
| `LIBREFOLIO_BRIM_PREWARM` | `false` (`true` in test mode) | Optional. `true` makes the broker-import workers ready at startup, with the import plugins loaded: the first broker import after a start is then about 4 seconds faster, for about 80 MB of memory held from the start and about 1.4 seconds of CPU at every start. Off by default, by decision N56: on a small cloud machine, that memory and CPU cost more than the seconds they save. `true` or `false`; `1`/`0`, `yes`/`no` and `on`/`off` work too, in any case. Any other value does not stop the server, unlike the main options: the log has a warning at startup, and it stays off. See [BRIM Architecture → Preload and warm-up](../developer/backend/brim/architecture.md#parse-pool-warm-up). |
| `LIBREFOLIO_SMTP_HOST` | _not set_: email off | Optional. The SMTP server that sends LibreFolio's emails, such as `smtp.example.com`. See [Email](email.md#variables). |
| `LIBREFOLIO_SMTP_TLS` | `starttls` | How the connection to the SMTP server is encrypted: `starttls`, `tls` or `none`. See [Encryption Modes](email.md#encryption-modes). |
| `LIBREFOLIO_SMTP_PORT` | `587` with `starttls`, `465` with `tls`, `25` with `none` | The port of the SMTP server, only when it is not the usual one of its encryption mode. See [Email](email.md#variables). |
| `LIBREFOLIO_SMTP_USER` | _not set_: no login | The login on the SMTP server, set together with `LIBREFOLIO_SMTP_PASSWORD` ([Secrets](#secrets)). See [Email](email.md#variables). |
| `LIBREFOLIO_SMTP_FROM` | _not set_ | The sender of the emails, required as soon as a server is set. See [Email](email.md#variables). |
| `LIBREFOLIO_SMTP_REPLY_TO` | _not set_: replies go to the sender | Where replies to LibreFolio's emails go. See [Email](email.md#variables). |
| `LIBREFOLIO_SMTP_MAX_PER_HOUR` | `50` | How many emails the instance may send in an hour, per server process. See [Email](email.md#variables). |

A value LibreFolio cannot use in `LIBREFOLIO_TOS_URL` or `LIBREFOLIO_PRIVACY_URL` never stops the
server: that link stays hidden, and the legal notice shows without it. The first time each server
process answers `/api/v1/system/instance`, which the app reads as soon as it opens, the log has an
error, `Invalid instance link`, with the variable and its value in `problem` (a value that holds an
`@` is not shown: it may carry a user name or a password), and in `consequence` what it costs until
you fix it, such as `the terms of service link stays hidden until it is fixed: the legal notice shows
without it`. Fix the value, then restart. A `LIBREFOLIO_SUPPORT_URL` that cannot be used logs the
same error, with its own `consequence`.

Older `.env` files may still contain `PORTFOLIO_BASE_CURRENCY`: LibreFolio ignores it, and new
users start from the **Default Currency** in [Global Settings](settings.md).

??? info "🔒 HTTPS and reverse proxies — the session cookie"

    `SESSION_COOKIE_SECURE` decides when the cookie that keeps users signed in is `Secure`: the
    browser then sends it over HTTPS only, so the session never travels on an unencrypted
    connection. Case and spaces around the value do not matter; any other value stops the server at
    startup with an error.
    {: #session-cookie-secure }

    - **`auto`** (default): `Secure` when the browser reached LibreFolio over HTTPS. LibreFolio
      itself serves plain HTTP, so HTTPS comes from a reverse proxy in front of it, which says so
      with the `X-Forwarded-Proto: https` header; only its first value counts. There is no list of
      trusted proxies to set up: the header can only turn `Secure` on, never off. Over plain HTTP,
      such as `http://localhost:6040`, a LAN IP or the Tailscale IP of Levels 1 and 2 in
      [Exposing Securely](service_exposure.md), the cookie is not `Secure`, so signing in keeps
      working.
    - **`always`**: always `Secure`, for an install reached over HTTPS only. Over plain HTTP the
      browser drops the cookie, so the sign-in does not stick: the next page sends the user back
      to the login page.
    - **`never`**: never `Secure`. It is the way out when a proxy sends `X-Forwarded-Proto: https`
      to a browser that actually uses plain HTTP, such as Nginx with a hard-coded
      `proxy_set_header X-Forwarded-Proto https;` in a plain-HTTP `server` block: in `auto`, that
      browser would be sent back to the login page after every sign-in. Fixing the proxy is better
      (`$scheme` instead of `https`); `never` is the fallback.

    Behind an HTTPS reverse proxy, `auto` relies on its `X-Forwarded-Proto` header:

    - **Tailscale Serve and Funnel** (Levels 3 and 4 in [Exposing Securely](service_exposure.md)),
      **Caddy** and **Traefik** send it on their own: nothing to configure.
    - **Nginx** does not: add `proxy_set_header X-Forwarded-Proto $scheme;` to the `location` that
      proxies LibreFolio.
    - **Any other proxy**: make it send the header or, if LibreFolio is reachable only through it,
      set `SESSION_COOKIE_SECURE=always`.

    To check in your browser whether the session cookie is marked `Secure`, see
    [Checking Connection Security](connection_checks.md#session-cookie).

??? info "🧮 Risk engine workers — advanced tuning"

    Risk simulations and portfolio optimizations run in separate worker processes, started on
    first use. The defaults suit most installs: add a variable to `.env` only to change it.

    | Variable | Default | What it does |
    | --- | --- | --- |
    | `RISK_SIMULATION_WORKERS`, `RISK_OPTIMIZATION_WORKERS` | `1` (1–8) | Worker processes per kind of job: more run more jobs at once. |
    | `RISK_SIMULATION_QUEUE_CAPACITY`, `RISK_OPTIMIZATION_QUEUE_CAPACITY` | `2` (0–64) | Jobs that can wait for a worker; beyond that, new requests are turned away. |
    | `RISK_SIMULATION_TIMEOUT_SECONDS`, `RISK_OPTIMIZATION_TIMEOUT_SECONDS` | `120` / `60` | Time limit of one job, in seconds. |
    | `RISK_SIMULATION_IDLE_TIMEOUT_SECONDS`, `RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS` | `600` (`60` in the `managed` profile) | Idle workers stop after this many seconds and restart with the next job; `0` keeps them running. |

---

## 🔐 Secrets {: #secrets }

These options are secrets: keep them as private as the database. Each one can be written in `.env` or
read from a file.

| Secret | From a file | What it is |
| --- | --- | --- |
| `JWT_SECRET` | `JWT_SECRET_FILE` | The key that signs login sessions, in the main options above. |
| `LIBREFOLIO_INSTANCE_KEY` | `LIBREFOLIO_INSTANCE_KEY_FILE` | The [instance key](#instance-key). Not set: LibreFolio creates one in the data directory. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` | The key of a paid search service, for the `apikey` engine of the web search below. Unlike the first two, a file that cannot give it does not stop the server: it only turns the web search off. |
| `LIBREFOLIO_SMTP_PASSWORD` | `LIBREFOLIO_SMTP_PASSWORD_FILE` | The password of the SMTP server that sends LibreFolio's emails: see [Email](email.md). Like the web-search key, a file that cannot give it does not stop the server: it only turns email off. |
| `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN` | `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN_FILE` | The token of the hosting panel that backs up the instance: see [Hosting for Others](hosting_providers.md#panel-backups). Like the web-search key, a file that cannot give it does not stop the server: the panel's backup routes answer `503`. |
| `LIBREFOLIO_WAKE_TOKEN` | `LIBREFOLIO_WAKE_TOKEN_FILE` | The token of the [scheduled wake-up](sleep_wake.md#wake-sync), in the main options above. A token that cannot be used, or a file that cannot give it, does not stop the server either: the scheduled wake-up answers `503` until it is fixed. |
| `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` | `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE` | The token of the setup link of the [initial administrator](#initial-admin), when a hosting panel delivers that link. A token that cannot be used stops the server at startup, and so does, as for the first two, a file that cannot give it. |

A plugin may have secrets of its own, such as the API key of a paid data source: see
[Plugin Settings](#plugin-settings).

### 📄 Secrets in Files {: #secret-files }

Add `_FILE` to the name of a secret and give the path of a file that holds it. This is how Docker and
Kubernetes hand over their secrets, such as `/run/secrets/jwt_secret`: the secret stays out of `.env`
and out of the container's environment.

- The secret is the text of the file, without the line breaks at its end and without the byte order
  mark that some Windows editors put at its start. Any other space counts, at the start and at the
  end too.
- A relative path starts from the project folder.
- A secret or its `_FILE` variable that is empty or holds only spaces counts as not set: a stray
  space is never used as a key.
- Set one of the two. When both are set, the variable itself wins, the file is ignored and the start
  log has a [warning](#startup-checks).
- For `JWT_SECRET_FILE`, `LIBREFOLIO_INSTANCE_KEY_FILE` and `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE`,
  a file that is missing, cannot be read, is empty or blank (only spaces and line breaks), is not
  UTF-8 text or is larger than 64 KiB stops the server at startup. The error names the variable and
  the path, never the secret.
- `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` is read only when a search uses the `apikey` engine. A
  file that cannot give the key does not stop the server: the search goes on without the web search,
  with a warning in the log (`web_link_finder: …; disabling`), and the providers' own search keeps
  working.
- `LIBREFOLIO_SMTP_PASSWORD_FILE` is read only when `LIBREFOLIO_SMTP_HOST` is set. Like the web-search
  key file, a file that cannot give the password does not stop the server: email stays off, with an
  error in the log (`Email configuration cannot be used: email stays off`).
- `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN_FILE` is read by the [startup checks](#startup-checks), then each
  time the hosting panel calls its backup routes. Like the web-search key file, a file that cannot give
  the token does not stop the server: the start log has an error
  (`The hosting panel's backup token cannot be read: LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN_FILE: <path> does not exist`,
  or another reason), and those routes answer `503`, with an error in the log at each call
  (`The hosting panel's backup token cannot be used: its routes refuse every request`).
- LibreFolio reads these variables from its environment: `./dev.py` and Docker Compose
  (`env_file: .env`) put the values of `.env` there, so `.env` works with both.

??? example "🐳 A Docker secret with Docker Compose"

    1. Save a new key in a file next to `docker-compose.yml`:

        ```bash
        python3 -c "import secrets; print(secrets.token_urlsafe(64))" > jwt_secret.txt
        ```

    2. Add the marked lines to `docker-compose.yml`, and keep the rest of the service as it is:

        ```yaml
        services:
          librefolio:
            environment:
              - LIBREFOLIO_DATA_DIR=/app/backend/data/prod-docker
              - HOST=0.0.0.0
              - JWT_SECRET_FILE=/run/secrets/jwt_secret  # added
            secrets:                                     # added
              - jwt_secret                               # added
        secrets:                                         # added
          jwt_secret:                                    # added
            file: ./jwt_secret.txt                       # added
        ```

    3. If `.env` gives `JWT_SECRET` a value, remove that line: it would win over the file. An empty
       `JWT_SECRET=` line does no harm. Then run `docker compose up -d`.

    Compose mounts the file in the container as it is on the host, with its owner and permissions.
    LibreFolio runs there as the user of the image, `1000:1000` for the official one (see
    [Advanced Docker](docker_advanced.md)), and that user must be able to read the file. With the
    official image, for example: `sudo chown 1000:1000 jwt_secret.txt`, then
    `sudo chmod 600 jwt_secret.txt`. Otherwise the server stops at startup and the error says that the
    file `cannot be read`.

    `LIBREFOLIO_INSTANCE_KEY_FILE`, `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE`,
    `LIBREFOLIO_SMTP_PASSWORD_FILE`, `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN_FILE` and
    `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE` are mounted the same way; what each does when its file
    cannot give the secret is in [Secrets in Files](#secret-files).

### 🗝️ The Instance Key {: #instance-key }

The instance key is one secret per installation: LibreFolio derives its encryption keys from it.
There is nothing to set up. LibreFolio uses the first key it finds:

1. `LIBREFOLIO_INSTANCE_KEY`, the key itself;
2. `LIBREFOLIO_INSTANCE_KEY_FILE`, a file that holds it, such as a Docker secret;
3. `secrets/instance.key` in the data directory, which LibreFolio creates the first time it needs the
   key: 43 random characters, in a folder and a file that only the user running LibreFolio can open
   (`0700` and `0600`).

A key of your own must be random and at least 32 characters long, such as the output of
`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`. Never use a passphrase: the keys
LibreFolio derives from it are only as strong as it is.

On a managed or cloud deployment, the key can come from the environment or a Docker secret instead of
the data directory. Give every instance its own key: never share one key between several instances.

!!! warning "🔑 Never change or delete the key once in use"

    Only the same key can read again what was encrypted with it.

    - Back up `secrets/` with the rest of the data directory, and keep the copies as private as the
      database: see [Backup](filesystem.md#backup).
    - Once the key exists, LibreFolio cannot tell a lost `instance.key` from a first use: it creates a
      new key, and what the old one encrypted can no longer be read. When you restore the data, put
      `secrets/` back with it before you start LibreFolio again. Never start LibreFolio on restored
      data without its `secrets/`. If LibreFolio has already created a new key, stop it, put your
      copy of `instance.key` in place of the new one and start it again, before anyone enters a
      [plugin secret](#plugin-secrets) again: a secret entered under the new key would become
      unreadable once the old key is back.
    - If `instance.key` is there but damaged or out of reach, LibreFolio logs an error and never
      replaces it: see what to do in [Startup Checks](#startup-checks).
    - Setting `LIBREFOLIO_INSTANCE_KEY` where `secrets/instance.key` already exists changes the key. To
      move the key to the environment or to a Docker secret, use the content of `secrets/instance.key`
      as the value.

---

## 🧩 Plugin Settings {: #plugin-settings }

A plugin can ask for settings of its own: the API key of a paid data source, a region, a
preference. Of the plugins shipped with LibreFolio, two ask for one, a personal search preference
each: justETF and Borsa Italiana. None asks for an instance-wide setting; a plugin you add may. A
setting is one of two kinds:

- **Instance-wide**: one value for the whole instance, which only an administrator can save. Every
  user can read a plain value, and of a secret one, such as an API key, only whether it is set.
- **Personal**: each user's own value, which only that user can save and read. Administrators never
  see it.

Personal and instance-wide settings are changed in **Settings › Plugins**, a tab every user has:
each user changes their personal ones there, and administrators the instance-wide ones too, which
the other users see read-only. In the asset dialog, **Configure**, next to the chosen price
provider, opens the same form for that provider alone. What the tab shows, setting by setting:
[Plugin Settings](../user/settings/plugins.md) in the user manual.

An instance-wide setting can also be given by an environment variable, in `.env` or in the
container's environment like the other options; a personal one cannot. The plugins that have
settings, with the keys of their settings, are listed by `GET /api/v1/settings/plugins` to any
signed-in user.

### 🏷️ The Variables {: #plugin-variables }

LibreFolio builds the name of the variable from the kind of plugin, the plugin's code and the
setting's key:

```text
LIBREFOLIO_PLUGIN_<KIND>_<PLUGIN CODE>_<SETTING KEY>
```

- `<KIND>` is `ASSET` for a price provider and `FX` for an exchange-rate provider.
- The whole name is in uppercase, and every character other than a letter or a digit becomes `_`:
  the `api_key` setting of the price provider `my_provider` is
  `LIBREFOLIO_PLUGIN_ASSET_MY_PROVIDER_API_KEY`.
- For a secret setting, a plugin may also accept the variable it read before it had settings, so
  that an existing install keeps working. When both are set, the name above wins.
- Each variable also has a `_FILE` form, the path of a file that holds the value, such as a Docker
  secret. The file is read as in [Secrets in Files](#secret-files), but one that cannot be read never
  stops the server: see below.

### 🔒 A Variable Locks the Setting {: #plugin-variable-lock }

While its variable is set, a setting takes its value from there, and nobody can change it from
inside LibreFolio: a save is refused (`LOCKED_BY_ENV`), and a value saved earlier is ignored until
you remove the variable and restart. **Settings › Plugins** shows the setting read-only, a secret
only as *Set*: *Set by the server variable* and the variable's name for administrators, *Set by the
server* for the other users.

- A wrong value, one the setting does not accept or a `_FILE` that cannot be read, still locks the
  setting, and the plugin is then not configured: LibreFolio refuses every request to it, even when
  the setting is optional, until you fix the variable. It never falls back to the saved value or to
  the plugin's default. The log says why, with a warning once per server process:
  `Plugin setting variable invalid: the plugin is not configured until it is fixed`, with the
  variable and the reason, never the value. In **Settings › Plugins** the plugin's badge reads
  **To configure**, and the setting says that its variable is invalid. Fix the value, then restart.
- In the [managed profile](hosting_providers.md#managed-profile), a setting locked by a variable is
  not shown at all, not even in **Settings › Plugins**, and a save to it is refused as if it did not
  exist: the hosting provider sets it, and the instance's administrators and users never see it.

### 🔐 Saved Secrets and the Instance Key {: #plugin-secrets }

A setting saved inside LibreFolio is kept in the database. A secret one is first encrypted
(AES-256-GCM) with a key derived from the [instance key](#instance-key), and is never shown again,
not even to whoever saved it: LibreFolio only says whether it is set (in **Settings › Plugins**,
*Set on* and the date it was saved). A value given by a variable, secret or not, is never saved in
the database.

If the instance key changes, the saved secrets can no longer be read. LibreFolio keeps them and
reports them as unreadable, and never uses a wrong value. The tab says so under each
one: *Saved, but this instance's key cannot read it. If an administrator can put the old key back,
that comes first; otherwise enter it again.* If you still have the old
key, put it back before anyone enters them again: a secret entered under the new key would become
unreadable once the old one is back. To bring them into another installation, which keeps its own
key, restore a backup there with the old key: `backup restore` with `--instance-key-file`
re-encrypts them with that installation's key ([The Instance Key of Another
Installation](cli_tools.md#backup-restore-instance-key)). From the first start after the change, and at every start
until they are entered again or the old key is back, the log has an error that counts the
instance-wide ones, if there are any: see [Startup Checks](#startup-checks).

If `secrets/instance.key` is damaged or out of reach, LibreFolio starts anyway, with an error from
the [startup checks](#startup-checks); a key you set yourself that cannot be used stops the start
instead. Until you fix it:

- every saved secret is reported as unreadable, and the plugins run without them: a plugin that needs
  one answers that it is not configured;
- secrets given by variables keep working;
- a new secret cannot be saved: the tab answers *Secrets cannot be saved: this instance's key cannot
  be used (see the configuration checks).*, and nothing of that save is written;
- the log has one more error, the first time each server process needs a saved secret:
  `Plugin secrets unreadable: the instance key cannot be used (see the configuration checks)`.

Fix the file, or restore it from a backup, and the saved secrets come back. A new key does not bring
them back: they would have to be entered again.

!!! warning "🗄️ The database and the key in one folder"

    The database (`sqlite/app.db`) and the instance key that LibreFolio generates
    (`secrets/instance.key`) are in the same [data directory](filesystem.md): whoever gets both, the
    folder itself or a copy of it, can read every saved secret.

    - Keep the data directory, and every copy of it, private.
    - Better, give the instance key from a secret store, with `LIBREFOLIO_INSTANCE_KEY_FILE` (a
      Docker secret) or `LIBREFOLIO_INSTANCE_KEY`: LibreFolio then never writes it to the data
      directory. If LibreFolio has already created `secrets/instance.key`, use its content as the
      value, as [The Instance Key](#instance-key) explains: another key would make the saved secrets
      unreadable.

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
| ⚠️ `warning` | `The session signing key from JWT_SECRET is … characters long: use at least 32 random characters` (or `from JWT_SECRET_FILE (<path>)`) | Generate a longer key, as in [Keep users signed in](index.md#session-persistence), and put it where the line says. In the `managed` profile the server does not start instead: see below. |
| ⚠️ `warning` | `Set both directly and through a *_FILE variable: …` | For each secret listed, keep only one of the two: the variable itself wins, the file is ignored. |
| ❌ `error` | `The instance key cannot be used: …`, ending with `cannot be reached (Permission denied)` or `cannot be read (…)` | The `secrets/` folder or `instance.key` belongs to another user, or its permissions keep LibreFolio out. Give both back to the user that runs LibreFolio (`chown`), then `chmod 700` on the folder and `chmod 600` on the file. Never replace the key with a new one. The server starts anyway. |
| ❌ `error` | `The instance key cannot be used: …`, ending with another reason, such as `is empty or blank` | `instance.key` is damaged: restore it from a backup, never replace it with a new key. The server starts anyway. |
| ⚠️ `warning` | `… is open to other users (…): the folder should be 0700 and the file 0600` | Restrict them: `chmod 700` on the `secrets/` folder, `chmod 600` on `instance.key`. |
| ⚠️ `warning` | `SESSION_COOKIE_SECURE=never: the session cookie is sent over plain HTTP too; prefer auto` | Go back to `auto` unless you really need `never`: see [HTTPS and reverse proxies](#session-cookie-secure). |
| ⚠️ `warning` | `LIBREFOLIO_FRAME_PROTECTION is off in the managed profile: any site can show LibreFolio in a frame; the managed profile turns it on` (`check` is `platform.frame_protection`; in the `managed` profile only) | Unless you mean to let pages at other addresses show LibreFolio in a frame, such as your hosting panel ([Hosting for Others](hosting_providers.md#managed-profile)), remove `LIBREFOLIO_FRAME_PROTECTION` from `.env` and from the environment, or set it to `true`, then restart. If neither `.env` nor the environment sets it, it is a fault of LibreFolio's own profile table: set it to `true` yourself, and report it. |
| ℹ️ `info` | `LIBREFOLIO_CSP_REPORT_ONLY is off in the managed profile: browsers list no Content-Security-Policy violation; the managed profile turns it on` (`check` is `platform.csp_report_only`; in the `managed` profile only) | Unless you turned it off on purpose, do the same for `LIBREFOLIO_CSP_REPORT_ONLY`. Nothing is blocked either way: the policy only reports, in the browser's developer console. |
| ℹ️ `info` | `The log level is DEBUG: the log records operational detail; …` (or `TRACE`) | Go back to `INFO` once you are done troubleshooting. |
| ❌ `error` | `LIBREFOLIO_TEST_MODE is on outside a test lane: test-only providers are served, the data are kept in the test data directory <path> and .env is not read; unset it on a production instance` (`check` is `platform.test_mode`) | Test mode is for LibreFolio's own test runs (`./dev.py test`, `./dev.py server --test`), which turn it on and off by themselves: remove `LIBREFOLIO_TEST_MODE` from the server's environment, or set it to `0`, then restart: look where the server's environment comes from, such as a service unit or your hosting panel. Until then the server works on the folder the line names instead of your [data directory](filesystem.md): what is entered meanwhile is saved there, not with your data. In the `managed` profile the server does not start instead: see below. |
| ❌ `error` | `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN is too short: use at least 32 random characters; the hosting panel's backup routes answer 503 until it is fixed`, `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN holds a space, a tab or a character outside visible ASCII: write it without them; …`, or `The hosting panel's backup token cannot be read: LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN_FILE: <path> does not exist` (or `cannot be read (…)`, `is empty or blank`, `is not UTF-8 text`, `is larger than 65536 bytes, too large for a secret`) (`check` is `backup.panel_token`) | The token of your hosting panel cannot be used. Generate a new one as in [Hosting for Others](hosting_providers.md#panel-token), or fix the file the line names, then restart. Only the panel's backup routes are off: they answer `503` until then. The server starts anyway. |
| ❌ `error` | `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB cannot be used: expected a whole number of megabytes, 0 for no limit; restore uploads answer 503 until it is fixed` (or, rarely, `The profile's default for LIBREFOLIO_BACKUP_MAX_UPLOAD_MB is missing or of the wrong type, an error of LibreFolio itself: …`) (`check` is `backup.upload_limit`) | Write a whole number of megabytes, `0` for no limit, or remove the variable, then restart ([The Upload Limit of a Restore](hosting_providers.md#restore-upload-limit)). (The rare line is a fault of LibreFolio's own profile table: set the variable yourself, and report it.) Until then Settings › Administration › Backup cannot upload an archive to restore it; the command line still restores one, but in the `managed` profile only with `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` set, such as `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` in front of `backup restore`, since the restore limit follows this one while it is unset. The server starts anyway. |
| ❌ `error` | `LIBREFOLIO_BACKUP_MAX_RESTORE_MB cannot be used: expected a whole number of megabytes, 0 for no limit; restore checks answer 503 until it is fixed`, or the same line naming `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`, which the restore limit follows while it is unset in the `managed` profile (or, rarely, `The profile's default for LIBREFOLIO_BACKUP_MAX_UPLOAD_MB, which LIBREFOLIO_BACKUP_MAX_RESTORE_MB follows while unset, is missing or of the wrong type, an error of LibreFolio itself: restore checks answer 503 until LIBREFOLIO_BACKUP_MAX_RESTORE_MB is set`) (`check` is `backup.restore_limit`) | Write a whole number of megabytes, `0` for no limit, in the variable the line names, or remove it, then restart ([The Upload Limit of a Restore](hosting_providers.md#restore-upload-limit)). (The rare line is a fault of LibreFolio's own profile table: set `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` yourself, and report it.) Until then every check of a restore is refused with `backup_restore_unavailable`, from Settings › Administration › Backup and from the command line, where `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` in front of `backup restore` lifts the limit for that command. The server starts anyway. |
| ⚠️ `warning` | `LIBREFOLIO_LOGIN_LIMIT=off: failed sign-ins are not limited; turn it back on unless this is a test instance` (`check` is `accounts.login_limit`) | Nothing, on an instance kept for tests. Otherwise remove the variable, or set it to `on`, then restart: see [Failed Sign-ins](#login-limit). |
| ❌ `error` | `LIBREFOLIO_SMTP_… cannot be used (SMTP_…): email stays off until it is fixed` (`check` is `email.smtp`) | Email is off, nothing else is: fix the variable the line names, then restart. What each code means: [Configuration Problems](email.md#configuration-problems). The server starts anyway. |
| ⚠️ `warning` | `LIBREFOLIO_SMTP_TLS=none with …: emails, their links and the SMTP password travel unencrypted; use starttls or tls` | Set `LIBREFOLIO_SMTP_TLS` to `starttls` or `tls`, or send through a relay on your own network: see [Security Notes](email.md#security). |
| ℹ️ `info` | `LIBREFOLIO_PUBLIC_URL is not set: emails work, but none with a link (forgotten password, invitation, reset) can go out` (`check` is `email.links`) | Nothing, if no link has to go out by email. Otherwise set `LIBREFOLIO_PUBLIC_URL` to the address your users open LibreFolio at ([Accounts and Sign-ups](#accounts)), then restart: see [Email](email.md). |
| ⚠️ `warning` | `LIBREFOLIO_PUBLIC_URL cannot start a link (it needs http:// or https:// and a host, with no user name, password, ? or #): no email with a link (forgotten password, invitation, reset) can go out` (`check` is `email.links`) | Write the address with `http://` or `https://` and a host name, without user name, password, `?` or `#`, such as `https://librefolio.example.com`, then restart: see [Email](email.md). |
| ❌ `error` | `Stored plugin secrets that the instance key cannot read: <N>. Enter them again in the plugin settings, or restore the instance key they were saved with` (`check` is `platform.plugin_secrets`; this one comes later in the start, once the database is ready) | The instance key changed after these instance-wide [plugin secrets](#plugin-secrets) were saved: a lost `secrets/instance.key` that LibreFolio replaced with a new one, data restored without its `secrets/`, or another `LIBREFOLIO_INSTANCE_KEY`. If you still have the old key (your copy of `secrets/instance.key`, backed up with the data directory as [The Instance Key](#instance-key) says, since a clear archive of **Back up the instance** leaves the key out, while a [secure](backup_restore.md#secure) one carries the key LibreFolio generated and its restore re-encrypts these secrets; or the old value of the variable), stop LibreFolio, put it in place of the new one and start again. Do it before anyone enters a secret again: a secret entered again is saved under the new key, and becomes unreadable once the old one is back. Only if the old key is lost, enter the secrets again in **Settings › Plugins**: from then on, the new key is the one to back up. If the log also says `The instance key cannot be used: …`, fix that first: see above. Personal secrets are not counted: each user sees theirs in their own tab. The server starts anyway. |

Some secrets you configured stop the start instead when they cannot be used: a `JWT_SECRET_FILE` or a
`LIBREFOLIO_INSTANCE_KEY_FILE` that cannot give its secret (see [Secrets in Files](#secret-files)),
or an instance key of your own shorter than 32 characters. In the `managed` profile, a `JWT_SECRET`
shorter than 32 characters stops it too. The error is in the server's console
output (`docker compose logs librefolio` with Docker): it names the variable, and the file when there
is one, never the secret. Fix it, then start
again.

In the `managed` profile, `LIBREFOLIO_TEST_MODE` on outside LibreFolio's own test runs stops the start as well, with
`In the managed profile LIBREFOLIO_TEST_MODE must not be on outside a test lane (no LIBREFOLIO_TEST_LANE_ID of 16 to 128 characters): …; unset LIBREFOLIO_TEST_MODE`
in the console output: remove the variable, then start again (see
[Hosting for Others](hosting_providers.md#managed-profile)).

A `LIBREFOLIO_BLOCKED` or `LIBREFOLIO_DELETION_DATE` value that LibreFolio cannot read also stops the
start, and a blocked instance logs a warning at every start,
`Instance blocked by its hosting provider (LIBREFOLIO_BLOCKED): …`: see
[Hosting for Others](hosting_providers.md#block-variables).

So does a value of the [initial administrator](#initial-admin) that LibreFolio cannot use, in
`LIBREFOLIO_ADMIN_EMAIL`, `LIBREFOLIO_ADMIN_USERNAME` or `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`, even on an
instance that already has accounts, and a `LIBREFOLIO_LOGIN_LIMIT` other than `on` or `off`
([Failed Sign-ins](#login-limit)).

---

## ⏹️ Stopping the Server {: #shutdown }

When the server is asked to stop, it must be done within a time limit, the **shutdown budget**:
8 seconds unless you change it, counted from the signal (SIGTERM from `docker stop`,
`docker compose down` or a restart; SIGINT from Ctrl+C). Most of the time users notice nothing,
except restarts that are quicker and cleaner.

| Variable | Default | What it does |
| --- | --- | --- |
| `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS` | `8` | The shutdown budget, in seconds: a whole number from `2` to `600`, or `0` for no limit, as before release 1.3. A value that cannot be used does not stop the server, unlike the main options: the log says `Shutdown budget setting cannot be used: the default applies`, and the budget stays at 8 seconds. |
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

## 💻 Parameters Set by the Tools

`./dev.py` and Docker Compose set these for you: change them only if you know why.

| Variable | Default | What it does |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Address `./dev.py server` listens on; `127.0.0.1` accepts local connections only. Docker Compose always uses `0.0.0.0`. |
| `LIBREFOLIO_LOG_LEVEL` | — | Replaces `LOG_LEVEL` when set; `./dev.py server --debug` sets it to `DEBUG`. |
| `LIBREFOLIO_NO_SCHEDULER` | — | Any non-empty value, `0` included, turns the scheduled price and FX syncs off. Set by `./dev.py server --no-scheduler`. |
| `LIBREFOLIO_TEST_MODE` | — | `1`, `true` or `yes`, in any case, switches to the test data folder. For LibreFolio's own test runs only: `./dev.py server --test` and the test runners set it, and `./dev.py server` turns it off. A server started without `./dev.py`, such as with `uvicorn` directly or from a service unit, takes it from its environment. On an instance in use, outside the test runner, the [startup checks](#startup-checks) report it as an error, and in the `managed` profile the server does not start. |
| `LIBREFOLIO_TEST_DATA_DIR` | `./backend/data/test` | Folder of the test data; it may not overlap the production one. |

---

## 👥 Accounts and Sign-ups {: #accounts }

Who may create an account, how many accounts the instance may hold, and the limit on failed
sign-ins. Without these variables, the **Registration** setting of the
[Global Settings](settings.md#registration) decides who may sign up, there is no limit on the
number of accounts, and failed sign-ins are limited ([Failed Sign-ins](#login-limit)). All five are
optional: uncomment a line of the **Accounts** section of `.env.example` to set one. Three more, for
hosting providers and scripted installs, create the [initial administrator](#initial-admin) of a new
instance.

| Variable | Default | What it does |
| --- | --- | --- |
| `LIBREFOLIO_REGISTRATION` | _not set_ | Who may create an account: `open` (anyone), `invite` (only with an invitation link) or `disabled` (nobody). Not set: the **Registration** global setting decides, **By invitation** on a new instance unless an administrator changed it (an instance upgraded from an earlier version keeps the mode it had). Set: this value wins, and the global setting cannot be changed from the app. Case and spaces around the value do not matter. Whatever the value, the first account of a new instance can be created from the login page, with **Register here**, and becomes the administrator: see [Who Can Sign Up](settings.md#registration). With `LIBREFOLIO_ADMIN_EMAIL`, LibreFolio creates that administrator itself instead: see [The Initial Administrator](#initial-admin). Set to `open`, it also gives the administrators who open the app at an address outside the local network a warning that names this variable: see [The Open-Registration Warning](settings.md#open-registration-warning). |
| `LIBREFOLIO_MAX_USERS` | _not set_ (no limit) | The most accounts the instance may hold: a whole number, at least `1`. Active accounts count, and so does each invitation until it is used, revoked or expires, each account waiting for its email verification while its link is live, and the [initial administrator](#initial-admin) while it waits for its setup; deactivated accounts do not. See [When the Instance Is Full](#user-limit). |
| `LIBREFOLIO_PUBLIC_URL` | _not set_ | The address your users open LibreFolio at, with `http://` or `https://`, such as `https://librefolio.example.com`. In the [Users](users.md) tab of Settings › Administration, the invitation and password-reset dialogs fill in their **Server address** with it; without it, with the address the administrator's browser is using. The administrator can change that address, and the browser then checks that this LibreFolio answers there. The [command line](cli_tools.md#invite) puts it in front of the invitation, password-reset and setup links it prints; without it, it prints the path only (`/invite#token=…`) and you add the address yourself. Emails with a link need it too, with no fallback to the browser's address: without it, no invitation, password-reset link, setup link or forgotten-password email goes out ([Email](email.md)). An address that holds a user name or a password is refused, and LibreFolio then works as it does without it. |
| `LIBREFOLIO_BILLING_URL` | _not set_ | For hosting providers: the page where the administrator of a managed instance manages the subscription, with `http://` or `https://`. Only administrators see it, as **Manage subscription**: in the [Users](users.md) tab of Settings › Administration, next to the count of places taken and in the banner shown when the instance is full, and on the block page of a [blocked instance](hosting_providers.md#instance-block). Not set: no such link. An address that holds a user name or a password is refused: no such link either. |
| `LIBREFOLIO_LOGIN_LIMIT` | `on` | The limit on failed sign-ins: `on` or `off`, in any case; spaces around the value do not matter. `off` is for a test instance only: anyone can then try passwords without pause, and every start logs a [warning](#startup-checks). Unlike the four above, any other value, `true`, `1` and `yes` included, stops the server at startup. See [Failed Sign-ins](#login-limit). |

An empty value counts as not set. A wrong value of the first four does not stop the server, unlike the
main options: LibreFolio stays on the safe side, and writes an error to its log the first time each
server process needs the value: `Invalid account configuration`, with the variable and its value in
`problem` (an address that holds an `@` is not shown: it may carry a user name or a password), and
in `consequence` what it costs until you fix it. Fix the value, then restart:

| Wrong value | What LibreFolio does | `consequence` in the log |
| --- | --- | --- |
| `LIBREFOLIO_REGISTRATION` other than the three modes | Registration is closed, and the global setting stays locked | `registration stays closed until it is fixed` |
| `LIBREFOLIO_MAX_USERS` that is not a whole number of at least 1, `0` included | A limit of 0: nobody can sign up without an invitation | `registration stays closed until it is fixed` |
| `LIBREFOLIO_PUBLIC_URL` without `http://` or `https://`, or with a user name or a password | Ignored, as if it were not set: the [command line](cli_tools.md#invite) prints the path only and says why under each link, and the dialogs of the [Users](users.md) tab start from the browser's address. No email with a link goes out, and while email works the start log has a [warning](#startup-checks) too ([Email](email.md)) | `links show the bare path until it is fixed` |
| `LIBREFOLIO_BILLING_URL` without `http://` or `https://`, or with a user name or a password | Ignored, as if it were not set | `the billing link stays hidden until it is fixed` |

`LIBREFOLIO_LOGIN_LIMIT` is the exception: a value other than `on` or `off` **stops the server at
startup**, as an unusable value of the [initial administrator](#initial-admin) does. The error is
in the server's console output (`docker compose logs librefolio` with Docker) and names the
variable and the value, such as `LIBREFOLIO_LOGIN_LIMIT='yes': expected on or off`. Fix it, then
start again.

### 📏 When the Instance Is Full {: #user-limit }

When the active accounts, the pending invitations, the accounts waiting for their email verification and an
[initial administrator](#initial-admin) waiting for its setup reach `LIBREFOLIO_MAX_USERS`:

- nobody can sign up without an invitation, whatever the [Registration](settings.md#registration)
  mode;
- an invitation link already sent still works: its place was counted when it was created;
- administrators cannot create invitations or reactivate accounts, except from the
  [command line](cli_tools.md): `user create`, `user invite` and `user activate` print a warning,
  then go ahead.

A place frees up when an account is deactivated or deleted, when an invitation is revoked or
expires, or when the link of an account waiting for its email verification expires (see
*Email Verification* in [Email](email.md)). The first account of a new instance can always be
created.

### 🚦 Failed Sign-ins {: #login-limit }

LibreFolio stops checking passwords for a while when sign-ins keep failing, so that nobody can try
password after password until one works. The limit is on unless you turn it off.

| Limit | Past it |
| --- | --- |
| 10 failed sign-ins every 15 minutes with the same username or email address, whether an account has it or not | Every sign-in with it is refused, the right password included, until the oldest failure is 15 minutes old. |
| 50 failed sign-ins every 15 minutes from the same address, whatever username or email address they use; an IPv6 address counts by its /64, the block one subscriber usually holds. Not counted for the sign-ins that come through a proxy LibreFolio does not trust, on a local address: see *Behind a reverse proxy* below | Every sign-in from that address is refused, for any account, until the oldest failure is 15 minutes old. |

- **What the user sees**: the login page says *Too many login attempts: wait a few minutes and try
  again.* The wait is 15 minutes at most. The answer is the same whether an account exists or not,
  so the limit tells nobody which accounts exist.
- **What counts as a failure**: a wrong password, or a username or email address that no account
  has. At the sign-in, the right password of a deactivated account, or of one still waiting for its
  email verification, counts neither as a failure nor as a success.
- **Trying again does not make the wait longer**: a sign-in the limit refuses is not counted, and
  its password is not even checked.
- **A successful sign-in** clears the failures of the username or email address it used, not those
  of the address it came from.
- **The username and the email address count apart**, even for one account: someone guessing its
  password gets 10 tries with the username and 10 with the email address every 15 minutes, still
  within the 50 of their address. Capitals A to Z do not matter: `Alice` and `alice` share one
  count.
- **The current password counts too.** A wrong current password in **Change Password**, or when a
  user changes their email address in the Profile tab ([Profile](../user/settings/profile.md)),
  counts as a failed sign-in with the account's username, from the same address. So 10 wrong
  current passwords also block signing in with that username, and failed sign-ins with the username
  block those two checks: **Change Password** and the Profile tab then say *Too many wrong
  passwords: wait a few minutes and try again.* Deleting one's own account asks for no password:
  nothing to limit there.
- **Send the link again counts too.** On the login page, an account that waits for its email
  verification gets **Send the link again**, which checks the username or email address and the
  password as a sign-in does ([Email Verification](email.md#verification)). A wrong password there
  counts as a failed sign-in with what was typed, from the same address; past the limit, it is
  refused before the password is checked, and the page says in how many minutes to try again. The
  right password clears the failures of what was typed, as a successful sign-in does. Its own limits
  still apply ([Limits of the Verification Emails](email.md#verification-limits)).
- **Not limited**: the links of invitations, password resets and setups. Their tokens are long
  random values nobody can guess, and a limit per address could refuse them to every user behind
  the same router. **Forgot Password?** asks for no password, and has limits of its own: see
  [Forgotten Passwords](email.md#forgot-password).
- **Kept in memory**, by each server process: a restart forgets every count, which also lets a user
  who cannot wait back in at once. With several server processes (`./dev.py server --workers N`),
  each keeps its own counts, so the limits are N times these; the Docker image runs one.
- **Behind a reverse proxy**, the address that counts is the visitor's, as LibreFolio reads it.
  Tell LibreFolio about your proxy, by listing it in `FORWARDED_ALLOW_IPS` or by naming the header it
  sets in `LIBREFOLIO_CLIENT_IP_HEADER`, as
  [The Visitor's Address](connection_checks.md#client-address) explains. Until then, LibreFolio sees
  every visitor with the proxy's address, and what happens depends on where the proxy is.
- **A proxy LibreFolio does not trust, on a local address** (a Docker network, your own network or
  your VPN), such as a proxy container in front of the Docker image, the usual setup: LibreFolio
  leaves the sign-ins through it out of the limit per address, so that 50 failed sign-ins from
  anyone cannot refuse everyone. The limit per username or email address still counts them. The log
  has one warning per server process, the first time a request through such a proxy meets a limit
  per address:
  `Requests come through a reverse proxy that LibreFolio does not trust: the limits per client address skip them. List the proxy in FORWARDED_ALLOW_IPS, or name the header it sets in LIBREFOLIO_CLIENT_IP_HEADER`.
- **A proxy LibreFolio does not trust, on a public address**, such as a CDN: every visitor shares
  the proxy's address and its count, so 50 failed sign-ins from anyone refuse every sign-in through
  the proxy, the right passwords included, for up to 15 minutes.

**Turning it off.** `LIBREFOLIO_LOGIN_LIMIT=off`, in any case, is meant for a test instance, whose
automated tests sign in wrongly on purpose: nothing is counted and nothing is refused. Every start
then logs a warning, with `accounts.login_limit` in `check`:
`LIBREFOLIO_LOGIN_LIMIT=off: failed sign-ins are not limited; turn it back on unless this is a test instance`.
The same check, on demand, is in the **Security** tab of **Settings › Administration**: a warning,
counted in the number on the tab, until the limit is back on (see «Security» in
[Global Settings](settings.md)).
Remove the variable, or set it to `on`, to turn the limit back on at the next start. Any other
value stops the server at startup: see [Accounts and Sign-ups](#accounts).

### 👑 The Initial Administrator {: #initial-admin }

LibreFolio can create the administrator of a new instance by itself, at its first start, for the
address you give it: nobody can register first and take its place. It is meant for hosting
providers and scripted installs. Without these variables nothing changes, and the first account
registered becomes the administrator ([Who Can Sign Up](settings.md#registration)).

| Variable | Default | What it does |
| --- | --- | --- |
| `LIBREFOLIO_ADMIN_EMAIL` | _not set_ | The email address of the administrator. Setting it turns the initial administrator on. |
| `LIBREFOLIO_ADMIN_USERNAME` | `admin` | The administrator's username: 3 to 50 characters, without `@`, as at registration. |
| `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` | _not set_ | Optional: the token of the setup link, for a hosting panel that delivers the link itself. 32 to 200 characters, only letters, digits and `-` `.` `_` `~`, since it travels in a link: the output of `openssl rand -hex 32`, for example. `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE` reads it from a file instead: see [Secrets](#secrets). Not set: LibreFolio generates the token. |

An empty value counts as not set. Spaces around the email and the username do not matter; the token
is used exactly as written, so a space in it, even at the end, makes it unusable.

At the first start of an instance **without any account**, LibreFolio:

1. creates the administrator, not yet active, with a random password nobody knows: nobody can sign
   in with it yet;
2. sets the **Registration** [global setting](settings.md#registration) to **By invitation**;
   `LIBREFOLIO_REGISTRATION`, when set, still decides;
3. issues a **setup link**, `/setup#token=…`, that works once, for 72 hours. It opens the
   instance's setup page, where the administrator chooses the password and is signed in.

While the administrator waits, nobody can register as the first account, and the administrator
takes a place of `LIBREFOLIO_MAX_USERS`. Who hands over the link depends on the token:

- **With `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`**, the hosting panel that chose it: the link is the
  instance's address followed by `/setup#token=` and the token. LibreFolio neither logs it nor
  emails it. See [Hosting for Others](hosting_providers.md#initial-admin).
- **Without it**, LibreFolio generates the token and hands the link over itself:
    - it writes the link **once** in its log, as a warning:
      `Setup link of the initial administrator, single use: open it to choose the password`, with
      the link in `link` (with Docker: `docker compose logs librefolio`). The link is the full
      address when `LIBREFOLIO_PUBLIC_URL` is set; otherwise it is the path, and `note` asks you to
      put the address of your server in front of it;
    - it emails the link to `LIBREFOLIO_ADMIN_EMAIL` when email works, that is with an SMTP server
      set up ([Email](email.md)) and `LIBREFOLIO_PUBLIC_URL` set. The email is in the instance's
      default language, and goes out once the server is up, so a slow mail server never delays the
      start. If it cannot go, the log has `Setup link of the initial administrator not emailed`,
      with the reason, and the link in the log still works.

A restart while the administrator waits issues nothing new, and does not write the link in the log
again. Once no link works any more, each start logs a warning:
`The initial administrator's setup link has expired: run ./dev.py user setup-link…` when the link
ran out, or
`The initial administrator's setup link was withdrawn (cancelled, or its address changed): run ./dev.py user setup-link…`
when it was [cancelled](users.md#cancel-setup) or the administrator's address changed. That command
prints a new link ([A New Setup Link](cli_tools.md#setup-link)). A new value of
`LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` also gives a new link, at the next start. Changing the username
or the email before the setup, and the rest of the provider's side:
[Hosting for Others](hosting_providers.md#initial-admin).

On an instance that already has accounts, and no administrator waiting, the variables create
nothing: each start logs `LIBREFOLIO_ADMIN_* ignored: this instance already has accounts`. The same
holds once the setup is done.

A value LibreFolio cannot use **stops the server at startup**, on any instance, one that already
has accounts included:

- `LIBREFOLIO_ADMIN_USERNAME` or `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` set without
  `LIBREFOLIO_ADMIN_EMAIL`;
- an email that is not an address;
- a username shorter than 3 or longer than 50 characters, or with an `@` in it: the sign-in reads a
  name with `@` as an email address, and the administrator signs in with the address of
  `LIBREFOLIO_ADMIN_EMAIL` anyway;
- a token shorter than 32 or longer than 200 characters, or with a character other than letters,
  digits and `-` `.` `_` `~`, a space included;
- a `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE` that cannot give the token
  ([Secrets in Files](#secret-files)).

The error is in the server's console output (`docker compose logs librefolio` with Docker): it
names the variable, never the token. Fix the value, then start again.

---

## 🥇 The Order of the Price Providers in the Search {: #provider-order }

When you create an asset, the search asks every price provider at once and lists the results
provider by provider. Each provider declares where it stands: its tier, **premium** for a source an
instance vouches for, such as licensed data, or **community**, the default; and its priority inside
the tier. When at least one premium provider is available, its results come first. None of the
providers shipped with LibreFolio is premium, so without one the search keeps its order.

| Variable | Default | What it does |
| --- | --- | --- |
| `LIBREFOLIO_ASSET_PROVIDERS_PREMIUM` | _not set_ | The providers to count as premium, by code, separated by commas, such as `yfinance,justetf`: exactly these, whatever they declare. Not set: what each provider declares. |
| `LIBREFOLIO_ASSET_PROVIDERS_ORDER` | _not set_ | The providers to list first, in this order, by code, separated by commas; the others follow in their declared order. Premium providers still come before the others. Not set: what each provider declares. |

- The codes of the providers shipped with LibreFolio are `yfinance`, `justetf`, `borsa_italiana`,
  `css_scraper` and `scheduled_investment`; a provider you add has its own. Case and spaces around
  them do not matter.
- A code that no provider has is ignored, and the server logs it once.
- The settings apply at the next search, with no restart: LibreFolio reads them at every search.

---

## 🔎 Optional: Web Search for New Assets

When you create an asset, also from the broker import wizard, and a provider's own search finds
nothing, LibreFolio can find the asset's page with a web search through the
[`ddgs`](https://pypi.org/project/ddgs/) library. It is on by default and never used for price
updates. All these variables are optional: uncomment a line of `.env.example` to change one.

| Variable | Default | What it does |
| --- | --- | --- |
| `LIBREFOLIO_WEB_LINK_FINDER_ENABLED` | `1` | `0` turns the web search off; the providers' own search keeps working. |
| `LIBREFOLIO_WEB_LINK_FINDER_ENGINE` | `ddgs` | `ddgs` needs no setup. `apikey` is reserved for a paid search service and returns no results yet. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_REGION` | `wt-wt` | Search region. `wt-wt` (worldwide) keeps national sites such as Borsa Italiana from being pushed down. Examples: `it-it`, `us-en`. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND` | `auto` | Engines that `ddgs` queries: `auto` rotates them for the widest coverage; a list such as `google,bing,duckduckgo` gives steadier results. |
| `LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT` | `6` | Time limit of one search, in seconds: at least `1`. Any other value means the default. |
| `LIBREFOLIO_WEB_LINK_FINDER_MAX` | `5` | Most links returned by one search: a whole number, at least `1`. Any other value means the default. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | _empty_ | Key for the `apikey` engine. `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` reads it from a file instead: see [Secrets](#secrets). |

??? tip "🔁 Results change between attempts — when a known asset is sometimes not found"

    With `auto`, each search may reach different engines, so the same query can do better or worse
    from one try to the next. Retry once, or set
    `LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND=google,bing,duckduckgo`.

---

## 🔝 Which Value Wins

From the highest priority to the lowest:

1. The `--host`, `--port` and `--data-dir` options of `./dev.py server`.
2. Variables set in the shell.
3. The `.env` file.
4. The defaults listed on this page.

With Docker Compose, the `environment:` block of `docker-compose.yml` wins over `.env`: it fixes
`HOST`, `LIBREFOLIO_DATA_DIR` and, inside the container, `PORT=6040` (your `PORT` still sets the host
port). See [Advanced Docker](docker_advanced.md#resolution-priority).

For a [plugin setting](#plugin-settings), from the highest priority to the lowest: its variable
(`LIBREFOLIO_PLUGIN_…` before the plugin's older name for it, each before its `_FILE` form), the
value saved inside LibreFolio, then the plugin's default. A variable with a wrong value still wins,
and leaves the plugin not configured. A personal setting has no variable: the user's saved value,
then the default.

---

## 📂 Where the Data Goes

- **Production**: `backend/data/prod/`, or `LIBREFOLIO_DATA_DIR`. It holds the database
  (`sqlite/app.db`), `custom-uploads/`, `broker_reports/`, `logs/` and, once LibreFolio has created
  the [instance key](#instance-key), `secrets/`.
- **Test**: `backend/data/test/`, or `LIBREFOLIO_TEST_DATA_DIR`. Same layout, kept apart.

[Filesystem Structure](filesystem.md) details each folder and how to back it up.

---

## 🔗 Related

- ⚙️ **[Global Settings](settings.md)** — Options changed from inside the app
- 🐳 **[Advanced Docker](docker_advanced.md)** — Compose file, volumes, user and group IDs
- 🧑‍💻 For developers: **[Settings System](../developer/architecture/settings.md)** — How these
  values are loaded
- 🔒 For developers: **[Security Architecture](../developer/architecture/security.md)** — Secrets,
  the instance key, the startup checks and the limit on failed sign-ins
- 🧩 For developers: **[Plugin Settings](../developer/architecture/patterns/plugin_settings.md)** —
  How plugins declare settings, and how secrets are protected
