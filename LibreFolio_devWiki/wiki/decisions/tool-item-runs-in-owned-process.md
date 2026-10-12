---
title: "Every Tool item runs in a fresh process the platform owns — no warm pool, no cache, no sharing; ownership is not a sandbox"
category: decision
status: resolved
date: 2026-09-10
updated: 2026-09-16
tags: [backend, tools, multiprocessing, process-group, cleanup, budgets, memory, cgroup, release-1.2, workstream-c, workstream-d]
related:
  - features/F-106
  - decisions/tool-calculation-without-authority
  - decisions/tool-contract-from-pydantic-compiled-renderer
  - sources/phase00-tool-platform-2026-09
---

# Decision: one owned process per Tool item

## Context

A Tool runs arbitrary packaged calculation code — the first one drives a MIQCP solver for up to 30 s. The platform
must bound time and memory, survive a crash or a runaway child, and never let one user's job leak into another's.

## Decision

- **A fresh `spawn` process for every item that reaches execution**, even for identical inputs: no coalescing, no
  cross-user cache, `deduplication` fixed to `"none"` (the developer's decision, plan §1). The dossier's reason: «un
  pool caldo riusa memoria e stato fra utenti diversi, e rende il kill duro una perdita di capacità invece che una
  pulizia» — atomicity before latency.
- **The platform owns the process tree.** The child calls `setsid` and sends a `ready` frame with its execution id,
  PID, process group and creation time; the supervisor adopts the group and only then sends the start ACK (`\x00`),
  after which discovery and computation begin. `OwnedProcessTree` tracks descendants by PID **and** creation time,
  against PID reuse; cleanup asks to terminate, escalates to kill, and must observe the termination.
- **Capacity returns only after confirmed cleanup.** A lane and its admission credit come back when the whole tree is
  gone; an unconfirmed cleanup quarantines the job (`cleanup_failed`) instead of recycling the lane. A result frame is
  not a cleanup acknowledgement.
- **Children of a plugin** (threads, processes) are allowed only inside the job's lifetime; nothing may be detached.
- **Deadlines are absolute**: the queue counts from the batch's admission, the hard budget includes the cold start,
  and `context.checkpoint()` is cooperative — it does not kill. A long engine claims its window first
  (`claim_engine_window()`).
- **Memory per job**: on Linux with a delegated cgroup-v2 directory, a private child cgroup holds a hard limit
  (`cgroup_v2_hard`), used only after proving the delegation and reading `memory.max` back; otherwise the supervisor
  sums the resident memory of the tree at most 50 ms apart (`process_tree_observed`); a non-POSIX host reports
  `unavailable` and refuses jobs (`service_unavailable`). A breach ends the item with `memory_limit`.
- **It is not a sandbox.** The developer doc says so in a warning: ownership manages the lifetime of packaged plugin
  work; it does not isolate the filesystem or make it safe to run untrusted plugins.

## How the budgets were set

| Budget | Initial policy (C, 2026-09-10) | After the capacity round (D, 2026-09-16) |
|--------|-------------------------------|------------------------------------------|
| Queue / hard / soft | 5 s / 5 s / 4 s | 5 s / 45 s / 44 s, engine 30 s, output reserve 1 s |
| Cleanup | 2 s | 5 s |
| Request / client | 20 s / 25 s | 59 s / 65 s |
| Memory | — | 1 GiB per job, about 2 GiB over two lanes |

The developer's decision of 2026-09-16 (PAC implementation master) withdrew a candidate product cap of
«16 Asset/4 Broker/32 route/4 valute» and asked instead for a growth curve and «un envelope anti-abuso alto,
resource-bound»: «massimo circa `1 GB RSS` per singolo job; due worker possono raggiungere circa `2 GB`; `30 s`
riservati al solver per item». Workstream C designed the envelope, and D implemented it as per-operation budgets
clamped by the platform plus `resources.py` (`4a38b9061`). The values the operations omit still default to the
initial ones, which is a trap for the next Tool ([[features/F-106]], implementation notes).

## Options Considered

| Option | Outcome |
|--------|---------|
| A warm worker pool | Rejected: shares memory and state between users; a hard kill costs capacity instead of cleaning up |
| A memory flag `memory_limited: true` | Rejected: `capabilities.memory.mode` has three values, so a host without enforcement says so |
| A fresh owned process per item, cleanup-confirmed capacity | **Chosen** |

## Consequences

- Every job pays a cold start, measured as `startup_ms`; metrics are measured durations, `null` when not observed,
  and parallel items are never summed into a latency.
- Capacity is per API process: several ASGI workers multiply it, and the diagnostics say they describe one process.
- Hardening after two reviews (`8e7259ecc`): frames read incrementally against deadlines, and a process group that
  lost its leader stays quarantined until the kernel confirms it is gone.
- **Still open** (dossier §5, checked at `8abce8e87`): no screen shows the memory mode; the observed mode can count
  shared pages twice and miss a spike between samples; the cgroup path has never run on a real delegated host.

## Source files

| Role | Path |
|------|------|
| Supervisor, admission, lanes, quarantine | `backend/app/services/tools/executor.py` |
| Child entry, handshake, `setsid` | `backend/app/services/tools/worker.py` |
| Owned process tree | `backend/app/services/tools/process_tree.py` |
| Memory enforcement | `backend/app/services/tools/resources.py` |
| Platform and operation policies | `backend/app/schemas/tools.py` |
| Clamp to the platform | `backend/app/services/tools/catalog.py` |
| Lifecycle tests | `backend/test_scripts/test_services/test_tools_executor.py` |
| Developer doc («Isolated execution») | `mkdocs_src/docs/developer/architecture/patterns/tool_plugins.en.md` |
| Capacity round | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00Step1Round1-ToolPlatformCapacity.prompt.md` |
