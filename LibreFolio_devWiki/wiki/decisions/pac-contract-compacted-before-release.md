---
title: "PAC contract: compacted before its first release and kept at 1.0.0 — defaults in the schema, optional fields with a stated meaning, no freshness on the wire"
category: decision
status: resolved
date: 2026-10-05
tags: [backend, frontend, pac-allocator, tools, contract, versioning, pydantic, json-schema, codegen, mcp, release-1.2, workstream-d]
related:
  - features/F-107
  - decisions/tool-contract-from-pydantic-compiled-renderer
  - decisions/ai-export-version-bump-once-per-release
  - decisions/pac-p1-prototype-removed
  - sources/phase00-pac-implementation-2026-10
---

# Decision: a compact wire and a resolved request, at version 1.0.0

## Context

The planner's request (`PacPlannerRequest`) had been born as «2.0.0», after P1's `1.0.0`. At the review rounds the
developer reset it on 2026-10-02: «il developer lo ha riportato a `1.0.0`, perché nessuna delle due versioni è mai
stata rilasciata» (hand-off §0). Two days later, at Round 14, he asked for a smaller packet:

> «se accepted non serve, togliamolo, non sono sicuro di aver capito freshness, e rendere gli zeri opzionali non
> sarebbe male, per rendere il pacchetto più rapido. […] quando poi passeremo al server MCP IA, sarà più facile fare
> il pacchetto di richiesta IA e trasformarlo in questo, evitiamo cose che non servono ora che ancora esiste tutto
> solo su questa macchina.»

## Decision

**When**: the coordinator's decision (a) — the slice runs **before** the contract enters `dev_release2`, so «nessun
fingerprint `1.0.0` pubblicato cambia senza cambiare versione»: «La versione resta `1.0.0`: non è mai stata
rilasciata. Il fingerprint cambia **una volta**, qui.» Delivered in `ac18ce097` (2026-10-05), merged with
`68483ddda`.

**The rule: a compact wire, a resolved request.**
- Defaults live in the schema, always as `Field(default=…)`, never `default_factory` — which emits no `default` in the
  JSON Schema, so the generated codec would not see it. A union default is a model instance (`NoFeeCap`), because
  strict mode does not validate defaults.
- The normalizer, the engine, the evaluator and the oracle see the validated request with every default filled: they
  do not change. `json_schema_serialization_defaults_required=True` keeps the output codec «all required».
- The UI sends the compact form; the result views read the resolved request (`z.output`). The same values give the
  same exact scenario and the same `request_fingerprint`.

**What left the wire**: the quote's `freshness` (`fresh` / `stale{age_days, accepted}`) and `reference_date`, the
cash `source_kind`, and three issue codes (79 → 76). Earlier, on 2026-09-24, `currency_specs` had left too: the
currency's minor unit is derived on the backend from babel (Q-C0-1: «cambiamo la api semplicemente, tanto le valute
sono standard e vincolate ad essere quelle di babel»).

**Optional, with a stated meaning**: `transfer_cap` absent transfers the whole source; an absent fixed fee or fee
floor is zero; a BUY route without a fee schedule pays no commission — the normalizer instantiates
`~zero~{capability_id}~{CUR}`, and `~` is forbidden in caller ids, so the implicit ids cannot collide.

## Consequences

- An external caller — an AI building the packet itself, through a future MCP server — has fewer values to invent.
  The compute depends only on the packet; the planner's copies exist for the user's convenience.
- The UI still shows a price's age in the draft (Q-C0-3: show how many days old, «ma in ogni caso la scelta finale è
  dell'utente»); only the wire stopped carrying it, and the order detail lost its «Price date» row.
- **«Once» held for the compaction, not for 1.2**: at `1.0.0` the fingerprint moved again with the FX fix
  (2026-10-09, `4f061103…` → `a999932e…`) and with the schema texts of the rounding fix. The version counts from the
  last release, as for the AI Export ([[decisions/ai-export-version-bump-once-per-release]]); the Rebalancer analysis
  plans «un solo salto di versione del contratto».
- A test caught a precedence, not a defect: a fee schedule in USD on an EUR scenario first needs the EUR/USD rate
  (`fx_rate_missing`, `needs_input`) before `currency_mismatch` (`invalid`) can surface; the test now supplies the
  rate and asserts the mismatch is the only error.

## Source files

| Role | Path |
|------|------|
| Contract (defaults, optional fields, strict model config) | `backend/app/schemas/pac_allocator/request.py`, `backend/app/schemas/pac_allocator/base.py` |
| Implicit fee schedules, babel minor units | `backend/app/services/pac_allocator/normalize.py` |
| Issue codes | `backend/app/services/pac_allocator/issues.py` |
| Request builder (compact form) | `frontend/src/lib/features/tools/pac-allocator/planner/request.ts` |
| Schema tests | `backend/test_scripts/test_schemas/test_pac_planner_schemas.py` |
| Wire fixture | `backend/test_scripts/fixtures/pac_allocator/pac_plan_request.compact.v2.json` |
| Compaction plan | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacContractCompaction.prompt.md` |
