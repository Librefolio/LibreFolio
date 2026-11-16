# <img src="https://fred.stlouisfed.org/favicon.ico" alt=""> Federal Reserve (FED)

Le fournisseur **Federal Reserve (FRED)** récupère les données de taux de change depuis la base de données Federal Reserve Economic Data (FRED). C'est la source principale ou fallback idéale pour les portefeuilles centrés sur le dollar américain.

## 📊 Capacités

- ✅ **Prix actuel** : Taux de référence mis à jour quotidiennement
- ✅ **Historique** : Taux historiques approfondis (dépend de la série de données)
- ❌ **Recherche** : Pas de recherche d'actifs (taux FX uniquement)

## 🔧 Spécifications

- **Devise de base** : USD 🇺🇸
- **Fréquence de mise à jour** : un taux par jour ouvrable américain, publié une fois par semaine (voir ci-dessous)
- **Clé API** : Non requise (récupérée via téléchargement CSV public)

## 💰 Devises prises en charge

FRED fournit les taux pour 23 devises :

- **Devises du G10** : EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CAD 🇨🇦, CHF 🇨🇭, AUD 🇦🇺, NZD 🇳🇿, SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰
- **Émergentes et régionales** : CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, KRW 🇰🇷, INR 🇮🇳, BRL 🇧🇷, MXN 🇲🇽, ZAR 🇿🇦, TWD 🇹🇼, THB 🇹🇭, MYR 🇲🇾, LKR 🇱🇰, VES 🇻🇪

## 📝 Notes importantes

- **Format des cotations** : FRED cote certaines devises comme « USD par unité de devise étrangère » (ex. : EUR, GBP) et d'autres comme « devise étrangère par USD » (ex. : JPY, CAD). LibreFolio lit chaque série dans son propre sens et la normalise pour garantir la cohérence dans votre base de données.
- **Publication hebdomadaire** : les taux FED sont quotidiens, une valeur par jour ouvrable américain, mais la Réserve fédérale les publie une fois par semaine, le lundi, avec les jours de la semaine précédente. Le dernier taux FED peut donc dater d'environ 10 jours, et une chaîne de conversion avec une étape FED n'a pas de taux pour les jours les plus récents avant la publication suivante. Les routes qui utilisent FED le signalent par une note ℹ️.
- **VES (bolívar vénézuélien)** : disponible à partir du 4 octobre 2021, jour de la dernière redénomination. Les valeurs FRED antérieures sont exprimées dans d'anciennes unités de bolívar et ne sont pas utilisées.
- **Jours fériés** : Aucun taux n'est publié les jours fériés fédéraux américains (tels que Thanksgiving, Independence Day, etc.) ou les week-ends.
