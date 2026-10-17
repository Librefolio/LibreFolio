"""The «Security» checks of the admin settings (decision of 14/10, point 4).

The configuration checks of ``services/platform/config_audit.py`` evaluated on demand: those the startup audit logs,
contributed by every workstream, and the stored plugin secrets the instance key can no longer read. Each one carries
the key of its message for the admin interface and that message's parameters; never its English log summary, never a
secret value.
"""

from typing import Literal

from pydantic import Field

from backend.app.schemas.common import StrictModel


class SecurityCheckRead(StrictModel):
    """One check, as the «Security» tab translates it."""

    check_id: str = Field(..., description="Stable id, such as accounts.login_limit or platform.jwt_secret")
    severity: Literal["ok", "info", "warning", "error"] = Field(..., description="ok: nothing to do; the tab shows the others")
    i18n_key: str = Field(..., description="The key of the message for the admin interface")
    detail: dict[str, str | int] = Field(default_factory=dict, description="The parameters of that message; never a secret value")


class SecurityChecksResponse(StrictModel):
    """Every check, evaluated now, in the order of the platform's list."""

    items: list[SecurityCheckRead]
