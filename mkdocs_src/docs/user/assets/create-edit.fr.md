# ➕ Créer et modifier des actifs

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-create" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="create-modal" data-title="➕ Formulaire de création manuelle" alt="Modale de création manuelle">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="create-wizard-modal" data-title="🧙 Formulaire d'auto-création de l'assistant d'importation" alt="Créer un actif via l'assistant">
</div>

## 🚀 Flux de création d'actifs

Dans LibreFolio, vous pouvez créer de nouveaux actifs de deux manières différentes :

=== "Création manuelle (avec recherche intelligente)"

    ```mermaid
    flowchart LR
        A[Début : Cliquer sur '+ Nouvel actif'] --> B[Saisir le nom, l'ISIN ou le Ticker dans la recherche intelligente]
        B --> C{Correspondance trouvée ?}
        C -->|Oui| D[Remplissage automatique des détails via les fournisseurs externes]
        C -->|Non| E[Saisir manuellement le nom, la catégorie et la devise]
        D --> F[Ajuster la configuration / Assigner un fournisseur de prix]
        E --> F
        F --> G[Cliquer sur Enregistrer]
        G --> H[Actif ajouté à la bibliothèque]
    ```

=== "Auto-création via l'importation de courtier"

    ```mermaid
    flowchart LR
        A[Début : Télécharger le rapport CSV dans l'assistant d'importation] --> B[Analyser les lignes du rapport]
        B --> C{ID de l'actif reconnu ?}
        C -->|Oui| D[Correspondance automatique avec un actif existant]
        C -->|Non| E[Afficher un avertissement ⚠️ et le bouton 'Créer']
        E --> F[Cliquer sur 'Créer' pour ouvrir la modale pré-remplie]
        F --> G[Enregistrer l'actif pour résoudre le mappage]
        G --> D
        D --> H[Valider toutes les transactions]
    ```

## 🧪 Test de la configuration du fournisseur

Après avoir configuré un fournisseur, cliquez sur **Tester la configuration** pour vérifier que les données de prix peuvent être récupérées. Le test vérifie :

- **Prix actuel** : récupère le prix le plus récent
- **Historique** : récupère les données de prix historiques (si pris en charge)

Les résultats sont affichés en ligne avec les temps d'exécution. Un avertissement ⚠️ signifie que l'opération n'est pas prise en charge par ce fournisseur (par exemple, le CSS Scraper ne prend pas en charge l'historique).

## 🔎 Détails de la recherche intelligente

La recherche intelligente interroge d'abord la recherche propre à chaque fournisseur. Si aucun fournisseur
pris en charge ne trouve rien, LibreFolio peut tenter une recherche de liens web pour résoudre les pages
de fournisseurs en candidats d'actifs. Pour Borsa Italiana, cela signifie qu'une URL de fond/détail peut devenir
un actif prêt à être enregistré avec les `provider_params` nécessaires pour évaluer le fond par son code interne.

Pour les fonds Borsa Italiana, l'ISIN visible identifie le fond lorsqu'il est disponible, mais la tarification
utilise le code de fond interne Borsa enregistré dans la configuration du fournisseur. La valeur liquidative
actuelle n'est utilisée que si elle date d'aujourd'hui ; l'historique contient un point à sa date réelle.

## 🔌 Assignation d'un fournisseur

Chaque actif peut avoir un seul fournisseur de prix assigné. Voir [Fournisseurs](providers/index.md) pour plus de détails sur les fournisseurs disponibles et leur configuration.

## 🛠️ Modifier un actif

Cliquez sur le bouton **Modifier** (✏️) sur la [page de détails](detail/index.md) pour ouvrir la modale de l'actif avec tous les champs pré-remplis. Tous les champs sont modifiables, y compris la configuration du fournisseur et les distributions.

Le champ **Autres identifiants** est une liste modifiable d'identifiants alternatifs. Les importations
et les fournisseurs peuvent y ajouter des étiquettes de courtier, des codes techniques ou des identifiants
de secours ; chaque valeur reste un élément de liste distinct.

## 🔗 Liens associés

- 📊 **[Page de détails de l'actif](detail/index.md)** — Consulter et analyser les données de l'actif
- 🔌 **[Fournisseurs](providers/index.md)** — Fournisseurs de prix disponibles
