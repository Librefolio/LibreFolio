# 💾 Backup, Restore and Moving Your Instance

A backup is one archive with your whole LibreFolio in it: the database and the files of every user. It is a plain zip or, for a [secure backup](#secure), an `.lfbk` encrypted with a password you choose.

**You make it from the app, in a few clicks, and you restore it from the app too**: no terminal is needed. The command line is there for the cases the app does not cover, such as backups that run on a schedule.

Here you find:

- the [quick start from the app](#quick-start), with the buttons to press;
- [what the archive holds](#contents) and [what follows](#what-follows);
- how to [make one](#create), from the app or from the command line, and how to [keep copies off the server](#keep-copies);
- how to [check it](#check) and how to [restore it](#restore), from the app or from the command line.

Every option and message of the commands: «Back Up the Instance», in [CLI Admin Tools](cli_tools.md).

!!! tip "🗓️ Make one before every update"

    LibreFolio never takes a database back to an older version. A backup made before an update is your way back to the version you had: see [Updating LibreFolio](../user/installation.md#updating).

!!! info "📚 This guide is in several pages"

    Besides this page: [Backups: Sealed Backups](backup_sealed.md), [Backups: Moving and Troubleshooting](backup_moving.md).

---

## 🖱️ Quick Start: Back Up from the App {: #quick-start }

Backup is an **administrator's** tool: it holds the data of every user, so only administrators see the **Backup** tab. In three steps:

1. Open **Settings**, and in the **Administration** group of the tab bar choose **Backup**.
2. In **Back up the instance** choose **Clear** (a plain `.zip`) or **Secure** (an `.lfbk` closed with a password of your choice, typed twice), then click **Create backup**.
3. At **Backup ready**, click **Download**: the file goes to your computer. LibreFolio also keeps a copy on the server, in **Backups on this server**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="backup-create" alt="Settings, Administration, Backup tab: the Back up the instance card with the Clear and Secure kinds and the Create backup button" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

The same list of copies kept on the server is in **Files › Backups**, where you **Download** or **Delete** each one:

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="backups" alt="Files, Backups tab: the backups kept on the server with their date, origin, type and size, and the Download and Delete buttons" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Every detail follows: [which kind to choose](#secure), [where the copies stay](#kept-backups) and [how to restore](#restore), all from the same tab. What to remember now:

- 💽 a copy that stays on the server's disk is not a real backup: download it and keep it elsewhere ([Keep Copies Off the Server](#keep-copies));
- 🔑 the password of a secure backup cannot be recovered: keep it apart from the file;
- 🗓️ make one before every update.

---

## 📦 What a Backup Holds {: #contents }

The archive is a zip with the layout of the [data directory](filesystem.md): unpacked into an empty data directory, it is your instance again. A [secure backup](#secure) is the same zip, encrypted with a password, in an `.lfbk` file. A [sealed backup](backup_sealed.md#sealed) is a secure backup whose password opens only with a private key of yours, in a `.tar`.

| In the archive | What it is |
| --- | --- |
| `sqlite/app.db` | The database: users, brokers, transactions, assets, prices, exchange rates and settings. A consistent copy, taken while LibreFolio keeps running |
| `custom-uploads/` | The files uploaded in the app |
| `broker_reports/` | The broker reports |
| `scenario_catalog/` | Your stress scenarios, if you added any |
| `secrets/instance.key` | Only in a [secure backup](#secure), and only if LibreFolio generated the instance key: the key that encrypts the saved keys of the data providers. A restore only reads it: the installation that receives the backup keeps its own |
| `manifest.json` | The description of the archive: LibreFolio version and creation date, migration revision of the database, rows per table, control totals of the ledger (the cash of every broker per currency and the quantity of every position), size and SHA-256 checksum of every file, and whether the archive carries the instance key |

Never in the archive:

- 🔑 `secrets/`: a [secure backup](#secure) carries only the key LibreFolio generated, `secrets/instance.key`, never a key you set yourself with `LIBREFOLIO_INSTANCE_KEY` or `LIBREFOLIO_INSTANCE_KEY_FILE` («The Instance Key» in [Environment Variables](configuration.md));
- 📝 `logs/` and `scheduler_state.json` (the last run of the scheduled syncs);
- 💾 `backups/`, where LibreFolio [keeps the backups it makes](#kept-backups), and `.restore/`, the work folder of a restore;
- ⚙️ the configuration: `.env` and the environment variables, the [email](email.md) settings included, which live only in the environment.

### 🧭 What Follows {: #what-follows }

- 🔒 **Keep it private.** A clear archive holds every user's data, not encrypted: keep it, with every copy, as private as the server. A [secure](#secure) one opens only with its password: keep the password apart from the archive.
- ⚙️ **Bring your configuration with you.** Keep a copy of your `.env` with the archives: on another installation, set again the options you need, the email ones included ([Where the Configuration Lives](email.md#where-it-lives)).
- 🏠 **Any installation can take it**, from Settings or from the command line, if it runs the same version of LibreFolio or a newer one, whoever made the archive.
- 🗝️ **Saved secrets and the instance key.** What LibreFolio encrypted with the instance key, such as the API key of a data source saved in the app, can be read only with that key:

| Backup | The instance key | Restored on an installation with another key |
| --- | --- | --- |
| [Secure](#secure), key generated by LibreFolio | Travels with the data | The secrets are re-encrypted with the key of the installation that receives it: nothing to do |
| Clear; [sealed](backup_sealed.md#sealed); secure with a key from the environment (`LIBREFOLIO_INSTANCE_KEY`, `LIBREFOLIO_INSTANCE_KEY_FILE`) or not usable | Stays out | The secrets stay saved but unreadable; LibreFolio never uses a wrong value. **Settings › Plugins** says under each one *Saved, but this instance's key cannot read it: enter it again.* |

If you still have the old key, put it back **before** anyone enters a secret again: a secret entered under the new key would become unreadable once the old one is back. Enter the secrets again only if the old key is lost.

1. Stop LibreFolio.
2. **On the server, in `secrets/` of the data directory**: put your copy of `secrets/instance.key` in place of the generated one. Or, **in `.env`**, set the old value of the variable again («The Instance Key» in [Environment Variables](configuration.md)).
3. Start LibreFolio again.

If the installation keeps its own key, or its secrets are already encrypted with its key, it takes the old key at the restore: **from the command line**, restore with `--instance-key-file` and your copy of the old key; the check re-encrypts those secrets with this installation's key («The Instance Key of Another Installation» in [CLI Admin Tools](cli_tools.md)).

For the settings of the whole instance, every start logs the error *Stored plugin secrets that the instance key cannot read: …*, with their count, until they are entered again or the old key is back. No plugin shipped with LibreFolio keeps one today.

---

## ⬇️ Make a Backup {: #create }

Two ways give the same archive:

| Where | What you get |
| --- | --- |
| **Settings › Administration › Backup**, in the app (administrators) | The archive downloaded to your computer, and a copy [kept on the server](#kept-backups) |
| **Terminal on the server**: `backup create` | The archive on the server, or where you say with `--output` |

From both, the backup can be [secure](#secure): the same zip, encrypted with a password you choose. Only from the command line can it be [sealed](backup_sealed.md#sealed): encrypted with a random password that only a private key of yours opens, for backups made without anyone at the keyboard.

LibreFolio keeps working during the backup. One backup runs at a time, whoever started it.

### 🖱️ From Settings › Administration › Backup {: #settings-backup }

1. Open **Settings › Administration › Backup** (only administrators have the tab), section **Back up the instance**.
2. Choose the kind:
    - **Clear** (default): *A plain .zip: whoever has the file sees all the data, and on another instance the keys of the data providers must be entered again.*
    - **Secure**: *An .lfbk encrypted with a password you choose: only that password opens it, and a lost password cannot be recovered. It also carries the keys of the data providers.* See [Secure Backups](#secure).
3. For a secure backup, type the password in **Password of the backup** and again in **The same password again**. The rules of an account password apply, given by the server: the meter under the first field lists them as you type (*At least 12 characters*, *One uppercase letter*, *One lowercase letter*, *One number*, *One special character*) and shows how strong it is. While the two fields differ, *The two passwords differ.* shows and **Create backup** stays disabled.
4. Click **Create backup**. The password fields empty at once; the card follows the backup phase by phase (a secure backup ends with *Encrypting with your password*).
5. At **Backup ready**, click **Download**. The browser saves `librefolio-backup-20261015-121500.zip` (date and time of start, in UTC), or `.lfbk` for a secure backup, which the card marks *Encrypted with your password: keep it safe, LibreFolio cannot recover it.*

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="backup-ready" alt="The Backup tab at Backup ready: the archive name, size and date, with the Download and Delete from the server buttons" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Good to know:

- 🔑 **Keep the password of a secure backup** in a password manager, apart from the archive: LibreFolio keeps no copy of it, and without it nobody opens the archive, you included.
- 💾 A copy stays on the server, in the list of [Backups Kept on the Server](#kept-backups), until you delete it or the [automatic clean-up](#backup-cleanup) removes it: download it from there later, too. A copy on the same disk as the data is not a real backup: keep it elsewhere ([Keep Copies Off the Server](#keep-copies)). **Delete from the server** removes it at once; **Create a new backup** starts another one.
- ⚠️ **The backup is complete, with warnings**: the database failed its integrity check or has broken references and was archived as it is; or some files were left out; or, for a secure backup, the instance key could not be used and was left out ([Making a Secure Backup](backup_moving.md#secure-problems)). The archive is written all the same: read the warnings before you rely on it.
- 🚦 **Another backup is running** (from the app or the command line): the card says so, try again when it ends.

What the card does with a backup already in progress:

| Backup in progress | The card |
| --- | --- |
| Clear, started from this or another tab of the app, whose answer never arrived (connection dropped at the start) | Not lost: the next **Create backup** finds it, follows it and offers its download |
| Secure, not started from this tab | Never followed: only its password opens the archive. The card says that another backup is running |
| Any, while the card already offers an archive | It keeps offering its own and only says that another backup is running |
| Started from the command line | Not followed: its archive goes elsewhere |

The card never says which backup is running: the browser's console does (id and origin).

### ⌨️ From the Command Line {: #command-line }

**In the server's terminal**, from the folder with `docker-compose.yml` (Docker) or from the LibreFolio folder (host installation):

```bash
# Docker: the archive appears in its own folder of ./LibreFolio-data/backups/ on the host
docker compose exec librefolio python dev.py backup create

# Host installation: the archive goes into its own folder of backups/ in the data directory
pipenv run ./dev.py backup create

# A secure backup (.lfbk): the password is asked twice
docker compose exec librefolio python dev.py backup create --encrypt
```

The command prints the path of the archive and its `SHA-256:`.

- 🗃️ Without `--output`, the archive stays on the server, in a folder of its own inside `backups/` ([Backups Kept on the Server](#kept-backups)).
- 📁 `--output` (`-o`) copies the archive into another folder that already exists, or under a name of your own; nothing stays in `backups/`. With Docker the path is inside the container: use a folder mounted from the host.
- 🔒 Only the owner of the archive can read it (`0600`): with Docker, the container's user.
- 🔐 `--encrypt` makes a [secure backup](#secure), `librefolio-backup-<date>-<time>.lfbk`, and asks the password twice at the terminal. Instead: `--password-file FILE`, a file with the password alone (the line breaks at its end do not count), such as a Docker secret; or `--password-stdin`, one line of the standard input from a pipe (at a terminal, the command asks it without showing it). Either one makes the backup secure by itself, with or without `--encrypt`; they are not used together.
- 🙈 There is no `--password`: every user of the server reads the commands that run (`ps`), and the shell keeps them in its history.
- 📏 Password rules, as in Settings › Administration › Backup: at least 12 characters, an uppercase letter, a lowercase letter, a digit and a symbol. Otherwise the command stops before writing anything: `❌ The password of a backup needs at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: min_length, digit)`.
- 🤖 Without a terminal (cron, script), `--encrypt` alone stops: `❌ A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal (password_required)`.
- 📖 Every option, warning and error: «Back Up the Instance» and «Back Up with Docker» in [CLI Admin Tools](cli_tools.md).

??? example "🐳 The password of the backups as a Docker secret"

    1. **Next to `docker-compose.yml`**, write the password alone in a file, such as `backup_password.txt`, never in `LibreFolio-data/` (whoever had the data would have the password too). Then `chmod 600 backup_password.txt`, and keep a copy of the password elsewhere: lost, it cannot be recovered.
    2. **In `docker-compose.yml`**, add the marked lines and leave the rest of the service as it is. If the file already has `secrets:` lists, such as for `JWT_SECRET_FILE` («Secrets in Files» in [Environment Variables](configuration.md)), add the lines to them.

        ```yaml
        services:
          librefolio:
            secrets:                              # added
              - backup_password                   # added
        secrets:                                  # added
          backup_password:                        # added
            file: ./backup_password.txt           # added
        ```

        Run `docker compose up -d`: the container is recreated with the secret.

    3. **In the server's terminal**, make the backup with the path of the secret in the container:

        ```bash
        docker compose exec librefolio python dev.py backup create --password-file /run/secrets/backup_password
        ```

### 🗃️ Backups Kept on the Server {: #kept-backups }

A backup made from the app or the command line is no longer deleted after an hour: it stays on the server until you delete it, or until the [automatic clean-up](#backup-cleanup) removes it. Each one has a folder of its own in `backups/` of the data directory: moment of creation (UTC), origin (`ui` app, `cli` command line) and a short code that tells two backups of the same second apart. The archive inside keeps its usual name, `.zip`, `.lfbk` or `.tar`:

```text
backups/librefolio-backup-20261015-121500-ui-1a2b3c4d/librefolio-backup-20261015-121500.zip
```

`backups/.jobs/` holds only a backup in progress or one that failed, removed after an hour.

**Where you see them**: **Settings › Administration › Backup**, under *Backups on this server*, or **Files › Backups**, the same list; administrators only. **Refresh**, at the top of the list, reads it again: a backup made from the command line appears only then. For each backup:

- 📅 date and time of creation, and origin: app or command line;
- 🔐 type: plain, with password ([secure](#secure)) or [sealed](backup_sealed.md#sealed);
- 📏 size and SHA-256: click to copy the whole checksum and compare it with the one of the downloaded file;
- 📦 **Once restored**: the space its contents take once restored, not compressed, that is what a restore will take; point at it for its parts: the database, the uploaded files, the broker reports and the other files. A backup made before LibreFolio recorded it shows «—»;
- ⬇️ **Download** and 🗑️ **Delete**, which removes the backup from the server at once.

!!! warning "💽 Download it and keep it elsewhere"

    A backup that stays on the same disk as your data is not a real backup: when the disk is lost, the data and its backups go together. Download the archive and keep it on another disk, a NAS or off-site ([Keep Copies Off the Server](#keep-copies)).

The list shows only the backups made by this version of LibreFolio. The loose `librefolio-backup-*.zip` files of earlier versions in `backups/` are not listed and LibreFolio never removes them: delete them yourself when you no longer need them.

### 🧹 Automatic Clean-up {: #backup-cleanup }

**In the closed Automatic clean-up panel**, in the **Backups on this server** section of **Settings › Administration › Backup** or of **Files › Backups**, you set two limits, both optional:

| Limit | What it does | Off |
| --- | --- | --- |
| Total size, in MB | When the kept backups weigh more, the oldest are deleted until the rest fits | `0` |
| Maximum age, in days | An older backup is deleted | `0` |

- 🛡️ **The latest backup is always kept**, whatever the limits say.
- ⏰ The clean-up runs after each backup and when LibreFolio starts, at most once an hour: a saved change applies within an hour.
- 🏠 **Self-hosted:** both limits are off until you set them.
- 🔍 Only the backups of the list are cleaned: never the older loose archives in `backups/`, a backup in progress or a failed one.
- ⌨️ The backups of the command line stay in the same place and follow the same limits: [Where the Backups Stay](cli_backup.md#backup-kept).

### 📊 The Space Bar {: #space-used }

**In Files**, above the tabs, administrators see the **Space used** bar: how much room your instance takes. It updates with **Refresh** and whenever the list of kept backups changes. The legend gives the size of each part:

| Part | What it counts |
| --- | --- |
| **Database** | The database and the files it keeps beside it |
| **Uploaded files** | The files uploaded in the app, such as those of the **Files** page |
| **Broker reports** | The statements uploaded to import transactions |
| **Backups** | Everything in `backups/`: the [backups kept on the server](#kept-backups), a backup in progress and a failed one |
| **Pending restore** | A [restore](#restore) not finished or dropped yet: the uploaded archive and its unpacked version |
| **Other LibreFolio files** | The rest of the data directory: logs, state and the like |

Three looks of the bar:

| Situation | The bar | The line under it |
| --- | --- | --- |
| 💽 **No limit** (self-hosted default) | The whole disk of the data: LibreFolio's parts coloured, **Other on the disk** grey, **Free** empty | How much LibreFolio uses of the disk |
| 📏 **With a limit** | The limit, filled as far as the data goes | *used of limit* |
| 📁 **No limit and the disk unknown** (LibreFolio cannot ask it) | LibreFolio's folder alone, split into its parts, with no free space | — |

**Set the limit** in **Files › Advanced** (closed panel under the bar), field **LibreFolio total space (MB)**: a whole number of megabytes, `0` for no limit, then **Save**; a green notice confirms. It is the most space LibreFolio may take in all. The same field is in **Settings › Administration › [Global Settings](settings.md)**, category **Memory**: either place changes it.

- 🚧 **Past the limit**, LibreFolio refuses what would add data: an uploaded file, a broker report, a backup started by hand (after trying the [automatic clean-up](#backup-cleanup)) and a [restore](#restore) whose result would pass it. The message says what to raise the total space to and, if the disk lacks room, how much more it needs free. Never stopped: transactions, prices and database, the backups of a hosting panel and of the command line (the clean-up follows them) and a restore already confirmed. The limit deletes nothing by itself.
- ⚠️ The bar warns that the limit is exceeded and suggests deleting backups or files, or raising the limit. It then becomes your data, so that no part is left out: a *Limit 20 MB* tick shows where the limit falls, the red lines after it by how much you pass it.
- 💬 **A refusal is told where you are**: in the upload or import window, or on the backup card. An administrator finds **Open the settings**, which opens **Settings › Administration › Global Settings** with the **LibreFolio total space (MB)** row in view and highlighted: unlock the tab to change it; a user reads how much space to free, or to ask an administrator. With a limit set by whoever hosts the instance, the message says to ask them.
- 🔒 **Set in the server's configuration**: with `LIBREFOLIO_STORAGE_LIMIT_MB` in the environment, its value is the limit, the field is read-only, here and in Global Settings, and a note says it is set by whoever hosts the instance ([Environment Variables](configuration.md)). A value that is not a whole number is ignored and the field works as above.
- 🧹 **Clean-up and bar work together.** Usually the backups grow: the [automatic clean-up](#backup-cleanup) keeps them in check, and every backup deleted in **Settings › Administration › Backup** or in **Files › Backups** shortens **Backups** in the bar. Near the limit, start there.

### 🗄️ Keep Copies Off the Server {: #keep-copies }

`backups/` is in the data directory, on the same disk: a backup there does not survive the loss of the disk. An archive downloaded from Settings is already off the server. From the command line, write the archives to another disk, a NAS or off-site with `--output`, on a schedule.

**In the `crontab` of the user that runs LibreFolio** (`crontab -e`), host installation, every night at 03:30:

```text
30 3 * * * cd /path/to/LibreFolio && pipenv run ./dev.py backup create --output /mnt/nas/librefolio/
```

**With Docker**, add `-T` (cron gives the command no terminal). The archive lands in a folder of its own in `LibreFolio-data/backups/`, where the [automatic clean-up](#backup-cleanup), once set, keeps the disk from filling up: copy it elsewhere with your usual tool.

```text
30 3 * * * cd /path/to/librefolio && docker compose exec -T librefolio python dev.py backup create
```

**[Secure](#secure) archives**: add `--password-file` with a file that holds the password (cron has no terminal to ask on). With Docker, the secret of the example above:

```text
30 3 * * * cd /path/to/librefolio && docker compose exec -T librefolio python dev.py backup create --password-file /run/secrets/backup_password
```

- 📁 The folder of `--output` must exist when the command runs: mount the NAS first. A path that is not an existing folder becomes the name of the archive.
- 🔢 The command prints what it did and exits with `1` when the archive is not where you asked: keep the output, or have cron mail it to you.
- 🧭 cron has a short `PATH`: if it does not find `pipenv` or `docker`, write the full path (`command -v pipenv` prints it).
- 🗑️ LibreFolio deletes none of these archives: remove the old ones yourself. Keep several, and the last one made before each update.
- 🔑 Keep a copy of `.env` too, as private as the archives: no archive holds it. And a copy of `secrets/`, unless your archives are secure: a clear or [sealed](backup_sealed.md#sealed) one leaves the instance key out ([What Follows](#what-follows)).
- 🔏 Nightly archives that the server itself cannot open, without a password file on its disk: [Every Night with cron](backup_sealed.md#sealed-cron), in Sealed Backups.

### 🧰 Backups with restic or Backrest {: #restic }

LibreFolio writes the archive; a backup tool takes it off-site and keeps a history of it. [restic](https://restic.net/) copies a folder, encrypted, to S3, Backblaze B2, SFTP and more, and forgets the old copies by a rule of yours. [Backrest](https://github.com/garethgeorge/backrest) is a web interface for restic, with its own scheduler. LibreFolio needs neither: they only read the folder of its archives.

Nightly recipe, host installation. **In a private file** (`chmod 600`), restic's variables:

```bash
# /etc/librefolio-restic.env: where the copies go, and the file with restic's password
RESTIC_REPOSITORY=sftp:backup@nas.example:/srv/restic/librefolio
RESTIC_PASSWORD_FILE=/root/.restic-librefolio-password
```

**In the `crontab`**:

```text
30 3 * * * cd /path/to/LibreFolio && pipenv run ./dev.py backup create --output /var/backups/librefolio/ && . /etc/librefolio-restic.env && restic backup /var/backups/librefolio/ && restic forget --keep-daily 7 --keep-weekly 4 --prune && find /var/backups/librefolio/ -name 'librefolio-backup-*' -mtime +2 -delete
```

The line makes the archive, sends the folder, keeps seven daily and four weekly copies in the repository and removes the local archives older than two days. With Docker, make the archive with the command of [Keep Copies Off the Server](#keep-copies) and give restic the host folder `LibreFolio-data/backups/`. With Backrest, add a plan on that folder, with its schedule and retention, and leave `backup create` in cron.

- 🔐 **restic's password is a key to all your data**: whoever holds it reads every copy. As private as the password of a [secure backup](#secure), with a copy elsewhere: lost, the repository cannot be read any more.
- 🔑 **No public key.** restic uses its password to write as well as to read: the server that sends the copies can also read them. If that is a problem, send [sealed backups](backup_sealed.md#sealed-cron) (`--sealed`): only your private key opens them, neither the server nor restic's password. [Secure backups](#secure) (`--password-file`) work too, but their password sits in a file on the same server.
- 📦 **Little to deduplicate.** Every archive is compressed, a secure one is encrypted: restic stores each archive almost whole. Plan the repository's space for the copies you keep.
- 🧪 **Try a restore before you need one.** `restic restore latest --target /tmp/librefolio-check`, then check the archive with [`backup restore --dry-run`](#check).

---

## 🔐 Secure Backups {: #secure }

A secure backup is the archive of a clear backup, encrypted with a password you choose, in a file of LibreFolio's own: `.lfbk`. You make it from [Settings › Administration › Backup](#settings-backup) or with `backup create --encrypt` on the [command line](#command-line); every check and restore of this page takes it, given its password.

- 🛡️ **It protects the file at rest.** Lost disk, stolen laptop, copy on a cloud or a NAS: without the password nothing can be read, neither the data nor the names of the files. A changed or truncated file is detected when opened and refused.
- 👁️ **It does not protect from whoever knows the password**: they read everything, the data of every user and the keys of the data providers. Give it only to whoever may restore the backup, never together with the file.
- 🗝️ **It carries the instance key**, if LibreFolio generated it (`secrets/instance.key`): the saved keys of the data providers travel with the backup, and the restore re-encrypts them with the key of the installation that receives it, which keeps its own. A key you set yourself (`LIBREFOLIO_INSTANCE_KEY`, `LIBREFOLIO_INSTANCE_KEY_FILE`) never leaves.
- 🆘 **A lost password cannot be recovered.** LibreFolio keeps no copy of it, and nothing else opens the file.
- ⏳ **Slow to guess.** The key of the file comes from the password through scrypt: 32 MiB of memory and about a tenth of a second per try, nothing for one backup, slow for whoever tries passwords one after another. Hence the rules: at least 12 characters, an uppercase letter, a lowercase letter, a digit and a symbol.
- 💽 **On the server, while it is made,** the clear archive is written first, in the work folder of the backup inside `backups/`, which only the server's user can open; it is removed as soon as the `.lfbk` is written, and when the backup fails. After an abrupt interruption (power cut, `kill -9`), the next start of LibreFolio removes what was left in clear, and the backup must be made again. A check decrypts the backup the same way: [Check a Backup](#check).

The design, for developers: [Secure Backups (`.lfbk`)](../developer/architecture/security.md#secure-backups).

---

## 🔎 Check a Backup {: #check }

Two commands check an archive without changing anything. **In the server's terminal**, inside the container with Docker: an archive in `LibreFolio-data/backups/` is there in `/app/backend/data/prod-docker/backups/`, and a [kept](#kept-backups) backup is in its own folder, such as `/app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/`.

```bash
# Is the archive whole, and what does it hold?
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# Can this installation restore it? A restore tried on a copy
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip --dry-run

# A secure backup: the same commands ask its password first
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.lfbk
```

Host installation: `pipenv run ./dev.py backup …` with the path of the archive on the host.

| | `backup inspect` | `backup restore --dry-run` |
| --- | --- | --- |
| It answers | Whether the archive is whole: size and SHA-256 of every entry, compared with the manifest | Whether this installation can restore it: archive unpacked into a copy, brought up to date and checked |
| It shows | Who made the archive and when, revision of the database, rows and tables, files, whether the instance key is included | The same, plus: the migrations a restore would apply, the ledger totals of the copy compared with those of the archive, the provider keys re-encrypted with this installation's key or to enter again, the administrators you would sign in with |
| It needs | Any LibreFolio, server running or stopped; no data directory, except for a secure backup, which it decrypts there | The installation that would receive the archive (the server may keep running) and free space in its data directory: archive unpacked + twice its database + 64 MB |
| It ends with | `✅ Every entry matches the manifest` | `✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed.` |

- 🔐 **Secure backup** (`.lfbk`): both ask the password first, at the terminal or with `--password-file FILE` / `--password-stdin`, as `backup create`. They decrypt it into a private folder of the data directory, which only the server's user can open, and remove the decrypted archive at the end: room is needed for that too, about the size of the `.lfbk`. After an abrupt interruption (power cut, `kill -9`), the next start of LibreFolio removes what was left in clear: the archive of `--dry-run` at once, the folder of `inspect` after an hour, which the next `inspect` also removes. The report adds `Secure backup: decrypted with its password`. Wrong password: `❌ The password does not open this backup (wrong_password)`. A `.zip` ignores the two options.
- 🗝️ `--dry-run` says what becomes of the saved keys of the data providers, for any archive: `Saved provider keys: 2 re-encrypted with this instance's key` if the backup carries the key that encrypted them, `⚠️ 1 saved provider key cannot be read with this instance's key: enter it again after the restore` for those it cannot read ([What Follows](#what-follows)).
- 🔁 Run `inspect` now and then on the copies you keep, and `--dry-run` before a move, on the installation that will receive the archive.
- 🖱️ **Restore an archive**, in Settings › Administration › Backup, runs the same check as `--dry-run` on an archive from your computer: read the report, then **Drop this archive**, and nothing changes ([Restore from Settings › Administration › Backup](#restore-settings)).
- ❌ A refusal ends with a code in parentheses: [When Something Goes Wrong](backup_moving.md#troubleshooting). Full lists in «Check an Archive» and «Try a Restore on a Copy», in [CLI Admin Tools](cli_tools.md).

---

## ♻️ Restore on This Installation {: #restore }

A restore replaces the data of the installation with the archive's: database and files, for every user. Two ways, which check the archive on a copy first and change nothing until you confirm; the next start of LibreFolio applies the restore:

| Where | Who | After confirming |
| --- | --- | --- |
| **Settings › Administration › Backup**, in the app | Administrators | LibreFolio stops at once, for that start |
| **Terminal on the server**: `backup restore` | Whoever has access to the server | You restart it when it suits you |

On an instance someone hosts for you, the command line is on their server: use Settings › Administration › Backup, or ask them.

### 🖱️ Restore from Settings › Administration › Backup {: #restore-settings }

1. **Choose the archive.** In **Settings › Administration › Backup**, under **Back up the instance**, the **Restore an archive** card reminds you that a restore replaces the data of every user: if you may want them back, [make a backup first](#settings-backup). **Choose an archive…** → a `.zip` or a secure `.lfbk` made by LibreFolio, here or elsewhere. The **Restore an archive** window opens, and the next steps go on in it: a `.zip` goes to the server at once, with a progress bar: **Stop sending** stops it, nothing is kept.

    **Or take a backup the server keeps**: **Restore** on its row in the list of [backups kept on the server](#kept-backups), here or in **Files › Backups**, opens the **Restore a backup** window, with no further confirmation: the server takes that backup as the archive, with no download or upload, and the next steps, report included, happen in that window. Close it, or choose **I'll decide later** in the report: the check waits on the **Restore an archive** card, with **Resume** and **Discard**. A sealed backup of a hosting panel opens only with the private key of its recipients: it is not restored here.

2. **Type the password**, for a secure backup: the window asks for it before sending anything (*A secure backup: type the password it was made with.*). Fill in **Password of the backup** and click **Check the backup**: the archive is sent, and the password goes with the request that starts the check, which tries it at once. Wrong password → *Wrong password, or the file was changed: type the password again.*; the archive stays on the server and the next try does not send it again. **Cancel** forgets the file.
3. **Let it be checked.** The server checks the archive on a copy, as `backup restore --dry-run` does ([Check a Backup](#check)): *Decrypting the backup* (secure only), *Checking the archive*, *Unpacking it on a copy*, *Updating the copy's database*, *Verifying the copy*. Nothing changes until you confirm. **Stop the check** drops it (a check still running is dropped as soon as it ends).
4. **Read the report**, in the **What this restore would do** window: closing it keeps the check for later, as **I'll decide later** does. Closing the window during the check keeps it too: the check goes on, and **Resume** follows it again. What it says: below.
5. **Type the word.** The window shows a real word, picked at random, of 6 to 10 letters in the language of the interface. Type it by hand in the field below: the field refuses pasted and dropped text. The word guards against a hasty click, not against an administrator: the API and the command line do without it. For an archive that cannot be restored, neither the word nor **Restore and restart** appears: only the button that drops it.
6. **Restore and restart.** It confirms the restore and stops LibreFolio at once, for everyone. A window covers the page, **LibreFolio is restarting**: *Its start applies the restore. This page waits for it to come back.* LibreFolio does not restart by itself: whatever supervises it does ([Who Starts LibreFolio Again](#supervisors)), and that start applies the restore ([What the Next Start Does](#next-start)).

#### 📋 What the Report Says

- who made the archive, with which version of LibreFolio and when;
- the database: at the version of this LibreFolio, or brought to it on the copy, with the migrations listed and the fixes applied to the copy;
- the files and their size, the size of the database and the tables whose rows the update changed; and a bar of what the backup holds: the database, the uploaded files, the broker reports and the other files;
- whether the backup carries the key of the instance it comes from: either way, this LibreFolio keeps its own;
- the saved keys of the data providers: how many re-encrypted with this LibreFolio's key (*2 saved keys of data providers are re-encrypted with this instance's key.*) and how many unreadable, to enter again after the restore (*1 saved key of a data provider cannot be read with this instance's key: enter it again after the restore.*) ([What Follows](#what-follows));
- the ledger totals: the same as when the backup was made, different on the lines listed ([how to read them](backup_moving.md#check-refused)), not recorded, recorded by another version of the method or unreadable;
- the administrators of the backup, with *After the restore you sign in with one of them, with the password of then; every session open now ends.*
- *Invitations and links sent before the restore will have expired: send them again if needed.*
- every administrator with the picture of their account in the backup, and **Verify a password before restoring**: pick one, type their password and click **Verify**. Answer: *You will sign in with this password after the restore.*, or *That is not their password.* The password is compared with the backup only: never stored, written to the log or sent back;
- the warnings, which let it go on, and the blockers, which forbid the restore: a backup without an active administrator, and a restore that would pass the [space limit](#space-used), with the size to raise it to; such a check gives its space back at once, and the report stays on screen until you close it;
- until when the uploaded archive is kept: 24 hours after the check.

Under the report: **Drop this archive** drops the check and its copy, nothing is restored. **I'll decide later** closes the window and keeps the check: the **Restore an archive** card shows *A restore waits for your decision until …*, with **Resume**, which opens the same report again, and **Discard**, from any tab or device of an administrator.

#### 🏁 How It Went

When LibreFolio answers again, the page shows the outcome:

| Outcome | What you see | What to do |
| --- | --- | --- |
| ✅ **It worked** | The sign-in page, with no message: every session has ended. A restore that worked leaves no line on the card | Sign in with an administrator of the backup, with the password it had when the backup was made: the first page shows the restored data |
| ↩️ **It did not go through** | **The restore did not go through**, with the reason. *The data is as it was before: …* = rolled back, the card says when and why. *LibreFolio restarted, but the restore was not applied.* = a start left it waiting, for the reason that follows | **Back to Backup** returns to the card (after the sign-in page if the restart ended your session, or to the block page on an instance blocked meanwhile). Then [What Settings › Administration › Backup Says](backup_moving.md#restore-settings-problems) |
| ⏳ **It takes long** | After a minute without the server: *LibreFolio has not come back yet. If nothing starts it again by itself, start it yourself: the restore is applied at that start.* If LibreFolio does not stop at all, after a minute: *LibreFolio has not stopped. If it does not restart by itself, restart it yourself: the restore is applied at that start.*, with **Back to Backup** | [What Settings › Administration › Backup Says](backup_moving.md#restore-settings-problems) |

The page reads the outcome with a one-time ticket received from the restart request, valid one hour and kept only in the memory of the tab: no session is needed. Without the ticket (page reloaded, more than an hour of waiting, restart from the command line instead of from here) the page goes by its session: without `JWT_SECRET`, which signs everyone out at every start ([Keep Users Signed In After a Restart](index.md#session-persistence)), it goes to the sign-in page whatever the outcome, and **Settings › Administration › Backup** says, once you are in, whether the restore went through.

#### ⏳ A Restore Waiting

A restore confirmed and not applied yet takes the place of **Choose an archive…**: one confirmed from the command line, or here when LibreFolio did not stop or a start left it waiting. The card says **A restore waits for the next start of LibreFolio**, with the backup, who confirmed it (`cli` from the command line) and when, the reason if a start left it waiting, and *Restarting stops LibreFolio for everyone; its next start applies the restore and ends every session.*

| Button | What it does |
| --- | --- |
| **Restart now and restore** | Stops LibreFolio, as **Restore and restart** does; the page waits for it the same way |
| **Cancel the restore** | Drops it with its checked copy, as `backup pending --cancel` does: the data stays as it is |

While a start applies the restore, the card says *A start of LibreFolio is applying the restore.*

Good to know:

- 👑 Only administrators have the tab. One restore at a time: one archive is checked at a time, wherever the check started, here, in another tab or on the command line (*Another archive is being checked: try again when it ends.*).
- 📏 If the installation limits the size of the archives (`LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`, none by default), the card says so (*Archives up to 500 MB.*) and refuses a larger file before sending anything: [The Upload Limit of a Restore](#restore-upload-limit).
- 💽 The disk of the data directory needs room for the archive, for its copy during the check and, for a secure backup, for the decrypted archive: how much, in [Check a Backup](#check).
- 📦 During the check, the archive takes its size on the server, which the card says while it is uploaded, plus its unpacked version; both count towards the space limit until the restore ends or is dropped.
- 🔑 The password of a secure backup goes to the server only with the request that starts the check, which tries it at once: never stored, written to the log or sent back. The field empties as soon as you send it.
- 🔄 A reload of the page keeps following the check and the report, and any other tab or device of an administrator picks it up from the Backup tab. The uploaded archive is kept 24 hours: after that, the confirmation answers *The check is too old: check the archive again.*
- 🚪 The restore ends every session, everyone signs in again with an account of the backup, and the links sent before stop working: [What the Next Start Does](#next-start).
- ❌ A refused upload, check or confirmation, or a server that does not answer, shows on the card with the reason. **Try again** reads the state of the restore again; to send an archive again, **Choose an archive…**. The check refuses the same archives as the command line: [The Check Refuses the Archive](backup_moving.md#check-refused).
- 🖥️ If nothing restarts LibreFolio, such as a host installation started by hand, [start the server](cli_tools.md#start-the-server) yourself once it has stopped: the page waits for it.

### 📤 The Upload Limit of a Restore {: #restore-upload-limit }

An administrator uploads the archive from Settings › Administration › Backup ([Restore from Settings › Administration › Backup](backup_restore.md#restore-settings)), through `PUT /api/v1/backup/restore/upload`, and the instance checks it on a copy, as `backup restore --dry-run` does on the [command line](cli_tools.md). Two variables limit how large it can be.

**`LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`** limits the archive as it is sent, compressed:

| Value | Largest archive accepted |
| --- | --- |
| Not set, or empty | No limit |
| `0` | No limit |
| A whole number, such as `2048` | That many megabytes, of 1024 × 1024 bytes each |

1. **In `.env`**, or in the container's environment:

    ```bash
    LIBREFOLIO_BACKUP_MAX_UPLOAD_MB=2048
    ```

2. Restart LibreFolio. With Docker Compose, run `docker compose up -d`.
3. **In the configuration of the proxy** in front of LibreFolio, let at least as much through: Nginx with `client_max_body_size`, default only 1 MB (`client_max_body_size 2048m;` matches the example), and your CDN, if it limits the size of a request.

The limit in force is read in `upload_limit_mb` of `GET /api/v1/backup/restore/status`: `0` no limit, `null` unreadable value. Settings › Administration › Backup shows it on the restore card (*Archives up to 500 MB.*) and refuses a larger file before sending it.

| The upload answers | Code | When |
| --- | --- | --- |
| `413` | `backup_too_large`, with the limit in `limit_mb` | Archive over the limit: before writing anything if the request announces its size, otherwise as soon as the upload goes past the limit. Nothing is kept |
| `413` without `backup_too_large` | — | It comes from the proxy, not from LibreFolio |
| `503` | `backup_upload_unavailable` | Value that is not a whole number (`500MB`, `-1`): the server does not stop, but the start log already has `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB cannot be used: …` (`check` is `backup.upload_limit`) and every upload adds to the log an error that names the variable: `The upload limit of a restore cannot be read` |
| `507` | `backup_no_space` | The disk of the data directory has no room for the archive and, during the check, for its unpacked copy (how much: «Try a Restore on a Copy» in [CLI Admin Tools](cli_tools.md)); also when the disk reports itself full only at the end of the file, as a network file system or a quota may. The check has a code of its own, `no_space`: `507` if it cannot even start, refusal of the archive once it runs |
| `500` | `backup_upload_failed` | The upload cannot be written for another reason; the log has the cause |

**`LIBREFOLIO_BACKUP_MAX_RESTORE_MB`** limits the unpacked size, from the sizes the manifest declares, before the check unpacks anything: a zip can unpack to far more than its size, on the disk of the data directory.

| Value | Largest unpacked size of an archive |
| --- | --- |
| Not set, or empty | No limit |
| `0` | No limit |
| A whole number, such as `16384` | That many megabytes, of 1024 × 1024 bytes each |

- An archive over the limit is refused before anything is unpacked: the check fails with the code `unpacked_too_large`, nothing of the copy is left. A secure archive is decrypted first (about its size), then measured the same way.
- A value you set always wins, `0` included. `backup restore` on the command line follows the same limit; whoever runs the server lifts it for one command with `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` in front of it («Try a Restore on a Copy» in [CLI Admin Tools](cli_tools.md)).
- A value that is not a whole number does not stop the server: the start log already has `LIBREFOLIO_BACKUP_MAX_RESTORE_MB cannot be used: …` (`check` is `backup.restore_limit`), then every check, `POST /api/v1/backup/restore/stage`, answers `503` with the code `backup_restore_unavailable`, the archive is kept and the log has an error.

### ⌨️ Restore from the Command Line {: #restore-command }

**In the server's terminal**, where LibreFolio runs: in the container with Docker.

```bash
# 1. Check the archive on a copy, read the report, then type "restore" to confirm
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# 2. Restart LibreFolio: its next start applies the restore
docker compose restart librefolio

# 3. See how it went
docker compose exec librefolio python dev.py backup pending
```

- 🧪 Step 1 runs the same check as `--dry-run`, shows the same report, then asks you to type `restore`. Nothing changes yet: LibreFolio keeps running on its data, the restore waits for the next start.
- 🖥️ Host installation: `pipenv run ./dev.py backup restore <archive>`, then stop the whole server and [start it](cli_tools.md#start-the-server) again: never one worker alone.
- ⏳ With LibreFolio up again, `backup pending` says `✅ The last restore was applied on …`. Before the restart, `backup pending --cancel` drops the restore waiting, with its checked copy.
- 🤖 In a script, `--yes` confirms without asking.
- 🔐 Secure backup (`.lfbk`): `backup restore` asks the password before the check, or reads it with `--password-file` or `--password-stdin`, as `inspect` does ([Check a Backup](#check)): in a script, one of the two together with `--yes`.
- 📖 More: «Restore an Archive» and «Follow or Cancel a Restore» in [CLI Admin Tools](cli_tools.md).

### 🔄 What the Next Start Does {: #next-start }

- 🔀 **The swap.** The database and the three folders of files change places with the checked copy, in an instant whatever the size. `secrets/`, `logs/`, `scheduler_state.json` and `backups/` stay as they are: the installation keeps its own instance key. The key a secure backup carries is never put in its place: the check already re-encrypted the keys of the data providers on the copy, with this installation's key.
- 🚪 **Every session ends.** Everyone signs in again, on every device, with an account of the backup and the password it had then.
- 🔗 **One-time links are revoked.** No invitation, password-reset or email-verification link sent before works any more, not even those in the backup: send new ones. An account still waiting for its email verification stops waiting: when its owner asks the sign-in page for a new link, the page answers that the account is disabled. An administrator reactivates it with **Reactivate** ([What Each Action Does](users.md#actions)) or deletes it ([Delete an Account](users.md#delete)) so that its owner signs up again.
- ✅ **The first start must complete.** Only then is the restore kept and the former data removed. If it fails (failed migration, damaged file), the next start puts the former data back by itself, and `backup pending`, like the card in Settings › Administration › Backup, says that the rollback was done, with the reason.

### 🔌 Who Starts LibreFolio Again {: #supervisors }

You start the restore: with the restart of the command line, or with **Restore and restart** in Settings › Administration › Backup, which stops LibreFolio. Nothing in LibreFolio restarts the server: whatever supervises it does, after that stop and after a first start that fails, so that the next start brings the data back.

| Supervisor | Restarts LibreFolio by itself |
| --- | --- |
| Docker Compose | With `restart: unless-stopped`, in both compose files LibreFolio ships |
| systemd | With `Restart=always` |
| None | No: start LibreFolio yourself, and the restore, or the way back, happens at that start |

**Restore and restart** stops LibreFolio cleanly: a policy that restarts only after a failure, such as `on-failure`, does not start it after that stop.

---

## 🔗 Related

- 📄 **[Backups: Sealed Backups](backup_sealed.md)** — Sealed Backups: a Key Instead of a Password
- 📄 **[Backups: Moving and Troubleshooting](backup_moving.md)** — Bring Your LibreFolio Home, When Something Goes Wrong
- 🛠️ **[CLI Admin Tools](cli_tools.md)** — «Back Up the Instance»: every option and message of `backup create`, `inspect`, `restore`, `decrypt` and `pending`, and «Back Up with Docker»
- 📂 **[Filesystem Structure](filesystem.md)** — The data directory, `secrets/` and a copy made by hand
- 🐳 **[Installation with Docker](../user/installation.md)** — Installing LibreFolio and updating it
- 👥 **[Users & Invitations](users.md)** — Reactivate or delete accounts and send new links
- 📧 **[Email](email.md)** — The email variables, which no archive holds
- 📝 **[Environment Variables](configuration.md)** — «The Instance Key» and every option of `.env`
- 🧑‍💻 For developers: **[Restoring a Backup](../developer/architecture/security.md#backup-restore)** — The swap, the journal, the rollback and the restart
- 🧑‍💻 For developers: **[Secure Backups (`.lfbk`)](../developer/architecture/security.md#secure-backups)** — The envelope, the password and the instance key a secure backup carries
- 🧑‍💻 For developers: **[Sealed Backups (`.tar`)](../developer/architecture/security.md#sealed-backups)** — The three members, age through `pyrage` and the strict reader

