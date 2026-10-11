# 📝 Configuración

Las opciones de inicio residen en un archivo `.env`: puertos, la carpeta de datos, registro, sesiones de inicio de sesión y algunas
funciones opcionales. Se encuentra en la raíz del proyecto, o junto a `docker-compose.yml` con
Docker. Las opciones que cambias desde dentro de la aplicación se encuentran en [Configuración global](settings.md).

---

## 🔧 Crear el archivo `.env`

En la carpeta del proyecto, copia el archivo de ejemplo y edita los valores que necesites:

```bash
cp .env.example .env
```

Con la imagen Docker precompilada, la guía de [instalación de Docker](../user/installation.md) descarga
el mismo ejemplo como `.env`.

- LibreFolio lee `.env` cuando se inicia: reinícialo después de un cambio. Con Docker Compose, ejecuta
  `docker compose up -d`, porque `docker compose restart` conserva los valores antiguos.
- Los nombres distinguen mayúsculas de minúsculas. En las opciones principales y la configuración de riesgo a continuación, un valor de
  tipo incorrecto o fuera de rango detiene el servidor al iniciarse con un error.

---

## ✏️ Opciones principales

| Variable | Predeterminado | Qué hace |
| --- | --- | --- |
| `PORT` | `6040` | Puerto del servidor web. Con Docker Compose, el puerto que se abre en el host (el contenedor siempre escucha en `6040`). |
| `TEST_PORT` | `6041` | Puerto del servidor de prueba (`./dev.py server --test`). |
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Carpeta de la base de datos, subidas, informes del bróker y registros; una ruta relativa parte de la carpeta del proyecto. Docker la fija en `/app/backend/data/prod-docker`: para mover los datos en el host, cambia el lado izquierdo del volumen `./LibreFolio-data` en `docker-compose.yml`. |
| `LOG_LEVEL` | `INFO` | Cuánto registra el servidor: `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR` o `CRITICAL`. |
| `JWT_SECRET` | _no establecido_ | Clave que firma las sesiones de inicio de sesión. No establecida: se genera una nueva clave en cada inicio, así que todos vuelven a iniciar sesión tras un reinicio. Consulta [Mantener a los usuarios conectados](index.md#session-persistence). |
| `SESSION_COOKIE_SECURE` | `auto` | Cuándo se envía la cookie de sesión de inicio de sesión solo por HTTPS: `auto` (si el navegador usa HTTPS), `always` o `never`. Consulta [HTTPS y proxies inversos](#session-cookie-secure). |
| `PREVIEW_CACHE_MAX_MB` | `50` | Memoria, en MB, de la caché de vistas previas de imágenes en cada proceso del servidor. |

Los archivos `.env` antiguos aún pueden contener `PORTFOLIO_BASE_CURRENCY`: LibreFolio lo ignora, y los nuevos
usuarios parten de la **Divisa predeterminada** en [Configuración global](settings.md).

??? info "🔒 HTTPS y proxies inversos — la cookie de sesión"

    `SESSION_COOKIE_SECURE` decide cuándo la cookie que mantiene a los usuarios conectados es `Secure`: el
    navegador entonces la envía solo por HTTPS, así que la sesión nunca viaja por una conexión sin cifrar. El uso de mayúsculas y minúsculas y los espacios alrededor del valor no importan; cualquier otro valor detiene el servidor al
    iniciarse con un error.
    {: #session-cookie-secure }

    - **`auto`** (predeterminado): `Secure` cuando el navegador llegó a LibreFolio por HTTPS. LibreFolio
      en sí sirve HTTP sin cifrar, así que HTTPS proviene de un proxy inverso delante de él, que lo indica
      con la cabecera `X-Forwarded-Proto: https`; solo cuenta su primer valor. No hay una lista de
      proxies de confianza que configurar: la cabecera solo puede activar `Secure`, nunca desactivarlo. Por HTTP sin cifrar,
      como `http://localhost:6040`, una IP de LAN o la IP de Tailscale de los niveles 1 y 2 en
      [Exponer de forma segura](service_exposure.md), la cookie no es `Secure`, así que iniciar sesión sigue
      funcionando.
    - **`always`**: siempre `Secure`, para una instalación a la que se accede solo por HTTPS. Por HTTP sin cifrar, el
      navegador descarta la cookie, así que el inicio de sesión no persiste: la siguiente página devuelve al usuario
      a la página de inicio de sesión.
    - **`never`**: nunca `Secure`. Es la salida cuando un proxy envía `X-Forwarded-Proto: https`
      a un navegador que en realidad usa HTTP sin cifrar, como Nginx con un
      `proxy_set_header X-Forwarded-Proto https;` codificado de forma fija en un bloque `server` de HTTP sin cifrar: en `auto`, ese
      navegador sería devuelto a la página de inicio de sesión tras cada inicio de sesión. Es mejor arreglar el proxy
      (`$scheme` en lugar de `https`); `never` es el fallback.

    Detrás de un proxy inverso HTTPS, `auto` se basa en su cabecera `X-Forwarded-Proto`:

    - **Tailscale Serve and Funnel** (niveles 3 y 4 en [Exponer de forma segura](service_exposure.md)),
      **Caddy** y **Traefik** la envían por su cuenta: nada que configurar.
    - **Nginx** no lo hace: añade `proxy_set_header X-Forwarded-Proto $scheme;` al `location` que
      hace de proxy para LibreFolio.
    - **Cualquier otro proxy**: haz que envíe la cabecera o, si solo se puede acceder a LibreFolio a través de él,
      establece `SESSION_COOKIE_SECURE=always`.

??? info "🧮 Trabajadores del motor de riesgo — ajuste avanzado"

    Las simulaciones de riesgo y las optimizaciones de cartera se ejecutan en procesos trabajadores separados, que se inician en
    el primer uso. Los valores predeterminados son adecuados para la mayoría de las instalaciones: añade una variable a `.env` solo para cambiarla.

    | Variable | Predeterminado | Qué hace |
    | --- | --- | --- |
    | `RISK_SIMULATION_WORKERS`, `RISK_OPTIMIZATION_WORKERS` | `1` (1–8) | Procesos trabajadores por tipo de trabajo: más procesos ejecutan más trabajos a la vez. |
    | `RISK_SIMULATION_QUEUE_CAPACITY`, `RISK_OPTIMIZATION_QUEUE_CAPACITY` | `2` (0–64) | Trabajos que pueden esperar a un trabajador; más allá de eso, las nuevas solicitudes se rechazan. |
    | `RISK_SIMULATION_TIMEOUT_SECONDS`, `RISK_OPTIMIZATION_TIMEOUT_SECONDS` | `120` / `60` | Límite de tiempo de un trabajo, en segundos. |
    | `RISK_SIMULATION_IDLE_TIMEOUT_SECONDS`, `RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS` | `600` | Los trabajadores inactivos se detienen tras esta cantidad de segundos y se reinician con el siguiente trabajo; `0` los mantiene en ejecución. |

---

## 💻 Parámetros establecidos por las herramientas

`./dev.py` y Docker Compose los establecen por ti: cámbialos solo si sabes por qué.

| Variable | Predeterminado | Qué hace |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Dirección en la que escucha `./dev.py server`; `127.0.0.1` acepta solo conexiones locales. Docker Compose siempre usa `0.0.0.0`. |
| `LIBREFOLIO_LOG_LEVEL` | — | Reemplaza a `LOG_LEVEL` cuando se establece; `./dev.py server --debug` lo establece en `DEBUG`. |
| `LIBREFOLIO_TEST_MODE` | — | `1`, `true` o `yes` cambia a la carpeta de datos de prueba. Lo establecen `./dev.py server --test` y los ejecutores de pruebas. |
| `LIBREFOLIO_TEST_DATA_DIR` | `./backend/data/test` | Carpeta de los datos de prueba; no puede solaparse con la de producción. |

---

## 🔎 Opcional: búsqueda web para nuevos activos

Cuando creas un activo, también desde el asistente de importación del bróker, y la búsqueda propia de un proveedor no encuentra
nada, LibreFolio puede encontrar la página del activo con una búsqueda web a través de la
biblioteca [`ddgs`](https://pypi.org/project/ddgs/). Está activada de forma predeterminada y nunca se usa para
actualizaciones de precios. Todas estas variables son opcionales: descomenta una línea de `.env.example` para cambiar una.

| Variable | Predeterminado | Qué hace |
| --- | --- | --- |
| `LIBREFOLIO_WEB_LINK_FINDER_ENABLED` | `1` | `0` desactiva la búsqueda web; la búsqueda propia de los proveedores sigue funcionando. |
| `LIBREFOLIO_WEB_LINK_FINDER_ENGINE` | `ddgs` | `ddgs` no necesita configuración. `apikey` está reservado para un servicio de búsqueda de pago y aún no devuelve resultados. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_REGION` | `wt-wt` | Región de búsqueda. `wt-wt` (mundial) evita que sitios nacionales como Borsa Italiana sean relegados. Ejemplos: `it-it`, `us-en`. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND` | `auto` | Motores que consulta `ddgs`: `auto` los rota para la mayor cobertura; una lista como `google,bing,duckduckgo` da resultados más estables. |
| `LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT` | `6` | Límite de tiempo de una búsqueda, en segundos. |
| `LIBREFOLIO_WEB_LINK_FINDER_MAX` | `5` | Máximo de enlaces devueltos por una búsqueda. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | _vacío_ | Clave para el motor `apikey`. |

??? tip "🔁 Los resultados cambian entre intentos — cuando un activo conocido a veces no se encuentra"

    Con `auto`, cada búsqueda puede llegar a motores diferentes, así que la misma consulta puede ir mejor o peor
    de un intento a otro. Reinténtalo una vez o establece
    `LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND=google,bing,duckduckgo`.

---

## 🔝 Qué valor prevalece

De mayor a menor prioridad:

1. Las opciones `--host`, `--port` y `--data-dir` de `./dev.py server`.
2. Variables establecidas en el shell.
3. El archivo `.env`.
4. Los valores predeterminados enumerados en esta página.

Con Docker Compose, el bloque `environment:` de `docker-compose.yml` prevalece sobre `.env`: fija
`HOST` y `LIBREFOLIO_DATA_DIR`. Consulta [Docker avanzado](docker_advanced.md#resolution-priority).

---

## 📂 Dónde van los datos

- **Producción**: `backend/data/prod/`, o `LIBREFOLIO_DATA_DIR`. Contiene la base de datos
  (`sqlite/app.db`), `custom-uploads/`, `broker_reports/` y `logs/`.
- **Prueba**: `backend/data/test/`, o `LIBREFOLIO_TEST_DATA_DIR`. Misma estructura, mantenida aparte.

[Estructura del sistema de archivos](filesystem.md) detalla cada carpeta y cómo hacer una copia de seguridad.

---

## 🔗 Relacionado

- ⚙️ **[Configuración global](settings.md)** — Opciones que se cambian desde dentro de la aplicación
- 🐳 **[Docker avanzado](docker_advanced.md)** — Archivo Compose, volúmenes, IDs de usuario y grupo
- 🧑‍💻 Para desarrolladores: **[Sistema de configuración](../developer/architecture/settings.md)** — Cómo se cargan estos
  valores
