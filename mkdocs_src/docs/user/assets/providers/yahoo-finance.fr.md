# 📈 Fournisseur Yahoo Finance

Yahoo Finance est le fournisseur par défaut pour les actions, les ETF et les fonds communs de placement. Il offre la couverture la plus large et prend en charge la recherche d'actifs.

## 📊 Fonctionnalités

- ✅ **Prix actuel** : Cotations en temps réel ou différées
- ✅ **Historique** : Données de prix historiques complètes
- ✅ **Recherche** : Recherche d'actifs par nom ou par ticker

## 🔧 Configuration

- **Identifiant** : Symbole ticker de Yahoo Finance (ex: `AAPL`, `VWCE.DE`, `BTC-USD`)
- **Type d'identifiant** : `TICKER`
- **Paramètres** : Aucun requis

## 💡 Exemples

| Actif | Ticker |
|-------|--------|
| Apple Inc. | `AAPL` |
| Vanguard FTSE All-World (Xetra) | `VWCE.DE` |
| Bitcoin | `BTC-USD` |
| iShares Core S&P 500 (Milan) | `CSSPX.MI` |

## 📝 Notes

- Pour les ETF cotés en Europe, ajoutez le suffixe de la place boursière (ex: `.DE` pour Xetra, `.MI` pour Milan, `.AS` pour Amsterdam)
- Les données de Yahoo Finance peuvent présenter un retard de 15 minutes pour certaines bourses
