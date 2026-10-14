# <img src="https://www.ecb.europa.eu/favicon-32.png" alt=""> Banque centrale européenne (BCE)

La **Banque centrale européenne (BCE)** est le principal fournisseur de taux de référence pour les portefeuilles européens. Elle publie chaque jour des taux de référence de l'euro par rapport à environ 30 devises.

## 📊 Fonctionnalités

- ✅ **Prix actuel** : Taux de référence mis à jour une fois par jour
- ✅ **Historique** : Taux historiques disponibles depuis 1999
- ❌ **Recherche** : Pas de recherche d'actifs (taux FX uniquement)

## 🔧 Spécifications

- **Devise de base** : EUR 🇪🇺
- **Fréquence de mise à jour** : Du lundi au vendredi (hors jours fériés de la BCE), vers 16:00 CET
- **Clé API** : Non requise (point d'accès public)

## 💰 Devises prises en charge

La BCE publie un taux chaque jour ouvré pour environ 30 devises, notamment :

- **Majeures** : USD 🇺🇸, GBP 🇬🇧, JPY 🇯🇵, CHF 🇨🇭, CAD 🇨🇦, AUD 🇦🇺, NZD 🇳🇿
- **Européennes/Régionales** : SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰, ISK 🇮🇸, PLN 🇵🇱, CZK 🇨🇿, HUF 🇭🇺, RON 🇷🇴, TRY 🇹🇷
- **Globales / Émergentes** : CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, KRW 🇰🇷, INR 🇮🇳, BRL 🇧🇷, MXN 🇲🇽, ZAR 🇿🇦

Les devises que la BCE ne publie plus, comme le lev bulgare (BGN, remplacé par l'euro en 2026), la kuna croate (HRK) ou le rouble russe (RUB), conservent leurs taux passés : une synchronisation télécharge toujours leur historique, et aucun nouveau taux n'arrive.

## 📝 Notes importantes

- **Format des cotations** : Les taux sont exprimés en quantité de devise étrangère pour 1 EUR (ex. : 1 EUR = 1,08 USD). LibreFolio normalise automatiquement ce taux en fonction de la devise de base de votre portefeuille.
- **Pas de données le week-end** : La BCE ne publie pas de taux les samedis, dimanches ou jours fériés officiels de la BCE (ex. : Vendredi saint, Lundi de Pâques, Noël). LibreFolio conservera le taux du dernier jour ouvré disponible pour les valorisations du week-end.
