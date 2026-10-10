# <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" alt=""> Yahoo Finance

Yahoo Finance couvre les actions, les ETF, les fonds, les indices et les cryptomonnaies des bourses du monde entier, et vous pouvez y effectuer des recherches par nom ou par ticker.

## 🔍 Ce qu'il propose

- **Prix actuel** : le dernier prix rapporté par Yahoo pour le ticker — sur certaines bourses, il est différé.
- **Historique** : ouverture, plus haut, plus bas, clôture et volume quotidiens, aussi loin que remonte Yahoo.
- **Dividendes et divisions** : enregistrés en tant qu'événements d'actif.
- **Recherche** : par nom ou par ticker.
- **Détails** : type, devise, description, secteur, ticker et, lorsque Yahoo le fournit, l'ISIN.

## ✏️ Configuration

**Recherche en ligne** le configure pour vous. Manuellement, dans **Affectation du fournisseur**, choisissez **Yahoo Finance**, définissez **Type d'identifiant** sur **TICKER** et saisissez le ticker comme **Identifiant**. Il n'y a rien d'autre à remplir.

| Actif | Ticker |
|-------|--------|
| Apple Inc. | `AAPL` |
| Vanguard FTSE All-World (Xetra) | `VWCE.DE` |
| iShares Core S&P 500 (Milan) | `CSSPX.MI` |
| Bitcoin en dollars américains | `BTC-USD` |

En dehors des États-Unis, ajoutez le suffixe de la bourse au ticker : `.DE` pour Xetra, `.MI` pour Milan, `.AS` pour Amsterdam.

## ⚠️ Limites

- **ISIN** fonctionne aussi comme **Type d'identifiant**, mais uniquement lorsque Yahoo peut l'associer à un ticker : privilégiez le ticker.
- Yahoo peut limiter le débit des requêtes fréquentes, et il peut manquer des jours pour certains tickers.

## 🔗 Voir aussi

- 🔌 **[Fournisseurs d'actifs](index.md)** — Comparez les fournisseurs
- 🛠️ **Pour les développeurs : [Fournisseur Yahoo Finance](../../../developer/backend/assets/provider_yahoo_finance.md)** — Requêtes, mise en cache et événements
