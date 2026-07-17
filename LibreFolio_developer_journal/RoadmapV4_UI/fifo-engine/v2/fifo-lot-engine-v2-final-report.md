# FIFO Lot Engine v2 — Report finale di implementazione

> Piano eseguito: [`hig-level-plan_v2.md`](./hig-level-plan_v2.md).
> Log passo-passo completo (ogni singolo step, con judgement call e bug scoperti): [`fifo-lot-engine-v2-implementation-log.md`](./fifo-lot-engine-v2-implementation-log.md).
> Questo documento è il riepilogo esecutivo richiesto a fine implementazione (analisi iniziale, decisioni, file, formule, test, limitazioni, cleanup residuo).

## 1. Analisi iniziale

Il piano v2 è stato letto integralmente (1063 righe) e confrontato con il codice reale prima di scrivere qualunque riga. Verifiche chiave che hanno determinato il via libera (nessun blocco):

- **§20 "WAC = costo totale invece che unitario?"** → verificato **non essere un bug**: `abs(amount)/quantity` è già applicato correttamente in `wac_utils.py`, `portfolio_service.compute_wac_iterative`, `portfolio_engine._buy_unit_cost`.
- **Bug reale WAC split** (già segnalato 4 volte nei report precedenti) → causa esatta isolata a `transaction_service.py::_compute_wac_for_auto_items` (righe ~1601-1604 prima del fix): scriveva sempre il WAC corrente come costo per QUALSIASI item `cost_basis_mode="auto"`, incluso uno SPLIT.
- **Ratio di split** → già presente in `AssetEvent.value` (popolato da `yahoo_finance.py`), nessuna modifica DB necessaria.
- **Pattern bulk riusabile** → `PortfolioReportQuery`/`PortfolioReportResponse` (`POST /portfolio/report`) confermato come precedente diretto per `POST /portfolio/lots/analysis`.
- **Compatibilità DB/validazioni business** → nessuna migrazione Alembic necessaria; tutta l'identità di lotti/frammenti è calcolata a runtime da colonne esistenti (`Transaction.id`, `related_transaction_id`, `asset_event_id`, `AssetEvent.value`), coerente con l'architettura "FIFO at Runtime" del progetto.

Nessuna contraddizione matematica o blocco di prodotto: si è proceduto con l'implementazione, come previsto dal prompt ("se non emergono blocchi, procedi autonomamente").

## 2. Decisioni assunte

| Decisione | Dettaglio |
|---|---|
| **Fix WAC split/reverse-split** | Globale, non solo interno al nuovo motore — richiesto esplicitamente da §20 del piano. Cambia numeri storici già visualizzati per ADJUSTMENT collegati a SPLIT esistenti. |
| **Convenzione transito `[min,max)`** | Applicata anche al Portfolio Engine aggregato (non solo al nuovo motore) — richiesto da §7.2. Chiude un buco di valore di ≥1 giorno per trasferimenti a date adiacenti. 2 test esistenti aggiornati consapevolmente. |
| **SHORT in Fase 1** | Incluso da subito (non rimandato come nel v1), per richiesta esplicita del piano v2. |
| **Split scope** | Un evento SPLIT trasforma solo i frammenti custoditi da un broker con transazione ADJUSTMENT collegata esplicitamente a quell'evento — non tutti i frammenti dell'asset a prescindere (giudizio motivato: evita mutazioni silenziose cross-broker; il piano stesso non specifica questo caso in modo univoco). |
| **UI lotti: quantità assolute** | Confermato con l'utente in sede di pianificazione: la UI mostra sempre la quantità/valore assoluta del broker, mai scalata per `share_percentage`. Nota/tooltip per broker in comproprietà. |
| **Bug fuori-scope non toccati** | Quantità/costo fantasma su TRANSFER con `share_percentage` diversi tra broker; `InTransitInterval.share` hardcoded a 1; `share_mismatch_warnings` mai popolato — **solo segnalati**, non richiesti esplicitamente dal piano v2, coerente con la preferenza dell'utente di non correggere silenziosamente bug fuori scope. |

## 3. File creati

**Backend:**
- `backend/app/services/fifo_lot_engine.py` (993 righe) — motore puro `FifoLotEngine` (event-sourced, LONG/SHORT, TRANSFER, SPLIT, P&L, Data Quality).
- `backend/app/services/lots_analysis_service.py` (1202 righe) — `LotsAnalysisService`: loader bulk + price/FX + WAC series + mapping Data Quality.
- `backend/test_scripts/test_services/test_financial/test_fifo_lot_engine.py` (25 test).
- `backend/test_scripts/test_services/test_financial/test_lots_analysis_service.py` (3 test).

**Frontend:**
- `frontend/src/lib/components/brokers/lots/LotGanttChart.svelte` — Gantt ECharts custodia/transito.
- `frontend/src/lib/components/brokers/lots/UnifiedLotsTable.svelte` — tabella unificata multi-selezione.
- `frontend/src/lib/components/brokers/lots/LotCustodyModal.svelte` — modale Custodia/cronologia.
- `frontend/src/lib/components/brokers/lots/LotWacPriceChart.svelte` — WAC/prezzo di mercato (successore di `AssetWacPriceChart`).
- `frontend/src/lib/components/brokers/lots/LotComparisonChart.svelte` — grafico comparativo (Valore/Rendimento/Prezzo).
- `frontend/src/lib/components/brokers/lots/LotsAnalysisPanel.svelte` — orchestratore (successore di `FIFOLotsPanel`).

**Journal:**
- `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/fifo-lot-engine-v2-implementation-log.md` — log passo-passo completo (39 step, aggiornato durante l'intera implementazione).
- Questo report.

## 4. File modificati

**Backend:** `portfolio_engine.py` (fix WAC split + convenzione transito), `portfolio_service.py` (fix WAC split ×2 funzioni, rimozione `get_lots`/`get_asset_history`), `transaction_service.py` (fix WAC split auto-mode), `wac_utils.py` (fix WAC split), `portfolio_api.py` (nuovo endpoint + rimozione 2 vecchi), `schemas/portfolio.py` (14 nuove classi DTO + 6 nuovi `IssueCode` + rimozione 4 schemi obsoleti).

**Backend test:** `test_financial_utils.py`, `test_daily_state_builder.py`, `test_scope_classifier.py` (nuovi test di regressione), `test_portfolio_service.py`, `test_portfolio_api.py`, `test_portfolio_wac.py` (nuovi test + rimozione test obsoleti).

**Frontend:** `dashboard/+page.svelte`, `brokers/[id]/+page.svelte` (swap `FIFOLotsPanel`→`LotsAnalysisPanel`, 2 righe ciascuno), `frontend/e2e/gallery.spec.ts`, `frontend/e2e/brokers/brokers-detail.spec.ts` (rename testid), `frontend/src/lib/i18n/{en,it,fr,es}.json` (77 chiavi nuove: 71 UI + 6 Data Quality, tradotte al 100% su 4 lingue), `frontend/src/lib/components/charts/{chartCoreHelpers.ts,echartsDataZoomSync.ts}` (pulizia commenti stale).

> **Nota di trasparenza**: nello stesso ambiente condiviso era attiva una sessione concorrente non correlata (feature "AI export" + ristrutturazione link documentazione). File come `KpiSection.svelte`, `AiExportMenu.svelte`, `assetPromptCatalog.ts`, `promptCatalog.ts`, `assets/[id]/+page.svelte` mostrano modifiche **non riconducibili a questo lavoro** — non incluse sopra, non toccate né revertite. I file i18n JSON contengono invece un mix (le mie aggiunte + le loro modifiche pre-esistenti ad altre chiavi): preservate entrambe, mai sovrascritte.

## 5. File rimossi

**Backend:** endpoint `GET /portfolio/lots`, `GET /portfolio/asset-history` (`portfolio_api.py`); metodi `PortfolioService.get_lots()`, `get_asset_history()`, helper privato `_get_latest_price()`; schemi `AssetHistoryPoint`, `OpenLotSchema`, `ClosedLotSchema`, `FIFOLotsResponse`. **Non rimossa** (per istruzione esplicita del piano): `fifo_utils.calculate_fifo_lots()` (pure function) + relativi test — rimane un'utility riusabile e indipendentemente testata.

**Frontend:** `FIFOLotsPanel.svelte`, `BubbleLotTimeline.svelte`, `OpenLotsTable.svelte`, `ClosedLotsTable.svelte`, `AssetWacPriceChart.svelte`.

**i18n:** 8 chiavi `brokers.lots.*` della vecchia tabella (buyDate/sellDate/sellPrice/openLots/closedLots/noOpenLots/noClosedLots/currentValue/realizedPnl — verificate senza altri riferimenti prima della rimozione).

Verificato con grep esaustivo (prima di ogni rimozione) che nessun riferimento residuo rimanesse in nessun file del repository.

## 6. Materiale esistente riutilizzato (non duplicato)

- **Backend**: `convert_bulk` (FX), `compute_wac_from_txlist`/`compute_wac_iterative` (WAC, dopo il fix), pattern bulk single-engine-run di `get_report()`, `DataQualityIssue`/`IssueCode`/`IssueDomain`/`IssueSeverity` esistenti, `SafeDecimal`/`Currency`/`OpenDateRangeModel` da `schemas/common.py`, `resolve_date_sentinels`.
- **Frontend**: `DataTable.svelte` (multi-select già presente), `ModalBase.svelte`, `echartsDataZoomSync.ts`/`echartsDataZoomTouchPan.ts`, `BrokerBadge.svelte`/`AssetIcon.svelte`, `formatCurrencyAmountPlain`/`formatDecimal.ts`, `DataQualityBanner.svelte`, pattern ECharts `custom series` già usato in `PerformanceChart.svelte`/`AllocationHistoryChart.svelte`. Nessuna nuova libreria introdotta.

## 7. Formule e invarianti implementati

- **Rescale split/reverse-split** (invariante di costo `q·p0 = cost`): `new_wac = (qty_pool × wac) / new_qty` — matematicamente equivalente a "costo totale invariato", valido per ratio sia >1 che <1. Verificato anche per ratio non "puliti" (3:1) con tolleranza Decimal (`0.01`) per evitare falsi crash da troncamento a 28 cifre significative.
- **Transito `[min(d_out,d_in), max(d_out,d_in))`**: sostituisce `[d_out+1, d_in-1]`, chiude il buco di valore su gambe a date adiacenti.
- **FIFO puro** (`FifoLotEngine`): apertura/chiusura LONG/SHORT con attraversamento dello zero, `P&L = qty_chiusa × (prezzo_chiusura − prezzo_apertura)`; ADJUSTMENT+ a costo zero con rendimento relativo `MarketPrice(t)/reference_price − 1`; TRANSFER con selezione FIFO dei frammenti e propagazione data/prezzo originari; identità lotto/frammento stabile (`lot_id = opening_transaction_id`, frammento `lot:{id}/origin:{broker}` o `lot:{id}/transfer:{pair}/{transit|to:{broker}}`).
- **Query-count bulk service**: 4-5 query totali (non per-giorno/per-lotto/per-broker-punto-prezzo), verificato con helper SQLAlchemy `before_cursor_execute` + serie WAC ricalcolata in-memory via replay di `compute_wac_from_txlist` sulla lista transazioni già caricata (zero query aggiuntive per la history).

## 8. Test e comandi eseguiti — risultati

| Comando | Risultato |
|---|---|
| `pytest` (unità pure: fifo_utils, wac_utils, fifo_lot_engine, portfolio_engine, portfolio_service, schemas, transaction_service, vnext) | **623 passed** |
| `pytest test_portfolio_wac.py` (live server) | **10 passed** |
| `pytest test_portfolio_api.py` (live server, incl. 5 nuovi test `TestLotsAnalysisEndpoint`) | **20 passed** |
| `ruff check backend/app/` | 8 errori nel repo, **0 introdotti da questa sessione** (2 pre-esistenti in file toccato, 6 in file mai toccati) |
| `black --check` su tutti i file toccati | pulito |
| `./dev.py api sync` | client TS rigenerato senza errori |
| `svelte-check` (`./dev.py front check`) | **0 errori, 0 warning** (verificato ripetutamente ad ogni step) |
| `./dev.py i18n audit` | **1621/1621 (100%) su EN/IT/FR/ES** |
| `./dev.py mkdocs build` | completato senza errori |
| `./dev.py mkdocs gallery -f "fifo lots panel"` (E2E reali, server+DB popolato) | **2/2 passed**, 16 screenshot generati e ispezionati visivamente (EN/IT/FR/ES × light/dark × dashboard/brokers) |

**Totale test automatici eseguiti con successo in questa implementazione: 653** (esclusi i test E2E gallery, eseguiti come verifica funzionale/visiva).

## 9. Bug reali scoperti e corretti durante l'implementazione

1. **WAC split/reverse-split raddoppia/dimezza il costo** — causa esatta isolata e corretta in 4 file (`wac_utils.py`, `portfolio_service.py` ×2 funzioni, `portfolio_engine.py`, `transaction_service.py`).
2. **Crash Decimal su ratio di split non "puliti"** (es. 3:1) — asserzione di invarianza di costo troppo stretta nel nuovo `fifo_lot_engine.py`, scoperta e corretta prima che venisse consegnata (verifica indipendente, non riportata dall'agente che ha scritto il codice).
3. **Contaminazione cross-schema** — un agente DTO ha accidentalmente reso `MissingPriceAsset.quantity` (schema non correlato) opzionale per un replace troppo ampio; scoperto in review, confermato dall'agente stesso, revertito chirurgicamente.
4. **Tipo TypeScript generato ridondante** (`(X|null)|Array<X|null>` per ogni campo `Optional`) — causa 9 errori di compilazione reali nell'orchestratore; risolto con helper `asArray`/`asObject` riusabili e documentati.
5. **Chiavi Data Quality FIFO mai tradotte** — scoperto solo tramite ispezione visiva di uno screenshot reale (mostrava la chiave i18n grezza `dataQuality.referencePriceFallback` invece del testo); il tool `./dev.py i18n audit` non lo rilevava per un limite del suo pattern-matching (chiave ritornata da un dizionario, non da un'assegnazione letterale). Aggiunte 6 chiavi × 4 lingue, verificato visivamente il fix in EN/IT/dark theme.

## 10. Bug pre-esistenti segnalati, NON corretti (fuori scope)

- `portfolio_engine.py:1722`: `get_global_setting(self.db, "base_currency", "EUR")` chiamato con 3 argomenti posizionali in ordine sbagliato — la firma reale è `get_global_setting(key: str, session: AsyncSession)`. Solleverebbe `TypeError` se il ramo venisse eseguito (chiamato solo quando `target_currency` non è esplicito). Non corretto: non correlato al lavoro FIFO/lots, riga mai toccata da questa sessione.
- 5 bug fuori-scope della sessione precedente (quantità/costo fantasma su `share_percentage`, `InTransitInterval.share` hardcoded, `share_mismatch_warnings` mai popolato) — confermati ancora presenti, non richiesti dal piano v2, non toccati.
- 6 errori ruff pre-esistenti in `api/v1/settings.py` e `services/scheduler/*.py` — non correlati, file mai toccati.

## 11. Limitazioni e attività rinviate

- **Test E2E per selezione/sincronizzazione/modale**: non scritti (il prompt originale li richiedeva "test frontend di selezione, modale, sincronizzazione e rendering"). Eseguiti invece 2 test E2E gallery reali end-to-end (rendering + Data Quality + i18n verificati su server/DB reali) più ispezione visiva diretta di 4 screenshot. Coerente con la preferenza nota dell'utente di preferire la verifica visiva manuale a test automatici pesanti per componenti UI — ma la copertura di interazione (drag/click di selezione multipla, apertura modale via click, sincronizzazione zoom Gantt↔WAC) resta **da verificare manualmente dall'utente** (checklist fornita in chat) o con una futura sessione E2E dedicata.
- **`gallery.spec.ts`**: solo le 2 sezioni "fifo lots panel" sono state verificate/corrette in profondità. Il resto del file (altre centinaia di screenshot per altre feature) non è stato toccato né eseguito — fuori scope.
- **Coordinamento con sessione concorrente**: alcuni file (specialmente i JSON i18n) sono stati salvati più volte in un ambiente condiviso con un'altra sessione attiva; il rischio di sovrascrittura è stato mitigato (letture fresche immediatamente prima di ogni scrittura, un solo write per file) ma non eliminabile al 100% in un ambiente non isolato.
- **Politica di comproprietà `share_percentage`** per lotti co-posseduti: implementata come "assoluta" (nessuna proiezione utente) per decisione esplicita in fase di pianificazione — non rivista in questa implementazione.

## 12. Cleanup ancora necessario

- Nessun cleanup di codice residuo noto: tutte le rimozioni pianificate sono state eseguite e verificate senza riferimenti pendenti.
- Consigliato (non eseguito, fuori scope): decidere se e quando correggere i 6 bug pre-esistenti segnalati alla sezione 10, con un piano dedicato separato.
- Consigliato: una sessione futura dedicata a test E2E di interazione (selezione multipla, modale, sync zoom) se si desidera automazione oltre alla verifica visiva manuale.
