# 🛡️ Manual de administración

Para las personas que instalan y ejecutan LibreFolio. Casi todo se hace en uno de tres lugares: desde la **línea de comandos**, en el archivo **`.env`** (variables de entorno) o en las pestañas **Configuración › Administración** de la aplicación.

---

## 📚 Guías

### 🐳 Despliegue y exposición
- 📦 **[Instalación en el host](host_installation.md)**: Python, Node.js y Pipenv directamente en la máquina host.
- 🐳 **[Docker avanzado](docker_advanced.md)**: Docker Compose, volúmenes y propiedad de los archivos mediante GID/UID.
- 🌐 **[Exposición segura](service_exposure.md)**: tu instancia privada con Tailscale, sin abrir ningún puerto del router: una VPN para tus propios dispositivos o un enrutador de subred para toda tu red doméstica.
    - 🌍 **[Exposición segura: acceso público con Funnel](service_exposure_funnel.md)**: una dirección HTTPS pública con Tailscale Funnel, una para LibreFolio o una para cada servicio con Docker.
- 🔍 **[Comprobación de la seguridad de la conexión](connection_checks.md)**: la lista de comprobación, el indicador, la vista del servidor y la cookie de sesión; qué hacer cuando falla una comprobación.
    - 🧰 **[Comprobación de la seguridad de la conexión: detrás de un proxy inverso](connection_proxy.md)**: Nginx, Caddy, Traefik o Tailscale: las cabeceras que se deben enviar, el proxy de confianza y la dirección del visitante.

### ⚙️ Configuración del sistema
- 📝 **[Variables de entorno](configuration.md)**: el archivo `.env` y las variables principales (`PORT`, `JWT_SECRET`, `LIBREFOLIO_DATA_DIR`, etc.), con la precedencia entre los valores.
    - 🔐 **[Configuración: secretos y ajustes de plugins](configuration_secrets.md)**: secretos leídos desde archivos (como los secretos de Docker), la clave de la instancia, los ajustes y las claves de API de los plugins.
    - 🛡️ **[Configuración: comprobaciones y protecciones](configuration_security.md)**: las comprobaciones al iniciar, la Content-Security-Policy, la protección de marcos y cómo se detiene el servidor.
    - 👥 **[Configuración: cuentas y búsqueda de activos](configuration_accounts.md)**: quién puede registrarse, límites en las cuentas y en los inicios de sesión fallidos, el administrador inicial, el orden de los proveedores de precios.
- 📧 **[Correo electrónico](email.md)**: SMTP opcional: las variables, ejemplos para los servidores más habituales, la pestaña **Correo** de Configuración › Administración y el correo de prueba.
    - 📬 **[Correo electrónico: enlaces y mensajes](email_flows.md)**: invitaciones y restablecimientos de contraseña, contraseñas olvidadas y sus límites, verificación del correo, el aviso de un cambio de correo.
    - 🛠️ **[Correo electrónico: cuando no funciona](email_troubleshooting.md)**: los errores, lo que dice el registro, notas de seguridad de SMTP.
- ⚙️ **[Configuración global](settings.md)**: los ajustes de ejecución (TTL de sesión, límites de subida, intervalos de sincronización de datos de mercado), las pestañas de **Administración** y las comprobaciones de **Seguridad** de la instancia.
- 👥 **[Usuarios e invitaciones](users.md)**: la pestaña **Usuarios** de la aplicación: invitaciones, enlaces de restablecimiento de contraseña, derechos de administrador, desactivación y eliminación.

### 🧹 Mantenimiento y operaciones
- 🛠️ **[Herramientas de administración de CLI](cli_tools.md)**: el script `dev.py` para la gestión de usuarios, las actualizaciones de la base de datos y las copias de seguridad de la instancia.
- 💾 **[Copia de seguridad, restauración y traslado](backup_restore.md)**: un único archivo con toda la instancia, desde Configuración › Administración › Copia de seguridad o desde la línea de comandos: créalo, compruébalo, restáuralo y traslada LibreFolio entre dos instalaciones.
- 📂 **[Estructura del sistema de archivos](filesystem.md)**: dónde se guardan las bases de datos, los registros, los archivos subidos y las carpetas temporales, y cómo hacer copias de seguridad.

---

## 🔔 Notificaciones de actualización {: #update-notifications }

Cuando un administrador inicia sesión, LibreFolio comprueba en GitHub si hay una versión **estable** más reciente. Si la hay, la ventana **Nueva versión disponible** muestra tu versión y la más reciente una al lado de la otra, con los enlaces **Cómo actualizar** ([guía de actualización](../user/installation.md#updating)) y **Notas de la versión en GitHub**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="update-available-modal" alt="Ventana modal de actualización disponible con la versión actual y la más reciente">
</div>

| Botón | Efecto |
| --- | --- |
| **Recordármelo más tarde** | Cierra la ventana hasta un inicio de sesión posterior. |
| **Omitir esta versión** | Sin aviso automático para esa versión; se anunciará una aún más reciente. |

- Una versión solo se anuncia cuando su imagen de Docker se puede descargar; la ventana espera hasta que no haya ninguna otra ventana o guía abierta.
- Sin acceso a internet, la comprobación falla en silencio: sin error, sin banner.
- Para comprobarlo de inmediato: **Buscar actualizaciones** en el [registro de cambios](../user/settings/about.md#changelog-modal). Informa de los errores, y también de las versiones omitidas.

??? note "👥 Otros usuarios — cuando comprueba alguien que no es administrador"

    Para los usuarios que no son administradores, no se ejecuta ninguna comprobación al iniciar sesión. Si uno de ellos ejecuta **Buscar actualizaciones** y existe una versión más reciente, la ventana **Actualización disponible — contacta a un administrador** muestra la lista de administradores, con sus direcciones de correo electrónico cuando están disponibles.

---

## 🔐 Mantener a los usuarios con la sesión iniciada tras un reinicio {: #session-persistence }

`JWT_SECRET` es la clave que firma cada sesión de acceso.

- **Sin definir** (el valor predeterminado): una clave aleatoria nueva en cada arranque, así que todos vuelven a iniciar sesión tras un reinicio o una actualización.
- **Definida**: las sesiones sobreviven a los reinicios. Defínela también cuando varios servidores LibreFolio comparten los mismos usuarios detrás de un balanceador de carga.

Para definirla:

1. Genera una clave. **Desde una terminal**, en el host:

    ```bash
    python3 -c "import secrets; print(secrets.token_urlsafe(64))"
    ```

    Obtienes una cadena aleatoria para copiar. Sin Python en el host, ejecuta el comando **en el contenedor**:

    ```bash
    docker exec librefolio python -c "import secrets; print(secrets.token_urlsafe(64))"
    ```

2. Añádela **al archivo `.env` de LibreFolio**:

    ```bash
    JWT_SECRET=paste-the-generated-value-here
    ```

3. Reinicia LibreFolio. Con Docker Compose, ejecuta `docker compose up -d`.

    A partir de entonces, un reinicio no cierra la sesión de nadie.

!!! warning "🔒 Mantén la clave en secreto"

    Quien la conozca puede falsificar una sesión.

??? tip "🐳 Mantén la clave fuera de `.env` — `JWT_SECRET_FILE`"

    Guarda la clave en un archivo, como un secreto de Docker, y define `JWT_SECRET_FILE` con su ruta en lugar de `JWT_SECRET`: por ejemplo `JWT_SECRET_FILE=/run/secrets/jwt_secret`. Las reglas y un ejemplo de Docker Compose están en [Secretos](configuration_secrets.md#secrets).

- Los workers de un único `./dev.py server --workers …` comparten una sola clave por su cuenta.
- Cuánto dura una sesión lo determina la **Duración de Sesión** en [Configuración global](settings.md).
- Detalles para desarrolladores: [Arquitectura de seguridad](../developer/architecture/security.md).
