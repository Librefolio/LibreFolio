---
title: "The span as a detector — and a detector proven only on the case it must catch is not proven"
category: concept
date: 2026-09-23
tags: [testing, method, gates, false-positive, measurement, lanes, contamination, sqlite]
related:
  - problems/tab-writes-after-the-look
  - problems/discarded-risk-answer-read-as-empty
  - problems/testid-grep-false-negative
  - concepts/characterisation-test-latch
---

# Concept: the span as a detector

> Declared in R2-101 (*"l'arco come rilevatore"*, with the asymmetry of a false positive on
> what a gate authorises). Filed 2026-09-23 from R2-96 and R2-100, with R2-68, R2-73, R2-97,
> R2-107 and R2-112 for the history and the family. All of it happened on 18/09 unless dated.

## Definition

To tell whether a lane's `price_history` was written by **one act** (a populate) or by more
(a populate, then a browser visit), measure the **span** of the writes — the time between the
first and the last `fetched_at` — not the number of distinct instants:

```sql
SELECT ROUND((julianday(MAX(fetched_at)) - julianday(MIN(fetched_at))) * 86400, 1) FROM price_history;
```

| lane | span |
|---|---:|
| freshly repopulated (measured) | **0.1 s** |
| contaminated (derived from the recorded `17:05:42` → `18:43:47`) | **5 885 s** |

Three orders of magnitude separate one act from two, and there is no threshold to tune.

> *The count asked "how many distinct instants?" — a property of the clock. The span asks
> "how long between the first write and the last?" — a property of the act.* (R2-96)

It works because every write stamps `fetched_at`: the model defaults it to `utcnow`, the price
store stamps it on every write, and the intra-day extend of a current price re-stamps it — so
any later write moves `MAX`. It reads `price_history` only; a write elsewhere (`fx_rates`
carries its own `fetched_at`) is outside what it sees.

## How it got there — three detectors in one day

| detector | reads | fate |
|---|---|---|
| N's: `COUNT(*) … WHERE close = ROUND(close,2)` (R2-68) | the **aspect** of a row | two false negatives on providers that do not round to two decimals (R2-73); then its premise fell to the price-store log — `price_store` copies what the provider gives, with 1, 2, 3 or 26 decimals — and it was retired even as a confirmation (R2-97): *"a detector whose error rate is drawn from the data it inspects can prove presence, never absence"* |
| v1: bursts of `fetched_at` per second (S5; made the campaign gate in R2-73) | the **act**, through the clock | false positive on a clean lane — retired (R2-96) |
| v2: the span (S5) | the act | the mandatory gate before any numeric measurement (`_comune.md`, Ⓓ) |

### Why v1 was retired rather than tuned (R2-96)

Measured on two equally clean lanes:

| lane | bursts | span | v1 verdict |
|---|---:|---:|---|
| coordinator's, never looked at | 1 (`17:58:38` → 2 615 rows) | 0.13 s | CLEAN |
| S5's, just repopulated | 2 (`18:45:52` → 1 331 · `18:45:53` → 1 284) | ~0.1 s | **CONTAMINATED** ❌ |

The only difference is where the populate crossed a second boundary: the coordinator's 2 615
rows fell inside one label by chance. His measurement, read without S5's, would have
"confirmed" v1 — **ratifying a broken gate with a lucky sample**.

The asymmetry decided retirement over calibration:

> **A false positive on what must *give the go-ahead* costs more than a false negative on what
> must stop — because people learn to ignore it.**

A gate that authorises ("this lane is clean, you may measure") and cries wolf on the healthy
state teaches its users to walk past it.

## The rule (R2-100)

> **A detector proven only on the case it must catch is not proven.**

*"v1 had never been tested on the state it must authorise. We had exercised it only on
contaminated lanes — where it worked — because that was where it was needed. Half of its
domain is the healthy case, and that is the half on which the go-ahead is decided."* That is why
the error was invisible to both parties: the gate was exercised only where the expected answer
was "contaminated", the half in which it could not be visibly wrong.

The finding surfaced only because the ordered procedure (repopulate → measure → look → discard)
handed S5 a clean state: *"I had not looked for it — the order you gave me handed it to me."* The
procedure produced the proof that falsified the gate it contained.

**For every gate**: exercise it on **both** expected outcomes, and exercise the one that
authorises **above all on the healthy case**.

## Same family, other axes

The registry lines up three variants (R2-112, 21/09):

| entry | defect |
|---|---|
| R2-100 | a gate **exercised** only on the half in which it fires |
| R2-107 | a gate whose **default** has no half in which it fires — `front format` runs `prettier --write` and repairs in silence; the reporting `--check` is opt-in |
| R2-112 | a tool whose **negative** result has two causes and shows one — a `grep -E` returning zero because of the pattern, not the file |

Two near relatives: a probe that demonstrates a defect must carry at least one case that must pass
(R2-56 — the control is there to discover that the probe does not discriminate); and an exception
logged inside a green test, raised on purpose, reads as a red (R2-104 — a signal that looks like a
defect and proves it is handled). For R2-112's shape in selectors see
[[problems/testid-grep-false-negative]]; for what the gate was protecting against, see
[[problems/tab-writes-after-the-look]].

## Source files

| Role | Path |
|------|------|
| The gate as adopted (Ⓓ); v1 and N's detector retired, with the reasons | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/_comune.md` |
| The measurement — passo 1e, *Fuori pista* 2 and 3 | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/progress/S5-esecuzione.md` |
| Registry — R2-68, R2-73, R2-96, R2-97, R2-100, R2-101, R2-107, R2-112 | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/REGISTRO.md` |
| `PriceHistory.fetched_at`, default `utcnow` | `backend/app/db/models.py` |
| Every price write stamps `fetched_at` | `backend/app/services/asset_sources/price_store.py` |
| Intra-day extend re-stamps `fetched_at` | `backend/app/services/asset_sources/price_query.py` |
| The single act that writes the lane | `backend/test_scripts/test_db/populate_mock_data.py` |
