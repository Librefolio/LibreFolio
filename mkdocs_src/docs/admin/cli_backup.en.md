# 💾 CLI Admin Tools: Backups

This page is part of the guide to the command-line tools. It covers the **backup** commands: creating, checking and restoring an archive, following a restore, and backing up with Docker.

The rest of the guide starts on [Command-Line Tools](cli_tools.md).

---

## 💾 Back Up the Instance {: #backup }

`backup create` puts the whole instance in one zip archive, while the server keeps running: the database, the uploaded files, the broker reports and your own stress scenarios. With `--encrypt`, it makes a [secure archive](#backup-secure), encrypted with a password you choose, which `backup decrypt` turns back into its zip. With `--sealed` or `--recipient`, it makes a [sealed archive](#backup-sealed), whose password only a private key of yours opens, for backups that run on their own. `backup inspect` checks an archive and shows what it holds, `backup restore --dry-run` tries a restore of it on a copy, leaving the instance as it is, and `backup restore` restores it at the next start of the server. To copy the data directory by hand instead, see [Backup](filesystem.md#backup).

### 📦 Create an Archive

```bash
# Write an archive into <data dir>/backups/
pipenv run ./dev.py backup create

# Write it into another folder, which must already exist
pipenv run ./dev.py backup create -o /mnt/nas/librefolio/

# Or give the archive a name of your own
pipenv run ./dev.py backup create -o /mnt/nas/librefolio/before-update.zip

# A secure archive (.lfbk): the password is asked twice
pipenv run ./dev.py backup create --encrypt -o /mnt/nas/librefolio/
```

- 🟢 The server keeps working, and writing, during the backup: the database is copied with SQLite's `VACUUM INTO`, a consistent snapshot, then SQLite's integrity check and foreign-key check run on the copy.
- 🏷️ The archive is named after the moment the backup starts, in UTC: `librefolio-backup-20261015-121500.zip`, or `.lfbk` for a [secure archive](#backup-secure). In a folder that already holds a file with that name, after two backups in the same second for instance, it becomes `librefolio-backup-20261015-121500-2.zip`, then `-3`, and so on: an archive never replaces a file.
- 📁 `--output` (`-o`) is checked before the backup starts, and the command must be able to write there. An existing folder receives the archive under its default name. Any other path is the archive's file, even one that ends with `/`: a folder that does not exist yet becomes the archive's name. That file must not exist yet, and its name is never changed. Its missing folders are created only when the archive is moved there, so a failed backup leaves no empty folder behind. Prefer absolute paths: a relative one starts at the project root, wherever you run the command from.
- 💽 Before writing anything, the command checks the free space where it builds the archive, in the data directory's `backups/` folder, even with `-o`: about twice the size of the database, plus the files, plus a small margin. When it is short, or when the disk or a quota fills up during the backup all the same, the command stops with `❌ Backup failed (backup_no_space): not enough free space`. When `-o` is on another disk, the space there is checked once the archive is built and its size known.
- 🛟 If the finished archive cannot go to `-o` (a file with that name appeared meanwhile, its folders cannot be created, the other disk is short of space, a write error), it is put in `backups/` instead, and the command exits with `1`. A move that fails half-way leaves no partial file behind.
- 🚦 One backup runs at a time: while another one is running, the command stops and asks you to try again when it ends.
- ✅ It ends with `✅ Backup written: <path>`, the size and the time taken, any warnings, and a reminder: `🔒 The archive holds every user's data: keep it private.`, or for a secure archive `🔐 Encrypted with your password: only that password opens it, and LibreFolio cannot recover a lost one.` It exits with `0` when the archive is where you asked, warnings included, and `1` otherwise.
- 🔒 Without a password, the archive is not encrypted: LibreFolio writes it, like a secure one, so that only its owner can read and write it (`0600`). Keep it, and every copy, as private as the data directory.
- 🗑️ LibreFolio never deletes the archives it puts in `backups/`: they stay there until you remove them. That folder is on the same disk as the data, so copy them to another disk, a NAS or off-site, or write them there directly with `-o`.
- 🔗 Keep `backups/` a real folder, never a link to a NAS or another disk: every archive is built inside it first, even with `-o`. A link, or a file, in its place stops the command with `❌ <data dir>/backups is not a plain folder (a link, or a file): …`.
- 🧪 `backup --test-db create` backs up the test data directory instead: a development option.

??? note "⚠️ Warnings and errors — what the messages mean"

    **Warnings**: the archive is written all the same.

    - `The database failed its integrity check` or `The database has foreign-key violations`: the archive keeps the database as it is, and `backup inspect` shows the integrity result.
    - `Left out (<n>): links, special files, files or folders that could not be read, or files removed during the backup`, followed by the entries, at most 50: they are not in the archive. Links are never followed, even when a whole folder such as `custom-uploads/` is a link to another disk.
    - `The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore`: a [secure archive](#backup-secure) without the key.

    **Not where you asked**: the archive is written, and the command exits with `1`.

    - `⚠️ <reason>: the archive was written to <path> instead`, followed by the usual lines: `-o` could not take the finished archive, so it is in `backups/`. Move it where you want it.
    - `❌ <reason>: the archive stays in <path>. Move it within the hour: the next backup after that removes it.`: `backups/` could not take it either. It is still in the backup's work folder, inside `backups/.jobs/`, which the first backup started after that hour, or the first start of LibreFolio after it, removes: move the archive out before then.

    **Errors**: no archive is written, and the command exits with `1`.

    - `❌ No data directory at <path>` or `❌ No database at <path>: nothing to back up`: the command backs up the [data directory](filesystem.md) LibreFolio is configured with; check `LIBREFOLIO_DATA_DIR`.
    - `❌ <path> already exists: choose another name or folder`, `❌ <path> is not a folder: choose another path` (a file stands where the path needs a folder) or `❌ cannot write into <folder>: choose another folder, or run the command as a user who can`: `-o` cannot receive the archive. The backup has not started, and nothing was created.
    - `❌ <data dir>/backups is not a plain folder (a link, or a file): …`: make `backups/` a real folder again. `❌ The backup could not run in <data dir>/backups: <reason>`: the command could not prepare its work folder there, for example because it cannot write into the data directory.
    - `❌ Backup failed (backup_no_space): not enough free space`: the free space was short at the start, or the disk or a quota filled up during the backup, even in the middle of a file. Free some space on the disk of the data directory.
    - `❌ Backup failed (backup_failed): the cause is in the log above`: any other failure. One of them is a file that fails while it is being copied into the archive, such as a read error in the middle of the file: part of a file cannot be taken back out of a zip, so the whole backup stops. A file that fails before its copy starts is left out with the warning above instead.

### 🔐 A Secure Archive {: #backup-secure }

```bash
# The password is asked twice at the terminal
pipenv run ./dev.py backup create --encrypt

# The password read from a file that holds it alone (with Docker, a secret: /run/secrets/…)
pipenv run ./dev.py backup create --password-file ~/.librefolio-backup-password

# The password read from the standard input, such as from a password manager
pass show librefolio/backup | pipenv run ./dev.py backup create --password-stdin
```

A secure archive, `librefolio-backup-20261015-121500.lfbk`, is the zip that `backup create` writes without a password, encrypted with a password you choose: only that password opens it, and LibreFolio cannot recover a lost one. What it protects, and what it does not: [Secure Backups](backup_restore.md#secure).

- 🔑 **Where the password comes from**, never from the command line, which every user of the server can read (`ps`) and the shell keeps in its history: there is no `--password` option, and the commands that take a password accept no abbreviated option.
    - `--encrypt` alone: typed at the terminal, twice.
    - `--password-file FILE`: the text of the file, without the byte order mark at its start and the line breaks at its end, as for [Secrets in Files](configuration_secrets.md#secret-files): a file that holds the password alone, such as a Docker secret. A relative path starts at the project root.
    - `--password-stdin`: one line of the standard input, without its line break, such as from a pipe. At a terminal, the password is asked as without the option, without being shown, twice for `create`: typed there as a line, it would show.

    `--password-file` and `--password-stdin` exclude each other, and either one makes the archive secure without `--encrypt`.

- 📄 **A file the command can trust.** The file of `--password-file`, like that of `--instance-key-file` ([The Instance Key of Another Installation](#backup-restore-instance-key)), must be a regular file: a FIFO, a folder or a device is refused at once, never waited on nor read, with `❌ password file: <path> is not a regular file (password_unreadable)`. Started as root, such as with `docker compose exec`, the command also refuses a path that goes through a link inside the data directory, where LibreFolio's user could have planted one to a file only root may read: `❌ password file: <path> goes through a link inside the data directory: give the file itself, from outside it (password_unreadable)`. A link elsewhere is followed, as Kubernetes mounts its secrets; Docker and Compose secrets are plain files. For `--instance-key-file`, the same lines start with `instance key file:` and end with `(instance_key_unreadable)`.

- 📏 **The rules** are those of an account's password with at least 12 characters: an uppercase and a lowercase letter, a digit and a symbol, each class counted in Unicode as for the accounts; at most 1024 characters. They are checked before the backup starts: a password that misses one writes nothing.
- 🗝️ **The instance key.** The archive carries `secrets/instance.key` when LibreFolio generated the key and can use it; never a key set with `LIBREFOLIO_INSTANCE_KEY` or `LIBREFOLIO_INSTANCE_KEY_FILE`. A generated key that cannot be used, damaged, out of reach, or longer than 4096 bytes, more than a restore reads back, is left out, with the warning `⚠️ The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore`, and the archive is written all the same.
- 🔐 **The encryption** comes after the usual phases, as `… encrypting`. It writes the `.lfbk` beside the zip in `backups/`, so it needs the zip's size again there, plus 64 MB: when that is short, `❌ Backup failed (backup_no_space): not enough free space`. The zip is removed once encrypted, or when the backup fails. A backup killed outright, by a power cut or `kill -9`, cannot remove it: the next start of LibreFolio ends that backup as interrupted and removes what it left in `backups/.jobs/`, the zip and the copy of the database included.
- ✅ It ends as above, the reminder being `🔐 Encrypted with your password: only that password opens it, and LibreFolio cannot recover a lost one.`

??? note "❌ Password errors — what the messages mean"

    Nothing is written, and the command exits with `1`.

    - `❌ A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal (password_required)`: `--encrypt` without a terminal to ask on, such as in cron. An empty password typed at the terminal ends with `❌ No password was typed (password_required)`, an empty line from a pipe with `--password-stdin` with `❌ The standard input carried no password (password_required)`.
    - `❌ The two passwords differ (password_mismatch)`.
    - `❌ The password of a backup needs at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: <rules>)`: the codes of the rules it misses, in this order: `min_length`, `uppercase`, `lowercase`, `digit`, `special`.
    - `❌ The password is longer than 1024 characters (password_too_long)`.
    - `❌ password file: <path> does not exist (password_unreadable)`, or `cannot be read (…)`, `is empty or blank`, `is not UTF-8 text`, `is larger than 65536 bytes, too large for a secret`, `is not a regular file`, `goes through a link inside the data directory: give the file itself, from outside it` (see «A file the command can trust» above).

    Both password options at once, or an option that does not exist, such as `--password`, stop the command before it starts, with its usage line and the exit code `2`.

### 🗂️ What the Archive Holds

The archive has the layout of the data directory, and holds only:

| Entry | What it is |
| --- | --- |
| `manifest.json` | The description of the archive, see below |
| `sqlite/app.db` | The copy of the database |
| `custom-uploads/` | The files uploaded in the app |
| `broker_reports/` | The broker reports |
| `scenario_catalog/` | Your own stress scenarios, if you added any |
| `secrets/instance.key` | In a [secure archive](#backup-secure) only, when LibreFolio generated the instance key: its text, outside the manifest's list of files. A restore reads it to re-encrypt the saved secrets, and never unpacks it |

Everything else stays out: `secrets/` (but `secrets/instance.key` in a secure archive), `logs/`, `scheduler_state.json`, the `backups/` folder itself, the `.librefolio-production-data` marker, and SQLite's working files next to the database: `app.db-wal`, `app.db-shm`, `app.db.post-migration.lock` and the `.bak` copies of the [post-migration fixes](cli_tools.md#post-migration-fixes). The copy of the database already holds what was waiting in `app.db-wal`. Symbolic links and special files are never followed nor archived.

!!! warning "🔑 The instance key is in a secure archive only"

    A clear archive leaves out `secrets/`, which holds the [instance key](configuration_secrets.md#instance-key). Back it up separately, as [Filesystem Structure → What to Back Up](filesystem.md#what-to-back-up) explains, and keep the copy as private as the archives. Before you start LibreFolio on the data of a clear archive, put `secrets/` back with it: without its key, what LibreFolio encrypted can no longer be read. A [secure archive](#backup-secure) carries the key LibreFolio generated, never one set with `LIBREFOLIO_INSTANCE_KEY` or `LIBREFOLIO_INSTANCE_KEY_FILE`: keep that one where you set it. With a copy of the key, a restore on another installation can still read the saved secrets of a clear archive: [The Instance Key of Another Installation](#backup-restore-instance-key).

??? info "📋 `manifest.json` — what it records"

    - the format, `librefolio-backup`, and its version;
    - the LibreFolio version that made the archive, how (`cli` for this command, `ui` for the web interface, `panel` for a [hosting panel](hosting_panel_backups.md#panel-backups)) and when, in UTC;
    - the database: its migration (Alembic) revision, the result of SQLite's integrity check, the number of foreign-key violations, the rows in each table and the ledger's control totals, the cash of every broker in each currency and the quantity of every position (an archive made before them has none);
    - every entry, the database first, with its path, its size and its SHA-256;
    - whether the archive carries the instance key, and the SHA-256 of that entry: only a secure archive does.

### 🔍 Check an Archive

```bash
# Check every entry against the manifest, and show what the archive holds
pipenv run ./dev.py backup inspect /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip

# Faster: compare the entry names with the manifest, without reading the entries
pipenv run ./dev.py backup inspect /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --no-verify
```

- 🟢 It works on any archive, with the server running or stopped, and needs no data directory, but for a secure archive (below). As with `-o`, a relative path starts at the project root.
- 📋 It shows who made the archive and when (`Made by LibreFolio <version> (cli) on <date> UTC`), the database's migration revision, size and integrity check, its rows and tables, the number and size of the files, and whether the instance key is included.
- 🔎 It compares the size and SHA-256 of every entry with the manifest, and ends with `✅ Every entry matches the manifest`. `--no-verify` compares only the entry names, without reading the entries, and ends with `ℹ️ The entry names match the manifest; their contents were not read (--no-verify)`.
- 🔐 A secure archive, recognised by its first bytes whatever its name, asks its password first, once, from the same sources as `create` ([A Secure Archive](#backup-secure)). It is then decrypted (`🔓 Decrypting <path>`) into a private folder `.decrypt-…` of the data directory's `backups/`, removed at the end, also when the command fails: the command needs that data directory, and room in it for the decrypted archive, about the size of the `.lfbk`. A folder that an `inspect` killed outright (a power cut, `kill -9`) left behind is removed by the next `inspect`, or by the next start of LibreFolio, once it is an hour old: a younger one may be another `inspect`'s, still running. Its report adds `Secure backup: decrypted with its password`. A wrong password ends with `❌ The password does not open this backup (wrong_password)`; see also `password_required`, `envelope_damaged` and `envelope_unsupported` in the refusals of [Try a Restore on a Copy](#backup-restore-dry-run). A `.zip` ignores the password options.
- ❌ It exits with `1` when entries are missing, differ from the manifest or are not in it (it names the first five of each), and when the file is not an archive it can read: the message then ends with a code, such as `archive_unreadable` (not a zip file, or one cut short), `manifest_missing`, `manifest_unknown_format` (not a LibreFolio backup) or `manifest_newer_format` (made by a newer LibreFolio: check it with that version or a newer one).

### 🔏 A Sealed Archive {: #backup-sealed }

A sealed archive is a `.tar` whose password LibreFolio draws itself and encrypts for one or two age public keys: only the matching private key opens it, and the server that made it cannot. It is made for backups that run on their own, such as every night from cron. What it holds, how to keep the key and how to change it: [Sealed Backups](backup_sealed.md#sealed).

```bash
# A key pair: the private key into a file of its own (0600, never over a file), the public key printed
pipenv run ./dev.py backup keygen --identity-file ~/librefolio-backup-key.txt

# A sealed archive for that public key (twice --recipient while a key is being changed)
pipenv run ./dev.py backup create --recipient age1…

# The same, for the keys of LIBREFOLIO_BACKUP_RECIPIENTS
pipenv run ./dev.py backup create --sealed

# Check, restore or decrypt it where the private key is
pipenv run ./dev.py backup inspect librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt
pipenv run ./dev.py backup restore librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt --dry-run
pipenv run ./dev.py backup decrypt librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt -o backup.zip
```

- 🗝️ **`keygen`** writes the private key in the format of `age-keygen` (`# created:`, `# public key: age1…`, then `AGE-SECRET-KEY-1…`), readable by its owner only, and never over a file that exists (`❌ <path> already exists: a key file is never written over`). It then prints `🔑 Public key, for --recipient or LIBREFOLIO_BACKUP_RECIPIENTS:` and the `age1…` line. Run it on a computer of yours, not on the server: the private key belongs off the server.
- 🔏 **`create --recipient age1…`** seals for the key given, `--recipient` twice for two keys; **`create --sealed`** seals for the keys of `LIBREFOLIO_BACKUP_RECIPIENTS` ([Environment Variables](configuration.md)). The archive is `librefolio-backup-20261015-121500.tar`, with the usual rules of `-o` and of names. After the phases of a secure archive, the backup shows `… sealing`, and ends with `🔏 Sealed for 1 key: only the matching private key opens its password, and this server cannot.`
- 🔑 **No password to give.** `--sealed` and `--recipient` go without `--encrypt`, `--password-file` and `--password-stdin`, and `--sealed` without `--recipient`: the command stops before anything is written. It needs no terminal, so it runs from cron as it is; with Docker, `docker compose exec -T librefolio python dev.py backup create --sealed`.
- 🗝️ **Never the instance key**, even one LibreFolio generated: unlike a [secure archive](#backup-secure), a sealed one leaves `secrets/instance.key` out.
- 💽 **Space.** Sealing writes the `.tar` beside the `.lfbk`, so the work folder in `backups/` needs the `.lfbk`'s size again, plus 64 MB, or the backup stops with `backup_no_space`.
- 🔓 **`--identity-file`** opens a sealed archive for `inspect`, `restore` and `decrypt`. It reads a key file as `age-keygen` writes it, before any switch of user, as `--password-file` does: a Docker secret works. The command checks the `.tar` and its manifest, opens the password with the key, checks it against `backup.lfbk`, prints `🔏 Sealed backup <path>: its password opened with <key file>`, then copies `backup.lfbk` into a private folder of the system's temporary folder, removed at the end, and goes on as for a secure archive with its password.
- ❌ A `.tar` without `--identity-file` stops with `sealed_backup_needs_key`; `--identity-file` with any other archive stops with `❌ --identity-file opens a sealed backup (.tar) only: <path> is not one`.
- 🧾 **The refusals**, each at the end of its message: `sealed_identity_invalid` (the key file holds no age key, or cannot be read), `sealed_no_identity` (no key of the file opens the password), `sealed_tar_invalid` (not the three files of a sealed archive, in order, as plain ustar files), `sealed_manifest_invalid` (its `manifest.json` does not describe it), `sealed_password_invalid` (what the key opened is not a password LibreFolio writes), then those of a secure archive: `wrong_password` (that password does not open `backup.lfbk`) and `envelope_damaged`. Every message, with what to do: [Making or Opening a Sealed Backup](backup_moving.md#sealed-problems).

### 🧪 Try a Restore on a Copy {: #backup-restore-dry-run }

```bash
# Check an archive for a restore, on a copy: the instance stays as it is
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --dry-run
```

`backup restore --dry-run` unpacks the archive into a copy, brings it up to date and checks it, then tells you what a restore would do. The copy is made in the data directory, in `.restore/stage/<id>/`, and removed at the end: the database and the files of the instance are never touched, so the server can keep running. Without `--dry-run`, the same check is the first half of a restore: see [Restore an Archive](#backup-restore).

A [secure archive](#backup-secure) asks its password first, as `inspect` does, and is decrypted into the folder of the copy, as `.restore/stage/<id>/archive.zip`, which is removed once unpacked. A check killed outright leaves that decrypted archive, or its part `archive.zip.part`: the next start of LibreFolio removes it. Then the check goes through six steps, and stops at the first one that refuses the archive:

1. **A LibreFolio archive.** Only an archive LibreFolio wrote, with its `manifest.json`, is accepted: a data directory zipped by hand is not. Every entry is checked before a byte is written: the manifest lists it (or announces it, for the instance key of a secure archive), it is a plain file (not a folder, a link or an encrypted entry), its name appears only once, even ignoring upper and lower case, its size is the one in the manifest, and the whole fits in the free space.
2. **Unpacked.** Each entry is written into a new file of the copy, never through a link nor over another file, and its SHA-256 is compared with the manifest's. Then, before anything else opens the copy, the schema of its database is read, and nothing of it runs: a trigger, a view or a virtual table, which LibreFolio never creates and whose SQL would run during the check and in the server after a restore, refuses the archive (`database_foreign_objects`).
3. **The revision decides.** The migration (Alembic) revision of the database, given by the manifest and confirmed by the database itself:
    - this LibreFolio's own revision: the database is restored as it is;
    - an older one: the copy is upgraded to this LibreFolio's revision, in a process of its own, which is stopped if it lasts more than an hour;
    - one this LibreFolio does not know, most likely from a newer version: refused with `revision_unknown`. Update LibreFolio first: a database is never downgraded.

    Then the [post-migration fixes](cli_tools.md#post-migration-fixes) run on the copy, as at every start.

4. **Checked before and after.** Before the upgrade, the copy passes SQLite's integrity check, holds exactly the rows the manifest counted, and holds no text that is not UTF-8: LibreFolio never writes such text, and the server could not read its rows after a restore. After it, the copy passes the integrity check again, at this LibreFolio's revision. A migration may change data, so rows that changed are a warning, not a refusal, and so are broken references (foreign keys), kept as they are.
5. **Administrators.** The report names the active administrators of the backup. Without any, the restore is blocked: nobody could manage the instance after it.
6. **Saved secrets.** The instance keeps its own [instance key](configuration_secrets.md#instance-key). When the archive carries the key that encrypted its saved plugin secrets, such as the API key of a data source, or when you give that key with `--instance-key-file` ([The Instance Key of Another Installation](#backup-restore-instance-key)), they are re-encrypted on the copy with this instance's key; the others are counted, to enter again after the restore. A copy without secrets does not even read this instance's key.

It shows the steps as it goes (`… decrypting` for a secure archive, `… checking`, `… unpacking`, `… upgrading`, `… verifying`), then its report:

- 📦 Who made the archive and when (`Made by LibreFolio <version> (<how>) on <date> UTC`), and what a restore does with the database: `this LibreFolio's own: restored as it is`, or `upgraded on the copy to <revision> (<n> migrations)`, followed by each migration with the first line of its description.
- 🩹 The post-migration fixes that changed something on the copy, if any.
- 🔢 The rows, the tables and the size of the database, then the tables whose rows the upgrade changed, as `<table> (<before> → <after>)`, with `—` for a table that did not exist.
- 📁 The number and size of the files; `Secure backup: decrypted with its password` for a secure archive; `Instance key: included` or `Instance key: not included`, or `Instance key: not included; given with --instance-key-file` with that option; and the saved keys of the data providers: `Saved provider keys: <n> re-encrypted with this instance's key`, and `⚠️ <n> saved provider keys cannot be read with this instance's key: enter them again after the restore` for those the archive's key, or the key given, did not read, or when there is no key.
- ⚖️ The ledger's control totals: the cash of every broker in each currency and the quantity of every position, summed from the transactions alone, with no price, exchange rate, cost or date. The backup recorded them in its manifest, and the check reads them again on the copy once it is up to date. A difference is a warning, never a refusal: a migration may correct data. The report says one of:
    - `Ledger totals: the same as when the backup was made`;
    - `⚠️ Ledger totals differ from the backup's (<n> lines):`, then the lines that differ, cash first, at most 20: `broker <id>, <currency> cash: <before> → <after>` or `broker <id>, asset <id> quantity: <before> → <after>`, the backup's amount before the arrow and the copy's after it, with `—` for zero. `… and <n> more` counts the lines left out;
    - `Ledger totals: not recorded in this archive`: an archive made by an earlier LibreFolio, from before the totals, records none, nor does one whose totals could not be read when it was made;
    - `Ledger totals: recorded by another version of the method, not compared`;
    - `⚠️ Ledger totals: could not be read on the copy`.
- 👑 The administrators, and what a restore will mean for everyone: `After a restore you sign in with one of them, with the password of then; every session open now ends.` and `Invitations and links sent before the restore will have expired: send them again if needed.`
- ⚠️ The warnings, which let a restore go on: `The upgrade changed the rows of some tables (listed above)`, `The backup's database has broken references: they are kept as they are`, `The upgrade added broken references to the copy`, `The ledger's totals differ from those the backup recorded (listed above)`, `The ledger's totals could not be read on the copy` or `Some currency codes in the backup are not ISO 4217 codes, names or numbers an earlier version saved: an edit of their rows is refused until they are corrected (./dev.py db currencies lists them after the restore)`, which [Currency Codes That Are Not ISO Codes](cli_tools.md) explains.
- 👥 A backup with more active accounts than `LIBREFOLIO_MAX_USERS` allows adds one line, printed once, which names no account and no address: `⚠️  The backup holds <n> active accounts; this instance accepts <m> (LIBREFOLIO_MAX_USERS): at the first sign-in the administrator chooses who keeps access, the others are deactivated (not deleted)`. It only informs: `backup restore --yes` confirms and `--dry-run` exits with `0`, as for any backup. What happens next is in [More Accounts Than the Plan Allows](backup_restore.md#users-limit).
- ⛔ The blocker, which forbids it: `❌ The backup has no active administrator: after a restore nobody could manage the instance`.

It ends with `✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed.` and exits with `0`. It exits with `1` when the archive is refused or the restore blocked. A refusal is one line, the reason followed by a code in parentheses, such as `❌ The file is not a LibreFolio backup (not_a_backup)`, and nothing of the copy is left.

- 💽 The copy needs free space on the disk of the data directory: everything the archive holds once unpacked, plus twice the size of its database for the upgrade, plus 64 MB. `backup inspect` shows those sizes; the archive itself is read where it is, never copied. A secure archive also needs room for its decrypted archive, about its own size, until it is unpacked. When the space is short, the check stops before it unpacks anything, with the number of bytes it needs (`no_space`); a disk that fills up during the check stops it too.
- 📦 What the archive unpacks to has a limit when `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` sets one, and in the `managed` profile of a hosting provider, where it is 8 times the upload limit while it is not set («Main Options» in [Environment Variables](configuration.md)). The sizes the manifest declares are added up before the free space is checked, and an archive over the limit is refused with `unpacked_too_large`, before anything is unpacked. `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` in front of the command lifts it for that command: `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0 pipenv run ./dev.py backup restore <archive>`, or `docker compose exec -e LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0 librefolio python dev.py backup restore <archive>` with Docker. A limit that cannot be read stops the command before `🔎 Checking … on a copy`, with exit code `1`: `❌ LIBREFOLIO_BACKUP_MAX_RESTORE_MB: expected a whole number of megabytes, 0 for no limit (backup_restore_unavailable)`, or, in the `managed` profile while it is not set, the same line about `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`, which the limit follows.
- 🚦 One archive is checked at a time: while another check runs, the command stops with `❌ Another archive is being checked (from the web interface or another command): try again when it ends`.
- 🆕 It never uses the database of the instance: any installation can check an archive, a new one included, as long as its data directory exists (otherwise `❌ No data directory at <path>`). As with `-o`, a relative path starts at the project root.
- 🔗 Keep `.restore/` and `.restore/stage/` real folders: a link, or a file, in their place stops the command with `❌ <path> is not a plain folder (a link, or a file): the copy is made in a folder of the data directory`.

??? note "❌ Refusals — what the codes mean"

    | Code | Why the archive is refused |
    | --- | --- |
    | `not_a_backup` | Not a zip, or a zip without the manifest LibreFolio writes, such as a data directory zipped by hand |
    | `password_required` | A secure archive, and no password: no terminal to ask on, and neither `--password-file` nor `--password-stdin` |
    | `wrong_password` | The password does not open the secure archive: not the one it was made with, or the start of the file was changed |
    | `envelope_damaged` | The secure archive is damaged, cut short, or was changed after it was made |
    | `envelope_unsupported` | The secure archive comes from a newer LibreFolio, or asks for settings this one does not accept: update LibreFolio first |
    | `instance_key_unreadable`, `instance_key_invalid` | The file given with `--instance-key-file` cannot give the key, or the key is shorter than 32 characters: see [The Instance Key of Another Installation](#backup-restore-instance-key) |
    | `archive_unreadable`, `archive_damaged` | The file cannot be read, or the zip is damaged |
    | `manifest_newer_format` | The archive format is newer than this LibreFolio reads: update LibreFolio first |
    | `manifest_invalid`, `manifest_unreadable`, `manifest_too_large` | The manifest is damaged or not valid |
    | `unexpected_entry`, `missing_entry` | The archive holds an entry its manifest does not list, or lacks entries the manifest lists; for the instance key, an entry the manifest does not announce, or one it announces and the archive lacks |
    | `duplicate_entry` | An entry appears twice, even when only the case of its name changes, or stands where the folder of another entry must be |
    | `not_a_file`, `encrypted_entry`, `unsupported_entry` | An entry is a folder or a link, is encrypted, or uses a compression LibreFolio does not write |
    | `too_many_entries` | The archive holds more than 500,000 entries |
    | `checksum_mismatch` | An entry's size or SHA-256 differs from the manifest: the archive is damaged or was changed |
    | `unpacked_too_large` | Unpacked, the archive would be larger than this installation accepts for a restore, from the sizes its manifest declares: `LIBREFOLIO_BACKUP_MAX_RESTORE_MB`, or, while it is not set in the `managed` profile, 8 times the upload limit. Nothing is unpacked |
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

```bash
# Check the archive on a copy, then restore it at the next start of the server
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip
```

Without `--dry-run`, `backup restore` runs the same check on a copy and shows the same report ([Try a Restore on a Copy](#backup-restore-dry-run)). When the archive can be restored, it asks you to confirm:

```text
   Type "restore" to restore this archive at the next start of the server:
```

- ⌨️ Type `restore`, in lower case; spaces around it do not count. Anything else, `Restore` or an empty line included, ends with `Nothing restored: the copy was removed.` and exit code `1`.
- 🤖 `--yes` (`-y`) confirms without asking. Without a terminal to ask on, in a script for instance, it is required: otherwise the command stops with `❌ No terminal to ask on: add --yes to confirm the restore. Nothing restored: the copy was removed.` and exits with `1`. A [secure archive](#backup-secure) needs its password there too: add `--password-file` or `--password-stdin`.

Once confirmed, the command exits with `0` and says:

```text
✅ The restore waits for the next start of the server: restart LibreFolio to apply it.
   That start replaces the database and the files, and ends every session: sign in with an administrator of the backup.
   ./dev.py backup pending shows it; ./dev.py backup pending --cancel drops it.
```

On an instance a hosting provider runs (the `managed` profile) with `LIBREFOLIO_ADMIN_EMAIL` set, the report of the check and the confirmation add one line about the owner's account: see [The Owner's Account on a Restore from the Command Line](#backup-restore-owner).

Nothing has changed yet: the server keeps running on its data, and the checked copy waits in `.restore/stage/<id>/`, however long it takes. Restart LibreFolio when it suits you: stop the whole server, then [start it](cli_tools.md#start-the-server) again; with Docker, `docker compose restart librefolio` ([Back Up with Docker](#backup-docker)). If the server is stopped, its next start applies the restore.

That start applies it before it reads any data:

1. 🛑 **Only a start of the whole server.** Every LibreFolio server process holds a lock on the data directory from early in its start, before it reads any data, until it exits. A start that finds it held by another process, such as a worker that uvicorn starts again beside its running siblings with `--workers` or a second server on the same data directory, leaves the restore waiting (`server_running`). Restart the whole server, never one worker. A start that finds the restore applied by another server that still runs, or by another start, stops instead of serving data whose restore is not committed.
2. 🔀 **The swap.** The instance's `sqlite/`, `custom-uploads/`, `broker_reports/` and `scenario_catalog/` swap places with those of the copy. Each move is a rename inside the data directory: instant, whatever the size. The instance's own folders are set aside in `.restore/previous/`.
3. 🔒 **What stays.** `secrets/`, `logs/`, `scheduler_state.json` and `backups/` are not touched: the instance keeps its [instance key](configuration_secrets.md#instance-key), its logs and its archives.
4. ✅ **The first start must complete.** The start goes on, on the restored data, which the check already brought to this LibreFolio's revision. Once it gets through, before it answers anyone, it ends every session, revokes the one-time links of the backup, and removes the instance's former data and the copy: the restore is done.
5. ↩️ **Otherwise, back as before.** If that first start fails, on a migration that fails or a damaged file, the next start puts the data as it was before back by itself, and records the restore as rolled back, with the reason ([Follow or Cancel a Restore](#backup-pending)). With Docker, the container starts again by itself after a failed start, so the data comes back without you; with nothing that starts the server again, start it yourself.

After the restore:

- 🔑 Everyone signs in again, on every device, with an account of the backup and the password it had then. The report of the check names the administrators of the backup.
- 🔗 No link sent before the restore works any more (invitations, password resets, email verifications), not even those the backup still held: send new ones.
- 📧 An account the backup held still waiting for its email verification loses its link too, and stops waiting: the sign-in page can no longer send it another link, and answers that the account is disabled. An administrator activates it in [Users & Invitations](users.md#actions), and its address stays unverified; or deletes it ([Delete an Account](users.md#delete)), so that its owner signs up again and receives a new link. Such an account never signed in, so it holds no data.
- 🆘 If nobody remembers an administrator's password of then, whoever runs the server creates a reset link with [`user reset-link`](cli_tools.md), or sets a new password with `user reset`. Once signed in, an administrator sends reset links to the others from [Users & Invitations](users.md#reset-links).

Good to know:

- 🔒 On an instance its hosting provider blocked (`LIBREFOLIO_BLOCKED`), the command confirms all the same, and adds `⚠️ The hosting provider blocked this instance: the restore waits until it is unblocked (instance_blocked)`: the first start after the unblock applies it.
- 🚦 One restore at a time: while one waits or is being applied, `backup restore` stops before the check with `❌ A restore already waits for the next start: ./dev.py backup pending --cancel drops it (restore_already_pending)` and exits with `1`. It stops there too when it cannot read the state of the restore, since it cannot tell whether one waits: `❌ The state of the restore cannot be read: <reason> (restore_state_unreadable)`, exit code `1`, nothing checked. `--dry-run` still works.
- ❌ If the confirmation itself is refused, the command prints one line that ends with a code, removes the copy and exits with `1`: `restore_stage_outdated` when LibreFolio was updated between the check and the confirmation (or, on a hosted instance, when the owner's address changed since the check), `restore_stage_expired` when the question waited more than 24 hours, `restore_already_pending` when another restore was confirmed meanwhile, `owner_conflict` for a backup that cannot give the owner their account (below). Run the command again; after `owner_conflict` or `restore_stage_outdated`, check the archive again.
- 📍 Run it where the server runs, in the container with Docker: the restore is recorded for the path of the data directory, and a server that finds its data directory under another path does not apply it.
- 🔗 Keep the four folders real folders of the data directory: one that is a link, or that is mounted on its own, cannot be swapped. The start then leaves the data as it is, and records the restore as rolled back with `swap_failed`.
- 💽 The swap needs no space of its own: the copy the check made becomes the instance's data, and the former data is removed once the first start completes.
- 🗝️ The restore keeps this installation's instance key. When the archive carries the key of the installation that made it (a [secure archive](#backup-secure), when LibreFolio generated that key), the check has already re-encrypted its saved secrets with this installation's key. From any other archive of another installation, give that installation's key with `--instance-key-file`, and the check re-encrypts them too ([The Instance Key of Another Installation](#backup-restore-instance-key)). Otherwise they cannot be read here: the report counts them, to enter again after the restore, unless you put that installation's key back first ([Saved Secrets and the Instance Key](configuration_secrets.md#plugin-secrets)). See «The instance key is in a secure archive only» above.

### 👑 The Owner's Account on a Restore from the Command Line {: #backup-restore-owner }

Only on a `managed` instance with `LIBREFOLIO_ADMIN_EMAIL` set. On your own installation (`selfhosted`, the default), or on a hosted instance without that variable, nothing changes: no owner is picked, nothing is refused, and every password stays as it is. A restore confirmed here has nobody to ask which account of the backup becomes the owner's, so the confirmation picks it from the checked copy, in this order:

1. The account that already holds the owner's address, whatever its role.
2. Otherwise the **one** active administrator the backup marks as its owner. The mark is written by whoever prepared the backup: it only suggests which account, and grants nothing.
3. Otherwise nobody: none marked, two or more marked, or a marked account that is not an active administrator. Never "the first one".

- 👤 **An account picked.** The report says `👤 The owner's account will be <username>: …`, by its username, never by an address. At the restore its password is closed (unusable, sessions ended), it gets the owner's address, becomes an active administrator and the instance's owner. The first start sends the link to choose a new password to `LIBREFOLIO_ADMIN_EMAIL`, never to an address of the backup; without email, the link is written in the log of the instance, to be given only to the owner. If it expires, the owner uses **Forgot Password?**. [Follow or Cancel a Restore](#backup-pending) shows how it went.
- 🚫 **Nobody picked.** The restore goes on without an owner, with a warning in the log. The report says `⚠️ No owner: no account of the backup can be taken for it. The restore goes on; name one afterwards with ./dev.py user reassign-owner <username>`, and `backup pending` says it again. [`user reassign-owner`](hosting_instances.md#owner-reassign) names the owner afterwards.
- 🛑 **Owner conflicts.** A backup with two accounts on one address or one name, the owner's address as another account's name, or an administrator still waiting for its setup link is refused, as from the app: the check prints `❌ The backup cannot give the owner their account: …` and the confirmation ends with `owner_conflict`. Remove the duplicate account or free the address in the instance the backup comes from, make a new backup, and check it again.
- ❌ **If the assignment fails after the swap**, for instance because the address is taken, the instance serves nothing but the recovery until `./dev.py backup pending --recover owner` ([Follow or Cancel a Restore](#backup-pending)).
- 🧹 The mark that says which account is the instance's owner, which a backup carries from the instance it was made on, is cleared on every account at every restore, on any profile, and set only on the account that is assigned.

The hosting panel restores in the same way and has the same refusals: the panel receives HTTP 409 with the code ([The Owner's Account on a Hosted Instance](backup_restore.md#owner-account)).

### 🗝️ The Instance Key of Another Installation {: #backup-restore-instance-key }

```bash
# A clear archive of another installation, with the instance key of that installation
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --instance-key-file ~/old-instance.key
```

A clear archive leaves the instance key out, and so does a secure one whose key came from the environment: the saved plugin secrets it holds, such as the API key of a data source, open only with the key of the installation that made it. `--instance-key-file FILE` gives that key to `backup restore`, with or without `--dry-run`: the check re-encrypts those secrets on the copy with this instance's key, which stays as it is.

- 📄 The file holds the old installation's instance key: a copy of its `secrets/instance.key`, the file of its `LIBREFOLIO_INSTANCE_KEY_FILE` as it is, or the value of its `LIBREFOLIO_INSTANCE_KEY` written into a file as it was written in the variable, spaces included. Only a byte order mark at its start and the line breaks at its end are dropped, as for `--password-file`: a key that worked as the variable works the same in the file.
- 🔑 The command reads it first, as the user who started it, before it switches to the owner of the data directory, as it reads `--password-file`: with `docker compose exec`, a Docker secret only root can read works. The file follows the same rule as `--password-file`, «A file the command can trust» in [A Secure Archive](#backup-secure): keep it outside the data directory.
- 🙈 The key is never printed. Only the command line takes it: the web interface never takes a key, and a restore from Settings › Administration › Backup counts those secrets as unreadable.
- 📁 The report says `Instance key: not included; given with --instance-key-file`, then `Saved provider keys: <n> re-encrypted with this instance's key`.
- ℹ️ An archive that carries its own key is restored with it, whatever the file holds: the report adds `ℹ️ The archive carries its own instance key: --instance-key-file is not used`.
- ⚠️ A key that reads none of the saved secrets is not the key of the installation that made the backup: the report adds `⚠️ The key given with --instance-key-file reads none of the saved provider keys: it is not the key of the instance this backup came from`, before the line that counts them, to enter again after the restore. When this instance's own key cannot be used, or when it has no key yet and the check cannot create one, such as when `secrets/` cannot be written, nothing is re-encrypted, whatever the key given, and the line is `⚠️ This instance's own key cannot be used, so nothing was re-encrypted with the key given: <problem>` instead: the problem of the start log's `The instance key cannot be used: …` («Startup Checks» in [Environment Variables](configuration.md)), or, without a key, `<path>: there is no instance key yet, and it could not be created`. Secrets already under this instance's key, as in an archive of this same instance, are left as they are, whatever the key given.
- ❌ It exits with `1`, before anything is checked, when the file cannot give the key: `❌ instance key file: <path> does not exist (instance_key_unreadable)`, or `cannot be read (…)`, `is empty or blank`, `is not UTF-8 text`, `is larger than 65536 bytes, too large for a secret`, `is not a regular file`, `goes through a link inside the data directory: give the file itself, from outside it`. A key shorter than 32 characters stops it before the copy is made: `❌ The instance key given is too short: an instance key has at least 32 characters (instance_key_invalid)`.

### ⏳ Follow or Cancel a Restore {: #backup-pending }

```bash
# The restore waiting for the next start, or the last one
pipenv run ./dev.py backup pending

# Drop the restore waiting, and its checked copy (the same as --recover cancel)
pipenv run ./dev.py backup pending --cancel

# When the state of the restore cannot be read: put the data of before back (LibreFolio stopped)
pipenv run ./dev.py backup pending --recover previous

# When the owner's account could not be set after a restore on a managed instance: clear the error and try again
pipenv run ./dev.py backup pending --recover owner

# For a script: the state as one JSON line, and the same actions with fixed exit codes
pipenv run ./dev.py backup pending --json
pipenv run ./dev.py backup pending --recover cancel --json
```

`backup pending` changes nothing and exits with `0`, except when it cannot read the state of the restore: see [An Unreadable Restore State](#backup-pending-unreadable) below. `--json` and `--recover` are made for scripts: see [For Scripts](#backup-pending-json). Otherwise it shows one of these:

| It prints | What it means |
| --- | --- |
| `ℹ️ No restore waits for the next start` | No restore was confirmed, or the last one was dropped |
| `⏳ A restore waits for the next start of the server`, then `backup made by LibreFolio <version> on <date> UTC; confirmed by <who> on <date> UTC` | Confirmed, not applied yet. `<who>` is `cli` for this command, otherwise the username of the administrator who confirmed it |
| `⏳ A restore is being applied by the server` | A start applied it and has not completed yet. If that start died, the next one puts the data back |
| `✅ The last restore was applied on <date> UTC: backup made by LibreFolio <version> on <date> UTC` | The restore is done |
| `⚠️ The last restore was rolled back on <date> UTC, the data is as it was before: <reason> (<code>)` | The restore was undone, for the reason below |

After `✅ The last restore was applied …`, a restore that gave the owner an account on a `managed` instance adds one line about it, whichever route confirmed it (the app, this command or the hosting panel): `✉️ The owner's account is set: …`, `⏳ The owner's account is set at the next start of the server`, or the other lines of [the owner's account](backup_restore.md#owner-account). A restore that found nobody for the owner adds `⚠️ No owner was assigned at the restore: no account of the backup could be taken for it. Name one with ./dev.py user reassign-owner <username>`: [the order in which the account is picked](#backup-restore-owner).

When a start found a restore waiting and did not apply it, one more line says why, and the restore keeps waiting:

- `⚠️ At the last start a backup was running: the next start applies it (backup_running)`: a backup was running when the server started, a `backup create` from the command line for instance.
- `⚠️ It was confirmed for another data directory (<path>): this one does not apply it (other_data_directory)`: the server found its data directory under another path than the one where the restore was confirmed, such as a copy of the data directory. Drop it with `--cancel`, then run `backup restore` where the server runs.
- `⚠️ At the last start another server process was serving the data directory: restart the whole server to apply it (server_running)`: a worker was started again while the others kept serving (`--workers`), or another server uses the same data directory. Restart the whole server.
- `⚠️ The hosting provider blocked this instance: the restore waits until it is unblocked (instance_blocked)`: the last start found the instance blocked (`LIBREFOLIO_BLOCKED`), or it is blocked now, and a restore is never applied on a blocked instance. The first start after the unblock applies it, and migrates it first if LibreFolio was updated meanwhile. Until then its checked copy keeps its disk space: `--cancel` drops the restore and frees it.

| Code | `<reason>` | What to do |
| --- | --- | --- |
| `first_start_failed` | `the first start after it did not complete` | The log of that start has the cause |
| `swap_interrupted` | `the start that applied it was interrupted` | Nothing: a start stopped during the swap, and the next one undid it |
| `swap_failed` | `its folders could not be moved into place` | Make the four folders real folders of the data directory, neither links nor separate mounts |
| `stage_missing` | `its checked copy was gone` | The copy in `.restore/stage/` was removed or changed: check the archive again |

A rollback also removes the restored data and the copy: to try again, run `backup restore` again. If even putting the data back fails, on a disk or permission error for instance, LibreFolio does not start: its log has `The data directory is half restored: the restore could not be undone, and LibreFolio does not start on it`, and every start tries again.

#### 🧩 An Unreadable Restore State {: #backup-pending-unreadable }

The state of the restore, `.restore/restore.json`, can become unreadable: its owner or permissions changed, a disk error, a link or a folder in its place, or content no LibreFolio wrote. A restore may then have stopped half way, and LibreFolio cannot tell which data it holds. `backup pending` says so and exits with `1`:

```text
❌ The state of the restore cannot be read: <why>: a restore may have stopped half way. LibreFolio serves no data until you choose (restore_state_unreadable: <reason>)
   The data of before is kept in .restore/previous/: sqlite, user_files
   Checked copies kept: 1 (none is removed while the state cannot be read)
👉 Stop LibreFolio, then run ./dev.py backup pending --recover previous: it puts the data of before back.
```

`<reason>` is `io` (the file system refuses it: give `.restore/` and its files back to the user that runs LibreFolio, then run `backup pending` again, which may be enough), `not_a_file` or `invalid`. While the state cannot be read, no checked copy is removed, by the server's clean-up or by Settings › Administration › Backup, and no restore can be confirmed.

`backup pending --recover previous`, with LibreFolio stopped, puts the data of before back from what the folders say: each folder kept in `.restore/previous/` returns to its place, and the one it replaces goes to `.restore/failed/`. A restore that was committed kept no data of before, so its data stays. The unreadable state is kept as `.restore/restore.json.unreadable-<date>` for a look, and never read again. Then start LibreFolio on the data of before, or restore a backup again with `backup restore`. While LibreFolio runs, it stops with `(restore_in_use)` and exits with `5`; with a state it can read, or none, it stops with `(restore_nothing_to_recover)` and exits with `3`: the exit codes are the table of [For Scripts](#backup-pending-json). Run twice, the second run changes nothing.

`--cancel`, the same as `--recover cancel` but with the exit codes below, drops the restore waiting, with its checked copy, whoever confirmed it: `✅ The restore waiting for the next start was dropped, with its copy: the data stays as it is`, exit code `0`. If the copy cannot be removed, on a permission or disk error for instance, the restore is dropped all the same, exit code `0`, with two lines instead: `✅ The restore waiting for the next start was dropped: the data stays as it is` and `⚠️ Its checked copy could not be removed: it goes when its check expires`. When the removal failed with an error, the log above them has the warning `The copy of a cancelled restore could not be removed: it goes when its check expires`; a copy left without an error, such as one holding a read-only folder, has none. LibreFolio tries again at its first start once the check is 24 hours old. If the restore itself cannot be dropped, on a file-system error before it is (its lock, or removing its state): `❌ The restore could not be cancelled: <reason>. It still waits for the next start (restore_cancel_failed)`, exit code `1`. When the state of the restore cannot be read: the `restore_state_unreadable` line of `backup pending`, exit code `1`. When no restore waits, or one is already being applied: `❌ No restore waits for the next start: nothing to cancel (restore_not_pending)`, exit code `1`.

#### 🤖 For Scripts: --json and --recover {: #backup-pending-json }

A script, or a machine that reaches the server over `ssh`, reads the state with `--json` and acts with `--recover CHOICE`. Both are made to be run without a person: nothing is ever asked on the terminal, and the exit codes are fixed.

**The JSON line.** With `--json`, `backup pending` writes exactly one line on stdout: a JSON object, then a newline, no colour. Everything it would say otherwise, and the log lines of LibreFolio, go to stderr. It exits with `0` whenever the line was printed: an unreadable state is a state, not a failure.

| Key | Value |
| --- | --- |
| `state` | `none`, `pending`, `in_progress`, `committed`, `rolled_back` or `unreadable` |
| `reason` | Why: the rollback reason of a `rolled_back` state (`first_start_failed`, `swap_interrupted`, `swap_failed`, `stage_missing`), or `io`, `not_a_file`, `invalid` for an `unreadable` one, or `owner_assignment` for a `committed` one whose owner's account could not be set; `null` otherwise |
| `waiting` | Why a start did not apply a restore that waits: `backup_running`, `other_data_directory`, `server_running`, `instance_blocked`, or `null` |
| `backup_created_at` | When the backup of the restore was made, as `2026-10-23T03:00:12Z` (UTC); `null` with no state, or an unreadable one |
| `safety_copy` | `{"present": true, "at": "<date>Z"}` when the data of before a swap is kept in `.restore/previous/`, otherwise `{"present": false, "at": null}` |
| `choices` | The words `--recover` accepts now, in the table below |

After a `--recover`, the line describes the state **after** it and adds `recover`, `{"choice": "<word>", "done": true}` or `false`, and, when the exit code is not `0`, `error`, the word of the exit-code table.

| `state` | It means | `choices` |
| --- | --- | --- |
| `none` | No restore was confirmed, or the last one was dropped | none |
| `pending` | A restore waits for the next start | `cancel` |
| `in_progress` | A start is applying it, or has applied it and has not completed yet | none |
| `committed` | The last restore is done. With `reason` `owner_assignment`, the owner's account could not be set (a restore on a managed instance, from the app, the command line or the hosting panel): the restore guard keeps the instance closed, and the server log has the code | `owner` with that `reason`, otherwise none |
| `rolled_back` | The last restore was undone, with its `reason` | none |
| `unreadable` | The state of the restore cannot be read: [An Unreadable Restore State](#backup-pending-unreadable) | `previous` |

```json
{"state":"unreadable","reason":"invalid","waiting":null,"backup_created_at":null,"safety_copy":{"present":true,"at":"2026-10-23T03:00:12Z"},"choices":["previous"]}
{"state":"pending","reason":null,"waiting":"instance_blocked","backup_created_at":"2026-10-22T21:30:05Z","safety_copy":{"present":false,"at":null},"choices":["cancel"]}
```

The line never holds a username, an email, a path or an identifier: who confirmed the restore, the data directory and the checked copy are not in it. `safety_copy.at` is the moment the restore was applied, or, with an unreadable state, when `.restore/previous/` last changed.

**The exit codes.** `--recover previous` puts the data of before back when the state cannot be read, with LibreFolio stopped; `--recover cancel` drops the restore waiting, with its checked copy; `--recover owner` tries again an owner's account that could not be set. The exit codes are the same with or without `--json`:

| Exit | When | `error` in the line |
| --- | --- | --- |
| `0` | Done: the data of before is back, the restore waiting was dropped, or the owner's account was set, or cleared and left pending (the line says which) | none |
| `2` | A usage error: `--recover` without a choice, `--recover` with `--cancel`, or `--json` with `--cancel` (use `--recover cancel`) | none: the line is not written |
| `3` | Nothing to recover: no restore state, or the choice was already done. For `--recover owner`: there is no failed assignment left to try again, because another reset won the race, or no restore | `nothing_to_recover` |
| `4` | The choice is not valid in this state, such as `previous` while the state can be read, `cancel` while it cannot, `owner` when the state offers no `owner` (a second run, after it worked, too), or a word that is not a choice: nothing changes | `choice_not_valid` |
| `5` | It failed: LibreFolio is running on this data directory (`restore_in_use`), a folder could not be moved back (`restore_apply_failed`), the restore could not be dropped (`failed`): nothing is claimed done. For `--recover owner`, `restore_in_use` also means another process is setting the owner's account right now: run it again in a moment; `owner_assignment_failed` means the account was refused again. With a data directory that is missing, `5` too, but no line is written: stdout stays empty and stderr says why | `restore_in_use`, `restore_apply_failed`, `owner_assignment_failed` or `failed` |

**`--recover owner`.** When a restore of a managed instance, confirmed from the app, the command line or the hosting panel, could not set the owner's account, the restore guard keeps the instance closed and the server log has the code. `backup pending` prints the error with its way out: `❌ The owner's account could not be set (<code>): the server log has the cause; ./dev.py backup pending --recover owner tries again`. `--recover owner` clears that error and tries again at once when LibreFolio is stopped; when LibreFolio runs, it only clears the error, and the account is set at its next start. Then:

- ✅ Exit `0`, and one line says which case: the account is set, or the error is cleared and the account is set at the next start. When no email could be sent (`link_only`), the line says so and that the link to choose the account's password is in the log of the instance: give it only to the owner. The line never carries the link. With `--json`, that line goes to stderr, and the JSON line never holds a link, a name, an address or an identifier.
- 🔁 Exit `5` with `owner_assignment_failed` when the account was refused again: the line has the code. Fix the cause, for instance an address already taken, then run it again.

Run again, a choice changes nothing: the second `--recover previous` finds no unreadable state, moves no folder, adds nothing to `.restore/failed/`, and exits with `3`; so does a second `--recover cancel`. A second `--recover owner` finds no failed assignment and exits with `4`. A script may therefore repeat `previous` or `cancel` until it reads `0` or `3`, and `owner` until it reads `0` or `4`.

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

```bash
# The zip inside a secure archive, to use it by hand
pipenv run ./dev.py backup decrypt /mnt/nas/librefolio/librefolio-backup-20261015-121500.lfbk -o /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip
```

`backup decrypt` writes the zip that a [secure archive](#backup-secure) holds: the archive `backup create` writes without a password, with `secrets/instance.key` when the secure archive carries the key. `inspect` and `restore` take that zip as any other, and its key still re-encrypts the saved secrets. To restore a secure archive, you do not need it: `backup restore` takes the `.lfbk` as it is.

- 🔑 It asks the password once, or reads it with `--password-file` or `--password-stdin` ([A Secure Archive](#backup-secure)).
- 🆕 `-o` (`--output`) is required, and is the zip's file: it must not exist yet. One that does is refused before the password is asked, `❌ <path> already exists: choose another name`, and nothing is written. As with `create`, a relative path starts at the project root.
- 🔒 The zip holds every user's data in clear, and only its owner can read it (`0600`): the user who ran the command, or the server's user when the command switched to it. It ends with `✅ Decrypted: <path> (<size>)` and `🔒 It holds every user's data in clear: keep it private, and remove it once used.` When the secure archive carries the instance key, a last line adds `🔑 It also holds the instance key: with it, every saved provider key can be read.`
- 🟢 It needs no data directory, and works with the server running or stopped. Where there is one and you run it as root, such as with `docker compose exec`, it reads a `--password-file` first, as root (a root-owned Docker secret works), then switches to the owner of the data directory, as the other commands do: the zip then belongs to the server's user, and `-o` must be a place that user can write ([Back Up with Docker](#backup-docker)). If it cannot switch, it stops before it reads the archive or asks the password, with the message of the other commands: `❌ cannot switch to the owner of <path> (<uid>:<gid>): <reason>. Run the command as that user.`
- ❌ It exits with `1` when it cannot read the file, such as a file only root can read once the command runs as the server's user (`❌ Cannot read <path>: <reason> (archive_unreadable)`, before the password is asked), when the file is not a secure archive (`❌ <path> is not a secure backup: a plain .zip needs no decrypting (not_an_envelope)`), when the password does not open it (`wrong_password`), when it is damaged (`envelope_damaged`: nothing is left at `-o`) or comes from a newer LibreFolio (`envelope_unsupported`), and when it cannot write at `-o` (`❌ Cannot write <path>: <reason>`, once the password is given: nothing is left there).

### 🚚 Use an Archive on Another Installation

[`backup restore`](#backup-restore) restores an archive on the installation where you run it, and keeps that installation's `secrets/`. To start another installation on the data of an archive by hand instead, with the `secrets/` of the installation that made it, such as when you move LibreFolio:

1. **Stop LibreFolio** on the installation that receives the data.
2. **Unzip the archive into an empty [data directory](filesystem.md)** (`LibreFolio-data/` with Docker Compose): if it holds anything, move it aside first. Nothing of the old data may mix with the archive's, not even SQLite's `app.db-wal` and `app.db-shm`. A secure archive is decrypted into its zip first ([Decrypt a Secure Archive](#backup-decrypt)).
3. **Put `secrets/` back** in the data directory, from the copy you saved separately. The zip of a secure archive that carries the key brings `secrets/instance.key` already: give the folder mode `0700` and the file `0600` (`chmod`), or the start log has a warning.
4. **Start LibreFolio**, the version that made the archive or a newer one: the pending migrations run by themselves at start.

Good to know:

- 🧪 Before step 1, check the archive on the installation that receives it, with `backup restore <archive> --dry-run` ([Try a Restore on a Copy](#backup-restore-dry-run)): without changing anything, it tells you whether that LibreFolio can take the archive, which migrations its start will apply, and which administrators you will sign in with.
- ⛔ LibreFolio never downgrades a database: an archive made by a newer version needs that version or a newer one, and an older one does not start on it. `backup inspect` shows which version made the archive, and `backup restore --dry-run` refuses such an archive with `revision_unknown`.
- 🧹 The `manifest.json` left at the root of the data directory is harmless: you can delete it.
- 👤 With Docker, the container gives the data directory to its user at every start, so the owner of the unzipped files does not matter. On a host installation, unzip as the user that runs LibreFolio, so that the files belong to it.
- 🗝️ The key of a secure archive works only where neither `LIBREFOLIO_INSTANCE_KEY` nor `LIBREFOLIO_INSTANCE_KEY_FILE` is set: a key set there wins over `secrets/instance.key`. Never put it in place of a key already in use: what was saved under that key would become unreadable. An installation with its own key takes the archive with [`backup restore`](#backup-restore), which re-encrypts the saved secrets.

### 🐳 Back Up with Docker {: #backup-docker }

```bash
# Write an archive: on the host, it appears in ./LibreFolio-data/backups/
docker compose exec librefolio python dev.py backup create

# Check it, with its path inside the container
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip

# Try a restore of it on a copy: the instance stays as it is
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip --dry-run

# Restore it: the same check, then type "restore" to confirm
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip

# Restart the container: its start applies the restore
docker compose restart librefolio

# Then see how it went
docker compose exec librefolio python dev.py backup pending
```

- 👤 `docker compose exec` runs as root: the command switches to the owner of the data directory, `backup decrypt` included, so everything it writes belongs to the server's user. If it cannot switch, it stops and asks you to run it as that user: `docker compose exec --user <uid>:<gid> librefolio python dev.py backup create`, with the numbers from the message.
- 📂 `-o` and the archives of `inspect` and `restore` are paths inside the container, where the data directory is `/app/backend/data/prod-docker`. To check an archive that is on the host, copy it into `LibreFolio-data/` first, such as into `LibreFolio-data/backups/`. To write the archive elsewhere than `LibreFolio-data/backups/`, use a folder mounted from the host that the server's user can write to: anywhere else, it stays inside the container and is lost when the container is recreated.
- 🔑 `restore` and `decrypt` also read the archive as the server's user: an archive that `backup create` wrote is fine, but one you copied in yourself must be readable by that user, or they stop with `archive_unreadable`. With the official image, `sudo chown 1000:1000 <archive>` on the host gives it to that user.
- ⌨️ `docker compose exec` gives the command a terminal to ask on. Without one, such as with `docker compose exec -T` in a script, add `--yes`.
- 🔐 For a [secure archive](#backup-secure), `--encrypt` asks the password on that terminal. With `-T`, from cron for instance, give it with `--password-file` and a Docker secret, such as `/run/secrets/backup_password`: [the example](backup_restore.md#command-line) in Backup, Restore and Moving Your Instance shows the lines to add to `docker-compose.yml`. `backup decrypt` switches to the server's user too, so its zip belongs to that user: give it an `-o` that user can write, in `LibreFolio-data/backups/` or a folder mounted from the host, such as `docker compose exec librefolio python dev.py backup decrypt /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.lfbk -o /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip`.
- 🔏 A [sealed archive](#backup-sealed) needs no terminal: `docker compose exec -T librefolio python dev.py backup create --sealed` reads `LIBREFOLIO_BACKUP_RECIPIENTS` from the container's environment, which `env_file: .env` fills; after a change of `.env`, `docker compose up -d` recreates the container with it. To open one in the container, give `--identity-file` a path inside it; better, open it on your computer, where the private key is ([Open a Sealed Backup](backup_sealed.md#sealed-open)).
- 🔁 After a first start that fails on the restored data, the container starts again by itself (`restart: unless-stopped`, in both compose files LibreFolio ships), and that start puts the data as it was before back.
- 🔒 On the host, the archives belong to the container's user, and only that user can read them: if your host user is another one, copy them with `sudo cp -a`.
- 💻 From a source checkout, `./dev.py docker exec backup create` does the same.

---

## 🔗 Related

- 📄 **[Command-Line Tools](cli_tools.md)** — Start the Server, Manage Users, Maintain the Database, …
