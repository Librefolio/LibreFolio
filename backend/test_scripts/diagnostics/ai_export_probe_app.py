"""Minimal production-mode ASGI entrypoint for the AI Export real-prompt probe."""

from backend.app.main import app as main_app
from backend.app.services.signal_runtime import validate_signal_runtime
from backend.app.services.signals.registry import SignalPluginRegistry

validate_signal_runtime()
SignalPluginRegistry.auto_discover()

app = main_app

__all__ = ["app"]
