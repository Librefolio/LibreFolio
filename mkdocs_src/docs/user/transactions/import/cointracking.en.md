# <img src="https://cointracking.info/favicon.ico" alt=""> CoinTracking

!!! warning "Beta — community feedback welcome"

    This plugin was built from **sample export files** and is currently in **beta**. We're happy to receive any report to improve it or to update the documentation on how to obtain the export.

## 📥 How to Export

Export your transaction history as **CSV** from CoinTracking and upload it in LibreFolio. For the step-by-step import flow, see the **[Import Guide](how-to.md)**.

## 📝 Notes

- Built from sample exports — some edge cases may not be covered yet.
- **Staking rewards in crypto** are imported as **Reward** transactions: the units you received, with no cash.
  The file gives no value for them: in the bulk workspace, **Fill from price history** writes the close of the asset on
  that very day, per unit, in the price's currency. A day with no stored price is left for you to fill in; the values
  can always be changed.
- A fee on a staking row is imported as a separate **Fee**, not linked to the reward.
- Found an issue or want to document the export steps? [Open a report](../../../community/contribute.md) — contributions welcome!
