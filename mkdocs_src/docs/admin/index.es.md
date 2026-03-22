# 🛡️ Manual del Administrador

Este manual está dirigido a administradores de sistemas y usuarios avanzados que necesitan realizar tareas de mantenimiento, gestionar usuarios o interactuar con el sistema mediante la línea de comandos.

## 📖 Descripción General

La mayoría de las tareas administrativas se gestionan a través de la herramienta CLI principal:

1. **`dev.py`**: El script de orquestación principal para desarrollo y mantenimiento. Proporciona una CLI estructurada en árbol para todas las tareas: ejecutar pruebas, gestionar la base de datos, construir el frontend, gestión de usuarios, traducciones y más.

## 📚 Guías

- 🛠️ **[Herramientas CLI](cli_tools.md)**: Documentación detallada sobre comandos y subcomandos de `dev.py`.
- ⚙️ **[Configuración Global](settings.md)**: Configure parámetros de todo el sistema (TTL de sesión, límites de carga, intervalos de sincronización, valores predeterminados).
- 📂 **[Estructura del Sistema de Archivos](filesystem.md)**: Comprenda dónde se almacenan los datos, cómo realizar copias de seguridad y cómo acceder al sistema desde el terminal del host.
- 🐳 **[Docker Avanzado](docker_advanced.md)**: Una exploración profunda de la configuración de Docker, incluyendo redes, volúmenes y personalización para entornos de producción.
- 🌐 **[Exponer mediante Tailscale](tailscale_exposure.md)**: Exponga su instancia de LibreFolio de forma segura a través de Internet usando Tailscale.

## 🔐 Autenticación

LibreFolio utiliza **JWT (JSON Web Tokens)** para la autenticación. El servidor genera un secreto de firma aleatorio al iniciar, compartido entre todos los workers. Los tokens expiran después de un número de horas configurable (ver [Configuración Global](settings.md)). Para detalles técnicos, consulte [Arquitectura de Seguridad](../developer/architecture/security.md).
