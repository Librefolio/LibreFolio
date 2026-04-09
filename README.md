# LibreFolio

**LibreFolio** is a self-hosted financial portfolio tracker for managing investments, cash accounts, and loans across multiple brokers.

## 📚 Documentation

The full documentation is available at: **[https://alfystar.github.io/LibreFolio/](https://alfystar.github.io/LibreFolio/)**

It includes:
- 🚀 **Getting Started**: Installation and setup guides.
- 📖 **User Manual**: How to use the application.
- 👨‍💻 **Developer Manual**: Architecture, API reference, and contribution guides.
- 🧮 **Financial Math**: Explanation of calculations used.

## 🏗️ Architecture

- **Backend**: Python (FastAPI + SQLModel + SQLite + Alembic)
  - **Async-first**: High-performance concurrent request handling (5-10x throughput)
  - **Dual Engine Pattern**: Sync for migrations/scripts, async for API
- **Frontend**: SvelteKit (TypeScript + TailwindCSS)
- **Deployment**: Docker Compose

## 📋 Features

- **Multi-Broker Support**: Import data from Interactive Brokers, Degiro, eToro, Trading212, and many others via CSV.
- **Asset Tracking**: Track Stocks, ETFs, Cryptocurrencies, and P2P Loans.
- **Automated Pricing**: Fetch prices from Yahoo Finance, JustETF, or custom web scrapers.
- **FX Handling**: Automatic currency conversion using official rates (ECB, FED, etc.).
- **Privacy First**: Your data stays on your server. No third-party cloud storage.

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- [Pipenv](https://pipenv.pypa.io/en/latest/installation.html)
- [Node.js](https://nodejs.org/en/download) 20.19+ (includes npm)
- Docker (optional, for deployment)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Alfystar/LibreFolio.git
cd LibreFolio
```

2. Install Python dependencies and activate the virtual environment:
```bash
pipenv install --dev
pipenv shell
```

3. Install all dependencies (backend + frontend):
```bash
./dev.py install
```

4. Create environment file:
```bash
cp .env.example .env
```

5. Run database migrations:
```bash
./dev.py db upgrade
```

6. Start the development server:
```bash
./dev.py server
```

7. Access the application:
   - **Dashboard**: http://localhost:8000
   - **API Docs**: http://localhost:8000/api/v1/docs

### Helper Script (`dev.py`)

The `./dev.py` script is your main tool for development (activate the virtual environment first with `pipenv shell`):

- `./dev.py install` - Install all dependencies (backend + frontend)
- `./dev.py server` - Start backend + frontend build
- `./dev.py test all` - Run all tests
- `./dev.py db migrate "msg"` - Create migration
- `./dev.py mkdocs serve` - Serve documentation locally
- `./dev.py --help` - Show all available commands

### 🐳 Docker Deployment

Build and run with Docker:

```bash
./dev.py docker build      # Build image (auto-builds frontend + docs)
docker compose up -d       # Start container
docker compose exec librefolio python dev.py user create <user> <email> <pass>
```

Use `./dev.py docker rebuild` to build a new image and restart containers in one step.

#### 🧪 Docker Test Mode

You can start a test server alongside the production one to explore the app with mock data:

```bash
./dev.py docker exec test db populate --force --with-static   # Populate test DB
./dev.py docker exec server --test                            # Start test server on :8001
```

Access: **http://localhost:8001** — Test users: `e2e_test_user` / `E2eTestPass123!`

> ⚠️ The test database lives inside the container's writable layer (not on a persistent volume). It is lost when the container is removed (`docker compose down`). Use `docker compose stop` / `docker compose start` to preserve it across restarts.

## 🌍 Internationalization

- **Code**: All code, comments, and docs are in English.
- **UI**: Frontend supports English, Italian, French, and Spanish.

## 🤝 Contributing

Contributions are welcome! Please read the **[Developer Manual](https://alfystar.github.io/LibreFolio/developer/)** before starting.

### For New Contributors

1. **Start with tests**: Run `./dev.py test all` to understand the project.
2. **Read the guides**: Check the "Developer Manual" section in the documentation.
3. **Code Standards**:
   - Use **type hints** everywhere.
   - Follow **async/await** pattern.
   - Write **tests** for new features.

## 📄 License

LibreFolio is licensed under the **GNU Affero General Public License v3.0** (AGPL-3.0).

This means:
- ✅ You can use, modify, and distribute this software freely
- ✅ You can use it for commercial purposes
- ⚠️ If you modify and distribute (including over a network), you must release your source code under AGPL-3.0
- ⚠️ You must include the original copyright and license notices

See the [LICENSE](LICENSE) file for the full license text.

**GitHub Repository**: [https://github.com/Alfystar/LibreFolio](https://github.com/Alfystar/LibreFolio)
