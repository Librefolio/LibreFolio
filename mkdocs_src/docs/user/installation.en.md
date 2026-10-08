# 🐳 Installation with Docker (User)

This guide installs LibreFolio with the official pre-built Docker image: the simplest and recommended way to run it at home.

You only need Docker: no Python, Node.js or Pipenv, and nothing to compile.

---

## ✅ Prerequisites

Install **Docker**, which includes Docker Compose, on the computer that will run LibreFolio:

=== "Linux"

    Follow Docker's official guide for your distribution: [Install Docker Engine](https://docs.docker.com/engine/install/). On Debian and Ubuntu, the guide first adds Docker's package repository, then installs:

    ```bash
    sudo apt-get update
    sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    ```

    !!! warning "Docker group permissions (Linux)"

        On Linux, your system user must belong to the `docker` group to run commands without `sudo`:

        ```bash
        sudo usermod -aG docker $USER
        ```

        Then **log out and log back in** (or run `newgrp docker`) to apply the changes to your current terminal session.

=== "macOS"

    Install **Docker Desktop**:

    - [Download Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/) (Apple Silicon or Intel).
    - Or, with Homebrew:

      ```bash
      brew install --cask docker-desktop
      ```

=== "Windows"

    Install **Docker Desktop**:

    - Download and install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/).
    - Enable the **WSL 2** backend during installation for the best performance.

---

## 🚀 Step-by-Step Installation

### 📁 1. Create a project folder

Open a terminal, go to the folder where you want to keep LibreFolio (for example your Documents folder), then create a `librefolio` folder and enter it:

```bash
# 🏠 Go to the main folder where you want to place the project (e.g. Documents)
cd /path/to/your/folder

# 📁 Create and enter the LibreFolio folder
mkdir librefolio
cd librefolio
```

### 📥 2. Get the base configuration files

LibreFolio needs two files: `docker-compose.yml`, which describes the container, and `.env`, which holds your settings. Download both from the official repository with one of these commands:

=== "wget"

    ```bash
    # 📥 Download the official docker-compose.yml file
    wget https://raw.githubusercontent.com/Librefolio/LibreFolio/main/docker-compose.prod.yml -O docker-compose.yml

    # 🔑 Download the .env.example file and save it as .env
    wget https://raw.githubusercontent.com/Librefolio/LibreFolio/main/.env.example -O .env
    ```

=== "curl"

    ```bash
    # 📥 Download the official docker-compose.yml file
    curl -L https://raw.githubusercontent.com/Librefolio/LibreFolio/main/docker-compose.prod.yml -o docker-compose.yml

    # 🔑 Download the .env.example file and save it as .env
    curl -L https://raw.githubusercontent.com/Librefolio/LibreFolio/main/.env.example -o .env
    ```

The stack runs the official image from the GitHub Container Registry (GHCR) and keeps all your data in a `LibreFolio-data` folder next to `docker-compose.yml`.

??? example "✍️ Prefer to write `docker-compose.yml` by hand?"

    Create a file named `docker-compose.yml` and paste this content, the same service as the official file:

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

    The `env_file: .env` line needs a `.env` file in the same folder: download it as shown above, or create an empty one, otherwise Docker stops with an error.

### ▶️ 3. Start the application

Start LibreFolio in the background:

```bash
docker compose up -d
```

Docker downloads the official image from GHCR and starts LibreFolio. The `latest` tag is the [light variant](#image-variants-full-and-light) of the image, the recommended default.

### 🌐 4. Access LibreFolio

Open your browser at **`http://localhost:6040`**.

On your first visit, LibreFolio shows the registration page: the first account you create automatically becomes the **administrator**.

??? tip "🖥️ Watch the status and the logs (optional)"

    From the terminal, `docker compose logs -f` follows LibreFolio's logs (`Ctrl+C` stops following). For a graphical view of your containers and their logs in real time, try **[Portainer](https://github.com/portainer/portainer)**, a lightweight and widely used Docker management tool.

### 📶 5. Local and Remote Network Access

Once started, LibreFolio is reachable:

- 💻 from the **host computer**, at `http://localhost:6040`;
- 📱 from **other devices on the same local network** (smartphones, tablets, other PCs), at the host computer's local IP address, for example `http://192.168.1.100:6040`.

??? note "🛡️ Firewall — only if other devices cannot connect"

    Open port `6040` in the host computer's firewall:

    === "Debian / Ubuntu (UFW)"

        ```bash
        sudo ufw allow 6040/tcp
        ```

    === "RHEL / Rocky Linux / Fedora (Firewalld)"

        ```bash
        sudo firewall-cmd --add-port=6040/tcp --permanent
        sudo firewall-cmd --reload
        ```

🌍 **Away from home**, use the solution you prefer, such as a reverse proxy with an SSL certificate. For the simplest and safest setup, with no ports opened on your router, **we recommend Tailscale**: see [Exposure with Tailscale](../admin/service_exposure.md).

---

## 🏷️ Image Variants: Full and Light {: #image-variants-full-and-light }

The official image comes in two variants. Both contain the whole application and all documentation text pages, in all four languages; they differ only in the documentation screenshots:

- 🪶 **Light** (the recommended default): **without the documentation screenshots**, which load on demand from the online documentation site. About 450 MB to download.
- 🗂️ **Full**: also includes the documentation screenshots (desktop and mobile, in all four languages, in light and dark themes), so the built-in documentation works fully offline. A larger download.

Each release is published with these tags:

| Tag | Variant | Use it to |
|-----|---------|-----------|
| `latest` | 🪶 Light | Follow the newest release (the tag used by the `docker-compose.yml` above) |
| `X.Y.Z` (e.g. `1.1.0`) | 🗂️ Full | Pin a version, with the documentation fully offline |
| `X.Y.Z-light` (e.g. `1.1.0-light`) | 🪶 Light | Pin a version and stay on the light variant |

- Version tags have no `v`: `1.1.0`, not `v1.1.0` as on the GitHub releases page.
- There is no `latest-light` tag: `latest` already is the light variant.
- The full variant exists only under a version number. Using it means pinning a version, and a pinned image does not move to newer releases on its own (see [Updating LibreFolio](#updating)).

!!! warning "The light variant needs internet for documentation screenshots"

    With the light variant (`latest` or any `-light` tag), viewing the screenshots inside the built-in documentation (Help menu) requires an **internet connection**, because they are fetched from the online documentation site. Everything else — the whole application and all documentation text — is served from the image itself.

??? example "🗂️ Switch to the full variant"

    Add this line to your `.env` file, with the version you want:

    ```bash
    LIBREFOLIO_IMAGE=ghcr.io/librefolio/librefolio:1.1.0
    ```

    Then run `docker compose up -d`: Docker downloads that image and restarts LibreFolio on it. If your `docker-compose.yml` has a fixed `image:` line, without `LIBREFOLIO_IMAGE`, put the tag on that line instead.

---

## ⚙️ Configuration Options

All LibreFolio settings, such as the port and the session security key, live in the `.env` file as environment variables.

For every option and how its value is resolved, see the [Configuration Guide in the Admin Manual](../admin/configuration.md).

---

## 💾 Data Backup {#data-backup}

All your data (the SQLite database, uploaded files, broker reports and logs) lives in the `./LibreFolio-data` folder next to `docker-compose.yml`. Back up that folder, stopping the container first for a consistent copy.

For what to save and how, see the [Backup section of the Admin Manual](../admin/filesystem.md#backup).

---

## 🔄 Updating LibreFolio {#updating}

Database migrations run automatically when the container starts and are designed to keep existing data, while some features, such as the **What if…?** risk simulation, are [still in beta](../financial-theory/technical-analysis/risk-metrics/simulation-modes.md#why-beta) and can change between versions. Take a [backup](#data-backup) before updating: it is your way back if something goes wrong.

- With the `latest` tag you always get the newest release, along with any change it brings.
- To update only when you decide, pin a version instead of `latest`: `ghcr.io/librefolio/librefolio:1.1.0` (full variant) or `ghcr.io/librefolio/librefolio:1.1.0-light` (light variant). See [Image Variants](#image-variants-full-and-light).

### 🛠️ 1. Manual Update {: #manual-update }

To update LibreFolio to the newest image:

```bash
# 🛑 Stop the running container
docker compose down

# 📥 Download the newest version of the image from the registry
docker compose pull

# 🚀 Restart LibreFolio using the new image
docker compose up -d
```

The database migrations run on their own when the container starts.

??? warning "🧯 LibreFolio does not come back after an update"

    If a database migration fails, LibreFolio stops and its log (`docker compose logs librefolio`) shows `Failed to apply database migrations` with the error; Docker then keeps restarting the container. Stop it with `docker compose down`, restore your [backup](#data-backup) of `LibreFolio-data`, and pin the version you were using until the problem is solved.

### 🤖 2. Automatic Update (Watchtower)

**Watchtower** updates containers as soon as a new image is published. We recommend its active and updated fork, [nicholas-fedor/watchtower](https://github.com/nicholas-fedor/watchtower). By default it watches **every** running container on the system: this command limits it to LibreFolio and checks once a week, on Sunday at 04:00:

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

- `--schedule` takes a cron expression with six fields, seconds first; set `TZ` to your timezone.
- `--cleanup` deletes the old images to save space.
- For every other option, see the [project repository](https://github.com/nicholas-fedor/watchtower).

### 🔌 3. Other Management Alternatives

For more control over notifications and over when to update:

- **[WUD (What's Up Docker)](https://github.com/getwud/wud)**: a homelab tool with a convenient **web interface** and notifications via Telegram, Discord, Gotify and more. It can alert you about new releases without updating, leaving the choice of when to you.
- **[Diun (Docker Image Update Notifier)](https://github.com/crazy-max/diun)**: a lightweight notifier that needs no write access to the Docker socket. It watches the image registries read-only and tells you when a new version of LibreFolio is published.
