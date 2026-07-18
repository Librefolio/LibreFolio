# FIFO UI v3 — Report finale · Performance completa dei lotti

> Spec: `highLevel-v3.md` + messaggio [[PLAN]] (§1–18). Log passo-passo: `implementation-log-v3.md`.
> Stato: **completato** (backend Wave 1 + frontend Wave 2 + integrazione). Verifica visiva finale = checklist manuale (in fondo), per preferenza utente.

---

## 1. Diagnosi iniziale (Wave 0)

Backend già presente: `LotSummarySchema` con realized_pnl, cumulative_proceeds, open_value, total_value, pnl, relative_return, reference_price_source, original_cost, open/original_quantity, opening_unit_price. Range **già** origin-based (`computed_from = transactions[0].date`). Proventi senza asset **già** gestiti dal Portfolio Engine ("Unallocated income/costs" per broker).

**Gap reali individuati**:
- Metriche per-lotto mancanti: `asset_income`, `market_pnl`, `total_pnl`, `cash_yield`, `total_return`, `value_source`.
- Allocazione DIVIDEND/INTEREST asset-linked ai lotti: **non** implementata (il FIFO engine gestisce solo BUY/SELL/ADJ/TRANSFER/SPLIT; il load escludeva `quantity IS NULL`).
- Estimated-at-cost (prezzo mancante): **non** implementato (i punti value/return venivano saltati → grafici vuoti).
- Frontend: Gantt lane 72px senza asse sticky/branch/marker; tabella con ricerca globale, senza footer/colonna azioni; nessuna vista bolle; selezione vuota ≠ "tutti"; modale senza le nuove metriche.

## 2. Decisioni

- Calcolo finanziario **solo backend**, valori già in target currency; il frontend seleziona/filtra/aggrega-visuale/renderizza/coordina.
- Proventi senza asset → **riuso** Portfolio Engine ("Altri effetti del periodo" dentro il pannello lots), **nessuna duplicazione** del calcolo.
- Data di allocazione proventi = `transaction.date` (non la data dell'Asset Event; l'Asset Event resta algoritmico solo per SPLIT).
- Prezzo mancante → policy esplicita `ESTIMATED_AT_COST` + Data Quality issue, mai mostrato come prezzo di mercato.
- Selezione implicita §13: `[]` = tutti i lotti visibili.

## 3. Formule (backend, verificate con test)

```
w_i(t)      = openQty_i(t) / Σ_j openQty_j(t)         (lotti LONG aperti alla tx.date)
Income_i(t) = convert(I(t), target, tx.date) · w_i     (Σ Income_i = I, residuo arrotondamento deterministico)
market_pnl_i  = open_value_i − open_cost_i             (= pnl − realized_pnl; 0 in estimated mode)
total_pnl_i   = market_pnl_i + realized_pnl_i + asset_income_i
cash_yield_i  = asset_income_i / opening_value_i
total_return_i= total_pnl_i / opening_value_i
```

Prezzo mancante: `open_value_i = openQty_i · adjusted_opening_unit_price_i`, `market_pnl_i = 0`, `value_source = ESTIMATED_AT_COST`.

## 4. File creati / modificati / rimossi

### Backend
- `backend/app/schemas/portfolio.py` — `IssueCode.CURRENT_PRICE_ASSUMED_AT_COST`; `LotValueSource`; `LotSummarySchema` +6 metriche; history `income`; **§11**: `LotAnalysisType.INCOME_EVENTS`, `LotIncomeEventKind`, `LotIncomeEventSchema`, `LotsAnalysisResponse.income_events`.
- `backend/app/services/lots_analysis_service.py` — `_load_income_transactions`; `_allocate_asset_income` (pro-rata + conservazione + payload eventi §11); estimated-at-cost nei builder value/return; DQ issue; income events trimmati alla finestra display.
- `backend/test_scripts/test_services/test_financial/test_lots_analysis_service.py` — +5 test (pro-rata/partial/conservazione, FX income, estimated crowdfunding, income post-chiusura, income_events markers).

### Frontend
- `LotGanttChart.svelte` (ricostruito): compatto/gerarchico/asse sticky/marker/reattività/tooltip.
- `LotPerformanceBubbleChart.svelte` (**nuovo**): bolle ABS/%, LONG only.
- `LotsOtherEffectsSection.svelte` (**nuovo**): "Altri effetti del periodo".
- `UnifiedLotsTable.svelte` + `table/DataTable.svelte` (core): no ricerca globale, footer aggregato net-new, colonna Azioni ⋮, ordine/default/condizionali, min-width Stato/Custodia.
- `LotComparisonChart.svelte`: marker proventi + styling estimated + `incomeEvents`.
- `LotWacPriceChart.svelte`: prop `incomeEvents` + marker/tooltip + `onEventDoubleClick` (§9).
- `LotCustodyModal.svelte`: metriche v3 (asset_income/market_pnl/total_pnl/total_return/cash_yield/value_source) + nota estimated.
- `LotsAnalysisPanel.svelte` (hub): toggle Timeline/Performance, wiring eventi/income/altri-effetti, §13 selezione implicita, §9 doppio click, fetch report.
- `routes/(app)/transactions/+page.svelte`: navigazione view-mode + scroll + pulse (§14).
- `i18n/{en,it,fr,es}.json`: +44 `brokers.lots.*` + 2 toggle + DQ key; WAC→PMC/CMP; rimossa `searchPlaceholder`.
- `api/generated.ts` + `openapi.json`: rigenerati (`./dev.py api sync`).

### Rimossi
- Chiave i18n orfana `brokers.lots.searchPlaceholder` (ricerca globale rimossa, §15).

## 5. Materiale riutilizzato
- Portfolio Engine `positions_contribution.{unallocated, other_effects}` (Altri effetti) via `fetchReport(...includeContribution)` — nessun ricalcolo.
- `DataTable` (column visibility/persistenza/context menu/filtri/sort/row actions) esteso col footer.
- `translatedOr` / `formatQuantity` / `attachDataZoomSync` esistenti.
- Endpoint bulk multi-analysis + FifoLotEngine event-sourced **non riprogettati**.

## 6. DTO / API
`POST /portfolio/lots/analysis` — `requested_analyses` accetta `INCOME_EVENTS`; response +`income_events: LotIncomeEventSchema[]` (type, date, broker_id, transaction_id, amount, lot_ids); `LotSummarySchema` +6 metriche; history point +`income`; nuovo IssueCode. Client TS rigenerato.

## 7. Test e validazione
- Backend: 15/15 service (`test_lots_analysis_service.py`), 37 passed su lots_analysis + portfolio_api + income_events. ruff+black OK.
- Frontend: `./dev.py front check` → **0 errors / 0 warnings**. `prettier --check` lots + tx page + DataTable → clean.
- i18n: `./dev.py i18n audit` → **1726/1726 complete, 0 incomplete**. (48 "unused" = falsi positivi da `translatedOr`.)

## 8. Limitazioni residue
- Bolle Performance limitate ai lotti LONG (SHORT esclusi con grazia) — come da spec §10.
- "unused" i18n audit include falsi positivi (`tooltip.*` via `translatedOr`); lo scanner statico non riconosce l'helper.

## 9. Fuori scope — segnalato, non toccato
- **Responsività WAC modal** (desktop↔mobile): diagnosi checkpoint 011 = nessuna cattura JS della larghezza; riflette su resize reale; probabile emulazione DevTools/build stale → serve repro esatto dall'utente.
- **BRIM FEE/TAX asset-linked ai lotti** (`TODO_ProssimeAttivita.md`): task dedicato (cost basis/WAC engine).

## 10. Cleanup
- Rimossa ricerca globale tabella + chiave i18n orfana.
- Nessun file di scope altrui toccato (working tree condiviso con task concorrenti: ai-export FX, preview_columns, gallery — lasciati invariati).

---

## Checklist verifica manuale (IT/EN · light/dark · desktop/mobile)

Percorso: Dashboard → tab broker → asset → range → **analisi lotti**.

1. **ETF solo BUY**: Gantt lane compatte, marker ▲ su ogni acquisto, asse X sticky durante scroll. Nessuna selezione = tutte le linee Valore/Rendimento visibili.
2. **SELL parziali**: marker ▼ sul segmento; spessore lotto si riduce dopo la vendita; doppio click su SELL nel 1° grafico → selezione + pulse dei lotti consumati + passaggio a Timeline.
3. **Transfer**: lane figlia nasce solo alla data di biforcazione (◆); doppio click TRANSFER → pulse dei frammenti coinvolti.
4. **Dividendi (asset-linked)**: marker verticali tratteggiati teal su 1°/Valore/Rendimento; tooltip tipo/data/broker/importo/lotti; modale lotto mostra Proventi + Rendimento da proventi + P&L complessivo.
5. **Crowdfunding senza prezzo**: modale/tabella mostrano "Valore stimato al costo"; Market P&L = 0; Total Return valorizzato da interessi.
6. **Proventi broker-level (no asset)**: compaiono in "Altri effetti del periodo" (Provento/Costo non allocato — <broker>), non attribuiti ai lotti.
7. **Vista Performance**: toggle `[Timeline][Performance]`; bolle su data apertura; `[ABS]` (y=P&L) / `[%]` (y=Total Return); dimensione = valore apertura; verde/rosso per segno.
8. **Tabella**: nessuna barra ricerca; column selector toggla subito; colonna Azioni ⋮ (dettaglio/gantt/tx/copia id); footer aggrega selezionate o visibili.
9. **Navigazione tx**: "Vai alla transazione di apertura" → `/transactions`, riga centrata, modale in view mode; chiusura → pulse riga; Back torna al pannello lotti con selezione preservata.
10. **SHORT**: escluso dalle bolle senza errori.
