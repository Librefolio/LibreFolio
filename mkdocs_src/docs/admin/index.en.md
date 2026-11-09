# 🛡️ Admin Manual

For the people who install and run LibreFolio. Almost everything is done in one of three places: from the **command line**, in the **`.env`** file (environment variables) or in the app's **Settings › Administration** tabs.

---

## 📚 Guides

### 🐳 Deployment & Exposure
- 📦 **[Host Installation](host_installation.md)**: Python, Node.js and Pipenv directly on the host machine.
- 🐳 **[Advanced Docker](docker_advanced.md)**: Docker Compose, volumes and file ownership through GID/UID.
- 🌐 **[Expose Securely](service_exposure.md)**: your private instance with Tailscale, no router port opened: a VPN for your own devices or a subnet router for your whole home network.
    - 🌍 **[Expose Securely: Public Access with Funnel](service_exposure_funnel.md)**: a public HTTPS address with Tailscale Funnel, one for LibreFolio or one for each service with Docker.
- 🔍 **[Check Connection Security](connection_checks.md)**: the checklist, the indicator, the server's view and the session cookie; what to do when a check fails.
    - 🧰 **[Check Connection Security: Behind a Reverse Proxy](connection_proxy.md)**: Nginx, Caddy, Traefik or Tailscale: the headers to send, the trusted proxy and the visitor's address.

### ⚙️ System Configuration
- 📝 **[Environment Variables](configuration.md)**: the `.env` file and the main variables (`PORT`, `JWT_SECRET`, `LIBREFOLIO_DATA_DIR`, etc.), with the precedence between the values.
    - 🔐 **[Configuration: Secrets and Plugin Settings](configuration_secrets.md)**: secrets read from files (such as Docker secrets), the instance key, the settings and API keys of the plugins.
    - 🛡️ **[Configuration: Checks and Protections](configuration_security.md)**: the checks at startup, the Content-Security-Policy, the frame protection and how the server stops.
    - 👥 **[Configuration: Accounts and Asset Search](configuration_accounts.md)**: who can sign up, limits on accounts and failed sign-ins, the initial administrator, the order of the price providers.
- 📧 **[Email](email.md)**: optional SMTP: the variables, examples for the most common servers, the **Email** tab of Settings › Administration and the test email.
    - 📬 **[Email: Links and Messages](email_flows.md)**: invitations and password resets, forgotten passwords and their limits, email verification, the notice of an email change.
    - 🛠️ **[Email: When It Does Not Work](email_troubleshooting.md)**: the errors, what the log says, SMTP security notes.
- ⚙️ **[Global Settings](settings.md)**: the runtime settings (session TTL, upload limits, market data sync intervals), the **Administration** tabs and the **Security** checks of the instance.
- 👥 **[Users & Invitations](users.md)**: the app's **Users** tab: invitations, password-reset links, administrator rights, deactivation and deletion.

### 🧹 Maintenance & Operations
- 🛠️ **[CLI Admin Tools](cli_tools.md)**: the `dev.py` script for user management, database upgrades and instance backups.
- 💾 **[Backup, Restore & Moving](backup_restore.md)**: one archive with the whole instance, from Settings › Administration › Backup or from the command line: make it, check it, restore it, move LibreFolio between two installations.
- 📂 **[Filesystem Structure](filesystem.md)**: where databases, logs, uploads and temporary folders live, and how to perform backups.

---

## 🔔 Update Notifications {: #update-notifications }

When an administrator signs in, LibreFolio checks GitHub for a newer **stable** release. If there is one, the **New version available** window shows your version and the latest side by side, with the **How to update** ([updating guide](../user/installation.md#updating)) and **Release notes on GitHub** links.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="update-available-modal" alt="Update available modal with the current and the latest version">
</div>

| Button | Effect |
| --- | --- |
| **Remind me later** | Closes the window until a later sign-in. |
| **Skip this version** | No automatic prompt for that version; an even newer one will be announced. |

- A release is announced only when its Docker image can be downloaded; the window waits until no other window or guide is open.
- Without internet access the check fails silently: no error, no banner.
- To check right away: **Check for updates** in the [changelog](../user/settings/about.md#changelog-modal). It reports errors, and skipped versions too.

??? note "👥 Other users — when someone who is not an administrator checks"

    For users who are not administrators, no check runs at sign-in. If one of them runs **Check for updates** and a newer release exists, the **Update available — contact an administrator** window lists the administrators, with their email addresses when available.

---

## 🔐 Keep Users Signed In After a Restart {: #session-persistence }

`JWT_SECRET` is the key that signs every login session.

- **Not set** (the default): a new random key at every start, so everyone signs in again after a restart or an update.
- **Set**: sessions survive restarts. Set it also when several LibreFolio servers share the same users behind a load balancer.

To set it:

1. Generate a key. **From a terminal**, on the host:

    ```bash
    python3 -c "import secrets; k = secrets.token_urlsafe(64); print(f'JWT_SECRET={k}'); print(k)"
    ```

    You get two lines: the first, `JWT_SECRET=…`, is ready to paste into `.env`; the second is the key alone, for when you keep it in a file (`JWT_SECRET_FILE`, below). Without Python on the host, run the command **in the container**:

    ```bash
    docker exec librefolio python -c "import secrets; k = secrets.token_urlsafe(64); print(f'JWT_SECRET={k}'); print(k)"
    ```

2. Paste the first line **into LibreFolio's `.env` file**:

    ```bash
    JWT_SECRET=paste-the-generated-value-here
    ```

3. Restart LibreFolio. With Docker Compose, run `docker compose up -d`.

    From then on, a restart signs nobody out.

!!! warning "🔒 Keep the key secret"

    Whoever knows it can forge a session.

??? tip "🐳 Keep the key out of `.env` — `JWT_SECRET_FILE`"

    Save the key in a file, such as a Docker secret, and set `JWT_SECRET_FILE` to its path instead of `JWT_SECRET`: for example `JWT_SECRET_FILE=/run/secrets/jwt_secret`. The rules and a Docker Compose example are in [Secrets](configuration_secrets.md#secrets).

- The workers of a single `./dev.py server --workers …` share one key on their own.
- How long a session lasts is the **Session Duration** in [Global Settings](settings.md).
- Details for developers: [Security Architecture](../developer/architecture/security.md).
