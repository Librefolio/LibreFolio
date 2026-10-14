"""Accounts section of the configuration.

Owner: workstream A (accounts). Read from the process environment only, never from ``.env``.
"""

import os


def donation_popup_disabled() -> bool:
    """``LIBREFOLIO_DISABLE_DONATION_POPUP``: ``1``, ``true`` or ``yes``, in any case, turns the donation popup off."""
    return os.environ.get("LIBREFOLIO_DISABLE_DONATION_POPUP", "").lower() in ("1", "true", "yes")
