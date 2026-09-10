# 09_feedbackJobs — indice

Backlog del prossimo round di sviluppo. Ogni file è un'area; i task dentro hanno contesto,
dettagli implementativi e rimandi al codice/ai piani. Creato il 07/09/2026 dalla revisione
di TODO_FUTURI.md (classificazione con l'utente) + gli 8 P4 ereditati dall'audit 08.

| File | Area | Contenuto |
|------|------|-----------|
| [00_backlog_strutturale_P4.md](00_backlog_strutturale_P4.md) | Debito strutturale | Gli 8 task P4 dell'audit (scissione asset_source, execute_batch, BRIM helpers, Yahoo, Runes, status matrix, cache store, coda S6) |
| [01_ux_dashboard.md](01_ux_dashboard.md) | UX & dashboard | Provider probe, global privacy, YOC, uploader filter, currency help, support, onboarding, mobile header |
| [02_grafici_avanzati.md](02_grafici_avanzati.md) | Grafici | F8 (P&L-only, synthetic candles, income histograms), delivered lot analysis, calendar-day asset return |
| [03_asset_dati_classificazione.md](03_asset_dati_classificazione.md) | Asset & dati | Settori bond Corporate/Governativi, import CSV distribuzioni geo/settore |
| [04_brim_import.md](04_brim_import.md) | BRIM & import | eToro fee reconciliation, delivered FIFO v4 cost allocation, asset deletion links |
| [05_pac_allocation_tool.md](05_pac_allocation_tool.md) | Tool platform | Backend plugins, custom-first UI, PAC/rebalancing, per-currency cash and optional buy/sell/FX |
| [06_piano_sprint.md](06_piano_sprint.md) | Analysis and sprint plan | Current-code evidence, 16 sprints, parallel-work dependency map, shared-resource ownership and developer UI review gates |

**Planning update (2026-09-07):** see [06](06_piano_sprint.md) for the current-code
assessment and decisions made during review. Global privacy, mobile auto-hide header,
synthetic P&L candles and the backend Tool plugin platform supersede the original narrower
scope. The initial publication was planning-only; the execution update below records
the subsequently authorized work.

**Review follow-up (2026-09-07):** YOC now specifies a 365-day window, explained dash states,
an English theory page and a column-header tooltip. The shared CsvEditor is extended rather
than duplicated. Tool schemas live in the catalogue; data copying uses domain APIs.
Section 11 maps parallel work; section 12 requires ASCII mockup approval before substantial
UI changes and an operational developer walkthrough/feedback round afterward.

## Execution update - 2026-09-07

**Group B only** is authorized to implement approved revision 2:
[Contracts and Runes - SP04-SP05](../11_feedbackContractsRunes/plan-phase00FeedbackContractsRunes.prompt.md).
Scope: P4-5, P4-6/S6 6.7, S6 6.2 and S6 6.11. Progress and acceptance live in that plan;
backlog pickup does not mean implementation is complete. A/C/D remain planning-only.
Group B owns the sequential shared runtime/API-generation queue. No production-data
repair, schema migration, staging, commit or push is part of this authorization.

**Handoff update (2026-09-08):** Group B's code work is complete. Final operational
developer review is deferred and remains open (`awaiting_dev_review`); use the runbook
in the linked execution plan. The B test server is stopped and the runtime queue has
been returned. This does not authorize implementation or runtime use by A/C/D.

## Regole della cartella

- I task si pescano da qui all'inizio di un round; quando un task parte, il suo piano vive in
  `Phase_0/<NN_area>/` come di consueto, e qui viene marcato ✅ con link al piano.
- Le note "Status" citano la decisione utente del 07/09/2026.
- Ciò che è deliberatamente rinviato resta in `TODO_FUTURI.md` (non qui).
