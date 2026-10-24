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
- 💾 `backups/`, where the command line writes its archives, and `.restore/`, the work folder of a restore;
- ⚙️ the configuration: `.env` and the environment variables, the [email](email.md) settings included, which LibreFolio keeps only in the environment.

### 🧭 What Follows {: #what-follows }

- 🔒 **Keep it private.** A clear archive holds every user's data and is not encrypted: keep it, and every copy, as private as the server itself. A [secure](#secure) one opens only with its password: keep the password apart from it.
- 🗝️ **Saved secrets and the instance key.** What LibreFolio encrypted with the instance key, such as the API key of a data source saved in the app, can be read only with that key.
    - A [secure backup](#secure) carries the key LibreFolio generated: its restore re-encrypts those secrets with the key of the installation that receives it, and there is nothing to do.
    - A clear backup leaves the key out, and so does a [sealed](backup_sealed.md#sealed) one, always, and a secure one whose key came from the environment (`LIBREFOLIO_INSTANCE_KEY`, `LIBREFOLIO_INSTANCE_KEY_FILE`) or could not be used. On an installation with another key, LibreFolio keeps those secrets, reports them as unreadable and never uses a wrong value: **Settings › Plugins** says under each one *Saved, but this instance's key cannot read it: enter it again.* If you still have the old key, put it back first, before anyone enters a secret again: stop LibreFolio, put your copy of `secrets/instance.key` in place of the generated one, or set the old value of the variable, and start it again («The Instance Key» in [Environment Variables](configuration.md)). An installation that keeps its own key, such as a hosted one, or one whose own secrets are already under its key, takes the old key at the restore instead: restore from the command line with `--instance-key-file` and your copy of the old key, and the check re-encrypts those secrets with this installation's key («The Instance Key of Another Installation» in [CLI Admin Tools](cli_tools.md)); on an instance someone hosts for you, ask whoever runs it. Enter the secrets again only if the old key is lost: a secret entered under the new key would become unreadable once the old one is back.
    - For the settings of the whole instance, every start also logs the error *Stored plugin secrets that the instance key cannot read: …* with their count, until they are entered again or the old key is back. No plugin shipped with LibreFolio keeps one today.
- ⚙️ **Bring your configuration.** Keep a copy of your `.env` with the archives: on another installation, set again the options you need, the email ones included ([Where the Configuration Lives](email.md#where-it-lives)).
- 🏠 **Any installation can take it**, if it runs the same version of LibreFolio or a newer one, whoever made the archive: Settings, the command line or a hosting panel.

---

## ⬇️ Make a Backup {: #create }

Three ways give the same archive:

- **Settings › Administration › Backup**, in the app: the archive downloads to your computer. For administrators.
- **The command line**, on the server: `backup create`.
- **A hosting panel**, if someone hosts LibreFolio for you and their panel takes backups: see [Backups for Your Hosting Panel](hosting_panel_backups.md#panel-backups).

From Settings and from the command line, the backup can also be [secure](#secure): the same zip, encrypted with a password you choose. From the command line, it can also be [sealed](backup_sealed.md#sealed): encrypted with a random password that only a private key of yours opens, for backups made without anyone at the keyboard. A hosting panel's backups are clear, or sealed when `LIBREFOLIO_BACKUP_RECIPIENTS` is set.

In every case LibreFolio keeps working during the backup, and one backup runs at a time, whoever started it.

### 🖱️ From Settings › Administration › Backup {: #settings-backup }

1. Open **Settings › Administration › Backup**: only administrators have this tab.
2. In **Back up the instance**, choose the kind of backup:
    - **Clear**, the choice the card starts with: *A plain .zip: whoever has the file sees all the data, and on another instance the keys of the data providers must be entered again.*
    - **Secure**: *An .lfbk encrypted with a password you choose: only that password opens it, and a lost password cannot be recovered. It also carries the keys of the data providers.* See [Secure Backups](#secure).
3. For a secure backup, type its password in **Password of the backup**, then again in **The same password again**. The password follows the rules the server gives, those of an account's password with at least 12 characters: the meter under the first field lists them as you type (*At least 12 characters*, *One uppercase letter*, *One lowercase letter*, *One number*, *One special character*) and shows how strong the password is. While the two fields differ, *The two passwords differ.* shows under the second one, and **Create backup** stays disabled until both are right.
4. Click **Create backup**. The password fields empty at once. The card follows the backup on the server, phase by phase; a secure backup ends with *Encrypting with your password*.
5. When it reads **Backup ready**, click **Download**. Your browser saves the archive, named after the moment the backup started, in UTC, such as `librefolio-backup-20261015-121500.zip`, or `librefolio-backup-20261015-121500.lfbk` for a secure backup, which the card marks *Encrypted with your password: keep it safe, LibreFolio cannot recover it.*

Good to know:

- 🔑 **Keep the password of a secure backup.** LibreFolio keeps no copy of it, and without it nobody opens the archive, you included: keep it in a password manager, apart from the archive.
- ⏱️ The archive stays on the server for one hour, then it is deleted: download it within the hour. **Delete from the server** removes it sooner, and **Create a new backup** starts another one.
- ⚠️ **The backup is complete, with warnings** means that the database failed its integrity check or has broken references, and was archived as it is, or that some files were left out, or, for a secure backup, that the instance key could not be used and was left out ([Making a Secure Backup](backup_moving.md#secure-problems)). The archive is written all the same: read the warnings before you rely on it.
- 🚦 While another backup runs, started from the app, the command line or a hosting panel, the card says so: try again when it ends. One started from this tab, or another tab of the app, whose answer never arrived (the connection dropped while it started) is not lost: the next **Create backup** finds it running, and the card follows it, then offers its download, as if it had just started it. This holds for a clear backup only: a secure one is never followed this way, because only its own password opens its archive, and a followed backup that turns out to be secure is not offered, unless the card had started it itself; in both cases the card says that another backup runs. A card that already offers an archive keeps offering it, and only says that another backup runs. One started from the command line or a hosting panel is not followed: its archive goes elsewhere. The card never says which backup runs; the browser's console does (its id and where it was started), should you need to find it.
- 🔒 On an instance its hosting provider has [blocked](hosting_instances.md#instance-block), the app shows the block page instead of Settings. Administrators find on it the same backup card, under **Keep a copy of the data**: make the backup and download it there ([What Users See](hosting_instances.md#what-users-see)). The hosting panel ([What Still Answers](hosting_instances.md#what-still-answers)) and the command line on the server can still make one too.

### ⌨️ From the Command Line {: #command-line }

```bash
# Docker: the archive appears in ./LibreFolio-data/backups/ on the host
docker compose exec librefolio python dev.py backup create

# Host installation: the archive goes into backups/ in the data directory
pipenv run ./dev.py backup create

# A secure backup (.lfbk): the password is asked twice
docker compose exec librefolio python dev.py backup create --encrypt
```

- 📁 `--output` (`-o`) writes the archive into another folder that already exists, or under a name of your own. With Docker, the path is inside the container: use a folder mounted from the host.
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

### 🗄️ Keep Copies Off the Server {: #keep-copies }

`backups/` is in the data directory, on the same disk as the data: an archive kept there does not survive the loss of that disk. An archive downloaded from Settings is already off the server. From the command line, write the archives to another disk, a NAS or off-site with `--output`, on a schedule.

A `cron` line for a host installation, every night at 03:30 (`crontab -e`, as the user that runs LibreFolio):

```text
30 3 * * * cd /path/to/LibreFolio && pipenv run ./dev.py backup create --output /mnt/nas/librefolio/
```

With Docker, add `-T`, as cron gives the command no terminal. The archive lands in `LibreFolio-data/backups/`: copy it elsewhere with your usual tool.

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
- 🗝️ **What it carries.** Besides the data, the instance key, when LibreFolio generated it (`secrets/instance.key`): the saved keys of the data providers travel with the backup, and its restore re-encrypts them with the key of the installation that receives it, which keeps its own. A key you set yourself, with `LIBREFOLIO_INSTANCE_KEY` or `LIBREFOLIO_INSTANCE_KEY_FILE`, or that a hosting panel gives the instance, never leaves: whoever set it keeps it.
- 🆘 **A lost password cannot be recovered.** LibreFolio keeps no copy of it, and nothing else opens the file.
- ⏳ **Slow to guess.** The key of the file comes from the password through scrypt, which takes 32 MiB of memory and about a tenth of a second for each try: nothing for one backup, light enough for a small server, but slow for whoever tries passwords one after another. Hence the rules: at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol.
- 💽 **On the server, while it is made,** the clear archive is written first, in the work folder of the backup inside `backups/`, which only the server's user can open; it is removed as soon as the `.lfbk` is written, and when the backup fails. A check decrypts the backup the same way, in a private folder of the data directory, and removes the decrypted archive once it has used it. A run killed outright, by a power cut or `kill -9`, cannot clean up: the next start of LibreFolio removes what it left in clear, and a backup cut short that way must be made again. The folder of a `backup inspect` killed that way goes once it is an hour old.

The design, for developers: [Secure Backups (`.lfbk`)](../developer/architecture/security.md#secure-backups).

---

## 🔎 Check a Backup {: #check }

Two commands check an archive and change nothing. With Docker, give the path inside the container: an archive in `LibreFolio-data/backups/` is in `/app/backend/data/prod-docker/backups/` there.

```bash
# Is the archive whole, and what does it hold?
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip

# Can this installation restore it? A restore tried on a copy
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip --dry-run

# A secure backup: the same commands ask its password first
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.lfbk
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
2. **Type its password**, for a secure backup. The card asks for it before anything is sent: *A secure backup: type the password it was made with.* Type it in **Password of the backup** and click **Check the backup**: the archive is sent, with the same progress bar, and the password goes with the request that starts the check, which tries it at once. A wrong password brings the form back, with *Wrong password, or the file was changed: type the password again.* The archive stays on the server, and the next try does not send it again. **Cancel** forgets the file.
3. **Let it be checked.** The server checks the archive on a copy, as `backup restore --dry-run` does ([Check a Backup](#check)): *Decrypting the backup*, for a secure backup only, *Checking the archive*, *Unpacking it on a copy*, *Updating the copy's database*, *Verifying the copy*. Nothing changes until you confirm. **Stop the check** drops it: a check still running is dropped as soon as it ends.
4. **Read the report.** It opens in a window, **What this restore would do**; once closed, **Read the report** opens it again. It gives:
    - who made the archive, with which version of LibreFolio, and when;
    - its database: at the version of this LibreFolio, or brought to it on the copy, with the migrations listed, and the fixes applied to the copy;
    - the files and their size, the size of the database, and the tables whose rows the update changed;
    - whether the backup carries the key of the instance it comes from: either way, this LibreFolio keeps its own;
    - the saved keys of the data providers: how many are re-encrypted with this LibreFolio's key, such as *2 saved keys of data providers are re-encrypted with this instance's key.*, and how many it cannot read, to enter again after the restore, such as *1 saved key of a data provider cannot be read with this instance's key: enter it again after the restore.* ([What Follows](#what-follows));
    - the ledger totals: the same as when the backup was made, different on the lines listed ([how to read them](backup_moving.md#check-refused)), not recorded, recorded by another version of the method, or unreadable;
    - the administrators of the backup, with *After the restore you sign in with one of them, with the password of then; every session open now ends.*
    - *Invitations and links sent before the restore will have expired: send them again if needed.*
    - the warnings, which let the restore go on, and the blocker, which forbids it: a backup without an active administrator;
    - until when the checked copy is kept: 24 hours after the check.

    **Drop this archive** drops the check and its copy: nothing is restored.

5. **Type the word.** The window shows a word picked at random, a real word of 6 to 10 letters in the language of the interface. Type it by hand in the field below it: the field refuses pasted and dropped text. The word guards against a hasty click, not against an administrator: the API and the command line do without it. For an archive that cannot be restored, the field and the button stay disabled.
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
- 📏 When the installation limits the size of the archives, the card says so, such as *Archives up to 500 MB.*, and refuses a larger file before sending anything. The limit is `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`, in megabytes of 1024 × 1024 bytes: none by default on your own installation, 500 MB by default in the managed profile of a hosting provider ([The Upload Limit of a Restore](hosting_panel_backups.md#restore-upload-limit)).
- 💽 The disk of the data directory needs room for the archive and, while it is checked, for its copy, and for a secure backup for its decrypted archive too: [Check a Backup](#check) says how much.
- 🔑 The password of a secure backup goes to the server only with the request that starts the check, which tries it at once: it is never stored, written to the log or sent back. The field empties as soon as you submit it.
- 🔄 A reload of the page, in the same tab, keeps following the check and its report. The checked copy is kept 24 hours: after that, the confirmation answers *The check is too old: check the archive again.*
- 🚪 The restore ends every session, everyone signs in again with an account of the backup, and the links sent before it stop working: see [What the Next Start Does](#next-start).
- ❌ A refused upload, check or confirmation, or a server that does not answer, shows on the card with the reason. **Try again** reads the state of the restore again; to send an archive again, choose it again with **Choose an archive…**. The check refuses the same archives as the command line: see [The Check Refuses the Archive](backup_moving.md#check-refused).
- 🖥️ With nothing that starts LibreFolio again, such as a host installation started by hand, [start the server](cli_tools.md#start-the-server) yourself once it has stopped: the page waits for it.
- 🔒 On an instance its hosting provider has [blocked](hosting_instances.md#instance-block), the app shows the block page instead of Settings: there is no restore from the app there. A restore confirmed before the block waits for the unblock: the first start after it applies it. If the start that follows **Restore and restart** finds the instance blocked, the window says why the restore was not applied, and **Back to Backup** leads to the block page.
- 👑 On an instance a hosting provider runs, the confirmation also asks which account of the backup becomes the owner's: see [The Owner's Account on a Hosted Instance](#owner-account).

### 👑 The Owner's Account on a Hosted Instance {: #owner-account }

On an instance a hosting provider runs for its users (the `managed` profile, see [The Managed Profile](hosting_providers.md#managed-profile)), the owner is the person whose address the provider set in `LIBREFOLIO_ADMIN_EMAIL`. A backup uploaded from the app may come from anywhere: in it, the owner's account may be missing, no longer an administrator, or have a password someone else knows. So, on such an instance, a restore confirmed from **Settings › Administration › Backup** names the account of the backup that becomes the owner's, and the owner then chooses its password.

- 🖱️ **When it is asked.** When you confirm the restore of an archive you uploaded, after the word is typed, LibreFolio asks you to choose that account. The choice is mandatory: without it the restore is not confirmed. It is asked only there: a restore the hosting provider makes from its panel ([Restoring an Instance from Your Panel](hosting_panel_backups.md#panel-restore)) or with `backup restore` on the command line never asks, and changes no account's password. On your own installation (`selfhosted`, the default) it is never asked.
- 👥 **Which accounts are offered.**
    - If an account of the backup already has the owner's address (the capitals of the letters do not matter), it is the only choice, whatever its role: no other account could take that address.
    - Otherwise, any active administrator of the backup.
- 🔄 **What the restore does with it.** At the first start on the restored data, as the restore is kept ([What the Next Start Does](#next-start)):
    - the password of the chosen account stops working: nobody signs in with the password it had in the backup, and whoever prepared the backup cannot sign in as the owner. As for every account, its sessions end and every link of the backup is revoked;
    - the account takes the owner's address and becomes an active administrator;
    - then the owner receives by email a link to choose a new password, valid 30 minutes, and signs in with it. Starting again after a crash is harmless: a new link replaces the old one, which stops working.
    - if the database is locked at that moment (by another worker of the start, or a backup running), LibreFolio waits and tries again, up to 4 times, 1 second apart, each try waiting up to 30 seconds for the lock. Only if it is still locked after that does the owner's account stay for the next start (`⏳` below).
- 📮 **Without email.** When the instance cannot send email ([Email](email.md)), no message goes out: LibreFolio writes the link in the log of the instance, and whoever runs the server gives it **only to the owner**: whoever has it sets the password of the owner's account. The link is never in the report of the restore, in `backup pending` or in any answer of the server, because every administrator reads them, including whoever prepared the backup. If the 30 minutes pass before the owner uses it, the owner chooses the password with **Forgot Password?** on the sign-in page, with the owner's address, which is now the account's.
- 🛡️ **The owner's protection is derived again.** The mark that says which account is the instance's owner, which a backup carries from the instance it was made on, is cleared at every restore. After it, the owner is the account the restore assigns or, in a restore with no choice of owner (from the hosting panel or the command line), the account the instance derives from `LIBREFOLIO_ADMIN_EMAIL` at its start.
- 🚫 **No administrator, no restore.** A backup without an active administrator cannot be restored, here as on any instance: the report shows it as a blocker.
- 🔑 The sentence of the report, *After the restore you sign in with one of them, with the password of then*, holds for the other administrators of the backup: the account chosen for the owner signs in only with the password set through its link.

After a restore that was kept, `backup pending` adds one line about the owner's account (`backup pending --recover owner` prints the same ones):

| Line | What it means |
| --- | --- |
| `✉️ The owner's account is set: a link to choose its password went to the owner's address` | Done: the owner chooses the password from the email |
| `⚠️ The owner's account is set, but no email could be sent: the link to choose its password is in the log of the instance; give it only to the owner` | No email went out: the line carries no link, which is in the log of the instance; give it only to the owner, and to nobody else |
| `⏳ The owner's account is set at the next start of the server` | The start has not given the owner the account yet, for instance because the database stayed locked through the tries: the next start does it |
| `❌ The owner's account could not be set (<CODE>): the server log has the cause` | The account could not be given to the owner: the log of the start names the cause |

`backup pending --json` does not carry this line.

When the confirmation is refused, nothing is confirmed and the data stays as it is:

| Code | Why | What to do |
| --- | --- | --- |
| `owner_choice_required` | No account was chosen for the owner | Choose one of the accounts offered, then confirm again |
| `owner_choice_invalid` | The account chosen is not one the restore offers: not an active administrator of the backup, or another one than the account that already has the owner's address | Choose one of the accounts offered |
| `owner_email_not_set` | The instance has no owner's address: `LIBREFOLIO_ADMIN_EMAIL` is not set | Ask the hosting provider to set it and restart LibreFolio, then choose the archive again to check it |
| `restore_stage_outdated` | LibreFolio was updated since the check, or the owner's address changed since then: the accounts offered were read for the old address | Choose the archive again: a new check offers the accounts for the current address |
| `owner_conflict` | The backup holds two accounts on one address or one name (the capitals of the letters aside), or an account named with the owner's address that does not have that address; or an administrator that still waits for its first-setup link (the initial administrator, never completed) while no account holds the owner's address: the start would give that account the owner's address. The owner's account could not be set safely | For the first causes, such a backup cannot be restored on a hosted instance: on the installation it comes from, give the accounts at fault their own name and address, then make a new backup. For the waiting administrator, in the source instance complete that account's setup or delete it, then make a new backup; or have an account hold the owner's address there |

### ⌨️ Restore from the Command Line {: #restore-command }

Run it where the server runs, in the container with Docker:

```bash
# 1. Check the archive on a copy, read the report, then type "restore" to confirm
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip

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
| A Fly.io Machine | With the `always` restart policy, or with `on-fail` where the Fly Proxy wakes the Machine on a request |
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
- 🏢 **[Hosting for Others](hosting_providers.md)** — [Backups for Your Hosting Panel](hosting_panel_backups.md#panel-backups) and [The Upload Limit of a Restore](hosting_panel_backups.md#restore-upload-limit)
- 🧑‍💻 For developers: **[Restoring a Backup](../developer/architecture/security.md#backup-restore)** — The swap, the journal, the rollback and the restart
- 🧑‍💻 For developers: **[Secure Backups (`.lfbk`)](../developer/architecture/security.md#secure-backups)** — The envelope, the password and the instance key a secure backup carries
- 🧑‍💻 For developers: **[Sealed Backups (`.tar`)](../developer/architecture/security.md#sealed-backups)** — The three members, age through `pyrage`, and the strict reader
