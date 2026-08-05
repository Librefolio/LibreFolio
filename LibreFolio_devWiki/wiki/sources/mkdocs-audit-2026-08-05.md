---
title: "MkDocs English Source Audit 2026-08-05"
category: source
source_type: journal_entry
date_ingested: 2026-08-05
original_path: LibreFolio_developer_journal/Release_2/Phase_0/05_cleanAudit/mkdocsAudit/00_INDEX.md
tags: [audit, mkdocs, documentation, backend, frontend, ai-export, fx, admin]
related:
  - sources/wiki-audit-2026-06-18
  - concepts/mkdocs-suffix-i18n
  - decisions/ai-export-versioned-snapshot-boundary
---

# Source: MkDocs English Source Audit 2026-08-05

## Summary

Read-only audit of every currently published non-developer English MkDocs page against
the current backend, frontend, API, CLI, configuration, and test behavior. The audit
covered 182/182 pages across nine bounded domains and recorded 64 evidence-backed
documentation discrepancies: 6 critical, 33 major, 20 minor, and 5 info. The
developer guide was deliberately excluded pending a fresh baseline and explicit user
authorization.

## Key Takeaways

- User-facing UI documentation drift is concentrated in dashboard/assets/settings,
  BRIM import wizard, FX detail flows, and synthetic benchmark defaults.
- Four admin critical records expose two functional settings no-ops
  (`enable_registration`, `require_email_verification`), one invalid documented CLI
  command, and one dead bootstrap URL.
- Documentation claims must be separated from purely educational finance theory:
  theory-only pages were not treated as code defects unless they asserted
  LibreFolio-specific behavior.
- Beta Risk Analysis surfaces were excluded from documentation-gap findings because
  their absence from public documentation is intentional.
- The published i18n nav exactly covered all 182 audited EN pages; MkDocs build
  passed. A cross-boundary link checker alert on `${lang` was traced to a nested
  template-literal parser false positive, not a broken user link.
- Second-order taxonomy separates 13 promises achievable by extending existing
  systems, 4 requiring a new library/system/external integration, and 25 capabilities
  already present but undocumented; 21 records remain editorial-only and 1 is
  product-ambiguous.

## Wiki Pages Updated

- [[sources/mkdocs-audit-2026-08-05]] - records scope, findings, validation, and the
  deferred developer-guide boundary.

## Source files

| Role | Path |
|---|---|
| Audit index and cross-report synthesis | `LibreFolio_developer_journal/Release_2/Phase_0/05_cleanAudit/mkdocsAudit/00_INDEX.md` |
| Reproducible source snapshot | `LibreFolio_developer_journal/Release_2/Phase_0/05_cleanAudit/mkdocsAudit/00_BASELINE.md` |
| Domain findings | `LibreFolio_developer_journal/Release_2/Phase_0/05_cleanAudit/mkdocsAudit/01_user-core.md` through `07_site-community-gallery.md` |
| Capability taxonomy | `LibreFolio_developer_journal/Release_2/Phase_0/05_cleanAudit/mkdocsAudit/08-functionality-gap-taxonomy.md` |
| Published documentation navigation | `mkdocs_src/mkdocs.yml` |
