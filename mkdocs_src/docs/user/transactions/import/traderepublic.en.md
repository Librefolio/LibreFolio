# <img src="https://traderepublic.com/favicon.ico" alt=""> Trade Republic

!!! warning "Beta — community feedback welcome"

    This plugin was built from **sample export files** and is currently in **beta**. We're happy to receive any report to improve it or to update the documentation on how to obtain the export.

## 📥 How to Export

Export your transaction history as **CSV** from Trade Republic and upload it in LibreFolio. For the step-by-step import flow, see the **[Import Guide](how-to.md)**.

## 📝 Notes

- Built from sample exports — some edge cases may not be covered yet.
- **The fee and tax columns (*Kosten*, *Belasting*) are not imported yet**: the row itself is imported, and an amber warning lists the rows that have a fee or a tax, with a link to open an issue on GitHub. Add the fee or the tax by hand. The same warning lists the rows LibreFolio does not know or cannot read.
- **Not sure the net value is really net**: see [Check the net amount](#check-the-net-amount) below.
- Found an issue or want to document the export steps? [Open a report](../../../community/contribute.md) — contributions welcome!

## 🔍 Check the net amount {: #check-the-net-amount }

!!! warning "We do not know if the net value already includes the fee and the tax"

    LibreFolio imports each Buy or Sell with the column **`Waarde (netto)`** ("net value") as its
    cash. We **do not know** whether that value already contains the fee (**`Kosten`**) and the tax
    (**`Belasting`**) of the row: the developer has no recent, safe export from Trade Republic to
    check against.

    A simple example: you buy shares and Trade Republic charges a fee of 1.00 EUR.

    - **If the net value already includes the fee** (for example 101.00 EUR, of which 1.00 is the fee),
      the Buy is already right. Adding the 1.00 fee by hand, as the amber warning suggests, would
      count it **twice**.
    - **If the net value does not include the fee** (it shows 100.00 EUR), the cash of the Buy is too
      small by 1.00 EUR, and the fee has to be added by hand.

    The same reasoning applies to a Sell and to the tax.

**What to check, before adding anything:**

1. Pick one Buy or one Sell that has a fee or a tax (the amber warning lists them).
2. Compare it with your **account statement** or with the total shown by the Trade Republic app:
   does the cash that left your account (or entered it, for a sale) match what LibreFolio shows for
   that row?
3. If the two **match**, the fee is already inside: do **not** add it. If LibreFolio shows **less**
   than the real cash movement, add the **Kosten** and **Belasting** by hand as separate Fee and Tax
   transactions.

A real, **anonymised example file** would settle the question for good. If you can share one, please
[open an issue](https://github.com/Librefolio/LibreFolio/issues): we will then fix the importer and
this page.
