# 🎛️ User Preferences

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="user-preferences" alt="User Preferences">
</div>

The **Preferences** tab controls **how the app looks and behaves for you** — changes apply only to your account. Your identity (username, email, avatar, password) lives in the **[Profile](profile.md)** tab instead.

| Setting | Category | Description |
|---------|----------|-------------|
| **Language** | 🌍 Display | Interface language — 🇬🇧 English, 🇮🇹 Italiano, 🇫🇷 Français, 🇪🇸 Español. Applies as soon as you save it |
| **Default Currency** | 💰 Currency | Your own base currency, proposed when you create something new — an asset, a new broker's first cash balance, a PAC plan. This menu lists every currency |
| **Theme** | 🎨 Appearance | ☀️ Light / 🌙 Dark / 🖥️ Auto (follows your operating system) |

<style>
/* Keep the first two columns on one line (long setting names would wrap otherwise) */
article table:first-of-type th:nth-child(-n + 2),
article table:first-of-type td:nth-child(-n + 2) {
    white-space: nowrap;
    min-width: 11rem;
}
</style>

Pick a category in the sidebar — on a phone, in the **Category** menu — to show only its settings;
**All Settings** shows everything.

!!! tip "Currency menus on the Dashboard and asset pages"

    The currency menus of the **Dashboard** and of an asset page are shorter than **Default Currency**: they offer only the currencies of your FX pairs, and **Create forex…** at the bottom of the list adds a missing pair. See **[Dashboard](../dashboard/index.md)**.

## 💾 Saving, Undo, Reset

Each field keeps its own state:

- Change a field and it shows **Save** and **Undo**; the header offers **Save All** and **Undo All**
  for every changed field.
- When a saved value differs from the **instance default** (set by your administrator in
  [Global Settings](../../admin/settings.md)), an orange **Reset to Default** button appears: it
  puts the default back in the field, ready to save. **Reset All to Defaults** does it for every
  field.

---

## 🧭 Onboarding and guides {: #onboarding-and-guides }

The **Onboarding** category lists every guide, grouped by where it appears. Each one shows its
status — **Pending**, **Completed** or **Skipped** — and the version you have seen.
**New version to view** means updated content is waiting: the guide starts again the next time you
reach it.

| Group | Guides |
|---|---|
| **Setup** | Welcome setup |
| **Core tour** | Quick tour |
| **Transactions** | Transactions overview, Add transaction guide, Bulk workspace overview, Import guide |
| **Brokers** | Brokers overview, Broker guide, Broker details guide |
| **FX** | FX overview, FX guide, FX pair details guide |
| **Assets** | Assets overview, Asset guide, Asset details guide |

### 🔁 Replay a guide

- **Welcome setup** and **Quick tour** — **Replay** starts them at once.
- Any other guide — **Replay at next trigger** gets it ready: it starts the next time you open its
  page, form, wizard or workspace. **Cancel activation** takes it back.
- **Replay all** gets every guide ready and opens the Welcome page first.

A replay never changes the saved status, and guides never click or save for you. One exception: in
a Welcome replay, **Continue** saves the language, currency and picture you chose (**Exit tour**
leaves without saving).

<!-- [Screenshot Placeholder: settings/onboarding-replay — the Onboarding category of Preferences: flows grouped by area with their status badges, version lines, and Replay actions] -->

??? info "🧩 Import guide and Bulk workspace overview — guides with steps"

    Expand the row of either guide to see each step with its own status. An optional Import step
    (**Unify assets**, **Corrections**, **Duplicates**, **Align with the bank**) stays **Pending**
    until an import first needs it.

    In these two guides, **✕** skips only the current step: the next one starts when the wizard or
    the workspace reaches it. In a replay, **✕** removes the step from the replay without changing
    its saved status.

??? note "💾 Where a replay is kept — this browser only"

    A replay is kept in this browser, for your account: a half-finished one survives a reload,
    closing the browser, or logging out and back in. It is not shared with other accounts,
    browsers or devices. It ends when you finish or exit it, cancel it here, or an update brings a
    newer version of the guide — and then it closes in your other open tabs too.

If the guide list cannot be loaded, this section shows its own **Retry** button.

---

## 🙈 Privacy mode {: #privacy-mode }

Privacy mode hides how much you own while someone else can see your screen — a colleague walking
past, a shared screen, a projector. It is not a field of this tab: it is the **eye button** in the
page header, at the top right next to the theme and language buttons.

- :material-eye-outline: **Hide amounts** — amounts are visible; click to hide them.
- :material-eye-off-outline: **Show amounts** — privacy mode is on; click to show the amounts again.

The change applies at once to the page you are on, without a reload, and privacy mode stays on as
you move between pages and after a reload, until you switch it off. Not to be confused with the eye
icon of a **table toolbar**, which shows or hides table columns.

<!-- [Screenshot Placeholder: dashboard/privacy-masked — the Dashboard with privacy mode on: amounts shown as ••• with their currency and sign, percentages still visible] -->

### 🔒 What is hidden

Privacy mode replaces the **number** of an amount with `•••`. The currency always stays, and so
does the sign, so a gain still reads as a gain and a loss as a loss:

| Normally | With privacy mode |
|---|---|
| `1,234.56 € 🇪🇺 EUR` | `••• € 🇪🇺 EUR` |
| `-1,234.56 € 🇪🇺 EUR` | `-••• € 🇪🇺 EUR` |
| `€1,234.56` or `1.234,56 €` | `€•••` or `••• €` |
| `—` (no value) | `—` |

`•••` is always the same three dots — even the **K** or **M** of a shortened figure goes — so it
never gives away the order of magnitude. It covers:

- **Dashboard**, **Brokers** and the **risk panels** — their amounts: the KPI cards, Cash Balances,
  the Allocation tooltips, the broker cards and the broker detail page.
- **[Positions](../dashboard/positions.md)** and
  **[FIFO Lots Analysis](../dashboard/positions.md#fifo-lots-analysis)** — every amount except the
  prices per unit, in the tables, the Lot Detail modal and the charts, and the quantities you hold
  (the Holdings **Qty** column, the lot quantities). A partly closed lot shows its open share, for
  example `••• (60%)`.
- **Transactions** — the cash amount of every transaction.
- **[PAC allocator](../tools/pac-allocator/index.md#reading-the-result)** — every amount and
  quantity of the result, and the purchase limits of a route.

### 👀 What stays visible

Numbers that do not tell **how much you own** stay readable, so you can keep working:

- the **currency** of every hidden amount, **percentages** (returns, weights, allocation shares,
  yield on cost) and **FX rates**;
- **prices per unit** — market prices, the **Price** and **Avg. Cost** columns of Positions, the
  prices of lots and the price lines of the WAC / Market Price chart;
- **counts, dates and names**, and **asset events** such as a dividend or a split, which describe
  the asset rather than your portfolio;
- the **quantities in the Transactions list** — a deliberate choice, even though a quantity times
  the public price hints at the size of a trade;
- the numbers inside **edit fields**, for example while you add or edit a transaction: a field you
  cannot read is a field you cannot edit.

### 🌐 Where the setting is kept

Privacy mode belongs to **this browser**, not to your account: it is about the screen someone may
be looking at.

- It is off until you turn it on. Logging out or switching account leaves it as it is, and it does
  not follow you to another browser or device.
- Other LibreFolio tabs already open in this browser pick up the change when you reload them.
- If the browser blocks site storage, privacy mode still works in this tab, but may be off again
  after a reload.

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
- 🛠️ **[Settings components](../../developer/frontend/components/features/settings.md)** — How this tab and its Onboarding list are built (for developers)
