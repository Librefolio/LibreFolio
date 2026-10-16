# 🛠️ Command-Line Tools

`dev.py`, at the root of the project, runs the administration tasks: starting the server, managing users, maintaining the database and backing up the instance. Each section says when a command needs the server stopped.

!!! tip "Where to run the commands"

    - **Host installation**: in the Pipenv environment, with the `pipenv run` prefix used on this page, or after `pipenv shell`.
    - **Docker**: in the running container, with `docker compose exec librefolio python dev.py <command>` (from a source checkout, `./dev.py docker exec <command>`, which runs it as the server's user instead of root). No `pipenv run` there: the image installs the dependencies globally. User commands, `db current`, `db check`, `backup create`, `backup inspect` and `backup restore --dry-run` work there ([Back Up with Docker](#backup-docker)); `db upgrade` and `db downgrade` do not, as they need the server stopped ([Apply Migrations](#apply-migrations)). Development commands such as `test` are not part of the image ([details](docker_advanced.md#docker-exec)).

---

## 🖥️ Start the Server {: #start-the-server }

```bash
# Standard start, one worker
pipenv run ./dev.py server

# Size the workers to the CPUs (`auto` and `0` do the same)
pipenv run ./dev.py server --workers auto

# Or set the number of workers
pipenv run ./dev.py server --workers 4

# Listen on another port (default: PORT from .env, else 6040)
pipenv run ./dev.py server --port 8080

# Kill whatever already holds the port, then start
pipenv run ./dev.py server --force
```

- 🧮 More workers serve more requests at once: use them on any machine with more than one CPU. `auto` starts $\max(1,\ 2\,(n-1))$ workers on $n$ CPUs.
- ⏳ The server first builds the web interface and this documentation when they are missing or out of date, so the first start takes a few minutes. If the interface does not build, the server does not start.
- 🔑 A restart signs everybody out, unless `JWT_SECRET` is set in `.env` (see [Configuration](configuration.md)).

??? note "⚙️ Other server options — rarely needed"

    | Option | What it does |
    | --- | --- |
    | `--host HOST` | Address to listen on (default: `HOST` from the environment or `.env`, else `0.0.0.0`) |
    | `--data-dir PATH` | Use another data directory for this run, instead of `LIBREFOLIO_DATA_DIR` |
    | `--no-scheduler` | Start without the scheduled price and FX syncs |
    | `--rebuild`, `-r` | Rebuild the web interface even when it looks up to date |
    | `--debug`, `-d` | `DEBUG` logs and a debug build of the web interface |

    Short forms: `-w` for `--workers`, `-p` for `--port`, `-f` for `--force`. `--test`, `--coverage` and `--no-reload` are development options: `pipenv run ./dev.py server --help` lists them all.

---

## 👤 Manage Users

These commands write straight to the database, so they also work while the server is running.

In the app, administrators manage the other accounts and the invitations from the **Users** tab of **Settings**: see [Users & Invitations](users.md). The commands below need no browser: use them on a headless server, or to go past the [user limit](configuration.md#user-limit).

### ➕ Create and List Users

```bash
# Create an administrator account
pipenv run ./dev.py user create <username> <email> <password>

# Create a regular account
pipenv run ./dev.py user create <username> <email> <password> --role user

# List all users: ID, username, email, active, administrator
pipenv run ./dev.py user list
```

- 👑 `user create` makes an **administrator** unless you add `--role user`, which makes a regular account. People can also create their own account: with **Register here** on the login page while **Registration** is **Open** (on a new instance, also until its first account exists), or with an [invitation link](#invite) (see [Who Can Sign Up](settings.md#registration)).
- 🔒 The password needs at least 8 characters, with an upper-case letter, a lower-case letter, a digit and a symbol.
- 📏 When the instance has reached its [user limit](configuration.md#user-limit), `user create` warns `The instance is at its limit (LIBREFOLIO_MAX_USERS: 5 of 5 places taken): the command line creates the account anyway`, then creates it: the command line is how you go past the limit.

### ✉️ Invite Someone {: #invite }

```bash
# An invitation link for a regular account
pipenv run ./dev.py user invite

# An invitation for an administrator, with a note of whom it is for
pipenv run ./dev.py user invite --admin --email anna@example.com
```

The command prints a link that works once, for 7 days. Send it to the person: they open it and create their account, with the username, email and password they choose ([what they see](../user/getting-started.md#invitation-link)).

- 👑 `--admin` makes the new account an administrator; without it, the account is a regular one.
- ✉️ `--email` is only a note of whom the invitation is for: the person can sign up with another address.
- 🌐 With [`LIBREFOLIO_PUBLIC_URL`](configuration.md#accounts) set, the link is complete, such as `https://librefolio.example.com/invite#token=…`. Without it, the command prints the path only, `/invite#token=…`, and reminds you to put the address of your server in front of it, such as `http://192.168.1.10:6040`. If the variable is set but is not an `http://` or `https://` address, the reminder says `LIBREFOLIO_PUBLIC_URL is not valid (…)` instead, with the reason.
- 🔒 The secret part of the link comes after `#`: browsers never send that part to the server, so it does not end up in server or proxy logs. Send the link whole.
- 🚪 Invitations work while **Registration** is **Open** or **By invitation**. While it is **Closed**, the command stops with the error `Registration is disabled: invitations cannot be created` and exits with `1`, and the links already sent do not work either.
- 📏 An invitation takes a place of the [user limit](configuration.md#user-limit) until it is used or revoked, or expires. At the limit, the command warns, then creates the invitation anyway.
- ⏳ There is no command to cancel an invitation: a link nobody used stops working after 7 days. An administrator can revoke it sooner with **Revoke** in the [Users](users.md#open-invitations) tab, or through the API: `GET /api/v1/users/invites` lists the pending invitations, `DELETE /api/v1/users/invites/<id>` revokes one.

### 🔑 Reset a Password or Lock an Account

```bash
# Set a new password (same rules as above)
pipenv run ./dev.py user reset <username> <new_password>

# Lock an account out, then let it back in
pipenv run ./dev.py user deactivate <username>
pipenv run ./dev.py user activate <username>
```

- ⏱️ A reset ends the sessions already open: every device signed in to the account is signed out at its next request. To lock someone out for good, deactivate the account: it is refused from its next request, and activating it again does not bring its old sessions back.
- 👑 `deactivate` refuses the last active administrator: it stops with the error `User '<username>' is the last active administrator: promote or activate another administrator first` and exits with `1`.
- 📏 When the instance has reached its [user limit](configuration.md#user-limit), `activate` of a deactivated account warns `… the command line reactivates the account anyway`, then reactivates it.
- 💬 The app's **Forgot Password?** screen shows this command for both installations: `docker compose exec librefolio python dev.py user reset …` for Docker, and `./dev.py user reset …` for a host installation, to run after `pipenv shell` or with `pipenv run` in front.

### 🔗 Send a Password-Reset Link {: #reset-link }

```bash
pipenv run ./dev.py user reset-link <username>
```

Instead of choosing a new password for someone with `user reset`, send them this link: they open it and choose the new password themselves ([what they see](../user/getting-started.md#password-reset-link)).

- ⏱️ The link works once, for 30 minutes. A new link for the same account cancels the earlier ones.
- 🚪 Once the new password is set, every device signed in to the account is signed out, as with `user reset`. Creating the link signs nobody out.
- 🌐 As for [invitations](#invite), the link is complete when `LIBREFOLIO_PUBLIC_URL` is set, and the path only (`/reset-password#token=…`) when it is not.

### 👑 Grant or Remove Administrator Rights

```bash
pipenv run ./dev.py user promote <username>
pipenv run ./dev.py user demote <username>
```

`demote` refuses the last active administrator: it stops with the error `User '<username>' is the last active administrator: promote another user first` and exits with `1`. A demotion signs the account out of every device.

### 🧭 Restart the Guides of a User {: #reset-onboarding }

```bash
# Every guide, the Welcome setup included
pipenv run ./dev.py user reset-onboarding <username>

# One guide only
pipenv run ./dev.py user reset-onboarding <username> --flow intro_tour
```

The next time the user opens LibreFolio, the Welcome setup and the guides start again, as on their first visit; their data and preferences stay as they are. `--flow` restarts one guide only: `pipenv run ./dev.py user reset-onboarding --help` lists the names, such as `welcome`, `intro_tour` or `import_guide`.

---

## 🗄️ Maintain the Database

### ⬆️ Apply Migrations {: #apply-migrations }

Every start of the server applies the pending migrations by itself, so you rarely need this. To do it by hand, **stop the server** first: `db upgrade` refuses to run while the server answers on the configured port.

```bash
# Apply pending migrations
pipenv run ./dev.py db upgrade

# Show the migration the database is at
pipenv run ./dev.py db current

# Look for missing CHECK constraints: changes nothing, exits with 1 if any
pipenv run ./dev.py db check

# Upgrade and check another database file, such as a copy
pipenv run ./dev.py db upgrade /path/to/copy/app.db
pipenv run ./dev.py db check /path/to/copy/app.db
```

- 📄 Without a path, the commands use the configured database. A path names another SQLite file: a relative one starts at the project root, wherever you run the command from. The file must exist, except for `db upgrade`, which creates it (folder included) and brings it up to date.
- 🐳 In Docker, the path is inside the container, where `LibreFolio-data/` is `/app/backend/data/prod-docker` (the database is `sqlite/app.db` in it). `db current` and `db check` work in the running container: `docker compose exec librefolio python dev.py db current <path>`. `db upgrade` and `db downgrade` need the server stopped (`docker compose stop librefolio`), then a one-off container: `docker compose run --rm librefolio python dev.py db upgrade <path>` ([details](docker_advanced.md#docker-exec)).

### 🩹 Post-Migration Fixes {: #post-migration-fixes }

Right after the migrations, every start also runs the **post-migration fixes**: repairs that a migration cannot make. Usually there is nothing to do. The log (the server output, also saved in `logs/`) may show:

- ✅ `Post-migration fixes applied and verified`: a repair was made. On a large database that start is slower, once.
- ⚠️ `Post-migration fix failed`: the database was left as it was and the server started normally. The warning gives the error and the copy of the database kept next to it until you delete it, such as `app.db.pre-autoincrement-20261008T101500Z.bak`. The fix is tried again at the next start.
- 🩺 `Post-migration fixes skipped`: the copy could not be made, or the database fails SQLite's integrity check. Nothing was changed.
- 🔗 `Foreign key violations already in the database, left as they are`: the database holds references to rows that no longer exist, listed in the warning. The fixes leave them alone and still run: a fix fails only on a broken reference it would add itself.

The empty file `app.db.post-migration.lock`, next to the database, makes the runs take turns when several workers start together: leave it in place.

The first fix, **`autoincrement`**, makes sure the id of a deleted user, broker, asset, transaction, FX conversion route or asset event is never given to a new one. While converting a database, it deletes the report folders of brokers that no longer exist, so that a new broker cannot inherit them.

The second fix, **`orphan_pair_halves`**, repairs, once, the transfers that an earlier broker deletion left without their other half on the brokers that remain:

- 📈 Securities received from the deleted broker become an opening position at their transfer cost, starting on the transfer date. That broker's capital then counts them at that cost instead of their market value on arrival, so its gain also counts what they gained before the transfer. When no cost was recorded, they stay without one and the app reports an acquisition without a purchase cost: enter the cost in the transaction.
- 💶 Cash transfers with the deleted broker become deposits or withdrawals: capital and gain do not change.
- 📤 Securities sent **to** the deleted broker: right after the fixes, at the same start, each of these transfers becomes an adjustment that takes the securities out of the sending broker at their average cost there — capital that leaves, not a loss. The log has one line for each (`Lone transfer leg converted at its Auto cost`). When that cost needs an exchange rate LibreFolio does not have, the transfer stays as it is (`Lone transfer leg left as it is`) and the next start tries again. On a database that fails SQLite's quick check, every one of them is left as it is (`Lone transfer legs left as they are: the database failed its quick check`). If the whole step fails (`Lone transfer legs could not be converted; starting normally`), nothing is changed and the server starts anyway.

The fix **`event_types`** repairs, once, the asset events stored with a type LibreFolio does not know, such as `dividend` or `dividendo` written by hand in a CSV file. Until now such an event made the whole list of that asset's events fail to load, so none of them was shown:

- ✅ A type that only differs in letter case or spaces (`dividend`, ` Split `) is corrected.
- 🗑️ An event whose type is still unknown is deleted. A transaction linked to it stays, without its linked event: link it again to the right event if you need to.

??? tip "⌨️ Run the fixes by hand — to preview them or retry a failed one"

    **Stop the server** first (the script does not check it), then run from the project root:

    ```bash
    # Preview: report what would be fixed, change nothing
    pipenv run python -m backend.app.db.post_migration --dry-run

    # Apply the fixes
    pipenv run python -m backend.app.db.post_migration
    ```

    The script prints each fix as `clean` (nothing to do), `would_apply` (dry run), `applied` or `failed`, with the orphan broker folders, a kept copy and any error, then one line for each transfer of securities sent to a deleted broker (`Lone transfer leg …`), and exits with `1` when something failed. `--db PATH` and `--data-dir PATH` point it at another database or data directory.

    To see what `orphan_pair_halves` will change on your database, preview it before the first start of the new version: `--dry-run` prints `Fix orphan_pair_halves: would_apply` when there is something to repair, and a warning lists the transactions by id, grouped by conversion (such as `TRANSFER->ADJUSTMENT`), with those that will stay without a cost and the transfers of securities sent to a deleted broker. Those transfers get a line each after the fixes: the average cost each would leave at (`would become an ADJUSTMENT at … per unit`), or why it would stay a transfer. The script also prints, on the console, what the server would log: the warning and, on a real run, one line per transaction changed (with `LOG_LEVEL` at `INFO`, the default). It writes no log file: keep its output if you want a record of a repair made by hand.

🔗 How the fixes work inside: [Database Schema — Post-migration fixes](../developer/architecture/database/index.md#post-migration-fixes).

### 🔧 Add Missing Global Settings

```bash
pipenv run ./dev.py user init-settings
```

Every start adds the missing [Global Settings](settings.md) with their default values; this command does the same without starting the server, and never changes a value already set.

### 🧹 Reset the Database

```bash
pipenv run ./dev.py db create-clean
```

!!! warning "All data is lost"

    `db create-clean` deletes the database and creates an empty one. Like `db upgrade`, it refuses to run while the server is up. Uploaded files and broker reports stay on disk: see [Database Initialization & Reset](host_installation.md#database-reset).

---

## 💾 Back Up the Instance {: #backup }

`backup create` puts the whole instance in one zip archive, while the server keeps running: the database, the uploaded files, the broker reports and your own stress scenarios. `backup inspect` checks an archive and shows what it holds, and `backup restore --dry-run` tries a restore of it on a copy, leaving the instance as it is. To copy the data directory by hand instead, see [Backup](filesystem.md#backup).

### 📦 Create an Archive

```bash
# Write an archive into <data dir>/backups/
pipenv run ./dev.py backup create

# Write it into another folder, which must already exist
pipenv run ./dev.py backup create -o /mnt/nas/librefolio/

# Or give the archive a name of your own
pipenv run ./dev.py backup create -o /mnt/nas/librefolio/before-update.zip
```

- 🟢 The server keeps working, and writing, during the backup: the database is copied with SQLite's `VACUUM INTO`, a consistent snapshot, then SQLite's integrity check and foreign-key check run on the copy.
- 🏷️ The archive is named after the moment the backup starts, in UTC: `librefolio-backup-20261015-121500.zip`. In a folder that already holds a file with that name, after two backups in the same second for instance, it becomes `librefolio-backup-20261015-121500-2.zip`, then `-3`, and so on: an archive never replaces a file.
- 📁 `--output` (`-o`) is checked before the backup starts, and the command must be able to write there. An existing folder receives the archive under its default name. Any other path is the archive's file, even one that ends with `/`: a folder that does not exist yet becomes the archive's name. That file must not exist yet, and its name is never changed. Its missing folders are created only when the archive is moved there, so a failed backup leaves no empty folder behind. Prefer absolute paths: a relative one starts at the project root, wherever you run the command from.
- 💽 Before writing anything, the command checks the free space where it builds the archive, in the data directory's `backups/` folder, even with `-o`: about twice the size of the database, plus the files, plus a small margin. When it is short, or when the disk or a quota fills up during the backup all the same, the command stops with `❌ Backup failed (backup_no_space): not enough free space`. When `-o` is on another disk, the space there is checked once the archive is built and its size known.
- 🛟 If the finished archive cannot go to `-o` (a file with that name appeared meanwhile, its folders cannot be created, the other disk is short of space, a write error), it is put in `backups/` instead, and the command exits with `1`. A move that fails half-way leaves no partial file behind.
- 🚦 One backup runs at a time: while another one is running, the command stops and asks you to try again when it ends.
- ✅ It ends with `✅ Backup written: <path>`, the size and the time taken, any warnings, and a reminder that the archive holds every user's data. It exits with `0` when the archive is where you asked, warnings included, and `1` otherwise.
- 🔒 The archive is not encrypted and has no password: LibreFolio writes it so that only its owner can read and write it (`0600`). Keep it, and every copy, as private as the data directory.
- 🗑️ LibreFolio never deletes the archives it puts in `backups/`: they stay there until you remove them. That folder is on the same disk as the data, so copy them to another disk, a NAS or off-site, or write them there directly with `-o`.
- 🔗 Keep `backups/` a real folder, never a link to a NAS or another disk: every archive is built inside it first, even with `-o`. A link, or a file, in its place stops the command with `❌ <data dir>/backups is not a plain folder (a link, or a file): …`.
- 🧪 `backup --test-db create` backs up the test data directory instead: a development option.

??? note "⚠️ Warnings and errors — what the messages mean"

    **Warnings**: the archive is written all the same.

    - `The database failed its integrity check` or `The database has foreign-key violations`: the archive keeps the database as it is, and `backup inspect` shows the integrity result.
    - `Left out (<n>): links, special files, files or folders that could not be read, or files removed during the backup`, followed by the entries, at most 50: they are not in the archive. Links are never followed, even when a whole folder such as `custom-uploads/` is a link to another disk.

    **Not where you asked**: the archive is written, and the command exits with `1`.

    - `⚠️ <reason>: the archive was written to <path> instead`, followed by the usual lines: `-o` could not take the finished archive, so it is in `backups/`. Move it where you want it.
    - `❌ <reason>: the archive stays in <path>. Move it within the hour: the next backup after that removes it.`: `backups/` could not take it either. It is still in the backup's work folder, inside `backups/.jobs/`, which the first backup started after that hour removes: move the archive out before then.

    **Errors**: no archive is written, and the command exits with `1`.

    - `❌ No data directory at <path>` or `❌ No database at <path>: nothing to back up`: the command backs up the [data directory](filesystem.md) LibreFolio is configured with; check `LIBREFOLIO_DATA_DIR`.
    - `❌ <path> already exists: choose another name or folder`, `❌ <path> is not a folder: choose another path` (a file stands where the path needs a folder) or `❌ cannot write into <folder>: choose another folder, or run the command as a user who can`: `-o` cannot receive the archive. The backup has not started, and nothing was created.
    - `❌ <data dir>/backups is not a plain folder (a link, or a file): …`: make `backups/` a real folder again. `❌ The backup could not run in <data dir>/backups: <reason>`: the command could not prepare its work folder there, for example because it cannot write into the data directory.
    - `❌ Backup failed (backup_no_space): not enough free space`: the free space was short at the start, or the disk or a quota filled up during the backup, even in the middle of a file. Free some space on the disk of the data directory.
    - `❌ Backup failed (backup_failed): the cause is in the log above`: any other failure. One of them is a file that fails while it is being copied into the archive, such as a read error in the middle of the file: part of a file cannot be taken back out of a zip, so the whole backup stops. A file that fails before its copy starts is left out with the warning above instead.

### 🗂️ What the Archive Holds

The archive has the layout of the data directory, and holds only:

| Entry | What it is |
| --- | --- |
| `manifest.json` | The description of the archive, see below |
| `sqlite/app.db` | The copy of the database |
| `custom-uploads/` | The files uploaded in the app |
| `broker_reports/` | The broker reports |
| `scenario_catalog/` | Your own stress scenarios, if you added any |

Everything else stays out: `secrets/`, `logs/`, `scheduler_state.json`, the `backups/` folder itself, the `.librefolio-production-data` marker, and SQLite's working files next to the database: `app.db-wal`, `app.db-shm`, `app.db.post-migration.lock` and the `.bak` copies of the [post-migration fixes](#post-migration-fixes). The copy of the database already holds what was waiting in `app.db-wal`. Symbolic links and special files are never followed nor archived.

!!! warning "🔑 The instance key is not in the archive"

    The archive leaves out `secrets/`, which holds the [instance key](configuration.md#instance-key). Back it up separately, as [Filesystem Structure → Backup](filesystem.md#backup) explains, and keep the copy as private as the archives. Before you start LibreFolio on the data of an archive, put `secrets/` back with it: without its key, what LibreFolio encrypted can no longer be read.

??? info "📋 `manifest.json` — what it records"

    - the format, `librefolio-backup`, and its version;
    - the LibreFolio version that made the archive, how (`cli` for this command, `ui` for the web interface, `panel` for a [hosting panel](hosting_providers.md#panel-backups)) and when, in UTC;
    - the database: its migration (Alembic) revision, the result of SQLite's integrity check, the number of foreign-key violations and the rows in each table;
    - every entry, the database first, with its path, its size and its SHA-256;
    - whether the instance key is included: it is not.

### 🔍 Check an Archive

```bash
# Check every entry against the manifest, and show what the archive holds
pipenv run ./dev.py backup inspect /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip

# Faster: compare the entry names with the manifest, without reading the entries
pipenv run ./dev.py backup inspect /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --no-verify
```

- 🟢 It works on any archive, with the server running or stopped, and needs no data directory. As with `-o`, a relative path starts at the project root.
- 📋 It shows who made the archive and when (`Made by LibreFolio <version> (cli) on <date> UTC`), the database's migration revision, size and integrity check, its rows and tables, the number and size of the files, and whether the instance key is included.
- 🔎 It compares the size and SHA-256 of every entry with the manifest, and ends with `✅ Every entry matches the manifest`. `--no-verify` compares only the entry names, without reading the entries, and ends with `ℹ️ The entry names match the manifest; their contents were not read (--no-verify)`.
- ❌ It exits with `1` when entries are missing, differ from the manifest or are not in it (it names the first five of each), and when the file is not an archive it can read: the message then ends with a code, such as `archive_unreadable` (not a zip file, or one cut short), `manifest_missing`, `manifest_unknown_format` (not a LibreFolio backup) or `manifest_newer_format` (made by a newer LibreFolio: check it with that version or a newer one).

### 🧪 Try a Restore on a Copy {: #backup-restore-dry-run }

```bash
# Check an archive for a restore, on a copy: the instance stays as it is
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --dry-run
```

`backup restore --dry-run` unpacks the archive into a copy, brings it up to date and checks it, then tells you what a restore would do. The copy is made in the data directory, in `.restore/stage/<id>/`, and removed at the end: the database and the files of the instance are never touched, so the server can keep running. This version only checks: without `--dry-run`, the command stops with `❌ Only --dry-run is available for now: it checks the archive on a copy and leaves the instance as it is`.

The check goes through five steps, and stops at the first one that refuses the archive:

1. **A LibreFolio archive.** Only an archive LibreFolio wrote, with its `manifest.json`, is accepted: a data directory zipped by hand is not. Every entry is checked before a byte is written: the manifest lists it, it is a plain file (not a folder, a link or an encrypted entry), its name appears only once, even ignoring upper and lower case, its size is the one in the manifest, and the whole fits in the free space.
2. **Unpacked.** Each entry is written into a new file of the copy, never through a link nor over another file, and its SHA-256 is compared with the manifest's.
3. **The revision decides.** The migration (Alembic) revision of the database, given by the manifest and confirmed by the database itself:
    - this LibreFolio's own revision: the database is restored as it is;
    - an older one: the copy is upgraded to this LibreFolio's revision, in a process of its own, which is stopped if it lasts more than an hour;
    - one this LibreFolio does not know, most likely from a newer version: refused with `revision_unknown`. Update LibreFolio first: a database is never downgraded.

    Then the [post-migration fixes](#post-migration-fixes) run on the copy, as at every start.

4. **Checked before and after.** Before the upgrade, the copy passes SQLite's integrity check and holds exactly the rows the manifest counted. After it, the copy passes the integrity check again, at this LibreFolio's revision. A migration may change data, so rows that changed are a warning, not a refusal, and so are broken references (foreign keys), kept as they are.
5. **Administrators.** The report names the active administrators of the backup. Without any, the restore is blocked: nobody could manage the instance after it.

It shows the steps as it goes (`… checking`, `… unpacking`, `… upgrading`, `… verifying`), then its report:

- 📦 Who made the archive and when (`Made by LibreFolio <version> (<how>) on <date> UTC`), and what a restore does with the database: `this LibreFolio's own: restored as it is`, or `upgraded on the copy to <revision> (<n> migrations)`, followed by each migration with the first line of its description.
- 🩹 The post-migration fixes that changed something on the copy, if any.
- 🔢 The rows, the tables and the size of the database, then the tables whose rows the upgrade changed, as `<table> (<before> → <after>)`, with `—` for a table that did not exist.
- 📁 The number and size of the files, and whether the instance key is included.
- 👑 The administrators, and what a restore will mean for everyone: `After a restore you sign in with one of them, with the password of then; every session open now ends.`
- ⚠️ The warnings, which let a restore go on: `The upgrade changed the rows of some tables (listed above)`, `The backup's database has broken references: they are kept as they are`, or `The upgrade added broken references to the copy`.
- ⛔ The blocker, which forbids it: `❌ The backup has no active administrator: after a restore nobody could manage the instance`.

It ends with `✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed.` and exits with `0`. It exits with `1` when the archive is refused or the restore blocked. A refusal is one line, the reason followed by a code in parentheses, such as `❌ The file is not a LibreFolio backup (not_a_backup)`, and nothing of the copy is left.

- 💽 The copy needs free space on the disk of the data directory: everything the archive holds once unpacked, plus twice the size of its database for the upgrade, plus 64 MB. `backup inspect` shows those sizes; the archive itself is read where it is, never copied. When the space is short, the check stops before it unpacks anything, with the number of bytes it needs (`no_space`); a disk that fills up during the check stops it too.
- 🚦 One archive is checked at a time: while another check runs, the command stops with `❌ Another archive is being checked (from the web interface or another command): try again when it ends`.
- 🆕 It never uses the database of the instance: any installation can check an archive, a new one included, as long as its data directory exists (otherwise `❌ No data directory at <path>`). As with `-o`, a relative path starts at the project root.
- 🔗 Keep `.restore/` and `.restore/stage/` real folders: a link, or a file, in their place stops the command with `❌ <path> is not a plain folder (a link, or a file): the copy is made in a folder of the data directory`.

??? note "❌ Refusals — what the codes mean"

    | Code | Why the archive is refused |
    | --- | --- |
    | `not_a_backup` | Not a zip, or a zip without the manifest LibreFolio writes, such as a data directory zipped by hand |
    | `archive_unreadable`, `archive_damaged` | The file cannot be read, or the zip is damaged |
    | `manifest_newer_format` | The archive format is newer than this LibreFolio reads: update LibreFolio first |
    | `manifest_invalid`, `manifest_unreadable`, `manifest_too_large` | The manifest is damaged or not valid |
    | `unexpected_entry`, `missing_entry` | The archive holds an entry its manifest does not list, or lacks entries the manifest lists |
    | `duplicate_entry` | An entry appears twice, even when only the case of its name changes, or stands where the folder of another entry must be |
    | `not_a_file`, `encrypted_entry`, `unsupported_entry` | An entry is a folder or a link, is encrypted, or uses a compression LibreFolio does not write |
    | `too_many_entries` | The archive holds more than 500,000 entries |
    | `checksum_mismatch` | An entry's size or SHA-256 differs from the manifest: the archive is damaged or was changed |
    | `no_space` | Not enough free space for the copy |
    | `stage_failed` | The copy could not be written: the error printed just above gives the cause |
    | `database_damaged` | The backup's database fails SQLite's integrity check, before or after the upgrade |
    | `manifest_mismatch` | The backup's database is not the one its manifest describes |
    | `revision_missing` | The backup's database records no migration revision |
    | `revision_unknown` | The backup comes from a newer LibreFolio, or not from this one: update LibreFolio, then check it again |
    | `upgrade_failed` | The upgrade of the copy failed or lasted more than an hour (the error printed just above gives the cause), or did not reach this LibreFolio's revision |
    | `post_migration_failed` | A post-migration fix failed on the copy: the error printed just above gives the cause |
    | `head_unknown` | This LibreFolio cannot read its own migration scripts |

### 🚚 Use an Archive on Another Installation

`backup restore` only checks an archive for now. To start LibreFolio on the data of an archive, by hand:

1. **Stop LibreFolio** on the installation that receives the data.
2. **Unzip the archive into an empty [data directory](filesystem.md)** (`LibreFolio-data/` with Docker Compose): if it holds anything, move it aside first. Nothing of the old data may mix with the archive's, not even SQLite's `app.db-wal` and `app.db-shm`.
3. **Put `secrets/` back** in the data directory, from the copy you saved separately.
4. **Start LibreFolio**, the version that made the archive or a newer one: the pending migrations run by themselves at start.

- 🧪 Before step 1, check the archive on the installation that receives it, with `backup restore <archive> --dry-run` ([Try a Restore on a Copy](#backup-restore-dry-run)): without changing anything, it tells you whether that LibreFolio can take the archive, which migrations its start will apply, and which administrators you will sign in with.
- ⛔ LibreFolio never downgrades a database: an archive made by a newer version needs that version or a newer one, and an older one does not start on it. `backup inspect` shows which version made the archive, and `backup restore --dry-run` refuses such an archive with `revision_unknown`.
- 🧹 The `manifest.json` left at the root of the data directory is harmless: you can delete it.
- 👤 With Docker, the container gives the data directory to its user at every start, so the owner of the unzipped files does not matter. On a host installation, unzip as the user that runs LibreFolio, so that the files belong to it.

### 🐳 Back Up with Docker {: #backup-docker }

```bash
# Write an archive: on the host, it appears in ./LibreFolio-data/backups/
docker compose exec librefolio python dev.py backup create

# Check it, with its path inside the container
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip

# Try a restore of it on a copy: the instance stays as it is
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip --dry-run
```

- 👤 `docker compose exec` runs as root: the command switches to the owner of the data directory, so everything it writes belongs to the server's user. If it cannot switch, it stops and asks you to run it as that user: `docker compose exec --user <uid>:<gid> librefolio python dev.py backup create`, with the numbers from the message.
- 📂 `-o` and the archives of `inspect` and `restore` are paths inside the container, where the data directory is `/app/backend/data/prod-docker`. To check an archive that is on the host, copy it into `LibreFolio-data/` first, such as into `LibreFolio-data/backups/`. To write the archive elsewhere than `LibreFolio-data/backups/`, use a folder mounted from the host that the server's user can write to: anywhere else, it stays inside the container and is lost when the container is recreated.
- 🔑 `restore` also reads the archive as the server's user: an archive that `backup create` wrote is fine, but one you copied in yourself must be readable by that user, or the check stops with `archive_unreadable`. With the official image, `sudo chown 1000:1000 <archive>` on the host gives it to that user.
- 🔒 On the host, the archives belong to the container's user, and only that user can read them: if your host user is another one, copy them with `sudo cp -a`.
- 💻 From a source checkout, `./dev.py docker exec backup create` does the same.

---

## 📋 Full Command Tree

```bash
# Every command, by category
pipenv run ./dev.py --help

# The options of one command
pipenv run ./dev.py server --help
```

??? info "👩‍💻 Developer and documentation commands"

    - **Frontend**: `pipenv run ./dev.py front build`, `front dev`, `front check` — see [Frontend Development](../developer/frontend/index.md)
    - **Testing**: `pipenv run ./dev.py test all` — see [Test Walkthrough](../developer/test-walkthrough/index.md)
    - **API Client**: `pipenv run ./dev.py api sync` — see [API Overview](../developer/api/overview.md)
    - **i18n**: `pipenv run ./dev.py i18n audit` — see [Internationalization](../developer/frontend/i18n.md)
    - **Documentation**: `pipenv run ./dev.py mkdocs deploy` publishes this documentation to GitHub Pages; `pipenv run ./dev.py mkdocs gallery` regenerates its screenshots with Playwright on a test server (`--no-populate` keeps the current test data).

    The full developer toolkit is in the [Developer Workflow Guide](../developer/dev_workflow.md).
