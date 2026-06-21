# 📂 Structure du système de fichiers

LibreFolio stocke toutes les données persistantes dans un répertoire structuré sous `backend/data/`. La compréhension de cette structure est importante pour la sauvegarde, le débogage et la maintenance.

---

## 🗂️ Disposition des répertoires

```
backend/data/
├── 📂 prod/                          # Production data (default)
│   ├── 🗃️ sqlite/
│   │   └── 📄 app.db                 # Main SQLite database (WAL mode)
│   ├── 🖼️ custom-uploads/            # User-uploaded files
│   │   ├── 📄 {uuid}.{ext}          # Binary file (image, document, etc.)
│   │   └── 📋 {uuid}.json           # Metadata sidecar (uploader, date, MIME type)
│   ├── 📊 broker_reports/
│   │   ├── 📥 uploaded/              # Reports waiting to be parsed
│   │   ├── ✅ parsed/               # Successfully parsed reports
│   │   └── ❌ failed/               # Reports that failed parsing
│   └── 📝 logs/                      # Application log files
│
└── 🧪 test/                          # Test data (completely isolated)
    ├── 🗃️ sqlite/app.db
    ├── 🖼️ custom-uploads/
    ├── 📊 broker_reports/
    └── 📝 logs/
```

---

## 📖 Contenu de chaque répertoire

### 🗃️ `sqlite/app.db`

La base de données SQLite principale. Elle contient toutes les données de l'application : utilisateurs, courtiers, transactions, taux de change, paramètres, etc.

- 📝 Utilise le mode de journalisation **WAL (Write-Ahead Logging)** pour un meilleur accès concurrent
- 📎 Les fichiers `.db-wal` et `.db-shm` sont des fichiers WAL temporaires — ils sont normaux et gérés par SQLite

:material-arrow-right: **Approfondissement développeur** : [Schéma de la base de données](../developer/architecture/database/index.md)

### 🖼️ `custom-uploads/`

Fichiers téléversés par les utilisateurs via la page Fichiers. Chaque téléversement crée deux fichiers :

- 📄 `{uuid}.{ext}` — Le fichier binaire réel (ex: `a1b2c3d4.png`)
- 📋 `{uuid}.json` — Métadonnées incluant : nom de fichier original, type MIME, taille du fichier, date de téléversement, ID de l'utilisateur ayant téléversé le fichier

:material-arrow-right: **Approfondissement développeur** : [Composant de téléchargement de fichiers](../developer/frontend/components/core-ui/file-upload.md)

### 📊 `broker_reports/`

Fichiers de rapports de courtiers pour le système BRIM (Broker Report Import Manager) :

- **📥 `uploaded/`** — Fichiers bruts tels que téléversés par les utilisateurs (CSV, Excel)
- **✅ `parsed/`** — Fichiers qui ont été traités avec succès (transactions extraites)
- **❌ `failed/`** — Fichiers dont l'analyse a échoué (conservés pour le débogage — consulter les logs pour plus de détails)

:material-arrow-right: **Approfondissement développeur** : [Architecture BRIM](../developer/backend/brim/architecture.md)

### 📝 `logs/`

Journaux de l'application au format JSON structuré (via `structlog`). Les fichiers de journaux font l'objet d'une rotation hebdomadaire et sont conservés pendant 1 an (compressés avec gzip).

La verbosité est contrôlée par la variable d'environnement `LOG_LEVEL`.

**Ce que chaque niveau capture** — chaque ligne montre quels niveaux de log sont visibles :

| LOG_LEVEL | 🔬 TRACE (5) | 🐛 DEBUG (10) | ℹ️ INFO (20) | ⚠️ WARNING (30) | ❌ ERROR (40) | 💀 CRITICAL (50) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 🔬`TRACE` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 🐛`DEBUG` | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ℹ️ **`INFO`** *(par défaut)* | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| ⚠️ `WARNING` | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| ❌`ERROR` | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| 💀`CRITICAL` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

**Signification de chaque niveau :**

| Niveau | Ce qu'il capture |
|-------|-----------------|
| 🔬`TRACE` | Données granulaires à haute fréquence : taux de change individuels analysés, points de prix par actif |
| 🐛`DEBUG` | Internes opérationnels : quel fournisseur a été utilisé, résultats intermédiaires, décisions algorithmiques |
| ℹ️`INFO` | Opérations utilisateur significatives : synchronisation terminée, import, connexion, ressource créée/supprimée |
| ⚠️`WARNING` | Anomalies récupérables : fallback activé, données optionnelles manquantes, mode dégradé |
| ❌`ERROR` | Erreurs gérées : opérations échouées, corruption de données, fournisseur injoignable |
| 💀`CRITICAL` | Erreurs fatales qui arrêtent le processus |

!!! tip "Paramètres recommandés"

    - **Production** : `LOG_LEVEL=INFO` — signal clair, sans bruit
    - **Dépannage** : `LOG_LEVEL=DEBUG` — voir les décisions du système
    - **Débogage profond taux de change/prix** : `LOG_LEVEL=TRACE` — voir chaque point de donnée individuel

---

## 🌍 Variables d'environnement

Les chemins de stockage et les comportements à l'exécution du système de fichiers sont contrôlés par des variables d'environnement (telles que `LIBREFOLIO_DATA_DIR` et `LIBREFOLIO_TEST_MODE`). Pour obtenir une liste complète de toutes les variables d'environnement prises en charge et savoir comment les configurer à l'aide du fichier `.env`, consultez la page de [Configuration](configuration.md).

---

## 💾 Sauvegarde

### 📦 Sauvegarde simple

Le moyen le plus simple de sauvegarder LibreFolio est de copier l'intégralité du répertoire de données :

```bash
# Stop the server first (to ensure database consistency)
cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
```

### 🐳 Sauvegarde Docker

Si vous exécutez LibreFolio via Docker Compose (la méthode de déploiement standard), le répertoire des données de production est directement monté (bind-mount) sur le répertoire `./LibreFolio-data` de votre machine hôte (et mappé sur `/app/backend/data/prod-docker` à l'intérieur du conteneur).

Par conséquent, vous n'avez pas besoin de commandes de copie Docker spécifiques ; il suffit de sauvegarder le dossier `./LibreFolio-data` sur votre machine hôte pour préserver vos données.

### ✅ Quoi sauvegarder

Au minimum, sauvegardez :

1. **`sqlite/app.db`** — Toutes vos données (utilisateurs, transactions, paramètres, taux de change)
2. **`custom-uploads/`** — Fichiers téléversés par les utilisateurs (avatars, documents)
3. **`broker_reports/uploaded/`** — Rapports de courtiers originaux (au cas où vous auriez besoin de les ré-analyser)

!!! tip "Sauvegarde de la base de données uniquement"

    Si l'espace de stockage est limité, la sauvegarde de `sqlite/app.db` seul préserve toutes les données structurées. Les fichiers peuvent toujours être téléversés à nouveau.
