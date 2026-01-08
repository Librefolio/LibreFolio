# LibreFolio

**LibreFolio** is a self-hosted financial portfolio tracker for managing investments, cash accounts, and loans across multiple brokers.

## 🏗️ Architecture

- **Backend**: Python (FastAPI + SQLModel + SQLite + Alembic)
  - **Async-first**: High-performance concurrent request handling (5-10x throughput)
  - **Dual Engine Pattern**: Sync for migrations/scripts, async for API
  - 📚 [Read the Async Architecture Guide](docs/async-architecture.md)
- **Frontend**: React (TypeScript + MUI + i18n) _(coming soon)_
- **Deployment**: Single Docker image _(coming soon)_

## 📋 Features (In Development)

- Multi-broker portfolio tracking
- Cash account management per broker
- FX rate handling for multi-currency portfolios
- Scheduled-yield assets (e.g., P2P loans with tiered interest)
- FIFO-based gain/loss calculations
- Transaction types: BUY, SELL, DIVIDEND, INTEREST, DEPOSIT, WITHDRAWAL, FEE, TAX, etc.
- REST API with OpenAPI documentation
- Multilingual UI (English, Italian, French, Spanish)

## 🚀 Quick Start

### Prerequisites

- Python 3.13+ (or 3.11+)
- Pipenv

### Project Setup

The project uses `pyproject.toml` for configuration and all imports start from the project root (e.g., `from backend.app.config import ...`). This means:
- ✅ No need to set `PYTHONPATH` manually
- ✅ IDE auto-completion works out of the box
- ✅ Imports are consistent across all modules

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd LibreFolio
```

2. Install all dependencies (development included):
```bash
./dev.sh install
```

3. Create environment file (optional - defaults work out of the box):
```bash
cp .env.example .env
# Edit .env if you need to customize settings
```

4. Run database migrations:
```bash
./dev.sh db:upgrade
```

5. Start the development server:
```bash
./dev.sh server
```

6. Access the API documentation:
   - Swagger UI: http://localhost:8000/api/v1/docs
   - ReDoc: http://localhost:8000/api/v1/redoc

### Helper Script

The `./dev.sh` script provides convenient commands:
- `./dev.sh install` - Install all dependencies
- `./dev.sh server` - Start the FastAPI server
- `./dev.sh db:current` - Show current migration
- `./dev.sh db:migrate` - Create a new migration
- `./dev.sh db:upgrade` - Apply pending migrations
- `./dev.sh db:downgrade` - Rollback one migration
- `./dev.sh shell` - Open a shell in the virtualenv
- `./dev.sh help` - Show all available commands

[//]: # TODO: aggiornare i comandi con i nuovi()
## 📁 Project Structure

```
LibreFolio/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── db/           # Database models and session
│   │   ├── config.py     # Configuration management
│   │   ├── logging_config.py  # Structured logging
│   │   └── main.py       # FastAPI application
│   ├── alembic/          # Database migrations
│   ├── data/             # SQLite database (gitignored)
│   └── test_scripts/     # Test scripts
│       └── test_db/      # Database tests
│           ├── db_schema_validate.py  # Schema validation
│           └── populate_db.py         # Sample data population
├── docs/                 # Documentation
│   └── alembic-guide.md  # Alembic migrations guide
├── frontend/             # React frontend (coming soon)
├── Pipfile              # Python dependencies
├── pyproject.toml       # Project metadata
├── test_runner.py       # Centralized test orchestrator
├── dev.sh               # Development helper script
├── .env                 # Environment configuration (create from .env.example)
└── .env.example         # Example environment configuration
```

## 🔧 Development Commands

### Server Management
```bash
./dev.sh server              # Start FastAPI development server
./dev.sh shell               # Open Python shell in virtualenv
```

### Database Management
```bash
./dev.sh db:current          # Show current migration
./dev.sh db:migrate "msg"    # Create new migration
./dev.sh db:upgrade          # Apply migrations
./dev.sh db:downgrade        # Rollback one migration
```

> 📚 **New to Alembic?** Read our [Alembic Simple Guide](docs/alembic-guide.md) to understand how database migrations work!

### Testing

**🆕 New to the project?** Start with the [Testing Guide for New Developers](docs/testing-guide.md) - A hands-on introduction to LibreFolio via the test suite!

LibreFolio has a comprehensive test suite organized into 4 categories:

**🔒 Test Database Isolation**
- All tests use a **separate test database** (in temp directory)
- Your development/production data is **never touched**
- Test database is automatically created and cleaned up

**📊 Coverage Tracking**
- Full async/await coverage for FastAPI endpoints (~60% baseline)
- See [Async Coverage Solution](docs/COVERAGE_ASYNC_SOLUTION.md) for technical details

**External Services Tests** (no server required)
```bash
python test_runner.py external ecb      # Test ECB API connection
python test_runner.py external all      # All external service tests
```

**Database Tests** (no server required)
```bash
python test_runner.py db create         # Create fresh database
python test_runner.py db validate       # Validate schema
python test_runner.py db fx-rates       # Test FX rates persistence
python test_runner.py db populate       # Populate with MOCK DATA
python test_runner.py db all            # All DB tests
```

**Backend Services Tests** (no server required)
```bash
python test_runner.py services fx       # Test FX conversion logic
python test_runner.py services all      # All service tests
```

**API Tests** (auto-starts server if needed)
```bash
# No need to start server manually - tests will auto-start it!
python test_runner.py api fx            # Test FX API endpoints
python test_runner.py api all           # All API tests

# Note: If server was started by tests, it will be automatically stopped after
```

**Run ALL Tests** (optimal order)
```bash
python test_runner.py all               # Complete test suite
```

**Quick shortcuts via dev.sh:**
```bash
./dev.sh test all                       # Run complete test suite
./dev.sh test db all                    # All database tests
./dev.sh test external ecb              # ECB API test
```

**Help:**
```bash
python test_runner.py --help            # Show all categories
python test_runner.py db --help         # Show DB test options
python test_runner.py services --help   # Show services test options
```

**📋 Prerequisites Information**
Each test clearly shows its prerequisites:
- External tests: require internet connection
- DB tests: require external services to be working
- Services tests: require data in test database
- API tests: auto-manage server lifecycle

### Code Quality
```bash
./dev.sh format              # Format code with black
./dev.sh lint                # Lint code with ruff
./dev.sh test                # Run pytest tests
```

## 🗄️ Database

LibreFolio uses SQLite with Alembic for schema management. The database file is stored at `backend/data/sqlite/app.db`.

**Documentation:**
- 📚 **[Database Schema Documentation](docs/database-schema.md)** - Complete guide to all tables, relationships, and concepts
- 🔧 [Alembic Migration Guide](docs/alembic-guide.md) - How to manage database migrations
- ⚡ **[Async Architecture Guide](docs/async-architecture.md)** - How LibreFolio handles concurrent requests efficiently
- 🚀 **[API Development Guide](docs/api-development-guide.md)** - Complete guide for adding new REST API endpoints
- ⚙️ [Environment Variables](docs/environment-variables.md) - Configuration options and Docker deployment

**Quick Example:**
```bash
# Populate database with example data
./dev.sh test db all

# Inspect the database
sqlite3 backend/data/sqlite/app.db
```

## 🌍 Internationalization

- **Code**: All code, comments, and documentation are in English
- **UI**: Frontend supports English, Italian, French, and Spanish

## 📝 API Principles

- All calculations happen in the backend
- Frontend only displays computed results
- FIFO matching is computed at runtime (no persisted splits)
- Proper transaction integrity with cash movements

## 🐳 Docker (Coming Soon)

Single-image deployment where the backend serves frontend static assets.

## 📄 License

TBD

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

### For New Contributors

1. **Start with tests**: Run `python test_runner.py all` to understand the project
2. **Read the guides**:
   - 📖 [Testing Guide](docs/testing-guide.md) - Learn by running tests
   - 🗄️ [Database Schema](docs/database-schema.md) - Understand data models
   - 🚀 **[API Development Guide](docs/api-development-guide.md)** - Add new endpoints

### Adding New Features

When adding new API endpoints:
1. Follow the [API Development Guide](docs/api-development-guide.md)
2. Use **bulk-first** design pattern for better performance
3. Write comprehensive tests (see existing tests as examples)
4. Document your code with docstrings and examples
5. Run `python test_runner.py all` before submitting

### Code Standards

- All code, comments, and docs must be in **English**
- Use **type hints** everywhere
- Follow **async/await** pattern (see [Async Guide](docs/async-architecture.md))
- Add **Pydantic validation** for API models
- Write **tests** for all new features

