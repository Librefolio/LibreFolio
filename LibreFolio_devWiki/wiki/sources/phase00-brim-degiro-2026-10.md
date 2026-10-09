---
title: "Phase 0 / 31 — BRIM DEGIRO (issue #35): read by position, in every language"
category: source
source_type: plan
date_ingested: 2026-10-09
original_path: LibreFolio_developer_journal/Release_2/phases/31_brimDegiro/plan-phase00BrimDegiro.prompt.md
tags: [phase0, release2, brim, degiro, csv, i18n, fx-conversion, issue-35]
related:
  - features/F-013
  - features/F-083
  - decisions/brim-parser-only
  - concepts/import-todo-signals
---

# Source: Phase 0 / 31 — the DEGIRO plugin

## Summary

One plan (~430 lines), integrated in train 9 (merge `2cecf5a00`, commits `05ff499c5`, `3d61fd63f`, `dfd6ed963`,
2026-10-07) and archived on 2026-10-09. Issue #35 reported DEGIRO statements in languages the plugin did not know.
The plugin was rewritten to read the Account Statement **by column position** — the twelve columns are the same in
every language — and the wizard learned to keep the two legs of a currency exchange together.

## Key takeaways (decisions D1–D10, all approved as recommended)

- **D1 numbers**: the decimal mark is decided per value when certain; the file's own mark only for ambiguous values
  such as `1.000` (one separator before exactly three digits). Rejected: one separator per file — the mixed-format
  sample breaks it.
- **D2 exchange legs** are paired without the rate (group, currency, sign, adjacency). Rejected: the rate as a
  tie-breaker, word matching.
- **D3** in the wizard, ticking one leg ticks its partner, and only complete pairs reach the editor
  (`frontend/src/lib/utils/transactions/importPairs.ts`); "Select visible" also adds each row's hidden partner.
- **D4** notices in English and Dutch at least, plus the languages whose headers were verified; **D5** known rows that
  cannot be imported (product change, stock dividend, money-market fund) → one grouped warning; **D6** "Corporate
  Action Kosten" → a FEE with no asset; **D7** flatex-era withdrawals → a warning; **D8** DEGIRO's own
  `cannot_parse_reason`; **D9** `Transactions.csv` (the order list) is recognised, imports 0 rows and says to export
  the Account Statement — not a parse error; **D10** a new E2E spec `tx-import-degiro`.
- Off-track lessons: an unpaired exchange leg with an Order Id was counted as a fee — exchange-leg words are now
  checked first; the repository stores the sample with LF line endings (git `autocrlf`), so CRLF input is covered by
  bytes the tests build themselves, without a `.gitattributes` change.
- Details now live in [[features/F-013]] ("Release 2 plugin notes").

## Residuals

None of its own. Closing issue #35 at release is backlog P-7.

## Wiki pages updated

- [[features/F-013]] — DEGIRO notes.

## Source files

| Role | Path |
|------|------|
| Plan | `LibreFolio_developer_journal/Release_2/phases/31_brimDegiro/plan-phase00BrimDegiro.prompt.md` |
| Plugin | `backend/app/services/brim_providers/broker_degiro.py` |
| Wizard pairing | `frontend/src/lib/utils/transactions/importPairs.ts` |
| Tests | `backend/test_scripts/test_external/test_brim_degiro.py` |
| E2E | `frontend/e2e/transactions/tx-import-degiro.spec.ts` |
| User doc | `mkdocs_src/docs/user/transactions/import/degiro.en.md` |
