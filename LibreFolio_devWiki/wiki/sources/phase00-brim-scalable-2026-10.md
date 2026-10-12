---
title: "Phase 0 / 37 — the Scalable Capital importers (workstream S), the exporter's recap, and the page out of alpha (M, batch 21)"
category: source
source_type: plan
date_ingested: 2026-10-12
original_path: LibreFolio_developer_journal/Release_2/Phase_0/37_brimScalable/plan-phase00BrimScalable.prompt.md
tags: [phase0, release2, workstream-s, brim, scalable, import-wizard, bulk-editor, icons, i18n, exporter]
related:
  - decisions/scalable-two-accounts-two-plugins
  - decisions/import-wizard-default-plugin-check
  - decisions/broker-icon-order-dedicated-plugin-first
  - decisions/bulk-pairs-new-with-saved
  - problems/merged-transfer-not-seen-as-duplicate
  - concepts/brim-texts-translated-by-code
---

# Source: Phase 0 / 37 — the Scalable Capital importers

## Summary

Plan 37 of workstream S (814 lines, closed on 2026-10-10, still in `Phase_0/`) built two BRIM plugins for the two
accounts of a Scalable Capital customer, on the files of the Chrome exporter that the same workstream had released
the day before. Its companion, the exporter's recap (245 lines), records that earlier phase: the file format, the
developer's decisions, the facts checked on real data, the gaps. The plan went further than the importers. It added a
check of every uploaded file against its broker's default plugin, pairs of new and saved rows in the bulk editor, and a
fix for merged transfers that came back as new. It also reversed the broker icon order and translated every plugin's
name and description. All five checkpoints entered `dev_release2` with train 30 (merge `262339501`); the developer's
test with his real exports passed 7 of 7. On 2026-10-12 M's batch 21 rewrote the user page and took the importers out
of alpha (`ff2cf5b3d`, train 55).

## Key Takeaways

- **One customer, two brokers, two plugins** that refuse each other's file with a code — the broker's default plugin
  names the account: [[decisions/scalable-two-accounts-two-plugins]].
- **The wrong-broker check**, for every broker: `cannot_parse_detail`, the `plugin-check` endpoint and a modal with
  Move, Keep, Remove — [[decisions/import-wizard-default-plugin-check]].
- **The bulk editor pairs new rows with saved ones**, reminds before saving, merges all, and pairs securities only when
  they cancel exactly — [[decisions/bulk-pairs-new-with-saved]].
- **A merged transfer is a duplicate on re-import**: [[problems/merged-transfer-not-seen-as-duplicate]].
- **The broker icon order** puts a dedicated plugin before the portal's favicon, with one threshold constant —
  [[decisions/broker-icon-order-dedicated-plugin-first]].
- **Plugin texts translated by code** in four languages: [[concepts/brim-texts-translated-by-code]].
- The glossary of the translations (PRU in French, PMC in Spanish, «Giroconto» in Italian…, `cd0b404d2`) and the
  non-breaking space before «%» in French and Spanish were aligned on the way.

## Checkpoints

| Checkpoint | Content | Commit |
|---|---|---|
| CP1 | the plan, the samples, the contract and the endpoint, the plugins, merged-transfer duplicates, API tests, icons, docs, the modal and its translations | `305b80202` |
| CP2 | new + saved pairs in the bulk editor | `94271713b` |
| CP3 | three items from the coordinator: the cost warning's text, eToro's description, the bulk page | `4347f8962` |
| CP4 | fixes from the developer's test; the glossary | `2046b7419`, `cd0b404d2` |
| CP5 | the icon order, French spaces, securities pairs that cancel, the spec for lot 40 | `d5c649e9f`, `1a4fe32a4`, `3efa748cd` |

Outside the monorepo: the exporter 1.0.1 (`6672084`, tag `v1.0.1`), committed and tagged by the developer.

## Left open, with whom (2026-10-10, updated)

- The translations of the documentation: done by M's batch 21 on 2026-10-12. A second rewrite of the page, M's batch
  23, is not in the target at `573f7c5c7`.
  *Update (step B8)*: batch 23 reached the target with train 58 (`11339afa6`). The developer reviewed the page in a live
  preview and approved it («vista la pagina di scalable, approvata a pieni voti»): accounts with their icons in the
  first column, «❓ Why two brokers?» as a heading, the exporter recommended in bold, the wrong-broker hint in a blue
  note — [[sources/phase00-translation-round12-2026-10]], [[problems/mkdocs-material-tables-resist-styling]].
- The per-broker P&L lines jumped at every merged transfer: found in the developer's test, then fixed by lot 41 —
  [[decisions/portfolio-pnl-series-contracts]], [[sources/phase00-broker-pnl-flows-2026-10]].
- Reported to P and closed by lot 42 (train 34): see [[decisions/bulk-pairs-new-with-saved]].
- Backlog 38: C-39, the catalogues split by namespace, and C-40, a selector for the broker icon.
- `SearchSelect` picking another option after a search: not reproduced in nine headless runs; suspended by the
  developer until it happens again.
- The exporter's own todos: the order's limit price, history and documents; anonymised fixtures to develop without an
  account; the Chrome Web Store only if the project grows.

## Wiki Pages Updated

- Created: the six pages above.
- Updated: [[features/F-013]], [[features/F-049]], [[features/F-048]], [[features/F-012]] (status history),
  [[entities/import-wizard-modal]].

## Source files

| Role | Path |
|------|------|
| Plan 37 | `LibreFolio_developer_journal/Release_2/Phase_0/37_brimScalable/plan-phase00BrimScalable.prompt.md` |
| The exporter's recap | `LibreFolio_developer_journal/Release_2/Phase_0/37_brimScalable/recap-phase00ScalableExporter.md` |
| M's journal, §12 (batch 21) | `LibreFolio_developer_journal/Release_2/Phase_0/27_releaseImages/plan-phase00TranslationRound12.prompt.md` |
| The plugins | `backend/app/services/brim_providers/` |
| User guide | `mkdocs_src/docs/user/transactions/import/scalable.en.md` |
| Developer page | `mkdocs_src/docs/developer/backend/brim/scalable.md` |
