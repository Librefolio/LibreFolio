"""The answer of a route that refuses to touch a protected account (A5-1): one place for every route that asks the hook.

``user_service.account_protection(user)`` says whether an account is protected and why (on a managed instance, the
paying administrator). Each route that would delete, deactivate, demote, reset, sign out or change the email of an
account asks it, and refuses with the same 409 ``ACCOUNT_PROTECTED``; only the sentence differs. The hook is read as
``user_service.account_protection`` at every call, so a test can replace it.
"""

from typing import Optional

from fastapi import HTTPException, status

from backend.app.db.models import User
from backend.app.services.accounts import user_service

#: ``error_code`` of every refusal.
ACCOUNT_PROTECTED = "ACCOUNT_PROTECTED"
#: Delete, deactivate and demote an account from the Users tab.
CHANGE_MESSAGE = "This account cannot be deleted, deactivated or demoted"
#: The reset link and the sessions of an account, asked by an administrator.
ELSEWHERE_MESSAGE = "This account is protected: ask the host of this instance if something has to change"
#: The protected account deleting itself.
OWN_DELETION_MESSAGE = "This account cannot be deleted from here: ask the host of this instance"
#: The protected account changing its own email address.
EMAIL_CHANGE_MESSAGE = "The email address of this account can only be changed by the host of this instance"


def protection_refusal(user: User, message: str) -> Optional[HTTPException]:
    """409 ``ACCOUNT_PROTECTED`` with ``message`` and the hook's ``reason`` when ``user`` is protected; ``None`` otherwise."""
    reason = user_service.account_protection(user)
    if reason is None:
        return None
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error_code": ACCOUNT_PROTECTED, "message": message, "reason": reason})
