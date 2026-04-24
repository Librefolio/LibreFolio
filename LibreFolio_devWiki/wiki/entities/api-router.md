---
title: "API v1 Router"
category: entity
tags: [backend, api, routing, infrastructure]
related_features: [F-001, F-009, F-011, F-016, F-024, F-046, F-063, F-073]
---

# Entity: API v1 Router

**File**: `backend/app/api/v1/router.py`

The central aggregator for all REST API endpoints in LibreFolio. Registers sub-routers in priority order at the `/api/v1` prefix.

## Registered sub-routers (in order)

| Module | Router var | Domain |
|--------|-----------|--------|
| `auth` | `auth.router` | [[F-001]] Auth & sessions (no prefix, uses `/auth`) |
| `settings` | `settings.router` | [[F-005]] / [[F-006]] User & global settings |
| `system` | `system.router` | Health check, version, system info |
| `uploads` | `uploads.router` | [[F-011]] File upload/list/delete |
| `users` | `users.router` | [[F-002]] User management |
| `fx` | `fx.fx_router` | [[F-016]] / [[F-017]] / [[F-023]] FX domain |
| `assets` | `asset_router` | [[F-024]] / [[F-027]] / [[F-031]] Asset domain |
| `transactions` | `tx_router` | [[F-046]] Transaction domain |
| `brokers` | `broker_router` | [[F-009]] / [[F-010]] Broker domain |
| `backup` | `backup_router` | [[F-073]] Backup & restore |
| `utilities` | `utilities_router` | Country/sector/currency reference lists |

## Notes
- Mounted at `/api/v1` in `backend/app/main.py`
- The Zodios client ([[F-066]]) is regenerated from this router's OpenAPI schema via `./dev.py api sync`
- Adding a new domain = create a module in `backend/app/api/v1/`, register here

> This file was originally created as a stub. Populated 2026-04-24.

## Source files

| Role | Path |
|------|------|
| API v1 router | `backend/app/api/v1/router.py` |
| FastAPI main app | `backend/app/main.py` |
| All API modules | `backend/app/api/v1/` |
