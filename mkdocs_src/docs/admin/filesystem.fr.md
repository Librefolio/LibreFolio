# 📂 Structure du système de fichiers

Tout ce que LibreFolio conserve se trouve dans un seul **répertoire de données** : base de données, fichiers téléversés, rapports de courtiers, journaux et clé d'instance.
Le connaître est tout ce qu'il vous faut pour les sauvegardes et la maintenance.

**Où il se trouve.** Dans la suite de la page, `<data>` désigne ce dossier :

| Installation | `<data>` sur l'hôte | `<data>` à l'intérieur du conteneur |
| --- | --- | --- |
| Hôte (Pipenv) | `backend/data/prod/` dans le dossier du projet, ou le chemin indiqué dans `LIBREFOLIO_DATA_DIR` | — |
| Docker Compose | `LibreFolio-data/` à côté de `docker-compose.yml` | `/app/backend/data/prod-docker` |

---

## 🗂️ Arborescence des répertoires

```text
backend/data/
├── 📂 prod/                          # Production data (default)
│   ├── 🗃️ sqlite/
│   │   └── 📄 app.db                 # Main SQLite database (WAL mode)
│   ├── 🖼️ custom-uploads/            # Files uploaded in the app
│   ├── 📊 broker_reports/
│   │   ├── 📥 uploaded/              # Reports waiting to be read
│   │   ├── ✅ parsed/                # Reports read successfully
│   │   └── ❌ failed/                # Reports that could not be read
│   ├── 📝 logs/                      # Application log files
│   ├── 💾 backups/                   # Backups kept by LibreFolio, one folder each
│   ├── 🎭 scenario_catalog/          # Optional: your own stress scenarios
│   ├── 🗄️ cache/                     # Safe to delete: PDF preview fonts, fetched again
│   ├── 🔐 secrets/                   # Created when LibreFolio first needs the key
│   │   └── 🔑 instance.key           # The instance key: back it up, never change it
│   └── 📋 scheduler_state.json       # Scheduled syncs: last run, pending retry
│
└── 🧪 test/                          # Test data (completely isolated)
    ├── 🗃️ sqlite/app.db
    ├── 🖼️ custom-uploads/
    ├── 📊 broker_reports/
    └── 📝 logs/
```

| Dossier | Ce qu'il contient | Qui l'écrit ou le lit |
| --- | --- | --- |
| 🗃️ `sqlite/` | `app.db` : utilisateurs, courtiers, transactions, actifs, prix, taux de change, paramètres | Le serveur |
| 🖼️ `custom-uploads/` | Les fichiers téléversés dans l'application (comme ceux de la page **Fichiers**) et les avatars par défaut | L'application |
| 📊 `broker_reports/` | Les rapports de courtiers téléversés, un dossier `broker_<id>/` par courtier | L'importation |
| 📝 `logs/` | `librefolio.log` et ses archives hebdomadaires | Le serveur écrit, vous lisez |
| 💾 `backups/` | Les sauvegardes conservées sur le serveur, un dossier chacune | Sauvegarde et restauration |
| 🎭 `scenario_catalog/` | Vos propres scénarios de stress, si vous en avez ajouté | Vous |
| 🗄️ `cache/` | Des copies qui peuvent être téléchargées à nouveau (`pdf-fonts/`) | L'aperçu PDF |
| 🔐 `secrets/` | `instance.key`, la clé d'instance | LibreFolio, la première fois qu'il a besoin de la clé |
| 📋 `scheduler_state.json` | Dernière exécution et nouvelle tentative en attente des synchronisations planifiées | Les synchronisations planifiées |

---

## 📖 Contenu de chaque répertoire

### 🗃️ `sqlite/`

- 📎 `app.db-wal` et `app.db-shm` : fichiers de travail de SQLite (mode WAL), présents pendant que le serveur tourne. Ne copiez jamais `app.db` seul tant que le serveur est démarré.
- 🔒 `app.db.post-migration.lock` : fichier vide utilisé au démarrage, laissez-le en place.
- 🗑️ `app.db.pre-<fix>-<UTC time>.bak` : copie conservée après l'échec d'un [correctif post-migration](cli_tools.md#post-migration-fixes). Supprimez-la dès que vous n'en avez plus besoin.

### 🖼️ `custom-uploads/`

Chaque fichier porte un nom aléatoire et un fichier `.json` à côté le décrit : conservez les paires ensemble.

### 📊 `broker_reports/`

Dans `broker_<id>/`, un rapport passe de `uploaded/` à `parsed/` ou `failed/` : l'original se trouve toujours dans l'un des trois.

- **📥 `uploaded/`** — en attente d'être lu
- **✅ `parsed/`** — lu avec succès
- **❌ `failed/`** — n'a pas pu être lu, conservé pour que vous puissiez vérifier pourquoi

### 📝 `logs/`

- 📄 `librefolio.log` : un enregistrement JSON par ligne ; le serveur affiche aussi le journal dans la console.
- 🗓️ Chaque lundi (UTC), le fichier est archivé et compressé (`.gz`) ; les 52 dernières archives, soit un an, sont conservées.

**Quantité à écrire.** Dans le **`.env`** de LibreFolio (par défaut `INFO`) :

```env
LOG_LEVEL=INFO
```

??? info "📶 Niveaux de journalisation — ce que chacun enregistre"

    Chaque niveau enregistre aussi tous les niveaux plus graves.

    | Niveau | Ce qu'il enregistre |
    |-------|-----------------|
    | 🔬 `TRACE` | Données granulaires à haute fréquence : taux de change individuels analysés, points de prix par actif |
    | 🐛 `DEBUG` | Détails internes du fonctionnement : fournisseur utilisé, résultats intermédiaires, décisions algorithmiques |
    | ℹ️ `INFO` *(par défaut)* | Opérations utilisateur importantes : synchronisation terminée, importation, connexion, ressource créée/supprimée |
    | ⚠️ `WARNING` | Anomalies récupérables : repli activé, données facultatives manquantes, mode dégradé |
    | ❌ `ERROR` | Erreurs gérées : opérations échouées, corruption de données, fournisseur inaccessible |
    | 💀 `CRITICAL` | Erreurs fatales qui arrêtent le processus |

    - **Production** : `LOG_LEVEL=INFO` — signal propre, sans bruit
    - **Dépannage** : `LOG_LEVEL=DEBUG` — voyez ce que le système décide
    - **Débogage approfondi des taux de change et des prix** : `LOG_LEVEL=TRACE` — voyez chaque point de données individuel

**Lire le journal.** Chaque ligne est un objet JSON : le message dans `event`, le niveau dans `level`, l'heure (UTC) dans `timestamp`, la trace d'appel dans `exception`.
Une ligne écrite pendant une requête porte son `request_id` ; lorsque quelque chose échoue, le même identifiant parvient au navigateur : en-tête `X-Request-Id` de la réponse, corps de l'erreur serveur, ligne `[API]` dans la console du navigateur (outils de développement, **Console**).

1. **Demandez l'identifiant** à l'utilisateur qui signale l'erreur.
2. **Dans le dossier `<data>/logs/`**, lisez ses lignes avec [jq](https://jqlang.org/) :

    ```bash
    # Every line of one request
    jq -cR 'fromjson? | select(.request_id == "3f2a9c0d41b7e865")' librefolio.log

    # The errors, each followed by its traceback
    jq -rR 'fromjson? | select(.level == "ERROR" or .level == "CRITICAL") | "\(.timestamp) \(.request_id // "-") \(.event)", (.exception // empty)' librefolio.log
    ```

    Une ligne de requête échouée indique la méthode et le chemin, jamais la chaîne de requête, les en-têtes ou le corps.

- `fromjson?` ignore les lignes qui ne sont pas du JSON, comme celles des bibliothèques utilisées par LibreFolio.
- Semaine archivée : `gzip -dc librefolio.log.2026-10-12.gz | jq -cR …`.

### 🗄️ `cache/`

`pdf-fonts/` : les polices chinoises, japonaises et coréennes que l'aperçu PDF télécharge à la première utilisation lorsque le PDF en a besoin, voir [La Content-Security-Policy](configuration_security.md#csp).
Le supprimer ne fait rien perdre ; il ne fait pas partie d'une [sauvegarde](backup_restore.md).

### 🔐 `secrets/`

- 🔑 `instance.key` est la [clé d'instance](configuration_secrets.md#instance-key), à partir de laquelle LibreFolio dérive ses clés de chiffrement. Si elle est absente, LibreFolio y voit une première utilisation : il crée une nouvelle clé et ce qui a été chiffré avec l'ancienne ne peut plus être lu.
- 🔒 Dossier en `0700`, fichier en `0600`, appartenant à l'utilisateur qui exécute LibreFolio. Sinon, le [journal de démarrage](configuration_security.md#startup-checks) contient un avertissement, ou une erreur si LibreFolio lui-même ne peut pas les ouvrir.
- ⛔ Ne modifiez, ne remplacez ni ne supprimez jamais le fichier `instance.key` en cours d'utilisation. S'il est endommagé, ou si LibreFolio a déjà remplacé une clé perdue par une nouvelle : arrêtez LibreFolio et remettez votre copie en place avant que quiconque ne saisisse à nouveau un secret de plugin, voir [La clé d'instance](configuration_secrets.md#instance-key).
- ♻️ Lorsque vous restaurez le répertoire de données, remettez `secrets/` avec lui avant de démarrer LibreFolio. Ne démarrez jamais LibreFolio sur des données restaurées sans leur `secrets/`.
- ⚙️ Lorsque la clé se trouve dans `LIBREFOLIO_INSTANCE_KEY` ou `LIBREFOLIO_INSTANCE_KEY_FILE`, LibreFolio n'utilise pas ce dossier.

🔗 Pour les développeurs : [Le répertoire de données sur le disque](../developer/architecture/database/index.md#data-directory) — chaque fichier, son format et le code qui l'écrit, `scenario_catalog/` inclus.

---

## 🌍 Variables d'environnement

**Hôte, dans le `.env` de LibreFolio**. Un chemin relatif part du dossier du projet :

```env
LIBREFOLIO_DATA_DIR=/path/to/data        # production data directory
LIBREFOLIO_TEST_DATA_DIR=/path/to/test   # test data directory
```

**Docker Compose, dans `docker-compose.yml`.** Le chemin à l'intérieur du conteneur est fixe : pour conserver les données ailleurs sur l'hôte, modifiez la partie gauche du volume.

```yaml
- ./LibreFolio-data:/app/backend/data/prod-docker
```

Les autres variables et le fichier `.env` : [Configuration](configuration.md).

---

## 💾 Sauvegarde {: #backup }

La méthode recommandée est une archive de sauvegarde, réalisée pendant que LibreFolio continue de fonctionner : [Sauvegarder, restaurer et déplacer votre instance](backup_restore.md).

- **En ligne de commande**, `./dev.py backup create` : un zip de la base de données, des fichiers téléversés, des rapports de courtiers et des scénarios de stress, par défaut dans son propre dossier à l'intérieur de `<data>/backups/`. Voir [Sauvegarder l'instance](cli_backup.md#backup) et, pour la commande dans le conteneur, [Sauvegarder avec Docker](cli_backup.md#backup-docker).
- L'archive **exclut `secrets/`**, que vous sauvegardez séparément ([Ce qu'il faut sauvegarder](#what-to-back-up)), sauf si vous la rendez [sécurisée](backup_restore.md#secure) avec `--encrypt` : une archive sécurisée contient la clé d'instance générée par LibreFolio.
- L'alternative est de copier le répertoire de données à la main, comme ci-dessous.

### 📦 Sauvegarde simple

1. **Arrêtez le serveur**, pour la cohérence de la base de données.
2. **Depuis le dossier du projet**, copiez l'intégralité du répertoire de données :

    ```bash
    # Stop the server first (to ensure database consistency)
    cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
    ```

    Résultat : une copie complète et datée de `<data>`.

Cette copie, comme celle avec Docker ci-dessous, inclut aussi `backups/`, avec toutes les sauvegardes que LibreFolio y conserve ([Sauvegardes conservées sur le serveur](backup_restore.md#kept-backups)) : supprimez d'abord celles dont vous n'avez plus besoin, configurez le [nettoyage automatique](backup_restore.md#backup-cleanup), ou omettez le dossier.

### 🐳 Sauvegarde avec Docker

Le répertoire de données est le dossier `LibreFolio-data/` sur l'hôte : aucune commande de copie Docker.

1. **Depuis le dossier de `docker-compose.yml`**, arrêtez le conteneur, copiez, redémarrez :

    ```bash
    docker compose stop librefolio
    cp -r ./LibreFolio-data/ /path/to/backup/librefolio-$(date +%Y%m%d)/
    docker compose start librefolio
    ```

    Résultat : une copie cohérente ; le serveur n'est arrêté que le temps de la copie.

??? tip "🔄 Sauvegarder la base de données sans arrêter le serveur"

    La sauvegarde en ligne de SQLite crée une copie cohérente pendant que le serveur tourne. Elle nécessite l'outil `sqlite3` :

    ```bash
    sqlite3 backend/data/prod/sqlite/app.db ".backup '/path/to/backup/app.db'"
    ```

    Avec Docker, la base de données est `./LibreFolio-data/sqlite/app.db`. Cette commande ne copie que la base de données : copiez les dossiers listés ci-dessous comme d'habitude.

### ✅ Ce qu'il faut sauvegarder {: #what-to-back-up }

Au minimum, sauvegardez :

1. **`sqlite/app.db`** — Toutes vos données (utilisateurs, transactions, paramètres, taux de change)
2. **`custom-uploads/`** — Les fichiers téléversés par les utilisateurs (avatars, documents)
3. **`broker_reports/`** — Les rapports de courtiers d'origine, au cas où vous auriez besoin de les importer à nouveau
4. **`scenario_catalog/`** — Vos propres scénarios de stress, si vous en avez ajouté
5. **`secrets/`** — La clé d'instance, si LibreFolio l'a créée

!!! warning "🔑 Conservez `secrets/` avec les données, et gardez-le confidentiel"

    Sauvegardez `secrets/` avec la base de données, et gardez les copies aussi confidentielles que la base de données. Ne modifiez ni ne supprimez jamais la clé d'instance en cours d'utilisation : ce qui a été chiffré avec elle ne pourrait plus être lu. Lors d'une restauration, remettez `secrets/` avec les données avant de démarrer LibreFolio.

    Seul l'utilisateur qui exécute LibreFolio peut ouvrir `secrets/`. Il en va de même pour `backups/`, créé lors de la première sauvegarde, et `.restore/`, créé la première fois qu'une archive est vérifiée en vue d'une restauration : LibreFolio crée ces deux dossiers en `0700`, et les archives de `backups/` en `0600`. Si `cp` signale `Permission denied` dans l'un d'eux, par exemple avec Docker lorsque votre utilisateur hôte n'est pas celui du conteneur, copiez en tant que root en conservant les permissions : `sudo cp -a`. La suppression d'une ancienne archive de `backups/` échoue de la même manière : utilisez `sudo rm`.

Si l'espace de stockage est limité, conservez au moins `sqlite/app.db`, qui contient toutes les données structurées, et le petit dossier `secrets/` : les fichiers et les rapports peuvent être téléversés à nouveau si vous les avez encore.
