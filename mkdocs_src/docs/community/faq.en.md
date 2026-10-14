# ❓ Frequently Asked Questions (FAQ)

Welcome to the LibreFolio FAQ. Here you'll find answers to common questions.

## 💬 General Questions

### 🤔 What is LibreFolio?

LibreFolio is an open-source portfolio tracker that gives you a complete, private view of all your investments. Powerful analytics tools turn your data into actionable insights — so you can make informed decisions with full confidence and full control.

### 💰 Is LibreFolio free?

Yes! LibreFolio is completely free and open-source under the [AGPL-3.0 license](https://www.gnu.org/licenses/agpl-3.0.html). You can install it on your own server and manage everything yourself at no cost.

!!! info "Coming soon: hosted platform ☁️"

    We're working on an online platform for those who don't have the time, interest, or technical skills to self-host. The hosted version will offer all features with zero setup, automatic updates, and dedicated support — available as a paid subscription.

### 🤖 Can I use LibreFolio with an AI assistant?

Yes. **[AI Export](../user/ai-export/index.md)** copies your data as ready-to-paste text, with a focused question if you want one, so you can ask the AI assistant of your choice about your portfolio, a broker, an asset or a currency pair. LibreFolio itself never contacts an AI service.

On the upcoming hosted platform, AI assistants will be fully integrated: ready to use with no configuration, along with premium support.

### 📊 What assets can I track?

LibreFolio supports:

- **Stocks, ETFs and funds** — prices fetched automatically from data providers (e.g., yfinance)
- **Bonds** — prices from a provider, or entered by hand
- **Crypto assets** — tracked as portfolio assets, not as currencies
- **Crowdfunding and P2P lending** — valued with a scheduled yield
- **Commodities, real estate**, and assets without a market price (art, collectibles, unlisted shares)
- **Cash** — the balance of each broker, in every currency

The full list is in [Asset Types](../financial-theory/instruments/asset-types/index.md).

!!! tip "Missing something? 💡"

    If there's an asset class or feature you'd like to see that we haven't thought of yet, we'd love to hear from you! Open a [feature request on GitHub](https://github.com/Librefolio/LibreFolio/issues/new?labels=enhancement) and let us know.

## 🚀 Getting Started

### 📦 How do I install LibreFolio?

Follow the [Docker Installation Guide](../user/installation.md), the recommended way, or the [Host Installation Guide](../admin/host_installation.md) to run it with Pipenv.

### 👤 How do I create an account?

1. Open the login page.
2. Click **Register here**, next to *Don't have an account?*
3. Fill in your details: your account is ready to use.

On a new instance, the first account created becomes the administrator. After that, signing up works only while the administrator keeps **Enable Registration** on in the [Global Settings](../admin/settings.md); otherwise, ask them for an account.

### 🔑 I forgot my password, what do I do?

Recovery by e-mail is not available yet: ask your instance administrator, who can set a new password from the command line ([Reset a Password](../admin/cli_tools.md#reset-a-password-or-lock-an-account)).

## 🔧 Troubleshooting

### 📉 My asset prices aren't updating

Check that:

1. **Scheduler Enabled** is on in the [Global Settings](../admin/settings.md#market-data-scheduler): it runs the automatic updates
2. Your assets have valid ISINs or symbols recognized by the configured **data provider** (e.g., [yfinance](https://pypi.org/project/yfinance/) for stocks and ETFs)
3. The provider's service is available (check server logs for errors)

### 💱 My FX rates aren't updating

Check that:

1. **Scheduler Enabled** is on in the [Global Settings](../admin/settings.md#market-data-scheduler)
2. The currency pair has at least one [data provider configured](../user/fx/detail/provider.md)
3. The provider's API is reachable (ECB, FED, BOE, SNB)
4. You've run a [sync](../user/fx/sync.md) for the desired date range
5. Check the [provider supply chain](../user/fx/detail/provider.md) for fallback options

### 🔐 I can't login

- Verify your username and password
- With a wrong password you always get the same *Invalid username or password* message, whether the account exists or not; with the right password, a disabled account is told so: ask your administrator to enable it again
- Clear browser cookies and try again

### 📱 Can I use LibreFolio as a mobile app?

Yes! LibreFolio supports **PWA (Progressive Web App)** installation. You can add it to your home screen on Android, iOS, or desktop for a full-screen, app-like experience — no app store needed.

See the [Install as App (PWA)](../user/pwa.md) guide for step-by-step instructions.

## 🆘 Need More Help?

- [Full Documentation](../index.md)
- [Report a Bug](https://github.com/Librefolio/LibreFolio/issues)
- [GitHub Discussions](https://github.com/Librefolio/LibreFolio/discussions)
