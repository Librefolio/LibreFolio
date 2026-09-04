# 🛡️ Admin Manual

This manual is for system administrators and advanced users who need to perform maintenance, manage users, or interact with the system via the command line.

## 📖 Overview

Most administrative and maintenance tasks are handled through the main command-line interface or configured via environment variables.

---

## 📚 Guides

The documentation is organized into three main areas:

### 🐳 Deployment & Exposure
- 📦 **[Host Installation](host_installation.md)**: Manual setup using Python, Node.js, and Pipenv directly on the host machine.
- 🐳 **[Advanced Docker](docker_advanced.md)**: Containerized deployment using Docker Compose, volume bindings, and user GID/UID ownership configuration.
- 🌐 **[Expose Securely](service_exposure.md)**: Securely expose your private LibreFolio instance over the internet.

### ⚙️ System Configuration
- 📝 **[Environment Variables](configuration.md)**: Full list of supported `.env` variables (`PORT`, `JWT_SECRET`, `LIBREFOLIO_DATA_DIR`, etc.) and variable resolution precedence.
- ⚙️ **[Global Settings](settings.md)**: Configure system-wide runtime settings (session TTL, upload limits, market data sync intervals).

### 🧹 Maintenance & Operations
- 🛠️ **[CLI Admin Tools](cli_tools.md)**: How to use the `dev.py` script for administrative tasks (user management, database upgrades).
- 📂 **[Filesystem Structure](filesystem.md)**: Details on where databases, logs, uploads, and temporary folders are stored, and how to perform backups.

---

## 🔔 Update Notifications {: #update-notifications }

After each login, the browser of an **administrator** checks the GitHub Releases API for a newer **stable** LibreFolio release (drafts and pre-releases are never considered). To stay unobtrusive:

- The check runs **at most once every 24 hours** — the last result is cached in the browser's local storage.
- Self-hosted installs without internet access simply fail the fetch silently: **no error, no banner**.

When a newer stable release exists, an **update-available modal** appears showing the current and latest versions side by side, with links to the **[updating guide](../user/installation.md#updating)** and to the GitHub release page. Two ways to dismiss it:

- **"Later"** — the modal closes and will prompt again at the next login.
- **"Skip this version"** — the modal never prompts for that specific version again (a future, newer version will still be announced).

Non-admin users are never probed at login. If a non-admin manually checks for updates from the [changelog modal](../user/settings/about.md#changelog-modal) and a newer release exists, they see a dialog listing the instance administrators (with e-mail addresses when available) instead, so they know whom to ask for the upgrade.


<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="update-available-modal" alt="Update available modal with current and latest version">
</div>


---

## 🔐 Authentication & Session Persistence

LibreFolio uses **JWT (JSON Web Tokens)** for user authentication. By default:
- If the **`JWT_SECRET`** environment variable is left empty in your `.env` file, the server generates a random signing secret at startup. This provides maximum security, but user sessions will be lost if the server is restarted.
- To persist sessions across server restarts (or when running multiple independent server instances behind a load balancer), define a stable **`JWT_SECRET`** key. Note that multiple uvicorn workers spawned on the same host will automatically share the parent process's generated secret, meaning session persistence is maintained across workers even when `JWT_SECRET` is left empty.

For technical details, see the developer-focused [Security Architecture](../developer/architecture/security.md) page.
