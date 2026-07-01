---
title: "Phase 07 Standalone — PWA Mobile Optimizations (archive)"
category: source
source_type: plan
date_ingested: 2026-06-30
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Standalone/plan-pwa-mobile-optimizations.prompt.md
tags: [pwa, mobile, css, manifest, service-worker, install-button, ios, android, svelte5]
related:
  - features/F-098
  - sources/r2-parallel-features-pwa-borsa-fx
---

# Source: Phase 07 Standalone — PWA Mobile Optimizations (archive)

## Summary

This is the archived standalone plan for the PWA and mobile optimization work, now located at `phases/phase-07-subplan/Standalone/`. The implementation was completed 2026-05-26 and previously ingested as part of `r2-parallel-features-pwa-borsa-fx` (2026-06-02) using the root-level plan path. This entry re-anchors it at the archived location with two additional bugfixes discovered post-completion.

> **See**: [[sources/r2-parallel-features-pwa-borsa-fx]] for the detailed source page — that page covers all implementation details, design decisions, and source file mapping.

## Additional Bugfixes (post-completion, captured in archive plan)

### Bugfix 2026-05-27 — HelpMenu Install Button Not Reactive
- **Cause**: `isOpen` was `let` (plain) but file used Svelte 5 runes mode → not reactive. `{#if isOpen}` never updated.
- **Fix**: `let isOpen = false` → `let isOpen = $state(false)`
- **Also**: `apple-mobile-web-app-capable` meta tag deprecated → replaced with `mobile-web-app-capable`

### Bugfix 2026-05-27 — Install Button Never Appeared (Race Condition)
- **Cause**: `beforeinstallprompt` fired BEFORE `onMount` registered the listener → `canInstall` stayed false.
- **Fix strategy**:
  1. Early capture in `app.html`: `window.__pwaInstallPrompt` captures the event before Svelte mounts
  2. `onMount` reads `window.__pwaInstallPrompt` as fallback
  3. Install button now **always visible** (except in standalone mode)
  4. Click handler: if `deferredPrompt` → native prompt; if iOS → share instructions; otherwise → hint "look for ⊕ in address bar"
  5. Added i18n key `help.installAppDesktop` (EN/IT/FR/ES)

## Key Takeaways

- Service Worker: offline fallback only — no app caching (financial data freshness critical)
- HTTP LAN: manifest + standalone work without HTTPS; only Chrome auto-banner requires HTTPS
- iOS never auto-prompts → manual instructions always provided
- PWA icons generated at build time by `dev.py generate_pwa_icons()` from `logo_square.png`
- `display: standalone` in manifest removes browser chrome and navigation gestures

## Wiki Pages Updated

- [[features/F-098]] — status remains `implemented`

## Source files

| Role | Path |
|------|------|
| Archived plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Standalone/plan-pwa-mobile-optimizations.prompt.md` |
| Service Worker | `frontend/static/service-worker.js` |
| Manifest | `frontend/static/manifest.json` |
| Install logic | `frontend/src/lib/components/layout/HelpMenu.svelte` |
| App HTML | `frontend/src/app.html` |
| App CSS | `frontend/src/app.css` |
| Icon generation | `dev.py` (generate_pwa_icons) |
