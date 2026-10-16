---
title: "Copying goes through one helper, kept there by a gate: `writeTextToClipboard()`, with a fallback that works on plain HTTP (M-20, C-63)"
category: decision
status: accepted
date: 2026-10-12
tags: [frontend, clipboard, http, secure-context, gate, vitest, connection-security, workstream-i, release-1.2]
related:
  - problems/copy-buttons-without-http-fallback
  - decisions/html-escape-at-the-source
  - features/F-102
  - sources/phase00-ui-polish-2026-10
---

# Decision: one way to copy

## Context

Browsers expose the Clipboard API only to secure contexts. Five copy buttons called `navigator.clipboard.writeText`
themselves and copied nothing on a LAN or Tailscale address over plain HTTP (M-20,
[[problems/copy-buttons-without-http-fallback]]); two more, in the file list and grid, had their own `execCommand`
fallback, and the grid said «copied» even when nothing was (C-63). M-20 went to workstream I's UI polish (plan 48).

## Decision

- **One helper**: `writeTextToClipboard()` in `frontend/src/lib/utils/clipboard.ts`. It uses the Clipboard API in a
  secure context and falls back to `execCommand('copy')` when the API is missing — on plain HTTP it copies at once
  through a read-only textarea (`legacyCopy`) — and also when the API refuses.
- **Every copy button uses it**: the five of M-20 (About, the lots table, the request to an admin, the file preview,
  the provider check) and the two of C-63 (`FilesTable`, `FileGrid`) — seven call sites in `65d20910e` («fix(clipboard):
  copy buttons work on plain HTTP», train 72).
- **A gate keeps it so**: `frontend/src/clipboardSink.gate.test.ts`, built like the HTML-sink gate
  ([[decisions/html-escape-at-the-source]]), fails on any other `navigator.clipboard.writeText` or `execCommand('copy')`
  in the frontend. The one exception, with its reason written in the gate, is AI Export's own writer
  (`aiExportClipboard.ts`), which turns every failure into a typed error its interface reports. The gate runs in
  `front-utility core-unit`; before the fix it listed 11 direct transports.
- **A known limit, accepted** (the coordinator's choice (b), 2026-10-12): in a secure context, after `window.open`, a
  refusal cannot fall back — the new tab has used up the click's activation, and without it Chromium refuses
  `execCommand('copy')` — so copy-and-go ends in its error state. The coordinator: «Il prodotto non cambia, e (c) è
  scartata per il rischio del blocco dei popup in Safari» ("the product does not change, and (c) is discarded for the
  risk of Safari's popup blocking"); the test proves that limit instead of avoiding it.

## Consequences

- Copy works on every address the connection-security indicator can describe ([[features/F-102]]); the 1.2
  CHANGELOG says so: «Copy buttons work over plain HTTP too».
- A new copy button that bypasses the helper fails the unit suite, not a user on HTTP.
- C-63 and M-20 are closed in the backlog (`2166eeb90`).
- Tests: the gate and the helper, 8 red before and green after (`125 passed`); `support-copy-and-go.spec.ts` red
  against the old helper (4 failed) and green after (16 passed).

## Source files

| Role | Path |
|------|------|
| The helper (`writeTextToClipboard`, `legacyCopy`) | `frontend/src/lib/utils/clipboard.ts` |
| The gate | `frontend/src/clipboardSink.gate.test.ts` |
| The model gate (HTML sinks) | `frontend/src/htmlSink.gate.test.ts` |
| AI Export's own writer (the exception) | `frontend/src/lib/features/ai-export/aiExportClipboard.ts` |
| File list and grid (C-63) | `frontend/src/lib/features/files/FilesTable.svelte`, `frontend/src/lib/features/files/FileGrid.svelte` |
| Copy-and-go E2E | `frontend/e2e/support-copy-and-go.spec.ts` |
| Plan 48 | `LibreFolio_developer_journal/Release_2/Phase_0/48_uiPolish/plan-phase00UiPolish.prompt.md` |
