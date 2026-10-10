# <img src="https://www.justetf.com/android-chrome-144x144.png?v2" alt=""> justETF

justETF valorise les ETF européens par leur ISIN, en euros, dollars américains, francs suisses ou livres sterling.
Il fournit en outre la description de chaque fonds ainsi que sa répartition par pays et par secteur.

## 🔍 Ce qu'il propose

- **Cours actuel** : en EUR, le prix live de la bourse gettex ; lorsqu'il n'y en a pas — et
  toujours en USD, CHF et GBP — le dernier cours quotidien.
- **Historique** : les cours de clôture quotidiens dans la devise de votre choix.
- **Dividendes** : les distributions affichées dans le graphique du fonds deviennent des événements de dividende.
- **Recherche** : par nom, ticker, WKN ou ISIN, parmi les ETF référencés sur justETF.
- **Détails** : une description avec le TER et la politique de distribution, les répartitions par pays et par
  secteur, l'ISIN et le ticker.

## ✏️ Le configurer

**Search Online** le configure pour vous. Manuellement, dans **Attribution du fournisseur** :

1. Choisissez **JustETF** comme **Fournisseur**.
2. Saisissez l'**ISIN** du fonds, par exemple `IE00B4L5Y983` (iShares Core MSCI World).
3. Dans `currency`, choisissez `EUR` (par défaut), `USD`, `CHF` ou `GBP` : chaque prix de l'actif est
   stocké dans cette devise.

### 💱 Choisir la devise dans la recherche

Chaque ETF apparaît quatre fois dans les résultats, une fois par devise : 🇪🇺 EUR, 🇺🇸 USD, 🇨🇭 CHF et
🇬🇧 GBP. 👑 marque la devise du fonds lui-même, celle dans laquelle sa NAV est calculée — pas nécessairement celle
dans laquelle vous négociez.

justETF convertit les prix en USD, CHF et GBP avec ses propres taux de change. Votre devise de reporting est-elle différente ? Choisissez l'une des quatre : LibreFolio convertit avec ses propres
[taux de change](../../fx/index.md).

## ⚠️ Limites

- ISIN uniquement : pour un ticker, utilisez [Yahoo Finance](yahoo-finance.md).
- Seul le prix en EUR est en direct.
- LibreFolio lit le site web de justETF : une modification de leur côté peut interrompre les prix jusqu'à ce que LibreFolio
  soit mis à jour.

## 🔗 Voir aussi

- 🔌 **[Fournisseurs d'actifs](index.md)** — Comparez les fournisseurs
- 🛠️ **Pour les développeurs : [Fournisseur JustETF](../../../developer/backend/assets/provider_justetf.md)** — Cours en direct, graphiques et mise en cache
