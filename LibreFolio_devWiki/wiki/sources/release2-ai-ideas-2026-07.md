---
title: "Release 2 / Ai_ideas — the July 2026 brainstorm that set the order of Release 2: signals and risk in the backend first, an AI assistant through MCP later"
category: source
source_type: brainstorm
date_ingested: 2026-10-12
original_path: LibreFolio_developer_journal/Release_2/Ai_ideas/
tags: [release2, ai, mcp, roadmap, brainstorm, signals, risk, ideas]
related:
  - decisions/signal-backend-plugin-architecture
  - sources/phase00-risk-integration-2026-09
---

# Source: Release 2 / Ai_ideas

## Summary

Four short documents in Italian (543 lines, 2026-07-20 → 08-05), written before Phase 0 began. They are ideas and a
roadmap, not delivered work: what shipped is on the pages linked below, and the future that was kept lives in
`TODO_FUTURI.md`, not in the feature registry.

| File | Date | What it holds |
|------|------|---------------|
| `brainstorming_ai_features.md` | 2026-07-20 | The vision of an AI agent beside a risk engine: every calculation in the backend, the AI harness in the backend too, data access read-only and validated |
| `roadmap_and_signals_brainstorm.md` | 2026-07-22 | The Release 2.0.0 roadmap: unify the signals in the backend first, then risk, then the AI server |
| `mcp_server_architecture_draft.md` | 2026-07-22 | A draft of a LibreFolio MCP server: a thin-controller service layer, transports, guided inserts tagged by batch, a «summary vs raw» strategy, a catalogue of phase-1 tools |
| `phase_0_detailed_roadmap.md` | 2026-08-05 | Phase 0 in steps: signals to the backend, Riskfolio-Lib and Monte Carlo, asset states (watchlist), the rolling N-period return chart, a dividend calendar |

## Key Takeaways

- **The order held**: the signals moved to backend plugins first ([[decisions/signal-backend-plugin-architecture]]),
  then risk was rebuilt on riskfolio-lib and QuantLib ([[sources/phase00-risk-integration-2026-09]]), and the rolling
  return chart shipped ([[features/F-088]]).
- **The AI assistant through MCP did not ship in 1.2.** It is a theme of `TODO_FUTURI.md`, «🤖 QuarkAI — Assistente AI
  (MCP Server)»; what reached users instead is the AI Export, which prepares data and prompts for an external assistant.
- Ideas only, no feature codes: by the coordinator's rule, the registry holds what is planned or built.

## Source files

| Role | Path |
|------|------|
| The vision | `LibreFolio_developer_journal/Release_2/Ai_ideas/brainstorming_ai_features.md` |
| The MCP draft | `LibreFolio_developer_journal/Release_2/Ai_ideas/mcp_server_architecture_draft.md` |
| The Phase 0 roadmap | `LibreFolio_developer_journal/Release_2/Ai_ideas/phase_0_detailed_roadmap.md` |
| Deferred themes (QuarkAI, MCP) | `TODO_FUTURI.md` |
