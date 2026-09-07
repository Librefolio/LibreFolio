# Feasibility Analysis v4 — Review conclusiva

**Documento analizzato:** `feasibility-analysis-v4.md` (1300 righe) — nonostante il nome, è il **disegno di alto livello v4** (non una feasibility).
**Focus:** solo le decisioni **nuove** della v4 e i loro effetti combinati. Non ripeto le analisi già svolte in v1/v2/v3 se non dove la v4 le altera.
**Metodo:** verifica contro il codice reale (`fifo_lot_engine.py`, `lots_analysis_service.py`, `portfolio_engine.py`, `schemas/portfolio.py`).
**Vincolo:** nessuna modifica a codice/schemi/test/documenti.

---

## 0. Executive summary

**Giudizio: GO CON MODIFICHE.**

La v4 chiude quasi tutte le criticità aperte in v3: riconciliazione con broker **accreditante** dell'evento (§30), accumulatori pre-share nel Portfolio Engine (§31), stato a tre valori + `net_metrics_status` (§27), rimozione dei metodi non qbq-aware (§8), migrazione atomica senza legacy (§5). Le nuove policy di **pooling giornaliero** e la **soppressione del ramo D+1** rendono il modello di matching **univoco e deterministico** — un progresso reale rispetto ai tie-break ambigui della v3.

Restano però **due criticità strutturali** (non bloccanti ma da risolvere prima del piano) e alcune imprecisioni matematiche/testuali:

| # | Severità | Criticità | §doc |
|---|----------|-----------|------|
| C1 | **ALTO (struttura audit)** | `EconomicAllocationGroup` ha **un solo `context`** per gruppo e **una sola `EconomicLotAllocation` per lotto**. Un pool misto BUY+SELL (§17.4) e un crossing (§20) producono per lo **stesso lotto** una quota `OPENING` e una `CLOSURE`: la struttura le collassa e perde la distinzione. | §26.1-26.2 |
| C2 | **ALTO (bond ×100)** | §17.1 `TradeValue_k = |Quantity_k·ExecutionPrice_k|` è ambiguo. Dal codice `unit_price = |amount|/|quantity|` (per unità singola) ⇒ la formula è corretta **solo** se `ExecutionPrice` è quel valore; con una *quote* per-qbq sarebbe ×100 sui bond. Va riscritta come `TradeValue_k = |amount_k|`. | §17.1 |
| C3 | **MEDIO** | Pool FEE/TAX misto-valuta sui trade: `β_k` è ben definito solo se i trade condividono la valuta. Con trade same-day in valute diverse la somma dei `TradeValue` è incoerente. Serve normalizzazione a una valuta nativa comune (asset currency), non target. | §17.1, §25.1 |
| C4 | **MEDIO** | `calculation_status` è oggi una **property binaria** `COMPLETE/DEGRADED` (`fifo_lot_engine.py:198-200`); il DTO è `Literal["COMPLETE","DEGRADED","UNAVAILABLE"]` (`schemas/portfolio.py:455`). `FAILED` + `net_metrics_status` richiedono estendere entrambi e rendere il campo severity-aware. | §27 |
| C5 | **BASSO (testuale)** | §15.1 definisce la chiave del pool **senza `currency`**; §25.1 la aggiunge. Contraddizione interna da correggere. | §15.1 vs §25.1 |
| C6 | **BASSO** | `ADJUSTMENT_IN/OUT` hanno `unit_price=0` (`fifo_lot_engine.py:429,431`) ⇒ `TradeValue=0`; il pool trade li ignorerebbe. Non documentato se gli adjustment partecipino o no al pool FEE. | §17 |
| C7 | **BASSO (prodotto)** | §17.4 somma due FEE non collegate (una da BUY, una da SELL) e le redistribuisce per controvalore, **senza warning** (policy ufficiale). Conservativo ma euristico: la mono-attribuzione reale è persa. | §17.4, §3 prompt |

**Verifiche positive nuove confermate:** pooling conservativo (`Σ = PoolTotal`); previous-day-only elimina i tie-break; broker-key di riconciliazione corretta; pre-share accumulator collocato in `portfolio_engine.py`; crossing invariante `Cost_close+Cost_open=CostTrade` ancora valido; migrazione atomica **fattibile** nel working tree (un solo entrypoint interno, nessun consumer esterno del vecchio percorso oltre `LotsAnalysisService`).

---

## 1. Verifica delle decisioni vincolanti (1.1–1.11)

| Decisione | Stato | Nota di verifica |
|---|---|---|
| 1.1 Un solo motore pubblico | **Coerente** | `FifoLotEngine.run()` (`fifo_lot_engine.py:343`) è già l'unico entrypoint; oggi non prende argomenti. §5 impone firma nuova con eventi economici. |
| 1.2 Migrazione atomica | **Fattibile** | Unico consumer del motore + income allocator è `LotsAnalysisService`; nessun altro call-site esterno (vedi §2). |
| 1.3 D-1 senza eccezioni | **Coerente** | Inverte il comportamento attuale (`_allocate_asset_income` usa `tx.date`, `:940-946`). Nessuna arrival-day grace: To in giorno di arrivo → orphan (§11.3). |
| 1.4 Transfer in corso | **Coerente** | `FragmentInterval.source_broker_id` (`:133`) + intervalli half-open (`:1691-1692`) supportano From = BROKER-From + IN_TRANSIT-from-From. |
| 1.5 Pool giornalieri | **Coerente (con C5)** | Chiave `(a,b,D,type,currency)`; §15.1 dimentica `currency`. `source_transaction_ids[]` preserva l'audit. |
| 1.6 Pool FEE sui trade | **Coerente (con C2)** | Ripartizione per controvalore + `SAME_DAY_MIXED_TRADES`; formula TradeValue da chiarire. |
| 1.7 Pool TAX sugli income | **Corretto** | Pesi combinati `W_i = Σ_k α_k w_{i,k}`; conservazione dimostrata (§18.1). |
| 1.8 Previous-day only | **Corretto** | Elimina D+1 ⇒ nessun tie-break passato/futuro. Univocità raggiunta. |
| 1.9 Fallback | **Coerente** | Lotti LONG aperti a D-1, `w_i = OpenQty_i(D-1)/Σ`. |
| 1.10 Audit one-shot | **Coerente (con C1)** | Nessuna analysis separata; gruppi compatti. Struttura da correggere per pool misti. |
| 1.11 original_cost invariato | **Corretto** | Feed-forward identico all'implementazione (`lots_analysis_service.py:1044,1047`). |

Tutte le decisioni v4 sono internamente compatibili tranne le imprecisioni C1–C7.

---

## 2. Unicità del motore e migrazione atomica

**Firma reale attuale.** `FifoLotEngine.run(self) -> FifoEngineResult` (`fifo_lot_engine.py:343`) non prende argomenti: gli eventi quantitativi sono passati al costruttore, l'income è filtrato a monte. La v4 richiede `run(quantitative_events, economic_events)`. Cambio di contratto obbligatorio.

**Dove caricare/normalizzare gli economic events.** Oggi `LotsAnalysisService` carica le transazioni, filtra quelle con `quantity != 0` per il motore e alloca income da sé in `_allocate_asset_income` (`lots_analysis_service.py:914-982`). In v4 il service deve:
1. Costruire `EconomicEvent` (DIVIDEND/INTEREST/FEE/TAX) in **valuta nativa** (senza FX).
2. Passarli a `run(...)`.
3. Convertire i **totali dei pool** una sola volta dopo (§25).

**Come impedire il doppio calcolo dell'income.** `_allocate_asset_income` va **rimosso** (non solo bypassato): la logica di pesatura per quantità migra nello stage economico interno. **Attenzione:** la funzione oggi converte in target currency *prima* di allocare (`:941 _converted_external_amount`); nel nuovo modello l'FX **esce** dal motore (deve restare target-agnostic, §25/§28). Questa è la modifica non banale: il motore produce pesi/allocazioni native, il service applica FX.

**Un solo `FifoEngineResult`.** Va esteso (§28) con `economic_allocation_groups`, `economic_accumulators_by_lot`, `asset_orphan_*`. È un `@dataclass(slots=True)` (`:189`); l'aggiunta di campi con `default_factory` mantiene costruibilità nei test. La migrazione atomica **elimina** il vecchio result — coerente con 1.2.

**Simboli/call-site da migrare o rimuovere:**
- `FifoLotEngine.run` (`:343`) — nuova firma.
- `FifoLotEngine.__init__` — accetta anche `economic_events` (o `run` li riceve).
- `FifoEngineResult` (`:189`) — nuovi campi.
- `LotsAnalysisService._allocate_asset_income` (`:914`) — **rimuovere**, logica nel motore.
- Chiamate a `_allocate_asset_income` e uso di `_converted_external_amount` sull'income (`:941`) — spostare l'FX a valle.
- `calculation_status` (property `:198-200`) — 3 stati (vedi §8).
- `value_for_lot`/`aggregate_value`/`relative_return_for_lot` (`:244-287`) — **rimuovere** (solo test).
- Consumer DTO in `lots_analysis_service.py:468,561` (`calculation_status`) e schemi (`portfolio.py:455,742`).

**`economic_stage_completed` non necessario:** concordo con 1.2 — con un unico entrypoint che esegue sempre entrambi gli stadi, il flag sarebbe ridondante. La v3 lo raccomandava per convivenza legacy; la migrazione atomica lo rende superfluo. **Recepimento corretto della critica v3.**

**Fattibilità atomica nel working tree:** **sì**. Il motore ha un solo consumer di dominio (`LotsAnalysisService`); il Portfolio Engine è indipendente (§31 aggiunge accumulatori, non usa il motore FIFO). L'onda tocca backend+schemi+client+frontend+test ma è un grafo di dipendenze lineare, integrabile in un unico merge (vedi §15).

---

## 3. Review del pooling

Chiave `(asset_id, broker_id, date, economic_type, currency)`. Verifica delle proprietà richieste:

- **FEE e TAX non mescolati:** garantito da `economic_type` in chiave. ✅
- **Valute diverse → pool distinti:** garantito da `currency` in chiave (§25.1) — ma **§15.1 la omette** (C5, correggere).
- **Broker diversi non mescolati:** `broker_id` in chiave. ✅
- **Asset-linked vs assetless separati:** gli assetless (`asset_id=null`) non entrano nel FIFO (§13.1, `broker_unallocated_*`), quindi non formano pool FIFO. ✅
- **Auditabilità sorgenti:** `source_transaction_ids[]` (§15.1). ✅
- **Conservazione:** `NativePool = Σ|Amount|` (§24). ✅
- **Nessuna perdita di info per il matching:** il pool conserva `(a,b,D,type,currency)`, sufficiente per determinare i target (trade/income stesso `(a,b,D)`). ✅

**Ordine pooling vs matching (prompt §3).** Il documento poola **prima** del matching (§15→§16). Corretto: il pool è per `(a,b,D,type)`, il matching cerca target compatibili con la stessa chiave `(a,b,D)`. Non serve classificare la famiglia di target prima: il pool è definito dagli eventi economici omogenei, indipendentemente dal target. ✅

**Caso critico (prompt §3): due FEE stesso giorno, una da BUY, una da SELL, nessun link.**
La v4 le somma (`FeePool`) e le distribuisce sul pool misto dei trade per controvalore (§17.4). **Valutazione:** poiché il ledger **non** contiene la causalità (confermato: nessun plugin BRIM valorizza `related_transaction_id` per FEE/TAX; le FEE standalone sono aggregati di estratto conto), attribuire la FeeA specificamente a BUY e la FeeB a SELL sarebbe *inventare* un link inesistente. La ripartizione proporzionale **conserva** l'importo (`Σ=FeePool`) e non introduce doppio conteggio. **Bias sistematico:** esiste solo a livello di *attribuzione per-lotto* (una fee di sola-vendita finisce in parte sui lotti aperti dalla BUY), ma è l'inevitabile conseguenza dell'assenza di causalità. **Difendibile come policy ufficiale**, a patto di documentarlo (C7). Non è un errore matematico.

---

## 4. Review del Pool FEE — formula del controvalore (C2, decisiva)

§17.1: `TradeValue_k = |Quantity_k · ExecutionPrice_k|`, `Fee_k = FeePool · TradeValue_k/ΣTradeValue_j`.

**Verifica dal codice.** Il motore deriva il prezzo unitario come:

```
_unit_price(amount, quantity) = |amount| / |quantity|      # fifo_lot_engine.py:984
```

e apre il lotto con `original_cost = quantity · unit_price` (`:838`). Quindi:

```
original_cost = |quantity| · (|amount|/|quantity|) = |amount|
```

**Conseguenza:** `unit_price` nel motore è un **prezzo per unità singola** (ricavato da `amount/quantity`), **non** una *quote di mercato per-qbq*. Per i bond, dove il market price è una quotazione per 100, la valutazione usa `compute_holding_value(qty, price, qbq) = (qty/qbq)·price` (`valuation_utils.py`), ma l'**execution price** memorizzato/derivato è già assorbito in `amount`.

**Pertanto:**
- Se `ExecutionPrice ≡ unit_price = |amount|/|quantity|`, allora `TradeValue_k = |quantity_k|·|amount_k|/|quantity_k| = |amount_k|` → **corretto anche per i bond**, senza alcuna divisione per qbq.
- La correzione proposta nel prompt `TradeValue = (|Quantity|/QBQ)·ExecutionQuote` è **corretta solo** se `ExecutionPrice` fosse una *quote* per-qbq — **cosa che in questo codice NON è**. Applicarla al `unit_price` reale produrrebbe un errore di ÷100.

**Raccomandazione (modifica testuale §17.1):** sostituire con la forma inequivocabile e qbq-safe:

```
TradeValue_k = |amount_k|      (controvalore lordo della transazione)
```

che coincide con `original_cost` del lotto aperto (BUY) o con i proventi della SELL, è già disponibile nel motore, ed evita per costruzione il trap ×100. In alternativa, definire esplicitamente «`ExecutionPrice = |amount|/|quantity|` (prezzo per unità singola, non quotazione per-qbq)».

**Simulazioni (con `TradeValue = |amount|`):**

| Caso | Trade | TradeValue | FeePool 10 | Fee_k |
|---|---|---|---|---|
| solo BUY | BUY |amount|=1000 | 1000 | 10 | 10 → lotti BUY |
| solo SELL | SELL |amount|=800 | 800 | 10 | 10 → closure |
| BUY+SELL | BUY 1000, SELL 500 | 1500 | 10 | BUY 6.67, SELL 3.33 (`SAME_DAY_MIXED_TRADES`) |
| più BUY | 600, 400 | 1000 | 10 | 6, 4 |
| prezzi diversi | BUY 10@100=1000, BUY 5@120=600 | 1600 | 10 | 6.25, 3.75 |
| qbq=100 bond | BUY nominale 1000 @0.985 → amount=985 | 985 | 10 | 10 (nessun ÷100) ✅ |
| crossing | BUY 10 (amount 1000) chiude SHORT4/apre LONG6 | 1000 | 10 | 10 → poi split close/open per quantità (§20) |
| ADJUSTMENT | unit_price=0 → TradeValue=0 | 0 | — | β=0 (C6) |

Per l'**ADJUSTMENT** (C6): con `TradeValue=0` non riceve fee; se un giorno ha solo ADJUSTMENT (nessun BUY/SELL/income) la FEE cade sul fallback open-lots. Coerente ma **da esplicitare** nel documento: gli adjustment non sono "trade" ai fini del pool FEE.

---

## 5. Review del Pool TAX

§18.1: `α_k = |I_k|/Σ|I_j|`, `W_i = Σ_k α_k w_{i,k}`, `TaxAllocation_i = TaxPool·W_i`.

**Conservazione:** dimostrata correttamente (`Σα_k=1`, `Σ_i w_{i,k}=1` ⇒ `Σ_i W_i=1` ⇒ `Σ TaxAllocation_i = TaxPool`, §18.1). ✅

**Casi (prompt §5):**

| Caso | Comportamento v4 | Verifica |
|---|---|---|
| più DIVIDEND | pesati per `α_k` (importo lordo) | ✅ |
| più INTEREST | idem | ✅ |
| DIVIDEND+INTEREST | stesso pool income (`type` distingue FEE/TAX, non income-subtype) | ⚠ vedi nota |
| più TAX | sommate in `TaxPool` | ✅ |
| income in valute diverse | pool income con currency diversa → **pool TAX distinti** (currency in chiave) | ✅ ma vedi C3 se la TAX è in altra valuta |
| income orfano + income allocabile stesso pool | **ambiguità non risolta** | ⚠ vedi sotto |
| income negativo/rettifica | `α_k = |I_k|/Σ|I_j|` usa `abs` → una rettifica negativa contribuisce peso positivo | ⚠ possibile distorsione |
| TAX > proventi | `TaxAllocation_i = TaxPool·W_i`, nessun cap; NetIncome può diventare negativo | ✅ ammesso (ritenuta > cedola rara ma legale) |
| TAX same-day con trade e income | income ha priorità (§18.1 > §18.2) | ✅ |
| TAX previous-day | `PREVIOUS_DAY_INCOME` (§18.3) | ✅ |

**Nota DIVIDEND+INTEREST nello stesso pool income:** la chiave del pool economico usa `economic_type` (DIVIDEND vs INTEREST sono type distinti). Ma il **target** di una TAX è "gli income compatibili same-day": la v4 non chiarisce se una TAX possa distribuirsi **congiuntamente** su DIVIDEND e INTEREST dello stesso giorno o solo su uno dei due. §18.1 parla di `I_1,…,I_n` generici → sembra includere entrambi. **Da esplicitare:** il pool-target della TAX include tutti gli income (DIVIDEND ∪ INTEREST) same-day dello stesso `(a,b,currency)`.

**Income orfano nel pool TAX (prompt §5, domanda esplicita).** Se tra gli income candidati uno è **orfano** (nessun lotto eleggibile), deve partecipare al peso `α_k`? **Raccomandazione motivata:** l'income orfano **non ha lotti** su cui distribuire `w_{i,k}`, quindi la sua quota `α_k·TaxPool` non può essere allocata a nessun lotto → deve confluire in `asset_orphan_taxes`. Cioè: l'income orfano **partecipa** al peso economico `α_k` (è un provento reale che ha subìto la ritenuta), ma la sua frazione di TAX diventa orphan invece di sparire. Formalmente:

```
AssetOrphanTax = TaxPool · Σ_{k orfano} α_k
Σ_i TaxAllocation_i + AssetOrphanTax = TaxPool     (conservazione preservata)
```

Il documento **non lo specifica** — è una lacuna. **Modifica testuale §18/§19.1:** aggiungere questa regola, altrimenti la conservazione `Σ TaxAllocation_i + AssetOrphanTax = TaxPool` (invariante §33) non regge quando un income candidato è orfano.

---

## 6. Previous-day: univocità

L'eliminazione di D+1 (§16, §1.8) **rende il modello univoco**: non esiste più il tie-break D-1 vs D+1 della v3 (C5 di v3 risolto). Gerarchie:

- **FEE:** same-day trade → previous-day trade → fallback → orphan. (§17)
- **TAX:** same-day income → same-day trade → previous-day income → previous-day trade → fallback → orphan. (§18)

**Verifica contro il testo:** le gerarchie sono esplicitate in §17.1-17.5 (FEE) e §18.1-18.4 (TAX). **Manca però** nel testo FEE l'esplicito tier `SAME_DAY_INCOME`/`PREVIOUS_DAY_INCOME`: il prompt §6 ipotizza per la FEE anche un ramo income, ma la v4 **non** lo prevede (una FEE non cerca income come target). **Valutazione:** corretto — una commissione di negoziazione non si attribuisce a un dividendo; il ramo income per la FEE sarebbe innaturale. La gerarchia FEE trade-only + fallback è coerente. **Segnalare** solo che il prompt e il documento divergono qui, e la scelta del documento è quella giusta.

**Precedenza same-day > previous-day anche con controvalore maggiore:** §16 elenca same-day come step 1 e previous-day come step 2 in ordine gerarchico stretto → il previous-day viene considerato **solo se** il same-day è vuoto. Quindi un previous-day con controvalore maggiore **non** scavalca un same-day. ✅ Univoco.

**Simulazioni:**

| Scenario | Target | Regola |
|---|---|---|
| trade in D-1, fee in D | trade D-1 (nessun trade D) | PREVIOUS_DAY_TRADES |
| income in D-1, tax in D | income D-1 (nessun income D) | PREVIOUS_DAY_INCOME |
| trade in D e D-1, fee in D | trade **D** (same-day vince) | SAME_DAY_MIXED_TRADES/TRADES |
| income in D e D-1, tax in D | income **D** | SAME_DAY_INCOME |
| più trade in D-1 | pool D-1, β per controvalore | PREVIOUS_DAY_TRADES |
| più income in D-1 | pool D-1, α per importo | PREVIOUS_DAY_INCOME |
| nessun candidato D/D-1 | lotti LONG aperti D-1 → orphan | OPEN_LOTS_FALLBACK / NO_ELIGIBLE |

Tutti univoci. ✅

---

## 7. Crossing LONG/SHORT nel pool misto

Composizione (prompt §7): `FeePool → quota trade per controvalore (β) → divisione close/open per quantità → divisione closure per quantità chiusa`.

**Verifica a due livelli:**
1. `Fee_k = FeePool·β_k` (per controvalore trade). `Σ_k Fee_k = FeePool`.
2. Per un trade crossing: `Cost_close = Fee_k·q_c/q`, `Cost_open = Fee_k·q_o/q` con `q=q_c+q_o`. `Cost_close+Cost_open = Fee_k`.
3. `Cost_close` ripartito sulle closure per `ClosedQuantity_i`; `Cost_open` al nuovo lotto opposto.

**Composizione conservativa:** `Σ_i AllocatedFee_i = Σ_k (Cost_close_k + Cost_open_k) = Σ_k Fee_k = FeePool`. ✅ Verificato algebricamente.

**Dati disponibili (codice):** per una BUY crossing, le closure con `close_reason=="BUY"` (`fifo_lot_engine.py:480`) danno `q_c` e i lotti SHORT chiusi; il lotto LONG aperto (`opening_transaction_id==buy.id`, `:485`) dà `q_o`. Per una SELL: closure `close_reason=="SELL"` + lotto SHORT aperto (`:510-520`). Tutto presente.

**Esempio numerico (BUY 10, amount 1000, chiude SHORT 4 su due lotti [3,1], apre LONG 6; FeePool 30, unico trade → β=1):**
- `Cost_closeShort = 30·4/10 = 12` → closure: lotto A `12·3/4=9`, lotto B `12·1/4=3`.
- `Cost_openLong = 30·6/10 = 18` → nuovo lotto LONG.
- Totale 9+3+18 = **30** = FeePool. ✅

**`LotClosure` immutabile:** §20.3 lo dichiara; verificato `frozen=True` (`:137`). Le quote vanno negli accumulatori economici per-lotto, non nelle closure. ✅ **Ma** questo è esattamente il punto in cui emerge **C1**: il lotto A riceve 9 (context CLOSURE); se lo stesso lotto A fosse anche aperto da un BUY nello stesso pool misto, riceverebbe pure una quota OPENING → due `EconomicLotAllocation` con context diverso per lo stesso `lot_id`. Vedi §9.

---

## 8. Status e validità locale (C4)

**Stato attuale.** `FifoEngineResult.calculation_status` è una **property** che ritorna `"DEGRADED" if self.issues else "COMPLETE"` (`fifo_lot_engine.py:198-200`) — binaria, non severity-aware. Il DTO usa `LotCalculationStatus = Literal["COMPLETE","DEGRADED","UNAVAILABLE"]` (`schemas/portfolio.py:455`); nota: `UNAVAILABLE` esiste già ma per lo status **per-lotto**, non globale.

**Cosa serve per la v4:**
- Global `FAILED`: la property va sostituita da logica che ispeziona la **max severity** delle issue (le issue devono portare `severity`; oggi `FifoDataQualityIssue` non ha un campo severity mappato a ERROR/FAILED — verificare in fase implementativa).
- Per-lotto `net_metrics_status: AVAILABLE/UNAVAILABLE` (§27.2): nuovo campo su `LotSummarySchema`/history.

**Definizioni proposte (coerenti col codice):**
- **COMPLETE:** nessuna issue.
- **DEGRADED:** issue WARNING/ERROR **isolabili** (orphan, FX mancante, segno inatteso, conservazione fallita su gruppo identificabile). Quantità e lordo restano validi; `net_metrics_status=UNAVAILABLE` solo sui lotti del gruppo affetto.
- **FAILED:** solo per errori **quantitativi non isolabili** — esempi concreti reali: `TRANSFER_PAIR_MISSING` (`:459`, topologia rotta), `FIFO_SOURCE_QUANTITY_MISSING` (`:523`, SELL>LONG senza shorting) se compromette il replay a valle, violazione dell'invariante di quantità (`InitialQty+In−Out≠OpenQty`).

**`ALLOCATION_CONSERVATION_FAILED` può sempre essere isolata al gruppo?** **Quasi sempre sì:** ogni fallimento di conservazione riguarda un `EconomicAllocationGroup` con `source_transaction_ids[]` e `allocations[].lot_id` noti → perimetro determinato → **DEGRADED + net UNAVAILABLE sui lotti del gruppo**. §27.7 lo modella correttamente (isolabile→DEGRADED, non-isolabile→FAILED). L'unico caso non-isolabile è un bug di somma che attraversa più pool (residuo FX mal ripartito globalmente) — raro. **Raccomandazione:** rendere `ALLOCATION_CONSERVATION_FAILED` **sempre** isolabile per costruzione (residuo confinato all'ultimo lotto del pool, §24), così che porti sempre DEGRADED; riservare FAILED ai soli errori quantitativi. Questo semplifica e rende il netto sempre parzialmente disponibile.

---

## 9. Audit one-shot (C1, strutturale)

Modello §26: un `EconomicAllocationGroup` con singolo `context` e `candidate_count`, e `EconomicLotAllocation(lot_id, weight, native_amount, target_amount)` — **una per lotto**.

**Domande del prompt §9, risposte verificate:**

1. **Un solo `context` basta per pool misti BUY+SELL?** **NO.** Un `SAME_DAY_MIXED_TRADES` (§17.4) attribuisce quote `OPENING` (lotti BUY) e `CLOSURE` (closure SELL) nello **stesso gruppo**. Un unico `context` di gruppo non le distingue.
2. **`target_transaction_ids[]` consente di ricostruire quale quota a quale target?** Solo parzialmente: dà l'insieme dei target, ma la mappa quota→target si perde se le `EconomicLotAllocation` non referenziano il target.
3. **Una sola allocation per lotto perde OPENING vs CLOSURE dello stesso lotto?** **SÌ.** Un lotto aperto da BUY in D e parzialmente chiuso da SELL in D, dentro un pool FEE misto, riceve **sia** una quota OPENING **sia** una quota CLOSURE. Con una sola `EconomicLotAllocation(lot_id)` i due importi si sommano e il breakdown si perde.
4. **Il crossing richiede più righe per lo stesso lot_id?** Il crossing apre un lotto **nuovo** (lot_id diverso) e chiude lotti esistenti → lot_id distinti; ma il caso (3) sopra genera comunque due context sullo stesso lot_id.

**Raccomandazione (struttura gerarchica minima):**

```
EconomicAllocationGroup            # per pool (a,b,D,type,currency)
- rule, native_total, target_total, source_transaction_ids[], candidate_count
- target_allocations[]:
    TargetOperationAllocation      # per operazione target (BUY/SELL/income/lot-fallback)
    - target_transaction_id | closure_ref | fallback
    - context: OPENING | CLOSURE | INCOME | HOLDING
    - lot_allocations[]:
        EconomicLotAllocation
        - lot_id, weight, native_amount, target_amount
```

Cioè spostare `context` (e il riferimento al target) dal **gruppo** al livello **target-operation**, e ammettere **più righe per lo stesso lot_id** sotto context diversi. Questo evita la moltiplicazione completa `source×target×lot` (il prompt §9 la scarta correttamente) ma preserva i due livelli `pool → operazione → lotto`. **Modifica testuale §26 richiesta.**

**Dimensione response (prompt §9).** Le allocazioni sono per **pool**, non per data della history ⇒ dimensione `O(P · L̄)` **indipendente da D**. Stime:
- 10 eventi economici, 20 lotti: ≤ ~10 gruppi × ~qualche lotto ciascuno → ordine 10²  righe. Trascurabile.
- 100 eventi, 100 lotti: worst-case 100 pool × 100 lotti = 10⁴ righe → ~MB di JSON. Gestibile ma non trascurabile.
- molte SELL multi-lotto: ogni pool SELL può toccare molti lotti → il fattore `L̄` cresce.

**Valutazione della scelta one-shot obbligatoria (1.10):** accettabile perché indipendente da D. **Ma** per portafogli con storia lunga e molte operazioni, il worst-case 10⁴ righe suggerisce di mantenere almeno la possibilità di **troncare/paginare** i gruppi nella response standard e fornire il dettaglio completo on-demand. Non è un blocco, ma una **decisione di prodotto** da annotare (vedi §residui).

---

## 10. FX e pool (C3)

**Conservazione nativa e target:** §24 (`Σ NativeAllocation = NativePool`) e §25 (`Σ TargetAllocation = TargetPool`, con conversione **una volta per pool**). Corretto e robusto: convertire il totale del pool una sola volta evita drift di arrotondamento. Residui assegnati deterministicamente in **entrambe** le valute (§24, §25). ✅ Motore target-agnostic (§25). ✅

**Nodo cross-currency FEE/TAX vs trade (prompt §10, "da risolvere matematicamente").** La chiave del pool contiene la valuta **dell'evento economico** (FEE/TAX). I **target** (trade/income) hanno una **loro** valuta, che può differire. Il peso `β_k = TradeValue_k/ΣTradeValue_j`:
- Se **tutti i trade** target condividono una sola valuta, `β_k` è un rapporto e la valuta si semplifica → nessun problema, **anche se** diversa da quella della FEE.
- Se i trade target sono in **valute diverse tra loro** (stesso asset+broker+giorno, caso raro ma rappresentabile), `Σ TradeValue_j` somma importi in valute diverse → **incoerente**.

**Soluzione matematica raccomandata:** calcolare `TradeValue_k` in una **valuta nativa comune di riferimento = valuta dell'asset** (o, equivalentemente, la valuta della FEE), convertendo i controvalori dei trade a `Date_k` con l'FX nativo→riferimento **prima** di calcolare `β`. Formalmente:

```
TradeValue_k = FXConvert(|amount_k|, currency_k, RefCurrency, D)
β_k = TradeValue_k / Σ_j TradeValue_j
```

Questo **non** viola il requisito target-agnostic: `RefCurrency` è la valuta **nativa** dell'asset/evento, non la target currency dell'analisi. La conversione a target avviene comunque una sola volta a valle (§25). **In alternativa più semplice:** vietare il pooling quando i trade candidati hanno valute native diverse (caso patologico) ed emettere `FEE_TAX_ALLOCATION_AMBIGUOUS` o cadere sul fallback. **Modifica testuale §17/§25:** definire esplicitamente la valuta di calcolo di `β` e il comportamento con trade multi-valuta.

**FX mancante:** §27.6 `FX_RATE_MISSING_FOR_ALLOCATION` — allocazione nativa valida, target e net-target UNAVAILABLE. Coerente col fallback FX esistente.

---

## 11. Riconciliazione assoluta

§30: chiave `(asset, broker **evento**, periodo, valuta)`, con `broker_id = broker dell'evento sorgente` conservato sul gruppo (§1075), **non** la custodia del lotto. **Recepisce C3 della v3.** ✅

**Verifica invarianti:** `AllocatedIncome + AssetOrphanIncome = AbsoluteAssetIncome` (idem fees/taxes), per `(a,b,T,c)`. Ben posti.

**Accumulatori pre-share (§31).** Verificato che il Portfolio Engine oggi accumula **già scalato** per `share`: `per_income[(asset,broker)] += amount_target` dopo `amount_target *= ctxn.share` (`portfolio_engine.py:748,838`); idem `per_fees_taxes` (`:849`). §31 introduce `per_income_absolute/per_fees_absolute/per_taxes_absolute` (pre-share) — **necessari e assenti oggi**. Collocazione corretta (`portfolio_engine.py`, Fase 6). ✅ Recepisce C4 della v3.

**Trattamenti (prompt §11):**
- **Assetless:** restano `broker_unallocated_*`, fuori dalla riconciliazione FIFO per-asset. ✅
- **share_percentage:** solo proiezione a valle (§31). Non nel FIFO. ✅
- **Broker multipli:** ogni `(a,b)` è un invariante separato. ✅
- **Target currency:** l'invariante primario è in **valuta nativa** `c`; la riconciliazione target è separata (residui FX). ✅
- **Eventi fuori range:** l'invariante di income/fee/tax si applica agli eventi **nel periodo**; lo stato lotti richiede il replay completo fino a `date_to`. Coerente con `_trim_dates` (`:1664`).
- **Pool orfani:** inclusi in `AssetOrphan*`. ✅
- **In transito:** i frammenti IN_TRANSIT contribuiscono all'eleggibilità (§11), non generano doppio conteggio (un evento = una transazione).

---

## 12. Data Quality

Cinque issue (§27): `ASSET_INCOME_NO_ELIGIBLE_LOTS`, `ASSET_COST_NO_ELIGIBLE_LOTS`, `ECONOMIC_EVENT_UNEXPECTED_SIGN`, `FX_RATE_MISSING_FOR_ALLOCATION`, `ALLOCATION_CONSERVATION_FAILED`.

**`FEE_TAX_ALLOCATION_AMBIGUOUS` è ancora necessario dopo il pooling?** Il prompt §12 chiede la distinzione. **Analisi:** il pooling rende **deterministica** la distribuzione multi-candidato (non è più "ambiguità"). Quindi l'issue **non serve più** per il caso "più candidati stesso tier" — che era la sua ragione d'essere in v2/v3. **Resta utile solo** per il caso patologico **cross-currency trade** (§10, C3): se i trade target hanno valute native incompatibili e si sceglie di non poolare, serve segnalarlo. **Raccomandazione:** o eliminare l'issue (se si adotta la normalizzazione RefCurrency di §10, il caso sparisce), oppure ridefinirla esclusivamente come `FEE_TAX_TARGET_CURRENCY_MISMATCH`. La v4 fa bene a **non** elencarla più tra le issue standard (§27 non la include) — **coerente col pooling ufficiale**. Confermare la rimozione esplicita.

**Policy segno inatteso (prompt §12).** §14/§27.5: una FEE/TAX con segno positivo (inatteso, atteso <0) → `ECONOMIC_EVENT_UNEXPECTED_SIGN` (WARNING/DEGRADED) e **non** viene normalizzata con `abs()` silenziosamente. **Policy univoca raccomandata:** *diagnostica prima, poi normalizza* — emettere l'issue **e** procedere con `abs()` per non perdere l'importo (altrimenti la conservazione salterebbe). Cioè: non ignorare, non orphan automatico, non invalidare solo il netto; **normalizzare con abs() dopo aver emesso il warning**. La v4 §14 dice "deve essere diagnosticato prima di applicare abs() silenziosamente" → **ambiguo** se poi lo applica. **Modifica testuale §14:** esplicitare «si emette il warning e si applica comunque `abs()`; l'importo resta conservato».

---

## 13. Performance

Indici locali proposti (§32) — verificati come sufficienti:

| Indice | Costo build | Uso |
|---|---|---|
| opening_tx → lot | O(L) | attribuzione BUY |
| closing_tx → closures | O(C) | attribuzione SELL |
| (date,asset,broker) → BUY/SELL | O(N) | pool trade |
| (date,asset,broker) → income | O(E) | pool income |
| (lot,date) → eligible qty | O(L·D_eco) o on-demand `_open_quantity_on_date` | pesi D-1 |
| (broker,date) → custody frags | O(F) | scope broker/transit |

**Complessità-obiettivo:**
- Replay quantitativo: `O(N log N + N·F̄)` (invariato).
- Pooling: `O(E)`.
- Matching: `O(P·k)` con `k` candidati medi.
- Net history: `O(L·D)`.

**Rischi da evitare (prompt §13):**
- `O(E·F)`: scansione di tutti i frammenti per ogni evento economico per calcolare l'eleggibilità D-1 → **mitigare** pre-indicizzando i frammenti per `(broker, giorno)` o con prefix-sum di `OpenQuantity` per lotto. **Il documento §32 lo prevede** ((broker,date)→fragments). ✅
- `O(P·L)`: costruzione allocazioni per ogni pool su tutti i lotti → limitare ai soli lotti eleggibili del `(a,b)` (già implicito nello scope broker).
- `O(L·D·E)`: **da evitare** — non ricostruire i candidati per ogni data della history. I candidati si calcolano **una volta** al replay economico; la history riusa gli accumulatori prefix (come già fa `income_prefix_by_lot`, `lots_analysis_service.py:974-981`). ✅

Nessuna cache persistente (§32). Concordo.

---

## 14. Matrice di test aggiornata

| ID | Scenario | Input chiave | Output atteso | Invariante | Test file |
|---|---|---|---|---|---|
| V1 | income D-1 | BUY D-1, DIV D | income→lotto | Σ=IncomeTotal | test_fifo_economic |
| V2 | BUY same-day | BUY D + DIV D | BUY non eleggibile | orphan | test_fifo_economic |
| V3 | SELL same-day | lotto D-1, SELL D + DIV D | eleggibile pre-SELL | Σ | test_fifo_economic |
| V4 | income su To giorno arrivo | ARRIVE D, DIV su To D | orphan (D-1 in transito) | ASSET_INCOME_NO_ELIGIBLE | test_fifo_transit |
| V5 | income orphan | 0 lotti | asset_orphan_income | Σ+orphan | test_fifo_economic |
| V6 | più FEE same-day | FEE-2, FEE-3 | FeePool 5 | pool conserv. | test_fifo_pool |
| V7 | più TAX same-day | TAX-2, TAX-4 | TaxPool 6 | Σ=6 | test_fifo_pool |
| V8 | pool FEE solo BUY | BUY 1000, FEE 10 | 10→lotti BUY | Σ=10 | test_fifo_fee |
| V9 | pool FEE solo SELL | SELL 800, FEE 8 | 8→closure | Σ=8 | test_fifo_fee |
| V10 | pool FEE BUY+SELL | BUY1000/SELL500, FEE10 | 6.67/3.33, SAME_DAY_MIXED_TRADES | Σ=10 | test_fifo_fee |
| V11 | pool TAX più income | DIV100+INT50, TAX15 | W_i=Σα_k w_{i,k} | Σ=15 | test_fifo_tax |
| V12 | income orphan in pool TAX | DIV(orfano)+DIV(ok), TAX | quota orfana→asset_orphan_taxes | Σ+orphan=TaxPool | test_fifo_tax |
| V13 | previous-day trade | trade D-1, FEE D | PREVIOUS_DAY_TRADES | Σ | test_fifo_fee |
| V14 | previous-day income | income D-1, TAX D | PREVIOUS_DAY_INCOME | Σ | test_fifo_tax |
| V15 | nessun D+1 | trade D+1, FEE D | D+1 ignorato → fallback/orphan | — | test_fifo_fee |
| V16 | fallback open lots | FEE custodia, no trade/income | w=OpenQty(D-1) | Σ | test_fifo_fee |
| V17 | orphan cost | 0 lotti LONG D-1 | asset_orphan_fees | ASSET_COST_NO_ELIGIBLE | test_fifo_fee |
| V18 | crossing LONG/SHORT | BUY10 chiude4/apre6, FEE30 | 12 close+18 open | Cost_close+open=30 | test_fifo_crossing |
| V19 | crossing in pool misto | BUY(cross)+SELL, FEE | β poi close/open | Σ=FeePool | test_fifo_crossing |
| V20 | qbq=100 bond | nominale1000@0.985, FEE10 | TradeValue=985, Fee=10 (no ÷100) | — | test_fifo_qbq |
| V21 | trade e FEE valute diverse | BUY USD, FEE EUR | β su Ref-currency | Σ | test_fifo_fx |
| V22 | FX mancante | DIV in XXX | native ok, target UNAVAILABLE | — | test_fifo_fx |
| V23 | residui | FEE frazionaria multi-lotto | residuo→ultimo lotto | Σ=Pool | test_fifo_conservation |
| V24 | chiusura completa | SELL totale + DIV + FEE | cristallizzato | net fisso | test_fifo_economic |
| V25 | estimated-at-cost | no market price, DIV | OpenValue≈cost | GrossPnL≈income | test_fifo_economic |
| V26 | SHORT | SELL apre SHORT, FEE | denom=nozionale apertura | — | test_fifo_crossing |
| V27 | status DEGRADED locale | conservazione fallita su 1 pool | DEGRADED + net UNAVAILABLE lotti gruppo | isolabile | test_fifo_status |
| V28 | status FAILED globale | TRANSFER_PAIR_MISSING | FAILED | non isolabile | test_fifo_status |
| V29 | audit one-shot | pool misto | group→target→lot con context per riga | — | test_fifo_audit |
| V30 | riconciliazione assoluta | mix eventi | Σ+orphan=absolute per (a,b,c) | — | test_fifo_reconciliation |
| V31 | share percentage | share<1 | FIFO assoluto invariato; PE proietta | absolute·share | test_portfolio_reconciliation |
| V32 | segno inatteso | FEE +5 | ECONOMIC_EVENT_UNEXPECTED_SIGN + abs() | Σ conservata | test_fifo_status |

Numeri esatti forniti in V10 (6.67/3.33), V18 (12/18), V20 (no ÷100), §5 (Pool TAX), §7 (crossing 9/3/18).

---

## 15. Migrazione atomica — dependency map

Sequenza §34 trasformata in grafo di dipendenze:

```
Fase 0 (qbq)  ──┐
                ├─► Fase 1a (D-1) ──► Fase 1b (broker/transfer/orphan) ──┐
                                                                          ├─► Fase 2a (contratto run/Result) ──► Fase 2b (economic stage/pool/income) ──► Fase 3 (FEE/TAX/crossing) ──► Fase 4 (FX/net/history) ──► Fase 5 (DTO/frontend) ──► Fase 6 (Portfolio pre-share) ──► Fase 7 (benchmark/cleanup)
```

| Aspetto | Valutazione |
|---|---|
| **File condivisi** | `fifo_lot_engine.py` (0,2a,2b,3), `lots_analysis_service.py` (1a,1b,2b,4), `portfolio_engine.py` (6), `schemas/portfolio.py` (5), frontend (5). |
| **Non parallelizzabile** | 2a→2b→3→4 è una catena stretta sullo stesso file (`fifo_lot_engine.py`) e sullo stesso contratto. Sequenziale. |
| **Parallelizzabile** | Fase 0 (qbq) indipendente; Fase 6 (Portfolio pre-share) indipendente dal motore, può procedere in parallelo dopo Fase 4. |
| **Ordine di integrazione** | 0 → 1a → 1b → 2a → 2b → 3 → 4 → 5 → 6 → 7. |
| **Test gate** | dopo 0 (qbq bond), dopo 1b (income D-1/broker regression), dopo 3 (FEE/TAX conservation), dopo 4 (net + FX), dopo 6 (reconciliation). |
| **Rollback** | realistico solo **prima** di 2a (percorso legacy ancora presente). Da 2a in poi il vecchio income allocator è rimosso → rollback = revert dell'intero branch. |
| **Working tree condiviso** | rischio alto se sviluppato in parallelo sullo stesso file: 2a-4 vanno fatti in serie sullo stesso branch. |

**Conclusione (prompt §15): la migrazione atomica NON è gestibile in una sola sessione**, ma **è integrabile in un unico merge finale** se sviluppata per fasi su un branch dedicato, con i test gate sopra. Il requisito 1.2 ("no coesistenza legacy") è rispettato al **merge**, non necessariamente durante lo sviluppo: internamente si può tenere il vecchio path fino a Fase 2a e rimuoverlo nello stesso branch prima del merge. **Modifica testuale §5:** distinguere «atomicità del merge» (richiesta) da «atomicità dello sviluppo» (non richiesta), altrimenti si impone una big-bang session non realistica.

---

## 16. Criticità residue ordinate per severità

1. **C1 [ALTO]** — Audit `context` a livello di gruppo insufficiente per pool misti e OPENING+CLOSURE sullo stesso lotto. → struttura a tre livelli (§9).
2. **C2 [ALTO]** — `TradeValue` §17.1 ambiguo / trap ×100 sui bond. → `TradeValue = |amount|` (§4).
3. **C3 [MEDIO]** — Pesatura `β` con trade multi-valuta indefinita. → normalizzare a RefCurrency nativa (§10).
4. **C4 [MEDIO]** — `FAILED` + `net_metrics_status` richiedono estendere property binaria e DTO Literal + severity sulle issue (§8).
5. **C5 [BASSO]** — Chiave pool §15.1 omette `currency` (vs §25.1). Testuale.
6. **C6 [BASSO]** — ADJUSTMENT nel pool FEE non specificato (TradeValue=0). Documentare.
7. **C7 [BASSO/prodotto]** — Pooling FEE misto senza warning: attribuzione euristica accettata. Documentare.
8. **Lacuna income-orfano nel pool TAX** [MEDIO] — quota `α_k` di income orfano deve confluire in `asset_orphan_taxes`, altrimenti la conservazione salta (§5).
9. **Lacuna DIVIDEND∪INTEREST target TAX** [BASSO] — esplicitare che il pool-target TAX unisce entrambi (§5).
10. **Segno inatteso** [BASSO] — chiarire che dopo il warning si applica `abs()` (§12).

---

## 17. Modifiche testuali consigliate a `feasibility-analysis-v4.md`

1. **§17.1** — sostituire `TradeValue_k = |Quantity·ExecutionPrice|` con `TradeValue_k = |amount_k|` (controvalore lordo della transazione), oppure definire `ExecutionPrice = |amount|/|quantity|` (per unità singola). Dimostrazione: `original_cost = quantity·unit_price = |amount|` (`fifo_lot_engine.py:838,984`). (C2)
2. **§26.1-26.2** — spostare `context` (e riferimento al target) dal gruppo alla `TargetOperationAllocation`; ammettere più `EconomicLotAllocation` per lotto con context diverso. (C1)
3. **§17/§25.1** — definire la valuta di calcolo di `β` (RefCurrency = valuta asset) e il comportamento con trade multi-valuta; chiarire che non viola il target-agnosticism. (C3)
4. **§27** — specificare che `FAILED` deriva dalla max severity delle issue e che `ALLOCATION_CONSERVATION_FAILED` è sempre isolabile→DEGRADED per costruzione del residuo (§24). (C4)
5. **§15.1** — aggiungere `currency` alla chiave del pool (allineare a §25.1). (C5)
6. **§17** — precisare che ADJUSTMENT_IN/OUT non partecipano al pool trade (TradeValue=0); una FEE su giorno di soli adjustment cade sul fallback. (C6)
7. **§18/§19.1** — regola income-orfano nel pool TAX: `AssetOrphanTax = TaxPool·Σ_{k orfano} α_k`; conservazione preservata.
8. **§18.1** — esplicitare che il pool-target di una TAX unisce DIVIDEND e INTEREST same-day dello stesso `(a,b,currency)`.
9. **§14** — chiarire: dopo `ECONOMIC_EVENT_UNEXPECTED_SIGN` si applica comunque `abs()` (importo conservato), non si scarta l'evento.
10. **§5** — distinguere atomicità del **merge** (richiesta) da atomicità dello **sviluppo** (non richiesta): consentire path legacy interno fino a Fase 2a, rimosso prima del merge.
11. **§27 (rimozione)** — annotare esplicitamente che `FEE_TAX_ALLOCATION_AMBIGUOUS` è **soppressa** dal pooling ufficiale (evita confusione con v2/v3).

---

## 18. Decisioni di prodotto residue

1. **Pooling FEE misto senza warning** (C7): confermare che una fee su round-trip BUY+SELL si distribuisca per controvalore senza alcun segnale. *Raccomandazione: confermato, ma esporre `SAME_DAY_MIXED_TRADES` nel tooltip.*
2. **Income-orfano nel pool TAX**: la sua quota diventa `asset_orphan_taxes` (raccomandato) o si redistribuisce sugli income allocabili? *Raccomandazione: orphan, per non gonfiare i lotti presenti.*
3. **Dimensione audit one-shot** (§9): mantenere sempre inline anche a 10⁴ righe o troncare con dettaglio on-demand per portafogli grandi? *Raccomandazione: inline con soglia di troncamento configurabile.*
4. **Costo post-chiusura via PREVIOUS_DAY_TRADES** (§790): un costo in D attribuito a un trade in D-1 modifica il netto **cristallizzato** dalle date ≥ D → la history netta diventa non-monotona nel punto D. Confermare che è il comportamento voluto (è corretto contabilmente).
5. **Trade multi-valuta stesso asset+broker+giorno** (C3): normalizzare `β` o vietare il pooling? *Raccomandazione: normalizzare a RefCurrency; è più robusto.*

---

## 19. Raccomandazione finale

**GO CON MODIFICHE.**

La v4 è la versione più solida e **implementabile**: risolve i due nodi bloccanti/strutturali della v3 (riconciliazione share-aware, stato a tre valori), rende il matching **univoco** grazie a pooling + previous-day-only, e definisce una migrazione atomica coerente col fatto che il motore ha un solo consumer di dominio.

Prima di redigere il piano implementativo vanno risolte **C1** (struttura audit per pool misti/crossing) e **C2** (formula TradeValue qbq-safe), più le lacune di conservazione del pool TAX (income orfano). Sono correzioni di **specifica**, non di architettura: il modello a due passate, motore assoluto e feed-forward resta corretto e verificato contro il codice.

Le 11 modifiche testuali di §17 e le 5 decisioni di prodotto di §18 completano il documento. Con queste, `feasibility-analysis-v4.md` è una base sufficiente per il piano implementativo.
