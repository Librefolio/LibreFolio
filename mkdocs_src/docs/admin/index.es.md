# 🛡️ Manual de administración

Este manual está dirigido a las personas que instalan y ejecutan LibreFolio. La mayor parte de la
administración se realiza desde la línea de comandos, mediante variables de entorno o en la
pestaña **Administración** de configuración de la aplicación.

---

## 📚 Guías

### 🐳 Despliegue y exposición
- 📦 **[Instalación en el host](host_installation.md)**: Configuración manual usando Python, Node.js y Pipenv directamente en la máquina host.
- 🐳 **[Docker avanzado](docker_advanced.md)**: Despliegue en contenedores usando Docker Compose, montajes de volumen y configuración de titularidad de GID/UID del usuario.
- 🌐 **[Exponer de forma segura](service_exposure.md)**: Expón de forma segura tu instancia privada de LibreFolio a través de internet.
- 🔍 **[Comprobar la seguridad de la conexión](connection_checks.md)**: Comprueba que tus usuarios se conectan de forma segura, y corrige la cookie de sesión o el proxy inverso cuando no es así.
- 💤 **[Suspensión y activación](sleep_wake.md)**: Una máquina de Fly.io sin uso se suspende sola y se reactiva a una hora programada: un panel de alojamiento o una tarea cron actualiza los precios y los tipos de cambio.

### ⚙️ Configuración del sistema
- 📝 **[Variables de entorno](configuration.md)**: Lista completa de variables `.env` soportadas (`PORT`, `JWT_SECRET`, `LIBREFOLIO_DATA_DIR`, etc.) y precedencia de resolución de variables.
- ⚙️ **[Configuración global](settings.md)**: Configura la configuración de tiempo de ejecución para todo el sistema (TTL de sesión, límites de carga, intervalos de sincronización de datos de mercado).

### 🧹 Mantenimiento y operaciones
- 🛠️ **[Herramientas de administración de CLI](cli_tools.md)**: Cómo usar el script `dev.py` para tareas administrativas (gestión de usuarios, actualizaciones de base de datos).
- 📂 **[Estructura del sistema de archivos](filesystem.md)**: Detalles sobre dónde se almacenan las bases de datos, los logs, las cargas y las carpetas temporales, y cómo realizar copias de seguridad.

---

## 🔔 Notificaciones de actualización {: #update-notifications }

Cuando un administrador inicia sesión, LibreFolio comprueba en GitHub si hay una versión
**estable** más reciente. Si la hay, la ventana **Nueva versión disponible** muestra tu versión y
la más reciente lado a lado, con un enlace **Cómo actualizar** a la
[guía de actualización](../user/installation.md#updating) y un enlace
**Notas de la versión en GitHub**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="update-available-modal" alt="Modal de actualización disponible con la versión actual y la más reciente">
</div>

- **Recordármelo más tarde** cierra la ventana hasta un inicio de sesión posterior.
- **Omitir esta versión** detiene el aviso automático para esa versión; se volverá a anunciar una
  más reciente.
- Una versión se anuncia solo cuando su imagen de Docker se puede descargar, y la ventana espera
  hasta que no haya ninguna otra ventana o guía abierta.
- Sin acceso a internet, la comprobación automática falla silenciosamente: sin error, sin banner.
- Para comprobarlo de inmediato, usa **Buscar actualizaciones** en el
  [registro de cambios](../user/settings/about.md#changelog-modal): informa de errores y también
  de las versiones que omitiste.

??? note "👥 Otros usuarios — cuando alguien que no es administrador comprueba"

    Para los usuarios que no son administradores, no se ejecuta ninguna comprobación al iniciar sesión. Si uno de ellos ejecuta
    **Buscar actualizaciones** y existe una versión más reciente, el
    diálogo **Actualización disponible — contacta a un administrador** muestra una lista de los administradores, con sus
    direcciones de correo electrónico cuando estén disponibles, para que sepan a quién preguntar.

---

## 🔐 Mantener a los usuarios con la sesión iniciada después de un reinicio {: #session-persistence }

LibreFolio firma cada sesión con una clave secreta, `JWT_SECRET`.

- **No establecida** (predeterminado): se genera una nueva clave aleatoria en cada inicio, por lo
  que todos deben iniciar sesión de nuevo tras un reinicio o una actualización.
- **Establecida**: las sesiones sobreviven a los reinicios. Configúrala también si varios
  servidores LibreFolio independientes comparten los mismos usuarios detrás de un balanceador de
  carga.

### 🔑 1. Generar una clave

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

¿No hay Python en el host? Ejecútalo dentro del contenedor en su lugar:

```bash
docker exec librefolio python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 📝 2. Añádela a `.env` y reinicia

```bash
JWT_SECRET=paste-the-generated-value-here
```

Reinicia LibreFolio (con Docker Compose: `docker compose up -d`). Mantén la clave en privado:
quien la conozca puede falsificar una sesión.

Los workers de un único `./dev.py server --workers …` comparten una clave entre sí por sí solos. La duración
de una sesión es la **Duración de Sesión** en
[Configuración global](settings.md). Para más detalles, consulta la página para desarrolladores
[Arquitectura de seguridad](../developer/architecture/security.md).
