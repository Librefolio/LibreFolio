# 📉 Repli à risque

Le repli à risque applique l'idée de quantile aux replis plutôt qu'aux rendements : c'est la profondeur de repli qui ne devrait pas être dépassée à un niveau de confiance choisi.

Tout ce qu'est la [valeur à risque](value-at-risk.md), celui-ci l'est — à une substitution près. Là où cette mesure trie les **pertes** subies par le portefeuille, celui-ci trie les **distances sous un sommet** qu'il a connues. L'étroitesse est identique, et le piège aussi : il marque où commence la queue de repli, et reste silencieux sur tout ce qui la dépasse.

---

## 🔢 Formule {: #formula }

Le repli à l'observation $t$ est la distance par rapport à la valeur la plus élevée atteinte jusqu'ici :

$$
DD_t = \frac{V_t - \max_{\tau \leq t} V_\tau}{\max_{\tau \leq t} V_\tau} \leq 0
$$

Au niveau de confiance $c$, en notant $\alpha = 1 - c$ la fraction de queue, le repli à risque est le $\alpha$-quantile de cette série :

$$
DaR_c = \inf\left\{\, d : P(DD_t \leq d) \geq \alpha \,\right\}
$$

En pratique, il s'agit d'un exercice de tri, exactement comme pour la valeur à risque : les replis observés sur la fenêtre analysée sont triés du plus profond au moins profond, et la valeur est lue à la position qu'indique $\alpha T$.

!!! info "Signe et lecture"

    Le repli à risque est **non positif** — nul ou négatif. Un repli est une baisse depuis un sommet, il ne peut donc pas être supérieur à zéro, et une valeur *plus profonde* est *plus négative*. À 95 % de confiance, l'énoncé est : dans 19 observations sur 20, le portefeuille ne se trouvait pas plus bas sous son sommet que cette valeur, et dans la dernière, il se trouvait plus bas — d'un montant que cette mesure n'indique pas.

    Le $T$ ici ne compte que les points observés. La référence de départ d'un indice de richesse porte un repli exactement nul par construction, et la famille des quantiles l'écarte avant le tri, de sorte qu'il n'entre pas dans le classement et ne gonfle pas le dénominateur. L'[indice d'Ulcer](ulcer-index.md) le conserve, sans dommage, pour une raison exposée [sur sa propre page](ulcer-index.md#the-divisor).

---

## 🎯 C'est une statistique d'ordre {: #it-is-an-order-statistic }

La valeur est lue sur une liste triée, ce qui fixe à l'avance deux de ses propriétés.

- **Il ne peut signaler qu'une profondeur que le portefeuille a réellement connue.** Il n'y a ni interpolation ni distribution supposée ; le nombre est l'une des observations, sélectionnée par sa position. Il ne peut pas décrire un repli que l'historique n'a jamais contenu.
- **C'est une fonction en escalier d'un indice.** Entre une position et la suivante, il ne bouge pas du tout, et lorsque la position change, il saute d'une observation entière. C'est le même mécanisme qui fait que la valeur à risque change de manière tout ou rien, décrit dans [ce que la correction change](value-at-risk.md#what-the-correction-changes).

---

## 🔁 Le même pas que la VaR franchit vers la CVaR {: #the-same-step-that-var-takes-to-cvar }

Un quantile s'arrête à la frontière. Deux portefeuilles peuvent afficher le même repli à risque alors que l'un le dépasse d'un cheveu et que l'autre s'effondre bien au-delà, et rien dans cette valeur ne les distingue. Ce silence est exactement ce que comble le [repli à risque conditionnel](conditional-drawdown-at-risk.md).

| Lit la série des **pertes** | Lit la série des **replis** | Ce à quoi il répond |
|---|---|---|
| [Valeur à risque](value-at-risk.md) | **Repli à risque** | Où commence la queue ? |
| [VaR conditionnelle](conditional-value-at-risk.md) | [Repli à risque conditionnel](conditional-drawdown-at-risk.md) | Jusqu'où va-t-elle une fois qu'elle commence ? |

Lire les colonnes de haut en bas donne les deux paires seuil-et-sévérité ; lire les lignes horizontalement donne la même question posée à une distribution et à un chemin. Une image complète nécessite les quatre, et la paire de droite est celle qui sait que le portefeuille avait un sommet d'où chuter.

---

## 💡 Interprétation {: #interpretation }

Lisez-le comme *la profondeur à laquelle un mauvais jour vous place typiquement sous le sommet*, jamais comme un plancher.

- **C'est un seuil, pas une borne.** Les replis plus profonds ne sont pas exclus — ils sont, par construction, attendus au taux indiqué.
- **Le niveau de confiance change la question, pas la précision.** Passer de 95 % à 99 % pose la question d'une période plus rare, estimée à partir de moins d'observations, et non de la même période mieux mesurée.
- **Ce n'est pas la perte maximale.** La [perte maximale](max-drawdown.md) est le point le plus profond unique de la fenêtre ; ici, c'est le niveau qu'une fraction choisie de la fenêtre a dépassé. Les deux ne coïncident que dans la limite où la queue contient une seule observation.

---

## ⚠️ Limites {: #limitations }

!!! warning "Silencieux au-delà du seuil"

    La mesure s'arrête à la frontière de la queue de repli. Que les chutes au-delà soient légèrement plus profondes ou catastrophiquement plus profondes est une information qu'elle ne porte pas, et aucun niveau de confiance ne la récupère. Utilisez le [repli à risque conditionnel](conditional-drawdown-at-risk.md) pour la profondeur.

!!! warning "Les observations de repli ne sont pas indépendantes les unes des autres"

    Les observations consécutives au sein d'un même épisode sont presque le même nombre : un portefeuille sous le sommet mardi est presque certainement sous le sommet mercredi. La queue d'une série de replis est donc rarement $\alpha T$ événements distincts — c'est plus souvent une poignée d'épisodes, ou un seul long, compté jour après jour.

    Cela rend la valeur moins stable que ne le suggère son nombre d'observations, et cela signifie qu'une seule baisse prolongée peut fournir toute la queue à elle seule.

!!! warning "Il hérite de sa fenêtre"

    Un quantile empirique est borné par l'historique dont il est issu. Une fenêtre sans épisode sévère produit un repli à risque faible — non pas parce que le portefeuille est sûr, mais parce que rien de pire n'a encore été observé. Un [Rejeu historique](historical-replay.md) ou un [Choc hypothétique](hypothetical-shock.md) est la façon dont un scénario extérieur à la fenêtre entre dans l'analyse.

---

## 🔗 Voir aussi {: #related }

- 🌊 **[Repli à risque conditionnel](conditional-drawdown-at-risk.md)** — jusqu'où la queue de repli va au-delà de ce seuil
- 📉 **[Valeur à risque](value-at-risk.md)** — la même construction de quantile, appliquée aux pertes plutôt qu'aux replis
- 🌊 **[VaR conditionnelle](conditional-value-at-risk.md)** — la contrepartie de sévérité sur la série des pertes
- 📉 **[Perte maximale](max-drawdown.md)** — la chute unique la plus profonde, plutôt qu'un taux
- 🩹 **[Indice d'Ulcer](ulcer-index.md)** — toute la série de replis en un seul nombre, sans niveau de confiance
- 🧪 **[Qualité des données](data-quality.md)** — la fenêtre et le nombre d'observations à partir desquels le quantile a été lu
