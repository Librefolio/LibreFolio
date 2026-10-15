"""Plugin settings: values a plugin declares, an administrator or a user sets, and the core hands to the plugin.

The modules, from the leaf up:

- ``fields.py``: what a plugin declares (``PluginSettingField``) and the checks of a declaration and of a value;
- ``contract.py``: the mixin of the family bases (``settings_fields``, ``test_only``, ``settings``) and the values the
  core binds to an instance (``BoundSettings``);
- ``crypto.py``: the encryption of the secret values, and the re-encryption a restore needs;
- ``resolver.py``: the value each field takes (environment, ``_FILE``, stored row, default) and its fingerprint;
- ``runtime.py``: a plugin's rows read from the database, and a configured instance, ready for a call;
- ``service.py``: the catalogue and the writes of ``/api/v1/settings/plugins``.

This package re-exports nothing: import a name from the module that defines it.
"""
