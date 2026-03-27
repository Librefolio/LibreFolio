# Plan: Phase 6 Step 3 — AssetModal + AssetSearchAutocomplete (v3)

**Data creazione**: 27 Marzo 2026
**Ultimo aggiornamento**: 27 Marzo 2026
**Status**: 📋 PIANIFICATO
**Durata stimata**: ~2.5 giorni
**Dipendenze**: Phase 6 Step 1 (params_schema ✅), Step 2/2b/2c (asset list dual view ✅)

---

## 1. Obiettivo

Implementare `AssetModal.svelte` e `AssetSearchAutocomplete.svelte` con:
- Endpoint bulk `POST /assets/provider/probe` (current_price, history, metadata — selezionabili)
- Arricchimento identifier da yfinance (`fetch_asset_metadata` potenziato)
- Auto-test-connection dopo selezione search result
- Pulsante "Ask Provider" sugli identifiers
- Campo `user_url` persistito + `provider_url` calcolato dal backend
- Confirmation modals (save without test, change identifier in edit)
- E3: Toggle Abs/% per AssetCard

**Escluso**: detail page (Step 4), matching wizard (Step 5), E2E test (Step 6).

---

## 2. Contesto — Stato Attuale

### Backend — già implementato

| Feature | Stato |
|---------|-------|
| `FAProviderParamField` + `FAProviderInfo.params_schema` | ✅ Step 1 |
| `params_schema` override in cssscraper + scheduled_investment | ✅ Step 1 |
| `supports_search` fix (no HTTP call, check locale) | ✅ Step 1 |
| Pre-warm provider caches | ✅ Step 1 |
| CRUD assets (POST/PATCH/GET/DELETE) | ✅ |
| Provider assignment (POST/DELETE/GET assignments) | ✅ |
| Provider search (`GET /assets/provider/search`) | ✅ |
| Bulk price query (`POST /assets/prices/query`) | ✅ Step 2b |

### Backend — da implementare (questo step)

| Feature | Stato |
|---------|-------|
| `user_url` su `AssetProviderAssignment` | ❌ Campo non esiste |
| `provider_url` calcolato dal backend (metodo `get_asset_url` nei provider) | ❌ Metodo non esiste |
| `POST /assets/provider/probe` (dry-run bulk modulare) | ❌ Endpoint non esiste |
| `fetch_asset_metadata` potenziato con identifiers (yfinance, justetf) | ❌ Non estrae identifiers |

### Frontend — già implementato

| Componente | Stato |
|-----------|-------|
| `AssetCard.svelte` | ✅ Step 2 |
| `AssetTable.svelte` | ✅ Step 2 |
| `AssetIcon.svelte` | ✅ Step 2 |
| `AssetSyncModal.svelte` | ✅ Step 2c |
| `ViewModeToggle.svelte` | ✅ Step 2 |
| `assets/+page.svelte` (953 righe, dual view) | ✅ Step 2 |

### Frontend — da implementare (questo step)

| Componente | Stato |
|-----------|-------|
| `AssetSearchAutocomplete.svelte` | ❌ |
| `ProviderAssignmentSection.svelte` | ❌ |
| `AssetModal.svelte` | ❌ |
| Integrazione modale nella pagina lista | ❌ |

### Schema inheritance — principio guida

Creare uno schema base `FAProviderConfigBase` con il set minimo di campi provider (usato dal probe
endpoint). `FAProviderAssignmentItem` estende il base aggiungendo solo `asset_id`, `fetch_interval`,
`user_url`. Le funzioni del service layer accettano il tipo base — oggetti figli passano direttamente
senza travasi.

```
FAProviderConfigBase          ← provider_code, identifier, identifier_type, provider_params (+ validatore)
  ├─ FAProviderProbeRequest   ← + operations: List[ProbeOperation]
  └─ FAProviderAssignmentItem ← + asset_id, fetch_interval, user_url
```

### Identifiers — come si ottengono

- La search restituisce **un solo** `identifier` + `identifier_type` per risultato (es. `AAPL`/`TICKER`
  da yfinance, o `IE00B4L5Y983`/`ISIN` da justetf).
- Al create, il frontend mappa quel valore su `identifier_{type.lower()}` di `FAAssetCreateItem`.
- Gli altri campi identifier rimangono vuoti.
- `fetch_asset_metadata()` attualmente **NON** popola gli identifier — restituisce solo `asset_type`,
  `currency`, `classification_params` (sector, description).
- **In questo step** potenziamo `fetch_asset_metadata` di yfinance per estrarre anche `identifier_ticker`
  (da `info['symbol']`) e `identifier_isin` (da `ticker.isin`).
- L'utente può poi usare il pulsante "Ask Provider" nella modale per popolare i campi vuoti.

### DB — nessuna migrazione Alembic

Modifica diretta di `001_initial.py` + `./dev.py db create-clean`. Nessuna backward compatibility.
`populate_mock_data.py` aggiornato per la nuova struttura.

---

## 3. Step di Implementazione

### 3.1 — Backend: Schema inheritance + `user_url` (~0.25 giorni)

#### 3.1a) `FAProviderConfigBase` — nuovo schema base

**File**: `backend/app/schemas/provider.py`

Creare `FAProviderConfigBase` con i campi minimi del provider:

```python
class FAProviderConfigBase(BaseModel):
    """Base provider configuration — minimal set for probe/test operations.

    Contains only the fields needed to identify and configure a provider,
    without persistence-related fields (asset_id, fetch_interval, etc.).

    Used as input for probe/test-config endpoint.
    Child classes extend this for assignment (FAProviderAssignmentItem)
    and probe requests (FAProviderProbeRequest).
    """

    model_config = ConfigDict(extra="forbid")

    provider_code: str = Field(
        ..., description="Provider code (yfinance, cssscraper, scheduled_investment, etc.)"
    )
    identifier: str = Field(
        ..., description="Asset identifier for this provider (ticker, ISIN, UUID, URL, etc.)"
    )
    identifier_type: IdentifierType = Field(
        ..., description="Type of identifier (TICKER, ISIN, UUID, OTHER, etc.)"
    )
    provider_params: Optional[dict[str, Any]] = Field(
        None, description="Provider-specific configuration (JSON)"
    )

    @model_validator(mode="after")
    def validate_provider_params_with_plugin(self):
        """Validate provider_params using the plugin's validate_params method."""
        from backend.app.services.provider_registry import AssetProviderRegistry
        from backend.app.services.asset_source import AssetSourceError

        provider = AssetProviderRegistry.get_provider_instance(self.provider_code)
        if not provider:
            raise ValueError(f"Unknown provider code: {self.provider_code}")

        try:
            provider.validate_params(self.provider_params)
        except AssetSourceError as e:
            raise ValueError(f"Invalid provider_params for {self.provider_code}: {e.message}")
        except Exception as e:
            raise ValueError(f"Provider validation error for {self.provider_code}: {str(e)}")

        return self
```

#### 3.1b) Evolvere `FAProviderAssignmentItem`

**File**: `backend/app/schemas/provider.py`

Evolvere per estendere `FAProviderConfigBase`:

```python
class FAProviderAssignmentItem(FAProviderConfigBase):
    """FA provider assignment — extends config base with persistence fields."""

    asset_id: int = Field(..., description="Asset ID")
    fetch_interval: int = Field(
        1440, description="Refresh frequency in minutes (default: 1440 = 24h)"
    )
    user_url: Optional[str] = Field(
        None, description="User-defined URL for this asset (notes, external dashboard, etc.)"
    )

    @field_validator("fetch_interval", mode="before")
    @classmethod
    def set_default_fetch_interval(cls, v):
        if v is None or v == "":
            return 1440
        return v
```

Il validatore `validate_provider_params_with_plugin` è ereditato dal base — rimuoverlo dalla classe
figlia.

#### 3.1c) Evolvere `FAProviderAssignmentReadItem`

**File**: `backend/app/schemas/provider.py`

Aggiungere `user_url` e `provider_url`:

```python
class FAProviderAssignmentReadItem(BaseModel):
    # ...existing fields...
    user_url: Optional[str] = Field(None, description="User-defined URL")
    provider_url: Optional[str] = Field(None, description="Auto-generated URL to provider page")
```

#### 3.1d) DB model + migration

**File**: `backend/app/db/models.py`

```python
class AssetProviderAssignment(SQLModel, table=True):
    # ...existing fields...
    user_url: Optional[str] = Field(
        default=None, description="User-defined URL (notes, external dashboard, etc.)"
    )
```

**File**: `backend/alembic/versions/001_initial.py`

Aggiungere nella tabella `asset_provider_assignments`:
```sql
user_url              VARCHAR     DEFAULT NULL,
```

#### 3.1e) Service layer: propagare `user_url` e `provider_url`

**File**: `backend/app/services/asset_source.py`

- In `bulk_assign_providers()`: copiare `user_url` da `FAProviderAssignmentItem` al modello DB.
- In `get_provider_assignments_bulk()` (o dove si costruisce `FAProviderAssignmentReadItem`):
  popolare `provider_url` chiamando `get_asset_url()` (vedi 3.2).

**File**: `backend/app/api/v1/assets.py`

- In `get_provider_assignments()`: popolare `provider_url` nel response.

#### 3.1f) Populate mock data

**File**: `backend/test_scripts/test_db/populate_mock_data.py`

Aggiornare `populate_asset_provider_assignments` con `user_url` di esempio:
```python
("Apple Inc.", "yfinance", "AAPL", IdentifierType.TICKER, None, "https://investor.apple.com"),
("Microsoft Corporation", "yfinance", "MSFT", IdentifierType.TICKER, None, "https://www.microsoft.com/en-us/investor"),
# ...rest without user_url (None)
```

#### Tasks 3.1

- [ ] Creare `FAProviderConfigBase` in `provider.py` con validatore spostato
- [ ] Evolvere `FAProviderAssignmentItem` per estendere `FAProviderConfigBase` (+ `user_url`)
- [ ] Evolvere `FAProviderAssignmentReadItem` con `user_url` + `provider_url`
- [ ] Aggiungere `user_url` a `AssetProviderAssignment` model
- [ ] Aggiornare `001_initial.py` (colonna `user_url`)
- [ ] Propagare `user_url` nel service layer (assign + read)
- [ ] Aggiornare `populate_mock_data.py`
- [ ] `./dev.py db create-clean`

---

### 3.2 — Backend: `get_asset_url()` nei provider + `provider_url` nei risultati (~0.15 giorni)

#### 3.2a) Metodo base

**File**: `backend/app/services/asset_source.py`

```python
class AssetSourceProvider(ABC):
    # ...existing code...

    def get_asset_url(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: dict | None = None,
    ) -> str | None:
        """
        Generate URL to the provider's page for this specific asset.

        Used by the frontend to show a "Go to Provider Page" link.
        Override in subclasses that have public web pages.

        Args:
            identifier: Asset identifier
            identifier_type: Type of identifier
            provider_params: Provider-specific params

        Returns:
            URL string or None if provider has no web page for assets
        """
        return None
```

#### 3.2b) Override nei provider

**File**: `backend/app/services/asset_source_providers/yahoo_finance.py`

```python
def get_asset_url(self, identifier, identifier_type, provider_params=None) -> str | None:
    return f"https://finance.yahoo.com/quote/{identifier}"
```

**File**: `backend/app/services/asset_source_providers/justetf.py`

```python
def get_asset_url(self, identifier, identifier_type, provider_params=None) -> str | None:
    return f"https://www.justetf.com/en/etf-profile.html?isin={identifier}"
```

**File**: `backend/app/services/asset_source_providers/css_scraper.py`

```python
def get_asset_url(self, identifier, identifier_type, provider_params=None) -> str | None:
    # The identifier IS the URL for CSS scraper
    return identifier if identifier.startswith("http") else None
```

#### 3.2c) `provider_url` in `FAProviderSearchResultItem`

**File**: `backend/app/schemas/provider.py`

```python
class FAProviderSearchResultItem(BaseModel):
    # ...existing fields...
    provider_url: Optional[str] = Field(None, description="URL to asset page on provider site")
```

**File**: `backend/app/services/asset_source.py` (in `AssetSearchService.search()`)

Dopo aver costruito i risultati, popolare `provider_url`:
```python
provider = AssetProviderRegistry.get_provider_instance(code)
provider_url = provider.get_asset_url(item["identifier"], item["identifier_type"]) if provider else None

results.append(FAProviderSearchResultItem(
    # ...existing fields...
    provider_url=provider_url,
))
```

#### 3.2d) `provider_url` in `FAProviderAssignmentReadItem`

Nel service layer dove si costruisce la risposta per `GET /assets/provider/assignments`, popolare
`provider_url` chiamando `get_asset_url()` per ogni assignment.

#### Tasks 3.2

- [ ] Aggiungere `get_asset_url()` alla base `AssetSourceProvider` (default None)
- [ ] Override in `yahoo_finance.py`
- [ ] Override in `justetf.py`
- [ ] Override in `css_scraper.py`
- [ ] Aggiungere `provider_url` a `FAProviderSearchResultItem`
- [ ] Popolare `provider_url` in `AssetSearchService.search()`
- [ ] Popolare `provider_url` in `get_provider_assignments` response

---

### 3.3 — Backend: Arricchimento `fetch_asset_metadata` con identifiers (~0.15 giorni)

#### 3.3a) YahooFinance — estrarre identifier_ticker + identifier_isin

**File**: `backend/app/services/asset_source_providers/yahoo_finance.py`

Potenziare `fetch_asset_metadata` per estrarre identifiers:

```python
async def fetch_asset_metadata(self, identifier, identifier_type, provider_params=None):
    # ...existing code to get ticker.info...

    # Extract identifiers
    symbol = info.get("symbol")
    identifier_ticker = symbol if symbol else None

    # Try to get ISIN (yfinance property — may not be available for all markets)
    identifier_isin = None
    try:
        isin_val = ticker.isin
        if isin_val and isin_val != "-" and len(isin_val) == 12:
            identifier_isin = isin_val
    except Exception:
        pass  # ISIN not available for this asset

    # Build FAAssetPatchItem with identifiers
    patch_item = FAAssetPatchItem(
        asset_id=0,
        asset_type=asset_type,
        currency=currency,
        classification_params=classification,
        identifier_ticker=identifier_ticker,
        identifier_isin=identifier_isin,
    )
    return patch_item
```

#### 3.3b) JustETF — best-effort identifier extraction

**File**: `backend/app/services/asset_source_providers/justetf.py`

Aggiungere `fetch_asset_metadata` se non esiste (o potenziare):

```python
async def fetch_asset_metadata(self, identifier, identifier_type, provider_params=None):
    """Best-effort metadata extraction from JustETF cached data."""
    self._check_availability()
    try:
        df = await asyncio.to_thread(JustETFProvider.etf_list)
        if identifier in df.index:
            row = df.loc[identifier]
            ticker_val = row.get("ticker") if "ticker" in df.columns else None

            patch_item = FAAssetPatchItem(
                asset_id=0,
                asset_type="ETF",
                identifier_isin=identifier,  # ISIN is the search key
                identifier_ticker=ticker_val if ticker_val else None,
            )
            return patch_item
    except Exception as e:
        logger.warning(f"JustETF metadata fetch failed for {identifier}: {e}")
    return None
```

#### Tasks 3.3

- [ ] Potenziare `fetch_asset_metadata` in `yahoo_finance.py` con `identifier_ticker` + `identifier_isin`
- [ ] Creare/potenziare `fetch_asset_metadata` in `justetf.py` con `identifier_isin` + `identifier_ticker` (best-effort)
- [ ] Verificare che `FAAssetPatchItem` ha già tutti i campi `identifier_*` (✅ confermato)

---

### 3.4 — Backend: `POST /assets/provider/probe` (endpoint bulk modulare) (~0.25 giorni)

#### 3.4a) Schema enum + request

**File**: `backend/app/schemas/provider.py`

```python
class ProbeOperation(str, Enum):
    """Operations available for provider probe endpoint."""
    CURRENT_PRICE = "current_price"
    HISTORY = "history"
    METADATA = "metadata"


class FAProviderProbeRequest(FAProviderConfigBase):
    """Probe request — extends config base with operation selection.

    Inherits provider_code, identifier, identifier_type, provider_params
    from FAProviderConfigBase. Adds operations list to select which
    probe operations to execute.
    """
    operations: List[ProbeOperation] = Field(
        ..., min_length=1,
        description="Operations to execute: current_price, history, metadata"
    )
```

#### 3.4b) Schema response

**File**: `backend/app/schemas/provider.py`

```python
class ProbeCurrentPriceResult(BaseModel):
    """Result of current_price probe operation."""
    model_config = ConfigDict(extra="forbid")

    success: bool = Field(..., description="Whether the operation succeeded")
    value: Optional[Decimal] = Field(None, description="Current price value")
    currency: Optional[str] = Field(None, description="Price currency")
    as_of_date: Optional[str] = Field(None, description="Date of the price (ISO format)")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time_ms: int = Field(..., description="Backend execution time in milliseconds")


class ProbeHistoryResult(BaseModel):
    """Result of history probe operation."""
    model_config = ConfigDict(extra="forbid")

    success: bool = Field(...)
    points_count: Optional[int] = Field(None, description="Number of price points found")
    date_range: Optional[str] = Field(None, description="Date range of found data (start → end)")
    error: Optional[str] = Field(None)
    execution_time_ms: int = Field(...)


class ProbeMetadataResult(BaseModel):
    """Result of metadata probe operation."""
    model_config = ConfigDict(extra="forbid")

    success: bool = Field(...)
    patch_data: Optional[FAAssetPatchItem] = Field(
        None, description="Asset metadata patch (identifiers, asset_type, classification, etc.)"
    )
    error: Optional[str] = Field(None)
    execution_time_ms: int = Field(...)


class FAProviderProbeResponse(BaseModel):
    """Response for provider probe endpoint.

    Contains results for each requested operation, with per-operation
    execution time and a total execution time.
    """
    model_config = ConfigDict(extra="forbid")

    provider_code: str = Field(...)
    identifier: str = Field(...)
    total_execution_time_ms: int = Field(..., description="Total backend execution time")
    provider_url: Optional[str] = Field(None, description="URL to asset page on provider site")

    current_price: Optional[ProbeCurrentPriceResult] = Field(
        None, description="Present only if current_price was requested"
    )
    history: Optional[ProbeHistoryResult] = Field(
        None, description="Present only if history was requested"
    )
    metadata: Optional[ProbeMetadataResult] = Field(
        None, description="Present only if metadata was requested"
    )
```

#### 3.4c) Service function

**File**: `backend/app/services/asset_source.py`

```python
class AssetSourceManager:
    # ...existing code...

    @staticmethod
    async def probe_provider_config(
        config: FAProviderConfigBase,
        operations: list[ProbeOperation],
    ) -> FAProviderProbeResponse:
        """
        Probe a provider configuration without persisting anything.

        Executes requested operations (current_price, history, metadata)
        and returns results with per-operation execution time.

        Accepts FAProviderConfigBase — child objects (FAProviderAssignmentItem,
        FAProviderProbeRequest) pass directly without field copying.
        """
        provider = AssetProviderRegistry.get_provider_instance(config.provider_code)
        if not provider:
            raise AssetSourceError(f"Unknown provider: {config.provider_code}", "UNKNOWN_PROVIDER")

        params = AssetSourceManager._parse_provider_params(config.provider_params)
        total_start = time.monotonic_ns()

        # Provider URL (always computed)
        provider_url = provider.get_asset_url(
            config.identifier, config.identifier_type, params
        )

        current_price_result = None
        history_result = None
        metadata_result = None

        # --- current_price ---
        if ProbeOperation.CURRENT_PRICE in operations:
            op_start = time.monotonic_ns()
            try:
                value = await asyncio.wait_for(
                    provider.get_current_value(
                        config.identifier, config.identifier_type, params
                    ),
                    timeout=15.0,
                )
                current_price_result = ProbeCurrentPriceResult(
                    success=True,
                    value=value.value,
                    currency=value.currency,
                    as_of_date=str(value.as_of_date),
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )
            except Exception as e:
                current_price_result = ProbeCurrentPriceResult(
                    success=False,
                    error=str(e),
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )

        # --- history ---
        if ProbeOperation.HISTORY in operations:
            op_start = time.monotonic_ns()
            try:
                end_date = date.today()
                start_date = end_date - timedelta(days=7)
                hist = await asyncio.wait_for(
                    provider.get_history_value(
                        config.identifier, config.identifier_type, params,
                        start_date, end_date,
                    ),
                    timeout=15.0,
                )
                points = hist.prices if hist else []
                date_range_str = None
                if points:
                    dates = [p.date for p in points]
                    date_range_str = f"{min(dates)} → {max(dates)}"

                history_result = ProbeHistoryResult(
                    success=True,
                    points_count=len(points),
                    date_range=date_range_str,
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )
            except Exception as e:
                history_result = ProbeHistoryResult(
                    success=False,
                    error=str(e),
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )

        # --- metadata ---
        if ProbeOperation.METADATA in operations:
            op_start = time.monotonic_ns()
            try:
                patch = await asyncio.wait_for(
                    provider.fetch_asset_metadata(
                        config.identifier, config.identifier_type, params,
                    ),
                    timeout=15.0,
                )
                metadata_result = ProbeMetadataResult(
                    success=patch is not None,
                    patch_data=patch,
                    error=None if patch else "Provider returned no metadata",
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )
            except Exception as e:
                metadata_result = ProbeMetadataResult(
                    success=False,
                    error=str(e),
                    execution_time_ms=(time.monotonic_ns() - op_start) // 1_000_000,
                )

        total_ms = (time.monotonic_ns() - total_start) // 1_000_000

        return FAProviderProbeResponse(
            provider_code=config.provider_code,
            identifier=config.identifier,
            total_execution_time_ms=total_ms,
            provider_url=provider_url,
            current_price=current_price_result,
            history=history_result,
            metadata=metadata_result,
        )
```

#### 3.4d) Endpoint

**File**: `backend/app/api/v1/assets.py`

```python
@provider_router.post("/probe", response_model=FAProviderProbeResponse)
async def probe_provider_config(
    request: FAProviderProbeRequest,
    _current_user: User = Depends(get_current_user),
):
    """
    Probe a provider configuration without persisting anything (dry-run).

    Executes selected operations against the provider and returns results
    with per-operation execution time. Nothing is stored in the database.

    Operations:
    - current_price: Fetch latest price
    - history: Fetch last 7 days of price history
    - metadata: Fetch asset metadata (identifiers, type, classification)

    Use cases:
    - Test provider configuration before assigning
    - "Ask Provider" button to fetch identifiers
    - Verify provider is working correctly
    """
    try:
        result = await AssetSourceManager.probe_provider_config(
            config=request,
            operations=request.operations,
        )
        return result
    except AssetSourceError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### Tasks 3.4

- [ ] Creare `ProbeOperation` enum in `provider.py`
- [ ] Creare `FAProviderProbeRequest(FAProviderConfigBase)` in `provider.py`
- [ ] Creare `ProbeCurrentPriceResult`, `ProbeHistoryResult`, `ProbeMetadataResult` in `provider.py`
- [ ] Creare `FAProviderProbeResponse` in `provider.py`
- [ ] Creare `probe_provider_config()` in `asset_source.py` con timeout 15s per operazione e `execution_time_ms`
- [ ] Creare endpoint `POST /assets/provider/probe` in `assets.py`

---

### 3.5 — Backend: Test + Rigenerazione API (~0.2 giorni)

1. **Test `user_url` round-trip** in `test_assets_provider.py`:
   - Assign con `user_url="https://example.com"` → GET assignments → verifica `user_url` presente
   - Verifica `provider_url` calcolato (es. `https://finance.yahoo.com/quote/AAPL`)

2. **Test probe `["current_price"]` con yfinance**:
   - POST probe con `{provider_code: "yfinance", identifier: "AAPL", identifier_type: "TICKER", operations: ["current_price"]}`
   - Verifica `current_price.success=true`, `execution_time_ms > 0`, `value > 0`
   - Verifica `history` e `metadata` sono `null` (non richiesti)

3. **Test probe bulk `["current_price", "history", "metadata"]`**:
   - POST probe con tutte le operazioni
   - Verifica tutte e 3 presenti, `total_execution_time_ms` coerente
   - Verifica `metadata.patch_data.identifier_ticker` populated

4. **Test probe con identifier invalido**:
   - POST probe con identifier inesistente
   - Verifica `current_price.success=false` con errore

5. **Test probe con mockprov**:
   - Verifica dry-run funziona col mock

6. **Test probe `["metadata"]` con yfinance (AAPL)**:
   - Verifica `patch_data.identifier_ticker = "AAPL"`
   - Verifica `patch_data.identifier_isin` populated (se disponibile)

7. Verificare test esistenti: `./dev.py test api run`
8. `./dev.py db create-clean` (per user_url column)
9. `./dev.py api sync` (rigenerare client Zodios)

#### Tasks 3.5

- [ ] Test user_url round-trip + provider_url calcolato
- [ ] Test probe `["current_price"]` con yfinance
- [ ] Test probe bulk `["current_price", "history", "metadata"]`
- [ ] Test probe con identifier invalido
- [ ] Test probe con mockprov
- [ ] Test probe `["metadata"]` verifica identifiers
- [ ] `./dev.py test api run` — tutti i test passano
- [ ] `./dev.py db create-clean`
- [ ] `./dev.py api sync`

---

### 3.6 — Frontend: `AssetSearchAutocomplete.svelte` (~0.2 giorni)

**File**: `src/lib/components/assets/AssetSearchAutocomplete.svelte`

```
── Search Online ──────────────────────────────────
🔍 [Search by name, ticker, ISIN...           ]
Providers: [X] Yahoo Finance  [X] JustETF
┌────────────────────────────────────────────────────┐
│ 🍎 Apple Inc.     AAPL · USD · STOCK   [🔗]       │
│    via Yahoo Finance                               │
│ 🌍 iShares Core   IE00B4L5Y983 · EUR · ETF  [🔗]  │
│    via JustETF                                     │
└────────────────────────────────────────────────────┘
```

1. Input debounced (300ms), chiama `GET /assets/provider/search?q=...&providers=...`.
2. Provider checkbox row: caricati da `GET /assets/provider`, mostra solo `supports_search=true`, tutti selezionati di default.
3. Dropdown risultati: icona, `display_name`, `identifier · currency · asset_type`, `via {provider_name}`, link `[🔗]` con `provider_url` (dal backend).
4. Evento `onselect(result: FAProviderSearchResultItem)`.
5. Loading spinner, empty state ("No results"), error state.
6. Svelte 5 runes (`$state`, `$derived`, `$effect`).

#### Tasks 3.6

- [ ] Creare `AssetSearchAutocomplete.svelte`
- [ ] Input debounced 300ms
- [ ] Provider checkbox row (da `GET /assets/provider`, solo `supports_search=true`)
- [ ] Dropdown risultati con `provider_url` link
- [ ] Evento `onselect`
- [ ] Loading, empty, error states

---

### 3.7 — Frontend: `ProviderAssignmentSection.svelte` (~0.3 giorni)

**File**: `src/lib/components/assets/ProviderAssignmentSection.svelte`

Componente riusabile (modal Step 3 + detail page Step 4):

```
▼ Provider Assignment
┌────────────────────────────────────────────────────┐
│ [ ] No Provider                                    │
│ Provider: [yfinance        ▾]                       │
│ Identifier: [AAPL                               ]   │
│ Identifier Type: [TICKER         ▾]                 │
│ (campi dinamici da params_schema, es. cssscraper:)  │
│ (  CSS Selector *: [span.price-value          ]  )  │
│ (  Decimal Format: [US ▾]                        )  │
│ User URL:   [https://investor.apple.com   ] [🔗]    │
│ Provider URL: (https://finance.yahoo.com/...) [🔗]  │
│                                                    │
│                                  [Test Configuration]│
│                                                    │
│ Current Price: ✅ 198.42 USD          (0.45s)       │
│ History:       ✅ 7 points            (0.89s)       │
│                              Total: 1.34s           │
└────────────────────────────────────────────────────┘
```

1. **Props**: `providerCode`, `identifier`, `identifierType`, `providerParams`, `userUrl`,
   `noProvider`, `disabled` (VIEWER), `readonly` (view mode), `providerUrl` (from backend/search).
2. Al cambio `providerCode` → carica `params_schema` da `GET /assets/provider` e genera form
   dinamico (`string`→input, `number`→input[type=number], `select`→SimpleSelect, `json`→textarea).
3. Bottone "Test Configuration" → chiama `POST /assets/provider/probe` con
   `operations: ["current_price", "history"]`. Mostra risultati inline:
   - ⚪ Not Tested (stato iniziale)
   - ⏳ Testing... (durante la richiesta)
   - ✅ 198.42 USD (0.45s) / ❌ Error message (0.45s)
   - Riga totale: `Total: 1.34s`
4. Link `[🔗]` User URL (editabile, apre in nuova tab) e Provider URL (readonly, da backend).
5. Checkbox "No Provider" → nasconde tutti i campi.
6. Evento `onchange({providerCode, identifier, identifierType, providerParams, userUrl, noProvider, testResults})`.
7. Svelte 5 runes.

#### Tasks 3.7

- [ ] Creare `ProviderAssignmentSection.svelte`
- [ ] Form dinamico da `params_schema`
- [ ] Bottone "Test Configuration" con probe `["current_price", "history"]`
- [ ] Risultati inline con `execution_time_ms` per riga + totale
- [ ] User URL editabile + Provider URL readonly con link `[🔗]`
- [ ] Checkbox "No Provider"
- [ ] Evento `onchange`

---

### 3.8 — Frontend: `AssetModal.svelte` (~0.5 giorni)

**File**: `src/lib/components/assets/AssetModal.svelte`

#### Layout — Create mode (stato iniziale)

```
┌──────────────────────────────────────────────────────────┐
│  ✕                    Add Asset                          │
├──────────────────────────────────────────────────────────┤
│  ── Search Online ──────────────────────────────────     │
│  🔍 Search by name, ticker, ISIN...                      │
│  Providers: [ ] Yahoo Finance  [ ] JustETF                │
│  (No search results)                                     │
│                                                          │
│  ── Asset Details ──────────────────────────────────     │
│  Display Name *  [                               ]       │
│  Asset Type *    [ STOCK           ▾]                    │
│  Currency *      [ 🇺🇸 USD          ▾]                   │
│  Icon            [📎 Choose image...       ]             │
│                                                          │
│  ▸ Identifiers (click to expand)                         │
│  ▸ Provider Assignment (click to expand)                 │
│                                                          │
│                          [Cancel]  [Create Asset]        │
└──────────────────────────────────────────────────────────┘
```

#### Layout — Dopo selezione search (auto-fill + auto-test)

```
┌──────────────────────────────────────────────────────────┐
│  ✕                    Add Asset                          │
├──────────────────────────────────────────────────────────┤
│  ── Search Online ──────────────────────────────────     │
│  🔍 [Apple                                        ]      │
│  Providers: [X] Yahoo Finance  [X] JustETF                │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 🍎 Apple Inc.  AAPL · USD · STOCK  via yfinance ← │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ── Asset Details ──────────────────────────────────     │
│  Display Name *  [ Apple Inc.              ]             │
│  Asset Type *    [ STOCK           ▾]                    │
│  Currency *      [ 🇺🇸 USD          ▾]                   │
│  Icon            [📎 Choose image...       ]             │
│                                                          │
│  ▼ Identifiers                        [🔄 Ask Provider]  │
│  ┌────────────────────────────────────────────────────┐  │
│  │ ISIN   [               ] Ticker [AAPL           ] │  │
│  │ CUSIP  [               ] SEDOL  [               ] │  │
│  │ FIGI   [               ]                          │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ▼ Provider Assignment (auto-filled, testing...)         │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Provider: yfinance  Identifier: AAPL / TICKER      │  │
│  │ User URL:   [                            ] [🔗]    │  │
│  │ Provider URL: (finance.yahoo.com/quote/AAPL) [🔗]  │  │
│  │                                                    │  │
│  │ Current Price: ⏳ Testing...                        │  │
│  │ History:       ⏳ Testing...                        │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ⓘ Provider "yfinance" will be auto-assigned on create   │
│                          [Cancel]  [Create Asset]        │
└──────────────────────────────────────────────────────────┘
```

#### Layout — Dopo "Ask Provider" con risultati

```
┌──────────────────────────────────────────────────────────┐
│  ...header + search + details (come sopra)...            │
│                                                          │
│  ▼ Identifiers                        [🔄 Ask Provider]  │
│  ┌────────────────────────────────────────────────────┐  │
│  │ ISIN   [US0378331005 ✔️] Ticker [AAPL      ✔️ ]   │  │
│  │ CUSIP  [               ] SEDOL  [               ] │  │
│  │ FIGI   [               ]                          │  │
│  └────────────────────────────────────────────────────┘  │
│  ✔️ = auto-filled from provider                          │
│                                                          │
│  ▼ Provider Assignment (tested ✅)                        │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Provider: yfinance  Identifier: AAPL / TICKER      │  │
│  │ User URL:   [                            ] [🔗]    │  │
│  │ Provider URL: (finance.yahoo.com/quote/AAPL) [🔗]  │  │
│  │                                                    │  │
│  │ Current Price: ✅ 198.42 USD          (0.45s)       │  │
│  │ History:       ✅ 7 points            (0.89s)       │  │
│  │                              Total: 1.34s           │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ⓘ Provider "yfinance" will be auto-assigned on create   │
│                          [Cancel]  [Create Asset]        │
└──────────────────────────────────────────────────────────┘
```

#### Layout — Edit mode con identifier conflict (⚠️)

```
┌──────────────────────────────────────────────────────────┐
│  ✕                    Edit Asset                         │
├──────────────────────────────────────────────────────────┤
│  ...search + details...                                  │
│                                                          │
│  ▼ Identifiers                        [🔄 Ask Provider]  │
│  ┌────────────────────────────────────────────────────┐  │
│  │ ISIN   [US0378331005   ] Ticker [AAPL ⚠️ MSFT ]   │  │
│  │ CUSIP  [037833100      ] SEDOL  [2046251      ]   │  │
│  │ FIGI   [BBG000B9XRY4   ]                          │  │
│  └────────────────────────────────────────────────────┘  │
│  ⚠️ = provider suggests different value (shown on hover)  │
│  ...rest of modal...                                     │
└──────────────────────────────────────────────────────────┘
```

#### Specifiche

1. **Create mode**: search visible, form vuoto, identifiers+provider collapsati.
2. **Edit mode**: search visible (può ri-cercare), form pre-popolato, identifiers+provider espansi se provider assegnato.
3. **Workflow post-selezione search** (automatico):
   a. Auto-fill form (`display_name`, `asset_type`, `currency`) dal search result.
   b. Auto-fill `identifier_{type.lower()}` nell'identifiers section (es. `identifier_ticker = "AAPL"` per yfinance).
   c. Auto-expand Provider Assignment + auto-populate con `provider_code`, `identifier`, `identifier_type`, `provider_url` dal risultato.
   d. **Auto-trigger** `POST /assets/provider/probe` con `operations: ["current_price", "history"]` — mostra ⏳ poi ✅/❌ con timing.
4. **Pulsante "🔄 Ask Provider"** nella sezione Identifiers:
   a. Chiama `POST /assets/provider/probe` con `operations: ["metadata"]`.
   b. Risposta `metadata.patch_data` contiene `identifier_isin`, `identifier_ticker`, ecc.
   c. Campi **vuoti** → compilati automaticamente (✔️ verde).
   d. Campi **pre-esistenti** con valore **diverso** → ⚠️ giallo accanto al campo. Tooltip mostra il valore suggerito dal provider. Al "Create/Save" i valori nel form (compresi quelli con ⚠️) vengono salvati — l'utente può accettare o rifiutare manualmente modificando il campo prima di salvare.
   e. Campi non ritornati dal provider → invariati.
5. Submit create: `POST /assets` → se provider: `POST /assets/provider` (con `user_url`) → toast + chiudi.
6. Submit edit: `PATCH /assets` → se provider cambiato: `DELETE` old + `POST /assets/provider` new → toast + chiudi.
7. Banner info: "Provider X will be auto-assigned on create" quando search result selezionato in create mode.
8. Validazione: `display_name` obbligatorio, errore unicità 409 dal backend mostrato inline.
9. `user_role`: VIEWER non può aprire in create/edit.
10. `ModalBase` con `allowOverflow={true}` per dropdown.
11. Svelte 5 runes.

#### Tasks 3.8

- [ ] Creare `AssetModal.svelte` con `ModalBase`
- [ ] Create mode: search + form + identifiers collapsible + provider collapsible
- [ ] Edit mode: pre-populate + expand provider if assigned
- [ ] Auto-fill form da search result
- [ ] Auto-trigger probe `["current_price", "history"]` dopo selezione
- [ ] Pulsante "🔄 Ask Provider": probe `["metadata"]` → fill identifiers (✔️ vuoti, ⚠️ conflitti)
- [ ] Auto-assign provider on create (2-step: POST /assets → POST /assets/provider)
- [ ] Edit: PATCH /assets + gestione provider change
- [ ] Banner info "Provider X will be auto-assigned"
- [ ] ImagePickerWrapper per icon_url
- [ ] CurrencySearchSelect per currency
- [ ] SimpleSelect per asset_type
- [ ] Validazione display_name + 409 inline
- [ ] user_role VIEWER check

---

### 3.9 — Frontend: Confirmation Modals (~0.1 giorni)

#### 3.9a) Save without test / test failed

Se provider configurato ma probe non eseguito o con errori → `ConfirmModal`:

```
┌──────────────────────────────────────────────────────────┐
│  ⚠️  Save Without Testing?                               │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  You are about to save the asset "My Custom Asset"       │
│  without verifying the provider configuration.           │
│                                                          │
│  This may cause errors when fetching price data.         │
│                                                          │
│                     [Cancel]  [Save Anyway]              │
└──────────────────────────────────────────────────────────┘
```

#### 3.9b) Change identifier in edit mode

Se nuova ricerca seleziona identifier diverso dall'attuale → `ConfirmModal`:

```
┌──────────────────────────────────────────────────────────┐
│  ⚠️  Confirm Asset Change                                │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  You are about to change the provider to "JustETF".      │
│                                                          │
│  The selected asset has a Ticker (EWG) different from    │
│  the current one (AAPL).                                 │
│                                                          │
│  Are you sure you want to associate "Apple Inc." with    │
│  a different financial instrument?                       │
│                                                          │
│                     [Cancel]  [Confirm Change]           │
└──────────────────────────────────────────────────────────┘
```

Entrambe usano il componente `ConfirmModal` esistente (`$lib/components/ui/ConfirmModal.svelte`).

#### Tasks 3.9

- [ ] Logica ConfirmModal "Save without test" (trigger: provider configurato + probe non ok)
- [ ] Logica ConfirmModal "Change identifier" (trigger: edit mode + identifier diverso)

---

### 3.10 — Frontend: E3 + i18n + Integrazione pagina (~0.2 giorni)

#### 3.10a) E3 Toggle Abs/%

La pagina lista assets (`assets/+page.svelte`) ha già un toggle Abs/% nella filter bar.
Propagare come prop alle `AssetCard`:
- In Abs mode → mostrare `+1.23 EUR` (con suffisso valuta).
- In % mode → mostrare `+2.3%` (come attualmente).
- Collegare ai segnali visivi verde ▲ / rosso ▼ di `PriceChartCompact`.

#### 3.10b) i18n

Aggiungere ~40 chiavi con `./dev.py i18n add` in EN/IT/FR/ES:

```
assets.modal.title
assets.modal.titleEdit
assets.modal.searchOnline
assets.modal.assetDetails
assets.modal.identifiers
assets.modal.createAsset
assets.modal.saveChanges
assets.modal.autoAssignInfo

assets.provider.assignment
assets.provider.noProvider
assets.provider.testConfig
assets.provider.testing
assets.provider.userUrl
assets.provider.providerUrl
assets.provider.selectProvider
assets.provider.identifier
assets.provider.identifierType

assets.probe.currentPrice
assets.probe.history
assets.probe.metadata
assets.probe.notTested
assets.probe.passed
assets.probe.failed
assets.probe.executionTime
assets.probe.totalTime

assets.identifiers.askProvider
assets.identifiers.askProviderHint
assets.identifiers.autoFilled
assets.identifiers.conflictWarning

assets.confirm.saveWithoutTest
assets.confirm.saveWithoutTestMessage
assets.confirm.saveAnyway
assets.confirm.identifierChanged
assets.confirm.identifierChangedMessage
assets.confirm.confirmChange

assets.search.placeholder
assets.search.providers
assets.search.noResults
assets.search.searching
```

#### 3.10c) Integrazione nella pagina lista

**File**: `src/routes/(app)/assets/+page.svelte`

- Collegare "Add Asset" button → apre `AssetModal` in create mode.
- Collegare azione "Edit" (card footer + table row) → apre `AssetModal` in edit mode con dati pre-popolati.
- Callback `oncreated` / `onupdated` → refresh lista.

#### 3.10d) Barrel export

**File**: `src/lib/components/assets/index.ts`

Aggiungere:
```typescript
export {default as AssetModal} from './AssetModal.svelte';
export {default as AssetSearchAutocomplete} from './AssetSearchAutocomplete.svelte';
export {default as ProviderAssignmentSection} from './ProviderAssignmentSection.svelte';
```

#### Tasks 3.10

- [ ] E3: propagare toggle Abs/% come prop alle AssetCard + suffisso valuta
- [ ] i18n: ~40 chiavi via `./dev.py i18n add` (EN/IT/FR/ES)
- [ ] Integrazione "Add Asset" → AssetModal create mode
- [ ] Integrazione "Edit" card/table → AssetModal edit mode
- [ ] Barrel export aggiornato

---

## 4. Riepilogo File

### Backend (modifiche)

```
backend/app/schemas/provider.py                                     # FAProviderConfigBase, ereditarietà, probe schemas, provider_url
backend/app/db/models.py                                            # AssetProviderAssignment.user_url
backend/alembic/versions/001_initial.py                             # colonna user_url
backend/app/services/asset_source.py                                # get_asset_url(), probe_provider_config()
backend/app/services/asset_source_providers/yahoo_finance.py        # get_asset_url(), fetch_asset_metadata potenziato
backend/app/services/asset_source_providers/justetf.py              # get_asset_url(), fetch_asset_metadata nuovo
backend/app/services/asset_source_providers/css_scraper.py          # get_asset_url()
backend/app/api/v1/assets.py                                        # POST /assets/provider/probe, provider_url in responses
backend/test_scripts/test_db/populate_mock_data.py                  # user_url negli assignment
backend/test_scripts/test_api/test_assets_provider.py               # nuovi test probe + user_url
```

### Frontend (nuovi)

```
src/lib/components/assets/AssetSearchAutocomplete.svelte            # Smart search multi-provider
src/lib/components/assets/ProviderAssignmentSection.svelte          # Provider config + test + URLs (riusabile)
src/lib/components/assets/AssetModal.svelte                         # Create/Edit modale completo
```

### Frontend (modifiche)

```
src/lib/components/assets/index.ts                                  # barrel export aggiornato
src/routes/(app)/assets/+page.svelte                                # integrazione modale + E3 toggle
src/lib/components/assets/AssetCard.svelte                          # E3: prop abs/% + suffisso valuta
```

### Rigenerazione

```
./dev.py db create-clean                                            # nuova colonna user_url
./dev.py api sync                                                   # client Zodios
```

---

## 5. Stima Totale: ~2.5 giorni

| Sotto-Step | Giorni | Contenuto |
|------------|--------|-----------|
| 3.1 | 0.25 | Schema inheritance + user_url + DB + populate |
| 3.2 | 0.15 | get_asset_url() + provider_url in search/read |
| 3.3 | 0.15 | fetch_asset_metadata potenziato (yfinance + justetf) |
| 3.4 | 0.25 | POST /assets/provider/probe (bulk modulare) |
| 3.5 | 0.20 | Test backend + API sync |
| 3.6 | 0.20 | AssetSearchAutocomplete.svelte |
| 3.7 | 0.30 | ProviderAssignmentSection.svelte |
| 3.8 | 0.50 | AssetModal.svelte |
| 3.9 | 0.10 | Confirmation modals |
| 3.10 | 0.20 | E3 + i18n + integrazione pagina |

---

## 6. Dependency Graph

```
Step 3.1 (Schema inheritance + user_url + DB)
    │
    ├── Step 3.2 (get_asset_url + provider_url)
    │
    ├── Step 3.3 (fetch_asset_metadata potenziato)
    │       │
    │       └──┐
    │          │
    ├── Step 3.4 (POST /assets/provider/probe) ← dipende da 3.1 + 3.2 + 3.3
    │       │
    │       └── Step 3.5 (Test backend + API sync) ← dipende da 3.4
    │               │
    │               ├── Step 3.6 (AssetSearchAutocomplete) ← dipende da API sync
    │               │
    │               ├── Step 3.7 (ProviderAssignmentSection) ← dipende da API sync + probe
    │               │       │
    │               │       └── Step 3.8 (AssetModal) ← dipende da 3.6 + 3.7
    │               │               │
    │               │               ├── Step 3.9 (Confirmation modals) ← dentro AssetModal
    │               │               │
    │               │               └── Step 3.10 (E3 + i18n + integrazione)
    │               │
    │               └── (3.6, 3.7 possono partire in parallelo dopo API sync)
    │
    └── (3.2, 3.3 possono partire in parallelo dopo 3.1)
```

---

## 7. Note per l'Implementazione

1. **Probe timeout**: i provider esterni (yfinance, justetf) possono essere lenti. Timeout 15s per
   operazione con `asyncio.wait_for`. Se scade → `success: false`, `error: "Timeout after 15s"`,
   `execution_time_ms` comunque popolato. L'UI mostra ❌ con il tempo.

2. **Backend unica fonte di verità**: `provider_url` è SEMPRE calcolato dal backend (tramite
   `get_asset_url`). Il frontend non fa calcoli locali — chiede al backend via search result
   (`FAProviderSearchResultItem.provider_url`) o assignment read (`FAProviderAssignmentReadItem.provider_url`).

3. **Scope `ProviderAssignmentSection` vs Step 4**: qui la usiamo solo dentro `AssetModal`. In
   Step 4 la incastriamo nel detail page senza modifiche al componente.

4. **JustETF `fetch_asset_metadata`**: best-effort. Se il DataFrame ha `ticker`, lo estraiamo.
   `identifier_isin` = identifier stesso (JustETF usa ISIN come chiave). Nessun blocco se fallisce.

5. **`FAAssetPatchItem` nel probe**: il campo `asset_id` è un placeholder (0) perché il probe
   non opera su asset persistiti. Il frontend ignora questo campo quando usa `patch_data` per
   popolare gli identifiers nella modale.

6. **Workflow auto-test dopo selezione**: la sequenza è sincrona dall'utente ma asincrona internamente:
   1. Utente seleziona risultato search
   2. Form si auto-compila (istantaneo)
   3. Provider section si espande con ⏳ Testing...
   4. Probe `["current_price", "history"]` parte in background
   5. Risultati appaiono con ✅/❌ + timing
   6. Utente può procedere al salvataggio anche durante il test (con ConfirmModal di warning)

