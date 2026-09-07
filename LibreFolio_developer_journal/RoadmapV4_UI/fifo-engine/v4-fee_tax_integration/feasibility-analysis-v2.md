# Feasibility Analysis v2 — FIFO Engine v4, integrazione FEE/TAX

> Seconda review tecnica/matematica di
> [`high-level-analysis-v2.md`](./high-level-analysis-v2.md), confrontata con il codice reale e con la
> prima [`feasibility-analysis.md`](./feasibility-analysis.md).
> **Nessun codice/schema/test/documento è stato modificato.** Solo lettura + verifica algebrica.

---

## 0. Executive summary

**Giudizio complessivo: GO CON MODIFICHE.**

`high-level-analysis-v2.md` **recepisce quasi integralmente** la prima review: elimina EXPLICIT_LINK come
prerequisito, conserva l'ordine di replay `TRANSFER → SPLIT → BUY/SELL`, sposta l'economia in una seconda
passata dentro il dominio FIFO, lascia `original_cost` invariato, mantiene la semantica lorda di
`total_pnl`/`total_return` aggiungendo i campi netti in modo additivo, affronta il qbq **prima**
dell'estensione, alloca in valuta nativa e uniforma il fallback FEE/TAX alla regola D-1. Su questi punti il
documento è **corretto e implementabile senza toccare il modello DB delle transazioni**.

Restano però **cinque criticità reali** — quattro nuove, una ereditata — che il documento non risolve e che
condizionano la fattibilità:

1. **[BLOCCANTE — nuovo] La riconciliazione col Portfolio Engine (§19) è numericamente FALSA** quando un
   broker ha `share_percentage < 1`. Verificato nel codice: il Portfolio Engine scala income/fee per
   `ctxn.share` (`portfolio_engine.py:741, 748` → `per_income`/`per_fees_taxes` `:838, 849`), mentre il
   `LotsAnalysisService`/FIFO usa importi **assoluti** senza `share_percentage`
   (`lots_analysis_service.py:497-506, 940-941`). Le due viste non sono confrontabili direttamente. (§12)
2. **[ALTO — nuovo] "UnallocatedIncome/Fees" è un termine ambiguo** in §19: confonde due bucket distinti —
   income *asset-linked ma senza lotti eleggibili* (che il FIFO salterebbe) e income *senza asset_id* (che il
   Portfolio Engine tiene in `unalloc_income`/`unallocated_income`, `portfolio_engine.py:840, 851`). Solo il
   secondo esiste oggi come "unallocated". (§12)
3. **[ALTO — nuovo] Data Quality incompleta**: v2 definisce solo `ASSET_INCOME_NO_ELIGIBLE_LOTS` e
   `ASSET_COST_NO_ELIGIBLE_LOTS`. Mancano `FEE_TAX_ALLOCATION_AMBIGUOUS`, `FX_RATE_MISSING_FOR_ALLOCATION`,
   `ALLOCATION_CONSERVATION_FAILED`, tutti necessari data la gerarchia euristica e la doppia conservazione
   (nativa + post-FX). (§10)
4. **[MEDIO — nuovo] Residuo post-FX non gestito**: §17 impone la conservazione **solo** in valuta nativa.
   Convertendo ogni allocazione singolarmente, `Σ TargetAllocation` può divergere da `FXConvert(NativeTotal)`
   per arrotondamento. Il documento non definisce dove assorbire questo secondo residuo. (§8)
5. **[MEDIO — parz. ereditato] ADJACENT_DAY vale solo per income**: una FEE con settlement T+1 rispetto a
   una SELL cade su `OPEN_LOTS_FALLBACK` anziché sulla SELL. L'audit BRIM (v1 §9) mostra che lo sfasamento
   settlement esiste. Va deciso a livello prodotto se accettarlo. (§5)

Nessuna di queste è un NO-GO: sono **specifiche mancanti** e un **invariante da ridefinire**, non errori
strutturali. Con le correzioni testuali della §16 il piano è solido.

---

## 1. Recepimento della prima review (punto per punto)

| # | Conclusione v1 | Stato in v2 | Evidenza |
|---|---|---|---|
| 1 | EXPLICIT_LINK non prerequisito | **RECEPITO** | v2 §8.3: "Un eventuale collegamento esplicito potrà essere supportato in futuro, ma non costituisce prerequisito." La gerarchia parte da SAME_DAY_*. |
| 2 | Replay quantitativo non riordinato | **RECEPITO** | v2 §2.1: "Questa sequenza è già stabilizzata e non deve essere sostituita da un nuovo ordinamento globale." Coerente con `fifo_lot_engine.py:468-471`. |
| 3 | TRANSFER prima di SPLIT e BUY/SELL | **RECEPITO** | v2 §2.1/§4: `TRANSFER → SPLIT → BUY/SELL/ADJUSTMENT`. Nessuna fase 3 unificata (correzione del difetto v1 §2). |
| 4 | Economia in seconda passata | **RECEPITO** | v2 §4: "Passata 1 quantitativo / Passata 2 economico". |
| 5 | Dominio FIFO decide l'allocazione sui lotti | **RECEPITO** | v2 §4/§5: il motore determina lotti eleggibili, pesi, contesto, regola. |
| 6 | Service responsabile di I/O, FX, qbq, DTO | **RECEPITO** | v2 §4/§17: "Il service applica la conversione FX", valutazione qbq-aware nel service. |
| 7 | Importi allocati in valuta originaria | **RECEPITO** (con lacuna post-FX, §8) | v2 §3.2/§17: conservazione in valuta nativa prima dell'FX. |
| 8 | `original_cost` invariato | **RECEPITO** | v2 §3.3/§10/§14: "FEE e TAX non modificano original_cost." |
| 9 | FEE/TAX in accumulatori indipendenti | **RECEPITO** | v2 §14.1: `allocated_fees`, `allocated_taxes` separati. |
| 10 | `total_pnl`/`total_return` mantengono semantica lorda | **RECEPITO** | v2 §2.3/§18: i campi esistenti restano lordi. Verificato che l'attuale `total_pnl` è già il gross (`lots_analysis_service.py:1044`). |
| 11 | Campi netti additivi | **RECEPITO** | v2 §18: aggiunge `net_total_pnl`/`net_total_return` senza rinomina distruttiva. |
| 12 | qbq affrontato prima dell'estensione | **RECEPITO** | v2 §6/Fase 0: rimozione o firma qbq obbligatoria + test qbq=100. |

**Recepiti aggiuntivi (raccomandazioni v1 non nell'elenco richiesto):**
- Broker-scope income → **RECEPITO** (v2 §7.2, formula `CustodyCompatible`).
- Transfer durante income → **RECEPITO** (v2 §7.3).
- Uniformare fallback FEE/TAX a D-1 → **RECEPITO** (v2 §13: `OpenQuantity(D-1)`, coerente con income; risolve la incoerenza v1 §7.5).
- Crossing LONG/SHORT → **RECEPITO con formula esplicita** (v2 §11; v1 lo lasciava come domanda aperta D2).
- Segno FEE/TAX negativo → **NON RECEPITO ESPLICITAMENTE**: v2 tratta `Cost`/`CostTotal` come positivi ma non ricorda che `amount < 0` per validazione (`schemas/transactions.py:296`). Da esplicitare (uso di `abs`). (§5, §16)

**Conflitti nuovi introdotti:** vedi §12 (riconciliazione share-scaled) e §10 (Data Quality incompleta).

**Verdetto §1:** 12/12 punti obbligatori **RECEPITI**. Nessuna regressione rispetto alle indicazioni v1.
Le criticità residue sono **specifiche incomplete**, non ripudi delle conclusioni v1.

---

## 2. Architettura a due passate

### 2.1 L'output quantitativo attuale è sufficiente per la passata economica?

| Dato richiesto | Disponibile oggi? | Simbolo |
|---|---|---|
| lot_id / opening_transaction_id | ✅ | `FifoLot.lot_id (== opening_transaction_id)` (`fifo_lot_engine.py:153, 156, 830`) |
| opening date / broker / direction | ✅ | `FifoLot.opening_date/opening_broker_id/direction` (`:155-158`) |
| original quantity | ✅ | `FifoLot.original_quantity` (`:159`) |
| open quantity per data | ✅ (derivato) | `_open_quantity_on_date(fragments, D)` (`lots_analysis_service.py:1633-1634`) |
| custody fragments | ✅ | `FragmentInterval` (`:122-134`) |
| IN_TRANSIT source/destination | ✅ | `FragmentInterval.source_broker_id/destination_broker_id` (`:133-134`) |
| closures / closing tx id / closed qty | ✅ | `LotClosure.transaction_id/quantity/lot_id` (`:137-148`) |
| SELL multi-lotto | ✅ | closures multiple con stesso `transaction_id` |
| crossing LONG/SHORT | ✅ | closures con `close_reason=="BUY"` (`:480`) + lotto `lot_id==buy_tx` |
| split-adjusted quantities | ✅ | frammenti riscalati in `_apply_split` (`:666-690`) |
| transfer lineage | ✅ | `_PendingTransferPiece` + frammenti IN_TRANSIT/BROKER |

**Conclusione:** l'output quantitativo (`FifoEngineResult`, `:189-287`) contiene **tutto** ciò che serve
alla passata economica. **Nessuna estensione obbligatoria** di `FifoLot`, `LotClosure`, `FragmentInterval`
per i dati *quantitativi*.

### 2.2 Dati mancanti → dove vanno gli accumulatori economici

Gli accumulatori economici (`gross_income`, `allocated_fees`, `allocated_taxes` per lotto) **NON** vanno
aggiunti alle dataclass del motore:
- `LotClosure` è `frozen=True` (`:137`): non può ricevere `allocated_fee`. La quota fee attribuita a una
  closure va tracciata **fuori**, nella lista `CostAllocation` (per `lot_id`+`context=CLOSURE`).
- `FifoLot` è mutabile (`slots=True`, `:151`) ma mutarlo dalla passata economica accoppierebbe i due domini
  e romperebbe la purezza del replay quantitativo (rischio regressione sul core rilasciato).

→ **Serve un mapping ausiliario per lotto e per closure** mantenuto dall'allocatore economico
(`dict[lot_id → EconomicAccumulator]` + `list[CostAllocation]`), non nuovi campi sulle strutture del motore.
Nessun nuovo indice temporale: si riusa `_open_quantity_on_date`.

### 2.3 `replay_economic()` vs `FifoEconomicAllocator` — raccomandazione

| Criterio | `FifoLotEngine.replay_economic()` | **`FifoEconomicAllocator` (classe dedicata)** |
|---|---|---|
| Purezza | ⬇ mescola quantitativo ed economico nella stessa classe | ⬆ separa i due domini |
| Coesione | media | alta (single responsibility) |
| Testabilità | i test del motore diventano più grandi | ⬆ testabile in isolamento su un `FifoEngineResult` fittizio |
| Rischio regressione sul core | ⬆ ogni modifica tocca la classe rilasciata | ⬇ core intatto |
| Riuso risultati quantitativi | diretto (self) | diretto (riceve `FifoEngineResult`) |
| Estensione euristiche | scomodo | ⬆ isolato |
| Dipendenza FX/target | resta fuori (nativa) in entrambi | resta fuori in entrambi |

**Raccomandazione: `FifoEconomicAllocator`**, classe **interna al dominio FIFO** (stesso package), che
consuma un `FifoEngineResult` + la lista di `EconomicEvent` e produce `(economic_accumulators_by_lot,
cost_allocations, issues)` in **valuta nativa**. Il `run_fifo_lot_engine` esistente resta invariato; un nuovo
`run_fifo_economic_allocation(engine_result, economic_events)` orchestra la seconda passata. Questo massimizza
il riuso e azzera il rischio sul motore quantitativo già testato (`test_fifo_lot_engine.py`).

---

## 3. Semantica temporale dei proventi — matrice

Regola v2: `EligibleQuantity_i(D) = OpenQuantity_i(D−1)` = stato a fine giornata `D−1`.

**Verifica helper:** il codice **ha già** un helper affidabile: `_open_quantity_on_date(fragments, q)` con
`_fragment_active_on_date: start ≤ q < end` (half-open, `lots_analysis_service.py:1691-1692`). Chiamandolo
con `q = D − 1 giorno` si ottiene esattamente lo stato end-of-`D−1` = start-of-`D`. **Non serve un nuovo
helper temporale** per la quantità; serve **solo** cambiare l'argomento da `tx.date` (oggi, `:946`) a
`tx.date − 1`. ⚠️ Il documento §3 mette in guardia dal riuso implicito di `query_date = D`: corretto, oggi
`_allocate_asset_income` usa proprio `D` (end-of-`D`) → va cambiato.

| Scenario | Stato a D−1 | Eventi in D | Lotti eleggibili | Qty eleggibile | Risultato atteso | Conflitto |
|---|---|---|---|---|---|---|
| BUY in D | lotto assente | BUY apre lotto | lotto BUY **escluso** | 0 sul BUY | provento non tocca il BUY | ok |
| SELL in D | lotto aperto q | SELL riduce | lotto **incluso** con q di D−1 | q(D−1) | venduto partecipa | ok |
| BUY e SELL stesso lotto in D | q | BUY+SELL | dipende dal lotto sottostante D−1 | q(D−1) | coerente con D−1 | ok |
| transfer depart in D | q su From | depart | From: BROKER+IN_TRANSIT(source=From) a D−1 = **q su From** (transito non ancora partito) | q(D−1) | attribuito al From | ok |
| transfer arrive in D | q IN_TRANSIT (source From) | arrive | a D−1 il transito è ancora IN_TRANSIT(source=From) → eleggibile sul **From** | q(D−1) | provento del giorno-arrivo su From se accredito su From; su To = 0 | ⚠️ vedi §4 |
| split in D | q | split riscala | eleggibilità su q(D−1) **pre-split** | q(D−1) | dividendo per-quota pre-split | ⚠️ chiarire base quote |
| adjustment in D | q | ADJ_IN/OUT | q(D−1) (pre-adjustment) | q(D−1) | ok | ok |
| lotto chiuso in D | q | SELL totale | incluso (held a D−1) | q(D−1) | income su lotto che a fine D ha open=0 | ⚠️ accumulatore su lotto chiuso |
| lotto riaperto/biforcato in D | dipende | BUY/transfer | solo la parte esistente a D−1 | q(D−1) | ok | ok |

**Note di conflitto:**
- **Split same-day**: se il provento è su `D` e uno split avviene su `D`, la regola D−1 valuta la quantità
  **pre-split**. Se l'importo del dividendo è dichiarato per-quota **post-split**, servirebbe coerenza. Il
  documento non lo chiarisce → **domanda di prodotto** (di norma il dividendo è già in valore totale, quindi
  irrilevante ai pesi; ma va scritto). 
- **Lotto chiuso in D**: coerente col codice, che mantiene accumulatori sui lotti chiusi
  (`realized_pnl`/`cumulative_proceeds` non azzerati alla chiusura). L'allocatore economico deve fare lo
  stesso per `gross_income`/`allocated_*`.
- **Transfer arrive in D con accredito su To**: la regola D−1 dice "eleggibile sul From" perché a D−1 il
  transito non è arrivato. Ma se l'accredito è materialmente su **To** nel giorno di arrivo, `CustodyCompatible(To, D)`
  con qty D−1 dà **0** → income orfano → issue. Vedi §4 (ambiguità reale).

---

## 4. Scope broker e transito

Formula v2: `L_{a,b,D} = { L_i : direction=LONG, EligibleQty_i(D)>0, CustodyCompatible_i(b,D) }`.

**Helper mancante:** non esiste oggi un helper `CustodyCompatible_i(b, D)`. `_fragment_in_scope`
(`lots_analysis_service.py:1636-1639`) verifica l'appartenenza allo **scope di analisi** (`broker_id in scope`
oppure IN_TRANSIT con source **e** dest in scope), **non** la logica "From = BROKER(b) + IN_TRANSIT(source=b)".
→ **Serve un nuovo helper** che, per broker `b` e data `D`, consideri attivi a `D−1`:
- frammenti `BROKER` con `broker_id == b`;
- frammenti `IN_TRANSIT` con `source_broker_id == b` (accredito From);
- (per l'accredito To) frammenti `BROKER` con `broker_id == b` già arrivati.

I campi necessari esistono tutti su `FragmentInterval` (`:122-134`).

**Broker ordinario:** con il filtro sopra, un provento su `b` non tocca lotti custoditi su altri broker. ✅
(Corregge il bug asset-wide attuale, `lots_analysis_service.py:943` che itera su tutti i lotti.)

**Matrice transito** (eventi income durante transfer):

| Caso | From eleggibile | To eleggibile | Determinismo | Nota |
|---|---|---|---|---|
| transfer totale, income su From durante transito | BROKER(From)+IN_TRANSIT(source=From) = 100% | 0 | ✅ univoco | half-open evita overlap |
| transfer parziale | BROKER(From) residuo + IN_TRANSIT | frammenti già arrivati | ✅ | frazionamento FIFO in `_extract_transfer_pieces` (`:697-743`) |
| transfer multi-lotto | somma per lotto | — | ✅ | ogni pezzo conserva lot_id |
| transfer di ritorno (B→A) | logica simmetrica | — | ✅ | source/dest invertiti |
| catena A→B→C | il 2° transfer parte dal frammento BROKER su B | — | ⚠️ | vedi sotto |
| più transfer contemporanei | ogni pair con proprio IN_TRANSIT id | — | ✅ | fragment_id univoco per pair |
| date depart/arrive invertite | il motore ordina `start=min,end=max` (`:387-388`) | — | ✅ | normalizzato |
| depart e arrive stesso giorno | **nessun frammento IN_TRANSIT** (transferiti direttamente) | To=BROKER da subito | ⚠️ | `transfer_date < arrival_date` falso → no transito (`:718`) |
| income su From nel giorno di arrivo | a D−1 ancora IN_TRANSIT(source=From) → eleggibile su From | — | ✅ | coerente |
| income su To nel giorno di arrivo | qty a D−1 su To = 0 (arrivo è in D) → **0** | — | ⚠️ **ambiguità reale** |
| income su entrambi i broker stesso D | ripartizione indipendente per accredito | — | ✅ | somma = due eventi distinti |

**Ambiguità reali da segnalare (risultato non univoco / potenzialmente sorprendente):**
1. **Income su To nel giorno di arrivo**: con D−1 la qty su To è 0 → income orfano → issue, anche se
   economicamente l'utente ha "ricevuto" il titolo quel giorno. Il documento non copre questo incrocio
   D−1 × giorno-di-arrivo. **Decisione di prodotto**: accettare l'issue, o valutare il To con qty *end-of-D*
   in deroga alla regola D−1 (introdurrebbe però incoerenza con la titolarità dei proventi).
2. **Catena A→B→C con transiti sovrapposti**: se il secondo transfer B→C parte mentre il primo A→B non è
   ancora "arrivato" contabilmente, `CustodyCompatible(B,·)` a D−1 potrebbe non vedere ancora il frammento
   BROKER su B. Il motore quantitativo gestisce il lineage, ma la **regola economica** su chi è "From" in una
   catena non è definita da v2. **Da specificare.**
3. **depart==arrive (stesso giorno)**: nessun frammento IN_TRANSIT viene creato (`:718`), quindi la nozione
   "IN_TRANSIT source=From" non esiste per quel giorno; il titolo è già su To. La regola §7.3 assume
   l'esistenza del transito. **Da specificare** che nel caso same-day si applica la custodia effettiva.

**Compatibilità D−1 × half-open × ownership:** coerente nel caso standard (l'IN_TRANSIT ha `start=depart`,
`end=arrival`; a D−1 durante il transito è attivo e ha `source=From`). I casi 1-3 sopra sono i soli in cui
la regola testuale non determina un risultato univoco.

---

## 5. Allocazione FEE/TAX

Gerarchia v2: `SAME_DAY_SELL → SAME_DAY_BUY → SAME_DAY_INCOME → ADJACENT_DAY_INCOME → OPEN_LOTS_FALLBACK → NO_ELIGIBLE_LOTS`.

| Regola | Dati necessari | Disponibili? | Deterministica? | Rischio attribuzione errata |
|---|---|---|---|---|
| SAME_DAY_SELL | closures con `transaction_id` di SELL stesso D/asset/broker | ✅ (`LotClosure`) | ✅ (ordine per closure) | media: se coesistono più SELL |
| SAME_DAY_BUY | lotti `opening_date==D`, stesso asset/broker | ✅ (`FifoLot`) | ✅ | media: se BUY e SELL stesso D |
| SAME_DAY_INCOME | pesi income dello stesso D | ✅ (passata income) | ✅ | bassa |
| ADJACENT_DAY_INCOME | income in D−1/D+1 | ✅ | ⚠️ più candidati a stessa distanza | media |
| OPEN_LOTS_FALLBACK | `OpenQuantity(D−1)` LONG stesso asset/broker | ✅ | ✅ | alta se assorbe fee di trade sfasate |
| NO_ELIGIBLE_LOTS | — | ✅ | ✅ | — |

**Segno:** `Cost`/`CostTotal` devono usare `abs(amount)` perché FEE/TAX hanno `amount < 0`
(`schemas/transactions.py:296`). v2 non lo dichiara. **Correggere.**

**Scenari obbligatori — esito atteso:**
- BUY+FEE stesso D → 100% al lotto BUY (OpeningValue unico). ✅
- più BUY + una FEE → peso `OpeningValue_i` (§10). ✅
- SELL+FEE / SELL+TAX → peso `ClosedQuantity_i` sulle closure della SELL. ✅
- SELL multi-lotto → più closure stesso `transaction_id`; pesi ClosedQty. ✅
- più SELL stesso D → **AMBIGUO**: quale SELL? La gerarchia non distingue tra SELL diverse dello stesso
  giorno. Serve tie-break (es. prossimità `transaction_id`, o ripartizione su **tutte** le closure del
  giorno). **Da specificare** + issue `FEE_TAX_ALLOCATION_AMBIGUOUS`.
- BUY e SELL stesso D → SELL vince (priorità). Deterministico ma **non necessariamente corretto** (una fee di
  acquisto verrebbe attribuita alla vendita). Vedi sotto.
- DIVIDEND/INTEREST + TAX stesso D → riusa pesi income (§12). ✅
- SELL + INTEREST + TAX stesso D → TAX cade su SAME_DAY_SELL (priorità) prima di SAME_DAY_INCOME: la TAX su
  un provento (ritenuta) verrebbe attribuita alla SELL, non all'income. **Rischio di attribuzione
  intuitivamente errata.** Le ritenute su cedole sono un caso reale (audit BRIM: trading212/directa/degiro
  emettono TAX su dividendi). **Rivedere la priorità** (vedi raccomandazione).
- TAX in D−1 e INTEREST in D → ADJACENT_DAY_INCOME (TAX cerca income in D/D+1). ✅ se D+1 lookup previsto.
- INTEREST in D e TAX in D+1 → TAX in D+1 cerca income in D (D−1 rispetto a TAX). ✅
- costo generico asset-linked → OPEN_LOTS_FALLBACK. ✅
- asset completamente chiuso → nessun lotto D−1 → NO_ELIGIBLE_LOTS. ✅
- costo senza asset → ignorato dal FIFO (§8.2), resta in `unalloc_fees` del Portfolio Engine. ✅

**La priorità SELL > BUY > INCOME è sufficientemente robusta?** **No, non del tutto.** Due problemi:
1. **TAX su income mascherata da SELL** (scenario SELL+INTEREST+TAX): una ritenuta fiscale verrebbe attribuita
   alla SELL. Raccomando di **anteporre SAME_DAY_INCOME per il tipo TAX** quando esiste un income candidato
   nello stesso giorno (le ritenute sono quasi sempre legate a proventi), mantenendo SELL>BUY per il tipo FEE.
   Questo è un segnale **strutturale** (tipo contabile), non fiscale — resta compatibile col vincolo v2 di non
   introdurre classificazione fiscale.
2. **Più candidati dello stesso tier** (più SELL, o BUY+SELL con importi diversi): serve un tie-break
   documentato. Segnali ammessi come **euristiche opzionali** (non obbligatorie): prossimità `transaction_id`,
   rapporto TAX/importo-provento, e — solo come ultima spiaggia — token nella `description`. In assenza di
   tie-break univoco → allocazione ripartita su tutti i candidati del tier + issue `FEE_TAX_ALLOCATION_AMBIGUOUS`
   (WARNING, DEGRADED) per trasparenza.

**Auditabilità:** ogni regola registra `rule` in `CostAllocation` (§9). Aggiungere `candidate_count` per
distinguere allocazioni univoche da euristiche (vedi §9).

---

## 6. Crossing LONG/SHORT — verifica matematica

Formula v2: `q = q_c + q_o`, `Cost_close = Cost·q_c/q`, `Cost_open = Cost·q_o/q`.

**Conservazione:** `Cost_close + Cost_open = Cost·(q_c+q_o)/q = Cost·q/q = Cost`. ✅ Somma esatta.

**Disponibilità dati** (BUY che chiude SHORT e apre LONG, singola tx `t`):
- `q_c` = `Σ closure.quantity` con `transaction_id==t` e `close_reason=="BUY"` (`fifo_lot_engine.py:480, 800-813`). ✅
- `q_o` = `FifoLot.original_quantity` del lotto `lot_id==t` (aperto in `_apply_buy`, `:485-494`). ✅
- Simmetrico per SELL→SHORT: closure `close_reason=="SELL"` + lotto SHORT `lot_id==t` (`:511-520`).

**Dove va la quota:**
- `Cost_close` → ripartita sulle **closure** con peso `ClosedQuantity_i` → accumulata sui **lotti chiusi**
  (SHORT nel caso BUY→LONG), `context=CLOSURE`.
- `Cost_open` → 100% al **nuovo lotto** aperto (`lot_id==t`), `context=OPENING`.

**Coerenza con:**
- closure multiple / frammenti distribuiti → ripartizione interna per `ClosedQuantity`. ✅
- quantità decimali / arrotondamenti → residuo all'ultimo lotto in ordine stabile (come income, `:955-961`). ✅
- **short parzialmente coperto + successiva chiusura**: il lotto SHORT residuo può ricevere altre fee in date
  successive; gli accumulatori sono per-lotto cumulativi → nessun conflitto. ✅
- **gross/net P&L delle due direzioni**: attenzione — il lotto SHORT aperto ha
  `cumulative_proceeds = quantity·unit_price` impostato **all'apertura** (`:841`), e il suo `gross_pnl` usa
  `proceeds − open_value`. La fee `Cost_open` su un lotto SHORT riduce il **net** P&L short senza toccare
  `original_cost` (che per lo short è `quantity·unit_price`). Coerente col modello feed-forward, ma il
  denominatore `NetReturn = NetPnL/OriginalCost` per lo SHORT usa `OriginalCost = q·p` (il "costo" nozionale
  short). **Va esplicitato** che per lo SHORT il denominatore resta il costo nozionale d'apertura (nessuna
  novità: è già così nel gross).

**Strutture dati che ricevono la quota:** nessuna modifica alle dataclass del motore; le quote vanno negli
accumulatori economici per-lotto (`allocated_fees`/`allocated_taxes` keyed by `lot_id`) e nella lista
`CostAllocation` (con `context` OPENING/CLOSURE). Confermato che `LotClosure` è frozen → l'attribuzione a una
closure è tracciata via `CostAllocation`, non mutando la closure.

**Verdetto §6:** formula **corretta e implementabile con i dati esistenti**. Unico chiarimento richiesto: il
trattamento del denominatore netto per lo SHORT.

---

## 7. Modello feed-forward — verifica

Le formule v2 (§14) coincidono con quanto **già** implementato per il lordo
(`lots_analysis_service.py:1023-1050`), con l'aggiunta netta. Verifica scenario per scenario:

| Scenario | Gross | Net | Doppio conteggio? | Note |
|---|---|---|---|---|
| lotto aperto | `OpenValue − Cost` | `− fees − taxes` | no | fee opening riduce net |
| parz. chiuso | `OpenValue+Proceeds−Cost` | `− costi` | no | come test esistente (`:823-878`) |
| completamente chiuso | `Proceeds+Income−Cost` (OpenValue=0) | `− costi` | no | **accumulatori su lotto chiuso** (cristallizzati) |
| soli proventi | `Income` (+OpenValue) | `− costi` | no | income una sola volta (`:1044`) |
| estimated-at-cost | `market_pnl=0`, `Income` separato | `− costi` | no | income NON in open_value (`:1034-1041`) |
| fee di apertura | come "aperto" | `−fee` opening | no | context OPENING |
| fee di chiusura | come "chiuso" | `−fee` closure | no | context CLOSURE, su lotto ridotto |
| tax su income | income invariato | `−tax` income | no | riusa pesi income (§12) |
| più costi nel tempo | cumulativi | prefix-sum | no | serve prefix per history (come income, `:974-981`) |
| SHORT | `Proceeds−OpenValue` | `− costi` | no | denominatore nozionale (§6) |

**Controlli espliciti richiesti dal task:**
- **doppio conteggio**: assente — income e costi sono accumulatori separati, entrano una sola volta in
  gross/net (verificato §4 v1, formula `total_pnl` `:1044`).
- **costi persi dopo la chiusura**: rischio se gli accumulatori venissero azzerati alla chiusura. Il codice
  quantitativo NON azzera `realized_pnl`/`cumulative_proceeds` alla chiusura → l'allocatore economico deve
  seguire lo stesso pattern (accumulatori persistenti). **Da garantire con test (chiusura completa).**
- **history che termina prima di date_to**: gestito da `_lot_history_end_date(..., extend_closed=True)`
  (`:1352, 1428`); le net-history devono riusare lo stesso meccanismo per fee/tax prefix.
- **denominatore zero**: `GrossReturn/NetReturn` calcolati solo per `OriginalCost > 0` (v2 §14.6; codice
  `:1047, 1471`). ✅
- **segno FEE/TAX**: `abs()` (§5). ⚠️ da esplicitare.
- **quantità negative**: le FEE/TAX hanno `quantity==0` → non entrano nel replay quantitativo; nessun impatto
  su `OpenQuantity`.
- **estimated-at-cost**: income/fee non entrano in `open_value` → nessun doppio conteggio (`:1034-1041`). ✅

**Verdetto §7:** modello feed-forward **corretto**, coerente col codice, minimo rischio di doppio conteggio.

---

## 8. Valuta nativa e FX

v2 §17: allocazione nativa `NativeAllocation_{i,E} = NativeAmount_E · w_i`, poi FX per allocazione a
`Date_E`. Conservazione dichiarata **solo** in nativa (§3.2).

**Problema di conservazione post-FX:** convertendo ogni `NativeAllocation` singolarmente con arrotondamento,
`Σ_i FXConvert(NativeAllocation_i) ≠ FXConvert(Σ_i NativeAllocation_i)` in generale. v2 **non definisce** dove
assorbire questo residuo. Il codice attuale per l'income converte l'**intero importo** una volta
(`_converted_external_amount(tx.amount, …)`, `:941`) e **poi** ripartisce sui lotti (`:953-961`): così la
conservazione vale **in target currency**. La regola v2 (ripartire in nativa, poi convertire ogni quota)
**inverte** l'ordine e introduce il residuo post-FX.

**Analisi casi:**
- più lotti con pesi frazionari + FX con molti decimali → residuo post-FX inevitabile.
- eventi in valute diverse / cambio target currency / analisi ripetuta EUR e USD → l'approccio nativo è
  robusto (motore valuta-agnostico), ma il residuo va gestito **due volte** (nativa + target).
- mancanza del cambio alla data / fallback FX → serve issue dedicata (§10, `FX_RATE_MISSING_FOR_ALLOCATION`).
- lotto originato in valuta diversa dall'evento → nessun problema: la conversione è per-evento a `Date_E`.

**Raccomandazione (dove applicare il residuo):** **entrambe le fasi con riconciliazione separata**:
1. conservazione **nativa** con residuo all'ultimo lotto in ordine stabile (come v2 §3.2, come income oggi);
2. in target currency, **convertire il totale nativo una volta** (`FXConvert(NativeAmount_E)`) e ripartire su
   `w_i`, oppure convertire per-quota e assegnare il residuo post-FX all'ultimo lotto, verificando
   `Σ TargetAllocation == FXConvert(NativeTotal)` entro tolleranza; in caso contrario issue
   `ALLOCATION_CONSERVATION_FAILED`.

Preferibile la variante "converti il totale una volta e ripartisci" (allineata al codice income esistente),
che elimina il residuo post-FX per costruzione. **Documentare esplicitamente la policy.**

---

## 9. Audit trail

Modello v2: `CostAllocation(transactionId, lotId, date, type, context, rule, amount, currency)`.

**Campi aggiuntivi — valutazione (modello minimo sufficiente):**

| Campo | Necessario? | Motivazione |
|---|---|---|
| `source_transaction_id` | ✅ (= `transactionId`) | è la FEE/TAX/income di origine |
| `target_transaction_id` | ⭐ consigliato | la BUY/SELL/income cui è attribuita (risponde "in base a quale evento") |
| `closure_id` | ➖ opzionale | ricavabile da (lot_id, target_tx); evitare se ridondante |
| `broker_id` | ✅ | necessario per riconciliazione per-broker (§12) |
| `native_amount` + `native_currency` | ✅ | conservazione nativa auditabile |
| `target_amount` + `target_currency` | ✅ | valore mostrato all'utente |
| `weight` | ⭐ consigliato | risponde "con quale peso"; evita di ricalcolarlo |
| `candidate_count` | ⭐ consigliato | distingue allocazione univoca da euristica ambigua |
| `confidence` | ➖ opzionale | derivabile da `rule`+`candidate_count`; evitare campo separato |
| `description` | ➖ opzionale | già sulla transazione; non duplicare, referenziare via `source_transaction_id` |

**Modello minimo raccomandato:**
```
CostAllocation(
  source_transaction_id, target_transaction_id, lot_id, broker_id, date,
  type ∈ {FEE,TAX} (o INCOME per i proventi),
  context ∈ {OPENING, CLOSURE, INCOME, HOLDING},
  rule ∈ {SAME_DAY_SELL, SAME_DAY_BUY, SAME_DAY_INCOME, ADJACENT_DAY_INCOME, OPEN_LOTS_FALLBACK},
  weight, candidate_count,
  native_amount, native_currency, target_amount, target_currency
)
```
Risponde a tutte le domande richieste (quale costo / a quale lotto / quantità / peso / evento / euristica /
valuta) senza campi ridondanti (`closure_id`, `confidence`, `description` esclusi).

**Nota:** `type` dovrebbe includere anche l'income se si vuole un audit unico income+costi; altrimenti tenere
due liste (income allocations già esistono di fatto come `income_events_payload`, `:964-973`).

---

## 10. Data Quality

v2 definisce solo `ASSET_INCOME_NO_ELIGIBLE_LOTS` e `ASSET_COST_NO_ELIGIBLE_LOTS`. **Mancano tre issue.**

| Issue | Severity | calc_status | Parametri | Messaggio (distingue) | Effetto metriche | Continua DEGRADED? |
|---|---|---|---|---|---|---|
| `ASSET_INCOME_NO_ELIGIBLE_LOTS` (v2) | WARNING | DEGRADED | tx_id, asset, broker, date, amount, ccy | **probabile errore di inserimento** (data/broker/asset incoerenti) | income non allocato ai lotti | sì |
| `ASSET_COST_NO_ELIGIBLE_LOTS` (v2) | WARNING | DEGRADED | idem + type FEE/TAX | **importo non allocato** | costo non nel net dei lotti | sì |
| `FEE_TAX_ALLOCATION_AMBIGUOUS` **(mancante)** | INFO/WARNING | DEGRADED | tx_id, candidate_count, rule, candidati | **allocazione euristica** (più target plausibili) | net ripartito euristicamente | sì |
| `FX_RATE_MISSING_FOR_ALLOCATION` **(mancante)** | WARNING | DEGRADED | tx_id, ccy, target_ccy, date | **dato finanziario non disponibile** (cambio mancante) | target allocation non calcolabile | sì (mostra nativa) |
| `ALLOCATION_CONSERVATION_FAILED` **(mancante)** | ERROR | DEGRADED/UNAVAILABLE | event_id, expected, got, delta | **errore interno di conservazione** | metriche inaffidabili | no se oltre tolleranza |

Le prime due esistono come pattern (`FifoDataQualityIssue`, `fifo_lot_engine.py:111-119`; mapping
`_message_key_for_issue`, `lots_analysis_service.py:1695+`). Le tre mancanti vanno aggiunte con relative i18n
key. Il messaggio deve **distinguere** esplicitamente i quattro casi richiesti dal task: probabile errore di
inserimento / allocazione euristica / importo non allocato / dato finanziario non disponibile.

**Verdetto §10:** v2 **incompleta**. Aggiungere le tre issue mancanti come prerequisito della Fase 2.

---

## 11. Hardening qbq

v2 §6 descrive correttamente il problema (metodi `value_for_lot`/`aggregate_value`/`relative_return_for_lot`
non qbq-aware, senza consumer produttivi) e propone rimozione **oppure** firma qbq obbligatoria, con test
qbq=100. **Sufficiente come descrizione.**

**Raccomandazione netta:** **rimuovere** i tre metodi. Verificato (v1 §5) che sono usati **solo** in
`test_fifo_lot_engine.py`, zero consumer di produzione (il service usa `compute_holding_value`,
`valuation_utils.py:19-26`). La rimozione:
- azzera il rischio di riuso errato ×100 **prima** di aggiungere la passata economica;
- riduce la superficie del motore;
- impatto test **contenuto**: vanno aggiornati/rimossi i soli test che li esercitano in
  `test_fifo_lot_engine.py` (446 righe totali). Se quei test coprono invarianti utili (P&L per lotto), vanno
  riscritti usando `compute_holding_value` o helper locali di test.

**Test anti-regressione permanenti (Fase 0):**

| # | Verifica | qbq=1 | qbq=100 (bond 1000 nom., quote 98.50) |
|---|---|---|---|
| T1 | opening unit price | invariato | 0.985 per unità |
| T2 | market quote → open value | `qty·price` | `(1000/100)·98.50 = 985` |
| T3 | P&L lordo | ok | usa 985, non 98 500 |
| T4 | P&L netto (con fee) | gross−fee | idem su base 985 |
| T5 | fee/tax allocation | invariante | invariante (unità nominali) |
| T6 | relative return | `price/ref−1` | confronto su `OpeningUnitPrice·qbq` |

---

## 12. Riconciliazione col Portfolio Engine — **criticità bloccante**

v2 §19 propone: `Σ GrossIncome_i + UnallocatedIncome = PortfolioIncome` (e analoghe per fees/taxes).

**Verifica nel codice → l'invariante NON è direttamente valido.**

1. **Share scaling.** Il Portfolio Engine scala ogni importo per `ctxn.share = broker.share_percentage`:
   - `amount_target = amount_target * ctxn.share` (`portfolio_engine.py:748`),
   - `per_income[(asset,broker)] += amount_target` (`:838`), `per_fees_taxes` (`:849`).
   - `broker_shares` da `BrokerUserAccess.share_percentage` (`:1805`).
   Il `LotsAnalysisService`/FIFO usa importi **assoluti** (100%): `_allocate_asset_income` prende
   `tx.amount` senza alcuno `share` (`:940-941`), e `_load_transactions` non legge `share_percentage`
   (`:497-506`). → Con qualunque broker a `share < 1`, `Σ GrossIncome_i (assoluto) ≠ PortfolioIncome (scalato)`.

2. **Ambiguità di "Unallocated".** In v2 il termine è unico, ma nel codice esistono **due** bucket diversi:
   - income **senza asset_id** → `unalloc_income[broker]` / DTO `unallocated_income` (`:840`, `schemas/portfolio.py:325`);
   - income **asset-linked ma senza lotti eleggibili** → oggi semplicemente **saltato** dal FIFO (`:950-951`),
     e comunque **contato** dal Portfolio Engine in `per_income` (perché ha asset_id).
   Il FIFO non ha, oggi, un accumulatore per il secondo caso. L'invariante richiede di **introdurlo**
   (l'income orfano asset-linked va tracciato come "unallocated a livello lotto" ma resta dentro `per_income`).

3. **Perimetro.** Il confronto va definito su: **asset × broker × date-range × user**, in **valuta target**,
   **prima** dello share scaling. Le due viste hanno scope diversi:
   - FIFO/Lots: user-scoped per accesso broker, **assoluto** (no share), no transazioni cash senza asset.
   - Portfolio: user-scoped, **share-weighted**, include cash senza asset.

**Raccomandazione — due invarianti distinti:**
- **(A) Riconciliazione assoluta per (asset, broker)**: confrontare `Σ_lot GrossIncome_i + OrphanIncome_{asset,broker}`
  (FIFO, assoluto) con il `per_income` **pre-share** del Portfolio Engine. Richiede di esporre nel Portfolio
  Engine un accumulatore income/fee **non scalato** (o di dividere per lo share del broker, possibile solo
  **prima** dell'aggregazione tra broker con share diversi).
- **(B) Riconciliazione user-scoped (share-weighted)**: `Σ_lot GrossIncome_i · share_broker(i) + Unallocated·share
  = PortfolioIncome`. Richiede che il FIFO conosca lo `share` per broker del lotto — informazione oggi **non**
  caricata dal `LotsAnalysisService`.

**Conclusione §12:** l'invariante di v2 §19, così com'è scritto, è **falso** con share < 1 e **impreciso** su
"Unallocated". Va **riscritto** distinguendo (A) assoluto per-broker e (B) user-scoped, e va deciso a livello
prodotto **quale vista è la fonte di verità** per il P&L netto per-lotto (probabilmente l'assoluto, essendo la
vista Lots per-lotto indipendente dallo share di comproprietà). **Questa è la modifica testuale più importante
da apportare al documento.**

---

## 13. Contratto DTO

v2 §18: aggiunta additiva `allocated_fees`, `allocated_taxes`, `net_total_pnl`, `net_total_return`,
`cost_allocations[]`. Verifica:

- **Tipi**: `SafeDecimal` (`schemas/common.py:50`) e `Currency` (`:106`) disponibili; `LotSummarySchema` usa
  già `SafeDecimal` (`schemas/portfolio.py:526-545`). ✅
- **`extra="forbid"`**: `LotSummarySchema` (`:516`), `LotValueHistoryPoint` (`:613`), `LotReturnHistoryPoint`
  (`:628`) sono tutti chiusi → i campi netti sono **breaking** per il client generato finché non si rigenera.
  Dopo l'aggiunta serve `./dev.py api sync`. ✅ (additivo, non distruttivo).
- **Target currency**: i campi netti seguono la stessa `target_currency` dei lordi. ✅
- **History lorde/nette**: `LotValueHistoryPoint`/`LotReturnHistoryPoint` hanno già `income` (`:622, 638`);
  vanno aggiunti `allocated_fees`/`allocated_taxes`/`net_pnl`/`net_total_return` (prefix-sum come `income`).
- **`cost_allocations[]` come analysis opzionale**: **consigliato**. La response può crescere molto (una riga
  per allocazione). Renderla una `LotAnalysisType` opzionale (come `INCOME_EVENTS`, già opzionale,
  `:293`) evita di gonfiare la response di default. ✅
- **Naming**: coerente con l'esistente (`asset_income`, `total_pnl`, `market_pnl`). Non serve rinomina
  distruttiva (v2 lo esclude correttamente). Unica nota: `total_pnl` resta "gross" ma il nome non lo dice; la
  descrizione del campo (`:542`) va aggiornata per chiarire "gross".

**Verdetto §13:** estensione DTO **fattibile e additiva**. Rendere `cost_allocations` un'analysis opzionale.

---

## 14. Matrice di test

Esempi numerici esatti per gli scenari critici. Prezzo/qbq indicati dove rilevante. Package suggerito:
`test_lots_analysis_service.py` (integrazione) o `test_fifo_lot_engine.py`/nuovo
`test_fifo_economic_allocator.py` (unit).

| ID | Scenario | Input / stato iniziale | Eventi in D | Allocazioni attese | Metriche lorde | Metriche nette | Issue | Test file |
|---|---|---|---|---|---|---|---|---|
| E1 | income D-1 | BUY 10@100 (D0) | DIV 50 (D1) | tutto al lotto | income=50, total_pnl=50 (no prezzo→0 market) | = gross | — | lots_analysis |
| E2 | income same-day BUY escluso | BUY 10@100 (D1) | DIV 50 (D1) | **nessun lotto** (D-1 vuoto) | — | — | ASSET_INCOME_NO_ELIGIBLE_LOTS | lots_analysis |
| E3 | income same-day SELL incluso | BUY 10@100 (D0) | SELL 4 (D1)+DIV 50 (D1) | 100% al lotto (q D-1=10) | income=50 | =gross | — | lots_analysis |
| E4 | scope broker | Directa 30, IBKR 70 | DIV 100 su Directa | Directa lotti=100, IBKR=0 | — | — | — | lots_analysis |
| E5 | transfer From durante transito | lotto 100, transfer 60 in corso | DIV su From | 100 eleggibile (40+60 transit) | — | — | — | lots_analysis |
| E6 | transfer To durante transito | idem | DIV su To | 0 → orfano | — | — | ASSET_INCOME_NO_ELIGIBLE_LOTS | lots_analysis |
| E7 | income senza lotti | nessun LONG | DIV 50 | non allocato | — | — | ASSET_INCOME_NO_ELIGIBLE_LOTS | lots_analysis |
| E8 | BUY+FEE | — | BUY 10@100, FEE −5 | 100% opening | gross invariato | net=gross−5 | — | allocator |
| E9 | più BUY + FEE | — | BUY 10@100, BUY 30@100, FEE −8 | 2/8 e 6/8 (OpeningValue 1000/3000) → 2 e 6 | — | net−8 | — | allocator |
| E10 | SELL+FEE | BUY 10@100 | SELL 4@120, FEE −4 | closure(4) 100% | realized=80 | net−4 | — | allocator |
| E11 | SELL+TAX | BUY 10@100 | SELL 4@120, TAX −6 | closure(4) | — | net−6 | — | allocator |
| E12 | SELL multi-lotto | BUY 4@100, BUY 6@100 | SELL 8@120, FEE −10 | 4/8 e 4/8 (ClosedQty) → 5 e 5 | — | net−10 | — | allocator |
| E13 | BUY/SELL same-day | BUY 5@100, SELL 3@120 (stesso D) | FEE −6 | **SELL vince** (priorità) → closure(3) | — | net−6 | FEE_TAX_ALLOCATION_AMBIGUOUS? | allocator |
| E14 | crossing BUY SHORT→LONG | SHORT 4@100 | BUY 10@110, FEE −10 | q_c=4,q_o=6,q=10 → close 4, open 6 | — | close −4, open −6 | — | allocator |
| E15 | income + TAX | BUY 10@100 (D0) | DIV 50 (D1), TAX −5 (D1) | TAX riusa pesi income | income=50 | net−5 | — | allocator |
| E16 | adjacent-day income | BUY 10@100 (D0) | INTEREST 40 (D1), TAX −4 (D2) | TAX→income D1 (ADJACENT) | income=40 | net−4 | — | allocator |
| E17 | fallback open lots | BUY 10@100 (D0) | FEE −3 (D5, no trade/income) | OpenQty(D4) 100% | — | net−3 | — | allocator |
| E18 | nessun target | asset chiuso | FEE −3 | non allocato | — | — | ASSET_COST_NO_ELIGIBLE_LOTS | allocator |
| E19 | conservazione | 3 lotti frazionari | FEE −10 | Σ=−10 (residuo ultimo) | — | Σnet coerente | — | allocator |
| E20 | FX | tx USD, target EUR | DIV 100 USD @1.1 | nativa 100, target 110 | — | — | — | lots_analysis |
| E21 | FX mancante | tx USD, no rate | DIV 100 USD | nativa 100, target n/d | — | — | FX_RATE_MISSING_FOR_ALLOCATION | lots_analysis |
| E22 | qbq=100 | bond 1000 nom | prezzo 98.50 | — | open_value=985 | net su 985 | — | fifo/lots |
| E23 | estimated-at-cost | BUY 10@100, no prezzo | DIV 50, FEE −5 | market_pnl=0 | income=50 | net−5, no doppio income | — | lots_analysis |
| E24 | chiusura completa | BUY 10@100 | SELL 10@120, FEE −5 | closure(10), accumulatori cristallizzati | realized=200 | net−5 | — | allocator |
| E25 | riconciliazione absolute | 1 broker share=1 | DIV 100 | Σlot=100 | — | = per_income | — | test_portfolio_engine + lots |
| E26 | riconciliazione share<1 | broker share=0.5 | DIV 100 | Σlot=100 (assoluto), per_income=50 | **due invarianti** | — | test_portfolio_engine + lots |

**Esempio numerico esatto E9 (più BUY + FEE):** OpeningValue A=1000, B=3000; FEE=8 →
`w_A=1000/4000=0.25`, `w_B=0.75` → `alloc_A=2`, `alloc_B=6`, Σ=8. ✅
**E14 (crossing):** q_c=4, q_o=6, q=10, Cost=10 → close=4, open=6, Σ=10. ✅

---

## 15. Piano di migrazione

La sequenza v2 (§21) è **corretta**. Precisazioni per fase:

| Fase | Contenuto | Dipendenze | File interessati | Test | Rilascio incrementale | Retrocompat |
|---|---|---|---|---|---|---|
| 0 | Hardening qbq | nessuna | `fifo_lot_engine.py`, `test_fifo_lot_engine.py` | T1-T6 (§11) | ✅ indipendente | ✅ (rimozione test-only) |
| 1 | Income D-1 + broker + transit | Fase 0 | `lots_analysis_service.py` (`_allocate_asset_income`, nuovo `CustodyCompatible`), issue income | E1-E7, riconciliazione | ✅ | ⚠️ cambia numeri same-day (nessun test rotto: quelli esistenti sono non-same-day, `:823`) |
| 2 | `FifoEconomicAllocator` + audit trail | Fase 1 | nuovo `fifo_economic_allocator.py`, `EconomicEvent`, `CostAllocation`, 3 issue mancanti | E8-E19 | ✅ (dietro flag) | ✅ additivo |
| 3 | Metriche/history nette | Fase 2 | `schemas/portfolio.py` (+campi), `lots_analysis_service.py` (net summary/history), `./dev.py api sync` | E20-E24 | ✅ | ✅ additivo DTO |
| 4 | DTO/frontend | Fase 3 | frontend (fuori scope backend) | E2E | ✅ | ✅ |
| 5 (nuova) | Riconciliazione Portfolio/FIFO | Fase 3 | `portfolio_engine.py` (accumulatore pre-share), test riconciliazione | E25-E26 | ✅ | ⚠️ richiede definizione invariante (§12) |
| 6 (nuova) | Benchmark/perf | tutte | — | perf | ✅ | ✅ |

**Correzione al piano v2:** la §21 fonde "riconciliazione" dentro Fase 1/testing. Data la criticità §12, la
riconciliazione merita una **fase dedicata (5)** con la decisione di prodotto sull'invariante e l'eventuale
accumulatore pre-share nel Portfolio Engine. Nessuna migrazione DB richiesta in alcuna fase (confermato:
FEE/TAX/income sono tipi esistenti; `related_transaction_id`/`asset_event_id` invariati; solo schema DTO/API).

---

## 16. Modifiche testuali consigliate a `high-level-analysis-v2.md`

1. **§19 (riconciliazione)** — riscrivere l'invariante distinguendo **(A) assoluto per (asset, broker)** e
   **(B) user-scoped share-weighted**, chiarendo che il Portfolio Engine scala per `share_percentage`
   (`portfolio_engine.py:748`) mentre il FIFO è assoluto. Definire quale vista è la fonte di verità netta.
2. **§19** — disambiguare "UnallocatedIncome/Fees": separare *income orfano asset-linked* (nuovo accumulatore
   FIFO) da *income senza asset_id* (`unalloc_income` esistente).
3. **§10/§13.1 → aggiungere §Data Quality** con `FEE_TAX_ALLOCATION_AMBIGUOUS`,
   `FX_RATE_MISSING_FOR_ALLOCATION`, `ALLOCATION_CONSERVATION_FAILED`.
4. **§17 (FX)** — definire la policy sul **residuo post-FX**: convertire il totale nativo una volta e
   ripartire (raccomandato), oppure per-quota con residuo all'ultimo lotto + verifica di conservazione target.
5. **§8/§14 (segno)** — esplicitare che FEE/TAX hanno `amount < 0` e che l'allocatore usa `abs()`.
6. **§8.3 (priorità)** — per il tipo **TAX**, anteporre `SAME_DAY_INCOME` quando esiste un income candidato
   nello stesso giorno (ritenute su cedole), mantenendo SELL>BUY per FEE. Definire un tie-break per più
   candidati dello stesso tier + emissione `FEE_TAX_ALLOCATION_AMBIGUOUS`.
7. **§7.3 (transfer)** — coprire i tre casi non univoci: income su **To nel giorno di arrivo**, **catena
   A→B→C**, **depart==arrive same-day** (usa custodia effettiva).
8. **§11 (crossing SHORT)** — chiarire che per lo SHORT il denominatore `NetReturn` resta il costo nozionale
   d'apertura.
9. **§7.1 (split same-day)** — precisare che i pesi income usano la quantità **pre-split** (l'importo income è
   totale, quindi i pesi non cambiano il risultato, ma va scritto).
10. **§6/§18** — la rimozione dei metodi non-qbq-aware è **raccomandata** (non solo "oppure firma"), e la
    descrizione DTO di `total_pnl`/`total_return` va aggiornata a "gross".

---

## 17. Decisioni di prodotto residue

- **D1 — Fonte di verità netta**: la vista Lots per-lotto (assoluta) o il Portfolio Engine (share-weighted)?
  Determina quale invariante di riconciliazione è vincolante (§12).
- **D2 — Income su To nel giorno di arrivo**: emettere issue (coerenza D-1) o valutare To a end-of-D in deroga?
- **D3 — Priorità TAX su income vs SELL** nello stesso giorno: anteporre income per le ritenute? (§5)
- **D4 — Più SELL/candidati stesso tier**: tie-break (transaction_id prossimo? ripartizione su tutte le
  closure?) e se emettere `FEE_TAX_ALLOCATION_AMBIGUOUS`.
- **D5 — ADJACENT_DAY solo income**: accettare che fee di trade con settlement T+1 cadano su fallback? (§5)
- **D6 — Policy residuo FX**: nativa+target con riconciliazione, o conversione del totale una volta? (§8)
- **D7 — `cost_allocations` come analysis opzionale** di default off? (§13)

---

## 18. Giudizio finale

### GO CON MODIFICHE

`high-level-analysis-v2.md` è un **netto miglioramento** rispetto alla v1 del piano: recepisce tutte le
conclusioni della prima feasibility, corregge l'ordine di replay, isola la seconda passata, mantiene la
matematica lorda già corretta e aggiunge il netto in modo additivo, tutto **senza toccare il modello DB delle
transazioni** e **preservando il motore quantitativo** esistente. Le formule di crossing e feed-forward sono
matematicamente corrette e implementabili con i dati già prodotti dal motore.

Le **condizioni** per il GO sono le dieci modifiche testuali della §16, di cui **una bloccante**: la
riconciliazione col Portfolio Engine (§12) va ridefinita perché, con `share_percentage < 1`, l'invariante
scritto è numericamente falso (FIFO assoluto vs Portfolio share-scaled). Le altre criticità (Data Quality
incompleta, residuo post-FX, priorità TAX/income, casi transito non univoci, segno FEE/TAX) sono **specifiche
mancanti** risolvibili senza cambiare l'architettura.

**Non ci sono ostacoli strutturali al NO-GO.** Con le correzioni indicate, il piano è pronto per la Fase 0
(hardening qbq) e la Fase 1 (income D-1/broker/transit), entrambe rilasciabili incrementalmente.

---

### Appendice — citazioni chiave (verifiche v2)

- Portfolio Engine scala per share: `portfolio_engine.py:741, 746-748`; accumulatori `:838, 849`; shares `:1805`.
- FIFO/Lots assoluto (no share): `lots_analysis_service.py:497-506, 940-941`.
- Bucket "unallocated": `portfolio_engine.py:840, 851`; DTO `schemas/portfolio.py:325-326`.
- Income orfano saltato oggi: `lots_analysis_service.py:950-951`.
- Helper quantità D-1 riusabile: `lots_analysis_service.py:1633-1634, 1691-1692`.
- Custody scope helper esistente (insufficiente): `lots_analysis_service.py:1636-1639`.
- Crossing: closures `close_reason=="BUY"` `fifo_lot_engine.py:480, 800-813`; lotto aperto `:485-494`; SHORT proceeds all'apertura `:841`.
- Output quantitativo completo: `FifoEngineResult` `fifo_lot_engine.py:189-287`; `LotClosure` frozen `:137`.
- Formule lorde già = piano: `lots_analysis_service.py:1023-1050` (total_pnl `:1044`).
- History extend closed: `lots_analysis_service.py:1352, 1428`.
- qbq: `compute_holding_value` `valuation_utils.py:19-26`; metodi non-qbq test-only `fifo_lot_engine.py:244-287`.
- DTO chiusi additivi: `schemas/portfolio.py:516, 613, 628`; income history `:622, 638`.
- Segno FEE/TAX negativo: `schemas/transactions.py:296`.
- Ordine replay stabilizzato: `fifo_lot_engine.py:468-471`.
