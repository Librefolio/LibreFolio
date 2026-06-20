# <img src="https://www.ecb.europa.eu/favicon-32.png" alt=""> Banque centrale européenne (BCE)

La **Banque centrale européenne (BCE)** est le principal fournisseur de taux de référence pour les portefeuilles européens. Elle publie quotidiennement les taux de change de l'euro par rapport à environ 45 devises majeures et émergentes.

## 📊 Fonctionnalités

- ✅ **Prix actuel** : Taux de référence mis à jour une fois par jour
- ✅ **Historique** : Taux historiques disponibles depuis 1999
- ❌ **Recherche** : Pas de recherche d'actifs (taux FX uniquement)

## 🔧 Spécifications

- **Devise de base** : EUR 🇪🇺
- **Fréquence de mise à jour** : Du lundi au vendredi (hors jours fériés de la BCE), vers 16:00 CET
- **Clé API** : Non requise (point d'accès public)

## 💰 Devises prises en charge

La BCE prend en charge un large éventail de devises, notamment :

- **Majeures** : USD 🇺🇸, GBP 🇬🇧, JPY 🇯🇵, CHF 🇨🇭, CAD 🇨🇦, AUD 🇦🇺, NZD 🇳🇿
- **Européennes/Régionales** : SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰, PLN 🇵🇱, CZK 🇨🇿, HUF 🇭🇺, RON 🇷🇴, BGN 🇧🇬, TRY 🇹🇷
- **Globales / Émergentes** : CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, KRW 🇰🇷, INR 🇮🇳, BRL 🇧🇷, MXN 🇲🇽, ZAR 🇿🇦

## 📝 Notes importantes

- **Format des cotations** : Les taux sont exprimés en quantité de devise étrangère pour 1 EUR (ex. : 1 EUR = 1,08 USD). LibreFolio normalise automatiquement ce taux en fonction de la devise de base de votre portefeuille.
- **Pas de données le week-end** : La BCE ne publie pas de taux les samedis, dimanches ou jours fériés officiels de la BCE (ex. : Vendredi saint, Lundi de Pâques, Noël). LibreFolio conservera le taux du dernier jour ouvré disponible pour les valorisations du week-end.
