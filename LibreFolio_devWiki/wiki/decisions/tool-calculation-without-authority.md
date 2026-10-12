---
title: "A Tool calculation receives only an explicit scenario — no user, database, provider or service layer — and writes nothing"
category: decision
status: resolved
date: 2026-09-08
updated: 2026-09-16
tags: [backend, frontend, tools, authority, security, privacy, isolation, api, release-1.2, workstream-c]
related:
  - features/F-106
  - decisions/tool-item-runs-in-owned-process
  - decisions/tool-contract-from-pydantic-compiled-renderer
  - concepts/backend-only-calculations
  - sources/phase00-tool-platform-2026-09
---

# Decision: a Tool computes a scenario; it never reaches into the portfolio

## Context

The backlog item «Piattaforma Tool e allocatore PAC» (`09_feedbackJobs/05_pac_allocation_tool.md`) asked for a PAC
calculator. On 2026-09-07 the planning broadened it into three tracks — a generic backend Tool platform, one
mathematical model shared by PAC and rebalancing, a custom Tool UI «with authorized domain snapshots rather than
Tool-owned portfolio lookups» (the PAC decision chronicle). The platform boundary was fixed at the checkpoint of
2026-09-08, and workstream C built it on 2026-09-08–10.

## Decision

- **Every input is explicit and packed before dispatch.** The child process receives a `ToolWorkerJob` with bounded
  parameter bytes and server-owned identity, deadlines and limits — no principal, database session, provider client
  or service-layer handle. A plugin that imports a provider or the database is outside the contract.
- **Authentication lives at the API boundary only**: the three routes (`catalog`, `compute`, `diagnostics`) depend
  on `get_current_user`. Diagnostics are open to every active authenticated user, not only administrators — the
  developer's decision (plan §1), confirmed by the coordinator for gate G2 — and they carry no scenario, result,
  cookie, trace or log.
- **Nothing is written and nothing is fetched** inside a calculation: no transactions, no broker orders, no live
  provider calls.
- **Out of the contract**: chained Tools, workflows or a Tool state machine; schema, prefill, jobs or cancel
  endpoints; an MCP server. Aborting the HTTP request stops the client's wait; it is not a cancellation
  acknowledgement.
- **Filling a draft from the user's own data is the renderer's job**, before dispatch, through an ordinary domain
  endpoint. For the PAC planner that endpoint is `POST /api/v1/portfolio/allocation-source` — authenticated,
  read-only, answered with `Cache-Control: no-store` — and the Tool API never sees the user.

## Why — the dossier's reasons

The review dossier of the platform (workstream C, 2026-09-11, §3.3) lists these refusals as deliberate, with reasons:

- «un processo che può scrivere è un processo che, quando viene ucciso a metà, lascia scritture parziali. La capacità
  di uccidere duramente e la capacità di scrivere sono incompatibili, e ho scelto di conservare la prima.» — the
  platform must be free to kill a job at its hard deadline ([[decisions/tool-item-runs-in-owned-process]]).
- A cancel endpoint would have needed a persistent job registry and a notion of job ownership across requests.
- No financial semantics in the platform: a crash, a time limit, an invalid output or a failed cleanup is a
  **platform error**, never a fabricated «infeasible» or a zero result.

## Options Considered

| Option | Outcome |
|--------|---------|
| Tool-owned portfolio lookups, or a `/tools/prefill` endpoint | Rejected: the Tool would gain the user's authority; snapshots come from domain APIs instead |
| A job, status and cancel API | Rejected: needs persistence and job ownership; three endpoints only |
| Live provider fetches during compute | Rejected: same root as the writes — a killable process must not have side effects |
| Explicit scenario, authority at the API, copies through domain endpoints | **Chosen** |

## Consequences

- **Any caller that can build the scenario can use a Tool.** The PAC contract compaction (2026-10-05) used it as an
  argument: an external AI caller builds the packet itself, so fewer mandatory fields mean fewer values to invent.
- **Validation is a gate, not a rewrite.** The client validates one plain snapshot with the Tool's codec and sends
  those same bytes; the server preserves the caller's values instead of a default-expanded copy.
- **The user page says it plainly**: «A tool never changes your portfolio.» Acting on a result is up to the user.

## Source files

| Role | Path |
|------|------|
| Worker job (no principal, no session) | `backend/app/services/tools/worker.py` |
| Plugin base and execution context | `backend/app/services/tools/base.py` |
| Authenticated routes | `backend/app/api/v1/tools.py` |
| The PAC planner's domain-copy endpoint | `backend/app/api/v1/portfolio_api.py` |
| Developer doc («Scope and authority») | `mkdocs_src/docs/developer/architecture/patterns/tool_plugins.en.md` |
| User doc («Good to know») | `mkdocs_src/docs/user/tools/index.en.md` |
| Platform plan (§1, the developer's decisions) | `LibreFolio_developer_journal/Release_2/Phase_0/16_toolPlatform/plan-phase00ToolPlatform.prompt.md` |
| Review dossier (§3.3) | `LibreFolio_developer_journal/Release_2/Phase_0/16_toolPlatform/dossier-piattaforma-tool.md` |
