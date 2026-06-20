# ➕ Ajouter une paire de devises

Pour ajouter une nouvelle paire de devises à votre tableau de bord FX :

1. Cliquez sur **"Add Pair"** sur la page de la liste FX
2. Sélectionnez les **deux devises** à l'aide du menu déroulant de recherche
3. Le système découvre automatiquement les **routes de données** disponibles — tant les routes directes que les routes en chaîne
4. Sélectionnez la route que vous préférez et cliquez sur **Confirm** — la paire est créée et la synchronisation des données commence automatiquement

---

## 🛤️ Routes de conversion (Directes et en Chaîne)

Lorsque vous sélectionnez une devise de base et une devise de cotation, LibreFolio interroge tous les fournisseurs installés pour découvrir les meilleures routes de taux de change disponibles.

<div class="lf-screenshot-carousel" data-carousel="carousel-fx-routes" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="fx" data-name="add-pair-routes" data-title="🔗 Routes Directes" alt="Ajouter une paire — Routes Directes">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="fx" data-name="add-pair-chain" data-title="🔀 Routes en Chaîne (Multi-étapes)" alt="Ajouter une paire — Routes en Chaîne">
</div>

### 🔗 Routes Directes
Si un fournisseur prend directement en charge les taux de change entre les deux devises (par exemple, la BCE fournissant les taux pour EUR 🇪🇺 / USD 🇺🇸), le système l'affiche comme une option de route directe.

### 🔀 Routes en Chaîne
Pour les paires exotiques (par exemple, RON 🇷🇴 / JPY 🇯🇵) pour lesquelles aucune banque centrale ne publie directement de taux, le système construit automatiquement des **chaînes de conversion** — des chemins multi-étapes via des devises intermédiaires (généralement EUR 🇪🇺 ou USD 🇺🇸).

!!! example "Exemple de Chaîne"

    **RON 🇷🇴 → JPY 🇯🇵** via la BCE :

    1. RON 🇷🇴 → EUR 🇪🇺 (la BCE fournit RON 🇷🇴 / EUR 🇪🇺)
    2. EUR 🇪🇺 → JPY 🇯🇵 (la BCE fournit EUR 🇪🇺 / JPY 🇯🇵)

    Le taux final est calculé en multipliant les taux intermédiaires.

---

## 🧭 Fonctionnement de la découverte de routes

Lorsque vous sélectionnez deux devises, LibreFolio interroge tous les fournisseurs installés pour trouver :

- 🔗 **Routes directes** : un seul fournisseur qui couvre les deux devises
- 🔀 **Routes en chaîne** : deux fournisseurs ou plus qui, ensemble, peuvent connecter les devises via une devise intermédiaire (par exemple, EUR 🇪🇺)

Chaque route affiche :

- 🏛️ Le nom et l'icône du **fournisseur**
- ➡️ La **direction** (base → cotation)
- 🔢 Pour les chaînes : la **devise intermédiaire** et le **nombre d'étapes**

Vous pouvez choisir n'importe quelle route disponible en fonction de votre préférence pour la source de données, la période de couverture ou la fréquence de mise à jour.

!!! info "Pour les Curieux : En coulisses"

    Si vous êtes intéressé par les détails mathématiques de la manière dont les chaînes de conversion multi-étapes sont calculées et routées, vous pouvez consulter la documentation pour les développeurs : [FX Configuration & Routing](../../developer/backend/fx/configuration.md) et [FX Chain Algorithm](../../developer/frontend/fx-chain-algorithm.md). 
 
    *Note : Cette documentation technique est destinée uniquement aux développeurs et n'est pas requise pour utiliser cette fonctionnalité.*
