# 🐳 Guide Docker Avancé

Ce guide propose un examen plus approfondi de la configuration Docker pour LibreFolio, destiné aux utilisateurs qui souhaitent personnaliser leur déploiement.

## ⚠️ Prérequis

!!! warning "Groupe Docker (Linux)"

    Sur Linux, votre utilisateur doit appartenir au groupe `docker` pour exécuter les commandes Docker sans `sudo` :

    ```bash
    sudo usermod -aG docker $USER
    ```

    Ensuite, **déconnectez-vous et reconnectez-vous**, ou exécutez `newgrp docker` pour activer le groupe dans la session actuelle. Sans cela, toutes les commandes `docker` et `docker compose` échoueront avec une erreur de permission.

!!! warning "Fichier `.env` requis"

    LibreFolio nécessite un fichier `.env` à la racine du projet. S'il est manquant, `./dev.py docker build` refusera de continuer.

    ```bash
    cp .env.example .env
    $EDITOR .env # examiner et personnaliser les paramètres
    ```

## 🏗️ Architecture

LibreFolio utilise une **image Docker destinée uniquement au runtime**. Le frontend (SvelteKit) et la documentation (MkDocs) sont construits sur l'hôte puis copiés dans l'image. La commande `./dev.py docker build` gère cela automatiquement.

```text
Host (build) Docker Image (runtime)
┌──────────────┐ ┌──────────────────────┐
│ frontend/src │──npm build──▶ │ frontend/build/ │
│ mkdocs_src/ │──mkdocs ───▶ │ mkdocs_src/site/ │
│ backend/ │──copy──────▶ │ backend/ │
│ Pipfile* │──pipenv ───▶ │ Python packages │
└──────────────┘ └──────────────────────┘
```

## 📄 `docker-compose.yml`

Le fichier `docker-compose.yml` définit le service et le répertoire de données persistantes.

### 🔧 Service : `librefolio`

- 🏗️ **`build: .`** : Construit à partir du `Dockerfile` à la racine du projet.
- 🔌 **`ports`** : Mappe le port de l'hôte (`${PORT:-8000}`) vers le port `8000` du conteneur, et `${TEST_PORT:-8001}` vers `8001` pour le mode test.
- 📂 **`volumes`** : Un montage lié (bind mount) `./LibreFolio-data` → `/app/backend/data/prod-docker` persiste la base de données, les uploads, les rapports de courtier et les logs **dans le même répertoire que `docker-compose.yml`**.
- 📝 **`env_file: .env`** : Charge toute la configuration depuis le fichier `.env` (copié depuis `.env.example`).
- 🌍 **`environment`** : Écrase uniquement les valeurs spécifiques à Docker : `LIBREFOLIO_DATA_DIR` (chemin dans le conteneur) et `HOST=0.0.0.0`.
- 🩺 **`healthcheck`** : Interroge `GET /api/v1/system/health` toutes les 30 secondes.

### 💾 Répertoire de données : `LibreFolio-data/`

Un répertoire en **montage lié** créé aux côtés de `docker-compose.yml`. Il contient la base de données SQLite, les uploads personnalisés, les rapports de courtier et les fichiers de log. Les données survivent à l'arrêt, au redémarrage ou à la suppression du conteneur. Vous pouvez les sauvegarder directement depuis le système de fichiers de l'hôte.

### 👤 Utilisateur et Permissions

Le conteneur LibreFolio s'exécute en tant qu'**utilisateur non-root** pour des raisons de sécurité. L'UID/GID par défaut est `1000:1000`. Les fichiers créés par l'application dans `LibreFolio-data/` appartiendront à l'utilisateur/groupe correspondant à cet UID/GID sur l'hôte.

#### Choisir le bon UID et GID

Configurez `UID` et `GID` dans votre fichier `.env` pour correspondre à l'**utilisateur hôte** (ou l'utilisateur dédié) qui doit posséder les fichiers de données :

```bash
UID=1000
GID=1000
```

!!! note "Comment `ls -l` affiche la propriété"

    Sur l'**hôte**, `ls -l LibreFolio-data/` affiche le nom de l'utilisateur/groupe choisi (résolu à partir de l'UID/GID via `/etc/passwd`).

    **À l'intérieur du conteneur**, les mêmes fichiers s'affichent comme `librefolio:librefolio` — il s'agit du même UID/GID numérique, simplement résolu par rapport au `/etc/passwd` propre au conteneur.

??? tip "Aide-mémoire Linux : utilisateurs, groupes et IDs"

 **Découvrir votre UID et GID actuels :**

 ```bash
 id -u # votre ID utilisateur (ex: 1000)
 id -g # votre ID de groupe primaire (ex: 1000)
 id # infos complètes : uid, gid, groups
 ```

 **Trouver l'UID/GID de n'importe quel utilisateur :**

 ```bash
 id -u username # UID de 'username'
 id -g username # GID primaire de 'username'
 ```

 **Créer un nouveau groupe :**

 ```bash
 sudo groupadd librefolio # créer le groupe (assigne le GID auto)
 sudo groupadd -g 1500 librefolio # créer le groupe avec un GID spécifique
 ```

 **Créer un nouvel utilisateur :**

 ```bash
 # Utilisateur système (sans home, sans login — idéal pour les services)
 sudo useradd --system --no-create-home --gid librefolio --shell /usr/sbin/nologin librefolio

 # Utilisateur régulier avec répertoire personnel
 sudo useradd -m -g librefolio librefolio
 ```

 **Vérifier les IDs assignés :**

 ```bash
 id librefolio
 # → uid=998(librefolio) gid=998(librefolio) groups=998(librefolio)
 ```

 **Ajouter votre utilisateur existant à un groupe :**

 ```bash
 sudo usermod -aG librefolio $USER
 newgrp librefolio # activer dans la session actuelle (ou déconnexion/connexion)
 ```

 **Vérifier l'appartenance au groupe :**

 ```bash
 groups $USER # liste tous les groupes de votre utilisateur
 ```

 **Définir la propriété du répertoire de données :**

 ```bash
 sudo chown -R librefolio:librefolio ./LibreFolio-data
 ```

 Ensuite, définissez l'UID/GID correspondant dans `.env`.

## 🛠️ Commandes CLI

Toutes les opérations Docker sont disponibles via `dev.py` :

```bash
./dev.py docker build # Construire l'image (construction automatique du frontend et de la doc)
./dev.py docker build --no-cache # Reconstruction complète sans cache Docker
./dev.py docker rebuild # Build → stop → restart (déploiement en une étape)
./dev.py docker up # Démarrer les conteneurs
./dev.py docker down # Arrêter les conteneurs
./dev.py docker logs -f # Suivre les logs du conteneur
./dev.py docker status # Afficher le statut du conteneur
./dev.py docker exec <cmd> # Exécuter une commande dev.py à l'intérieur du conteneur
```

!!! tip "Documentation avec captures d'écran"

    Si vous construisez la documentation et souhaitez des captures d'écran complètes dans la galerie, exécutez :

    ```bash
    ./dev.py mkdocs --gallery
    ```

    Cela nécessite un environnement entièrement installé (avec `pipenv`) et un serveur en cours d'exécution avec des données de test peuplées. Soyez patient — la génération de la galerie prend quelques minutes.

### 📡 `docker exec` — Exécuter des commandes à l'intérieur du conteneur

La sous-commande `docker exec` transmet n'importe quelle commande `dev.py` dans le conteneur en cours d'exécution :

```bash
./dev.py docker exec user create admin admin@example.com Pass123!
./dev.py docker exec user list
./dev.py docker exec db upgrade
./dev.py docker exec server --test
```

Ceci est équivalent à l'exécution de `docker compose exec librefolio python dev.py <cmd>`.

## 🧪 Mode Test

La configuration Docker Compose expose **deux ports** :

| Port | Usage | Base de données |
|------|---------|----------|
| `8000` | Serveur de production (démarré par le CMD du conteneur) | `prod-docker/sqlite/app.db` (volume persistant) |
| `8001` | Serveur de test (démarré manuellement via `docker exec`) | `test/sqlite/app.db` (éphémère) |

### Démarrer le serveur de test

1. **Démarrez le conteneur** (le serveur de production démarre automatiquement sur `:8000`) :

 ```bash
 docker compose up -d
 ```

2. **Peuplez la base de données de test** avec des données fictives :

 ```bash
 ./dev.py docker exec test db populate --force --with-static
 ```

3. **Démarrez le serveur de test** sur le port 8001 :

 ```bash
 ./dev.py docker exec server --test
 ```

4. **Accédez** à l'adresse **`http://localhost:8001`**

 Identifiants de test :

 | Nom d'utilisateur | Mot de passe |
 |----------|----------|
 | `e2e_test_user` | `E2eTestPass123!` |
 | `e2e_test_admin` | `E2eAdminPass123!` |

!!! warning "Les données de test sont éphémères"

    La base de données de test réside dans la **couche d'écriture** du conteneur, et non sur un montage lié persistant. Cela signifie que :

    - ✅ Les données survivent à `docker compose stop` / `docker compose start` (le conteneur est mis en pause, pas supprimé).
    - ❌ Les données sont **perdues** avec `docker compose down` (le conteneur est supprimé et recréé).

    Si vous avez besoin de données de test persistantes, ajoutez un montage lié dédié dans `docker-compose.yml` :

    ```yaml
    volumes:
    - ./LibreFolio-data:/app/backend/data/prod-docker
    - ./LibreFolio-test-data:/app/backend/data/test # ← ajoutez ceci
    ```

## 🏭 Considérations pour la Production

### 🎮 1. Personnaliser `docker-compose.yml`

Le dépôt inclut un fichier `docker-compose.yml` prêt à l'emploi. Voici le fichier complet avec des annotations montrant ce que vous pouvez personnaliser :

```yaml
services:
 librefolio:
 image: librefolio:latest # Construit par ./dev.py docker build
 build:
 context: .
 args:
 UID: ${UID:-1000} # (1) Correspondre à l'UID de l'utilisateur hôte
 GID: ${GID:-1000} # (1) Correspondre au GID de l'utilisateur hôte
 container_name: librefolio
 # Pas de directive 'user:' — l'entrypoint démarre en root, corrige les permissions,
 # puis bascule vers l'utilisateur 'librefolio' via gosu (même schéma que postgres/redis).
 restart: unless-stopped
 ports:
 - "${PORT:-8000}:8000" # (2) Port de production — modifier via PORT dans .env
 - "${TEST_PORT:-8001}:8001" # (3) Port du serveur de test (optionnel)
 volumes:
 - ./LibreFolio-data:/app/backend/data/prod-docker # (4) Données persistantes (bind mount)
 env_file: .env # (5) Toute la config depuis le fichier .env
 environment:
 - LIBREFOLIO_DATA_DIR=/app/backend/data/prod-docker # Override spécifique à Docker
 - HOST=0.0.0.0
 healthcheck:
 test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/system/health')"]
 interval: 30s
 timeout: 10s
 start_period: 15s
 retries: 3
```

**Personnalisations courantes :**

| # | Quoi | Comment |
|---|------|-----|
| (1) | Correspondre à l'UID/GID hôte | Définir `UID=1001` et `GID=1001` dans `.env`, puis reconstruire |
| (2) | Changer le port de production | Définir `PORT=3000` dans `.env` |
| (3) | Désactiver le port de test | Supprimer la ligne `TEST_PORT` de `ports:` |
| (4) | Chemin de données personnalisé | Modifier le montage lié : `./my-data:/app/backend/data/prod-docker` |
| (5) | Toute la configuration | Modifier le fichier `.env` (copié depuis `.env.example`) |

!!! tip "Premier utilisateur"

    La première fois que vous accédez à LibreFolio dans le navigateur, vous verrez une page d'inscription. Créez votre compte directement — le premier utilisateur devient automatiquement l'administrateur. Pas besoin de CLI.

### 🔒 2. Reverse Proxy

Il est fortement recommandé d'exécuter LibreFolio derrière un reverse proxy comme **Nginx** ou **Traefik**. Cela vous permet de :

- 🔐 Gérer facilement les certificats SSL/TLS pour le HTTPS.
- 🖥️ Servir plusieurs applications sur le même serveur.
- 🛡️ Ajouter des en-têtes de sécurité et une limitation du débit (rate limiting).

### 💾 3. Sauvegarde de la base de données

La base de données est stockée dans le répertoire `LibreFolio-data/` aux côtés de `docker-compose.yml`. Sauvegardez-la directement depuis le système de fichiers de l'hôte :

```bash
#!/bin/bash
cp ./LibreFolio-data/sqlite/app.db /path/to/backups/app.db-$(date +%F)
```

Aucun `docker cp` n'est nécessaire — le répertoire de données est un montage lié accessible depuis l'hôte.

### 🔑 4. Variables d'environnement

Toute la configuration est gérée dans le fichier `.env` (copié depuis `.env.example`). Les overrides spécifiques à Docker dans le bloc `environment:` ne doivent pas être modifiés :

| Variable | Par défaut | Description | Où |
|----------|---------|-------------|-------|
| `PORT` | `8000` | Port hôte pour le serveur de production | `.env` |
| `TEST_PORT` | `8001` | Port hôte pour le serveur de test | `.env` |
| `UID` | `1000` | UID de l'utilisateur conteneur (doit correspondre au propriétaire du répertoire de données) | `.env` |
| `GID` | `1000` | GID de l'utilisateur conteneur (doit correspondre au propriétaire du répertoire de données) | `.env` |
| `LOG_LEVEL` | `INFO` | Verbosité des logs (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `.env` |
| `PORTFOLIO_BASE_CURRENCY` | `EUR` | Devise de base pour les calculs de portefeuille | `.env` |
| `PREVIEW_CACHE_MAX_MB` | `50` | Cache maximum en mémoire pour les aperçus d'images (MB) | `.env` |
| `LIBREFOLIO_DATA_DIR` | `/app/backend/data/prod-docker` | Chemin des données dans le conteneur (ne pas modifier) | `docker-compose.yml` |
| `HOST` | `0.0.0.0` | Adresse de liaison du conteneur (ne pas modifier) | `docker-compose.yml` |
