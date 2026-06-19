# LibreFolio — Phase 09 Milestone 2: Status Report

> **Audience:** AI specializzata in analisi dati / portfolio analytics  
> **Purpose:** Full picture dello stato attuale — algoritmi, codice, transazioni, gap aperti  
> **Style:** High-density, caveman-ultra  
> **Date:** 2026-06-19

---

## 1. Contesto Progetto

LibreFolio = self-hosted portfolio tracker (alternativa a Ghostfolio).  
Stack: Python/FastAPI backend + SvelteKit frontend + SQLite.  
Phase 09 = riprogettazione dashboard + backend portfolio engine.  
M1 = backend creato. M2 = frontend dashboard + patch backend. M2 completata poi bloccata.

---

## 2. Modello Dati: Transazioni

### 2.1 Enum `TransactionType`

| Tipo | qty | amount | Note |
|------|-----|--------|------|
| `BUY` | > 0 | < 0 | Cash esce, asset entra |
| `SELL` | < 0 | > 0 | Asset esce, cash entra |
| `DIVIDEND` | 0 | > 0 | Cash entra (interno, non CF esterno) |
| `INTEREST` | 0 | > 0 | Cash entra (interno, non CF esterno) |
| `DEPOSIT` | 0 | > 0 | CF esterno: soldi dall'investitore entrano nel broker |
| `WITHDRAWAL` | 0 | < 0 | CF esterno: soldi escono verso l'investitore |
| `FEE` | 0 | < 0 | Cash esce (costo, abbassa NAV) |
| `TAX` | 0 | < 0 | Cash esce (costo) |
| `ADJUSTMENT` | +/- | 0 | Rettifica qty (split/gift). No cash |
| `TRANSFER` | +/- | 0 | Spostamento asset broker→broker. Richiede `related_transaction_id` |
| `FX_CONVERSION` | 0 | +/- | Cambio valuta. Richiede pair. Sum netta = 0 |
| `CASH_TRANSFER` | 0 | +/- | Bonifico cash broker→broker. Richiede pair |

### 2.2 Logica segni — perché esistono

**Regola base:** `amount` nel DB è già algebricamente signato per ogni tipo.  
BUY → amount < 0 perché la cash decresce.  
SELL → amount > 0 perché la cash aumenta.  
DIVIDEND/INTEREST → amount > 0, MA sono **flussi interni**: aumentano la cash del portfolio senza che l'investitore abbia versato denaro di tasca propria.  
DEPOSIT → amount > 0, flusso **esterno**: l'investitore porta nuova liquidità.  
WITHDRAWAL → amount < 0, flusso **esterno**: l'investitore ritira liquidità.

### 2.3 Distinzione critica: CF esterno vs interno

Per TWRR/MWRR corretto:
- **CF esterno** (usato nelle formule) = solo DEPOSIT + WITHDRAWAL
- **DIVIDEND, INTEREST, FEE, TAX, BUY, SELL** = movimenti interni → NON entrano nella lista `cash_flows`
- Includere BUY come CF esterno sarebbe errore: farebbe apparire ogni acquisto come nuovo "versamento", distorcendo MWRR

```python
# Da portfolio_service.py ~L1014-1016
all_cash_flows: list[CashFlowInput] = []
for row in rows:
    if row.type in {"DEPOSIT", "WITHDRAWAL"}:
        all_cash_flows.append(CashFlowInput(date=row.date, amount=-(row.amount * row.share)))
```

> **Nota segno:** DEPOSIT ha `amount > 0` nel DB. In `CashFlowInput` la convenzione è negata: deposit → amount < 0 (denaro "versato" dall'investitore = uscita per l'investitore).

### 2.4 Cash Algebra nel ledger

`_build_history_series()` somma algebricamente tutti i `row.amount` — **nessun filtro per tipo**.  
Questo produce la cash corretta: BUY drena cash, SELL la ricarica, DIVIDEND la incrementa, FEE la decrementa.

```python
# _build_history_series — pura somma algebrica
for row in sorted(transactions, key=lambda r: r.date):
    cash_delta_by_date[row.date] += row.amount * row.share
```

---

## 3. Schema Dati API: Portfolio

### 3.1 `PortfolioSummary` (snapshot puntuale)

```python
class PortfolioSummary(BaseModel):
    net_worth: Currency               # NAV = cash + market_value (base currency)
    total_invested: Currency          # sum(DEPOSIT - WITHDRAWAL) in base currency
    total_gain_loss: Currency         # NAV - total_invested
    total_gain_loss_percent: SafeDecimal
    cash_total: Currency              # solo cash liquida
    cash_balances: List[Currency]     # per-currency breakdown
    twrr_percent: Optional[SafeDecimal]   # None se non calcolabile
    mwrr_percent: Optional[SafeDecimal]   # None se Newton non converge
    simple_roi_percent: SafeDecimal
    allocation_by_type: List[AllocationItem]      # % per asset type
    allocation_by_sector: List[AllocationItem]    # % per settore
    allocation_by_geography: List[AllocationItem] # % per paese
    holdings: List[PortfolioHolding]
    by_broker: Optional[List[BrokerBreakdown]]   # solo se include_breakdown=True
    missing_fx_pairs: List[WACMissingPairInfo]   # FX mancanti
    missing_prices_assets: List[str]             # asset senza PriceHistory
```

### 3.2 `AllocationItem` (elemento allocazione)

```python
class AllocationItem(BaseModel):
    name: str          # "ETF", "Technology", "US", "Unknown"
    value: SafeDecimal # % su totale (0-100)
    amount: SafeDecimal # valore assoluto in base currency
```

> `"Unknown"` = asset senza metadati (nessun tipo/settore/paese censito).

### 3.3 `PortfolioHistoryPoint` (time series)

```python
class PortfolioHistoryPoint(BaseModel):
    date: date_type
    cash_value: Currency      # liquido al giorno
    invested_value: Currency  # mark-to-market: Σ(qty_i × price_i × FX_i)
    nav_value: Currency       # cash + invested
    twrr: Optional[SafeDecimal]  # cumulativo da period_start
    mwrr: Optional[SafeDecimal]  # XIRR cumulativo da period_start
    roi: Optional[SafeDecimal]   # Simple ROI cumulativo
```

---

## 4. Algoritmi di Performance

### 4.1 Simple ROI

**Formula:**
```
ROI = (NAV - Net_Invested) / Net_Invested
```

**Net_Invested** = `-sum(deposit_CFs)` — solo depositi netti (prelievi aumentano).

**Implementazione (`roi_utils.py`):**

```python
def calculate_simple_roi_series(nav_snapshots, cash_flows) -> list[SimpleROIPoint]:
    cumulative_cf = Decimal("0")
    for snap in sorted_navs:
        cf_today = cf_by_date.get(snap.date, Decimal("0"))
        cumulative_cf += cf_today
        # deposit < 0 in CashFlowInput → -cumulative_cf = soldi versati
        net_invested = -cumulative_cf if cumulative_cf < 0 else Decimal("0")
        roi = (snap.nav - net_invested) / net_invested  # se net_invested > 0
        result.append(SimpleROIPoint(date=snap.date, roi=roi))
```

- **Complessità:** O(N) iterativo
- **Edge case:** net_invested = 0 → ROI = 0 (nessuna divisione per zero)
- **Semantica:** "quanto ho guadagnato rispetto a quanto ho versato di tasca mia"

### 4.2 TWRR (Time-Weighted Rate of Return)

**Scopo:** misura la performance pura degli asset, depurata dal timing dei versamenti.  
Standard CFA/GIPS per confrontare fund manager.

**Algoritmo — composizione geometrica dei sotto-periodi (HPR):**

```
TWRR = Π(1 + HPR_i) - 1

HPR_i = (NAV_end_pre_CF - NAV_start) / NAV_start
NAV_end_pre_CF = NAV_end_post_CF + CF_amount   (undo the CF)
```

> Snapshot sono POST-CF. Bisogna "togliere" il CF per ottenere il NAV puro di mercato.

**Implementazione (`roi_utils.py`):**

```python
def calculate_twrr_series(nav_snapshots, cash_flows) -> list[TWRRPoint]:
    compound = Decimal("1")
    for i in range(1, len(sorted_navs)):
        v_start = sorted_navs[i-1].nav
        v_end = sorted_navs[i].nav
        cf_amount = cf_by_date.get(snap_date, Decimal("0"))
        v_end_pre_cf = v_end + cf_amount   # undo CF (deposit<0 → +, withdrawal>0 → -)
        if v_start != 0:
            hpr = (v_end_pre_cf - v_start) / v_start
            compound *= Decimal("1") + hpr
        result.append(TWRRPoint(date=snap_date, twrr=compound - 1))
```

- **Complessità:** O(N) iterativo (nessun ricalcolo dall'inizio)
- **Edge case:** `v_start == 0` → skip (nessun investimento precedente)

### 4.3 MWRR / XIRR (Money-Weighted Rate of Return)

**Scopo:** rendimento effettivo dell'investitore, penalizza/premia il timing dei versamenti.  
Equivale all'IRR (Internal Rate of Return) su flussi a date irregolari.

**Equazione:**
```
NPV(r) = Σ [ CF_i / (1+r)^(days_i/365) ] = 0
```

**Costruzione flussi:**
- `day=0, amount=-initial_NAV` (investitore "compra" il portfolio)
- `day=d_i, amount=CF_i` (depositi intermedi < 0, prelievi > 0)
- `day=T, amount=+final_NAV + CF_on_T` (investitore "vende")

**Solver:** `scipy.optimize.newton` (Newton-Raphson).  
**Ottimizzazione warm-start:** `prev_guess = rate` precedente → 1-2 iterazioni invece di ~20.

```python
def calculate_mwrr_series(nav_snapshots, cash_flows) -> list[MWRRPoint]:
    prev_guess: float = 0.1
    for i in range(1, len(sorted_navs)):
        flows = [
            (0.0, -float(initial_nav)),
            (float(total_days), float(snap.nav) + final_day_cf),
            # + CF intermedi
        ]
        def npv(r, _flows=flows):
            if 1.0 + r <= 0.0: return float("inf")
            return sum(amount / (1.0+r)**(d/365.0) for d, amount in _flows)
        
        rate = scipy_newton(npv, x0=prev_guess, tol=1e-8, maxiter=100)
        prev_guess = rate  # warm-start
        result.append(MWRRPoint(date=snap.date, mwrr=Decimal(str(rate))))
```

- **Complessità:** O(N × K) dove K = iterazioni Newton (~1-3 con warm-start)
- **CPU-bound:** avvolto in `asyncio.to_thread()` per non bloccare event loop

### 4.4 Period Re-basing

Quando l'utente seleziona un `date_from`, le metriche devono mostrare il rendimento **del periodo selezionato**, non dall'inizio storia.

**Meccanismo:**
1. Calcola history completa da t=0 (sempre)
2. Trova NAV al `date_from` (o ultima data ≤ date_from)
3. Inietta CF sintetico: `(-period_start_nav, date=period_start_date)` — "investitore inizia con questo NAV"
4. Esclude CF storici ≤ period_start_date
5. Primo punto visibile → twrr=mwrr=roi=0 (convenzione grafico)

```python
# portfolio_service.py ~L1021-1035
if date_from and all_history:
    pre_period = [pt for pt in all_history if pt.date <= date_from]
    period_start_nav = pre_period[-1].nav_value if pre_period else all_history[0].nav_value
    synthetic_cf = CashFlowInput(date=period_start_date, amount=-period_start_nav)
    period_cash_flows = [synthetic_cf] + [cf for cf in all_cash_flows if cf.date > period_start_date]
    period_nav_snapshots = [s for s in all_nav_snapshots if s.date >= period_start_date]
```

---

## 5. Calcolo NAV Mark-to-Market

**Il NAV non è solo cash.** `invested_value = Σ(qty_i × price_i × FX_i)`.

**Pipeline in `get_history()`:**

```
1. Per ogni broker: query transazioni ALL types (nessun filtro data da, per avere
   il full history)
2. Converti ogni amount in base_currency via FX rate storico
3. _build_history_series() → dense calendar, cash cumulativa per ogni giorno
4. Traccia qty cumulativa per ogni asset (solo BUY/SELL)
5. Carica PriceHistory bulk: dict[asset_id → [(date, close, currency)]]
6. Bulk FX conversion per asset priced in non-base-currency
7. Per ogni giorno: market_value = Σ_assets(qty * price_on_date * FX)
8. NAV = cash + market_value
9. Poi taglia la serie a [date_from, date_to]
10. Calcola TWRR/ROI/MWRR sulla sub-serie re-basata
```

**Backward fill prezzi:** `_price_on_date()` usa `bisect_right` per trovare l'ultimo prezzo ≤ query_date. Asset senza prezzi → escluso da NAV (tracciato in `missing_prices_assets`).

---

## 6. Allocazioni — Come Calcolate

### 6.1 Per Tipo Asset

```python
allocation_by_type: dict[str, Decimal] = defaultdict(Decimal)
# Per ogni holding con quantity > 0:
asset_type = asset.asset_type.value  # "ETF", "STOCK", "BOND", etc.
current_value = qty * price * fx_rate
allocation_by_type[asset_type] += current_value * share_percentage
```

### 6.2 Per Settore

Settori estratti da `classification_params` (JSON) dell'asset:

```python
# classification_params: FAClassificationParams schema
if cp.sector_distribution:
    for sector, weight in cp.sector_distribution.items():
        allocation_by_sector[sector] += current_value * weight
else:
    allocation_by_sector["Unknown"] += current_value
```

### 6.3 Per Geografia

```python
if cp.geographic_area and cp.geographic_area.distribution:
    for country, weight in cp.geographic_area.distribution.items():
        allocation_by_geo[country] += current_value * weight
else:
    allocation_by_geo["Unknown"] += current_value
```

### 6.4 Conversione in percentuale

```python
total_market = sum(allocation_by_type.values()) or Decimal("1")
# Per ogni voce:
value_pct = (amt / total_market * 100).quantize(Decimal("0.01"))
```

**Pesi:** basati su **market value corrente** (non costo). Asset ETF multi-country → valore spalmato su tutti i paesi per il peso.

### 6.5 Frontend: AllocationItem → Chart

```typescript
// dashboard/+page.svelte
// AllocationItem[] → Record<string, number> per SectorPieChart
const typeData: Record<string, number> = {};
for (const item of summary.allocation_by_type) {
    typeData[item.name] = Number(item.value) / 100;  // 0-1 scale
}
// GeographyMap accetta stessa forma ma value = percentuale 0-100
```

---

## 7. Frontend Dashboard — Componenti

### 7.1 Struttura

```
dashboard/+page.svelte
├── Header: [DateRangePicker] [BrokerFilter] [↻ Sync]
├── Row KPI: KpiCard×3 (Net Worth, Gain/Loss, ROI)
├── Row Charts:
│   ├── GrowthChart (col-span-3): toggle Abs/% + currency selector
│   └── AllocationPanel (col-span-2): tabs [Tipo|Settore|Geo]
│       ├── SectorPieChart (Tipo)
│       ├── SectorPieChart (Settore)
│       └── GeographyMap (Geo)
└── RecentTransactionsPanel (last 10, read-only)
```

### 7.2 GrowthChart — Serie

| Toggle | Serie | Campo history |
|--------|-------|---------------|
| **Abs** | NAV (solid) | `nav_value.amount` |
| **Abs** | Invested (dashed) | `invested_value.amount` |
| **Abs** | Cash (dotted) | `cash_value.amount` |
| **%** | MWRR (solid) | `mwrr × 100` |
| **%** | TWRR (dashed) | `twrr × 100` |
| **%** | ROI (dotted) | `roi × 100` |

ECharts diretto (non `LineChart.svelte` che è single-series).

### 7.3 portfolioStore (Svelte 5 runes)

```typescript
// Cache key: broker_ids + date range
let summaryCache = $state(new Map<CacheKey, CacheEntry<PortfolioSummary>>());
let historyCache = $state(new Map<CacheKey, CacheEntry<PortfolioHistoryPoint[]>>());

// API: POST /portfolio/summary e POST /portfolio/history
// Invalidazione: su CRUD transazioni + import CSV + click ↻
```

---

## 8. Problemi Noti e Questioni Aperte

### 8.1 MWRR Numerica — Annualizzazione su periodi brevi

**Fenomeno:** MWRR = 1.17×10^16 per +50% in 4 giorni (matematicamente corretto, informativamente inutile).

**Causa:** annualizzare un rendimento breve produce valori astronomici.

**Fix applicato:** cap `abs(rate) > 100.0` → return `None`.

**Problemi residui del fix:**
- Crypto legittimamente può avere >10000% su periodi brevi
- Warm-start non si aggiorna quando un valore viene rifiutato

**Alternative principiate discusse:**
- Minimum period check: skip MWRR se `total_days < 30`
- Cap relativo al periodo: `max_annual = (1 + max_daily)^(365/days)`
- Rendimento grezzo non annualizzato (cambio semantica API)

### 8.2 get_asset_history() — ROI per singolo asset DEFERRED

`AssetHistoryPoint` ha `wac` in base currency ma `market_price` in asset currency → unità miste.  
Per ROI corretto servono FX call per ogni data di prezzo (costoso).  
**Stato:** deferred a fase dedicata.

### 8.3 Cash Algebra storica (Round 4 — non ancora eseguito)

`get_summary()` derivava cash solo da DEPOSIT/WITHDRAWAL, ignorando l'effetto cash di BUY/SELL/DIVIDEND/FEE/TAX.  
**Fix progettato in Round 4:** usare ledger algebrico completo per la cash.  
**Stato:** piano scritto (`plan-phase09Step2Round4-CashMtMTransparency.prompt.md`), non eseguito.

### 8.4 Asset senza PriceHistory

P2P loans e asset manuali senza provider → esclusi dal NAV → `missing_prices_assets` tracciato ma non ancora mostrato nel dashboard UI.  
**Fix:** seeding di un punto nominale via `PriceHistory` + banner amber nel dashboard.

### 8.5 Seed dati mock non realistici

`populate_mock_data.py` creava transazioni prima dei prezzi → amount non derivata dal prezzo → MWRR sballato nel seed.  
**Piano Round 3:** invertire ordine (prezzi prima, poi amount = qty × price).

---

## 9. Stato Implementazione al Momento del Blocco

| Componente | Stato |
|------------|-------|
| `roi_utils.py` — TWRR/MWRR/ROI pure math | ✅ Completo |
| `portfolio_service.get_history()` — dense daily + MtM | ✅ Completo |
| `portfolio_service.get_summary()` — allocations + ROI | ✅ Completo (cash algebra parziale) |
| `portfolio.py` schemas (Currency payload) | ✅ Completo |
| API routes POST `/portfolio/summary` + `/history` | ✅ Completo |
| `portfolioStore.svelte.ts` | ✅ Completo |
| `GrowthChart.svelte` — toggle Abs/% + ECharts multi-serie | ✅ Completo |
| `KpiCard.svelte` | ✅ Completo |
| `RecentTransactionsPanel.svelte` | ✅ Completo |
| Allocation panel — SectorPieChart + GeographyMap | ✅ Completo |
| MWRR stabilità numerica — cap fix | ✅ Applicato (parziale) |
| Cash algebra ledger completo (Round 4) | ❌ Non eseguito |
| P2P loan nominal pricing nel seed | ❌ Non eseguito |
| Dashboard warning banner missing data | ❌ Non eseguito |
| ROI per singolo asset (get_asset_history) | ❌ Deferred |
| Seed mock dati realistici (Round 3+) | ❌ Parziale |

---

## 10. Domande Chiave per AI Analyst

Le seguenti domande sono state identificate nel progetto come aperte e richiedono analisi:

1. **MWRR su periodi brevi:** qual è la strategia ottimale — minimum period floor, cap relativo, o rendimento non annualizzato?
2. **Allocation granularità:** le allocazioni attuali usano market value corrente. Sarebbe utile aggiungere viste su cost basis? Su delta (gain/loss per categoria)?
3. **Risk metrics mancanti:** Sharpe ratio, volatility, max drawdown — hanno senso con dati giornalieri scarsi? Come gestire la mancanza di prezzi per alcuni giorni?
4. **Correlazione multi-asset:** dati sufficienti per matrice di correlazione? Che utilità per l'utente self-hosted?
5. **Benchmark:** confronto con indici (S&P500, MSCI World) — già presente come `AssetComparisonSignal` nei grafici asset, ma non a livello portfolio dashboard.
6. **Liquidità vs NAV:** la separazione `cash_value + invested_value` è già presente. Si potrebbe evidenziare meglio l'evoluzione del "cash drag"?

---

*Fine report — generato automaticamente da sessione Copilot 2026-06-19.*

