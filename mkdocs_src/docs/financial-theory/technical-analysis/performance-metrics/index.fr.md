# 📈 Métriques de performance

Lors de l'évaluation du succès d'un portefeuille d'investissement, se contenter de regarder le solde total ou le profit absolu ne suffit pas. Pour véritablement comprendre la performance, vous avez besoin de métriques standardisées qui répondent à différentes questions : « Comment mes actifs ont-ils performé ? », « Quelle était la qualité de mon timing ? » et « Quel est le rendement de cette transaction spécifique ? ».

---

## 🎭 Les deux acteurs de votre portefeuille

Pour comprendre pourquoi plusieurs métriques existent, imaginez qu'il y a deux « acteurs » différents qui gèrent votre patrimoine :

1. **Le Marché (Les Actifs) :** Fait monter ou descendre les prix des choses que vous possédez.
2. **Vous (L'Investisseur) :** Décidez *quand* déposer ou retirer de l'argent du portefeuille.

Ces deux acteurs peuvent avoir des performances très différentes. Vous pourriez choisir une excellente action (Le Marché performe bien), mais l'acheter au sommet, juste avant un krach (Vous performez mal). LibreFolio utilise différentes métriques pour isoler ces deux comportements.

---

## 📚 Sujets de ce chapitre

Les métriques de performance de LibreFolio sont organisées autour de trois moteurs de calcul. Chacun possède sa propre page d'aperçu avec le modèle mathématique complet.

### ⚙️ Moteur de portefeuille

Comptabilité agrégée basée sur le PMP pour l'ensemble du portefeuille (ou tout périmètre courtier/actif).

| Métrique / Concept | Description |
|------------------|-------------|
| **[Aperçu du moteur de portefeuille](portfolio-engine/index.md)** | Modèle mathématique complet : résolveur de prix unifié, PMP, agrégation, modèle à 3 pools, contribution, architecture pre-frame/frame. |
| **[Résolution des prix](portfolio-engine/price-resolution.md)** | Niveaux du résolveur unifié : MARKET → TRADE_AVG → CARRIED → MISSING, avec valorisations natives et FX par date. |
| **[Valeur nette d'inventaire (NAV)](portfolio-engine/nav.md)** | Valorisation totale au prix du marché du portefeuille (actifs + liquidités + en transit), à l'aide du résolveur unifié. |
| **[Valeur comptable](portfolio-engine/book-value.md)** | Coût comptable historique des positions ouvertes (PMP × quantité) plus les liquidités. La différence avec la NAV = P&L non réalisé. |
| **[P&L de période](portfolio-engine/period-pnl.md)** | Profit/perte monétaire ajusté des flux de trésorerie sur une fenêtre. Se décompose en : delta non réalisé + réalisé + revenus − frais. Inclut l'attribution de contribution par actif. |
| **[Capital déposé et P&L total](portfolio-engine/deposited-capital.md)** | Capital externe net depuis la création. Documente le modèle de décomposition de trésorerie **événementiel à 3 pools** (K, R, W) avec des règles de mise à jour formelles au niveau des transactions. |
| **[Effet de timing](portfolio-engine/timing-effect.md)** | Différence entre le MWRR cumulé et le TWRR cumulé — quantifie l'impact du timing des flux de trésorerie sur les rendements. |
| **[ROI simple](portfolio-engine/roi.md)** | Rendement en pourcentage par rapport au capital net investi. Simple mais sujet à la dilution des flux de trésorerie. |
| **[Rendement net annualisé](portfolio-engine/net-annualized-return.md)** | Définitions du CAGR net pour les positions, la contribution de période et les lots FIFO, avec une fenêtre minimale de 30 jours. |
| **[TWRR](portfolio-engine/twrr.md)** | Taux de rendement pondéré en fonction du temps. Performance pure des actifs/stratégie, neutralisant le timing des dépôts/retraits. |
| **[MWRR (XIRR)](portfolio-engine/mwrr.md)** | Taux de rendement pondéré par les capitaux. Performance personnelle de l'investisseur tenant compte du timing des flux de trésorerie. Formes annualisée et cumulée. |

### 🔬 Moteur FIFO

Comptabilité par lot : suit chaque lot d'acquisition à travers son propre cycle de vie au lieu de le fusionner en une moyenne unique.

| Métrique / Concept | Description |
|------------------|-------------|
| **[Aperçu du moteur FIFO](fifo-engine/index.md)** | États du cycle de vie des lots, traitement chronologique des événements, appariement FIFO, divisions et transferts entre courtiers. |
| **[Analyse des lots FIFO](fifo-engine/fifo-lot-analysis.md)** | Complément par lot au PMP : suit chaque lot d'acquisition à travers son propre cycle de vie, apparie les ventes dans l'ordre FIFO et calcule le rendement ouvert/total par lot. |

### 📊 Prix moyen pondéré (PMP)

| Métrique / Concept | Description |
|------------------|-------------|
| **[Prix moyen pondéré (PMP)](weighted-average-cost.md)** | PMP itératif tenant compte de l'inventaire par position (courtier, actif). Calculé directement dans la boucle quotidienne du moteur. |

---

## ⚖️ Guide de comparaison des métriques

Pour vous aider à choisir la métrique adaptée à votre analyse, utilisez ce guide de comparaison :

### 💼 1. [Valeur nette d'inventaire (NAV) / Valeur nette](portfolio-engine/nav.md)
* **Question Clé :** « Combien vaut actuellement le portefeuille dans le périmètre sélectionné ? »
* **Concept de Formule :** $\text{Valeur de Marché} + \text{Liquidités} + \text{Actifs en Transit}$ à la fin de la période.
* **Meilleur Cas d'Usage :** Instantané de la richesse absolue à la date de fin sélectionnée (`date_to`).

### 📖 2. [Valeur comptable](portfolio-engine/book-value.md)
* **Question Clé :** « Combien m'a coûté la construction de mon portefeuille actuel ? »
* **Concept de Formule :** $\text{Base de Coût Ouverte} + \text{Liquidités} + \text{Valeur Comptable en Transit}$ en utilisant le prix moyen pondéré (PMP).
* **Meilleur Cas d'Usage :** Évaluer les coûts d'acquisition et comparer avec la valeur de marché actuelle (NAV) pour identifier les gains latents.

### 📊 3. [P&L de période](portfolio-engine/period-pnl.md)
* **Question Clé :** « Combien d'argent ai-je réellement gagné ou perdu durant cette période ? »
* **Concept de Formule :** $\text{NAV}_{\text{fin}} - \text{NAV}_{\text{début}} - \Delta\text{CapitalBaseline}$.
* **Meilleur Cas d'Usage :** Mesurer les gains de période en termes monétaires absolus, indépendamment des injections/retraits de liquidités de l'investisseur.

### ⏱️ 4. [Effet de timing](portfolio-engine/timing-effect.md)
* **Question Clé :** « Comment le timing et l'ampleur de mes flux de trésorerie ont-ils affecté mon rendement global par rapport à une stratégie d'achat et de conservation ? »
* **Concept de Formule :** $\text{MWRR}_{\text{cumulé}} - \text{TWRR}_{\text{cumulé}}$.
* **Meilleur Cas d'Usage :** Diagnostiquer si les dépôts et retraits ont ajouté de la valeur ($>0$ pp) ou ont fait baisser la performance ($<0$ pp).

### 📉 5. [ROI simple](portfolio-engine/roi.md)
* **Question Clé :** « Combien ai-je gagné par rapport au capital net que j'ai investi ? »
* **Dénominateur de la Formule :** Base de capital, y compris le capital en nature valorisé.
* **Limitations :** Ne tient pas compte du *moment* où les flux de trésorerie ont eu lieu, ce qui entraîne une dilution des flux de trésorerie lors de l'achat ultérieur de quantités supplémentaires d'un actif.

### ⏱️ 6. [TWRR (Taux de rendement pondéré en fonction du temps)](portfolio-engine/twrr.md)
* **Question Clé :** « Comment mon allocation d'actifs/stratégie choisie a-t-elle performé, en ignorant le timing de mes liquidités ? »
* **Concept de Formule :** Découpe la chronologie à chaque flux de trésorerie, calcule les rendements de sous-périodes et les multiplie.
* **Meilleur Cas d'Usage :** Comparer votre performance avec des benchmarks externes (comme le S&P 500) ou évaluer la performance pure des actifs.

### 📈 7. [MWRR annualisé (Taux de rendement pondéré par les capitaux)](portfolio-engine/mwrr.md#annualized-mwrr)
* **Question Clé :** « À quel taux annuel composé mon capital réel a-t-il augmenté, en tenant compte de mes dépôts et retraits ? »
* **Concept de Formule :** Détermine le taux de rendement interne ($r$) qui ramène la valeur actuelle nette de tous les flux de trésorerie à zéro.
* **Meilleur Cas d'Usage :** Comparer votre performance personnelle aux taux d'intérêt à long terme ou évaluer la croissance composée sur de longs horizons. Peut être très volatil sur de courtes fenêtres.

### 📊 8. [MWRR cumulé](portfolio-engine/mwrr.md#cumulative-mwrr)
* **Question Clé :** « Quel est le rendement cumulé équivalent, pondéré par les capitaux, sur cette fenêtre temporelle sélectionnée ? »
* **Concept de Formule :** Compose le MWRR annualisé pour le nombre réel de jours écoulés.
* **Meilleur Cas d'Usage :** Graphiques de séries chronologiques et widgets de tableau de bord pour comparer visuellement les tendances de performance côte à côte avec le TWRR et le ROI.

---

## 💡 L'exemple pratique (TWRR vs MWRR vs ROI)

Prenons un exemple extrême pour voir comment le TWRR, le MWRR et le ROI simple racontent des histoires différentes, mais mathématiquement correctes.

* **Mois 1 :** Vous achetez **1 000 €** d'une action. Le mois suivant, l'action double (+100 %). Vous avez maintenant **2 000 €**.
* **Mois 2 :** Vous déposez **100 000 €** supplémentaires dans exactement la même action. Vous avez maintenant 102 000 € investis.
* **Mois 3 :** L'action baisse de **-10 %**. Votre capital total chute à **91 800 €**.

Voici ce que LibreFolio calculera pour ce scénario :

### 📊 TWRR cumulé : +80,00 %

Les actifs que vous avez choisis ont augmenté de +100 %, puis ont baissé de 10 %. Mathématiquement :

$$
(1 + 1{,}00) \times (1 - 0{,}10) - 1 = +80{,}00\%
$$

Cela isole la performance pure de l'action. Votre *sélection d'actifs* était excellente. Si vous aviez investi tout votre argent le premier jour, vous auriez réalisé un rendement de 80 %.

### 📉 ROI simple : -9,11 %

Vous avez déposé un total de 101 000 € de votre propre poche (1 000 € + 100 000 €), mais vous détenez actuellement 91 800 € :

$$
ROI = \frac{91\,800 - 101\,000}{101\,000} = -9{,}11\%
$$

Cela représente votre gain/perte réel et brut par rapport à votre capital net investi.

### 💵 MWRR cumulé : -16,99 %

Parce que vous avez déposé 100 000 € juste au sommet avant une chute, votre timing a considérablement fait baisser votre rendement :

$$
\text{MWRR}_{\text{cumulé}} \approx -16{,}99\%
$$

Ce rendement cumulé pondéré par les capitaux représente la performance d'un « euro théorique » selon le timing réel de vos flux de trésorerie.

### 📈 MWRR annualisé : -67,19 %

Étant donné que la chute substantielle s'est produite sur une fenêtre temporelle très courte (31 jours) sur une base de capital massive (100 000 €), le taux de perte composé annualisé est très élevé :

$$
\text{MWRR}_{\text{annualisé}} \approx -67{,}19\%
$$

Cela représente la vitesse annualisée de perte de capital sur cette fenêtre spécifique.

---

## ⚖️ Pourquoi LibreFolio affiche les deux côte à côte

En plaçant le TWRR et le MWRR côte à côte sur votre tableau de bord, LibreFolio vous offre un diagnostic comportemental immédiat :

* **TWRR > MWRR :** *« Vous choisissez de bons investissements, mais votre timing est mauvais. Vous achetez probablement au sommet (FOMO) et faites baisser vos rendements personnels. »*
* **MWRR > TWRR :** *« Vous avez un excellent timing ! Vous achetez des actifs à décote lorsque le marché chute, ce qui propulse vos rendements personnels au-dessus de la moyenne du marché. »*

---

## 🔗 Intégration de l'UI et liens d'aide du tableau de bord

Pour faciliter la navigation, les trois cartes KPI du tableau de bord LibreFolio — **P&L de période**, **Rendements** et **Valeur nette** — comportent chacune une icône d'aide. L'accès à ces chapitres théoriques se fait en deux étapes :

1. L'icône d'aide ouvre la section correspondante de la page [Cartes KPI](../../../user/dashboard/kpi-cards.md) du guide utilisateur ([Carte 1](../../../user/dashboard/kpi-cards.md#card-1-period-pl), [Carte 2](../../../user/dashboard/kpi-cards.md#card-2-returns), [Carte 3](../../../user/dashboard/kpi-cards.md#card-3-net-worth)).
2. De là, chaque métrique renvoie à son chapitre de théorie financière : [P&L de période](portfolio-engine/period-pnl.md), [Valeur comptable](portfolio-engine/book-value.md), [ROI](portfolio-engine/roi.md), [TWRR](portfolio-engine/twrr.md), [MWRR](portfolio-engine/mwrr.md), [Effet de timing](portfolio-engine/timing-effect.md), [NAV / Valeur nette](portfolio-engine/nav.md), [Capital déposé et P&L total](portfolio-engine/deposited-capital.md).

Ailleurs dans l'application, l'aperçu du PMP dans le formulaire de transaction renvoie directement au chapitre [Prix moyen pondéré (PMP)](weighted-average-cost.md), et chaque signal/indicateur de graphique renvoie à sa propre page de théorie.
