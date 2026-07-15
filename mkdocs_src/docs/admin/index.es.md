# 🛡️ Manual de Admin

Este manual es para administradores de sistemas y usuarios avanzados que necesitan realizar mantenimiento, gestionar usuarios o interactuar con el sistema a través de la línea de comandos.

## 📖 Descripción General

La mayoría de las tareas de administración y mantenimiento se manejan a través de la interfaz de línea de comandos principal o se configuran mediante variables de entorno.

---

## 📚 Guías

La documentación está organizada en tres áreas principales:

### 🐳 Despliegue y Exposición
- 📦 **[Instalación en Host](host_installation.md)**: Configuración manual utilizando Python, Node.js y Pipenv directamente en la máquina host.
- 🐳 **[Docker Avanzado](docker_advanced.md)**: Despliegue en contenedores usando Docker Compose, enlaces de volumen y configuración de propiedad GID/UID del usuario.
- 🌐 **[Exponer en Seguridad](service_exposure.md)**: Exponga de forma segura su instancia privada de LibreFolio a través de Internet.

### ⚙️ Configuración del Sistema
- 📝 **[Variables de Entorno](configuration.md)**: Lista completa de las variables `.env` soportadas (`PORT`, `JWT_SECRET`, `LIBREFOLIO_DATA_DIR`, etc.) y orden de precedencia de resolución.
- ⚙️ **[Configuración Global](settings.md)**: Configure los ajustes de tiempo de ejecución de todo el sistema (TTL de la sesión, límites de subida, intervalos de sincronización de datos de mercado).

### 🧹 Mantenimiento y Operaciones
- 🛠️ **[Herramientas CLI de Admin](cli_tools.md)**: Cómo utilizar el script `dev.py` para tareas administrativas (gestión de usuarios, actualizaciones de bases de datos).
- 📂 **[Estructura del Sistema de Archivos](filesystem.md)**: Detalles sobre dónde se almacenan las bases de datos, los logs, las subidas y las carpetas temporales, y cómo realizar copias de seguridad.

---

## 🔐 Autenticación y Persistencia de Sesiones

LibreFolio utiliza **JWT (JSON Web Tokens)** para la autenticación de usuarios. Por defecto:
- Si la variable de entorno **`JWT_SECRET`** se deja vacía en su archivo `.env`, el servidor genera una clave secreta de firma aleatoria al iniciar. Esto proporciona la máxima seguridad, pero las sesiones de usuario se perderán si el servidor se reinicia.
- Para mantener las sesiones de usuario entre reinicios del servidor (o al ejecutar varias instancias independientes del servidor detrás de un balanceador de carga), defina una clave **`JWT_SECRET`** estable. Tenga en cuenta que los múltiples procesos de trabajo de uvicorn iniciados en el mismo host compartirán automáticamente el secreto generado por el proceso principal, lo que significa que la persistencia de la sesión entre procesos de trabajo se mantiene incluso cuando `JWT_SECRET` se deja vacía.

Para obtener detalles técnicos, consulte la página dedicada a la [Seguridad y Autenticación](../developer/architecture/security.md) en el manual del desarrollador.
