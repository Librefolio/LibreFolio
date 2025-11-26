# Asset Pricing Providers

This guide provides an overview of the asset pricing provider system in LibreFolio.

> For a guide on how to create a new asset provider, see [New Asset Provider](../contributing/new-asset-provider.md).

## 🏛️ Architecture

LibreFolio uses a modular, plugin-based architecture for fetching asset price data from various sources. This allows the system to be easily extended with new providers.

### Key Components:
-   **AssetSourceProvider (Abstract Base Class)**: Defines the interface that all asset providers must implement. This includes methods for fetching current and historical prices.
-   **AssetProviderRegistry**: A registry that auto-discovers and manages all available asset providers.
-   **AssetSourceManager**: The service layer that orchestrates calls to the providers, handles data caching, and persists prices to the database.

## 🔌 Available Providers

The following providers are currently implemented:

-   `yfinance`: Fetches data for stocks and ETFs from Yahoo Finance.
-   `cssscraper`: A generic web scraper that can extract prices from any website using CSS selectors.
-   `scheduled_investment`: A "synthetic" provider that calculates the value of scheduled-yield assets (like P2P loans) based on their interest schedule.
-   `mockprov`: A mock provider used for testing purposes.

## 🔄 Data Flow

1.  **Request**: An API call is made to refresh the price of an asset.
2.  **Provider Selection**: The `AssetSourceManager` looks up the assigned provider for the asset in the `asset_provider_assignments` table.
3.  **Data Fetch**: The manager calls the appropriate method on the provider (e.g., `get_current_value()`).
4.  **Provider Execution**: The provider fetches the data from its external source (e.g., Yahoo Finance API or a website).
5.  **Data Return**: The provider returns the data in a standardized Pydantic model (`CurrentValueModel` or `HistoricalDataModel`).
6.  **Persistence**: The `AssetSourceManager` saves the fetched prices to the `price_history` table in the database.

## 🕵️ How to get information about the asset pricing system

To get information about the asset pricing system an Agent can:

1.  Read this file and the other guides in this section.
2.  Inspect the `backend/app/services/asset_source.py` file for the core logic and abstract base class.
3.  Inspect the `backend/app/services/asset_source_providers/` directory for provider implementations.
4.  Read the [Provider Development Guide](../contributing/new-asset-provider.md) for instructions on how to create a new provider.
5.  Run the asset provider tests: `./test_runner.py external asset-providers`
