"""Auto-discovered technical signal plugins: one folder per plugin, its code in ``<name>/plugin.py``; the contract is ``base.py``."""

from backend.app.services.signal_plugins.base import SignalPlugin

__all__ = ["SignalPlugin"]
