# Plugin System Overview

This section documents LibreFolio's plugin-based provider system for fetching external data.

## Architecture

- **Provider Base Classes**: `AssetSourceProvider` and `FXRateProvider` define the interfaces.
- **Auto-Discovery**: Providers are automatically registered at startup using the `@register_provider` decorator.
- **Configuration**: Each asset can be assigned a provider and provider-specific parameters via the API.

## Implemented Asset Providers

- [yfinance](./yfinance.md)
- [CSS Scraper](./cssscraper.md)
- [Scheduled Investment](./scheduled-investment.md)

## Contributing

To learn how to create a new provider, see the [Contributing Guide](../../contributing/new-asset-provider.md).
