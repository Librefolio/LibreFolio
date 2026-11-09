# 🛠️ Herramientas de línea de comandos

`dev.py` ejecuta las tareas de administración: iniciar el servidor, gestionar usuarios e invitaciones, mantener la base de datos y hacer copias de seguridad de la instancia. Cada sección indica **dónde** ejecutar el comando y cuándo necesita el servidor detenido.

!!! tip "Dónde ejecutar los comandos"

    | Instalación | Dónde | Forma del comando |
    | --- | --- | --- |
    | **En el host** | Terminal del servidor, en la carpeta de LibreFolio (la raíz del proyecto), entorno de Pipenv | `pipenv run ./dev.py <command>` — o `./dev.py <command>` tras `pipenv shell` |
    | **Docker, servidor en ejecución** | Terminal del host, en la carpeta de `docker-compose.yml` | `docker compose exec librefolio python dev.py <command>` |
    | **Docker, servidor detenido** | La misma terminal | `docker compose stop librefolio`, luego `docker compose run --rm librefolio python dev.py <command>` (contenedor de un solo uso) y después `docker compose start librefolio` |

    - En el contenedor no hay `pipenv run`: la imagen instala las dependencias globalmente.
    - `docker compose exec` ejecuta el comando como root. Desde una copia del código fuente, `./dev.py docker exec <command>` lo ejecuta, en cambio, como el usuario del servidor ([detalles](docker_advanced.md#docker-exec)).
    - Los comandos `user`, `db current`, `db check`, `db currencies`, `backup create`, `backup inspect`, `backup restore`, `backup decrypt` y `backup pending` funcionan en la imagen ([Copia de seguridad con Docker](cli_backup.md#backup-docker)). `db upgrade` y `db downgrade` necesitan el servidor detenido, así que la tercera forma ([Aplicar migraciones](#apply-migrations)). Los comandos de desarrollo, como `test`, no forman parte de la imagen.

!!! info "📚 Esta guía se reparte en varias páginas"

    Además de esta página: [Herramientas de administración de la CLI: copias de seguridad](cli_backup.md).

---

## 🖥️ Iniciar el servidor {: #start-the-server }

**En el host**, en la terminal del servidor, carpeta de LibreFolio. En Docker el servidor es el proceso principal del contenedor: `docker compose up -d` lo inicia.

```bash
# Standard start, one worker
pipenv run ./dev.py server

# Size the workers to the CPUs (`auto` and `0` do the same)
pipenv run ./dev.py server --workers auto

# Or set the number of workers
pipenv run ./dev.py server --workers 4

# Listen on another port (default: PORT from .env, else 6040)
pipenv run ./dev.py server --port 8080

# Kill whatever already holds the port, then start
pipenv run ./dev.py server --force
```

El servidor responde en el puerto elegido (`PORT` de `.env`; si no, 6040).

- 🧮 Más procesos worker atienden más solicitudes a la vez: úsalos en cualquier máquina con más de una CPU. `auto` inicia $\max(1,\ 2\,(n-1))$ procesos worker en $n$ CPU.
- ⏳ En el primer arranque, o cuando están desactualizadas, el servidor compila la interfaz web y esta documentación: tarda unos minutos. Si la interfaz no se compila, el servidor no arranca.
- 🔑 Un reinicio cierra la sesión de todos, a menos que `JWT_SECRET` esté definido en `.env` ([Configuración](configuration.md)).
- ⏹️ Ctrl+C detiene el servidor de forma limpia: `dev.py` le concede el [presupuesto de cierre](configuration_security.md#shutdown) más 2 segundos (10 segundos por defecto) y después lo finaliza; un segundo Ctrl+C lo finaliza de inmediato. Un SIGTERM enviado solo a `dev.py`, por ejemplo por un supervisor de procesos, recibe la misma espera: `dev.py` lo reenvía al servidor.

??? note "⚙️ Otras opciones del servidor — rara vez necesarias"

    | Opción | Qué hace |
    | --- | --- |
    | `--host HOST` | Dirección en la que escuchar (por defecto: `HOST` del entorno o de `.env`; si no, `0.0.0.0`) |
    | `--data-dir PATH` | Otro directorio de datos para esta ejecución, en lugar de `LIBREFOLIO_DATA_DIR` |
    | `--no-scheduler` | Iniciar sin las sincronizaciones programadas de precios y tipos de cambio FX |
    | `--rebuild`, `-r` | Recompilar la interfaz web aunque parezca estar actualizada |
    | `--debug`, `-d` | Registros `DEBUG`, una compilación de depuración de la interfaz web y las páginas de documentación de la API (`/api/v1/docs`, `/api/v1/redoc`), que de lo contrario están desactivadas |

    Formas cortas: `-w` para `--workers`, `-p` para `--port`, `-f` para `--force`. `--test`, `--coverage` y `--no-reload` son opciones de desarrollo: `pipenv run ./dev.py server --help` las enumera todas.

---

## 👤 Gestionar usuarios

**En el host** o **en Docker con el servidor en ejecución** (primera o segunda forma de la tabla anterior): estos comandos escriben directamente en la base de datos, por lo que también funcionan mientras el servidor está en ejecución.

En la aplicación, los administradores gestionan las cuentas y las invitaciones en **Configuración › Administración › Usuarios** ([Usuarios e invitaciones](users.md)). La línea de comandos sirve para un servidor sin navegador, o para superar el [límite de usuarios](configuration_accounts.md#user-limit).

### ➕ Crear y listar usuarios

```bash
# Create an administrator account
pipenv run ./dev.py user create <username> <email> <password>

# Create a regular account
pipenv run ./dev.py user create <username> <email> <password> --role user

# List all users: ID, username, email, active, administrator
pipenv run ./dev.py user list
```

`user list` imprime, para cada cuenta: ID, nombre de usuario, correo electrónico, activa, administrador.

- 👑 `user create` crea un **administrador**; con `--role user`, una cuenta normal. Las personas también pueden registrarse por su cuenta: con **Regístrate aquí** en la página de inicio de sesión mientras **Registro** esté **Abierto** (en una instancia nueva, también hasta que exista la primera cuenta), o con un [enlace de invitación](#invite) ([Quién puede registrarse](settings.md#registration)).
- 🔒 Contraseña: las mismas reglas que en la aplicación y la API. Al menos 8 caracteres, con una letra mayúscula, una letra minúscula, un dígito y un símbolo. Cuentan las letras y los dígitos de cualquier alfabeto (`É`, `é`); un símbolo es cualquier carácter que no sea una letra, un número ni un espacio (`!`, `_`, `€`). Una contraseña no válida no cambia nada: el comando imprime `Password does not meet security requirements:` y una línea por cada regla incumplida, que empieza por el código de la regla (`digit: the password must contain a digit`), y después sale con `1`.
- 🔤 Nombre de usuario: de 3 a 50 caracteres, sin `@` (al iniciar sesión, cualquier cosa que contenga `@` se interpreta como una dirección de correo electrónico). Los espacios, las letras acentuadas, `.`, `_`, `-`, `+` son válidos. Errores, cada uno con salida `1` y sin cambiar nada: `A username cannot contain @: the sign-in reads it as an email address`; `A username must be 3 to 50 characters long`; `Username already taken`; `Email already registered` si otra cuenta tiene esa dirección, o si la dirección es el nombre de usuario de otra cuenta ([`user set-email`](#set-email)), sin importar las mayúsculas.
- 📏 En el [límite de usuarios](configuration_accounts.md#user-limit), `user create` advierte `The instance is at its limit (LIBREFOLIO_MAX_USERS: 5 of 5 places taken): the command line creates the account anyway` y después crea la cuenta: la línea de comandos es la forma de superar el límite.

### ✉️ Invitar a alguien {: #invite }

```bash
# An invitation link for a regular account
pipenv run ./dev.py user invite

# An invitation for an administrator, with a note of whom it is for
pipenv run ./dev.py user invite --admin --email anna@example.com
```

El comando imprime un enlace que funciona una sola vez, durante 7 días: envíaselo a la persona, que lo abre y crea su propia cuenta con el nombre de usuario, el correo electrónico y la contraseña que elija ([lo que ve](../user/getting-started.md#invitation-link)).

- 👑 `--admin`: la nueva cuenta es administradora; sin esa opción, es una cuenta normal.
- ✉️ `--email`: solo una nota de a quién va dirigida la invitación; la persona puede registrarse con otra dirección.
- 🌐 Con [`LIBREFOLIO_PUBLIC_URL`](configuration_accounts.md#accounts) definida, el enlace está completo (`https://librefolio.example.com/invite#token=…`). Sin ella, el comando imprime solo la ruta, `/invite#token=…`, y te recuerda que pongas delante la dirección del servidor (`http://192.168.1.10:6040`). Si la variable está definida pero no es una dirección `http://` o `https://`, el recordatorio dice `LIBREFOLIO_PUBLIC_URL is not valid (…)`, con el motivo. Esto vale para todos los enlaces de esta página.
- 🔒 La parte secreta va después de `#`: los navegadores nunca la envían al servidor, por lo que no acaba en los registros del servidor ni del proxy. Envía el enlace completo.
- 🚪 Las invitaciones funcionan con **Registro** **Abierto** o **Por invitación**. Con **Cerrado**, el comando se detiene con `Registration is disabled: invitations cannot be created` y sale con `1`; los enlaces ya enviados tampoco funcionan.
- 📏 Una invitación ocupa una plaza del [límite de usuarios](configuration_accounts.md#user-limit) hasta que se usa, se revoca o caduca. En el límite, el comando advierte y después crea la invitación de todos modos.
- ⏳ Ningún comando cancela una invitación: un enlace que nadie usó caduca a los 7 días. Antes, **Revocar** en la pestaña [Usuarios](users.md#open-invitations), o mediante la API: `GET /api/v1/users/invites` enumera las invitaciones pendientes y `DELETE /api/v1/users/invites/<id>` revoca una.

### 🔑 Restablecer una contraseña o bloquear una cuenta {: #reset-a-password-or-lock-an-account }

```bash
# Set a new password (same rules as above)
pipenv run ./dev.py user reset <username> <new_password>

# Lock an account out, then let it back in
pipenv run ./dev.py user deactivate <username>
pipenv run ./dev.py user activate <username>
```

`reset` cambia la contraseña al instante; `deactivate` rechaza la cuenta desde su siguiente solicitud.

- ⏱️ `reset` termina las sesiones abiertas: a todos los dispositivos se les cierra la sesión en su siguiente solicitud. Para dejar a alguien fuera de forma definitiva, `deactivate`: volver a activar la cuenta no recupera sus sesiones antiguas.
- 🔗 `reset` también cancela cualquier [enlace de restablecimiento](#reset-link) que siga abierto para la cuenta, independientemente de quién lo haya creado.
- 👑 `deactivate` rechaza al último administrador activo: `User '<username>' is the last active administrator: promote or activate another administrator first`, salida `1`.
- 📏 En el [límite de usuarios](configuration_accounts.md#user-limit), `activate` sobre una cuenta desactivada advierte `… the command line reactivates the account anyway` y después la reactiva. Ninguna advertencia para una cuenta que ya ocupa su plaza: una que espera su correo con un enlace activo, o el administrador inicial que espera su enlace de configuración.
- 📬 Con la verificación de correo electrónico activada, `activate` permite entrar de inmediato a una cuenta que espera su correo y `deactivate` termina la espera: en cualquiera de los dos casos, sus enlaces de verificación dejan de funcionar (*Verificación de correo electrónico* en [Correo electrónico](email.md)).
- 🏁 En el [administrador inicial](configuration_accounts.md#initial-admin) que aún espera su enlace de configuración, `reset` y `activate` lo configuran sin el enlace y terminan la espera de forma definitiva: sus enlaces de configuración dejan de ser válidos, incluido el de `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`, y ni [`user setup-link`](#setup-link) ni un nuevo `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` le dan otro. `activate` por sí solo deja una cuenta activa cuya contraseña nadie conoce, hasta que `reset` o un [enlace de restablecimiento](#reset-link) le dé una; `reset` por sí solo la deja inactiva, hasta que intervengas con `activate`.
- 🚫 En ese mismo administrador que espera, `deactivate` no configura nada: cancela el enlace de configuración, como hace **Cancelar el enlace de configuración** en [Usuarios e invitaciones](users.md#cancel-setup). Imprime `✅ User '<username>' deactivated`; todos los enlaces de configuración de la cuenta dejan de ser válidos, incluido el de `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`, y la cuenta sigue esperando: [`user setup-link`](#setup-link) le da uno nuevo, y un **nuevo** `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` en el siguiente arranque también. El mismo token, en un reinicio, no: la instancia ya lo ha visto.
- 💬 La pantalla **¿Olvidaste tu contraseña?** de la aplicación muestra este comando para ambas instalaciones: para Docker, la línea `docker compose exec librefolio sh -c 'exec gosu …' sh user reset …` (la de [`docker exec`](docker_advanced.md#docker-exec), que se ejecuta como el usuario del servidor, no como root); para el host, `./dev.py user reset …`, tras `pipenv shell` o con `pipenv run` delante. Cuando la instancia puede enviar por correo un enlace de restablecimiento, la pantalla muestra solo el formulario de correo, sin los comandos ([Contraseñas olvidadas](email_flows.md#forgot-password)).

### 🔗 Enviar un enlace de restablecimiento de contraseña {: #reset-link }

```bash
pipenv run ./dev.py user reset-link <username>
```

El comando imprime un enlace: la persona lo abre y elige ella misma la nueva contraseña, en lugar de recibir la que elegiste tú con `user reset` ([lo que ve](../user/getting-started.md#password-reset-link)).

- ⏱️ El enlace funciona una sola vez, durante 30 minutos. Un nuevo enlace para la misma cuenta cancela los anteriores; un cambio de la contraseña o del correo electrónico de la cuenta —en el Perfil del usuario, o con `user reset` o `user set-email`— los cancela todos.
- 🚪 Una vez establecida la nueva contraseña, se cierra la sesión en todos los dispositivos con sesión iniciada, como con `user reset`. Crear el enlace no cierra la sesión de nadie.
- 🌐 Enlace completo con `LIBREFOLIO_PUBLIC_URL`, solo la ruta (`/reset-password#token=…`) sin ella ([como con las invitaciones](#invite)).

### 🔁 Un nuevo enlace de configuración para el administrador inicial {: #setup-link }

```bash
pipenv run ./dev.py user setup-link
```

El comando imprime un nuevo enlace de configuración para el administrador creado a partir de `LIBREFOLIO_ADMIN_EMAIL` en el primer arranque ([El administrador inicial](configuration_accounts.md#initial-admin)), mientras nadie haya usado el suyo: lo abre, elige la contraseña y se inicia sesión. Úsalo cuando el enlace haya caducado, se haya perdido o se haya cancelado.

- ⏱️ El enlace funciona una sola vez, durante 72 horas. Los enlaces de configuración anteriores dejan de ser válidos, incluido el de `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`.
- 🚫 Tras una cancelación —**Cancelar el enlace de configuración** en [Usuarios e invitaciones](users.md#cancel-setup), o `user deactivate` sobre el administrador que espera— el administrador sigue esperando: este comando le da un nuevo enlace.
- 📮 Tras una nueva dirección para el administrador que espera —`LIBREFOLIO_ADMIN_EMAIL` cambiada antes de un reinicio, o [`user set-email`](#set-email)— sus enlaces, enviados a la dirección anterior, dejan de ser válidos: este comando le da un enlace para la nueva. La misma dirección con otras mayúsculas de las letras A-Z no es un cambio: el enlace sigue funcionando.
- 🔚 Configurado de otra forma —`user activate`, o una contraseña asignada con `user reset` o con un [enlace de restablecimiento](#reset-link)— el administrador ya no espera: sus enlaces dejan de ser válidos de forma definitiva y el comando se detiene con el error que se indica abajo.
- 🌐 Enlace completo con `LIBREFOLIO_PUBLIC_URL`, solo la ruta (`/setup#token=…`) sin ella ([como con las invitaciones](#invite)).
- 📧 El comando solo imprime el enlace: no envía ningún correo electrónico.
- ❌ Sin un administrador que espere, el comando se detiene con `No administrator account is waiting for its setup link` y sale con `1`. Lo mismo ocurre si el administrador completa la configuración mientras el comando se ejecuta: el comando lo comprueba de nuevo justo antes de emitir el enlace y no da ninguno a una cuenta ya configurada.

### 📧 Cambiar la dirección de correo electrónico de una cuenta {: #set-email }

```bash
pipenv run ./dev.py user set-email <username> <new_email>
```

El mismo cambio que un nuevo correo electrónico en el [Perfil](../user/settings/profile.md#email-change) del usuario, sin su contraseña: para quien no puede cambiar su dirección por su cuenta, o para separar dos cuentas que comparten una ([más abajo](#email-case-conflict)).

- 🔤 Una dirección pertenece a una sola cuenta, sin importar las mayúsculas: `Anna@example.com` y `anna@example.com` son la misma dirección. Solo las letras A-Z se comparan de esta forma, no las acentuadas: `Émile@example.com` y `émile@example.com` son dos direcciones diferentes.
- 🚪 Una nueva dirección cierra la sesión de la cuenta en todos los dispositivos, cancela todos los enlaces de restablecimiento de contraseña y todos los enlaces de cambio de correo electrónico pendientes, y se registra como no verificada; la cuenta aún puede iniciar sesión. No toca la contraseña. La misma dirección con otras mayúsculas solo cambia la forma de escribirla: no se cierra la sesión de nadie y sigue verificada.
- 👑 En el administrador inicial que aún espera su enlace de configuración, la nueva dirección también invalida ese enlace: la cuenta sigue esperando, y [`user setup-link`](#setup-link) le da uno nuevo. Mientras `LIBREFOLIO_ADMIN_EMAIL` esté definida, cada arranque del servidor vuelve a asignar esa dirección a la cuenta que espera: cambia también la variable, o el siguiente arranque restaurará la dirección anterior e invalidará también el nuevo enlace.
- ❌ Rechazados, con salida `1` y sin cambiar nada: una dirección que ya tiene otra cuenta, sin importar las mayúsculas (`Email already registered`); una dirección que es el nombre de usuario de otra cuenta, sin importar las mayúsculas (el mismo error: una cuenta creada antes de la versión 1.3 puede tener un `@` en su nombre de usuario, [Nombres de usuario con una @](users.md#usernames-with-at), y si ese nombre pasara a ser la dirección de alguien, el inicio de sesión, que interpreta primero una dirección, ya no encontraría esa cuenta); una dirección no válida (`Not an email address`); un nombre de usuario desconocido (`User '<username>' not found`). El propio nombre de usuario de la cuenta no es un obstáculo: puede convertirse en su dirección.

### 👑 Conceder o retirar derechos de administrador

```bash
pipenv run ./dev.py user promote <username>
pipenv run ./dev.py user demote <username>
```

Una degradación cierra la sesión de la cuenta en todos los dispositivos.

- 👑 `demote` rechaza al último administrador activo: `User '<username>' is the last active administrator: promote another user first`, salida `1`.
- 🏁 `demote` también rechaza al [administrador inicial](configuration_accounts.md#initial-admin) que aún espera su enlace de configuración, que conserva su rol hasta entonces: `User '<username>' is the initial administrator waiting for its setup: it keeps its role until then; deactivate it to cancel its setup link, or delete it from Settings › Administration › Users`, salida `1`, sin cambiar nada. Para cancelar su enlace: `user deactivate` ([más arriba](#reset-a-password-or-lock-an-account)). Para eliminar la cuenta: bórrala en [Usuarios e invitaciones](users.md#delete), sin degradarla antes. La línea de comandos no elimina ninguna cuenta.

### 🧭 Reiniciar las guías de un usuario {: #reset-onboarding }

```bash
# Every guide, the Welcome setup included
pipenv run ./dev.py user reset-onboarding <username>

# One guide only
pipenv run ./dev.py user reset-onboarding <username> --flow intro_tour
```

La próxima vez que el usuario abra LibreFolio, la configuración de bienvenida y las guías vuelven a empezar, como en su primera visita; los datos y las preferencias del usuario se mantienen. `--flow` reinicia una sola guía: `pipenv run ./dev.py user reset-onboarding --help` enumera los nombres (`welcome`, `intro_tour`, `import_guide`…).

---

## 🗄️ Mantener la base de datos

### ⬆️ Aplicar migraciones {: #apply-migrations }

Cada arranque del servidor aplica por sí mismo las migraciones pendientes: rara vez necesitas hacerlo a mano.

**En el host**, en la terminal del servidor, carpeta de LibreFolio, **con el servidor detenido**: `db upgrade` se niega a ejecutarse mientras el servidor responde en el puerto configurado. `db current`, `db check` y `db currencies` no cambian nada y también se ejecutan con el servidor en marcha.

```bash
# Apply pending migrations
pipenv run ./dev.py db upgrade

# Show the migration the database is at
pipenv run ./dev.py db current

# Look for missing CHECK constraints: changes nothing, exits with 1 if any
pipenv run ./dev.py db check

# List the currency codes that are not ISO codes: changes nothing, exits with 1 if any
pipenv run ./dev.py db currencies

# Upgrade and check another database file, such as a copy
pipenv run ./dev.py db upgrade /path/to/copy/app.db
pipenv run ./dev.py db check /path/to/copy/app.db
```

`db upgrade` lleva la base de datos a la última migración; `db current` imprime aquella en la que se encuentra.

- 📄 Sin una ruta, los comandos usan la base de datos configurada. Una ruta nombra otro archivo SQLite: una relativa empieza en la raíz del proyecto, desde dondequiera que ejecutes el comando. El archivo debe existir, excepto para `db upgrade`, que lo crea (incluida la carpeta) y lo pone al día.
- 🐳 **En Docker**, la ruta está dentro del contenedor: `LibreFolio-data/` es `/app/backend/data/prod-docker`, y la base de datos es `sqlite/app.db` dentro de ella. `db current`, `db check` y `db currencies`: servidor en ejecución, `docker compose exec librefolio python dev.py db current <path>`. `db upgrade` y `db downgrade`: servidor detenido (`docker compose stop librefolio`) y después un contenedor de un solo uso, `docker compose run --rm librefolio python dev.py db upgrade <path>` ([detalles](docker_advanced.md#docker-exec)).

### 🔤 Dos cuentas con la misma dirección de correo electrónico {: #email-case-conflict }

A partir de la versión 1.3, una dirección de correo electrónico pertenece a una sola cuenta, sin importar las mayúsculas. Si una base de datos anterior tiene dos cuentas con direcciones que solo difieren en las mayúsculas (`Anna@example.com` y `anna@example.com`), la actualización se detiene en la migración que comprueba esto y el servidor no arranca. Las migraciones anteriores siguen aplicadas, no se cambia ninguna cuenta y el siguiente arranque continúa desde ahí. El registro (o la salida de `db upgrade`) nombra las cuentas por id y nombre de usuario, nunca por dirección; un `;` separa un grupo del siguiente:

```text
Email addresses must be unique regardless of case (release 1.3), and these accounts share one apart from upper and lower case: #3 'anna', #8 'anna_work'. Give all but one account of each group another address with …
```

LibreFolio nunca fusiona dos cuentas: asigna otra dirección a todas las cuentas de cada grupo menos a una y después vuelve a iniciar LibreFolio.

=== "En el host"

    En la terminal del servidor, carpeta de LibreFolio:

    ```bash
    pipenv run ./dev.py user set-email <username> <new_email>
    ```

=== "Docker"

    En la carpeta de `docker-compose.yml`. El servidor es el proceso principal del contenedor, así que el contenedor no se mantiene en ejecución y `docker compose exec` no sirve: usa un contenedor de un solo uso.

    ```bash
    docker compose stop librefolio
    docker compose run --rm librefolio python dev.py user set-email <username> <new_email>
    docker compose start librefolio
    ```

### 🩹 Reparaciones posteriores a las migraciones {: #post-migration-fixes }

Justo después de las migraciones, cada arranque ejecuta las **reparaciones posteriores a las migraciones**: reparaciones que una migración no puede hacer. Normalmente no hay nada que hacer. En el registro (la salida del servidor, que también se guarda en `logs/`) puedes leer:

| Línea del registro | Significado |
| --- | --- |
| ✅ `Post-migration fixes applied and verified` | Se hizo una reparación. En una base de datos grande, ese arranque es más lento, una sola vez. |
| ⚠️ `Post-migration fix failed` | Base de datos dejada como estaba, servidor arrancado con normalidad. La advertencia indica el error y la copia de la base de datos que se conserva junto al original hasta que la borres (`app.db.pre-autoincrement-20261008T101500Z.bak`). La reparación se vuelve a intentar en el siguiente arranque. |
| 🩺 `Post-migration fixes skipped` | No se pudo hacer la copia, o la base de datos no supera la comprobación de integridad de SQLite. No se cambió nada. |
| 🔗 `Foreign key violations already in the database, left as they are` | La base de datos contiene referencias a filas que ya no existen, enumeradas en la advertencia. Las reparaciones las dejan como están y aun así se ejecutan: una reparación solo falla por una referencia rota que ella misma añadiría. |

El archivo vacío `app.db.post-migration.lock`, junto a la base de datos, hace que las ejecuciones se turnen cuando varios procesos worker arrancan a la vez: déjalo en su sitio.

Las reparaciones:

- **`autoincrement`**: el id de un usuario, bróker, activo, transacción, ruta de conversión FX o evento de activo eliminado nunca se vuelve a asignar. Al convertir, elimina las carpetas de informes de los brókers que ya no existen, para que un nuevo bróker no las herede.
- **`orphan_pair_halves`**, una vez: repara las transferencias que la eliminación de un bróker dejó sin su otra mitad en los brókers restantes.
    - 📈 Valores recibidos del bróker eliminado → posición de apertura al coste de transferencia, a partir de la fecha de transferencia. El capital de ese bróker los cuenta a ese coste, no a su valor de mercado al llegar, por lo que su ganancia también incluye lo que ganaron antes de la transferencia. Sin un coste registrado se quedan sin uno y la aplicación informa de una adquisición sin valor de compra: introduce el coste en la transacción.
    - 💶 Transferencias de efectivo con el bróker eliminado → depósitos o retiros: el capital y la ganancia no cambian.
    - 📤 Valores enviados **al** bróker eliminado: justo después de las reparaciones, en el mismo arranque, cada transferencia se convierte en un ajuste que saca los valores del bróker emisor, sin valor: solo disminuye la cantidad, y el coste cuenta como una pérdida realizada en ese bróker. Una línea de registro para cada una (`Lone transfer leg converted to an ADJUSTMENT-out without a value`). Si la base de datos no supera la comprobación rápida de SQLite, se quedan como estaban (`Lone transfer legs left as they are: the database failed its quick check`). Si falla todo el paso (`Lone transfer legs could not be converted; starting normally`), no se cambia nada y el servidor arranca de todos modos.
- **`event_types`**, una vez: repara los eventos de activo con un tipo que LibreFolio no conoce, como `dividend` o `dividendo` escritos a mano en un CSV. Hasta ahora, un evento así hacía que fallara la carga de toda la lista de eventos del activo, por lo que no se mostraba ninguno.
    - ✅ Un tipo que solo difiere en mayúsculas/minúsculas o espacios (`dividend`, ` Split `) se corrige.
    - 🗑️ Un evento cuyo tipo sigue siendo desconocido se elimina. Una transacción vinculada permanece, sin su evento: vuelve a vincularla al evento correcto si lo necesitas.

??? tip "⌨️ Ejecutar las reparaciones a mano — para previsualizarlas o reintentar una fallida"

    **En el host**, en la terminal del servidor, carpeta de LibreFolio, **con el servidor detenido** (el script no lo comprueba). En Docker: [Reparaciones posteriores a las migraciones con el servidor detenido](docker_advanced.md#post-migration-fixes).

    ```bash
    # Preview: report what would be fixed, change nothing
    pipenv run python -m backend.app.db.post_migration --dry-run

    # Apply the fixes
    pipenv run python -m backend.app.db.post_migration
    ```

    El script imprime cada reparación como `clean` (nada que hacer), `would_apply` (simulación), `applied` o `failed`, con las carpetas de brókers huérfanas, una copia conservada y cualquier error; después, una línea por cada transferencia de valores enviada a un bróker eliminado (`Lone transfer leg …`); sale con `1` cuando algo falla. `--db PATH` y `--data-dir PATH` lo apuntan a otra base de datos o a otro directorio de datos.

    Para ver qué hará `orphan_pair_halves` en tu base de datos, ejecuta `--dry-run` antes del primer arranque de la nueva versión: imprime `Fix orphan_pair_halves: would_apply` cuando hay algo que reparar, y una advertencia enumera las transacciones por id, agrupadas por conversión (`TRANSFER->ADJUSTMENT`), con las que se quedarán sin coste y las transferencias de valores enviadas a un bróker eliminado; estas reciben una línea cada una después de las reparaciones (`would become an ADJUSTMENT-out without a value`). El script imprime en la consola lo que el servidor escribiría en el registro: la advertencia y, en una ejecución real, una línea por cada transacción modificada (con `LOG_LEVEL` en `INFO`, el valor predeterminado). No escribe ningún archivo de registro: conserva su salida si quieres tener constancia de la reparación.

🔗 Cómo funcionan las reparaciones por dentro: [Esquema de la base de datos — Reparaciones posteriores a las migraciones](../developer/architecture/database/index.md#post-migration-fixes).

### 💱 Códigos de divisa que no son códigos ISO {: #currency-codes }

A partir de la versión 1.3, LibreFolio guarda una divisa solo como un código alfabético ISO 4217 (`EUR`, `USD`). Las versiones anteriores también aceptaban el nombre o el código numérico y lo guardaban tal como se escribía: `Euro`, `978`. Ese valor todavía se lee, pero se rechaza una edición que vuelva a guardar su fila hasta que se corrija el código, y sus importes no se suman con los del código ISO: `978` y `EUR` forman dos saldos. Una copia de seguridad restaurada puede traer de vuelta esos valores.

Poco después de cada arranque, el registro advierte cuando la base de datos contiene alguno; LibreFolio no los cambia por sí mismo:

```text
Stored currency codes that are not ISO 4217 codes: an edit of their rows is refused until they are corrected (./dev.py db currencies lists them)
```

**En el host** o **en Docker con el servidor en ejecución** (`docker compose exec librefolio python dev.py db currencies`):

```bash
# Where each value is stored, how many rows hold it, and the ISO code it stands for
pipenv run ./dev.py db currencies

# Another database file, such as a copy
pipenv run ./dev.py db currencies /path/to/copy/app.db
```

El comando enumera los valores sin cambiar nada.

- 🔎 Cada línea indica el lugar (`transactions.currency`, `assets.currency`, los pasos de una ruta FX, la configuración de un proveedor, la divisa base de un usuario…), el valor, cuántas filas lo contienen y el código ISO que representa: `978` es `EUR`, `US DOLLAR` es `USD`.
- ➖ Un guion: ningún código único. Un nombre que comparten dos divisas (`Bolívar Soberano`: `VED` o `VES`), un valor que no es una divisa, o un código que cuenta céntimos en lugar de unidades (`GBX`, `ZAC`, `ILA`), que nunca debe renombrarse sin más.
- 🔤 Un código en minúsculas o con espacios (`eur`) también se enumera: la divisa correcta, en una forma que las comparaciones exactas no detectan.
- 🧱 Un valor guardado como bytes sin procesar o como texto que no es UTF-8 válido, algo que solo contiene una base de datos dañada o hecha a mano, aparece en la notación de SQLite (`X'455552'`) con un guion: nunca es un código.
- 🚦 Salida `0` cuando todos los códigos son ISO, `1` cuando enumera alguno, `2` cuando no puede leer la base de datos.

### 🔧 Añadir la configuración global que falta

**En el host** o **en Docker con el servidor en ejecución**:

```bash
pipenv run ./dev.py user init-settings
```

Añade la [Configuración global](settings.md) que falta con sus valores predeterminados, como hace cada arranque, pero sin iniciar el servidor; nunca cambia un valor ya establecido.

### 🧹 Restablecer la base de datos

**En el host**, en la terminal del servidor, carpeta de LibreFolio, **con el servidor detenido**:

```bash
pipenv run ./dev.py db create-clean
```

!!! warning "Se pierden todos los datos"

    `db create-clean` elimina la base de datos y crea una vacía. Como `db upgrade`, se niega a ejecutarse mientras el servidor está activo. Los archivos subidos y los informes de los brókers permanecen en el disco: [Inicialización y restablecimiento de la base de datos](host_installation.md#database-reset).

---

## 📋 Árbol completo de comandos

```bash
# Every command, by category
pipenv run ./dev.py --help

# The options of one command
pipenv run ./dev.py server --help
```

??? info "👩‍💻 Comandos para desarrollo y documentación"

    - **Frontend**: `pipenv run ./dev.py front build`, `front dev`, `front check` — [Desarrollo del frontend](../developer/frontend/index.md)
    - **Pruebas**: `pipenv run ./dev.py test all` — [Recorrido por las pruebas](../developer/test-walkthrough/index.md)
    - **Cliente de API**: `pipenv run ./dev.py api sync` — [Resumen de la API](../developer/api/overview.md)
    - **i18n**: `pipenv run ./dev.py i18n audit` — [Internacionalización](../developer/frontend/i18n.md)
    - **Documentación**: `pipenv run ./dev.py mkdocs deploy` publica esta documentación en GitHub Pages; `pipenv run ./dev.py mkdocs gallery` regenera las capturas de pantalla con Playwright en un servidor de pruebas (`--no-populate` conserva los datos de prueba actuales).

    El conjunto completo de herramientas para desarrolladores: [Guía del flujo de trabajo para desarrolladores](../developer/dev_workflow.md).

---

## 🔗 Relacionado

- 📄 **[Herramientas de administración de la CLI: copias de seguridad](cli_backup.md)** — Hacer una copia de seguridad de la instancia
