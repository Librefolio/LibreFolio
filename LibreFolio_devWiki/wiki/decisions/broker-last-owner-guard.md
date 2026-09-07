---
title: "Removing the last broker owner is forbidden; demoting them to VIEWER is not"
category: decision
status: open
date: 2026-08-30
tags: [brokers, sharing, permissions, frontend, ux, product-decision]
related: [concepts/characterisation-test-latch, decisions/settings-write-path-contract]
---

# Decision: the last-owner guard is asymmetric — and the fix is a product question

## The finding

`BrokerSharingPanel.svelte` guards **removal** of the last `OWNER` and refuses
it. Seventeen lines earlier, the **role change** path allows that same last owner
to be set to `VIEWER`.

The two paths reach the same end state: a broker with no owner, which nobody can
administer. One is blocked, the other is not.

The guard is therefore not protecting the invariant it appears to protect. It is
protecting one **spelling** of the operation.

## What the user decided

> The last owner cannot be deleted. The system should ask whether to **delete the
> broker** — together with its transactions — or to **promote a new owner**.

So the answer is not "add the same guard to the role-change path". Blocking both
paths leaves the user in a dead end: they own a broker they no longer want and
have no supported way out.

The intended shape is a **dialogue at the point of refusal**, offering the two
legitimate exits:

1. delete the broker and everything attached to it, or
2. promote another user to `OWNER` first, then step down.

## Feasibility, verified

`DELETE /api/v1/brokers/{id}` already exists and already accepts a `force`
parameter, so exit (1) needs no backend work — only the confirmation UI and an
honest count of what will be destroyed.

Exit (2) is the existing role-change call, ordered.

## Status

**Open.** The behaviour is currently held by a characterisation test
([[concepts/characterisation-test-latch]]) so that the asymmetry cannot be
"fixed" by accident in a direction the user did not choose. Closing this means
building the dialogue, not tightening the guard.

## Why it is recorded as a decision and not a bug

Because the obvious repair is the wrong one. A future reader finding the
asymmetry will want to add the missing guard in five minutes; this page exists to
tell them that the five-minute fix was considered and **rejected**, and why.

## Source files

| Role | Path |
|------|------|
| Removal guard | `frontend/src/lib/components/brokers/BrokerSharingPanel.svelte` (~262) |
| Unguarded role change | `frontend/src/lib/components/brokers/BrokerSharingPanel.svelte` (~245) |
| Broker delete endpoint (`force`) | `backend/app/api/v1/brokers.py` |
| Sharing service | `backend/app/services/broker_service.py` |
| mkdocs | `mkdocs_src/docs/user/brokers/index.en.md` |
