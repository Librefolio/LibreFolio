# 📂 Structure du système de fichiers

LibreFolio conserve tout ce qu’il stocke dans un seul **répertoire de données** : la base de données, les fichiers téléversés, les rapports de courtiers, les journaux et la clé d’instance. Son organisation est tout ce que vous devez connaître pour les sauvegardes et la maintenance.

| Installation | Répertoire de données |
| --- | --- |
| Hôte (Pipenv) | `backend/data/prod/` dans le dossier du projet, ou le chemin indiqué dans `LIBREFOLIO_DATA_DIR` |
| Docker Compose | `LibreFolio-data/` à côté de `docker-compose.yml` (`/app/backend/data/prod-docker` à l’intérieur du conteneur) |

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

---

## 📖 Contenu de chaque répertoire

### 🗃️ `sqlite/`

- 📄 `app.db` contient toutes les données structurées : utilisateurs, courtiers, transactions, actifs, prix, taux de change et paramètres.
- 📎 `app.db-wal` et `app.db-shm` sont les fichiers de travail de SQLite (mode WAL), attendus pendant l’exécution du serveur : ne copiez jamais `app.db` seul tant que le serveur est démarré.
- 🔒 `app.db.post-migration.lock` est un fichier vide utilisé au démarrage : laissez-le en place. Un fichier nommé `app.db.pre-<fix>-<UTC time>.bak` est une copie conservée après l’échec d’une [correction post-migration](cli_tools.md#post-migration-fixes) : supprimez-la dès que vous n’en avez plus besoin.

### 🖼️ `custom-uploads/`

Fichiers téléversés dans l’application, comme ceux de la page **Fichiers**, ainsi que les avatars par défaut. Chaque fichier porte un nom aléatoire et un fichier `.json` adjacent le décrit : conservez les paires ensemble.

### 📊 `broker_reports/`

Les rapports de courtiers téléversés en vue de leur importation, dans un dossier `broker_<id>/` par courtier :

- **📥 `uploaded/`** — en attente d’être lus
- **✅ `parsed/`** — lus avec succès
- **❌ `failed/`** — n’ont pas pu être lus, conservés pour que vous puissiez vérifier pourquoi

Un rapport passe de `uploaded/` à `parsed/` ou `failed/`, de sorte que son fichier d’origine se trouve toujours dans l’un des trois.

### 📝 `logs/`

- 📄 `librefolio.log` contient un enregistrement JSON par ligne ; le serveur affiche aussi le journal dans sa console.
- 🗓️ Chaque lundi (UTC), le fichier est archivé et compressé (`.gz`) ; les 52 dernières archives, soit un an, sont conservées.
- 🎚️ `LOG_LEVEL` dans `.env` détermine la quantité d’informations écrites (par défaut `INFO`).

??? info "📶 Niveaux de journalisation — ce que chacun enregistre"

    Chaque niveau enregistre aussi tous les niveaux plus graves.

    | Niveau | Ce qu’il enregistre |
    |-------|-----------------|
    | 🔬 `TRACE` | Données granulaires à haute fréquence : taux de change individuels analysés, points de prix par actif |
    | 🐛 `DEBUG` | Détails internes du fonctionnement : fournisseur utilisé, résultats intermédiaires, décisions algorithmiques |
    | ℹ️ `INFO` *(par défaut)* | Opérations utilisateur importantes : synchronisation terminée, importation, connexion, ressource créée/supprimée |
    | ⚠️ `WARNING` | Anomalies récupérables : fallback activé, données facultatives manquantes, mode dégradé |
    | ❌ `ERROR` | Erreurs gérées : opérations échouées, corruption de données, fournisseur inaccessible |
    | 💀 `CRITICAL` | Erreurs fatales qui arrêtent le processus |

    - **Production** : `LOG_LEVEL=INFO` — signal propre, sans bruit
    - **Dépannage** : `LOG_LEVEL=DEBUG` — voyez ce que le système décide
    - **Débogage approfondi des taux de change et des prix** : `LOG_LEVEL=TRACE` — voyez chaque point de données individuel

**Lire le journal.** Chaque ligne écrite par LibreFolio est un objet JSON : le message se trouve dans `event`, le niveau dans `level`, l’heure (UTC) dans `timestamp` et la trace d’appel d’une erreur dans `exception`. Chaque ligne écrite pendant que le serveur répond à une requête porte le `request_id` de cette requête. Lorsqu’une opération échoue, le même identifiant parvient au navigateur : dans l’en-tête `X-Request-Id` de la réponse, dans le corps d’une erreur serveur et dans la ligne `[API]` que l’application web écrit dans la console du navigateur (outils de développement, **Console**). Demandez cet identifiant à l’utilisateur qui signale une erreur, puis lisez ses lignes avec [jq](https://jqlang.org/), depuis le dossier `logs/` :

```bash
# Every line of one request
jq -cR 'fromjson? | select(.request_id == "3f2a9c0d41b7e865")' librefolio.log

# The errors, each followed by its traceback
jq -rR 'fromjson? | select(.level == "ERROR" or .level == "CRITICAL") | "\(.timestamp) \(.request_id // "-") \(.event)", (.exception // empty)' librefolio.log
```

`fromjson?` ignore les quelques lignes qui ne sont pas du JSON, comme celles des bibliothèques utilisées par LibreFolio. Pour une semaine archivée, décompressez-la à la volée : `gzip -dc librefolio.log.2026-10-12.gz | jq -cR …`. Une ligne concernant une requête échouée indique sa méthode et son chemin, jamais sa chaîne de requête, ses en-têtes ou son corps.

### 🗄️ `cache/`

Copies que LibreFolio peut récupérer à nouveau. Aujourd’hui, il contient `pdf-fonts/`, les polices chinoises, japonaises et coréennes dont l’aperçu PDF a besoin pour un PDF qui les utilise, conservées après le premier téléchargement : voir [La Content-Security-Policy](configuration_security.md#csp). Le supprimer ne fait perdre aucune donnée, et il ne fait pas partie d’une [sauvegarde](backup_restore.md).

### 🔐 `secrets/`

- 🔑 `instance.key` contient la [clé d’instance](configuration_secrets.md#instance-key), le secret à partir duquel LibreFolio dérive ses clés de chiffrement. LibreFolio la crée la première fois qu’il a besoin de la clé. Ensuite, l’absence du fichier `instance.key` ressemble à une première utilisation : LibreFolio crée une nouvelle clé, et ce qui a été chiffré avec l’ancienne ne peut plus être lu.
- 🔒 Seul l’utilisateur qui exécute LibreFolio peut ouvrir le dossier et le fichier : le dossier est en `0700`, le fichier en `0600`. Laissez-les ainsi et faites en sorte qu’ils appartiennent à cet utilisateur : sinon le [journal de démarrage](configuration_security.md#startup-checks) contient un avertissement, ou une erreur lorsque LibreFolio lui-même ne peut pas les ouvrir.
- ⛔ Ne modifiez, ne remplacez ni ne supprimez jamais le fichier `instance.key` en cours d’utilisation : ce qui a été chiffré avec cette clé ne pourrait plus être lu. S’il est endommagé, ou si LibreFolio a déjà remplacé une clé perdue par une nouvelle, arrêtez LibreFolio et remettez votre copie en place avant que quiconque ne saisisse à nouveau un secret de plugin : voir [La clé d’instance](configuration_secrets.md#instance-key).
- ♻️ Lorsque vous restaurez le répertoire de données, remettez `secrets/` avec lui avant de redémarrer LibreFolio. Ne démarrez jamais LibreFolio sur des données restaurées sans leur `secrets/`.
- ⚙️ Lorsque la clé provient de `LIBREFOLIO_INSTANCE_KEY` ou `LIBREFOLIO_INSTANCE_KEY_FILE`, LibreFolio n’utilise pas ce dossier.

🔗 Pour les développeurs : [Le répertoire de données sur le disque](../developer/architecture/database/index.md#data-directory) — chaque fichier, son format et le code qui l’écrit, `scenario_catalog/` inclus.

---

## 🌍 Variables d’environnement

- `LIBREFOLIO_DATA_DIR` déplace le répertoire de données de production, et `LIBREFOLIO_TEST_DATA_DIR` celui des tests. Un chemin relatif part du dossier du projet.
- Avec Docker Compose, le chemin à l’intérieur du conteneur est fixe : pour conserver les données ailleurs sur l’hôte, modifiez la partie gauche du volume `./LibreFolio-data:/app/backend/data/prod-docker` dans `docker-compose.yml`.

Les autres variables, ainsi que le fichier `.env`, sont décrites dans [Configuration](configuration.md).

---

## 💾 Sauvegarde {: #backup }

La méthode recommandée est une archive de sauvegarde, réalisée pendant que LibreFolio continue de fonctionner : voir [Sauvegarder, restaurer et déplacer votre instance](backup_restore.md). En ligne de commande, `./dev.py backup create` écrit une archive zip de la base de données, des fichiers téléversés, des rapports de courtiers et de vos propres scénarios de stress, par défaut dans son propre dossier à l’intérieur du dossier `backups/` du répertoire de données : voir [Sauvegarder l’instance](cli_backup.md#backup), et [Sauvegarder avec Docker](cli_backup.md#backup-docker) pour la commande dans le conteneur. Elle exclut `secrets/`, que vous sauvegardez comme l’explique [Ce qu’il faut sauvegarder](#what-to-back-up), sauf si vous la rendez [sécurisée](backup_restore.md#secure) (`--encrypt`) : une archive sécurisée contient la clé d’instance générée par LibreFolio. Copier le répertoire de données à la main, ci-dessous, constitue l’alternative.

### 📦 Sauvegarde simple

Le moyen le plus simple de sauvegarder LibreFolio est de copier l’intégralité du répertoire de données :

```bash
# Stop the server first (to ensure database consistency)
cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
```

Cette copie, comme celle avec Docker ci-dessous, inclut aussi `backups/`, avec toutes les sauvegardes que LibreFolio y conserve ([Sauvegardes conservées sur le serveur](backup_restore.md#kept-backups)) : supprimez d’abord celles dont vous n’avez plus besoin, configurez le [nettoyage automatique](backup_restore.md#backup-cleanup), ou omettez le dossier.

### 🐳 Sauvegarde avec Docker

Avec Docker Compose, le répertoire de données est le dossier `LibreFolio-data/` sur l’hôte ; aucune commande de copie Docker n’est donc nécessaire. Arrêtez le conteneur pour obtenir une copie cohérente :

```bash
docker compose stop librefolio
cp -r ./LibreFolio-data/ /path/to/backup/librefolio-$(date +%Y%m%d)/
docker compose start librefolio
```

??? tip "🔄 Sauvegarder la base de données sans arrêter le serveur"

    La sauvegarde en ligne de SQLite permet de créer une copie cohérente pendant que le serveur fonctionne. Elle nécessite l’outil `sqlite3` :

    ```bash
    sqlite3 backend/data/prod/sqlite/app.db ".backup '/path/to/backup/app.db'"
    ```

    Avec Docker, la base de données est `./LibreFolio-data/sqlite/app.db`. Cette commande ne copie que la base de données : copiez les dossiers ci-dessous comme d’habitude.

### ✅ Ce qu’il faut sauvegarder {: #what-to-back-up }

Au minimum, sauvegardez :

1. **`sqlite/app.db`** — Toutes vos données (utilisateurs, transactions, paramètres, taux de change)
2. **`custom-uploads/`** — Fichiers téléversés par les utilisateurs (avatars, documents)
3. **`broker_reports/`** — Les rapports de courtiers d’origine, au cas où vous auriez besoin de les importer à nouveau
4. **`scenario_catalog/`** — Vos propres scénarios de stress, si vous en avez ajouté
5. **`secrets/`** — La clé d’instance, si LibreFolio l’a créée

!!! warning "🔑 Conservez `secrets/` avec les données, et gardez-le confidentiel"

    Sauvegardez `secrets/` avec la base de données, et gardez les copies aussi confidentielles que la base de données elle-même. Ne modifiez ni ne supprimez jamais la clé d’instance une fois en service : ce qui a été chiffré avec elle ne pourrait plus être lu. Lors d’une restauration, remettez `secrets/` avec les données avant de démarrer LibreFolio.

    Seul l’utilisateur qui exécute LibreFolio peut ouvrir `secrets/`. Il en va de même pour `backups/`, créé lors de la première sauvegarde, et `.restore/`, créé la première fois qu’une archive est vérifiée en vue d’une restauration : LibreFolio crée ces deux dossiers en `0700`, et les archives dans `backups/` en `0600`. Si `cp` signale `Permission denied` dans l’un d’eux, par exemple avec Docker lorsque votre utilisateur hôte n’est pas celui du conteneur, copiez en tant que root et conservez les permissions : `sudo cp -a`. La suppression d’une ancienne archive dans `backups/` échoue de la même manière : utilisez `sudo rm`.

Si l’espace de stockage est limité, conservez au moins `sqlite/app.db`, qui contient toutes les données structurées, et le petit dossier `secrets/` : les fichiers et les rapports peuvent être téléversés à nouveau si vous les avez encore.
