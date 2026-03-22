# 🔌 Configuration des fournisseurs

Dans LibreFolio, chaque paire de devises est alimentée par un ou plusieurs **fournisseurs de données** — des banques centrales qui fournissent les taux de change. La Configuration des fournisseurs vous permet d'**afficher** et de modifier les fournisseurs utilisés pour une paire spécifique.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="provider-config" alt="Configuration des fournisseurs" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔓 Comment y accéder

Cliquez sur le bouton **Fournisseur** (⚙️) dans la barre d'outils du graphique sur la page de détail de la paire. Cela ouvre la **fenêtre modale** de configuration des fournisseurs affichant la configuration actuelle des routes.

---

## 📋 Ce que vous voyez

La fenêtre modale affiche :

- 🛤️ **Route(s) actuelle(s)** — La/les source(s) de données active(s) pour cette paire, par ordre de priorité
- 🔀 **Type de route** — Qu'il s'agisse d'une route **Directe** (un seul fournisseur) ou d'une route **en chaîne** (conversion via une devise intermédiaire)
- 🏛️ **Détails du fournisseur** — Nom, icône et devise de base de chaque fournisseur dans la route

---

## 🔧 Modifier les fournisseurs

Pour changer la source de données d'une paire :

1. Ouvrez la fenêtre modale de Configuration des fournisseurs
2. **Supprimez** la route actuelle si nécessaire
3. **Ajoutez une nouvelle route** — le système identifiera automatiquement les routes disponibles (identique à l'[ajout d'une nouvelle paire](../add-pair.md))
4. Sélectionnez la nouvelle route et **confirmez**

La prochaine synchronisation récupérera les données depuis le nouveau fournisseur.

---

## 🔢 Priorité et itinéraire de secours

Lorsque plusieurs routes sont configurées pour une paire :

- **Le système teste les routes** dans l'**ordre de priorité** (en haut = priorité la plus élevée)
- Si le fournisseur principal échoue (délai d'attente, erreur API), le système bascule automatiquement vers l'**itinéraire de secours** suivant
- Vous pouvez **réorganiser** les routes pour changer les priorités

!!! example "Exemple d'itinéraire de secours"
 EUR/USD configurée avec :

 1. **BCE** (principale) — Banque Centrale Européenne
 2. **Fed** (secours) — Réserve fédérale

 Si l'API de la BCE est inaccessible pendant la synchronisation, le système utilise automatiquement la Fed à la place.

---

## 📚 Liens associés

- ➕ **[Ajouter une paire](../add-pair.md)** — Découverte complète des routes (directes + en chaîne)
- 🔄 **[Synchronisation](../sync.md)** — Comment la synchronisation utilise les fournisseurs configurés
- 📋 **[Liste des fournisseurs FX](../../../developer/backend/fx/providers_list.md)** — Détails techniques sur chaque fournisseur (BCE, Fed, Banque d'Angleterre, BNS)

!!! tip "🔗 Comment les routes en chaîne sont calculées"
 Pour l'algorithme mathématique derrière les conversions multi-saut, voir [Algorithme de chaîne FX](../../../developer/frontend/fx-chain-algorithm.md).
