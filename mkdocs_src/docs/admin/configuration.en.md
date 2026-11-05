# 📝 Configuration

Startup options live in a `.env` file: ports, the data folder, logging, login sessions, sign-ups,
secrets and a few optional features. It sits at the root of the project, or next to
`docker-compose.yml` with Docker. The options you change from inside the app are
[Global Settings](settings.md) instead.

This page is the start of the configuration guide: how to create the `.env` file, the **main
options** with their defaults, and which value wins when the same option is set in several places.

!!! info "📚 This guide is in several pages"

    The rest of the guide goes deeper, once the basics here are in place:

    - [Configuration: Secrets and Plugin Settings](configuration_secrets.md): the options that are secrets, how to read them from files, the instance key and the settings of the plugins.
    - [Configuration: Checks and Protections](configuration_security.md): what LibreFolio checks at its start, the browser protections (Content-Security-Policy, frame protection) and how it stops.
    - [Configuration: Accounts and Asset Search](configuration_accounts.md): who can sign up, the limit on failed sign-ins, the initial administrator, the order of the price providers in the search and the web search.

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

## ✏️ Main Options {: #main-options }

| Variable | Default | What it does |
| --- | --- | --- |
| `PORT` | `6040` | Port of the web server. With Docker Compose, the port opened on the host (the container always listens on `6040`). |
| `TEST_PORT` | `6041` | Port of the test server (`./dev.py server --test`). |
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Folder of the database, uploads, broker reports and logs; a relative path starts from the project folder. Docker fixes it to `/app/backend/data/prod-docker`: to move the data on the host, change the left side of the `./LibreFolio-data` volume in `docker-compose.yml`. |
| `LOG_LEVEL` | `INFO` | How much the server logs: `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`. At `DEBUG` or `TRACE`, the web app also writes every failed call to the server to the browser's console, a refused one (a `4xx` answer) included; at the other levels, only the server errors, the calls that got no answer and the answers it cannot read. |
| `JWT_SECRET` | _not set_ | Key that signs login sessions. Not set, empty or only spaces: a new key at every start, so everyone logs in again after a restart. `JWT_SECRET_FILE` reads it from a file instead: see [Secrets](configuration_secrets.md#secrets). See [Keep users signed in](index.md#session-persistence). |
| `SESSION_COOKIE_SECURE` | `auto` | When the login session cookie is sent over HTTPS only: `auto` (if the browser uses HTTPS), `always` or `never`. See [HTTPS and reverse proxies](#session-cookie-secure). |
| `LIBREFOLIO_CLIENT_IP_HEADER` | _not set_ | Behind a reverse proxy, the header in which it passes the visitor's address, such as `Fly-Client-IP` on Fly.io: set it only if every request crosses that proxy. See [The Visitor's Address](connection_proxy.md#client-address). |
| `PREVIEW_CACHE_MAX_MB` | `50` | Memory, in MB, of the image-preview cache in each server process. |
| `LIBREFOLIO_FRAME_PROTECTION` | `false` | Leave it unset on an install of your own: dashboards at another address, such as Home Assistant panels, can then show LibreFolio in a frame. `true` lets only LibreFolio's own pages show it in a frame, with `X-Frame-Options: SAMEORIGIN` and `Content-Security-Policy: frame-ancestors 'self'`, to every response. The three rules `object-src 'none'; base-uri 'self'; form-action 'self'` do not depend on it: LibreFolio's pages always carry them ([The Content-Security-Policy](configuration_security.md#csp)). `true` or `false`; `1`/`0`, `yes`/`no` and `on`/`off` work too, in any case; any other value stops the server at startup. See [Frame Protection](configuration_security.md#frame-protection). |
| `LIBREFOLIO_CSP_REPORT_ONLY` | `false` | Leave it unset on an install of your own. `true` adds a second, wider Content-Security-Policy to the pages of the web app, not to the documentation or the API, in report-only mode: it blocks nothing, and the browser lists in its developer console what that wider policy would block, without sending a report anywhere. The enforced [Content-Security-Policy](configuration_security.md#csp) is always on, with or without it. Same values as `LIBREFOLIO_FRAME_PROTECTION`. See [The Report-Only Policy](configuration_security.md#csp-report-only). |
| `LIBREFOLIO_API_DOCS` | `false` | Leave it unset. `true` serves the API's own documentation pages, Swagger UI at `/api/v1/docs` and ReDoc at `/api/v1/redoc`, with the API's schema at `/api/v1/openapi.json`. Off, they answer `404`, in every profile and with Docker too: an instance in use publishes no map of its API. A browser that opens one of these addresses, or any other address under `/api/`, or a documentation page that does not exist under `/mkdocs/`, is taken to the app (`/`); a program calling the API still gets `404` with `{"detail": "Not Found"}`. In the web app, a page that does not exist takes you back to the page you came from, or to the Dashboard. It is a tool for developers, so `./dev.py server --debug` turns it on, and LibreFolio's own test runs have it on. `true` or `false`; `1` and `0` work too. The pages' own policy is in [The Content-Security-Policy](configuration_security.md#csp). |
| `LIBREFOLIO_SUPPORT_URL` | _not set_ | Where the users of the instance ask for help, such as an asset the search does not find ([Let us know](../user/assets/create-edit.md#let-us-know), under the search results): a page with `http://` or `https://`, or one email address as `mailto:help@example.org`. With an email address, the user's email app opens a message with the details of the search; with a page, the page opens in a new tab and receives the report in its address, as the `title` and `body` query parameters, like a prefilled GitHub issue, so that a support form can fill itself in, and the details are copied too, to paste there. Not set: on an install of your own (the `selfhosted` profile), a new public issue on LibreFolio's GitHub opens with the details, for the user to review before sending it. Any other value is ignored, as if it were not set, and the server logs it once. A page whose address holds a user name or a password counts as not set too. The address is public: anyone who can reach the server can read it at `/api/v1/system/instance`. |
| `LIBREFOLIO_TOS_URL` | _not set_ | The terms of service of the instance: a page with `http://` or `https://`. The legal notice that every user sees, in Settings › About, on the Welcome page, under the card of every sign-in page and at the foot of the sidebar, links it as **Terms of service**, opened in a new tab. Not set: no link, the notice alone. Unlike `LIBREFOLIO_SUPPORT_URL`, no `mailto:`. A value LibreFolio cannot use, an address with a user name or a password included, does not stop the server: the link stays hidden, and the log has an error (see below). The address is public: anyone who can reach the server can read it at `/api/v1/system/instance`. |
| `LIBREFOLIO_PRIVACY_URL` | _not set_ | The privacy policy of the instance, linked as **Privacy policy** next to the terms of service: the same rules as `LIBREFOLIO_TOS_URL`. |
| `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` | _not set_ | Leave it unset. The largest archive an administrator may upload to check it for a restore, in megabytes; `0` is no limit. Not set: no limit. A value that is not a whole number does not stop the server: the uploads answer `503`, and the log has an error, from the start already ([Startup Checks](configuration_security.md#startup-checks)) and then each time the limit is read. Read from the environment only. See [The Upload Limit of a Restore](backup_restore.md#restore-upload-limit). |
| `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` | _not set_ | Leave it unset. The largest size an archive may unpack to while it is checked for a restore, in megabytes, from the sizes its manifest declares; `0` is no limit. Not set: no limit. A value you set always wins, `0` included, and `backup restore` on the command line follows it too. An archive over the limit is refused before anything is unpacked (`unpacked_too_large`). A value that is not a whole number does not stop the server: the checks of a restore answer `503` (`backup_restore_unavailable`), the log has an error, from the start already ([Startup Checks](configuration_security.md#startup-checks)) and then at each check, and the **Security** tab of Settings › Administration reports it (`backup.restore_limit`). Read from the environment only. See [The Upload Limit of a Restore](backup_restore.md#restore-upload-limit). |
| `LIBREFOLIO_BACKUP_RECIPIENTS` | _not set_ | One or two age public keys (`age1…`, as `backup keygen` or `age-keygen` prints them), comma-separated: two only while a key is being changed. Not a secret. Set, `backup create --sealed` makes a [sealed](backup_sealed.md#sealed) backup: a `.tar` whose password only the matching private keys open, never with the instance key. A value LibreFolio cannot use (not an `age1…` key, more than two, the same one twice) does not stop the server: the log has an error, and the **Security** tab of Settings › Administration reports it (`backup.recipients`). Read from the environment only. |
| `LIBREFOLIO_STORAGE_LIMIT_MB` | _not set_ | Leave it unset on an install of your own: you set the limit in the space bar of the **Files** page. The space the instance may take, in megabytes; `0` is no limit. Set, it wins over the **Space limit (MB)** setting, whatever an administrator saved before, and locks it: the field in the space bar is greyed out and a save is refused. Not set: the setting decides, `0` until an administrator saves another value. A value that is not a whole number is ignored, and the setting speaks. It is a line drawn on the bar, not a quota: LibreFolio shows a warning when the data passes it, and deletes nothing. Read from the environment only. See [The Space Bar](backup_restore.md#space-used). |
| `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS` | `60` | The first pause of a price provider that answers «too many requests» (HTTP 429): no request reaches it until the pause ends, and each refusal in a row doubles the next one. A whole number of seconds from `0` to `86400`; `0` turns the pauses off, as before release 1.3. On by default, by developer decision 34: an exception to the rule that a new option leaves an install as it was. A value that cannot be used does not stop the server either: the log has an error, and both defaults apply. See [Provider Pauses](settings.md#provider-pauses). |
| `LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS` | `3600` | The longest pause the doubling reaches: a whole number of seconds from `1` to `86400`, not below the first pause while the pauses are on. A provider's `Retry-After` may still ask for more, up to one day. A value that cannot be used does not stop the server either: the log has an error, and both defaults apply. See [Provider Pauses](settings.md#provider-pauses). |
| `LIBREFOLIO_PROBE_RATE_LIMIT` | `30` | How many times a minute one user may test a price provider's settings (**Test Configuration** in the asset form; **Ask Provider** counts too), which may call the provider; past it, the form tells the user when to try again. A whole number from `0` to `10000`; `0` turns the limit off, for a test instance only (`./dev.py server --test` does it), and the log has a warning at every start. Read at every test: a change applies without a restart. A value that cannot be used does not stop the server: the log has an error, and `30` applies. |
| `LIBREFOLIO_BRIM_PREWARM` | `false` (`true` in test mode) | Optional. `true` makes the broker-import workers ready at startup, with the import plugins loaded: the first broker import after a start is then about 4 seconds faster, for about 80 MB of memory held from the start and about 1.4 seconds of CPU at every start. Off by default, by decision N56: on a small cloud machine, that memory and CPU cost more than the seconds they save. `true` or `false`; `1`/`0`, `yes`/`no` and `on`/`off` work too, in any case. Any other value does not stop the server, unlike the main options: the log has a warning at startup, and it stays off. See [BRIM Architecture → Preload and warm-up](../developer/backend/brim/architecture.md#parse-pool-warm-up). |
| `LIBREFOLIO_SMTP_HOST` | _not set_: email off | Optional. The SMTP server that sends LibreFolio's emails, such as `smtp.example.com`. See [Email](email.md#variables). |
| `LIBREFOLIO_SMTP_TLS` | `starttls` | How the connection to the SMTP server is encrypted: `starttls`, `tls` or `none`. See [Encryption Modes](email.md#encryption-modes). |
| `LIBREFOLIO_SMTP_PORT` | `587` with `starttls`, `465` with `tls`, `25` with `none` | The port of the SMTP server, only when it is not the usual one of its encryption mode. See [Email](email.md#variables). |
| `LIBREFOLIO_SMTP_USER` | _not set_: no login | The login on the SMTP server, set together with `LIBREFOLIO_SMTP_PASSWORD` ([Secrets](configuration_secrets.md#secrets)). See [Email](email.md#variables). |
| `LIBREFOLIO_SMTP_FROM` | _not set_ | The sender of the emails, required as soon as a server is set. See [Email](email.md#variables). |
| `LIBREFOLIO_SMTP_REPLY_TO` | _not set_: replies go to the sender | Where replies to LibreFolio's emails go. See [Email](email.md#variables). |
| `LIBREFOLIO_SMTP_MAX_PER_HOUR` | `50` | How many emails the instance may send in an hour, per server process. See [Email](email.md#variables). |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` | `20` | How many registration emails one client address may trigger in an hour, per server process: a whole number, at least 1. One count for the registrations, **Send the link again** and **Forgot password?**. Past it, a new account is created and waits, and its email is held. See [Limits on Activation and Password-Reset Emails](email_flows.md#activation-limits). |

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
    | `RISK_SIMULATION_IDLE_TIMEOUT_SECONDS`, `RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS` | `600` | Idle workers stop after this many seconds and restart with the next job; `0` keeps them running. |

---

## 💻 Parameters Set by the Tools

`./dev.py` and Docker Compose set these for you: change them only if you know why.

| Variable | Default | What it does |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Address `./dev.py server` listens on; `127.0.0.1` accepts local connections only. Docker Compose always uses `0.0.0.0`. |
| `LIBREFOLIO_LOG_LEVEL` | — | Replaces `LOG_LEVEL` when set; `./dev.py server --debug` and `./dev.py server --test` set it to `DEBUG`. |
| `LIBREFOLIO_API_DOCS` | — | Set to `1` by `./dev.py server --debug`, which turns on the API's documentation pages (the variable of the same name, above). |
| `LIBREFOLIO_NO_SCHEDULER` | — | Any non-empty value, `0` included, turns the scheduled price and FX syncs off. Set by `./dev.py server --no-scheduler`. |
| `LIBREFOLIO_TEST_MODE` | — | `1`, `true` or `yes`, in any case, switches to the test data folder. For LibreFolio's own test runs only: `./dev.py server --test` and the test runners set it, and `./dev.py server` turns it off. A server started without `./dev.py`, such as with `uvicorn` directly or from a service unit, takes it from its environment. On an instance in use, outside the test runner, the [startup checks](configuration_security.md#startup-checks) report it as an error. |
| `LIBREFOLIO_TEST_DATA_DIR` | `./backend/data/test` | Folder of the test data; it may not overlap the production one. |

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

For a [plugin setting](configuration_secrets.md#plugin-settings), from the highest priority to the lowest: its variable
(`LIBREFOLIO_PLUGIN_…` before the plugin's older name for it, each before its `_FILE` form), the
value saved inside LibreFolio, then the plugin's default. A variable with a wrong value still wins,
and leaves the plugin not configured. A personal setting has no variable: the user's saved value,
then the default.

---

## 📂 Where the Data Goes

- **Production**: `backend/data/prod/`, or `LIBREFOLIO_DATA_DIR`. It holds the database
  (`sqlite/app.db`), `custom-uploads/`, `broker_reports/`, `logs/` and, once LibreFolio has created
  the [instance key](configuration_secrets.md#instance-key), `secrets/`.
- **Test**: `backend/data/test/`, or `LIBREFOLIO_TEST_DATA_DIR`. Same layout, kept apart.

[Filesystem Structure](filesystem.md) details each folder and how to back it up.

---

## 🔗 Related

- 📄 **[Configuration: Secrets and Plugin Settings](configuration_secrets.md)** — Secrets, Plugin Settings
- 📄 **[Configuration: Checks and Protections](configuration_security.md)** — Startup Checks, Browser Protections, Stopping the Server
- 📄 **[Configuration: Accounts and Asset Search](configuration_accounts.md)** — Accounts and Sign-ups, The Order of the Price Providers in the Search, Optional: Web Search for New Assets
- ⚙️ **[Global Settings](settings.md)** — Options changed from inside the app
- 🐳 **[Advanced Docker](docker_advanced.md)** — Compose file, volumes, user and group IDs
- 🧑‍💻 For developers: **[Settings System](../developer/architecture/settings.md)** — How these
  values are loaded
- 🔒 For developers: **[Security Architecture](../developer/architecture/security.md)** — Secrets,
  the instance key, the startup checks and the limit on failed sign-ins
- 🧩 For developers: **[Plugin Settings](../developer/architecture/patterns/plugin_settings.md)** —
  How plugins declare settings, and how secrets are protected
