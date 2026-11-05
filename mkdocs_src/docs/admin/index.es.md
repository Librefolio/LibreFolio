# 🛡️ Manual de administración

Este manual está dirigido a las personas que instalan y ejecutan LibreFolio. La mayor parte de la administración se realiza desde la línea de comandos, mediante variables de entorno o en las pestañas **Configuración › Administración** de la aplicación.

---

## 📚 Guías

### 🐳 Despliegue y exposición
- 📦 **[Instalación en el host](host_installation.md)**: Configuración manual con Python, Node.js y Pipenv directamente en la máquina host.
- 🐳 **[Docker avanzado](docker_advanced.md)**: Despliegue en contenedores con Docker Compose, vinculaciones de volúmenes y configuración de la propiedad de usuario mediante GID/UID.
- 🌐 **[Exposición segura](service_exposure.md)**: Expón de forma segura tu instancia privada de LibreFolio con Tailscale, sin abrir ningún puerto del router: por qué es mejor que el reenvío de puertos, y los niveles privados: una VPN para tus propios dispositivos o un enrutador de subred para toda tu red doméstica.
    - 🌍 **[Exposición segura: acceso público con Funnel](service_exposure_funnel.md)**: Una dirección HTTPS pública con Tailscale Funnel: habilitar Funnel y las ACLs, una dirección para LibreFolio o una para cada servicio con Docker.
- 🔍 **[Comprobación de la seguridad de la conexión](connection_checks.md)**: Verifica que tus usuarios se conecten de forma segura: la lista de comprobación, el indicador, la vista del servidor y la cookie de sesión, y qué hacer cuando falla una comprobación.
    - 🧰 **[Comprobación de la seguridad de la conexión: detrás de un proxy inverso](connection_proxy.md)**: Ejecuta LibreFolio detrás de Nginx, Caddy, Traefik o Tailscale: las cabeceras que se deben enviar, el proxy en el que confía LibreFolio y la dirección del visitante.

### ⚙️ Configuración del sistema
- 📝 **[Variables de entorno](configuration.md)**: Crea el archivo `.env` y consulta las principales variables compatibles (`PORT`, `JWT_SECRET`, `LIBREFOLIO_DATA_DIR`, etc.), con la precedencia que determina qué valor prevalece.
    - 🔐 **[Configuración: secretos y configuración de plugins](configuration_secrets.md)**: Los secretos y cómo leerlos desde archivos como los secretos de Docker, la clave de la instancia y la configuración y las claves de API de los plugins.
    - 🛡️ **[Configuración: comprobaciones y protecciones](configuration_security.md)**: Qué comprueba LibreFolio al iniciarse, la Content-Security-Policy y la protección de marcos, y cómo se detiene el servidor.
    - 👥 **[Configuración: cuentas y búsqueda de activos](configuration_accounts.md)**: Quién puede registrarse, los límites en las cuentas y en los inicios de sesión fallidos, el administrador inicial y el orden de los proveedores de precios en la búsqueda de activos.
- 📧 **[Correo electrónico](email.md)**: Correo electrónico SMTP opcional: las variables, ejemplos para los servidores habituales y la pestaña **Correo electrónico** de Configuración › Administración, con su correo de prueba.
    - 📬 **[Correo electrónico: enlaces y mensajes](email_flows.md)**: Los correos con un enlace, las invitaciones y los restablecimientos de contraseña, las contraseñas olvidadas y sus límites, la verificación de correo electrónico y el aviso de cambio de correo.
    - 🛠️ **[Correo electrónico: cuando no funciona](email_troubleshooting.md)**: Los errores, lo que dice el registro y las notas de seguridad de la configuración de SMTP.
- ⚙️ **[Configuración global](settings.md)**: Establece la configuración de ejecución para todo el sistema (TTL de sesión, límites de subida, intervalos de sincronización de datos de mercado), oriéntate en las pestañas **Administración** de Configuración y consulta las comprobaciones de **Seguridad** de la instancia.
- 👥 **[Usuarios e invitaciones](users.md)**: Gestiona las cuentas de la instancia desde la pestaña **Usuarios** de la aplicación: invitaciones, enlaces para restablecer contraseñas, derechos de administrador, desactivación y eliminación.

### 🧹 Mantenimiento y operaciones
- 🛠️ **[Herramientas de administración de CLI](cli_tools.md)**: Cómo usar el script `dev.py` para tareas administrativas (gestión de usuarios, actualizaciones de la base de datos, copias de seguridad de la instancia).
- 💾 **[Copia de seguridad, restauración y traslado](backup_restore.md)**: Un único archivo comprimido con toda la instancia: créalo desde Configuración › Administración › Copia de seguridad o desde la línea de comandos, compruébalo, restáuralo y traslada LibreFolio entre dos instalaciones.
- 📂 **[Estructura del sistema de archivos](filesystem.md)**: Detalles sobre dónde se almacenan las bases de datos, los registros, los archivos subidos y las carpetas temporales, y cómo realizar copias de seguridad.

---

## 🔔 Notificaciones de actualización {: #update-notifications }

Cuando un administrador inicia sesión, LibreFolio comprueba en GitHub si hay una versión **estable** más reciente. Si la hay, la ventana **Nueva versión disponible** muestra tu versión y la más reciente una al lado de la otra, con un enlace **Cómo actualizar** a la [guía de actualización](../user/installation.md#updating) y un enlace **Notas de la versión en GitHub**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="update-available-modal" alt="Ventana modal de actualización disponible con la versión actual y la más reciente">
</div>

- **Recordármelo más tarde** cierra la ventana hasta un inicio de sesión posterior.
- **Omitir esta versión** detiene el aviso automático para esa versión; cuando aparezca una versión aún más reciente, se volverá a anunciar.
- Una versión solo se anuncia una vez que su imagen de Docker se puede descargar, y la ventana espera hasta que no haya ninguna otra ventana o guía abierta.
- Sin acceso a internet, la comprobación automática falla en silencio: sin errores ni banner.
- Para comprobarlo de inmediato, usa **Buscar actualizaciones** en el [registro de cambios](../user/settings/about.md#changelog-modal): informa de errores y también de las versiones que omitiste.

??? note "👥 Otros usuarios — cuando alguien que no es administrador comprueba"

    Para los usuarios que no son administradores, no se ejecuta ninguna comprobación al iniciar sesión. Si uno de ellos ejecuta
    **Buscar actualizaciones** y existe una versión más reciente, el diálogo
    **Actualización disponible — contacta con un administrador** muestra una lista de los administradores, con sus
    direcciones de correo electrónico cuando estén disponibles, para que sepan a quién preguntar.

---

## 🔐 Mantener a los usuarios con la sesión iniciada tras un reinicio {: #session-persistence }

LibreFolio firma cada sesión de acceso con una clave secreta, `JWT_SECRET`.

- **Sin definir** (valor predeterminado): se genera una nueva clave aleatoria en cada arranque, por lo que todos deben volver a iniciar sesión después de un reinicio o una actualización.
- **Definida**: las sesiones sobreviven a los reinicios. Defínela también si varios servidores LibreFolio independientes comparten los mismos usuarios detrás de un balanceador de carga.

### 🔑 1. Generar una clave

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

¿No tienes Python en el host? Ejecútalo dentro del contenedor:

```bash
docker exec librefolio python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 📝 2. Añádela a `.env` y reinicia

```bash
JWT_SECRET=paste-the-generated-value-here
```

Reinicia LibreFolio (con Docker Compose: `docker compose up -d`). Mantén la clave en privado: cualquiera que la conozca puede falsificar una sesión.

??? tip "🐳 Mantén la clave fuera de `.env` — `JWT_SECRET_FILE`"

    Guarda la clave en un archivo, como un secreto de Docker, y define `JWT_SECRET_FILE` con su ruta en lugar de
    `JWT_SECRET`, por ejemplo `JWT_SECRET_FILE=/run/secrets/jwt_secret`. Las reglas y un ejemplo de Docker
    Compose están en [Secretos](configuration_secrets.md#secrets).

Los procesos worker de un único `./dev.py server --workers …` comparten una sola clave por su cuenta. La duración de una sesión se configura con la **Duración de la sesión** en [Configuración global](settings.md). Para más detalles, consulta la página para desarrolladores [Arquitectura de seguridad](../developer/architecture/security.md).
