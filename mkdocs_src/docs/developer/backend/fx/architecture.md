# FX Architecture

The Foreign Exchange (FX) system is responsible for fetching, storing, and providing exchange rates for currency conversion.

## Multi-Provider Support

LibreFolio supports multiple FX rate providers (e.g., ECB, FED). This ensures redundancy and allows users to choose the source that best fits their needs (e.g., a US user might
prefer FED rates, while a European user prefers ECB).

### The `FXRateProvider` Interface

All providers must implement the `FXRateProvider` abstract base class:

```python
class FXRateProvider(ABC):
    @property
    def base_currency(self) -> str:
        """The provider's base currency (e.g., 'EUR' for ECB)."""
        pass

    async def fetch_rates(self, date_range, currencies) -> dict:
        """Fetch rates from the external API."""
        pass
```

## Normalization and Storage

Providers typically return rates relative to a specific base currency (e.g., ECB returns `1 EUR = X USD`).

To simplify storage and querying, LibreFolio normalizes all rates before saving them to the database. The rule is: **Base currency is always alphabetically smaller than Quote
currency.**

- **Input**: `EUR/USD` (EUR < USD) -> Stored as `base='EUR', quote='USD', rate=1.08`
- **Input**: `USD/GBP` (USD > GBP) -> Stored as `base='GBP', quote='USD', rate=1/0.78`

This ensures that we only need to store one rate per pair, and we can easily calculate the inverse if needed.

## Priority System

When converting currency, the system needs to decide which rate to use if multiple providers have data for the same pair and date.

Currently, the system allows the user (or admin) to select a **preferred provider** for synchronization. The `ensure_rates_multi_source` function orchestrates the fetching process
using the selected provider.

## Conversion Logic

The `convert` function handles the actual currency conversion:

1. **Direct Rate**: If a rate exists for `From/To` (or `To/From`), use it directly.
2. **Triangulation** (Future): If no direct rate exists, try to convert via a common intermediate currency (e.g., `USD`).
3. **Backward Fill**: If no rate exists for the exact requested date, find the most recent available rate.
