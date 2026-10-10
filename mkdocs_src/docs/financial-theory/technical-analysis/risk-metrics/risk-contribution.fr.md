# 🧩 Contribution au risque

La contribution au risque attribue le risque total du portefeuille aux positions individuelles, et ce qu'apporte chaque position n'est généralement pas identique à la part du portefeuille qu'elle représente.

Connaître les pondérations n'apprend rien de nouveau — elles sont visibles dans le portefeuille lui-même. Savoir d'où vient le **risque** est en revanche instructif, car la contribution d'une position dépend de sa volatilité et de la façon dont elle évolue conjointement avec tout ce avec quoi elle est détenue.

---

## 🔢 Formule {: #formula }

La décomposition part de la variance du portefeuille, écrite à l'aide de la matrice de covariance $\Sigma$ des rendements des actifs et du vecteur des pondérations $w$ :

$$
\sigma_p = \sqrt{w^{\top} \Sigma\, w}
$$

Trois quantités en sont dérivées, dans cet ordre :

$$
MCTR_i = \frac{(\Sigma w)_i}{\sigma_p}, \qquad
CCTR_i = w_i \cdot MCTR_i, \qquad
PCTR_i = \frac{CCTR_i}{\sigma_p}
$$

| Quantité | Se lit comme | Répond à |
|---|---|---|
| $MCTR_i$ — marginale | Sensibilité de la volatilité du portefeuille à la pondération de $i$ | *Si j'ajoute un peu de cette position, de combien le risque total bouge-t-il ?* |
| $CCTR_i$ — composante | Cette sensibilité multipliée par la pondération réellement détenue | *Quelle part du risque total cette position apporte-t-elle, en unités de volatilité ?* |
| $PCTR_i$ — pourcentage | La composante exprimée en part de la volatilité totale | *Quelle fraction du risque du portefeuille cette position représente-t-elle ?* |

La valeur marginale est la dérivée $\partial \sigma_p / \partial w_i$ : elle décrit la **prochaine** unité de la position, pas celle détenue. La valeur de composante est celle qui décrit la position telle qu'elle est.

!!! info "L'annualisation est appliquée à la matrice de covariance"

    Chaque entrée de $\Sigma$ est multipliée par le facteur d'annualisation observé $f$ avant que la décomposition ne s'exécute, de sorte que la volatilité du portefeuille et les trois valeurs de contribution ressortent sur une base annuelle. Mettre à l'échelle une covariance par $f$ est la forme matricielle de la multiplication d'un écart-type par $\sqrt{f}$ — la même opération, et le même facteur mesuré, que ceux utilisés par [Volatilité](volatility.md). Voir [Annualisation observée](observed-annualization.md) pour l'origine de $f$.

---

## ➗ Pourquoi les parties s'additionnent {: #why-the-parts-add-up }

Les contributions de composante s'additionnent pour donner **exactement** la volatilité du portefeuille, et les contributions en pourcentage s'additionnent donc pour donner $1$ :

$$
\sum_i CCTR_i = \sum_i w_i \frac{(\Sigma w)_i}{\sigma_p} = \frac{w^{\top} \Sigma\, w}{\sigma_p} = \frac{\sigma_p^{2}}{\sigma_p} = \sigma_p
\qquad\Longrightarrow\qquad
\sum_i PCTR_i = 1
$$

Il ne s'agit pas d'une approximation qui se trouve être proche, ni d'une normalisation appliquée après coup pour forcer les chiffres à un total rond. C'est la décomposition d'Euler, et elle tient parce que $\sigma_p$ est **homogène de degré 1 par rapport aux pondérations** : doubler chaque pondération double la volatilité du portefeuille. Toute fonction de ce type est reconstituée exactement par la somme de ses arguments multipliés par ses propres dérivées partielles, ce qui est précisément la somme ci-dessus.

La conséquence pratique est la raison même pour laquelle la métrique est publiée : parce que les parts sont exactes et sont égales à 1, **une contribution en pourcentage peut être comparée directement à une pondération**. Une position représentant 10 % du portefeuille et portant 30 % du risque est un énoncé sans aucun facteur d'échelle caché.

---

## ⚖️ La contribution n'est pas la pondération {: #contribution-is-not-weight }

Les deux nombres répondent à des questions différentes, et ils se séparent pour deux raisons qui se cumulent :

- **La volatilité.** Une position qui évolue deux fois plus que le reste apporte plus de risque par unité de capital.
- **La corrélation.** Une position qui évolue *avec* les autres ajoute sa volatilité à la leur ; une position qui évolue contre elles annule en partie ce que font les autres. La même position, à la même pondération, contribue différemment selon les autres positions avec lesquelles elle est détenue.

Cette seconde raison explique pourquoi la contribution ne peut pas se lire sur une position isolée : $(\Sigma w)_i$ contient toutes les covariances entre l'actif $i$ et le reste du portefeuille, si bien que modifier une position *sans lien* change la contribution de celle-ci.

!!! tip "Ce qui justifie la place de cette métrique"

    Une petite position dans un actif volatil et étroitement lié au reste du portefeuille peut porter une part de risque plusieurs fois supérieure à sa part de capital — et la vue du portefeuille ne le montrera jamais, car la vue du portefeuille montre les pondérations. Inversement, une position importante qui évolue en décalage avec tout le reste peut contribuer bien moins de risque que sa taille ne le suggère. La diversification est visible ici d'une manière qu'elle n'a pas dans [Corrélation](correlation.md) seule : la corrélation dit quelles paires évoluent ensemble, celle-ci dit ce que cela coûte une fois les montants détenus pris en compte.

---

## 🧾 Ce que les entrées doivent satisfaire {: #what-the-inputs-must-satisfy }

La décomposition refuse les entrées qu'elle ne peut pas décomposer honnêtement. Ce sont des **limites déclarées de la première vague**, non des lacunes laissées par omission :

| Exigence | Comportement en cas de violation |
|---|---|
| Les pondérations doivent être non négatives | Refusé — les positions courtes sont hors du contrat de la première vague |
| La composition ne doit pas comporter d'effet de levier | Refusé en amont — des pondérations d'actifs supérieures à 100 % de la valeur du périmètre sont hors du contrat |
| La matrice de covariance doit être symétrique | Refusé, à une tolérance numérique près pour le bruit en virgule flottante |
| Les dimensions de la matrice doivent correspondre aux pondérations | Refusé |
| Toutes les séries de rendements doivent partager un même calendrier commun | Refusé — la matrice de covariance est construite sur un seul calendrier d'observation |

Une position courte briserait l'arithmétique ci-dessus d'une manière précise : avec des pondérations négatives, une contribution de composante peut être négative, et une part de « risque total » inférieure à zéro ne peut se lire comme la part de quoi que ce soit. Refuser l'entrée est la réponse honnête tant que le contrat de présentation ne couvre pas ce cas.

Les liquidités sont traitées sans apparaître du tout dans la matrice. Les pondérations des actifs sont égales à un moins la part de liquidités, si bien que la volatilité calculée est déjà celle du portefeuille **entier**, liquidités comprises — et les liquidités n'apparaissent jamais comme contributrices, car une position qui ne bouge pas a une contribution marginale nulle. La part de liquidités est publiée aux côtés des contributions afin que le lecteur puisse voir ce que représente le reste.

---

## 💡 Interprétation {: #interpretation }

Lisez la contribution en pourcentage **par rapport à la pondération**, et non isolément :

- contribution ≈ pondération — la position porte sa propre part, pas plus
- contribution > pondération — elle est une source concentrée de risque par rapport au capital qui lui est engagé
- contribution < pondération — elle dilue le risque du portefeuille, soit parce qu'elle est calme, soit parce qu'elle évolue différemment du reste

La valeur marginale répond à une autre question et c'est celle à utiliser lorsqu'on envisage un changement : elle indique ce que le **prochain** euro placé dans cette position fait à la volatilité totale. Une position peut porter une contribution de composante importante simplement parce qu'elle est grande, alors que sa contribution marginale est quelconque.

---

## ⚠️ Limites {: #limitations }

!!! warning "Elle décompose la volatilité, pas la perte"

    Chaque valeur de cette page est une part de la **volatilité du portefeuille**. La volatilité compte les mouvements dans les deux sens, de sorte qu'une position qui contribue à 30 % du risque n'est pas pour autant censée produire 30 % d'une quelconque perte. Les contributions à une mesure de baisse sont une décomposition différente, et ce n'est pas celle-ci. Pour ce que la fluctuation capture et ne capture pas, voir [Volatilité](volatility.md).

!!! warning "C'est un instantané de la composition actuelle"

    Les pondérations sont celles détenues aujourd'hui, et la matrice de covariance est estimée sur la fenêtre analysée. Le résultat décrit le portefeuille d'aujourd'hui mesuré par rapport à cet historique — ce n'est pas un énoncé sur la façon dont le risque était réparti dans le passé, lorsque la composition était différente.

!!! warning "La matrice est une estimation, et elle hérite de sa fenêtre"

    Les covariances sont estimées à partir d'un échantillon fini sur un même calendrier commun. Une fenêtre courte, une période agitée ou un actif dont l'historique de prix est clairsemé produisent une estimation qu'une autre fenêtre ne reproduirait pas, et chaque contribution dérive de cette estimation. Les corrélations en particulier sont connues pour se déplacer lorsque les marchés sont sous tension. Chaque résultat publie le nombre d'observations et la fenêtre utilisée — voir [Qualité des données](data-quality.md).

!!! warning "Une volatilité nulle renvoie des zéros, pas un résultat absent"

    Si la volatilité du portefeuille est indiscernable de zéro, les trois valeurs de contribution sont renvoyées égales à zéro exactement. C'est la réponse, pas une valeur de remplissage : sans risque à attribuer, chaque part de ce risque n'est véritablement rien. Il est instructif de comparer ce cas à la page [Bêta et rendement actif](beta-active-return.md), où un indice de référence sans variance **ne produit aucune valeur du tout** — là, la quantité serait une division par zéro, donc il n'y a rien à rapporter ; ici, la quantité existe et vaut zéro.

---

## 🔗 Voir aussi {: #related }

- 🔗 **[Corrélation](correlation.md)** — quelles positions évoluent ensemble, avant que les montants ne soient pris en compte
- 📊 **[Volatilité](volatility.md)** — le total qui est décomposé
- 🎯 **[Concentration](concentration.md)** — quelle part du portefeuille repose sur un petit nombre de positions
- 🗓️ **[Annualisation observée](observed-annualization.md)** — le facteur appliqué à la matrice de covariance
- 🧪 **[Qualité des données](data-quality.md)** — la fenêtre et les observations sur lesquelles la matrice a été estimée
