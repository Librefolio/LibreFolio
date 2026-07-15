---
title: "Broker List/Detail Visibility for Non-Members"
category: decision
status: resolved
date: 2026-07-06
tags: [backend, frontend, brokers, sharing, discovery, access-control]
related:
  - domains/brokers
  - decisions/brim-broker-scoped
  - sources/phase09-m3-broker-redesign-2026-07
---

# Decision: Broker List/Detail Visibility for Non-Members

## Context

The Broker v2 redesign (list + detail shell) needed two related visibility gaps closed: (1) users had no way
to discover brokers that exist but that they don't have access to, and (2) the "who has access" sharing icon
was only visible/functional for the OWNER — EDITOR/VIEWER and non-members had no way to see the access list,
and `GET /brokers/{id}/access` 404'd outright for non-members.

## Options Considered

1. **Full "Request Access" flow** — discovery + a request/notification/approval pipeline. Rejected as
   out-of-scope for this phase; adds a notification system dependency.
2. **Opt-in minimal discovery + read-only sharing panel** (chosen) — surface existence without a request
   flow; let non-owners see (not edit) the access list via the same icon already used by OWNER.
3. **No changes** — keep discovery/sharing OWNER-only. Rejected: blocks the "who else has this broker"
   use case entirely, forces coordination outside the app.

## Decision

- `GET /brokers` gains an opt-in `include_inaccessible: bool = False` query param. When `true`, the response
  additionally includes brokers the user doesn't own/have access to, but **only** `{id, name, icon_url}` — no
  financial data. Default `False` so it never pollutes the existing lightweight broker selectors used
  throughout the app (performance + correctness).
- Every broker card (own or others') now shows a Condividi icon opening `BrokerSharingModal`:
  - **OWNER**: editable (unchanged from before).
  - **EDITOR/VIEWER**: read-only view of the access list (previously impossible — button was OWNER-only).
  - **Non-members**: read-only view via a reduced payload — `GET /brokers/{id}/access` must be opened to
    non-members returning only `{username, role}` per entry, omitting `email`/`share_percentage`.
- No "Request Access" / notification flow in this phase — confirmed out of scope.

## Consequences

- `BrokerDiscoveryCard.svelte` and `BrokerSharingPanel.svelte`/`BrokerSharingModal.svelte` added on the
  frontend; `broker_service.py.get_all(include_inaccessible=...)` and a relaxed non-member branch in the
  `/brokers/{id}/access` endpoint on the backend.
- Existing broker selectors are unaffected (they never pass `include_inaccessible=true`).
- Sensitive fields (`email`, `share_percentage`) stay hidden from non-members; only role visibility is
  extended.

## Links
- [[domains/brokers]]
- [[decisions/broker-card-aggregation-no-n-plus-one]] — same redesign, companion decision on per-card metrics
- Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_3/plan_ui_broker_overview.md`, `impl_plan_broker_overview.md`
