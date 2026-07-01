# 📊 Graphiques

*[⬅️ Retour à l'aperçu du tableau de bord](index.md)*

La section des graphiques se situe sous les cartes KPI et vous offre une **vue historique et structurelle** de votre portefeuille sur la période sélectionnée.

---

## 📈 Graphique de croissance du portefeuille

Le graphique de croissance montre comment la valeur de votre portefeuille a évolué sur la période sélectionnée. Utilisez l'**interrupteur Abs / %** dans le coin supérieur droit pour basculer entre deux vues.

<div class="lf-screenshot-carousel" data-carousel="carousel-growth" data-carousel-interval="5000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Mode Absolu" alt="Graphique de croissance — Mode Absolu">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Mode Pourcentage" alt="Graphique de croissance — Mode Pourcentage">
</div>

### Mode ABS — valeurs absolues

Le graphique utilise un design de **zones empilées + lignes de superposition** :

| Élément | Couleur | Signification |
|---------|-------|---------|
| Zone — **Coût des actifs** | Bleu | Base de coût de toutes les positions ouvertes (coût moyen × quantité) |
| Zone — **Rendements** | Émeraude | Rendements du portefeuille détenus en liquidités (intérêts, gains réalisés non encore réinvestis) |
| Zone — **Capital** | Gris-vert | Dépôts non déployés détenus en espèces |
| Ligne — **[NAV](../../financial-theory/technical-analysis/performance-metrics/nav.md)** | Vert foncé plein | Valeur totale du portefeuille aux prix actuels du marché |
| Ligne — **[Capital déposé](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)** | Gris pointillé | Capital externe net apporté au fil du temps |

**L'écart entre la ligne NAV et la ligne du Capital déposé = P&L Total** — tous les gains jamais générés, y compris les gains non réalisés, les gains réalisés, les intérêts et les dividendes, moins les frais et les taxes.

#### Détail de l'infobulle

Lorsque vous survolez le graphique, l'infobulle affiche :

- **NAV** — valeur totale du portefeuille à cette date
- **Capital déposé** — capital net que vous avez apporté jusqu'à cette date
- **P&L Total** — la différence (NAV − Capital déposé)
- **Coût des actifs** / **Rendements** / **Capital** — les trois composantes de trésorerie

!!! tip "Lecture des portefeuilles basés sur les revenus (P2P, obligations)"

    Pour les portefeuilles tels que le prêt P2P où les actifs sont évalués à leur prix d'achat (pas de prix de marché en direct), NAV ≈ Coût des actifs. L'écart entre le NAV et le Capital déposé peut ne pas être visible sous forme d'écart sur le graphique — mais l'infobulle **P&L Total** affiche la valeur correcte.

    Lorsque vous réinvestissez tous les rendements dans de nouveaux actifs, la zone Rendements reste proche de zéro, et les revenus gagnés finissent par être intégrés dans la zone Coût des actifs. C'est mathématiquement correct : votre base de coût a augmenté parce que vous avez réinvesti vos profits.

🔗 **Théorie** : [Capital déposé & P&L Total](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md) · [Décomposition de la trésorerie](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md#modele-de-cash-a-trois-pools)

### Mode % — taux de rendement

Toutes les séries commencent à 0% au début de la période sélectionnée et montrent comment chaque indicateur de rendement a évolué :

| Série | Ce qu'elle montre |
|--------|--------------|
| **[MWRR cumulé](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** | Votre rendement personnel pondéré par les flux monétaires, incluant le timing des dépôts |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** | Rendement pur de la stratégie d'actifs, ignorant le moment de vos dépôts |
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/roi.md)** | Rendement brut sur le capital net investi |

L'écart entre le MWRR et le TWRR est l'[Effet de Timing](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md).

!!! note "MWRR indisponible"

    Si une **bannière de qualité des données** apparaît indiquant que le MWRR n'est pas fiable, la série MWRR est masquée du graphique %. Ce problème survient généralement lorsque la période présente des flux de trésorerie très importants par rapport à la taille initiale du portefeuille, rendant le solveur mathématique instable. Le ROI et le TWRR sont toujours affichés.

---

## 🥧 Panneau d'allocation

Le panneau d'allocation montre comment votre portefeuille est réparti à l'instant présent et comment cette répartition a évolué historiquement.

<div class="lf-screenshot-carousel" data-carousel="carousel-alloc" data-carousel-interval="5000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="allocation-type-now" data-title="Par Type (Actuel)" alt="Allocation par Type — Actuelle">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-sector-now" data-title="Par Secteur (Actuel)" alt="Allocation par Secteur — Actuelle">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-geo-now" data-title="Par Géographie (Actuel)" alt="Allocation par Géographie — Actuelle">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-history" data-title="Par Type (Historique)" alt="Historique de l'allocation par Type">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-sector-history" data-title="Par Secteur (Historique)" alt="Historique de l'allocation par Secteur">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-geo-history" data-title="Par Géographie (Historique)" alt="Historique de l'allocation par Géographie">
</div>

### Trois dimensions

| Dimension | Ce qu'elle montre |
|-----------|--------------|
| **Type** | ETF, Actions, Obligations, Crypto, Immobilier, Liquidité (espèces) |
| **Secteur** | Secteur industriel : 💻 Technologie, 🏦 Finance, 💊 Santé, etc. |
| **Géographie** | Pays ou région de la cotation principale de chaque actif |

### Onglets Actuel vs Historique

- **Actuel** — Graphique en anneau présentant l'allocation actuelle à la date `date_to`. Survolez n'importe quelle section pour voir le pourcentage exact et la valeur absolue.
- **Historique** — Graphique d'aires empilées à 100% montrant comment l'allocation a évolué dans le temps. Utile pour visualiser le rééquilibrage du portefeuille sur plusieurs mois ou années.

### Le cash comme Liquidité

Le **Cash** (votre solde chez le courtier) apparaît toujours comme la section **Liquidité** dans les vues Type et Secteur. Sur la carte Géographie, le cash n'est assigné à aucun pays et n'apparaît pas.

!!! info "Portée du courtier"

    Lorsque vous filtrez par courtiers spécifiques, l'allocation n'affiche que les actifs et le cash détenus chez ces courtiers.

---

## 🔗 Liens connexes

- 💰 **[Cartes KPI](kpi-cards.md)** — Valeur nette, P&L de la période, Rendements
- 💼 **[NAV / Valeur nette](../../financial-theory/technical-analysis/performance-metrics/nav.md)**
- 💸 **[Capital déposé & P&L Total](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** · **[MWRR](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** · **[Effet de Timing](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md)**
