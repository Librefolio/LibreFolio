# LibreFolio

**LibreFolio** is a self-hosted financial portfolio tracker for managing investments, cash accounts, and loans across multiple brokers.

## 🏗️ Architecture

- **Backend**: Python (FastAPI + SQLModel + SQLite + Alembic)
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

2. Install dependencies:
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
```bash
# Database tests via dev.sh
./dev.sh test db validate           # Validate database schema
./dev.sh test db populate           # Populate DB with sample data
./dev.sh test db all                # Run all database tests
./dev.sh test --reset db all        # Reset DB and run all tests
./dev.sh test --help                # Show test options

# Or use test_runner.py directly
python test_runner.py db validate       # Validate schema only
python test_runner.py db populate       # Populate DB only
python test_runner.py db all            # All DB tests
python test_runner.py --reset db all    # Reset env + all DB tests
```

### Code Quality
```bash
./dev.sh format              # Format code with black
./dev.sh lint                # Lint code with ruff
./dev.sh test                # Run pytest tests
```

## 🗄️ Database

LibreFolio uses SQLite with Alembic for schema management. The database file is stored at `backend/data/sqlite/app.db`.

For database inspection and debugging, see [DB Guide](LibreFolio_prompts_and_db_guide/db/DB_Guide_and_Debugging.md).

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

TBD

