# 📁 Fichiers & Téléversements

La page **Fichiers** (`/files`) est votre centre de gestion pour tout le contenu téléversé dans LibreFolio. Elle se compose de deux sections distinctes avec des règles de visibilité différentes.

---

## 📂 Deux onglets, deux objectifs

### 📁 Ressources statiques

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="files" data-name="static-tab" alt="Onglet Fichiers Statiques" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Les ressources statiques sont **visibles par tous les utilisateurs** du système. C'est ici que vous trouverez :

- 🖼️ Les **avatars** et photos de profil des utilisateurs
- 🏷️ Les **icônes** et logos des courtiers
- 📄 Tous les **documents partagés** ou images téléversés par les utilisateurs

Ces fichiers sont stockés dans le répertoire `custom-uploads/` sur le serveur.

Vous pouvez basculer entre la **vue en liste** et la **vue en grille** pour un aperçu visuel des fichiers images :

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="files" data-name="static-grid" alt="Vue Grille des Fichiers Statiques" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📊 Rapports de courtiers

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="files" data-name="brim-tab" alt="Onglet Rapports de Courtiers" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Les rapports de courtiers ont une **visibilité restreinte** — vous ne pouvez voir que les rapports des courtiers auxquels vous avez accès (en tant que propriétaire, éditeur ou lecteur). Ces fichiers incluent :

- 📋 Les **exports de transactions** CSV ou Excel de votre courtier
- ✅ Les **résultats analysés** par le système d'importation automatique (BRIM)
- ❌ Les fichiers dont l'**analyse a échoué** (conservés pour le débogage)

---

## ⬆️ Téléversement de fichiers

Pour téléverser un fichier :

1. Cliquez sur la **zone de téléversement** ou faites un **glisser-déposer** des fichiers directement
2. Pour les **fichiers images**, l'outil [Image Crop](../misc/image-crop.md) s'ouvre automatiquement, vous permettant de redimensionner et de recadrer avant le téléversement
3. Pour les **fichiers non-images** (CSV, PDF, etc.), vous pouvez renommer le fichier avant de confirmer

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
 <img class="gallery-img" data-category="media" data-name="file-uploader-empty" alt="Zone de dépôt de téléchargement de fichiers" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! tip "Limite de taille de fichier"

    La taille maximale de téléversement est configurée par l'administrateur système dans les [Paramètres Globaux](../../admin/settings.md). La valeur par défaut est généralement de 10 Mo.

---

## 📤 Téléversement de rapports de courtiers

Si vous souhaitez importer des transactions de votre courtier :

1. Allez dans l'onglet **Rapports de courtiers**
2. Téléversez le fichier CSV ou Excel exporté de votre courtier (Degiro, Interactive Brokers, eToro, Directa, etc.)
3. Choisissez le **courtier à associer** au fichier — c'est ici que les transactions importées seront stockées
4. Le système tentera ultérieurement de **détecter automatiquement** le format du fichier via le système d'importation BRIM et d'analyser les transactions

!!! info "Association ≠ Analyse"

    Le courtier que vous choisissez lors du téléversement sert uniquement à l'**association** — il détermine quel compte courtier reçoit les transactions importées. La détection du format et l'analyse se font dans une étape distincte et sont **indépendantes** du courtier : le même plugin BRIM peut fonctionner pour plusieurs courtiers s'ils exportent dans le même format.

!!! note "Travail en cours"

    L'interface complète d'importation des rapports de courtiers (BRIM) est en cours de développement actif. Actuellement, vous pouvez téléverser des rapports et les associer à des courtiers, mais l'assistant d'importation guidé n'est pas encore disponible.

---

## 🔒 Sécurité

- 🌐 Les **fichiers statiques** sont accessibles à toute personne possédant un compte LibreFolio
- 🔐 Les **rapports de courtiers** respectent le contrôle d'accès du courtier — seuls les utilisateurs ayant accès à ce courtier peuvent consulter ses rapports
- 🚫 Les **fichiers exécutables** (`.exe`, `.sh`, `.py`, etc.) sont bloqués pour des raisons de sécurité
- 🔍 Le **type MIME** du fichier est validé côté serveur pour empêcher le camouflage (par exemple, renommer un `.exe` en `.jpg`)
