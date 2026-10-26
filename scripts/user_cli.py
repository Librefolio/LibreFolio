#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
"""
User Management CLI

Command-line tool for managing users from the server terminal.
Use this when you need to reset passwords or manage users without the web UI.

Usage:
    ./dev.py user create <username> <email> <password> [--role admin|user]
    ./dev.py user reset <username> <new_password>
    ./dev.py user list
    ./dev.py user activate <username>
    ./dev.py user deactivate <username>

Or directly:
    pipenv run python user_cli.py create-superuser <username> <email> <password>
    pipenv run python user_cli.py create-user <username> <email> <password>
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

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import set_test_mode
from backend.app.config.accounts import public_url
from backend.app.db.models import AccountTokenPurpose, OnboardingFlow
from backend.app.db.session import get_async_engine
from backend.app.services.accounts import bootstrap_admin_service, instance_owner, password_policy, registration_service, token_service, user_service
from backend.app.services.accounts.onboarding_service import reset_onboarding_progress
from backend.app.services.accounts.registration_service import RegistrationError
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.email import verification as email_verification

#: The sentence the command line prints for each rule of ``password_policy`` a new password misses.
_RULE_MESSAGES = {
    "min_length": f"min_length: the password must be at least {password_policy.MIN_LENGTH} characters long",
    "uppercase": "uppercase: the password must contain an uppercase letter",
    "lowercase": "lowercase: the password must contain a lowercase letter",
    "digit": "digit: the password must contain a digit",
    "special": "special: the password must contain a symbol (neither a letter, a number nor a space)",
}


def validate_password(password: str) -> tuple[bool, list[str]]:
    """The app's password rules (``password_policy``, decision 37): whether ``password`` meets them, and a sentence per rule it misses."""
    failed = password_policy.failed_rules(password)
    return not failed, [_RULE_MESSAGES.get(code, f"{code}: the password does not meet this rule") for code in failed]


async def cmd_reset_password(username: str, new_password: str):
    """Reset a user's password with validation."""
    # Validate password first
    is_valid, errors = validate_password(new_password)
    if not is_valid:
        print("❌ Password does not meet security requirements:")
        for error in errors:
            print(f"   • {error}")
        return False

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        success, error = await user_service.reset_password(session, username, new_password)

        if success:
            print(f"✅ Password reset for user '{username}'")
        else:
            print(f"❌ {error}")

        return success


async def cmd_create_user(username: str, email: str, password: str, is_superuser: bool):
    """Create an administrator or a regular account, with password validation."""
    # Validate password first
    is_valid, errors = validate_password(password)
    if not is_valid:
        print("❌ Password does not meet security requirements:")
        for error in errors:
            print(f"   • {error}")
        return False

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        _warn_if_full(await registration_service.user_usage(session), "creates the account")
        user, error = await user_service.create_user(session, username, email, password, is_superuser=is_superuser)

        if user:
            print(f"✅ {'Superuser' if is_superuser else 'User'} '{username}' created with ID {user.id}")
            return True
        else:
            print(f"❌ {error}")
            return False


def _warn_if_full(usage: registration_service.UserUsage, action: str) -> None:
    """Tell the operator the instance is at its limit: the command line goes past it (``action``: what it does anyway)."""
    if usage.full:
        print(f"⚠️  The instance is at its limit (LIBREFOLIO_MAX_USERS: {usage.used} of {usage.max_users} places taken): the command line {action} anyway")


def _public_url_note() -> str:
    """Why a printed link has no server address: the variable is unset, or set to something that is not an address."""
    try:
        public_url()
    except ValueError as exc:
        return f"LIBREFOLIO_PUBLIC_URL is not valid ({exc}): put the address of your server in front of the path"
    return "LIBREFOLIO_PUBLIC_URL is not set: put the address of your server in front of the path"


def _print_link(label: str, path: str, expires_at) -> None:
    """Print a single-use link: the full address with LIBREFOLIO_PUBLIC_URL, the path otherwise."""
    url = registration_service.public_link(path)
    print(f"✅ {label} link, single use, valid until {expires_at:%Y-%m-%d %H:%M} UTC:")
    print(f"   {url or path}")
    if url is None:
        print(f"   {_public_url_note()}")


async def cmd_invite(grants_admin: bool, email: str | None):
    """Create an invitation link; refused when registration is disabled."""
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        usage = await registration_service.user_usage(session)
        try:
            issued = await registration_service.create_invite(session, created_by_user_id=None, grants_admin=grants_admin, email=email, enforce_limit=False)
        except RegistrationError as exc:
            print(f"❌ {exc.message}")
            return False
        # This session expires its objects on commit: read the deadline before it
        expires_at = issued.record.expires_at
        await session.commit()
        _warn_if_full(usage, "creates the invitation")
        _print_link("Administrator invitation" if grants_admin else "Invitation", token_service.token_path(AccountTokenPurpose.INVITE, issued.token), expires_at)
        return True


async def cmd_reset_link(username: str):
    """Create a password-reset link for a user; the links issued before stop working."""
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        user = await user_service.get_user_by_username(session, username)
        if user is None:
            print(f"❌ User '{username}' not found")
            return False
        issued = await user_service.create_password_reset(session, user)
        expires_at = issued.record.expires_at
        await session.commit()
        _print_link(f"Password reset for '{username}'", token_service.token_path(AccountTokenPurpose.PASSWORD_RESET, issued.token), expires_at)
        return True


async def cmd_setup_link():
    """Create a new setup link for the initial administrator waiting for it (F02); the links issued before stop working."""
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        waiting = await bootstrap_admin_service.pending_admin(session)
        issued = await bootstrap_admin_service.issue_setup_link(session) if waiting is not None else None
        if waiting is None or issued is None:
            print("❌ No administrator account is waiting for its setup link")
            return False
        username, expires_at = waiting.username, issued.record.expires_at
        await session.commit()
        _print_link(f"Administrator setup for '{username}'", token_service.token_path(AccountTokenPurpose.ADMIN_SETUP, issued.token), expires_at)
        return True


async def cmd_set_email(username: str, address: str):
    """Change the email address of an account, as a change of address in its profile (decision P18).

    The address must be free regardless of case. A change ends the account's sessions and its address is not verified
    any more; the same address in another case only changes how it is written. It also separates two accounts that
    share an address apart from case, which stops the 1.3 migration (``005_release_1_3_0_schema``) before its unique
    index: it works on the database as it is.
    """
    try:
        email = TypeAdapter(EmailStr).validate_python(address)
    except ValidationError:
        print("❌ Not an email address")
        return False
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        user = await user_service.get_user_by_username(session, username)
        if user is None:
            print(f"❌ User '{username}' not found")
            return False
        updated, error = await user_service.update_profile(session, user.id, email=email)
        if updated is None:
            print(f"❌ {error}")
            return False
        print(f"✅ Email address of '{username}' changed")
        return True


#: What the command line says for each reason ``assign_owner_and_send_reset`` refuses.
_OWNER_REFUSALS = {
    "NOT_MANAGED": "This instance is not managed (LIBREFOLIO_PROFILE): the command is for managed instances only",
    "OWNER_EMAIL_NOT_SET": "LIBREFOLIO_ADMIN_EMAIL is not set: it holds the address the owner must have",
    "USER_NOT_FOUND": "User not found",
    "EMAIL_TAKEN": "Another account already has the address of LIBREFOLIO_ADMIN_EMAIL, or has it as its username: free it first with `user set-email`",
}


async def cmd_reassign_owner(username: str):
    """Give a managed instance back to its owner: the account takes the address of ``LIBREFOLIO_ADMIN_EMAIL`` (A5-4).

    For an owner address confirmed by mistake, or a managed instance taken over. It is the treatment a restore gives the
    owner's account (``instance_owner.assign_owner_and_send_reset``): the account takes the address of the variable, is an
    active administrator and the only owner, its password stops working, its sessions end, its links are cancelled, and ONE
    password-reset link goes to that address. The command never prints the link itself: if the email cannot go, the link is
    in the warning the treatment writes in the log, which the command line shows on its terminal, and ``user reset-link``
    prints another.
    """
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        user = await user_service.get_user_by_username(session, username)
        if user is None:
            print(f"❌ User '{username}' not found")
            return False
        try:
            result = await instance_owner.assign_owner_and_send_reset(session, user.id)
        except instance_owner.OwnerAssignmentError as exc:
            print(f"❌ {_OWNER_REFUSALS.get(exc.code, exc.code)}")
            return False
    print(f"✅ '{username}' is the owner of the instance, with the address of LIBREFOLIO_ADMIN_EMAIL; its password no longer works and its sessions ended")
    if result.outcome == instance_owner.OwnerResetOutcome.SENT:
        print("   One password-reset link was emailed to that address: the owner opens it and chooses a password")
    else:
        print("⚠️  The email could not go: the link is in the log line «Password-reset link for the instance owner» above, on this terminal only")
        print(f"   Pass it to the owner, or print a link on its own with: ./dev.py user reset-link {username}")
    return True


async def cmd_reset_onboarding(username: str, flow: str | None):
    """Put the onboarding of a user back to pending: every flow, or one."""
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        user = await user_service.get_user_by_username(session, username)
        if user is None:
            print(f"❌ User '{username}' not found")
            return False
        reset = await reset_onboarding_progress(session, user.id, OnboardingFlow(flow) if flow else None)
        print(f"✅ Onboarding of '{username}' reset ({flow or 'every flow'}, {reset} flow row(s))")
        return True


async def cmd_list_users():
    """List all users."""
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        users = await user_service.list_users(session)

        if not users:
            print("No users found")
            return True

        print(f"\n{'ID':<5} {'Username':<20} {'Email':<30} {'Active':<8} {'Super':<8}")
        print("-" * 75)

        for user in users:
            active = "✅" if user.is_active else "❌"
            superuser = "👑" if user.is_superuser else ""
            print(f"{user.id:<5} {user.username:<20} {user.email:<30} {active:<8} {superuser:<8}")

        print(f"\nTotal: {len(users)} user(s)")
        return True


async def cmd_set_user_active(username: str, active: bool):
    """Activate or deactivate a user."""
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        if active:
            user = await user_service.get_user_by_username(session, username)
            # An account that already holds its place takes no new one: one waiting for its email verification while its
            # link is live (workstream E), or the initial administrator waiting for its setup (A-40)
            if user is not None and not user.is_active and not await email_verification.holds_place(session, user) and not await registration_service.is_pending_admin(session, user):
                _warn_if_full(await registration_service.user_usage(session), "reactivates the account")
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
  python user_cli.py create-user john john@example.com Johnpass1!
  python user_cli.py list-users
  python user_cli.py deactivate john
  python user_cli.py activate john
  python user_cli.py promote john
  python user_cli.py demote john

  # Operate on test database:
  python user_cli.py --test-db list-users
  python user_cli.py --test-db promote john
        """,
    )

    # Global flag for test database
    parser.add_argument("--test-db", action="store_true", help="Operate on test database instead of production")

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

    # create-user (a regular account)
    create_user_parser = subparsers.add_parser("create-user", help="Create regular (non-admin) user")
    create_user_parser.add_argument("username", help="Username")
    create_user_parser.add_argument("email", help="Email address")
    create_user_parser.add_argument("password", help="Password")

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

    _add_link_commands(subparsers)

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return 0 if _dispatch_user_command(args) else 1


def _add_link_commands(subparsers) -> None:
    """The commands that print a single-use link, change an address or restart an onboarding: the same names here and in dev.py."""
    p = subparsers.add_parser("set-email", help="Change the email address of a user (unique regardless of case)")
    p.add_argument("username", help="Username")
    p.add_argument("email", help="The new email address")

    p = subparsers.add_parser("invite", help="Create an invitation link")
    p.add_argument("--admin", action="store_true", help="The account it creates is an administrator")
    p.add_argument("--email", default=None, help="Who it is for (kept for reference, not enforced)")

    p = subparsers.add_parser("reset-link", help="Create a password-reset link for a user")
    p.add_argument("username", help="Username")

    subparsers.add_parser("setup-link", help="Create a new setup link for the initial administrator (LIBREFOLIO_ADMIN_EMAIL)")

    p = subparsers.add_parser("reassign-owner", help="Give a managed instance back to its owner: the account takes the address of LIBREFOLIO_ADMIN_EMAIL, loses its password and gets one reset link")
    p.add_argument("username", help="Username of the account that becomes the owner")

    p = subparsers.add_parser("reset-onboarding", help="Restart the onboarding of a user")
    p.add_argument("username", help="Username")
    p.add_argument("--flow", choices=[flow.value for flow in OnboardingFlow], default=None, help="Only this flow (default: every flow)")


def _dispatch_user_command(args):
    """Dispatch to appropriate user command."""
    # Set test mode environment variable if --test-db flag is used
    if getattr(args, "test_db", False):
        set_test_mode(True)
        print("ℹ️  Operating on TEST database")

    commands = {
        "reset-password": lambda: cmd_reset_password(args.username, args.new_password),
        "create-superuser": lambda: cmd_create_user(args.username, args.email, args.password, is_superuser=True),
        "create-user": lambda: cmd_create_user(args.username, args.email, args.password, is_superuser=False),
        "list-users": cmd_list_users,
        "deactivate": lambda: cmd_set_user_active(args.username, False),
        "activate": lambda: cmd_set_user_active(args.username, True),
        "promote": lambda: cmd_set_admin(args.username, True),
        "demote": lambda: cmd_set_admin(args.username, False),
        "init-settings": cmd_init_settings,
        "invite": lambda: cmd_invite(args.admin, args.email),
        "reset-link": lambda: cmd_reset_link(args.username),
        "setup-link": cmd_setup_link,
        "set-email": lambda: cmd_set_email(args.username, args.email),
        "reassign-owner": lambda: cmd_reassign_owner(args.username),
        "reset-onboarding": lambda: cmd_reset_onboarding(args.username, args.flow),
    }
    command = commands.get(args.command)
    return asyncio.run(command()) if command else False


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
  ./dev.py user create admin admin@ex.com pw   Create an administrator
  ./dev.py user create bob bob@ex.com pw --role user
                                               Create a regular account
  ./dev.py user reset admin newpassword        Reset password
  ./dev.py user promote admin                  Make admin
  ./dev.py user --test-db list                 Use test database
""",
    )

    user_parser.add_argument("--test-db", action="store_true", help="Use test database instead of production")

    user_subparsers = user_parser.add_subparsers(dest="command", title="User commands", metavar="")

    # create-superuser, or create-user with --role user
    p = user_subparsers.add_parser("create", help="Create new user (an administrator unless --role user)")
    p.add_argument("username", help="Username")
    p.add_argument("email", help="Email address")
    p.add_argument("password", help="Password")
    p.add_argument("--role", choices=("admin", "user"), default="admin", help="admin (default) or user, a regular account")

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

    _add_link_commands(user_subparsers)

    user_parser.set_defaults(func=_dispatch_user_from_devpy)

    return user_parser


def _dispatch_user_from_devpy(args):
    """Handle user commands when called from dev.py."""
    if not args.command:
        print("Error: user command required. Use: ./dev.py user --help")
        return 1

    # Map dev.py command names to internal names
    command_map = {
        "create": "create-user" if getattr(args, "role", "admin") == "user" else "create-superuser",
        "list": "list-users",
        "reset": "reset-password",
    }
    args.command = command_map.get(args.command, args.command)

    # A command that fails (it printed ❌) exits 1, for scripts that check the status.
    return 0 if _dispatch_user_command(args) else 1


if __name__ == "__main__":
    sys.exit(main())
