# :heart: Support LibreFolio

LibreFolio is an **open-source** project, licensed under AGPL-3.0. The source code is freely available, and anyone with the skills and infrastructure can install and run it independently — that's the beauty of open source.

If you use LibreFolio and find it valuable, we'd love your support — whether through **code**, **ideas**, or a **small donation**. Every contribution fuels the project's growth.

---

## :coffee: Buy Me a Coffee

If LibreFolio helps you manage your investments better, consider supporting development with a coffee:

<a href="https://www.buymeacoffee.com/librefolio" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-green.png" alt="Buy Me a Coffee" style="height: 60px !important;width: 217px !important;" ></a>

Every donation — no matter how small — helps cover development tools, testing infrastructure, and motivates continued improvement.

---

## :rocket: High-Impact Contributions

For us, **a great idea or a code contribution is just as valuable as a donation**. Here are the areas where your help can make the biggest difference:

### :electric_plug: New Plugins

LibreFolio uses a [Registry & Plugin System](../developer/architecture/patterns/registry_pattern.md) with auto-discovery. Adding a new plugin is one of the most impactful contributions you can make:

| Type | Guide | What it does |
|------|-------|-------------|
| 📥 **BRIM** | [BRIM Plugin Guide](../developer/architecture/patterns/brim_plugin_guide.md) | Import transactions from a new broker (CSV/Excel) |
| 📈 **Asset** | [Asset Plugin Guide](../developer/architecture/patterns/asset_plugin_guide.md) | Fetch prices from a new data source |
| 💱 **FX** | [FX Plugin Guide](../developer/architecture/patterns/fx_plugin_guide.md) | Add a new exchange rate provider |
| 📊 **Chart Signals** | *Guide coming soon* | New technical indicators and chart overlays (EMA, MACD, RSI, Bollinger…) |

* **If you are not a developer**: You can request a new plugin using our [Plugin Request Form](https://github.com/Librefolio/LibreFolio/issues/new?template=plugin_request.yml). In addition to the request details, you must provide anonymized examples of the broker report file (e.g. CSV or Excel) so we can understand the format.
* **If you are a developer**: You can implement the plugin directly on your own. Please refer to the [Registry & Plugin System Guide](../developer/architecture/patterns/registry_pattern.md) and the specific guides linked in the table above to learn how to build them.

### :art: UI/UX Ideas

Aesthetic improvements, layout suggestions, accessibility enhancements — if you see something that could look or work better, tell us by opening a ticket using our [UX Idea & Suggestions Form](https://github.com/Librefolio/LibreFolio/issues/new?template=idea.yml) on GitHub.

### :bug: Bug Reports

Finding and clearly reporting issues is incredibly helpful. Open a new report using our [Bug Report Form](https://github.com/Librefolio/LibreFolio/issues/new?template=bug_report.yml) on GitHub.

The form will guide you in providing browser information, deployment method, and error logs.

---

## :rocket: Feature Requests

Propose specific features with clear use cases by filling out our [Feature Request Form](https://github.com/Librefolio/LibreFolio/issues/new?template=feature_request.yml) on GitHub.

Every request will be evaluated and taken on as soon as there's capacity to develop it. Well-described requests with concrete examples get prioritised faster.

---

## :computer: Contribute Code

If you're a developer and want to contribute directly:

1. **Fork** the [repository](https://github.com/Librefolio/LibreFolio)
2. **Create a branch** for your feature or fix
3. **Develop and test** in your own repo
4. **Submit a Pull Request** with a clear description and keyword prefix in the title:

| Keyword | When to use |
|---------|------------|
| **`[FIX]`** | Bug fixes |
| **`[FEAT]`** | New features or enhancements |
| **`[PLUGIN]`** | New plugin (BRIM, Asset, FX, Signal) |
| **`[DOCS]`** | Documentation improvements |

!!! warning "Merge policy"

    A PR will be merged **only if all existing tests continue to pass**. If your changes require test updates, include them in the PR — that's perfectly fine and expected.

Check the [Developer Manual](../developer/index.md) for architecture details, coding conventions, and testing guidelines.

---

## :star: Star the Project

A simple but powerful way to help: **star the repository** on GitHub! It increases visibility and helps other users discover LibreFolio.

[:octicons-star-fill-24: Star on GitHub](https://github.com/Librefolio/LibreFolio){ .md-button .md-button--primary }

---

## :globe_with_meridians: What's Next — LibreFolio Cloud

For those who want to use LibreFolio but don't have the time, skills, or infrastructure to self-host, we're planning a **hosted platform** — **LibreFolio Cloud**. It will offer all the same powerful features without any technical setup, plus upcoming **AI-powered analytics** to help you make smarter investment decisions.

To sustain the infrastructure, maintenance, and ongoing development, the cloud platform will be offered as a **subscription service** — pricing to be determined later.

---

!!! tip "Thank you!"

    Every form of support — code, ideas, bug reports, or donations — is deeply appreciated. Together we can build the best self-hosted portfolio tracker! :rocket:
