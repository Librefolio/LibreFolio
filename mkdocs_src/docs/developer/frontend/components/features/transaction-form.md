# 📝 Transaction Form Modal

The Transaction Form Modal is a complex domain component responsible for creating and editing financial transactions. It dynamically adjusts its fields, performs real-time reactive calculations, and interacts with the backend validation engine.

## 🏗️ Architecture

The form operates on a transient reactive state before data is persisted.

### DraftRow vs PendingOp

It is crucial to understand the distinction between the UI state and the backend state during transaction editing:

- **`DraftRow`**: The localized, reactive Svelte 5 state inside the form. It holds the user's current inputs (which might be temporarily invalid or incomplete). It uses Svelte's `$state` runes to allow instant, unvalidated changes.
- **`PendingOp`**: Once the user hits "Save", the `DraftRow` is sanitized and cast into a `PendingOp` payload. This is sent to the backend's validation queue where it is evaluated against the user's actual portfolio balances before being committed to the database.

## 🗄️ State Schema

The `DraftRow` dynamically mounts different fields based on the selected **Transaction Type**.

### Common Fields

Present for all operations:

| Field | Type | Description |
|-------|------|-------------|
| `type` | `TransactionType` | Core discriminator (e.g., `BUY`, `SELL`, `DIVIDEND`) |
| `date` | `string` | Execution date in `YYYY-MM-DD` format |
| `currency` | `string` | ISO 4217 code |
| `amount` | `number` | Total gross monetary value |
| `fee` | `number \| null` | Brokerage commission or withheld taxes |
| `notes` | `string \| null` | Free-text memo |

### Asset Operations (BUY / SELL / TRANSFER)

Mounted only when the `TransactionType` involves an asset:

| Field | Type | Description |
|-------|------|-------------|
| `asset_id` | `UUID` | Foreign key to the selected Asset |
| `quantity` | `number` | Number of shares/units |

## ✅ Client-Side Validation

Before casting to a `PendingOp`, the form performs basic sanity checks (fail-fast validation):

- Dates cannot be in the future (unless explicitly overridden via Settings).
- `Quantity` must be `> 0`.
- The `Amount` must be provided and correctly signed based on the transaction type rule (e.g. `BUY` requires negative cash outflow, but the form handles the absolute value display).

For deep validation (e.g., "Does the user have enough shares to SELL?"), the frontend defers to the backend's [Balance Validation](../../../backend/transactions/balance_validation.md) engine.

## 💰 WAC State

When modifying a `BUY` or `SELL`, the form instantiates a `WacPreview` component. This component reads the `DraftRow` and queries the backend for the current Weighted Average Cost (WAC), providing instant feedback on the projected new cost basis. It handles both `Auto` and `Manual` WAC override modes.
