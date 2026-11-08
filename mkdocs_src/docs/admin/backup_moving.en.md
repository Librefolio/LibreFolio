# 🏠 Backups: Moving and Troubleshooting

This page of the backup guide covers **moving** LibreFolio from one installation to another (from a hosting to a server of your own, or the other way round) and what to do **when something goes wrong** with a backup or a restore.

The rest of the guide starts on [Backup, Restore and Moving Your Instance](backup_restore.md).

---

## 🏠 Bring Your LibreFolio Home {: #bring-home }

An archive moves your LibreFolio from one installation to another. Two ways:

| Way | When | Where |
| --- | --- | --- |
| **Restore** | The restore checks the archive on a copy before anything changes; with Docker it takes a secure backup (`.lfbk`) as it is, and it is the simplest way | Settings › Administration › Backup, or `backup restore` ([Restore on This Installation](backup_restore.md#restore)) |
| **By hand** | The data folder of the destination is empty, or does not exist yet: unzip the zip there before the first start | Terminal of the destination server, [below](#by-hand) |

In both cases the destination runs the same version of LibreFolio or a newer one ([Never Backwards](#never-backwards)).

### ✋ By Hand: Unzip Before the First Start {: #by-hand }

Know this before you start:

- 🔎 **Nothing checks the archive first.** A damaged archive, or one from a newer LibreFolio, shows when the start fails, and some damage only later, when a page reads the data it touches. A restore checks it on a copy before anything changes. To check an archive before you unzip it by hand, use an installation of LibreFolio that **already runs**: `backup inspect <archive>` compares each file with the manifest and, for a zip, writes nothing; `backup restore <archive> --dry-run` makes the whole check of a restore, on a copy («Check an Archive» and «Try a Restore on a Copy» in [CLI Admin Tools](cli_tools.md)). The dry run works in that installation's data folder: never point it at the empty folder you are about to fill.
- 📖 The steps for any installation, the host one included: «Use an Archive on Another Installation» in [CLI Admin Tools](cli_tools.md).

The steps, with Docker Compose:

1. **Source server — Settings › Administration › Backup, or terminal.** Make a backup and bring it to the destination server ([Make a Backup](backup_restore.md#create)). If it is a clear backup, bring the `secrets/` folder of its data folder too: the archive does not hold it.

    Result: the archive (`.zip` or `.lfbk`) is on the destination server.

2. **Destination server — terminal, folder of `docker-compose.yml`.** The data folder `LibreFolio-data` must be empty, or not exist yet. If LibreFolio has already started on it, stop it (`docker compose down`) and move `LibreFolio-data` aside first.

    Result: no other data mixes with the archive's.

3. **Only for a secure backup (`.lfbk`) — terminal of an installation where LibreFolio's command line is available.** An `.lfbk` is not a zip: turn it into its zip with `backup decrypt`.

    ```bash
    # Host installation
    pipenv run ./dev.py backup decrypt librefolio-backup-20261015-121500.lfbk -o librefolio-backup-20261015-121500.zip

    # Docker, in a running LibreFolio container: the paths inside it, and the zip where the container's user can write
    docker compose exec librefolio python dev.py backup decrypt /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.lfbk -o /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip
    ```

    Result: the zip to unzip at step 4. Know this:

    - 🔓 The password is asked at the terminal, or read with `--password-file` or `--password-stdin`.
    - 🚫 An `-o` that already exists is refused, and nothing is written: the command never replaces a file.
    - 🔒 Only the owner reads the zip (`0600`): the user who ran the command, or with Docker the container's user.
    - 🗑️ The zip holds every user's data in clear: delete it once unzipped.
    - 🔑 If the backup holds the instance key, the command adds `🔑 It also holds the instance key: with it, every saved provider key can be read.`: whoever has that zip also reads the saved keys of the data providers.

4. **Destination server — terminal, folder of `docker-compose.yml`.** Unzip the zip into the data folder.

    ```bash
    # In the folder of docker-compose.yml, before the first start
    unzip librefolio-backup-20261015-121500.zip -d LibreFolio-data
    ```

    Result: `LibreFolio-data/` holds the archive's data. The `manifest.json` left there is harmless: you can delete it.

5. **Destination server — folder `LibreFolio-data/secrets/`.** Before the first start:

    - 🗝️ **Clear backup**: put the `secrets/` of the source server back into `LibreFolio-data/`, and the saved secrets stay readable. Without it, LibreFolio creates a new instance key the first time it needs one.
    - 🔐 **Secure backup that carries the key**: the zip already holds `secrets/instance.key`, and the saved keys of the data providers stay readable. Make the folder and the file private, or the start log has a warning («Startup Checks» in [Environment Variables](configuration.md)):

    ```bash
    chmod 700 LibreFolio-data/secrets
    chmod 600 LibreFolio-data/secrets/instance.key
    ```

    Result: the instance key is in place, and nothing in the start log is about it.

    !!! warning "⛔ The key of a backup, only on an empty data folder"

        Use the key of a backup only this way: on an empty data folder, on an installation that sets neither `LIBREFOLIO_INSTANCE_KEY` nor `LIBREFOLIO_INSTANCE_KEY_FILE`. A key set there wins over `secrets/instance.key`, and the saved keys of the data providers would stay unreadable.
        Never put it in place of a key already in use: what was saved with that key would become unreadable. To bring a secure backup to an installation that has its own key, restore it: the restore encrypts the saved keys again with that installation's key.

6. **Destination server — terminal, folder of `docker-compose.yml`.** First start, with the same image as the source or a newer one.

    ```bash
    docker compose up -d
    ```

    Result: the start applies the pending migrations by itself.

### ⛔ Never Backwards {: #never-backwards }

LibreFolio never takes a database back to an older version: use the version that made the archive, or a newer one. An older LibreFolio refuses an archive whose database holds a migration it does not know.

- 🏷️ `backup inspect` shows which version made the archive (`Made by LibreFolio <version>`); **Settings › About** shows the version of an instance.
- ❌ `backup restore` refuses such an archive with `revision_unknown`, before anything changes.
- 🛑 By hand, an older LibreFolio does not start on such data: the log has `Failed to apply database migrations`, and Docker keeps restarting the container. Stop it with `docker compose down`.

Update the receiving LibreFolio first ([Updating LibreFolio](../user/installation.md#updating)), then restore. With Docker, the `latest` image is the newest release.

---

## 🧯 When Something Goes Wrong {: #troubleshooting }

### 🔐 Making a Secure Backup {: #secure-problems }

| What you see | Why | What to do |
| --- | --- | --- |
| `❌ A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal (password_required)` | `backup create --encrypt` without a terminal to ask on, such as in cron | Give the password with `--password-file` or `--password-stdin` ([From the Command Line](backup_restore.md#command-line)) |
| `❌ The password of a backup needs at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: …)`, or in Settings › Administration › Backup *The password does not meet the rules of a backup's password.* | The rules are listed after `password_too_weak:`. In Settings, **Create backup** stays disabled until every rule is met; if the rules of a backup did not come from the server (`GET /api/v1/backup/instance/options`), the meter applies those of an account's password (8 characters), and the server still refuses fewer than 12 | Choose a longer password that meets every rule. Nothing was written |
| `❌ The two passwords differ (password_mismatch)` | The second password typed at the terminal is not the first | Run the command again |
| `❌ password file: <path> does not exist (password_unreadable)`, or `cannot be read`, `is empty or blank`, `is not UTF-8 text` | `--password-file` cannot give the password | Fix the file: the password alone, in UTF-8. With Docker, the path inside the container, such as `/run/secrets/backup_password` |
| `⚠️ The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore`, or in Settings › Administration › Backup *The instance key cannot be used: the backup was made without it, so the keys of the data providers must be entered again after a restore.* | `secrets/instance.key` is there, but damaged or out of reach, or longer than the 4096 bytes a restore can read back (the key LibreFolio generates has 43 characters). The backup is complete, without the key | If the start log says what is wrong with the key, fix it («Startup Checks» in [Environment Variables](configuration.md)), then make a new secure backup. If it says nothing, the key is too long to travel: keep a copy of `secrets/` with the backup, as for a clear backup |

### 🧾 The Check Refuses the Archive {: #check-refused }

`backup restore`, with or without `--dry-run`, ends with a refusal and its code in parentheses, without changing anything. Settings › Administration › Backup refuses the same archives and says why on the card, without the code: *The archive is damaged.* for `archive_damaged`, for instance.

| Code | Why | What to do |
| --- | --- | --- |
| `revision_unknown` | The archive comes from a newer LibreFolio | Update this installation ([Never Backwards](#never-backwards)), then run the command again |
| `manifest_newer_format` | The archive format is newer than the one this LibreFolio reads | Update LibreFolio first |
| `checksum_mismatch`, `archive_damaged`, `missing_entry` | The archive is damaged, cut short or changed | `backup inspect` names the entries that differ. Copy the archive again from where you keep it, or use another one |
| `database_damaged` | The database fails SQLite's integrity check, SQLite cannot read its schema, or it holds text that is not UTF-8. Settings › Administration › Backup: *The backup's database is damaged: it cannot be restored.* | Copy the archive again from where you keep it, or use another one. Text that is not UTF-8 means another program wrote to the database (LibreFolio never writes it), or the archive was changed |
| `database_foreign_objects` | The database holds a trigger, a view or a virtual table, which LibreFolio never creates. Settings › Administration › Backup: *The backup's database holds triggers, views or other objects LibreFolio never creates: it was not made by LibreFolio, or it was changed, and it cannot be restored.* | The archive was not made by LibreFolio, or was changed after: use another backup |
| `not_a_backup` | Not an archive LibreFolio wrote, such as a data folder zipped by hand | Put such a copy back [by hand](#by-hand), into an empty data folder |
| `sealed_backup_needs_key` | A sealed nightly backup (`.tar`): its password is inside, encrypted for a key the check does not have. Settings › Administration › Backup: *This is a sealed backup of a hosting panel: its password is encrypted for the provider's key. Extract backup.lfbk, open password.age with age, then restore backup.lfbk with that password.* | Restore it where its private key is: `backup restore <archive>.tar --identity-file <key file>` ([Sealed Backups](backup_sealed.md#sealed)) |
| `sealed_no_identity`, `sealed_identity_invalid`, `sealed_tar_invalid`, `sealed_manifest_invalid`, `sealed_password_invalid` | A [sealed backup](backup_sealed.md#sealed) given with `--identity-file` that does not open | See [Making or Opening a Sealed Backup](#sealed-problems) |
| `no_space` | The copy needs more free space than the disk of the data folder has | Free some space: the archive unpacked, plus twice its database, plus 64 MB, and for a secure backup the size of its `.lfbk` too |
| `archive_unreadable` | The archive cannot be opened, most often because the server's user cannot read it | With Docker and the official image, `sudo chown 1000:1000 <archive>` on the host gives it to that user |
| `restore_already_pending` | Another restore waits for the next start | Restart LibreFolio to apply it, or cancel it with `backup pending --cancel` or **Cancel the restore** in Settings › Administration › Backup |
| `wrong_password` | The password does not open the secure backup: not the one it was made with, or the start of the file was changed. Settings › Administration › Backup asks for it again: *Wrong password, or the file was changed: type the password again.* | Type it again as it was chosen, upper and lower case included. If it is right, copy the file again from where you keep it |
| `password_required` | A secure backup, and no password: the command had no terminal to ask on, and neither `--password-file` nor `--password-stdin` | Run the command at a terminal, or give the password with one of the two options |
| `envelope_damaged` | The secure backup is damaged, cut short, or changed after it was made | Copy it again from where you keep it, or use another one: LibreFolio reads no part of a damaged `.lfbk` |
| `envelope_unsupported` | The secure backup comes from a newer LibreFolio, or asks for settings this one does not accept | Update this installation first ([Never Backwards](#never-backwards)), then run the command again |

Two more messages:

- `❌ No file at <path>`: with Docker, give the path inside the container, `/app/backend/data/prod-docker/…`.
- `❌ The backup has no active administrator: after a restore nobody could manage the instance`, or the same in the report of Settings › Administration › Backup, whose confirmation stays disabled: on the installation the backup comes from, make an active account administrator, then make a new backup.

Every code: «Refusals — what the codes mean» in [CLI Admin Tools](cli_tools.md).

Two notices let the restore go on, but read them before you confirm:

- 🔑 *Your account is not among the administrators of this backup: after the restart you cannot sign in with it.* Only in the report of Settings › Administration › Backup, in red. After the restore you sign in with an account of the backup, with the password it had then: the account you use now is not in it. Before you confirm, make sure you know the password of one of the administrators the report names; if you do not know it, use another backup.
- `⚠️ Ledger totals differ from the backup's (<n> lines):`, or *Ledger totals differ from the backup's on 2 lines:* in the report of Settings › Administration › Backup: the cash of a broker or the quantity of a position in the copy, once up to date, is not the one the backup recorded, because transactions were lost, added or changed between the two (by a migration that corrects data, for instance). Each line that follows gives a broker's number, then a currency or an asset's number, with the backup's amount before the arrow and the copy's after it: the numbers are those of the addresses `/brokers/<id>` and `/assets/<id>` in the app. Compare these lines with the instance the backup comes from. The notice never blocks the restore: whether you confirm is up to you.

### 🔏 Making or Opening a Sealed Backup {: #sealed-problems }

To make one, with `backup create --sealed` or `--recipient`: nothing is written, and the command exits with `1`.

| What you see | Why | What to do |
| --- | --- | --- |
| `❌ LIBREFOLIO_BACKUP_RECIPIENTS is not set: give the recipients there, or with --recipient age1…` | `--sealed` did not find the variable: not in `.env`, or the container was not recreated after it was added | Set it ([Seal Every Backup](backup_sealed.md#sealed-recipients)), then `docker compose up -d`, or run the command from the project folder with `pipenv run`, which reads `.env` |
| `❌ LIBREFOLIO_BACKUP_RECIPIENTS: item 2 is not an age recipient: expected age1… as age-keygen prints it (BACKUP_RECIPIENTS_INVALID)`, or `expected at most 2 recipients, comma-separated (BACKUP_RECIPIENTS_TOO_MANY)`, or `item 2 repeats an earlier recipient (BACKUP_RECIPIENTS_DUPLICATE)` | The variable holds something other than one or two distinct `age1…` keys: a private key, an SSH key, a comma too many | Write the public keys only, as `keygen` or `age-keygen -y` prints them. The **Security** tab says the same (`backup.recipients`) |
| `❌ A --recipient is not an age recipient: expected age1…, as keygen or age-keygen prints it`, `❌ The same recipient is given twice`, `❌ At most 2 recipients: --recipient twice, while a key is being changed` | The same rules, for `--recipient` | Give one or two different public keys |
| `❌ A sealed backup draws a password of its own: --sealed and --recipient go without --encrypt, --password-file or --password-stdin` | A sealed backup has no password to give | Drop the password options |
| `❌ --sealed reads the recipients from LIBREFOLIO_BACKUP_RECIPIENTS: give them there or with --recipient, not both` | `--sealed` and `--recipient` together | Keep one of the two |
| `❌ <path> already exists: a key file is never written over` | `backup keygen` never replaces a key: the old one may still open backups | Choose another file name, or move the old file away first if you are sure no backup needs it |

To open one, with `--identity-file`: the command changes nothing and exits with `1`. It reads the key file first, then the `.tar`.

| What you see | Why | What to do |
| --- | --- | --- |
| `(sealed_backup_needs_key)` | A `.tar` given without `--identity-file`, on the command line or in Settings › Administration › Backup | Give the key file, or [open it by hand](backup_sealed.md#sealed-by-hand) and restore `backup.lfbk` with its password |
| `❌ --identity-file opens a sealed backup (.tar) only: <path> is not one` | A `.zip` or an `.lfbk` given with `--identity-file` | Drop `--identity-file`: those archives open as usual |
| `❌ The key file cannot be read (sealed_identity_invalid)`, `Line 3 of the key file is not an age key`, `The key file holds no age key` | The file is not a private key: the public key alone, a key copied with a missing character, or a file the command cannot read | Give the file written by `keygen` or `age-keygen`, with its `AGE-SECRET-KEY-1…` line. Comments (`#`) and blank lines may stay |
| `❌ None of the keys given opens the password of this backup (sealed_no_identity)` | The backup was sealed for another key: an older one, before a [change of key](backup_sealed.md#sealed-rotation) | Compare its `recipients` (`tar xOf <archive>.tar manifest.json`) with the `# public key:` line of your key files, and give the matching one |
| `(sealed_tar_invalid)`, such as `The archive is cut short` or `The archive does not hold manifest.json, password.age and backup.lfbk, in this order` | Not the `.tar` LibreFolio wrote: cut short by a copy, rebuilt by hand with `tar cf`, or not a sealed backup | Copy the original again from where you keep it, or use another night's backup |
| `(sealed_manifest_invalid)`, such as `The manifest does not describe backup.lfbk: its size or SHA-256 differs` | `manifest.json` or `backup.lfbk` was changed | The copy is damaged: use another one |
| `(sealed_password_invalid)` | The key opened `password.age`, but what it holds is not a password LibreFolio wrote | Not a LibreFolio backup, or changed: use another copy |
| `❌ The password does not open this backup (wrong_password)` | The key opened the password, but that password does not open `backup.lfbk`: the two files come from different backups, or one was changed | Use another copy, kept whole as LibreFolio wrote it |
| `(envelope_damaged)`, during the check or the restore | A byte of `backup.lfbk` was changed after the backup was made: the password was right | Use another copy: LibreFolio reads no part of a damaged `.lfbk` |

### 🔁 The Restore Does Not Go Through {: #restart-problems }

| What you see | Why | What to do |
| --- | --- | --- |
| `backup pending` says `The state of the restore cannot be read`, `(restore_state_unreadable: <reason>)` | `.restore/restore.json` cannot be used: permissions (`io`), a link or a folder in its place (`not_a_file`), or content LibreFolio did not write (`invalid`). A restore may have stopped half way. Meanwhile no checked copy is removed | For `io`, give `.restore/` back to the user that runs LibreFolio and check again. Otherwise stop LibreFolio and run `backup pending --recover previous`: the data of before comes back from `.restore/previous/`. Then start it, or restore a backup again («An Unreadable Restore State» in [CLI Admin Tools](cli_tools.md)) |
| `backup pending` ends with `(server_running)` | At the last start, another server process served the data folder: a worker restarted on its own, or a second server | Restart the whole server, never one worker, and run one server per data folder |
| `backup pending` ends with `(other_data_directory)` | The server found its data folder under a path other than the one the restore was confirmed for, such as a copy of the data folder | `backup pending --cancel`, or **Cancel the restore** in Settings › Administration › Backup, then restore the archive again: with `backup restore`, where the server runs |
| `backup pending` ends with `(backup_running)` | A backup was running at the last start | Nothing: the next start applies the restore |
| `backup pending` says the restore was rolled back, `(first_start_failed)` | The first start on the restored data did not complete | The data is as it was. The log of that start has the cause: fix it, then restore the archive again |
| … rolled back, `(swap_interrupted)` | The start that applied the restore was interrupted, and the next one undid it | Restore the archive again |
| … rolled back, `(swap_failed)` | The folders could not be moved into place | Make `sqlite/`, `custom-uploads/`, `broker_reports/` and `scenario_catalog/` real folders of the data folder, neither links nor separate mounts, then restore the archive again |
| … rolled back, `(stage_missing)` | The checked copy was gone or changed | Restore the archive again |
| A start stops, and its log says another server applied the restore or serves the data folder | Two LibreFolio servers use the same data folder | Stop the other one, then start LibreFolio again: `backup pending` will tell whether the restore was kept |
| LibreFolio does not start, and its log has `The data directory is half restored` | Putting the former data back failed too, on a disk or permission error for instance | Fix the cause the log gives: every start tries again |
| `Failed to apply database migrations` after an unzip by hand | An archive from a newer LibreFolio, or a migration that fails: the log has the error | For a newer archive, `docker compose down`, then use the version that made it or a newer one ([Never Backwards](#never-backwards)) |

### 🖱️ What Settings › Administration › Backup Says {: #restore-settings-problems }

The restart window gives in words the reason that `backup pending` gives as a code: the table says which one, and the row of that code in [The Restore Does Not Go Through](#restart-problems) says what to do. On the card, **Try again** reads the state of the restore again; to send an archive again, choose it again.

| What you see | Why | What to do |
| --- | --- | --- |
| After **Restore and restart**, the sign-in page, with no message | The restore worked and ended every session. Only in the case of the next row does the sign-in page come although the restore did not go through | Sign in with an administrator of the backup, with the password the account had when the backup was made. If nobody remembers it: [After a Restore](#after-restore) |
| The sign-in page appeared, but once signed in the data is as before | The page did not read the outcome with its ticket (a reload of the page, more than an hour of waiting, or LibreFolio restarted from the command line rather than from the page), and LibreFolio runs without `JWT_SECRET` ([Keep Users Signed In After a Restart](index.md#session-persistence)): every start signs everyone out, even if the restore did not go through. The accounts and passwords of before still sign in | Open **Settings › Administration › Backup**: the card says *The last restore was rolled back on …*, or shows the restore waiting, with the reason; then see the row of that reason below |
| *LibreFolio has not come back yet. If nothing starts it again by itself, start it yourself: the restore is applied at that start.* | LibreFolio has not answered for a minute: nothing restarted it (no supervisor, or one that starts it only after a failure, [Who Starts LibreFolio Again](backup_restore.md#supervisors)), or its start is slow | If it is stopped, start it: `docker compose up -d` with Docker, or [start the server](cli_tools.md#start-the-server) on a host installation. The page goes on by itself once LibreFolio answers |
| *LibreFolio has not stopped. If it does not restart by itself, restart it yourself: the restore is applied at that start.*, a minute after **Restore and restart**, with **Back to Backup** | The request did not stop the server: the restore still waits for the next start, and `backup pending` shows it waiting | Restart LibreFolio yourself: `docker compose restart librefolio` with Docker, or stop the whole server and [start it](cli_tools.md#start-the-server) again. Its start applies the restore, and the page goes on by itself. Or **Back to Backup**: the card shows the restore waiting, to restart (**Restart now and restore**) or cancel (**Cancel the restore**) |
| **The restore did not go through**, with *The data is as it was before: …* | The restore was rolled back: *the first start after it did not complete* (`first_start_failed`), *the start that applied it was interrupted* (`swap_interrupted`), *its folders could not be moved into place* (`swap_failed`) or *its checked copy was gone* (`stage_missing`) | What the row of that code says. **Back to Backup** returns to the card, which says when the last restore was rolled back and why |
| **The restore did not go through**, with *LibreFolio restarted, but the restore was not applied.* and the reason | A start left the restore waiting: *At the last start a backup was running…* (`backup_running`), *It was confirmed for another data directory…* (`other_data_directory`) or *At the last start another LibreFolio process was serving the data…* (`server_running`) | What the row of that code says. **Back to Backup** shows the restore waiting, with **Restart now and restore** and **Cancel the restore** |
| *The archive is larger than this LibreFolio accepts (500 MB).* | The installation limits the archives uploaded for a restore with `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` (`backup_too_large`) | There is no limit unless someone set one: raise it, or set it to `0`, then restart ([The Upload Limit of a Restore](backup_restore.md#restore-upload-limit)). Or restore from the command line, which has no upload limit |
| *Unpacked, the archive is larger than this LibreFolio accepts for a restore.* | The sizes the manifest declares, added up, exceed `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` (`unpacked_too_large`). The check refused the archive before unpacking anything | There is no limit unless someone set one: raise it, set it to `0` or remove it, then restart ([The Upload Limit of a Restore](backup_restore.md#restore-upload-limit)). Or restore from the command line with `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` in front of `backup restore` |
| *LibreFolio cannot read its restore limit right now: try again later.* | `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` is not a whole number of megabytes (`backup_restore_unavailable`): no check starts, and the archive stays on the server. The log has an error, from the start already | Write a whole number of megabytes, `0` for no limit, or remove the variable, then restart; the **Security** tab of Settings › Administration names it (`backup.restore_limit`). Then choose the archive again |
| Sending stops with *A proxy in front of LibreFolio refused an archive this large: ask whoever runs it to accept larger uploads, or restore from the command line.*, or with *The server does not answer: check the connection and try again.* or *The server answered with an error: the server's log has the cause.*, and the log of LibreFolio has nothing about it | A proxy in front of LibreFolio refused the archive: Nginx takes only 1 MB by default. The first message: the proxy answers *too large* (HTTP 413); the others: it drops the connection or answers otherwise | Let the proxy take archives as large as yours, with `client_max_body_size` in Nginx ([The Upload Limit of a Restore](backup_restore.md#restore-upload-limit)), or restore from the command line |
| *Not enough free space on the server for this archive.* | The disk of the data folder, or a quota, is full (`backup_no_space`): while sending, and then nothing of the archive is kept (a network file system or a quota may report it only at the end of the file), or at the confirmation with **Restore and restart**, and then nothing is confirmed and the checked copy stays; the log has `A restore could not be confirmed: not enough free space` | Free some space on the disk of the data folder, then choose the archive again. After a confirmation, **Try again**: the report comes back, and **Restore and restart** confirms again |
| *Not enough free space on the server to check the archive.* | The disk of the data folder, or a quota, is full when the check starts, and then the archive stays on the server, or while the check makes its copy (`no_space`) | Free some space, as much as the `no_space` row of [The Check Refuses the Archive](#check-refused) says, then choose the archive again |
| *The copy could not be written: the server's log has the cause.* | The check did not start, or did not write its copy, for a reason other than space (`stage_failed`): owner or permissions of a folder of `.restore/`, a read-only disk, a disk error. The log has `A check of a backup archive could not start`, with the error and the system's reason | Fix what the log line names, for instance by giving `.restore/` back to the user that runs LibreFolio, then choose the archive again |
| *Not enough free space on the server for the backup.*, on the card **Back up the instance** | The disk of the data folder, or a quota, is full (`backup_no_space`), as the backup starts or while it runs: the backup is made in `backups/`, on that disk | Free some space on that disk, then **Try again**. How much space a backup needs: «Create an Archive» in [CLI Admin Tools](cli_tools.md) |
| *The restore could not be confirmed: the server's log has the cause. Nothing changed.*, after **Restore and restart** | The confirmation was not written, for a reason other than space (`restore_confirm_failed`): owner or permissions of `.restore/`, a read-only disk, a disk error. The log has `A restore could not be confirmed`, with the error and the system's reason. Nothing is confirmed, and the checked copy stays | Fix what the log line names, for instance by giving `.restore/` back to the user that runs LibreFolio, then **Try again**: the report comes back, and **Restore and restart** confirms again |
| *The restore could not be cancelled: the server's log has the cause. It still waits for the next start.*, after **Cancel the restore**: the card still shows the restore waiting, with **Restart now and restore** and **Cancel the restore** | Its state in `.restore/` could not be locked or removed (`restore_cancel_failed`): owner or permissions, a read-only disk, a disk error. The log has `A pending restore could not be cancelled`, with the error and the system's reason. A copy that cannot be removed after the cancellation is no such failure: the restore is cancelled, and the log has the warning `The copy of a cancelled restore could not be removed: it goes when its check expires` | Fix what the log line names, then **Cancel the restore** again, on the same card: until it is cancelled, the next start of LibreFolio applies the restore. A copy left behind is removed at the first start of LibreFolio once its check is 24 hours old |
| *LibreFolio could not be restarted: the server's log has the cause. The restore still waits for the next start.*, after **Restore and restart** or **Restart now and restore** | LibreFolio was not stopped: the ticket with which the page reads the outcome was not written (`restore_restart_failed`), for a full disk or for the owner or permissions of `.restore/`. The log has `The ticket of the restore's outcome could not be written: no restart`. The restore is confirmed, and waits | Fix what the log line names, then **Restart now and restore**, which the card shows with the restore waiting. Or restart LibreFolio yourself, `docker compose restart librefolio` with Docker: its start applies the restore |
| *The state of the restore cannot be read: the server's log has the cause. A restore may still wait for the next start.* | The state of the restore in `.restore/` cannot be read (`restore_state_unreadable`): owner or permissions, such as files written by `root`, or a disk error. Whether a restore waits is not known: confirming another restore is refused, and a start that does not read the state leaves it as it is and applies nothing | Give `.restore/` and its files back to the user that runs LibreFolio, readable by it, then **Try again**. With Docker, each start of the container gives the data folder back to that user before LibreFolio reads the state, so a restore that waits is applied at that start; permissions changed with `chmod` stay as they are. `backup pending` says the same, with the system's reason |
| The card refuses the archive, for instance *This file is not a LibreFolio backup.*, *The archive is damaged.* or *The secure backup is damaged or was changed: it cannot be opened.* | The check refused it, as `backup restore` does | See its code in [The Check Refuses the Archive](#check-refused) |
| The card asks for the password of a secure backup again: *Wrong password, or the file was changed: type the password again.* | The password does not open the backup (`wrong_password`) | Type it again: the archive stays on the server and is not sent again. If the password is right, the file was changed: **Cancel**, then choose a good copy with **Choose an archive…** |

### 🔑 After a Restore {: #after-restore }

| What happens | What to do |
| --- | --- |
| Nobody remembers the password an administrator had in the backup | Whoever runs the server sets a new one with `user reset`, or creates a reset link with `user reset-link` ([Reset a Password or Lock an Account](cli_tools.md#reset-a-password-or-lock-an-account)) |
| The sign-in page answers that an account is disabled: it was waiting for its email verification | An administrator clicks **Reactivate** on its row ([What Each Action Does](users.md#actions)), or deletes it so that its owner signs up again ([Delete an Account](users.md#delete)) |
| A link sent before the restore no longer works | Send a new invitation or a new password-reset link ([Users & Invitations](users.md)) |
| A secret plugin setting is reported as set but unreadable, as the report of the check announced (*… cannot be read with this instance's key: enter them again after the restore.*) | The backup had no key able to read it: a clear backup, or a secure one whose instance had a key set in its environment, or could not use its own. If you still have the old key, put it back in place before anyone enters a secret again; only otherwise enter the setting again in **Settings › Plugins**, where each user enters their own ([What Follows](backup_restore.md#what-follows)). If the start log says that the key of this installation cannot be used, fix that first («Startup Checks» in [Environment Variables](configuration.md)) |
| After a move, no email is sent | Set the email variables on this installation, then restart ([Email](email.md)) |

---

## 🔗 Related

- 📄 **[Backup, Restore and Moving Your Instance](backup_restore.md)** — What a Backup Holds, Make a Backup, Secure Backups, …
- 📄 **[Backups: Sealed Backups](backup_sealed.md)** — Sealed Backups: a Key Instead of a Password
