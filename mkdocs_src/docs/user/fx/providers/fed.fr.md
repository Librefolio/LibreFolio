# <img src="https://fred.stlouisfed.org/favicon.ico" alt=""> Federal Reserve (FED)

Le fournisseur **Federal Reserve (FRED)** récupère les données de taux de change depuis la base de données Federal Reserve Economic Data (FRED). C'est la source principale ou fallback idéale pour les portefeuilles centrés sur le dollar américain.

## 📊 Capacités

- ✅ **Prix actuel** : Taux de référence mis à jour quotidiennement
- ✅ **Historique** : Taux historiques approfondis (dépend de la série de données)
- ❌ **Recherche** : Pas de recherche d'actifs (taux FX uniquement)

## 🔧 Spécifications

- **Devise de base** : USD 🇺🇸
- **Fréquence de mise à jour** : Quotidienne durant les jours ouvrables américains
- **Clé API** : Non requise (récupérée via téléchargement CSV public)

## 💰 Devises prises en charge

FRED fournit les taux pour environ 20 devises majeures, notamment :

- **Devises du G10** : EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CAD 🇨🇦, CHF 🇨🇭, AUD 🇦🇺, NZD 🇳🇿, SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰
- **Émergentes et régionales** : CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, KRW 🇰🇷, INR 🇮🇳, BRL 🇧🇷, MXN 🇲🇽, ZAR 🇿🇦, TWD 🇹🇼, THB 🇹🇭

## 📝 Notes importantes

- **Format des cotations** : FRED cote certaines devises comme « USD par unité de devise étrangère » (ex: EUR, GBP) et d'autres comme « devise étrangère par USD » (ex: JPY, CAD). LibreFolio inverse et normalise automatiquement ces taux pour garantir la cohérence dans votre base de données.
- **Jours fériés** : Aucun taux n'est publié les jours fériés fédéraux américains (tels que Thanksgiving, Independence Day, etc.) ou les week-ends.
