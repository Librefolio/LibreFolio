# API Development Guide - LibreFolio

**Version**: 2.1
**Last Updated**: November 18, 2025
**Target Audience**: Developers contributing to LibreFolio

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Creating a New API Endpoint](#creating-a-new-api-endpoint)
4. [Bulk-First Design Pattern](#bulk-first-design-pattern)
5. [Request/Response Models](#requestresponse-models)
6. [Service Layer](#service-layer)
7. [Testing](#testing)
8. [Documentation](#documentation)
9. [Best Practices](#best-practices)
10. [Complete Example](#complete-example)

---

## 🎯 Overview

LibreFolio uses **FastAPI** for REST API endpoints with the following stack:

- **Framework**: FastAPI (async)
- **Validation**: Pydantic v2
- **Database**: SQLite (async via aiosqlite)
- **ORM**: SQLModel (SQLAlchemy 2.x)
- **Pattern**: 3-layer architecture (API → Service → Database)

**Key Principles**:

- ✅ **Bulk-first**: Where multiple items can be processed, prefer bulk endpoints
- ✅ **Async**: All endpoints and database operations are async
- ✅ **Validation**: Comprehensive Pydantic models for request/response
- ✅ **Type hints**: Full typing for better IDE support and maintainability
- ✅ **Testing**: Every endpoint must have comprehensive tests

---

## 🏗️ Architecture

### Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── fx.py              # FX endpoints (example)
│   │       ├── your_module.py     # Your new endpoints
│   │       └── router.py          # Main router aggregation
│   ├── db/
│   │   ├── models.py              # SQLModel database models
│   │   └── session.py             # Database session management
│   └── services/
│       ├── fx.py                  # FX business logic (example)
│       └── your_service.py        # Your business logic
└── test_scripts/
    └── test_api/
        └── test_your_api.py       # API tests
```

### 3-Layer Architecture

```
┌─────────────────────────────────────────┐
│  API Layer (FastAPI Endpoints)         │  ← Request validation, response formatting
│  Location: backend/app/api/v1/         │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Service Layer (Business Logic)        │  ← Core logic, calculations
│  Location: backend/app/services/       │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Database Layer (SQLModel/SQLAlchemy)  │  ← Data persistence
│  Location: backend/app/db/             │
└─────────────────────────────────────────┘
```

---

## 🆕 Creating a New API Endpoint

### Step 1: Define Database Models (if needed)

If your endpoint needs new database tables:

**File**: `backend/app/db/models.py`

```python
from sqlmodel import Field, SQLModel
from datetime import datetime
from typing import Optional
from decimal import Decimal
from sqlalchemy import Column, Numeric


class YourModel(SQLModel, table=True):
    """
    Brief description of what this model represents. 
    
    Usage: Explain when/how this is used
    """
    __tablename__ = "your_table"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, index=True)
    value: Decimal = Field(sa_column=Column(Numeric(18, 6)))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

> **📚 Technical Note - SQLModel**:
>
> **What is SQLModel?**
> SQLModel combines Pydantic (data validation) with SQLAlchemy (ORM) in a single class.
>
> **Value Added**:
> - ✅ **Type safety**: Python type hints become database column types automatically
> - ✅ **Data validation**: Pydantic validates data before inserting to database
> - ✅ **IDE support**: Full autocomplete for table columns
> - ✅ **Single source of truth**: One model for both API validation and database schema
> - ✅ **Async support**: Works with SQLAlchemy 2.x async engine
>
> **How it works**:
> ```python
> # The same class definition:
> class YourModel(SQLModel, table=True):
>     name: str = Field(nullable=False)
>
> # Creates database table:
> CREATE TABLE your_table (
>     name VARCHAR NOT NULL
> )
>
> # AND provides Python validation:
> model = YourModel(name="test")  # ✅ OK
> model = YourModel(name=None)    # ❌ ValidationError
> ```
>
> **When a field changes**:
> - Python code: Update type hint
> - Database: Run Alembic migration (auto-generated from model changes)
> - API validation: Automatically updated (same model)

---

### Step 2: Create Service Layer

**File**: `backend/app/services/your_service.py`

```python
"""
Your Service Module
Brief description of what this service does.
"""
import logging
from datetime import date
from decimal import Decimal
from sqlmodel import select
from backend.app.db.models import YourModel

logger = logging.getLogger(__name__)


class YourServiceError(Exception):
    """Base exception for your service errors."""
    pass


async def your_bulk_function(
        session,  # AsyncSession
        items: list[tuple[...]]  # Input data as tuples
        ) -> tuple[list[...], list[str]]:
    """
    Process multiple items in a single batch operation. 
    
    This is the MAIN implementation - single items should call this with 1 element.
    
    Args:
        session: Database session
        items: List of input data tuples
    
    Returns:
        Tuple of (results, errors) where:
        - results: List of processed results (or None for failed items)
        - errors: List of error messages for failed items
    
    Raises:
        YourServiceError: If operation fails
    """
    if not items:
        return ([], [])

    results = []
    errors = []

    # OPTIMIZATION: Batch database queries where possible
    # Example: Single query for all items instead of N queries

    for idx, item in enumerate(items):
        try:
            # Process item
            result = await process_item(session, item)
            results.append(result)
        except Exception as e:
            errors.append(f"Item {idx}: {str(e)}")
            results.append(None)

    return (results, errors)


async def your_single_function(
        session,  # AsyncSession
        item_data: ...
        ) -> ...:
    """
    Convenience wrapper for single item processing. 
    Calls your_bulk_function() with 1 element.
    
    Args:
        session: Database session
        item_data: Single item data
    
    Returns:
        Processed result
    
    Raises:
        YourServiceError: If operation fails
    """
    results, errors = await your_bulk_function(session, [item_data])

    if errors:
        raise YourServiceError(errors[0])

    return results[0]
```

> **📚 Technical Note - Async/Await Pattern**:
>
> **What is async/await?**
> Python's built-in concurrency model for I/O-bound operations (database, network calls).
>
> **Value Added**:
> - ✅ **Non-blocking I/O**: While waiting for database response, server can handle other requests
> - ✅ **High throughput**: Single Python process can handle 1000+ concurrent requests
> - ✅ **Resource efficient**: No need for thread-per-request (lighter than threading)
> - ✅ **Native database support**: SQLAlchemy 2.x, aiosqlite are fully async
>
> **How it works**:
> ```python
> # ❌ Synchronous (blocks entire server during DB query):
> def get_data():
>     result = session.execute(query)  # Server frozen for 100ms
>     return result
>
> # ✅ Asynchronous (server handles other requests while waiting):
> async def get_data():
>     result = await session.execute(query)  # Server free during wait
>     return result
>
> # During 100ms DB query time:
> # Sync: 0 other requests handled
> # Async: 10+ other requests can be processed
> ```
>
> **Why service layer?**
> - **Separation of concerns**: Business logic separate from HTTP/API concerns
> - **Reusability**: Same function used by API endpoint, CLI tools, background jobs
> - **Testability**: Test business logic without HTTP server
> - **Maintainability**: Changes to logic don't affect API contract
>
> **Learn more**: See [async-architecture.md](../architecture/async.md) for detailed guide on async patterns in LibreFolio

---

### Step 3: Create Pydantic Models

**File**: `backend/app/api/v1/your_module.py`

```python
"""
Your API Module
REST API endpoints for your feature.
"""
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_session_generator
from backend.app.services.your_service import (
    YourServiceError,
    your_bulk_function,
    )

router = APIRouter(prefix="/your-prefix", tags=["YourFeature"])


# ============================================================================ 
# REQUEST MODELS
# ============================================================================ 

class YourItemRequest(BaseModel):
    """
    Single item in bulk request. 
    
    Example:
        {
            "field1": "value1",
            "field2": 123.45
        }
    """
    field1: str = Field(..., min_length=1, max_length=100, description="Description of field1")
    field2: Decimal = Field(..., gt=0, description="Description of field2 (must be positive)")
    optional_field: str | None = Field(None, description="Optional field description")

    class Config:
        # Allow using both field name and alias
        populate_by_name = True


class YourBulkRequest(BaseModel):
    """
    Bulk request for processing multiple items. 
    
    Example:
        {
            "items": [
                {"field1": "value1", "field2": 123.45},
                {"field1": "value2", "field2": 678.90}
            ]
        }
    """
    items: list[YourItemRequest] = Field(
        ...,
        min_length=1,
        description="List of items to process (minimum 1)"
        )


# ============================================================================ 
# RESPONSE MODELS
# ============================================================================ 

class YourItemResult(BaseModel):
    """
    Single item result. 
    
    Example:
        {
            "success": true,
            "processed_value": 246.90,
            "message": "Item processed successfully"
        }
    """
    success: bool = Field(..., description="Whether operation succeeded")
    processed_value: Decimal = Field(..., description="Processed result value")
    message: str = Field(..., description="Status message")


class YourBulkResponse(BaseModel):
    """
    Bulk response with results and errors. 
    
    Example:
        {
            "results": [
                {"success": true, "processed_value": 246.90, "message": "OK"},
                {"success": true, "processed_value": 1357.80, "message": "OK"}
            ],
            "success_count": 2,
            "errors": []
        }
    """
    results: list[YourItemResult] = Field(..., description="Results for each item (in order)")
    success_count: int = Field(..., description="Number of successful operations")
    errors: list[str] = Field(default_factory=list, description="Error messages (if any)")


# ============================================================================ 
# ENDPOINTS
# ============================================================================ 

@router.post("/process", response_model=YourBulkResponse, status_code=200)
async def process_items_bulk(
        request: YourBulkRequest,
        session: AsyncSession = Depends(get_session_generator)
        ):
    """
    Process one or more items (bulk operation). 
    
    This endpoint accepts a list of items to process. Even single items
    should be sent as a list with one element.
    
    **Request Body**:
    ```json
    {
        "items": [
            {"field1": "value1", "field2": 123.45},
            {"field1": "value2", "field2": 678.90}
        ]
    }
    ```
    
    **Response** (success):
    ```json
    {
        "results": [
            {"success": true, "processed_value": 246.90, "message": "OK"},
            {"success": true, "processed_value": 1357.80, "message": "OK"}
        ],
        "success_count": 2,
        "errors": []
    }
    ```
    
    **Response** (partial failure):
    ```json
    {
        "results": [
            {"success": true, "processed_value": 246.90, "message": "OK"}
        ],
        "success_count": 1,
        "errors": ["Item 1: Invalid data"]
    }
    ```
    
    **Error Handling**:
    - Returns 200 with partial results if some items succeed
    - Returns 400/404 if all items fail
    - Returns 422 for validation errors
    
    Args:
        request: Bulk request with list of items
        session: Database session (injected)
    
    Returns:
        Bulk response with results and errors
    """
    # Prepare input for service layer
    service_input = [
        (item.field1, item.field2, item.optional_field)
        for item in request.items
        ]

    # Call bulk service function
    try:
        service_results, service_errors = await your_bulk_function(
            session,
            service_input
            )
    except YourServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Format response
    results = []
    for idx, result in enumerate(service_results):
        if result is not None:
            results.append(YourItemResult(
                success=True,
                processed_value=result,
                message="Item processed successfully"
                ))

    # If all failed, return error
    if service_errors and not results:
        raise HTTPException(
            status_code=400,
            detail=f"All items failed: {'; '.join(service_errors)}"
            )

    return YourBulkResponse(
        results=results,
        success_count=len(results),
        errors=service_errors
        )


@router.get("/items", response_model=list[YourItemResult])
async def list_items(
        limit: int = Query(100, ge=1, le=1000, description="Maximum items to return"),
        offset: int = Query(0, ge=0, description="Offset for pagination"),
        session: AsyncSession = Depends(get_session_generator)
        ):
    """
    List items with pagination. 
    
    **Query Parameters**:
    - `limit`: Maximum items to return (1-1000, default 100)
    - `offset`: Offset for pagination (default 0)
    
    **Example Request**:
    ```
    GET /api/v1/your-prefix/items?limit=50&offset=0
    ```
    
    **Example Response**:
    ```json
    [
        {"success": true, "processed_value": 123.45, "message": "OK"},
        {"success": true, "processed_value": 678.90, "message": "OK"}
    ]
    ```
    
    Args:
        limit: Maximum items to return
        offset: Pagination offset
        session: Database session (injected)
    
    Returns:
        List of items
    """
    from backend.app.db.models import YourModel
    from sqlmodel import select

    stmt = select(YourModel).offset(offset).limit(limit)
    result = await session.execute(stmt)
    items = result.scalars().all()

    return [
        YourItemResult(
            success=True,
            processed_value=item.value,
            message=item.name
            )
        for item in items
        ]
```

> **📚 Technical Note - Pydantic v2**:
>
> **What is Pydantic?**
> Data validation library using Python type hints. LibreFolio uses **Pydantic v2** (rewritten in Rust for performance).
>
> **Value Added**:
> - ✅ **Automatic validation**: Type hints = runtime validation (no manual checks)
> - ✅ **Performance**: V2 is ~10x faster than v1 (Rust core)
> - ✅ **Error messages**: Clear, user-friendly validation errors
> - ✅ **JSON serialization**: Automatic conversion Python ↔ JSON
> - ✅ **OpenAPI generation**: FastAPI uses Pydantic models to generate Swagger docs
> - ✅ **IDE support**: Autocomplete, type checking at development time
>
> **How it works**:
> ```python
> # Define model with type hints:
> class Request(BaseModel):
>     amount: Decimal = Field(..., gt=0)
>     currency: str = Field(..., min_length=3, max_length=3)
>
> # Pydantic automatically validates:
> Request(amount=100, currency="USD")     # ✅ OK
> Request(amount=-100, currency="USD")    # ❌ ValidationError: amount must be > 0
> Request(amount=100, currency="US")      # ❌ ValidationError: currency min_length=3
> Request(amount="not_a_number", ...)     # ❌ ValidationError: not a valid decimal
>
> # FastAPI does this automatically for every request:
> @router.post("/endpoint")
> async def endpoint(request: Request):  # ← Validation happens here
>     # If we reach this point, data is already validated!
>     # No need for: if amount <= 0: raise ...
> ```
>
> **Benefits for API development**:
> 1. **No manual validation**: Type hints do the work
> 2. **Consistent errors**: 422 status with detailed field-level errors
> 3. **Self-documenting**: Field descriptions appear in Swagger UI
> 4. **Type safety**: IDE warns if you use wrong types
>
> **Example error response** (automatic):
> ```json
> {
>   "detail": [
>     {
>       "type": "greater_than",
>       "loc": ["body", "amount"],
>       "msg": "Input should be greater than 0",
>       "input": -100
>     }
>   ]
> }
> ```

---

### Step 4: Register Router

**File**: `backend/app/api/v1/router.py`

```python
from fastapi import APIRouter
from backend.app.api.v1 import fx, your_module  # Add your module

router = APIRouter()

# Include sub-routers
router.include_router(fx.fx_router)
router.include_router(your_module.asset_router)  # Add this line
```

> **📚 Technical Note - FastAPI Router & Dependency Injection**:
>
> **What is APIRouter?**
> FastAPI's modular routing system to organize endpoints by feature/domain.
>
> **Value Added**:
> - ✅ **Modularity**: Each feature (fx, portfolio, assets) has its own file
> - ✅ **Prefix management**: `/fx` prefix applied to all routes in fx.py
> - ✅ **Tag grouping**: Automatic Swagger UI grouping by feature
> - ✅ **Maintainability**: Add/remove features without touching main router
>
> **How router registration works**:
> ```python
> # In backend/app/api/v1/fx.py:
> router = APIRouter(prefix="/fx", tags=["FX"])
>
> @router.post("/convert")  # Actual path: /api/v1/fx/convert/bulk
> async def convert(): pass
>
> # In backend/app/api/v1/router.py:
> router = APIRouter()
> router.include_router(fx.asset_router)  # All fx.py routes now included
>
> # In backend/app/main.py:
> app.include_router(router, prefix="/api/v1")  # Final path prefix
>
> # Result: POST /api/v1/fx/convert/bulk
> ```
>
> **Dependency Injection (`Depends`)**:
> ```python
> # FastAPI automatically injects dependencies:
> @router.post("/endpoint")
> async def endpoint(
>     request: YourRequest,                        # ← Parsed from JSON body
>     session: AsyncSession = Depends(get_session) # ← Created automatically
> ):
>     # session is ready to use - no manual creation!
>     result = await session.execute(stmt)
>
> # get_session() is called automatically by FastAPI:
> async def get_session():
>     async with AsyncSession(engine) as session:
>         yield session  # Provided to endpoint
>         # Automatically closed after endpoint finishes
> ```
>
> **Benefits**:
> - Database session automatically created and closed
> - No connection leaks (guaranteed cleanup)
> - Easy to mock in tests
> - Reusable across all endpoints

---

## 🚀 Bulk-First Design Pattern

### Why Bulk-First?

**Performance**: Portfolio with 100 assets

- ❌ **Without bulk**: 100 API calls = 100 requests + 100 DB queries
- ✅ **With bulk**: 1 API call = 1 request + 1-2 DB queries

**Benefits**:

1. **Network efficiency**: Fewer round-trips
2. **Database efficiency**: Batch queries reduce load
3. **Transactional consistency**: All-or-nothing operations
4. **Partial failure support**: Continue processing on errors

### When to Use Bulk

✅ **Use bulk when**:

- Processing multiple similar items (conversions, upserts, calculations)
- Portfolio operations (valuation, rebalancing)
- Data imports (CSV, API sync)
- Batch updates

❌ **Don't use bulk for**:

- Single entity operations (GET /user/:id)
- Unrelated operations
- Simple lookups

### Bulk Design Pattern

```python
# ✅ CORRECT: Bulk-first with single as special case

async def process_bulk(items: list[...]) -> tuple[list[...], list[str]]:
    """Main implementation - handles N items."""
    # Batch database queries
    # Process all items
    # Return (results, errors)
    pass


async def process_single(item: ...) -> ...:
    """Convenience wrapper - calls bulk with 1 item."""
    results, errors = await process_bulk([item])
    if errors:
        raise Exception(errors[0])
    return results[0]


# API endpoint uses bulk function directly
@router.post("/process")
async def process_endpoint(request: BulkRequest):
    results, errors = await process_bulk(request.items)
    return BulkResponse(results=results, errors=errors)
```

### Partial Failure Handling

```python
# Service layer returns (results, errors)
results, errors = await your_bulk_function(session, items)

# API layer decides what to do
if errors and not results:
    # All failed
    raise HTTPException(status_code=400, detail="All items failed")
elif errors:
    # Partial failure - return 200 with both results and errors
    return BulkResponse(
        results=results,
        success_count=len(results),
        errors=errors  # Client can see what failed
        )
else:
    # All succeeded
    return BulkResponse(results=results, success_count=len(results), errors=[])
```

---

## 📝 Request/Response Models

### Pydantic Best Practices

#### 1. Field Validation

```python
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal


class YourRequest(BaseModel):
    # Basic validation
    amount: Decimal = Field(..., gt=0, description="Amount (must be positive)")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO 4217 currency code")

    # Custom validation
    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        v = v.upper()
        if v not in VALID_CURRENCIES:
            raise ValueError(f"Invalid currency: {v}")
        return v
```

#### 2. Field Aliases

```python
class YourRequest(BaseModel):
    # Use alias for different JSON key name
    conversion_date: date = Field(..., alias="date", description="Date for operation")

    class Config:
        populate_by_name = True  # Allow both 'date' and 'conversion_date'
```

#### 3. Optional Fields

```python
class YourRequest(BaseModel):
    required_field: str = Field(..., description="This field is required")
    optional_field: str | None = Field(None, description="This field is optional")
    field_with_default: int = Field(100, description="Has default value")
```

#### 4. Nested Models

```python
class Address(BaseModel):
    street: str
    city: str


class Person(BaseModel):
    name: str
    address: Address  # Nested model
    emails: list[str]  # List of strings
```

### Schema Organization (Since v2.1 Refactoring)

**Important**: Since November 2025 (v2.1), all Pydantic schema definitions have been moved to dedicated modules under `backend/app/schemas/`. **No inline BaseModel definitions are
allowed in `api/v1/*.py` files.**

#### Schema Module Structure

```
backend/app/schemas/
├── __init__.py          # Central exports (32+ classes)
├── common.py            # Shared: BackwardFillInfo, DateRangeModel
├── assets.py            # FA core: PricePointModel, CurrentValueModel, ScheduledInvestment*
├── provider.py          # Provider assignment (FA + FX)
├── prices.py            # FA price operations (upsert, delete, query)
├── refresh.py           # FA refresh + FX sync (operational workflows)
└── fx.py                # FX specific: conversion, upsert, delete, pair sources
```

#### Naming Conventions

**FA Prefix** (Financial Assets):

- Domain: Stocks, ETFs, bonds, P2P loans, etc.
- Examples: `FAUpsertItem`, `FABulkRefreshRequest`, `FAProviderInfo`

**FX Prefix** (Foreign Exchange):

- Domain: Currency rates from central banks (ECB, FED, BOE, SNB)
- Examples: `FXUpsertItem`, `FXSyncResponse`, `FXProviderInfo`

**No Prefix**:

- Common/shared models: `BackwardFillInfo`, `DateRangeModel`
- Core FA models: `PricePointModel`, `CurrentValueModel` (foundational, no prefix needed)

#### Import Pattern

```python
# In api/v1/your_endpoint.py

# Option 1: Import from specific module
from backend.app.schemas.prices import FAUpsertItem, FABulkUpsertRequest
from backend.app.schemas.refresh import FABulkRefreshResponse

# Option 2: Import from package __init__ (recommended for common schemas)
from backend.app.schemas import PricePointModel, BackwardFillInfo
```

#### FA vs FX Schema Comparison

The FA and FX systems have similar operational needs (upsert, delete, sync/refresh) but different data complexity, resulting in different schema structures:

| Aspect               | FA (Financial Assets)                               | FX (Foreign Exchange)                    | Reason for Difference                                                            |
|----------------------|-----------------------------------------------------|------------------------------------------|----------------------------------------------------------------------------------|
| **Nesting Levels**   | 3-level (Item → Asset → Bulk)                       | 2-level (Item → Bulk)                    | FA groups multiple price points per asset, FX rates are simpler (pair-date-rate) |
| **Upsert Structure** | `FAUpsertItem` → `FAUpsert` → `FABulkUpsertRequest` | `FXUpsertItem` → `FXBulkUpsertRequest`   | FA needs intermediate grouping by asset_id                                       |
| **Data Complexity**  | OHLC + volume + currency per point                  | Base + quote + rate                      | FA tracks intraday data, FX only closing rates                                   |
| **Delete Structure** | Asset + multiple DateRanges                         | Direct pair + DateRange                  | FA allows deleting multiple ranges per asset in one call                         |
| **Refresh/Sync**     | Asset-by-asset refresh (provider per asset)         | Date range sync (provider for all pairs) | FA has heterogeneous assets, FX is uniform currency pairs                        |

**Example - Upsert Structure Comparison**:

```python
# FA: 3 levels (Item → Asset → Bulk)
FABulkUpsertRequest(
    assets=[
        FAUpsert(
            asset_id=1,
            prices=[
                FAUpsertItem(date="2025-01-01", close=100.50, volume=1000),
                FAUpsertItem(date="2025-01-02", close=101.25, volume=1500),
                ]
            ),
        FAUpsert(
            asset_id=2,
            prices=[...]
            )
        ]
    )

# FX: 2 levels (Item → Bulk)
FXBulkUpsertRequest(
    rates=[
        FXUpsertItem(date="2025-01-01", base="EUR", quote="USD", rate=1.08),
        FXUpsertItem(date="2025-01-02", base="EUR", quote="USD", rate=1.09),
        FXUpsertItem(date="2025-01-01", base="EUR", quote="GBP", rate=0.85),
        ]
    )
```

**Why This Matters**:

- When creating FA endpoints: Group data by asset_id first, then by dates
- When creating FX endpoints: Direct flat structure, no intermediate grouping
- Don't mix patterns: FA always 3-level, FX always 2-level for consistency

#### Docstring Requirements

Every schema file must include a comprehensive docstring covering:

1. **Purpose**: What domain/operations does this file cover?
2. **Naming conventions**: FA/FX prefix usage
3. **Design notes**: Structural differences, no backward compatibility
4. **Domain coverage**: Specific operations included

**Example** (from `refresh.py`):

```python
"""
Refresh & Sync Operation Schemas (FA + FX).

**Naming Conventions**:
- FA prefix: Financial Assets refresh operations
- FX prefix: Foreign Exchange sync operations

**Domain Coverage**:
- FA Refresh: Fetch and store asset prices from providers
- FX Sync: Fetch and store FX rates from central banks

**Design Notes**:
- Consolidation rationale: Both operations perform similar workflows
- Kept separate sections (FA Refresh / FX Sync) for semantic clarity
- No backward compatibility maintained during refactoring

**Structure Differences**:
- FA Refresh: 3-level (Item → Bulk → Result per asset)
- FX Sync: 2-level (Request with params → Response with summary)
"""
```

#### Schema Consolidation Notes

**refresh.py Consolidation** (November 2025):

- Previously: FA refresh in `assets.py` endpoints, FX sync in `fx.py` schemas
- Now: Both consolidated in `refresh.py` under separate sections
- Rationale: Both are "fetch-and-store" operational workflows
- Benefit: Single location for all data refresh operations

**common.py Reusability**:

- `DateRangeModel`: Used in both FA delete and FX operations
- `BackwardFillInfo`: Used in both FA prices and FX conversion responses
- Future validators (e.g., `end >= start`) can be centralized here

---

## 🔧 Service Layer

### Service Layer Responsibilities

- ✅ **Business logic**: Calculations, validations, transformations
- ✅ **Database queries**: Batch queries, transactions
- ✅ **Error handling**: Custom exceptions, error messages
- ❌ **NOT**: HTTP concerns (status codes, headers)

### Optimization: Batch Queries

```python
# ❌ BAD: N queries
async def process_items_slow(session, items):
    results = []
    for item in items:
        stmt = select(Model).where(Model.id == item.id)  # Separate query per item
        result = await session.execute(stmt)
        results.append(result.scalars().first())
    return results


# ✅ GOOD: 1 batch query
async def process_items_fast(session, items):
    # Collect all IDs
    ids = [item.id for item in items]

    # Single query with OR/IN condition
    stmt = select(Model).where(Model.id.in_(ids))
    result = await session.execute(stmt)
    all_models = result.scalars().all()

    # Build lookup dictionary
    model_lookup = {model.id: model for model in all_models}

    # Process using in-memory lookup (no DB access)
    results = [model_lookup.get(item.id) for item in items]
    return results
```

### Batch INSERT/UPDATE

```python
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy import func


async def upsert_bulk(session, items):
    """Batch UPSERT - single INSERT statement for all items."""

    # Prepare all values
    values_list = [
        {
            'field1': item.field1,
            'field2': item.field2,
            'updated_at': func.current_timestamp()
            }
        for item in items
        ]

    # Single batch INSERT
    batch_stmt = insert(YourModel).values(values_list)

    # On conflict: update
    batch_stmt = batch_stmt.on_conflict_do_update(
        index_elements=['field1'],
        set_={
            'field2': batch_stmt.excluded.field2,
            'updated_at': func.current_timestamp()
            }
        )

    # Execute once for all items
    await session.execute(batch_stmt)
    await session.commit()
```

---

## 🧪 Testing

### Test Structure

**File**: `backend/test_scripts/test_api/test_your_api.py`

```python
"""
Test Your API Endpoints
Tests REST API endpoints for your feature.
"""
import sys
from pathlib import Path
import httpx

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from backend.test_scripts.test_server_helper import _TestingServerManager, TEST_API_BASE_URL
from backend.test_scripts.test_utils import (
    print_error, print_info, print_section, print_success,
    print_test_header, print_test_summary, exit_with_result
    )

API_BASE_URL = TEST_API_BASE_URL
TIMEOUT = 30.0


def test_single_item():
    """Test processing single item (1-element bulk)."""
    print_section("Test 1: Single Item Processing")

    try:
        response = httpx.post(
            f"{API_BASE_URL}/your-prefix/process",
            json={
                "items": [
                    {"field1": "value1", "field2": "123.45"}
                    ]
                },
            timeout=TIMEOUT
            )

        if response.status_code != 200:
            print_error(f"Expected 200, got {response.status_code}")
            return False

        data = response.json()

        # Validate response structure
        if "results" not in data or "errors" not in data:
            print_error("Invalid response structure")
            return False

        if len(data["results"]) != 1:
            print_error(f"Expected 1 result, got {len(data['results'])}")
            return False

        print_success("Single item processed successfully")
        return True

    except Exception as e:
        print_error(f"Request failed: {e}")
        return False


def test_bulk_items():
    """Test processing multiple items."""
    print_section("Test 2: Bulk Processing (3 items)")

    try:
        response = httpx.post(
            f"{API_BASE_URL}/your-prefix/process",
            json={
                "items": [
                    {"field1": "value1", "field2": "100.00"},
                    {"field1": "value2", "field2": "200.00"},
                    {"field1": "value3", "field2": "300.00"}
                    ]
                },
            timeout=TIMEOUT
            )

        if response.status_code != 200:
            print_error(f"Expected 200, got {response.status_code}")
            return False

        data = response.json()

        if len(data["results"]) != 3:
            print_error(f"Expected 3 results, got {len(data['results'])}")
            return False

        if data["success_count"] != 3:
            print_error(f"Expected success_count=3, got {data['success_count']}")
            return False

        print_success("Bulk processing successful (3 items)")
        return True

    except Exception as e:
        print_error(f"Request failed: {e}")
        return False


def test_partial_failure():
    """Test partial failure handling."""
    print_section("Test 3: Partial Failure (2 valid, 1 invalid)")

    try:
        response = httpx.post(
            f"{API_BASE_URL}/your-prefix/process",
            json={
                "items": [
                    {"field1": "valid1", "field2": "100.00"},
                    {"field1": "invalid", "field2": "-100.00"},  # Invalid (negative)
                    {"field1": "valid2", "field2": "200.00"}
                    ]
                },
            timeout=TIMEOUT
            )

        if response.status_code != 200:
            print_error(f"Expected 200 (partial success), got {response.status_code}")
            return False

        data = response.json()

        # Should have 2 results and 1 error
        if data["success_count"] != 2:
            print_error(f"Expected 2 successes, got {data['success_count']}")
            return False

        if len(data["errors"]) != 1:
            print_error(f"Expected 1 error, got {len(data['errors'])}")
            return False

        print_success("Partial failure handled correctly")
        print_info(f"  Successes: {data['success_count']}")
        print_info(f"  Errors: {len(data['errors'])}")
        return True

    except Exception as e:
        print_error(f"Request failed: {e}")
        return False


def test_validation():
    """Test request validation."""
    print_section("Test 4: Validation")

    all_ok = True

    # Test 1: Empty array
    print_info("Test 4.1: Empty items array")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/your-prefix/process",
            json={"items": []},
            timeout=TIMEOUT
            )

        if response.status_code == 200:
            print_error("Empty array was accepted (should return 422)")
            all_ok = False
        else:
            print_success(f"Empty array rejected (status {response.status_code})")
    except Exception as e:
        print_error(f"Request failed: {e}")
        all_ok = False

    # Test 2: Missing required field
    print_info("\nTest 4.2: Missing required field")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/your-prefix/process",
            json={
                "items": [
                    {"field1": "value1"}  # Missing field2
                    ]
                },
            timeout=TIMEOUT
            )

        if response.status_code == 200:
            print_error("Missing field was accepted (should return 422)")
            all_ok = False
        else:
            print_success(f"Missing field rejected (status {response.status_code})")
    except Exception as e:
        print_error(f"Request failed: {e}")
        all_ok = False

    return all_ok


def run_all_tests():
    """Run all tests."""
    print_test_header(
        "LibreFolio - Your API Tests",
        description="Tests for your feature endpoints",
        prerequisites=["Test server will be started automatically"]
        )

    with _TestingServerManager() as server_manager:
        print_section("Backend Server Management")

        print_info("Starting test server...")
        if not server_manager.start_server():
            print_error("Failed to start server")
            return False

        print_success("Test server started")

        # Run tests
        results = {
            "Single Item": test_single_item(),
            "Bulk Items": test_bulk_items(),
            "Partial Failure": test_partial_failure(),
            "Validation": test_validation()
            }

        success = print_test_summary(results, "Your API Tests")

        print_info("Stopping test server...")
        return success


if __name__ == "__main__":
    success = run_all_tests()
    exit_with_result(success)
```

### Test Coverage Requirements

Every endpoint must test:

1. ✅ **Happy path**: Valid single item
2. ✅ **Bulk operation**: Multiple items (3+)
3. ✅ **Partial failure**: Mix of valid/invalid items
4. ✅ **Validation**: Empty array, missing fields, invalid values
5. ✅ **Error handling**: 400/404/422/500 status codes

---

## 📚 Documentation

### 1. Inline Documentation (FastAPI)

FastAPI automatically generates OpenAPI/Swagger docs from your code:

```python
@router.post("/process", response_model=YourBulkResponse, status_code=200)
async def process_items_bulk(
        request: YourBulkRequest,
        session: AsyncSession = Depends(get_session)
        ):
    """
    Process one or more items (bulk operation). 
    
    This endpoint accepts a list of items to process. Even single items
    should be sent as a list with one element.
    
    **Request Body**:
    ```json
    {
        "items": [
            {"field1": "value1", "field2": 123.45}
        ]
    }
    ```
    
    **Response** (success):
    ```json
    {
        "results": [...],
        "success_count": 1,
        "errors": []
    }
    ```
    
    Args:
        request: Bulk request with list of items
        session: Database session (injected)
    
    Returns:
        Bulk response with results and errors
    """
    # Implementation
    pass
```

**Access docs at**:` http://localhost:8000/docs` (Swagger UI)

### 2. Pydantic Model Documentation

```python
class YourItemRequest(BaseModel):
    """
    Single item in bulk request. 
    
    Example:
        {
            "field1": "value1",
            "field2": 123.45
        }
    """
    field1: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Description shown in API docs"
        )
    field2: Decimal = Field(
        ...,
        gt=0,
        description="Must be positive number"
        )
```

### 3. Markdown Documentation

Create detailed guides in `docs/` folder:

**File**: `docs/your-feature-api.md`

````markdown
# Your Feature API

## Overview

Brief description of what this API does.

## Endpoints

### POST /api/v1/your-prefix/process

Process one or more items in bulk.

**Request**:

```json
{
    "items": [
        {"field1": "value1", "field2": 123.45}
    ]
}
```

**Response**:

```json
{
    "results": [...],
    "success_count": 1,
    "errors": []
}
```

**Errors**:

- `400`: All items failed
- `422`: Validation error
- `500`: Server error

## Examples

### Single Item

```bash
curl -X POST http://localhost:8000/api/v1/your-prefix/process \
  -H "Content-Type: application/json" \
  -d '{"items": [{"field1": "test", "field2": 100.00}]}'
```

### Bulk Items

```bash
curl -X POST http://localhost:8000/api/v1/your-prefix/process \
  -H "Content-Type: application/json" \
  -d 
    "items": [
        {"field1": "item1", "field2": 100.00},
        {"field1": "item2", "field2": 200.00}
    ]
}
```
````

---

## ✅ Best Practices

### 1. Always Use Type Hints

```python
# ✅ GOOD
async def process_items(
        session: AsyncSession,
        items: list[tuple[str, Decimal]]
        ) -> tuple[list[dict], list[str]]:
    pass


# ❌ BAD
async def process_items(session, items):
    pass
```

### 2. Use Pydantic for Validation

```python
# ✅ GOOD: Pydantic validates automatically
class Request(BaseModel):
    amount: Decimal = Field(..., gt=0)


# ❌ BAD: Manual validation
def endpoint(amount: float):
    if amount <= 0:
        raise HTTPException(400, "Invalid amount")
```

### 3. Async All the Way

```python
# ✅ GOOD: Fully async
async def endpoint():
    result = await async_function()
    return result


# ❌ BAD: Mixing sync/async
async def endpoint():
    result = sync_function()  # Blocks event loop!
    return result
```

### 4. Error Handling

```python
# ✅ GOOD: Specific exceptions
try:
    result = await service_function()
except YourServiceError as e:
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")

# ❌ BAD: Catch-all without logging
try:
    result = await service_function()
except:
    raise HTTPException(500, "Error")
```

### 5. Logging

```python
import logging

logger = logging.getLogger(__name__)


async def service_function():
    logger.info("Starting operation")
    try:
        # ... operation ...
        logger.debug(f"Processed {count} items")
    except Exception as e:
        logger.error(f"Operation failed: {e}", exc_info=True)
        raise
```

### 6. Database Session Management

```python
# ✅ GOOD: Use dependency injection
@router.post("/endpoint")
async def endpoint(session: AsyncSession = Depends(get_session)):
    result = await session.execute(stmt)
    return result


# ❌ BAD: Manual session management
@router.post("/endpoint")
async def endpoint():
    async with AsyncSession(engine) as session:  # Don't do this!
        pass
```

---

## 📖 Complete Example

See the FX API implementation as reference:

- **API Layer**: `backend/app/api/v1/fx.py`
- **Service Layer**: `backend/app/services/fx.py`
- **Database Models**: `backend/app/db/models.py` (FxRate model)
- **Tests**: `backend/test_scripts/test_api/test_fx_api.py`
- **Documentation**: `docs/fx-implementation.md`

**Key endpoints to study**:

1. `POST /fx/convert/bulk` - Bulk conversion (single query for N conversions)
2. `POST /fx/rate` - Bulk upsert (single INSERT for N rates)
3. `POST /fx/sync/bulk` - Bulk fetch from external API

---

## 🎓 Quick Start Checklist

When adding a new API endpoint:

- [ ] 
    1. Define database models (if needed) in `backend/app/db/models.py`
- [ ] 
    2. Create migration with Alembic (if schema changes)
- [ ] 
    3. Implement service layer in `backend/app/services/your_service.py`

    - [ ] Implement bulk function first
    - [ ] Add single-item wrapper
    - [ ] Use batch DB queries
- [ ] 
    4. Create Pydantic models in `backend/app/api/v1/your_module.py`

    - [ ] Request models with validation
    - [ ] Response models with examples
- [ ] 
    5. Implement endpoints

    - [ ] Use bulk-first design
    - [ ] Handle partial failures
    - [ ] Add comprehensive docstrings
- [ ] 
    6. Register router in `backend/app/api/v1/router.py`
- [ ] 
    7. Write tests in `backend/test_scripts/test_api/test_your_api.py`

    - [ ] Single item test
    - [ ] Bulk test (3+ items)
    - [ ] Partial failure test
    - [ ] Validation tests
- [ ] 
    8. Update documentation

    - [ ] Add inline docs (docstrings)
    - [ ] Create markdown guide in `docs/`
- [ ] 
    9. Run tests: `python test_runner.py api your-feature`
- [ ] 
    10. Verify Swagger docs: `http://localhost:8000/docs`

---

## 🆘 Common Issues

### Issue: "NullPool has no attribute 'connect'"

**Solution**: Use `get_session()` dependency injection, don't create sessions manually.

### Issue: "asyncio.run() cannot be called from a running event loop"

**Solution**: Use `await` everywhere, don't mix `asyncio.run()` in async code.

### Issue: "SQLite database is locked"

**Solution**:

- Ensure using WAL mode: `PRAGMA journal_mode=WAL`
- Use NullPool for SQLite (already configured)
- Don't hold transactions open too long

### Issue: "Field required" validation error

**Solution**: Check Pydantic model - all fields without default are required. Use `Field(None)` for optional.

### Issue: Test server won't start

**Solution**: Check if port is in use:

```bash
lsof -ti:8001 | xargs kill -9  # Kill process on port 8001
```

---

## 📞 Support

- **GitHub Issues**: Report bugs and feature requests
- **Discussions**: Ask questions and share ideas
- **Documentation**: Check `docs/` folder for detailed guides
- **Examples**: Study `backend/app/api/v1/fx.py` for reference implementation

---

**Last Updated**: November 2, 2025
**Version**: 1.0
**Maintainer**: LibreFolio Contributors

## 🕵️ How to get information about API development

To get information about API development an Agent can:

1.  Read this file.
2.  Inspect the directory `backend/app/api/v1/` to see existing API endpoints.
3.  Read the `backend/app/services/` directory to understand the business logic layer.
4.  Run the API tests in `backend/test_scripts/test_api/` to see the endpoints in action.

```
