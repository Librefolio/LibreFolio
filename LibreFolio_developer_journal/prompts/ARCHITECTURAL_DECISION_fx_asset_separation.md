# Architectural Decision: FX and Asset Pricing Separation

**Date**: 2025-11-06  
**Status**: ✅ APPROVED  
**Context**: Phase 0.2 implementation planning for Step 05

---

## 🎯 Decision

**Keep `fx.py` and `asset_source.py` DB operations SEPARATE.**

Do NOT create a shared `pricing.py` layer that tries to abstract over both `fx_rates` and `price_history` tables.

---

## 🔍 Problem Analysis

### Initial Plan (REJECTED)
Create `pricing.py` with shared DB operations for both FX rates and asset prices:
- Single backward-fill implementation
- Generic bulk upsert/delete
- Shared query optimization

### Why It Seemed Good
- Less code duplication (~20 lines of backward-fill logic)
- Single source of truth for pricing operations
- Unified testing approach

### Why It's Actually BAD

#### 1. **Different Table Structures**

**FX Rates** (`fx_rates`):
```sql
id, base, quote, rate, date, source, fetched_at
```
- Query pattern: `WHERE base=? AND quote=? AND date=?`
- Single value: `rate` (Decimal 24,10)
- Pair-based: needs both base AND quote

**Asset Prices** (`price_history`):
```sql
id, asset_id, date, open, high, low, close, volume, currency, source_plugin_key, fetched_at
```
- Query pattern: `WHERE asset_id=? AND date=?`
- Multiple values: OHLC + volume
- Single asset: only asset_id

#### 2. **Different Query Patterns**

**FX backward-fill**:
```python
# Find most recent rate for EUR/USD before target_date
SELECT * FROM fx_rates 
WHERE base='EUR' AND quote='USD' AND date <= ?
ORDER BY date DESC LIMIT 1
```

**Asset backward-fill**:
```python
# Find most recent price for asset_id=123 before target_date
SELECT * FROM price_history
WHERE asset_id=123 AND date <= ?
ORDER BY date DESC LIMIT 1
```

**Trying to abstract**: Would need complex conditionals based on table type, reducing readability.

#### 3. **Different Constraints**

- FX: CHECK constraint `base < quote` (alphabetical ordering)
- Asset: UNIQUE constraint `(asset_id, date)` (one price per day per asset)
- FX: Supports inverse queries (EUR/USD → 1/rate = USD/EUR)
- Asset: No inversion concept

#### 4. **Synthetic Yield Special Case**

Asset pricing needs special handling for `SCHEDULED_YIELD` assets:
- Check `asset.valuation_model` field
- Calculate value from interest_schedule
- Skip DB query entirely

FX has no equivalent concept.

---

## ✅ Approved Solution

### Keep Separate Services

**`fx.py`** (existing, unchanged):
- Handles `fx_rates` table
- FX-specific query patterns
- Supports inverse rate calculations
- Backward-fill for currency pairs

**`asset_source.py`** (new):
- Handles `price_history` table
- Asset-specific query patterns
- OHLC field handling
- Backward-fill for assets
- **Synthetic yield calculation** (for SCHEDULED_YIELD assets)

### Share Only Common Schemas

**`schemas/common.py`** (new):
```python
class BackwardFillInfo(TypedDict):
    """Used by both FX and Asset pricing."""
    actual_rate_date: str  # ISO date
    days_back: int
```

### Independent Implementations

- Backward-fill logic: **Duplicated (~20 lines)** in both services
- DB query optimization: Tailored to each table structure
- Helper functions: Specific to each domain

---

## 📊 Trade-offs

### ✅ Advantages of Separation

1. **Clear Ownership**: Each service owns its table completely
2. **No Leaky Abstraction**: No generic layer with `if table_type == "fx"` conditionals
3. **Independent Evolution**: Can change fx_rates structure without affecting assets
4. **Simpler Testing**: Test each service independently with its own fixtures
5. **Better Performance**: Queries optimized for specific table structure
6. **Easier Onboarding**: New developers understand one service at a time

### ❌ Disadvantages

1. **Code Duplication**: ~20 lines of backward-fill logic duplicated
2. **Schema Updates**: BackwardFillInfo changes need updates in 2 places
3. **Testing**: Need to test backward-fill twice (once per service)

### 🎯 Assessment

**Duplication cost**: ~20 lines × 2 services = 40 lines total  
**Abstraction cost**: Generic layer would be ~100+ lines of complex conditional logic  
**Maintenance burden**: Higher with generic layer (changes affect both systems)

**Verdict**: Duplication is CHEAPER than abstraction here.

---

## 💡 Design Patterns Used

### DRY Principle - Applied Correctly

"Don't Repeat Yourself" doesn't mean "never duplicate code."

It means "don't duplicate **knowledge** or **business logic**."

- ✅ **Knowledge duplication**: Backward-fill algorithm is the SAME
  - Solution: Could extract to `_backward_fill_helper()` utility if really needed
- ❌ **Implementation duplication**: Query patterns are DIFFERENT
  - Solution: Keep separate implementations

### KISS Principle

"Keep It Simple, Stupid"

- Generic pricing layer: Complex, fragile, hard to understand
- Separate services: Simple, clear, easy to reason about

### YAGNI Principle

"You Aren't Gonna Need It"

- Generic layer anticipates future table types that don't exist
- Build for actual requirements (2 different tables), not hypothetical future

---

## 📝 Implementation Notes

### What IS Shared

1. **`BackwardFillInfo` TypedDict** (`schemas/common.py`)
   - Exact same structure for both services
   - Single source of truth for response format

2. **Provider Registry Pattern** (`provider_registry.py`)
   - Abstract base: `AbstractProviderRegistry[T]`
   - Specializations: `FXProviderRegistry`, `AssetProviderRegistry`
   - Auto-discovery mechanism identical

3. **Bulk-First Design Pattern**
   - Both services: bulk operations PRIMARY
   - Both services: single operations call bulk with 1 element

### What Is NOT Shared

1. **DB Query Logic** - Completely separate
2. **Backward-Fill Implementation** - Duplicated but tailored
3. **Helper Functions** - Domain-specific (precision, truncation, etc.)
4. **Manager Classes** - Different responsibilities

---

## 🔮 Future Considerations

### If We Ever NEED Shared Logic

**Option A**: Extract to utility function
```python
# utils/backward_fill.py
def find_most_recent_record(
    session: AsyncSession,
    table: Type[SQLModel],
    filters: dict,
    date_column: str,
    target_date: date
) -> dict | None:
    """Generic backward-fill query builder."""
    pass
```

**When to use**: If we add 3+ more pricing tables with similar patterns.  
**Not now**: Premature optimization for 2 different tables.

### Refactoring Trigger

Consider shared layer ONLY if:
- We have 3+ pricing tables with **identical** query patterns
- Backward-fill logic becomes more complex (>50 lines)
- Performance profiling shows duplication is a bottleneck (unlikely)

---

## 📚 References

- [Martin Fowler - Beck Design Rules](https://martinfowler.com/bliki/BeckDesignRules.html)
- [Sandi Metz - The Wrong Abstraction](https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction)
- [Dan Abramov - The WET Codebase](https://overreacted.io/the-wet-codebase/)

**Key Quote**:
> "Duplication is far cheaper than the wrong abstraction."  
> — Sandi Metz

---

## ✅ Decision Log

**Proposed by**: User (ea_enel)  
**Date**: 2025-11-06  
**Reviewed by**: GitHub Copilot (architectural analysis)  
**Status**: APPROVED  
**Implementation**: Phase 0.2 updated in both main doc and checklist  

**Alternative considered**: Shared `pricing.py` layer  
**Reason for rejection**: Different table structures make abstraction fragile and complex  

---

## 🎯 Action Items

- [x] Remove `pricing.py` from Phase 0.2 plan
- [x] Update Phase 0.2 to create `schemas/common.py` with `BackwardFillInfo`
- [x] Update Phase 0.2 to create `asset_source.py` (similar to fx.py)
- [x] Update checklist with new structure
- [x] Update folder structure diagram
- [x] Document this decision (this file)
- [ ] Implement Phase 0.2 with separated approach
- [ ] Validate decision with working code

**Next Phase**: Phase 0.2.1 - Create `schemas/common.py`

