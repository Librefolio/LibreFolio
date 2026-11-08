# 📦 Installation sur l'hôte (Pipenv)

Installez LibreFolio sur votre machine sans Docker, avec Python, Node.js et Pipenv : pratique quand les ressources sont limitées, et première étape vers un environnement de développement.

Pour Docker, voir l'[Installation du Manuel Utilisateur](../user/installation.md) ou le [Guide Docker Avancé](docker_advanced.md).

---

## ✅ Prérequis

Installez d'abord ces trois outils.

??? info "🐍 Python 3.13"

    La version définie dans le `Pipfile` du projet.

    * **macOS**, avec Homebrew :
      ```bash
      brew install python@3.13
      ```
    * **Windows** : téléchargez l'installateur depuis [python.org](https://www.python.org/downloads/) et cochez « Add Python to PATH ».
    * **Linux (Ubuntu/Debian)** :
      ```bash
      sudo apt update
      sudo apt install python3.13 python3.13-venv python3.13-dev
      ```

??? info "📦 Node.js 24+"

    Construit l'interface web.

    * **macOS**, avec Homebrew :
      ```bash
      brew install node@24
      ```
    * **Windows/Linux** : avec [nvm](https://github.com/nvm-sh/nvm) (Linux/macOS) ou [nvm-windows](https://github.com/coreybutler/nvm-windows) (Windows), ou téléchargez depuis [nodejs.org](https://nodejs.org/).

??? info "📋 Pipenv"

    Gère l'environnement virtuel Python et ses paquets.

    * **Toutes les plateformes** :
      ```bash
      pip install --user pipenv
      ```
      Ajoutez le dossier des binaires de l'utilisateur (`~/.local/bin` sous Linux/macOS, `%APPDATA%\Python` sous Windows) au `PATH` du shell.

---

## 📋 Instructions d'installation

!!! tip "Les commandes s'exécutent dans l'environnement Pipenv"

    Les commandes `dev.py` commencent par `pipenv run`, qui les exécute dans l'environnement virtuel du projet.
    Ou entrez-y une fois avec `pipenv shell`, puis tapez `./dev.py …` sans le préfixe.

### 📥 1. Télécharger le projet

**Où :** terminal, dans le dossier où vous voulez placer le projet.

```bash
git clone https://github.com/Librefolio/LibreFolio.git
cd LibreFolio
```

Résultat : le dossier `LibreFolio/`. Ou téléchargez et décompressez la dernière version depuis [GitHub Releases](https://github.com/Librefolio/LibreFolio/releases).

### 🐍 2. Créer l'environnement Python

**Où :** terminal, dossier `LibreFolio/`.

```bash
pipenv install --dev
```

Résultat : l'environnement virtuel avec les paquets Python. Faites-le avant toute commande `dev.py` : sans cela, elle s'arrête avec `ModuleNotFoundError`.

### 📦 3. Installer les autres dépendances

**Où :** terminal, dossier `LibreFolio/`.

```bash
pipenv run ./dev.py install
```

Résultat, dans l'ordre :

1. à nouveau les paquets Python (`pipenv install --dev`) ;
2. les outils du projet (`npm ci`) ;
3. les dépendances de l'interface web (`npm ci` dans `frontend/`) ;
4. le navigateur Chromium de Playwright, pour les tests de bout en bout et les captures d'écran de la documentation. Si seul ce téléchargement échoue, l'installation se termine quand même.

### ⚙️ 4. Configurer l'environnement

**Où :** terminal, dossier `LibreFolio/` ; puis le fichier `.env` qui vient d'être créé.

```bash
cp .env.example .env
```

Résultat : le fichier `.env` avec des valeurs par défaut qui conviennent telles quelles. Les principales variables :

| Variable | Défaut | Description |
| --- | --- | --- |
| `PORT` | `6040` | Port de liaison du serveur. |
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Répertoire de la base de données, des fichiers téléversés et des journaux (voir [Structure du système de fichiers](filesystem.md)). |
| `LOG_LEVEL` | `INFO` | Niveau de verbosité des journaux. |

Les autres variables : [Guide des variables d'environnement](configuration.md).

### 🚀 5. Démarrer le serveur

**Où :** terminal, dossier `LibreFolio/`.

```bash
pipenv run ./dev.py server
```

Résultat : LibreFolio répond sur `http://localhost:6040`. Le premier démarrage construit l'interface web et la documentation : quelques minutes. Workers, autre port, autres options : [Outils en ligne de commande](cli_tools.md#start-the-server).

### 👤 6. Créer votre compte

**Où :** navigateur, `http://localhost:6040`, lien **Inscrivez-vous ici** sous le formulaire de connexion.

Résultat : le premier compte enregistré devient l'administrateur. Pour gérer les utilisateurs depuis le terminal, voir [Outils en ligne de commande](cli_tools.md). Pour que LibreFolio crée lui-même l'administrateur à son premier démarrage, voir [L'administrateur initial](configuration_accounts.md#initial-admin).

---

## 🗃️ Initialisation et réinitialisation de la base de données {: #database-reset }

Il n'y a rien à initialiser : à chaque démarrage, le serveur crée la base de données si elle est absente et applique les migrations en attente.

Pour repartir d'une **base de données vide**, utilisez l'une des deux méthodes ci-dessous.

!!! warning "Toutes les données sont perdues"

    Les deux méthodes suppriment définitivement la base de données : utilisateurs, courtiers, transactions et paramètres. Faites d'abord une sauvegarde (voir [Sauvegarde](filesystem.md#backup)).

### 🧹 Avec `dev.py`

**Où :** terminal, dossier `LibreFolio/`, serveur arrêté (la commande refuse de s'exécuter tant que le serveur est en marche).

```bash
pipenv run ./dev.py db create-clean
```

Résultat : une nouvelle base de données vide.

### 🗑️ Manuellement

**Où :** le répertoire de données, par défaut `backend/data/prod/`.

1. Arrêtez le serveur s'il est en cours d'exécution.
2. Supprimez le fichier de base de données SQLite, par défaut `backend/data/prod/sqlite/app.db`.
3. Démarrez le serveur : il en crée une nouvelle.

Les deux méthodes ne remplacent que la base de données : les fichiers téléversés, les rapports de courtier et les journaux restent dans le répertoire de données. Pour un démarrage complètement neuf, arrêtez le serveur et supprimez tout le répertoire de données : le prochain démarrage le recrée.
