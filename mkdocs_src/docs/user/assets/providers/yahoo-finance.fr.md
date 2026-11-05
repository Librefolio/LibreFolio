# <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" alt=""> Yahoo Finance

Yahoo Finance couvre les actions, les ETF, les fonds, les indices et les cryptomonnaies des bourses du monde entier, et vous pouvez y effectuer une recherche par nom ou par ticker.

## 🔍 Ce qu'il propose

- **Prix actuel** : le dernier prix que Yahoo indique pour le ticker — sur certaines bourses, il est différé.
- **Historique** : l'ouverture, le plus haut, le plus bas, la clôture et le volume, au jour le jour, aussi loin que Yahoo remonte. Les clôtures sont enregistrées telles que la bourse les fournit, sans l'ajustement pour les dividendes versés depuis (une division est déjà intégrée aux clôtures de Yahoo et est enregistrée comme un événement).
- **Dividendes et divisions** : enregistrés comme des événements de l'actif. Pour une ligne londonienne cotée en pence, le dividende est enregistré en livres (1,95 pence correspond à 0,0195 GBP).
- **Recherche** : par nom ou par ticker.
- **Détails** : type, devise, description, secteur, ticker et, lorsque Yahoo le fournit, l'ISIN.
- **Détails du fonds** : pour un ETF ou un fonds, la répartition sectorielle (une action n'a qu'un seul secteur), la description propre au fonds lorsque Yahoo ne dispose pas d'un résumé d'activité pour celui-ci, et, à la fin de la description, les frais courants (`TER: 0.03%`) et l'émetteur (`Issuer: Vanguard`). Yahoo ne donne pas à chaque fonds ses frais courants — Vanguard FTSE All-World (`VWCE.DE`) n'en a pas — et cette partie est alors omise. La répartition par pays provient uniquement de [justETF](justetf.md).

## ✏️ Configuration

**Recherche en ligne** s'en occupe pour vous. Manuellement, dans **Attribution du fournisseur**, choisissez **Yahoo Finance**, réglez **Type d'identifiant** sur **TICKER** et saisissez le ticker comme **Identifiant**. Il n'y a rien d'autre à remplir.

| Actif | Ticker |
|-------|--------|
| Apple Inc. | `AAPL` |
| Vanguard FTSE All-World (Xetra) | `VWCE.DE` |
| iShares Core S&P 500 (Milan) | `CSSPX.MI` |
| Bitcoin en dollars américains | `BTC-USD` |

En dehors des États-Unis, ajoutez le suffixe de la bourse au ticker : `.DE` pour Xetra, `.MI` pour Milan, `.AS` pour Amsterdam.

De nombreuses lignes londoniennes (suffixe `.L`) sont cotées en pence, que Yahoo indique avec la devise `GBp`. LibreFolio enregistre la devise comme `GBP` et les prix tels que Yahoo les fournit, en pence ; un tel actif nécessite donc **Unités par prix unitaire** à 100, faute de quoi sa valeur ressort 100 fois trop élevée. Lorsque Yahoo indique `GBp`, sélectionner la ligne dans **Recherche en ligne** règle la valeur sur 100, avec une note sous le champ, et **Demander au fournisseur** la propose si le champ indique autre chose ([Vérifier les données du fournisseur](../create-edit.md#provider-data-comparison)).

## ⚠️ Limites

- **L'ISIN** fonctionne aussi comme **Type d'identifiant**, mais uniquement lorsque Yahoo peut l'associer à un ticker : privilégiez le ticker.
- **Les données enregistrées avant ce comportement restent telles quelles.** Si vous avez un actif Yahoo dont les clôtures ont été enregistrées auparavant, elles portent toujours l'ajustement de dividende du jour de leur lecture, et les dividendes d'une ligne en pence sont toujours en pence. Rien ne les réécrit automatiquement : relancez la **synchronisation complète** de l'actif (la boîte de dialogue prévient avant d'écraser) et l'historique est relu. Cela ne change pas le comportement des divisions décrit ci-dessous.
- **Limitation connue : les divisions.** Après une division d'actions, Yahoo réécrit les clôtures passées (et les dividendes) selon le nouveau nombre d'actions. Pour la division 4:1 d'Apple du 31 août 2020, la clôture du 28 août 2020 est indiquée comme 124,81 au lieu des 499 qu'elle valait réellement. La valeur d'une position les jours précédant une division peut donc ressortir divisée par le ratio de division (10 actions × 124,81 = 1 248 au lieu de 4 990), et le rendement fait un bond le jour de la division. Une correction est prévue après la 1.3.
- Yahoo peut limiter le débit des requêtes : LibreFolio suspend alors ses requêtes pendant un moment et continue d'afficher les derniers prix enregistrés. Certains tickers présentent des jours manquants.

## 🔗 Voir aussi

- 🔌 **[Fournisseurs d'actifs](index.md)** — Comparer les fournisseurs
- 🛠️ **Pour les développeurs : [Fournisseur Yahoo Finance](../../../developer/backend/assets/provider_yahoo_finance.md)** — Requêtes, mise en cache et événements
