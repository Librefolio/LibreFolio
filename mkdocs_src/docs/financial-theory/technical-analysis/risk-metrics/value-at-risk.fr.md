# 📉 Valeur à risque

La valeur à risque répond à une question délibérément étroite : sur un horizon donné et à un niveau de confiance choisi, quelle est la perte qui ne devrait pas être dépassée ?

L'étroitesse est le but, et c'est aussi le piège. La VaR marque **où commence la queue** — c'est un seuil, pas un maximum, et elle reste silencieuse sur tout ce qui le dépasse.

---

## 🔢 Formule {: #formula }

Au niveau de confiance $c$, la valeur à risque est le quantile de la distribution des pertes :

$$
VaR_c = \inf\left\{\, \ell : P(L \le \ell) \ge c \,\right\}
$$

En pratique, il s'agit d'un exercice de tri : les pertes observées sur la fenêtre analysée sont triées, et la valeur est lue à la position que le niveau de confiance indique.

Le résultat est un **énoncé de fréquence**. À 95 %, il dit que dans 19 périodes sur 20, la perte n'est pas pire que la valeur rapportée — et que dans la période restante, elle est pire, d'un montant que cette mesure ne précise pas.

---

## 📜 Mesuré, pas modélisé {: #measured-not-modelled }

La valeur à risque de LibreFolio est **historique** : c'est le quantile empirique des pertes que le portefeuille a réellement subies. Aucune distribution supposée n'entre en jeu.

C'est un choix délibéré contre l'alternative la plus courante, dans laquelle les rendements sont supposés suivre une distribution normale et le quantile est lu sur cette courbe.

!!! warning "L'hypothèse gaussienne échoue exactement quand le chiffre compte"

    Les rendements réels des marchés ont des **queues plus épaisses** qu'une distribution normale : les mouvements extrêmes se produisent plus souvent, et sont plus amples, que ne le permet la courbe en cloche. Une VaR gaussienne paramétrique promet donc que les pires journées sont plus rares qu'elles ne le sont — et elle fait cette promesse avec d'autant plus d'assurance aux niveaux de confiance élevés, qui sont précisément ceux utilisés pour penser les crises.

    C'est une mesure de risque rassurante à proportion de son degré d'erreur. L'approche empirique ne peut pas commettre cette erreur, car elle ne revendique aucune forme : elle compte ce qui s'est produit.

L'avantage se mérite, il n'est pas gratuit, et le prix figure sur la même page que le bénéfice :

!!! warning "Elle ne peut pas vous montrer une perte que vous n'avez jamais vécue"

    Un quantile empirique est borné par l'échantillon dont il est issu. Un historique court, ou calme, produit une valeur à risque calme — non parce que le portefeuille est sûr, mais parce que rien de pire n'a encore été observé. La mesure décrit la fenêtre qui lui a été donnée, et une fenêtre qui ne contient aucune crise ne contient aucune perte de taille de crise.

---

## 💡 Interprétation {: #interpretation }

Lisez le chiffre comme *à quelle fréquence*, jamais comme *combien au pire* :

- **C'est un seuil, pas une borne.** Les pertes au-delà ne sont pas exclues — par construction, elles sont censées se produire au taux indiqué.
- **Elle ne dit rien sur la profondeur au-delà.** Deux portefeuilles peuvent afficher la même VaR alors que l'un la dépasse modestement et l'autre de manière catastrophique. Cette différence est ce à quoi sert la [VaR conditionnelle](conditional-value-at-risk.md), et c'est la raison pour laquelle cette section commence par ce chiffre-là plutôt que par celui-ci.
- **C'est un taux, pas un calendrier.** « Une période sur vingt » ne signifie pas une mauvaise période tous les vingt. Les mauvaises périodes arrivent par grappes, et un quantile n'a aucune mémoire de l'ordre.

Cette dernière propriété mérite d'être énoncée précisément, car elle sépare cette mesure de la moitié de la section : **mélangez l'ordre des rendements observés et la valeur à risque ne bouge pas du tout.** Elle lit la distribution, pas la séquence. Les chiffres qui lisent la séquence — [perte maximale](max-drawdown.md) et [repli actuel](current-drawdown.md) — peuvent changer complètement sous le même mélange. Aucune des deux vues n'est complète seule, c'est pourquoi les deux sont publiées.

L'observation unique la moins favorable de la fenêtre est rapportée comme un chiffre à part, la [pire réalisation](worst-realization.md) : là où la valeur à risque dit *une période sur vingt fait pire que ceci*, celle-ci dit *et le pire a été ceci, à cette date*.

---

## 🔄 Ce que la correction de l'estimateur de queue change ici {: #what-the-correction-changes }

La moyenne de queue utilisée par la [VaR conditionnelle](conditional-value-at-risk.md) a été corrigée, et la question naturelle est de savoir si le chiffre de la valeur à risque change avec elle.

Il change pour certaines configurations et pas pour d'autres, et la frontière entre les deux est exacte. Le côté où tombe un chiffre donné est décidé par l'arithmétique, non par l'inspection, de sorte qu'il peut être vérifié plutôt que supposé.

!!! info "La condition, en entier"

    La valeur à risque rapportée change **exactement lorsque $(1-c) \cdot T$ est un nombre entier**, où $c$ est le niveau de confiance et $T$ le nombre d'observations entrant dans le calcul de la queue.

    Lorsque ce produit n'est pas un nombre entier, les deux conventions sélectionnent la même observation et le chiffre n'est pas simplement proche mais identique.

### 🎚️ Pourquoi le changement est tout ou rien {: #why-the-change-is-all-or-nothing }

Une étude de mesure sur 24 combinaisons de niveau de confiance et de longueur d'historique, 300 échantillons chacune — 7 200 essais — a montré que chaque combinaison était de celles où **soit tous les échantillons changeaient, soit aucun**. Aucune combinaison n'a produit de proportion intermédiaire.

Cela découle de ce qu'est le chiffre. La valeur à risque ici est une **statistique d'ordre** : le calcul trie les pertes observées et lit celle à la position que le niveau de confiance indique, de sorte que le nombre rapporté est toujours une perte que le portefeuille a réellement subie. C'est une fonction en escalier d'un indice, pas une fonction continue des données.

Lorsque la condition ci-dessus est remplie, l'indice se décale d'une position — et un indice qui se décale ne se décale pas un peu. Il sélectionne une **observation différente**. Le chiffre saute donc d'une statistique d'ordre entière, et le plus grand saut de ce type mesuré était de **+4,587 %**. Entre des nombres entiers, les deux conventions arrondissent au même indice et la sortie est identique bit à bit.

!!! info "Là où le chiffre change, il change à la hausse"

    Ce chiffre et la [VaR conditionnelle](conditional-value-at-risk.md) vont tous deux dans la même direction : à la hausse. Aucune configuration n'a été trouvée dans laquelle l'un ou l'autre nombre évoluait vers une lecture plus optimiste. Là où une valeur à risque a changé, le risque précédemment rapporté était **trop faible**.

### 📅 Quels historiques sont affectés {: #which-histories-are-affected }

$(1-c) \cdot T$ est un nombre entier lorsque $T$ est divisible par 10 au niveau de confiance 90 %, par 20 à 95 %, et par 100 à 99 % :

| Observations $T$ | 90 % | 95 % | 99 % |
|---|---|---|---|
| 250 | change | — | — |
| 500 | change | change | change |
| 750 | change | — | — |
| 1000 | change | change | change |
| 1003 | — | — | — |
| 2000 | change | change | change |

Le motif de ce tableau mérite d'être nommé, car c'est l'opposé d'un cas limite rare : **les historiques affectés sont les historiques bien rangés**. Un an, deux ans, trois ans, mille jours — les nombres ronds sont précisément les nombres divisibles, et les nombres ronds sont ce qu'une interface vous invite à saisir. Un historique de 1 003 observations, en revanche, n'est affecté à aucun niveau de confiance.

C'est le fait qui répond à la question que la correction soulève habituellement — **pourquoi une analyse a changé et pas celle d'un collègue**. Deux analyses du même portefeuille au même niveau de confiance peuvent diverger sur le point de savoir si quelque chose s'est produit, parce que l'une a été exécutée sur une fenêtre ronde et l'autre non. Ni l'une ni l'autre n'est fausse, et la différence entre elles n'est pas une question de degré : c'est la divisibilité d'un seul entier.

### ⏳ Le nombre d'observations n'est pas la longueur de l'historique {: #the-observation-count-is-not-the-history-length }

$T$ n'est pas le nombre de jours dans la fenêtre. La queue est calculée à partir de rendements **composés sur l'horizon** — chaque suite de $n$ rendements consécutifs composée en un seul — de sorte que le nombre de valeurs entrant dans le calcul est

$$
T = N - n + 1
$$

où $N$ est le nombre de rendements dans la fenêtre et $n$ est l'horizon compté en observations. Le paramètre **Horizon (jours)** $h$ est en **jours calendaires**, et il est converti en observations au rythme auquel la série a réellement été observée — son [facteur d'annualisation observé](observed-annualization.md) $f$ :

$$
n = \max\left(1,\ \operatorname{round}\left(\frac{h \cdot f}{365}\right)\right)
$$

Un horizon couvre donc la même étendue de calendrier sur chaque série, à l'observation près. Trente jours — le mauvais mois que l'application rapporte à côté du mauvais jour — sont $n = 21$ observations d'une série cotée en jours de bourse ($f \approx 252$) et $n = 30$ d'une série cotée chaque jour calendaire ($f = 365$).

L'analyse calcule exactement ces quantités et publie les deux avec le résultat : $n$ comme son horizon en observations, $T$ comme son nombre d'observations. Ce nombre publié, et non la longueur de la fenêtre, est le $T$ auquel la règle s'applique. C'est aussi le nombre par rapport auquel le minimum de 20 observations est vérifié : avec moins de 20 fenêtres composées, le chiffre n'est pas calculé, et le résultat revient indisponible pour historique insuffisant. Un mauvais mois nécessite donc $N \ge 40$ rendements à $f \approx 252$, où $n = 21$, et $N \ge 49$ à $f = 365$.

L'horizon est un champ de formulaire de l'analyse, avec $h = 1$ par défaut et acceptant des valeurs de 1 à 365. Par défaut, $n = 1$ sur chaque série — aucune n'est observée plus d'une fois par jour calendaire, donc $f \le 365$ — et $T = N$, c'est pourquoi les historiques ronds sont ceux qui sont affectés.

Augmentez-le et le tableau ci-dessus s'inverse. À $h = 10$, une série cotée en jours de bourse compose $n = 7$ observations, donc un $N$ rond donne $T = N - 6$, un nombre se terminant par 4 ; une série cotée chaque jour calendaire compose $n = 10$, et $T = N - 9$ se termine par 1. Ni l'un ni l'autre n'est jamais divisible par 10, 20 ou 100, et il en va de même pour toute série observée au moins 54,75 fois par an ($f \ge 54.75$) : dix jours contiennent alors entre 2 et 10 observations, donc un $N$ rond en perd entre 1 et 9. Sur les mêmes longueurs d'historique, à $h = 10$, **250, 500, 750, 1000, 1250 et 2000 observations ne sont affectées à aucun des trois niveaux de confiance**, sur l'un ou l'autre type de série. L'horizon par défaut de 1 est précisément le réglage sous lequel les historiques bien rangés changent ; un horizon de 10 laisse ces mêmes historiques intacts — sauf sur une série observée moins souvent, comme un fonds hebdomadaire ($f \approx 52$), où dix jours arrondissent encore à une seule observation et $T = N$. C'est une conséquence de l'arithmétique plutôt qu'un défaut de celle-ci, mais cela signifie qu'une comparaison entre deux analyses doit faire correspondre l'horizon ainsi que la fenêtre et le niveau — et, puisque le même horizon contient un $n$ différent à un $f$ différent, la fréquence observée de la série également.

!!! info "Comment vérifier un cas particulier"

    Prenez le nombre d'observations que la valeur à risque publie avec ses chiffres — `observations`, déjà net de l'horizon et publié à côté de `horizon_observations` — et multipliez-le par $1 - c$. Un nombre entier signifie que le chiffre a changé, d'une observation ; toute autre valeur signifie qu'il est inchangé. Le nombre d'observations dans les métadonnées du résultat (`n_observations`, voir [Qualité des données](data-quality.md)) est $N$, compté avant composition : il est égal à $T$ seulement lorsque $n = 1$.

---

## ⚠️ Limites {: #limitations }

!!! warning "Silencieuse au-delà du seuil"

    La mesure s'arrête à la frontière de la queue. Que les pertes au-delà soient légèrement pires ou plusieurs fois pires est une information qu'elle ne porte pas, et aucun niveau de confiance ne la récupère. Utilisez la [VaR conditionnelle](conditional-value-at-risk.md) pour la profondeur.

!!! warning "Le niveau de confiance change la question, pas la précision"

    Passer de 95 % à 99 % ne produit pas une réponse plus précise ; cela pose une question sur un événement plus rare. Cela pose aussi une question sur un événement estimé à partir de moins d'observations, de sorte que le niveau plus élevé est lu dans une tranche plus fine du même historique.

!!! warning "Elle hérite de sa fenêtre"

    Le chiffre est calculé à partir des rendements de la période analysée, sur le calendrier d'observation que ces séries partagent. La fenêtre, le nombre d'observations et la base utilisée sont publiés avec le résultat — voir [Qualité des données](data-quality.md).

---

## 🔗 Voir aussi {: #related }

- 🌊 **[VaR conditionnelle](conditional-value-at-risk.md)** — jusqu'où va la queue une fois le seuil franchi
- 📉 **[perte maximale](max-drawdown.md)** — la pire chute le long du parcours, qu'un quantile ne peut pas voir
- 📊 **[Volatilité](volatility.md)** — la dispersion dans son ensemble, plutôt qu'un point de la distribution
- ⏮️ **[Rejeu historique](historical-replay.md)** — un épisode spécifique au lieu d'une statistique résumée
- 🔻 **[pire réalisation](worst-realization.md)** — l'observation unique la plus profonde, comme un fait daté plutôt qu'un taux
- 🧪 **[Qualité des données](data-quality.md)** — la fenêtre et les observations à partir desquelles le quantile a été lu
