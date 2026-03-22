# ❓ Frequently Asked Questions (FAQ)

Welcome to the LibreFolio FAQ. Here you'll find answers to common questions.

## 💬 General Questions

### 🤔 What is LibreFolio?

LibreFolio is a self-hosted, open-source portfolio tracker designed for privacy-conscious investors. It allows you to track your investments, analyze performance, and maintain full
control of your financial data.

### 💰 Is LibreFolio free?

Yes! LibreFolio is completely free and open-source under the [AGPL-3.0 license](https://www.gnu.org/licenses/agpl-3.0.html).

### 📊 What assets can I track?

LibreFolio supports:

- **Stocks & ETFs** — Automatically fetched prices via data providers (e.g., yfinance)
- **Cryptocurrencies** — Coming soon
- **Bonds** — Manual entry supported
- **P2P Lending** — Scheduled-yield assets
- **Cash & Deposits** — Track your liquidity

!!! tip "Missing something? 💡"
    If there's an asset class or feature you'd like to see that we haven't thought of yet, we'd love to hear from you! Open a [feature request on GitHub](https://github.com/Alfystar/LibreFolio/issues/new?labels=enhancement) and let us know.

## 🚀 Getting Started

### 📦 How do I install LibreFolio?

See our [Installation Guide](developer/dev-installation.md) for detailed instructions.

### 👤 How do I create an account?

1. Navigate to the login page
2. Click "Register"
3. Fill in your details
4. Your account is ready to use!

### 🔑 I forgot my password, what do I do?

Currently, password reset is done via CLI. Contact your instance administrator or run:

```bash
./dev.py user reset <username> <new_password>
```

## 🔧 Troubleshooting

### 📉 My asset prices aren't updating

Check that:

1. Auto-sync is enabled in Global Settings
2. Your assets have valid ISINs or symbols recognized by the configured **data provider** (e.g., [yfinance](https://pypi.org/project/yfinance/) for stocks and ETFs)
3. The provider's service is available (check server logs for errors)

### 💱 My FX rates aren't updating

Check that:

1. The currency pair has at least one [data provider configured](user/fx/detail/provider.md)
2. The provider's API is reachable (ECB, FED, BOE, SNB)
3. You've run a [sync](user/fx/sync.md) for the desired date range
4. Check the [provider supply chain](user/fx/detail/provider.md) for fallback options

### 🔐 I can't login

- Verify your username and password
- Check if your account is activated
- Clear browser cookies and try again

## 🆘 Need More Help?

- [Full Documentation](index.md)
- [Report a Bug](https://github.com/Alfystar/LibreFolio/issues)
- [GitHub Discussions](https://github.com/Alfystar/LibreFolio/discussions)
