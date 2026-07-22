# Piano implementativo — FIFO Engine v5 (proventi D-1, FEE/TAX, metriche nette)

> **Sorgente spec:** `hig-level-analysis-v5.md` · **Sorgente stato:** codice reale (citazioni `file:riga`).
> **Natura del documento:** piano eseguibile. Non contiene codice applicativo: descrive *dove/come/dipendenze/formula/test/risultato verificabile* per ogni attività.
> **Decisioni prodotto recepite** (confermate dall'utente):
> 1. **Nessun CHECK DB** sul segno (fragile sull'enum del tipo); integrità = Pydantic + scrittura DB solo via API.
> 2. **Nessun toggle lordo/netto**: le metriche nette sono **colonne aggiuntive** mostrate di default (occultabili dal column selector).

---

## 0. Recepimento review pre-run (v5 → run-ready)

Quattro precisazioni integrate dopo la review di fattibilità, **senza cambiare l'architettura** (dettaglio nelle sezioni citate):

1. **Controvalore target dei trade esplicito (§3.5, Fase 2/3/4).** BUY/SELL portano al motore anche `target_amount`/`target_currency` estendendo `FifoInputTransaction`; il motore usa `|target_amount|` come `TradeValue` — nessuna riconversione interna, nessuna mappa parallela, nessun uso accidentale del nativo.
2. **Fonte di verità unica del pool (§3.4, Fase 3).** `NativePool` è canonico; `TargetPool = FXConvert(NativePool)` una sola volta; i `target_amount` per-evento servono **solo** a pesi e audit e **non** si sommano per formare `TargetPool`; il running-remainder riconcilia al `TargetPool` canonico.
3. **Due enum di stato distinti (§7.2, Fase 8).** Globale `LotAnalysisStatus = COMPLETE|DEGRADED|FAILED`; per-lotto `LotNetMetricsStatus = AVAILABLE|UNAVAILABLE`. Il campo top-level resta `calculation_status` (no churn) ma perde `UNAVAILABLE`; l'attuale `UNAVAILABLE` globale (caso "nessun dato") va **migrato esplicitamente** prima dell'`api sync`.
4. **UI manual checklist completa (Appendice A).** La lista A–N di §10 è la sintesi; l'Appendice A è il test di accettazione frontend completo (tutte le combinazioni FEE/TAX/previous-day/fallback/orphan/crossing/status/audit).

**Gate pre-run (da passare nel prompt di esecuzione):**
- (1) i trade portano `target_amount`/`target_currency` al motore (§3.5);
- (2) `TargetPool` deriva dalla conversione unica di `NativePool` (§3.4);
- (3) stato globale e per-lotto usano **due enum distinti**, fissati **prima** dell'`api sync` (§7.2);
- (4) l'Appendice A è eseguita per intero come accettazione frontend.

**Nota operativa (rischio principale = operativo, non logico):** il core `fifo_lot_engine.py` ↔ `lots_analysis_service.py` va sviluppato **in sequenza da un solo owner**, con test-gate dopo *contratto → income → pooling → metriche nette* (§11).

---

## 1. Executive summary

### 1.1 Obiettivo
Portare l'intero calcolo economico dei lotti (proventi, FEE, TAX, metriche nette, audit) dentro un
**unico motore FIFO pubblico** — `FifoLotEngine.run(...)` — che oggi esegue solo il replay
quantitativo, e propagare i nuovi valori fino a DTO/API/client/frontend con un merge finale atomico.

Pipeline a tendere (invariata rispetto a v5 §4):

```
LotsAnalysisService  →  FifoLotEngine.run()  →  LotsAnalysisService  →  Frontend
(DB·FX·prezzi·qbq·        1. Quantitative Replay     (history·DTO·API)      (lordo·costi·
 eventi native+target)    2. Economic Pooling/Alloc                          netto·audit·DQ)
                          3. Combined Validation
                          → FifoEngineResult
```

### 1.2 Giudizio di fattibilità: **GO**
La spec v5 è coerente con il codice. Nessun paradosso architetturale residuo. I punti che richiedono
attenzione (non bloccanti) sono elencati in §15. Le criticità note e già risolte in fase di analisi
(v4/v4.1) sono recepite come decisioni chiuse.

### 1.3 Cosa esiste già (da NON rifare)
- Modello **gross** dei lotti (open_value, proceeds, realized/market pnl, total_pnl, total_return, asset_income) — `schemas/portfolio.py:513-545`, `lots_analysis_service.py`.
- **`_FxRateResolver`** date-aware, bulk, senza arrotondamento intermedio (`lots_analysis_service.py:114-150`); income già convertito a `tx.date`.
- **`_unit_price = |amount|/|quantity|`** → `original_cost = |amount|` qbq-safe (`fifo_lot_engine.py:981-984`).
- **Regola 11** segno FEE/TAX su CREATE + import BRIM (`schemas/transactions.py:293-299`, `brim_provider.py:398-410`).
- Replay quantitativo completo (TRANSFER→SPLIT→BUY/SELL/ADJ), frammenti, closure, transfer/transito, crossing (`fifo_lot_engine.py`).

### 1.4 Cosa cambia (in una frase per fase)
| Fase | Cambiamento |
|------|-------------|
| 0 | Fix UPDATE segno (validator condiviso), audit dati legacy (script read-only), rimozione metodi non-qbq. |
| 1 | Income: eleggibilità **D-1**, **scope broker**, transfer From/To, orphan. |
| 2 | Nuova firma `run(...)` + `FifoEngineResult` esteso + tipi audit a 3 livelli. |
| 3 | `EconomicEvent` native+target; FX risolto dal service; motore target-value aware. |
| 4 | Pool FEE/TAX, pesi target, ordine matching same-day→previous-day→fallback→orphan. |
| 5 | Crossing LONG/SHORT: split del costo close/open, closure immutabili. |
| 6 | Audit `EconomicAllocationGroup → TargetOperationAllocation → EconomicLotAllocation` inline. |
| 7 | Accumulatori netti + history nette (allocated_fees/taxes, net_pnl, net_total_return). |
| 8 | `analysis_status` COMPLETE/DEGRADED/FAILED + `net_metrics_status` per lotto + Data Quality. |
| 9 | Portfolio Engine: accumulatori assoluti pre-share + riconciliazione con FIFO assoluto. |
| DTO/FE | Estensione DTO/API, `api sync`, colonne nette (no toggle), modal, audit, i18n. |

### 1.5 Definizione di "fatto" (sintesi; dettaglio in §14)
Un solo percorso quantitativo+economico; income D-1 e broker-aware; FEE/TAX in pool conservativi con
`TradeValue=|amount|` senza qbq; `original_cost` e lordo invariati; netto sottrae FEE+TAX una sola
volta; audit 3 livelli sempre inline; orphan/FX→DEGRADED (nessuna perdita silenziosa); FAILED solo per
errori quantitativi; frontend `check/build/i18n` verdi; checklist UI eseguibile.

---

## 2. Stato corrente verificato

Tabella degli anchor su cui il piano opera. Ogni riga è verificata nel codice.

### 2.1 Motore FIFO — `backend/app/services/fifo_lot_engine.py`
| Elemento | Riga | Nota per il piano |
|----------|------|-------------------|
| `FifoLotEngine.__init__(transactions, broker_shorting, *, split_ratios_by_tx_id, reference_price_lookup)` | `314-341` | La firma cambia in Fase 2: aggiunge `economic_events`, `target_currency`. |
| `run() -> FifoEngineResult` | `343-367` | Diventa la pipeline a 3 stage; oggi esegue solo lo stage quantitativo. |
| `FifoEngineResult(asset_id, classified_events, lots, fragment_intervals, closures, issues)` | `189-196` | Esteso in Fase 2/6/7 (vedi §7). |
| `calculation_status` (property, `COMPLETE`/`DEGRADED`) | `198-200` | Diventa `analysis_status` a 3 stati (Fase 8). |
| `value_for_lot` / `aggregate_value` / `relative_return_for_lot` | `244` / `262` / `283` | **Rimuovere** (Fase 0.4): consumer solo test. |
| `run_fifo_lot_engine(...)` helper | `961-973` | Aggiornare firma (Fase 2). Call-site: `lots_analysis_service.py:224,253`. |
| `_unit_price = |amount|/|quantity|` | `981-984` | Conferma `original_cost=|amount|`, base qbq-safe di `TradeValue`. |
| `_event_sort_key` | `469` | Ordinamento quantitativo TRANSFER→SPLIT→BUY/SELL/ADJ: **invariato**. |

### 2.2 Servizio — `backend/app/services/lots_analysis_service.py`
| Elemento | Riga | Nota |
|----------|------|------|
| Chiamata motore principale | `224` | Passerà anche `economic_events`+`target_currency`. |
| Chiamata motore "performance" (broker-scope allargato) | `253` | Stessa nuova firma. |
| `_allocate_asset_income(...)` | `914-982` | **Da rimuovere** (Fase 1→motore). Bug D vs D-1 e scope broker qui sotto. |
| — eleggibilità `lot.opening_date > tx.date` (usa **D**) | `944` | BUY same-day **inclusa** → va portata a `OpenQty(D-1)`. |
| — **nessun filtro broker** | `942-948` | Income allocato a tutti i lotti dell'asset → va ristretto al broker accreditante. |
| — running-remainder (conserva la somma) | `955-961` | Pattern da riusare nel motore. |
| `_FxRateResolver` (date-aware, bulk, no rounding) | `114-150` | Riuso per preparare `target_amount` degli `EconomicEvent`. |
| `_open_quantity_on_date(fragments, d)` | `~1633` | Base per `OpenQty(D-1)` e per il fallback. |

### 2.3 DTO — `backend/app/schemas/portfolio.py`
| Elemento | Riga | Nota |
|----------|------|------|
| `LotCalculationStatus = Literal["COMPLETE","DEGRADED","UNAVAILABLE"]` | `455` | **Sostituire** con `LotAnalysisStatus` COMPLETE/DEGRADED/FAILED (globale) + `LotNetMetricsStatus` per-lotto; migrare l'`UNAVAILABLE` globale attuale (§7.2). |
| `LotSummarySchema` (gross: `total_pnl`,`total_return`,`asset_income`,`market_pnl`,`pnl`) | `513-545` | Aggiungere `allocated_fees, allocated_taxes, net_total_pnl, net_total_return, net_metrics_status`. |
| `LotValueHistoryPoint` (campo `income`) | `610-622` | Aggiungere `allocated_fees, allocated_taxes`. |
| `LotReturnHistoryPoint` (campo `income`) | `625-638` | Aggiungere `net_pnl, net_total_return, net_metrics_status`. |
| `LotsAnalysisResponse` (`calculation_status`,`data_quality`) | `728-760` | Aggiungere `economic_allocation_groups, asset_orphan_income/fees/taxes`. |

### 2.4 Integrità transazioni
| Elemento | Riga | Nota |
|----------|------|------|
| `TXCreateItem._business_rules` (Regole 5–12; Regola 11 segno FEE/TAX `amount<0` a `:296`) | `~204-343` | **Fattorizzare** in validator condiviso (Fase 0.1). |
| packing multi-errore | `319-341` | Riusare così com'è dal validator condiviso. |
| `TXUpdateItem._business_rules` (**solo `id>0`**) | `548-558` | Il buco: nessuna business rule sul merge. |
| Loop update service: `cash→tx.amount/currency` raw | `1149-1151` | Nessuna rivalidazione dello stato finale. |
| Guardia esistente = solo swap-group del tipo | `1139-1142` | Va affiancata dalla rivalidazione completa. |
| BRIM `build_transaction_or_issue` avvolge `TXCreateItem` | `398-410` | Import eredita la Regola 11 (già ok). |

### 2.5 DB — `backend/app/db/models.py`
| Elemento | Riga | Nota |
|----------|------|------|
| `Transaction.__table_args__` = **solo indici, nessun CHECK** | `590-595` | **Resta così** (decisione: no CHECK type-dipendenti). |
| `amount Numeric(18,6)` | `615-619` | — |
| CheckConstraint esistenti (NON type-dipendenti): `fx_rates base<quote`, route, asset | `813`,`861`,`437` | Mostrano che i CHECK si usano solo per invarianti strutturali stabili. |
| Migrazioni: solo `001_initial.py` | — | Nessuna nuova migrazione richiesta da questo piano. |
| `./dev.py db check` → `verify_db_check_constraints.py` **inesistente** | `dev.py:368` | Discrepanza preesistente, fuori scope (annotata in §15). |

### 2.6 Portfolio Engine — `backend/app/services/portfolio_engine.py`
| Elemento | Riga | Nota |
|----------|------|------|
| FEE/TAX (frame / pre-frame) → `per_fees_taxes[(asset_id,broker_id)]` | `842-851` / `578-582` | Base per `per_fees_absolute`/`per_taxes_absolute`. |
| Income (frame / pre-frame) → `per_income[(asset_id,broker_id)]` | `834-840` / `576-578` | Base per `per_income_absolute`. |
| accumulatori `dict[(int,int),Decimal]`, export | `537-541` / `990-995` | Chiave riconciliazione già `(asset_id,broker_id)`. |
| `share_percentage` map | `1804-1805` | — |
| share applicata **inline e sparsa** | `224-247`,`499-505`,`560-563`,`741-749`,`1165-1191` | **Nessun choke point pre-share** → Fase 9 introduce accumulatori assoluti separati. |
| Non chiama FIFO/LotsAnalysis | — | Doppio percorso income/fee/tax → riconciliazione esplicita (Fase 9). |

### 2.7 Frontend — `frontend/src/lib/components/brokers/lots/`
| Componente | File | Nota |
|------------|------|------|
| Orchestratore | `LotsAnalysisPanel.svelte` | Fetch analisi+selezione; instrada i nuovi campi. |
| Tabella/cards | `UnifiedLotsTable.svelte` (colonne `468-620`, footer `439-465`, `ColumnVisibilityToggle`) | Nuove colonne nette (mostrate di default). |
| Modale lotto | `LotCustodyModal.svelte` | Breakdown netto + audit. |
| Chart | `LotComparisonChart.svelte` (mode valore/rendimento, nessun toggle lordo/netto) | Serie nette senza toggle globale. |
| Gantt tooltip | `LotGanttChart.svelte` (`817-858`) | Aggiungere netto/stato. |
| Data Quality | `ui/feedback/DataQualityBanner.svelte` | Nuovi codici + status. |
| Tipi generati | `frontend/src/lib/api/generated.ts` (`LotSummarySchema` 3974-4035, `LotValueHistoryPoint` 4407-4420, `LotReturnHistoryPoint` 4422-4448, `LotsAnalysisResponse` 4298-4378) | Rigenerati da `./dev.py api sync`. |
| i18n | `frontend/src/lib/i18n/{en,it,fr,es}.json` (`brokers.lots.*`, `brokers.lots.modal.*`, `dataQuality.*`) | Nuove chiavi. |
| Persistenza/toggle | `frontend/src/lib/utils/storage.ts`, `ViewModeToggle.svelte` | Pattern per la visibilità colonne. |

### 2.8 Comandi reali (dal repo)
- **Test backend:** `./dev.py test services roi-fifo-utils` (→ `backend/test_scripts/test_services/test_financial/`, include `test_fifo_lot_engine.py`, `test_lots_analysis_service.py`), `./dev.py test services portfolio-engine`, `./dev.py test services financial-utils`, `./dev.py test schemas all`, `./dev.py test api all`. Singolo test: `pipenv run pytest backend/test_scripts/.../test_file.py::test_name -v`.
- **API/client:** `./dev.py api sync` (schema + client TS).
- **Frontend:** `./dev.py front check` (svelte-check), `./dev.py front build`, `./dev.py front format`.
- **i18n:** `./dev.py i18n audit`.

---

## 3. Architettura finale

### 3.1 Contratto del motore
```
FifoLotEngine(
    transactions,            # Sequence[TransactionLike|FifoInputTransaction]  (quantitativi; arricchiti dal service con target_amount/target_currency — §3.5)
    broker_shorting,
    *,
    economic_events,         # Sequence[EconomicEvent]  (DIVIDEND/INTEREST/FEE/TAX, native+target)
    target_currency,         # str — valuta comune di confronto/metriche
    split_ratios_by_tx_id=None,
    reference_price_lookup=None,
).run() -> FifoEngineResult
```
Stage privati (coesi, testabili, non pubblici):
1. `_run_quantitative_replay()` — l'attuale logica (invariata).
2. `_run_economic_pooling_and_allocation()` — pool, matching, allocazione, orphan, accumulatori.
3. `_run_combined_validation()` — quantità, conservazione nativa/target, scope, status.

### 3.2 `EconomicEvent` (nuovo tipo, §7.2 v5)
`(id, date, type, asset_id, broker_id, native_amount, native_currency, target_amount, target_currency, description)`.
Il motore usa `target_amount` per pesi/pool/metriche e conserva `native_*` per l'audit. **Non** accede
al sistema FX (Opzione B). Gli eventi assetless restano fuori dal FIFO (§8.1 v5).

### 3.3 Invarianti economici (feed-forward, §18 v5)
```
GrossEconomicValue_i = OpenValue_i + SaleProceeds_i + GrossIncome_i
GrossPnL_i           = GrossEconomicValue_i − OriginalCost_i
NetPnL_i             = GrossPnL_i − AllocatedFees_i − AllocatedTaxes_i
GrossReturn_i        = GrossPnL_i / OriginalCost_i          (OriginalCost_i > 0)
NetReturn_i          = NetPnL_i  / OriginalCost_i           (OriginalCost_i > 0)
```
`original_cost` invariato; FEE/TAX non toccano `opening_unit_price`, PMC/WAC, proceeds/PnL lordi.

### 3.4 Conservazione e fonte di verità del pool (§21 v5 + review pre-run)
Regola canonica in **una sola direzione** (evita due fonti di verità):
1. Il service raccoglie e risolve **tutti** i tassi FX necessari in un unico bulk load.
2. Ogni evento conserva `native_amount` **e** `target_amount` (usati **solo** per pesi e audit).
3. Il **totale canonico** del pool è `NativePool` convertito **una sola volta**:
   `NativePool_P = Σ_e |NativeAmount_e|` · `TargetPool_P = FXConvert(NativePool_P, c_P, target, D_P)`.
   I `target_amount` dei singoli eventi **non** vengono sommati per determinare `TargetPool`.
4. Pesi trade `TargetTradeValue_k = |target_amount_k|`; pesi income `α_k = |target_amount_k| / Σ_j |target_amount_j|`.
5. Il **running-remainder** riconcilia le allocazioni al `TargetPool` **canonico** (l'ultimo lotto in ordine stabile assorbe il residuo).

Conservazione (per ogni pool): `Σ NativeAllocation_i + NativeOrphan = NativePool` **e**
`Σ TargetAllocation_i + TargetOrphan = TargetPool`. Poiché la chiave-pool include **data e valuta nativa**,
tutti gli eventi condividono `(D_P, c_P)`: la conversione unica del totale è esatta e col resolver attuale
(nessun arrotondamento intermedio, `lots_analysis_service.py:114-150`) coincide numericamente con la somma
dei target per-evento — ma la conversione del totale resta l'**unica** fonte di verità. Pattern
running-remainder già usato a `lots_analysis_service.py:955-961`.

### 3.5 Controvalore target dei trade (review pre-run)
BUY/SELL sono **eventi quantitativi**, ma i pesi FEE `β_k` richiedono il loro controvalore in
target_currency. Per non riconvertire dentro il motore né costruire mappe parallele, il controvalore
target viaggia **sulla stessa struttura del trade**: si estende `FifoInputTransaction`
(`fifo_lot_engine.py:54-65`) con due campi opzionali:
```python
target_amount: Decimal | None = None      # |amount| convertito in target_currency alla data del trade
target_currency: str | None = None
```
- Il **service** (che già risolve FX via `_FxRateResolver`) popola `target_amount`/`target_currency`
  quando costruisce le input transaction, come già fa per gli `EconomicEvent` (Opzione B, simmetrica).
- Il **motore** usa `TradeValue_k = |target_amount_k|` per `β_k`; **nessuna** riconversione interna,
  **nessun** accesso FX, **nessun** uso accidentale del nativo quando le valute differiscono.
- **Fallback:** se `target_amount` manca (FX assente), il trade entra nel percorso **degradato** del suo
  pool (`FX_RATE_MISSING_FOR_ALLOCATION`, `net_metrics_status=UNAVAILABLE`), **non** si ricade sul nativo.
- **Audit:** `native_amount=|amount|` e `target_amount` restano entrambi disponibili per la riconciliazione.

---

## 4. Dependency map

### 4.1 Grafo di dipendenza tra fasi
```
Fase 0 (integrità+qbq) ─┐
                        ├─▶ Fase 2 (contratto run/Result/audit types) ─▶ Fase 3 (FX/target)
Fase 1 (income D-1) ────┘                                                     │
                                                                              ▼
                                                        Fase 4 (pool FEE/TAX + matching)
                                                                              │
                                              ┌───────────────────────────────┤
                                              ▼                               ▼
                                     Fase 5 (crossing)             Fase 6 (audit 3 livelli)
                                              └───────────────┬───────────────┘
                                                              ▼
                                              Fase 7 (netto + history) ─▶ Fase 8 (status/DQ)
                                                              │
                                                              ▼
                                              DTO/API + api sync ─▶ Frontend (8-9) ─▶ UI manual
                                                              │
                                                              ▼
                                              Fase 9 (Portfolio Engine pre-share/riconciliazione)
```

### 4.2 File "caldi" condivisi (ownership esclusiva, no parallelismo su di essi)
`fifo_lot_engine.py`, `lots_analysis_service.py`, `schemas/portfolio.py`,
`frontend/.../LotsAnalysisPanel.svelte`, `UnifiedLotsTable.svelte`, `LotComparisonChart.svelte`,
`frontend/src/lib/i18n/*.json`, `frontend/src/lib/api/generated.ts`.

### 4.3 Attività scorporabili (dettaglio in §11)
Fase 0.1 UPDATE + audit segni · qbq hardening · accumulatori Portfolio pre-share (Fase 9) ·
progettazione colonne/i18n (dopo congelamento schema DTO).

---

## 5. Fasi backend

Formato per ogni fase: **Obiettivo · Stato attuale · Modifiche · File/simboli · Formule/algoritmi ·
Nuovi tipi · Dipendenze · Test · Gate · Rischi.**

### Fase 0 — Integrità delle transazioni e hardening qbq

#### 0.1 — Fix UPDATE segno FEE/TAX (validator condiviso)
- **Obiettivo:** una FEE/TAX non può diventare positiva via UPDATE; lo stato finale del merge rispetta le stesse business rule del CREATE.
- **Stato attuale:** `TXUpdateItem._business_rules` valida solo `id>0` (`transactions.py:548-558`); il service applica `cash→tx.amount` raw senza rivalidare (`transaction_service.py:1149-1151`); unica guardia = swap-group tipo (`:1139-1142`).
- **Modifiche:**
  1. Estrarre le Regole 5–12 da `TXCreateItem._business_rules` (`transactions.py:~204-343`) in una **funzione pura condivisa** `validate_transaction_business_rules(*, type, asset_id, cash, quantity, asset_event_id, cost_basis_mode) -> list[PydanticCustomError]`, riusando il packing multi-errore (`:319-341`).
  2. `TXCreateItem._business_rules` chiama la funzione condivisa (comportamento invariato; i test CREATE esistenti restano verdi).
  3. Nel loop update del service (`transaction_service.py:1131-1172`) costruire lo **stato finale candidato** = `(tx corrente) + (patch)` per i campi `type, asset_id, quantity, cash(amount+currency), asset_event_id, cost_basis_mode`, poi invocare la funzione condivisa **prima di persistere**; su errori → `TXValidationIssue(operation="update", ...)` con lo stesso codice/params del CREATE (nessun percorso di errore nuovo lato frontend).
- **File/simboli:** `schemas/transactions.py` (nuova funzione + `TXCreateItem._business_rules`), `services/transaction_service.py` (loop `parsed_updates`).
- **Nuovi tipi:** nessuno (solo la funzione condivisa).
- **Dipendenze:** nessuna a monte. Indipendente dal resto (§11).
- **Test** (`test_schemas/` + `test_api/test_transactions_api.py`, `test_transactions_validate.py`):
  - CREATE FEE `+50` → rifiutata; CREATE FEE `-50` → ok (regressione).
  - UPDATE FEE→`cash.amount=+50` → **rifiutata**; UPDATE TAX→`+X` → rifiutata.
  - UPDATE `type BUY→SELL` + `cash` coerente → ok; `type BUY→FEE` con `amount>0` → rifiutata.
  - Cambio `type`+`cash` nella stessa patch: validazione sullo stato finale, non sui singoli campi.
  - UPDATE negativo valido (FEE resta `-`) → accettato.
  - Comando: `./dev.py test schemas all` + `./dev.py test api all` (o pytest mirato sul file transazioni).
- **Gate:** nessun modo, via API, di persistere FEE/TAX con `amount>=0` (CREATE, IMPORT, UPDATE).
- **Rischi:** duplicazione logica se non fattorizzata → mitigato dal validator unico; retro-compatibilità messaggi errore → mantenere codici/`ctx` identici. **Non accoppiare** `TXCreateItem` a un modello di update: la funzione condivisa riceve lo **stato finale normalizzato** (type, asset_id, cash, quantity, asset_event_id, cost_basis_mode), non i DTO → CREATE e UPDATE usano la stessa regola senza dipendere l'uno dall'altro.

> **✅ FATTO (2026-07-21)** — Estratta `validate_transaction_business_rules(*, tx_type, asset_id, quantity, cash, asset_event_id, cost_basis_mode) -> list[PydanticCustomError]` a livello di modulo in `schemas/transactions.py` (Regole 5–12); `TXCreateItem.validate_transaction_rules` la richiama via `errors.extend(...)` (Regole 1–4 + field-positivity + packing invariati). Iniettata la validazione dello **stato finale** nel loop update di `transaction_service.py` (`:1168-1197`): costruisce `final_cash = Currency(code=tx.currency, amount=tx.amount)` post-merge, applica il validator condiviso, e su ogni errore appende un `TXValidationIssue(operation="update", error=rerr.message(), code=rerr.type, params=dict(rerr.context))` + `continue`. Poiché un `issue` non vuoto → `committed=False` (`:1518-1527`) → il router non committa e il batch fa rollback: la `tx` mutata non viene mai persistita. Param `tx_type` (non `type`) per evitare shadowing/ruff A002. Aggiunti 3 test a `test_transactions_validate.py` (UPDATE FEE→positiva rifiutata; UPDATE FEE negativa accettata; type-swap DEPOSIT→WITHDRAWAL senza flip segno rifiutato). **Verifica:** schemas+validate 80 passed; transactions_api 22+1skip; batch/split/promote 20 passed; ruff+black clean.
> **⚠️ Fuori pista**: la validazione dello stato finale rifiuterebbe ora anche un edit di campo non correlato (es. `description`) su una FEE/TAX *legacy-invalida*. Ritenuto accettabile/desiderabile (l'audit 0.2 mostra 0 righe simili; forza la bonifica). Annotato, non bloccante.

#### 0.2 — Audit dati legacy (script diagnostico read-only)
- **Obiettivo:** confermare che i dati esistenti rispettano i segni, così la matematica può assumere `CostTotal = −Amount` senza `abs()` difensivo obbligatorio.
- **Stato attuale:** nessuno script di audit segni.
- **Modifiche:** aggiungere uno **script di sola lettura** (es. `backend/test_scripts/test_db/audit_transaction_signs.py`, coerente con `db_schema_validate.py`) che riporta: FEE/TAX con `amount>=0`; BUY con `amount>0`; SELL con `amount<0`; DIVIDEND/INTEREST con `amount<=0`. Output: conteggi + elenco `id` anomali. **Non** modifica dati; comportamento su anomalie = report (correzione manuale/API).
- **File/simboli:** nuovo script; nessuna modifica a modelli/migrazioni.
- **Dipendenze:** indipendente.
- **Test:** esecuzione manuale su DB popolato (`./dev.py db create-clean --test` + populate) → 0 anomalie attese.
- **Gate:** report pulito su prod e test prima di rimuovere l'`abs()` difensivo nello stage economico. Lo script è un **gate diagnostico pre-deploy read-only**, da eseguire sul DB interessato, **non** un test automatico permanente.
- **Rischi:** dataset reali con segni storici incoerenti → in tal caso mantenere l'assert difensivo (0.3) e correggere i dati via API.

> **✅ FATTO (2026-07-21)** — Creato `backend/test_scripts/test_db/audit_transaction_signs.py` (read-only, coerente con `db_schema_validate.py`): 4 regole segno (FEE/TAX `amount>=0`; BUY `amount>0`; SELL `amount<0`; DIV/INT `amount<=0`), stampa conteggi + elenco `id` anomali, exit 0 pulito / 1 anomalie. Eseguito sul DB reale: **36 FEE/TAX, 73 BUY, 11 SELL, 33 DIV/INT → 0 anomalie, CLEAN** → confermata l'assunzione `CostTotal = −Amount` senza `abs()` difensivo obbligatorio. ruff+black clean. Run: `PYTHONPATH=. pipenv run python backend/test_scripts/test_db/audit_transaction_signs.py`.

#### 0.3 — Vincolo DB: **NON introdotto** (decisione)
- **Decisione:** niente CHECK DB type-dipendente sul segno (fragile rispetto all'enum `TransactionType`); l'integrità è garantita da Pydantic e dall'assunzione "il DB si scrive solo via API". Coerente con `Transaction.__table_args__` (solo indici, `models.py:590-595`) e con l'uso dei CHECK riservato a invarianti strutturali stabili (`fx_rates base<quote` `:813`).
- **Conseguenze nel piano:**
  - Nessuna migrazione Alembic aggiunta.
  - Nello stage economico (Fase 4) resta un'**asserzione difensiva interna non fatale**: se un `EconomicEvent` FEE/TAX arriva con segno inatteso, si usa `abs(amount)` e si emette un `FifoDataQualityIssue` diagnostico (`ECONOMIC_EVENT_UNEXPECTED_SIGN`, severity WARNING) — **non** una policy economica. L'anomalia è **loggata chiaramente** nel log applicativo, pur non essendo esposta come Data Quality pubblica.
  - `ECONOMIC_EVENT_UNEXPECTED_SIGN` NON compare come codice Data Quality pubblico (§23.5 v5): resta interno/diagnostico.
- **Gate:** lo stage economico non produce risultati errati anche se un dato incoerente sfuggisse a monte.

> **✅ CONFERMATO (2026-07-21) — nessun codice** — Decisione ribadita: nessun CHECK DB, nessuna migrazione. L'asserzione difensiva `ECONOMIC_EVENT_UNEXPECTED_SIGN` sarà implementata come guardia interna loggata dentro lo stage economico (Fase 4), non ora. L'audit 0.2 (0 anomalie) supporta la scelta.

#### 0.4 — Hardening `quote_base_quantity` (rimozione metodi non-qbq)
- **Obiettivo:** eliminare un rischio latente di valutazione ×qbq errata.
- **Stato attuale:** `value_for_lot` (`fifo_lot_engine.py:244`), `aggregate_value` (`:262`), `relative_return_for_lot` (`:283`) non qbq-aware; **consumer solo test** (`test_fifo_lot_engine.py:210,416,417,418`); citati in `mkdocs_src/docs/developer/backend/transactions/fifo_lot_engine.md:56,82`.
- **Modifiche:**
  1. Ricerca esaustiva preventiva: `rg -n "value_for_lot|aggregate_value|relative_return_for_lot"` (atteso: solo motore + test + docs) prima della rimozione.
  2. Rimuovere i 3 metodi e i dataclass di supporto se orfani (`LotValuation` `:171`, `AggregatedLotValuation` `:181` — verificare zero consumer residui).
  3. La valutazione di mercato resta nel service via `OpenValue = (Quantity/QBQ)·MarketQuote` (già così); FEE/TAX **non** subiscono scaling qbq.
  4. Aggiornare `test_fifo_lot_engine.py` sostituendo le asserzioni sui metodi rimossi con **test qbq-aware permanenti** a livello service (o helper locale ai test): `Quantity=1000, QBQ=100, MarketQuote=98,50 → OpenValue=985`; più asserzioni gross/net P&L e relative return che NON dividano/moltiplichino per qbq gli importi cash.
  5. Aggiornare la doc `fifo_lot_engine.md` (rimuovere i riferimenti ai metodi).
- **File/simboli:** `fifo_lot_engine.py`, `test_fifo_lot_engine.py`, `mkdocs_src/.../fifo_lot_engine.md`.
- **Dipendenze:** indipendente; da fare prima o durante Fase 2 (stessa area file).
- **Test:** `./dev.py test services roi-fifo-utils` (suite `test_financial/`), + test qbq=100 su bond.
- **Gate:** i 3 metodi non esistono più; suite verde; test qbq=100 permanente presente.
- **Rischi:** un consumer nascosto → mitigato dalla ricerca esaustiva; docs disallineate → aggiornate contestualmente.

> **✅ FATTO (2026-07-21)** — `rg` esaustivo (`value_for_lot|aggregate_value|relative_return_for_lot|LotValuation|AggregatedLotValuation`) → consumer solo motore + `test_fifo_lot_engine.py` + mkdocs (i ref nel journal sono storici). Rimossi da `fifo_lot_engine.py` i 3 metodi + 2 dataclass orfane (`LotValuation`, `AggregatedLotValuation`); mantenuti `Sequence` (ancora usato) e i campi `reference_unit_price`/`reference_price_source` (ancora popolati). In `test_fifo_lot_engine.py` sostituite le asserzioni sui metodi rimossi con calcoli inline dai campi raw dei lotti (preservate aggregazione multi-lotto + relative-return). Aggiornato `mkdocs_src/.../fifo_lot_engine.md`. Il test qbq=100 permanente richiesto **esiste già** (`test_lots_analysis_service.py:1287` `test_bond_quote_base_quantity_scales_open_value_and_pnl`, `open_value=(1000/100)·102,50=1025`) → nessun duplicato aggiunto. **Verifica:** suite `test_financial/` completa → **236 passed**; ruff+black clean.

---

### Fase 1 — Semantica dei proventi (income allocato dal motore)

> Nota migrazione: l'allocazione income si sposta dal service al motore. Per evitare doppio conteggio,
> `_allocate_asset_income` viene **rimosso nello stesso commit** in cui il motore inizia ad allocare
> income (vedi §12). Fino a Fase 2/4 la logica D-1/scope può essere sviluppata come helper puro e
> testata in isolamento.

#### 1.1 — Regola D-1
- **Obiettivo:** `EligibleQuantity_i(D) = OpenQuantity_i(D−1)`.
- **Stato attuale:** eleggibilità a **D** (`lots_analysis_service.py:944`, `lot.opening_date > tx.date`) → BUY same-day erroneamente inclusa.
- **Modifiche:** l'insieme eleggibile per un income in `D` usa la quantità aperta **alla fine di `D−1`**, cioè `_open_quantity_on_date(fragments, D − 1 giorno)`; equivalentemente lo stato prima di applicare gli eventi di `D`.
- **Casi coperti:** BUY in D → esclusa; SELL in D → inclusa (era aperta a D−1); lotto aperto **e** chiuso in D → escluso; lotto interamente venduto in D → **ancora eleggibile** al provento di D; split same-day → pesi invarianti (§1.2 v5, `rq_i/Σrq_j = q_i/Σq_j`).
- **Formula peso:** `w_i = OpenQty_i(D−1) / Σ_j OpenQty_j(D−1)` sui lotti eleggibili.
- **Test** (`test_lots_analysis_service.py` / nuova suite motore): BUY same-day esclusa; SELL same-day inclusa; open+close same-day escluso; split same-day (pesi pre/post identici).
- **Gate:** nessun provento allocato a lotti nati in D.

#### 1.2 — Scope broker
- **Obiettivo:** eleggibilità ristretta a stesso **asset**, **broker accreditante**, direzione **LONG**, `OpenQty(D−1)>0`, custody-compatibile.
- **Stato attuale:** nessun filtro broker (`lots_analysis_service.py:942-948`) → income spalmato su tutti i lotti dell'asset.
- **Modifiche:** aggiungere il filtro `broker` dell'evento economico all'insieme eleggibile: `L_{a,b,D} = { L_i : direction=LONG, EligibleQty_i(D)>0, CustodyCompatible_i(b,D) }`.
- **Simulazione di verifica (§3.2 task):** Asset X, Directa 30q, IBKR 70q, DIVIDEND +100 su Directa → tutti i 100 ai lotti Directa, 0 a IBKR.
- **Test:** broker scope (2 broker, income su uno solo).
- **Gate:** income mai allocato a lotti di broker diversi dall'accreditante.

#### 1.3 — Transfer From/To
- **Obiettivo:** durante il transito, attribuire correttamente i proventi.
- **Regole (§9 v5):**
  - Income sul **From** → frammenti `BROKER` sul From **+** frammenti `IN_TRANSIT` con `source_broker_id=From`.
  - Income sul **To** → solo quantità **già presenti sul To a D−1**.
  - Income sul **To nel giorno di arrivo** (a D−1 ancora in transito) → **nessun lotto eleggibile** → `asset_orphan_income` + `ASSET_INCOME_NO_ELIGIBLE_LOTS`, senza eccezioni end-of-day.
- **Stato attuale:** `FragmentInterval` (`fifo_lot_engine.py:123-134`) espone già `custody_type` (BROKER/IN_TRANSIT), `broker_id`, `source_broker_id`, `destination_broker_id`, `start_date`, `end_date`; usati da `active_fragments`/logica custody (`:218-239`) → informazione sufficiente per From/To e transito.
- **Test:** From durante transito; To durante transito (solo pre-esistenti); To giorno di arrivo → orphan; provento su entrambi i broker → accrediti distinti senza doppio conteggio.
- **Gate:** nessuna doppia allocazione, nessuna perdita, nessun accredito retroattivo a frammenti non ancora esistenti.

#### 1.4 — Pool income e orphan
- **Obiettivo:** DIVIDEND ∪ INTEREST con stessa chiave `(asset, broker, date, native_currency, target_currency)` condividono l'eleggibilità → il pool è **interamente allocabile** oppure **interamente orphan** (dimostrato in v4.1: l'eleggibilità è `f(asset,broker,D−1)`, indipendente dal tipo). **Non** implementare rami "uno allocabile e uno orphan".
- **Orphan (§12 v5):** `L_{a,b,D}=∅` → intero pool income → `asset_orphan_income`; `ASSET_INCOME_NO_ELIGIBLE_LOTS` severity WARNING; `analysis_status=DEGRADED`; importo **non** ridistribuito ad altri broker/lotti.
- **Precondizione documentata:** vale finché l'eleggibilità non dipende da tipo/Asset Event/ex-date per-transazione (`asset_event_id` NON entra nel filtro lotti — oggi non entra).
- **Test:** pool interamente allocabile; pool interamente orphan; (test negativo) impossibilità mix allocabile/orphan nello stesso pool.

> **✅ FATTO (Fase 1 — income nel motore)** — 2025
> Migrazione completata: allocazione income spostata dal service al motore.
> - **Motore** (`fifo_lot_engine.py`): `run()` → `_allocate_economics()` → `_allocate_income_pools()`; helper `_eligible_income_quantity(fragments, broker, cutoff=D−1)` (transfer-aware: `IN_TRANSIT` conta per `source_broker_id`). Pool key `(broker,date,type,native_ccy,target_ccy)`; running-remainder su `TargetPool` canonico (native e target riconciliati indipendentemente); orphan → `asset_orphan_income` + issue `ASSET_INCOME_NO_ELIGIBLE_LOTS`. Regola audit `ASSET_INCOME_HOLDINGS`, context `HOLDING`.
> - **Service** (`lots_analysis_service.py`): `_build_income_economic_events()` risolve FX (native+target) **prima** del run e passa `economic_events`+`target_currency`; `_extract_income_outputs()` ricava `income_by_lot` (accumulatori), `income_prefix_by_lot` (gruppi audit), `income_events_payload` (per-tx + lot eleggibili condivisi). `_allocate_asset_income` **rimosso**. `_FxRateResolver.load()` reso **incrementale** (due load: income pre-run, valuation post-run).
> - **Data Quality**: `ASSET_INCOME_NO_ELIGIBLE_LOTS` aggiunto a `IssueCode` (engine Literal + DTO enum), `_WARNING_ISSUE_CODES`, `_message_key_for_issue` → `dataQuality.assetIncomeNoEligibleLots` (chiave i18n FE da aggiungere in Fase 8).
> - **Test**: +11 test motore (`TestAssetIncomeAllocation`): pro-rata, BUY same-day escluso, SELL same-day incluso, scope broker (Directa/IBKR), orphan+DEGRADED, transfer From/To durante transito/dopo arrivo, pool conservato, DIVIDEND/INTEREST gruppi distinti, FX target. **247 finanziari verdi** (236+11), ruff+black clean.
> - **⚠️ Fuori pista**: comportamento cambiato per "income dopo chiusura lotto" — prima silenziosamente scartato, ora orphan+DEGRADED+DQ (voluto da §1.4). Test esistenti (`test_income_after_lot_closed`, `test_closed_lot_history_keeps_income_crystallized`) restano verdi (non asseriscono su status/DQ). FX-missing su income resta silent-fallback (raw amount) come oggi; `FX_RATE_MISSING_FOR_ALLOCATION` rinviato a Fase 3.

---

### Fase 2 — Contratto unico del motore

- **Obiettivo:** un solo entrypoint `run()` con `FifoEngineResult` esteso; call-site aggiornati; tipi audit definiti.
- **Stato attuale:** `run()` e `run_fifo_lot_engine` senza input/output economici (`fifo_lot_engine.py:343-367,961-973`); call-site `lots_analysis_service.py:224,253`.
- **Modifiche:**
  1. Estendere `__init__`/`run_fifo_lot_engine` con `economic_events: Sequence[EconomicEvent]` e `target_currency: str` (default vuoto/`[]` per retro-compatibilità **solo interna e temporanea**; al merge finale i call-site passano sempre gli eventi). Estendere inoltre `FifoInputTransaction` (`:54-65`) con `target_amount`/`target_currency` popolati dal service (§3.5), così i trade portano il proprio controvalore target al motore.
  2. Estendere `FifoEngineResult` (`:189-196`) con: `economic_allocation_groups`, `economic_accumulators_by_lot`, `asset_orphan_income`, `asset_orphan_fees`, `asset_orphan_taxes`, `analysis_status`.
  3. Definire i **tipi audit a 3 livelli** (dataclass frozen) `EconomicAllocationGroup → TargetOperationAllocation → EconomicLotAllocation` (campi in §7.3 di questo piano).
  4. Aggiornare i 2 call-site del service per costruire e passare `economic_events`+`target_currency`.
- **Nuovi tipi:** `EconomicEvent`, `EconomicAllocationGroup`, `TargetOperationAllocation`, `EconomicLotAllocation`, `LotEconomicAccumulators`, enum `AllocationRule`, `AllocationContext`.
- **Dipendenze:** dopo Fase 1 (logica income) e Fase 0.4 (stessa area). Precede 3/4/5/6.
- **Test:** costruzione risultato con `economic_events=[]` → identico all'attuale (regressione replay quantitativo); smoke test dei nuovi campi vuoti.
- **Gate:** un solo `run()`; nessun percorso economico alternativo pubblico.
- **Rischi:** rottura call-site → coperta da default temporaneo + test regressione.

> **✅ FATTO — solo scaffolding contratto (2026-07-21)** — Landato il **gate 1 del reviewer ("contratto")** in modo retro-compatibile e verde:
> - `fifo_lot_engine.py`: aggiunti alias `Literal` `EconomicType`/`AllocationContext`/`AllocationRule` (coerenti con lo stile `Direction`/`EventKind` del modulo); definite le dataclass frozen `EconomicEvent`, `EconomicLotAllocation`, `TargetOperationAllocation`, `EconomicAllocationGroup`, `LotEconomicAccumulators` (campi da §7.3). `FifoInputTransaction` esteso con `target_amount`/`target_currency` (`Optional=None`; `from_transaction` li lascia `None` → li popola il service in Fase 3). `FifoEngineResult` esteso con `economic_allocation_groups`/`economic_accumulators_by_lot`/`asset_orphan_income`/`asset_orphan_fees`/`asset_orphan_taxes` (default vuoti via `field(default_factory=...)`/`Decimal("0")`). Property `calculation_status`→**`analysis_status`** 3-stati (`COMPLETE|DEGRADED|FAILED`; `FAILED` riservato). `__init__`/`run_fifo_lot_engine` estesi con `economic_events: Sequence[EconomicEvent]=()` + `target_currency: str=""` (memorizzati su `self`).
> - `lots_analysis_service.py:468`: unico consumer del property aggiornato a `engine_result.analysis_status`; il **campo DTO** `LotsAnalysisResponse.calculation_status` resta invariato (§7.2).
> - Doc `mkdocs_src/.../fifo_lot_engine.md` (righe 52/135/323) allineata al rename.
> - **Verifica gate:** con `economic_events=()` ovunque il replay quantitativo è invariato → suite `test_financial/` **236 passed**; ruff+black clean.
> **⚠️ Residuo Fase 2 (NON fatto)**: punto 4 (i 2 call-site del service costruiscono/passano `economic_events`+`target_currency`) è rinviato al gate 2 ("income"), perché ha senso solo quando il motore inizia ad allocare (Fase 1+4). I nuovi tipi audit/accumulatori sono definiti ma non ancora prodotti finché non parte lo stage economico.

---

### Fase 3 — FX e preparazione target

- **Obiettivo:** motore *target-value aware, FX-mechanism agnostic* (Opzione B).
- **Stato attuale:** `_FxRateResolver` (`lots_analysis_service.py:114-150`) già date-aware/bulk/no-rounding; income già convertito a `tx.date`.
- **Modifiche:**
  1. Nel service, **prima del run**, raccogliere tutti i bisogni FX (income, trade candidati, pool FEE/TAX) verso `target_currency` e risolverli in un unico caricamento bulk (riuso `_collect_fx_needs`/`_FxRateResolver`).
  2. Costruire gli `EconomicEvent` con `native_amount/native_currency` + `target_amount/target_currency`.
  3. **Nessuna** conversione DB/async dentro il motore.
- **Conversione del pool (§10.2 v5 + §3.4):** poiché gli eventi di un pool condividono data e valuta nativa, il service converte **una sola volta** il totale: `TargetPool = FXConvert(NativePool, NativeCurrency, TargetCurrency, Date)`. `TargetPool` è la **fonte di verità** (§3.4): i `target_amount` per-evento servono solo a pesi/audit e **non** si sommano per formare `TargetPool`. (Dimostrazione v4.1: pesi FX-invarianti dentro il pool → drift 0.)
- **Trade value:** `NativeTradeValue_k = |TransactionAmount_k|`; `TargetTradeValue_k = |FXConvert(TransactionAmount_k, TxCurrency_k, TargetCurrency, Date_k)|`. **Nessuna** ricostruzione da quantità·prezzo; **nessun** qbq.
- **FX mancante (§7.4 v5):** `FX_RATE_MISSING_FOR_ALLOCATION` (WARNING); `analysis_status=DEGRADED`; allocazioni target non disponibili per quel pool; `net_metrics_status=UNAVAILABLE` sui lotti coinvolti; metriche **gross** indipendenti preservate quando calcolabili.
- **Test:** target EUR; target USD; pool omogeneo mono-valuta; trade multivaluta; FX mancante; conservazione nativa; conservazione target.
- **Gate:** nessuna query FX nel motore; conservazione nativa e target verificate.

---

### Fase 4 — Pooling e allocazione economica

- **Chiave pool (§10.1 v5):** `(asset_id, broker_id, date, economic_type, native_currency, target_currency)`. Eventi assetless esclusi dal FIFO.

#### 4.1 — Pool FEE
- **Target same-day:** tutti i BUY/SELL compatibili del giorno; **ADJUSTMENT_IN/OUT esclusi**.
- **Pesi e quote:** `β_k = TargetTradeValue_k / Σ_j TargetTradeValue_j` (con `TargetTradeValue_k = |FifoInputTransaction.target_amount_k|`, §3.5); `TargetFee_k = TargetFeePool · β_k`.
- **Pool misto BUY/SELL:** `rule = SAME_DAY_MIXED_TRADES`, ripartizione per controvalore target, **senza warning** (policy ufficiale; audit esplicita la regola).
- **Allocazione sui lotti (§13.4 v5):** quota BUY → lotti aperti dall'operazione (`context=OPENING`); quota SELL → lotti ridotti/chiusi, peso `w_i = ClosedQty_i / Σ ClosedQty_j` (`context=CLOSURE`).

#### 4.2 — Pool TAX
- **Target primario same-day:** `DIVIDEND ∪ INTEREST` (asset/broker/giorno/valuta compatibili).
- **Pesi:** `α_k = |TargetIncome_k| / Σ_j |TargetIncome_j|`; con `w_{i,k}` peso del lotto nell'income `k`: `W_i = Σ_k α_k w_{i,k}`; `TargetTax_i = TargetTaxPool · W_i` (`context=INCOME`).
- **Pool income orphan → intero pool TAX orphan** (`asset_orphan_taxes`, `ASSET_COST_NO_ELIGIBLE_LOTS`). Nessuna ripartizione mista allocated/orphan.
- **Trade same-day fallback:** se non esistono income same-day, TAX sul pool BUY/SELL same-day con pesi trade.

#### 4.3 — Ordine di matching
```
FEE : same-day trades → previous-day trades → open-lots fallback → orphan
TAX : same-day income → same-day trades → previous-day income → previous-day trades → open-lots fallback → orphan
```
Nessun candidato in `D+1`. Previous-day: `rule=PREVIOUS_DAY_TRADES`/`PREVIOUS_DAY_INCOME`.

#### 4.4 — Fallback e orphan
- **Fallback (§15 v5):** lotti LONG dello stesso asset/broker aperti a D−1, `w_i = OpenQty_i(D−1)/Σ OpenQty_j(D−1)`; `rule=OPEN_LOTS_FALLBACK` (`context=HOLDING`).
- **Orphan:** nessun lotto eleggibile → `asset_orphan_fees`/`asset_orphan_taxes` + `ASSET_COST_NO_ELIGIBLE_LOTS` (WARNING) + `analysis_status=DEGRADED`.
- **Somma pool multi-evento:** più FEE/più TAX della stessa chiave si sommano prima dell'allocazione; `source_transaction_ids[]` conserva le origini.
- **Test:** più FEE; solo BUY; solo SELL; BUY+SELL; previous-day; fallback; orphan; trade multivaluta; FEE in valuta diversa dai trade; bond qbq=100; più TAX; DIVIDEND+INTEREST; pool income orphan.
- **Gate:** conservazione per ogni pool (nativa+target); nessun importo perso; regola registrata nell'audit.

---

### Fase 5 — Crossing LONG/SHORT

- **Obiettivo:** un trade che chiude una direzione e ne apre l'opposta ripartisce il costo del pool senza perdite.
- **Formule (§16 v5):** `q=q_close+q_open`; `Cost_close = CostTrade·q_close/q`; `Cost_open = CostTrade·q_open/q`; `Cost_close+Cost_open=CostTrade`.
- **Allocazione:** `Cost_close` distribuito sui lotti chiusi (per quantità chiusa, `context=CLOSURE`); `Cost_open` al nuovo lotto nella direzione opposta (`context=OPENING`).
- **Vincolo:** `LotClosure` **immutabile** (`fifo_lot_engine.py:137-149`); i costi vivono solo negli accumulatori economici.
- **Dipendenze:** dopo Fase 4 (pesi trade).
- **Test:** SHORT→LONG; LONG→SHORT; più closure; quantità frazionarie; residui; pool misto.
- **Gate:** `Σ` costi close+open = costo trade (conservazione).

> **✅ FATTO (Fase 3+4+5 — FEE/TAX nel motore)** — 2025
> Allocazione FEE/TAX asset-linked integrata nel motore, con crossing unificato.
> - **Fase 3 (FX/target)** — `lots_analysis_service.py`: `_build_engine_transactions()` risolve il controvalore **target** dei trade (BUY/SELL) via `_FxRateResolver` **prima** del run e lo mette in `FifoInputTransaction.target_amount` (correzione reviewer #1); `_build_cost_economic_events()` costruisce gli `EconomicEvent` FEE/TAX (native+target). FX bulk unico (income+cost+trade) prima del run. Nessuna FX I/O nel motore. FX-missing → silent fallback (raw) come income; `FX_RATE_MISSING_FOR_ALLOCATION` non ancora emesso (rinviato).
> - **Fase 4 (pooling+matching)** — `fifo_lot_engine.py`: `_allocate_cost_pools()` + `_match_cost_operations()`. Pool key `(broker,date,native_ccy,target_ccy)`. Ordine: **FEE** = same-day trades → prev-day trades → holdings fallback → orphan; **TAX** = same-day income → same-day trades → prev-day income → prev-day trades → holdings fallback → orphan. Pesi trade `β_k=|target_amount_k|/Σ`; fallback/income per D-1 holdings (riuso `_eligible_income_quantity`). TAX su income orphan → **intero pool TAX orphan** (no mix, §4.2). `ASSET_COST_NO_ELIGIBLE_LOTS` (WARNING → DEGRADED) esteso a engine Literal + DTO enum + `_WARNING_ISSUE_CODES` + `_message_key_for_issue`→`dataQuality.assetCostNoEligibleLots`.
> - **Fase 5 (crossing)** — `_split_trade_cost()` **unifica Fase 4 e 5**: per ogni trade `q=q_close+q_open`; `Cost_close→CLOSURE` (lotti chiusi per `ClosedQty`), `Cost_open→OPENING` (lotti aperti per `original_quantity`). BUY puro→solo OPENING; SELL puro→solo CLOSURE; crossing SHORT→LONG / LONG→SHORT → split automatico. Conservazione native+target via running-remainder a ogni livello (pool→trade→open/close→lotti).
> - **Audit (Fase 6, prodotto qui)** — ogni pool → `EconomicAllocationGroup(rule, source_transaction_ids, native/target_pool_total, operation_allocations)`; il `context` (OPENING/CLOSURE/INCOME/HOLDING) vive sul `TargetOperationAllocation` → **stesso lotto in OPENING+CLOSURE** stesso giorno preservato.
> - **Test**: +19 test motore (`TestFeeTaxAllocation`): FEE only-BUY/only-SELL/mixed/multi-valuta(target weight)/multi-FEE/prev-day/fallback/orphan/crossing×2/same-lot-OPENING+CLOSURE/FX-conservation; TAX su income/DIV+INT/prev-day-income/orphan-da-income-orphan/same-day-trade/prev-day-trade/fallback+orphan. **266 finanziari verdi**, 22 API portfolio verdi, ruff+black clean.
> - **⚠️ Fuori pista**: FEE/TAX **asset-linked** ora entrano nell'analisi lotti; FEE/TAX **broker-level** (`asset_id=None`) restano esclusi (Portfolio Engine). Accumulatori `allocated_fees/allocated_taxes` prodotti ma **non ancora esposti nel DTO** (Fase 7). `_build_engine_transactions` invocato solo se esistono cost tx → zero overhead sugli asset senza FEE/TAX.

---

### Fase 6 — Audit a tre livelli

- **Obiettivo:** audit gerarchico sempre inline nel risultato.
- **Tipi (dettaglio campi in §7.3):** `EconomicAllocationGroup` (gruppo/pool) → `TargetOperationAllocation[]` (operazione target: opening/closure/income/holding, con `context`) → `EconomicLotAllocation[]` (lotto).
- **Punto chiave:** il **context appartiene al target operativo**, non al gruppo → lo stesso lotto può comparire in più target/context (es. OPENING e CLOSURE) senza perdere il breakdown.
- **Copertura richiesta (§7 task):** pool FEE solo BUY; solo SELL; misto; crossing; pool TAX su più income; fallback HOLDING; orphan; costo previous-day; stesso lotto in OPENING+CLOSURE.
- **Dipendenze:** dopo Fase 4/5 (produce le allocazioni).
- **Test:** un caso per contesto + conservazione `native_orphan`/`target_orphan`.
- **Gate:** audit presente per ogni pool; ricostruibile senza leggere il codice; nessuna paginazione/troncamento (solo **benchmark** dimensione payload).

---

### Fase 7 — Metriche nette e history

- **Obiettivo:** accumulatori e history nette per lotto.
- **Accumulatori (§17 v5):** `original_cost, sale_proceeds, gross_income, allocated_fees, allocated_taxes, open_value` (gli economici non modificano le strutture quantitative).
- **Formule (§3.3 di questo piano):** GrossPnL/NetPnL/GrossReturn/NetReturn; rendimento non disponibile se `OriginalCost ≤ 0` (per SHORT il denominatore resta il nozionale di apertura del modello lordo).
- **History:** aggiungere i prefissi temporali `allocated_fees, allocated_taxes, net_pnl, net_total_return, net_metrics_status` (stesso pattern di `income_prefix_by_lot`, `lots_analysis_service.py:974-981`).
- **Persistenza post-chiusura (§19 v5):** dopo chiusura completa `OpenValue=0`; restano cristallizzati proceeds/income/fee/tax/gross/net; una **FEE/TAX in D attribuita a un trade in D−1** (PREVIOUS_DAY_TRADES) modifica il **netto dalla data D** (gradino solo netto), lordo invariato; history estesa fino a `date_to`.
- **Dipendenze:** dopo Fase 4/5/6.
- **Test:** gross P&L; net P&L; gross return; net return; estimated-at-cost; chiusura completa; costo post-chiusura (gradino netto in D); SHORT; `OriginalCost ≤ 0`.
- **Gate:** `NetPnL = GrossPnL − Fee − Tax` (sottrazione unica); lordo invariato bit-per-bit rispetto a oggi.

> **✅ FATTO (Fase 7 — metriche nette, history, audit DTO + split enum status) — 2025**
> **DTO (`schemas/portfolio.py`):** split `LotCalculationStatus` → `LotAnalysisStatus = COMPLETE|DEGRADED|FAILED` (globale, campo `calculation_status` invariato, 1:1 con `FifoEngineResult.analysis_status`) + nuovo `LotNetMetricsStatus = AVAILABLE|UNAVAILABLE` (per-lotto). `LotSummarySchema` +`allocated_fees/allocated_taxes/net_total_pnl/net_total_return/net_metrics_status`. `LotValueHistoryPoint` +`allocated_fees/allocated_taxes/net_pnl`. `LotReturnHistoryPoint` +`net_total_return`. Nuovi modelli audit Pydantic `EconomicLotAllocationSchema`/`TargetOperationAllocationSchema`/`EconomicAllocationGroupSchema` (mirror 1:1 delle dataclass motore, `extra="forbid"`). `LotsAnalysisResponse` +`economic_allocation_groups` (inline, con LOT_SUMMARY) +`asset_orphan_income/fees/taxes`.
> **Service (`lots_analysis_service.py`):** nuovo `_extract_cost_outputs()` (fees/taxes per lotto + prefissi cumulativi per la history, stesso pattern di `_extract_income_outputs`); `_map_economic_groups()` mappa audit motore→Pydantic. `_build_lot_summaries` calcola `net_total_pnl = total_pnl − fees − taxes` e `net_total_return = net_total_pnl / opening_value` (quando `opening_value > 0`), `net_metrics_status="AVAILABLE"` (il trigger UNAVAILABLE arriva con la DQ FX-missing, Fase 8 — oggi nessun pool degrada un singolo lotto: gli orphan non toccano lotti eleggibili, la conservazione è garantita dal running-remainder). Le due history feed-forward `net_pnl`/`net_total_return`. Migrato l'`_empty_response` `UNAVAILABLE`→`COMPLETE` (reviewer #3, pre-api-sync). Response espone audit groups + orphan aggregati.
> **Client:** `./dev.py api sync` → `generated.ts` con enum status a 3 valori + tutti i nuovi campi/tipi; nessun consumer FE referenzia `calculation_status`/`UNAVAILABLE` (grep=0), migrazione safe.
> **Verifica:** `test_financial/` **267 passed** (nuovo `test_fee_and_tax_allocated_to_lot_and_net_metrics`: FEE same-day BUY + TAX same-day DIVIDEND → allocated_fees=30, allocated_taxes=10, total_pnl=50, net_total_pnl=10, net_total_return=0.01, conservazione per-pool, audit 3 gruppi, 0 orphan, net history); `test_schemas/` **274 passed**; `TestLotsAnalysisEndpoint` **7 passed**; ruff+black clean.

---

### Fase 8 — Status e Data Quality

- **Obiettivo:** separare stato globale analisi da stato locale lotto.
- **`analysis_status`** (globale): `COMPLETE` (nessuna issue che riduca affidabilità) · `DEGRADED` (errore economico isolabile: orphan, FX mancante, conservazione fallita in un pool, metrica netta localmente indisponibile) · `FAILED` (errore quantitativo non isolabile: quantità incoerente, topologia frammenti invalida, transfer non ricostruibile, replay non affidabile).
- **`net_metrics_status`** (per lotto): `AVAILABLE` / `UNAVAILABLE`.
- **`ALLOCATION_CONSERVATION_FAILED`** (ERROR) → **sempre** localizzata al pool → `analysis_status=DEGRADED` + `net_metrics_status=UNAVAILABLE` **solo** sui lotti del pool (mai FAILED).
- **Data Quality minima:** `ASSET_INCOME_NO_ELIGIBLE_LOTS` (W), `ASSET_COST_NO_ELIGIBLE_LOTS` (W), `FX_RATE_MISSING_FOR_ALLOCATION` (W), `ALLOCATION_CONSERVATION_FAILED` (E). `ECONOMIC_EVENT_UNEXPECTED_SIGN` resta **diagnostico interno** (Fase 0.3), non codice pubblico.
- **Modifiche codice:** `FifoEngineResult.calculation_status` (`fifo_lot_engine.py:198-200`) → `analysis_status` a 3 stati derivato dalla natura delle issue (quantitative vs economiche); **sostituire** `LotCalculationStatus` con `LotAnalysisStatus = COMPLETE|DEGRADED|FAILED` (`schemas/portfolio.py:455`) e introdurre l'enum separato `LotNetMetricsStatus` per il campo `net_metrics_status` per lotto (§7.2).
- **Naming e migrazione (reconciliazione con §7.2):** `analysis_status` è la **property interna del motore** (3 stati). Il **campo DTO pubblico resta `LotsAnalysisResponse.calculation_status`** (`:742`) — non rinominato, per non rompere API/frontend — ma tipizzato `LotAnalysisStatus` a **3 valori** (senza `UNAVAILABLE`), mappato **1:1** da `analysis_status`. L'attuale `UNAVAILABLE` globale (caso "nessun dato") ha significato diverso dal per-lotto e va **migrato esplicitamente** (→ `COMPLETE` su risultato vuoto) come da §7.2, **prima** dell'`api sync`.
- **Dipendenze:** dopo Fase 7.
- **Test:** COMPLETE; DEGRADED orphan; DEGRADED FX; DEGRADED conservazione locale (net unavailable per lotto); FAILED quantitativo.
- **Gate:** errori economici isolabili non invalidano quantità/lordo/altri lotti; FAILED riservato al quantitativo non isolabile.

> **✅ FATTO (Fase 8 — status a 3 stati + frontend netto/DQ) — 2025**
> **Backend status (`fifo_lot_engine.py`):** `analysis_status` ora deriva 3 stati dalla **natura** delle issue: `COMPLETE` (nessuna issue) · `DEGRADED` (solo issue economiche/reference isolabili: `ASSET_INCOME/COST_NO_ELIGIBLE_LOTS`, reference-price) · `FAILED` (almeno una issue **quantitativa non isolabile**). Introdotto il frozenset modulo `_QUANTITATIVE_FAILURE_CODES = {SHORT_TRANSFER_NOT_SUPPORTED, SHORT_ADJUSTMENT_NOT_SUPPORTED, FIFO_SOURCE_QUANTITY_MISSING, TRANSFER_PAIR_MISSING}`. Il campo DTO pubblico resta `calculation_status` (mappato 1:1). Aggiunta `TestAnalysisStatus` (COMPLETE / DEGRADED economico / FAILED quantitativo / FAILED domina economico) — 4 test; le 2 asserzioni DEGRADED preesistenti (orphan income/cost) restano verdi perché economiche. **Verifica:** 83 fifo+service, 545 financial+schemas, 7 API lots verdi; ruff+black clean.
> **Frontend (§8.1–8.5):** `UnifiedLotsTable` 4 colonne nette (fees/taxes/net P&L/net return) + footer (Fase 7). `LotCustodyModal` **breakdown netto** (gross → −fees → −taxes → net + net return; placeholder "—" su `net_metrics_status=UNAVAILABLE`). `LotsAnalysisPanel` banner **FAILED** (`calculation_status==='FAILED'` → alert rosso, `data-testid=lots-analysis-panel-failed`). `LotGanttChart` tooltip: righe fee/tax (rosse) + net P&L quando presenti. `DataQualityBanner` mostra automaticamente i nuovi codici (i18n aggiunte). i18n `{en,it,fr,es}` parità 0 mancanti (`brokers.lots.{allocatedFees,allocatedTaxes,netTotalPnl,netTotalReturn,netMetricsUnavailable,analysisFailed}`, `brokers.lots.modal.{netBreakdown,grossTotalPnl,fees,taxes,netTotalPnl,netTotalReturn}`, `dataQuality.{assetIncomeNoEligibleLots,assetCostNoEligibleLots}`). **Gate:** `front check` 0/0, `i18n audit` parità, `front format` pulito, `front build` OK.
>
> **⚠️ Fuori pista / decisioni da rivedere insieme:**
> - **`UnifiedLotsTable` colonne nette `hiddenByDefault: !hasNetCosts`** (visibili di default **solo** se l'asset ha FEE/TAX), coerente con la colonna `asset-income` esistente (`!hasPositiveAssetIncome`). §8.1 dice "visibili di default" in assoluto → scelta la variante meno affollata e coerente con la convenzione. **Da confermare.**
> - **`LotComparisonChart` serie nette parallele — RINVIATO (non implementato).** §8.3 lo marca esplicitamente come rifinitura da **verificare manualmente** e semplificare **dopo** aver visto il risultato reale; il chart è molto intricato (mode × unit × aggregate/per-lot × bucket × resolution × tooltip override) → alto rischio di regressione senza verifica visiva. Il netto è già esposto in 3 superfici (tabella, modal, tooltip Gantt). **Da implementare in modo iterativo dopo review visiva**, coerente con la preferenza utente (verifica manuale guidata) e con la cautela del piano.
> - **Provenienza pool nel modal (§8.2, opzionale "se presente")** non aggiunta: il breakdown mostra gli importi ma non il mapping `economic_allocation_groups`→lotto (regola + `source_transaction_ids`). Deferibile; da valutare in review.
> - **`net_metrics_status` resta sempre `AVAILABLE`** (trigger `UNAVAILABLE` + `FX_RATE_MISSING_FOR_ALLOCATION` + `ALLOCATION_CONSERVATION_FAILED` rinviati come da nota Fase 7): la machinery FE per "—" è pronta ma latente finché il backend non emette il trigger FX-missing.

### Fase 9 — Portfolio Engine e riconciliazione

- **Obiettivo:** accumulatori assoluti pre-share + riconciliazione con il FIFO assoluto.
- **Stato attuale:** `per_income`/`per_fees_taxes` per `(asset_id,broker_id)` (`portfolio_engine.py:834-851`); `share_percentage` applicata **inline e sparsa** (`:224-247,499-505,560-563,741-749,1165-1191`) → nessun choke point unico; Portfolio Engine indipendente dal FIFO.
- **Modifiche:**
  1. Introdurre accumulatori **assoluti pre-share** `per_income_absolute`, `per_fees_absolute`, `per_taxes_absolute` (chiave `(asset_id, event_broker_id)`), popolati **prima** dell'applicazione di `Share_{user,broker}`.
  2. Separare `per_fees_taxes` in `per_fees` e `per_taxes` se necessario alla riconciliazione (TAX e FEE distinte lato FIFO).
  3. Proiezione utente invariata a valle: `Amount^{user} = Amount^{absolute} · Share_{user,broker}`.
  4. Il FIFO **non** riceve `share_percentage` (resta assoluto).
- **Invarianti riconciliazione (§26 v5):** `AllocatedIncome + AssetOrphanIncome = AbsoluteAssetIncome`; idem Fees e Taxes; chiave `(asset_id, event_broker_id, periodo, native_currency, target_currency)`.
- **Dipendenze:** logicamente scorporabile (§11), ma la verifica di riconciliazione richiede il FIFO economico (Fase 4/7).
- **Test:** FIFO assoluto; Portfolio pre-share; Portfolio share-weighted; broker multipli; asset orphan.
- **Gate:** le tre uguaglianze di conservazione valgono su scenari multi-broker.
- **Rischi:** share sparsa → refactor esteso; mitigazione: introdurre gli accumulatori assoluti **accanto** a quelli esistenti (additivi) e verificare l'uguaglianza `absolute·share == user` sui test prima di rimuovere percorsi.

> **🟡 PARZIALE (Fase 9) — lato FIFO fatto, lato Portfolio RINVIATO alla review — 2025**
> **✅ Fatto (lato FIFO, zero rischio produzione):** aggiunta `TestEconomicConservation` (`test_fifo_lot_engine.py`) che blocca la **metà FIFO** dell'invariante di riconciliazione: per ogni tipo economico `Σ(allocato ai lotti) + asset_orphan == pool target assoluto (pre-share)`, su scenario **multi-broker** (Directa 30 / IBKR 70, income+fee su b1, income+tax su b2 → tutto allocato, orphan=0) e su scenario **con orphan** (posizione b1 chiusa → dividend+fee b1 orphan, b2 aperto). Verificato anche lo scope broker (nessun bleed cross-broker). Il motore è già assoluto e broker-scoped → questi totali sono la ground-truth verso cui il Portfolio Engine (share-weighted) dovrà riconciliare.
> **⏸️ Rinviato alla review congiunta (lato Portfolio Engine):** l'introduzione degli accumulatori **assoluti pre-share** (`per_income_absolute`/`per_fees_absolute`/`per_taxes_absolute`) + split `per_fees_taxes`→`per_fees`/`per_taxes` + riconciliazione runtime **NON** è stata implementata. Motivi (da decidere insieme):
> - **Doppio path accumulatori**: gli accumulatori esistono in **due** implementazioni parallele — `portfolio_engine.py:537-539,834-851` (3-pool, share applicata a `:748`) **e** `portfolio_service.py:1715-1762` (path separato, share a `:1756-1762`). Va deciso **quale** è il target canonico degli accumulatori assoluti (o entrambi) prima di scrivere codice.
> - **Nessun consumer attuale** dei valori assoluti: senza una sede definita per la riconciliazione (test-only vs asserzione runtime vs campo esposto), gli accumulatori assoluti sarebbero dead-code. Serve decisione di design.
> - **File caldo, refactor esteso** (share sparsa in 5+ punti, `portfolio_engine.py` ~1800 righe): alto rischio di regressione senza verifica funzionale → coerente con la preferenza utente (flag di modifiche estese/incerte invece di implementarle silenziosamente) e con la cautela additiva del piano stesso.
> **Proposta per il run dedicato:** (1) scegliere il path canonico; (2) aggiungere gli accumulatori assoluti **accanto** a quelli esistenti (additivi, zero rimozioni); (3) test `absolute·share == user` per chiave; (4) test di riconciliazione che confronta Portfolio-assoluto vs FIFO `allocated+orphan` (la metà FIFO è già bloccata sopra); (5) solo dopo, valutare un choke-point unico per la share.

---

## 6. Test backend obbligatori

**Package e comandi reali:**
- Motore + service: `backend/test_scripts/test_services/test_financial/` → `./dev.py test services roi-fifo-utils`.
- Portfolio Engine: `backend/test_scripts/test_services/test_portfolio_engine/` → `./dev.py test services portfolio-engine`.
- Schemi Pydantic: `backend/test_scripts/test_schemas/` → `./dev.py test schemas all`.
- API: `backend/test_scripts/test_api/` → `./dev.py test api all`.
- Singolo: `pipenv run pytest backend/test_scripts/.../file.py::Test::test_x -v`.

### 6.1 Scenario canonico end-to-end (riconciliazione lordo/netto)
Input (un lotto LONG, un broker, target=native):
```
BUY   10 × 100 = 1.000        (original_cost = 1.000)
SELL   4 × 120 =   480        (sale_proceeds = 480)
Prezzo corrente = 110         (open_value = 6 × 110 = 660)
DIVIDEND        =    50        (gross_income = 50)   [D-1 rispetto al mark, lotto eleggibile]
FEE             =   -8         (allocated_fees = 8)  [same-day trade pool]
TAX             =   -5         (allocated_taxes = 5) [su income]
```
Output atteso:
```
GrossEconomicValue = 660 + 480 + 50            = 1.190
GrossPnL           = 1.190 − 1.000             =   190
NetPnL             = 190 − 8 − 5               =   177
GrossReturn        = 190 / 1.000               = 19,0%
NetReturn          = 177 / 1.000               = 17,7%
```
Invarianti verificati: `GrossPnL` invariato dall'introduzione di FEE/TAX; `NetPnL = GrossPnL − Fee − Tax` (sottrazione unica); `income` non entra due volte (è in GrossEconomicValue, non ri-sommato nel return). File: `test_financial/test_lots_analysis_service.py` (+ unit motore in `test_fifo_lot_engine.py`).

### 6.2 Matrice per area
| # | Area | Scenario | Input → Output atteso | Invariante | File |
|---|------|----------|-----------------------|-----------|------|
| I1 | Integrità | CREATE FEE positiva | `cash.amount=+50` → ValidationError `cashSignNegative` | Regola 11 | `test_schemas/…transactions` |
| I2 | Integrità | IMPORT FEE positiva | provider emette FEE `+` → issue (via `TXCreateItem`) | Regola 11 in import | `test_external`/`test_schemas` |
| I3 | Integrità | UPDATE FEE→positiva | PATCH `cash.amount=+50` → **rifiutata** | validator condiviso su merge | `test_api/test_transactions_api.py` |
| I4 | Integrità | UPDATE type+cash | BUY→FEE con `amount>0` → rifiutata; BUY→SELL coerente → ok | stato finale | `test_api/test_transactions_api.py` |
| I5 | Integrità | UPDATE negativo valido | FEE resta `-` → accettata | non regressione | `test_api/test_transactions_api.py` |
| I6 | Integrità | Audit legacy | DB popolato → 0 anomalie | segno coerente | script `audit_transaction_signs.py` |
| Q1 | FIFO quant. | Regressione | suite esistente invariata (economic_events=[]) | replay stabile | `test_fifo_lot_engine.py` |
| Q2 | qbq | qbq=1 e qbq=100 | `1000/100·98,50 = 985` | no scaling cash | `test_fifo_lot_engine.py`/service |
| Q3 | qbq | metodi rimossi | `value_for_lot`/`aggregate_value`/`relative_return_for_lot` assenti | hardening | `test_fifo_lot_engine.py` |
| N1 | Income | BUY same-day | DIV in D, BUY in D → BUY escluso | D-1 | `test_lots_analysis_service.py` |
| N2 | Income | SELL same-day | SELL in D → incluso (aperto a D-1) | D-1 | idem |
| N3 | Income | open+close same-day | lotto nato e chiuso in D → escluso | D-1 | idem |
| N4 | Income | split same-day | pesi pre/post identici | `rq/Σrq=q/Σq` | idem |
| N5 | Income | scope broker | Directa 30 / IBKR 70, DIV +100 Directa → 100 Directa, 0 IBKR | broker-aware | idem |
| N6 | Income | From in transito | income su From → BROKER From + IN_TRANSIT(source=From) | scope transito | idem |
| N7 | Income | To in transito | income su To → solo pre-esistenti a D-1 | scope transito | idem |
| N8 | Income | To giorno arrivo | a D-1 in transito → orphan + `ASSET_INCOME_NO_ELIGIBLE_LOTS` | no eccezione EOD | idem |
| N9 | Income | pool allocabile/orphan | pool interamente allocabile / interamente orphan; mix impossibile | pool omogeneo | idem |
| F1 | Pool FEE | più FEE | `-2` + `-3` → pool `5` | somma pool | `test_financial/` motore |
| F2 | Pool FEE | solo BUY | quota su lotti aperti (OPENING) | `β_k` | idem |
| F3 | Pool FEE | solo SELL | quota su lotti chiusi `w=ClosedQty/ΣClosed` (CLOSURE) | pesi chiusura | idem |
| F4 | Pool FEE | BUY+SELL | `rule=SAME_DAY_MIXED_TRADES`, per controvalore target, no warning | policy ufficiale | idem |
| F5 | Pool FEE | previous-day | nessun same-day → `PREVIOUS_DAY_TRADES` | no D+1 | idem |
| F6 | Pool FEE | fallback | nessun trade → open-lots(D-1) `OPEN_LOTS_FALLBACK` (HOLDING) | fallback | idem |
| F7 | Pool FEE | orphan | nessun lotto → `asset_orphan_fees` + `ASSET_COST_NO_ELIGIBLE_LOTS` | orphan | idem |
| F8 | Pool FEE | bond qbq=100 | `TradeValue=|amount|` senza qbq | no scaling | idem |
| F9 | Pool FEE | multivaluta | 2 trade valute diverse → pesi in target | FX-invarianza | idem |
| T1 | Pool TAX | più TAX | somma pool prima dell'alloc | somma pool | idem |
| T2 | Pool TAX | DIVIDEND+INTEREST | target congiunto, `α_k`, `W_i=Σα_k w_{i,k}` | unione income | idem |
| T3 | Pool TAX | same-day trade fallback | no income → pesi trade | ordine matching | idem |
| T4 | Pool TAX | previous-day income | `PREVIOUS_DAY_INCOME` | no D+1 | idem |
| T5 | Pool TAX | pool income orphan | intero pool TAX orphan | no mix | idem |
| C1 | Crossing | SHORT→LONG / LONG→SHORT | `Cost_close+Cost_open=CostTrade` | conservazione | `test_fifo_lot_engine.py` |
| C2 | Crossing | più closure / frazionari / residui | distribuzione per quantità, residuo all'ultimo | stabile | idem |
| X1 | FX | target EUR / USD | metriche nella target | target-currency | `test_lots_analysis_service.py` |
| X2 | FX | conservazione nativa | `Σ NativeAlloc + NativeOrphan = NativePool` | conservazione | motore |
| X3 | FX | conservazione target | `Σ TargetAlloc + TargetOrphan = TargetPool` | conservazione | motore |
| X4 | FX | FX mancante | `FX_RATE_MISSING_FOR_ALLOCATION`, DEGRADED, net UNAVAILABLE, gross preservato | isolabilità | motore/service |
| M1 | Metriche | scenario 6.1 | Gross 190 / Net 177 / 19% / 17,7% | sottrazione unica | `test_lots_analysis_service.py` |
| M2 | Metriche | costo post-chiusura | SELL completa in D-1, FEE in D → gradino solo netto in D | lordo invariato | idem |
| M3 | Metriche | SHORT / OriginalCost≤0 | return None quando `OriginalCost≤0` | denominatore | idem |
| S1 | Status | COMPLETE / DEGRADED(orphan) / DEGRADED(FX) / DEGRADED(conservazione locale) / FAILED(quant.) | mappatura corretta | isolabilità | motore/service |
| R1 | Riconcil. | FIFO assoluto vs Portfolio pre-share vs share-weighted | `absolute·share=user`; 3 uguaglianze conservazione | riconciliazione | `test_portfolio_engine/` |

### 6.3 Nota su determinismo
Ogni test finanziario critico usa importi interi/decimali esatti e verifica sia il **valore** sia
l'**invariante** (conservazione o uguaglianza gross/net), non solo il valore puntuale, per intercettare
doppi conteggi o drift di arrotondamento.

---

## 7. DTO, API e client generato

Home canonica delle definizioni DTO. Il motore produce **dataclass** interne; il service le mappa nei
**modelli Pydantic** di `schemas/portfolio.py`; `./dev.py api sync` rigenera il client TS.

### 7.1 Estensioni ai modelli esistenti
**`LotSummarySchema`** (`schemas/portfolio.py:513-545`) — aggiungere dopo i campi gross (mantenendo
`extra="forbid"`):
```python
allocated_fees: SafeDecimal = Field(default=0, description="Cumulative FEE allocated to this lot, target_currency (positive magnitude).")
allocated_taxes: SafeDecimal = Field(default=0, description="Cumulative TAX allocated to this lot, target_currency (positive magnitude).")
net_total_pnl: Optional[SafeDecimal] = Field(None, description="total_pnl - allocated_fees - allocated_taxes.")
net_total_return: Optional[SafeDecimal] = Field(None, description="net_total_pnl / original_cost, when original_cost > 0.")
net_metrics_status: LotNetMetricsStatus = Field("AVAILABLE", description="AVAILABLE when net metrics are reliable; UNAVAILABLE when the lot belongs to a degraded economic pool.")
```
**`LotValueHistoryPoint`** (`:610-622`) e **`LotReturnHistoryPoint`** (`:625-638`) — aggiungere le
serie nette cumulative (feed-forward, gradino dalla data del costo):
```python
# value point
allocated_fees: SafeDecimal = Field(default=0, ...)
allocated_taxes: SafeDecimal = Field(default=0, ...)
net_pnl: SafeDecimal = Field(default=0, ...)
# return point
net_total_return: Optional[SafeDecimal] = Field(None, ...)
```

### 7.2 Stato globale e stato per-lotto — due enum distinti (review pre-run)
**Decisione:** separare nettamente lo stato *globale* dell'analisi dallo stato *per-lotto* delle metriche
nette, con **due enum diversi**. Il campo top-level mantiene il nome `calculation_status` (no churn) ma ne
cambia la semantica.
```python
LotAnalysisStatus   = Literal["COMPLETE", "DEGRADED", "FAILED"]     # globale (rimpiazza LotCalculationStatus)
LotNetMetricsStatus = Literal["AVAILABLE", "UNAVAILABLE"]           # per-lotto (net_metrics_status)
```
- `LotsAnalysisResponse.calculation_status` (`schemas/portfolio.py:742`) resta **con questo nome** ma tipizzato `LotAnalysisStatus` (3 valori). Mapping **1:1** con `FifoEngineResult.analysis_status` — ora davvero 1:1 (nessun quarto valore).
- `LotSummarySchema.net_metrics_status` (§7.1) usa `LotNetMetricsStatus`.

**Migrazione obbligatoria di `UNAVAILABLE` globale (breaking, esplicita).** Oggi
`LotCalculationStatus = ["COMPLETE","DEGRADED","UNAVAILABLE"]` (`:455`) e `UNAVAILABLE` è **emesso a livello
globale** dal percorso "nessun dato" (`_empty_response(status="UNAVAILABLE")`, `lots_analysis_service.py:190,205`;
assegnato a `calculation_status` come le altre uscite `:468,561`): significato = *analisi vuota / non
calcolabile*, **diverso** dal nuovo `net_metrics_status=UNAVAILABLE` per-lotto. Non riusare la stringa nel
nuovo enum globale solo per compatibilità. Passi:
1. **Ricerca consumatori completa** (già svolta in fase di piano): backend `:190,205,468,561`, DTO `:455,742`, `generated.ts:4310,8392`; **nessun** consumer `.svelte`/`.ts` ramifica su `calculation_status`/`UNAVAILABLE` (grep = 0) → migrazione a basso rischio FE.
2. Migrare il caso "nessun dato" di `_empty_response` a **`COMPLETE`** (analisi completata con `lots=[]`): il frontend deriva lo stato vuoto dal payload (lista lotti vuota), non dallo status. *(Micro-decisione prodotto: vedi §"Decisioni aperte".)*
3. Rimuovere `UNAVAILABLE` dall'enum globale; introdurre `FAILED`.
4. Aggiornare i test backend che asseriscono `calculation_status=="UNAVAILABLE"` sul caso vuoto → `"COMPLETE"`.
5. `./dev.py api sync` rigenera l'enum a 3 valori; verificare `generated.ts:4310,8392`.

**Gate pre-`api sync`:** questa scelta va fissata *prima* dell'`api sync` (l'enum del client ne dipende).

`FAILED` = solo errori quantitativi non isolabili (replay compromesso). `DEGRADED` = errori economici
isolabili (orphan, FX mancante, conservazione locale di un pool) → gross intatto, `net_metrics_status=UNAVAILABLE`
solo sui lotti del pool colpito.

### 7.3 DTO audit a 3 livelli (nuovi modelli)
Rispecchiano le dataclass del motore (Fase 6). Livello alto→basso:
```python
class EconomicLotAllocation(BaseModel):        # foglia
    model_config = ConfigDict(extra="forbid")
    lot_id: int
    weight: SafeDecimal                        # peso del lotto nell'operazione target
    native_amount: SafeDecimal                 # quota in valuta nativa del pool
    target_amount: SafeDecimal                 # quota in target_currency

class TargetOperationAllocation(BaseModel):    # operazione target (opening/closure/income/holding)
    model_config = ConfigDict(extra="forbid")
    context: Literal["OPENING", "CLOSURE", "INCOME", "HOLDING"]
    operation_transaction_id: Optional[int]    # trade o income target (None per HOLDING/fallback)
    weight: SafeDecimal                        # α_k (income) o β_k (trade)
    lot_allocations: List[EconomicLotAllocation]

class EconomicAllocationGroup(BaseModel):      # pool
    model_config = ConfigDict(extra="forbid")
    economic_type: Literal["FEE", "TAX", "DIVIDEND", "INTEREST"]
    asset_id: int
    broker_id: int
    date: date_type
    native_currency: str
    target_currency: str
    rule: str                                  # SAME_DAY_MIXED_TRADES | PREVIOUS_DAY_TRADES | PREVIOUS_DAY_INCOME | OPEN_LOTS_FALLBACK | ...
    source_transaction_ids: List[int]          # transazioni originali sommate nel pool
    native_pool_total: SafeDecimal
    target_pool_total: SafeDecimal
    native_orphan: SafeDecimal = 0             # residuo non allocato (nativo)
    target_orphan: SafeDecimal = 0             # residuo non allocato (target)
    operation_allocations: List[TargetOperationAllocation]
```
Motivazione livelli: il `context` sta sull'**operazione target**, non sul gruppo, così lo stesso lotto
può ricevere quote con contesti diversi (OPENING + CLOSURE) mantenendole distinte. Ogni livello espone
**campi nativi e target** per la doppia conservazione (§ Fase 3). Rappresenta tutti i casi del task:
pool FEE solo-BUY, solo-SELL, misto (crossing), pool TAX multi-income, HOLDING fallback, orphan,
costo previous-day, lotto in OPENING+CLOSURE.

### 7.4 Aggancio in `LotsAnalysisResponse`
`LotsAnalysisResponse` (`:728-761`) — aggiungere sezione audit + orphan aggregati:
```python
economic_allocation_groups: Optional[List[EconomicAllocationGroup]] = Field(None, description="Inline one-shot economic audit (FEE/TAX/income). Present with LOT_SUMMARY.")
asset_orphan_fees: SafeDecimal = Field(default=0, description="FEE with no eligible lot, target_currency.")
asset_orphan_taxes: SafeDecimal = Field(default=0, description="TAX with no eligible lot, target_currency.")
asset_orphan_income: SafeDecimal = Field(default=0, description="Income with no eligible lot, target_currency.")
```
L'audit resta **inline** nella risposta one-shot; nessun endpoint aggiuntivo. Nuovi codici Data Quality
(`ASSET_INCOME_NO_ELIGIBLE_LOTS`, `ASSET_COST_NO_ELIGIBLE_LOTS`, `FX_RATE_MISSING_FOR_ALLOCATION`)
confluiscono nel `data_quality` esistente (`:744`).

### 7.5 Sync client + gate
1. `./dev.py api sync` → rigenera `frontend/src/lib/api/generated.ts`.
2. Verificare i blocchi generati: `LotSummarySchema` (~3974-4035), `LotValueHistoryPoint` (~4407),
   `LotReturnHistoryPoint` (~4422), `LotsAnalysisResponse` (~4298-4378) contengono i nuovi campi +
   i nuovi tipi `EconomicAllocationGroup`/`TargetOperationAllocation`/`EconomicLotAllocation`.
3. Test schemi: `./dev.py test schemas all` (serializzazione, default, `extra="forbid"`).
4. Gate: nessun campo `Optional` dimenticato che rompa il client; enum status allineato FE/BE.

---

## 8. Aggiornamento frontend

**Decisione prodotto recepita: NESSUN toggle lordo/netto.** Le metriche nette sono **colonne aggiuntive
mostrate di default**, occultabili tramite il column selector già esistente (`ColumnVisibilityToggle`).
Nessuno stato globale gross/net.

### 8.1 `UnifiedLotsTable.svelte`
- **Colonne nuove** (definizione colonne `~:468-620`): `allocated_fees`, `allocated_taxes`,
  `net_total_pnl`, `net_total_return`. Visibili di default; registrate nel `ColumnVisibilityToggle`
  così l'utente può nasconderle.
- **Footer/aggregati** (`~:439-465`): sommare i nuovi campi coerentemente con i gross esistenti.
- **`net_metrics_status=UNAVAILABLE`**: cella con placeholder esplicito (es. "—" + tooltip
  "Metriche nette non disponibili: pool economico degradato"), non `0`, per non confondere con netto reale.
- Selettori sempre via `data-testid` (mai classi/testo).

### 8.2 `LotCustodyModal.svelte`
- Aggiungere **breakdown netto**: righe gross → `− fees` → `− taxes` → **net**, con i valori del lotto.
- Se il lotto ha `economic_allocation_groups` correlati, mostrare la **provenienza** (regola pool +
  `source_transaction_ids`) in forma compatta (audit inline già presente nella response).

### 8.3 Chart (`LotComparisonChart.svelte`, `LotGanttChart.svelte`)
- `LotComparisonChart` (mode valore/rendimento, oggi **nessun** concetto netto): aggiungere **serie nette**
  parallele alle gross (`net_pnl`, `net_total_return`) usando i nuovi campi delle history point.
  Presentazione come serie aggiuntiva/tratteggiata, **senza** toggle globale (rifinitura eventuale come flag locale). ⚠️ La compresenza di serie lorde e nette **aumenta la densità** del grafico → implementare come previsto, verificare manualmente il risultato reale; eventuali semplificazioni grafiche **dopo** aver visto il risultato, non prima.
- `LotGanttChart` tooltip (`~:817-858`): includere fee/tax allocate quando presenti.

### 8.4 Data Quality / status
- `DataQualityBanner.svelte`: già consuma `data_quality`; i nuovi codici (`ASSET_INCOME_NO_ELIGIBLE_LOTS`,
  `ASSET_COST_NO_ELIGIBLE_LOTS`, `FX_RATE_MISSING_FOR_ALLOCATION`) appaiono automaticamente se mappati in i18n.
- Nuovo stato `FAILED` in `calculation_status`: gestire il ramo (banner d'errore / sezioni non renderizzate)
  in `LotsAnalysisPanel.svelte` accanto a `DEGRADED`.

### 8.5 i18n (`frontend/src/lib/i18n/{en,it,fr,es}.json`)
Aggiungere chiavi in **tutte e 4** le lingue (gruppi `brokers.lots.*`, `brokers.lots.modal.*`, `dataQuality.*`):
- etichette colonne: `allocatedFees`, `allocatedTaxes`, `netTotalPnl`, `netTotalReturn`;
- label modal breakdown (gross/fees/taxes/net, provenienza);
- messaggi Data Quality dei 3 nuovi codici;
- tooltip `net_metrics_status=UNAVAILABLE` e stato `FAILED`.
Nessuna chiave orfana; parità EN/IT/FR/ES.

---

## 9. Check, build e i18n frontend

Gate obbligatori (0 errori/0 warning) prima del merge frontend:
1. `./dev.py api sync` già eseguito (§7.5) — il client riflette i nuovi DTO.
2. `./dev.py front check` → svelte-check + type-check contro `generated.ts` aggiornato (i nuovi campi
   devono tipizzare senza `any`).
3. `./dev.py i18n audit` → parità chiavi EN/IT/FR/ES, nessuna chiave mancante/orfana.
4. `./dev.py front build` → build di produzione pulita.
5. `./dev.py front format` → formattazione Prettier.

---

## 10. UI manual test list (verifica manuale)

Percorso: login `e2e_test_user` → asset con storia nota → pannello **Lots Analysis**. Selettori
`data-testid`. Per ogni check: dove andare + valore atteso.

| ID | Scenario | Azione UI | Atteso |
|----|----------|-----------|--------|
| A | Regressione FIFO | Asset solo BUY/SELL, nessun FEE/TAX/income | Colonne gross invariate vs oggi; nette = gross (fees=0, taxes=0) |
| B | Income D-1 | Asset con BUY in D e DIVIDEND in D | Il lotto aperto in D **non** riceve l'income (solo lotti aperti a D-1); income visibile |
| C | Scope broker | Directa 30 / IBKR 70, DIVIDEND +100 su Directa | Somma income lotti Directa = 100; lotti IBKR = 0 |
| D | Transfer From | Income su From durante transito | Allocato a BROKER From + IN_TRANSIT(source=From); nessuna doppia allocazione |
| E | Transfer To arrivo | Income su To nel giorno d'arrivo, a D-1 in transito | Orphan (`asset_orphan_income`) + banner `ASSET_INCOME_NO_ELIGIBLE_LOTS` |
| F | Pool FEE misto | Stesso giorno BUY+SELL con FEE | FEE ripartita per controvalore; regola `SAME_DAY_MIXED_TRADES`; **nessun** warning |
| G | Pool TAX multi-income | DIVIDEND+INTEREST stesso asset/broker/giorno + TAX | TAX su unione income; conservazione (Σalloc+orphan=pool) |
| H | Lordo vs netto (scenario 6.1) | BUY 10×100, SELL 4×120, prezzo 110, DIV 50, FEE 8, TAX 5 | Open 660, Proceeds 480, GrossPnL **190**, NetPnL **177**, GrossRet **19%**, NetRet **17,7%** |
| I | Costo post-chiusura | SELL completa in D-1, FEE in D | Serie **netta** con gradino in D; serie **lorda** invariata |
| J | FX target | Stessa analisi in EUR e in USD | Metriche coerenti nella target scelta; audit mostra nativo+target |
| K | Status / Data Quality | Forzare FX mancante su un pool | `DEGRADED`; gross intatto; celle nette del pool = "—" (UNAVAILABLE); banner FX |
| L | Colonne nette | Column selector | 4 colonne nette visibili di default, occultabili; footer somma corretta |
| M | Modal breakdown | Aprire `LotCustodyModal` su lotto con FEE/TAX | Righe gross → −fees → −taxes → net; provenienza pool |
| N | Responsive/temi | Dark mode + viewport stretto | Nuove colonne/righe leggibili; flag emoji broker corrette |

> Coerente con la preferenza utente: la verifica visiva è **manuale guidata** (dove andare + numero
> atteso), non una batteria di test automatici sull'UI.

---

## 11. Parallelizzazione

**Stream indipendenti** (sviluppabili in parallelo, file disgiunti):
- **S0 — Integrità**: validator condiviso CREATE/UPDATE (`schemas/transactions.py`, `transaction_service.py`) + script audit segni. Nessun overlap col motore.
- **Sqbq — qbq hardening**: rimozione metodi morti + test qbq-aware (`fifo_lot_engine.py` metodi isolati, `test_fifo_lot_engine.py`, mkdocs).
- **SPE — Portfolio Engine pre-share**: accumulatori assoluti (`portfolio_engine.py`), indipendente dal FIFO.

**Catena sequenziale (core, un solo owner per file):**
`EconomicEvent + FifoEngineResult` (contratto) → economic stage (pooling/alloc) → FEE/TAX → metriche/history nette → tipi audit → **DTO** (`schemas/portfolio.py`) → **`api sync`** (`generated.ts`) → **frontend** (`UnifiedLotsTable`, `LotCustodyModal`, chart, i18n).

**File caldi (un solo editor alla volta):** `fifo_lot_engine.py`, `lots_analysis_service.py`,
`schemas/portfolio.py`, `generated.ts`, i JSON i18n, `UnifiedLotsTable.svelte`, `LotComparisonChart.svelte`.

**Punti di integrazione/gate:** (1) contratto motore stabile → sbloccca economic stage; (2) DTO
congelati → `api sync` → sblocca frontend; (3) tutti i test backend verdi → merge FE.

**Cadenza test-gate sul core (un solo owner, sequenziale):** il core `fifo_lot_engine.py` ↔
`lots_analysis_service.py` non è parallelizzabile; suite verde **obbligatoria dopo ciascuna tappa** prima
di procedere: (a) contratto motore, (b) income D-1/scope/transfer, (c) pooling FEE/TAX, (d) metriche nette.

---

## 12. Strategia di integrazione

- Sviluppo **per fasi su branch dedicato**; ammesse fasi intermedie transitorie.
- **Merge finale atomico**: un solo `FifoLotEngine.run(...)`, un solo `FifoEngineResult`, income
  allocato **solo** nel motore, FEE/TAX **solo** nel motore, service/DTO/client/frontend aggiornati
  insieme, **vecchio income allocator rimosso** nello stesso merge. Nessun doppio percorso residuo.
- Ordine di merge interno: integrità → contratto+economic → metriche/DTO → api sync → frontend →
  Portfolio Engine riconciliazione → cleanup.

---

## 13. Cleanup (con verifica preventiva)

Prima di ogni rimozione, `rg` per confermare zero consumer residui:
- `_allocate_asset_income` (`lots_analysis_service.py:914-982`) → **rimuovere** dopo che il motore alloca l'income.
- `value_for_lot` / `aggregate_value` / `relative_return_for_lot` (`fifo_lot_engine.py:244/262/283`) →
  rimuovere; consumer solo test (`test_fifo_lot_engine.py:210,416-418`) da riscrivere qbq-aware; aggiornare `mkdocs_src/.../fifo_lot_engine.md`.
- Helper FX duplicati eventuali dopo unificazione resolver.
- Chiavi i18n orfane (dopo che le nuove sostituiscono eventuali placeholder).
- Test che asseriscono la **vecchia semantica D** dell'income → riscritti su D-1.
- Verificare che `./dev.py db check` (script `verify_db_check_constraints.py` inesistente) resti **fuori scope** (annotato, non introdotto).

---

## 14. Criteri finali di accettazione

Gate verificabili (mappati al task §21):
1. Un solo entrypoint pubblico `FifoLotEngine.run(...)`; nessun income allocator esterno.
2. Income eleggibile per `OpenQuantity(D-1)`, broker-aware, transfer-aware; nessuna eccezione arrival-day.
3. FEE pool su BUY/SELL per `|amount|` in target; misto = `SAME_DAY_MIXED_TRADES` senza warning; ADJUSTMENT esclusi.
4. TAX pool su `DIVIDEND ∪ INTEREST`; `α_k`, `W_i=Σα_k w_{i,k}`.
5. Fallback previous-day (mai D+1) → open-lots(D-1) → orphan con codici dedicati.
6. `original_cost`, `opening_unit_price`, WAC, gross proceeds, gross P&L **invariati**; netto = feed-forward.
7. `GrossPnL=Open+Proceeds+Income−OriginalCost`; `NetPnL=Gross−Fees−Taxes`; return su `OriginalCost`.
8. Calcolo economico in **target_currency**; audit con importi **nativi e target**; doppia conservazione.
9. Conservazione: `Σalloc+orphan=pool` sia nativo sia target, per ogni pool.
10. Audit 3 livelli inline; `context` sull'operazione target.
11. Status: `DEGRADED` per errori economici isolabili (net UNAVAILABLE locale), `FAILED` solo quantitativo non isolabile.
12. Segno FEE/TAX garantito da Pydantic su CREATE **e** UPDATE (buco chiuso); nessun CHECK DB.
13. DTO estesi + `api sync` + `generated.ts` coerente; `front check`/`build`/`i18n audit` a 0.
14. Colonne nette default-on senza toggle globale; modal breakdown; chart net series.
15. Portfolio Engine: accumulatori assoluti pre-share; riconciliazione `(asset_id,broker_id)`; `absolute·share=user`.
16. Test verdi: `test services roi-fifo-utils`, `portfolio-engine`, `schemas all`, `api all`.
17. Vecchio allocator + metodi qbq morti rimossi; mkdocs aggiornato.
18. Nessuna regressione FIFO quantitativa (economic_events vuoto ⇒ output identico).
19. UI manual list A–N superata coi numeri attesi.
20. Nessun doppio conteggio income (in GrossEconomicValue, non ri-sommato nel return).
21. Merge finale atomico, singolo percorso canonico.

---

## 15. Rischi e rollback

| Rischio | Impatto | Mitigazione / Rollback |
|---------|---------|------------------------|
| Refactor share Portfolio Engine (inline/sparso) | Regressione allocazione utente | Introdurre accumulatori assoluti **accanto** ai correnti, confrontare `absolute·share` vs valori attuali in test prima di rimuovere il vecchio path |
| Contratto motore cambia firma | Rottura call-site `:224/:253` | Aggiornare entrambe le chiamate nello stesso commit; economic_events opzionale ⇒ regressione FIFO nulla |
| Doppia conversione FX / drift | Metriche errate | Convertire **il totale del pool una volta** (valuta+data uniche nella chiave); pesi FX-invarianti; test conservazione nativo+target |
| Buco UPDATE non chiuso ovunque | Segni incoerenti a valle | Validator condiviso sullo **stato finale merge**, test API I3–I5 |
| Rimozione metodi qbq usati altrove | Build rotto | `rg` preventivo; consumer solo test noti |
| `FAILED` non gestito nel FE | Pannello rotto | Ramo esplicito in `LotsAnalysisPanel` accanto a `DEGRADED` |
| i18n incompleta | `i18n audit` fallisce | Aggiungere le chiavi in tutte e 4 le lingue insieme al codice |

**Rollback**: essendo tutto su branch dedicato con merge atomico, il rollback è il non-merge del branch;
nessuna migrazione DB introdotta (nessuno schema DB modificato) ⇒ rollback senza downgrade.

---

## Chiusura operativa

### Dependency graph (sintesi)
```
Integrità(S0) ─┐
qbq(Sqbq) ─────┤
               ├─▶ [nessun blocco reciproco]
Contratto motore ─▶ economic stage ─▶ FEE/TAX ─▶ metriche/history nette ─▶ tipi audit
     └────────────────────────────────────────────────────────────────▶ DTO ─▶ api sync ─▶ frontend
PortfolioEngine(SPE) ─▶ riconciliazione (dopo metriche nette)
Cleanup ─▶ (dopo che il motore alloca income/fee/tax)
```

### Ordine di implementazione consigliato
1. **Fase 0** integrità (validator condiviso CREATE/UPDATE) + audit segni + qbq hardening. *(parallelo, sblocca)*
2. **Fase 1–2** contratto `EconomicEvent`/`FifoEngineResult` + income D-1/scope/transfer nel motore.
3. **Fase 3–5** FX target prep + pooling FEE/TAX + crossing.
4. **Fase 6–7** tipi audit 3 livelli + metriche/history nette + DTO.
5. `./dev.py api sync` + test schemi/service/api.
6. **Fase 8** frontend (colonne nette, modal, chart, i18n) + `front check/build` + `i18n audit`.
7. **Fase 9** Portfolio Engine accumulatori pre-share + riconciliazione.
8. **Cleanup** allocator/metodi morti/test D-legacy + merge finale atomico.

### Definition of Done
- Tutti i 21 criteri §14 soddisfatti e verificati.
- Suite backend verdi (§16 dei criteri) + `front check`/`build`/`i18n audit` a 0.
- UI manual list A–N (§10) **e Appendice A** (checklist completa di accettazione frontend) superate coi risultati attesi.
- Un solo percorso canonico; vecchio allocator e metodi qbq morti rimossi; mkdocs aggiornato.
- Nessuno schema DB modificato; nessun toggle gross/net introdotto.

## Appendice A — UI manual checklist completa (accettazione frontend)

Poiché **non** si scrivono test grafici automatici, questa checklist **è** il test di accettazione del
frontend e va eseguita per intero. §10 (A–N) ne è la sintesi; qui la copertura completa di ogni policy che
il motore implementa. Per ciascun caso: preparare i dati (transazioni via API/import), aprire il pannello
**Lots Analysis** dell'asset, verificare l'atteso. Selettori `data-testid`.

### A.1 — Pool FEE
| # | Caso | Atteso |
|---|------|--------|
| FEE-1 | FEE solo BUY | quota su lotti aperti (`context=OPENING`), peso per controvalore target |
| FEE-2 | FEE solo SELL | quota su lotti chiusi (`context=CLOSURE`), peso `ClosedQty/ΣClosed` |
| FEE-3 | FEE BUY+SELL | `rule=SAME_DAY_MIXED_TRADES`, ripartizione per controvalore, **nessun warning** |
| FEE-4 | più FEE stesso pool | somma pool prima dell'allocazione; `source_transaction_ids[]` elenca tutte |
| FEE-5 | FEE previous-day | nessun trade same-day → `rule=PREVIOUS_DAY_TRADES` |
| FEE-6 | FEE fallback holding | nessun trade → open-lots(D-1), `rule=OPEN_LOTS_FALLBACK` (`context=HOLDING`) |
| FEE-7 | FEE orphan | nessun lotto → `asset_orphan_fees` + `ASSET_COST_NO_ELIGIBLE_LOTS`, banner DQ |
| FEE-8 | crossing LONG→SHORT e SHORT→LONG | costo split close/open, `Σ = CostTrade`, closure immutabili |

### A.2 — Pool TAX
| # | Caso | Atteso |
|---|------|--------|
| TAX-1 | TAX su DIVIDEND | allocata sui lotti eleggibili dell'income |
| TAX-2 | TAX su INTEREST | idem, target INTEREST |
| TAX-3 | TAX su DIVIDEND+INTEREST | target congiunto, `α_k`, `W_i=Σα_k w_{i,k}` |
| TAX-4 | più TAX stesso pool | somma pool prima dell'allocazione |
| TAX-5 | TAX senza income ma con trade same-day | fallback sul pool trade same-day |
| TAX-6 | TAX previous-day income | `rule=PREVIOUS_DAY_INCOME` |
| TAX-7 | TAX previous-day trade | `rule=PREVIOUS_DAY_TRADES` |
| TAX-8 | TAX fallback holding | open-lots(D-1), `context=HOLDING` |
| TAX-9 | TAX orphan | `asset_orphan_taxes` + `ASSET_COST_NO_ELIGIBLE_LOTS`, banner DQ |

### A.3 — Status
| # | Caso | Atteso |
|---|------|--------|
| ST-1 | COMPLETE | analisi piena, nessuna issue di affidabilità |
| ST-2 | DEGRADED income orphan | `calculation_status=DEGRADED`, income non allocato visibile, gross intatto |
| ST-3 | DEGRADED cost orphan | `DEGRADED`, FEE/TAX orphan visibili, gross intatto |
| ST-4 | DEGRADED FX mancante | `DEGRADED`, `FX_RATE_MISSING_FOR_ALLOCATION`, gross preservato |
| ST-5 | net UNAVAILABLE localizzato | `net_metrics_status=UNAVAILABLE` **solo** sui lotti del pool colpito; gli altri AVAILABLE |
| ST-6 | FAILED quantitativo | `calculation_status=FAILED`, ramo errore in `LotsAnalysisPanel` |

### A.4 — History e chiusura
| # | Caso | Atteso |
|---|------|--------|
| HI-1 | lotto chiuso senza costi successivi | serie lorda e netta coincidono dopo la chiusura |
| HI-2 | lotto chiuso con FEE in D+1 relativa alla SELL in D | (previous-day) netto modificato **dalla data della FEE** |
| HI-3 | lordo piatto dopo la chiusura | nessuna variazione lorda post-chiusura |
| HI-4 | netto con scalino | gradino **solo** sulla serie netta alla data del costo |
| HI-5 | prosecuzione serie | entrambe le serie continuano fino a `date_to` |

### A.5 — Audit (3 livelli, inline)
| # | Caso | Atteso |
|---|------|--------|
| AU-1 | pool solo OPENING | un `TargetOperationAllocation` `context=OPENING` |
| AU-2 | pool solo CLOSURE | un `TargetOperationAllocation` `context=CLOSURE` |
| AU-3 | pool misto | OPENING **e** CLOSURE nello stesso gruppo |
| AU-4 | stesso lotto in OPENING e CLOSURE | il lotto compare in due operazioni con `context` distinti |
| AU-5 | target INCOME | `context=INCOME`, `operation_transaction_id` = income |
| AU-6 | target HOLDING | `context=HOLDING`, `operation_transaction_id=None` |
| AU-7 | source transaction IDs | `source_transaction_ids[]` completo per pool multi-evento |
| AU-8 | importi nativi e target | ogni livello espone `native_amount` **e** `target_amount` |
| AU-9 | somma allocazioni = totale pool | `Σ allocation + orphan = pool` (nativo **e** target) |

---

## Decisioni aperte (conferma prodotto)

Micro-decisioni a basso rischio emerse dal recepimento review, da confermare (default proposto in grassetto):
1. **Empty analysis status:** il caso "nessun dato" (nessun broker/nessuna transazione) migra da
   `calculation_status=UNAVAILABLE` a **`COMPLETE`** con `lots=[]` (§7.2). Nessun consumer FE ramifica sullo
   status (grep=0), quindi la UI mostra lo stato vuoto dal payload. *Alternativa se si preferisce un segnale
   esplicito: mantenere un valore dedicato — ma esce dai 3 valori globali concordati.*
2. **Visibilità colonne nette:** mostrate di default (già deciso); rivalutare se nasconderle di default
   dopo aver visto la densità reale della tabella.
3. **Densità grafici lordo+netto:** implementare come previsto, decidere eventuali semplificazioni dopo la
   verifica manuale (Appendice A.4 / §8.3).

<!-- FINE PIANO -->
