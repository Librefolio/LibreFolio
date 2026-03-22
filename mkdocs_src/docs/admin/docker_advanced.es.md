# 🐳 Guía Avanzada de Docker

Esta guía ofrece una visión más profunda de la configuración de Docker para LibreFolio, dirigida a usuarios que deseen personalizar su despliegue.

## 📄 `docker-compose.yml`

El archivo `docker-compose.yml` define los servicios, redes y volúmenes de la aplicación.

### 🔧 Servicios

- **`backend`**: La aplicación principal de FastAPI.
 - 🏗️ **`build`**: Especifica el Dockerfile en la raíz del proyecto.
 - 🔌 **`ports`**: Mapea el puerto del anfitrión (definido por `${PORT}` en `.env`) al puerto 8000 del contenedor.
 - 📂 **`volumes`**:
 - `./backend:/app/backend`: Monta el código fuente del backend para desarrollo, permitiendo recarga en caliente.
 - `./frontend/build:/app/frontend/build`: Monta la versión compilada del frontend para producción.
 - `./mkdocs_src/site:/app/mkdocs_src/site`: Monta el sitio de documentación.
 - `./logs:/app/logs`: Monta el directorio de registros para preservar los archivos de log.
 - 🌍 **`env_file`**: Carga las variables de entorno desde el archivo `.env`.

### 💾 Volúmenes

- **`libre-folio-data`**: Un volumen con nombre utilizado para mantener los archivos de la base de datos SQLite. Esto asegura que sus datos no se pierdan cuando detenga o elimine los contenedores.

### 🌐 Redes

- **`libre-folio-net`**: Una red bridge personalizada para permitir la comunicación entre servicios.

## 🏭 Consideraciones para Producción

Para un despliegue en producción, considere los siguientes cambios:

### 🔒 1. Proxy Inverso

Se recomienda encarecidamente ejecutar LibreFolio detrás de un proxy inverso, como **Nginx** o **Traefik**. Esto permite:

- 🔐 Gestionar fácilmente certificados SSL/TLS para HTTPS.
- 🖥️ Servir múltiples aplicaciones en el mismo servidor.
- 🛡️ Añadir encabezados de seguridad y limitación de tasa.

### 💾 2. Respaldo de la Base de Datos

Dado que la base de datos se almacena en un volumen de Docker, debe diseñar una estrategia de respaldo. Puede utilizar una simple tarea cron para copiar el archivo de la base de datos desde el volumen a una ubicación segura.

Ejemplo de script de respaldo:

```bash
#!/bin/bash
docker cp librefolio_backend_1:/app/backend/data/sqlite/app.db /path/to/backups/app.db-$(date +%F)
```

### 🚫 3. Deshabilitar los Montajes de Desarrollo

En un entorno de producción, es posible que no desee montar el código fuente directamente. Puede crear un archivo `docker-compose.prod.yml` separado que omita los volúmenes de código fuente y dependa únicamente de la imagen Docker construida.
