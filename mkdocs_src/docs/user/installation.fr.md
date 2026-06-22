# 🐳 Installation avec Docker (Utilisateur)

Ce guide explique comment installer et exécuter LibreFolio pour un usage régulier à l'aide de l'image Docker officielle précompilée. C'est la méthode la plus simple et recommandée pour les utilisateurs finaux.

Vous n'avez pas besoin d'installer des outils de développement ou de compiler le code sur votre machine hôte (aucun prérequis concernant Python, Node.js ou Pipenv).

---

## ✅ Prérequis

Avant de commencer, assurez-vous d'avoir installé **Docker** (qui inclut Docker Compose) sur votre machine hôte. Selon votre système d'exploitation, vous pouvez suivre ces étapes :

=== "Linux"

    La plupart des distributions Linux permettent l'installation via leurs dépôts officiels.
    
    Pour les distributions basées sur Debian/Ubuntu :
    ```bash
    sudo apt-get update
    sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    ```
    
    !!! warning "Permissions du groupe Docker (Linux)"
        Sur Linux, votre utilisateur système doit appartenir au groupe `docker` pour exécuter les commandes sans `sudo` :
        ```bash
        sudo usermod -aG docker $USER
        ```
        Ensuite, **déconnectez-vous et reconnectez-vous** (ou exécutez `newgrp docker`) pour appliquer les modifications à la session de terminal actuelle.

=== "macOS"

    Sur macOS, la méthode recommandée est d'installer **Docker Desktop** :
    
    - [Télécharger Docker Desktop pour Mac](https://docs.docker.com/desktop/install/mac-install/) (disponible pour Apple Silicon ou Intel).
    - Alternativement, si vous utilisez Homebrew, vous pouvez l'installer via le terminal :
      ```bash
      brew install --cask docker
      ```

=== "Windows"

    Sur Windows, installez **Docker Desktop** :
    
    - Téléchargez et installez [Docker Desktop pour Windows](https://docs.docker.com/desktop/install/windows-install/).
    - Assurez-vous d'activer le moteur **WSL 2** lors de l'installation pour des performances optimales.

---

## 🚀 Installation Étape par Étape

### 📁 1. Créer un dossier pour le projet

📂 Naviguez vers le dossier dans lequel vous souhaitez enregistrer le projet (par exemple, votre dossier utilisateur ou vos documents), créez un nouveau répertoire pour LibreFolio et accédez-y :

```bash
# 🏠 Allez dans le dossier principal où vous souhaitez placer le projet (ex. Documents)
cd /chemin/vers/votre/dossier

# 📁 Créez et accédez au dossier de LibreFolio
mkdir librefolio
cd librefolio
```

### 📥 2. Récupérer les fichiers de configuration de base

⚙️ Pour démarrer LibreFolio, vous aurez besoin du fichier `docker-compose.yml` (qui décrit la pile de conteneurs) et du fichier `.env` (qui contient vos paramètres d'environnement personnalisés).

⬇️ Vous pouvez les télécharger directement depuis le dépôt GitHub officiel en utilisant l'une des commandes suivantes :

=== "wget"

    ```bash
    # 📥 Téléchargez le fichier docker-compose.yml officiel
    wget https://raw.githubusercontent.com/Librefolio/LibreFolio/main/docker-compose.prod.yml -O docker-compose.yml

    # 🔑 Téléchargez le fichier .env.example et enregistrez-le sous .env
    wget https://raw.githubusercontent.com/Librefolio/LibreFolio/main/.env.example -O .env
    ```

=== "curl"

    ```bash
    # 📥 Téléchargez le fichier docker-compose.yml officiel
    curl -L https://raw.githubusercontent.com/Librefolio/LibreFolio/main/docker-compose.prod.yml -o docker-compose.yml

    # 🔑 Téléchargez le fichier .env.example et enregistrez-le sous .env
    curl -L https://raw.githubusercontent.com/Librefolio/LibreFolio/main/.env.example -o .env
    ```

✍️ Alternativement, vous pouvez créer manuellement un fichier nommé `docker-compose.yml` et y coller le code suivant :

```yaml
services:
  librefolio:
    image: ghcr.io/librefolio/librefolio:latest
    container_name: librefolio
    restart: unless-stopped
    ports:
      - "6040:6040"
    volumes:
      - ./librefolio-data:/app/backend/data/prod-docker
    env_file: .env
    environment:
      - LIBREFOLIO_DATA_DIR=/app/backend/data/prod-docker
      - HOST=0.0.0.0
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:6040/api/v1/system/health')"]
      interval: 30s
      timeout: 10s
      start_period: 15s
      retries: 3
```

💡 *(Si vous n'avez pas téléchargé le fichier `.env.example`, supprimez la ligne `env_file: .env` du code ci-dessus, ou créez un fichier `.env` vide pour éviter les erreurs de démarrage).*

### ▶️ 3. Démarrer l'application

🚀 Démarrez le conteneur en arrière-plan (mode détaché) en exécutant :

```bash
docker compose up -d
```

📦 Docker va télécharger l'image officielle depuis le registre de conteneurs GitHub (GHCR) et démarrer LibreFolio.

### 🌐 4. Accéder à LibreFolio

🖥️ Une fois le conteneur démarré, ouvrez votre navigateur et accédez à :

**`http://localhost:6040`**

👤 Lors du premier accès, la page d'inscription s'affichera pour créer le compte administrateur de LibreFolio. Le premier utilisateur à s'inscrire recevra automatiquement les privilèges d'administrateur.

!!! tip "Surveillance de l'état et des journaux avec Portainer"

    Si vous préférez une interface graphique pratique pour surveiller l'état de votre conteneur LibreFolio et consulter ses journaux en temps réel, nous vous recommandons d'utiliser **[Portainer](https://github.com/portainer/portainer)**, un outil de gestion Docker léger et largement utilisé.

### 📶 5. Accès Réseau Local et Distant

Une fois démarré, LibreFolio sera accessible :

- 💻 Directement depuis l'**ordinateur hôte** en visitant `http://localhost:6040`.
- 📱 Depuis d'**autres appareils sur le même réseau local (LAN)** (par exemple, smartphones, tablettes, autres PC) en saisissant l'adresse IP locale de l'ordinateur hôte dans le navigateur (par exemple, `http://192.168.1.100:6040`).

#### 🛡️ Configuration du Pare-feu (facoltatif)
Si vous ne pouvez pas accéder à LibreFolio depuis d'autres appareils du réseau local, il se peut que vous deviez ouvrir le port `6040` dans le pare-feu de l'ordinateur hôte :

=== "Debian / Ubuntu (UFW)"

    ```bash
    sudo ufw allow 6040/tcp
    ```

=== "RHEL / Rocky Linux / Fedora (Firewalld)"

    ```bash
    sudo firewall-cmd --add-port=6040/tcp --permanent
    sudo firewall-cmd --reload
    ```

#### 🌐 Accès Distant
Pour accéder à LibreFolio en toute sécurité lorsque vous n'êtes pas chez vous (en dehors du réseau local), vous êtes libre de configurer la solution de votre choix (telle qu'un reverse proxy avec certificat SSL).

Cependant, pour une simplicité et une sécurité maximales sans ouvrir de ports sur votre routeur, **nous recommandons l'utilisation de Tailscale**. Vous trouverez tous les détails et un guide étape par étape sur la page [Exposition avec Tailscale](../admin/tailscale_exposure.md).

---

## ⚙️ Options de Configuration

Tous les paramètres de LibreFolio (tels que les ports, la devise de base et les clés de sécurité de session) sont gérés via des variables d'environnement dans le fichier `.env`.

Pour plus de détails sur chaque option et sur la façon dont les variables sont résolues, consultez le [Guide de Configuration du Manuel Administrateur](../admin/configuration.md).

---

## 💾 Sauvegarde des Données

Toutes les données de LibreFolio (base de données SQLite, fichiers téléversés par les utilisateurs, rapports chargés et journaux) sont sauvegardées localement dans le dossier `./librefolio-data` créé à côté du fichier `docker-compose.yml`.

Pour des instructions détaillées sur ce qu'il faut sauvegarder et comment effectuer des sauvegardes cohérentes, consultez la [Section Sauvegarde du Manuel Administrateur](../admin/filesystem.md#backup).

---

## 🔄 Mise à jour de LibreFolio

### ⚠️ Attention : Statut Alpha
LibreFolio est actuellement en cours de développement **Alpha**. Cela signifie qu'entre les versions, il pourrait y avoir des modifications structurelles ou des migrations de base de données susceptibles d'empêcher le démarrage de la nouvelle version, nécessitant une intervention manuelle ou la restauration d'une version précédente.

- En utilisant le tag `:latest` dans le fichier `docker-compose.yml`, vous recevrez immédiatement les dernières fonctionnalités mais vous vous exposerez à de potentielles incompatibilités lors des mises à jour automatiques.
- Si vous préférez la stabilité et un contrôle absolu, nous vous recommandons de figer l'image en remplaçant `:latest` par un tag de version spécifique (par exemple, `ghcr.io/librefolio/librefolio:v0.10.0`).

### 🛠️ 1. Mise à jour Manuelle

Pour mettre à jour LibreFolio manuellement vers la dernière version disponible :

```bash
# 🛑 Arrêtez le conteneur en cours d'exécution
docker compose down

# 📥 Téléchargez la version la plus récente de l'image depuis le registre
docker compose pull

# 🚀 Redémarrez LibreFolio en appliquant la nouvelle image
docker compose up -d
```

Les migrations de la base de données seront exécutées automatiquement au démarrage du conteneur.

### 🤖 2. Mise à jour Automatique (Watchtower)

Si vous souhaitez automatiser les mises à jour des conteneurs dès qu'une nouvelle image est publiée sur le registre, vous pouvez utiliser **Watchtower** (nous vous recommandons le fork actif et mis à jour de [nicholas-fedor/watchtower](https://github.com/nicholas-fedor/watchtower)).

!!! note "Comportement par défaut"

    Par défaut, Watchtower surveille et met à jour tous les conteneurs actifs sur le système. Pour plus de détails et des options avancées, consultez le [dépôt officiel du projet](https://github.com/nicholas-fedor/watchtower).

Pour plus de commodité, si vous souhaitez limiter les vérifications du logiciel uniquement à LibreFolio et exécuter la vérification de manière hebdomadaire (par exemple, tous les dimanches à 4h00 via une expression Cron), vous pouvez démarrer Watchtower avec cette commande :

```bash
docker run -d \
  --name watchtower \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e TZ=Europe/Rome \
  nicholas-fedor/watchtower \
  --cleanup \
  --schedule "0 0 4 * * 0" \
  librefolio
```
💡 *(Cette commande démarre Watchtower en arrière-plan avec accès au socket Docker. Elle recherchera de nouvelles images sur le registre uniquement pour le conteneur `librefolio` chaque dimanche à 04:00:00, en supprimant les anciennes images pour gagner de l'espace. Modifiez `TZ` pour définir votre fuseau horaire de référence).*

### 🔌 3. Autres Alternatives de Gestion

Si vous souhaitez une approche différente ou plus de contrôle sur les notifications et le déploiement des versions, il existe d'excellentes alternatives :

- **[WUD (What's Up Docker)](https://github.com/fmartinou/whats-up-docker)**  
  Outil moderne pour les homelabs doté d'une **interface web** pratique.  
  Il est extrêmement modulaire et prend en charge les notifications via Telegram, Discord et Gotify.  
  Il permet d'envoyer des alertes concernant les nouvelles versions sans mise à jour automatique, vous laissant le choix du moment pour le faire.  
  
- **[Diun (Docker Image Update Notifier)](https://github.com/crazy-max/diun)**  
  Un notificateur pur, léger et sécurisé.  
  Il ne nécessite pas de droits d'écriture sur le socket Docker.  
  Il surveille les registres d'images en mode lecture seule et vous avertit lorsqu'une nouvelle version de LibreFolio est publiée.
