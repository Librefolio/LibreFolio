# 🔍 Page de Détails de l'Actif

Cliquez sur n'importe quel actif depuis la [Liste des Actifs](../index.md) pour ouvrir sa page de détails. Ici, vous pouvez visualiser, analyser et gérer les données de prix pour cet actif spécifique.

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Page de Détails de l'Actif" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La page de détails est organisée en plusieurs fonctionnalités, chacune accessible depuis la barre d'outils :

---

## 🧭 Fonctionnalités

### 📈 [Graphique Interactif](chart.md)

La vue principale — un graphique complet propulsé par ECharts avec zoom, panoramique, filtrage par plage de dates et conversion de devises. Les marqueurs d'événements (dividendes, fractionnements, intérêts) sont superposés directement sur la courbe des prix.

### 📊 [Signaux](signals.md)

Superposez des indicateurs techniques (EMA, MACD, RSI, Bandes de Bollinger, Comparaison d'Actifs) sur le graphique. Chaque signal est calculé en temps réel à partir des données de prix et peut être commuté indépendamment.

### 📐 [Mesures](measures.md)

Outil de mesure par clic. Sélectionnez deux points sur le graphique pour voir le delta, la variation en pourcentage et le rendement annualisé entre eux.

### 🗂️ [Classification](classification.md)

Graphique sectoriel, carte mondiale géographique et répartition par pays — lorsque les données de classification sont configurées pour l'actif.

### ✏️ [Éditeur de Données](data-editor.md)

Visualisez, ajoutez, modifiez ou supprimez des points de données de prix individuels directement sur le graphique.

### 📅 [Événements](events.md)

Événements au niveau de l'actif (dividendes, intérêts, fractionnements, ajustements de prix) affichés sous forme de marqueurs sur le graphique.

---

## 🔧 En-tête & Contrôles

- **Bouton de retour ←** : revenir à la liste des actifs (ou à la page précédente)
- **Infos Actif** : nom, badge de type, devise, prix actuel
- **Modifier** (✏️) : ouvrir la fenêtre modale d'édition pour modifier les propriétés de l'actif
- **Synchroniser** (🔄) : récupérer les dernières données de prix depuis le fournisseur
- **Actualiser** (↻) : recharger les données depuis la base de données

---

## 🔗 Liens Associés

- ➕ **[Créer & Modifier](../create-edit.md)** — Création et configuration des actifs
- 📋 **[Liste des actifs](../index.md)** — Retour à la page de liste des actifs
