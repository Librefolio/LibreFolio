# <img src="https://www.justetf.com/android-chrome-144x144.png?v2" alt=""> justETF

justETF fournit les cours des ETF européens à partir de leur ISIN, en euros, en dollars américains, en francs suisses ou en livres sterling.
Il fournit également la description de chaque fonds ainsi que sa distribution géographique et sectorielle.

## 🔍 Ce qu'il propose

- **Cours actuel** : en EUR, le prix live de la bourse gettex ; lorsqu'il n'y en a pas — et
  toujours en USD, CHF et GBP — le dernier cours quotidien.
- **Historique** : les cours de clôture quotidiens dans la devise de votre choix.
- **Dividendes** : les distributions affichées dans le graphique du fonds deviennent des événements de dividende.
- **Recherche** : par nom, ticker, WKN ou ISIN, parmi les ETF listés sur justETF.
- **Détails** : une description avec le TER et la politique de distribution, la distribution
  géographique et sectorielle, l'ISIN et le ticker.

## ✏️ Configuration

**Recherche en ligne** effectue la configuration pour vous. Manuellement, dans **Attribution du fournisseur** :

1. Choisissez **JustETF** comme **Fournisseur**.
2. Saisissez l'**ISIN** du fonds, par exemple `IE00B4L5Y983` (iShares Core MSCI World).
3. Dans `currency`, choisissez `EUR` (par défaut), `USD`, `CHF` ou `GBP` : tous les prix de l'actif
   sont stockés dans cette devise.

### 💱 Choisir la devise lors de la recherche {: #search-currency }

Chaque ETF apparaît quatre fois dans les résultats, une fois par devise : 🇪🇺 EUR, 🇺🇸 USD, 🇨🇭 CHF et
🇬🇧 GBP — sauf si vous avez choisi une [devise préférée](#preferred-currency). 👑 marque la devise
propre du fonds, celle dans laquelle sa NAV est calculée — pas nécessairement celle dans laquelle
vous négociez. Une ligne en bas des résultats l'indique dès qu'un résultat affiche 👑.

justETF convertit les prix en USD, CHF et GBP avec ses propres taux de change. Votre devise de
référence en est-elle une autre ? Choisissez l'une des quatre : LibreFolio convertit avec ses propres
[taux de change](../../fx/index.md).

### ⭐ Votre devise préférée {: #preferred-currency }

Vous choisissez toujours la même devise ? Sélectionnez-la une fois comme **Devise préférée**, sous
**JustETF** dans **Paramètres › Plugins**, ou avec **Configurer** à côté du fournisseur dans la boîte
de dialogue de l'actif. Vos recherches n'affichent alors chaque ETF qu'une seule fois, dans cette
devise, avec 👑 uniquement sur les fonds calculés dans celle-ci. L'option **Toutes les devises**, qui est la valeur par
défaut, affiche les quatre devises.

Il s'agit d'un paramètre personnel : il ne modifie que vos propres recherches, jamais un prix ni un
actif que vous possédez déjà. Voir [Paramètres des plugins](../../settings/plugins.md#search-preferences).

## ⚠️ Limites

- ISIN uniquement : pour un ticker, utilisez [Yahoo Finance](yahoo-finance.md).
- Seul le prix en EUR est live.
- LibreFolio lit le site web de justETF : un changement de leur côté peut interrompre les prix
  jusqu'à ce que LibreFolio soit mis à jour.

## 🔗 Voir aussi

- 🔌 **[Fournisseurs d'actif](index.md)** — Comparez les fournisseurs
- 🧩 **[Paramètres des plugins](../../settings/plugins.md)** — Votre devise préférée dans la recherche
- 🛠️ **Pour les développeurs : [Fournisseur JustETF](../../../developer/backend/assets/provider_justetf.md)** — Cotations en direct, graphiques et mise en cache
