# 🐳 Installation (Utilisateur)

Ce guide explique comment déployer LibreFolio pour un usage régulier en utilisant Docker. C'est la méthode recommandée pour les utilisateurs qui n'ont pas l'intention de modifier le code source.

## ✅ Prérequis

- 🐍 **Python 3.13+** : [Installer Python](https://www.python.org/downloads/)
- 📦 **Node.js 20.19+** : [Installer Node.js](https://nodejs.org/) (inclut npm)
- 📋 **Pipenv** : `pip install pipenv`
- 🐋 **Docker** : [Installer Docker](https://docs.docker.com/get-docker/) (inclut Docker Compose)

!!! warning "Groupe Docker (Linux)"

    Sur Linux, votre utilisateur doit appartenir au groupe `docker` pour exécuter les commandes Docker sans `sudo` :

    ```bash
    sudo usermod -aG docker $USER
    ```

    Ensuite, **déconnectez-vous et reconnectez-vous**, ou exécutez `newgrp docker` pour activer le groupe dans la session actuelle.

!!! note "Pourquoi Python et Node.js ?"

    LibreFolio utilise une **image Docker d'exécution seule** — le frontend et la documentation sont construits sur l'hôte avant d'être empaquetés dans l'image Docker. Des images pré-construites sur un registre de conteneurs sont prévues pour les prochaines versions.

## 📥 1. Télécharger le Projet

Clonez le dépôt :

```bash
git clone https://github.com/Alfystar/LibreFolio.git
cd LibreFolio
```

Ou téléchargez la dernière version depuis [GitHub Releases](https://github.com/Alfystar/LibreFolio/releases) et dézippez-la.

## ⚙️ 2. Configurer l'Environnement

1. **Copiez le fichier d'exemple** (requis — le build refusera de continuer sans `.env`) :

 ```bash
 cp .env.example .env
 ```

2. **Modifiez `.env`** pour personnaliser :

 - 🔌 `PORT` : Changez le port si `6040` est déjà utilisé.
 - 💰 `PORTFOLIO_BASE_CURRENCY` : Votre devise de base du portefeuille (par défaut : `EUR`).
 - 📊 `LOG_LEVEL` : Verbosité des journaux (par défaut : `INFO`).

## 📦 3. Installer les Dépendances

```bash
./dev.py install
```

Ceci installe les dépendances Python (backend) et Node.js (frontend).

## 🏗️ 4. Construire l'Image Docker

```bash
./dev.py docker build
```

Cette commande effectue automatiquement :

1. La construction du frontend (build de production SvelteKit)
2. La construction du site de documentation (MkDocs)
3. L'empaquetage de l'ensemble des composants dans une seule image Docker taguée `librefolio:latest`

## 🚀 5. Démarrer avec Docker Compose

```bash
docker compose up -d
```

- 🔄 `-d` exécute l'application en mode détaché (en arrière-plan).

## 🌐 6. Accéder à LibreFolio

Ouvrez votre navigateur et allez à l'adresse :

**`http://localhost:6040`**

(Ou utilisez le port que vous avez configuré dans `.env`).

La première fois que vous accéderez à LibreFolio, une **page d'inscription** s'affichera — créez votre compte directement depuis le navigateur. Le premier utilisateur enregistré devient automatiquement l'administrateur.

Points de terminaison disponibles :

- 🏠 **Frontend** : `http://localhost:6040/`
- 📚 **Docs Utilisateur** : `http://localhost:6040/mkdocs/`

!!! tip "Gestion des utilisateurs via CLI"

    Vous pouvez également gérer les utilisateurs depuis la ligne de commande. Consultez le [Manuel Admin — Outils CLI](../admin/cli_tools.md) pour les commandes de création, de promotion et de listage des utilisateurs.

## 🔄 Mettre à jour LibreFolio

Pour passer à une nouvelle version :

1. **Récupérez la dernière version du code** :

 ```bash
 git pull
 ```

2. **Reconstruisez l'image Docker** (reconstruit automatiquement le frontend et la doc si modifiés) :

 ```bash
 ./dev.py docker rebuild
 ```

 Cette commande construit une nouvelle image, arrête les conteneurs en cours et redémarre avec la nouvelle version.

3. Les **migrations de base de données** sont appliquées automatiquement au démarrage.

## 🧪 Essayer avec des Données de Test (Optionnel)

Vous pouvez démarrer un serveur de test avec des données fictives pré-remplies pour explorer l'application avant d'y saisir des données réelles :

```bash
./dev.py docker exec test db populate --force --with-static
./dev.py docker exec server --test
```

Accédez à **`http://localhost:6041`** avec l'utilisateur `e2e_test_user` / `E2eTestPass123!`.

Le serveur de test s'exécute parallèlement au serveur de production, en utilisant une base de données séparée. Voir le [Guide Docker Avancé](../admin/docker_advanced.md#test-mode) pour plus de détails.

---

!!! tip "Sujets avancés"

    Pour la configuration d'un reverse proxy, les sauvegardes de base de données, les chemins de données personnalisés et les considérations de production, consultez le [🐳 Guide Docker Avancé](../admin/docker_advanced.md).
