# 🛠️ Herramientas de línea de comandos

`dev.py`, en la raíz del proyecto, ejecuta las tareas de administración: iniciar el servidor, gestionar usuarios, mantener la base de datos y hacer copias de seguridad de la instancia. Cada sección indica cuándo un comando necesita el servidor detenido.

!!! tip "Dónde ejecutar los comandos"

    - **Instalación en el host**: en el entorno de Pipenv, con el prefijo `pipenv run` que se usa en esta página, o después de `pipenv shell`.
    - **Docker**: en el contenedor en ejecución, con `docker compose exec librefolio python dev.py <command>` (desde una copia del código fuente, `./dev.py docker exec <command>`, que lo ejecuta como el usuario del servidor en lugar de root). Ahí no se usa `pipenv run`: la imagen instala las dependencias globalmente. Los comandos de usuario, `db current`, `db check`, `backup create`, `backup inspect`, `backup restore`, `backup decrypt` y `backup pending` funcionan ahí ([Hacer una copia de seguridad con Docker](cli_backup.md#backup-docker)); `db upgrade` y `db downgrade` no, ya que necesitan el servidor detenido ([Aplicar migraciones](#apply-migrations)). Los comandos de desarrollo, como `test`, no forman parte de la imagen ([detalles](docker_advanced.md#docker-exec)).

!!! info "📚 Esta guía se reparte en varias páginas"

    Además de esta página: [Herramientas de administración de la CLI: copias de seguridad](cli_backup.md).

---

## 🖥️ Iniciar el servidor {: #start-the-server }

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

- 🧮 Más procesos worker atienden más solicitudes a la vez: úsalos en cualquier máquina con más de una CPU. `auto` inicia $\max(1,\ 2\,(n-1))$ procesos worker en $n$ CPU.
- ⏳ El servidor primero compila la interfaz web y esta documentación cuando faltan o están desactualizadas, así que el primer arranque tarda unos minutos. Si la interfaz no se compila, el servidor no arranca.
- 🔑 Un reinicio cierra la sesión de todos, a menos que `JWT_SECRET` esté definido en `.env` (consulta [Configuración](configuration.md)).
- ⏹️ Ctrl+C detiene el servidor de forma limpia: `dev.py` le concede hasta el [presupuesto de cierre](configuration_security.md#shutdown) más 2 segundos para detenerse (10 segundos por defecto), y después lo finaliza; un segundo Ctrl+C lo finaliza de inmediato. Un SIGTERM enviado solo a `dev.py`, por ejemplo por un supervisor de procesos, recibe la misma espera: `dev.py` lo reenvía al servidor.

??? note "⚙️ Otras opciones del servidor — rara vez necesarias"

    | Opción | Qué hace |
    | --- | --- |
    | `--host HOST` | Dirección en la que escuchar (por defecto: `HOST` del entorno o de `.env`; si no, `0.0.0.0`) |
    | `--data-dir PATH` | Usar otro directorio de datos para esta ejecución, en lugar de `LIBREFOLIO_DATA_DIR` |
    | `--no-scheduler` | Iniciar sin las sincronizaciones programadas de precios y FX |
    | `--rebuild`, `-r` | Recompilar la interfaz web aunque parezca estar actualizada |
    | `--debug`, `-d` | Registros `DEBUG`, una compilación de depuración de la interfaz web y las páginas de documentación de la API (`/api/v1/docs`, `/api/v1/redoc`), que de lo contrario están desactivadas |

    Formas cortas: `-w` para `--workers`, `-p` para `--port`, `-f` para `--force`. `--test`, `--coverage` y `--no-reload` son opciones de desarrollo: `pipenv run ./dev.py server --help` las enumera todas.

---

## 👤 Gestionar usuarios

Estos comandos escriben directamente en la base de datos, por lo que también funcionan mientras el servidor está en ejecución.

En la aplicación, los administradores gestionan las demás cuentas y las invitaciones desde la pestaña **Usuarios** de **Configuración › Administración**: consulta [Usuarios e invitaciones](users.md). Los comandos siguientes no necesitan navegador: úsalos en un servidor sin interfaz gráfica o para superar el [límite de usuarios](configuration_accounts.md#user-limit).

### ➕ Crear y listar usuarios

```bash
# Create an administrator account
pipenv run ./dev.py user create <username> <email> <password>

# Create a regular account
pipenv run ./dev.py user create <username> <email> <password> --role user

# List all users: ID, username, email, active, administrator
pipenv run ./dev.py user list
```

- 👑 `user create` crea un **administrador** a menos que añadas `--role user`, que crea una cuenta normal. Las personas también pueden crear su propia cuenta: con **Registrarse aquí** en la página de inicio de sesión mientras **Registro** esté **Abierto** (en una instancia nueva, también hasta que exista su primera cuenta), o con un [enlace de invitación](#invite) (consulta [Quién puede registrarse](settings.md#registration)).
- 🔒 La contraseña sigue las mismas reglas que en la aplicación y la API: al menos 8 caracteres, con una letra mayúscula, una letra minúscula, un dígito y un símbolo. Cuentan las letras y los dígitos de cualquier alfabeto, como `É` o `é`; un símbolo es cualquier carácter que no sea una letra, un número ni un espacio, como `!`, `_` o `€`. Una contraseña que incumple una regla no cambia nada: el comando imprime `Password does not meet security requirements:` y una línea por cada regla incumplida, cada una empezando por el código de la regla, como `digit: the password must contain a digit`, y después sale con `1`.
- 🔤 Un nombre de usuario no puede contener `@`: al iniciar sesión, LibreFolio interpreta cualquier cosa con un `@` como una dirección de correo electrónico. Un nombre de usuario así no cambia nada: el comando se detiene con el error `A username cannot contain @: the sign-in reads it as an email address` y sale con `1`. Los espacios, las letras acentuadas y los signos como `.`, `_`, `-` o `+` son válidos. Un nombre de usuario también debe tener entre 3 y 50 caracteres, como en el registro: uno más corto o más largo tampoco cambia nada; el comando se detiene con el error `A username must be 3 to 50 characters long` y sale con `1`. El comando también se detiene, con `Username already taken`, ante un nombre de usuario que ya tiene otra cuenta y, con `Email already registered`, ante una dirección que ya tiene otra cuenta o que es el nombre de usuario de otra cuenta (consulta [`user set-email`](#set-email)), sin importar las mayúsculas.
- 📏 Cuando la instancia ha alcanzado su [límite de usuarios](configuration_accounts.md#user-limit), `user create` advierte `The instance is at its limit (LIBREFOLIO_MAX_USERS: 5 of 5 places taken): the command line creates the account anyway` y después la crea: la línea de comandos es la forma de superar el límite.

### ✉️ Invitar a alguien {: #invite }

```bash
# An invitation link for a regular account
pipenv run ./dev.py user invite

# An invitation for an administrator, with a note of whom it is for
pipenv run ./dev.py user invite --admin --email anna@example.com
```

El comando imprime un enlace que funciona una sola vez, durante 7 días. Envíalo a la persona: lo abre y crea su cuenta con el nombre de usuario, el correo electrónico y la contraseña que elija ([lo que ve](../user/getting-started.md#invitation-link)).

- 👑 `--admin` convierte la nueva cuenta en administrador; sin esa opción, la cuenta es normal.
- ✉️ `--email` solo sirve para indicar a quién va dirigida la invitación: la persona puede registrarse con otra dirección.
- 🌐 Con [`LIBREFOLIO_PUBLIC_URL`](configuration_accounts.md#accounts) definida, el enlace está completo, como `https://librefolio.example.com/invite#token=…`. Sin ella, el comando imprime solo la ruta, `/invite#token=…`, y te recuerda que pongas delante la dirección de tu servidor, como `http://192.168.1.10:6040`. Si la variable está definida pero no es una dirección `http://` o `https://`, el recordatorio dice en su lugar `LIBREFOLIO_PUBLIC_URL is not valid (…)`, con el motivo.
- 🔒 La parte secreta del enlace va después de `#`: los navegadores nunca envían esa parte al servidor, por lo que no acaba en los registros del servidor ni del proxy. Envía el enlace completo.
- 🚪 Las invitaciones funcionan mientras **Registro** esté **Abierto** o **Por invitación**. Mientras esté **Cerrado**, el comando se detiene con el error `Registration is disabled: invitations cannot be created` y sale con `1`, y los enlaces ya enviados tampoco funcionan.
- 📏 Una invitación ocupa una plaza del [límite de usuarios](configuration_accounts.md#user-limit) hasta que se usa, se revoca o caduca. En el límite, el comando advierte y después crea la invitación de todos modos.
- ⏳ No hay ningún comando para cancelar una invitación: un enlace que nadie usó deja de funcionar a los 7 días. Un administrador puede revocarla antes con **Revocar** en la pestaña [Usuarios](users.md#open-invitations), o mediante la API: `GET /api/v1/users/invites` enumera las invitaciones pendientes y `DELETE /api/v1/users/invites/<id>` revoca una.

### 🔑 Restablecer una contraseña o bloquear una cuenta {: #reset-a-password-or-lock-an-account }

```bash
# Set a new password (same rules as above)
pipenv run ./dev.py user reset <username> <new_password>

# Lock an account out, then let it back in
pipenv run ./dev.py user deactivate <username>
pipenv run ./dev.py user activate <username>
```

- ⏱️ Un restablecimiento termina las sesiones ya abiertas: a todos los dispositivos con sesión iniciada en la cuenta se les cierra la sesión en su siguiente solicitud. Para dejar a alguien fuera de forma definitiva, desactiva la cuenta: se le rechaza desde su siguiente solicitud, y volver a activarla no recupera sus sesiones antiguas.
- 🔗 Un restablecimiento también cancela cualquier enlace de restablecimiento de contraseña que siga abierto para la cuenta, independientemente de quién lo haya creado.
- 👑 `deactivate` rechaza al último administrador activo: se detiene con el error `User '<username>' is the last active administrator: promote or activate another administrator first` y sale con `1`.
- 📏 Cuando la instancia ha alcanzado su [límite de usuarios](configuration_accounts.md#user-limit), `activate` sobre una cuenta desactivada advierte `… the command line reactivates the account anyway` y después la reactiva. No imprime ninguna advertencia para una cuenta que ya ocupa su plaza: una que espera su correo con un enlace activo (más abajo), o el administrador inicial que espera su enlace de configuración.
- 📬 Con la verificación de correo electrónico activada, `activate` permite entrar de inmediato a una cuenta que espera su correo —sin advertencia de límite mientras su enlace esté activo, ya que su plaza ya está contada— y `deactivate` termina su espera: en cualquiera de los dos casos, los enlaces de verificación que se le enviaron dejan de funcionar. Consulta *Verificación de correo electrónico* en [Correo electrónico](email.md).
- 🏁 En el [administrador inicial](configuration_accounts.md#initial-admin) que aún espera su enlace de configuración, `reset` y `activate` funcionan como en cualquier cuenta: lo configuran sin su enlace, y `activate` no imprime ninguna advertencia de límite, ya que la cuenta ya ocupa su plaza. Cualquiera de los dos termina la espera de forma definitiva: sus enlaces de configuración dejan de funcionar, incluido el de `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`, y ni [`user setup-link`](#setup-link) ni un nuevo `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` le dan otro. `activate` por sí solo deja una cuenta activa cuya contraseña nadie conoce, hasta que `reset` o un [enlace de restablecimiento](#reset-link) le dé una; `reset` por sí solo la deja inactiva, hasta `activate`.
- 🚫 En ese administrador que aún espera, `deactivate` no configura nada: cancela el enlace de configuración, como hace **Cancelar enlace de configuración** en [Usuarios e invitaciones](users.md#cancel-setup). El comando imprime `✅ User '<username>' deactivated`; todos los enlaces de configuración de la cuenta dejan de funcionar, incluido el de `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`, y la cuenta sigue esperando uno nuevo: [`user setup-link`](#setup-link) le da uno, y un nuevo `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` en el siguiente arranque también. El mismo token en un reinicio no da ninguno, ya que la instancia ya lo ha visto.
- 💬 La pantalla **¿Olvidaste tu contraseña?** de la aplicación muestra este comando para ambas instalaciones: la línea `docker compose exec librefolio sh -c 'exec gosu …' sh user reset …` para Docker (la de [`docker exec`](docker_advanced.md#docker-exec), que se ejecuta como el usuario del servidor, no como root), y `./dev.py user reset …` para una instalación en el host, para ejecutarlo después de `pipenv shell` o con `pipenv run` delante. Cuando tu instancia puede enviar por correo un enlace de restablecimiento, la pantalla muestra primero el formulario de correo y mantiene los comandos en un panel cerrado de forma predeterminada ([Contraseñas olvidadas](email_flows.md#forgot-password)).

### 🔗 Enviar un enlace de restablecimiento de contraseña {: #reset-link }

```bash
pipenv run ./dev.py user reset-link <username>
```

En lugar de elegir una nueva contraseña para alguien con `user reset`, envíale este enlace: lo abre y elige la nueva contraseña por su cuenta ([lo que ve](../user/getting-started.md#password-reset-link)).

- ⏱️ El enlace funciona una sola vez, durante 30 minutos. Un nuevo enlace para la misma cuenta cancela los anteriores; un cambio de la contraseña o de la dirección de correo electrónico de la cuenta —en el perfil del usuario, o con `user reset` o `user set-email`— los cancela todos.
- 🚪 Una vez establecida la nueva contraseña, se cierra la sesión en todos los dispositivos con sesión iniciada en la cuenta, como con `user reset`. Crear el enlace no cierra la sesión de nadie.
- 🌐 Al igual que con las [invitaciones](#invite), el enlace está completo cuando `LIBREFOLIO_PUBLIC_URL` está definida, y solo la ruta (`/reset-password#token=…`) cuando no lo está.

### 🔁 Un nuevo enlace de configuración para el administrador inicial {: #setup-link }

```bash
pipenv run ./dev.py user setup-link
```

Cuando LibreFolio creó el administrador a partir de `LIBREFOLIO_ADMIN_EMAIL` en su primer arranque ([El administrador inicial](configuration_accounts.md#initial-admin)) y nadie ha usado aún su enlace de configuración, este comando imprime uno nuevo: el administrador lo abre, elige la contraseña y se inicia sesión. Úsalo cuando el enlace haya caducado, se haya perdido o se haya cancelado.

- ⏱️ El enlace funciona una sola vez, durante 72 horas. Los enlaces de configuración emitidos antes dejan de funcionar, incluido el de `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`.
- 🚫 Un enlace cancelado —**Cancelar enlace de configuración** en [Usuarios e invitaciones](users.md#cancel-setup), o `user deactivate` sobre el administrador que espera— deja al administrador esperando: este comando le da un nuevo enlace.
- 📮 Una nueva dirección para el administrador que espera —`LIBREFOLIO_ADMIN_EMAIL` cambiada antes de un reinicio, o [`user set-email`](#set-email)— invalida sus enlaces de configuración, que iban a la dirección anterior. El administrador sigue esperando: este comando le da un enlace para la nueva dirección. La misma dirección con otras mayúsculas de las letras A a Z no es un cambio, y el enlace sigue funcionando.
- 🔚 Configurado de otra forma —activado con `user activate`, o con una contraseña asignada con `user reset` o un [enlace de restablecimiento](#reset-link)—, el administrador ya no espera: sus enlaces de configuración dejan de funcionar de forma definitiva, y este comando se detiene con el error que se indica abajo.
- 🌐 Al igual que con las [invitaciones](#invite), el enlace está completo cuando `LIBREFOLIO_PUBLIC_URL` está definida, y solo la ruta (`/setup#token=…`) cuando no lo está.
- 📧 El comando solo imprime el enlace: no envía ningún correo electrónico.
- ❌ Cuando ningún administrador está esperando su configuración, el comando se detiene con el error `No administrator account is waiting for its setup link` y sale con `1`. También lo hace cuando el administrador completa su configuración mientras el comando se ejecuta: el comando vuelve a comprobarlo justo antes de emitir el enlace y no da ninguno a una cuenta ya configurada.

### 📧 Cambiar la dirección de correo electrónico de una cuenta {: #set-email }

```bash
pipenv run ./dev.py user set-email <username> <new_email>
```

El mismo cambio que un nuevo correo electrónico en el [perfil](../user/settings/profile.md#email-change) del usuario, sin su contraseña: úsalo cuando alguien no pueda cambiar su dirección por su cuenta, o para separar dos cuentas que comparten una ([más abajo](#email-case-conflict)).

- 🔤 Una dirección pertenece a una sola cuenta, sin importar las mayúsculas: `Anna@example.com` y `anna@example.com` son la misma dirección. Solo las letras A a Z se consideran iguales de esta forma; las letras acentuadas no: `Émile@example.com` y `émile@example.com` son dos direcciones diferentes.
- 🚪 Una nueva dirección cierra la sesión de la cuenta en todos los dispositivos, cancela cualquier enlace de restablecimiento de contraseña que siga abierto y se registra como no verificada; la cuenta aún puede iniciar sesión. La propia dirección de la cuenta con otras mayúsculas es la misma dirección: solo cambia la forma de escribirla, no se cierra la sesión de nadie y sigue verificada.
- 👑 En el administrador inicial que aún espera su enlace de configuración, una nueva dirección también invalida ese enlace, que iba a la dirección anterior: la cuenta sigue esperando, y [`user setup-link`](#setup-link) le da uno nuevo. Mientras `LIBREFOLIO_ADMIN_EMAIL` esté definida, cada arranque del servidor vuelve a asignar esa dirección a la cuenta que espera: cambia también la variable, o el siguiente arranque restaurará la dirección anterior e invalidará también el nuevo enlace.
- ❌ Una dirección que ya tiene otra cuenta, sin importar las mayúsculas, se rechaza: el comando se detiene con el error `Email already registered` y sale con `1`, sin cambiar nada. También se rechaza una dirección que sea el nombre de usuario de otra cuenta, sin importar las mayúsculas: una cuenta creada antes de la versión 1.3 puede tener un `@` en su nombre de usuario ([Nombres de usuario con una @](users.md#usernames-with-at)), y una vez que ese nombre es la dirección de alguien, el inicio de sesión, que interpreta primero una dirección, ya no encontraría esa cuenta por su nombre. El propio nombre de usuario de la cuenta no es un obstáculo: puede convertirse en su dirección. Una dirección que no es válida (`Not an email address`) o un nombre de usuario desconocido (`User '<username>' not found`) también detienen el comando.
- 📮 Una nueva dirección también cancela cualquier enlace de cambio de correo electrónico que siga pendiente para la cuenta. No toca la contraseña.

### 👑 Conceder o retirar derechos de administrador

```bash
pipenv run ./dev.py user promote <username>
pipenv run ./dev.py user demote <username>
```

`demote` rechaza al último administrador activo: se detiene con el error `User '<username>' is the last active administrator: promote another user first` y sale con `1`. Una degradación cierra la sesión de la cuenta en todos los dispositivos.

### 🧭 Reiniciar las guías de un usuario {: #reset-onboarding }

```bash
# Every guide, the Welcome setup included
pipenv run ./dev.py user reset-onboarding <username>

# One guide only
pipenv run ./dev.py user reset-onboarding <username> --flow intro_tour
```

La próxima vez que el usuario abra LibreFolio, la configuración de bienvenida y las guías vuelven a empezar, como en su primera visita; sus datos y preferencias se mantienen tal como están. `--flow` reinicia una sola guía: `pipenv run ./dev.py user reset-onboarding --help` enumera los nombres, como `welcome`, `intro_tour` o `import_guide`.
`demote` también rechaza al [administrador inicial](configuration_accounts.md#initial-admin) que aún espera su enlace de configuración, que conserva su rol hasta entonces: se detiene con el error `User '<username>' is the initial administrator waiting for its setup: it keeps its role until then; deactivate it to cancel its setup link, or delete it from Settings › Administration › Users` y sale con `1`, sin cambiar nada. Para cancelar su enlace, ejecuta `user deactivate` (consulta «Restablecer una contraseña o bloquear una cuenta» más arriba); para eliminar la cuenta, bórrala en [Usuarios e invitaciones](users.md#delete), sin degradarla antes: la línea de comandos no elimina ninguna cuenta.

---

## 🗄️ Mantener la base de datos

### ⬆️ Aplicar migraciones {: #apply-migrations }

Cada arranque del servidor aplica por sí mismo las migraciones pendientes, así que rara vez necesitas esto. Para hacerlo a mano, **detén el servidor** primero: `db upgrade` se niega a ejecutarse mientras el servidor responde en el puerto configurado.

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

- 📄 Sin una ruta, los comandos usan la base de datos configurada. Una ruta nombra otro archivo SQLite: una relativa empieza en la raíz del proyecto, desde dondequiera que ejecutes el comando. El archivo debe existir, excepto para `db upgrade`, que lo crea (incluida la carpeta) y lo pone al día.
- 🐳 En Docker, la ruta está dentro del contenedor, donde `LibreFolio-data/` es `/app/backend/data/prod-docker` (la base de datos es `sqlite/app.db` dentro de ella). `db current`, `db check` y `db currencies` funcionan en el contenedor en ejecución: `docker compose exec librefolio python dev.py db current <path>`. `db upgrade` y `db downgrade` necesitan el servidor detenido (`docker compose stop librefolio`) y después un contenedor de un solo uso: `docker compose run --rm librefolio python dev.py db upgrade <path>` ([detalles](docker_advanced.md#docker-exec)).

### 🔤 Dos cuentas con la misma dirección de correo electrónico {: #email-case-conflict }

A partir de la versión 1.3, una dirección de correo electrónico pertenece a una sola cuenta, sin importar las mayúsculas. Una base de datos de una versión anterior puede contener dos cuentas cuyas direcciones solo difieren en las mayúsculas, como `Anna@example.com` y `anna@example.com`: entonces la actualización se detiene en la migración que comprueba esto, y el servidor no arranca. Las migraciones anteriores a ella siguen aplicadas, no se cambia ninguna cuenta, y el siguiente arranque continúa desde esa migración. El registro (o la salida de `db upgrade`) nombra las cuentas por id y nombre de usuario, nunca por dirección; un `;` separa un grupo de cuentas del siguiente:

```text
Email addresses must be unique regardless of case (release 1.3), and these accounts share one apart from upper and lower case: #3 'anna', #8 'anna_work'. Give all but one account of each group another address with …
```

LibreFolio nunca fusiona dos cuentas: asigna otra dirección a todas las cuentas de cada grupo menos a una con [`user set-email`](#set-email), y después vuelve a iniciar LibreFolio:

```bash
pipenv run ./dev.py user set-email <username> <new_email>
```

En Docker, el servidor es el proceso principal del contenedor, así que el contenedor no se mantiene en ejecución y no se puede confiar en `docker compose exec`: ejecuta el comando en un contenedor de un solo uso en su lugar.

```bash
docker compose stop librefolio
docker compose run --rm librefolio python dev.py user set-email <username> <new_email>
docker compose start librefolio
```

### 🩹 Reparaciones posteriores a las migraciones {: #post-migration-fixes }

Justo después de las migraciones, cada arranque también ejecuta las **reparaciones posteriores a las migraciones**: reparaciones que una migración no puede hacer. Normalmente no hay nada que hacer. El registro (la salida del servidor, que también se guarda en `logs/`) puede mostrar:

- ✅ `Post-migration fixes applied and verified`: se hizo una reparación. En una base de datos grande, ese arranque tarda más, pero solo una vez.
- ⚠️ `Post-migration fix failed`: la base de datos se dejó como estaba y el servidor arrancó con normalidad. La advertencia indica el error y la copia de la base de datos que se conserva junto a ella hasta que la borres, como `app.db.pre-autoincrement-20261008T101500Z.bak`. La reparación se vuelve a intentar en el siguiente arranque.
- 🩺 `Post-migration fixes skipped`: no se pudo hacer la copia, o la base de datos no supera la comprobación de integridad de SQLite. No se cambió nada.
- 🔗 `Foreign key violations already in the database, left as they are`: la base de datos contiene referencias a filas que ya no existen, enumeradas en la advertencia. Las reparaciones las dejan intactas y aun así se ejecutan: una reparación solo falla por una referencia rota que ella misma añadiría.

El archivo vacío `app.db.post-migration.lock`, junto a la base de datos, hace que las ejecuciones se turnen cuando varios procesos worker arrancan a la vez: déjalo en su sitio.

La primera reparación, **`autoincrement`**, asegura que el id de cualquier usuario, bróker, activo, transacción, ruta de conversión FX o evento de activo que se elimine nunca se asigne a uno nuevo. Al convertir una base de datos, elimina las carpetas de informes de los brókers que ya no existen, para que un nuevo bróker no pueda heredarlas.

La segunda reparación, **`orphan_pair_halves`**, repara, una vez, las transferencias que una eliminación anterior de un bróker dejó sin su otra mitad en los brókers que permanecen:

- 📈 Los valores recibidos del bróker eliminado se convierten en una posición de apertura a su coste de transferencia, a partir de la fecha de transferencia. El capital de ese bróker los cuenta entonces a ese coste en lugar de a su valor de mercado al llegar, por lo que su ganancia también cuenta lo que ganaron antes de la transferencia. Cuando no se registró ningún coste, se quedan sin uno y la aplicación informa de una adquisición sin coste de compra: introduce el coste en la transacción.
- 💶 Las transferencias de fondos con el bróker eliminado se convierten en depósitos o retiros: el capital y la ganancia no cambian.
- 📤 Valores enviados **al** bróker eliminado: justo después de las reparaciones, en el mismo arranque, cada una de estas transferencias se convierte en un ajuste que saca los valores del bróker emisor. Ese ajuste no tiene valor: los valores solo disminuyen la cantidad, y su coste cuenta como una pérdida realizada en ese bróker. El registro tiene una línea para cada una (`Lone transfer leg converted to an ADJUSTMENT-out without a value`). En una base de datos que no supera la comprobación rápida de SQLite, todas se dejan como están (`Lone transfer legs left as they are: the database failed its quick check`). Si falla todo el paso (`Lone transfer legs could not be converted; starting normally`), no se cambia nada y el servidor arranca de todos modos.

La reparación **`event_types`** repara, una vez, los eventos de activo guardados con un tipo que LibreFolio no conoce, como `dividend` o `dividendo` escritos a mano en un archivo CSV. Hasta ahora, un evento así hacía que fallara la carga de toda la lista de eventos de ese activo, por lo que no se mostraba ninguno:

- ✅ Un tipo que solo difiere en mayúsculas/minúsculas o espacios (`dividend`, ` Split `) se corrige.
- 🗑️ Un evento cuyo tipo sigue siendo desconocido se elimina. Una transacción vinculada a él permanece, sin su evento vinculado: vuelve a vincularla al evento correcto si lo necesitas.

??? tip "⌨️ Ejecutar las reparaciones a mano — para previsualizarlas o reintentar una fallida"

    **Detén el servidor** primero (el script no lo comprueba), y después ejecuta desde la raíz del proyecto:

    ```bash
    # Preview: report what would be fixed, change nothing
    pipenv run python -m backend.app.db.post_migration --dry-run

    # Apply the fixes
    pipenv run python -m backend.app.db.post_migration
    ```

    El script imprime cada reparación como `clean` (nada que hacer), `would_apply` (simulación), `applied` o `failed`, con las carpetas de brókers huérfanas, una copia conservada y cualquier error; después, una línea por cada transferencia de valores enviada a un bróker eliminado (`Lone transfer leg …`), y sale con `1` cuando algo falla. `--db PATH` y `--data-dir PATH` lo apuntan a otra base de datos o directorio de datos.

    Para ver qué cambiará `orphan_pair_halves` en tu base de datos, previsualízalo antes del primer arranque de la nueva versión: `--dry-run` imprime `Fix orphan_pair_halves: would_apply` cuando hay algo que reparar, y una advertencia enumera las transacciones por id, agrupadas por conversión (como `TRANSFER->ADJUSTMENT`), con las que se quedarán sin coste y las transferencias de valores enviadas a un bróker eliminado. Esas transferencias reciben una línea cada una después de las reparaciones (`would become an ADJUSTMENT-out without a value`). El script también imprime, en la consola, lo que registraría el servidor: la advertencia y, en una ejecución real, una línea por cada transacción modificada (con `LOG_LEVEL` en `INFO`, el valor predeterminado). No escribe ningún archivo de registro: conserva su salida si quieres tener constancia de una reparación hecha a mano.

🔗 Cómo funcionan las reparaciones por dentro: [Esquema de la base de datos — Reparaciones posteriores a las migraciones](../developer/architecture/database/index.md#post-migration-fixes).

### 💱 Códigos de divisa que no son códigos ISO {: #currency-codes }

A partir de la versión 1.3, LibreFolio guarda una divisa solo como un código alfabético ISO 4217, como `EUR` o `USD`. Las versiones anteriores también aceptaban el nombre de una divisa o su código numérico, y lo guardaban tal como se escribía: `Euro`, `978`. Ese valor todavía se lee, pero se rechaza una edición que vuelva a guardar su fila hasta que se corrija su código, y sus importes nunca coinciden con los del código ISO: `978` y `EUR` forman dos saldos. Una copia de seguridad restaurada puede traer de vuelta esos valores.

Poco después de cada arranque, el registro advierte cuando la base de datos contiene alguno, y LibreFolio no los cambia por sí mismo:

```text
Stored currency codes that are not ISO 4217 codes: an edit of their rows is refused until they are corrected (./dev.py db currencies lists them)
```

`db currencies` los enumera, sin cambiar nada:

```bash
# Where each value is stored, how many rows hold it, and the ISO code it stands for
pipenv run ./dev.py db currencies

# Another database file, such as a copy
pipenv run ./dev.py db currencies /path/to/copy/app.db
```

- 🔎 Cada línea indica el lugar (`transactions.currency`, `assets.currency`, los pasos de una ruta FX, la configuración de un proveedor, la divisa base de un usuario…), el valor, cuántas filas lo contienen y el código ISO que representa: `978` es `EUR`, `US DOLLAR` es `USD`.
- ➖ Un guion significa que no hay un único código: un nombre que comparten dos divisas (`Bolívar Soberano`: `VED` o `VES`), un valor que no es una divisa, o un código que cuenta céntimos en lugar de unidades (`GBX`, `ZAC`, `ILA`), que nunca debe renombrarse sin más.
- 🔤 Un código en minúsculas o con espacios, como `eur`, también se enumera: la divisa correcta, en una forma que las comparaciones exactas no detectan.
- 🧱 Un valor guardado como bytes sin procesar en lugar de texto, o como texto que no es UTF-8 válido, algo que solo se encuentra en una base de datos dañada o hecha a mano, se enumera en la notación de SQLite, como `X'455552'`, con un guion: nunca es un código.
- 🚦 El comando sale con `0` cuando todos los códigos son códigos ISO, `1` cuando enumera algunos y `2` cuando no puede leer la base de datos.
- 🐳 En Docker: `docker compose exec librefolio python dev.py db currencies`.

### 🔧 Añadir la configuración global faltante

```bash
pipenv run ./dev.py user init-settings
```

Cada arranque añade la [Configuración global](settings.md) que falte con sus valores predeterminados; este comando hace lo mismo sin iniciar el servidor y nunca cambia un valor ya establecido.

### 🧹 Restablecer la base de datos

```bash
pipenv run ./dev.py db create-clean
```

!!! warning "Se pierden todos los datos"

    `db create-clean` elimina la base de datos y crea una vacía. Como `db upgrade`, se niega a ejecutarse mientras el servidor está activo. Los archivos subidos y los informes del bróker permanecen en el disco: consulta [Inicialización y restablecimiento de la base de datos](host_installation.md#database-reset).

---

## 📋 Árbol completo de comandos

```bash
# Every command, by category
pipenv run ./dev.py --help

# The options of one command
pipenv run ./dev.py server --help
```

??? info "👩‍💻 Comandos para desarrollo y documentación"

    - **Frontend**: `pipenv run ./dev.py front build`, `front dev`, `front check` — consulta [Desarrollo del frontend](../developer/frontend/index.md)
    - **Pruebas**: `pipenv run ./dev.py test all` — consulta [Recorrido por las pruebas](../developer/test-walkthrough/index.md)
    - **Cliente de API**: `pipenv run ./dev.py api sync` — consulta [Resumen de la API](../developer/api/overview.md)
    - **i18n**: `pipenv run ./dev.py i18n audit` — consulta [Internacionalización](../developer/frontend/i18n.md)
    - **Documentación**: `pipenv run ./dev.py mkdocs deploy` publica esta documentación en GitHub Pages; `pipenv run ./dev.py mkdocs gallery` regenera sus capturas de pantalla con Playwright en un servidor de pruebas (`--no-populate` conserva los datos de prueba actuales).

    El conjunto completo de herramientas para desarrolladores está en la [Guía del flujo de trabajo para desarrolladores](../developer/dev_workflow.md).

---

## 🔗 Relacionado

- 📄 **[Herramientas de administración de la CLI: copias de seguridad](cli_backup.md)** — Hacer una copia de seguridad de la instancia
