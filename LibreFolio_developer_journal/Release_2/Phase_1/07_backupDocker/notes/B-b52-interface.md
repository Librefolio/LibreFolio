# B · B5-2 — `backup pending --json` and `--recover <choice>`: the interface the red tests pin (23/10/2026)

Base: `1fd80c481`. Requester: the cloud coordinator. Kickoff: `ondata5/kickoff-B.md` item 1. Files: `scripts/backup_cli.py`, optionally a small
read-only helper in `backend/app/services/platform/instance_backup/apply.py`; tests in `utils backup-cli*`.

## The states (what `--json` calls `state`)

| `state` | When | `reason` | `choices` (valid for `--recover`) |
|---|---|---|---|
| `none` | no state file | `null` | `[]` |
| `pending` | `RestoreState.status == "pending"` | `null` (the `waiting` reason, if any, is in `waiting`) | `["cancel"]` |
| `in_progress` | status `applying`, `applied` or `rolling_back` | `null` | `[]` |
| `committed` | status `committed` | `null` | `[]` |
| `rolled_back` | status `rolled_back` | the rollback reason (`first_start_failed`, `swap_interrupted`, `swap_failed`, `stage_missing`) | `[]` |
| `unreadable` | `read_restore` raises `RestoreStateUnreadableError` | its `reason`: `io`, `not_a_file`, `invalid` | `["previous"]` |

## `backup pending --json` (a read)

- stdout is **exactly one line**: a JSON object, `\n` at the end, nothing else, no ANSI colour. Everything the command
  would say otherwise — the emoji lines, the log lines of the modules it calls (structlog prints to stdout by default) —
  goes to **stderr**.
- Keys, always present: `state`, `reason`, `waiting` (`backup_running` | `other_data_directory` | `server_running` |
  `instance_blocked` | `null`), `backup_created_at` (ISO 8601 UTC with `Z`, the waiting/last restore's backup; `null` for
  `none` and `unreadable`), `safety_copy` = `{"present": bool, "at": ISO 8601 UTC `Z` | null}`, `choices` (list of
  strings).
- **Never** a username, an email, a path, a stage id: `confirmed_by`, `data_dir`, `stage_id` are not in the line. A
  test builds a state whose `confirmed_by` is `alice@example.test` and whose data directory has a distinctive name, and
  checks neither string is anywhere in stdout.
- `safety_copy.present`: `.restore/previous/` is a plain folder holding at least one of `SWAPPED_FOLDERS` (the data of
  before a swap); `at`: the readable state's `applied_at`, else the modification time of `.restore/previous/` (UTC,
  whole seconds); `{"present": false, "at": null}` otherwise.
- Exit code **0** whenever the line was printed (an `unreadable` state is a state, not a failure). **2** a usage error
  (argparse, as always); **5** the data directory is missing or the state could not be determined at all (stdout stays
  empty, the cause is on stderr).
- Without `--json`, `backup pending` is unchanged (emoji output, exit 0, or 1 for an unreadable state).

## `backup pending --recover <choice>` (an action)

`--recover` takes a required argument (it was a bare flag in the 1.3 development builds, never released). Exclusive
with `--cancel`; `--cancel` and `--json` cannot go together (argparse error, exit 2; use `--recover cancel`).

- Never asks anything (no prompt, no terminal needed). Choices: `previous`, `cancel`.
- Exit codes (fixed, the same with or without `--json`):
  - **0** done: `previous` put the data of before back (`recover_unreadable_restore`), or `cancel` dropped the waiting
    restore with its copy (`cancel_restore(drop_copy=True)`);
  - **2** usage error (argparse: missing argument, `--cancel` with `--recover`…);
  - **3** nothing to recover: the state is readable-and-none, or `previous` was already done (the unreadable state is
    gone), or `cancel` with no pending restore;
  - **4** the choice is not valid in this state: any choice not in the state's `choices` (e.g. `previous` while the
    state is readable; `cancel` while it is unreadable; an unknown word like `restore`); nothing changes;
  - **5** failed: a server serves the data directory (`restore_in_use`), the move failed (`restore_apply_failed`), an
    `OSError`; nothing is claimed done.
  Precedence when several apply: an unknown choice word → 4; then the state decides: `none` or a state with no valid
  choices and a known word → 3 if the state is `none`, otherwise 4.
- **Idempotent**: running `--recover previous` twice does the work once: the second run exits 3 and changes nothing (no
  folder moved, nothing new in `failed/`, no second `restore.json.unreadable-*`). Same for `cancel`.
- With `--json`, after the action stdout is the same one-line object as above, describing the state **after** the
  action, plus `"recover": {"choice": "<word>", "done": true|false}`, and, when the exit code is not 0, `"error": "<code>"`
  (`nothing_to_recover`, `choice_not_valid`, `restore_in_use`, `restore_apply_failed`, `failed`). Human text on stderr.
- Without `--json`: today's messages on stdout, with the new exit codes; the hints in the messages say
  `--recover previous` (not the bare flag).

## What the existing tests/doc must follow

The B-33 tests and docs call the bare `--recover` (and its 1/0 exits): they become `--recover previous` with the codes
above (`restore_nothing_to_recover` → 3, `restore_in_use` → 5). `backup pending` (no `--recover`) is untouched.
