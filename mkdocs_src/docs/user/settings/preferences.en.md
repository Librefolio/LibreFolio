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
workspace to begin. You can cancel an armed replay before its trigger. **Replay all** arms every
flow and opens Welcome first.

!!! info "Step-managed guides"

    In an automatic Import or bulk guide, **X** skips only the current step or checkpoint. It
    does not mark the remaining steps skipped. The next due step starts when its real screen or
    milestone is encountered.

    In replay mode, exiting a step removes it only from the current browser-session replay. It
    does not change the saved **Completed** or **Skipped** status.

!!! note "Replay is non-destructive"

    Replays are scoped to your current browser session and account. Guides point at real controls
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

## 🔗 Related

- 👤 **[Profile](profile.md)** — Username, email, avatar, password, delete account
- ⚙️ **[Settings Overview](index.md)** — General settings summary
- ℹ️ **[About](about.md)** — Version info, plugins, and changelog
- 🛡️ **[Global Settings](../../admin/settings.md)** — Administrator options and scheduler
