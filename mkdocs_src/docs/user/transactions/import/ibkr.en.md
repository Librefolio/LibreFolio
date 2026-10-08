# <img src="https://www.interactivebrokers.com/favicon.ico" alt=""> Interactive Brokers (IBKR)

!!! info "Beta"

    This plugin is in **Beta** — tested with sample files but edge cases may exist.

## 📥 How to Export

LibreFolio reads the trades of an **Activity Flex Query** exported as CSV. The standard
**Activity Statement** is not supported.

1. Log in to the [Interactive Brokers Client Portal](https://www.interactivebrokers.com) and open
   **Flex Queries**, in the reports menu.
2. Create an **Activity Flex Query** with only the **Trades** section, and select the fields that
   give these columns: `Buy/Sell`, `TradeDate`, `ISIN`, `Quantity`, `TradeMoney`,
   `CurrencyPrimary`, `IBCommission`, `IBCommissionCurrency`.
3. Choose **CSV** as the format and `yyyyMMdd` as the date format (for example `20240315`), then
   save the query.
4. Run it for the period you want and download the file.

## ⚠️ Common Pitfalls

- **The first line must be the column names.** LibreFolio recognises the file by the quoted
  `Buy/Sell`, `TradeDate`, `ISIN` and `IBCommission` headers on its first line: keep column
  headers on, and leave header and trailer records and section codes off.
- **CSV only**: PDF and XML exports are not read.

## 📝 What Is Imported

- **Buys and sells** of instruments with an ISIN, in the trade's currency (`CurrencyPrimary`;
  USD when the column is empty).
- **Commissions**, each as a separate **Fee** on the same asset and date, in
  `IBCommissionCurrency` (or the trade's currency when that column is empty).
- **Not imported**: dividends, interest, taxes, deposits and withdrawals, currency conversions
  (rows without an ISIN are skipped with a warning) and corporate actions. Add them by hand, or
  with a [Generic CSV](generic-csv.md) file.
