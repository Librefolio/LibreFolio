# 🔌 Fournisseurs

LibreFolio prend en charge plusieurs fournisseurs de prix pour récupérer automatiquement les prix actuels et les données historiques de vos actifs.

## 📊 Comparaison des fournisseurs

| Fournisseur | Prix actuel | Historique | Recherche | Identifiant | Notes |
|----------|:---:|:---:|:---:|---|---|
| **Yahoo Finance** | ✅ | ✅ | ✅ | Ticker (ex: `AAPL`, `VWCE.DE`) | Idéal pour les actions, ETF, fonds communs de placement |
| **justETF** | ✅ | ✅ | ❌ | ISIN (ex: `IE00BK5BQT80`) | ETF européens avec données détaillées |
| **CSS Scraper** | ✅ | ❌ | ❌ | URL | Extraire les données de prix de n'importe quelle page web |
| **Scheduled Investment** | ✅ | ✅ | ❌ | Auto-généré | Produits à revenu fixe avec échéanciers d'intérêts |

## 🎯 Choisir un fournisseur

- **Actions & ETF** : Utilisez **Yahoo Finance** — couverture la plus étendue et prise en charge de la recherche
- **ETF européens** : Utilisez **justETF** pour des données d'ETF européens plus détaillées
- **Obligations sur Borsa Italiana** : Utilisez **CSS Scraper** pour extraire les prix directement
- **Comptes d'épargne / Dépôts à terme** : Utilisez **Scheduled Investment** avec des échéanciers de taux d'intérêt

## 📚 Détails des fournisseurs

- [📈 Yahoo Finance](yahoo-finance.md)
- [📊 justETF](justetf.md)
- [🔍 CSS Scraper](css-scraper.md) — guide détaillé pour le web scraping
- [🧮 Scheduled Investment](scheduled-investment.md)
