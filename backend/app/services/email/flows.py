"""What LibreFolio sends, and to whom: one function per email that an action of the application sends.

Every email of an account goes out in the account's language: its own (``user_settings.language``), otherwise the
instance's ``default_language``, otherwise English. A language that names none of the four counts as unset. The
functions here only decide content, recipient and language; ``delivery.send_email`` checks the configuration and the
hourly budget, sends, and logs.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import User, UserSettings
from backend.app.schemas.settings import SETTINGS_REGISTRY
from backend.app.services.accounts.global_settings_service import get_setting_value
from backend.app.services.email.delivery import send_email
from backend.app.services.email.messages import build_test_message, email_language, supported_email_language


async def account_language(session: AsyncSession, user_id: int) -> str:
    """The language of the emails of an account: its own, else the instance's ``default_language``, else English.

    Reads the language column alone: a settings row that no longer validates (an old theme, say) never stops an email.
    Creates nothing.
    """
    own = (await session.execute(select(UserSettings.language).where(UserSettings.user_id == user_id))).scalar_one_or_none()
    language = supported_email_language(own)
    if language is not None:
        return language
    return email_language(await get_setting_value(session, SETTINGS_REGISTRY.global_.DEFAULT_LANGUAGE.key, "en"))


async def send_test_email(session: AsyncSession, user: User, *, instance: str) -> str:
    """Send the test email to ``user``'s own address, in their language; returns that language.

    ``instance`` names the instance in the text. Raises what ``delivery.send_email`` raises.
    """
    language = await account_language(session, user.id)
    content = build_test_message(language=language, username=user.username, instance=instance)
    await send_email(content, to=user.email, user_id=user.id)
    return language
