# 🚀 Premiers pas

Bienvenue sur LibreFolio ! En quelques étapes, vous créez votre compte, faites un rapide tour d'horizon et importez votre
premier relevé de courtier — et votre tableau de bord se remplit tout seul.

---

## 📝 1. Créer votre compte

Ouvrez votre adresse LibreFolio (par exemple `http://localhost:6040`) : la page de connexion s'affiche. Cliquez sur
**S'inscrire ici** pour créer un compte.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Formulaire d'inscription" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Renseignez vos informations :

- 👤 **Nom d'utilisateur** — unique : c'est avec lui que vous vous connectez.
- 📧 **E-mail** — une adresse valide ; elle sert aussi à la connexion.
- 🔑 **Mot de passe** et **Confirmer le mot de passe** — l'indicateur de robustesse vous indique quand le mot de passe est
  suffisamment fort.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Inscription avec indicateur de robustesse du mot de passe" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! info "Premier utilisateur = Administrateur"

    Le tout premier compte à s'inscrire devient l'**administrateur** : il gère les
    **[Paramètres globaux](../admin/settings.md)** de l'instance et toutes les fonctionnalités d'administration.

---

## 🔐 2. Se connecter

Après votre inscription, vous revenez sur la page de connexion. Connectez-vous avec votre nom d'utilisateur (ou votre e-mail) et votre
mot de passe.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="01-login" alt="Page de connexion" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🎉 3. Configuration d'accueil et visite rapide {: #welcome-setup }

La première fois que vous vous connectez, LibreFolio ouvre une page de **Bienvenue** avant le tableau de bord :

- 🌍 Vérifiez la **Langue** et la **Devise par défaut** : elles reprennent les valeurs par défaut de votre administrateur.
- 🖼️ Ajoutez une **photo de profil** si vous le souhaitez — sinon, vos initiales sont affichées.
- ✅ Cliquez sur **Continuer** pour enregistrer, ou sur **Ignorer définitivement la configuration** pour conserver les paramètres actuels.
- 🚪 Besoin de partir ? La fonction **Se déconnecter** se trouve en haut à droite.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="onboarding" data-name="welcome-setup" alt="La page de bienvenue au premier lancement : le bloc photo de profil avec l'avatar en initiales et Choisir une photo, la Langue et la Devise par défaut pré-remplies, la note indiquant que votre préférence de thème reste inchangée, ainsi que Ignorer définitivement la configuration et Continuer" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Une courte animation de bienvenue suit, puis la **Visite rapide** démarre d'elle-même — cliquez sur **Démarrer la visite**
pour commencer immédiatement, ou sur **✕** pour l'ignorer. La visite montre où se trouvent les choses : le bouton de menu, puis
**Tableau de bord**, **Transactions**, **Courtiers**, **FX**, **Actifs**, **Outils** et **Paramètres**. Elle
ne fait qu'indiquer : elle n'ouvre jamais de formulaire et ne crée aucune donnée.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="onboarding" data-name="core-tour-step" alt="La visite rapide sur le tableau de bord à l'étape 5 sur 8, Taux FX : un cadre et un curseur sur l'entrée Taux FX de la barre latérale, ainsi que le panneau de message avec Précédent et Suivant" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

??? note "👋 Vous utilisez déjà LibreFolio ? — les comptes antérieurs aux guides"

    Si votre compte existait avant l'ajout des guides, LibreFolio ne vous les propose pas :
    la configuration d'accueil est considérée comme **Terminée**, la visite et tous les guides comme **Ignorés**. Vous pouvez toutefois
    les relancer depuis
    **[Paramètres → Préférences → Prise en main et guides](settings/preferences.md#onboarding-and-guides)**.

??? warning "⚠️ La configuration ne se charge pas — que faire"

    Si vos paramètres ou votre progression dans les guides ne peuvent pas être chargés, une page **Nous n'avons pas pu charger la prise en main**
    propose **Réessayer** et **Se déconnecter**. Si votre configuration d'accueil est déjà effectuée, vous verrez peut-être le
    tableau de bord à la place, avec une bannière **Réessayer** en haut.

### 🧭 Guides contextuels

Plus tard, de courts guides démarrent la première fois que vous arrivez à un endroit où ils sont utiles :

| Zone | Guides contextuels |
|---|---|
| **Transactions** | Vue d'ensemble de la page, formulaire Ajouter une transaction, espace de travail groupé et Assistant d'importation |
| **Courtiers** | Page Courtiers, formulaire Ajouter un courtier et détails du courtier |
| **FX** | Page FX, formulaire Ajouter une paire et détails de la paire |
| **Actifs** | Page Actifs, formulaire Ajouter un actif et détails de l'actif |

- Ils pointent vers de vrais contrôles et ne cliquent, ne téléversent, ne modifient ni n'enregistrent jamais à votre place.
- Un cadre pulsant marque la zone dont parle une étape ; un petit curseur marque un bouton que vous pouvez essayer.
  Cliquer dessus effectue son action normale et fait avancer le guide.
- Le panneau de message s'estompe un peu après un moment, pour que vous puissiez voir la page derrière ; survolez-le pour
  le faire réapparaître.
- Quittez une page au milieu d'un guide et son guide reprend à la même étape lorsque vous revenez ; fermer un formulaire
  redémarre le guide de ce formulaire.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="onboarding" data-name="contextual-guide" alt="Le guide de la page FX à l'étape 2 sur 4, sur le filtrage des dates, devises et vues : un cadre autour des filtres de devises, ainsi que le panneau de message avec Précédent et Suivant" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Vous pouvez relancer n'importe quel guide depuis
**[Paramètres → Préférences → Prise en main et guides](settings/preferences.md#onboarding-and-guides)**.

---

## 🏦 4. Importer votre premier relevé (créer un courtier et des actifs à la volée)

Votre tableau de bord est encore vide — que vous y arriviez directement ou après les écrans de bienvenue ci-dessus.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="empty-state" alt="Tableau de bord vide" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La façon la plus rapide de le remplir est d'importer votre historique de transactions. Vous n'avez pas besoin de configurer des courtiers
ni des actifs au préalable : l'Assistant d'importation les crée au fur et à mesure.

### 📋 Étapes

1. **Ouvrir l'Assistant d'importation** : sur la page **[Transactions](transactions/index.md)**, cliquez sur **Importer** (:material-file-upload:). La page de détails d'un courtier propose le même bouton, avec ce courtier déjà sélectionné.

2. **Téléverser votre relevé** : déposez le rapport de votre courtier (`.csv`, `.xlsx` ou `.xls`) dans l'assistant et assignez-le à son courtier — choisissez **Créer nouveau** s'il n'existe pas encore. Chaque rapport que vous téléversez est conservé (vous le retrouvez dans **[Fichiers et téléversements](files/index.md#broker-reports)**) : la prochaine fois, sautez cette étape et cochez le rapport à l'étape suivante.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Étape de téléversement de l'assistant" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

3. **Sélectionner les fichiers et analyser** : cochez les rapports à importer. Chacun reçoit le parseur de son courtier — modifiez-le fichier par fichier si nécessaire, **CSV générique** pour une structure inconnue. LibreFolio lit ensuite chaque ligne et récapitule ce qu'il a trouvé : transactions, titres, problèmes et doublons probables. Certains fichiers nécessitent alors une ou deux étapes supplémentaires (voir le panneau ci-dessous).
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Étape d'analyse de l'assistant" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

4. **Vérifier et importer** : associez chaque titre à votre bibliothèque d'actifs, ou créez-le **à la volée** avec les informations lues dans le relevé. Les doublons probables arrivent décochés, et les lignes antérieures à la date d'ouverture du courtier sont écartées. Plus d'informations dans **[Mappage des actifs](transactions/import/index.md#asset-mapping)**.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Étape de vérification de l'assistant : résolution des actifs" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

5. **Enregistrer depuis l'éditeur groupé** : **Importer N transactions** déplace les lignes cochées dans l'éditeur groupé — rien n'est encore enregistré. Jetez-y un dernier coup d'œil, puis cliquez sur **Tout enregistrer**.

??? note "🧩 Étapes supplémentaires — uniquement si vos fichiers en ont besoin"

    L'assistant ajoute une étape uniquement lorsque vos fichiers le nécessitent ; un rapport unique et propre les saute
    toutes :

    - **Unifier les actifs** — le même titre apparaît sous différents noms ou codes.
    - **Corrections** — certaines lignes n'ont pas pu être entièrement lues.
    - **Doublons** — le même mouvement figure dans deux fichiers que vous importez ensemble.
    - **Aligner avec la banque** — après **Vérifier**, pour un lot de rapports tel que Danske Bank, lorsque les
      chiffres de la banque diffèrent de ceux de LibreFolio.

    Voir **[Étapes qui n'apparaissent qu'en cas de besoin](transactions/import/how-to.md#only-when-needed)**.

La première fois que vous ouvrez l'assistant, un guide vous accompagne à travers les étapes nécessaires à vos fichiers ; il ne
clique ni n'enregistre jamais à votre place (voir **[Première importation guidée](transactions/import/how-to.md#guided-first-import)**).
Pour la procédure complète, voir **[Comment importer des transactions](transactions/import/how-to.md)** ; pour les
courtiers et formats de fichiers pris en charge, voir **[Importer depuis un courtier](transactions/import/index.md)**.

---

## 📈 5. Retour au tableau de bord

Revenez au **Tableau de bord** : la valeur de votre portefeuille, votre allocation (par type, secteur et zone géographique)
et votre historique de performance sont désormais renseignés.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="main" alt="Vue principale du tableau de bord" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔮 6. Et ensuite ?

Maintenant que votre portefeuille est renseigné, vous pouvez :

- 🤝 **[Partager votre courtier](brokers/sharing.md)** — Donnez accès à des membres de votre famille ou à des conseillers.
- 💱 **[Configurer les taux de change](fx/index.md)** — Configurez la conversion de devise pour les portefeuilles multidevises.
- ⚙️ **[Personnaliser vos préférences](settings/preferences.md)** — Ajustez votre langue, votre devise par défaut et votre thème. Les administrateurs gèrent également les **[Paramètres globaux](../admin/settings.md)** à l'échelle du système.
- 🧭 **[Relancer la configuration d'accueil ou les visites guidées](settings/preferences.md#onboarding-and-guides)** — Revenez à tout moment sur l'écran de bienvenue, la visite rapide ou le guide d'importation depuis Paramètres → Préférences.
- 📱 **[Installer LibreFolio comme application](pwa.md)** — Placez-le sur l'écran d'accueil de votre téléphone ou dans sa propre fenêtre de bureau.
