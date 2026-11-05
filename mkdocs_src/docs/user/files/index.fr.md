# 📁 Fichiers et téléversements

La page **Fichiers** conserve tout ce qui est téléversé dans LibreFolio, réparti en deux onglets :

- **Ressources statiques** — avatars, icônes de courtiers et autres images ou documents, chacun étant soit **partagé** avec tous les utilisateurs, soit **personnel** à la personne qui l'a téléversé ;
- **Rapports de courtiers** — les fichiers de relevés à partir desquels vous importez des transactions, visibles uniquement par les personnes ayant accès à leur courtier.

Les administrateurs voient également un troisième onglet, [Sauvegardes](#backups-tab), ainsi qu'une barre indiquant [l'espace occupé par l'instance](#space-used).

---

## 🖼️ Ressources statiques

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-tab" alt="Onglet des fichiers statiques" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Vous y trouvez les **avatars** des utilisateurs, les **icônes** des courtiers et les **images et documents** téléversés par les utilisateurs : les partagés, que toute personne disposant d'un compte LibreFolio peut voir, et les vôtres personnels, que seuls vous et les administrateurs pouvez voir (voir [Partagé ou personnel](#visibility)).

- Basculez entre la vue **liste** et la vue **grille** : la grille affiche un aperçu des images.
- Dans la liste, faites un clic droit sur un fichier pour **Aperçu**, **Copier le lien**, **Télécharger** ou **Supprimer**. Vous ne pouvez supprimer que les fichiers que vous avez téléversés : **Supprimer** n'apparaît donc que sur ceux-ci ; un administrateur peut supprimer n'importe lequel. Cochez plusieurs fichiers pour les supprimer ensemble : les fichiers des autres utilisateurs restent en place, et un message vous en informe.
- **Aperçu** affiche un PDF dans une visionneuse en lecture seule : vous pouvez le lire, y effectuer une recherche et copier son texte, mais pas le modifier, l'annoter ni l'imprimer ; pour conserver le fichier, utilisez **Télécharger**. Un PDF protégé par mot de passe demande son mot de passe, qui reste dans votre navigateur : il n'est jamais envoyé au serveur ni enregistré, et il disparaît dès que l'aperçu est fermé.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-grid" alt="Vue grille des fichiers statiques" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### ⬆️ Téléverser un fichier

1. Cliquez sur **Téléverser**, puis déposez des fichiers sur la zone ou cliquez dessus pour parcourir vos fichiers.
2. Avant de téléverser, vous pouvez cliquer sur ✏️ **Modifier** sur une image pour la recadrer avec l'[outil de recadrage d'image](../misc/image-crop.md), puis confirmer avec **Recadrer** ; sur tout autre fichier, ✏️ **Renommer** change son nom. **Restaurer l'original** rétablit un fichier tel que vous l'avez sélectionné.
3. Cliquez sur **Téléverser**. Les fichiers sont **personnels** : seuls vous et les administrateurs les voyez, jusqu'à ce que vous [les partagiez](#visibility).

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
    <img class="gallery-img" data-category="media" data-name="file-uploader-empty" alt="Zone de dépôt de fichiers" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 👥 Partagé ou personnel {: #visibility }

Chaque ressource statique porte le badge **Partagé** ou **Personnel**, comme l'indique la colonne **Visibilité** de la liste :

- **Partagé** — tout utilisateur connecté peut la voir ;
- **Personnel** — seuls la personne qui l'a téléversé et les administrateurs peuvent la voir. Les autres utilisateurs ne la trouvent pas dans leur liste et ne peuvent ni l'ouvrir, ni en afficher l'aperçu, ni la télécharger.

Un fichier que vous téléversez est :

- **personnel** lorsque vous le téléversez depuis cette page ;
- **partagé** lorsque vous le téléversez depuis un sélecteur d'image (votre photo de profil, dans **Profil** ou sur la page d'accueil ; une icône de courtier ; une icône d'actif), car les autres utilisateurs voient l'image là où vous l'utilisez.

Les fichiers téléversés avec une ancienne version de LibreFolio sont partagés s'il s'agit d'images, personnels sinon.

Vous pouvez modifier la visibilité des fichiers que vous avez téléversés ; un administrateur, celle de n'importe quel fichier :

- dans la liste, faites un clic droit sur le fichier : un fichier personnel propose **Partager avec tous**, un fichier partagé **Rendre personnel** ;
- dans la grille, utilisez le même interrupteur sur la carte du fichier : 👥 le partage, 🔒 le rend personnel.

Le partage est immédiat. **Rendre personnel** vous demande d'abord une confirmation : les autres utilisateurs perdent l'accès au fichier, y compris là où il apparaît comme icône ou photo.

Le filtre **Visibilité**, dans l'en-tête de colonne, ne conserve que les fichiers partagés ou que les fichiers personnels. Comme le filtre [Téléversé par](#uploaded-by), il s'applique aussi à la vue grille et est enregistré dans l'adresse de la page.

L'onglet **Existants** d'un sélecteur d'image liste les images partagées ainsi que vos propres images personnelles, même pour un administrateur. En y choisissant l'une de vos images personnelles, vous la rendez partagée, et un message vous en informe : les autres utilisateurs peuvent alors la voir là où vous l'avez utilisée.

---

## 📊 Rapports de courtiers {: #broker-reports }

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="brim-tab" alt="Onglet des rapports de courtiers" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Ce sont les relevés exportés par vos courtiers, en attente d'importation ou déjà importés. Vous voyez les rapports de tous les courtiers auxquels vous avez accès, en tant que Propriétaire, Éditeur ou Lecteur. Les rapports qu'une ancienne version de LibreFolio a stockés sans courtier n'apparaissent ici que pour les administrateurs et pour la personne qui les a téléversés, lorsque LibreFolio a enregistré qui l'a fait.

La colonne **Statut** indique où en est chaque fichier :

- **Téléversé** — stocké, pas encore analysé ;
- **Analysé** — l'assistant d'importation l'a lu avec succès ;
- **Échec** — l'analyse a échoué ; le fichier reste ici pour que vous puissiez le vérifier ou le signaler.

### 📤 Téléverser un rapport de courtier

1. Dans **Rapports de courtiers**, cliquez sur **Téléverser** et sélectionnez des fichiers CSV ou Excel.
2. Dans **Attribuer des courtiers**, choisissez le courtier de chaque fichier, ou un seul pour tous avec **Tout attribuer à**. **Créer nouveau** ajoute un courtier sur-le-champ ; si vous ne pouvez modifier qu'un seul courtier, il est déjà sélectionné.
3. Cliquez sur **Téléverser**. Les fichiers sont stockés, mais **rien n'est encore importé**.

Pour les importer, ouvrez l'[assistant d'importation](../transactions/import/index.md) (**Transactions** → **Importer**) : son étape **Sélectionner les fichiers** liste les rapports que vous avez téléversés.

Le courtier que vous choisissez détermine seulement quel compte reçoit les transactions. L'importateur reconnaît le format du fichier de lui-même, et un même plugin d'importation peut lire les exports de plusieurs courtiers.

### ⚙️ Gérer les rapports

Faites un clic droit sur un rapport pour **Aperçu**, **Télécharger** ou **Supprimer**, ou cochez-en plusieurs pour les supprimer ensemble. **Supprimer** n'apparaît que sur les rapports que vous pouvez supprimer, et supprimer plusieurs rapports laisse les autres en place, avec un message. Supprimer un rapport ne supprime jamais les transactions déjà importées depuis celui-ci.

### 🧩 Lots de rapports {: #report-sets }

Certaines banques répartissent un compte sur plusieurs exports : [Danske Bank](../transactions/import/danske-bank.md), par exemple, nécessite un export de titres et un relevé du compte espèces. Les exports d'une telle banque que vous téléversez **ensemble** forment un **lot de rapports**, et LibreFolio les importe comme un seul lot, via un **fichier combiné** qu'il construit à partir d'eux. La colonne **Lot de rapports** indique où en est chaque fichier (la même colonne apparaît dans les **Rapports téléversés** d'un courtier) :

| Badge | Signification |
|:--|:--|
| **Lot du ‹date›** | Le fichier appartient au lot téléversé à cette date, avec les autres exports du lot. |
| **Incomplet** | Il manque encore un export requis au lot : survolez le badge pour voir lequel. Ajoutez-le depuis la carte du lot dans l'assistant d'importation, avec **Téléverser le fichier manquant**. |
| **Combiné** | Le fichier que LibreFolio a construit à partir des exports d'un lot — celui que l'importation lit réellement. Survolez le badge pour voir les fichiers à partir desquels il a été construit, et lesquels ont été supprimés depuis. |
| **Utilisé dans un fichier combiné** | Cet export a été intégré à un fichier combiné de son lot. |
| **À recombiner** | L'importateur a changé depuis la construction du fichier combiné : analyser à nouveau le lot le reconstruit. |

Vous pouvez prévisualiser, télécharger et supprimer ces fichiers comme n'importe quel autre rapport. Supprimer un export d'un lot laisse son fichier combiné en place, mais pour importer à nouveau le lot, vous devez d'abord y téléverser à nouveau cet export.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="brim-report-sets" alt="Onglet des rapports de courtiers avec des fichiers Danske Bank, leurs badges de lot de rapports et le filtre Téléversé par ouvert" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 👤 Qui a téléversé chaque fichier {: #uploaded-by }

Les deux onglets indiquent qui a téléversé chaque fichier dans la colonne **Téléversé par**, avec l'avatar et le nom de la personne :

- cliquez sur l'en-tête de colonne pour trier par auteur du téléversement ;
- ouvrez son filtre pour ne conserver que les fichiers d'une ou plusieurs personnes : cochez-les dans la liste ou recherchez-les par nom ;
- un fichier dont l'auteur du téléversement n'a pas été enregistré affiche *Auteur du téléversement non enregistré*.

Le filtre s'applique aussi à la vue grille des **Ressources statiques**. Il est enregistré dans l'adresse de la page, si bien qu'un signet ou un lien partagé s'ouvre avec le même filtre.

---

## 🛠️ Pour les administrateurs {: #admin-files }

Seuls les administrateurs voient ce qui suit ; les autres utilisateurs ne trouvent ni l'un ni l'autre sur la page.

### 📊 L'espace utilisé {: #space-used }

Au-dessus des onglets, une barre indique la place qu'occupe l'instance, répartie entre la **base de données**, les **fichiers téléversés**, les **rapports de courtiers**, les **sauvegardes** et les **autres fichiers de LibreFolio**. Sans limite définie, elle est tracée par rapport au disque, les autres fichiers du disque apparaissant en gris ; avec une limite, par rapport à cette limite. Dans la même barre, vous définissez la **Limite d'espace (MB)**, `0` pour aucune limite. Lorsque la limite est dépassée, la barre vous avertit, et rien n'est supprimé. La barre se met à jour avec **Actualiser**. Comment l'interpréter, et ce qui définit la limite : [La barre d'occupation de l'espace](../../admin/backup_restore.md#space-used).

### 🗃️ L'onglet Sauvegardes {: #backups-tab }

L'onglet **Sauvegardes** liste les sauvegardes que LibreFolio conserve sur le serveur, avec leur date, leur origine, leur type et leur taille. Pour chacune, vous pouvez la **Télécharger** ou la **Supprimer**. La même liste se trouve dans **Paramètres › Administration › Sauvegarde**, où vous réglez également le nettoyage automatique : voir [Sauvegardes conservées sur le serveur](../../admin/backup_restore.md#kept-backups).

---

## 🔒 Accès et limites

- 🌐 **Ressources statiques** — tout utilisateur connecté peut voir les ressources partagées ; pour un fichier personnel, seuls la personne qui l'a téléversé et les administrateurs le voient (voir [Partagé ou personnel](#visibility)). La suppression d'un fichier et la modification de sa visibilité reviennent à la personne qui l'a téléversé, ainsi qu'à un administrateur.
- 🔐 **Rapports de courtiers** — seuls les utilisateurs ayant accès au courtier peuvent les voir ; le téléversement et la suppression nécessitent un accès Propriétaire ou Éditeur. Un administrateur peut voir et supprimer tous les rapports.
- 📏 **Taille** — jusqu'à la limite définie par l'administrateur dans les [Paramètres globaux](../../admin/settings.md) : 10 MB sauf modification.
- 🚫 **Types de fichiers** — les programmes et scripts (comme les fichiers `.exe`, `.sh` ou `.py`) sont refusés comme ressources statiques ; les rapports de courtiers doivent être des fichiers CSV ou Excel.

L'emplacement des fichiers sur le serveur est décrit dans la [Structure du système de fichiers](../../admin/filesystem.md).
