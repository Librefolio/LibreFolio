# 👥 Utilisateurs et invitations

L’onglet **Utilisateurs** de **Paramètres › Administration** est l’endroit où un administrateur s’occupe des
comptes de l’instance : qui peut se connecter, qui est administrateur et qui est invité à rejoindre. Il
fonctionne de la même manière sur chaque installation.

---

## 🧭 Ouvrir l’onglet {: #open-the-tab }

Ouvrez **Paramètres** (icône d’engrenage dans la barre latérale), puis **Administration** et son onglet **Utilisateurs**, à côté de
**Paramètres globaux**. Seuls les administrateurs disposent de cet onglet : tous les autres ne le voient pas.

L’onglet comporte trois parties : les places occupées, en haut ; les **Comptes** ; les **Invitations en cours**.
Après chaque modification, l’onglet recharge ses listes, de sorte qu’il affiche toujours ce que contient le serveur.

!!! tip "💻 Sur un serveur sans navigateur"

    La [ligne de commande](cli_tools.md) fait aussi la plupart de ces opérations : `user invite`, `user reset-link`,
    `user deactivate` et `user activate`, `user promote` et `user demote`, `user reset-onboarding`.
    Elle peut également dépasser la limite d’utilisateurs. Elle ne peut ni supprimer un compte ni révoquer une invitation.

---

## 📏 Places {: #places }

L’en-tête compte les places occupées : **3 / 10 comptes** lorsque l’instance a une limite d’utilisateurs,
**3 comptes** lorsqu’elle n’en a pas. Les comptes actifs et les invitations en cours occupent une place, tout comme un
compte [en attente de son e-mail](#waiting) tant que son lien est actif, et tout comme un
administrateur initial encore [en attente de son lien de configuration](#pending-setup) ; les comptes désactivés
n’en occupent pas. La limite est définie sur le serveur avec `LIBREFOLIO_MAX_USERS` : voir « Quand l’instance est pleine » dans
[Variables d’environnement](configuration_accounts.md#user-limit).

- 🚫 Lorsque l’instance est pleine, une bannière indique *L’instance est pleine : aucune nouvelle invitation tant
  que vous n’avez pas désactivé ou supprimé un compte, ou révoqué une invitation.* **Inviter** est désactivé, et un compte désactivé ne peut pas être réactivé tant
  qu’une place n’est pas libre, sauf s’il est [en attente de son e-mail](#waiting) avec un lien actif.
- 🔒 **Inviter** est également désactivé tant que l’inscription est fermée. Si le paramètre global **Inscription** est
  sur **Fermé**, l’onglet vous indique de le modifier à cet endroit ([Paramètres globaux](settings.md), « Qui peut
  s’inscrire »). Si le serveur le ferme avec `LIBREFOLIO_REGISTRATION`, l’onglet nomme la variable : seule la
  configuration du serveur peut le rouvrir.

### 🚪 Qui peut s’inscrire {: #registration }

**Qui peut s’inscrire**, à côté d’**Inviter**, correspond au paramètre global **Inscription**, ici comme dans
[Paramètres globaux](settings.md) (« Qui peut s’inscrire ») : **Ouvert**, **Sur invitation** ou **Fermé**. Un choix est
enregistré immédiatement, sans bouton **Enregistrer**, et l’onglet relit le paramètre. Seul **Ouvert** vous demande de
confirmer d’abord, car il laisse entrer toute personne qui atteint la page de connexion ; si vous annulez, le mode reste tel qu’il était.
Si le serveur définit le mode avec `LIBREFOLIO_REGISTRATION`, le sélecteur est désactivé et l’onglet nomme la
variable.

---

## 👤 Comptes {: #accounts }

Une ligne par compte, du plus ancien au plus récent : l’avatar du compte, le nom d’utilisateur avec ses badges, puis
l’adresse e-mail et la date de création. L’avatar est l’image choisie pour le compte par son utilisateur (voir
[Profil](../user/settings/profile.md)) ; un compte qui n’en a pas affiche la première lettre de son
nom d’utilisateur dans un cercle uni.

| Badge | Signification |
|---|---|
| **Vous** | Votre propre compte |
| **Admin** | Un administrateur : il gère l’instance, ses paramètres, ses utilisateurs et ses invitations |
| **Désactivé** | Le compte ne peut pas se connecter et n’occupe aucune place. Un compte [en attente de son e-mail](#waiting) possède son propre badge, ci-dessous |
| **En attente de configuration** | L’[administrateur initial](configuration_accounts.md#initial-admin), pas encore actif : personne n’a utilisé son lien de configuration, ni configuré le compte autrement. Affiché à la place de **Désactivé** : voir [En attente de son lien de configuration](#pending-setup) |
| **En attente de vérification** | Un compte qui n’a pas encore ouvert le lien de vérification que LibreFolio a envoyé à son adresse par e-mail, même une fois ce lien expiré. Il ne peut pas se connecter et occupe une place tant que son lien est actif. Affiché à la place de **Désactivé** : voir [Comptes en attente de leur e-mail](#waiting) |

Cliquez sur une ligne pour ouvrir ses actions, et de nouveau pour les fermer. Votre propre ligne n’en a aucune : elle indique *Ceci est
votre compte. Gérez-le depuis :* avec un lien vers **Profil**, l’onglet où vous modifiez vos informations ou
[supprimez votre compte](../user/settings/profile.md).

### ⚙️ Ce que fait chaque action {: #actions }

| Action | Ce qu’elle fait | Demande confirmation |
|---|---|---|
| **Désactiver** | Le compte ne peut plus se connecter et est déconnecté de tous les appareils. Ses courtiers et transactions sont conservés, et sa place est libérée. Affichée pour un compte actif | ✅ |
| **Réactiver** | Le compte peut de nouveau se connecter, avec ses données telles qu’elles étaient ; ses anciennes sessions ne reviennent pas. Il occupe de nouveau une place, il lui faut donc une place libre, sauf si le compte est [en attente de son e-mail](#waiting) avec un lien actif : sa place est déjà comptée. Affichée pour un compte désactivé, y compris un compte en attente de son e-mail, mais pas pour l’administrateur initial [en attente de son lien de configuration](#pending-setup) | — |
| **Annuler le lien de configuration** | Le lien de configuration de l’administrateur initial [en attente de sa configuration](#pending-setup) cesse de fonctionner, y compris celui déjà remis ; le compte continue d’attendre un nouveau lien. Affichée pour ce compte uniquement, à la place de **Réactiver** : voir [Annuler son lien de configuration](#cancel-setup) | ✅ |
| **Nommer administrateur** | Le compte gère aussi l’instance : paramètres, utilisateurs et invitations | ✅ |
| **Retirer le rôle d’administrateur** | Le compte est conservé, comme utilisateur standard, et est déconnecté de tous les appareils | ✅ |
| **Lien de réinitialisation du mot de passe** | Un lien pour choisir un nouveau mot de passe : voir [Liens de réinitialisation du mot de passe](#reset-links) | Sa propre boîte de dialogue |
| **Déconnecter de tous les appareils** | Le compte est déconnecté de tous les appareils : son utilisateur se reconnecte sur chacun d’eux. Le compte reste actif | ✅ |
| **Redémarrer les guides** | La prochaine fois que son utilisateur ouvre LibreFolio, la [Configuration d’accueil](../user/getting-started.md#welcome-setup) et tous les guides recommencent, comme pour un nouveau compte. Ses données et préférences sont conservées | ✅ |
| **Supprimer** | Supprime définitivement le compte : voir [Supprimer un compte](#delete) | Sa propre boîte de dialogue |

### 🔒 Quand une action est indisponible {: #action-off }

LibreFolio désactive les actions qu’il sait que le serveur refuserait, et en explique la raison sous les boutons :

| Le panneau indique | Désactivée | Ce que vous pouvez faire |
|---|---|---|
| *C’est le seul administrateur actif : il ne peut être ni désactivé ni rétrogradé.* | **Désactiver**, **Retirer le rôle d’administrateur** | Nommez d’abord un autre compte administrateur |
| *L’instance est pleine : libérez une place pour le réactiver.* | **Réactiver** | Désactivez ou supprimez un autre compte, ou révoquez une invitation ; la commande `user activate` de la ligne de commande dépasse la limite |
| *Un administrateur doit être rétrogradé avant de pouvoir être supprimé.* | **Supprimer** | **Retirer le rôle d’administrateur** d’abord, puis **Supprimer** |
| *Il attend sa configuration : il conserve son rôle jusque-là.* | **Retirer le rôle d’administrateur**, pour l’administrateur initial [en attente de son lien de configuration](#pending-setup) | [Annulez son lien de configuration](#cancel-setup), ou **Supprimez**-le : il n’a pas besoin de **Retirer le rôle d’administrateur** au préalable |
| *Ce compte administrateur s’active au moyen de son lien de configuration. Si le lien est perdu, exécutez `dev.py user setup-link` sur le serveur.* | Pas de **Réactiver** : **Annuler le lien de configuration** à sa place | Faites en sorte que son lien de configuration soit utilisé, ou donnez-en un nouveau : voir [En attente de son lien de configuration](#pending-setup) |

- 👑 L’instance conserve toujours un administrateur actif. Votre propre ligne n’a aucune action ; pour renoncer à votre rôle :
  nommez un autre compte administrateur, puis demandez-lui de vous retirer vos droits.

### ⏳ Comptes en attente de leur e-mail {: #waiting }

Lorsque **Exiger la vérification de l’e-mail** est activé ([Paramètres globaux](settings.md)), un nouveau compte attend que
son propriétaire confirme l’adresse au moyen du lien que LibreFolio lui envoie par e-mail. D’ici là :

- sa ligne affiche **En attente de vérification** au lieu de **Désactivé**, même une fois son lien expiré.
  Survolez le badge pour voir l’indication, ou ouvrez la ligne, où il est indiqué sous les boutons : *Son
  propriétaire n’a pas encore ouvert le lien de vérification : la connexion propose d’en envoyer un nouveau. Réactiver
  laisse entrer le compte immédiatement, sans l’e-mail.* Un compte désactivé pendant qu’il attend (voir le
  dernier point) cesse d’attendre, et sa ligne affiche de nouveau **Désactivé** ;
- il occupe une place tant que son lien est actif, c’est-à-dire pendant 24 heures après l’envoi du dernier lien ;
- **Réactiver** le laisse entrer immédiatement : il peut se connecter, et les liens déjà envoyés cessent de fonctionner. Tant que
  son lien est actif, cela n’occupe pas de place supplémentaire, puisque sa place est déjà comptée : **Réactiver**
  fonctionne même sur une instance pleine, tout comme `user activate` sur la
  [ligne de commande](cli_tools.md), sans avertissement de limite. Une fois le lien expiré, sa réactivation
  nécessite une place libre, comme pour tout compte désactivé ;
- **Supprimer** le supprime, comme tout compte. Cet onglet ne propose pas de **Désactiver** pour un compte qui
  n’est pas actif ; `user deactivate` sur la ligne de commande, ou l’API administrateur
  (`PATCH /api/v1/users/{id}` avec `is_active: false`), le conserve mais met fin à l’attente : ses liens cessent de
  fonctionner, sa place est libérée, et il ne peut se connecter qu’une fois réactivé.

Fonctionnement de la vérification et ses limites : [Vérification de l’e-mail](email_flows.md#verification).

### 👑 En attente de son lien de configuration {: #pending-setup }

Lorsque LibreFolio crée l’administrateur de `LIBREFOLIO_ADMIN_EMAIL` à son premier démarrage, le
compte attend, pas encore actif, que quelqu’un ouvre son lien de configuration et choisisse le mot de passe, ou le configure
d’une autre manière (ci-dessous) : voir
[L’administrateur initial](configuration_accounts.md#initial-admin). D’ici là :

- sa ligne affiche **En attente de configuration** au lieu de **Désactivé**, même une fois son lien expiré ou
  [annulé](#cancel-setup) ;
- il occupe une place, comme un compte actif ;
- son panneau n’a pas de **Réactiver** : personne ne connaît son mot de passe, et l’activer empêcherait aussi son
  lien de configuration de fonctionner. **Annuler le lien de configuration** prend sa place ([ci-dessous](#cancel-setup)). Sous
  les boutons, le panneau indique : *Ce compte administrateur s’active au moyen de son lien de configuration. Si
  le lien est perdu, exécutez `dev.py user setup-link` sur le serveur.* ;
- **Retirer le rôle d’administrateur** est désactivé, avec la raison *Il attend sa configuration : il conserve son rôle jusque-là.*
  Pour invalider le lien déjà remis, annulez-le ; pour supprimer complètement le compte, supprimez-le ;
- **Supprimer** ne nécessite pas de **Retirer le rôle d’administrateur** au préalable, contrairement à tout autre administrateur ;
- les autres actions sont celles de tout compte désactivé.

Le serveur refuse de l’activer ou de lui retirer ses droits d’administrateur : `PATCH /api/v1/users/{id}`
avec `is_active: true`, ou avec `is_superuser: false`, répond `409`, avec le code `PENDING_SETUP`,
et ne change rien. Si une telle modification parvient malgré tout au serveur, par exemple depuis une liste chargée
auparavant, l’onglet explique pourquoi au lieu d’afficher une erreur générique : *Cet administrateur attend sa configuration : il ne peut
être ni réactivé ni rétrogradé ici.* `GET /api/v1/users` marque le compte avec
`pending_setup: true`.

Cette version n’a pas de bouton pour créer un nouveau lien de configuration : sur le serveur, `user setup-link` en affiche un (voir
« Un nouveau lien de configuration pour l’administrateur initial » dans [Outils en ligne de commande](cli_tools.md)). Une fois le lien utilisé, le compte est
actif, comme tout autre.

Le compte cesse également d’attendre lorsqu’il est configuré autrement, sans son lien :

- **activé sur le serveur** avec `user activate` : la ligne de commande ne le refuse pas, contrairement à
  cet onglet, et n’affiche aucun avertissement de limite, puisque le compte occupe déjà sa place. Son mot de passe
  reste celui que personne ne connaît, jusqu’à ce que `user reset` ou un lien de réinitialisation lui en attribue un ;
- **doté d’un mot de passe**, avec `user reset` sur le serveur, ou avec un
  [lien de réinitialisation du mot de passe](#reset-links) une fois celui-ci utilisé : celui que vous créez avec
  **Lien de réinitialisation du mot de passe** dans son panneau, ou celui qu’affiche `user reset-link`. Le compte reste inactif
  jusqu’à son activation.

À partir de ce moment, tous les liens de configuration qu’il avait cessent de fonctionner : la page de configuration indique *Ce lien a été
retiré.*, et `user setup-link` ne trouve aucun administrateur en attente. L’onglet l’affiche comme tout autre
compte : **Désactivé** tant qu’il n’est pas actif, avec **Réactiver**, et `GET /api/v1/users` le marque
`pending_setup: false`. Comme tout compte désactivé, il n’occupe alors aucune place ; **Réactiver**
nécessite donc une place libre. Un lien de réinitialisation que personne n’utilise le laisse en attente, tout comme
[l’annulation de son lien de configuration](#cancel-setup).

### 🚫 Annuler son lien de configuration {: #cancel-setup }

Annulez le lien de configuration de l’administrateur initial lorsqu’il est parvenu à la mauvaise personne, ou lorsque quelqu’un
d’autre a pu le voir, par exemple dans un e-mail transféré ou dans le journal du serveur :

1. Ouvrez la ligne du compte **En attente de configuration** et cliquez sur **Annuler le lien de configuration**.
2. La boîte de dialogue demande *Annuler le lien de configuration de {username} ?* et explique : *Le lien déjà remis
   cesse de fonctionner. Le compte continue d’attendre sa configuration : un nouveau lien s’obtient avec « dev.py user
   setup-link » sur le serveur.*
3. Cliquez sur **Annuler le lien**. Un message confirme : *Le lien de configuration de {username} ne fonctionne plus.*

Ce qui se passe :

- 🔗 tous les liens de configuration du compte cessent de fonctionner, y compris celui déjà remis : quiconque l’ouvre
  obtient *Ce lien a été retiré.* et ne peut pas configurer le compte ;
- ⏳ le compte attend toujours : sa ligne affiche encore **En attente de configuration**, il conserve sa place, et il
  ne peut toujours pas être réactivé ici ;
- 🔁 pour laisser entrer l’administrateur, donnez-lui un nouveau lien : sur le serveur, `user setup-link` en affiche un (voir
  « Un nouveau lien de configuration pour l’administrateur initial » dans [Outils en ligne de commande](cli_tools.md))). Redémarrer le serveur avec le même
  `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` ne donne pas de nouveau lien, car l’instance a déjà vu ce
  jeton : chaque démarrage consigne un avertissement indiquant que le lien de configuration a été retiré, et demande d’exécuter
  `dev.py user setup-link`, ou de définir un nouveau jeton.

Sur le serveur, `user deactivate` sur ce compte annule son lien de la même manière.

Si l’administrateur a terminé sa configuration après le chargement de votre liste, il ne reste rien à
annuler : LibreFolio ne change rien et indique *Cet administrateur a terminé sa configuration entre-temps : rien n’a été modifié.*
L’onglet se recharge, et la ligne affiche désormais un administrateur actif,
avec **Désactiver** à la place de **Annuler le lien de configuration**. Le compte reste actif et son propriétaire
connecté.

Pour supprimer plutôt le compte, cliquez sur **Supprimer** ([Supprimer un compte](#delete)), sans
**Retirer le rôle d’administrateur** au préalable. Le compte disparaît avec ses liens de configuration, sa place est libérée, et
plus personne n’attend de configuration : `user setup-link` ne trouve personne, et les variables `LIBREFOLIO_ADMIN_*`
ne créent rien aux démarrages suivants, puisque l’instance possède des comptes. Si la configuration a été
terminée entre-temps là aussi, rien n’est supprimé : la boîte de dialogue indique *Un administrateur doit être
rétrogradé avant de pouvoir être supprimé.*, car le compte est désormais un administrateur actif.

### 🔤 Noms d’utilisateur contenant un @ {: #usernames-with-at }

À partir de la version 1.3, un nouveau nom d’utilisateur ne peut pas contenir `@` : à la connexion, LibreFolio interprète tout ce qui contient un
`@` comme une adresse e-mail. L’inscription, un changement de nom d’utilisateur dans le Profil et `user create` sur la
[ligne de commande](cli_tools.md) le refusent, et un `LIBREFOLIO_ADMIN_USERNAME` contenant un `@` empêche le
serveur de démarrer (« L’administrateur initial » dans [Variables d’environnement](configuration_accounts.md#initial-admin)).
Les espaces, les lettres accentuées et les signes tels que `.`, `_`, `-` ou `+` restent acceptés.

Un compte créé avant la version 1.3 peut en avoir un, par exemple `anna@example.com` comme nom d’utilisateur :

- 🏷️ le nom d’utilisateur reste tel quel : rien ne le renomme. Son utilisateur peut le changer dans son
  [Profil](../user/settings/profile.md), pour un nom sans `@` ;
- 🔑 le compte se connecte avec son adresse e-mail, car chaque compte en possède une. Le nom d’utilisateur lui-même
  ne fonctionne que tant qu’aucun compte ne l’a comme adresse e-mail : saisie à la connexion, une adresse désigne le
  compte qui la possède ;
- 📧 aucun autre compte ne peut prendre ce nom d’utilisateur comme adresse e-mail, quelle que soit la casse : l’inscription,
  le Profil, `user create` et `user set-email` le refusent avec *E-mail déjà enregistré*. Le
  compte lui-même peut le prendre comme sa propre adresse.

---

## ✉️ Invitations {: #invitations }

Pour inviter quelqu’un :

1. Cliquez sur **Inviter**.
2. Facultativement, saisissez son adresse dans **E-mail (facultatif)**. Ce n’est qu’une indication de la personne à qui
   l’invitation est destinée : le lien fonctionne pour quiconque l’ouvre. La liste des invitations l’affiche, et
   le formulaire d’inscription la préremplit ; la personne peut la modifier.
3. Cochez **Administrateur** si le nouveau compte doit gérer l’instance.
4. Cliquez sur **Créer le lien** : *Partagez ce lien : il fonctionne une fois, pendant 7 jours.* Vérifiez l’[adresse du serveur](#server-address), cliquez sur **Copier** et envoyez le lien vous-même, par message ou
   e-mail, ou laissez LibreFolio l’envoyer par e-mail : [Envoyer par e-mail](#send-by-email).
5. Cliquez sur **Terminé** : l’invitation rejoint les **Invitations en cours**.

La personne ouvre le lien et crée son compte avec le nom d’utilisateur, l’adresse e-mail et le mot de passe de son
choix : [Premiers pas](../user/getting-started.md) montre ce qu’elle voit.

- 🔗 Le lien n’est affiché qu’une fois, au moment où vous le créez. S’il est perdu, révoquez l’invitation et
  créez-en une nouvelle.
- 📏 Une invitation occupe une place à partir du moment où vous la créez et jusqu’à ce qu’elle soit utilisée, révoquée ou
  expirée ; le compte qu’elle crée prend ensuite cette place.
- 🔤 Une adresse e-mail n’appartient qu’à un seul compte, quelle que soit la casse (`Anna@example.com` est
  `anna@example.com`), mais seules les lettres A à Z sont comparées sans tenir compte de la casse : `Émile@example.com` et
  `émile@example.com` sont deux adresses différentes.

### 📋 Invitations en cours {: #open-invitations }

Les invitations que personne n’a encore utilisées, de la plus ancienne à la plus récente : l’adresse e-mail (ou *Aucun e-mail*), un badge
**Admin** lorsque l’invitation crée un administrateur, ainsi que quand elle a été créée et quand elle expire. Une invitation
quitte la liste dès qu’elle est utilisée, révoquée ou expirée.

**Révoquer** retire une invitation à tout moment, après une confirmation : le lien cesse immédiatement de fonctionner, et sa place est libérée.

---

## 🔑 Liens de réinitialisation du mot de passe {: #reset-links }

Lorsque quelqu’un a oublié son mot de passe, envoyez-lui un lien pour qu’il en choisisse lui-même un nouveau. Avec l’e-mail,
il peut aussi en demander un depuis la page de connexion : voir [Mots de passe oubliés](email_flows.md#forgot-password).

1. Ouvrez sa ligne et cliquez sur **Lien de réinitialisation du mot de passe**.
2. La boîte de dialogue explique : *Un lien à usage unique pour définir un nouveau mot de passe, valable 30 minutes. Les liens
   créés auparavant pour ce compte cessent de fonctionner.* Cliquez sur **Créer le lien**.
3. Vérifiez l’[adresse du serveur](#server-address), cliquez sur **Copier** et envoyez le lien, ou cliquez sur
   **Envoyer par e-mail** ([Envoyer par e-mail](#send-by-email)) ; puis cliquez sur **Terminé**.

- ⏱️ Le lien fonctionne une fois, pendant 30 minutes, et seul le lien le plus récent d’un compte fonctionne.
- 🔒 Il cesse également de fonctionner dès que la personne change son mot de passe ou son adresse e-mail, ou que vous
  exécutez `user reset` ou `user set-email` sur la [ligne de commande](cli_tools.md).
- 🚪 La création du lien ne déconnecte personne. Une fois que la personne définit le nouveau mot de passe, son compte est
  déconnecté de tous les appareils.
- 🔗 Le lien n’est affiché qu’une fois : s’il est perdu, créez-en un nouveau.

Ce que la personne voit est décrit dans [Premiers pas](../user/getting-started.md).

---

## 🌐 L’adresse du serveur d’un lien {: #server-address }

Les liens d’invitation et de réinitialisation du mot de passe s’affichent dans le même panneau :

- **Adresse du serveur** : le début du lien. Elle est renseignée avec `LIBREFOLIO_PUBLIC_URL` lorsque le
  serveur la définit, sinon avec l’adresse qu’utilise actuellement votre navigateur. *Modifiez-la si vos utilisateurs
  accèdent à LibreFolio à une autre adresse* : par exemple, vous êtes chez vous sur `http://192.168.1.10:6040`, tandis que vos utilisateurs passent par `https://librefolio.example.com`.
- **Lien** : l’adresse du serveur suivie du chemin propre au lien. **Copier** le place dans le presse-papiers ;
  si le navigateur refuse, le lien est sélectionné pour que vous puissiez le copier à la main. *Valable jusqu’au …*
  indique son expiration.

Lorsque vous modifiez l’adresse, votre navigateur vérifie, une demi-seconde après que vous avez cessé de taper, que
**cette** instance répond à cette adresse, et pas n’importe quel serveur : il charge une minuscule image depuis
`<address>/api/v1/auth/address-probe.png?nonce=…`, qui mesure 1×1 lorsque cette instance répond et 2×1
lorsqu’une autre le fait. L’adresse renseignée elle-même n’est pas vérifiée.

| Message | Ce que cela signifie |
|---|---|
| *Vérification que ce LibreFolio répond à cette adresse…* | La vérification est en cours |
| *Cette instance répond à cette adresse.* | Le lien atteint ce LibreFolio |
| *Quelque chose répond à cette adresse, mais pas cette instance : vérifiez avant de partager.* | Un autre LibreFolio y répond : ce n’est probablement pas l’adresse voulue |
| *Cette adresse n’a pas pu être vérifiée depuis ce navigateur : vous pouvez tout de même partager le lien.* | Le navigateur n’a pas pu charger l’image. Rien n’y répond (adresse erronée ou fermée, ou aucune réponse en 8 secondes) ; une page ouverte avec `https://` vérifie une adresse `http://`, ce que le navigateur bloque ; une page sur une adresse publique vérifie une adresse locale, que certains navigateurs bloquent ou n’autorisent qu’après vous avoir demandé la permission ; une instance bloquée ne fournit pas l’image ; ou un LibreFolio plus ancien répond, ce qui ne peut pas être vérifié |
| *Saisissez une adresse commençant par http:// ou https://, sans ? ni #.* | Ce n’est pas une adresse : **Copier** reste désactivé jusqu’à correction |

Quel que soit le résultat, sauf s’il ne s’agit pas d’une adresse, vous pouvez copier le lien : la vérification ne donne qu’un avis. De retour sur l’adresse renseignée, le message disparaît. Fonctionnement de la vérification :
[Sonde d’adresse](../developer/architecture/security.md#address-probe), pour les développeurs.

!!! tip "🌐 Définissez l’adresse une fois"

    Définissez `LIBREFOLIO_PUBLIC_URL` sur l’adresse qu’ouvrent vos utilisateurs, et le panneau part de celle-ci : voir
    « Comptes et inscriptions » dans [Variables d’environnement](configuration_accounts.md#accounts). La
    [ligne de commande](cli_tools.md) la place aussi devant les liens qu’elle affiche.

---

## 📧 Envoyer par e-mail {: #send-by-email }

Lorsque l’instance peut envoyer des e-mails contenant un lien — e-mail **Prêt** et `LIBREFOLIO_PUBLIC_URL` défini sur
une adresse que LibreFolio peut utiliser ([E-mails avec un lien](email_flows.md#public-url)) — les deux boîtes de dialogue de lien proposent
**Envoyer par e-mail** sous le lien :

- **Une invitation** : **Envoyer à** est prérempli avec l’adresse indiquée dans l’invitation, et vous pouvez la
  modifier. Si vous le laissez vide, l’e-mail est envoyé à l’adresse indiquée dans l’invitation ; si l’invitation n’en comporte pas, la
  boîte de dialogue en demande une.
- **Un lien de réinitialisation du mot de passe** n’a pas de champ : l’e-mail est envoyé à l’adresse du compte, et uniquement
  tant que le compte est actif.
- **Le lien contenu dans l’e-mail commence par `LIBREFOLIO_PUBLIC_URL`**, quel que soit le contenu de l’**Adresse du serveur**
  ci-dessus : la boîte de dialogue le précise.
- **La langue** : une invitation est rédigée dans la langue choisie dans **Langue de l’e-mail**, la
  **Langue par défaut** de l’instance sauf si vous en choisissez une autre ; un lien de réinitialisation est rédigé dans celle du compte.
- **Le résultat** s’affiche dans la boîte de dialogue : *Envoyé à …* avec l’adresse et la langue dans laquelle l’e-mail a été
  rédigé, ou la raison pour laquelle l’e-mail n’a pas été envoyé ([Erreurs d’envoi](email_troubleshooting.md#sending-errors)).

Sans e-mail, le bouton n’est pas présent : copiez le lien comme auparavant. Les règles et les limites :
[Liens envoyés par un administrateur](email_flows.md#admin-links).

---

## 🗑️ Supprimer un compte {: #delete }

Ouvrez la ligne du compte et cliquez sur **Supprimer** ; pour un administrateur, cliquez d’abord sur **Retirer le rôle d’administrateur**,
sauf s’il s’agit de l’administrateur initial [en attente de son lien de configuration](#cancel-setup), que vous
supprimez directement. La suppression suit la même règle que la suppression de son propre compte
([Profil](../user/settings/profile.md)) :

1. Pour un compte actif, la boîte de dialogue propose d’abord **Désactiver** à la place : cela conserve tous les courtiers et
   toutes les transactions et peut être annulé ; le compte ne peut simplement plus se connecter.
2. Ensuite, elle montre ce que la suppression emporterait :
    - **Supprimés, avec toutes leurs transactions et tous leurs fichiers** : les courtiers dont le compte est le seul Propriétaire,
      chacun avec son nombre de transactions. Ils disparaissent aussi pour les utilisateurs avec lesquels il les partageait.
      S’il n’y en a aucun, la boîte de dialogue indique *Aucun courtier n’est supprimé* ;
    - **Courtiers partagés qui restent (seul l’accès disparaît)** : les autres courtiers que le compte peut ouvrir,
      avec son rôle sur chacun ;
    - un avertissement lorsque des transactions sur d’autres courtiers sont les moitiés de transferts avec les courtiers qui
      disparaissent : elles restent, sans leur autre moitié. Un transfert reçu devient un ajustement à son
      coût, et un transfert envoyé à l’un de ces courtiers devient un ajustement qui sort les actifs du courtier qui les a envoyés,
      sans valeur : leur coût y compte comme une perte réalisée (voir
      [Modifier ou supprimer un courtier](../user/brokers/index.md)).
3. Saisissez le nom d’utilisateur du compte, puis cliquez sur **Supprimer définitivement**.

!!! danger "La suppression d’un compte est irréversible"

    Le compte, ses paramètres et les courtiers indiqués comme supprimés disparaissent immédiatement, et quiconque y est
    connecté est déconnecté à sa prochaine requête. Si la suppression échoue pour une raison technique,
    rien n’est supprimé. Si la boîte de dialogue ne parvient pas à charger ce que la suppression emporterait, elle ne vous laisse pas
    supprimer : fermez-la et réessayez.

Fonctionnement de la règle : [Suppression d’un compte](../developer/architecture/access_control.md#admin-account-deletion),
pour les développeurs.

---

## 🔗 Voir aussi

- 📝 **[Variables d’environnement](configuration_accounts.md#accounts)** — « Comptes et inscriptions » : `LIBREFOLIO_MAX_USERS`,
  `LIBREFOLIO_REGISTRATION` et `LIBREFOLIO_PUBLIC_URL`
- ⚙️ **[Paramètres globaux](settings.md)** — « Qui peut s’inscrire » : le paramètre **Inscription**
- 🛠️ **[Outils en ligne de commande](cli_tools.md)** — « Gérer les utilisateurs » : la plupart de ces tâches, sans navigateur
- 👤 **[Profil](../user/settings/profile.md)** — Votre propre compte, et comment le supprimer
- 🧑‍💻 Pour les développeurs : **[API administrateur](../developer/architecture/access_control.md#admin-user-api)**
  et **[Composants des paramètres](../developer/frontend/components/features/settings.md#userstab)**
