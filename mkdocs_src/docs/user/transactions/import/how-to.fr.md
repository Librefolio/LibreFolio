# 🧙 Comment importer des transactions

<style>
/* Corrections plugin table: plugin column keeps icon+name on one line */
.md-typeset details.warning table th:first-child,
.md-typeset details.warning table td:first-child { min-width: 9rem; white-space: nowrap; }
.md-typeset details.warning .md-typeset__table table td { vertical-align: middle; }
</style>

Apprenez à utiliser le module d'importation des relevés de courtier (BRIM) pour importer vos
transactions étape par étape.

---

## 🚀 Guide étape par étape

1. Exportez un relevé de transactions depuis votre courtier (généralement un fichier CSV — consultez
le centre d'aide de votre courtier).
2. Dans LibreFolio, accédez à la page **[Transactions](../index.md)**.
3. Cliquez sur le bouton **Importer** (:material-file-upload:) dans l'en-tête de la page.
4. L'**assistant d'importation** s'ouvre — vous pouvez glisser-déposer votre fichier de relevé dans
son étape de téléversement.
5. Examinez l'aperçu — vérifiez que les dates, les montants et les noms d'actifs semblent corrects.
6. Cliquez sur **Importer N transactions** — les lignes sélectionnées arrivent dans l'**éditeur en
masse** en tant que nouvelles lignes, où vous pouvez leur donner un dernier coup d'œil (ou continuer
à les modifier) avant que **Tout enregistrer** ne les engage dans votre portefeuille.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Modale d’import rapide" alt="Modale d’import rapide">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Étape 1 : Téléverser le fichier de relevé" alt="Assistant — Étape 1">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Étape 2 : Sélectionner les fichiers et l’analyseur" alt="Assistant — Étape 2">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Étape 3 : Analyse et traitement" alt="Assistant — Étape 3">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🗂️ Résolution des actifs" alt="Résolution des actifs">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Détection des doublons" alt="Détection des doublons">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Étape 4 : Révision et importation" alt="Révision et importation">
</div>

!!! tip "Création à la volée de courtiers et d'actifs"

       Si le relevé importé contient un compte de courtier ou des actifs qui ne sont pas encore
       créés dans LibreFolio, vous n'avez pas besoin de quitter le flux d'importation ! L'assistant
       vous guidera pour créer à la volée les **[Courtiers](../../brokers/index.md)** et
       **[Actifs](../../assets/index.md)** manquants, en pré-remplissant les détails à partir du
       relevé.

!!! tip "Vous pouvez aussi utiliser la section Fichiers"

       La section **[Fichiers](../../files/index.md)** (onglet BRIM) vous permet de gérer
       centralement les relevés de courtier téléversés, de les réimporter ou de les supprimer.

---

## 🧙 Les étapes de l'assistant d'importation

L'assistant comporte **quatre étapes que vous voyez toujours** et **trois qui n'apparaissent que
lorsque vos fichiers en ont réellement besoin**. La barre de progression n'affiche que les étapes
qui s'appliquent à votre importation, si bien qu'un relevé mono-fichier propre reste un parcours
court, tandis qu'un relevé multi-fichiers en désordre reçoit exactement les questions
supplémentaires qu'il mérite — et aucune autre.

| Étape | Toujours affichée ? | Apparaît quand |
| :--- | :--- | :--- |
| 1 · Téléverser le fichier de relevé | ✅ Toujours | — |
| 2 · Sélectionner les fichiers et l'analyseur | ✅ Toujours | — |
| 3 · Analyse et traitement | ✅ Toujours | — |
| 🧬 Unifier les actifs | ⚪ Optionnelle | La même valeur a été trouvée sous plus d'un nom ou d'un code |
| 🔧 Corrections | ⚪ Optionnelle | L'analyseur a enregistré des lignes qu'il n'a pas pu entièrement comprendre |
| 🧹 Doublons | ⚪ Optionnelle | Le même mouvement apparaît dans deux des fichiers que vous importez ensemble |
| 4 · Révision et importation | ✅ Toujours | — |

!!! info "Les étapes optionnelles se déroulent dans cet ordre pour une raison"

       Chaque étape s'appuie sur les réponses de la précédente. Les valeurs sont unifiées
       **d'abord**, afin que lorsque vous associez ensuite un instrument à une ligne corrigée, vous
       choisissiez dans une liste propre plutôt que parmi trois copies de la même obligation. Les
       corrections viennent **avant** la vérification des doublons, car un achat que l'analyseur n'a
       pu lire que comme un retrait d'espèces serait sinon comparé aux retraits d'espèces — manquant
       ainsi un vrai doublon, ou en inventant un qui n'existe pas.

### 🧙 Étape 1 : Téléverser le fichier de relevé

Cette étape accepte les relevés CSV ou XLSX exportés depuis votre courtier. Vous pouvez sélectionner
les fichiers manuellement ou les glisser-déposer directement dans l'assistant. Assignez un courtier
à chaque fichier, soit fichier par fichier, soit avec le sélecteur global — et si le courtier
n'existe pas encore, vous pouvez le créer à la volée depuis ici.

Cette étape est **optionnelle** : les relevés téléversés lors de sessions précédentes sont déjà
stockés, et vous pouvez les sélectionner à l'étape suivante sans les téléverser à nouveau.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Assistant — Étape 1 : Téléversement" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### ⚙️ Étape 2 : Sélectionner les fichiers et l'analyseur

Cette étape répertorie les relevés stockés pour chaque courtier, regroupés dans des panneaux
repliables par courtier, afin que vous puissiez sélectionner exactement ceux à analyser — y compris
les fichiers téléversés lors d'une session précédente (les fichiers que vous venez de téléverser
sont présélectionnés). Les relevés peuvent être prévisualisés ou supprimés depuis cette étape.
Chaque fichier dispose de son propre analyseur : le système détecte automatiquement le format du
courtier (par exemple Degiro, Directa, Interactive Brokers, Intesa Sanpaolo, Crédit Agricole), et
vous pouvez modifier le choix pour chaque fichier. Si vous téléversez une feuille de calcul
générique, utilisez l'analyseur **CSV générique** pour mapper manuellement vos colonnes (date, type,
quantité, actif, trésorerie nette) aux champs de LibreFolio.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Assistant — Étape 2 : Configuration de l’analyseur" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🧠 Étape 3 : Analyse et traitement

Le système analyse les fichiers, en validant les dates, les nombres et les devises. Vous verrez une
barre de progression indiquant la vitesse et l'état du traitement. Une fois l'analyse terminée, tout
avertissement ou erreur de traitement sera résumé avant de continuer.

Les vignettes récapitulatives en haut sont **consolidées** : une fois le traitement terminé, elles
décrivent ce qui sera réellement importé — les transactions sélectionnées et les valeurs distinctes
après unification — et non les lignes brutes de chaque fichier ; **Tout afficher** ouvre la vue
agrégée. Si vous revenez en arrière et modifiez le choix d'un analyseur, utilisez **Tout
réanalyser** pour recalculer les résultats.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Assistant — Étape 3 : Analyse" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

À la fin de l'analyse, le tableau affiche un résumé du traitement de chaque fichier avec les
colonnes statistiques suivantes marquées par des emojis :

| Emoji / Colonne | Nom de la métrique | Signification et règles de calcul |
| :--- | :--- | :--- |
| `📊` | **Transactions** | Le nombre total de transactions financières lues et identifiées dans le fichier. |
| `🏦` | **Actifs identifiés** | Le nombre d'instruments financiers (actions, ETF, etc.) trouvés dans les transactions analysées. |
| `✗` | **Actifs non résolus** | Le nombre d'instruments du fichier qui n'ont pas été trouvés dans la base de données de LibreFolio (marqués en rouge si > 0, nécessitant une correspondance à l'étape 4). |
| `🔴` | **Problèmes de validation** | Erreurs formelles détectées dans les données (par exemple, formats invalides, dates incorrectes, données obligatoires manquantes). |
| `🔧` | **Action requise (À faire)** | Champs ou attributs nécessitant une attention (rouge si bloquant, orange pour les actions de niveau avertissement/information). Ce ne sont pas nécessairement des erreurs : ils indiquent simplement des données manquantes qui ne peuvent pas être extraites automatiquement du seul relevé, et que vous pouvez facilement remplir manuellement dans le formulaire de transactions en masse à la fin de l'assistant. |
| `⚠️` | **Avertissements** | Notifications générales ou messages d'avertissement générés par l'analyseur pendant le traitement. |

??? abstract "🧬 Unifier les actifs — apparaît lorsque la même valeur a été trouvée sous plus d'un nom ou d'un code"

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-assets-step" alt="Assistant d’importation — étape Unifier les actifs avec un groupe proposé">
    </div>

    **Quand vous la verrez.** Chaque fois que deux instruments ou plus lus dans vos fichiers ressemblent à la même valeur — parce qu'ils partagent un ISIN, un ticker ou un nom — ou lorsque vos fichiers décrivent une même obligation sous deux codes différents. Une importation mono-fichier dans laquelle chaque valeur est distincte n'affiche jamais cette étape.

    **Pourquoi elle existe.** Chaque fichier est lu indépendamment, si bien que le même BTP apparaissant dans un relevé de positions *et* dans un relevé de mouvements arrive comme deux instruments sans lien. Si l'on n'y touche pas, cela devient deux actifs en double dans votre bibliothèque — et deux entrées d'apparence identique dans chaque liste qui suit, où la moitié de vos lignes s'attacherait silencieusement à la moitié de l'instrument.

    **Ce que vous faites ici.** L'assistant propose un regroupement et vous le confirmez, l'ajustez ou le rejetez. Chaque carte représente une valeur, et sa bordure vous indique qui a décidé :

    | Bordure | Signification |
    | :--- | :--- |
    | 🟩 verte continue | **Unifiée** — le moteur est certain (même ISIN, ticker ou nom), ou c'est vous qui l'avez décidé |
    | 🟨 ambre en pointillés | **À confirmer** — une ressemblance sur laquelle le moteur n'agira pas de lui-même |
    | ⬜ grise unie | **Seule** — rien à décider |

    - **Fusionnez ou séparez** à l'aide du menu `⋮` sur chaque carte, ou en faisant glisser une carte sur une autre.
    - **Désignez le code principal** en cliquant sur l'un des badges colorés : il reçoit une ⭐ et devient l'identifiant sous lequel l'actif sera connu. Les codes non retenus sont conservés comme identifiants alternatifs, de sorte que rien de ce que vos fichiers connaissaient n'est perdu.
    - **Renommez** un groupe avec le crayon. Un groupe correspondant déjà à quelque chose dans votre bibliothèque porte un badge **dans les archives**, et c'est le nom de votre bibliothèque qui l'emporte.
    - **Restaurez le regroupement automatique** : en haut, ce bouton annule en un clic toutes les fusions, divisions et choix de code si vous souhaitez recommencer.

    !!! tip "C'est ici que les obligations à double code sont réglées"

        Les obligations de détail italiennes (BTP Valore, BTP Più, BTP Italia) sont souscrites sous
        un ISIN et négociées sous un autre. Choisissez le code **négociable** comme code principal —
        c'est le seul qu'un fournisseur de cours puisse coter — et laissez le code de souscription
        (« CUM ») comme code alternatif. Voir [Créer et modifier les
        actifs](../../assets/create-edit.md) pour tous les détails.

??? warning "🔧 Corrections — apparaît lorsque l'analyseur a enregistré des lignes qu'il n'a pas pu entièrement comprendre"

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-fix-step" alt="Assistant d’importation — étape Corrections avec des lignes signalées">
    </div>

    **Quand vous la verrez.** Lorsque votre relevé contient des lignes que le plugin a enregistrées mais n'a pas pu lire complètement : une transaction dont le fichier ne comporte tout simplement ni l'instrument ni la quantité, ou des frais ou taxes qu'il n'a pas pu rattacher à une valeur. Les relevés analysés sans accroc sautent cette étape.

    Cette étape n'existe que si le plugin du courtier **marque des lignes pour révision** — un
    plugin qui n'émet jamais ces marques ne l'ouvrira jamais. Les plugins qui le font actuellement :

    | Plugin | Marques qu'il peut émettre |
    |--------|--------------------|
    | <img src="https://www.credit-agricole.it/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> [Crédit Agricole](credit_agricole.md) | Lignes transaction+frais groupées (proposées pour **division**), lignes de trésorerie qui n'ont pas pu être liées à un instrument, blocages liés aux doublons |

    Au fur et à mesure que d'autres plugins apprendront à marquer des lignes, ils seront répertoriés
    ici.

    **Pourquoi elle existe.** Un achat que le plugin n'a pu enregistrer que comme un retrait d'espèces — parce que le fichier ne lui fournissait ni quantité ni instrument — serait comparé aux retraits d'espèces lors de la vérification des doublons. Un vrai doublon serait manqué, ou un doublon imaginaire inventé. Corriger ces lignes *avant* la comparaison est le seul moment où cela fonctionne.

    **Ce que vous faites ici.** Les lignes sont regroupées par nature de la question, afin que vous régliez ensemble des cas similaires. Pour chacune, vous pouvez :

    - **La corriger** — choisissez le bon type de transaction et, le cas échéant, l'instrument et la quantité. Seuls les types qui ont du sens pour cette ligne sont proposés ; des frais ou une taxe n'ont pas de champ de quantité et peuvent légitimement n'avoir **aucun instrument** (« frais de courtier »).
    - **La diviser** — lorsqu'une ligne regroupe une transaction avec ses frais ou taxes.
    - **La conserver telle quelle** — vous êtes d'accord avec ce que le plugin a fait. La ligne se grise et reste dans la liste, afin que vous puissiez toujours voir, et réviser, ce que vous avez décidé.
    - **Réinitialiser** une seule ligne, ou toutes les lignes d'un groupe, et recommencer.

    Un bouton **montre-moi la source** met en évidence chaque ligne d'origine derrière un
    avertissement dans l'aperçu du fichier, afin que vous puissiez vérifier le relevé lui-même avant
    de décider.

    !!! danger "Lignes bloquantes"

        Les lignes marquées en **rouge** sont bloquantes : l'importation ne peut pas être
        enregistrée tant que vous ne les avez pas réglées. Les lignes ambre sont informatives — vous
        pouvez les laisser exactement telles quelles.

??? note "🧹 Doublons — apparaît lorsque le même mouvement se trouve dans deux des fichiers que vous importez ensemble"

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicates-step" alt="Assistant d’importation — étape Doublons avec une paire entre fichiers">
    </div>

    **Quand vous la verrez.** Uniquement lorsque deux fichiers ou plus de cette importation se chevauchent dans le temps et contiennent le même mouvement. Les doublons par rapport à des transactions **déjà présentes dans votre base de données** n'ouvrent *pas* cette étape — ils arrivent simplement à la révision finale déjà décochés.

    **Pourquoi elle existe.** Les exports qui se chevauchent sont normaux : vous téléchargez un relevé annuel complet, puis un relevé trimestriel qui en répète une partie. Décocher les jumeaux un par un est fastidieux et facile à faire de travers, c'est pourquoi l'assistant les regroupe et vous laisse décider une seule fois.

    **Ce que vous faites ici.**

    - **Classez vos fichiers par priorité.** Disposez-les dans l'ordre auquel vous faites confiance : la copie conservée pour chaque groupe provient du fichier de plus haute priorité.
    - **Recalculez** après avoir réordonné, afin de redériver chaque choix à partir de la nouvelle priorité.
    - **Dérogez individuellement** dans le tableau du groupe : chaque ligne comporte une case à cocher **Conserver** et indique de quel fichier elle provient et si elle est la copie conservée. **Rétablir les valeurs par défaut** restaure les choix automatiques.
    - **Comparez côte à côte** lorsque deux copies diffèrent et que vous voulez voir précisément en quoi avant de choisir — la fenêtre modale de comparaison met en évidence les champs qui diffèrent.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-nway-compare" alt="Fenêtre modale de comparaison à N voies avec différences par champ mises en évidence">
    </div>

    Chaque groupe est étiqueté **Total** (les fichiers s'accordent sur chaque détail — un pur
    chevauchement) ou **Partiel** (quelque chose diffère, donc il mérite un coup d'œil).

### 📦 Étape 4 : Révision et importation

La révision finale affiche chaque transaction à importer dans une grille de type tableur, et c'est
là que chaque instrument est finalement mis en correspondance avec votre bibliothèque.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Grille de révision et d’importation" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Le tableau affiche :

- **Date** : la date d'exécution.
- **Type** : ACHAT, VENTE, DIVIDENDE, DÉPÔT, etc.
- **Actif** : l'actif correspondant dans votre bibliothèque.
- **Quantité** : le nombre d'unités/parts.
- **Prix** : le prix unitaire.
- **Montant net** : l'impact de trésorerie total.
- **Frais/Taxes** : commissions et taxes incluses.

#### 🗂️ Résolution des actifs

Un panneau repliable au-dessus de la grille répertorie chaque instrument trouvé dans vos fichiers et
vous permet d'indiquer ce qu'il est dans votre bibliothèque. Un seul champ de recherche couvre tout,
en deux sections :

- **Dans cette importation** — les instruments lus dans vos fichiers, déjà unifiés par l'étape précédente. Un instrument déjà lié à votre bibliothèque porte un badge **dans les archives** et n'apparaît ici qu'une seule fois, jamais deux.
- **Dans les archives** — tout le reste de votre bibliothèque d'actifs.

Les candidats appariés automatiquement sont épinglés en haut du champ de recherche avec un badge de
confiance (**Exact** / **Élevé** / **Moyen** / **Faible**), de sorte que la correspondance la plus
probable est généralement à un clic.

Si aucune des deux sections ne contient ce qu'il vous faut, le bouton **Créer «…»** en bas de la
liste est toujours visible et contient déjà ce que vous avez saisi — vous n'avez jamais à aller le
chercher.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Panneau de résolution des actifs" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Le crayon ✏️ à côté d'un instrument apparié ouvre l'éditeur d'actif complet sans quitter
l'assistant, afin que vous puissiez corriger un identifiant ou un nom et revenir directement.
Lorsqu'un instrument correspond à **deux** actifs déjà présents dans votre bibliothèque, l'assistant
détecte l'ambiguïté et propose une action de **fusion** pour intégrer l'un dans l'autre.

!!! question "« Quel code est le principal ? »"

       Lorsque votre relevé comporte un identifiant et que l'actif — ou le fournisseur de cours — en
       comporte un autre du même type, LibreFolio n'écrase rien. Il demande lequel doit prévaloir,
       en affichant d'où vient chaque valeur : **du fournisseur**, **déjà enregistrée** ou **du
       relevé**. Celui que vous choisissez devient l'identifiant de l'actif ; les autres sont
       conservés comme identifiants alternatifs, de sorte que la prochaine importation reconnaîtra
       la valeur d'une manière ou d'une autre.

       La valeur du fournisseur est présélectionnée, car c'est la seule qui dispose d'un flux de
       cours derrière elle.

#### ⛔ Date d'ouverture du courtier

Si le courtier cible a une date d'ouverture, l'assistant marque les lignes datées **strictement
avant** celle-ci avec le statut `Before opening`. Ces lignes sont décochées et ne peuvent pas être
importées ; une ligne datée du jour d'ouverture reste valide. Si la date est incorrecte, une
bannière par courtier vous permet de **modifier la date du courtier** manuellement ou de la
**corriger automatiquement** en la ramenant à la date de transaction la plus ancienne trouvée, puis
de revérifier/rafraîchir afin que l'assistant réévalue chaque ligne par rapport à la date mise à
jour.

#### ⚠️ Avis sur les actifs

Certains plugins attachent des avis informatifs aux actifs extraits. Par exemple, Intesa Sanpaolo et
Crédit Agricole peuvent avertir qu'une valeur est peut-être arrivée à échéance ou a été remboursée.
Ces avis apparaissent sous forme de bannières ambre lorsque vous créez ou mappez l'actif ; ils ne
bloquent pas l'importation.

#### ⚠️ Doublons par rapport à votre base de données

Indépendamment de l'étape optionnelle **Doublons** — qui compare les fichiers importés *entre eux* —
chaque ligne est également comparée aux transactions déjà présentes dans votre base de données, sur
le type, la date, le montant, la quantité et la description. Ces cas n'ouvrent pas d'étape dédiée :
ils sont signalés ici même avec un badge de statut.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Badges de détection des doublons" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

| Badge d'interface | Niveau de confiance | Critères / Règles de correspondance |
| :--- | :--- | :--- |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY_WITH_ASSET` | Les champs de base et la description correspondent, et l'actif est résolu automatiquement (doublon à forte confiance). |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY` | Les champs de base et la description correspondent, mais l'actif n'est pas résolu. |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE_WITH_ASSET` | Les champs de base correspondent, et l'actif est résolu automatiquement (mais la description diffère ou est vide). |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE` | Les champs de base (type, date, quantité, montant) correspondent, mais l'actif n'est pas résolu. |
| <span style="background-color: rgba(16, 185, 129, 0.15); color: #10b981; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">✅ UNIQUE</span> | — | La transaction n'a aucun enregistrement correspondant dans la base de données et est classée comme nouvelle (aucun doublon détecté). |
| <span style="background-color: rgba(239, 68, 68, 0.15); color: #ef4444; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">❌ UNRESOLVED</span> | — | Le courtier ou l'instrument financier n'a pas été mis en correspondance avec une entité existante dans la base de données (nécessite une résolution à l'étape 4 avant l'importation). |

Par défaut, l'assistant décoche automatiquement les doublons « probables » pour éviter une saisie en
double, mais vous pouvez passer outre ce choix. Une bannière au-dessus de la grille résume pourquoi
des lignes sont décochées.

Deux autres badges proviennent de comparaisons *au sein de cette importation* plutôt qu'avec la base
de données :

| Badge d'interface | Signification |
| :--- | :--- |
| ⧉ **Doublon dans le lot** | Copie exacte d'une ligne encore en attente dans cette importation (ou déjà préparée dans l'éditeur en masse) — décochée par défaut. |
| ≈ **Doublon de lot possible** | Identique, mais la description diffère — reste sélectionné afin que vous puissiez décider. |

Cliquez sur **Importer N transactions** pour transmettre les lignes sélectionnées à l'**éditeur en
masse** en tant que nouvelles lignes : rien n'est encore écrit dans le grand livre. Donnez-leur un
dernier coup d'œil — ou continuez à les modifier — puis cliquez sur **Tout enregistrer** pour les
engager dans votre portefeuille.
