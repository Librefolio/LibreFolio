# 🔻 Pire réalisation

La pire réalisation est simplement le rendement sur une période isolée le moins favorable effectivement observé dans l'historique disponible — un fait observé plutôt qu'une estimation.

Toutes les autres valeurs de cette section sont calculées *à partir* des observations. Celle-ci **est** l'une d'entre elles.

---

## 🔢 Ce que c'est {: #what-it-is }

Étant donné les rendements de la fenêtre analysée, la pire réalisation est leur minimum :

$$
WR = \min_t \; r_t
$$

Il n'y a pas de niveau de confiance à choisir, pas de distribution à présumer, pas de moyenne à calculer. La valeur est un rendement qui a eu lieu, et elle est accompagnée de **la date à laquelle il a eu lieu** — ce qui la distingue de tous les paramètres des pages voisines. Une date peut être vérifiée. Elle ancre le nombre à un événement que le portefeuille a réellement traversé, plutôt qu'à une construction statistique.

---

## 🆚 Face à la valeur à risque {: #against-value-at-risk }

Le pendant naturel est [Valeur à risque](value-at-risk.md), et le duo fonctionne par **contraste** plutôt que par répétition :

| | Dit | Nature |
|---|---|---|
| Valeur à risque | *Une période sur vingt est pire que cela* | Un seuil, estimé |
| Pire réalisation | *Et la pire a été celle-ci, à cette date* | Un point unique, observé |

La valeur à risque décrit un **taux** et reste muette sur l'ampleur au-delà du seuil. La pire réalisation décrit une **ampleur** et reste muette sur le taux — elle s'est produite une fois, et la valeur ne dit rien de la probabilité qu'elle se reproduise. [VaR conditionnelle](conditional-value-at-risk.md) se situe entre les deux, en moyennant toute la queue plutôt qu'en lisant sa frontière ou son extrême.

Ensemble, ils encadrent la queue : où elle commence, quelle est sa profondeur moyenne et le pas unique le plus profond enregistré.

---

## 🧭 Distribution ou chemin {: #distribution-or-path }

Les métriques étiquetées *risque* se répartissent en deux familles qui répondent à des questions différentes, et rien dans une rangée de huit nombres n'indique à quelle famille elles appartiennent.

!!! info "Mélangez les rendements, et regardez ce qui bouge"

    **Mélangez l'ordre des rendements d'un portefeuille et la valeur à risque ne change pas d'une virgule — alors que la perte maximale peut doubler.**

    La valeur à risque, la VaR conditionnelle et la pire réalisation lisent la **distribution** : quels rendements se sont produits, dans n'importe quel ordre. [Perte maximale](max-drawdown.md), [Repli actuel](current-drawdown.md) et les durées qui leur sont attachées lisent le **chemin** : l'ordre dans lequel ils sont arrivés.

La pire réalisation appartient fermement à la famille des distributions, et la distinction n'est pas académique. Elle répond à *combien une période isolée peut-elle être mauvaise ?* — alors qu'un portefeuille n'est pas détruit par un mauvais jour, mais par une **séquence** de ceux-ci. Trois pertes consécutives de 5 % font plus de dégâts financiers qu'une perte isolée de 12 %, et seule la famille qui lit le chemin peut les distinguer.

Lire une valeur distributionnelle comme si elle décrivait la pire expérience possible est l'erreur que cette section est agencée pour prévenir.

---

## 💡 Interprétation {: #interpretation }

Utilisez-la comme un contrôle de réalité sur les valeurs estimées. Une valeur à risque bien plus douce que la pire réalisation n'est pas une contradiction — le quantile est censé être dépassé parfois, et voici à quoi ressemblait ce dépassement à son paroxysme.

La date compte autant que la valeur. Une pire réalisation issue d'un événement de marché bien connu ne se lit pas de la même façon que celle d'un jour sans particularité, ce qui pointe souvent vers quelque chose de spécifique au portefeuille : une seule position, un événement sur titres, ou un artefact de valorisation qu'il vaut la peine de vérifier dans [Qualité des données](data-quality.md).

---

## ⚠️ Limites {: #limitations }

!!! warning "C'est un extremum, donc la fenêtre ne peut que l'empirer"

    Allonger la période analysée ne peut jamais améliorer cette valeur et ne peut que l'empirer : une fenêtre plus longue contient toutes les observations de la plus courte, plus de chances de trouver pire. Comparer les pires réalisations entre portefeuilles n'a donc pas de sens, sauf si elles ont été mesurées sur la même fenêtre — un historique plus long paraîtra généralement pire pour cette seule raison.

!!! warning "Une observation ne porte aucune fréquence"

    La valeur repose sur une seule période. Elle ne dit rien sur la fréquence d'une telle période, sur le fait qu'un épisode proche se soit produit plus d'une fois, ni sur le comportement du reste de la queue. Pour la forme de la queue plutôt que son extrême, utilisez [VaR conditionnelle](conditional-value-at-risk.md).

!!! warning "Cela dépend de la longueur d'une période"

    Le pire jour, la pire semaine et le pire mois sont des quantités différentes, et elles ne se convertissent pas les unes en les autres. La valeur est liée à la fréquence d'observation de la série à partir de laquelle elle a été lue — voir [Annualisation observée](observed-annualization.md) pour savoir comment cette fréquence est établie.

---

## 🔗 Voir aussi {: #related }

- 📉 **[Valeur à risque](value-at-risk.md)** — où commence la queue, sous forme de taux plutôt que de fait
- 🌊 **[VaR conditionnelle](conditional-value-at-risk.md)** — la profondeur moyenne de la queue au bout de laquelle se situe cette valeur
- 📉 **[Perte maximale](max-drawdown.md)** — la pire baisse cumulée, qui lit le chemin plutôt que la distribution
- 📊 **[Volatilité](volatility.md)** — dispersion typique, à l'aune de laquelle un extrême peut être jugé
- 🧪 **[Qualité des données](data-quality.md)** — la fenêtre et la série sur lesquelles le minimum a été pris
