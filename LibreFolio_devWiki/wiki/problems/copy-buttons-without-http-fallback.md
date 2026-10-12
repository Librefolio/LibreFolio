---
title: "Five copy buttons call the Clipboard API directly and copy nothing over plain HTTP (M-20)"
category: problem
status: open
date: 2026-10-12
tags: [frontend, clipboard, http, secure-context, tailscale, connection-security, ux, workstream-m, workstream-i]
related:
  - features/F-102
  - decisions/connection-security-server-never-upgrades
  - sources/phase00-translation-round12-2026-10
---

# Problem: copy buttons that need a secure context

## Symptom

On a page served over plain `http://` from anything but `localhost` — Tailscale over HTTP, or the LAN address — five
copy buttons do nothing (one of them shows an error toast). Found on 2026-10-12 by the `docs-writer` agent while
checking a sentence of the connection-security guide against the code: the guide said the installable app was «the
only reason» to prefer an HTTPS address over a VPN on HTTP, and it was not the only one.

## Root Cause

Browsers expose the Clipboard API only to secure contexts. The app has a shared helper with a fallback,
`writeTextToClipboard()` in `frontend/src/lib/utils/clipboard.ts` (the API when `window.isSecureContext`, otherwise
`document.execCommand('copy')`), but five buttons bypass it and call `navigator.clipboard.writeText` themselves:

| Component | What it copies |
|-----------|----------------|
| `components/settings/tabs/AboutTab.svelte` | the system information |
| `components/brokers/lots/UnifiedLotsTable.svelte` | a lot id |
| `components/auth/AskAdminModal.svelte` | an administrator's e-mail (an error toast on failure) |
| `components/files/FilePreviewModal.svelte` | the text of the file in preview |
| `components/assets/ProviderAssignmentSection.svelte` | a provider's error detail |

Still the case at `35c4242f3`.

## Solution

Not fixed yet. The guide no longer claims exclusivity: it says «That is why an HTTPS address is still better», in a
warning on the Tailscale-over-HTTP case, which as a risk is equal to HTTPS ([[features/F-102]]). Backlog M-20 (low),
assigned by the coordinator to workstream I, in the UI polish batch of release 1.2: route the five buttons through the
shared helper.

## Prevention

Copy through `writeTextToClipboard()`, never through `navigator.clipboard` directly: the helper is the one place that
knows about secure contexts. A test over plain HTTP from a non-localhost origin is what would have caught it.

## Source files

| Role | Path |
|------|------|
| Shared helper with the fallback | `frontend/src/lib/utils/clipboard.ts` |
| Direct call (system info) | `frontend/src/lib/components/settings/tabs/AboutTab.svelte` |
| Direct call (lot id) | `frontend/src/lib/components/brokers/lots/UnifiedLotsTable.svelte` |
| Direct call (administrator e-mail) | `frontend/src/lib/components/auth/AskAdminModal.svelte` |
| Direct call (previewed text) | `frontend/src/lib/components/files/FilePreviewModal.svelte` |
| Direct call (provider error detail) | `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte` |
| The guide's warning | `mkdocs_src/docs/user/connection-security.en.md` |
| Backlog (M-20) | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
