# LibreFolio — Backend Testing Reference

## 📁 Struttura Test

```text
backend/test_scripts/
├── test_api/               # 276+ test — REST endpoints via httpx
│   ├── test_assets_crud.py
│   ├── test_assets_events.py
│   ├── test_assets_metadata.py
│   ├── test_assets_patch_fields.py
│   ├── test_assets_prices.py
│   ├── test_assets_provider.py
│   ├── test_auth_api.py
│   ├── test_brokers_api.py
│   ├── test_broker_access_api.py
│   ├── test_broker_multiuser_api.py
│   ├── test_brim_api.py
│   ├── test_fx_api.py
│   ├── test_fx_sync.py
│   ├── test_profile_api.py
│   ├── test_settings_api.py
│   ├── test_transactions_api.py
│   ├── test_uploads_api.py
│   └── test_users_search.py
├── test_db/                # Database layer
│   ├── populate_mock_data.py   # Mock data per test DB
│   ├── db_schema_validate.py
│   ├── test_db_referential_integrity.py
│   ├── test_fx_rates_persistence.py
│   └── test_numeric_truncation.py
├── test_services/          # Business logic
│   ├── test_asset_source.py
│   ├── test_asset_metadata.py
│   ├── test_fx_conversion.py
│   ├── test_provider_registry.py
│   └── ...
├── test_e2e/               # End-to-end backend flows
│   ├── test_search_to_prices.py
│   └── test_brim_e2e.py
├── test_external/          # Provider + network tests
├── test_schemas/           # Pydantic validation
├── test_utilities/         # Utility functions
├── test_server_helper.py   # Auto-start server per API tests
└── test_utils.py           # Output formatting, helpers
```

---

## ▶️ Come Eseguire

```bash
# Tutti i test backend (800+)
./dev.py test all

# Singola categoria
./dev.py test api all         # REST endpoint tests
./dev.py test db all          # Database tests
./dev.py test services all    # Service layer tests
./dev.py test utils all       # Utility tests
./dev.py test schemas all     # Schema validation
./dev.py test external all    # Provider tests (needs network)
./dev.py test e2e all         # Backend end-to-end

# Con coverage
./dev.py test api all --coverage

# Verbose
./dev.py test api all -v

# Singolo file (bypass dev.py, direttamente pytest)
cd /path/to/LibreFolio
pipenv run pytest backend/test_scripts/test_api/test_assets_crud.py -v

# Singolo test
pipenv run pytest backend/test_scripts/test_api/test_assets_crud.py::test_create_single_asset -v

# Popola DB con dati mock
./dev.py test db populate --force
```

---

## 🏗️ Architettura Test API

I test API usano `_TestingServerManager` da `test_server_helper.py`:

1. **Server come thread**: uvicorn gira in un thread nel processo pytest (non subprocess) → abilita `pytest-cov` coverage tracking
2. **Porta test**: `TEST_PORT` (default 8001, configurabile via env var)
3. **DB test isolato**: `backend/data/test/sqlite/app.db` — completamente separato da prod
4. **Client HTTP**: `httpx.AsyncClient` per chiamate API asincrone
5. **Auto-cleanup**: server si ferma automaticamente a fine test

### Pattern tipo per un test API

```python
"""Test per feature X."""
import httpx
import pytest
from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30


async def create_user_and_login(client: httpx.AsyncClient) -> None:
    """Helper: crea utente temporaneo e loggalo."""
    import uuid, time
    username = f"test_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"
    await client.post(f"{API_BASE}/auth/register",
        json={"username": username, "email": f"{username}@test.com", "password": "TestPass123!"},
        timeout=TIMEOUT)
    await client.post(f"{API_BASE}/auth/login",
        json={"username": username, "password": "TestPass123!"},
        timeout=TIMEOUT)


@pytest.mark.asyncio
class TestFeatureX:
    """Tests for feature X."""

    @pytest.fixture(autouse=True)
    def server(self):
        """Ensure test server is running."""
        mgr = _TestingServerManager()
        mgr.ensure_started()
        yield
        # Server cleanup is automatic

    async def test_create_something(self):
        print_section("Create Something")
        async with httpx.AsyncClient() as client:
            await create_user_and_login(client)
            resp = await client.post(f"{API_BASE}/something",
                json={...}, timeout=TIMEOUT)
            assert resp.status_code == 201
            print_success("Created successfully")
```

---

## 🗄️ Mock Data

`populate_mock_data.py` crea dati deterministici per test:

- **Users**: `e2e_test_user` e `e2e_test_admin`
- **Brokers**: 3 broker con accesso condiviso
- **Assets**: Apple Inc. (AAPL, yfinance), iShares MSCI World (JustETF), BTP (CSS Scraper), Scheduled Investment — con 30 giorni di prezzi mock
- **FX Pairs**: EUR/USD, GBP/EUR, USD/CHF con rate mock
- **Transactions**: 10+ transazioni associate

```bash
# Pulisci DB e ripopola
./dev.py db create-clean --test
./dev.py test db populate --force

# Solo popola (senza ricreare)
./dev.py test db populate

# Con risorse statiche (per gallery screenshot)
./dev.py test db populate --force --clean --with-static --with-reports
```

---

## 📊 Coverage

### Esecuzione con coverage

```bash
# Backend tests con coverage
./dev.py test --coverage api all
./dev.py test --coverage services all

# Clean coverage prima di una nuova sessione
./dev.py test --coverage --cov-clean-backend api all
./dev.py test --coverage --cov-clean-frontend front-fx all

# Frontend E2E con backend coverage tracking
./dev.py test --coverage front-fx all
```

### Report differenziati

I report coverage sono separati per sorgente:

| Report | Directory | Generato da |
|--------|-----------|-------------|
| Backend | `htmlcov-backend/` | `--coverage` su test backend (pytest-cov) |
| Frontend | `htmlcov-frontend/` | `--coverage` su test frontend (`coverage run` + gracefulShutdown + coverage combine) |
| Combined | `htmlcov/` | Merge di tutti i `.coverage.*` files |

```bash
# Visualizzare i report
./dev.py test coverage show backend     # Apre htmlcov-backend/
./dev.py test coverage show frontend    # Apre htmlcov-frontend/
./dev.py test coverage show combined    # Merge tutto + apre htmlcov/

# Solo merge senza aprire browser
./dev.py test coverage combine
```

### Coverage Analysis — Funzioni scoperte

Lo script `scripts/coverage_analysis.py` analizza il JSON coverage per trovare funzioni
dove il `def` è coperto ma il body non è mai stato eseguito (funzione mai chiamata):

```bash
# Prima: generare il JSON coverage
coverage json -o /tmp/cov_report.json

# Poi: analizzare
./dev.py test coverage-report                  # Report completo
./dev.py test coverage-report --priority high  # Solo HIGH priority
./dev.py test coverage-report --summary        # Conteggi rapidi
./dev.py test coverage-report --json           # Output machine-readable
```

Classificazione automatica per priorità:
- **HIGH**: core business logic (asset_source, fx, broker_service, user_service)
- **MEDIUM**: API endpoints, provider specifici
- **LOW**: utility, cache, settings
- **INFRA**: main.py, logging, uploads (non unit-testabile)

Filtri automatici: esclude `abstract` (body=pass), `@property` semplici, `@field_validator`.

### Architettura Coverage

- **`.coveragerc`** — config: `source=backend/app`, `parallel=true`, `concurrency=thread,gevent`, `sigterm=true`
- **`coverage run --parallel-mode -m uvicorn`** — dev.py in coverage mode usa `os.execvpe()` per avviare uvicorn sotto `coverage run`
- **`gracefulShutdown`** — `playwright.config.ts` configura `{signal: 'SIGTERM', timeout: 5000}` per permettere a `coverage run` di scrivere i dati prima della terminazione
- **Frontend E2E**: `playwright.config.ts` aggiunge `--coverage` al webServer command quando `COVERAGE_BACKEND=1` è nell'env

---

## ⚠️ Convenzioni

- **Naming**: `test_*.py` per file, `test_*` per funzioni, `Test*` per classi
- **Isolamento**: ogni test crea il proprio utente temporaneo (`unique_id`)
- **No side effects**: i test non devono dipendere dall'ordine di esecuzione
- **Output formattato**: usare `print_section()`, `print_success()`, `print_error()` da `test_utils.py`
- **Timeout**: `TIMEOUT = 30` secondi per chiamate API (evita hang)



