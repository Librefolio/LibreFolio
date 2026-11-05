# 🛠️ Outils en ligne de commande

`dev.py`, à la racine du projet, exécute les tâches d'administration : démarrer le serveur, gérer les utilisateurs, entretenir la base de données et sauvegarder l'instance. Chaque section précise quand une commande nécessite l'arrêt du serveur.

!!! tip "Où exécuter les commandes"

    - **Installation sur l'hôte** : dans l'environnement Pipenv, avec le préfixe `pipenv run` utilisé dans cette page, ou après `pipenv shell`.
    - **Docker** : dans le conteneur en cours d'exécution, avec `docker compose exec librefolio python dev.py <command>` (depuis une copie du code source, `./dev.py docker exec <command>`, qui l'exécute en tant qu'utilisateur du serveur plutôt que root). Pas de `pipenv run` ici : l'image installe les dépendances globalement. Les commandes utilisateur, `db current`, `db check`, `backup create`, `backup inspect`, `backup restore`, `backup decrypt` et `backup pending` y fonctionnent ([Sauvegarder avec Docker](cli_backup.md#backup-docker)) ; `db upgrade` et `db downgrade` non, car elles nécessitent l'arrêt du serveur ([Appliquer les migrations](#apply-migrations)). Les commandes de développement telles que `test` ne font pas partie de l'image ([détails](docker_advanced.md#docker-exec)).

!!! info "📚 Ce guide est réparti sur plusieurs pages"

    Outre cette page : [Outils d'administration CLI : sauvegardes](cli_backup.md).

---

## 🖥️ Démarrer le serveur {: #start-the-server }

```bash
# Démarrage standard, un worker
pipenv run ./dev.py server

# Adapter le nombre de workers aux CPU (`auto` et `0` ont le même effet)
pipenv run ./dev.py server --workers auto

# Ou définir le nombre de workers
pipenv run ./dev.py server --workers 4

# Écouter sur un autre port (par défaut : PORT depuis .env, sinon 6040)
pipenv run ./dev.py server --port 8080

# Arrêter ce qui occupe déjà le port, puis démarrer
pipenv run ./dev.py server --force
```

- 🧮 Davantage de workers permettent de traiter plus de requêtes à la fois : utilisez-les sur toute machine dotée de plus d'un CPU. `auto` démarre $\max(1,\ 2\,(n-1))$ workers sur $n$ CPU.
- ⏳ Le serveur construit d'abord l'interface web et cette documentation lorsqu'elles sont absentes ou obsolètes ; le premier démarrage prend donc quelques minutes. Si l'interface ne se construit pas, le serveur ne démarre pas.
- 🔑 Un redémarrage déconnecte tout le monde, sauf si `JWT_SECRET` est défini dans `.env` (voir [Configuration](configuration.md)).
- ⏹️ Ctrl+C arrête proprement le serveur : `dev.py` lui accorde jusqu'au [budget d'arrêt](configuration_security.md#shutdown) plus 2 secondes pour s'arrêter (10 secondes par défaut), puis y met fin ; un second Ctrl+C y met fin immédiatement. Un SIGTERM envoyé à `dev.py` seul, par un superviseur de processus par exemple, bénéficie de la même attente : `dev.py` le transmet au serveur.

??? note "⚙️ Autres options du serveur — rarement nécessaires"

    | Option | Ce qu'elle fait |
    | --- | --- |
    | `--host HOST` | Adresse d'écoute (par défaut : `HOST` provenant de l'environnement ou de `.env`, sinon `0.0.0.0`) |
    | `--data-dir PATH` | Utiliser un autre répertoire de données pour cette exécution, au lieu de `LIBREFOLIO_DATA_DIR` |
    | `--no-scheduler` | Démarrer sans les synchronisations planifiées des prix et des FX |
    | `--rebuild`, `-r` | Reconstruire l'interface web même lorsqu'elle semble à jour |
    | `--debug`, `-d` | Journaux `DEBUG`, compilation de débogage de l'interface web et pages de documentation de l'API (`/api/v1/docs`, `/api/v1/redoc`), désactivées autrement |

    Formes courtes : `-w` pour `--workers`, `-p` pour `--port`, `-f` pour `--force`. `--test`, `--coverage` et `--no-reload` sont des options de développement : `pipenv run ./dev.py server --help` les liste toutes.

---

## 👤 Gérer les utilisateurs

Ces commandes écrivent directement dans la base de données ; elles fonctionnent donc aussi pendant que le serveur est en cours d'exécution.

Dans l'application, les administrateurs gèrent les autres comptes et les invitations depuis l'onglet **Utilisateurs** de **Paramètres › Administration** : voir [Utilisateurs et invitations](users.md). Les commandes ci-dessous ne nécessitent pas de navigateur : utilisez-les sur un serveur sans interface graphique, ou pour dépasser la [limite d'utilisateurs](configuration_accounts.md#user-limit).

### ➕ Créer et lister les utilisateurs

```bash
# Créer un compte administrateur
pipenv run ./dev.py user create <username> <email> <password>

# Créer un compte ordinaire
pipenv run ./dev.py user create <username> <email> <password> --role user

# Lister tous les utilisateurs : ID, nom d'utilisateur, adresse e-mail, actif, administrateur
pipenv run ./dev.py user list
```

- 👑 `user create` crée un **administrateur**, sauf si vous ajoutez `--role user`, qui crée un compte ordinaire. Les personnes peuvent aussi créer leur propre compte : avec **S'inscrire ici** sur la page de connexion tant que **Inscription** est **Ouverte** (sur une nouvelle instance, également jusqu'à ce que son premier compte existe), ou avec un [lien d'invitation](#invite) (voir [Qui peut s'inscrire](settings.md#registration)).
- 🔒 Le mot de passe suit les mêmes règles que dans l'application et l'API : au moins 8 caractères, avec une lettre majuscule, une lettre minuscule, un chiffre et un symbole. Les lettres et chiffres de tout alphabet comptent, comme `É` ou `é` ; un symbole est tout caractère qui n'est ni une lettre, ni un chiffre, ni un espace, comme `!`, `_` ou `€`. Un mot de passe qui ne respecte pas une règle ne change rien : la commande affiche `Password does not meet security requirements:` et une ligne par règle non respectée, chacune commençant par le code de la règle, comme `digit: the password must contain a digit`, puis quitte avec le code `1`.
- 🔤 Un nom d'utilisateur ne peut pas contenir `@` : à la connexion, LibreFolio interprète tout ce qui contient un `@` comme une adresse e-mail. Un tel nom d'utilisateur ne change rien : la commande s'arrête avec l'erreur `A username cannot contain @: the sign-in reads it as an email address` et quitte avec le code `1`. Les espaces, les lettres accentuées et les signes tels que `.`, `_`, `-` ou `+` sont acceptés. Un nom d'utilisateur doit aussi comporter entre 3 et 50 caractères, comme à l'inscription : un nom plus court ou plus long ne change rien non plus ; la commande s'arrête avec l'erreur `A username must be 3 to 50 characters long` et quitte avec le code `1`. La commande s'arrête également, avec `Username already taken`, sur un nom d'utilisateur qu'un autre compte possède, et, avec `Email already registered`, sur une adresse qu'un autre compte possède, ou qui est le nom d'utilisateur d'un autre compte (voir [`user set-email`](#set-email)), quelles que soient les majuscules.
- 📏 Lorsque l'instance a atteint sa [limite d'utilisateurs](configuration_accounts.md#user-limit), `user create` avertit `The instance is at its limit (LIBREFOLIO_MAX_USERS: 5 of 5 places taken): the command line creates the account anyway`, puis crée le compte : la ligne de commande est le moyen de dépasser la limite.

### ✉️ Inviter quelqu'un {: #invite }

```bash
# Un lien d'invitation pour un compte ordinaire
pipenv run ./dev.py user invite

# Une invitation pour un administrateur, avec une note indiquant à qui elle est destinée
pipenv run ./dev.py user invite --admin --email anna@example.com
```

La commande affiche un lien qui fonctionne une fois, pendant 7 jours. Envoyez-le à la personne : elle l'ouvre et crée son compte, avec le nom d'utilisateur, l'adresse e-mail et le mot de passe qu'elle choisit ([ce qu'elle voit](../user/getting-started.md#invitation-link)).

- 👑 `--admin` fait du nouveau compte un administrateur ; sans cette option, le compte est ordinaire.
- ✉️ `--email` n'est qu'une indication du destinataire de l'invitation : la personne peut s'inscrire avec une autre adresse.
- 🌐 Lorsque [`LIBREFOLIO_PUBLIC_URL`](configuration_accounts.md#accounts) est défini, le lien est complet, par exemple `https://librefolio.example.com/invite#token=…`. Sans cela, la commande affiche uniquement le chemin, `/invite#token=…`, et vous rappelle de placer l'adresse de votre serveur devant, par exemple `http://192.168.1.10:6040`. Si la variable est définie mais n'est pas une adresse `http://` ou `https://`, le rappel indique plutôt `LIBREFOLIO_PUBLIC_URL is not valid (…)`, avec la raison.
- 🔒 La partie secrète du lien se trouve après `#` : les navigateurs n'envoient jamais cette partie au serveur, elle ne se retrouve donc pas dans les journaux du serveur ou du proxy. Envoyez le lien en entier.
- 🚪 Les invitations fonctionnent tant que **Inscription** est **Ouverte** ou **Sur invitation**. Lorsqu'elle est **Fermée**, la commande s'arrête avec l'erreur `Registration is disabled: invitations cannot be created` et quitte avec le code `1`, et les liens déjà envoyés ne fonctionnent pas non plus.
- 📏 Une invitation occupe une place de la [limite d'utilisateurs](configuration_accounts.md#user-limit) jusqu'à ce qu'elle soit utilisée ou révoquée, ou qu'elle expire. À la limite, la commande avertit, puis crée quand même l'invitation.
- ⏳ Il n'existe aucune commande pour annuler une invitation : un lien que personne n'a utilisé cesse de fonctionner après 7 jours. Un administrateur peut le révoquer plus tôt avec **Révoquer** dans l'onglet [Utilisateurs](users.md#open-invitations), ou via l'API : `GET /api/v1/users/invites` liste les invitations en attente, `DELETE /api/v1/users/invites/<id>` en révoque une.

### 🔑 Réinitialiser un mot de passe ou verrouiller un compte {: #reset-a-password-or-lock-an-account }

```bash
# Définir un nouveau mot de passe (mêmes règles que ci-dessus)
pipenv run ./dev.py user reset <username> <new_password>

# Verrouiller un compte, puis le déverrouiller
pipenv run ./dev.py user deactivate <username>
pipenv run ./dev.py user activate <username>
```

- ⏱️ Une réinitialisation met fin aux sessions déjà ouvertes : chaque appareil connecté au compte est déconnecté à sa prochaine requête. Pour bloquer quelqu'un durablement, désactivez le compte : il est refusé dès sa prochaine requête, et le réactiver ne restaure pas ses anciennes sessions.
- 🔗 Une réinitialisation annule aussi tout lien de réinitialisation de mot de passe encore ouvert pour le compte, quel qu'en soit le créateur.
- 👑 `deactivate` refuse le dernier administrateur actif : la commande s'arrête avec l'erreur `User '<username>' is the last active administrator: promote or activate another administrator first` et quitte avec le code `1`.
- 📏 Lorsque l'instance a atteint sa [limite d'utilisateurs](configuration_accounts.md#user-limit), `activate` sur un compte désactivé avertit `… the command line reactivates the account anyway`, puis réactive le compte. Elle n'affiche aucun avertissement pour un compte qui occupe déjà sa place : un compte en attente de son e-mail avec un lien actif (ci-dessous), ou l'administrateur initial en attente de son lien de configuration.
- 📬 Lorsque la vérification de l'e-mail est activée, `activate` autorise immédiatement l'accès à un compte qui attend son e-mail — sans avertissement de limite tant que son lien est actif, puisque sa place est déjà comptée — et `deactivate` met fin à son attente : dans les deux cas, les liens de vérification envoyés cessent de fonctionner. Voir *Vérification de l'e-mail* dans [E-mail](email.md).
- 🏁 Sur l'[administrateur initial](configuration_accounts.md#initial-admin) qui attend encore son lien de configuration, `reset` et `activate` fonctionnent comme sur tout compte : elles le configurent sans son lien, et `activate` n'affiche aucun avertissement de limite, puisque le compte occupe déjà sa place. L'une ou l'autre met définitivement fin à l'attente : ses liens de configuration cessent de fonctionner, y compris celui de `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`, et ni [`user setup-link`](#setup-link) ni un nouveau `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` ne lui en donnent un autre. `activate` seul laisse un compte actif dont personne ne connaît le mot de passe, jusqu'à ce que `reset` ou un [lien de réinitialisation](#reset-link) lui en donne un ; `reset` seul le laisse inactif, jusqu'à `activate`.
- 🚫 Sur cet administrateur encore en attente, `deactivate` ne met rien en place : elle annule le lien de configuration, comme le fait **Annuler le lien de configuration** dans [Utilisateurs et invitations](users.md#cancel-setup). La commande affiche `✅ User '<username>' deactivated` ; tous les liens de configuration du compte cessent de fonctionner, y compris celui de `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`, et le compte continue d'attendre un nouveau lien : [`user setup-link`](#setup-link) lui en donne un, tout comme un nouveau `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` au démarrage suivant. Le même jeton lors d'un redémarrage n'en donne aucun, car l'instance l'a déjà vu.
- 💬 L'écran **Mot de passe oublié ?** de l'application affiche cette commande pour les deux installations : la ligne `docker compose exec librefolio sh -c 'exec gosu …' sh user reset …` pour Docker (celle de [`docker exec`](docker_advanced.md#docker-exec), qui s'exécute en tant qu'utilisateur du serveur, et non root), et `./dev.py user reset …` pour une installation sur l'hôte, à exécuter après `pipenv shell` ou précédée de `pipenv run`. Lorsque votre instance peut envoyer un lien de réinitialisation par e-mail, l'écran affiche d'abord le formulaire d'e-mail et conserve les commandes dans un panneau fermé par défaut ([Mots de passe oubliés](email_flows.md#forgot-password)).

### 🔗 Envoyer un lien de réinitialisation de mot de passe {: #reset-link }

```bash
pipenv run ./dev.py user reset-link <username>
```

Au lieu de choisir un nouveau mot de passe pour quelqu'un avec `user reset`, envoyez-lui ce lien : la personne l'ouvre et choisit elle-même le nouveau mot de passe ([ce qu'elle voit](../user/getting-started.md#password-reset-link)).

- ⏱️ Le lien fonctionne une fois, pendant 30 minutes. Un nouveau lien pour le même compte annule les précédents ; un changement du mot de passe ou de l'adresse e-mail du compte — dans le Profil de l'utilisateur, ou avec `user reset` ou `user set-email` — les annule tous.
- 🚪 Une fois le nouveau mot de passe défini, chaque appareil connecté au compte est déconnecté, comme avec `user reset`. La création du lien ne déconnecte personne.
- 🌐 Comme pour les [invitations](#invite), le lien est complet lorsque `LIBREFOLIO_PUBLIC_URL` est défini, et le chemin seul (`/reset-password#token=…`) lorsqu'il ne l'est pas.

### 🔁 Un nouveau lien de configuration pour l'administrateur initial {: #setup-link }

```bash
pipenv run ./dev.py user setup-link
```

Lorsque LibreFolio a créé l'administrateur à partir de `LIBREFOLIO_ADMIN_EMAIL` à son premier démarrage ([L'administrateur initial](configuration_accounts.md#initial-admin)) et que personne n'a encore utilisé son lien de configuration, cette commande en affiche un nouveau : l'administrateur l'ouvre, choisit le mot de passe et est connecté. Utilisez-la lorsque le lien a expiré, a été perdu ou a été annulé.

- ⏱️ Le lien fonctionne une fois, pendant 72 heures. Les liens de configuration émis auparavant cessent de fonctionner, y compris celui de `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`.
- 🚫 Un lien annulé — **Annuler le lien de configuration** dans [Utilisateurs et invitations](users.md#cancel-setup), ou `user deactivate` sur l'administrateur en attente — laisse l'administrateur en attente : cette commande lui donne un nouveau lien.
- 📮 Une nouvelle adresse pour l'administrateur en attente — `LIBREFOLIO_ADMIN_EMAIL` modifié avant un redémarrage, ou [`user set-email`](#set-email) — met fin à ses liens de configuration, qui étaient destinés à l'ancienne adresse. L'administrateur attend toujours : cette commande lui donne un lien pour la nouvelle adresse. La même adresse avec d'autres majuscules des lettres A à Z ne constitue pas un changement, et le lien continue de fonctionner.
- 🔚 Configuré d'une autre manière — activé avec `user activate`, ou doté d'un mot de passe avec `user reset` ou un [lien de réinitialisation](#reset-link) — l'administrateur n'attend plus : ses liens de configuration cessent définitivement de fonctionner, et cette commande s'arrête avec l'erreur ci-dessous.
- 🌐 Comme pour les [invitations](#invite), le lien est complet lorsque `LIBREFOLIO_PUBLIC_URL` est défini, et le chemin seul (`/setup#token=…`) lorsqu'il ne l'est pas.
- 📧 La commande affiche uniquement le lien : elle n'envoie aucun e-mail.
- ❌ Lorsqu'aucun administrateur n'attend sa configuration, la commande s'arrête avec l'erreur `No administrator account is waiting for its setup link` et quitte avec le code `1`. Elle fait de même lorsque l'administrateur termine sa configuration pendant que la commande s'exécute : la commande vérifie à nouveau juste avant d'émettre le lien, et n'en donne aucun à un compte déjà configuré.

### 📧 Changer l'adresse e-mail d'un compte {: #set-email }

```bash
pipenv run ./dev.py user set-email <username> <new_email>
```

Le même changement qu'une nouvelle adresse e-mail dans le [Profil](../user/settings/profile.md#email-change) de l'utilisateur, sans son mot de passe : utilisez-le lorsqu'une personne ne peut pas changer elle-même son adresse, ou pour séparer deux comptes qui en partagent une ([ci-dessous](#email-case-conflict)).

- 🔤 Une adresse n'appartient qu'à un seul compte, quelles que soient ses majuscules : `Anna@example.com` et `anna@example.com` sont la même adresse. Seules les lettres A à Z sont comparées de cette manière ; les lettres accentuées ne le sont pas : `Émile@example.com` et `émile@example.com` sont deux adresses différentes.
- 🚪 Une nouvelle adresse déconnecte le compte de chaque appareil, annule tout lien de réinitialisation de mot de passe encore ouvert et est enregistrée comme non vérifiée ; le compte peut toujours se connecter. L'adresse du compte avec d'autres majuscules est la même adresse : seule son écriture change, personne n'est déconnecté et elle reste vérifiée.
- 👑 Sur l'administrateur initial qui attend encore son lien de configuration, une nouvelle adresse met également fin à ce lien, qui était destiné à l'ancienne adresse : le compte attend toujours, et [`user setup-link`](#setup-link) lui en donne un nouveau. Tant que `LIBREFOLIO_ADMIN_EMAIL` est défini, chaque démarrage du serveur redonne cette adresse au compte en attente : modifiez aussi la variable, sinon le démarrage suivant rétablit l'ancienne adresse et met également fin au nouveau lien.
- ❌ Une adresse qu'un autre compte possède déjà, quelles que soient les majuscules, est refusée : la commande s'arrête avec l'erreur `Email already registered` et quitte avec le code `1`, sans rien changer. Il en va de même pour une adresse qui est le nom d'utilisateur d'un autre compte, quelles que soient les majuscules : un compte créé avant la version 1.3 peut avoir un `@` dans son nom d'utilisateur ([Noms d'utilisateur avec un @](users.md#usernames-with-at)), et une fois que ce nom est l'adresse de quelqu'un, la connexion, qui lit d'abord une adresse, ne trouverait plus ce compte par son nom. Le nom d'utilisateur du compte lui-même n'est pas un obstacle : il peut devenir son adresse. Une adresse qui n'est pas valide (`Not an email address`) ou un nom d'utilisateur inconnu (`User '<username>' not found`) font aussi s'arrêter la commande.
- 📮 Une nouvelle adresse annule aussi tout lien de changement d'e-mail encore en attente pour le compte. Elle ne touche pas au mot de passe.

### 👑 Accorder ou retirer les droits d'administrateur

```bash
pipenv run ./dev.py user promote <username>
pipenv run ./dev.py user demote <username>
```

`demote` refuse le dernier administrateur actif : la commande s'arrête avec l'erreur `User '<username>' is the last active administrator: promote another user first` et quitte avec le code `1`. Une rétrogradation déconnecte le compte de chaque appareil.

### 🧭 Redémarrer les guides d'un utilisateur {: #reset-onboarding }

```bash
# Tous les guides, y compris la configuration d'accueil
pipenv run ./dev.py user reset-onboarding <username>

# Un seul guide
pipenv run ./dev.py user reset-onboarding <username> --flow intro_tour
```

La prochaine fois que l'utilisateur ouvre LibreFolio, la configuration d'accueil et les guides redémarrent, comme lors de sa première visite ; ses données et préférences restent inchangées. `--flow` ne redémarre qu'un seul guide : `pipenv run ./dev.py user reset-onboarding --help` en liste les noms, comme `welcome`, `intro_tour` ou `import_guide`.
`demote` refuse également l'[administrateur initial](configuration_accounts.md#initial-admin) qui attend encore son lien de configuration, car cet administrateur conserve son rôle jusque-là : la commande s'arrête avec l'erreur `User '<username>' is the initial administrator waiting for its setup: it keeps its role until then; deactivate it to cancel its setup link, or delete it from Settings › Administration › Users` et quitte avec le code `1`, sans rien changer. Pour annuler son lien, exécutez `user deactivate` (voir « Réinitialiser un mot de passe ou verrouiller un compte » ci-dessus) ; pour supprimer le compte, supprimez-le dans [Utilisateurs et invitations](users.md#delete), sans rétrogradation préalable : la ligne de commande ne supprime aucun compte.

---

## 🗄️ Entretenir la base de données

### ⬆️ Appliquer les migrations {: #apply-migrations }

Chaque démarrage du serveur applique lui-même les migrations en attente ; vous en avez donc rarement besoin. Pour le faire manuellement, **arrêtez d'abord le serveur** : `db upgrade` refuse de s'exécuter tant que le serveur répond sur le port configuré.

```bash
# Appliquer les migrations en attente
pipenv run ./dev.py db upgrade

# Afficher la migration sur laquelle se trouve la base de données
pipenv run ./dev.py db current

# Rechercher les contraintes CHECK manquantes : ne modifie rien, quitte avec le code `1` s'il en existe
pipenv run ./dev.py db check

# Lister les codes de devise qui ne sont pas des codes ISO : ne modifie rien, quitte avec le code `1` s'il en existe
pipenv run ./dev.py db currencies

# Mettre à niveau et vérifier un autre fichier de base de données, comme une copie
pipenv run ./dev.py db upgrade /path/to/copy/app.db
pipenv run ./dev.py db check /path/to/copy/app.db
```

- 📄 Sans chemin, les commandes utilisent la base de données configurée. Un chemin désigne un autre fichier SQLite : un chemin relatif part de la racine du projet, quel que soit l'endroit d'où vous exécutez la commande. Le fichier doit exister, sauf pour `db upgrade`, qui le crée (dossier compris) et le met à jour.
- 🐳 Dans Docker, le chemin se trouve à l'intérieur du conteneur, où `LibreFolio-data/` correspond à `/app/backend/data/prod-docker` (la base de données est `sqlite/app.db` dans ce répertoire). `db current`, `db check` et `db currencies` fonctionnent dans le conteneur en cours d'exécution : `docker compose exec librefolio python dev.py db current <path>`. `db upgrade` et `db downgrade` nécessitent l'arrêt du serveur (`docker compose stop librefolio`), puis un conteneur ponctuel : `docker compose run --rm librefolio python dev.py db upgrade <path>` ([détails](docker_advanced.md#docker-exec)).

### 🔤 Deux comptes avec la même adresse e-mail {: #email-case-conflict }

À partir de la version 1.3, une adresse e-mail n'appartient qu'à un seul compte, quelles que soient ses majuscules. Une base de données d'une version antérieure peut contenir deux comptes dont les adresses ne diffèrent que par les majuscules, comme `Anna@example.com` et `anna@example.com` : la mise à niveau s'arrête alors à la migration qui vérifie ce point, et le serveur ne démarre pas. Les migrations précédentes restent appliquées, aucun compte n'est modifié, et le démarrage suivant reprend à cette migration. Le journal (ou la sortie de `db upgrade`) nomme les comptes par id et nom d'utilisateur, jamais par adresse ; un `;` sépare un groupe de comptes du suivant :

```text
Email addresses must be unique regardless of case (release 1.3), and these accounts share one apart from upper and lower case: #3 'anna', #8 'anna_work'. Give all but one account of each group another address with …
```

LibreFolio ne fusionne jamais deux comptes : donnez une autre adresse à tous les comptes de chaque groupe sauf un, avec [`user set-email`](#set-email), puis redémarrez LibreFolio :

```bash
pipenv run ./dev.py user set-email <username> <new_email>
```

Dans Docker, le serveur est le processus principal du conteneur ; le conteneur ne reste donc pas actif et il ne faut pas compter sur `docker compose exec` : exécutez plutôt la commande dans un conteneur ponctuel.

```bash
docker compose stop librefolio
docker compose run --rm librefolio python dev.py user set-email <username> <new_email>
docker compose start librefolio
```

### 🩹 Correctifs post-migration {: #post-migration-fixes }

Juste après les migrations, chaque démarrage exécute aussi les **correctifs post-migration** : des réparations qu'une migration ne peut pas effectuer. Habituellement, il n'y a rien à faire. Le journal (la sortie du serveur, également enregistrée dans `logs/`) peut afficher :

- ✅ `Post-migration fixes applied and verified` : une réparation a été effectuée. Sur une base de données volumineuse, ce démarrage est plus lent, une seule fois.
- ⚠️ `Post-migration fix failed` : la base de données a été laissée telle quelle et le serveur a démarré normalement. L'avertissement donne l'erreur et la copie de la base de données conservée à côté jusqu'à ce que vous la supprimiez, par exemple `app.db.pre-autoincrement-20261008T101500Z.bak`. Le correctif est retenté au démarrage suivant.
- 🩺 `Post-migration fixes skipped` : la copie n'a pas pu être faite, ou la base de données échoue au contrôle d'intégrité de SQLite. Rien n'a été modifié.
- 🔗 `Foreign key violations already in the database, left as they are` : la base de données contient des références à des lignes qui n'existent plus, listées dans l'avertissement. Les correctifs les laissent en l'état et s'exécutent quand même : un correctif n'échoue que sur une référence brisée qu'il ajouterait lui-même.

Le fichier vide `app.db.post-migration.lock`, à côté de la base de données, fait que les exécutions se relaient lorsque plusieurs workers démarrent ensemble : laissez-le en place.

Le premier correctif, **`autoincrement`**, garantit que l'id d'une entité supprimée — utilisateur, courtier, actif, transaction, route de conversion FX ou événement d'actif — n'est jamais réattribué à un nouvel élément. Lors de la conversion d'une base de données, il supprime les dossiers de rapports des courtiers qui n'existent plus, afin qu'un nouveau courtier ne puisse pas en hériter.

Le deuxième correctif, **`orphan_pair_halves`**, répare une fois les transferts qu'une suppression antérieure de courtier a laissés sans leur autre moitié sur les courtiers restants :

- 📈 Les titres reçus du courtier supprimé deviennent une position d'ouverture à leur coût de transfert, à partir de la date de transfert. Le capital de ce courtier les compte alors à ce coût au lieu de leur valeur de marché à l'arrivée, si bien que son gain tient aussi compte de ce qu'ils ont gagné avant le transfert. Lorsqu'aucun coût n'a été enregistré, ils restent sans coût et l'application signale une acquisition sans coût d'achat : saisissez le coût dans la transaction.
- 💶 Les virements avec le courtier supprimé deviennent des dépôts ou des retraits : le capital et le gain ne changent pas.
- 📤 Titres envoyés **au** courtier supprimé : juste après les correctifs, au même démarrage, chacun de ces transferts devient un ajustement qui retire les titres du courtier expéditeur. Un tel ajustement n'a pas de valeur : les titres quittent seulement la quantité, et leur coût est compté comme une moins-value réalisée sur ce courtier. Le journal contient une ligne pour chacun (`Lone transfer leg converted to an ADJUSTMENT-out without a value`). Sur une base de données qui échoue au contrôle rapide de SQLite, chacun de ces transferts est laissé en l'état (`Lone transfer legs left as they are: the database failed its quick check`). Si toute l'étape échoue (`Lone transfer legs could not be converted; starting normally`), rien n'est modifié et le serveur démarre quand même.

Le correctif **`event_types`** répare une fois les événements d'actif enregistrés avec un type que LibreFolio ne connaît pas, comme `dividend` ou `dividendo` saisis à la main dans un fichier CSV. Jusqu'à présent, un tel événement faisait échouer le chargement de toute la liste des événements de cet actif, si bien qu'aucun n'était affiché :

- ✅ Un type qui ne diffère que par la casse ou les espaces (`dividend`, ` Split `) est corrigé.
- 🗑️ Un événement dont le type reste inconnu est supprimé. Une transaction qui lui est liée subsiste, sans son événement lié : reliez-la à nouveau au bon événement si nécessaire.

??? tip "⌨️ Exécuter les correctifs manuellement — pour les prévisualiser ou retenter un correctif échoué"

    **Arrêtez d'abord le serveur** (le script ne le vérifie pas), puis exécutez depuis la racine du projet :

    ```bash
    # Aperçu : signaler ce qui serait corrigé, ne rien modifier
    pipenv run python -m backend.app.db.post_migration --dry-run

    # Appliquer les correctifs
    pipenv run python -m backend.app.db.post_migration
    ```

    Le script affiche chaque correctif comme `clean` (rien à faire), `would_apply` (simulation), `applied` ou `failed`, avec les dossiers de courtiers orphelins, une copie conservée et toute erreur, puis une ligne pour chaque transfert de titres envoyé à un courtier supprimé (`Lone transfer leg …`), et quitte avec le code `1` lorsque quelque chose a échoué. `--db PATH` et `--data-dir PATH` le pointent vers une autre base de données ou un autre répertoire de données.

    Pour voir ce que `orphan_pair_halves` modifiera dans votre base de données, prévisualisez-le avant le premier démarrage de la nouvelle version : `--dry-run` affiche `Fix orphan_pair_halves: would_apply` lorsqu'il y a quelque chose à réparer, et un avertissement liste les transactions par id, groupées par conversion (comme `TRANSFER->ADJUSTMENT`), avec celles qui resteront sans coût et les transferts de titres envoyés à un courtier supprimé. Ces transferts reçoivent chacun une ligne après l'application des correctifs (`would become an ADJUSTMENT-out without a value`). Le script affiche aussi, sur la console, ce que le serveur journaliserait : l'avertissement et, lors d'une exécution réelle, une ligne par transaction modifiée (avec `LOG_LEVEL` à `INFO`, la valeur par défaut). Il n'écrit aucun fichier journal : conservez sa sortie si vous voulez garder une trace d'une réparation effectuée manuellement.

🔗 Fonctionnement interne des correctifs : [Schéma de la base de données — Correctifs post-migration](../developer/architecture/database/index.md#post-migration-fixes).

### 💱 Codes de devise qui ne sont pas des codes ISO {: #currency-codes }

À partir de la version 1.3, LibreFolio n'enregistre une devise que sous la forme d'un code alphabétique ISO 4217, comme `EUR` ou `USD`. Les versions antérieures acceptaient aussi le nom d'une devise ou son code numérique, et l'enregistraient tel quel : `Euro`, `978`. Une telle valeur reste lisible, mais une modification qui réenregistre sa ligne est refusée jusqu'à ce que son code soit corrigé, et ses montants ne rejoignent jamais ceux du code ISO : `978` et `EUR` forment deux soldes. Une sauvegarde restaurée peut réintroduire de telles valeurs.

Peu après chaque démarrage, le journal avertit lorsque la base de données en contient, et LibreFolio ne les modifie pas de lui-même :

```text
Stored currency codes that are not ISO 4217 codes: an edit of their rows is refused until they are corrected (./dev.py db currencies lists them)
```

`db currencies` les liste, sans rien modifier :

```bash
# Où chaque valeur est stockée, combien de lignes la contiennent et le code ISO qu'elle représente
pipenv run ./dev.py db currencies

# Un autre fichier de base de données, comme une copie
pipenv run ./dev.py db currencies /path/to/copy/app.db
```

- 🔎 Chaque ligne indique l'emplacement (`transactions.currency`, `assets.currency`, les étapes d'une route FX, les paramètres d'un fournisseur, la devise de base d'un utilisateur…), la valeur, le nombre de lignes qui la contiennent et le code ISO qu'elle représente : `978` correspond à `EUR`, `US DOLLAR` à `USD`.
- ➖ Un tiret signifie qu'il n'existe pas de code unique : un nom partagé par deux devises (`Bolívar Soberano` : `VED` ou `VES`), une valeur qui n'est pas une devise, ou un code qui compte des centimes plutôt que des unités (`GBX`, `ZAC`, `ILA`), lequel ne doit jamais être simplement renommé.
- 🔤 Un code en minuscules ou avec des espaces, comme `eur`, est également listé : la bonne devise, sous une forme que les comparaisons exactes ne repèrent pas.
- 🧱 Une valeur enregistrée sous forme d'octets bruts plutôt que de texte, ou sous forme de texte qui n'est pas un UTF-8 valide, ce que seule une base de données endommagée ou créée à la main contient, est listée dans la notation de SQLite, comme `X'455552'`, avec un tiret : ce n'est jamais un code.
- 🚦 La commande quitte avec le code `0` lorsque tous les codes sont des codes ISO, avec le code `1` lorsqu'elle en liste certains, et avec le code `2` lorsqu'elle ne peut pas lire la base de données.
- 🐳 Dans Docker : `docker compose exec librefolio python dev.py db currencies`.

### 🔧 Ajouter les paramètres globaux manquants

```bash
pipenv run ./dev.py user init-settings
```

Chaque démarrage ajoute les [paramètres globaux](settings.md) manquants avec leurs valeurs par défaut ; cette commande fait de même sans démarrer le serveur, et ne modifie jamais une valeur déjà définie.

### 🧹 Réinitialiser la base de données

```bash
pipenv run ./dev.py db create-clean
```

!!! warning "Toutes les données sont perdues"

    `db create-clean` supprime la base de données et en crée une vide. Comme `db upgrade`, elle refuse de s'exécuter tant que le serveur est actif. Les fichiers téléversés et les rapports de courtiers restent sur le disque : voir [Initialisation et réinitialisation de la base de données](host_installation.md#database-reset).

---

## 📋 Arborescence complète des commandes

```bash
# Toutes les commandes, par catégorie
pipenv run ./dev.py --help

# Les options d'une commande
pipenv run ./dev.py server --help
```

??? info "👩‍💻 Commandes de développement et de documentation"

    - **Frontend** : `pipenv run ./dev.py front build`, `front dev`, `front check` — voir [Développement du frontend](../developer/frontend/index.md)
    - **Tests** : `pipenv run ./dev.py test all` — voir [Parcours de test](../developer/test-walkthrough/index.md)
    - **Client API** : `pipenv run ./dev.py api sync` — voir [Vue d'ensemble de l'API](../developer/api/overview.md)
    - **i18n** : `pipenv run ./dev.py i18n audit` — voir [Internationalisation](../developer/frontend/i18n.md)
    - **Documentation** : `pipenv run ./dev.py mkdocs deploy` publie cette documentation sur GitHub Pages ; `pipenv run ./dev.py mkdocs gallery` régénère ses captures d'écran avec Playwright sur un serveur de test (`--no-populate` conserve les données de test actuelles).

    La boîte à outils complète du développeur se trouve dans le [Guide du workflow développeur](../developer/dev_workflow.md).

---

## 🔗 Voir aussi

- 📄 **[Outils d'administration CLI : sauvegardes](cli_backup.md)** — Sauvegarder l'instance
