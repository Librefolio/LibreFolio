# 🐳 Installation (Utilisateur)

Ce guide explique comment déployer LibreFolio pour **un usage courant** à l'aide de Docker. C'est la méthode recommandée pour les utilisateurs qui n'ont pas l'intention de modifier le code source.

## ✅ Prérequis

- 🐋 **Docker** : [Installer Docker](https://docs.docker.com/get-docker/)
- 🔗 **Docker Compose** : Généralement inclus avec Docker Desktop.

## 📥 1. Télécharger le projet

Téléchargez la dernière version depuis la page [GitHub Releases](https://github.com/ea-enel/LibreFolio/releases). Décompressez le dossier.

Alternativement, vous pouvez cloner le dépôt :

```bash
git clone https://github.com/ea-enel/LibreFolio.git
cd LibreFolio
```

## ⚙️ 2. Configurer l'environnement

Le projet utilise un fichier `.env` pour la configuration. Un fichier d'exemple est fourni.

1. **Copiez le fichier d'exemple** :
 ```bash
 cp .env.example .env
 ```

2. **Éditez `.env`** (Optionnel) :
 - 🔌 `PORT` : Modifiez le port si `8000` est déjà utilisé.
 - 📁 `LIBREFOLIO_DATA_DIR` : Changez l'emplacement de stockage des données (par défaut : `./backend/data/prod`).

## 🚀 3. Lancer avec Docker Compose

**Cette seule commande va générer** les images et démarrer l'application.

```bash
docker-compose up -d
```

- 🔄 `-d` exécute l'application **en mode détaché** (en arrière-plan).
- ⏳ La première fois, Docker téléchargera les images de base nécessaires et générera l'application, ce qui peut prendre quelques minutes.

## 👤 4. Créer un superutilisateur

Pour vous connecter, vous devez créer **un compte admin**. Le premier utilisateur créé devient automatiquement le superutilisateur.

Exécutez la commande suivante (via `docker-compose exec` dans le conteneur `backend` en utilisant le script `dev.py`) :

```bash
docker-compose exec backend ./dev.py user create <nom_utilisateur> <email> <mot_de_passe>
```

Remplacez `<nom_utilisateur>`, `<email>` et `<mot_de_passe>` par vos identifiants.

## 🌐 5. Accéder à LibreFolio

L'application est maintenant en cours d'exécution ! Ouvrez votre navigateur et allez à :

**`http://localhost:8000`**

(Ou utilisez le port configuré dans `.env`).

## 🔄 Mettre à jour LibreFolio

Pour mettre à jour vers une nouvelle version :

1. **Récupérer la dernière version du code** :
 ```bash
 git pull
 ```

2. **Reconstruire et redémarrer les conteneurs** :
 ```bash
 docker-compose up -d --build
 ```

3. **Appliquer les migrations** (le cas échéant) :
 ```bash
 docker-compose exec backend pipenv run alembic upgrade head
 ```

---
