# LibreFolio — Todo Futuri (backlog)

Cross-phase future ideas not scheduled yet. Each item: date, short rationale, trigger to
revisit, and a link to the detailed plan if one exists.

---

## Web search / link-finder

### SearXNG metasearch — Fase B (deferred 2026-07-28)
- **What**: self-hosted, anonymized, multi-engine metasearch as an *opt-in primary* engine for
  the asset web link-finder, in front of the `ddgs` fallback (runtime chain `[searxng → ddgs]`).
- **Why deferred**: `ddgs` (pip, multi-engine, zero-infra) already solves the DDG 202-anomaly
  rate-limiting with no new infrastructure. SearXNG adds a container + config for marginal gain
  today.
- **Trigger to revisit**: search usage grows beyond what `ddgs` covers — heavier/aggregate
  querying, need for true upstream anonymization, or `ddgs` itself gets rate-limited/broken.
- **Detailed plan (already written)**:
  `Phase_0/04_webSearchEngine/plan-phase00SearxngMetasearch.prompt.md`
- **Deploy shape**: sidecar container (no Redis — limiter off), dev lifecycle via
  `dev.py` (`docker compose up -d searxng`), internal-only in prod. Best-effort (boot never
  waits for it). See the plan for D1–D10.

### External shared cache across uvicorn workers (study — 2026-07-28)
- **What**: the link-finder result cache (`web_link_finder._cache`) is an **in-process TTL dict**
  → not shared across uvicorn workers (each worker re-queries the same URL). Study whether an
  **external cache** (e.g. Redis/Valkey) shared by all workers is worth it.
- **Synergy with SearXNG**: if/when the SearXNG Fase B lands it may ship a Redis anyway →
  **reuse the same Redis** for this cross-worker cache instead of standing up a second store.
- **Scope of the study**: which caches benefit (link-finder results, FX rates, provider probes?),
  TTL/invalidation, single-worker dev vs multi-worker prod, and it MUST degrade gracefully to the
  in-process dict when no external cache is configured (optional dependency).
- **Trigger to revisit**: together with the SearXNG Fase B decision (shared Redis), or if prod
  moves to multi-worker uvicorn.

---

## Risk Analysis

### RQMC with explicit scrambling contract (low priority — 2026-07-28)
- **What**: re-evaluate randomized quasi-Monte Carlo only when the QuantLib Python
  binding exposes a complete scrambling path suitable for production.
- **Why deferred**: production now supports MC and QMC entirely in QuantLib. The
  previous SciPy RQMC path was removed, and its overloaded `seed` mixed random seed,
  Sobol offset and scrambling semantics.
- **Required contract**: separate scramble seed from `sobol_start_index`; never
  overload either field.
- **Required gate**: convergence across randomized replicates, QuantLib-only
  execution inside the `spawn` worker and no silent SciPy production fallback.
- **Trigger to revisit**: a newer QuantLib binding exposes the required scrambling
  primitives or a separately approved production engine is adopted.

### Dynamic scenario catalog (future — 2026-07-29)
- **What**: evolve the initial static, typed, startup-loaded built-in/host YAML
  catalog with file detection without restart, manual/hot reload, personal
  scenario CRUD, persistence of UI edits, YAML import/export, explicit built-in
  overrides and administrative diagnostics.
- **Why deferred**: G6 first needs a small deterministic contract with no database,
  watcher or generic form engine.
- **Trigger to revisit**: the static catalog and typed editors are stable in
  production and users need scenario lifecycle management.
- **Reference**:
  `Phase_0/02_riskfolioIntegration/plan-phase01Step6RiskFrontendInformationArchitecture.prompt.md`.

### Persistent historical-replay proxies (future — 2026-07-29)
- **What**: persist asset→proxy associations, optionally propose proxies only with
  explicit user confirmation, and reuse confirmed mappings in later replays.
- **Why deferred**: G6 deliberately keeps proxy choice explicit and ephemeral;
  automatic or silent substitution is forbidden.
- **Trigger to revisit**: repeated replay use demonstrates stable, auditable proxy
  mappings and the persistence UX has been designed.
