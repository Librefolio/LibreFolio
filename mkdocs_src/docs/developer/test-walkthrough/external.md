# 🌐 External Services Tests (`external`)

These tests verify integrations with external APIs and data sources. They do **not** require the backend server to be running, but they do require an internet connection (except BRIM, which uses local sample files).

## 🎯 Purpose

To ensure that external providers (like Yahoo Finance, ECB, etc.) are reachable and returning data in the expected format.

## 🔑 Sub-commands

| Sub-command | What It Tests |
|-------------|---------------|
| `fx-providers` | FX rate providers: ECB, FED, BOE, SNB, MANUAL |
| `asset-providers` | Asset pricing providers: yfinance, JustETF, CSS Scraper, etc. |
| `brim-providers` | Broker Report Import Manager parsers (local sample files, no network) |
| `all` | All of the above |

## 🚀 Running

```bash
# All external tests
./dev.py test external all

# Single sub-command
./dev.py test external fx-providers
./dev.py test external asset-providers
./dev.py test external brim-providers

# Verbose output
./dev.py test -v external asset-providers

# With coverage tracking
./dev.py test --coverage external all
```

## 🔍 Provider Filtering

When an external service is down (e.g., Yahoo Finance outage), you can skip its tests without modifying code.

### Exclude specific providers

```bash
# Skip yfinance tests (Yahoo Finance is down)
./dev.py test external asset-providers --exclude-providers yfinance

# Skip multiple providers
./dev.py test external all --exclude-providers yfinance broker_coinbase
```

### Include only specific providers

```bash
# Only test JustETF
./dev.py test external asset-providers --providers justetf

# Only test ECB and FED
./dev.py test external fx-providers --providers ECB FED
```

### Works with `all` and `all-backend` too

```bash
# Run the full test suite but exclude yfinance
./dev.py test all --exclude-providers yfinance

# Run all backend tests, only test ECB for FX
./dev.py test all-backend --providers ECB justetf
```

### How it works

The `--providers` / `--exclude-providers` flags translate to pytest `-k` expressions:

| Flag | Pytest equivalent |
|------|-------------------|
| `--providers yfinance justetf` | `-k "yfinance or justetf"` |
| `--exclude-providers yfinance` | `-k "not yfinance"` |

!!! tip "Dynamic help"

    Run `./dev.py test external -h` to see all available provider codes, discovered automatically from the source tree.

### Lightweight discovery

Provider codes are discovered by **regex-parsing** the Python source files — the modules are never imported. This avoids heavy side-effects (TTL cache creation, logger initialisation, network client setup) and keeps `./dev.py test -h` instant.

## 🔄 yfinance Retry Logic

The Yahoo Finance provider includes automatic retry with exponential backoff for transient network errors (API instability, rate limiting, timeouts).

| Parameter | Value |
|-----------|-------|
| Max retries | 3 |
| Base delay | 1.5 s (→ 1.5 s, 3 s, 6 s) |
| Transient keywords | `curl`, `connection`, `timeout`, `reset`, `503`, `429`, `rate limit`, etc. |

**Wrapped operations:** `get_current_value`, `get_history_value`, `search`, `fetch_asset_metadata`.

Non-transient errors (e.g., `INVALID_IDENTIFIER_TYPE`) are raised immediately without retry.

!!! note "Thread safety"

    yfinance calls run in dedicated threads (via `_run_provider_in_thread()` in the core), so `time.sleep()` blocks only that thread without affecting the asyncio event loop.

