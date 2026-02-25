# Admin Manual

This manual is for system administrators and advanced users who need to perform maintenance, manage users, or interact with the system via the command line.

## Overview

Most administrative tasks are handled through the main CLI tool:

1. **`dev.py`**: The main orchestration script for development and maintenance. It provides a tree-structured CLI for all tasks: running tests, managing the database, building the
   frontend, user management, translations, and more.

## Guides

- **[CLI Tools](cli_tools.md)**: Detailed documentation on `dev.py` commands and subcommands.
- **[Advanced Docker](docker_advanced.md)**: A deep dive into the Docker setup, including networking, volumes, and customization for production environments.
