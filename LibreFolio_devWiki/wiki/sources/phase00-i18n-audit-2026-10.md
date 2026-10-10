---
title: "Phase 0 / 29 — the Release 2 i18n audit (S0–S22)"
category: source
source_type: plan
date_ingested: 2026-10-09
original_path: LibreFolio_developer_journal/Release_2/phases/29_i18nAudit/plan-phase00I18nAudit.prompt.md
tags: [phase0, release2, i18n, audit, tooling, svelte-i18n, workstream-o]
related:
  - problems/i18n-audit-false-dead-and-false-used
  - problems/svelte-i18n-formatter-cache-ignores-locale
  - problems/i18n-loading-gate-remounts-app
  - decisions/i18n-key-rationalization
  - features/F-008
---

# Source: Phase 0 / 29 — the i18n audit

## Summary

Workstream O audited the four catalogues end to end — unused keys, duplicates, plurals and the audit tool itself —
in 23 steps (S0–S22), archived on 2026-10-09. Its findings were filed while it ran (2026-10-07): the usage audit was
wrong in both directions, svelte-i18n leaks plural rules across locales, and the language loading gate rebuilt the
whole app. Result recorded by the plan: 4 215 keys per language, 0 dead (re-counted on `en.json` at `586a4f0ea`:
4 215 leaf keys).

## Key takeaways

- The audit counted live keys as dead (wrappers, props, backend dictionaries, relative helpers) and absolved a whole
  namespace through one template literal; tests were counted as evidence. Rewritten to read product sources only,
  with one import hop, reachability from the SvelteKit entries and generated clients excluded:
  [[problems/i18n-audit-false-dead-and-false-used]].
- svelte-i18n 4.0.1 memoises its formatter by message text, so an ICU text identical in two catalogues keeps the
  first locale's rules: [[problems/svelte-i18n-formatter-cache-ignores-locale]] (gate:
  `frontend/src/lib/i18n/catalogIcuLocale.test.ts`; reporting it upstream is residual O-18).
- A slow catalogue load swapped the app for a placeholder: [[problems/i18n-loading-gate-remounts-app]].
- Duplicates follow the older rule — intentional when namespacing clarity beats DRY:
  [[decisions/i18n-key-rationalization]].

## Residuals (backlog 38)

O-1 … O-18 from this plan (phantom key families, files reported dead by knip, missing test hooks and test ids,
hard-coded English in the asset data editor, provider parameters without i18n, missing plurals, login network
errors in English, upstream report of the formatter cache) and O-19 / O-20 from
[[sources/phase00-feedback-contracts-runes-2026-09]].

## Wiki pages updated

- [[features/F-008]] — key count (840+ → 4 215), audit and library traps.
- The three problem pages above were filed on 2026-10-07; unchanged here.

## Source files

| Role | Path |
|------|------|
| Plan (S0–S22, residuals) | `LibreFolio_developer_journal/Release_2/phases/29_i18nAudit/plan-phase00I18nAudit.prompt.md` |
| Audit command | `frontend/scripts/i18n-audit.py` |
| Usage analysis | `scripts/i18n_usage.py` |
| Catalogues | `frontend/src/lib/i18n/en.json` |
| ICU/locale gate | `frontend/src/lib/i18n/catalogIcuLocale.test.ts` |
| Developer doc | `mkdocs_src/docs/developer/frontend/i18n.md` |
