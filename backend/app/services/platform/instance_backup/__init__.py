"""Backup of the whole instance (F01): a zip of the data directory, with a manifest.

Owner: workstream B (plan ``Release_2/Phase_1/07_backupDocker``). The modules, each a step of the work:

- ``paths``: what an archive carries, and where backups are written in the data directory;
- ``snapshot``: the consistent copy of the database (``VACUUM INTO``), never the live file;
- ``manifest``: the description of an archive, written as its last entry and read back to check it;
- ``archive``: builds the archive and checks one;
- ``jobs``: runs a backup in the background for the API, one at a time across workers, with its state on disk;
- ``staging``: checks an archive for a restore, on a copy brought to this LibreFolio's revision (lot B2);
- ``restore_jobs``: the upload of an archive and its check in the background, for the API (lot B2b);
- ``apply``: a checked restore confirmed, then applied at the next start, or undone when that start fails (lot B3);
- ``restart``: stops the server so that its next start applies a confirmed restore (lot B3).

The per-series exports of the backup API are a different thing: ``services/platform/series_export.py``.
"""
