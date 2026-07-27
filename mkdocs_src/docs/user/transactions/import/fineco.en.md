# <img src="https://finecobank.com/favicon.ico" alt=""> Fineco

!!! info "Beta"

    This plugin is in **Beta** — tested with sample files but edge cases may exist.

## 📥 How to Export

LibreFolio imports the **"Movimenti Dossier Titoli"** (securities dossier movements)
report exported from FinecoBank.

1. Log in to your **FinecoBank** account (web or app).
2. Open the **Dossier Titoli** section and select the account/period you want.
3. Export the movements list. Fineco offers the report as an Excel file.
4. If the file is `.xls`/`.xlsx`, open it and **save it as CSV** before importing — the
   plugin reads the **CSV** format.

## 📝 Notes

- Two export layouts are supported automatically:
    - **without commissions** (11 columns), and
    - **with commissions** (15 columns). Commission columns are imported as separate
      **fee** transactions.
- Supported operations: buys and sells (*Compravendita titoli*), dividends
  (*Dividendo*), bond coupons (*Stacco Cedole*), redemptions/maturities (*Rimborso*),
  and capital increases (*Aumento capitale*, imported as a quantity **adjustment**
  without cash movement).
- **Bond redeemed above par** — when a *Rimborso* row is a bond priced **above par (100)**,
  the amount credited over par (a *premio fedeltà* / inflation revaluation) is booked as a
  separate **interest** leg and the **sell** is recorded at par 100. This mirrors how coupons
  are treated (reddito di capitale) and keeps the realised gain based on price-vs-cost only.
  Bonds redeemed at or below par, and equity redemptions, are imported as a single sell.
- **Amounts are imported verbatim** in the currency reported by Fineco: the *Divisa*
  column of each row determines the currency of that row's figures. No currency
  conversion is performed and the *Cambio* (exchange rate) column is ignored — the
  numbers land in LibreFolio exactly as they appear in the report.
- The *Data valuta* (value date) is used as the transaction settlement date.

## 🔗 Developer Reference

→ [BRIM Providers — Implementation Details](../../../developer/backend/brim/providers_list.md)
