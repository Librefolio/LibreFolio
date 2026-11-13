# BRIM Sample Reports

Sample broker report files for testing BRIM plugins.

**Where they are.** Each plugin keeps its own samples in `brim_providers/<plugin>/sample_reports/` (a sample belongs to the plugin
whose `test_file_patterns` match its file name; the Generic CSV plugin owns the `generic_*` files). This folder, at the root of the
family, keeps what belongs to no plugin: this README and `malformed/`, the deliberately broken fixtures. The tests reach them all as one
folder through `backend/test_scripts/brim_samples.py` (`SampleDir`).

**Where they come from.** Almost all are synthetic (invented values on the real column layout). Two are the public samples of the
[Export-To-Ghostfolio](https://github.com/dickwolff/Export-To-Ghostfolio) project, which is licensed under Apache-2.0 (compatible with the
AGPL-3.0 of LibreFolio): `broker_degiro/sample_reports/degiro-export.csv` and `broker_traderepublic/sample_reports/traderepublic-export.csv`.
Their provenance and licence are in `THIRD_PARTY_LICENSES.md`. Do not add a file taken from a real account or from a source whose licence
is not written down here.

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
| `fineco_btp_market.csv`, `fineco_btp_placement.csv` | Variant B, bond trades with commissions | BUY (Controvalore minus commission) + separate FEE rows |
| `fineco_variant_a.csv` | Variant A (11 columns, no commission columns)           | Same operations parsed, no FEE rows (currency from Divisa)  |

In the Variant-B samples the **Controvalore** of a trade already includes the commission (purchase) or has it taken off (sale), as in a real Fineco export (discussion #49): `Prezzo` = `Controvalore` / `Quantita` on euro rows.

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

### Crédit Agricole Plugin (`broker_credit_agricole`) — report sets

Synthetic files with invented values, built on the structure of the two Italian exports (securities movements and
account movements). A member is never parsed alone: each set is combined first, and the combined file is parsed. The sets
are declared in the plugin's `test_sample_sets`.

| Set  | File                                  | Description                                                                                                     | Expected Result                                                                                                                              |
|------|---------------------------------------|-----------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| main | `credit_agricole-securities.csv`      | Securities movements, newest first: a transfer before the opening, coupons, a placement, a fund, a maturity     | Role `securities`; one row with no account counterpart (`no_counterpart`)                                                                    |
| main | `credit_agricole-account.xlsx`        | Account movements with the header (opening and closing balance, period); the balances add up                    | Role `account`; pairs by value date, a coupon of the account alone, an opening checkpoint with its position, a closing verification         |
| gap  | `credit_agricole-gap-securities.xlsx` | Securities movements of three periods                                                                           | Role `securities`; a coupon inside the month no account export covers (`in_gap`)                                                             |
| gap  | `credit_agricole-gap-account-1.xlsx`  | Account movements of May-June, with its header                                                                  | Role `account`; segment before the hole                                                                                                      |
| gap  | `credit_agricole-gap-account-2.xlsx`  | Account movements of August, with its header; the opening balance differs from the first file's closing balance | A hole in July: a `gap` checkpoint (a proposed cash correction at its end)                                                                   |

The older `credit_agricole-export.*` (securities) and `credit_agricole-conti*.*` (account) files are not a matching pair:
they stay as fixtures for the tests of single rows (unknown causali, unreadable amounts, the dates of the rows).

`credit_agricole-conti-contract.csv` (account) and `credit_agricole-securities-contract.csv` (securities, one transfer from
another dossier that pairs with nothing and raises no cash) form the set of the E2E spec `tx-import-ca-contract.spec.ts`:
the account rows raise every channel of the plugin → wizard contract (notices, field todos, split hints, asset advisory),
the securities member is there because a set needs both exports and is chosen to change none of them.

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

### Trade Republic Plugin (`broker_traderepublic`)

The two `traderepublic-transactions*` files are synthetic, with invented values, built on the structure of a real
«Transaction export» (23 columns, Trade Republic's own CSV since April 2026). No row of the user's file is in them: ids,
amounts, the counterparty and its IBAN are invented; the ISINs are public securities. `traderepublic-export.csv` is the older
Dutch 8-column CSV, the sample of the Export-To-Ghostfolio project (Apache-2.0, see above), written by the community tool pytr.

| File                                   | Description                                                                                                            | Expected Result                                                                                                     |
|----------------------------------------|------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| `traderepublic-transactions.csv`       | Transaction export as written (`,`, every cell quoted): interest with withholding, stamp duty, a tax refund, buys and a sell of a fund, a stock and a crypto with fee and tax, an evening trade (`datetime` on the day before `date`), an instant transfer in | 15 transactions: each `amount`, `fee` and `tax` column its own leg, dated by `date`; the refund as INTEREST with an info note |
| `traderepublic-transactions-excel.csv` | The same rows as Excel saves them back: each line one quoted cell, inner quotes doubled, CRLF                         | The same 15 transactions                                                                                            |
| `traderepublic-export.csv`             | Dutch 8-column CSV (`;`), with three later English rows                                                                | 9 transactions; the two rows with a fee listed (fee and tax not imported)                                           |


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

