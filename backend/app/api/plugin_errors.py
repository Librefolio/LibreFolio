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

#: The error code of a write refused because the plugin settings could not be read (project 76, N2b): retry.
PLUGIN_SETTINGS_UNAVAILABLE = "PLUGIN_SETTINGS_UNAVAILABLE"


def not_configured_error(plugin_code: str, missing: Sequence[str], *, reason: str = "missing_fields", variables: Sequence[str] = ()) -> HTTPException:
    """The 422 of a call to ``plugin_code`` while ``missing`` (the fields a caller may be told) are not set.

    ``reason`` (N2b) says what the interface can offer: ``missing_fields`` (set them: Configure, or ask an
    administrator) or ``invalid_locked_setting`` (an environment variable that locks a field has an invalid value: fixed
    on the server); ``variables`` names those variables, outside the managed profile only
    (``PluginReadiness.reason``/``variables``).
    """
    keys = list(missing)
    named = ", ".join(keys) if keys else "a required setting"
    detail = {"error_code": NOT_CONFIGURED, "message": f"'{plugin_code}' is not configured: {named} missing", "missing": keys, "reason": reason, "variables": list(variables)}
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)


def settings_unavailable_error() -> HTTPException:
    """The 503 of a write that needs to know whether a plugin is configured while its settings could not be read (a
    database error): nothing written, retry (N2b)."""
    detail = {"error_code": PLUGIN_SETTINGS_UNAVAILABLE, "message": "The plugin settings could not be read: nothing was saved, try again"}
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
