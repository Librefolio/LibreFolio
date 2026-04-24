---
title: "Knowledge Base: Frontend Testing (Playwright E2E)"
category: source
source_type: knowledge_base
date_ingested: 2026-04-24
original_path: LibreFolio_developer_journal/knowledge_base/07_testing_frontend.md
tags: [testing, frontend, playwright, e2e, coverage, gallery]
related_features: [F-067, F-074]
---

# Source: Knowledge Base 07 — Frontend Testing Reference (Playwright E2E)

## Summary

Complete Playwright E2E testing guide covering: 181+ tests across 7 categories, 2 projects (desktop Chrome + mobile Chromium with iPhone viewport), fixtures (`auth-helpers.ts`, `db-helpers.ts`, `test-users.ts`), backend coverage tracking via 3-level SIGTERM architecture (`gracefulShutdown` → `exec` → `os.execvpe()` chain), gallery screenshot automation with deterministic DB state, and strict conventions (`data-testid` always, never CSS classes or text).

## Key insights extracted

- **data-testid mandatory rule** (never CSS classes/text, essential for i18n safety) → [[concepts/e2e-data-testid-rule]] created
- **Backend coverage during E2E** (gracefulShutdown + exec chain ensures SIGTERM reaches `coverage run`) → [[features/F-067]] enriched
- **Mobile uses Chromium** (not WebKit on Linux due to stability issues) → [[features/F-067]] enriched
- **Gallery prerequisites** (deterministic DB via `--with-static --with-reports`, Linux needs `playwright install-deps`) → [[features/F-074]] enriched
- **Graceful skip pattern** (test.skip() when data missing, not hard failure) → [[features/F-067]] enriched
- **Fixtures for DB management** (`resetDatabase()`, `populateDatabase()`) → [[features/F-067]] enriched

## Wiki pages updated

- [[features/F-067]] — Playwright E2E Tests — added structure, 2-project config, fixtures, backend coverage architecture, conventions
- [[features/F-074]] — E2E Test Gallery — added prerequisites, deterministic DB, Linux deps
- [[concepts/e2e-data-testid-rule]] — created new concept page for data-testid convention

## Source files

| Role | Path |
|------|------|
| Source KB file | `LibreFolio_developer_journal/knowledge_base/07_testing_frontend.md` |
| Playwright config | `frontend/playwright.config.ts` |
| Auth helpers | `frontend/e2e/fixtures/auth-helpers.ts` |
| DB helpers | `frontend/e2e/fixtures/db-helpers.ts` |
| Test users | `frontend/e2e/fixtures/test-users.ts` |
| Gallery spec | `frontend/e2e/gallery.spec.ts` |
| E2E tests directory | `frontend/e2e/` |
| Test runner | `scripts/test_runner.py` |
