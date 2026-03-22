# 🐳 Instalación (Usuario)

Esta guía explica cómo desplegar LibreFolio para uso regular mediante Docker. Este es el método recomendado para usuarios que no pretenden modificar el código fuente.

## ✅ Requisitos previos

- 🐋 **Docker**: [Instalar Docker](https://docs.docker.com/get-docker/)
- 🔗 **Docker Compose**: Normalmente incluido con Docker Desktop.

## 📥 1. Descarga el Proyecto

Descarga la última versión desde la página de [Lanzamientos de GitHub](https://github.com/ea-enel/LibreFolio/releases). Descomprime el archivo.

Alternativamente, puedes clonar el repositorio:

```bash
git clone https://github.com/ea-enel/LibreFolio.git
cd LibreFolio
```

## ⚙️ 2. Configura el Entorno

El proyecto utiliza un archivo `.env` para la configuración. Se proporciona un archivo de ejemplo.

1. **Copia el archivo de ejemplo**:
 ```bash
 cp .env.example .env
 ```

2. **Edita `.env`** (Opcional):
 - 🔌 `PORT`: Cambia el puerto si `8000` ya está en uso.
 - 📁 `LIBREFOLIO_DATA_DIR`: Cambia dónde se almacenan los datos (predeterminado: `./backend/data/prod`).

## 🚀 3. Ejecuta con Docker Compose

Este único comando construirá las imágenes y pondrá en marcha la aplicación.

```bash
docker-compose up -d
```

- 🔄 `-d` ejecuta la aplicación en **modo desacoplado** (en segundo plano).
- ⏳ La primera vez que ejecutes esto, Docker descargará las imágenes base necesarias y construirá la aplicación, lo que puede tardar unos minutos.

## 👤 4. Crea un Superusuario

Para iniciar sesión, necesitas crear una cuenta de administrador. El primer usuario creado automáticamente se convierte en superusuario.

```bash
docker-compose exec backend ./dev.py user create <usuario> <correo> <contraseña>
```

Reemplaza `<usuario>`, `<correo>` y `<contraseña>` con tus credenciales.

## 🌐 5. Accede a LibreFolio

¡La aplicación ya está en ejecución! Abre tu navegador y ve a:

**`http://localhost:8000`**

(O usa el puerto que configuraste en `.env`).

## 🔄 Actualizar LibreFolio

Para actualizar a una nueva versión:

1. **Descarga el código más reciente**:
 ```bash
 git pull
 ```

2. **Reconstruye y reinicia los contenedores**:
 ```bash
 docker-compose up -d --build
 ```

3. **Aplica migraciones de la base de datos** (si las hay):
 ```bash
 docker-compose exec backend pipenv run alembic upgrade head
 ```
