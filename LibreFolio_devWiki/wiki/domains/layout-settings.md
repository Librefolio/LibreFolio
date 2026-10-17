---
title: "Domain: LAYOUT & SETTINGS"
category: domain
features: [F-004, F-005, F-006, F-007, F-008, F-101, F-104, F-105, F-109]
status: stable
mkdocs: "developer/frontend/styling.md"
---

# Domain: LAYOUT & SETTINGS

> The foundational UX layer — the persistent shell, theming, language, and application configuration that frames every other domain.

## What it does

Every authenticated page in LibreFolio lives inside the same persistent shell: a collapsible sidebar listing the six main sections (Brokers, FX, Assets, Transactions, Files, Settings), a top header with the theme toggle and language selector, and a footer with the live price ticker. The shell is the first thing a user sees after logging in and the last thing they see before logging out. It enforces authentication: unauthenticated users are silently redirected to the login page before any page content loads.

Language and theme are user-level preferences, persisted both in the backend (`UserSettings`) and in `localStorage` for immediate startup without a round trip. The system supports four languages (EN, IT, FR, ES) with 840+ keys per language, all managed via the `dev.py i18n` CLI. Theme choices are dark, light, or auto (follows OS preference), implemented with Svelte 5 runes in `themeStore.svelte.ts`.

Global settings are a distinct concept from user settings: they are admin-managed, stored in a key-value table (`GlobalSetting`), and govern application-wide behaviour — session TTL, portfolio base currency, scheduler parameters, and future feature flags. Non-admin users can read the subset of global settings that affect their experience (e.g. base currency) but cannot modify them.

## Feature cluster

| Code | Feature | Layer | Role in domain | Status |
|------|---------|-------|----------------|--------|
| [[F-004]] | App Shell & Navigation (sidebar, header) | frontend | core — persistent container for all pages | implemented |
| [[F-005]] | User Settings (language, theme) | fullstack | core — per-user preferences persisted | implemented |
| [[F-006]] | Global Settings (admin-managed app config) | fullstack | core — app-wide config: base currency, session TTL, scheduler | implemented |
| [[F-007]] | Theme System (dark/light/auto) | frontend | support — CSS variables, Svelte 5 runes, localStorage | implemented |
| [[F-008]] | i18n System (EN/IT/FR/ES, 840+ keys) | frontend | core — all UI strings translated, 4 languages | implemented |
| [[F-101]] | Global Privacy Mode (hide values) | frontend | support — masks amounts at the formatter, device-scoped | documented |
| [[F-104]] | Recommend LibreFolio (social share) | frontend | support — share card in About and in the donation popup | documented |
| [[F-105]] | Guided onboarding (Welcome, intro tour, contextual guides) | fullstack | core — first-run setup and guides; the layout gate redirects to Welcome | documented |
| [[F-109]] | In-app changelog (localized by chapter) | frontend | support — the bundled CHANGELOG in a modal, from the sidebar's version and the About tab | documented |

## Architecture at a glance

```mermaid
graph TD
    Login -->|auth guard| Shell[App Shell<br/>+layout.svelte]
    Shell --> Sidebar[Sidebar.svelte]
    Shell --> Header[Header.svelte]
    Shell --> PageSlot[Page content slot]
    Header --> ThemeToggle[themeStore.svelte.ts<br/>dark/light/auto]
    Header --> LangSelector[LanguageSelector.svelte]
    LangSelector --> i18n[svelte-i18n<br/>en/it/fr/es.json]
    LangSelector -->|PATCH /users/me/settings| UserSettings[(UserSettings DB)]
    ThemeToggle -->|localStorage| Browser
    AdminSettings[Admin settings page] -->|PATCH /settings/global| GlobalSettings[(GlobalSetting DB)]
    GlobalSettings -->|read at startup| BackendConfig[JWT TTL, base currency,<br/>scheduler params]
```

## Key decisions that shaped this domain

- [[decisions/i18n-key-rationalization]] — intentional key duplication between namespaces is accepted when it improves clarity; the audit tool flags duplicates but does not enforce deduplication.
- [[decisions/sveltekit-over-react]] — the SvelteKit v4 rewrite (Phase 0) established this shell architecture; earlier versions used React + MUI, which had heavier theming complexity.
- Svelte 5 runes in `themeStore.svelte.ts` — the theme store is one of the first files migrated to `$state`/`$derived`; this decision established the `*.svelte.ts` pattern for all new rune-based stores.
- [[decisions/onboarding-versioned-progress-per-flow]] and [[decisions/automatic-popups-wait-for-guides]] — since
  1.2 the shell also hosts the onboarding: one versioned progress row per user and flow, and a popup lane that holds
  the donation and update prompts while a guide or a modal is on screen ([[F-105]]).
- The Settings tabs come from a registry (`settingsTabs.ts`, release 1.3, workstream A, lot A3, 15/10): the page
  names no tab, so a workstream adds its tab with one entry (`id`, `order`, `visible(ctx)`, `props(ctx)`,
  `alignEnd`), and an admin-only tab is hidden from everyone else. How-to in the developer page
  `frontend/components/features/settings.md#tab-registry`.

## Known problems / limitations

- [[problems/flag-emoji-windows]] — flag emoji (language selector, currencies) print as letter pairs on Windows, whose emoji font has no flags; resolved by the global flags-only face `'LF Flags'` (`static/lf-flags.css`), which leads every font stack: Apple flags on Apple devices, the self-hosted Noto flags subset elsewhere. ECharts text is not covered yet.
- [[problems/liveticker-header-crash]] — LiveTicker in `Header.svelte` caused a crash on navigation in early versions; resolved by lifecycle guard.

## What comes next

- [[F-092]] Default Language/Currency for New Users — admin sets a system default that pre-fills new user preferences; small addition to the Global Settings page. *Delivered (`2a8e5bf1c`, 2026-07-17) and documented in `admin/settings` (lint 2026-10-12).*
- No major structural changes planned — this domain is intentionally stable as the foundation for all other domains.

## Source files

| Role | Path |
|------|------|
| Primary mkdocs | `mkdocs_src/docs/developer/frontend/styling.md` |
| i18n mkdocs | `mkdocs_src/docs/developer/frontend/i18n.md` |
| Settings mkdocs | `mkdocs_src/docs/developer/architecture/settings.md` |
| App layout | `frontend/src/routes/(app)/+layout.svelte` |
| Header | `frontend/src/lib/components/layout/Header.svelte` |
| Sidebar | `frontend/src/lib/components/layout/Sidebar.svelte` |
| Theme store | `frontend/src/lib/stores/app/themeStore.ts` |
| Language store | `frontend/src/lib/stores/app/language.ts` |
| i18n translations | `frontend/src/lib/i18n/base/{en,it,fr,es}.json` |
| Settings page (runtime of the tab registry) | `frontend/src/routes/(app)/settings/+page.svelte` |
| Settings tab registry | `frontend/src/lib/features/settings/settingsTabs.ts` |
| Settings components mkdocs | `mkdocs_src/docs/developer/frontend/components/features/settings.md` |
| Global settings API | `backend/app/api/v1/settings.py` |
| Global settings service | `backend/app/services/accounts/global_settings_service.py` |
| Onboarding engine | `frontend/src/lib/features/onboarding/onboardingGuide.svelte.ts` |
| Popup lane | `frontend/src/lib/features/onboarding/components/DeferredAppPopups.svelte` |
