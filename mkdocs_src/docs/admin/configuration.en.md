# 📝 Configuration

Startup options live in a `.env` file: ports, the data folder, logging, login sessions and a few
optional features. It sits at the root of the project, or next to `docker-compose.yml` with
Docker. The options you change from inside the app are [Global Settings](settings.md) instead.

---

## 🔧 Create the `.env` File

In the project folder, copy the sample file, then edit the values you need:

```bash
cp .env.example .env
```

With the pre-built Docker image, the [Docker installation](../user/installation.md) guide downloads
the same sample as `.env`.

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
| `JWT_SECRET` | _not set_ | Key that signs login sessions. Not set: a new key at every start, so everyone logs in again after a restart. See [Keep users signed in](index.md#session-persistence). |
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
| `LIBREFOLIO_LOG_LEVEL` | — | Replaces `LOG_LEVEL` when set; `./dev.py server --debug` sets it to `DEBUG`. |
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
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | _empty_ | Key for the `apikey` engine. |

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
  (`sqlite/app.db`), `custom-uploads/`, `broker_reports/` and `logs/`.
- **Test**: `backend/data/test/`, or `LIBREFOLIO_TEST_DATA_DIR`. Same layout, kept apart.

[Filesystem Structure](filesystem.md) details each folder and how to back it up.

---

## 🔗 Related

- ⚙️ **[Global Settings](settings.md)** — Options changed from inside the app
- 🐳 **[Advanced Docker](docker_advanced.md)** — Compose file, volumes, user and group IDs
- 🧑‍💻 For developers: **[Settings System](../developer/architecture/settings.md)** — How these
  values are loaded
