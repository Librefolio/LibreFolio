# 09_feedbackJobs — indice

Backlog del prossimo round di sviluppo. Ogni file è un'area; i task dentro hanno contesto,
dettagli implementativi e rimandi al codice/ai piani. Creato il 07/09/2026 dalla revisione
di TODO_FUTURI.md (classificazione con l'utente) + gli 8 P4 ereditati dall'audit 08.

| File | Area | Contenuto |
|------|------|-----------|
| [00_backlog_strutturale_P4.md](00_backlog_strutturale_P4.md) | Debito strutturale | Gli 8 task P4 dell'audit (scissione asset_source, execute_batch, BRIM helpers, Yahoo, Runes, status matrix, cache store, coda S6) |
| [01_ux_dashboard.md](01_ux_dashboard.md) | UX & dashboard | Bug testa-config, modalità privacy, colonna YOC, filtro utente files, tooltip valuta, decisione mode='duplicate' |
| [02_grafici_avanzati.md](02_grafici_avanzati.md) | Grafici | F8 (P&L assoluto/candele/istogrammi), guadagni per transazione, rendimento a N (asset) |
| [03_asset_dati_classificazione.md](03_asset_dati_classificazione.md) | Asset & dati | Settori bond Corporate/Governativi, import CSV distribuzioni geo/settore |
| [04_brim_import.md](04_brim_import.md) | BRIM & import | eToro Withdraw/Conversion Fee, FEE/TAX collegamento asset, link transazioni in delete modal |
| [05_pac_allocation_tool.md](05_pac_allocation_tool.md) | Feature grande | Tool allocazione PAC multi-ETF (vincolo intero, euro), backend API + frontend, futura esportazione MCP |

## Regole della cartella

- I task si pescano da qui all'inizio di un round; quando un task parte, il suo piano vive in
  `Phase_0/<NN_area>/` come di consueto, e qui viene marcato ✅ con link al piano.
- Le note "Status" citano la decisione utente del 07/09/2026.
- Ciò che è deliberatamente rinviato resta in `TODO_FUTURI.md` (non qui).
