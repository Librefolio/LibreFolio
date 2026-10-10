# 🐳 Installation avec Docker (Utilisateur)

Ce guide installe LibreFolio avec l'image Docker officielle pré-construite : la méthode la plus simple et recommandée pour l'exécuter chez vous.

Vous avez seulement besoin de Docker : pas de Python, Node.js ni Pipenv, et rien à compiler.

---

## ✅ Prérequis

Installez **Docker**, qui inclut Docker Compose, sur l'ordinateur qui exécutera LibreFolio :

=== "Linux"

    Suivez le guide officiel de Docker pour votre distribution : [Installer Docker Engine](https://docs.docker.com/engine/install/). Sur Debian et Ubuntu, le guide ajoute d'abord le dépôt de paquets Docker, puis installe :

    ```bash
    sudo apt-get update
    sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    ```

    !!! warning "Autorisations du groupe Docker (Linux)"

        Sur Linux, votre utilisateur système doit appartenir au groupe `docker` pour exécuter des commandes sans `sudo` :

        ```bash
        sudo usermod -aG docker $USER
        ```

        Ensuite, **déconnectez-vous puis reconnectez-vous** (ou exécutez `newgrp docker`) pour appliquer les changements à votre session de terminal actuelle.

=== "macOS"

    Installez **Docker Desktop** :

    - [Télécharger Docker Desktop pour Mac](https://docs.docker.com/desktop/install/mac-install/) (Apple Silicon ou Intel).
    - Ou, avec Homebrew :

      ```bash
      brew install --cask docker-desktop
      ```

=== "Windows"

    Installez **Docker Desktop** :

    - Téléchargez et installez [Docker Desktop pour Windows](https://docs.docker.com/desktop/install/windows-install/).
    - Activez le backend **WSL 2** lors de l'installation pour de meilleures performances.

---

## 🚀 Installation pas à pas

### 📁 1. Créer un dossier de projet

Ouvrez un terminal, rendez-vous dans le dossier où vous souhaitez conserver LibreFolio (par exemple votre dossier Documents), puis créez un dossier `librefolio` et entrez dedans :

```bash
# 🏠 Allez dans le dossier principal où vous voulez placer le projet (par ex. Documents)
cd /path/to/your/folder

# 📁 Créez et entrez dans le dossier LibreFolio
mkdir librefolio
cd librefolio
```

### 📥 2. Obtenir les fichiers de configuration de base

LibreFolio a besoin de deux fichiers : `docker-compose.yml`, qui décrit le conteneur, et `.env`, qui contient vos paramètres. Téléchargez les deux depuis le dépôt officiel avec l'une de ces commandes :

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

La stack exécute l'image officielle depuis le GitHub Container Registry (GHCR) et conserve toutes vos données dans un dossier `LibreFolio-data` à côté de `docker-compose.yml`.

??? example "✍️ Vous préférez écrire `docker-compose.yml` à la main ?"

    Créez un fichier nommé `docker-compose.yml` et collez ce contenu, le même service que le fichier officiel :

    ```yaml
    services:
      librefolio:
        image: ${LIBREFOLIO_IMAGE:-ghcr.io/librefolio/librefolio:latest}
        container_name: librefolio
        restart: unless-stopped
        ports:
          - "${PORT:-6040}:6040"
        volumes:
          - ./LibreFolio-data:/app/backend/data/prod-docker
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

    La ligne `env_file: .env` nécessite un fichier `.env` dans le même dossier : téléchargez-le comme indiqué ci-dessus, ou créez-en un vide, sinon Docker s'arrête avec une erreur.

### ▶️ 3. Démarrer l'application

Démarrez LibreFolio en arrière-plan :

```bash
docker compose up -d
```

Docker télécharge l'image officielle depuis GHCR et démarre LibreFolio. Le tag `latest` est la [variante light](#image-variants-full-and-light) de l'image, la valeur par défaut recommandée.

### 🌐 4. Accéder à LibreFolio

Ouvrez votre navigateur à l'adresse **`http://localhost:6040`**.

Lors de votre première visite, LibreFolio affiche la page d'inscription : le premier compte que vous créez devient automatiquement **administrateur**.

??? tip "🖥️ Surveiller l'état et les logs (facultatif)"

    Depuis le terminal, `docker compose logs -f` suit les logs de LibreFolio (`Ctrl+C` arrête le suivi). Pour une vue graphique de vos conteneurs et de leurs logs en temps réel, essayez **[Portainer](https://github.com/portainer/portainer)**, un outil de gestion Docker léger et largement utilisé.

### 📶 5. Accès réseau local et distant

Une fois démarré, LibreFolio est accessible :

- 💻 depuis l'**ordinateur hôte**, à `http://localhost:6040` ;
- 📱 depuis **d'autres appareils sur le même réseau local** (smartphones, tablettes, autres PC), à l'adresse IP locale de l'ordinateur hôte, par exemple `http://192.168.1.100:6040`.

??? note "🛡️ Pare-feu — uniquement si d'autres appareils ne peuvent pas se connecter"

    Ouvrez le port `6040` dans le pare-feu de l'ordinateur hôte :

    === "Debian / Ubuntu (UFW)"

        ```bash
        sudo ufw allow 6040/tcp
        ```

    === "RHEL / Rocky Linux / Fedora (Firewalld)"

        ```bash
        sudo firewall-cmd --add-port=6040/tcp --permanent
        sudo firewall-cmd --reload
        ```

🌍 **En dehors de chez vous**, utilisez la solution que vous préférez, comme un proxy inverse avec un certificat SSL. Pour la configuration la plus simple et la plus sûre, sans ouvrir de ports sur votre routeur, **nous recommandons Tailscale** : voir [Exposition avec Tailscale](../admin/service_exposure.md).

---

## 🏷️ Variantes d'image : Full et Light {: #image-variants-full-and-light }

L'image officielle existe en deux variantes. Les deux contiennent l'application complète et toutes les pages de texte de la documentation, dans les quatre langues ; elles ne diffèrent que par les captures d'écran de la documentation :

- 🪶 **Light** (la valeur par défaut recommandée) : **sans les captures d'écran de la documentation**, qui se chargent à la demande depuis le site de documentation en ligne. Environ 450 Mo à télécharger.
- 🗂️ **Full** : inclut également les captures d'écran de la documentation (bureau et mobile, dans les quatre langues, en thèmes clair et sombre), de sorte que la documentation intégrée fonctionne entièrement hors ligne. Un téléchargement plus important.

Chaque version est publiée avec ces tags :

| Tag | Variante | Utilisez-le pour |
|-----|---------|-----------|
| `latest` | 🪶 Light | Suivre la dernière version (le tag utilisé par le `docker-compose.yml` ci-dessus) |
| `X.Y.Z` (par ex. `1.1.0`) | 🗂️ Full | Épingler une version, avec la documentation entièrement hors ligne |
| `X.Y.Z-light` (par ex. `1.1.0-light`) | 🪶 Light | Épingler une version et rester sur la variante light |

- Les tags de version n'ont pas de `v` : `1.1.0`, pas `v1.1.0` comme sur la page des versions GitHub.
- Il n'y a pas de tag `latest-light` : `latest` est déjà la variante light.
- La variante full n'existe que sous un numéro de version. L'utiliser signifie épingler une version, et une image épinglée ne passe pas automatiquement à des versions plus récentes (voir [Mise à jour de LibreFolio](#updating)).

!!! warning "La variante light nécessite Internet pour les captures d'écran de la documentation"

    Avec la variante light (tag `latest` ou tout tag `-light`), la visualisation des captures d'écran dans la documentation intégrée (menu Aide) nécessite une **connexion Internet**, car elles sont récupérées depuis le site de documentation en ligne. Tout le reste — l'application complète et tout le texte de la documentation — est servi depuis l'image elle-même.

??? example "🗂️ Passer à la variante full"

    Ajoutez cette ligne à votre fichier `.env`, avec la version souhaitée :

    ```bash
    LIBREFOLIO_IMAGE=ghcr.io/librefolio/librefolio:1.1.0
    ```

    Ensuite, exécutez `docker compose up -d` : Docker télécharge cette image et redémarre LibreFolio avec cette image. Si votre `docker-compose.yml` a une ligne `image:` fixe, sans `LIBREFOLIO_IMAGE`, mettez le tag sur cette ligne à la place.

---

## ⚙️ Options de configuration

Tous les paramètres de LibreFolio, tels que le port et la clé de sécurité de session, se trouvent dans le fichier `.env` sous forme de variables d'environnement.

Pour chaque option et la façon dont sa valeur est résolue, consultez le [Guide de configuration dans le manuel d'administration](../admin/configuration.md).

---

## 💾 Sauvegarde des données {#data-backup}

Toutes vos données (la base de données SQLite, les fichiers téléchargés, les rapports de courtier et les logs) se trouvent dans le dossier `./LibreFolio-data` à côté de `docker-compose.yml`. Sauvegardez ce dossier, en arrêtant d'abord le conteneur pour une copie cohérente.

Pour savoir quoi sauvegarder et comment, consultez la [section Sauvegarde du manuel d'administration](../admin/filesystem.md#backup).

---

## 🔄 Mise à jour de LibreFolio {#updating}

Les migrations de base de données s'exécutent automatiquement au démarrage du conteneur et sont conçues pour conserver les données existantes, tandis que certaines fonctionnalités, comme la simulation de risque **What if…?**, sont [encore en bêta](../financial-theory/technical-analysis/risk-metrics/simulation-modes.md#why-beta) et peuvent changer entre les versions. Effectuez une [sauvegarde](#data-backup) avant de mettre à jour : c'est votre moyen de revenir en arrière en cas de problème.

- Avec le tag `latest`, vous obtenez toujours la dernière version, avec tous les changements qu'elle apporte.
- Pour ne mettre à jour que lorsque vous le décidez, épinglez une version au lieu de `latest` : `ghcr.io/librefolio/librefolio:1.1.0` (variante full) ou `ghcr.io/librefolio/librefolio:1.1.0-light` (variante light). Voir [Variantes d'image](#image-variants-full-and-light).

### 🛠️ 1. Mise à jour manuelle {: #manual-update }

Pour mettre à jour LibreFolio vers l'image la plus récente :

```bash
# 🛑 Arrêtez le conteneur en cours d'exécution
docker compose down

# 📥 Téléchargez la version la plus récente de l'image depuis le registre
docker compose pull

# 🚀 Redémarrez LibreFolio avec la nouvelle image
docker compose up -d
```

Les migrations de base de données s'exécutent d'elles-mêmes au démarrage du conteneur.

??? warning "🧯 LibreFolio ne redémarre pas après une mise à jour"

    Si une migration de base de données échoue, LibreFolio s'arrête et son log (`docker compose logs librefolio`) affiche `Failed to apply database migrations` avec l'erreur ; Docker continue alors de redémarrer le conteneur. Arrêtez-le avec `docker compose down`, restaurez votre [sauvegarde](#data-backup) de `LibreFolio-data`, et épinglez la version que vous utilisiez jusqu'à ce que le problème soit résolu.

### 🤖 2. Mise à jour automatique (Watchtower)

**Watchtower** met à jour les conteneurs dès qu'une nouvelle image est publiée. Nous recommandons son fork actif et mis à jour, [nicholas-fedor/watchtower](https://github.com/nicholas-fedor/watchtower). Par défaut, il surveille **tous** les conteneurs en cours d'exécution sur le système : cette commande le limite à LibreFolio et vérifie une fois par semaine, le dimanche à 04:00 :

```bash
docker run -d \
  --name watchtower \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e TZ=Europe/Rome \
  nickfedor/watchtower \
  --cleanup \
  --schedule "0 0 4 * * 0" \
  librefolio
```

- `--schedule` prend une expression cron avec six champs, les secondes en premier ; réglez `TZ` sur votre fuseau horaire.
- `--cleanup` supprime les anciennes images pour économiser de l'espace.
- Pour toutes les autres options, consultez le [dépôt du projet](https://github.com/nicholas-fedor/watchtower).

### 🔌 3. Autres alternatives de gestion

Pour plus de contrôle sur les notifications et sur le moment de la mise à jour :

- **[WUD (What's Up Docker)](https://github.com/getwud/wud)** : un outil homelab avec une **interface web** pratique et des notifications via Telegram, Discord, Gotify et plus encore. Il peut vous alerter des nouvelles versions sans les mettre à jour, vous laissant le choix du moment.
- **[Diun (Docker Image Update Notifier)](https://github.com/crazy-max/diun)** : un notificateur léger qui n'a pas besoin d'un accès en écriture au socket Docker. Il surveille les registres d'images en lecture seule et vous informe lorsqu'une nouvelle version de LibreFolio est publiée.
