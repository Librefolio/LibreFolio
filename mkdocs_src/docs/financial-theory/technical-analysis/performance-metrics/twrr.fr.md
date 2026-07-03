# ⏱️ TWRR (Taux de Rendement Pondéré par le Temps)

*[⬅️ Retour à l'aperçu des indicateurs de performance](index.md)*

## 💡 Qu'est-ce que c'est ?
Le TWRR (d'après l'anglais *Time-Weighted Rate of Return*) mesure la **performance « pure »** de vos actifs et de votre stratégie d'investissement (Le Marché), en ignorant complètement le timing et la taille de vos dépôts ou retraits.

C'est la métrique standard utilisée par les fonds communs de placement et les ETF parce que les gestionnaires de fonds n'ont aucun contrôle sur le moment où les clients décident de déposer ou de retirer des capitaux ; ils doivent donc être évalués uniquement sur les rendements générés par les investissements sous-jacents.

---

## 🧩 Qu'est-ce qu'une sous-période ?
Pour isoler la performance des actifs de celle du timing des flux de trésorerie, le TWRR divise la période d'évaluation en intervalles plus petits appelés **sous-périodes**.

Une **sous-période** est un intervalle de temps continu entre deux flux de trésorerie externes consécutifs (dépôts ou retraits).

Par définition :
* Une nouvelle sous-période commence immédiatement après tout flux de trésorerie externe.
* Durant une sous-période donnée, **aucun capital externe n'est ajouté ou retiré** du portefeuille.
* Par conséquent, toute variation de la valeur du portefeuille pendant une sous-période est uniquement due à la performance des actifs (variations de cours, dividendes, intérêts).

---

## 🧮 Comment ça fonctionne
Le TWRR calcule le taux de rendement de chaque sous-période individuellement, puis les lie (multiplie) ensemble.

$$
R_{\text{TWRR}} = \prod_{i=1}^{n} (1 + r_i) - 1 = (1 + r_1) \times (1 + r_2) \times \dots \times (1 + r_n) - 1
$$

**Description des Variables :**

* $r_i$ = Le taux de rendement de la sous-période $i$.
* $n$ = Le nombre total de sous-périodes.

---

??? note "Exemple de déroulement du TWRR"

    ### 1. Le scénario

    * **Jour 0 :** Vous commencez votre portefeuille avec un dépôt initial de **1 000 €**.
    * **Jour 10 :** Le marché monte. Votre portefeuille vaut maintenant **1 100 €**. Ce même jour, vous effectuez un dépôt supplémentaire de **500 €**.
    * **Jour 20 :** Le marché baisse. Votre portefeuille se termine sur une valeur finale de **1 440 €**.
    
    ### 2. Décomposition des sous-périodes
    La chronologie est divisée en deux sous-périodes en raison du flux de trésorerie du Jour 10 :
    
    **Sous-période 1 (du Jour 0 au Jour 10) :**

    * Valeur initiale (\(V_{\text{start}}\)) : **1 000 €**
    * Valeur finale (\(V_{\text{end}}\) avant flux de trésorerie) : **1 100 €**
    * Rendement de la sous-période (\(r_1\)) :

    \[
    r_1 = \frac{V_{\text{end}}}{V_{\text{start}}} - 1 = \frac{1\,100}{1\,000} - 1 = +10\ \%
    \]
    
    **Sous-période 2 (du Jour 10 au Jour 20) :**

    * Valeur initiale (\(V_{\text{start}}\) après flux de trésorerie) : 1 100 € + 500 € (dépôt) = **1 600 €**
    * Valeur finale (\(V_{\text{end}}\)) : **1 440 €**
    * Rendement de la sous-période (\(r_2\)) :

    \[
    r_2 = \frac{V_{\text{end}}}{V_{\text{start}}} - 1 = \frac{1\,440}{1\,600} - 1 = -10\ \%
    \]
    
    ### 3. Déroulement du calcul du TWRR
    Nous multiplions les rendements des sous-périodes ensemble :
    
    \[
    \begin{aligned}
    R_{\text{TWRR}} &= (1 + r_1) \times (1 + r_2) - 1 \\
    &= (1 + 0{,}10) \times (1 - 0{,}10) - 1 \\
    &= 1{,}10 \times 0{,}90 - 1 \\
    &= 0{,}99 - 1 \\
    &= -1\ \%
    \end{aligned}
    \]
    
    Les actifs que vous avez choisis ont augmenté de 10 % puis ont baissé de 10 %, ce qui donne un rendement net de la stratégie de **-1 %**.
    
    ### 4. TWRR vs. ROI Simple
    Calculons le **ROI Simple** pour le même scénario pour voir le contraste :

    * Capital net total investi = 1 000 € + 500 € = **1 500 €**
    * Valeur finale du portefeuille = **1 440 €**
    * ROI Simple :

    \[
    ROI = \frac{1\,440 - 1\,500}{1\,500} = -4\ \%
    \]
    
    **Pourquoi sont-ils différents ?**

    * **Le ROI Simple (-4 %)** montre la performance réelle de votre portefeuille. Il est pénalisé parce que vous avez déposé 500 € juste avant une baisse de -10 %, ce qui a alourdi vos pertes en valeur absolue.
    * **Le TWRR (-1 %)** isole la performance de la stratégie des actifs. Il montre ce qui se serait passé si vous aviez simplement investi une somme unique au début et n'y aviez plus touché.

---

## 🎯 Quand l'utiliser
* Pour évaluer la qualité des **actifs et de la stratégie choisis**, indépendamment de votre rythme d'épargne ou du timing de vos dépôts.
* Pour comparer directement la performance de votre portefeuille à des indices de référence externes (comme le S&P 500 ou un ETF indiciel).

---

!!! tip "Analyser la Différence de Performance"

    Pour comprendre comment vos flux de trésorerie personnels ont fait dévier vos rendements réels du rendement de la stratégie pure (TWRR), reportez-vous à la page de l'[Effet de timing](timing-effect.md).

