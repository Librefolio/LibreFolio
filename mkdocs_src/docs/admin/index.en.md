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

## 🔐 Authentication & Session Persistence

LibreFolio uses **JWT (JSON Web Tokens)** for user authentication. By default:
- If the **`JWT_SECRET`** environment variable is left empty in your `.env` file, the server generates a random signing secret at startup. This provides maximum security, but user sessions will be lost if the server is restarted.
- To persist sessions across server restarts (or when running multiple independent server instances behind a load balancer), define a stable **`JWT_SECRET`** key. Note that multiple uvicorn workers spawned on the same host will automatically share the parent process's generated secret, meaning session persistence is maintained across workers even when `JWT_SECRET` is left empty.

For technical details, see the developer-focused [Security Architecture](../developer/architecture/security.md) page.
