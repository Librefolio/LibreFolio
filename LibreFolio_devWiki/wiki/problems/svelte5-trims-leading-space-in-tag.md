---
title: "Svelte 5 removes the whitespace at the start and end of a tag: a leading space inside a span vanished («ROUTING–»)"
category: problem
status: resolved
date: 2026-10-10
tags: [frontend, svelte5, whitespace, template, typography, gallery, pac-allocator, workstream-d]
related:
  - features/F-107
  - concepts/svelte5-runes
  - sources/phase00-pac-implementation-2026-10
---

# Problem: a space that the compiler removes

## Symptom

In the gallery's batch 9 (workstream M, `pac-step-routing` on desktop), the title of the PAC planner's Routing step
read «ROUTING–», with no space before the dash.

## Root Cause

The title is the step name followed by an intro span; the space before the dash was the first character inside the
span: `<span data-testid="pac-planner-routing-intro"> – …</span>`. Svelte 5 removes the whitespace at the start and
the end of a tag, so the span rendered «– …» glued to the name. The capital letters come from the step title's class
(`SECTION_TITLE`, `uppercase`), which made the missing space more visible. The line arrived with the review rounds
(`6f29ec1cf`).

## Solution

`161a5b06b` (2026-10-10): the span opens with an expression, `{' '}`, which the compiler keeps — the same idiom
`ExposureMaps.svelte` already used. Proved with the lockfile's compiler (Svelte 5.48.0) on the file before and
after: the span renders «– …» before and « – …» after, in both the client and the SSR output. No other tag of the
PAC planner had the same shape. The fix holds in all four languages.

## Prevention

- When text inside a tag must start or end with a space, write it as `{' '}`; a literal space at the edge of a tag is
  layout whitespace for Svelte 5, not content.
- No test was added: the planner has no component test of `PacPlannerTool`, and its dedicated E2E tests come after
  the Rebalancer. The gallery found it — a screenshot is a typography test.

## Source files

| Role | Path |
|------|------|
| The fixed span | `frontend/src/lib/features/tools/pac-allocator/planner/PacPlannerTool.svelte` |
| The idiom already in use | `frontend/src/lib/features/tools/pac-allocator/planner/result/ExposureMaps.svelte` |
| Step title class | `frontend/src/lib/features/tools/pac-allocator/planner/ui.ts` |
| PAC backlog (defect 3) | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/README.md` |
