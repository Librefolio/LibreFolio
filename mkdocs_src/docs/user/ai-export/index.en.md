# 🧠 AI Export

AI Export copies your LibreFolio data as ready-to-paste text, with a focused question if you want
one, so you can ask the AI assistant of your choice about your portfolio, a broker, an asset or a
currency pair. LibreFolio itself never contacts an AI service.

---

## 🎯 What It Is For

- **Review with real figures**: a broker, a position, a currency pair and your exposure to it.
- **Plan**: recurring investments, a rebalancing, or how expiring tax losses might offset gains.
- **Explain**: what drove your performance, asset by asset, with dated sources.
- **Keep a snapshot**: just the facts, ready for your own question.

What you copy is factual context, not investment advice.

---

## 🚀 Open It

Select **AI Export** (:material-brain:) in the toolbar of one of these pages:

| Page | What the export covers | Guide |
| :--- | :--- | :--- |
| **Dashboard** | Your portfolio, as the Dashboard shows it | [Portfolio](portfolio.md) |
| A **Broker** detail page | That broker only | [Broker](broker.md) |
| An **Asset** detail page | That asset and, if you hold it, your position | [Asset](asset.md) |
| An **FX** detail page | That currency pair and your direct exposure to it | [FX](fx.md) |

The export is dated on the **last day of the page's date range**: move that date to export an
earlier moment.

---

## 🧭 Choose What to Export

The panel opens on a ready-to-use choice: change only what you need.

### 📤 Step 1: Choose the export type

Under **Export type**:

- **Export Data** copies only the facts: keep a snapshot, or ask your own question.
- **Request Analysis** adds a focused question, rules for checking the figures, and the
  structure of the expected answer.

### 🗂️ Step 2: Pick a dataset or an analysis

Open **Dataset or analysis**: each entry has a one-line description. Every page offers a general
data export, a detailed market history, and two to four analyses, listed in the guides above.

### 🔍 Step 3: Set the detail level

Choose **Compact**, **Standard** (the default) or **Full**. All three cover the same assets,
indicators and period; they only keep more or less history. **Full** can be very long.

### 📅 Step 4: Set the AI period

Choose **3M** (the default), **6M**, **1Y** or **Custom** (days, weeks, months or years), ending
on the export date. If LibreFolio holds less history, the export flags it as partial: it never
invents prices or uses future ones.

### 📝 Step 5: Add notes (analyses only)

With **Request Analysis**, add context or questions in **Notes for the AI**: a monthly budget, a
target allocation, what worries you. The AI reads them as information, not as new rules.

### 📋 Step 6: Copy

Select **Copy AI Export**. After **Preparing export…**, a message confirms the copy with its
estimated size.

??? warning "📏 Large prompt — when the text is long"

    The panel first shows the **Final prompt size** with a warning. Choose **Use Compact** for a
    shorter text (not shown on Compact), or **Copy Anyway**: the same settings then copy without
    asking for a while.

LibreFolio remembers your last choices on each page for a few minutes; logging out resets them.

---

## 🤖 Paste It Into Your AI Assistant

You copy plain text: a short header (what was exported, the date, period, currency and detail
level) and your data in compact tables. **Request Analysis** adds the question and the expected
answer structure around them.

1. Open a new chat in an AI assistant you trust with financial data.
2. Paste the text and send it. With **Request Analysis**, the question is already in it.
3. Answer the AI's questions: it is told to ask only for what changes the result (a budget, a
   goal, your tax situation) and never to guess it.

Good to know:

- With **Request Analysis**, the AI is asked to answer in your LibreFolio interface language and
  to keep your figures apart from its interpretation.
- The **Performance & Market Drivers** analyses need an assistant that can search the web;
  without it, the answer says so instead of inventing sources.
- Assets, brokers, currency pairs and lots appear as short codes (A1, B1, F1, L1) explained in
  the text; the AI is asked to answer with the real names.
- An analysis may suggest one more export under **Additional LibreFolio Data**, with where to
  find it. If the AI asks for it, copy that export too and paste it into the same chat.

---

## 🔒 Privacy

- LibreFolio sends the export nowhere: it only writes it to your clipboard.
- The text holds your **real figures** and the names of your brokers and assets, even while
  privacy mode is on.
- Each page exports only its own scope:
    - **Dashboard**: the brokers you own with a share above 0%, narrowed by the broker filter;
    - **Broker**: that broker only;
    - **Asset** and **FX**: every broker you can open, including brokers shared with you.
- Review the text before pasting it anywhere; a reminder appears after every copy.

---

## 🛠️ When Something Goes Wrong

- **AI Export is greyed out**: the page is still loading or, on the Dashboard, you own no broker
  with a share above 0%.
- *This selection is not applicable to the current data.*: pick another analysis.
  **Position Review** needs a position in the asset; **FX Exposure Impact** needs cash or a
  position linked to the pair.
- A message ending in *Refresh and try again.*: reload the page.
- *Clipboard access is unavailable. Check browser permissions.*: allow clipboard access for
  LibreFolio in your browser.

---

## 🔗 Related

- 🛠️ **[How AI Export works](../../developer/architecture/patterns/ai_export_snapshot.md)** — for developers
