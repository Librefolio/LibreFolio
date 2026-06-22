# 🐳 Instalación con Docker (Usuario)

Esta guía explica cómo instalar y ejecutar LibreFolio para uso regular utilizando la imagen Docker oficial precompilada. Este es el método más sencillo y recomendado para los usuarios finales.

No es necesario instalar herramientas de desarrollo ni compilar el código en su máquina host (sin requisitos de Python, Node.js ni Pipenv).

---

## ✅ Requisitos previos

Antes de comenzar, asegúrese de tener instalado **Docker** (que incluye Docker Compose) en su máquina host. Según su sistema operativo, puede seguir estos pasos:

=== "Linux"

    La mayoría de las distribuciones Linux permiten la instalación a través de sus repositorios oficiales.
    
    Para distribuciones basadas en Debian/Ubuntu:
    ```bash
    sudo apt-get update
    sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    ```
    
    !!! warning "Permisos del grupo Docker (Linux)"
        En Linux, su usuario de sistema debe pertenecer al grupo `docker` para poder ejecutar comandos sin `sudo`:
        ```bash
        sudo usermod -aG docker $USER
        ```
        Luego, **cierre la sesión y vuelva a entrar** (o ejecute `newgrp docker`) para aplicar los cambios a la sesión de terminal actual.

=== "macOS"

    En macOS, el método recomendado es instalar **Docker Desktop**:
    
    - [Descargar Docker Desktop para Mac](https://docs.docker.com/desktop/install/mac-install/) (disponible para Apple Silicon o Intel).
    - Alternativamente, si utiliza Homebrew, puede instalarlo desde la terminal:
      ```bash
      brew install --cask docker
      ```

=== "Windows"

    En Windows, instale **Docker Desktop**:
    
    - Descargue e instale [Docker Desktop para Windows](https://docs.docker.com/desktop/install/windows-install/).
    - Asegúrese de habilitar el motor basado en **WSL 2** durante la instalación para obtener el mejor rendimiento.

---

## 🚀 Instalación paso a paso

### 📁 1. Crear una carpeta para el proyecto

📂 Navegue a la carpeta donde desea guardar el proyecto (por ejemplo, su carpeta de usuario o documentos), cree un nuevo directorio para LibreFolio y acceda a él:

```bash
# 🏠 Vaya a la carpeta principal donde desea colocar el proyecto (ej. Documentos)
cd /ruta/de/tu/carpeta

# 📁 Cree y acceda a la carpeta de LibreFolio
mkdir librefolio
cd librefolio
```

### 📥 2. Obtener los archivos de configuración base

⚙️ Para iniciar LibreFolio, necesitará el archivo `docker-compose.yml` (que describe la pila de contenedores) y el archivo `.env` (que contiene sus configuraciones de entorno personalizadas).

⬇️ Puede descargarlos directamente desde el repositorio oficial de GitHub utilizando uno de los siguientes comandos:

=== "wget"

    ```bash
    # 📥 Descargue el archivo docker-compose.yml oficial
    wget https://raw.githubusercontent.com/Librefolio/LibreFolio/main/docker-compose.prod.yml -O docker-compose.yml

    # 🔑 Descargue el archivo .env.example y guárdelo como .env
    wget https://raw.githubusercontent.com/Librefolio/LibreFolio/main/.env.example -O .env
    ```

=== "curl"

    ```bash
    # 📥 Descargue el archivo docker-compose.yml oficial
    curl -L https://raw.githubusercontent.com/Librefolio/LibreFolio/main/docker-compose.prod.yml -o docker-compose.yml

    # 🔑 Descargue el archivo .env.example y guárdelo como .env
    curl -L https://raw.githubusercontent.com/Librefolio/LibreFolio/main/.env.example -o .env
    ```

✍️ Alternativamente, puede crear manualmente un archivo llamado `docker-compose.yml` y pegar el siguiente código en su interior:

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

💡 *(Si no descargó el archivo `.env.example`, elimine la línea `env_file: .env` del código de arriba, o cree un archivo `.env` vacío, para evitar errores al iniciar).*

### ▶️ 3. Iniciar la aplicación

🚀 Inicie el contenedor en segundo plano (modo detached) ejecutando:

```bash
docker compose up -d
```

📦 Docker descargará la imagen oficial desde el registro de contenedores de GitHub (GHCR) e iniciará LibreFolio.

### 🌐 4. Acceder a LibreFolio

🖥️ Una vez iniciado el contenedor, abra su navegador y vaya a:

**`http://localhost:6040`**

👤 En el primer acceso, se le presentará la página de registro para crear la cuenta de administrador de LibreFolio. El primer usuario que se registre recibirá automáticamente privilegios de administrador.

!!! tip "Visualización del estado y registros con Portainer"

    Si prefiere una interfaz gráfica conveniente para monitorear el estado de su contenedor LibreFolio y leer sus registros en tiempo real, le recomendamos usar **[Portainer](https://github.com/portainer/portainer)**, una herramienta de gestión de Docker ligera y muy extendida.

### 📶 5. Acceso en red local y remoto

Una vez iniciado, LibreFolio estará accesible:

- 💻 Directamente desde la **computadora host** visitando `http://localhost:6040`.
- 📱 Desde **otros dispositivos en la misma red local (LAN)** (ej. teléfonos inteligentes, tabletas, otros PC) ingresando la dirección IP local de la computadora host en el navegador (ej. `http://192.168.1.100:6040`).

#### 🛡️ Configuración del Firewall (opcional)
Si no puede acceder a LibreFolio desde otros dispositivos de la red local, es posible que deba abrir el puerto `6040` en el firewall de la computadora host:

=== "Debian / Ubuntu (UFW)"

    ```bash
    sudo ufw allow 6040/tcp
    ```

=== "RHEL / Rocky Linux / Fedora (Firewalld)"

    ```bash
    sudo firewall-cmd --add-port=6040/tcp --permanent
    sudo firewall-cmd --reload
    ```

#### 🌐 Acceso remoto
Para acceder a LibreFolio de forma segura cuando está fuera de casa (fuera de la red local), es libre de configurar la solución que prefiera (como un proxy inverso con certificado SSL).

Sin embargo, para la máxima simplicidad y seguridad sin abrir puertos en su enrutador, **recomendamos usar Tailscale**. Puede encontrar todos los detalles y la guía paso a paso en la página [Exposición con Tailscale](../admin/tailscale_exposure.md).

---

## ⚙️ Opciones de configuración

Todos los ajustes de LibreFolio (como puertos, moneda base y claves de seguridad de la sesión) se gestionan mediante variables de entorno en el archivo `.env`.

Para obtener detalles completos sobre cada opción y cómo se resuelven las variables, consulte la [Guía de configuración en el Manual de Administración](../admin/configuration.md).

---

## 💾 Copias de seguridad de datos

Todos los datos de LibreFolio (base de datos SQLite, archivos subidos por los usuarios, informes cargados y registros) se guardan localmente dentro de la carpeta `./librefolio-data` creada junto al archivo `docker-compose.yml`.

Para obtener instrucciones detalladas sobre qué guardar y cómo realizar copias de seguridad consistentes, consulte la [Sección de Copias de Seguridad del Manual de Administración](../admin/filesystem.md#backup).

---

## 🔄 Actualizar LibreFolio

### ⚠️ Advertencia: Estado Alpha
LibreFolio se encuentra actualmente en desarrollo **Alpha**. Esto significa que entre versiones puede haber cambios estructurales o migraciones de base de datos que podrían impedir el inicio de la nueva versión, lo que requiere intervención manual o restaurar una versión anterior.

- Al usar la etiqueta `:latest` en el archivo `docker-compose.yml`, recibirá de inmediato las últimas funciones, pero se expondrá a posibles incompatibilidades durante las actualizaciones automáticas.
- Si prefiere estabilidad y un control absoluto, le recomendamos fijar la imagen reemplazando `:latest` con una etiqueta de versión específica (por ejemplo, `ghcr.io/librefolio/librefolio:v0.10.0`).

### 🛠️ 1. Actualización manual

Para actualizar LibreFolio manualmente a la última versión disponible:

```bash
# 🛑 Detenga el contenedor en ejecución
docker compose down

# 📥 Descargue la última versión de la imagen desde el registro
docker compose pull

# 🚀 Reinicie LibreFolio aplicando la nueva imagen
docker compose up -d
```

Las migraciones de la base de datos se ejecutarán automáticamente al iniciar el contenedor.

### 🤖 2. Actualización automática (Watchtower)

Si desea automatizar las actualizaciones del contenedor tan pronto como se publique una nueva imagen en el registro, puede usar **Watchtower** (le recomendamos la bifurcación activa y actualizada de [nicholas-fedor/watchtower](https://github.com/nicholas-fedor/watchtower)).

!!! note "Comportamiento por defecto"

    Por defecto, Watchtower monitorea y actualiza todos los contenedores activos en el sistema. Para obtener más detalles y opciones avanzadas, consulte el [repositorio oficial del proyecto](https://github.com/nicholas-fedor/watchtower).

Para mayor comodidad, si desea limitar las comprobaciones del software solo a LibreFolio y ejecutar la verificación semanalmente (por ejemplo, todos los domingos a las 4:00 AM utilizando una expresión Cron), puede iniciar Watchtower con este comando:

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
💡 *(Este comando inicia Watchtower en segundo plano con acceso al socket de Docker. Comprobará la presencia de nuevas imágenes en el registro solo para el contenedor `librefolio` todos los domingos a las 04:00:00, eliminando las imágenes antiguas para ahorrar espacio. Modifique `TZ` para establecer su zona horaria de referencia).*

### 🔌 3. Otras alternativas de gestión

Si desea un enfoque diferente o más control sobre las notificaciones y el despliegue de las versiones, existen excelentes alternativas:

- **[WUD (What's Up Docker)](https://github.com/fmartinou/whats-up-docker)**  
  Herramienta moderna para homelabs que cuenta con una práctica **interfaz web**.  
  Es muy modular y admite notificaciones a través de Telegram, Discord y Gotify.  
  Permite enviar alertas sobre nuevas versiones sin actualizar automáticamente, dejándole a usted la elección de cuándo hacerlo.  
  
- **[Diun (Docker Image Update Notifier)](https://github.com/crazy-max/diun)**  
  Un notificador puro, ligero y seguro.  
  No requiere permisos de escritura en el socket de Docker.  
  Monitorea los registros de imágenes en modo de solo lectura y le avisa cuando se publica una nueva versión de LibreFolio.
