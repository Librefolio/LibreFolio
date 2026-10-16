# 💾 Backup, Restore and Moving Your Instance

A backup is one archive with your whole LibreFolio in it: the database and the files of every user. This page tells the whole story: what the archive holds, how to make and check one, how to restore it, and how to move LibreFolio from an instance someone hosts for you to your own server, or the other way round. Every option and message of the commands is in «Back Up the Instance», in [CLI Admin Tools](cli_tools.md).

!!! tip "🗓️ Make one before every update"

    LibreFolio never takes a database back to an older version. A backup made before an update is your way back to the version you had: see [Updating LibreFolio](../user/installation.md#updating).

---

## 📦 What a Backup Holds {: #contents }

The archive is a zip with the layout of the [data directory](filesystem.md): unpacked into an empty data directory, it is your instance again.

| In the archive | What it is |
| --- | --- |
| `sqlite/app.db` | The database: users, brokers, transactions, assets, prices, exchange rates and settings. A consistent copy, made while LibreFolio keeps running |
| `custom-uploads/` | The files uploaded in the app |
| `broker_reports/` | The broker reports |
| `scenario_catalog/` | Your own stress scenarios, if you added any |
| `manifest.json` | The description of the archive: the LibreFolio version that made it and when, the migration revision of the database, its rows per table, the ledger's control totals (the cash of every broker in each currency and the quantity of every position), and the size and SHA-256 checksum of every file |

Never in the archive:

- 🔑 `secrets/`, which holds the instance key: see «The Instance Key» in [Environment Variables](configuration.md);
- 📝 `logs/`, and `scheduler_state.json`, the last run of the scheduled syncs;
- 💾 `backups/`, where the command line writes its archives, and `.restore/`, the work folder of a restore;
- ⚙️ the configuration: `.env` and the environment variables, the [email](email.md) settings included, which LibreFolio keeps only in the environment.

### 🧭 What Follows {: #what-follows }

- 🔒 **Keep it private.** The archive holds every user's data and is not encrypted: keep it, and every copy, as private as the server itself.
- 🗝️ **Saved secrets stay behind.** What LibreFolio encrypted with the instance key cannot be read on an installation with another key. There, a secret plugin setting saved in the app, such as the API key of a data source, is reported as set but unreadable: enter it again. No plugin shipped with LibreFolio keeps one today.
- ⚙️ **Bring your configuration.** Keep a copy of your `.env` with the archives: on another installation, set again the options you need, the email ones included ([Where the Configuration Lives](email.md#where-it-lives)).
- 🏠 **Any installation can take it**, if it runs the same version of LibreFolio or a newer one, whoever made the archive: Settings, the command line or a hosting panel.

---

## ⬇️ Make a Backup {: #create }

Three ways give the same archive:

- **Settings › Backup**, in the app: the archive downloads to your computer. For administrators.
- **The command line**, on the server: `backup create`.
- **A hosting panel**, if someone hosts LibreFolio for you and their panel takes backups: see [Backups for Your Hosting Panel](hosting_providers.md#panel-backups).

In every case LibreFolio keeps working during the backup, and one backup runs at a time, whoever started it.

### 🖱️ From Settings › Backup {: #settings-backup }

1. Open **Settings › Backup**: only administrators have this tab.
2. In **Back up the instance**, click **Create backup**. The card follows the backup on the server, phase by phase.
3. When it reads **Backup ready**, click **Download**. Your browser saves the archive, named after the moment the backup started, in UTC, such as `librefolio-backup-20261015-121500.zip`.

Good to know:

- ⏱️ The archive stays on the server for one hour, then it is deleted: download it within the hour. **Delete from the server** removes it sooner, and **Create a new backup** starts another one.
- ⚠️ **The backup is complete, with warnings** means that the database failed its integrity check or has broken references, and was archived as it is, or that some files were left out. The archive is written all the same: read the warnings before you rely on it.
- 🚦 While another backup runs, started from the app, the command line or a hosting panel, the card says so: try again when it ends.
- 🔒 On an instance its hosting provider has [blocked](hosting_providers.md#instance-block), the app shows the block page instead of Settings, and that page has no backup button yet. The backup itself is still allowed there: for an administrator through the API and for the hosting panel ([What Still Answers](hosting_providers.md#what-still-answers)), and from the command line on the server.

### ⌨️ From the Command Line {: #command-line }

```bash
# Docker: the archive appears in ./LibreFolio-data/backups/ on the host
docker compose exec librefolio python dev.py backup create

# Host installation: the archive goes into backups/ in the data directory
pipenv run ./dev.py backup create
```

- 📁 `--output` (`-o`) writes the archive into another folder that already exists, or under a name of your own. With Docker, the path is inside the container: use a folder mounted from the host.
- 🔒 Only the owner of the archive can read it (`0600`): with Docker, that is the container's user.
- 📖 Every option, warning and error: «Back Up the Instance» and «Back Up with Docker» in [CLI Admin Tools](cli_tools.md).

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

- 📁 The folder given to `--output` must exist when the command runs, so mount the NAS first: a path that is not an existing folder becomes the name of the archive itself.
- 🔢 The command prints what it did, and exits with `1` when the archive is not where you asked: keep that output, or have cron mail it to you.
- 🧭 cron runs commands with a short `PATH`: if it does not find `pipenv` or `docker`, write the full path, which `command -v pipenv` prints.
- 🗑️ LibreFolio deletes none of these archives: remove the old ones yourself. Keep several, and the last one made before each update.
- 🔑 Keep a copy of `secrets/` and of `.env` as well, as private as the archives: neither is in them.

---

## 🔎 Check a Backup {: #check }

Two commands check an archive and change nothing. With Docker, give the path inside the container: an archive in `LibreFolio-data/backups/` is in `/app/backend/data/prod-docker/backups/` there.

```bash
# Is the archive whole, and what does it hold?
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip

# Can this installation restore it? A restore tried on a copy
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip --dry-run
```

On a host installation, run `pipenv run ./dev.py backup …` with the path of the archive on the host.

| | `backup inspect` | `backup restore --dry-run` |
| --- | --- | --- |
| It answers | Whether the archive is whole: the size and SHA-256 checksum of every entry, compared with the manifest | Whether this installation can restore it: the archive unpacked into a copy, brought up to date and checked |
| It shows | Who made the archive and when, the revision of its database, its rows and tables, its files, and that the instance key is not included | The same, plus the migrations a restore would apply, the ledger's control totals of the copy compared with those the archive recorded, and the administrators you would sign in with |
| It needs | Any LibreFolio, its server running or stopped: no data directory | The installation that would receive the archive, whose server may keep running, and free space in its data directory: the archive unpacked, plus twice its database, plus 64 MB |
| It ends with | `✅ Every entry matches the manifest` | `✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed.` |

- 🔁 Run `inspect` now and then on the copies you keep, and `--dry-run` before a move, on the installation that will receive the archive.
- 🖱️ **Restore an archive**, in Settings › Backup, runs the same check as `--dry-run` on an archive from your computer: read its report, then **Drop this archive**, and nothing changes ([Restore from Settings › Backup](#restore-settings)).
- ❌ A refusal ends with a code in parentheses: see [When Something Goes Wrong](#troubleshooting). The full lists are in «Check an Archive» and «Try a Restore on a Copy», in [CLI Admin Tools](cli_tools.md).

---

## ♻️ Restore on This Installation {: #restore }

A restore replaces the data of the installation with the archive's: the database and the files, for every user. Two ways lead to it: **Settings › Backup**, in the app, for administrators, and `backup restore`, on the command line of the server. Both check the archive on a copy first and change nothing until you confirm: the next start of LibreFolio then applies it. From Settings › Backup, LibreFolio stops as soon as you confirm, for that start; on the command line, you restart it when it suits you. On an instance someone hosts for you, the command line is on their server: as one of its administrators, use Settings › Backup, or ask them.

### 🖱️ Restore from Settings › Backup {: #restore-settings }

1. **Choose the archive.** In **Settings › Backup**, under **Back up the instance**, the card **Restore an archive** reminds you that a restore replaces the data of every user: if you may want the current data back, [make a backup](#settings-backup) first. Click **Choose an archive…** and pick a backup archive, a `.zip` made by LibreFolio here or on another installation. It is sent to the server with a progress bar: **Stop sending** stops it, and nothing is kept.
2. **Let it be checked.** The server checks the archive on a copy, as `backup restore --dry-run` does ([Check a Backup](#check)): *Checking the archive*, *Unpacking it on a copy*, *Updating the copy's database*, *Verifying the copy*. Nothing changes until you confirm. **Stop the check** drops it: a check still running is dropped as soon as it ends.
3. **Read the report.** It opens in a window, **What this restore would do**; once closed, **Read the report** opens it again. It gives:
    - who made the archive, with which version of LibreFolio, and when;
    - its database: at the version of this LibreFolio, or brought to it on the copy, with the migrations listed, and the fixes applied to the copy;
    - the files and their size, the size of the database, and the tables whose rows the update changed;
    - that the instance key is not included: this LibreFolio keeps its own;
    - the ledger totals: the same as when the backup was made, different on the lines listed ([how to read them](#check-refused)), not recorded, recorded by another version of the method, or unreadable;
    - the administrators of the backup, with *After the restore you sign in with one of them, with the password of then; every session open now ends.*
    - *Invitations and links sent before the restore will have expired: send them again if needed.*
    - the warnings, which let the restore go on, and the blocker, which forbids it: a backup without an active administrator;
    - until when the checked copy is kept: 24 hours after the check.

    **Drop this archive** drops the check and its copy: nothing is restored.

4. **Type the word.** The window shows a word picked at random, a real word of 6 to 10 letters in the language of the interface. Type it by hand in the field below it: the field refuses pasted and dropped text. The word guards against a hasty click, not against an administrator: the API and the command line do without it. For an archive that cannot be restored, the field and the button stay disabled.
5. **Restore and restart.** Once the word is typed, **Restore and restart** confirms the restore and stops LibreFolio at once, for everyone. A window covers the page, **LibreFolio is restarting**: *Its start applies the restore. This page waits for it to come back.* LibreFolio does not start itself again: whatever supervises it does ([Who Starts LibreFolio Again](#supervisors)), and that start applies the restore ([What the Next Start Does](#next-start)).

Once LibreFolio answers again, the page shows how it went:

- ✅ **It worked**: the page goes to the sign-in page, with no message, as every session has ended. Sign in with an administrator of the backup, with the password the account had when the backup was made: the usual first page shows the restored data. A restore that worked leaves no line on the card.
- ↩️ **It did not go through**: the window reads **The restore did not go through**, with the reason, and **Back to Backup** returns to the card, after the sign-in page if the restart ended your session, or to the block page on an instance blocked meanwhile. *The data is as it was before: …* means that the restore was rolled back: the card then says when, and why. *LibreFolio restarted, but the restore was not applied.* means that a start left it waiting, for the reason that follows. What to do: [What Settings › Backup Says](#restore-settings-problems).
- ⏳ **It takes long**: after a minute without the server, the window adds *LibreFolio has not come back yet. If nothing starts it again by itself, start it yourself: the restore is applied at that start.* A window that keeps waiting while LibreFolio still answers: see [What Settings › Backup Says](#restore-settings-problems).

The page reads the outcome with a one-time ticket that its restart request received, valid one hour and kept only in the memory of the tab: it needs no session, so the window tells the outcome whatever your configuration. Without that ticket, after a reload of the page, more than an hour of waiting, or LibreFolio restarted from the command line rather than from this page, the page goes by its session: without `JWT_SECRET`, which signs everyone out at every start ([Keep Users Signed In After a Restart](index.md#session-persistence)), it then goes to the sign-in page whatever the outcome, and **Settings › Backup** says, once you are signed in, whether the restore went through.

A restore confirmed and not applied yet shows on the card instead of **Choose an archive…**: one confirmed from the command line, or here when LibreFolio did not stop or a start left it waiting. The card reads **A restore waits for the next start of LibreFolio**, with the backup, who confirmed it (`cli` from the command line) and when, why a start left it waiting if one did, and *Restarting stops LibreFolio for everyone; its next start applies the restore and ends every session.*

- **Restart now and restore** stops LibreFolio, as **Restore and restart** does, and the page waits for it in the same way.
- **Cancel the restore** drops it with its checked copy, as `backup pending --cancel` does: the data stays as it is.

While a start applies the restore, the card reads *A start of LibreFolio is applying the restore.*

Good to know:

- 👑 Only administrators have the tab, and one restore runs at a time: one archive is checked at a time, wherever the check started, here, in another tab or on the command line (*Another archive is being checked: try again when it ends.*), and a restore waiting takes the place of **Choose an archive…**.
- 📏 When the installation limits the size of the archives, the card says so, such as *Archives up to 500 MB.*, and refuses a larger file before sending anything. The limit is `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`, in megabytes of 1024 × 1024 bytes: none by default on your own installation, 500 MB by default in the managed profile of a hosting provider ([The Upload Limit of a Restore](hosting_providers.md#restore-upload-limit)).
- 💽 The disk of the data directory needs room for the archive and, while it is checked, for its copy: [Check a Backup](#check) says how much.
- 🔄 A reload of the page, in the same tab, keeps following the check and its report. The checked copy is kept 24 hours: after that, the confirmation answers *The check is too old: check the archive again.*
- 🚪 The restore ends every session, everyone signs in again with an account of the backup, and the links sent before it stop working: see [What the Next Start Does](#next-start).
- ❌ A refused upload, check or confirmation, or a server that does not answer, shows on the card with the reason. **Try again** reads the state of the restore again; to send an archive again, choose it again with **Choose an archive…**. The check refuses the same archives as the command line: see [The Check Refuses the Archive](#check-refused).
- 🖥️ With nothing that starts LibreFolio again, such as a host installation started by hand, [start the server](cli_tools.md#start-the-server) yourself once it has stopped: the page waits for it.
- 🔒 On an instance its hosting provider has [blocked](hosting_providers.md#instance-block), the app shows the block page instead of Settings: there is no restore from the app there. A restore confirmed before the block waits for the unblock: the first start after it applies it. If the start that follows **Restore and restart** finds the instance blocked, the window says why the restore was not applied, and **Back to Backup** leads to the block page.

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
- 📖 More: «Restore an Archive» and «Follow or Cancel a Restore» in [CLI Admin Tools](cli_tools.md).

### 🔄 What the Next Start Does {: #next-start }

- 🔀 **The swap.** The database and the three folders of files change places with the checked copy: one rename per folder, instant whatever its size. `secrets/`, `logs/`, `scheduler_state.json` and `backups/` stay as they are, so the installation keeps its own instance key.
- 🚪 **Every session ends.** Everyone signs in again, on every device, with an account of the backup and the password it had then.
- 🔗 **One-time links are revoked.** No invitation, password-reset or email-verification link sent before works any more, not even those the backup held: send new ones. An account still waiting for its email verification stops waiting: when its owner asks the sign-in page for a new link, the page answers that the account is disabled. An administrator reactivates it with **Reactivate** ([What Each Action Does](users.md#actions)), or deletes it ([Delete an Account](users.md#delete)) so that its owner signs up again.
- ✅ **The first start must complete.** Only then is the restore kept and the former data removed. If that start fails, on a migration that fails or a damaged file, the next start puts the former data back by itself, and `backup pending`, like the card in Settings › Backup, says that the restore was rolled back, with the reason.

### 🔌 Who Starts LibreFolio Again {: #supervisors }

You start the restore yourself: with the restart of the command line, or with **Restore and restart** in Settings › Backup, which stops LibreFolio. Nothing in LibreFolio starts the server again: whatever supervises it does, after that stop, and after a first start that fails, so that the next start brings the data back.

| Supervisor | Starts LibreFolio again by itself |
| --- | --- |
| Docker Compose | With `restart: unless-stopped`, in both compose files LibreFolio ships |
| systemd | With `Restart=always` |
| A Fly.io Machine | With the `always` restart policy, or with `on-fail` where the Fly Proxy wakes the Machine on a request |
| None | No: start LibreFolio yourself, and the restore, or the way back, happens at that start |

**Restore and restart** stops LibreFolio cleanly: a policy that starts it again only after a failure, such as `on-failure`, does not start it after that stop.

---

## 🏠 Bring Your LibreFolio Home {: #bring-home }

An archive moves your LibreFolio from one installation to another: from an instance someone hosts for you to your own server, or the other way round. The installation that receives it must run the same version of LibreFolio or a newer one ([Never Backwards](#never-backwards)).

### 🏡 From a Hosted Instance to Your Server {: #to-your-server }

With Docker Compose on your server:

1. **Download a backup** of the hosted instance, as one of its administrators: **Settings › Backup**, **Create backup**, then **Download** ([From Settings › Backup](#settings-backup)). Its version is in **Settings › About** ([About](../user/settings/about.md)).
2. **Prepare LibreFolio** on your server with steps 1 and 2 of [Installation with Docker](../user/installation.md): the folder, `docker-compose.yml` and `.env`. Do not start it yet.
3. **Copy the archive into its data folder**, next to `docker-compose.yml`, to restore it from the command line:

    ```bash
    mkdir -p LibreFolio-data/backups
    cp /path/to/librefolio-backup-20261015-121500.zip LibreFolio-data/backups/
    ```

    From the app, skip this step: you choose the archive on your computer.

4. **Start LibreFolio, restore the archive, restart**:

    ```bash
    docker compose up -d
    docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip
    docker compose restart librefolio
    ```

    `backup restore` checks the archive on a copy first: if this LibreFolio cannot take it, the command says why, and nothing changes. Read the report, then type `restore`.

    Or, from the app: start LibreFolio with `docker compose up -d`, open it, and create the administrator account it asks for, with **Register here**. Then restore the archive from **Settings › Backup** ([Restore from Settings › Backup](#restore-settings)): it is checked on a copy in the same way, and **Restore and restart** stops LibreFolio, which Docker starts again to apply the restore. The restore replaces the account you created with the accounts of the backup.

5. **Sign in** with your account of the hosted instance, and the password it had when you made the backup.
6. **Set what the archive does not carry**: the options of `.env` you need, the email ones included ([Email](email.md)), and any secret plugin setting saved in the app ([What Follows](#what-follows)).

Good to know:

- 🐳 At every start the container gives the whole `LibreFolio-data/` folder to its user: an archive copied in before the first start can be read by the server. One copied in later may need `sudo chown 1000:1000 <archive>` with the official image: see «Back Up with Docker» in [CLI Admin Tools](cli_tools.md).
- 🔒 If the hosted instance is blocked, its app shows the block page instead of Settings: ask your hosting provider for the archive. A hosting panel can still make one on a blocked instance ([Backups for Your Hosting Panel](hosting_providers.md#panel-backups)).
- 🖥️ On a host installation, the same steps with `pipenv run ./dev.py backup restore <archive>`, then a restart of the server by hand. From Settings › Backup, the server stops by itself: start it again yourself, unless something supervises it ([Who Starts LibreFolio Again](#supervisors)).

### ✋ By Hand: Unzip Before the First Start {: #by-hand }

Instead of a restore, unzip the archive into the data folder before the first start of LibreFolio, with the same image or a newer one. The start applies the pending migrations by itself.

```bash
# In the folder of docker-compose.yml, before the first start
unzip librefolio-backup-20261015-121500.zip -d LibreFolio-data
docker compose up -d
```

- 📂 The data folder must be empty, or not exist yet: if LibreFolio has already started on it, stop LibreFolio and move `LibreFolio-data` aside first. Nothing of other data may mix with the archive's.
- 🔎 Nothing checks the archive first: a damaged archive, or one from a newer LibreFolio, shows only when the start fails. A restore, from Settings › Backup or the command line, checks it on a copy before anything changes.
- 🧹 The `manifest.json` left in `LibreFolio-data/` is harmless: you can delete it.
- 🗝️ Without `secrets/`, LibreFolio creates a new instance key the first time it needs one. When you move your own installation, put its `secrets/` back into `LibreFolio-data/` before the first start, and the saved secrets stay readable.
- 📖 The steps for any installation, the host one included: «Use an Archive on Another Installation» in [CLI Admin Tools](cli_tools.md).

### ☁️ From Your Server to a Hosted Instance {: #to-a-hosted-instance }

1. **Make a backup** on your server: **Settings › Backup**, or `backup create` on the command line ([Make a Backup](#create)).
2. **Restore it on the hosted instance.** As one of its administrators, restore it yourself from **Settings › Backup** ([Restore from Settings › Backup](#restore-settings)), within the upload limit the card shows, if the instance has one ([The Upload Limit of a Restore](hosting_providers.md#restore-upload-limit)). Otherwise, or for a larger archive, hand it to whoever runs the hosted instance, as privately as you keep it: they restore it on its server with the same command, `backup restore`, then restart it ([Restore on This Installation](#restore)). The hosted instance must run the same version as yours, or a newer one.
3. **Sign in** there with your account of your own server, and the password it had when you made the backup.
4. **Enter again any secret plugin setting saved in the app**: the hosted instance keeps its own instance key. Email and the other options are the configuration of the hosted instance.

### ⛔ Never Backwards {: #never-backwards }

LibreFolio never takes a database back to an older version: use the version that made the archive, or a newer one. An older LibreFolio refuses an archive whose database carries a migration it does not know.

- 🏷️ `backup inspect` shows which version made the archive (`Made by LibreFolio <version>`), and **Settings › About** shows the version of an instance.
- ❌ `backup restore` refuses such an archive with `revision_unknown`, before anything changes.
- 🛑 By hand, an older LibreFolio does not start on such data: its log has `Failed to apply database migrations`, and Docker keeps restarting the container. Stop it with `docker compose down`.

Update the receiving LibreFolio first ([Updating LibreFolio](../user/installation.md#updating)), then restore. With Docker, the `latest` image is the newest release.

---

## 🧯 When Something Goes Wrong {: #troubleshooting }

### 🧾 The Check Refuses the Archive {: #check-refused }

`backup restore`, with or without `--dry-run`, ends a refusal with its code in parentheses, and changes nothing. Settings › Backup refuses the same archives and says why on its card, without the code: *The archive is damaged.* for `archive_damaged`, for instance.

| Code | Why | What to do |
| --- | --- | --- |
| `revision_unknown` | The archive comes from a newer LibreFolio | Update this one ([Never Backwards](#never-backwards)), then run the command again |
| `manifest_newer_format` | The archive format is newer than this LibreFolio reads | Update LibreFolio first |
| `checksum_mismatch`, `archive_damaged`, `missing_entry` | The archive is damaged, cut short, or was changed | `backup inspect` names the entries that differ. Copy the archive again from where you keep it, or use another one |
| `not_a_backup` | Not an archive LibreFolio wrote, such as a data directory zipped by hand | Put such a copy back [by hand](#by-hand), into an empty data directory |
| `no_space` | The copy needs more free space than the disk of the data directory has | Free some space: the archive unpacked, plus twice its database, plus 64 MB |
| `archive_unreadable` | The archive cannot be opened, most often because the server's user may not read it | With Docker and the official image, `sudo chown 1000:1000 <archive>` on the host gives it to that user |
| `restore_already_pending` | Another restore waits for the next start | Restart LibreFolio to apply it, or drop it with `backup pending --cancel` or **Cancel the restore** in Settings › Backup |

Two more messages:

- `❌ No file at <path>`: with Docker, give the path inside the container, `/app/backend/data/prod-docker/…`.
- `❌ The backup has no active administrator: after a restore nobody could manage the instance`, or the same in the report of Settings › Backup, whose confirmation then stays disabled: on the installation the backup comes from, make an active account administrator, then make a new backup.

Every code: «Refusals — what the codes mean» in [CLI Admin Tools](cli_tools.md).

One warning lets the restore go on, but read it before you confirm:

- `⚠️ Ledger totals differ from the backup's (<n> lines):`, or *Ledger totals differ from the backup's on 2 lines:* in the report of Settings › Backup: the cash of a broker or the quantity of a position in the copy, once up to date, is not the one the backup recorded. Transactions were lost, added or changed between the backup and the copy, by a migration that corrects data for instance. Read the lines that follow: each gives a broker's number, then a currency or an asset's number, with the backup's amount before the arrow and the copy's after it. The numbers are those in the addresses of the broker's and the asset's pages in the app, `/brokers/<id>` and `/assets/<id>`. Compare these lines with the instance the backup comes from. The warning never blocks the restore: whether you confirm it is up to you.

### 🔁 The Restore Does Not Go Through {: #restart-problems }

| What you see | Why | What to do |
| --- | --- | --- |
| `backup pending` ends with `(server_running)` | At the last start, another server process served the data directory: a worker started again on its own, or a second server | Restart the whole server, never one worker, and run one server per data directory |
| `backup pending` ends with `(instance_blocked)` | The hosting provider blocked the instance: a restore is never applied on a blocked instance | Nothing: the first start after the unblock applies it. `backup pending --cancel` drops it meanwhile |
| `backup pending` ends with `(other_data_directory)` | The server found its data directory under another path than the one the restore was confirmed for, such as a copy of the data directory | `backup pending --cancel`, or **Cancel the restore** in Settings › Backup, then restore the archive again: with `backup restore`, where the server runs |
| `backup pending` ends with `(backup_running)` | A backup was running at the last start | Nothing: the next start applies the restore |
| `backup pending` says the restore was rolled back, `(first_start_failed)` | The first start on the restored data did not complete | The data is as it was. The log of that start has the cause: fix it, then restore the archive again |
| … rolled back, `(swap_interrupted)` | The start that applied the restore was interrupted, and the next one undid it | Restore the archive again |
| … rolled back, `(swap_failed)` | The folders could not be moved into place | Make `sqlite/`, `custom-uploads/`, `broker_reports/` and `scenario_catalog/` real folders of the data directory, neither links nor separate mounts, then restore the archive again |
| … rolled back, `(stage_missing)` | The checked copy was gone or changed | Restore the archive again |
| A start stops, and its log says that another server applied the restore or serves the data directory | Two LibreFolio servers use the same data directory | Stop the other one, then start LibreFolio again: `backup pending` then tells whether the restore was kept |
| LibreFolio does not start, and its log has `The data directory is half restored` | Even putting the former data back failed, on a disk or permission error for instance | Fix the cause the log gives: every start tries again |
| `Failed to apply database migrations` after an unzip by hand | An archive from a newer LibreFolio, or a migration that fails: the log has the error | For a newer archive, `docker compose down`, then use the version that made it or a newer one ([Never Backwards](#never-backwards)) |

### 🖱️ What Settings › Backup Says {: #restore-settings-problems }

The window of the restart gives a reason in words where `backup pending` gives a code: the table says which one, and the row of that code in [The Restore Does Not Go Through](#restart-problems) says what to do. On the card, **Try again** reads the state of the restore again: to send an archive again, choose it again.

| What you see | Why | What to do |
| --- | --- | --- |
| After **Restore and restart**, the sign-in page, with no message | The restore worked: it ended every session. Only in the case of the next row does the sign-in page come although it did not | Sign in with an administrator of the backup, with the password the account had when the backup was made. If nobody remembers it: [After a Restore](#after-restore) |
| The sign-in page appeared, but once signed in the data is as before | The page could not read the outcome with its ticket (a reload of the page, more than an hour of waiting, or LibreFolio restarted from the command line rather than from the page), and LibreFolio runs without `JWT_SECRET` ([Keep Users Signed In After a Restart](index.md#session-persistence)): every start signs everyone out, so the page went to the sign-in page although the restore did not go through. The accounts and passwords of before still sign in | Open **Settings › Backup**: the card says *The last restore was rolled back on …*, or shows the restore waiting, with the reason; then see the row of that reason below. If the block page shows instead of the app, the hosting provider blocked the instance: the restore waits for the unblock |
| *LibreFolio has not come back yet. If nothing starts it again by itself, start it yourself: the restore is applied at that start.* | LibreFolio has not answered for a minute: nothing started it again, with no supervisor or one that starts it only after a failure ([Who Starts LibreFolio Again](#supervisors)), or its start is slow | If it is stopped, start it: `docker compose up -d` with Docker, or [start the server](cli_tools.md#start-the-server) on a host installation. The page goes on by itself once LibreFolio answers. On an instance someone hosts for you, ask them |
| The window keeps saying **LibreFolio is restarting**, without *LibreFolio has not come back yet*, while LibreFolio still answers, in another tab for instance | The request did not stop the server: the restore still waits for the next start, and `backup pending` shows it waiting | Restart LibreFolio yourself: `docker compose restart librefolio` with Docker, or stop the whole server and [start it](cli_tools.md#start-the-server) again. Its start applies the restore, and the page goes on by itself. On an instance someone hosts for you, ask them |
| **The restore did not go through**, with *The data is as it was before: …* | The restore was rolled back: *the first start after it did not complete* (`first_start_failed`), *the start that applied it was interrupted* (`swap_interrupted`), *its folders could not be moved into place* (`swap_failed`) or *its checked copy was gone* (`stage_missing`) | What the row of that code says. **Back to Backup** returns to the card, which says when the last restore was rolled back, and why |
| **The restore did not go through**, with *LibreFolio restarted, but the restore was not applied.* and the reason | A start left the restore waiting: *At the last start a backup was running…* (`backup_running`), *It was confirmed for another data directory…* (`other_data_directory`) or *At the last start another LibreFolio process was serving the data…* (`server_running`) | What the row of that code says. **Back to Backup** shows the restore waiting, with **Restart now and restore** and **Cancel the restore** |
| **The restore did not go through**, with *LibreFolio restarted, but the restore was not applied. The hosting provider blocked this instance: the restore waits until it is unblocked.* | The start found the instance blocked by its hosting provider (`instance_blocked`): a restore is never applied on a blocked instance | Settle it with the hosting provider: the first start after the unblock applies the restore. **Back to Backup** leads to the block page. Whoever runs the server can drop the restore meanwhile, with `backup pending --cancel` |
| *The archive is larger than this LibreFolio accepts (500 MB).* | The installation limits the archives uploaded for a restore with `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` (`backup_too_large`) | On your own installation there is no limit unless someone set one: raise it, or set it to `0`, then restart ([The Upload Limit of a Restore](hosting_providers.md#restore-upload-limit)). Or restore from the command line, which has no limit. On an instance someone hosts for you, ask them |
| Sending stops with *The server answered with an error: the server's log has the cause.* or *The server does not answer: check the connection and try again.*, and the log of LibreFolio has nothing about it | A proxy in front of LibreFolio refused the archive: Nginx takes only 1 MB by default | Let the proxy take archives as large as yours, with `client_max_body_size` in Nginx ([The Upload Limit of a Restore](hosting_providers.md#restore-upload-limit)), or restore from the command line |
| The card refuses the archive, such as *This file is not a LibreFolio backup.* or *The archive is damaged.* | The check refused it, as `backup restore` does | See its code in [The Check Refuses the Archive](#check-refused) |

### 🔑 After a Restore {: #after-restore }

| What happens | What to do |
| --- | --- |
| Nobody remembers the password an administrator had in the backup | Whoever runs the server sets a new one with `user reset`, or creates a reset link with `user reset-link` ([Reset a Password or Lock an Account](cli_tools.md#reset-a-password-or-lock-an-account)) |
| The sign-in page answers that an account is disabled: it was waiting for its email verification | An administrator clicks **Reactivate** on its row ([What Each Action Does](users.md#actions)), or deletes it so that its owner signs up again ([Delete an Account](users.md#delete)) |
| A link sent before the restore no longer works | Send a new invitation or password-reset link ([Users & Invitations](users.md)) |
| A secret plugin setting is reported as set but unreadable | The archive carries no instance key: enter the setting again |
| After a move, no email goes out | Set the email variables on this installation, then restart ([Email](email.md)) |

---

## 🔗 Related

- 🛠️ **[CLI Admin Tools](cli_tools.md)** — «Back Up the Instance»: every option and message of `backup create`, `inspect`, `restore` and `pending`, and «Back Up with Docker»
- 📂 **[Filesystem Structure](filesystem.md)** — The data directory, `secrets/`, and a copy made by hand
- 🐳 **[Installation with Docker](../user/installation.md)** — Installing LibreFolio, and updating it
- 👥 **[Users & Invitations](users.md)** — Reactivate or delete accounts, and send new links
- 📧 **[Email](email.md)** — The email variables, which no archive holds
- 📝 **[Environment Variables](configuration.md)** — «The Instance Key», and every option of `.env`
- 🏢 **[Hosting for Others](hosting_providers.md)** — [Backups for Your Hosting Panel](hosting_providers.md#panel-backups) and [The Upload Limit of a Restore](hosting_providers.md#restore-upload-limit)
- 🧑‍💻 For developers: **[Restoring a Backup](../developer/architecture/security.md#backup-restore)** — The swap, the journal, the rollback and the restart
