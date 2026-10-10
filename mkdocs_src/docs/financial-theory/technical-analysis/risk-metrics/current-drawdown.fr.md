# 📍 Repli actuel

Le repli actuel mesure de combien un portefeuille se situe **actuellement** sous son propre pic historique, par opposition à la pire chute qu'il ait jamais subie. La [Perte maximale](max-drawdown.md) rapporte un fait sur le passé ; cet indicateur-ci rapporte une position dans le présent, et c'est celui qui change à chaque nouvelle observation.

---

## 🔢 Formule {: #formula }

Les deux mesures de repli sont lues à partir de la même série sous le sommet. Un indice de richesse est construit à partir des rendements analysés, un sommet glissant est reporté, et le repli à chaque point est la distance entre les deux :

$$
DD_t = \frac{W_t}{\displaystyle\max_{\tau \le t} W_\tau} - 1
$$

Le repli actuel est la valeur de cette série à la **dernière** observation, jamais supérieure à zéro :

$$
DD_{current} = \min\left(0,\; DD_{last}\right)
$$

À un nouveau plus haut historique, la dernière valeur de richesse *est* le sommet glissant, donc le ratio vaut $1$ et le repli est exactement $0$.

!!! info "La position sous le sommet est décidée avec une tolérance"

    Un portefeuille n'est considéré comme sous le sommet que lorsque le repli actuel est négatif **au-delà d'une tolérance numérique**, et non à chaque fraction de cent sous le sommet. La tolérance existe pour absorber le bruit en virgule flottante, afin qu'une valeur indiscernable du sommet soit traitée comme étant au sommet. C'est une protection contre les artefacts arithmétiques, et non un seuil visible par l'utilisateur en dessous duquel une baisse cesse de compter.

---

## 📅 Ce qui est publié {: #what-is-published }

Quatre quantités décrivent la position actuelle. Leur comportement lorsque le portefeuille n'est **pas** sous le sommet fait partie du contrat, et non d'un accident.

| Quantité | Signification | À un plus haut historique |
|---|---|---|
| Repli actuel | Distance sous le sommet glissant, en ratio décimal, jamais positive | Exactement $0$ |
| Date du pic actuel | La date du sommet **glissant** à partir duquel le repli est mesuré | La date de la dernière observation |
| Durée du repli actuel | Jours calendaires écoulés **depuis ce sommet** | Exactement $0$ |
| Restant pour revenir au sommet | Le gain encore nécessaire, sur la valeur actuelle, pour revenir au sommet | Exactement $0$ |

Deux d'entre elles méritent une lecture attentive.

**La durée est comptée depuis le sommet, et non depuis le point bas.** C'est la même convention que celle utilisée par la perte maximale pour sa durée : le chronomètre démarre lorsque le portefeuille quitte son plus haut historique, et non lorsqu'il cesse de chuter. La baisse n'est pas un prélude à la perte — elle est la perte en train de se produire —, si bien que le décompte couvre toute la période passée sous le sommet. Voir [Temps de récupération](max-drawdown.md#recovery-time) pour le même raisonnement appliqué au pire épisode.

**La date du pic actuel n'est pas celle du pic du pire épisode.** C'est le plus haut historique le plus récent, que le sommet glissant déplace chaque fois que le portefeuille en établit un nouveau. Un portefeuille à son plus haut historique rapporte donc la date du jour et un repli de durée nulle ; le sommet qui a précédé la chute historique la plus profonde appartient à la [Perte maximale](max-drawdown.md) et est publié séparément.

---

## 🧗 Ce qu'il faut pour revenir au sommet {: #what-it-takes-to-get-back }

Le gain nécessaire pour revenir au sommet n'est pas l'image miroir de la chute, car le gain s'applique à une base plus petite. Exprimé à partir du repli actuel $DD$ :

$$
\text{Gain requis} = \frac{1}{1 + DD} - 1 = \frac{-DD}{1 + DD}
$$

Les deux formes sont la même expression — la seconde est la première avec la fraction combinée — et la [Perte maximale](max-drawdown.md) explique l'asymétrie que cela crée, avec les valeurs calculées.

!!! warning "La même formule, appliquée à une question différente"

    Cette asymétrie est une leçon générale, et elle est enseignée sur la page de la perte maximale. La quantité calculée ici l'applique au **repli actuel** à la place, et la différence n'est pas cosmétique :

    - appliquée à la **perte maximale**, c'est un énoncé historique — *combien il aurait fallu pour récupérer, au pire point jamais atteint* ;
    - appliquée au **repli actuel**, c'est un énoncé présent — *combien il faut pour récupérer depuis la position où se trouve aujourd'hui le portefeuille*.

    Seul le second peut être mis à profit. Un portefeuille qui a chuté fortement il y a des années et qui s'est depuis rétabli affiche simultanément une perte maximale élevée et un indicateur actuel proche de zéro : ce ne sont pas deux nombres en désaccord, ce sont les réponses à deux questions différentes, et les deux sont vraies.

---

## 💡 Interprétation {: #interpretation }

Le repli actuel répond à la question *où en suis-je, par rapport à mon propre meilleur résultat ?* — une question à laquelle aucune mesure de rendement ne répond, car un rendement mesure un trajet entre deux dates choisies, tandis que celui-ci mesure une distance à un sommet que le portefeuille a lui-même établi.

Lus ensemble, les quatre quantités décrivent une position plutôt qu'un score : **de combien** sous le sommet, **depuis quand**, et **combien** manque encore. La durée est souvent la plus révélatrice des deux : une baisse modeste qui perdure longtemps est une expérience différente d'une baisse plus profonde entamée la semaine dernière, et la profondeur seule ne permet pas de les distinguer. C'est cette combinaison de profondeur et de persistance que l'[Indice d'Ulcer](ulcer-index.md) entreprend de résumer en un seul nombre.

Parce qu'il est mesuré par rapport au sommet glissant, l'indicateur présente une asymétrie qui lui est propre : il s'améliore à mesure que le portefeuille progresse et se réinitialise à zéro dès qu'un nouveau sommet est établi, même si ce nouveau sommet n'est dépassé que de très peu.

---

## ⚠️ Limitations {: #limitations }

!!! warning "C'est une position, pas une prévision"

    Le repli actuel indique à quelle distance le portefeuille se situe sous le sommet, et rien sur ce qui va se produire ensuite. Il n'indique pas si la baisse se termine, se poursuit ou est sur le point de s'aggraver, et le gain restant à réaliser pour revenir au sommet est arithmétique — le gain nécessaire pour combler l'écart — et non l'anticipation que ce gain se matérialisera.

!!! warning "Un nouveau sommet efface la mémoire"

    Le sommet glissant ne se déplace que vers le haut, si bien que dépasser le précédent plus haut, quelle qu'en soit la marge, réinitialise le repli actuel à zéro et redémarre la durée à partir de cette date. La chute qui l'a précédé ne disparaît pas de l'analyse, mais elle cesse d'être décrite par *cet* indicateur : elle appartient à la perte maximale et à l'historique des épisodes.

!!! warning "Il hérite de la série sur laquelle il a été calculé"

    La série sous le sommet est construite à partir des mêmes rendements que le reste de l'analyse, sur la même fenêtre d'observation. Une fenêtre plus courte ne peut contenir que les sommets qu'elle a vus : un portefeuille analysé sur une fenêtre récente peut apparaître proche de son sommet simplement parce que le sommet plus élevé se situe avant la date de début. Chaque résultat publie la fenêtre utilisée, son nombre d'observations et la base sur laquelle les rendements ont été calculés. Voir [Qualité des données](data-quality.md).

---

## 🔗 Voir aussi {: #related }

- 📉 **[Perte maximale](max-drawdown.md)** — la pire chute de l'historique, sa durée et son état de récupération
- 🩹 **[Indice d'Ulcer](ulcer-index.md)** — profondeur et persistance combinées en un seul indicateur
- 📊 **[Volatilité](volatility.md)** — l'ampleur des fluctuations du portefeuille, indépendamment de tout sommet
- 🧪 **[Qualité des données](data-quality.md)** — la fenêtre et les observations à partir desquelles le repli a été lu
