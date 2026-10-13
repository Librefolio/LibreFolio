---
title: "After a logout in the single-page app, stores kept the previous account's data: one client-session state now resets everything when the user changes"
category: problem
status: resolved
date: 2026-07-23
tags: [frontend, auth, session, stores, cache, privacy, multi-user, spa]
related:
  - features/F-001
  - decisions/signal-backend-plugin-architecture
---

# Problem: the next user saw the last user's portfolio

## Symptom

LibreFolio is a single-page app, so a logout does not reload the page. After one, `portfolioStore` and `brokerStore`
survived in memory and could show the previous account's data to whoever signed in next on the same browser. Found and
fixed during the signals backend migration (folder `01_signalMigration`, 2026-07-23).

## Root Cause

Each store owned its own cache and nothing told them the user had changed; in-flight responses of the old session
could also land after the switch.

## Solution

`5b9dddb45` («feat: add backend signals and isolate sessions») added `ClientSessionState`
(`stores/app/clientSession.ts`): one central reset whenever the signed-in user changes; portfolio keys scoped per
user; a generation guard that drops responses started under the previous session; resets for the broker, asset,
transaction, file-preview, settings and chart, date and navigation state; and one cache invalidator for API
mutations.

## Prevention

A new store with user data registers with the client session's reset; a cache key that holds user data includes the
user.

## Source files

| Role | Path |
|------|------|
| `ClientSessionState` | `frontend/src/lib/stores/app/clientSession.ts` |
| Tests | `frontend/src/lib/stores/app/clientSession.test.ts` |
| Journal | `LibreFolio_developer_journal/Release_2/phases/01_signalMigration/plan-phase00SignalsBackendMigrationImplementation.prompt.md` |
