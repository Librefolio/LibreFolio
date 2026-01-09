#!/usr/bin/env python3
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
"""
import sys
import argparse
import asyncio
from pathlib import Path

# Add project root to path (file is now in root)
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_engine
from backend.app.services import user_service


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
        """
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

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

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


if __name__ == "__main__":
    main()

