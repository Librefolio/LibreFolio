"""The asset profile (plan 68): the descriptive facts of an asset, each with its source and its history.

The package re-exports nothing: import every name from the module that defines it.

- ``catalogue.py`` lists every voice of the profile (``CATALOGUE``) and turns a raw value into the form stored in
  ``asset_profile_updates.value`` (``normalize_value``); a voice it does not list, or a value of the wrong shape, is
  refused with ``ProfileValueError``.
- ``store.py`` writes a voice only when it changes and reads the profile as steps over a date range; it forgets rows
  and lists the changes (``asset_profile_updates``).
"""
