# 💵 MWRR (taux de rendement pondéré par les flux de trésorerie) / XIRR

## 💡 Qu’est-ce que c’est ?
Le MWRR (également appelé taux de rendement interne) mesure **votre performance personnelle** en tant qu’investisseur. Contrairement aux indicateurs qui portent uniquement sur les actifs, il tient compte à la fois de la performance des actifs sous-jacents et du **moment et de la taille** de vos dépôts et retraits.

Pour offrir une visibilité complète, LibreFolio distingue deux formes de cet indicateur : le **MWRR annualisé** et le **MWRR cumulé**.

---

## 📈 MWRR annualisé vs. MWRR cumulé

### 📈 MWRR annualisé {: #annualized-mwrr }
Le MWRR annualisé est le taux de rendement annuel composé qui rend la valeur actuelle nette (VAN) de tous les flux de trésorerie égale à zéro.

Ce taux composé est mathématiquement équivalent au **CAGR** (taux de croissance annuel composé) de votre argent réellement investi ; il représente le taux de croissance annuel lissé nécessaire pour que le capital atteigne le solde final, en tenant compte de tous les mouvements intermédiaires.

$$
0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{\frac{t_i}{365}}}
$$

??? note "🧮 Comment l’équation VAN est développée"

    #### 1. Forme intuitive de la valeur finale
    Imaginez que vous cherchiez à projeter votre valeur nette (NAV) finale en faisant croître chaque flux de trésorerie à un taux composé \(r\) :
    
    \[
    NAV_{final} = CF_0 \times (1 + r)^{\frac{d_0}{365}} + CF_1 \times (1 + r)^{\frac{d_1}{365}} + \dots + CF_n \times (1 + r)^{\frac{d_n}{365}}
    \]
    
    où \(d_i\) représente le nombre de jours pendant lesquels chaque flux de trésorerie a été investi au cours de la période.
    
    #### 2. Actualisation vers la valeur actuelle nette (VAN = 0)
    En divisant les deux membres de l’équation par \((1 + r)^{\frac{\text{nombre total de jours}}{365}}\), nous ramenons tous les flux de trésorerie au début de la période (\(t_0\)). On obtient ainsi l’équation standard de la valeur actuelle nette (VAN), où la somme des flux de trésorerie actualisés est égale à zéro :
    
    \[
    0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{\frac{t_i}{365}}}
    \]
    
    où \(t_i\) est le nombre de jours entre le début de la période et la date du flux de trésorerie \(i\).
    
    #### 3. Exemple de développement des flux de trésorerie
    Voyons comment les flux de trésorerie s’agencent pour un portefeuille sur une période de 31 jours :
    
    * **Jour 0 :** la valeur de départ du portefeuille est de 1 000 € (représentée comme un dépôt/un investissement).
    * **Jour 15 :** vous déposez 100 €.
    * **Jour 31 :** la NAV finale du portefeuille est de 1 150 €.
    
    Tout d’abord, nous construisons le tableau des transactions du point de vue de l’investisseur (l’argent qui entre dans le portefeuille est négatif, l’argent qui en revient est positif) :
    
    | Étape (\(i\)) | Jour (\(t_i\)) | Événement | Flux de trésorerie de l’investisseur (\(CF_i\)) |
    |------------|-------------|-------|---------------------------|
    | 0 | 0 | Solde initial | **-1 000 €** (Sortie) |
    | 1 | 15 | Dépôt | **-100 €** (Sortie) |
    | 2 | 31 | Liquidation hypothétique (NAV) | **+1 150 €** (Entrée) |
    
    À présent, nous développons ces transactions dans la somme VAN :
    
    \[
    0 = -1\,000 + \frac{-100}{(1+r)^{\frac{15}{365}}} + \frac{1\,150}{(1+r)^{\frac{31}{365}}}
    \]
    
    Le solveur mathématique recherche de manière itérative la valeur de \(r\) (MWRR annualisé) qui rend le membre de droite de cette équation égal à 0.

    #### 4. Ancrage du graphique cumulé
    Cette convention de signe garantit que, dès le premier jour (\(t_0\)), le dépôt initial (\(CF_0 = -1\,000\)) et la liquidation hypothétique (\(CF_1 = +1\,000\)) s’annulent mutuellement :
    
    \[
    0 = -1\,000 + 1\,000 = 0\%
    \]
    
    Cela ancre le début du graphique MWRR cumulé exactement à **0 %**.

**Descriptions des variables :**

* $r$ = MWRR annualisé (représentant le CAGR de votre argent réel).
* $CF_i$ = flux de trésorerie du point de vue de l’investisseur :
    * **Flux de trésorerie négatifs ($CF_i < 0$) :** capital engagé dans le portefeuille (dépôts, investissements). Cela représente de l’argent qui quitte les liquidités personnelles de l’investisseur.
    * **Flux de trésorerie positifs ($CF_i > 0$) :** capital restitué à l’investisseur (retraits, dividendes). Cela représente de l’argent qui revient dans les liquidités personnelles de l’investisseur.
    * **Valorisation finale ($CF_n > 0$) :** la valeur nette (NAV) finale du portefeuille à la fin de la période, traitée comme un flux entrant positif (une liquidation hypothétique où l’ensemble du portefeuille est reconverti en liquidités revenant à l’investisseur).
* $t_i$ = nombre de jours écoulés depuis le début de la période ($t_0 = 0$).

**Concepts clés :**

* Il représente une **vitesse/taux annuel** de croissance.
* Il est idéal pour les comparaisons à long terme (par exemple, comparer votre performance à un taux d’intérêt bancaire annuel ou au CAGR).
* **Avertissement sur la volatilité :** sur des périodes courtes (par exemple, quelques jours ou semaines), le rendement annualisé peut être très volatil et afficher des pourcentages extrêmes, car le calcul extrapole un rendement observé sur une petite fenêtre à une année complète de 365 jours.

LibreFolio construit les flux de trésorerie du MWRR à partir des deltas de la base de capital, et non des lignes de dépôt en espèces uniquement. Le capital d’ajustement/transfert valorisé en nature est donc traité comme du capital versé plutôt que comme une performance d’investissement soudaine. Un ajustement sortant n’a aucune valeur : il ne restitue rien à l’investisseur et ne constitue pas un flux de trésorerie ([Capital versé — Ajustements sortants](deposited-capital.md#outgoing-adjustments)).

### 📊 MWRR cumulé {: #cumulative-mwrr }
Le MWRR cumulé représente le rendement total équivalent sur la période sélectionnée, obtenu en composant le taux annualisé sur la durée réelle de cette fenêtre.

**Formule directe (sans racines, utilise directement $r$) :**

$$
\text{MWRR}_{\text{cumulé}} = (1 + r)^{\frac{\text{jours}}{365}} - 1
$$

**Formule du taux quotidien (avec racine) :**

$$
\text{MWRR}_{\text{cumulé}} = (1 + r_d)^{\text{jours}} - 1 \quad \text{où} \quad r_d = \sqrt{1 + r} - 1
$$

Les deux formules sont mathématiquement équivalentes. Toutefois, sur le plan du calcul, la formule directe utilisant $r$ (sans racines) est préférée une fois le taux annualisé $r$ trouvé, car l’exponentiation directe est plus simple et plus efficace à calculer pour le logiciel.

**Descriptions des variables :**

* $\text{jours}$ = nombre effectif de jours calendaires dans la fenêtre temporelle sélectionnée.

**Concepts clés :**

* Il représente la **distance totale parcourue** sur la période.
* Il commence à 0 % et croît au fil de la chronologie, ce qui en fait l’indicateur correct pour une visualisation graphique en série.
* **Pas un simple HPR :** bien qu’il représente un rendement cumulé, il s’agit d’un rendement cumulé pondéré par les flux de trésorerie. Il ne faut pas le confondre avec le simple rendement de la période de détention (ROI), qui ignore la chronologie des flux de trésorerie.

---

## 🔢 Exemple numérique sur 10 ans

Prenons un scénario sur 10 ans pour voir comment le moment des flux influe sur la performance et comment ces indicateurs se convertissent :

* **Année 0 :** vous déposez **10 000 €**.
* **Année 5 :** vous déposez **90 000 €** supplémentaires.
* **Année 10 :** votre valeur nette (NAV) finale est de **200 000 €**.

### 📉 Comparaison avec le ROI simple
Le ROI simple est calculé uniquement sur le total des contributions nettes :

$$
ROI = \frac{200\,000 - 100\,000}{100\,000} = +100\%
$$

### ⏱️ Effet timing du MWRR
Si l’essentiel de votre capital (90 000 €) a été déposé au cours de l’année 5, juste avant une reprise massive du marché sur plusieurs années, votre argent a travaillé très efficacement. Comme la somme la plus importante a été exposée aux années de forte croissance, votre **MWRR annualisé** serait bien supérieur au TWRR du marché.

En utilisant un solveur mathématique VAN pour ce scénario précis :
* Le **MWRR annualisé ($r$)** est exactement de **13,02 %**.

### 🔁 Conversion en MWRR cumulé
En composant ce rendement annualisé de 13,02 % sur la période de 10 ans :

$$
\text{MWRR}_{\text{cumulé}} = (1 + 0{,}130227)^{10} - 1 \approx +240{,}14\,\%
$$

### 💡 Que signifie +240,14 % ?
* Cela ne signifie **pas** que vos contributions totales de 100 000 € ont atteint 340 140 €.
* Cela signifie qu’un **euro théorique**, investi au tout début de la période de 10 ans et laissé sans y toucher, aurait atteint 3,40 €, soit un rendement total de 240,14 %, en croissant à la même vitesse moyenne composée que vos flux de trésorerie réels.

---

## 🖥️ Intégration à l’interface et utilisation du tableau de bord

LibreFolio affiche ces indicateurs de performance dans le tableau de bord :

### 📊 Graphique en pourcentage (`%`)
Les séries tracées utilisent le **MWRR cumulé**, le **TWRR cumulé** et le **ROI simple**. Cela permet une comparaison visuelle directe côte à côte, car les trois séries commencent à 0 % et représentent la progression totale sur la période sélectionnée.

### 📐 La courbe MWRR est constituée de points réels {: #mwrr-line }

Contrairement au TWRR et au ROI, le MWRR change même un jour où rien ne se passe : le temps passe et, avec plusieurs flux, il n’existe pas de forme fermée permettant de l’étendre d’un jour au suivant. Dans le rapport de portefeuille, il n’est donc pas stocké dans les [étapes quotidiennes](index.md#daily-states-as-steps) de l’historique, mais dans sa propre série, `mwrr_line`, dont les points sont des **valeurs réelles** : chacun est le MWRR de la période se terminant à sa date, calculé ce jour-là, annualisé et cumulé, selon la même règle que les cartes (voir ci-dessous). La courbe possède un point au début et à la fin de chaque étape de l’historique, plus un point à la fin de chaque mois calendaire dans les étapes de plus de 62 jours (au maximum 24 par étape) ; son premier point est 0. Rien entre deux points n’est estimé ni stocké : le graphique les relie.

### 🧾 Cartes KPI
* **ROI simple** (indicateur principal pour le rendement absolu).
* **TWRR cumulé** (indicateur de performance de la stratégie/allocation).
* **MWRR cumulé** (indicateur principal de l’effet timing personnel).
* **MWRR annualisé** (affiché comme indicateur secondaire/comparatif pour comprendre le taux annuel composé).

### 🚫 Quand aucun MWRR n’est affiché

Les cartes KPI et la courbe MWRR du graphique suivent la même règle chaque jour de la période. Un jour possède un MWRR uniquement lorsque :

* la valeur du portefeuille ce jour-là est supérieure à zéro, et
* la période conserve encore du **capital net investi** ce jour-là : la valeur avec laquelle elle a ouvert, plus les dépôts, moins les retraits effectués jusqu’à ce jour (les flux de capital décrits ci-dessus), est supérieure à zéro.

Sinon, il n’y a pas de taux : la carte affiche `—`, et la courbe présente un vide (un point sans valeur). Après des retraits nets, le vide commence le jour où ils font passer le capital net investi à zéro ou en dessous, et dure jusqu’à ce que de nouveaux dépôts le ramènent au-dessus de zéro. Les cartes affichent toujours le dernier point de la courbe ; une carte sans MWRR va donc de pair avec une courbe qui se termine par un vide. Un jour n’a pas non plus de MWRR lorsqu’aucun taux ne résout l’équation des flux de trésorerie : LibreFolio n’affiche jamais un taux qui ne la résout pas.

!!! tip "Analyse de la différence de performance"

    Pour interpréter la différence entre le MWRR cumulé et le TWRR cumulé, consultez la page [Effet timing](timing-effect.md).
