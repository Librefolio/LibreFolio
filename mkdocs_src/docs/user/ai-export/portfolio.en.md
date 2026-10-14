# 🧠 Portfolio AI Export

Export your whole portfolio, as the Dashboard shows it, to ask an AI about its structure, its
performance, a recurring investment plan or your tax losses. The options and how to paste are in
the [AI Export overview](index.md).

---

## 📍 Where to Find It

On the **Dashboard**, select **AI Export** in the toolbar, next to **Refresh**. It first opens on
**Recurring Investment Plan**.

The export follows the [Dashboard](../dashboard/index.md):

- the brokers you **own** with a share above 0%, narrowed by the broker filter when it is on;
  brokers shared with you as an Editor or a Viewer are left out;
- the Dashboard currency, with the last day of its date range as the export date.

The button turns on once the Dashboard has loaded your brokers, and stays off if you own none
with a share above 0%.

---

## 📤 Export Data

| Choice | What you get |
| :--- | :--- |
| **Portfolio Overview & History** | Positions, cash, allocations, performance, flows, income, recorded costs, an economic FIFO summary, a compact market context per asset, and drawdown |
| **Portfolio Asset History** | Detailed prices, returns, indicators, states and events for each asset you hold, with coverage |

---

## 🎯 Analyses

| Analysis | What the AI does |
| :--- | :--- |
| **Recurring Investment Plan** | Plans conditional recurring investments from your figures, asking only for what it is missing |
| **Portfolio Rebalancing** | Compares your allocation with the targets you give and frames conditional rebalancing paths |
| **Portfolio Performance & Market Drivers** | Explains your result and researches dated market drivers for every asset you hold: use an AI that can search the web |
| **Capital-Loss Offset Strategies** | Explores how available or expiring tax losses might offset gains, using your FIFO lots |

??? note "📅 Recurring Investment Plan — what the AI will ask you"

    The AI starts from your data and asks only what changes the plan: how much you can invest and
    how often, your goal and horizon, how large a decline you can stand, and practical limits such
    as liquidity, brokers, minimum orders or assets to avoid. It never guesses these answers, can
    sketch conditional scenarios in the meantime, and compares investing at once with investing
    in stages.

??? note "🧾 Capital-Loss Offset Strategies — have your tax facts at hand"

    FIFO lots are LibreFolio's economic calculation, not your legal tax position. Before comparing
    paths, the AI asks for your tax residence and regime, the account type, and your official
    tax-loss inventory (for example the Italian *cassetto fiscale*) with amounts, categories and
    expiry dates. It never suggests a trade just for tax reasons.

---

## 🔗 Related

- 🧠 **[AI Export overview](index.md)** — options, pasting and privacy
- 📊 **[Dashboard](../dashboard/index.md)** — the scope this export follows
