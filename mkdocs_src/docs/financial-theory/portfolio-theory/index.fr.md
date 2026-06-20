# 📈 Théorie du Portefeuille

La théorie du portefeuille fournit le cadre mathématique pour construire des portefeuilles d'investissement qui maximisent le rendement attendu pour un niveau de risque donné — ou, inversement, minimisent le risque pour un rendement attendu donné.

---

## 📖 Aperçu

### 🏛️ Théorie Moderne du Portefeuille (MPT)

Introduite par Harry Markowitz en 1952, la Théorie Moderne du Portefeuille a révolutionné l'investissement en démontrant que **le risque d'un portefeuille n'est pas simplement la somme des risques individuels des actifs**. Grâce à la diversification, un investisseur peut réduire la volatilité de son portefeuille sans sacrifier le rendement attendu.

L'idée clé : ce qui importe n'est pas seulement le risque et le rendement individuels de chaque actif, mais la manière dont les actifs évoluent **les uns par rapport aux autres** (corrélation).

### 📐 La Frontière Efficiente

La frontière efficiente est l'ensemble des portefeuilles qui offrent le **rendement attendu le plus élevé pour chaque niveau de risque** :

$$
\max_{w} \quad E[R_p] = \sum_i w_i \cdot E[R_i]
$$

sous contrainte de :

$$
\sigma_p^2 = \sum_i \sum_j w_i w_j \sigma_i \sigma_j \rho_{ij} \leq \sigma_{target}^2
$$

où $w_i$ sont les poids du portefeuille, $E[R_i]$ les rendements attendus, $\sigma_i$ les volatilités et $\rho_{ij}$ les corrélations.

Tout portefeuille situé **sous** la frontière est suboptimal — vous pourriez obtenir un rendement plus élevé pour le même risque, ou un risque plus faible pour le même rendement.

---

## 📖 Ce que vous trouverez ici

### 🔀 [Diversification](diversification.md)

Le fondement mathématique du principe "ne pas mettre tous ses œufs dans le même panier". Comment la combinaison d'actifs ayant une corrélation imparfaite réduit la variance du portefeuille — et les limites de la diversification face au risque systématique.

### ⚖️ [Allocation d'Actifs](asset-allocation.md)

Allocation stratégique vs tactique, trajectoires de glissement (glide paths), stratégies à date cible et l'art du rééquilibrage. Comment décider *quelle quantité* de chaque classe d'actifs détenir.

### 📊 [Mesures de Risque](../technical-analysis/risk-metrics/index.md)

Mesures quantitatives du risque de portefeuille. De l'écart-type au ratio de Sharpe, chaque mesure capture un aspect différent du risque :

- **[Ratio de Sharpe](../technical-analysis/risk-metrics/sharpe-ratio.md)** — Rendement ajusté au risque (volatilité totale)
- **[Ratio de Sortino](../technical-analysis/risk-metrics/sortino-ratio.md)** — Rendement ajusté au risque (risque de baisse uniquement)
- **[Maximum Drawdown](../technical-analysis/risk-metrics/max-drawdown.md)** — La pire baisse du sommet au creux
- **[Volatilité](../technical-analysis/risk-metrics/volatility.md)** — Écart-type des rendements

---

## 🔑 Hypothèses Clés et Limitations

!!! warning "MPT assumptions"

    La Théorie Moderne du Portefeuille suppose :

    1. **Des investisseurs rationnels** qui cherchent à maximiser leur utilité
    2. **Une distribution normale** des rendements (en pratique, les rendements présentent des queues épaisses)
    3. Des rendements attendus, des volatilités et des corrélations **connus** (en pratique, ceux-ci sont sujets à des erreurs d'estimation)
    4. **Des marchés sans friction** — pas de taxes, pas de frais de transaction (LibreFolio vous aide à les suivre !)

Malgré ces limitations, la MPT reste le fondement de la gestion de portefeuille institutionnelle et fournit le vocabulaire utilisé par l'ensemble de l'industrie de l'investissement.

---

## 🔗 Sections Associées

- 🏦 **[Instruments](../instruments/index.md)** — Les composants de base des portefeuilles
- 📐 **[Fondamentaux](../fundamentals/index.md)** — Rendements, conventions de comptage des jours, fiscalité
- 📊 **[Analyse Technique](../technical-analysis/index.md)** — Outils d'analyse d'actifs individuels
