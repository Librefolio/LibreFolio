# 📊 Tableau de bord

Le Tableau de bord est le **centre de commande de votre portefeuille** — un écran unique qui vous indique la valeur de votre portefeuille, ses performances et la répartition de votre capital.

<div class="lf-screenshot-carousel" data-carousel="carousel-dashboard-main" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Vue principale (Absolu)" alt="Tableau de bord — Mode Absolu">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Vue principale (Pourcentage)" alt="Tableau de bord — Mode Pourcentage">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-now" data-title="📊 Allocation" alt="Tableau de bord — Allocation">
</div>

## 🗂️ Disposition par onglets

L'interface du Tableau de bord est organisée en trois onglets principaux, vous permettant de basculer entre différents niveaux de détail :

1. **Aperçu** (par défaut) : Indicateurs clés, soldes de trésorerie et graphiques visuels de votre portefeuille.
2. **[Positions et analyse](positions.md)** : Avoirs ouverts, pondérations et analyse détaillée des lots fiscaux (FIFO).
3. **Transactions** : Liste des opérations récentes avec un visualisateur de détails en lecture seule.

---

## 📈 Onglet Aperçu

L'onglet Aperçu est la page d'accueil par défaut. Il est structuré en les sections suivantes :

| Section | Description |
|---------|-------------|
| **[Cartes KPI](kpi-cards.md)** | Résumé de la Valeur nette, des P&L de période et des indicateurs de taux de rendement. |
| **Soldes de trésorerie** | Soldes liquides regroupés par devise dans le périmètre du courtier actif. |
| **[Graphique de croissance](charts.md#portfolio-growth-chart)** | Graphique en aires empilées montrant le coût des actifs, la trésorerie et les rendements dans le temps. |
| **[Panneau d'allocation](charts.md#allocation-panel)** | Graphiques en anneau et historiques empilés regroupés par Type, Secteur et Géographie. |

### 🪙 Soldes de trésorerie

Juste en dessous des cartes KPI, le panneau **Soldes de trésorerie** affiche votre trésorerie liquide totale agrégée par devise. Par exemple, si vous détenez des USD chez le courtier A et des EUR chez le courtier B, les deux soldes seront affichés côte à côte.

Lorsque vous appliquez un filtre de courtier, les soldes de trésorerie se mettent automatiquement à jour pour refléter uniquement la trésorerie détenue dans les courtiers sélectionnés.

---

## 🎛️ Plage de dates, Filtres et Export IA

En haut à droite du tableau de bord, vous disposez de plusieurs commandes pour personnaliser votre vue :

- **Plage de temps** — préréglages de 1 semaine à Tout le temps (MAX), ou une plage personnalisée via le sélecteur de dates.
- **Filtre de courtier** — filtrer tous les indicateurs pour un ou plusieurs courtiers spécifiques.
- **Devise cible** — convertit dynamiquement tous les actifs et soldes de trésorerie dans une devise unique sélectionnée pour une vue agrégée.
- **Export IA** (:material-brain:) — Cliquez sur ce bouton pour copier dans le presse-papiers un résumé textuel de l'état actuel de votre portefeuille, optimisé pour le collage dans des LLM (par exemple, Gemini). Vous pouvez choisir entre :
 - **Export complet** : Inclut toutes les valeurs KPI, les positions, les pondérations et les allocations.
 - **Données uniquement** : Une représentation JSON/texte compacte de vos avoirs et soldes.

!!! tip "Le périmètre compte"

    Lorsque vous filtrez sur un seul courtier, les transferts de trésorerie *vers d'autres courtiers* deviennent des flux externes pour ce périmètre. Cela affecte les calculs du [Capital déposé](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md) et des [P&L](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md).

---

## 🌡️ Bannière de qualité des données

Si des prix ou des taux de change sont manquants à la date de fin, une bannière apparaît en haut expliquant quels actifs n'ont pas pu être valorisés. Les actifs sans fournisseur de prix (saisis manuellement, comme les projets de crowdfunding immobilier) sont définitivement valorisés au coût d'achat — cela est intentionnel et ne génère pas d'avertissement.

---

## 🔗 Dans cette section

- 💰 **[Cartes KPI](kpi-cards.md)** — Valeur nette, P&L de période et Rendements expliqués
- 📊 **[Graphiques](charts.md)** — Graphique de croissance et Panneau d'allocation expliqués
- 🔍 **[Positions et analyse](positions.md)** — Positions ouvertes, vues tableau vs. carte, et analyse détaillée des lots fiscaux FIFO.

## 🔗 Théorie connexe

- **[VNI / Valeur nette](../../financial-theory/technical-analysis/performance-metrics/nav.md)**
- **[Valeur comptable](../../financial-theory/technical-analysis/performance-metrics/book-value.md)**
- **[P&L de période](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md)**
- **[Capital déposé et P&L total](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)**
- **[Aperçu des indicateurs de performance](../../financial-theory/technical-analysis/performance-metrics/index.md)**
