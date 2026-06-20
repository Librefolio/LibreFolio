# 📁 Fichiers & Téléchargements

La page **Fichiers** (`/files`) est votre centre névralgique pour la gestion de tout le contenu téléchargé dans LibreFolio. Elle se compose de deux sections distinctes avec des règles de visibilité différentes.

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

**Menu Contextuel** : Faites un clic droit sur n'importe quelle ligne de fichier (en vue liste) pour accéder aux actions rapides (Aperçu, Renommer, Supprimer).

Vous pouvez basculer entre la **vue liste** et la **vue grille** pour un aperçu visuel des fichiers images :

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="files" data-name="static-grid" alt="Static Files Grid View" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📊 Rapports de Courtier

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="files" data-name="brim-tab" alt="Broker Reports Tab" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Les rapports de courtier ont une **visibilité restreinte** — vous ne pouvez voir que les rapports des courtiers auxquels vous avez accès (en tant que Propriétaire, Éditeur ou Lecteur). Ces fichiers incluent :

- 📋 Les **exports de transactions** CSV ou Excel de votre courtier
- ✅ Les **résultats analysés** par le système d'importation automatique (BRIM)
- ❌ Les fichiers dont l'**analyse a échoué** (conservés pour le débogage)

**Menu Contextuel** : Faites un clic droit sur n'importe quelle ligne de rapport pour accéder aux actions rapides (Aperçu, Renommer, Supprimer).

---

## ⬆️ Téléchargement de Fichiers

Pour télécharger un fichier :

1. Cliquez sur la **zone de téléchargement** ou faites un **glisser-déposer** des fichiers directement
2. Pour les **fichiers images**, l'[outil de recadrage d'image](../misc/image-crop.md) s'ouvre automatiquement, vous permettant de redimensionner et de recadrer avant le téléchargement
3. Pour les **fichiers non-images** (CSV, PDF, etc.), vous pouvez renommer le fichier avant de confirmer

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
 <img class="gallery-img" data-category="media" data-name="file-uploader-empty" alt="File Upload Drop Zone" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! tip "Limite de taille de fichier"

    La taille maximale de téléchargement est configurée par l'administrateur système dans les [Paramètres Globaux](../../admin/settings.md). La valeur par défaut est généralement de 10 Mo.

---

## 📤 Téléchargement de Rapports de Courtier

Si vous souhaitez importer des transactions de votre courtier :

1. Allez dans l'onglet **Rapports de Courtier**
2. Téléchargez le fichier CSV ou Excel exporté depuis votre courtier (Degiro, Interactive Brokers, eToro, Directa, etc.)
3. Choisissez le **courtier à associer** au fichier — c'est là que les transactions importées seront stockées
4. Le système tentera plus tard de **détecter automatiquement** le format du fichier via le système d'importation BRIM et d'analyser les transactions

!!! info "Association ≠ Analyse"

    Le courtier que vous choisissez lors du téléchargement sert uniquement à l'**association** — il détermine quel compte courtier reçoit les transactions importées. La détection du format et l'analyse se font dans une étape distincte et sont **indépendantes** du courtier : le même plugin BRIM peut fonctionner pour plusieurs courtiers s'ils exportent dans le même format.

!!! note "Travail en cours"

    L'interface complète d'importation des rapports de courtier (BRIM) est en cours de développement actif. Actuellement, vous pouvez télécharger des rapports et les associer à des courtiers, mais l'assistant d'importation guidé n'est pas encore disponible.

---

## 🔒 Sécurité

- 🌐 Les **fichiers statiques** sont accessibles à toute personne possédant un compte LibreFolio
- 🔐 Les **rapports de courtier** respectent le contrôle d'accès du courtier — seuls les utilisateurs ayant accès à ce courtier peuvent voir ses rapports
- 🚫 Les **fichiers exécutables** (`.exe`, `.sh`, `.py`, etc.) sont bloqués pour des raisons de sécurité
- 🔍 Le **type MIME** du fichier est validé côté serveur pour empêcher le masquage (par exemple, renommer un `.exe` en `.jpg`)
