# 🧙 Comment importer des transactions

L'**Assistant d'importation** transforme les rapports que vous téléchargez depuis votre courtier en transactions. Vous vérifiez ce qu'il a lu et levez ses doutes ; rien n'est enregistré tant que vous n'avez pas cliqué sur **Enregistrer Tout**.

---

## 🚀 Guide étape par étape

1. Exportez un rapport de transactions depuis votre courtier : sa page dans les **[Courtiers pris en charge](index.md)** indique quel fichier utiliser.
2. Sur la page **[Transactions](../index.md)**, cliquez sur **Importer** (:material-file-upload:).
3. Déposez le rapport dans l'assistant, attribuez-le à son courtier et suivez les étapes ci-dessous.
4. Cliquez sur **Importer N transactions** : les lignes s'ouvrent dans l'espace de travail groupé, pas encore enregistrées.
5. Jetez-y un dernier coup d'œil et cliquez sur **Enregistrer Tout**.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Modale d'import rapide" alt="Modale d'import rapide">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Étape 1 : Téléverser le fichier de rapport" alt="Étape 1 de l'assistant">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Étape 2 : Sélectionner les fichiers &amp; l'analyseur" alt="Étape 2 de l'assistant">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Étape 3 : Analyse &amp; traitement" alt="Étape 3 de l'assistant">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🗂️ Résolution des actifs" alt="Résolution des actifs">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Détection des doublons" alt="Détection des doublons">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Étape 4 : Vérification &amp; import" alt="Vérification et import">
</div>

---

## 🧙 Les étapes de l'assistant d'importation

Quatre étapes sont toujours présentes ; les autres n'apparaissent que lorsque vos fichiers en ont besoin, et la barre de progression n'affiche que les étapes de l'import en cours.

| Étape | Quand elle apparaît |
| :--- | :--- |
| 1 · **Téléverser** | Toujours |
| 2 · **Sélectionner** | Toujours |
| 3 · **Analyser** | Toujours |
| 🧬 **Unifier les actifs** | Le même titre apparaît sous plusieurs noms ou codes |
| 🔧 **Corrections** | L'importateur a enregistré des lignes qu'il n'a pas pu comprendre entièrement |
| 🧹 **Doublons** | Le même mouvement figure dans deux des fichiers que vous importez ensemble |
| 4 · **Révision** | Toujours |
| ⚖️ **Aligner avec la banque** | Lots de rapports uniquement, lorsque les chiffres de la banque diffèrent de ceux de LibreFolio |

### 📤 Étape 1 : Téléversement

Glissez vos rapports dans l'assistant, ou cliquez pour les choisir (CSV ou XLSX), puis attribuez chacun à son courtier — ou tous d'un coup avec **Courtier pour les téléversements**. Un courtier manquant peut être créé depuis la même liste (**Créer nouveau**).

- Chaque rapport que vous téléversez est conservé : pour en réutiliser un, passez cette étape avec **Suivant : Sélectionner**.
- Lorsqu'un compte arrive en plusieurs exports (par ex. [Danske Bank](danske-bank.md)), téléversez-les ensemble : s'il en manque un, l'assistant reste ici et le nomme.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Étape 1 de l'assistant : Téléversement" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

#### 🧭 Un fichier dans le mauvais courtier {: #wrong-broker }

Lorsque vous cliquez sur **Suivant : Sélectionner**, l'assistant vérifie chaque fichier que vous venez de téléverser par rapport au **Plugin d'Import par Défaut** de son courtier. Si ce plugin ne peut pas lire un fichier, celui-ci appartient probablement à un autre courtier, et l'assistant vous interroge à ce sujet avant de continuer (*Ce fichier appartient peut-être à un autre courtier*). De haut en bas, il affiche :

- **Assigné à** — le courtier dans lequel se trouve le fichier, avec son icône, et son plugin par défaut, marqué *ne sait pas le lire* ;
- **Notes du plugin** — pourquoi ce plugin ne peut pas lire le fichier, lorsqu'il en donne la raison : dans votre langue lorsqu'une traduction existe ;
- **Le déplacer vers** — le courtier dont le plugin par défaut *sait le lire*. Lorsque les plugins par défaut de plusieurs courtiers le lisent, l'invite liste ces courtiers à la place : choisissez-en un, le premier est déjà sélectionné.

Choisissez ensuite :

- **Déplacer**, avec l'icône du courtier choisi sous **Le déplacer vers** — le fichier est téléversé vers ce courtier, dans la même session, et retiré du mauvais courtier. Si le déplacement échoue, une erreur le signale et le fichier reste où il était ;
- **Le garder ici** — le fichier reste, et l'assistant le lit avec un autre plugin qui le peut, comme avant : vous le voyez dans la colonne **Plugin** de l'étape **Sélectionner** ;
- **Retirer** — le fichier est supprimé.

Une invite par fichier, l'une après l'autre (*Fichier 1 sur 3*) ; la fermer conserve le fichier. Si vous supprimez tous les fichiers que vous venez de téléverser, l'assistant reste sur **Téléverser**, prêt pour d'autres. Lorsqu'aucun de vos courtiers n'a de plugin par défaut qui lit le fichier, l'invite nomme les plugins qui le lisent — ou indique qu'aucun ne le peut — et propose seulement de le conserver ou de le supprimer.

Les courtiers sans plugin d'importation par défaut ne sont jamais questionnés, et les rapports que vous réutilisez sans les téléverser à nouveau non plus.

### 🗂️ Étape 2 : Sélection des fichiers

Le panneau de chaque courtier liste ses rapports stockés, les fichiers que vous venez de téléverser étant déjà cochés. Cochez les fichiers à lire et cliquez sur **Analyser (N)**.

L'importateur de chaque fichier est détecté pour vous : changez-le dans la colonne **Plugin** s'il est erroné, et pour un CSV que vous avez créé vous-même, choisissez **[Generic CSV](generic-csv.md)**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Étape 2 de l'assistant : Configuration de l'analyseur" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Les **lots de rapports** forment une seule carte, cochée dans son ensemble. **Lu comme**, dans son en-tête, change la façon dont le lot est lu, et le menu **⋮** de chaque fichier peut le retirer du lot (**Lire seul avec ‹plugin›**, **Retirer du lot**) — [détails](danske-bank.md#how-the-set-is-read).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-read-as" alt="Carte de lot de rapports dans Sélection des fichiers avec la liste Lire comme ouverte : Danske Bank (détecté) et Lire les fichiers un par un" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-file-menu" alt="Le menu ⋮ d'un fichier de liquidités dans un lot de rapports : Aperçu, Retirer du lot et Supprimer" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**L'analyse est désactivée ?** Un fichier coché n'a pas de plugin, ou un lot coché est incomplet ou seulement partiellement coché (un tiret dans sa case à cocher) : choisissez le plugin, utilisez **Téléverser le fichier manquant**, ou cochez ou décochez le lot entier.

### 🧠 Étape 3 : Analyse

LibreFolio lit chaque fichier, le vérifie et le résume dans un tableau :

| Colonne | Ce qu'elle compte |
| :--- | :--- |
| 📊 | Transactions lues |
| 🏦 | Titres trouvés |
| ✗ | Titres pas encore associés à vos actifs — vous les associez dans **Révision** |
| 🔴 | Problèmes de validation : lignes qui n'ont pas pu devenir des transactions |
| 🔧 | Champs à renseigner avant l'enregistrement (en rouge quand l'un bloque l'enregistrement) |
| ⚠️ | Avertissements de l'importateur, comme des lignes ignorées |

Les tuiles au-dessus du tableau comptent ce qui sera réellement importé ; **Voir tout** ouvre les détails.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Étape 3 de l'assistant : Analyse" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- **Avertissements** : **Continuer** les liste d'abord ; lisez-les, puis cliquez sur **Continuer quand même**.
- **Un fichier a échoué** : une bannière en explique la raison. Corrigez son plugin dans **Sélectionner**, puis cliquez sur **Réanalyser tout**.

### 🧩 Étapes qui n'apparaissent qu'en cas de besoin {: #only-when-needed }

Selon ce que l'étape **Analyser** trouve, jusqu'à trois étapes peuvent précéder **Révision**, dans cet ordre. Ouvrez celle que l'assistant vous montre :

??? abstract "🧬 Unifier les actifs — lorsque le même titre apparaît sous plusieurs noms ou codes"

    Vos fichiers décrivent le même titre plusieurs fois — sous deux noms ou codes, ou dans deux fichiers.
    Unifiez-le ici, sinon il devient deux actifs avec ses transactions réparties entre eux.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-assets-step" alt="Assistant d'importation — étape Unifier les actifs avec un groupe proposé">
    </div>

    Chaque carte correspond à un titre : une bordure **vert uni** signifie unifié, **ambre en pointillés** signifie à confirmer, **gris** signifie rien à décider.

    - **Confirmer** ou **Séparer** une proposition ; fusionnez ou séparez des cartes avec **⋮** (**Fusionner avec…**,
      **Retirer du groupe**) ou par glisser-déposer.
    - **Cliquez sur un badge de code** pour en faire le code principal (⭐) — choisissez celui sur lequel les prix sont cotés ; les
      autres restent comme alternatives.
    - **Renommez** avec le crayon ; un titre déjà présent dans votre bibliothèque (**en archive**) conserve son nom.
    - **Continuer** attend qu'aucune proposition ne soit ouverte : **Tout confirmer (N)** les règle d'un coup, et
      **Rétablir le regroupement automatique** recommence.

??? warning "🔧 Corrections — lorsque l'importateur a enregistré des lignes qu'il n'a pas pu comprendre entièrement"

    L'importateur a enregistré des lignes qu'il n'a pas pu comprendre entièrement — aujourd'hui, des lignes issues des rapports
    de [Crédit Agricole](credit_agricole.md) et de [Danske Bank](danske-bank.md).

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-fix-step" alt="Assistant d'importation — étape Corrections avec des lignes signalées">
    </div>

    Les lignes sont groupées par question. Donnez une réponse à chacune :

    - **Corriger** : choisissez le type et, le cas échéant, le titre et la quantité, puis
      **Appliquer la correction**. Des frais ou un impôt peuvent relever de **Aucun instrument (frais du courtier)**.
    - **Scinder** : séparez le prix des commissions, impôts ou intérêts courus figurant sur votre
      note d'opération.
    - **Garder tel quel** : acceptez ce que l'importateur a lu.

    **Ligne N dans le fichier** affiche la ligne d'origine, et **Restaurer** annule une réponse. **Continuer** attend
    chaque réponse ; **Conserver les N lignes restantes telles que lues** répond à toutes les questions ouvertes.

??? note "🧹 Doublons — lorsque le même mouvement figure dans deux des fichiers que vous importez ensemble"

    Le même mouvement figure dans deux des fichiers que vous importez ensemble, comme un relevé annuel et un relevé
    trimestriel. Les correspondances avec des transactions déjà enregistrées n'ouvrent pas cette étape : **Révision** les signale.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicates-step" alt="Assistant d'importation — étape Doublons avec une paire inter-fichiers">
    </div>

    - **Priorité des fichiers** : faites glisser les fichiers dans l'ordre auquel vous faites confiance et cliquez sur **Recalculer par priorité**.
      Chaque groupe conserve la copie du fichier le plus prioritaire — jamais une copie déjà enregistrée ou en attente dans l'espace de travail
      groupé.
    - **Garder** : cochez les copies à importer, ligne par ligne ; **Réinitialiser** rétablit le choix automatique.
    - **Comparer** affiche les copies côte à côte, les différences mises en évidence.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-nway-compare" alt="Modale de comparaison à N voies avec les différences champ par champ mises en évidence">
    </div>

    Les groupes sont listés sous **Chevauchement total** (copies identiques) et **Chevauchement partiel** (quelque chose
    diffère).

### 📦 Étape 4 : Vérification {: #review }

Chaque ligne à importer dans une seule grille — statut, date, type, titre, courtier, quantité, liquidités et tags,
plus le fichier lorsque vous en importez plusieurs.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Grille Vérification et import" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

#### 🗂️ Associer chaque titre

Le panneau **Résoudre les actifs** au-dessus de la grille liste les titres de vos fichiers. Associez chacun :

- Recherchez **Dans cet import** et **Dans l’archive** (votre bibliothèque) depuis un seul champ. Les correspondances probables
  viennent en premier, avec un badge de confiance (**Exacte** à **Faible**) ; une correspondance unique est déjà sélectionnée.
- **Créer « … »** ouvre le formulaire de nouvel actif, prérempli avec le nom et les codes issus du rapport.
- ✏️ **Inspecter / modifier** ouvre l'actif choisi ; **Fusionner** apparaît lorsque deux de vos actifs correspondent.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Panneau de résolution des actifs" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Si le code du rapport diffère de celui de l'actif ou du fournisseur de prix, LibreFolio vous demande lequel est
le principal. Le code du fournisseur, celui qui porte les prix, est présélectionné ; les autres restent comme
alternatives. Une note ambre sur un nouvel actif, comme une échéance possible, n'est qu'un conseil.

#### 🚦 Lire les badges de statut

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Badges de détection des doublons" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

| Badge | Signification | Coché au départ ? |
| :--- | :--- | :--- |
| **✓ Unique** | Rien de similaire n'est enregistré | ✅ |
| **ℹ Doublon possible** | Une transaction enregistrée a le même type, la même date, la même quantité et le même montant, mais une autre description | ✅ — vérifiez-la |
| **⚠ Doublon probable** | Une transaction enregistrée correspond, description comprise | ⬜ |
| **⧉ Doublon dans le lot** | Copie exacte d'une autre ligne de cet import, ou de l'espace de travail groupé | ⬜ |
| **≈ Doublon possible du lot** | La même chose, avec une autre description | ✅ — vérifiez-la |
| **✗ Non résolu** | Son titre n'est pas encore associé | ✅ — associez-le ou décochez-le |
| **⛔ Avant l'ouverture** | Datée avant la date d'ouverture du courtier | Ne peut pas être importée |
| **⏮ Déjà dans LibreFolio** | Lots de rapports : plus anciens que l'historique détenu par LibreFolio ; masqués derrière un compteur | Ne peut pas être importée |

Cliquez sur un badge de doublon pour comparer la ligne avec son jumeau ; une bannière explique pourquoi des lignes sont décochées. Une
conversion de devise est une seule ligne, importée entièrement.

#### ⛔ Lignes antérieures à la date d'ouverture du courtier {: #opening-date }

Les lignes datées avant la date d'ouverture du courtier ne peuvent pas être importées (le jour d'ouverture lui-même convient). Si
la date est erronée, la bannière propose **Définir l'ouverture à la ‹date›** — la date de la ligne la plus ancienne — et
**Modifier la date du courtier** ; les lignes sont alors vérifiées à nouveau.

#### 📥 Importer les lignes

**Importer N transactions** est activé dès qu'au moins une ligne est cochée et que chaque ligne cochée a son
titre. Une dernière vérification des doublons s'exécute d'abord : des doublons modifiés entre fichiers vous renvoient vers
**Doublons**, et une sélection modifiée vous garde ici avec un message — vérifiez les cases cochées et cliquez
à nouveau.

??? info "⚖️ Aligner avec la banque — après Vérification, uniquement pour un lot de rapports tel que Danske Bank"

    Pour un lot de rapports tel que [Danske Bank](danske-bank.md#first-import-align-with-the-bank), LibreFolio
    compare ce qu'il va détenir avec les soldes et positions de la banque. Des cartes présentent chaque point —
    **Point de départ**, **Après la période manquante**, **Vérification de fin de période** — au-dessus des corrections proposées,
    toutes cochées. Décochez celles que vous ne voulez pas et cliquez sur **Continuer** ; si la comparaison a échoué, continuez
    sans elles.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-gapfix-step" alt="Aligner avec la banque : les cartes Point de départ, Après l'écart et Vérification de fin de période au-dessus des corrections proposées étiquetées gap_fix" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

### 💾 Enregistrer dans l'espace de travail groupé

Les lignes arrivent dans l'espace de travail groupé sans être enregistrées. Vérifiez-les ou modifiez-les, puis cliquez sur **Enregistrer Tout** : cela attend
les lignes listées en rouge, et demande confirmation avant d'enregistrer les valeurs listées en ambre que vous n'avez pas
vérifiées (**Enregistrer quand même**). Une ligne dont la quantité a plus de 10 décimales, dont le montant en a
plus de 6, ou dont le prix de revient unitaire en a plus de 12, est refusée à **Enregistrer Tout**, avec le
maximum dans le message (*Quantité : Au maximum 10 décimales*) : LibreFolio ne l'arrondit jamais.
Les dates des transactions vont du 1er janvier 1900 à un an après aujourd'hui : une ligne du relevé datée hors
de cet intervalle est elle aussi refusée à **Enregistrer Tout**, avec l'intervalle dans le message (*Date : Entre
1900-01-01 et 2027-10-17* si nous sommes le 17 octobre 2026).

---

## 🧭 Première importation guidée {: #guided-first-import }

La première fois que vous ouvrez l'assistant, une bulle de guide vous accompagne :

- son **Étape N sur M** ne compte que les étapes que vous voyez ; les astuces des étapes facultatives attendent un import
  qui en a besoin ;
- il ne fait qu'indiquer : il ne clique, ne téléverse et ne modifie jamais à votre place ;
- il se termine en mettant en évidence **Enregistrer Tout**, sans l'actionner ;
- **X** ne passe que l'astuce en cours.

Pour le revoir, choisissez **Relancer à la prochaine activation** pour le **Guide d'importation** dans
**[Paramètres → Préférences → Prise en main et guides](../../settings/preferences.md#onboarding-and-guides)** :
il démarre à votre prochain import.

---

## 🔗 Voir aussi

- 🏦 **[Courtiers pris en charge](index.md)** — quel fichier exporter
- 🛠️ **[Fonctionnement interne de l'assistant d'importation](../../../developer/frontend/components/features/import-wizard.md)** — pour les développeurs
