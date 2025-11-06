# OFPF — SQLite DB Guide & Debugging Notes

**Scope:** How to inspect, debug, and maintain the OFPF SQLite database during development and after deployment.

> All code and documentation are in English. Only the frontend UI is multilingual.

---

## 1) Where is the DB?
- Path inside the container: `/app/data/sqlite/app.db`
- Recommended host mount (docker-compose): `./data:/app/data` → DB file on host at `./data/sqlite/app.db`

## 2) Open the DB with a GUI
Use any of the following tools:
- **DB Browser for SQLite** — lightweight, open-source GUI.
- **SQLiteStudio** — portable, rich features.
- **DBeaver** — multi-DB IDE, supports SQLite.

### Steps (DB Browser / SQLiteStudio / DBeaver)
1. Stop the container **or** use a **copy** of the file to avoid locks:
   - `cp ./data/sqlite/app.db ./data/sqlite/app-copy.db`
2. Open the file in the GUI.
3. Browse tables, run queries, export CSV.

> Tip: If you must open the live DB while the container runs, prefer **read-only** mode in the GUI. Avoid writing concurrently.

## 3) SQLite PRAGMAs to know
Execute in your GUI (Execute SQL tab) or during app startup via SQLAlchemy:
```sql
PRAGMA foreign_keys = ON;             -- enforce FK constraints (should be ON by app)
PRAGMA journal_mode = WAL;            -- good for concurrent read
PRAGMA synchronous = NORMAL;          -- performance vs durability trade-off
PRAGMA temp_store = MEMORY;           -- faster temp ops (optional)
```

## 4) Alembic basics
- Show current revision: `alembic current`
- Create a new migration: `alembic revision --autogenerate -m "desc"`
- Apply migrations: `alembic upgrade head`
- Roll back: `alembic downgrade -1`

> For SQLite, ensure `render_as_batch=True` in Alembic’s env to support table alters.

## 5) Reset and seed the DB
- **Reset script** (`scripts/reset_db.py`):
  - Option A: delete `./data/sqlite/app.db` and run `alembic upgrade head`.
  - Option B: `alembic downgrade base && alembic upgrade head`.
- **Seed script** (`scripts/seed_demo.py`):
  - Creates sample brokers, assets (ETF, STOCK, LOAN with scheduled yield), cash deposits, and transactions.
  - Useful for local experimentation and GUI inspection.

Run with Pipenv:
```bash
pipenv run python scripts/reset_db.py
pipenv run python scripts/seed_demo.py
```

## 6) Useful queries

### Inventory per asset+broker
```sql
SELECT asset_id, broker_id,
       SUM(CASE WHEN type='BUY' THEN quantity
                WHEN type='SELL' THEN -quantity
                WHEN type='ADD_HOLDING' THEN quantity
                WHEN type='REMOVE_HOLDING' THEN -quantity
                WHEN type='TRANSFER_IN' THEN quantity
                WHEN type='TRANSFER_OUT' THEN -quantity
                ELSE 0 END) AS held_qty
FROM transactions
GROUP BY asset_id, broker_id
ORDER BY asset_id, broker_id;
```

### Cash balance by account
```sql
SELECT ca.id AS cash_account_id, ca.broker_id, ca.currency,
       SUM(CASE WHEN cm.type IN ('DEPOSIT','TRANSFER_IN','SALE_PROCEEDS','DIVIDEND_INCOME','INTEREST_INCOME')
                THEN cm.amount
                WHEN cm.type IN ('WITHDRAWAL','TRANSFER_OUT','BUY_SPEND','FEE','TAX')
                THEN -cm.amount
                ELSE 0 END) AS balance,
       MAX(cm.trade_date) AS last_op
FROM cash_accounts ca
LEFT JOIN cash_movements cm ON cm.cash_account_id = ca.id
GROUP BY ca.id, ca.broker_id, ca.currency
ORDER BY ca.broker_id, ca.currency;
```

### Price history for an asset
```sql
SELECT date, close, currency
FROM price_history
WHERE asset_id = :asset_id
ORDER BY date ASC;
```

### FX rate lookup for a day
```sql
SELECT date, base, quote, rate
FROM fx_rates
WHERE (base = 'USD' AND quote = 'EUR') AND date <= :d
ORDER BY date DESC
LIMIT 1;
```

## 7) Locking and concurrency
- SQLite supports one writer at a time; readers are concurrent with WAL mode.
- Avoid long write transactions.
- For batch imports, chunk operations and commit periodically; still keep per-item atomicity where needed.

## 8) Backups
- Safest backup is to **stop the container** and copy `app.db`.
- With WAL mode, you may copy `app.db`, `app.db-wal`, `app.db-shm` together to get a consistent snapshot.
- Or use the `.backup` command in `sqlite3` CLI.

## 9) Performance tips
- Keep indexes in sync with query patterns (`transactions(...)`, `cash_movements(...)`, `price_history(...)`).
- Run `ANALYZE;` occasionally after big imports.
- Avoid storing huge blobs; large raw payloads should be pruned or stored compressed if necessary.

## 10) Data hygiene & integrity checks
- Periodically verify inventory non-negative invariant by recomputing per (asset, broker) in date order.
- Verify cash non-negative policy only if enabled (`enforce_cash_non_negative=true`).
- Cross-check that every asset transaction that affects cash has a linked cash_movement (BUY_SPEND/SALE_PROCEEDS/DIVIDEND_INCOME/INTEREST_INCOME).

## 11) Inspect during Docker runtime
- If the DB directory is mounted, you can run queries using the `sqlite3` CLI on host:
```bash
sqlite3 ./data/sqlite/app.db "SELECT count(*) FROM transactions;"
```
- Or exec into the container and run sqlite3 if installed.

## 12) Bruno API tests
- Store a Bruno collection under `tests/bruno/` with variables (baseUrl). Include requests to create brokers/assets, deposit, buy, sell (oversell case), dividends, interest, transfers, and analysis.
- Use it to validate invariants after each development step.

---

This guide should help you quickly inspect and validate your schema, data, and invariants while you iterate on OFPF.
