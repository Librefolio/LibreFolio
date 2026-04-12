# ➕ Ajouter une Paire de Devises

Pour ajouter une nouvelle paire de devises à votre tableau de bord FX :

1. Cliquez sur **"Ajouter une paire"** sur la page de la liste FX
2. Sélectionnez les **deux devises** via le menu déroulant de recherche
3. Le système détecte automatiquement les **routes de données** disponibles — routes directes et routes en chaîne
4. Sélectionnez la route que vous préférez et cliquez sur **Confirmer** — la paire est créée et la synchronisation des données commence automatiquement

---

## 🔗 Routes Directes

Si un fournisseur prend en charge les deux devises directement (ex: ECB pour EUR→USD), vous verrez une section **Routes directes** :

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="add-pair-routes" alt="Add Pair — Direct Routes" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Routes en Chaîne

Pour les paires exotiques (ex: RON→JPY) où aucun fournisseur ne couvre seul les deux devises, le système construit des **chaînes de conversion** — des chemins en plusieurs étapes via des devises intermédiaires :

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="add-pair-chain" alt="Add Pair — Chain Routes" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! example "Exemple de chaîne"

    **RON → JPY** via ECB :

    1. RON → EUR (ECB fournit RON/EUR)
    2. EUR → JPY (ECB fournit EUR/JPY)

    Le taux final est calculé en multipliant les taux intermédiaires.

---

## 🧭 Fonctionnement de la Découverte de Routes

Lorsque vous sélectionnez deux devises, LibreFolio interroge tous les fournisseurs installés pour trouver :

- 🔗 **Routes directes** : un seul fournisseur qui couvre les deux devises
- 🔀 **Routes en chaîne** : deux fournisseurs ou plus qui, ensemble, peuvent connecter les devises via une devise intermédiaire (ex: EUR)

Chaque route affiche :

- 🏛️ Le nom et l'icône du **fournisseur**
- ➡️ La **direction** (devise de base → devise de contrepartie)
- 🔢 Pour les chaînes : la **devise intermédiaire** et le **nombre de sauts**

Vous pouvez choisir n'importe quelle route disponible en fonction de votre préférence pour la source de données, la période de couverture ou la fréquence de mise à jour.

Pour plus de détails techniques sur l'algorithme de routage, consultez la documentation développeur : [FX Configuration & Routing](../../developer/backend/fx/configuration.md).
