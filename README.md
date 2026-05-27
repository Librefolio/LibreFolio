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

---

Bring all your investments into one private, secure dashboard. Track stocks, ETFs, crypto, bonds, and loans across multiple brokers — with automated pricing, FX conversion, and technical analysis tools.

Your data stays on your server. No third-party cloud. No tracking.

📚 **Full Documentation**: [https://alfystar.github.io/LibreFolio/](https://alfystar.github.io/LibreFolio/)

## 🚀 Quick Start

<details>
<summary><strong>Local Development (Pipenv)</strong></summary>

**Prerequisites**: Python 3.13+, [Pipenv](https://pipenv.pypa.io/en/latest/installation.html), [Node.js](https://nodejs.org/) 20.19+

```bash
git clone https://github.com/Alfystar/LibreFolio.git
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

For full setup details see the [Developer Installation Guide](https://alfystar.github.io/LibreFolio/developer/dev-installation/).

</details>

<details>
<summary><strong>Docker Deployment</strong></summary>

```bash
git clone https://github.com/Alfystar/LibreFolio.git
cd LibreFolio

cp .env.example .env       # Configure environment
./dev.py docker build      # Build image (auto-builds frontend + docs)
docker compose up -d       # Start container
```

Access: **http://localhost:6040** — The first registered user becomes administrator.

For reverse proxy, test mode, and advanced options see the [Docker Guide](https://alfystar.github.io/LibreFolio/admin/docker_advanced/).

</details>

## 🤝 Contribute

LibreFolio values **every form of contribution equally** — code, ideas, and donations all drive the project forward.

### 💡 High-Impact Contributions

- **New Plugins** — LibreFolio uses a [Registry & Plugin System](https://alfystar.github.io/LibreFolio/developer/architecture/patterns/registry_pattern/) with three plugin types:
  - 📥 **[BRIM Plugins](https://alfystar.github.io/LibreFolio/developer/architecture/patterns/brim_plugin_guide/)** — Import from a new broker (CSV/Excel)
  - 📈 **[Asset Plugins](https://alfystar.github.io/LibreFolio/developer/architecture/patterns/asset_plugin_guide/)** — Fetch prices from a new data source
  - 💱 **[FX Plugins](https://alfystar.github.io/LibreFolio/developer/architecture/patterns/fx_plugin_guide/)** — Add a new exchange rate provider
- **Chart Signal Plugins** — New technical indicators and chart overlays
- **UI/UX Ideas** — Aesthetic improvements and design suggestions
- **Bug Reports** — Finding and reporting issues on [GitHub Issues](https://github.com/Alfystar/LibreFolio/issues)

### 🛠️ How to Contribute Code

1. **Fork** the [repository](https://github.com/Alfystar/LibreFolio)
2. **Create a branch** for your feature or fix
3. **Submit a Pull Request** with a clear description

See the [Developer Manual](https://alfystar.github.io/LibreFolio/developer/) for architecture, conventions, and testing guidelines.

## 📄 License

LibreFolio is licensed under **GNU Affero General Public License v3.0** (AGPL-3.0).
You can use, modify, and distribute it freely — if you distribute modifications (including over a network), you must release your source under AGPL-3.0.

See [LICENSE](LICENSE) for the full text and the [Credits & Legal](https://alfystar.github.io/LibreFolio/community/credits-legal/) page for details.

---

<p align="center">
  If LibreFolio helps you manage your investments, consider supporting its development:<br><br>
  <a href="https://www.buymeacoffee.com/librefolio" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-green.png" alt="Buy Me a Coffee" height="40"></a>
  <br><br>
  ⭐ <a href="https://github.com/Alfystar/LibreFolio">Star on GitHub</a> · 💡 <a href="https://github.com/Alfystar/LibreFolio/discussions">Share Ideas</a> · 🐛 <a href="https://github.com/Alfystar/LibreFolio/issues">Report Bugs</a>
</p>
