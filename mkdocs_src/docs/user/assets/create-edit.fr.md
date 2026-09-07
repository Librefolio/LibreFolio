# ➕ Créer et modifier des actifs

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-create" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="create-modal" data-title="➕ Manual Creation Form" alt="Manual Create Modal">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="create-wizard-modal" data-title="🧙 Import Wizard Auto-Creation Form" alt="Create Asset from Wizard">
</div>

## 🚀 Processus de création d'actifs {: #asset-creation-flows }

Dans LibreFolio, vous pouvez créer de nouveaux actifs de deux manières différentes :

=== "Création manuelle (avec recherche intelligente)"

 ```mermaid
 flowchart LR
 A[Départ : cliquer sur « + Nouvel actif »] --> B[Saisir le nom, l'ISIN ou le ticker dans la recherche intelligente]
 B --> C{Correspondance trouvée ?}
 C -->|Oui| D[Remplissage automatique des détails depuis les fournisseurs externes]
 C -->|Non| E[Saisie manuelle du nom, de la catégorie et de la devise]
 D --> F[Ajuster la configuration / Attribuer le fournisseur de prix]
 E --> F
 F --> G[Cliquer sur Enregistrer]
 G --> H[Actif ajouté à la bibliothèque]
 ```

=== "Création automatique à partir d'un import de courtier"

 ```mermaid
 flowchart LR
 A[Départ : téléverser le rapport CSV dans l'assistant d'importation] --> B[Analyser les lignes du rapport]
 B --> C{Identifiant d'actif reconnu ?}
 C -->|Oui| D[Correspondance automatique avec l'actif existant]
 C -->|Non| E[Signaler un avertissement ⚠️ et afficher le bouton « Créer »]
 E --> F[Cliquer sur « Créer » pour ouvrir la fenêtre pré-remplie]
 F --> G[Enregistrer l'actif pour résoudre la correspondance]
 G --> D
 D --> H[Valider toutes les transactions]
 ```

## 🧪 Tester la configuration du fournisseur

Après avoir configuré un fournisseur, cliquez sur **Tester la configuration** pour vérifier que les données de prix peuvent être récupérées. Le test vérifie :

- **Prix actuel** : récupère le dernier prix
- **Historique** : récupère les données de prix historiques (si cette fonction est prise en charge)

Les résultats sont affichés directement dans la page, avec les temps d'exécution. Un avertissement ⚠️ signifie que l'opération n'est pas prise en charge par ce fournisseur (par exemple, CSS Scraper ne prend pas en charge l'historique).

## 🔎 Détails de la recherche intelligente

La recherche intelligente interroge d'abord le moteur de recherche propre à chaque fournisseur. Si un fournisseur pris en charge ne trouve rien, LibreFolio peut tenter une recherche de liens web du mieux possible et reconvertir les pages des fournisseurs en candidats-actifs. Pour Borsa Italiana, cela signifie qu'une URL de fonds/détail peut devenir un actif prêt à être enregistré, avec le `provider_params` nécessaire pour évaluer le fonds grâce à son code interne.

Pour les fonds Borsa Italiana, l'ISIN visible identifie le fonds lorsqu'il est disponible, mais la valorisation utilise le code Borsa interne du fonds enregistré dans la configuration du fournisseur. La NAV courante n'est utilisée que si elle est datée du jour ; l'historique contient un point de NAV à sa date réelle.

## 🔌 Attribution du fournisseur

Chaque actif peut se voir attribuer un fournisseur de prix. Voir [Fournisseurs](providers/index.md) pour plus de détails sur les fournisseurs disponibles et leur configuration.

## 🛠️ Modifier un actif {: #editing-an-asset }

Cliquez sur le bouton **Modifier** (✏️) de la [page de détail](detail/index.md) pour ouvrir la fenêtre de l'actif avec tous les champs pré-remplis. Tous les champs sont modifiables, y compris la configuration du fournisseur et les distributions.

Le champ **Autres identifiants** est une liste modifiable d'identifiants alternatifs. Les importations et les fournisseurs peuvent y ajouter des libellés de courtier, des codes techniques ou des identifiants fallback ; chaque valeur reste un élément de liste distinct.

## 🗺️ Répartition géographique et distribution sectorielle manuelles

Les fournisseurs renseignent la **répartition géographique** et la **distribution sectorielle** lorsqu'ils le peuvent — mais de nombreux actifs (instruments personnalisés, obligations, investissements programmés, ou simplement des actifs dont le fournisseur ne fournit pas de ventilation) arrivent sans aucune répartition. Vous pouvez toujours définir ou corriger les deux à la main depuis la fenêtre de l'actif : elles alimentent les **graphiques d'allocation** du tableau de bord (anneaux géographique et sectoriel, à l'instant T et dans le temps) ainsi que le contexte de concentration de l'exportation IA.

Dans la fenêtre de l'actif ([création](#asset-creation-flows) ou [modification](#editing-an-asset)), ouvrez la zone **Classification** :

1. **Répartition géographique** — une ligne par pays/zone, avec son poids en pourcentage.
2. **Distribution sectorielle** — une ligne par secteur, avec son poids en pourcentage.

Pour chaque distribution, vous pouvez :

- **Ajouter une ligne** et choisir la zone/le secteur dans le menu déroulant, puis saisir le poids.
- **Modifier les poids en ligne** ; le **total** cumulé se trouve en bas de l'éditeur et devient **vert à exactement 100 %** — orange quand il manque quelque chose, rouge en cas de dépassement.
- **Supprimer** une ligne avec son bouton de suppression.

!!! tip "La règle des 100 %"

    Le tableau de bord normalise les répartitions partielles, mais un 100 % net donne les
    anneaux d'allocation les plus parlants. Si l'instrument est investi à 100 % dans un seul
    pays ou secteur, une seule ligne à 100 est à la fois valide et le choix le plus clair.

*(Des captures d'écran des deux éditeurs de distribution — `assets/detail-classification` existe déjà et montre la zone ; des gros plans dédiés des éditeurs sont prévus lors de la prochaine itération de la galerie.)*

## 🏷️ Un même instrument, plusieurs codes

La même valeur mobilière peut être connue sous plusieurs codes. Lorsque c'est le cas, LibreFolio conserve **un seul actif** et stocke les codes supplémentaires dans **Autres identifiants**, où ils sont recherchables et servent à reconnaître l'instrument lors des importations ultérieures.

Le choix du code qui va dans le champ **ISIN** principal n'est pas une question de goût :

!!! tip "Conserver le code coté comme ISIN principal"

    Un prix est la valeur de la dernière transaction : seul un code réellement négociable a donc
    un prix. Placez le code négociable dans **ISIN** et tout le reste dans **Autres identifiants** —
    sinon, aucun fournisseur ne pourra évaluer l'actif.

### Obligations d'État italiennes pour les particuliers (BTP Valore, BTP Più, BTP Italia)

Ces obligations sont émises sous un ISIN et négociées sous un autre :

| Phase | Code | Rôle |
|---|---|---|
| Souscription à l'émission | l'ISIN « CUM » | Donne droit à la **prime de fidélité** si vous les conservez jusqu'à l'échéance. **Non négociable**, donc aucun fournisseur ne le cote |
| Marché secondaire | un ISIN différent | Librement négocié et **coté** — c'est celui qui a un prix |

Pour vendre avant l'échéance, l'obligation est convertie au code de marché. Dans LibreFolio, les deux correspondent au même instrument, donc :

1. Placez l'**ISIN de marché** dans le champ **ISIN**.
2. Placez l'**ISIN CUM** dans **Autres identifiants**.
3. Enregistrez la **prime de fidélité**, lorsqu'elle est versée, comme une transaction **Intérêt** sur cet actif, datée du jour où vous la recevez.

L'étape 3 fonctionne même après l'échéance de l'obligation et la désactivation de l'actif : un actif désactivé reste sélectionnable précisément pour que le dernier coupon, le remboursement et la prime puissent être saisis.

!!! note "Lors d'une importation, on vous demande votre avis, on ne passe pas outre"

    Si un fichier de courtier contient le code CUM et que l'actif possède déjà le code de marché,
    l'importation demande lequel des deux doit prévaloir. Celui que vous ne choisissez pas est
    ajouté à **Autres identifiants** — rien n'est perdu, et l'importation suivante reconnaîtra
    l'obligation grâce à l'un ou l'autre code.

    Lorsque la même obligation apparaît dans deux fichiers sous des codes différents, l'étape
    **Unifier les actifs** de l'assistant d'importation les regroupe en un seul instrument avant
    toute autre décision.

## 🧲 Fusionner les actifs en double

Si le même instrument s'est retrouvé deux fois dans votre bibliothèque — un résultat courant lorsqu'une obligation est importée une fois sous son code de souscription et une autre fois sous son code de marché — vous pouvez fusionner l'un dans l'autre via l'action **Fusionner**, disponible sur la liste des actifs et sur la page de détail de l'actif.

L'opération est **destructive** ; elle se déroule donc en deux étapes bien distinctes :

1. **Choisissez l'actif à conserver.** Celui d'où vous êtes parti est celui qui disparaîtra ; vous choisissez celui qui lui survit dans tout le catalogue, actifs désactivés compris — une obligation arrivée à échéance est précisément le genre d'élément que l'on fusionne.
2. **Voyez ce qui bouge, puis tranchez la question de l'identité.** LibreFolio effectue d'abord un essai à blanc et affiche les chiffres réels : combien de transactions, de prix et d'événements seront réaffectés, et ce qu'il advient du fournisseur de prix. Lorsque les deux actifs portent une valeur pour le même identifiant, il demande lequel doit prévaloir ; l'autre est conservé dans **Autres identifiants**.

| Ce qui est déplacé | Ce qui se passe |
|---|---|
| Transactions | Réaffectées à l'actif survivant |
| Historique des prix | Réaffecté ; si les deux actifs ont un prix le même jour, celui du survivant l'emporte |
| Événements d'entreprise (dividendes, coupons) | Réaffectés ; les événements identiques sont regroupés, et les transactions qui y font référence les suivent |
| Attribution du fournisseur | Transférée uniquement si le survivant n'en a pas — sinon, le survivant garde la sienne |
| Identifiants | **Fusionnés**, jamais supprimés : tout ce que l'actif supprimé connaissait survit comme identifiant alternatif |

!!! warning "L'actif source est supprimé"

    La fusion ne peut pas être annulée depuis l'interface. Lisez l'aperçu avant de confirmer —
    il s'agit d'un décompte exact, pas d'une estimation.

!!! tip "Une fusion peut vous être proposée lors d'une importation"

    Lorsqu'une importation trouve **deux** actifs répondant au même code — la signature classique
    d'un doublon créé par une importation antérieure — l'assistant affiche un avis discret avec
    un bouton **Fusionner**, juste à l'endroit où vous pouvez voir les deux côte à côte. On ne
    propose jamais une fusion sur la seule ressemblance de nom : deux fonds du même émetteur sont
    censés se ressembler.

## 🔗 Voir aussi

- 📊 **[Page de détail de l'actif](detail/index.md)** — Consulter et analyser les données d'un actif
- 🔌 **[Fournisseurs](providers/index.md)** — Fournisseurs de prix disponibles
