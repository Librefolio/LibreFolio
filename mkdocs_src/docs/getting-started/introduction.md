# Introduction to LibreFolio

**LibreFolio** is a self-hosted, open-source application designed for private and personal tracking of financial investments.

## 🎯 Project Goals

- **Privacy First**: Keep track of your financial investments in a private, self-hosted environment.
- **Diverse Asset Support**: Supports both traditional assets (ETFs, stocks, crypto) and scheduled-yield loans (e.g., P2P lending).
- **Comprehensive Analytics**: Calculate performance, ROI, and historical trends.
- **Cash Management**: Manage cash movements associated with transactions.
- **Modern UI**: A modern, multilingual web interface.
- **Simple Deployment**: Distributed as a single, easy-to-deploy Docker container.

## 🧰 Technology Stack

### Backend
- **Language**: Python
- **Framework**: FastAPI
- **Database**: SQLModel (on top of SQLAlchemy) with SQLite
- **Migrations**: Alembic
- **Dependencies**: Pipenv

### Frontend
- **Framework**: React
- **Language**: TypeScript
- **Builder**: Vite
- **UI**: Material UI (MUI)

## 🧠 How to get information about the project idea

To get information about the project idea an Agent can:

1. Read the file `LibreFolio_developer_journal/01-Riassunto_generale.md` to get a general overview of the project.
2. Read the files in `LibreFolio_developer_journal/prompts/` to understand the original requirements for each feature.
3. Read the files in `docs/` to see the existing detailed documentation.
