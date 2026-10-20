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
- **Dates.** Each operation is recorded on the day you made it (**Operazione**): a purchase you
  made on the 27th is a purchase of the 27th, even if the money moves a couple of days later.
  When **Operazione** is missing, LibreFolio uses the value date (**Data valuta**).
- **Only settled operations.** An operation whose value date (**Data valuta**) is after today has
  not settled yet: typically one of the last one or two working days. It is not imported this
  time, commission included, and a blue note says how many. Nothing to do: it arrives with your
  next export, once settled, still on the day you made it.
- **Files imported with LibreFolio 1.2 or earlier.** Those versions recorded each operation on its
  value date. Imported again, the same operations now come with the day you made them, a day or
  two earlier, so LibreFolio does not recognise them as [duplicates](index.md#duplicate-detection)
  and they would count twice. So, once: delete the Fineco transactions those files created and
  import the files again, or import only the operations after the last day you already imported.
  From then on, importing a period again finds its duplicates as usual.
- **Rows with a missing number.** If a row has no quantity or no amount, LibreFolio reads it as
  it is: a missing amount counts as 0, and an operation that needs a quantity cannot be
  imported without one. A blue note lists these rows and asks you to check them. The importer
  is in beta, so it may be wrong: if the file looks right to you, use the link in the note to
  open an issue on GitHub, and we will look into it.

## 🔗 Developer Reference

→ [BRIM Architecture — Fineco notes](../../../developer/backend/brim/architecture.md#plugin-fineco)
