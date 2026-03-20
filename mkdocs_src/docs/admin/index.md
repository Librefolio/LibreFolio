# 🛡️ Admin Manual

This manual is for system administrators and advanced users who need to perform maintenance, manage users, or interact with the system via the command line.

## Overview

Most administrative tasks are handled through the main CLI tool:

1. **`dev.py`**: The main orchestration script for development and maintenance. It provides a tree-structured CLI for all tasks: running tests, managing the database, building the
   frontend, user management, translations, and more.

## Guides

- **[CLI Tools](cli_tools.md)**: Detailed documentation on `dev.py` commands and subcommands.
- **[Global Settings](settings.md)**: Configure system-wide parameters (session TTL, upload limits, sync intervals, defaults).
- **[Filesystem Structure](filesystem.md)**: Understand where data is stored, how to back up, and how to access the system from the host terminal.
- **[Advanced Docker](docker_advanced.md)**: A deep dive into the Docker setup, including networking, volumes, and customization for production environments.
- **[Exposing with Tailscale](tailscale_exposure.md)**: Securely expose your LibreFolio instance over the internet using Tailscale.

## Authentication

LibreFolio uses **JWT (JSON Web Tokens)** for authentication. The server generates a random signing secret at startup, shared across all workers. Tokens expire after a configurable number of hours (see [Global Settings](settings.md)). For technical details, see [Security Architecture](../developer/architecture/security.md).
