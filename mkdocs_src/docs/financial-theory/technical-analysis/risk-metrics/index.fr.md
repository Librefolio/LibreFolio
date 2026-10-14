# 📊 Métriques de risque

Les métriques de risque fournissent des **mesures quantitatives** du risque de portefeuille. Chaque métrique capture un aspect différent de l'incertitude, et aucune métrique seule ne raconte toute l'histoire. L'utilisation de plusieurs métriques ensemble donne une vue complète du risque de portefeuille.

---

## 🧭 Les quatre questions {: #the-four-questions }

Chaque page de cette section existe pour répondre à l'une des quatre questions. Une métrique mérite sa place en répondant à l'une d'elles ; deux pages transversales expliquent comment les réponses sont calculées et dans quelle mesure elles peuvent être fiables. Les deux tableaux ci-dessous comparent côte à côte les quatre métriques les plus connues parmi celles-ci et suggèrent quand recourir à chacune.

### 📉 Combien cela peut-il faire mal ? {: #how-much-can-it-hurt }

| Métrique | À quoi elle répond |
|--------|-----------------|
| **[Perte maximale](max-drawdown.md)** | La plus grande baisse d'un sommet à un creux avant un nouveau sommet — la pire perte qu'un investisseur aurait réellement vécue. |
| **[Repli actuel](current-drawdown.md)** | Dans quelle mesure un portefeuille se situe actuellement en dessous de son propre sommet historique, par opposition à la pire chute qu'il ait jamais subie. |
| **[Repli à risque](drawdown-at-risk.md)** | Le repli à risque applique l'idée de quantile aux replis plutôt qu'aux rendements : c'est la profondeur de repli qui ne devrait pas être dépassée à un niveau de confiance choisi. |
| **[Repli à risque conditionnel](conditional-drawdown-at-risk.md)** | Le repli à risque conditionnel fait la moyenne des replis qui ont effectivement dépassé le seuil de repli à risque, répondant à la question de savoir jusqu'où va la chute une fois ce point dépassé. |
| **[Indice d'Ulcer](ulcer-index.md)** | L'indice d'Ulcer combine la profondeur de la chute d'un portefeuille avec sa durée, de sorte qu'une baisse modérée qui persiste peut être moins bien notée qu'une baisse brutale qui se rétablit rapidement. |
| **[Valeur à risque](value-at-risk.md)** | Une question délibérément étroite : sur un horizon donné et à un niveau de confiance choisi, quelle est la perte qui ne devrait pas être dépassée ? |
| **[VaR conditionnelle](conditional-value-at-risk.md)** | Prend le relais exactement là où la valeur à risque s'arrête : la perte moyenne dans les cas où le seuil de valeur à risque a effectivement été dépassé. |
| **[Pire réalisation](worst-realization.md)** | Le rendement le moins favorable observé sur une période unique dans l'historique disponible — un fait observé plutôt qu'une estimation. |

*Les cinq premières lisent le **chemin** que le portefeuille a réellement emprunté ; les trois dernières lisent la **distribution** de ses rendements. Mélangez l'ordre de ces rendements et les trois dernières restent inchangées, tandis que les cinq premières peuvent changer complètement.*

### 🧩 Suis-je diversifié ? {: #am-i-diversified }

| Métrique | À quoi elle répond |
|--------|-----------------|
| **[Corrélation](correlation.md)** | Comment les positions évoluent les unes par rapport aux autres, c'est pourquoi la diversification dépend de la façon dont les positions se comportent ensemble plutôt que de leur nombre. |
| **[Contribution au risque](risk-contribution.md)** | Comment le risque total du portefeuille est attribué aux différentes positions — ce qu'apporte chaque position n'est généralement pas la même chose que la part du portefeuille qu'elle représente. |
| **[Concentration](concentration.md)** | Dans quelle mesure le poids d'un portefeuille est concentré sur quelques positions, donnant une lecture qu'un simple décompte des positions ne peut pas fournir. |

### ⚖️ Suis-je rémunéré pour le risque ? {: #am-i-paid-for-the-risk }

| Métrique | À quoi elle répond |
|--------|-----------------|
| **[Volatilité](volatility.md)** | La dispersion des rendements — combien la valeur fluctue, et la brique de base de presque toutes les autres métriques de risque. |
| **[Ratio de Sharpe](sharpe-ratio.md)** | Combien de rendement excédentaire a été gagné par unité de volatilité totale. |
| **[Ratio de Sortino](sortino-ratio.md)** | La même comparaison, avec uniquement la volatilité à la baisse au dénominateur. |
| **[Bêta et rendement actif](beta-active-return.md)** | À quel point un portefeuille a tendance à suivre son indice de référence, et quelle partie du résultat l'indice de référence n'explique pas. |
| **[Sélection de l'indice de référence](benchmark-selection.md)** | Chaque chiffre relatif à un indice de référence hérite de l'indice par rapport auquel il a été mesuré, donc le choix de la comparaison fait lui-même partie du verdict. |

### 🎲 Et si… ? {: #what-if }

| Métrique | À quoi elle répond |
|--------|-----------------|
| **[Rejeu historique](historical-replay.md)** | Ce que les mouvements d'un épisode passé réel feraient au portefeuille tel qu'il est composé aujourd'hui. |
| **[Choc hypothétique](hypothetical-shock.md)** | Remplace l'épisode historique par un épisode choisi, ce qui permet de tester un scénario que l'historique disponible n'a jamais contenu. |
| **[Modes de simulation](simulation-modes.md)** | Chaque mode repose sur ses propres hypothèses, et ces hypothèses déterminent autant ce que ses résultats ne peuvent pas dire que ce qu'ils peuvent dire. |

### 🔧 Méthode {: #method }

| Page | À quoi elle répond |
|------|-----------------|
| **[Annualisation observée](observed-annualization.md)** | Comment un chiffre par période devient un chiffre annuel, avec le nombre de périodes dans une année mesuré à partir des données plutôt que supposé à l'avance. |
| **[Qualité des données](data-quality.md)** | Un chiffre de risque n'est fiable que dans la mesure où les observations qui le sous-tendent le sont, donc la quantité et la fraîcheur des données sous-jacentes font partie de la lecture du résultat. |

---

## 📋 Vue d'ensemble comparative {: #comparative-overview }

| Métrique | Ce qu'elle mesure | Formule | Plage | Détails |
|--------|-----------------|---------|-------|---------|
| **[Ratio de Sharpe](sharpe-ratio.md)** | Rendement ajusté au risque (volatilité totale) | $\frac{R_p - R_f}{\sigma_p}$ | $(-\infty, +\infty)$ | [📖](sharpe-ratio.md) |
| **[Ratio de Sortino](sortino-ratio.md)** | Rendement ajusté au risque (baisse uniquement) | $\frac{R_p - R_f}{\sigma_d}$ | $(-\infty, +\infty)$ | [📖](sortino-ratio.md) |
| **[Perte maximale](max-drawdown.md)** | Pire baisse entre un sommet et un creux | $\frac{Trough - Peak}{Peak}$ | $[-100\%, 0\%]$ | [📖](max-drawdown.md) |
| **[Volatilité](volatility.md)** | Dispersion des rendements | $\sigma = \sqrt{\text{Var}(R)}$ | $[0, +\infty)$ | [📖](volatility.md) |

---

## 🔑 Quand utiliser chaque métrique {: #when-to-use-each-metric }

| Scénario | Meilleure métrique | Pourquoi |
|----------|-------------|-----|
| Comparer deux fonds | **Ratio de Sharpe** | Normalise le rendement par le risque total |
| Distributions de rendement asymétriques | **Ratio de Sortino** | Ne pénalise que la volatilité à la baisse |
| Planification de scénario défavorable | **Perte maximale** | Montre le point de douleur maximal |
| Évaluation générale du risque | **Volatilité** | Fondement de toutes les autres métriques |
| Optimisation de portefeuille | **Les quatre** | Chacune capture une dimension différente |

---

## ⚠️ Pièges courants {: #common-pitfalls }

!!! warning "Limites"

    - **Les métriques historiques ≠ risque futur** : La volatilité passée peut ne pas prédire la volatilité future
    - **Hypothèse de distribution normale** : Sharpe et Sortino supposent que les rendements sont à peu près normaux ; les rendements financiers ont des queues épaisses
    - **Sensibilité à la période d'observation** : Les métriques changent considérablement selon la fenêtre temporelle
    - **Dépendance à l'indice de référence** : Sharpe et Sortino dépendent du taux sans risque, qui change au fil du temps

---

## 🔗 Voir aussi {: #related }

- 🔀 **[Diversification](../../portfolio-theory/diversification.md)** — Comment la réduction du risque fonctionne mathématiquement
- ⚖️ **[Allocation d'actifs](../../portfolio-theory/asset-allocation.md)** — Utiliser les métriques de risque pour guider l'allocation
- 📈 **[Rendements et taux de croissance](../../fundamentals/returns.md)** — Le côté « rendement » du couple risque-rendement
