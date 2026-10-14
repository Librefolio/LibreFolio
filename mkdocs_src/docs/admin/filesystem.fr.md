# 📂 Structure du système de fichiers

LibreFolio conserve tout ce qu'il stocke dans un **répertoire de données** : la base de données, les fichiers téléversés, les rapports de courtier et les journaux. Il suffit de connaître son organisation pour les sauvegardes et la maintenance.

| Installation | Répertoire de données |
| --- | --- |
| Hôte (Pipenv) | `backend/data/prod/` dans le dossier du projet, ou le chemin dans `LIBREFOLIO_DATA_DIR` |
| Docker Compose | `LibreFolio-data/` à côté de `docker-compose.yml` (`/app/backend/data/prod-docker` à l'intérieur du conteneur) |

---

## 🗂️ Organisation des répertoires

```text
backend/data/
├── 📂 prod/                          # Données de production (par défaut)
│   ├── 🗃️ sqlite/
│   │   └── 📄 app.db                 # Base de données SQLite principale (mode WAL)
│   ├── 🖼️ custom-uploads/            # Fichiers téléversés dans l'application
│   ├── 📊 broker_reports/
│   │   ├── 📥 uploaded/              # Rapports en attente de lecture
│   │   ├── ✅ parsed/                # Rapports lus avec succès
│   │   └── ❌ failed/                # Rapports qui n'ont pas pu être lus
│   ├── 📝 logs/                      # Fichiers journaux de l'application
│   ├── 🎭 scenario_catalog/          # Optionnel : vos propres scénarios de stress
│   └── 📋 scheduler_state.json       # Dernière exécution des synchronisations planifiées
│
└── 🧪 test/                          # Données de test (complètement isolées)
    ├── 🗃️ sqlite/app.db
    ├── 🖼️ custom-uploads/
    ├── 📊 broker_reports/
    └── 📝 logs/
```

---

## 📖 Contenu de chaque répertoire

### 🗃️ `sqlite/`

- 📄 `app.db` contient toutes les données structurées : utilisateurs, courtiers, transactions, actifs, prix, taux de change et paramètres.
- 📎 `app.db-wal` et `app.db-shm` sont les fichiers de travail de SQLite (mode WAL), attendus pendant que le serveur fonctionne : ne copiez jamais `app.db` seul pendant que le serveur est démarré.
- 🔒 `app.db.post-migration.lock` est un fichier vide utilisé au démarrage : laissez-le en place. Un fichier nommé `app.db.pre-<fix>-<UTC time>.bak` est une copie conservée après un échec de [correctif post-migration](cli_tools.md#post-migration-fixes) : supprimez-le dès que vous n'en avez plus besoin.

### 🖼️ `custom-uploads/`

Fichiers téléversés dans l'application, comme ceux de la page **Fichiers**, ainsi que les avatars par défaut. Chaque fichier a un nom aléatoire et un fichier `.json` à côté qui le décrit : conservez les paires ensemble.

### 📊 `broker_reports/`

Les rapports de courtier téléversés pour importation, dans un dossier `broker_<id>/` par courtier :

- **📥 `uploaded/`** — en attente de lecture
- **✅ `parsed/`** — lus avec succès
- **❌ `failed/`** — n'ont pas pu être lus, conservés pour que vous puissiez vérifier pourquoi

Un rapport passe de `uploaded/` à `parsed/` ou `failed/`, donc son fichier d'origine se trouve toujours dans l'un des trois dossiers.

### 📝 `logs/`

- 📄 `librefolio.log` contient un enregistrement JSON par ligne ; le serveur affiche aussi le journal dans sa console.
- 🗓️ Chaque lundi (UTC), le fichier est archivé et compressé (`.gz`) ; les 52 dernières archives, soit un an, sont conservées.
- 🎚️ `LOG_LEVEL` dans `.env` définit la quantité écrite (par défaut `INFO`).

??? info "📶 Niveaux de journalisation — ce que chacun enregistre"

    Chaque niveau enregistre aussi tous les niveaux plus graves.

    | Niveau | Ce qu'il enregistre |
    |-------|-----------------|
    | 🔬 `TRACE` | Données granulaires à haute fréquence : taux de change individuels analysés, points de prix par actif |
    | 🐛 `DEBUG` | Détails internes opérationnels : quel fournisseur a été utilisé, résultats intermédiaires, décisions algorithmiques |
    | ℹ️ `INFO` *(par défaut)* | Opérations utilisateur significatives : synchronisation terminée, importation, connexion, ressource créée/supprimée |
    | ⚠️ `WARNING` | Anomalies récupérables : fallback activé, données optionnelles manquantes, mode dégradé |
    | ❌ `ERROR` | Erreurs gérées : opérations échouées, corruption de données, fournisseur inaccessible |
    | 💀 `CRITICAL` | Erreurs fatales qui arrêtent le processus |

    - **Production** : `LOG_LEVEL=INFO` — signal propre, sans bruit
    - **Dépannage** : `LOG_LEVEL=DEBUG` — voir ce que le système décide
    - **Débogage approfondi FX/prix** : `LOG_LEVEL=TRACE` — voir chaque point de données individuel

🔗 Pour les développeurs : [Répertoire de données sur disque](../developer/architecture/database/index.md#data-directory) — chaque fichier, son format et le code qui l'écrit, `scenario_catalog/` inclus.

---

## 🌍 Variables d'environnement

- `LIBREFOLIO_DATA_DIR` déplace le répertoire de données de production, et `LIBREFOLIO_TEST_DATA_DIR` celui de test. Un chemin relatif part du dossier du projet.
- Avec Docker Compose, le chemin à l'intérieur du conteneur est fixe : pour conserver les données ailleurs sur l'hôte, modifiez le côté gauche du volume `./LibreFolio-data:/app/backend/data/prod-docker` dans `docker-compose.yml`.

Les autres variables, ainsi que le fichier `.env`, sont décrites dans [Configuration](configuration.md).

---

## 💾 Sauvegarde {: #backup }

### 📦 Sauvegarde simple

La façon la plus simple de sauvegarder LibreFolio est de copier l'intégralité du répertoire de données :

```bash
# Arrêtez d'abord le serveur (pour garantir la cohérence de la base de données)
cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
```

### 🐳 Sauvegarde Docker

Avec Docker Compose, le répertoire de données est le dossier `LibreFolio-data/` sur l'hôte, donc aucune commande de copie Docker n'est nécessaire. Arrêtez le conteneur pour une copie cohérente :

```bash
docker compose stop librefolio
cp -r ./LibreFolio-data/ /path/to/backup/librefolio-$(date +%Y%m%d)/
docker compose start librefolio
```

??? tip "🔄 Sauvegarder la base de données sans arrêter le serveur"

    La sauvegarde en ligne de SQLite réalise une copie cohérente pendant que le serveur fonctionne. Elle nécessite l'outil `sqlite3` :

    ```bash
    sqlite3 backend/data/prod/sqlite/app.db ".backup '/path/to/backup/app.db'"
    ```

    Avec Docker, la base de données est `./LibreFolio-data/sqlite/app.db`. Cela ne copie que la base de données : copiez les dossiers ci-dessous comme d'habitude.

### ✅ Éléments à sauvegarder

Au minimum, sauvegardez :

1. **`sqlite/app.db`** — Toutes vos données (utilisateurs, transactions, paramètres, taux de change)
2. **`custom-uploads/`** — Fichiers téléversés par l'utilisateur (avatars, documents)
3. **`broker_reports/`** — Les rapports de courtier originaux, au cas où vous auriez besoin de les importer à nouveau
4. **`scenario_catalog/`** — Vos propres scénarios de stress, si vous en avez ajouté

Si l'espace de stockage est limité, `sqlite/app.db` seul conserve toutes les données structurées : les fichiers et les rapports peuvent être téléversés à nouveau si vous les avez encore.
