# 📈 Rendements et taux de croissance

Cette page présente les fondements mathématiques des **rendements d'investissement** — comment mesurer, comparer et annualiser les taux de croissance. Ces concepts sont utilisés dans l'ensemble des outils de mesure et des analyses de portefeuille de LibreFolio.

---

## 📊 Rendement simple (discret)

Le **rendement simple** sur une période est la variation en pourcentage :

$$
R_{simple} = \frac{P_{end} - P_{start}}{P_{start}} = \frac{P_{end}}{P_{start}} - 1
$$

!!! example

    Si EUR/USD passe de 1,10 à 1,14 :

    $$R = \frac{1.14 - 1.10}{1.10} = 0.0364 = 3.64\%$$

### 📊 Propriétés

- **Intuitif** : représente directement « combien vous avez gagné/perdu »
- **Non additif** : vous ne pouvez pas simplement additionner les rendements simples sur plusieurs périodes pour obtenir le rendement total
- **Composition** : les rendements multi-périodes doivent être **multipliés**, et non additionnés

$$
R_{total} = (1 + R_1)(1 + R_2) \cdots (1 + R_n) - 1
$$

---

## 📐 Rendement logarithmique (continu)

Le **rendement logarithmique** est le logarithme népérien du ratio de prix :

$$
r_{log} = \ln\left(\frac{P_{end}}{P_{start}}\right) = \ln(P_{end}) - \ln(P_{start})
$$

### 📊 Propriétés

- **Additif dans le temps** : rendement log total = somme des rendements log des sous-périodes

$$
r_{total} = r_1 + r_2 + \cdots + r_n
$$

- **Symétrique** : une variation de +5 % suivie d'une variation de −5 % revient exactement au point de départ
- **Approximativement égal** au rendement simple pour les petites valeurs : $r_{log} \approx R_{simple}$ lorsque $R_{simple}$ est petit

### 🔄 Conversion

$$
r_{log} = \ln(1 + R_{simple}) \qquad R_{simple} = e^{r_{log}} - 1
$$

---

## 📅 Rendement annualisé

Pour comparer des rendements sur différentes périodes, nous les **annualisons** — en projetant le taux de croissance observé sur une année complète.

### 📈 Taux de croissance annuel composé (CAGR)

La méthode d'annualisation la plus courante. Étant donné un rendement total sur $d$ jours calendaires :

$$
R_{annual} = \left(\frac{P_{end}}{P_{start}}\right)^{365/d} - 1
$$

C'est ce que l'[outil Mesures](../../user/fx/detail/measures.md) de LibreFolio affiche.

!!! example

    EUR/USD passe de 1,10 à 1,14 sur 90 jours :

    $$R_{annual} = \left(\frac{1.14}{1.10}\right)^{365/90} - 1 = (1.0364)^{4.056} - 1 \approx 15.5\%$$

### 📐 Rendement logarithmique annualisé

Pour les rendements logarithmiques, l'annualisation est simplement une mise à l'échelle :

$$
r_{annual} = r_{log} \times \frac{365}{d}
$$

Cette linéarité est l'un des principaux avantages des rendements logarithmiques en finance quantitative.

---

## 🔄 Relation entre rendements simple et logarithmique

| Propriété | Rendement simple $R$ | Rendement logarithmique $r$ |
|----------|:---:|:---:|
| **Composition** | Multiplicatif : $(1+R_1)(1+R_2)$ | Additif : $r_1 + r_2$ |
| **Symétrie** | Asymétrique : +10 % puis −10 % ≠ 0 | Symétrique : +10 % puis −10 % = 0 |
| **Annualisation** | $(1+R)^{365/d} - 1$ | $r \times 365/d$ |
| **Rendements de portefeuille** | La somme pondérée fonctionne ✅ | La somme pondérée ne fonctionne pas ❌ |
| **Séries temporelles** | Non additif ❌ | Additif ✅ |
| **Interprétation** | « J'ai gagné 5 % » | « Le taux de croissance logarithmique était de 0,0488 » |

!!! tip "Quand utiliser l'un ou l'autre ?"

    - **Rendements simples** pour le reporting aux utilisateurs et le calcul des rendements au niveau du portefeuille
    - **Rendements logarithmiques** pour l'analyse statistique, l'estimation de la volatilité et les modèles de séries temporelles

---

## 🔁 Rendement glissant {: #rolling-return }

Un **rendement glissant** est le rendement simple des sections ci-dessus, mesuré sur une fenêtre qui glisse le long de la série : une valeur par date, chacune remontant sur la même étendue. Deux fonctionnalités de la page d'un actif le calculent, et elles diffèrent dans la façon dont l'étendue est comptée — en séances, ou en jours calendaires. Le 📖 bouton guide sur la carte du signal **Rendement glissant** ouvre cette page.

### 📊 Sur une fenêtre de séances {: #rolling-return-sessions }

Le signal **Rendement glissant** du panneau Signaux, dans la famille des risques, lit la série de rendements préparée de l'actif, dans la devise du graphique : un rendement simple par **séance**, un jour où l'actif possède une cote qui lui est propre. Un prix stocké un week-end ou un jour férié boursier qui ne fait que répéter la clôture précédente n'est pas une séance. Avec $V_t$ la valeur à la séance $t$ et $r_t = V_t / V_{t-1} - 1$, le rendement glissant sur une fenêtre de $w$ séances est

$$
R_t^{(w)} = \prod_{k=0}^{w-1} \left(1 + r_{t-k}\right) - 1 = \frac{V_t}{V_{t-w}} - 1
$$

calculé au moyen de logarithmes, $R_t^{(w)} = \exp\left(\sum_{k=0}^{w-1} \ln(1 + r_{t-k})\right) - 1$, afin que la fenêtre puisse glisser d'un pas à la fois. La fenêtre $w$ — 30 par défaut, de 1 à 500 — compte les observations de rendement, et non les jours calendaires : 30 séances d'un instrument coté en semaine couvrent environ six semaines, 30 séances d'un instrument coté tous les jours couvrent 30 jours. La première valeur apparaît dès que $w + 1$ valorisations sont disponibles.

### 🗓️ Sur une fenêtre de jours calendaires {: #rolling-return-calendar }

Le mode **Rendement glissant** du graphique mesure chaque date par rapport à la clôture exactement $N$ jours calendaires plus tôt. Avec $\hat{P}(d)$ la clôture résolue du jour calendaire $d$ — la dernière clôture disponible à $d$ ou avant, convertie dans la devise du graphique, de sorte qu'un week-end ou un jour férié reprend la séance qui le précède — le rendement au jour $d$ est

$$
R^{[N]}(d) = \frac{\hat{P}(d)}{\hat{P}(d - N)} - 1
$$

Les préréglages **1W**, **1M**, **3M** et **1Y** fixent $N$ à 7, 30, 90 et 365 jours ; une fenêtre personnalisée compte 7 jours par semaine, 30 par mois et 365 par an. Un point est laissé vide, jamais estimé, lorsqu'une des extrémités n'a pas de clôture résolue ou a une clôture qui n'est pas positive ; lorsqu'aucun point de la plage ne peut être calculé, le résultat est indisponible. Chaque point indique la date de référence demandée et les dates du prix et du taux de change réellement utilisés — voir le [Graphique interactif](../../user/assets/detail/chart.md#rolling-return).

### ⚖️ Séances ou jours calendaires {: #sessions-or-calendar-days }

Les deux mesures sont des rendements simples fondés uniquement sur le prix : aucune n'ajoute de dividendes, de coupons ou de flux de trésorerie, et aucune n'est annualisée. Elles répondent à des questions légèrement différentes :

| | Fenêtre de séances | Fenêtre de jours calendaires |
|---|---|---|
| Étendue | $w$ cotes, quelle que soit la période qu'elles couvrent | exactement $N$ jours, quel que soit le rythme de cotation |
| Défini sur | les séances de l'actif | chaque date du graphique |
| Comparer deux actifs | un $w$ égal peut signifier des étendues différentes | un $N$ égal signifie toujours la même étendue |
| Un jour de fermeture à l'une des extrémités | ne peut pas se produire : seules les séances sont utilisées | résolu à la dernière clôture qui le précède |

Pour comparer un rendement glissant avec un autre sur une étendue différente, annualisez-le avec la formule du CAGR ci-dessus, $d$ étant l'étendue en jours calendaires — en gardant à l'esprit le piège des périodes très courtes ci-dessous.

---

## 📏 Conventions de décompte des jours

Le nombre de jours $d$ peut être calculé différemment selon la convention :

- **Actual/365** : jours calendaires (ce que LibreFolio utilise)
- **Actual/360** : jours calendaires sur une année de 360 jours (courant sur les marchés monétaires)
- **30/360** : suppose des mois de 30 jours et une année de 360 jours

Pour plus de détails, voir [Conventions de décompte des jours](day-count.md).

---

## 💰 Méthodes de rendement de portefeuille

Lorsqu'un portefeuille comporte des **flux de trésorerie** (dépôts, retraits), une formule de rendement unique ne suffit pas, car les injections ou retraits de capital dilueraient ou gonfleraient artificiellement le rendement en pourcentage.

Pour résoudre ce problème, des indicateurs de performance avancés sont utilisés :
- **TWRR (taux de rendement pondéré dans le temps)** : isole la performance des actifs, en ignorant le timing des flux de trésorerie de l'investisseur.
- **MWRR (taux de rendement pondéré par les flux monétaires)** : mesure la performance personnelle de l'investisseur, en tenant compte du timing des flux de trésorerie.

Pour une analyse approfondie du fonctionnement de ces indicateurs, de leurs différences et de la manière dont LibreFolio les utilise, voir le chapitre dédié [Indicateurs de performance](../technical-analysis/performance-metrics/index.md).

---

## ⚠️ Pièges

1. **Périodes très courtes** : annualiser un rendement sur 3 jours peut produire des chiffres trompeurs (par ex., une variation de 0,1 % sur 3 jours → 12,5 % annualisé)
2. **Prix négatifs** : les rendements logarithmiques ne sont pas définis pour les valeurs négatives — ce n'est pas un problème pour les taux de change
3. **Fréquence de composition** : le CAGR suppose une composition continue ; les instruments du monde réel peuvent composer quotidiennement, mensuellement ou trimestriellement
