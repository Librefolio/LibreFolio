# 👥 Configuration : comptes et recherche d'actifs

Qui peut **s'inscrire** à votre LibreFolio, combien de comptes il peut contenir, la limite des connexions
échouées et l'**administrateur initial** ; puis deux options de la recherche d'actifs : l'ordre des
fournisseurs de prix dans les résultats et la recherche web facultative.

- **Où l'écrire** : dans le fichier `.env` de LibreFolio ([Configuration](configuration.md), la première page du guide,
  explique le fichier et ses autres options). Puis redémarrez LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`.
- **Depuis l'application** : les choix correspondants se trouvent dans les [Paramètres globaux](settings.md)
  (**Paramètres › Administration**). Une variable définie l'emporte : chaque ligne ci-dessous explique comment.

---

## 👥 Comptes et inscriptions {: #accounts }

**Où** : dans le `.env` de LibreFolio, section **Accounts** de `.env.example` : décommentez une ligne pour la définir. Toutes
sont facultatives ; une valeur vide équivaut à une valeur non définie. Sans elles, les [Paramètres globaux](settings.md) décident ; trois
autres variables, pour les installations faites avec un script et Docker Compose, créent l'[administrateur initial](#initial-admin) d'une nouvelle instance.

| Variable | Valeur par défaut | Ce qu'elle fait |
| --- | --- | --- |
| `LIBREFOLIO_REGISTRATION` | _non définie_ | Qui peut créer un compte : `open` (tout le monde), `invite` (uniquement avec un lien d'invitation) ou `disabled` (personne). Non définie : le paramètre **Inscription** décide. |
| `LIBREFOLIO_MAX_USERS` | _non définie_ (aucune limite) | Le nombre maximal de comptes que l'instance peut contenir : un nombre entier, au moins `1` ; toute autre valeur (`0`, `abc`, `-3`, `1.5`) arrête le serveur au démarrage. Voir [Quand l'instance est pleine](#user-limit). |
| `LIBREFOLIO_DEFAULT_LANGUAGE` | _non définie_ | La langue des comptes qui n'en ont pas choisi une, et des e-mails envoyés aux personnes qui n'ont pas encore de compte : `en`, `it`, `fr` ou `es`. Non définie : le paramètre **Langue par Défaut** décide ; sur une nouvelle instance, l'anglais. |
| `LIBREFOLIO_DEFAULT_CURRENCY` | _non définie_ | La devise avec laquelle les nouveaux comptes démarrent : un code ISO 4217 que LibreFolio connaît, comme `EUR`, `USD` ou `CHF`. Non définie : le paramètre **Devise par défaut** décide ; sur une nouvelle instance, `EUR`. |
| `LIBREFOLIO_DEFAULT_TIMEZONE` | _non définie_ | Le fuseau horaire de l'application, celui dans lequel sont lues les heures du [planificateur de données de marché](settings.md#market-data-scheduler) : un nom IANA comme `Europe/Rome` ou `America/New_York`. Non définie : le paramètre **Fuseau horaire** décide ; sur une nouvelle instance, `UTC`. |
| `LIBREFOLIO_PUBLIC_URL` | _non définie_ | L'adresse à laquelle vos utilisateurs ouvrent LibreFolio, avec `http://` ou `https://`, comme `https://librefolio.example.com` : le début des liens d'invitation et de réinitialisation du mot de passe, et des liens des e-mails. |
| `LIBREFOLIO_LOGIN_LIMIT` | `on` | La limite des connexions échouées : `on` ou `off`, quelle que soit la casse, espaces autour de la valeur compris. `off` uniquement pour une instance de test. Toute autre valeur, `true`, `1` et `yes` compris, arrête le serveur au démarrage. Voir [Connexions échouées](#login-limit). |

- **`LIBREFOLIO_REGISTRATION`** — dans l'application : **Inscription**, dans les Paramètres globaux. Non définie : sur une nouvelle
  instance, c'est **Sur invitation**, sauf si un administrateur l'a modifié ; une instance mise à niveau depuis une version
  antérieure conserve le mode qu'elle avait. Définie : cette valeur l'emporte, et le paramètre global ne peut pas être modifié depuis l'application.
  La casse et les espaces autour de la valeur n'ont pas d'importance. Quelle que soit la valeur, le premier compte d'une nouvelle instance peut être
  créé depuis la page de connexion, avec **Inscrivez-vous ici**, et devient l'administrateur
  ([Qui peut s'inscrire](settings.md)) ; avec `LIBREFOLIO_ADMIN_EMAIL`, LibreFolio crée directement cet administrateur
  à la place ([L'administrateur initial](#initial-admin)). `open` affiche aussi aux administrateurs qui ouvrent
  l'application depuis une adresse extérieure au réseau local un avertissement qui nomme cette variable
  ([L'avertissement d'inscription ouverte](settings.md)).
- **`LIBREFOLIO_MAX_USERS`** — les comptes actifs comptent, tout comme chaque invitation jusqu'à ce qu'elle soit utilisée, révoquée ou
  expirée, chaque compte en attente de la vérification de son e-mail tant que son lien est actif, et
  l'[administrateur initial](#initial-admin) tant qu'il attend sa configuration ; les comptes désactivés ne comptent pas.
- **`LIBREFOLIO_DEFAULT_LANGUAGE`, `LIBREFOLIO_DEFAULT_CURRENCY`, `LIBREFOLIO_DEFAULT_TIMEZONE`** — dans l'application :
  **Langue par Défaut** et **Devise par défaut** des [Paramètres globaux](settings.md), **Fuseau horaire** de la configuration
  du planificateur. La variable s'applique jusqu'à ce qu'un administrateur enregistre ce paramètre pour la première fois ;
  à partir de ce premier enregistrement, la valeur de l'administrateur l'emporte, même si elle revient à la valeur par défaut (anglais, `EUR`,
  `UTC`). Langue et devise quelle que soit la casse. Le serveur lui-même fonctionne toujours en UTC.
- **`LIBREFOLIO_PUBLIC_URL`** — qui l'utilise :
    - l'onglet [Utilisateurs](users.md) de Paramètres › Administration : les boîtes de dialogue d'invitation et de réinitialisation du mot de passe renseignent
      leur champ **Adresse du serveur** avec elle ; sans elle, avec l'adresse qu'utilise le navigateur de l'administrateur.
      L'administrateur peut la modifier, et le navigateur vérifie alors que ce LibreFolio y répond ;
    - la [ligne de commande](cli_tools.md) : elle la place devant les liens d'invitation et de réinitialisation du mot de passe qu'elle
      affiche ; sans elle, elle n'affiche que le chemin (`/invite#token=…`) et vous ajoutez l'adresse vous-même ;
    - les e-mails contenant un lien, sans repli sur l'adresse du navigateur : sans elle, aucun e-mail d'invitation,
      aucun e-mail avec le lien de réinitialisation du mot de passe et aucun e-mail de mot de passe oublié
      ([E-mail](email.md)).

    Une adresse contenant un nom d'utilisateur ou un mot de passe est refusée : LibreFolio fonctionne comme si elle n'était pas définie.

**Valeur incorrecte**, deux comportements :

- **`LIBREFOLIO_REGISTRATION` et `LIBREFOLIO_PUBLIC_URL` n'arrêtent pas le serveur**, contrairement aux
  [options principales](configuration.md) : LibreFolio reste prudent et écrit une erreur dans le journal la première
  fois que chaque processus serveur a besoin de la valeur : `Invalid account configuration`, avec la variable et sa valeur
  dans `problem` (une adresse contenant un `@` n'est pas affichée : elle peut contenir un nom d'utilisateur ou un mot de passe) et dans
  `consequence` ce que cela coûte jusqu'à ce que vous corrigiez la valeur :

    | Valeur incorrecte | Ce que fait LibreFolio | `consequence` dans le journal |
    | --- | --- | --- |
    | `LIBREFOLIO_REGISTRATION` autre que les trois modes | L'inscription est fermée et le paramètre global reste verrouillé | `registration stays closed until it is fixed` |
    | `LIBREFOLIO_PUBLIC_URL` sans `http://` ni `https://`, ou avec un nom d'utilisateur ou un mot de passe | Ignorée, comme si elle n'était pas définie : la [ligne de commande](cli_tools.md) n'affiche que le chemin et indique pourquoi sous chaque lien ; les boîtes de dialogue de l'onglet [Utilisateurs](users.md) partent de l'adresse du navigateur ; aucun e-mail avec un lien et, tant que l'e-mail fonctionne, le journal de démarrage contient aussi un [avertissement](configuration_security.md#startup-checks) ([E-mail](email.md)) | `links show the bare path until it is fixed` |

- **Les cinq autres arrêtent le serveur au démarrage** avec une valeur autre que celles autorisées dans le tableau ci-dessus
  (comme une valeur inutilisable de l'[administrateur initial](#initial-admin)). L'erreur figure dans la sortie
  console du serveur (`docker compose logs librefolio` avec Docker) et nomme la variable et la valeur :
  `LIBREFOLIO_LOGIN_LIMIT='yes': expected on or off`,
  `LIBREFOLIO_MAX_USERS='abc': expected a whole number of at least 1`.

Corrigez la valeur, puis redémarrez LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`.

### 📏 Quand l'instance est pleine {: #user-limit }

Lorsque les comptes actifs, les invitations en attente, les comptes en attente de la vérification de leur e-mail et un
[administrateur initial](#initial-admin) en attente de sa configuration atteignent `LIBREFOLIO_MAX_USERS` :

- personne ne peut s'inscrire sans invitation, quel que soit le mode d'[Inscription](settings.md) ;
- un lien d'invitation déjà envoyé fonctionne toujours : sa place a été comptée lors de sa création ;
- les administrateurs ne peuvent ni créer d'invitations ni réactiver de comptes, sauf depuis la
  [ligne de commande](cli_tools.md) : `user create`, `user invite` et `user activate` affichent un avertissement,
  puis continuent. `user activate` n'en affiche aucun pour un compte qui occupe déjà sa place : un compte
  en attente de la vérification de son e-mail tant que son lien est actif, ou l'administrateur initial en attente
  de sa configuration.

Une place se libère lorsqu'un compte est désactivé ou supprimé, lorsqu'une invitation est révoquée ou
expire, ou lorsque le lien d'un compte en attente de la vérification de son e-mail expire (voir
*Vérification de l'adresse e-mail* dans [E-mail](email.md)). Le premier compte d'une nouvelle instance peut toujours être
créé.

### 📉 Quand la limite est réduite {: #user-limit-over }

Si les comptes **actifs** sont plus nombreux que `LIBREFOLIO_MAX_USERS` — vous avez abaissé la limite et redémarré, ou vous avez
restauré une sauvegarde qui contient plus d'utilisateurs que la limite ne l'autorise —, l'instance est *au-delà de la limite*. LibreFolio
ne supprime personne : il demande à un administrateur de choisir.

- **Qui est concerné** : uniquement `active > limit`. Avec exactement autant de comptes actifs que la limite, rien
  ne se passe. Les invitations et les comptes en attente de leur vérification occupent des places mais ne déclenchent jamais cet état.
- **Ce que voient tous les autres** jusqu'à ce que le choix soit fait : un message indiquant qu'un administrateur doit choisir qui
  conserve l'accès. Personne d'autre qu'un administrateur n'entre, et les administrateurs ne voient rien d'autre que ce
  choix.
- **Une limite que LibreFolio ne peut pas lire** (`LIBREFOLIO_MAX_USERS=abc`, `0`) ne déclenche jamais cet état : le serveur
  ne démarre pas tant que vous n'avez pas corrigé la valeur, de sorte qu'une faute de frappe ne peut pas bloquer tout le monde.

**Où** : dans l'application, en tant qu'administrateur.

1. Connectez-vous. Avant toute autre page, la liste des comptes actifs s'affiche : vous êtes coché et ne pouvez pas être
   décoché ; chaque ligne indique combien de courtiers le compte détient **seul** (ces courtiers restent, mais personne d'autre ne peut
   y accéder tant que le compte n'est pas réactivé) ; un compteur indique combien de comptes sont choisis par rapport à
   ce que la limite autorise.
2. Avant tout, faites la sauvegarde complète : la même page la propose, afin que les données puissent être emportées avant que
   quiconque soit désactivé.
3. Choisissez qui conserve l'accès, puis **Désactiver les autres et continuer**. La page indique combien
   d'invitations elle annulera avant que vous confirmiez.

   Résultat : les comptes non choisis sont **désactivés**, pas supprimés : ils sont déconnectés, ne peuvent plus se connecter et
   conservent toutes leurs données ; vous pouvez en réactiver un lorsqu'une place se libère
   ([Quand l'instance est pleine](#user-limit)). Les invitations en attente sont annulées, des plus récentes aux plus anciennes, seulement dans la mesure
   où les comptes choisis ont besoin de leurs places.

Aucune étape particulière n'est nécessaire après une restauration : les comptes restaurés sont comptés de la même manière.

### 🚦 Connexions échouées {: #login-limit }

Lorsque les connexions échouent à répétition, LibreFolio cesse de vérifier les mots de passe pendant un moment : personne ne peut essayer mot de passe après
mot de passe jusqu'à ce qu'un fonctionne. La limite est active sauf si vous la désactivez.

| Limite | Au-delà |
| --- | --- |
| 10 connexions échouées toutes les 15 minutes avec le même nom d'utilisateur ou la même adresse e-mail, qu'un compte la possède ou non | Toute connexion avec ce nom d'utilisateur ou cette adresse e-mail est refusée, bon mot de passe compris, jusqu'à ce que l'échec le plus ancien ait 15 minutes. |
| 50 connexions échouées toutes les 15 minutes depuis la même adresse, quels que soient le nom d'utilisateur ou l'adresse e-mail utilisés ; une adresse IPv6 est comptée par son /64, le bloc qu'un abonné détient habituellement. Ne sont pas comptées les connexions qui passent par un proxy en lequel LibreFolio n'a pas confiance, sur une adresse locale : voir *Derrière un proxy inverse* ci-dessous | Toute connexion depuis cette adresse est refusée, pour n'importe quel compte, jusqu'à ce que l'échec le plus ancien ait 15 minutes. |

**Ce que voit l'utilisateur** : la page de connexion indique *Trop de tentatives de connexion : patientez quelques minutes et réessayez.*
L'attente est de 15 minutes au maximum. La réponse est la même, que le compte existe ou non : la limite ne
révèle pas quels comptes existent.

**Ce qui compte comme un échec** :

- un mauvais mot de passe, ou un nom d'utilisateur ou une adresse e-mail qu'aucun compte ne possède ;
- **un mauvais mot de passe actuel** dans **Changer le Mot de Passe**, ou lorsqu'un utilisateur modifie sa propre adresse e-mail dans l'onglet
  Profil ([Profil](../user/settings/profile.md)) : cela compte comme une connexion échouée avec le nom d'utilisateur du compte,
  depuis la même adresse. Ainsi, 10 mots de passe actuels erronés bloquent aussi la connexion avec ce nom d'utilisateur,
  et les connexions échouées avec le nom d'utilisateur bloquent ces deux contrôles : **Changer le Mot de Passe** et l'onglet Profil
  affichent alors *Trop de mots de passe erronés : patientez quelques minutes et réessayez.* La suppression de son propre compte ne demande
  aucun mot de passe : rien à limiter ici ;
- **un mauvais mot de passe dans Renvoyer le lien** : sur la page de connexion, un compte en attente de la vérification de son e-mail
  dispose de **Renvoyer le lien**, qui vérifie le nom d'utilisateur ou l'adresse e-mail et le mot de passe comme le fait une
  connexion ([Vérification de l'adresse e-mail](email_flows.md#verification)). Cela compte comme une connexion échouée avec ce qui
  a été saisi, depuis la même adresse ; au-delà de la limite, il est refusé avant la vérification du mot de passe, et la
  page indique dans combien de minutes réessayer. Le bon mot de passe efface les échecs de ce qui a été saisi, comme le fait une
  connexion réussie. Ses propres limites s'appliquent toujours
  ([Limites des e-mails de vérification](email_flows.md#verification-limits)).

**Ce qui ne compte pas** :

- le bon mot de passe d'un compte désactivé, ou d'un compte encore en attente de la vérification de son e-mail : ni un
  échec ni une réussite ;
- une connexion que la limite refuse : elle n'est pas comptée et son mot de passe n'est même pas vérifié, de sorte que réessayer ne
  prolonge pas l'attente ;
- les liens d'invitation et de réinitialisation du mot de passe : leurs jetons sont de longues valeurs aléatoires que personne ne peut deviner, et une limite
  par adresse pourrait les refuser à tous les utilisateurs derrière le même routeur.
  **Mot de passe oublié ?** ne demande aucun mot de passe et possède ses propres limites : voir
  [Mots de passe oubliés](email_flows.md#forgot-password).

**Comment elles sont comptées** :

- **une connexion réussie** efface les échecs du nom d'utilisateur ou de l'adresse e-mail utilisés, pas ceux de l'adresse d'où elle provient ;
- **le nom d'utilisateur et l'adresse e-mail sont comptés séparément**, même pour un seul compte : une personne qui devine son mot de passe
  dispose de 10 essais avec le nom d'utilisateur et de 10 avec l'adresse e-mail toutes les 15 minutes, toujours dans la limite des 50 de
  son adresse. Les majuscules A à Z n'ont pas d'importance : `Alice` et `alice` partagent un même compteur ;
- **conservés en mémoire**, par chaque processus serveur : un redémarrage oublie tous les compteurs, ce qui permet aussi à un utilisateur qui
  ne peut pas attendre de se reconnecter immédiatement. Avec plusieurs processus serveur (`./dev.py server --workers N`), chacun conserve ses
  propres compteurs, de sorte que les limites sont N fois celles-ci ; l'image Docker n'en exécute qu'un.

**Derrière un proxy inverse**, l'adresse comptée est celle du visiteur, telle que LibreFolio la lit. Indiquez votre proxy
à LibreFolio, en le listant dans `FORWARDED_ALLOW_IPS` ou en nommant l'en-tête qu'il définit dans
`LIBREFOLIO_CLIENT_IP_HEADER` : où et comment, dans [L'adresse du visiteur](connection_proxy.md#client-address).
D'ici là, LibreFolio voit chaque visiteur avec l'adresse du proxy, et ce qui se passe dépend de l'emplacement du
proxy :

| Proxy en lequel LibreFolio n'a pas confiance | Ce qui se passe |
| --- | --- |
| Sur une **adresse locale** (un réseau Docker, votre propre réseau ou votre VPN), comme un conteneur proxy devant l'image Docker, la configuration habituelle | LibreFolio exclut de la limite par adresse les connexions qui le traversent, afin que 50 connexions échouées de n'importe qui ne puissent pas refuser toutes les connexions. La limite par nom d'utilisateur ou adresse e-mail continue de les compter. Le journal contient un avertissement par processus serveur, la première fois qu'une requête passant par un tel proxy rencontre une limite par adresse : `Requests come through a reverse proxy that LibreFolio does not trust: the limits per client address skip them. List the proxy in FORWARDED_ALLOW_IPS, or name the header it sets in LIBREFOLIO_CLIENT_IP_HEADER` |
| Sur une **adresse publique**, comme un CDN | Chaque visiteur partage l'adresse du proxy et son compteur : 50 connexions échouées de n'importe qui refusent toute connexion passant par le proxy, bons mots de passe compris, pendant jusqu'à 15 minutes |

**Pour la désactiver**, uniquement pour une instance de test, dont les tests automatisés se connectent volontairement de manière erronée :
n'importe qui peut alors essayer des mots de passe sans pause.

**Où** : dans le `.env` de LibreFolio.

1. Ajoutez la ligne (la casse n'a pas d'importance) :

    ```env
    LIBREFOLIO_LOGIN_LIMIT=off
    ```

2. Redémarrez LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`.

    Rien n'est plus compté et rien n'est refusé. Chaque démarrage journalise un
    [avertissement](configuration_security.md#startup-checks), avec `accounts.login_limit` dans `check` :
    `LIBREFOLIO_LOGIN_LIMIT=off: failed sign-ins are not limited; turn it back on unless this is a test instance`.
    Le même contrôle, à la demande, se trouve dans l'onglet **Sécurité** de **Paramètres › Administration** : un avertissement,
    compté dans le nombre affiché sur l'onglet, jusqu'à ce que la limite soit réactivée (« Sécurité » dans les
    [Paramètres globaux](settings.md)).

3. Pour réactiver la limite, supprimez la variable ou définissez-la sur `on`, puis redémarrez : elle s'applique dès le prochain démarrage.
   Toute autre valeur arrête le serveur au démarrage ([Comptes et inscriptions](#accounts)).

### 👑 L'administrateur initial {: #initial-admin }

LibreFolio peut créer lui-même l'administrateur d'une nouvelle instance, à son premier démarrage, pour l'adresse que vous lui
donnez : personne ne peut s'inscrire en premier et prendre sa place. Il est destiné aux installations réalisées avec un script ou Docker
Compose. Sans ces variables, rien ne change, et le premier compte inscrit devient l'administrateur
([Qui peut s'inscrire](settings.md)).

| Variable | Valeur par défaut | Ce qu'elle fait |
| --- | --- | --- |
| `LIBREFOLIO_ADMIN_EMAIL` | _non définie_ | L'adresse e-mail de l'administrateur. La définir active l'administrateur initial. |
| `LIBREFOLIO_ADMIN_USERNAME` | `admin` | Le nom d'utilisateur de l'administrateur : de 3 à 50 caractères, sans `@`, comme à l'inscription. |
| `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` | _non définie_ | Facultatif : le jeton du lien de configuration, pour un script qui remet lui-même le lien. De 32 à 200 caractères, uniquement des lettres, des chiffres et `-` `.` `_` `~`, puisqu'il circule dans un lien : la sortie de `openssl rand -hex 32`, par exemple. `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE` le lit plutôt depuis un fichier : voir [Secrets](configuration_secrets.md#secrets). Non définie : LibreFolio génère le jeton. |

Une valeur vide équivaut à une valeur non définie. Les espaces autour de l'adresse e-mail et du nom d'utilisateur n'ont pas d'importance ; le jeton est utilisé
exactement tel qu'il est écrit, de sorte qu'un espace à l'intérieur, même à la fin, le rend inutilisable.

**Où** : dans le `.env` de LibreFolio, avant le premier démarrage de l'instance.

1. Définissez l'adresse de l'administrateur ; le nom d'utilisateur et le jeton seulement si vous ne voulez pas ceux qui sont générés :

    ```env
    LIBREFOLIO_ADMIN_EMAIL=admin@example.com
    # LIBREFOLIO_ADMIN_USERNAME=admin
    # LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN=
    ```

2. Démarrez LibreFolio. Au premier démarrage d'une instance **sans aucun compte**, LibreFolio :

    1. crée l'administrateur, pas encore actif, avec un mot de passe aléatoire que personne ne connaît : personne ne peut encore se connecter
       avec ;
    2. définit le [paramètre global](settings.md) **Inscription** sur **Sur invitation** ; `LIBREFOLIO_REGISTRATION`,
       lorsqu'elle est définie, décide toujours ;
    3. émet un **lien de configuration**, `/setup#token=…`, qui fonctionne une seule fois, pendant 72 heures.

3. Remettez le lien à l'administrateur. Qui le remet dépend du jeton :

    - **Avec `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`**, celui qui l'a choisi : le lien est l'adresse de l'instance suivie
      de `/setup#token=` et du jeton. LibreFolio ne le journalise pas et ne l'envoie pas par e-mail.
    - **Sans elle**, LibreFolio génère le jeton et remet lui-même le lien :
        - il écrit le lien **une fois** dans son journal, sous forme d'avertissement :
          `Setup link of the initial administrator, single use: open it to choose the password`, avec le lien dans
          `link` (avec Docker : `docker compose logs librefolio`). Le lien est l'adresse complète lorsque
          `LIBREFOLIO_PUBLIC_URL` est définie ; sinon, c'est le chemin, et `note` vous demande de placer l'adresse de
          votre serveur devant ;
        - il envoie le lien par e-mail à `LIBREFOLIO_ADMIN_EMAIL` lorsque l'e-mail fonctionne, c'est-à-dire avec un serveur SMTP configuré
          ([E-mail](email.md)) et `LIBREFOLIO_PUBLIC_URL` définie. L'e-mail est dans la langue par défaut de l'instance
          et part une fois le serveur démarré, de sorte qu'un serveur de messagerie lent ne retarde jamais le démarrage. S'il ne peut pas être
          envoyé, le journal contient
          `Setup link of the initial administrator not emailed`, avec la raison, et le lien figurant dans le journal fonctionne toujours.

4. L'administrateur ouvre le lien : la page de configuration de l'instance, où il choisit le mot de passe et se connecte.
   À partir de là, les variables ne créent plus rien : chaque démarrage journalise
   `LIBREFOLIO_ADMIN_* ignored: this instance already has accounts`, comme sur une instance qui possède déjà des comptes
   et aucun administrateur en attente.

**Pendant que l'administrateur attend** : personne ne peut s'inscrire comme premier compte, et l'administrateur occupe une
place de `LIBREFOLIO_MAX_USERS`. Un redémarrage n'émet rien de nouveau et n'écrit pas à nouveau le lien dans le journal.

**Lorsqu'aucun lien ne fonctionne plus**, chaque démarrage journalise un avertissement :

| Avertissement dans le journal | Quand |
| --- | --- |
| `The initial administrator's setup link has expired: run ./dev.py user setup-link…` | Le lien a expiré |
| `The initial administrator's setup link was withdrawn (cancelled, or its address changed): run ./dev.py user setup-link…` | Le lien a été [annulé](users.md#cancel-setup) ou l'adresse de l'administrateur a changé |

Cette commande affiche un nouveau lien ([Un nouveau lien de configuration](cli_tools.md)). Une nouvelle valeur de
`LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` donne aussi un nouveau lien, au démarrage suivant.

**Valeur inutilisable** : **arrête le serveur au démarrage**, sur toute instance, y compris une instance qui possède déjà des comptes :

- `LIBREFOLIO_ADMIN_USERNAME` ou `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` défini sans `LIBREFOLIO_ADMIN_EMAIL` ;
- un e-mail qui n'est pas une adresse ;
- un nom d'utilisateur de moins de 3 ou de plus de 50 caractères, ou contenant un `@` : la connexion lit un nom contenant
  `@` comme une adresse e-mail, et l'administrateur se connecte de toute façon avec l'adresse de `LIBREFOLIO_ADMIN_EMAIL` ;
- un jeton de moins de 32 ou de plus de 200 caractères, ou contenant un caractère autre que des lettres, des chiffres et `-` `.` `_`
  `~`, espace compris ;
- un `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE` qui ne peut pas fournir le jeton
  ([Secrets dans des fichiers](configuration_secrets.md#secret-files)).

L'erreur figure dans la sortie console du serveur (`docker compose logs librefolio` avec Docker) : elle nomme la
variable, jamais le jeton. Corrigez la valeur, puis redémarrez.

---

## 🥇 L'ordre des fournisseurs de prix dans la recherche {: #provider-order }

Lorsque vous créez un actif, la recherche interroge tous les fournisseurs de prix en même temps et liste les résultats fournisseur par
fournisseur. Chaque fournisseur déclare son niveau, **premium** (une source dont l'instance se porte garante, comme des
données sous licence) ou **community** (la valeur par défaut), et sa priorité au sein du niveau. Les résultats des fournisseurs premium
passent en premier. Aucun des fournisseurs livrés avec LibreFolio n'est premium ; sans fournisseur premium, la recherche conserve donc son ordre.

**Où** : dans le `.env` de LibreFolio. Aucun redémarrage : LibreFolio les lit à chaque recherche, et elles s'appliquent à la recherche
suivante.

| Variable | Valeur par défaut | Ce qu'elle fait |
| --- | --- | --- |
| `LIBREFOLIO_ASSET_PROVIDERS_PREMIUM` | _non définie_ | Les fournisseurs à considérer comme premium, par code, séparés par des virgules, comme `yfinance,justetf` : exactement ceux-là, quelles que soient leurs déclarations. Non définie : ce que déclare chaque fournisseur. |
| `LIBREFOLIO_ASSET_PROVIDERS_ORDER` | _non définie_ | Les fournisseurs à lister en premier, dans cet ordre, par code, séparés par des virgules ; les autres suivent dans leur ordre déclaré. Les fournisseurs premium passent toujours avant les autres. Non définie : ce que déclare chaque fournisseur. |

- Les codes des fournisseurs livrés avec LibreFolio sont `yfinance`, `justetf`, `borsa_italiana`, `css_scraper` et
  `scheduled_investment` ; un fournisseur que vous ajoutez a le sien. La casse et les espaces autour des codes n'ont pas
  d'importance.
- Un code qu'aucun fournisseur ne possède est ignoré, et le serveur le journalise une fois.

---

## 🔎 Facultatif : recherche web pour de nouveaux actifs {: #optional-web-search-for-new-assets }

Lorsque vous créez un actif, y compris depuis l'assistant d'importation de courtiers, et que la recherche propre à un fournisseur ne trouve rien,
LibreFolio peut trouver la page de l'actif au moyen d'une recherche web via la bibliothèque
[`ddgs`](https://pypi.org/project/ddgs/). Elle est activée par défaut et n'est jamais utilisée pour les mises à jour
de prix.

**Où** : dans le `.env` de LibreFolio : décommentez une ligne de `.env.example` pour en modifier une. Toutes sont facultatives. Puis redémarrez
LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`.

| Variable | Valeur par défaut | Ce qu'elle fait |
| --- | --- | --- |
| `LIBREFOLIO_WEB_LINK_FINDER_ENABLED` | `1` | `0` désactive la recherche web ; la recherche propre aux fournisseurs continue de fonctionner. |
| `LIBREFOLIO_WEB_LINK_FINDER_ENGINE` | `ddgs` | `ddgs` ne nécessite aucune configuration. `apikey` est réservé à un service de recherche payant et ne renvoie encore aucun résultat. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_REGION` | `wt-wt` | Région de recherche. `wt-wt` (monde entier) empêche les sites nationaux comme Borsa Italiana d'être relégués. Exemples : `it-it`, `us-en`. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND` | `auto` | Moteurs que `ddgs` interroge : `auto` les fait tourner pour une couverture maximale ; une liste comme `google,bing,duckduckgo` donne des résultats plus stables. |
| `LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT` | `6` | Délai d'une recherche, en secondes : au moins `1`. Toute autre valeur équivaut à la valeur par défaut. |
| `LIBREFOLIO_WEB_LINK_FINDER_MAX` | `5` | Nombre maximal de liens renvoyés par une recherche : un nombre entier, au moins `1`. Toute autre valeur équivaut à la valeur par défaut. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | _vide_ | Clé du moteur `apikey`. `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` la lit plutôt depuis un fichier : voir [Secrets](configuration_secrets.md#secrets). |

??? tip "🔁 Les résultats changent d'une tentative à l'autre — lorsqu'un actif connu n'est parfois pas trouvé"

    Avec `auto`, chaque recherche peut atteindre des moteurs différents, si bien qu'une même requête peut donner de meilleurs ou de moins bons
    résultats d'une tentative à l'autre. Réessayez une fois, ou définissez
    `LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND=google,bing,duckduckgo`.

---

## 🔗 Voir aussi

- 📄 **[Configuration](configuration.md)** — Créer le fichier `.env`, options principales, paramètres définis par les outils, …
- 📄 **[Configuration : secrets et paramètres des plugins](configuration_secrets.md)** — Secrets, paramètres des plugins
- 📄 **[Configuration : vérifications et protections](configuration_security.md)** — Vérifications au démarrage, protections du navigateur, arrêt du serveur
