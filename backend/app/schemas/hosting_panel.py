"""Schemas of the hosting panel's own routes (lot H-61): what an instance tells the panel that runs it."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PanelStatusResponse(BaseModel):
    """``GET /api/v1/panel/status``: the state of the initial administrator's setup, and nothing else.

    No email, no username, no count: the panel learns whether the customer has activated the instance, and until when
    the setup link works.
    """

    model_config = ConfigDict(extra="forbid")

    admin_setup: Literal["none", "pending", "done", "expired"] = Field(
        ...,
        description="none: no setup link was ever issued, or its account no longer exists; pending: a link works; done: the setup was completed, or the account was activated another way; expired: the link expired after 72 hours, or was withdrawn",
    )
    setup_expires_at: datetime | None = Field(None, description="When the pending link stops working, in UTC; null in every other state")
