# 🔌 Configuration des Fournisseurs

Chaque paire de devises dans LibreFolio s'appuie sur un ou plusieurs **fournisseurs de données** — des banques centrales qui fournissent les données de taux de change. La Configuration des Fournisseurs vous permet de visualiser et de modifier les fournisseurs utilisés pour une paire spécifique.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="provider-config" alt="Configuration des Fournisseurs" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔓 Comment y accéder

Cliquez sur le bouton **Fournisseur** (⚙️) dans la barre d'outils du graphique sur la page de détails de la paire. Cela ouvre la fenêtre modale de configuration des fournisseurs affichant la configuration actuelle des routes.

---

## 📋 Ce que vous voyez

La fenêtre modale affiche :

- 🛤️ **Route(s) actuelle(s)** — La ou les sources de données actives pour cette paire, par ordre de priorité
- 🔀 **Type de route** — S'il s'agit d'une route **Directe** (fournisseur unique) ou d'une route en **Chaîne** (multi-sauts via une devise intermédiaire)
- 🏛️ **Détails du fournisseur** — Nom, icône et devise de base de chaque fournisseur dans la route

---

## 🔧 Modifier les Fournisseurs

Vous pouvez configurer **un ou plusieurs** fournisseurs de données pour chaque paire. Plusieurs fournisseurs agissent comme une **chaîne de fallback** — si la source primaire échoue, le système tente automatiquement la route suivante.

Pour modifier ou ajouter des fournisseurs :

1. Ouvrez la fenêtre modale de Configuration des Fournisseurs
2. **Supprimez** la route actuelle si nécessaire
3. **Ajoutez une nouvelle route** — le système détectera les routes disponibles (comme lors de l' [ajout d'une nouvelle paire](../add-pair.md))
4. **Réorganisez** les routes pour définir les priorités (glisser-déposer ou boutons fléchés)
5. Cliquez sur **Enregistrer** — la prochaine synchronisation récupérera les données du fournisseur disponible ayant la priorité la plus élevée

---

## 🔢 Priorité & Fallback

Lorsque plusieurs routes sont configurées pour une paire :

- Les routes sont testées **par ordre de priorité** (le haut = priorité maximale)
- Si le fournisseur primaire échoue (timeout, erreur API), le système bascule automatiquement vers la route suivante
- Vous pouvez **réorganiser** les routes pour modifier les priorités

!!! example "Exemple de fallback"

    EUR/USD configuré avec :

    1. **ECB** (primaire) — Banque Centrale Européenne
    2. **FED** (fallback) — Réserve Fédérale

    Si l'API de l'ECB est inaccessible pendant la synchronisation, le système utilise automatiquement la FED à la place.

---

## 📚 Liens connexes

- ➕ **[Ajouter une Paire](../add-pair.md)** — Découverte complète des routes (routes directes + en chaîne)
- 🔄 **[Synchronisation](../sync.md)** — Comment la synchronisation utilise les fournisseurs configurés
- 🔌 **[Fournisseurs FX](../providers/index.md)** — Guide utilisateur et détails sur chaque fournisseur (ECB, FED, BOE, SNB)

!!! tip "🔗 Comment les routes en chaîne sont calculées"

    Pour l'algorithme mathématique derrière les chaînes de conversion multi-sauts, voir [FX Chain Algorithm](../../../developer/frontend/fx-chain-algorithm.md).
