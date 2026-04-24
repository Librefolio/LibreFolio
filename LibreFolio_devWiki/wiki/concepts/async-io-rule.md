---
title: "Async I/O Rule (Event Loop Safety)"
category: concept
tags: [backend, async, uvicorn, fastapi, yfinance, performance]
related_features: [F-025, F-060]
related_problems: [problems/event-loop-blocking.md]
---

# Concept: Async I/O Rule

## Definition
In LibreFolio, every synchronous I/O call inside an `async def` FastAPI handler **must** be offloaded to a thread pool via `await asyncio.to_thread(...)`. Calling sync I/O directly stalls the entire uvicorn event loop.

## Why it matters
Uvicorn runs a **single event loop**. A blocking call (e.g. `requests.get()`, `yf.Ticker().info`) freezes the loop for its entire duration — stalling all concurrent requests including static file serving (JS chunks). A 1–5 second yfinance call makes the whole app feel unresponsive.

## The rule

```python
# ❌ WRONG — blocks the event loop
async def get_current_value(self, ...):
    info = yf.Ticker(identifier).info   # sync HTTP call!

# ✅ CORRECT — offloads to thread pool
async def get_current_value(self, ...):
    info = await asyncio.to_thread(lambda: yf.Ticker(identifier).info)
```

**Never call directly inside `async def`:**
- `requests.get()`, `urllib.urlopen()`, any `httplib`
- `yf.Ticker().info`, `yf.Search()`, `ticker.history()` — yfinance uses `requests` internally
- Slow filesystem ops (directory walk, large file reads) — fast `Path.exists()` is OK

**Complementary rule**: if an endpoint does only light sync I/O (`Path.exists()`, `FileResponse`), define it as `def` (not `async def`). FastAPI will run it in the thread pool automatically.

Examples of sync-safe endpoints: `frontend_catchall()`, `mkdocs_static()` in `main.py`.

## Where it applies
- All asset providers (`F-025`): `get_current_value()`, `get_history_value()`, `search()`
- Thread isolation (`F-060`) addresses this at the framework level — `_run_provider_in_thread()` wraps every provider call
- Any future endpoint that calls external HTTP APIs

## Source
`LibreFolio_developer_journal/knowledge_base/05_project_conventions.md` — "⚠️ Async I/O Rule" section

## Source files

| Role | Path |
|------|------|
| Thread isolation (provider calls) | `backend/app/services/asset_source.py` |
| FX service (async patterns) | `backend/app/services/fx.py` |
| Example: yfinance provider | `backend/app/services/asset_source_providers/yahoo_finance.py` |
| FastAPI main (sync endpoints) | `backend/app/main.py` |
