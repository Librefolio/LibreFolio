# 👤 Profil

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="profile" alt="Profil">
</div>

L'onglet **Profil** gère votre **identité** dans LibreFolio — qui vous êtes et comment vous vous connectez. Les choix d'affichage (langue, devise, thème) se trouvent quant à eux dans **[Préférences](preferences.md)** ; les options propres à l'instance se trouvent dans **[Paramètres › Administration › Paramètres globaux](../../admin/settings.md)**.

## 🔒 Verrouillage des modifications

L'onglet s'ouvre **verrouillé** : les champs sont en lecture seule jusqu'à ce que vous cliquiez sur le ✏️ **bouton crayon** dans l'en-tête. Cela évite les modifications accidentelles. Si vous reverrouillez l'onglet alors que des modifications ne sont pas enregistrées, une boîte de dialogue de confirmation vous demande si vous souhaitez les abandonner.

Pendant qu'il est déverrouillé, chaque champ modifié affiche ses propres boutons **enregistrer** / **annuler**, et l'en-tête propose **tout enregistrer** et **tout annuler** pour les actions groupées.

## 🖼️ Avatar

Survolez votre avatar (tant que l'onglet est déverrouillé) et cliquez sur l'icône d'appareil photo 📷 en superposition pour ouvrir le sélecteur d'image : choisissez une image existante dans la [bibliothèque de fichiers](../files/index.md), une image partagée ou l'une des vôtres, ou téléversez-en une nouvelle. Les téléversements passent par l'**[outil de recadrage d'image](../misc/image-crop.md)** avec le préréglage *avatar* (recadrage carré, aperçu circulaire).

L'avatar est enregistré immédiatement et est utilisé dans toute l'application, partout où votre identité apparaît — barre latérale, partage de courtiers et listes de collaborateurs. Les administrateurs le voient également dans **[Paramètres › Administration › Utilisateurs](../../admin/users.md#accounts)**, à côté de votre nom d'utilisateur.

Comme les autres utilisateurs voient votre avatar, son image est **partagée** : une image que vous téléversez ici est stockée comme partagée, et l'une de vos images personnelles devient partagée lorsque vous la choisissez, avec une notification (voir [Partagée ou personnelle](../files/index.md#visibility)).

!!! note "Également définissable depuis la page de bienvenue"

    Les comptes tout nouveaux peuvent choisir la même image une fois, lors de la **[configuration
    d'accueil à la première connexion](../getting-started.md#welcome-setup)** — c'est le
    même sélecteur, auquel on accède simplement depuis un autre écran. Si vous sautez cette étape, vos initiales
    servent d'avatar ; vous pouvez toujours ajouter ou modifier une image plus tard depuis cet onglet.

## ✏️ Nom d'utilisateur, e-mail, date de création du compte

- Le **nom d'utilisateur** et l'**e-mail** sont modifiables (onglet déverrouillé requis). Les modifications s'appliquent immédiatement à vos identifiants de connexion. Changer l'e-mail demande aussi votre mot de passe actuel : voir [Changer votre adresse e-mail](#email-change) ci-dessous.
- La **date de création du compte** est un champ en lecture seule indiquant votre date d'inscription.

### 📧 Changer votre adresse e-mail {: #email-change }

Dès que l'adresse e-mail saisie dans le champ diffère de votre adresse actuelle, un champ **Mot de passe actuel** apparaît juste sous le champ de l'e-mail, avec un rappel : *Pour changer votre adresse e-mail, saisissez votre mot de passe actuel. Vos autres appareils seront déconnectés.* Le bouton d'enregistrement de l'e-mail, ainsi que **tout enregistrer**, restent désactivés tant que vous ne l'avez pas saisi.

- **Mot de passe erroné** : l'onglet indique *Le mot de passe actuel est incorrect*. Votre nouvel e-mail reste dans son champ et seul le mot de passe est vidé : saisissez-le à nouveau, puis enregistrez.
- **Mot de passe erroné, encore et encore** : les mots de passe erronés saisis ici et les connexions échouées avec votre nom d'utilisateur sont comptés ensemble. Après 10 échecs en 15 minutes, la modification est refusée même avec le bon mot de passe, tout comme la connexion avec votre nom d'utilisateur, pendant 15 minutes au maximum. L'onglet indique alors *Trop de mots de passe erronés : attendez quelques minutes et réessayez.*, et conserve à la fois votre nouvel e-mail et le mot de passe que vous avez saisi : enregistrez à nouveau une fois l'attente terminée.
- **E-mail refusé pour une autre raison**, par exemple parce qu'un autre compte l'utilise déjà, comme adresse e-mail ou comme nom d'utilisateur, même avec une casse différente : l'onglet affiche la raison, et votre adresse e-mail actuelle revient.
- **E-mail enregistré** : vous restez connecté sur cet appareil. Tous les autres appareils connectés à votre compte sont déconnectés et doivent se reconnecter. Tout lien de réinitialisation de mot de passe qui vous a été envoyé avant la modification cesse de fonctionner, même s'il attend encore dans votre ancienne boîte aux lettres.
- **Un e-mail à chaque adresse** : lorsque votre instance peut envoyer des e-mails, LibreFolio écrit à l'adresse que vous aviez auparavant pour vous informer du changement, et à votre nouvelle adresse pour confirmer qu'elle est désormais celle de votre compte. Le premier ne révèle rien de la nouvelle adresse et indique quoi faire si vous n'êtes pas à l'origine du changement ; le second ne révèle rien de l'ancienne. Si l'un d'eux n'arrive pas, vérifiez aussi les spams.
- **Seule la casse a changé**, par exemple `Anna@example.com` pour `anna@example.com` : il s'agit toujours de votre adresse, l'onglet ne demande donc aucun mot de passe, vous l'enregistrez directement, aucun appareil n'est déconnecté et elle reste vérifiée. Seules les lettres A à Z sont mises en correspondance de cette manière ; les lettres accentuées ne le sont pas : `Émile@example.com` et `émile@example.com` sont deux adresses différentes.

Changer uniquement votre nom d'utilisateur ne demande pas de mot de passe et ne déconnecte aucun appareil. Le nouveau nom d'utilisateur ne peut pas contenir `@`, car lorsque vous vous connectez, LibreFolio interprète tout ce qui contient un `@` comme une adresse e-mail : l'onglet indique *Le nom d'utilisateur ne peut pas contenir @ : pour vous connecter, vous pouvez toujours utiliser votre adresse e-mail.*, et votre nom d'utilisateur actuel revient. Les espaces, les lettres accentuées et les signes tels que `.`, `_`, `-` ou `+` sont acceptés.

!!! info "Pourquoi votre mot de passe"

    Votre adresse e-mail est le moyen de récupérer votre compte : un lien de réinitialisation de mot de passe qui y est envoyé permet à quiconque le lit de choisir un nouveau mot de passe. Sans cette vérification, quelqu'un qui aurait brièvement accès à votre session ouverte (un ordinateur laissé déverrouillé, un cookie de session volé) pourrait mettre sa propre adresse sur votre compte et conserver le compte définitivement. Sans votre mot de passe, il ne peut pas changer l'adresse.

## 🔐 Sécurité

### 🔑 Changer le mot de passe

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="password-modal" alt="Changer le mot de passe">
</div>

Le bouton **Changer le mot de passe** (toujours disponible, aucun déverrouillage nécessaire) ouvre une modale qui exige :

1. Votre **mot de passe actuel** (pour vérification)
2. Un **nouveau mot de passe** respectant toutes les règles de la liste sous le champ : au moins 8 caractères, une lettre majuscule, une lettre minuscule, un chiffre et un caractère spécial — et il doit différer du mot de passe actuel
3. La **confirmation** du nouveau mot de passe

La liste suit ce que vous saisissez, et le serveur applique exactement les mêmes règles. Les lettres et les chiffres de n'importe quel alphabet comptent : `É` est une lettre majuscule, `é` une minuscule. Un caractère spécial est tout ce qui n'est ni une lettre, ni un chiffre, ni un espace, comme `!`, `_` ou `€`. Si le serveur refuse malgré tout le nouveau mot de passe, la modale indique *Le mot de passe ne répond pas aux exigences de sécurité*, et la liste montre les règles manquantes.

Les mots de passe actuels erronés et les connexions échouées avec votre nom d'utilisateur sont comptés ensemble, comme pour [l'adresse e-mail](#email-change) : après 10 échecs en 15 minutes, la modification est refusée même avec le bon mot de passe actuel, tout comme la connexion avec votre nom d'utilisateur, pendant 15 minutes au maximum. La modale indique alors *Trop de mots de passe erronés : attendez quelques minutes et réessayez.*, et conserve ce que vous avez saisi dans ses trois champs : réessayez une fois l'attente terminée.

Après confirmation, votre session reste active — vous n'avez pas besoin de vous reconnecter. Tous les autres appareils connectés à votre compte sont déconnectés. Tout lien de réinitialisation de mot de passe qui vous a été envoyé avant la modification cesse de fonctionner.

### 🗑️ Supprimer le compte

Le bouton **Supprimer le compte** supprime définitivement votre compte et ses paramètres. Sa boîte de dialogue montre d'abord ce que votre suppression emporterait avec elle, puis vous demande de saisir votre **nom d'utilisateur**. **Supprimer définitivement** agit immédiatement : vous êtes déconnecté et renvoyé à la page de connexion.

Vos courtiers suivent la même règle que pour [quitter un courtier partagé](../brokers/sharing.md), et la boîte de dialogue les liste avant votre confirmation :

- **Supprimés, avec toutes leurs transactions et fichiers** : les courtiers dont vous êtes le **seul propriétaire**, chacun avec son nombre de transactions. Leurs fichiers de rapport importés sont supprimés aussi, et ils disparaissent également pour les utilisateurs avec lesquels vous les avez partagés. S'il n'y en a aucun, la boîte de dialogue indique *Aucun courtier n'est supprimé* ;
- **Courtiers partagés qui restent (seul l'accès disparaît)** : tous les autres courtiers que vous pouvez ouvrir, avec votre rôle sur chacun. Ils restent pour leurs autres utilisateurs : seul votre accès est supprimé ;
- un avertissement lorsque des transactions sur d'autres courtiers constituent l'une des moitiés de transferts avec les courtiers qui disparaissent : elles restent, sans leur autre moitié. Un transfert reçu devient un ajustement à son coût, et un transfert envoyé vers l'un de ces courtiers devient un ajustement qui retire les actifs du courtier qui les a envoyés, sans valeur : leur coût y est comptabilisé comme une moins-value réalisée (voir [Modifier ou supprimer un courtier](../brokers/index.md)).

Si la boîte de dialogue ne parvient pas à charger cette liste, elle ne vous laisse pas supprimer : fermez-la et réessayez. Si la suppression échoue pour une raison technique, rien n'est supprimé.

!!! warning "Irréversible"

    La suppression de votre compte ne peut pas être annulée. Si vous êtes le **seul administrateur actif** de l'instance, la suppression est refusée : commencez par donner le rôle d'administrateur à un autre compte, depuis l'onglet [Utilisateurs](../../admin/users.md).

---

## 🔗 Voir aussi

- 🎛️ **[Préférences utilisateur](preferences.md)** — Langue, devise de base et thème
- ⚙️ **[Vue d'ensemble des paramètres](index.md)** — Résumé des paramètres généraux
- ℹ️ **[À propos](about.md)** — Informations sur la version, plugins et journal des modifications
- 🛡️ **[Paramètres globaux](../../admin/settings.md)** — Options propres à l'instance (admin)
