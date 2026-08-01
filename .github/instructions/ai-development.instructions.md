---
applyTo: "backend/app/services/ai_export/**,backend/test_scripts/diagnostics/ai_export*.py,frontend/src/lib/features/ai-export/**,frontend/scripts/*ai-export*,mkdocs_src/docs/developer/architecture/patterns/ai_export_*.md,mkdocs_src/docs/user/ai-export/**,.github/skills/ai-export-probe-tuning/**"
---

# AI Development Entry Rules

## Read Current Guidance First

Before designing or modifying AI-related behavior:

1. read the relevant MkDocs Developer Guide pages;
2. read `.github/skills/ai-export-probe-tuning/SKILL.md` when prompts or AI Export
   runtime behavior can change;
3. verify the current code, tests, runtime catalog, and command help.

Do not rely on historical reports, remembered paths, copied commands, or old
component counts when current documentation and implementation can be inspected.

## Stable Architecture

### Backend Owns

- deterministic calculations and financial semantics;
- reusable components and datasets;
- Analysis composition and applicability;
- coverage, partial, unavailable, and failure status;
- semantic selection of technical facts and events;
- runtime catalog identities.

### Frontend Owns

- the official prompt renderer;
- presentation and localization;
- local instruction and response-contract text;
- safe serialization and clipboard-ready text;
- localized Additional Data guidance.

The frontend must not duplicate financial calculations, arbitrarily select Signal,
create alternative prompt renderers, or invent technical projections.

## Prompt Rules

Prompts must:

- distinguish facts, interpretation, assumptions, and limits;
- never invent missing data or user preferences;
- state coverage and partial/unavailable semantics;
- use user-facing names and local A#/B#/F#/L# references rather than database IDs;
- guide Additional Data requests with localized labels, UI path, period, detail,
  reason, and necessity;
- keep technical context proportional to the task.

## Divergences

If MkDocs disagrees with code, tests, the runtime catalog, or observed behavior,
report the discrepancy before changing documentation. Explain the competing
interpretations and likely correction, then ask whether the affected MkDocs page
should be updated unless the current task explicitly authorizes that update.

Do not modify documentation outside the authorized scope.

## Probe Selection

Use the probe-tuning skill to choose among smoke, targeted, full tuning,
comparison, Task Adequacy, and partial-history probes. Prefer the smallest probe
that proves the requested behavior and preserve UI/probe byte equivalence.

## Future AI Infrastructure Guidance

This instruction currently covers AI Export architecture and validation workflow.
Future revisions may add documented guidance for MCP servers, tool integration,
agent runtime, model routing, prompt execution, and related AI infrastructure.

Do not infer or implement those conventions until they are documented in MkDocs
and referenced from this instruction.
