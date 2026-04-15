# ➕ Créer et modifier des actifs

## Créer un nouvel actif

1. Cliquez sur **+ Nouvel actif** sur la page des actifs
2. Utilisez la **Recherche Intelligente** pour trouver votre actif : tapez un nom, ISIN ou ticker et LibreFolio recherche en parallèle parmi plusieurs fournisseurs (Yahoo Finance, justETF, CSS Scraper)
3. Sélectionnez un résultat pour **remplir automatiquement** le nom, les identifiants, la devise, la distribution sectorielle/géographique et la configuration du fournisseur
4. Ou remplissez manuellement :
    - **Nom** (requis)
    - **Catégorie** (requis) : Action, ETF, Obligation, Crypto, Matière première, P2P, Index, etc.
    - **Devise** (requis) : la devise dans laquelle l'actif est libellé
    - **Identifiants** : ISIN, ticker, CUSIP, SEDOL, etc.
5. Optionnellement, configurez un **[Fournisseur](providers/index.md)** pour la récupération automatique des prix
6. Optionnellement, ajoutez des distributions **Sectorielles** et **Géographiques**
7. Cliquez sur **Enregistrer**

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="create-modal" alt="Modale de création d'actif" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

## 🧪 Tester la configuration du fournisseur

Après avoir configuré un fournisseur, cliquez sur **Tester la configuration** pour vérifier que les données de prix peuvent être récupérées. Le test vérifie :

- **Prix actuel** : récupère le dernier prix
- **Historique** : récupère les données de prix historiques (si pris en charge)

Les résultats sont affichés en ligne avec les temps d'exécution. Un avertissement ⚠️ signifie que l'opération n'est pas prise en charge par ce fournisseur (par exemple, le CSS Scraper ne prend pas en charge l'historique).

## 🔌 Attribution d'un fournisseur

Chaque actif peut avoir un seul fournisseur de prix attribué. Consultez [Fournisseurs](providers/index.md) pour plus de détails sur les fournisseurs disponibles et leur configuration.

## ⏱️ Intervalle de récupération

L'intervalle de récupération contrôle la fréquence à laquelle LibreFolio actualise automatiquement les données de prix de l'actif. La valeur par défaut est 24 heures (`24:00`). Format : `HH:MM`.

## 🛠️ Modifier un actif

Cliquez sur le bouton **Modifier** (✏️) sur la [page de détails](detail/index.md) pour ouvrir la fenêtre modale de l'actif avec tous les champs pré-remplis. Tous les champs sont modifiables, y compris la configuration du fournisseur et les distributions.

## 🔗 Liens connexes

- 📊 **[Page de détails de l'actif](detail/index.md)** — Visualiser et analyser les données de l'actif
- 🔌 **[Fournisseurs](providers/index.md)** — Fournisseurs de prix disponibles
