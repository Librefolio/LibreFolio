# 🚀 Prise en main

Bienvenue sur LibreFolio ! Ce guide vous accompagne dans l'enregistrement d'un compte, la connexion et la création de votre premier courtier — tout ce dont vous avez besoin pour commencer à suivre votre portefeuille.

---

## 📝 1. Enregistrer votre compte

Naviguez vers l'URL de LibreFolio (par exemple, `http://localhost:6040`) et vous verrez la page de connexion. Cliquez sur **S'enregistrer** pour créer un nouveau compte.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Registration Form" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Remplissez vos informations :

- 👤 **Nom d'utilisateur** : Votre nom d'affichage (unique dans tout le système)
- 📧 **E-mail** : Une adresse e-mail valide
- 🔑 **Mot de passe** : Un mot de passe robuste (l'indicateur de force vous guide)

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Registration with Password Strength" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! info "First User = Admin"

    Le tout premier utilisateur à s'enregistrer devient automatiquement l'**administrateur du système** (superuser). Cet utilisateur peut gérer les paramètres globaux, promouvoir d'autres utilisateurs et accéder à toutes les fonctionnalités d'administration.

---

## 🔐 2. Se connecter

Après vous être enregistré, vous serez redirigé vers la page de connexion. Entrez vos identifiants pour accéder à votre tableau de bord.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="01-login" alt="Login Page" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🏦 3. Créer votre premier courtier

Un **Courtier** dans LibreFolio représente un compte de courtage — l'endroit où se trouvent vos investissements (par exemple, Interactive Brokers, Degiro, un compte bancaire, etc.).

!!! note "Why do I need a Broker?"

    Toutes les transactions dans LibreFolio sont liées à un courtier. C'est le conteneur qui regroupe vos transactions, vos imports et vos rapports. Vous avez besoin d'au moins un courtier avant de pouvoir commencer tout suivi de portefeuille.

### 📋 Étapes

1. Naviguez vers la page **Courtiers** depuis la barre latérale
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="list" alt="Broker List" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>
2. Cliquez sur le bouton **"Nouveau Courtier"**
3. Remplissez les détails du courtier :
 - 🏷️ **Nom** : Un nom descriptif (ex: "Mon compte Degiro")
 - 💰 **Devise de base** : La devise du compte (ex: EUR, USD)
 - 🖼️ **Icône** *(optionnel)* : Téléchargez un logo ou un avatar du courtier
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="edit-modal" alt="Broker List" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>
4. Une fois créé, vous pouvez cliquer sur un courtier pour voir ses détails, importer des rapports et gérer les transactions.
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="detail" alt="Broker Detail" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>

---

## 🔮 4. Et après ?

Maintenant que vous avez un compte et un courtier, vous pouvez :

- 📤 **[Importer des rapports de courtage](files/index.md)** — Importez des fichiers CSV/Excel de votre courtier pour une analyse automatique des transactions
- 🤝 **[Partager votre courtier](brokers/sharing.md)** — Donnez l'accès à des membres de votre famille, des conseillers ou des comptables
- 💱 **[Configurer les taux FX](fx/index.md)** — Configurez la conversion de devise pour les portefeuilles multi-devises
- ⚙️ **[Personnaliser les paramètres](../admin/settings.md)** — Ajustez la langue, le thème et les préférences du système

!!! tip "Portfolio Calculations"

    Les courtiers sont également utilisés pour les calculs d'agrégation de portefeuille. Lorsque vous partagez un courtier avec un autre utilisateur et définissez un **pourcentage de partage**, le système peut calculer la part de chaque utilisateur dans la valeur totale du portefeuille. Cette fonctionnalité est en cours de développement actif.
