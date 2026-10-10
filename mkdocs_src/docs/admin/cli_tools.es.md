# 🛠️ Herramientas de línea de comandos

`dev.py`, en la raíz del proyecto, ejecuta las tareas de administración: iniciar el servidor, gestionar usuarios y mantener la base de datos. Cada sección indica cuándo un comando necesita el servidor detenido.

!!! tip "Dónde ejecutar los comandos"

    - **Instalación en el host**: en el entorno de Pipenv, con el prefijo `pipenv run` usado en esta página, o después de `pipenv shell`.
    - **Docker**: en el contenedor en ejecución, con `docker compose exec librefolio python dev.py <command>` (desde una copia del código fuente, `./dev.py docker exec <command>`). Allí no se usa `pipenv run`: la imagen instala las dependencias de forma global. Los comandos de usuario, `db current` y `db check` funcionan allí; `db upgrade` y `db downgrade` no, ya que necesitan el servidor detenido ([Aplicar migraciones](#apply-migrations)). Los comandos de desarrollo como `test` no forman parte de la imagen ([detalles](docker_advanced.md#docker-exec)).

---

## 🖥️ Iniciar el servidor {: #start-the-server }

```bash
# Inicio estándar, un worker
pipenv run ./dev.py server

# Ajusta los workers a las CPUs (`auto` y `0` hacen lo mismo)
pipenv run ./dev.py server --workers auto

# O define el número de workers
pipenv run ./dev.py server --workers 4

# Escucha en otro puerto (por defecto: PORT de .env; si no, 6040)
pipenv run ./dev.py server --port 8080

# Mata lo que ya ocupe el puerto y luego inicia
pipenv run ./dev.py server --force
```

- 🧮 Más workers atienden más peticiones a la vez: úsalos en cualquier máquina con más de una CPU. `auto` inicia $\max(1,\ 2\,(n-1))$ workers en $n$ CPUs.
- ⏳ El servidor primero compila la interfaz web y esta documentación cuando faltan o están desactualizadas, por lo que el primer inicio tarda unos minutos. Si la interfaz no se compila, el servidor no se inicia.
- 🔑 Un reinicio cierra la sesión de todos, a menos que `JWT_SECRET` esté definido en `.env` (consulta [Configuración](configuration.md)).

??? note "⚙️ Otras opciones del servidor — rara vez necesarias"

    | Opción | Qué hace |
    | --- | --- |
    | `--host HOST` | Dirección en la que escuchar (por defecto: `HOST` del entorno o de `.env`; si no, `0.0.0.0`) |
    | `--data-dir PATH` | Usar otro directorio de datos para esta ejecución, en lugar de `LIBREFOLIO_DATA_DIR` |
    | `--no-scheduler` | Iniciar sin las sincronizaciones programadas de precios y FX |
    | `--rebuild`, `-r` | Recompilar la interfaz web incluso cuando parece estar actualizada |
    | `--debug`, `-d` | Registros `DEBUG` y una compilación de depuración de la interfaz web |

    Formas cortas: `-w` para `--workers`, `-p` para `--port`, `-f` para `--force`. `--test`, `--coverage` y `--no-reload` son opciones de desarrollo: `pipenv run ./dev.py server --help` las lista todas.

---

## 👤 Gestionar usuarios

Estos comandos escriben directamente en la base de datos, por lo que también funcionan mientras el servidor está en ejecución.

### ➕ Crear y listar usuarios

```bash
# Crea una cuenta de administrador
pipenv run ./dev.py user create <username> <email> <password>

# Lista todos los usuarios: ID, nombre de usuario, correo electrónico, activo, administrador
pipenv run ./dev.py user list
```

- 👑 Las cuentas creadas aquí son siempre **administradores**. Para una cuenta normal, deja que la persona se registre con **Regístrate aquí** en la página de inicio de sesión (cuando el registro esté abierto en la [Configuración global](settings.md)), o usa `demote` sobre la cuenta nueva.
- 🔒 La contraseña debe tener al menos 8 caracteres, con una letra mayúscula, una letra minúscula, un dígito y un símbolo.

### 🔑 Restablecer una contraseña o bloquear una cuenta {: #reset-a-password-or-lock-an-account }

```bash
# Establece una nueva contraseña (mismas reglas que arriba)
pipenv run ./dev.py user reset <username> <new_password>

# Bloquea una cuenta y luego vuelve a permitirle el acceso
pipenv run ./dev.py user deactivate <username>
pipenv run ./dev.py user activate <username>
```

- ⏱️ Un restablecimiento no finaliza las sesiones ya abiertas: siguen siendo válidas hasta que expiran. Para bloquear a alguien de inmediato, desactiva la cuenta: se rechazará la cuenta desde su siguiente petición.
- 💬 La pantalla **¿Olvidaste tu contraseña?** de la aplicación muestra este comando para ambas instalaciones: `docker compose exec librefolio python dev.py user reset …` para Docker, y `./dev.py user reset …` para una instalación en el host, para ejecutarse después de `pipenv shell` o con `pipenv run` delante.

### 👑 Conceder o quitar derechos de administrador

```bash
pipenv run ./dev.py user promote <username>
pipenv run ./dev.py user demote <username>
```

`demote` no comprueba que quede otro administrador: si no queda ninguno, promueve a alguien de nuevo.

---

## 🗄️ Mantener la base de datos

### ⬆️ Aplicar migraciones {: #apply-migrations }

Cada inicio del servidor aplica las migraciones pendientes por sí solo, por lo que rara vez necesitarás esto. Para hacerlo a mano, **detén el servidor** primero: `db upgrade` se niega a ejecutarse mientras el servidor responde en el puerto configurado.

```bash
# Aplica las migraciones pendientes
pipenv run ./dev.py db upgrade

# Muestra la migración en la que está la base de datos
pipenv run ./dev.py db current

# Busca restricciones CHECK faltantes: no cambia nada, sale con 1 si hay alguna
pipenv run ./dev.py db check

# Actualiza y comprueba otro archivo de base de datos, como una copia
pipenv run ./dev.py db upgrade /path/to/copy/app.db
pipenv run ./dev.py db check /path/to/copy/app.db
```

- 📄 Sin una ruta, los comandos usan la base de datos configurada. Una ruta designa otro archivo SQLite: una ruta relativa comienza en la raíz del proyecto, sin importar desde dónde ejecutes el comando. El archivo debe existir, excepto para `db upgrade`, que lo crea (incluida la carpeta) y lo pone al día.
- 🐳 En Docker, la ruta está dentro del contenedor, donde `LibreFolio-data/` es `/app/backend/data/prod-docker` (la base de datos es `sqlite/app.db` dentro de él). `db current` y `db check` funcionan en el contenedor en ejecución: `docker compose exec librefolio python dev.py db current <path>`. `db upgrade` y `db downgrade` necesitan el servidor detenido (`docker compose stop librefolio`), y luego un contenedor de un solo uso: `docker compose run --rm librefolio python dev.py db upgrade <path>` ([detalles](docker_advanced.md#docker-exec)).

### 🩹 Correcciones posteriores a la migración {: #post-migration-fixes }

Justo después de las migraciones, cada inicio también ejecuta las **correcciones posteriores a la migración**: reparaciones que una migración no puede hacer. Normalmente no hay nada que hacer. El registro (la salida del servidor, también guardada en `logs/`) puede mostrar:

- ✅ `Post-migration fixes applied and verified`: se hizo una reparación. En una base de datos grande, ese inicio es más lento, una sola vez.
- ⚠️ `Post-migration fix failed`: la base de datos se dejó tal como estaba y el servidor se inició con normalidad. La advertencia indica el error y la copia de la base de datos conservada junto a ella hasta que la elimines, como `app.db.pre-autoincrement-20261008T101500Z.bak`. La corrección se intenta de nuevo en el siguiente inicio.
- 🩺 `Post-migration fixes skipped`: no se pudo hacer la copia, o la base de datos no supera la comprobación de integridad de SQLite. No se cambió nada.

El archivo vacío `app.db.post-migration.lock`, junto a la base de datos, hace que las ejecuciones se turnen cuando varios workers arrancan a la vez: déjalo en su sitio.

La primera corrección, **`autoincrement`**, garantiza que el id de cualquier usuario, bróker, activo, transacción, ruta de conversión FX o evento de activo que se elimine nunca se asigne a uno nuevo. Mientras convierte una base de datos, elimina las carpetas de informes de los brókers que ya no existen, para que un nuevo bróker no pueda heredarlas.

??? tip "⌨️ Ejecutar las correcciones a mano — para previsualizarlas o reintentar una fallida"

    **Detén el servidor** primero (el script no lo comprueba), y luego ejecuta desde la raíz del proyecto:

    ```bash
    # Vista previa: informa de lo que se corregiría, no cambia nada
    pipenv run python -m backend.app.db.post_migration --dry-run

    # Aplica las correcciones
    pipenv run python -m backend.app.db.post_migration
    ```

    El script imprime cada corrección como `clean` (nada que hacer), `would_apply` (simulación), `applied` o `failed`, con las carpetas de brókers huérfanas, una copia conservada y cualquier error, y sale con `1` cuando algo falla. `--db PATH` y `--data-dir PATH` lo apuntan a otra base de datos o directorio de datos.

🔗 Cómo funcionan las correcciones por dentro: [Esquema de la base de datos — Correcciones posteriores a la migración](../developer/architecture/database/index.md#post-migration-fixes).

### 🔧 Añadir configuración global faltante

```bash
pipenv run ./dev.py user init-settings
```

Cada inicio añade los valores faltantes de la [Configuración global](settings.md) con sus valores por defecto; este comando hace lo mismo sin iniciar el servidor, y nunca cambia un valor ya establecido.

### 🧹 Restablecer la base de datos

```bash
pipenv run ./dev.py db create-clean
```

!!! warning "Se pierden todos los datos"

    `db create-clean` elimina la base de datos y crea una vacía. Al igual que `db upgrade`, se niega a ejecutarse mientras el servidor está activo. Los archivos subidos y los informes del bróker permanecen en el disco: consulta [Inicialización y restablecimiento de la base de datos](host_installation.md#database-reset).

---

## 📋 Árbol completo de comandos

```bash
# Todos los comandos, por categoría
pipenv run ./dev.py --help

# Las opciones de un comando
pipenv run ./dev.py server --help
```

??? info "👩‍💻 Comandos de desarrollo y documentación"

    - **Frontend**: `pipenv run ./dev.py front build`, `front dev`, `front check` — consulta [Desarrollo del frontend](../developer/frontend/index.md)
    - **Pruebas**: `pipenv run ./dev.py test all` — consulta [Recorrido de pruebas](../developer/test-walkthrough/index.md)
    - **Cliente de API**: `pipenv run ./dev.py api sync` — consulta [Resumen de la API](../developer/api/overview.md)
    - **i18n**: `pipenv run ./dev.py i18n audit` — consulta [Internacionalización](../developer/frontend/i18n.md)
    - **Documentación**: `pipenv run ./dev.py mkdocs deploy` publica esta documentación en GitHub Pages; `pipenv run ./dev.py mkdocs gallery` regenera sus capturas de pantalla con Playwright en un servidor de prueba (`--no-populate` conserva los datos de prueba actuales).

    El conjunto completo de herramientas para desarrolladores está en la [Guía del flujo de trabajo para desarrolladores](../developer/dev_workflow.md).
