# 🔍 Positions & Analyse

*[⬅️ Retour à l'aperçu du tableau de bord](index.md)*

L'onglet **Positions** du tableau de bord vous permet d'inspecter les positions ouvertes, d'analyser les performances et d'explorer les lots fiscaux correspondants.

<div class="lf-screenshot-carousel" data-carousel="carousel-positions-views" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="positions-holdings-table" data-title="📋 Holdings (Table)" alt="Vue Tableau des positions">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-holdings-map" data-title="🗺️ Holdings (Map / Treemap)" alt="Vue Carte des positions">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-table" data-title="📈 Performance (Table)" alt="Vue Tableau des performances">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-map" data-title="📊 Performance (Map / Chart)" alt="Vue Carte des performances">
</div>

---

## 🔍 Onglet Positions

L'onglet **Positions** fournit une répartition détaillée de tous les instruments financiers actuellement détenus dans votre portefeuille (Actions, ETF, Obligations, Cryptomonnaies, etc.).

L'onglet Positions vous permet de basculer entre deux modes de métriques principaux via le sélecteur de vue, chacun se commandant sur un aspect différent de vos positions :

#### 📋 Vue Positions (Holdings)

La vue **Positions** (Holdings) se concentre sur la comptabilité, le suivi des quantités et l'évaluation actuelle des actifs. Elle vous aide à surveiller l'exposition actuelle de votre portefeuille et les métriques de base.

| Métrique | Description |
|:---|:---|
| **Quantité** | Actions, parts ou unités actuellement détenues dans votre portefeuille. |
| **Prix de marché** | Prix en direct de l'actif récupéré auprès du fournisseur de données connecté. |
| **Valeur de marché** | Valeur totale aux prix actuels du marché (\(\text{Prix} \times \text{Quantité}\)). |
| **Prix moyen (PMP)** | Le prix moyen pondéré payé pour acquérir la position ouverte actuelle. |
| **Poids** | Part proportionnelle de cet actif par rapport à la valeur totale du portefeuille. |

#### 📈 Vue Performance

La vue **Performance** se concentre sur les rendements absolus et relatifs. Elle vous aide à analyser la rentabilité de vos positions ouvertes, en intégrant les transactions passées et les revenus distribués.

| Métrique | Description |
|:---|:---|
| **Valeur totale** | Valeur actuelle des positions (correspond à la Valeur de marché). |
| **P&L non réalisé** | Gain ou perte papier calculé comme \(\text{Valeur de marché} - \text{Valeur comptable}\). |
| **ROI %** | Taux de rendement par rapport à la base de coût de la position. |
| **P&L total** | Rendements absolus cumulés (inclut les ventes passées closes et les dividendes). |

#### 🗺️ Style Visuel : Tableau vs. Carte

| Mode Visuel | Fonctionnalités principales | Cas d'utilisation optimal |
|:---|:---|:---|
| **📋 Vue Tableau** | • Disposition en grille triable<br>• Valeurs numériques précises<br>• Tri rapide des colonnes | Tenue de livres standard, recherche d'actifs spécifiques par quantité ou comparaison des valeurs PMP. |
| **🗺️ Vue Carte** | • Visualisation Treemap<br>• La taille indique le poids de l'actif<br>• L'intensité de la couleur indique la performance (vert = gain, rouge = perte) | Diagnostics visuels rapides, repérage de la sur-allocation ou identification des actifs sous-performants. |

---

## 🔬 Analyse des Lots FIFO {: #fifo-lots-analysis }

Lorsque vous cliquez sur une position dans la vue Tableau ou Carte, un panneau **Analyse des Lots FIFO** glisse depuis le côté droit de l'écran. Ce panneau fournit un historique détaillé des lots et de leur appariement fiscal pour cet actif spécifique.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-panel" alt="Panneau d'analyse des lots FIFO">
</div>

### 1. Chronologie à Bulles

Le graphique **Chronologie à Bulles** visualise tous les achats et ventes sur la période sélectionnée :

- 🟢 **Bulles Vertes** : Représentent les transactions d'achat. La taille de la bulle représente la quantité achetée.
- 🔴 **Bulles Rouges** : Représentent les transactions de vente. La taille représente la quantité vendue.
- 🔵 **Ligne Bleue** : Trace la progression historique de votre Prix Moyen Pondéré (PMP/Valeur comptable par action).
- 🔍 **Infobulles** : Passer la souris sur une bulle révèle la date, le type de transaction, la quantité et le prix de transaction.

### 2. Graphique du Prix PMP

Ce graphique superpose la ligne du **Prix Moyen Pondéré (PMP)** sur la ligne historique du **Prix de Marché**. Cela vous aide à visualiser quand vous avez acheté par rapport aux mouvements du marché et si vos positions actuelles sont en profit ou en perte.

🔗 **Théorie** : Reportez-vous à **[Prix Moyen Pondéré (PMP)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)** pour comprendre comment la base de coût est calculée, et à **[Chaîne de Prix d'Évaluation](../../financial-theory/technical-analysis/performance-metrics/nav.md#valuation-price-chain)** pour comprendre comment les prix de marché sont résolus par les fournisseurs de données.

### 3. Tableau des Lots Ouverts

Affiche les **Lots Fiscaux** actifs qui sont actuellement ouverts (pas encore appariés avec une vente). Il indique :

- 📅 **Date d'acquisition** : La date exacte d'achat des actions.
- 💰 **Prix d'acquisition** : Le prix d'achat initial.
- 📦 **Quantité restante** : Les actions de ce lot encore détenues.
- 📊 **Valeur du lot** : Valeur actuelle sur le marché de ce lot spécifique.
- 📈 **P&L non réalisé** : Gain ou perte spécifique à cet achat.

### 4. Tableau des Lots Clos

Affiche l'historique des **ventes réalisées** où un lot d'achat a été apparié à un lot de vente. Il vous aide à suivre :

- 🤝 **Date d'appariement** : La date de vente.
- 📦 **Quantité appariée** : Les actions closes.
- 💸 **P&L réalisé** : Le gain ou la perte final reconnu suite à l'appariement de cet achat avec la vente.

!!! info "Logique d'appariement FIFO"

    LibreFolio résout les lots fiscaux en suivant strictement la méthodologie comptable du **Premier Entré, Premier Sorti (FIFO)**. Les actions acquises les plus anciennes sont appariées en premier avec toutes les opérations de vente entrantes.

    Pour un aperçu théorique détaillé de la manière dont l'appariement FIFO est lié au calcul des plus-values et à la fiscalité, veuillez consulter **[Théorie Fiscale](../../financial-theory/fundamentals/taxation.md)** et le **[Modèle de Transaction Achat/Vente](../../financial-theory/instruments/transaction-types/buy-sell.md#fifo-matching)**.

---

## 💸 Onglet Transactions

L'onglet **Transactions** du Tableau de Bord affiche une liste complète et paginée de toutes les opérations enregistrées dans le périmètre du portefeuille actif (ordres d'achat/vente, paiements de dividendes, dépôts d'espèces, transferts, etc.).

Pour une explication détaillée de la liste des transactions, des filtres et de la manière de lire les détails des transactions en lecture seule, veuillez consulter la page dédiée **[Aperçu des Transactions](../transactions/index.md)**.
