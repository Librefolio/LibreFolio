# 🛠️ Outils en ligne de commande

`dev.py` exécute les tâches d'administration : démarrer le serveur, gérer les utilisateurs et les invitations, entretenir la base de données, sauvegarder l'instance. Chaque section indique **où** lancer la commande et quand elle exige que le serveur soit arrêté.

!!! tip "Où exécuter les commandes"

    | Installation | Où | Forme de la commande |
    | --- | --- | --- |
    | **Sur l'hôte** | Terminal sur le serveur, dans le dossier LibreFolio (la racine du projet), environnement Pipenv | `pipenv run ./dev.py <command>` — ou `./dev.py <command>` après `pipenv shell` |
    | **Docker, serveur en cours d'exécution** | Terminal sur l'hôte, dans le dossier de `docker-compose.yml` | `docker compose exec librefolio python dev.py <command>` |
    | **Docker, serveur arrêté** | Même terminal | `docker compose stop librefolio`, puis `docker compose run --rm librefolio python dev.py <command>` (conteneur ponctuel), puis `docker compose start librefolio` |

    - Il n'y a pas de `pipenv run` dans le conteneur : l'image installe les dépendances globalement.
    - `docker compose exec` exécute la commande en tant que root. Depuis une copie du code source, `./dev.py docker exec <command>` l'exécute à la place en tant qu'utilisateur du serveur ([détails](docker_advanced.md#docker-exec)).
    - Les commandes `user`, `db current`, `db check`, `db currencies`, `backup create`, `backup inspect`, `backup restore`, `backup decrypt` et `backup pending` fonctionnent dans l'image ([Sauvegarder avec Docker](cli_backup.md#backup-docker)). `db upgrade` et `db downgrade` exigent que le serveur soit arrêté : c'est donc la troisième forme ([Appliquer les migrations](#apply-migrations)). Les commandes de développement telles que `test` ne font pas partie de l'image.

!!! info "📚 Ce guide est réparti sur plusieurs pages"

    Outre cette page : [Outils d'administration CLI : sauvegardes](cli_backup.md).

---

## 🖥️ Démarrer le serveur {: #start-the-server }

**Sur l'hôte**, dans le terminal du serveur, dossier LibreFolio. Dans Docker, le serveur est le processus principal du conteneur : `docker compose up -d` le démarre.

```bash
# Standard start, one worker
pipenv run ./dev.py server

# Size the workers to the CPUs (`auto` and `0` do the same)
pipenv run ./dev.py server --workers auto

# Or set the number of workers
pipenv run ./dev.py server --workers 4

# Listen on another port (default: PORT from .env, else 6040)
pipenv run ./dev.py server --port 8080

# Kill whatever already holds the port, then start
pipenv run ./dev.py server --force
```

Le serveur répond sur le port choisi (`PORT` de `.env`, sinon 6040).

- 🧮 Davantage de workers traitent plus de requêtes à la fois : utilisez-en sur toute machine dotée de plus d'un CPU. `auto` démarre $\max(1,\ 2\,(n-1))$ workers sur $n$ CPU.
- ⏳ Au premier démarrage, ou lorsqu'elles ne sont plus à jour, le serveur construit l'interface web et cette documentation : cela prend quelques minutes. Si l'interface ne se construit pas, le serveur ne démarre pas.
- 🔑 Un redémarrage déconnecte tout le monde, sauf si `JWT_SECRET` est défini dans `.env` ([Configuration](configuration.md)).
- ⏹️ Ctrl+C arrête proprement le serveur : `dev.py` lui accorde le [budget d'arrêt](configuration_security.md#shutdown) plus 2 secondes (10 secondes par défaut), puis y met fin ; un second Ctrl+C y met fin immédiatement. Un SIGTERM envoyé à `dev.py` seul, par un superviseur de processus par exemple, bénéficie de la même attente : `dev.py` le transmet au serveur.

??? note "⚙️ Autres options du serveur — rarement nécessaires"

    | Option | Ce qu'elle fait |
    | --- | --- |
    | `--host HOST` | Adresse d'écoute (par défaut : `HOST` de l'environnement ou de `.env`, sinon `0.0.0.0`) |
    | `--data-dir PATH` | Un autre répertoire de données pour cette exécution, au lieu de `LIBREFOLIO_DATA_DIR` |
    | `--no-scheduler` | Démarrer sans les synchronisations planifiées des prix et des taux de change |
    | `--rebuild`, `-r` | Reconstruire l'interface web même lorsqu'elle semble à jour |
    | `--debug`, `-d` | Journaux `DEBUG`, compilation de débogage de l'interface web et pages de documentation de l'API (`/api/v1/docs`, `/api/v1/redoc`), désactivés autrement |

    Formes courtes : `-w` pour `--workers`, `-p` pour `--port`, `-f` pour `--force`. `--test`, `--coverage` et `--no-reload` sont des options de développement : `pipenv run ./dev.py server --help` les liste toutes.

---

## 👤 Gérer les utilisateurs

**Sur l'hôte** ou **dans Docker, serveur en cours d'exécution** (première ou deuxième forme du tableau ci-dessus) : ces commandes écrivent directement dans la base de données, elles fonctionnent donc aussi pendant que le serveur tourne.

Dans l'application, les administrateurs gèrent les comptes et les invitations dans **Paramètres › Administration › Utilisateurs** ([Utilisateurs et invitations](users.md)). La ligne de commande sert pour un serveur sans navigateur, ou pour dépasser la [limite d'utilisateurs](configuration_accounts.md#user-limit).

### ➕ Créer et lister les utilisateurs

```bash
# Create an administrator account
pipenv run ./dev.py user create <username> <email> <password>

# Create a regular account
pipenv run ./dev.py user create <username> <email> <password> --role user

# List all users: ID, username, email, active, administrator
pipenv run ./dev.py user list
```

`user list` affiche, pour chaque compte : ID, nom d'utilisateur, adresse e-mail, actif, administrateur.

- 👑 `user create` crée un **administrateur** ; avec `--role user`, un compte ordinaire. Les personnes peuvent aussi s'inscrire elles-mêmes : **Inscrivez-vous ici** sur la page de connexion tant que **Inscription** est **Ouverte** (sur une nouvelle instance, également jusqu'à ce que le premier compte existe), ou avec un [lien d'invitation](#invite) ([Qui peut s'inscrire](settings.md#registration)).
- 🔒 Mot de passe : mêmes règles que dans l'application et l'API. Au moins 8 caractères, avec une lettre majuscule, une lettre minuscule, un chiffre et un symbole. Les lettres et chiffres de tout alphabet comptent (`É`, `é`) ; un symbole est tout caractère qui n'est ni une lettre, ni un chiffre, ni un espace (`!`, `_`, `€`). Un mot de passe invalide ne change rien : la commande affiche `Password does not meet security requirements:` et une ligne par règle non respectée, commençant par le code de la règle (`digit: the password must contain a digit`), puis quitte avec le code `1`.
- 🔤 Nom d'utilisateur : de 3 à 50 caractères, sans `@` (à la connexion, tout ce qui contient un `@` est lu comme une adresse e-mail). Les espaces, les lettres accentuées, `.`, `_`, `-`, `+` sont acceptés. Erreurs, chacune avec le code de sortie `1` et sans rien changer : `A username cannot contain @: the sign-in reads it as an email address` ; `A username must be 3 to 50 characters long` ; `Username already taken` ; `Email already registered` si un autre compte possède cette adresse, ou si l'adresse est le nom d'utilisateur d'un autre compte ([`user set-email`](#set-email)), quelles que soient les majuscules.
- 📏 À la [limite d'utilisateurs](configuration_accounts.md#user-limit), `user create` avertit `The instance is at its limit (LIBREFOLIO_MAX_USERS: 5 of 5 places taken): the command line creates the account anyway`, puis crée le compte : la ligne de commande est le moyen de dépasser la limite.

### ✉️ Inviter quelqu'un {: #invite }

```bash
# An invitation link for a regular account
pipenv run ./dev.py user invite

# An invitation for an administrator, with a note of whom it is for
pipenv run ./dev.py user invite --admin --email anna@example.com
```

La commande affiche un lien qui ne fonctionne qu'une fois, pendant 7 jours : envoyez-le à la personne, qui l'ouvre et crée son propre compte avec le nom d'utilisateur, l'adresse e-mail et le mot de passe qu'elle choisit ([ce qu'elle voit](../user/getting-started.md#invitation-link)).

- 👑 `--admin` : le nouveau compte est un administrateur ; sans cette option, un compte ordinaire.
- ✉️ `--email` : simple indication de la personne visée par l'invitation ; elle peut s'inscrire avec une autre adresse.
- 🌐 Lorsque [`LIBREFOLIO_PUBLIC_URL`](configuration_accounts.md#accounts) est défini, le lien est complet (`https://librefolio.example.com/invite#token=…`). Sans cela, la commande affiche uniquement le chemin, `/invite#token=…`, et vous rappelle de placer l'adresse du serveur devant (`http://192.168.1.10:6040`). Si la variable est définie mais n'est pas une adresse `http://` ou `https://`, le rappel indique `LIBREFOLIO_PUBLIC_URL is not valid (…)`, avec la raison. Cela vaut pour tous les liens de cette page.
- 🔒 La partie secrète vient après `#` : les navigateurs ne l'envoient jamais au serveur, elle ne se retrouve donc pas dans les journaux du serveur ou du proxy. Envoyez le lien en entier.
- 🚪 Les invitations fonctionnent avec **Inscription** **Ouverte** ou **Sur invitation**. Avec **Fermée**, la commande s'arrête avec `Registration is disabled: invitations cannot be created` et quitte avec le code `1` ; les liens déjà envoyés ne fonctionnent pas non plus.
- 📏 Une invitation occupe une place de la [limite d'utilisateurs](configuration_accounts.md#user-limit) jusqu'à ce qu'elle soit utilisée, révoquée ou expirée. À la limite, la commande avertit, puis crée quand même l'invitation.
- ⏳ Aucune commande n'annule une invitation : un lien que personne n'a utilisé expire après 7 jours. Plus tôt, **Révoquer** dans l'onglet [Utilisateurs](users.md#account-links), ou via l'API : `GET /api/v1/users/account-links` liste chaque lien de compte avec son état, `DELETE /api/v1/users/account-links/<id>` en révoque un ouvert.

### 🔑 Réinitialiser un mot de passe ou verrouiller un compte {: #reset-a-password-or-lock-an-account }

```bash
# Set a new password (same rules as above)
pipenv run ./dev.py user reset <username> <new_password>

# Lock an account out, then let it back in
pipenv run ./dev.py user deactivate <username>
pipenv run ./dev.py user activate <username>
```

`reset` change le mot de passe immédiatement ; `deactivate` refuse le compte dès sa prochaine requête.

- ⏱️ `reset` met fin aux sessions ouvertes : chaque appareil est déconnecté à sa prochaine requête. Pour bloquer quelqu'un durablement, `deactivate` : réactiver le compte ne restaure pas ses anciennes sessions.
- 🔗 `reset` annule aussi tout [lien de réinitialisation](#reset-link) encore ouvert pour le compte, quel qu'en soit le créateur.
- 👑 `deactivate` refuse le dernier administrateur actif : `User '<username>' is the last active administrator: promote or activate another administrator first`, code de sortie `1`.
- 📏 À la [limite d'utilisateurs](configuration_accounts.md#user-limit), `activate` sur un compte désactivé avertit `… the command line reactivates the account anyway`, puis le réactive. Aucun avertissement pour un compte qui occupe déjà sa place : un compte qui attend son e-mail avec un lien actif, ou l'administrateur initial qui attend son lien de configuration.
- 📬 Lorsque la vérification de l'e-mail est activée, `activate` laisse entrer immédiatement un compte qui attend son e-mail et `deactivate` met fin à l'attente : dans les deux cas, ses liens de vérification cessent de fonctionner (*Vérification de l'adresse e-mail* dans [E-mail](email.md)).
- 🏁 Sur l'[administrateur initial](configuration_accounts.md#initial-admin) qui attend encore son lien de configuration, `reset` et `activate` le configurent sans le lien et mettent définitivement fin à l'attente : ses liens de configuration sont invalidés, y compris celui de `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`, et ni [`user setup-link`](#setup-link) ni un nouveau `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` ne lui en donnent un autre. `activate` seul laisse un compte actif dont personne ne connaît le mot de passe, jusqu'à ce que `reset` ou un [lien de réinitialisation](#reset-link) lui en donne un ; `reset` seul le laisse inactif, jusqu'à ce que vous interveniez avec `activate`.
- 🚫 Sur ce même administrateur en attente, `deactivate` ne configure rien : elle annule le lien de configuration, comme le fait **Annuler le lien de configuration** dans [Utilisateurs et invitations](users.md#cancel-setup). Elle affiche `✅ User '<username>' deactivated` ; tous les liens de configuration du compte sont invalidés, y compris celui de `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`, et le compte continue d'attendre : [`user setup-link`](#setup-link) lui en donne un nouveau, tout comme un **nouveau** `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` au démarrage suivant. Le même jeton, lors d'un redémarrage, n'en donne aucun : l'instance l'a déjà vu.
- 💬 L'écran **Mot de passe oublié ?** de l'application affiche cette commande pour les deux installations : pour Docker, la ligne `docker compose exec librefolio sh -c 'exec gosu …' sh user reset …` (celle de [`docker exec`](docker_advanced.md#docker-exec), exécutée en tant qu'utilisateur du serveur, et non root) ; pour l'hôte, `./dev.py user reset …`, après `pipenv shell` ou précédée de `pipenv run`. Lorsque l'instance peut envoyer un lien de réinitialisation par e-mail, l'écran affiche seulement le formulaire d'e-mail, sans les commandes ([Mots de passe oubliés](email_flows.md#forgot-password)).

### 🔗 Envoyer un lien de réinitialisation de mot de passe {: #reset-link }

```bash
pipenv run ./dev.py user reset-link <username>
```

La commande affiche un lien : la personne l'ouvre et choisit elle-même le nouveau mot de passe, au lieu de recevoir celui que vous avez choisi avec `user reset` ([ce qu'elle voit](../user/getting-started.md#password-reset-link)).

- ⏱️ Le lien ne fonctionne qu'une fois, pendant 30 minutes. Un nouveau lien pour le même compte annule les précédents ; un changement du mot de passe ou de l'adresse e-mail du compte — dans le Profil de l'utilisateur, ou avec `user reset` ou `user set-email` — les annule tous.
- 🚪 Une fois le nouveau mot de passe défini, chaque appareil connecté est déconnecté, comme avec `user reset`. La création du lien ne déconnecte personne.
- 🌐 Lien complet avec `LIBREFOLIO_PUBLIC_URL`, le chemin seul (`/reset-password#token=…`) sans elle ([comme pour les invitations](#invite)).

### 🔁 Un nouveau lien de configuration pour l'administrateur initial {: #setup-link }

```bash
pipenv run ./dev.py user setup-link
```

La commande affiche un nouveau lien de configuration pour l'administrateur créé à partir de `LIBREFOLIO_ADMIN_EMAIL` au premier démarrage ([L'administrateur initial](configuration_accounts.md#initial-admin)), tant que personne n'a utilisé le sien : il l'ouvre, choisit le mot de passe et est connecté. Utilisez-la lorsque le lien a expiré, a été perdu ou a été annulé.

- ⏱️ Le lien ne fonctionne qu'une fois, pendant 72 heures. Les liens de configuration précédents sont invalidés, y compris celui de `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`.
- 🚫 Après une annulation — **Annuler le lien de configuration** dans [Utilisateurs et invitations](users.md#cancel-setup), ou `user deactivate` sur l'administrateur en attente — l'administrateur attend toujours : cette commande lui donne un nouveau lien.
- 📮 Après une nouvelle adresse pour l'administrateur en attente — `LIBREFOLIO_ADMIN_EMAIL` modifié avant un redémarrage, ou [`user set-email`](#set-email) — ses liens, envoyés à l'ancienne adresse, sont invalidés : cette commande lui donne un lien pour la nouvelle. La même adresse avec d'autres majuscules des lettres A à Z ne constitue pas un changement : le lien continue de fonctionner.
- 🔚 Configuré d'une autre manière — `user activate`, ou un mot de passe donné par `user reset` ou par un [lien de réinitialisation](#reset-link) — l'administrateur n'attend plus : ses liens sont invalidés définitivement et la commande s'arrête avec l'erreur ci-dessous.
- 🌐 Lien complet avec `LIBREFOLIO_PUBLIC_URL`, le chemin seul (`/setup#token=…`) sans elle ([comme pour les invitations](#invite)).
- 📧 La commande affiche uniquement le lien : elle n'envoie aucun e-mail.
- ❌ Sans administrateur en attente, la commande s'arrête avec `No administrator account is waiting for its setup link` et quitte avec le code `1`. Il en va de même si l'administrateur termine sa configuration pendant que la commande s'exécute : elle vérifie à nouveau juste avant d'émettre le lien et n'en donne aucun à un compte déjà configuré.

### 📧 Changer l'adresse e-mail d'un compte {: #set-email }

```bash
pipenv run ./dev.py user set-email <username> <new_email>
```

Le même changement qu'une nouvelle adresse e-mail dans le [Profil](../user/settings/profile.md#email-change) de l'utilisateur, sans son mot de passe : pour une personne qui ne peut pas changer elle-même son adresse, ou pour séparer deux comptes qui en partagent une ([ci-dessous](#email-case-conflict)).

- 🔤 Une adresse n'appartient qu'à un seul compte, quelles que soient ses majuscules : `Anna@example.com` et `anna@example.com` sont la même adresse. Seules les lettres A à Z sont comparées de cette manière, pas les lettres accentuées : `Émile@example.com` et `émile@example.com` sont deux adresses différentes.
- 🚪 Une nouvelle adresse déconnecte le compte de chaque appareil, annule tout lien de réinitialisation de mot de passe et tout lien de changement d'e-mail en attente, et est enregistrée comme non vérifiée ; le compte peut toujours se connecter. Elle ne touche pas au mot de passe. La même adresse avec d'autres majuscules ne change que son écriture : personne n'est déconnecté et elle reste vérifiée.
- 👑 Sur l'administrateur initial qui attend encore son lien de configuration, la nouvelle adresse invalide aussi ce lien : le compte attend toujours, et [`user setup-link`](#setup-link) lui en donne un nouveau. Tant que `LIBREFOLIO_ADMIN_EMAIL` est défini, chaque démarrage du serveur redonne cette adresse au compte en attente : modifiez aussi la variable, sinon le démarrage suivant rétablit l'ancienne adresse et invalide aussi le nouveau lien.
- ❌ Refusé, avec le code de sortie `1` et sans rien changer : une adresse qu'un autre compte possède déjà, quelles que soient les majuscules (`Email already registered`) ; une adresse qui est le nom d'utilisateur d'un autre compte, quelles que soient les majuscules (même erreur : un compte créé avant la version 1.3 peut avoir un `@` dans son nom d'utilisateur, [Noms d'utilisateur avec un @](users.md#usernames-with-at), et si ce nom devenait l'adresse de quelqu'un, la connexion, qui lit d'abord une adresse, ne trouverait plus ce compte) ; une adresse invalide (`Not an email address`) ; un nom d'utilisateur inconnu (`User '<username>' not found`). Le nom d'utilisateur du compte lui-même n'est pas un obstacle : il peut devenir son adresse.

### 👑 Accorder ou retirer les droits d'administrateur

```bash
pipenv run ./dev.py user promote <username>
pipenv run ./dev.py user demote <username>
```

Une rétrogradation déconnecte le compte de chaque appareil.

- 👑 `demote` refuse le dernier administrateur actif : `User '<username>' is the last active administrator: promote another user first`, code de sortie `1`.
- 🏁 `demote` refuse aussi l'[administrateur initial](configuration_accounts.md#initial-admin) qui attend encore son lien de configuration et qui conserve son rôle jusque-là : `User '<username>' is the initial administrator waiting for its setup: it keeps its role until then; deactivate it to cancel its setup link, or delete it from Settings › Administration › Users`, code de sortie `1`, sans rien changer. Pour annuler son lien : `user deactivate` ([ci-dessus](#reset-a-password-or-lock-an-account)). Pour supprimer le compte : supprimez-le dans [Utilisateurs et invitations](users.md#delete), sans rétrogradation préalable. La ligne de commande ne supprime aucun compte.

### 🧭 Redémarrer les guides d'un utilisateur {: #reset-onboarding }

```bash
# Every guide, the Welcome setup included
pipenv run ./dev.py user reset-onboarding <username>

# One guide only
pipenv run ./dev.py user reset-onboarding <username> --flow intro_tour
```

La prochaine fois que l'utilisateur ouvre LibreFolio, la configuration d'accueil et les guides redémarrent, comme lors de sa première visite ; ses données et ses préférences restent. `--flow` ne redémarre qu'un seul guide : `pipenv run ./dev.py user reset-onboarding --help` en liste les noms (`welcome`, `intro_tour`, `import_guide`…).

---

## 🗄️ Entretenir la base de données

### ⬆️ Appliquer les migrations {: #apply-migrations }

Chaque démarrage du serveur applique lui-même les migrations en attente : vous avez rarement besoin de le faire à la main.

**Sur l'hôte**, dans le terminal du serveur, dossier LibreFolio, **serveur arrêté** : `db upgrade` refuse de s'exécuter tant que le serveur répond sur le port configuré. `db current`, `db check` et `db currencies` ne changent rien et fonctionnent aussi serveur démarré.

```bash
# Apply pending migrations
pipenv run ./dev.py db upgrade

# Show the migration the database is at
pipenv run ./dev.py db current

# Look for missing CHECK constraints: changes nothing, exits with 1 if any
pipenv run ./dev.py db check

# List the currency codes that are not ISO codes: changes nothing, exits with 1 if any
pipenv run ./dev.py db currencies

# Upgrade and check another database file, such as a copy
pipenv run ./dev.py db upgrade /path/to/copy/app.db
pipenv run ./dev.py db check /path/to/copy/app.db
```

`db upgrade` amène la base de données à la dernière migration ; `db current` affiche celle sur laquelle elle se trouve.

- 📄 Sans chemin, les commandes utilisent la base de données configurée. Un chemin désigne un autre fichier SQLite : un chemin relatif part de la racine du projet, quel que soit le dossier d'où vous lancez la commande. Le fichier doit exister, sauf pour `db upgrade`, qui le crée (dossier compris) et le met à jour.
- 🐳 **Dans Docker**, le chemin se trouve à l'intérieur du conteneur : `LibreFolio-data/` correspond à `/app/backend/data/prod-docker`, la base de données est `sqlite/app.db` dans ce dossier. `db current`, `db check` et `db currencies` : serveur en cours d'exécution, `docker compose exec librefolio python dev.py db current <path>`. `db upgrade` et `db downgrade` : serveur arrêté (`docker compose stop librefolio`), puis un conteneur ponctuel, `docker compose run --rm librefolio python dev.py db upgrade <path>` ([détails](docker_advanced.md#docker-exec)).

### 🔤 Deux comptes avec la même adresse e-mail {: #email-case-conflict }

À partir de la version 1.3, une adresse e-mail n'appartient qu'à un seul compte, quelles que soient ses majuscules. Si une base de données antérieure contient deux comptes dont les adresses ne diffèrent que par les majuscules (`Anna@example.com` et `anna@example.com`), la mise à niveau s'arrête à la migration qui vérifie ce point et le serveur ne démarre pas. Les migrations précédentes restent appliquées, aucun compte n'est modifié, le démarrage suivant reprend à partir de là. Le journal (ou la sortie de `db upgrade`) nomme les comptes par id et nom d'utilisateur, jamais par adresse ; un `;` sépare un groupe du suivant :

```text
Email addresses must be unique regardless of case (release 1.3), and these accounts share one apart from upper and lower case: #3 'anna', #8 'anna_work'. Give all but one account of each group another address with …
```

LibreFolio ne fusionne jamais deux comptes : donnez une autre adresse à tous les comptes de chaque groupe sauf un, puis redémarrez LibreFolio.

=== "Sur l'hôte"

    Dans le terminal du serveur, dossier LibreFolio :

    ```bash
    pipenv run ./dev.py user set-email <username> <new_email>
    ```

=== "Docker"

    Dans le dossier de `docker-compose.yml`. Le serveur est le processus principal du conteneur : le conteneur ne reste donc pas actif et `docker compose exec` ne sert à rien. Utilisez un conteneur ponctuel.

    ```bash
    docker compose stop librefolio
    docker compose run --rm librefolio python dev.py user set-email <username> <new_email>
    docker compose start librefolio
    ```

### 🩹 Correctifs post-migration {: #post-migration-fixes }

Juste après les migrations, chaque démarrage exécute les **correctifs post-migration** : des réparations qu'une migration ne peut pas effectuer. Habituellement, il n'y a rien à faire. Dans le journal (la sortie du serveur, également enregistrée dans `logs/`), vous pouvez lire :

| Ligne du journal | Signification |
| --- | --- |
| ✅ `Post-migration fixes applied and verified` | Une réparation a été effectuée. Sur une base de données volumineuse, ce démarrage est plus lent, une seule fois. |
| ⚠️ `Post-migration fix failed` | Base de données laissée telle quelle, serveur démarré normalement. L'avertissement donne l'erreur et la copie de la base de données conservée à côté de l'original jusqu'à ce que vous la supprimiez (`app.db.pre-autoincrement-20261008T101500Z.bak`). Le correctif est retenté au démarrage suivant. |
| 🩺 `Post-migration fixes skipped` | La copie n'a pas pu être faite, ou la base de données échoue au contrôle d'intégrité de SQLite. Rien n'a été modifié. |
| 🔗 `Foreign key violations already in the database, left as they are` | La base de données contient des références à des lignes qui n'existent plus, listées dans l'avertissement. Les correctifs les laissent en l'état et s'exécutent quand même : un correctif n'échoue que sur une référence brisée qu'il ajouterait lui-même. |

Le fichier vide `app.db.post-migration.lock`, à côté de la base de données, fait que les exécutions se relaient lorsque plusieurs workers démarrent ensemble : laissez-le en place.

Les correctifs :

- **`autoincrement`** : l'id d'un utilisateur, d'un courtier, d'un actif, d'une transaction, d'une route de conversion FX ou d'un événement d'actif supprimé n'est jamais réattribué. Lors de la conversion, il supprime les dossiers de rapports des courtiers qui n'existent plus, afin qu'un nouveau courtier ne puisse pas en hériter.
- **`orphan_pair_halves`**, une fois : répare les transferts qu'une suppression de courtier a laissés sans leur autre moitié sur les courtiers restants.
    - 📈 Titres reçus du courtier supprimé → position d'ouverture au coût du transfert, à partir de la date du transfert. Le capital de ce courtier les compte à ce coût, non à leur valeur de marché à l'arrivée, si bien que son gain tient aussi compte de ce qu'ils ont gagné avant le transfert. Sans coût enregistré, ils restent sans coût et l'application signale une acquisition sans valeur d'achat : saisissez le coût dans la transaction.
    - 💶 Transferts d'argent avec le courtier supprimé → dépôts ou retraits : le capital et le gain ne changent pas.
    - 📤 Titres envoyés **au** courtier supprimé : juste après les correctifs, au même démarrage, chaque transfert devient un ajustement qui retire les titres du courtier expéditeur, sans valeur : seule la quantité diminue, et le coût est compté comme une moins-value réalisée sur ce courtier. Une ligne de journal chacun (`Lone transfer leg converted to an ADJUSTMENT-out without a value`). Si la base de données échoue au contrôle rapide de SQLite, ils restent en l'état (`Lone transfer legs left as they are: the database failed its quick check`). Si toute l'étape échoue (`Lone transfer legs could not be converted; starting normally`), rien n'est modifié et le serveur démarre quand même.
- **`event_types`**, une fois : répare les événements d'actif dont le type est inconnu de LibreFolio, comme `dividend` ou `dividendo` saisis à la main dans un fichier CSV. Jusqu'à présent, un tel événement faisait échouer le chargement de toute la liste des événements de l'actif, si bien qu'aucun n'était affiché.
    - ✅ Un type qui ne diffère que par la casse ou les espaces (`dividend`, ` Split `) est corrigé.
    - 🗑️ Un événement dont le type reste inconnu est supprimé. Une transaction liée subsiste, sans son événement : reliez-la au bon événement si nécessaire.

??? tip "⌨️ Exécuter les correctifs manuellement — pour les prévisualiser ou retenter un correctif échoué"

    **Sur l'hôte**, dans le terminal du serveur, dossier LibreFolio, **serveur arrêté** (le script ne le vérifie pas). Dans Docker : [Correctifs post-migration, serveur arrêté](docker_advanced.md#post-migration-fixes).

    ```bash
    # Preview: report what would be fixed, change nothing
    pipenv run python -m backend.app.db.post_migration --dry-run

    # Apply the fixes
    pipenv run python -m backend.app.db.post_migration
    ```

    Le script affiche chaque correctif comme `clean` (rien à faire), `would_apply` (simulation), `applied` ou `failed`, avec les dossiers de courtiers orphelins, une copie conservée et toute erreur, puis une ligne pour chaque transfert de titres envoyé à un courtier supprimé (`Lone transfer leg …`) ; il quitte avec le code `1` lorsque quelque chose a échoué. `--db PATH` et `--data-dir PATH` le pointent vers une autre base de données ou un autre répertoire de données.

    Pour voir ce que `orphan_pair_halves` fera sur votre base de données, lancez `--dry-run` avant le premier démarrage de la nouvelle version : il affiche `Fix orphan_pair_halves: would_apply` lorsqu'il y a quelque chose à réparer, et un avertissement liste les transactions par id, groupées par conversion (`TRANSFER->ADJUSTMENT`), avec celles qui resteront sans coût et les transferts de titres envoyés à un courtier supprimé ; ces derniers reçoivent chacun une ligne après les correctifs (`would become an ADJUSTMENT-out without a value`). Le script affiche sur la console ce que le serveur écrirait dans le journal : l'avertissement et, lors d'une exécution réelle, une ligne par transaction modifiée (avec `LOG_LEVEL` à `INFO`, la valeur par défaut). Il n'écrit aucun fichier journal : conservez sa sortie si vous voulez garder une trace de la réparation.

🔗 Fonctionnement interne des correctifs : [Schéma de la base de données — Correctifs post-migration](../developer/architecture/database/index.md#post-migration-fixes).

### 💱 Codes de devise qui ne sont pas des codes ISO {: #currency-codes }

À partir de la version 1.3, LibreFolio n'enregistre une devise que sous la forme d'un code alphabétique ISO 4217 (`EUR`, `USD`). Les versions antérieures acceptaient aussi le nom ou le code numérique et l'enregistraient tel quel : `Euro`, `978`. Une telle valeur reste lisible, mais une modification qui réenregistre sa ligne est refusée jusqu'à ce que le code soit corrigé, et ses montants ne sont pas additionnés à ceux du code ISO : `978` et `EUR` forment deux soldes. Une sauvegarde restaurée peut réintroduire de telles valeurs.

Peu après chaque démarrage, le journal avertit lorsque la base de données en contient ; LibreFolio ne les modifie pas de lui-même :

```text
Stored currency codes that are not ISO 4217 codes: an edit of their rows is refused until they are corrected (./dev.py db currencies lists them)
```

**Sur l'hôte** ou **dans Docker, serveur en cours d'exécution** (`docker compose exec librefolio python dev.py db currencies`) :

```bash
# Where each value is stored, how many rows hold it, and the ISO code it stands for
pipenv run ./dev.py db currencies

# Another database file, such as a copy
pipenv run ./dev.py db currencies /path/to/copy/app.db
```

La commande liste les valeurs sans rien modifier.

- 🔎 Chaque ligne indique l'emplacement (`transactions.currency`, `assets.currency`, les étapes d'une route FX, les paramètres d'un fournisseur, la devise de base d'un utilisateur…), la valeur, le nombre de lignes qui la contiennent et le code ISO qu'elle représente : `978` correspond à `EUR`, `US DOLLAR` à `USD`.
- ➖ Un tiret : pas de code unique. Un nom que deux devises partagent (`Bolívar Soberano` : `VED` ou `VES`), une valeur qui n'est pas une devise, ou un code qui compte des centimes plutôt que des unités (`GBX`, `ZAC`, `ILA`), à ne jamais simplement renommer.
- 🔤 Un code en minuscules ou avec des espaces (`eur`) est également listé : la bonne devise, sous une forme que les comparaisons exactes ne repèrent pas.
- 🧱 Une valeur enregistrée sous forme d'octets bruts ou de texte qui n'est pas un UTF-8 valide, ce que seule une base de données endommagée ou créée à la main contient, apparaît dans la notation de SQLite (`X'455552'`) avec un tiret : ce n'est jamais un code.
- 🚦 Code de sortie `0` lorsque tous les codes sont des codes ISO, `1` lorsqu'elle en liste certains, `2` lorsqu'elle ne peut pas lire la base de données.

### 🔧 Ajouter les paramètres globaux manquants

**Sur l'hôte** ou **dans Docker, serveur en cours d'exécution** :

```bash
pipenv run ./dev.py user init-settings
```

Ajoute les [paramètres globaux](settings.md) manquants avec leurs valeurs par défaut, comme le fait chaque démarrage, mais sans démarrer le serveur ; elle ne modifie jamais une valeur déjà définie.

### 🧹 Réinitialiser la base de données

**Sur l'hôte**, dans le terminal du serveur, dossier LibreFolio, **serveur arrêté** :

```bash
pipenv run ./dev.py db create-clean
```

!!! warning "Toutes les données seront perdues"

    `db create-clean` supprime la base de données et en crée une vide. Comme `db upgrade`, elle refuse de s'exécuter tant que le serveur est actif. Les fichiers téléversés et les rapports de courtiers restent sur le disque : [Initialisation et réinitialisation de la base de données](host_installation.md#database-reset).

---

## 📋 Arborescence complète des commandes

```bash
# Every command, by category
pipenv run ./dev.py --help

# The options of one command
pipenv run ./dev.py server --help
```

??? info "👩‍💻 Commandes de développement et de documentation"

    - **Frontend** : `pipenv run ./dev.py front build`, `front dev`, `front check` — [Développement du frontend](../developer/frontend/index.md)
    - **Tests** : `pipenv run ./dev.py test all` — [Parcours de test](../developer/test-walkthrough/index.md)
    - **Client API** : `pipenv run ./dev.py api sync` — [Vue d'ensemble de l'API](../developer/api/overview.md)
    - **i18n** : `pipenv run ./dev.py i18n audit` — [Internationalisation](../developer/frontend/i18n.md)
    - **Documentation** : `pipenv run ./dev.py mkdocs deploy` publie cette documentation sur GitHub Pages ; `pipenv run ./dev.py mkdocs gallery` régénère les captures d'écran avec Playwright sur un serveur de test (`--no-populate` conserve les données de test actuelles).

    La boîte à outils complète du développeur : [Guide du workflow développeur](../developer/dev_workflow.md).

---

## 🔗 Voir aussi

- 📄 **[Outils d'administration CLI : sauvegardes](cli_backup.md)** — Sauvegarder l'instance
