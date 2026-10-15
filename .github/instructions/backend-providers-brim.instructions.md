---
applyTo: "backend/app/services/brim_providers/**,backend/app/services/brim/**"
---

# BRIM Providers (Broker Report Import Manager)

## Architecture

All BRIM plugins extend `BRIMProvider` (abstract base in `brim_provider.py`) and are auto-discovered via `@register_provider(BRIMProviderRegistry)`.

Each plugin parses a specific broker's export file format and extracts transactions.

## Plugins

| Plugin | File | Broker | Extensions |
|--------|------|--------|------------|
| `broker_ibkr` | `broker_ibkr/plugin.py` | Interactive Brokers | `.csv` |
| `broker_degiro` | `broker_degiro/plugin.py` | Degiro | `.csv` |
| `broker_directa` | `broker_directa/plugin.py` | Directa | `.csv`, `.xlsx` |
| `broker_etoro` | `broker_etoro/plugin.py` | eToro | `.xlsx` |
| `broker_coinbase` | `broker_coinbase/plugin.py` | Coinbase | `.csv` |
| `broker_revolut` | `broker_revolut/plugin.py` | Revolut | `.csv` |
| `broker_trading212` | `broker_trading212/plugin.py` | Trading212 | `.csv` |
| `broker_schwab` | `broker_schwab/plugin.py` | Charles Schwab | `.csv` |
| `broker_finpension` | `broker_finpension/plugin.py` | Finpension | `.csv` |
| `broker_freetrade` | `broker_freetrade/plugin.py` | Freetrade | `.csv` |
| `broker_generic_csv` | `broker_generic_csv/plugin.py` | Generic CSV | `.csv` |

## Base Class

The abstract base class `BRIMProvider` is defined in `backend/app/services/brim/brim_provider.py`. Read that file for the full contract (abstract methods, properties, return types). Key methods: `parse_file()` → returns (transactions, warnings, extracted_assets), `detect()` for auto-detection.

## Fake Asset ID Flow

BRIM plugins use **fake asset IDs** — high positive placeholders counting down from `FAKE_ASSET_ID_BASE` (`2**31 - 1`) — during parsing. The frontend then maps these to real assets via the asset matching UI. This two-phase approach allows import without requiring pre-existing assets.

## Adding a New Plugin

The abstract base class is in `backend/app/services/brim/brim_provider.py`. Read that file for the full contract.

1. Create the folder `backend/app/services/brim_providers/broker_mybroker/` with `__init__.py` (the plugin's
   docstring only, no re-export) and `plugin.py` (the code); helpers private to it go beside as `_*.py`, helpers shared
   by several brokers stay at the family root (`_brim_io.py`, `_brim_output.py`)
2. Extend `BRIMProvider` (from `brim_provider.py`)
3. Decorate with `@register_provider(BRIMProviderRegistry)` (`BRIMProviderRegistry` from `services/brim/registry.py`, the
   decorator from `services/provider_registry.py`)
4. Implement the required abstract methods (see base class)
5. Add sample report in `sample_reports/` for testing
6. Add icon in `static/` directory
7. Give the plugin its name and description in the four languages, in its own `i18n/` fragment:
   `./dev.py i18n add brimPlugins.broker_mybroker.name --en … --it … --fr … --es … --into brim_providers/broker_mybroker`
   (and `.description`). Import its names, and patch them, from `backend.app.services.brim_providers.broker_mybroker.plugin`

## Testing

```bash
./dev.py test external brim-providers                           # All BRIM tests
./dev.py test external brim-providers --exclude-providers broker_coinbase  # Skip one
```

