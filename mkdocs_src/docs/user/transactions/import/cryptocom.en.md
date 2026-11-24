# <img src="https://crypto.com/favicon.ico" alt=""> Crypto.com

!!! warning "Beta — community feedback welcome"

    This plugin was built from **sample export files** and is currently in **beta**. We're happy to receive any report to improve it or to update the documentation on how to obtain the export.

## 📥 How to Export

Export your transaction history as **CSV** from Crypto.com and upload it in LibreFolio. For the step-by-step import flow, see the **[Import Guide](how-to.md)**.

## 📝 Notes

- Built from sample exports — some edge cases may not be covered yet.
- **Rewards paid in a crypto asset** (staking rewards, Crypto Earn interest, card cashback) are imported as **Reward**
  transactions: the units you received, with no cash, at the value in the `Native Amount` column, in the `Native Currency`.
  That value is both their purchase cost and your income. A reward paid in a fiat currency is imported as interest.
- A reward that lists a value but no crypto amount to credit is **not imported**: a warning names its row, date and value,
  so you can add it by hand if you received it.
- A file you imported before this change had the crypto rewards as **Adjustment** transactions. Importing it again marks
  each reward as a likely duplicate of the old row, and leaves it unselected: nothing is counted twice.
- Found an issue or want to document the export steps? [Open a report](../../../community/contribute.md) — contributions welcome!
