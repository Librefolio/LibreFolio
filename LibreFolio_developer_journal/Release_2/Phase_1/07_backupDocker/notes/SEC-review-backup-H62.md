# Security review — backup L3 + panel restore (H-62)

Worktree `e-alfy-sturdy-memory`, branch `e-alfy-h-piattaforma`, HEAD `14cd6a91f`, diff against merge-base `c042f2481`.
Read-only review. Paths are relative to `LibreFolio-worktrees/e-alfy-sturdy-memory/`.

**Verdict: no HIGH or MEDIUM issue found.** The ticket-only scope, the order of the checks, the R1 redaction and the
awaiting-restore gate hold. All findings below are LOW or INFO: robustness, gaps against the contract, hardening.

## Findings (ranked)

### 1. LOW — the clear zip stays on disk while the backup is sealed: peak 3x, contract says 2x
`backend/app/services/platform/instance_backup/jobs.py:384-392` (`_protect`) and `:372-381` (`_encrypt`: "the archive
is left to the clean-up").
- **Scenario:** for a sealed panel job, `_encrypt` writes the `.lfbk` and leaves the clear zip. `_seal` then writes the
  `.tar`. The zip is removed only by `_remove_work_files` in the `finally` of `_run`. During sealing the job folder holds
  the zip, the `.lfbk` and the `.tar` together.
- **Outcome:** disk peak is about 3x the archive, not the 2x of contract §4. On a 1 GB volume, nightly jobs fail with
  `backup_no_space` sooner. The clear zip, which holds every user's data, also stays on disk longer.
- **Fix:** in `_protect`, when `recipients` is set, unlink `folder / name` after `_encrypt` returns and before `_seal`.

### 2. LOW — the sealed-tar reader accepts data after the end-of-archive marker
`backend/app/services/platform/instance_backup/sealed.py:199-220` (`_members`).
- **Scenario:** the loop stops at the first all-zero block. It never checks the second zero block, or that only zeros
  follow. Verified with a probe on the fixture (scratch copies only):
  - 3 valid members, one zero block, then a 4th ustar member `evil.sh`: accepted.
  - 100 garbage bytes appended: accepted.
- **Outcome:** this breaks "esattamente tre membri" (§3.5) and differs from a strict coordinator reader. GNU `tar xf`
  also stops there, with only a "lone zero block" warning, but `tar xif` in the §8 emergency path would extract the
  hidden member. Only the CLI uses this reader, so the impact is small.
- **Fix:** after the first zero block, require a second zero block, and require zeros up to EOF (or up to the next
  10240-byte boundary).

### 3. LOW — a refused panel upload is written whole, and first deletes the previous good upload
`backend/app/api/v1/backup/panel_restore.py:147-158` with `restore_jobs.py:189-214` (`UploadWriter.finish` calls
`_remove_replaced_uploads` before the route checks `kind`).
- **Scenario:** a ticket holder PUTs a clear zip or the `.tar`.
- **Outcome:** the whole body is written to `.restore/uploads/` (in clear for a zip), up to the limit. `finish()` deletes
  the previous valid `.lfbk` upload. Only then does the route refuse with `restore_envelope_required` and unlink the
  file. It never leaks data, because the caller holds the ticket. But D2 is enforced after the fact, and a failed
  retry destroys the good upload.
- **Fix:** check the first 4 bytes for `LFBK` in `_receive` (or in a panel-specific writer) before writing more. Remove
  replaced uploads only after the kind check passes.

### 4. LOW — an orphan upload can be left when `finish()` fails after the rename
`backend/app/services/platform/instance_backup/restore_jobs.py:203-212`, used by `panel_restore.py:146-153`. Shared with
the admin route.
- **Scenario:** `os.replace(partial, final)` succeeds, then `_remove_replaced_uploads` raises an `OSError` (iterdir or
  unlink). The route's `except BaseException` calls `writer.abort()`. `_fd` is already `None` and the partial file is
  gone, so `abort()` removes nothing.
- **Outcome:** the final upload stays on disk with no `upload_id` returned. For the admin route, that file can be a
  clear zip. It stays until the next upload replaces it or until prune at startup.
- **Fix:** in `abort()`, also unlink `self._final` when `finish()` did not return. Or move the replaced-upload cleanup
  into a best-effort `try` that logs.

### 5. LOW — the idempotency of `POST stage` races
`backend/app/api/v1/backup/panel_restore.py:180-190`.
- **Scenario:** two identical starts arrive at the same time. Both see `running_check(...)` return `None` before either
  has written its state. One takes the lock, the other gets `StagingBusyError`.
- **Outcome:** `409 restore_busy` instead of the `202` with the same stage that §5 promises. This is not a security
  issue. It matters only if the coordinator treats 409 as fatal.
- **Fix:** on `StagingBusyError`, call `running_check(body.upload_id)` again. If it now returns a panel check, answer it.

### 6. LOW — a retried `restart` during shutdown sends a second SIGTERM
`backend/app/api/v1/backup/panel_restore.py:274-294`.
- **Scenario:** the panel retries `POST restart` after losing the first response. The state is still `pending` until
  the next start runs `pending-restore`, so `prepare_restart` succeeds again and a second SIGTERM is scheduled.
- **Outcome:** §5 promises "no second SIGTERM" only for `in_progress`/`committed`, so this matches the letter of the
  contract. Uvicorn treats a repeated SIGTERM as a no-op. **Not verified:** how the arming handler of
  `shutdown_budget.install_shutdown_watchdog` reacts to a second signal.
- **Fix (optional):** a process-level "restart already requested" flag, so a retry answers 202 without signalling.

### 7. INFO — panel `status`/`restart`/`cancel` act on the global restore, not only on panel stages
`panel_restore.py:274-327`.
- `confirm` and `GET stage` are scoped to `origin == "panel"`. The pending restore itself is global.
- So in awaiting-restore mode the panel can restart, or `DELETE …/pending`, a restore confirmed through the CLI. The
  username is never exposed (`PanelRestoreStatus.of` drops `confirmed_by`).
- Probably acceptable, since the ticket is the restore authority. Document it, or refuse `cancel` when
  `confirmed_via != "panel"`.

### 8. INFO — the mode gate relies only on `LIBREFOLIO_AWAIT_RESTORE`
`panel_restore.py:81-87`. The module docstring says "never write over the data of an instance that runs". That is true
only if the coordinator never sets the variable on a populated volume: nothing checks that the volume is empty.
Consistent with §6 (the mode is the coordinator's decision). Consider wording the docstring that way.

### 9. INFO — error-handling notes
- `panel_restore.py:202,258,290,325` log `OSError` with `strerror` and no `exc_info`. This is the AP-API-12 pattern
  already used by the admin `restore.py`, and `server_errors.py` then skips the second log line. It does not follow the
  "exc_info" wording of the project rule, but no path or stack reaches the client.
- `panel_restore.py:156`: the `unlink` in the D2 branch is not guarded. An `OSError` there becomes Starlette's generic
  500, which is safe.
- `_upload_limit()` answers 503 `backup_upload_unavailable`, but the panel OpenAPI `_GATE_RESPONSES` documents only
  `backup_restore_unavailable`. This is a documentation mismatch.

### 10. INFO — the JSON body is read before the ticket check (generic FastAPI behaviour)
For `POST /panel/restore/stage`, FastAPI reads and parses the JSON body before it solves dependencies, so an
unauthenticated caller can make the server buffer an arbitrary JSON body. This holds for every JSON route of the app
and is not new in H-62. The raw `PUT upload` is not affected: it is streamed only after the ticket. A global body-size
limit, in middleware or the proxy, would cover it.

### 11. INFO — CLI hardening
`scripts/backup_cli.py`:
- `read_identities` does not warn about a group- or world-readable identity file.
- `cmd_keygen`: if the write fails after `O_EXCL` creation, an empty or partial key file is left behind.
- Neither is a vulnerability.

## Checked and found sound
- **Password:** `secrets.token_bytes(32)` → base64url, 43 characters (`sealed.py:93-95`). Passed to
  `pyrage.encrypt(password.encode("ascii"), …)` in-process: no argv, no subprocess. It lives only in the job thread's
  locals: not in the job state, the logs or the reprs. The tar is written through `_NewFile` (`O_EXCL|O_NOFOLLOW`,
  0600, `.part`, removed on error). The structlog chain (`format_exc_info`, JSON) renders no locals.
- **Manifest:** only public data (recipients, sizes, sha256, version, revision). The reader rejects duplicate keys,
  unknown or missing keys and bool-as-int, and checks the types and the `lfbk_size`/`lfbk_sha256` match.
- **Tar reader** (`sealed.py:199-245`):
  - It accepts only `ustar\0` + `00` headers, which refuses GNU and old-GNU.
  - It accepts only typeflag `0`/`\0`, which refuses PAX `x`/`g`, links and directories.
  - It refuses a non-empty prefix, verifies the checksum and accepts octal-only numbers (base-256 refused).
  - Names must equal the 3 members, in order, which rules out traversal and duplicates. It never extracts by name.
  - Small members are capped at 4096 bytes before they are read. Oversized sizes fail as "cut short".
  - `pyrage.decrypt` raises `DecryptError` on garbage (probed). The decrypted password must fullmatch
    `[A-Za-z0-9_-]{43}`.
- **`check` formula and header:** reused unchanged (`unlock_header`, `_check_supported` bounds before scrypt,
  `hmac.compare_digest`).
- **Ticket scope:**
  - `BACKUP_RESTORE` has `read_token=lambda: None`, so an L1 token falls through to ticket parsing and gets a counted
    401 `backup_restore_unauthorized`.
  - Without `PANEL_PUBLIC_KEYS` the route answers 404.
  - The scope comparison is exact (`tickets.py:121`), so a `backup` ticket gets 401 `panel_ticket_wrong_scope`.
  - The `jti` is recorded once. `panel_tickets.sqlite3` is outside `SWAPPED_FOLDERS`, so replay protection survives
    the restore.
- **Order of checks:** the router dependencies (`refuse_when_blocked`, `refuse_when_awaiting_restore`) let the seven
  routes through. Then come the ticket, then 423 `instance_blocked`, then 409 `restore_mode_required`. A caller without
  a ticket learns neither the block nor the mode. The upload body is streamed after the dependencies (R3). The
  Content-Length check, the per-write limit, the free-space check and `abort()` on every receive failure are the
  admin's code, unchanged.
- **Password in responses:** the routes use `NoInputEchoRoute` (the route class is preserved through
  `include_router`). `RestoreStageRequest.password` is a `SecretStr` with max 1024. The `EnvelopeError` messages
  returned to the client are fixed text.
- **Panel scoping:** `_panel_check` returns 404 for a check whose origin is not the panel, before confirm and get. The
  confirm retry returns 202 only for the same pending `stage_id`. The restart retry returns 202 without a signal for
  `in_progress`/`committed`.
- **Private helpers of `restore.py`:** the panel route calls the same `restore_jobs.start_check`/`confirm_check` and
  `apply.prepare_restart`/`cancel_restore` as the admin route, so the blockers, expiry, outdated-revision and
  already-pending checks all still run. The admin's only extra check is the router-level block dependency, which the
  panel replaces with its own 423.
- **R1 redaction:**
  - `PanelRestoreStageReport` uses `extra=forbid` with an include-list. Administrators become a count. There are no
    tables, sizes or totals differences.
  - `PanelRestoreStage` and `PanelRestoreStatus` use `extra=forbid` and build from `model_dump`: a future field added
    by B fails with a 500 instead of leaking.
  - `GET /panel/status` → `PanelRestoreSummary` holds `state`, `reason`, `waiting`, `backup_created_at`, `stage_id`.
    `reason` and `waiting` are Literals. No usernames, emails, amounts or paths.
- **Awaiting-restore mode:**
  - The env var parse raises on any other value. `configuration-checks` runs before `pending-restore`, so a bad value
    stops startup.
  - Every `/api/v1` route is an `APIRoute` under a router carrying `refuse_when_awaiting_restore`.
  - Outside the router: `openapi.json`, docs and redoc exist only when `api_docs_enabled()` and carry no data.
    Static, mkdocs and the SPA catch-all serve no data. There are no websockets. `test_lane_health` answers 404 outside
    test mode.
  - `wake-sync` runs no job. Admin `restore/outcome`, login and registration answer 423.
  - The skipped steps all run again on the first start without the mode. Prune and leftovers sweeps do not depend on
    the scheduler.
- **Panel backup in the mode:** `start` answers 409 `backup_awaiting_restore`. Without recipients a managed instance
  answers 503, so no clear zip is handed out. `backup_recipients()` never echoes the value (an `AGE-SECRET-KEY` pasted
  by mistake is refused by the `age1` prefix check).
- **Frontend:** `InstanceAwaitingRestorePage` and `AwaitingRestoreGate` render only static i18n text: no `{@html}`, no
  server strings, no info leak.
