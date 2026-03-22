# 🚀 Premiers pas

Bienvenue sur LibreFolio ! Ce guide vous explique comment créer un compte, vous connecter et créer votre premier courtier — tout ce dont vous avez besoin pour commencer à suivre votre portefeuille.

---

## 📝 1. Créer votre compte

Accédez à l'URL de LibreFolio (par exemple, `http://localhost:8000`) et vous verrez la page de connexion. Cliquez sur **S'inscrire** pour créer un nouveau compte.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Formulaire d'inscription" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Remplissez vos informations :

- 👤 **Nom d'utilisateur** : Votre nom d'affichage (unique dans le système)
- 📧 **Email** : Une adresse email valide
- 🔑 **Mot de passe** : Un mot de passe fort (l'indicateur de force vous aide)

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Inscription avec indicateur de force du mot de passe" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! info "Premier utilisateur = Administrateur"
 Le tout premier utilisateur à s'inscrire devient automatiquement l'**administrateur système** (superutilisateur). Cet utilisateur peut gérer les paramètres globaux, promouvoir d'autres utilisateurs et accéder à toutes les fonctionnalités d'administration.

---

## 🔐 2. Se connecter

Après l'inscription, vous serez redirigé vers la page de connexion. Entrez vos identifiants pour accéder à votre tableau de bord.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="01-login" alt="Page de connexion" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🏦 3. Créer votre premier courtier

Dans LibreFolio, un **courtier** correspond à un compte de courtage — l'endroit où se trouvent vos investissements (par exemple, Interactive Brokers, Degiro, un compte bancaire, etc.).

!!! note "Pourquoi ai-je besoin d'un courtier ?"
 Toutes les transactions dans LibreFolio sont liées à un courtier. C'est le conteneur qui regroupe vos transactions, fichiers importés et rapports. Vous avez besoin d'au moins un courtier avant de pouvoir commencer à suivre quoi que ce soit.

### 📋 Étapes

1. Accédez à la page **Courtiers** depuis le menu latéral
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="list" alt="Liste des courtiers" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>
2. Cliquez sur le bouton **"Nouveau courtier"**
3. Remplissez les détails du courtier :
 - 🏷️ **Nom** : Un nom descriptif (par exemple, "Mon compte Degiro")
 - 💰 **Devise de base** : La devise du compte (par exemple, EUR, USD)
 - 🖼️ **Icône** *(facultatif)* : Téléchargez un logo ou un avatar de courtier
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="edit-modal" alt="Liste des courtiers" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>
4. Une fois créé, vous pouvez cliquer sur un courtier pour voir ses détails, importer des rapports et gérer les transactions.
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="detail" alt="Détails du courtier" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>

---

## 🔮 4. Et ensuite ?

Maintenant que vous avez un compte et un courtier, vous pouvez :

- 📤 **[Importer des rapports de courtier](files/index.md)** — Importer des fichiers CSV/Excel de votre courtier pour l'**analyse** automatique des transactions
- 🤝 **[Partager votre courtier](brokers/sharing.md)** — Donner accès à des membres de la famille, des conseillers ou des comptables
- 💱 **[Configurer les taux de change](fx/index.md)** — Configurer la conversion de devises pour les portefeuilles multi-devises
- ⚙️ **[Personnaliser les paramètres](../admin/settings.md)** — Ajuster la langue, le thème et les préférences système

!!! astuce "Calculs de portefeuille"
 Les courtiers sont également utilisés pour les calculs d'agrégation de portefeuille. Lorsque vous partagez un courtier avec un autre utilisateur et définissez un **pourcentage de partage**, le système peut calculer la part de chaque utilisateur dans la valeur totale du portefeuille. Cette fonctionnalité est **actuellement en développement**.
