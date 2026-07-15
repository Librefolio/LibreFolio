# 📊 Types d'actifs

LibreFolio prend en charge une large gamme de classes d'actifs pour couvrir un portefeuille diversifié. Chaque type d'actif a des comportements spécifiques concernant le prix, les dividendes et la gestion fiscale.

## 📋 Actifs pris en charge

| | Type | Code | Description | |
|:---:|:---|:---|---|:---:|
| ![](../../../static/icons/asset-types/stock.png){: width="32" } | **Action** | `STOCK` | Parts de capital d'une entreprise. Les prix sont généralement récupérés depuis les bourses publiques. | [📖](stocks.md) |
| ![](../../../static/icons/asset-types/etf.png){: width="32" } | **ETF** | `ETF` | Fonds négociés en bourse. Paniers de titres qui se négocient comme des actions. | [📖](etfs.md) |
| ![](../../../static/icons/asset-types/bond.png){: width="32" } | **Obligation** | `BOND` | Titres à revenu fixe représentant un prêt à un emprunteur (gouvernement ou entreprise). | [📖](bonds.md) |
| ![](../../../static/icons/asset-types/crypto.png){: width="32" } | **Crypto** | `CRYPTO` | Monnaies numériques et jetons (Bitcoin, Ethereum, etc.). | [📖](crypto.md) |
| ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" } | **P2P / Crowdfunding** | `CROWDFUND` | Prêts pair-à-pair ou crowdfunding immobilier. Souvent valorisés via des paiements d'intérêts programmés. | [📖](real-estate.md) |
| ![](../../../static/icons/asset-types/fund.png){: width="32" } | **Fonds commun de placement** | `FUND` | Fonds d'investissement gérés professionnellement. | [📖](mutual-fund.md) |
| ![](../../../static/icons/asset-types/hold.png){: width="32" } | **Matières premières** | `HOLD` | Actifs physiques comme l'Or, l'Argent ou les Diamants détenus pour leur valeur à long terme. | [📖](commodities.md) |
| ![](../../../static/icons/asset-types/other.png){: width="32" } | **Autre** | `OTHER` | Toute autre classe d'actifs (par exemple, Art, Private Equity, Objets de collection). | [📖](other.md) |
| ![](../../../static/icons/asset-types/other.png){: width="32" } | **Indice &amp; Benchmark** | `—` | Indices de marché (S&amp;P 500, MSCI World) utilisés comme références — non négociables directement. | [📖](index-benchmark.md) |

---

## 🔗 Liens connexes

- 💸 **[Types de transactions](../transaction-types/index.md)** — Opérations qui affectent votre portefeuille
- 📅 **[Événements d'actifs](../asset-events/index.md)** — Actions d'entreprise affectant les prix des actifs
- 💰 **[Fiscalité](../../fundamentals/taxation.md)** — Implications fiscales par classe d'actifs
