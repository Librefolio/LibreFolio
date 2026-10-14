# 🎯 Concentration

La concentration mesure à quel point le poids d'un portefeuille se rassemble dans quelques positions, fournissant une lecture qu'un simple décompte des positions ne peut pas donner.

Elle est traitée ici sous la forme de **deux** chiffres plutôt que d'un seul, et c'est délibéré : le premier compte la manière dont l'argent est réparti, le second vérifie si cette répartition a réellement apporté quelque chose. Lu seul, le premier qualifiera de diversifié un portefeuille qui ne l'est pas.

---

## 🔢 Le chiffre fondé sur le décompte {: #the-count-based-figure }

Le point de départ est l'indice de Herfindahl — la somme des poids au carré :

$$
H = \sum_i w_i^{2}
$$

C'est l'élévation au carré qui en fait une mesure de concentration : un poids de 50 % contribue vingt-cinq fois plus qu'un poids de 10 %, si bien que les positions importantes dominent le total d'une manière qu'un simple décompte ne reflète jamais.

L'inverse transforme cela en quelque chose de lisible, le **nombre d'actifs effectifs** :

$$
N_{eff} = \frac{1}{H}
$$

Ce nombre répond à la question : *combien de positions de taille égale produiraient la concentration que j'ai réellement ?* Dix positions de 10 % chacune donnent $H = 10 \times 0.1^2 = 0.1$ et donc exactement 10. Une position de 50 % accompagnée de dix positions de 5 % donne bien moins que onze — le nombre tend vers le décompte des positions qui comptent réellement.

Le chiffre est intuitif précisément parce qu'il s'exprime sur l'échelle d'un décompte tout en se comportant de façon totalement différente. Cette lecture dépend bien du fait que les poids somment à un : dès qu'une trésorerie est détenue, ce n'est plus le cas, et le résultat peut dépasser purement et simplement le nombre de positions — [Où se situe la trésorerie](#where-cash-sits) traite de ce qui se passe alors.

---

## 🙈 Ce qu'un décompte ne peut pas voir {: #what-a-count-cannot-see }

Le nombre d'actifs effectifs ne lit **que les poids**. Il ne regarde jamais comment les positions se comportent, et c'est là son angle mort — un angle mort total.

Prenons trois portefeuilles, contenant chacun dix actifs équipondérés, ne différant que par la corrélation entre ces actifs. Outre le chiffre fondé sur le décompte, le tableau présente le **ratio de diversification**, qui compare la volatilité que les positions auraient eue séparément avec la volatilité du portefeuille qu'elles forment :

$$
DR = \frac{\sum_i w_i \sigma_i}{\sigma_p}
$$

| Corrélation entre les positions | Nombre d'actifs effectifs | Ratio de diversification |
|---|---|---|
| 0 | **10,00** | 3,15 |
| 0,5 | **10,00** | 1,35 |
| 0,95 | **10,00** | **1,02** |

Le chiffre fondé sur le décompte ne bouge pas d'un centième. Le ratio de diversification s'effondre.

!!! warning "Dix positions qui évoluent ensemble ne sont pas dix paris"

    Avec une corrélation de 0,95, le portefeuille se comporte presque exactement comme une position unique : le ratio de 1,02 indique que répartir l'argent sur dix actifs n'a procuré qu'une réduction de 2 % de la volatilité par rapport à la détention d'un seul d'entre eux. Le chiffre fondé sur le décompte affiche 10,00 dans les trois cas, et un lecteur qui ne regarderait que ce nombre conclurait que les trois portefeuilles sont aussi bien diversifiés les uns que les autres.

    C'est pourquoi les deux chiffres doivent figurer sur la même page et se lire d'un même coup d'œil. L'un mesure comment l'argent est **réparti**, l'autre si cette répartition a **fonctionné**.

Les valeurs mesurées ci-dessus sont cohérentes avec le cas idéalisé : pour $n$ positions équipondérées de volatilité égale et de corrélation par paire constante $\rho$, le ratio vaut $\sqrt{n / (1 + (n-1)\rho)}$, ce qui donne approximativement 3,16, 1,35 et 1,02 pour les trois lignes.

---

## 🏦 Le même mot à deux niveaux de granularité {: #two-granularities }

Un portefeuille peut afficher deux chiffres de concentration différents au même instant, et aucun des deux n'est faux. Ce qui change, c'est **ce qui compte comme une position**.

Supposons que le même instrument soit détenu chez deux courtiers, à hauteur de 6 % et 4 % du portefeuille.

- Compté **par position**, il contribue à hauteur de $0.06^2 + 0.04^2 = 0.0052$.
- Compté **par instrument**, les positions sont d'abord additionnées pour donner 10 %, ce qui contribue à hauteur de $0.10^2 = 0.0100$.

La différence vaut exactement $2 w_1 w_2$, toujours positive. La vue par instrument affiche donc **toujours** la concentration la plus élevée — et, comme le chiffre des actifs effectifs en est l'inverse, la vue par position affiche **toujours** le nombre le plus rassurant.

!!! info "Deux questions, pas deux réponses"

    *À quel point suis-je concentré par position ?* et *à quel point suis-je concentré par instrument ?* sont deux questions différentes, et un portefeuille réparti entre plusieurs courtiers y répond différemment par construction. La vue par instrument est celle qui correspond à l'exposition au marché : le même fonds détenu sur deux comptes est un seul pari, quel que soit le nombre de lignes qu'il occupe.

    Lorsque deux chiffres divergent, ce qu'il faut établir, c'est le niveau de granularité utilisé par chacun — et non lequel des deux est correct.

Un chiffre calculé sur les positions est vérifiable sur ce point : les rapports de portefeuille et de courtier de LibreFolio construisent leur indice de Herfindahl à partir des poids par position, et une position y est identifiée par **à la fois** son instrument et son courtier.

---

## 🪙 Où se situe la trésorerie {: #where-cash-sits }

La trésorerie doit être traitée d'une manière ou d'une autre, et ce choix change le résultat. Dans les rapports de portefeuille et de courtier, la règle est énoncée dans le code lui-même : les poids correspondent à la valeur de la position rapportée à la **NAV totale**, et la trésorerie est *incluse dans le dénominateur mais ne constitue pas elle-même un terme de l'indice*.

La conséquence mérite d'être explicitée, car elle va dans un sens que la plupart des lecteurs ne devineraient pas. La trésorerie dilue chaque poids sans apporter son propre carré, si bien que détenir plus de trésorerie **abaisse** l'indice et donc **élève** le décompte des actifs effectifs. Un portefeuille détenant la moitié de sa valeur en trésorerie paraît mieux diversifié que les mêmes positions sans cette trésorerie.

Sous cette règle, l'effet est plus important qu'un simple *paraître meilleur*. Notons $s$ la part investie du portefeuille, de sorte que $s = 1 - \text{fraction de trésorerie}$ et que les poids somment à $s$ au lieu de un. Ajouter de la trésorerie à un ensemble fixe de positions multiplie l'indice par $s^{2}$ et le décompte des actifs effectifs par $1/s^{2}$ ; pour $n$ positions équipondérées, cela vaut exactement

$$
N_{eff} = \frac{n}{s^{2}}
$$

Deux positions et aucune trésorerie donnent 2,00. Les mêmes deux positions donnent 8,00 avec la moitié de la valeur en trésorerie, environ **11,4** avec un peu plus de la moitié en trésorerie, et 200 avec quatre-vingt-dix pour cent en trésorerie. Un portefeuille de deux positions peut donc afficher un chiffre plusieurs fois supérieur à deux, sans aucune borne supérieure : lorsque la trésorerie tend vers la totalité du portefeuille, le décompte diverge.

Des poids inégaux tirent en sens inverse, si bien qu'un portefeuille déséquilibré détenant peu de trésorerie peut malgré tout afficher moins d'actifs effectifs que de positions. L'inflation, elle, est toujours présente — et la lecture familière, une valeur comprise entre un et le nombre de positions, ne décrit que le cas sans trésorerie.

C'est défendable — la trésorerie est réellement une position non concentrée, et elle réduit réellement l'exposition à un instrument donné — mais c'est une hypothèse, non un fait neutre, et lire un chiffre de concentration sans la connaître invite à une conclusion erronée. Deux portefeuilles aux positions identiques mais aux soldes de trésorerie différents ne sont pas également diversifiés du point de vue de leur capital investi.

---

## 💡 Interprétation {: #interpretation }

Lisez les deux chiffres comme une paire, dans cet ordre :

1. **Les actifs effectifs face au nombre réel de positions.** Le sens de l'écart en détermine la signification : **en dessous** du décompte, les poids sont déséquilibrés et quelques positions portent le portefeuille quel que soit le nombre de lignes ; **au-dessus**, l'excédent est de la trésorerie, et il ne dit rien de la répartition des poids.
2. **Le ratio de diversification.** Une valeur proche de 1 signifie que les positions évoluent d'un seul bloc et que la répartition n'a pas apporté grand-chose. Plus la valeur dépasse 1, plus les positions se compensent mutuellement.

C'est le second chiffre qui peut contredire le premier, et c'est cette contradiction qui porte l'information. Un portefeuille peut être parfaitement équilibré en termes de poids et non diversifié sur le fond — c'est le résultat ordinaire de la détention de plusieurs fonds suivant des marchés qui se recoupent.

Aucun des deux chiffres ne dit **quelles** positions portent le risque. Cette attribution relève de la [Contribution au risque](risk-contribution.md), et le comportement par paire qui sous-tend les deux est traité dans la [Corrélation](correlation.md).

---

## ⚠️ Limitations {: #limitations }

!!! warning "Les poids seuls peuvent être rassurants"

    Le chiffre fondé sur le décompte est une fonction des poids et de rien d'autre. Il ne peut pas distinguer un portefeuille réellement varié d'un ensemble de positions quasi identiques, et il ne constitue pas à lui seul une preuve de diversification.

!!! warning "Sensible à la corrélation ne signifie pas prospectif"

    Le ratio de diversification dépend de volatilités et de corrélations estimées sur une fenêtre, et celles-ci changent — généralement dans la direction la moins commode, car les corrélations ont tendance à augmenter sur les marchés sous tension. Un ratio confortable mesuré sur une période calme est une mesure de cette période. Voir la [Qualité des données](data-quality.md) pour la fenêtre sur laquelle chaque résultat a été calculé.

!!! warning "La concentration n'est pas automatiquement un défaut"

    Aucun des deux chiffres n'est une note. Un portefeuille délibérément concentré est un choix, et un décompte élevé d'actifs effectifs n'est pas une réussite en soi — comme le montre le tableau ci-dessus, il peut être affiché par un portefeuille détenant dix versions du même pari.

---

## 🔗 Voir aussi {: #related }

- 🔗 **[Corrélation](correlation.md)** — le comportement par paire que résume le ratio de diversification
- 🧩 **[Contribution au risque](risk-contribution.md)** — quelles positions portent le risque, une fois les poids et les co-mouvements combinés
- 📊 **[Volatilité](volatility.md)** — la grandeur à laquelle le ratio de diversification se compare
- 🧪 **[Qualité des données](data-quality.md)** — la fenêtre sur laquelle les volatilités et corrélations ont été estimées
