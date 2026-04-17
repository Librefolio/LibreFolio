---
applyTo: "backend/app/services/brim_providers/**,backend/app/services/brim_provider.py"
---

# BRIM Providers (Broker Report Import Manager)

## Architecture

All BRIM plugins extend `BRIMProvider` (abstract base in `brim_provider.py`) and are auto-discovered via `@register_provider(BRIMProviderRegistry)`.

Each plugin parses a specific broker's export file format and extracts transactions.

## Plugins

| Plugin | File | Broker | Extensions |
|--------|------|--------|------------|
| `broker_ibkr` | `broker_ibkr.py` | Interactive Brokers | `.csv` |
| `broker_degiro` | `broker_degiro.py` | Degiro | `.csv` |
| `broker_directa` | `broker_directa.py` | Directa | `.csv`, `.xlsx` |
| `broker_etoro` | `broker_etoro.py` | eToro | `.xlsx` |
| `broker_coinbase` | `broker_coinbase.py` | Coinbase | `.csv` |
| `broker_revolut` | `broker_revolut.py` | Revolut | `.csv` |
| `broker_trading212` | `broker_trading212.py` | Trading212 | `.csv` |
| `broker_schwab` | `broker_schwab.py` | Charles Schwab | `.csv` |
| `broker_finpension` | `broker_finpension.py` | Finpension | `.csv` |
| `broker_freetrade` | `broker_freetrade.py` | Freetrade | `.csv` |
| `broker_generic_csv` | `broker_generic_csv.py` | Generic CSV | `.csv` |

## Base Class

The abstract base class `BRIMProvider` is defined in `backend/app/services/brim_provider.py`. Read that file for the full contract (abstract methods, properties, return types). Key methods: `parse_file()` → returns (transactions, warnings, extracted_assets), `detect()` for auto-detection.

## Fake Asset ID Flow

BRIM plugins use **fake asset IDs** (negative integers) during parsing. The frontend then maps these to real assets via the asset matching UI. This two-phase approach allows import without requiring pre-existing assets.

## Adding a New Plugin

The abstract base class is in `backend/app/services/brim_provider.py`. Read that file for the full contract.

1. Create `backend/app/services/brim_providers/broker_mybroker.py`
2. Extend `BRIMProvider` (from `brim_provider.py`)
3. Decorate with `@register_provider(BRIMProviderRegistry)`
4. Implement the required abstract methods (see base class)
5. Add sample report in `sample_reports/` for testing
6. Add icon in `static/` directory

## Testing

```bash
./dev.py test external brim-providers                           # All BRIM tests
./dev.py test external brim-providers --exclude-providers broker_coinbase  # Skip one
```

