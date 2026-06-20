# 📦 Installation sur l'Hôte (Pipenv)

Ce guide couvre la configuration de LibreFolio directement sur une machine hôte à l'aide de Python, Node.js et Pipenv. Cette méthode d'installation manuelle convient aux utilisateurs qui souhaitent exécuter LibreFolio sans Docker (par exemple, sur des machines à ressources limitées) et constitue également la première étape pour les développeurs préparant un environnement de développement local.

Pour un déploiement conteneurisé, consultez le [Guide d'Installation du Manuel Utilisateur](../user/installation.md) ou le [Guide Docker Avancé](docker_advanced.md).

---

## ✅ Prérequis

Avant de continuer, assurez-vous que les éléments suivants sont installés sur votre système :

??? info "🐍 Python 3.13+"

    Python 3.13 est requis pour le backend FastAPI.
    
    * **macOS** : Installez à l'aide de Homebrew :
      ```bash
      brew install python@3.13
      ```
    * **Windows** : Téléchargez l'installateur sur [python.org](https://www.python.org/downloads/) (veillez à cocher la case "Add Python to PATH").
    * **Linux (Ubuntu/Debian)** :
      ```bash
      sudo apt update
      sudo apt install python3.13 python3.13-venv python3.13-dev
      ```

??? info "📦 Node.js 20.19+"

    Node.js est requis pour compiler le frontend SvelteKit.
    
    * **macOS** : Installez via Homebrew :
      ```bash
      brew install node@20
      ```
    * **Windows/Linux** : Installez à l'aide de [nvm](https://github.com/nvm-sh/nvm) (Linux/macOS) ou [nvm-windows](https://github.com/coreybutler/nvm-windows) (Windows), ou téléchargez-le directement depuis [nodejs.org](https://nodejs.org/).

??? info "📋 Pipenv"

    Pipenv gère les environnements virtuels et les dépendances pour Python.
    
    * **Toutes les plateformes** :
      ```bash
      pip install --user pipenv
      ```
      *Remarque : Assurez-vous que les chemins des binaires de l'utilisateur (par exemple, `~/.local/bin` sur Linux/macOS ou `%APPDATA%\Python` sur Windows) sont ajoutés à la variable `PATH` de votre shell.*

---

## 📋 Instructions de Configuration

LibreFolio inclut un script d'orchestration principal, `dev.py`, pour automatiser les tâches de gestion courantes.

!!! important "Prérequis pour l'Environnement Python"

    Comme `dev.py` importe des modules du code de l'application backend, l'exécuter directement avant d'installer les dépendances entraînera des exceptions de type `ImportError`. 
    
    Par conséquent, la toute première fois que vous configurez le projet sur votre hôte, vous devez initialiser l'environnement virtuel en exécutant :
    ```bash
    pipenv install --dev
    ```
    Une fois cet environnement virtuel initial configuré, vous pouvez utiliser `dev.py` en toute sécurité pour toutes les étapes suivantes.

!!! tip "Exécution de `dev.py` (Contexte Pipenv)"

    Comme toutes les dépendances du backend sont installées dans l'environnement virtuel géré par `pipenv`, toute exécution de commande sur l'hôte doit être effectuée dans ce contexte :
    
    * **Commandes ponctuelles** : Préfixez votre commande par `pipenv run` (par ex. `pipenv run ./dev.py server`).
    * **Shell interactif** : Exécutez d'abord `pipenv shell` pour entrer dans l'environnement virtuel, après quoi vous pourrez exécuter directement `./dev.py` sans préfixe.
    
    *Remarque : Si vous exécutez des commandes à l'intérieur d'un conteneur Docker en cours d'exécution (par ex. via `docker exec`), vous n'avez **pas** besoin d'utiliser `pipenv run` ou `pipenv shell`. L'image Docker de production pré-installe toutes les dépendances Python globalement dans l'environnement système du conteneur.*

### 📥 1. Télécharger le Projet

Clonez le dépôt :

```bash
git clone https://github.com/Librefolio/LibreFolio.git
cd LibreFolio
```

Ou téléchargez le dernier package de version depuis [GitHub Releases](https://github.com/Librefolio/LibreFolio/releases) et décompressez-le.

### 📦 2. Installer les Dépendances

Une fois votre environnement virtuel initialisé, installez toutes les dépendances restantes de Python, Node.js et du navigateur :

```bash
pipenv run ./dev.py install
```

Sous le capot, cette commande va :

1. Initialiser l'environnement virtuel Python et installer les packages via `pipenv`.
2. Installer les dépendances frontend SvelteKit via `npm`.
3. Installer les binaires du navigateur Playwright (utilisés pour la génération de rapports PDF et les tests E2E).

### ⚙️ 3. Configurer l'Environnement

Copiez l'exemple de fichier d'environnement pour créer votre configuration `.env` active :

```bash
cp .env.example .env
```

Les paramètres par défaut fonctionnent immédiatement. Voici les variables clés :

* **`PORT`** : Port de liaison du serveur (par défaut : `6040`).
* **`LIBREFOLIO_DATA_DIR`** : Chemin du répertoire où la base de données, les téléchargements et les journaux sont stockés (par défaut : `./backend/data/prod`).
* **`LOG_LEVEL`** : Niveau de détail des journaux (par défaut : `INFO`).

Pour une description complète de toutes les variables d'environnement prises en charge, consultez le [Guide des Variables d'Environnement](configuration.md).

### 🚀 4. Démarrer le Serveur

Pour démarrer le serveur FastAPI sur l'hôte :

```bash
pipenv run ./dev.py server
```

Le serveur sera disponible à l'adresse `http://localhost:6040`.

#### Options de la Commande du Serveur

| Option | Description |
|------|-------------|
| `--host HOST` | Adresse de liaison (par défaut : var d'env `HOST` ou `0.0.0.0`) |
| `--port PORT` / `-p PORT` | Port de liaison (par défaut : var d'env `PORT` ou `6040`) |
| `--workers N` / `-w N` | Nombre de processus de travail uvicorn (par défaut : 1, désactive le rechargement automatique) |
| `--no-scheduler` | Désactive les tâches en arrière-plan pour synchroniser les données de marché |

### 👤 5. Accéder à l'Application et Créer des Utilisateurs

La première fois que vous accédez à LibreFolio dans votre navigateur, vous verrez une **page d'inscription** où vous pourrez créer votre premier compte. Le premier utilisateur enregistré devient automatiquement l'administrateur du système.

Pour gérer les utilisateurs ou les promouvoir administrateur via la ligne de commande, reportez-vous au [Guide des Outils CLI pour les Utilisateurs](cli_tools.md).

---

## 🗃️ Initialisation & Réinitialisation de la Base de Données

Lors de la première exécution de l'application, la base de données est automatiquement initialisée. Si vous devez réinitialiser la base de données pour repartir de zéro, vous pouvez le faire de deux manières :

### 1. Commande de Terminal
Vous pouvez exécuter la commande de nettoyage depuis la CLI de la base de données :
```bash
pipenv run ./dev.py db create-clean
```
> [!WARNING]
> Cette commande supprimera complètement la base de données SQLite existante et recréera le schéma à partir de zéro. **Toutes les données seront définitivement perdues.**

### 2. Réinitialisation Manuelle
1. Arrêtez le serveur s'il est en cours d'exécution.
2. Supprimez le fichier de base de données SQLite (situé par défaut dans `backend/data/prod/sqlite/app.db`).
3. Redémarrez le serveur ; il initialisera automatiquement un nouveau fichier de base de données SQLite.
