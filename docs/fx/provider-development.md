# FX Provider Development Guide

Quick reference guide for developing new FX rate providers in LibreFolio.

> 📚 For complete FX system documentation, see [FX Implementation Guide](./fx-implementation.md)

---

## 🎯 Quick Start Checklist

- [ ] Create provider class in `backend/app/services/fx_providers/`
- [ ] Inherit from `FXRateProvider` abstract base class
- [ ] Implement all required methods
- [ ] Register provider in `__init__.py`
- [ ] Run tests: `./test_runner.py -v external all`
- [ ] Done! Your provider is ready to use

---

## 📝 Minimal Provider Template

```python
# backend/app/services/fx_providers/your_provider.py
"""
Your Central Bank FX rate provider.
"""
import logging
from datetime import date
from decimal import Decimal
import httpx

from backend.app.services.fx import FXRateProvider, FXProviderFactory, FXServiceError

logger = logging.getLogger(__name__)


class YourProvider(FXRateProvider):
    """Your Central Bank FX rate provider."""
    
    BASE_URL = "https://api.yourcentralbank.com/..."
    
    @property
    def code(self) -> str:
        return "YCB"  # Uppercase code
    
    @property
    def name(self) -> str:
        return "Your Central Bank"
    
    @property
    def base_currency(self) -> str:
        return "XXX"  # ISO 4217 code (primary/default base)
    
    @property
    def base_currencies(self) -> list[str]:
        """
        For single-base providers: return [self.base_currency]
        For multi-base providers: return all supported bases
        """
        return [self.base_currency]  # Default implementation
    
    @property
    def multi_unit_currencies(self) -> set[str]:
        return set()  # or {'JPY', 'SEK'} if applicable
    
    async def get_supported_currencies(self) -> list[str]:
        """Return list of supported currencies."""
        return ['XXX', 'USD', 'EUR', 'GBP']
    
    async def fetch_rates(
        self,
        date_range: tuple[date, date],
        currencies: list[str],
        base_currency: str | None = None
    ) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """Fetch rates from API."""
        # Validate base_currency for single-base provider
        if base_currency is not None and base_currency != self.base_currency:
            raise ValueError(
                f"{self.name} only supports {self.base_currency} as base, "
                f"got {base_currency}"
            )
        
        start_date, end_date = date_range
        results = {}
        
        for currency in currencies:
            if currency == self.base_currency:
                continue
            
            # 1. Fetch from API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/rates",
                    params={'currency': currency, 'start': start_date, 'end': end_date}
                )
                response.raise_for_status()
                data = response.json()
            
            # 2. Parse response
            observations = []
            for item in data['rates']:
                rate_date = date.fromisoformat(item['date'])
                rate_value = Decimal(str(item['rate']))
                
                # 3. Apply multi-unit adjustment if needed
                if currency in self.multi_unit_currencies:
                    rate_value = rate_value / Decimal("100")
                
                # 4. Return 4-tuple: (date, base, quote, rate)
                observations.append((
                    rate_date,
                    self.base_currency,
                    currency,
                    rate_value
                ))
            
            results[currency] = observations
        
        return results


# Auto-register
FXProviderFactory.register(YourProvider)
```

---

## ✅ Required Methods

### 1. `code` (property)

```python
@property
def code(self) -> str:
    return "YCB"  # UPPERCASE, unique identifier
```

**Rules:**
- Must be UPPERCASE
- Must be unique across all providers
- Typically 3-4 letters (e.g., ECB, FED, BOE, SNB)

---

### 2. `name` (property)

```python
@property
def name(self) -> str:
    return "Your Central Bank"
```

**Rules:**
- Human-readable name
- Used in logs and UI

---

### 3. `base_currency` (property)

```python
@property
def base_currency(self) -> str:
    return "XXX"  # ISO 4217 code
```

**Rules:**
- Must be valid ISO 4217 currency code
- This is the base currency for your provider's rates
- Example: EUR for ECB, USD for FED, GBP for BOE

---

### 4. `get_supported_currencies()` (async method)

```python
async def get_supported_currencies(self) -> list[str]:
    return ['XXX', 'USD', 'EUR', 'GBP']
```

**Options:**

**Static list:**
```python
async def get_supported_currencies(self) -> list[str]:
    return ['XXX', 'USD', 'EUR', 'GBP', 'JPY']
```

**Dynamic (fetch from API):**
```python
async def get_supported_currencies(self) -> list[str]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{self.BASE_URL}/currencies")
        response.raise_for_status()
        return response.json()['currencies']
```

---

### 5. `fetch_rates()` (async method)

```python
async def fetch_rates(
    self,
    date_range: tuple[date, date],
    currencies: list[str],
    base_currency: str | None = None
) -> dict[str, list[tuple[date, str, str, Decimal]]]:
    # Validate base_currency (for single-base providers)
    if base_currency is not None and base_currency != self.base_currency:
        raise ValueError(f"Provider only supports {self.base_currency}")
    
    # Implementation here
```

**Return format:** `dict[str, list[tuple[date, str, str, Decimal]]]`

**Example return:**
```python
{
    'USD': [
        (date(2025-01-01), 'EUR', 'USD', Decimal('1.08')),
        (date(2025-01-02), 'EUR', 'USD', Decimal('1.09')),
    ],
    'GBP': [
        (date(2025-01-01), 'EUR', 'GBP', Decimal('0.85')),
    ]
}
```

**4-tuple elements:**
1. `date`: The rate date (Python `date` object)
2. `base`: Base currency (string, e.g., 'EUR')
3. `quote`: Quote currency (string, e.g., 'USD')
4. `rate`: The exchange rate (Decimal)

**Rate semantics:** `1 base = rate × quote`

Example: `(date(2025-01-01), 'EUR', 'USD', Decimal('1.08'))`  
Means: **1 EUR = 1.08 USD**

---

## 🔧 Optional Properties

### `description` (property)

```python
@property
def description(self) -> str:
    return "Custom description"
```

Default: `"Official exchange rates from {self.name}"`

---

### `test_currencies` (property)

```python
@property
def test_currencies(self) -> list[str]:
    return ["XXX", "USD", "EUR", "GBP", "JPY"]
```

Used by automated test suite to verify provider works correctly.

Default: `["USD", "EUR", "GBP", "JPY", "CHF"]`

---

### `multi_unit_currencies` (property)

```python
@property
def multi_unit_currencies(self) -> set[str]:
    return {'JPY', 'SEK', 'NOK', 'DKK'}
```

**Only needed if** your provider quotes certain currencies per 100 units instead of per 1 unit.

**Example:** SNB quotes JPY as "100 JPY = 1.50 CHF" instead of "1 JPY = 0.015 CHF"

**Handling:**
```python
async def fetch_rates(self, ...):
    # API returns: 100 JPY = 1.50 CHF
    api_rate = Decimal("1.50")
    
    # Convert to per-1-unit: 1 JPY = 0.015 CHF
    if currency in self.multi_unit_currencies:
        rate_value = api_rate / Decimal("100")
    
    return (rate_date, 'CHF', 'JPY', rate_value)
```

Default: `set()` (empty - no multi-unit currencies)

---

## 🌐 Multi-Base Currency Providers (Advanced)

For commercial APIs or providers that support multiple base currencies:

### Implementation Example

```python
class MultiBaseProvider(FXRateProvider):
    """Example provider with multiple base currencies."""
    
    @property
    def code(self) -> str:
        return "MULTI"
    
    @property
    def name(self) -> str:
        return "Multi-Base API"
    
    @property
    def base_currency(self) -> str:
        return "USD"  # Default/preferred base
    
    @property
    def base_currencies(self) -> list[str]:
        """All supported base currencies."""
        return ["EUR", "GBP", "USD"]  # Alphabetical order recommended
    
    async def fetch_rates(
        self,
        date_range: tuple[date, date],
        currencies: list[str],
        base_currency: str | None = None
    ) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """Fetch rates with specified base."""
        
        # 1. Determine which base to use
        actual_base = base_currency if base_currency else self.base_currency
        
        # 2. Validate base_currency
        if actual_base not in self.base_currencies:
            raise ValueError(
                f"Base {actual_base} not supported. "
                f"Available: {', '.join(self.base_currencies)}"
            )
        
        # 3. Filter out base from quote currencies
        quote_currencies = [c for c in currencies if c != actual_base]
        
        # 4. Fetch from API with specified base
        results = {}
        for currency in quote_currencies:
            url = f"{self.BASE_URL}/rates?base={actual_base}&quote={currency}"
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                data = response.json()
            
            observations = []
            for item in data['rates']:
                observations.append((
                    date.fromisoformat(item['date']),
                    actual_base,  # Use specified base
                    currency,
                    Decimal(str(item['rate']))
                ))
            
            results[currency] = observations
        
        return results
```

### Usage

```python
# Fetch rates with EUR as base
result = await ensure_rates_multi_source(
    session,
    date_range=(date(2025, 1, 1), date(2025, 1, 31)),
    currencies=["JPY", "CHF"],
    provider_code="MULTI",
    base_currency="EUR"  # Explicitly specify base
)

# Fetch with default base (USD)
result = await ensure_rates_multi_source(
    session,
    date_range=(date(2025, 1, 1), date(2025, 1, 31)),
    currencies=["JPY", "CHF"],
    provider_code="MULTI"
    # base_currency=None uses provider's default (USD)
)
```

### Key Points

- ✅ `base_currencies` returns list of all supported bases
- ✅ `base_currency` returns the default/preferred base
- ✅ `fetch_rates()` accepts optional `base_currency` parameter
- ✅ Filter base currency from quotes list to avoid fetching BASE/BASE
- ✅ Validate base_currency is in base_currencies list
- ✅ Return tuples with actual base used

---

## ⚠️ Common Pitfalls

### ❌ DON'T: Return 2-tuple format

```python
# WRONG - old format
return (rate_date, rate_value)
```

### ✅ DO: Return 4-tuple format

```python
# CORRECT - new format
return (rate_date, base_currency, quote_currency, rate_value)
```

---

### ❌ DON'T: Normalize alphabetically

```python
# WRONG - don't try to normalize
if base > quote:
    return (quote, base, 1/rate)
```

### ✅ DO: Return as-is from API

```python
# CORRECT - service layer handles normalization
return (rate_date, self.base_currency, currency, rate_value)
```

---

### ❌ DON'T: Raise error on missing data

```python
# WRONG - weekends/holidays are normal
if not data:
    raise FXServiceError("No data!")
```

### ✅ DO: Return empty list

```python
# CORRECT - handle missing data gracefully
if not data:
    logger.info(f"No rates for {currency} (weekends/holidays)")
    results[currency] = []
    continue
```

---

### ❌ DON'T: Return multi-unit rates as-is

```python
# WRONG - if API returns per-100 rates
api_rate = Decimal("1.50")  # 100 JPY = 1.50 CHF
return (date, 'CHF', 'JPY', api_rate)  # WRONG!
```

### ✅ DO: Convert to per-1-unit

```python
# CORRECT - adjust to per-1-unit
api_rate = Decimal("1.50")  # 100 JPY = 1.50 CHF
if currency in self.multi_unit_currencies:
    rate_value = api_rate / Decimal("100")  # 1 JPY = 0.015 CHF
return (date, 'CHF', 'JPY', rate_value)  # CORRECT!
```

---

## 🧪 Testing Your Provider

### Run automated tests

```bash
# Test all providers (including yours)
./test_runner.py -v external all
```

Your provider will be automatically tested for:
- ✅ Registration and metadata
- ✅ Supported currencies
- ✅ Rate fetching (live API)
- ✅ Data format validation
- ✅ Normalization logic
- ✅ Multi-unit handling (if applicable)

### Test output example

```
============================================================
  Testing Provider: YCB
============================================================

Test 1: YCB - Metadata & Registration
✅ YCB is registered in factory
✅ Provider metadata valid

Test 2: YCB - Supported Currencies
✅ Found 15 supported currencies
✅ All test currencies present

Test 3: YCB - Fetch Rates
✅ Received rate data for 2 currencies
✅ Rate data structure valid

Test 4: YCB - Normalization
✅ Rate normalization works correctly

Results: 4/4 tests passed
```

---

## 📦 Registration

Add to `backend/app/services/fx_providers/__init__.py`:

```python
from backend.app.services.fx_providers.ecb import ECBProvider
from backend.app.services.fx_providers.fed import FEDProvider
from backend.app.services.fx_providers.boe import BOEProvider
from backend.app.services.fx_providers.snb import SNBProvider
from backend.app.services.fx_providers.your_provider import YourProvider  # Add this

__all__ = [
    'ECBProvider',
    'FEDProvider',
    'BOEProvider',
    'SNBProvider',
    'YourProvider',  # Add this
]
```

**That's it!** Your provider auto-registers via `FXProviderFactory.register()` in the module.

---

## 🚀 Using Your Provider

### In Python code

```python
from backend.app.services.fx import ensure_rates_multi_source

# Fetch rates using your provider
await ensure_rates_multi_source(
    session,
    date_range=(start_date, end_date),
    currencies=['USD', 'EUR'],
    provider_code='YCB'  # Your provider code
)
```

### Via API

```bash
# Sync rates
POST /api/v1/fx/sync/bulk?start=2025-01-01&end=2025-01-31&currencies=USD,EUR&provider=YCB

# Response
{
  "synced": 60,
  "provider": "YCB",
  "date_range": ["2025-01-01", "2025-01-31"],
  "currencies": ["USD", "EUR"]
}
```

---

## 📖 Real Examples

Study these working implementations:

| Provider | Features | File |
|----------|----------|------|
| **BOE** | Simple, static currency list | `fx_providers/boe.py` |
| **ECB** | Dynamic currency list, JSON parsing | `fx_providers/ecb.py` |
| **FED** | CSV parsing, date filtering | `fx_providers/fed.py` |
| **SNB** | Multi-unit currencies | `fx_providers/snb.py` |

---

## 🐛 Debugging Tips

### Enable debug logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test individual provider

```python
from backend.app.services.fx import FXProviderFactory

provider = FXProviderFactory.get_provider('YCB')
currencies = await provider.get_supported_currencies()
print(currencies)

rates = await provider.fetch_rates(
    (date(2025, 1, 1), date(2025, 1, 3)),
    ['USD', 'EUR']
)
print(rates)
```

### Check API response format

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(f"{BASE_URL}/...")
    print(response.text)  # Raw response
    print(response.json())  # Parsed JSON
```

---

## 📚 Related Documentation

- **[FX Implementation Guide](./fx-implementation.md)** - Complete FX system documentation
- **[Testing Guide](./testing-guide.md)** - How to run and write tests
- **[Async Architecture Guide](./async-architecture.md)** - Async patterns in LibreFolio
- **[API Development Guide](./api-development-guide.md)** - API endpoint development

---

## 🔧 Advanced: Multi-Base Currency Providers

### Overview

Most providers support a **single base currency** (ECB=EUR, FED=USD, etc.). However, the system is ready for **multi-base providers** (e.g., commercial APIs that let you choose the base).

### Single-Base vs Multi-Base

**Single-Base Provider** (current):
```python
class ECBProvider(FXRateProvider):
    @property
    def base_currency(self) -> str:
        return "EUR"  # Only EUR supported
    
    @property
    def base_currencies(self) -> list[str]:
        return ["EUR"]  # Default: single item
```

**Multi-Base Provider** (future):
```python
class HypotheticalMultiProvider(FXRateProvider):
    @property
    def base_currency(self) -> str:
        return "EUR"  # Primary/default base
    
    @property
    def base_currencies(self) -> list[str]:
        return ["EUR", "USD", "GBP"]  # Multiple bases supported!
```

### Implementation Template

```python
class MultiBaseProvider(FXRateProvider):
    """Example multi-base provider (hypothetical commercial API)."""
    
    BASE_URL = "https://api.example.com/rates"
    API_KEY_REQUIRED = True
    
    @property
    def code(self) -> str:
        return "MULTI"
    
    @property
    def name(self) -> str:
        return "Multi-Base Commercial API"
    
    @property
    def base_currency(self) -> str:
        return "EUR"  # Default base
    
    @property
    def base_currencies(self) -> list[str]:
        return ["EUR", "USD", "GBP"]  # All supported bases
    
    @property
    def multi_unit_currencies(self) -> set[str]:
        return set()  # Usually not needed for commercial APIs
    
    async def get_supported_currencies(self) -> list[str]:
        """Return all supported currencies (independent of base)."""
        return ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD']
    
    async def fetch_rates(
        self,
        date_range: tuple[date, date],
        currencies: list[str],
        base_currency: str | None = None
    ) -> dict[str, list[tuple[date, str, str, Decimal]]]:
        """
        Fetch rates with optional base selection.
        
        Args:
            date_range: (start_date, end_date) inclusive
            currencies: List of quote currencies to fetch
            base_currency: Which base to use (EUR, USD, or GBP)
                          If None, uses self.base_currency (EUR)
        
        Returns:
            Dict mapping currency to list of (date, base, quote, rate) tuples
        """
        # Step 1: Determine which base to use
        selected_base = base_currency or self.base_currency
        
        # Step 2: Validate base is supported
        if selected_base not in self.base_currencies:
            raise ValueError(
                f"{self.name} does not support {selected_base} as base. "
                f"Supported bases: {', '.join(self.base_currencies)}"
            )
        
        logger.info(
            f"Fetching rates from {self.name} with base={selected_base} "
            f"for {len(currencies)} currencies"
        )
        
        # Step 3: Build API request with base parameter
        start_date, end_date = date_range
        results = {}
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # API call with base parameter
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "base": selected_base,
                        "symbols": ",".join(currencies),
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "apikey": os.getenv("MULTI_API_KEY")  # From environment
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            # Step 4: Parse response and normalize to (date, base, quote, rate)
            for currency in currencies:
                if currency == selected_base:
                    continue  # Skip identity pair
                
                rates_list = []
                for date_str, rates in data.get("rates", {}).items():
                    if currency in rates:
                        obs_date = date.fromisoformat(date_str)
                        rate = Decimal(str(rates[currency]))
                        
                        # Normalize to alphabetical order
                        base, quote, normalized_rate = normalize_for_storage(
                            selected_base, currency, rate
                        )
                        
                        rates_list.append((obs_date, base, quote, normalized_rate))
                
                if rates_list:
                    results[currency] = rates_list
            
            logger.info(f"Fetched {sum(len(v) for v in results.values())} rates")
            return results
            
        except httpx.HTTPError as e:
            raise FXServiceError(f"{self.name} API error: {e}")
```

### How Multi-Base Works

**API call with base selection**:
```bash
# Fetch EUR-based rates
curl ".../sync/bulk?currencies=JPY,CHF&provider=MULTI&base_currency=EUR"
# Fetches: EUR/JPY, EUR/CHF

# Fetch USD-based rates (different values!)
curl ".../sync/bulk?currencies=JPY,CHF&provider=MULTI&base_currency=USD"
# Fetches: USD/JPY, USD/CHF
```

**Backend behavior**:
```python
# User requests USD base
provider = FXProviderFactory.get_provider('MULTI')
rates = await provider.fetch_rates(
    (date(2025, 1, 1), date(2025, 1, 31)),
    ['JPY', 'CHF'],
    base_currency='USD'  # ← Passed to fetch_rates()
)

# Provider validates USD is in base_currencies
# Then calls API with base=USD parameter
# Returns USD/JPY and USD/CHF rates
```

### Best Practices

**1. Validate base_currency early**:
```python
if base_currency and base_currency not in self.base_currencies:
    raise ValueError(f"Unsupported base: {base_currency}")
```

**2. Use default base if not specified**:
```python
selected_base = base_currency or self.base_currency
```

**3. Document API requirements**:
```python
class MyProvider(FXRateProvider):
    """
    Multi-base provider requiring API key.
    
    Environment Variables:
        MY_PROVIDER_API_KEY: API key (required)
    
    Supported Bases:
        EUR, USD, GBP
    """
```

**4. Handle API base parameter variations**:
```python
# Some APIs use 'base', others 'from' or 'source'
params = {
    "base": selected_base,  # or "from", "source", etc.
    "symbols": ",".join(currencies)
}
```

### Testing Multi-Base Providers

```bash
# Test with default base
./test_runner.py -v external your-provider

# Test with explicit base (requires manual test script)
# backend/test_scripts/test_external/test_your_provider.py
```

**Manual test**:
```python
from backend.app.services.fx import FXProviderFactory
from datetime import date

provider = FXProviderFactory.get_provider('MULTI')

# Test each supported base
for base in provider.base_currencies:
    print(f"\nTesting base={base}")
    rates = await provider.fetch_rates(
        (date(2025, 1, 1), date(2025, 1, 3)),
        ['JPY', 'CHF'],
        base_currency=base
    )
    print(f"  Fetched {sum(len(v) for v in rates.values())} rates")
```

### Use Cases

**1. Portfolio optimization**: Choose base closest to your holdings
```bash
# European portfolio
curl ".../sync/bulk?currencies=USD,GBP,CHF&provider=MULTI&base_currency=EUR"

# US portfolio
curl ".../sync/bulk?currencies=EUR,GBP,CHF&provider=MULTI&base_currency=USD"
```

**2. Historical analysis**: Compare rates from different perspectives
```python
# EUR perspective
eur_based = await fetch_rates(..., base_currency='EUR')

# USD perspective (different values!)
usd_based = await fetch_rates(..., base_currency='USD')
```

**3. API cost optimization**: Some APIs charge per base currency
```bash
# Fetch all EUR-based pairs in one call
curl ".../sync/bulk?currencies=USD,GBP,JPY,CHF&base_currency=EUR"
# More efficient than separate calls per base
```

### Common Pitfalls

❌ **Don't** forget to validate base:
```python
# BAD: No validation
async def fetch_rates(self, ..., base_currency=None):
    # API call with base_currency (could be invalid!)
```

✅ **Do** validate early:
```python
# GOOD: Validate first
if base_currency and base_currency not in self.base_currencies:
    raise ValueError(...)
```

❌ **Don't** assume base is always provided:
```python
# BAD: Assumes base_currency is always set
url = f"{BASE_URL}?base={base_currency}"  # Could be None!
```

✅ **Do** use default:
```python
# GOOD: Fallback to default
selected_base = base_currency or self.base_currency
url = f"{BASE_URL}?base={selected_base}"
```

---

## 💡 Need Help?

1. Check existing provider implementations in `backend/app/services/fx_providers/`
2. Run tests with verbose output: `./test_runner.py -v external all`
3. Enable debug logging to see API requests/responses
4. Read the [FX Implementation Guide](./fx-implementation.md) for architecture details

Happy coding! 🚀

