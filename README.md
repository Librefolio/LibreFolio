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

- Python 3.11+
- Node.js 18+
- Pipenv
- Docker (optional)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/ea-enel/LibreFolio.git
cd LibreFolio
```

2. Install all dependencies:
```bash
./dev.sh install
```

3. Create environment file:
```bash
cp .env.example .env
```

4. Run database migrations:
```bash
./dev.sh db:upgrade
```

5. Start the development server:
```bash
./dev.sh server
```

6. Access the application:
   - **Dashboard**: http://localhost:8000
   - **API Docs**: http://localhost:8000/api/v1/docs

### Helper Script (`dev.sh`)

The `./dev.sh` script is your main tool for development:

- `./dev.sh install` - Install dependencies
- `./dev.sh server` - Start backend + frontend build
- `./dev.sh test all` - Run all tests
- `./dev.sh db:migrate "msg"` - Create migration
- `./dev.sh info:mk serve` - Serve documentation locally

## 🌍 Internationalization

- **Code**: All code, comments, and docs are in English.
- **UI**: Frontend supports English, Italian, French, and Spanish.

## 🤝 Contributing

Contributions are welcome! Please read the **[Developer Manual](https://alfystar.github.io/LibreFolio/developer/)** before starting.

### For New Contributors

1. **Start with tests**: Run `./dev.sh test all` to understand the project.
2. **Read the guides**: Check the "Developer Manual" section in the documentation.
3. **Code Standards**:
   - Use **type hints** everywhere.
   - Follow **async/await** pattern.
   - Write **tests** for new features.

## 📄 License

TBD
