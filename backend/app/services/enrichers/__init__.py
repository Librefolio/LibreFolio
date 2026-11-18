"""The enrichers (plan 68, wave B): the plugin family that reads an asset's profile from an outside source.

The package re-exports nothing: import every name from the module that defines it.

- ``base.py`` holds ``EnricherPlugin``, the contract every enricher in ``services/enricher_providers/`` follows, with the
  values it exchanges with the core (``EnricherBinding``, ``EnricherRecognition``, ``EnricherReadItem``…).
- ``registry.py`` holds ``EnricherRegistry``, which discovers those plugins and refuses one whose declarations are
  incomplete.
"""
