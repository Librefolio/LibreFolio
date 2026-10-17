"""Email administration: the state of the instance's email and the test email (workstream E, lot E2).

What an administrator sees of the email configuration: whether email is off, ready or unusable, the problem and the
variable at fault, the configuration checks of the email section, the hourly budget. Never the host, the port, the
user, the sender nor the password: the SMTP configuration is never shown in the interface (F04).
"""

from typing import Literal, Optional

from pydantic import EmailStr, Field

from backend.app.schemas.common import StrictModel


class EmailCheckRead(StrictModel):
    """One configuration check of the email section, as the admin interface translates it: never its log summary."""

    check_id: str = Field(..., description="email.smtp or email.smtp_encryption")
    severity: Literal["ok", "info", "warning", "error"]
    i18n_key: str = Field(..., description="The key of the message for the admin interface (email.checks.*)")
    detail: dict[str, str | int] = Field(default_factory=dict, description="The parameters of that message; never the host, the user nor the sender")


class EmailBudgetRead(StrictModel):
    """The hourly budget of the instance (LIBREFOLIO_SMTP_MAX_PER_HOUR), per server process."""

    max_per_hour: int = Field(..., description="How many emails the instance may send in an hour")
    remaining: int = Field(..., description="How many more fit in the last hour")
    retry_after_seconds: int = Field(..., description="Seconds until the next email fits; 0 when one fits now")


class EmailLinksRead(StrictModel):
    """Whether emails can carry links: they are built only from LIBREFOLIO_PUBLIC_URL (developer decision 45)."""

    ready: bool = Field(default=False, description="LIBREFOLIO_PUBLIC_URL is set to an address a link can start from: http(s), a host, no credentials, no ? or #")
    base: Optional[str] = Field(None, description="LIBREFOLIO_PUBLIC_URL, the base of every emailed link: the browser checks that it reaches this instance")
    problem: Optional[Literal["PUBLIC_URL_MISSING", "PUBLIC_URL_INVALID"]] = Field(None, description="Why no link can be emailed")


class EmailStatusResponse(StrictModel):
    """``GET /email/status``: the state of the instance's email, for administrators."""

    state: Literal["off", "ready", "invalid"] = Field(..., description="off: no LIBREFOLIO_SMTP_HOST; ready: usable; invalid: a value cannot be used, email stays off")
    problem: Optional[str] = Field(None, description="invalid only: the code of the problem (SMTP_PORT_INVALID, SMTP_FROM_MISSING...)")
    variable: Optional[str] = Field(None, description="invalid only: the environment variable at fault")
    checks: list[EmailCheckRead] = Field(default_factory=list, description="The configuration checks of the email section")
    budget: Optional[EmailBudgetRead] = Field(None, description="ready only: the hourly budget")
    links: EmailLinksRead = Field(default_factory=EmailLinksRead, description="Whether emails can carry links (LIBREFOLIO_PUBLIC_URL)")


class EmailTestResponse(StrictModel):
    """``POST /email/test``: the test email went to the administrator's own address."""

    language: Literal["en", "it", "fr", "es"] = Field(..., description="The language the test email was written in")
    message: str = "Test email sent"


class EmailInstanceConfig(StrictModel):
    """The email part of ``GET /system/instance``: public, the same for whoever asks, never the configuration itself."""

    # One-line docstring on purpose: the API client generator writes a multi-line description as a template literal
    # without escaping its backticks. The default is the instance without email: an answer built without this part
    # says that nothing can be sent.
    available: bool = Field(default=False, description="Whether this instance can send emails now: an SMTP server is set and every LIBREFOLIO_SMTP_* variable can be used")
    links: bool = Field(default=False, description="Whether emails with a link can go out now: email is available and LIBREFOLIO_PUBLIC_URL is set")


class EmailLinkRequest(StrictModel):
    """Email a link an administrator has just created: an invitation, or a password-reset link."""

    purpose: Literal["invite", "password_reset"] = Field(..., description="What the link is for")
    token: str = Field(..., min_length=1, max_length=512, description="The token of the link, as the route that created it answered it; never logged")
    to: Optional[EmailStr] = Field(None, description="invite only: where to send it; without it, the address written in the invitation")
    language: Optional[Literal["en", "it", "fr", "es"]] = Field(None, description="invite only: the language of the email; without it, the instance's default language")


class EmailLinkResponse(StrictModel):
    """``POST /email/links``: the link went out."""

    purpose: Literal["invite", "password_reset"]
    to: str = Field(..., description="Where the email went")
    language: Literal["en", "it", "fr", "es"] = Field(..., description="The language the email was written in")


class PasswordResetEmailRequest(StrictModel):
    """``POST /email/password-reset``: a forgotten password, by username or email address."""

    identifier: str = Field(..., min_length=1, max_length=254, description="The username or the email address of the account")


class PasswordResetEmailAccepted(StrictModel):
    """The same answer whether or not an account matches: if one does, its owner gets an email."""

    message: str = "If an active account matches, its owner gets an email with a link to choose a new password"


class EmailVerificationConfirmRequest(StrictModel):
    """POST /email/verification/confirm: the token of an email-verification link, from its fragment."""

    token: str = Field(..., min_length=1, max_length=256, description="The token of the link, read from #token= in the address")


class EmailVerificationConfirmResponse(StrictModel):
    """The account of the link is active and its address verified: its owner can sign in."""

    username: str = Field(..., description="The username of the account, to fill in the sign-in form")


class EmailVerificationResendRequest(StrictModel):
    """POST /email/verification/resend: the verification link again, with the credentials of the sign-in."""

    username: str = Field(..., min_length=1, max_length=254, description="The username or the email address, as at sign-in")
    password: str = Field(..., min_length=1, max_length=1024, description="The password of the account")


class EmailVerificationResendResponse(StrictModel):
    """A new verification link went to the address of the account; the older ones no longer work."""

    language: str = Field(..., description="The language of the email")
