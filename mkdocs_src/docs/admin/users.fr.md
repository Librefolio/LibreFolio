# 👥 Utilisateurs et invitations

Un administrateur s'occupe des comptes de l'instance — qui peut se connecter, qui est administrateur, qui est invité — dans un seul onglet.

**Où :** **Paramètres › Administration › Utilisateurs**. Le même sur chaque installation.

---

## 🧭 Ouvrir l'onglet {: #open-the-tab }

1. Ouvrez **Paramètres** (icône d'engrenage dans la barre latérale), puis **Administration**, puis l'onglet **Utilisateurs**, à côté de **Paramètres Globaux**.

    Seuls les administrateurs voient cet onglet.

L'onglet comporte trois parties : les **places** occupées, en haut ; les **Comptes** ; les **Liens de compte**. Après chaque modification, il recharge ses listes : il affiche toujours ce que contient le serveur.

!!! tip "💻 Sur un serveur sans navigateur"

    La [ligne de commande](cli_tools.md) fait la plupart de ces opérations, sur le serveur, dans le dossier de LibreFolio :

    ```bash
    pipenv run ./dev.py user invite
    pipenv run ./dev.py user reset-link <username>
    pipenv run ./dev.py user deactivate <username>
    pipenv run ./dev.py user activate <username>
    pipenv run ./dev.py user promote <username>
    pipenv run ./dev.py user demote <username>
    pipenv run ./dev.py user reset-onboarding <username>
    ```

    Avec Docker, la commande s'exécute dans le conteneur : « Où exécuter les commandes » dans [Outils en ligne de commande](cli_tools.md).
    La ligne de commande peut aussi dépasser la limite d'utilisateurs. Elle ne peut ni supprimer un compte ni révoquer une invitation.

---

## 📏 Places {: #places }

L'en-tête compte les places occupées : **3 / 10 comptes** avec une limite d'utilisateurs, **3 comptes** sans.

| Occupe une place | |
|---|---|
| Compte actif | ✅ |
| Invitation ouverte | ✅ |
| Compte [en attente de son e-mail](#waiting) | ✅ tant que son lien est actif |
| Administrateur initial [en attente de son lien de configuration](#pending-setup) | ✅ |
| Compte désactivé | ❌ |

**Où la limite est définie :** dans le `.env` de LibreFolio, avec `LIBREFOLIO_MAX_USERS` : « Quand l'instance est pleine » dans [Variables d'environnement](configuration_accounts.md#user-limit).

Lorsque **Inviter** est désactivé :

| Pourquoi | Ce que dit l'onglet | Ce que vous pouvez faire |
|---|---|---|
| 🚫 L'instance est pleine | Une bannière : *L'instance est pleine : aucune nouvelle invitation tant que vous ne désactivez ou ne supprimez pas un compte, ou ne révoquez pas une invitation.* Même un compte désactivé ne peut pas être réactivé, sauf s'il est [en attente de son e-mail](#waiting) avec un lien actif | Désactivez ou supprimez un compte, ou révoquez une invitation |
| 🔒 Le paramètre global **Inscription** est **Fermée** | Il vous indique de le modifier dans les [Paramètres globaux](settings.md), « Qui peut s'inscrire » | Modifiez-le là, ou dans [Qui peut s'inscrire](#registration) ci-dessous |
| 🔒 Le serveur ferme l'inscription avec `LIBREFOLIO_REGISTRATION` | Il nomme la variable | Seule la configuration du serveur peut la rouvrir |

### 🚪 Qui peut s'inscrire {: #registration }

**Où :** le sélecteur **Qui peut s'inscrire**, à côté d'**Inviter**. C'est le paramètre global **Inscription**, le même que dans les [Paramètres globaux](settings.md) (« Qui peut s'inscrire »).

1. Choisissez **Ouverte**, **Sur invitation** ou **Fermée**.

    Le choix est enregistré immédiatement, sans bouton **Enregistrer**, et l'onglet relit le paramètre.

- ⚠️ Seule **Ouverte** vous demande de confirmer d'abord : elle laisse entrer toute personne qui atteint la page de connexion. Si vous annulez, le mode reste tel qu'il était.
- 🔒 Si le serveur définit le mode avec `LIBREFOLIO_REGISTRATION`, le sélecteur est désactivé et l'onglet nomme la variable.

---

## 👤 Comptes {: #accounts }

Une ligne par compte, du plus ancien au plus récent : avatar, nom d'utilisateur avec ses badges, adresse e-mail, date de création. L'avatar est l'image choisie par l'utilisateur dans son [Profil](../user/settings/profile.md) ; sans avatar, la première lettre du nom d'utilisateur dans un cercle.

| Badge | Signification |
|---|---|
| **Vous** | Votre propre compte |
| **Admin** | Un administrateur : il gère l'instance, ses paramètres, ses utilisateurs et ses invitations |
| **Désactivé** | Le compte ne peut pas se connecter et n'occupe aucune place |
| **En attente de configuration** | L'[administrateur initial](configuration_accounts.md#initial-admin), pas encore actif : personne n'a utilisé son lien de configuration, ni configuré le compte autrement. À la place de **Désactivé** : voir [En attente de son lien de configuration](#pending-setup) |
| **En attente de vérification** | Un compte qui n'a pas encore ouvert le lien de vérification envoyé à son adresse, même une fois ce lien expiré. Il ne peut pas se connecter et occupe une place tant que le lien est actif. À la place de **Désactivé** : voir [Comptes en attente de leur e-mail](#waiting) |

**Où se trouvent les actions :** cliquez sur une ligne pour les ouvrir, de nouveau pour les fermer. Votre propre ligne n'en a aucune : elle indique *C'est votre compte. Gérez-le depuis :* avec un lien vers **Profil**, où vous modifiez vos informations ou [supprimez votre compte](../user/settings/profile.md).

### ⚙️ Ce que fait chaque action {: #actions }

| Action | Ce qu'elle fait | Demande confirmation |
|---|---|---|
| **Désactiver** | Le compte ne peut plus se connecter et est déconnecté de tous les appareils. Les courtiers et les transactions restent ; sa place est libérée. Uniquement pour un compte actif | ✅ |
| **Réactiver** | Le compte se connecte de nouveau, avec ses données ; les anciennes sessions ne reviennent pas. Il occupe de nouveau une place, il lui en faut donc une libre, sauf s'il est [en attente de son e-mail](#waiting) avec un lien actif (la place est déjà comptée). Pour un compte désactivé, y compris un compte en attente de son e-mail, mais pas pour l'administrateur initial [en attente de son lien de configuration](#pending-setup) | — |
| **Annuler le lien de configuration** | Le lien de configuration de l'administrateur initial [en attente de sa configuration](#pending-setup) cesse de fonctionner, y compris celui déjà remis ; le compte continue d'attendre un nouveau lien. Uniquement pour ce compte, à la place de **Réactiver** : voir [Annuler son lien de configuration](#cancel-setup) | ✅ |
| **Nommer administrateur** | Le compte gère aussi l'instance : paramètres, utilisateurs et invitations | ✅ |
| **Retirer administrateur** | Le compte est conservé, comme utilisateur standard, et est déconnecté de tous les appareils | ✅ |
| **Lien de réinitialisation** | Un lien pour choisir un nouveau mot de passe : voir [Liens de réinitialisation du mot de passe](#reset-links) | Sa propre boîte de dialogue |
| **Déconnecter partout** | Le compte est déconnecté de tous les appareils et se reconnecte sur chacun d'eux. Il reste actif | ✅ |
| **Relancer les guides** | La prochaine fois que LibreFolio est ouvert, la [Configuration d'accueil](../user/getting-started.md#welcome-setup) et tous les guides recommencent, comme pour un nouveau compte. Les données et les préférences sont conservées | ✅ |
| **Supprimer** | Supprime définitivement le compte : voir [Supprimer un compte](#delete) | Sa propre boîte de dialogue |

### 🔒 Quand une action est indisponible {: #action-off }

LibreFolio désactive les actions que le serveur refuserait et en explique la raison sous les boutons :

| Le panneau indique | Désactivée | Ce que vous pouvez faire |
|---|---|---|
| *C'est le seul administrateur actif : il ne peut être ni désactivé ni rétrogradé.* | **Désactiver**, **Retirer administrateur** | Nommez d'abord un autre compte administrateur |
| *L'instance est pleine : libérez une place pour le réactiver.* | **Réactiver** | Désactivez ou supprimez un autre compte, ou révoquez une invitation ; la commande `user activate` de la ligne de commande dépasse la limite |
| *Un administrateur doit être rétrogradé avant d'être supprimé.* | **Supprimer** | **Retirer administrateur** d'abord, puis **Supprimer** |
| *Il attend sa configuration : il garde son rôle jusque-là.* | **Retirer administrateur**, pour l'administrateur initial [en attente de son lien de configuration](#pending-setup) | [Annulez son lien de configuration](#cancel-setup), ou **Supprimez** le compte, sans **Retirer administrateur** au préalable |
| *Ce compte administrateur s'active par son lien de configuration. Si le lien est perdu, lancez `dev.py user setup-link` sur le serveur.* | Pas de **Réactiver** : **Annuler le lien de configuration** à sa place | Faites utiliser son lien de configuration, ou donnez-en un nouveau : voir [En attente de son lien de configuration](#pending-setup) |

- 👑 L'instance conserve toujours un administrateur actif. Votre propre ligne n'a aucune action : pour renoncer à votre rôle, nommez un autre compte administrateur, puis demandez-lui de vous retirer vos droits.

### ⏳ Comptes en attente de leur e-mail {: #waiting }

Avec **Vérification Email Requise** activée ([Paramètres globaux](settings.md)), un nouveau compte attend que son propriétaire confirme l'adresse au moyen du lien que LibreFolio lui envoie par e-mail. D'ici là :

- 🏷️ sa ligne affiche **En attente de vérification** au lieu de **Désactivé**, même une fois le lien expiré. Survolez le badge pour voir l'indication, ou ouvrez la ligne : sous les boutons, on lit *Son titulaire n'a pas encore ouvert le lien de vérification : en se connectant, il peut s'en faire envoyer un nouveau. Réactiver le laisse entrer tout de suite, sans l'e-mail.* ;
- 📏 il occupe une place tant que son lien est actif : 24 heures après l'envoi du dernier lien ;
- ✅ **Réactiver** le laisse entrer tout de suite : il peut se connecter, et les liens déjà envoyés cessent de fonctionner. Tant que le lien est actif, aucune place libre n'est nécessaire (la sienne est déjà comptée) : cela fonctionne même sur une instance pleine, comme `user activate` sur la [ligne de commande](cli_tools.md), sans avertissement de limite. Une fois le lien expiré, il faut une place libre, comme pour tout compte désactivé ;
- 🗑️ **Supprimer** le supprime, comme tout compte ;
- ⛔ l'onglet ne propose pas **Désactiver** pour un compte qui n'est pas actif. Sur le serveur, `user deactivate`, ou l'API administrateur (`PATCH /api/v1/users/{id}` avec `is_active: false`), le conserve mais met fin à l'attente : ses liens cessent de fonctionner, sa place est libérée, la ligne affiche de nouveau **Désactivé**, et il ne peut se connecter qu'une fois réactivé.

Fonctionnement de la vérification et ses limites : [Vérification de l'adresse e-mail](email_flows.md#verification).

### 👑 En attente de son lien de configuration {: #pending-setup }

Lorsque LibreFolio crée l'administrateur de `LIBREFOLIO_ADMIN_EMAIL` au premier démarrage, le compte attend, pas encore actif, que quelqu'un ouvre son lien de configuration et choisisse le mot de passe, ou le configure autrement (ci-dessous) : [L'administrateur initial](configuration_accounts.md#initial-admin). D'ici là :

- 🏷️ sa ligne affiche **En attente de configuration** au lieu de **Désactivé**, même une fois le lien expiré ou [annulé](#cancel-setup) ;
- 📏 il occupe une place, comme un compte actif ;
- ⛔ le panneau n'a pas de **Réactiver** : personne ne connaît son mot de passe, et l'activer empêcherait aussi le lien de configuration de fonctionner. À sa place, il y a **Annuler le lien de configuration** ([ci-dessous](#cancel-setup)), avec la raison du [tableau ci-dessus](#action-off) ;
- 🔒 **Retirer administrateur** est désactivé, avec sa raison ([tableau ci-dessus](#action-off)). Pour invalider le lien déjà remis, annulez-le ; pour supprimer complètement le compte, supprimez-le ;
- 🗑️ **Supprimer** ne nécessite pas de **Retirer administrateur** au préalable, contrairement à tout autre administrateur ;
- les autres actions sont celles de tout compte désactivé.

Le serveur refuse de l'activer ou de le rétrograder : `PATCH /api/v1/users/{id}` avec `is_active: true`, ou avec `is_superuser: false`, répond `409`, code `PENDING_SETUP`, et ne change rien. Si une telle modification parvient malgré tout au serveur, par exemple depuis une liste chargée auparavant, l'onglet indique *Cet administrateur attend sa configuration : il ne peut être ni réactivé ni rétrogradé ici.* `GET /api/v1/users` le marque avec `pending_setup: true`.

**Un nouveau lien de configuration.** Cette version n'a pas de bouton pour en créer un.

**Où :** sur le serveur, dans le dossier de LibreFolio :

```bash
pipenv run ./dev.py user setup-link
```

La commande affiche le lien : « Un nouveau lien de configuration pour l'administrateur initial » dans [Outils en ligne de commande](cli_tools.md). Une fois utilisé, le compte est actif comme tout autre.

**Configuré autrement, sans son lien.** Le compte cesse aussi d'attendre de cette façon :

| Où | Comment | Résultat |
|---|---|---|
| Sur le serveur | `user activate` | La ligne de commande ne le refuse pas, contrairement à l'onglet, et n'affiche aucun avertissement de limite : le compte occupe déjà sa place. Son mot de passe reste celui que personne ne connaît, jusqu'à ce que `user reset` ou un lien de réinitialisation lui en attribue un |
| Sur le serveur | `user reset` | Un mot de passe est attribué. Le compte reste inactif jusqu'à son activation |
| Dans son panneau, ou sur le serveur | Un [lien de réinitialisation du mot de passe](#reset-links) utilisé : depuis **Lien de réinitialisation**, ou affiché par `user reset-link` | Comme ci-dessus : inactif jusqu'à son activation |

À partir de ce moment, tous les liens de configuration cessent de fonctionner : la page de configuration indique *Ce lien a été révoqué.*, et `user setup-link` ne trouve aucun administrateur en attente. L'onglet l'affiche comme tout autre compte : **Désactivé** tant qu'il n'est pas actif, avec **Réactiver**, et `GET /api/v1/users` le marque avec `pending_setup: false`. Il n'occupe plus aucune place, donc **Réactiver** nécessite une place libre. Un lien de réinitialisation que personne n'utilise le laisse en attente, tout comme [l'annulation de son lien de configuration](#cancel-setup).

### 🚫 Annuler son lien de configuration {: #cancel-setup }

Lorsque le lien est parvenu à la mauvaise personne, ou que quelqu'un d'autre a pu le voir (un e-mail transféré, le journal du serveur).

**Où :** la ligne du compte **En attente de configuration**, bouton **Annuler le lien de configuration**. Sur le serveur, `user deactivate` sur ce compte annule le lien de la même façon.

1. Ouvrez la ligne et cliquez sur **Annuler le lien de configuration**.

    La boîte de dialogue demande *Annuler le lien de configuration de {username} ?* et explique : *Le lien déjà remis cesse de fonctionner. Le compte reste en attente de sa configuration : un nouveau lien s'obtient avec « dev.py user setup-link » sur le serveur.*

2. Cliquez sur **Annuler le lien**.

    Un message confirme : *Le lien de configuration de {username} ne fonctionne plus.*

Ce qui se passe :

- 🔗 tous les liens de configuration du compte cessent de fonctionner, y compris celui déjà remis : quiconque l'ouvre lit *Ce lien a été révoqué.* et ne peut pas configurer le compte ;
- ⏳ le compte continue d'attendre : la ligne affiche encore **En attente de configuration**, il conserve sa place, et il ne peut pas être réactivé ici ;
- 🔁 pour laisser entrer l'administrateur, donnez un nouveau lien avec `user setup-link` sur le serveur (ci-dessus). Redémarrer le serveur avec le même `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` ne donne pas de nouveau lien : l'instance a déjà vu ce jeton. Chaque démarrage journalise un avertissement indiquant que le lien de configuration a été retiré, et demande d'exécuter `dev.py user setup-link` ou de définir un nouveau jeton.

Cas particuliers :

| Cas | Ce qui se passe |
|---|---|
| L'administrateur a terminé la configuration après le chargement de votre liste | Rien à annuler : LibreFolio ne change rien et indique *Cet administrateur a terminé sa configuration entre-temps : rien n'a été modifié.* L'onglet se recharge : la ligne affiche un administrateur actif, avec **Désactiver** à la place de **Annuler le lien de configuration** ; son propriétaire s'est connecté |
| Vous voulez supprimer le compte | **Supprimer** ([Supprimer un compte](#delete)), sans **Retirer administrateur** au préalable. Le compte est supprimé avec ses liens de configuration, la place est libérée et plus personne n'attend de configuration : `user setup-link` ne trouve personne, et les variables `LIBREFOLIO_ADMIN_*` ne créent rien aux démarrages suivants, puisque l'instance possède des comptes |
| Vous voulez le supprimer, mais la configuration a été terminée entre-temps | Rien n'est supprimé : la boîte de dialogue indique *Un administrateur doit être rétrogradé avant d'être supprimé.*, car il s'agit désormais d'un administrateur actif |

### 🔤 Noms d'utilisateur contenant un @ {: #usernames-with-at }

À partir de la version 1.3, un nouveau nom d'utilisateur ne peut pas contenir `@` : à la connexion, LibreFolio lit tout ce qui contient un `@` comme une adresse e-mail. L'inscription, un changement de nom d'utilisateur dans le Profil et `user create` sur la [ligne de commande](cli_tools.md) le refusent ; un `LIBREFOLIO_ADMIN_USERNAME` contenant un `@` arrête le serveur au démarrage (« L'administrateur initial » dans [Variables d'environnement](configuration_accounts.md#initial-admin)). Les espaces, les lettres accentuées et les signes tels que `.`, `_`, `-` ou `+` sont acceptés.

Un compte créé avant la version 1.3 peut en avoir un, par exemple `anna@example.com` :

- 🏷️ le nom d'utilisateur reste tel quel : rien ne le renomme. Son utilisateur peut le changer dans son propre [Profil](../user/settings/profile.md), pour un nom sans `@` ;
- 🔑 le compte se connecte avec sa propre adresse e-mail. Le nom d'utilisateur ne fonctionne à la connexion que tant qu'aucun compte ne l'a comme adresse e-mail : une adresse saisie désigne le compte qui la possède ;
- 📧 aucun autre compte ne peut prendre ce nom d'utilisateur comme adresse e-mail, quelle que soit la casse : l'inscription, le Profil, `user create` et `user set-email` le refusent avec *Cet email est déjà enregistré*. Le compte lui-même peut le prendre comme sa propre adresse.

---

## ✉️ Invitations {: #invitations }

**Où :** **Utilisateurs**, bouton **Inviter**. Sur le serveur : `pipenv run ./dev.py user invite` ([ligne de commande](cli_tools.md)).

1. Cliquez sur **Inviter**.

2. Facultatif : écrivez son adresse dans **E-mail (facultatif)**.

    Ce n'est qu'une indication de la personne à qui l'invitation est destinée : le lien fonctionne pour quiconque l'ouvre. La liste des invitations l'affiche, et le formulaire d'inscription la préremplit, modifiable.

3. Cochez **Administrateur** si le nouveau compte doit gérer l'instance.

4. Cliquez sur **Créer le lien**.

    *Partagez ce lien : il fonctionne une seule fois, pendant 7 jours.* Vérifiez l'[adresse du serveur](#server-address), cliquez sur **Copier** et envoyez le lien vous-même (message ou e-mail), ou laissez LibreFolio l'envoyer : [Envoyer par e-mail](#send-by-email).

5. Cliquez sur **Terminé**.

    L'invitation apparaît dans [Liens de compte](#account-links). La personne ouvre le lien et crée le compte avec le nom d'utilisateur, l'adresse e-mail et le mot de passe de son choix : [Premiers pas](../user/getting-started.md) montre ce qu'elle voit.

- 🔗 Le lien n'est affiché qu'une fois, au moment où vous le créez. S'il est perdu, révoquez l'invitation et créez-en une nouvelle.
- 📏 Une invitation occupe une place à partir du moment où vous la créez et jusqu'à ce qu'elle soit utilisée, révoquée ou expirée ; le compte qu'elle crée prend ensuite cette place.
- 🔤 Une adresse e-mail n'appartient qu'à un seul compte, quelle que soit la casse (`Anna@example.com` est `anna@example.com`), mais seules les lettres A à Z sont comparées ainsi : `Émile@example.com` et `émile@example.com` sont deux adresses différentes.

---

## 🔑 Liens de réinitialisation du mot de passe {: #reset-links }

Lorsque quelqu'un a oublié son mot de passe, envoyez-lui un lien pour qu'il en choisisse lui-même un nouveau. Avec l'e-mail, il peut aussi en demander un depuis la page de connexion : [Mots de passe oubliés](email_flows.md#forgot-password).

**Où :** la ligne du compte, bouton **Lien de réinitialisation**. Sur le serveur : `pipenv run ./dev.py user reset-link <username>` ([ligne de commande](cli_tools.md)).

1. Ouvrez la ligne et cliquez sur **Lien de réinitialisation**.

    La boîte de dialogue explique : *Un lien à usage unique pour définir un nouveau mot de passe, valable 30 minutes. Les liens créés auparavant pour ce compte cessent de fonctionner.*

2. Cliquez sur **Créer le lien**.

3. Vérifiez l'[adresse du serveur](#server-address), cliquez sur **Copier** et envoyez le lien, ou cliquez sur **Envoyer par e-mail** ([Envoyer par e-mail](#send-by-email)). Puis **Terminé**.

    La personne ouvre le lien et choisit le mot de passe : [Premiers pas](../user/getting-started.md).

- ⏱️ Le lien fonctionne une fois, pendant 30 minutes ; seul le lien le plus récent d'un compte est valable.
- 🔒 Il cesse aussi de fonctionner dès que la personne change son mot de passe ou son adresse e-mail, ou que vous exécutez `user reset` ou `user set-email` sur la [ligne de commande](cli_tools.md).
- 🚪 La création du lien ne déconnecte personne. Une fois que la personne définit le nouveau mot de passe, le compte est déconnecté de tous les appareils.
- 🔗 Le lien n'est affiché qu'une fois : s'il est perdu, créez-en un nouveau.

---

## 📋 Liens de compte {: #account-links }

Chaque lien à usage unique de l'instance, et où il en est : invitations, liens de réinitialisation du mot de passe, vérifications de l'e-mail, le lien de configuration du premier administrateur, le changement d'e-mail du titulaire d'une instance gérée. Le lien lui-même n'apparaît jamais ici : il ne s'affiche qu'une fois, à sa création.

**Où :** **Utilisateurs**, la section **Liens de compte**, sous les comptes.

| Colonne | Ce qu'elle affiche |
|---|---|
| **Type** | *Invitation*, *Réinitialisation du mot de passe*, *Vérification de l'e-mail*, *Configuration de l'administrateur* ou *Changement d'e-mail* |
| **Pour** | Le compte sur lequel agit le lien ; pour une invitation, l'adresse qui y est écrite, ou *Toute personne ayant le lien* ; un badge **Admin** lorsque l'invitation crée un administrateur |
| **Créé par** | L'administrateur qui l'a créé ; *—* lorsque LibreFolio ou la personne l'a demandé (une vérification, une réinitialisation depuis la page de connexion) |
| **Créé**, **Expire** | Date et heure |
| **État** | *Ouvert* ; *Utilisé*, avec quand et par qui ; *Expiré* ; *Révoqué*, avec quand |

Les liens ouverts sont dans le premier tableau. Les liens fermés — utilisés, expirés ou révoqués — sont dans **Liens fermés**, replié : cliquez dessus pour l'ouvrir. Chaque tableau trie par colonne (clic sur l'en-tête), filtre par colonne (l'entonnoir dans l'en-tête), masque ou affiche des colonnes (l'œil) et pagine les longues listes.

**Révoquer**, dans le menu (⋮) d'un lien ouvert, le retire après une confirmation : le lien cesse immédiatement de fonctionner, et une invitation libère sa place. Les invitations, les liens de réinitialisation du mot de passe et les vérifications de l'e-mail se révoquent ici. Le lien de configuration de l'administrateur en attente s'annule depuis son compte ([Annuler son lien de configuration](#cancel-setup)) ; le changement d'e-mail du titulaire suit l'adresse fixée par l'hébergeur, et ne se révoque pas ici.

---

## 🌐 L'adresse du serveur d'un lien {: #server-address }

Les liens d'invitation et de réinitialisation du mot de passe s'affichent dans le même panneau :

- **Adresse du serveur** : le début du lien. Renseignée avec `LIBREFOLIO_PUBLIC_URL` lorsque le serveur la définit, sinon avec l'adresse qu'utilise actuellement votre navigateur. *Modifiez-la si vos utilisateurs accèdent à LibreFolio par une autre adresse* : par exemple, vous êtes chez vous sur `http://192.168.1.10:6040`, vos utilisateurs passent par `https://librefolio.example.com`.
- **Lien** : l'adresse du serveur suivie du chemin du lien. **Copier** le place dans le presse-papiers ; si le navigateur refuse, le lien est sélectionné pour que vous puissiez le copier à la main. *Valable jusqu'au …* indique son expiration.

Lorsque vous modifiez l'adresse, une demi-seconde après que vous avez cessé de taper, le navigateur vérifie que **cette** instance répond à cette adresse, et pas n'importe quel serveur : il charge `<address>/api/v1/auth/address-probe.png?nonce=…`. L'adresse renseignée elle-même n'est pas vérifiée.

| Message | Ce que cela signifie |
|---|---|
| *Vérification que ce LibreFolio répond à cette adresse…* | La vérification est en cours |
| *Cette instance répond à cette adresse.* | Le lien atteint ce LibreFolio |
| *Quelque chose répond à cette adresse, mais pas cette instance : vérifiez-la avant de partager.* | Un autre LibreFolio y répond : ce n'est probablement pas l'adresse voulue |
| *Cette adresse n'a pas pu être vérifiée depuis ce navigateur : vous pouvez quand même partager le lien.* | Le navigateur n'a pas chargé l'image. Rien n'y répond (adresse erronée ou fermée, ou aucune réponse en 8 secondes) ; une page `https://` vérifie une adresse `http://`, ce que le navigateur bloque ; une page sur une adresse publique vérifie une adresse locale, que certains navigateurs bloquent ou n'autorisent qu'après vous avoir demandé la permission ; une instance bloquée ne fournit pas l'image ; ou un LibreFolio plus ancien répond, ce qui ne peut pas être vérifié |
| *Saisissez une adresse commençant par http:// ou https://, sans ? ni #.* | Ce n'est pas une adresse : **Copier** reste désactivé jusqu'à correction |

Quel que soit le résultat, sauf pour une adresse qui n'en est pas une, vous pouvez copier le lien : la vérification n'est qu'un avis. De retour sur l'adresse renseignée, le message disparaît. Fonctionnement : [Sonde d'adresse](../developer/architecture/security.md#address-probe), pour les développeurs.

!!! tip "🌐 Définissez l'adresse une fois"

    **Où :** dans le `.env` de LibreFolio, l'adresse qu'ouvrent vos utilisateurs :

    ```bash
    LIBREFOLIO_PUBLIC_URL=https://librefolio.example.com
    ```

    Le panneau part de là : « Comptes et inscriptions » dans [Variables d'environnement](configuration_accounts.md#accounts). La [ligne de commande](cli_tools.md) la place aussi devant les liens qu'elle affiche.

---

## 📧 Envoyer par e-mail {: #send-by-email }

Condition : e-mail **Prêt** et `LIBREFOLIO_PUBLIC_URL` défini sur une adresse que LibreFolio peut utiliser ([E-mails contenant un lien](email_flows.md#public-url)). Alors les deux boîtes de dialogue de lien proposent **Envoyer par e-mail** sous le lien. Sans e-mail, le bouton n'est pas présent : copiez le lien comme auparavant.

| | Invitation | Lien de réinitialisation du mot de passe |
|---|---|---|
| **Destinataire** | **Envoyer à** est prérempli avec l'adresse indiquée dans l'invitation ; vous pouvez la modifier. Vide, l'e-mail est envoyé à l'adresse de l'invitation ; s'il n'y en a pas, la boîte de dialogue en demande une | Aucun champ : il est envoyé à l'adresse du compte, et uniquement tant que le compte est actif |
| **Langue** | **Langue de l'e-mail** : la **Langue par Défaut** de l'instance, sauf si vous en choisissez une autre | La langue du compte |

- 🌐 **Le lien contenu dans l'e-mail commence par `LIBREFOLIO_PUBLIC_URL`**, quelle que soit l'**Adresse du serveur** affichée ci-dessus : la boîte de dialogue le précise.
- 📨 **Le résultat** s'affiche dans la boîte de dialogue : *Envoyé à …* avec l'adresse et la langue de l'e-mail, et un rappel : s'il n'arrive pas, le destinataire doit aussi vérifier les spams ; ou la raison pour laquelle l'e-mail n'est pas parti ([Erreurs d'envoi](email_troubleshooting.md#sending-errors)).

Règles et limites : [Liens envoyés par un administrateur](email_flows.md#admin-links).

---

## 🗑️ Supprimer un compte {: #delete }

**Où :** la ligne du compte, bouton **Supprimer**. Pour un administrateur, **Retirer administrateur** d'abord ; pas pour l'administrateur initial [en attente de son lien de configuration](#cancel-setup), que vous supprimez directement. La ligne de commande ne supprime pas de comptes.

La suppression suit la même règle que la suppression de son propre compte ([Profil](../user/settings/profile.md)) :

1. Pour un compte actif, la boîte de dialogue propose d'abord **Désactiver** à la place.

    Cela conserve tous les courtiers et toutes les transactions et peut être annulé ; le compte ne peut simplement plus se connecter.

2. La boîte de dialogue montre ce que la suppression emporterait :

    - **Supprimés, avec toutes leurs transactions et fichiers** : les courtiers dont le compte est le seul propriétaire, chacun avec son nombre de transactions. Ils sont aussi supprimés pour les utilisateurs avec lesquels il les partageait. S'il n'y en a aucun : *Aucun broker n'est supprimé* ;
    - **Brokers partagés qui restent (seul l'accès disparaît)** : les autres courtiers que le compte peut ouvrir, avec son rôle sur chacun ;
    - un avertissement lorsque des transactions sur d'autres courtiers sont les moitiés de transferts avec les courtiers supprimés : elles restent, sans leur autre moitié. Un transfert reçu devient un ajustement à son coût ; un transfert envoyé à l'un de ces courtiers devient un ajustement qui sort les actifs du courtier qui les a envoyés, sans valeur : leur coût compte comme une perte réalisée sur ce courtier ([Modifier ou supprimer un courtier](../user/brokers/index.md)).

3. Saisissez le nom d'utilisateur du compte, puis cliquez sur **Supprimer Définitivement**.

    Le compte, ses paramètres et les courtiers indiqués sont supprimés immédiatement.

!!! danger "La suppression d'un compte est irréversible"

    Quiconque est connecté avec ce compte est déconnecté à sa prochaine requête. Si la suppression échoue pour une raison technique, rien n'est supprimé. Si la boîte de dialogue ne parvient pas à charger ce que la suppression emporterait, elle ne vous laisse pas supprimer : fermez-la et réessayez.

Fonctionnement de la règle : [Suppression d'un compte](../developer/architecture/access_control.md#admin-account-deletion), pour les développeurs.

---

## 🔗 Voir aussi

- 📝 **[Variables d'environnement](configuration_accounts.md#accounts)** — « Comptes et inscriptions » : `LIBREFOLIO_MAX_USERS`, `LIBREFOLIO_REGISTRATION` et `LIBREFOLIO_PUBLIC_URL`
- ⚙️ **[Paramètres globaux](settings.md)** — « Qui peut s'inscrire » : le paramètre **Inscription**
- 🛠️ **[Outils en ligne de commande](cli_tools.md)** — « Gérer les utilisateurs » : la plupart de ces tâches, sans navigateur
- 👤 **[Profil](../user/settings/profile.md)** — Votre propre compte et comment le supprimer
- 🧑‍💻 Pour les développeurs : **[API administrateur](../developer/architecture/access_control.md#admin-user-api)** et **[Composants des paramètres](../developer/frontend/components/features/settings.md#userstab)**
