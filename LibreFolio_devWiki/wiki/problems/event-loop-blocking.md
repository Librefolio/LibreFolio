---
title: "Event Loop Blocking (sync I/O in async handlers)"
category: problem
status: resolved
date: 2025 (recurring risk)
tags: [backend, async, performance, uvicorn, yfinance]
related_features: [F-025, F-060]
related_concepts: [concepts/async-io-rule.md]
---

# Problem: Event Loop Blocking

## Symptom
The entire LibreFolio app becomes unresponsive — API requests queue up, static files (JS chunks) fail to load, the frontend hangs. Typically triggered by navigating to a page that fetches asset prices.

## Root Cause
A `requests`-based library (yfinance, or any sync HTTP library) called directly inside an `async def` FastAPI handler. Uvicorn uses a **single event loop** — one blocking call freezes all concurrent handlers for its entire duration (1–5 seconds for yfinance calls).

## Example that caused the problem
```python
# ❌ This was found in early provider implementations
async def get_current_value(self, identifier: str, ...):
    ticker = yf.Ticker(identifier)
    info = ticker.info  # blocks event loop for 1-5 seconds!
```

## Solution
Two complementary fixes applied:

**1. `asyncio.to_thread()` for direct provider calls:**
```python
async def get_current_value(self, identifier: str, ...):
    info = await asyncio.to_thread(lambda: yf.Ticker(identifier).info)
```

**2. Thread isolation at framework level ([[F-060]]):**
`_run_provider_in_thread()` in `asset_source.py` runs every provider call in a dedicated thread with its own event loop — providers can use sync I/O directly without `asyncio.to_thread()`.

## Prevention
See [[concepts/async-io-rule]] — the rule codified from this problem.
Any new provider or endpoint touching external HTTP must follow the rule.

## Impact
- Caused session-level freezes during development testing
- Discovered early enough not to reach production
- Led to the creation of `F-060` Thread Isolation as a systemic fix

## Source files

| Role | Path |
|------|------|
| Thread isolation fix | `backend/app/services/asset_source.py` |
| yfinance provider (example) | `backend/app/services/asset_source_providers/yahoo_finance.py` |
| FastAPI main (sync endpoints) | `backend/app/main.py` |
