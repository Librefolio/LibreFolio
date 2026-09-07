---
title: "`NamedCache.clear()` left the admission filter loaded and the cache stopped storing forever"
category: problem
status: resolved
date: 2026-08-30
tags: [backend, cache, theine, silent-failure, third-party]
related: [concepts/discard-the-answer-not-the-question]
---

# Problem: a cache that reports empty and refuses every write

## Symptom

After `NamedCache.clear()`, the cache accepted no new entries. Not slowly — at
all. `len()` said zero, `set()` returned normally, `get()` always missed.

Silently, permanently, for the lifetime of the process.

## Root cause

theine 2.0.0 uses a **W-TinyLFU** admission policy: a new key is admitted only if
its estimated frequency beats that of the victim it would evict.

`NamedCache.clear()` emptied the backing map but left the **frequency sketch**
loaded with the counts of everything the cache had ever held. Every subsequent
`set()` was measured against ghosts and rejected.

## The measurement that pinned it

The behaviour depends on how full the cache was before the clear:

| entries before `clear()` | recovers? |
|---|---|
| 19 | **yes** |
| 20 | **no** |

The discontinuity is the sketch's reset threshold. Below it the counters are
still small enough for a new key to win; above it they never are.

## Fix

`maxsize` is touched **once** after the clear, which forces theine to rebuild the
policy structures. One line, found by reading the library's source after the
19/20 boundary made it obvious the problem was in the admission path and not in
the map.

## Why it is worth a page

The failure has **no signal**. No exception, no log line, no metric — the only
externally visible effect is that everything downstream gets slower, which reads
as load. It would have survived indefinitely in production.

> A cache that stops caching does not fail. It degrades into a very expensive
> pass-through, and the only way to notice is to assert on the hit rate.

The general lesson matches
[[concepts/discard-the-answer-not-the-question]] from the other direction: here
the code discarded the *data* and kept the *statistics*, which is exactly the
wrong half to keep.

## Source files

| Role | Path |
|------|------|
| Cache wrapper | `backend/app/utils/cache_utils.py` — `NamedCache.clear` |
| Dependency | `theine` 2.0.0 (`requirements.txt`) |
| Cache consumers | `backend/app/services/fx.py`, `backend/app/services/asset_service.py` |
