# 🐳 Installation (User)

This guide explains how to deploy LibreFolio for regular use using Docker. This is the recommended method for users who do not intend to modify the source code.

## Prerequisites

- **Docker**: [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose**: Usually included with Docker Desktop.

## 1. Download the Project

Download the latest release from the [GitHub Releases](https://github.com/ea-enel/LibreFolio/releases) page. Unzip the folder.

Alternatively, you can clone the repository:

```bash
git clone https://github.com/ea-enel/LibreFolio.git
cd LibreFolio
```

## 2. Configure Environment

The project uses a `.env` file for configuration. A sample file is provided.

1. **Copy the example file**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env`** (Optional):
    - `PORT`: Change the port if `8000` is already in use.
    - `LIBREFOLIO_DATA_DIR`: Change where data is stored (default: `./backend/data/prod`).

## 3. Run with Docker Compose

This single command will build the images and start the application.

```bash
docker-compose up -d
```

- `-d` runs the application in detached mode (in the background).
- The first time you run this, Docker will download the necessary base images and build the application, which may take a few minutes.

## 4. Create a Superuser

To log in, you need to create an administrator account. The first user created automatically becomes the superuser.

```bash
docker-compose exec backend ./dev.py user create <username> <email> <password>
```

Replace `<username>`, `<email>`, and `<password>` with your credentials.

## 5. Access LibreFolio

The application is now running! Open your browser and go to:

**`http://localhost:8000`**

(Or use the port you configured in `.env`).

## Updating LibreFolio

To update to a new version:

1. **Download the latest code**:
   ```bash
   git pull
   ```

2. **Rebuild and restart the containers**:
   ```bash
   docker-compose up -d --build
   ```

3. **Apply database migrations** (if any):
   ```bash
   docker-compose exec backend pipenv run alembic upgrade head
   ```
