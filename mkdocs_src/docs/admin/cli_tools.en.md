# 🛠️ Command-Line Tools

`dev.py`, at the root of the project, runs the administration tasks: starting the server, managing users, maintaining the database and backing up the instance. Each section says when a command needs the server stopped.

!!! tip "Where to run the commands"

    - **Host installation**: in the Pipenv environment, with the `pipenv run` prefix used on this page, or after `pipenv shell`.
    - **Docker**: in the running container, with `docker compose exec librefolio python dev.py <command>` (from a source checkout, `./dev.py docker exec <command>`, which runs it as the server's user instead of root). No `pipenv run` there: the image installs the dependencies globally. User commands, `db current`, `db check`, `backup create`, `backup inspect`, `backup restore`, `backup decrypt` and `backup pending` work there ([Back Up with Docker](cli_backup.md#backup-docker)); `db upgrade` and `db downgrade` do not, as they need the server stopped ([Apply Migrations](#apply-migrations)). Development commands such as `test` are not part of the image ([details](docker_advanced.md#docker-exec)).

!!! info "📚 This guide is in several pages"

    Besides this page: [CLI Admin Tools: Backups](cli_backup.md).

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
- ⏹️ Ctrl+C stops the server cleanly: `dev.py` gives it up to the [shutdown budget](configuration_security.md#shutdown) plus 2 seconds to stop (10 seconds by default), then ends it; a second Ctrl+C ends it at once. A SIGTERM sent to `dev.py` alone, by a process supervisor for example, gets the same wait: `dev.py` passes it on to the server.

??? note "⚙️ Other server options — rarely needed"

    | Option | What it does |
    | --- | --- |
    | `--host HOST` | Address to listen on (default: `HOST` from the environment or `.env`, else `0.0.0.0`) |
    | `--data-dir PATH` | Use another data directory for this run, instead of `LIBREFOLIO_DATA_DIR` |
    | `--no-scheduler` | Start without the scheduled price and FX syncs |
    | `--rebuild`, `-r` | Rebuild the web interface even when it looks up to date |
    | `--debug`, `-d` | `DEBUG` logs, a debug build of the web interface and the API's documentation pages (`/api/v1/docs`, `/api/v1/redoc`), which are off otherwise |

    Short forms: `-w` for `--workers`, `-p` for `--port`, `-f` for `--force`. `--test`, `--coverage` and `--no-reload` are development options: `pipenv run ./dev.py server --help` lists them all.

---

## 👤 Manage Users

These commands write straight to the database, so they also work while the server is running.

In the app, administrators manage the other accounts and the invitations from the **Users** tab of **Settings › Administration**: see [Users & Invitations](users.md). The commands below need no browser: use them on a headless server, or to go past the [user limit](configuration_accounts.md#user-limit).

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
- 🔤 A username cannot contain `@`: at sign-in, LibreFolio reads anything with an `@` as an email address. Such a username changes nothing: the command stops with the error `A username cannot contain @: the sign-in reads it as an email address` and exits with `1`. Spaces, accented letters and signs such as `.`, `_`, `-` or `+` are fine. A username also has 3 to 50 characters, as at registration: a shorter or a longer one changes nothing either, the command stops with the error `A username must be 3 to 50 characters long` and exits with `1`. The command also stops, with `Username already taken`, on a username another account has, and, with `Email already registered`, on an address another account has, or that is another account's username (see [`user set-email`](#set-email)), in any capitals.
- 📏 When the instance has reached its [user limit](configuration_accounts.md#user-limit), `user create` warns `The instance is at its limit (LIBREFOLIO_MAX_USERS: 5 of 5 places taken): the command line creates the account anyway`, then creates it: the command line is how you go past the limit.

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
- 🌐 With [`LIBREFOLIO_PUBLIC_URL`](configuration_accounts.md#accounts) set, the link is complete, such as `https://librefolio.example.com/invite#token=…`. Without it, the command prints the path only, `/invite#token=…`, and reminds you to put the address of your server in front of it, such as `http://192.168.1.10:6040`. If the variable is set but is not an `http://` or `https://` address, the reminder says `LIBREFOLIO_PUBLIC_URL is not valid (…)` instead, with the reason.
- 🔒 The secret part of the link comes after `#`: browsers never send that part to the server, so it does not end up in server or proxy logs. Send the link whole.
- 🚪 Invitations work while **Registration** is **Open** or **By invitation**. While it is **Closed**, the command stops with the error `Registration is disabled: invitations cannot be created` and exits with `1`, and the links already sent do not work either.
- 📏 An invitation takes a place of the [user limit](configuration_accounts.md#user-limit) until it is used or revoked, or expires. At the limit, the command warns, then creates the invitation anyway.
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
- 📏 When the instance has reached its [user limit](configuration_accounts.md#user-limit), `activate` of a deactivated account warns `… the command line reactivates the account anyway`, then reactivates it. It prints no warning for an account that already holds its place: one waiting for its email with a live link (below), or the initial administrator waiting for its setup link.
- 📬 With email verification on, `activate` lets an account that waits for its email in at once — with no limit warning while its link is live, since its place is already counted — and `deactivate` ends its wait: either way, the verification links it was sent stop working. See *Email Verification* in [Email](email.md).
- 🏁 On the [initial administrator](configuration_accounts.md#initial-admin) still waiting for its setup link, `reset` and `activate` work as on any account: they set it up without its link, and `activate` prints no limit warning, since the account already holds its place. Either one ends the wait for good: its setup links stop working, the one of `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` included, and neither [`user setup-link`](#setup-link) nor a new `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` gives it another one. `activate` alone leaves an active account whose password nobody knows, until `reset` or a [reset link](#reset-link) gives it one; `reset` alone leaves it inactive, until `activate`.
- 🚫 On that administrator still waiting, `deactivate` sets nothing up: it cancels the setup link, as **Cancel setup link** does in [Users & Invitations](users.md#cancel-setup). The command prints `✅ User '<username>' deactivated`; every setup link of the account stops working, the one of `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` included, and the account keeps waiting for a new one: [`user setup-link`](#setup-link) gives it one, and so does a new `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` at the next start. The same token at a restart gives none, as the instance has already seen it.
- 💬 The app's **Forgot Password?** screen shows this command for both installations: `docker compose exec librefolio python dev.py user reset …` for Docker, and `./dev.py user reset …` for a host installation, to run after `pipenv shell` or with `pipenv run` in front. When your instance can email a reset link, the screen shows the email form first and keeps the commands in a panel closed by default ([Forgotten Passwords](email_flows.md#forgot-password)). In the `managed` profile it shows no command: it tells users to ask their administrator for a password-reset link ([Hosting for Others](hosting_providers.md#managed-profile)).

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

When LibreFolio created the administrator from `LIBREFOLIO_ADMIN_EMAIL` at its first start ([The Initial Administrator](configuration_accounts.md#initial-admin)) and nobody has used its setup link yet, this command prints a new one: the administrator opens it, chooses the password and is signed in. Use it when the link has expired, got lost or was cancelled.

- ⏱️ The link works once, for 72 hours. The setup links issued before stop working, the one of `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` included.
- 🚫 A cancelled link — **Cancel setup link** in [Users & Invitations](users.md#cancel-setup), or `user deactivate` on the waiting administrator — leaves the administrator waiting: this command gives it a new link.
- 📮 A new address for the waiting administrator — `LIBREFOLIO_ADMIN_EMAIL` changed before a restart, or [`user set-email`](#set-email) — stops its setup links, which went to the old address. The administrator still waits: this command gives it a link for the new address. The same address with other capitals of the letters A to Z is no change, and the link keeps working.
- 🔚 Set up another way — activated with `user activate`, or given a password with `user reset` or a [reset link](#reset-link) — the administrator waits no more: its setup links stop working for good, and this command stops with the error below.
- 🌐 As for [invitations](#invite), the link is complete when `LIBREFOLIO_PUBLIC_URL` is set, and the path only (`/setup#token=…`) when it is not.
- 📧 The command only prints the link: it sends no email.
- ❌ When no administrator is waiting for its setup, the command stops with the error `No administrator account is waiting for its setup link` and exits with `1`. It does so too when the administrator completes its setup while the command runs: the command checks again just before it issues the link, and gives none to an account already set up.

### 📧 Change the Email Address of an Account {: #set-email }

```bash
pipenv run ./dev.py user set-email <username> <new_email>
```

The same change as a new email in the user's [Profile](../user/settings/profile.md#email-change), without their password: use it when someone cannot change their address themselves, or to separate two accounts that share one ([below](#email-case-conflict)).

- 🔤 An address belongs to one account only, whatever its capitals: `Anna@example.com` and `anna@example.com` are the same address. Only the letters A to Z are matched this way, accented letters are not: `Émile@example.com` and `émile@example.com` are two different addresses.
- 🚪 A new address signs the account out of every device, cancels any password-reset link still open, and is recorded as not verified; the account can still sign in. The account's own address with other capitals is the same address: only the way it is written changes, nobody is signed out, and it stays verified.
- 👑 On the initial administrator still waiting for its setup link, a new address also stops that link, which went to the old address: the account still waits, and [`user setup-link`](#setup-link) gives it a new one. While `LIBREFOLIO_ADMIN_EMAIL` is set, each start of the server gives the waiting account that address again: change the variable as well, or the next start brings the old address back and stops the new link too.
- ❌ An address another account already has, in any capitals, is refused: the command stops with the error `Email already registered` and exits with `1`, changing nothing. So does an address that is another account's username, in any capitals: an account created before version 1.3 may have an `@` in its username ([Usernames with an @](users.md#usernames-with-at)), and once that name is someone's address, the sign-in, which reads an address first, would no longer find that account by its name. The account's own username is no obstacle: it can become its address. An address that is not valid (`Not an email address`) or an unknown username (`User '<username>' not found`) stops the command too.
- 📮 A new address also cancels any email-change link still waiting for the account. It does not touch the password: to take back the administrator account of a [managed instance](hosting_instances.md#owner-reassign), use `user reassign-owner`.

### 🛟 Give a Managed Instance Back to Its Owner {: #reassign-owner }

```bash
pipenv run ./dev.py user reassign-owner <username>
```

For a managed instance whose administrator's address was confirmed by mistake: the account takes the address of `LIBREFOLIO_ADMIN_EMAIL`, becomes the only owner, loses its password and its sessions, and one reset link is emailed to that address. The whole procedure is in [A Wrong Address Was Confirmed](hosting_instances.md#owner-reassign).

- ❌ On an instance that is not managed, without `LIBREFOLIO_ADMIN_EMAIL`, for an unknown username, or when another account has that address, the command prints the reason, changes nothing and exits with `1`.
- 🔗 It never prints the link: when the email cannot go, the link is in a log line on the terminal (*Password-reset link for the instance owner*), and [`user reset-link`](#reset-link) prints another.

### 👑 Grant or Remove Administrator Rights

```bash
pipenv run ./dev.py user promote <username>
pipenv run ./dev.py user demote <username>
```

`demote` refuses the last active administrator: it stops with the error `User '<username>' is the last active administrator: promote another user first` and exits with `1`. A demotion signs the account out of every device.

`demote` also refuses the [initial administrator](configuration_accounts.md#initial-admin) still waiting for its setup link, which keeps its role until then: it stops with the error `User '<username>' is the initial administrator waiting for its setup: it keeps its role until then; deactivate it to cancel its setup link, or delete it from Settings › Administration › Users` and exits with `1`, changing nothing. To cancel its link, run `user deactivate` (see «Reset a Password or Lock an Account» above); to remove the account, delete it in [Users & Invitations](users.md#delete), with no demotion first: the command line deletes no account.

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

# List the currency codes that are not ISO codes: changes nothing, exits with 1 if any
pipenv run ./dev.py db currencies

# Upgrade and check another database file, such as a copy
pipenv run ./dev.py db upgrade /path/to/copy/app.db
pipenv run ./dev.py db check /path/to/copy/app.db
```

- 📄 Without a path, the commands use the configured database. A path names another SQLite file: a relative one starts at the project root, wherever you run the command from. The file must exist, except for `db upgrade`, which creates it (folder included) and brings it up to date.
- 🐳 In Docker, the path is inside the container, where `LibreFolio-data/` is `/app/backend/data/prod-docker` (the database is `sqlite/app.db` in it). `db current`, `db check` and `db currencies` work in the running container: `docker compose exec librefolio python dev.py db current <path>`. `db upgrade` and `db downgrade` need the server stopped (`docker compose stop librefolio`), then a one-off container: `docker compose run --rm librefolio python dev.py db upgrade <path>` ([details](docker_advanced.md#docker-exec)).

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
- 📤 Securities sent **to** the deleted broker: right after the fixes, at the same start, each of these transfers becomes an adjustment that takes the securities out of the sending broker. Such an adjustment has no value: the securities only leave the quantity, and their cost counts as a realized loss on that broker. The log has one line for each (`Lone transfer leg converted to an ADJUSTMENT-out without a value`). On a database that fails SQLite's quick check, every one of them is left as it is (`Lone transfer legs left as they are: the database failed its quick check`). If the whole step fails (`Lone transfer legs could not be converted; starting normally`), nothing is changed and the server starts anyway.

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

    To see what `orphan_pair_halves` will change on your database, preview it before the first start of the new version: `--dry-run` prints `Fix orphan_pair_halves: would_apply` when there is something to repair, and a warning lists the transactions by id, grouped by conversion (such as `TRANSFER->ADJUSTMENT`), with those that will stay without a cost and the transfers of securities sent to a deleted broker. Those transfers get a line each after the fixes (`would become an ADJUSTMENT-out without a value`). The script also prints, on the console, what the server would log: the warning and, on a real run, one line per transaction changed (with `LOG_LEVEL` at `INFO`, the default). It writes no log file: keep its output if you want a record of a repair made by hand.

🔗 How the fixes work inside: [Database Schema — Post-migration fixes](../developer/architecture/database/index.md#post-migration-fixes).

### 💱 Currency Codes That Are Not ISO Codes {: #currency-codes }

From version 1.3, LibreFolio saves a currency only as an ISO 4217 alphabetic code, such as `EUR` or `USD`. Earlier versions also accepted the name of a currency or its numeric code, and saved it as written: `Euro`, `978`. Such a value still reads, but an edit that saves its row again is refused until its code is corrected, and its amounts never meet those of the ISO code: `978` and `EUR` make two balances. A restored backup can bring such values back.

Shortly after every start, the log warns when the database holds some, and LibreFolio does not change them by itself:

```text
Stored currency codes that are not ISO 4217 codes: an edit of their rows is refused until they are corrected (./dev.py db currencies lists them)
```

`db currencies` lists them, without changing anything:

```bash
# Where each value is stored, how many rows hold it, and the ISO code it stands for
pipenv run ./dev.py db currencies

# Another database file, such as a copy
pipenv run ./dev.py db currencies /path/to/copy/app.db
```

- 🔎 Each line names the place (`transactions.currency`, `assets.currency`, the steps of an FX route, a provider's settings, a user's base currency…), the value, how many rows hold it, and the ISO code it stands for: `978` is `EUR`, `US DOLLAR` is `USD`.
- ➖ A dash means there is no single code: a name two currencies share (`Bolívar Soberano`: `VED` or `VES`), a value that is no currency, or a code that counts cents rather than units (`GBX`, `ZAC`, `ILA`), which must never simply be renamed.
- 🔤 A code in lower case or with spaces, such as `eur`, is listed too: the right currency, in a form that exact comparisons miss.
- 🧱 A value saved as raw bytes rather than text, or as text that is not valid UTF-8, which only a damaged or hand-made database holds, is listed in SQLite's notation, such as `X'455552'`, with a dash: it is never a code.
- 🚦 The command exits with `0` when every code is an ISO code, `1` when it lists some, and `2` when it cannot read the database.
- 🐳 In Docker: `docker compose exec librefolio python dev.py db currencies`.

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

---

## 🔗 Related

- 📄 **[CLI Admin Tools: Backups](cli_backup.md)** — Back Up the Instance
