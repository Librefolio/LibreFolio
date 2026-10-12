---
title: "AI Export component versions: bump only when the implementation changes, and at most once (+1) per release"
category: decision
status: resolved
date: 2026-10-12
tags: [ai-export, contracts, versioning, components, renderer, compact-tables, release, release-1.2]
related:
  - decisions/ai-export-versioned-snapshot-boundary
  - entities/ai-export-snapshot-service
  - problems/ai-export-reconciled-false-on-rounding-dust
  - decisions/native-cash-daily-revaluation
  - decisions/financial-math-single-average-cost
  - sources/phase00-financial-math-home-2026-10
---

# Decision: when and by how much an AI Export component's version moves

## Context

Every AI Export component carries a stable `component_id` and an implementation `version`
([[decisions/ai-export-versioned-snapshot-boundary]]; `ai_export_composition.md`, «ComponentSpec»). The version is
written in two places — the component's spec and the frozen catalogue placeholder in `components/catalog.py` — and the
registry checks they match. On the frontend, `snapshotDataRenderer.ts` prints a section as a compact table only when
its component version is listed in `COMPACT_COMPONENT_VERSIONS` (version 1 alone for a component without an entry);
any other version falls back to `PAYLOAD YAML FALLBACK`.

During the 1.2 cycle several components changed, and three questions came up: does a change of values need a bump,
how many bumps can accumulate before the release, and what else must move with a bump.

## Decision

1. **The version is the implementation's.** A bump is due when the builder or the payload changes — a field added or
   made nullable, a flag computed differently. A change of the *values* that reach an unchanged builder is not one:
   - lot 41 step F-W added an «FX on cash» row to the broker effects and lowered the residual, through the same
     builder and the same payload shape — no bump of `broker.flows_income_costs` (coordinator, 2026-10-12);
   - C-50 renamed a field only in the renderer's output, the payload staying canonical — no bump (2026-10-11).
2. **At most one +1 over the last released version, until the release ships** (the developer's rule, 2026-10-12): a
   component already moved in the cycle does not move again. The released reference is `v1.1.0`.
3. **A bump updates `COMPACT_COMPONENT_VERSIONS` in the same change**, or the section silently becomes YAML. This is the
   lesson of `asset.lot_detail`: beta fix F6 (`3e3f9c41f`, 2026-09-01) took it to v2 without the map, so from
   `v1.1.0` on its lots came out as a longer YAML block — a silent regression, found by workstream T and fixed on
   2026-10-11 (`03c57b066`) with v3, compact, in the map.

## State at `5d0585595`

Nine components moved in the cycle, each exactly +1 over `v1.1.0`, each listed in the compact map:

| Component | `v1.1.0` | Now | Commit |
|---|---|---|---|
| `portfolio.provenance`, `broker.provenance` | 1 | 2 | `de252a38a` (issue #32, 2026-10-07) |
| `portfolio.fifo_summary`, `broker.fifo_summary`, `portfolio.fifo_lots`, `broker.fifo_lots` | 1 | 2 | `03c57b066` (2026-10-11) |
| `asset.lot_detail` | 2 | 3 | `03c57b066` (2026-10-11) |
| `portfolio.reconciliation`, `broker.reconciliation` | 1 | 2 | `876d2b430` (C-53, 2026-10-12) |

The rule had a concrete effect on a pending item: lot 41's cost estimate for F-AI (b) counted an optional sentence in
the two provenances' `valuation_semantics` as a bump «to v3» with a map `{1,2,3}`. Under the rule it would stay at v2,
the version they already have in this cycle.

## Consequences

- Several fixes in one cycle cost one version per component, and a reader of a 1.2 prompt sees at most one version
  step from 1.1.
- Before bumping, check the component's version in the last release tag (`git show v1.1.0:…/catalog.py`).
- The rule is recorded in the journal (plan 43, C-53; backlog 38, C-53). At `5d0585595` it is not yet written in
  `.github/instructions/ai-development.instructions.md` nor in `ai_export_composition.md`.

## Links

- [[problems/ai-export-reconciled-false-on-rounding-dust]] — C-53, the first change made under the rule
- [[decisions/native-cash-daily-revaluation]] — F-W and F-AI, the values-only case
- [[entities/ai-export-snapshot-service]]
- Source: [[sources/phase00-financial-math-home-2026-10]]

## Source files

| Role | Path |
|------|------|
| Component catalogue (frozen versions) | `backend/app/services/ai_export/components/catalog.py` |
| Compact renderer and `COMPACT_COMPONENT_VERSIONS` | `frontend/src/lib/features/ai-export/templates/snapshotDataRenderer.ts` |
| Composition doc («ComponentSpec», «Snapshot Data Tables») | `mkdocs_src/docs/developer/architecture/patterns/ai_export_composition.md` |
| C-53 analysis and the version rule | `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` |
| Backlog C-53 | `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/README.md` |
| F-AI cost and the no-bump decision | `LibreFolio_developer_journal/Release_2/Phase_0/41_brokerPnlFlows/plan-phase00BrokerPnlFlows.prompt.md` |
