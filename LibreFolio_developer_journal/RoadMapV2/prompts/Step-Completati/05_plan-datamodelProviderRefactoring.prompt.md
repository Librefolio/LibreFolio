# Plan: Rifacimento DataModel e Provider System per Asset Management

Il progetto ha subito un'evoluzione concettuale durante lo sviluppo: la tabella `asset_provider_assignments` è diventata centrale, mentre alcuni campi in `Asset` devono essere spostati o rimossi. Il plugin system deve diventare indipendente dal DB (tranne `scheduled_investment` che recupera le transazioni internamente), e gli endpoint API vanno riorganizzati per riflettere la nuova architettura. Database esistenti vanno eliminati e ricreati con Alembic.

## Context

### Problemi identificati dai TODO nel codice:

1. **ValuationModel enum** (models.py:98) - Da rimuovere perché `asset_provider_assignments` gestisce la valutazione in modo più flessibile
2. **Vincoli di unicità Asset** (models.py:328) - Aggiungere constraint `UNIQUE(display_name)` per evitare confusione utente
3. **identifier e identifier_type** (models.py:393) - Spostare da `Asset` a `asset_provider_assignments` (legati al provider)
4. **interest_schedule** (models.py:402) - Spostare da `Asset.interest_schedule` a `asset_provider_assignments.provider_params` (solo per scheduled_investment provider)
5. **Provider methods** (asset_source.py:113, 140, 205) - Passare identifier E identifier_type ai provider
6. **API endpoints** (assets.py:119) - Creare PATCH /assets per bulk update, rimuovere metadata/refresh, creare nuovi endpoint /provider
7. **Garbage collector** (asset_source.py:229) - Metodo per pulizia cache (TODO mantenuto per dopo logica fuzzy)
8. **YahooFinance** (yahoo_finance.py:353) - investment_type non più metadato ma campo primario `asset_type`

### Decisioni architetturali:

- **Vincolo unicità**: Solo `display_name` UNIQUE, sta all'utente evitare asset duplicati
- **Provider params**: Resta TEXT nel DB, validazione nei plugin (libertà per contributori)
- **Relazione 1-to-1**: Asset ↔ AssetProviderAssignment (scheduled_investment sono asset manuali)
- **Merge strategy PATCH**: Campo presente (anche None) = update/blank, campo assente = ignora
- **JSON optimization**: Campi sbiancati omessi dalla stringa JSON salvata
- **Migration**: Nessuna retrocompatibilità, modificare 001_initial.py direttamente
- **_transaction_override**: Mantenuto per test, evita creazione record DB nei test service
- **Backward-fill**: scheduled_investment deve supportare per uniformità (anche se sempre None)
- **Refresh strategy**: NO auto-refresh durante provider assignment. Refresh è ESPLICITO via POST /assets/provider/refresh
- **Field selection in refresh**: L'endpoint refresh supporta selezione campi opzionale:
  - Se `fields` non specificato: aggiorna tutti i campi che il provider riesce a ottenere
  - Se `fields` specificato: aggiorna solo quei campi (keys di FAAssetPatchItem e sottochiavi, es. ['asset_type', 'classification_params.sector'])
  - I campi sono ottenuti dinamicamente da FAAssetPatchItem.model_fields
- **Refresh response**: Liste dinamiche di `refreshed_fields`, `missing_data_fields`, `ignored_fields` da FAAssetPatchItem

## Steps

### ✅ 1. Ristrutturare il modello `Asset` in models.py - COMPLETATO

**File**: `backend/app/db/models.py`

**Changes**:
- ✅ Eliminare completamente `ValuationModel` enum (linee 96-133)
- ✅ Rimuovere campi da Asset: `identifier`, `identifier_type`, `valuation_model`, `interest_schedule` (linee 393-407)
- ✅ Aggiungere `__table_args__` con `UniqueConstraint("display_name")`
- ✅ Aggiornare docstring Asset eliminando:
  - Riferimenti a interest_schedule e FAScheduledInvestmentSchedule schema
  - Logica di provider assignments basata su valuation_model
  - Esempi con face_value e maturity_date (non più applicabili a livello Asset)
- ✅ Mantenere `classification_params` (JSON TEXT) e `asset_type` (enum)
- ✅ Aggiornare commenti AssetType enum rimuovendo riferimenti a valuation_model
- ✅ Rimosso da base.py e __init__.py

**Rationale**: Asset diventa un contenitore "puro" di metadati generali (nome, tipo, classificazione), mentre la logica di pricing e identificazione migra completamente in AssetProviderAssignment.

---

### ✅ 2. Estendere `AssetProviderAssignment` in models.py - COMPLETATO

**File**: `backend/app/db/models.py`

**Changes**:
- Aggiungere campi dopo `asset_id`:
  ```python
  identifier: str = Field(nullable=False, description="Asset identifier for this provider (ticker, ISIN, UUID, etc.)")
  identifier_type: IdentifierType = Field(nullable=False, description="Type of identifier (TICKER, ISIN, UUID, etc.)")
  ```
- Aggiornare docstring con:
  - Nuovi campi identifier/identifier_type spiegando che rappresentano come il provider vede l'asset
  - Esempio provider_params per scheduled_investment: `{"schedule": [...], "late_interest": {...}}` (FAScheduledInvestmentSchedule JSON)
  - Esempio provider_params per yfinance: `{}` o `{"some_config": "value"}` (identifier ora campo separato)
  - Esempio provider_params per cssscraper: `{"url": "https://...", "selector": ".price"}` (identifier è l'URL, tipo è OTHER)
- Rimuovere da docstring:
  - Riferimenti a valuation_model (non più esistente)
  - Frasi su "Assets with valuation_model=MANUAL/SCHEDULED_YIELD: No provider needed"

**Rationale**: AssetProviderAssignment diventa la "fonte di verità" per come un asset viene identificato e prezzato, con provider_params completamente flessibile (TEXT validato dai plugin).

---

### ✅ 3. Aggiornare migration 001_initial.py - COMPLETATO

**File**: `backend/alembic/versions/001_initial.py`

**Changes**:
- Modificare CREATE TABLE assets (linee ~33-45):
  - Eliminare colonne: `identifier`, `identifier_type`, `valuation_model`, `interest_schedule`
  - Aggiungere dopo la creazione tabella: `conn.execute(sa.text("CREATE UNIQUE INDEX uq_assets_display_name ON assets (display_name)"))`
- Modificare CREATE TABLE asset_provider_assignments (linee ~106-124):
  - Aggiungere colonne dopo `provider_code`:
    ```sql
    identifier            VARCHAR     NOT NULL,
    identifier_type       VARCHAR(6)  NOT NULL,
    ```
  - Mantenere provider_params come TEXT
- Aggiornare print statements per riflettere nuove colonne

**Post-migration actions**:
- Eliminare manualmente tutti i file `backend/data/*.db` e `backend/data/*.db-journal`
- Eseguire `cd backend && alembic upgrade head`
- Verificare con `alembic current` che 001_initial sia applicata
- Testare creazione manuale di asset + provider assignment

**Rationale**: Modifica diretta della migration iniziale senza creare nuove migration (siamo pre-alpha, nessun dato in produzione).

---

### ✅ 4. Aggiornare interfaccia `AssetSourceProvider` in asset_source.py - COMPLETATO

**File**: `backend/app/services/asset_source.py`

**Changes**:
- Aggiungere parametro `identifier_type: IdentifierType` dopo `identifier: str` nei metodi:
  - `get_current_value` (linea ~117)
  - `get_history_value` (linea ~144)
  - `fetch_asset_metadata` (linea ~208)
- Rimuovere i 3 commenti TODO per identifier_type (linee ~113, 140, 205)
- Aggiornare docstring metodi includendo il nuovo parametro:
  ```python
  Args:
      identifier: Asset identifier for provider (e.g., ticker, ISIN, UUID)
      identifier_type: Type of identifier (TICKER, ISIN, UUID, etc.)
      provider_params: Provider-specific configuration (JSON)
  ```
- Mantenere TODO per garbage collector (linea ~229): `# TODO: definire metodo da far chiamare periodicamente ad un job garbage collector, per ripulire eventuali cache`

**Rationale**: Interfaccia uniforme per tutti i provider, permettendo validazione del tipo di identifier (es. yfinance accetta solo TICKER/ISIN, scheduled_investment accetta UUID).

---

### ✅ 5. Aggiornare `ScheduledInvestmentProvider` in scheduled_investment.py - COMPLETATO

**File**: `backend/app/services/asset_source_providers/scheduled_investment.py`

**Changes**:
- Mantenere logica `_transaction_override` in provider_params (linea ~87):
  ```python
  transaction_override = provider_params.get("_transaction_override")
  if transaction_override:
      transactions = transaction_override
      # Parse schedule from provider_params (not Asset.interest_schedule)
      params_copy = {k: v for k, v in provider_params.items() if k != "_transaction_override"}
      schedule = self.validate_params(params_copy)
  ```
- Modificare sezione "Production mode" per leggere schedule da provider_params:
  ```python
  else:
      async for session in get_session_generator():
          asset = await self._get_asset_from_db(asset_id, session)
          transactions = await self._get_transactions_from_db(asset_id, session)
          
          # Get assignment to read provider_params
          assignment = await session.execute(
              select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == asset_id)
          )
          assignment = assignment.scalar_one_or_none()
          if not assignment or not assignment.provider_params:
              raise AssetSourceError(...)
          
          schedule = self.validate_params(json.loads(assignment.provider_params))
          currency = asset.currency
          break
  ```
- Implementare `validate_params` method:
  ```python
  def validate_params(self, params: dict | None) -> FAScheduledInvestmentSchedule:
      """Validate and deserialize provider_params as FAScheduledInvestmentSchedule."""
      if not params:
          raise AssetSourceError("provider_params required for scheduled_investment", "MISSING_PARAMS")
      
      # Remove test override if present
      params_clean = {k: v for k, v in params.items() if k != "_transaction_override"}
      
      try:
          return FAScheduledInvestmentSchedule.model_validate(params_clean)
      except Exception as e:
          raise AssetSourceError(f"Invalid schedule params: {e}", "INVALID_PARAMS")
  ```
- Aggiungere parametro `identifier_type: IdentifierType` a `get_current_value` e `get_history_value` (non usato ma richiesto da interfaccia)
- Supportare backward-fill info nelle response: sempre None per valori calcolati
  ```python
  return FACurrentValue(
      value=total_value,
      currency=currency,
      as_of_date=target_date,
      source=self.provider_name,
      backward_fill_info=None  # Always None for calculated values
  )
  ```
- Aggiornare docstring del file rimuovendo "Interest schedule from Asset.interest_schedule" e aggiungere "Interest schedule from provider_params (AssetProviderAssignment)"

**Rationale**: scheduled_investment rimane responsabile del recupero transazioni DB (unico plugin con accesso DB), ma legge configurazione da provider_params invece che da Asset.

---

### ✅ 6. Aggiornare `YahooFinanceProvider` in yahoo_finance.py - COMPLETATO

**File**: `backend/app/services/asset_source_providers/yahoo_finance.py`

**Changes**:
- ✅ Aggiungere parametro `identifier_type: IdentifierType` a `get_current_value`, `get_history_value`, `fetch_asset_metadata`
- ✅ Validare identifier_type nei metodi (solo TICKER e ISIN accettati)
- ✅ Modificare `fetch_asset_metadata` per ritornare dict con asset_type invece di FAClassificationParams
- ✅ Rimosso import inutilizzato FAClassificationParams
- ⚠️ **TODO**: Modificare `fetch_asset_metadata` per ritornare `FAAssetPatchItem` invece di dict generico (da fare dopo creazione schema)
  ```python
  async def fetch_asset_metadata(
      self,
      identifier: str,
      identifier_type: IdentifierType,
      provider_params: dict | None = None,
  ) -> dict | None:
      """
      Fetch asset metadata from Yahoo Finance.
      
      Returns:
          dict with keys: asset_type, sector, short_description, geographic_area (optional)
          or None if metadata unavailable
      """
      if not YFINANCE_AVAILABLE:
          return None
      
      try:
          ticker = yf.Ticker(identifier)
          info = ticker.info
          
          # Map quoteType to asset_type
          quote_type = info.get('quoteType', '').lower()
          investment_type_map = {
              'equity': 'STOCK',
              'etf': 'ETF',
              'mutualfund': 'FUND',
              'cryptocurrency': 'CRYPTO',
              # ... other mappings
          }
          asset_type = investment_type_map.get(quote_type, 'OTHER')
          
          # Get description
          short_description = info.get('longBusinessSummary', '')[:500] or info.get('shortName', '')
          
          # Get sector
          sector = info.get('sector')
          
          # Return dict (not FAClassificationParams)
          result = {
              'asset_type': asset_type,
              'short_description': short_description,
          }
          if sector:
              result['sector'] = sector
          
          return result
      except Exception as e:
          logger.warning(f"Could not fetch metadata for {identifier}: {e}")
          return None
  ```
- Aggiungere parametro `identifier_type: IdentifierType` a `get_current_value`, `get_history_value`, `fetch_asset_metadata`
- Validare identifier_type nei metodi:
  ```python
  if identifier_type not in [IdentifierType.TICKER, IdentifierType.ISIN]:
      raise AssetSourceError(
          f"Yahoo Finance only supports TICKER and ISIN, got {identifier_type}",
          "INVALID_IDENTIFIER_TYPE"
      )
  ```
- Rimuovere commento TODO su investment_type (linea ~353)
- Aggiornare docstring con nuovo parametro e ritorno dict

**Rationale**: Yahoo Finance ritorna dati completi per refresh (asset_type + metadata), permettendo aggiornamento atomico dell'asset via merge.

---

### ✅ 7. Creare schema `FAAssetPatchItem` in assets.py - COMPLETATO

**File**: `backend/app/schemas/assets.py`

**Changes**:
- ✅ Aggiunto FAAssetPatchItem con campi opzionali (asset_id obbligatorio + opzionali: display_name, currency, asset_type, classification_params, active)
- ✅ Aggiunto FABulkAssetPatchRequest e FABulkAssetPatchResponse
- ✅ Aggiunto FAAssetPatchResult con campo updated_fields
- ✅ Aggiornato FAAssetCreateItem rimuovendo identifier, identifier_type, valuation_model, interest_schedule
- ✅ Aggiornato __all__ export list
- ✅ Modificato YahooFinanceProvider.fetch_asset_metadata per ritornare FAAssetPatchItem
- ✅ Aggiornato AssetSourceProvider.fetch_asset_metadata signature per ritornare FAAssetPatchItem
- ✅ **CORREZIONE**: asset_type ora usa AssetType enum invece di str in FAAssetPatchItem e FAAssetCreateItem
- ✅ **CORREZIONE**: Aggiornate chiamate a fetch_asset_metadata per usare assignment.identifier/identifier_type e impostare asset_id corretto
- ✅ **DECISIONE**: Rimosso auto-refresh durante provider assignment (ora esplicito via endpoint dedicato)
- ✅ Aggiunto commento esplicativo nel codice con rationale della decisione

---

### ✅ 8. Aggiornare schema Provider in provider.py - COMPLETATO

**File**: `backend/app/schemas/provider.py`

**Changes**:
- ✅ Aggiunto campi obbligatori `identifier` e `identifier_type` a FAProviderAssignmentItem
- ✅ Aggiunto validator per identifier_type che verifica enum IdentifierType  
- ✅ Creato FAProviderAssignmentReadItem per risposta GET
- ✅ Creato FAProviderAssignmentsReadResponse
- ✅ Creato FAProviderRefreshFieldsDetail
- ✅ Aggiornato FAProviderAssignmentResult con fields_detail

---

### 9. Riorganizzare API endpoints in assets.py
  ```python
  class FAProviderAssignmentItem(BaseModel):
      model_config = ConfigDict(extra="forbid")
      
      asset_id: int = Field(..., description="Asset ID")
      provider_code: str = Field(..., description="Provider code (yfinance, cssscraper, scheduled_investment, etc.)")
      identifier: str = Field(..., description="Asset identifier for provider (ticker, ISIN, UUID, etc.)")
      identifier_type: str = Field(..., description="Identifier type (TICKER, ISIN, UUID, etc.)")  # Accept string, validate in validator
      provider_params: Optional[dict[str, Any]] = Field(None, description="Provider-specific configuration (JSON)")
      fetch_interval: int = Field(1440, description="Refresh frequency in minutes (default: 1440 = 24h)")
      
      @field_validator('identifier_type')
      @classmethod
      def validate_identifier_type(cls, v):
          """Validate identifier_type is valid enum value."""
          from backend.app.db.models import IdentifierType
          try:
              IdentifierType(v)
              return v
          except ValueError:
              valid_types = [t.value for t in IdentifierType]
              raise ValueError(f"Invalid identifier_type: {v}. Must be one of: {valid_types}")
      
      # ... existing validators
  ```
- Creare `FAProviderAssignmentReadItem` dopo `FAProviderAssignmentItem`:
  ```python
  class FAProviderAssignmentReadItem(BaseModel):
      """Provider assignment read response (includes all fields)."""
      model_config = ConfigDict(extra="forbid")
      
      asset_id: int
      provider_code: str
      identifier: str
      identifier_type: str
      provider_params: Optional[dict[str, Any]] = None
      fetch_interval: Optional[int] = None
      last_fetch_at: Optional[str] = None


  class FAProviderAssignmentsReadResponse(BaseModel):
      """Response for GET /assets/provider/assignments."""
      model_config = ConfigDict(extra="forbid")
      
      assignments: List[FAProviderAssignmentReadItem]
  ```
- Creare schema per refresh response fields detail:
  ```python
  class FAProviderRefreshFieldsDetail(BaseModel):
      """Field-level details for provider refresh operation."""
      model_config = ConfigDict(extra="forbid")
      
      refreshed_fields: List[str] = Field(..., description="Fields successfully refreshed from provider")
      missing_data_fields: List[str] = Field(..., description="Fields provider couldn't fetch (no data)")
      ignored_fields: List[str] = Field(..., description="Fields ignored by provider (not supported)")
  ```
- Aggiornare `FAProviderAssignmentResult` per includere fields_detail:
  ```python
  class FAProviderAssignmentResult(BaseModel):
      model_config = ConfigDict(extra="forbid")
      
      asset_id: int
      success: bool
      message: str
      fields_detail: Optional[FAProviderRefreshFieldsDetail] = None  # Add this
      # Remove old metadata_updated, metadata_changes
  ```

**Rationale**: Schema esteso per supportare identifier/identifier_type in assignments, con response dettagliata per refresh operations.

---

### ✅ 9. Riorganizzare API endpoints in assets.py - COMPLETATO

**File**: `backend/app/api/v1/assets.py`

**Changes**:
- Creare nuovo endpoint PATCH /assets dopo create_assets_bulk:
  ```python
  @asset_router.patch("", response_model=FABulkAssetPatchResponse, tags=["FA CRUD"])
  async def patch_assets_bulk(
      request: FABulkAssetPatchRequest,
      session: AsyncSession = Depends(get_session_generator)
  ):
      """
      Update multiple assets in bulk (partial success allowed).
      
      **Merge Logic**:
      - Field present (even if None): UPDATE or BLANK value
      - Field absent: IGNORE (keep existing value)
      
      **Example Request**:
      ```json
      {
        "assets": [
          {
            "asset_id": 1,
            "display_name": "Apple Inc. - Updated",
            "classification_params": {
              "sector": "Technology",
              "short_description": "New description"
            }
          },
          {
            "asset_id": 2,
            "classification_params": null,  // Clear metadata
            "active": false
          }
        ]
      }
      ```
      """
      try:
          return await AssetCRUDService.patch_assets_bulk(request.assets, session)
      except Exception as e:
          logger.error(f"Error in bulk asset patch: {e}")
          raise HTTPException(status_code=500, detail=str(e))
  ```
- Eliminare completamente endpoint `@metadata_router.patch("/metadata")` e import correlati
- Rinominare e spostare refresh endpoint:
  ```python
  @asset_router.post("/provider/refresh", response_model=FABulkRefreshResponse, tags=["FA Provider"])
  async def refresh_assets_from_provider(
      request: FABulkRefreshRequest,
      session: AsyncSession = Depends(get_session_generator)
  ):
      """
      Refresh asset data from assigned providers (bulk operation).
      
      Fetches latest metadata from provider and updates:
      - asset_type (if provider supports)
      - classification_params (sector, short_description, geographic_area)
      
      **Field-level response**:
      - refreshed_fields: Successfully updated from provider
      - missing_data_fields: Provider couldn't fetch (no data available)
      - ignored_fields: Provider doesn't support these fields
      
      **Example Response**:
      ```json
      {
        "results": [
          {
            "asset_id": 1,
            "success": true,
            "message": "Refreshed from yfinance",
            "fields_detail": {
              "refreshed_fields": ["asset_type", "sector", "short_description"],
              "missing_data_fields": ["geographic_area"],
              "ignored_fields": []
            }
          }
        ],
        "success_count": 1,
        "failed_count": 0
      }
      ```
      """
      try:
          return await AssetSourceManager.refresh_assets_from_provider(request.asset_ids, session)
      except Exception as e:
          logger.error(f"Error refreshing assets from provider: {e}")
          raise HTTPException(status_code=500, detail=str(e))
  ```
- Creare nuovo endpoint GET /provider/assignments:
  ```python
  @asset_router.get("/provider/assignments", response_model=FAProviderAssignmentsReadResponse, tags=["FA Provider"])
  async def get_provider_assignments(
      asset_ids: List[int] = Query(..., description="List of asset IDs"),
      session: AsyncSession = Depends(get_session_generator)
  ):
      """
      Get provider assignments for multiple assets.
      
      Returns identifier, identifier_type, and provider_params for each assigned asset.
      
      **Example**:
      ```
      GET /api/v1/assets/provider/assignments?asset_ids=1&asset_ids=2&asset_ids=3
      ```
      
      **Response**:
      ```json
      {
        "assignments": [
          {
            "asset_id": 1,
            "provider_code": "yfinance",
            "identifier": "AAPL",
            "identifier_type": "TICKER",
            "provider_params": {},
            "fetch_interval": 1440,
            "last_fetch_at": "2025-01-15T10:30:00Z"
          }
        ]
      }
      ```
      """
      try:
          # Query with WHERE IN
          stmt = select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id.in_(asset_ids))
          result = await session.execute(stmt)
          assignments = result.scalars().all()
          
          # Convert to response schema
          items = []
          for a in assignments:
              params = json.loads(a.provider_params) if a.provider_params else None
              items.append(FAProviderAssignmentReadItem(
                  asset_id=a.asset_id,
                  provider_code=a.provider_code,
                  identifier=a.identifier,
                  identifier_type=a.identifier_type,
                  provider_params=params,
                  fetch_interval=a.fetch_interval,
                  last_fetch_at=a.last_fetch_at.isoformat() if a.last_fetch_at else None
              ))
          
          return FAProviderAssignmentsReadResponse(assignments=items)
      except Exception as e:
          logger.error(f"Error getting provider assignments: {e}")
          raise HTTPException(status_code=500, detail=str(e))
  ```
- Aggiornare import statements per nuovi schema
- Aggiornare TODO comment (linea ~119) rimuovendo parti implementate

**Rationale**: API riorganizzata con naming consistente (/provider/... per operazioni provider), endpoint PATCH per bulk update, GET per lettura assignments.

---

### ✅ 10. Implementare merge logic PATCH in asset_crud.py - COMPLETATO

**File**: `backend/app/services/asset_crud.py`

**Changes**:
- Completare i pending TODO in asset_source.py e asset_providers che sono stati lasciati in attesa di questo step
- Aggiungere metodo `patch_assets_bulk` dopo `delete_assets_bulk`:
  ```python
  @staticmethod
  async def patch_assets_bulk(
      patches: List[FAAssetPatchItem],
      session: AsyncSession
  ) -> FABulkAssetPatchResponse:
      """
      Patch multiple assets in bulk (partial success allowed).
      
      Merge logic:
      - Field present in patch (even if None): UPDATE or BLANK
      - Field absent in patch: IGNORE (keep existing value)
      
      For classification_params:
      - If None: Set DB column to NULL
      - If present: model_dump_json(exclude_none=True) to omit blank subfields
      
      Args:
          patches: List of asset patches
          session: Database session
          
      Returns:
          FABulkAssetPatchResponse with per-item results
      """
      from backend.app.schemas.assets import FAAssetPatchResult
      
      results: list[FAAssetPatchResult] = []
      
      for patch in patches:
          try:
              # Fetch asset
              stmt = select(Asset).where(Asset.id == patch.asset_id)
              result = await session.execute(stmt)
              asset = result.scalar_one_or_none()
              
              if not asset:
                  results.append(FAAssetPatchResult(
                      asset_id=patch.asset_id,
                      success=False,
                      message=f"Asset {patch.asset_id} not found",
                      updated_fields=None
                  ))
                  continue
              
              # Track updated fields
              updated_fields = []
              
              # Update fields if present in patch (use model_dump to detect presence)
              patch_dict = patch.model_dump(exclude={'asset_id'}, exclude_unset=True)
              
              for field, value in patch_dict.items():
                  if field == 'classification_params':
                      if value is None:
                          asset.classification_params = None
                      else:
                          # value is FAClassificationParams instance
                          asset.classification_params = value.model_dump_json(exclude_none=True)
                      updated_fields.append('classification_params')
                  elif field == 'currency':
                      # Validate currency
                      asset.currency = normalize_currency_code(value) if value else asset.currency
                      updated_fields.append('currency')
                  elif field == 'asset_type':
                      # Validate enum
                      from backend.app.db.models import AssetType
                      if value:
                          try:
                              AssetType(value)
                              asset.asset_type = value
                              updated_fields.append('asset_type')
                          except ValueError:
                              raise ValueError(f"Invalid asset_type: {value}")
                  else:
                      setattr(asset, field, value)
                      updated_fields.append(field)
              
              await session.flush()
              
              results.append(FAAssetPatchResult(
                  asset_id=patch.asset_id,
                  success=True,
                  message=f"Asset patched successfully ({len(updated_fields)} fields)",
                  updated_fields=updated_fields
              ))
              
              logger.info(f"Asset patched: id={patch.asset_id}, fields={updated_fields}")
              
          except Exception as e:
              logger.error(f"Error patching asset {patch.asset_id}: {e}")
              results.append(FAAssetPatchResult(
                  asset_id=patch.asset_id,
                  success=False,
                  message=f"Error: {str(e)}",
                  updated_fields=None
              ))
      
      # Commit all successful patches
      await session.commit()
      
      success_count = sum(1 for r in results if r.success)
      failed_count = len(results) - success_count
      
      return FABulkAssetPatchResponse(
          results=results,
          success_count=success_count,
          failed_count=failed_count
      )
  ```
- Aggiornare import per includere FAAssetPatchItem, FABulkAssetPatchResponse

**Rationale**: Service layer implementa logica merge con detection di campi presenti via model_dump(exclude_unset=True), ottimizzazione JSON con exclude_none=True.

---

### ✅ 11. Aggiornare AssetSourceManager in asset_source.py - COMPLETATO

**File**: `backend/app/services/asset_source.py`

**Changes**:
- Rinominare `refresh_asset_metadata` in `refresh_assets_from_provider`
- Aggiungere parametro `fields: Optional[List[str]] = None` per selezione campi
- Implementare logica field selection:
  ```python
  @staticmethod
  async def refresh_assets_from_provider(
      asset_ids: List[int],
      fields: Optional[List[str]] = None,  # NEW: field selection
      session: AsyncSession,
  ) -> FABulkRefreshResponse:
      """
      Refresh asset data from assigned providers (bulk operation).
      
      EXPLICIT REFRESH (no auto-refresh during assignment).
      
      Field Selection:
      - If fields=None: Update ALL fields the provider can fetch
      - If fields specified: Update ONLY those fields (e.g., ['asset_type', 'classification_params.sector'])
      - Fields are keys from FAAssetPatchItem and subkeys
      - Fields obtained dynamically: set(FAAssetPatchItem.model_fields.keys()) - {'asset_id'}
      
      For each asset:
      1. Get provider assignment (identifier, identifier_type, provider_params)
      2. Call provider.fetch_asset_metadata() -> returns FAAssetPatchItem
      3. Filter FAAssetPatchItem based on 'fields' parameter (if specified)
      4. Call AssetCRUDService.patch_assets_bulk with filtered patches
      5. Calculate refreshed_fields, missing_data_fields, ignored_fields dynamically
      
      Field classification:
      - refreshed_fields: Fields actually updated (present in patch and provider returned them)
      - missing_data_fields: Fields requested but provider couldn't fetch
      - ignored_fields: Fields not requested (when fields filter is used)
      
      Returns:
          FABulkRefreshResponse with per-asset results including fields_detail
      """
  ```
  ```python
  @staticmethod
  async def refresh_assets_from_provider(
      asset_ids: List[int],
      session: AsyncSession,
  ) -> FABulkRefreshResponse:
      """
      Refresh asset data from assigned providers (bulk operation).
      
      For each asset:
      1. Get provider assignment (identifier, identifier_type, provider_params)
      2. Call provider.fetch_asset_metadata(identifier, identifier_type, provider_params)
      3. Receive dict with: asset_type, sector, short_description, geographic_area (optional)
      4. Create FAAssetPatchItem from dict
      5. Call AssetCRUDService.patch_assets_bulk
      6. Calculate refreshed_fields, missing_data_fields, ignored_fields dynamically
      
      Field classification:
      - refreshed_fields: Keys present in provider dict with non-None values
      - missing_data_fields: Keys in FAAssetPatchItem.model_fields but not in provider dict
      - ignored_fields: Always empty (future use: provider explicitly says "I don't support X")
      
      Args:
          asset_ids: List of asset IDs to refresh
          session: Database session
          
      Returns:
          FABulkRefreshResponse with per-asset results including fields_detail
      """
      from backend.app.schemas.assets import FAAssetPatchItem
      from backend.app.services.asset_crud import AssetCRUDService
      from backend.app.schemas.provider import FAProviderRefreshFieldsDetail
      
      results = []
      patches_to_apply = []
      asset_fields_map = {}  # Map asset_id -> fields_detail
      
      # Get all patchable fields from FAAssetPatchItem
      all_possible_fields = set(FAAssetPatchItem.model_fields.keys()) - {'asset_id'}
      
      for asset_id in asset_ids:
          try:
              # Get asset and assignment
              asset_stmt = select(Asset).where(Asset.id == asset_id)
              asset_result = await session.execute(asset_stmt)
              asset = asset_result.scalar_one_or_none()
              
              if not asset:
                  results.append(FAProviderAssignmentResult(
                      asset_id=asset_id,
                      success=False,
                      message=f"Asset {asset_id} not found",
                      fields_detail=None
                  ))
                  continue
              
              assignment_stmt = select(AssetProviderAssignment).where(
                  AssetProviderAssignment.asset_id == asset_id
              )
              assignment_result = await session.execute(assignment_stmt)
              assignment = assignment_result.scalar_one_or_none()
              
              if not assignment:
                  results.append(FAProviderAssignmentResult(
                      asset_id=asset_id,
                      success=False,
                      message=f"No provider assigned to asset {asset_id}",
                      fields_detail=None
                  ))
                  continue
              
              # Get provider instance
              provider = AssetProviderRegistry.get_provider_instance(assignment.provider_code)
              if not provider:
                  results.append(FAProviderAssignmentResult(
                      asset_id=asset_id,
                      success=False,
                      message=f"Provider {assignment.provider_code} not found",
                      fields_detail=None
                  ))
                  continue
              
              # Fetch metadata from provider
              provider_params = json.loads(assignment.provider_params) if assignment.provider_params else None
              metadata_dict = await provider.fetch_asset_metadata(
                  assignment.identifier,
                  assignment.identifier_type,
                  provider_params
              )
              
              if not metadata_dict:
                  results.append(FAProviderAssignmentResult(
                      asset_id=asset_id,
                      success=False,
                      message=f"Provider {assignment.provider_code} returned no metadata",
                      fields_detail=None
                  ))
                  continue
              
              # Build FAAssetPatchItem from metadata_dict
              patch_data = {'asset_id': asset_id}
              refreshed_fields = []
              
              # Map dict keys to FAAssetPatchItem fields
              if 'asset_type' in metadata_dict:
                  patch_data['asset_type'] = metadata_dict['asset_type']
                  refreshed_fields.append('asset_type')
              
              # Build classification_params if any classification fields present
              classification_fields = ['sector', 'short_description', 'geographic_area']
              classification_data = {}
              for field in classification_fields:
                  if field in metadata_dict and metadata_dict[field]:
                      classification_data[field] = metadata_dict[field]
                      refreshed_fields.append(field)
              
              if classification_data:
                  from backend.app.schemas.assets import FAClassificationParams
                  patch_data['classification_params'] = FAClassificationParams(**classification_data)
              
              # Calculate missing_data_fields
              provider_returned_fields = set(metadata_dict.keys())
              missing_data_fields = list(all_possible_fields - provider_returned_fields - {'active', 'currency', 'display_name'})
              
              # Create patch
              patch = FAAssetPatchItem(**patch_data)
              patches_to_apply.append(patch)
              
              # Store fields detail
              asset_fields_map[asset_id] = FAProviderRefreshFieldsDetail(
                  refreshed_fields=refreshed_fields,
                  missing_data_fields=missing_data_fields,
                  ignored_fields=[]  # Future use
              )
              
          except Exception as e:
              logger.error(f"Error preparing refresh for asset {asset_id}: {e}")
              results.append(FAProviderAssignmentResult(
                  asset_id=asset_id,
                  success=False,
                  message=f"Error: {str(e)}",
                  fields_detail=None
              ))
      
      # Apply all patches in bulk
      if patches_to_apply:
          patch_response = await AssetCRUDService.patch_assets_bulk(patches_to_apply, session)
          
          # Map patch results to refresh results with fields_detail
          for patch_result in patch_response.results:
              fields_detail = asset_fields_map.get(patch_result.asset_id)
              results.append(FAProviderAssignmentResult(
                  asset_id=patch_result.asset_id,
                  success=patch_result.success,
                  message=patch_result.message,
                  fields_detail=fields_detail
              ))
      
      success_count = sum(1 for r in results if r.success)
      failed_count = len(results) - success_count
      
      return FABulkRefreshResponse(
          results=results,
          success_count=success_count,
          failed_count=failed_count
      )
  ```
- Aggiornare `bulk_assign_providers` per gestire identifier e identifier_type:
  ```python
  @staticmethod
  async def bulk_assign_providers(
      assignments: List[FAProviderAssignmentItem],
      session: AsyncSession,
  ) -> list[FAProviderAssignmentResult]:
      """
      Bulk assign/update providers to assets (PRIMARY bulk method).
      
      Now includes identifier and identifier_type fields.
      """
      if not assignments:
          return []
      
      # ... existing validation ...
      
      # Bulk insert new assignments with identifier/identifier_type
      new_assignments = []
      for a in assignments:
          raw_params = a.provider_params
          if isinstance(raw_params, dict):
              params_to_store = json.dumps(raw_params)
          else:
              params_to_store = raw_params
          
          new_assignments.append(
              AssetProviderAssignment(
                  asset_id=a.asset_id,
                  provider_code=a.provider_code,
                  identifier=a.identifier,  # NEW
                  identifier_type=a.identifier_type,  # NEW
                  provider_params=params_to_store,
                  fetch_interval=a.fetch_interval,
                  last_fetch_at=None,
              )
          )
      
      # ... rest of existing logic ...
  ```
- Aggiornare tutte le fetch operations per passare identifier_type ai provider:
  ```python
  # In bulk_refresh_prices and similar methods
  current = await prov.get_current_value(
      assignment.identifier,
      assignment.identifier_type,  # NEW
      provider_params
  )
  
  hist_data = await prov.get_history_value(
      assignment.identifier,
      assignment.identifier_type,  # NEW
      provider_params,
      start,
      end
  )
  ```

**Rationale**: Service layer orchestration per refresh con calcolo dinamico dei field status, propagazione identifier_type a tutti i provider calls.

---

## 🧹 BEFORE STEP 12: Execute Schema Cleanup Plan

**⚠️ IMPORTANTE**: Prima di procedere con Step 12 (test updates), eseguire il piano di pulizia schema:

📄 **Vedere**: `05b_plan-datamodelProviderRefactoring.prompt.md`

**Motivo**: Durante la review del codice sono stati identificati:
- 16 classi wrapper inutili che contengono solo `List[...]`
- 5 classi che dovrebbero usare `DateRangeModel`
- 2 coppie di classi duplicate/simili da consolidare

Eseguendo la pulizia **prima** di aggiornare i test, si evita di dover modificare i test due volte.

**Contenuto del piano 05b**:
- Rimozione wrapper classes (FABulkAssignRequest, FXConvertRequest, etc.)
- Integrazione DateRangeModel in FXConversionRequest, FXDeleteItem, FARefreshItem
- Consolidamento FAPricePoint + FAUpsertItem
- Standardizzazione pattern response bulk operations con `BaseBulkResponse[TResult]`
- Aggiornamento endpoint per accettare `List[ItemType]` direttamente

Una volta completato il piano 05b, procedere con Step 12.

---

### 12. Adattare tutti i test - VEDERE PIANO UNIFICATO

**⚠️ IMPORTANTE**: I test vanno aggiornati DOPO aver completato sia il piano 05 che il piano 05b.

📄 **Piano Unificato Test**: `05c_plan-testUpdates.prompt.md`

**Perché un piano separato?**
- Evita di aggiornare i test due volte
- Consolida tutti i cambi necessari da piano 05 + 05b
- Fornisce checklist completa di validazione

**Contenuto piano test**:
- Step 1-10: Aggiornamenti per fixture, CRUD, provider, prices, FX, etc.
- Validazione wrapper classes removal
- Validazione DateRangeModel integration
- Validazione BaseBulkResponse structure
- Checklist finale di validazione

**Non procedere con Step 12** senza aver consultato il piano unificato test.

---

## Riepilogo Ordine Esecuzione

**File**: `backend/test_scripts/**/*.py`

**Changes per fixture e setup**:
- Eliminare setup di identifier/identifier_type in Asset fixtures:
  ```python
  # OLD
  asset = Asset(
      display_name="Apple Inc.",
      identifier="AAPL",
      identifier_type=IdentifierType.TICKER,
      currency="USD",
      valuation_model=ValuationModel.MARKET_PRICE
  )
  
  # NEW
  asset = Asset(
      display_name="Apple Inc.",
      currency="USD",
      asset_type=AssetType.STOCK
  )
  ```
- Creare provider_assignments con identifier e identifier_type:
  ```python
  assignment = AssetProviderAssignment(
      asset_id=asset.id,
      provider_code="yfinance",
      identifier="AAPL",
      identifier_type=IdentifierType.TICKER,
      provider_params=None,
      fetch_interval=1440
  )
  session.add(assignment)
  ```
- Validare display_name univoco nei test (catch IntegrityError se duplicati)

**Changes per test scheduled_investment**:
- Aggiornare _transaction_override per essere compatibile con nuova struttura:
  ```python
  provider_params = {
      "schedule": [
          {
              "start_date": "2025-01-01",
              "end_date": "2025-12-31",
              "annual_rate": "0.05",
              "compounding": "SIMPLE",
              "day_count": "ACT/365"
          }
      ],
      "late_interest": None,
      "_transaction_override": [
          {
              "type": "BUY",
              "quantity": 1,
              "price": "10000",
              "trade_date": "2025-01-01"
              # NO identifier, identifier_type, valuation_model, interest_schedule
          }
      ]
  }
  ```
- Aggiornare chiamate provider per passare identifier_type:
  ```python
  result = await provider.get_current_value(
      identifier="1",  # asset_id as string
      identifier_type=IdentifierType.UUID,
      provider_params=provider_params
  )
  ```

**Changes per test API PATCH /assets**:
- Creare test per merge logic:
  ```python
  async def test_patch_assets_merge_logic():
      # Test 1: Field present = update
      response = await client.patch("/api/v1/assets", json={
          "assets": [
              {
                  "asset_id": 1,
                  "display_name": "New Name",
                  "active": False
              }
          ]
      })
      assert response.json()["results"][0]["updated_fields"] == ["display_name", "active"]
      
      # Test 2: Field absent = ignore
      response = await client.patch("/api/v1/assets", json={
          "assets": [
              {
                  "asset_id": 1,
                  "display_name": "Another Name"
                  # currency, asset_type, etc. not present = kept unchanged
              }
          ]
      })
      
      # Test 3: classification_params = None = clear
      response = await client.patch("/api/v1/assets", json={
          "assets": [
              {
                  "asset_id": 1,
                  "classification_params": None
              }
          ]
      })
  ```

**Changes per test GET /provider/assignments**:
- Test WHERE IN query:
  ```python
  async def test_get_provider_assignments_bulk():
      response = await client.get(
          "/api/v1/assets/provider/assignments",
          params={"asset_ids": [1, 2, 3]}
      )
      assert len(response.json()["assignments"]) == 3
      for item in response.json()["assignments"]:
          assert "identifier" in item
          assert "identifier_type" in item
  ```

**Changes per test yahoo_finance**:
- Test che ritorna dict con asset_type:
  ```python
  async def test_yfinance_fetch_metadata():
      provider = YahooFinanceProvider()
      result = await provider.fetch_asset_metadata(
          "AAPL",
          IdentifierType.TICKER,
          None
      )
      assert isinstance(result, dict)
      assert "asset_type" in result
      assert result["asset_type"] in ["STOCK", "ETF", ...]
      assert "sector" in result or "short_description" in result
  ```
- Test validazione identifier_type:
  ```python
  async def test_yfinance_rejects_invalid_identifier_type():
      provider = YahooFinanceProvider()
      with pytest.raises(AssetSourceError) as exc:
          await provider.get_current_value(
              "AAPL",
              IdentifierType.UUID,  # Not supported by yfinance
              None
          )
      assert "only supports TICKER and ISIN" in str(exc.value)
  ```

**Rationale**: Test completo coverage per nuove funzionalità (PATCH merge, GET assignments, provider identifier_type validation, scheduled_investment con provider_params).

---

### 13. Cleanup e ricostruzione DB

**File**: `backend/data/`

**Actions**:
1. Eliminare manualmente:
   ```bash
   cd backend/data
   rm -f *.db *.db-journal *.db-shm *.db-wal
   ```

2. Verificare migration clean:
   ```bash
   cd backend
   alembic current
   # Should show: (no current revision) or empty
   ```

3. Applicare migration:
   ```bash
   alembic upgrade head
   ```

4. Verificare risultato:
   ```bash
   alembic current
   # Should show: 001_initial (head)
   ```

5. Test manuale creazione dati:
   ```python
   # Via Python shell o script
   from backend.app.db.session import get_session_generator
   from backend.app.db.models import Asset, AssetProviderAssignment, IdentifierType, AssetType
   
   async def test_new_schema():
       async for session in get_session_generator():
           # Create asset (no identifier/valuation_model/interest_schedule)
           asset = Asset(
               display_name="Test Asset",
               currency="USD",
               asset_type=AssetType.STOCK
           )
           session.add(asset)
           await session.flush()
           
           # Create provider assignment (with identifier/identifier_type)
           assignment = AssetProviderAssignment(
               asset_id=asset.id,
               provider_code="yfinance",
               identifier="AAPL",
               identifier_type=IdentifierType.TICKER,
               provider_params=None,
               fetch_interval=1440
           )
           session.add(assignment)
           await session.commit()
           
           print(f"✅ Created asset {asset.id} with provider assignment")
           break
   
   import asyncio
   asyncio.run(test_new_schema())
   ```

6. Eseguire test suite:
   ```bash
   python test_runner.py
   # or
   ./dev.sh test
   ```

**Rationale**: Cleanup completo e verifica manuale + automatica che nuovo schema funzioni correttamente.

---

## Summary

### What Changes

**Database Schema**:
- Asset: Removed `identifier`, `identifier_type`, `valuation_model`, `interest_schedule` → Added `UNIQUE(display_name)`
- AssetProviderAssignment: Added `identifier`, `identifier_type` fields
- Migration 001_initial: Modified CREATE TABLE statements

**Domain Model**:
- ValuationModel enum: Deleted completely
- Asset: Simplified to pure metadata container (name, type, classification, currency)
- AssetProviderAssignment: Now holds identification + pricing logic

**Provider Interface**:
- All methods now accept `identifier_type: IdentifierType` parameter
- ScheduledInvestmentProvider reads schedule from `provider_params`
- YahooFinanceProvider returns dict (not FAClassificationParams) with asset_type

**API Endpoints**:
- New: `PATCH /assets` - Bulk update with merge logic
- New: `GET /assets/provider/assignments` - Read assignments by asset_ids
- Renamed: `POST /metadata/refresh` → `POST /assets/provider/refresh`
- Removed: `PATCH /metadata` - Absorbed into PATCH /assets
- Updated: `POST /assets/provider` - Requires identifier/identifier_type

**Service Layer**:
- AssetCRUDService: New `patch_assets_bulk` method with merge logic
- AssetSourceManager: Renamed `refresh_asset_metadata` → `refresh_assets_from_provider`
- All provider calls propagate identifier_type

**Schemas**:
- New: FAAssetPatchItem, FABulkAssetPatchRequest/Response
- New: FAProviderAssignmentReadItem, FAProviderRefreshFieldsDetail
- Updated: FAProviderAssignmentItem includes identifier/identifier_type
- Updated: FAAssetCreateItem removed obsolete fields

### What Stays the Same

- Asset classification_params structure (FAClassificationParams with geo normalization)
- Provider registry and plugin system architecture
- Bulk operations with partial success pattern
- Transaction and cash movement models unchanged
- FX rates system unchanged
- Test infrastructure (pytest, test_runner.py, dev.sh)

### Migration Path

1. **Phase 1**: Models + Migration (Steps 1-3)
   - Modify models.py
   - Update 001_initial.py
   - Delete DBs and recreate with alembic

2. **Phase 2**: Provider Layer (Steps 4-6)
   - Update AssetSourceProvider interface
   - Modify ScheduledInvestmentProvider
   - Modify YahooFinanceProvider

3. **Phase 3**: Schemas (Steps 7-8)
   - Create FAAssetPatchItem and related schemas
   - Update FAProviderAssignmentItem

4. **Phase 4**: API + Services (Steps 9-11)
   - Add PATCH /assets endpoint
   - Add GET /provider/assignments endpoint
   - Rename refresh endpoint
   - Implement patch_assets_bulk service
   - Update refresh_assets_from_provider service

5. **Phase 5**: Tests + Verification (Steps 12-13)
   - Update all test fixtures
   - Add tests for new endpoints
   - Verify manual creation
   - Run full test suite

### Validation Checklist

- [ ] ValuationModel enum completely removed from codebase
- [ ] Asset table has UNIQUE constraint on display_name
- [ ] AssetProviderAssignment has identifier and identifier_type columns
- [ ] All provider methods accept identifier_type parameter
- [ ] ScheduledInvestmentProvider reads from provider_params (not Asset.interest_schedule)
- [ ] YahooFinanceProvider returns dict with asset_type
- [ ] PATCH /assets endpoint working with merge logic
- [ ] GET /provider/assignments returns identifier/identifier_type
- [ ] POST /provider/refresh returns field-level detail
- [ ] All tests passing with new structure
- [ ] Manual asset + assignment creation works
- [ ] No references to old fields in codebase (grep for identifier in Asset context)

### Risk Mitigation

**High Risk Areas**:
1. Database migration failure → **Mitigation**: Manual DB deletion + fresh alembic upgrade
2. Test failures due to missing fields → **Mitigation**: Update fixtures systematically
3. Provider calls missing identifier_type → **Mitigation**: Search codebase for provider method calls

**Rollback Strategy**:
- Keep git branch separate until all steps complete
- Tag commit before starting: `git tag pre-refactoring`
- If critical issues: `git reset --hard pre-refactoring`

**Verification Points**:
- After Step 3: Verify DB schema with SQLite browser
- After Step 6: Run provider tests in isolation
- After Step 11: Test full flow (create asset → assign provider → refresh → patch)
- After Step 12: Full test suite green

## Notes

- This is a breaking change for all existing data (pre-alpha acceptable)
- No backward compatibility code maintained
- All old field references must be removed
- Focus on clean, consistent architecture
- Documentation updated inline (docstrings)
- Future-proof for additional providers and asset types

