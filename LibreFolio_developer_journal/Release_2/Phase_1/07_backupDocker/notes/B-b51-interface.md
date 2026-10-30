# B · B5-1 — restore of an uploaded backup with the owner's choice: the interface the red tests pin (23/10/2026)

Base: HEAD `acefd8c0d`. Sources: `ondata5/kickoff-B.md` item 3; A's signature
(`side-session-notes/…/A5-2-firma-ripristino-titolare.md`, incl. «Requisito per B»). A's code is NOT in this branch:
tests use a fake `assign_owner_and_send_reset` with A's signature. Panel restores (`panel_restore.py`, H) and the CLI are
out of scope: they never ask nor apply an owner choice.

## 0. When the choice applies

`owner_choice_required()` (new, `instance_backup/owner.py`): `get_settings().LIBREFOLIO_PROFILE == "managed"`. Only
then, and only for a restore confirmed through the administrators' API route (`confirmed_via == "admin"`).

## 1. Staging: the candidates (`staging.py`)

- New model `OwnerCandidate(user_id: int, username: str, email: str | None, is_superuser: bool, is_active: bool)`;
  `StagingReport.owner_candidates: list[OwnerCandidate] = []` (default: a report written before reads `[]`).
- Filled at every check, read-only on the upgraded copy, one parameterised query:
  `SELECT id, username, email, is_superuser, is_active FROM users WHERE (is_superuser = 1 AND is_active = 1) OR
  (? IS NOT NULL AND lower(email) = lower(?)) ORDER BY username`, the parameter being the configured owner email
  (`admin_bootstrap_config().email`, `None` when unset or unreadable; never raises out of the check). Never a SQL built
  with a value. Emails never in a log line.
- `administrators` (usernames) unchanged.

## 2. The API view (`schemas/backup.py`, `restore.py`)

- `RestoreStageReport.owner_choice: RestoreOwnerChoice | None` — `None` outside `managed`. In `managed`:
  `{"required": true, "owner_email": "<configured>", "forced_user_id": <id> | null, "candidates": [{"user_id", "username",
  "email", "owner_email": bool, "administrator": bool}]}` where `owner_email` = `same_email(candidate.email, configured)`
  (`user_service.same_email`), `administrator` = `is_superuser and is_active`, `forced_user_id` = the candidate whose
  email is the owner's (there is at most one: unique `lower(email)`), else `null`.
- `owner_choice` is only in the administrators' route view. Never in `backup pending --json`, never in the panel's
  report (H's closed schema), never logged.

## 3. Confirmation (`restore.py`, `restore_jobs.py`, `apply.py`)

- `POST /api/v1/backup/restore/stage/{stage_id}/confirm` takes an optional JSON body `RestoreConfirmRequest`
  `{"owner_user_id": int | null}` (`extra="forbid"`; no body = `null`).
- `restore_jobs.confirm_check(stage_id, *, confirmed_by, confirmed_via="admin", owner_user_id=None, data_dir=None)` and
  `apply.confirm_restore(…, owner_user_id=None, …)`. In `confirm_restore`, after the report is read and before the state
  is written, when `confirmed_via == "admin"` and `owner_choice_required()`:
  - `owner_user_id is None` → `RestoreOwnerChoiceRequiredError` (code `owner_choice_required`, 409 at the route);
  - no configured owner email → `RestoreOwnerEmailNotSetError` (`owner_email_not_set`, 409);
  - `owner_user_id` not among the report's candidates that are (administrator) or (owner email) → or a forced user exists
    and `owner_user_id` is another one → `RestoreOwnerChoiceInvalidError` (`owner_choice_invalid`, 409);
  - nothing written in any of these cases.
- Outside `managed`, or for `confirmed_via` `cli`/`panel`: `owner_user_id` given to the admin route outside managed →
  `owner_choice_not_applicable` (400 at the route, nothing written); `cli`/`panel` never pass one.
- `RestoreState` gains `owner_user_id: int | None = None`, `owner_outcome: str | None = None` (one of A's outcomes, or
  `error:<CODE>`), `owner_reset_path: str | None = None` (only for `link_only`). `owner_reset_path` is a secret: never in
  `RestoreStatus`, the outcome route, `pending --json`, the panel status, any log line.
- `RestoreStatus` (admin) gains `owner_outcome: str | null` (not the id, not the path).

## 4. After the swap, at the first start (`instance_backup/owner.py`)

`async def assign_restored_owner(data_dir: Path | None = None) -> RestoreState | None` — the startup step
`restore-owner`, right after `restore-commit` (the line in `app_lifespan.py` is H's, requested). Never raises.
- Reads the state; does nothing (returns `None`) unless `status == "committed"`, `confirmed_via == "admin"`,
  `owner_user_id is not None` and `owner_outcome is None`.
- Calls A's `assign_owner_and_send_reset(session, owner_user_id)` with an `AsyncSession(get_async_engine(),
  expire_on_commit=False)`; A commits. The function is looked up through `owner._assign_owner()` (lazy import of
  `backend.app.services.email.flows`), so tests replace it, and an `ImportError` (A not merged) logs an error and leaves
  the state pending.
- Records under the apply lock: `owner_outcome = result.outcome` (string value), `owner_reset_path = result.reset_path`
  only for `link_only`; on `OwnerAssignmentError` `owner_outcome = "error:<code>"` (logged with the code only); any
  other exception → logged (type only), state left pending: the next start calls again (A is idempotent:
  `already_issued`).
- Idempotent: a second call after a recorded outcome does nothing; a crash between A's commit and the record → the
  next start calls A again and records `already_issued`.
- Log lines: the stage id, the user id, the outcome; never the email, the username, the reset path.

## 5. CLI (`backup pending`, human output only)

A committed restore with `owner_outcome` prints one line: `sent` → the link went to the owner's mailbox; `link_only` →
the link (from `owner_reset_path`) with «give it only to the owner»; `already_*` → nothing to do; `error:*` → the code and
what to do; pending (None) → «the owner's account is set at the next start». `--json` unchanged (none of this).

## 6. Frontend (later, with A's modal)

The restore report shows A's modal when `report.owner_choice` is present; confirm sends `{owner_user_id}`. Mounted
after A's branch is merged (A's props unknown today).

## 7. Addendum after the independent security review (23/10) — the interface the second red tests pin

Review findings addressed here (2 = fail-open forced by the backup, 3, 4, 5, 7); 1 (the step's wiring) and the
fail-closed guard are H's, with the hook of §7.4.

### 7.1 Staging: the owner's conflicts and robust rows (`staging.py`)
- `StagingReport.owner_email_checked: str | None = None`: the owner's address the check used (`configured_owner_email()`
  at that time), so the confirmation sees whether it changed.
- `StagingReport.owner_conflicts: list[str] = []`, codes (sorted, unique), computed on the copy, read-only, bound values:
  - `duplicate_email`: two accounts share `lower(email)` (a copy without the unique index);
  - `duplicate_username`: two accounts share `lower(username)`;
  - `address_is_a_username`: the owner's address (when set) is the username, case-folded, of an account other than
    the one whose email is the owner's (A's `address_is_a_username` rule: A's assignment would refuse).
- Rows: an account whose `id` is not an integer, or whose `username` is NULL, makes the check fail with
  `database_damaged` (never a generic `stage_failed`, never a crash), whatever the query that meets it.
- Never an address or a username in a log line.

### 7.2 Confirmation (`apply.confirm_restore`, only `confirmed_via == "admin"` on managed, after §3's checks order)
- The current owner address differs (`email_fold`) from `report.owner_email_checked`, or the report has none (written
  before) → `RestoreStageOutdatedError` (`restore_stage_outdated`, 409: «check the archive again»). Checked before the
  choice itself.
- `report.owner_conflicts` not empty → new `RestoreOwnerConflictError` (code `owner_conflict`, 409), whatever the choice.
- Nothing written on any refusal.

### 7.3 One worker calls A (`owner.py`)
- `assign_restored_owner` takes a non-blocking exclusive `flock` on `.restore/owner.lock` (created 0600) before calling
  A and holds it until the record is written; a worker that cannot take it returns `None` without calling A (the other
  worker does it). Re-checks `owner_pending` once the lock is held.

### 7.4 The hook for H's guard (`apply.py`)
- `owner_assignment_problem(data_dir: Path | None = None) -> str | None`: for the last restore — committed, confirmed
  from the app, `owner_user_id` set — `"pending"` while `owner_outcome` is None, the code (e.g. `"EMAIL_TAKEN"`) when it
  is `error:<CODE>`; `None` otherwise (no such restore, an outcome of A recorded, a state that cannot be read: that one
  is `restore_state_problem`'s). Never raises. H's restore guard serves no data while it is not None (H's part).

### 7.5 The chosen account closed at the commit (`apply._close_the_way_in`, step `restore-commit`) — agreed with A (23/10)
Closes review finding 2 for the case «A's call never comes»: from the first request on the restored data, whoever
prepared the backup cannot sign in as the chosen account.
- `_close_the_way_in(data_dir, now, owner_user_id: int | None = None) -> tuple[int, int]` (return unchanged);
  `finish_pending_restore` passes `state.owner_user_id`. Restores without one (panel, CLI, self-hosted): exactly as
  today, no account's password touched.
- With `owner_user_id`, in the SAME transaction as the session versions and the revoked links:
  - `hashed_password` of that account = `auth_service.hash_password(secrets.token_urlsafe(32))`: a real bcrypt hash of
    a secret nobody sees (A's `unusable_password_hash()` once merged), computed before the transaction. Afterwards
    `verify_password(<the backup's password>, stored)` is False and the stored hash differs from the backup's.
  - when `configured_owner_email()` is set and NO OTHER account has `lower(email) = lower(<owner address>)`: that
    account's `email` = the owner address, `is_superuser = 1`, `is_active = 1`, and `is_instance_owner = 1` only when
    the column exists (`PRAGMA table_info(users)`; A's migration 006, absent in this branch: skipped, no error).
  - another account holds the address: only the password; a warning (stage id, user id; never the address). A's call
    later refuses (`EMAIL_TAKEN`) and H's guard sees it through §7.4.
  - the address not set: only the password.
  - no account with that id in the restored database: nothing for the owner, a warning, the commit goes on.
- Never fails the commit because of the owner: the unique index is never violated (checked first, same transaction).
- Log: one line «owner account closed» with stage id, user id, `assigned: bool`; never the address, the name, a hash.
- A's later call is unaffected (A checks tokens, not the hash; every live link was revoked by this same commit, so A
  issues a new one).

## 8. Frontend B5-1b — the interface the Vitest reds pin (23/10)

Folder `frontend/src/lib/features/backup/`. API types from `$lib/api/generated` (already synced):
`RestoreStageReport.owner_choice?: {required, owner_email, forced_user_id: number|null, candidates: [{user_id, username,
email: string|null, owner_email: boolean, administrator: boolean, is_superuser, is_active}]} | null`.

- `backupApi.confirmRestore(stageId, ownerUserId: number | null = null)`: POST body `{owner_user_id: ownerUserId}` (done).
- `RestoreApi.confirm(stageId: string, ownerUserId?: number | null)`; `RestoreFlow.confirm(ownerUserId: number | null =
  null)` passes it to `api.confirm(stage_id, ownerUserId)` unchanged (`null` when not given). Nothing else changes.
- Refusals at the confirmation, new codes: `owner_choice_required`, `owner_choice_invalid`, `owner_email_not_set`
  (check kept: `retry()` brings the report back) and `owner_conflict` (joins `CHECK_GONE`: the check is forgotten, as for
  `restore_not_restorable`). Each fails with `'confirm'` and its code.
- `restoreText.restoreErrorKey(code)` for the 4 codes → `backup.restore.errors.<code>`, the same keys in the four
  catalogues (restoreI18n.test.ts list «an error of a request»). `restore_stage_outdated`'s text also names the owner's
  address changing (text only, key unchanged).
- `RestoreReportModal`: `onConfirm: (ownerUserId: number | null) => void`.
  - `report.owner_choice` null/absent: as today, the word typed then «confirm» → `onConfirm(null)`; no owner modal.
  - present: «confirm» (same word rule) does NOT call `onConfirm`; it opens `OwnerChoiceModal` (testid
    `owner-choice-modal`) with `ownerEmail = owner_choice.owner_email` and `users` =
    - only the candidate whose `user_id === forced_user_id` when that is not null;
    - otherwise the candidates with `administrator === true`;
    each mapped `{id: user_id, username, email: email ?? '', is_superuser, is_active}`; `busy` passed through.
    Its `onConfirm(id)` → the owner modal closes and `onConfirm(id)` is called once. Its `onCancel` → it closes, nothing
    confirmed, the report stays open with the typed word.
- `RestoreCard`: `onConfirm={(ownerUserId) => controller.confirm(ownerUserId)}`.
- `OwnerChoiceModal.svelte`: a STAND-IN with A's props and testids (A's file: replaced whole at the merge). Tests drive it
  only through A's testids: `owner-choice-option[data-user-id]` click selects, `owner-choice-confirm`, `owner-choice-cancel`,
  `data-locked`, `data-selected`.

## 9. B5-1b — `backup pending --recover owner` (24/10, request of the coordinator)

Gap (found by H): an `owner_outcome` of `error:<CODE>` is terminal (`owner_pending` does not retry; `--recover previous` only
cures an unreadable state), so the instance stays closed (H's guard, `owner_assignment_problem() != None`) with no remedy.

### 9.1 Core (`apply.py`, `owner.py`)
- New `RestoreOwnerNotFailedError(RestoreStateError)`, code `owner_not_failed`: «there is no failed owner assignment to try again».
- `owner.held_owner_lock(data_dir) -> contextmanager yielding bool`: the non-blocking exclusive `flock` on `.restore/owner.lock`
  (same file and mode as the startup step); `False` when another process holds it. Never raises for a held lock.
- `apply.reset_owner_assignment(data_dir: Path | None = None) -> bool`: takes `owner.lock` (not held → `RestoreInUseError`),
  then `_apply_lock`, then probes the serving lock (as `recover_unreadable_restore` does; holding it exclusive only for the call).
  Lock order is always owner lock → apply lock (the startup step does the same).
  - State must be `committed`, `confirmed_via == "admin"`, `owner_user_id` set, `owner_outcome` a string starting with `error:`.
    Otherwise `RestoreOwnerNotFailedError`, nothing written (also: no `.restore` folder, no state).
  - Writes the state with `owner_outcome = None` and `owner_reset_path = None`. Nothing else changes. Returns whether a server
    serves the data directory. Logs one line (stage id, user id, the code that was reset); never an address, name or link.
  - Idempotent: a second call finds `owner_outcome` None → `RestoreOwnerNotFailedError`.
  - A state that cannot be read propagates `RestoreStateUnreadableError`.

### 9.2 CLI (`scripts/backup_cli.py`)
- `RECOVER_CHOICES = ("previous", "cancel", "owner")`; `--recover` help names `owner`.
- `_pending_snapshot`: a `committed` state confirmed from the app, with an owner named and an outcome starting `error:` →
  `state: "committed"`, `reason: "owner_assignment"`, `choices: ["owner"]`. Every other committed state: `reason: null`, `choices: []`
  as today. No code, name, id or link in the snapshot.
- `--recover owner`:
  - not offered by the state (anything but the case above, incl. no state) → exit 4 `choice_not_valid` (no state at all keeps
    exit 3 `nothing_to_recover`), message as for the other choices; nothing changes.
  - offered: `reset_owner_assignment`. Held `owner.lock` → exit 5 `restore_in_use`. Any `RestoreOwnerNotFailedError` (someone reset it
    meanwhile) → exit 3 `nothing_to_recover`. `OSError`/`BackupPathError` → exit 5 `failed`.
  - a server serves the data directory: the outcome is cleared, nothing is called; exit 0, one `✅` line saying the owner's
    account is set when LibreFolio starts again (a running server only retries at its start).
  - nobody serves: right after the reset it runs `asyncio.run(owner.assign_restored_owner(data_dir))` and reads the state:
    - outcome recorded and not `error:` → exit 0, and the same line `_print_owner_outcome` prints for that outcome (including the
      `link_only` line with the link, to stdout only; with `--json` everything printed goes to stderr as today);
    - outcome `error:<CODE>` again → exit 5 `owner_assignment_failed`, a `❌` line with the code;
    - no outcome recorded (A's function missing, a transient failure) → exit 0, `⏳` line: it is set at the next start.
  - never a link, name, address or id in the JSON line. `recover: {"choice": "owner", "done": bool}`, `error` as for the others.
- `_print_owner_outcome`: the `error:` line gains the way out, on the same line:
  `…: the server log has the cause; ./dev.py backup pending --recover owner tries again`.
