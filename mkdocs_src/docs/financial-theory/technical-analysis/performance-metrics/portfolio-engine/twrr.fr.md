# ⏱️ TWRR (taux de rendement pondéré par le temps)

## 💡 Qu'est-ce que c'est ?
Le TWRR mesure la **performance « pure »** des actifs et de la stratégie que vous avez choisis (le marché), en ignorant totalement le moment et le montant de vos dépôts ou retraits.

LibreFolio détecte les ruptures externes de sous-période à partir des variations de la base de capital. Cela inclut le capital d'AJUSTEMENT/TRANSFERT en nature valorisé, de sorte que les actifs injectés au départ sont traités comme du capital d'investisseur entrant dans le portefeuille, et non comme un rendement de marché. Un AJUSTEMENT sortant n'a pas de valeur et ne constitue pas un flux ([Capital versé — Ajustements sortants](deposited-capital.md#outgoing-adjustments)) : la valeur de ses unités quitte la NAV, et le rendement du jour l'interprète comme une perte.

Il s'agit de la mesure standard utilisée par les fonds communs de placement et les ETF, car les gérants n'ont aucun contrôle sur le moment où les clients déposent ou retirent du capital ; ils doivent être évalués uniquement sur les rendements des investissements sous-jacents.

---

## 🧩 Qu'est-ce qu'une sous-période ?
Pour isoler la performance des actifs de la chronologie des flux de capitaux, le TWRR découpe la chronologie d'évaluation en intervalles plus petits appelés **sous-périodes**.

Une **sous-période** est un intervalle de temps continu entre deux flux de capitaux externes consécutifs (dépôts ou retraits).

Par définition :
* Une nouvelle sous-période commence immédiatement après tout flux externe de capitaux.
* Pendant une sous-période donnée, **aucun capital externe n'est ajouté ni retiré** du portefeuille.
* Par conséquent, toute variation de la valeur du portefeuille pendant une sous-période est entièrement due à la performance des actifs (fluctuations des prix, dividendes, intérêts).

---

## 🧮 Comment ça fonctionne
Le TWRR calcule le taux de rendement de chaque sous-période individuellement, puis les enchaîne (les multiplie) entre eux.

$$
R_{\text{TWRR}} = \prod_{i=1}^{n} (1 + r_i) - 1 = (1 + r_1) \times (1 + r_2) \times \dots \times (1 + r_n) - 1
$$

**Descriptions des variables :**

* $r_i$ = le taux de rendement de la sous-période $i$.
* $n$ = le nombre total de sous-périodes.

---

??? note "Exemple de déroulement du TWRR"

    ### 🧾 1. Le scénario

    * **Jour 0 :** Vous démarrez votre portefeuille avec un dépôt initial de **1 000 €**.
    * **Jour 10 :** Le marché monte. Votre portefeuille vaut désormais **1 100 €**. Le même jour, vous déposez **500 €** supplémentaires en liquidités.
    * **Jour 20 :** Le marché baisse. Votre portefeuille termine à une valeur finale de **1 440 €**.

    ### 🧩 2. Décomposition des sous-périodes
    La chronologie est divisée en deux sous-périodes en raison du flux de capitaux du jour 10 :

    **Sous-période 1 (du jour 0 au jour 10) :**

    * Valeur de début (\(V_{\text{start}}\)) : **1 000 €**
    * Valeur de fin (\(V_{\text{end}}\) avant le flux de capitaux) : **1 100 €**
    * Rendement de la sous-période (\(r_1\)) :

    \[
    r_1 = \frac{V_{\text{end}}}{V_{\text{start}}} - 1 = \frac{1\,100}{1\,000} - 1 = +10\%
    \]

    **Sous-période 2 (du jour 10 au jour 20) :**

    * Valeur de début (\(V_{\text{start}}\) après le flux de capitaux) : 1 100 € + 500 € de dépôt = **1 600 €**
    * Valeur de fin (\(V_{\text{end}}\)) : **1 440 €**
    * Rendement de la sous-période (\(r_2\)) :

    \[
    r_2 = \frac{V_{\text{end}}}{V_{\text{start}}} - 1 = \frac{1\,440}{1\,600} - 1 = -10\%
    \]

    ### 🧮 3. Déroulement du calcul du TWRR
    Nous enchaînons les rendements des sous-périodes :

    \[
    \begin{aligned}
    R_{\text{TWRR}} &= (1 + r_1) \times (1 + r_2) - 1 \\
    &= (1 + 0.10) \times (1 - 0.10) - 1 \\
    &= 1.10 \times 0.90 - 1 \\
    &= 0.99 - 1 \\
    &= -1\%
    \end{aligned}
    \]

    Les actifs que vous avez choisis ont augmenté de 10 %, puis baissé de 10 %, ce qui donne un rendement net au niveau des actifs de **-1 %**.

    ### ⚖️ 4. TWRR vs. ROI simple
    Calculons le **ROI simple** pour exactement le même scénario afin de voir le contraste :

    * Total du capital net investi = 1 000 € + 500 € = **1 500 €**
    * Valeur finale du portefeuille = **1 440 €**
    * ROI simple :

    \[
    ROI = \frac{1\,440 - 1\,500}{1\,500} = -4\%
    \]

    **Pourquoi sont-ils différents ?**

    * Le **ROI simple (-4 %)** montre la performance réelle et brute de votre portefeuille. Il est tiré vers le bas parce que vous avez déposé 500 € juste avant une baisse de 10 %, ce qui rend votre perte plus lourde en termes absolus.
    * Le **TWRR (-1 %)** isole la performance de la stratégie des actifs. Il montre ce qui se serait passé si vous aviez investi une somme unique au départ et ne l'aviez plus jamais touchée.

---

## 🎯 Quand l'utiliser
* Pour juger de la qualité des **actifs et de la stratégie que vous avez retenus**, indépendamment de votre taux d'épargne personnel ou du moment de vos versements.
* Pour comparer directement la performance de votre portefeuille à des indices de référence externes (comme le S&P 500 ou un ETF indiciel).

---

## 🚫 Quand aucun TWRR n'est affiché {: #when-no-twrr }

La carte KPI et la ligne TWRR du graphique du tableau de bord suivent la même règle chaque jour de la période : un jour présente un TWRR uniquement lorsque la valeur du portefeuille ce jour-là est supérieure à zéro. Un portefeuille que vous avez vidé — tout a été vendu et les liquidités ont été retirées — ou dont les dettes dépassent ce qu'il détient n'a aucun rendement pondéré par le temps à afficher.

Ce jour-là, la carte affiche `—` et la ligne présente une interruption. La carte affiche toujours le dernier point de la ligne ; ainsi, une carte sans TWRR est associée à une ligne qui se termine par une interruption, et l'[Effet timing](timing-effect.md), qui nécessite le TWRR, affiche `—` lui aussi. Lorsque de nouveaux dépôts ramènent la valeur au-dessus de zéro, la ligne reprend à partir du rendement qu'elle avait atteint avant l'interruption : les jours à zéro n'ajoutent ni gain ni perte, et la chaîne des sous-périodes continue de se composer à partir de là.

Le premier point de la ligne fait exception : il vaut toujours 0, le point de départ de chaque rendement de la période.

---

!!! tip "Analyser la différence de performance"

    Pour comprendre comment vos flux de capitaux personnels ont fait dévier vos rendements réels du rendement pur de la stratégie (TWRR), consultez la page [Effet timing](timing-effect.md).
