# 🔀 FX Configuration & Routing

LibreFolio supports a sophisticated multi-provider routing system for Foreign Exchange (FX) rates. This allows administrators to define exactly which provider should be used for each currency pair, with automatic fallback capabilities and **multi-step conversion chains**.

## 🛤️ The Routing Logic

When the system needs to fetch FX rates (e.g., via the `/api/v1/fx/currencies/sync` endpoint), it consults the `fx_conversion_routes` table.

### 🔢 Priority System

Each currency pair can have multiple **routes** assigned, ranked by **priority** (1 = highest/primary).

1. **Primary Route**: The system first attempts to use the route with `priority=1`.
2. **Fallback**: If the primary route fails (API error, timeout, provider down), the system automatically tries the route with `priority=2`, and so on.
3. **Failure**: If all configured routes fail, the sync operation reports an error for that specific pair.

### 🔗 Direct vs. Chain Routes

Each route is defined as a **chain of steps** (`chain_steps` JSON array):

- **Direct (1-step)**: A single provider converts the pair directly.
  Example: `EUR → USD` via ECB → `[{"from": "EUR", "to": "USD", "provider": "ECB"}]`

- **Multi-step (chain)**: Multiple steps are chained to compute a derived rate.
  Example: `RON → USD` via ECB+ECB → `[{"from": "RON", "to": "EUR", "provider": "ECB"}, {"from": "EUR", "to": "USD", "provider": "ECB"}]`

A chain's steps do not need to use *distinct* providers: `RON → USD` above uses `ECB` twice, once per leg, and that is a valid 2-step chain — "multi-step" only means "more than one step", not "more than one provider".

The system multiplies the intermediate rates to compute the final derived rate, which is stored in `fx_rates` with `source = "CHAIN:ECB+ECB"`.

### 📋 Example Configuration

| Base    | Quote   | Priority | Chain Steps                               | Description                  |
|:--------|:--------|:---------|:------------------------------------------|:-----------------------------|
| **EUR** | **USD** | 1        | `EUR →[ECB]→ USD`                         | Direct via ECB (primary)     |
| **EUR** | **USD** | 2        | `EUR →[FED]→ USD`                         | Direct via FED (fallback)    |
| **RON** | **USD** | 1        | `RON →[ECB]→ EUR →[ECB]→ USD`            | 2-step chain via ECB         |
| **GBP** | **USD** | 1        | `GBP →[BOE]→ USD`                         | Direct via BOE               |

In this example:

- For **EUR/USD**, the system prefers ECB. If ECB is down, it falls back to FED.
- For **RON/USD**, no provider offers this pair directly, so it uses a 2-step chain through EUR.
- For **GBP/USD**, it uses BOE directly.

## 🗃️ Database Schema

The configuration is stored in the `FxConversionRoute` model:

```python
class FxConversionRoute(SQLModel, table=True):
    __tablename__ = "fx_conversion_routes"

    id: int                     # Primary key
    base: str                   # e.g., "EUR" (alphabetically first: base < quote)
    quote: str                  # e.g., "USD"
    priority: int               # 1 = primary, 2+ = fallback
    chain_steps: str            # JSON array of conversion steps
    fetch_interval: int | None  # Optional refresh frequency (minutes), default 1440
    created_at: datetime
    updated_at: datetime
```

**`chain_steps` JSON format:**

```json
// Direct (1-step):
[{"from": "EUR", "to": "USD", "provider": "ECB"}]

// Multi-step chain (2-step):
[
  {"from": "RON", "to": "EUR", "provider": "ECB"},
  {"from": "EUR", "to": "USD", "provider": "ECB"}
]

// Manual-only pair:
[{"from": "NOK", "to": "SEK", "provider": "MANUAL"}]
```

**Validation rules:**

- **Continuity**: `step[i].to == step[i+1].from` for consecutive steps
- **No repeated edges**: The same currency pair cannot appear twice in a chain (any direction)
- **Alphabetical ordering**: `base < quote` constraint

## 🌐 API Endpoints

Configuration is managed via the `/api/v1/fx/providers/routes` endpoints.

### 📋 List Routes

`GET /api/v1/fx/providers/routes`

Returns all configured routes ordered by base, quote, and priority. Each route includes the full `chain_steps` array plus two response-only fields, derived from the stored steps and not stored themselves:

| Field           | Type         | Meaning                                                                                     |
|:----------------|:-------------|:----------------------------------------------------------------------------------------------|
| `is_chain`      | `bool`       | `true` if the route has more than one step (`len(chain_steps) > 1`)                          |
| `providers_used`| `list[str]`  | Sorted unique list of provider codes appearing in `chain_steps` (including `MANUAL`)          |

`providers_used` is a **sorted unique list representing membership**, not an ordered traversal and not proof that a fetch succeeded: it lists which provider codes are *configured* on the route, so a route with two `ECB` steps still reports `["ECB"]`, and a MANUAL-only route reports `["MANUAL"]` with `is_chain: false`.

**Example** — for the `EUR/USD` primary route and the `RON/USD` chain route from the table above:

```json
{
  "items": [
    {
      "base": "EUR",
      "quote": "USD",
      "priority": 1,
      "chain_steps": [
        {"from": "EUR", "to": "USD", "provider": "ECB"}
      ],
      "is_chain": false,
      "providers_used": ["ECB"]
    },
    {
      "base": "RON",
      "quote": "USD",
      "priority": 1,
      "chain_steps": [
        {"from": "RON", "to": "EUR", "provider": "ECB"},
        {"from": "EUR", "to": "USD", "provider": "ECB"}
      ],
      "is_chain": true,
      "providers_used": ["ECB"]
    }
  ]
}
```

Note that `RON/USD` is `is_chain: true` (2 steps) with a single-member `providers_used` — the flag and the set answer different questions: "how many steps" versus "which providers are configured".

### ➕ Create/Update Routes (Bulk)

`POST /api/v1/fx/providers/routes`

Creates or updates multiple conversion routes atomically.

**Request:**

```json
[
  {
    "base": "EUR",
    "quote": "USD",
    "priority": 1,
    "chain_steps": [
      {"from": "EUR", "to": "USD", "provider": "ECB"}
    ]
  },
  {
    "base": "EUR",
    "quote": "USD",
    "priority": 2,
    "chain_steps": [
      {"from": "EUR", "to": "USD", "provider": "FED"}
    ]
  },
  {
    "base": "RON",
    "quote": "USD",
    "priority": 1,
    "chain_steps": [
      {"from": "RON", "to": "EUR", "provider": "ECB"},
      {"from": "EUR", "to": "USD", "provider": "ECB"}
    ]
  }
]
```

The request body's inputs remain `base`, `quote`, `priority`, and `chain_steps` — clients simply omit the derived `is_chain`/`providers_used` metadata. If a client supplies them anyway, the values are ignored: they are never writable or authoritative, and are recomputed server-side from `chain_steps` for the response.

**Result:**

Each submitted item gets one result carrying the same `is_chain`/`providers_used` pair described for `GET`, computed from that item's own `chain_steps`, plus `success`, `action` (`"created"` or `"updated"`), and an optional `message`.

!!! note "Validation failures and the transaction"

    If any submitted route references a provider code not registered in the provider registry, that item's result reports `success: false`, `action: "error"`, and a `message` naming the unknown code(s) — with `providers_used` still derived from the *submitted* `chain_steps`, so an unknown code appears in `providers_used` too (it is membership of what was posted, not a check that the code is valid). When at least one item fails validation, the whole batch is rolled back and the endpoint responds `400` with the per-item results (including the successful ones, none of which were actually persisted) in the error detail body.

### 🗑️ Delete Routes

`DELETE /api/v1/fx/providers/routes`

Removes routing rules. Can delete a specific priority or all rules for a pair.

**Request:**

```json
[
  {
    "base": "EUR",
    "quote": "USD",
    "priority": 2
  }
]
```

If `priority` is omitted, all routes for the pair are deleted. When all real-provider routes are deleted, a MANUAL sentinel route is automatically reinstated to preserve the pair in the system.

## 🔄 Auto-Sync Behavior

When calling `POST /api/v1/fx/currencies/sync`:

1. The system queries `fx_conversion_routes` to find all configured pairs and their routes.
2. For **1-step routes**, it groups target currencies by provider and fetches in batch.
3. For **multi-step (chain) routes**, it fetches each leg's rates from the respective providers, then computes the derived rate by multiplying the intermediate rates.
4. If a route fails, the system tries the next priority route for that pair.
5. Results are saved to the `fx_rates` table. Chain-derived rates are stored with `source = "CHAIN:provider1+provider2"`.

This ensures resilience to individual provider outages and supports currency pairs that no single provider covers directly.
