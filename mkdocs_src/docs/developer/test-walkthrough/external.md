# External Services Tests (`external`)

These tests verify integrations with external APIs and data sources. They do **not** require the backend server to be running, but they do require an internet connection.

## Purpose

To ensure that external providers (like Yahoo Finance, ECB, etc.) are reachable and returning data in the expected format.

## Key Tests

- **FX Providers**: Verifies fetching rates from ECB, FED, etc.
- **Asset Providers**: Verifies fetching prices from Yahoo Finance, JustETF.

## Running

```bash
./dev.sh test external
```
