# phase-00-web-search-ddgs — link-finder transport → ddgs

> Archived from `04_webSearchEngine/` on 2026-09-02. Both plans archived: the executed
> ddgs plan AND the deferred SearXNG one (user decision 2026-09-02: ddgs is sufficient and
> lighter — SearXNG will not be revisited unless search needs fundamentally outgrow a
> pip library).

The fragile hand-rolled DuckDuckGo HTML scraper was replaced by the `ddgs` metasearch
library (multi-engine, zero infra). Verified live: real Borsa Italiana URLs resolved for
queries that previously returned empty (the 202-anomaly transport failure).

| File | Description | Status |
|---|---|---|
| `plan-phase00DdgsMetasearchEngine.prompt.md` | ddgs metasearch plan (Steps 1–6) | ✅ 24 tests green |
| `plan-phase00SearxngMetasearch.prompt.md` | SearXNG self-hosted adapter | 🚫 Not needed — ddgs suffices |

**Known follow-up (noted in the ddgs plan's progress log):** under `backend="auto"` the
per-call backend rotation makes one BTP query engine-lottery dependent; ISIN search is
reliable. Candidate fixes (pin `_DDGS_BACKEND`, post-rank `/scheda/`) are open for a
future pass.
