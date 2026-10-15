# 🏢 Hosting for Others

This page is for whoever runs LibreFolio for other people: a hosting provider with customers, an
association for its members, or a friend who hosts an instance for the family. On this page, all of
them are the **hosting provider**. A few settings exist for them:

- the **managed profile** says that the instance is run for others;
- the **instance block** closes the app but keeps the data, for example when a subscription is not
  paid;
- the **panel token** lets your hosting panel take backups of the instance;
- the **upload limit** caps the size of the archives uploaded for a restore.

All of them are set with plain environment variables, the same in every LibreFolio and documented
here: they are not tied to any particular provider or cloud.

!!! tip "🏠 Running LibreFolio for yourself?"

    You need nothing on this page. Leave its variables unset: your install is `selfhosted`, the
    default, and it is never blocked. To back it up, see «Back Up the Instance» in
    [CLI Admin Tools](cli_tools.md).

---

## 🏷️ The Managed Profile {: #managed-profile }

`LIBREFOLIO_PROFILE` says who runs the instance:

- **`selfhosted`** (the default): an install run by its owner;
- **`managed`**: an instance a hosting provider runs for its users.

Set it in `.env` or in the container's environment, then restart LibreFolio (with Docker Compose:
`docker compose up -d`):

```bash
LIBREFOLIO_PROFILE=managed
```

Case and spaces around the value do not matter; any other value stops the server at startup.

Today the profile changes three things:

| | `selfhosted` | `managed` |
| --- | --- | --- |
| `GET /api/v1/system/instance` answers | `{"profile": "selfhosted"}` | `{"profile": "managed"}` |
| A `JWT_SECRET` shorter than 32 characters | A warning in the startup log | The server does not start |
| The largest archive uploaded for a restore, while `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` is not set | No limit | 500 MB: see [The Upload Limit of a Restore](#restore-upload-limit) |

- The profile is public: anyone who can reach the server can read it at `/api/v1/system/instance`,
  without signing in. The web app reads it when it starts.
- The interface is the same in both profiles.

### 🔑 A Session Key of 32 Characters or More {: #managed-jwt-secret }

`JWT_SECRET` is the key that signs the login sessions. In the managed profile, a key shorter than 32
characters, set in `JWT_SECRET` or in the file of `JWT_SECRET_FILE`, stops the server at startup:

```text
In the managed profile the session signing key from JWT_SECRET must be at least 32 characters long; it is 12
```

Generate a long random key, put it in `JWT_SECRET`, and start again:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Leaving `JWT_SECRET` unset is allowed in both profiles: every start then makes a new random key, and
your users sign in again after each restart. See
[Keep Users Signed In After a Restart](index.md#session-persistence).

### 📋 For Each Instance

- `LIBREFOLIO_PROFILE=managed`.
- A `JWT_SECRET` of at least 32 random characters, so that sessions survive restarts. To keep it out
  of `.env`, use `JWT_SECRET_FILE`: see «Secrets» in [Environment Variables](configuration.md).
- Its own instance key: never share one key between instances. See «The Instance Key» in
  [Environment Variables](configuration.md).
- HTTPS in front of it: see [Expose Securely](service_exposure.md) and
  [HTTPS and reverse proxies](configuration.md#session-cookie-secure).
- A monitor on `GET /api/v1/system/ready`: see the monitoring tip in
  [Advanced Docker](docker_advanced.md).
- If your hosting panel takes its backups: its own `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN`, never shared
  with another instance. See [Backups for Your Hosting Panel](#panel-backups).

---

## 🔒 Blocking an Instance {: #instance-block }

A hosting provider can block an instance, for example when its subscription is not paid. Users can
still sign in, follow a password-reset link already sent to them, read why the instance is blocked
and sign out; the rest of the app is closed.
LibreFolio deletes nothing: the data stays as it is. The block works in both profiles.

### ⚙️ The Variables {: #block-variables }

| Variable | Values | What it does |
| --- | --- | --- |
| `LIBREFOLIO_BLOCKED` | `1`, `true`, `yes` or `on` block; `0`, `false`, `no` or `off` do not, in any case. Not set or empty: not blocked | Blocks the instance |
| `LIBREFOLIO_DELETION_DATE` | An ISO date, such as `2026-11-14`. Not set or empty: no date | The day you will delete the instance and its data, shown to the users on the block page |

To block an instance and announce its deletion date:

```bash
LIBREFOLIO_BLOCKED=true
LIBREFOLIO_DELETION_DATE=2026-11-14
```

- LibreFolio reads both from its environment. Set them in the container's environment, or in
  `.env`: `./dev.py` and Docker Compose (`env_file: .env`) hand the values of `.env` to the server.
- A change applies when the server restarts. With Docker Compose, run `docker compose up -d`:
  `docker compose restart` keeps the old values.
- To lift the block, remove `LIBREFOLIO_BLOCKED` or set it to `false`, then restart.
- Any other value stops the server at startup, so a typo never leaves the instance blocked or open
  by chance. The error names the variable:

    ```text
    LIBREFOLIO_BLOCKED must be one of 1/0, true/false, yes/no, on/off, or unset
    LIBREFOLIO_DELETION_DATE must be an ISO date such as 2026-11-14, not '14/11/2026'
    ```

- While the instance is blocked, every start logs a warning,
  `Instance blocked by its hosting provider (LIBREFOLIO_BLOCKED): only a few API routes answer`,
  with the deletion date when there is one.

### 👀 What Users See {: #what-users-see }

After signing in, users get a full page instead of the app, **This instance is blocked**:

- it says that the hosting provider has blocked the instance, for example because its subscription
  is not paid;
- administrators read that they should settle it with the provider to unblock the instance; the
  other users, that they should ask their administrator for a backup of their data;
- with `LIBREFOLIO_DELETION_DATE`, it adds the date, in the user's language: *The instance and its
  data will be deleted on …*;
- with `LIBREFOLIO_BILLING_URL` ([Environment Variables](configuration.md)),
  administrators also get a **Manage subscription** link to your subscription page, which opens in
  a new tab; the other users do not see it;
- **Logout** signs out.

A user still signed in after the restart gets the page as soon as the app asks the server for data.
Once you lift the block and restart, users get the app back at their next page load.

### ✅ What Still Answers {: #what-still-answers }

On a blocked instance, only these API calls answer as usual:

| For | Endpoints |
| --- | --- |
| Signing in and out, and who is signed in | `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me` |
| Following a link already sent: checking it, and setting a new password with a reset link | `POST /api/v1/auth/tokens/inspect`, `POST /api/v1/auth/password-reset` |
| Deleting one's own account, and seeing first what it would delete | `DELETE /api/v1/auth/users/me`, `GET /api/v1/auth/users/me/deletion-preview`: the block page has no button for it yet |
| Taking the data away: a backup of the whole instance, by an administrator or by your hosting panel | For an administrator, `POST /api/v1/backup/instance`, then `GET`, `GET …/file` and `DELETE` on `/api/v1/backup/instance/jobs/{job_id}`: the block page has no button for it yet. For your panel, its [four routes](#panel-jobs), with its token |
| The block page | `GET /api/v1/system/block` (signed-in users only), `GET /api/v1/system/instance` |
| Probes and version | `GET /api/v1/system/health`, `GET /api/v1/system/ready`, `GET /api/v1/system/info` |

- Your monitoring keeps working: `/system/health` and `/system/ready` answer as on any other
  instance.
- The web app itself is still served: the block covers the API only.
- Scheduled jobs, such as the price and FX syncs, keep running: they do not go through the API.

The list is short on purpose, and it is fixed in the code: there is no setting to change it.

### 🚫 Every Other Call {: #refused-calls }

Every other API call is refused:

- a **signed-in user** gets `423 Locked`, and the web app shows the block page on the first one:

    ```json
    {"detail": {"code": "instance_blocked", "message": "This instance is blocked by its hosting provider"}}
    ```

- a caller **without a valid session** gets `401`.

For a caller without a session, most of the API answers as on any other instance:

- the calls that always need a sign-in answer the same `401` whether or not the instance is blocked;
- the calls of the list above answer as usual: `/system/instance`, `/system/info` and
  `/system/ready` do not reveal the block.

A few calls are normally open to anyone: registration (`POST /api/v1/auth/register`), the address
probe (`GET /api/v1/auth/address-probe`), the reference lists (`GET /api/v1/utilities/*`), the global
settings (`GET /api/v1/settings/global`, also by key) and the AI Export catalogue
(`GET /api/v1/ai-export/catalog`). On a blocked instance they answer `401` too. The address probe
then cannot confirm a public address, and the check of your instance's address reports it as not
verifiable. From them, a caller without a session can tell that the instance is blocked, and nothing
more: they return no data.

### 📅 The Deletion Date {: #deletion-date }

`LIBREFOLIO_DELETION_DATE` is information for your users: LibreFolio shows it on the block page and
does nothing on that day. Deleting the instance and its data is up to you. The date is checked at
every start, blocked or not, but users see it only on the block page.

---

## 💾 Backups for Your Hosting Panel {: #panel-backups }

Your hosting panel can back up the whole instance and download the archive, with a token instead of
a user's session. It is the same archive as `backup create` on the [command line](cli_tools.md): the
database, the uploaded files, the broker reports and the stress scenarios of every user.

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
- LibreFolio reads the token when the panel calls, not at startup: a token it cannot use does not
  stop the server, but every call then answers `503` and logs an error that names the variable,
  never the token: `The hosting panel's backup token cannot be used: its routes refuse every request`.
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
- 🔒 The four routes keep answering on a [blocked instance](#instance-block): that is when you hand
  the data back to your customer.

### 🚫 When a Call Is Refused {: #panel-refusals }

| Answer | When | `code` |
| --- | --- | --- |
| `404` | `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN` is not set: every route answers as a path that does not exist | — |
| `401` | No token, or not the token of this instance | `backup_panel_unauthorized` |
| `503` | The token is set but cannot be used: shorter than 32 characters, a character that is not visible ASCII, or a `_FILE` that cannot give it. The log has the error | `backup_panel_unavailable` |
| `404` | A job your panel did not start, or one that does not exist, or no longer does | `backup_job_not_found` |
| `409` | A start while another backup runs | `backup_busy` |
| `409` | A download of a job that has no archive: still running, or failed | `backup_job_not_ready` |
| `409` | A delete while the job runs | `backup_job_running` |
| `500` | The backup cannot start: the `backups/` folder of the data directory is a link or a file, or cannot be written. The log has the cause | `backup_folder_unusable`, `backup_failed` |

The `code` comes in the `detail` of the answer, with a `message` in English:

```json
{"detail": {"code": "backup_panel_unauthorized", "message": "A valid panel token is required"}}
```

---

## 📤 The Upload Limit of a Restore {: #restore-upload-limit }

To check an archive for a restore, an administrator uploads it to the instance
(`PUT /api/v1/backup/restore/upload`), which then checks it on a copy, as `backup restore --dry-run`
does on the [command line](cli_tools.md). On an
instance you host, the administrator is your customer: `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` is how you
cap the size of the archives they can upload.

| `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` | Largest archive accepted |
| --- | --- |
| Not set, or empty | No limit on a `selfhosted` instance; 500 MB in the [managed profile](#managed-profile) |
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
- A value other than a whole number, such as `500MB` or `-1`, does not stop the server: each upload
  then answers `503` with the code `backup_upload_unavailable`, and the log has an error that names
  the variable: `The upload limit of a restore cannot be read`.
- The disk of the data directory needs room for the archive and, while it is checked, for its copy
  unpacked as well (how much: «Try a Restore on a Copy» in [CLI Admin Tools](cli_tools.md)): short of
  space, the upload answers `507` with the code `backup_no_space`, and the check refuses the archive
  with `no_space`.
  An upload that cannot be written for another reason answers `500` with the code
  `backup_upload_failed`, and the log has the cause.
- On a [blocked instance](#instance-block), the upload is refused like the rest of the app: the
  block lets the data leave, never come in.

---

## 🔗 Related

- 📝 **[Environment Variables](configuration.md)** — Every variable, those of this page included
- 🔐 **[Keep Users Signed In After a Restart](index.md#session-persistence)** — Generating
  `JWT_SECRET`
- 💾 **[CLI Admin Tools](cli_tools.md)** — «Back Up the Instance»: the same archives from the
  command line, and a restore tried on a copy
- 🐳 **[Advanced Docker](docker_advanced.md)** — Compose file, health check and monitoring
- 🔒 For developers: **[Instance Block](../developer/architecture/security.md#instance-block)** —
  The guard on the API and its list
