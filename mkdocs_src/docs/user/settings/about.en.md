# ℹ️ About

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="about" alt="About">
</div>

The **About** tab shows:

- Current LibreFolio **version**
- **License** (AGPL-3.0)
- Links to the **GitHub repository** and **documentation**
- A **Support LibreFolio** card with the coffee link and the share buttons — see [Support LibreFolio](#support-librefolio) below
- A **system information** grid (Python version, operating system, deployment mode — Docker or local — browser, viewport, theme and language) with a **copy-for-issue** button that packs these details into a ready-to-paste bug report
- The **installed plugins**: collapsible lists of the asset price providers, FX rate providers, broker import plugins, and signal indicators detected at startup, followed by **Plugin diagnostics**

---

## ❤️ Support LibreFolio {: #support-librefolio }

The **Support LibreFolio** card offers two ways to help the project:

- **Buy Me a Coffee** opens the project's Buy Me a Coffee page in a new tab. The same link is in
  the page header (the coffee icon, with its label on wider screens) and in the
  **Help & Support** menu.
- Below **Or share**, one button per social network: **X**, **Reddit**, **Facebook**,
  **Instagram**, and **TikTok**.

A share button opens a **Share on …** dialog with a **Suggested message** written for that
network, in the language of the interface. Whatever the language, every message ends with the
same five hashtags: `#LibreFolio #OpenSource #SelfHosted #PortfolioTracker #PersonalFinance`.

<!-- [Screenshot Placeholder: support/social-share-modal — the Share on Reddit dialog with the Suggested title, the Suggested message ending with the five hashtags, and the Close and Copy and go buttons] -->

**Copy and go** copies the message, followed by the link to the project's public website, and
opens the social network in a new tab: LibreFolio stays open in its own tab. Each network accepts
a different amount of prepared content, and the dialog explains what to expect before you click:

| Network | What opens |
|---|---|
| **X** | A new post with the message and the project link already filled in. |
| **Reddit** | A new text post, with the **Suggested title** as its title and the message as its body. If Reddit leaves the body empty, paste the text you just copied. |
| **Facebook** | A post with the link preview only: paste the copied text into the post's message. |
| **Instagram** | Instagram itself, which cannot prepare a post from a link: choose **Create** (+), select a photo or video, then paste the copied caption. |
| **TikTok** | TikTok's upload page (sign in if asked): select your video, then paste the copied caption. |

If the text cannot be copied, the dialog says so and asks you to allow clipboard access. If the
browser blocks the new tab, the dialog says that the text is copied but the site could not be
opened, and asks you to allow pop-ups. LibreFolio never publishes anything for you: the post is
yours to review and publish on the social network.

### ☕ The donation popup {: #donation-popup }

Now and then, right after you sign in, LibreFolio shows a popup titled
**LibreFolio grows thanks to users like you!**, with the same coffee link and share buttons. It
waits until no guide and no other window is open. Counting from the last time it appeared (or
from the creation of your account, if it never has), it appears only when:

- at least 60 days have passed, or
- you have signed in at least 10 times and at least 7 days have passed.

The popup has no close button, and clicking outside it or pressing <kbd>Esc</kbd> does not
dismiss it: choose **Buy Me a Coffee**, which also closes it, or **Maybe later**. Sharing from the
popup opens the share dialog and leaves the popup open behind it.

<!-- [Screenshot Placeholder: support/donation-popup — the donation popup shown after sign-in, with Buy Me a Coffee, the five share buttons, and Maybe later] -->

---

## 🧩 Plugin Diagnostics

The **Plugin diagnostics** collapsible reports the health of the four plugin registries — **Asset**
(price providers), **FX** (rate providers), **BRIM** (broker importers), and **Signals**
(indicators) — and, below them, of the **Tools**.

Each registry is either marked **All loaded** (green) or lists the **plugins that failed to import** (red), with the file name and the underlying error. If a provider, importer, or indicator you expected is missing from the rest of the application, this panel tells you why — a plugin that fails to load at startup is simply not registered.
<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="about-plugin-diagnostics" alt="Plugin diagnostics collapsible in the About tab">
</div>

### 🧰 Tools and Tool diagnostics {: #tool-diagnostics }

Below the registries, the **Tools** panel lists the catalogue of [Tools](../tools/index.md). It is
read-only — no calculation, probe, or repair is run — and it loads only when you open
**Plugin diagnostics**; **Reload** reads it again. For each tool you see its name and description,
a **Documentation** link, its code and `Version: <contract_version>`, and whether a compatible
interface is included in the frontend you are running. The implementation version is not shown
here, and the `Backend/API · UI` version pair appears only on the cards of the Tools page and in the
header of an open tool.

Open **Tool diagnostics** to load a snapshot of the server process that answered:

- the **Snapshot scope** and the **API process identifier**;
- the **Execution pool snapshot**: whether the pool is available, the active, queued, pending,
  completed, and failed jobs, and the degraded lanes;
- the **Tools loaded in this API process**, each with its name, code, and contract version, and
  any **Discovery failures**;
- the **Effective platform limits**, in a collapsible of their own.

The snapshot describes one server process, not the whole instance, and does not update by itself:
reload it to read it again. The [Tools overview](../tools/index.md) explains how to read these
counters.

<!-- [Screenshot Placeholder: settings/about-tool-diagnostics — the Tools panel inside Plugin diagnostics, with the PAC allocator entry and the Tool diagnostics collapsible open] -->


---

## 📜 Changelog Modal {: #changelog-modal }

The in-app **changelog modal** renders the bundled `CHANGELOG.md`. You can reach it from two places:

- the **version number at the bottom of the sidebar** (any page), and
- the **version label right below the title of this About page** (Settings → About).

- One **foldable panel per release** — only the most recent release starts open; sections and sub-sections fold too.
- A **version index** of chips across the top: clicking a version unfolds it and scrolls straight to it.
- A **search box** that descends into the folds: matching sections auto-open, and the clickable result chips jump to the exact spot.
<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="changelog-modal-search" alt="Changelog modal search opening the matching folds">
</div>

- **Expand-all / collapse-all** buttons, and a link to the changelog file on GitHub.


<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="changelog-modal" alt="Changelog modal with foldable releases and search">
</div>


### 🔄 Checking for updates

The modal header also has a **Check for updates** button. It asks the server which version is
running, reads the latest **stable** release from GitHub again (instead of reusing the result
that the automatic check keeps for an hour), and compares the two. A newer release counts only
once its Docker image is available on the registry, so a release whose build is still in progress
is not offered yet — see [Update Notifications](../../admin/index.md#update-notifications).

A check started here always tells you how it went:

- If LibreFolio is **up to date**, a confirmation toast appears, with the version detected online.
- If GitHub has **no stable release**, or a newer release's **Docker image is not available yet**,
  a warning says so.
- If the check **fails** — for example when GitHub or the registry cannot be reached — an error
  asks you to try again. A failed check never reports that you are up to date.
- If a newer release exists and you are an **admin**, the **New version available** modal opens at
  once, on top of the changelog: current and latest versions side by side, with **How to update**
  (the [updating guide](../installation.md#updating)) and **Release notes on GitHub**. You can
  dismiss it with **Remind me later** (you will be reminded at the next login) or
  **Skip this version** (the automatic check never prompts again for that release; a check started
  here still shows it). Admins are also probed automatically at login — see
  [Update Notifications](../../admin/index.md#update-notifications) for the admin-side flow.
- If a newer release exists and you are **not an admin**, the **Update available — contact an administrator** dialog lists the instance **administrators** — with e-mail addresses when available, each with a mailto link and a copy button — so you know whom to ask for the upgrade. Non-admins are never probed automatically.

---

## 🔗 Related

- ⚙️ **[Settings Overview](index.md)** — General settings summary
- 👤 **[Profile](profile.md)** — Username, email, avatar, password
- 🎛️ **[User Preferences](preferences.md)** — Language, base currency, and theme
- 🛡️ **[Global Settings](../../admin/settings.md)** — Administrator options and scheduler
