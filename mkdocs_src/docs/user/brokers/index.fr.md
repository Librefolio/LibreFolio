# 🏦 Courtiers

Un **Courtier** dans LibreFolio représente un compte de courtage — l'endroit où vos investissements résident (par exemple, Interactive Brokers, Degiro, un compte bancaire).

Toutes les transactions, rapports et données d'importation sont liés à un courtier. Vous avez besoin d'au moins un courtier pour commencer à suivre votre portefeuille.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="list" alt="Liste des Courtiers" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## ➕ Créer un Courtier

1. Accédez à la page **Courtiers** depuis la barre latérale
2. Cliquez sur **"Nouveau Courtier"**
3. Remplissez les détails : nom, devise de base et éventuellement une icône
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="edit-modal" alt="Formulaire de Modification du Courtier" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>

4. Le courtier apparaît dans votre liste, prêt à recevoir des transactions et des rapports
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="detail" alt="Détail du Courtier" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>
---

## 🗂️ Disposition des Détails du Courtier

Une fois que vous sélectionnez un courtier dans la liste, l'interface est divisée en quatre onglets principaux :

1. **Aperçu** : Affichage de la valeur nette, des indicateurs de rendement, de l'historique de croissance et des graphiques de répartition limités à ce seul compte de courtage (voir **[Aperçu du Tableau de Bord](../dashboard/index.md)**).
2. **Positions** : Liste des positions ouvertes, pondérations des actifs et mesures de performance au sein de ce courtier, avec accès au panneau coulissant des Lots FIFO (voir **[Positions du Tableau de Bord](../dashboard/positions.md)**).
3. **Transactions** : Le journal de toutes les activités financières, y compris les saisies manuelles, les importations de relevés et les historiques (voir **[Importation de Transactions](import.md)**).
4. **Infos** : Métadonnées du courtier, configurations de découvert et de vente à découvert, Export IA et contrôles de partage intégrés (voir **[Configuration & Infos](info.md)**).

---

## 📈 Onglet Aperçu

L'onglet **Aperçu** agit comme un tableau de bord local pour le courtier sélectionné. Il contient les mêmes éléments que le **[Tableau de Bord](../dashboard/index.md)** principal mais limité à ce seul compte de courtage :

- **Cartes KPI Locales** : Valeur nette, P&L de la période et rendements spécifiques à ce courtier. (Voir **[Cartes KPI du Tableau de Bord](../dashboard/kpi-cards.md)** pour les détails de calcul).
- **Panneau des Soldes de Trésorerie** : Liquidités détenues sur ce compte de courtage, ventilées par devise.
- **Graphique de Croissance** : Croissance historique de la valeur de ce compte (voir **[Graphique de Croissance du Portefeuille](../dashboard/charts.md#portfolio-growth-chart)**).
- **Panneau de Répartition** : Composition du portefeuille (par Type, Secteur et Répartition Géographique) pour les titres détenus chez ce courtier spécifique (voir **[Panneau de Répartition](../dashboard/charts.md#allocation-panel)**).

---

## 🔍 Onglet Positions

L'onglet **Positions** répertorie tous les actifs actuellement détenus chez ce courtier. Il est identique en termes de fonctionnalités à la vue principale **[Positions du Tableau de Bord](../dashboard/positions.md)**, mais limitée à ce seul courtier :

<div class="lf-screenshot-carousel" data-carousel="carousel-broker-positions" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="positions-holdings-table" data-title="📋 Positions (Tableau)" alt="Vue Tableau des Positions du Courtier">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-holdings-map" data-title="🗺️ Positions (Carte / Treemap)" alt="Vue Carte des Positions du Courtier">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-table" data-title="📈 Performance (Tableau)" alt="Vue Tableau de Performance du Courtier">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="positions-performance-map" data-title="📊 Performance (Carte / Graphique)" alt="Vue Carte de Performance du Courtier">
</div>

- **Boutons Bascule & Dispositions** : Vous pouvez basculer entre les métriques de **Positions** (quantités, valeurs, pondérations) et de **Performance** (P&L non réalisé, ROI %) et choisir entre une disposition en **Tableau** ou en **Carte** (treemap).
- **Analyse FIFO** : Cliquez sur n'importe quelle ligne ou carte d'actif pour ouvrir le panneau coulissant **Analyse des Lots FIFO**. (Voir **[Analyse des Lots FIFO](../dashboard/positions.md#fifo-lots-analysis)** pour les règles de correspondance détaillées).

---

## 📑 Dans Cette Section

- 📥 **[Importer des Transactions (BRIM)](import.md)** — Comment enregistrer manuellement des transactions, exécuter l'assistant d'import CSV/Excel BRIM et consulter les journaux d'importation.
- ⚙️ **[Configuration & Infos](info.md)** — Paramètres de métadonnées (découverts, ventes à découvert), générateur de prompt d'Export IA limité et panneau de partage de courtier intégré.
- 🤝 **[Partage de Courtier](sharing.md)** — Guide détaillé sur les permissions des rôles (Propriétaire, Éditeur, Lecteur) et les paramètres de répartition en pourcentage des actifs.
