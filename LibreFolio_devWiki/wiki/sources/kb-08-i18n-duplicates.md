---
title: "Knowledge Base: i18n Duplicate Management"
category: source
source_type: knowledge_base
date_ingested: 2026-04-24
original_path: LibreFolio_developer_journal/knowledge_base/08_i18n_duplicates.md
tags: [i18n, frontend, translations, duplicates, rationalization]
related_features: [F-008]
---

# Source: Knowledge Base 08 — i18n Duplicate Management

## Summary

Strategic documentation of i18n key rationalization (consolidate under `common.*` only when meaning, context AND value match in all 4 languages). Covers 42 total duplicate groups (18 consolidated, ~30 accepted), rationale for keeping semantic duplicates (e.g., `common.close` button vs `dataEditor.col.close` OHLC price), dynamic prefix preservation (`assets.types.*`), and the principle: **intentional duplicates are OK when namespacing clarity > DRY**.

## Key insights extracted

- **i18n rationalization principle** (consolidate only when ALL languages + context match) → [[decisions/i18n-key-rationalization]] created
- **42 duplicate groups** (18 consolidated, ~30 accepted for semantic reasons) → [[features/F-008]] enriched
- **Dynamic prefix exceptions** (must preserve for runtime lookup like `$t(\`assets.types.${var}\`)`) → [[decisions/i18n-key-rationalization]]
- **Context matters** (same EN value but different context = keep separate, e.g., "Close" button vs "Close" price) → [[decisions/i18n-key-rationalization]]
- **Phase 6 cleanup** (875→825 keys after 50 consolidations) → [[features/F-008]] status history updated

## Wiki pages updated

- [[features/F-008]] — i18n System — added duplicate rationalization details, Phase 6 cleanup stats
- [[decisions/i18n-key-rationalization]] — created new decision page for duplicate management principle

## Source files

| Role | Path |
|------|------|
| Source KB file | `LibreFolio_developer_journal/knowledge_base/08_i18n_duplicates.md` |
| EN translations | `frontend/src/lib/i18n/en.json` |
| IT translations | `frontend/src/lib/i18n/it.json` |
| FR translations | `frontend/src/lib/i18n/fr.json` |
| ES translations | `frontend/src/lib/i18n/es.json` |
| i18n CLI | `dev.py` (i18n subcommands) |
| Phase 6 plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-06-subplan/Bugfix-Step6/plan-phase06Step6-i18n-dedup.prompt.md` |
