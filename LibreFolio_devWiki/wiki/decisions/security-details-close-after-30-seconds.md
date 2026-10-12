---
title: "The connection-security details close by themselves after 30 s; the pointer anywhere on the indicator, or the focus inside the details, holds the count"
category: decision
status: accepted
date: 2026-10-12
tags: [frontend, layout, connection-security, sidebar, timer, accessibility, focus, ux, workstream-i, release-1.2]
related:
  - features/F-102
  - decisions/connection-security-server-never-upgrades
  - sources/phase00-ui-polish-2026-10
---

# Decision: details that do not stay open forever

## Context

The connection-security indicator in the sidebar ([[features/F-102]]) opens a panel that explains the level of the
connection. The developer asked, verbatim: «un clic sul testo che spiega il livello chiude il pannello; il pannello si
chiude da solo dopo 30 secondi» ("a click on the text that explains the level closes the panel; the panel closes by
itself after 30 seconds"). Workstream I implemented it in plan 48.

## Decision

The coordinator's choice (b), 2026-10-12, verbatim: «Il puntatore ferma il timer dentro tutto l'indicatore, con gli
eventi pointer; il fuoco lo ferma solo dentro i dettagli (motivo e link), non sul toggle; all'uscita riparte da 30 s.
Resta nello spirito di quanto approvato dallo sviluppatore» ("the pointer stops the timer anywhere on the indicator,
through pointer events; the focus stops it only inside the details — the reason and the link — not on the toggle; on
leaving, it starts again from 30 s").

- **Why not the focus on the toggle**: Chrome, and Firefox on Windows and Linux, give the focus to a clicked button.
  Whoever opened the panel with the mouse would leave the focus on the toggle, and the timer would never run: the
  panel would stay open for ever.
- **Why not `:focus-visible`** (option (a)): it depends on each browser's heuristics, and jsdom, where the tests run,
  cannot tell the keyboard from the mouse.

`5e9eff52d` («feat(layout): security details close by themselves», train 72), in `ConnectionSecurityIndicator.svelte`:
the reason becomes a button that closes the panel; `pointerInside` and `focusInDetails` hold the count; an effect arms
`AUTO_CLOSE_MS` (30 000 ms) whenever the panel is open and neither holds it.

## Consequences

- A keyboard user reading the details keeps them open; a mouse user who moves away sees them close after 30 s.
- 20 new Vitest cases with fake timers (red before, 34 green after); the `connection-security` E2E, 8 passed.
- The gallery shoots the open panel and parks the pointer away before a shot (`parkPointer`), which starts the 30 s:
  that risk was passed to workstream M, who prepared the fix in batch 32 (I5), to apply once T's CP3 is in the target. *Applied in batch 33*
  (`2d0ca1660`): the gallery opens the details right before the shot and leaves the pointer on the indicator, so the
  count never starts.

## Source files

| Role | Path |
|------|------|
| The indicator (`AUTO_CLOSE_MS`, `pointerInside`, `focusInDetails`) | `frontend/src/lib/components/layout/ConnectionSecurityIndicator.svelte` |
| Its tests (fake timers) | `frontend/src/lib/components/layout/ConnectionSecurityIndicator.test.ts` |
| The gallery's `parkPointer` | `frontend/e2e/fixtures/galleryRiskLab.ts` |
| Plan 48 (the developer's request, choice (b)) | `LibreFolio_developer_journal/Release_2/Phase_0/48_uiPolish/plan-phase00UiPolish.prompt.md` |
