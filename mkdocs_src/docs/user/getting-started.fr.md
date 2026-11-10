# 🚀 Premiers pas

Bienvenue dans LibreFolio ! En quelques étapes, vous créez votre compte, faites une visite rapide et importez votre
premier relevé de courtier — et votre tableau de bord se remplit tout seul.

---

## 📝 1. Créez votre compte

Ouvrez l'adresse de votre instance LibreFolio (par exemple `http://localhost:6040`) : la page de connexion s'affiche. Cliquez sur
**S'inscrire ici** pour créer un compte.

Si la page de connexion n'affiche pas **S'inscrire ici**, votre administrateur n'autorise l'accès qu'avec un
lien d'invitation, ou a fermé les inscriptions : demandez-lui une invitation ou un compte. Si vous avez une
invitation, suivez [Si vous avez reçu un lien d'invitation](#invitation-link).

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Formulaire d'inscription" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Remplissez vos informations :

- 👤 **Nom d'utilisateur** — unique, de 3 à 50 caractères, sans `@` : vous vous connectez avec celui-ci. Les espaces, les lettres accentuées
  et les signes tels que `.`, `_`, `-` ou `+` sont acceptés. Lorsque vous vous connectez, LibreFolio interprète
  tout ce qui contient un `@` comme une adresse e-mail ; c'est pourquoi le formulaire refuse un nom d'utilisateur contenant un `@` : *Le nom d'utilisateur ne peut pas contenir @ :
  pour vous connecter, vous pouvez toujours utiliser votre adresse e-mail.*
- 📧 **E-mail** — une adresse valide ; elle sert aussi à la connexion.
- 🔑 **Mot de passe** et **Confirmer le mot de passe** — l'indicateur de robustesse vous indique quand le mot de passe est
  suffisamment fort.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Inscription avec indicateur de robustesse du mot de passe" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! info "Premier utilisateur = administrateur"

    Le tout premier compte inscrit devient **administrateur** : il gère les **[paramètres globaux](../admin/settings.md)** de l'instance
    et toutes les fonctionnalités d'administration.

### ✉️ Si vous avez reçu un lien d'invitation {: #invitation-link }

Un administrateur peut vous inviter avec un lien qui vous est propre, par message ou par e-mail : l'e-mail s'intitule
*Vous êtes invité à LibreFolio*, et son bouton **Créer votre compte** ouvre le lien.

1. Ouvrez le lien. LibreFolio le vérifie, puis affiche le formulaire d'inscription avec une note indiquant que vous avez
   été invité ; une seconde note vous précise si l'invitation fait de vous un administrateur.
2. Si l'administrateur a indiqué votre adresse e-mail sur l'invitation, elle est déjà remplie : vous
   pouvez la modifier.
3. Choisissez votre nom d'utilisateur et votre mot de passe, puis cliquez sur **S'inscrire**.
4. Vous revenez à la page de connexion, avec une confirmation : connectez-vous avec votre nouveau compte.

- ⏱️ Un lien d'invitation fonctionne une seule fois, pendant 7 jours. Si la page indique que le lien a expiré, a déjà
  été utilisé, a été retiré ou n'est pas valide, demandez-en un nouveau à votre administrateur.
- 📬 Si l'instance vous demande de confirmer votre adresse e-mail, ouvrez le lien qu'elle vous envoie par e-mail avant de vous
  connecter : voir [Si LibreFolio vous demande de confirmer votre adresse e-mail](#verify-email).
- 🔒 Dès que la page s'ouvre, la barre d'adresse perd la partie secrète du lien : conservez le message
  reçu au cas où vous auriez besoin de rouvrir le lien. Si la page indique que le lien est incomplet,
  rouvrez-le depuis ce message.
- 🚪 Si la page indique que l'inscription est désactivée, l'administrateur a fermé les inscriptions pour le moment :
  demandez-lui.

### 📬 Si LibreFolio vous demande de confirmer votre adresse e-mail {: #verify-email }

Certaines instances demandent à chaque nouveau compte de confirmer son adresse e-mail avant la première connexion. Dans ce cas,
après **S'inscrire** :

1. La page de connexion indique : *Compte créé. Nous vous envoyons un e-mail contenant un lien pour l'activer :
   ouvrez-le dans les 24 heures, puis connectez-vous. Pas d'e-mail après quelques minutes ? Vérifiez le dossier des spams, puis
   connectez-vous avec votre nom d'utilisateur et votre mot de passe : un nouveau lien vous sera proposé.* Vous ne pouvez pas encore vous connecter.
2. Ouvrez l'e-mail *Confirmez votre adresse e-mail* et cliquez sur **Confirmer mon adresse e-mail**. Si le
   bouton ne fonctionne pas, copiez dans votre navigateur l'adresse écrite en dessous.
3. Le bouton ouvre une page LibreFolio qui vous demande de confirmer. Cliquez sur **Confirmer mon adresse e-mail**
   à cet endroit : LibreFolio confirme alors votre adresse et vous ramène à la page de connexion, avec une
   confirmation : connectez-vous avec votre nom d'utilisateur et votre mot de passe.

- 🖱️ Pourquoi un clic de plus ? Certains services de messagerie ouvrent eux-mêmes les liens d'un message pour les vérifier
  : le clic permet de s'assurer que c'est bien vous qui confirmez.
- 🙋 Si vous ne vous êtes pas inscrit sur cette instance, fermez simplement la page : rien ne se passe.
- ⏱️ Le lien fonctionne une seule fois, pendant 24 heures.
- 📭 Pas d'e-mail ? Regardez dans le dossier des spams. Ensuite, sur la page de connexion, connectez-vous avec votre nom d'utilisateur et
  votre mot de passe : LibreFolio indique que votre adresse n'est pas encore vérifiée et propose **Renvoyer le lien**
  en dessous. Un nouveau lien remplace les précédents. Si vous demandez trop souvent, ou après trop de mots de passe erronés,
  la page vous indique dans combien de minutes vous pourrez redemander.
- 🚦 Si la page de connexion indique plutôt que l'e-mail d'activation n'a pas pu être envoyé pour le moment, parce qu'il y a
  eu trop d'inscriptions depuis votre réseau au cours de la dernière heure (ou que l'instance a envoyé trop d'e-mails),
  aucun e-mail n'est en route. Votre compte est tout de même créé : attendez le nombre de minutes indiqué par la page,
  puis connectez-vous avec votre nom d'utilisateur et votre mot de passe, et **Renvoyer le lien** vous sera proposé.
- ⌛ Si la page indique que le lien a expiré, connectez-vous de la même manière : un nouveau lien vous sera proposé.
  Si, entre-temps, l'instance n'a plus de place disponible, demandez à votre administrateur.
- ✅ Si la page indique que le lien a déjà été utilisé, votre compte est probablement déjà actif :
  connectez-vous.
- 🔒 Comme pour une invitation, la barre d'adresse perd la partie secrète du lien dès que la page
  s'ouvre : conservez l'e-mail jusqu'à ce que votre compte soit actif.

---

## 🔐 2. Connexion

Après votre inscription, vous revenez à la page de connexion. Connectez-vous avec votre nom d'utilisateur (ou votre e-mail) et votre
mot de passe. Saisissez votre nom d'utilisateur exactement comme vous l'avez choisi, majuscules comprises. Si votre nom d'utilisateur contient
un `@`, ce qui peut être le cas des comptes créés avant la version 1.3, connectez-vous plutôt avec votre adresse e-mail.
Si LibreFolio vous a demandé de confirmer votre adresse e-mail, ouvrez d'abord le lien qu'il vous a envoyé par e-mail
: voir [Si LibreFolio vous demande de confirmer votre adresse e-mail](#verify-email).

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="01-login" alt="Page de connexion" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Sous la carte, comme sur chaque page de connexion, une ligne affiche les [mentions légales](settings/about.md#legal-notice)
de votre instance.

!!! note "Trop de tentatives de connexion"

    Après 10 mots de passe erronés en 15 minutes pour le même nom d'utilisateur ou la même adresse e-mail, ou 50 depuis la même adresse IP,
    la page de connexion indique *Trop de tentatives de connexion : attendez quelques minutes et réessayez.*
    Jusqu'à la fin de l'attente, même le bon mot de passe est refusé : attendez jusqu'à 15 minutes, puis
    connectez-vous. Votre administrateur peut aussi vous laisser entrer immédiatement en redémarrant LibreFolio.

### 📧 Si vous avez oublié votre mot de passe {: #forgot-password }

Sur la page de connexion, cliquez sur **Mot de passe oublié ?**. Lorsque votre instance peut envoyer des e-mails, la page affiche un
formulaire en haut :

1. Saisissez votre nom d'utilisateur ou votre adresse e-mail, puis cliquez sur **Envoyez-moi un lien de réinitialisation**.
2. La page répond *E-mail envoyé : vérifiez aussi vos spams.*, de la même manière, qu'un compte corresponde ou non : regardez dans votre boîte de réception et dans le
   dossier des spams.
3. Ouvrez l'e-mail *Réinitialisez votre mot de passe LibreFolio* et cliquez sur **Choisir un nouveau mot de passe**. La page
   qui s'ouvre est celle d'un lien envoyé par un administrateur : suivez
   [Si un administrateur vous a envoyé un lien de réinitialisation du mot de passe](#password-reset-link) à partir de l'étape 2.

- ⏱️ Le lien fonctionne une seule fois, pendant 30 minutes.
- 📭 Pas d'e-mail après quelques minutes ? Le compte est peut-être désactivé ou enregistré avec une autre
  adresse, ou les demandes ont été faites trop rapprochées : réessayez plus tard ou demandez à votre administrateur.
- ⏳ Après une demande, le bouton affiche un compte à rebours de 5 minutes avant que vous puissiez redemander : le serveur
  envoie au plus un e-mail toutes les 5 minutes pour le même compte. Recharger la page conserve le compte à rebours.
- 💻 Lorsque votre instance ne peut pas envoyer d'e-mails, la page affiche à la place la commande que votre administrateur
  exécute sur le serveur pour réinitialiser un mot de passe : demandez-lui.

### 🔑 Si un administrateur vous a envoyé un lien de réinitialisation du mot de passe {: #password-reset-link }

Votre administrateur peut aussi vous envoyer un lien pour choisir vous-même un nouveau mot de passe, par message ou par
e-mail.

1. Ouvrez le lien : la page affiche le compte auquel il appartient.
2. Saisissez deux fois le nouveau mot de passe : il doit respecter les règles indiquées sous le champ.
3. Cliquez sur **Définir le nouveau mot de passe**. Vous revenez à la page de connexion, avec une confirmation : connectez-vous avec
   le nouveau mot de passe.

- ⏱️ Le lien fonctionne une seule fois, pendant 30 minutes. Si la page indique qu'il a expiré, qu'il a déjà été utilisé ou
  qu'il a été retiré, demandez-en un nouveau : chaque nouveau lien retire ceux envoyés avant lui.
- 🚪 La définition du nouveau mot de passe déconnecte votre compte sur tous les appareils : reconnectez-vous avec le nouveau
  mot de passe sur chacun d'eux.

---

## 🎉 3. Configuration d'accueil et visite rapide {: #welcome-setup }

La première fois que vous vous connectez, LibreFolio ouvre une page **Bienvenue** avant le tableau de bord :

- 🌍 Vérifiez **Langue** et **Devise par défaut** : elles reprennent les valeurs par défaut de votre administrateur.
- 🖼️ Ajoutez une **photo de profil** si vous le souhaitez — sinon, vos initiales sont affichées.
- ✅ Cliquez sur **Continuer** pour enregistrer, ou sur **Ignorer définitivement la configuration d'accueil** pour conserver les paramètres actuels.
- 🚪 Besoin de partir ? **Se déconnecter** se trouve en haut à droite.
- ⚖️ Sous la carte : les [mentions légales](settings/about.md#legal-notice) de votre instance.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="onboarding" data-name="welcome-setup" alt="La page Bienvenue de la première connexion : le bloc de photo de profil avec l'avatar à initiales et Choisir une image, Langue et Devise par défaut préremplies, la note indiquant que votre préférence de thème reste inchangée, ainsi que les boutons Ignorer définitivement la configuration d'accueil et Continuer" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Une courte animation de bienvenue suit, puis la **Visite rapide** démarre d'elle-même — cliquez sur **Commencer la visite**
pour commencer tout de suite, ou sur **✕** pour l'ignorer. La visite montre où se trouvent les choses : le bouton de menu, puis
**Tableau de bord**, **Transactions**, **Courtiers**, **FX**, **Actifs**, **Outils** et **Paramètres**. Elle
ne fait qu'indiquer : elle n'ouvre jamais de formulaire et ne crée aucune donnée.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="onboarding" data-name="core-tour-step" alt="La visite rapide sur le tableau de bord à l'étape 5 sur 8, taux de change : un cadre et un curseur sur l'entrée Taux de change de la barre latérale, et le panneau de message avec Précédent et Suivant" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

??? note "👋 Vous utilisez déjà LibreFolio ? — comptes plus anciens que les guides"

    Si votre compte existait avant l'ajout des guides, LibreFolio ne vous les fait pas parcourir :
    la configuration d'accueil est considérée comme **Terminée**, la visite et chaque guide comme **Ignorés**. Vous pouvez néanmoins
    les relancer à tout moment depuis
    **[Paramètres → Préférences → Prise en main et guides](settings/preferences.md#onboarding-and-guides)**.

??? warning "⚠️ La configuration d'accueil ne se charge pas — que faire"

    Si vos paramètres ou la progression de vos guides ne peuvent pas être chargés, une page **Impossible de charger la prise en main**
    propose **Réessayer** et **Se déconnecter**. Si votre configuration d'accueil est déjà terminée, vous pouvez plutôt voir le
    tableau de bord, avec une bannière **Réessayer** en haut.

### 🧭 Guides contextuels

Plus tard, de courts guides démarrent la première fois que vous arrivez à un endroit où ils sont utiles :

| Zone | Guides contextuels |
|---|---|
| **Transactions** | Vue d'ensemble de la page, formulaire Ajouter une transaction, espace de travail groupé et assistant d'importation |
| **Courtiers** | Page Courtiers, formulaire Ajouter un courtier et détails du courtier |
| **FX** | Page FX, formulaire Ajouter une paire FX et détails de la paire FX |
| **Actifs** | Page Actifs, formulaire Ajouter un actif et détails de l'actif |

- Ils pointent vers de vrais contrôles et ne cliquent jamais, ne téléversent jamais, ne modifient jamais et n'enregistrent jamais à votre place.
- Un cadre pulsant marque la zone dont parle une étape ; un petit curseur marque un bouton que vous pouvez essayer.
  Cliquer dessus effectue son action normale et fait avancer le guide.
- Le panneau de message s'estompe légèrement au bout d'un instant, pour que vous puissiez voir la page derrière ; survolez-le pour
  le faire réapparaître.
- Quittez une page au milieu d'un guide et son guide reprend à la même étape lorsque vous revenez ; fermer un formulaire
  redémarre le guide de ce formulaire.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="onboarding" data-name="contextual-guide" alt="Le guide de la page FX à l'étape 2 sur 4, sur le filtrage des dates, des devises et des vues : un cadre autour des filtres de devises, et le panneau de message avec Précédent et Suivant" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Vous pouvez relancer n'importe quel guide depuis
**[Paramètres → Préférences → Prise en main et guides](settings/preferences.md#onboarding-and-guides)**.

---

## 🏦 4. Importez votre premier relevé (créer un courtier et des actifs à la volée)

Votre tableau de bord est encore vide — que vous y arriviez directement ou après les écrans de bienvenue ci-dessus.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="empty-state" alt="Tableau de bord vide" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Le moyen le plus rapide de le remplir est d'importer votre historique de transactions. Vous n'avez pas besoin de configurer d'abord des courtiers
ou des actifs : l'assistant d'importation les crée au fur et à mesure.

### 📋 Étapes

1. **Ouvrez l'assistant d'importation** : sur la page **[Transactions](transactions/index.md)**, cliquez sur **Importer** (:material-file-upload:). La page de détail d'un courtier propose le même bouton, avec ce courtier déjà sélectionné.

2. **Téléversez votre relevé** : déposez le rapport de votre courtier (`.csv`, `.xlsx` ou `.xls`) dans l'assistant et affectez-le à son courtier — choisissez **Créer un nouveau** si le courtier n'existe pas encore. Chaque rapport que vous téléversez est conservé (vous le retrouvez dans **[Fichiers et téléversements](files/index.md#broker-reports)**) : la prochaine fois, sautez cette étape et cochez le rapport à l'étape suivante.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Étape de téléversement de l'assistant" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

3. **Sélectionnez les fichiers et analysez** : cochez les rapports à importer. Chacun reçoit l'analyseur de son courtier — modifiez-le par fichier si nécessaire, **CSV générique** pour un format inconnu. LibreFolio lit ensuite chaque ligne et récapitule ce qu'il a trouvé : transactions, titres, anomalies et doublons probables. Certains fichiers nécessitent alors une ou deux étapes supplémentaires (voir le panneau ci-dessous).
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Étape d'analyse de l'assistant" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

4. **Vérifiez et importez** : associez chaque titre à votre bibliothèque d'actifs, ou créez-le **à la volée** avec les informations lues dans le relevé. Les doublons probables arrivent décochés, et les lignes antérieures à la date d'ouverture du courtier sont exclues. Plus d'informations dans **[Association des actifs](transactions/import/index.md#asset-mapping)**.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Étape de vérification de l'assistant : résolution des actifs" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

5. **Enregistrez depuis l'éditeur groupé** : **Importer N transactions** déplace les lignes cochées dans l'éditeur groupé — rien n'est encore enregistré. Jetez-y un dernier coup d'œil, puis cliquez sur **Tout enregistrer**.

??? note "🧩 Étapes supplémentaires — uniquement lorsque vos fichiers en ont besoin"

    L'assistant ajoute une étape uniquement lorsque vos fichiers l'exigent ; un rapport unique et propre les saute
    toutes :

    - **Unifier les actifs** — le même titre apparaît sous des noms ou des codes différents.
    - **Corrections** — certaines lignes n'ont pas pu être entièrement lues.
    - **Doublons** — le même mouvement figure dans deux fichiers que vous importez ensemble.
    - **Aligner avec la banque** — après l'étape **Vérifiez et importez**, pour un lot de rapports tel que Danske Bank, lorsque les
      chiffres de la banque diffèrent de ceux de LibreFolio.

    Voir **[Étapes qui n'apparaissent qu'en cas de besoin](transactions/import/how-to.md#only-when-needed)**.

La première fois que vous ouvrez l'assistant, un guide vous accompagne à travers les étapes dont vos fichiers ont besoin ; il ne
clique jamais et n'enregistre jamais à votre place (voir **[Premier import guidé](transactions/import/how-to.md#guided-first-import)**).
Pour le déroulé complet, voir **[Comment importer des transactions](transactions/import/how-to.md)** ; pour les
courtiers et formats de fichiers pris en charge, voir **[Importer depuis un courtier](transactions/import/index.md)**.

---

## 📈 5. Retour au tableau de bord

Revenez au **Tableau de bord** : la valeur de votre portefeuille, votre allocation (par type, secteur et zone géographique)
et l'historique de votre performance sont désormais renseignés.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="main" alt="Vue principale du tableau de bord" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔮 6. Et ensuite ?

Maintenant que votre portefeuille est rempli, vous pouvez :

- 🤝 **[Partager votre courtier](brokers/sharing.md)** — Donnez accès à des membres de votre famille ou à des conseillers.
- 💱 **[Configurer les taux de change](fx/index.md)** — Configurez la conversion de devise pour les portefeuilles multidevises.
- ⚙️ **[Personnaliser vos préférences](settings/preferences.md)** — Ajustez votre langue, votre devise par défaut et votre thème. Les administrateurs gèrent aussi les **[paramètres globaux](../admin/settings.md)** à l'échelle du système.
- 🧭 **[Relancer la configuration d'accueil ou les visites guidées](settings/preferences.md#onboarding-and-guides)** — Revenez à l'écran de bienvenue, à la visite rapide ou au guide d'importation à tout moment depuis Paramètres → Préférences.
- 📱 **[Installer LibreFolio comme application](pwa.md)** — Placez-la sur l'écran d'accueil de votre téléphone ou dans sa propre fenêtre de bureau.
