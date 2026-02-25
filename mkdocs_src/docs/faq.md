# Frequently Asked Questions (FAQ)

Welcome to the LibreFolio FAQ. Here you'll find answers to common questions.

## General Questions

### What is LibreFolio?

LibreFolio is a self-hosted, open-source portfolio tracker designed for privacy-conscious investors. It allows you to track your investments, analyze performance, and maintain full
control of your financial data.

### Is LibreFolio free?

Yes! LibreFolio is completely free and open-source under the MIT license.

### What assets can I track?

LibreFolio supports:

- **Stocks & ETFs** - Automatically fetched prices from yfinance
- **Cryptocurrencies** - Coming soon
- **Bonds** - Manual entry supported
- **P2P Lending** - Scheduled-yield assets
- **Cash & Deposits** - Track your liquidity

## Getting Started

### How do I install LibreFolio?

See our [Installation Guide](getting-started/installation.md) for detailed instructions.

### How do I create an account?

1. Navigate to the login page
2. Click "Register"
3. Fill in your details
4. Your account is ready to use!

### I forgot my password, what do I do?

Currently, password reset is done via CLI. Contact your instance administrator or run:

```bash
./dev.py user reset <username> <new_password>
```

## Troubleshooting

### My prices aren't updating

Check that:

1. Auto-sync is enabled in Global Settings
2. Your assets have valid ISINs or symbols
3. The yfinance provider is working (check logs)

### I can't login

- Verify your username and password
- Check if your account is activated
- Clear browser cookies and try again

## Need More Help?

- [Full Documentation](index.md)
- [Report a Bug](https://github.com/Alfystar/LibreFolio/issues)
- [GitHub Discussions](https://github.com/Alfystar/LibreFolio/discussions)

