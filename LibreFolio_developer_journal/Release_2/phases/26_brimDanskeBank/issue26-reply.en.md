<!-- Published on issue #26 by the developer on 2026-09-28T10:48:03Z: https://github.com/Librefolio/LibreFolio/issues/26#issuecomment-5868387443 -->

Hi @jaska087 👋

Thanks a lot for the request, and for trusting LibreFolio with your portfolio!

Your two exports taught me something I didn't expect 🤯.
I had assumed that a single bank export would be enough to import an account. Yours, together with the Crédit Agricole and Intesa Sanpaolo importers LibreFolio already has, shows that banks often split one account across several exports: one for the securities and one for the cash.
To import them properly, LibreFolio needs an importer that takes several files and combines them.

For the other two, I had come up with workarounds, but I’m realizing that they aren’t exceptions—they represent a systemic issue that deserves a proper solution.

That is a bigger piece of work than I planned, so I doubt I'll be able to release something this week. Thank you for pointing me in this direction!

A few questions first, then a short summary of what I understood.

**About the exports**

1. Which menu did you use for each file? How far back can each export go? Can you pick exactly the same period for both, and does the period filter use the trade date or the value date?
I need this information to confirm that it's feasible and, subsequently, to write the guide properly—much like I did here: https://librefolio.github.io/LibreFolio/user/transactions/import/credit_agricole/
2. Did you change the files before uploading, apart from replacing the name and the account number? For example re-saving them, or removing rows or columns.
3. Could you send the same two exports with the web bank set to English or Swedish? The header plus two made-up rows is enough.
It would be helpful for writing a plugin that handles language switching robustly right from the start; however, if you can't do it, it's not an urgent matter.

---

Could you also read the section below? It lists the column names and what I think they mean. If there are any errors, could you correct me?

**Columns I'm guessing**

1. `Tila`: can it be anything other than `Toteutunut` / `Toteutettu`, for example pending, reserved or cancelled?
2. `Tarkastus`: is it the check mark you can set yourself in the web bank? Can it ever be `Kyllä`?
3. `Palkkio sis. Alv` is always `0`: is the commission already included in `Summa`?
4. `Kurssi`: is it quoted in the currency of the market where the security trades, while `Summa` is in euros?
5. `Tuotto`: is it always a cash dividend, with `Määrä` being the number of shares you held?
6. `Jakautuminen, vanha` / `uusi`: is it a demerger? Does Danske tell you how the purchase cost is split between the new shares?
7. What other values can `Toimeksiantotyyppi` take? For example fund subscriptions, transfers or splits.
8. In the CSV, what is the 10-digit number at the end of the income rows?

**Securities and prices**

1. The XLSX only has the security name. Is there an export that includes the ISIN or the ticker, such as the holdings view or the trade confirmations?
2. **Which markets do you trade on, and where do you usually check prices**? LibreFolio prices shares through Yahoo Finance; if you normally use another source, I can look into supporting it.

### 🧾 What I understood

- **The two files are two halves of the same account** (an *osakesäästötili*?): the XLSX is the securities side, the CSV is the cash side.
- **The XLSX** has one row per buy, sell, dividend (`Tuotto`) or corporate action (`Jakautuminen`), with quantity and price.
  - Buy or sell comes from the sign of `Määrä`: `+` is a buy, `−` is a sell.
  - `Rajakurssi`, `Päivän kurssi` and `Pikakauppa` are just order types.
- **The CSV** has one row per cash movement, with the running balance. Every buy, sell and dividend in the XLSX shows up here too, as `Osto …`, `Myynti …` or the dividend credit, with the same value date and amount.
- **Only the CSV** has deposits, withdrawals (`Nosto osakesäästötililtä`), the tax on withdrawals (`Vero osakesäästötililtä`) and service fees (`Palvelumaksut`).

**The plan:**
- trades and dividends come from the XLSX;
- from the CSV, only the cash-only movements;
- that way nothing is counted twice.

That's why both exports must cover the same period: a row whose counterpart is missing from the other file would be left out.

When a first version is ready, would you like to try it on your real files? 

Thanks again! 🙏

