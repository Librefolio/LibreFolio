# FIFO, WAC e trasferimenti tra broker — stato attuale dell'implementazione

> **Stato**: Analisi tecnica completa. Nessuna modifica al codice applicata.
> **Data**: 2026-07-14
> **Scopo**: documentare con precisione (formule, codice citato riga per riga, esempi numerici verificati) come funzionano oggi il motore FIFO, il calcolo WAC e la gestione dei `TRANSFER` tra broker, come base per una eventuale riprogettazione.
> **Documento collegato**: `REPORT-fifo-lots-transfer-mismatch.md` (stessa cartella, analisi precedente più sintetica, focalizzata sui sintomi osservati in UI). Questo documento va più in profondità nel "perché" a livello di codice e formule, e aggiunge almeno un finding non presente nel report precedente (§7.3).

---

## Indice

1. [Creazione, consumo e visualizzazione dei lotti FIFO](#1-creazione-consumo-e-visualizzazione-dei-lotti-fifo)
2. [Vendite complete e parziali: quale lotto viene consumato](#2-vendite-complete-e-parziali-quale-lotto-viene-consumato)
3. [WAC unitario e cost basis totale: verifica della formula](#3-wac-unitario-e-cost-basis-totale-verifica-della-formula)
4. [Quantità frazionarie, valute, FX, commissioni, share_percentage](#4-quantità-frazionarie-valute-fx-commissioni-share_percentage)
5. [TRANSFER OUT/IN, cost_basis_override, vincoli DB, validazioni](#5-transfer-outin-cost_basis_override-vincoli-db-validazioni)
6. [cost_basis_override: costo unitario o totale?](#6-cost_basis_override-costo-unitario-o-totale)
7. [Perché get_lots() ignora i transfer mentre WAC/holdings no](#7-perché-get_lots-ignora-i-transfer-mentre-wacholdings-no)
8. [Comportamento atteso per transfer parziali, multipli, di ritorno, in catena](#8-comportamento-atteso-per-transfer-parziali-multipli-di-ritorno-in-catena)
9. [Confronto opzioni di redesign](#9-confronto-opzioni-di-redesign)
10. [Pro/contro/rischi per ciascuna opzione](#10-procontrorischi-per-ciascuna-opzione)
11. [Ricostruzione passo-passo del caso BTC](#11-ricostruzione-passo-passo-del-caso-btc)
12. [Invarianti, edge case, test necessari](#12-invarianti-edge-case-test-necessari)
13. [Domande aperte e raccomandazione](#13-domande-aperte-e-raccomandazione)

---

## 1. Creazione, consumo e visualizzazione dei lotti FIFO

### 1.1 Il motore puro: `calculate_fifo_lots()`

File: `backend/app/utils/financial/fifo_utils.py` (148 righe totali, funzione pura, nessuna I/O).

**Input**: `list[FIFOTransactionInput]`, dove ogni elemento è:
```python
class FIFOTransactionInput(NamedTuple):
    id: int
    type: str        # SOLO "BUY" | "SELL" — qualunque altro valore viene silenziosamente ignorato
    quantity: Decimal
    price: Decimal    # prezzo unitario
    date: date
```

**Algoritmo** (righe 66-148):
1. Filtra e ordina le transazioni per `(date, id)` crescente — **il filtro `type in ("BUY","SELL")` avviene qui, due volte** (una volta implicitamente nella docstring "the caller is responsible", una volta esplicitamente nella list-comprehension di riga 87-90: `[t for t in transactions if t.type in ("BUY", "SELL")]`). Qualunque altro tipo (incluso `TRANSFER`) passato in input viene scartato **prima ancora di entrare nel ciclo principale**.
2. Mantiene una coda FIFO (`deque`) di lotti aperti: ogni `BUY` viene *appeso in coda* come `[tx, remaining_qty]`.
3. Ogni `SELL` consuma dalla **testa** della coda (il lotto più vecchio), in un ciclo `while sell_qty_remaining > 0`:
   - `matched_qty = min(sell_qty_remaining, buy_remaining)`
   - `realized_pnl = (tx.price - buy_tx.price) * matched_qty` — accumulato in `total_realized_pnl`
   - Se il lotto in testa si esaurisce (`remaining == 0`), viene rimosso dalla coda (`popleft()`)
   - Se la coda è vuota ma restano quantità da vendere → `raise ValueError("... exceeds available bought quantity ...")`
4. Al termine, i lotti rimasti in coda diventano `open_lots` (con `remaining_quantity` residua); i match parziali/completi generano `closed_lots`.

### 1.2 Cosa significa esattamente `N/N` ("quantità residua / quantità iniziale")

Il pannello Open Lots mostra due numeri per ogni lotto:
- **`original_quantity`**: la quantità del `BUY` originale, **immutabile** una volta creato il lotto.
- **`remaining_quantity`**: quanto di quella quantità **non è ancora stato consumato da una SELL** (secondo l'algoritmo FIFO puro sopra descritto).

`0.15 / 0.15` per il caso BTC (vedi §11) significa letteralmente: *"il lotto acquistato con 0.15 BTC non ha ancora subito nessuna SELL"* — **non** "0.15 BTC sono ancora fisicamente su questo broker". Questa distinzione è la radice di tutto il problema analizzato in questo documento: il numero è matematicamente corretto rispetto all'algoritmo FIFO puro (nessuna vendita è avvenuta), ma **non riflette la posizione fisica corrente per broker** quando ci sono stati `TRANSFER`.

### 1.3 Come i lotti arrivano in UI

Catena di chiamata:
```
GET /portfolio/lots
  → PortfolioService.get_lots()                          (backend/app/services/portfolio_service.py:2331)
      → per ciascun broker accessibile:
          → self._get_transactions(broker_id, tx_types=_HOLDING_TYPES, date_to=as_of_date)
          → calculate_fifo_lots(fifo_inputs)              (fifo_utils.py:66)
      → arricchimento con P&L non realizzato usando l'ultimo prezzo di mercato
  → FIFOLotsResponse { open_lots: [OpenLotSchema], closed_lots: [ClosedLotSchema], ... }
      → frontend: FIFOLotsPanel.svelte
          → tabella lotti + BubbleLotTimeline.svelte (una bolla per lotto)
          → AssetWacPriceChart.svelte (linea WAC + linea Market Price)
```

`_HOLDING_TYPES = {TransactionType.BUY, TransactionType.SELL}` (`portfolio_service.py:698`) — **questo è il filtro che esclude i TRANSFER**, spiegato in dettaglio al §7.

Schema di risposta (`backend/app/schemas/portfolio.py:455-488`):
```python
class OpenLotSchema(BaseModel):
    buy_transaction_id: int
    broker_id: int              # <- SEMPRE il broker del BUY originale, mai aggiornato
    buy_date: date_type
    buy_price: SafeDecimal
    original_quantity: SafeDecimal
    remaining_quantity: SafeDecimal
    unrealized_pnl: Optional[SafeDecimal]
```

---

## 2. Vendite complete e parziali: quale lotto viene consumato

Il metodo è **FIFO puro** (First-In-First-Out) senza eccezioni: si vende sempre a partire dal lotto **più vecchio** con quantità residua > 0.

**Esempio — vendita parziale**:
```
Lotto A: buy 2026-01-10, 10 unità @ 100
Lotto B: buy 2026-02-15, 5 unità @ 130

SELL 2026-03-01, 6 unità @ 150
```
- `matched_qty = min(6, 10) = 6` → consuma 6 unità dal Lotto A (il più vecchio)
- Lotto A: `remaining_quantity = 10 - 6 = 4` (resta APERTO, parzialmente consumato)
- Lotto B: non toccato, resta `5/5`
- `realized_pnl = (150 - 100) * 6 = 300`
- 1 solo `ClosedLot` generato: `{buy_tx=A, sell_tx=..., quantity=6, realized_pnl=300}`

**Esempio — vendita che attraversa due lotti**:
```
SELL 2026-03-01, 12 unità @ 150   (invece di 6)
```
- Primo giro: `matched_qty = min(12, 10) = 10` → Lotto A esaurito (`remaining=0` → `popleft()`), `realized_pnl_A = (150-100)*10 = 500`
- `sell_qty_remaining = 12 - 10 = 2`
- Secondo giro: `matched_qty = min(2, 5) = 2` → Lotto B: `remaining = 5 - 2 = 3`, `realized_pnl_B = (150-130)*2 = 40`
- Risultato: **2 `ClosedLot`** separati (uno per ogni lotto toccato), `total_realized_pnl = 540`
- Lotto B resta aperto con `3/5`

**Vendita che eccede la quantità disponibile** (bug di dati o stock split non riconosciuto):
```python
raise ValueError(f"SELL transaction {tx.id} on {tx.date} exceeds available bought quantity. "
                  "Possible unrecognized stock split or missing BUY transactions.")
```
Questo è un **fail-fast intenzionale**: il sistema preferisce un errore esplicito a un risultato silenziosamente sbagliato (quantità negativa). È rilevante per §12: qualunque redesign che introduca `TRANSFER` come pseudo-SELL deve garantire che la quantità trasferita non superi mai la quantità disponibile sul broker mittente (altrimenti l'errore si propagherebbe in un contesto — il transfer — dove l'utente non se lo aspetta).

---

## 3. WAC unitario e cost basis totale: verifica della formula

### 3.1 Il motore puro: `compute_wac_from_txlist()`

File: `backend/app/utils/financial/wac_utils.py` (157 righe, funzione pura).

**Punto centrale da chiarire**: il WAC **non è calcolato come una formula batch** `Σ(qty×unit_cost)/Σ(qty)` applicata a tutta la storia in un colpo — è calcolato **iterativamente**, transazione per transazione (raggruppate per data, con gli acquisti elaborati prima delle riduzioni nello stesso giorno):

```python
# wac_utils.py righe 78-137 (pseudocodice fedele all'originale)
for ogni transazione, in ordine di data (acquisti prima delle riduzioni nello stesso giorno):
    if quantità > 0:  # acquisizione
        if cost_basis_mode == "auto":
            unit_cost = wac corrente (se pool>0) altrimenti 0   # "add_at_wac" — vedi §7
        elif unit_cost_convertito è fornito:
            unit_cost = quel valore
        else:
            unit_cost = 0
        nuova_qty = qty_pool + qty_tx
        if nuova_qty > 0:
            wac = (wac_vecchio × qty_pool + unit_cost × qty_tx) / nuova_qty
    else:  # riduzione (vendita)
        unit_cost = wac corrente  # esce AL costo medio, il WAC non cambia
        nuova_qty = qty_pool + qty_tx  # qty_tx è negativo
        if nuova_qty == 0: wac = 0
        elif nuova_qty < 0: wac = 0, qty_pool = 0  # clamp di sicurezza (errore di arrotondamento)
    qty_pool = nuova_qty
```

### 3.2 Verifica formale: è davvero una media ponderata?

**Sì, ma solo lungo una sequenza di pure acquisizioni** (nessuna vendita nel mezzo). La formula iterativa
```
wac_n = (wac_{n-1} × qty_pool_{n-1} + unit_cost_n × qty_n) / (qty_pool_{n-1} + qty_n)
```
è la **definizione ricorsiva standard** di una media ponderata cumulativa. Si dimostra per induzione che, per una sequenza di *k* acquisizioni pure, il risultato finale è algebricamente identico a:
```
WAC = Σ(i=1..k) [qty_i × unit_cost_i] / Σ(i=1..k) [qty_i]
```
**Esempio numerico** (valori rotondi per chiarezza; nella §11 uso i valori reali del caso BTC):
```
Acquisto 1: 10 unità @ 100  → totale 1000
Acquisto 2:  5 unità @ 130  → totale  650

Formula batch:     WAC = (10×100 + 5×130) / (10+5) = 1650 / 15 = 110.00

Formula iterativa:
  step 1 (buy 10@100): qty_pool=10, wac=100.00
  step 2 (buy  5@130): nuova_qty=15
                        wac = (100.00×10 + 130×5) / 15 = 1650/15 = 110.00   ✓ IDENTICO
```

**Cosa succede quando si mescolano vendite**: una `SELL` **non cambia il WAC** (esce al costo medio corrente, quindi il "peso" della vendita è neutro sul WAC restante) — questo è il comportamento contabile standard "costo medio ponderato in continuo" (non "costo medio storico su tutti gli acquisti mai fatti"). Continuando l'esempio:
```
SELL 6 unità @ 140 (prezzo di mercato, irrilevante per il WAC):
  tx_cost = wac corrente = 110.00 (non il prezzo di vendita!)
  nuova_qty = 15 - 6 = 9
  wac = (110.00×15 - 110.00×6) / 9 = (1650 - 660) / 9 = 990/9 = 110.00   ← INVARIATO, corretto
  realized_pnl (calcolato altrove, non in questa funzione) = (140 - 110.00) × 6 = 180

BUY 5 unità @ 150 (nuovo acquisto dopo la vendita):
  nuova_qty = 9 + 5 = 14
  wac = (110.00×9 + 150×5) / 14 = (990 + 750) / 14 = 1740/14 = 124.2857...
```
Da questo momento, **`WAC = Σ(qty×unit_cost)/Σ(qty)` NON è più verificabile su "tutti gli acquisti mai fatti"** (10@100 + 5@130 + 5@150 diviso 20 darebbe 122.50, diverso da 124.29) — è verificabile solo sul **pool residuo attuale**, che è esattamente ciò che un WAC/costo-medio-ponderato-in-continuo deve fare per definizione contabile. **Conclusione: la formula richiesta dall'utente è corretta e verificata, con la precisazione che si applica al pool corrente, non alla storia grezza non filtrata dalle vendite.**

### 3.3 Cost basis totale

Il "cost basis totale" di una posizione aperta è semplicemente:
```
cost_basis_totale = WAC_unitario × quantità_residua_pool
```
Calcolato es. in `portfolio_engine.py:1006`: `ocb_local = wac_val * qty` (vedi §7.3 per il contesto completo).

### 3.4 Riduzioni "in eccesso" (clamp di sicurezza)

```python
else:
    # Negative (rounding error) → clamp to 0
    wac = Decimal("0")
    new_qty = Decimal("0")
```
A differenza di `calculate_fifo_lots()` (che **rilancia un'eccezione** se una SELL eccede la quantità disponibile), `compute_wac_from_txlist()` **silenzia** il caso (qty diventa negativa per un errore di arrotondamento) azzerando pool e WAC. Le due funzioni hanno quindi **filosofie diverse di fronte allo stesso tipo di anomalia** — un punto da armonizzare in un eventuale redesign (§12).

---

## 4. Quantità frazionarie, quote intere, valute, FX, commissioni, `share_percentage`

### 4.1 Quantità frazionarie vs intere

Colonna DB: `quantity: Decimal` con `sa_column=Column(Numeric(18, 6))` (`backend/app/db/models.py:603-607`) — **6 decimali per qualunque asset**, azioni comprese. Non esiste, a livello di schema o validazione, alcun vincolo che forzi quantità intere per un tipo di asset e frazionarie per un altro (es. azioni vs crypto). Il sistema tratta **0.15 BTC e 15.0 azioni AAPL con la stessa identica precisione decimale** — nessuna logica speciale "azioni frazionarie" o "solo lotti interi". `quantity_sign` (`backend/app/schemas/transactions.py:1018`) vincola solo il **segno** consentito (positivo/negativo/qualunque/diverso da zero) in base al tipo di transazione, non la granularità.

### 4.2 Valute e FX nel WAC

Il WAC è calcolato in una **`target_currency`** determinata da `determine_target_currency()` (`wac_utils.py:51-61`):
```python
def determine_target_currency(txs, asset_currency):
    acquisizioni = [tx per tx con qty > 0]
    if non ci sono acquisizioni: return asset_currency
    return valuta dell'acquisizione più recente   # regola deterministica
```
Se una transazione di acquisto è in una valuta diversa dalla `target_currency`, il layer di preparazione (`compute_wac_iterative`, `portfolio_service.py:191-234`) chiama `convert_bulk()` (servizio FX) **alla data della transazione**, prima di passare i costi convertiti alla funzione pura. Ogni "riga qualificante" (`WACQualifyingTX`) conserva sia il costo originale che quello convertito, più metadati di staleness FX (`fx_rate_date`, `fx_days_back`) per trasparenza.

**Esempio dal mock data reale**: AAPL comprato su Directa in EUR mentre l'asset è nativamente in USD → il sistema convertirà l'importo EUR in USD (o nella valuta target scelta) usando il tasso FX della data di acquisto, PRIMA di combinarlo nel pool WAC.

### 4.3 Commissioni (fee)

**Non esiste un meccanismo automatico che sottragga una fee separata dal costo di un lotto specifico.** Osservate due modalità distinte, entrambe supportate ma con effetti opposti sul WAC:

1. **Fee inclusa nell'importo della transazione** (bundling manuale): es. nei dati mock, `backend/test_scripts/test_db/populate_mock_data.py` riga ~1062: `"amount": Decimal("-2633.50"),  # 15 * 175.50 + 1.00 fee` con `"fee": Decimal("1.00")` — la funzione `_derive_market_amount()` (righe 122-145) SOMMA la fee al costo lordo (`gross + fee_amount`) prima di scrivere `amount`. In questo caso **la fee entra a far parte del `unit_cost` del lotto** (`unit_cost = abs(amount)/qty` includerà la fee media per unità).
2. **Fee come transazione separata** (`TransactionType.FEE`): tracciata in `_FEE_TAX_TYPES = {FEE, TAX}` (`portfolio_service.py:1003,1623`), **esclusa esplicitamente** da `_HOLDING_TYPES`/`_QTY_TYPES` — contribuisce solo al saldo di cassa e alla colonna "Costs" nel report periodo, **non tocca in alcun modo il WAC o il cost basis del lotto**.

La scelta tra le due modalità è **lasciata all'utente** in fase di inserimento — non c'è enforcement automatico di una policy unica.

### 4.4 `share_percentage` (comproprietà broker)

Verificato per assenza: **`share_percentage` non appare né in `wac_utils.py` né in `compute_wac_iterative()`/`compute_wac_iterative_multi_broker()`** (grep esaustivo, zero occorrenze). Appare invece in:
- `portfolio_service.py:1007,1638` — dentro `get_positions_contribution()` e il metodo affine per il report periodo, dove **ogni importo/quantità viene moltiplicato per `share` DOPO essere stato ottenuto dal calcolo grezzo** (`broker_cash[tx.currency] += tx.amount * share`, `qty_at_start += q * share`).
- `portfolio_engine.py` — passato come `ctxn.share` nel classificatore di transazioni (`ScopeAwareTransactionClassifier`), applicato quando si accumulano i pool WAC per-broker (`tx_qty = tx.quantity * ctxn.share`, riga ~587).

**Conclusione verificata**: il WAC (**prezzo unitario**) è calcolato sulla quantità e sul costo **assoluti** (100%) del broker; la quota di comproprietà si applica **solo alla quantità aggregata visualizzata** (holdings, contribution), non al prezzo medio stesso — logicamente corretto: se possiedo il 30% di un broker che ha comprato 10 azioni a 100, il MIO WAC per unità resta 100 (il prezzo pagato per azione non cambia in base a quante azioni "mi spettano"), ma la MIA quantità visualizzata è 10×0.3=3 e il MIO costo totale visualizzato è 3×100=300.

---

## 5. `TRANSFER OUT/IN`, `cost_basis_override`, vincoli DB, validazioni business

### 5.1 Struttura dati

Dal modello (`backend/app/db/models.py:557-662`):
```python
class Transaction(SQLModel, table=True):
    quantity: Decimal          # segnato: + in, - out
    amount: Decimal            # segnato: + in, - out — per TRANSFER è sempre 0
    related_transaction_id: Optional[int]   # collega le due gambe della coppia, FK bidirezionale DEFERRABLE
    cost_basis_override: Optional[Decimal]  # "Frozen cost basis for TRANSFER_IN"
    cost_basis_currency: Optional[str]      # valuta di cost_basis_override, sempre insieme (entrambi null o entrambi set)
```
Regola di semantica documentata direttamente nel modello (righe 576-579):
> `TRANSFER`: `quantity != 0`, `amount = 0`, `related_transaction_id` **REQUIRED**

### 5.2 Vincoli e validazioni verificate nel codice

| Regola | Dove | Comportamento |
|---|---|---|
| Le due gambe devono avere lo stesso `type` | `_validate_linked_pair()`, `transaction_service.py:244-274` | Errore `pairTypeMismatch` se mescolati (es. TRANSFER + SELL) |
| `TRANSFER` richiede broker diversi | stesso metodo, riga ~263 | Errore `pairSameBroker` — un transfer sullo stesso broker è un no-op rifiutato |
| Descrizione e tag identici sulle due gambe | `_validate_pair_description_tags()`, righe ~277-299 | Errore `pairDescriptionMismatch` / `pairTagsMismatch` |
| Quantità opposte (`qty_a == -qty_b`) | riga 848 (in un validatore generico di compatibilità, usato anche per suggerimenti di promote) | Se non opposte, la coppia non è considerata compatibile |
| Saldo asset non negativo per broker/giorno | "balance walk" — `transaction_service.py:440-508` | **Itera giorno per giorno, sommando `tx.quantity` per QUALUNQUE tipo (nessun filtro `_HOLDING_TYPES`)** — se il saldo per un asset scende sotto zero in un broker che non permette shorting (`allow_asset_shorting=False`), l'intero batch viene rifiutato con `BalanceValidationError`. **Nota**: questo controllo, a differenza di `get_lots()`, GIÀ include correttamente i TRANSFER nella somma — un'ulteriore controprova che l'esclusione dei transfer in `get_lots()` è un'anomalia isolata, non un pattern architetturale diffuso. |
| `cost_basis_override` richiesto per `TRANSFER` con `quantity > 0` | `_requires_cost_basis()`, riga 234-242 | Se non impostato, errore `"{type} with qty>0 requires cost_basis_override"` (righe 1452-1498) |

### 5.3 Propagazione del WAC al momento del transfer — l'architettura "snapshot"

Questo è il meccanismo più importante per capire come il sistema **già** gestisce (parzialmente) i transfer per WAC e holdings, pur non gestendoli in `get_lots()`.

Docstring del campo, testuale (`models.py:648-653`):
> *"Frozen cost basis for TRANSFER_IN transactions. When set, this value is used as acquisition price instead of calculating from source broker history. Enables 'snapshot' architecture for transfers: Backend calculates PMC on source broker at transfer time, Saves it here so destination broker never needs to query source history. Can be manually overridden (e.g., Exit Tax, inheritances use market value)."*

Implementazione, `_compute_wac_for_auto_items()` (`transaction_service.py:1533-1620`), eseguita **al momento della creazione** della coppia TRANSFER (quando la gamba IN ha `cost_basis_mode in ("auto","auto-detail")`):
```python
# Determina il broker sorgente = broker della gamba OUT (via link_uuid)
source_broker_id = self._resolve_source_broker_from_link(...)

# Calcola il WAC del broker sorgente ALLA DATA del transfer
wac_result = await compute_wac_iterative(
    broker_id=source_broker_id, asset_id=..., as_of_date=db_tx.date, ...
)

# Congela il risultato sulla gamba IN, per sempre (fino a modifica manuale)
db_tx.cost_basis_override = wac_result.wac.amount     # PER-UNIT
db_tx.cost_basis_currency = wac_result.wac.code
```
**Punto critico**: questo è un calcolo **one-shot, eseguito una sola volta alla creazione**. Se in seguito il WAC storico del broker sorgente cambia (es. l'utente corregge una BUY passata), **il valore congelato in `cost_basis_override` NON si aggiorna automaticamente** — è "frozen" esattamente come documentato. Questo è presumibilmente intenzionale (architettura "snapshot" per evitare che il broker destinazione debba ricalcolare sempre a ritroso), ma va tenuto presente come comportamento noto, non come bug.

---

## 6. `cost_basis_override`: costo unitario o totale?

**Verificato in tre punti di codice indipendenti — è sempre trattato come COSTO UNITARIO (per-unit), mai totale:**

**Punto 1** — `compute_wac_iterative()`, `portfolio_service.py:255-262`:
```python
elif cbo_amt is not None:
    if i in fx_converted:
        unit_cost = fx_converted[i] / qty       # diviso per qty DOPO la conversione FX
    else:
        unit_cost = cbo_amt                      # <-- usato DIRETTAMENTE come unit_cost, nessuna divisione
```
E per la conversione FX (riga 205): `cost = qty * cbo_amt` — si moltiplica per `qty` per ottenere il totale da convertire, poi si **ridivide per `qty`** dopo la conversione (riga 257) per tornare a un valore per-unità. Questa andata-e-ritorno ha senso matematico **solo se `cbo_amt` era già un valore per-unità in partenza**.

**Punto 2** — `PortfolioEngine._buy_unit_cost()`, `portfolio_engine.py:1230-1233`:
```python
elif tx.cost_basis_override is not None:
    # TRANSFER with cost_basis_override
    total_cost = tx.cost_basis_override * qty    # <-- MOLTIPLICATO per qty per ottenere il TOTALE
    cost_ccy = tx.cost_basis_currency or asset_ccy
```
Stessa logica, prospettiva opposta: se `cost_basis_override` fosse già un totale, moltiplicarlo per `qty` darebbe un numero senza senso (un "totale al quadrato"). La moltiplicazione ha senso solo se `cost_basis_override` è un valore **per-unità**.

**Punto 3** — Il meccanismo di scrittura (`transaction_service.py:1601-1604`):
```python
if wac_result.wac:
    db_tx.cost_basis_override = wac_result.wac.amount   # wac.amount è un WACCalcResult.wac_amount,
                                                          # documentato come "per-unit WAC in target_currency"
```

**Conclusione univoca: `cost_basis_override` rappresenta sempre un COSTO UNITARIO (prezzo per unità/quota), analogo a `buy_price` in un lotto FIFO — non un costo totale.** Il nome del campo ("cost basis", spesso usato colloquialmente per il costo totale di una posizione) è potenzialmente ambiguo rispetto al suo effettivo significato "prezzo unitario congelato" — possibile spunto di documentazione/naming da chiarire in futuro, ma il comportamento del codice è **coerente e univoco** su questo punto in tutti i punti verificati.

---

## 7. Perché `get_lots()` ignora i transfer mentre WAC/holdings no

### 7.1 La causa esatta

`get_lots()` (`portfolio_service.py:2331-2430`) interroga le transazioni con:
```python
txns = await self._get_transactions(broker_id, tx_types=_HOLDING_TYPES, date_to=as_of_date)
```
dove `_HOLDING_TYPES = {TransactionType.BUY, TransactionType.SELL}` (riga 698) — **filtro esplicito che esclude `TRANSFER` prima ancora di costruire i `FIFOTransactionInput`**. Il motore puro `calculate_fifo_lots()` (§1.1) filtra di nuovo internamente (`type in ("BUY","SELL")`), quindi anche se un `TRANSFER` sfuggisse al primo filtro non verrebbe comunque elaborato — sarebbero necessarie **due modifiche in cascata** per farlo funzionare "naturalmente".

### 7.2 Perché WAC (`compute_wac_iterative`) invece funziona

La query di `compute_wac_iterative()` (`portfolio_service.py:117-123`) **non filtra per tipo**:
```python
stmt = select(Transaction).where(
    Transaction.broker_id == broker_id,
    Transaction.asset_id == asset_id,
    Transaction.date <= as_of_date,
    Transaction.quantity.is_not(None),
    Transaction.quantity != 0,     # <- unico filtro: quantità diversa da zero, NESSUN filtro sul type
)
```
Ogni riga (incluse le `TRANSFER`) viene passata a `compute_wac_from_txlist()`, che gestisce `quantity > 0` con `cost_basis_mode`/`cost_basis_override` (vedi §3, §6) e `quantity < 0` come riduzione generica (uscita al WAC corrente) — **senza mai controllare il campo `type`** per decidere se includere o no una riga. Il TRANSFER è trattato semplicemente come "un'acquisizione con un costo noto" (in entrata) o "una riduzione" (in uscita), esattamente come farebbe con BUY/SELL.

### 7.3 Perché Holdings (`PortfolioEngine`) invece funziona — finding aggiuntivo rispetto al report precedente

`PortfolioEngine`/`DailyStateBuilder` (`portfolio_engine.py`) mantiene un pool WAC per-broker-per-asset **indipendente** da `compute_wac_iterative()` (stessa matematica, codice diverso — un potenziale rischio di divergenza futura se le due implementazioni non vengono mantenute in sync, vedi §12). La selezione delle transazioni rilevanti (riga 483-488):
```python
position_txs_by_date: dict[date_type, list[ClassifiedTransaction]] = defaultdict(list)
for ctxn in self.classified_txs:
    tx = ctxn.tx
    if tx.quantity and tx.quantity != 0 and tx.asset_id is not None:
        position_txs_by_date[tx.date].append(ctxn)
```
**Nessun filtro sul `type`**, esattamente come per il WAC. Il costo unitario per ogni riga viene risolto da `_buy_unit_cost()` (righe 1207-1257, vedi §6 Punto 2), che gestisce esplicitamente sia `BUY` (da `amount`) sia `TRANSFER`-con-`cost_basis_override` (da `cost_basis_override × qty`). Questo è il motore che alimenta `PortfolioSummary.holdings` → `ExposureTable.svelte` → la vista "Holdings/Positions" che nel report precedente avevo verificato mostrare correttamente `0.10`/`0.05` BTC per Coinbase/IB (poi scalati per `share_percentage`).

### 7.4 Finding aggiuntivo non presente nel report precedente: `get_positions_contribution()` ha lo stesso problema di `get_lots()`

Durante questa analisi più approfondita ho verificato che **anche** `get_positions_contribution()` (la funzione dietro "Your Positions"/tab Performance, `portfolio_service.py:1593+`) filtra le transazioni con:
```python
_QTY_TYPES = {TransactionType.BUY, TransactionType.SELL}     # riga 1624
...
if tx.type not in _QTY_TYPES:
    continue                                                  # riga 1678-1679
```
usato per costruire `txns_by_asset` da cui derivano `qty_at_start`/`qty_at_end` (righe ~1747-1754). **Questo significa che, indipendentemente dalla pagina in cui ci si trova (dettaglio broker o dashboard multi-broker), la tabella "Your Positions"/ContributionTable rischia di avere lo stesso tipo di gap di `get_lots()` per un asset trasferito** — non l'ho potuto verificare empiricamente al 100% nel caso concreto (il report precedente attribuiva l'osservazione "solo Coinbase" alla pagina di dettaglio broker, spiegazione che resta valida come causa **primaria** per quel caso specifico, dato che `brokerIds=[broker.id]` filtra a monte), ma è una **seconda area di codice potenzialmente affetta dallo stesso problema strutturale**, che andrebbe testata esplicitamente con un broker multi-transfer sul dashboard (nessun filtro broker attivo) prima di considerare il problema risolto anche lì. Vedi §12 per il test da scrivere.

**Tabella riepilogativa**:

| Componente | Filtra per `type`? | Gestisce TRANSFER? | Verificato |
|---|---|---|---|
| `calculate_fifo_lots()` (motore puro) | Sì, by design | No (compito del chiamante) | ✅ codice letto per intero |
| `get_lots()` (Open Lots / FIFO panel) | Sì (`_HOLDING_TYPES`) | **No — bug confermato** | ✅ codice letto per intero |
| `compute_wac_iterative()` / `compute_wac_from_txlist()` | No | **Sì, correttamente** | ✅ codice letto per intero |
| `PortfolioEngine`/`DailyStateBuilder` (Holdings) | No | **Sì, correttamente** | ✅ codice letto per intero |
| `get_positions_contribution()` ("Your Positions") | Sì (`_QTY_TYPES`) | **Probabile bug analogo, non confermato al 100% su dashboard multi-broker** | ⚠️ codice letto, scenario non testato live |
| Balance-walk validation (saldo non negativo) | No | Sì, correttamente | ✅ codice letto per intero |

---

## 8. Comportamento atteso per transfer parziali, multipli, di ritorno, in catena

Principio generale desumibile dall'architettura "snapshot" già esistente (§5.3): **un transfer non crea né distrugge valore né "invecchia" un lotto — sposta quantità preservando data di acquisto originale e costo unitario originale.**

### 8.1 Transfer parziale (quantità < intero lotto)

```
Lotto su Broker A: buy 2026-01-10, 10 unità @ 100
TRANSFER 3 unità → Broker B, in data 2026-02-01
```
**Atteso**: Broker A resta con `remaining_quantity = 7` sullo stesso lotto (stessa `buy_date`, stesso `buy_price`); Broker B ottiene un **nuovo lotto derivato** con `buy_date = 2026-01-10` (**preservata**, non la data del transfer), `buy_price = 100` (**preservato**), `original_quantity = 3` (o un campo che distingua "originato da transfer" per trasparenza), `remaining_quantity = 3`.

### 8.2 Transfer multiplo (più trasferimenti nel tempo, stesso lotto)

```
Lotto: buy 2026-01-10, 10 unità @ 100
TRANSFER 3 → B (2026-02-01)
TRANSFER 2 → C (2026-03-01)
```
**Atteso**: A resta con 5/10, B con 3/10 (data/prezzo preservati), C con 2/10 (data/prezzo preservati) — **tre "frammenti" dello stesso lotto originale**, ciascuno con la propria quantità residua ma identica identità di costo/data.

### 8.3 Transfer di ritorno (round-trip) — il caso BTC di questo documento

```
Lotto: buy Coinbase 2026-06-18, 0.15 @ P
TRANSFER 0.10 → IB (2026-07-06)
TRANSFER 0.05 → Coinbase (2026-07-10)     [IB → Coinbase, di ritorno]
```
**Atteso**: alla fine, Coinbase ha `0.15 - 0.10 + 0.05 = 0.10` **ancora sullo stesso lotto originale** (stessa data/prezzo), IB ha `0.10 - 0.05 = 0.05` (stessa data/prezzo). **Nessuna nuova "data di acquisto" deve apparire per il ritorno** — il ritorno non è un nuovo acquisto, è la restituzione di un frammento già esistente. Vedi §11 per i numeri esatti.

### 8.4 Transfer in catena (A→B→C dello stesso frammento)

Se il frammento trasferito a B viene poi ri-trasferito da B a C, il frammento su C deve **ereditare** la stessa data/prezzo originali di A (**non** la data in cui è arrivato su B) — la "catena" di trasferimenti è trasparente rispetto all'identità del lotto. Questo è già implicitamente garantito dall'architettura "snapshot" per il WAC (il `cost_basis_override` su C, se calcolato in modalità `auto`, interrogherebbe il WAC di B **alla data del secondo transfer**, che a sua volta rifletterebbe il costo ereditato da A) — ma **solo se nessuna vendita o riacquisto a prezzo diverso è avvenuto su B nel frattempo**. Se B ha anche comprato altre unità a prezzo diverso prima di ritrasferire, il pool WAC di B si sarebbe already "mescolato" (media ponderata) — a quel punto anche il comportamento CORRETTO per un lotto-based FIFO diventerebbe ambiguo: **quale "lotto" specifico si sta trasferendo da un pool misto?** Questo è un limite intrinseco di qualunque soluzione lotto-per-lotto in presenza di pool WAC aggregati — va deciso esplicitamente (§13, domande aperte).

---

## 9. Confronto opzioni di redesign

### 9.1 Opzione A — Redistribuzione post-FIFO (per-broker, poi redistribuita)

Si lascia `get_lots()` calcolare i lotti per-broker come oggi (solo BUY/SELL, motore puro invariato), poi si applica **un passo aggiuntivo** che, per ogni coppia di `TRANSFER` collegata (`related_transaction_id`), sposta quota dei lotti aperti dal broker mittente al broker destinatario, **consumando FIFO** (stesso algoritmo di consumo di una SELL) dal mittente e **creando/estendendo** un lotto sul destinatario con la stessa `buy_date`/`buy_price` del lotto consumato.

### 9.2 Opzione B — FIFO globale cross-broker con broker "corrente" mutabile

Si esegue **un solo** `calculate_fifo_lots()` per l'intero asset, con **tutte** le transazioni BUY/SELL/TRANSFER di **tutti** i broker accessibili insieme, ordinate per data. Ogni lotto aperto porta con sé un attributo `current_broker_id` che viene **aggiornato** (non consumato) quando si incontra un evento di TRANSFER che lo riguarda.

### 9.3 Opzione C — Pseudo-SELL / pseudo-BUY non economici

Si trasforma ogni `TRANSFER OUT` in un `FIFOTransactionInput` sintetico di tipo `"SELL"` con **prezzo = prezzo di acquisto del lotto che si sta consumando** (quindi `realized_pnl = 0` per costruzione — "vendita a costo", nessun realizzo) sul broker mittente, e ogni `TRANSFER IN` in un `"BUY"` sintetico con **prezzo = `cost_basis_override`** (già disponibile, già calcolato con l'architettura snapshot esistente) e **data = data originale del lotto sorgente** (non la data del transfer) sul broker destinatario.

**Nota tecnica importante**: `FIFOTransactionInput.price` è un valore **singolo per transazione**, ma un `TRANSFER OUT` può, in teoria, attraversare **più lotti con prezzi diversi** (come una SELL che attraversa due lotti, §2). Per garantire *zero* realizzo su OGNI lotto toccato (non solo in media), l'Opzione C richiede di **scomporre** un singolo `TRANSFER OUT` in più pseudo-SELL sintetiche, una per ciascun lotto effettivamente consumato, ciascuna al prezzo esatto di quel lotto — informazione disponibile solo eseguendo prima un "dry run" del FIFO per sapere quali lotti verrebbero toccati.

---

## 10. Pro/contro/rischi per ciascuna opzione

| Criterio | A — Redistribuzione post-FIFO | B — FIFO globale cross-broker | C — Pseudo-SELL/BUY non economici |
|---|---|---|---|
| **Modifica al motore puro `calculate_fifo_lots()`** | Nessuna | Nessuna (stesso motore, input diverso) | Nessuna (stesso motore, input arricchito) |
| **Modifica a `get_lots()`** | Media (nuovo passo di post-processing) | Alta (cambia il modo di interrogare/raggruppare le transazioni) | Media (nuovo passo di preparazione input, prima della chiamata al motore) |
| **Coerenza con l'architettura WAC/Holdings esistente** | Media — logica nuova, non riusa pattern esistenti | Bassa — introduce un modello concettuale diverso ("un lotto può cambiare broker") che non esiste altrove nel codice | **Alta — ricalca esattamente il pattern già usato da `compute_wac_iterative()`/`PortfolioEngine` (TRANSFER trattato come acquisizione/riduzione con costo noto)** |
| **Perdita informativa** | Bassa (si conservano `buy_date`/`buy_price` originali) | Bassa (idem) | Bassa, **ma solo se si implementa la scomposizione multi-lotto** (altrimenti rischio di P&L≠0 su transfer che attraversano più lotti a prezzi diversi) |
| **Rischi fiscali/contabili** | Basso, se la redistribuzione preserva `buy_date` (rilevante per holding period/plusvalenze a lungo termine in molte giurisdizioni) | Medio — il concetto di "broker corrente mutabile" su un lotto potrebbe confondersi con un evento realizzativo se non documentato con chiarezza per gli utenti/contabili | Basso, a condizione di garantire `realized_pnl=0` rigorosamente su ogni lotto (vedi nota tecnica §9.3) |
| **Impatto su broker scope (`brokerIds` filter)** | Nessuno — il filtro per broker continua a funzionare sul risultato finale già redistribuito | Richiede ri-filtrare DOPO il calcolo globale (oggi il filtro avviene PRIMA, per query) — piccolo cambio di flusso | Nessuno — l'input arricchito è già scoped per broker prima di chiamare il motore, come oggi |
| **Impatto su comproprietà (`share_percentage`)** | Nessuno — si applica a valle come oggi (§4.4) | Nessuno, stesso discorso | Nessuno, stesso discorso |
| **Rischio di regressione sui test esistenti** | Basso — cambio isolato in un solo metodo | Alto — cambia la query e la struttura dati di partenza di `get_lots()`, superficie di test più ampia | Basso-medio — richiede gestire con cura il caso multi-lotto (rischio se non testato a fondo) |
| **Coerenza concettuale "un lotto = un evento di acquisto immutabile"** | Sì — il lotto originale non "si muove", si redistribuisce la sua quantità residua tra rappresentazioni broker-specifiche | Discutibile — un lotto che "cambia broker" nel tempo è concettualmente più vicino a "un lotto che si muove", meno immutabile | Sì — coerente con "ogni riga della coda FIFO ha origine (broker, data, prezzo) propria" |
| **Sforzo di implementazione stimato** | Medio | Alto | Medio (con l'accortezza della scomposizione multi-lotto) |

**Osservazione trasversale**: le opzioni A e C sono concettualmente molto vicine (entrambe post-processano/arricchiscono senza toccare il motore puro); la differenza principale è **dove** avviene la logica di "trasferimento" (fuori dal motore FIFO per A, dentro il flusso di input per C). L'opzione C ha il vantaggio di **riusare direttamente e testualmente lo stesso pattern già dimostrato corretto** in `compute_wac_iterative()`/`PortfolioEngine._buy_unit_cost()` (TRANSFER trattato come "acquisizione con costo noto da `cost_basis_override`"), il che la rende, sulla carta, l'opzione con il **minor rischio di introdurre un terzo modello di calcolo divergente** dai due già esistenti.

---

## 11. Ricostruzione passo-passo del caso BTC

### 11.1 Dati di partenza (DB di test, popolamento standard)

```
id  type      date        quantity  amount     broker
22  BUY       2026-06-18   0.15     -1130.38    Coinbase
29  TRANSFER  2026-07-06  -0.10      0.00       Coinbase   (↔ 30)
30  TRANSFER  2026-07-06  +0.10      0.00       Interactive Brokers
37  TRANSFER  2026-07-10  -0.05      0.00       Interactive Brokers (↔ 38)
38  TRANSFER  2026-07-10  +0.05      0.00       Coinbase
```
Prezzo unitario del BUY: `1130.38 / 0.15 = 7535.8666...` ≈ **7535.87 USD/BTC** (fonte: `_derive_market_amount()`, prezzo storico simulato del 2026-06-18 — vedi `REPORT-fifo-lots-transfer-mismatch.md` §2.3 per il contesto sull'instabilità della fonte prezzi esterna, non rilevante per questa ricostruzione).

### 11.2 Cosa succede OGGI (comportamento attuale, verificato)

**`get_lots()` con `brokerIds=[Coinbase]`**:
- Query `_get_transactions(Coinbase, tx_types={BUY,SELL})` → **solo** la riga `id=22` (BUY). Le righe `29` e `38` (TRANSFER su Coinbase) sono escluse dal filtro.
- `calculate_fifo_lots([BUY 0.15@7535.87])` → 1 open lot: `original_quantity=0.15, remaining_quantity=0.15`.
- **Risultato mostrato**: `0.15 / 0.15`, broker=Coinbase. ❌ **Non riflette che 0.05 BTC sono stati ritrasferiti fuori e poi rientrati per un netto di 0.10 residenti fisicamente qui, e soprattutto non riflette che 0.05 sono attualmente su IB.**

**`get_lots()` con `brokerIds=[Interactive Brokers]`**:
- Query `_get_transactions(IB, tx_types={BUY,SELL})` → **nessuna riga** (righe `30` e `37` sono TRANSFER, escluse).
- `asset_txns` vuoto → `continue` → **zero lotti prodotti per IB.**
- **Risultato mostrato**: nessuna riga, nessuna bolla per IB. ❌ **IB detiene realmente 0.05 BTC (via transfer) ma il pannello non mostra nulla.**

### 11.3 Cosa succede OGGI per WAC e Holdings (per confronto — questi SONO corretti)

**`compute_wac_iterative(broker_id=Coinbase, asset_id=BTC)`**: include righe `22, 29, 38` (nessun filtro tipo).
- `22` (BUY, qty=+0.15): pool passa da 0 a 0.15, wac=7535.87
- `29` (TRANSFER OUT, qty=-0.10): riduzione, esce al wac corrente (7535.87) → pool=0.05, wac invariato=7535.87
- `38` (TRANSFER IN, qty=+0.05): se `cost_basis_mode="auto"`, `cost_basis_override` ≈ WAC di IB alla data 2026-07-10 (che a sua volta discende dal transfer `30`, quindi ≈7535.87 anch'esso, dato che IB non ha fatto altro nel frattempo) → pool=0.10, wac **resta** 7535.87 (nessun realizzo, nessuna variazione di costo)
- **WAC Coinbase risultante: 7535.87, quantità 0.10** ✅ corretto.

**`compute_wac_iterative(broker_id=IB, asset_id=BTC)`**: include righe `30, 37`.
- `30` (TRANSFER IN, qty=+0.10, `cost_basis_override`≈7535.87): pool=0.10, wac=7535.87
- `37` (TRANSFER OUT, qty=-0.05): riduzione al wac corrente → pool=0.05, wac invariato=7535.87
- **WAC IB risultante: 7535.87, quantità 0.05** ✅ corretto.

### 11.4 Cosa CI SI ASPETTEREBBE da `get_lots()` corretto (con una delle opzioni §9)

| Broker | buy_date (preservata) | buy_price (preservato) | remaining_quantity |
|---|---|---|---|
| Coinbase | 2026-06-18 (originale, non 2026-07-10 del ritorno) | 7535.87 | **0.10** |
| Interactive Brokers | 2026-06-18 (originale, non 2026-07-06 del transfer) | 7535.87 | **0.05** |

**Somma delle quantità residue attese: 0.10 + 0.05 = 0.15**, identica alla quantità originale — **nessuna quantità creata o persa**, solo correttamente distribuita. Il P&L non realizzato totale, calcolato con un unico prezzo di mercato corrente su queste due righe (0.10 + 0.05), deve essere identico a quello calcolabile oggi con l'unico lotto errato da 0.15 — cambia **solo l'attribuzione per broker**, non il totale.

---

## 12. Invarianti, edge case, test necessari

### 12.1 Invarianti che qualunque redesign deve preservare

1. **Conservazione della quantità**: `Σ(remaining_quantity per tutti i broker) == Σ(original_quantity dei lotti mai creati) − Σ(quantità vendute via SELL)`, indipendentemente da quanti TRANSFER sono avvenuti nel mezzo.
2. **Neutralità di P&L del TRANSFER**: nessun `TRANSFER` deve generare `realized_pnl != 0` (a meno che l'utente non abbia esplicitamente impostato un `cost_basis_override` manuale diverso dal WAC sorgente — es. per finalità fiscali specifiche come "Exit Tax", che è un caso *voluto* di scostamento, non un bug).
3. **Preservazione di `buy_date`/`buy_price` originali attraverso qualunque numero di transfer** (§8.2-8.4) — rilevante per il calcolo dei giorni di possesso (holding period) mostrato nelle bolle (vedi report precedente, punto 6) e per eventuali normative fiscali basate sulla durata di possesso.
4. **Idempotenza rispetto all'ordine di calcolo per broker**: il risultato aggregato (su tutti i broker) non deve dipendere dall'ordine in cui i broker vengono elaborati.
5. **Compatibilità con `share_percentage`**: la redistribuzione dei lotti deve avvenire su quantità **assolute** (100%), con la quota applicata solo alla visualizzazione finale — mai moltiplicare per `share` dentro il motore FIFO stesso (coerente con quanto già verificato per il WAC, §4.4).
6. **Nessuna doppia contabilizzazione cross-broker**: la somma dei lotti aperti su tutti i broker per un asset deve sempre coincidere con la quantità totale netta (BUY − SELL, i TRANSFER si annullano a somma zero per definizione).

### 12.2 Edge case da testare esplicitamente

- Transfer che coincide **esattamente** con la quantità residua di un lotto (nessun frammento parziale).
- Transfer che attraversa **più lotti con prezzi diversi** (nota tecnica §9.3) — verificare che il realizzo resti zero su ciascuno.
- Transfer **di ritorno** (round-trip, come nel caso BTC) — verificare che non si creino "duplicati" di data di acquisto.
- Transfer **in catena** (A→B→C) con un acquisto aggiuntivo su B nel mezzo (ambiguità di attribuzione, §8.4) — comportamento da **decidere esplicitamente**, non lasciare indefinito.
- `TRANSFER OUT` che eccede la quantità disponibile sul broker mittente (deve fallire in modo controllato, coerente con `BalanceValidationError` già esistente — non silenziosamente clampare come fa oggi `compute_wac_from_txlist` per le riduzioni in eccesso, §3.4).
- `cost_basis_override` **manuale** (non `auto`) diverso dal WAC sorgente calcolato — verificare che il redesign rispetti il valore impostato dall'utente senza sovrascriverlo.
- Asset con **prezzo mancante** alla data di valutazione (nessun impatto diretto sui lotti, ma sul P&L non realizzato mostrato — verificare che il fallback esistente, es. `LAST_BUY_PRICE` in `PortfolioEngine`, resti coerente anche per lotti "redistribuiti").
- **`get_positions_contribution()`** con un asset trasferito, filtro broker disattivato (dashboard) — verificare se il finding §7.4 è un bug reale o se altre parti del flusso compensano.
- FX: transfer tra broker con asset in valute diverse dalla valuta di reporting, con tassi di cambio diversi alle due date coinvolte (data transfer OUT vs data eventuale successivo transfer di ritorno).

### 12.3 Test da scrivere prima di qualunque implementazione (contratto)

1. Test unitario sul motore puro (se arricchito, Opzione C) o su un nuovo helper di redistribuzione (Opzione A): dato un set di transazioni BUY + TRANSFER note, verificare l'esatta attribuzione per broker attesa (replicare i numeri di §11.4).
2. Test di integrazione su `get_lots()`: stesso scenario, verificato end-to-end via il servizio.
3. Test di regressione su `get_positions_contribution()` per il finding §7.4, con scenario dashboard multi-broker (nessun filtro `brokerIds`).
4. Test E2E frontend: verificare che `BubbleLotTimeline` mostri una bolla per **ciascun broker coinvolto** in un transfer.
5. Test di non-regressione sui casi **senza** transfer (BUY/SELL puri) — verificare che il comportamento esistente, oggi corretto, non cambi in alcun modo.

---

## 13. Domande aperte e raccomandazione

### 13.1 Domande aperte (da risolvere prima di implementare, non tecniche ma di prodotto/policy)

1. **Attribuzione in caso di pool misto** (§8.4): se il broker che riceve un transfer ha *già* un pool WAC misto (acquisti propri + transfer precedenti a prezzi diversi), un successivo transfer OUT da quel broker consuma "il lotto più vecchio in assoluto" (FIFO puro cross-origine) o serve un criterio diverso (es. LIFO, o "consuma prima i frammenti arrivati per transfer")? Il sistema attuale non ha bisogno di rispondere a questa domanda perché non traccia lotti multi-origine — un redesign lotto-based dovrà farlo esplicitamente.
2. **Naming/documentazione di `cost_basis_override`**: il nome suggerisce "costo totale" a un lettore non avvertito, mentre è sempre un valore per-unità (§6). Vale la pena rinominare il campo (rischio: migrazione DB, impatto su codice/schemi esistenti) o basta rafforzare la documentazione inline?
3. **Doppia implementazione WAC** (`compute_wac_iterative()` in `portfolio_service.py` vs il pool WAC dentro `PortfolioEngine`): sono matematicamente equivalenti ma sono **due implementazioni di codice separate**. Un redesign dei lotti FIFO dovrebbe riusare una delle due come riferimento unico, o è accettabile mantenerle separate perché servono scopi diversi (preview interattivo vs calcolo batch dell'intero portafoglio)?
4. **`get_positions_contribution()`** (§7.4): merita una fix nello stesso intervento di `get_lots()`, o va trattato come un secondo problema separato con priorità propria, dato che non è stato ancora confermato empiricamente sul dashboard multi-broker?
5. **Comportamento in caso di errore** (SELL/TRANSFER che eccede la quantità disponibile): armonizzare il "fail-fast" di `calculate_fifo_lots()` con il "clamp silenzioso" di `compute_wac_from_txlist()` (§3.4), oppure lasciare le due funzioni con filosofie diverse perché usate in contesti diversi (preview vs storico consolidato)?
6. **Retroattività**: se si implementa la redistribuzione, deve applicarsi anche a transfer storici già esistenti nel DB (probabile sì, dato che i dati sorgente — TRANSFER con `related_transaction_id` — sono già completi e non richiedono migrazione), o solo a nuovi transfer da questo punto in avanti?

### 13.2 Raccomandazione motivata

**Tra le tre opzioni analizzate (§9-10), l'Opzione C (pseudo-SELL/pseudo-BUY non economici) appare la più coerente con l'architettura esistente**, per tre motivi verificati nel codice:

1. **Riusa un pattern già dimostrato corretto**: sia `compute_wac_iterative()` sia `PortfolioEngine._buy_unit_cost()` già trattano un `TRANSFER IN` come "un'acquisizione con costo noto da `cost_basis_override`" e un `TRANSFER OUT` come "una riduzione neutra sul costo" — esattamente il modello che l'Opzione C propone di applicare anche al motore FIFO. Non si inventa un terzo paradigma di calcolo (rischio evitato: 3 implementazioni divergenti di uno stesso concetto).
2. **Non richiede toccare il motore puro `calculate_fifo_lots()`** (ben isolato, testato, usato altrove) — la trasformazione avviene nel layer di preparazione dati, come già fa `get_lots()` oggi per costruire i `FIFOTransactionInput`.
3. **`cost_basis_override` è già disponibile e calcolato correttamente** al momento della creazione del transfer (architettura "snapshot", §5.3) — l'Opzione C può limitarsi a **leggerlo**, senza dover reinventare un calcolo di WAC-al-momento-del-transfer che già esiste altrove nel sistema.

**Riserva importante**: la nota tecnica del §9.3 (scomposizione multi-lotto per garantire realizzo zero su transfer che attraversano più lotti a prezzi diversi) **non è opzionale** — senza di essa, l'Opzione C introdurrebbe un bug più sottile di quello che risolve (P&L fantasma su transfer di grandi quantità che coprono più acquisti storici a prezzi diversi). Questo aumenta lo sforzo di implementazione stimato da "medio" a "medio-alto", ma resta comunque inferiore all'Opzione B.

Questa raccomandazione **non costituisce un'implementazione** né un impegno a procedere — è una sintesi tecnica per informare la decisione, in linea con quanto richiesto. Le domande del §13.1, in particolare la 1 e la 4, richiedono una decisione di prodotto prima che qualunque codice venga scritto.
