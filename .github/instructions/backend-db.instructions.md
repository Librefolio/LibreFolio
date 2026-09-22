---
applyTo: "backend/app/db/**,backend/alembic/**"
---

# Database & Alembic Reference

## ORM: SQLModel (SQLAlchemy 2.x async)

All models are in `backend/app/db/models.py`. Session management in `session.py`.

### Models

Verified against the real schema on 2026-09-22 (`backend/data/prod`, revision
`004_release_1_2_0_schema`): 14 tables, columns/indexes/FK matching SQLModel metadata
exactly. **Table names are plural** — a lookup for `asset` or `transaction` finds nothing.

| Model | Table | Key Fields |
|-------|-------|------------|
| `User` | `users` | username, email, hashed_password, **is_superuser**, is_active, login_count, donation_popup_last_shown_at, donation_popup_logins_since_shown |
| `UserSettings` | `user_settings` | user_id (FK), base_currency, language, theme, avatar_url |
| `UserOnboardingProgress` | `user_onboarding_progress` | user_id, flow, status, version, completed_at, skipped_at |
| `UserOnboardingStepProgress` | `user_onboarding_step_progress` | user_id, flow, step_id, status, version, completed_at, skipped_at |
| `GlobalSetting` | `global_settings` | key, value, value_type, description, updated_by_user_id |
| `Broker` | `brokers` | name, description, portal_url, icon_url, default_import_plugin, allow_cash_overdraft, allow_asset_shorting, is_active, opened_at |
| `BrokerUserAccess` | `broker_user_access` | broker_id, user_id, role, share_percentage |
| `Asset` | `assets` | display_name, currency, asset_type, **is_benchmark**, classification_params (JSON), quote_base_quantity, active, user_url, identifier_* (one column per `IdentifierType`) |
| `Transaction` | `transactions` | broker_id, asset_id, type, date, quantity, **amount**, currency, related_transaction_id, tags, cost_basis_override, cost_basis_currency, asset_event_id |
| `PriceHistory` | `price_history` | asset_id, date, open, high, low, close, volume, adjusted_close, currency, source_plugin_key, fetched_at |
| `AssetEvent` | `asset_events` | asset_id, date, type, value, currency, provider_assignment_id, notes |
| `FxRate` | `fx_rates` | base, quote, date, rate, **source** |
| `FxConversionRoute` | `fx_conversion_routes` | base, quote, priority, chain_steps |
| `AssetProviderAssignment` | `asset_provider_assignments` | asset_id, provider_code, identifier, identifier_type, provider_params, last_fetch_at |

Two traps this table used to set: a transaction carries a signed **`amount`**, not
`price` + `fees` (unified transactions), and a user's role is the boolean
`is_superuser` — `UserRole` is a *different* thing (per-broker access).

### Enums

| Enum | Values |
|------|--------|
| `AssetType` | base: STOCK, ETF, BOND, CRYPTO, FUND, CROWDFUND, HOLD, COMMODITY, REAL_ESTATE, INDEX, OTHER<br>ETF subtypes: ETF_STOCK, ETF_BOND, ETF_COMMODITY, ETF_REAL_ESTATE, ETF_CRYPTO, ETF_MONETARY |
| `TransactionType` | BUY, SELL, DIVIDEND, INTEREST, DEPOSIT, WITHDRAWAL, FEE, TAX, ADJUSTMENT, TRANSFER, FX_CONVERSION, CASH_TRANSFER |
| `AssetEventType` | DIVIDEND, INTEREST, PRICE_ADJUSTMENT, SPLIT, MATURITY_SETTLEMENT |
| `IdentifierType` | ISIN, TICKER, CUSIP, SEDOL, FIGI, UUID, OTHER — each one owns an `identifier_*` column in `assets` |
| `UserRole` | OWNER, EDITOR, VIEWER — **per-broker access**, not the global user role |
| `OnboardingFlow` | 15 values: welcome, intro_tour, then the page/entity guides for transactions, brokers, FX and assets |
| `OnboardingStatus` | pending, completed, skipped |

An ETF subtype answers *which base type does this ETF hold?*, so the second level is the
set of base types, not a parallel taxonomy. `INDEX` forbids transactions; every other
value is behaviourally inert in the backend. `AssetType` also feeds the `asset_class`
buckets of stress scenarios, where **a type missing from `bucket_shocks` is shocked by
zero silently** — hence the dedicated coverage test.

### Conventions

- **Decimal columns**: `Numeric(18, 6)` for precision
- **Timestamps**: UTC via `utcnow()` helper
- **Daily-point policy**: one record per day for prices and FX rates
- **Foreign keys**: enforced with `PRAGMA foreign_keys=ON`
- **Currency validation**: via `Currency.validate_code()` from schemas

## Alembic Migrations

### Current Phase: Released — Incremental Migrations

LibreFolio is **officially released**. Existing user installations carry real data, so schema changes
MUST ship as **incremental Alembic migrations** that upgrade an existing DB in place. Do **not** edit
`001_initial.py` for changes to already-shipped tables — that would silently break deployed databases.

```bash
./dev.py db migrate "describe change"   # Autogenerate a new migration from model changes
./dev.py db upgrade                      # Apply pending migrations (runs on user installs too)
./dev.py db downgrade                    # Revert last migration
```

**Rule**: model change → add an incremental migration with working `upgrade()` **and** `downgrade()`,
tested against a populated DB. Only touch `001_initial.py` for the initial schema of a brand-new table
that has never shipped.

`./dev.py db create-clean` still rebuilds a DB from scratch for **fresh installs and test runs**, but is
**no longer** the way to evolve an existing schema.

### Naming: `00N_<target release or scope>`

`./dev.py db migrate` generates a random hex revision id and a slugified filename. **Rename both**
before committing, while the migration is still unreleased:

```
001_initial.py                  002_identifier_other_json_list.py
003_scheduler_timezone.py       004_release_1_2_0_schema.py
```

- **Zero-padded sequential prefix** (`00N_`) so the chain reads in order on disk.
- After the prefix, either the **target release version** it ships in
  (`004_release_1_2_0_schema` → v1.2.0) or the **functional scope** when the migration is a
  single self-contained change (`003_scheduler_timezone`).
- The `revision` string inside the file equals the filename without `.py`.

⚠️ **The revision id is the contract; the filename is not.** Alembic resolves revisions by id,
never by path, so a file can be renamed freely — this is *verified*: renaming
`5b1333fa6b07_scheduler_times_use_configured_timezone.py` to `003_scheduler_timezone.py` left
databases stamped `5b1333fa6b07` upgrading to head with a schema identical to a from-scratch
build. The **id**, once it appears in a published tag, is in users' `alembic_version` tables
and can never change or disappear. Before removing or consolidating any revision:

```bash
git cat-file -e <tag>:backend/alembic/versions/<file>   # is it inside a released tag?
```

Anything inside a released tag stays in the chain. Anything not released may be consolidated.

### One head, always — never `alembic merge`

Two migrations authored in parallel that declare the same `down_revision` produce **no Git
conflict** and a fork that only bites on a fresh install. Resolve it by re-parenting one onto
the other, not with a merge node.

This is not a style preference. `main.py:_alembic_head_revision()` calls
`ScriptDirectory.get_current_head()` (singular), which **raises `CommandError` on multiple
heads**; the caller swallows it and returns `None`, so the pending-migration check at startup
silently evaluates to false and **the server boots without migrating** — the exact failure the
check exists to prevent. A fork therefore disables auto-upgrade for every install while
leaving only a warning in the log.

`db_schema_validate.py` enforces `len(ScriptDirectory.get_heads()) == 1`.

### Standard Commands

```bash
./dev.py db check                 # Check migration status
./dev.py db current               # Show current revision
./dev.py db upgrade               # Apply pending migrations
./dev.py db downgrade             # Revert last migration
./dev.py db migrate "message"     # Create a new incremental migration
```

### Data Separation

| Environment | DB Path | Command |
|-------------|---------|---------|
| Production | `backend/data/prod/sqlite/app.db` | `./dev.py db create-clean` |
| Test | `backend/data/test/sqlite/app.db` | `./dev.py db create-clean --test` |

Completely isolated — different SQLite files, different data directories.

## Session Management

- `get_async_engine()` — singleton async engine
- `get_session_generator()` — FastAPI dependency yielding `AsyncSession`
- All DB operations use async SQLAlchemy sessions

