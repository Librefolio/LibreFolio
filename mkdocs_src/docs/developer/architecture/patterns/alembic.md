# 🗃️ Database Migrations (Alembic)

LibreFolio uses **Alembic** to manage database schema changes. Alembic is a lightweight database migration tool for SQLAlchemy that provides a versioning system for your database
schema.

## 🔄 Workflow

The basic workflow for making a schema change is:

1. **Modify SQLAlchemy Models**: Make changes to your `db/models.py` files (e.g., add a new column, create a new table).

2. **Generate a Migration Script**: Run the `dev.py` command to automatically generate a new migration script.
   ```bash
   ./dev.py db migrate "Your descriptive message"
   ```
   This command compares your SQLAlchemy models to the current state of the database and generates a Python script in `backend/alembic/versions/` that contains the necessary
   `upgrade()` and `downgrade()` functions.

3. **Review the Migration Script**: **Always review the generated script.** Alembic is not perfect, especially with SQLite, and may require manual adjustments.

4. **Apply the Migration**: Run the `upgrade` command to apply the changes to your database.
   ```bash
   ./dev.py db upgrade
   ```

## 📦 One Migration per Release {: #one-migration-per-release }

Each release ships one migration: `004_release_1_2_0_schema` for 1.2, `005_release_1_3_0_schema` for 1.3 (the
developer's decision, 19/10/2026). During a cycle a migration is written whenever the work needs one; before the
release, the cycle's unreleased migrations are folded into one `00N_release_<version>_schema`, on the head of the
previous release. The chain as it stands is in [Migrations](../database/index.md#migrations).

1. **Only what no released tag holds.** A database stores the revision id in `alembic_version`, so an id that a
   released tag holds stays in the chain for good. Check each file before folding it:

    ```bash
    git cat-file -e <tag>:backend/alembic/versions/<file>   # succeeds when the tag holds the file
    ```

2. **Freeze the schema, then delete the chain.** Once its files are gone the chain cannot run, so first freeze the
   schema it builds on a new database. For 1.3: every row of `sqlite_master`, its SQL with whitespace collapsed, in
   `backend/test_scripts/fixtures/migrations/schema_1_3_retired_chain_v4.json`, never regenerated.
3. **Test the new file against it.** A new database taken to the new revision must be the frozen schema. For 1.3:
   `./dev.py test db migration-005` (`backend/test_scripts/test_db/test_migration_005_release_1_3.py`), which also
   carries the data scenarios of the retired tests.
4. **Keep the id within 32 characters**, as for any revision: Alembic's `alembic_version.version_num` is
   `VARCHAR(32)`. `005_release_1_3_0_schema` has 24.

`005_release_1_3_0_schema` keeps the work of the retired revisions as steps, in their order, each checking before it
acts, so that a run stopped half way can run again; its docstring maps each retired id to its step.

A database stamped with a retired id comes from an unreleased build. It is brought forward by hand, with the
procedure the developer journal keeps, never by code in the app: the server does not start on it, and a backup at
such an id is refused as from a newer LibreFolio (see «Retired revision ids» in
[Migrations](../database/index.md#migrations)).

## 🗂️ Indexes: Only the Ones a Query Uses {: #indexes }

An index costs space, and time on every insert and update, and serves only the queries that read it. The rule (the
developer's decision, 19/10/2026) came with an analysis that read every query of 67 endpoints with
`EXPLAIN QUERY PLAN`: `005_release_1_3_0_schema` dropped 13 indexes of `001_initial` (`001_initial.py` stays as
released), and no query plan got worse.

- **A `UNIQUE` constraint already creates its index** (`sqlite_autoindex_<table>_<n>`). Never add an `Index`,
  `index=True` or `CREATE INDEX` on the same columns: in a model, `Field(unique=True)` or a `UniqueConstraint`
  alone. `unique=True, index=True` makes `create_all` build a unique index where a migration writes the constraint,
  and `001_initial`, which wrote both, left six copies: `idx_price_history_asset_date`, `idx_asset_provider_asset_id`,
  `uq_assets_display_name` (the index; the `UNIQUE` on `display_name` stays), `ix_brokers_name`,
  `ix_users_username` and `ix_users_email`.
- **No index that is the left prefix of another.** `(broker_id, date, id)` already serves every query on
  `broker_id`, and SQLite's foreign-key checks on it. Five of the 13 were such prefixes:
  `ix_transactions_broker_id`, `ix_transactions_asset_id`, `ix_broker_user_access_user_id`, `idx_route_base_quote`
  and `ix_fx_conversion_routes_base`.
- **Every new index has a query that uses it, proven with `EXPLAIN QUERY PLAN`.** Name the query in the
  migration's docstring, with its plan line. The last two of the 13 had no reader: `ix_transactions_date` (every
  query on transactions is scoped by broker or asset) and `ix_fx_conversion_routes_quote` (a pair is always looked
  up with its base).

The plan line is what SQLite will do for the query, on any database at the revision:

```bash
sqlite3 app.db "EXPLAIN QUERY PLAN SELECT * FROM transactions WHERE broker_id = 1 ORDER BY date, id"
```

```text
QUERY PLAN
`--SEARCH transactions USING INDEX idx_transactions_broker_date (broker_id=?)
```

`SEARCH <table> USING INDEX <name>` (or `USING COVERING INDEX <name>`) is the proof that `<name>` serves the query;
`SCAN <table>` means that no index does. Here `idx_transactions_broker_date` serves a filter on its first column,
which is why `ix_transactions_broker_id` could go, and its `date` and `id` give the order with no
`USE TEMP B-TREE FOR ORDER BY` line. Filtered on `date` alone, the same query answers `SCAN transactions`: no index
serves it, and none needs to, since every query of the app on transactions is scoped by broker or asset.

**The guard.** `./dev.py test db validate` runs `test_no_redundant_indexes`
(`backend/test_scripts/test_db/db_schema_validate.py`). It reads every index of every table from SQLite's catalogue,
the automatic ones of the `UNIQUE` and `PRIMARY KEY` constraints included, and fails on an index whose key columns
equal another's, or are a left prefix of them, naming both. A `UNIQUE` index on a left prefix of a longer index (it
enforces a constraint the longer one does not), a partial index and an index on an expression (such as
`ux_users_email_lower` on `lower(email)`) are not redundancy. A redundancy kept on purpose goes in
`_REDUNDANT_INDEXES_ALLOWED`, the pair with its reason on one line; an entry that no longer matches a pair fails too.
An index nobody reads cannot be told from the catalogue: that is what the `EXPLAIN QUERY PLAN` rule is for.

## ⚠️ SQLite and Alembic Limitations

SQLite has limited support for `ALTER TABLE` statements, which can make schema migrations more complex than with other databases like PostgreSQL. Alembic works around this by using
a "batch mode" that:

1. Creates a new table with the desired schema.
2. Copies the data from the old table to the new table.
3. Drops the old table.
4. Renames the new table to the original name.

### 🔍 The `CHECK` Constraint Problem

A significant limitation of this approach is that **Alembic's autogenerate feature does not detect `CHECK` constraints in SQLite**.

This means that if you add or modify a `CHECK` constraint in your SQLAlchemy model, you **must manually add it** to the generated migration script.

#### 📝 Example: Manually Adding a `CHECK` Constraint

If you add a `CHECK` constraint to the `Transaction` model:

```python
class Transaction(SQLModel, table=True):
    # ...
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="check_quantity_positive"),
    )
```

Alembic will **not** include this in the autogenerated script. You must edit the `upgrade()` function in the migration file and add it yourself:

```python
# In the generated migration file: backend/alembic/versions/xxxx_add_check.py

def upgrade() -> None:
    # ... other operations ...

    with op.batch_alter_table('transaction', schema=None) as batch_op:
        batch_op.create_check_constraint(
            'check_quantity_positive',  # Constraint name
            'quantity >= 0'             # SQL expression
        )

def downgrade() -> None:
    # ... other operations ...

    with op.batch_alter_table('transaction', schema=None) as batch_op:
        batch_op.drop_constraint('check_quantity_positive', type_='check')
```

The `dev.py db upgrade` command includes a post-flight check that will warn you if `CHECK` constraints are missing after a migration, guiding you to fix the issue.
