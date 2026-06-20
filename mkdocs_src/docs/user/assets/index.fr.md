# 💼 Actifs

Les actifs sont le cœur de LibreFolio. Ils représentent tout instrument financier que vous possédez ou suivez : actions, ETF, obligations, crypto-monnaies ou instruments personnalisés comme des comptes d'épargne avec intérêts programmés.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="list" data-title="🔲 Vue Grille de Cartes" alt="Page Liste des Actifs (Grille)">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="list-table" data-title="📋 Vue Tableau de Données" alt="Page Liste des Actifs (Tableau)">
</div>

## 📌 Qu'est-ce qu'un Actif ?

Un actif dans LibreFolio est un instrument financier comprenant :

- **Identité** : nom, ISIN, ticker ou autres identifiants
- **Catégorie** : action, ETF, obligation, crypto, matière première, etc.
- **Devise** : la devise dans laquelle l'actif est libellé
- **Fournisseur** : un fournisseur de prix optionnel qui récupère automatiquement les cours actuels et l'historique
- **Classification** : secteur et répartition géographique (graphiques en secteurs + carte du monde)
- **Transactions** : opérations d'achat, de vente, de dividendes et d'intérêts liées à un portefeuille

## 📋 Liste des Actifs

Accédez à **Assets** dans la barre latérale pour voir tous vos actifs. La page de liste propose :

- 🔀 **Mises en page Grille / Tableau** : Choisissez entre une grille visuelle basée sur des cartes ou un tableau de données dense et triable. Votre préférence de mise en page est automatiquement conservée dans le `localStorage` de votre navigateur et sera chargée lors des sessions futures.
- 🔎 **Recherche Intelligente** : Filtrez les actifs en temps réel en saisissant un nom, un ISIN, un ticker ou le nom d'un courtier.
- 🏷️ **Filtres par Type** : Filtrez la liste pour n'afficher que des classes spécifiques (ex. ETF, Actions, Obligations, Crypto).
- 🗃️ **Actifs Archivés** : Basculez entre les positions actives et les actifs archivés pour garder votre liste propre.
- ⏱️ **Sélecteur de Delta Temporel** : Modifiez la période utilisée pour calculer les variations de prix (ex. `1D`, `1W`, `1M`, `YTD`, `ALL`).
- 🔄 **Synchronisation & Rafraîchissement** : Synchronisez les données de prix en temps réel pour tous les fournisseurs configurés ou rafraîchissez manuellement la liste.
- 🖱️ **Menu Contextuel** : Faites un clic droit sur n'importe quelle ligne dans la mise en page en tableau pour des actions rapides (Modifier, Supprimer, Synchroniser).

Cliquez sur n'importe quelle carte d'actif pour naviguer vers sa **[page de détail](detail/index.md)**.

## 🧭 Fonctionnalités

### ➕ [Créer & Modifier](create-edit.md)

Guide étape par étape pour créer de nouveaux actifs, configurer les fournisseurs et modifier des actifs existants.

### 📊 [Page de Détail de l'Actif](detail/index.md)

Le cœur de l'analyse d'actif — graphique interactif, signaux techniques, mesures, classification et éditeur de données.

### 🔌 [Fournisseurs](providers/index.md)

Récupération automatique des prix depuis Yahoo Finance, justETF, CSS Scraper ou le moteur d'investissement programmé.

---

## 📡 Prix en temps réel & Ticker en temps réel

Pour vous tenir informé des mouvements du marché sans forcer des rafraîchissements constants de la page, LibreFolio affiche des badges de prix compacts et en direct sur le **Tableau de bord** et les pages de **Détail d'actif**.

### ⏱️ Interrogation Automatique (Polling)

Lorsque vous consultez ces pages, votre navigateur interroge le backend toutes les **30 secondes** pour obtenir les prix actuels des actifs. Ce processus s'exécute silencieusement en arrière-plan et n'est absolument pas bloquant (l'interface utilisateur est prête instantanément, et les prix se chargent à leur arrivée).

### 🎨 Indicateurs Visuels

Les badges changent de couleur dynamiquement pour indiquer les mouvements de prix récents par rapport à la dernière interrogation :

* 🟢 **Vert (Hausse)** : Le prix de l'actif a augmenté.
* 🔴 **Rouge (Baisse)** : Le prix de l'actif a diminué.
* ⚪ **Gris (Neutre)** : Le prix est inchangé, en cours de chargement, ou le marché est actuellement fermé.

!!! note "Fermeture du Marché & Fallbacks"

    Pendant les week-ends ou les fermetures de marché, le ticker en temps réel affichera le dernier prix de clôture disponible dans un badge gris neutre.

### 🔌 Mise en cache & Planificateur d'arrière-plan

Pour garantir des temps de chargement rapides et éviter que votre instance ne soit limitée en débit ou bloquée par des fournisseurs externes (tels que Yahoo Finance), LibreFolio utilise une stratégie à double couche :

1. **Planificateur d'arrière-plan** : Un démon d'arrière-plan sur le serveur rafraîchit les cours de tous les actifs actifs à intervalle régulier (par défaut : toutes les 10 minutes, configurable par les administrateurs dans les Paramètres Globaux). Cela maintient la base de données et le cache de prix local à jour.
2. **Cache d'interrogation à la demande** : Lorsque le frontend interroge le backend, il lit ce cache local. Si le cache est froid, le fournisseur récupère le prix et le stocke avec un TTL (Time-To-Live) de 120 secondes. Les rafraîchissements de page ultérieurs ou les vues du tableau de bord d'autres utilisateurs accèdent directement au cache local.

---

## 🔗 Liens connexes

- 📚 **[Théorie Financière — Types d'Actifs](../../financial-theory/instruments/asset-types/index.md)** — Actions, ETF, Obligations, Crypto, etc.
- 💱 **[Taux FX](../fx/index.md)** — Taux de change utilisés pour la conversion entre devises
