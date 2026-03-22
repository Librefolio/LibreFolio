# ➕ Ajouter une paire de devises

Pour ajouter une nouvelle paire de devises à votre tableau de bord FX :

1. Cliquez sur **« Ajouter une paire »** sur la page de la liste FX
2. Sélectionnez les **deux devises** à l’aide de la liste déroulante de recherche
3. Le système détecte automatiquement les **itinéraires de données** disponibles — à la fois directs et en chaîne
4. Sélectionnez l’itinéraire de votre choix et cliquez sur **Confirmer** — la paire est créée et la synchronisation des données commence automatiquement

---

## 🔗 Itinéraires directs

Si un fournisseur prend en charge les deux devises directement (par ex. la BCE pour EUR → USD), vous verrez une section **Itinéraires directs** :

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="add-pair-routes" alt="Ajouter une paire — Itinéraires directs" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Itinéraires en chaîne

Pour les paires exotiques (par ex. RON → JPY) où aucun fournisseur unique ne couvre les deux devises, le système construit des **chaînes de conversion** — des chemins à étapes multiples via des devises intermédiaires :

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="add-pair-chain" alt="Ajouter une paire — Itinéraires en chaîne" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! example "Exemple de chaîne"
 **RON → JPY** via la BCE :

 1. RON → EUR (la BCE fournit RON/EUR)
 2. EUR → JPY (la BCE fournit EUR/JPY)

 Le taux final est calculé en multipliant les taux intermédiaires.

---

## 🧭 Fonctionnement de la découverte des itinéraires

Lorsque vous sélectionnez deux devises, LibreFolio interroge tous les fournisseurs installés pour trouver :

- 🔗 **Itinéraires directs** : un fournisseur unique qui couvre les deux devises
- 🔀 **Itinéraires en chaîne** : deux fournisseurs ou plus qui, ensemble, peuvent relier les devises par une devise intermédiaire (par ex. l’EUR)

Chaque itinéraire affiche :

- 🏛️ Le **fournisseur** (nom et icône)
- ➡️ La **direction** (de base à cotation)
- 🔢 Pour les chaînes : la **devise intermédiaire** et le **nombre de sauts**

Vous pouvez choisir n’importe quel itinéraire disponible en fonction de vos préférences concernant la source de données, la période de couverture ou la fréquence de mise à jour.

Pour les détails techniques sur l’algorithme de routage, consultez la documentation développeur : [Configuration et routage FX](../../developer/backend/fx/configuration.md).
