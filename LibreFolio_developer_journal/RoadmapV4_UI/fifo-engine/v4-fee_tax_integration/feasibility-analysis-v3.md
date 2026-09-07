# Feasibility Analysis v3 — FIFO Engine v4 "Omni", integrazione FEE/TAX

**Documento analizzato:** `hig-level-analysis-v3.md` (1173 righe)
**Confronto con:** `high-level-analysis.md`, `feasibility-analysis.md`, `high-level-analysis-v2.md`, `feasibility-analysis-v2.md`
**Metodo:** verifica riga-per-riga contro il codice reale (`backend/app/services/fifo_lot_engine.py`, `lots_analysis_service.py`, `portfolio_engine.py`, `schemas/portfolio.py`, `schemas/transactions.py`).
**Vincolo:** nessuna modifica a codice, schemi, test o documenti esistenti. Solo review.

---

## 0. Executive summary

**Giudizio complessivo: GO CON MODIFICHE.**

`hig-level-analysis-v3.md` è la versione più matura e completa della serie. **Recepisce 17/18** dei punti obbligatori della review v2, inclusa la criticità BLOCCANTE (riconciliazione assoluta vs share_percentage) che ora è correttamente risolta con due invarianti distinti (§26.1 assoluto FIFO, §26.2 proiezione Portfolio). La matematica lorda del documento coincide esattamente con quella già implementata; il modello feed-forward è privo di doppio conteggio; la gerarchia FEE/TAX differenziata per tipo risolve il problema della ritenuta-su-cedola sollevato in v2.

Il documento è **sufficientemente completo, coerente e non ambiguo da diventare la base del piano implementativo**, a condizione di risolvere prima le seguenti criticità residue (nessuna è bloccante di per sé, ma 2 sono strutturali):

| # | Severità | Criticità | §doc |
|---|----------|-----------|------|
| C1 | **ALTO (strutturale)** | Cambio firma `run(quantitative_events, economic_events)` rompe TUTTI i call-site e le costruzioni dirette di `FifoEngineResult` nei test; manca strategia retro-compat concreta. | §2.1, §24 |
| C2 | **ALTO (strutturale)** | `calculation_status` è oggi binario `COMPLETE/DEGRADED` (proprietà derivata da `issues`); `ALLOCATION_CONSERVATION_FAILED` con `severity=ERROR` (§23.5) non è rappresentabile → serve un terzo stato `FAILED`/perimetro parziale. | §23.5, §24 |
| C3 | **MEDIO** | Chiave di raggruppamento della riconciliazione §26.1 non disambiguata: `Σ GrossIncome_i` per `(a,b)` — `b` è il broker **accreditante** dell'evento o quello di **custodia** del lotto? Durante i transfer differiscono. | §26.1 |
| C4 | **MEDIO** | L'accumulatore pre-share richiesto da §26.2 **non esiste** nel Portfolio Engine (`per_income`/`per_fees_taxes` sono già scalati per `share`). Va creato in Fase 7. | §26.2 |
| C5 | **MEDIO** | Tie-break adjacent-day mancante: con candidato a `D-1` e uno a `D+1` entrambi a distanza 1, "distanza minima" (§13.3) non decide. | §13.3 |
| C6 | **BASSO** | Multi-candidato same-tier: mancano formule esplicite di pooling per più SELL / più BUY / più income nello stesso tier (§14/§15/§17 definiscono il singolo caso). | §13.4, §14–17 |
| C7 | **BASSO (prodotto)** | FEE `SAME_DAY_SELL > SAME_DAY_BUY` attribuisce silenziosamente (senza issue) una fee di BUY a una SELL round-trip dello stesso giorno. Scelta deterministica accettabile ma da documentare. | §13.1 |

**Verifiche positive confermate sul codice:** crossing LONG/SHORT matematicamente esatto e implementabile coi dati esistenti; output quantitativo già sufficiente per la passata economica (nessuna estensione a `FifoLot`/`LotClosure`/`FragmentInterval`); D-1 riusa `_open_quantity_on_date`; rimozione dei metodi non qbq-aware sicura (zero consumer produttivi); DTO netti additivi compatibili.

---

## 1. Recepimento delle review precedenti

Confronto puntuale delle conclusioni cumulate delle due feasibility analysis con `hig-level-analysis-v3.md`.

| # | Conclusione precedente | Stato v3 | Evidenza |
|---|------------------------|----------|----------|
| 1 | Un solo `FifoLotEngine` pubblico | **RECEPITA** | §2.1: "una sola operazione pubblica … un solo risultato finale". |
| 2 | Due stadi interni obbligatori | **RECEPITA** | §2.2 pipeline `QuantitativeReplayStage → EconomicAllocationStage → CombinedInvariantValidation`. |
| 3 | Un solo `FifoEngineResult` finale | **RECEPITA** | §24: output pubblico unico con campi economici sempre presenti. |
| 4 | Core quantitativo non riordinato | **RECEPITA** | §3.1: "Questo ordinamento deve essere preservato". Coincide con `_event_sort_key` (`fifo_lot_engine.py:468-471`). |
| 5 | TRANSFER prima di SPLIT e BUY/SELL | **RECEPITA** | §3.1 ordine `TRANSFER_DEPART → TRANSFER_ARRIVE → SPLIT → BUY/SELL/ADJ`. Verificato: phase 0/1/2/3 in `_event_sort_key`. |
| 6 | Allocazione economica interna al dominio FIFO | **RECEPITA** | §2.2, §4: stage interno `_FifoEconomicAllocationStage` privato. Oggi l'income è allocato dal service (`lots_analysis_service.py:914` `_allocate_asset_income`). |
| 7 | `original_cost` invariato | **RECEPITA** | §1, §15, §19.1: "non aumentare original_cost con una fee". |
| 8 | Accumulatori indipendenti e feed-forward | **RECEPITA** | §2.4, §19: sei accumulatori separati, metriche derivate una sola volta. |
| 9 | FIFO assoluto e `share_percentage` esterno | **RECEPITA** | §2.3: "Il FifoLotEngine continua a operare su … importi assoluti. Non applica share_percentage". Coerente con `lots_analysis_service` che non applica share. |
| 10 | Riconciliazione assoluta pre-share | **RECEPITA (con dipendenza)** | §26.1 invariante assoluto; §26.2 proiezione. Vedi C4: l'accumulatore pre-share va creato. |
| 11 | Distinzione broker-unallocated vs asset-orphan | **RECEPITA** | §11.1 `broker_unallocated_*` (asset_id null, fuori FIFO) vs §11.2 `asset_orphan_*`. Risolve l'ambiguità "Unallocated" della v2. |
| 12 | Importi allocati in valuta originaria | **RECEPITA** | §21.1 `NativeAllocation`; §21.2 conversione dopo. |
| 13 | Riconciliazione separata in target currency | **RECEPITA** | §21.2, §27 (FX nativo + FX target). |
| 14 | Campi lordi esistenti mantenuti | **RECEPITA** | §25: `total_pnl`/`total_return` restano lordi. Coincide con `schemas/portfolio.py:542,544`. |
| 15 | Campi netti additivi | **RECEPITA** | §25: aggiunta `net_total_pnl`, `net_total_return`. |
| 16 | Audit trail opzionale | **RECEPITA** | §25: `COST_ALLOCATIONS` come analysis opzionale. |
| 17 | Rimozione metodi non qbq-aware | **RECEPITA** | §6.2. Verificato: `value_for_lot`/`aggregate_value`/`relative_return_for_lot` usati solo in test. |
| 18 | Data Quality completa | **RECEPITA** | §23: tutte e 5 le issue (v2 ne definiva 2). |
| — | FEE/TAX segno negativo → `abs()` | **RECEPITA (nuovo)** | §12.1 `CostTotal = |TransactionAmount|`. Coincide con `schemas/transactions.py` (amount<0). |
| — | Priorità TAX distinta (ritenuta su income) | **RECEPITA (nuovo)** | §13.2 `SAME_DAY_INCOME` primo per TAX. |
| — | ADJACENT_DAY per SELL/BUY oltre income | **RECEPITA (nuovo)** | §13.1/§13.2: tier adjacent per tutti e tre. Risolve il gap v2 (fee di trade T+1). |

**Punti SUPERATI:** la v2 raccomandava una classe `FifoEconomicAllocator` come componente separato interno; v3 la trasforma correttamente in stage privato di modulo (`_FifoEconomicAllocationStage`), coerente con "un solo motore pubblico". Scelta migliore.

**NUOVI CONFLITTI:** nessun conflitto logico introdotto. I 7 punti in C1–C7 sono lacune di specifica, non contraddizioni.

---

## 2. Unicità e autoconsistenza del motore

La pipeline `Q = ReplayQuantitative(E_Q)`, `A = AllocateEconomic(E_E, Q)`, `R = ValidateAndCompose(Q, A)` è concettualmente corretta e garantisce che il risultato economico dipenda da quello quantitativo, non viceversa.

**Stato reale del codice (da correggere in fase implementativa):**

- `FifoLotEngine.run()` oggi **non prende argomenti** (`fifo_lot_engine.py:343`); gli eventi sono passati al costruttore e l'income è filtrato a monte nel service. La firma proposta `run(quantitative_events=…, economic_events=…)` è un cambio di contratto.
- `FifoEngineResult` (`fifo_lot_engine.py:190`) è un `@dataclass(slots=True)` con soli campi quantitativi (`lots`, `fragment_intervals`, `closures`, `issues`, `classified_events`). `calculation_status` è una **property derivata** da `issues` (`:198-200`), non un campo.

**C1 — rischio retro-compatibilità (ALTO).** Ogni costruzione diretta di `FifoEngineResult` (presente nei test, es. `test_fifo_lot_engine.py`) e ogni call-site di `run()` andranno aggiornati. Il documento §15/§24 riconosce il rischio ma non fornisce strategia. **Modifica testuale richiesta:** aggiungere in §24 la regola:
> «I nuovi campi economici hanno `default_factory=list`/`dict`; se `economic_events` è vuota lo stage economico produce collection vuote ma **viene comunque eseguito**; `run()` senza `economic_events` resta valido e restituisce accumulatori economici a zero. Nessun campo economico è opzionale (`None`): sempre presente, eventualmente vuoto.»

**Come distinguere "nessun evento economico" da "risultato incompleto":** la domanda del prompt §2 è pertinente. Raccomandazione: **non** usare l'assenza di allocazioni come segnale. Aggiungere un flag esplicito `economic_stage_completed: bool` in `FifoEngineResult` (sempre `True` dopo `run()`, poiché lo stage è obbligatorio). Questo previene che `LotsAnalysisService` usi accidentalmente un risultato solo-quantitativo: se un percorso ottiene un result senza stage economico, il flag è `False` e il service può sollevare errore. **Modifica testuale:** integrare §24 con `economic_stage_completed`.

**Superficie API minima raccomandata (pubblica):**
- `FifoLotEngine.run(quantitative_events, economic_events, *, target_currency=None) -> FifoEngineResult` — unico entrypoint.
- `FifoEngineResult` — dataclass di sola lettura; metodi query esistenti (`get_lot`, `active_fragments`, `get_lot_states`).

**Interno (privato di modulo):** `_QuantitativeReplayStage`, `_FifoEconomicAllocationStage`, `_CombinedInvariantValidation`. Nessuno esposto. **Non** deve esistere un `AllocateEconomic()` pubblico che accetti un `Q` arbitrario: sarebbe una seconda fonte di verità.

**Nota su "passata sempre eseguita anche con lista vuota":** sì, obbligatoria. Serve a garantire che gli accumulatori economici (a zero) e il flag `economic_stage_completed=True` siano presenti sempre, uniformando il contratto.

---

## 3. Stato quantitativo disponibile alla passata economica

Verifica che `Q` contenga tutto il necessario. Riscontro sul codice (`fifo_lot_engine.py`):

| Dato richiesto (prompt §3) | Disponibile | Simbolo |
|---|---|---|
| lot_id | ✅ | `FifoLot.lot_id` (`:153`) |
| opening_transaction_id | ✅ | `FifoLot.opening_transaction_id` (`:156`) |
| opening_date | ✅ | `FifoLot.opening_date` (`:158`) |
| opening_broker_id | ✅ | `FifoLot.opening_broker_id` (`:157`) |
| direction | ✅ | `FifoLot.direction` (`:155`) |
| original_quantity | ✅ | `:159` |
| original_cost | ✅ | `:161` |
| fragments / fragment intervals | ✅ | `FragmentInterval` (`:122-134`) |
| source/destination broker | ✅ | `FragmentInterval.source_broker_id`, `destination_broker_id` (`:133-134`) |
| custody_type (BROKER/IN_TRANSIT) | ✅ | `:127` |
| closures | ✅ | `LotClosure` list (`:195`) |
| closing transaction id | ✅ | `LotClosure.transaction_id` (`:140`) |
| closed quantity | ✅ | `LotClosure.quantity` (`:141`) |
| close reason | ✅ | `LotClosure.close_reason` ∈ {SELL, BUY, ADJUSTMENT_OUT} (`:143`) |
| transaction date | ✅ | `LotClosure.close_date` (`:142`) |
| split-adjusted quantities | ✅ | applicate nei fragment (`_apply_split`) |
| transfer lineage | ✅ | fragment `source/destination_broker_id` + intervalli half-open |

**Conclusione: nessuna estensione di `FifoLot`, `LotClosure` o `FragmentInterval` è necessaria** per la passata economica. Il documento non chiede estensioni a queste dataclass (corretto). L'unico dato "nuovo" sono gli accumulatori economici, che risiedono nel risultato dell'allocation stage (§19.1), non nelle strutture quantitative — coerente.

**Mapping ausiliari da costruire una sola volta** (raccomandazione al piano, prompt §3):

```
opening_tx_id → lot                    # da FifoLot
closing_tx_id → [closures]             # group-by LotClosure.transaction_id
(date, asset, broker) → [BUY lots]     # lot con opening_date/broker + close_reason
(date, asset, broker) → [SELL closures]# closures con close_reason=="SELL"
(date, asset, broker) → [income tx]    # da EconomicEvent
(lot_id, D-1) → EligibleQuantity       # _open_quantity_on_date(frags, D-1)
(broker, D-1) → custody-compatible frags
```

**Complessità (vedi §18):** costruzione dei mapping `O(N + C + F)` una tantum; ogni evento economico consulta gli indici in `O(candidati)`. Accettabile. Il rischio è la scansione ripetuta dei frammenti per ogni evento economico (`O(E·F)`): mitigabile pre-indicizzando i frammenti per `(broker, giorno)`.

---

## 4. Semantica temporale completa (D-1)

Regola v3 §7.1: `EligibleQuantity_i(D) = OpenQuantity_i(D-1)`.

**Comportamento attuale (da cambiare):** `_allocate_asset_income` (`lots_analysis_service.py:940-951`) usa **`tx.date` (= D)**, non D-1:
- filtra lotti LONG con `opening_date <= tx.date` (`:944`) → un **BUY in D è oggi eleggibile** (opening_date == D passa);
- `_fragment_active_on_date` è half-open `start ≤ q < end` (`:1691-1692`) → una SELL in D chiude il frammento con `end_date=D`, quindi `q < end` è falso in D → **SELL in D oggi NON eleggibile**.

La regola D-1 **inverte entrambi**: BUY in D → non eleggibile; SELL in D → eleggibile. È un vero cambio di comportamento (già segnalato in v1/v2, ora formalizzato). Implementabile riusando `_open_quantity_on_date(frags, D - timedelta(days=1))` — **nessun nuovo helper temporale necessario** (l'helper è data-parametrico, `:1633`).

**Matrice temporale (stato a D-1 → eventi in D → risultato):**

| Scenario | Stato a D-1 | Eventi in D | Lotti eleggibili | Qty eleggibile | Risultato atteso | Conflitto |
|---|---|---|---|---|---|---|
| BUY + income in D | 0 | BUY q, income | ∅ (BUY non conta) | 0 | income → orphan/issue | Nessuno |
| SELL + income in D | q aperta | SELL q, income | il lotto (open a D-1) | q | income → lotto pre-SELL | Nessuno |
| BUY e SELL in D (round-trip) | 0 | BUY q, SELL q | ∅ | 0 | income → orphan | Nessuno |
| SPLIT + income in D | q aperta | SPLIT ×k, income | lotto | q (pre-split) | income totale su lotto; pesi invarianti | Nessuno (vedi nota) |
| ADJUSTMENT + income in D | q aperta | ADJ, income | lotto pre-adj | q(D-1) | income su qty pre-adj | Coerente |
| TRANSFER depart in D | q su From | depart, income su From | frammenti From + IN_TRANSIT-from-From | q | income → From | Nessuno |
| TRANSFER arrive in D | in transito | arrive, income su To | ∅ su To (D-1 = in transito) | 0 su To | issue su To; From eleggibile | Vedi §5/C7-prod |
| depart e arrive stesso D | q su From (D-1) | depart+arrive, income | From (D-1) | q | income → From | §9.4 OK |
| lotto chiuso in D | q aperta | SELL totale, income | lotto (D-1) | q | income cristallizzato sul lotto | Nessuno |
| aperto+chiuso stesso D | 0 | BUY+SELL, income | ∅ | 0 | orphan | Nessuno |
| più eventi economici in D | q | income₁, income₂ | lotto | q(D-1) per entrambi | ciascuno pesato su D-1 | Nessuno |

**Nota SPLIT (§7.2):** l'uso della quantità **pre-split** è economicamente neutro. I pesi sono rapporti `q_i / Σq_j`; se lo split applica lo stesso fattore `k` a tutti i lotti dell'asset, `k` si semplifica e i pesi restano identici. La conservazione `Σ IncomeAllocation_i = IncomeTotal` è preservata. Il documento è corretto ma la giustificazione in §7.2 è incompleta: **modifica testuale suggerita** — aggiungere «poiché lo split applica un fattore uniforme, i pesi pre/post-split coincidono; la scelta è indifferente ai fini dell'allocazione».

**Verifica "nessun uso opportunistico di end-of-day quando si dichiara D-1":** confermato che il codice attuale usa end-of-day D (`tx.date`), non D-1. La migrazione deve sostituire `tx.date` con `D-1` in `_open_quantity_on_date`. **Attenzione:** il filtro `opening_date <= tx.date` (`:944`) va cambiato in `opening_date <= D-1` (equivalente a `opening_date < tx.date`), altrimenti un lotto aperto in D resterebbe candidato pur avendo `EligibleQuantity=0`.

---

## 5. Proventi broker-aware e transfer

**Formula §8** `EligibleLots(a,b,D)`: verificata concettualmente corretta. Oggi **non** è broker-aware: `_allocate_asset_income` itera `lots_by_id` (tutti i lotti dell'asset, `:943`) senza filtro broker → **bug confermato**. Il helper `_fragment_in_scope` (`:1636-1639`) esiste già e sa distinguere custody BROKER vs IN_TRANSIT con source/destination — riutilizzabile per `CustodyCompatible_i(b,D)`.

**Simulazioni numeriche:**

*Caso ordinario (§5 prompt):* Directa 30, IBKR 70, DIVIDEND +100 su Directa.
- `L(asset, Directa, D)` = solo lotti custoditi su Directa → 30 quote → peso 1 → **Directa = 100, IBKR = 0**. ✅

*Transfer parziale:* 100 originarie, 40 restano su From, 60 in transito From→To.
- Income su **From**: eleggibili = 40 (BROKER-From) + 60 (IN_TRANSIT source=From) = **100**. ✅ (§9.1)
- Income su **To**: eleggibili = 0 fino all'arrivo (nessun frammento BROKER-To a D-1). ✅ (§9.2)

**Casi risolti rispetto alla v2:**

| Caso | Regola v3 | Univoco? |
|---|---|---|
| Giorno di arrivo, income su To | D-1 = in transito → 0 su To → issue | ✅ §9.3 |
| Giorno di arrivo, income su From | D-1 = in transito da From → eleggibile su From | ✅ §9.3 |
| Transfer same-day (depart=arrive) | D-1 stato = From → income su From | ✅ §9.4 |
| Transfer di ritorno | stato reale frammenti a D-1 | ✅ §9.5 |
| Catena A→B→C | solo stato materializzato a D-1; no custodie inferite | ✅ §9.5 |
| Più transfer concorrenti | somma frammenti per broker a D-1 | ✅ |
| Transfer che consuma più lotti | ogni frammento porta il suo `source_broker_id` | ✅ |

**C7-prodotto (attrito reale):** la combinazione D-1 + broker-aware genera una issue `ASSET_INCOME_NO_ELIGIBLE_LOTS` ogni volta che un broker reale accredita un dividendo sul broker **ricevente** nel giorno di arrivo (pratica comune: molti broker pagano la cedola sul conto di destinazione dopo il trasferimento). Economicamente corretto (a D-1 il titolo era in transito dal From), ma potenzialmente rumoroso. **Decisione di prodotto:** accettare il rumore come segnale di riconciliazione (posizione del documento) oppure introdurre una tolleranza "arrival-day grace" che consideri eleggibili i frammenti IN_TRANSIT-verso-To nel solo giorno di arrivo. Il documento sceglie la prima (§9.3: "senza introdurre eccezioni end-of-day") — **coerente e difendibile**, ma va esplicitato tra le decisioni di prodotto.

---

## 6. Bucket orphan e riconciliazione assoluta

**Distinzione §11 verificata e corretta:**
- `broker_unallocated_*` ↔ `asset_id = null` → oggi già gestito dal Portfolio Engine: `unalloc_income` (`portfolio_engine.py:840`), `unalloc_fees` (`:851`). **Resta fuori dal FIFO** (corretto).
- `asset_orphan_*` ↔ `asset_id` presente ma nessun lotto eleggibile → nuovo bucket nel FIFO.

**Invariante assoluto §26.1:** `Σ GrossIncome_i + AssetOrphanIncome = AbsoluteAssetIncome_{a,b,T}` (idem fees/taxes). Matematicamente ben posto **a condizione** di chiarire la chiave `b`.

**C3 — ambiguità della chiave broker (MEDIO).** Nel Portfolio Engine `per_income` è keyed su `(tx.asset_id, tx.broker_id)` (`:838`) dove `tx.broker_id` è il **broker accreditante** dell'evento. Nel FIFO, `GrossIncome_i` è allocato ai **lotti** che possono risiedere su un broker di custodia diverso dall'`opening_broker_id` (dopo un transfer). Perché l'invariante regga, la somma `Σ GrossIncome_i` va raggruppata per il **broker accreditante dell'evento economico** (lo stesso `b` del Portfolio Engine), non per il broker di custodia del lotto. **Modifica testuale §26.1:** specificare «`b` = broker accreditante dell'evento; ogni `EconomicAllocation` conserva `broker_id` = broker dell'evento sorgente per il raggruppamento della riconciliazione, indipendentemente dalla custodia del lotto ricevente».

**C4 — accumulatore pre-share mancante (MEDIO).** §26.2 richiede accumulatori pre-share per riconciliare FIFO assoluto vs Portfolio user-scoped. Verificato: `per_income`/`per_fees_taxes` sono **già scalati** per `ctxn.share` (`:748` `amount_target *= ctxn.share`; usati a `:838,849`). Non esiste oggi un accumulatore assoluto pre-share nel Portfolio Engine. **Va introdotto in Fase 7** un `per_income_absolute[(asset,broker)]` che accumuli `amount_target` **prima** della moltiplicazione per share. Il documento lo prevede ("usare accumulatori pre-share oppure una proiezione esplicita") ma non lo colloca in un file: **modifica testuale Fase 7** — nominare esplicitamente `portfolio_engine.py` e il nuovo accumulatore.

**Perimetro dell'invariante (prompt §6):** asset, broker (accreditante), periodo `[date_from, date_to]`, valuta (nativa per l'invariante nativo; target per quello FX), utente. **Transazioni fuori range ma rilevanti allo stato:** il replay quantitativo deve caricare tutte le transazioni fino a `date_to` (stato lotti), ma l'invariante di income/fee/tax si applica solo agli eventi economici **nel periodo**. Coerente con `_trim_dates` (`:1664`). **Eventi in transito:** contribuiscono all'eleggibilità (frammenti IN_TRANSIT), non generano doppio conteggio perché ogni evento economico è un'unica transazione.

**Conferma:** `share_percentage` non deve entrare nel FIFO. §2.3 corretto.

---

## 7. Priorità FEE e TAX

Gerarchie §13.1 (FEE) e §13.2 (TAX). Valutazione per tier:

| Tier | Candidati | Scope | Qty temporale | Peso | Issue |
|---|---|---|---|---|---|
| SAME_DAY_SELL | closures `close_reason=="SELL"`, stesso D/a/b | asset+broker | ClosedQty | `w_i = ClosedQty_i/ΣClosedQty` (§14) | AMBIGUOUS se >1 candidato |
| SAME_DAY_BUY | lotti aperti da BUY, stesso D/a/b | asset+broker | OpeningValue | `w_i = OV_i/ΣOV` (§15) | idem |
| SAME_DAY_INCOME | income tx, stesso D/a/b | asset+broker | pesi income (§17) | riusa income weights | idem |
| ADJACENT_DAY_* | idem in D±1 | asset+broker | idem | idem | AMBIGUOUS + adjacency |
| OPEN_LOTS_FALLBACK | lotti LONG aperti a D-1 | asset+broker | OpenQty(D-1) | `w_i = OpenQty_i/Σ` (§18) | — |
| NO_ELIGIBLE_LOTS | — | — | — | — | ASSET_COST_NO_ELIGIBLE_LOTS |

**Simulazioni:**
- *SELL + INTEREST + TAX stesso giorno:* FEE→SELL (§13.1), TAX→INCOME (§13.2 primo). ✅ separazione corretta.
- *BUY + SELL + FEE stesso giorno:* FEE→SELL (SAME_DAY_SELL vince su SAME_DAY_BUY). **C7:** se la fee era di apertura (BUY), viene silenziosamente attribuita alla SELL, senza issue (tier diversi, non "più candidati nello stesso tier"). Accettabile ma da documentare come euristica.
- *Due SELL + una FEE:* stesso tier SAME_DAY_SELL con 2 candidati → distribuzione sull'intero tier + AMBIGUOUS. Vedi C6.
- *Due BUY + una FEE:* SAME_DAY_BUY, 2 candidati → distribuzione + AMBIGUOUS.
- *Due proventi + una TAX:* SAME_DAY_INCOME, 2 candidati → distribuzione + AMBIGUOUS.
- *FEE/TAX a D-1 e a D+1:* ADJACENT_DAY. **C5:** entrambi a distanza 1 → tie non risolto.
- *Costo asset-linked periodico (custodia):* nessun SELL/BUY/income → OPEN_LOTS_FALLBACK. ✅
- *Asset completamente chiuso:* nessun lotto LONG aperto a D-1 → NO_ELIGIBLE_LOTS → asset_orphan. ✅

**Robustezza della priorità differenziata:** sufficiente per il caso dominante (ritenuta su cedola). Restano due ambiguità documentabili (C5 tie adjacent, C7 fee round-trip). **Non** serve classificazione fiscale testuale obbligatoria (il documento correttamente la lascia euristica opzionale, §5.2).

---

## 8. Più candidati nello stesso tier

**Decisione §13.4** (distribuzione sull'intero tier + AMBIGUOUS) è robusta e conservativa. **C6:** mancano le formule di pooling esplicite. Definizione raccomandata (da aggiungere al documento):

- **Più SELL:** unione di **tutte** le closure dei SELL candidati; `w_i = ClosedQty_i / Σ_j ClosedQty_j` sul pool unificato. Conservativo: `Σ AllocatedCost_i = CostTotal`.
- **Più BUY:** unione dei lotti aperti dai BUY candidati; `w_i = OpeningValue_i / Σ OpeningValue_j`.
- **Più income:** raccomandazione — **pesi finali dei lotti** prodotti da ciascun income (combinazione a due livelli): per ogni income `k` con peso relativo `α_k = |Income_k| / Σ|Income_j|`, e per ogni lotto `i` con peso `w_{i,k}` interno all'income `k`, il peso finale è `Σ_k α_k · w_{i,k}`. Questo garantisce che una TAX su due cedole segua la distribuzione economica effettiva delle cedole, non la sola quantità. Conservativo per costruzione (`Σα_k=1`, `Σ_i w_{i,k}=1`).

**Semantica dell'issue AMBIGUOUS (prompt §8):** rappresenta **entrambe** le condizioni — allocazione **eseguita** (nessun importo perso) **ma euristica** (segnalata). Non è "costo non allocato" (quello è NO_ELIGIBLE_LOTS). **Modifica testuale §23.3:** esplicitare «l'importo è interamente allocato; la issue segnala solo l'incertezza sul target, non una perdita».

---

## 9. Crossing LONG/SHORT

**Verifica matematica §16:** `Cost_close = CostTotal·q_c/q`, `Cost_open = CostTotal·q_o/q`, con `q = q_c + q_o` ⇒ `Cost_close + Cost_open = CostTotal`. ✅ Invariante §16.3 esatto.

**Disponibilità dati (verificata):**
- *BUY che chiude SHORT e apre LONG* (`_apply_buy`, `fifo_lot_engine.py:473-494`): `q_c` = Σ quantità delle closure con `transaction_id==buy.id` e `close_reason=="BUY"` (`:480`); `q_o` = quantità del lotto aperto con `opening_transaction_id==buy.id` (`:485-494`). Entrambi disponibili.
- *SELL che chiude LONG e apre SHORT* (`_apply_sell`, `:496-528`): `q_c` = closure `close_reason=="SELL"`; `q_o` = lotto SHORT aperto (`:510-520`). Disponibili.

**Simulazioni numeriche:**

*BUY 10 chiude SHORT 4, apre LONG 6, CostTotal=30:*
- `Cost_closeShort = 30·4/10 = 12` → ripartito sulle closure SHORT (per ClosedQty).
- `Cost_openLong = 30·6/10 = 18` → al nuovo lotto LONG (accumulatore `allocated_fees`).
- Somma 12+18=30. ✅

*SELL 10 chiude LONG 7, apre SHORT 3, CostTotal=50:*
- `Cost_closeLong = 50·7/10 = 35` → closure LONG.
- `Cost_openShort = 50·3/10 = 15` → nuovo lotto SHORT.
- 35+15=50. ✅

**Strutture destinatarie:** la quota closure NON può mutare `LotClosure` (è `frozen=True`, `:137`). Va tracciata come `EconomicAllocation` con `context=CLOSURE` e accumulata nell'`allocated_fees/taxes` del **lotto chiuso**. La quota opening va nell'accumulatore del **lotto opposto appena aperto** (`context=OPENING`). Il documento §16 dice "assegnata al nuovo lotto" ma non menziona il vincolo `frozen` — **modifica testuale §16:** aggiungere «le closure sono immutabili; l'attribuzione avviene sugli accumulatori economici per-lotto, non mutando `LotClosure`».

**Rendimento SHORT:** §16.3 usa il nozionale di apertura come denominatore, coerente con `total_return = total_pnl/opening_value` già implementato. Per SHORT `opening_value` = proventi di apertura (short sale). ✅

---

## 10. Modello feed-forward e minimalità

**Sei accumulatori** (§19.1): `original_cost, sale_proceeds, gross_income, allocated_fees, allocated_taxes, open_value`. Formule §19.2-19.6.

**Coincidenza con l'implementazione lorda:** `lots_analysis_service.py:1044` calcola `total_pnl = market_pnl + realized_pnl + asset_income`; `:1047` `total_return = total_pnl/opening_value`. Corrisponde a `GrossPnL = OpenValue + SaleProceeds + GrossIncome − OriginalCost` (con `OpenValue+SaleProceeds−OriginalCost = market_pnl+realized_pnl`). ✅

**Verifica assenza doppio conteggio** (scenario canonico BUY 10@100, SELL 4@120, prezzo 110, DIV 50):
- OpenValue = 6·110 = 660; SaleProceeds = 480; OriginalCost = 1000; GrossIncome = 50.
- GrossPnL = 660 + 480 + 50 − 1000 = **190**. GrossReturn = 190/1000 = **19%**.
- Con FEE 5 su SELL + TAX 10 su DIV: NetPnL = 190 − 15 = **175**; NetReturn = 17.5%.
- L'income entra **una sola volta** in GrossEconomicValue; le fee/tax entrano **una sola volta** in NetPnL. Nessun importo aggiunto e poi sottratto tramite accumulatori diversi. ✅

**NetIncome (§17)** è vista **derivata**, non accumulatore: `NetIncome_i = GrossIncome_i − IncomeFee_i − IncomeTax_i`. Le fee/tax su income confluiscono in `allocated_fees/allocated_taxes` (unica fonte), e NetPnL le sottrae una volta. Nessun doppio conteggio tra NetIncome e NetPnL (NetIncome è una scomposizione di reporting). ✅ §17 lo dichiara esplicitamente.

**Persistenza dopo chiusura (§20):** verificata la necessità — dopo chiusura `OpenValue=0` ma `SaleProceeds/GrossIncome/AllocatedFees/AllocatedTaxes` restano cristallizzati fino a `date_to`. Corretto: nel codice attuale il P&L realizzato e i proventi restano sul lotto chiuso (le closure sono cristallizzate). Coerente.

**Estimated-at-cost:** se `OpenValue` è stimato al costo (reference price = opening price), `OpenValue ≈ OriginalCost` per la parte aperta ⇒ `GrossPnL ≈ realized + income`. L'income NON è contato due volte (entra solo in GrossEconomicValue). ✅ Nessun rischio individuato.

**Casi limite:** `OriginalCost ≤ 0` (§19.6): il rendimento resta non disponibile (non inventato). ✅ Coerente con `total_return` opzionale (`schemas/portfolio.py:544`, "when > 0").

---

## 11. Valuta nativa, target e residui

**Doppia conservazione §21/§27:** `Σ NativeAllocation = NativeTotal` e `Σ TargetAllocation = TargetTotal`. La policy in 5 passi (pesi nel motore → alloca nativo → converte totale evento una volta → ripartisce target con stessi pesi → residui deterministici) è **corretta e robusta**.

**Punto di forza:** convertire il **totale dell'evento una sola volta** (§21.2), non le singole allocazioni, evita errori di arrotondamento accumulati e garantisce che `Σ TargetAllocation = FXConvert(NativeTotal)` esattamente. Coerente con il pattern running-remainder già usato in `_allocate_asset_income` (`:955-961`, l'ultimo lotto assorbe il residuo).

**Residuo:** il documento assegna il residuo "all'ultimo lotto secondo ordinamento stabile" **in entrambe le valute** (§21.1, §21.2). Raccomandazione (prompt §11): applicare il residuo **in entrambe le fasi indipendentemente** (nativo sull'ultimo lotto in valuta nativa; target sull'ultimo lotto in target), poiché la conversione non è lineare sugli arrotondamenti. Il documento lo fa correttamente. ✅

**Indipendenza dalla target currency:** il **risultato del motore** (pesi + allocazioni native) NON dipende dalla target currency (§2.3, §21). Le metriche target sono responsabilità del service. ✅ Questo abilita analisi ripetute in EUR/USD senza rieseguire il replay quantitativo — proprietà preziosa, correttamente sancita.

**FX mancante:** §23.4 `FX_RATE_MISSING_FOR_ALLOCATION` (WARNING/DEGRADED) — l'allocazione nativa resta disponibile, le metriche target coinvolte incomplete. Coerente con il fallback FX esistente.

---

## 12. Audit trail

**Modello §22** `EconomicAllocation` (14 campi). Valutazione:

| Campo | Fonte | Note |
|---|---|---|
| source_transaction_id, target_transaction_id, lot_id, broker_id, date, type, context, rule, weight, candidate_count | **motore** (risultato nativo) | tutti derivabili dallo stato quantitativo + regola |
| native_amount, native_currency | **motore** | |
| target_amount, target_currency | **service** (dopo FX) | |

**Decisione struttura unica vs doppia (prompt §12):** raccomando **struttura unica arricchita dal service**. Il motore produce `EconomicAllocation` con `target_amount=None`/`target_currency=None`; il service li popola dopo FX. Motivazione: coerente con "un solo motore, un solo risultato"; evita duplicazione `Native*`/`Target*`; l'ordinamento deterministico è unico. Una doppia struttura `NativeEconomicAllocation`/`TargetEconomicAllocation` violerebbe la minimalità.

**Campi esclusi correttamente (§22):** `confidence`, `description` duplicata, `closure_id` — ricavabili da `rule`+`context`+transazioni. ✅ Concordo. `context=CLOSURE` + `target_transaction_id` identificano la closure senza `closure_id`.

**Distinzione closure vs opening:** via `context ∈ {OPENING, CLOSURE, INCOME, HOLDING}`. ✅ Sufficiente.

**Ordinamento deterministico:** raccomandazione — ordinare per `(date, source_transaction_id, rule, lot_id)`. Da esplicitare nel documento.

**Multi-target (un costo su più lotti):** una `EconomicAllocation` **per (source_tx, lot)**, con `weight` che ne indica la quota. Non serve una struttura annidata. ✅

---

## 13. Data Quality

Le 5 issue §23 sono complete rispetto a prompt §13. Verifica:

| Issue | Emissione | Severity | Status | Note |
|---|---|---|---|---|
| ASSET_INCOME_NO_ELIGIBLE_LOTS | allocation income, `L=∅` | WARNING | DEGRADED | ✅ |
| ASSET_COST_NO_ELIGIBLE_LOTS | fallback fee/tax vuoto | WARNING | DEGRADED | ✅ |
| FEE_TAX_ALLOCATION_AMBIGUOUS | >1 candidato same-tier | WARNING | DEGRADED | ✅ vedi C6/§8 |
| FX_RATE_MISSING_FOR_ALLOCATION | conversione target fallita | WARNING | DEGRADED | ✅ |
| ALLOCATION_CONSERVATION_FAILED | delta > tolleranza | **ERROR** | (vedi C2) | ⚠ |

**C2 — stato non rappresentabile (ALTO).** `calculation_status` è oggi una property binaria: `DEGRADED if self.issues else COMPLETE` (`fifo_lot_engine.py:198-200`). Una issue `severity=ERROR` (§23.5) **verrebbe comunque mappata a DEGRADED**, indistinguibile da un WARNING. §23.5 vuole invece che «net_total_pnl e net_total_return risultino non disponibili nel perimetro affetto» mentre «il resto continua DEGRADED se isolabile» — un comportamento a tre stati. **Modifica richiesta:** introdurre un terzo valore (`FAILED` o `PARTIAL`) o rendere `calculation_status` funzione della **massima severity** presente, e definire il perimetro (per-lotto/per-broker) su cui le metriche nette diventano `None`. Da specificare in §23.5 e §24.

**Issue aggiuntive suggerite (prompt §13):** valutate, ma **evitare duplicazioni**:
- "adjacent-day con più candidati" → coperto da FEE_TAX_ALLOCATION_AMBIGUOUS (aggiungere param `adjacency=True`). Non serve nuova issue.
- "orphan asset-linked" → coperto da ASSET_COST/INCOME_NO_ELIGIBLE_LOTS.
- "target transaction non trovato" → non applicabile (nessun EXPLICIT_LINK nei dati reali; vedi §16).
- "evento economico con segno inatteso" (es. FEE positiva) → **nuova issue utile**: `ECONOMIC_EVENT_UNEXPECTED_SIGN` (WARNING), segnala dati sporchi. Raccomandata.
- "peso totale nullo" / "original_cost nullo" → gestiti come metrica non disponibile, non serve issue (rendimento resta `None`, §19.6). Non emettere issue per evitare rumore.

---

## 14. Hardening qbq

**Conferma rimozione (§6.2):** `value_for_lot` (`fifo_lot_engine.py:244`), `aggregate_value` (`:262`), `relative_return_for_lot` (`:283`). Ricerca esaustiva:

```
value_for_lot        → :269 (uso interno di aggregate_value) + test_fifo_lot_engine.py:416,417
aggregate_value      → test_fifo_lot_engine.py:418
relative_return_for_lot → test_fifo_lot_engine.py:210
```

**Zero consumer produttivi.** Il percorso produttivo usa `compute_holding_value(qty, price, qbq) = (qty/qbq)·price` (`valuation_utils.py`). La rimozione è sicura. ✅

**Test interessati:** solo `backend/test_scripts/test_services/test_financial/test_fifo_lot_engine.py` (righe 210, 416-418). Gli invarianti utili vanno riscritti con `compute_holding_value` o un helper qbq-aware locale ai test (§6.2 lo prescrive correttamente).

**Test permanente §6.3** (bond qbq=100): `Quantity=1000, QBQ=100, quote=98.50 → OpenValue=985`. Corretto. Deve coprire: open value, gross P&L, net P&L, relative return, e verificare che **FEE/TAX non siano scalate da qbq** (§6.3) — punto importante: le fee sono importi monetari assoluti, non quotazioni. ✅

**Raccomandazione netta:** **rimozione** (non "qbq obbligatoria in firma"). I metodi sono morti in produzione; mantenerli con firma qbq sarebbe superficie inutile. Concordo con §6.2.

---

## 15. Risultato unico e contratto interno

`FifoEngineResult` esteso (§24) con `economic_allocations`, `economic_accumulators_by_lot`, `asset_orphan_income/fees/taxes`. Valutazione:

- **Sempre presenti, collection vuote** (non opzionali): raccomandato per contratto stabile. Vedi C1.
- **`economic_stage_completed`**: aggiungere flag esplicito (§2 sopra) per impedire uso accidentale di risultato solo-quantitativo.
- **Costruzioni dirette nei test:** `FifoEngineResult(...)` è invocato con kwargs posizionali nei test; l'aggiunta di campi con `default_factory` mantiene la retro-compatibilità **solo se** i nuovi campi hanno default. `@dataclass(slots=True)` supporta default → OK, ma i test che verificano l'uguaglianza strutturale o il numero di campi vanno riesaminati.

**Strategia retro-compatibile raccomandata:**
1. Aggiungere campi economici con `default_factory` → i test quantitativi esistenti continuano a costruire `FifoEngineResult` senza specificarli.
2. Mantenere `run()` eseguibile con `economic_events=[]` (default) → percorsi solo-quantitativi restano validi durante la migrazione.
3. Solo in Fase 2, quando `LotsAnalysisService` smette di allocare income da sé, spostare la logica nello stage.

---

## 16. DTO/API

Estensione additiva §25: `allocated_fees, allocated_taxes, net_total_pnl, net_total_return` (summary) + `allocated_fees, allocated_taxes, net_pnl, net_total_return` (history).

**Verifica schemi (`schemas/portfolio.py`):**
- `LotSummarySchema` (`:513`), `LotValueHistoryPoint` (`:610`), `LotReturnHistoryPoint` (`:625`): tutti `extra="forbid"` (`:516,613,628`). I campi netti **additivi** sono fattibili ma richiedono `./dev.py api sync` (rigenerazione client Zodios).
- `total_pnl` (`:542`) e `total_return` (`:544`) già documentati come lordi — §25 chiede solo di esplicitarlo. Le history hanno già `income` (`:622,638`).
- Tipi: `SafeDecimal` (già usato) per gli importi; `Currency` per valori target-currency (`:395,440`). Precisione Decimal garantita. Optionalità: `net_total_return` deve essere `Optional` (denominatore può essere ≤0).

**`COST_ALLOCATIONS` come analysis opzionale (§25):** corretto per non gonfiare la response standard. Esiste già il pattern `requested_analyses`/`LotAnalysisType` (`lots_analysis_service.py:1677`) e `income_events` è già un'analysis opzionale (`:758`). Il DTO minimo: `CostAllocationSchema` con i campi §22 (source_tx, target_tx, lot_id, broker_id, date, type, context, rule, weight, candidate_count, native_amount, native_currency, target_amount, target_currency). Riusare `SafeDecimal`/`Currency`.

**Impatto client generato:** additivo → nessuna breaking change; solo nuovi campi opzionali. Dimensione response: `COST_ALLOCATIONS` può essere grande (una entry per (evento, lotto)); mantenerla opt-in è corretto.

**Naming:** coerente con l'esistente (`total_pnl`→`net_total_pnl`). **Nessuna rinomina distruttiva** — concordo con la scelta additiva.

---

## 17. Riconciliazione assoluta e Portfolio Engine

Invarianti §26.1 (assoluto FIFO) verificati matematicamente ben posti. La proiezione §26.2 `UserAmount = AbsoluteAmount · Share` è corretta.

**Stato del Portfolio Engine:** NON espone oggi valori pre-share. `per_income`/`per_fees_taxes` accumulano il valore **già** moltiplicato per `share` (`:748,838,849`). **Serve un accumulatore interno aggiuntivo** pre-share (C4). Non introdurre share nel FIFO (§2.3 corretto).

**Due invarianti distinti (risoluzione del BLOCCANTE v2):**
1. **Riconciliazione assoluta per broker** (FIFO ↔ Portfolio pre-share): `Σ GrossIncome_i^{FIFO} + AssetOrphan = per_income_absolute_{a,b}`.
2. **Riconciliazione user-scoped** (Portfolio): `per_income_{a,b} = per_income_absolute_{a,b} · Share_{user,b}`.

Il documento v3 le distingue correttamente (§26.1 vincolante FIFO, §26.2 proiezione). Questo **recepisce e risolve** la criticità bloccante della v2. Resta l'implementazione dell'accumulatore pre-share (Fase 7).

---

## 18. Performance e complessità

Con `N` transazioni quantitative, `E` eventi economici, `L` lotti, `F` frammenti, `C` closure, `D` date history:

| Stadio | Target | Rischio | Mitigazione |
|---|---|---|---|
| Replay quantitativo | `O(N log N)` (sort) + `O(N·F)` peggiore (consumo frammenti) | scansione frammenti per evento | già così oggi; accettabile |
| Matching same-day | `O(E)` con indici `(date,asset,broker)→candidati` | `O(E·(C+L))` se scansione lineare | pre-indicizzare closure/lotti per giorno |
| Matching adjacent-day | `O(E)` con stessi indici su D±1 | idem | riuso indici |
| Lookup custody D-1 | `O(F)` per evento se ingenuo | `O(E·F)` | pre-indicizzare frammenti per `(broker, giorno)`; oppure prefix-sum di OpenQuantity per lotto |
| Costruzione history | `O(L·D)` | `O(L·D)` denso | già presente; usare mappe prefix (`_open_quantity_on_date` già a mappe) |

**Complessità-obiettivo ragionevole:** replay `O(N log N + N·F̄)`; matching `O(E·k)` con `k` = candidati medi per giorno (piccolo); history `O(L·D)`. **Nessuna cache persistente** (prompt §18): solo strutture pre-indicizzate locali alla singola esecuzione. Il documento non affronta la performance esplicitamente — **modifica testuale suggerita:** aggiungere una nota in Fase 2 sui mapping pre-costruiti una tantum.

**Rischio conversioni FX duplicate:** mitigato dalla policy §21.2 (una conversione per evento, non per allocazione). ✅

---

## 19. Matrice di test definitiva

| ID | Scenario | Stato D-1 | Eventi qty | Eventi econ | Target | Allocazioni native | Metriche lorde | Metriche nette | Orphan | Issue | Test package |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | income D-1 | lot A open q | — | DIV su A | A | 100→A | income+ | — | — | — | test_fifo_economic |
| E2 | same-day BUY + income | 0 | BUY q | DIV | — | ∅ | — | — | income | ASSET_INCOME_NO_ELIGIBLE_LOTS | test_fifo_economic |
| E3 | same-day SELL + income | q open | SELL q | DIV | lot | 100→lot | income su lotto pre-SELL | — | — | — | test_fifo_economic |
| E4 | split same-day + income | q | SPLIT×2 | DIV | lot | 100→lot | pesi invarianti | — | — | — | test_fifo_economic |
| E5 | broker scope | Directa30/IBKR70 | — | DIV su Directa | Directa | Directa=100,IBKR=0 | — | — | — | — | test_fifo_broker |
| E6 | transfer From | 40 From+60 transit | — | DIV su From | From | 100 su From | — | — | — | — | test_fifo_transit |
| E7 | transfer To | 60 su To | — | DIV su To | To | 0 | — | — | income | NO_ELIGIBLE (se D-1 non arrivato) | test_fifo_transit |
| E8 | arrival day To | in transito D-1 | ARRIVE | DIV su To | — | 0 | — | — | income | ASSET_INCOME_NO_ELIGIBLE_LOTS | test_fifo_transit |
| E9 | same-day transfer | From D-1 | DEPART+ARRIVE | DIV | From | 100 su From | — | — | — | — | test_fifo_transit |
| E10 | catena A→B→C | reale D-1 | transfers | DIV su B | B (se transit-from-B) | per stato D-1 | — | — | — | — | test_fifo_transit |
| E11 | income orphan | 0 | — | DIV su A | — | ∅ | — | — | asset_orphan_income | ASSET_INCOME_NO_ELIGIBLE_LOTS | test_fifo_economic |
| E12 | FEE same-day SELL | q | SELL q | FEE | closures | w=ClosedQty | — | net−fee | — | — | test_fifo_fee |
| E13 | FEE same-day BUY | 0 | BUY q | FEE | lot | 100% | — | net−fee su lotto | — | — | test_fifo_fee |
| E14 | TAX same-day income | q | — | DIV+TAX | lot (income weights) | riusa pesi income | — | net income | — | — | test_fifo_tax |
| E15 | più candidati (2 SELL+FEE) | q | 2 SELL | FEE | pool closures | w=ClosedQty pool | — | net | — | FEE_TAX_ALLOCATION_AMBIGUOUS | test_fifo_fee |
| E16 | adjacent-day FEE (D+1) | q | SELL in D | FEE in D+1 | closures D | ADJACENT_DAY_SELL | — | net | — | (adjacency) | test_fifo_fee |
| E17 | fallback open lots | q LONG | — | FEE custodia | lotti LONG D-1 | w=OpenQty(D-1) | — | net | — | — | test_fifo_fee |
| E18 | nessun target | 0 LONG | — | FEE | — | ∅ | — | — | asset_orphan_fees | ASSET_COST_NO_ELIGIBLE_LOTS | test_fifo_fee |
| E19 | conservazione | q | SELL | FEE frazionaria | multi-lotto | residuo su ultimo lotto | — | Σ=CostTotal | — | — | test_fifo_conservation |
| E20 | crossing BUY (SHORT4→LONG6) | SHORT 4 | BUY 10 | FEE 30 | 12 close +18 open | 12+18=30 | — | net split | — | — | test_fifo_crossing |
| E21 | crossing SELL (LONG7→SHORT3) | LONG 7 | SELL 10 | FEE 50 | 35 close+15 open | 35+15=50 | — | net split | — | — | test_fifo_crossing |
| E22 | FX EUR/USD | q | SELL | DIV in USD, target EUR | lot | native USD, target EUR | — | — | — | — | test_fifo_fx |
| E23 | FX mancante | q | — | DIV in XXX | lot | native ok | — | target incompleto | — | FX_RATE_MISSING_FOR_ALLOCATION | test_fifo_fx |
| E24 | qbq=100 (bond) | q=1000 | BUY | — | — | OpenValue=985 | GrossPnL, return | net | — | — | test_fifo_qbq |
| E25 | estimated-at-cost | q | — | DIV | lot@cost | OpenValue≈cost | GrossPnL≈income | net | — | REFERENCE_PRICE_FALLBACK | test_fifo_economic |
| E26 | chiusura completa | q | SELL totale | DIV+FEE | lot | cristallizzato | GrossPnL fisso | NetPnL fisso | — | — | test_fifo_economic |
| E27 | SHORT return | — | SELL apre SHORT | FEE | lotto SHORT | denom=nozionale apertura | GrossReturn SHORT | net | — | — | test_fifo_crossing |
| E28 | original_cost=0 | q@0 | — | DIV | lot | income | return=None | net return=None | — | — | test_fifo_economic |
| E29 | riconciliazione assoluta | q | mix | DIV+FEE+TAX | per broker | — | Σ+orphan=absolute | — | — | — | test_fifo_reconciliation |
| E30 | share_percentage | q | DIV | — | — | FIFO assoluto | invariato da share | — | — | — | test_portfolio_reconciliation |

**Esempi numerici esatti** già forniti in §9 (crossing) e §10 (feed-forward 190/19%, net 175/17.5%). E5, E6, E20, E21, E24 hanno risultati esatti.

---

## 20. Migrazione incrementale

Sequenza §28 valutata. È **corretta e ben ordinata**. Raccomandazioni per fase:

| Fase | Dipendenze | File | Test | Rischio | Rilascio separato | Rollback | Completamento |
|---|---|---|---|---|---|---|---|
| 0 — qbq hardening | — | `fifo_lot_engine.py` (rimozione metodi), `test_fifo_lot_engine.py` | E24 + riscrittura test | **Basso** | ✅ | banale (revert) | metodi rimossi, test verdi |
| 1 — income D-1/broker/transit/orphan | 0 | `lots_analysis_service.py` (`_allocate_asset_income`) | E1,E3,E5–E11 | **Medio** (cambia risultati income) | ✅ ma **cambia output** | feature flag | D-1 + broker + orphan attivi |
| 2 — economic stage interno | 1 | `fifo_lot_engine.py` (nuovo stage), `FifoEngineResult` | E1–E11 riportati nel motore | **Alto** (C1: firma+result) | ⚠ | mantenere path service | stage obbligatorio, income nel motore |
| 3 — FEE/TAX matching+crossing | 2 | stage economico | E12–E21 | **Alto** | ✅ | disattivare tier | tutte le regole + crossing |
| 4 — FX, metriche nette, history | 3 | `lots_analysis_service.py`, `valuation_utils.py` | E22,E23,E26 | Medio | ✅ | campi netti opzionali | net P&L/return + history |
| 5 — DTO/API | 4 | `schemas/portfolio.py` + `./dev.py api sync` | contract test | Basso | ✅ | additivo | client rigenerato |
| 6 — frontend | 5 | frontend | E2E | Basso | ✅ | UI graceful | UI lordo/netto |
| 7 — riconciliazione | 2–4 | `portfolio_engine.py` (accumulatore pre-share) | E29,E30 | Medio (C4) | ✅ | — | invarianti verdi |

**Suddivisione consigliata:** la **Fase 1 va spezzata** in 1a (D-1) e 1b (broker-aware + transit + orphan), perché 1a da sola cambia i risultati income di ogni asset con BUY/SELL nel giorno di stacco — merita un rilascio isolato con benchmark di regressione. La **Fase 2** (C1: cambio firma) è la più rischiosa: isolare la migrazione del contratto `run()`/`FifoEngineResult` in un sotto-step 2a puramente meccanico (aggiunta campi con default, nessun cambio di comportamento), poi 2b (spostamento logica income).

---

## 21. Modifiche testuali consigliate a `hig-level-analysis-v3.md`

1. **§2.1/§24** — aggiungere regola contratto: campi economici sempre presenti con `default_factory`, `run()` valido anche con `economic_events` vuota, flag `economic_stage_completed`. (C1)
2. **§23.5/§24** — definire un terzo `calculation_status` (`FAILED`/`PARTIAL`) o basarlo sulla max severity; specificare il perimetro (per-lotto/broker) su cui le metriche nette diventano `None`. (C2)
3. **§26.1** — specificare che `b` è il **broker accreditante dell'evento** e che ogni `EconomicAllocation` conserva tale `broker_id` per il raggruppamento della riconciliazione. (C3)
4. **§26.2 / Fase 7** — nominare `portfolio_engine.py` e l'accumulatore `per_income_absolute` (pre-share) da introdurre. (C4)
5. **§13.3** — aggiungere tie-break adjacent-day (raccomandato: preferire `D-1` a `D+1` a parità di distanza, coerente con la titolarità D-1; oppure preferire il tier gerarchicamente superiore). (C5)
6. **§13.4/§14–17** — esplicitare il pooling multi-candidato: più SELL → unione closure; più BUY → unione OpeningValue; più income → pesi combinati a due livelli `Σ_k α_k·w_{i,k}`. (C6)
7. **§13.1** — documentare esplicitamente che una FEE su round-trip BUY+SELL stesso giorno è attribuita alla SELL senza issue (euristica deterministica). (C7)
8. **§16** — aggiungere che `LotClosure` è immutabile (`frozen`); l'attribuzione crossing avviene sugli accumulatori per-lotto, non mutando le closure.
9. **§7.2** — completare la giustificazione: i pesi pre/post-split coincidono perché lo split è un fattore uniforme; la scelta è indifferente all'allocazione.
10. **§23.3** — chiarire che AMBIGUOUS = allocazione eseguita ma euristica (nessuna perdita d'importo).
11. **§23 (nuova)** — valutare `ECONOMIC_EVENT_UNEXPECTED_SIGN` (WARNING) per FEE/TAX con segno inatteso (dati sporchi).
12. **Fase 2** — nota performance: costruire i mapping `(date,asset,broker)→candidati` e `(broker,giorno)→frammenti` una sola volta per esecuzione.

---

## 22. Decisioni di prodotto residue

1. **Rumore issue su dividendi cross-broker nel giorno di arrivo** (§9.3): accettare come segnale (posizione attuale) o introdurre una "arrival-day grace"? — *Raccomandazione: accettare, ma monitorare il tasso di issue sui dati reali.*
2. **FEE round-trip → SELL senza ambiguità** (C7): confermare la priorità deterministica `SELL>BUY` o segnalare come ambigua? — *Raccomandazione: deterministica + documentata.*
3. **Tie-break adjacent D-1 vs D+1** (C5): preferire D-1 (titolarità) o il tier superiore? — *Raccomandazione: D-1.*
4. **Perimetro `calculation_status` su conservazione fallita** (C2): fallire l'intero asset o solo il broker/lotto affetto? — *Raccomandazione: isolare al perimetro minimo.*
5. **Ripartizione multi-income di una TAX** (§8): per quantità o per importo lordo delle cedole? — *Raccomandazione: per importo (pesi combinati).*
6. **`COST_ALLOCATIONS` sempre disponibile o solo su richiesta** (§25): opt-in per dimensione response. — *Confermato opt-in.*

---

## 23. Componenti da mantenere / modificare / creare / deprecare

**Mantenere:**
- Ordinamento `_event_sort_key` (`fifo_lot_engine.py:468-471`).
- Matematica lorda `total_pnl`/`total_return` (`lots_analysis_service.py:1044,1047`).
- `compute_holding_value` (qbq-aware) come unico calcolo di valore.
- `LotClosure` frozen, `FifoLot`, `FragmentInterval` (nessuna estensione necessaria).
- Buckets `unalloc_income`/`unalloc_fees` del Portfolio Engine (`portfolio_engine.py:840,851`).

**Modificare:**
- `_allocate_asset_income`: D-1 + broker-aware (Fase 1) → poi spostare nel motore (Fase 2).
- `FifoLotEngine.run()`: firma con `economic_events` (Fase 2).
- `FifoEngineResult`: campi economici + `economic_stage_completed` + `calculation_status` a tre stati (Fase 2/3).
- `portfolio_engine.py`: accumulatore pre-share (Fase 7).
- `schemas/portfolio.py`: campi netti additivi + `CostAllocationSchema` (Fase 5).

**Creare:**
- `_FifoEconomicAllocationStage` (privato).
- `EconomicAllocation` / accumulatori per-lotto.
- Mapping pre-indicizzati per matching.
- Test `test_fifo_economic/fee/tax/transit/crossing/conservation/fx/qbq/reconciliation`.

**Deprecare/rimuovere:**
- `value_for_lot`, `aggregate_value`, `relative_return_for_lot` (`fifo_lot_engine.py:244-287`) — zero consumer produttivi.

---

## 24. Raccomandazione finale

**GO CON MODIFICHE.**

`hig-level-analysis-v3.md` è pronto a diventare la base del piano implementativo dopo aver applicato le 12 modifiche testuali di §21 (in particolare C1 e C2, strutturali). Il documento:
- recepisce integralmente le due review precedenti, inclusa la criticità bloccante v2 (riconciliazione), ora risolta;
- ha matematica lorda/netta verificata contro il codice e priva di doppio conteggio;
- richiede zero estensioni alle dataclass quantitative;
- adotta la rimozione qbq corretta e sicura;
- definisce una gerarchia FEE/TAX robusta con sole ambiguità documentabili (non bloccanti);
- propone una migrazione incrementale sana (con la sola raccomandazione di spezzare Fase 1 e Fase 2).

Le criticità residue sono **lacune di specifica**, non contraddizioni: risolvibili in fase di scrittura del piano senza ripensare l'architettura. La pipeline a due passate interne, il motore assoluto e il modello feed-forward sono la scelta corretta.

**Domande residue che richiedono decisione di prodotto:** le 6 di §22.
