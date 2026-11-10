# 🧙 Comment importer des transactions

L’**assistant d’importation** transforme les relevés que vous téléchargez depuis votre courtier en transactions. Vous vérifiez ce qu’il a lu et levez ses doutes ; rien n’est enregistré tant que vous n’avez pas appuyé sur **Enregistrer tout**.

---

## 🚀 Guide étape par étape

1. Exportez un relevé de transactions depuis votre courtier : sa page dans **[Courtiers pris en charge](index.md)** indique quel fichier utiliser.
2. Sur la page **[Transactions](../index.md)**, cliquez sur **Importer** (:material-file-upload:).
3. Déposez le relevé dans l’assistant, attribuez-le à son courtier et suivez les étapes ci-dessous.
4. Cliquez sur **Importer N transactions** : les lignes s’ouvrent dans l’espace de travail groupé, pas encore enregistrées.
5. Jetez-y un dernier coup d’œil et cliquez sur **Enregistrer tout**.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Modale d’importation rapide" alt="Modale d’importation rapide">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Étape 1 : Téléverser le fichier de relevé" alt="Étape 1 de l’assistant">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Étape 2 : Sélectionner les fichiers &amp; l’analyseur" alt="Étape 2 de l’assistant">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Étape 3 : Analyse &amp; lecture" alt="Étape 3 de l’assistant">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🗂️ Résolution des actifs" alt="Résolution des actifs">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Détection des doublons" alt="Détection des doublons">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Étape 4 : Vérification &amp; import" alt="Vérification et import">
</div>

---

## 🧙 Les étapes de l’assistant d’importation

Quatre étapes sont toujours présentes ; les autres n’apparaissent que lorsque vos fichiers en ont besoin, et la barre de progression n’affiche que les étapes de l’importation en cours.

| Étape | Quand elle s’affiche |
| :--- | :--- |
| 1 · **Téléverser** | Toujours |
| 2 · **Sélectionner les fichiers** | Toujours |
| 3 · **Analyser** | Toujours |
| 🧬 **Unifier les actifs** | Le même titre apparaît sous plus d’un nom ou code |
| 🔧 **Corrections** | L’importateur a consigné des lignes qu’il n’a pas pu comprendre entièrement |
| 🧹 **Doublons** | Le même mouvement figure dans deux des fichiers importés ensemble |
| 4 · **Vérification** | Toujours |
| ⚖️ **Aligner sur la banque** | Lots de rapports uniquement, lorsque les chiffres de la banque diffèrent de ceux de LibreFolio |

### 📤 Étape 1 : Téléverser

Faites glisser vos relevés dans l’assistant, ou cliquez pour les choisir (CSV ou XLSX), et attribuez chacun à son courtier — ou tous à la fois avec **Attribuer un courtier aux téléversements**. Un courtier manquant peut être créé depuis la même liste (**Créer nouveau**).

- Chaque relevé que vous téléversez est conservé : pour en réutiliser un, sautez cette étape avec **Suivant : Sélectionner les fichiers**.
- Lorsqu’un compte arrive en plusieurs exports (par ex. [Danske Bank](danske-bank.md)), téléversez-les ensemble : s’il en manque un, l’assistant reste ici et le nomme.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Étape 1 de l’assistant : Téléverser" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

#### 🧭 Un fichier dans le mauvais courtier {: #wrong-broker }

Lorsque vous cliquez sur **Suivant : Sélectionner les fichiers**, l’assistant vérifie chaque fichier que vous venez de téléverser par rapport au **Plugin d’importation par défaut** de son courtier. Si ce plugin ne peut pas lire un fichier, celui-ci appartient probablement à un autre courtier, et l’assistant vous interroge à son sujet avant de continuer (*Ce fichier peut appartenir à un autre courtier*). De haut en bas, il affiche :

- **Attribué à** — le courtier dans lequel se trouve le fichier, avec son icône, et son plugin par défaut, marqué *ne peut pas le lire* ;
- **Notes du plugin** — pourquoi ce plugin ne peut pas lire le fichier, lorsqu’il l’indique : dans votre langue lorsqu’une traduction existe ;
- **Déplacer vers** — le courtier dont le plugin par défaut *peut le lire*. Lorsque les plugins par défaut de plusieurs courtiers le lisent, l’invite liste ces courtiers à la place : choisissez-en un, le premier est déjà sélectionné.

Choisissez ensuite :

- **Déplacer**, avec l’icône du courtier choisi sous **Déplacer vers** — le fichier est téléversé chez ce courtier, dans la même session, et retiré du mauvais. Si le déplacement échoue, une erreur l’indique et le fichier reste où il était ;
- **Conserver ici** — le fichier reste, et l’assistant le lit avec un autre plugin qui le peut, comme avant : vous le voyez dans la colonne **Plugin** de **Sélectionner les fichiers** ;
- **Supprimer** — le fichier est supprimé.

Une invite par fichier, à tour de rôle (*Fichier 1 sur 3*) ; la fermer conserve le fichier. Si vous supprimez tous les fichiers que vous venez de téléverser, l’assistant reste sur **Téléverser**, prêt pour d’autres. Lorsqu’aucun de vos courtiers n’a de plugin par défaut qui lit le fichier, l’invite nomme les plugins qui le lisent — ou indique qu’aucun ne le peut — et ne propose que de le conserver ou de le supprimer.

Les courtiers sans plugin d’importation par défaut ne sont jamais interrogés, et les relevés que vous réutilisez sans les téléverser à nouveau non plus.

### 🗂️ Étape 2 : Sélectionner les fichiers

Le panneau de chaque courtier liste ses relevés stockés, les fichiers que vous venez de téléverser étant déjà cochés. Cochez les fichiers à lire et cliquez sur **Analyser (N)**.

L’importateur de chaque fichier est détecté automatiquement : modifiez-le dans la colonne **Plugin** s’il est erroné, et pour un CSV que vous avez créé vous-même, choisissez **[CSV générique](generic-csv.md)**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Étape 2 de l’assistant : Configuration de l’analyseur" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Chaque **lot de rapports** forme une seule carte, cochée en bloc. **Lire comme**, dans son en-tête, modifie la façon dont le lot est lu, et le menu **⋮** de chaque fichier peut le retirer du lot (**Lire seul avec ‹plugin›**, **Retirer du lot**) — [détails](danske-bank.md#how-the-set-is-read).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-read-as" alt="Carte de lot de rapports dans Sélectionner les fichiers, avec la liste Lire comme ouverte : Danske Bank (détecté) et Lire les fichiers un par un" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-file-menu" alt="Menu ⋮ d’un fichier de liquidités dans un lot de rapports : Aperçu, Retirer du lot et Supprimer" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

**Analyser est désactivé ?** Un fichier coché n’a pas de plugin, ou un lot coché est incomplet ou seulement partiellement coché (un tiret dans sa case à cocher) : choisissez le plugin, utilisez **Téléverser le fichier manquant**, ou cochez ou décochez le lot.

### 🧠 Étape 3 : Analyser

LibreFolio lit chaque fichier, le vérifie et le résume dans un tableau :

| Colonne | Ce qu’elle compte |
| :--- | :--- |
| 📊 | Transactions lues |
| 🏦 | Titres trouvés |
| ✗ | Titres pas encore associés à vos actifs — vous les associez dans **Vérification** |
| 🔴 | Problèmes de validation : lignes qui n’ont pas pu devenir des transactions |
| 🔧 | Champs à remplir avant l’enregistrement (en rouge lorsqu’un champ bloque l’enregistrement) |
| ⚠️ ℹ️ | Deux nombres : les avertissements (en ambre) nécessitent un coup d’œil, comme des lignes ignorées ; les notes (en bleu) expliquent un choix effectué par l’importateur, sans rien à corriger |

Les tuiles sous le tableau comptabilisent ce qui sera réellement importé ; **Tout afficher**, ou **Voir le détail** dans le menu **⋮** d’une ligne, ouvre les détails, avec les avertissements et les notes listés séparément.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Étape 3 de l’assistant : Analyse" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- **Avertissements et notes** : **Continuer** liste d’abord les avertissements, puis les notes ; lisez-les, puis cliquez sur **Continuer quand même**. Un avertissement concernant des lignes que l’importateur a omises, parce qu’il ne les connaît pas ou ne peut pas les lire, comporte un lien pour ouvrir un ticket sur GitHub.
- **Un fichier a échoué** : une bannière en indique la raison. Corrigez son plugin dans **Sélectionner les fichiers**, puis analysez à nouveau. **Tout réanalyser** n’apparaît dans l’analyse qu’une fois qu’au moins un fichier a été lu ; si aucun ne l’a été, revenez à **Sélectionner les fichiers** et cliquez sur **Analyser (N)**.

### 🧩 Étapes qui n’apparaissent qu’en cas de besoin {: #only-when-needed }

Selon ce que **Analyser** trouve, jusqu’à trois étapes peuvent précéder **Vérification**, dans cet ordre. Ouvrez celle que l’assistant vous montre :

??? abstract "🧬 Unifier les actifs — lorsque le même titre apparaît sous plus d’un nom ou code"

    Vos fichiers décrivent le même titre plus d’une fois — sous deux noms ou codes, ou dans deux fichiers. Unifiez-le ici, sinon il devient deux actifs dont les transactions sont réparties entre eux.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-assets-step" alt="Assistant d’importation — étape Unifier les actifs avec un groupe proposé">
    </div>

    Chaque carte correspond à un titre : une bordure **verte unie** signifie que le titre est unifié, une bordure **ambre en pointillés** qu’il faut confirmer, une bordure **grise** qu’il n’y a rien à décider.

    - **Confirmer** ou **Séparer** une proposition ; fusionnez ou séparez des cartes avec **⋮** (**Fusionner avec…**, **Retirer du groupe**) ou par glisser-déposer.
    - **Cliquez sur un badge de code** pour en faire le code principal (⭐) — choisissez celui sur lequel les prix sont cotés ; les autres restent comme alternatives.
    - **Renommer** avec le crayon ; un titre déjà présent dans votre bibliothèque (**dans l’archive**) conserve son nom.
    - **Continuer** attend qu’aucune proposition ne soit ouverte : **Tout confirmer (N)** les règle d’un coup, et **Rétablir le regroupement automatique** recommence.

??? warning "🔧 Corrections — lorsque l’importateur a consigné des lignes qu’il n’a pas pu comprendre entièrement"

    L’importateur a consigné des lignes qu’il n’a pas pu comprendre entièrement — aujourd’hui, des lignes issues de relevés de [Crédit Agricole](credit_agricole.md) et de [Danske Bank](danske-bank.md).

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-fix-step" alt="Assistant d’importation — étape Corrections avec des lignes signalées">
    </div>

    Les lignes sont regroupées par question. Donnez une réponse à chacune :

    - **Corriger** : choisissez le type et, le cas échéant, le titre et la quantité, puis **Appliquer la correction**. Des frais ou un impôt peuvent relever de **Aucun instrument (frais du courtier)**.
    - **Séparer** : séparez le prix des commissions, impôts ou intérêts courus indiqués sur votre avis d’opéré.
    - **Conserver la ligne telle que consignée** : acceptez ce que l’importateur a lu.

    **Ligne N du fichier** affiche la ligne d’origine, et **Rétablir** annule une réponse. **Continuer** attend toutes les réponses ; **Conserver les N lignes restantes telles que lues** répond à toutes celles qui sont ouvertes.

??? note "🧹 Doublons — lorsque le même mouvement figure dans deux des fichiers importés ensemble"

    Le même mouvement figure dans deux des fichiers que vous importez ensemble, comme un relevé annuel et un relevé trimestriel. Les correspondances avec des transactions déjà enregistrées n’ouvrent pas cette étape : **Vérification** les signale.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicates-step" alt="Assistant d’importation — étape Doublons avec une paire inter-fichiers">
    </div>

    - **Priorité des fichiers** : faites glisser les fichiers dans l’ordre auquel vous faites confiance et cliquez sur **Recalculer par priorité**. Chaque groupe conserve la copie du fichier le plus prioritaire — jamais une copie déjà enregistrée ou en attente dans l’espace de travail groupé.
    - **Conserver** : cochez les copies à importer, ligne par ligne ; **Réinitialiser les valeurs par défaut** rétablit le choix automatique.
    - **Comparer** affiche les copies côte à côte, les différences étant mises en évidence.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-nway-compare" alt="Modale de comparaison à N voies avec les différences par champ mises en évidence">
    </div>

    Les groupes sont listés sous **Chevauchement total** (copies identiques) et **Chevauchement partiel** (quelque chose diffère).

### 📦 Étape 4 : Vérification {: #review }

Chaque ligne à importer dans une seule grille — statut, date, type, titre, courtier, quantité, liquidités et étiquettes, plus le fichier lorsque vous en importez plusieurs.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Grille Vérification et import" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

#### 🗂️ Associer chaque titre

Le panneau **Résoudre les actifs** au-dessus de la grille liste les titres de vos fichiers. Associez chacun :

- Recherchez **Dans cette importation** et **Dans l’archive** (votre bibliothèque) depuis un seul champ. Les correspondances probables viennent en premier, avec un badge de confiance (**Exact** à **Faible**) ; une correspondance unique est déjà sélectionnée.
- **Créer « … »** ouvre le formulaire de nouvel actif, prérempli avec le nom et les codes du relevé.
- ✏️ **Inspecter / modifier** ouvre l’actif choisi ; **Fusionner** apparaît lorsque deux de vos actifs correspondent.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Panneau de résolution des actifs" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Si le code du relevé diffère de celui de l’actif ou de celui du fournisseur de prix, LibreFolio demande lequel est le principal. Le code du fournisseur, celui qui comporte des prix, est présélectionné ; les autres restent comme alternatives. Une note ambre sur un nouvel actif, comme une échéance possible, n’est qu’un conseil.

#### 🚦 Lire les badges de statut

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Badges de détection des doublons" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

| Badge | Signification | Coché initialement ? |
| :--- | :--- | :--- |
| **✓ Unique** | Rien de similaire n’est enregistré | ✅ |
| **ℹ Doublon possible** | Une transaction enregistrée a le même type, la même date, la même quantité et le même montant, mais une autre description | ✅ — vérifiez-la |
| **⚠ Doublon probable** | Une transaction enregistrée correspond, description comprise | ⬜ |
| **⧉ Doublon dans le lot** | Copie exacte d’une autre ligne de cette importation, ou de l’espace de travail groupé | ⬜ |
| **≈ Doublon possible dans le lot** | La même chose, avec une autre description | ✅ — vérifiez-la |
| **✗ Non résolu** | Son titre n’est pas encore associé | ✅ — associez-le ou décochez-le |
| **⛔ Avant l’ouverture** | Datée avant la date d’ouverture du courtier | Ne peut pas être importée |
| **⏮ Déjà dans LibreFolio** | Lots de rapports : ligne antérieure à l’historique conservé par LibreFolio ; masquée derrière un compteur | Ne peut pas être importée |

Cliquez sur un badge de doublon pour comparer la ligne avec sa jumelle ; une bannière explique pourquoi des lignes sont décochées. Une conversion de devise est une seule ligne, importée en entier.

#### ⛔ Lignes antérieures à la date d’ouverture du courtier {: #opening-date }

Les lignes datées avant la date d’ouverture du courtier ne peuvent pas être importées (le jour d’ouverture lui-même convient). Si la date est erronée, la bannière propose **Définir l’ouverture à ‹date›** — la date de la ligne la plus ancienne — et **Modifier la date du courtier** ; les lignes sont alors vérifiées à nouveau.

#### 📥 Importer les lignes

**Importer N transactions** est activé dès qu’au moins une ligne est cochée et que chaque ligne cochée a son titre. Une dernière vérification des doublons s’exécute d’abord : des doublons modifiés entre fichiers vous renvoient à **Doublons**, et une sélection modifiée vous garde ici avec un message — vérifiez les cases cochées et cliquez à nouveau.

??? info "⚖️ Aligner sur la banque — après Vérification, uniquement pour un lot de rapports tel que Danske Bank"

    Pour un lot de rapports tel que [Danske Bank](danske-bank.md#first-import-align-with-the-bank), LibreFolio compare ce qu’il contiendra avec les soldes et positions de la banque. Des cartes affichent chaque point — **Point de départ**, **Après l’écart**, **Contrôle de fin de période** — au-dessus des corrections proposées, toutes cochées. Décochez celles que vous ne voulez pas et cliquez sur **Continuer** ; si la comparaison a échoué, continuez sans elles.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-gapfix-step" alt="Aligner sur la banque : les cartes Point de départ, Après l’écart et Contrôle de fin de période au-dessus des corrections proposées étiquetées gap_fix" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

### 💾 Enregistrer dans l’espace de travail groupé

Les lignes arrivent dans l’espace de travail groupé sans être enregistrées. Vérifiez-les ou modifiez-les, puis cliquez sur **Enregistrer tout** : le bouton attend les lignes listées en rouge et demande une confirmation avant d’enregistrer les valeurs listées en ambre que vous n’avez pas vérifiées (**Enregistrer quand même**). Une ligne dont la quantité comporte plus de 10 décimales, dont le montant en liquidités comporte plus de 6 décimales, ou dont le coût de base unitaire comporte plus de 12 décimales est refusée à **Enregistrer tout**, avec le maximum dans le message (*Quantité : au maximum 10 décimales*) : LibreFolio ne l’arrondit jamais.
Les dates de transaction peuvent remonter jusqu’à l’an 1 et aller jusqu’à demain. Une ligne datée d’avant 1900 est marquée en ambre dans la vérification (une note au-dessus du tableau les compte) et l’espace de travail groupé demande une fois de les confirmer, car une telle date est généralement une faute de frappe ; une fois confirmée, elle est enregistrée comme n’importe quelle autre. Une ligne datée d’après demain est refusée à **Enregistrer tout**, avec le dernier jour autorisé dans le message (*Date : au plus tard le 2026-10-18* lorsque aujourd’hui est le 17 octobre 2026).

Une ligne qui apporte des unités — un **Ajustement** qui ajoute des unités, ou le côté récepteur d’un **Transfert d’actif** — conserve le coût inscrit dans le relevé, même 0, en **Manuel**. Si le relevé n’en donne aucun, elle démarre en **Auto** (💡 dans la colonne **Remplacement du coût de base**) : **Enregistrer tout** l’enregistre au [coût moyen](../form.md#cost-basis) des unités déjà détenues, sauf si vous la passez en **Manuel**. S’il n’y a rien à moyenner, la ligne est refusée : choisissez **Manuel** et saisissez son coût, 0 pour un don.

Les lignes dont le coût manquant est signalé par l’importateur font exception : une position ajoutée par **Aligner sur la banque**, une nouvelle ligne d’une [scission](danske-bank.md#demergers) de Danske Bank, une ligne `ADJUSTMENT` d’un fichier [CSV générique](generic-csv.md) qui ajoute des unités sans coût. Elles sont listées en rouge, et leur formulaire s’ouvre en **Manuel** avec le coût vide : saisissez-le à la main, même s’il vaut 0 — choisir **Auto** ne les retire pas de la liste.

À l’arrivée des lignes, ainsi qu’après **⚡ Valider maintenant** ou un **Enregistrer tout** refusé, la grille passe à la page de la première ligne dont le [coût **Auto** a été refusé](../form.md#cost-basis), et la met en évidence : la plus ancienne par la date, car la corriger peut permettre aux lignes ultérieures du même actif chez ce courtier de passer. La vérification automatique qui s’exécute pendant que vous modifiez ne le fait pas.

---

## 🧭 Première importation guidée {: #guided-first-import }

La première fois que vous ouvrez l’assistant, une bulle de guide vous accompagne :

- son indicateur **Étape N sur M** ne compte que les étapes que vous voyez ; les astuces des étapes facultatives attendent une importation qui en a besoin ;
- il ne fait que pointer : il ne clique jamais, ne téléverse ni ne modifie à votre place ;
- il se termine en mettant en évidence **Enregistrer tout**, sans l’appuyer ;
- **X** ignore uniquement l’astuce en cours.

Pour le revoir, choisissez **Relancer au prochain déclenchement** pour le **Guide d’importation** dans **[Paramètres → Préférences → Prise en main et guides](../../settings/preferences.md#onboarding-and-guides)** : il démarre à votre prochaine importation.

---

## 🔗 Voir aussi

- 🏦 **[Courtiers pris en charge](index.md)** — quel fichier exporter
- 🛠️ **[Fonctionnement interne de l’assistant d’importation](../../../developer/frontend/components/features/import-wizard.md)** — pour les développeurs
