# 📁 Fichiers & Téléversements

La page **Fichiers** conserve tout ce qui est téléversé dans LibreFolio, dans deux onglets :

- **Ressources statiques** — avatars, icônes de courtiers et autres images ou documents, visibles par tous les utilisateurs ;
- **Rapports de courtiers** — les fichiers de relevés à partir desquels vous importez des transactions, visibles uniquement par les personnes ayant accès à leur courtier.

---

## 🖼️ Ressources statiques

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-tab" alt="Onglet Fichiers statiques" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Vous trouverez ici les **avatars** des utilisateurs, les **icônes** des courtiers et toute **image ou document** partagé par les utilisateurs. Toute personne disposant d’un compte LibreFolio peut les voir.

- Basculez entre la vue **liste** et **grille** : la grille affiche un aperçu des images.
- Dans la liste, faites un clic droit sur un fichier pour **Aperçu**, **Copier le lien**, **Télécharger** ou **Supprimer**. Vous ne pouvez supprimer que les fichiers que vous avez téléversés ; un administrateur peut supprimer n’importe lequel.
- **Aperçu** affiche un PDF dans une visionneuse en lecture seule : vous pouvez le lire, y effectuer des recherches et copier son texte, mais pas le modifier, l’annoter ou l’imprimer ; pour conserver le fichier, utilisez **Télécharger**. Un PDF protégé par mot de passe demande son mot de passe, qui reste dans votre navigateur : il n’est jamais envoyé au serveur ni enregistré, et il disparaît dès que l’aperçu se ferme.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-grid" alt="Vue grille des fichiers statiques" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### ⬆️ Téléverser un fichier

1. Cliquez sur **Téléverser**, puis déposez les fichiers sur la zone ou cliquez dessus pour parcourir.
2. Avant de téléverser, vous pouvez cliquer sur ✏️ **Modifier** sur une image pour la recadrer avec l’[outil de recadrage d’image](../misc/image-crop.md), puis confirmer avec **Recadrer** ; sur tout autre fichier, ✏️ **Renommer** change son nom. **Restaurer l’original** rétablit un fichier tel que vous l’avez sélectionné.
3. Cliquez sur **Téléverser**.

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
    <img class="gallery-img" data-category="media" data-name="file-uploader-empty" alt="Zone de dépôt de fichier" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📊 Rapports de courtiers {: #broker-reports }

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="brim-tab" alt="Onglet Rapports de courtiers" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Ce sont les relevés exportés par vos courtiers, en attente d’importation ou déjà importés. Vous voyez les rapports de chaque courtier auquel vous avez accès, en tant que Propriétaire, Éditeur ou Lecteur.

La colonne **Statut** vous indique où en est chaque fichier :

- **Téléversé** — stocké, pas encore analysé ;
- **Analysé** — l’Assistant d’importation l’a lu avec succès ;
- **Échec** — l’analyse a échoué ; le fichier reste ici pour que vous puissiez le vérifier ou le signaler.

### 📤 Téléverser un rapport de courtier

1. Dans **Rapports de courtiers**, cliquez sur **Téléverser** et sélectionnez des fichiers CSV ou Excel.
2. Dans **Attribuer des courtiers**, choisissez le courtier de chaque fichier, ou un seul pour tous avec **Tout attribuer à**. **Créer nouveau** ajoute un courtier sur-le-champ ; si vous ne pouvez modifier qu’un seul courtier, il est déjà sélectionné.
3. Cliquez sur **Téléverser**. Les fichiers sont stockés, mais **rien n’est encore importé**.

Pour les importer, ouvrez l’[Assistant d’importation](../transactions/import/index.md) (**Transactions** → **Importer**) : son étape **Sélectionner des fichiers** liste les rapports que vous avez téléversés.

Le courtier que vous choisissez détermine uniquement le compte qui reçoit les transactions. L’importateur reconnaît automatiquement le format du fichier, et un plugin d’importation peut lire les exports de plusieurs courtiers.

### ⚙️ Gérer les rapports

Faites un clic droit sur un rapport pour **Aperçu**, **Télécharger** ou **Supprimer**, ou cochez-en plusieurs pour les supprimer ensemble. Supprimer un rapport ne supprime jamais les transactions déjà importées à partir de celui-ci.

### 🧩 Lots de rapports {: #report-sets }

Certaines banques répartissent un compte sur plusieurs exports : [Danske Bank](../transactions/import/danske-bank.md), par exemple, nécessite un export d’opérations sur titres et un relevé du compte espèces. Les exports d’une telle banque que vous téléversez **ensemble** forment un **lot de rapports**, et LibreFolio les importe comme un seul lot, via un **fichier combiné** qu’il construit à partir de ceux-ci. La colonne **Lot de rapports** vous indique où en est chaque fichier (la même colonne apparaît dans les **Rapports téléversés** d’un courtier) :

| Badge | Signification |
|:--|:--|
| **Lot du ‹date›** | Le fichier appartient au lot téléversé à cette date, avec les autres exports du lot. |
| **Incomplet** | Le lot manque encore d’un export requis : survolez le badge pour voir lequel. Ajoutez-le depuis la carte du lot dans l’Assistant d’importation, avec **Téléverser le fichier manquant**. |
| **Combiné** | Le fichier que LibreFolio a construit à partir des exports d’un lot — celui que l’importation lit réellement. Survolez le badge pour voir les fichiers à partir desquels il a été construit, et lesquels d’entre eux ont été supprimés depuis. |
| **Utilisé dans un fichier combiné** | Cet export a été intégré à un fichier combiné de son lot. |
| **À recombiner** | L’importateur a été modifié depuis la construction du fichier combiné : une nouvelle analyse du lot le reconstruit. |

Vous pouvez prévisualiser, télécharger et supprimer ces fichiers comme n’importe quel autre rapport. Supprimer un export d’un lot laisse son fichier combiné en place, mais pour importer à nouveau le lot, vous devez d’abord y téléverser à nouveau cet export.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="brim-report-sets" alt="Onglet Rapports de courtiers avec les fichiers Danske Bank, leurs badges de lot de rapports et le filtre Téléversé par ouvert" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 👤 Qui a téléversé chaque fichier {: #uploaded-by }

Les deux onglets indiquent qui a téléversé chaque fichier dans la colonne **Téléversé par**, avec l’avatar et le nom de la personne :

- cliquez sur l’en-tête de colonne pour trier par téléverseur ;
- ouvrez son filtre pour ne conserver que les fichiers d’une ou plusieurs personnes : cochez-les dans la liste, ou recherchez-les par nom ;
- un fichier dont le téléverseur n’a pas été enregistré affiche *Téléverseur non enregistré*.

Le filtre s’applique également à la vue grille des **Ressources statiques**. Il est enregistré dans l’adresse de la page, donc un signet ou un lien partagé s’ouvre avec le même filtre.

---

## 🔒 Accès et limites

- 🌐 **Ressources statiques** — tout utilisateur connecté peut les voir.
- 🔐 **Rapports de courtiers** — seuls les utilisateurs ayant accès au courtier peuvent les voir ; le téléversement et la suppression nécessitent un accès Propriétaire ou Éditeur.
- 📏 **Taille** — jusqu’à la limite définie par l’administrateur dans les [Paramètres globaux](../../admin/settings.md) : 10 Mo sauf modification.
- 🚫 **Types de fichiers** — les programmes et scripts (tels que les fichiers `.exe`, `.sh` ou `.py`) sont refusés comme ressources statiques ; les rapports de courtiers doivent être des fichiers CSV ou Excel.

L’emplacement des fichiers sur le serveur est décrit dans la [Structure du système de fichiers](../../admin/filesystem.md).
