# 📝 Configuration

LibreFolio's startup options live in a `.env` file: ports, the data folder, logging, login sessions, sign-ups, secrets and a few optional features.

**Where it goes**: in the `.env` file in LibreFolio's folder (the root of the project; with Docker, the folder of `docker-compose.yml`). With Docker, the same variables also work in the `environment:` block of `docker-compose.yml`, which wins over `.env`. LibreFolio reads `.env` when it starts.

The options you change from inside the app are the [Global Settings](settings.md) instead.

!!! info "📚 This guide is in several pages"

    - [Configuration: Secrets and Plugin Settings](configuration_secrets.md): the options that are secrets, how to read them from files, the instance key and the settings of the plugins.
    - [Configuration: Checks and Protections](configuration_security.md): what LibreFolio checks at startup, the browser protections (Content-Security-Policy, frame protection) and how it stops.
    - [Configuration: Accounts and Asset Search](configuration_accounts.md): who can sign up, the limit on failed sign-ins, the initial administrator, the order of the price providers in the search and the web search.

---

## 🔧 Create the `.env` File

**In LibreFolio's folder**, from a terminal:

1. Copy the sample file:

    ```bash
    cp .env.example .env
    ```

    You get a `.env` with every option, grouped by what they do. With the pre-built Docker image, the [Docker installation](../user/installation.md) guide downloads the same sample as `.env`.

2. Edit the values you need. A commented option, such as `# SESSION_COOKIE_SECURE=auto`, shows the default: remove the `#` only to change the value. Names are case-sensitive.

3. Restart LibreFolio. With Docker Compose, run `docker compose up -d`.

---

## ✏️ Main Options {: #main-options }

**Where**: in LibreFolio's `.env`, or in the container's environment (`environment:` block of `docker-compose.yml`). Then restart LibreFolio. With Docker Compose, run `docker compose up -d`.

In the main options and in the risk settings below, a value of the wrong type or out of range stops the server at startup with an error. The exceptions are in the details under each table, with what appears in the log.

**Server, data and logs**

| Variable | Default | What it does |
| --- | --- | --- |
| `PORT` | `6040` | Port of the web server. With Docker Compose, the port opened on the host: the container always listens on `6040`. |
| `TEST_PORT` | `6041` | Port of the test server (`./dev.py server --test`). |
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Folder of the database, the uploads, the broker reports and the logs; a relative path starts from the project folder. |
| `LOG_LEVEL` | `INFO` | How much the server writes to the logs: `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`. |
| `PREVIEW_CACHE_MAX_MB` | `50` | Memory, in MB, of the image-preview cache, for each server process. |

- **`LIBREFOLIO_DATA_DIR` with Docker**: fixed to `/app/backend/data/prod-docker`. To move the data on the host, **in `docker-compose.yml`** change the left side of the `./LibreFolio-data` volume.
- **`LOG_LEVEL`**: at `DEBUG` or `TRACE`, the web app also writes to the browser's console every failed call to the server, the refused ones included (a `4xx` answer); at the other levels, only the server errors, the calls that got no answer and the answers it cannot read.

**Login sessions and reverse proxies**

| Variable | Default | What it does |
| --- | --- | --- |
| `JWT_SECRET` | _not set_ | Key that signs the login sessions. See [Keep users signed in](index.md#session-persistence). |
| `SESSION_COOKIE_SECURE` | `auto` | When the login session cookie is sent over HTTPS only: `auto` (if the browser uses HTTPS), `always` or `never`. See [HTTPS and reverse proxies](#session-cookie-secure). |
| `LIBREFOLIO_CLIENT_IP_HEADER` | _not set_ | Behind a reverse proxy, the header in which it passes the visitor's address, such as `Fly-Client-IP` on Fly.io. See [The Visitor's Address](connection_proxy.md#client-address). |

- **`JWT_SECRET`** not set, empty or made of spaces only: a new key at every start, so everyone has to sign in again after a restart. `JWT_SECRET_FILE` reads it from a file instead: see [Secrets](configuration_secrets.md#secrets).
- **`LIBREFOLIO_CLIENT_IP_HEADER`**: set it only if every request crosses that proxy.

**Browser protections and API documentation**

| Variable | Default | What it does |
| --- | --- | --- |
| `LIBREFOLIO_FRAME_PROTECTION` | `false` | Leave it unset on an install of your own. `true` lets only LibreFolio's own pages show it in a frame. See [Frame Protection](configuration_security.md#frame-protection). |
| `LIBREFOLIO_CSP_REPORT_ONLY` | `false` | Leave it unset on an install of your own. `true` adds a second, wider Content-Security-Policy to the pages of the web app, in report-only mode. See [The Report-Only Policy](configuration_security.md#csp-report-only). |
| `LIBREFOLIO_API_DOCS` | `false` | Leave it unset. `true` serves the API's documentation pages: Swagger UI at `/api/v1/docs`, ReDoc at `/api/v1/redoc`, schema at `/api/v1/openapi.json`. |

- **`LIBREFOLIO_FRAME_PROTECTION`** not set: dashboards at another address, such as Home Assistant panels, can show LibreFolio in a frame. `true` adds `X-Frame-Options: SAMEORIGIN` and `Content-Security-Policy: frame-ancestors 'self'` to every response. The three rules `object-src 'none'; base-uri 'self'; form-action 'self'` do not depend on this option: LibreFolio's pages always carry them ([The Content-Security-Policy](configuration_security.md#csp)). Valid values: `true` or `false`; `1`/`0`, `yes`/`no` and `on`/`off` too, in any case; any other value stops the server at startup.
- **`LIBREFOLIO_CSP_REPORT_ONLY`**: only the pages of the web app, not the documentation or the API. It blocks nothing: the browser lists in its developer console what that policy would block, without sending a report anywhere. The enforced [Content-Security-Policy](configuration_security.md#csp) always stays on. Same values as `LIBREFOLIO_FRAME_PROTECTION`.
- **`LIBREFOLIO_API_DOCS`** off: the pages answer `404`, in every profile and with Docker too (an instance in use does not publish the map of its own API). A browser that opens one of these addresses, another address under `/api/` or a documentation page that does not exist under `/mkdocs/` is taken to the app (`/`); a program still gets `404` with `{"detail": "Not Found"}`. In the web app, a page that does not exist takes you back to the page you came from, or to the Dashboard. `./dev.py server --debug` turns it on; LibreFolio's test runs keep it on. Valid values: `true` or `false`; `1` and `0` too. The pages' own policy: [The Content-Security-Policy](configuration_security.md#csp).

**Instance links: support, terms of service, privacy**

| Variable | Default | What it does |
| --- | --- | --- |
| `LIBREFOLIO_SUPPORT_URL` | _not set_ | Where the users of the instance ask for help: a page with `http://` or `https://`, or an email address such as `mailto:help@example.org`. |
| `LIBREFOLIO_TOS_URL` | _not set_ | The terms of service of the instance: a page with `http://` or `https://`, linked from the **Terms of service** link of the legal notice. |
| `LIBREFOLIO_PRIVACY_URL` | _not set_ | The privacy policy of the instance, linked as **Privacy policy** next to the terms of service: same rules as `LIBREFOLIO_TOS_URL`. |

- **The three addresses are public**: anyone who can reach the server can read them at `/api/v1/system/instance`.
- **`LIBREFOLIO_SUPPORT_URL`**: for example for an asset the search does not find ([Let us know](../user/assets/create-edit.md#let-us-know), under the search results). With an email address, the user's email app opens a message with the details of the search. With a page, it opens in a new tab and receives the report in the `title` and `body` query parameters, like a prefilled GitHub issue, so that a support form can fill itself in; the details are copied too, to paste there. Not set: on an install of your own (the `selfhosted` profile), a new public issue on LibreFolio's GitHub opens with the details, for the user to review before sending it. Any other value is ignored, as if it were not set, and the server logs it once. A page whose address holds a user name or a password counts as not set too.
- **`LIBREFOLIO_TOS_URL`**: the legal notice that every user sees (Settings › About, the Welcome page, under the card of every sign-in page, at the foot of the sidebar) points to the terms with the **Terms of service** link, opened in a new tab. Not set: no link, the notice alone. Unlike `LIBREFOLIO_SUPPORT_URL`, no `mailto:`.
- **A value that cannot be used in `LIBREFOLIO_TOS_URL` or `LIBREFOLIO_PRIVACY_URL`**, an address with a user name or a password included: the server never stops; that link stays hidden and the legal notice is shown without it. The log has an error, `Invalid instance link`, the first time each server process answers `/api/v1/system/instance` (the app reads it as soon as it opens): the variable and its value in `problem` (a value with an `@` is not shown: it may hold a user name or a password) and, in `consequence`, what it costs until you fix it, for example `the terms of service link stays hidden until it is fixed: the legal notice shows without it`. A `LIBREFOLIO_SUPPORT_URL` that cannot be used logs the same error too, with its own `consequence`. Fix the value, then restart.

**Backup and space**

| Variable | Default | What it does |
| --- | --- | --- |
| `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` | _not set_: no limit | Leave it unset. The largest size, in megabytes, of an archive an administrator may upload to check it for a restore; `0` means no limit. See [The Upload Limit of a Restore](backup_restore.md#restore-upload-limit). |
| `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` | _not set_: no limit | Leave it unset. The largest size, in megabytes, an archive may unpack to while it is checked for a restore, from the sizes its manifest declares; `0` means no limit. |
| `LIBREFOLIO_BACKUP_RECIPIENTS` | _not set_ | One or two age public keys (`age1…`), comma-separated: `backup create --sealed` then makes a [sealed](backup_sealed.md#sealed) backup. Not a secret. |
| `LIBREFOLIO_STORAGE_LIMIT_MB` | _not set_ | Leave it unset on an install of your own: the limit is set in the space bar of the **Files** page. The space the instance may take, in megabytes; `0` means no limit. See [The Space Bar](backup_restore.md#space-used). |

- **All four are read from the environment only.**
- **`LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`** with a value that is not a whole number: the server does not stop; the uploads answer `503` and the log has an error, from startup already ([Startup Checks](configuration_security.md#startup-checks)) and then each time the limit is read.
- **`LIBREFOLIO_BACKUP_MAX_RESTORE_MB`**: a value you set always wins, `0` included; `backup restore` on the command line follows it too. An archive over the limit is refused before anything is unpacked (`unpacked_too_large`). With a value that is not a whole number the server does not stop: the checks of a restore answer `503` (`backup_restore_unavailable`), the log has an error from startup already ([Startup Checks](configuration_security.md#startup-checks)) and then at each check, and the **Security** tab of Settings › Administration reports it (`backup.restore_limit`).
- **`LIBREFOLIO_BACKUP_RECIPIENTS`**: the keys as `backup keygen` or `age-keygen` print them; two only while a key is being changed. The sealed backup is a `.tar` that only the matching private keys open, never the instance key. A value that cannot be used (a key that is not `age1…`, more than two, the same one twice) does not stop the server: the log has an error and the **Security** tab of Settings › Administration reports it (`backup.recipients`).
- **`LIBREFOLIO_STORAGE_LIMIT_MB`** set: it wins over the **LibreFolio total space (MB)** setting, whatever value an administrator saved, and locks it: the field in the space bar is disabled (greyed out) and a save is refused. Not set: the setting decides, `0` until an administrator saves another value. A value that is not a whole number is ignored and the setting applies. Past the limit, LibreFolio refuses an uploaded file, a broker report, a backup started by hand and a restore that would take the data beyond it; it deletes nothing. The administrator cannot raise it from here: the message asks whoever hosts the instance to do it.

**Price providers and broker imports**

| Variable | Default | What it does |
| --- | --- | --- |
| `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS` | `60` | The first pause of a price provider that answers «too many requests» (HTTP 429); each refusal in a row doubles the next pause. A whole number of seconds from `0` to `86400`; `0` turns the pauses off. See [Provider Pauses](settings.md#provider-pauses). |
| `LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS` | `3600` | The longest pause the doubling reaches: a whole number of seconds from `1` to `86400`, not below the first pause while the pauses are on. |
| `LIBREFOLIO_PROBE_RATE_LIMIT` | `30` | How many times a minute one user may test the settings of a price provider (**Test Configuration** in the asset form; **Ask Provider** counts too). A whole number from `0` to `10000`; `0` turns the limit off. |
| `LIBREFOLIO_BRIM_PREWARM` | `false` (`true` in test mode) | Optional. `true` makes the workers for importing broker reports ready at startup, with the import plugins loaded. See [BRIM Architecture → Preload and warm-up](../developer/backend/brim/architecture.md#parse-pool-warm-up). |

- **Provider pauses**: during a pause no request reaches the provider. On by default: an exception to the rule that a new option leaves an install as it was. A provider's `Retry-After` may still ask for more, up to one day. A value that cannot be used in either variable does not stop the server: the log has an error and both defaults apply.
- **`LIBREFOLIO_PROBE_RATE_LIMIT`**: the tests may call the provider; past the limit, the form tells the user when to try again. `0` only for a test instance (`./dev.py server --test` does it): the log has a warning at every start. Read at every test: a change applies without a restart. A value that cannot be used does not stop the server: the log has an error and `30` applies.
- **`LIBREFOLIO_BRIM_PREWARM`**: the first broker import after a start is about 4 seconds faster, for about 80 MB of memory from startup and about 1.4 seconds of CPU at every start; on a small cloud machine they cost more than the seconds they save, so it is off. Valid values: `true` or `false`; `1`/`0`, `yes`/`no` and `on`/`off` too, in any case. Any other value does not stop the server, unlike the main options: the log has a warning at startup and the option stays off.

**Email**

| Variable | Default | What it does |
| --- | --- | --- |
| `LIBREFOLIO_SMTP_HOST` | _not set_: email off | Optional. The SMTP server that sends LibreFolio's emails, such as `smtp.example.com`. |
| `LIBREFOLIO_SMTP_TLS` | `starttls` | How the connection to the SMTP server is encrypted: `starttls`, `tls` or `none`. See [Encryption Modes](email.md#encryption-modes). |
| `LIBREFOLIO_SMTP_PORT` | `587` with `starttls`, `465` with `tls`, `25` with `none` | The port of the SMTP server, only when it is not the usual one of its encryption mode. |
| `LIBREFOLIO_SMTP_USER` | _not set_: no login | The user for the login on the SMTP server, set together with `LIBREFOLIO_SMTP_PASSWORD` ([Secrets](configuration_secrets.md#secrets)). |
| `LIBREFOLIO_SMTP_FROM` | _not set_ | The sender of the emails, required as soon as a server is set. |
| `LIBREFOLIO_SMTP_REPLY_TO` | _not set_: replies go to the sender | Where the replies to LibreFolio's emails go. |
| `LIBREFOLIO_SMTP_MAX_PER_HOUR` | `50` | How many emails the instance may send in an hour, per server process. |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` | `20` | How many registration emails one client address may trigger in an hour, per server process: a whole number, at least 1. See [Limits on Activation and Password-Reset Emails](email_flows.md#activation-limits). |

- **`LIBREFOLIO_SMTP_*` variables**: all explained in [Email](email.md#variables).
- **`LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS`**: one single count for the registrations, **Send the link again** and **Forgot Password?**. Past the limit, a new account is created and waits, and its email is held.

Older `.env` files may still contain `PORTFOLIO_BASE_CURRENCY`: LibreFolio ignores it and new users start from the **Default Currency** in [Global Settings](settings.md).

??? info "🔒 HTTPS and reverse proxies — the session cookie"

    `SESSION_COOKIE_SECURE` decides when the cookie that keeps users signed in is `Secure`: the browser then sends it over HTTPS only. Case and spaces around the value do not matter; any other value stops the server at startup with an error.
    {: #session-cookie-secure }

    | Value | When to use it |
    | --- | --- |
    | `auto` (default) | `Secure` when the browser reached LibreFolio over HTTPS, that is when the reverse proxy says so with the `X-Forwarded-Proto: https` header (only the first value counts). No list of trusted proxies to set up: the header can only turn `Secure` on, never off. Over plain HTTP (`http://localhost:6040`, a LAN IP, the Tailscale IP of Levels 1 and 2 in [Exposing Securely](service_exposure.md)) the cookie is not `Secure` and signing in works. |
    | `always` | Always `Secure`: an install reached over HTTPS only. Over plain HTTP the browser drops the cookie and the sign-in does not stick: the next page sends you back to the login. |
    | `never` | Never `Secure`. The way out when a proxy sends `X-Forwarded-Proto: https` to a browser that uses plain HTTP, such as Nginx with a hard-coded `proxy_set_header X-Forwarded-Proto https;` in a plain-HTTP `server` block: with `auto`, that browser would be sent back to the login after every sign-in. Better fix the proxy (`$scheme` instead of `https`); `never` is the fallback. |

    With `auto`, behind an HTTPS reverse proxy the proxy must send `X-Forwarded-Proto`:

    - **Tailscale Serve and Funnel** (Levels 3 and 4 in [Exposing Securely](service_exposure.md)), **Caddy** and **Traefik** send it on their own: nothing to configure.
    - **Nginx** does not. **In Nginx's configuration**, in the `location` block that proxies LibreFolio, add:

        ```nginx
        proxy_set_header X-Forwarded-Proto $scheme;
        ```

    - **Any other proxy**: make it send the header. Or, if LibreFolio is reachable only through it, **in `.env`**:

        ```bash
        SESSION_COOKIE_SECURE=always
        ```

    To check in your browser whether the session cookie is `Secure`: [Checking Connection Security](connection_checks.md#session-cookie).

??? info "🧮 Risk engine workers — advanced tuning"

    Risk simulations and portfolio optimizations run in separate worker processes, started on first use. The defaults suit most installs: add a variable **to `.env`** only to change them.

    | Variable | Default | What it does |
    | --- | --- | --- |
    | `RISK_SIMULATION_WORKERS`, `RISK_OPTIMIZATION_WORKERS` | `1` (1–8) | Worker processes per kind of job: more processes run more jobs at once. |
    | `RISK_SIMULATION_QUEUE_CAPACITY`, `RISK_OPTIMIZATION_QUEUE_CAPACITY` | `2` (0–64) | Jobs that can wait for a worker; beyond that limit, new requests are refused. |
    | `RISK_SIMULATION_TIMEOUT_SECONDS`, `RISK_OPTIMIZATION_TIMEOUT_SECONDS` | `120` / `60` | Time limit of one job, in seconds. |
    | `RISK_SIMULATION_IDLE_TIMEOUT_SECONDS`, `RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS` | `600` | Idle workers stop after this many seconds and start again with the next job; `0` keeps them running. |

---

## 💻 Parameters Set by the Tools

`./dev.py` and Docker Compose set them for you: change them only if you know why.

| Variable | Default | What it does |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Address `./dev.py server` listens on; `127.0.0.1` accepts local connections only. Docker Compose always uses `0.0.0.0`. |
| `LIBREFOLIO_LOG_LEVEL` | — | Replaces `LOG_LEVEL` when set; `./dev.py server --debug` and `./dev.py server --test` set it to `DEBUG`. |
| `LIBREFOLIO_API_DOCS` | — | Set to `1` by `./dev.py server --debug`, which turns on the API's documentation pages (the variable of the same name, above). |
| `LIBREFOLIO_NO_SCHEDULER` | — | Any non-empty value, `0` included, turns the scheduled price and FX rate syncs off. Set by `./dev.py server --no-scheduler`. |
| `LIBREFOLIO_TEST_MODE` | — | `1`, `true` or `yes`, in any case, switches to the test data folder. For LibreFolio's test runs only: `./dev.py server --test` and the test runners set it, `./dev.py server` turns it off. A server started without `./dev.py` (`uvicorn` directly, a service unit) takes it from its own environment. On an instance in use, outside the test runner, the [startup checks](configuration_security.md#startup-checks) report it as an error. |
| `LIBREFOLIO_TEST_DATA_DIR` | `./backend/data/test` | Folder of the test data; it cannot overlap the production one. |

---

## 🔝 Which Value Wins

From the highest priority to the lowest:

1. The `--host`, `--port` and `--data-dir` options of `./dev.py server`.
2. The variables set in the shell.
3. The `.env` file.
4. The defaults listed on this page.

With Docker Compose, the `environment:` block of `docker-compose.yml` wins over `.env`: it fixes `HOST`, `LIBREFOLIO_DATA_DIR` and, inside the container, `PORT=6040` (your `PORT` still sets the port on the host). See [Advanced Docker](docker_advanced.md#resolution-priority).

For a [plugin setting](configuration_secrets.md#plugin-settings), from the highest priority to the lowest:

1. Its variable: `LIBREFOLIO_PLUGIN_…` before the plugin's older name for it, and each before its `_FILE` form.
2. The value saved inside LibreFolio.
3. The plugin's default.

A variable with a wrong value still wins and leaves the plugin not configured. A personal setting has no variable: the value saved by the user, then the default.

---

## 📂 Where the Data Goes

- **Production**: `backend/data/prod/`, or `LIBREFOLIO_DATA_DIR`. It holds the database (`sqlite/app.db`), `custom-uploads/`, `broker_reports/`, `logs/` and, once LibreFolio has created the [instance key](configuration_secrets.md#instance-key), `secrets/`.
- **Test**: `backend/data/test/`, or `LIBREFOLIO_TEST_DATA_DIR`. Same layout, kept apart.

[Filesystem Structure](filesystem.md) details each folder and how to back it up.

---

## 🔗 Related

- 📄 **[Configuration: Secrets and Plugin Settings](configuration_secrets.md)** — Secrets, Plugin Settings
- 📄 **[Configuration: Checks and Protections](configuration_security.md)** — Startup Checks, Browser Protections, Stopping the Server
- 📄 **[Configuration: Accounts and Asset Search](configuration_accounts.md)** — Accounts and Sign-ups, The Order of the Price Providers in the Search, Optional: Web Search for New Assets
- ⚙️ **[Global Settings](settings.md)** — Options changed from inside the app
- 🐳 **[Advanced Docker](docker_advanced.md)** — Compose file, volumes, user and group IDs
- 🧑‍💻 For developers: **[Settings System](../developer/architecture/settings.md)** — How these values are loaded
- 🔒 For developers: **[Security Architecture](../developer/architecture/security.md)** — Secrets, the instance key, the startup checks and the limit on failed sign-ins
- 🧩 For developers: **[Plugin Settings](../developer/architecture/patterns/plugin_settings.md)** — How plugins declare settings and how secrets are protected
