# 📦 Installation sur l'hôte (Pipenv)

Ce guide installe LibreFolio directement sur votre machine avec Python, Node.js et Pipenv, sans Docker : pratique sur les machines à faibles ressources, et la première étape vers un environnement de développement.

Pour Docker, voir l'[Installation du Manuel Utilisateur](../user/installation.md) ou le [Guide Docker Avancé](docker_advanced.md).

---

## ✅ Prérequis

Installez d'abord ces trois outils.

??? info "🐍 Python 3.13"

    Le backend a besoin de Python 3.13, la version définie dans le `Pipfile` du projet.

    * **macOS** : Installez avec Homebrew :
      ```bash
      brew install python@3.13
      ```
    * **Windows** : Téléchargez l'installateur depuis [python.org](https://www.python.org/downloads/) (assurez-vous de cocher « Add Python to PATH »).
    * **Linux (Ubuntu/Debian)** :
      ```bash
      sudo apt update
      sudo apt install python3.13 python3.13-venv python3.13-dev
      ```

??? info "📦 Node.js 24+"

    Node.js construit l'interface web.

    * **macOS** : Installez via Homebrew :
      ```bash
      brew install node@24
      ```
    * **Windows/Linux** : Installez avec [nvm](https://github.com/nvm-sh/nvm) (Linux/macOS) ou [nvm-windows](https://github.com/coreybutler/nvm-windows) (Windows), ou téléchargez directement depuis [nodejs.org](https://nodejs.org/).

??? info "📋 Pipenv"

    Pipenv gère l'environnement virtuel Python et ses paquets.

    * **Toutes les plateformes** :
      ```bash
      pip install --user pipenv
      ```
      *Remarque : Assurez-vous que les chemins d'accès aux binaires de votre base utilisateur (par ex. `~/.local/bin` sous Linux/macOS ou `%APPDATA%\Python` sous Windows) sont ajoutés à la variable `PATH` de votre shell.*

---

## 📋 Instructions d'installation

!!! tip "Les commandes s'exécutent dans l'environnement Pipenv"

    Les commandes `dev.py` commencent par `pipenv run`, qui les exécute dans l'environnement virtuel du projet. Vous pouvez aussi l'activer une fois avec `pipenv shell`, puis taper `./dev.py …` sans le préfixe.

### 📥 1. Télécharger le projet

```bash
git clone https://github.com/Librefolio/LibreFolio.git
cd LibreFolio
```

Ou téléchargez le paquet de la dernière version depuis [GitHub Releases](https://github.com/Librefolio/LibreFolio/releases) et décompressez-le.

### 🐍 2. Créer l'environnement Python

```bash
pipenv install --dev
```

Faites-le avant toute commande `dev.py` : `dev.py` a besoin de ces paquets Python, et sans eux il s'arrête avec une `ModuleNotFoundError`.

### 📦 3. Installer les autres dépendances

```bash
pipenv run ./dev.py install
```

Dans l'ordre, il installe :

1. à nouveau les paquets Python, avec `pipenv install --dev` ;
2. les outils du projet, avec `npm install` ;
3. les dépendances de l'interface web, avec `npm ci` dans `frontend/` ;
4. le navigateur Chromium de Playwright, utilisé par les tests de bout en bout et les captures d'écran de la documentation. Si seul ce téléchargement échoue, l'installation se termine quand même.

### ⚙️ 4. Configurer l'environnement

```bash
cp .env.example .env
```

Les valeurs par défaut conviennent telles quelles. Les principales variables :

| Variable | Défaut | Description |
| --- | --- | --- |
| `PORT` | `6040` | Port de liaison du serveur. |
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Répertoire où sont stockés la base de données, les téléversements et les journaux (voir [Structure du système de fichiers](filesystem.md)). |
| `LOG_LEVEL` | `INFO` | Niveau de verbosité des journaux. |

Les autres variables sont décrites dans le [Guide des variables d'environnement](configuration.md).

### 🚀 5. Démarrer le serveur

```bash
pipenv run ./dev.py server
```

Le premier démarrage construit l'interface web et la documentation, cela prend donc quelques minutes. Ensuite, ouvrez `http://localhost:6040`. Pour les workers, un autre port et les autres options, voir [Outils en ligne de commande](cli_tools.md#start-the-server).

### 👤 6. Créer votre compte

Ouvrez LibreFolio dans votre navigateur et choisissez **S'inscrire ici** sous le formulaire de connexion : le premier compte enregistré devient l'administrateur. Pour gérer les utilisateurs depuis le terminal, voir [Outils en ligne de commande](cli_tools.md).

---

## 🗃️ Initialisation et réinitialisation de la base de données {: #database-reset }

Il n'y a rien à initialiser manuellement : à chaque démarrage, le serveur crée la base de données si elle est absente et applique toute migration en attente.

Pour repartir d'une **base de données vide**, utilisez l'une des deux méthodes ci-dessous.

!!! warning "Toutes les données sont perdues"

    Les deux méthodes suppriment définitivement la base de données : utilisateurs, courtiers, transactions et paramètres. Sauvegardez-la d'abord (voir [Sauvegarde](filesystem.md#backup)).

### 🧹 Avec `dev.py`

Arrêtez le serveur (la commande refuse de s'exécuter tant qu'il est en marche), puis :

```bash
pipenv run ./dev.py db create-clean
```

### 🗑️ Manuellement

1. Arrêtez le serveur s'il est en cours d'exécution.
2. Supprimez le fichier de base de données SQLite (par défaut `backend/data/prod/sqlite/app.db`).
3. Démarrez le serveur : il crée une nouvelle base de données.

Les deux méthodes ne remplacent que la base de données : les fichiers téléversés, les rapports de courtier et les journaux restent dans le répertoire de données. Pour un démarrage complètement neuf, arrêtez le serveur et supprimez plutôt tout le répertoire de données (par défaut `backend/data/prod/`) : le prochain démarrage le recrée.
