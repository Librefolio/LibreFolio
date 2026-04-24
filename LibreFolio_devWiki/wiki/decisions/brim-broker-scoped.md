---
title: "BRIM Files Scoped to Broker (Multi-User Support)"
category: decision
status: resolved
date: 2026-01-22
tags: [brim, brokers, multiuser, access-control, upload]
related_features: [F-011, F-012, F-010]
---

# Decision: BRIM Files Must Be Broker-Scoped

## Context
Initially, BRIM file uploads had no association with a broker at upload time. The broker was specified only at parse time (`POST /brokers/import/files/{id}/parse` body: `{ broker_id }`). This caused files to be "orphaned" — not filterable by broker, no permission check at upload.

## Problem
1. No `uploaded_by_user_id` on file — impossible to know who uploaded what
2. No `target_broker_id` — file list couldn't be filtered by broker
3. Upload without permission check — any authenticated user could upload to any broker
4. Files page showed all files regardless of broker membership
5. Test broker IDs visible in prod (no isolation)

## Decision
Move broker association to **upload time**: `POST /api/v1/brokers/{broker_id}/import/upload`

Access control enforced at upload: user must have `EDITOR` or `OWNER` role on the target broker.

File list now scoped: `GET /api/v1/brokers/{broker_id}/import/files` filters by broker and by user's access.

## Alternatives considered
- **Broker at parse time (status quo)**: rejected — too late, creates orphan files
- **Global file pool + broker tag**: rejected — violates permission model (EDITOR should see only their broker's files)

## Consequences
- Breaking URL change for upload endpoint
- Existing uploaded files (dev env) need re-association or deletion
- Cleaner permission model: upload → parse → commit all gated by broker role

## Resolved
✅ Completed Phase 4 — `analysis-brim-multiuser.md`, `plan-brim-multiuser-implementation.md`

## Source files

| Role | Path |
|------|------|
| BRIM abstract base | `backend/app/services/brim_provider.py` |
| Broker service | `backend/app/services/broker_service.py` |
| DB model (BrokerUserAccess) | `backend/app/db/models.py` |
