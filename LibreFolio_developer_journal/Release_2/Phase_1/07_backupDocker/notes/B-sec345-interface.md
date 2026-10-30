# B · SEC-3, SEC-4, SEC-5 and the status 500 — the interface the red tests pin (2026-10-22)

Base: HEAD `b61c3ede3`. Security review: `ondata4/SEC-review-backup-H62.md` (findings 3, 4, 11). Not ours: H's
`panel_restore.py`, `app_lifespan.py`, `instance_block.py`, `features/instance/**`.

## SEC-3 — replaced uploads removed only after the caller accepts the upload (`restore_jobs.py`)

- `UploadWriter.finish(*, replace_others: bool = True) -> RestoreUploaded`: with `replace_others=False` it keeps the
  other finished uploads (it only renames its own file into place); with `True` (the default, the admin route) it
  behaves as today.
- New public `remove_replaced_uploads(data_dir: Path, *, keep: str) -> None` (today's private `_remove_replaced_uploads`,
  same behaviour: never the one a running check reads). H's panel route will call `finish(replace_others=False)`, check
  the kind, then `remove_replaced_uploads(data_dir, keep=upload_id)`.

## SEC-4 — `abort()` leaves nothing after a `finish()` that failed (`restore_jobs.py`)

- `UploadWriter.abort()`: when `finish()` has not returned (it raised, before or AFTER `os.replace`, e.g. in
  `remove_replaced_uploads`), `abort()` removes the partial AND the final file of this upload. After a `finish()` that
  returned, `abort()` removes nothing (the upload is kept). Calling `abort()` twice is harmless.
- The admin route (`PUT /api/v1/backup/restore/upload`, `restore.py`) already calls `abort()` on any exception of
  `_receive`: with a failure of the replaced-uploads removal (monkeypatch it to raise `OSError`), no file of that upload
  is left in `.restore/uploads/` and the answer is the existing `500 backup_upload_failed`.

## SEC-5 — the age key file on the command line (`scripts/backup_cli.py`)

- `inspect|restore|decrypt ARCHIVE.tar --identity-file F`: when F can be read by its group or others (`mode & 0o077`),
  one line starting with `⚠️` names F and its mode in octal (e.g. `0644`) and suggests `chmod 600`; the command goes
  on (a warning, not a refusal). A `0600` file: no such line.
- `backup keygen --identity-file F`: the key is written to a temporary file in F's folder (0600, `O_EXCL`), flushed and
  `fsync`ed, then linked/renamed to F only if F does not exist; on any failure (writing, fsync — monkeypatch to raise)
  exit 1 with a ❌ line, F does not exist and no temporary file is left in the folder. An existing F: unchanged
  behaviour (refused, untouched), and no temporary file left.

## Status — `GET /api/v1/backup/restore/status` 500 with `reason` (`restore.py`)

- The answer to an unreadable state stays `500`, `detail` = `{"code": "restore_state_unreadable", "message": …,
  "reason": "io" | "not_a_file" | "invalid"}` (the `RestoreStateUnreadableError.reason`). The same detail on every
  route of `/backup/restore` that answers `restore_state_unreadable` today (status, confirm, cancel `DELETE pending`,
  restart). The OpenAPI description of that 500 names `reason`. `_state_unreadable` keeps its name; its argument is
  optional (H's route may call it).

## Frontend — the restart page stops polling on an unreadable state

- `backupApi.ts`: `RestoreOutcomeRead` gains `{kind: 'unreadable'; reason: string | null}`. `readStatusWithSession`
  returns it for a `500` whose `detail.code` is `restore_state_unreadable` (`reason` from `detail.reason`, null when
  absent or not a string); any other 500 is still `down`; a body that is not JSON → `down`.
- `restoreFlow.svelte.ts`: `RestartOutcome` gains `'state_unreadable'`; `#settle` on `unreadable` stops polling
  (returns true), clears `slow`/`notStopping`, sets `outcome = 'state_unreadable'` and a new public field
  `unreadableReason` (`string | null`). Emits nothing new.
- `RestartOverlay.svelte`: `state_unreadable` counts as an ended, failed wait (the Back button, as `rolled_back` and
  `still_pending`); the text is the i18n key `backup.restore.restart.stateUnreadable` with `{reason}` (4 languages),
  e.g. EN «The state of the restore cannot be read ({reason}): LibreFolio serves no data until the administrator runs
  ./dev.py backup pending on the server.»; `data-outcome="state_unreadable"`, `data-reason` the reason.
