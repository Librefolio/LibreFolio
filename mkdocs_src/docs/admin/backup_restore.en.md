# 💾 Backup, Restore and Moving Your Instance

A backup is one archive with your whole LibreFolio in it: the database and the files of every user, in a plain zip or, for a [secure backup](#secure), encrypted with a password you choose. This page tells the whole story: what the archive holds, how to make and check one, how to protect it with a password, how to restore it, and how to move LibreFolio from an instance someone hosts for you to your own server, or the other way round. Every option and message of the commands is in «Back Up the Instance», in [CLI Admin Tools](cli_tools.md).

!!! tip "🗓️ Make one before every update"

    LibreFolio never takes a database back to an older version. A backup made before an update is your way back to the version you had: see [Updating LibreFolio](../user/installation.md#updating).

!!! info "📚 This guide is in several pages"

    Besides this page: [Backups: Sealed Backups](backup_sealed.md), [Backups: Moving and Troubleshooting](backup_moving.md).

---

## 📦 What a Backup Holds {: #contents }

The archive is a zip with the layout of the [data directory](filesystem.md): unpacked into an empty data directory, it is your instance again. A [secure backup](#secure) is the same zip, encrypted with a password into an `.lfbk` file, and a [sealed backup](backup_sealed.md#sealed) is a secure backup whose password only a private key of yours opens, in a `.tar`.

| In the archive | What it is |
| --- | --- |
| `sqlite/app.db` | The database: users, brokers, transactions, assets, prices, exchange rates and settings. A consistent copy, made while LibreFolio keeps running |
| `custom-uploads/` | The files uploaded in the app |
| `broker_reports/` | The broker reports |
| `scenario_catalog/` | Your own stress scenarios, if you added any |
| `secrets/instance.key` | Only in a [secure backup](#secure), and only when LibreFolio generated the instance key: the key that encrypted the saved keys of the data providers, so that they travel with the data. A restore only reads it: the installation that receives the backup keeps its own key |
| `manifest.json` | The description of the archive: the LibreFolio version that made it and when, the migration revision of the database, its rows per table, the ledger's control totals (the cash of every broker in each currency and the quantity of every position), the size and SHA-256 checksum of every file, and whether the archive carries the instance key |

Never in the archive:

- 🔑 `secrets/`, which holds the instance key: a [secure backup](#secure) carries only the key LibreFolio generated, `secrets/instance.key`, never a key you set yourself with `LIBREFOLIO_INSTANCE_KEY` or `LIBREFOLIO_INSTANCE_KEY_FILE`. See «The Instance Key» in [Environment Variables](configuration.md);
- 📝 `logs/`, and `scheduler_state.json`, the last run of the scheduled syncs;
- 💾 `backups/`, where LibreFolio [keeps the backups it makes](#kept-backups), and `.restore/`, the work folder of a restore;
- ⚙️ the configuration: `.env` and the environment variables, the [email](email.md) settings included, which LibreFolio keeps only in the environment.

### 🧭 What Follows {: #what-follows }

- 🔒 **Keep it private.** A clear archive holds every user's data and is not encrypted: keep it, and every copy, as private as the server itself. A [secure](#secure) one opens only with its password: keep the password apart from it.
- 🗝️ **Saved secrets and the instance key.** What LibreFolio encrypted with the instance key, such as the API key of a data source saved in the app, can be read only with that key.
    - A [secure backup](#secure) carries the key LibreFolio generated: its restore re-encrypts those secrets with the key of the installation that receives it, and there is nothing to do.
    - A clear backup leaves the key out, and so does a [sealed](backup_sealed.md#sealed) one, always, and a secure one whose key came from the environment (`LIBREFOLIO_INSTANCE_KEY`, `LIBREFOLIO_INSTANCE_KEY_FILE`) or could not be used. On an installation with another key, LibreFolio keeps those secrets, reports them as unreadable and never uses a wrong value: **Settings › Plugins** says under each one *Saved, but this instance's key cannot read it: enter it again.* If you still have the old key, put it back first, before anyone enters a secret again: stop LibreFolio, put your copy of `secrets/instance.key` in place of the generated one, or set the old value of the variable, and start it again («The Instance Key» in [Environment Variables](configuration.md)). An installation that keeps its own key, or one whose own secrets are already under its key, takes the old key at the restore instead: restore from the command line with `--instance-key-file` and your copy of the old key, and the check re-encrypts those secrets with this installation's key («The Instance Key of Another Installation» in [CLI Admin Tools](cli_tools.md)). Enter the secrets again only if the old key is lost: a secret entered under the new key would become unreadable once the old one is back.
    - For the settings of the whole instance, every start also logs the error *Stored plugin secrets that the instance key cannot read: …* with their count, until they are entered again or the old key is back. No plugin shipped with LibreFolio keeps one today.
- ⚙️ **Bring your configuration.** Keep a copy of your `.env` with the archives: on another installation, set again the options you need, the email ones included ([Where the Configuration Lives](email.md#where-it-lives)).
- 🏠 **Any installation can take it**, if it runs the same version of LibreFolio or a newer one, whoever made the archive: Settings or the command line.

---

## ⬇️ Make a Backup {: #create }

Three ways give the same archive:

- **Settings › Administration › Backup**, in the app: the archive downloads to your computer. For administrators.
- **The command line**, on the server: `backup create`.

From Settings and from the command line, the backup can also be [secure](#secure): the same zip, encrypted with a password you choose. From the command line, it can also be [sealed](backup_sealed.md#sealed): encrypted with a random password that only a private key of yours opens, for backups made without anyone at the keyboard.

In every case LibreFolio keeps working during the backup, and one backup runs at a time, whoever started it.

### 🖱️ From Settings › Administration › Backup {: #settings-backup }

1. Open **Settings › Administration › Backup**: only administrators have this tab.
2. In **Back up the instance**, choose the kind of backup:
    - **Clear**, the choice the card starts with: *A plain .zip: whoever has the file sees all the data, and on another instance the keys of the data providers must be entered again.*
    - **Secure**: *An .lfbk encrypted with a password you choose: only that password opens it, and a lost password cannot be recovered. It also carries the keys of the data providers.* See [Secure Backups](#secure).
3. For a secure backup, type its password in **Password of the backup**, then again in **The same password again**. The password follows the rules the server gives, those of an account's password with at least 12 characters: the meter under the first field lists them as you type (*At least 12 characters*, *One uppercase letter*, *One lowercase letter*, *One number*, *One special character*) and shows how strong the password is. While the two fields differ, *The two passwords differ.* shows under the second one, and **Create backup** stays disabled until both are right.
4. Click **Create backup**. The password fields empty at once. The card follows the backup on the server, phase by phase; a secure backup ends with *Encrypting with your password*.
5. When it reads **Backup ready**, click **Download**. Your browser saves the archive, named after the moment the backup started, in UTC, such as `librefolio-backup-20261015-121500.zip`, or `librefolio-backup-20261015-121500.lfbk` for a secure backup, which the card marks *Encrypted with your password: keep it safe, LibreFolio cannot recover it.* A copy stays on the server, in the list of [Backups Kept on the Server](#kept-backups): download it from there later, too.

Good to know:

- 🔑 **Keep the password of a secure backup.** LibreFolio keeps no copy of it, and without it nobody opens the archive, you included: keep it in a password manager, apart from the archive.
- 💾 The archive stays on the server until you delete it, or until the [automatic clean-up](#backup-cleanup) you set removes it. A copy on the same disk as your data is not a real backup: download it and store it elsewhere ([Keep Copies Off the Server](#keep-copies)). **Delete from the server** removes it at once, and **Create a new backup** starts another one.
- ⚠️ **The backup is complete, with warnings** means that the database failed its integrity check or has broken references, and was archived as it is, or that some files were left out, or, for a secure backup, that the instance key could not be used and was left out ([Making a Secure Backup](backup_moving.md#secure-problems)). The archive is written all the same: read the warnings before you rely on it.
- 🚦 While another backup runs, started from the app or the command line, the card says so: try again when it ends. One started from this tab, or another tab of the app, whose answer never arrived (the connection dropped while it started) is not lost: the next **Create backup** finds it running, and the card follows it, then offers its download, as if it had just started it. This holds for a clear backup only: a secure one is never followed this way, because only its own password opens its archive, and a followed backup that turns out to be secure is not offered, unless the card had started it itself; in both cases the card says that another backup runs. A card that already offers an archive keeps offering it, and only says that another backup runs. One started from the command line is not followed: its archive goes elsewhere. The card never says which backup runs; the browser's console does (its id and where it was started), should you need to find it.

### ⌨️ From the Command Line {: #command-line }

```bash
# Docker: the archive appears in its own folder of ./LibreFolio-data/backups/ on the host
docker compose exec librefolio python dev.py backup create

# Host installation: the archive goes into its own folder of backups/ in the data directory
pipenv run ./dev.py backup create

# A secure backup (.lfbk): the password is asked twice
docker compose exec librefolio python dev.py backup create --encrypt
```

- 🗃️ Without `--output`, the archive stays on the server, in its own folder of `backups/` ([Backups Kept on the Server](#kept-backups)), and the command prints its path and its `SHA-256:`.
- 📁 `--output` (`-o`) copies the archive into another folder that already exists, or under a name of your own, and prints its `SHA-256:` too; nothing is kept in `backups/` then. With Docker, the path is inside the container: use a folder mounted from the host.
- 🔒 Only the owner of the archive can read it (`0600`): with Docker, that is the container's user.
- 🔐 `--encrypt` makes a [secure backup](#secure), `librefolio-backup-<date>-<time>.lfbk`, and asks its password twice at the terminal. Instead of typing it, give it with `--password-file FILE`, a file that holds only the password (the line breaks at its end do not count), such as a Docker secret, or with `--password-stdin`, one line of the standard input, from a pipe: at a terminal, the command asks it instead, without showing it, as without the option. Either one makes the backup secure by itself, `--encrypt` or not; the two cannot go together.
- 🙈 A password is never an argument of the command: every user of the server can read the commands that run (`ps`), and the shell keeps them in its history. There is no `--password` option.
- 📏 The password follows the rules of Settings › Administration › Backup: at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol. One that misses some stops the command before anything is written, with the rules it misses: `❌ The password of a backup needs at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: min_length, digit)`.
- 🤖 Without a terminal, from cron or a script, `--encrypt` alone stops with `❌ A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal (password_required)`.
- 📖 Every option, warning and error: «Back Up the Instance» and «Back Up with Docker» in [CLI Admin Tools](cli_tools.md).

??? example "🐳 The password of the backups as a Docker secret"

    1. Write the password alone in a file next to `docker-compose.yml`, such as `backup_password.txt`, never in `LibreFolio-data/`: whoever had the data would have its password too. Keep the file private, `chmod 600 backup_password.txt`, and a copy of the password elsewhere: a lost password cannot be recovered.
    2. Add the marked lines to `docker-compose.yml`, and keep the rest of the service as it is:

        ```yaml
        services:
          librefolio:
            secrets:                              # added
              - backup_password                   # added
        secrets:                                  # added
          backup_password:                        # added
            file: ./backup_password.txt           # added
        ```

        If the file already has `secrets:` lists, such as for `JWT_SECRET_FILE` («Secrets in Files» in [Environment Variables](configuration.md)), add the lines to them. Then run `docker compose up -d`, which recreates the container with the secret.

    3. Make the backup with the path where Docker puts the secret in the container:

        ```bash
        docker compose exec librefolio python dev.py backup create --password-file /run/secrets/backup_password
        ```

### 🗃️ Backups Kept on the Server {: #kept-backups }

A backup made from the app or the command line is no longer deleted after an hour: it stays on the server until you delete it, or until the [automatic clean-up](#backup-cleanup) removes it. Each one has a folder of its own in the `backups/` folder of the data directory, named after the moment it was made (in UTC), where it came from (`ui` for the app, `cli` for the command line) and a short code that tells two backups of the same second apart:

```text
backups/librefolio-backup-20261015-121500-ui-1a2b3c4d/librefolio-backup-20261015-121500.zip
```

The archive inside keeps its usual name, `.zip`, `.lfbk` or `.tar`. `backups/.jobs/` holds only a backup in progress or one that failed, which goes after an hour.

**Refresh**, at the top of the list of backups, reads it again: a backup made from the command line shows only then.

**Settings › Administration › Backup**, under *Backups on this server*, lists every backup kept. **Files**, in its **Backups** tab, shows the same list; only administrators see either. For each backup it gives:

- 📅 the date and time it was made, and where it came from: the app or the command line;
- 🔐 its type: plain, with a password ([secure](#secure)) or [sealed](backup_sealed.md#sealed);
- 📏 its size, and its SHA-256: click it to copy the whole checksum, and compare it with the one of the file you download;
- ⬇️ **Download** and 🗑️ **Delete**, which removes the backup from the server at once.

!!! warning "💽 Download it and store it elsewhere"

    A backup that stays on the same disk as your data is not a real backup: when the disk is lost, the data and its backups go together. Download the archive and keep it on another disk, a NAS or off-site ([Keep Copies Off the Server](#keep-copies)).

The list shows only the backups made by this version of LibreFolio. The loose `librefolio-backup-*.zip` files that earlier versions left in `backups/` are not listed and are never removed by LibreFolio: delete them yourself when you no longer need them.

### 🧹 Automatic Clean-up {: #backup-cleanup }

Kept backups pile up, and they live on the disk of your data. In the closed **Automatic clean-up** panel of the same **Backups on this server** section, in **Settings › Administration › Backup** and in **Files › Backups**, you set two limits, both optional:

| Limit | What it does | Off |
| --- | --- | --- |
| Total size, in MB | When the kept backups weigh more, the oldest are deleted until the rest fits | `0` |
| Maximum age, in days | A backup older than this is deleted | `0` |

- 🛡️ **The latest backup is always kept**, whatever the limits say: an instance never ends up with none.
- ⏰ The clean-up runs after each backup and when LibreFolio starts, at most once an hour: a change you save applies within the hour.
- 🏠 **Self-hosted:** both limits are off until you set them.
- 🔍 Only the backups of the list are cleaned. Older loose archives in `backups/`, a backup in progress and a failed one are never touched by it.
- ⌨️ The command line leaves its backups in the same place and the same limits apply: see [Where the Backups Stay](cli_backup.md#backup-kept).

### 📊 The Space Bar {: #space-used }

**Files** shows administrators a bar, **Space used**, above its tabs, whichever tab is open: how much room your instance takes. It reads again when you click **Refresh** and whenever the list of kept backups changes, so a backup made or deleted shows at once. Its legend gives the size of each part:

| Part | What it counts |
| --- | --- |
| **Database** | The database and the files it keeps beside it |
| **Uploaded files** | The files uploaded in the app, such as those of the **Files** page |
| **Broker reports** | The statements uploaded to import transactions |
| **Backups** | Everything in `backups/`: the [backups kept on the server](#kept-backups), a backup in progress and a failed one |
| **Restore under way** | A [restore](#restore) not ended or discarded yet: the uploaded archive and its opened version |
| **Other LibreFolio files** | The rest of the data directory: logs, state and the like |

The bar has three looks, depending on whether a limit is set and whether the disk is known:

- 💽 **No limit** (the default on a self-hosted install): the bar is the whole disk of your data. LibreFolio's parts are coloured, **Other on the disk** is grey, and the **Free** space is left empty. The line under the bar says how much LibreFolio uses of how large a disk.
- 📏 **With a limit**: the bar is the limit, and LibreFolio's parts fill it as far as the data goes. The line under the bar reads *used of limit*.
- 📁 **No limit and the disk unknown**: LibreFolio cannot ask the disk, so the bar is LibreFolio's own folder, split into its parts, with no free space.

**Set the limit** in the closed **Advanced** panel under the same bar, in the **LibreFolio total space (MB)** field: a whole number of megabytes, `0` for no limit, then **Save**; a green notice confirms it. It is the most space LibreFolio may take in all. It is also the *Space limit* [global setting](settings.md), which is not shown in the Administration tab: this field is the place to change it.

- 🚧 **Past the limit**, LibreFolio refuses what would add data: an uploaded file, a broker report, a backup you start by hand (after trying the [automatic clean-up](#backup-cleanup) first) and a [restore](#restore) whose result would pass it. The message says to raise the total space to at least a size and, when the disk itself lacks the room, how much more it needs free. Never stopped: your transactions, prices and database, the backups of a hosting panel and of the command line (the clean-up follows them), and an existing restore already confirmed. The limit deletes nothing by itself.
- ⚠️ **Over the limit**, the bar warns that the limit is exceeded and suggests deleting backups or files, or raising the limit. The bar is then your data, so that no part is left out: a tick named *Limit 20 MB* shows where the limit falls, and red stripes after it show how far past it you are.
- 💬 **A refusal is said where you are**: in the upload or import window, or on the backup card. An administrator gets **Open the settings**, which opens **Files** with the **Advanced** panel open; a user reads how much to free, or to ask an administrator. With a limit set by whoever hosts the instance, the message says to ask them.
- 🔒 **Set in the server's configuration**: when `LIBREFOLIO_STORAGE_LIMIT_MB` is set, its value is the limit, the field is greyed out and a note says it is set by whoever hosts the instance. See [Environment Variables](configuration.md). A value LibreFolio cannot use, one that is not a whole number, is ignored, and the field works as above.
- 🧹 **The clean-up and the bar work together.** Backups are usually the part that grows: the [automatic clean-up](#backup-cleanup) keeps them in check, and every backup you delete in **Settings › Administration › Backup** or in **Files › Backups** shortens **Backups** in the bar. When you are near the limit, start there.

### 🗄️ Keep Copies Off the Server {: #keep-copies }

`backups/` is in the data directory, on the same disk as the data: a backup kept there does not survive the loss of that disk. An archive downloaded from Settings is already off the server. From the command line, write the archives to another disk, a NAS or off-site with `--output`, on a schedule.

A `cron` line for a host installation, every night at 03:30 (`crontab -e`, as the user that runs LibreFolio):

```text
30 3 * * * cd /path/to/LibreFolio && pipenv run ./dev.py backup create --output /mnt/nas/librefolio/
```

With Docker, add `-T`, as cron gives the command no terminal. The archive lands in its own folder of `LibreFolio-data/backups/`, where the [automatic clean-up](#backup-cleanup), once you set it, keeps the disk from filling: copy it elsewhere with your usual tool.

```text
30 3 * * * cd /path/to/librefolio && docker compose exec -T librefolio python dev.py backup create
```

For [secure](#secure) archives, add `--password-file` with the path of a file that holds the password, as cron has no terminal to ask on; with Docker, the secret of the example above:

```text
30 3 * * * cd /path/to/librefolio && docker compose exec -T librefolio python dev.py backup create --password-file /run/secrets/backup_password
```

- 📁 The folder given to `--output` must exist when the command runs, so mount the NAS first: a path that is not an existing folder becomes the name of the archive itself.
- 🔢 The command prints what it did, and exits with `1` when the archive is not where you asked: keep that output, or have cron mail it to you.
- 🧭 cron runs commands with a short `PATH`: if it does not find `pipenv` or `docker`, write the full path, which `command -v pipenv` prints.
- 🗑️ LibreFolio deletes none of these archives: remove the old ones yourself. Keep several, and the last one made before each update.
- 🔑 Keep a copy of `.env` as well, as private as the archives: no archive holds it. Keep one of `secrets/` too, unless your archives are secure: a clear or [sealed](backup_sealed.md#sealed) archive leaves the instance key out, a secure one carries the key LibreFolio generated.
- 🔏 For nightly archives that the server itself cannot open, without a password file on its disk, see [Every Night with cron](backup_sealed.md#sealed-cron), in Sealed Backups.

### 🧰 Backups with restic or Backrest {: #restic }

LibreFolio writes the archive; a backup tool can then send it off-site and keep a history of it. [restic](https://restic.net/) sends a folder to an S3 bucket, Backblaze B2, a server over SFTP and other places, encrypted, and forgets the old copies by a rule you give it. [Backrest](https://github.com/garethgeorge/backrest) is a web interface for restic, with its own scheduler. LibreFolio needs neither: they only read the folder its archives are written to.

A nightly recipe for a host installation, with restic's variables in a private file (`chmod 600`):

```bash
# /etc/librefolio-restic.env: where the copies go, and the file with restic's password
RESTIC_REPOSITORY=sftp:backup@nas.example:/srv/restic/librefolio
RESTIC_PASSWORD_FILE=/root/.restic-librefolio-password
```

```text
30 3 * * * cd /path/to/LibreFolio && pipenv run ./dev.py backup create --output /var/backups/librefolio/ && . /etc/librefolio-restic.env && restic backup /var/backups/librefolio/ && restic forget --keep-daily 7 --keep-weekly 4 --prune && find /var/backups/librefolio/ -name 'librefolio-backup-*' -mtime +2 -delete
```

The line makes the archive, sends the folder, keeps seven daily and four weekly copies in the repository, and removes the local archives older than two days. With Docker, make the archive with the command of [Keep Copies Off the Server](#keep-copies) and give restic the host folder `LibreFolio-data/backups/`. With Backrest, add a plan on that same folder, with its schedule and its retention, and leave `backup create` in cron.

- 🔐 **restic's password is a key to all your data.** restic encrypts the repository with it, but anyone who has it reads every copy in it: keep it as private as the password of a [secure backup](#secure), and a copy of it elsewhere. Lost, the repository cannot be read.
- 🔑 **No public key.** restic needs its password to write as well as to read, so the server that sends the copies can also read them. If that matters to you, send [sealed backups](backup_sealed.md#sealed-cron) (`--sealed`): restic then stores files that only your private key opens, and neither the server nor restic's password reads them. [Secure backups](#secure) (`--password-file`) work too, but their password then sits in a file on the same server.
- 📦 **Little to deduplicate.** Each archive is compressed, and a secure one is encrypted: two nights look different to restic, which stores each archive almost whole. Plan the repository's space for the copies you keep.
- 🧪 **Try a restore before you need one.** `restic restore latest --target /tmp/librefolio-check`, then check the archive with [`backup restore --dry-run`](#check).

---

## 🔐 Secure Backups {: #secure }

A secure backup is the archive of a clear backup, encrypted with a password you choose, in a file of LibreFolio's own: `.lfbk`. Make one from [Settings › Administration › Backup](#settings-backup) or with `backup create --encrypt` on the [command line](#command-line); every check and restore of this page takes it, once given its password.

- 🛡️ **What it protects: the file at rest.** A lost disk, a stolen laptop, a copy on a cloud drive or a NAS: without the password, nothing in it can be read, neither the data nor the names of the files. A file changed or cut short is detected when it is opened, and refused.
- 👁️ **What it does not protect.** Whoever knows the password reads everything: the data of every user, and the keys of the data providers. Give it only to whoever may restore the backup, and never keep it with the file.
- 🗝️ **What it carries.** Besides the data, the instance key, when LibreFolio generated it (`secrets/instance.key`): the saved keys of the data providers travel with the backup, and its restore re-encrypts them with the key of the installation that receives it, which keeps its own. A key you set yourself, with `LIBREFOLIO_INSTANCE_KEY` or `LIBREFOLIO_INSTANCE_KEY_FILE`, never leaves: whoever set it keeps it.
- 🆘 **A lost password cannot be recovered.** LibreFolio keeps no copy of it, and nothing else opens the file.
- ⏳ **Slow to guess.** The key of the file comes from the password through scrypt, which takes 32 MiB of memory and about a tenth of a second for each try: nothing for one backup, light enough for a small server, but slow for whoever tries passwords one after another. Hence the rules: at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol.
- 💽 **On the server, while it is made,** the clear archive is written first, in the work folder of the backup inside `backups/`, which only the server's user can open; it is removed as soon as the `.lfbk` is written, and when the backup fails. A check decrypts the backup the same way, in a private folder of the data directory, and removes the decrypted archive once it has used it. A run killed outright, by a power cut or `kill -9`, cannot clean up: the next start of LibreFolio removes what it left in clear, and a backup cut short that way must be made again. The folder of a `backup inspect` killed that way goes once it is an hour old.

The design, for developers: [Secure Backups (`.lfbk`)](../developer/architecture/security.md#secure-backups).

---

## 🔎 Check a Backup {: #check }

Two commands check an archive and change nothing. With Docker, give the path inside the container: an archive in `LibreFolio-data/backups/` is in `/app/backend/data/prod-docker/backups/` there. A backup LibreFolio [keeps](#kept-backups) is in a folder of its own, such as `/app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/`.

```bash
# Is the archive whole, and what does it hold?
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# Can this installation restore it? A restore tried on a copy
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip --dry-run

# A secure backup: the same commands ask its password first
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.lfbk
```

On a host installation, run `pipenv run ./dev.py backup …` with the path of the archive on the host.

| | `backup inspect` | `backup restore --dry-run` |
| --- | --- | --- |
| It answers | Whether the archive is whole: the size and SHA-256 checksum of every entry, compared with the manifest | Whether this installation can restore it: the archive unpacked into a copy, brought up to date and checked |
| It shows | Who made the archive and when, the revision of its database, its rows and tables, its files, and whether the instance key is included | The same, plus the migrations a restore would apply, the ledger's control totals of the copy compared with those the archive recorded, the saved keys of the data providers re-encrypted with this installation's key or to enter again, and the administrators you would sign in with |
| It needs | Any LibreFolio, its server running or stopped: no data directory, but for a secure backup, which it decrypts there | The installation that would receive the archive, whose server may keep running, and free space in its data directory: the archive unpacked, plus twice its database, plus 64 MB |
| It ends with | `✅ Every entry matches the manifest` | `✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed.` |

- 🔐 **A secure backup** (`.lfbk`): both commands ask its password first, typed at the terminal or given with `--password-file FILE` or `--password-stdin`, as for `backup create`. They decrypt it into a private folder of the data directory, which only the server's user can open, and remove it at the end: the disk there needs room for the decrypted archive too, about the size of the `.lfbk`. What a command killed outright, by a power cut or `kill -9`, leaves in clear goes at the next start of LibreFolio: the decrypted archive of `--dry-run` at once, the folder of `inspect` once it is an hour old, which the next `inspect` also removes. Their report adds `Secure backup: decrypted with its password`. A wrong password stops them with `❌ The password does not open this backup (wrong_password)`. A `.zip` ignores the two password options.
- 🗝️ `--dry-run` also says what becomes of the saved keys of the data providers, for any archive: `Saved provider keys: 2 re-encrypted with this instance's key` when the backup carries the key that encrypted them, `⚠️ 1 saved provider key cannot be read with this instance's key: enter it again after the restore` for those it cannot read ([What Follows](#what-follows)).
- 🔁 Run `inspect` now and then on the copies you keep, and `--dry-run` before a move, on the installation that will receive the archive.
- 🖱️ **Restore an archive**, in Settings › Administration › Backup, runs the same check as `--dry-run` on an archive from your computer: read its report, then **Drop this archive**, and nothing changes ([Restore from Settings › Administration › Backup](#restore-settings)).
- ❌ A refusal ends with a code in parentheses: see [When Something Goes Wrong](backup_moving.md#troubleshooting). The full lists are in «Check an Archive» and «Try a Restore on a Copy», in [CLI Admin Tools](cli_tools.md).

---

## ♻️ Restore on This Installation {: #restore }

A restore replaces the data of the installation with the archive's: the database and the files, for every user. Two ways lead to it: **Settings › Administration › Backup**, in the app, for administrators, and `backup restore`, on the command line of the server. Both check the archive on a copy first and change nothing until you confirm: the next start of LibreFolio then applies it. From Settings › Administration › Backup, LibreFolio stops as soon as you confirm, for that start; on the command line, you restart it when it suits you. On an instance someone hosts for you, the command line is on their server: as one of its administrators, use Settings › Administration › Backup, or ask them.

### 🖱️ Restore from Settings › Administration › Backup {: #restore-settings }

1. **Choose the archive.** In **Settings › Administration › Backup**, under **Back up the instance**, the card **Restore an archive** reminds you that a restore replaces the data of every user: if you may want the current data back, [make a backup](#settings-backup) first. Click **Choose an archive…** and pick a backup archive made by LibreFolio here or on another installation: a `.zip`, or a secure `.lfbk`. A `.zip` is sent to the server at once, with a progress bar: **Stop sending** stops it, and nothing is kept.
    Or take a backup the server keeps: **Restore** on its row in the list of [backups kept on the server](#kept-backups), here or in **Files › Backups**, asks first, then the server takes that backup as the archive, with no download and no upload, and the card goes on from the next step. A sealed backup of a hosting panel opens only with its recipients' private key: it is not restored here.
2. **Type its password**, for a secure backup. The card asks for it before anything is sent: *A secure backup: type the password it was made with.* Type it in **Password of the backup** and click **Check the backup**: the archive is sent, with the same progress bar, and the password goes with the request that starts the check, which tries it at once. A wrong password brings the form back, with *Wrong password, or the file was changed: type the password again.* The archive stays on the server, and the next try does not send it again. **Cancel** forgets the file.
3. **Let it be checked.** The server checks the archive on a copy, as `backup restore --dry-run` does ([Check a Backup](#check)): *Decrypting the backup*, for a secure backup only, *Checking the archive*, *Unpacking it on a copy*, *Updating the copy's database*, *Verifying the copy*. Nothing changes until you confirm. **Stop the check** drops it: a check still running is dropped as soon as it ends.
4. **Read the report.** It opens in a window, **What this restore would do**; once closed, **Read the report** opens it again. It gives:
    - who made the archive, with which version of LibreFolio, and when;
    - its database: at the version of this LibreFolio, or brought to it on the copy, with the migrations listed, and the fixes applied to the copy;
    - the files and their size, the size of the database, and the tables whose rows the update changed; and a bar of what the backup holds: the database, the uploaded files, the broker reports and the other files;
    - whether the backup carries the key of the instance it comes from: either way, this LibreFolio keeps its own;
    - the saved keys of the data providers: how many are re-encrypted with this LibreFolio's key, such as *2 saved keys of data providers are re-encrypted with this instance's key.*, and how many it cannot read, to enter again after the restore, such as *1 saved key of a data provider cannot be read with this instance's key: enter it again after the restore.* ([What Follows](#what-follows));
    - the ledger totals: the same as when the backup was made, different on the lines listed ([how to read them](backup_moving.md#check-refused)), not recorded, recorded by another version of the method, or unreadable;
    - the administrators of the backup, with *After the restore you sign in with one of them, with the password of then; every session open now ends.*
    - each administrator with the picture of their account in the backup, and **Check a password before you restore**: choose one, type their password and click **Verify**: *With this password you will sign in after the restore.*, or *This is not their password.* The password is checked against the backup only, and never kept, written to the log or sent back;
    - *Invitations and links sent before the restore will have expired: send them again if needed.*
    - the warnings, which let the restore go on, and the blockers, which forbid it: a backup without an active administrator, and a restore that would pass the [space limit](#space-used), with the size to raise it to; such a check gives its room back at once, and its report stays on screen until you close it;
    - until when the uploaded archive is kept: 24 hours after the check.

    **Drop this archive** drops the check and its copy: nothing is restored. **I'll decide later** closes the window and keeps the check: the card then reads *A restore waits for your decision until …*, with **Resume**, which opens the same report again, and **Discard**, from any tab or device of an administrator.

5. **Type the word.** The window shows a word picked at random, a real word of 6 to 10 letters in the language of the interface. Type it by hand in the field below it: the field refuses pasted and dropped text. The word guards against a hasty click, not against an administrator: the API and the command line do without it. For an archive that cannot be restored, neither the word nor **Restore and restart** is shown: only the button that drops it.
6. **Restore and restart.** Once the word is typed, **Restore and restart** confirms the restore and stops LibreFolio at once, for everyone. A window covers the page, **LibreFolio is restarting**: *Its start applies the restore. This page waits for it to come back.* LibreFolio does not start itself again: whatever supervises it does ([Who Starts LibreFolio Again](#supervisors)), and that start applies the restore ([What the Next Start Does](#next-start)).

Once LibreFolio answers again, the page shows how it went:

- ✅ **It worked**: the page goes to the sign-in page, with no message, as every session has ended. Sign in with an administrator of the backup, with the password the account had when the backup was made: the usual first page shows the restored data. A restore that worked leaves no line on the card.
- ↩️ **It did not go through**: the window reads **The restore did not go through**, with the reason, and **Back to Backup** returns to the card, after the sign-in page if the restart ended your session, or to the block page on an instance blocked meanwhile. *The data is as it was before: …* means that the restore was rolled back: the card then says when, and why. *LibreFolio restarted, but the restore was not applied.* means that a start left it waiting, for the reason that follows. What to do: [What Settings › Administration › Backup Says](backup_moving.md#restore-settings-problems).
- ⏳ **It takes long**: after a minute without the server, the window adds *LibreFolio has not come back yet. If nothing starts it again by itself, start it yourself: the restore is applied at that start.* If LibreFolio does not stop at all, after a minute the window says *LibreFolio has not stopped. If it does not restart by itself, restart it yourself: the restore is applied at that start.*, and offers **Back to Backup**: see [What Settings › Administration › Backup Says](backup_moving.md#restore-settings-problems).

The page reads the outcome with a one-time ticket that its restart request received, valid one hour and kept only in the memory of the tab: it needs no session, so the window tells the outcome whatever your configuration. Without that ticket, after a reload of the page, more than an hour of waiting, or LibreFolio restarted from the command line rather than from this page, the page goes by its session: without `JWT_SECRET`, which signs everyone out at every start ([Keep Users Signed In After a Restart](index.md#session-persistence)), it then goes to the sign-in page whatever the outcome, and **Settings › Administration › Backup** says, once you are signed in, whether the restore went through.

A restore confirmed and not applied yet shows on the card instead of **Choose an archive…**: one confirmed from the command line, or here when LibreFolio did not stop or a start left it waiting. The card reads **A restore waits for the next start of LibreFolio**, with the backup, who confirmed it (`cli` from the command line) and when, why a start left it waiting if one did, and *Restarting stops LibreFolio for everyone; its next start applies the restore and ends every session.*

- **Restart now and restore** stops LibreFolio, as **Restore and restart** does, and the page waits for it in the same way.
- **Cancel the restore** drops it with its checked copy, as `backup pending --cancel` does: the data stays as it is.

While a start applies the restore, the card reads *A start of LibreFolio is applying the restore.*

Good to know:

- 👑 Only administrators have the tab, and one restore runs at a time: one archive is checked at a time, wherever the check started, here, in another tab or on the command line (*Another archive is being checked: try again when it ends.*), and a restore waiting takes the place of **Choose an archive…**.
- 📏 When the installation limits the size of the archives, the card says so, such as *Archives up to 500 MB.*, and refuses a larger file before sending anything. The limit is `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`, in megabytes of 1024 × 1024 bytes: none by default on your own installation ([The Upload Limit of a Restore](#restore-upload-limit)).
- 💽 The disk of the data directory needs room for the archive and, while it is checked, for its copy, and for a secure backup for its decrypted archive too: [Check a Backup](#check) says how much.
- 🔑 The password of a secure backup goes to the server only with the request that starts the check, which tries it at once: it is never stored, written to the log or sent back. The field empties as soon as you submit it.
- 📦 While it is checked, the archive takes its own size on the server, which the card says while it goes up, and its opened version; both count in the space limit until the restore ends or is discarded.
- 🔄 A reload of the page keeps following the check and its report, and any other tab or device of an administrator resumes it from the card. The uploaded archive is kept 24 hours: after that, the confirmation answers *The check is too old: check the archive again.*
- 🚪 The restore ends every session, everyone signs in again with an account of the backup, and the links sent before it stop working: see [What the Next Start Does](#next-start).
- ❌ A refused upload, check or confirmation, or a server that does not answer, shows on the card with the reason. **Try again** reads the state of the restore again; to send an archive again, choose it again with **Choose an archive…**. The check refuses the same archives as the command line: see [The Check Refuses the Archive](backup_moving.md#check-refused).
- 🖥️ With nothing that starts LibreFolio again, such as a host installation started by hand, [start the server](cli_tools.md#start-the-server) yourself once it has stopped: the page waits for it.

### 📤 The Upload Limit of a Restore {: #restore-upload-limit }

To check an archive for a restore, an administrator uploads it to the instance from
Settings › Administration › Backup
([Restore from Settings › Administration › Backup](backup_restore.md#restore-settings)), through
`PUT /api/v1/backup/restore/upload`; the instance then checks it on a copy, as
`backup restore --dry-run` does on the [command line](cli_tools.md). `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` caps the size of the
archives an administrator can upload.

| `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` | Largest archive accepted |
| --- | --- |
| Not set, or empty | No limit |
| `0` | No limit |
| A whole number, such as `2048` | That many megabytes, of 1024 × 1024 bytes each |

```bash
LIBREFOLIO_BACKUP_MAX_UPLOAD_MB=2048
```

- Set it in the container's environment or in `.env`, then restart LibreFolio.
- An archive over the limit answers `413`, with the code `backup_too_large` and the limit in
  `limit_mb`: before anything is written when the request announces its size, otherwise as soon as
  the upload goes past the limit. Nothing of it is kept.
- A proxy in front of LibreFolio must let at least as much through: Nginx with
  `client_max_body_size`, whose default is only 1 MB (`client_max_body_size 2048m;` matches the
  example above), and your CDN, if it limits the size of a request. A `413` without the
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

The upload limit bounds the archive as it is sent, compressed: a zip can unpack to far more than its
own size, and the check unpacks it on the disk of the data directory.
`LIBREFOLIO_BACKUP_MAX_RESTORE_MB` bounds what an archive unpacks to, from the sizes its manifest
declares, before the check unpacks anything.

| `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` | Largest size an archive unpacks to |
| --- | --- |
| Not set, or empty | No limit |
| `0` | No limit |
| A whole number, such as `16384` | That many megabytes, of 1024 × 1024 bytes each |

- An archive over the limit is refused before anything is unpacked: the check fails with the code
  `unpacked_too_large`, and nothing of its copy is left. A secure archive is decrypted first, which
  takes about its own size, then measured the same way.
- A value you set always wins, `0` included. `backup restore` on the command line follows the same
  limit; whoever runs the server lifts it for one command with `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0`
  in front of it («Try a Restore on a Copy» in [CLI Admin Tools](cli_tools.md)).
- A value other than a whole number does not stop the server: the start log already has an error,
  `LIBREFOLIO_BACKUP_MAX_RESTORE_MB cannot be used: …` (`check` is `backup.restore_limit`), then each
  check, `POST /api/v1/backup/restore/stage`, answers `503` with the code
  `backup_restore_unavailable`, the archive kept, and the log has an error.

### ⌨️ Restore from the Command Line {: #restore-command }

Run it where the server runs, in the container with Docker:

```bash
# 1. Check the archive on a copy, read the report, then type "restore" to confirm
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# 2. Restart LibreFolio: its next start applies the restore
docker compose restart librefolio

# 3. See how it went
docker compose exec librefolio python dev.py backup pending
```

- 🧪 Step 1 runs the same check as `--dry-run` and shows the same report, then asks you to type `restore`. Nothing changes yet: LibreFolio keeps running on its data, and the restore waits for the next start.
- 🖥️ On a host installation, run `pipenv run ./dev.py backup restore <archive>`, then stop the whole server and [start it](cli_tools.md#start-the-server) again: never restart one worker alone.
- ⏳ Once LibreFolio is up again, `backup pending` says `✅ The last restore was applied on …`. Before the restart, `backup pending --cancel` drops the restore waiting, with its checked copy.
- 🤖 In a script, `--yes` confirms without asking.
- 🔐 For a secure backup (`.lfbk`), `backup restore` asks its password before the check, or reads it with `--password-file` or `--password-stdin`, as `inspect` does ([Check a Backup](#check)): in a script, give one of them as well as `--yes`.
- 📖 More: «Restore an Archive» and «Follow or Cancel a Restore» in [CLI Admin Tools](cli_tools.md).

### 🔄 What the Next Start Does {: #next-start }

- 🔀 **The swap.** The database and the three folders of files change places with the checked copy: one rename per folder, instant whatever its size. `secrets/`, `logs/`, `scheduler_state.json` and `backups/` stay as they are, so the installation keeps its own instance key. The key a secure backup carries is never put in its place: the check already re-encrypted the saved keys of the data providers on the copy, with this installation's key.
- 🚪 **Every session ends.** Everyone signs in again, on every device, with an account of the backup and the password it had then.
- 🔗 **One-time links are revoked.** No invitation, password-reset or email-verification link sent before works any more, not even those the backup held: send new ones. An account still waiting for its email verification stops waiting: when its owner asks the sign-in page for a new link, the page answers that the account is disabled. An administrator reactivates it with **Reactivate** ([What Each Action Does](users.md#actions)), or deletes it ([Delete an Account](users.md#delete)) so that its owner signs up again.
- ✅ **The first start must complete.** Only then is the restore kept and the former data removed. If that start fails, on a migration that fails or a damaged file, the next start puts the former data back by itself, and `backup pending`, like the card in Settings › Administration › Backup, says that the restore was rolled back, with the reason.

### 🔌 Who Starts LibreFolio Again {: #supervisors }

You start the restore yourself: with the restart of the command line, or with **Restore and restart** in Settings › Administration › Backup, which stops LibreFolio. Nothing in LibreFolio starts the server again: whatever supervises it does, after that stop, and after a first start that fails, so that the next start brings the data back.

| Supervisor | Starts LibreFolio again by itself |
| --- | --- |
| Docker Compose | With `restart: unless-stopped`, in both compose files LibreFolio ships |
| systemd | With `Restart=always` |
| None | No: start LibreFolio yourself, and the restore, or the way back, happens at that start |

**Restore and restart** stops LibreFolio cleanly: a policy that starts it again only after a failure, such as `on-failure`, does not start it after that stop.

---

## 🔗 Related

- 📄 **[Backups: Sealed Backups](backup_sealed.md)** — Sealed Backups: a Key Instead of a Password
- 📄 **[Backups: Moving and Troubleshooting](backup_moving.md)** — Bring Your LibreFolio Home, When Something Goes Wrong
- 🛠️ **[CLI Admin Tools](cli_tools.md)** — «Back Up the Instance»: every option and message of `backup create`, `inspect`, `restore`, `decrypt` and `pending`, and «Back Up with Docker»
- 📂 **[Filesystem Structure](filesystem.md)** — The data directory, `secrets/`, and a copy made by hand
- 🐳 **[Installation with Docker](../user/installation.md)** — Installing LibreFolio, and updating it
- 👥 **[Users & Invitations](users.md)** — Reactivate or delete accounts, and send new links
- 📧 **[Email](email.md)** — The email variables, which no archive holds
- 📝 **[Environment Variables](configuration.md)** — «The Instance Key», and every option of `.env`
- 🧑‍💻 For developers: **[Restoring a Backup](../developer/architecture/security.md#backup-restore)** — The swap, the journal, the rollback and the restart
- 🧑‍💻 For developers: **[Secure Backups (`.lfbk`)](../developer/architecture/security.md#secure-backups)** — The envelope, the password and the instance key a secure backup carries
- 🧑‍💻 For developers: **[Sealed Backups (`.tar`)](../developer/architecture/security.md#sealed-backups)** — The three members, age through `pyrage`, and the strict reader
