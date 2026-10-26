# 💾 Hosting for Others: Backups and Restores

This page is part of the guide for whoever runs LibreFolio for other people. It covers what your hosting panel does with an instance's data: **taking its backups**, **restoring** one on a new machine, and the **upload limit** of a restore.

The rest of the guide starts on [Hosting for Others](hosting_providers.md).

---

## 💾 Backups for Your Hosting Panel {: #panel-backups }

Your hosting panel can back up the whole instance and download the archive, with a token instead of
a user's session. It is the same archive as `backup create` on the [command line](cli_tools.md): the
database, the uploaded files, the broker reports and the stress scenarios of every user.

These routes are the `backup` scope of the [Hosting Panel API](hosting_panel_api.md#panel-api), which holds the rules
the three scopes share: the header, the `401`, the `429` and the log line.

### 🔑 The Token {: #panel-token }

Generate a token:

```bash
openssl rand -hex 32
```

Give it to the instance in `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN`, in the container's environment or in
`.env`, then restart LibreFolio. With Docker Compose, run `docker compose up -d`:
`docker compose restart` keeps the old values.

```bash
LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN=<the 64 characters printed by openssl>
```

- To keep the token out of `.env` and of the container's environment, put it in a file and give the
  file's path in `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN_FILE`, as Docker mounts its secrets: see
  «Secrets in Files» in [Environment Variables](configuration.md).
- The token is at least 32 characters long, all of them visible ASCII characters: no space, no tab,
  no accented letter. A space makes it unusable, even at the end: in a file, the line breaks at its
  end are dropped, spaces are not.
- The panel sends it in one header, `Authorization: Bearer <token>`, and never in the URL, where
  access logs would keep it.
- LibreFolio checks the token at startup, and reads it again at every call: a token it cannot use does
  not stop the server. The start log has an error that names the variable, never the token
  (`check` is `backup.panel_token`: see «Startup Checks» in [Environment Variables](configuration.md)),
  and every call then answers `503` and logs an error that names the variable too:
  `The hosting panel's backup token cannot be used: its routes refuse every request`.
- Anyone who has the token can download all the data of the instance: keep it as private as the
  archives, and call the routes over HTTPS only.

### 🔄 Start, Follow, Download, Delete {: #panel-jobs }

| Step | Route | Answer |
| --- | --- | --- |
| Start a backup | `POST /api/v1/backup/panel/jobs` | `202`, and the job with its `job_id` |
| Follow it | `GET /api/v1/backup/panel/jobs/{job_id}` | The job: its `status` is `running`, then `done` or `failed` |
| Download the archive | `GET /api/v1/backup/panel/jobs/{job_id}/file` | The zip archive |
| Delete it from the server | `DELETE /api/v1/backup/panel/jobs/{job_id}` | `204` |

```bash
TOKEN='<your LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN>'
JOBS=https://librefolio.example.com/api/v1/backup/panel/jobs

# Start a backup: the answer gives its job_id
curl -sS -X POST -H "Authorization: Bearer $TOKEN" "$JOBS"

# Follow it until "status" is "done" (or "failed", with an "error_code")
curl -sS -H "Authorization: Bearer $TOKEN" "$JOBS/<job_id>"

# Download the archive
curl -fsS -H "Authorization: Bearer $TOKEN" -o librefolio-backup.zip "$JOBS/<job_id>/file"

# Delete it from the server once you have it
curl -sS -X DELETE -H "Authorization: Bearer $TOKEN" "$JOBS/<job_id>"
```

- ⏳ While the backup runs, the job gives its `phase` (`preparing`, `database`, `files`,
  `finalizing`) and its progress, `done_bytes` of `total_bytes`. Once it is `done`, `file_name` and
  `file_size` describe the archive. A `failed` job gives its `error_code`: `backup_no_space`,
  `backup_failed` (the server's log has the cause) or `backup_interrupted` (the server stopped
  during the backup).
- 🚦 One backup runs at a time on an instance, whoever started it: an administrator, the
  [command line](cli_tools.md) or your panel. While one runs, a start answers `409`: try
  again later.
- 🕐 The server keeps a finished job and its archive for one hour, then removes them: download the
  archive within the hour, and delete the job as soon as you have it.
- 👀 Your panel sees only the backups it started: any other job, such as one an administrator
  started from the app, answers as if it did not exist.
- 🏷️ The archive records that your panel made it: `backup inspect`, on the
  [command line](cli_tools.md), shows `Made by LibreFolio <version> (panel)`.
- 🗝️ Its archives never hold the instance key («The Instance Key» in
  [Environment Variables](configuration.md)). Keep the key of each
  instance with its archives, from `LIBREFOLIO_INSTANCE_KEY_FILE` or from its `secrets/` folder, and
  hand it over with them: without it, what LibreFolio encrypted can no longer be read.
- 🔒 The four routes keep answering on a [blocked instance](hosting_instances.md#instance-block): that is when you hand
  the data back to your customer.

### 🚫 When a Call Is Refused {: #panel-refusals }

| Answer | When | `code` |
| --- | --- | --- |
| `404` | `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN` is not set, and neither are the panel's [public keys](hosting_panel_api.md#panel-api-tickets): every route answers as a path that does not exist | — |
| `401` | No token, or not the token of this instance. A refused ticket has its own `panel_ticket_…` code: [Why a Ticket Is Refused](hosting_panel_api.md#panel-api-ticket-refusals) | `backup_panel_unauthorized` |
| `429` | Too many refused credentials from your panel's address: see [The Limit on Refused Credentials](hosting_panel_api.md#panel-api-limit) | `panel_too_many_attempts` |
| `503` | The token is set but cannot be used: shorter than 32 characters, a character that is not visible ASCII, or a `_FILE` that cannot give it. The start log names it already (`check` is `backup.panel_token`), and each call logs it | `backup_panel_unavailable` |
| `404` | A job your panel did not start, or one that does not exist, or no longer does | `backup_job_not_found` |
| `409` | A start while another backup runs. When it is a backup your panel started, the answer adds its `job_id` and `origin` (`panel`): follow that job instead of starting another | `backup_busy` |
| `409` | A download of a job that has no archive: still running, or failed | `backup_job_not_ready` |
| `409` | A delete while the job runs | `backup_job_running` |
| `409` | A start while the instance [awaits a restore](#await-restore): a backup of its empty data never starts | `backup_awaiting_restore` |
| `409` | A start while a [restore stopped half way](#restore-interrupted): a backup of data in doubt never starts. Your panel's credential is checked first: without a valid one the answer is the `401` or `404` above | `backup_restore_interrupted` |
| `409` | A start while the instance key is not the one its data was written with ([When the Instance Key Does Not Match](#instance-key-mismatch): `instance_key` is `mismatch` in the [status](hosting_panel_api.md#panel-status)): a copy made with the wrong key would push a good one out of the ones you keep. The credential is checked first, as above. Following a job, downloading and deleting still answer | `backup_instance_key_mismatch` |
| `507` | A start while the disk of the data directory, or a quota, is full: free some space, then start again | `backup_no_space` |
| `500` | The backup cannot start: the `backups/` folder of the data directory is a link or a file, or cannot be written for another reason. The log has the cause | `backup_folder_unusable`, `backup_failed` |

The `code` comes in the `detail` of the answer, with a `message` in English:

```json
{"detail": {"code": "backup_panel_unauthorized", "message": "A valid panel token is required"}}
```

---

### 🔏 When the Instance Key Does Not Match {: #instance-key-mismatch }

The instance keeps, next to its key, a check value of it ([The Key Check](configuration_secrets.md#instance-key-check)).
When the key the machine has is not the one the data was written with, the panel's [status](hosting_panel_api.md#panel-status)
answers `"instance_key": "mismatch"`, and two things of yours stop, nothing else: a backup start answers `409`
`backup_instance_key_mismatch` (once your panel's credential is checked), and the [scheduled wake-up](wake_sync.md#wake-sync)
answers the status `instance_key_mismatch` and runs no job. The instance **keeps serving** its users, and following a
job, downloading and deleting still answer. The stop protects your copies: a backup made with the wrong key would push a good one out of the ones you keep.

**Your backups resume by themselves.** Nothing is stored about the mismatch: the instance compares the key with the check
value at every request. The first time your panel asks after the cause is gone, the status says `ok`, the next start is accepted
and the next night's visit runs its jobs. There is nothing to reset, and no flag to clear.

Three ways out, from the most common:

1. **The wrong key was an error** (a machine started with another instance's key, an old value left in the
   configuration): apply the right key, with `LIBREFOLIO_INSTANCE_KEY` or its `_FILE`, and restart the
   machine once. The status says `ok` at once. If it still says `mismatch` after one restart with the key you
   hold in custody, do not try other keys: the key you hold is not the one the data was written with, so go on with the third way.
2. **You mean to change the key** (a rotation, decided with the customer): start the machine **once** with
   `LIBREFOLIO_INSTANCE_KEY_ACCEPT=1` beside the new key. That start stores the check value of the new key and logs a
   warning. Then remove the variable and restart: while it is set, every start accepts any key, and the protection does nothing.
   The plugin secrets that the old key encrypted can no longer be read: they are entered again.
3. **The right key is lost**: the data cannot be read back with it, so go the second way, with the key you
   have now, and the customer enters the plugin secrets again, in Settings › Plugins. Decide it with the customer and your
   support: LibreFolio never does it by itself. If the lost key turns up later, put it back as in the first way: the
   secrets entered again under the new key then stop reading, and are entered once more.

## ♻️ Restoring an Instance from Your Panel {: #panel-restore }

When the server of an instance is gone, your hosting panel can put the instance's backup back on a
new machine. The new machine starts in the **awaiting restore** mode: nobody can sign in, register or
set up an administrator there, until your panel has restored the data and ended the mode.

The restore takes the instance's [secure backup](backup_restore.md#secure), the `.lfbk` file, still
encrypted, with its password. Its routes are the `backup:restore` scope of the
[Hosting Panel API](hosting_panel_api.md#panel-api): they accept a [signed ticket](hosting_panel_api.md#panel-api-tickets) of that scope and
nothing else, never a token. Without `LIBREFOLIO_PANEL_PUBLIC_KEYS` they answer `404`.

### ⏳ The Awaiting Restore Mode {: #await-restore }

| Variable | Values | What it does |
| --- | --- | --- |
| `LIBREFOLIO_AWAIT_RESTORE` | The values of `LIBREFOLIO_BLOCKED`: `1`, `true`, `yes` or `on` turn it on; `0`, `false`, `no` or `off` do not, in any case. Not set or empty: off | The instance waits for your panel to restore its data |

Set it on the new machine, before its first start on the empty data directory:

```bash
LIBREFOLIO_AWAIT_RESTORE=true
```

- Leave it unset on every other instance. A change applies when the server restarts, as for the
  block.
- Any other value stops the server at startup, and the error names the variable:
  `LIBREFOLIO_AWAIT_RESTORE must be one of 1/0, true/false, yes/no, on/off, or unset`.
- While it is on, every start logs a warning,
  `Instance awaiting its restore by the hosting panel (LIBREFOLIO_AWAIT_RESTORE): only the panel's routes and the probes answer`.
- The start skips what would make the machine a new instance: no
  [initial administrator](hosting_instances.md#initial-admin) and no setup link, even with `LIBREFOLIO_ADMIN_EMAIL` (the
  backup brings its own accounts), no [market data scheduler](settings.md#market-data-scheduler),
  and none of the background warm-ups. The log has one `Startup step skipped` line for each, naming
  the step: `admin-bootstrap`, `stored-currencies`, `provider-prewarm`, `market-holidays`,
  `brim-parse-pool` and `scheduler`. The database, the steps of the restore and the idle monitor
  still run.

While the mode is on, only these API calls answer:

| For | Endpoints |
| --- | --- |
| Probes and version | `GET /api/v1/system/health`, `GET /api/v1/system/ready`, `GET /api/v1/system/info`. `/system/ready` adds `"mode": "awaiting_restore"`, and `ready` then means ready to receive the backup |
| The public configuration of the instance, with `"mode": "awaiting_restore"` | `GET /api/v1/system/instance` |
| The [scheduled wake-up](wake_sync.md#wake-sync), with its own token: it answers `awaiting_restore` and runs no job | `POST /api/v1/system/wake-sync` |
| Your panel's [status](hosting_panel_api.md#panel-status), with `mode` and `restore` | `GET /api/v1/panel/status` |
| Your panel's [backup jobs](#panel-jobs): a start answers `409` with the code `backup_awaiting_restore`, since a backup of the empty data never starts | The four `/api/v1/backup/panel/jobs…` routes |
| Your panel's restore | The [seven routes](#panel-restore-routes) below |

Every other call answers `423 Locked`, to anyone, signed in or not, registration, the sign-in and the
setup of an administrator included:

```json
{"detail": {"code": "instance_awaiting_restore", "message": "This instance is waiting for its hosting provider to restore its data"}}
```

Users who open the instance get a full page instead of every page of the app, the sign-in page
included: **Restoring your data**, on the sign-in page's background. It asks the instance every 30
seconds whether the mode has ended, and reloads itself when it has; **Try again** reloads it at once.

### 🔄 Upload, Check, Confirm, Restart {: #panel-restore-routes }

Each call carries a new ticket of scope `backup:restore`, in `Authorization: Bearer <ticket>`. The
paths are under `/api/v1/backup/panel/restore`:

| Step | Route | Answer |
| --- | --- | --- |
| Upload the `.lfbk` file, as the raw body | `PUT …/upload` | `201`, with its `upload_id` |
| Check it on a copy, with its password | `POST …/stage`, body `{"upload_id": "…", "password": "…"}` | `202`, and the check with its `stage_id` |
| Follow the check | `GET …/stage/{stage_id}` | The check: its `status` is `running`, with `phase` and `done_bytes` of `total_bytes`, then `done`, with the report, or `failed`, with an `error_code` |
| Confirm the restore | `POST …/stage/{stage_id}/confirm` | `202`, and the restore's status, `pending` |
| Restart the server, to apply it | `POST …/restart` | `202`, and the status. The server stops once the answer is sent; your restart policy starts it again, and that start applies the restore |
| Follow the restore | `GET …/status` | Its status: `none`, `pending`, `in_progress`, `committed` or `rolled_back` |
| Drop a confirmed restore before the restart | `DELETE …/pending` | `204`, its checked copy removed |

- **Only the `.lfbk` file.** A zip or the sealed `.tar` that holds it is refused with `400` and the
  code `restore_envelope_required`, and removed: on its first bytes, or once the whole file is
  received and is no `.lfbk` after all. The [upload limit](#restore-upload-limit) and the
  limit on what an archive unpacks to apply, as for an administrator's restore.
- **A new upload replaces the previous one only once it is accepted**: received to its end, then
  found to be an `.lfbk` file. A refused upload, empty, incomplete, too large or not an `.lfbk`,
  leaves the previous one in place, for its check. An upload that a running check reads is never
  removed.
- **The report holds no personal or portfolio data.** It gives the backup's date, version, origin
  and revision, the version this instance runs, whether the restore keeps the version (`same`) or
  upgrades it (`upgrade`) and with which migrations, whether the instance key is included, the
  warnings and blockers (`no_administrator`), the control totals as a verdict (`same`, `changed`,
  `absent`, `other_version` or `unreadable`) with the number of differences, `administrators_count`,
  `restorable` and `expires_at`. Never a username, an amount, a table or a size.
- **Your panel sees only the checks it started.** A check started by an administrator or from the
  command line answers `404` with the code `restore_stage_not_found`, as an unknown id.
- **The status names who confirmed only as `confirmed_via`**: `admin`, `cli` or `panel`. A
  confirmation by your panel is `panel`, and the instance records your ticket's `kid` as who
  confirmed it.
- **Repeating a call never makes two restores.** Starting the check again with the same
  `upload_id` while its check runs answers `202` with that same check; confirming the same check
  again answers `202` with the same status; a restart while the restore is already under way, or committed, answers
  `202` with its state and stops nothing.
- **The password is never echoed**, in an answer or in a validation error.
- **What the next start does** is the restore of an administrator: see
  [What the Next Start Does](backup_restore.md#next-start).

### 🏁 Ending the Mode {: #await-restore-end }

The instance never leaves the mode by itself. When the status reads `committed`, your panel removes
`LIBREFOLIO_AWAIT_RESTORE` from the machine and restarts it: from then on it is the instance again,
with its accounts. A restore that ends `rolled_back` stays in the mode, with its `reason`.

!!! warning "Restoring a blocked instance: change the variables in one update"

    To restore an instance that was [blocked](hosting_instances.md#instance-block), start the new machine with
    `LIBREFOLIO_AWAIT_RESTORE` on and `LIBREFOLIO_BLOCKED` off: with the block on, the restore
    routes answer `423 instance_blocked`. Every user route still answers `423` while the mode is on,
    so the instance is never usable in the meantime.

    Once the status reads `committed`, change the variables in **one** update of the machine,
    followed by one restart: `LIBREFOLIO_AWAIT_RESTORE` off, `LIBREFOLIO_BLOCKED` on, and
    `LIBREFOLIO_DELETION_DATE` unchanged. The first request after that restart already gets the
    block. Two updates, the mode removed first and the block set again later, leave the instance
    running unblocked between the two restarts.

### 🚫 When a Restore Call Is Refused {: #panel-restore-refusals }

Each route checks, in this order: the ticket, then the block, then the mode. A call without a valid
ticket learns neither whether the instance is blocked nor whether it awaits a restore.

| Answer | When | `code` |
| --- | --- | --- |
| `404` | `LIBREFOLIO_PANEL_PUBLIC_KEYS` is not set: the routes answer as a path that does not exist | — |
| `401` | No credential, any token, or a ticket that cannot be verified. A refused signed ticket has its own `panel_ticket_…` code: [Why a Ticket Is Refused](hosting_panel_api.md#panel-api-ticket-refusals) | `backup_restore_unauthorized` |
| `429` | Too many refused credentials from your panel's address: [The Limit on Refused Credentials](hosting_panel_api.md#panel-api-limit) | `panel_too_many_attempts` |
| `503` | The ticket settings, or the registry of used tickets, cannot be used; or the limit on what an archive unpacks to cannot be read | `backup_restore_unavailable` |
| `423` | The instance is blocked: no restore | `instance_blocked` |
| `409` | `LIBREFOLIO_AWAIT_RESTORE` is off: a restore never writes over an instance that runs | `restore_mode_required` |
| `400` | The upload is empty, incomplete, or not an `.lfbk` file; the check has no password, a wrong one, or a damaged file (the upload stays, for another try) | `backup_upload_empty`, `backup_upload_incomplete`, `restore_envelope_required`, `password_required`, `wrong_password`, `envelope_damaged` |
| `413` | The file is larger than the [upload limit](#restore-upload-limit) | `backup_too_large` |
| `404` | No upload or no check has this id; or no restore is confirmed, for `DELETE …/pending` | `backup_upload_not_found`, `restore_stage_not_found`, `restore_not_pending` |
| `409` | Another file is being checked, a secure backup this version cannot read, a check still running or that refused the file, LibreFolio updated since the check, another restore already confirmed, or a restart with no restore confirmed | `restore_busy`, `envelope_unsupported`, `restore_stage_running`, `restore_not_restorable`, `restore_stage_outdated`, `restore_already_pending`, `restore_not_pending` |
| `410` | The check expired: check the file again | `restore_stage_expired` |
| `507` | Not enough free space in the data directory | `backup_no_space`, `no_space` |
| `500` | The data directory's restore folder cannot be used, the state of the restore cannot be read (the answer's `detail` then adds `reason`: `io`, `not_a_file` or `invalid`), or a step could not be done; the log has the cause | `restore_folder_unusable`, `restore_state_unreadable`, `backup_upload_failed`, `stage_failed`, `restore_confirm_failed`, `restore_restart_failed`, `restore_cancel_failed` |

### 🧩 When the State of a Restore Cannot Be Read {: #restore-interrupted }

Every restore, yours or an administrator's, keeps its state in the data directory, in
`.restore/restore.json`. That file can become unreadable: its owner or permissions changed, a disk
error, a link or a folder in its place, or content no LibreFolio wrote. A restore may then have
stopped half way, and LibreFolio cannot tell which data it holds. This can happen on any instance,
managed or not.

Every start checks it, right after applying a restore that waits for it. When it cannot read it,
the instance serves **no data** until its administrator chooses what to do, and the start logs one
error, with the reason (`io`, `not_a_file` or `invalid`), never the file's content:

```text
The state of the restore cannot be read: LibreFolio serves no data until the administrator runs ./dev.py backup pending --recover previous
```

- **The start skips** what repairs, writes or warms up the data. The log has one
  `Startup step skipped` line for each, naming the step: `post-migration-fixes`,
  `lone-transfer-legs`, `admin-bootstrap`, `stored-currencies`, `provider-prewarm`,
  `market-holidays`, `brim-parse-pool` and `scheduler`. The database, the steps of the restore and
  the idle monitor still run.
- **The same API calls answer as in the [awaiting restore mode](#await-restore)**: the probes and
  the version, `GET /api/v1/system/instance`, the
  [scheduled wake-up](wake_sync.md#wake-sync) and your panel's routes (its status, its backup jobs
  and its restore), but a backup start. Every other call answers `423 Locked`, to anyone, signed in
  or not, the sign-in included:

    ```json
    {"detail": {"code": "instance_restore_interrupted", "message": "A restore of this instance stopped half way: it serves no data until its administrator recovers it"}}
    ```

- `GET /api/v1/system/instance` says `"restore_interrupted": true`.
- The scheduled wake-up answers the status `restore_interrupted` and runs no job.
- Your panel's [status](hosting_panel_api.md#panel-status) answers `200` with `restore.state` `unreadable` and its
  `reason`, as it does whenever the state of the restore cannot be read.
- Your panel's [backup jobs](#panel-jobs): a start answers `409` with the code
  `backup_restore_interrupted`, once your panel's credential is checked (without a valid one, the
  same `401` or `404` as always): a backup of data in doubt would take the place of a good one among
  those you keep. Following a job, downloading its archive and deleting it still answer.
- Users who open the instance get a full page instead of every page of the app, the sign-in page
  included: **The restore stopped half way**, on the sign-in page's background. It asks them to
  contact their administrator, links the steps to recover, asks the instance every 30 seconds
  whether it serves the data again, and reloads itself when it does; **Try again** reloads it at
  once. When `LIBREFOLIO_SUPPORT_URL` holds an address the page can use, a `mailto:` address or an
  `http://` or `https://` page (the page checks it again), it adds a **Contact support** link to it.
  Not set or not usable: no link, and no fallback to the project's GitHub.

**The way out is on the machine**, for whoever runs it: stop LibreFolio, run
`./dev.py backup pending` to see what happened, then `./dev.py backup pending --recover previous`, which puts
the data of before back, and start LibreFolio again: see
«An Unreadable Restore State» in [Command-Line Tools](cli_tools.md). The instance decides once,
at its start: a file made readable again while LibreFolio runs counts only at the next start.

### 🧩 When the Owner of a Restored Instance Has No Account Yet {: #restore-owner-pending }

On a managed instance, an administrator who restores a backup from Settings › Administration › Backup
names the account of the backup that becomes the owner's (the person whose address is
`LIBREFOLIO_ADMIN_EMAIL`). The first start on the restored data gives that account the owner's
address and sends the owner a link to choose a password: a backup may come from anywhere, and whoever
prepared it must not be able to sign in as the owner. A restore from your panel or from the command
line names no owner, and none of this happens.

Until the owner has their account, the instance serves **no data**, exactly as in
[the previous section](#restore-interrupted): the same skipped steps, the same `423
instance_restore_interrupted` for every call but the probes, `GET /api/v1/system/instance`, the
scheduled wake-up and your panel's routes, and the same `409 backup_restore_interrupted` for a backup
start. `GET /api/v1/system/instance` adds `"restore_interrupted_reason": "owner_assignment"` (it says
`"restore_state"` for an unreadable state, and `null` otherwise); users see the page **The owner's
account is not ready**.

- **It usually takes a moment.** The first start does it right after committing the restore, and the
  start logs one line with the outcome. With several workers one of them does it and the others ask
  again every two seconds: they open when it is done, with no restart.
- **When it cannot be done** (for example the chosen account no longer exists) the start logs one
  error with the code, `The owner of the restored data has no account yet: LibreFolio serves no data
  until it is set`, and the instance stays closed. Its administrator stops LibreFolio, runs
  `./dev.py backup pending --recover owner`, which clears the recorded outcome and tries again, and
  starts LibreFolio again.

---

## 📤 The Upload Limit of a Restore {: #restore-upload-limit }

To check an archive for a restore, an administrator uploads it to the instance from
Settings › Administration › Backup
([Restore from Settings › Administration › Backup](backup_restore.md#restore-settings)), through
`PUT /api/v1/backup/restore/upload`; the instance then checks it on a copy, as
`backup restore --dry-run` does on the [command line](cli_tools.md). On an instance you host, the
administrator is your customer: `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` is how you cap the size of the
archives they can upload.

| `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` | Largest archive accepted |
| --- | --- |
| Not set, or empty | No limit on a `selfhosted` instance; 500 MB in the [managed profile](hosting_providers.md#managed-profile) |
| `0` | No limit, in both profiles |
| A whole number, such as `2048` | That many megabytes, of 1024 × 1024 bytes each |

```bash
LIBREFOLIO_BACKUP_MAX_UPLOAD_MB=2048
```

- Set it in the container's environment or in `.env`, then restart LibreFolio, as for the token.
- An archive over the limit answers `413`, with the code `backup_too_large` and the limit in
  `limit_mb`: before anything is written when the request announces its size, otherwise as soon as
  the upload goes past the limit. Nothing of it is kept.
- A proxy in front of LibreFolio must let at least as much through: Nginx with
  `client_max_body_size`, whose default is only 1 MB (`client_max_body_size 2048m;` matches the
  example above), and your platform or CDN, if it limits the size of a request. A `413` without the
  code `backup_too_large` comes from the proxy, not from LibreFolio.
- A value other than a whole number, such as `500MB` or `-1`, does not stop the server: the start log
  already has an error, `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB cannot be used: …` (`check` is
  `backup.upload_limit`), then each upload answers `503` with the code `backup_upload_unavailable`, and
  the log has an error that names the variable: `The upload limit of a restore cannot be read`.
- The disk of the data directory needs room for the archive and, while it is checked, for its copy
  unpacked as well (how much: «Try a Restore on a Copy» in [CLI Admin Tools](cli_tools.md)): short of
  space, the upload answers `507` with the code `backup_no_space`, also when the disk reports itself
  full only at the end of the file, as a network file system or a quota may. The check answers with
  its own code, `no_space`: a `507` when it cannot even start, a refusal of the archive once it runs.
  An upload that cannot be written for another reason answers `500` with the code
  `backup_upload_failed`, and the log has the cause.
- An administrator reads the limit in force in `upload_limit_mb` of
  `GET /api/v1/backup/restore/status`: `0` for no limit, `null` when the value cannot be read.
  Settings › Administration › Backup shows it on its restore card, such as *Archives up to 500 MB.*,
  and refuses a larger file before sending it.
- On a [blocked instance](hosting_instances.md#instance-block), the upload is refused like the rest of the app, and so
  are the check and the restore: the block lets the data leave, never come in.

The upload limit bounds the archive as it is sent, compressed: a zip can unpack to far more than its
own size, and the check unpacks it on the disk of the data directory.
`LIBREFOLIO_BACKUP_MAX_RESTORE_MB` bounds what an archive unpacks to, from the sizes its manifest
declares, before the check unpacks anything.

| `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` | Largest size an archive unpacks to |
| --- | --- |
| Not set, or empty | No limit on a `selfhosted` instance; in the [managed profile](hosting_providers.md#managed-profile), 8 times the upload limit: 4000 MB with its default 500 MB, 16384 MB with the `2048` above, none when the upload limit is `0` |
| `0` | No limit, in both profiles |
| A whole number, such as `16384` | That many megabytes, of 1024 × 1024 bytes each |

- Why 8: a database shrinks to about a quarter of its size in an archive, and uploaded images, PDF
  files and spreadsheets barely shrink. An archive heavy with its database unpacks to about four
  times its size, so 8 leaves it twice that room, and still bounds what any archive unpacks to at
  4000 MB with the default, where a zip can otherwise unpack to about a thousand times its size.
- An archive over the limit is refused before anything is unpacked: the check fails with the code
  `unpacked_too_large`, and nothing of its copy is left. A secure archive is decrypted first, which
  takes about its own size, then measured the same way.
- A value you set always wins, `0` included. `backup restore` on the command line follows the same
  limit; whoever runs the server lifts it for one command with `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0`
  in front of it («Try a Restore on a Copy» in [CLI Admin Tools](cli_tools.md)).
- A value other than a whole number does not stop the server: the start log already has an error,
  `LIBREFOLIO_BACKUP_MAX_RESTORE_MB cannot be used: …` (`check` is `backup.restore_limit`), then each
  check, `POST /api/v1/backup/restore/stage`, answers `503` with the code
  `backup_restore_unavailable`, the archive kept, and the log has an error. While this variable is
  unset in the managed profile, an upload limit that cannot be used refuses the checks the same way,
  and the start log's line names `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` instead.

---

## 🔗 Related

- 📄 **[Hosting for Others](hosting_providers.md)** — The Managed Profile, Your Legal Pages
- 📄 **[Hosting for Others: Your Instances](hosting_instances.md)** — The Initial Administrator, Blocking an Instance
- 📄 **[Hosting for Others: the Panel API](hosting_panel_api.md)** — Hosting Panel API
