"""Schemas of the instance backup (``/backup/instance``): the state of a backup job."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class InstanceBackupJob(BaseModel):
    """A backup of the whole instance, built in the background: poll it until ``status`` is ``done`` or ``failed``.

    ``done_bytes`` of ``total_bytes`` measure the bytes read so far; ``total_bytes`` is 0 until the database is copied.
    ``warnings`` are stable codes: ``database_integrity`` (the database failed its integrity check),
    ``foreign_key_violations``, ``files_skipped`` (files that changed or vanished during the backup, left out).
    ``error_code``: ``backup_no_space``, ``backup_failed`` (the server log has the cause) or ``backup_interrupted`` (the
    server stopped during the backup).
    """

    model_config = ConfigDict(extra="forbid")

    job_id: str
    status: Literal["running", "done", "failed"]
    phase: Literal["preparing", "database", "files", "finalizing"] | None = None
    done_bytes: int = Field(ge=0)
    total_bytes: int = Field(ge=0)
    created_at: datetime
    finished_at: datetime | None = None
    file_name: str | None = None
    file_size: int | None = Field(default=None, ge=0)
    warnings: list[Literal["database_integrity", "foreign_key_violations", "files_skipped"]] = []
    error_code: Literal["backup_no_space", "backup_failed", "backup_interrupted"] | None = None
