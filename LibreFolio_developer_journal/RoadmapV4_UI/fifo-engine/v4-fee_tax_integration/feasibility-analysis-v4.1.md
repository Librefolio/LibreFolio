# Review tecnica 4.1 — FIFO Engine v4: pooling in target currency e validazione dei segni

> Documento di sola verifica. Nessuna modifica a codice, schemi, test o documenti.
> Fonte di verità: codice reale del repository. Riferimento di piano: `feasibility-analysis-v4.md`.
> Le tre review precedenti (`feasibility-analysis.md`, `-v2`, `-v3`, `-v4-review`) NON vengono ripetute:
> qui si analizzano solo le tre decisioni residue della 4.1 e i loro effetti combinati.

---

## 0. Executive summary

La review 4.1 verifica tre punti:

1. **Calcolo economico in `target_currency`** come valuta comune di pooling, pesi, allocazioni e metriche.
2. **Reale rappresentabilità** dello scenario "un income allocabile + un income asset-orphan nello stesso pool TAX".
3. **Garanzia multilivello del segno** di FEE/TAX (Pydantic, service, DB, plugin BRIM).

Esiti sintetici:

| # | Tema | Esito | Azione |
|---|------|-------|--------|
| 1 | Target currency | **Coerente e in gran parte già implementato**. Il servizio converte già l'income a `tx.date` con `_FxRateResolver`. Raccomandata **Opzione B** (native + target sull'`EconomicEvent`). | Adozione + 1 chiarimento matematico |
| 2 | Income orphan/allocabile nello stesso pool TAX | **IMPOSSIBILE per costruzione** con la chiave `(asset, broker, date, currency)`: l'eleggibilità non dipende dal tipo income. | **Rimuovere lo scenario** da spec e test |
| 3 | Segno FEE/TAX | **GARANTITO SOLO SU CREATE e IMPORT (a livello API/Pydantic). NON garantito su UPDATE né su DB.** Due bypass reali individuati. | Correzione minima obbligatoria prima di eliminare il ramo difensivo |

**Giudizio complessivo: GO CON MODIFICHE.**

Le tre decisioni sono sane, ma:

- il punto 2 consente una **semplificazione netta** della specifica (scenario impossibile → via da test e policy);
- il punto 3 **non può** portare all'eliminazione incondizionata di `ECONOMIC_EVENT_UNEXPECTED_SIGN` **finché** il percorso di UPDATE e il DB non vengono blindati: l'assunzione `CostTotal = -Amount` non è oggi vera end-to-end.

Le criticità residue sono raccolte e ordinate per severità al §14.

---

## 1. Valutazione del calcolo in `target_currency`

### 1.1 Cosa fa già il codice

La conversione FX dell'analisi è centralizzata in `_FxRateResolver`:

- costruito con la sola `target_currency` — `lots_analysis_service.py:114-116`, istanziato in `get_lots_analysis` a `:269`;
- accumula i bisogni `(currency, as_of_date)` — `:121-128` — e li risolve in blocco via `convert_bulk` — `:130-140`;
- converte con `amount * rate` **senza arrotondamento intermedio** — `:142-150` (rounding solo a serializzazione DTO).

L'income asset-linked è **già** convertito in target currency **alla data della transazione**, *prima* dell'allocazione:

```python
# lots_analysis_service.py:940-941
for tx in sorted(income_transactions, ...):
    total = self._converted_external_amount(tx.amount, tx.currency or asset_currency, tx.date, fx_resolver)
```

con `_converted_external_amount` = `fx_resolver.convert(amount, currency, as_of_date) or amount` — `:1641-1648`.

**Conseguenza forte**: la decisione 4.1 "convertire tutto in target currency prima del calcolo economico" **non è una rottura architetturale**: è l'estensione a FEE/TAX e ai trade di ciò che il servizio fa già per l'income. Il resolver è già:

- **date-aware** (rate a `tx.date`, non "latest") → soddisfa il requisito "conversione alla data della transazione";
- **bulk** (una sola query FX per analisi) → nessuna esplosione di chiamate;
- **riusabile** dal nuovo motore senza duplicare la logica FX.

### 1.2 Le tre architetture

| Opzione | Descrizione | FX duplicata? | Audit nativo? | Motore testabile? | Motore FX-agnostic? |
|---------|-------------|---------------|---------------|-------------------|---------------------|
| **A** – eventi pre-convertiti | il service normalizza in target e passa solo importi target | No | **Perso** (solo target) | Sì | Sì (ma perde native) |
| **B** – native + target sull'evento | `EconomicEvent{native_amount, native_currency, target_amount, target_currency}` | No (FX nel service) | **Sì** | Sì (input puri) | **Value-aware, FX-mechanism agnostic** |
| **C** – resolver nel motore | il motore riceve `_FxRateResolver` e converte | Sì (logica FX entra nel motore) | Sì | **No** (motore dipende da DB/FX async) | No (motore target-aware + FX-aware) |

**Raccomandazione: Opzione B.**

Motivazioni ancorate ai vincoli espressi (§2 del prompt):

- *"usare target per tutti i confronti"* → il motore usa `target_amount` per pesi (`β`, `α`) e metriche nette;
- *"evitare doppie conversioni"* → il service converte **una sola volta per pool** (vedi §2), il motore non riconverte;
- *"mantenere l'audit nativi"* → l'evento porta `native_amount`/`native_currency` accanto ai target;
- *"non duplicare la logica FX"* → resta tutta in `_FxRateResolver`/`convert_bulk`; il motore non tocca il DB;
- *"FifoEngineResult autoconsistente"* → l'unico entrypoint riceve eventi già arricchiti e restituisce allocazioni sia native sia target.

**Nota di coerenza con la review precedente.** La v4-review raccomandava un motore *target-agnostic*. La decisione 4.1 lo sovrascrive esplicitamente: il motore diventa **target-value aware** (consuma `target_amount`) ma resta **FX-mechanism agnostic** (nessun resolver interno). Questa è la conciliazione corretta: si guadagna il confronto cross-currency mantenendo un motore puro e deterministico. La Opzione C va **scartata** perché reintrodurrebbe I/O async e dipendenza dal DB nel motore, contraddicendo il requisito di unico entrypoint testabile del §1.1 del piano.

### 1.3 Stessa analisi in target currency diverse

Con Opzione B, richiedere la stessa analisi in EUR e in USD significa: due `_FxRateResolver` distinti → due set di `target_amount` → due run del motore. Il motore resta puro (nessuno stato condiviso). **Nessun conflitto**: è già così che il servizio produce output multi-valuta oggi (target_currency è parametro di `get_lots_analysis`, `:1675`).

---

## 2. Conservazione nativa e target

### 2.1 Risultato matematico chiave: i pesi sono FX-invarianti dentro un pool omogeneo

Il pooling raggruppa per chiave `(asset_id, broker_id, date, economic_type, currency)`. **Tutti** gli eventi di un pool condividono quindi **stessa valuta nativa e stessa data**, dunque **lo stesso tasso** `r` restituito da `convert_bulk` per `(currency, date)`.

Per un pool FEE/TAX, ogni peso è un rapporto:

```
β_k = TargetTradeValue_k / Σ_j TargetTradeValue_j
    = (r · |amount_k|) / Σ_j (r · |amount_j|)
    = |amount_k| / Σ_j |amount_j|
```

Il tasso `r` **si cancella**. **I pesi calcolati in native e in target sono identici** finché il target di allocazione condivide la valuta del pool. La conversione in target currency **cambia i numeri solo** quando un pool costo in valuta X deve essere distribuito su operazioni target in valuta Y (FEE↔trade cross-currency) — è l'**unico** punto in cui la normalizzazione a valuta comune è realmente necessaria.

> Implicazione redazionale per il piano: le formule §2.1 del prompt (pesi in target) sono corrette ma, per pool a valuta unica, **ridondanti**. Vanno mantenute perché diventano indispensabili nel caso cross-currency (§2.3 qui sotto).

### 2.2 "Convertire ogni transazione" vs "convertire il pool una volta"

Poiché ogni pool ha valuta+data uniche e `convert` è un multiplo lineare senza arrotondamento intermedio (`:150`):

```
Σ_e (amount_e · r) = r · (Σ_e amount_e)
```

Le due modalità sono **algebricamente identiche, drift = 0 per costruzione**. Non serve scegliere "a seconda dei casi": la condizione (stessa data+valuta) è **garantita dalla chiave di pooling**.

**Raccomandazione**: convertire **la somma del pool nativo una sola volta** (`TargetPool = r · NativePool`). Vantaggi: meno conversioni, conservazione banale, coerenza col Portfolio Engine (che già aggrega su somme). Conservare gli `native_amount` per-transazione solo ai fini di audit.

### 2.3 Cross-currency (FEE in valuta ≠ trade)

Qui la chiave di pooling **separa** già la FEE (currency X) dal pool trade (currency Y): sono pool distinti. Per distribuire la FEE X sui trade Y il peso `β_k` va calcolato su un **controvalore comune**. Determinazione:

- **Valuta comune = `target_currency` dell'analisi** (non una valuta "asset ref" arbitraria): è l'unica nota, coerente e già disponibile via resolver. Questo risolve il nodo lasciato aperto in v4-review C3.
- La conversione avviene **nel service** (Opzione B), non nel motore.
- **Non** contraddice il requisito di motore "value-aware": il motore riceve `target_amount` già pronto e calcola `β` su quei valori.

**Policy residui in target currency.** Dopo `TargetPool = r · NativePool`, la ripartizione `TargetPool · β_k` produce residui di divisione. Applicare lo **stesso running-remainder già in uso** per l'income (`lots_analysis_service.py:955-961`: l'ultimo elemento in ordine deterministico assorbe il residuo). Invarianti da mantenere:

```
Σ_i NativeAllocation_i + NativeOrphan = NativePool     (audit nativo)
Σ_i TargetAllocation_i + TargetOrphan = TargetPool     (audit target, con TargetPool = r · NativePool)
```

Poiché `TargetPool` è derivato dal native con lo stesso `r`, le due conservazioni sono **la stessa equazione moltiplicata per `r`**: verificarne una implica l'altra (non serve doppia riconciliazione runtime; basta conservare `r` per pool nell'audit).

---

## 3. Controvalore dei trade — verifica dal codice

### 3.1 `TradeValue_k = |TransactionAmount_k|` è corretto e qbq-safe

Confermato nella review v4 (decisione consolidata §1.6) e ri-ancorato:

- `_unit_price(amount, quantity) = |amount| / |quantity|` — `fifo_lot_engine.py:984` — è un **prezzo per unità singola**, NON una quotazione per-qbq;
- `original_cost = quantity · unit_price = |amount|` — `:838`.

Quindi `|Quantity · ExecutionPrice| = |amount|` **è già il controvalore lordo registrato**, senza ulteriore scaling qbq. La decisione 4.1 di usare direttamente `|TransactionAmount_k|` (l'`amount` firmato della transazione, in valore assoluto) è **la formulazione più robusta**: elimina il rischio di re-derivare il prezzo e di doppia divisione per qbq che affliggeva la proposta `(|Q|/QBQ)·ExecutionQuote`.

**Conferma esplicita richiesta dal prompt**: NON serve alcun ulteriore scaling qbq sul controvalore FEE. Il qbq riguarda solo la **valorizzazione di mercato** (`compute_holding_value(qty, price, qbq) = (qty/qbq)·price`), non il controvalore transazionale, che è già l'`amount` netto scambiato.

### 3.2 Post-FX

```
TargetTradeValue_k = |r · TransactionAmount_k| = r · |TransactionAmount_k|   (r > 0)
```

L'`abs` e la conversione commutano (tasso positivo). Nessun ulteriore scaling.

### 3.3 Esempi numerici

| Caso | Input | TradeValue nativo | Target (r) | Note |
|------|-------|-------------------|------------|------|
| Azione qbq=1 | BUY 10 @ 100 → amount = −1.000 | 1.000 | EUR→EUR, r=1 → 1.000 | banale |
| Bond qbq=100 | BUY 1.000 nominali @ quota 98 → amount = −980 | 980 | 980 | il qbq **non** rientra: `amount` è già netto |
| USD→EUR | SELL amount = +1.200 USD, r=0,90 | 1.200 | 1.080 EUR | conversione una volta |
| Due trade valute diverse | BUY −1.000 USD (r=0,90), SELL +500 GBP (r=1,15) | non comparabili nativi | 900 EUR, 575 EUR | pesi solo dopo target-normalizzazione |
| FEE EUR + trade USD | FEE −5 EUR; BUY amount −1.000 USD (r=0,90) | pool distinti (chiave currency) | FEE su base target: trade = 900 EUR → β=1 | cross-currency: peso in target |
| Crossing LONG/SHORT | SELL 15 su lotto LONG 10 → chiude 10, apre SHORT 5, amount = +1.800 | 1.800 | 1.800 | β sul controvalore totale del trade; poi split close/open per quantità (§7) |

**Verifica β cross-currency (riga 5).** Con un solo trade nel pool target, `β = 1` → l'intera FEE (in EUR) va su quel trade: nessuna ambiguità. Con due trade in valute diverse (riga 4) i pesi si calcolano **solo** dopo la normalizzazione target: `β_USD = 900/1475 ≈ 0,610`, `β_GBP = 575/1475 ≈ 0,390`. Conservazione: `900+575 = 1475 = TargetTradeValueTotal`.

---

## 4. Scenario "income allocabile + income orphan nello stesso pool TAX": è reale?

### 4.1 La funzione di eleggibilità dal codice

L'insieme dei lotti eleggibili per un income è calcolato in `_allocate_asset_income`:

```python
# lots_analysis_service.py:942-951
open_lots = []
for lot_id, lot in lots_by_id.items():
    if lot.direction != "LONG" or lot.opening_date > tx.date:
        continue
    open_qty = self._open_quantity_on_date(fragments_by_lot.get(lot_id, []), tx.date)
    if open_qty > 0:
        open_lots.append((lot_id, open_qty))
total_qty = sum(qty for _, qty in open_lots)
if total_qty <= 0:
    continue   # <-- income "orphan": nessun lotto → oggi semplicemente skippato
```

con `_open_quantity_on_date(fragments, tx.date)` — `:1633-1634` — che somma i frammenti attivi a `tx.date` (`_fragment_active_on_date`, `:1691-1692`).

**Osservazioni decisive:**

1. L'eleggibilità dipende **esclusivamente** da: direzione LONG, `opening_date ≤ tx.date`, e quantità aperta `> 0` alla data `tx.date`.
2. **Non compare mai `tx.type`**: DIVIDEND e INTEREST attraversano **identico** codice di selezione lotti.
3. La quantità aperta è funzione **solo** di `(fragments, date)`, non della singola transazione income.

Quindi, nel modello v4 (dove l'eleggibilità diventa `f(asset, broker, D−1)`):

```
EligibleLots(income) = f(asset_id, broker_id, D−1)     ⟂  tipo income, ⟂ id transazione
```

### 4.2 Conseguenza: lo scenario misto è impossibile per costruzione

Due income con **stessa chiave** `(asset_id, broker_id, date, currency)` — che è esattamente la chiave che li mette **nello stesso pool TAX** — hanno **necessariamente lo stesso insieme di lotti eleggibili** (stesso asset, stesso broker, stessa `D−1`). Perciò:

- se quel set è non vuoto → **entrambi allocabili**;
- se quel set è vuoto → **entrambi orphan**.

Non esiste alcun meccanismo (fragment, transfer, scope, Asset Event, tipo income) che renda **un** income della stessa chiave allocabile e **l'altro** orphan:

- fragment/transfer/transit incidono via `_open_quantity_on_date(fragments, D−1)`, **identico** per entrambi (stessa data);
- valute diverse ⇒ **pool diversi** per definizione della chiave (currency inclusa);
- il tipo DIVIDEND/INTEREST **non filtra** i lotti (§4.1 punto 2);
- lo scope broker (una volta corretto il noto bug broker-scope) è parametro di chiave, non della singola tx.

**Conclusione**: lo scenario "uno allocabile e uno orphan nello stesso pool TAX" **va rimosso** dalla specifica e dai relativi test. La policy di conservazione TAX si semplifica: **un pool TAX è O interamente allocabile O interamente orphan**. In caso orphan, l'intero `TaxPool` diventa `asset_orphan_taxes` con un solo `ASSET_COST_NO_ELIGIBLE_LOTS`. Nessun bisogno della complessità "quota α_k dell'income orphan instradata a orphan_taxes" ipotizzata in v4-review.

### 4.3 Unico caveat da blindare

L'impossibilità regge **a condizione** che l'eleggibilità sia realmente `f(asset, broker, date)` **senza** dipendenze per-transazione. Due punti da fissare nel piano perché l'invariante non si rompa in implementazione:

- **(a)** L'eventuale `asset_event_id` **non** deve entrare nel filtro dei lotti eleggibili (oggi non lo fa: `:942-951` ignora `asset_event_id`). Mantenerlo così.
- **(b)** La transizione a `D−1` deve usare **la stessa data** per tutti gli income del pool (la chiave garantisce già `date` uguale). Confermato compatibile.

Se in futuro si introducesse un'eleggibilità income-specifica (es. dividendi che escludono lotti acquistati ex-date diversa), l'invariante cadrebbe: in tal caso lo scenario tornerebbe possibile. **Va documentato come precondizione esplicita del design.**

---

## 5. Garanzia del segno di FEE e TAX — verifica multilivello

### 5.1 Livello Pydantic — CREATE (`TXCreateItem`)

`TXCreateItem._business_rules` impone:

- **Rule 7** — cash **obbligatorio** per FEE/TAX — `transactions.py:234-249` (FEE, TAX in `cash_required_types`);
- **Rule 11** — segno del cash — `:293-299`:

```python
# :296
if self.type in (BUY, WITHDRAWAL, FEE, TAX) and amt >= zero:
    errors.append(... "cashSignNegative", "{type} requires cash.amount < 0" ...)
```

Il valore persistito è `amount = item.get_amount()` = `cash.amount` firmato — `transaction_service.py:1216`, `get_amount` a `transactions.py:345-347`. **Sul CREATE il segno FEE/TAX < 0 è garantito.**

### 5.2 Livello Pydantic — UPDATE (`TXUpdateItem`) — **BYPASS**

`TXUpdateItem._business_rules` valida **soltanto `id > 0`**:

```python
# transactions.py:548-558
@model_validator(mode="after")
def _business_rules(self) -> TXUpdateItem:
    if self.id is not None and self.id <= 0:
        raise PydanticCustomError("idRequired", ...)
    return self
```

**Non c'è alcuna Rule 10/11.** Il service applica i campi **grezzi**, senza ri-validazione:

```python
# transaction_service.py:1147-1151
if item.quantity is not None:
    tx.quantity = item.quantity
if item.cash is not None:
    tx.amount = item.cash.amount     # <-- nessun controllo di segno per tipo
    tx.currency = item.cash.code
```

L'unico controllo tipo-correlato è lo swap di tipo entro il **swap group** (`:1138-1142`), ma:

- il swap group FEE↔TAX (`transactions.py:470`) mantiene entrambi negativi → non aiuta;
- soprattutto, **anche senza cambio tipo**, un `PATCH` che porta il `cash.amount` di una FEE a **valore positivo** passa la validazione e viene scritto tal quale. Dopo il loop (`:1167-1172`) non c'è **nessuna** ri-validazione del modello mergiato.

⇒ **Bypass reale e raggiungibile via API pubblica di update.**

### 5.3 Livello DB — **NESSUN VINCOLO**

Il modello `Transaction` non ha CHECK sul segno:

```python
# db/models.py:590-595  → solo Index, nessun CheckConstraint
# :615-619  amount: Numeric(18,6), nullable=False, default 0  → nessun vincolo di segno
```

Inserimento diretto via ORM (fixture, script di migrazione, test che costruiscono `Transaction(...)`) può produrre FEE/TAX con qualsiasi segno.

### 5.4 Livello plugin BRIM

I provider costruiscono `TXCreateItem` tramite l'helper del framework, che intercetta le `ValidationError` come issue strutturate:

- `brim_provider.py:398-410` — `build_transaction_or_issue` chiama `TXCreateItem(**kwargs)`.

⇒ **anche se un provider dimenticasse di negare**, la Rule 11 (§5.1) **rifiuterebbe** la riga in import. La garanzia dell'import **deriva da `TXCreateItem`**, non dalla disciplina dei plugin. In aggiunta, i provider normalizzano comunque a `-abs`:

| Provider | Riferimento |
|----------|-------------|
| avanza | `broker_avanza.py:80-81` (`-abs` per BUY/WITHDRAWAL/FEE/TAX) |
| bux | `broker_bux.py:107-108` |
| schwab | `broker_schwab.py:368` (`amount=-abs(fees)`) |
| bitvavo | `broker_bitvavo.py:312` (`-abs(fee_amount)`) |
| coinbase | `broker_coinbase.py:305` (`amount=-fees`) |
| cointracking | `broker_cointracking.py:188` (`-fee`) |
| degiro | `broker_degiro.py:401-405` (flip export positivi per BUY/FEE/TAX) |
| revolut | `broker_revolut.py:501` (`-abs(amount)`) |

Ridondanza sana (plugin + API), ma **non copre update né ORM diretto**.

### 5.5 Classificazione richiesta dal prompt

> **GARANTITO SOLTANTO A LIVELLO API DI CREATE E IMPORT.**
> **NON GARANTITO SU UPDATE (bypass Pydantic) NÉ SUL DB (nessun CHECK).**

Pertanto **NON** si può oggi assumere incondizionatamente `CostTotal = −Amount` eliminando il ramo difensivo: esistono due percorsi (update API, ORM diretto) che producono FEE/TAX con segno inatteso.

### 5.6 Correzione minima consigliata

Ordine di preferenza (dal più forte/economico end-to-end al più locale):

1. **CHECK constraint DB** (copertura totale, incluso ORM diretto e legacy). Migrazione Alembic incrementale con un CHECK per famiglia di segno, es.:
   - `type IN ('BUY','WITHDRAWAL','FEE','TAX') ⇒ amount ≤ 0`
   - `type IN ('SELL','DIVIDEND','INTEREST','DEPOSIT') ⇒ amount ≥ 0`
   Da valutare la **compatibilità coi dati legacy** già presenti (uno script di verifica pre-migrazione è d'obbligo: un CHECK su dati sporchi fallirebbe la migrazione). Questo rispetta la regola repo "migrazioni incrementali per install rilasciate".
2. **Validazione service post-merge sull'update**: dopo aver applicato i campi (`:1147-1151`), ricostruire il tipo effettivo (`item.type or tx.type`) e applicare la stessa Rule 11 di `TXCreateItem`, raccogliendo l'errore nel medesimo canale issues (`:1171-1172`). Correzione più piccola a livello di codice, ma **non copre l'ORM diretto**.

La scelta **(1) + (2)** rende il segno **GARANTITO END-TO-END**; solo allora la specifica può eliminare `ECONOMIC_EVENT_UNEXPECTED_SIGN` e usare `CostTotal = −Amount` senza ramo difensivo.

Finché la correzione non è in essere, il piano **deve mantenere** il trattamento difensivo: normalizzare con `abs()` **e** emettere il warning (preserva conservazione senza perdere il segnale diagnostico). NON ignorare l'evento e NON invalidare solo il netto: `abs()` mantiene la riconciliazione.

---

## 6. Struttura audit a tre livelli

La decisione consolidata `EconomicAllocationGroup → TargetOperationAllocation → EconomicLotAllocation`, con **context sul target operativo** (non sul gruppo), risolve la criticità strutturale C1 della v4-review (pool misto BUY+SELL e stesso lotto in OPENING+CLOSURE). Verifica di copertura:

| Scenario | Rappresentabile? | Come |
|----------|------------------|------|
| Pool FEE solo BUY | Sì | 1 gruppo → N target(OPENING) → lotti |
| Pool FEE solo SELL | Sì | 1 gruppo → N target(CLOSURE) → lotti/closure |
| Pool FEE misto BUY+SELL | Sì | 1 gruppo → target OPENING **e** CLOSURE con context distinti |
| Crossing LONG/SHORT | Sì | stesso trade → 2 target (CLOSURE quota chiusa, OPENING quota aperta opposta) |
| Pool TAX su più income | Sì | 1 gruppo → N target(INCOME) → lotti pesati α_k·w_i,k |
| Fallback HOLDING | Sì | 1 gruppo → 1 target(HOLDING) → lotti per quantità |
| Orphan | Sì | 1 gruppo → 0 target o target sentinel, `native_orphan`/`target_orphan` valorizzati |
| Costo previous-day | Sì | target datati `D−1`, `rule = PREVIOUS_DAY_*` |
| Stesso lotto OPENING+CLOSURE | Sì | **due** `EconomicLotAllocation` sotto **due** target diversi (non più collassato) |

### 6.1 DTO minimo proposto (campi native + target separati)

```text
EconomicAllocationGroup
- asset_id, broker_id, date
- economic_type            # FEE | TAX
- rule                     # SAME_DAY_MIXED_TRADES | PREVIOUS_DAY_TRADES | PREVIOUS_DAY_INCOME | FALLBACK_HOLDING | ORPHAN
- source_transaction_ids[] # transazioni FEE/TAX pooled
- native_currency, native_total
- target_currency, target_total
- fx_rate                  # r del pool (per riconciliazione, §2.3)
- native_orphan, target_orphan
- targets: TargetOperationAllocation[]

TargetOperationAllocation
- context                  # OPENING | CLOSURE | INCOME | HOLDING
- target_transaction_ids[] # operazione/e target (trade o income)
- weight                   # β_k (trade) o α_k (income)
- native_amount, target_amount
- lots: EconomicLotAllocation[]

EconomicLotAllocation
- lot_id
- weight                   # w_i (o w_i,k)
- native_amount, target_amount
```

`fx_rate` sul gruppo consente di verificare `target_total = fx_rate · native_total` senza doppia riconciliazione (§2.3). L'audit resta **inline** nella risposta one-shot.

### 6.2 Stima dimensione risposta

- **10 eventi / 20 lotti**: pochi gruppi (raggruppati per chiave), tipicamente ≤10 gruppi × (1–3 target) × (≤20 lotti) → ordine 10²–10³ righe. Trascurabile.
- **100 eventi / 100 lotti**: dominato da `P · T · L` con P = numero pool. Con pooling la P è molto < 100 (eventi omogenei collassati). Stima ordine 10³–10⁴ righe: gestibile inline; se necessario, la struttura a 3 livelli **non moltiplica** source×target×lot (che sarebbe l'esplosione da evitare) perché le source sono aggregate nel gruppo.
- **Molte vendite multi-lotto**: il costo è `Σ closure`, già presente nell'analisi FIFO; l'audit costo aggiunge un fattore costante per closure. Nessuna esplosione combinatoria.

---

## 7. Status

Confermata la semplificazione a tre stati con la seguente semantica:

| Status | Trigger | Isolabilità |
|--------|---------|-------------|
| **COMPLETE** | nessuna issue che riduca affidabilità/disponibilità | — |
| **DEGRADED** | errori economici **isolabili** al pool/lotti (orphan, FX mancante, segno inatteso normalizzato, allocazione localmente fallita) → metriche nette `UNAVAILABLE` solo sui lotti del pool | sì |
| **FAILED** | errore quantitativo **non isolabile** (replay, quantità, topologia, matching generale, conservazione economica globale) | no |

`ALLOCATION_CONSERVATION_FAILED` è **sempre riconducibile a un pool noto** (chiave `(asset, broker, date, type, currency)` + `source_transaction_ids[]` + `lot_ids`): l'audit a 3 livelli fornisce esattamente il perimetro. Perciò **deve produrre DEGRADED**, con `net_metrics_status = UNAVAILABLE` solo sui lotti del gruppo, **mai FAILED**.

**FAILED reali** (non isolabili al pool):

- replay quantitativo incoerente (es. SHORT non supportato su transfer, `:1700` issue esistenti);
- quantità negativa non ammessa dove `allow_asset_shorting = False`;
- topologia frammenti rotta (frammento senza intervallo valido);
- errore di matching che impedisce di costruire i lotti stessi.

### 7.1 Impatti da modificare (per implementazione, non ora)

- `FifoEngineResult.calculation_status` è oggi **property binaria** — `fifo_lot_engine.py:198-200` — va estesa a tre stati.
- Il DTO `LotCalculationStatus = Literal["COMPLETE","DEGRADED","UNAVAILABLE"]` — `schemas/portfolio.py:455` — necessita del terzo stato di gruppo `FAILED` (o un enum separato per il livello analisi vs livello lotto: consigliato **separare** "status analisi" {COMPLETE,DEGRADED,FAILED} da "net_metrics_status lotto" {AVAILABLE,UNAVAILABLE}).
- Frontend + i18n: nuove chiavi per DEGRADED/FAILED e per `net_metrics_status`. (Solo enumerazione qui; nessuna modifica in questa review.)

---

## 8. Test matrix 4.1

| # | Scenario | Layer | Output atteso | Invariante | Package/file suggerito |
|---|----------|-------|---------------|------------|------------------------|
| T1 | Pooling diretto in target currency (1 valuta) | engine | pesi = rapporti native | `Σ alloc = pool` | `backend/test_scripts/` fifo engine |
| T2 | Stessa analisi in EUR e USD | service | due output, pesi identici, importi × r | pesi FX-invarianti (§2.1) | lots analysis |
| T3 | Pool con una sola valuta nativa | engine | conversione una volta | drift = 0 | fifo engine |
| T4 | Trade candidati in valute differenti | service+engine | β su base target | `Σβ=1` | lots analysis |
| T5 | FEE in valuta ≠ trade | service | β cross-currency in target | conservazione target | lots analysis |
| T6 | Bond qbq=100 | engine | TradeValue = |amount|, no scaling | qbq-safe | fifo engine |
| T7 | Conservazione nativa | engine | `Σ native + orphan = native pool` | esatta | fifo engine |
| T8 | Conservazione target | engine | `Σ target + orphan = r·native pool` | esatta | fifo engine |
| T9 | Residui | engine | ultimo lotto assorbe | nessun valore perso | fifo engine |
| T10 | FX mancante | service | DEGRADED, net UNAVAILABLE sul pool | gross intatto | lots analysis |
| T11 | DIVIDEND + INTEREST stessa chiave | engine | stesso set lotti eleggibili | eleggibilità = f(asset,broker,D−1) | fifo engine |
| T12 | **Impossibilità** allocabile/orphan stesso pool TAX | engine | pool O tutto allocabile O tutto orphan | §4.2 | fifo engine |
| T13 | FEE positiva via **CREATE API** | API | **422** rifiutato (Rule 11) | segno < 0 | api transactions |
| T14 | FEE positiva via **IMPORT** | brim | issue strutturata, non persistita | segno < 0 | brim import |
| T15 | FEE positiva via **UPDATE API** | API | **oggi PASSA (bug)** → atteso 422 dopo fix | bypass §5.2 | api transactions |
| T16 | FEE positiva via **ORM diretto** | DB | **oggi PASSA** → atteso violazione CHECK dopo fix | bypass §5.3 | db/migration |
| T17 | TAX positiva (create/update/orm) | tutti | come T13/T15/T16 | segno < 0 | api + db |
| T18 | Plugin BRIM normalizzano `-abs` | brim | tutti negativi | — | brim providers |
| T19 | Audit pool misto BUY+SELL | engine | 2 context sotto 1 gruppo | §6 | fifo engine |
| T20 | Crossing (stesso lotto OPENING+CLOSURE) | engine | 2 lot allocation distinte | §6 | fifo engine |
| T21 | Status DEGRADED locale (orphan cost) | engine | DEGRADED, perimetro = pool | isolabilità | fifo engine |
| T22 | Status FAILED quantitativo (short transfer) | engine | FAILED, no metriche | non isolabile | fifo engine |

Per gli scenari critici gli input numerici sono nei §3.3 e §4.

---

## 9. Verifica delle decisioni chiuse (nessuna riapertura)

Nessuna contraddizione **nuova** emersa contro: adjustment esclusi dal pool trade; pool FEE misto senza warning; DIVIDEND∪INTEREST nel target TAX; previous-day only; audit inline; costo post-chiusura modifica il netto dalla propria data; `original_cost` invariato; qbq hardening via rimozione metodi morti; FIFO assoluto + share nel Portfolio Engine; broker di riconciliazione = broker dell'evento.

Unica precisazione (§4.3): la chiusura "DIVIDEND e INTEREST insieme nel target TAX" **regge** proprio perché l'eleggibilità è type-independent; va però documentata come **precondizione** (se in futuro l'eleggibilità diventasse type-specific, la decisione andrebbe rivista).

---

## 10. Riconciliazione col Portfolio Engine (nota di coerenza target)

Il calcolo in target currency è coerente col Portfolio Engine, che già lavora su somme in target e scala per `share_percentage` (FIFO assoluto, PE per-share). Con Opzione B, gli accumulatori pre-share `per_income_absolute` / `per_fees_absolute` / `per_taxes_absolute` (richiesti dal §31 del piano) ricevono importi **target** dal motore, coerenti con l'aggregazione PE. Nessun nuovo conflitto rispetto a quanto già rilevato in v4-review. La chiave assoluta resta `(asset_id, broker_evento, periodo, currency)`, non il broker di custodia.

---

## 11. Modifiche testuali consigliate a `feasibility-analysis-v4.md`

1. **§FX / decisione target currency**: recepire **Opzione B** esplicitamente e dichiarare il motore *"target-value aware, FX-mechanism agnostic"*, sovrascrivendo la nota v4-review "motore target-agnostic".
2. **§conservazione**: aggiungere il risultato "pesi FX-invarianti dentro pool omogeneo" (§2.1) e la policy "convertire la somma del pool una volta" con residuo running-remainder.
3. **§cross-currency**: fissare **`target_currency` come valuta comune** per `β` quando FEE e trade differiscono di valuta; conversione nel service.
4. **§Pool TAX**: **eliminare** lo scenario "income orphan dentro pool TAX" e la relativa policy α_k→orphan_taxes; sostituire con "pool TAX O interamente allocabile O interamente orphan" (§4.2). Documentare la precondizione §4.3.
5. **§controvalore trade**: confermare `TradeValue = |TransactionAmount|`, con nota esplicita "no scaling qbq" e cancellazione della formula alternativa `(|Q|/QBQ)·quote`.
6. **§Data Quality / segno**: **non** eliminare `ECONOMIC_EVENT_UNEXPECTED_SIGN` finché non sono in essere (1) CHECK DB e (2) validazione update; documentare i due bypass (§5.2, §5.3) come prerequisiti di Fase 0.
7. **§audit**: adottare il DTO a 3 livelli con campi native+target separati e `fx_rate` per gruppo (§6.1).
8. **§status**: separare `analysis_status {COMPLETE,DEGRADED,FAILED}` da `net_metrics_status {AVAILABLE,UNAVAILABLE}`; classificare `ALLOCATION_CONSERVATION_FAILED` come **sempre DEGRADED**.

---

## 12. Criticità residue ordinate per severità

| ID | Sev | Descrizione | Riferimento codice |
|----|-----|-------------|--------------------|
| **R1** | **ALTA** | Bypass segno su UPDATE: `TXUpdateItem` valida solo `id>0`; service scrive `tx.amount` grezzo. FEE/TAX positivi persistibili via API. | `transactions.py:548-558`, `transaction_service.py:1147-1151` |
| **R2** | **ALTA** | Nessun CHECK DB sul segno: ORM diretto / legacy possono violare l'assunzione `amount<0`. Serve migrazione incrementale + verifica dati legacy. | `db/models.py:590-595,615-619` |
| **R3** | MEDIA | La v4 (pre-4.1) prevede lo scenario impossibile income-orphan-in-TAX-pool: complessità inutile in spec/test da rimuovere. | §4.2 |
| **R4** | MEDIA | `calculation_status` binario e `LotCalculationStatus` Literal a 3 valori non coprono ancora {COMPLETE,DEGRADED,FAILED} + `net_metrics_status`. | `fifo_lot_engine.py:198-200`, `schemas/portfolio.py:455` |
| **R5** | BASSA | Cross-currency FEE↔trade: valuta comune non fissata nel testo v4; va esplicitata come `target_currency`. | §2.3 |
| **R6** | BASSA | Precondizione "eleggibilità type-independent" non documentata: se violata in futuro, R3 torna reale. | §4.3 |

---

## 13. Decisioni di prodotto ancora aperte

1. **Enforcement del segno**: solo validazione service sull'update (economica, non copre ORM) **oppure** CHECK DB (forte, richiede gestione dati legacy) **o entrambi**? Raccomandato: **entrambi**.
2. **Rimozione `ECONOMIC_EVENT_UNEXPECTED_SIGN`**: subordinata alla decisione 1. Se si sceglie enforcement end-to-end, rimuovere; altrimenti mantenere il ramo `abs()`+warning.
3. **Modello enum status**: un unico enum a tre stati riusato a due livelli, o due enum separati (analisi vs lotto)? Raccomandato: **due enum separati**.
4. **`fx_rate` nell'audit**: esporlo per gruppo (per riconciliazione target esplicita) o ricalcolarlo lato consumer? Raccomandato: **esporlo**.
5. **Trattamento legacy pre-CHECK**: cosa fare dei record esistenti con segno anomalo (se presenti)? Script di normalizzazione una-tantum o solo report? Da decidere prima della migrazione R2.

---

## 14. Conclusione

**GO CON MODIFICHE.** Le tre decisioni 4.1 sono tecnicamente fondate:

- il **target currency** è coerente e per l'income già implementato; Opzione B lo estende senza duplicare FX e mantenendo l'audit nativo; i pesi sono FX-invarianti nei pool omogenei (drift zero);
- lo **scenario income orphan/allocabile nello stesso pool TAX è impossibile** per costruzione → semplificazione netta di spec e test;
- il **segno FEE/TAX non è garantito end-to-end**: due bypass reali (UPDATE, DB) impongono una correzione minima (CHECK DB + validazione update) **prima** di poter assumere `CostTotal = −Amount` ed eliminare il ramo difensivo.

Le criticità R1/R2 sono le uniche bloccanti per la premessa economica "segno sempre negativo" e vanno risolte in Fase 0 della migrazione. Il resto è coerente e pronto a diventare base del piano implementativo.
