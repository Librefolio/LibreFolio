-- LibreFolio database schema as released in v1.1.0 (Alembic revision 5b1333fa6b07), schema only.
-- Used by the post-migration tests (plan 34_accountAndIdReuse): an existing 1.1 install upgraded to head.
-- Generated, never hand-edited:
--   git archive v1.1.0 backend/alembic backend/alembic.ini | tar -x -C <tmp>
--   cd <tmp> && PYTHONPATH=<repo> LIBREFOLIO_TEST_MODE=1 alembic -c backend/alembic.ini \
--       -x sqlalchemy.url=sqlite:///<tmp>/v110.db upgrade head
--   then every sqlite_master statement in creation order (rowid), trailing spaces stripped, plus the alembic_version row.

CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL,
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

CREATE TABLE users
               (
                   id                                 INTEGER PRIMARY KEY,
                   username                           VARCHAR(50) NOT NULL UNIQUE,
                   email                              VARCHAR     NOT NULL UNIQUE,
                   hashed_password                    VARCHAR     NOT NULL,
                   is_active                          BOOLEAN     NOT NULL DEFAULT 1,
                   is_superuser                       BOOLEAN     NOT NULL DEFAULT 0,
                   login_count                        INTEGER     NOT NULL DEFAULT 0,
                   donation_popup_last_shown_at       DATETIME             DEFAULT NULL,
                   donation_popup_logins_since_shown  INTEGER     NOT NULL DEFAULT 0,
                   created_at                         DATETIME    NOT NULL,
                   updated_at                         DATETIME    NOT NULL
               );

CREATE UNIQUE INDEX ix_users_username ON users (username);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE user_settings
               (
                   id            INTEGER PRIMARY KEY,
                   user_id       INTEGER     NOT NULL UNIQUE,
                   base_currency VARCHAR(3)  NOT NULL DEFAULT 'EUR',
                   language      VARCHAR(5)  NOT NULL DEFAULT 'en',
                   theme         VARCHAR(20) NOT NULL DEFAULT 'light',
                   avatar_url    VARCHAR(500)         DEFAULT NULL,
                   created_at    DATETIME    NOT NULL,
                   updated_at    DATETIME    NOT NULL,
                   FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                   CONSTRAINT uq_user_settings_user_id UNIQUE (user_id)
               );

CREATE TABLE global_settings
               (
                   key                VARCHAR(100) PRIMARY KEY,
                   value              TEXT        NOT NULL,
                   value_type         VARCHAR(20) NOT NULL,
                   description        TEXT,
                   updated_at         DATETIME    NOT NULL,
                   updated_by_user_id INTEGER,
                   FOREIGN KEY (updated_by_user_id) REFERENCES users (id) ON DELETE SET NULL
               );

CREATE TABLE assets
               (
                   id                    INTEGER PRIMARY KEY,
                   display_name          VARCHAR     NOT NULL UNIQUE,
                   currency              VARCHAR     NOT NULL,
                   icon_url              VARCHAR,
                   classification_params TEXT,
                   asset_type            VARCHAR(14) NOT NULL,
                   quote_base_quantity   INTEGER     DEFAULT 1,
                   active                BOOLEAN     NOT NULL,
                   user_url              VARCHAR     DEFAULT NULL,
                   identifier_isin       VARCHAR(12),
                   identifier_ticker     VARCHAR(20),
                   identifier_cusip      VARCHAR(9),
                   identifier_sedol      VARCHAR(7),
                   identifier_figi       VARCHAR(12),
                   identifier_uuid       VARCHAR(36),
                   identifier_other      VARCHAR(100),
                   created_at            DATETIME    NOT NULL,
                   updated_at            DATETIME    NOT NULL
               );

CREATE UNIQUE INDEX uq_assets_display_name ON assets (display_name);

CREATE INDEX ix_assets_identifier_isin ON assets (identifier_isin);

CREATE INDEX ix_assets_identifier_ticker ON assets (identifier_ticker);

CREATE TABLE brokers
               (
                   id                    INTEGER PRIMARY KEY,
                   name                  VARCHAR  NOT NULL UNIQUE,
                   description           TEXT,
                   portal_url            VARCHAR,
                   icon_url              VARCHAR,
                   default_import_plugin VARCHAR,
                   allow_cash_overdraft  BOOLEAN  NOT NULL DEFAULT 0,
                   allow_asset_shorting  BOOLEAN  NOT NULL DEFAULT 0,
                   is_active             BOOLEAN  NOT NULL DEFAULT 1,
                   opened_at             DATE,
                   created_at            DATETIME NOT NULL,
                   updated_at            DATETIME NOT NULL
               );

CREATE UNIQUE INDEX ix_brokers_name ON brokers (name);

CREATE TABLE broker_user_access
               (
                   id               INTEGER PRIMARY KEY,
                   user_id          INTEGER       NOT NULL,
                   broker_id        INTEGER       NOT NULL,
                   role             VARCHAR(10)   NOT NULL DEFAULT 'VIEWER',
                   share_percentage NUMERIC(7, 6) NOT NULL DEFAULT 1,
                   created_at       DATETIME      NOT NULL,
                   updated_at       DATETIME      NOT NULL,
                   FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                   FOREIGN KEY (broker_id) REFERENCES brokers (id) ON DELETE CASCADE,
                   CONSTRAINT uq_broker_user_access UNIQUE (user_id, broker_id),
                   CONSTRAINT chk_broker_user_access_role CHECK (role IN ('OWNER', 'EDITOR', 'VIEWER')),
                   CONSTRAINT ck_broker_user_access_share_percentage CHECK (share_percentage >= 0 AND share_percentage <= 1)
               );

CREATE INDEX ix_broker_user_access_user_id ON broker_user_access (user_id);

CREATE INDEX ix_broker_user_access_broker_id ON broker_user_access (broker_id);

CREATE TABLE fx_rates
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
               );

CREATE INDEX idx_fx_rates_base_quote_date ON fx_rates (base, quote, date);

CREATE TABLE fx_conversion_routes
               (
                   id             INTEGER PRIMARY KEY,
                   base           VARCHAR  NOT NULL,
                   quote          VARCHAR  NOT NULL,
                   priority       INTEGER  NOT NULL DEFAULT 1,
                   chain_steps    TEXT     NOT NULL,
                   created_at     DATETIME NOT NULL,
                   updated_at     DATETIME NOT NULL,
                   CONSTRAINT uq_route_base_quote_priority UNIQUE (base, quote, priority),
                   CONSTRAINT ck_route_base_less_than_quote CHECK (base < quote)
               );

CREATE INDEX idx_route_base_quote ON fx_conversion_routes (base, quote);

CREATE INDEX ix_fx_conversion_routes_base ON fx_conversion_routes (base);

CREATE INDEX ix_fx_conversion_routes_quote ON fx_conversion_routes (quote);

CREATE TABLE asset_provider_assignments
               (
                   id              INTEGER PRIMARY KEY,
                   asset_id        INTEGER     NOT NULL UNIQUE,
                   provider_code   VARCHAR(50) NOT NULL,
                   identifier      VARCHAR,
                   identifier_type VARCHAR(20) NOT NULL,
                   provider_params TEXT,
                   last_fetch_at   DATETIME,
                   created_at      DATETIME    NOT NULL,
                   updated_at      DATETIME    NOT NULL,
                   FOREIGN KEY (asset_id) REFERENCES assets (id) ON DELETE CASCADE,
                   CONSTRAINT uq_asset_provider_asset_id UNIQUE (asset_id)
               );

CREATE INDEX idx_asset_provider_asset_id ON asset_provider_assignments (asset_id);

CREATE TABLE price_history
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
               );

CREATE INDEX idx_price_history_asset_date ON price_history (asset_id, date);

CREATE TABLE asset_events
               (
                   id                     INTEGER PRIMARY KEY,
                   asset_id               INTEGER        NOT NULL,
                   date                   DATE           NOT NULL,
                   type                   VARCHAR        NOT NULL,
                   value                  NUMERIC(18, 6) NOT NULL,
                   currency               VARCHAR        NOT NULL,
                   provider_assignment_id INTEGER,
                   notes                  TEXT,
                   created_at             DATETIME       NOT NULL,
                   updated_at             DATETIME       NOT NULL,
                   FOREIGN KEY (asset_id) REFERENCES assets (id) ON DELETE CASCADE,
                   FOREIGN KEY (provider_assignment_id) REFERENCES asset_provider_assignments (id) ON DELETE CASCADE
               );

CREATE INDEX idx_asset_event_asset_date ON asset_events (asset_id, date);

CREATE INDEX idx_asset_event_asset_type_date ON asset_events (asset_id, type, date);

CREATE INDEX idx_asset_event_provider_assignment ON asset_events (provider_assignment_id);

CREATE TABLE transactions
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
                   cost_basis_override    NUMERIC(18, 6),
                   cost_basis_currency    VARCHAR(3),
                   asset_event_id         INTEGER,
                   created_at             DATETIME       NOT NULL,
                   updated_at             DATETIME       NOT NULL,
                   FOREIGN KEY (broker_id) REFERENCES brokers (id),
                   FOREIGN KEY (asset_id) REFERENCES assets (id),
                   FOREIGN KEY (related_transaction_id) REFERENCES transactions (id)
                       DEFERRABLE INITIALLY DEFERRED,
                   FOREIGN KEY (asset_event_id) REFERENCES asset_events (id) ON DELETE RESTRICT
               );

CREATE INDEX idx_transactions_broker_date ON transactions (broker_id, date, id);

CREATE INDEX idx_transactions_asset_date ON transactions (asset_id, date);

CREATE INDEX idx_transactions_related ON transactions (related_transaction_id);

CREATE INDEX idx_transactions_asset_event ON transactions (asset_event_id);

CREATE INDEX ix_transactions_broker_id ON transactions (broker_id);

CREATE INDEX ix_transactions_asset_id ON transactions (asset_id);

CREATE INDEX ix_transactions_date ON transactions (date);

INSERT INTO alembic_version (version_num) VALUES ('5b1333fa6b07');
