---
title: "Phase 0 / 26 — BRIM Danske Bank: the report-set pilot, CSV encoding, steps 4–9"
category: source
source_type: plan
date_ingested: 2026-10-09
original_path: LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/
tags: [phase0, release2, brim, danske-bank, report-sets, encoding, upload, issue-26, workstream-l]
related:
  - decisions/brim-report-sets
  - features/F-103
  - problems/brim-text-exports-hardcoded-utf8
  - problems/brim-compatible-plugins-frozen-at-upload
  - problems/stale-frontend-after-update-html-cached
  - features/F-013
  - decisions/brim-broker-scoped
---

# Source: Phase 0 / 26 — BRIM Danske Bank

## Summary

Ten files (~5 600 lines: an analysis, the report-set design, the main plan, the Step 4 implementation plan, steps
5–9 and a reply drafted for issue #26), archived on 2026-10-09. Danske Bank is the pilot of **report sets** — one
import built from several exports of the same bank. The folder also carries the CSV-encoding fix (2026-09-28,
`6ea71ea8d`) and five follow-ups: plugin re-detection (`b0abeb07d`), a damaged workbook preview that answered 500
(`c3e6fa0a8`), partly ticked sets (`955148dfb`), the set card on phones (`038109e91`) and a stale cached frontend
(`333bfc985`).

## Key takeaways

- The report-set model and its decisions (derived combined file; a set = files uploaded together, same broker, same
  set plugin; D-S31 rejected; truth points and gap fix): [[decisions/brim-report-sets]], [[features/F-103]].
- Never assume an encoding: [[problems/brim-text-exports-hardcoded-utf8]].
- A capability list stored at upload needs the version that computed it: [[problems/brim-compatible-plugins-frozen-at-upload]].
- The entry HTML must revalidate, the hashed chunks may be immutable: [[problems/stale-frontend-after-update-html-cached]].
- Danske plugin decisions: the value date (D5); `Tuotto` → DIVIDEND (D6); notices in Finnish (D7).
- Step 6: a damaged workbook preview now answers 400 (`UnreadablePreviewError`, `backend/app/services/file_preview.py`);
  the developer **rejected** restricting the upload formats (backlog L4).
- Gotcha recorded by the design (§3): the real save path is `/transactions/commit`; a
  `/brokers/{id}/transactions/bulk` endpoint does not exist.

## Residuals (backlog 38)

L1 a deleted set member mishandled · L2 negative adjustments and invested capital · L3 Crédit Agricole as a report set
· L4 a `.json` upload overwritten by its sidecar · L5 `get_file_path` on the event loop · L6 the rejection message shows
the saved name · L7 a forced set plugin on an unreadable file · L8 `auto` falls back to Generic CSV (undocumented) · L9
`clean_data_dirs` reports zero files.

## Wiki pages updated

- [[decisions/brim-report-sets]], [[features/F-103]], [[problems/brim-text-exports-hardcoded-utf8]],
  [[problems/brim-compatible-plugins-frozen-at-upload]], [[problems/stale-frontend-after-update-html-cached]] — new.
- [[features/F-013]] — encoding rule, roles, detection; stale `detected()` and "Generic CSV fallback" corrected.
- [[decisions/brim-broker-scoped]] — `batch_id`, set scope, `combined_into`.

## Source files

| Role | Path |
|------|------|
| Analysis | `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/analysis-phase00BrimDanskeBank.md` |
| Report-set design (§10 decisions) | `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/design-phase00BrimReportSets.md` |
| Main plan (§4 encoding) | `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBank.prompt.md` |
| Step 4 implementation | `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBankStep4Implementation.prompt.md` |
| Step 5 re-detection | `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBankStep5PluginRedetection.prompt.md` |
| Step 6 upload robustness | `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBankStep6UploadRobustness.prompt.md` |
| Step 7 button and R6 | `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBankStep7ButtonAndR6.prompt.md` |
| Step 8 mobile card | `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBankStep8MobileCard.prompt.md` |
| Step 9 stale frontend | `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBankStep9StaleFrontend.prompt.md` |
| Danske Bank plugin | `backend/app/services/brim_providers/broker_danske_bank.py` |
| File preview (400 on a damaged workbook) | `backend/app/services/file_preview.py` |
| Plugin tests | `backend/test_scripts/test_external/test_brim_danske_bank.py` |
| User doc | `mkdocs_src/docs/user/transactions/import/danske-bank.en.md` |
| Developer doc | `mkdocs_src/docs/developer/backend/brim/danske_bank.md` |
