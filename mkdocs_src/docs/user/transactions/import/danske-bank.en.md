# 📥 <img src="https://danskebank.fi/favicon.ico" alt=""> Danske Bank

!!! info "Alpha"

    This importer is in **Alpha**: it was built from the exports of a single account, shared in [issue #26](https://github.com/Librefolio/LibreFolio/issues/26). If your files look different, or a row is imported in a way that looks wrong, please tell us there.

LibreFolio imports the **equity savings account** (*osakesäästötili*) of **Danske Bank Finland**. The bank splits it into **two exports**, and neither is enough on its own:

- the **securities transactions** (XLSX): trades, dividends and demergers, with quantities and prices — but no deposits, withdrawals or balance;
- the **cash statement** (CSV): every cash movement and the balance — but no quantities.

So you upload them **together**: LibreFolio reads them as one **report set**, matches each trade with its payment and checks its balances against the bank's.

---

## 📤 What to export

| Export (name in LibreFolio) | Where in eBanking | Format | How far back |
|:--|:--|:--|:--|
| **Securities transactions** (`Transactions.xlsx`) | **Sijoitukset → Tapahtumat** | XLSX | at most **one year** per export |
| **Cash statement** | the account transactions of your equity savings account's cash account | CSV | up to **five years** |

- Securities transactions: the **whole year** the bank allows.
- Cash statement: the same period, from the day before it, and ideally **a few days past** its end — trades are paid a few business days after they are made.
- Import the files **as downloaded**, without re-saving them in Excel.

---

## 🧺 Upload both files together

1. Open the **[Import Wizard](how-to.md)**, drop **both** files in **Upload**, assign them to your Danske Bank broker and click **Next: Select Files**.
2. In **Select Files**, the two files form **one card**, already ticked: check that it reads **Complete**. A note on the card tells you what this import will do.
3. Click **Parse**: LibreFolio merges the two files into one **combined file** and analyses it as one row. Its detail, **Matching securities ↔ cash**, shows how the trades were matched with their payments, and why any row was left out.
4. Go on as usual up to **Import N transactions**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-card" alt="Danske Bank report set card in Select Files: a table per kind of export, the files' timeline and Read as in its header" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-pairing" alt="Parse detail of the set: Matching securities ↔ cash, with the outcome chips and the reasons with their number of rows" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Files uploaded together from the [Files](../../files/index.md#broker-reports) page or a broker's **Uploaded Reports** form a set too. Exports uploaded with LibreFolio 1.1.0 or earlier cannot: upload the two again, together.

### 🧩 If one file is missing

- Dropped only one file? **Next: Select Files** keeps you on **Upload**, naming the missing export and its period: drop it there — it joins the **same set** — and click **Next: Select Files** again.
- Going on without it? The card shows **A file is missing** and offers **Upload the missing file**. Meanwhile the ticked set blocks **Parse**: untick it to import your other files first.
- Files uploaded at different times **never join**: upload the missing one again with **Upload the missing file** on the right card, then delete the earlier, lone copy.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-missing" alt="Set card in Select Files showing A file is missing: the missing cash statement, the period it must cover and Upload the missing file" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🔀 How the set is read {: #how-the-set-is-read }

Normally there is nothing to change: **Read as**, in the card's header, shows **Danske Bank (detected)**. If a file does not belong in the set — say, a statement of another account uploaded by mistake — choose **Remove from the set** in its **⋮** menu: the file moves, without a plugin, under **Other files of this broker**, where you untick it. To put it back, choose *Danske Bank* in its **Plugin** column there (the choice appears once the file is ticked).

**Read the files one by one** is of no use here, since no other importer reads these exports: if you chose it, put each file back the same way. A set ticked only in part — its checkbox shows a dash — blocks **Parse**: click the checkbox once to untick the set, twice to tick it whole.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-read-as" alt="Set card with the Read as list open: Danske Bank (detected), selected, and Read the files one by one" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

<!-- [Screenshot Placeholder: brokers/import-report-set-file-menu — the ⋮ menu of the cash statement in a Danske Bank set's card: Preview, Remove from the set and Delete, with no Read alone] -->

---

## 🗓️ Import at least once a year

The securities export only goes back one year, so import **at least once a year**, each new securities export reaching back to where the previous one ended. Overlaps are fine: what LibreFolio already holds is hidden in the **Review** (*N already in LibreFolio (hidden)*) or arrives deselected as a [duplicate](index.md#duplicate-detection). Skipped more than a year? See [Gaps](#gaps).

---

## 📝 What is imported

| In your files | Imported as |
|:--|:--|
| A purchase (positive `Määrä`) and its `Osto …` payment | **Buy** |
| A sale (negative `Määrä`) and its `Myynti …` payment | **Sell** |
| `Tuotto` and its credit | **Dividend** |
| `Nosto osakesäästötililtä` | **Withdrawal** |
| `Vero osakesäästötililtä` | **Tax** |
| `Palvelumaksu…` (service fees) | **Fee** |
| `Korko…` (interest) | **Interest** |
| Any other credit (only your own money can be paid in) | **Deposit** — a notice lists them |
| `Jakautuminen, vanha` / `uusi` (a demerger) | **Adjustments** without cash — see [Demergers](#demergers) |

- Each transaction gets its **value date** (the day the money or the shares moved) and its amount in **euro**, as the bank wrote it.
- The files give no ISIN or ticker: confirm each security in the wizard's [asset mapping](index.md#asset-mapping).
- **Nothing is dropped silently**: rows left out — a missing payment, an order not executed, a trade paid after the statement ends… — are counted in the set's detail and listed in the importer's notices, in **Finnish** like the files. Check the matched trades a notice flags because their names differ.

### 💶 Fees are included in the trade amounts

The files give **one total per trade**, commission included, so the **Corrections** step asks, for every purchase and sale:

- **Separate the price from the charges?**, then **Apply correction** — for a security priced in euro, LibreFolio suggests the likely commission; the exact figure is on the trade confirmation in eBanking;
- or **Keep as recorded**: the trade keeps its whole amount (your cash is right either way).

Each trade needs a choice; **Keep the remaining N rows as read** settles the rest in one click.

### ✂️ Demergers {: #demergers }

A demerger (`Jakautuminen`) arrives as **adjustments without cash**: the old line (`vanha`) removes your old shares, each new line (`uusi`) adds new ones. In the editor, each new line needs its **cost per share** (**Save All** waits for it): the cost of your old shares × the line's percentage published by the Finnish Tax Administration ([vero.fi](https://www.vero.fi/)), divided by its number of shares.

---

## 🏁 First import: align with the bank {: #first-import-align-with-the-bank }

On the first import, everything before the first day of your securities export is summarised in a **starting point** at the end of the previous day; from then on, every movement is imported one by one. The set's card tells you the date.

After the **Review**, **Import N transactions** may open **Align with the bank**: it compares what LibreFolio will hold with what the bank states, and proposes what closes the difference — a **Deposit** or a **Withdrawal** that brings the cash to the balance of the cash statement, and an **Adjustment** for each position your files prove.

1. Cards at the top show each point — the **Starting point**, an **After the gap** point per [gap](#gaps), the [End-of-period check](#end-of-period-check). Click one to see its comparison and only its corrections; click it again to see them all.
2. The corrections, tagged `gap_fix`, are **selected by default**: untick those you don't want (or use **Select All**, **Select visible**, **Deselect All**), then click **Continue**.
3. In the editor, enter the **cost per share** of each position marked *cost to enter* — the bank's website shows each holding's average purchase price. **Save All** waits for it.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-gapfix-step" alt="Align with the bank: the Starting point, After the gap and End-of-period check cards above the proposed corrections tagged gap_fix" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

The step opens **only when there is something to show** — usually not after a yearly import that overlaps the previous one. History you entered by hand counts: only the difference is proposed. If the comparison with the bank fails, you can **Continue** without corrections.

### ✅ End-of-period check

The last card compares your cash with the statement's balance at the end of the last securities period: **Matches** or **Does not match**. It is **never corrected**: your next import brings the trades of the last days, missing from your cash until then. If it does not match, add by hand the movement the import left out (see the set's detail in **Parse**).

---

## 🕳️ Gaps between securities exports {: #gaps }

A **gap** is a period that no securities export covers while the cash statement shows trades in it — you skipped more than a year, or left a hole between two securities exports. Without quantities, those trades cannot be rebuilt:

- the gap's deposits, withdrawals, taxes, fees and interest are imported with their own date;
- its trades are summarised in the **After the gap** corrections;
- securities bought or sold in the gap must be checked on the bank's website and fixed by hand.

The set's card warns you about such a hole: if the bank still has that period, export it and upload it with the others.

---

## ⚠️ Limits {: #limits }

- **Securities that never show up**: positions are proven only by a dividend, a demerger's old line, or a sale of more shares than you bought (*at least N*). A security that did not move and paid no dividends cannot be seen: check your positions on the bank's website and add the missing ones by hand.
- **Invested capital**: a negative position correction, or a demerger's old line, removes shares without lowering your invested capital.
- **No going back in time**: a securities export older than the history LibreFolio holds for the broker is not imported; the set's card says so.
- **Earlier corrections**: if a new set covers the date of a `gap_fix` correction imported before, delete that correction after the import, as the card asks — or the cash counts twice.

## 🔗 Developer Reference

→ [Danske Bank Importer (developer reference)](../../../developer/backend/brim/danske_bank.md)
