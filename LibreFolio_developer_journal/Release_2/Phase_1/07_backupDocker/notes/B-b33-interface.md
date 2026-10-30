# B · B-33 (part without H): an unreadable restore state — the interface the red tests pin (2026-10-22)

Developer decision (backlog B-33, 🌊): an unreadable state never serves the data; a page «restore interrupted, the
administrator is needed» (H-62's mode, later); `dev.py backup pending` says what happened; the administrator chooses on
the command line between the data of before and a new restore. This lot does the reading, the protection of the
copies, the CLI and the hook for H. NOT the startup block, NOT the page, NOT `GET /status`'s code (proposed only).

Files: `backend/app/services/platform/instance_backup/apply.py`, `restore_jobs.py`, `scripts/backup_cli.py`.

## 1. Reading (`apply.py`)

Today `_read_state` gives `None` for «none» AND for a state file that is a link/folder or not valid JSON of a state
(§10, «ignored»), and raises `RestoreStateUnreadableError` only for an `OSError`. From now on:

- **None** only when there is no state file (`.restore` absent, or `restore.json` absent). A `.restore` that is a link
  or a file stays as today (`_restore_folder` False: ignored, `restore_folder_unusable` where it already is).
- **`RestoreStateUnreadableError`**, with a new attribute `reason: Literal["io", "not_a_file", "invalid"]`, for:
  an `OSError` reading it (`io`, as today); `restore.json` a link, a folder, a FIFO… (`not_a_file`); content that is not
  a state this LibreFolio reads — not JSON, wrong fields, `format` other than 1 (`invalid`). Logged once, as today.
- `read_restore(data_dir)` raises it in all three cases (callers that already catch it — confirm, cancel,
  prepare_restart, the routes, the CLI — now also refuse for `not_a_file`/`invalid`, never write over it).
- Startup (`_state_at_start`, used by `apply_pending_restore` and `finish_pending_restore`): UNCHANGED behaviour for now
  (logs, returns None, the start goes on). H-62 adds the block using §4.
- New public `restore_state_problem(data_dir: Path | None = None) -> RestoreStateUnreadableError | None`: the error a
  read would raise, or None when the state is readable or absent. Never raises. (§4: the hook for H.)

## 2. Protection of the copies

- `protected_stage(data_dir)`: unchanged for a readable state; with an unreadable state it returns the new constant
  `EVERY_STAGE = "*"` (no stage id can equal it): which copy a restore waits for is unknown, so no copy is touched.
- `restore_jobs.remove_check(stage_id)`: with `EVERY_STAGE`, refuses with `CheckPendingError` (as for the protected
  stage today) for every check whose copy exists.
- `restore_jobs.prune(...)`: with `EVERY_STAGE`, removes no stage copy and no check of a stage, however old (uploads and
  stray decrypted archives may still go, as today).
- Starting a new check is NOT blocked by this (only confirm is, by §1).

## 3. CLI (`scripts/backup_cli.py`)

- `dev.py backup pending` with an unreadable state: exit 1; prints `❌ The state of the restore cannot be read
  (<reason>): a restore may have stopped half way. LibreFolio serves no data until you choose (restore_state_unreadable)`
  — exact wording free, but the line has the code `restore_state_unreadable` and the reason word (`io`, `not_a_file`,
  `invalid`); then what is on disk: whether `.restore/previous/` exists and which of the swapped folders
  (`SWAPPED_FOLDERS`) it holds, and how many checked copies are kept; then the command to run:
  `./dev.py backup pending --recover`. Never prints a path's content.
- `dev.py backup pending --recover` (new, exclusive with `--cancel`):
  - refuses while a server serves the data directory (the exclusive serving lock cannot be taken): exit 1, a ❌ line,
    nothing moved;
  - with a readable state or none: exit 1, `❌ Nothing to recover: …` (use `--cancel` / nothing to do), nothing moved;
  - with an unreadable state, under `_apply_lock` and the exclusive serving lock: puts the data of before back **from
    what the files say** (the journal is in the unreadable state): for each folder of `SWAPPED_FOLDERS` present in
    `.restore/previous/`: the live one, if present, goes to `.restore/failed/<folder>` (the restored copy's), then
    `previous/<folder>` moves back into place; a folder absent from `previous/` stays as it is. Then the state file is
    renamed `restore.json.unreadable-<YYYYMMDDTHHMMSSZ>` (kept for diagnosis, never read again) and no new state is
    written: `backup pending` then says nothing waits. Prints what it moved and that the instance now holds the data of
    before; to restore a backup instead, run `./dev.py backup restore ARCHIVE` next. Exit 0.
  - the outcome is idempotent: a second `--recover` finds no unreadable state (exit 1, nothing to recover).
- New apply function the CLI calls: `recover_unreadable_restore(data_dir: Path | None = None) -> RecoveredRestore`
  (frozen dataclass: `moved_back: tuple[str, ...]`, `set_aside: tuple[str, ...]` (the live folders sent to `failed/`),
  `state_kept_as: str` (the new file name)); raises `RestoreInUseError` when a server serves the directory,
  `RestoreNotPendingError`-like `RestoreNothingToRecoverError` (new, code `restore_nothing_to_recover`) when the state is
  readable or absent.

## 4. For H-62 (written in the checkpoint, not built here)

At startup, before `pending-restore`: `apply.restore_state_problem(data_dir)` not None → the instance enters H's
«restore interrupted» mode (serves no data; page «restore interrupted, the administrator is needed»;
`GET /api/v1/panel/status` → whatever the cloud contract decides). Leaving it: `dev.py backup pending --recover`, then a
restart.

## 5. `GET /api/v1/backup/restore/status` (proposal only, not built)

Today `500 restore_state_unreadable`, which the restart overlay takes for «server down». Proposal: `409
restore_state_unreadable` with `reason` (`io`/`not_a_file`/`invalid`) in the detail and the message «run ./dev.py backup
pending on the server»; the overlay stops polling and shows it.
