# 🩹 Indice d'Ulcer

L'indice d'Ulcer combine la profondeur de la chute d'un portefeuille et la durée pendant laquelle il reste en baisse ; ainsi, un déclin modéré mais persistant peut obtenir un score pire qu'une chute brutale qui se rétablit rapidement.

Toutes les autres mesures de repli des pages voisines indiquent un **moment** — le pire, ou l'actuel. Celle-ci indique une **étendue temporelle** : elle examine le repli à chaque observation et demande quelle part de l'historique a été passée sous un sommet, et dans quelle mesure.

---

## 🔢 Formule {: #formula }

Le repli à l'observation $t$ est la distance depuis la valeur la plus haute atteinte jusqu'ici :

$$
DD_t = \frac{V_t - \max_{\tau \leq t} V_\tau}{\max_{\tau \leq t} V_\tau} \leq 0
$$

L'indice d'Ulcer est la **moyenne quadratique** de cette série sur les $T$ observations :

$$
UI = \sqrt{\frac{1}{T} \sum_{t=1}^{T} DD_t^{2}}
$$

Trois propriétés découlent directement de cette expression, avant même qu'une quelconque interprétation y soit ajoutée :

- Il est **positif**. C'est une dispersion construite à partir d'une racine carrée, et une racine carrée ne peut pas renvoyer un nombre négatif. C'est le seul membre de la famille des replis qui n'est pas rapporté comme une baisse.
- **Chaque observation compte**, y compris celles qui se situent exactement à un sommet. Celles-ci contribuent $0$ à la somme mais occupent tout de même une place dans le diviseur, ce qui fait qu'une longue période calme tire la valeur vers le bas.
- **L'élévation au carré n'est pas neutre.** Un repli deux fois plus profond contribue quatre fois plus, de sorte que la mesure est dominée par les périodes profondes plutôt que par celles qui sont simplement sous le sommet.

---

## 📐 Le diviseur qui ressemble à la correction de Bessel {: #the-divisor }

C'est le détail qui fait trébucher quiconque recalcule la valeur à la main, et il vaut la peine d'être énoncé précisément car l'erreur qu'il produit est suffisamment petite pour survivre à une vérification rapide.

!!! info "La série comporte un point de plus que l'historique"

    Une série de replis est dérivée d'un indice de richesse qui commence à une base unitaire, elle contient donc $T + 1$ points : les $T$ points observés, plus cette base. Le repli de la base est **toujours exactement zéro** — un point de départ ne peut pas être sous un sommet qu'il n'a pas encore quitté.

    L'implémentation de référence standard divise la somme des carrés par $n - 1$, où le compteur $n$ parcourt toute la série et **inclut** donc cette base. Comme $n = T + 1$ :

    $$
    \frac{1}{n - 1} = \frac{1}{(T + 1) - 1} = \frac{1}{T}
    $$

    Le $-1$ annule le point fantôme, il n'applique pas une correction d'échantillon.

!!! warning "Le lire comme un écart-type d'échantillon surestime le résultat"

    La base contribue $0$ à la somme des carrés et $+1$ au comptage, et ces deux contributions s'annulent exactement — c'est pourquoi l'expression se réduit à une véritable moyenne sur les $T$ observations réelles. Prendre le $n - 1$ pour la correction de Bessel et diviser par $T - 1$ à la place gonfle la valeur de

    $$
    \sqrt{\frac{T}{T - 1}}
    $$

    À $T = 750$, cela représente **+0,0667 %** : bien trop petit pour paraître faux, et pourtant faux. L'indice d'Ulcer est une moyenne quadratique, pas un écart-type d'échantillon, et il n'a aucune moyenne à estimer.

---

## 🆚 Face à la perte maximale {: #against-the-maximum-drawdown }

[Perte maximale](max-drawdown.md) indique le pire moment. L'indice d'Ulcer indique quelle part du temps a été passée sous le sommet, et à quelle profondeur. Ils sont construits à partir de la même série et classent les portefeuilles différemment, ce qui est précisément la raison de publier les deux.

| Deux historiques avec la **même** perte maximale | Indice d'Ulcer |
|---|---|
| Une chute brutale, récupérée en quelques jours | **petit** — les observations profondes sont peu nombreuses, et le reste se situe à un sommet |
| Une lente érosion qui reste sous le sommet pendant des mois | **grand** — la plupart des observations sont sous le sommet, et chacune compte |

La relation entre les deux n'est pas seulement qualitative. Puisque $DD_t^{2} \leq MDD^{2}$ pour tout $t$, la moyenne des carrés ne peut pas dépasser la plus grande d'entre elles :

$$
UI \leq |MDD|
$$

L'égalité nécessiterait que le portefeuille reste à son point le plus profond pendant toute la fenêtre. Le ratio $UI / |MDD|$ se lit donc comme **la part de l'historique qui a ressemblé au pire de celui-ci** — proche de $0$ pour un pic isolé dans un parcours par ailleurs sans encombre, s'approchant de $1$ pour un portefeuille qui a baissé et y est resté.

---

## 💡 Interprétation {: #interpretation }

Lisez la valeur comme une profondeur *typique* plutôt qu'une profondeur extrême — pondérée par la durée, et exprimée dans les mêmes unités que les replis à partir desquels elle est construite.

- **Zéro signifie jamais sous un sommet.** Un portefeuille qui n'a jamais fait que de nouveaux sommets n'a pas vraiment de série de replis, et l'indice se réduit à $0$. Tout historique contenant un déclin produit une valeur strictement positive.
- **Plus bas, c'est mieux**, ce qui inverse l'habitude de lecture du reste de la famille des replis. Ici, un nombre plus grand correspond à une expérience pire, sans signe moins pour le signaler.
- **Il lit la séquence, pas la distribution.** Réorganiser les rendements observés laisse la [valeur à risque](value-at-risk.md) et la [VaR conditionnelle](conditional-value-at-risk.md) inchangées, mais reconstruit entièrement la série de replis et peut déplacer considérablement cette valeur. Il appartient à la moitié dépendante du chemin de cette section, aux côtés de la [Perte maximale](max-drawdown.md) et du [Repli actuel](current-drawdown.md).

---

## ⚠️ Limitations {: #limitations }

!!! warning "Une fenêtre calme plus longue l'abaisse"

    Le diviseur est le nombre d'observations, donc prolonger un historique par des périodes passées à un sommet ajoute des zéros au numérateur et des places au dénominateur. La valeur diminue sans que rien n'ait changé dans les mauvais épisodes du portefeuille. Deux indices d'Ulcer ne sont comparables que lorsqu'ils ont été calculés sur des fenêtres de longueur et de fréquence d'observation comparables.

!!! warning "Ce n'est pas la fraction du temps passée sous le sommet"

    L'élévation au carré accorde un poids disproportionné aux périodes profondes, de sorte que l'indice n'est pas une statistique de durée portant un signe de pourcentage. Un portefeuille ayant passé la moitié de la fenêtre à $2\%$ sous son sommet et un autre y ayant passé un huitième à $4\%$ sous celui-ci obtiennent un score identique, et aucune des deux valeurs ne vous dit quelle forme les a produits.

!!! warning "Il ne porte aucune date"

    La mesure résume toute la fenêtre en un seul nombre et ne dit rien sur **quand** les périodes sous le sommet se sont produites, ni si le portefeuille est actuellement sous le sommet. Le [Repli actuel](current-drawdown.md) répond à la seconde question et la [Perte maximale](max-drawdown.md) date la première.

---

## 🔗 Voir aussi {: #related }

- 📉 **[Perte maximale](max-drawdown.md)** — le pire moment, face auquel cette mesure évalue toute l'étendue
- 📍 **[Repli actuel](current-drawdown.md)** — où en est le portefeuille par rapport à son sommet aujourd'hui
- 📉 **[Repli à risque](drawdown-at-risk.md)** — un quantile de la même série de replis, plutôt que sa moyenne quadratique
- 🌊 **[Repli à risque conditionnel](conditional-drawdown-at-risk.md)** — la sévérité de la queue de repli au-delà de ce quantile
- 📊 **[Volatilité](volatility.md)** — dispersion des rendements, qui n'a aucune mémoire du sommet
- 🧪 **[Qualité des données](data-quality.md)** — la fenêtre et le nombre d'observations sur lesquels la série a été construite
