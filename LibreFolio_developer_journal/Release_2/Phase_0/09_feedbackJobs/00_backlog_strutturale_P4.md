# Backlog strutturale — i task P4 dell'audit 08

**Creato**: 2026-09-07 · **Origine**: `08_newCleanAndDocumentation_audit` (archiviato in
`Release_2/phases/`) · **Natura**: lavoro strutturale rimandato — NON bug, NON urgente,
ma debito che cresce col tempo. Da pescare al prossimo round di sviluppo.

Questi 8 task sono i "grandi" dell'audit di pulizia (02/09) che non sono stati fatti nella
tornata P0–P3 perché richiedono un lavoro dedicato. I 26 `TODO(P2-refactor)` marcati nel
codice al 03/09 (gate C901) sono la loro proiezione puntuale: `grep -rn "TODO(P2-refactor)" backend/ scripts/`.

> ⚠️ I report citati sotto sono **archiviati** in `../../phases/08_newCleanAndDocumentation_audit/`
> (li descrivono con l'evidenza del 02/09; le righe possono essere scivolate da allora).

| # | Task | Perché / cosa comporta | Dimensione | Descritto in |
|---|------|------------------------|-----------|--------------|
| P4-1 | **Scissione di `asset_source.py`** (5 162 righe al 02/09, in crescita) in moduli: provider management / prezzi / metadata / bulk ops | Il file più grosso del backend; ogni modifica lo fa crescere. Il report 03 ha la mappa delle sezioni | L | [03 §T8](../../phases/08_newCleanAndDocumentation_audit/03_services_pricing_fx.md) · [14 #6.13](../../phases/08_newCleanAndDocumentation_audit/14_backlog_ed_esecuzione.md) |
| P4-2 | **Scomposizione di `transaction_service.execute_batch`** (complessità C901 = 115, ~640 righe) in handler per verbo con dispatch tabellare | Il singolo punto più complesso del codice; ogni bugfix lì dentro è a rischio | L | [02 §T8](../../phases/08_newCleanAndDocumentation_audit/02_services_core.md) · [11 #7](../../phases/08_newCleanAndDocumentation_audit/11_crosscutting.md) |
| P4-3 | **Estrazione helper condivisi BRIM** dai parser, un provider alla volta, partendo da `broker_credit_agricole._parse_account_movements` (C901 = 71) | 35 siti C901 BRIM quasi identici; una volta fattorizzati, i test possono coprire i rami errore oggi irraggiungibili | L | [04 §T2](../../phases/08_newCleanAndDocumentation_audit/04_providers.md) · [17 #4](../../phases/08_newCleanAndDocumentation_audit/17_stabilizzazione.md) |
| P4-4 | **`get_history_value` di Yahoo Finance** (complessità 31, invariata da un mese) | Il provider più usato e più instabile; i retry/fallback annidati sono il punto caldo | M | [04 §T4](../../phases/08_newCleanAndDocumentation_audit/04_providers.md) |
| P4-5 | **Migrazione Svelte 5 Runes** di `BrokerSharingPanel.svelte` (24 `$:` legacy) + le due tab settings (9+9) | Il debito `$:` cresce a ogni feature; la migrazione costa di più col tempo | M | [11 #6](../../phases/08_newCleanAndDocumentation_audit/11_crosscutting.md) · [10 §G3](../../phases/08_newCleanAndDocumentation_audit/10_frontend_charts.md) |
| P4-6 | **Matrice dichiarativa per `validate_status_matrix`** (`schemas/signals.py:1069`, C901 32) | La matrice stato×segnale è una catena di if; una tabella dichiarativa la rende estensibile. Trigger naturale: il prossimo `SignalStatus` | M | [05 §T4](../../phases/08_newCleanAndDocumentation_audit/05_signals_risk.md) |
| P4-7 | **Ciclo di vita dei cache store frontend** (`removeAssetPriceStore` mai chiamato, registry/pool mai rilasciati) | Le cache in-memory crescono senza tetto; serve una misura e una decisione (LRU? clear on logout?). Collegato alla nota in TODO_FUTURI sull'audit delle cache | M | [08 §T2](../../phases/08_newCleanAndDocumentation_audit/08_frontend_state_api.md) · [14 #9](../../phases/08_newCleanAndDocumentation_audit/14_backlog_ed_esecuzione.md) |
| P4-8 | **Voci S6 residue del vecchio backlog** (6.2, 6.3, 6.4, 6.7, 6.8, 6.11, 6.12; 6.14 sconsigliata) + **TRY003 congelata** finché TRY non entra nel select ruff | Coda lunga del backlog di agosto; dettaglio nel report 14 | varie | [14 #23/#26](../../phases/08_newCleanAndDocumentation_audit/14_backlog_ed_esecuzione.md) |

## Come leggerlo

- **P4-1/2/3** sono i tre colli grossi (L): un round di sviluppo dedicato li può chiudere in
  sequenza, e ognuno sblocca i test che oggi non si possono scrivere.
- **P4-4/5/6/7** sono medi (M): entrano in un round misto.
- **P4-8** è la coda: si spunta quando si tocca l'area.
- I 26 marker `TODO(P2-refactor)` nel codice (tabella completa nel piano P1 archiviato,
  `phases/08_newCleanAndDocumentation_audit/plan-phase00P1QuickWins.prompt.md` §P1-2) sono
  i punti esatti da cui partire per ciascuno.
