# 📐 Bêta et rendement actif

Le bêta mesure la force avec laquelle un portefeuille tend à suivre son indice de référence, tandis que le rendement actif isole la part du résultat que l’indice de référence n’explique pas. Les deux sont des chiffres **relatifs** : ils ne décrivent un portefeuille qu’en relation avec la série à laquelle il a été comparé, et ils changent lorsque cette série change.

---

## 🔢 Formule {: #formula }

Quatre quantités sont calculées à partir des deux séries de rendements alignées — le portefeuille, $p$, et la série de comparaison, $b$.

**Le bêta** est la covariance d’échantillon des deux séries divisée par la variance de la comparaison :

$$
\beta = \frac{\mathrm{Cov}(r_p, r_b)}{\mathrm{Var}(r_b)}
$$

Les deux moments utilisent les estimateurs non biaisés $(N-1)$, donc au moins deux observations communes sont nécessaires.

**Le rendement actif** est la différence entre les deux rendements composés sur l’ensemble de la fenêtre :

$$
AR = \left[\prod_{t=1}^{N} (1 + r_{p,t}) - 1\right] - \left[\prod_{t=1}^{N} (1 + r_{b,t}) - 1\right]
$$

**L’erreur de suivi** est la dispersion de la différence par période $a_t = r_{p,t} - r_{b,t}$, annualisée avec le facteur mesuré :

$$
TE = \sigma_a \times \sqrt{f}
$$

**Le ratio d’information** relie la moyenne de cette différence à sa dispersion, annualisée sur la même base :

$$
IR = \frac{\bar{a}}{\sigma_a} \times \sqrt{f}
$$

Le facteur $f$ est le même facteur d’annualisation observé que celui utilisé partout ailleurs dans l’analyse — compté à partir des données plutôt que supposé. Voir [Annualisation observée](observed-annualization.md).

!!! info "Les deux séries doivent être alignées"

    Les deux séries étant comparées point par point, elles doivent donc couvrir les mêmes observations : une comparaison n’est calculée que lorsque les deux séries ont la même longueur et au moins deux observations. L’alignement est effectué avant que les métriques ne soient calculées, c’est pourquoi un résultat qui a utilisé une fenêtre raccourcie l’indique par son nombre d’observations plutôt que par une comparaison silencieusement décalée.

---

## 🚫 Quand le bêta n’a pas de valeur {: #when-beta-has-no-value }

Le bêta n’est pas toujours défini, et lorsqu’il ne l’est pas, aucun nombre n’est publié.

**Une série de comparaison de variance nulle ne produit pas de bêta.** Le bêta exprime la manière dont le portefeuille réagit aux mouvements de la série de comparaison ; une série qui ne bouge pas n’offre rien à quoi réagir. Mathématiquement, le dénominateur s’annule, et toute valeur renvoyée à sa place serait un artefact de l’arithmétique plutôt qu’une mesure. Le résultat signale plutôt l’absence.

La même discipline s’applique au ratio d’information : si la différence par période entre les deux séries ne varie jamais, sa dispersion est nulle, et le ratio est laissé non publié plutôt que d’être forcé.

!!! info "Une valeur absente est un résultat"

    Un bêta manquant n’est pas un échec du calcul — c’est ce que les données permettent d’affirmer. L’interpréter comme « aucune relation » serait une conclusion erronée : cela signifie que la série de comparaison n’a fourni aucune variation permettant de mesurer la moindre relation.

---

## ➗ Le rendement actif est une différence de rendements composés {: #active-return-is-a-difference-of-compounded-returns }

L’ordre des opérations compte, et c’est la source de la mauvaise interprétation la plus courante de ce nombre. Le rendement actif compose chaque série sur la fenêtre **d’abord**, puis soustrait **ensuite**. Ce n’est pas la composition des différences par période.

Trois conséquences en découlent.

**Il ne s’additionne pas dans le temps.** Le rendement actif d’une année n’est pas la somme — ni la composition — des rendements actifs de ses mois. Chaque chiffre appartient à la fenêtre sur laquelle il a été calculé, et les fenêtres ne peuvent pas être enchaînées.

**Ce n’est pas le rendement d’une stratégie.** Ce n’est pas ce qu’un investisseur aurait gagné en détenant le portefeuille et en vendant à découvert l’indice de référence : cette position composerait la différence, et porterait aussi des effets de financement et de rééquilibrage qu’aucune soustraction de deux rendements composés ne peut représenter.

**Il ne se décompose pas en compétence.** Le rendement actif indique que le portefeuille a terminé la fenêtre devant ou derrière sa comparaison, de ce montant. Il n’attribue rien : l’écart peut provenir d’expositions différentes, d’un timing différent, ou d’une comparaison qui n’a jamais été un étalon approprié au départ.

---

## 💡 Interprétation {: #interpretation }

**Le bêta** décrit une sensibilité, pas une qualité. Un bêta de $1$ signifie que le portefeuille a eu tendance à évoluer dans les mêmes proportions que la série de comparaison ; en dessous de $1$, il a moins évolué que la série, au-dessus de $1$, davantage. Le signe compte plus que tout seuil : un bêta négatif signifie que le portefeuille a eu tendance à évoluer dans la direction opposée.

Il est utile de distinguer le bêta de la corrélation, car ils sont facilement confondus. D’après les définitions ci-dessus, $\beta = \rho_{p,b} \times \dfrac{\sigma_p}{\sigma_b}$ : la corrélation ne capture que la *direction* de la relation, tandis que le bêta porte aussi le rapport des deux volatilités. Un portefeuille peut suivre étroitement sa comparaison et avoir malgré tout un bêta éloigné de $1$ simplement parce qu’il fluctue plus, ou moins, que la série qu’il suit. Voir [Corrélation](correlation.md).

**Le rendement actif** est la distance entre les deux lignes d’arrivée, mesurée sur la fenêtre.

**L’erreur de suivi** indique avec quelle régularité cette distance a été parcourue. C’est la volatilité de la différence, donc une valeur élevée indique que le portefeuille s’est écarté de sa comparaison fréquemment ou violemment — dans un sens ou dans l’autre, puisqu’il s’agit d’une dispersion et qu’elle ne porte aucun signe.

**Le ratio d’information** réunit les deux : il exprime la différence moyenne par période en unités de sa propre dispersion, annualisée. Un ratio plus élevé signifie que la différence était plus régulière par rapport à l’ampleur de ses variations ; un ratio proche de zéro signifie que la différence, quel que soit son signe, est faible comparée à la variation qui l’entoure. Aucune valeur n’est bonne ou mauvaise en soi — le chiffre dépend de la longueur de la fenêtre et de la comparaison choisie, et le même nombre mesuré sur une fenêtre différente ne constitue pas la même affirmation.

---

## ⚠️ Limites {: #limitations }

!!! warning "Chaque chiffre ici hérite de son indice de référence"

    Le bêta, le rendement actif, l’erreur de suivi et le ratio d’information sont tous mesurés *par rapport à* une série de comparaison. Changez la série et chacun d’eux change, sans que rien n’ait changé dans le portefeuille. Un chiffre relatif cité sans préciser par rapport à quoi il a été mesuré est incomplet. Voir [Sélection de l’indice de référence](benchmark-selection.md).

!!! warning "Le bêta voit une ligne droite, sur une seule fenêtre"

    Le bêta est la pente d’une relation linéaire estimée sur la période observée. Un portefeuille dont le comportement diffère entre des conditions calmes et tendues est résumé par une pente unique qui ne décrit ni l’un ni l’autre. Et parce qu’il est estimé, une fenêtre courte produit un chiffre qui reflète la séquence particulière qu’elle contenait par hasard.

!!! warning "La sensibilité n’est pas une explication"

    Un bêta proche de $1$ indique que le portefeuille a évolué avec la série de comparaison ; il ne dit pas que la série entraîne le portefeuille, ni que le reste relève de la compétence. Deux séries peuvent évoluer ensemble sous l’effet d’une cause commune sans lien entre elles — la même prudence que celle qui s’applique à la corrélation vaut ici, avec en plus le rapport des volatilités.

---

## 🔗 Voir aussi {: #related }

- 🎯 **[Sélection de l’indice de référence](benchmark-selection.md)** — le choix dont hérite chaque chiffre de cette page
- 🔗 **[Corrélation](correlation.md)** — direction de la relation, avec le rapport des volatilités retiré
- 📊 **[Volatilité](volatility.md)** — la dispersion qui transforme une corrélation en bêta
- 📏 **[Annualisation observée](observed-annualization.md)** — le facteur mesuré utilisé pour annualiser l’erreur de suivi et le ratio d’information
