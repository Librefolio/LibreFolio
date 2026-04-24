---
title: "SvelteKit 2 + Svelte 5 over React + MUI"
category: decision
status: resolved
date: 2026-01-01
tags: [frontend, svelte, react, architecture, bundle]
related: [concepts/svelte5-runes, concepts/dual-view-pattern, decisions/zodios-api-client]
---

# Decision: SvelteKit 2 + Svelte 5 over React + MUI

## Context
LibreFolio V1 used React + Material UI (MUI). The V4 rewrite (Phase 0–1) selected a new frontend stack from scratch. The choice had long-term implications for bundle size, reactivity model, and developer ergonomics across the project.

## Options Considered
1. **React + MUI (existing)** — familiar, large ecosystem, but heavyweight bundle, complex state management (context/Redux), virtual DOM overhead, slow HMR at scale.
2. **SvelteKit 2 + Svelte 5** — compiler-based, no virtual DOM, minimal runtime, native reactivity via runes (`$state`, `$derived`, `$effect`), fast HMR. Tailwind CSS 4 compatibility.
3. **Vue 3 + Nuxt** — middle ground, but less differentiated vs React.

## Decision
**SvelteKit 2 + Svelte 5** was chosen for the V4 rewrite. Key reasons:
- Simpler reactivity model via Svelte 5 runes — no `useEffect` dependency arrays
- Significantly lighter bundle — no VDOM runtime
- `adapter-static` for SPA mode — output is a plain static build served by FastAPI
- Tailwind CSS v4 with `@theme {}` in `app.css` (no TS config file) — compatible out of the box
- Skeleton UI was evaluated and removed (not compatible with Tailwind v4); Tailwind alone was sufficient

## Consequences
- All new components use Svelte 5 runes (`$state`, `$derived`, `$effect`) — old `$:` reactive syntax is avoided in new code
- i18n: `svelte-i18n` (840+ keys, EN/IT/FR/ES)
- Date handling: `date-fns`
- API client: `@zodios/core` (see [[decisions/zodios-api-client]])
- `frontend/build/` is pre-built on host before Docker image assembly
- No React dependency anywhere in the project

## Links
- [[concepts/svelte5-runes]]
- Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-00-setup.md`
- Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-01-foundation.md`

## Source files

| Role | Path |
|------|------|
| Phase 0 plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-00-setup.md` |
| Phase 1 plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-01-foundation.md` |
| Tailwind theme | `frontend/src/app.css` |
| SvelteKit config | `frontend/svelte.config.js` |
