# 📈 Métriques de Performance

Lors de l'évaluation du succès d'un portefeuille d'investissement, regarder uniquement le solde total ou le profit absolu ne suffit pas. Pour véritablement comprendre la performance, vous avez besoin de métriques standardisées qui répondent à différentes questions : « Comment mes actifs ont-ils performé ? », « Quelle a été la qualité de mon timing ? », et « Quel est le rendement de cette opération spécifique ? ».

---

## 🎭 Les Deux Acteurs de Votre Portefeuille

Pour comprendre pourquoi plusieurs métriques existent, imaginez qu'il y a deux « acteurs » différents qui gèrent votre patrimoine :

1. **Le Marché (Les Actifs) :** Fait varier (à la hausse ou à la baisse) le prix des actifs que vous possédez.
2. **Vous (L'Investisseur) :** Décide *quand* déposer ou retirer de l'argent du portefeuille.

Ces deux acteurs peuvent avoir des performances très différentes. Vous pourriez choisir une excellente action (Le Marché performe bien), mais vous pourriez l'acheter au sommet juste avant un krach (Vous performez mal). LibreFolio utilise différentes métriques pour isoler ces deux comportements.

---

## 📚 Sujets de ce Chapitre

Les métriques de performance de LibreFolio sont organisées autour de trois moteurs de calcul. Chacun a sa propre page d'aperçu avec le modèle mathématique complet.

### ⚙️ Moteur de Portefeuille

Comptabilité agrégée basée sur le PMP pour l'ensemble du portefeuille (ou toute portée courtier/actif).

| Métrique / Concept | Description |
|------------------|-------------|
| **[Aperçu du Moteur de Portefeuille](portfolio-engine/index.md)** | Modèle mathématique complet : chaîne d'évaluation, PMP, agrégation, modèle à 3 pools, contribution, architecture pré-cadre/cadre. |
| **[Valeur Liquidative (NAV)](portfolio-engine/nav.md)** | Valorisation boursière totale du portefeuille (actifs + cash + en transit). Utilise la chaîne d'évaluation : Prix du Marché → Dernier Prix d'Achat → Manquant. |
| **[Valeur Comptable](portfolio-engine/book-value.md)** | Coût historique comptable des positions ouvertes (PMP × qté) plus le cash. La différence avec la NAV = P&L latent. |
| **[P&L de Période](portfolio-engine/period-pnl.md)** | Profit/perte monétaire ajusté des flux de trésorerie sur une fenêtre. Se décompose en : delta latent + réalisé + revenus − frais. Inclut l'attribution de contribution par actif. |
| **[Capital Déposé & P&L Total](portfolio-engine/deposited-capital.md)** | Capital externe net depuis la création. Documente le modèle de décomposition de trésorerie **basé sur les événements à 3 pools** (K, R, W) avec des règles de mise à jour formelles au niveau des transactions. |
| **[Effet de Timing](portfolio-engine/timing-effect.md)** | Différence entre le MWRR Cumulé et le TWRR Cumulé — quantifie l'impact du timing des flux de trésorerie sur les rendements. |
| **[ROI Simple](portfolio-engine/roi.md)** | Rendement en pourcentage par rapport au capital net investi. Simple mais sujet à la dilution des flux de trésorerie. |
| **[TWRR](portfolio-engine/twrr.md)** | Taux de Rendement Pondéré dans le Temps. Performance pure des actifs/stratégies, neutralisant le timing des dépôts/retraits. |
| **[MWRR (XIRR)](portfolio-engine/mwrr.md)** | Taux de Rendement Pondéré par l'Argent. Performance personnelle de l'investisseur tenant compte du timing des flux de trésorerie. Formes annualisées et cumulatives. |

### 🔬 Moteur FIFO

Comptabilité par lot : suit chaque lot d'acquisition à travers son propre cycle de vie au lieu de le fusionner en une seule moyenne.

| Métrique / Concept | Description |
|------------------|-------------|
| **[Aperçu du Moteur FIFO](fifo-engine/index.md)** | États du cycle de vie des lots, traitement chronologique des événements, appariement FIFO, divisions et transferts entre courtiers. |
| **[Analyse des Lots FIFO](fifo-engine/fifo-lot-analysis.md)** | Complément par lot au PMP : suit chaque lot d'acquisition à travers son propre cycle de vie, apparie les ventes dans l'ordre FIFO et calcule le rendement ouvert/total par lot. |

### 📊 Moyen Pondéré (PMP)

| Métrique / Concept | Description |
|------------------|-------------|
| **[Prix Moyen Pondéré (PMP)](weighted-average-cost.md)** | PMP itératif tenant compte des stocks par position (courtier, actif). Calculé en ligne pendant la boucle quotidienne du moteur. |

---

## ⚖️ Guide de Comparaison des Métriques

Pour vous aider à choisir la métrique appropriée pour votre analyse, utilisez ce guide de comparaison :

### 💼 . [Valeur Liquidative (NAV) / Valeur Nette](portfolio-engine/nav.md)
* **Question Centrale :** « Quelle est la valeur actuelle du portefeuille dans la portée sélectionnée ? »
* **Concept de Formule :** $\text{Valeur de Marché} + \text{Cash} + \text{Actifs en Transit}$ à la fin de la période.
* **Meilleur Cas d'Utilisation :** Instantané de la richesse absolue à la date de fin sélectionnée (`date_to`).

### 📖 . [Valeur Comptable](portfolio-engine/book-value.md)
* **Question Centrale :** « Combien a coûté la construction de mon portefeuille actuel ? »
* **Concept de Formule :** $\text{Base de Coût Ouvert} + \text{Cash} + \text{Valeur Comptable en Transit}$ en utilisant le prix moyen pondéré (PMP).
* **Meilleur Cas d'Utilisation :** Évaluation des coûts d'acquisition et comparaison avec la valeur de marché actuelle (NAV) pour trouver les gains latents.

### 📊 . [P&L de Période](portfolio-engine/period-pnl.md)
* **Question Centrale :** « Combien d'argent ai-je réellement gagné ou perdu pendant cette période ? »
* **Concept de Formule :** $\text{NAV}_{\text{fin}} - \text{NAV}_{\text{début}} - \text{Flux Externes Nets}$.
* **Meilleur Cas d'Utilisation :** Mesure des gains de période en devise absolue, indépendamment des injections/retraits de cash de l'investisseur.

### ⏱️ . [Effet de Timing](portfolio-engine/timing-effect.md)
* **Question Centrale :** « Comment le timing et la taille de mes flux de trésorerie ont-ils affecté mon rendement global par rapport à une stratégie d'achat et de détention ? »
* **Concept de Formule :** $\text{MWRR}_{\text{cumulé}} - \text{TWRR}_{\text{cumulé}}$.
* **Meilleur Cas d'Utilisation :** Diagnostiquer si les dépôts et retraits ont ajouté de la valeur ($>0$ pp) ou freiné la performance ($<0$ pp).

### 📉 . [ROI Simple](portfolio-engine/roi.md)
* **Question Centrale :** « Combien ai-je gagné par rapport au capital net que j'ai investi ? »
* **Dénominateur de la Formule :** Prix moyen pondéré (PMP).
* **Limitations :** Ne tient pas compte du *moment* où les flux de trésorerie ont eu lieu, conduisant à une dilution des flux de trésorerie lors de l'achat ultérieur de plus d'un actif.

### ⏱️ . [TWRR (Taux de Rendement Pondéré dans le Temps)](portfolio-engine/twrr.md)
* **Question Centrale :** « Comment ma stratégie/allocation d'actifs choisie a-t-elle performé, sans tenir compte de mon timing de cash ? »
* **Concept de Formule :** Divise la chronologie à chaque flux de trésorerie, calcule les rendements des sous-périodes et les multiplie.
* **Meilleur Cas d'Utilisation :** Comparer votre performance avec des indices de référence externes (comme le S&P 500) ou évaluer la performance pure des actifs.

### 📈 . [MWRR Annualisé (Money-Weighted Rate of Return)](portfolio-engine/mwrr.md#annualized-mwrr)
* **Question Centrale :** « À quel taux annuel composé mon capital réel a-t-il augmenté, en tenant compte de mes dépôts et retraits ? »
* **Concept de Formule :** Résout le taux de rendement interne ($r$) qui ramène la valeur actuelle nette de tous les flux de trésorerie à zéro.
* **Meilleur Cas d'Utilisation :** Comparer votre performance personnelle aux taux d'intérêt à long terme ou évaluer la croissance composée sur de longs horizons. Peut être très volatil sur de courtes fenêtres.

### 📊 . [MWRR Cumulé](portfolio-engine/mwrr.md#cumulative-mwrr)
* **Question Centrale :** « Quel est le rendement cumulé équivalent pondéré par l'argent sur cette fenêtre temporelle sélectionnée ? »
* **Concept de Formule :** Compose le MWRR annualisé pour le nombre réel de jours écoulés.
* **Meilleur Cas d'Utilisation :** Graphiques en série et widgets de tableau de bord pour comparer visuellement les tendances de performance côte à côte avec le TWRR et le ROI.

---

## 💡 L'Exemple Pratique (TWRR vs MWRR vs ROI)

Regardons un exemple extrême pour voir comment le TWRR, le MWRR et le ROI Simple racontent des histoires différentes, mais mathématiquement correctes.

* **Mois 1 :** Vous achetez **1 000 €** d'une action. Le mois suivant, l'action double (+100 %). Vous avez maintenant **2 000 €**.
* **Mois 2 :** Vous déposez **100 000 €** supplémentaires dans la même action. Vous avez maintenant 102 000 € investis.
* **Mois 3 :** L'action chute de **-10 %**. Votre capital total tombe à **91 800 €**.

Voici ce que LibreFolio calculera pour ce scénario :

### 📊 Cumulé : +80,00 %
Les actifs que vous avez choisis ont augmenté de +100 %, puis ont chuté de -10 %. Mathématiquement :

$$
(1 + 1,00) \times (1 - 0,10) - 1 = +80,00\%
$$

Cela isole la performance pure de l'action. Votre *sélection d'actifs* était excellente. Si vous aviez investi tout votre argent le premier jour, vous auriez réalisé un rendement de 80 %.

### 📉 Simple : -9,11 %
Vous avez déposé un total de 101 000 € de votre propre poche (1 000 € + 100 000 €), mais vous détenez actuellement 91 800 € :

$$
ROI = \frac{91 800 - 101 000}{101 000} = -9,11\%
$$

Cela représente votre gain/perte réel et brut par rapport à votre capital net investi.

### 💵 Cumulé : -16,99 %
Parce que vous avez déposé 100 000 € juste au sommet avant une chute, votre timing a considérablement freiné votre rendement :

$$
\text{MWRR}_{\text{cumulé}} \approx -16,99\%
$$

Ce rendement cumulé pondéré par l'argent représente la performance d'un « euro théorique » sous votre timing de flux de trésorerie réel.

### 📈 Annualisé : -67,19 %
Étant donné que la baisse substantielle s'est produite sur une très courte fenêtre temporelle (31 jours) sur une base de capital massive (100 000 €), le taux de perte annuel composé est très élevé :

$$
\text{MWRR}_{\text{annualisé}} \approx -67,19\%
$$

Cela représente la vitesse annualisée de la perte de capital sur cette fenêtre spécifique.

---

## ⚖️ Pourquoi LibreFolio affiche les deux côte à côte

En plaçant le TWRR et le MWRR l'un à côté de l'autre sur votre Tableau de Bord, LibreFolio vous donne un diagnostic comportemental immédiat :

* **TWRR > MWRR :** *« Vous choisissez de bons investissements, mais votre timing est mauvais. Vous achetez probablement au sommet (FOMO) et freinez vos rendements personnels. »*
* **MWRR > TWRR :** *« Vous avez un excellent timing ! Vous achetez des actifs à prix réduit lorsque le marché baisse, ce qui booste vos rendements personnels au-dessus de la moyenne du marché. »*

---

## 🔗 Intégration UI & Liens d'Aide du Tableau de Bord

Pour faciliter la navigation, le tableau de bord de LibreFolio propose des icônes d'aide et des liens à côté de chaque métrique. Cliquer sur ces liens vous redirige directement vers le chapitre de théorie financière pertinent :

* Les widgets **Valeur Nette (NAV)** sont liés directement à la [Page NAV / Valeur Nette](portfolio-engine/nav.md).
* Les champs **Valeur Comptable** sont liés directement à la [Page Valeur Comptable](portfolio-engine/book-value.md).
* Les widgets **P&L de Période** sont liés directement à la [Page P&L de Période](portfolio-engine/period-pnl.md).
* Les widgets **Effet de Timing** sont liés directement à la [Page Effet de Timing](portfolio-engine/timing-effect.md).
* Les widgets **ROI** sont liés directement à la [Page ROI Simple](portfolio-engine/roi.md).
* Les widgets **TWRR** sont liés directement à la [Page TWRR](portfolio-engine/twrr.md).
* Les widgets **MWRR** sont liés directement à la [Page MWRR](portfolio-engine/mwrr.md).
* **Capital Déposé / P&L Total** (infobulle du Graphique de Croissance) est lié à la [Page Capital Déposé & P&L Total](portfolio-engine/deposited-capital.md).
| **[Résolution des Prix](portfolio-engine/price-resolution.md)** | Niveaux de résolution unifiés : MARKET → TRADE_AVG → CARRIED → MISSING, avec cours natifs et FX par date. |
| **[Rendement Annualisé Net](portfolio-engine/net-annualized-return.md)** | Définitions CAGR net pour positions, contribution de la période et lots FIFO, avec fenêtre minimale de 30 jours. |
