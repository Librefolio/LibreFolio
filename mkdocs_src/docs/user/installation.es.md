# 🐳 Instalación con Docker (Usuario)

Esta guía instala LibreFolio con la imagen Docker oficial precompilada: la forma más sencilla y recomendada de ejecutarlo en casa.

Solo necesitas Docker: nada de Python, Node.js o Pipenv, y nada que compilar.

---

## ✅ Requisitos previos

Instala **Docker**, que incluye Docker Compose, en el equipo que ejecutará LibreFolio:

=== "Linux"

    Sigue la guía oficial de Docker para tu distribución: [Instalar Docker Engine](https://docs.docker.com/engine/install/). En Debian y Ubuntu, la guía primero añade el repositorio de paquetes de Docker, luego instala:

    ```bash
    sudo apt-get update
    sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    ```

    !!! warning "Permisos del grupo Docker (Linux)"

        En Linux, tu usuario del sistema debe pertenecer al grupo `docker` para ejecutar comandos sin `sudo`:

        ```bash
        sudo usermod -aG docker $USER
        ```

        Luego **cierra sesión y vuelve a iniciarla** (o ejecuta `newgrp docker`) para aplicar los cambios a tu sesión de terminal actual.

=== "macOS"

    Instala **Docker Desktop**:

    - [Descargar Docker Desktop para Mac](https://docs.docker.com/desktop/install/mac-install/) (Apple Silicon o Intel).
    - O, con Homebrew:

      ```bash
      brew install --cask docker-desktop
      ```

=== "Windows"

    Instala **Docker Desktop**:

    - Descarga e instala [Docker Desktop para Windows](https://docs.docker.com/desktop/install/windows-install/).
    - Habilita el backend **WSL 2** durante la instalación para obtener el mejor rendimiento.

---

## 🚀 Instalación paso a paso

### 📁 1. Crear una carpeta de proyecto

Abre una terminal, ve a la carpeta donde quieras mantener LibreFolio (por ejemplo, tu carpeta Documentos), luego crea una carpeta `librefolio` y entra en ella:

```bash
# 🏠 Ve a la carpeta principal donde quieras colocar el proyecto (p. ej. Documentos)
cd /path/to/your/folder

# 📁 Crea y entra en la carpeta LibreFolio
mkdir librefolio
cd librefolio
```

### 📥 2. Obtener los archivos de configuración base

LibreFolio necesita dos archivos: `docker-compose.yml`, que describe el contenedor, y `.env`, que contiene tu configuración. Descarga ambos desde el repositorio oficial con uno de estos comandos:

=== "wget"

    ```bash
    # 📥 Descarga el archivo docker-compose.yml oficial
    wget https://raw.githubusercontent.com/Librefolio/LibreFolio/main/docker-compose.prod.yml -O docker-compose.yml

    # 🔑 Descarga el archivo .env.example y guárdalo como .env
    wget https://raw.githubusercontent.com/Librefolio/LibreFolio/main/.env.example -O .env
    ```

=== "curl"

    ```bash
    # 📥 Descarga el archivo docker-compose.yml oficial
    curl -L https://raw.githubusercontent.com/Librefolio/LibreFolio/main/docker-compose.prod.yml -o docker-compose.yml

    # 🔑 Descarga el archivo .env.example y guárdalo como .env
    curl -L https://raw.githubusercontent.com/Librefolio/LibreFolio/main/.env.example -o .env
    ```

El stack ejecuta la imagen oficial desde el GitHub Container Registry (GHCR) y guarda todos tus datos en una carpeta `LibreFolio-data` junto a `docker-compose.yml`.

??? example "✍️ ¿Prefieres escribir `docker-compose.yml` a mano?"

    Crea un archivo llamado `docker-compose.yml` y pega este contenido, el mismo servicio que el archivo oficial:

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

    La línea `env_file: .env` necesita un archivo `.env` en la misma carpeta: descárgalo como se muestra arriba, o crea uno vacío; de lo contrario, Docker se detiene con un error.

### ▶️ 3. Iniciar la aplicación

Inicia LibreFolio en segundo plano:

```bash
docker compose up -d
```

Docker descarga la imagen oficial desde GHCR e inicia LibreFolio. La etiqueta `latest` es la [variante ligera](#image-variants-full-and-light) de la imagen, la predeterminada recomendada.

### 🌐 4. Acceder a LibreFolio

Abre tu navegador en **`http://localhost:6040`**.

En tu primera visita, LibreFolio muestra la página de registro: la primera cuenta que crees se convierte automáticamente en **administrador**.

??? tip "🖥️ Ver el estado y los registros (opcional)"

    Desde la terminal, `docker compose logs -f` sigue los registros de LibreFolio (`Ctrl+C` deja de seguirlos). Para una vista gráfica de tus contenedores y sus registros en tiempo real, prueba **[Portainer](https://github.com/portainer/portainer)**, una herramienta de gestión de Docker ligera y ampliamente utilizada.

### 📶 5. Acceso a la red local y remota

Una vez iniciado, se puede acceder a LibreFolio:

- 💻 desde el **equipo anfitrión**, en `http://localhost:6040`;
- 📱 desde **otros dispositivos en la misma red local** (smartphones, tablets, otros PC), en la dirección IP local del equipo anfitrión, por ejemplo `http://192.168.1.100:6040`.

??? note "🛡️ Cortafuegos — solo si otros dispositivos no pueden conectarse"

    Abre el puerto `6040` en el cortafuegos del equipo anfitrión:

    === "Debian / Ubuntu (UFW)"

        ```bash
        sudo ufw allow 6040/tcp
        ```

    === "RHEL / Rocky Linux / Fedora (Firewalld)"

        ```bash
        sudo firewall-cmd --add-port=6040/tcp --permanent
        sudo firewall-cmd --reload
        ```

🌍 **Fuera de casa**, usa la solución que prefieras, como un proxy inverso con certificado SSL. Para la configuración más simple y segura, sin abrir puertos en tu router, **recomendamos Tailscale**: consulta [Exposición con Tailscale](../admin/service_exposure.md).

---

## 🏷️ Variantes de imagen: Completa y Ligera {: #image-variants-full-and-light }

La imagen oficial viene en dos variantes. Ambas contienen toda la aplicación y todas las páginas de texto de la documentación, en los cuatro idiomas; solo se diferencian en las capturas de pantalla de la documentación:

- 🪶 **Ligera** (la predeterminada recomendada): **sin las capturas de pantalla de la documentación**, que se cargan bajo demanda desde el sitio de documentación en línea. Aproximadamente 450 MB de descarga.
- 🗂️ **Completa**: también incluye las capturas de pantalla de la documentación (escritorio y móvil, en los cuatro idiomas, en temas claro y oscuro), por lo que la documentación integrada funciona completamente sin conexión. Una descarga más grande.

Cada versión se publica con estas etiquetas:

| Etiqueta | Variante | Úsala para |
|-----|---------|-----------|
| `latest` | 🪶 Ligera | Seguir la versión más reciente (la etiqueta que usa el `docker-compose.yml` de arriba) |
| `X.Y.Z` (p. ej. `1.1.0`) | 🗂️ Completa | Fijar una versión, con la documentación completamente sin conexión |
| `X.Y.Z-light` (p. ej. `1.1.0-light`) | 🪶 Ligera | Fijar una versión y permanecer en la variante ligera |

- Las etiquetas de versión no tienen `v`: `1.1.0`, no `v1.1.0` como en la página de versiones de GitHub.
- No hay etiqueta `latest-light`: `latest` ya es la variante ligera.
- La variante completa existe solo bajo un número de versión. Usarla significa fijar una versión, y una imagen fijada no se actualiza a versiones más recientes por sí sola (consulta [Actualizar LibreFolio](#updating)).

!!! warning "La variante ligera necesita internet para las capturas de pantalla de la documentación"

    Con la variante ligera (etiqueta `latest` o cualquier `-light`), ver las capturas de pantalla dentro de la documentación integrada (menú Ayuda) requiere una **conexión a internet**, porque se obtienen del sitio de documentación en línea. Todo lo demás —toda la aplicación y todo el texto de la documentación— se sirve desde la propia imagen.

??? example "🗂️ Cambiar a la variante completa"

    Añade esta línea a tu archivo `.env`, con la versión que quieras:

    ```bash
    LIBREFOLIO_IMAGE=ghcr.io/librefolio/librefolio:1.1.0
    ```

    Luego ejecuta `docker compose up -d`: Docker descarga esa imagen y reinicia LibreFolio con ella. Si tu `docker-compose.yml` tiene una línea `image:` fija, sin `LIBREFOLIO_IMAGE`, pon la etiqueta en esa línea en su lugar.

---

## ⚙️ Opciones de configuración

Toda la configuración de LibreFolio, como el puerto y la clave de seguridad de la sesión, reside en el archivo `.env` como variables de entorno.

Para cada opción y cómo se resuelve su valor, consulta la [Guía de configuración en el Manual de administración](../admin/configuration.md).

---

## 💾 Copia de seguridad de datos {#data-backup}

Todos tus datos (la base de datos SQLite, los archivos subidos, los informes de brókeres y los registros) viven en la carpeta `./LibreFolio-data` junto a `docker-compose.yml`. Haz una copia de seguridad de esa carpeta, deteniendo primero el contenedor para obtener una copia consistente.

Para saber qué guardar y cómo, consulta la [sección de Copia de seguridad del Manual de administración](../admin/filesystem.md#backup).

---

## 🔄 Actualizar LibreFolio {#updating}

Las migraciones de la base de datos se ejecutan automáticamente cuando se inicia el contenedor y están diseñadas para conservar los datos existentes, mientras que algunas funciones, como la simulación de riesgo **What if…?**, están [aún en beta](../financial-theory/technical-analysis/risk-metrics/simulation-modes.md#why-beta) y pueden cambiar entre versiones. Haz una [copia de seguridad](#data-backup) antes de actualizar: es tu forma de volver atrás si algo sale mal.

- Con la etiqueta `latest` siempre obtienes la versión más reciente, junto con cualquier cambio que traiga.
- Para actualizar solo cuando tú decidas, fija una versión en lugar de `latest`: `ghcr.io/librefolio/librefolio:1.1.0` (variante completa) o `ghcr.io/librefolio/librefolio:1.1.0-light` (variante ligera). Consulta [Variantes de imagen](#image-variants-full-and-light).

### 🛠️ 1. Actualización manual {: #manual-update }

Para actualizar LibreFolio a la imagen más reciente:

```bash
# 🛑 Detén el contenedor en ejecución
docker compose down

# 📥 Descarga la versión más reciente de la imagen desde el registro
docker compose pull

# 🚀 Reinicia LibreFolio usando la nueva imagen
docker compose up -d
```

Las migraciones de la base de datos se ejecutan solas cuando se inicia el contenedor.

??? warning "🧯 LibreFolio no vuelve después de una actualización"

    Si falla una migración de la base de datos, LibreFolio se detiene y su registro (`docker compose logs librefolio`) muestra `Failed to apply database migrations` con el error; entonces Docker sigue reiniciando el contenedor. Detenlo con `docker compose down`, restaura tu [copia de seguridad](#data-backup) de `LibreFolio-data`, y fija la versión que estabas usando hasta que se resuelva el problema.

### 🤖 2. Actualización automática (Watchtower)

**Watchtower** actualiza los contenedores tan pronto como se publica una nueva imagen. Recomendamos su fork activo y actualizado, [nicholas-fedor/watchtower](https://github.com/nicholas-fedor/watchtower). Por defecto vigila **todos** los contenedores en ejecución del sistema: este comando lo limita a LibreFolio y comprueba una vez a la semana, los domingos a las 04:00:

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

- `--schedule` acepta una expresión cron con seis campos, siendo los segundos el primero; configura `TZ` con tu zona horaria.
- `--cleanup` elimina las imágenes antiguas para ahorrar espacio.
- Para cualquier otra opción, consulta el [repositorio del proyecto](https://github.com/nicholas-fedor/watchtower).

### 🔌 3. Otras alternativas de gestión

Para tener más control sobre las notificaciones y sobre cuándo actualizar:

- **[WUD (What's Up Docker)](https://github.com/getwud/wud)**: una herramienta de homelab con una cómoda **interfaz web** y notificaciones vía Telegram, Discord, Gotify y más. Puede alertarte sobre nuevas versiones sin actualizar, dejándote a ti la elección de cuándo hacerlo.
- **[Diun (Docker Image Update Notifier)](https://github.com/crazy-max/diun)**: un notificador ligero que no necesita acceso de escritura al socket de Docker. Vigila los registros de imágenes en modo solo lectura y te avisa cuando se publica una nueva versión de LibreFolio.
