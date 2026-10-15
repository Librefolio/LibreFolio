"""Backup of the whole instance (F01): a zip of the data directory, with a manifest.

Owner: workstream B (plan ``Release_2/Phase_1/07_backupDocker``). The modules, each a step of the work:

- ``paths``: what an archive carries, and where backups are written in the data directory;
- ``snapshot``: the consistent copy of the database (``VACUUM INTO``), never the live file;
- ``manifest``: the description of an archive, written as its last entry and read back to check it;
- ``archive``: builds the archive and checks one;
- ``jobs``: runs a backup in the background for the API, one at a time across workers, with its state on disk.

The per-series exports of the backup API are a different thing: ``services/platform/series_export.py``.
"""
