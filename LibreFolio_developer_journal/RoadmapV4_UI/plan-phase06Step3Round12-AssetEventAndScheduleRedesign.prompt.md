# Plan: Phase 6 Step 3 — Round 12: AssetEvent Infrastructure + `scheduled_investment` Redesign

Data: 2026-04-01
Post Round 11 Piano A. Elimina la dipendenza circolare `provider ← transazioni` introducendo la tabella `AssetEvent` come infrastruttura cross-provider, `initial_value` + `currency` nel provider `scheduled_investment`, e estendendo `FAHistoricalData` per restituire anche eventi. Tutti i provider vengono adeguati (ritornano `events=[]` + TODO). Il DB populate, i test e le docs vengono aggiornati.

---

## §0 — Contesto e Problema Architetturale

### Stato attuale (rotto)

Il provider `scheduled_investment` **viola il pattern architetturale** di LibreFolio:

**Flusso corretto** (tutti gli altri provider):
```
configurazione provider / fonte esterna → calcolo prezzi → PriceHistory → portafoglio legge i prezzi
```

**Flusso attuale `scheduled_investment`** (circolare):
```
transazioni → provider legge transazioni → calcola prezzi → prezzi → transazioni
```

Questo crea una **dipendenza circolare** incompatibile con Phase 7 (Transactions).

### Decisioni architetturali confermate

1. **Provider puro e deterministico**: dato `provider_params` (e solo quelli), produce prezzi + eventi. Nessun accesso DB.
2. **`initial_value` obbligatorio**: il capitale iniziale è parte della configurazione dell'asset, non del portafoglio.
3. **`currency` nel provider**: il provider sa la propria valuta dallo schema, non dal DB.
4. **`AssetEvent` come tabella DB**: infrastruttura cross-provider per dividendi, interessi, aggiustamenti prezzo, split.
5. **`FAAssetEventPoint` shape condiviso**: stessi campi tra tabella DB e editor frontend (meno id/timestamps).
6. **Interesse sempre su `initial_value`**: il `compounding` per-periodo gestisce semplice/composto. Nessun flag globale.
7. **`partial_repayment`**: modellato come SELL frazionata sul portafoglio (Phase 7), non come evento provider.
8. **`PRICE_ADJUSTMENT`**: variazione di valore senza cash — vive nel dominio provider/asset, non transazioni.
9. **Nessuna backward compatibility**: pre-alpha, rompi tutto quello che serve.
10. **TODO su tutti i provider**: Yahoo e justETF dovranno in futuro popolare eventi (dividendi).

### Flusso target

```
1. Configurazione: provider_params (initial_value, currency, schedule, asset_events)
2. Provider: genera prezzi + eventi (deterministico)
3. Sync: salva PriceHistory + AssetEvent nel DB
4. Lettura: frontend/portfolio leggono dal DB (prezzi per valutazione, eventi per grafici/dettaglio)
5. Utente: crea BUY/SELL/INTEREST/DIVIDEND (Phase 7)
6. Valutazione: qty × price (unidirezionale)
7. Smart assistant (futuro): confronta eventi asset ↔ transazioni, suggerisce azioni
```

---

## Blocco 1 — DB: Enum `AssetEventType` + Tabella `AssetEvent` + Export

**Scopo**: creare l'infrastruttura persistente per gli eventi asset.

### §1.1 — `AssetEventType` enum

**File**: `backend/app/db/models.py` (~L178, prima di `TransactionType`)

```python
class AssetEventType(str, Enum):
    """
    Types of asset-level events that affect price or generate distributions.

    These events live in the asset domain (not portfolio/transaction domain):
    - DIVIDEND: Cash distribution from equity/ETF (ex-date price drop)
    - INTEREST: Interest payment from debt/loan (ex-date price drop)
    - PRICE_ADJUSTMENT: Non-cash value change (write-down, haircut, re-rating)
    - SPLIT: Stock/unit split (changes quantity, not total value)
    """
    DIVIDEND = "DIVIDEND"
    INTEREST = "INTEREST"
    PRICE_ADJUSTMENT = "PRICE_ADJUSTMENT"
    SPLIT = "SPLIT"
```

### §1.2 — `AssetEvent` model

**File**: `backend/app/db/models.py` (~L698, dopo `PriceHistory`, prima di `FxRate`)

```python
class AssetEvent(SQLModel, table=True):
    """
    Asset-level events that affect pricing or generate distributions.

    Source of truth: provider configuration (provider_params) or external API.
    Persisted in DB by sync layer for efficient querying.

    Events are NOT transactions — they describe what happens to the asset globally,
    not what happens in a user's portfolio. The portfolio reads these events
    for display, smart assistant suggestions, and ex-date price adjustments.

    UniqueConstraint: one event per (asset_id, date, type) for dedup.
    """
    __tablename__ = "asset_events"
    __table_args__ = (
        UniqueConstraint("asset_id", "date", "type", name="uq_asset_event_asset_date_type"),
        Index("idx_asset_event_asset_date", "asset_id", "date"),
        Index("idx_asset_event_asset_type_date", "asset_id", "type", "date"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="assets.id", nullable=False)
    date: date_type = Field(nullable=False)
    type: AssetEventType = Field(nullable=False)
    value: Decimal = Field(sa_column=Column(Numeric(18, 6), nullable=False))
    currency: str = Field(nullable=False)
    source_plugin_key: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @field_validator("currency", mode="before")
    @classmethod
    def validate_currency(cls, v: Any) -> str:
        return _validate_currency_field(v)
```

### §1.3 — Export chain

**File**: `backend/app/db/base.py`
Aggiungere `AssetEvent` e `AssetEventType` a import e `__all__`.

**File**: `backend/app/db/__init__.py`
Aggiungere `AssetEvent` e `AssetEventType` a import e `__all__`.

### §1.4 — Migrazione DB

```bash
./dev.py db create-clean
```

Pre-alpha → ricrea da zero, niente Alembic incrementale.

**Effort**: 25 min

---

## Blocco 2 — Schemas: `FAAssetEventPoint` + Estensioni

**Scopo**: definire il contratto dati per eventi asset e estendere i modelli esistenti.

### §2.1 — `FAAssetEventPoint` schema

**File**: `backend/app/schemas/prices.py` (~L222, dopo `FAHistoricalData`)

```python
class FAAssetEventPoint(BaseModel):
    """
    Single asset event data point — shared shape between DB, provider output, and frontend editor.

    Used in:
    - FAHistoricalData.events (provider output)
    - FAPriceQueryResult.events (API response)
    - FAScheduledInvestmentSchedule.asset_events (provider_params config)
    """
    model_config = ConfigDict(extra="forbid")

    date: date_type = Field(..., description="Event date")
    type: AssetEventType = Field(..., description="Event type")
    value: Decimal = Field(..., description="Event value (amount distributed or price adjustment)")
    currency: Optional[str] = Field(None, description="Currency (if different from asset currency)")
    notes: Optional[str] = Field(None, description="Optional notes")
```

### §2.2 — Estendere `FAHistoricalData`

**File**: `backend/app/schemas/prices.py` L215-222

Aggiungere:
```python
events: List[FAAssetEventPoint] = Field(default_factory=list, description="Asset events in the date range")
```

Questo è il campo di ritorno che **tutti** i provider devono ora restituire (default `[]` = nessun evento).

### §2.3 — Estendere `FAPriceQueryItem`

**File**: `backend/app/schemas/prices.py` L230

Aggiungere:
```python
include_events: bool = Field(False, description="Include asset events in response")
```

### §2.4 — Estendere `FAPriceQueryResult`

**File**: `backend/app/schemas/prices.py` L243

Aggiungere:
```python
events: List[FAAssetEventPoint] = Field(default_factory=list, description="Asset events (if requested)")
```

### §2.5 — Modificare `FAScheduledInvestmentSchedule`

**File**: `backend/app/schemas/assets.py` L264

Aggiungere prima di `schedule`:
```python
initial_value: Decimal = Field(..., description="Initial capital / face value (required, > 0)")
currency: str = Field(..., description="Currency code (ISO 4217)")
asset_events: List[FAAssetEventPoint] = Field(default_factory=list, description="Planned asset events (interest payouts, price adjustments)")
```

Validatori:
- `initial_value > 0`
- `currency` validato con `Currency.validate_code`

**Effort**: 25 min

---

## Blocco 3 — Provider Base + Tutti i Provider: `events` nel Contratto

**Scopo**: adeguare tutti i provider al nuovo contratto `FAHistoricalData` con `events`.

### §3.1 — `supports_events` in `AssetSourceProvider`

**File**: `backend/app/services/asset_source.py` (~L310, dopo `supports_history`)

```python
@property
def supports_events(self) -> bool:
    """Whether this provider can produce asset events (dividends, interest, etc.).
    Default: False. Override to True in providers that generate events."""
    return False
```

### §3.2 — Yahoo Finance

**File**: `backend/app/services/asset_source_providers/yahoo_finance.py`

In `get_history_value`, aggiungere `events=[]` al costruttore `FAHistoricalData`.
Aggiungere commento:
```python
# TODO [AssetEvent]: Fetch dividend events from Yahoo Finance API
# yfinance provides .dividends and .splits on Ticker objects
# Parse and return as FAAssetEventPoint(type=DIVIDEND/SPLIT)
```

### §3.3 — justETF

**File**: `backend/app/services/asset_source_providers/justetf.py`

In `get_history_value`, aggiungere `events=[]` al costruttore `FAHistoricalData`.
Aggiungere commento:
```python
# TODO [AssetEvent]: Scrape distribution events from justETF profile page
# justETF shows dividend dates and amounts on the ETF profile
# Parse and return as FAAssetEventPoint(type=DIVIDEND)
```

### §3.4 — CSS Scraper

**File**: `backend/app/services/asset_source_providers/css_scraper.py`

`get_history_value` raises `NOT_SUPPORTED` → nessuna modifica al return. Aggiungere commento in cima al file:
```python
# NOTE [AssetEvent]: CSS Scraper doesn't support history, so no events either.
# If history support is added in the future, events=[] should be included.
```

### §3.5 — mockprov

**File**: `backend/app/services/asset_source_providers/mockprov.py`

In `get_history_value`, aggiungere `events=[]` al costruttore `FAHistoricalData`.

### §3.6 — TODO_FUTURI.md

**File**: `TODO_FUTURI.md`

Aggiungere nuova sezione:

```markdown
## 📊 AssetEvent: Dividendi/Eventi da Provider Esterni

**Data aggiunta**: 1 Aprile 2026
**Status**: 📋 PIANIFICATO
**Priorità**: Media (post Phase 7)

### Contesto

La tabella `AssetEvent` e il campo `supports_events` nella classe base `AssetSourceProvider`
sono stati introdotti come infrastruttura cross-provider. Attualmente solo `scheduled_investment`
genera eventi. I provider market dovranno essere estesi per catturare:

- **Yahoo Finance**: dividendi e split (disponibili via `yfinance` Ticker.dividends/.splits)
- **justETF**: distribuzioni ETF (disponibili sulla pagina profilo)

### Azione Futura

1. Yahoo Finance: parsare `.dividends` e `.splits` in `get_history_value`, ritornare come `FAAssetEventPoint`
2. justETF: scraping pagina profilo per date e importi distribuzioni
3. Override `supports_events = True` nei provider aggiornati
4. Il sync layer già gestisce l'upsert — basta ritornare gli eventi nel `FAHistoricalData.events`
5. Il frontend (pagina Asset Detail, Phase 8) dovrà mostrare gli eventi sul grafico come marker
```

**Effort**: 20 min

---

## Blocco 4 — Provider `scheduled_investment`: Refactor Completo

**Scopo**: trasformare il provider in un motore deterministico puro. Nessun accesso DB, nessuna dipendenza transazioni.

### §4.1 — Aggiornare `validate_params` (~L639)

Accetta il nuovo schema con `initial_value`, `currency`, `asset_events`.

### §4.2 — Riscrivere `_calculate_value_for_date` (~L524)

Nuova signature: `_calculate_value_for_date(schedule, target_date) → Decimal`
(rimuovere parametro `face_value` — ora è `schedule.initial_value`)

Logica:
1. `face_value = schedule.initial_value`
2. Calcolare interessi maturati usando la logica esistente per-periodo (invariata)
3. Per ogni `event` in `schedule.asset_events` con `event.date <= target_date`:
   - `INTEREST` → sottrae dal prezzo (ex-date drop: l'utente ha incassato, il valore dell'asset scende)
   - `PRICE_ADJUSTMENT` → aggiunge algebraicamente (negativo = write-down, positivo = write-up)
4. `prezzo(d) = face_value + accrued_interest - Σ(INTEREST events) + Σ(PRICE_ADJUSTMENT events)`

**Nota**: l'interesse è **sempre calcolato su `initial_value`**, non sul valore corrente. Il per-periodo `compounding` gestisce già semplice/composto all'interno di ciascun periodo.

### §4.3 — Riscrivere `get_current_value` (~L248-372)

Provider puro:
```python
async def get_current_value(self, identifier, identifier_type, provider_params):
    schedule = self.validate_params(provider_params)
    value = self._calculate_value_for_date(schedule, date.today())
    return FACurrentValue(value=value, currency=schedule.currency, as_of_date=date.today(), source=self.provider_name)
```

**Nessun** accesso DB, nessun `_transaction_override`, nessun `_get_asset_from_db`.

### §4.4 — Riscrivere `get_history_value` (~L379-505)

Provider puro:
```python
async def get_history_value(self, identifier, identifier_type, provider_params, start_date, end_date):
    schedule = self.validate_params(provider_params)
    prices = []
    current = start_date
    while current <= end_date:
        value = self._calculate_value_for_date(schedule, current)
        prices.append(FAPricePoint(date=current, close=value, currency=schedule.currency))
        current += timedelta(days=1)
    # Build events list from schedule.asset_events filtered to range
    events = [
        FAAssetEventPoint(date=e.date, type=e.type, value=e.value, currency=e.currency, notes=e.notes)
        for e in schedule.asset_events
        if start_date <= e.date <= end_date
    ]
    return FAHistoricalData(prices=prices, events=events, currency=schedule.currency, source=self.provider_name)
```

Override `supports_events = True`.

### §4.5 — Eliminare metodi deprecati

Rimuovere completamente:
- `_get_transactions_from_db` (~L177-200)
- `_calculate_face_value_from_transactions` (~L203-246)
- `_get_asset_from_db` (~L151-175)
- Ogni riferimento a `_transaction_override` in `validate_params`, `test_cases`, etc.
- Import di `Transaction`, `AssetProviderAssignment`, `get_session_generator`, `select`, `and_`

### §4.6 — Aggiornare `test_cases` (~L123-144)

```python
@property
def test_cases(self) -> list[dict]:
    return [
        {
            "identifier": "test-scheduled-1",
            "provider_params": FAScheduledInvestmentSchedule(
                initial_value=Decimal("10000"),
                currency="EUR",
                schedule=[
                    FAInterestRatePeriod(
                        start_date=date(2025, 1, 1),
                        end_date=date(2025, 12, 31),
                        annual_rate=Decimal("0.05"),
                        compounding=CompoundingType.SIMPLE,
                        day_count=DayCountConvention.ACT_365,
                    )
                ],
                late_interest=None,
                asset_events=[],
            ).model_dump(mode="json"),
        }
    ]
```

**Effort**: 1h 30min

---

## Blocco 5 — Service Layer: Sync Eventi + Query Bulk

**Scopo**: il sync salva eventi nel DB, la query bulk li restituisce.

### §5.1 — Upsert eventi in `bulk_refresh_prices`

**File**: `backend/app/services/asset_source.py` (~L1523, Phase 3 PERSIST)

Dopo aver salvato i prezzi in `PriceHistory`, se `history_result.events` è non vuota:
- Upsert in `AssetEvent` con logica `INSERT OR REPLACE` (dedup su `asset_id, date, type`)
- Nuovo helper statico: `_upsert_asset_events(session, asset_id, events: list[FAAssetEventPoint], source_plugin_key: str, currency: str)`

### §5.2 — Query eventi in `get_prices_bulk`

**File**: `backend/app/services/asset_source.py` (~L1457)

Se `req.include_events == True`:
- Query aggiuntiva su `AssetEvent` nella stessa finestra temporale
- Popolare `FAPriceQueryResult.events`

Se `False` (default): `events=[]`, nessuna query aggiuntiva. Backward compatible.

**Effort**: 40 min

---

## Blocco 6 — DB Populate + Test Suite Completa

**Scopo**: aggiornare tutti i test e i mock data per il nuovo modello.

### §6.1 — populate_mock_data.py

**File**: `backend/test_scripts/test_db/populate_mock_data.py`

- Import: `AssetEvent`, `AssetEventType`
- `tables_to_clean`: aggiungere `AssetEvent` prima di `PriceHistory` (~L83)
- Creare un asset `scheduled_investment` di test:
  - Display name: "Test Savings Account 5%"
  - `initial_value=10000`, `currency="EUR"`
  - Schedule: 1 periodo 2025-01-01 → 2025-12-31, 5% simple ACT/365
  - `asset_events`: 1 INTEREST da €250 il 2025-07-01
- Popolare qualche `AssetEvent` record per l'asset di test
- Aggiornare conteggio finale (~L1535): aggiungere `"asset_events"`

### §6.2 — db_schema_validate.py

**File**: `backend/test_scripts/test_db/db_schema_validate.py`

Test che la tabella `asset_events` esiste con colonne e vincoli attesi.

### §6.3 — test_asset_schemas.py

**File**: `backend/test_scripts/test_schemas/test_asset_schemas.py`

- Test `FAScheduledInvestmentSchedule` con `initial_value` + `currency` → OK
- Test `FAScheduledInvestmentSchedule` senza `initial_value` → `ValidationError`
- Test `FAScheduledInvestmentSchedule` con `initial_value <= 0` → `ValidationError`
- Test `FAAssetEventPoint` serializzazione/deserializzazione

### §6.4 — test_synthetic_yield.py

**File**: `backend/test_scripts/test_services/test_synthetic_yield.py`

Riscrivere **tutti** i test:
- Niente `_transaction_override`, solo `initial_value` + `schedule`
- Test base: `initial_value=10000`, 5% simple → valore a fine anno ≈ 10500
- Test con `asset_events`: INTEREST €250 il 01/07 → prezzo cala di 250 ex-date
- Test con `PRICE_ADJUSTMENT`: write-down di -1000 → prezzo cala
- Test late interest: invariato nella logica, solo `initial_value` invece di transazioni
- Test compound interest: invariato nella logica

### §6.5 — test_assets_prices.py

**File**: `backend/test_scripts/test_api/test_assets_prices.py`

- Test `POST /assets/prices/query` con `include_events=true` → risposta contiene `events: [...]`
- Test con `include_events=false` (default) → `events: []`
- Test con asset senza eventi → `events: []`

### §6.6 — test_assets_provider.py

**File**: `backend/test_scripts/test_api/test_assets_provider.py`

- Test probe `scheduled_investment` funziona **senza** `_transaction_override`
- Probe riceve solo `provider_params` con `initial_value`, `currency`, `schedule`
- Risultato: current price calcolato, history calcolata, nessun 500

**Effort**: 1h

---

## Blocco 7 — Frontend: Editor Upgrade

**Scopo**: aggiornare il ScheduledInvestmentEditor per il nuovo modello.

### §7.1 — Sezione "Initial Value" + "Currency"

**File**: `frontend/src/lib/components/assets/ScheduledInvestmentEditor.svelte`

Prima della DataTable degli interest periods, aggiungere:
- Campo numerico `initial_value` (label: "💰 Initial Value", i18n)
- `CurrencySearchSelect` per `currency` (label: "💱 Currency", i18n)
- Layout: riga inline con i due campi

Serializzazione: `onchange` emette `{ initial_value, currency, schedule, late_interest, asset_events }`.

### §7.2 — Sezione "Asset Events"

**File**: `frontend/src/lib/components/assets/ScheduledInvestmentEditor.svelte`

Dopo DataTable periodi, prima del toggle Late Interest:
- Mini-tabella editabile (può usare DataTable o layout custom semplice)
- Colonne: Date (SingleDatePicker), Type (select: INTEREST / PRICE_ADJUSTMENT), Value (number), Notes (text, opzionale)
- Bottone "+ Add Event", bottone delete per riga
- Shape identico a `FAAssetEventPoint`

### §7.3 — Abilitare Test Configuration

**File**: `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte` (~L605)

Rimuovere il guard `isAutoGenerated` che nasconde il bottone "Test Configuration". Ora il probe funziona senza transazioni.

### §7.4 — Aggiornare `deserialize()` / `serialize()`

Gestire `initial_value`, `currency`, `asset_events` nella conversione JSON ↔ stato interno dell'editor.

**Effort**: 1h

---

## Blocco 8 — Documentazione

### §8.1 — scheduled-investment.en.md

**File**: `mkdocs_src/docs/user/assets/providers/scheduled-investment.en.md`

- "🧮 How Value is Calculated": riscritta con `initial_value` + interessi, senza transazioni
- Nuova sezione "📋 Asset Events": spiega INTEREST e PRICE_ADJUSTMENT
- Rimosso "BUY transactions to determine the principal"
- Aggiornato "🔧 Configuration": menziona `initial_value`, `currency`, `asset_events`

### §8.2 — TODO_FUTURI.md

Già coperto in §3.6.

**Effort**: 15 min

---

## Ordine di Esecuzione

| # | Blocco | Step | Descrizione | Effort |
|---|--------|------|-------------|--------|
| 1 | DB | §1.1-§1.4 | Enum + Tabella + Export + Ricreazione | 25 min |
| 2 | Schema | §2.1-§2.5 | `FAAssetEventPoint`, estensione `FAHistoricalData`, `FAScheduledInvestmentSchedule` | 25 min |
| 3 | Provider base | §3.1-§3.6 | `supports_events` + `events=[]` su tutti i provider + TODO | 20 min |
| 4 | Provider scheduled | §4.1-§4.6 | Refactor completo: puro, deterministico, senza DB | 1h 30min |
| 5 | Service | §5.1-§5.2 | Sync eventi + query bulk | 40 min |
| 6 | Test + Populate | §6.1-§6.6 | populate mock, schema test, service test, API test | 1h |
| 7 | Frontend | §7.1-§7.4 | Editor: initial value + currency + events + test button | 1h |
| 8 | Docs | §8.1-§8.2 | MkDocs + TODO_FUTURI | 15 min |
| **Totale** | | | | **~6h** |

---

## Validation Checklist (Round 12)

### DB & Schema
- [x] Tabella `asset_events` esiste con colonne e vincoli corretti
- [x] `./dev.py db create-clean` completa senza errori
- [x] `FAScheduledInvestmentSchedule` richiede `initial_value` e `currency`
- [x] `FAScheduledInvestmentSchedule` senza `initial_value` → `ValidationError`
- [x] `FAAssetEventPoint` serializza/deserializza correttamente
- [x] `FAHistoricalData` ha campo `events` (default `[]`)

### Provider scheduled_investment
- [x] `get_current_value` funziona senza accesso DB (provider puro)
- [x] `get_history_value` funziona senza accesso DB (provider puro)
- [x] Nessun import di `Transaction`, `get_session_generator`, `_transaction_override`
- [x] `_calculate_value_for_date`: interesse calcolato su `initial_value`
- [x] `_calculate_value_for_date`: INTEREST event riduce il prezzo
- [x] `_calculate_value_for_date`: PRICE_ADJUSTMENT event modifica il prezzo
- [x] `test_cases` usa solo `provider_params` con `initial_value`

### Altri provider
- [x] Yahoo Finance: `get_history_value` ritorna `events=[]`
- [x] justETF: `get_history_value` ritorna `events=[]`
- [x] mockprov: `get_history_value` ritorna `events=[]`
- [x] TODO comments presenti in ogni provider file

### Service Layer
- [x] `bulk_refresh_prices` salva eventi in `AssetEvent` quando presenti
- [x] `get_prices_bulk` con `include_events=true` → ritorna eventi dal DB
- [x] `get_prices_bulk` con `include_events=false` → `events=[]` (no query)

### API
- [ ] `POST /assets/prices/query` con `include_events=true` → risposta con eventi
- [ ] `POST /assets/provider/probe` per `scheduled_investment` → funziona senza hack
- [ ] Probe ritorna current price + history calcolati da `initial_value`

### Test Suite
- [x] `./dev.py test db populate` completa con `AssetEvent` mock data
- [x] `./dev.py test db validate` passa con nuova tabella
- [x] `./dev.py test schemas all` passa (nuovo schema validato)
- [x] `./dev.py test services synthetic-yield` passa (nessun `_transaction_override`)
- [ ] `./dev.py test api prices` passa (include_events testato)
- [ ] `./dev.py test api provider` passa (probe scheduled_investment)

### Frontend
- [x] ScheduledInvestmentEditor mostra campo Initial Value + Currency
- [x] ScheduledInvestmentEditor mostra sezione Asset Events
- [x] Asset Events: add/delete row funziona
- [x] Serializzazione JSON include `initial_value`, `currency`, `asset_events`
- [x] Bottone "Test Configuration" visibile per `scheduled_investment`
- [ ] Test Configuration funziona: risultati Current Price e History

### Documentazione
- [x] `scheduled-investment.en.md` aggiornato (no transazioni, sì initial_value)
- [x] `TODO_FUTURI.md` ha sezione AssetEvent per provider esterni
- [x] Developer docs: `system_providers.md` aggiornato (pure engine, no transactions)
- [x] Developer docs: `architecture.md` aggiornato (AssetEvent table + event sync)
- [x] Developer docs: `providers_list.md` aggiornato (Events feature)
- [x] i18n: chiavi per Initial Value, Currency, Asset Events, event types

### Miglioramenti aggiuntivi (post-review)
- [x] `FAAssetEventPoint.value` usa `Currency` class (code + amount) invece di value + currency separati
- [x] `FAPriceQueryItem` ha sia `include_price` (default True) che `include_events` (default False)
- [x] `get_history_value` ottimizzato: accumulazione incrementale (non ricalcola da zero per ogni giorno)
- [x] `_find_active_period` helper per lookup O(1) del periodo attivo
- [x] Frontend: i18n per tutte le stringhe hardcoded (labels, column headers, empty states)
- [x] Frontend: event type labels usano chiavi i18n con enum come key

### Round 12.1 — Semplificazione & Cache (2026-04-02)

#### Schema
- [x] `initial_value` + `currency` unificati in `Currency` object (`{code, amount}`) in `FAScheduledInvestmentSchedule`
- [x] Rimosso `CompoundingType` (SIMPLE/COMPOUND) — interesse sempre semplice su initial_value
- [x] Rimosso `CompoundFrequency` → sostituito con `MaturationFrequency` (DAILY, WEEKLY, MONTHLY, QUARTERLY, SEMIANNUAL, ANNUAL)
- [x] Rimosso `CONTINUOUS` da frequenze (non serve per interesse semplice)
- [x] `FAInterestRatePeriod`: campo `compounding` + `compound_frequency` → `maturation_frequency: MaturationFrequency`
- [x] `FALateInterestConfig`: stessa semplificazione

#### Motore di Calcolo
- [x] Rimossa `_calculate_value_for_date` (calcolo per-giorno)
- [x] Creata `_generate_schedule_values()` — genera TUTTI i valori per l'intero schedule range
- [x] Cache con `get_ttl_cache('scheduled_investment', maxsize=256, ttl=172800)` (48h TTL)
- [x] Hash MD5 dei params canonici come chiave cache
- [x] `get_current_value` e `get_history_value` usano la funzione cached
- [x] Late interest calcolato on-demand da ultimo valore cached + grace period
- [x] `test_cases` usa `model_dump()` invece di `model_dump(mode="json")`

#### Pulizia
- [x] Rimossa proprietà `supports_events` da base class e tutti i provider
- [x] Rimossa `validate_compound_frequency` import da assets.py
- [x] `financial_math.py`: aggiornato per usare `MaturationFrequency`, rimosso CONTINUOUS

#### Bug Fix
- [x] Fix `ProviderInputType` mapping in `bulk_assign_providers` — mappa `IdentifierType.OTHER` → `ProviderInputType.URL`

#### Test (tutti passati)
- [x] `test_synthetic_yield.py` — 8/8 passed (riscritto per nuovo modello)
- [x] `test_synthetic_yield_integration.py` — 3/3 passed (riscritto)
- [x] `test_asset_schemas.py` — 60/60 passed (aggiornato per Currency, MaturationFrequency)
- [x] `test_utilities/` — 140/140 passed (compound interest, financial math aggiornati)
- [x] `test_services/` — 139/139 passed (rimosso test_find_active_period)

#### Frontend
- [x] `ScheduledInvestmentEditor.svelte`: Currency per initial_value, rimosso compounding/compound_frequency
- [x] Nuova colonna "Maturation Frequency" al posto di "Compounding" + "Comp. Freq."
- [x] `serialize()`: emette `initial_value: {code, amount}` invece di campi separati
- [x] Deserializzazione compatibile con nuovo formato Currency
- [x] `svelte-check`: 0 errors, 0 warnings
- [x] `npm run build`: ✔ done

#### TODO rimanenti
- [ ] `POST /assets/prices/query` con `include_events=true` → risposta con eventi
- [ ] `POST /assets/provider/probe` per `scheduled_investment` → funziona senza hack
- [ ] Probe ritorna current price + history calcolati da `initial_value`
- [ ] `./dev.py test api prices` passa (include_events testato)
- [ ] `./dev.py test api provider` passa (probe scheduled_investment + CSS scraper fix)
- [ ] Fix `metadata_updated` field on `FAProviderAssignmentResult` (warning in CSS scraper test)
- [ ] Test Configuration frontend: risultati Current Price e History
- [ ] `./dev.py api sync` → aggiornare tipi TypeScript generati con nuovi enum

---


Riepilogo Analisi
✅ Conferma: financial_math.py è usata solo da scheduled_investment.py
In codice di produzione, tutte le funzioni esportate (calculate_day_count_fraction, calculate_simple_interest) sono importate esclusivamente da scheduled_investment.py. L'altra import in test_asset_source.py è solo per i test.
❌ find_active_period — Dead Code
Non è importata da nessun codice di produzione. Era parte della vecchia architettura per-data. Il motore attuale (_generate_schedule_values) itera sullo schedule con indice diretto. I 13 test in test_financial_math.py testano una funzione orfana → da rimuovere.
🔍 Compound Interest — Come Funziona
Scenario
Meccanismo
COMPOUND nello schedule
Loop giornaliero: base = principal + total_interest, poi total_interest += base * rate * Δt. Equiv. a P*(1+r/365)^N
SIMPLE nello schedule
Loop giornaliero: total_interest += principal * rate * Δt. Base sempre il capitale iniziale.
COMPOUND nel late
Stesso loop day-by-day, rate cambia a grace_end (da scheduled rate → late rate)
SIMPLE nel late
Calcolo diretto P * r * Δt senza loop. Base = initial_value.amount, non last_scheduled_value
💡 Proposte di Refactoring
find_active_period → rimuovere (dead code)
_calculate_act_365 + _calculate_act_360 → fattorizzare in _calculate_act_fixed(start, end, denominator)
calculate_simple_interest → mantenere (self-documenting), ma consapevoli che è a*b*c


### 📋 Checklist Frontend — ScheduledInvestmentEditor (da Round 12)

Le modifiche backend al motore `scheduled_investment` e agli schemi impattano il frontend.
Verificare **manualmente** in browser tutti i seguenti scenari:

#### Serializzazione / Deserializzazione
- [ ] **Caricamento editor**: un asset esistente con schedule + late_interest si carica correttamente
non abbiamo ancora la edit page, siamo ancora in solo creazione
- [ ] **`initial_value` Currency**: il campo mostra amount + currency code (non il vecchio formato flat)
Si, ma il campo del currencySelector è pù alto degli altri, si reisce a farlo alto tanto quanto gli altri?

- [x] **`interest_type` globale**: il select mostra SIMPLE/COMPOUND e il valore è persistito nel JSON
- [x] **`day_count` globale**: il select mostra tutte le 4 opzioni (ACT/365, ACT/360, ACT/ACT, 30/360)
Sarebbe molto utile se nel titolo avesse anche lui, come per le colonne della tabella una i con un tooltip custom che spieghi che si applica a tutta la schedulazione e che se cliccato riporta alla pagina di documentazione: http://localhost:8001/mkdocs/it/financial-theory/day-count/
- [x] **`maturation_frequency`**: la colonna nella tabella mostra tutte le 6 opzioni
si e sono pure tradotte, ma le opzini sono solo testuali, delle icone aiuterebbero, in oltre ora è la colonna del tasso di interesse ad avere la dimensione troppo grande, ti direi di lasciare la colonna azione e selezione di questa grandezza e fare le altre 3 equi distribuite.
- [x] **Late interest row**: toggle on/off funziona, `interest_type` per late è indipendente dal globale
- [-] **Salvataggio**: `serialize()` produce JSON corretto con `initial_value: {code, amount}` formato Currency
Appena salvato il frontend ha mandato solo questo  pacchetto:
Request URL
http://localhost:8001/api/v1/assets
Request Method
POST
[{"display_name":"asdasd","currency":"USD","asset_type":"STOCK"}]

e la modale si è chiusa 


Piccola nota, il pulsante di testa configurazione c'è ma è read only, non capisco se manca qualcosa da impostare da me, o un problema sw
In oltre al salva, quando l'asset si crea, io farei subito un sinc non solo nel range date configurato nella pagina (come avviene con gli altri) bensì essendo sintetico e locale, lo farei su tutte le date del periodo impostato, o almeno dall'inizio ad oggi, aggiungiamo nel piano principale (plan-phase06Asset) nello step in cui andiamo a fare la pagina di dettaglio, che se il frontend rileva delle riconfigurazioni del provider di un asset con shcedule_investment, allora fa preventivamente delete di tutti i prezzi ed eventi precedentemente salvati, così da garantire un DB allineato alle configurazioni.
#### Asset Events
- [x] **Aggiunta evento**: nuovo INTEREST o PRICE_ADJUSTMENT con amount + currency
- [-] **Modifica evento**: date, tipo, valore, note editabili inline
c'è tutto ma con componenti standard os, dovevi usare singleDatePick e simpleSelect
- [x] **Rimozione evento**: elimina e riserializza correttamente
Si ma manca la selezione e l'azione bulk, che come toolbar dovrebbe comparire accanto ad aggiungi evento e chiedere la conferma elencando gli eventi che verranno eliminati
In oltre l'aggiungi evento di questa sezione ha la label che non scompare quando si va in modalità mobile
- [?] **Currency evento**: se non impostata, eredita dalla currency globale dell'editor
non ho capito il test, cosa è, dove lo vedo e a cosa serve

#### CRUD Periodi
- [x] **Add periodo**: aggiunge contiguamente dopo l'ultimo
- [x] **Delete periodo**: gestisce boundary date con modale
- [x] **Split periodo**: divide a metà con boundary modale
- [x] **Merge periodi**: selezionando 2+ periodi contigui, il merge funziona
- [x] **Bulk delete**: selezionando periodi non contigui, gaps risolti correttamente
- [x] **Range change**: propagazione contiguità (backward/forward) senza gap/overlap

#### Probe / Test Configuration (da verificare dopo API completata)
- [ ] **Probe `scheduled_investment`**: con `initial_value` Currency produce current_price + history
- [ ] **Chart preview**: grafico mostra valori crescenti (interesse) con eventuale drop per eventi
- [ ] **Late interest nel chart**: post-maturity il grafico continua a salire
come detto sopra, il test è readonly

#### Edge Cases
- [x] **Schedule vuoto**: stato empty corretto, nessun crash
- [ ] **Un solo periodo**: CRUD funziona senza errori
senza test-connection non lo so
- [ ] **Tasso 0%**: valore resta costante (= initial_value)
senza test-connection non lo so
- [ ] **COMPOUND vs SIMPLE**: switch globale cambia il JSON, ma UI non cambia (è calcolo backend)
senza test-connection non lo so
- [!] **Retrocompatibilità**: vecchi JSON con `initial_value` flat number vengono deserializzati
Non serve, sto in ambiente di test e ho resettato il DB, e se il codice attuale gestisce la retro compatibilità. rimuovila.

