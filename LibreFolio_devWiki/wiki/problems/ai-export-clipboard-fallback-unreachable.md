---
title: "AI Export non-modern clipboard fallback was unreachable"
category: problem
status: resolved
date: 2026-07-26
updated: 2026-07-27
mkdocs: "developer/architecture/patterns/ai_export_snapshot.md"
tags: [frontend, ai-export, clipboard, browser-compatibility, user-activation, fallback]
related:
  - sources/phase00-ai-export-backend-snapshot
  - decisions/ai-export-versioned-snapshot-boundary
  - decisions/ai-export-contextual-ui-memory
  - entities/ai-export-snapshot-service
---

# Problem: AI Export non-modern clipboard fallback was unreachable

## Symptom

AI Export already had `navigator.clipboard.writeText` and `document.execCommand('copy')` transports, but browsers without the modern `ClipboardItem` plus `clipboard.write` combination could not reach them because `copyAiExportV2` failed before preparing the V2 export.

## Root Cause

The activation-preserving modern path was treated as a prerequisite instead of one clipboard capability branch. That made an absent `ClipboardItem` terminate the copy flow before the generic text transport could receive a prepared prompt.

## Solution

- When `ClipboardItem`, `Blob`, and `clipboard.write` are available, start preparation inside the user gesture, pass a `Promise<Blob>` to `ClipboardItem`, invoke `write()` immediately, and await preparation plus transport together.
- Otherwise, prepare the V2 export exactly once and write that exact prompt through `writeText`, falling back to `execCommand` where needed.
- Keep dependency-injected writers on the same prepare-once path.
- Never fall back to deleted legacy exporters, serializers, technical engines, or prompt logic.

## Prevention

Test modern and non-modern capability branches separately. Assert that snapshot fetch and rendering each run once, that the transported text equals the prepared prompt, and that fallback changes only the transport—not the export contract.

## Impact

The bug broke copy on otherwise capable non-modern clipboard environments. The fix restores compatibility without weakening user-activation handling or reintroducing legacy production behavior.

## Final verification

- Clipboard/browser compatibility is now an internal transport concern; the final panel intentionally hides compatibility status and web/language/mode controls without removing the fail-closed catalog handshake or fallback transports.
- Cross-surface E2E verifies the real request/response and clipboard path, including Snapshot's exclusion of hidden notes.
- The project owner approved representative desktop/mobile clipboard behavior on 27 July 2026.

## Links

- [[sources/phase00-ai-export-backend-snapshot]]
- [[decisions/ai-export-versioned-snapshot-boundary]]
- [[decisions/ai-export-contextual-ui-memory]]
- [[entities/ai-export-snapshot-service]]

## Source files

| Role | Path |
|------|------|
| Final plan and archive index | `LibreFolio_developer_journal/Release_2/phases/01_signalMigration/02_aiExport/plan-phase00AiExportBackendSnapshotImplementation.prompt.md`, `LibreFolio_developer_journal/Release_2/phases/01_signalMigration/02_aiExport/README.md` |
| V2 preparation and clipboard orchestration | `frontend/src/lib/features/ai-export/aiExportClipboard.ts` |
| Modern/fallback regression tests | `frontend/src/lib/features/ai-export/__tests__/aiExportClipboard.test.ts` |
| Snapshot hidden-note E2E | `frontend/e2e/ai-export/` |
| Frontend AI Export suite registration | `scripts/test_runner/_frontend_ai_export.py` |
| Canonical registry inclusion | `scripts/test_runner/_registry.py`, `scripts/test_runner/_suites.py` |
| Developer architecture | `mkdocs_src/docs/developer/architecture/patterns/ai_export_snapshot.md` |
