# 📅 Annualisation observée

Annualiser un indicateur de risque nécessite de savoir combien de périodes contient une année, et ce nombre peut être mesuré à partir des données observées plutôt que supposé à l'avance. LibreFolio le mesure : le facteur utilisé pour mettre à l'échelle une valeur par période vers une valeur annuelle est **compté à partir de la série réellement analysée**, jamais repris d'une convention de marché fixée au préalable.

---

## 🔢 Formule {: #formula }

Deux quantités sont lues sur la série avant qu'une valeur ne soit annualisée — l'étendue calendaire qu'elle couvre, et le nombre de rendements observés à l'intérieur de cette étendue :

$$
D = d_{last} - d_{baseline}
$$

$$
f = \frac{N \times 365}{D}
$$

où :

- $N$ = nombre de rendements de période réellement utilisés
- $d_{baseline}$ = date de la première valorisation (elle ouvre la série et ne produit donc aucun rendement qui lui soit propre)
- $d_{last}$ = date du dernier rendement
- $D$ = jours calendaires couverts, week-ends et fermetures inclus

Le facteur $f$ est ensuite appliqué partout où une valeur par période doit être exprimée sur une base annuelle. Pour la volatilité :

$$
\sigma_{annual} = \sigma_{period} \times \sqrt{f}
$$

!!! info "C'est un comptage, pas une convention"

    $f$ a une lecture littérale : **observations par an, comptées**. Une série avec $N$ rendements répartis sur $D$ jours calendaires a été observée à un rythme de $N/D$ par jour, donc $365N/D$ par an. Aucune hypothèse n'est faite sur l'instrument, son calendrier de marché ou sa classe d'actifs — le rythme est ce que les données révèlent. La seule connaissance calendaire impliquée décide ce qui compte comme une observation, jamais combien il devrait y en avoir : un prix stocké qui ne fait que répéter la clôture précédente un week-end ou un jour férié boursier est un report, pas une cotation (voir [ci-dessous](#252-is-recovered-not-imposed)).

Si l'étendue s'effondre — une seule date de valorisation, donc $D \leq 0$ — aucun facteur n'existe et aucune valeur annualisée n'est produite. L'alternative serait d'en inventer une.

---

## 💡 Interprétation {: #interpretation }

Le tableau ci-dessous applique la formule à quelques formes de séries. Il s'agit d'arithmétique, pas de la sortie d'une exécution LibreFolio :

| Série | Rendements $N$ | Jours calendaires $D$ | $f = 365N/D$ | $\sqrt{f}$ |
|---|---|---|---|---|
| Instrument coté uniquement les jours de bourse, année complète | 252 | 365 | 252.0 | 15.87 |
| Instrument coté tous les jours (crypto), année complète | 365 | 365 | 365.0 | 19.10 |
| Fonds valorisé hebdomadairement, année complète | 52 | 365 | 52.0 | 7.21 |
| Instrument coté les jours de bourse, démarré en milieu de période | 126 | 183 | 251.3 | 15.85 |
| Série quotidienne avec des lacunes | 180 | 365 | 180.0 | 13.42 |

Quatre lectures découlent de ces lignes.

### 📈 √252 est retrouvé, pas imposé {: #252-is-recovered-not-imposed }

Un instrument coté uniquement lorsque son marché est ouvert contribue à environ 252 rendements sur une année calendaire complète, donc $f = 252 \times 365 / 365 = 252$ et le fameux $\sqrt{252}$ ressort de la mesure. Le nombre conventionnel est **un résultat** ici, pas une entrée — c'est précisément pourquoi rien n'est perdu à refuser de le coder en dur.

Il ressort même lorsque la source de prix fournit une ligne pour chaque jour calendaire. Certaines sources répètent la dernière clôture les jours où le marché est fermé — justETF, par exemple, répète la clôture du vendredi le samedi et le dimanche. Comptées comme des cotations, ces lignes ajouteraient un rendement nul qu'aucun marché n'a produit pour chaque jour de fermeture, et pousseraient $f$ vers 365. Elles ne sont pas comptées : un prix stocké daté d'un samedi, d'un dimanche ou d'un jour férié boursier en semaine dont la clôture répète **exactement** la clôture de la ligne précédente est un **report** — la dernière cotation reportée, pas une nouvelle — et sa date n'ajoute aucune observation à la série. Un prix qui a bougé un jour de fermeture reste une cotation, comme le font les prix de week-end d'un crypto-actif, et il en va de même d'un prix inchangé un jour de semaine ordinaire, comme un jour sans mouvement d'une obligation. L'instrument conserve ses jours de bourse, et $f$ reste proche de 252. La règle complète, avec les bourses dont les jours fériés sont pris en compte, se trouve dans [Qualité des données](data-quality.md#stored-carries).

!!! info "Une série de portefeuille est lue les jours de cotation de ses positions"

    Cette ligne décrit les prix cotés propres à un instrument ; la série de rendements d'un **portefeuille** y parvient par une autre voie. Le [rendement pondéré dans le temps](../performance-metrics/portfolio-engine/twrr.md) du portefeuille est calculé jour calendaire par jour calendaire, week-ends et jours fériés inclus, en reportant le dernier prix connu là où rien n'a été coté. L'analyse des risques ne le lit que sur ses **jours d'observation** — les jours où au moins une des positions détenues à la fin de la période analysée avait une cotation qui lui soit propre — et enchaîne le rendement de chaque autre jour dans le jour d'observation suivant, de sorte que le rendement cumulé est exactement ce qu'il était : seul l'échantillonnage change. Un portefeuille d'actions et de fonds cotés les jours de bourse contribue donc à environ 252 rendements par an, comme la première ligne, bien que son historique ait un point pour chaque jour calendaire ; un portefeuille qui détient un instrument coté chaque jour calendaire, comme un crypto-actif, est observé chaque jour, comme la deuxième. Le facteur suit la série sur laquelle la métrique est calculée, ce qui est exactement pourquoi il est mesuré plutôt que supposé.

### 🪙 Un instrument 24/7 donne ≈ √365 {: #a-247-instrument-gives-365 }

Un instrument qui se négocie chaque jour calendaire est observé 365 fois par an, donc $f \approx 365$. Un $\sqrt{252}$ codé en dur qui lui serait appliqué **sous-estimerait** sa volatilité annualisée d'un facteur de :

$$
\frac{\sqrt{365}}{\sqrt{252}} \approx 1.20
$$

L'erreur n'est pas un détail d'arrondi : elle est systématique, et elle pointe toujours dans la direction rassurante.

### 📐 Le facteur mesure un rythme, pas une longueur {: #the-factor-measures-a-rate-not-a-length }

La quatrième ligne est une action valorisée quotidiennement observée pendant environ la moitié d'une année : $f$ atterrit encore près de 252, car numérateur et dénominateur diminuent ensemble. Une fenêtre plus courte ne réduit pas le facteur — elle le rend seulement plus bruité (voir les limitations ci-dessous).

### 🕳️ Les lacunes le font baisser, honnêtement {: #gaps-lower-it-honestly }

Jours fériés, prix manquants, un actif démarré en milieu de période : ce qui a été observé est ce qui est compté. Une série avec des lacunes est annualisée comme la série clairsemée qu'elle est, plutôt que comme la série dense qu'on supposait qu'elle était.

---

## 📏 Couverture {: #coverage }

À côté du facteur, une seconde quantité est publiée avec le résultat : parmi les jours où la série aurait pu être observée, la part sur laquelle elle l'a été.

$$
c = \frac{N}{Q}
$$

où $Q$ est le nombre de ces jours. La couverture indique avec quelle **densité** la série a été échantillonnée, sous forme d'une fraction entre 0 et 1. Ce n'est pas un second facteur d'annualisation : $f$ indique à quel rythme la série a été observée, $c$ indique combien de ses observations possibles elle a conservées. Les jours qui comptent dans $Q$ dépendent de la façon dont la série est construite :

- Une série d'**instrument** — et toute série construite à partir des prix de plusieurs actifs — fonctionne sur un calendrier commun. Chaque date de la fenêtre demandée pour laquelle au moins un des actifs a une cotation qui lui soit propre est un candidat, et un candidat ne devient une observation que si chaque actif peut être valorisé à cette date, y compris un prix reporté d'une date antérieure. $Q$ compte les candidats, la ligne de base mise à part. Pour un instrument coté uniquement lorsque son marché est ouvert, les candidats sont le calendrier propre au marché, donc ses jours de fermeture ne coûtent rien : un report n'est pas une cotation, et n'ajoute aucun candidat.
- Une série de **portefeuille** est son rendement pondéré dans le temps lu sur ses jours d'observation (voir [ci-dessus](#252-is-recovered-not-imposed)), avec son premier point conservé comme ligne de base. $Q$ compte les jours d'observation après la ligne de base, jusqu'au dernier rendement. L'historique du portefeuille a un point pour chaque jour calendaire, donc pour un portefeuille détenu sans interruption, chaque jour d'observation en porte un, et la couverture se situe en haut de sa plage par construction. Ce n'est que si aucune des positions n'a de cotation qui lui soit propre dans la fenêtre que chaque jour calendaire est conservé, et $Q$ est alors l'étendue $D$.

Ce que la couverture ne dit **pas**, c'est si les prix derrière ces observations étaient réels. Sur un calendrier commun, une date à laquelle seulement certains des actifs étaient cotés reste une observation, les autres entrant avec un prix reporté ; lors du jour d'observation d'un portefeuille, chaque position non cotée ce jour-là entre à sa dernière valeur connue. Ainsi, une couverture élevée n'est pas un certificat et une couverture faible n'est pas un défaut : les deux décrivent *combien d'observations possibles la série a conservées*, pas la qualité de ce qu'elles contiennent. Cette seconde question — ces prix étaient-ils cotés, ou reportés ? — relève de [Qualité des données](data-quality.md).

!!! info "Les deux chiffres accompagnent le résultat"

    Chaque résultat de risque porte les entrées de sa propre annualisation dans ses métadonnées — le nombre d'observations, les jours calendaires couverts, le facteur et la couverture. Une valeur annuelle publiée peut donc être recalculée à la main à partir des mêmes entrées qui l'ont produite.

---

## ⚠️ Limites {: #limitations }

!!! warning "Une étendue courte rend le facteur instable"

    Le dénominateur est l'étendue calendaire observée. Sur quelques semaines, $D$ est petit, donc une observation manquante ou une observation supplémentaire déplace $f$ de manière appréciable, et $\sqrt{f}$ avec lui. La valeur annualisée hérite de cette instabilité : elle est extrapolée à partir d'une fenêtre bien plus courte que l'année qu'elle prétend décrire.

!!! warning "Mesurer le facteur ne corrige pas l'hypothèse"

    La mise à l'échelle par $\sqrt{f}$ découle de l'additivité de la variance sur des périodes **indépendantes** (voir [Volatilité](volatility.md)). Si les rendements sont autocorrélés — tendances, regroupement de volatilité, retour à la moyenne — la valeur mise à l'échelle est biaisée, quelle que soit la précision avec laquelle $f$ a été compté. Mesurer le facteur retire une constante erronée ; cela ne retire pas l'hypothèse d'indépendance qui la sous-tend.

Deux valeurs annualisées avec des facteurs différents ne sont également comparables que si l'échantillonnage qui les sous-tend est comparable. Un fonds valorisé hebdomadairement et un instrument 24/7 sont tous deux annualisés correctement, et sont pourtant observés de manières très différentes — ce que le nombre d'observations et la couverture sont là pour rendre visible.

---

## 🔗 Associés {: #related }

- 📊 **[Volatilité](volatility.md)** — la valeur la plus souvent exprimée sur une base annuelle
- 🧪 **[Qualité des données](data-quality.md)** — ce que signifie une couverture faible pour la fiabilité d'un résultat
- 📐 **[Ratio de Sharpe](sharpe-ratio.md)** — un ratio ajusté du risque qui porte aussi une échelle annuelle
- 📊 **[Ratio de Sortino](sortino-ratio.md)** — la variante uniquement à la baisse, même question de mise à l'échelle
