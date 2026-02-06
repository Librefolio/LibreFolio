# Introduction

## What is LibreFolio?

**LibreFolio** is a self-hosted financial portfolio tracker designed for privacy and flexibility. It allows you to aggregate data from multiple brokers and asset sources into a
single, unified dashboard.

### Key Features

- **Privacy First**: Your data stays on your server. No third-party cloud storage.
- **Multi-Broker Support**: Import data from Interactive Brokers, Degiro, eToro, Trading212, and many others via CSV.
- **Asset Tracking**: Track Stocks, ETFs, Cryptocurrencies, and P2P Loans.
- **Automated Pricing**: Fetch prices from Yahoo Finance, JustETF, or custom web scrapers.
- **FX Handling**: Automatic currency conversion using official rates (ECB, FED, etc.).
- **Modern Stack**: Built with Python (FastAPI), SvelteKit, and SQLite.

## Technology Stack

LibreFolio is built on a modern, efficient stack:

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy (Async), Pydantic.
- **Frontend**: SvelteKit, TypeScript, TailwindCSS.
- **Database**: SQLite (with strict mode and WAL journal).
- **Containerization**: Docker & Docker Compose.

## Project Goals

1. **Data Sovereignty**: Users should own their financial data.
2. **Extensibility**: Easy to add new brokers and data sources via a plugin system.
3. **Simplicity**: Easy to deploy via Docker for non-technical users.
