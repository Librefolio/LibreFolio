# 📊 Graphiques

*[⬅️ Retour à la vue d'ensemble du tableau de bord](index.md)*

La section des graphiques se situe sous les cartes KPI et vous offre une **vue historique et structurelle** de votre portefeuille sur la période sélectionnée.

---

## 📈 Graphique de croissance du portefeuille {: #portfolio-growth-chart }

Le graphique de croissance montre l'évolution de la valeur de votre portefeuille sur la période sélectionnée. Utilisez l'interrupteur **Abs / %** dans le coin supérieur droit pour basculer entre les deux vues.

<div class="lf-screenshot-carousel" data-carousel="carousel-growth" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <div class="lf-screenshot-carousel-item is-active chart-crop-container" data-title="📈 Mode Absolu" alt="Graphique de croissance — Mode Absolu">
 <img class="gallery-img" data-category="dashboard" data-name="main" alt="Graphique de croissance — Mode Absolu">
 </div>
 <div class="lf-screenshot-carousel-item chart-crop-container" data-title="📈 Mode Pourcentage" alt="Graphique de croissance — Mode Pourcentage">
 <img class="gallery-img" data-category="dashboard" data-name="main-pct" alt="Graphique de croissance — Mode Pourcentage">
 </div>
</div>

### ABS ABS — valeurs absolues

Le graphique utilise une **combinaison d'aires empilées et de lignes superposées** :

| Élément | Couleur | Signification |
|---------|---------|---------------|
| Aire — **Coût des actifs** | Bleue | Base de coût de toutes les positions ouvertes (coût moyen × quantité) |
| Aire — **Rendements** | Émeraude | Rendements du portefeuille sous forme de liquidités disponibles (intérêts, plus-values réalisées non encore réinvesties) |
| Aire — **Capital** | Gris-vert | Dépôts non déployés en liquidités |
| Ligne — **[VNI](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)** | Vert foncé continue | Valeur totale du portefeuille aux prix de marché actuels |
| Ligne — **[Capital déposé](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)** | Gris pointillé | Capital externe net apporté au fil du temps |

**L'écart entre la ligne VNI et la ligne Capital déposé = P&L total** — tous les gains jamais générés, y compris les plus-values latentes, les gains réalisés, les intérêts et les dividendes, moins les frais et taxes.

#### Tooltip détaillée de l'infobulle

Lorsque vous survolez le graphique, l'infobulle affiche :

- **VNI** — valeur totale du portefeuille à cette date
- **Capital déposé** — capital net que vous avez apporté jusqu'à cette date
- **P&L total** — la différence (VNI − Capital déposé)
- **Coût des actifs** / **Rendements** / **Capital** — les trois composantes de liquidités

!!! tip "Lecture des portefeuilles axés sur les revenus (P2P, obligations)"

    Pour les portefeuilles comme le prêt P2P où les actifs sont évalués à leur prix d'achat (pas de prix de marché en temps réel), VNI ≈ Coût des actifs. L'écart entre VNI et Capital déposé peut ne pas être visible sous forme d'écart sur le graphique — mais l'infobulle **P&L total** affiche la valeur correcte.

    Lorsque vous réinvestissez tous les rendements dans de nouveaux actifs, la zone Rendements reste proche de zéro, et le revenu gagné se retrouve intégré dans la zone Coût des actifs. C'est mathématiquement correct : votre base de coût a augmenté parce que vous avez réinvesti les bénéfices.

🔗 **Théorie** : [Capital déposé et P&L total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) · [Décomposition de la trésorerie](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#three-pool-cash-model)

### Mode % — taux de rendement

Toutes les séries commencent à 0% au début de la période sélectionnée et montrent comment chaque indicateur de rendement a évolué :

| Série | Ce qu'elle montre |
|-------|------------------|
| **[MWRR cumulatif](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** | Votre rendement personnel pondéré par les flux de trésorerie, incluant le moment des dépôts |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** | Rendement pur de la stratégie d'actifs, ignorant le moment de vos dépôts |
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md)** | Rendement brut sur le capital net investi |

L'écart entre MWRR et TWRR est l'[Effet de timing](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md).

!!! note "MWRR indisponible"

    Si une bannière **Qualité des données** apparaît indiquant que le MWRR n'est pas fiable, la série MWRR est masquée dans le graphique en %. Ce problème survient généralement lorsque la période comporte des flux de trésorerie très importants par rapport à la taille initiale du portefeuille, ce qui rend le solveur mathématique instable. Le ROI et le TWRR sont toujours affichés.

---

## 🥧 Panneau d'allocation {: #allocation-panel }

Le panneau d'allocation montre comment votre portefeuille est distribué à l'instant présent et comment il a évolué historiquement.

<div class="lf-screenshot-carousel" data-carousel="carousel-alloc" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <div class="lf-screenshot-carousel-item is-active alloc-crop-container" data-title="Par type (Actuel)" alt="Allocation par type — Actuelle">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-type-now" alt="Allocation par type — Actuelle">
 </div>
 <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Par secteur (Actuel)" alt="Allocation par secteur — Actuelle">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-sector-now" alt="Allocation par secteur — Actuelle">
 </div>
 <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Par géographie (Actuel)" alt="Allocation par géographie — Actuelle">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-geo-now" alt="Allocation par géographie — Actuelle">
 </div>
 <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Par type (Historique)" alt="Historique d'allocation par type">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-type-history" alt="Historique d'allocation par type">
 </div>
 <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Par secteur (Historique)" alt="Historique d'allocation par secteur">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-sector-history" alt="Historique d'allocation par secteur">
 </div>
 <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="Par géographie (Historique)" alt="Historique d'allocation par géographie">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-geo-history" alt="Historique d'allocation par géographie">
 </div>
</div>

### Three dimensions

| Dimension | Ce qu'elle montre |
|-----------|------------------|
| **Type** | ETF, Action, Obligation, Crypto, Immobilier, Liquidités |
| **Secteur** | Secteur industriel : 💻 Technologies, 🏦 Finance, 💊 Santé, etc. |
| **Géographie** | Pays ou région de la cotation principale de chaque actif |

### Now Actuel vs. Historique

- **Actuel** — Graphique en anneau de l'allocation actuelle à `date_to`. Survolez une section pour voir le pourcentage exact et la valeur absolue.
- **Historique** — Graphique en aires empilées à 100 % montrant comment l'allocation a évolué dans le temps. Utile pour visualiser le rééquilibrage du portefeuille sur plusieurs mois ou années.

### Cash 

**Les liquidités** (votre solde de courtage) apparaissent toujours comme la part **Liquidités** dans les vues Type et Secteur. Dans la carte géographique, les liquidités ne sont attribuées à aucun pays et n'apparaissent pas.

!!! info "Périmètre du courtier"

    Lorsque vous filtrez par courtiers spécifiques, l'allocation n'affiche que les actifs et les liquidités présents chez ces courtiers.

---

## 🔗 Liens connexes

- 💰 **[Cartes KPI](kpi-cards.md)** — Valeur nette, P&L de période, Rendements
- 💼 **[VNI / Valeur nette](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- 💸 **[Capital déposé et P&L total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** · **[MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** · **[Effet de timing](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)**
