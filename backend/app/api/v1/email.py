"""Email: its state and a test email for administrators, links emailed by an administrator, «forgot password», and the
verification of an address at sign-up.

The SMTP configuration itself is never returned (F04): only the state, the problem and the variable at fault, the
configuration checks of the email section (their i18n keys and parameters, never their log summary, which may name the
server), the hourly budget and whether emails can carry links. Every emailed link is built from
``LIBREFOLIO_PUBLIC_URL`` alone (developer decision 45), never from anything in a request.
"""

import math
from typing import Annotated, NoReturn

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.settings import require_admin
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.email import (
    EmailBudgetRead,
    EmailChangeConfirmRequest,
    EmailChangeConfirmResponse,
    EmailCheckRead,
    EmailLinkRequest,
    EmailLinkResponse,
    EmailLinksRead,
    EmailStatusResponse,
    EmailTestResponse,
    EmailVerificationConfirmRequest,
    EmailVerificationConfirmResponse,
    EmailVerificationResendRequest,
    EmailVerificationResendResponse,
    PasswordResetEmailAccepted,
    PasswordResetEmailRequest,
)
from backend.app.services.accounts import instance_owner
from backend.app.services.email import flows, verification
from backend.app.services.email.checks import EMAIL_CONFIG_CHECKS
from backend.app.services.email.delivery import EmailDeliveryError, EmailRateLimitedError, EmailUnavailableError, budget_status, email_config_state
from backend.app.services.email.links import EmailLinksUnavailableError, links_state
from backend.app.services.email.messages import EmailRecipientError
from backend.app.services.platform.client_address import rate_limit_address

logger = get_logger(__name__)

router = APIRouter(prefix="/email", tags=["Email"])


def _links_read() -> EmailLinksRead:
    state = links_state()
    return EmailLinksRead(ready=state.ready, base=state.base, problem=state.problem)


@router.get("/status", response_model=EmailStatusResponse, summary="State of the instance's email (admin)")
def get_email_status(admin: Annotated[User, Depends(require_admin)]) -> EmailStatusResponse:
    """Whether email is off, ready or unusable, with the configuration checks, whether emails can carry links and, when
    ready, the hourly budget.

    A plain ``def``: reading the configuration may read the small password file of ``LIBREFOLIO_SMTP_PASSWORD_FILE``,
    so the work runs in FastAPI's thread pool, not on the event loop.
    """
    checks = [EmailCheckRead(check_id=result.check_id, severity=result.severity, i18n_key=result.i18n_key, detail=result.detail) for result in (check() for check in EMAIL_CONFIG_CHECKS)]
    links = _links_read()
    state = email_config_state()
    if not state.configured:
        return EmailStatusResponse(state="off", checks=checks, links=links)
    if not state.usable:
        return EmailStatusResponse(state="invalid", problem=state.problem, variable=state.variable, checks=checks, links=links)
    decision = budget_status(state.max_per_hour)
    budget = EmailBudgetRead(max_per_hour=state.max_per_hour, remaining=decision.remaining, retry_after_seconds=math.ceil(decision.retry_after))
    return EmailStatusResponse(state="ready", checks=checks, budget=budget, links=links)


def _rate_limited(exc: EmailRateLimitedError, message: str) -> NoReturn:
    seconds = max(1, math.ceil(exc.retry_after))
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={"error_code": "EMAIL_RATE_LIMITED", "retry_after": seconds, "message": message},
        headers={"Retry-After": str(seconds)},
    ) from None


def _delivery_failed(exc: EmailDeliveryError) -> NoReturn:
    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail={"error_code": "EMAIL_DELIVERY_FAILED", "smtp_code": exc.code, "message": "The SMTP server did not take the message"}) from None


def _unavailable(exc: EmailUnavailableError) -> NoReturn:
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error_code": "EMAIL_UNAVAILABLE", "problem": exc.code, "message": "Email is off or cannot be used on this instance"}) from None


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
        _unavailable(exc)
    except EmailRateLimitedError as exc:
        _rate_limited(exc, "The hourly email limit of the instance is reached")
    except EmailDeliveryError as exc:
        _delivery_failed(exc)
    except EmailRecipientError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail={"error_code": "EMAIL_RECIPIENT_INVALID", "message": "The address of this account is not a single email address"}) from None
    logger.info("Test email sent by an administrator", admin_id=admin.id, language=language)
    return EmailTestResponse(language=language)


@router.post("/links", response_model=EmailLinkResponse, summary="Email a link just created: an invitation or a password reset (admin)")
async def send_link(body: EmailLinkRequest, admin: Annotated[User, Depends(require_admin)], session: AsyncSession = Depends(get_session_generator)) -> EmailLinkResponse:
    """Email the link of a token that ``POST /users/invites`` or ``POST /users/{id}/password-reset-link`` has just given.

    The link is built from ``LIBREFOLIO_PUBLIC_URL`` alone. An invitation goes to ``to``, else to the address written
    in it; a password-reset link only to the address of its account. 409 ``EMAIL_UNAVAILABLE``, 409
    ``EMAIL_LINKS_UNAVAILABLE`` (with the ``problem``), 409 ``EMAIL_LINK_INVALID`` (with the token's ``status``), 409
    ``EMAIL_ACCOUNT_INACTIVE`` (a reset link of an inactive account), 422
    ``EMAIL_RECIPIENT_REQUIRED``, ``EMAIL_RECIPIENT_NOT_ALLOWED`` or ``EMAIL_RECIPIENT_INVALID``, 429
    ``EMAIL_RATE_LIMITED``, 502 ``EMAIL_DELIVERY_FAILED``. The token is never logged.
    """
    try:
        sent = await flows.send_link_email(session, admin=admin, purpose=body.purpose, token=body.token, to=body.to, language=body.language)
    except EmailUnavailableError as exc:
        _unavailable(exc)
    except EmailLinksUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error_code": "EMAIL_LINKS_UNAVAILABLE", "problem": exc.code, "message": "Emails cannot carry links: LIBREFOLIO_PUBLIC_URL is not set, or cannot start a link"}) from None
    except flows.EmailLinkInvalidError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error_code": "EMAIL_LINK_INVALID", "status": exc.code, "message": "The link is not a live link of that kind"}) from None
    except flows.EmailAccountInactiveError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error_code": "EMAIL_ACCOUNT_INACTIVE", "message": "The account is not active: activate it before sending it a reset link"}) from None
    except (flows.EmailRecipientRequiredError, flows.EmailRecipientNotAllowedError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail={"error_code": exc.code, "message": "The address to send the link to is missing or not allowed"}) from None
    except EmailRecipientError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail={"error_code": "EMAIL_RECIPIENT_INVALID", "message": "The address to send the link to is not a single email address"}) from None
    except EmailRateLimitedError as exc:
        _rate_limited(exc, "The hourly email limit of the instance is reached")
    except EmailDeliveryError as exc:
        _delivery_failed(exc)
    return EmailLinkResponse(purpose=body.purpose, to=sent.to, language=sent.language)


@router.post("/password-reset", response_model=PasswordResetEmailAccepted, status_code=status.HTTP_202_ACCEPTED, summary="Forgot password: a reset link by email")
async def request_password_reset_email(
    body: PasswordResetEmailRequest,
    request: Request,
    background: BackgroundTasks,
    session: AsyncSession = Depends(get_session_generator),
) -> PasswordResetEmailAccepted:
    """No session needed. The answer never says whether an account matches: 202, the same for everyone, and the work
    (look the account up, create the link, send it) runs after it, in the background.

    409 ``EMAIL_UNAVAILABLE`` or ``EMAIL_LINKS_UNAVAILABLE`` when the instance cannot send such an email, which
    ``GET /system/instance`` already says; 429 ``EMAIL_RATE_LIMITED`` with ``Retry-After`` past the limits per address
    and per identifier, or with the hourly budget spent. Neither depends on the accounts. Changing an account's email
    asks for its current password (workstream A, lot A6e): a moment inside someone's session cannot move their address,
    then their password, through here.
    """
    # None behind a reverse proxy LibreFolio does not trust: no count per address then (N70, E-13)
    address = rate_limit_address(request)
    try:
        await flows.admit_forgotten_password(address, body.identifier)
    except EmailUnavailableError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error_code": "EMAIL_UNAVAILABLE", "message": "This instance cannot send emails"}) from None
    except EmailLinksUnavailableError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error_code": "EMAIL_LINKS_UNAVAILABLE", "message": "This instance cannot send emails with a link"}) from None
    except EmailRateLimitedError as exc:
        _rate_limited(exc, "Too many requests: try again later")
    # The session of this request ends with it: the work opens its own, on the same database.
    background.add_task(flows.forgotten_password_work, body.identifier, engine=session.bind, address=address)
    return PasswordResetEmailAccepted()


@router.post("/verification/confirm", response_model=EmailVerificationConfirmResponse, summary="Verify an email address: spend the link of the verification email")
async def confirm_email_verification(body: EmailVerificationConfirmRequest, session: AsyncSession = Depends(get_session_generator)) -> EmailVerificationConfirmResponse:
    """No session needed: the link proves that its reader received the email. The account becomes active, its address
    verified, and its other verification links stop working.

    400 ``TOKEN_INVALID`` with the token's ``status`` (``expired``, ``consumed``, ``revoked``, ``unknown``): ``revoked``
    also for a link emailed to an address the account no longer has (revoked then), and for one whose email did not go
    as far as LibreFolio knows (left as it is: the account keeps waiting). A dead link is not the end: signing in
    offers to send a new one.
    """
    try:
        user = await verification.confirm_email(session, body.token)
    except verification.EmailVerificationLinkInvalidError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error_code": "TOKEN_INVALID", "status": exc.code, "message": "This verification link is not valid"}) from None
    return EmailVerificationConfirmResponse(username=user.username)


@router.post("/email-change/confirm", response_model=EmailChangeConfirmResponse, summary="Confirm the new address of the instance owner: spend the link emailed to it")
async def confirm_owner_email_change(body: EmailChangeConfirmRequest, background: BackgroundTasks, session: AsyncSession = Depends(get_session_generator)) -> EmailChangeConfirmResponse:
    """No session needed: the link proves that its reader received the email at the new address, which the host put in
    ``LIBREFOLIO_ADMIN_EMAIL`` of a managed instance. The owner's address becomes the link's, verified; every session of
    the owner ends (it signs in again, same password); its other change links and its password-reset links stop
    working. When email works, the address it had before gets a notice after the answer, as for a change of the profile.

    400 ``TOKEN_INVALID`` with the token's ``status`` (``expired``, ``consumed``, ``revoked``, ``unknown``): ``revoked``
    also when the link no longer matches the instance (the host changed the variable again, the instance is no longer
    managed, the account is no longer the owner, or another account took the address meanwhile; the link is revoked
    then and nothing changed). A token of another purpose is ``unknown``.
    """
    try:
        changed = await instance_owner.confirm_email_change(session, body.token)
    except instance_owner.OwnerEmailChangeLinkInvalidError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error_code": "TOKEN_INVALID", "status": exc.code, "message": "This confirmation link is not valid"}) from None
    # The notice to the old address (workstream E): after the answer, with a session of its own; never raises.
    background.add_task(flows.email_changed_work, changed.user.id, changed.old_email, changed.user.email, engine=session.bind)
    return EmailChangeConfirmResponse(username=changed.user.username)


@router.post("/verification/resend", response_model=EmailVerificationResendResponse, summary="Send the verification email again, with the credentials of the sign-in")
async def resend_email_verification(body: EmailVerificationResendRequest, request: Request, session: AsyncSession = Depends(get_session_generator)) -> EmailVerificationResendResponse:
    """For an account waiting for its verification link: the sign-in's credentials, then a new link by email.

    The credentials are checked as the sign-in checks them: 401 ``INVALID_CREDENTIALS`` for a wrong password or an
    unknown account, the same answer and the same cost; any other 401 of this public route is the block's, which an
    anonymous caller gets on a blocked instance (E-11); 403 ``ACCOUNT_DISABLED`` for an account an administrator
    deactivated. 409 ``EMAIL_VERIFICATION_NOT_NEEDED`` for an active account; 409 ``EMAIL_UNAVAILABLE``,
    ``EMAIL_LINKS_UNAVAILABLE`` (without the ``problem``: not an administrator); 409 ``USER_LIMIT_REACHED`` when the old link expired and the instance is full now; 429
    ``EMAIL_RATE_LIMITED`` with ``Retry-After`` (10 requests per 15 minutes per address, before the password; the
    sign-in's limit on failed passwords, 10 per identifier and 50 per address in 15 minutes, shared with
    ``POST /auth/login``, before the password too; per account, one email every 5 minutes and 3 an hour; the hourly
    budget); 502 ``EMAIL_DELIVERY_FAILED`` (without the
    ``smtp_code``); 422
    ``EMAIL_RECIPIENT_INVALID`` when the account's address is not one address.
    """
    # None behind a reverse proxy LibreFolio does not trust: no count per address then (N70, E-13)
    address = rate_limit_address(request)
    try:
        language = await verification.resend_verification(session, identifier=body.username, password=body.password, address=address)
    except verification.VerificationCredentialsError:
        # Its own code: the web app reads any other 401 of this route as the instance's block (E-11).
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"error_code": "INVALID_CREDENTIALS", "message": "Invalid credentials"}) from None
    except verification.VerificationAccountDisabledError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error_code": "ACCOUNT_DISABLED", "message": "Account is disabled"}) from None
    except verification.EmailVerificationNotNeededError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error_code": "EMAIL_VERIFICATION_NOT_NEEDED", "message": "This account is active: sign in"}) from None
    except verification.VerificationUserLimitError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error_code": "USER_LIMIT_REACHED", "message": "The instance has reached its maximum number of users"}) from None
    except EmailUnavailableError:
        # Without the problem: whoever asks is not an administrator.
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error_code": "EMAIL_UNAVAILABLE", "message": "This instance cannot send emails"}) from None
    except EmailLinksUnavailableError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error_code": "EMAIL_LINKS_UNAVAILABLE", "message": "This instance cannot send emails with a link"}) from None
    except EmailRateLimitedError as exc:
        _rate_limited(exc, "Too many requests: try again later")
    except EmailDeliveryError:
        # Without the SMTP code: whoever asks is not an administrator.
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail={"error_code": "EMAIL_DELIVERY_FAILED", "message": "The email could not be sent"}) from None
    except EmailRecipientError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail={"error_code": "EMAIL_RECIPIENT_INVALID", "message": "The address of this account is not a single email address"}) from None
    return EmailVerificationResendResponse(language=language)
