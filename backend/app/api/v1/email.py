"""Email administration, for administrators only: the state of the instance's email, and a test email to oneself.

The SMTP configuration itself is never returned (F04): only the state, the problem and the variable at fault, the
configuration checks of the email section (their i18n keys and parameters, never their log summary, which may name the
server) and the hourly budget. The test email goes only to the administrator's own address, in their language.
"""

import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.settings import require_admin
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.email import EmailBudgetRead, EmailCheckRead, EmailStatusResponse, EmailTestResponse
from backend.app.services.email import flows
from backend.app.services.email.checks import EMAIL_CONFIG_CHECKS
from backend.app.services.email.delivery import EmailDeliveryError, EmailRateLimitedError, EmailUnavailableError, budget_status, email_config_state
from backend.app.services.email.messages import EmailRecipientError

logger = get_logger(__name__)

router = APIRouter(prefix="/email", tags=["Email"])


@router.get("/status", response_model=EmailStatusResponse, summary="State of the instance's email (admin)")
def get_email_status(admin: Annotated[User, Depends(require_admin)]) -> EmailStatusResponse:
    """Whether email is off, ready or unusable, with the configuration checks and, when ready, the hourly budget.

    A plain ``def``: reading the configuration may read the small password file of ``LIBREFOLIO_SMTP_PASSWORD_FILE``,
    so the work runs in FastAPI's thread pool, not on the event loop.
    """
    checks = [EmailCheckRead(check_id=result.check_id, severity=result.severity, i18n_key=result.i18n_key, detail=result.detail) for result in (check() for check in EMAIL_CONFIG_CHECKS)]
    state = email_config_state()
    if not state.configured:
        return EmailStatusResponse(state="off", checks=checks)
    if not state.usable:
        return EmailStatusResponse(state="invalid", problem=state.problem, variable=state.variable, checks=checks)
    decision = budget_status(state.max_per_hour)
    budget = EmailBudgetRead(max_per_hour=state.max_per_hour, remaining=decision.remaining, retry_after_seconds=math.ceil(decision.retry_after))
    return EmailStatusResponse(state="ready", checks=checks, budget=budget)


@router.post("/test", response_model=EmailTestResponse, summary="Send a test email to yourself (admin)")
async def send_test(request: Request, admin: Annotated[User, Depends(require_admin)], session: AsyncSession = Depends(get_session_generator)) -> EmailTestResponse:
    """Send the test email to the administrator's own address, in their language; it costs one unit of the hourly budget.

    409 ``EMAIL_UNAVAILABLE`` (with the ``problem``) when email is off or unusable; 429 ``EMAIL_RATE_LIMITED`` with
    ``Retry-After`` when the hourly budget is spent; 502 ``EMAIL_DELIVERY_FAILED`` with the ``smtp_code`` when the SMTP
    server did not take the message; 422 ``EMAIL_RECIPIENT_INVALID`` when the account's address is not one address.
    """
    try:
        language = await flows.send_test_email(session, admin, instance=request.url.netloc)
    except EmailUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error_code": "EMAIL_UNAVAILABLE", "problem": exc.code, "message": "Email is off or cannot be used on this instance"}) from None
    except EmailRateLimitedError as exc:
        seconds = max(1, math.ceil(exc.retry_after))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error_code": "EMAIL_RATE_LIMITED", "retry_after": seconds, "message": "The hourly email limit of the instance is reached"},
            headers={"Retry-After": str(seconds)},
        ) from None
    except EmailDeliveryError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail={"error_code": "EMAIL_DELIVERY_FAILED", "smtp_code": exc.code, "message": "The SMTP server did not take the message"}) from None
    except EmailRecipientError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail={"error_code": "EMAIL_RECIPIENT_INVALID", "message": "The address of this account is not a single email address"}) from None
    logger.info("Test email sent by an administrator", admin_id=admin.id, language=language)
    return EmailTestResponse(language=language)
