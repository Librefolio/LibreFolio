# <img src="https://www.investimental.ro/wp-content/themes/investimental/img/favicon/favicon.ico" alt=""> Investimental

!!! warning "Beta — community feedback welcome"

    This plugin was built from **sample export files** and is currently in **beta**. We're happy to receive any report to improve it or to update the documentation on how to obtain the export.

## 📥 How to Export

Export your transaction history as **CSV** from Investimental and upload it in LibreFolio. For the step-by-step import flow, see the **[Import Guide](how-to.md)**.

## 📝 Notes

- Built from sample exports — some edge cases may not be covered yet.
- An order filled in several parts becomes **one** transaction with the whole executed quantity and amount, dated on its last fill; a warning tells you when the parts fall on different days or their numbers do not add up. Imported with an earlier version, such an order kept only its last part: delete that trade and import the file again.
- An export that starts with an order already under way (without its first rows) cannot give that order's whole quantity: the order is left out, and a warning shows what the file has (date, price, the part it shows) so that you can enter it by hand from your statement.
- Found an issue or want to document the export steps? [Open a report](../../../community/contribute.md) — contributions welcome!
