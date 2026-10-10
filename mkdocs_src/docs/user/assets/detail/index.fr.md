# 🔍 Page de détail d'un actif

Cliquez sur un actif dans la [page Actifs](../index.md) pour ouvrir sa propre page : son historique de prix, les outils pour l'analyser et les données qui le sous-tendent.

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Page de détail d'un actif" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La page comporte deux onglets : **Vue d'ensemble**, décrit ci-dessous, et **Risques & Scénarios**.

!!! info "Bêta"

    L'onglet **Risques & Scénarios** est encore en bêta : il s'ouvre avec la mention *L'analyse des risques est en bêta.* et n'est pas encore couvert par cette documentation.

---

## 🧭 Ce que montre la Vue d'ensemble

De haut en bas :

### 📊 [Signaux](signals.md)

Tracez n'importe lequel des **22 indicateurs techniques**, un autre actif ou une paire de devises, ou une courbe de référence sur le graphique.

### 📈 [Graphique interactif](chart.md)

L'historique des prix, ou le **[Rendement glissant](chart.md#rolling-return)** sur une fenêtre de votre choix (1S, 1M, 3M, 1A ou une durée personnalisée). Zoomez, déplacez et convertissez-le dans une autre devise.

### ✏️ [Éditeur de données](data-editor.md)

Ajoutez, corrigez ou supprimez des prix et des événements, un par un ou à partir d'un fichier CSV.

### 📐 [Mesures](measures.md)

Cliquez sur deux points du graphique pour lire la variation entre eux.

### 🗂️ [Classification](classification.md)

La répartition par secteur et par pays, dans le panneau **Métadonnées & Classification**.

### 📅 [Événements](events.md)

Dividendes, divisions, intérêts et autres événements de l'actif, représentés par des marqueurs sur le graphique.

---

## 🔧 En-tête et barre d'outils

- **←** revient à la liste, ou à la page d'où vous venez, en une seule étape, même après avoir navigué avec les flèches.
- **L'actif** — un point (vert actif, rouge archivé), son nom, son type et sa devise, un lien **Transactions (N)** lorsqu'il en possède, son fournisseur (ou **✏️ Manuel**), et un lien vers sa page web : celle que vous avez définie sur l'actif, ou sinon celle du fournisseur.
- **‹ n/N ›** — l'actif précédent ou suivant, en conservant les mêmes dates (voir le panneau ci-dessous).
- **Plage de dates** et **Convertir en** — la période et la devise du [graphique](chart.md).
- **Export IA** — copie les données de l'actif pour un assistant IA ([Export IA d'un actif](../../ai-export/asset.md)).
- **Modifier** (✏️) — ouvre le formulaire de l'actif ([Créer & Modifier](../create-edit.md)).
- **Synchroniser** (🔄) — télécharge les derniers prix, avec ceux des actifs comparés et les taux de change dont le graphique a besoin ; il affiche **Recalculer** pour un Investissement programmé. Non disponible pour un actif sans fournisseur ou archivé.
- **Recharger** (↻) — recharge les données de la page à partir de ce que LibreFolio a stocké.

??? info "🧭 Quel ordre suivent les flèches ‹ ›"

    - **Ouvert depuis la page Actifs** : la liste telle que vous l'avez laissée — sa recherche, ses filtres, sa vue grille ou tableau et, dans le tableau, son tri et ses filtres de colonnes.
    - **Ouvert de toute autre manière** (un lien ou un favori, un rechargement, le tableau de bord, Transactions…), ou pour un actif que cette liste n'affiche pas : tous les actifs dans l'ordre par défaut de la page Actifs, les actifs archivés uniquement lorsque l'actif que vous avez ouvert est archivé.
    - Le compteur (par exemple 3/12) indique où vous êtes. Les flèches s'arrêtent aux deux extrémités et disparaissent lorsqu'il n'y a qu'un seul actif à parcourir.

---

## 🔗 Voir aussi

- ➕ **[Créer & Modifier](../create-edit.md)** — Créer et configurer des actifs
- 📋 **[Vue d'ensemble des actifs](../index.md)** — Retour à la page de la liste des actifs
