# FX Configuration & Routing

LibreFolio supports a sophisticated multi-provider routing system for Foreign Exchange (FX) rates. This allows administrators to define exactly which provider should be used for
each currency pair, with automatic fallback capabilities.

## The Routing Logic

When the system needs to fetch FX rates (e.g., via the `/api/v1/fx/currencies/sync` endpoint without an explicit provider), it consults the `fx_currency_pair_sources` table.

### Priority System

Each currency pair can have multiple providers assigned, ranked by **priority** (1 = highest/primary).

1. **Primary Source**: The system first attempts to fetch rates from the provider with `priority=1`.
2. **Fallback**: If the primary provider fails (API error, timeout) or returns no data, the system automatically tries the provider with `priority=2`, and so on.
3. **Failure**: If all configured providers fail, the sync operation reports an error for that specific pair.

### Example Configuration

| Base    | Quote   | Provider | Priority | Role                            |
|:--------|:--------|:---------|:---------|:--------------------------------|
| **EUR** | **USD** | `ECB`    | 1        | Primary (European Central Bank) |
| **EUR** | **USD** | `FED`    | 2        | Fallback (Federal Reserve)      |
| **USD** | **JPY** | `FED`    | 1        | Primary                         |
| **GBP** | **USD** | `BOE`    | 1        | Primary (Bank of England)       |

In this example:

- For **EUR/USD**, the system prefers ECB. If ECB is down, it falls back to FED.
- For **USD/JPY**, it only uses FED.
- For **GBP/USD**, it uses BOE.

## Database Schema

The configuration is stored in the `FxCurrencyPairSource` model:

```python
class FxCurrencyPairSource(SQLModel, table=True):
    base: str          # e.g., "EUR"
    quote: str         # e.g., "USD"
    provider_code: str # e.g., "ECB"
    priority: int      # 1, 2, 3...
    fetch_interval: int | None  # Optional refresh frequency (minutes)
```

## API Endpoints

Configuration is managed via the `/api/v1/fx/providers/pair-sources` endpoints.

### List Configuration

`GET /api/v1/fx/providers/pair-sources`
Returns all configured pairs ordered by priority.

### Configure Pairs (Bulk)

`POST /api/v1/fx/providers/pair-sources`

Allows creating or updating multiple routing rules atomically.

**Request:**

```json
[
  {
    "base": "EUR",
    "quote": "USD",
    "provider_code": "ECB",
    "priority": 1
  },
  {
    "base": "EUR",
    "quote": "USD",
    "provider_code": "FED",
    "priority": 2
  }
]
```

### Delete Configuration

`DELETE /api/v1/fx/providers/pair-sources`

Removes routing rules. Can delete a specific priority or all rules for a pair.

**Request:**

```json
[
  {
    "base": "EUR",
    "quote": "USD",
    "priority": 2  // Only delete the fallback
  }
]
```

## Auto-Sync Behavior

When calling `GET /api/v1/fx/currencies/sync` **without** the `provider` parameter:

1. The system queries `fx_currency_pair_sources` to find all configured pairs.
2. It groups pairs by their **Primary Provider** (Priority 1).
3. It executes parallel fetch requests to these providers.
4. If a provider fails, it immediately looks up the next priority provider for the affected pairs and retries.
5. Results are merged and saved to the `fx_rates` table.

This ensures that the system is resilient to individual provider outages.
