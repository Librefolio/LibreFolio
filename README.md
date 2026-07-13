<p align="center">
  <img src="mkdocs_src/docs/static/logo.png" alt="LibreFolio Logo" width="180">
</p>

<h1 align="center">LibreFolio</h1>

<p align="center">
  <strong>Free to understand, free to act.</strong><br>
  A self-hosted, open-source financial portfolio tracker.
</p>

<p align="center">
  <a href="https://www.buymeacoffee.com/librefolio" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-green.png" alt="Buy Me a Coffee" height="40"></a>
</p>

<p align="center">
  <a href="https://github.com/Librefolio/LibreFolio/actions/workflows/release.yml"><img src="https://github.com/Librefolio/LibreFolio/actions/workflows/release.yml/badge.svg" alt="Build Status"></a>
  <a href="https://www.gnu.org/licenses/agpl-3.0"><img src="https://img.shields.io/badge/License-AGPL_v3-blue.svg" alt="License: AGPL v3"></a>
  <a href="https://github.com/orgs/Librefolio/packages/container/package/librefolio"><img src="https://img.shields.io/badge/container-ghcr.io-blue?logo=github" alt="Docker Registry"></a>
  <a href="https://github.com/Librefolio/LibreFolio/stargazers"><img src="https://img.shields.io/github/stars/Librefolio/LibreFolio.svg" alt="GitHub stars"></a>
</p>

---

Bring all your investments into one private, secure dashboard. Track stocks, ETFs, crypto, bonds, and loans across multiple brokers — with automated pricing, FX conversion, and technical analysis tools.

Your data stays on your server. No third-party cloud. No tracking.

📚 **Full Documentation**: [https://librefolio.github.io/LibreFolio/](https://librefolio.github.io/LibreFolio/)

---

## 🖼️ Gallery

<p align="center">
  <img src="https://librefolio.github.io/LibreFolio/gallery/desktop/en/light/dashboard/main.png" alt="LibreFolio Dashboard" width="100%">
</p>

<details>
<summary>📸 <strong>More Screenshots</strong></summary>

### Asset Management
<p align="center">
  <img src="https://librefolio.github.io/LibreFolio/gallery/desktop/en/light/assets/list.png" alt="Asset List" width="100%">
</p>

### Transactions Log & Imports
<p align="center">
  <img src="https://librefolio.github.io/LibreFolio/gallery/desktop/en/light/transactions/list.png" alt="Transactions List" width="100%">
</p>

### Forex conversion graph & routes
<p align="center">
  <img src="https://librefolio.github.io/LibreFolio/gallery/desktop/en/light/fx/list.png" alt="Forex Pairs and Rates" width="100%">
</p>

</details>

## 🤔 Why LibreFolio?

LibreFolio is built to solve common issues found in existing portfolio tracking tools:

- **🔒 Verifiable Security & Privacy**: Your financial data belongs to you. Since LibreFolio is fully open-source, its code is auditable by anyone, ensuring complete transparency with no hidden tracking, telemetries, or silent data collection.
- **🧮 Open & Transparent Calculations**: Traditional trackers use black-box formulas. LibreFolio calculates cost basis (FIFO and WAC) and ROI (TWRR and MWRR) at runtime with completely open-source, verifiable formulas.
- **🏦 Broad Broker & Data Integration**: Easily import statement files from a wide range of [supported brokers](https://librefolio.github.io/LibreFolio/user/transactions/import/) and keep your assets updated with price quotes from various [market data providers](https://librefolio.github.io/LibreFolio/user/assets/providers/) and [forex rates sources](https://librefolio.github.io/LibreFolio/user/fx/providers/).
- **🤖 AI-Assisted Portfolio Analysis**: Export your anonymized portfolio data to leverage AI models for custom performance analysis, risk assessments, and allocation insights. This is a core focus area of our roadmap and will be continuously enhanced.

---

> ### 📢 Stay Updated on LibreFolio Progress
>
> If you want to follow the development and get notified about new features, updates, and releases, set up an alert in 10 seconds:
>
> 1. Scroll to the top of this page.
> 2. Click the **Watch** button (top right).
> 3. Select **Custom** in the dropdown menu.
> 4. Check **Releases** and click **Apply**.
>
> *You will receive an automatic notification directly on GitHub whenever a new version is released!*

---
## 🚀 Quick Start

<details>
<summary><strong>🐳 Docker Installation (Recommended for Users)</strong></summary>

Run LibreFolio using the official pre-built image. No development tools or compilers required.

**Prerequisites**: Docker & Docker Compose installed.

1. **Create a project directory**:
   ```bash
   mkdir librefolio && cd librefolio
   ```

2. **Download the configuration files**:
   ```bash
   # Using curl:
   curl -L https://raw.githubusercontent.com/Librefolio/LibreFolio/main/docker-compose.prod.yml -o docker-compose.yml
   curl -L https://raw.githubusercontent.com/Librefolio/LibreFolio/main/.env.example -o .env

   # Or using wget:
   wget https://raw.githubusercontent.com/Librefolio/LibreFolio/main/docker-compose.prod.yml -O docker-compose.yml
   wget https://raw.githubusercontent.com/Librefolio/LibreFolio/main/.env.example -o .env
   ```

3. **Start the application**:
   ```bash
   docker compose up -d
   ```

Access: **http://localhost:6040**. The first registered user automatically becomes the administrator.

For complete guide, auto-updates (Watchtower), and backups, see the [🐳 User Installation Manual](https://librefolio.github.io/LibreFolio/user/installation/).

</details>

<details>
<summary><strong>💻 Host Installation (Local Development)</strong></summary>

**Prerequisites**: Python 3.13+, [Pipenv](https://pipenv.pypa.io/en/latest/installation.html), [Node.js](https://nodejs.org/) 24+

```bash
git clone https://github.com/Librefolio/LibreFolio.git
cd LibreFolio

pipenv install --dev
pipenv shell

./dev.py install        # Install all dependencies (backend + frontend)
cp .env.example .env    # Configure environment
./dev.py db upgrade     # Run database migrations
./dev.py server         # Start development server
```

Access: **http://localhost:6040** — API Docs: **http://localhost:6040/api/v1/docs**

`./dev.py --help` shows all available commands.

For full host setup and administration details, see the [💻 Host Installation Guide](https://librefolio.github.io/LibreFolio/admin/host_installation/) and the [Developer Workflow](https://librefolio.github.io/LibreFolio/developer/dev_workflow/).

</details>

<details>
<summary><strong>🏗️ Advanced Docker (Build from Source)</strong></summary>

Build your own custom Docker image from the source code.

**Prerequisites**: Python 3.13+, Pipenv, Node.js 24+, and Docker.

```bash
git clone https://github.com/Librefolio/LibreFolio.git
cd LibreFolio

cp .env.example .env       # Configure environment
./dev.py docker build      # Build custom image (builds frontend + docs)
docker compose up -d       # Start container
```

Access: **http://localhost:6040**

For advanced deployment options, reverse proxy configurations, and test mode, see the [🏗️ Advanced Docker Guide](https://librefolio.github.io/LibreFolio/admin/docker_advanced/).

</details>

## 🤝 Contribute

LibreFolio values **every form of contribution equally** — code, ideas, and donations all drive the project forward.

### 💡 High-Impact Contributions

- **New Plugins** — LibreFolio uses a [Registry & Plugin System](https://librefolio.github.io/LibreFolio/developer/architecture/patterns/registry_pattern/) with three plugin types:
  - 📥 **[BRIM Plugins](https://librefolio.github.io/LibreFolio/developer/architecture/patterns/brim_plugin_guide/)** — Import from a new broker (CSV/Excel). See [🏦 Supported Brokers](https://librefolio.github.io/LibreFolio/user/transactions/import/) for the list of already supported brokers.
  - 📈 **[Asset Plugins](https://librefolio.github.io/LibreFolio/developer/architecture/patterns/asset_plugin_guide/)** — Fetch prices from a new data source. See [📈 Supported Asset Providers](https://librefolio.github.io/LibreFolio/user/assets/providers/) for existing providers.
  - 💱 **[FX Plugins](https://librefolio.github.io/LibreFolio/developer/architecture/patterns/fx_plugin_guide/)** — Add a new exchange rate provider. See [💱 Supported Forex Providers](https://librefolio.github.io/LibreFolio/user/fx/providers/) for existing providers.
- **Chart Signal Plugins** — New technical indicators and chart overlays
- **UI/UX Ideas** — Aesthetic improvements and design suggestions
- **Bug Reports** — Finding and reporting issues on [GitHub Issues](https://github.com/Librefolio/LibreFolio/issues)

### 🛠️ How to Contribute Code

1. **Fork** the [repository](https://github.com/Librefolio/LibreFolio)
2. **Create a branch** for your feature or fix
3. **Submit a Pull Request** with a clear description

See the [Developer Manual](https://librefolio.github.io/LibreFolio/developer/) for architecture, conventions, and testing guidelines.

## 📄 License

LibreFolio is licensed under **GNU Affero General Public License v3.0** (AGPL-3.0).
You can use, modify, and distribute it freely — if you distribute modifications (including over a network), you must release your source under AGPL-3.0.

See [LICENSE](LICENSE) for the full text and the [Credits & Legal](https://librefolio.github.io/LibreFolio/community/credits-legal/) page for details.

---

<p align="center">
  If LibreFolio helps you manage your investments, consider supporting its development:<br><br>
  <a href="https://www.buymeacoffee.com/librefolio" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-green.png" alt="Buy Me a Coffee" height="40"></a>
  <br><br>
  ⭐ <a href="https://github.com/Librefolio/LibreFolio">Star on GitHub</a> · 💡 <a href="https://github.com/Librefolio/LibreFolio/discussions">Share Ideas</a> · 🐛 <a href="https://github.com/Librefolio/LibreFolio/issues">Report Bugs</a>
</p>
