# 📊 Tableau de bord

Le Tableau de bord est le **centre de commande de votre portefeuille** — un écran unique qui vous indique la valeur de votre portefeuille, ses performances et la répartition de votre argent.

<div class="lf-screenshot-carousel" data-carousel="carousel-dashboard-main" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Vue principale (Absolu)" alt="Tableau de bord — Mode absolu">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Vue principale (Pourcentage)" alt="Tableau de bord — Mode pourcentage">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-now" data-title="📊 Allocation" alt="Tableau de bord — Allocation">
</div>

## 🗂️ Disposition par onglets

L'interface du Tableau de bord est organisée en trois onglets principaux, vous permettant de basculer entre différents niveaux de détail :

1. **Aperçu** (par défaut) : Indicateurs clés, soldes de liquidités et graphiques visuels de votre portefeuille.
2. **[Positions et analyse](positions.md)** : Titres détenus, pondérations et analyse détaillée des lots fiscaux (FIFO).
3. **Transactions** : Liste des opérations récentes avec un visualiseur de détails en lecture seule.

---

## 📈 Onglet Aperçu

L'onglet Aperçu est la page d'accueil par défaut. Il est structuré dans les sections suivantes :

| Section | Description |
|---------|-------------|
| **[Indicateurs KPI](kpi-cards.md)** | Résumé de la Valeur nette, du P&L de période et des indicateurs de taux de rendement. |
| **Soldes de liquidités** | Soldes liquides regroupés par devise dans le périmètre du courtier actif. |
| **[Graphique de croissance](charts.md#portfolio-growth-chart)** | Graphique en aires empilées montrant le coût des actifs, la trésorerie et les rendements au fil du temps. |
| **[Panneau d'allocation](charts.md#allocation-panel)** | Graphiques en anneau et historiques empilés regroupés par type, secteur et zone géographique. |

### 🪙 Soldes de liquidités

Juste en dessous des indicateurs KPI, le panneau **Soldes de liquidités** affiche votre trésorerie liquide totale agrégée par devise. Par exemple, si vous détenez des USD chez le courtier A et des EUR chez le courtier B, les deux soldes seront affichés côte à côte.

Lorsque vous appliquez un filtre de courtier, les soldes de liquidités se mettent automatiquement à jour pour refléter uniquement la trésorerie détenue chez les courtiers sélectionnés.

---

## 🎛️ Période, Filtres et Export IA

En haut à droite du tableau de bord, plusieurs contrôles vous permettent de personnaliser votre vue :

- **Période** — préréglages de 1 semaine à Tout (MAX), ou une période personnalisée via le sélecteur de dates.
- **Filtre courtier** — filtrer tous les indicateurs sur un ou plusieurs courtiers spécifiques.
- **Devise cible** — convertit dynamiquement tous les actifs et soldes de liquidités dans une devise unique sélectionnée pour une vue agrégée.
- **Export IA** (:material-brain:) — Cliquez sur ce bouton pour copier dans le presse-papiers un résumé textuel de l'état actuel de votre portefeuille, optimisé pour être collé dans des LLM (ex. Gemini). Vous pouvez choisir entre :
 - **Export complet** : Inclut toutes les valeurs KPI, les positions, les pondérations et les allocations.
 - **Données uniquement** : Une représentation compacte en JSON/texte de vos avoirs et soldes.

!!! tip "Le périmètre a son importance"

    Lorsque vous filtrez sur un seul courtier, les transferts de liquidités *vers d'autres courtiers* deviennent des flux externes pour ce périmètre. Cela affecte le calcul du [Capital déposé](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) et du [P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md).

---

## 🌡️ Bannière de qualité des données

Si des cours ou des taux de change sont manquants à la date de fin, une bannière apparaît en haut pour expliquer quels actifs n'ont pas pu être valorisés. Les actifs sans fournisseur de cours (saisis manuellement, comme les projets de crowdfunding immobilier) sont valorisés en permanence au coût d'achat — cela est intentionnel et ne génère pas d'avertissement.

---

## 🔗 Dans cette section

- 💰 **[Indicateurs KPI](kpi-cards.md)** — Valeur nette, P&L de période et rendements expliqués
- 📊 **[Graphiques](charts.md)** — Graphique de croissance et panneau d'allocation expliqués
- 🔍 **[Positions et analyse](positions.md)** — Positions ouvertes, vues tableau vs. carte, et analyse détaillée des lots fiscaux FIFO.

## 🔗 Théorie connexe

- **[VNI / Valeur nette](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- **[Valeur comptable](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)**
- **[P&L de période](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)**
- **[Capital déposé et P&L total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- **[Aperçu des métriques de performance](../../financial-theory/technical-analysis/performance-metrics/index.md)**
