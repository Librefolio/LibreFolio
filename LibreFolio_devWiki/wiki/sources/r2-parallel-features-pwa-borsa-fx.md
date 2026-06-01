---
title: "Batch 3 — Parallel Features: PWA, Port 60/40, Borsa Italiana, FX Provider Removal Fix"
category: source
source_type: commits
date_ingested: 2026-06-02
original_path: (multiple commits — no single plan file)
tags: [pwa, mobile, offline, ports, infrastructure, assets, providers, borsa-italiana, fx, sentinel, ux]
related:
  - features/F-098
  - features/F-099
  - features/F-019
  - features/F-015
  - features/F-025
  - decisions/port-6040-scheme
---

# Source: Batch 3 — Parallel Features (PWA, Port 60/40, Borsa Italiana, FX Fix)

## Summary

Four independent features/fixes developed in a parallel terminal without formal roadmap plan chains. Ingested together as a batch since they share the same delivery window (post R2-Walktest, pre Phase 8).

---

## 1. PWA Support (Progressive Web App)

**Commits**: `b0bfde60`, `f6023a73`, `6db90b73`, `2b0142f0`
**Plan file**: `LibreFolio_developer_journal/RoadmapV4_UI/plan-pwa-mobile-optimizations.prompt.md`
**Status**: ✅ Completed (2026-05-26)

### What was done

1. **Mobile CSS optimizations**: no-zoom (`maximum-scale=1, user-scalable=no`), `overscroll-behavior: contain`, `touch-action: manipulation`, `-webkit-tap-highlight-color: transparent`
2. **PWA Manifest**: `frontend/static/manifest.json` — `display: standalone`, theme colors, icons 192×192 and 512×512
3. **Service Worker**: offline fallback page only (no app caching). Auto-versioned via `dev.py stamp_service_worker()` with MD5 hash
4. **Install button in HelpMenu**: `beforeinstallprompt` interception for Chrome; iOS manual instructions; Android HTTPS hint; desktop fallback
5. **Dynamic theme-color meta tag**: synced with dark/light mode toggle (dark = `#156534` sidebar green)
6. **iOS safe-area-inset-top**: `.safe-top` / `.safe-top-offset` CSS classes for standalone mode (Sidebar, Header, login toolbar)
7. **Flag emoji fix**: reordered `.emoji-flag` font-family — Apple Color Emoji first for iOS, Noto fallback for Windows/Linux
8. **Icon generation**: `dev.py generate_favicon()` extended — PIL generates 192/512 icons with 12% white padding from `logo_square.png`
9. **Documentation**: user docs (`pwa.en.md`), developer docs (`developer/frontend/pwa.md`), FAQ entry

### Key design decisions
- **No app caching**: Service Worker only handles offline fallback page — avoids stale cache bugs for a financial app where data freshness is critical
- **HTTP LAN support**: manifest + standalone work without HTTPS; only Chrome auto-install banner requires HTTPS (documented Tailscale workaround)
- **iOS limitation accepted**: iOS never shows auto-install banner → manual "Share → Add to Home" instructions in UI

### Source files
| Role | Path |
|------|------|
| Service Worker | `frontend/static/service-worker.js` |
| Manifest | `frontend/static/manifest.json` |
| Offline page | `frontend/static/offline.html` |
| Install logic | `frontend/src/lib/components/layout/HelpMenu.svelte` |
| App HTML (meta tags) | `frontend/src/app.html` |
| Icon generation | `dev.py` (generate_favicon function) |
| CSS safe-area | `frontend/src/app.css` |
| User docs | `mkdocs_src/docs/user/pwa.en.md` |
| Dev docs | `mkdocs_src/docs/developer/frontend/pwa.md` |
| Plan | `LibreFolio_developer_journal/RoadmapV4_UI/plan-pwa-mobile-optimizations.prompt.md` |

---

## 2. Port 60/40 Scheme

**Commit**: `a7b30d52`
**Status**: ✅ Completed

### What was done

Migrated all port defaults from `8000/8001/8002` to `6040/6041/6042`.

| Port | Role |
|------|------|
| 6040 | Production server |
| 6041 | Test server |
| 6042 | MkDocs dev server |

**Mnemonic**: the "60/40 rule" — 60% equities, 40% bonds — the iconic asset allocation principle. Instantly memorable for a portfolio tracker application.

### Files touched
- `.env.example`, `backend/app/config.py`, `dev.py`, `Dockerfile`, `docker-compose.yml`
- All E2E test files (`global-setup.ts`, spec files)
- Backend test helpers (`test_server_helper.py`)
- Documentation (README, skills, wiki pages)
- CI / GitHub instructions

### Source files
| Role | Path |
|------|------|
| Config defaults | `backend/app/config.py` |
| Docker compose | `docker-compose.yml` |
| Dockerfile | `Dockerfile` |
| Dev CLI | `dev.py` |
| Env template | `.env.example` |

---

## 3. Borsa Italiana Provider

**Commit**: `7fd9c6df`
**Status**: ✅ Completed

### What was done

New asset source provider for the Italian stock exchange (borsaitaliana.it). Supports:
- **Stocks** (azioni)
- **Bonds** (obbligazioni)
- **ETFs**

Uses the `borsa-italiana-scraping` library (optional dependency). Follows the standard `@register_provider` auto-discovery pattern. Implements all `AssetSourceProvider` abstract methods:
- `search()` — multi-instrument search
- `get_current_value()` — live price
- `get_historical_data()` — OHLCV history
- `get_metadata()` — classification, geographic/sector data
- `shutdown()` — closes shared HTTP session

### Key implementation details
- Shared `Sessione` instance across calls (closed on `shutdown()`)
- Graceful degradation: if `borsa-italiana-scraping` not installed, provider silently unavailable
- 541 lines — largest single-file provider in the codebase
- Developer documentation added: `developer/backend/assets/provider_borsa_italiana.md`

### Source files
| Role | Path |
|------|------|
| Provider implementation | `backend/app/services/asset_source_providers/borsa_italiana.py` |
| Provider schema (enum) | `backend/app/schemas/provider.py` |
| Service registry | `backend/app/services/asset_source.py` |
| Frontend search integration | `frontend/src/lib/components/assets/AssetSearchAutocomplete.svelte` |
| Dev docs | `mkdocs_src/docs/developer/backend/assets/provider_borsa_italiana.md` |
| Plugin guide | `mkdocs_src/docs/developer/architecture/patterns/asset_plugin_guide.md` |

---

## 4. FX Provider Removal Fix

**Commit**: `0d7607e8`
**Status**: ✅ Completed

### What was done

Fixed FX provider removal flow + added UX improvements to the FX detail page editor:

**Backend fixes**:
- **Delete-before-create in edit mode**: stale routes no longer persist when providers are reordered
- **MANUAL sentinel auto-reinstate**: `priority=None` deletes now correctly trigger MANUAL sentinel re-insertion
- **Skip redundant MANUAL POST**: when user removes all providers, only DELETEs are sent (MANUAL creation is automatic server-side)

**Frontend UX**:
- **"Insert Manually" button**: shown alongside "Sync" when FX chart has no data — gives user a direct path to manual data entry
- **Chart interaction tip**: editor header shows "dblclick / long-press" hint for mobile/desktop data point insertion

### Source files
| Role | Path |
|------|------|
| Backend FX endpoint | `backend/app/api/v1/fx.py` |
| FX pair modal | `frontend/src/lib/components/fx/FxPairAddModal.svelte` |
| FX detail page | `frontend/src/routes/(app)/fx/[pair]/+page.svelte` |
| Asset detail page (tip) | `frontend/src/routes/(app)/assets/[id]/+page.svelte` |

---

## Cross-cutting observations

1. **Provider pattern consistency**: Borsa Italiana follows the exact same `@register_provider` + `AssetSourceProvider` ABC pattern as yfinance, JustETF, CSS Scraper. The pattern is now proven across 5+ providers.
2. **FX MANUAL sentinel reliability**: the removal fix confirms the sentinel auto-insert/remove logic (F-019) handles all edge cases including bulk-delete scenarios.
3. **PWA as infrastructure**: PWA support is infrastructure (not a feature users "configure") — once installed, it's invisible. No backend changes needed.
4. **Port mnemonic**: choosing domain-meaningful port numbers improves developer ergonomics with zero runtime cost.
