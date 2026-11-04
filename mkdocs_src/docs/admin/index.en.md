# 🛡️ Admin Manual

This manual is for the people who install and run LibreFolio. Most administration happens from the
command line, through environment variables, or in the app's **Settings › Administration** tabs.

---

## 📚 Guides

### 🐳 Deployment & Exposure
- 📦 **[Host Installation](host_installation.md)**: Manual setup using Python, Node.js, and Pipenv directly on the host machine.
- 🐳 **[Advanced Docker](docker_advanced.md)**: Containerized deployment using Docker Compose, volume bindings, and user GID/UID ownership configuration.
- 🌐 **[Expose Securely](service_exposure.md)**: Securely expose your private LibreFolio instance with Tailscale, no router port opened: why it beats port forwarding, and the private levels, a VPN for your own devices or a subnet router for your whole home network.
    - 🌍 **[Expose Securely: Public Access with Funnel](service_exposure_funnel.md)**: A public HTTPS address with Tailscale Funnel: enabling Funnel and the ACLs, one address for LibreFolio, or one for each service with Docker.
- 🔍 **[Check Connection Security](connection_checks.md)**: Verify that your users connect securely: the checklist, the indicator, the server's view and the session cookie, and what to do when a check fails.
    - 🧰 **[Check Connection Security: Behind a Reverse Proxy](connection_proxy.md)**: Run LibreFolio behind Nginx, Caddy, Traefik or Tailscale: the headers to send, the proxy LibreFolio trusts and the visitor's address.
- 🏢 **[Hosting for Others](hosting_providers.md)**: Run LibreFolio for other people: the managed profile, the initial administrator, how to block an instance, backups for your hosting panel, the upload limit of a restore and your legal pages.
- 💤 **[Sleep and Wake](sleep_wake.md)**: Let an unused Fly.io machine suspend itself, check that it works, and see how a price provider that answers «too many requests» is paused.
    - ⏰ **[Sleep and Wake: Scheduled Wake-up](wake_sync.md)**: Wake the instance on a schedule: a hosting panel or a cron job calls one route with a token, and prices and exchange rates are brought up to date.

### ⚙️ System Configuration
- 📝 **[Environment Variables](configuration.md)**: Create the `.env` file and read the main supported variables (`PORT`, `JWT_SECRET`, `LIBREFOLIO_DATA_DIR`, etc.), with the precedence that decides which value wins.
    - 🔐 **[Configuration: Secrets and Plugin Settings](configuration_secrets.md)**: Secrets and how to read them from files such as Docker secrets, the instance key, and the settings and API keys of the plugins.
    - 🛡️ **[Configuration: Checks and Protections](configuration_security.md)**: What LibreFolio checks at startup, the Content-Security-Policy and frame protection, and how the server stops.
    - 👥 **[Configuration: Accounts and Asset Search](configuration_accounts.md)**: Who can sign up, the limits on accounts and failed sign-ins, the initial administrator, and the order of the price providers in the asset search.
- 📧 **[Email](email.md)**: Optional SMTP email: the variables, examples for the usual servers, and the **Email** tab of Settings › Administration with its test email.
    - 📬 **[Email: Links and Messages](email_flows.md)**: The emails with a link, invitations and password resets, forgotten passwords and their limits, email verification and the notice of an email change.
    - 🛠️ **[Email: When It Does Not Work](email_troubleshooting.md)**: The errors, what the log says, and the security notes of the SMTP setup.
- ⚙️ **[Global Settings](settings.md)**: Configure system-wide runtime settings (session TTL, upload limits, market data sync intervals), find your way in the **Administration** tabs of Settings, and read the **Security** checks of the instance.
- 👥 **[Users & Invitations](users.md)**: Manage the accounts of the instance from the app's **Users** tab: invitations, password-reset links, administrator rights, deactivation and deletion.

### 🧹 Maintenance & Operations
- 🛠️ **[CLI Admin Tools](cli_tools.md)**: How to use the `dev.py` script for administrative tasks (user management, database upgrades, instance backups).
- 💾 **[Backup, Restore & Moving](backup_restore.md)**: One archive with the whole instance: make it from Settings › Administration › Backup or the command line, check it, restore it, and move LibreFolio between a hosted instance and your own server.
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
- On an instance in the `managed` profile, run by a hosting provider, there is no check at all:
  none at sign-in, and no **Check for updates** in the changelog. The provider updates the instance
  ([Hosting for Others](hosting_providers.md#managed-profile)).

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

??? tip "🐳 Keep the key out of `.env` — `JWT_SECRET_FILE`"

    Save the key in a file, such as a Docker secret, and set `JWT_SECRET_FILE` to its path instead of
    `JWT_SECRET`, for example `JWT_SECRET_FILE=/run/secrets/jwt_secret`. The rules and a Docker
    Compose example are in [Secrets](configuration_secrets.md#secrets).

The workers of a single `./dev.py server --workers …` share one key on their own. How long a
session lasts is the **Session Duration** in [Global Settings](settings.md). For the details, see
the developer page [Security Architecture](../developer/architecture/security.md).
