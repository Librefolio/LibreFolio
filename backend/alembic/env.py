import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy import pool

# Add the backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import SQLModel base and config
from backend.app.db.base import SQLModel
from backend.app.config import get_settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override sqlalchemy.url with our config or from -x parameter
# Check if database URL was passed via -x sqlalchemy.url="..."
db_url = None
if hasattr(config, 'cmd_opts') and hasattr(config.cmd_opts, 'x'):
    if config.cmd_opts.x:
        for x_arg in config.cmd_opts.x:
            if x_arg.startswith('sqlalchemy.url='):
                db_url = x_arg.split('=', 1)[1]
                break

if db_url:
    # Use URL passed from command line (e.g., for tests)
    print(f"[Alembic env.py] Using DATABASE_URL from -x parameter: {db_url}")
    config.set_main_option("sqlalchemy.url", db_url)
else:
    # Use URL from config.py (reads from environment/env file)
    settings = get_settings()
    print(f"[Alembic env.py] Using DATABASE_URL from config: {settings.DATABASE_URL}")
    config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# Set SQLModel metadata for autogenerate
target_metadata = SQLModel.metadata


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Enable batch mode for SQLite
        )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Enable batch mode for SQLite
            )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
