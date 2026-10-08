# 🛡️ Admin Manual

This manual is for the people who install and run LibreFolio. Most administration happens from the
command line, through environment variables, or in the app's **Admin** settings tab.

---

## 📚 Guides

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

When an administrator signs in, LibreFolio checks GitHub for a newer **stable** release. If there
is one, the **New version available** window shows your version and the latest side by side, with
a **How to update** link to the [updating guide](../user/installation.md#updating) and a
**Release notes on GitHub** link.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="update-available-modal" alt="Update available modal with current and latest version">
</div>

- **Remind me later** closes the window until a later sign-in.
- **Skip this version** stops the automatic prompt for that version; a newer one is announced
  again.
- A release is announced only once its Docker image can be downloaded, and the window waits until
  no other window or guide is open.
- Without internet access, the automatic check fails silently: no error, no banner.
- To check right away, use **Check for updates** in the
  [changelog](../user/settings/about.md#changelog-modal): it reports errors, and versions you
  skipped too.

??? note "👥 Other users — when someone who is not an administrator checks"

    For users who are not administrators, no check runs at sign-in. If one of them runs
    **Check for updates** and a newer release exists, the
    **Update available — contact an administrator** dialog lists the administrators, with their
    e-mail addresses when available, so they know whom to ask.

---

## 🔐 Keep Users Signed In After a Restart {: #session-persistence }

LibreFolio signs every login session with a secret key, `JWT_SECRET`.

- **Not set** (the default): a new random key is made at every start, so everyone must log in
  again after a restart or an update.
- **Set**: sessions survive restarts. Set it also if several separate LibreFolio servers share the
  same users behind a load balancer.

### 🔑 1. Generate a key

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

No Python on the host? Run it inside the container instead:

```bash
docker exec librefolio python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 📝 2. Add it to `.env` and restart

```bash
JWT_SECRET=paste-the-generated-value-here
```

Restart LibreFolio (with Docker Compose: `docker compose up -d`). Keep the key private: whoever
knows it can forge a session.

The workers of a single `./dev.py server --workers …` share one key on their own. How long a
session lasts is the **Session Duration** in [Global Settings](settings.md). For the details, see
the developer page [Security Architecture](../developer/architecture/security.md).
