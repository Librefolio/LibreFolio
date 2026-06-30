# 📁 Fichiers et Téléchargements

La page **Fichiers** (`/files`) est votre centre névralgique pour gérer tous les contenus téléchargés dans LibreFolio. Elle se compose de deux sections distinctes avec des règles de visibilité différentes.

---

## 📂 Deux Onglets, Deux Objectifs

### 📁 Ressources Statiques

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-tab" alt="Static Files Tab" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Les ressources statiques sont **visibles par tous les utilisateurs** du système. C'est ici que vous trouverez :

- 🖼️ Les **avatars** et photos de profil des utilisateurs
- 🏷️ Les **icônes** et logos des courtiers
- 📄 Tout **document partagé** ou image téléchargée par les utilisateurs

Ces fichiers résident dans le répertoire `custom-uploads/` sur le serveur.

**Menu Contextuel** : Faites un clic droit sur n'importe quelle ligne de fichier (dans la vue en liste) pour accéder aux actions rapides (Aperçu, Renommer, Supprimer).

Vous pouvez basculer entre la **vue en liste** et la **vue en grille** pour obtenir un aperçu visuel des fichiers image :

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-grid" alt="Static Files Grid View" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📊 Rapports de Courtier {: #broker-reports }

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="brim-tab" alt="Broker Reports Tab" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Les rapports de courtier ont une **visibilité restreinte** : vous ne pouvez voir que les rapports des courtiers auxquels vous avez accès (en tant que propriétaire, éditeur ou lecteur). Ces fichiers comprennent :

- 📋 Les **exportations de transactions** au format CSV ou Excel de votre courtier
- ✅ Les **résultats de l'analyse** du système d'importation automatique (BRIM)
- ❌ Les fichiers dont **l'analyse a échoué** (conservés pour le débogage)

**Menu Contextuel** : Faites un clic droit sur n'importe quelle ligne de rapport pour accéder aux actions rapides (Aperçu, Renommer, Supprimer).

---

## ⬆️ Téléchargement de Fichiers

Pour télécharger un fichier :

1. Cliquez sur **l'zone de téléchargement** ou **glissez-déposez** les fichiers directement.
2. Pour les **fichiers image**, l'outil de [recadrage d'image](../misc/image-crop.md) s'ouvre automatiquement pour vous permettre de redimensionner et recadrer l'image avant le téléchargement.
3. Pour les **fichiers non image** (CSV, PDF, etc.), vous pouvez renommer le fichier avant de confirmer le téléchargement.

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
    <img class="gallery-img" data-category="media" data-name="file-uploader-empty" alt="File Upload Drop Zone" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! tip "Limite de Taille de Fichier"

    La taille maximale de téléchargement est configurée par l'administrateur système dans les [Paramètres Globaux](../../admin/settings.md). La valeur par défaut est généralement de 10 Mo.

---

## 📤 Gestion des Rapports de Courtiers

Si vous souhaitez importer des transactions ou gérer des relevés existants :

1. Allez sur l'onglet **Rapports de Courtier**.
2. Téléchargez le fichier CSV ou Excel exporté de votre courtier (Degiro, Interactive Brokers, eToro, Directa SIM, etc.).
3. Choisissez à quel **courtier associer** le fichier : cela détermine quel compte de courtier recevra les transactions importées.
4. Le système détecte automatiquement le format et lance **[l'Assistant d'Importation](../transactions/import/index.md)** guidé.

### ⚙️ Actions sur les Rapports Existants

Faites un clic droit sur n'importe quel rapport dans le tableau pour ouvrir son menu contextuel :
- 🔄 **Re-traiter (Reprocess)** : Relance l'analyseur d'importation sur le relevé. C'est utile après la mise à jour d'un plugin d'importation ou si vous avez supprimé des transactions par erreur et souhaitez les restaurer.
- 📥 **Télécharger (Download)** : Télécharge le fichier brut d'origine.
- 🗑️ **Supprimer (Delete)** : Supprime le relevé et toutes les transactions associées de votre registre.

!!! info "Association ≠ Analyse"

    Le courtier que vous choisissez lors du téléchargement sert uniquement à **l'association** : il détermine quel compte de courtier recevra les transactions importées. La détection du format et l'analyse se font dans une étape distincte et sont **indépendantes** du courtier : le même plugin BRIM peut fonctionner pour plusieurs courtiers s'ils exportent dans le même format.

---

## 🔒 Sécurité

- 🌐 Les **fichiers statiques** sont accessibles à toute personne disposant d'un compte LibreFolio.
- 🔐 Les **rapports de courtier** respectent le contrôle d'accès du courtier : seuls les utilisateurs ayant accès à ce courtier peuvent consulter ses rapports.
- 🚫 Les **fichiers exécutables** (`.exe`, `.sh`, `.py`, etc.) sont bloqués pour des raisons de sécurité.
- 🔍 Le **type MIME** du fichier est validé côté serveur pour empêcher l'usurpation de type de fichier (par exemple, renommer un `.exe` en `.jpg`).
