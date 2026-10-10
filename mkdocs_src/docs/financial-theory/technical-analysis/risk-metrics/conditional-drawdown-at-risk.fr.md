# 🌊 Repli à risque conditionnel

Le repli à risque conditionnel fait la moyenne des replis qui ont effectivement franchi le seuil de Repli à risque, répondant à la question : jusqu'où va la chute une fois ce point dépassé.

[Repli à risque](drawdown-at-risk.md) indique **où commence la queue des replis**. Celui-ci indique **jusqu'où elle descend** — la même étape que [VaR conditionnelle](conditional-value-at-risk.md) franchit au-delà de [valeur à risque](value-at-risk.md), appliquée à la série des replis plutôt qu'à celle des pertes.

Le mot *moyenne* dans cette première phrase porte plus de poids qu'il n'y paraît. Il s'agit d'une moyenne **pondérée**, et le poids est fixé par le niveau de confiance plutôt que par le nombre d'observations qui se trouvent dans la queue. Cette distinction fait l'objet de la majeure partie de cette page, car le raccourci qu'elle exclut est plausible.

---

## 🔢 Formule {: #formula }

Au niveau de confiance $c$, en notant $\alpha = 1 - c$ la fraction de queue, la mesure prend la forme **Rockafellar–Uryasev** :

$$
CDaR_c = DaR_c - \frac{1}{\alpha T} \sum_{t=1}^{T} \left( DaR_c - DD_t \right)^{+}
$$

où $(x)^{+} = \max(x, 0)$, $DD_t$ est le repli à l'observation $t$, et $T$ est le nombre de points observés dans la série.

La somme recueille la **sévérité excédentaire** : pour chaque observation plus profonde que le seuil, de combien elle est plus profonde. Toute observation moins profonde que le seuil ne contribue en rien. Ce total est ensuite réparti sur $\alpha T$ et soustrait du seuil, ce qui entraîne le résultat plus loin sous zéro que le Repli à risque dont il part.

Comme le seuil qu'il étend, le repli à risque conditionnel est **non positif** — un repli est une chute depuis un sommet, et faire la moyenne de chutes ne produit pas une hausse. Il est toujours au moins aussi sévère que le Repli à risque au même niveau de confiance, car toute quantité qu'il ajoute à ce seuil est une chute au-delà de celui-ci.

---

## 🔬 Ce n'est pas la moyenne des pires observations {: #it-is-not-the-average-of-the-worst-observations }

La recette intuitive — prendre les $k$ replis les plus profonds et en faire la moyenne — n'est pas cette formule, et la différence réside dans le dénominateur.

La normalisation ci-dessus est $\alpha T$ : une quantité **fixe** déterminée par le niveau de confiance et la longueur de l'historique. Le nombre d'observations dans la queue $k$ est une quantité différente — le nombre d'observations qui ont réellement dépassé le seuil, qui ne peut être qu'un nombre entier. Lorsque $\alpha T$ n'est pas entier, la queue contient nécessairement **plus** d'observations que $\alpha T$, et diviser la même sévérité totale par ce nombre plus grand produit une valeur moins profonde.

!!! warning "Le raccourci sous-estime la queue"

    Faire la moyenne sur le nombre d'observations de la queue plutôt que sur $\alpha T$ présente le cas défavorable moyen comme **plus clément** que ne le disent les données. Les deux formes coïncident **exactement** lorsque $\alpha T$ est un nombre entier, et le raccourci est trop optimiste chaque fois que ce n'est pas le cas.

    | Observations $T$ | $\alpha T$ à 95 % | Nombre entier ? | Écart relatif |
    |---|---|---|---|
    | 740 | 37,00 | oui | **0,00000 %** |
    | 745 | 37,25 | non | $-0{,}03817\ \%$ |
    | 750 | 37,50 | non | $-0{,}02528\ \%$ |
    | 760 | 38,00 | oui | **0,00000 %** |
    | 800 | 40,00 | oui | **0,00000 %** |
    | 1 000 | 50,00 | oui | **0,00000 %** |

    Les écarts sont des fractions de pour cent. C'est précisément ce qui rend le raccourci tenace : une valeur fausse de trois centièmes de pour cent ressemble à un arrondi, pas à une formule différente.

---

## 🪤 Le même piège, en sens inverse {: #the-same-trap-in-the-opposite-sense }

C'est la même forme d'erreur que celle décrite par la page [VaR conditionnelle](conditional-value-at-risk.md) pour la queue des pertes : une moyenne uniforme plausible, fausse d'une fraction de pour cent, dans la même direction — la sous-estimation de la queue. Et elle est régie par la **même quantité arithmétique**, $(1 - c) \cdot T$, que celle déjà exposée par la page [valeur à risque](value-at-risk.md#what-the-correction-changes).

!!! warning "La même quantité, le sens opposé — ne transposez pas une règle à l'autre"

    Un $(1 - c) \cdot T$ entier signifie des choses opposées sur les deux pages, et les deux énoncés se confondent facilement en un seul.

    | Mesure | Lorsque $(1 - c) \cdot T$ est un nombre entier |
    |---|---|
    | [valeur à risque](value-at-risk.md#what-the-correction-changes) | les deux conventions **divergent** — la valeur se décale d'une observation entière |
    | **Repli à risque conditionnel** | le raccourci **se trouve être juste** — les deux formes coïncident exactement |

    La divisibilité est la condition dans les deux cas ; elle sélectionne simplement le désaccord dans l'un et l'accord dans l'autre.

---

## 🔍 Vérifier soi-même la valeur {: #checking-the-figure-yourself }

Comme un $\alpha T$ entier est exactement le cas où le raccourci est indiscernable de la forme correcte, le choix de la longueur de l'historique décide si une vérification manuelle peut détecter la différence.

!!! warning "Une longueur d'historique ronde ne permet pas de distinguer les deux formes"

    | Observations $T$ | 90 % | 95 % | 99 % |
    |---|---|---|---|
    | 250 | aveugle | voit | voit |
    | 500 | **aveugle** | **aveugle** | **aveugle** |
    | 750 | aveugle | voit | voit |
    | 1 000 | **aveugle** | **aveugle** | **aveugle** |
    | 1 003 | voit | voit | voit |
    | 2 000 | **aveugle** | **aveugle** | **aveugle** |

    **500, 1 000 et 2 000 observations sont aveugles à tous les niveaux de confiance ; 1 003 détecte à tous les niveaux.**

    Ce schéma n'est pas un cas limite rare — c'est l'inverse. $\alpha T$ est entier lorsque $T$ est divisible par 10 à 90 % de confiance, par 20 à 95 %, et par 100 à 99 %, et les nombres ronds sont précisément les nombres divisibles. Deux ans, mille jours, cinq cents séances : les longueurs de fenêtre que l'on choisit en premier sont celles où les deux formes renvoient le même nombre.

!!! tip "Choisissez donc une fenêtre non arrondie"

    Si vous souhaitez vérifier la valeur en la recalculant, choisissez une longueur d'historique qui n'est **pas** un multiple rond de 10, 20 ou 100 — 1 003 observations plutôt que 1 000. À une longueur divisible, les deux formules candidates coïncident jusqu'au dernier chiffre, donc une correspondance ne vous dit rien sur celle qui l'a produite.

---

## 💡 Interprétation {: #interpretation }

Lisez-le comme *jusqu'où l'on descend sous le sommet une fois le seuil franchi* — la sévérité de la queue des replis, et non sa frontière.

- **L'écart par rapport au seuil est instructif.** Un Repli à risque conditionnel très en dessous de son Repli à risque décrit un portefeuille dont les mauvaises passes, une fois commencées, vont bien plus profond que ne le suggère le seuil.
- **C'est une profondeur, pas une durée.** Il indique jusqu'où descend la queue de la distribution des replis, et rien sur le temps pendant lequel le portefeuille y est resté. [indice d'Ulcer](ulcer-index.md) est la valeur qui intègre la durée.
- **Il lit une série dépendante du chemin.** Contrairement au couple fondé sur les pertes, cette mesure et son seuil sont calculés à partir des replis, qui dépendent de l'ordre d'arrivée des rendements. Remélanger l'historique reconstruit les deux.

---

## ⚠️ Limites {: #limitations }

!!! warning "La queue est estimée à partir de peu d'observations"

    Seule une petite fraction de la fenêtre se situe au-delà du seuil, et à 99 % cette fraction est très faible. La valeur est en conséquence instable : elle peut se décaler sensiblement à mesure que les observations arrivent, et deux fenêtres adjacentes peuvent diverger plus que ne le suggère leur différence de longueur.

!!! warning "Ces quelques observations ne sont pas indépendantes"

    Les replis au sein d'un même épisode sont presque le même nombre jour après jour, si bien que la queue est souvent une seule baisse prolongée comptée plusieurs fois plutôt que $\alpha T$ événements distincts. La mesure fait la moyenne des observations, pas des épisodes, et un historique comportant une mauvaise année peut à lui seul placer cette année dans la queue.

!!! warning "Il est borné par l'historique qui lui est fourni"

    Faire la moyenne de la queue des replis ne fait pas apparaître des baisses que le portefeuille n'a jamais connues. Une fenêtre ne contenant aucun épisode sévère produit une queue modérée, rapportée honnêtement. Un [Rejeu historique](historical-replay.md) ou un [Choc hypothétique](hypothetical-shock.md) est la manière dont un scénario extérieur à la fenêtre entre dans l'analyse.

---

## 🔗 Voir aussi {: #related }

- 📉 **[Repli à risque](drawdown-at-risk.md)** — le seuil au-delà duquel cette valeur fait la moyenne
- 🌊 **[VaR conditionnelle](conditional-value-at-risk.md)** — la même étape de sévérité, appliquée à la série des pertes
- 📉 **[Valeur à risque](value-at-risk.md)** — où la règle de divisibilité est exposée en détail
- 📉 **[Perte maximale](max-drawdown.md)** — la chute la plus profonde unique, plutôt qu'une moyenne sur la queue
- 🩹 **[indice d'Ulcer](ulcer-index.md)** — profondeur et durée ensemble, sans niveau de confiance
- 🧪 **[Qualité des données](data-quality.md)** — la fenêtre et le nombre d'observations dont la queue est issue
