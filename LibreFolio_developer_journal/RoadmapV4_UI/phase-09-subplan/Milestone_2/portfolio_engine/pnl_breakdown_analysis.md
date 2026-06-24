# Analisi P&L Breakdown — Card Dashboard

_Analisi esplorativa, nessuna modifica al codice._

---

## 1. Realized Gain/Loss

### Cosa esiste già

`fifo_utils.py::calculate_fifo_lots()` calcola `ClosedLot.realized_pnl` con:

```python
realized_pnl = (sell_price - buy_price) * matched_qty
```

dove `price = abs(amount) / qty` — ovvero il prezzo unitario **in valuta della transazione**.

`get_lots()` in `portfolio_service.py` lo chiama per singolo `(broker_id, asset_id)` ma:
- non aggrega su tutto il portfolio
- non filtra per periodo
- non fa FX conversion a target_currency
- non gestisce WAC (usa FIFO puro)

### Il problema del prezzo FIFO

`FIFOTransactionInput.price = abs(amount) / qty`

Questo è il **prezzo medio pagato per unità nella valuta della transazione**. Non è il WAC del sistema principale (che usa FX conversion alla data di acquisto).

Incoerenze:
- Se acquisto ETF a €50, poi a €60 → WAC = €55, FIFO lot buy_price = €50 o €60
- Se acquisto in USD, FIFO usa il prezzo in USD senza FX; WAC usa FX alla data dell'acquisto
- `open_cost_basis` nel sistema è `WAC × qty` → se usassimo FIFO per realized il totale non quadrerebbe

### WAC-based realized G/L (approccio alternativo)

Con WAC l'approccio è più semplice e coerente:

```python
realized_gain_loss_wac =
    sum(sell_proceeds_in_target_ccy)
    - sum(wac_at_sell_date × qty_sold)
```

Dove `wac_at_sell_date` è il WAC del pool appena prima della SELL.

**Vantaggio**: coerente con `open_cost_basis = WAC × qty_remaining`.  
**Svantaggio**: non è il "vero" FIFO; non è fiscalmente preciso in molte giurisdizioni.

### Possibilità di calcolare realized G/L oggi

| Metodo | Fattibilità | Coerenza | Complessità |
|--------|-------------|---------|-------------|
| FIFO (già implementato) | ✓ per singolo asset | ✗ non aggregabile in target_ccy | Media |
| WAC-based | ✓ con nuovo helper | ✓ coerente con open_cost_basis | Media |
| FIFO aggregato multi-asset | Mancano dati FX per periodo | ✗ | Alta |

**Risposta**: possiamo calcolare `realized_gain_loss` oggi con WAC, ma serve un nuovo helper
`compute_realized_gain_loss_series()` per ogni `(broker, asset)` che:
1. Iteri le SELL nel periodo
2. Per ogni SELL recuperi WAC appena prima della vendita dalla `wac_series`
3. Calcoli `proceeds - wac_cost` e converta a `target_currency`

**Non serve nuova modellazione DB.**

**Rischio di incoerenza**: se usiamo WAC per realized e WAC per open_cost_basis, la somma
`realized_gain_loss + unrealized_gain_loss` dovrebbe quadrare con `period_pnl`.
Questo va verificato con test.

**Periodo vs lifetime**: serve distinguere:
- `realized_gain_loss_period`: solo SELL con `date_from <= sell_date <= date_to`
- `realized_gain_loss_lifetime`: tutte le SELL

La card vuole il valore di periodo.

---

## 2. Unrealized Gain/Loss

### Semantica attuale

In `DailyPortfolioState`:
```python
unrealized_gain_loss = nav_value - book_value
```

dove `book_value = open_cost_basis + cash + in_transit_book_value`.

Quindi include anche cash nella formula. Meglio sarebbe:
```python
unrealized_gain_loss_assets = market_value - open_cost_basis
```

La card `Period P&L` mostra già la `unrealized_gain_loss` come snapshot all'`end_date`.

### Snapshot vs Delta

Per il breakdown P&L di periodo:
- **Snapshot a `date_to`**: mostra quanta è la posizione unrealized oggi. Non risponde "quanto è cambiata nel periodo".
- **Delta di periodo**: `unrealized_end - unrealized_start`. Risponde "quanta parte del P&L periodo è cambiamento di unrealized".

Formula identità:
```
period_pnl = unrealized_delta + realized_gain_loss + income - fees_taxes
```

Se vogliamo mostrare il breakdown, serve il **delta**, non lo snapshot.

Per calcolarlo:
- `unrealized_start = market_value_at_start - open_cost_basis_at_start`
- Questi valori sono in `DailyPortfolioState` ma non vengono esposti nell'API summary.

### Cosa esiste / cosa manca

| Campo | Esiste in schema | Note |
|-------|-----------------|------|
| `unrealized_gain_loss` snapshot a `date_to` | ✅ `PortfolioSummary.unrealized_gain_loss` | `nav - book_value` (include cash) |
| `unrealized_gain_loss` snapshot a `date_from` | ❌ | Da aggiungere |
| `unrealized_gain_loss_delta` | ❌ | Derivabile da sopra |

---

## 3. Income (DIVIDEND + INTEREST)

### Come vengono gestiti oggi

DIVIDEND e INTEREST hanno `amount > 0` (cash in entrata). Vengono inclusi nel **cash ledger** dell'engine:

```python
# DailyStateBuilder.build()
cash_deltas[tx.date] += converted * ctxn.share  # tutti i tx.amount
```

Quindi DIVIDEND e INTEREST sono già inclusi nel `cash_value` e nel `nav_value`. Non sono però separati come categoria.

### Non sono `external_cash_flows`

In `ScopeAwareTransactionClassifier`, solo DEPOSIT e WITHDRAWAL sono `_EXTERNAL_CASH_TYPES`.
DIVIDEND e INTEREST NON vanno negli `external_cash_flows`, quindi NON entrano nel calcolo MWRR come "flussi" — corretto: sono rendimento interno.

### Calcolo

Aggregare dal DB è semplice e affidabile:

```python
income = sum(
    tx.amount * fx_rate * share
    for tx in transactions
    if tx.type in (DIVIDEND, INTEREST)
    and date_from <= tx.date <= date_to
    and tx.amount > 0
)
```

Nessuna ambiguità. Il segno è già positivo (cash in entrata).

**Risposta**: il campo è affidabile. Serve solo aggregazione sul periodo + FX conversion.
Nessun helper esistente — da aggiungere.

---

## 4. Fees & Taxes

### Come vengono gestiti oggi

FEE e TAX hanno `amount < 0` (cash out). Inclusi nel cash ledger come tutti gli altri.
Non sono separati.

### Fee incorporate nei BUY/SELL

Problema critico: molte piattaforme includono le commissioni nell'`amount` del BUY/SELL.
Esempio: acquisto 10 VWCE, commissione €5 inclusa → `amount = -1005` (€100 × 10 + €5).

In questo caso:
- `WAC = 1005/10 = 100.5` → WAC sovrastimato
- Non c'è una transazione FEE separata
- Non c'è modo di distinguerlo senza un campo `fee_amount` separato (che non esiste)

Le transazioni FEE/TAX **separate** sono affidabili. Le fee embedded in BUY/SELL non sono estraibili.

### Aggregazione

```python
fees_taxes = sum(
    abs(tx.amount * fx_rate * share)
    for tx in transactions
    if tx.type in (FEE, TAX)
    and date_from <= tx.date <= date_to
)
```

Valore sempre positivo (erogazione). Da mostrare come negativo nel P&L.

**Risposta**: affidabile solo per FEE/TAX come transazioni separate. Non cattura fee embedded.
Meglio chiamarlo `fees_taxes` (unificato) per ora — separare solo se si dimostra utilità.

---

## 5. Nav Start e il bug `date_from` precedente ai dati

### Il problema

Codice attuale in `get_summary()`:

```python
pre_period = [s for s in nav_snapshots if s.date <= date_from]
period_nav_start_val = pre_period[-1].nav if pre_period else nav_snapshots[0].nav
```

Se `date_from = 2020-01-01` e il primo evento è `2025-02-11`:
- `pre_period` è vuoto → fallback a `nav_snapshots[0].nav`
- `nav_snapshots[0].nav` è il NAV **il giorno del primo evento** (es. EUR 600 se si fa un BUY)
- La card mostra "NAV start = EUR 600" anche se si seleziona un range che inizia prima del portfolio

**Il comportamento è sbagliato.** Il NAV pre-portfolio è 0.

### Fix corretto

```python
if not pre_period:
    period_nav_start_val = Decimal("0")   # portfolio non esisteva ancora
else:
    period_nav_start_val = pre_period[-1].nav
```

Stessa correzione serve in `get_history()` per la rebasing:

```python
period_start_nav = pre_period[-1].nav if pre_period else Decimal("0")
```

(Attualmente usa `nav_snapshots[0].nav` come fallback — stesso bug.)

### Semantica corretta dei campi

| Campo | Semantica | Implementato |
|-------|-----------|--------------|
| `requested_date_from` | Data richiesta dall'utente | ✅ in `PortfolioReportMetadata` |
| `computed_date_from` | Prima data per cui il motore ha dati | ✅ in metadata |
| `period_start_nav_pre_flow` | NAV alla `date_from` prima di qualsiasi CF su quella data | ❌ manca |
| `period_start_nav_post_flow` | NAV alla `date_from` dopo CF | ❌ non necessario per card |

**Campo da usare in card**: `period_start_nav_pre_flow` — il NAV snapshot pre-flow alla data di inizio.  
Il campo attuale `period_nav_start` ha il bug sopra descritto.

---

## 6. Opzioni di breakdown P&L

### Opzione A — Semplice e robusta ✅ CONSIGLIATA ORA

```
Period P&L
Start NAV
Net flows
Unrealized G/L snapshot
Other result
```

**Dati richiesti**: tutti esistono (con fix bug nav_start)  
**Affidabilità**: alta  
**Rischio double-counting**: nessuno  
**Implementabile ora**: sì

`other_result = period_pnl - (unrealized_delta) - income - fees_taxes`
→ se non calcoliamo income/fees, "Other result" = tutto il resto (unrealized change + income - fees)

Limitazione: non distingue le componenti.

---

### Opzione B — Breakdown avanzato ❌ TROPPO PRESTO

```
Period P&L
Unrealized G/L delta
Realized G/L
Income
Fees & Taxes
Other result
Start NAV
Net flows
```

**Dati richiesti**: unrealized_delta (manca), realized_GL (da implementare), income (da implementare), fees_taxes (da implementare)  
**Rischio double-counting**: medio — serve verifica che la somma sia identica a `period_pnl`  
**Implementabile ora**: parzialmente (income + fees sono semplici)

---

### Opzione C — Ibrida (RACCOMANDAZIONE FUTURA)

```
Period P&L
Unrealized G/L delta
Income
Fees & Taxes
Other result
Start NAV
Net flows
```

**Dati richiesti**: unrealized_delta (da aggiungere), income (da aggiungere), fees_taxes (da aggiungere)  
**Rischio double-counting**: basso se formula `other_result = pnl - unrealized_delta - income + fees_taxes`  
**Implementabile con 1 step**: sì  
**Vantaggio**: separa le 3 componenti più informative; `other_result` = realized G/L + fee embedded  

---

## 7. DTO consigliati

### Campi esistenti (in `PortfolioSummary`)

| Campo | Valore |
|-------|--------|
| `period_pnl` | ✅ esiste |
| `period_nav_start` | ✅ esiste (con bug nav=0 da fixare) |
| `period_net_flows` | ✅ esiste |
| `unrealized_gain_loss` | ✅ esiste (snapshot a date_to) |

### Campi mancanti per Opzione C

| Campo | Descrizione | Derivabile frontend? | Note |
|-------|-------------|---------------------|------|
| `period_unrealized_gain_loss_end` | UGL snapshot a date_to | ✅ già in summary | Da rinominare per chiarezza |
| `period_unrealized_gain_loss_start` | UGL snapshot a date_from | ❌ serve backend | Richiede query engine su date_from |
| `period_income` | DIVIDEND + INTEREST nel periodo | ❌ serve backend | Aggregazione semplice |
| `period_fees_taxes` | FEE + TAX nel periodo | ❌ serve backend | Aggregazione semplice |
| `period_realized_gain_loss` | Realized G/L WAC-based | ❌ serve backend | Nuovo helper |

### Naming consigliato

```python
# PortfolioSummary — da aggiungere
period_unrealized_gain_loss_start: Optional[Currency]   # UGL snapshot a date_from
period_income: Optional[Currency]                       # DIVIDEND + INTEREST nel periodo
period_fees_taxes: Optional[Currency]                   # FEE + TAX nel periodo (valore positivo)
period_realized_gain_loss: Optional[Currency]           # realized WAC-based nel periodo
```

**Non aggiungere tutti adesso** — aggiungere in 2 step:
1. Step A: fix bug nav_start → Opzione A già funziona
2. Step B: add income + fees_taxes + unrealized_start → Opzione C

---

## 8. Card Period P&L consigliata (stato attuale + bug fix)

**Opzione A — implementabile ora:**

```text
┌──────────────────────────────────────────┐
│ PERIOD P&L                           (?) │
│                                          │
│  +EUR 5.215,84                           │
│                                          │
│  Start NAV    EUR  27.380,00             │
│  Net flows    EUR       0,00             │
│                                          │
│  Cash-flow adjusted result               │
└──────────────────────────────────────────┘
```

**Opzione C — dopo step B (income + fees + unrealized_start):**

```text
┌──────────────────────────────────────────┐
│ PERIOD P&L                           (?) │
│                                          │
│  +EUR 5.215,84                           │
│                                          │
│  Unrealized G/L   +EUR 4.980            │
│  Income            EUR   330            │
│  Fees & Taxes     −EUR    94            │
│  Other result      EUR     0            │
│                                          │
│  Start NAV    EUR  27.380,00             │
│  Net flows    EUR       0,00             │
└──────────────────────────────────────────┘
```

Note:
- Nessun NAV end (già in card Net Worth)
- Nessun P&L% (già in card Returns)
- `Other result` = pnl − unrealized_delta − income + fees (quasi zero in casi normali; segnala anomalie)
- Le righe di breakdown devono sommare a `period_pnl`

---

## 9. Test minimi

```python
test_period_pnl_basic
  - portfolio: deposito 1000, acquisto asset, asset sale valore 1200
  - period_pnl = 200 (unrealized gain)
  - net_flows = 0 (no depositi nel periodo)

test_period_nav_start_before_first_event
  - data_from = 2020-01-01, primo evento = 2025-02-11
  - period_nav_start deve essere 0 (non 600)

test_period_nav_start_within_history
  - data_from = giorno dopo secondo deposito
  - period_nav_start = NAV esatto in quel giorno

test_net_external_flows_only_deposit_withdrawal
  - DIVIDEND e INTEREST non contano come net_flows
  - solo DEPOSIT e WITHDRAWAL contribuiscono

test_income_aggregation
  - 2 DIVIDEND nel periodo, 1 fuori periodo
  - period_income = somma solo dei 2 nel periodo

test_fees_taxes_aggregation
  - 1 FEE, 1 TAX nel periodo
  - period_fees_taxes = somma assoluta dei 2

test_pnl_identity_opzione_c
  - period_pnl == unrealized_delta + income - fees_taxes + other_result
  - tolleranza rounding 0.01

test_realized_gain_loss_wac_vs_fifo
  - BUY 10 @ €50, BUY 10 @ €60, SELL 10
  - WAC = €55 → realized = 10 × (sell_price - 55)
  - FIFO → realized = 10 × (sell_price - 50)
  - Verificare che WAC è coerente con open_cost_basis restante

test_no_double_counting_income_in_cash
  - DIVIDEND appare in cash_value
  - NON appare in net_external_flows (solo DEPOSIT/WITHDRAWAL)
  - period_income va aggiunto separatamente, non sottratto da pnl
```

---

## 10. Rischi e domande aperte

### Rischi

1. **Fee embedded in BUY/SELL**: non estraibili senza nuovo campo `fee_amount`.
   `period_fees_taxes` catturerà solo FEE/TAX separati.

2. **Realized G/L WAC vs FIFO**: il metodo fiscale dipende dal paese.
   Per IT è LIFO, per US FIFO, per CH FIFO. WAC è "ragionevole" ma non fiscalmente corretto.
   Documentare chiaramente "cost-average method, not tax-compliant".

3. **Transfer-in con cost_basis_override**: quando un asset entra con CBO, il WAC
   viene correttamente inizializzato dal CBO, quindi realized G/L WAC resta coerente.
   Tuttavia il prezzo FIFO sarà il `abs(amount)/qty` che potrebbe NON coincidere con il CBO.

4. **Transaction-implied valuation**: asset valorizzati a costo non hanno market_value
   → `unrealized_gain_loss_delta` sarà distorto per quei giorni.

5. **ADJUSTMENT**: i SELL sintetici da adjustment/transfer potrebbero creare realized G/L
   non voluto. Escludere ADJUSTMENT da realized computation.

### Domande aperte

1. **Quando mostrare Opzione A vs C?**: l'Opzione A è robusta ma poco informativa.
   L'Opzione C è più utile ma richiede step B. Conviene pianificare step B subito dopo A?

2. **Unrealized G/L come base del P&L card?**: mostrare `unrealized_end` snapshot (già disponibile)
   o `unrealized_delta` (serve unrealized_start)? Delta è più utile per il P&L breakdown.

3. **`other_result` quando è > 0?**: può esserci un "other_result" significativo in casi di
   aggiustamenti, split, price adjustment (PRICE_ADJUSTMENT). Da documentare nell'UI.

4. **Period income già in NAV?**: DIVIDEND/INTEREST sono già nel cash_value (e quindi nel NAV).
   Il breakdown non aggiunge income al P&L — lo scompone. Verificare che l'utente non pensi
   che income sia "extra".

---

## Raccomandazione

**Ora (Step A):** fixare il bug `period_nav_start = 0` quando `date_from` è prima del primo evento.
La card attuale Opzione A è già corretta dopo il fix.

**Prossimo step (Step B):** aggiungere `period_income`, `period_fees_taxes`, `period_unrealized_gain_loss_start`
→ abilitare Opzione C.

**Dopo (Step C):** aggiungere `period_realized_gain_loss` con WAC-based helper.
→ Opzione B completa.

Non implementare B e C in un unico step — il rischio di double-counting e i test di verifica
dell'identità richiedono attenzione separata.
