# 🚀 Pour commencer

Bienvenue sur LibreFolio ! Ce guide vous accompagne pas à pas dans la création d'un compte, la connexion et l'importation de votre premier relevé de courtier afin d'alimenter instantanément votre tableau de bord.

---

## 📝 1. Créer votre compte

Accédez à l'URL LibreFolio (par exemple, `http://localhost:6040`) et vous verrez la page de connexion. Cliquez sur **S'inscrire** pour créer un nouveau compte.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Registration Form" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Renseignez vos informations :

- 👤 **Nom d'utilisateur** : votre nom d'affichage (unique dans le système)
- 📧 **E-mail** : une adresse e-mail valide
- 🔑 **Mot de passe** : un mot de passe robuste (l'indicateur de robustesse vous aide)

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Registration with Password Strength" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! info "Premier utilisateur = Administrateur"

    Le tout premier utilisateur à s'inscrire devient automatiquement **l'administrateur système** (superutilisateur). Cet utilisateur peut gérer les paramètres globaux, promouvoir d'autres utilisateurs et accéder à toutes les fonctionnalités d'administration.

---

## 🔐 2. Se connecter

Après l'inscription, vous serez redirigé vers la page de connexion. Saisissez vos identifiants pour accéder à votre tableau de bord.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="01-login" alt="Login Page" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🏦 3. Importer votre premier relevé (créer le courtier et les actifs à la volée)

Lors de votre première connexion, vous serez accueilli par un tableau de bord vide, sans aucune donnée.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="dashboard" data-name="empty-state" alt="Empty Dashboard" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Dans LibreFolio, le moyen le plus rapide de commencer est d'importer directement votre historique de transactions. Pas besoin de configurer les courtiers ou les actifs au préalable : le système les crée automatiquement pour vous pendant le processus d'importation !

### 📋 Étapes

1. **Ouvrir l'assistant d'importation** : accédez à la page **[Transactions](transactions/index.md)** depuis le menu de la barre latérale et cliquez sur le bouton **« Importer »** (:material-file-upload:). Vous pouvez également démarrer depuis la page de détail d'un courtier — dans ce cas, le courtier est présélectionné.

2. **Téléverser votre relevé** : déposez le fichier de relevé de votre courtier (`.csv`, `.xlsx` ou `.xls`) dans la première étape de l'assistant — le glisser-déposer fonctionne ici — et associez-le à un courtier, en créant le courtier **à la volée** s'il est nouveau. Cette étape est facultative : les relevés téléversés lors de sessions précédentes sont déjà stockés, et l'étape suivante les répertorie.
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Wizard Upload Step" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>

3. **Sélectionner les fichiers et analyser** : choisissez précisément quels relevés stockés importer. Chaque fichier reçoit son analyseur présélectionné à partir du plugin d'importation par défaut du courtier (modifiable par fichier — utilisez **Generic CSV** pour un format inconnu), puis LibreFolio lit et valide chaque ligne. Un résumé consolidé indique ce qui sera réellement importé : transactions, titres distincts, problèmes de validation, tâches à faire, avertissements et doublons probables.
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Wizard Parse Step" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>

4. **Étapes supplémentaires, uniquement si nécessaire** : selon le contenu de vos fichiers, jusqu'à trois étapes supplémentaires apparaissent — **Unifier les actifs** (le même titre trouvé sous des noms ou codes différents), **Corrections** (les lignes que l'analyseur n'a pas pu lire entièrement) et **Doublons** (le même mouvement présent dans deux fichiers importés ensemble). Un relevé propre à fichier unique les ignore toutes.

5. **Vérifier et importer** : associez chaque instrument à votre bibliothèque d'actifs — ou créez-le **à la volée** avec des détails préremplis à partir du relevé — et vérifiez les indicateurs par ligne : les doublons (par rapport à votre comptabilité existante, ou les copies exactes en attente dans cette importation) arrivent décochés, et les lignes datées avant la date d'ouverture du courtier sont exclues automatiquement. Pour plus d'informations, consultez le guide **[Importation depuis un courtier - Correspondance des actifs](transactions/import/index.md#asset-mapping)**.
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Wizard Review Step: Asset Resolution" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>

6. **Enregistrer à partir de l'éditeur en masse** : cliquer sur **Importer N transactions** transfère les lignes sélectionnées vers l'éditeur en masse sous forme de nouvelles lignes — rien n'est encore écrit. Jetez-y un dernier coup d'œil, puis cliquez sur **Tout enregistrer** pour les intégrer à votre portefeuille.

!!! tip "Pas besoin de téléverser à nouveau"

    Les relevés téléversés lors de sessions précédentes sont déjà répertoriés dans l'étape **Sélectionner les fichiers** de l'assistant — il suffit de les re-cocher. Vous pouvez également prévisualiser ou supprimer les relevés stockés depuis la page **[Fichiers et téléversements](files/index.md#broker-reports)**.

Pour le guide complet, consultez **[Comment importer des transactions](transactions/import/how-to.md)** ; pour les courtiers et formats de fichiers pris en charge, consultez **[Importation depuis un courtier](transactions/import/index.md)**.

---

## 📈 4. Retour au tableau de bord

Après avoir importé votre relevé avec succès, revenez au **Tableau de bord**.

LibreFolio calcule en temps réel les indicateurs de votre portefeuille, l'allocation d'actifs (par type, secteur, géographie) et l'historique des performances. Vous pouvez désormais voir l'ensemble de votre situation financière magnifiquement représentée !

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="dashboard" data-name="main" alt="Dashboard Main View" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔮 5. Et ensuite ?

Maintenant que votre portefeuille est alimenté, vous pouvez :

- 🤝 **[Partager votre courtier](brokers/sharing.md)** — Donner accès à des membres de la famille ou à des conseillers.
- 💱 **[Configurer les taux de change](fx/index.md)** — Configurer la conversion de devise pour les portefeuilles multi-devises.
- ⚙️ **[Personnaliser les paramètres](../admin/settings.md)** — Ajuster la langue, le thème et les préférences système.
