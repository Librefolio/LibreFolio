# B · L3-2 (CP2): the interface the red tests pin (2026-10-22)

Contract: `LibreFolio_developer_journal/Release_2/Phase_1/07_backupDocker/notes/BACKUP-contratto-L3.md` (AGREED; read §2, §3, §4, §7, §8, §9).
Vectors: `backend/test_scripts/fixtures/backup_l3/` (`vectors.json` + 10 `.tar` + 2 test identities; generator
`generate_vectors.py` shows exactly how the files are built). Base HEAD `5b71e0666`.

## 1. `backend/app/config/backup.py`

- `RECIPIENTS_VARIABLE = "LIBREFOLIO_BACKUP_RECIPIENTS"`, `MAX_RECIPIENTS = 2`.
- `backup_recipients() -> tuple[str, ...] | None`: unset or blank → `None`. Otherwise comma-separated, spaces around each
  stripped, each parsed with `pyrage.x25519.Recipient.from_str` and returned as `str(Recipient)` (canonical lowercase
  `age1…`), in the order written. Errors raise `BackupConfigError(RECIPIENTS_VARIABLE, code, message)`:
  `BACKUP_RECIPIENTS_INVALID` (an empty item between commas, not an X25519 `age1…` — an ssh key, garbage, an
  `AGE-SECRET-KEY-1…` private key), `BACKUP_RECIPIENTS_TOO_MANY` (more than 2), `BACKUP_RECIPIENTS_DUPLICATE` (the same
  recipient twice). The message names the variable and the rule; it may quote a public recipient (not a secret) but
  NEVER echoes an `AGE-SECRET-KEY-…` string.

## 2. `backend/app/services/platform/instance_backup/checks.py`

- `check_recipients() -> ConfigCheck`, id `backup.recipients`, registered with the other backup checks:
  - unset, profile `selfhosted` → `ok`, key `backup.checks.recipients.off`;
  - set and valid → `ok`, key `backup.checks.recipients.ok`, params `{"count": n}`;
  - invalid → `error`, key `backup.checks.recipients.invalid`, params `{"reason": <BackupConfigError code>}`;
  - unset, profile `managed` → `error`, key `backup.checks.recipients.missingManaged`.
  Summaries name the variable, never a secret. Profile read from `get_settings().LIBREFOLIO_PROFILE`.

## 3. `backend/app/services/platform/instance_backup/envelope.py` (format unchanged, one public function added)

- `unlock_header(header: EnvelopeHeader, password: str) -> EnvelopeKey`: what `unlock(path, password)` does once the
  header is read; `EnvelopeError("wrong_password")` on a wrong one. `unlock` calls it.

## 4. New `backend/app/services/platform/instance_backup/sealed.py`

Constants: `MEMBERS = ("manifest.json", "password.age", "backup.lfbk")`, `FORMAT = "lfbk-tar"`, `FORMAT_VERSION = 1`,
`PASSWORD_LENGTH = 43`, `SMALL_MEMBER_MAX = 4096`, `HEAD_BYTES = 10240`, `FILE_SUFFIX = ".tar"`.

`class SealedError(Exception)` with `.code` one of: `sealed_tar_invalid`, `sealed_manifest_invalid`,
`sealed_no_identity`, `sealed_password_invalid`, `sealed_identity_invalid`. Messages hold no path, no secret.

Functions:
- `new_password() -> str`: `secrets.token_bytes(32)` in base64url without padding (43 chars of `[A-Za-z0-9_-]`).
- `seal_password(password: str, recipients: Sequence[str]) -> bytes`: `pyrage.encrypt` (binary, not armored).
- `build_manifest(*, created_at: datetime, lfbk_sha256: str, lfbk_size: int, recipients: Sequence[str], librefolio_version: str, db_revision: str | None) -> bytes`:
  contract §3.2 bytes exactly (`json.dumps(sort_keys=True, separators=(",", ":"))`, UTF-8, no newline; `created_at` as
  `YYYY-MM-DDTHH:MM:SSZ` in UTC; `password_member` `"password.age"`; `format`, `version`).
- `write_sealed(dst: Path, *, manifest: bytes, password_age: bytes, envelope: Path, mtime: int) -> EncryptedFile`
  (size and sha256 of the `.tar`): ustar, the three members in order, fields of contract §3.4 (mode 0o600, uid/gid 0,
  empty uname/gname, `mtime`), padded to 10 240; written through `<dst>.part`, `0600`, published once complete, like
  the envelope's `_NewFile`; `FileExistsError` if `dst` exists. Given the good vector's three members and
  `mtime=1792724412`, the bytes equal `librefolio-backup-20261023-030012.tar` exactly.
- `is_sealed(path: Path) -> bool`: ustar magic at 257; False for a short/unreadable file.
- `read_sealed(path: Path) -> SealedArchive`: strict rules of contract §3.5 with no decryption. `SealedArchive` (frozen
  dataclass) has `manifest: dict`, `password_age: bytes`, `envelope_offset: int`, `envelope_size: int`,
  `envelope_header: EnvelopeHeader` (the 52 bytes parsed). Refuses with `sealed_tar_invalid`: not exactly three members,
  other names or order, a member that is not a regular file (link, dir…), a PAX or GNU header (any `pax_headers` or a
  type outside REGTYPE), `manifest.json` or `password.age` over 4096 bytes, `backup.lfbk` not starting with `LFBK`
  version 1. With `sealed_manifest_invalid`: not UTF-8 JSON object, duplicate keys, unknown keys, missing keys, wrong
  types, `format`/`version` unknown, `recipients` not 1–2 `age1…` strings, `lfbk_size`/`lfbk_sha256` not matching the
  member, `password_member` not `password.age`.
- `read_identities(path: Path) -> list[pyrage.x25519.Identity]`: an `age-keygen` file (comment lines `#…`, blank lines,
  one or more `AGE-SECRET-KEY-1…` lines). Nothing usable / a bad line → `SealedError("sealed_identity_invalid")`
  (message never quotes the line).
- `identity_file_text(identity, created_at: datetime) -> str`: `# created: <iso>Z`, `# public key: age1…`, the key line.
- `open_password(archive: SealedArchive, identities) -> str`: `pyrage.decrypt`; no identity opens it →
  `sealed_no_identity`; plaintext not exactly 43 base64url ASCII chars → `sealed_password_invalid`.
- `check_password(archive: SealedArchive, password: str) -> EnvelopeKey`: `envelope.unlock_header(archive.envelope_header, password)`
  (`EnvelopeError("wrong_password")` when the password does not open the `.lfbk`).
- `extract_envelope(path: Path, archive: SealedArchive, dst: Path) -> None`: copy the `backup.lfbk` member's bytes to
  the new file `dst` (`0600`, `.part`, never over an existing file).

Expected outcomes on the vectors (`vectors.json` `expect`): `ok`; `sealed_no_identity` (neg-other-recipient);
`wrong_password` (neg-wrong-password, at `check_password`); `sealed_manifest_invalid`; `sealed_tar_invalid`
(extra-member, bad-order, traversal, symlink); `envelope_damaged` (neg-tampered-lfbk: reads, opens, checks, then
`envelope.decrypt_file` of the extracted envelope fails).

## 5. Jobs (`jobs.py`), view (`schemas/backup.py`, `job_views.py`), panel route (`api/v1/backup/panel.py`)

- `jobs.Phase` and `InstanceBackupJob.phase` gain `"sealing"`. `jobs.BackupJob` gains `sealed: bool = False` and
  `sealed_recipients: tuple[str, ...] = ()` (persisted; old states read False / ()). `InstanceBackupJob` gains
  `sealed: bool = False`, `sealed_recipients: list[str] = []`.
- `jobs.archive_name(created_at, *, encrypted=False, sealed=False)` → `librefolio-backup-YYYYMMDD-HHMMSS.tar` when sealed.
- `start_backup(*, origin="ui", data_dir=None, password=None, recipients: tuple[str, ...] | None = None)` and
  `run_backup(..., recipients=None)`: `password` and `recipients` together → `ValueError`. With `recipients`: a fresh
  `sealed.new_password()`; the instance key is NEVER included (even when LibreFolio generated it); archive → `.lfbk`
  with that password → phase `sealing` → `.tar` (`write_sealed`) with `manifest` (`created_at` = job's, `librefolio_version`
  and `db_revision` = the zip manifest's `app_version` and `alembic_revision`, `recipients` as given). Done job:
  `file_name` the `.tar`, `file_size`/`file_sha256` of the `.tar`, `encrypted` True, `sealed` True, `sealed_recipients`,
  `instance_key_included` False; only the `.tar` and `state.json` stay in the job folder. The password never appears
  in `state.json`, the job, the log. A pyrage failure ends the job `failed` / `backup_failed`.
- `job_views.start_job(origin, password=None, recipients=None)`; `job_view` maps `sealed`, `sealed_recipients`.
  Download of a `.tar`: `Content-Type: application/x-tar`.
- `POST /api/v1/backup/panel/jobs`: reads `backup_recipients()` at each request. Invalid → `503 backup_panel_unavailable`
  (one error log line naming the variable, never a value); unset and profile `managed` → `503 backup_panel_unavailable`
  (one error line); set → `start_job("panel", recipients=…)`; unset `selfhosted` → as today (`start_job("panel")`, a
  clear zip). The jobs are never reached on a 503.

## 6. CLI (`scripts/backup_cli.py`, `./dev.py backup …`)

- `backup keygen --identity-file FILE`: writes a new identity (`identity_file_text`), mode `0600`, refuses an existing
  path (exit 1, `❌ … exists`), prints the `age1…` recipient on its own line. Never prints the private key.
- `backup create --sealed` (recipients from `LIBREFOLIO_BACKUP_RECIPIENTS`; unset → exit 1 naming the variable) or
  `--recipient age1…` (repeatable, at most 2): a sealed `.tar`. Exclusive with `--encrypt`, `--password-file`,
  `--password-stdin` (argparse error or exit 1 with a clear message).
- `backup inspect|decrypt|restore ARCHIVE.tar --identity-file FILE`: `read_sealed` → `open_password` →
  `check_password` → then exactly the `.lfbk` path with that password (the envelope extracted to a private temporary
  file, removed afterwards). Errors print `❌ <message> (<code>)` and exit 1, codes as in §4 (and `wrong_password`,
  `envelope_damaged`). A `.tar` without `--identity-file` → exit 1, `sealed_backup_needs_key`. `--identity-file` on a
  non-sealed archive → exit 1 with a clear message. `decrypt X.tar --identity-file F -o out.zip` writes the zip.

## 7. Frontend

- `BackupDownloadCard.svelte` phase map gains `sealing: 'backup.download.phase.sealing'` (a panel job the tab may follow).
- i18n keys (4 languages): `backup.download.phase.sealing`, `backup.checks.recipients.{off,ok,invalid,missingManaged}`.
