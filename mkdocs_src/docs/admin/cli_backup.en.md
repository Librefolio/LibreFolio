# 💾 CLI Admin Tools: Backups

This page of the command guide covers `dev.py backup`: creating, checking and restoring an archive, following a restore, working with Docker.

The rest of the guide starts on [Command-Line Tools](cli_tools.md).

---

## 💾 Back Up the Instance {: #backup }

`backup create` puts the whole instance in one zip, with the server running: database, uploaded files, broker reports, stress scenarios. To copy the data directory by hand, see [Backup](filesystem.md#backup).

| Task | Command |
| --- | --- |
| Create an archive | `backup create`; with `--encrypt` a [secure archive](#backup-secure), with `--sealed` or `--recipient` a [sealed archive](#backup-sealed) for backups that run on their own |
| Check an archive and see what it holds | `backup inspect` |
| Try a restore on a copy, instance untouched | `backup restore --dry-run` |
| Restore at the next start of the server | `backup restore` |
| Follow or cancel a restore | `backup pending` |
| Turn a secure archive back into its zip | `backup decrypt` |
| Generate the key of a sealed archive | `backup keygen` |

**Where the commands run:**

| Installation | Where | Command |
| --- | --- | --- |
| Host | Terminal of the server, LibreFolio folder | `pipenv run ./dev.py backup …` |
| Docker | Terminal of the server, folder of `docker-compose.yml`: the command runs inside the container | `docker compose exec librefolio python dev.py backup …`, with the container's paths: [Back Up with Docker](#backup-docker) |
| A computer of yours | `backup keygen`, and opening a sealed archive where the private key is | [A Sealed Archive](#backup-sealed) |

A relative path (`-o`, archives, password files) starts at the project root, wherever you run the command from: prefer absolute paths. `backup --test-db create` backs up the test data directory: a development option.

### 📦 Create an Archive

**Where: terminal of the server, LibreFolio folder** (Docker: [inside the container](#backup-docker)).

```bash
# Keep an archive in its own folder of <data dir>/backups/, and print its SHA-256
pipenv run ./dev.py backup create

# Copy it into another folder instead, which must already exist
pipenv run ./dev.py backup create -o /mnt/nas/librefolio/

# Or give the archive a name of your own
pipenv run ./dev.py backup create -o /mnt/nas/librefolio/before-update.zip

# A secure archive (.lfbk): the password is asked twice
pipenv run ./dev.py backup create --encrypt -o /mnt/nas/librefolio/
```

Result: the zip archive, in the place chosen with the options below, and its checksum printed.

| Option | Effect |
| --- | --- |
| none | **The archive stays on the server**, in a folder of its own in `backups/`: `backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip` (moment, origin `cli`, short code). Nothing is copied or moved. It appears in **Settings › Administration › Backup** and in the automatic clean-up: [Backups Kept on the Server](backup_restore.md#kept-backups) |
| `-o`, `--output PATH` | **The archive is copied there**, nothing stays in `backups/`. An existing folder: the archive with its default name inside. Any other path, even with a trailing `/`: the archive's file, which must not exist and is never renamed; the missing folders are created only at the move, so a failed backup leaves no empty folder behind. Checked before the backup starts: the command must be able to write there |
| `--encrypt` | [Secure archive](#backup-secure) `.lfbk`, password asked twice |
| `--password-file FILE`, `--password-stdin` | Secure archive with the password from a file or from the standard input, without `--encrypt` |
| `--recipient age1…`, `--sealed` | [Sealed archive](#backup-sealed) `.tar`, no password |

Good to know:

- ✅ It ends with `✅ Backup written: <path>`, the size and the time taken, `SHA-256: <checksum>`, any warnings and the reminder `🔒 The archive holds every user's data: keep it private.` (secure archive: `🔐 Encrypted with your password: only that password opens it, and LibreFolio cannot recover a lost one.`). It exits with `0` when the archive is where you asked, warnings included; `1` otherwise.
- 🟢 The server keeps working, and writing: the database is copied with SQLite's `VACUUM INTO`, a consistent snapshot, then the copy passes the integrity check and the foreign-key check.
- 🏷️ The name comes from the moment the backup starts, in UTC: `librefolio-backup-20261015-121500.zip`, `.lfbk` for a secure archive. In an `--output` folder that already holds that name, after two backups in the same second for instance: `librefolio-backup-20261015-121500-2.zip`, then `-3`, and so on. An archive never replaces a file.
- 🧾 After the path, the command prints `SHA-256: <64 hexadecimal digits>`, the checksum of the archive: compare it with the file's once it is on another disk.
- 💽 **Space**: checked before writing, in the data directory's `backups/`, even with `-o`: about twice the database, plus the files, plus a small margin. Short, or a disk or quota that fills up during the backup → `❌ Backup failed (backup_no_space): not enough free space`. With `-o` on another disk, the space there is checked once the archive is built and its size known.
- 🛟 If the finished archive cannot go to `-o` (a file with that name appeared meanwhile, folders that cannot be created, the other disk full, a write error) → it stays in `backups/` as a loose file: outside the list of kept backups, never removed by the automatic clean-up. The command exits with `1`. A move that fails half-way leaves no partial file behind.
- 🚦 One backup at a time: with another one running, the command stops and asks you to try again when the other has ended.
- 🔒 Without a password the archive is not encrypted: it is written `0600`, readable and writable by its owner only. Keep it, with every copy, as private as the data directory.
- 🗑️ The backups in `backups/` stay until you delete them from **Settings › Administration › Backup** or from the folder, or until the [automatic clean-up](backup_restore.md#backup-cleanup) removes them, the latest one excepted. The loose `librefolio-backup-*.zip` files of earlier versions are never touched. `backups/` is on the data disk: copy the archives to another disk, a NAS or off-site, or write them there directly with `-o`.
- 🔗 Keep `backups/` a real folder, never a link to a NAS or another disk: every archive is built there, even with `-o`. A link, or a file, in its place → `❌ <data dir>/backups is not a plain folder (a link, or a file): …`.

??? note "⚠️ Warnings and errors — what the messages mean"

    **Warnings**: the archive is written all the same.

    - `The database failed its integrity check` or `The database has foreign-key violations`: the database is in the archive as it is; `backup inspect` shows the result of the check.
    - `Left out (<n>): links, special files, files or folders that could not be read, or files removed during the backup`, then the entries, at most 50: they are not in the archive. Links are never followed, even when a whole folder such as `custom-uploads/` is a link to another disk.
    - `The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore`: a [secure archive](#backup-secure) without the key.

    **Not where you asked**: the archive is written, exit code `1`.

    - `⚠️ <reason>: the archive was written to <path> instead`, then the usual lines: `-o` could not receive the archive, which is in `backups/` as a loose file, outside the list of kept backups. Move it where you want it.
    - `❌ <reason>: the archive stays in <path>. Move it within the hour: the next backup after that removes it.`: `backups/` could not receive it either. It is in the work folder, inside `backups/.jobs/`, which the first backup or the first start of LibreFolio after that hour removes: move it out before then.

    **Errors**: no archive written, exit code `1`.

    - `❌ No data directory at <path>` or `❌ No database at <path>: nothing to back up`: the command uses the [data directory](filesystem.md) LibreFolio is configured with; check `LIBREFOLIO_DATA_DIR`.
    - `❌ <path> already exists: choose another name or folder`, `❌ <path> is not a folder: choose another path` (a file stands where the path needs a folder) or `❌ cannot write into <folder>: choose another folder, or run the command as a user who can`: `-o` cannot receive the archive. The backup has not started.
    - `❌ <data dir>/backups is not a plain folder (a link, or a file): …`: make `backups/` a real folder again. `❌ The backup could not run in <data dir>/backups: <reason>`: the work folder cannot be prepared there, for example because the data directory is not writable.
    - `❌ Backup failed (backup_no_space): not enough free space`: not enough space at the start, or a disk or quota that filled up during the backup, even in the middle of a file. Free some space on the disk of the data directory.
    - `❌ Backup failed (backup_failed): the cause is in the log above`: any other error, for example a file that fails while it is being copied into the archive (a read error half-way): part of a file cannot be taken out of a zip, so the whole backup stops. A file that fails before the copy is left out with the warning above instead.

### 🗃️ Where the Backups Stay {: #backup-kept }

Command and app leave the finished backups in `backups/`, one folder each: `librefolio-backup-<date>-<time>-<origin>-<id>`, origin `cli` for the command and `ui` for the app. `backups/.jobs/` holds only a backup in progress or one that failed.

| What to do with them | Where |
| --- | --- |
| List, download, delete them | **Settings › Administration › Backup**, or **Files › Backups** (administrators only): [Backups Kept on the Server](backup_restore.md#kept-backups) |
| Delete the oldest by themselves, never the latest: total size and maximum age, both optional | [Automatic Clean-up](backup_restore.md#backup-cleanup). The command applies them after each backup, as the app does |
| Check or restore a kept archive from the command line | `backup inspect` or `backup restore`, with the path printed by `backup create` |

💽 A copy on the disk of your data is not a real backup: copy the archive to another disk, or use `--output`.

### 🔐 A Secure Archive {: #backup-secure }

**Where: terminal of the server, LibreFolio folder** (Docker, from cron: `-T` and a secret, [below](#backup-docker)).

```bash
# The password is asked twice at the terminal
pipenv run ./dev.py backup create --encrypt

# The password read from a file that holds it alone (with Docker, a secret: /run/secrets/…)
pipenv run ./dev.py backup create --password-file ~/.librefolio-backup-password

# The password read from the standard input, such as from a password manager
pass show librefolio/backup | pipenv run ./dev.py backup create --password-stdin
```

Result: `librefolio-backup-20261015-121500.lfbk`, the zip that `backup create` writes without a password, encrypted with yours.

Only that password opens it, and LibreFolio does not recover a lost password: the command ends like a normal backup, with the reminder `🔐 Encrypted with your password: only that password opens it, and LibreFolio cannot recover a lost one.` What it protects and what it does not: [Secure Backups](backup_restore.md#secure).

**Where the password comes from**: never from the command line, which every user of the server reads (`ps`) and the shell keeps in its history. There is no `--password`, and the password options have no abbreviated form.

| Option | The password |
| --- | --- |
| `--encrypt` alone | Typed at the terminal, twice |
| `--password-file FILE` | The text of the file, without the byte order mark at its start and the line breaks at its end, as for [Secrets in Files](configuration_secrets.md#secret-files): a file with the password alone, such as a Docker secret. A relative path starts at the project root |
| `--password-stdin` | One line of the standard input, without its line break, such as from a pipe. At the terminal it is asked as without the option, hidden, twice for `create`: typed there as a line it would show |

`--password-file` and `--password-stdin` exclude each other, and either one makes the archive secure without `--encrypt`.

- 📄 **A file the command can trust.** The file of `--password-file`, like that of `--instance-key-file` ([The Instance Key of Another Installation](#backup-restore-instance-key)), must be a regular file. A FIFO, a folder or a device is refused at once, without reading it: `❌ password file: <path> is not a regular file (password_unreadable)`. As root, for example with `docker compose exec`, a path that goes through a link inside the data directory is refused too (LibreFolio's user could point it to a file only root reads): `❌ password file: <path> goes through a link inside the data directory: give the file itself, from outside it (password_unreadable)`. A link elsewhere is followed, as Kubernetes secrets are; Docker and Compose secrets are plain files. For `--instance-key-file`, the same lines start with `instance key file:` and end with `(instance_key_unreadable)`.
- 📏 **The rules**: as for an account password, at least 12 characters with an uppercase letter, a lowercase letter, a digit and a symbol (classes counted in Unicode as for the accounts), at most 1024. Checked before the backup starts: a password that breaks one writes nothing.
- 🗝️ **The instance key**: `secrets/instance.key` is in the archive when LibreFolio generated the key and can use it; never a key from `LIBREFOLIO_INSTANCE_KEY` or `LIBREFOLIO_INSTANCE_KEY_FILE`. A generated key that cannot be used (damaged, out of reach, over 4096 bytes, more than a restore reads back) is left out with `⚠️ The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore`; the archive is written all the same.
- 💽 **Space**: the encryption (`… encrypting`, after the usual phases) writes the `.lfbk` beside the zip in `backups/`: the zip's size is needed there again, plus 64 MB, otherwise `❌ Backup failed (backup_no_space): not enough free space`. The zip is removed once encrypted, or if the backup fails. After an abrupt interruption (power cut, `kill -9`), the next start of LibreFolio ends that backup as interrupted and removes what is left in `backups/.jobs/`, zip and copy of the database included.

??? note "❌ Password errors — what the messages mean"

    Nothing is written, exit code `1`.

    - `❌ A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal (password_required)`: `--encrypt` without a terminal to ask on, for example in cron. Empty password typed at the terminal: `❌ No password was typed (password_required)`; empty line through a pipe with `--password-stdin`: `❌ The standard input carried no password (password_required)`.
    - `❌ The two passwords differ (password_mismatch)`.
    - `❌ The password of a backup needs at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: <rules>)`: the codes of the rules broken, in this order: `min_length`, `uppercase`, `lowercase`, `digit`, `special`.
    - `❌ The password is longer than 1024 characters (password_too_long)`.
    - `❌ password file: <path> does not exist (password_unreadable)`, or `cannot be read (…)`, `is empty or blank`, `is not UTF-8 text`, `is larger than 65536 bytes, too large for a secret`, `is not a regular file`, `goes through a link inside the data directory: give the file itself, from outside it` («A file the command can trust» above).

    Both password options together, or an option that does not exist such as `--password`, stop the command before it starts, with the usage line and exit code `2`.

### 🗂️ What the Archive Holds

The archive has the layout of the data directory and holds only:

| Entry | What it is |
| --- | --- |
| `manifest.json` | The description of the archive, below |
| `sqlite/app.db` | The copy of the database |
| `custom-uploads/` | The files uploaded in the app |
| `broker_reports/` | The broker reports |
| `scenario_catalog/` | Your own stress scenarios, if you added any |
| `secrets/instance.key` | In a [secure archive](#backup-secure) only, when LibreFolio generated the instance key: its text, outside the manifest's list of files. A restore reads it to re-encrypt the saved secrets, and never unpacks it |

Everything else stays out: `secrets/` (but `secrets/instance.key` in a secure archive), `logs/`, `scheduler_state.json`, the `backups/` folder, the `.librefolio-production-data` marker and SQLite's working files next to the database: `app.db-wal`, `app.db-shm`, `app.db.post-migration.lock` and the `.bak` copies of the [post-migration fixes](cli_tools.md#post-migration-fixes). The copy of the database already holds what was waiting in `app.db-wal`. Symbolic links and special files are never followed nor archived.

!!! warning "🔑 The instance key is in a secure archive only"

    A clear archive leaves out `secrets/`, with the [instance key](configuration_secrets.md#instance-key). Back it up separately ([Filesystem Structure → What to Back Up](filesystem.md#what-to-back-up)) and keep the copy as private as the archives. Before you start LibreFolio on the data of a clear archive, put `secrets/` back with it: without its key, what LibreFolio encrypted can no longer be read. A [secure archive](#backup-secure) holds the key LibreFolio generated, never one from `LIBREFOLIO_INSTANCE_KEY` or `LIBREFOLIO_INSTANCE_KEY_FILE`: keep that one where you set it. With a copy of the key, a restore on another installation still reads the saved secrets of a clear archive: [The Instance Key of Another Installation](#backup-restore-instance-key).

??? info "📋 `manifest.json` — what it records"

    - the format, `librefolio-backup`, and its version;
    - the LibreFolio version that made the archive, how (`cli` for this command, `ui` for the web interface) and when, in UTC;
    - the database: the migration (Alembic) revision, the result of SQLite's integrity check, the number of foreign-key violations, the rows of each table and the ledger's control totals, the cash of every broker in each currency and the quantity of every position (an archive made before them has none);
    - every entry, the database first, with path, size and SHA-256;
    - whether the archive holds the instance key, and the SHA-256 of that entry: only a secure archive holds it.

### 🔍 Check an Archive

**Where: any installation**, with the server running or stopped; it needs no data directory, except for a secure archive (below). Docker: [inside the container](#backup-docker), with the container's path.

```bash
# Check every entry against the manifest, and show what the archive holds
pipenv run ./dev.py backup inspect /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip

# Faster: compare the entry names with the manifest, without reading the entries
pipenv run ./dev.py backup inspect /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --no-verify
```

Result: the report of the archive, and `✅ Every entry matches the manifest` once the size and SHA-256 of every entry are compared with the manifest.

| Option | Effect |
| --- | --- |
| `--no-verify` | Compares only the entry names, without reading them: `ℹ️ The entry names match the manifest; their contents were not read (--no-verify)` |
| `--password-file FILE`, `--password-stdin` | The password of a secure archive, from the same sources as `create` ([A Secure Archive](#backup-secure)); a `.zip` ignores them |
| `--identity-file FILE` | The private key of a [sealed archive](#backup-sealed) |

- 📋 The report: who made the archive and when (`Made by LibreFolio <version> (cli) on <date> UTC`), the database's migration revision, its size and integrity check, rows and tables, number and size of the files, whether the instance key is included.
- 🔐 A secure archive, recognised by its first bytes whatever its name, asks the password first, once. It is decrypted (`🔓 Decrypting <path>`) into a private folder `.decrypt-…` inside the data directory's `backups/`, removed at the end even if the command fails: that directory is needed, and room for the decrypted archive, about the size of the `.lfbk`. A folder left by an `inspect` interrupted abruptly (power cut, `kill -9`) is removed by the next `inspect`, or by the next start of LibreFolio, once it is an hour old: a younger one may be another `inspect`'s, still running. The report adds `Secure backup: decrypted with its password`. Wrong password: `❌ The password does not open this backup (wrong_password)`; `password_required`, `envelope_damaged` and `envelope_unsupported` are among the refusals of [Try a Restore on a Copy](#backup-restore-dry-run).
- ❌ It exits with `1` when entries are missing, differ from the manifest or are not in it (the first five of each kind), and when the file is not a readable archive: the message ends with a code, such as `archive_unreadable` (not a zip, or cut short), `manifest_missing`, `manifest_unknown_format` (not a LibreFolio backup) or `manifest_newer_format` (made by a newer LibreFolio: check it with that version or a newer one).

### 🔏 A Sealed Archive {: #backup-sealed }

A sealed archive is a `.tar` whose password is generated by LibreFolio and encrypted for one or two age public keys: only the matching private key opens it, the server that made it cannot. It is made for backups that run on their own, for example every night from cron. What it holds, how to keep and change the key: [Sealed Backups](backup_sealed.md#sealed).

1. **On a computer of yours, not on the server**: the private key must not stay on the server.

    ```bash
    # A key pair: the private key into a file of its own (0600, never over a file), the public key printed
    pipenv run ./dev.py backup keygen --identity-file ~/librefolio-backup-key.txt
    ```

    Result: the private key in the format of `age-keygen` (`# created:`, `# public key: age1…`, then `AGE-SECRET-KEY-1…`), readable by its owner only, never over an existing file (`❌ <path> already exists: a key file is never written over`); then `🔑 Public key, for --recipient or LIBREFOLIO_BACKUP_RECIPIENTS:` and the `age1…` line.

2. **Terminal of the server, LibreFolio folder** (Docker: `docker compose exec -T librefolio python dev.py backup create --sealed`).

    ```bash
    # A sealed archive for that public key (twice --recipient while a key is being changed)
    pipenv run ./dev.py backup create --recipient age1…

    # The same, for the keys of LIBREFOLIO_BACKUP_RECIPIENTS
    pipenv run ./dev.py backup create --sealed
    ```

    Result: `librefolio-backup-20261015-121500.tar`, with the usual rules of `-o` and of names; after the phases of a secure archive, `… sealing`, then `🔏 Sealed for 1 key: only the matching private key opens its password, and this server cannot.`

3. **Where the private key is**: check it, restore it or decrypt it with `--identity-file`.

    ```bash
    # Check, restore or decrypt it where the private key is
    pipenv run ./dev.py backup inspect librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt
    pipenv run ./dev.py backup restore librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt --dry-run
    pipenv run ./dev.py backup decrypt librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt -o backup.zip
    ```

    Result: `🔏 Sealed backup <path>: its password opened with <key file>`, then the command goes on as for a secure archive with its password.

| Option | Effect |
| --- | --- |
| `--recipient age1…` | Seals for that key; twice for two keys, while a key is being changed |
| `--sealed` | Seals for the keys of `LIBREFOLIO_BACKUP_RECIPIENTS` ([Environment Variables](configuration.md)); without `--recipient` |
| `--identity-file FILE` | Opens a `.tar` for `inspect`, `restore` and `decrypt`: a key file as `age-keygen` writes it, read before any switch of user, like `--password-file`: a Docker secret works |

Good to know:

- 🔑 **No password to give**: `--sealed` and `--recipient` go without `--encrypt`, `--password-file` and `--password-stdin`, otherwise the command stops before anything is written. It needs no terminal: it runs from cron as it is.
- 🗝️ **Never the instance key**, not even one LibreFolio generated: unlike a [secure archive](#backup-secure), a sealed archive leaves `secrets/instance.key` out.
- 💽 **Space**: sealing writes the `.tar` beside the `.lfbk`, so the work folder in `backups/` needs the `.lfbk`'s size again, plus 64 MB, otherwise `backup_no_space`.
- 🔓 **How it opens**: the command checks the `.tar` and its manifest, opens the password with the key, checks it against `backup.lfbk`, then copies `backup.lfbk` into a private folder of the system's temporary folder, removed at the end.
- ❌ A `.tar` without `--identity-file` stops with `sealed_backup_needs_key`; `--identity-file` with any other archive with `❌ --identity-file opens a sealed backup (.tar) only: <path> is not one`.
- 🧾 **The refusals**, at the end of the message: `sealed_identity_invalid` (the file holds no age key, or cannot be read), `sealed_no_identity` (no key of the file opens the password), `sealed_tar_invalid` (it does not hold the three files of a sealed archive, in order, as plain ustar files), `sealed_manifest_invalid` (its `manifest.json` does not describe it), `sealed_password_invalid` (what the key opened is not a password written by LibreFolio), then those of a secure archive: `wrong_password` (it does not open `backup.lfbk`) and `envelope_damaged`. Every message, with what to do: [Making or Opening a Sealed Backup](backup_moving.md#sealed-problems).

### 🧪 Try a Restore on a Copy {: #backup-restore-dry-run }

**Where: terminal of the server, LibreFolio folder** (Docker: [inside the container](#backup-docker)). It works on any installation with a data directory, a new one included: it never uses the instance's database, and the server can keep running.

```bash
# Check an archive for a restore, on a copy: the instance stays as it is
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --dry-run
```

Result: the archive is unpacked into a copy, `.restore/stage/<id>/` in the data directory, brought up to date and checked, then the report says what a restore would do and the copy is removed.

- ✅ It ends with `✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed.`, exit code `0`; `1` when the archive is refused or the restore blocked: one line with a code in parentheses, such as `❌ The file is not a LibreFolio backup (not_a_backup)`, and nothing of the copy is left.
- ♻️ Without `--dry-run`, the same check is the first half of a restore: [Restore an Archive](#backup-restore).
- 🔐 A [secure archive](#backup-secure) asks the password first, as `inspect` does, and is decrypted into the copy as `.restore/stage/<id>/archive.zip`, removed once unpacked. A check interrupted abruptly leaves that archive, or its part `archive.zip.part`: the next start of LibreFolio removes it.

**What it checks**, in six steps, stopping at the first one that refuses the archive (`… decrypting` for a secure archive, `… checking`, `… unpacking`, `… upgrading`, `… verifying`):

1. **A LibreFolio archive**, with its `manifest.json`: a data directory zipped by hand is not one. Every entry, before a byte is written: listed by the manifest (or announced, for the instance key), a plain file (not a folder, a link or an encrypted entry), unique name even ignoring upper and lower case, the manifest's size; the whole fits in the free space.
2. **Unpacked**: every entry into a new file of the copy, never through a link nor over another file, SHA-256 compared with the manifest. The schema of the database is read without running any of it: a trigger, a view or a virtual table, which LibreFolio never creates, refuses the archive (`database_foreign_objects`).
3. **The revision decides**: the migration (Alembic) revision, from the manifest and confirmed by the database.
    - the same as this LibreFolio's: restored as it is;
    - older: the copy is upgraded to this LibreFolio's revision, in a separate process, stopped after an hour;
    - unknown, most likely newer: `revision_unknown`. Update LibreFolio first: a database is never downgraded.

    Then the [post-migration fixes](cli_tools.md#post-migration-fixes) run on the copy, as at every start.

4. **Checked before and after**: before the upgrade the copy passes SQLite's integrity check, holds exactly the rows the manifest counted and no text that is not UTF-8 (LibreFolio writes none, and the server could not read it); after, it passes the integrity check again. Rows changed by a migration and broken references (foreign keys), kept as they are, are warnings, not refusals.
5. **Administrators**: without an active administrator in the backup, the restore is blocked: nobody could manage the instance afterwards.
6. **Saved secrets**: the instance keeps its own [instance key](configuration_secrets.md#instance-key). The saved plugin secrets (such as the API key of a data source) are re-encrypted on the copy with it when the archive holds the key that encrypted them, or you give it with `--instance-key-file` ([The Instance Key of Another Installation](#backup-restore-instance-key)); the others are counted, to enter again after the restore. A copy without secrets does not even read this instance's key.

**The report**:

- 📦 Who made the archive and when (`Made by LibreFolio <version> (<how>) on <date> UTC`), and what a restore does with the database: `this LibreFolio's own: restored as it is`, or `upgraded on the copy to <revision> (<n> migrations)`, then each migration with the first line of its description.
- 🩹 The post-migration fixes that changed something on the copy, if any.
- 🔢 Rows, tables and size of the database, then the tables whose rows changed with the upgrade, as `<table> (<before> → <after>)`, with `—` for a table that did not exist.
- 📁 Number and size of the files; `Secure backup: decrypted with its password` for a secure archive; `Instance key: included` or `Instance key: not included`, or `Instance key: not included; given with --instance-key-file` with that option; the saved keys of the data providers: `Saved provider keys: <n> re-encrypted with this instance's key`, and `⚠️ <n> saved provider keys cannot be read with this instance's key: enter them again after the restore` for those the archive's key, or the key given, did not read, or when there is no key.
- ⚖️ The ledger's control totals: the cash of every broker in each currency and the quantity of every position, from the transactions alone, with no price, exchange rate, cost or date. Recorded in the manifest at creation, read again on the copy once it is up to date. A difference is a warning, never a refusal: a migration may correct data. One of these lines:
    - `Ledger totals: the same as when the backup was made`;
    - `⚠️ Ledger totals differ from the backup's (<n> lines):`, then the lines that differ, cash first, at most 20: `broker <id>, <currency> cash: <before> → <after>` or `broker <id>, asset <id> quantity: <before> → <after>`, the backup's amount before the arrow and the copy's after it, `—` for zero. `… and <n> more` counts the lines left out;
    - `Ledger totals: not recorded in this archive`: an archive of a LibreFolio from before the totals, or whose totals could not be read at creation;
    - `Ledger totals: recorded by another version of the method, not compared`;
    - `⚠️ Ledger totals: could not be read on the copy`.
- 👑 The administrators, and what a restore will mean for everyone: `After a restore you sign in with one of them, with the password of then; every session open now ends.` and `Invitations and links sent before the restore will have expired: send them again if needed.`
- ⚠️ The warnings, which let the restore go on: `The upgrade changed the rows of some tables (listed above)`, `The backup's database has broken references: they are kept as they are`, `The upgrade added broken references to the copy`, `The ledger's totals differ from those the backup recorded (listed above)`, `The ledger's totals could not be read on the copy` or `Some currency codes in the backup are not ISO 4217 codes, names or numbers an earlier version saved: an edit of their rows is refused until they are corrected (./dev.py db currencies lists them after the restore)`, as [Currency Codes That Are Not ISO Codes](cli_tools.md) explains.
- 👥 A backup with more active accounts than `LIBREFOLIO_MAX_USERS` allows adds one line, once, with no names nor addresses: `⚠️ The backup holds <n> active accounts; this instance accepts <m> (LIBREFOLIO_MAX_USERS): at the first sign-in the administrator chooses who keeps access, the others are deactivated (not deleted)`. It only informs: `backup restore --yes` confirms and `--dry-run` exits with `0`, as for any backup.
- ⛔ The blocker: `❌ The backup has no active administrator: after a restore nobody could manage the instance`.

Good to know:

- 💽 The copy needs free space on the disk of the data directory: the unpacked content of the archive, plus twice its database for the upgrade, plus 64 MB (`backup inspect` shows those sizes); the archive is read where it is, never copied. A secure archive also needs room for the decrypted archive, about its own size, until it is unpacked. Not enough space → the check stops before unpacking, with the bytes needed (`no_space`); a disk that fills up during the check stops it too.
- 📦 `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` («Main Options» in [Environment Variables](configuration.md)) limits the unpacked size: the manifest's sizes are added up before the space check, and an archive over the limit is refused with `unpacked_too_large`, without unpacking anything. To lift the limit for one command, put `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` in front of it:

    ```bash
    # Host
    LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0 pipenv run ./dev.py backup restore <archive>

    # Docker
    docker compose exec -e LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0 librefolio python dev.py backup restore <archive>
    ```

    An unreadable limit stops the command before `🔎 Checking … on a copy`, exit code `1`: `❌ LIBREFOLIO_BACKUP_MAX_RESTORE_MB: expected a whole number of megabytes, 0 for no limit (backup_restore_unavailable)`.

- 🚦 One archive at a time: with another check running, `❌ Another archive is being checked (from the web interface or another command): try again when it ends`.
- 🆕 Only the data directory is needed, otherwise `❌ No data directory at <path>`. As with `-o`, a relative path starts at the project root.
- 🔗 Keep `.restore/` and `.restore/stage/` real folders: a link, or a file, in their place → `❌ <path> is not a plain folder (a link, or a file): the copy is made in a folder of the data directory`.

??? note "❌ Refusals — what the codes mean"

    | Code | Why the archive is refused |
    | --- | --- |
    | `not_a_backup` | Not a zip, or a zip without the manifest LibreFolio writes, such as a data directory zipped by hand |
    | `password_required` | A secure archive, and no password: no terminal to ask on, and neither `--password-file` nor `--password-stdin` |
    | `wrong_password` | The password does not open the secure archive: not the one it was made with, or the start of the file was changed |
    | `envelope_damaged` | The secure archive is damaged, cut short, or was changed after it was made |
    | `envelope_unsupported` | The secure archive comes from a newer LibreFolio, or asks for settings this one does not accept: update LibreFolio first |
    | `instance_key_unreadable`, `instance_key_invalid` | The file given with `--instance-key-file` cannot give the key, or the key is shorter than 32 characters: [The Instance Key of Another Installation](#backup-restore-instance-key) |
    | `archive_unreadable`, `archive_damaged` | The file cannot be read, or the zip is damaged |
    | `manifest_newer_format` | The archive format is newer than this LibreFolio reads: update LibreFolio first |
    | `manifest_invalid`, `manifest_unreadable`, `manifest_too_large` | The manifest is damaged or not valid |
    | `unexpected_entry`, `missing_entry` | The archive holds an entry the manifest does not list, or lacks entries it lists; for the instance key, an entry the manifest does not announce, or one it announces and the archive lacks |
    | `duplicate_entry` | An entry appears twice, even when only the case of its name changes, or stands where the folder of another entry must be |
    | `not_a_file`, `encrypted_entry`, `unsupported_entry` | An entry is a folder or a link, is encrypted, or uses a compression LibreFolio does not write |
    | `too_many_entries` | The archive holds more than 500,000 entries |
    | `checksum_mismatch` | An entry's size or SHA-256 differs from the manifest: the archive is damaged or was changed |
    | `unpacked_too_large` | Unpacked, the archive would exceed what this installation accepts for a restore, from the manifest's sizes: `LIBREFOLIO_BACKUP_MAX_RESTORE_MB`. Nothing is unpacked |
    | `no_space` | Not enough free space for the copy |
    | `stage_failed` | The copy could not be written: the error printed just above gives the cause |
    | `database_damaged` | The backup's database fails SQLite's integrity check, before or after the upgrade, SQLite cannot read its schema, or it holds text that is not UTF-8 (another program wrote to it, or it was changed) |
    | `database_foreign_objects` | The backup's database holds a trigger, a view or a virtual table, which LibreFolio never creates: it was not made by LibreFolio, or was changed. Use another backup |
    | `manifest_mismatch` | The backup's database is not the one its manifest describes |
    | `revision_missing` | The backup's database records no migration revision |
    | `revision_unknown` | The backup comes from a newer LibreFolio, or not from this one: update LibreFolio, then check it again |
    | `upgrade_failed` | The upgrade of the copy failed or lasted more than an hour (the error printed just above gives the cause), or did not reach this LibreFolio's revision |
    | `post_migration_failed` | A post-migration fix failed on the copy: the error printed just above gives the cause |
    | `head_unknown` | This LibreFolio cannot read its own migration scripts |

### ♻️ Restore an Archive {: #backup-restore }

**Where: where the server runs** — terminal of the server, LibreFolio folder; with Docker [inside the container](#backup-docker). The restore is recorded for the path of the data directory: a server that finds its data directory under another path does not apply it.

1. **Run the command.**

    ```bash
    # Check the archive on a copy, then restore it at the next start of the server
    pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip
    ```

    Result: the same check on a copy and the same report as [Try a Restore on a Copy](#backup-restore-dry-run); if the archive can be restored, the question:

    ```text
       Type "restore" to restore this archive at the next start of the server:
    ```

2. **Type `restore`**, in lower case; spaces around it do not count. Anything else, `Restore` or an empty line included, ends with `Nothing restored: the copy was removed.` and exit code `1`.

    Result, exit code `0`:

    ```text
    ✅ The restore waits for the next start of the server: restart LibreFolio to apply it.
       That start replaces the database and the files, and ends every session: sign in with an administrator of the backup.
       ./dev.py backup pending shows it; ./dev.py backup pending --cancel drops it.
    ```

    Nothing has changed yet: the server keeps running on its data, and the checked copy waits in `.restore/stage/<id>/`, however long it takes.

3. **Restart LibreFolio** when it suits you: stop the whole server, then [start it again](cli_tools.md#start-the-server); with Docker, `docker compose restart librefolio` ([Back Up with Docker](#backup-docker)). If the server is stopped, its next start applies the restore.

    Result: that start applies the restore before it reads any data (below).

| Option | Effect |
| --- | --- |
| `--dry-run` | The check only: [Try a Restore on a Copy](#backup-restore-dry-run) |
| `--yes`, `-y` | Confirms without asking. Without a terminal, for example in a script, it is required: otherwise `❌ No terminal to ask on: add --yes to confirm the restore. Nothing restored: the copy was removed.`, exit code `1` |
| `--password-file FILE`, `--password-stdin` | The password of a [secure archive](#backup-secure), required without a terminal |
| `--instance-key-file FILE` | The instance key of another installation: [below](#backup-restore-instance-key) |
| `--identity-file FILE` | The private key of a [sealed archive](#backup-sealed) |

**What that start does:**

1. 🛑 **Only a start of the whole server.** Every server process holds a lock on the data directory from the beginning of its start until it exits. A start that finds it held by another process (a worker that uvicorn starts again beside its siblings, with `--workers`; a second server on the same directory) leaves the restore waiting (`server_running`). Restart the whole server, never one worker. A start that finds the restore applied by another server still running, or by another start, stops instead of serving data whose restore is not completed.
2. 🔀 **The swap.** The instance's `sqlite/`, `custom-uploads/`, `broker_reports/` and `scenario_catalog/` swap places with those of the copy: renames inside the data directory, instant whatever the size. The instance's folders go to `.restore/previous/`.
3. 🔒 **What stays.** `secrets/`, `logs/`, `scheduler_state.json` and `backups/` are not touched: the instance keeps its [instance key](configuration_secrets.md#instance-key), its logs and its archives.
4. ✅ **The first start must complete.** It goes on, on the restored data, already at this LibreFolio's revision. Once through, before it answers anyone, it ends every session, revokes the one-time links of the backup and removes the former data and the copy: the restore is completed.
5. ↩️ **Otherwise, back as before.** If that first start fails (a migration, a damaged file), the next start puts the data back as it was by itself and records the rollback with the reason ([Follow or Cancel a Restore](#backup-pending)). With Docker the container restarts by itself; if nothing restarts the server, start it yourself.

**After the restore:**

- 🔑 Everyone signs in again, on every device, with an account of the backup and the password of then. The report of the check names the administrators of the backup.
- 🔗 No link sent before the restore works any more (invitations, password resets, email verifications), not even those still in the backup: send new ones.
- 📧 An account the backup held waiting for its email verification loses its link and stops waiting: the sign-in page does not send it another one and answers that the account is disabled. An administrator activates it in [Users & Invitations](users.md#actions), with the address staying unverified, or deletes it ([Delete an Account](users.md#delete)), so that its owner signs up again and receives a new link. Such an account never signed in: it holds no data.
- 🆘 If nobody remembers an administrator's password of then, whoever runs the server creates a reset link with [`user reset-link`](cli_tools.md), or sets a new password with `user reset`. Once in, an administrator sends reset links to the others from [Users & Invitations](users.md#reset-links).

Good to know:

- 🚦 One restore at a time: while one waits or is being applied, `backup restore` stops before the check with `❌ A restore already waits for the next start: ./dev.py backup pending --cancel drops it (restore_already_pending)`, exit code `1`. It stops there too when it cannot read the state of the restore, because it cannot tell whether one waits: `❌ The state of the restore cannot be read: <reason> (restore_state_unreadable)`, exit code `1`, nothing checked. `--dry-run` still works.
- ❌ If the confirmation is refused, the command prints one line with a code, removes the copy and exits with `1`: `restore_stage_outdated` (LibreFolio updated between the check and the confirmation), `restore_stage_expired` (question waiting more than 24 hours), `restore_already_pending` (another restore confirmed meanwhile). Run the command again; after `restore_stage_outdated`, check the archive again.
- 🔗 Keep the four folders real folders of the data directory: one that is a link, or mounted on its own, cannot be swapped. The start leaves the data as it is and records the rollback with `swap_failed`.
- 💽 The swap needs no space of its own: the copy of the check becomes the instance's data, and the former data is removed once the first start completes.
- 🗝️ The restore keeps this installation's instance key. The saved secrets of an archive of another installation are re-encrypted with it by the check if the archive holds the key that encrypted them (a [secure archive](#backup-secure), with a key LibreFolio generated) or if you give it with `--instance-key-file` ([The Instance Key of Another Installation](#backup-restore-instance-key)). Otherwise they cannot be read here: the report counts them, to enter again after the restore, unless you put that installation's key back first ([Saved Secrets and the Instance Key](configuration_secrets.md#plugin-secrets)). See «The instance key is in a secure archive only» above.

### 🗝️ The Instance Key of Another Installation {: #backup-restore-instance-key }

**Where: terminal of the server, LibreFolio folder**, with the key file outside the data directory (Docker: a secret only root reads, [below](#backup-docker)).

```bash
# A clear archive of another installation, with the instance key of that installation
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --instance-key-file ~/old-instance.key
```

Result: the check re-encrypts on the copy the saved plugin secrets (such as the API key of a data source) with this instance's key, which stays as it is.

It is needed because a clear archive leaves the instance key out, and so does a secure archive whose key came from the environment: its saved secrets open only with the key of the installation that made it. It works with or without `--dry-run`.

- 📁 The report says `Instance key: not included; given with --instance-key-file`, then `Saved provider keys: <n> re-encrypted with this instance's key`.
- 📄 **The file**: a copy of the old installation's `secrets/instance.key`, the file of its `LIBREFOLIO_INSTANCE_KEY_FILE` as it is, or the value of its `LIBREFOLIO_INSTANCE_KEY` written into a file as it was in the variable, spaces included. Only a byte order mark at its start and the line breaks at its end are dropped, as for `--password-file`: a key that worked as a variable works the same in the file.
- 🔑 Read first, as the user who started the command, before the switch to the owner of the data directory, like `--password-file`: with `docker compose exec` a Docker secret only root reads works. Same rule as `--password-file`, «A file the command can trust» in [A Secure Archive](#backup-secure): keep it outside the data directory.
- 🙈 The key is never printed. Only the command line takes it: the web interface does not, and a restore from Settings › Administration › Backup counts those secrets as unreadable.
- ℹ️ An archive with its own key is restored with that one, whatever the file holds: `ℹ️ The archive carries its own instance key: --instance-key-file is not used`.
- ⚠️ A key that reads no saved secret is not the key of the installation that made the backup: `⚠️ The key given with --instance-key-file reads none of the saved provider keys: it is not the key of the instance this backup came from`, before the line that counts them. If this instance's key cannot be used, or there is none and the check cannot create it (`secrets/` not writable), nothing is re-encrypted, whatever the key given: `⚠️ This instance's own key cannot be used, so nothing was re-encrypted with the key given: <problem>`, with the problem of the start log's `The instance key cannot be used: …` («Startup Checks» in [Environment Variables](configuration.md)) or, without a key, `<path>: there is no instance key yet, and it could not be created`. The secrets already under this instance's key, as in an archive of this same instance, stay as they are.
- ❌ It exits with `1`, before checking anything, when the file does not give the key: `❌ instance key file: <path> does not exist (instance_key_unreadable)`, or `cannot be read (…)`, `is empty or blank`, `is not UTF-8 text`, `is larger than 65536 bytes, too large for a secret`, `is not a regular file`, `goes through a link inside the data directory: give the file itself, from outside it`. A key shorter than 32 characters stops it before the copy is made: `❌ The instance key given is too short: an instance key has at least 32 characters (instance_key_invalid)`.

### ⏳ Follow or Cancel a Restore {: #backup-pending }

**Where: terminal of the server, LibreFolio folder** (Docker: [inside the container](#backup-docker)); `--recover previous` only with LibreFolio stopped.

```bash
# The restore waiting for the next start, or the last one
pipenv run ./dev.py backup pending

# Drop the restore waiting, and its checked copy (the same as --recover cancel)
pipenv run ./dev.py backup pending --cancel

# When the state of the restore cannot be read: put the data of before back (LibreFolio stopped)
pipenv run ./dev.py backup pending --recover previous

# For a script: the state as one JSON line, and the same actions with fixed exit codes
pipenv run ./dev.py backup pending --json
pipenv run ./dev.py backup pending --recover cancel --json
```

Result: `backup pending` changes nothing and exits with `0`, except when it cannot read the state of the restore ([An Unreadable Restore State](#backup-pending-unreadable)). It shows one of these lines:

| It prints | What it means |
| --- | --- |
| `ℹ️ No restore waits for the next start` | No restore confirmed, or the last one dropped |
| `⏳ A restore waits for the next start of the server`, then `backup made by LibreFolio <version> on <date> UTC; confirmed by <who> on <date> UTC` | Confirmed, not applied yet. `<who>` is `cli` for this command, otherwise the username of the administrator who confirmed it |
| `⏳ A restore is being applied by the server` | A start applied it and has not completed yet. If that process ended abnormally, the next one puts the data back |
| `✅ The last restore was applied on <date> UTC: backup made by LibreFolio <version> on <date> UTC` | Completed |
| `⚠️ The last restore was rolled back on <date> UTC, the data is as it was before: <reason> (<code>)` | Undone, for the reason in the table below |

| Option | Effect |
| --- | --- |
| `--cancel` | Drops the restore waiting, with its copy: [below](#backup-pending-unreadable) |
| `--json` | The state as one JSON line, for scripts: [For Scripts](#backup-pending-json) |
| `--recover CHOICE` | `previous` or `cancel`, with fixed exit codes: [For Scripts](#backup-pending-json) |

When a start found a restore waiting without applying it, one more line says why, and the restore keeps waiting:

- `⚠️ At the last start a backup was running: the next start applies it (backup_running)`: a backup was running at the start, for example a `backup create` from the command line.
- `⚠️ It was confirmed for another data directory (<path>): this one does not apply it (other_data_directory)`: the server found its data directory under a different path than the one of the confirmation, for example a copy of the data directory. Drop it with `--cancel`, then run `backup restore` where the server runs.
- `⚠️ At the last start another server process was serving the data directory: restart the whole server to apply it (server_running)`: a worker restarted while the others were serving (`--workers`), or another server on the same data directory. Restart the whole server.

| Code | `<reason>` | What to do |
| --- | --- | --- |
| `first_start_failed` | `the first start after it did not complete` | The log of that start gives the cause |
| `swap_interrupted` | `the start that applied it was interrupted` | Nothing: a start stopped during the swap, and the next one undid it |
| `swap_failed` | `its folders could not be moved into place` | Make the four folders real folders of the data directory, neither links nor separate mounts |
| `stage_missing` | `its checked copy was gone` | The copy in `.restore/stage/` was removed or changed: check the archive again |

A rollback also removes the restored data and the copy: to try again, run `backup restore` again. If even going back to the former data fails (disk, permissions), LibreFolio does not start: the log holds `The data directory is half restored: the restore could not be undone, and LibreFolio does not start on it`, and every start tries again.

#### 🧩 An Unreadable Restore State {: #backup-pending-unreadable }

The state of the restore, `.restore/restore.json`, can become unreadable: owner or permissions changed, a disk error, a link or a folder in its place, content LibreFolio did not write. A restore may have stopped half way, and LibreFolio does not know which data it holds. `backup pending` says so and exits with `1`:

```text
❌ The state of the restore cannot be read: <why>: a restore may have stopped half way. LibreFolio serves no data until you choose (restore_state_unreadable: <reason>)
   The data of before is kept in .restore/previous/: sqlite, user_files
   Checked copies kept: 1 (none is removed while the state cannot be read)
👉 Stop LibreFolio, then run ./dev.py backup pending --recover previous: it puts the data of before back.
```

`<reason>` is `io` (the file system refuses it: give `.restore/` and its files back to the user that runs LibreFolio, then run `backup pending` again, which may be enough), `not_a_file` or `invalid`. While the state cannot be read, no checked copy is removed, neither by the server's clean-up nor by Settings › Administration › Backup, and no restore can be confirmed.

**`--recover previous`**, with LibreFolio stopped, puts the data of before back from the folders: each folder kept in `.restore/previous/` returns to its place, and the one it replaces goes to `.restore/failed/`. A completed restore kept no former data: its data stays. The unreadable state is kept as `.restore/restore.json.unreadable-<date>` for a look, and never read again. Then start LibreFolio on the data of before, or restore a backup again with `backup restore`. With LibreFolio running it stops with `(restore_in_use)`, exit code `5`; with a readable state, or none, with `(restore_nothing_to_recover)`, exit code `3` ([For Scripts](#backup-pending-json)). Run twice, the second run changes nothing.

**`--cancel`**, the same as `--recover cancel` but with the exit codes below, drops the restore waiting with its checked copy, whoever confirmed it:

| Outcome | It prints | Exit |
| --- | --- | --- |
| Dropped | `✅ The restore waiting for the next start was dropped, with its copy: the data stays as it is` | `0` |
| Dropped, copy not removed (permissions, disk) | `✅ The restore waiting for the next start was dropped: the data stays as it is` and `⚠️ Its checked copy could not be removed: it goes when its check expires`. With an error, the log above holds `The copy of a cancelled restore could not be removed: it goes when its check expires`; a copy left without an error, such as one with a read-only folder, has none. LibreFolio tries again at its first start once the check is 24 hours old | `0` |
| Not droppable, for a file-system error before (the lock, or removing the state) | `❌ The restore could not be cancelled: <reason>. It still waits for the next start (restore_cancel_failed)` | `1` |
| Unreadable state | The `restore_state_unreadable` line of `backup pending` | `1` |
| No restore waiting, or one already being applied | `❌ No restore waits for the next start: nothing to cancel (restore_not_pending)` | `1` |

#### 🤖 For Scripts: --json and --recover {: #backup-pending-json }

A script, or a machine that reaches the server over `ssh`, reads the state with `--json` and acts with `--recover CHOICE`: nothing is asked on the terminal, and the exit codes are fixed.

**The JSON line.** With `--json`, `backup pending` writes exactly one line on stdout: a JSON object, then a newline, no colour. Everything else, LibreFolio's log lines included, goes to stderr. It exits with `0` whenever the line is printed: an unreadable state is a state, not an error.

| Key | Value |
| --- | --- |
| `state` | `none`, `pending`, `in_progress`, `committed`, `rolled_back` or `unreadable` |
| `reason` | The rollback reason of a `rolled_back` state (`first_start_failed`, `swap_interrupted`, `swap_failed`, `stage_missing`), or `io`, `not_a_file`, `invalid` for an `unreadable` one; `null` otherwise |
| `waiting` | Why a start did not apply a restore that waits: `backup_running`, `other_data_directory`, `server_running`, or `null` |
| `backup_created_at` | When the backup of the restore was made, as `2026-10-23T03:00:12Z` (UTC); `null` with no state, or an unreadable one |
| `safety_copy` | `{"present": true, "at": "<date>Z"}` when the data of before a swap is in `.restore/previous/`, otherwise `{"present": false, "at": null}` |
| `choices` | The words `--recover` accepts now, in the table below |

After a `--recover`, the line describes the state **after** it and adds `recover`, `{"choice": "<word>", "done": true}` or `false`, and, with an exit code other than `0`, `error`, the word of the exit-code table.

| `state` | It means | `choices` |
| --- | --- | --- |
| `none` | No restore confirmed, or the last one dropped | none |
| `pending` | A restore waits for the next start | `cancel` |
| `in_progress` | A start is applying it, or has applied it and has not completed yet | none |
| `committed` | The last restore is completed | none |
| `rolled_back` | The last restore was undone, with its `reason` | none |
| `unreadable` | The state cannot be read: [An Unreadable Restore State](#backup-pending-unreadable) | `previous` |

```json
{"state":"unreadable","reason":"invalid","waiting":null,"backup_created_at":null,"safety_copy":{"present":true,"at":"2026-10-23T03:00:12Z"},"choices":["previous"]}
{"state":"pending","reason":null,"waiting":"server_running","backup_created_at":"2026-10-22T21:30:05Z","safety_copy":{"present":false,"at":null},"choices":["cancel"]}
```

The line never holds a username, an email, a path or an identifier: who confirmed, the data directory and the checked copy are not in it. `safety_copy.at` is the moment the restore was applied, or, with an unreadable state, the last change of `.restore/previous/`.

**The exit codes.** `--recover previous` puts the data of before back when the state cannot be read, with LibreFolio stopped; `--recover cancel` drops the restore waiting, with its checked copy. The same with or without `--json`:

| Exit | When | `error` in the line |
| --- | --- | --- |
| `0` | Done: the data of before is back, or the restore waiting was dropped | none |
| `2` | A usage error: `--recover` without a choice, `--recover` with `--cancel`, or `--json` with `--cancel` (use `--recover cancel`) | none: the line is not written |
| `3` | Nothing to recover: no restore state, or the choice was already done | `nothing_to_recover` |
| `4` | The choice is not valid in this state, such as `previous` while the state can be read, `cancel` while it cannot, or a word that is not a choice: nothing changes | `choice_not_valid` |
| `5` | It failed: LibreFolio is running on this data directory (`restore_in_use`), a folder cannot be moved back (`restore_apply_failed`), the restore cannot be dropped (`failed`): nothing is claimed done. With a missing data directory, `5` too, but no line: stdout empty, stderr says why | `restore_in_use`, `restore_apply_failed` or `failed` |

Run again, a choice changes nothing: the second `--recover previous` finds no unreadable state, moves no folder, adds nothing to `.restore/failed/` and exits with `3`; the same for a second `--recover cancel`. A script may repeat `previous` or `cancel` until it reads `0` or `3`.

A script that reads the state and recovers, on a server where LibreFolio is stopped:

```bash
state=$(pipenv run ./dev.py backup pending --json 2>/dev/null)

if [ "$(echo "$state" | jq -r '.choices | index("previous") != null')" = "true" ]; then
    pipenv run ./dev.py backup pending --recover previous --json 2>/dev/null
    case $? in
        0|3) echo "data of before is back" ;;
        5)   echo "failed: stop LibreFolio, read the log" >&2; exit 1 ;;
    esac
fi
```

### 🔓 Decrypt a Secure Archive {: #backup-decrypt }

**Where: any installation**, server running or stopped; it needs no data directory. Docker: [inside the container](#backup-docker), with `-o` where the server's user can write.

```bash
# The zip inside a secure archive, to use it by hand
pipenv run ./dev.py backup decrypt /mnt/nas/librefolio/librefolio-backup-20261015-121500.lfbk -o /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip
```

Result: the zip held in the [secure archive](#backup-secure), the one `backup create` writes without a password, with `secrets/instance.key` if the secure archive holds the key.

| Option | Effect |
| --- | --- |
| `-o`, `--output FILE` | Required: the zip's file, which must not exist yet. An existing one is refused before the password, `❌ <path> already exists: choose another name`, nothing written. Relative path from the project root, as with `create` |
| `--password-file FILE`, `--password-stdin` | The password, otherwise asked once at the terminal ([A Secure Archive](#backup-secure)) |
| `--identity-file FILE` | The private key of a [sealed archive](#backup-sealed) |

- ✅ It ends with `✅ Decrypted: <path> (<size>)` and `🔒 It holds every user's data in clear: keep it private, and remove it once used.`; with the instance key, a last line: `🔑 It also holds the instance key: with it, every saved provider key can be read.`
- ♻️ `inspect` and `restore` take that zip as any other, and its key still re-encrypts the saved secrets. To restore a secure archive it is not needed: `backup restore` takes the `.lfbk` as it is.
- 🔒 The zip holds every user's data in clear, and only its owner reads it (`0600`): the user who ran the command, or the server's user when the command switched to it.
- 👤 Where there is a data directory and you run it as root, for example with `docker compose exec`, it reads `--password-file` first as root (a root Docker secret works), then switches to the owner of the data directory, as the other commands do: the zip belongs to the server's user, and `-o` must be writable by that user ([Back Up with Docker](#backup-docker)). If it cannot switch, it stops before reading the archive or asking the password: `❌ cannot switch to the owner of <path> (<uid>:<gid>): <reason>. Run the command as that user.`
- ❌ It exits with `1` when it cannot read the file, such as one only root reads once switched to the server's user (`❌ Cannot read <path>: <reason> (archive_unreadable)`, before the password), when the file is not a secure archive (`❌ <path> is not a secure backup: a plain .zip needs no decrypting (not_an_envelope)`), when the password does not open it (`wrong_password`), when it is damaged (`envelope_damaged`: nothing is left at `-o`) or from a newer LibreFolio (`envelope_unsupported`), and when it cannot write at `-o` (`❌ Cannot write <path>: <reason>`, once the password is given: nothing is left there).

### 🚚 Use an Archive on Another Installation

[`backup restore`](#backup-restore) restores an archive on the installation where you run it, with that installation's `secrets/`. To start another installation by hand on the data of an archive instead, with the `secrets/` of the installation that made it, for example when you move LibreFolio:

1. **Installation that receives the data, terminal**: first, check the archive with `backup restore <archive> --dry-run` ([Try a Restore on a Copy](#backup-restore-dry-run)): without changing anything, it tells you whether that LibreFolio takes the archive, which migrations it will apply and which administrators you will sign in with. Then **stop LibreFolio**.
2. **Empty data directory** (`LibreFolio-data/` with Docker Compose): if it holds anything, move it aside first: nothing of the old data may mix with the archive's, not even SQLite's `app.db-wal` and `app.db-shm`. **Unzip the archive** there; a secure archive is decrypted into its zip first ([Decrypt a Secure Archive](#backup-decrypt)).
3. **`secrets/` in the data directory**: put it back from the copy saved separately. The zip of a secure archive with the key already brings `secrets/instance.key`: give the folder mode `0700` and the file `0600` (`chmod`), otherwise the start log shows a warning.
4. **Start LibreFolio**, the version that made the archive or a newer one: the pending migrations run by themselves at start.

Good to know:

- ⛔ LibreFolio never downgrades a database: an archive of a newer version needs that version or a newer one, and an older one does not start on it. `backup inspect` shows the version that made the archive; `backup restore --dry-run` refuses it with `revision_unknown`.
- 🧹 The `manifest.json` left at the root of the data directory is harmless: you can delete it.
- 👤 With Docker, the container gives the data directory to its user at every start: the owner of the unzipped files does not matter. On a host installation, unzip as the user that runs LibreFolio.
- 🗝️ The key of a secure archive works only where neither `LIBREFOLIO_INSTANCE_KEY` nor `LIBREFOLIO_INSTANCE_KEY_FILE` is set: a key set there wins over `secrets/instance.key`. Never put it in place of a key already in use: what was saved with that key would become unreadable. An installation with its own key takes the archive with [`backup restore`](#backup-restore), which re-encrypts the saved secrets.

### 🐳 Back Up with Docker {: #backup-docker }

**Where: terminal of the server, folder of `docker-compose.yml`.** The command runs inside the container, where the data directory is `/app/backend/data/prod-docker`.

```bash
# Write an archive: on the host, it appears in its own folder of ./LibreFolio-data/backups/
docker compose exec librefolio python dev.py backup create

# Check it, with its path inside the container
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# Try a restore of it on a copy: the instance stays as it is
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip --dry-run

# Restore it: the same check, then type "restore" to confirm
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# Restart the container: its start applies the restore
docker compose restart librefolio

# Then see how it went
docker compose exec librefolio python dev.py backup pending
```

Result: as on the host; the archive of `backup create` is in a folder of its own, such as `/app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/`, that is `./LibreFolio-data/backups/` on the host.

- 👤 `docker compose exec` runs as root: the command switches to the owner of the data directory, `backup decrypt` included, and what it writes belongs to the server's user. If it cannot switch, it stops and asks you to run it as that user: `docker compose exec --user <uid>:<gid> librefolio python dev.py backup create`, with the numbers from the message.
- 📂 `-o` and the archives of `inspect` and `restore` are paths inside the container. An archive that is on the host: copy it into `LibreFolio-data/` first, for example into `LibreFolio-data/backups/`. An archive to write outside `LibreFolio-data/backups/`: a folder mounted from the host, writable by the server's user; anywhere else it stays inside the container and is lost when the container is recreated.
- 🔑 `restore` and `decrypt` read the archive as the server's user: one written by `backup create` is fine, one you copied must be readable by that user, otherwise `archive_unreadable`. With the official image, `sudo chown 1000:1000 <archive>` on the host.
- ⌨️ `docker compose exec` gives the command a terminal to ask on. Without one, for example `docker compose exec -T` in a script, add `--yes`.
- 🔐 [Secure archive](#backup-secure): `--encrypt` asks the password on that terminal. With `-T`, for example from cron, use `--password-file` and a Docker secret, such as `/run/secrets/backup_password`: [the example](backup_restore.md#command-line) in Backup, Restore and Moving Your Instance shows the lines to add to `docker-compose.yml`. The zip of `backup decrypt` belongs to the server's user: give it an `-o` that user can write, in `LibreFolio-data/backups/` or in a folder mounted from the host: `docker compose exec librefolio python dev.py backup decrypt /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.lfbk -o /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip`.
- 🔏 [Sealed archive](#backup-sealed), without a terminal: `docker compose exec -T librefolio python dev.py backup create --sealed` reads `LIBREFOLIO_BACKUP_RECIPIENTS` from the container's environment, which `env_file: .env` fills; after a change of `.env`, `docker compose up -d` recreates the container. To open one in the container, give `--identity-file` a path inside it; better, open it on your computer, where the private key is ([Open a Sealed Backup](backup_sealed.md#sealed-open)).
- 🔁 After a first start that fails on the restored data, the container restarts by itself (`restart: unless-stopped`, in both compose files LibreFolio ships), and that start puts the data back as it was.
- 🔒 On the host, the archives belong to the container's user, and only that user reads them: with another host user, copy them with `sudo cp -a`.
- 💻 From a source checkout, `./dev.py docker exec backup create` does the same.

---

## 🔗 Related

- 📄 **[Command-Line Tools](cli_tools.md)** — Start the Server, Manage Users, Maintain the Database, …
