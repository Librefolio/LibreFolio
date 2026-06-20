# 📝 Configuración

LibreFolio utiliza un archivo `.env` para la configuración, impulsado por `BaseSettings` de Pydantic. Esto permite una gestión sencilla de las variables de entorno tanto para el desarrollo local como para los despliegues con Docker.

## 📄 Archivo `.env`

El archivo `.env` se encuentra en la raíz del proyecto. Se proporciona un archivo de ejemplo, `.env.example`. Para comenzar, simplemente cópielo:

```bash
cp .env.example .env
```

### 🔑 Variables de Entorno Clave

- **`PORT`**: El puerto en el que se ejecutará el servidor FastAPI.
 - Valor predeterminado: `6040`

- **`TEST_PORT`**: El puerto en el que se ejecutará el servidor de pruebas cuando el modo de prueba esté habilitado.
 - Valor predeterminado: `6041`

- **`LIBREFOLIO_DATA_DIR`**: La ruta del directorio donde se almacenan los datos de producción (base de datos SQLite, registros, archivos subidos).
 - Valor predeterminado: `./backend/data/prod`

- **`JWT_SECRET`**: La clave secreta utilizada para firmar los JWT (JSON Web Tokens) de las sesiones de usuario.
 - **Importante**: Esta clave debe establecerse con un valor estable si desea evitar que los clientes pierdan sus sesiones al reiniciar el servidor (o si utiliza múltiples workers de uvicorn). Sin embargo, para obtener la máxima seguridad, la opción recomendada es dejarla vacía y permitir que se recalcule dinámicamente en tiempo de ejecución.

- **`LOG_LEVEL`**: El nivel de registro (logging) para la aplicación.
 - Opciones: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
 - Valor predeterminado: `INFO`

- **`PORTFOLIO_BASE_CURRENCY`**: La moneda base predeterminada para los cálculos de la cartera.
 - Valor predeterminado: `EUR`

- **`PREVIEW_CACHE_MAX_MB`**: Tamaño máximo (en MB) para la caché de previsualización de imágenes en memoria.
 - Valor predeterminado: `50`
 - Las miniaturas almacenadas en caché se eliminan mediante LRU cuando se alcanza el límite.

- **`BACKEND_CORS_ORIGINS`**: Una lista JSON de orígenes CORS permitidos para desarrollo.
 - Valor predeterminado: `["http://localhost:3000", "http://localhost:5173"]`

- **`LIBREFOLIO_TEST_MODE`**: Una bandera para indicar si la aplicación se está ejecutando en modo de prueba (forzando el aislamiento mediante la base de datos de prueba).
 - Establezca `1` para habilitar el modo de prueba.

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
