# 📊 Types d'actifs

LibreFolio prend en charge un large éventail de classes d'actifs afin de couvrir un portefeuille diversifié. Chaque type d'actif possède des règles de gestion spécifiques concernant la tarification, les dividendes et la gestion fiscale.

## 📋 Actifs pris en charge

| | Type | Code | Description | |
|:---:|:---|:---|---|:---:|
| ![](../../../static/icons/asset-types/stock.png){: width="32" } | **Stock** | `STOCK` | Parts de capital d'une entreprise. Les prix sont généralement récupérés depuis les marchés boursiers. | [📖](stocks.md) |
| ![](../../../static/icons/asset-types/etf.png){: width="32" } | **ETF** | `ETF` | Exchange Traded Funds. Paniers de titres qui s'échangent comme des actions. | [📖](etfs.md) |
| ![](../../../static/icons/asset-types/bond.png){: width="32" } | **Bond** | `BOND` | Titres à revenu fixe représentant un prêt à un emprunteur (gouvernemental ou d'entreprise). | [📖](bonds.md) |
| ![](../../../static/icons/asset-types/crypto.png){: width="32" } | **Crypto** | `CRYPTO` | Monnaies numériques et jetons (Bitcoin, Ethereum, etc.). | [📖](crypto.md) |
| ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" } | **P2P / Crowdfunding** | `CROWDFUND` | Prêts entre particuliers ou financement participatif immobilier. Souvent valorisés via des paiements d'intérêts programmés. | [📖](real-estate.md) |
| ![](../../../static/icons/asset-types/fund.png){: width="32" } | **Fonds commun de placement** | `FUND` | Fonds d'investissement gérés professionnellement. | [📖](mutual-fund.md) |
| ![](../../../static/icons/asset-types/hold.png){: width="32" } | **Matières premières** | `HOLD` | Actifs physiques comme l'or, l'argent ou les diamants détenus pour leur valeur à long terme. | [📖](commodities.md) |
| ![](../../../static/icons/asset-types/other.png){: width="32" } | **Autre** | `OTHER` | Toute autre classe d'actifs (ex: Art, Private Equity, Objets de collection). | [📖](other.md) |
| ![](../../../static/icons/asset-types/other.png){: width="32" } | **Index &amp; Benchmark** | `—` | Index de marché (S&amp;P 500, MSCI World) utilisés comme benchmarks — non négociables directement. | [📖](index-benchmark.md) |

---

## 🔗 Liens connexes

- 💸 **[Types de transactions](../transaction-types/index.md)** — Opérations qui affectent votre portefeuille
- 📅 **[Événements d'actifs](../asset-events/index.md)** — Opérations sur titres affectant le prix des actifs
- 💰 **[Fiscalité](../../fundamentals/taxation.md)** — Implications fiscales par classe d'actifs
