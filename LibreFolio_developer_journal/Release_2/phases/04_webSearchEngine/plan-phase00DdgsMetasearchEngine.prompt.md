# Plan — `ddgs` Metasearch Engine for the Web Link-Finder

> Replace the fragile, hand-rolled DuckDuckGo HTML scraper behind the asset web
> link-finder with the **`ddgs`** library (the renamed, actively-maintained
> `duckduckgo_search`). `ddgs` is a **pip-installable metasearch library** that
> aggregates 10 text backends (bing, brave, duckduckgo, google, mojeek, startpage,
> yandex, yahoo, wikipedia, grokipedia) behind one sync `text()` call, so a single
> upstream engine can no longer rate-limit us into an empty result — **without any new
> infrastructure** (no container, no Redis).
>
> **Scope decision = `code + docs`** — one new Python dependency (`ddgs`, base install),
> a new pluggable `DdgsEngine` in `web_link_finder.py`, retirement of the raw DDG
> scraper, tests, and dev-guide documentation. No docker/compose changes.

Related history:
- Broker Import Recovery (origin of the link-finder + BI meta-search idea):
  `../03_brokerImportRecovery/plan-phase00BrokerImportRecovery.prompt.md` (section **G1**).
- **SearXNG (Fase B, deferred)**: `plan-phase00SearxngMetasearch.prompt.md` — the optional
  self-hosted power-user upgrade, revisited only if search usage outgrows `ddgs`.
- Future backlog: `../../todo_futuri.md`.

---

## Why (root cause recap)

The current default engine `DuckDuckGoEngine` scrapes `https://html.duckduckgo.com/html/`
directly. Empirically proven (`/tmp/libreFolio_ddg_diff.log`): during query bursts DDG's
bot-detection returns **HTTP 202 + an "anomaly" page + 0 results** to the backend (the same
query in a browser returns the correct page — trusted human session). Two compounding bugs
make it silent: `resp.raise_for_status()` does not fire on 202 (it is 2xx) → 0 anchors
parsed → `[]`; then the empty result is cached for 15 minutes. A browser works, the backend
does not. **User decision: replace, don't fix.**

`ddgs` sidesteps this: it is maintained, rotates/aggregates multiple engines (`backend="auto"`),
and handles anti-bot quirks upstream. DDG remains *one* of its backends, so we lose no
coverage while gaining bing/brave/google/startpage/… for free.

## `ddgs` facts (PyPI, verified)

- Install: `pip install -U ddgs` (base install = lightweight; extras `[api]`, `[mcp]`, `[dht]`
  exist — we use **base only**; `[dht]` P2P shared-cache drags heavy git deps → skip).
- API (**sync**):
  ```python
  from ddgs import DDGS
  results = DDGS(proxy=None, timeout=…, verify=True).text(
      query, region="wt-wt", safesearch="moderate", timelimit=None,
      max_results=10, page=1, backend="auto",
  )  # -> list[dict] with keys: title, href, body
  ```
- URL extraction for our engine = `[r["href"] for r in results if r.get("href")]`.
- 10 text backends; `backend="auto"` rotates/aggregates them.
- Proxy: http/https/socks5 (kept as a future config knob; not wired now).
- Region: default `us-en` biases toward US pages → we default the engine to **`wt-wt`**
  (worldwide, no region bias) so Italian BI pages are not down-ranked; env-overridable.

## Fit with the existing module

`web_link_finder.py` already exposes a pluggable **`_SearchEngine` Protocol** whose
`search(query, *, timeout, max_results) -> list[str]` is **synchronous** and is invoked from
`find_candidate_urls` via `await asyncio.to_thread(engine.search, …)`. `ddgs` is sync → it
drops straight into that seam. Optional third-party imports are already guarded by
`_WEB_DEPS_OK` (httpx/bs4); we add an analogous guard for `ddgs`.

---

## Locked decisions

- **D1 — `ddgs` becomes the default engine.** `_build_engine()` default returns `DdgsEngine`.
- **D2 — Retire the raw DDG scraper.** Remove `DuckDuckGoEngine` + its private helper
  `_unwrap_ddg` (only it used the `/l/?uddg=` redirect unwrap). The httpx/bs4 deps stay in the
  Pipfile — still used elsewhere (BI/justETF scrapers), just not by the link-finder anymore.
- **D3 — Keep the engine-selector seam.** `LIBREFOLIO_WEB_LINK_FINDER_ENGINE` still selects
  `ddgs` (default) | `apikey` (existing stub, Brave/Bing/SerpAPI drop-in later). The `searxng`
  value is reserved for **Fase B** (documented, not implemented here).
- **D4 — Best-effort, never fatal.** Transport/library errors → the engine raises, the chain
  falls through, `find_candidate_urls` returns `[]`. A *legitimate* empty result (200, 0 hits)
  is accepted as `[]`. **Do not poison the 15-min result cache on a total transport failure**
  (self-heal guard — reuse the existing behaviour).
- **D5 — `region` configurable, default `wt-wt`; `backend` configurable, default `auto`.**
  New env: `LIBREFOLIO_WEB_LINK_FINDER_DDGS_REGION`, `LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND`.
- **D6 — pip dep is the user's action (VPN).** Add `ddgs` to the Pipfile, then **STOP** and ask
  the user to run `pipenv install ddgs`; resume with code+tests+docs once installed.

---

## Steps

### Step 1 — Pipfile ✅ (done)
- `ddgs = "*"` added to `[packages]`. **→ HANDOFF: user runs `pipenv install ddgs`.**

### Step 2 — `DdgsEngine` (backend)
- New `DdgsEngine(_SearchEngine)` in `web_link_finder.py`: defensive `try: from ddgs import DDGS`
  guarded by `_DDGS_OK`. `search()` = `DDGS(timeout=timeout).text(query, region=<env>,
  max_results=max_results, backend=<env>)` → `[r["href"] for r in results if r.get("href")]`.
  Classify library/transport errors so they **raise** (chain falls through); an empty list from a
  successful call → `[]`.
- If `ddgs` is not importable → engine unavailable → `find_candidate_urls` degrades to `[]`
  (matching the `_WEB_DEPS_OK` philosophy), logged once at debug.

### Step 3 — Retire the raw scraper + rewire the selector
- Delete `DuckDuckGoEngine` and `_unwrap_ddg`. `_build_engine()` → default `DdgsEngine`;
  `apikey` → existing stub; unknown/`searxng` → default (with a debug log noting Fase B).
- Keep `is_enabled()` (default on) and `find_candidate_urls()` unchanged in shape (it already
  goes through the engine + domain filter + TTL cache + self-heal).
- Update the module docstring env-var list (engine + new ddgs region/backend vars; drop the
  scraper-specific mentions).

### Step 4 — Tests (`test_web_link_finder.py`)
- Remove DDG-HTML-scraper-specific tests (`_unwrap_ddg`, anchor parsing). Add `DdgsEngine`
  tests with **mocked `ddgs.DDGS`** (patch `web_link_finder.DDGS`): href extraction, empty→[],
  library-error→raises (→ `find_candidate_urls` returns []), missing-lib guard. Keep the
  transport-agnostic tests (domain filter, dedup, cap, cache, disabled, subdomain,
  `_augment_with_link_finder` resolve/short-circuit/identifier-filter/rich-first hints) — they
  mock the engine, so they are unaffected.
- `_build_engine` default now → `DdgsEngine` (update any assertion).

### Step 5 — Docs
- **Dev-guide**: update `mkdocs_src/docs/developer/backend/assets/search_link_finder.md` — the
  L2 transport is now `ddgs` (multi-engine, pip, zero-infra); config env vars; SearXNG noted as
  a deferred Fase B upgrade. Update the architecture **overview** node
  (`developer/architecture/overview.md`: `WebSearch[Web Search Engine / DuckDuckGo]` →
  `ddgs (multi-engine)`). Provider guide note + `.env.example` if present.
- Keep it English; no build needed (repo convention).

### Step 6 — Validate
- `./dev.py lint --fix && ./dev.py format` on the touched Python (line-length 300).
- Targeted `pytest test_web_link_finder.py` + the BI funds/search suite (regression) → green.
- No `api sync` (link-finder is not an OpenAPI type). Propose commit msg to `/tmp/` (never commit).

---

## Risks / notes
- **Region bias**: `us-en` default in `ddgs` would down-rank Italian BI pages → we default to
  `wt-wt`. Watch result quality; expose region as env if a locale bias helps a provider.
- **Lock churn / risk agent**: a parallel agent previously restored `Pipfile.lock`. After the
  user installs `ddgs`, confirm the lock actually pins it before running tests.
- **Fase B coexistence**: the selector reserves `searxng`; when Fase B lands, the runtime chain
  becomes `[searxng → ddgs]` with ddgs as the always-present in-process fallback.

## Progress log
- 2026-07-28 — Plan created. Pipfile `ddgs` added (Step 1). Awaiting user `pipenv install ddgs`
  before Steps 2–6.
- 2026-07-28 — User ran `pipenv install ddgs` (ddgs 9.14.4, lock updated). **Steps 2–6 done**:
  - **Step 2/3** — `DdgsEngine` added; `_unwrap_ddg` + `DuckDuckGoEngine` retired; httpx/bs4 import
    guard swapped for a `ddgs`/`_DDGS_OK` guard; `_build_engine()` default → `DdgsEngine`
    (region `wt-wt`, backend `auto`), `apikey` kept, `searxng` reserved (Fase B). Module docstring
    env list updated (`web_link_finder.py`).
  - **Step 4** — `test_web_link_finder.py`: added `DdgsEngine` parse/empty/error tests + selector
    matrix (default ddgs, region/backend override, apikey-without-key). **24 passed**.
  - **Step 5** — Docs: `search_link_finder.md` (transport = ddgs + new *Transport history* section
    explaining the 202-anomaly + SearXNG Fase B), overview map node (`ddgs metasearch`),
    `provider_borsa_italiana.md`, `architecture.md`, and `.env.example` env block.
  - **Step 6** — ruff+black clean (line-length 300); live end-to-end probe confirmed real BI URLs
    for cases that previously returned empty (`BTP 01/08/31 0,60%` → correct `IT0005436693-MOTX`).
  - **> ⚠️ Fuori pista**: live probes show `BTP 1/12/2026 1.25%` is **engine-lottery dependent**
    under `backend="auto"`: one call ranks the correct scheda `IT0005210650-MOTX` ("Btp Tf 1.25%
    Dc26", the exact bond) at **#1**, while a moments-later call returns only generic MOT
    `lista.html` pages (one weak engine even HTML-entity-mangles the query string, `&ord=`→`∨`).
    Root cause = per-call backend-rotation variance, **not** a transport failure. Future fix
    options: pin `_DDGS_BACKEND` to a reliable set (e.g. `google,bing,duckduckgo`), pass a `scheda`
    path_hint, or post-rank `/scheda/` over `/lista.html`. ISIN search already resolves reliably.
