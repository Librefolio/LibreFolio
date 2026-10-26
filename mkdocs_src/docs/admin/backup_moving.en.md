# 🏠 Backups: Moving and Troubleshooting

This page is part of the backup guide. It covers **moving** your LibreFolio between a hosted instance and your own server, and what to do **when something goes wrong** with a backup or a restore.

The rest of the guide starts on [Backup, Restore and Moving Your Instance](backup_restore.md).

---

## 🏠 Bring Your LibreFolio Home {: #bring-home }

An archive moves your LibreFolio from one installation to another: from an instance someone hosts for you to your own server, or the other way round. The installation that receives it must run the same version of LibreFolio or a newer one ([Never Backwards](#never-backwards)).

### 🏡 From a Hosted Instance to Your Server {: #to-your-server }

With Docker Compose on your server:

1. **Download a backup** of the hosted instance, as one of its administrators: **Settings › Administration › Backup**, **Create backup**, then **Download** ([From Settings › Administration › Backup](backup_restore.md#settings-backup)). Its version is in **Settings › About** ([About](../user/settings/about.md)). Choose **Secure** to bring along the saved keys of the data providers: they travel when LibreFolio generated the key of the hosted instance, not when its provider set it, and the report of the check says whether the backup carries it. When it does not, as a clear backup never does, keep the instance key of the hosted instance if your hosting provider gives it to you, as privately as the archive: the restore then re-encrypts those saved keys with the key of your server (step 4).
2. **Prepare LibreFolio** on your server with steps 1 and 2 of [Installation with Docker](../user/installation.md): the folder, `docker-compose.yml` and `.env`. Do not start it yet.
3. **Copy the archive into its data folder**, next to `docker-compose.yml`, to restore it from the command line:

    ```bash
    mkdir -p LibreFolio-data/backups
    cp /path/to/librefolio-backup-20261015-121500.zip LibreFolio-data/backups/
    ```

    A secure backup goes the same way, `.lfbk` instead of `.zip`. The instance key, if you have it, never goes into `LibreFolio-data/`: step 4 hands it to the container. From the app, skip this step: you choose the archive on your computer.

4. **Start LibreFolio, restore the archive, restart**:

    ```bash
    docker compose up -d
    docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip
    docker compose restart librefolio
    ```

    `backup restore` checks the archive on a copy first: if this LibreFolio cannot take it, the command says why, and nothing changes. For a secure backup, it asks its password first. Read the report, then type `restore`.

    With the instance key of the hosted instance, in a file such as `old-instance.key` next to `docker-compose.yml`, kept private (`chmod 600 old-instance.key`), the restore line becomes three, before the restart:

    ```bash
    docker compose cp old-instance.key librefolio:/root/old-instance.key
    docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip --instance-key-file /root/old-instance.key
    docker compose exec librefolio rm /root/old-instance.key
    ```

    `/root` is root's own folder in the container, which LibreFolio's user can neither read nor change, while it could swap a file in `LibreFolio-data/`: the command reads the key as root, before it runs as that user. The report counts the saved keys it re-encrypted with the key of your server («The Instance Key of Another Installation» in [CLI Admin Tools](cli_tools.md)). Keep your own copy of the key apart.

    Or, from the app, which takes no instance key: start LibreFolio with `docker compose up -d`, open it, and create the administrator account it asks for, with **Register here**. Then restore the archive from **Settings › Administration › Backup** ([Restore from Settings › Administration › Backup](backup_restore.md#restore-settings)): it is checked on a copy in the same way, and **Restore and restart** stops LibreFolio, which Docker starts again to apply the restore. The restore replaces the account you created with the accounts of the backup.

5. **Sign in** with your account of the hosted instance, and the password it had when you made the backup.
6. **Set what the archive does not carry**: the options of `.env` you need, the email ones included ([Email](email.md)), and the secret plugin settings the report counted as unreadable ([What Follows](backup_restore.md#what-follows)).

Good to know:

- 🐳 At every start the container gives the whole `LibreFolio-data/` folder to its user: an archive copied in before the first start can be read by the server. One copied in later may need `sudo chown 1000:1000 <archive>` with the official image: see «Back Up with Docker» in [CLI Admin Tools](cli_tools.md).
- 🔒 If the hosted instance is blocked, its app shows the block page instead of Settings: as an administrator, download the archive from its card **Keep a copy of the data** ([What Users See](hosting_instances.md#what-users-see)). Otherwise ask your hosting provider: a hosting panel can still make one on a blocked instance ([Backups for Your Hosting Panel](hosting_panel_backups.md#panel-backups)).
- 🖥️ On a host installation, the same steps with `pipenv run ./dev.py backup restore <archive>`, then a restart of the server by hand. From Settings › Administration › Backup, the server stops by itself: start it again yourself, unless something supervises it ([Who Starts LibreFolio Again](backup_restore.md#supervisors)).

### ✋ By Hand: Unzip Before the First Start {: #by-hand }

Instead of a restore, unzip the archive into the data folder before the first start of LibreFolio, with the same image or a newer one. The start applies the pending migrations by itself.

```bash
# In the folder of docker-compose.yml, before the first start
unzip librefolio-backup-20261015-121500.zip -d LibreFolio-data
docker compose up -d
```

A secure backup (`.lfbk`) is not a zip: first turn it into its zip with `backup decrypt` («Decrypt a Secure Archive» in [CLI Admin Tools](cli_tools.md)), where LibreFolio's command line runs, then unzip that zip as above. With Docker, a restore is simpler: it takes the `.lfbk` as it is ([From a Hosted Instance to Your Server](#to-your-server)).

```bash
# Host installation
pipenv run ./dev.py backup decrypt librefolio-backup-20261015-121500.lfbk -o librefolio-backup-20261015-121500.zip

# Docker, in a running LibreFolio container: the paths inside it, and the zip where the container's user can write
docker compose exec librefolio python dev.py backup decrypt /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.lfbk -o /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip
```

- 📂 The data folder must be empty, or not exist yet: if LibreFolio has already started on it, stop LibreFolio and move `LibreFolio-data` aside first. Nothing of other data may mix with the archive's.
- 🔎 Nothing checks the archive first: a damaged archive, or one from a newer LibreFolio, shows when the start fails, and some damage only later, when a page reads the data it touches. A restore, from Settings › Administration › Backup or the command line, checks it on a copy before anything changes. To check an archive before you unzip it by hand, use an installation of LibreFolio that already runs: `backup inspect <archive>` compares each file with the manifest and, for a zip, writes nothing; `backup restore <archive> --dry-run` makes the whole check of a restore, on a copy («Check an Archive» and «Try a Restore on a Copy» in [CLI Admin Tools](cli_tools.md)). The dry run works in that installation's data directory: never point it at the empty folder you are about to fill.
- 🧹 The `manifest.json` left in `LibreFolio-data/` is harmless: you can delete it.
- 🔓 `backup decrypt` asks the password at the terminal, or reads it with `--password-file` or `--password-stdin`. It never replaces a file: an `-o` that already exists is refused, and nothing is written. Only the owner of the zip can read it (`0600`): the user who ran the command, or with Docker the container's user. It holds every user's data in clear, so delete it once unzipped. When the backup carries the instance key, the command adds `🔑 It also holds the instance key: with it, every saved provider key can be read.`: whoever has that zip can also read the saved keys of the data providers.
- 🗝️ From a clear backup, there is no `secrets/`: LibreFolio creates a new instance key the first time it needs one. When you move your own installation, put its `secrets/` back into `LibreFolio-data/` before the first start, and the saved secrets stay readable.
- 🔐 The zip of a secure backup holds `secrets/instance.key` when the backup carries the key: unzipped, the key is in place, and the saved keys of the data providers stay readable. Before the first start, make the folder and the file private, or the start log has a warning («Startup Checks» in [Environment Variables](configuration.md)): `chmod 700 LibreFolio-data/secrets` and `chmod 600 LibreFolio-data/secrets/instance.key`.
- ⛔ Use the key of a backup only this way, on an empty data folder, and on an installation that sets neither `LIBREFOLIO_INSTANCE_KEY` nor `LIBREFOLIO_INSTANCE_KEY_FILE`: a key set there wins over `secrets/instance.key`, and the saved keys of the data providers would stay unreadable. Never put it in place of a key already in use: what was saved under that key would become unreadable. To bring a secure backup to an installation that has its own key, restore it: the restore re-encrypts the saved keys with that installation's key.
- 📖 The steps for any installation, the host one included: «Use an Archive on Another Installation» in [CLI Admin Tools](cli_tools.md).

### ☁️ From Your Server to a Hosted Instance {: #to-a-hosted-instance }

1. **Make a backup** on your server: **Settings › Administration › Backup**, or `backup create` on the command line ([Make a Backup](backup_restore.md#create)). Make it [secure](backup_restore.md#secure) to bring along the saved keys of the data providers, if LibreFolio generated the key of your server.
2. **Restore it on the hosted instance.** As one of its administrators, restore it yourself from **Settings › Administration › Backup** ([Restore from Settings › Administration › Backup](backup_restore.md#restore-settings)), within the upload limit the card shows, if the instance has one ([The Upload Limit of a Restore](hosting_panel_backups.md#restore-upload-limit)). Otherwise, or for a larger archive, hand it to whoever runs the hosted instance, as privately as you keep it: they restore it on its server with the same command, `backup restore`, then restart it ([Restore on This Installation](backup_restore.md#restore)). The hosted instance must run the same version as yours, or a newer one.
3. **Sign in** there with your account of your own server, and the password it had when you made the backup.
4. **Enter again the secret plugin settings the report counted as unreadable**: the hosted instance keeps its own instance key. A secure backup brings the others along, re-encrypted with that key. Email and the other options are the configuration of the hosted instance.

### ⛔ Never Backwards {: #never-backwards }

LibreFolio never takes a database back to an older version: use the version that made the archive, or a newer one. An older LibreFolio refuses an archive whose database carries a migration it does not know.

- 🏷️ `backup inspect` shows which version made the archive (`Made by LibreFolio <version>`), and **Settings › About** shows the version of an instance.
- ❌ `backup restore` refuses such an archive with `revision_unknown`, before anything changes.
- 🛑 By hand, an older LibreFolio does not start on such data: its log has `Failed to apply database migrations`, and Docker keeps restarting the container. Stop it with `docker compose down`.

Update the receiving LibreFolio first ([Updating LibreFolio](../user/installation.md#updating)), then restore. With Docker, the `latest` image is the newest release.

---

## 🧯 When Something Goes Wrong {: #troubleshooting }

### 🔐 Making a Secure Backup {: #secure-problems }

| What you see | Why | What to do |
| --- | --- | --- |
| `❌ A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal (password_required)` | `backup create --encrypt` without a terminal to ask on, such as in cron | Give the password with `--password-file` or `--password-stdin` ([From the Command Line](backup_restore.md#command-line)) |
| `❌ The password of a backup needs at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: …)`, or in Settings › Administration › Backup *The password does not meet the rules of a backup's password.* | The password misses the rules listed after `password_too_weak:`. In Settings the meter keeps **Create backup** disabled until every rule is met; when it could not read the rules of a backup from the server (`GET /api/v1/backup/instance/options`), it checks those of an account's password, with 8 characters, and the server refuses a shorter one than 12 | Choose a longer password that meets every rule. Nothing was written |
| `❌ The two passwords differ (password_mismatch)` | The second password typed at the terminal is not the first | Run the command again |
| `❌ password file: <path> does not exist (password_unreadable)`, or `cannot be read`, `is empty or blank`, `is not UTF-8 text` | `--password-file` cannot give the password | Fix the file: it holds the password alone, in UTF-8. With Docker, give the path inside the container, such as `/run/secrets/backup_password` |
| `⚠️ The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore`, or in Settings › Administration › Backup *The instance key cannot be used: the backup was made without it, so the keys of the data providers must be entered again after a restore.* | `secrets/instance.key` is there, but damaged or out of reach, or longer than 4096 bytes, more than a restore reads back (the key LibreFolio generates has 43 characters). The backup is complete, without the key | If the start log says what is wrong with the key, fix it first («Startup Checks» in [Environment Variables](configuration.md)), then make a new secure backup. If it says nothing, the key is too long to travel: keep a copy of `secrets/` with the backup, as for a clear one |

### 🧾 The Check Refuses the Archive {: #check-refused }

`backup restore`, with or without `--dry-run`, ends a refusal with its code in parentheses, and changes nothing. Settings › Administration › Backup refuses the same archives and says why on its card, without the code: *The archive is damaged.* for `archive_damaged`, for instance.

| Code | Why | What to do |
| --- | --- | --- |
| `revision_unknown` | The archive comes from a newer LibreFolio | Update this one ([Never Backwards](#never-backwards)), then run the command again |
| `manifest_newer_format` | The archive format is newer than this LibreFolio reads | Update LibreFolio first |
| `checksum_mismatch`, `archive_damaged`, `missing_entry` | The archive is damaged, cut short, or was changed | `backup inspect` names the entries that differ. Copy the archive again from where you keep it, or use another one |
| `database_damaged` | The archive's database fails SQLite's integrity check, SQLite cannot read its schema, or it holds text that is not UTF-8: LibreFolio never writes such text, and after a restore every list holding it would fail to load. Settings › Administration › Backup: *The backup's database is damaged: it cannot be restored.* | Copy the archive again from where you keep it, or use another one. Text that is not UTF-8 means another program wrote to the database, or the archive was changed |
| `database_foreign_objects` | The archive's database holds a trigger, a view or a virtual table. LibreFolio never creates them, and their SQL would run during the check and in the server after a restore, so the check refuses them before it opens the copy for anything else. Settings › Administration › Backup: *The backup's database holds triggers, views or other objects LibreFolio never creates: it was not made by LibreFolio, or it was changed, and it cannot be restored.* | The archive was not made by LibreFolio, or was changed after: use another backup |
| `not_a_backup` | Not an archive LibreFolio wrote, such as a data directory zipped by hand | Put such a copy back [by hand](#by-hand), into an empty data directory |
| `sealed_backup_needs_key` | A sealed nightly backup of a hosting panel (`.tar`): its password is inside, encrypted for the provider's key, and the check cannot open it. Settings › Administration › Backup: *This is a sealed backup of a hosting panel: its password is encrypted for the provider's key. Extract backup.lfbk, open password.age with age, then restore backup.lfbk with that password.* | Restore it where its private key is: `backup restore <archive>.tar --identity-file <key file>` ([Sealed Backups](backup_sealed.md#sealed)), or the way your hosting provider tells you |
| `sealed_no_identity`, `sealed_identity_invalid`, `sealed_tar_invalid`, `sealed_manifest_invalid`, `sealed_password_invalid` | A [sealed backup](backup_sealed.md#sealed) given with `--identity-file` that does not open | See [Making or Opening a Sealed Backup](#sealed-problems) |
| `no_space` | The copy needs more free space than the disk of the data directory has | Free some space: the archive unpacked, plus twice its database, plus 64 MB, and for a secure backup the size of its `.lfbk` too |
| `archive_unreadable` | The archive cannot be opened, most often because the server's user may not read it | With Docker and the official image, `sudo chown 1000:1000 <archive>` on the host gives it to that user |
| `restore_already_pending` | Another restore waits for the next start | Restart LibreFolio to apply it, or drop it with `backup pending --cancel` or **Cancel the restore** in Settings › Administration › Backup |
| `wrong_password` | The password does not open the secure backup: not the one it was made with, or the start of the file was changed. Settings › Administration › Backup asks for it again: *Wrong password, or the file was changed: type the password again.* | Type it again as it was chosen, upper and lower case included. If it is right, copy the file again from where you keep it |
| `password_required` | A secure backup, and no password: the command had no terminal to ask on, and neither `--password-file` nor `--password-stdin` | Run the command at a terminal, or give the password with one of the two options |
| `envelope_damaged` | The secure backup is damaged, cut short, or was changed after it was made | Copy it again from where you keep it, or use another one: LibreFolio reads no part of a damaged `.lfbk` |
| `envelope_unsupported` | The secure backup comes from a newer LibreFolio, or asks for settings this one does not accept | Update this one first ([Never Backwards](#never-backwards)), then run the command again |

Two more messages:

- `❌ No file at <path>`: with Docker, give the path inside the container, `/app/backend/data/prod-docker/…`.
- `❌ The backup has no active administrator: after a restore nobody could manage the instance`, or the same in the report of Settings › Administration › Backup, whose confirmation then stays disabled: on the installation the backup comes from, make an active account administrator, then make a new backup.

Every code: «Refusals — what the codes mean» in [CLI Admin Tools](cli_tools.md).

Two notices let the restore go on, but read them before you confirm.

- 🔑 *Your account is not among the administrators of this backup: after the restart you cannot sign in with it.* This one is shown only in the report of Settings › Administration › Backup, in red. After a restore you sign in with an account of the backup, with the password it had then, and the account you are using now is not in it. Before you confirm, make sure you know the password of one of the administrators the report names. If you do not know it, use another backup.
- `⚠️ Ledger totals differ from the backup's (<n> lines):`, or *Ledger totals differ from the backup's on 2 lines:* in the report of Settings › Administration › Backup: the cash of a broker or the quantity of a position in the copy, once up to date, is not the one the backup recorded. Transactions were lost, added or changed between the backup and the copy, by a migration that corrects data for instance. Read the lines that follow: each gives a broker's number, then a currency or an asset's number, with the backup's amount before the arrow and the copy's after it. The numbers are those in the addresses of the broker's and the asset's pages in the app, `/brokers/<id>` and `/assets/<id>`. Compare these lines with the instance the backup comes from. The warning never blocks the restore: whether you confirm it is up to you.

### 🔏 Making or Opening a Sealed Backup {: #sealed-problems }

Making one, with `backup create --sealed` or `--recipient`: nothing is written, and the command exits with `1`.

| What you see | Why | What to do |
| --- | --- | --- |
| `❌ LIBREFOLIO_BACKUP_RECIPIENTS is not set: give the recipients there, or with --recipient age1…` | `--sealed` found no variable: not in `.env`, or the container was not recreated after it was added | Set it ([Seal Every Backup](backup_sealed.md#sealed-recipients)), then `docker compose up -d`, or run the command from the project folder with `pipenv run`, which reads `.env` |
| `❌ LIBREFOLIO_BACKUP_RECIPIENTS: item 2 is not an age recipient: expected age1… as age-keygen prints it (BACKUP_RECIPIENTS_INVALID)`, or `expected at most 2 recipients, comma-separated (BACKUP_RECIPIENTS_TOO_MANY)`, or `item 2 repeats an earlier recipient (BACKUP_RECIPIENTS_DUPLICATE)` | The variable holds something else than one or two different `age1…` keys: a private key, an SSH key, a comma too many | Write the public keys only, as `keygen` or `age-keygen -y` prints them. The **Security** tab says the same (`backup.recipients`) |
| `❌ A --recipient is not an age recipient: expected age1…, as keygen or age-keygen prints it`, `❌ The same recipient is given twice`, `❌ At most 2 recipients: --recipient twice, while a key is being changed` | The same rules, for `--recipient` | Give one or two different public keys |
| `❌ A sealed backup draws a password of its own: --sealed and --recipient go without --encrypt, --password-file or --password-stdin` | A sealed backup has no password to give | Drop the password options |
| `❌ --sealed reads the recipients from LIBREFOLIO_BACKUP_RECIPIENTS: give them there or with --recipient, not both` | `--sealed` and `--recipient` together | Keep one of the two |
| `❌ <path> already exists: a key file is never written over` | `backup keygen` never replaces a key: the old one may still open backups | Choose another file name, or move the old file away first if you are sure no backup needs it |

Opening one, with `--identity-file`: the command changes nothing and exits with `1`. The key file is read first, then the `.tar`.

| What you see | Why | What to do |
| --- | --- | --- |
| `(sealed_backup_needs_key)` | A `.tar` given without `--identity-file`, on the command line or in Settings › Administration › Backup | Give the key file, or [open it by hand](backup_sealed.md#sealed-by-hand) and restore `backup.lfbk` with its password |
| `❌ --identity-file opens a sealed backup (.tar) only: <path> is not one` | A `.zip` or an `.lfbk` given with `--identity-file` | Drop `--identity-file`: those archives open as usual |
| `❌ The key file cannot be read (sealed_identity_invalid)`, `Line 3 of the key file is not an age key`, `The key file holds no age key` | The file is not a private key: the public key alone, a key copied with a missing character, or a file the command may not read | Give the file `keygen` or `age-keygen` wrote, with its `AGE-SECRET-KEY-1…` line. Comments (`#`) and blank lines may stay |
| `❌ None of the keys given opens the password of this backup (sealed_no_identity)` | The backup was sealed for another key: an older one, before a [change of key](backup_sealed.md#sealed-rotation), or a hosting provider's | Compare its `recipients` (`tar xOf <archive>.tar manifest.json`) with the `# public key:` line of your key files, and give the matching one |
| `(sealed_tar_invalid)`, such as `The archive is cut short` or `The archive does not hold manifest.json, password.age and backup.lfbk, in this order` | Not the `.tar` LibreFolio wrote: cut short by a copy, rebuilt by hand with `tar cf`, or not a sealed backup | Copy the original again from where you keep it, or use another night's backup |
| `(sealed_manifest_invalid)`, such as `The manifest does not describe backup.lfbk: its size or SHA-256 differs` | `manifest.json` was changed, or `backup.lfbk` was | The copy is damaged: use another one |
| `(sealed_password_invalid)` | The key opened `password.age`, but what is inside is not a password LibreFolio writes | Not a LibreFolio backup, or changed: use another copy |
| `❌ The password does not open this backup (wrong_password)` | The key opened the password, but that password does not open `backup.lfbk`: the two files come from different backups, or one was changed | Use another copy, kept whole as LibreFolio wrote it |
| `(envelope_damaged)`, during the check or the restore | A byte of `backup.lfbk` was changed after the backup was made: the password was right | Use another copy: LibreFolio reads no part of a damaged `.lfbk` |

### 🔁 The Restore Does Not Go Through {: #restart-problems }

| What you see | Why | What to do |
| --- | --- | --- |
| `backup pending` says `The state of the restore cannot be read`, `(restore_state_unreadable: <reason>)` | `.restore/restore.json` cannot be used: its permissions (`io`), a link or a folder in its place (`not_a_file`), or content LibreFolio did not write (`invalid`). A restore may have stopped half way. No checked copy is removed meanwhile | For `io`, give `.restore/` back to the user that runs LibreFolio and look again. Otherwise stop LibreFolio and run `backup pending --recover previous`: the data of before comes back from `.restore/previous/`. Then start it, or restore a backup again: «An Unreadable Restore State» in [CLI Admin Tools](cli_tools.md) |
| `backup pending` ends with `(server_running)` | At the last start, another server process served the data directory: a worker started again on its own, or a second server | Restart the whole server, never one worker, and run one server per data directory |
| `backup pending` ends with `(instance_blocked)` | The hosting provider blocked the instance: a restore is never applied on a blocked instance | Nothing: the first start after the unblock applies it. `backup pending --cancel` drops it meanwhile |
| `backup pending` ends with `(other_data_directory)` | The server found its data directory under another path than the one the restore was confirmed for, such as a copy of the data directory | `backup pending --cancel`, or **Cancel the restore** in Settings › Administration › Backup, then restore the archive again: with `backup restore`, where the server runs |
| `backup pending` ends with `(backup_running)` | A backup was running at the last start | Nothing: the next start applies the restore |
| `backup pending` says the restore was rolled back, `(first_start_failed)` | The first start on the restored data did not complete | The data is as it was. The log of that start has the cause: fix it, then restore the archive again |
| … rolled back, `(swap_interrupted)` | The start that applied the restore was interrupted, and the next one undid it | Restore the archive again |
| … rolled back, `(swap_failed)` | The folders could not be moved into place | Make `sqlite/`, `custom-uploads/`, `broker_reports/` and `scenario_catalog/` real folders of the data directory, neither links nor separate mounts, then restore the archive again |
| … rolled back, `(stage_missing)` | The checked copy was gone or changed | Restore the archive again |
| A start stops, and its log says that another server applied the restore or serves the data directory | Two LibreFolio servers use the same data directory | Stop the other one, then start LibreFolio again: `backup pending` then tells whether the restore was kept |
| LibreFolio does not start, and its log has `The data directory is half restored` | Even putting the former data back failed, on a disk or permission error for instance | Fix the cause the log gives: every start tries again |
| `Failed to apply database migrations` after an unzip by hand | An archive from a newer LibreFolio, or a migration that fails: the log has the error | For a newer archive, `docker compose down`, then use the version that made it or a newer one ([Never Backwards](#never-backwards)) |

### 🖱️ What Settings › Administration › Backup Says {: #restore-settings-problems }

The window of the restart gives a reason in words where `backup pending` gives a code: the table says which one, and the row of that code in [The Restore Does Not Go Through](#restart-problems) says what to do. On the card, **Try again** reads the state of the restore again: to send an archive again, choose it again.

| What you see | Why | What to do |
| --- | --- | --- |
| After **Restore and restart**, the sign-in page, with no message | The restore worked: it ended every session. Only in the case of the next row does the sign-in page come although it did not | Sign in with an administrator of the backup, with the password the account had when the backup was made. If nobody remembers it: [After a Restore](#after-restore) |
| The sign-in page appeared, but once signed in the data is as before | The page could not read the outcome with its ticket (a reload of the page, more than an hour of waiting, or LibreFolio restarted from the command line rather than from the page), and LibreFolio runs without `JWT_SECRET` ([Keep Users Signed In After a Restart](index.md#session-persistence)): every start signs everyone out, so the page went to the sign-in page although the restore did not go through. The accounts and passwords of before still sign in | Open **Settings › Administration › Backup**: the card says *The last restore was rolled back on …*, or shows the restore waiting, with the reason; then see the row of that reason below. If the block page shows instead of the app, the hosting provider blocked the instance: the restore waits for the unblock |
| *LibreFolio has not come back yet. If nothing starts it again by itself, start it yourself: the restore is applied at that start.* | LibreFolio has not answered for a minute: nothing started it again, with no supervisor or one that starts it only after a failure ([Who Starts LibreFolio Again](backup_restore.md#supervisors)), or its start is slow | If it is stopped, start it: `docker compose up -d` with Docker, or [start the server](cli_tools.md#start-the-server) on a host installation. The page goes on by itself once LibreFolio answers. On an instance someone hosts for you, ask them |
| *LibreFolio has not stopped. If it does not restart by itself, restart it yourself: the restore is applied at that start.*, a minute after **Restore and restart**, with **Back to Backup** | The request did not stop the server: the restore still waits for the next start, and `backup pending` shows it waiting | Restart LibreFolio yourself: `docker compose restart librefolio` with Docker, or stop the whole server and [start it](cli_tools.md#start-the-server) again. Its start applies the restore, and the page goes on by itself. Or **Back to Backup**: the card shows the restore waiting, to restart it again (**Restart now and restore**) or cancel it (**Cancel the restore**). On an instance someone hosts for you, ask them |
| **The restore did not go through**, with *The data is as it was before: …* | The restore was rolled back: *the first start after it did not complete* (`first_start_failed`), *the start that applied it was interrupted* (`swap_interrupted`), *its folders could not be moved into place* (`swap_failed`) or *its checked copy was gone* (`stage_missing`) | What the row of that code says. **Back to Backup** returns to the card, which says when the last restore was rolled back, and why |
| **The restore did not go through**, with *LibreFolio restarted, but the restore was not applied.* and the reason | A start left the restore waiting: *At the last start a backup was running…* (`backup_running`), *It was confirmed for another data directory…* (`other_data_directory`) or *At the last start another LibreFolio process was serving the data…* (`server_running`) | What the row of that code says. **Back to Backup** shows the restore waiting, with **Restart now and restore** and **Cancel the restore** |
| **The restore did not go through**, with *LibreFolio restarted, but the restore was not applied. The hosting provider blocked this instance: the restore waits until it is unblocked.* | The start found the instance blocked by its hosting provider (`instance_blocked`): a restore is never applied on a blocked instance | Settle it with the hosting provider: the first start after the unblock applies the restore. **Back to Backup** leads to the block page. Whoever runs the server can drop the restore meanwhile, with `backup pending --cancel` |
| *The archive is larger than this LibreFolio accepts (500 MB).* | The installation limits the archives uploaded for a restore with `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` (`backup_too_large`) | On your own installation there is no limit unless someone set one: raise it, or set it to `0`, then restart ([The Upload Limit of a Restore](hosting_panel_backups.md#restore-upload-limit)). Or restore from the command line, which has no upload limit. On an instance someone hosts for you, ask them |
| *Unpacked, the archive is larger than this LibreFolio accepts for a restore.* | The sizes the archive's manifest declares add up to more than the installation accepts for a restore (`unpacked_too_large`): `LIBREFOLIO_BACKUP_MAX_RESTORE_MB`, or, while it is not set in a hosting provider's `managed` profile, 8 times the upload limit. The check refused the archive before unpacking anything | On your own installation there is no limit unless someone set one: raise it, set it to `0` or remove it, then restart ([The Upload Limit of a Restore](hosting_panel_backups.md#restore-upload-limit)). Or restore from the command line with `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` in front of `backup restore`. On an instance someone hosts for you, it is your hosting provider's limit: ask them |
| *LibreFolio cannot read its restore limit right now: try again later.* | `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` is not a whole number of megabytes (`backup_restore_unavailable`): no check starts, and the archive stays on the server. The log has an error, from the start already | Write a whole number of megabytes, `0` for no limit, or remove the variable, then restart; the **Security** tab of Settings › Administration names it (`backup.restore_limit`). Then choose the archive again. On an instance someone hosts for you, ask them |
| Sending stops with *A proxy in front of LibreFolio refused an archive this large: ask whoever runs it to accept larger uploads, or restore from the command line.*, or with *The server does not answer: check the connection and try again.* or *The server answered with an error: the server's log has the cause.*, and the log of LibreFolio has nothing about it | A proxy in front of LibreFolio refused the archive: Nginx takes only 1 MB by default. The first message comes from a proxy that answers *too large* (HTTP 413), the others from one that drops the connection or answers otherwise | Let the proxy take archives as large as yours, with `client_max_body_size` in Nginx ([The Upload Limit of a Restore](hosting_panel_backups.md#restore-upload-limit)), or restore from the command line |
| *Not enough free space on the server for this archive.* | The disk of the data directory, or a quota, is full (`backup_no_space`): while the archive was sent, and then nothing of it is kept (a network file system or a quota may report it only at the end of the file), or when **Restore and restart** confirmed the restore, and then nothing is confirmed and the checked copy stays. The log of a confirmation has `A restore could not be confirmed: not enough free space` | Free some space on the disk of the data directory, then choose the archive again. After a confirmation, **Try again**: the report comes back, and **Restore and restart** confirms again |
| *Not enough free space on the server to check the archive.* | The disk of the data directory, or a quota, is full when the check starts, and then the archive stays on the server, or while the check makes its copy (`no_space`) | Free some space, as much as the `no_space` row of [The Check Refuses the Archive](#check-refused) says, then choose the archive again |
| *The copy could not be written: the server's log has the cause.* | The check could not start, or could not write its copy, for another reason than space (`stage_failed`): the owner or the permissions of a folder of `.restore/`, a read-only disk, a disk error. At the start, the log has `A check of a backup archive could not start`, with the error and the system's reason | Fix what the log line names, such as giving `.restore/` back to the user that runs LibreFolio, then choose the archive again |
| *Not enough free space on the server for the backup.*, on the card **Back up the instance** | The disk of the data directory, or a quota, is full (`backup_no_space`), as the backup started or while it ran: the backup is built in `backups/`, on that disk | Free some space on that disk, then **Try again**. How much a backup needs: «Create an Archive» in [CLI Admin Tools](cli_tools.md) |
| *The restore could not be confirmed: the server's log has the cause. Nothing changed.*, after **Restore and restart** | The confirmation could not be written, for another reason than space (`restore_confirm_failed`): the owner or the permissions of `.restore/`, a read-only disk, a disk error. The log has `A restore could not be confirmed`, with the error and the system's reason. Nothing is confirmed, and the checked copy stays | Fix what the log line names, such as giving `.restore/` back to the user that runs LibreFolio, then **Try again**: the report comes back, and **Restore and restart** confirms again |
| *The restore could not be cancelled: the server's log has the cause. It still waits for the next start.*, after **Cancel the restore**: the card still shows the restore waiting, with **Restart now and restore** and **Cancel the restore** | The restore waiting could not be dropped (`restore_cancel_failed`): its state in `.restore/` could not be locked or removed, for its owner or permissions, a read-only disk or a disk error. The log has `A pending restore could not be cancelled`, with the error and the system's reason. A copy that cannot be removed once the restore is dropped is no such failure: the restore is cancelled, and the log has the warning `The copy of a cancelled restore could not be removed: it goes when its check expires` | Fix what the log line names, then **Cancel the restore** again, on the same card: until it is cancelled, the next start of LibreFolio applies the restore. A copy left goes at the first start of LibreFolio once its check is 24 hours old |
| *LibreFolio could not be restarted: the server's log has the cause. The restore still waits for the next start.*, after **Restore and restart** or **Restart now and restore** | LibreFolio was not stopped: the ticket with which the page reads the outcome could not be written (`restore_restart_failed`), on a full disk or for the owner or the permissions of `.restore/`. The log has `The ticket of the restore's outcome could not be written: no restart`. The restore is confirmed, and waits | Fix what the log line names, then **Restart now and restore**, which the card shows with the restore waiting. Or restart LibreFolio yourself, `docker compose restart librefolio` with Docker: its start applies the restore |
| *The state of the restore cannot be read: the server's log has the cause. A restore may still wait for the next start.* | LibreFolio cannot read the restore's state in `.restore/` (`restore_state_unreadable`): its owner or its permissions, such as files written by `root`, or a disk error. Whether a restore waits is not known: confirming another restore is refused too, and a start that cannot read the state leaves it as it is and applies nothing | Give `.restore/` and its files back to the user that runs LibreFolio, readable by it, then **Try again**. With Docker, each start of the container gives the data directory back to that user before LibreFolio reads the state, so a restore that waits is applied at that start; permissions changed with `chmod` stay as they are. `backup pending` says the same, with the system's reason |
| The card refuses the archive, such as *This file is not a LibreFolio backup.*, *The archive is damaged.* or *The secure backup is damaged or was changed: it cannot be opened.* | The check refused it, as `backup restore` does | See its code in [The Check Refuses the Archive](#check-refused) |
| The card asks for the password of a secure backup again: *Wrong password, or the file was changed: type the password again.* | The password does not open the backup (`wrong_password`) | Type it again: the archive stays on the server and is not sent again. If the password is right, the file was changed: **Cancel**, then choose a good copy of it with **Choose an archive…** |

### 🔑 After a Restore {: #after-restore }

| What happens | What to do |
| --- | --- |
| Nobody remembers the password an administrator had in the backup | Whoever runs the server sets a new one with `user reset`, or creates a reset link with `user reset-link` ([Reset a Password or Lock an Account](cli_tools.md#reset-a-password-or-lock-an-account)) |
| The sign-in page answers that an account is disabled: it was waiting for its email verification | An administrator clicks **Reactivate** on its row ([What Each Action Does](users.md#actions)), or deletes it so that its owner signs up again ([Delete an Account](users.md#delete)) |
| A link sent before the restore no longer works | Send a new invitation or password-reset link ([Users & Invitations](users.md)) |
| A secret plugin setting is reported as set but unreadable, as the report of the check announced (*… cannot be read with this instance's key: enter them again after the restore.*) | The backup carried no key that reads it: a clear backup, or a secure one whose instance had a key set in its environment, or could not use its own. If you still have the old key, put it back first, before anyone enters a secret again; only otherwise enter the setting again in **Settings › Plugins**, where each user enters their own ([What Follows](backup_restore.md#what-follows)). If the start log says that this installation's own key cannot be used, fix that first («Startup Checks» in [Environment Variables](configuration.md)) |
| After a move, no email goes out | Set the email variables on this installation, then restart ([Email](email.md)) |

---

## 🔗 Related

- 📄 **[Backup, Restore and Moving Your Instance](backup_restore.md)** — What a Backup Holds, Make a Backup, Secure Backups, …
- 📄 **[Backups: Sealed Backups](backup_sealed.md)** — Sealed Backups: a Key Instead of a Password
