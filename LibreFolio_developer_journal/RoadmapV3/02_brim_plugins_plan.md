# Plan: BRIM Plugin Development for Major Brokers

**Document:** 02_brim_plugins_plan.md  
**Created:** 2026-01-06  
**Last Updated:** 2026-01-06  
**Status:** 🔄 IN PROGRESS

---

## Overview

This document outlines the plan to implement BRIM plugins for popular brokers.
The plugin system is now fully functional with auto-detection support.

### Architecture

```
BRIMProvider (base class)
├── provider_code       # Unique identifier
├── provider_name       # Human-readable name
├── description         # For UI
├── supported_extensions # ['.csv', ...]
├── detection_priority  # Higher = checked first (100 = broker-specific, 0 = generic)
├── icon_url            # Broker logo URL
├── can_parse()         # Auto-detection
└── parse()             # Returns (transactions, warnings, extracted_assets)
```

---

## Implementation Status

### ✅ Completed (Phase 1 - Alta priorità)

| Plugin              | Code                 | Priority | Icon | Status |
|---------------------|----------------------|----------|------|--------|
| Base Infrastructure | -                    | -        | -    | ✅      |
| Generic CSV         | `broker_generic_csv` | 0        | ❌    | ✅      |
| Directa SIM         | `broker_directa`     | 100      | ✅    | ✅      |
| DEGIRO              | `broker_degiro`      | 100      | ✅    | ✅      |
| Trading212          | `broker_trading212`  | 100      | ✅    | ✅      |
| Interactive Brokers | `broker_ibkr`        | 100      | ✅    | ✅      |
| eToro               | `broker_etoro`       | 100      | ✅    | ✅      |

### ✅ Completed (Phase 2 - Media priorità)

| Plugin         | Code                | Priority | Icon | Status |
|----------------|---------------------|----------|------|--------|
| Revolut        | `broker_revolut`    | 100      | ✅    | ✅      |
| Charles Schwab | `broker_schwab`     | 100      | ✅    | ✅      |
| Freetrade      | `broker_freetrade`  | 100      | ✅    | ✅      |
| Coinbase       | `broker_coinbase`   | 100      | ✅    | ✅      |
| Finpension     | `broker_finpension` | 100      | ✅    | ✅      |

### 📋 Future (Phase 3 - Bassa priorità)

| Plugin        | Code                   | Notes             |
|---------------|------------------------|-------------------|
| Avanza        | `broker_avanza`        | Swedish           |
| Bitvavo       | `broker_bitvavo`       | Dutch crypto      |
| Bux           | `broker_bux`           | Dutch             |
| Delta         | `broker_delta`         | Crypto tracker    |
| InvestEngine  | `broker_investengine`  | UK                |
| Investimental | `broker_investimental` | Portuguese        |
| Parqet        | `broker_parqet`        | German            |
| Rabobank      | `broker_rabobank`      | Dutch bank        |
| Relai         | `broker_relai`         | Swiss Bitcoin     |
| Saxo          | `broker_saxo`          | Danish/EU         |
| XTB           | `broker_xtb`           | Polish/EU         |
| Cointracking  | `broker_cointracking`  | Crypto aggregator |

---

## Testing Strategy

### Sample Files Location

```
backend/app/services/brim_providers/sample_reports/
```

### Current Sample Files

| File                        | Expected Plugin    | Status |
|-----------------------------|--------------------|--------|
| `directa-export.csv`        | broker_directa     | ✅      |
| `degiro-export.csv`         | broker_degiro      | ✅      |
| `trading212-export.csv`     | broker_trading212  | ✅      |
| `ibkr-trades-export.csv`    | broker_ibkr        | ✅      |
| `etoro-export.csv`          | broker_etoro       | ✅      |
| `revolut-invest-export.csv` | broker_revolut     | ✅      |
| `schwab-export.csv`         | broker_schwab      | ✅      |
| `freetrade-export.csv`      | broker_freetrade   | ✅      |
| `coinbase-export.csv`       | broker_coinbase    | ✅      |
| `finpension-export.csv`     | broker_finpension  | ✅      |
| `generic_*.csv`             | broker_generic_csv | ✅      |

### Test Execution Rules

1. **Iterate all sample files** in `sample_reports/` directory
2. **All files must parse successfully** (no exceptions)
3. **Each plugin must be called at least once** during test run
4. **Auto-detection must work** for broker-specific files

---

## Auto-Detection System

### Priority Levels

| Priority | Description                                 | Example                       |
|----------|---------------------------------------------|-------------------------------|
| 100+     | Broker-specific plugins with unique headers | broker_directa, broker_degiro |
| 50-99    | Semi-generic plugins                        | (reserved for future)         |
| 0-49     | Generic fallback plugins                    | broker_generic_csv            |

### How it works

1. When `plugin_code="auto"` (default), the parse endpoint calls `BRIMProviderRegistry.auto_detect_plugin(file_path)`
2. All registered plugins are sorted by `detection_priority` (descending)
3. Each plugin's `can_parse(file_path)` is called in order
4. First plugin returning `True` is selected
5. If none match, fallback to `broker_generic_csv`

---

## Plugin Details

### broker_directa (Directa SIM - Italy)

**Detection Patterns:**

- `Conto :` in first 10 lines
- `Data operazione`, `Tipo operazione`, `Isin`, `Importo euro` in headers

**Type Mappings:**

- Acquisto → BUY
- Vendita → SELL
- Provento etf/azioni, Dividendi, Coupon → DIVIDEND
- Cedola → INTEREST
- Conferimento → DEPOSIT
- Prelievo → WITHDRAWAL
- Rit.provento, Ritenuta, Tobin tax → TAX
- Commissioni → FEE

---

### broker_degiro (DEGIRO - Netherlands/EU)

**Detection Patterns:**

- `Datum`, `Tijd`, `ISIN`, `Omschrijving` in first line

**Type Mappings (multi-language):**

- Koop/Buy/Compra/Achat + number → BUY
- Verkoop/Sell/Venta/Vente + number → SELL
- Dividend/Dividende → DIVIDEND
- Dividendbelasting/Impôts sur dividende → TAX
- iDEAL Deposit/Ingreso → DEPOSIT
- Transactiekosten/Frais/Comissões → FEE

**Skip Patterns:**

- Valuta Creditering/Debitering (FX)
- Cash Sweep, Overboeking (internal transfers)
- Stock dividend, Corporate action

---

### broker_trading212 (Trading212 - UK/EU)

**Detection Patterns:**

- `Action`, `Time`, `ISIN`, `Ticker`, `No. of shares` in first line

**Type Mappings:**

- Market buy/Limit buy → BUY
- Market sell/Limit sell → SELL
- Deposit → DEPOSIT
- Withdrawal → WITHDRAWAL
- Dividend (Dividend) → DIVIDEND
- Interest on cash → INTEREST
- Withholding tax (separate column) → TAX

**Skip Patterns:**

- Stock split, Stock distribution
- Transfer, Currency conversion

---

### broker_ibkr (Interactive Brokers - Global)

**Detection Patterns:**

- Quoted headers: `"Buy/Sell"`, `"TradeDate"`, `"ISIN"`, `"IBCommission"`

**Type Mappings:**

- BUY → BUY
- SELL → SELL
- IBCommission → FEE (separate transaction)

**Notes:**

- FX trades (no ISIN) are skipped
- Date format: YYYYMMDD

---

### broker_etoro (eToro - Global)

**Detection Patterns:**

- `Date`, `Type`, `Details`, `Amount`, `Units`, `Realized Equity` in first line

**Type Mappings:**

- Open Position → BUY
- Position closed → SELL
- Dividend → DIVIDEND
- Interest Payment → INTEREST
- Withdraw Request → WITHDRAWAL
- Deposit → DEPOSIT

**Skip Patterns:**

- Overnight fee/refund
- Withdraw Fee, Conversion Fee
- SDRT (UK stamp duty)

**Notes:**

- Ticker extracted from Details column (e.g., `NKE/USD`)
- Currency inferred from ticker suffix

---

## Notes

1. **Encoding**: Always try `utf-8-sig` first (handles BOM), then `utf-8`, then `latin-1`
2. **Separators**: Use `_detect_separator()` for semi-colon vs comma
3. **Numbers**: Handle both US (1,234.56) and EU (1.234,56) formats
4. **Dates**: Support multiple formats (DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD, YYYYMMDD)
5. **Icons**: Each broker plugin should provide `icon_url` property with favicon URL

