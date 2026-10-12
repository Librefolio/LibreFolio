---
title: "Phase 0 / 05 — the clean audit of August 2026: what the code carried that newer code had replaced"
category: source
source_type: audit
date_ingested: 2026-10-12
original_path: LibreFolio_developer_journal/Release_2/phases/05_cleanAudit/
tags: [phase0, release2, audit, cleanliness, dead-code, coverage, async-io, tests]
related:
  - problems/asset-events-lost-on-price-cache-hit
  - concepts/test-isolation-classes
  - concepts/async-io-rule
---

# Source: Phase 0 / 05 — the clean audit

## Summary

A code-cleanliness audit of the backend, the frontend and the AI Export, dated 2026-08-07 on `dev_release2`: 17
numbered reports plus an index. Tools (ruff, coverage, N+1 and async-I/O checks) produced the evidence; each finding
was then traced by hand to one question — was this logic taken over by newer code (safe to remove), or not (discuss,
do not remove)?

## Key Takeaways

- **Mostly healthy**: one async-I/O violation in about 74,000 lines ([[concepts/async-io-rule]]), backend coverage
  90.48 %.
- **The debt sat in a few places**: three features shown to users but never wired (for example, `/auth/register` did
  not check the «Allow new user registration» switch), the pre-engine leftovers of `portfolio_service.py`, a 4,800-line
  `asset_source.py` (split later, P4-1), twelve dead `index.ts` barrels.
- **Remediation** in bands S1–S3 (`52c8d0d70`); report 16 lists features lost in redesigns, report 17 made the full
  suite pass end to end — finding [[problems/asset-events-lost-on-price-cache-hit]], and that `test all` could not pass
  by construction, because the services category recreated an empty database before the API category
  ([[concepts/test-isolation-classes]]).

## Source files

| Role | Path |
|------|------|
| README | `LibreFolio_developer_journal/Release_2/phases/05_cleanAudit/README.md` |
| Index of the reports | `LibreFolio_developer_journal/Release_2/phases/05_cleanAudit/INDEX.md` |
| The full suite made runnable | `LibreFolio_developer_journal/Release_2/phases/05_cleanAudit/17_stabilizzazione_suite_completa.md` |
| API runner (database populated before the API category) | `scripts/test_runner/_backend_api.py` |
