# 🔍 Positions & Analyse

L'onglet **Positions** du tableau de bord vous permet d'inspecter les positions ouvertes, d'analyser les performances et d'explorer les lots correspondants selon la méthode FIFO.

<div class="lf-screenshot-carousel" data-carousel="carousel-positions-views" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="positions-holdings-table" data-title="📋 Holdings (Table)" alt="Holdings Table View">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-holdings-map" data-title="🗺️ Holdings (Map / Treemap)" alt="Holdings Map View">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-table" data-title="📈 Performance (Table)" alt="Performance Table View">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-map" data-title="📊 Performance (Map / Chart)" alt="Performance Map View">
</div>

---

## 🔍 Onglet Positions

L'onglet **Positions** a deux modes sémantiques : **Positions** et **Performance**.

Utilisez le sélecteur de vue pour passer de l'un à l'autre, et le bascule tableau/carte pour changer la présentation visuelle.

#### 📋 Vue Positions

La vue **Positions** montre l'instantané des positions ouvertes. Le tableau comporte 13 colonnes :

| Colonne | Description |
|:---|:---|
| **Actif** | Nom de l'actif avec l'icône du type — cliquez pour ouvrir la page de détail de l'actif. |
| **Δ1** | Variation du P&L latent par rapport à hier, à quantité du jour constante. |
| **Δ1%** | La même variation quotidienne en pourcentage de la valeur de marché de la position d'hier. |
| **P&L latent** | Gain/perte ouvert : valeur actuelle moins le coût résiduel. |
| **P&L %** | P&L latent en pourcentage du coût résiduel. |
| **Annualisé** | Rendement net annualisé (CAGR) des lots encore ouverts, de la première transaction à aujourd'hui — pour comparer des positions détenues sur des durées différentes. |
| **Valeur** | Valeur totale aux prix de marché courants (\(\text{Prix} \times \text{Quantité}\)). |
| **Poids** | Part proportionnelle de cette position par rapport à la valeur totale du portefeuille. |
| **Qté** | Actions, unités ou pièces actuellement détenues. |
| **Courtiers** | Compte(s) courtier détenant la position. |
| **Prix** *(masquée par défaut)* | Prix actuel de l'actif fourni par le fournisseur connecté. |
| **Coût Moyen** *(masquée par défaut)* | Coût moyen par unité de la position actuellement ouverte (Prix Moyen de Revient). |
| **Lot ouvert le plus ancien** *(masquée par défaut)* | Date d'ouverture du plus ancien lot FIFO encore ouvert pour cette position. |

Utilisez l'**icône en forme d'œil** dans la barre d'outils du tableau pour afficher ou masquer des colonnes — vos choix sont mémorisés d'une session à l'autre.

#### 📈 Vue Performance

La vue **Performance** se charge à la demande et montre ensemble les positions ouvertes et clôturées. Dans le tableau/la carte, le **Statut** est filtrable à l'intérieur du composant, pas via un sélecteur de premier niveau.

#### 🗺️ Style Visuel : Tableau vs. Carte

| Mode Visuel | Fonctionnalités Principales | Cas d'Utilisation Optimal |
|:---|:---|:---|
| **📋 Vue Tableau** | • Grille triable<br>• Valeurs numériques précises<br>• Tri rapide des colonnes | Comptabilité standard, recherche de quantités d'actifs spécifiques ou comparaison des valeurs PMP. |
| **🗺️ Vue Carte** | • Visualisation Treemap<br>• La taille indique le poids de l'actif<br>• L'intensité de la couleur indique la performance (vert = gain, rouge = perte) | Diagnostics visuels rapides, repérage de la sur-allocation ou identification des actifs sous-performants. |

---

## 🔬 Analyse des Lots FIFO {: #fifo-lots-analysis }

Lorsque vous cliquez sur une position dans la vue Tableau ou Carte, LibreFolio développe un panneau **Analyse des Lots FIFO** directement **en dessous** de la vue Positions. Il utilise une transition de diapositive verticale et défile automatiquement pour être visible — ce n'est **pas** un panneau coulissant sur le côté droit. Si nécessaire, une bannière de qualité des données apparaît en premier, puis les blocs d'analyse restent dans cet ordre : PMP / Cours de marché, Durée de vie & Conservation des lots, tableau unifié des lots, comparaison Valeur / Rendement, et la fenêtre modale de détail du lot. Par défaut, sans sélection explicite, **tous les lots actuellement visibles** sont inclus dans les graphiques liés.

<div class="lf-screenshot-carousel" data-carousel="carousel-fifo-lots-analysis" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="fifo-lots-panel" data-title="🔍 Overview" alt="FIFO Lots Analysis Overview">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-wac-chart" data-title="📈 WAC / Market Price" alt="WAC and Market Price Chart">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-gantt-chart" data-title="🕒 Lot Life & Custody" alt="Lot Life and Custody Gantt Chart">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-table" data-title="📋 Unified Lots Table" alt="Unified Lots Table">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart" data-title="💰 Value Comparison" alt="Value Comparison Chart">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart-return" data-title="📊 Return Comparison" alt="Return Comparison Chart">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-custody-modal" data-title="🧾 Lot Detail Modal" alt="Lot Detail Modal">
</div>

### 1. PMP / Cours de marché

Ce premier graphique compare le **Cours de marché** de l'actif avec les lignes **PMP** par courtier et la ligne PMP combinée pour la position sélectionnée.

- Utilisez l'interrupteur **ABS / %** pour basculer entre les prix absolus et l'évolution en pourcentage depuis le début de la période.
- En mode **ABS**, basculez **Auto / À partir de 0** pour choisir si l'axe Y est ajusté automatiquement ou forcé à démarrer à zéro.
- Les marqueurs d'événements et les bulles de performance des lots vous aident à relier les achats, ventes, transferts, divisions et événements de revenus à l'historique de la base de coût.
- Cliquer sur les bulles de lots met à jour la sélection partagée de lots utilisée par les autres blocs.
- **La couleur des bulles** correspond au **courtier d'ouverture** du lot — les mêmes couleurs utilisées par les barres de conservation dans le bloc 2 ci-dessous.
- **La taille des bulles** reflète la **valeur d'ouverture** du lot (sa base de coût d'origine) : les bulles plus grosses correspondent à des investissements initiaux plus importants.
- **Un bord de bulle en tirets** marque un lot actuellement affiché **au coût** car aucun cours de marché en direct n'est encore disponible pour celui-ci.

🔗 **Théorie** : Reportez-vous à **[Prix Moyen Pondéré (PMP)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)** pour les règles de base de coût, et à **[Chaîne de Prix d'Évaluation](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md#valuation-price-chain)** pour comprendre comment les cours de marché sont déterminés.

### 2. Durée de vie & Conservation des Lots

Le bloc **Durée de vie & Conservation des lots** est une chronologie de type Gantt montrant quand chaque lot était ouvert et où il était détenu au fil du temps.

- Utilisez le filtre **Ouvert / Fermé** pour afficher uniquement les lots ouverts, uniquement les lots fermés, ou les deux.
- Chaque barre représente la durée de vie d'un lot ; les transferts créent des voies de conservation supplémentaires afin que vous puissiez voir les mouvements entre courtiers et les périodes de transit.
- **La couleur de la barre** identifie le **courtier de conservation** détenant actuellement ce segment du lot — les badges de courtier correspondants sont listés dans la légende située sous le graphique. Un segment violet en tirets marque une période **en transit** entre les courtiers (transfert initié mais pas encore arrivé).
- **L'épaisseur de la barre** est proportionnelle à la **quantité détenue** pendant ce segment exact — un lot qui a été partiellement vendu ou divisé montre des barres plus fines par la suite.
- Cliquer sur une barre sélectionne ce lot dans l'analyse partagée ; un double-clic peut ramener à la ligne correspondante dans le tableau.

🔗 **Théorie** : Voir **[Moteur FIFO — Cycle de vie des lots & Modèle d'appariement](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/index.md)** pour comprendre comment les états des lots, les divisions et les transferts entre courtiers sont définis.

### 3. Tableau Unifié des Lots

v3 remplace les anciens tableaux séparés **Lots ouverts** et **Lots fermés** par un **tableau unifié**.

- Le tableau montre l'ensemble actuel des lots avec des colonnes telles que la date d'ouverture, le rendement total, la valeur actuelle, la conservation et le **Statut**.
- Le filtrage partagé signifie que le tableau reflète toujours le même ensemble de lots visibles que les graphiques ci-dessus.
- Le menu **Actions** de chaque ligne comprend :
 - **Voir le détail du lot**
 - **Aller au lot dans le Gantt**
 - **Aller à la transaction d'ouverture**
 - **Copier l'identifiant du lot**

### 4. Comparaison Valeur / Rendement

Ce graphique de comparaison se concentre sur les lots actuellement sélectionnés dans le panneau. Si vous n'avez pas sélectionné de lots spécifiques, il utilise **tous les lots visibles**.

- Basculez entre **Valeur** et **Rendement** à l'aide de l'interrupteur de mode en haut à droite.
- Le mode **Valeur** compare les lots sélectionnés en termes monétaires absolus et propose également le bouton à bascule **Auto / À partir de 0** pour l'axe Y.
- Le mode **Rendement** compare le pourcentage de rendement de chaque lot depuis sa date d'ouverture sur le même ensemble de lots sélectionnés.

### 5. Fenêtre Modale Détail du Lot

Choisissez **Voir le détail du lot** dans les actions de la ligne du tableau pour ouvrir la fenêtre modale **Détail du Lot FIFO** pour un lot spécifique.

- Le résumé comprend le **P&L total**, le **Rendement total**, les **Revenus de l'actif**, le **Rendement en cash**, le P&L FIFO, la valeur d'ouverture/actuelle et d'autres métriques au niveau du lot.
- **Conservation actuelle** montre comment le lot est actuellement réparti entre les courtiers ou en tranches en transit.
- **Historique** liste la chronologie complète de la conservation et du cycle de vie, y compris les transferts et autres événements de lot, avec une action directe **Aller à la transaction** pour la transaction concernée.

!!! info "Logique d'appariement FIFO"

    LibreFolio résout la clôture des lots strictement avec l'appariement **Premier Entré, Premier Sorti (FIFO)** : les quantités vendues consomment toujours le **lot ouvert éligible le plus ancien en premier** avant que les lots plus récents ne soient touchés.

    Pour une théorie et des formules plus approfondies, consultez :

    - **[Théorie de la Fiscalité](../../financial-theory/fundamentals/taxation.md)**
    - **[Modèle de Transaction Achat/Vente](../../financial-theory/instruments/transaction-types/buy-sell.md#fifo-matching)**
    - **[Analyse des Lots FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)**

---

## 💸 Onglet Transactions

L'onglet **Transactions** du tableau de bord affiche une liste complète et paginée de toutes les opérations enregistrées dans le périmètre du portefeuille actif (ordres d'achat/vente, paiements de dividendes, dépôts d'espèces, transferts, etc.).

Pour une explication détaillée de la liste des transactions, des filtres et de la façon de lire les détails des transactions en lecture seule, veuillez vous référer à la page dédiée **[Aperçu des Transactions](../transactions/index.md)**.

---

*[⬅️ Retour à la vue d'ensemble du tableau de bord](index.md)*
