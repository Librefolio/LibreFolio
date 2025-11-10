"""initial schema - squashed

Revision ID: 001_initial
Revises:
Create Date: 2025-11-06

SQUASHED from 9 migrations (37d14b3d7a82..a63a8001e62c)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '001_initial'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables."""
    conn = op.get_bind()

    print("🔧 Starting migration 001_initial...")
    print("=" * 60)

    # Assets table
    print("📦 Creating table: assets...")
    conn.execute(sa.text("""CREATE TABLE assets
                            (
                                id                INTEGER PRIMARY KEY,
                                display_name      VARCHAR     NOT NULL,
                                identifier        VARCHAR     NOT NULL,
                                identifier_type   VARCHAR(6)  NOT NULL,
                                currency          VARCHAR     NOT NULL,
                                asset_type        VARCHAR(14) NOT NULL,
                                valuation_model   VARCHAR(15) NOT NULL,
                                face_value        NUMERIC(18, 6),
                                maturity_date     DATE,
                                interest_schedule TEXT,
                                late_interest     TEXT,
                                active            BOOLEAN     NOT NULL,
                                created_at        DATETIME    NOT NULL,
                                updated_at        DATETIME    NOT NULL
                            )"""))
    print("  ✓ Table created")
    conn.execute(sa.text("CREATE INDEX ix_assets_identifier ON assets (identifier)"))
    print("  ✓ Index created")

    # Brokers table
    print("📦 Creating table: brokers...")
    conn.execute(sa.text("""CREATE TABLE brokers
                            (
                                id          INTEGER PRIMARY KEY,
                                name        VARCHAR  NOT NULL,
                                description TEXT,
                                portal_url  VARCHAR,
                                created_at  DATETIME NOT NULL,
                                updated_at  DATETIME NOT NULL
                            )"""))
    print("  ✓ Table created")
    conn.execute(sa.text("CREATE UNIQUE INDEX ix_brokers_name ON brokers (name)"))
    print("  ✓ Index created")

    # FX rates table
    print("📦 Creating table: fx_rates...")
    conn.execute(sa.text("""CREATE TABLE fx_rates
                            (
                                id         INTEGER PRIMARY KEY,
                                date       DATE            NOT NULL,
                                base       VARCHAR         NOT NULL,
                                quote      VARCHAR         NOT NULL,
                                rate       NUMERIC(24, 10) NOT NULL,
                                source     VARCHAR         NOT NULL,
                                fetched_at DATETIME        NOT NULL,
                                CONSTRAINT ck_fx_rates_base_less_than_quote CHECK (base < quote),
                                CONSTRAINT uq_fx_rates_date_base_quote UNIQUE (date, base, quote)
                            )"""))
    print("  ✓ Table created")
    conn.execute(sa.text("CREATE INDEX idx_fx_rates_base_quote_date ON fx_rates (base, quote, date)"))
    print("  ✓ Index created")

    # FX currency pair sources table
    print("📦 Creating table: fx_currency_pair_sources...")
    conn.execute(sa.text("""CREATE TABLE fx_currency_pair_sources
                            (
                                id             INTEGER PRIMARY KEY,
                                base           VARCHAR  NOT NULL,
                                quote          VARCHAR  NOT NULL,
                                provider_code  VARCHAR  NOT NULL,
                                priority       INTEGER  NOT NULL,
                                fetch_interval INTEGER,
                                created_at     DATETIME NOT NULL,
                                updated_at     DATETIME NOT NULL,
                                CONSTRAINT uq_pair_source_base_quote_priority UNIQUE (base, quote, priority)
                            )"""))
    print("  ✓ Table created")
    conn.execute(sa.text("CREATE INDEX idx_pair_source_base_quote ON fx_currency_pair_sources (base, quote)"))
    conn.execute(sa.text("CREATE INDEX ix_fx_currency_pair_sources_base ON fx_currency_pair_sources (base)"))
    conn.execute(sa.text("CREATE INDEX ix_fx_currency_pair_sources_quote ON fx_currency_pair_sources (quote)"))
    print("  ✓ 3 Indexes created")

    # Asset provider assignments table
    print("📦 Creating table: asset_provider_assignments...")
    conn.execute(sa.text("""CREATE TABLE asset_provider_assignments
                            (
                                id              INTEGER PRIMARY KEY,
                                asset_id        INTEGER     NOT NULL,
                                provider_code   VARCHAR(50) NOT NULL,
                                provider_params TEXT,
                                last_fetch_at   DATETIME,
                                fetch_interval  INTEGER,
                                created_at      DATETIME    NOT NULL,
                                updated_at      DATETIME    NOT NULL,
                                FOREIGN KEY (asset_id) REFERENCES assets (id) ON DELETE CASCADE,
                                CONSTRAINT uq_asset_provider_asset_id UNIQUE (asset_id)
                            )"""))
    print("  ✓ Table created")
    conn.execute(sa.text("CREATE INDEX idx_asset_provider_asset_id ON asset_provider_assignments (asset_id)"))
    print("  ✓ Index created")

    # Cash accounts table
    print("📦 Creating table: cash_accounts...")
    conn.execute(sa.text("""CREATE TABLE cash_accounts
                            (
                                id           INTEGER PRIMARY KEY,
                                broker_id    INTEGER  NOT NULL,
                                currency     VARCHAR  NOT NULL,
                                display_name VARCHAR  NOT NULL,
                                created_at   DATETIME NOT NULL,
                                updated_at   DATETIME NOT NULL,
                                FOREIGN KEY (broker_id) REFERENCES brokers (id),
                                CONSTRAINT uq_cash_accounts_broker_currency UNIQUE (broker_id, currency)
                            )"""))
    print("  ✓ Table created")
    conn.execute(sa.text("CREATE INDEX ix_cash_accounts_broker_id ON cash_accounts (broker_id)"))
    print("  ✓ Index created")

    # Price history table
    print("📦 Creating table: price_history...")
    conn.execute(sa.text("""CREATE TABLE price_history
                            (
                                id                INTEGER PRIMARY KEY,
                                asset_id          INTEGER  NOT NULL,
                                date              DATE     NOT NULL,
                                open              NUMERIC(18, 6),
                                high              NUMERIC(18, 6),
                                low               NUMERIC(18, 6),
                                close             NUMERIC(18, 6),
                                adjusted_close    NUMERIC(18, 6),
                                currency          VARCHAR  NOT NULL,
                                source_plugin_key VARCHAR  NOT NULL,
                                fetched_at        DATETIME NOT NULL,
                                FOREIGN KEY (asset_id) REFERENCES assets (id),
                                CONSTRAINT uq_price_history_asset_date UNIQUE (asset_id, date)
                            )"""))
    print("  ✓ Table created")
    conn.execute(sa.text("CREATE INDEX idx_price_history_asset_date ON price_history (asset_id, date)"))
    print("  ✓ Index created")

    # Transactions table
    print("📦 Creating table: transactions...")
    conn.execute(sa.text("""CREATE TABLE transactions
                            (
                                id              INTEGER PRIMARY KEY,
                                asset_id        INTEGER        NOT NULL,
                                broker_id       INTEGER        NOT NULL,
                                type            VARCHAR(14)    NOT NULL,
                                quantity        NUMERIC(18, 6) NOT NULL,
                                price           NUMERIC(18, 6),
                                currency        VARCHAR        NOT NULL,
                                fees            NUMERIC(18, 6),
                                taxes           NUMERIC(18, 6),
                                trade_date      DATE           NOT NULL,
                                settlement_date DATE,
                                note            TEXT,
                                created_at      DATETIME       NOT NULL,
                                updated_at      DATETIME       NOT NULL,
                                FOREIGN KEY (asset_id) REFERENCES assets (id),
                                FOREIGN KEY (broker_id) REFERENCES brokers (id)
                            )"""))
    print("  ✓ Table created")
    conn.execute(sa.text("CREATE INDEX idx_transactions_asset_broker_date ON transactions (asset_id, broker_id, trade_date, id)"))
    conn.execute(sa.text("CREATE INDEX ix_transactions_asset_id ON transactions (asset_id)"))
    conn.execute(sa.text("CREATE INDEX ix_transactions_broker_id ON transactions (broker_id)"))
    conn.execute(sa.text("CREATE INDEX ix_transactions_trade_date ON transactions (trade_date)"))
    print("  ✓ 4 Indexes created")

    # Cash movements table
    print("📦 Creating table: cash_movements...")
    conn.execute(sa.text("""CREATE TABLE cash_movements
                            (
                                id                    INTEGER PRIMARY KEY,
                                cash_account_id       INTEGER        NOT NULL,
                                type                  VARCHAR(15)    NOT NULL,
                                amount                NUMERIC(18, 6) NOT NULL,
                                trade_date            DATE           NOT NULL,
                                note                  TEXT,
                                linked_transaction_id INTEGER,
                                created_at            DATETIME       NOT NULL,
                                updated_at            DATETIME       NOT NULL,
                                FOREIGN KEY (cash_account_id) REFERENCES cash_accounts (id),
                                FOREIGN KEY (linked_transaction_id) REFERENCES transactions (id)
                            )"""))
    print("  ✓ Table created")
    conn.execute(sa.text("CREATE INDEX idx_cash_movements_account_date ON cash_movements (cash_account_id, trade_date, id)"))
    conn.execute(sa.text("CREATE INDEX ix_cash_movements_cash_account_id ON cash_movements (cash_account_id)"))
    conn.execute(sa.text("CREATE INDEX ix_cash_movements_linked_transaction_id ON cash_movements (linked_transaction_id)"))
    conn.execute(sa.text("CREATE INDEX ix_cash_movements_trade_date ON cash_movements (trade_date)"))
    print("  ✓ 4 Indexes created")

    print("=" * 60)
    print("✅ Migration 001_initial completed successfully!")
    print("📊 Created 9 tables with all indexes and constraints")


def downgrade() -> None:
    """Drop all tables."""
    conn = op.get_bind()
    for table in [
        'cash_movements', 'transactions', 'price_history', 'cash_accounts',
        'asset_provider_assignments', 'fx_currency_pair_sources', 'fx_rates',
        'brokers', 'assets'
        ]:
        conn.execute(sa.text(f"DROP TABLE IF EXISTS {table}"))
