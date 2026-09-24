# 🎛️ User Preferences

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="user-preferences" alt="User Preferences">
</div>

The **Preferences** tab controls **how the app looks and behaves for you** — changes apply only to your account. Your identity (username, email, avatar, password) lives in the **[Profile](profile.md)** tab instead.

| Setting | Category | Description |
|---------|----------|-------------|
| **Language** | 🌍 Display | Interface language — 🇬🇧 English, 🇮🇹 Italiano, 🇫🇷 Français, 🇪🇸 Español. Applies immediately |
| **Base Currency** | 💰 Currency | Default display currency for portfolio values |
| **Theme** | 🎨 Appearance | ☀️ Light / 🌙 Dark / 🖥️ Auto (follows your operating system) |

<style>
/* Keep the first two columns on one line (long setting names would wrap otherwise) */
article table:first-of-type th:nth-child(-n + 2),
article table:first-of-type td:nth-child(-n + 2) {
    white-space: nowrap;
    min-width: 11rem;
}
</style>

Use the **category sidebar** on the left to filter the visible settings.

## 💾 Saving, Undo, Reset

Each field tracks its own state:

- A modified field shows **save** and **undo** buttons; the header offers **save all** / **undo all** for bulk actions.
- Fields whose value differs from the **instance default** (set by the administrator in [Global Settings](../../admin/settings.md)) are highlighted as non-default; the **reset** button restores the instance default for that field, and **reset all** restores every field at once.

---

## 🧭 Onboarding and guides {: #onboarding-and-guides }

The **Onboarding** category shows all **15 independently versioned flows**. They are grouped by
where they appear:

| Group | Flows |
|---|---|
| **Setup** | Welcome setup |
| **Core tour** | Quick navigation tour |
| **Transactions** | Transactions overview, Add Transaction, bulk workspace, Import Wizard |
| **Brokers** | Brokers overview, Add Broker, broker details |
| **FX** | FX overview, Add Pair, pair details |
| **Assets** | Assets overview, Add Asset, asset details |

Each flow has a **Pending**, **Completed**, or **Skipped** badge and a
**Seen vX · current vY** line. **New version to view** means newer content is due even when the
earlier version was completed or skipped; the flow reopens at the newer version when its trigger
is reached.

**Import Wizard** and **bulk workspace** are each one step-managed flow with individually saved
steps. Expand either row to see its **N/M** progress and the status of each step. Optional Import
steps (**Unify Assets**, **Corrections**, and **Duplicates**) stay pending until a real import
first encounters them; they are not silently completed when an earlier import does not need
them.

For **Welcome setup** and **Quick tour**, **Replay** starts immediately. Contextual flows use
**Replay at next trigger**: open the matching page, Add form, detail page, Import Wizard, or bulk
workspace to begin. If you leave a page or detail page mid-guide, its guide resumes at the same
step when you return; closing an Add form mid-guide restarts that form's guide from its first
step. You can cancel an armed replay before its trigger. **Replay all** arms every flow and opens
Welcome first.

!!! info "Step-managed guides"

    In an automatic Import or bulk guide, **X** skips only the current step or checkpoint. It
    does not mark the remaining steps skipped. The next due step starts when its real screen or
    milestone is encountered.

    In replay mode, exiting a step removes it only from the replay stored in this browser for
    your account. It does not change the saved **Completed** or **Skipped** status.

!!! note "Replay is non-destructive"

    Replays are saved in this browser for your account: an armed or unfinished replay carries over
    to other tabs and survives closing the tab or restarting the browser, but it is not shared with
    other browsers or devices. Logging out cancels it, including when LibreFolio signs you out
    because your session expired, and so does switching account; when it ends in one tab, it also
    closes in your other open tabs. Guides point at real controls
    but do not click or write for you. A Welcome replay has one explicit exception:
    **Continue** saves the language, base currency, and avatar you selected while preserving the
    Welcome flow's onboarding status.

An onboarding refresh or bootstrap failure keeps the Dashboard available with an inline
**Retry** banner only when LibreFolio already has a cached terminal Welcome state
(**Completed** or **Skipped**) for your signed-in account. Without that cache — including on the
first load or while Welcome is **Pending** — startup stays blocked and offers **Retry** and
**Log out**. A user-settings failure also blocks startup. If this section has no flow list to
retain, it shows its own **Retry** button.

---

## 🙈 Privacy mode {: #privacy-mode }

Privacy mode hides how much you own while someone else can see your screen — a colleague walking
past, a shared screen, a projector. It is not a field of this tab: it is the **eye button** in the
page header, at the top right next to the theme and language buttons.

- :material-eye-outline: **Hide amounts** — amounts are visible; click to hide them.
- :material-eye-off-outline: **Show amounts** — privacy mode is on; click to show the amounts again.

The change applies at once to the page you are on, in both directions, without a reload. Privacy
mode then stays on as you move between pages and after a reload, until you switch it off.

!!! tip "Two different eye icons"

    The eye icon in a **table toolbar** is a different control: it shows or hides table columns.

### 🔒 What is hidden

Privacy mode replaces the **number** of an amount with `•••`. The currency always stays, and so
does the sign, so a gain still reads as a gain and a loss as a loss:

| Normally | With privacy mode |
|---|---|
| `1,234.56 € 🇪🇺 EUR` | `••• € 🇪🇺 EUR` |
| `-1,234.56 € 🇪🇺 EUR` | `-••• € 🇪🇺 EUR` |
| `€1,234.56` or `1.234,56 €` | `€•••` or `••• €` |
| `—` (no value) | `—` |

`•••` is always the same three dots, whatever the size of the amount — even the **K** or **M** of
a shortened figure disappears — so it does not give away the order of magnitude. Where it
applies:

- **Dashboard** — every amount in the KPI cards and in Cash Balances, and the amounts in the
  Allocation panel's tooltips.
- **[Positions](../dashboard/positions.md)** — in the Holdings table and map and in the
  Performance table, every amount except the prices per unit (**Value**, **Unrealized P&L**,
  **Δ1** and the others), and the **Qty** column of the Holdings table.
- **[FIFO Lots Analysis](../dashboard/positions.md#fifo-lots-analysis)** — in the lots table and
  the Lot Detail modal: values, P&L, income, proceeds, fees and taxes, and the open and original
  quantity of each lot. A partially closed lot shows its open share instead, for example
  `••• (60%)`. In the charts: the axis of the Value / Return comparison whenever it shows money,
  the quantity on the Lot Life & Custody bars, and the amounts and quantities in the tooltips.
- **Brokers** — the value, gain or loss, and every cash balance on the broker cards and on the
  broker detail page; the panels the detail page shares with the dashboard behave as they do
  there.
- **Risk panels** — the amounts.
- **Transactions** — the cash amount of every transaction.

### 👀 What stays visible

Privacy mode hides what would tell someone **how much you own**. Numbers that do not reveal it
stay readable, so you can keep working:

- the **currency** next to every hidden amount;
- **percentages** — returns, P&L %, weights, allocation shares, yield on cost;
- **prices per unit** — market prices, the **Price** and **Avg. Cost** (WAC) columns of Positions,
  the opening and closing prices of lots, and the price lines of the WAC / Market Price chart;
- **FX rates**;
- **counts, dates and names** — for example the number of transactions of an asset;
- **asset events**, such as a dividend or a split, on the asset pages: they describe the asset
  itself, not your portfolio;
- the **quantities in the Transactions list** — a deliberate choice: there, a quantity multiplied
  by the asset's public price still gives an idea of a trade's size;
- the numbers inside **edit fields**, for example while you add or edit a transaction: a field
  you cannot read is a field you cannot edit.

### 🌐 Where the setting is kept

Privacy mode belongs to **this browser**, not to your account: it describes the screen someone may
be looking at, not who is signed in.

- It is off until you first turn it on, and it stays as you left it when you come back in this
  browser.
- Logging out or signing in with another account does not change it: whoever uses this browser
  finds it as you left it.
- It does not follow you to another browser or device, and it is not saved on the server.
- Other LibreFolio tabs already open in this browser pick up the change when you reload them.
- If the browser refuses to store the setting (for example when site storage is blocked), privacy
  mode still works in this tab, but may be off again after a reload.

!!! warning "What privacy mode does not cover"

    - **[AI Export](../ai-export/index.md)** copies the real figures to the clipboard even while
      privacy mode is on. Review the text before you share it.
    - **Downloads and exported files** contain the real figures.
    - It hides what is **drawn on the screen**. The figures still reach your browser, so it is not
      protection against someone who can use your device or its developer tools.
    - Some figures can still be **worked out**: the sign tells a gain from a loss, and when you hold
      a single unit of an asset, its visible price is its value.

---

## 🔗 Related

- 👤 **[Profile](profile.md)** — Username, email, avatar, password, delete account
- ⚙️ **[Settings Overview](index.md)** — General settings summary
- ℹ️ **[About](about.md)** — Version info, plugins, and changelog
- 🛡️ **[Global Settings](../../admin/settings.md)** — Administrator options and scheduler
