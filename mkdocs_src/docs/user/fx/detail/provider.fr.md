# 🔌 Configuration des fournisseurs

Chaque paire de devises obtient ses taux à partir d'une ou plusieurs **routes** : une banque centrale qui cote la paire directement, ou une chaîne de conversions. Ici, vous voyez et modifiez les routes de la paire que vous consultez.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="provider-config" alt="Configuration du fournisseur" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔓 Comment y accéder

Sur la page de détail de la paire, cliquez sur **Fournisseurs** (🔧) dans la barre d'outils, à côté de **Synchroniser**. La fenêtre **Modifier les fournisseurs de la paire** s'ouvre.

---

## 📋 Ce que vous voyez

Sous **Routes de conversion**, chaque ligne est une route, par ordre de priorité :

- les devises, avec le fournisseur de chaque étape entre elles — survolez l'icône d'un fournisseur pour voir son nom et sa description ;
- le badge de priorité : **#1** est utilisé en premier ;
- ⚠️ lorsqu'un fournisseur a un avertissement sur les données, comme les taux mensuels de la SNB ;
- 🗑️ pour supprimer la route.

---

## 🔧 Modifier les fournisseurs

1. Cliquez sur **Ajouter une route de conversion** et choisissez une route sous **Conversion directe (1 étape)** ou **Conversion en chaîne**. Tapez dans la zone de recherche pour filtrer par fournisseur, devise ou pays.
2. Faites glisser les lignes pour définir leur priorité (sur téléphone, utilisez les flèches haut et bas).
3. Cliquez sur **Enregistrer la configuration** : la prochaine synchronisation utilisera les nouvelles routes.

??? note "🔗 Créer aussi des paires intermédiaires — lorsque vous choisissez une route en chaîne"

    Cochez cette option pour enregistrer chaque étape de la chaîne comme une paire à part entière, avec son fournisseur, afin que vous puissiez la synchroniser et la consulter séparément.

??? note "✍️ Plus aucune route — lorsque vous les supprimez toutes"

    La paire devient manuelle : **Synchroniser** est désactivé, et vous saisissez vous-même les taux dans l'[Éditeur de données](data-editor.md).

---

## 🔢 Priorité et fallback

Une synchronisation essaie les routes de haut en bas. Si l'une échoue — par exemple, si sa banque centrale ne répond pas — elle passe à la suivante ; la paire n'échoue que lorsque toutes les routes échouent. Avec EUR/USD défini sur **#1** ECB et **#2** FED, une synchronisation qui ne peut pas atteindre l'ECB utilise le taux de la FED à la place.

---

## 📚 Voir aussi

- ➕ **[Ajouter une paire](../add-pair.md)** — Découverte complète des routes (routes directes + en chaîne)
- 🔄 **[Synchronisation](../sync.md)** — Comment la synchronisation utilise les fournisseurs configurés
- 🔌 **[Fournisseurs FX](../providers/index.md)** — Guide d'utilisation et détails sur chaque fournisseur (ECB, FED, BOE, SNB)
- 🧮 **Pour les développeurs : [Algorithme de chaîne FX](../../../developer/frontend/fx-chain-algorithm.md)** — Comment les routes en chaîne sont trouvées et calculées
