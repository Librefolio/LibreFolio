# 🐳 Installation with Docker (User)

This guide explains how to install and run LibreFolio for regular use using the official pre-built Docker image. This is the simplest and recommended method for end users.

You do not need to install development tools or compile code on your host machine (no Python, Node.js, or Pipenv requirements).

---

## ✅ Prerequisites

Before starting, ensure you have **Docker** (which includes Docker Compose) installed on your host machine. Depending on your operating system, you can follow these steps:

=== "Linux"

    Most Linux distributions allow installation through their official repositories.
    
    For Debian/Ubuntu-based distributions:
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

    On macOS, the recommended way is to install **Docker Desktop**:
    
    - [Download Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/) (available for Apple Silicon or Intel).
    - Alternatively, if you use Homebrew, you can install it via terminal:
      ```bash
      brew install --cask docker
      ```

=== "Windows"

    On Windows, install **Docker Desktop**:
    
    - Download and install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/).
    - Make sure to enable the **WSL 2** backend during installation for the best performance.

---

## 🚀 Step-by-Step Installation

### 📁 1. Create a project folder

📂 Navigate to the folder where you want to save the project (for example, your user folder or documents), create a new directory for LibreFolio, and enter it:

```bash
# 🏠 Go to the main folder where you want to place the project (e.g. Documents)
cd /path/to/your/folder

# 📁 Create and enter the LibreFolio folder
mkdir librefolio
cd librefolio
```

### 📥 2. Get the base configuration files

⚙️ To start LibreFolio, you will need the `docker-compose.yml` file (which describes the container stack) and the `.env` file (which contains your custom environment settings).

⬇️ You can download them directly from the official GitHub repository using one of the following commands:

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

✍️ Alternatively, you can manually create a file named `docker-compose.yml` and paste the following code inside:

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

💡 *(If you did not download the `.env.example` file, remove the `env_file: .env` line from the code above, or create an empty `.env` file, to prevent startup errors).*

### ▶️ 3. Start the application

🚀 Start the container in the background (detached mode) by running:

```bash
docker compose up -d
```

📦 Docker will download the official image from the GitHub Container Registry (GHCR) and start LibreFolio.

### 🌐 4. Access LibreFolio

🖥️ Once the container has started, open your browser and go to:

**`http://localhost:6040`**

👤 On first access, you will be presented with the registration page to create the LibreFolio administrator account. The first user to register will automatically receive administrator privileges.

!!! tip "Monitoring Status and Logs with Portainer"

    If you prefer a convenient graphical interface to monitor the status of your LibreFolio container and view its logs in real time, we recommend using **[Portainer](https://github.com/portainer/portainer)**, a lightweight and widely used Docker management tool.

### 📶 5. Local and Remote Network Access

Once started, LibreFolio will be reachable:

- 💻 Directly from the **host computer** by visiting `http://localhost:6040`.
- 📱 From **other devices on the same local network (LAN)** (e.g. smartphones, tablets, other PCs) by entering the host computer's local IP address in the browser (e.g. `http://192.168.1.100:6040`).

#### 🛡️ Firewall Configuration (optional)
If you cannot access LibreFolio from other devices on the local network, you may need to open port `6040` in the host computer's firewall:

=== "Debian / Ubuntu (UFW)"

    ```bash
    sudo ufw allow 6040/tcp
    ```

=== "RHEL / Rocky Linux / Fedora (Firewalld)"

    ```bash
    sudo firewall-cmd --add-port=6040/tcp --permanent
    sudo firewall-cmd --reload
    ```

#### 🌐 Remote Access
To access LibreFolio securely when you are away from home (outside the local network), you are free to configure your preferred solution (such as a reverse proxy with an SSL certificate).

However, for maximum simplicity and security without opening ports on your router, **we recommend using Tailscale**. You can find all the details and a step-by-step guide on the [Exposure with Tailscale](../admin/service_exposure.md) page.

---

## ⚙️ Configuration Options

All LibreFolio settings (such as ports, base currency, and session security keys) are managed via environment variables in the `.env` file.

For full details on each option and how variables are resolved, see the [Configuration Guide in the Admin Manual](../admin/configuration.md).

---

## 💾 Data Backup

All LibreFolio data (SQLite database, user-uploaded files, loaded reports, and logs) are saved locally inside the `./librefolio-data` folder created alongside the `docker-compose.yml` file.

For detailed instructions on what to save and how to perform consistent backups, see the [Backup Section of the Admin Manual](../admin/filesystem.md#backup).

---

## 🔄 Updating LibreFolio

### ⚠️ Warning: Alpha Status
LibreFolio is currently in **Alpha** development. This means that between versions there could be structural changes or database migrations that might prevent the new version from starting, requiring manual intervention or restoring a previous version.

- By using the `:latest` tag in the `docker-compose.yml` file, you will immediately receive the latest features but expose yourself to potential incompatibilities during automatic updates.
- If you prefer stability and absolute control, we recommend pinning the image by replacing `:latest` with a specific version tag (for example, `ghcr.io/librefolio/librefolio:v0.10.0`).

### 🛠️ 1. Manual Update

To update LibreFolio manually to the latest available version:

```bash
# 🛑 Stop the running container
docker compose down

# 📥 Download the newest version of the image from the registry
docker compose pull

# 🚀 Restart LibreFolio using the new image
docker compose up -d
```

Database migrations will be executed automatically when the container starts.

### 🤖 2. Automatic Update (Watchtower)

If you want to automate container updates as soon as a new image is released on the registry, you can use **Watchtower** (we recommend the active and updated fork [nicholas-fedor/watchtower](https://github.com/nicholas-fedor/watchtower)).

!!! note "Default behavior"

    By default, Watchtower monitors and updates all active containers on the system. For more details and advanced options, see the [official project repository](https://github.com/nicholas-fedor/watchtower).

For convenience, if you want to limit software checks only to LibreFolio and run the verification weekly (for example, every Sunday at 4:00 AM using a Cron expression), you can start Watchtower with this command:

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
💡 *(This command starts Watchtower in the background with access to the Docker socket. It will check for new images on the registry only for the `librefolio` container every Sunday at 04:00:00, deleting old images to save space. Adjust `TZ` to set your reference timezone).*

### 🔌 3. Other Management Alternatives

If you want a different approach or more control over notifications and release deployment, there are excellent alternatives:

- **[WUD (What's Up Docker)](https://github.com/fmartinou/whats-up-docker)**  
  A modern tool for homelabs featuring a convenient **web interface**.  
  It is highly modular and supports notifications via Telegram, Discord, and Gotify.  
  It allows sending alerts about new releases without automatically updating, leaving the choice of when to do so to you.  
  
- **[Diun (Docker Image Update Notifier)](https://github.com/crazy-max/diun)**  
  A pure, lightweight, and secure notifier.  
  It does not require write permissions on the Docker socket.  
  It monitors image registries in read-only mode and notifies you when a new version of LibreFolio is published.
