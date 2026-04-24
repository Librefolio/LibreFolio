---
title: "TanStack Table v8 — Svelte 5 Incompatibility"
category: problem
status: workaround
date: 2026-05-10
tags: [frontend, svelte5, tanstack, table, adapter]
related_features: [F-075]
---

# Problem: TanStack Table v8 — Svelte 5 Incompatibility

## Summary
The official `@tanstack/svelte-table` adapter for TanStack Table v8 is incompatible with Svelte 5 runes (`$state`, `$derived`, `$effect`). Attempting to use the v8 adapter with Svelte 5 results in reactivity failures and hydration errors.

## Root Cause
The official v8 adapter was written for Svelte 4's reactivity model (stores, `$:` reactive declarations). It does not integrate with Svelte 5 runes-based reactivity.

## Workaround Applied
A custom Svelte 5 adapter was created at `frontend/src/lib/tanstack-table/`. This adapter wraps TanStack Table v8 core (headless) with Svelte 5 runes-compatible bindings.

## Resolution path
**[[F-075]]** — When TanStack Table v9 releases a stable official Svelte adapter, migrate to it and delete the custom adapter.

## Lesson
Before adopting a UI library adapter, verify it explicitly supports the target framework version (Svelte 5 runes in this case).

## Affected files
- `frontend/src/lib/tanstack-table/` (custom adapter — workaround)
- All `DataTable` usages in `frontend/src/lib/components/table/`

## Source files

| Role | Path |
|------|------|
| Custom Svelte 5 adapter (workaround) | `frontend/src/lib/tanstack-table/` |
| DataTable component | `frontend/src/lib/components/table/DataTable.svelte` |
