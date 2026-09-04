# ℹ️ About

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="about" alt="About">
</div>

The **About** tab shows:

- Current LibreFolio **version**
- **License** (AGPL-3.0)
- Links to the **GitHub repository** and **documentation**
- A **system information** grid (Python version, operating system, deployment mode — Docker or local — browser, viewport, theme and language) with a **copy-for-issue** button that packs these details into a ready-to-paste bug report
- The **installed plugins**: collapsible lists of the asset price providers, FX rate providers, broker import plugins, and signal indicators detected at startup

---

## 🧩 Plugin Diagnostics

The **Plugin diagnostics** collapsible reports the health of the four plugin registries — **asset providers**, **FX providers**, **broker importers**, and **signal indicators**.

Each registry is either marked **all loaded** (green) or lists the **plugins that failed to import** (red), with the file name and the underlying error. If a provider, importer, or indicator you expected is missing from the rest of the application, this panel tells you why — a plugin that fails to load at startup is simply not registered.

---

## 📜 Changelog Modal {: #changelog-modal }

The in-app **changelog modal** renders the bundled `CHANGELOG.md`. You can reach it from two places:

- the **version number at the bottom of the sidebar** (any page), and
- the **version label right below the title of this About page** (Settings → About).

- One **foldable panel per release** — only the most recent release starts open; sections and sub-sections fold too.
- A **version index** of chips across the top: clicking a version unfolds it and scrolls straight to it.
- A **search box** that descends into the folds: matching sections auto-open, and the clickable result chips jump to the exact spot.
- **Expand-all / collapse-all** buttons, and a link to the changelog file on GitHub.

*(Screenshot `settings/changelog-modal` is not in the gallery yet.)*

### 🔄 Checking for updates

The modal header also has a **check-for-updates** button, which probes GitHub for the latest stable release. What happens next depends on your role:

- If LibreFolio is **up to date**, a confirmation toast appears.
- If a newer release exists and you are an **admin**, the **update-available modal** opens: current and latest versions side by side, with links to the [updating guide](../installation.md#updating) and the GitHub release page. You can dismiss it with **Later** (you will be reminded at the next login) or **Skip this version** (never prompted again for that release). Admins are also probed automatically at login — see [Update Notifications](../../admin/index.md#update-notifications) for the admin-side flow.
- If a newer release exists and you are **not an admin**, a dialog lists the instance **administrators** — with e-mail addresses when available, each with a mailto link and a copy button — so you know whom to ask for the upgrade. Non-admins are never probed automatically.

---

## 🔗 Related

- ⚙️ **[Settings Overview](index.md)** — General settings summary
- 👤 **[Profile](profile.md)** — Username, email, avatar, password
- 🎛️ **[User Preferences](preferences.md)** — Language, base currency, and theme
- 🛡️ **[Global Settings](../../admin/settings.md)** — Administrator options and scheduler
