# 📈 Rendements et taux de croissance

Cette page présente les fondements mathématiques des **rendements d'investissement** — comment mesurer, comparer et annualiser des taux de croissance. Ces concepts sont utilisés dans l'ensemble des outils de mesure et des analyses de portefeuille de LibreFolio.

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
- **Non additif** : on ne peut pas simplement additionner les rendements simples de plusieurs périodes pour obtenir le rendement total
- **Composition** : les rendements multi-périodes doivent être **multipliés**, et non additionnés

$$
R_{total} = (1 + R_1)(1 + R_2) \cdots (1 + R_n) - 1
$$

---

## 📐 Rendement logarithmique (continu)

Le **rendement log** est le logarithme népérien du rapport des prix :

$$
r_{log} = \ln\left(\frac{P_{end}}{P_{start}}\right) = \ln(P_{end}) - \ln(P_{start})
$$

### 📊 Propriétés

- **Additif dans le temps** : le rendement log total = la somme des rendements log des sous-périodes

$$
r_{total} = r_1 + r_2 + \cdots + r_n
$$

- **Symétrique** : une variation de +5 % suivie d'une variation de −5 % ramène exactement au point de départ
- **Approximativement égal** au rendement simple pour de petites valeurs : $r_{log} \approx R_{simple}$ lorsque $R_{simple}$ est petit

### 🔄 Conversion

$$
r_{log} = \ln(1 + R_{simple}) \qquad R_{simple} = e^{r_{log}} - 1
$$

---

## 📅 Rendement annualisé

Pour comparer des rendements sur des périodes différentes, nous les **annualisons** — en projetant le taux de croissance observé sur une année complète.

### 📈 Taux de croissance annuel composé (CAGR)

La méthode d'annualisation la plus courante. Étant donné un rendement total sur $d$ jours calendaires :

$$
R_{annual} = \left(\frac{P_{end}}{P_{start}}\right)^{365/d} - 1
$$

C'est ce qu'affiche l'[outil Mesures](../../user/fx/detail/measures.md) de LibreFolio.

!!! example

    EUR/USD passe de 1,10 à 1,14 en 90 jours :

    $$R_{annual} = \left(\frac{1.14}{1.10}\right)^{365/90} - 1 = (1.0364)^{4.056} - 1 \approx 15.5\%$$

### 📐 Rendement log annualisé

Pour les rendements log, l'annualisation se réduit à une mise à l'échelle :

$$
r_{annual} = r_{log} \times \frac{365}{d}
$$

Cette linéarité est l'un des principaux avantages des rendements log en finance quantitative.

---

## 🔄 Relation entre rendements simples et rendements log

| Propriété | Rendement simple $R$ | Rendement log $r$ |
|----------|:---:|:---:|
| **Composition** | Multiplicative : $(1+R_1)(1+R_2)$ | Additive : $r_1 + r_2$ |
| **Symétrie** | Asymétrique : +10 % puis −10 % ≠ 0 | Symétrique : +10 % puis −10 % = 0 |
| **Annualisation** | $(1+R)^{365/d} - 1$ | $r \times 365/d$ |
| **Rendements de portefeuille** | La somme pondérée fonctionne ✅ | La somme pondérée ne fonctionne pas ❌ |
| **Séries temporelles** | Non additives ❌ | Additives ✅ |
| **Interprétation** | « J'ai gagné 5 % » | « Le taux de croissance logarithmique était de 0,0488 » |

!!! tip "Quand utiliser l'un plutôt que l'autre ?"

    - **Rendements simples** pour présenter les résultats aux utilisateurs et calculer les rendements au niveau du portefeuille
    - **Rendements log** pour l'analyse statistique, l'estimation de la volatilité et les modèles de séries temporelles

---

## 🔁 Rendement glissant {: #rolling-return }

Un **rendement glissant** est le rendement simple des sections ci-dessus, mesuré sur une fenêtre qui glisse le long de la série : une valeur par date, chacune remontant sur la même étendue. LibreFolio compte cette étendue en **jours calendaires**, et un même calcul alimente deux fonctionnalités de la page d'un actif : le mode **Rendement glissant** du graphique, et le signal **Rendement glissant** du panneau Signaux, dans la famille des risques, qui trace la même série par-dessus les prix. Le bouton guide 📖 de la carte du signal **Rendement glissant** ouvre cette page.

### 🗓️ Sur une fenêtre de jours calendaires {: #rolling-return-calendar }

Chaque date est mesurée par rapport à la clôture exactement $N$ jours calendaires plus tôt. Avec $\hat{P}(d)$ la clôture résolue du jour calendaire $d$ — la dernière clôture disponible à la date $d$ ou avant, convertie dans la devise du graphique, de sorte qu'un week-end ou un jour férié corresponde à la séance qui le précède — le rendement au jour $d$ est

$$
R^{[N]}(d) = \frac{\hat{P}(d)}{\hat{P}(d - N)} - 1
$$

Dans le mode du graphique, les préréglages **1S**, **1M**, **3M** et **1A** fixent $N$ à 7, 30, 90 et 365 jours, et une fenêtre personnalisée compte 7 jours par semaine, 30 par mois et 365 par an ; sur la carte du signal, $N$ correspond à la **Fenêtre**, un nombre entier de jours — 30 par défaut, au minimum 1. Un point est laissé vide, jamais estimé, lorsque l'une des deux extrémités n'a pas de clôture résolue ou a une clôture non positive ; lorsqu'aucun point de la plage ne peut être calculé, le résultat est indisponible. Le mode du graphique affiche également, pour chaque point, la date de référence demandée ainsi que les dates du prix et du taux de change réellement utilisés — voir le [Graphique interactif](../../user/assets/detail/chart.md#rolling-return).

### ⚖️ Jours calendaires, et non séances {: #sessions-or-calendar-days }

La fenêtre est un intervalle de temps, pas un nombre de cotations. Les autres indicateurs du panneau Signaux comptent en revanche des cotations : les [indicateurs techniques](../technical-analysis/indicators/index.md) comptent les séances, c'est-à-dire les jours disposant de leur propre cotation, tandis que la volatilité glissante, le ratio de Sharpe et le bêta comptent les observations de rendement. Un même nombre peut alors désigner des étendues différentes — 30 séances d'un instrument coté en semaine couvrent environ six semaines, 30 séances d'un instrument coté tous les jours couvrent 30 jours — tandis qu'une fenêtre de $N$ jours calendaires couvre exactement $N$ jours sur tout actif, quel que soit son rythme de cotation : deux rendements glissants de même $N$ comparent toujours la même étendue. Le rendement est défini à chaque date du graphique, et un jour de fermeture à l'une des extrémités est rattaché à la dernière clôture qui le précède.

Le rendement glissant est un rendement simple fondé uniquement sur les prix : il n'ajoute ni dividendes, ni coupons, ni flux de trésorerie, et il n'est pas annualisé. Pour le comparer à un rendement sur une étendue différente, annualisez-le avec la formule du CAGR ci-dessus, $d$ valant $N$ — en gardant à l'esprit le piège des périodes très courtes évoqué plus bas.

---

## 📏 Conventions de décompte des jours

Le nombre de jours $d$ peut être calculé différemment selon la convention :

- **Actual/365** : jours calendaires (ce qu'utilise LibreFolio)
- **Actual/360** : jours calendaires sur une année de 360 jours (courant sur les marchés monétaires)
- **30/360** : suppose des mois de 30 jours et une année de 360 jours

Pour plus de détails, voir [Conventions de décompte des jours](day-count.md).

---

## 💰 Méthodes de rendement de portefeuille

Lorsqu'un portefeuille comporte des **flux de trésorerie** (dépôts, retraits), une seule formule de rendement ne suffit pas, car les apports ou retraits de capital dilueraient ou gonfleraient artificiellement le rendement en pourcentage.

Pour résoudre ce problème, des mesures de performance avancées sont utilisées :
- **TWRR (Time-Weighted Rate of Return)** : isole la performance des actifs, en ignorant le calendrier des flux de trésorerie de l'investisseur.
- **MWRR (Money-Weighted Rate of Return)** : mesure la performance personnelle de l'investisseur, en tenant compte du calendrier des flux de trésorerie.

Pour approfondir le fonctionnement de ces mesures, la raison pour laquelle elles diffèrent et la façon dont LibreFolio les utilise, voir le chapitre dédié [Mesures de performance](../technical-analysis/performance-metrics/index.md).

---

## ⚠️ Pièges

1. **Périodes très courtes** : annualiser un rendement sur 3 jours peut produire des chiffres trompeurs (par exemple, une variation de 0,1 % sur 3 jours → 12,5 % annualisé)
2. **Prix négatifs** : les rendements log ne sont pas définis pour les valeurs négatives — ce n'est pas un problème pour les taux de change
3. **Fréquence de composition** : le CAGR suppose une composition continue ; les intérêts des instruments réels peuvent être composés quotidiennement, mensuellement ou trimestriellement
