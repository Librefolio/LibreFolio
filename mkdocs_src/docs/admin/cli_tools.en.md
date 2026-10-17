# 🛠️ Command-Line Tools

`dev.py`, at the root of the project, runs the administration tasks: starting the server, managing users, maintaining the database and backing up the instance. Each section says when a command needs the server stopped.

!!! tip "Where to run the commands"

    - **Host installation**: in the Pipenv environment, with the `pipenv run` prefix used on this page, or after `pipenv shell`.
    - **Docker**: in the running container, with `docker compose exec librefolio python dev.py <command>` (from a source checkout, `./dev.py docker exec <command>`, which runs it as the server's user instead of root). No `pipenv run` there: the image installs the dependencies globally. User commands, `db current`, `db check`, `backup create`, `backup inspect`, `backup restore`, `backup decrypt` and `backup pending` work there ([Back Up with Docker](#backup-docker)); `db upgrade` and `db downgrade` do not, as they need the server stopped ([Apply Migrations](#apply-migrations)). Development commands such as `test` are not part of the image ([details](docker_advanced.md#docker-exec)).

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
- ⏹️ Ctrl+C stops the server cleanly: `dev.py` gives it up to the [shutdown budget](configuration.md#shutdown) plus 2 seconds to stop (10 seconds by default), then ends it; a second Ctrl+C ends it at once. A SIGTERM sent to `dev.py` alone, by a process supervisor for example, gets the same wait: `dev.py` passes it on to the server.

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

In the app, administrators manage the other accounts and the invitations from the **Users** tab of **Settings › Administration**: see [Users & Invitations](users.md). The commands below need no browser: use them on a headless server, or to go past the [user limit](configuration.md#user-limit).

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
- 🔒 The password follows the same rules as in the app and the API: at least 8 characters, with an upper-case letter, a lower-case letter, a digit and a symbol. Letters and digits of any alphabet count, such as `É` or `é`; a symbol is any character that is neither a letter, a number nor a space, such as `!`, `_` or `€`. A password that misses a rule changes nothing: the command prints `Password does not meet security requirements:` and one line per rule missed, each starting with the rule's code, such as `digit: the password must contain a digit`, then exits with `1`.
- 🔤 A username cannot contain `@`: at sign-in, LibreFolio reads anything with an `@` as an email address. Such a username changes nothing: the command stops with the error `A username cannot contain @: the sign-in reads it as an email address` and exits with `1`. Spaces, accented letters and signs such as `.`, `_`, `-` or `+` are fine. The command also stops, with `Username already taken`, on a username another account has, and, with `Email already registered`, on an address another account has, or that is another account's username (see [`user set-email`](#set-email)), in any capitals.
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
- 🔗 A reset also cancels any password-reset link still open for the account, whoever created it.
- 👑 `deactivate` refuses the last active administrator: it stops with the error `User '<username>' is the last active administrator: promote or activate another administrator first` and exits with `1`.
- 📏 When the instance has reached its [user limit](configuration.md#user-limit), `activate` of a deactivated account warns `… the command line reactivates the account anyway`, then reactivates it.
- 📬 With email verification on, `activate` lets an account that waits for its email in at once — with no limit warning while its link is live, since its place is already counted — and `deactivate` ends its wait: either way, the verification links it was sent stop working. See *Email Verification* in [Email](email.md).
- 🏁 On the [initial administrator](configuration.md#initial-admin) still waiting for its setup link, `reset` and `activate` work as on any account: they set it up without its link. Either one ends the wait for good: its setup links stop working, the one of `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` included, and neither [`user setup-link`](#setup-link) nor a new `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` gives it another one. `activate` alone leaves an active account whose password nobody knows, until `reset` or a [reset link](#reset-link) gives it one; `reset` alone leaves it inactive, until `activate`.
- 💬 The app's **Forgot Password?** screen shows this command for both installations: `docker compose exec librefolio python dev.py user reset …` for Docker, and `./dev.py user reset …` for a host installation, to run after `pipenv shell` or with `pipenv run` in front. When your instance can email a reset link, the screen shows the email form first and keeps the commands in a panel closed by default ([Forgotten Passwords](email.md#forgot-password)).

### 🔗 Send a Password-Reset Link {: #reset-link }

```bash
pipenv run ./dev.py user reset-link <username>
```

Instead of choosing a new password for someone with `user reset`, send them this link: they open it and choose the new password themselves ([what they see](../user/getting-started.md#password-reset-link)).

- ⏱️ The link works once, for 30 minutes. A new link for the same account cancels the earlier ones; a change of the account's password or email address — in the user's Profile, or with `user reset` or `user set-email` — cancels them all.
- 🚪 Once the new password is set, every device signed in to the account is signed out, as with `user reset`. Creating the link signs nobody out.
- 🌐 As for [invitations](#invite), the link is complete when `LIBREFOLIO_PUBLIC_URL` is set, and the path only (`/reset-password#token=…`) when it is not.

### 🔁 A New Setup Link for the Initial Administrator {: #setup-link }

```bash
pipenv run ./dev.py user setup-link
```

When LibreFolio created the administrator from `LIBREFOLIO_ADMIN_EMAIL` at its first start ([The Initial Administrator](configuration.md#initial-admin)) and nobody has used its setup link yet, this command prints a new one: the administrator opens it, chooses the password and is signed in. Use it when the link has expired or got lost.

- ⏱️ The link works once, for 72 hours. The setup links issued before stop working, the one of `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` included.
- 📮 A new address for the waiting administrator — `LIBREFOLIO_ADMIN_EMAIL` changed before a restart, or [`user set-email`](#set-email) — stops its setup links, which went to the old address. The administrator still waits: this command gives it a link for the new address. The same address with other capitals of the letters A to Z is no change, and the link keeps working.
- 🔚 Set up another way — activated with `user activate`, or given a password with `user reset` or a [reset link](#reset-link) — the administrator waits no more: its setup links stop working for good, and this command stops with the error below.
- 🌐 As for [invitations](#invite), the link is complete when `LIBREFOLIO_PUBLIC_URL` is set, and the path only (`/setup#token=…`) when it is not.
- 📧 The command only prints the link: it sends no email.
- ❌ When no administrator is waiting for its setup, the command stops with the error `No administrator account is waiting for its setup link` and exits with `1`.

### 📧 Change the Email Address of an Account {: #set-email }

```bash
pipenv run ./dev.py user set-email <username> <new_email>
```

The same change as a new email in the user's [Profile](../user/settings/profile.md#email-change), without their password: use it when someone cannot change their address themselves, or to separate two accounts that share one ([below](#email-case-conflict)).

- 🔤 An address belongs to one account only, whatever its capitals: `Anna@example.com` and `anna@example.com` are the same address. Only the letters A to Z are matched this way, accented letters are not: `Émile@example.com` and `émile@example.com` are two different addresses.
- 🚪 A new address signs the account out of every device, cancels any password-reset link still open, and is recorded as not verified; the account can still sign in. The account's own address with other capitals is the same address: only the way it is written changes, nobody is signed out, and it stays verified.
- 👑 On the initial administrator still waiting for its setup link, a new address also stops that link, which went to the old address: the account still waits, and [`user setup-link`](#setup-link) gives it a new one. While `LIBREFOLIO_ADMIN_EMAIL` is set, each start of the server gives the waiting account that address again: change the variable as well, or the next start brings the old address back and stops the new link too.
- ❌ An address another account already has, in any capitals, is refused: the command stops with the error `Email already registered` and exits with `1`, changing nothing. So does an address that is another account's username, in any capitals: an account created before version 1.3 may have an `@` in its username ([Usernames with an @](users.md#usernames-with-at)), and once that name is someone's address, the sign-in, which reads an address first, would no longer find that account by its name. The account's own username is no obstacle: it can become its address. An address that is not valid (`Not an email address`) or an unknown username (`User '<username>' not found`) stops the command too.

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

### 🔤 Two Accounts with the Same Email Address {: #email-case-conflict }

From version 1.3, an email address belongs to one account only, whatever its capitals. A database from an earlier version may hold two accounts whose addresses differ only in capitals, such as `Anna@example.com` and `anna@example.com`: the upgrade then stops at the migration that checks this, and the server does not start. The migrations before it stay applied, no account is changed, and the next start picks up from that migration. The log (or the output of `db upgrade`) names the accounts by id and username, never by address; a `;` separates one group of accounts from the next:

```text
Email addresses must be unique regardless of case (release 1.3), and these accounts share one apart from upper and lower case: #3 'anna', #8 'anna_work'. Give all but one account of each group another address with …
```

LibreFolio never merges two accounts: give all but one account of each group another address with [`user set-email`](#set-email), then start LibreFolio again:

```bash
pipenv run ./dev.py user set-email <username> <new_email>
```

In Docker, the server is the container's main process, so the container does not stay up and `docker compose exec` cannot be relied on: run the command in a one-off container instead.

```bash
docker compose stop librefolio
docker compose run --rm librefolio python dev.py user set-email <username> <new_email>
docker compose start librefolio
```

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

`backup create` puts the whole instance in one zip archive, while the server keeps running: the database, the uploaded files, the broker reports and your own stress scenarios. With `--encrypt`, it makes a [secure archive](#backup-secure), encrypted with a password you choose, which `backup decrypt` turns back into its zip. `backup inspect` checks an archive and shows what it holds, `backup restore --dry-run` tries a restore of it on a copy, leaving the instance as it is, and `backup restore` restores it at the next start of the server. To copy the data directory by hand instead, see [Backup](filesystem.md#backup).

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
    - `--password-file FILE`: the text of the file, without the byte order mark at its start and the line breaks at its end, as for [Secrets in Files](configuration.md#secret-files): a file that holds the password alone, such as a Docker secret. A relative path starts at the project root.
    - `--password-stdin`: one line of the standard input, without its line break, such as from a pipe. At a terminal, the password is asked as without the option, without being shown, twice for `create`: typed there as a line, it would show.

    `--password-file` and `--password-stdin` exclude each other, and either one makes the archive secure without `--encrypt`.

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
    - `❌ password file: <path> does not exist (password_unreadable)`, or `cannot be read (…)`, `is empty or blank`, `is not UTF-8 text`, `is larger than 65536 bytes, too large for a secret`.

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

Everything else stays out: `secrets/` (but `secrets/instance.key` in a secure archive), `logs/`, `scheduler_state.json`, the `backups/` folder itself, the `.librefolio-production-data` marker, and SQLite's working files next to the database: `app.db-wal`, `app.db-shm`, `app.db.post-migration.lock` and the `.bak` copies of the [post-migration fixes](#post-migration-fixes). The copy of the database already holds what was waiting in `app.db-wal`. Symbolic links and special files are never followed nor archived.

!!! warning "🔑 The instance key is in a secure archive only"

    A clear archive leaves out `secrets/`, which holds the [instance key](configuration.md#instance-key). Back it up separately, as [Filesystem Structure → What to Back Up](filesystem.md#what-to-back-up) explains, and keep the copy as private as the archives. Before you start LibreFolio on the data of a clear archive, put `secrets/` back with it: without its key, what LibreFolio encrypted can no longer be read. A [secure archive](#backup-secure) carries the key LibreFolio generated, never one set with `LIBREFOLIO_INSTANCE_KEY` or `LIBREFOLIO_INSTANCE_KEY_FILE`: keep that one where you set it. With a copy of the key, a restore on another installation can still read the saved secrets of a clear archive: [The Instance Key of Another Installation](#backup-restore-instance-key).

??? info "📋 `manifest.json` — what it records"

    - the format, `librefolio-backup`, and its version;
    - the LibreFolio version that made the archive, how (`cli` for this command, `ui` for the web interface, `panel` for a [hosting panel](hosting_providers.md#panel-backups)) and when, in UTC;
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

    Then the [post-migration fixes](#post-migration-fixes) run on the copy, as at every start.

4. **Checked before and after.** Before the upgrade, the copy passes SQLite's integrity check and holds exactly the rows the manifest counted. After it, the copy passes the integrity check again, at this LibreFolio's revision. A migration may change data, so rows that changed are a warning, not a refusal, and so are broken references (foreign keys), kept as they are.
5. **Administrators.** The report names the active administrators of the backup. Without any, the restore is blocked: nobody could manage the instance after it.
6. **Saved secrets.** The instance keeps its own [instance key](configuration.md#instance-key). When the archive carries the key that encrypted its saved plugin secrets, such as the API key of a data source, or when you give that key with `--instance-key-file` ([The Instance Key of Another Installation](#backup-restore-instance-key)), they are re-encrypted on the copy with this instance's key; the others are counted, to enter again after the restore. A copy without secrets does not even read this instance's key.

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
- ⚠️ The warnings, which let a restore go on: `The upgrade changed the rows of some tables (listed above)`, `The backup's database has broken references: they are kept as they are`, `The upgrade added broken references to the copy`, `The ledger's totals differ from those the backup recorded (listed above)` or `The ledger's totals could not be read on the copy`.
- ⛔ The blocker, which forbids it: `❌ The backup has no active administrator: after a restore nobody could manage the instance`.

It ends with `✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed.` and exits with `0`. It exits with `1` when the archive is refused or the restore blocked. A refusal is one line, the reason followed by a code in parentheses, such as `❌ The file is not a LibreFolio backup (not_a_backup)`, and nothing of the copy is left.

- 💽 The copy needs free space on the disk of the data directory: everything the archive holds once unpacked, plus twice the size of its database for the upgrade, plus 64 MB. `backup inspect` shows those sizes; the archive itself is read where it is, never copied. A secure archive also needs room for its decrypted archive, about its own size, until it is unpacked. When the space is short, the check stops before it unpacks anything, with the number of bytes it needs (`no_space`); a disk that fills up during the check stops it too.
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
    | `no_space` | Not enough free space for the copy |
    | `stage_failed` | The copy could not be written: the error printed just above gives the cause |
    | `database_damaged` | The backup's database fails SQLite's integrity check, before or after the upgrade, or SQLite cannot read its schema |
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

Nothing has changed yet: the server keeps running on its data, and the checked copy waits in `.restore/stage/<id>/`, however long it takes. Restart LibreFolio when it suits you: stop the whole server, then [start it](#start-the-server) again; with Docker, `docker compose restart librefolio` ([Back Up with Docker](#backup-docker)). If the server is stopped, its next start applies the restore.

That start applies it before it reads any data:

1. 🛑 **Only a start of the whole server.** Every LibreFolio server process holds a lock on the data directory from early in its start, before it reads any data, until it exits. A start that finds it held by another process, such as a worker that uvicorn starts again beside its running siblings with `--workers` or a second server on the same data directory, leaves the restore waiting (`server_running`). Restart the whole server, never one worker. A start that finds the restore applied by another server that still runs, or by another start, stops instead of serving data whose restore is not committed.
2. 🔀 **The swap.** The instance's `sqlite/`, `custom-uploads/`, `broker_reports/` and `scenario_catalog/` swap places with those of the copy. Each move is a rename inside the data directory: instant, whatever the size. The instance's own folders are set aside in `.restore/previous/`.
3. 🔒 **What stays.** `secrets/`, `logs/`, `scheduler_state.json` and `backups/` are not touched: the instance keeps its [instance key](configuration.md#instance-key), its logs and its archives.
4. ✅ **The first start must complete.** The start goes on, on the restored data, which the check already brought to this LibreFolio's revision. Once it gets through, before it answers anyone, it ends every session, revokes the one-time links of the backup, and removes the instance's former data and the copy: the restore is done.
5. ↩️ **Otherwise, back as before.** If that first start fails, on a migration that fails or a damaged file, the next start puts the data as it was before back by itself, and records the restore as rolled back, with the reason ([Follow or Cancel a Restore](#backup-pending)). With Docker, the container starts again by itself after a failed start, so the data comes back without you; with nothing that starts the server again, start it yourself.

After the restore:

- 🔑 Everyone signs in again, on every device, with an account of the backup and the password it had then. The report of the check names the administrators of the backup.
- 🔗 No link sent before the restore works any more (invitations, password resets, email verifications), not even those the backup still held: send new ones.
- 📧 An account the backup held still waiting for its email verification loses its link too, and stops waiting: the sign-in page can no longer send it another link, and answers that the account is disabled. An administrator activates it in [Users & Invitations](users.md#actions), and its address stays unverified; or deletes it ([Delete an Account](users.md#delete)), so that its owner signs up again and receives a new link. Such an account never signed in, so it holds no data.
- 🆘 If nobody remembers an administrator's password of then, whoever runs the server creates a reset link with [`user reset-link`](#reset-link), or sets a new password with `user reset`. Once signed in, an administrator sends reset links to the others from [Users & Invitations](users.md#reset-links).

Good to know:

- 🔒 On an instance its hosting provider blocked (`LIBREFOLIO_BLOCKED`), the command confirms all the same, and adds `⚠️ The hosting provider blocked this instance: the restore waits until it is unblocked (instance_blocked)`: the first start after the unblock applies it.
- 🚦 One restore at a time: while one waits or is being applied, `backup restore` stops before the check with `❌ A restore already waits for the next start: ./dev.py backup pending --cancel drops it (restore_already_pending)` and exits with `1`. It stops there too when it cannot read the state of the restore, since it cannot tell whether one waits: `❌ The state of the restore cannot be read: <reason> (restore_state_unreadable)`, exit code `1`, nothing checked. `--dry-run` still works.
- ❌ If the confirmation itself is refused, the command prints one line that ends with a code, removes the copy and exits with `1`: `restore_stage_outdated` when LibreFolio was updated between the check and the confirmation, `restore_stage_expired` when the question waited more than 24 hours, `restore_already_pending` when another restore was confirmed meanwhile. Run the command again.
- 📍 Run it where the server runs, in the container with Docker: the restore is recorded for the path of the data directory, and a server that finds its data directory under another path does not apply it.
- 🔗 Keep the four folders real folders of the data directory: one that is a link, or that is mounted on its own, cannot be swapped. The start then leaves the data as it is, and records the restore as rolled back with `swap_failed`.
- 💽 The swap needs no space of its own: the copy the check made becomes the instance's data, and the former data is removed once the first start completes.
- 🗝️ The restore keeps this installation's instance key. When the archive carries the key of the installation that made it (a [secure archive](#backup-secure), when LibreFolio generated that key), the check has already re-encrypted its saved secrets with this installation's key. From any other archive of another installation, give that installation's key with `--instance-key-file`, and the check re-encrypts them too ([The Instance Key of Another Installation](#backup-restore-instance-key)). Otherwise they cannot be read here: the report counts them, to enter again after the restore, unless you put that installation's key back first ([Saved Secrets and the Instance Key](configuration.md#plugin-secrets)). See «The instance key is in a secure archive only» above.

### 🗝️ The Instance Key of Another Installation {: #backup-restore-instance-key }

```bash
# A clear archive of another installation, with the instance key of that installation
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --instance-key-file ~/old-instance.key
```

A clear archive leaves the instance key out, and so does a secure one whose key came from the environment: the saved plugin secrets it holds, such as the API key of a data source, open only with the key of the installation that made it. `--instance-key-file FILE` gives that key to `backup restore`, with or without `--dry-run`: the check re-encrypts those secrets on the copy with this instance's key, which stays as it is.

- 📄 The file holds the old installation's instance key: a copy of its `secrets/instance.key`, or the value of its `LIBREFOLIO_INSTANCE_KEY` in a file, such as the one of its `LIBREFOLIO_INSTANCE_KEY_FILE`. The line breaks at its end do not count.
- 🔑 The command reads it first, as the user who started it, before it switches to the owner of the data directory, as it reads `--password-file`: with `docker compose exec`, a Docker secret only root can read works.
- 🙈 The key is never printed. Only the command line takes it: the web interface never takes a key, and a restore from Settings › Administration › Backup counts those secrets as unreadable.
- 📁 The report says `Instance key: not included; given with --instance-key-file`, then `Saved provider keys: <n> re-encrypted with this instance's key`.
- ℹ️ An archive that carries its own key is restored with it, whatever the file holds: the report adds `ℹ️ The archive carries its own instance key: --instance-key-file is not used`.
- ⚠️ A key that reads none of the saved secrets is not the key of the installation that made the backup: the report adds `⚠️ The key given with --instance-key-file reads none of the saved provider keys: it is not the key of the instance this backup came from`, before the line that counts them, to enter again after the restore. When this instance's own key cannot be used, nothing is re-encrypted, whatever the key given, and the line is `⚠️ This instance's own key cannot be used, so nothing was re-encrypted with the key given: <problem>` instead: the problem of the start log's `The instance key cannot be used: …` («Startup Checks» in [Environment Variables](configuration.md)). Secrets already under this instance's key, as in an archive of this same instance, are left as they are, whatever the key given.
- ❌ It exits with `1`, before anything is checked, when the file cannot give the key: `❌ instance key file: <path> does not exist (instance_key_unreadable)`, or `cannot be read (…)`, `is empty or blank`, `is not UTF-8 text`, `is larger than 65536 bytes, too large for a secret`. A key shorter than 32 characters stops it before the copy is made: `❌ The instance key given is too short: an instance key has at least 32 characters (instance_key_invalid)`.

### ⏳ Follow or Cancel a Restore {: #backup-pending }

```bash
# The restore waiting for the next start, or the last one
pipenv run ./dev.py backup pending

# Drop the restore waiting, and its checked copy
pipenv run ./dev.py backup pending --cancel
```

`backup pending` changes nothing and exits with `0`, except when it cannot read the state of the restore: it then prints `❌ The state of the restore cannot be read: <reason> (restore_state_unreadable)` and exits with `1`. The reason, such as `Permission denied`, says why: give `.restore/` and its files back to the user that runs LibreFolio, readable by it. Otherwise it shows one of these:

| It prints | What it means |
| --- | --- |
| `ℹ️ No restore waits for the next start` | No restore was confirmed, or the last one was dropped |
| `⏳ A restore waits for the next start of the server`, then `backup made by LibreFolio <version> on <date> UTC; confirmed by <who> on <date> UTC` | Confirmed, not applied yet. `<who>` is `cli` for this command, otherwise the username of the administrator who confirmed it |
| `⏳ A restore is being applied by the server` | A start applied it and has not completed yet. If that start died, the next one puts the data back |
| `✅ The last restore was applied on <date> UTC: backup made by LibreFolio <version> on <date> UTC` | The restore is done |
| `⚠️ The last restore was rolled back on <date> UTC, the data is as it was before: <reason> (<code>)` | The restore was undone, for the reason below |

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

`--cancel` drops the restore waiting, with its checked copy, whoever confirmed it: `✅ The restore waiting for the next start was dropped, with its copy: the data stays as it is`, exit code `0`. If the copy cannot be removed, on a permission or disk error for instance, the restore is dropped all the same, exit code `0`, with two lines instead: `✅ The restore waiting for the next start was dropped: the data stays as it is` and `⚠️ Its checked copy could not be removed: it goes when its check expires`. When the removal failed with an error, the log above them has the warning `The copy of a cancelled restore could not be removed: it goes when its check expires`; a copy left without an error, such as one holding a read-only folder, has none. LibreFolio tries again at its first start once the check is 24 hours old. If the restore itself cannot be dropped, on a file-system error before it is (its lock, or removing its state): `❌ The restore could not be cancelled: <reason>. It still waits for the next start (restore_cancel_failed)`, exit code `1`. When the state of the restore cannot be read: the `restore_state_unreadable` line of `backup pending`, exit code `1`. When no restore waits, or one is already being applied: `❌ No restore waits for the next start: nothing to cancel (restore_not_pending)`, exit code `1`.

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
- 🔁 After a first start that fails on the restored data, the container starts again by itself (`restart: unless-stopped`, in both compose files LibreFolio ships), and that start puts the data as it was before back.
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
