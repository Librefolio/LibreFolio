# 🛡️ Manual del Administrador

Este manual está dirigido a administradores de sistemas y usuarios avanzados que necesitan realizar tareas de mantenimiento, gestionar usuarios o interactuar con el sistema mediante la línea de comandos.

## 📖 Descripción general

La mayoría de las tareas administrativas y de mantenimiento se gestionan mediante la interfaz principal de línea de comandos o se configuran a través de variables de entorno.

---

## 📚 Guías

La documentación está organizada en tres áreas principales:

### 🐳 Despliegue y Exposición
- 📦 **[Instalación en el Host](host_installation.md)**: Configuración manual utilizando Python, Node.js y Pipenv directamente en la máquina host.
- 🐳 **[Docker Avanzado](docker_advanced.md)**: Despliegue en contenedores mediante Docker Compose, enlaces de volúmenes y configuración de propiedad de GID/UID de usuario.
- 🌐 **[Exposición Segura](service_exposure.md)**: Exponga de forma segura su instancia privada de LibreFolio a través de internet.

### ⚙️ Configuración del Sistema
- 📝 **[Variables de Entorno](configuration.md)**: Lista completa de variables `.env` compatibles (`PORT`, `JWT_SECRET`, `LIBREFOLIO_DATA_DIR`, etc.) y precedencia en la resolución de variables.
- ⚙️ **[Configuración Global](settings.md)**: Permite configurar los ajustes de ejecución globales del sistema (TTL de sesión, límites de subida, intervalos de sincronización de datos de mercado).

### 🧹 Mantenimiento y Operaciones
- 🛠️ **[Herramientas CLI de Administración](cli_tools.md)**: Cómo utilizar el script `dev.py` para tareas administrativas (gestión de usuarios, actualizaciones de base de datos).
- 📂 **[Estructura del Sistema de Archivos](filesystem.md)**: Detalles sobre dónde se almacenan las bases de datos, los registros, las subidas y las carpetas temporales, y cómo realizar copias de seguridad.

---

## 🔔 Notificaciones de Actualización {: #update-notifications }

Después de cada inicio de sesión, el navegador de un **administrador** consulta la API de GitHub Releases en busca de una versión **estable** más reciente de LibreFolio (los borradores y las versiones preliminares nunca se consideran). Para que la comprobación pase desapercibida:

- La comprobación se ejecuta **como máximo una vez por hora** — el último resultado se almacena en caché en el almacenamiento local del navegador.
- La ventana modal solo aparece cuando la versión es **realmente instalable**: la comprobación verifica además que la imagen Docker de esa etiqueta exista en el registro, por lo que una versión cuya compilación aún está en curso no se anuncia todavía.
- Las instalaciones autoalojadas sin acceso a internet simplemente fallan silenciosamente al obtener los datos: **sin errores, sin banners**.

Cuando existe una versión estable más reciente, aparece un **modal de actualización disponible** que muestra las versiones actual y más reciente una al lado de la otra, con enlaces a la **[guía de actualización](../user/installation.md#updating)** y a la página de lanzamientos de GitHub. Hay dos formas de descartarlo:

- **«Más tarde»** — el modal se cierra y volverá a mostrarse en el próximo inicio de sesión.
- **«Omitir esta versión»** — el modal no volverá a avisar sobre esa versión específica (una versión futura más reciente sí se anunciará).

Los usuarios no administradores nunca son consultados al iniciar sesión. Si un usuario no administrador comprueba manualmente las actualizaciones desde el [modal de registro de cambios](../user/settings/about.md#changelog-modal) y existe una versión más reciente, verá en su lugar un diálogo que enumera los administradores de la instancia (con direcciones de correo electrónico cuando estén disponibles) para que sepa a quién solicitar la actualización.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="update-available-modal" alt="Modal de actualización disponible con la versión actual y la más reciente">
</div>

---

## 🔐 Autenticación y Persistencia de Sesión

LibreFolio utiliza **JWT (JSON Web Tokens)** para la autenticación de usuarios. Por defecto:

- Si la variable de entorno **`JWT_SECRET`** se deja vacía en su archivo `.env`, el servidor genera un secreto de firma aleatorio al iniciarse. Esto proporciona la máxima seguridad, pero las sesiones de usuario se perderán si el servidor se reinicia.
- Para mantener las sesiones entre reinicios del servidor (o al ejecutar varias instancias independientes del servidor detrás de un balanceador de carga), defina una clave **`JWT_SECRET`** estable. Tenga en cuenta que varios workers de uvicorn generados en el mismo host compartirán automáticamente el secreto generado por el proceso padre, lo que significa que la persistencia de sesión se mantiene entre los workers incluso cuando `JWT_SECRET` se deja vacía.

Para más detalles técnicos, consulte la página [Arquitectura de Seguridad](../developer/architecture/security.md), orientada a desarrolladores.
