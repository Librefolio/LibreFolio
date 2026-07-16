---
title: "AI export used ticker/ISIN as the primary asset label instead of name"
category: problem
status: resolved
date: 2026-07-15
tags: [frontend, ai-export, naming, bug-fix]
related: [decisions/ai-export-prompt-catalog]
---

# Problem: AI export used ticker/ISIN as the primary asset label instead of name

## Symptom

While using the AI Portfolio Export feature over several days, the user noticed the receiving AI
kept referring to assets by their ticker or ISIN in its responses (e.g. "VWCE" or "IE00BK5BQT80")
instead of the human-readable name — "pessima scelta ... dovrebbe usare il nome" (bad choice, should
use the name).

## Root Cause

Two independent causes, both needed fixing:

1. **Real code bug**: several places in `frontend/src/lib/features/ai-export/` built a compact
   "label" for an asset as `symbol ?? name` (ticker first, name only as fallback) instead of the
   other way around:
   - `technical/technicalExportBuilder.ts:177` — `asset: input.assetTicker ?? input.assetName` for
     every technical event.
   - `aiExportBuilder.ts` — `by_asset` allocation mapping, and the technical-summary weight-lookup
     key/label, both did `p.symbol ?? p.name` / `a.metadata.symbol ?? a.metadata.asset`.
   - `aiPromptRenderer.ts` / `aiDataRenderer.ts` — the `### Technical Series — {label}` table headers
     used the same ticker-first fallback.

   `AiPosition.name` (the full display name) was already exported correctly as its own field — the
   bug was specifically in these secondary "compact label" call sites, not in the main position data.

2. **No explicit instruction to the receiving AI**: even with the data fixed, nothing told the
   external AI to *prefer* the name when writing its own prose — a model might still pick the shorter
   ticker string out of habit.

## Solution

- Introduced `assetLabel.ts` with `buildAssetIdentifiers()` (wraps the existing
  `buildIdentifiersList()` from `$lib/utils/assetTypes.ts` — reused unchanged, already covers all
  `IdentifierType` enum values: ISIN/TICKER/CUSIP/SEDOL/FIGI/UUID/OTHER) and
  `disambiguateAssetName()`/`findCollidingAssetIds()` for the one legitimate edge case where a
  ticker-like disambiguator might seem tempting: two *different* assets (different `asset_id`) that
  happen to share the exact same `display_name`. That case is now disambiguated with asset
  type/currency/broker instead of an identifier — ticker/ISIN is never used as a display label, full
  stop. Positions of the *same* asset across multiple brokers are correctly NOT treated as a
  collision (identical name there is correct, not ambiguous).
- Replaced every `symbol ?? name` fallback with plain `name` (or the resolved, disambiguated name)
  across `aiExportBuilder.ts`, `technicalExportBuilder.ts`, `aiPromptRenderer.ts`, `aiDataRenderer.ts`.
- Replaced the `symbol?: string` field on `AiPosition` / `AiTechnicalMetadata` / `AiTechnicalSummaryItem`
  with `identifiers?: Record<string, string>` — *all* known identifiers are still exported (per the
  user's explicit instruction: "dagli tutti gli identificatori che abbiamo in db" — give it all
  identifiers we have in the DB), just as an auxiliary block clearly meant for the AI's own web
  research, never as the primary label.
- Added a new shared prompt fragment, `PROMPT_ASSET_NAMING` (in
  `templates/responseStyleTemplate.ts`), included in the header of every instruction-bearing prompt:
  "Refer to assets only by their `name` field ... Never use ticker, ISIN, or other identifier codes to
  refer to an asset when talking to the user — those fields are provided only to support accurate web
  research." This is the defense-in-depth half of the fix — even a well-behaved data model can't force
  an LLM's word choice, only ask for it.

## Prevention

Any new field or renderer added to the AI export feature that needs a compact/unique asset label
should call `buildAssetIdentifiers()` for the identifiers block and use `name` (never `symbol`/ticker)
for anything readable by a human or by the receiving AI's prose. If two different assets can share a
`display_name`, run them through `findCollidingAssetIds()`/`disambiguateAssetName()` first.

## Impact

Frontend-only fix, no backend/API changes, no data migration. `svelte-check`: 0 errors/warnings after
the refactor; `./dev.py i18n audit`: 0 incomplete keys (unrelated i18n additions from the same session
covered separately in [[decisions/ai-export-prompt-catalog]]).
