# BRIM Sample Reports

This directory contains sample broker report files for testing BRIM plugins.

## Test Files

### Generic CSV Plugin (`broker_generic_csv`)

| File                        | Description                                        | Expected Result                                 |
|-----------------------------|----------------------------------------------------|-------------------------------------------------|
| `generic_simple.csv`        | Basic CSV with all standard columns                | All rows parsed successfully                    |
| `generic_dates.csv`         | Various date formats (ISO, DD/MM/YYYY, etc.)       | All dates parsed correctly                      |
| `generic_types.csv`         | All transaction types (BUY, SELL, DIVIDEND, etc.)  | All types mapped correctly                      |
| `generic_multilang.csv`     | Mixed language headers (English, Italian, Spanish) | Headers auto-detected                           |
| `generic_with_warnings.csv` | Some invalid rows                                  | Valid rows parsed, warnings for invalid         |
| `generic_with_assets.csv`   | Transactions with asset identifiers                | Fake IDs assigned, assets classified            |
| `generic_no_asset.csv`      | No asset column - requires manual mapping          | UNKNOWN_ROW_* fake IDs for asset-required types |

## File Format

All CSV files should have headers in the first row. The plugin auto-detects
columns based on header names (case-insensitive).

### Supported Headers

| Standard Name | Accepted Variations                                 |
|---------------|-----------------------------------------------------|
| date          | date, data, settlement_date, value_date, trade_date |
| type          | type, tipo, transaction_type, operation, action     |
| quantity      | quantity, quantità, qty, shares, units              |
| amount        | amount, importo, value, cash, total, price          |
| currency      | currency, valuta, ccy                               |
| description   | description, descrizione, notes, memo               |
| asset         | asset, symbol, ticker, isin, instrument, security   |

### Supported Transaction Types

| Type       | Keywords                         |
|------------|----------------------------------|
| BUY        | buy, acquisto, purchase, compra  |
| SELL       | sell, vendita, sale              |
| DIVIDEND   | dividend, dividendo, div         |
| INTEREST   | interest, interesse, interessi   |
| DEPOSIT    | deposit, deposito, versamento    |
| WITHDRAWAL | withdrawal, prelievo, ritiro     |
| FEE        | fee, commissione, fees, charge   |
| TAX        | tax, tassa, imposta, withholding |

## Adding New Test Files

When adding a new test file:

1. Use a descriptive filename: `{plugin}_{feature}.{ext}`
2. Add an entry to this README
3. Include comments in the file if needed for context
4. Ensure the file is valid for at least one registered plugin

## Test Coverage

The test suite (`test_brim_providers.py`) verifies that:

1. Every plugin can parse at least one sample file
2. Every sample file is parsed by at least one plugin
3. Parsed transactions are valid `TXCreateItem` objects
4. Warnings are generated for problematic rows

