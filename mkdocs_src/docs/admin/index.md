# Admin Manual

This manual is for system administrators and advanced users who need to perform maintenance, manage users, or interact with the system via the command line.

## Overview

Most administrative tasks are handled through three primary tools:

1. **`dev.sh`**: The main helper script for development and maintenance. It provides shortcuts for common tasks like running tests, managing the database, and building the
   frontend.
2. **`user_cli.py`**: A command-line interface for user management, such as creating superusers, resetting passwords, and managing roles.
3. **`test_runner.py`**: The script used to run the project's test suites.

## Guides

- **[CLI Tools](cli_tools.md)**: Detailed documentation on using `dev.sh`, `user_cli.py`, and `test_runner.py`.
- **[Advanced Docker](docker_advanced.md)**: A deep dive into the Docker setup, including networking, volumes, and customization for production environments.
