---
title: "Unused or superseded API routes are removed, with no deprecation period (API-CLEAN)"
category: decision
status: resolved
date: 2026-11-05
tags: [api, breaking-change, cleanup, changelog]
related: [decisions/broker-page-is-a-portfolio-view]
---

# Decision: remove unused routes, no deprecation

## Context
After the 1.2 release the API had routes nobody called any more: replaced by a better one, or left over from a
removed screen. The developer's rule: a route with no caller is removed, not deprecated. No released install depends
on them.

## Decision
- **Remove, don't deprecate.** A route with no caller in the app or the tests goes, together with its schemas, its
  tests and its documentation; the commit is marked `!` (breaking) and the CHANGELOG gets a line under
  *Breaking changes* naming each replacement.
- **Thirteen routes in the first pass**, among them `POST /transactions/transfers/promote` (use
  `POST /transactions/commit` with `promotes[]`), `POST /transactions/events/suggest` (use
  `GET /transactions/event-reconciliation`), `DELETE /assets/events` (use `POST /assets/events` with `delete_ids`),
  `GET /assets/all` (use `GET /assets/query?active=true`), `POST /assets/provider/refresh` (use
  `POST /assets/provider/probe`), `POST /portfolio/wac` (use `POST /portfolio/lots/analysis`).
- **`GET /brokers/{id}/summary` last**, after the broker page moved to the shared view
  ([[decisions/broker-page-is-a-portfolio-view]]).
- **After the removal, look for what only the route used**: dead helper modules (a metadata service, a summary
  module) went with it, and tests that imported them failed at collection. Run the whole test collection, not the
  API area only, before calling the removal done.
- Run `./dev.py api sync` so the TypeScript client loses the routes too.

## Lessons
- A check that prints nothing proves nothing: `black --check -q` is quiet on failure, so counting its lines said
  «clean» for a tree with five unformatted files. Read the exit code.
- Wiki pages that still cite a removed module are history, not errors; `check_source_paths.py` lists them.

## Source files
| Role | Path |
|------|------|
| Routers | `backend/app/api/v1/` |
| Changelog line | `CHANGELOG.md` (Breaking changes of the 1.3.0 chapter) |
