---
title: "API v1 Router"
category: entity
type: module
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
| `address_probe_image` | `address_probe_image.router` | The public-address probe as an image (`/auth/address-probe.png`) |
| `ai_export` | `ai_export.router` | AI Export catalog and snapshot ([[entities/ai-export-snapshot-service]]) |
| `settings` | `settings.router` | [[F-005]] / [[F-006]] User & global settings |
| `plugin_settings` | `plugin_settings.router` | Plugin settings (`/settings/plugins`) |
| `system` | `system.router` | Health check, version, system info |
| `uploads` | `uploads.router` | [[F-011]] File upload/list/delete |
| `pdf_fonts` | `pdf_fonts.router` | The PDF viewer's CJK fonts, served by the instance |
| `users` | `users.router` | [[F-002]] User management |
| `email` | `email.router` | Email state and test email (admin) — [[domains/email]] |
| `security` | `security.router` | The checks of the admin «Security» tab |
| `fx` | `fx.fx_router` | [[F-016]] / [[F-017]] / [[F-023]] FX domain |
| `assets` | `assets.asset_router` | [[F-024]] / [[F-027]] / [[F-031]] Asset domain |
| `transactions` | `transactions.tx_router` | [[F-046]] Transaction domain |
| `brokers` | `brokers.broker_router` | [[F-009]] / [[F-010]] Broker domain |
| `backup` | `backup.backup_router` | [[F-073]] Backup & restore ([[entities/backup-router]]) |
| `panel` | `panel.panel_router` (prefix `/panel`) | Hosting panel: the setup status of the instance |
| `portfolio_api` | `portfolio_api.portfolio_router` | Portfolio report, lots, charts |
| `risk` | `risk.router` | Risk analytics |
| `signals` | `signals.signals_router` | Technical signals |
| `tools` | `tools.router` | Tool plugins |
| `utilities` | `utilities_router` | Country/sector/currency reference lists |

> 2026-11-07 lint: table realigned with `router.py` (the 2026-04-24 list had 11 of today's 22 sub-routers). The
> aggregate router carries four guard dependencies, read in this order: `refuse_when_blocked`,
> `refuse_when_awaiting_restore`, `refuse_when_restore_interrupted` (`instance_block.py`) and `refuse_when_over_limit`
> (`user_limit.py`, `LIBREFOLIO_MAX_USERS`).

## Notes
- Mounted at `/api/v1` (`API_V1_PREFIX`) in `backend/app/main.py`
- The Zodios client ([[F-066]]) is regenerated from this router's OpenAPI schema via `./dev.py api sync`
- Adding a new domain = create a module in `backend/app/api/v1/`, register here

> This file was originally created as a stub. Populated 2026-04-24.

## Source files

| Role | Path |
|------|------|
| API v1 router | `backend/app/api/v1/router.py` |
| FastAPI main app | `backend/app/main.py` |
| All API modules | `backend/app/api/v1/` |
