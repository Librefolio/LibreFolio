# 📊 Graphiques

*[⬅️ Retour à l'aperçu du tableau de bord](index.md)*

La section des graphiques se trouve sous les cartes KPI et vous offre une **vue historique et structurelle** de votre portefeuille sur la période sélectionnée.

---

## 📈 Graphique de croissance du portefeuille {: #portfolio-growth-chart }

Le graphique de croissance montre comment la valeur de votre portefeuille a évolué sur la période sélectionnée. Utilisez le bouton **Abs / %** dans le coin supérieur droit pour basculer entre les deux vues.

<div class="lf-screenshot-carousel" data-carousel="carousel-growth" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <div class="lf-screenshot-carousel-item is-active chart-crop-container" data-title="📈 Absolute Mode" alt="Growth Chart — Absolute Mode">
 <img class="gallery-img" data-category="dashboard" data-name="main" alt="Growth Chart — Absolute Mode">
 </div>
 <div class="lf-screenshot-carousel-item chart-crop-container" data-title="📈 Percentage Mode" alt="Growth Chart — Percentage Mode">
 <img class="gallery-img" data-category="dashboard" data-name="main-pct" alt="Growth Chart — Percentage Mode">
 </div>
</div>

### Mode ABS — valeurs absolues

Le graphique utilise une conception **d'aire empilée + lignes superposées** :

| Élément | Couleur | Signification |
|---------|---------|---------------|
| Aire — **Coût des actifs** | Bleu | Base de coût de toutes les positions ouvertes (coût moyen × quantité) |
| Aire — **Rendements** | Émeraude | Rendements du portefeuille sous forme de liquidités disponibles (intérêts, plus-values réalisées non encore réinvesties) |
| Aire — **Capital** | Gris-vert | Dépôts non déployés en liquidités |
| Ligne — **[VNI](../../financial-theory/technical-analysis/performance-metrics/nav.md)** | Vert foncé uni | Valeur totale du portefeuille aux prix actuels du marché |
| Ligne — **[Capital déposé](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)** | Gris pointillé | Capital externe net apporté au fil du temps |

**L'écart entre la ligne VNI et la ligne Capital déposé = P&L Total** — tous les gains jamais générés, y compris les plus-values latentes, les plus-values réalisées, les intérêts et les dividendes, moins les frais et les taxes.

#### Décomposition de l'infobulle

Lorsque vous survolez le graphique, l'infobulle affiche :

- **VNI** — valeur totale du portefeuille à cette date
- **Capital déposé** — capital net que vous avez apporté jusqu'à cette date
- **P&L Total** — la différence (VNI − Capital déposé)
- **Coût des actifs** / **Rendements** / **Capital** — les trois composantes de trésorerie

!!! tip "Lecture des portefeuilles axés sur le revenu (P2P, obligations)"

    Pour les portefeuilles comme le prêt entre particuliers où les actifs sont évalués à leur prix d'achat (pas de prix de marché en direct), VNI ≈ Coût des actifs. L'écart entre VNI et Capital déposé peut ne pas être visible sous forme d'écart dans le graphique — mais l'infobulle **P&L Total** affiche la valeur correcte.

    Lorsque vous réinvestissez tous les rendements dans de nouveaux actifs, la zone Rendements reste proche de zéro, et le revenu gagné se retrouve intégré dans la zone Coût des actifs. C'est mathématiquement correct : votre coût de base a augmenté parce que vous avez réinvesti les bénéfices.

🔗 **Théorie** : [Capital déposé & P&L Total](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md) · [Décomposition de la trésorerie](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md#three-pool-cash-model)

### Mode % — taux de rendement

Toutes les séries commencent à 0% au début de la période sélectionnée et montrent comment chaque mesure de rendement a évolué :

| Série | Ce qu'elle montre |
|--------|------------------|
| **[MWRR cumulatif](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** | Votre rendement personnel pondéré par le capital, incluant le moment des dépôts |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** | Rendement pur de la stratégie d'actifs, ignorant le moment de vos dépôts |
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/roi.md)** | Rendement brut sur le capital net investi |

L'écart entre MWRR et TWRR est l'[effet de calendrier](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md).

!!! note "MWRR indisponible"

    Si une bannière **Qualité des Données** apparaît indiquant que le MWRR n'est pas fiable, la série MWRR est masquée dans le graphique en %. Le problème survient généralement lorsque la période présente des flux de trésorerie très importants par rapport à la taille initiale du portefeuille, ce qui rend le solveur mathématique instable. ROI et TWRR sont toujours affichés.

---

## 🥧 Panneau de répartition {: #allocation-panel }

Le panneau de répartition montre comment votre portefeuille est distribué à l'instant présent et comment il a évolué historiquement.

<div class="lf-screenshot-carousel" data-carousel="carousel-alloc" data-carousel-interval="5000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <div class="lf-screenshot-carousel-item is-active alloc-crop-container" data-title="By Type (Current)" alt="Allocation by Type — Current">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-type-now" alt="Allocation by Type — Current">
 </div>
 <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="By Sector (Current)" alt="Allocation by Sector — Current">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-sector-now" alt="Allocation by Sector — Current">
 </div>
 <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="By Geography (Current)" alt="Allocation by Geography — Current">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-geo-now" alt="Allocation by Geography — Current">
 </div>
 <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="By Type (Historical)" alt="Allocation History by Type">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-type-history" alt="Allocation History by Type">
 </div>
 <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="By Sector (Historical)" alt="Allocation History by Sector">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-sector-history" alt="Allocation History by Sector">
 </div>
 <div class="lf-screenshot-carousel-item alloc-crop-container" data-title="By Geography (Historical)" alt="Allocation History by Geography">
 <img class="gallery-img" data-category="dashboard" data-name="allocation-geo-history" alt="Allocation History by Geography">
 </div>
</div>

### Trois dimensions

| Dimension | Ce qu'elle montre |
|-----------|------------------|
| **Type** | ETF, Action, Obligation, Crypto, Immobilier, Liquidités (espèces) |
| **Secteur** | Secteur d'activité : 💻 Technologie, 🏦 Finance, 💊 Santé, etc. |
| **Géographie** | Pays ou région de la cotation principale de chaque actif |

### Onglets Maintenant vs. Historique

- **Maintenant** — Diagramme en anneau de la répartition actuelle à `date_to`. Survolez une section pour voir le pourcentage exact et la valeur absolue.
- **Historique** — Graphique en aires empilées à 100 % montrant comment la répartition a évolué au fil du temps. Utile pour visualiser le rééquilibrage du portefeuille sur plusieurs mois ou années.

### Trésorerie comme liquidités

**La trésorerie** (votre solde de liquidités chez le courtier) apparaît toujours comme la part **Liquidités** dans les vues Type et Secteur. Dans la carte géographique, la trésorerie n'est attribuée à aucun pays et n'apparaît pas.

!!! info "Périmètre du courtier"

    Lorsque vous filtrez sur des courtiers spécifiques, la répartition n'affiche que les actifs et la trésorerie au sein de ces courtiers.

---

## 🔗 Liens connexes

- 💰 **[Cartes KPI](kpi-cards.md)** — Valeur Nette, P&L de Période, Rendements
- 💼 **[VNI / Valeur Nette](../../financial-theory/technical-analysis/performance-metrics/nav.md)**
- 💸 **[Capital déposé & P&L Total](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** · **[MWRR](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** · **[effet de calendrier](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md)**
