# 🗄️ Database Schema

The LibreFolio database is designed using SQLAlchemy with SQLModel. The schema is stored in a single SQLite file (`app.db`).

> 💡 **Tip**: To explore the live database schema interactively (including all constraints and indexes), we recommend using a tool like **DBeaver** or **DB Browser for SQLite** connected to your local `backend/data/sqlite/app.db` file.

## Logical Data Flow

This diagram illustrates how data flows from the User down to the financial records.

```mermaid
graph TD
    User[User] -->|Owns| Broker[Broker Account]
    User -->|Has| Settings[User Settings]
    
    Broker -->|Contains| Tx[Transactions]
    
    Tx -->|References| Asset[Global Asset]
    Asset -->|Has| Prices[Price History]
    
    subgraph "Global Data"
        Asset
        Prices
        FX[FX Rates]
    end
    
    subgraph "User Data"
        User
        Settings
        Broker
        Tx
    end
```

## Subsystems

### 1. User & Access Control

Manages authentication and the sharing of brokers between users.

```mermaid
erDiagram
    USER ||--|| USER_SETTINGS : "has preferences"
    USER ||--o{ BROKER_USER_ACCESS : "has access"
    BROKER ||--o{ BROKER_USER_ACCESS : "granted to"

    USER {
        int id PK
        string username
        string hashed_password
    }

    BROKER_USER_ACCESS {
        int user_id FK
        int broker_id FK
        enum role "OWNER, EDITOR, VIEWER"
    }
```

-   **`BROKER_USER_ACCESS`**: The pivot table for the Many-to-Many relationship. It stores the `role` defining permissions.

### 2. Broker & Transactions

The core financial data structure.

```mermaid
erDiagram
    BROKER ||--o{ TRANSACTION : "contains"
    TRANSACTION |o--o| TRANSACTION : "related to"

    BROKER {
        int id PK
        string name
        bool allow_cash_overdraft
    }

    TRANSACTION {
        int id PK
        int broker_id FK
        int asset_id FK "Nullable"
        int related_transaction_id FK "Nullable"
        enum type "BUY, SELL..."
        decimal quantity
        decimal amount
    }
```

-   **`TRANSACTION`**: The single source of truth.
    -   **`related_transaction_id`**: Self-reference for paired operations (Transfers, FX Conversions).

### 3. Asset Management

Global financial instruments and their pricing sources.

```mermaid
erDiagram
    ASSET ||--o{ TRANSACTION : "referenced in"
    ASSET ||--o{ PRICE_HISTORY : "has history"
    ASSET ||--|| ASSET_PROVIDER_ASSIGNMENT : "priced by"

    ASSET {
        int id PK
        string display_name
        string identifier_isin
        string identifier_ticker
        json classification_params
    }

    ASSET_PROVIDER_ASSIGNMENT {
        int asset_id FK
        string provider_code
        string identifier
    }
```

-   **`ASSET`**: Global definition. `classification_params` (JSON) stores metadata like Sector and Geography.
-   **`ASSET_PROVIDER_ASSIGNMENT`**: Decouples the asset from its data source (e.g., "Use Yahoo Finance for AAPL").

### 4. FX Subsystem

Currency exchange rates and routing configuration.

```mermaid
erDiagram
    FX_RATE
    FX_CURRENCY_PAIR_SOURCE

    FX_RATE {
        date date
        string base
        string quote
        decimal rate
    }
    
    FX_CURRENCY_PAIR_SOURCE {
        string base
        string quote
        string provider_code
        int priority
    }
```

-   **`FX_RATE`**: Stores daily rates. Enforces `base < quote` (alphabetical) to prevent duplicates.
-   **`FX_CURRENCY_PAIR_SOURCE`**: Configures which provider (ECB, FED) to use for which pair.

## Design Philosophy

1.  **Normalization**: Assets are global; Transactions are broker-specific.
2.  **Strict Constraints**:
    -   `CHECK` constraints ensure logical consistency.
    -   Foreign Keys are enforced (`PRAGMA foreign_keys=ON`).
3.  **JSON for Flexibility**: Used for `classification_params` and `provider_params` to allow schema-less extension.
