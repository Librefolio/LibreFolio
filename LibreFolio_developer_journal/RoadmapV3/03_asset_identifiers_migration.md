# Asset Identifiers Migration Plan

**Data:** 2026-01-06  
**Status:** ✅ COMPLETED

## Obiettivo

Aggiungere una colonna per ogni `IdentifierType` direttamente nella tabella `assets`:

- `identifier_isin` (ISIN - 12 chars)
- `identifier_ticker` (TICKER - 20 chars)
- `identifier_cusip` (CUSIP - 9 chars)
- `identifier_sedol` (SEDOL - 7 chars)
- `identifier_figi` (FIGI - 12 chars)
- `identifier_uuid` (UUID - 36 chars)
- `identifier_other` (OTHER - 100 chars)

Questo permette:

1. Ricerca diretta senza JOIN con `asset_provider_assignments`
2. Ogni asset può avere multipli identificatori (ISIN + TICKER + ...)
3. Test automatico: ogni enum `IdentifierType` ha la sua colonna

## Analisi Performance

### Colonne NULL in SQLite

- **Nessun impatto negativo**: SQLite non alloca spazio per colonne NULL
- Le colonne sono memorizzate in formato "record", non "column-store"
- Un campo NULL occupa solo 1 byte (type header)
- Query con indici funzionano efficientemente anche con molti NULL

### Conclusione

✅ Sicuro procedere con colonne opzionali

---

## Step-by-Step Implementation

### Phase 1: Database Schema (Migration)

**File:** `backend/alembic/versions/001_initial.py`

```python
# Aggiungere in assets table dopo display_name:
sa.Column("identifier_isin", sa.String(12), nullable=True, index=True),
sa.Column("identifier_ticker", sa.String(20), nullable=True, index=True),
sa.Column("identifier_cusip", sa.String(9), nullable=True),
sa.Column("identifier_sedol", sa.String(7), nullable=True),
sa.Column("identifier_figi", sa.String(12), nullable=True),
sa.Column("identifier_uuid", sa.String(36), nullable=True),
sa.Column("identifier_other", sa.String(100), nullable=True),
```

**Note:**

- Solo ISIN e TICKER hanno indici (più usati per ricerche)
- Nessun unique constraint (stesso ISIN può essere in più asset per errore utente)

### Phase 2: SQLModel/Pydantic Models

**File:** `backend/app/db/models.py`

```python
class Asset(SQLModel, table=True):
    # ...existing fields...

    # Identifier columns (one per IdentifierType enum value)
    identifier_isin: Optional[str] = Field(default=None, max_length=12, index=True)
    identifier_ticker: Optional[str] = Field(default=None, max_length=20, index=True)
    identifier_cusip: Optional[str] = Field(default=None, max_length=9)
    identifier_sedol: Optional[str] = Field(default=None, max_length=7)
    identifier_figi: Optional[str] = Field(default=None, max_length=12)
    identifier_uuid: Optional[str] = Field(default=None, max_length=36)
    identifier_other: Optional[str] = Field(default=None, max_length=100)

    @field_validator('identifier_isin', mode='before')
    @classmethod
    def validate_isin(cls, v):
        if v is None or v == '':
            return None
        v = v.strip().upper()
        if len(v) != 12:
            raise ValueError("ISIN must be 12 characters")
        return v

    @field_validator('identifier_ticker', mode='before')
    @classmethod
    def validate_ticker(cls, v):
        if v is None or v == '':
            return None
        return v.strip().upper()
```

### Phase 3: Schema Updates

**File:** `backend/app/schemas/assets.py`

```python
class FACreateItem(BaseModel):
    # ...existing fields...
    identifier_isin: Optional[str] = None
    identifier_ticker: Optional[str] = None
    identifier_cusip: Optional[str] = None
    identifier_sedol: Optional[str] = None
    identifier_figi: Optional[str] = None
    identifier_uuid: Optional[str] = None
    identifier_other: Optional[str] = None


class FAUpdateItem(BaseModel):
    # ...existing fields...
    identifier_isin: Optional[str] = None
    identifier_ticker: Optional[str] = None
    # ... etc


class FAinfoResponse(BaseModel):
    # ...existing fields...
    identifier_isin: Optional[str] = None
    identifier_ticker: Optional[str] = None
    # ... etc


class FAAinfoFiltersRequest(BaseModel):
    # MODIFY to search directly on Asset:
    isin: Optional[str] = None  # Search Asset.identifier_isin
    symbol: Optional[str] = None  # Search Asset.identifier_ticker
```

### Phase 4: Service Layer Updates

**File:** `backend/app/services/asset_source.py`

```python
@staticmethod
async def list_assets(filters, session) -> List[FAinfoResponse]:
    # SIMPLIFIED: Search directly on Asset table
    stmt = select(Asset)

    conditions = []

    if filters.isin:
        conditions.append(Asset.identifier_isin == filters.isin.upper())

    if filters.symbol:
        conditions.append(Asset.identifier_ticker == filters.symbol.upper())

    # ...rest of query...
```

### Phase 5: BRIM Plugin Updates

**File:** `backend/app/services/brim_provider.py`

```python
async def search_asset_candidates(session, extracted_symbol, extracted_isin, extracted_name):
    """
    SIMPLIFIED: Search directly on Asset table.
    """
    # Priority 1: ISIN exact match (EXACT confidence)
    if extracted_isin:
        results = await AssetCRUDService.list_assets(
            filters=FAAinfoFiltersRequest(isin=extracted_isin),
            session=session
            )

    # Priority 2: Symbol exact match (MEDIUM confidence)
    if extracted_symbol and not candidates:
        results = await AssetCRUDService.list_assets(
            filters=FAAinfoFiltersRequest(symbol=extracted_symbol),
            session=session
            )
```

### Phase 6: Test - IdentifierType ↔ Schema Sync Validation

**File:** `backend/test_scripts/test_db/db_schema_validate.py`

This test automatically validates that ALL dependent schemas are in sync with IdentifierType:

```python
def test_identifier_columns_match_enum():
    """
    Verify every IdentifierType enum has corresponding fields in ALL dependent schemas.
    
    Checks 35 field mappings across:
    - Asset model columns (7)
    - FAAssetCreateItem fields (7)
    - FAAssetPatchItem fields (7)
    - FAinfoResponse fields (7)
    - FAAinfoFiltersRequest filter fields (7)
    
    If this test fails, see IdentifierType docstring in models.py for full update checklist.
    """
```

**Run validation:**

```bash
pytest backend/test_scripts/test_db/db_schema_validate.py::test_identifier_columns_match_enum -v -s
```

**Auto-detection:** If you add a new IdentifierType value without updating schemas, this test will FAIL automatically with a clear message showing which fields are missing.

---

## Files to Modify

| File                                                 | Changes                                                                           |
|------------------------------------------------------|-----------------------------------------------------------------------------------|
| `backend/alembic/versions/001_initial.py`            | Add 7 identifier columns                                                          |
| `backend/app/db/models.py`                           | Add 7 fields + validators + IdentifierType docstring                              |
| `backend/app/schemas/assets.py`                      | Update FAAssetCreateItem, FAAssetPatchItem, FAinfoResponse, FAAinfoFiltersRequest |
| `backend/app/services/asset_source.py`               | Simplify list_assets to query Asset directly                                      |
| `backend/app/services/brim_provider.py`              | Update search_asset_candidates                                                    |
| `backend/app/api/v1/assets.py`                       | Ensure endpoints pass/return identifiers                                          |
| `backend/test_scripts/test_db/db_schema_validate.py` | Add comprehensive enum↔schema test                                                |
| `backend/test_scripts/test_services/test_brim_db.py` | Update fixtures                                                                   |

---

## Adding a New IdentifierType

When adding a new value to IdentifierType (e.g., `WKN = "WKN"`):

1. **Run the validation test first** - it will show exactly what's missing
2. **Follow the checklist** in IdentifierType docstring (models.py)
3. **Run test again** to confirm all 35+ checks pass

---

## Pre-Implementation Cleanup

```bash
# Delete existing databases before recreating with new schema
rm -f backend/data/sqlite/app.db
rm -f backend/data/sqlite/test_app.db
```

---

## Effort Estimate

| Phase        | Effort     | Risk   |
|--------------|------------|--------|
| 1. Migration | 15 min     | Low    |
| 2. Models    | 15 min     | Low    |
| 3. Schemas   | 20 min     | Low    |
| 4. Services  | 20 min     | Medium |
| 5. BRIM      | 10 min     | Low    |
| 6. Tests     | 15 min     | Low    |
| DB Cleanup   | 5 min      | Low    |
| **Total**    | ~1.5 hours | Low    |

