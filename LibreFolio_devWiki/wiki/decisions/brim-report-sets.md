---
title: "BRIM report sets: the exports uploaded together are combined into one derived file, and the wizard parses that"
category: decision
status: resolved
date: 2026-09-28
tags: [backend, frontend, brim, import, report-sets, danske-bank, gap-fix, upload, issue-26]
related: [features/F-103, features/F-012, features/F-013, decisions/brim-broker-scoped, decisions/brim-parser-only, decisions/brim-fake-asset-id, entities/import-wizard-modal, workflows/brim-import-flow, problems/brim-compatible-plugins-frozen-at-upload, sources/phase00-brim-danske-bank-2026-10]
---

# Decision: report sets

## Context

Some banks do not export one file that contains everything. Danske Bank (issue #26) gives a **custody** export
(XLSX: positions and trades) and a **cash** export (CSV: the account movements); neither alone is a complete import,
and the two overlap at their edges. BRIM was built around "one file → one plugin → one parse"
([[decisions/brim-parser-only]]). The design (`design-phase00BrimReportSets.md`, §10, D-S1…D-S31) answers how
several files become one import without changing the single-file plugins.

## Decisions

- **D-S1 — a derived "combined" file.** A set plugin merges its members into one combined file
  (`combine(members) → BRIMCombinedTable`); the wizard then works only on that file, through the ordinary
  parse/review path. Single-file plugins do not change.
- **D-S22 — a set is born at upload.** It is the files uploaded **together** (same `batch_id`, one per wizard
  session) for the **same broker** and recognised by the **same set plugin**. Different uploads never mix.
  - **Rejected — D-S31**, completing a set from files uploaded earlier: withdrawn because it would turn the file
    archive into hidden memory.
- **D-S4** — parsing one member on its own answers 422. **D-S6** — the combined file is reused while its members and
  the plugin version are unchanged. **D-S26** — `combine` is pure; the broker history start (`H0`) is applied at
  parse time. **D-S28** — overlapping files of the same role: identical ones are merged, otherwise the newest wins,
  with a notice.
- **Roles** are declared by the plugin (`report_roles`: `code`, `required`, `multiple`, `extensions`,
  `max_history`, `must_cover`); `detect_role` tells which role a file plays; Danske declares `custody` (XLSX) and
  `cash` (CSV, which must cover the custody period).
- **Truth points and gap fix** (D-S13…D-S16, D-S19/27): the combined parse returns the bank's own statements — cash
  balances and positions at given dates. The **checkpoint** is the day before the first day of the custody file;
  trades settled in its first ≤ 5 business days are folded into it (replacing an earlier idea of moving `T0`
  forward). Before the hand-off, `POST /brokers/import/gap-fix` compares each checkpoint with what LibreFolio will know
  at that date and proposes **only the difference**, as ordinary transactions tagged `gap_fix`; the end of the last
  segment is only **verified**, never corrected; the endpoint writes nothing.
- **D-S21** — extending history backwards with an older set is postponed.
- Wizard (Step 7, R6): a set ticked only in part blocks the analysis; the "Exclude from import" button was removed.

## Consequences

- A new multi-export bank needs a set plugin (roles, `detect_role`, `describe_member`, `combine`), not a new
  pipeline. Crédit Agricole as a report set is backlog L3.
- Files uploaded by 1.1.0 have no `batch_id`: they must be uploaded again, together.
- The upload contract gained `batch_id` (a UUID, else 422) and files gained `combined_into` — see
  [[decisions/brim-broker-scoped]].

## Links

- [[features/F-103]] · [[workflows/brim-import-flow]] · [[entities/import-wizard-modal]]
- Source: [[sources/phase00-brim-danske-bank-2026-10]]

## Source files

| Role | Path |
|------|------|
| Set service (`collect_members`, `preview_set`, `combine_set`, `apply_history`) | `backend/app/services/brim_report_sets.py` |
| Gap fix (`compute_gap_fix`) | `backend/app/services/brim_gap_fix.py` |
| Plugin hooks (`report_roles`, `detect_role`, `describe_member`, `combine`) | `backend/app/services/brim_provider.py` |
| `BRIMReportRole`, `batch_id`, `combined_into` | `backend/app/schemas/brim.py` |
| Upload with `batch_id`; `/sets/preview`, `/sets/combine`, `/gap-fix` | `backend/app/api/v1/brokers.py` |
| Danske Bank set plugin | `backend/app/services/brim_providers/broker_danske_bank.py` |
| Wizard set logic | `frontend/src/lib/utils/transactions/importReportSets.ts` |
| Set card, gap-fix step | `frontend/src/lib/components/transactions/import/ReportSetCard.svelte` |
| Gap-fix step | `frontend/src/lib/components/transactions/import/GapFixStep.svelte` |
| Tests | `backend/test_scripts/test_services/test_brim_report_sets.py` |
| Gap-fix tests | `backend/test_scripts/test_services/test_brim_gap_fix.py` |
| Developer doc ("Report sets") | `mkdocs_src/docs/developer/backend/brim/architecture.md` |
| Design (§10 decisions) | `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/design-phase00BrimReportSets.md` |
