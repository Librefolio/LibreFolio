# phase-00-web-search-ddgs — link-finder transport → ddgs

> Archived from `04_webSearchEngine/` on 2026-09-02 (only the executed plan; the deferred
> SearXNG plan stayed behind at `../../04_webSearchEngine/plan-phase00SearxngMetasearch.prompt.md`).

The fragile hand-rolled DuckDuckGo HTML scraper was replaced by the `ddgs` metasearch
library (multi-engine, zero infra). Verified live: real Borsa Italiana URLs resolved for
queries that previously returned empty (the 202-anomaly transport failure).

| File | Description | Status |
|---|---|---|
| `plan-phase00DdgsMetasearchEngine.prompt.md` | ddgs metasearch plan (Steps 1–6) | ✅ 24 tests green |

**Known follow-up (noted in the plan's progress log):** under `backend="auto"` the per-call
backend rotation makes one BTP query engine-lottery dependent; ISIN search is reliable.
Candidate fixes (pin `_DDGS_BACKEND`, post-rank `/scheda/`) are open for a future pass.
