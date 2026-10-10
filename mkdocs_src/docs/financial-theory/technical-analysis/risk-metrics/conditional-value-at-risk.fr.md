# 🌊 VaR conditionnelle

La VaR conditionnelle prend le relais exactement là où la valeur à risque s'arrête : elle mesure la perte moyenne dans les cas où le seuil de la valeur à risque a effectivement été franchi.

La [valeur à risque](value-at-risk.md) dit **où commence la queue**. Celle-ci dit **jusqu'où elle va**. Toute la différence est là, et c'est pourquoi c'est le chiffre que la section met en avant.

---

## 🔢 Formule {: #formula }

Au niveau de confiance $c$, la VaR conditionnelle est la perte espérée **sachant** que la perte a dépassé la valeur à risque :

$$
CVaR_c = E\left[\, L \mid L \ge VaR_c \,\right]
$$

Empiriquement, elle est la moyenne des pertes dans la queue au-delà du seuil — la moyenne des mauvais cas, plutôt que la frontière des mauvais cas.

Parce qu'elle fait la moyenne d'une région au lieu de lire un point, elle porte une information que le quantile ne peut pas porter : deux portefeuilles ayant la **même** valeur à risque peuvent avoir des VaR conditionnelles très différentes, l'une dépassant le seuil de peu et l'autre de beaucoup. Rien dans le premier chiffre ne permet de les distinguer ; celle-ci le fait.

!!! tip "Elle récompense elle aussi la diversification de manière cohérente"

    Il existe une seconde raison, plus technique, pour laquelle la pratique du risque s'est tournée vers les moyennes de queue. Un quantile peut se comporter de manière perverse lorsque des portefeuilles sont combinés : il est possible que la valeur à risque d'un portefeuille combiné dépasse la somme des valeurs à risque de ses composantes, ce qui reviendrait à dire que diversifier a augmenté le risque. Une moyenne sur la queue n'a pas ce défaut, ce qui en fait le chiffre au comportement le plus fiable lorsqu'on compare le risque entre différentes compositions.

---

## 🔬 Comment la moyenne de queue est calculée {: #how-the-tail-average-is-taken }

La queue contient rarement un nombre entier d'observations. À un niveau de confiance de 95 % sur quelques centaines de périodes, la frontière de la queue tombe **entre** deux pertes observées, et l'observation située sur cette frontière n'appartient que partiellement à la queue.

La moyenne pondère donc cette observation frontière par la fraction de celle-ci qui se situe réellement au-delà du seuil, au lieu de compter chaque observation de la queue à poids égal. Traiter une observation partiellement incluse comme pleinement incluse tire la moyenne vers la frontière — c'est-à-dire vers la perte la moins sévère de la queue — et indique donc une queue moins profonde qu'elle ne l'est.

---

## 📐 La correction, et ce qu'elle fait à votre chiffre {: #the-correction }

Il s'agit d'une modification d'un chiffre que vous avez peut-être déjà vu. L'estimateur précédent prenait une moyenne **uniforme** sur la queue ; l'actuel applique la pondération fractionnaire décrite ci-dessus.

!!! warning "Le nouveau chiffre n'est pas simplement différent — il est moins optimiste"

    La correction déplace la VaR conditionnelle **à la hausse à chaque niveau de confiance**, dans chaque échantillon d'une étude de mesure portant sur 2 000 séries simulées de 750 observations chacune : 2 000 sur 2 000, sans une seule exception dans un sens ou dans l'autre.

    C'est là tout l'enjeu. Le chiffre précédent **sous-estimait la queue** : il rapportait le mauvais cas moyen comme plus bénin que ne le disaient les données. Un utilisateur qui voit ce chiffre augmenter ne voit pas une nouvelle méthodologie produire une différence arbitraire — il voit une estimation optimiste remplacée par une estimation exacte.

| Confiance | Variation mesurée (médiane) | Variation maximale observée | Échantillons ayant augmenté |
|---|---|---|---|
| 90 % | +0,364 % | +0,476 % | 2 000 / 2 000 |
| 95 % | +0,267 % | +0,404 % | 2 000 / 2 000 |
| 99 % | +0,727 % | +1,748 % | 2 000 / 2 000 |

**Le décalage croît avec le niveau de confiance**, et la raison découle du mécanisme : plus le niveau est élevé, moins il y a d'observations dans la queue, de sorte que l'unique observation partiellement incluse porte une part plus importante de la moyenne. À 99 %, une poignée d'observations décide du chiffre, et une mauvaise pondération de l'une d'elles déplace le résultat davantage qu'à 90 %.

!!! info "Le chiffre corrigé correspond à l'implémentation de référence"

    Mesuré par rapport à l'implémentation de référence standard du même estimateur, l'écart restant est de $-4{,}27 \times 10^{-18}$ — du bruit d'arrondi en virgule flottante, et non un écart méthodologique. Les deux calculent désormais la même quantité.

Le chiffre du seuil évolue lui aussi, mais sous une condition bien plus étroite : la [valeur à risque](value-at-risk.md) rapportée à côté de celle-ci ne change que lorsque le nombre d'observations est divisible de la manière que requiert le niveau de confiance, et là où elle change, elle saute d'une observation entière plutôt que de dériver légèrement. La règle, et la façon de vérifier un cas particulier, sont exposées dans [ce que la correction change](value-at-risk.md#what-the-correction-changes). Les deux sont des changements distincts qui se produisent en même temps : celui-ci porte sur la manière dont la queue est moyennée, et non sur l'endroit où la queue commence.

---

## 💡 Interprétation {: #interpretation }

Lisez ce chiffre comme *à quel point cela devient mauvais quand cela devient mauvais* — le résultat moyen sur les pires cas de la fenêtre, et non le pire d'entre eux.

- Elle est toujours au moins aussi sévère que la valeur à risque au même niveau, car elle fait la moyenne de valeurs qui dépassent toutes ce seuil.
- L'écart entre les deux est en soi informatif : une VaR conditionnelle très supérieure à sa valeur à risque décrit un portefeuille dont les mauvais cas, lorsqu'ils surviennent, sont bien pires que ne le suggère le seuil.
- Comme le quantile qu'elle étend, elle lit la **distribution** et non la séquence : réordonner l'ordre des rendements observés la laisse inchangée. La vue dépendante du chemin appartient à la [perte maximale](max-drawdown.md) et au [repli actuel](current-drawdown.md), et une vue complète nécessite les deux.

---

## ⚠️ Limites {: #limitations }

!!! warning "La queue est estimée à partir de peu d'observations"

    Par définition, seule une petite fraction de la fenêtre se situe au-delà du seuil, et à 99 % cette fraction est très petite. Le chiffre est donc la mesure distributionnelle la moins stable : il peut se déplacer sensiblement à mesure que de nouvelles observations arrivent, et deux fenêtres adjacentes peuvent diverger davantage que ne le suggère leur différence de longueur.

!!! warning "Elle reste bornée par l'historique qui lui a été fourni"

    Faire la moyenne de la queue ne fait pas surgir des pertes que le portefeuille n'a jamais connues. Si la fenêtre ne contient aucun épisode sévère, la queue dont elle fait la moyenne est bénigne — la mesure rendra honnêtement compte d'un historique qui n'a simplement pas été mis à l'épreuve. Un [rejeu historique](historical-replay.md) ou un [choc hypothétique](hypothetical-shock.md) est la façon dont un scénario extérieur à la fenêtre entre dans l'analyse.

!!! warning "Elle décrit la sévérité, pas la probabilité"

    Le chiffre est conditionné au fait que la queue soit atteinte. Il ne dit rien de la probabilité que cela se produise au-delà du niveau de confiance qui l'a défini, ni du moment où cela arrivera — les mauvaises périodes se regroupent, et aucun résumé distributionnel ne porte cette information.

---

## 🔗 Voir aussi {: #related }

- 📉 **[valeur à risque](value-at-risk.md)** — le seuil au-delà duquel cette mesure fait la moyenne
- 📉 **[Perte maximale](max-drawdown.md)** — la pire baisse cumulée le long du chemin
- 📊 **[Volatilité](volatility.md)** — la dispersion dans les deux sens, plutôt que la seule queue de pertes
- ⚡ **[Choc hypothétique](hypothetical-shock.md)** — un scénario que l'historique observé n'a jamais contenu
- 🧪 **[Qualité des données](data-quality.md)** — la fenêtre dont la queue a été tirée
