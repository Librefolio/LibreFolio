# 🔌 Fournisseurs

LibreFolio prend en charge plusieurs fournisseurs de prix pour récupérer automatiquement les cours actuels et les données historiques de vos actifs.

## 📊 Comparaison des fournisseurs

| Fournisseur | Prix actuel | Historique | Recherche | Identifiant | Notes |
|----------|:---:|:---:|:---:|---|---|
| **Yahoo Finance** | ✅ | ✅ | ✅ | Ticker (ex: `AAPL`, `VWCE.DE`) | Idéal pour les actions, ETF, fonds communs de placement |
| **justETF** | ✅ (EUR) | ✅ | ✅ | ISIN (ex: `IE00BK5BQT80`) | ETF européens, multi-devises (EUR/USD/CHF/GBP) |
| **CSS Scraper** | ✅ | ❌ | ❌ | URL | Scraper n'importe quelle page web pour les données de prix |
| **Investissement programmé** | ✅ | ✅ | ❌ | Auto-généré | Instruments à revenu fixe avec calendriers d'intérêts |

## 🎯 Choisir un fournisseur

- **Actions & ETF** : Utilisez **Yahoo Finance** — couverture la plus large, prend en charge la recherche
- **ETF Européens** : Utilisez **justETF** pour des données plus détaillées sur les ETF européens
- **Obligations sur Borsa Italiana** : Utilisez **CSS Scraper** pour extraire les prix directement
- **Comptes d'épargne / Dépôts à terme** : Utilisez **Investissement programmé** avec des calendriers de taux d'intérêt

## 📚 Détails des fournisseurs

- [📈 Yahoo Finance](yahoo-finance.md)
- [📊 justETF](justetf.md)
- [🔍 CSS Scraper](css-scraper.md) — guide détaillé pour le web scraping
- [🧮 Investissement programmé](scheduled-investment.md)
