# Plan — SearXNG Metasearch Adapter for the Web Link-Finder

> **STATUS: DEFERRED — Fase B (2026-07-28), confermato 2026-09-02.** Il piano ddgs
> (`../phases/phase-00-web-search-ddgs/plan-phase00DdgsMetasearchEngine.prompt.md`) è stato
> eseguito e archiviato: `DdgsEngine` vive in `backend/app/services/web_link_finder.py` e
> `ddgs==9.14.4` è in `requirements.txt`. Questo piano SearXNG resta come upgrade opzionale
> per power-user, da riaprire **solo se** l'uso del cerca supera ddgs (vedi
> `../../../../TODO_FUTURI.md`). Quando riaperto, la catena engine diventa `[searxng → ddgs]`.

> Replace the fragile, hand-rolled DuckDuckGo HTML scraper behind the asset
> web link-finder with a pluggable **SearXNG** metasearch adapter. SearXNG is a
> self-hosted, anonymized, multi-engine metasearch **service** (not a pip library):
> it aggregates Google/Bing/Brave/DDG/Startpage/… and returns unified JSON, so a
> single upstream engine can no longer rate-limit us into an empty result.
>
> **Scope decision = `code + deploy + docs`** — backend adapter, docker-compose
> service, dev.py lifecycle helper, dev-guide documentation. No new Python
> dependency (adapter uses the existing `httpx`). SearXNG runs as its own container.

Related history:
- Broker Import Recovery (origin of the link-finder + BI meta-search idea):
  `../phases/phase-00-broker-import-recovery/plan-phase00BrokerImportRecovery.prompt.md`
  (§ "Meta-search transport: prefer an official search API behind a small pluggable interface")
- Link-finder integration lives in `backend/app/services/web_link_finder.py`
  (already a pluggable `_SearchEngine` Protocol + `_build_engine()` selector) and is
  wired into `backend/app/services/asset_source.py` (`_augment_with_link_finder`).
- AI ideas note (web-search options — Playwright/Firecrawl, superseded here by SearXNG):
  `../../Ai_ideas/brainstorming_ai_features.md` § B.

---

## 0. Context & motivation

The BI asset link-finder issues a `"{query} site:borsaitaliana.it"` search to a search
engine and resolves the winning page. The current engine (`DuckDuckGoEngine`) scrapes
`https://html.duckduckgo.com/html/`. During a normal import session it fires bursts of
queries (rich + base × providers × repeated user searches), and DDG's bot-detection
responds with **HTTP 202 + an "anomaly" page + 0 results**. Two of our own behaviours
make this worse:

1. `resp.raise_for_status()` does **not** raise on 202 (it is 2xx) → the anomaly page is
   parsed, yields 0 anchors, and returns `[]` **silently** (no warning).
2. The empty result is **cached for 15 minutes** (`_CACHE_TTL_SECONDS`) → a rate-limited
   "0" sticks even after DDG recovers.

**Evidence (live probe, 2026-07-28)** — this is NOT an indexing problem:

| Query (as backend sends) | DDG HTML endpoint |
| --- | --- |
| `BTP 1/12/2026 1.25% site:borsaitaliana.it` | **200 OK, 10 results, correct BI page #1** |
| `"BTP 1/12/2026 1.25%" site:borsaitaliana.it` (quoted) | **202, "anomaly", 0 results** |
| `BTP 01/08/31 0,60% site:borsaitaliana.it` (isolated) | 200 OK, 5 results (all IT0005436693 tabs) |

**Decision (user):** do **not** invest in fixing the DDG scraper — replace the transport
with SearXNG. Keep DDG only as an unmaintained zero-config fallback.

---

## 1. Locked decisions

| # | Decision | Rationale |
| --- | --- | --- |
| D1 | Add a **`SearxngEngine`** behind the existing `_SearchEngine` Protocol | Pure transport swap; call sites (`find_candidate_urls`, `_augment_with_link_finder`, `site:` scoping, dedup, ISIN filter) are **unchanged** |
| D2 | **No new pip dependency** — adapter uses `httpx` (already present) | SearXNG is a Flask/uwsgi **service**, not a library; `pip install searxng` would drag a huge conflicting tree + settings.yml. **Do NOT add to Pipfile.** |
| D3 | **DDG kept as-is as the zero-config fallback** — still supported, we just don't over-invest in it ("non super-OP") | Bare `pipenv` boot without Docker must still work (degrades to best-effort) |
| D4 | Shipped **default engine = `duckduckgo` ("safe")** | Boot never depends on Docker. Our compose + `dev.py` explicitly set `ENGINE=searxng` when SearXNG is up |
| D5 | SearXNG runs as a **sidecar container**, config centralized in **one** compose service definition, reused by prod (full stack) and dev (single service via `dev.py`) | One source of truth; compose reconciles state (start/stop/kill) better than raw `docker run` |
| D6 | Prod compose: SearXNG **internal by default** (no host port needed — LibreFolio reaches it over the compose network); publishing a port is **harmless** (metasearch, no secrets) if a user wants it. Dev **publishes** `127.0.0.1:8888` because the pipenv backend runs on the host | Minimal by default, but no security framing — exposing it is fine |
| D7 | **No Redis** — disable the SearXNG `limiter` (only needed for public anti-abuse) | Minimum footprint = 1 extra container |
| D8 | Neither LibreFolio boot **nor** `dev.py` **wait** for SearXNG readiness | Availability is decided **per-search at runtime** (D10), not frozen at boot — "nothing guarantees it's still up later either". Compose uses `depends_on: service_started` for **ordering only**, never `service_healthy` |
| D9 | `dev.py server run` starts/stops SearXNG **best-effort, non-blocking**; failure = only **start/pull error** | Docker missing / pull fails / command errors → **warning print + continue** (runtime falls back to DDG). Does NOT probe online status |
| D10 | **Runtime engine resolution with a fallback chain**, evaluated every search | Prefer SearXNG; on **transport failure** fall back to DDG; a **short down-cache** (~30–60 s) skips a known-down instance during bursts but self-heals when it reappears/disappears |

---

## 2. Architecture

```
asset_source._augment_with_link_finder(...)
   └── web_link_finder.find_candidate_urls(query, ["borsaitaliana.it"])
          ├── scoped = f"{query} site:borsaitaliana.it"          # unchanged
          └── chain = _build_engine_chain()   # ordered, resolved PER CALL
                 primary → fallback
                 ├── ENGINE=searxng  → [SearxngEngine, DuckDuckGoEngine]
                 ├── ENGINE=duckduckgo → [DuckDuckGoEngine]
                 └── ENGINE=apikey   → [ApiKeyEngine]
             for engine in chain:
                 try: urls = engine.search(...)        # 200 (even empty) → accept, stop
                 except TransportError: continue        # conn-refused/timeout/5xx/403 → next
```

The engine boundary is a plain `search(query, *, timeout, max_results) -> list[str]`.
SearXNG receives the same `site:` operator and passes it to upstream engines, so **all
downstream logic (dedup, `_matches_allowed`, ISIN filter, two-stage rich→base fallback)
is untouched**.

**Runtime resolution (D10).** The chain is rebuilt on **every** `find_candidate_urls` call
(the selector is already per-call, not cached at boot), so it **self-heals**: if SearXNG was
down at boot but comes up later, the next search uses it; if it dies, the search falls through
to DDG. A legit `200 + empty` from SearXNG is **accepted** (it did its job); only a **transport
failure** (`httpx.ConnectError`/`TimeoutException`/5xx/`403 json-disabled`) triggers fall-through.
A short **down-cache** (~30–60 s, keyed by engine+url) marks a just-failed SearXNG as skip-for-now
so a burst of queries doesn't each pay the connect-timeout, while still re-probing after the TTL.

### New env vars
| Var | Values / example | Notes |
| --- | --- | --- |
| `LIBREFOLIO_WEB_LINK_FINDER_ENGINE` | `duckduckgo` (default) \| `searxng` \| `apikey` | already exists; `searxng` builds the `[searxng → ddg]` runtime chain (D10) |
| `LIBREFOLIO_WEB_LINK_FINDER_SEARXNG_URL` | prod `http://searxng:8080` / dev `http://127.0.0.1:8888` | **NEW**; if `ENGINE=searxng` and unset → warn + chain = `[ddg]` only |
| (existing) `..._ENABLED`, `..._MAX`, `..._TIMEOUT` | — | unchanged |

---

## 3. Deliverables (step-by-step)

### Step 1 — Backend: SearXNG adapter + resilient runtime chain ⏳

**1a — `SearxngEngine`**
- [ ] Add `class SearxngEngine(_SearchEngine)` to `web_link_finder.py`:
  - `GET {base_url}/search` params `{"q": query, "format": "json", "categories": "general"}`,
    `httpx.Client(timeout=..., headers={User-Agent}, follow_redirects=True)`.
  - `resp.raise_for_status()`; parse `resp.json()["results"]`; return `[r["url"] for r in results if r.get("url")]`
    capped at `max_results * _OVER_FETCH_FACTOR`.
  - A **200 with empty `results`** is a **legit empty** → return `[]` (do NOT treat as failure).
  - Raise a **transport error** (do not swallow) on: `httpx.ConnectError`, `httpx.TimeoutException`, 5xx,
    and **403** (json disabled — log "SearXNG JSON format off: settings.yml → formats: [html, json]").

**1b — Resilient runtime chain (D10)**
- [ ] Replace `_build_engine()` with `_build_engine_chain() -> list[_SearchEngine]`:
  - `ENGINE=searxng` + URL set → `[SearxngEngine, DuckDuckGoEngine]`; URL unset → warn + `[DuckDuckGoEngine]`.
  - `ENGINE=duckduckgo`/unknown → `[DuckDuckGoEngine]`; `ENGINE=apikey` + key → `[ApiKeyEngine]`.
- [ ] In `find_candidate_urls`, iterate the chain **rebuilt every call** (self-heals): first engine whose
  `search()` **returns** (200, even empty) wins; a **transport error** logs once and falls through to the next.
- [ ] Short **availability down-cache** (`_SEARXNG_DOWN_TTL` ~30–60 s, keyed by base_url): on transport failure
  mark down → subsequent burst queries skip SearXNG straight to DDG; re-probe after TTL (self-heals up/down).
- [ ] **Self-heal guard on the result cache**: if the **whole chain transport-failed** (no engine reachable),
  return `[]` **without** writing the 15-min result cache — otherwise a recovery moments later would be blocked.
  Only cache results from an engine that actually responded (200).
- [ ] Do not otherwise touch the DDG path (we are replacing, not fixing it).
- [ ] Lint+format (ruff+black, line-length 300); `ast.parse` syntax check.

### Step 2 — SearXNG runtime config ⏳
- [ ] Ship `deploy/searxng/settings.yml`:
  ```yaml
  use_default_settings: true
  server:
    secret_key: "CHANGE_ME_or_generated_by_entrypoint"
    limiter: false            # no Redis
    bind_address: "0.0.0.0"
    port: 8080
  search:
    formats:
      - html
      - json                  # REQUIRED for the API, else 403
  ```
- [ ] Decide secret handling: entrypoint-generated vs `.env` (`SEARXNG_SECRET`). Prefer generated
  on first run to avoid a shipped default secret.
- [ ] (Optional) trim `engines:` to a stable subset if default set is noisy for `site:` queries.

### Step 3 — docker-compose service (prod, internal-only) ⏳
- [ ] Add `searxng` service to `docker-compose.yml`:
  ```yaml
  searxng:
    image: searxng/searxng:latest
    container_name: librefolio-searxng
    restart: unless-stopped
    volumes:
      - ./deploy/searxng:/etc/searxng:ro
    # NO ports: — internal only (reachable as http://searxng:8080 on the compose network)
    healthcheck:                       # TBD exact command for the searxng image
      test: ["CMD", "wget", "-qO-", "http://localhost:8080/"]
      interval: 30s
      timeout: 10s
      retries: 3
  ```
- [ ] Extend the `librefolio` service:
  ```yaml
  environment:
    - LIBREFOLIO_WEB_LINK_FINDER_ENGINE=searxng
    - LIBREFOLIO_WEB_LINK_FINDER_SEARXNG_URL=http://searxng:8080
  depends_on:
    searxng:
      condition: service_started       # ordering only, NOT service_healthy
  ```
- [ ] Mirror in `docker-compose.prod.yml` if it diverges.
- [ ] Add a dev override `docker-compose.searxng-dev.yml` (host-reachable for the pipenv backend):
  ```yaml
  services:
    searxng:
      ports:
        - "127.0.0.1:8888:8080"
  ```

### Step 4 — dev.py lifecycle (best-effort, non-blocking) ⏳
- [ ] In `server run` (pipenv path), before launching uvicorn:
  - Pre-cleanup orphan: `docker compose -p librefolio-dev ... rm -sf searxng` (idempotent).
  - Start: `docker compose -p librefolio-dev -f docker-compose.yml -f docker-compose.searxng-dev.yml up -d searxng`.
  - **Failure = only** Docker missing / pull error / command non-zero → **print warning, continue** (chain stays `[ddg]`).
  - **Do NOT wait for readiness / do NOT health-probe.** If the start command **succeeded** (container created),
    inject into the uvicorn subprocess env: `LIBREFOLIO_WEB_LINK_FINDER_ENGINE=searxng`,
    `..._SEARXNG_URL=http://127.0.0.1:8888`. The runtime chain (D10) uses DDG until SearXNG answers, then self-heals.
- [ ] Teardown: register `SIGINT`/`SIGTERM`/`atexit` → `docker compose -p librefolio-dev ... stop searxng`
  (reuse next time) or `down` (full clean). Choose `stop` for faster iteration.
- [ ] Note the first-run image pull (~200 MB) — print a one-time "pulling SearXNG image…".
- [ ] Optional convenience: `dev.py searxng up|down|status` subcommands sharing the same helper.

### Step 5 — Documentation (dev guide) ⏳
- [ ] New page `mkdocs_src/.../dev-guide/web-search-linkfinder.md`: the link-finder subsystem —
  purpose, `site:` scoping, two-stage rich→base query, the `_SearchEngine` Protocol, the three
  engines (DDG legacy/fallback, **SearXNG** default, apikey stub), env vars, the 202-anomaly
  history (why we moved off raw DDG), SearXNG deploy (sidecar + settings.yml + no-Redis).
- [ ] Add the subsystem to the **dev-guide overview/architecture map**.
- [ ] Update the "how to write an asset provider" guide to mention the link-finder fallback hook.
- [ ] Update the Borsa Italiana provider guide (search resolution now routes via SearXNG).
- [ ] `.env.example`: document `LIBREFOLIO_WEB_LINK_FINDER_ENGINE` + `..._SEARXNG_URL`.
- [ ] (Optional, evergreen) a `/websearch-plugin`-style skill mirroring `/brim-plugin` — where to
  look for engine/config updates and the invariant rules.

### Step 6 — Tests ⏳
- [ ] Unit: `SearxngEngine.search` parses a mocked JSON payload → list of URLs (respx/monkeypatch httpx).
- [ ] Unit: `SearxngEngine` raises transport error on ConnectError/timeout/5xx/403; returns `[]` on 200-empty.
- [ ] Unit: `_build_engine_chain()` matrix (`searxng`+URL → `[searxng, ddg]`; `searxng` no URL → `[ddg]`+warn;
  `duckduckgo`/unknown → `[ddg]`; `apikey`+key → `[apikey]`).
- [ ] Integration (fallback): `ENGINE=searxng`, SearXNG unreachable, DDG mocked with URLs → chain returns DDG's URLs.
- [ ] Integration (self-heal): whole chain transport-fails → returns `[]` **and does not** poison the 15-min cache
  (a subsequent call with SearXNG reachable succeeds).
- [ ] Integration (down-cache): two rapid failing calls → SearXNG probed once, second skips to DDG within TTL.
- [ ] Re-run existing `test_web_link_finder.py` (must stay green — behaviour above the engine is unchanged).

---

## 4. Risks / open questions
- **SearXNG healthcheck command** for the official image is TBD (does it expose `/healthz`? else GET `/`). Verify.
- **Secret key**: avoid shipping a fixed `secret_key`; generate on first run or require `SEARXNG_SECRET` in `.env`.
- **Result quality vs DDG**: SearXNG default engine set may rank differently; validate the BI `site:` cases
  (`LU2178929613`, the BTPs) return the right page #1 after switch.
- **First-run latency** in dev (image pull) — acceptable, warn once.
- **`docker compose` v2 syntax** assumed (`docker compose`, not `docker-compose`). Confirm dev.py already uses v2.
- **prod.yml drift**: ensure the searxng service + env land in whichever compose file(s) prod uses.

---

## 5. Progress log
> Update after EVERY step (✅ + date + "Note implementazione"; detours → "⚠️ Fuori pista").

- 2026-07-28 — Plan created. Design converged with user: SearXNG sidecar, adapter behind existing
  Protocol, DDG kept as zero-config fallback (default), dev lifecycle via `docker compose up -d searxng`
  (single service, centralized config, best-effort/non-blocking), no Redis, no pipenv dep, internal-only
  in prod.
- 2026-07-28 (refinement) — Added **D10 runtime engine chain** (`[searxng → ddg]`, per-call, self-healing,
  transport-error vs legit-empty distinction, ~30–60 s down-cache, no-poison result cache on total failure).
  `dev.py` failure = only start/pull error (**no readiness wait / no health probe**). Dev **publishes** the
  localhost SearXNG port (harmless — metasearch, no secrets). Awaiting go-ahead to execute Step 1.
