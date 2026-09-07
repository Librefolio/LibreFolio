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

## 🔗 Related

- 👤 **[Profile](profile.md)** — Username, email, avatar, password, delete account
- ⚙️ **[Settings Overview](index.md)** — General settings summary
- ℹ️ **[About](about.md)** — Version info, plugins, and changelog
- 🛡️ **[Global Settings](../../admin/settings.md)** — Administrator options and scheduler
