# 📝 Configuration

Startup options live in a `.env` file: ports, the data folder, logging, login sessions, secrets and a
few optional features. It sits at the root of the project, or next to `docker-compose.yml` with
Docker. The options you change from inside the app are [Global Settings](settings.md) instead.

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
| `PREVIEW_CACHE_MAX_MB` | `50` | Memory, in MB, of the image-preview cache in each server process. |

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

## 🔐 Secrets {: #secrets }

Three options are secrets: keep them as private as the database. Each one can be written in `.env` or
read from a file.

| Secret | From a file | What it is |
| --- | --- | --- |
| `JWT_SECRET` | `JWT_SECRET_FILE` | The key that signs login sessions, in the main options above. |
| `LIBREFOLIO_INSTANCE_KEY` | `LIBREFOLIO_INSTANCE_KEY_FILE` | The [instance key](#instance-key). Not set: LibreFolio creates one in the data directory. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` | The key of a paid search service, for the `apikey` engine of the web search below. Unlike the other two, a file that cannot give it does not stop the server: it only turns the web search off. |

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
- For `JWT_SECRET_FILE` and `LIBREFOLIO_INSTANCE_KEY_FILE`, a file that is missing, cannot be read, is
  empty or blank (only spaces and line breaks), is not UTF-8 text or is larger than 64 KiB stops the
  server at startup. The error names the variable and the path, never the secret.
- `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` is read only when a search uses the `apikey` engine. A
  file that cannot give the key does not stop the server: the search goes on without the web search,
  with a warning in the log (`web_link_finder: …; disabling`), and the providers' own search keeps
  working.
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

    `LIBREFOLIO_INSTANCE_KEY_FILE` and `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` work the same way.

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
      data without its `secrets/`.
    - If `instance.key` is there but damaged or out of reach, LibreFolio logs an error and never
      replaces it: see what to do in [Startup Checks](#startup-checks).
    - Setting `LIBREFOLIO_INSTANCE_KEY` where `secrets/instance.key` already exists changes the key. To
      move the key to the environment or to a Docker secret, use the content of `secrets/instance.key`
      as the value.

---

## 🩺 Startup Checks {: #startup-checks }

Right after its `Starting LibreFolio` line, the server checks its configuration. It changes nothing:
each finding is one line of the log, at its level, with the name of the check in `check`, such as
`platform.jwt_secret`.

| Level | The log says | What to do |
| --- | --- | --- |
| ℹ️ `info` | `JWT_SECRET is not set: every start makes a new session signing key, …` | Nothing, if signing everyone out at every restart is fine. Otherwise see [Keep users signed in](index.md#session-persistence). |
| ⚠️ `warning` | `The session signing key from JWT_SECRET is … characters long: use at least 32 random characters` (or `from JWT_SECRET_FILE (<path>)`) | Generate a longer key, as in [Keep users signed in](index.md#session-persistence), and put it where the line says. |
| ⚠️ `warning` | `Set both directly and through a *_FILE variable: …` | For each secret listed, keep only one of the two: the variable itself wins, the file is ignored. |
| ❌ `error` | `The instance key cannot be used: …`, ending with `cannot be reached (Permission denied)` or `cannot be read (…)` | The `secrets/` folder or `instance.key` belongs to another user, or its permissions keep LibreFolio out. Give both back to the user that runs LibreFolio (`chown`), then `chmod 700` on the folder and `chmod 600` on the file. Never replace the key with a new one. The server starts anyway. |
| ❌ `error` | `The instance key cannot be used: …`, ending with another reason, such as `is empty or blank` | `instance.key` is damaged: restore it from a backup, never replace it with a new key. The server starts anyway. |
| ⚠️ `warning` | `… is open to other users (…): the folder should be 0700 and the file 0600` | Restrict them: `chmod 700` on the `secrets/` folder, `chmod 600` on `instance.key`. |
| ⚠️ `warning` | `SESSION_COOKIE_SECURE=never: the session cookie is sent over plain HTTP too; prefer auto` | Go back to `auto` unless you really need `never`: see [HTTPS and reverse proxies](#session-cookie-secure). |
| ℹ️ `info` | `The log level is DEBUG: the log records operational detail; …` (or `TRACE`) | Go back to `INFO` once you are done troubleshooting. |

A secret you configured that cannot be used stops the start instead: a `JWT_SECRET_FILE` or a
`LIBREFOLIO_INSTANCE_KEY_FILE` that cannot give its secret (see [Secrets in Files](#secret-files)),
or an instance key of your own shorter than 32 characters. The error is in the server's console
output (`docker compose logs librefolio` with Docker): it names the variable, and the file when there
is one, never the secret. Fix it, then start
again.

---

## 💻 Parameters Set by the Tools

`./dev.py` and Docker Compose set these for you: change them only if you know why.

| Variable | Default | What it does |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Address `./dev.py server` listens on; `127.0.0.1` accepts local connections only. Docker Compose always uses `0.0.0.0`. |
| `LIBREFOLIO_LOG_LEVEL` | — | Replaces `LOG_LEVEL` when set; `./dev.py server --debug` sets it to `DEBUG`. |
| `LIBREFOLIO_NO_SCHEDULER` | — | Any non-empty value, `0` included, turns the scheduled price and FX syncs off. Set by `./dev.py server --no-scheduler`. |
| `LIBREFOLIO_TEST_MODE` | — | `1`, `true` or `yes` switches to the test data folder. Set by `./dev.py server --test` and the test runners. |
| `LIBREFOLIO_TEST_DATA_DIR` | `./backend/data/test` | Folder of the test data; it may not overlap the production one. |

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
| `LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT` | `6` | Time limit of one search, in seconds. |
| `LIBREFOLIO_WEB_LINK_FINDER_MAX` | `5` | Most links returned by one search. |
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
`HOST` and `LIBREFOLIO_DATA_DIR`. See [Advanced Docker](docker_advanced.md#resolution-priority).

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
  the instance key and the startup checks
