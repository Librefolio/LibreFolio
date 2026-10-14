# 📥 <img src="https://finecobank.com/favicon.ico" alt=""> Fineco

!!! info "Beta"

    This plugin is in **Beta** — tested with sample files but edge cases may exist.

LibreFolio imports FinecoBank's **Movimenti Dossier Titoli** report — the movements of your
securities dossier — saved as CSV.

## 📥 How to Export

1. Log in to your **FinecoBank** account (web or app).
2. Open the **Dossier Titoli** movements and choose the account and the period you want.
3. Export the list: Fineco gives you an Excel file.
4. Open it and **save it as CSV**. Keep the lines above the table (**Dossier:**,
   **Intestatario:**) and the column names: LibreFolio recognises the report by them.

## 🔄 What Gets Imported

| In the report (**Descrizione**) | Imported as |
|:--------------------------------|:------------|
| *Compravendita titoli*, with **Segno** `A` or `V` | **Buy** or **Sell** |
| *Dividendo* | **Dividend** |
| *Stacco Cedole* | **Interest** (bond coupon) |
| *Rimborso* | **Sell** (redemption or maturity) |
| *Aumento capitale* | **Adjustment** of the quantity, without cash |
| Commission columns, when the report has them | One separate **Fee** per row, in euro |

Any other operation is skipped with a warning.

**Bonds repaid above par.** When a bond is repaid above par (100) — a *premio fedeltà* or an
inflation revaluation — the sale is recorded at par and the amount above it as a separate
**Interest**, like a coupon, so your gain reflects the price alone. LibreFolio recognises bonds by
their name (BTP, BOT, CCT…). Bonds repaid at or below par, and other redemptions, stay a single
**Sell**.

## ⚠️ Good to know

- **Both layouts work**, with or without the commission columns: LibreFolio tells them apart on its
  own.
- **Amounts as written.** Each row keeps its own currency (**Divisa**), with no conversion; the
  **Cambio** column is ignored.
- **Dates.** LibreFolio uses the value date (**Data valuta**), or the trade date when it is missing.

## 🔗 Developer Reference

→ [BRIM Architecture — Fineco notes](../../../developer/backend/brim/architecture.md#plugin-fineco)
