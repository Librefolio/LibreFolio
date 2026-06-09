# BRIM Plugin Audit — Sign Rules & Missing Transactions
**Data**: 2026-06-08  
**Autore**: Copilot (sessione Phase07 Part5 M2-W)  
**Metodo**: esecuzione di tutti i plugin sui rispettivi sample file; analisi di `validation_issues` e `warnings` generati da `_create_transaction()`

---

## Regole di segno del progetto (riferimento)

| Tipo | `quantity` | `cash.amount` | Asset |
|------|-----------|--------------|-------|
| BUY | > 0 | < 0 | obbligatorio |
| SELL | < 0 | > 0 | obbligatorio |
| DIVIDEND | = 0 | > 0 | obbligatorio |
| INTEREST | = 0 | > 0 | opzionale |
| DEPOSIT | = 0 | > 0 | vietato |
| WITHDRAWAL | = 0 | < 0 | vietato |
| FEE | = 0 | < 0 | opzionale |
| TAX | = 0 | < 0 | opzionale |

---

## broker_coinbase

### Problemi trovati
- `qtyZero` su righe INTEREST (staking rewards): Coinbase esporta la quantità di token ricevuti (es. `0.000037835 ETH`) nella colonna `Quantity Transacted`, ma il tipo INTEREST del progetto richiede `qty = 0`.

### Fix applicato
**File**: `backend/app/services/brim_providers/broker_coinbase.py`

Per INTEREST e DIVIDEND: forza `quantity = 0`. Se la quantità originale era > 0, emette un `warning` nel canale libero:

```python
if tx_type in (TransactionType.INTEREST, TransactionType.DIVIDEND):
    if quantity != Decimal("0"):
        warnings.append(
            f"Row {row_num}: {tx_type_raw} had quantity={quantity} {asset}"
            f" — recorded as cash-only INTEREST (token qty discarded, cash preserved)"
        )
    quantity = Decimal("0")
```

### ⚠️ Dubbio aperto — Crypto staking rewards
Il tipo INTEREST del progetto è pensato per interessi *cash* (obbligazioni, conti di risparmio). Le staking rewards di Coinbase sono token reali ricevuti: non è solo un incasso monetario, è un aumento effettivo della quantità dell'asset in portafoglio.

**Opzione A — INTEREST qty=0** *(soluzione attuale)*  
- ✅ Schema-compliant  
- ✅ Il valore EUR/USD è preservato (visibile nel report fiscale)  
- ❌ La quantità di token ricevuti non è tracciata → il portafoglio non riflette il saldo reale

**Opzione B — Tipo BUY con cash=0**  
- ✅ Traccia la quantità di token  
- ❌ Il schema impone `cash.amount < 0` per BUY → serve un valore dummy  
- ❌ Distorce il rendimento (come se avessi comprato a €0, abbassando il WAC)

**Opzione C — Nuovo tipo RECEIVE (futuro)**  
- ✅ Semantica corretta: "ricevo X token come rendimento"  
- ❌ Richiede modifica allo schema e al frontend → fuori scope attuale  
- ✅ Scalabile per tutti i casi simili (airdrop, mining, rendimenti in token)

**Raccomandazione**: lasciare Opzione A per ora, aggiungere Opzione C ai `TODO_FUTURI.md`. L'impatto pratico è limitato finché il portafoglio non ha criptovalute significative da staking.

---

## broker_degiro

### Problemi trovati (21 validation issues)
DeGiro esporta gli importi nella colonna `Mutatie` con logica opposta alle regole del progetto:
- BUY, FEE, TAX: esportati come **positivi** (uscite di cassa viste come debiti) → richiedono negativi
- DIVIDEND: esportato come **negativo** (credito contabile) → richiede positivo

```
Row 15: cashSignPositive DIVIDEND  → amount era negativo
Row 21: cashSignNegative FEE       → amount era positivo
Row 29-32: cashSignNegative BUY    → amount era positivo
Row 60: cashSignNegative TAX       → amount era positivo
```

### Fix applicato
**File**: `backend/app/services/brim_providers/broker_degiro.py`

```python
if tx_type in (TransactionType.BUY, TransactionType.FEE, TransactionType.TAX) \
        and amount is not None and amount > 0:
    amount = -amount
if tx_type == TransactionType.DIVIDEND and amount is not None and amount < 0:
    amount = -amount
```

Le condizioni (`> 0` / `< 0`) proteggono da doppia negazione se il broker cambia formato in futuro.

**Effetto**: 21 TX → 42 TX valide (le righe precedentemente scartate vengono ora importate).

---

## broker_directa

### Problemi trovati (4 validation issues)
Directa SIM esporta dividendi e cedole come importi **negativi** (dal punto di vista del conto titoli: uscita verso il conto corrente). Il progetto richiede `cash > 0` per DIVIDEND e INTEREST.

```
Row 13, 15: cashSignPositive DIVIDEND
Row 20, 22: cashSignPositive INTEREST
```

### Fix applicato
**File**: `backend/app/services/brim_providers/broker_directa.py`

```python
if tx_type in (TransactionType.DIVIDEND, TransactionType.INTEREST) \
        and amount is not None and amount < 0:
    amount = -amount
```

**Nessuna perdita di dati.** I warning restanti ("Pippo", riga vuota) sono dati di test nel sample file.

---

## broker_etoro

### Problemi trovati
Nessuno. Tutti i segni già corretti. ✅

---

## broker_finpension

### Problemi trovati
7 transazioni DIVIDEND **completamente saltate** (non un problema di segno ma di mappatura mancante):

```
Row 20–26: unknown category 'dividend', skipping
```

Il `TYPE_MAPPINGS` aveva: `"buy"`, `"sell"`, `"interests"`, `"flat-rate administrative fee"`, `"deposit"`, `"withdrawal"` — ma **mancava `"dividend"`**.

I dati nel CSV erano completi: ISIN presente, importo positivo in CHF, nessuna quantità (corretto per DIVIDEND).

### Fix applicato
**File**: `backend/app/services/brim_providers/broker_finpension.py`

```python
TYPE_MAPPINGS = {
    ...
    "dividend": TransactionType.DIVIDEND,  # aggiunto
    ...
}
```

Aggiunto anche `TransactionType.DIVIDEND` al blocco `asset_required` (DIVIDEND richiede asset, che in finpension è identificato dall'ISIN).

**Effetto**: 19 TX → 26 TX valide.

---

## broker_freetrade

### Problemi trovati (3 validation issues)
`qtyZero` su righe DIVIDEND (righe 4, 5, 10): il CSV Freetrade include una colonna `Quantity` anche per DIVIDEND (probabilmente il numero di quote detenute). Il progetto richiede `qty = 0` per DIVIDEND.

### Fix applicato
**File**: `backend/app/services/brim_providers/broker_freetrade.py`

```python
if tx_type in (TransactionType.DIVIDEND, TransactionType.INTEREST):
    quantity = Decimal("0")
```

**Nessuna perdita significativa**: la quantità nei DIVIDEND di Freetrade è informativa (quote possedute), non una quantità transata.

**Effetto**: 7 TX → 10 TX valide.

---

## broker_generic_csv

### Problemi trovati
Nessun problema di segno rilevato sui sample file validi. Il plugin richiede una colonna `date` obbligatoria che non è presente nel primo file CSV trovato in modo automatico dall'audit script — comportamento atteso (il generic CSV ha requisiti minimi specifici).

---

## broker_ibkr

### Problemi trovati
Nessun problema di segno. 3 warning attesi: righe senza ISIN saltate (FX trades senza asset azionario). ✅

---

## broker_revolut

### Problemi trovati (2 validation issues)
`cashRequired` per WITHDRAWAL (riga 2) e FEE (riga 7): la funzione `_parse_revolut_amount()` non gestiva il formato **negativo con simbolo valuta** (`-$30.93`, `-€0.01`).

Il parser cercava `$` o `€` come primo carattere, ma per valori negativi il primo carattere è `-`. Risultato: ritornava `None` → `cash = None` → validazione falliva con `cashRequired`.

### Fix applicato
**File**: `backend/app/services/brim_providers/broker_revolut.py`

```python
def _parse_revolut_amount(value: str) -> Tuple[Optional[Decimal], str]:
    value = value.strip()
    negative = value.startswith("-")
    if negative:
        value = value[1:]        # strip the minus BEFORE checking currency symbol
    # ... detect $, €, £ as before ...
    result = Decimal(value)
    return (-result if negative else result), currency
```

**Nessuna perdita di dati.** È un bug fix puro: i dati c'erano ma non venivano letti.

**Effetto**: 6 TX → 8 TX valide.

---

## broker_schwab

### Problemi trovati e fix

#### 1. `cashSignPositive` DEPOSIT (riga 102) — Fix applicato
`MoneyLink Transfer` mappato sempre a DEPOSIT, ma il valore `-$30.00` indica un'uscita (prelievo verso banca). DEPOSIT richiede `cash > 0`.

**Fix**: dopo il parsing dell'importo, flip del tipo basato sul segno:
```python
if tx_type == TransactionType.DEPOSIT and amount is not None and amount < 0:
    tx_type = TransactionType.WITHDRAWAL
elif tx_type == TransactionType.WITHDRAWAL and amount is not None and amount > 0:
    tx_type = TransactionType.DEPOSIT
```

#### 2. 41 transazioni saltate — Fix applicato (mappature estese)
Il `TYPE_MAPPINGS` originale copriva solo 9 action type. Schwab ha ~25 tipi diversi.

**Aggiunte**:

| Action CSV | Tipo | Note |
|-----------|------|------|
| `cash dividend` | DIVIDEND | Dividendo cash standard |
| `non-qualified div` | DIVIDEND | Dividendo non qualificato US |
| `qual div reinvest` | DIVIDEND | Cash leg del reinvestimento |
| `reinvest dividend` | DIVIDEND | Cash leg del reinvestimento (era BUY — **errore**) |
| `special non qual div` | DIVIDEND | Dividendo speciale |
| `pr yr cash div` | DIVIDEND | Dividendo anno precedente |
| `pr yr div reinvest` | DIVIDEND | Cash leg, anno precedente |
| `long term cap gain reinvest` | DIVIDEND | Distribuzione plusvalenza fondo |
| `advisor fee` | FEE | Commissione consulente (10 righe!) |
| `adr mgmt fee` | FEE | Commissione ADR |
| `foreign tax paid` | TAX | Ritenuta estera |
| `wire sent` | WITHDRAWAL | Bonifico uscente |

> **Nota importante**: `reinvest dividend` era stato inizialmente mappato come BUY (errore). Schwab usa una struttura a due righe per i dividendi reinvestiti:
> - Riga A: `reinvest dividend` qty=empty, amount=+$X → **DIVIDEND** (cash ricevuto)
> - Riga B: `reinvest shares` qty=Y, amount=-$X → **BUY** (azioni acquistate)

#### 3. DIVIDEND senza ticker → INTEREST
Riga 104: `Non-Qualified Div` da fondo monetario (CMF), nessun ticker, descrizione `TDA TRAN - NON-TAXABLE DIVIDENDS (CMF)`. DIVIDEND richiede asset ma non c'è symbol.

**Fix**: reclassificazione automatica a INTEREST con warning:
```python
if tx_type == TransactionType.DIVIDEND and not symbol:
    warnings.append(f"Row {row_num}: DIVIDEND '{description}' has no ticker — reclassified as INTEREST")
    tx_type = TransactionType.INTEREST
```

#### Corporate actions — skip esplicito con warning differenziato
`stock split`, `reverse split`, `stock merger`, `name change`, `spin-off`, `journaled shares`, `conversion`, `internal transfer`, `stock div dist` → skip con warning `"corporate action '...' has no equivalent, skipping"` (invece del generico "unknown action").

**Effetto**: 84 TX → 106 TX valide.

---

## broker_trading212

### Problemi trovati (3 validation issues)
`qtyZero` su righe DIVIDEND (righe 7, 8, 9): Trading212 include la colonna `No. of shares` anche per i dividendi. Il progetto richiede `qty = 0` per DIVIDEND.

### Fix applicato
**File**: `backend/app/services/brim_providers/broker_trading212.py`

```python
if tx_type in (TransactionType.DIVIDEND, TransactionType.INTEREST):
    quantity = Decimal("0")
```

**Effetto**: 9 TX → 12 TX valide.

---

## Riepilogo generale

| Plugin | Issues prima | Issues dopo | TX prima | TX dopo | Note |
|--------|-------------|-------------|----------|---------|------|
| coinbase | 2 | 0 | 4 | 6 | ⚠️ staking qty persa (warning emesso) |
| degiro | 21 | 0 | 21 | 42 | segni invertiti in 4 tipi |
| directa | 4 | 0 | 19 | 23 | abs per DIVIDEND/INTEREST |
| etoro | 0 | 0 | 22 | 22 | ✅ già corretto |
| finpension | 0\* | 0 | 19 | 26 | \*erano skip silenziosi, non issues |
| freetrade | 3 | 0 | 7 | 10 | qty=0 per DIVIDEND |
| generic_csv | 0 | 0 | — | — | ✅ già corretto |
| ibkr | 0 | 0 | 16 | 16 | ✅ già corretto |
| revolut | 2 | 0 | 6 | 8 | bug parser `-$X` |
| schwab | 1+41skip | 0 | 84 | 106 | mappature estese |
| trading212 | 3 | 0 | 9 | 12 | qty=0 per DIVIDEND |
| **TOTALE** | **36** | **0** | **207** | **271** | +64 TX recuperate |

---

## Summary — Transazioni senza mappatura nel modello del progetto

Queste transazioni esistono nei file reali dei broker ma **non possono essere importate senza perdita** per un limite del modello dati attuale (non dei plugin).

### 1. Crypto staking rewards (coinbase, etoro, futuro)
**Problema**: ricevere token come rendimento aumenta il saldo in portafoglio, ma INTEREST richiede `qty=0`.  
**Impatto**: il portafoglio mostra il valore del rendimento in euro, ma non le quantità di token acquisite → saldo crypto non corretto.  
**Soluzione necessaria**: nuovo tipo `RECEIVE` (o `REWARD`) con `qty > 0` e `cash` opzionale.

### 2. Corporate actions (schwab, ibkr, altri)
Attualmente saltate con warning "no equivalent":

| Evento | Descrizione | Impatto se ignorato |
|--------|-------------|-------------------|
| Stock Split / Reverse Split | Modifica qty e prezzo per azione | WAC e qty portafoglio errati dopo split |
| Stock Merger | N azioni vecchie → M azioni nuove | Asset scompare, non viene sostituito |
| Spin-off | Nuovo asset ricevuto come stacco | Asset spin-off mai registrato |
| Stock Dividend (stock div dist) | Dividendo pagato in azioni | Azioni non registrate in portafoglio |
| Name Change | Cambio ticker/ISIN stesso asset | Potrebbe creare duplicati |

**Soluzione necessaria**: un tipo `ADJUSTMENT` con logica corporate action, oppure eventi specifici sul modello `Asset` (non sulle transazioni).

### 3. Stock dividends / scrip dividends (freetrade, trading212)
Alcuni broker offrono dividendi in forma di azioni anziché cash. La scelta tra cash e azioni è dell'utente. Attualmente vengono importati come DIVIDEND cash se c'è un importo, ignorati se non c'è cash.

**Soluzione necessaria**: distinguere dividend-in-shares (→ mapping verso BUY a prezzo 0? O tipo dedicato?).

### 4. Finpension: reinvestimento automatico (categoria "Redemption" e altri)
Finpension effettua ribilanciamenti periodici automatici che non sempre mappano a BUY/SELL semplici. Alcune categorie potrebbero emergere in export reali oltre quelle del sample file.

**Raccomandazione**: verificare con export reale e aggiungere mappature al bisogno.

### 5. Schwab: `stock div dist` (distribuzione azioni)
Dividendo pagato in azioni (non cash). Attualmente skippa con "corporate action".  
**Potrebbe essere modellato** come BUY a prezzo 0 (ricevi azioni gratis) ma distorce il WAC.

---

## Aggiornamento del 2026-06-09 — Migliorie, Decisioni e Sentinel Value

In seguito a una rilettura congiunta dei requisiti e dei limiti della contabilità a partita doppia del portafoglio, sono state implementate le seguenti migliorie strutturali ed è stata tracciata una soluzione UX per il raffinamento del WAC (PMC).

### 1. Risoluzione Staking Crypto (Coinbase)
* **Decisione**: Lo staking crypto/reward (staking income, rewards income, learning reward) non è un provento cash classico (`INTEREST`). È una distribuzione in natura che incrementa la quantità fisica di token in portafoglio senza muovere la cassa in valuta fiat. Mapparlo a `INTEREST` costringeva ad azzerare la quantità, sballando il saldo reale delle crypto.
* **Miglioria**: Queste transazioni sono state ri-mappate a **`TransactionType.ADJUSTMENT`**.
  * La quantità di token ricevuta viene preservata (`quantity > 0`).
  * Il controvalore in cassa viene azzerato (`amount = None`) per superare i vincoli del DB (`cashForbidden` su ADJUSTMENT).
  * Il controvalore monetario originario e la valuta del reward vengono inseriti nella descrizione (es. `Value: 0.12649 EUR`) per fini informativi e fiscali.

### 2. Dettaglio Quote nei Dividendi (Freetrade & Trading212)
* **Decisione**: I dividendi sono di natura legati alle azioni detenute. Il dato sulle quote al momento dello stacco è prezioso per l'utente, ma a livello di DB la transazione `DIVIDEND` richiede `quantity = 0` (poiché le quote le possiedi già in portafoglio e il dividendo sposta solo cassa).
* **Miglioria**: I parser estraggono la quantità di quote originale e calcolano dinamicamente il dividendo unitario per azione (`Total Amount / Shares`). Compilano poi una descrizione dettagliata in inglese:
  `At the time of the dividend, <shares> shares were present on the broker, yielding <dividend_per_share> <currency> per share` (es. `yielding 0.25 USD per share`).

### 3. Schwab: Mappatura Corporate Actions e Calcolo WAC (PMC)
* **Decisione**: Skipping o warning semplici sulle corporate actions causano la perdita dei saldi quantitativi dei titoli in portafoglio. Mappare a `ADJUSTMENT` è la soluzione più corretta.
* **Analisi del WAC**:
  * **Stock Split e Reverse Split**: Il calcolo del WAC avviene in modo **automatico (AUTO)**. Aggiungendo o rimuovendo quote (quantity +/-) tramite `ADJUSTMENT` con cassa a zero, la formula del WAC ricalcola correttamente il prezzo medio per azione (diluizione per lo split, concentrazione per il reverse split) basandosi sul costo storico complessivo che rimane invariato. Non serve intervento manuale. *Nota: è atteso che il provider dei prezzi storici adegui le quotazioni storiche a partire dalla data di split.*
  * **Stock Merger, Name Change, Conversion**: Queste transazioni avvengono cambiando asset (es. da CCIV a LCID) e quantità (rapporto non 1:1). Il WAC storico del vecchio asset non risiede nel file CSV corrente (che mostra solo il merge) ma nella storia degli acquisti del DB. Quindi, il calcolo automatico imposterà a 0 il WAC del nuovo titolo (errato). L'utente deve necessariamente interagire inserendo il PMC storico del titolo precedente.

### 4. ~~Proposta: Sentinel Value per il Frontend~~ → Sostituita con BRIMFieldTodo (2026-06-09)

**Proposta originale (scartata)**: tag `"requires-cost-basis-refinement"` in `TXCreateItem.tags` + `cost_basis_mode = "manual"` + `cost_basis_override = None`. Scartata perché i tags sono user-facing (raggruppamento/filtro) e non devono essere inquinati con metadati di workflow.

**Architettura approvata — `BRIMFieldTodo`**:

Il plugin segnala esplicitamente quali campi di quali transazioni sono stati lasciati intenzionalmente incompleti tramite un tipo dedicato `BRIMFieldTodo`, trasportato in `BRIMParseOutput.field_todos` e `BRIMParseResponse.field_todos`.

1. **Safe placeholder values**: Il plugin imposta `cost_basis_mode = "manual"` e `cost_basis_override = None`. Entrambi passano il validatore Pydantic (Rule 12: mode valido per ADJUSTMENT qty>0; nessuna regola richiede override non-None quando mode='manual').
2. **BRIMFieldTodo**: Il plugin emette un `BRIMFieldTodo(tx_index=N, field='cost_basis_override', severity='blocker', reason_code='stock_merger', message='Cost basis from OLD must be entered manually', context={...})`.
3. **Tre canali, tre scopi**: `warnings` (note free-text) / `validation_issues` (TX rifiutate) / `field_todos` (TX accettate ma campo incompleto).
4. **Step 3**: Mostra conteggio TODOs per file nella DataTable e nel summary aggregato.
5. **Step 4**: Righe con blocker TODO → badge rosso ⚠️, import bloccato finché l'utente non compila il campo mancante.

Dettagli completi: [Import Wizard Plan §8.8](plan-phase07Part5-v5-ImportWizard.prompt.md#88-m2-ft-brimfieldtodo-schema--step-3-integration-).

---

**Related Plan**:
- [Import Wizard Plan (Phase 07 Part 5)](plan-phase07Part5-v5-ImportWizard.prompt.md)

*File aggiornato in data 2026-06-09 dall'assistente di pair programming.*
