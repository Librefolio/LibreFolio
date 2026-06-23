# 💵 MWRR (Taux de Rendement Pondéré par les Capitaux) / XIRR

*[⬅️ Retour à l'aperçu des indicateurs de performance](index.md)*

## 💡 Qu'est-ce que c'est ?
Le MWRR (également connu sous le nom de Taux de Rendement Interne) mesure **votre performance personnelle** en tant qu'investisseur. Contrairement aux indicateurs centrés uniquement sur les actifs, il prend en compte à la fois la performance des actifs sous-jacents et le **timing et la taille** de vos dépôts et retraits.

Pour offrir une visibilité complète, LibreFolio distingue deux formes de cet indicateur : le **MWRR Annualisé** et le **MWRR Cumulatif**.

---

## 📈 MWRR Annualisé vs. MWRR Cumulatif

### MWRR Annualisé {: #annualized-mwrr }
Le MWRR Annualisé est le taux annuel composé qui égalise la valeur actuelle de tous les flux de trésorerie (valeur actuelle nette, VAN) avec zéro.

Ce taux composé est mathématiquement équivalent au **CAGR** (Compound Annual Growth Rate - taux de croissance annuel composé) de votre capital réellement investi, représentant le taux de croissance annuel constant nécessaire pour que le capital initial atteigne le solde final, en tenant compte de tous les mouvements intermédiaires.

$$
0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{\frac{t_i}{365}}}
$$

??? note "🧮 Comment l'équation NPV est déroulée"

    #### 1. Formule intuitive de la valeur finale
    Imaginez projeter votre valeur nette finale (VNI) en faisant croître chaque flux de trésorerie à un taux composé \(r\) :
    
    \[
    VNI_{finale} = CF_0 \times (1 + r)^{\frac{d_0}{365}} + CF_1 \times (1 + r)^{\frac{d_1}{365}} + \dots + CF_n \times (1 + r)^{\frac{d_n}{365}}
    \]
    
    Où \(d_i\) représente le nombre de jours pendant lesquels chaque flux a été investi durant la période.
    
    #### 2. Actualisation à la Valeur Actuelle Nette (VAN = 0)
    En divisant les deux côtés de l'équation par \((1 + r)^{\frac{\text{jours totaux}}{365}}\), nous ramenons tous les flux de trésorerie au début de la période (\(t_0\)). Cela nous donne l'équation standard de la Valeur Actuelle Nette (VAN) où la somme des flux actualisés est égale à zéro :
    
    \[
    0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{\frac{t_i}{365}}}
    \]
    
    Où \(t_i\) est le nombre de jours écoulés entre le début de la période et la date du flux \(i\).
    
    #### 3. Exemple de déroulement des flux de trésorerie
    Voyons comment les flux de trésorerie se répartissent pour un portefeuille sur une période de 31 jours :
    
    * **Jour 0 :** La valeur initiale du portefeuille est de 1 000 € (représentée comme un dépôt/investissement).
    * **Jour 15 :** Vous déposez 100 €.
    * **Jour 31 :** La VNI finale du portefeuille est de 1 150 €.
    
    Tout d'abord, nous construisons le tableau des transactions du point de vue de l'investisseur (l'argent versé dans le portefeuille est négatif, l'argent récupéré est positif) :
    
    | Étape (\(i\)) | Jour (\(t_i\)) | Événement | Flux de trésorerie (\(CF_i\)) |
    |-------------|--------------|-----------|-----------------------------|
    | 0 | 0 | Solde Initial | **-1 000 €** (Sortie) |
    | 1 | 15 | Dépôt | **-100 €** (Sortie) |
    | 2 | 31 | Liquidation hypothétique (VNI) | **+1 150 €** (Entrée) |
    
    Now, nous déployons ces transactions dans la sommation de la VAN :
    
    \[
    0 = -1000 + \frac{-100}{(1+r)^{\frac{15}{365}}} + \frac{1150}{(1+r)^{\frac{31}{365}}}
    \]
    
    Le solveur mathématique recherche de manière itérative la valeur de \(r\) (MWRR Annualisé) qui rend le côté droit de cette équation égal à 0.

    #### 4. Ancrage du graphique cumulatif
    Cette convention de signe garantit qu'au tout premier jour (\(t_0\)), le dépôt initial (\(CF_0 = -1000\)) et la liquidation hypothétique (\(CF_1 = +1000\)) s'annulent parfaitement :
    
    \[
    0 = -1000 + 1000 = 0\%
    \]
    
    Cela ancre le début du graphique du MWRR Cumulatif à exactement **0 %**.

**Description des Variables :**

* $r$ = MWRR Annualisé (représentant le CAGR de votre argent réel).
* $CF_i$ = Flux de trésorerie du point de vue de l'investisseur :
    * **Flux de trésorerie négatifs ($CF_i < 0$) :** Capital engagé dans le portefeuille (dépôts, achats). Cela représente l'argent sortant du portefeuille personnel de l'investisseur pour être investi.
    * **Flux de trésorerie positifs ($CF_i > 0$) :** Capital restitué à l'investisseur (retraits, dividendes). Cela représente l'argent retournant dans le portefeuille de l'investisseur.
    * **Valorisation finale ($CF_n > 0$) :** Le Net Asset Value (NAV) ou valeur nette finale (VNI) du portefeuille à la fin de la période, traité comme un afflux positif (une liquidation hypothétique où l'ensemble du portefeuille est converti en liquidités revenant à l'investisseur).
* $t_i$ = Jours écoulés depuis le début de la période ($t_0 = 0$).

**Concepts clés :**

* Il représente une **vitesse ou un taux annuel composé** de croissance.
* Il est idéal pour les comparaisons à long terme (ex. comparer votre performance avec un taux d'intérêt bancaire annuel ou le CAGR).
* **Avertissement sur la volatilité :** Sur des périodes courtes (ex. quelques jours ou semaines), le rendement annualisé peut être très volatile et afficher des pourcentages extrêmes car la formule extrapole le rendement d'une petite période sur une année complète de 365 jours.

### MWRR Cumulatif {: #cumulative-mwrr }
Le MWRR Cumulatif représente le rendement total équivalent sur la période sélectionnée, obtenu en capitalisant le taux annualisé sur la durée réelle de cette période.

**Formule Directe (sans racine, utilise directement $r$) :**

$$
\text{MWRR}_{\text{cumulatif}} = (1 + r)^{\frac{\text{jours}}{365}} - 1
$$

**Formule par Taux Journalier (avec racine) :**

$$
\text{MWRR}_{\text{cumulatif}} = (1 + r_d)^{\text{jours}} - 1 \quad \text{où} \quad r_d = \sqrt[365]{1 + r} - 1
$$

Les deux formules sont mathématiquement équivalentes. Cependant, sur le plan informatique, la formule directe utilisant $r$ (sans racine) est préférée une fois que le taux annualisé $r$ a été trouvé, car l'exponentiation directe est plus simple et plus efficace à calculer pour le logiciel.

**Description des Variables :**

* $\text{jours}$ = Le nombre réel de jours calendaires dans la période sélectionnée.

**Concepts clés :**

* Il représente la **distance totale parcourue** sur la période.
* Il commence à 0 % et augmente le long de la ligne de temps, ce qui en fait l'indicateur idéal pour la visualisation sur le graphique temporel.
* **Ce n'est pas un simple ROI :** Bien qu'il représente un rendement cumulatif, il s'agit d'un rendement cumulatif pondéré par les capitaux (money-weighted). Il ne doit pas être confondu avec le rendement simple de la période (ROI), qui ignore le timing des flux de trésorerie.

---

## 🔢 Exemple numérique sur 10 ans

Voyons un scénario sur 10 ans pour comprendre l'impact du timing sur la performance et comment ces indicateurs se convertissent :

* **Année 0 :** Vous déposez **10 000 €**.
* **Année 5 :** Vous déposez **90 000 €** supplémentaires.
* **Année 10 :** Votre valeur nette finale (VNI) est de **200 000 €**.

### Comparaison avec le ROI Simple
Le ROI simple est calculé uniquement sur les contributions nettes totales :

$$
ROI = \frac{200\,000 - 100\,000}{100\,000} = +100\ \%
$$

### Effet du timing sur le MWRR
Si la majeure partie de votre capital (90 000 €) a été déposée à l'Année 5, juste avant une forte reprise du marché sur plusieurs années, votre argent a travaillé très efficacement. Parce que la somme la plus importante a été exposée aux années de forte croissance, votre **MWRR Annualisé** sera bien supérieur au TWRR du marché.

En utilisant un solveur VAN pour ce scénario spécifique :
* Le **MWRR Annualisé ($r$)** est exactement de **13,02 %**.

### Conversion en MWRR Cumulatif
En capitalisant ce rendement annualisé de 13,02 % sur la période de 10 ans :

$$
\text{MWRR}_{\text{cumulatif}} = (1 + 0{,}130227)^{10} - 1 \approx +240{,}14\ \%
$$

### Que signifie +240,14 % ?
* Cela ne signifie **pas** que vos 100 000 € de contributions totales sont devenus 340 140 € :
* Cela signifie qu'un **euro théorique**, investi au tout début de la période de 10 ans et jamais retouché, serait devenu 3,40 €, réalisant un rendement total de 240,14 % en croissant à la même vitesse composée moyenne que vos flux réels.

---

## 🖥️ Intégration UI et utilisation sur le tableau de bord

LibreFolio affiche ces indicateurs de performance à différents endroits du tableau de bord :

### Graphique en pourcentage (`%`)
Les courbes tracées utilisent le **MWRR Cumulatif**, le **TWRR Cumulatif** et le **ROI Simple**. Cela permet une comparaison visuelle directe, car les trois courbes commencent à 0 % et représentent la progression totale sur la période sélectionnée.

### Cartes KPI
* **ROI Simple** (Indicateur principal pour le rendement absolu).
* **TWRR Cumulatif** (Indicateur de performance de la stratégie ou de l'allocation d'actifs).
* **MWRR Cumulatif** (Indicateur principal du timing personnel).
* **MWRR Annualisé** (Affiché comme indicateur secondaire pour comprendre le taux annuel composé).
