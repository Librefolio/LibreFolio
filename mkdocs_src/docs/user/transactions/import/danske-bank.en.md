# 📥 <img src="https://danskebank.fi/favicon.ico" alt=""> Danske Bank

!!! info "Alpha"

    This importer is in **Alpha**: it was built from the exports of a single account, shared in [issue #26](https://github.com/Librefolio/LibreFolio/issues/26). If your files look different, or a row is imported in a way that looks wrong, please tell us there.

LibreFolio imports the **equity savings account** (*osakesäästötili*) of **Danske Bank Finland**. The bank splits this account into **two exports**, and neither is enough on its own:

- the **securities transactions** (XLSX) hold your purchases, sales, dividends and demergers, with quantities and prices — but no deposits, no withdrawals and no balance;
- the **cash statement** (CSV) holds every movement of the account's cash, with the running balance — but no quantities.

So you upload the two files **together**. LibreFolio treats them as one **report set**: it pairs every trade with its cash movement and, at the end, checks its balances against the bank's.

---

## 📤 What to export

Danske Bank's eBanking exports these files in **Finnish**: the labels quoted on this page are the ones you will find in them.

| Export | Where in eBanking | Format | How far back | Called in LibreFolio |
|:--|:--|:--|:--|:--|
| Securities transactions (`Transactions.xlsx`) | **Sijoitukset → Tapahtumat** | XLSX | at most **one year** per export, chosen by trade date | *Securities transactions* |
| Cash statement | the account transactions of your equity savings account's cash account | CSV | up to **five years** | *Cash statement* |

**Which period?**

- **Securities transactions**: the whole year the bank lets you export.
- **Cash statement**: the same period or a longer one. It must cover the whole securities period, starting at least the day before it, and ideally run until **a few days after** it ends: a trade is paid a few business days after it is made, and LibreFolio needs that payment in the statement. If the statement stops earlier, the trades of the last days simply arrive with your next import.

Import the files **as downloaded**: don't open and re-save them in Excel first.

---

## 🧺 Upload both files together

1. Open the **[Import Wizard](how-to.md)**. In **Upload**, drop **both** files and assign them to your Danske Bank broker.
2. Files uploaded together for the same broker form one **report set**. In **Select Files** the set is one card, already ticked when you have just uploaded it. The card lists the files by kind — *Securities transactions* and *Cash statement* — each kind in a small table, its files ordered by the period they cover, with **Preview** and **Delete** in each row's **⋮** menu (a double click opens the preview too). The card's timeline shows each file as a bar, any days that no export of a kind covers between two of its files as a dashed gap, and — when LibreFolio already holds this broker's history — a grey bar up to the last day it holds: point at a bar, or click it, to read its dates and its number of rows (or, for the grey bar, of transactions already in LibreFolio). A note tells you what this import will do. Any other files you uploaded for the broker are listed below the card, under **Other files of this broker**. To read the files another way, see [How the set is read](#how-the-set-is-read).
3. **Parse** combines the two files into one **combined file** and analyses it, so the set stays a single row. Its detail (**Matching securities ↔ cash**) shows the outcome as chips — the trades paired with their cash, the rows that exist in one file only, the movements summarised in a starting point or after a gap, the trades left for your next import, the rows left out — then the reasons in a table, with their number of rows, and lets you **preview** or **download the combined file**.

Uploading from the [Files](../../files/index.md#broker-reports) page, or from a broker's **Uploaded Reports**, works the same way: the files you upload in one go form one set, which you then tick in the wizard's **Select Files**.

### 🧩 If one file is missing

Dropped only one of the two files? LibreFolio notices it as soon as you click **Next: Select Files**: it stays on **Upload** and tells you which export is missing and which period it must cover. Drop the missing file there — it joins the **same set** — and click **Next: Select Files** again.

You can also continue without it: in **Select Files** the set shows **A file is missing**, and its card offers **Upload the missing file**, which adds the file to that same set. While a ticked set is incomplete the wizard cannot parse; to import your other files first, use **Exclude from the import** on the set's card.

!!! warning "Files uploaded at different times do not join"

    A set is made of the files you upload **together**. A cash statement uploaded on its own a few days earlier forms a separate, incomplete set: it never joins the securities file automatically. Add it again with **Upload the missing file** on the right card, then delete the leftover file.

### 🔀 How the set is read {: #how-the-set-is-read }

LibreFolio reads the exports it recognises as one set. You can change that on the set's card in **Select Files**:

- **Read as**, in the card's header (visible even when the card is folded), shows how the set is read and lets you change it. It lists **Danske Bank (detected)** — the plugin that recognised the files — and **Read the files one by one**; any other plugin able to read every file of the set as a set would be listed too. Reading the files one by one dissolves the set, but it changes only *how* the files are read: each file stays ticked, or unticked, as it was. A file that a plugin can read on its own gets the best such plugin — your broker's **Default Import Plugin** first, when it can. A file that no such plugin reads gets no plugin — if it is ticked, its **Plugin** column shows *Select plugin…* — and **Parse** waits until every ticked file has a plugin.
- Each file's **⋮** menu offers **Read alone with ‹plugin›**, one entry for each plugin that can read that file on its own: the file leaves the set with that plugin, and stays ticked, or unticked, as it was. The menu also offers **Remove from the set**: the file leaves the set without being deleted and without a plugin, and it too stays ticked, or unticked, as it was — taking a file out of the set means you don't want this plugin to read it, not that you don't want the file. If it is ticked, its **Plugin** column shows *Select plugin…*, and **Parse** waits until you choose a plugin for it, or untick it. Handy, for example, for a statement of another account uploaded by mistake: remove it from the set, then untick it to import the set without it.

None of these commands ticks or unticks a file, and neither does choosing a plugin: they change only *how* the files are read, and the ticks stay as you set them.

Today only the Danske Bank plugin reads these exports: **Read alone** is never offered for them, while **Remove from the set** always is. Reading them one by one leaves both files still ticked, with no plugin: **Parse** then waits until you put them back in the set, as described below, or untick them.

A file taken out of the set joins the broker's other files, below the card, under **Other files of this broker**, ticked or unticked as it was. If it is ticked, its **Plugin** column lets you choose its plugin. If it is unticked — a file of a set you had not ticked, for example — the column shows *—*: tick it, and the column lets you choose its plugin. To put the file back in the set, choose *Danske Bank* there: the list offers every plugin that reads the file, the set's own included. After **Read the files one by one**, do this on each file: the first file you put back brings the card back, showing *A file is missing* until the other file joins it. Taking out an export the set needs makes the set incomplete (*A file is missing*), which blocks **Parse** as long as the set is ticked: put the file back, upload the missing file, or use **Exclude from the import**, as in [If one file is missing](#if-one-file-is-missing) — and if the file you took out is still ticked, choose its plugin or untick it.

The open card also tells you, at its top, when the files could be read another way. When your broker's **Default Import Plugin** could read one of them, a note says that the set is read as a set rather than with that plugin, and how to change it. When another plugin for report sets also recognises one of the files, a note names it.

**What LibreFolio remembers.** While the files are only uploaded, your choices last until you close the wizard: open it again and LibreFolio reads the files as it detects them. Once the files have been analysed (**Parse**), LibreFolio remembers how it read them: the set keeps the files it was analysed with and its plugin, a file analysed alone keeps its plugin, and a file left out of an analysed set stays out. When you open the wizard again it shows your files that way, and so does the **Report set** column of your [files](#your-files-in-librefolio). You can still change it with the same commands: your next analysis becomes the new memory.

---

## 🗓️ Import at least once a year

The securities export only goes back one year, so import **at least once a year**: each new securities export should reach back to where the previous one ended.

The periods may **overlap** — there is nothing to cut by hand:

- LibreFolio remembers from which day it holds your Danske Bank history. Rows dated before that day are **already in LibreFolio**: the **Review** hides them behind a counter (*N already in LibreFolio (hidden)*). Click **show** to list them, greyed out: they cannot be selected.
- Rows you already imported are recognised as [duplicates](index.md#duplicate-detection), as usual, and arrive deselected.
- In **Select Files** the sets of earlier imports stay in the list, unticked: each import uses the files you have just uploaded.

Skipped more than a year? See [Gaps](#gaps) below.

---

## 📝 What is imported

| In your files | Imported as |
|:--|:--|
| A purchase: a positive `Määrä` in the securities export and its `Osto …` row in the cash statement | **Buy** |
| A sale: a negative `Määrä` and its `Myynti …` row | **Sell** |
| `Tuotto` and its credit in the cash statement | **Dividend** |
| `Nosto osakesäästötililtä` | **Withdrawal** |
| `Vero osakesäästötililtä` | **Tax** |
| `Palvelumaksu…` (service fees) | **Fee** |
| `Korko…` (interest) | **Interest** |
| Any other credit to the account | **Deposit** — only your own money can be paid into an equity savings account; a notice lists these rows so you can check them |
| `Jakautuminen, vanha` / `Jakautuminen, uusi` (a demerger) | **Adjustments** without cash — see [Demergers](#demergers) |

- **Dates**: every transaction gets its **value date** — the day the money, or the shares, actually moved.
- **Amounts** are taken as they are, in euro (the account's currency): no conversion.
- **Securities by name**: the files carry only the name of each security, with no ISIN and no ticker, so confirm each one in the wizard's [asset mapping](index.md#asset-mapping).
- **Nothing is dropped silently**: a trade whose payment is not in the statement, rows that cannot be paired without guessing, a trade not paid yet (it comes with the next import), an order that was not executed… The set's detail in **Parse** counts them by reason, and the importer's notices list the rows. Like the bank's files, notices and suggestions are in **Finnish**.
- When the name of a trade in the cash statement does not match the securities export, LibreFolio still pairs the two rows if date, amount and direction match, and a notice asks you to check them.

### 💶 Fees are included in the trade amounts

Danske Bank's files give **one total per trade**: the fee column is always zero, and the commission is already inside the amount. Your cash is right either way — LibreFolio just cannot tell the commission apart on its own.

So the **Corrections** step lists every purchase and sale you are importing and asks you to decide:

- separate the commission (**Separate the price from the charges?**, then **Apply correction**): for a security priced in euro, the suggestion shows the likely commission — the difference between the amount and quantity × price; the exact figure is on the trade confirmation in eBanking;
- or **Keep as recorded**: the trade keeps its whole amount.

Every trade needs a decision before you can continue; **Keep the remaining N rows as read** settles all the remaining ones in one click.

### ✂️ Demergers {: #demergers }

A demerger (`Jakautuminen`) arrives as **adjustments without cash**: the old line (`vanha`) removes your old holding, and each new line (`uusi`) adds the new shares.

LibreFolio cannot know what the new shares cost you. In the editor each new line asks for its **cost per share**, and **Save All** stays disabled until you enter it. Work it out from the cost of your old shares and the split of the acquisition cost that the Finnish Tax Administration ([vero.fi](https://www.vero.fi/)) publishes for each demerger: the old cost × that line's percentage, divided by its number of shares.

The old line carries a warning instead: removing those shares does not lower your invested capital by itself (see [Limits](#limits)).

---

## 🏁 First import: align with the bank {: #first-import-align-with-the-bank }

On the first import of a Danske Bank broker, LibreFolio does not replay years of old movements. Everything before the first day of your securities export is summarised in a **starting point**, at the end of the previous day; from that first day on, every movement is imported one by one. The set's card in **Select Files** tells you the date.

After the **Review**, **Import N transactions** opens a new step, **Align with the bank**. It compares what LibreFolio will hold with what the bank states, and proposes the transactions that close the difference:

- a **Deposit** that brings the cash to the balance of the cash statement;
- an **Adjustment** for each position your files prove.

At the top, the step shows one card per point, in date order: the **Starting point**; an **After the gap** point after each period that no securities export covers (see [Gaps](#gaps)); and the **End-of-period check**, which reads **Matches** or **Does not match**. The card of a starting point or of an *After the gap* point shows its cash difference, how many positions differ and how many corrections it proposes. Click it to see its full comparison — what LibreFolio will hold next to what the bank states, and where the difference comes from — and only its corrections; click it again to see them all.

The corrections are listed in one table, **selected by default** and tagged `gap_fix`: untick any you don't want, or use **Select All**, **Select visible** (the rows of the page you are looking at) or **Deselect All**, then **Continue** to the editor.

Each position the step adds needs its **average cost**, marked *cost to enter*. In the editor, enter the cost per share — the bank's website shows the average purchase price of each holding. **Save All** stays disabled until every cost is filled in.

!!! info "Which positions can the files prove?"

    Neither export lists your holdings, so LibreFolio looks for rows that reveal them: a dividend (`Tuotto`) tells how many shares earned it (when no trade of that security happened in the 30 days before), the old line of a demerger tells the whole holding, and selling more shares than you bought during the period proves you held **at least** the difference — the step then shows *at least N*. A security that did not move and paid no dividends cannot be seen at all: see [Limits](#limits).

A few more things about this step:

- It appears **only when there is something to show**: a correction to propose, an end-of-period check that does not match, or a comparison that failed. On a normal yearly import that overlaps the previous one there is usually nothing to correct, and the wizard goes straight to the editor.
- **Back** returns to the Review; the corrections are worked out again the next time you click **Import N transactions**.
- Already entered some of this broker's history by hand? The comparison counts it, and only the difference is proposed.
- If the comparison with the bank fails, the broker's box shows the error, and you can **Continue** without corrections.

---

## 🕳️ Gaps between securities exports {: #gaps }

A **gap** is a stretch of time that no securities export covers while the cash statement shows trades in it — because you skipped more than a year, or because you uploaded two securities exports with a hole between them. LibreFolio cannot rebuild those trades (the cash statement has no quantities), so:

- the **deposits, withdrawals, taxes and fees** of the gap keep their own date: they come from the cash statement;
- the **trades** of the gap are summarised in the corrections proposed on the eve of the next securities export: one cash correction, plus the positions that export proves;
- the securities **bought or sold in the gap** are not rebuilt: check them on the bank's website and fix them by hand.

When two securities exports uploaded together leave a hole between them, the set's card warns you; if the bank still has that period, export it and upload it with the others.

---

## ✅ End-of-period check

**Align with the bank** also compares LibreFolio's cash with the statement's balance at the end of the last securities period. Its card, **End-of-period check**, reads **Matches**, or **Does not match** with the difference: then click it to see LibreFolio's balance next to the bank's — the list of corrections stays as it is, since the check proposes none. It is **never corrected** automatically: the next import brings the trades of the last days, and a correction there would count them twice. If it does not match, look at the rows the import left out (the set's detail in **Parse**): once you add the missing movement by hand, the balance matches.

---

## ⚠️ Limits {: #limits }

- **Securities that never show up**: a security that did not move and paid no dividends in your files cannot be seen. Check your positions on the bank's website and add the missing ones by hand.
- **Invested capital**: a negative position correction and the old line of a demerger remove shares without a cost, so your invested capital does not go down by itself.
- **Cash between imports**: until your next import, LibreFolio's cash can differ from the bank's by the trades of the last days, which arrive with that import.
- **No going back in time**: a securities export older than the history LibreFolio already holds for the broker is not imported; the set's card says so.
- **A correction inside a new period**: if a new set covers the date of a `gap_fix` correction you imported earlier, the set's card asks you to delete that correction after the import — otherwise the cash counts twice.

---

## 🗂️ Your files in LibreFolio

The [Files](../../files/index.md#broker-reports) page and a broker's **Uploaded Reports** show a **Report set** column: **Set of ‹date›** on the exports of a set, **Combined** on the file LibreFolio built from them, **Used in a combined file** on the exports already combined, **Incomplete** when a set still lacks an export, and **To re-combine** when a newer version of the importer will rebuild the combined file. The column follows how the files were last analysed (see [How the set is read](#how-the-set-is-read)): a file left out of the set, or analysed alone, shows no **Set of ‹date›** badge.

## 🔗 Developer Reference

- [BRIM Providers — Implementation details](../../../developer/backend/brim/providers_list.md)
- [Multi-report plugins (report sets)](../../../developer/architecture/patterns/brim_plugin_guide.md#report-sets)
