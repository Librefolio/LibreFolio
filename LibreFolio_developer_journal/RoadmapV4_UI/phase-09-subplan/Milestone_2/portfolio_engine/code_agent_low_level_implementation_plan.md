# Portfolio Engine — Low-Level Implementation Plan

**Data:** 2026-06-19
**Design di riferimento:** `gpt5.5_high_level_design_v2.md`
**Review di coerenza:** `code_agent_coherence_review.md`
**Agente:** Claude Opus 4.6

---

## 1. Obiettivo (sintesi)

Sostituire le logiche sparse in `PortfolioService.get_summary()` e `get_history()` con un unico **PortfolioCalculationEngine** runtime (no cache) che:

1. Classifica le transazioni come internal/external rispetto allo scope broker selezionato
2. Calcola un `DailyPortfolioState[]` completo (cash, market_value, in-transit, NAV, book_value, allocation, data quality)
3. Deriva summary/history/allocation/performance come viste su quel vettore
4. Corregge 6 bug noti (NAV flat in TWRR, quantity tracking incompleta, naming ambiguo, ecc.)
5. Introduce `DataQualityReport`, `MissingPriceAsset` ricco, stale prices, in-transit

### Punti ancora ambigui pre-implementazione

| # | Punto | Decisione proposta |
|---|-------|-------------------|
| 1 | Threshold stale price (quanti giorni?) | Piano v2 dice 7 giorni calendario → adottare |
| 2 | `share_percentage` in-transit: share sorgente o destinazione? | Piano v2 dice share sorgente → adottare |
| 3 | Allocation su NAV incompleto: calcolare su subset o escludere? | Piano v2 dice calcolare su subset + warning → adottare |
| 4 | Sampling allocation history (daily vs weekly) | Primo rilascio: solo daily, aggiungere sampling dopo se serve |
| 5 | `net_worth` alias di `nav_value` in API? | Piano v2 dice sì → mantenere entrambi, internamente `nav_value` |

---

## 2. File di riferimento analizzati

| File | LOC | Ruolo nel refactor |
|------|-----|-------------------|
| `backend/app/db/models.py` | ~900 | Solo lettura — nessuna modifica DB |
| `backend/app/services/portfolio_service.py` | ~1220 | **Da sostituire progressivamente** — get_summary/get_history diventano adapter |
| `backend/app/services/fx.py` | ~400 | Riusare `convert_bulk()` — nessuna modifica |
| `backend/app/utils/financial/roi_utils.py` | ~320 | Riusare tutto — nessuna modifica |
| `backend/app/utils/financial/wac_utils.py` | ~160 | Riusare `compute_wac_from_txlist()` — nessuna modifica |
| `backend/app/utils/financial/fifo_utils.py` | ~100 | Non usato nel nuovo engine (FIFO rimandato) |
| `backend/app/utils/financial/valuation_utils.py` | 27 | Riusare `compute_holding_value()` — nessuna modifica |
| `backend/app/schemas/portfolio.py` | ~215 | **Da modificare** — rename + nuovi campi |
| `backend/app/schemas/wac.py` | ~80 | Solo lettura — `WACMissingPairInfo` riusato |
| `backend/app/api/v1/portfolio_api.py` | ~100 | **Da modificare** — adapter + nuovo endpoint |
| `frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts` | ~120 | **Da aggiornare** dopo api sync |
| `frontend/src/routes/(app)/dashboard/+page.svelte` | ~500 | **Da aggiornare** — KPI, banner, allocation |
| `frontend/src/lib/components/dashboard/GrowthChart.svelte` | ~300 | **Da riscrivere stacked** — ABS con stacked book_value |
| `frontend/src/lib/components/charts/AllocationPieChart.svelte` | ~200 | Riusare — aggiungere toggle Ora/Storia wrapper |

---

## 3. Piano implementativo basso livello

---

### STEP A — Backend Schemas / DTO

**PR isolabile: sì — safe, API breaking, richiede frontend sync**

#### A.1 Nuovi schema in `backend/app/schemas/portfolio.py`

**File:** `backend/app/schemas/portfolio.py`

```python
# NUOVI DTO
class MissingPriceAsset(BaseModel):
    asset_id: int
    symbol: Optional[str]
    name: str
    broker_id: int
    broker_name: str
    first_position_date: date_type
    quantity: SafeDecimal
    open_cost_basis: Optional[SafeDecimal]
    currency: str

class StalePriceAsset(BaseModel):
    asset_id: int
    name: str
    last_price_date: date_type
    stale_days: int

class DataQualityReport(BaseModel):
    missing_price_assets: List[MissingPriceAsset] = Field(default_factory=list)
    missing_fx_pairs: List[WACMissingPairInfo] = Field(default_factory=list)
    stale_prices: List[StalePriceAsset] = Field(default_factory=list)
    incomplete_nav_dates: List[date_type] = Field(default_factory=list)
    incomplete_book_value_dates: List[date_type] = Field(default_factory=list)
    incomplete_allocation_dates: List[date_type] = Field(default_factory=list)
    in_transit_cost_basis_warnings: List[str] = Field(default_factory=list)
    share_mismatch_warnings: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
```

#### A.2 Modifica `PortfolioHistoryPoint`

**File:** `backend/app/schemas/portfolio.py`
**Breaking change:** `invested_value` → `market_value`

```python
class PortfolioHistoryPoint(BaseModel):
    date: date_type
    cash_value: Currency
    market_value: Currency          # WAS: invested_value
    broker_nav_value: Currency      # NEW
    in_transit_cash_value: Optional[Currency] = None           # NEW
    in_transit_asset_market_value: Optional[Currency] = None   # NEW
    in_transit_market_value: Optional[Currency] = None         # NEW
    nav_value: Currency
    open_cost_basis: Optional[Currency] = None                 # NEW
    in_transit_asset_cost_basis: Optional[Currency] = None     # NEW
    in_transit_book_value: Optional[Currency] = None           # NEW
    book_value: Optional[Currency] = None                      # NEW
    unrealized_gain_loss: Optional[Currency] = None            # NEW
    twrr: Optional[SafeDecimal] = None
    mwrr: Optional[SafeDecimal] = None
    roi: Optional[SafeDecimal] = None
```

#### A.3 Modifica `PortfolioSummary`

**File:** `backend/app/schemas/portfolio.py`

Aggiungere campi:

```python
# Nuovi campi in PortfolioSummary
market_value: Currency              # NEW (era implicito)
broker_nav_value: Currency          # NEW
in_transit_market_value: Optional[Currency] = None  # NEW
open_cost_basis: Optional[Currency] = None          # NEW
in_transit_book_value: Optional[Currency] = None    # NEW
book_value: Optional[Currency] = None               # NEW
unrealized_gain_loss: Optional[Currency] = None     # NEW
data_quality: Optional[DataQualityReport] = None    # NEW

# Cambiare missing_prices_assets da List[str] a:
missing_price_assets: List[MissingPriceAsset] = Field(default_factory=list)
# Deprecare il vecchio:
missing_prices_assets  # → rimuovere
```

#### A.4 Nuovo `AllocationHistoryResponse`

```python
class AllocationHistoryPoint(BaseModel):
    date: date_type
    components: List[AllocationItem]

class AllocationHistoryQuery(BaseModel):
    broker_ids: Optional[List[int]] = None
    date_range: Optional[OpenDateRangeModel] = None
    target_currency: Optional[str] = None
    dimension: str = Field("type", pattern="^(type|sector|geography)$")

class AllocationHistoryResponse(BaseModel):
    dimension: str
    series: List[AllocationHistoryPoint]
    data_quality: Optional[DataQualityReport] = None
```

#### A.5 Funzioni da deprecare/rimuovere

| Funzione/campo | File | Azione |
|----------------|------|--------|
| `invested_value` in `PortfolioHistoryPoint` | `schemas/portfolio.py:166` | Rinominare → `market_value` |
| `invested_value` in `_HistoryCalcPoint` | `portfolio_service.py:324` | Rinominare → `market_value` |
| `missing_prices_assets: List[str]` | `schemas/portfolio.py:155-158` | Sostituire con `missing_price_assets: List[MissingPriceAsset]` |

#### A.6 Test

- Validazione Pydantic dei nuovi DTO
- Serializzazione JSON round-trip
- Verifica breaking field non nullo dove richiesto

---

### STEP B — Portfolio Engine Core

**PR isolabile: sì — safe, non rompe API (le API continuano a usare il vecchio codice finché non si collegano)**

#### B.1 Nuovo file: `backend/app/services/portfolio_engine.py`

**Struttura:**

```python
# ──────────────────────────────────────────
# Dataclass interne (non DTO — oggetti runtime)
# ──────────────────────────────────────────

@dataclass
class ClassifiedTransaction:
    """Transazione classificata dal ScopeAwareTransactionClassifier."""
    tx: Transaction
    classification: Literal["normal", "linked_internal", "linked_external_inflow",
                            "linked_external_outflow", "ignored"]
    paired_tx: Optional[Transaction]
    in_transit_interval: Optional[tuple[date, date]]  # (start_excl, end_excl) o None
    share: Decimal  # share_percentage del broker di questa tx

@dataclass
class InTransitInterval:
    """Intervallo in-transit per una coppia linked."""
    start_date: date   # departure_date + 1
    end_date: date     # arrival_date - 1
    tx_type: str       # "cash" | "asset"
    departure_leg: Transaction
    arrival_leg: Transaction
    share: Decimal
    # Per asset:
    asset_id: Optional[int]
    cost_basis_amount: Optional[Decimal]  # cbo o fallback WAC
    cost_basis_currency: Optional[str]

@dataclass
class DailyPortfolioState:
    """Stato giornaliero completo — cuore del sistema."""
    date: date
    # Valuation
    cash_value: Decimal
    market_value: Decimal
    broker_nav_value: Decimal
    in_transit_cash_value: Decimal
    in_transit_asset_market_value: Decimal
    in_transit_market_value: Decimal
    nav_value: Decimal
    # Accounting
    open_cost_basis: Decimal
    in_transit_asset_cost_basis: Decimal
    in_transit_book_value: Decimal
    book_value: Decimal
    unrealized_gain_loss: Decimal
    # Performance inputs
    external_cash_flow: Decimal
    # Allocation
    by_type: dict[str, Decimal]       # asset_type → market_value
    by_sector: dict[str, Decimal]     # sector → market_value
    by_geography: dict[str, Decimal]  # country → market_value
    # Data quality
    missing_price_asset_ids: set[int]
    missing_fx_pairs: set[str]
    stale_price_asset_ids: set[int]
    nav_complete: bool

@dataclass
class PortfolioCalculationResult:
    """Risultato completo del motore."""
    daily_states: list[DailyPortfolioState]
    data_quality: DataQualityReport  # aggregato
    # Metadati
    scope_broker_ids: list[int]
    target_currency: str
    date_from: date
    date_to: date

# ──────────────────────────────────────────
# Classi principali
# ──────────────────────────────────────────

class ScopeAwareTransactionClassifier:
    ...

class DailyStateBuilder:
    ...

class DerivedViewsBuilder:
    ...

class PortfolioCalculationEngine:
    ...
```

#### B.2 `ScopeAwareTransactionClassifier`

**Input:**
- `scope_broker_ids: set[int]`
- `all_transactions: list[Transaction]` (da tutti i broker dello scope)
- `broker_shares: dict[int, Decimal]` (broker_id → share_percentage)

**Output:**
- `classified: list[ClassifiedTransaction]`
- `in_transit_intervals: list[InTransitInterval]`
- `external_cash_flows: list[tuple[date, Decimal]]` (date, amount in tx currency)
- `quality_warnings: list[str]`

**Algoritmo:**

```python
def classify(self) -> ClassificationResult:
    # 1. Raccogliere tutti i related_transaction_id presenti nello scope
    tx_by_id = {tx.id: tx for tx in self.all_transactions}
    
    # 2. Per linked tx, caricare anche la paired tx se fuori scope
    #    (serve per sapere se è internal o external)
    paired_ids_needed = set()
    for tx in self.all_transactions:
        if tx.related_transaction_id and tx.related_transaction_id not in tx_by_id:
            paired_ids_needed.add(tx.related_transaction_id)
    # → query DB per paired_ids_needed (async, passata dall'esterno)
    
    # 3. Classificare ogni tx
    for tx in self.all_transactions:
        if tx.related_transaction_id is None:
            # Non linked → "normal"
            # Se DEPOSIT/WITHDRAWAL → external cash flow
            ...
        else:
            paired = tx_by_id.get(tx.related_transaction_id) or external_paired.get(tx.related_transaction_id)
            if paired is None:
                # Paired tx non trovata → trattare come normal + warning
                ...
            elif paired.broker_id in self.scope_broker_ids:
                # Entrambe le leg nello scope → "linked_internal"
                if tx.date != paired.date:
                    # In-transit interval
                    ...
            else:
                # Solo questa leg nello scope → "linked_external_inflow/outflow"
                ...
    
    # 4. Share percentage
    for ctxn in classified:
        ctxn.share = self.broker_shares.get(ctxn.tx.broker_id, Decimal("1"))
        # Warning se share sorgente != share destinazione per linked internal
```

**Funzioni esistenti da riusare:**
- Nessuna — logica nuova, ma usa dati dal Transaction model esistente

**Funzioni esistenti da sostituire:**
- `_CASH_FLOW_TYPES = {DEPOSIT, WITHDRAWAL}` in `portfolio_service.py:416` — troppo restrittivo

**Dipendenze:**
- `Transaction` model (read)
- `BrokerUserAccess` per `share_percentage` (read)
- DB query per paired tx fuori scope (async)

**Test:**
- `test_scope_classifier_internal_same_day`
- `test_scope_classifier_internal_different_dates`
- `test_scope_classifier_external_outflow`
- `test_scope_classifier_external_inflow`
- `test_scope_classifier_fx_conversion`
- `test_scope_classifier_asset_transfer`
- `test_scope_classifier_unlinked_deposit`
- `test_scope_classifier_share_mismatch_warning`

#### B.3 `DailyStateBuilder`

**Input (pre-caricati, niente I/O):**
- `classified_txs: list[ClassifiedTransaction]`
- `in_transit_intervals: list[InTransitInterval]`
- `external_cash_flows: list[tuple[date, Decimal]]`
- `price_map: dict[int, list[tuple[date, Decimal, str]]]` (asset_id → sorted prices)
- `quote_base_map: dict[int, int | None]`
- `wac_series: dict[tuple[int, int], list[tuple[date, Decimal, str]]]` (asset/broker → sorted WAC points with currency)
- `fx_converter: Callable` (batch FX, pre-caricato o lazy)
- `asset_classification: dict[int, FAClassificationParams | None]`
- `asset_types: dict[int, str]`
- `target_currency: str`
- `date_from: date`
- `date_to: date`

**Output:**
- `list[DailyPortfolioState]` — un punto per giorno

**Algoritmo ad alto livello:**

```python
def build(self) -> list[DailyPortfolioState]:
    # 1. Calcolare CashLedger: cumulative amount per day
    cash_deltas = defaultdict(Decimal)  # date → sum of amount * share
    for ctxn in self.classified_txs:
        if ctxn.tx.amount and ctxn.tx.amount != 0:
            # Convertire in target_currency
            converted = self._convert_amount(ctxn.tx.amount, ctxn.tx.currency, ctxn.tx.date)
            if converted is not None:
                cash_deltas[ctxn.tx.date] += converted * ctxn.share
    
    # 2. Calcolare QuantityLedger: cumulative qty per (asset_id, broker_id) per day
    qty_deltas = defaultdict(lambda: defaultdict(Decimal))
    for ctxn in self.classified_txs:
        if ctxn.tx.quantity and ctxn.tx.quantity != 0 and ctxn.tx.asset_id:
            key = (ctxn.tx.asset_id, ctxn.tx.broker_id)
            qty_deltas[ctxn.tx.date][key] += ctxn.tx.quantity * ctxn.share
    
    # 3. Dense daily loop
    states = []
    cumulative_cash = Decimal("0")
    cumulative_qty: dict[tuple[int,int], Decimal] = defaultdict(Decimal)
    cumulative_ecf = Decimal("0")
    
    current = self.date_from
    while current <= self.date_to:
        # 3a. Update cash
        cumulative_cash += cash_deltas.get(current, Decimal("0"))
        
        # 3b. Update quantities
        for key, delta in qty_deltas.get(current, {}).items():
            cumulative_qty[key] += delta
        
        # 3c. Market value (per asset/broker con qty > 0)
        market_value = Decimal("0")
        by_type, by_sector, by_geo = {}, {}, {}
        missing, stale = set(), set()
        for (asset_id, broker_id), qty in cumulative_qty.items():
            if qty <= 0:
                continue
            mv, price_ok, stale_flag = self._market_value_for(asset_id, qty, current)
            if mv is not None:
                market_value += mv
                self._distribute_allocation(asset_id, mv, by_type, by_sector, by_geo)
            if not price_ok:
                missing.add(asset_id)
            if stale_flag:
                stale.add(asset_id)
        
        # 3d. In-transit values
        it_cash, it_asset_mv, it_asset_cb = self._compute_in_transit(current)
        
        # 3e. WAC / open_cost_basis
        open_cost_basis = self._compute_open_cost_basis(cumulative_qty, current)
        
        # 3f. Compose
        broker_nav = market_value + cumulative_cash
        in_transit_mv = it_cash + it_asset_mv
        nav = broker_nav + in_transit_mv
        in_transit_bv = it_cash + it_asset_cb
        book = open_cost_basis + cumulative_cash + in_transit_bv
        ug = nav - book
        
        # 3g. External cash flow for this day
        ecf_today = sum(a for d, a in self.external_cash_flows if d == current)
        
        # 3h. Allocation: add cash as Liquidity
        by_type["Liquidity"] = by_type.get("Liquidity", Decimal("0")) + cumulative_cash + it_cash
        by_sector["Liquidity"] = by_sector.get("Liquidity", Decimal("0")) + cumulative_cash + it_cash
        # geography: cash non è paese — non aggiungere
        
        states.append(DailyPortfolioState(
            date=current, cash_value=cumulative_cash, market_value=market_value,
            broker_nav_value=broker_nav,
            in_transit_cash_value=it_cash, in_transit_asset_market_value=it_asset_mv,
            in_transit_market_value=in_transit_mv, nav_value=nav,
            open_cost_basis=open_cost_basis, in_transit_asset_cost_basis=it_asset_cb,
            in_transit_book_value=in_transit_bv, book_value=book,
            unrealized_gain_loss=ug,
            external_cash_flow=ecf_today,
            by_type=by_type, by_sector=by_sector, by_geography=by_geo,
            missing_price_asset_ids=missing, missing_fx_pairs=set(),
            stale_price_asset_ids=stale,
            nav_complete=len(missing)==0,
        ))
        current += timedelta(days=1)
    
    return states
```

**Funzioni helper interne:**

```python
def _market_value_for(self, asset_id, qty, d) -> tuple[Decimal|None, bool, bool]:
    """Calcola market_value per un asset, gestendo quote_base_quantity e FX."""
    # Usa _price_on_date() da portfolio_service.py (logica identica)
    # Usa compute_holding_value() da valuation_utils.py
    # Converte da price_currency a target_currency
    # Ritorna (value, price_found, is_stale)
    ...

def _compute_in_transit(self, d) -> tuple[Decimal, Decimal, Decimal]:
    """Calcola in_transit_cash, in_transit_asset_mv, in_transit_asset_cb per giorno d."""
    it_cash = Decimal("0")
    it_asset_mv = Decimal("0")
    it_asset_cb = Decimal("0")
    for interval in self.in_transit_intervals:
        if interval.start_date <= d <= interval.end_date:
            if interval.tx_type == "cash":
                # abs(departure_leg.amount) convertito in target_currency
                ...
                it_cash += value * interval.share
            else:  # asset
                # qty × price × FX per market value
                ...
                it_asset_mv += mv * interval.share
                # cost_basis_amount × FX per cost basis
                ...
                it_asset_cb += cb * interval.share
    return it_cash, it_asset_mv, it_asset_cb

def _compute_open_cost_basis(self, cumulative_qty, d) -> Decimal:
    """WAC forward-fill × quantity per ogni asset/broker con qty > 0."""
    total_ocb = Decimal("0")
    for (asset_id, broker_id), qty in cumulative_qty.items():
        if qty <= 0:
            continue
        wac_series = self.wac_series.get((asset_id, broker_id), [])
        wac_val, wac_ccy = self._wac_on_date(wac_series, d)
        if wac_val is not None:
            ocb_in_wac_ccy = wac_val * qty
            # Convertire da wac_ccy a target_currency
            converted = self._convert(ocb_in_wac_ccy, wac_ccy, d)
            if converted is not None:
                total_ocb += converted
    return total_ocb
```

**Funzioni esistenti da riusare:**
- `compute_holding_value()` da `valuation_utils.py`
- `_price_on_date()` logica da `portfolio_service.py:336-353` (copiare come pure function)
- `convert_bulk()` da `fx.py` (pre-batch all FX needs)

**Funzioni da sostituire:**
- `_build_history_series()` in `portfolio_service.py:356-407` → sostituita da DailyStateBuilder
- `_HistoryCalcPoint` in `portfolio_service.py:319-328` → sostituita da DailyPortfolioState

**Rischi:**
- Complessità dell'FX batching (many currencies × many days)
- In-transit con asset senza `cost_basis_override` → fallback WAC richiede query extra

**Test:**
- `test_daily_state_cash_ledger_all_types`
- `test_daily_state_quantity_includes_transfer_adjustment`
- `test_daily_state_market_value_with_quote_base`
- `test_daily_state_nav_formula`
- `test_daily_state_book_value_formula`
- `test_daily_state_unrealized_gain_loss`
- `test_daily_state_in_transit_cash`
- `test_daily_state_in_transit_asset`
- `test_daily_state_allocation_liquidity`
- `test_daily_state_missing_price_flagging`
- `test_daily_state_stale_price_detection`

#### B.4 `DerivedViewsBuilder`

**Input:**
- `daily_states: list[DailyPortfolioState]`
- `target_currency: str`

**Output (metodi):**

```python
def build_summary(self, holdings_data, broker_data) -> PortfolioSummary
def build_history(self, date_from, date_to) -> list[PortfolioHistoryPoint]
def build_performance(self, date_from) -> tuple[list, list, list]  # twrr, mwrr, roi series
def build_allocation_current(self) -> tuple[list, list, list]  # by_type, by_sector, by_geo
def build_allocation_history(self, dimension) -> list[AllocationHistoryPoint]
def build_data_quality_report(self) -> DataQualityReport
```

**Funzioni da riusare:**
- `calculate_twrr_series()` da `roi_utils.py`
- `calculate_mwrr_series()` da `roi_utils.py` (wrappata in `asyncio.to_thread`)
- `calculate_simple_roi_series()` da `roi_utils.py`
- `AllocationItem` schema esistente

**Performance da DailyPortfolioState:**

```python
def build_performance(self, date_from) -> ...:
    # NAV series = [NAVSnapshot(d.date, d.nav_value) for d in self.daily_states if d.date >= date_from]
    # Cash flows = [CashFlowInput(d.date, -d.external_cash_flow) for d in self.daily_states
    #               if d.external_cash_flow != 0 and d.date >= date_from]
    # → calculate_twrr_series(nav_series, cash_flows)
    # → calculate_simple_roi_series(nav_series, cash_flows)
    # → asyncio.to_thread(calculate_mwrr_series, nav_series, cash_flows)
```

**Questo corregge il bug NAV flat:** il `get_summary()` attuale usa `NAVSnapshot(d, total_nav)` con un unico total_nav per tutte le date. Il nuovo engine produce NAV giornaliero reale da DailyPortfolioState.

#### B.5 `PortfolioCalculationEngine`

**Orchestrator principale — classe async.**

```python
class PortfolioCalculationEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def calculate(
        self,
        user_id: int,
        broker_ids: list[int] | None,
        date_from: date | None,
        date_to: date | None,
        target_currency: str,
    ) -> PortfolioCalculationResult:
        # 1. Resolve scope
        accesses = await self._get_user_broker_access(user_id, broker_ids)
        scope_broker_ids = {a.broker_id for a in accesses}
        broker_shares = {a.broker_id: a.share_percentage or Decimal("1") for a in accesses}
        
        # 2. Load ALL transactions for scope brokers
        all_txs = await self._load_transactions(scope_broker_ids, date_to)
        
        # 3. Classify
        classifier = ScopeAwareTransactionClassifier(scope_broker_ids, all_txs, broker_shares)
        # Need to load paired txs for linked ones outside scope
        paired_ids = classifier.get_needed_paired_ids()
        external_paired = await self._load_transactions_by_ids(paired_ids)
        classification = classifier.classify(external_paired)
        
        # 4. Determine date range
        first_tx_date = min(tx.date for tx in all_txs) if all_txs else date.today()
        actual_from = date_from or first_tx_date
        actual_to = date_to or date.today()
        
        # 5. Preload prices (bulk)
        held_asset_ids = {tx.asset_id for tx in all_txs if tx.asset_id and tx.quantity and tx.quantity != 0}
        price_map = await self._bulk_load_prices(held_asset_ids, actual_from, actual_to)
        quote_base_map = await self._load_quote_base(held_asset_ids)
        
        # 6. Preload WAC (forward-fill)
        wac_series = await self._build_wac_series(
            held_asset_ids, scope_broker_ids, actual_to, target_currency
        )
        
        # 7. Preload asset classification
        asset_classification = await self._load_asset_classification(held_asset_ids)
        asset_types = await self._load_asset_types(held_asset_ids)
        
        # 8. Build daily states
        builder = DailyStateBuilder(
            classified_txs=classification.classified,
            in_transit_intervals=classification.in_transit_intervals,
            external_cash_flows=classification.external_cash_flows,
            price_map=price_map,
            quote_base_map=quote_base_map,
            wac_series=wac_series,
            asset_classification=asset_classification,
            asset_types=asset_types,
            target_currency=target_currency,
            date_from=actual_from,
            date_to=actual_to,
            db=self.db,  # per FX convert_bulk
        )
        daily_states = await builder.build()
        
        # 9. Return result
        dq = DerivedViewsBuilder(daily_states, target_currency).build_data_quality_report()
        return PortfolioCalculationResult(
            daily_states=daily_states,
            data_quality=dq,
            scope_broker_ids=list(scope_broker_ids),
            target_currency=target_currency,
            date_from=actual_from,
            date_to=actual_to,
        )
```

**Funzioni helper da migrare da `PortfolioService`:**

| Funzione in PortfolioService | Azione |
|------------------------------|--------|
| `_get_user_broker_access()` | Copiare in engine |
| `_bulk_load_asset_prices()` | Copiare in engine |
| `_get_quote_base_map()` | Copiare in engine |
| `_get_base_currency()` | Riusare via `get_global_setting` |
| `_convert_to_base()` | Non copiare — usare `convert_bulk` direttamente |
| `_merge_missing_pairs()` | Copiare come utility statica |

**Nuove funzioni:**

```python
async def _build_wac_series(self, asset_ids, broker_ids, as_of, target_currency):
    """Per ogni (asset_id, broker_id) computa WAC as_of e estrae running_wac."""
    result = {}
    for asset_id in asset_ids:
        for broker_id in broker_ids:
            wac_result = await compute_wac_iterative(
                self.db, broker_id, asset_id, as_of,
                asset_currency=..., # da Asset.currency
            )
            if wac_result.wac and wac_result.wac_qualifying_txs:
                points = [
                    (q.date, q.running_wac, wac_result.wac.code)
                    for q in wac_result.wac_qualifying_txs
                    if q.running_wac is not None
                ]
                result[(asset_id, broker_id)] = sorted(points, key=lambda p: p[0])
    return result

async def _load_transactions_by_ids(self, tx_ids: set[int]):
    """Carica transazioni per ID (per paired tx fuori scope)."""
    ...
```

---

### STEP C — Scope-aware linked transactions

**Incorporato nello Step B.2 (ScopeAwareTransactionClassifier)**

Dettagli aggiuntivi per i casi:

#### C.1 CASH_TRANSFER

```python
# Entrambe le leg nello scope, stessa data:
# → linked_internal, external_cf = 0, in_transit = none
# Entrambe le leg nello scope, date diverse:
# → linked_internal, external_cf = 0, in_transit cash
# Solo una leg nello scope:
# → linked_external_inflow o outflow, external_cf = amount
```

#### C.2 FX_CONVERSION

```python
# Stessa logica di CASH_TRANSFER.
# Nota: FX_CONVERSION può essere intra-broker.
# Se intra-broker → linked_internal per definizione (stesso broker = nello scope se broker è nello scope)
# In-transit su FX: usare leg negativa (amount < 0) come valore in transito
```

#### C.3 TRANSFER (asset)

```python
# Leg OUT: quantity < 0, amount = 0, broker_id = source
# Leg IN: quantity > 0, amount = 0, broker_id = dest, cost_basis_override opzionale
# Se entrambi nello scope, stessa data:
# → linked_internal, quantity si sposta, market_value invariato
# Se date diverse:
# → in_transit_asset con qty_in_transit = abs(departure_leg.quantity)
# In-transit cost basis:
#   1. arrival_leg.cost_basis_override × arrival_leg.quantity (se presente)
#   2. fallback: WAC(source_broker, asset, departure_date) × qty
#   3. se nessuno: warning, cost_basis = 0
```

#### C.4 ADJUSTMENT linked

```python
# Stessa logica di TRANSFER.
# La differenza è che ADJUSTMENT ha related_transaction_id OPZIONALE.
# Se related_transaction_id è presente → trattare come transfer.
# Se assente → evento standalone (split, gift), non è un transfer.
```

#### C.5 share_percentage

```python
# Per ogni tx: share = broker_shares[tx.broker_id]
# Per in-transit: share = share del broker sorgente (departure_leg.broker_id)
# Se share_source != share_dest → DataQuality warning
```

**Rischi:**
- Paired tx fuori scope richiede query DB extra (un roundtrip)
- FX_CONVERSION con date diverse è edge case raro ma va gestito

---

### STEP D — Valuation

**Incorporato nello Step B.3 (DailyStateBuilder)**

#### D.1 cash_value

```python
# Cumulative sum of amount * share for all txs in scope
# Tutti i tipi — nessun filtro per TransactionType
# Conversione in target_currency via convert_bulk
```

#### D.2 Quantity ledger

```python
# Cumulative qty per (asset_id, broker_id)
# Include: BUY, SELL, TRANSFER, ADJUSTMENT (tutto ciò con quantity != 0)
# Corregge bug attuale: _HOLDING_TYPES = {BUY, SELL} ignorava TRANSFER/ADJUSTMENT
```

#### D.3 Market value

```python
market_value = compute_holding_value(qty, price, quote_base_qty) * fx_rate
# Dove: compute_holding_value = (qty / quote_base) * raw_price
# Riusare valuation_utils.py
```

#### D.4 Price lookup

```python
# Riusare logica _price_on_date() da portfolio_service.py
# Backward-fill: latest price con date <= query_date
# Stale detection: se (query_date - price_date).days > 7 → stale
```

#### D.5 FX conversion strategy

```python
# BATCH: raccogliere tutte le conversioni necessarie per il giorno
# Prima pass: collezionare richieste (amount, from_ccy, to_ccy, date)
# Una chiamata convert_bulk() per giorno (o raggruppata per più giorni)
# Risultati cachati per la durata del calcolo
```

**Ottimizzazione FX:**

```python
# Pre-caricare tutte le FX rates necessarie in una sola query
# Il motore sa in anticipo quali coppie servono (tx currencies × target_currency)
# Costruire un dict locale: (from_ccy, to_ccy, date) → rate
# Fallback a convert_bulk() per coppie mancanti
```

#### D.6 Missing/stale prices e missing FX

```python
# Missing price: qty > 0 ma nessun prezzo disponibile
# → mv = None, asset_id aggiunto a missing_price_asset_ids
# → nav_complete = False

# Stale price: prezzo più vecchio di 7 giorni
# → mv calcolato normalmente
# → asset_id aggiunto a stale_price_asset_ids

# Missing FX: conversione fallita
# → valore escluso dalla somma
# → pair aggiunto a missing_fx_pairs
```

---

### STEP E — WAC / Book Value

#### E.1 WAC forward-fill

**Già descritto in B.5 `_build_wac_series`.**

Dettaglio forward-fill:

```python
def _wac_on_date(wac_points: list[tuple[date, Decimal, str]], d: date) -> tuple[Decimal|None, str|None]:
    """Ritorna (wac_amount, wac_currency) per data d usando forward-fill."""
    # wac_points è sorted by date ascending
    # bisect_right per trovare l'ultimo punto <= d
    if not wac_points:
        return None, None
    dates = [p[0] for p in wac_points]
    idx = bisect.bisect_right(dates, d) - 1
    if idx < 0:
        return None, None
    _, wac_val, wac_ccy = wac_points[idx]
    return wac_val, wac_ccy
```

#### E.2 Open cost basis

```python
open_cost_basis(d) = Σ (WAC(asset, broker, d) × qty(asset, broker, d)) convertito in target_ccy
```

**Attenzione doppia conversione:**
- WAC è calcolato nella propria `target_currency` (determinata da `determine_target_currency()`)
- Il portfolio engine ha la `target_currency` della query
- Serve **una sola** conversione: `wac_currency → query_target_currency`

#### E.3 In-transit asset cost basis

```python
# Prima scelta: cost_basis_override della leg ricevente
# Fallback: WAC del broker sorgente alla departure_date
# Fallback finale: 0 + DataQuality warning
```

Implementazione nel `_compute_in_transit()` del DailyStateBuilder.

#### E.4 Book value

```python
book_value(d) = open_cost_basis(d) + cash_value(d) + in_transit_book_value(d)
# dove: in_transit_book_value = in_transit_cash_value + in_transit_asset_cost_basis
```

#### E.5 Unrealized gain/loss

```python
unrealized_gain_loss(d) = nav_value(d) - book_value(d)
```

---

### STEP F — Performance

#### F.1 Input corretti

```python
# NAV series = [NAVSnapshot(d.date, d.nav_value) for d in daily_states]
# External CF = [CashFlowInput(d.date, -d.external_cash_flow) for d in daily_states
#                if d.external_cash_flow != 0]
```

Il segno: `external_cash_flow` nel DailyPortfolioState è **dal punto di vista del portfolio**: positivo = inflow (deposit), negativo = outflow (withdrawal). `CashFlowInput` in roi_utils usa la convenzione opposta (deposit = negative). Da cui il `-`.

#### F.2 TWRR/MWRR/ROI

```python
# Riusare le pure functions esistenti:
twrr_series = calculate_twrr_series(nav_snapshots, cash_flows)
roi_series = calculate_simple_roi_series(nav_snapshots, cash_flows)
mwrr_series = await asyncio.to_thread(calculate_mwrr_series, nav_snapshots, cash_flows)
```

**Nessuna modifica a `roi_utils.py`.**

#### F.3 Bug NAV flat corretto

Il bug attuale (`portfolio_service.py:806`):
```python
nav_snapshots = [NAVSnapshot(d, total_nav) for d in cf_dates] + [NAVSnapshot(today, total_nav)]
```
usa `total_nav` (odierno) per tutte le date storiche.

Nel nuovo engine: NAV è preso da `DailyPortfolioState.nav_value` → corretto per ogni giorno.

#### F.4 Period re-basing

La logica di re-basing per `date_from` (`portfolio_service.py:1019-1035`) viene preservata nel `DerivedViewsBuilder.build_performance()`:

```python
# Se date_from è specificato:
# 1. NAV al period start come synthetic deposit
# 2. Solo CF dopo period start
# 3. TWRR/MWRR calcolati sul periodo selezionato
```

---

### STEP G — API Integration

**PR non isolabile — richiede che il nuovo engine sia funzionante**

#### G.1 `get_summary()` come adapter

**File:** `backend/app/services/portfolio_service.py`

```python
async def get_summary(self, user_id, broker_ids, include_breakdown, target_currency_override):
    base_currency = target_currency_override or await self._get_base_currency()
    engine = PortfolioCalculationEngine(self.db)
    result = await engine.calculate(user_id, broker_ids, None, None, base_currency)
    views = DerivedViewsBuilder(result.daily_states, base_currency)
    
    # Compute derived values
    summary = views.build_summary(...)
    return summary
```

#### G.2 `get_history()` come adapter

```python
async def get_history(self, user_id, broker_ids, date_from, date_to, target_currency_override):
    base_currency = target_currency_override or await self._get_base_currency()
    engine = PortfolioCalculationEngine(self.db)
    result = await engine.calculate(user_id, broker_ids, date_from, date_to, base_currency)
    views = DerivedViewsBuilder(result.daily_states, base_currency)
    
    history = views.build_history(date_from, date_to)
    perf = await views.build_performance(date_from)
    # merge perf into history points
    return history
```

#### G.3 Nuovo endpoint `POST /portfolio/allocation-history`

**File:** `backend/app/api/v1/portfolio_api.py`

```python
@portfolio_router.post("/allocation-history", response_model=AllocationHistoryResponse)
async def get_allocation_history(
    body: AllocationHistoryQuery,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_generator),
) -> AllocationHistoryResponse:
    engine = PortfolioCalculationEngine(session)
    result = await engine.calculate(
        current_user.id, body.broker_ids,
        body.date_range.start if body.date_range else None,
        body.date_range.end if body.date_range else None,
        body.target_currency or "EUR",
    )
    views = DerivedViewsBuilder(result.daily_states, result.target_currency)
    series = views.build_allocation_history(body.dimension)
    return AllocationHistoryResponse(
        dimension=body.dimension, series=series,
        data_quality=result.data_quality,
    )
```

#### G.4 Breaking changes e api sync

| Cambio | File | Impatto |
|--------|------|---------|
| `invested_value` → `market_value` | portfolio.py, portfolio_service.py, GrowthChart.svelte | Breaking API |
| `missing_prices_assets: List[str]` → `missing_price_assets: List[MissingPriceAsset]` | portfolio.py | Breaking API |
| Nuovi campi Optional in PortfolioHistoryPoint | portfolio.py | Non breaking (Optional) |
| Nuovi campi Optional in PortfolioSummary | portfolio.py | Non breaking (Optional) |
| Nuovo endpoint `/allocation-history` | portfolio_api.py | Additive |

**Dopo Step G:** eseguire `./dev.py api sync` per rigenerare il client TypeScript.

---

### STEP H — Frontend

**PR richiede api sync completato**

#### H.1 GrowthChart ABS — riscrittura

**File:** `frontend/src/lib/components/dashboard/GrowthChart.svelte`

Cambio sostanziale nel viewMode `'eur'`:

```typescript
// ATTUALE (linee):
//   NAV (line, solid)
//   Invested Capital (line, dashed)  ← era invested_value = market_value
//   Cash (line, dotted)

// NUOVO (stacked area + overlay):
//   STACKED AREA:
//     open_cost_basis (area)
//     cash_value (area)
//     in_transit_book_value (area)
//   OVERLAY LINE:
//     nav_value (line, solid)
```

**Tooltip** da aggiornare con breakdown completo (NAV, book_value, unrealized_gain_loss, ecc.).

#### H.2 Rename `invested_value` → `market_value`

**File:** `GrowthChart.svelte:71`
```diff
- data: history.map((pt) => (pt.invested_value != null ? Number(pt.invested_value.amount) : null)),
+ data: history.map((pt) => (pt.market_value != null ? Number(pt.market_value.amount) : null)),
```

Ma il GrowthChart sarà riscritto (H.1), quindi il rename avviene naturalmente.

#### H.3 DataQualityBanner

**File:** `frontend/src/routes/(app)/dashboard/+page.svelte`

Attualmente ci sono banner separati per missing prices e missing FX (righe 361-378).

Refactor: usare `summary.data_quality` per un DataQualityBanner unificato:

```svelte
<!-- Nuovo componente: DataQualityBanner.svelte -->
{#if dataQuality?.missing_price_assets?.length > 0}
    <Banner type="amber">
        {$_('dashboard.missingPricesRich', { count: dataQuality.missing_price_assets.length })}
        <!-- Lista con asset_name, broker_name, quantity -->
    </Banner>
{/if}
{#if dataQuality?.stale_prices?.length > 0}
    <Banner type="yellow">...</Banner>
{/if}
```

#### H.4 AllocationPanel Ora/Storia

**File:** `frontend/src/routes/(app)/dashboard/+page.svelte` (riga 398+)

Aggiungere toggle:

```svelte
<SegmentedToggle bind:value={allocationView} options={['now', 'history']} />
{#if allocationView === 'now'}
    <AllocationPieChart data={...} />
{:else}
    <AllocationStackedChart data={allocationHistory} />
{/if}
```

Nuovo componente: `AllocationStackedChart.svelte` — 100% stacked area chart con ECharts.

#### H.5 Geography: Unknown senza cash

**File:** `frontend/src/routes/(app)/dashboard/+page.svelte` (riga 132)

Già gestito: `allocationByGeo` viene da `summary.allocation_by_geography`.

Il backend nel nuovo engine non includerà cash nella geography allocation → il frontend non cambierà logica, ma mostrare sotto la mappa:

```svelte
{#if unknownGeoPercent > 0}
    <p>{$_('dashboard.geoUnknown', { percent: unknownGeoPercent })}</p>
{/if}
```

---

### STEP I — Test Plan

#### I.1 Unit test pure functions — `backend/test_scripts/test_portfolio_engine/`

**Nuovo file:** `test_scope_classifier.py`
```
test_unlinked_deposit → external inflow
test_unlinked_withdrawal → external outflow
test_cash_transfer_internal_same_day → internal, no cf, no transit
test_cash_transfer_internal_diff_dates → internal, no cf, in-transit
test_cash_transfer_external → one leg only, external cf
test_fx_conversion_internal → both legs same broker
test_asset_transfer_internal → quantity moves, NAV stable
test_asset_transfer_external → external flow
test_adjustment_linked → treated as transfer
test_adjustment_standalone → no related, normal
test_share_mismatch_warning → different shares on linked legs
```

**Nuovo file:** `test_daily_state_builder.py`
```
test_cash_ledger_all_types → every TransactionType with amount
test_quantity_ledger_buy_sell_transfer_adjustment
test_market_value_simple → qty × price
test_market_value_bond → qty / quote_base × price
test_market_value_multi_currency → FX conversion
test_nav_formula → mv + cash + in_transit
test_book_value_formula → ocb + cash + in_transit_bv
test_unrealized_gain_loss → nav - book
test_in_transit_cash_window → [dep+1, arr-1]
test_in_transit_asset_market_value → daily price update
test_in_transit_cost_basis_with_cbo → use cost_basis_override
test_in_transit_cost_basis_fallback_wac → fallback to WAC
test_in_transit_cost_basis_missing → warning
test_missing_price_detection
test_stale_price_detection_7_days
test_missing_fx_exclusion
test_allocation_liquidity_in_type_sector
test_allocation_geography_no_cash
test_share_percentage_halves_everything
```

**Nuovo file:** `test_derived_views.py`
```
test_summary_from_daily_states
test_history_output_format
test_performance_uses_daily_nav → not flat NAV
test_performance_excludes_internal_cf
test_performance_includes_external_cf
test_allocation_current_from_last_state
test_allocation_history_daily
test_data_quality_report_aggregation
```

#### I.2 Integration test engine — `test_portfolio_engine_integration.py`

```
test_empty_portfolio → all zeros
test_single_buy → cash down, market_value up
test_buy_then_sell → cash changes, qty changes
test_multi_broker_aggregation → cross-broker with shares
test_multi_currency_portfolio → FX conversion chain
test_internal_transfer_nav_stability → NAV unchanged
test_external_deposit_nav_increase → NAV increases
test_full_lifecycle → deposit, buy, dividend, transfer, sell, withdraw
```

#### I.3 API tests — `test_portfolio_api.py`

```
test_summary_endpoint_new_fields → verify new DTO fields present
test_history_endpoint_market_value_rename → invested_value gone
test_allocation_history_endpoint → new endpoint works
test_data_quality_in_summary → data_quality field populated
```

#### I.4 Frontend smoke — aggiornare E2E esistenti

```
test_dashboard_loads → verify no crash after DTO changes
test_growth_chart_renders → ECharts renders new series
test_allocation_tab_type_sector_geo → tabs work
```

---

## 4. Strategia incrementale (PR sequence)

| PR | Step | Safe? | API Breaking? | Frontend sync? | Testabile isolatamente? |
|----|------|-------|---------------|----------------|------------------------|
| **PR 1** | A — Schema/DTO | ✅ Safe | ⚠️ Breaking (invested_value rename, missing_prices_assets type change) | ✅ Serve api sync + frontend update | ✅ Pydantic unit test |
| **PR 2** | B.2 — ScopeClassifier | ✅ Safe | ❌ No API change | ❌ No | ✅ Pure function unit tests |
| **PR 3** | B.3 — DailyStateBuilder | ✅ Safe | ❌ No API change | ❌ No | ✅ Pure function + integration tests |
| **PR 4** | B.4+B.5 — DerivedViews + Engine | ✅ Safe | ❌ No API change | ❌ No | ✅ Integration tests |
| **PR 5** | G — API adapter wiring | ⚠️ Rischio | ⚠️ Comportamento API cambia (valori più corretti) | ❌ No | ✅ API tests |
| **PR 6** | H.1+H.2+H.3 — Frontend GrowthChart + Banner + rename | ✅ Safe | ❌ No | — (è il frontend) | ✅ E2E smoke |
| **PR 7** | G.3+H.4 — Allocation history endpoint + frontend | ✅ Safe | ✅ Additive | ✅ api sync | ✅ API + E2E |
| **PR 8** | F — Performance validation | ✅ Safe | ❌ No | ❌ No | ✅ Regression tests |

### Nota: PR 1 e PR 2-4 possono procedere in parallelo

PR 1 è uno schema change puro. PR 2-4 sono engine internals. Il collegamento avviene in PR 5.

**Strategia consigliata:** fare PR 1 (schema + frontend + api sync) come primo step autonomo per pulire il naming. Poi PR 2-4 in sequenza per l'engine. Infine PR 5 per collegare.

---

## 5. Rischi e blocchi

### Top rischi

| # | Rischio | Probabilità | Impatto | Mitigazione |
|---|---------|-------------|---------|-------------|
| 1 | **FX batching troppo pesante** su range lunghi (3y × 30 asset × daily) | Media | Performance | Pre-caricare FX rates in-memory, raggruppare per coppia, caricare tutto in una query SQL |
| 2 | **WAC forward-fill errato** se `compute_wac_iterative` cambia currency mid-stream | Bassa | Correttezza | Usare `wac_result.wac.code` consistentemente, test con multi-currency WAC |
| 3 | **In-transit edge case** con FX_CONVERSION intra-broker date diverse | Molto bassa | Correttezza | Gestire come cash in-transit, test specifico |
| 4 | **Regressione performance** passando da 2 query specifiche a 1 engine completo | Media | UX | Profiling prima/dopo, lazy allocation history |
| 5 | **cost_basis_override mancante** su TRANSFER genera in_transit_cost_basis = 0 silenziosamente | Media | Correttezza | DataQuality warning esplicito + test |

### Parti non chiare nel design

1. **Sampling allocation history**: il design v2 dice "da definire lato UI/API" — per il primo rilascio, andare daily senza sampling
2. **Period re-basing**: il design v2 non lo menziona esplicitamente — preservare la logica attuale (synthetic deposit al period start)
3. **Dividendi/interessi e external_cash_flow**: il design dice che un DIVIDEND standalone non è un external cash flow (è un ritorno interno). `roi_utils.py:27` conferma: "Dividends and interest are NOT cash flows". ✅ Coerente

### Assunzioni da confermare

1. `related_transaction_id` è SEMPRE bidirezionale (A→B e B→A) — verificato in `models.py:616-637` ✅
2. `TRANSFER` e `CASH_TRANSFER` richiedono broker diversi — verificato in `transaction_service.py:264-272` ✅
3. `FX_CONVERSION` può essere intra-broker — implicito dal codice (nessun check distinct broker) ✅
4. Tutti gli amount sono già signati correttamente nel DB — verificato da `models.py:602-612` ✅

### Bug esistenti corretti dal nuovo engine

| # | Bug | File attuale | Correzione |
|---|-----|-------------|------------|
| 1 | TWRR in get_summary usa NAV flat su date storiche | `portfolio_service.py:806` | Engine produce NAV daily reale |
| 2 | Quantity tracking solo BUY/SELL | `portfolio_service.py:417` | QuantityLedger include TRANSFER/ADJUSTMENT |
| 3 | `invested_value` significa `market_value` | `portfolio.py:166` | Rename pulito |
| 4 | Missing prices solo `List[str]` | `portfolio.py:155-158` | DTO ricco con quantità e cost basis |
| 5 | Linked tx non classificate per scope | `portfolio_service.py:620-622` | ScopeAwareTransactionClassifier |
| 6 | Summary e history duplicano logiche | multiple | Engine unico, viste derivate |

### Parti da rimandare

| Feature | Motivo |
|---------|--------|
| FIFO/lotti avanzati | Design dice "rimandato" |
| Cache portfolio | Design dice "no cache iniziale" |
| Benchmark | Fuori scope |
| Max drawdown / volatility / Sharpe | Fuori scope |
| Sampling allocation history | Primo rilascio daily, ottimizzare dopo |

---

## 6. Output finale

### Ordine implementativo raccomandato

```
1. PR 1: Schema/DTO (rename + nuovi campi + api sync + frontend update)
2. PR 2: ScopeAwareTransactionClassifier (pure logic + unit tests)
3. PR 3: DailyStateBuilder (pure logic + unit tests)
4. PR 4: DerivedViewsBuilder + PortfolioCalculationEngine (integration tests)
5. PR 5: API adapter wiring (get_summary/get_history → engine) (API tests)
6. PR 6: Frontend GrowthChart rewrite + DataQualityBanner
7. PR 7: Allocation history endpoint + frontend toggle
8. PR 8: Performance validation + regression tests
```

### File/funzioni principali da creare

| File | Classi/funzioni |
|------|----------------|
| `backend/app/services/portfolio_engine.py` | `PortfolioCalculationEngine`, `ScopeAwareTransactionClassifier`, `DailyStateBuilder`, `DerivedViewsBuilder`, `DailyPortfolioState`, `ClassifiedTransaction`, `InTransitInterval`, `PortfolioCalculationResult` |
| `backend/app/schemas/portfolio.py` | `MissingPriceAsset`, `StalePriceAsset`, `DataQualityReport`, `AllocationHistoryPoint`, `AllocationHistoryQuery`, `AllocationHistoryResponse` (modifica: `PortfolioHistoryPoint`, `PortfolioSummary`) |
| `backend/app/api/v1/portfolio_api.py` | endpoint `POST /portfolio/allocation-history` |
| `backend/test_scripts/test_portfolio_engine/` | `test_scope_classifier.py`, `test_daily_state_builder.py`, `test_derived_views.py`, `test_portfolio_engine_integration.py` |
| `frontend/src/lib/components/dashboard/GrowthChart.svelte` | Rewrite stacked area + overlay |
| `frontend/src/lib/components/dashboard/DataQualityBanner.svelte` | Nuovo componente |
| `frontend/src/lib/components/charts/AllocationStackedChart.svelte` | Nuovo componente |

### File/funzioni da modificare

| File | Modifica |
|------|---------|
| `backend/app/services/portfolio_service.py` | `get_summary()` e `get_history()` diventano adapter |
| `backend/app/schemas/portfolio.py` | Rename `invested_value`, aggiungere nuovi campi, nuovi DTO |
| `frontend/src/routes/(app)/dashboard/+page.svelte` | KPI, banner, allocation toggle |
| `frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts` | Type auto-update dopo api sync |

### Lista test minimi

| Test | Tipo |
|------|------|
| Cash ledger tutti i tipi | Unit |
| Quantity ledger con TRANSFER/ADJUSTMENT | Unit |
| NAV = mv + cash + in_transit | Unit |
| Book = ocb + cash + in_transit_bv | Unit |
| Unrealized = nav - book | Unit |
| Market value con quote_base_quantity (BTP) | Unit |
| WAC forward-fill | Unit |
| Scope classifier internal same day | Unit |
| Scope classifier internal diff dates → in-transit | Unit |
| Scope classifier external outflow | Unit |
| Missing price → NAV incompleto | Unit |
| Missing FX → valore escluso | Unit |
| Stale price detection (>7 days) | Unit |
| share_percentage = 0.5 | Unit |
| Performance: internal transfer non altera ROI | Unit |
| Performance: uses daily NAV (not flat) | Integration |
| Full lifecycle: deposit→buy→dividend→transfer→sell→withdraw | Integration |
| API summary new fields present | API |
| API history market_value rename | API |
| API allocation-history endpoint | API |
| Dashboard loads without crash | E2E |

### Checklist "ready for coding"

- [x] Design v2 letto e compreso
- [x] Code coherence review completata
- [x] Modello dati DB compatibile (no schema changes)
- [x] Funzioni pure riusabili identificate (roi_utils, wac_utils, valuation_utils)
- [x] Breaking changes documentati
- [x] Strategia incrementale PR definita
- [x] Test plan definito
- [x] Rischi mappati con mitigazioni
- [x] Bug esistenti documentati e correzioni pianificate
- [x] Conferma utente sull'ordine dei PR → PR 1 (schema) prima, poi engine
- [x] Conferma utente su threshold stale price → 7 giorni calendario (da design v2)
- [x] Conferma utente su `net_worth` → campo backend calcolato (= nav_value)
- [x] Conferma utente su test E2E → aggiornare rename + correggere matematica

### Domande aperte — RISOLTE

1. **PR 1 (schema rename) prima dell'engine?** → **Sì, prima.** Pulisce il naming immediatamente. Frontend update incluso nel PR 1.
2. **Endpoint debug DailyPortfolioState?** → **No.** Solo endpoint necessari (summary, history, allocation-history).
3. **Allocation history: maximum days?** → **Nessun limite** per ora. Ottimizzare dopo se serve.
4. **`net_worth` nel PortfolioSummary?** → **Sì, campo backend calcolato** (`= nav_value`). Il backend fa i calcoli, il frontend usa il dato.
5. **Test E2E esistenti con `invested_value`?** → **Sì, vanno aggiornati.** Rename `invested_value` → `market_value` in tutti i test E2E e unit test. Anche la matematica dei test va verificata/corretta per allinearsi al nuovo engine.

---

*Fine piano implementativo. Nessun codice modificato.*
