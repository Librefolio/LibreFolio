---
title: "BRIM is a Parser Only (Revision 2)"
date: 2026-04-20
status: resolved
tags: [brim, architecture, separation-of-concerns]
related_features: [F-012, F-049]
related_sources: [sources/phase07-part2-brim-revision]
---

# Decision: BRIM is a Parser Only

## Context

Phase 07 Part 2 v1 had extended BRIM beyond parsing: it introduced `BRIMCapabilities`,
generated `asset_events` from dividends, and had a dedicated `POST /brokers/import/commit`
endpoint that atomically created both events and transactions in one call.

A design review with the user triggered a full architectural reset.

## Decision

**BRIM is a parser. It reads a broker file, produces transactions with fake asset IDs,
and returns the extracted data. It does not commit, does not emit asset events, and does
not declare capabilities.**

### What was REMOVED

| Item | Reason |
|------|--------|
| `BRIMCapabilities` | No real consumers — dead code from day one |
| `BRIMParseOutput.asset_events` | Dividends as AssetEvents are the asset provider's job (yfinance/JustETF), not the broker file importer's |
| `POST /brokers/import/commit` | After fake-ID resolution, the frontend uses the standard `/transactions/bulk` endpoint |
| `commit_import()` service | Follows commit endpoint removal |
| `BRIMCommitRequest/Response/ResultItem` | No endpoint to serve them |
| `AssetCRUDService.bulk_upsert_events_strict()` | Was only used by commit_import |

### What was KEPT

- `BRIMProvider.parse()` → `BRIMParseOutput(transactions, warnings, extracted_assets)`
- `search_asset_candidates()` (backend suggests candidates; frontend decides)
- `detect_tx_duplicates()`
- `is_fake_asset_id()` + `FAKE_ASSET_ID_BASE`
- File auto-transition: `move_to_parsed()` / `move_to_failed()`
- Parse result cache via metadata sidecar

### What was ADDED

- `BRIMProvider.plugin_version: str` (default `"1.0.0"`) — for cache invalidation
- `BRIMFileInfo.parse_is_stale: bool` — computed lazily comparing `parsed_plugin_version`
  in sidecar vs current registry version. UI shows "stale parse" without re-parsing.

## Final Flow

```
upload → parse (BRIM) → fake-ID resolution (Staging Modal) → commit (POST /transactions/bulk)
```

The commit step uses the same atomic multi-broker endpoint as manual entry.
No BRIM-specific commit API exists.

## Alternatives Considered

- **Keep commit endpoint, remove events only**: rejected. The commit endpoint was
  architecturally inconsistent — it was a duplicate path for something the standard
  bulk TX endpoint already did, with added complexity.

## Implications

- `TRANSFER_IN`/`TRANSFER_OUT` from broker files are plain transactions — no auto-link
  creation in the BRIM layer. The Staging Modal may suggest links via `events/suggest`.
- The Schwab plugin no longer generates `AssetEvent` rows for dividends — it generates
  `DIVIDEND` transaction rows (cash flow in the portfolio).

## Source files

| Role | Path |
|------|------|
| BRIM abstract base | `backend/app/services/brim_provider.py` |
| BRIM schemas | `backend/app/schemas/brim.py` |
| BRIM API | `backend/app/api/v1/brokers.py` |

## Related decisions

- [[decisions/brim-fake-asset-id]] — the fake-ID mechanism is what makes parser-only viable: parsers emit negative integers as placeholder IDs, decoupling parse from the asset catalog. BRIM cannot be parser-only without fake IDs.
- [[decisions/multi-broker-atomic-tx]] — the standard `/transactions/bulk` endpoint (the only commit path after Revision 2) is multi-broker atomic.
