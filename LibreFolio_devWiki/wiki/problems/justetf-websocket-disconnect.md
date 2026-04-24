---
title: "JustETF WebSocket silent disconnect"
category: problem
status: workaround
date: 2026-04-01
tags: [backend, providers, justetf, websocket, threading, live-quotes]
related: [decisions/provider-shutdown-generic]
---

# Problem: JustETF WebSocket Silent Disconnect

## Symptom
The JustETF provider streams live quotes via a persistent WebSocket. After an indeterminate period (hours), the WebSocket can stop delivering quotes without raising an exception. `get_current_value()` continues returning the last known value indefinitely — the stale price is not flagged as stale.

## Root Cause
`iterate_live_quote` (from the `justetf-scraping` library) can enter a frozen state where the generator yields nothing and throws no exception — the worker thread blocks on the generator without timing out. There is no active watchdog to detect this frozen state. Only exceptions trigger the reconnect loop.

## Solution
The implemented workaround:
1. Each ISIN gets a dedicated daemon thread: `_live_quote_worker(isin)` in `justetf.py`
2. The worker wraps `iterate_live_quote` in `try/except Exception` and reconnects on any exception with **exponential backoff** (1 s → cap at 60 s)
3. Backoff sleep uses `_live_quote_stop.wait(timeout=backoff)` — interruptible when `shutdown_live_feeds()` is called
4. Global state: `_live_quote_store: dict[str, object]` (isin → latest Quote), `_live_quote_threads`, `_live_quote_stop: threading.Event`
5. `get_current_value()` reads from `_live_quote_store` (instant, no I/O)
6. `shutdown_live_feeds()` called at app shutdown via `provider_shutdown_generic` pattern

## Prevention
- A future improvement would add a **watchdog thread** that checks `_live_quote_store[isin].timestamp` and restarts the worker if no update was received within N minutes
- For now: the exponential backoff handles disconnects that raise exceptions; frozen generators are not handled

## Impact
- Users may see stale prices for an ISIN if the WebSocket freezes without exception
- No crash, no data loss — just a frozen price display until next app restart or next reconnect cycle

## Source files

| Role | Path |
|------|------|
| JustETF provider | `backend/app/services/asset_source_providers/justetf.py` |
| Provider shutdown pattern | `backend/app/services/asset_source.py` |
