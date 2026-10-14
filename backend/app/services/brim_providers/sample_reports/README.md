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

### Fineco Plugin (`broker_fineco`)

| File                   | Description                                              | Expected Result                                             |
|------------------------|---------------------------------------------------------|-------------------------------------------------------------|
| `fineco-export.csv`    | Variant B (15 columns, with commission columns)         | Trades/dividends/coupons/redemptions + separate FEE rows    |
| `fineco_variant_a.csv` | Variant A (11 columns, no commission columns)           | Same operations parsed, no FEE rows (currency from Divisa)  |

### Danske Bank Plugin (`broker_danske_bank`) — report sets

Synthetic files with invented values, built on the structure of the Finnish equity savings
account exports (custody XLSX + cash CSV). A member is never parsed alone: each set is
combined first, and the combined file is parsed. The sets are declared in the plugin's
`test_sample_sets`.

| Set  | File                             | Description                                                                                                          | Expected Result                                                                                                                                      |
|------|----------------------------------|----------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| main | `danske_bank-custody.xlsx`       | Custody transactions: text dates, literal `<br/>` in the fee header, unnamed currency column, constant columns        | Role `custody`; buys, sells, identical partial fills, a `Tuotto`, a demerger (old line + two new lines), a foreign-quoted title                     |
| main | `danske_bank-cash.csv`           | Cash statement: Latin-1, `;`, newest first, running `Saldo`, labels truncated at 24 characters                         | Role `cash`; one year of history before the custody period, a border orphan, standalone deposits, fees, a withdrawal with its tax, a deferred trade |
| gap  | `danske_bank-gap-custody-1.xlsx` | First custody period                                                                                                  | Segment 1                                                                                                                                            |
| gap  | `danske_bank-gap-custody-2.xlsx` | Second custody period, two months later                                                                               | Segment 2; the last trade settles after the cash export ends (`not_yet_settled`)                                                                    |
| gap  | `danske_bank-gap-cash.csv`       | Cash statement covering both periods and the trades in between                                                        | A proven gap: an opening checkpoint and a gap checkpoint; the standalone rows of the gap are imported                                               |

### Scalable Capital plugins (`broker_scalable`, `broker_scalable_deposit`)

Synthetic files with invented values, built on the real structure: Scalable's own CSV
export (PRIME, broker only) and the two files of the LibreFolio exporter
(`Librefolio/librefolio-exporter`, version 1.0.1), one per account. References, ids and
amounts are invented; the ISINs are public securities and the IBAN is the standard
documentation example. The two exporter files mirror each other: the internal transfers
have the same dates and amounts on both sides.

| File                          | Plugin                    | Description                                                                                                                     | Expected Result                                                                                                                                                         |
|-------------------------------|---------------------------|---------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `scalable-prime-export.csv`   | `broker_scalable`         | PRIME export, 14 columns: buys (gross `amount`), a savings plan, a sell with fee and tax, a dividend with withholding, cash rows | Trades with FEE and TAX legs, gross dividend and interest with a TAX leg, a tax refund as DEPOSIT; pending, cancelled and security-transfer rows only in notices       |
| `scalable-broker-export.csv`  | `broker_scalable`         | Exporter, broker account, 23 columns: the same families, plus internal transfers, an open partial order, a reversal, a venue fee | Same mapping, ids in the descriptions; notices for the open order, the reversal, the unknown cash type, the net dividend, the trade without details, the transfers |
| `scalable-deposit-export.csv` | `broker_scalable_deposit` | Exporter, overnight account, 19 columns: interest with and without details, bank transfers, internal transfers                  | Gross interest with a TAX leg, net interest with a notice, deposits and withdrawals; each plugin refuses the other account's file                                     |


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

