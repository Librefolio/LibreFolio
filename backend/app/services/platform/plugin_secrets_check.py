"""The startup check of the stored plugin secrets: the ones the instance key can no longer read.

Owner: workstream H (platform), H-15. The plugin settings (workstream X) store their secrets encrypted with a subkey of
the instance key, each row with the ``key_id`` of the key that encrypted it. When the instance key changes (a lost
``secrets/instance.key`` generated again, a backup restored without its ``secrets/`` folder, another
``LIBREFOLIO_INSTANCE_KEY``), those secrets can no longer be read: they must be entered again, or the old key restored.

``plugin_secrets_key_status()`` (X) counts them by ``key_id``, without decrypting, and reads no key at all while no
secret is stored, so a fresh install never generates the key at startup. It needs the database, so this check is not
one of ``CONFIG_CHECKS``, which run before the ``database`` step: ``log_plugin_secrets_check()`` is the startup step
``plugin-secrets-check``, after ``global-settings``. Its result has the shape of the configuration checks
(``config_audit.ConfigCheck``), for the «Security» tab of the admin settings too.

Only the ``system`` count reaches the result, by the rule of workstream X: the secrets of a user are that user's, who
sees them ``unreadable`` in their own settings and enters them again.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_async_engine
from backend.app.logging_config import get_logger
from backend.app.services.platform.config_audit import ConfigCheck
from backend.app.services.plugin_settings.crypto import plugin_secrets_key_status

logger = get_logger(__name__)

CHECK_ID = "platform.plugin_secrets"


async def check_plugin_secrets(session: AsyncSession) -> ConfigCheck:
    """The stored system secrets the instance key cannot read: ``ok`` without any, an ``error`` with their count."""
    status = await plugin_secrets_key_status(session)
    if status.system == 0:
        return ConfigCheck(CHECK_ID, "ok", "instance.checks.pluginSecrets.ok")
    return ConfigCheck(
        CHECK_ID,
        "error",
        "instance.checks.pluginSecrets.unreadable",
        {"count": status.system},
        f"Stored plugin secrets that the instance key cannot read: {status.system}. Enter them again in the plugin settings, or restore the instance key they were saved with",
    )


async def log_plugin_secrets_check() -> None:
    """Startup step ``plugin-secrets-check``: log the check when it is not ``ok``. A check that fails stops nothing."""
    try:
        async with AsyncSession(get_async_engine()) as session:
            result = await check_plugin_secrets(session)
    except Exception as exc:  # noqa: BLE001 — a diagnostic must never stop the start; the class name only, never a value
        logger.warning("Plugin secrets check could not run", error=type(exc).__name__)
        return
    if result.severity == "ok":
        return
    log = {"info": logger.info, "warning": logger.warning, "error": logger.error}[result.severity]
    log(result.summary, check=result.check_id, detail=result.detail)
