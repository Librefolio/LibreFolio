"""Test-only SignalPlugin implementations; never scanned by production registry."""

from backend.test_scripts.fixtures.signal_plugins.registry import (
    FixtureSignalPluginRegistry,
)

__all__ = ["FixtureSignalPluginRegistry"]
