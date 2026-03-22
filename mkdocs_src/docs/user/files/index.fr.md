# 📁 Fichiers & Téléversements

La page **Fichiers** (`/files`) est votre centre névralgique pour gérer tout le contenu téléversé dans LibreFolio. Elle comporte deux sections distinctes avec des règles de visibilité différentes.

---

## 📂 Deux onglets, deux fonctions

### 📁 Ressources statiques

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="files" data-name="static-tab" alt="Onglet Ressources statiques" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Les ressources statiques sont **visibles par tous les utilisateurs** du système. C'est là que vous trouverez :

- 🖼️ Les **avatars** et photos de profil des utilisateurs
- 🏷️ Les **icônes** et logos des courtiers
- 📄 Les **documents partagés** ou images téléversées par les utilisateurs

Ces ressources se trouvent dans le répertoire `custom-uploads/` sur le serveur.

Vous pouvez basculer entre la **vue liste** et la **vue grille** pour un aperçu visuel des fichiers image :

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="files" data-name="static-grid" alt="Vue grille des ressources statiques" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📊 Rapports des courtiers

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="files" data-name="brim-tab" alt="Onglet Rapports des courtiers" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Les rapports des courtiers ont une **visibilité restreinte** — vous ne pouvez voir que les rapports des courtiers auxquels vous avez accès (en tant que Propriétaire, Éditeur ou Lecteur). Ces fichiers incluent :

- 📋 Les **exports de transactions** au format CSV ou Excel provenant de votre courtier
- ✅ Les **résultats analysés** par le système d'importation automatique (BRIM)
- ❌ Les fichiers qui ont **échoué lors de l'analyse** (conservés pour le débogage)

---

## ⬆️ Téléverser des fichiers

Pour téléverser un fichier :

1. Cliquez sur la **zone de téléversement** ou **glissez-déposez** les fichiers directement
2. Pour les **fichiers image**, l'outil [Recadrage d'image](../misc/image-crop.md) s'ouvre automatiquement, vous permettant de redimensionner et recadrer avant le téléversement
3. Pour les **fichiers non-image** (CSV, PDF, etc.), vous pouvez renommer le fichier avant de confirmer

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
 <img class="gallery-img" data-category="media" data-name="file-uploader-empty" alt="Zone de dépôt de fichiers" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! tip "Limite de taille de fichier"
 La taille maximale de téléversement est configurée par l'administrateur système dans les [Paramètres globaux](../../admin/settings.md). La valeur par défaut est généralement de 10 Mo.

---

## 📤 Téléverser des rapports de courtiers

Si vous souhaitez importer des transactions depuis votre courtier :

1. Allez dans l'onglet **Rapports des courtiers**
2. Téléversez le fichier CSV ou Excel exporté depuis votre courtier (Degiro, Interactive Brokers, eToro, Directa, etc.)
3. Le système tentera de **détecter automatiquement** le format du courtier et d'analyser les transactions

!!! note "En cours de développement"
 L'interface complète d'importation des rapports de courtiers (BRIM) est en développement actif. Actuellement, vous pouvez téléverser des rapports et déclencher l'analyse, mais l'assistant d'importation guidé n'est pas encore disponible.

---

## 🔒 Sécurité

- 🌐 Les **ressources statiques** sont accessibles à toute personne possédant un compte LibreFolio
- 🔐 Les **rapports de courtiers** respectent le contrôle d'accès du courtier — seuls les utilisateurs ayant accès à ce courtier peuvent consulter ses rapports
- 🚫 Les **fichiers exécutables** (`.exe`, `.sh`, `.py`, etc.) sont bloqués pour des raisons de sécurité
- 🔍 Le **type MIME** des fichiers est validé côté serveur pour éviter les usurpations (par exemple, renommer un `.exe` en `.jpg`)
