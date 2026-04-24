---
title: "i18n Key Rationalization — Intentional Duplicates"
category: decision
status: resolved
date: 2026-04-24
tags: [frontend, i18n, translations, duplicates, consolidation]
related_features: [F-008]
---

# Decision: i18n Key Rationalization — Intentional Duplicates

## Context

Phase 6 i18n cleanup reduced keys from 875 → 825 (50 duplicates consolidated under `common.*`). However, 42 duplicate groups remain. The question: should all duplicates be eliminated in favor of DRY principle, or are some duplicates intentional and beneficial?

Initial impulse: consolidate everything with identical values (e.g., "Close" appears 5 times → merge to `common.close`). But real-world analysis revealed many "duplicates" serve **different semantic purposes** despite identical EN text.

## Options Considered

### Option A: Aggressive DRY (consolidate all)

**Approach**: Any key with identical value in any language → consolidated under `common.*`.

**Pros**:
- Minimum key count (~750 keys)
- Single source of truth for each string
- Easier for translators (change once, affects all)

**Cons**:
- **Loss of semantic clarity**: `common.close` used for both "Close button" and "Close price (OHLC)" — different meanings
- **Translation inflexibility**: IT/FR/ES might need different translations based on context (e.g., "Chiudi" vs "Chiusura")
- **Dynamic prefix breakage**: keys under `assets.types.*` must stay for `$t(\`assets.types.${var}\`)` to work
- **Future divergence locked out**: if "Close" button becomes "Dismiss" but OHLC "Close" stays, the keys were always separate concepts

### Option B: Context-aware rationalization (chosen)

**Approach**: Consolidate under `common.*` **only when meaning, context, AND value match in all 4 languages**. Accept duplicates when:
1. **Semantic difference** (button "Close" ≠ OHLC "Close")
2. **Dynamic prefix** (must preserve for runtime lookup)
3. **Context specificity** (generic "Save" ≠ form "Save Changes")
4. **Future flexibility** (EN identical today, but IT/FR/ES already diverge or likely will)

**Pros**:
- **Namespace clarity**: `dataEditor.col.close` = OHLC price, `common.close` = UI button — intent explicit
- **Translation flexibility**: IT can use "Chiusura" for OHLC, "Chiudi" for button
- **Future-proof**: if usage diverges, keys already separate
- **Dynamic lookups safe**: `assets.types.*` stays intact

**Cons**:
- Slightly higher key count (~825 vs ~750)
- Some perceived redundancy (EN shows "Close" twice)

### Option C: Hybrid (consolidate same-context only)

**Approach**: Merge duplicates within same namespace (e.g., `assets.sync.title` + `assets.sync.modalTitle`) but keep cross-namespace separate.

**Rejected because**: Still loses semantic clarity. Modal title and page title might diverge in phrasing even within same feature.

## Decision

**Chosen: Option B — Context-aware rationalization.**

**Principle**: **Intentional duplicates are OK when namespacing clarity > DRY.**

Consolidate a duplicate group **only** when:
- Same **semantic meaning** (both are buttons, both are labels, etc.)
- Same **UI context** (both in forms, both in tables, etc.)
- Identical **value in all 4 languages** (EN/IT/FR/ES)
- No future divergence expected

If any of the above is false → **keep keys separate**.

## Consequences

### Positive

1. **Semantic integrity preserved**: `common.close` (button) ≠ `dataEditor.col.close` (OHLC) — intent clear
2. **Translation quality**: IT translators can use "Chiudi" vs "Chiusura" appropriately
3. **Namespace stability**: `assets.types.*`, `settings.globalSettingUnits.*` dynamic prefixes intact
4. **Refactor-safe**: if "Close" button changes to "Dismiss", only `common.close` changes — OHLC unaffected

### Trade-offs

1. **~30 accepted duplicate groups remain** (documented in `knowledge_base/08_i18n_duplicates.md`)
2. **Not strict DRY**: some strings repeated across namespaces
3. **Translator sees duplicates**: must understand context to translate correctly (but this is true regardless — context always matters)

### Implementation

**Phase 6 cleanup actions**:
- Consolidated 18 groups where all 4 languages + context matched (e.g., `common.cancel` absorbed 3 duplicates)
- Accepted ~30 groups as intentional (e.g., `common.close` vs `dataEditor.col.close`)
- Documented rationale for each accepted group in `knowledge_base/08_i18n_duplicates.md`

**Commands**:
```bash
./dev.py i18n audit --duplicates  # show all duplicate groups
./dev.py i18n search "Close" --values  # check all keys with "Close"
```

### Future Guidelines

**Before creating a new key**:
1. Search `common.*` for existing key (`./dev.py i18n search`)
2. If found and **same semantic meaning** → reuse `common.*`
3. If found but **different context/meaning** → create namespaced key
4. Document rationale if value is identical but key is separate

**When translating**:
1. Check namespace for context clues (`dataEditor.col.X` = table column)
2. Verify EN usage in codebase (`grep -r "dataEditor.col.close"`)
3. Choose appropriate translation based on semantic meaning, not just EN text

## Examples of Accepted Duplicates

| Key A | Key B | EN Value | Reason Separate |
|-------|-------|----------|-----------------|
| `common.close` | `dataEditor.col.close` | "Close" | Button (Chiudi) vs OHLC price (Chiusura) |
| `common.reset` | `common.undo` | IT: "Ripristina" | EN different ("Reset to Default" vs "Undo"), IT happens to match |
| `assets.types.OTHER` | `common.other` | "Other" | `assets.types.*` is dynamic prefix for runtime lookup |
| `assets.sync.assetsCount` | `assets.title` | EN: "Assets" | Count label vs page title — may diverge ("2 assets synced" vs "Assets") |
| `chartSettings.signals.ema` | `chartSettings.signals.emaAbbr` | Both "EMA" today | Name might become "Exponential Moving Average" while abbreviation stays "EMA" |

Full list: `knowledge_base/08_i18n_duplicates.md`

## Links

- [[features/F-008]] — i18n System feature page
- Source: `LibreFolio_developer_journal/knowledge_base/08_i18n_duplicates.md`
- Plan: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step6/plan-phase06Step6-i18n-dedup.prompt.md`

## Source files

| Role | Path |
|------|------|
| Source KB file | `LibreFolio_developer_journal/knowledge_base/08_i18n_duplicates.md` |
| EN translations | `frontend/src/lib/i18n/en.json` |
| IT translations | `frontend/src/lib/i18n/it.json` |
| FR translations | `frontend/src/lib/i18n/fr.json` |
| ES translations | `frontend/src/lib/i18n/es.json` |
| i18n audit CLI | `dev.py` (i18n audit subcommand) |
| Phase 6 plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step6/plan-phase06Step6-i18n-dedup.prompt.md` |
