# 📈 Indicateurs de Performance

Lorsqu'on évalue le succès d'un portefeuille d'investissement, regarder uniquement le solde total ou le profit absolu ne suffit pas. Pour vraiment comprendre la performance, vous avez besoin d'indicateurs standardisés qui répondent à différentes questions : « Comment mes actifs se sont-ils comportés ? », « Mon timing a-t-il été bon ? » et « Quel est le rendement de cette transaction spécifique ? ».

---

## 🎭 Les deux acteurs de votre portefeuille

Pour comprendre pourquoi il existe plusieurs indicateurs, imaginez que deux « acteurs » différents gèrent votre patrimoine :

1. **Le Marché (Les Actifs) :** Fait varier à la hausse ou à la baisse le cours des actifs que vous détenez.
2. **Vous (L'Investisseur) :** Décidez *quand* déposer ou retirer des capitaux du portefeuille.

Ces deux acteurs peuvent obtenir des performances très différentes. Vous pouvez choisir un excellent actif (le Marché se comporte bien), mais l'acheter au plus haut juste avant un krach (vos résultats personnels sont mauvais). LibreFolio utilise différents indicateurs pour isoler ces deux comportements.

---

## 📚 Sujets traités dans ce chapitre

| Indicateur / Concept | Description |
|----------------------|-------------|
| **[Net Asset Value (NAV)](nav.md)** | Net Worth / Net Asset Value. La valorisation boursière totale du portefeuille (actifs + liquidités) à la fin de la fenêtre de temps sélectionnée. |
| **[Book Value](book-value.md)** | Le coût historique d'acquisition des positions ouvertes plus la liquidité. Utilisé pour comparer le coût d'achat à la valeur de marché. |
| **[P&L de la Période](period-pnl.md)** | Le profit ou la perte monétaire absolu généré par votre portefeuille au cours de la période sélectionnée, ajusté des flux de trésorerie. |
| **[Effet de timing](timing-effect.md)** | Différence entre le MWRR cumulé et le TWRR cumulé. Indique à quel point le moment et le montant de vos flux de trésorerie ont influencé votre rendement global. |
| **[ROI Simple](roi.md)** | Rendement en pourcentage absolu généré par un investissement par rapport à son coût. Idéal pour évaluer des positions individuelles. |
| **[TWRR](twrr.md)** | Taux de rendement pondéré par le temps (Time-Weighted Rate of Return). Mesure la performance pure des actifs sous-jacents, en ignorant le timing des flux de trésorerie. |
| **[MWRR (XIRR)](mwrr.md)** | Taux de rendement pondéré par les capitaux (Money-Weighted Rate of Return). Mesure votre performance personnelle en tant qu'investisseur, en tenant compte du timing des flux de trésorerie. Comprend à la fois la forme **Annualisée** et la forme **Cumulative**. |
| **[Coût Moyen Pondéré](weighted-average-cost.md)** | Le coût unitaire moyen d'un actif dans un portefeuille, pondéré par les quantités acquises. |

---

## ⚖️ Guide de comparaison des indicateurs

Pour vous aider à choisir le bon indicateur pour votre analyse, utilisez ce guide comparatif :

### 1. [Net Asset Value (NAV) / Valeur Nette](nav.md)
* **Question centrale :** « Combien vaut le portefeuille dans le périmètre sélectionné en ce moment précis ? »
* **Concept de la formule :** $\text{Valeur de Marché} + \text{Liquidité} + \text{Actifs en Transit}$ à la fin de la période.
* **Meilleur cas d'utilisation :** Instantané du patrimoine absolu à la date de fin sélectionnée (`date_to`).

### 2. [Valeur Comptable (Book Value)](book-value.md)
* **Question centrale :** « Combien la construction de mon portefeuille actuel a-t-elle coûté ? »
* **Concept de la formule :** $\text{Coût Positions Ouvertes} + \text{Liquidité} + \text{Coût en Transit}$ en utilisant le Coût Moyen Pondéré (CMP / WAC).
* **Meilleur cas d'utilisation :** Évaluer le capital engagé et le comparer à la valeur actuelle du marché (NAV) pour déterminer les plus-values latentes.

### 3. [P&L de la Période](period-pnl.md)
* **Question centrale :** « Combien d'argent ai-je réellement gagné ou perdu au cours de cette période ? »
* **Concept de la formule :** $\text{NAV}_{\text{end}} - \text{NAV}_{\text{start}} - \text{Flux Externes Nets}$.
* **Meilleur cas d'utilisation :** Mesurer les gains absolus de la période en devise réelle, indépendamment des dépôts et retraits de l'investisseur.

### 4. [Effet de timing](timing-effect.md)
* **Question centrale :** « Comment le moment et le montant de mes flux de trésorerie ont-ils affecté mon rendement global par rapport à une stratégie passive ? »
* **Concept de la formule :** $\text{MWRR}_{\text{cumulé}} - \text{TWRR}_{\text{cumulé}}$.
* **Meilleur cas d'utilisation :** Diagnostiquer si les dépôts et retraits ont apporté de la valeur ($>0$ pp) ou pesé sur la performance ($<0$ pp).

### 5. [ROI Simple](roi.md)
* **Question centrale :** « Combien ai-je gagné par rapport au capital net que j'ai investi ? »
* **Dénominateur de la formule :** Prix de Revient Moyen (PRM).
* **Limites :** Ne prend pas en compte le *moment* où les flux de trésorerie ont eu lieu, ce qui entraîne une dilution du ROI en cas d'achats successifs du même actif.

### 6. [TWRR (Taux de Rendement Pondéré par le Temps)](twrr.md)
* **Question centrale :** « Comment ma stratégie ou mon allocation d'actifs s'est-elle comportée, sans tenir compte du timing de mon épargne ? »
* **Concept de la formule :** Découpe la période à chaque flux de trésorerie, calcule les rendements des sous-périodes et les multiplie.
* **Meilleur cas d'utilisation :** Comparer votre performance à des indices de référence externes (comme le S&P 500) ou évaluer la performance intrinsèque des actifs choisis.

### 6. [MWRR Annualisé (Taux de Rendement Pondéré par les Capitaux)](mwrr.md#annualized-mwrr)
* **Question centrale :** « À quel taux annuel composé mon capital réel a-t-il progressé, compte tenu de mes dépôts et retraits ? »
* **Concept de la formule :** Détermine le taux de rendement interne ($r$) qui annule la valeur actuelle nette de tous les flux de trésorerie.
* **Meilleur cas d'utilisation :** Comparer votre performance personnelle à des taux d'intérêt à long terme ou évaluer la croissance composée sur de longues périodes. Peut être très volatile sur des périodes courtes.

### 7. [MWRR Cumulatif](mwrr.md#cumulative-mwrr)
* **Question centrale :** « Quel est le rendement cumulatif équivalent pondéré par les capitaux pour la période sélectionnée ? »
* **Concept de la formule :** Capitalise le MWRR annualisé sur le nombre réel de jours écoulés.
* **Meilleur cas d'utilisation :** Graphiques temporels et widgets du tableau de bord pour comparer visuellement les tendances de performance côte à côte avec le TWRR et le ROI.

---

## 💡 L'Exemple Pratique (TWRR vs MWRR vs ROI)

Voyons un exemple extrême pour comprendre comment le TWRR, le MWRR et le ROI Simple racontent des histoires différentes, mais mathématiquement correctes.

* **Mois 1 :** Vous achetez **1 000 €** d'une action. Le mois suivant, l'action double (+100 %). Vous avez maintenant **2 000 €**.
* **Mois 2 :** Vous déposez **100 000 €** de plus sur cette même action. Vous avez maintenant 102 000 € investis.
* **Mois 3 :** L'action baisse de **-10 %**. Votre capital total tombe à **91 800 €**.

Voici ce que LibreFolio calculera pour ce scénario :

### TWRR Cumulé : +80,00 %
Les actifs que vous avez choisis ont grimpé de +100 %, puis ont baissé de -10 %. Mathématiquement :

$$
(1 + 1{,}00) \times (1 - 0{,}10) - 1 = +80{,}00\%
$$

Cela isole la performance pure de l'action. Votre sélection d'actifs (*asset picking*) était excellente. Si vous aviez investi tout votre capital au premier jour, vous auriez obtenu un rendement de 80 %.

### ROI Simple : -9,11 %
Vous avez déposé un total de 101 000 € de votre poche (1 000 € + 100 000 €), mais vous ne détenez plus que 91 800 € aujourd'hui :

$$
ROI = \frac{91 800 - 101 000}{101 000} = -9{,}11\%
$$

Cela représente la perte ou le gain réel de votre portefeuille par rapport à votre capital net investi.

### MWRR Cumulé : -16,99 %
Comme vous avez déposé 100 000 € juste au sommet avant une baisse, votre timing a lourdement pénalisé votre rendement :

$$
\text{MWRR}_{\text{cumulatif}} \approx -16{,}99\%
$$

Ce rendement cumulé pondéré par les capitaux représente la performance d'un « euro théorique » soumis au timing de vos flux réels.

### MWRR Annualisé : -67,19 %
Puisque la baisse substantielle s'est produite sur une fenêtre de temps très courte (31 jours) sur une base de capital énorme (100 000 €), le taux annuel composé de perte est extrêmement élevé :

$$
\text{MWRR}_{\text{annualisé}} \approx -67{,}19\%
$$

Cela représente la vitesse annualisée de perte de capital sur cette fenêtre spécifique.

---

## ⚖️ Pourquoi LibreFolio affiche les deux côte à côte

En plaçant le TWRR et le MWRR l'un à côté de l'autre sur votre tableau de bord, LibreFolio vous donne un diagnostic comportemental immédiat :

* **TWRR > MWRR :** *« Vous choisissez de bons investissements, mais votre timing est mauvais. Vous achetez probablement au plus haut (FOMO) et faites baisser vos rendements personnels. »*
* **MWRR > TWRR :** *« Vous avez un excellent timing ! Vous achetez des actifs avec une décote lorsque le marché chute, augmentant vos rendements personnels au-dessus de la moyenne du marché. »*

---

## 🔗 Intégration UI et liens d'aide du tableau de bord

Pour faciliter la navigation, le tableau de bord de LibreFolio propose des icônes et des liens d'aide à côté de chaque indicateur. Cliquer sur ces liens vous redirige directement vers le chapitre d'explication financière correspondant :

* Les widgets de la **Valeur Nette (NAV)** renvoient directement à la [Page du NAV / Net Worth](nav.md).
* Les champs de la **Valeur Comptable** renvoient directement à la [Page de la Valeur Comptable](book-value.md).
* Les widgets du **P&L de la Période** renvoient directement à la [Page du P&L de la Période](period-pnl.md).
* Les widgets de l'**Effet de timing** renvoient directement à la [Page de l'Effet de timing](timing-effect.md).
* Les widgets du **ROI** renvoient directement à la [Page du ROI Simple](roi.md).
* Les widgets du **TWRR** renvoient directement à la [Page du TWRR](twrr.md).
* Les widgets du **MWRR** renvoient directement à la [Page du MWRR](mwrr.md).
