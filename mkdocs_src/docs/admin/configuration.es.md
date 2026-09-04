# 📝 Configuración

LibreFolio utiliza un archivo `.env` para la configuración, impulsado por `BaseSettings` de Pydantic. Esto permite una gestión sencilla de las variables de entorno tanto para el desarrollo local como para implementaciones en Docker.

## 🔧 Inicio Rápido: Inicializar la Configuración

El archivo `.env` se encuentra en la raíz del proyecto. Se proporciona un archivo de ejemplo, `.env.example`. Para comenzar, simplemente cópielo:

```bash
cp .env.example .env
```

## ✏️ Opciones de Configuración (Archivo `.env`)

Estas variables le permiten personalizar el comportamiento de LibreFolio dentro del archivo `.env`. Son las mismas variables cargadas por defecto por Docker Compose.

| Variable | Predeterminado | Descripción |
| --- | --- | --- |
| `PORT` | `6040` | El puerto en el que se ejecutará el servidor FastAPI de producción. |
| `TEST_PORT` | `6041` | El puerto en el que se ejecutará el servidor de prueba cuando el modo de prueba esté activado. |
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | La ruta del directorio raíz donde se almacenan los datos persistentes (base de datos SQLite, cargas, registros, etc.). Resuelto a nivel de sistema: las rutas relativas se resuelven a absolutas respecto a la raíz del proyecto, mientras que en Docker se anula y se fuerza a `/app/backend/data/prod-docker` a través de mapeos de volumen de Compose. |
| `LOG_LEVEL` | `INFO` | El nivel de registro principal para la aplicación. Opciones: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `PORTFOLIO_BASE_CURRENCY` | `EUR` | La moneda base predeterminada para los cálculos de cartera (código ISO 4217). |
| `PREVIEW_CACHE_MAX_MB` | `50` | Tamaño máximo (en MB) para la caché de vista previa de imágenes en memoria. Las entradas expiran tras 1 hora (TTL); cuando se alcanza el límite, se expulsan primero las más antiguas. |

## 💻 Parámetros del Sistema (Variables de Entorno)

Estas variables manejan la integración de bajo nivel entre los módulos de la aplicación, el aislamiento de pruebas y los scripts CLI de desarrollo. Por lo general, el usuario no necesita modificarlas directamente, ya que el sistema (Docker Compose o el script `dev.py`) las asigna o gestiona automáticamente.

| Variable | Predeterminado | Descripción |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | La dirección de enlace de red para el servidor web FastAPI, inyectada automáticamente en Docker y comandos CLI. |
| `JWT_SECRET` | _auto-generated_ | La clave secreta utilizada para firmar y descifrar las sesiones de usuario (JSON Web Tokens). Esta variable **no** forma parte de la validación `Settings` de Pydantic y se lee en tiempo de ejecución directamente desde el entorno del sistema operativo. Si se deja vacía, la aplicación asigna automáticamente una clave aleatoria segura al iniciar (`secrets.token_urlsafe(64)`). Al iniciar el servidor localmente a través de `./dev.py server`, el script genera e inyecta automáticamente un secreto compartido para garantizar la persistencia de las sesiones. |
| `LIBREFOLIO_TEST_MODE` | — | Una bandera para indicar si la aplicación se está ejecutando en modo de prueba. Cuando se establece en `1` o `true`, fuerza a la aplicación a aislarse por completo redirigiendo el directorio de datos a `backend/data/test/`. Esto es gestionado automáticamente por los ejecutores de pruebas. |
| `LIBREFOLIO_LOG_LEVEL` | — | Anulación de alta prioridad para el nivel de registro. Si se establece, tiene precedencia absoluta y anula la propiedad `LOG_LEVEL` cargada por Pydantic en tiempo de ejecución (utilizado por `./dev.py server --debug`). |

## 🔎 Búsqueda de Activos — Buscador de Enlaces Web (Opcional)

Estas variables ajustan la **metabúsqueda externa de último recurso** utilizada *solo* durante la búsqueda interactiva de activos (Crear activo y asistente "crear activo" dentro de la importación del bróker) cuando la búsqueda interna de un proveedor devuelve cero resultados. **Nunca** se utilizan en la obtención automática de precios. El transporte es la biblioteca de metabúsqueda [`ddgs`](https://pypi.org/project/ddgs/). **Todas son opcionales y vienen con valores predeterminados seguros** — solo necesita tocarlas para ajustar, diagnosticar o desactivar la función. Consulte la guía para desarrolladores [Búsqueda de activos y buscador de enlaces](../developer/backend/assets/search_link_finder.md) para el diseño completo.

| Variable | Predeterminado | Descripción |
| --- | --- | --- |
| `LIBREFOLIO_WEB_LINK_FINDER_ENABLED` | `1` | Interruptor maestro encendido/apagado. Establecer en `0` para desactivar por completo el recurso externo; la búsqueda interna del proveedor sigue funcionando. |
| `LIBREFOLIO_WEB_LINK_FINDER_ENGINE` | `ddgs` | Transporte de búsqueda. Opciones: `ddgs`, `apikey`. `ddgs` es el agregador de metabúsqueda sin configuración. `apikey` está reservado para un motor con clave (requiere `..._API_KEY`); `searxng` está reservado para una futura fase autoalojada. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_REGION` | `wt-wt` | Sugerencia de región `ddgs`. `wt-wt` (todo el mundo) evita un sesgo de EE. UU. para que las páginas localizadas (por ejemplo, Borsa Italiana) no bajen de rango. Ejemplos: `es-es`, `us-en`. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND` | `auto` | Qué motor(es) subyacente(s) consulta `ddgs`. `auto` rota a través de muchos motores por llamada (máxima cobertura, pero la **calidad de los resultados varía de una llamada a otra**). Fije un subconjunto separado por comas (por ejemplo, `google,bing,duckduckgo`) para obtener resultados **más deterministas** a costa de la cobertura. |
| `LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT` | `6` | Tiempo de espera por solicitud, en segundos. |
| `LIBREFOLIO_WEB_LINK_FINDER_MAX` | `5` | Número máximo de URL candidatas devueltas por búsqueda. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | _vacío_ | Clave API, utilizada solo cuando `ENGINE=apikey`. |

!!! tip "Resultados no deterministas con `auto`"

    Con el valor predeterminado `DDGS_BACKEND=auto`, la misma consulta puede devolver resultados de diferente calidad en llamadas consecutivas, porque `ddgs` rota los motores. Si una búsqueda interactiva ocasionalmente no devuelve nada para un instrumento que sabe que está indexado, vuelva a intentarlo una vez, o fije `DDGS_BACKEND` en un subconjunto estable como `google,bing,duckduckgo`.

## 🔝 Prioridad de Resolución

Al resolver las variables de configuración, LibreFolio respeta un orden de precedencia desde el más bajo (valores predeterminados en el código) hasta el más alto (anulaciones de Docker Compose). Para obtener un mapa de prioridades y un diagrama detallados, consulte la [Sección de Prioridad de Resolución de Docker](docker_advanced.md#resolution-priority).

## 📂 Separación de Datos

LibreFolio utiliza directorios de datos separados para producción y prueba:

- **Producción**: `backend/data/prod/` (sqlite, custom-uploads, broker_reports, logs)
- **Test**: `backend/data/test/` (misma estructura, completamente aislado)

La función `get_data_dir()` en `config.py` selecciona automáticamente la ruta correcta basándose en `LIBREFOLIO_TEST_MODE`.

## ⚙️ Cómo Funciona

La configuración se carga en una clase Pydantic `Settings` ubicada en `backend/app/config.py`. Esta clase lee automáticamente las variables del archivo `.env` y valida sus tipos.

Este enfoque proporciona:

- **Seguridad de Tipos**: La configuración se valida al iniciar la aplicación.
- **Configuración Centralizada**: Toda la configuración se define en un solo lugar.
- **Flexibilidad**: La configuración se puede proporcionar a través de un archivo `.env` o como variables de entorno reales, lo que facilita su configuración en diferentes entornos (local, Docker, etc.).
