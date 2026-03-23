# 📂 Structure du système de fichiers

LibreFolio stocke toutes les données persistantes dans un répertoire structuré sous `backend/data/`. Comprendre cette structure est importante pour la sauvegarde, le débogage et la maintenance.

---

## 🗂️ Organisation des dossiers

```
backend/data/
├── 📂 prod/ # Données de production (par défaut)
│ ├── 🗃️ sqlite/
│ │ └── 📄 app.db # Base de données SQLite principale (mode WAL)
│ ├── 🖼️ custom-uploads/ # Fichiers téléversés par les utilisateurs
│ │ ├── 📄 {uuid}.{ext} # Fichier binaire (image, document, etc.)
│ │ └── 📋 {uuid}.json # Métadonnées associées (sidecar) (téléverseur, date, type MIME)
│ ├── 📊 broker_reports/
│ │ ├── 📥 uploaded/ # Rapports en attente d'analyse
│ │ ├── ✅ parsed/ # Rapports analysés avec succès
│ │ └── ❌ failed/ # Rapports dont l'analyse a échoué
│ └── 📝 logs/ # Fichiers de journaux de l'application
│
└── 🧪 test/ # Données de test (complètement isolées)
 ├── 🗃️ sqlite/app.db
 ├── 🖼️ custom-uploads/
 ├── 📊 broker_reports/
 └── 📝 logs/
```

---

## 📖 Contenu de chaque dossier

### 🗃️ `sqlite/app.db`

La base de données SQLite principale. Contient toutes les données de l'application : utilisateurs, courtiers, transactions, taux de change, paramètres, etc.

- 📝 Utilise le mode de journalisation **WAL (Write-Ahead Logging)** pour un meilleur accès concurrent
- 📎 Les fichiers `.db-wal` et `.db-shm` sont des fichiers temporaires WAL — ils sont attendus et gérés automatiquement par SQLite

:material-arrow-right: **Approfondissement pour les développeurs** : [Schéma de la base de données](../developer/architecture/database/index.md)

### 🖼️ `custom-uploads/`

Fichiers téléversés par les utilisateurs via la page Fichiers. Chaque téléversement crée deux fichiers :

- 📄 `{uuid}.{ext}` — Le fichier binaire réel (ex. `a1b2c3d4.png`)
- 📋 `{uuid}.json` — Métadonnées associées incluant : nom de fichier original, type MIME, taille, date de téléversement, identifiant de l'utilisateur

:material-arrow-right: **Approfondissement pour les développeurs** : [Composant de téléversement de fichiers](../developer/frontend/components/file-upload.md)

### 📊 `broker_reports/`

Fichiers de rapports de courtiers pour le système BRIM (Broker Report Import Manager) :

- **📥 `uploaded/`** — Fichiers bruts tels que téléversés par les utilisateurs (CSV, Excel)
- **✅ `parsed/`** — Fichiers qui ont été traités avec succès (transactions extraites)
- **❌ `failed/`** — Fichiers dont l'analyse a échoué (conservés pour le débogage — vérifiez les journaux pour plus de détails)

:material-arrow-right: **Approfondissement pour les développeurs** : [Architecture BRIM](../developer/backend/brim/architecture.md)

### 📝 `logs/`

Journaux de l'application au format JSON structuré (via `structlog`).

---

## 🌍 Variables d'environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Remplace le chemin du répertoire de données de production |
| `LIBREFOLIO_TEST_MODE` | `0` | Définir à `1` pour utiliser `backend/data/test/` au lieu de `prod/` |
| `PORT` | `8000` | Port du serveur de production |
| `TEST_PORT` | `8001` | Port du serveur de test (utilisé quand `LIBREFOLIO_TEST_MODE=1`) |

---

## 💾 Sauvegarde

### 📦 Sauvegarde simple

La manière la plus simple de sauvegarder LibreFolio est de copier l'ensemble du répertoire de données :

```bash
# Arrêtez d'abord le serveur (pour assurer la cohérence de la base de données)
cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
```

### 🐳 Sauvegarde Docker

Si vous exécutez via Docker, le répertoire de données est généralement monté en volume :

```bash
# Trouver le volume
docker volume inspect librefolio_data

# Copier les données hors du conteneur
docker cp librefolio-container:/app/backend/data/prod/ ./backup/
```

### ✅ Que sauvegarder

Au minimum, sauvegardez :

1. **`sqlite/app.db`** — Toutes vos données (utilisateurs, transactions, paramètres, taux de change)
2. **`custom-uploads/`** — Fichiers téléversés par les utilisateurs (avatars, documents)
3. **`broker_reports/uploaded/`** — Rapports de courtiers originaux (au cas où vous devriez ré-analyser)

!!! tip "Sauvegarde de la base de données uniquement"

    Si l'espace de stockage est limité, sauvegarder uniquement `sqlite/app.db` préserve toutes les données structurées. Les fichiers peuvent toujours être re-téléversés.

---

## 🔧 Maintenance depuis le terminal hôte

### 🐳 `docker exec`

```bash
# Accéder au shell du conteneur
docker exec -it librefolio-container /bin/bash

# Exécuter des commandes dev.py à l'intérieur du conteneur
./dev.py user list
./dev.py user reset admin newpassword
./dev.py db upgrade
```

### 💻 Accès direct (sans Docker)

```bash
# Depuis la racine du projet
./dev.py user list # Lister tous les utilisateurs
./dev.py user reset <user> <pw> # Réinitialiser le mot de passe d'un utilisateur
./dev.py user promote <user> # Accorder les privilèges de superutilisateur
./dev.py user demote <user> # Révoquer les privilèges de superutilisateur
./dev.py db upgrade # Appliquer les migrations en attente
./dev.py db create-clean # Réinitialiser la base de données (ATTENTION : supprime toutes les données)
```

Pour une liste complète des commandes CLI, voir [Outils CLI](cli_tools.md).
