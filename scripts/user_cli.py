#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
"""
User Management CLI

Command-line tool for managing users from the server terminal.
Use this when you need to reset passwords or manage users without the web UI.

Usage:
    ./dev.sh user:create <username> <email> <password>
    ./dev.sh user:reset <username> <new_password>
    ./dev.sh user:list
    ./dev.sh user:activate <username>
    ./dev.sh user:deactivate <username>

Or directly:
    pipenv run python user_cli.py create-superuser <username> <email> <password>
    pipenv run python user_cli.py reset-password <username> <new_password>
    pipenv run python user_cli.py list-users
    pipenv run python user_cli.py activate <username>
    pipenv run python user_cli.py deactivate <username>

Use --test-db to operate on the test database:
    pipenv run python user_cli.py --test-db list-users
"""
import argparse
import asyncio
import sys
from pathlib import Path

import argcomplete

# Add project root to path (file is in scripts/)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_engine
from backend.app.services import user_service
from backend.app.services.settings_service import initialize_global_settings


async def cmd_reset_password(username: str, new_password: str):
    """Reset a user's password."""
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        success, error = await user_service.reset_password(session, username, new_password)

        if success:
            print(f"✅ Password reset for user '{username}'")
        else:
            print(f"❌ {error}")

        return success


async def cmd_create_superuser(username: str, email: str, password: str):
    """Create a new superuser."""
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        user, error = await user_service.create_user(
            session, username, email, password, is_superuser=True
            )

        if user:
            print(f"✅ Superuser '{username}' created with ID {user.id}")
            return True
        else:
            print(f"❌ {error}")
            return False


async def cmd_list_users():
    """List all users."""
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        users = await user_service.list_users(session)

        if not users:
            print("No users found")
            return

        print(f"\n{'ID':<5} {'Username':<20} {'Email':<30} {'Active':<8} {'Super':<8}")
        print("-" * 75)

        for user in users:
            active = "✅" if user.is_active else "❌"
            superuser = "👑" if user.is_superuser else ""
            print(f"{user.id:<5} {user.username:<20} {user.email:<30} {active:<8} {superuser:<8}")

        print(f"\nTotal: {len(users)} user(s)")


async def cmd_set_user_active(username: str, active: bool):
    """Activate or deactivate a user."""
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        success, error = await user_service.set_user_active(session, username, active)

        if success:
            status = "activated" if active else "deactivated"
            print(f"✅ User '{username}' {status}")
        else:
            print(f"❌ {error}")

        return success


async def cmd_set_admin(username: str, is_admin: bool):
    """Promote or demote a user to/from admin."""
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        success, error = await user_service.set_user_admin(session, username, is_admin)

        if success:
            status = "promoted to admin" if is_admin else "demoted from admin"
            print(f"✅ User '{username}' {status}")
        else:
            print(f"❌ {error}")

        return success


async def cmd_init_settings():
    """Initialize global settings with default values."""
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        created = await initialize_global_settings(session)

        if created > 0:
            print(f"✅ Initialized {created} global setting(s)")
        else:
            print("ℹ️  Global settings already initialized (no changes)")

        return True


def main():
    parser = argparse.ArgumentParser(
        description="LibreFolio User Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python user_cli.py reset-password john newpassword123
  python user_cli.py create-superuser admin admin@example.com adminpass
  python user_cli.py list-users
  python user_cli.py deactivate john
  python user_cli.py activate john
  python user_cli.py promote john
  python user_cli.py demote john
  
  # Operate on test database:
  python user_cli.py --test-db list-users
  python user_cli.py --test-db promote john
        """
        )

    # Global flag for test database
    parser.add_argument(
        "--test-db",
        action="store_true",
        help="Operate on test database instead of production"
        )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # reset-password
    reset_parser = subparsers.add_parser("reset-password", help="Reset user password")
    reset_parser.add_argument("username", help="Username")
    reset_parser.add_argument("new_password", help="New password")

    # create-superuser
    super_parser = subparsers.add_parser("create-superuser", help="Create superuser")
    super_parser.add_argument("username", help="Username")
    super_parser.add_argument("email", help="Email address")
    super_parser.add_argument("password", help="Password")

    # list-users
    subparsers.add_parser("list-users", help="List all users")

    # deactivate
    deact_parser = subparsers.add_parser("deactivate", help="Deactivate user")
    deact_parser.add_argument("username", help="Username")

    # activate
    act_parser = subparsers.add_parser("activate", help="Activate user")
    act_parser.add_argument("username", help="Username")

    # promote (make admin)
    promote_parser = subparsers.add_parser("promote", help="Promote user to admin")
    promote_parser.add_argument("username", help="Username")

    # demote (remove admin)
    demote_parser = subparsers.add_parser("demote", help="Demote user from admin")
    demote_parser.add_argument("username", help="Username")

    # init-settings (initialize global settings)
    subparsers.add_parser("init-settings", help="Initialize global settings with defaults")

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    _dispatch_user_command(args)


def _dispatch_user_command(args):
    """Dispatch to appropriate user command."""
    # Set test mode environment variable if --test-db flag is used
    if getattr(args, 'test_db', False):
        from backend.app.config import set_test_mode
        set_test_mode(True)
        print("ℹ️  Operating on TEST database")

    if args.command == "reset-password":
        asyncio.run(cmd_reset_password(args.username, args.new_password))
    elif args.command == "create-superuser":
        asyncio.run(cmd_create_superuser(args.username, args.email, args.password))
    elif args.command == "list-users":
        asyncio.run(cmd_list_users())
    elif args.command == "deactivate":
        asyncio.run(cmd_set_user_active(args.username, False))
    elif args.command == "activate":
        asyncio.run(cmd_set_user_active(args.username, True))
    elif args.command == "promote":
        asyncio.run(cmd_set_admin(args.username, True))
    elif args.command == "demote":
        asyncio.run(cmd_set_admin(args.username, False))
    elif args.command == "init-settings":
        asyncio.run(cmd_init_settings())


def register_subparser(parent_subparsers):
    """
    Register user commands as a subparser of dev.py.

    This allows dev.py to import and integrate user_cli's full parser.
    """
    user_parser = parent_subparsers.add_parser(
        "user",
        help="👤 User management (create, list, reset, activate, promote...)",
        description="User Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./dev.py user list                           List all users
  ./dev.py user create admin admin@ex.com pw   Create user
  ./dev.py user reset admin newpassword        Reset password
  ./dev.py user promote admin                  Make admin
  ./dev.py user --test-db list                 Use test database
"""
        )

    user_parser.add_argument(
        "--test-db",
        action="store_true",
        help="Use test database instead of production"
        )

    user_subparsers = user_parser.add_subparsers(
        dest="command",
        title="User commands",
        metavar=""
        )

    # create-superuser
    p = user_subparsers.add_parser("create", help="Create new user")
    p.add_argument("username", help="Username")
    p.add_argument("email", help="Email address")
    p.add_argument("password", help="Password")

    # list-users
    user_subparsers.add_parser("list", help="List all users")

    # reset-password
    p = user_subparsers.add_parser("reset", help="Reset user password")
    p.add_argument("username", help="Username")
    p.add_argument("new_password", help="New password")

    # deactivate
    p = user_subparsers.add_parser("deactivate", help="Deactivate user")
    p.add_argument("username", help="Username")

    # activate
    p = user_subparsers.add_parser("activate", help="Activate user")
    p.add_argument("username", help="Username")

    # promote
    p = user_subparsers.add_parser("promote", help="Promote user to admin")
    p.add_argument("username", help="Username")

    # demote
    p = user_subparsers.add_parser("demote", help="Demote from admin")
    p.add_argument("username", help="Username")

    # init-settings
    user_subparsers.add_parser("init-settings", help="Initialize global settings")

    user_parser.set_defaults(func=_dispatch_user_from_devpy)

    return user_parser


def _dispatch_user_from_devpy(args):
    """Handle user commands when called from dev.py."""
    if not args.command:
        print("Error: user command required. Use: ./dev.py user --help")
        return 1

    # Map dev.py command names to internal names
    command_map = {
        "create": "create-superuser",
        "list": "list-users",
        "reset": "reset-password",
        }
    args.command = command_map.get(args.command, args.command)

    _dispatch_user_command(args)
    return 0


if __name__ == "__main__":
    main()
