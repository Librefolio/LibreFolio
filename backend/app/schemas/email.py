"""Email administration: the state of the instance's email and the test email (workstream E, lot E2).

What an administrator sees of the email configuration: whether email is off, ready or unusable, the problem and the
variable at fault, the configuration checks of the email section, the hourly budget. Never the host, the port, the
user, the sender nor the password: the SMTP configuration is never shown in the interface (F04).
"""

from typing import Literal, Optional

from pydantic import Field

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


class EmailStatusResponse(StrictModel):
    """``GET /email/status``: the state of the instance's email, for administrators."""

    state: Literal["off", "ready", "invalid"] = Field(..., description="off: no LIBREFOLIO_SMTP_HOST; ready: usable; invalid: a value cannot be used, email stays off")
    problem: Optional[str] = Field(None, description="invalid only: the code of the problem (SMTP_PORT_INVALID, SMTP_FROM_MISSING...)")
    variable: Optional[str] = Field(None, description="invalid only: the environment variable at fault")
    checks: list[EmailCheckRead] = Field(default_factory=list, description="The configuration checks of the email section")
    budget: Optional[EmailBudgetRead] = Field(None, description="ready only: the hourly budget")


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
