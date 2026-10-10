# 🛠️ Outils en ligne de commande

`dev.py`, à la racine du projet, exécute les tâches d'administration : démarrer le serveur, gérer les utilisateurs et maintenir la base de données. Chaque section précise quand une commande nécessite l'arrêt du serveur.

!!! tip "Où exécuter les commandes"

    - **Installation sur hôte** : dans l'environnement Pipenv, avec le préfixe `pipenv run` utilisé sur cette page, ou après `pipenv shell`.
    - **Docker** : dans le conteneur en cours d'exécution, avec `docker compose exec librefolio python dev.py <command>` (depuis une copie des sources, `./dev.py docker exec <command>`). Pas de `pipenv run` ici : l'image installe les dépendances globalement. Les commandes de gestion des utilisateurs, `db current` et `db check` y fonctionnent ; `db upgrade` et `db downgrade` non, car elles nécessitent l'arrêt du serveur ([Appliquer les migrations](#apply-migrations)). Les commandes de développement telles que `test` ne font pas partie de l'image ([détails](docker_advanced.md#docker-exec)).

---

## 🖥️ Démarrer le serveur {: #start-the-server }

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

- 🧮 Davantage de workers permettent de traiter plus de requêtes simultanément : utilisez-les sur toute machine avec plus d'un CPU. `auto` démarre $\max(1,\ 2\,(n-1))$ workers sur $n$ CPU.
- ⏳ Le serveur construit d'abord l'interface web et cette documentation lorsqu'elles sont absentes ou obsolètes, donc le premier démarrage prend quelques minutes. Si l'interface ne se construit pas, le serveur ne démarre pas.
- 🔑 Un redémarrage déconnecte tout le monde, sauf si `JWT_SECRET` est défini dans `.env` (voir [Configuration](configuration.md)).

??? note "⚙️ Autres options du serveur — rarement nécessaires"

    | Option | Ce qu'elle fait |
    | --- | --- |
    | `--host HOST` | Adresse d'écoute (par défaut : `HOST` depuis l'environnement ou `.env`, sinon `0.0.0.0`) |
    | `--data-dir PATH` | Utiliser un autre répertoire de données pour cette exécution, au lieu de `LIBREFOLIO_DATA_DIR` |
    | `--no-scheduler` | Démarrer sans les synchronisations planifiées des prix et des taux de change |
    | `--rebuild`, `-r` | Reconstruire l'interface web même lorsqu'elle semble à jour |
    | `--debug`, `-d` | Journaux `DEBUG` et une compilation de débogage de l'interface web |

    Formes courtes : `-w` pour `--workers`, `-p` pour `--port`, `-f` pour `--force`. `--test`, `--coverage` et `--no-reload` sont des options de développement : `pipenv run ./dev.py server --help` les liste toutes.

---

## 👤 Gérer les utilisateurs

Ces commandes écrivent directement dans la base de données, elles fonctionnent donc aussi pendant que le serveur est en cours d'exécution.

### ➕ Créer et lister les utilisateurs

```bash
# Create an administrator account
pipenv run ./dev.py user create <username> <email> <password>

# List all users: ID, username, email, active, administrator
pipenv run ./dev.py user list
```

- 👑 Les comptes créés ici sont toujours des **administrateurs**. Pour un compte standard, laissez la personne s'inscrire avec **S’inscrire ici** sur la page de connexion (lorsque l'inscription est ouverte dans les [Paramètres globaux](settings.md)), ou utilisez `demote` sur le nouveau compte.
- 🔒 Le mot de passe doit contenir au moins 8 caractères, avec une lettre majuscule, une lettre minuscule, un chiffre et un symbole.

### 🔑 Réinitialiser un mot de passe ou verrouiller un compte {: #reset-a-password-or-lock-an-account }

```bash
# Set a new password (same rules as above)
pipenv run ./dev.py user reset <username> <new_password>

# Lock an account out, then let it back in
pipenv run ./dev.py user deactivate <username>
pipenv run ./dev.py user activate <username>
```

- ⏱️ Une réinitialisation ne met pas fin aux sessions déjà ouvertes : elles restent valides jusqu'à leur expiration. Pour verrouiller quelqu'un immédiatement, désactivez le compte : il est refusé dès sa prochaine requête.
- 💬 L’écran **Mot de passe oublié ?** de l’application affiche cette commande pour les deux installations : `docker compose exec librefolio python dev.py user reset …` pour Docker, et `./dev.py user reset …` pour une installation sur hôte, à exécuter après `pipenv shell` ou avec `pipenv run` devant.

### 👑 Accorder ou retirer les droits d'administrateur

```bash
pipenv run ./dev.py user promote <username>
pipenv run ./dev.py user demote <username>
```

`demote` ne vérifie pas qu'un autre administrateur subsiste : s'il n'en reste aucun, promouvez à nouveau quelqu'un.

---

## 🗄️ Maintenir la base de données

### ⬆️ Appliquer les migrations {: #apply-migrations }

Chaque démarrage du serveur applique lui-même les migrations en attente, vous n'avez donc que rarement besoin de cette commande. Pour le faire manuellement, **arrêtez d'abord le serveur** : `db upgrade` refuse de s'exécuter tant que le serveur répond sur le port configuré.

```bash
# Apply pending migrations
pipenv run ./dev.py db upgrade

# Show the migration the database is at
pipenv run ./dev.py db current

# Look for missing CHECK constraints: changes nothing, exits with 1 if any
pipenv run ./dev.py db check

# Upgrade and check another database file, such as a copy
pipenv run ./dev.py db upgrade /path/to/copy/app.db
pipenv run ./dev.py db check /path/to/copy/app.db
```

- 📄 Sans chemin, les commandes utilisent la base de données configurée. Un chemin désigne un autre fichier SQLite : un chemin relatif part de la racine du projet, quel que soit l'endroit depuis lequel vous exécutez la commande. Le fichier doit exister, sauf pour `db upgrade`, qui le crée (dossier compris) et le met à jour.
- 🐳 Dans Docker, le chemin est à l'intérieur du conteneur, où `LibreFolio-data/` correspond à `/app/backend/data/prod-docker` (la base de données est `sqlite/app.db` à l'intérieur). `db current` et `db check` fonctionnent dans le conteneur en cours d'exécution : `docker compose exec librefolio python dev.py db current <path>`. `db upgrade` et `db downgrade` nécessitent l'arrêt du serveur (`docker compose stop librefolio`), puis un conteneur ponctuel : `docker compose run --rm librefolio python dev.py db upgrade <path>` ([détails](docker_advanced.md#docker-exec)).

### 🩹 Correctifs post-migration {: #post-migration-fixes }

Juste après les migrations, chaque démarrage exécute aussi les **correctifs post-migration** : des réparations qu'une migration ne peut pas effectuer. Habituellement, il n'y a rien à faire. Le journal (la sortie du serveur, également enregistrée dans `logs/`) peut afficher :

- ✅ `Post-migration fixes applied and verified` : une réparation a été effectuée. Sur une grande base de données, ce démarrage est plus lent, une seule fois.
- ⚠️ `Post-migration fix failed` : la base de données a été laissée telle quelle et le serveur a démarré normalement. L'avertissement indique l'erreur et la copie de la base de données conservée à côté jusqu'à ce que vous la supprimiez, par exemple `app.db.pre-autoincrement-20261008T101500Z.bak`. Le correctif est retenté au démarrage suivant.
- 🩺 `Post-migration fixes skipped` : la copie n'a pas pu être effectuée, ou la base de données échoue au contrôle d'intégrité de SQLite. Rien n'a été modifié.

Le fichier vide `app.db.post-migration.lock`, à côté de la base de données, fait que les exécutions se relaient lorsque plusieurs workers démarrent ensemble : laissez-le en place.

Le premier correctif, **`autoincrement`**, garantit que l’id d’une entité supprimée — utilisateur, courtier, actif, transaction, route de conversion FX ou événement d’actif — n’est jamais attribué à une nouvelle entité. Lors de la conversion d’une base de données, il supprime les dossiers de rapports des courtiers qui n’existent plus, afin qu’un nouveau courtier ne puisse pas en hériter.

??? tip "⌨️ Exécuter les correctifs manuellement — pour les prévisualiser ou retenter un échec"

    **Arrêtez d'abord le serveur** (le script ne le vérifie pas), puis exécutez depuis la racine du projet :

    ```bash
    # Preview: report what would be fixed, change nothing
    pipenv run python -m backend.app.db.post_migration --dry-run

    # Apply the fixes
    pipenv run python -m backend.app.db.post_migration
    ```

    Le script affiche chaque correctif comme `clean` (rien à faire), `would_apply` (exécution à blanc), `applied` ou `failed`, avec les dossiers de courtiers orphelins, une copie conservée et toute erreur, et se termine avec `1` lorsqu'un échec s'est produit. `--db PATH` et `--data-dir PATH` le pointent vers une autre base de données ou un autre répertoire de données.

🔗 Comment les correctifs fonctionnent en interne : [Schéma de base de données — Correctifs post-migration](../developer/architecture/database/index.md#post-migration-fixes).

### 🔧 Ajouter les paramètres globaux manquants

```bash
pipenv run ./dev.py user init-settings
```

Chaque démarrage ajoute les [Paramètres globaux](settings.md) manquants avec leurs valeurs par défaut ; cette commande fait de même sans démarrer le serveur, et ne modifie jamais une valeur déjà définie.

### 🧹 Réinitialiser la base de données

```bash
pipenv run ./dev.py db create-clean
```

!!! warning "Toutes les données sont perdues"

    `db create-clean` supprime la base de données et en crée une vide. Comme `db upgrade`, elle refuse de s'exécuter tant que le serveur est actif. Les fichiers téléversés et les rapports de courtier restent sur le disque : voir [Initialisation et réinitialisation de la base de données](host_installation.md#database-reset).

---

## 📋 Arborescence complète des commandes

```bash
# Every command, by category
pipenv run ./dev.py --help

# The options of one command
pipenv run ./dev.py server --help
```

??? info "👩‍💻 Commandes de développement et de documentation"

    - **Frontend** : `pipenv run ./dev.py front build`, `front dev`, `front check` — voir [Développement Frontend](../developer/frontend/index.md)
    - **Tests** : `pipenv run ./dev.py test all` — voir [Parcours de test](../developer/test-walkthrough/index.md)
    - **Client API** : `pipenv run ./dev.py api sync` — voir [Vue d'ensemble de l'API](../developer/api/overview.md)
    - **i18n** : `pipenv run ./dev.py i18n audit` — voir [Internationalisation](../developer/frontend/i18n.md)
    - **Documentation** : `pipenv run ./dev.py mkdocs deploy` publie cette documentation sur GitHub Pages ; `pipenv run ./dev.py mkdocs gallery` régénère ses captures d'écran avec Playwright sur un serveur de test (`--no-populate` conserve les données de test actuelles).

    La boîte à outils complète du développeur se trouve dans le [Guide du flux de travail développeur](../developer/dev_workflow.md).
