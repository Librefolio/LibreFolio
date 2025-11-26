# Installation

This guide covers the setup for a local development environment. For production, please refer to the Docker deployment guide (coming soon).

## 1. Prerequisites

- Python 3.11+
- `pipenv`

## 2. Clone the Repository

```bash
git clone https://github.com/LibreFolio/LibreFolio.git
cd LibreFolio
```

## 3. Install Dependencies

Use `pipenv` to install all required packages from the `Pipfile`.

```bash
pipenv install --dev
```
This command creates a virtual environment and installs both production and development dependencies.

## 4. Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```
You can edit the `.env` file to change default settings like the database path or log level.

## 5. Database Setup

Initialize the database and apply all migrations:
```bash
./dev.sh db:upgrade
```
This will create the SQLite database file at `backend/data/sqlite/app.db`.

## 6. Run the Application

Start the backend server:
```bash
./dev.sh server
```
The API will be available at `http://localhost:8000`. You can access the interactive API documentation (Swagger UI) at `http://localhost:8000/docs`.

## AGENT-ACTION
To get info on how to install and run the project an Agent should:
1. Read this file.
2. Read the `README.md` file in the root directory.
3. Inspect the `Pipfile` to see the project dependencies.
4. Inspect the `dev.sh` script to understand the available commands.
