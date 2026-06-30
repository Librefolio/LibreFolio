# 🚀 Guide de Démarrage

Bienvenue dans LibreFolio ! Ce guide vous accompagne dans l'enregistrement de votre compte, la connexion et l'importation de votre premier relevé de courtier pour alimenter instantanément votre tableau de bord.

---

## 📝 1. Enregistrez votre Compte

Naviguez vers l'URL de LibreFolio (par exemple, `http://localhost:6040`) et vous verrez la page de connexion. Cliquez sur **Register** pour créer un nouveau compte.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Registration Form" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Remplissez vos coordonnées :

- 👤 **Username**: Votre nom d'affichage (unique dans le système)
- 📧 **Email**: Une adresse e-mail valide
- 🔑 **Password**: Un mot de passe fort (l'indicateur de force vous aidera)

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Registration with Password Strength" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! info "Premier Utilisateur = Admin"

    Le tout premier utilisateur à s'enregistrer devient automatiquement l'**administrateur système** (superutilisateur). Cet utilisateur peut gérer les paramètres globaux, promouvoir d'autres utilisateurs et accéder à toutes les fonctionnalités d'administration.

---

## 🔐 2. Connectez-vous

Après vous être enregistré, vous serez redirigé vers la page de connexion. Entrez vos identifiants pour accéder à votre tableau de bord.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="01-login" alt="Login Page" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🏦 3. Importez votre Premier Relevé (Créez le Courtier et les Actifs à la Volée)

Lors de votre première connexion, vous serez accueilli par un tableau de bord vide.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="empty-state" alt="Tableau de Bord Vide" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Dans LibreFolio, le moyen le plus rapide de commencer est d'importer directement votre historique de transactions. Il n'est pas nécessaire de configurer au préalable des courtiers ou des actifs : le système les créera automatiquement lors du processus d'importation !

### 📋 Étapes

1. **Téléchargez votre Relevé** : Accédez à la page des **[Transactions](transactions/index.md)** depuis le menu latéral. Cliquez sur le bouton **"Importer"** (:material-file-upload:) ou **glissez-déposez** le fichier de relevé de votre courtier (CSV ou PDF) directement sur la page.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Assistant Étape 1 : Télécharger" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

2. **Configuration de l'Analyseur** : L'assistant détectera automatiquement le format du relevé. Vous pouvez vérifier les paramètres (tels que formats de date et délimiteurs) et configurer les options de secours (fallback) si vous importez un relevé CSV générique.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Assistant Étape 2 : Configuration de l'Analyseur" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>
    
    !!! tip "Re-traiter les relevés existants"
    
        Vous pouvez également re-traiter (re-process) tout relevé précédemment téléchargé directement depuis la page **[Files & Uploads](files/index.md#broker-reports)**. C'est particulièrement utile après la mise à jour d'un plugin d'importation ou si vous avez accidentellement supprimé des transactions et souhaitez les restaurer.

3. **Analyse et Lecture** : Le système lit, valide et traite les lignes du relevé. Vous verrez une barre de progression indiquant la vitesse et l'état de la lecture.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Assistant Étape 3 : Analyse" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

4. **Résolution Courtier et Actifs** : Si le rapport contient un compte de courtier ou des actifs (tels que des ETF, actions) qui n'existent pas encore dans votre instance LibreFolio, le système les signalera. Vous pouvez rechercher des éléments existants ou les créer **à la volée** (on-the-fly) directement dans l'assistant, avec les informations pré-remplies du relevé. Pour plus de détails, consultez la section **[Import from Broker - Asset Mapping](transactions/import/index.md#asset-mapping)**.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Assistant Étape 4 : Résolution" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

5. **Détection des Doublons** : L'assistant compare les transactions du relevé avec votre historique existant. Il regroupe les correspondances potentielles dans deux badges de statut de l'interface utilisateur basés sur 4 niveaux de confiance :
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Assistant Étape 5 : Détection des Doublons" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>
    
    | Badge UI | Niveau de Confiance | Critères / Règles de Correspondance |
    | :--- | :--- | :--- |
    | <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY_WITH_ASSET` | Les champs de base et la description correspondent, et l'actif a été résolu automatiquement (doublon hautement probable). |
    | <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY` | Les champs de base et la description correspondent, mais l'actif n'est pas résolu. |
    | <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE_WITH_ASSET` | Les champs de base correspondent et l'actif a été résolu automatiquement (mais la description diffère ou est vide). |
    | <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE` | Les champs de base (type, date, quantité, montant) correspondent, mais l'actif n'est pas résolu. |
    | <span style="background-color: rgba(16, 185, 129, 0.15); color: #10b981; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">✅ UNIQUE</span> | — | La transaction ne présente aucune correspondance dans la base de données et est considérée comme nouvelle (aucun doublon détecté). |
    | <span style="background-color: rgba(239, 68, 68, 0.15); color: #ef4444; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">❌ NON RÉSOLU</span> | — | Le courtier ou l'instrument financier n'a pas été associé à une entité existante dans la base de données (nécessite une résolution à l'Étape 4 avant l'importation). |

    Pour plus de détails sur les règles et la configuration des doublons, consultez la section **[Import from Broker - Duplicate Detection](transactions/import/index.md#duplicate-detection)**.

6. **Mise en attente et Révision Finale**: Examinez la liste de toutes les transactions analysées. Une fois tout vérifié et correct, cliquez sur **Importer** pour enregistrer les transactions dans votre portefeuille.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Assistant Étape 6 : Révision Finale" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

    Le tableau de révision affiche les colonnes suivantes :

    - **Date**: La data d'exécution de la transaction.
    - **Type**: Le type d'opération financière (ACHAT, VENTE, DIVIDENDE, DÉPÔT, etc.).
    - **Asset**: L'actif correspondant de votre bibliothèque.
    - **Quantity**: Le nombre d'unités ou d'actions négociées.
    - **Price**: Le prix unitaire de l'actif.
    - **Net Amount**: L'impact total de trésorerie (positif ou négatif) sur le compte.
    - **Fees/Taxes**: Les commissions de courtage ou taxes de transaction incluses.

    Pour les paramètres avancés ou erreurs de validation en staging, consultez la page **[Import from Broker](transactions/import/index.md)**.

---

## 📈 4. Retour au Tableau de Bord

Après avoir importé votre relevé avec succès, retournez sur le **Tableau de Bord**.

LibreFolio calcule toutes les métriques de votre portefeuille, l'allocation d'actifs (par type, secteur, zone géographique) et l'historique des performances en temps réel. Vous pouvez maintenant voir l'intégralité de votre situation financière magnifiquement représentée graphiquement !

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="main" alt="Dashboard View" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔮 5. Et ensuite ?

Maintenant que votre portefeuille est alimenté, vous pouvez :

- 🤝 **[Partager votre courtier](brokers/sharing.md)** — Accordez l'accès à des membres de votre famille ou à des conseillers.
- 💱 **[Configurer les taux de change](fx/index.md)** — Configurez la conversion de devises pour les portefeuilles multi-devises.
- ⚙️ **[Personnaliser les paramètres](../admin/settings.md)** — Ajustez la langue, le thème et les préférences système.
