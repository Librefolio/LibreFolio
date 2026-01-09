"""initial schema - squashed (v2)

Revision ID: 001_initial
Revises:
Create Date: 2025-12-22

REFACTORED for unified Transaction model.
Removed: cash_accounts, cash_movements
Added: users, user_settings, broker_user_access
Updated: transactions (unified), brokers (new flags)
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

    print("🔧 Starting migration 001_initial (v2 - Unified Transaction)...")
    print("=" * 60)

    # Users table (NEW)
    print("📦 Creating table: users...")
    conn.execute(sa.text("""CREATE TABLE users
                            (
                                id              INTEGER PRIMARY KEY,
                                username        VARCHAR(50) NOT NULL UNIQUE,
                                email           VARCHAR     NOT NULL UNIQUE,
                                hashed_password VARCHAR     NOT NULL,
                                is_active       BOOLEAN     NOT NULL DEFAULT 1,
                                is_superuser    BOOLEAN     NOT NULL DEFAULT 0,
                                created_at      DATETIME    NOT NULL,
                                updated_at      DATETIME    NOT NULL
                            )"""))
    print("  ✓ Table created")
    conn.execute(sa.text("CREATE UNIQUE INDEX ix_users_username ON users (username)"))
    conn.execute(sa.text("CREATE UNIQUE INDEX ix_users_email ON users (email)"))
    print("  ✓ 2 Indexes created")

    # User Settings table (NEW)
    print("📦 Creating table: user_settings...")
    conn.execute(sa.text("""CREATE TABLE user_settings
                            (
                                id            INTEGER PRIMARY KEY,
                                user_id       INTEGER     NOT NULL UNIQUE,
                                base_currency VARCHAR(3)  NOT NULL DEFAULT 'EUR',
                                language      VARCHAR(5)  NOT NULL DEFAULT 'en',
                                theme         VARCHAR(20) NOT NULL DEFAULT 'light',
                                created_at    DATETIME    NOT NULL,
                                updated_at    DATETIME    NOT NULL,
                                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                                CONSTRAINT uq_user_settings_user_id UNIQUE (user_id)
                            )"""))
    print("  ✓ Table created")

    # Assets table
    print("📦 Creating table: assets...")
    conn.execute(sa.text("""CREATE TABLE assets
                            (
                                id                    INTEGER PRIMARY KEY,
                                display_name          VARCHAR     NOT NULL UNIQUE,
                                currency              VARCHAR     NOT NULL,
                                icon_url              VARCHAR,
                                classification_params TEXT,
                                asset_type            VARCHAR(14) NOT NULL,
                                active                BOOLEAN     NOT NULL,
                                identifier_isin       VARCHAR(12),
                                identifier_ticker     VARCHAR(20),
                                identifier_cusip      VARCHAR(9),
                                identifier_sedol      VARCHAR(7),
                                identifier_figi       VARCHAR(12),
                                identifier_uuid       VARCHAR(36),
                                identifier_other      VARCHAR(100),
                                created_at            DATETIME    NOT NULL,
                                updated_at            DATETIME    NOT NULL
                            )"""))
    print("  ✓ Table created")
    conn.execute(sa.text("CREATE UNIQUE INDEX uq_assets_display_name ON assets (display_name)"))
    conn.execute(sa.text("CREATE INDEX ix_assets_identifier_isin ON assets (identifier_isin)"))
    conn.execute(sa.text("CREATE INDEX ix_assets_identifier_ticker ON assets (identifier_ticker)"))
    print("  ✓ 3 Indexes created")

    # Brokers table (UPDATED with new flags)
    print("📦 Creating table: brokers...")
    conn.execute(sa.text("""CREATE TABLE brokers
                            (
                                id                   INTEGER PRIMARY KEY,
                                name                 VARCHAR  NOT NULL UNIQUE,
                                description          TEXT,
                                portal_url           VARCHAR,
                                allow_cash_overdraft BOOLEAN  NOT NULL DEFAULT 0,
                                allow_asset_shorting BOOLEAN  NOT NULL DEFAULT 0,
                                created_at           DATETIME NOT NULL,
                                updated_at           DATETIME NOT NULL
                            )"""))
    print("  ✓ Table created")
    conn.execute(sa.text("CREATE UNIQUE INDEX ix_brokers_name ON brokers (name)"))
    print("  ✓ Index created")

    # Broker User Access table (NEW)
    print("📦 Creating table: broker_user_access...")
    conn.execute(sa.text("""CREATE TABLE broker_user_access
                            (
                                id         INTEGER PRIMARY KEY,
                                user_id    INTEGER     NOT NULL,
                                broker_id  INTEGER     NOT NULL,
                                role       VARCHAR(10) NOT NULL DEFAULT 'VIEWER',
                                created_at DATETIME    NOT NULL,
                                updated_at DATETIME    NOT NULL,
                                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                                FOREIGN KEY (broker_id) REFERENCES brokers (id) ON DELETE CASCADE,
                                CONSTRAINT uq_broker_user_access UNIQUE (user_id, broker_id)
                            )"""))
    print("  ✓ Table created")
    conn.execute(sa.text("CREATE INDEX ix_broker_user_access_user_id ON broker_user_access (user_id)"))
    conn.execute(sa.text("CREATE INDEX ix_broker_user_access_broker_id ON broker_user_access (broker_id)"))
    print("  ✓ 2 Indexes created")

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
                                asset_id        INTEGER     NOT NULL UNIQUE,
                                provider_code   VARCHAR(50) NOT NULL,
                                identifier      VARCHAR     NOT NULL,
                                identifier_type VARCHAR(6)  NOT NULL,
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
                                volume            NUMERIC(24, 0),
                                adjusted_close    NUMERIC(18, 6),
                                currency          VARCHAR  NOT NULL,
                                source_plugin_key VARCHAR  NOT NULL,
                                fetched_at        DATETIME NOT NULL,
                                FOREIGN KEY (asset_id) REFERENCES assets (id) ON DELETE CASCADE,
                                CONSTRAINT uq_price_history_asset_date UNIQUE (asset_id, date)
                            )"""))
    print("  ✓ Table created")
    conn.execute(sa.text("CREATE INDEX idx_price_history_asset_date ON price_history (asset_id, date)"))
    print("  ✓ Index created")

    # Unified Transactions table (REFACTORED)
    # NOTE: related_transaction_id uses DEFERRABLE INITIALLY DEFERRED FK
    # This allows bidirectional linking (A->B and B->A) within the same transaction.
    # The FK constraint is only checked at COMMIT, not at INSERT/UPDATE time.
    print("📦 Creating table: transactions (UNIFIED)...")
    conn.execute(sa.text("""CREATE TABLE transactions
                            (
                                id                     INTEGER PRIMARY KEY,
                                broker_id              INTEGER        NOT NULL,
                                asset_id               INTEGER,
                                type                   VARCHAR(14)    NOT NULL,
                                date                   DATE           NOT NULL,
                                quantity               NUMERIC(18, 6) NOT NULL DEFAULT 0,
                                amount                 NUMERIC(18, 6) NOT NULL DEFAULT 0,
                                currency               VARCHAR(3),
                                related_transaction_id INTEGER,
                                tags                   TEXT,
                                description            TEXT,
                                created_at             DATETIME       NOT NULL,
                                updated_at             DATETIME       NOT NULL,
                                FOREIGN KEY (broker_id) REFERENCES brokers (id),
                                FOREIGN KEY (asset_id) REFERENCES assets (id),
                                FOREIGN KEY (related_transaction_id) REFERENCES transactions (id)
                                    DEFERRABLE INITIALLY DEFERRED
                            )"""))
    print("  ✓ Table created")
    conn.execute(sa.text("CREATE INDEX idx_transactions_broker_date ON transactions (broker_id, date, id)"))
    conn.execute(sa.text("CREATE INDEX idx_transactions_asset_date ON transactions (asset_id, date)"))
    conn.execute(sa.text("CREATE INDEX idx_transactions_related ON transactions (related_transaction_id)"))
    conn.execute(sa.text("CREATE INDEX ix_transactions_broker_id ON transactions (broker_id)"))
    conn.execute(sa.text("CREATE INDEX ix_transactions_asset_id ON transactions (asset_id)"))
    conn.execute(sa.text("CREATE INDEX ix_transactions_date ON transactions (date)"))
    print("  ✓ 6 Indexes created")

    print("=" * 60)
    print("✅ Migration 001_initial (v2) completed successfully!")
    print("📊 Created 10 tables with all indexes and constraints")
    print("🆕 New: users, user_settings, broker_user_access")
    print("🔄 Updated: brokers (flags), transactions (unified)")
    print("🗑️  Removed: cash_accounts, cash_movements")


def downgrade() -> None:
    """Drop all tables."""
    conn = op.get_bind()
    for table in [
        'transactions', 'price_history', 'asset_provider_assignments',
        'fx_currency_pair_sources', 'fx_rates', 'broker_user_access',
        'brokers', 'assets', 'user_settings', 'users'
        ]:
        conn.execute(sa.text(f"DROP TABLE IF EXISTS {table}"))
