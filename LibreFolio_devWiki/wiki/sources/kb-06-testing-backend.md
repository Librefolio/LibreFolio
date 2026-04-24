---
title: "Knowledge Base: Backend Testing"
category: source
source_type: knowledge_base
date_ingested: 2026-04-24
original_path: LibreFolio_developer_journal/knowledge_base/06_testing_backend.md
tags: [testing, backend, pytest, api, coverage, providers]
related_features: [F-068]
---

# Source: Knowledge Base 06 — Backend Testing Reference

## Summary

Comprehensive backend test architecture guide covering: test structure (7 categories across `backend/test_scripts/`), `_TestingServerManager` (uvicorn as thread, not subprocess, for pytest-cov coverage tracking on port 8001), 276+ API tests, mock data via `populate_mock_data.py`, 3-layer coverage (backend/frontend/combined), provider filtering (`--providers`/`--exclude-providers` via regex discovery), and yfinance retry logic with exponential backoff.

## Key insights extracted

- **Backend test isolation** (each test creates its own user via `unique_id()`) → [[concepts/backend-test-isolation]] created
- **Coverage tracking architecture** (uvicorn in thread, not subprocess, enables pytest-cov) → [[features/F-068]] enriched
- **Test server on port 8001** (isolated from production port 8000) → [[features/F-068]] enriched
- **Mock data deterministic** (`populate_mock_data.py` creates e2e_test_user, 3 brokers, 4 assets, 10+ transactions) → [[features/F-068]] enriched
- **Provider filtering** (dynamic regex discovery without importing modules, avoids cache/logger side effects) → [[features/F-068]] enriched
- **Coverage analysis** (uncovered functions classification HIGH/MEDIUM/LOW/INFRA) → [[features/F-068]] enriched

## Wiki pages updated

- [[features/F-068]] — Backend API Tests — added structure, TestingServerManager, coverage architecture, provider filtering, mock data
- [[concepts/backend-test-isolation]] — created new concept page for test isolation pattern (unique_id, no cross-test state)

## Source files

| Role | Path |
|------|------|
| Source KB file | `LibreFolio_developer_journal/knowledge_base/06_testing_backend.md` |
| Test server manager | `backend/test_scripts/test_server_helper.py` |
| Test utilities | `backend/test_scripts/test_utils.py` |
| Mock data | `backend/test_scripts/test_db/populate_mock_data.py` |
| API tests directory | `backend/test_scripts/test_api/` |
| Test runner | `scripts/test_runner.py` |
| Coverage config | `.coveragerc` |
| Coverage analysis | `scripts/coverage_analysis.py` |
