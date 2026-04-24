---
title: "Data Separation: prod/ and test/ Isolated Directories"
category: decision
status: resolved
date: 2026-01-26
tags: [backend, testing, data, isolation, devops]
related_features: [F-064]
---

# Decision: Complete prod/test Data Isolation

## Context
Originally both prod and test used the same `backend/data/` directory with only different SQLite filenames (`app.db` vs `test_app.db`). As the project grew (uploads, BRIM files, logs), shared paths created contamination risk.

## Problem
1. Test uploads (`uploads/`) and BRIM files (`brim/`) landed in same folder as prod — impossible to clean test data without risking prod
2. No structural isolation: a misrouted test could write to prod
3. Hard to gitignore test data selectively

## Decision
Complete directory separation:
```
backend/data/
├── prod/     → SQLite, uploads/, brim/, logs/
└── test/     → same structure, content gitignored, structure tracked
```

Configured via environment variable or `get_data_dir(mode)` in `backend/app/config.py`.
`./dev.py server --test` switches all paths to `test/`.

## Consequences
- Clean `./dev.py db create-clean --test` wipes only test DB
- Prod and test files never share a directory
- Initial migration: existing paths needed updating in config

## Resolved
✅ Completed 2026-02-06 — `plan-data-separation.md` (~3 hours implementation)

## Source files

| Role | Path |
|------|------|
| Config module | `backend/app/config.py` |
| Prod data dir | `backend/data/prod/` |
| Test data dir | `backend/data/test/` |
| mkdocs | `mkdocs_src/docs/developer/architecture/database/index.md` |
