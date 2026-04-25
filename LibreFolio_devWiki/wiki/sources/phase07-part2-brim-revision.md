---
type: source
title: "Phase 07 — Part 2: BRIM Revision 2 (Parser-Only)"
date_ingested: 2026-04-24
date_updated: 2026-04-25
git_hash: a61b0dfa
path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte2/plan-phase07-transaction-Part2.prompt.md
status: "✅ DONE"
related: [features/F-012, decisions/brim-parser-only, sources/phase07-transactions, workflows/brim-import-flow]
---

# Phase 07 Part 2 — BRIM Revision 2

> Architectural reset of BRIM after v1 was partly implemented then reconsidered.
> The core principle: **BRIM is a parser, nothing more.**
>
> **Path note**: archived 2026-04-25 from `RoadmapV4_UI/plan-phase07-transaction-Part2.prompt.md`
> into `phases/phase-07-subplan/Parte2/`. All Part 2 work is complete.

## Context

Phase 07 Part 1 had already built the basic transaction model. Part 2 v1 had
tried to give BRIM more responsibilities (commit endpoint, asset events, capability
flags). A critical design review triggered a full architectural reset (Revisione 2).

## Key Decisions Made

### BRIM Parser-Only (Revisione 2)

The fundamental principle confirmed: BRIM reads a file, produces `transactions[]`
with negative fake_asset_ids and `extracted_assets{}`, and stops there.

**REMOVED from v1:**
- `BRIMCapabilities` (no real consumers, dead code)
- `BRIMParseOutput.asset_events` (dividends as events are the asset provider's job)
- `POST /brokers/import/commit` endpoint
- `commit_import()` service function
- `BRIMCommitRequest/Response/ResultItem` schemas
- `AssetCRUDService.bulk_upsert_events_strict()` (was only used by removed endpoint)
- Tests for removed code

**ADDED:**
- `BRIMProvider.plugin_version: str` (default `"1.0.0"`) for cache invalidation
- `BRIMFileInfo.parse_is_stale: bool` — computed lazily: `True` if `status==PARSED AND parsed_plugin_version != registry.current_version`
- `BRIMFileInfo.parsed_plugin_version` (stored in sidecar JSON)

**RENAMED:**
- `AssetSourceManager.bulk_upsert_events_manual()` → `bulk_upsert_events()` (suffix was redundant after removing `_strict` variant)

### Final BRIM Flow

```
upload → POST /brokers/import/upload               → file_id
parse  → POST /brokers/import/files/:id/parse
        plugin.parse() → BRIMParseOutput (tx + extracted_assets + warnings)
        + search_asset_candidates() → asset_mappings[]
        + detect_tx_duplicates()    → duplicates
        auto: move_to_parsed() + save_parse_result(plugin_version)
                    ▼
Staging Modal (frontend — Part 5)
  resolves fake_id → real asset_id
  matches TX ↔ AssetEvent (events/suggest endpoint)
  deselects duplicates
                    ▼
commit → POST /transactions/bulk  (standard endpoint — Part 3)
         atomic multi-broker
```

### Internal Refactors

- Extracted module-level `_build_file_info_from_metadata(meta_path)` — unified the
  two inner helpers that had identical bodies in `list_files` and `get_file_info`
- Extracted `_find_metadata_path(file_id)` for DRY metadata path scanning

### Test Standardization

Merged `TestPluginInterface` (pattern A: parametrize on string code, instantiate inside)
and `TestBRIMPluginsContract` (pattern B: parametrize on tuple, instantiate at collection
time) into a single `TestBRIMPlugin` class using Pattern B — fail-fast at collection,
consistent with `test_asset_providers.py` / `test_fx_providers.py`.

New tests added:
- `test_parse_is_idempotent` — same file, same output (required for cache reuse)
- `test_parse_produces_negative_fake_ids`
- `test_parse_broker_id_propagated_on_all_tx`
- `test_parse_is_stale_detection` (monkeypatching plugin_version 1.0.0 → 2.0.0)

## Wiki Cross-References

- [[F-012]] BRIM Framework — enriched
- [[decisions/brim-parser-only]] — decision extracted
- [[sources/phase07-transactions]] — Part 1 (predecessor)

## Source files

| Role | Path |
|------|------|
| BRIM abstract base | `backend/app/services/brim_provider.py` |
| BRIM schemas | `backend/app/schemas/brim.py` |
| BRIM API endpoint | `backend/app/api/v1/brokers.py` |
| Asset source (renamed method) | `backend/app/services/asset_source.py` |
| Plugin test | `backend/test_scripts/test_external/test_brim_providers.py` |
