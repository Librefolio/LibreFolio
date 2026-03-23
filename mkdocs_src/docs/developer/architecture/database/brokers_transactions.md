# 🏦 Brokers & Transactions

The core financial data structure. Brokers are containers for transactions, and transactions are the single source of truth for all portfolio calculations.

## 📐 ER Diagram

```mermaid
erDiagram
    BROKER ||--o{ TRANSACTION : "contains"
    TRANSACTION |o--o| TRANSACTION : "related to"
    TRANSACTION }o--o| ASSET : "references"
    TRANSACTION }o..o| FX_RATE : "currency (logical)"

    BROKER {
        int id PK
        string name
        string base_currency "ISO 4217"
        string icon_url
        bool allow_cash_overdraft
    }

    TRANSACTION {
        int id PK
        int broker_id FK
        int asset_id FK "Nullable"
        int related_transaction_id FK "Nullable"
        enum type "BUY, SELL..."
        date date
        decimal quantity
        decimal unit_price
        decimal amount
        string currency "ISO 4217"
    }

    FX_RATE {
        date date
        string base "ISO 4217"
        string quote "ISO 4217"
        decimal rate
    }
```

## 📋 Tables

### 🏦 `BROKER`

Represents a brokerage account (e.g., Interactive Brokers, Degiro, a bank account). Each broker has a `base_currency` used for cash balance tracking and an optional `icon_url` for the UI.

- 🚫 **`allow_cash_overdraft`**: When `false`, the system prevents transactions that would result in a negative cash balance.

### 💰 `TRANSACTION`

The single source of truth for all financial operations. Each transaction belongs to exactly one broker.

- 🏷️ **`type`**: One of the [Transaction Types](../../../financial-theory/transaction-types.md) (BUY, SELL, DIVIDEND, DEPOSIT, WITHDRAWAL, FX_CONVERSION, TRANSFER, etc.)
- 📈 **`asset_id`**: References a global [Asset](assets_pricing.md). Nullable for cash-only operations (DEPOSIT, WITHDRAWAL).
- 🔗 **`related_transaction_id`**: Self-referencing foreign key for paired operations:
    - 🔄 **Transfers**: Links the WITHDRAWAL from Broker A to the DEPOSIT in Broker B
    - 💱 **FX Conversions**: Links the sell-side to the buy-side of a currency exchange

---

## 💱 Currency & FX Integration

The `currency` field in `TRANSACTION` and `base_currency` in `BROKER` are **ISO 4217 strings** (e.g., `EUR`, `USD`, `JPY`). There is **no foreign key** to an FX table — currencies are standard codes validated in the backend using the ISO 4217 reference list from `pycountry`.

The dotted line in the ER diagram represents a **logical relationship**, not a relational one:

- When the system needs to **convert between currencies** (e.g., aggregating a multi-currency portfolio into a single display currency), it queries the [FX Rates subsystem](fx_rates.md) for the appropriate exchange rate.
- The backend resolves conversion chains automatically — for example, to convert RON → JPY, it may route through EUR as an intermediate currency.

!!! info "Why no currency table?"

    Currencies are an international standard (ISO 4217) with a fixed, well-known list. Storing them as strings avoids unnecessary joins while keeping validation strict at the application layer.

For details on how FX conversion works, see [FX Architecture](../../backend/fx/architecture.md) and [FX Configuration & Routing](../../backend/fx/configuration.md).

## 🔗 Related Documentation

- 📖 [Brokers (User Guide)](../../../user/brokers/index.md) — How to create and manage brokers
- 🤝 [Broker Sharing](../../../user/brokers/sharing.md) — RBAC sharing system
- 📚 [Transaction Types (Financial Theory)](../../../financial-theory/transaction-types.md) — Definitions of all transaction types
