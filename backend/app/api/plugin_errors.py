"""The API's answer about a plugin's configuration, one shape for every family (plan 68 B2b, project 76 N2).

A call that needs a plugin whose required setting is empty is refused with the app's coded error: 422, ``error_code``
and ``message``, as the other coded refusals (``api/v1/email.py``), plus ``missing``, the fields to set. ``missing`` is
what a caller may be told (``plugin_settings.readiness.PluginReadiness.missing``: in the managed profile a field an
environment variable locks is not named), so the interface reads providers and enrichers the same way.
"""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import HTTPException, status

#: The error code of a call refused because a required setting of the plugin is empty.
NOT_CONFIGURED = "NOT_CONFIGURED"


def not_configured_error(plugin_code: str, missing: Sequence[str]) -> HTTPException:
    """The 422 of a call to ``plugin_code`` while ``missing`` (the fields a caller may be told) are not set."""
    keys = list(missing)
    named = ", ".join(keys) if keys else "a required setting"
    detail = {"error_code": NOT_CONFIGURED, "message": f"'{plugin_code}' is not configured: {named} missing", "missing": keys}
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
