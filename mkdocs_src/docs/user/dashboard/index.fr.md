# 📊 Dashboard

Le Tableau de bord est le **centre de contrôle de votre portefeuille** — un écran unique qui vous indique la valeur de votre portefeuille, ses performances et la manière dont votre argent est alloué.

<div class="lf-screenshot-carousel" data-carousel="carousel-dashboard-main" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Vue Principale (Absolu)" alt="Tableau de bord — Mode Absolu">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Vue Principale (Pourcentage)" alt="Tableau de bord — Mode Pourcentage">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-now" data-title="📊 Allocation" alt="Tableau de bord — Allocation">
</div>

---

## 🗂️ Disposition (Layout)

| Section | Emplacement | Contenu |
|---------|-------------|---------|
| **[Cartes KPI](kpi-cards.md)** | Rangée supérieure | [Patrimoine Net](kpi-cards.md#card-1--net-worth) · [P&L de la Période](kpi-cards.md#card-2--period-pl) · [Rendements](kpi-cards.md#card-3--returns) |
| **[Graphique de Croissance](charts.md#portfolio-growth-chart)** | Milieu gauche | Zone empilée absolue + série des rendements en pourcentage |
| **[Panneau d'Allocation](charts.md#allocation-panel)** | Milieu droit + bas | Type / Secteur / Géographie — actuel et historique |

---

## 🎛️ Période & Filtre de Courtier

En haut du tableau de bord, vous pouvez sélectionner :

- **Période** — préréglages de 1 semaine à Tout (All-Time), ou une période personnalisée via le sélecteur de dates
- **Filtre de courtier** — affichez tous les courtiers ou concentrez-vous sur un ou plusieurs
- **Devise cible** — convertit toutes les valeurs dans une seule devise de votre choix

!!! tip "La portée compte"

    Lorsque vous filtrez sur un seul courtier, les transferts de liquidités *vers d'autres courtiers* deviennent des flux externes pour cette portée. Cela affecte les calculs du [Capital Déposé](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md) et du [P&L de la Période](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md).

---

## 🌡️ Bannière de Qualité des Données

Si des cours ou des taux de change (FX) sont manquants à la date de fin, une bannière apparaît en haut pour expliquer quels actifs n'ont pas pu être évalués. Les actifs sans fournisseur de prix (saisis manuellement, comme les projets de crowdfunding immobilier) sont valorisés en permanence au coût d'achat — ceci est intentionnel et ne génère pas d'alerte.

---

## 🔗 Dans cette section

- 💰 **[Cartes KPI](kpi-cards.md)** — Patrimoine Net, P&L de la Période, et Rendements expliqués
- 📊 **[Graphiques](charts.md)** — Graphique de Croissance et Panneau d'Allocation expliqués

## 🔗 Théorie associée

- **[NAV / Patrimoine Net](../../financial-theory/technical-analysis/performance-metrics/nav.md)**
- **[Valeur Comptable](../../financial-theory/technical-analysis/performance-metrics/book-value.md)**
- **[P&L de la Période](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md)**
- **[Capital Déposé & P&L Total](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)**
- **[Aperçu des Métriques de Performance](../../financial-theory/technical-analysis/performance-metrics/index.md)**
