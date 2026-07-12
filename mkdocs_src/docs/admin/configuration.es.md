# 📝 Configuración

LibreFolio utiliza un archivo `.env` para la configuración, impulsado por `BaseSettings` de Pydantic. Esto permite una gestión sencilla de las variables de entorno tanto para el desarrollo local como para los despliegues con Docker.

## 🔧 Guía Rápida: Inicializar la Configuración

El archivo `.env` se encuentra en la raíz del proyecto. Se proporciona un archivo de ejemplo, `.env.example`. Para comenzar, simplemente cópielo:

```bash
cp .env.example .env
```

## ✏️ Opciones de Configuración (Archivo `.env`)

Estas variables permiten personalizar el comportamiento de LibreFolio dentro del archivo `.env`. Son las mismas variables cargadas por defecto por Docker Compose.

- **`PORT`** (Valor predeterminado: `6040`): El puerto en el que se ejecutará el servidor FastAPI en producción.
- **`TEST_PORT`** (Valor predeterminado: `6041`): El puerto en el que se ejecutará el servidor de pruebas cuando el modo de prueba esté habilitado.
- **`LIBREFOLIO_DATA_DIR`** (Valor predeterminado: `./backend/data/prod`): La ruta del directorio raíz donde se almacenan los datos persistentes (base de datos SQLite, archivos subidos, registros, etc.). Se procesa a nivel de sistema: las rutas relativas se resuelven a rutas absolutas en relación con la raíz del proyecto, mientras que en Docker se anula y se fuerza a `/app/backend/data/prod-docker` mediante las asignaciones de volumen de Compose.
- **`LOG_LEVEL`** (Valor predeterminado: `INFO`, Opciones: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`): El nivel de registro (logging) principal para la aplicación.
- **`PORTFOLIO_BASE_CURRENCY`** (Valor predeterminado: `EUR`): La moneda base predeterminada para los cálculos de la cartera (código ISO 4217).
- **`PREVIEW_CACHE_MAX_MB`** (Valor predeterminado: `50`): Tamaño máximo (en MB) para la caché de previsualización de imágenes en memoria. Las miniaturas almacenadas en caché se eliminan mediante el algoritmo LRU cuando se alcanza el límite.

## 💻 Parámetros del Sistema (Variables de Entorno)

Estas variables gestionan la integración de bajo nivel entre los módulos de la aplicación, el aislamiento de las pruebas y los scripts de la CLI de desarrollo. Normalmente, el usuario no necesita modificarlas directamente, ya que el sistema (Docker Compose o el script `dev.py`) las asigna o las gestiona automáticamente.

- **`HOST`** (Valor predeterminado: `0.0.0.0`): La dirección de enlace de red (bind address) para el servidor web FastAPI, inyectado automáticamente en Docker y comandos de la CLI.
- **`JWT_SECRET`**: La clave secreta utilizada para firmar y descifrar las sesiones de usuario (JSON Web Tokens). Esta variable **no** forma parte de la variación de `Settings` de Pydantic y se lee en tiempo de ejecución directamente desde el entorno del sistema operativo. Si se deja vacía, la aplicación autoasigna una clave segura y aleatoria en cada inicio (`secrets.token_urlsafe(64)`). Al iniciar el servidor localmente a través de `./dev.py server`, el script genera e inyecta automáticamente un secreto compartido para garantizar la persistencia de las sesiones entre los workers.
- **`LIBREFOLIO_TEST_MODE`**: Una bandera para indicar si la aplicación se está ejecutando en modo de prueba. Cuando se establece en `1` o `true`, obliga a la aplicación a aislarse por completo redirigiendo el directorio de datos a `backend/data/test/`. Esto se gestiona automáticamente por los ejecutores de pruebas.
- **`LIBREFOLIO_LOG_LEVEL`**: Anulación de prioridad para el nivel de registro. Si se establece, tiene prioridad absoluta y reemplaza en tiempo de ejecución la propiedad `LOG_LEVEL` cargada por Pydantic (utilizada por `./dev.py server --debug`).

## 🔝 Prioridad de Resolución

Al resolver las variables de configuración, LibreFolio respeta un orden de precedencia desde el más bajo (valores predeterminados del código) hasta el más alto (anulaciones de Docker Compose). Para obtener un mapa y diagrama de prioridad detallados, consulte la [Sección de Prioridad de Resolución de Docker](docker_advanced.md#resolution-priority).

## 📂 Separación de Datos

LibreFolio utiliza directorios de datos separados para producción y test:

- **Producción**: `backend/data/prod/` (sqlite, custom-uploads, broker_reports, logs)
- **Test**: `backend/data/test/` (misma estructura, completamente aislado)

La función `get_data_dir()` en `config.py` selecciona automáticamente la ruta correcta basándose en `LIBREFOLIO_TEST_MODE`.

## ⚙️ Cómo Funciona

La configuración se carga en una clase `Settings` de Pydantic ubicada en `backend/app/config.py`. Esta clase lee automáticamente las variables del archivo `.env` y valida sus tipos.

Este enfoque proporciona:

- **Seguridad de Tipos**: La configuración se valida al iniciar la aplicación.
- **Configuración Centralizada**: Toda la configuración se define en un solo lugar.
- **Flexibilidad**: La configuración puede proporcionarse a través de un archivo `.env` o como variables de entorno reales, lo que facilita la configuración en diferentes entornos (local, Docker, etc.).
