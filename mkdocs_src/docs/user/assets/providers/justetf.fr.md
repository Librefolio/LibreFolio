# <img src="https://www.justetf.com/android-chrome-144x144.png?v2" alt=""> justETF

justETF fournit des données détaillées pour les ETF européens, incluant les prix actuels et les données historiques avec un support multi-devises.

## 📊 Capacités

- ✅ **Prix actuel** : Cotations gettex en temps réel (EUR uniquement)
- ✅ **Historique** : Données de prix historiques en EUR, USD, CHF ou GBP
- ✅ **Recherche** : Recherche plein texte parmi plus de 3000 ETF européens

## 💱 Sélection de la devise

justETF permet de récupérer les prix dans **4 devises** : EUR, USD, CHF, GBP.

Lorsque vous recherchez un ETF, les résultats s'affichent avec des drapeaux de devise :

| Drapeau | Signification |
|------|---------|
| 🇪🇺 | Prix en Euros |
| 🇺🇸 | Prix en Dollars US |
| 🇨🇭 | Prix en Francs Suisses |
| 🇬🇧 | Prix en Livres Sterling |
| 👑 | Devise NAV native du fonds (affichée à côté du drapeau) |

!!! note "Conversion de devise"

    JustETF effectue la conversion côté serveur en utilisant ses propres taux de change.
    Pour les devises ne figurant pas dans la liste supportée (JPY, SEK, etc.), utilisez le système de conversion de devise intégré de LibreFolio.

## ⚠️ Limitations

!!! warning "Prix actuel : EUR uniquement"

    Les prix en temps réel (valeur actuelle) sont uniquement disponibles en **EUR** car ils proviennent du WebSocket de la bourse **gettex**, qui est une bourse européenne dont les cotations sont en EUR.

    Pour les devises autres que l'EUR (USD, CHF, GBP) :

    - ✅ Les données historiques sont disponibles (converties par JustETF)
    - ❌ Le prix en temps réel n'est **pas** disponible — la synchronisation de l'actif affichera "valeur actuelle indisponible"

    **Recommandation** : Si vous avez besoin de prix en temps réel, utilisez l'EUR. Pour le suivi de portefeuille où les prix de clôture quotidiens suffisent, n'importe quelle devise convient.

## 🔧 Configuration

- **Identifiant** : Code ISIN (ex: `IE00BK5BQT80`)
- **Type d'identifiant** : `ISIN`
- **Paramètres** :
 - `currency` : Devise du prix — EUR (par défaut), USD, CHF ou GBP

## 💡 Exemples

| Actif | ISIN | Devise suggérée |
|-------|------|--------------------|
| Vanguard FTSE All-World | `IE00BK5BQT80` | EUR ou USD 👑 |
| iShares Core MSCI World | `IE00B4L5Y983` | EUR ou USD 👑 |
| Xtrackers MSCI Emerging Markets | `IE00BTJRMP35` | EUR ou USD 👑 |

## 📝 Notes

- Idéal pour les ETF domiciliés en Europe et listés sur justETF
- Utilise l'ISIN comme identifiant principal
- Le 👑 dans les résultats de recherche indique la dénomination NAV native du fonds — il s'agit de la devise que le gestionnaire du fonds utilise en interne, pas nécessairement la devise dans laquelle vous effectuez vos transactions
