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

The **Onboarding** category groups together the **welcome setup**, the **quick tour**, and the
**contextual import guide** — the screens new accounts see once, on their own. From here you can
check their status and replay any of them without changing that status. Guide replays do not
write app data; the Welcome replay saves only the preferences you explicitly submit.

| Column | Meaning |
|---|---|
| **Flow name** | *Welcome setup*, *Quick tour*, or *Import guide*. |
| **Status badge** | **Pending** (never completed or skipped), **Completed**, or **Skipped**. |
| **Update available** | Shown when LibreFolio ships a newer version of that guide's content than the one you last went through. |
| **Seen vX · current vY** | The content version you last completed or skipped, versus the version currently shipped. |

For each flow, a **Replay** button restarts it:

- **Welcome setup** and **Quick tour** replay immediately, taking you to the welcome page or
  opening the tour's three-phrase narrative intro. From that intro, press **Start** or wait for
  the one-shot automatic start after 10 seconds.
- **Import guide** instead shows **Replay on next import** — clicking it doesn't launch anything
  now; it arms the guide at **Upload** for the *next* time you open the Import Wizard (shown as a
  **Ready for next import** badge until then).

A **Replay all** button in the header queues every flow at once and takes you to the welcome
page, so the whole sequence — welcome, narrative intro and tour, then the import guide on your
next import — runs again end to end. If you change the Welcome language and continue, that locale
is saved through the normal user-settings update and active before the intro appears; the
Welcome flow's existing **Completed** or **Skipped** status stays unchanged.

!!! info "Guide controls and non-writing previews"

    In an automatic pending quick tour or import guide, the coachmark's top row contains **Skip
    permanently** and **X**. In replay mode, that first action is **Exit replay** instead. The
    footer uses **Back**, **Next**, and **Finish** on the quick tour's last step. Only the
    automatic pending flow's **Finish** or **Skip permanently** changes its saved status; replay
    **Finish** and **Exit replay** only clear the session replay state.

    The Broker, FX, and Asset screens opened by the tour are previews only and cannot save.
    **X** suspends without ending the replay: the quick tour keeps its current position, while
    the import guide resets its next entry to **Upload**. There is no Pause button. The guide
    never restores a wizard draft, clicks controls, uploads a file, or presses **Save All** for
    you.

!!! note "Replay is non-destructive"

    Replay state is scoped to your current browser session and account. Finishing or exiting a
    quick-tour or import-guide replay never calls complete/skip and never changes the flow's
    **Completed** or **Skipped** status. A Welcome replay has one explicit exception: **Continue**
    can save the language, base currency, and avatar you selected through the normal
    user-settings update, while still preserving its onboarding status. **Exit replay** saves
    nothing.

If your onboarding status fails to load and no earlier flow list is available, this section shows
a **Retry** button instead of the flow list.

---

## 🔗 Related

- 👤 **[Profile](profile.md)** — Username, email, avatar, password, delete account
- ⚙️ **[Settings Overview](index.md)** — General settings summary
- ℹ️ **[About](about.md)** — Version info, plugins, and changelog
- 🛡️ **[Global Settings](../../admin/settings.md)** — Administrator options and scheduler
