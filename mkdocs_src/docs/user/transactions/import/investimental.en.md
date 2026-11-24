# <img src="https://www.investimental.ro/wp-content/themes/investimental/img/favicon/favicon.ico" alt=""> Investimental

!!! warning "Beta — community feedback welcome"

    This plugin was built from **sample export files** and is currently in **beta**. We're happy to receive any report to improve it or to update the documentation on how to obtain the export.

## 📥 How to Export

Export your transaction history as **CSV** from Investimental and upload it in LibreFolio. For the step-by-step import flow, see the **[Import Guide](how-to.md)**.

## 📝 Notes

- Built from sample exports — some edge cases may not be covered yet.
- An order filled in several parts becomes **one** transaction with the whole executed quantity and amount, dated on its last fill; a warning tells you when the parts fall on different days or their numbers do not add up. Imported with an earlier version, such an order kept only its last part: delete that trade and import the file again.
- An export that starts with an order already under way (without its first rows) cannot give that order's whole quantity: the order is left out, and a warning shows what the file has (date, price, the part it shows) so that you can enter it by hand from your statement.
- Each executed order brings its **commission** as a fee linked to its trade. The export gives the commission still due on the open part of the order, so the commission of each fill is the drop of that figure; the result comes from the order log, at the order's price, and may differ slightly from your statement, so a warning asks you to check it. On sells and bonds the file writes 0, so no fee is created: if the broker charges them, add them by hand. Orders imported with an earlier version get their fees as free rows when you import the file again: link them to their trade from the selection.
- Found an issue or want to document the export steps? [Open a report](../../../community/contribute.md) — contributions welcome!
