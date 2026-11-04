# <img src="https://www.swissquote.com/favicon.ico" alt=""> Swissquote

!!! warning "Beta — community feedback welcome"

    This plugin was built from **sample export files** and is currently in **beta**. We're happy to receive any report to improve it or to update the documentation on how to obtain the export.

## 📥 How to Export

Export your transaction history as **CSV** from Swissquote and upload it in LibreFolio. For the step-by-step import flow, see the **[Import Guide](how-to.md)**.

## 🔄 What Gets Imported

| In the export (**Transaction**) | Imported as |
|:--------------------------------|:------------|
| Buy | **Buy** |
| Sell | **Sell** |
| Dividend | **Dividend** |
| Interest, Interests | **Interest** |
| Tax, Withholding | **Tax** |
| Custody fee, any other fee | **Fee** |
| Debit | **Withdrawal** |
| Credit | **Deposit** |
| Forex credit + Forex debit, same **Order #** | One linked **Currency Exchange** pair |

**Currency conversions.** The two legs of one conversion, a **Forex credit** and a **Forex debit**
with the same **Order #**, become two linked **Currency Exchange** transactions: the money out in one
currency and the money in in the other. Each leg keeps its own date and its own **Net Amount**.

## 📝 Notes

- Built from sample exports — some edge cases may not be covered yet.
- The costs and the accrued interest of a trade are written in its description, not imported as separate transactions.
- Rows LibreFolio does not know are listed in an amber warning, with a link to open an issue on GitHub; a second warning lists the rows it cannot read.
- Found an issue or want to document the export steps? [Open a report](../../../community/contribute.md) — contributions welcome!

## 🚧 Known limitations

- **Only a clean pair of forex legs is imported.** A forex leg is left out, and listed in the amber warning with the link to open an issue (add that conversion by hand), when:
    - its partner is missing (no other leg with the same **Order #**);
    - the order has more than two legs;
    - a leg carries **Costs** (the file does not say whether the cost is inside or outside its **Net Amount**);
    - the two legs are in the same currency, or are both credits or both debits.
- **Something is off?** Please [open a report](../../../community/contribute.md), with an anonymised example file.
