# 🛠️ Command-Line Tools

`dev.py` runs the administration tasks: starting the server, managing users and invitations, maintaining the database, backing up the instance. Each section says **where** to run the command and when it needs the server stopped.

!!! tip "Where to run the commands"

    | Installation | Where | Command form |
    | --- | --- | --- |
    | **On the host** | Terminal on the server, in the LibreFolio folder (the project root), Pipenv environment | `pipenv run ./dev.py <command>` — or `./dev.py <command>` after `pipenv shell` |
    | **Docker, server running** | Terminal on the host, in the folder of `docker-compose.yml` | `docker compose exec librefolio python dev.py <command>` |
    | **Docker, server stopped** | Same terminal | `docker compose stop librefolio`, then `docker compose run --rm librefolio python dev.py <command>` (one-off container), then `docker compose start librefolio` |

    - There is no `pipenv run` in the container: the image installs the dependencies globally.
    - `docker compose exec` runs the command as root. From a source checkout, `./dev.py docker exec <command>` runs it as the server's user instead ([details](docker_advanced.md#docker-exec)).
    - The commands `user`, `db current`, `db check`, `db currencies`, `backup create`, `backup inspect`, `backup restore`, `backup decrypt` and `backup pending` work in the image ([Back Up with Docker](cli_backup.md#backup-docker)). `db upgrade` and `db downgrade` need the server stopped, so the third form ([Apply Migrations](#apply-migrations)). Development commands such as `test` are not part of the image.

!!! info "📚 This guide is in several pages"

    Besides this page: [CLI Admin Tools: Backups](cli_backup.md).

---

## 🖥️ Start the Server {: #start-the-server }

**On the host**, in the server's terminal, LibreFolio folder. In Docker the server is the container's main process: `docker compose up -d` starts it.

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

The server answers on the chosen port (`PORT` from `.env`, else 6040).

- 🧮 More workers serve more requests at once: use them on any machine with more than one CPU. `auto` starts $\max(1,\ 2\,(n-1))$ workers on $n$ CPUs.
- ⏳ At the first start, or when they are out of date, the server builds the web interface and this documentation: it takes a few minutes. If the interface does not build, the server does not start.
- 🔑 A restart signs everybody out, unless `JWT_SECRET` is set in `.env` ([Configuration](configuration.md)).
- ⏹️ Ctrl+C stops the server cleanly: `dev.py` gives it the [shutdown budget](configuration_security.md#shutdown) plus 2 seconds (10 seconds by default), then ends it; a second Ctrl+C ends it at once. A SIGTERM sent to `dev.py` alone, by a process supervisor for example, gets the same wait: `dev.py` passes it on to the server.

??? note "⚙️ Other server options — rarely needed"

    | Option | What it does |
    | --- | --- |
    | `--host HOST` | Address to listen on (default: `HOST` from the environment or `.env`, else `0.0.0.0`) |
    | `--data-dir PATH` | Another data directory for this run, instead of `LIBREFOLIO_DATA_DIR` |
    | `--no-scheduler` | Start without the scheduled price and FX rate syncs |
    | `--rebuild`, `-r` | Rebuild the web interface even when it looks up to date |
    | `--debug`, `-d` | `DEBUG` logs, a debug build of the web interface and the API documentation pages (`/api/v1/docs`, `/api/v1/redoc`), otherwise off |

    Short forms: `-w` for `--workers`, `-p` for `--port`, `-f` for `--force`. `--test`, `--coverage` and `--no-reload` are development options: `pipenv run ./dev.py server --help` lists them all.

---

## 👤 Manage Users

**On the host** or **in Docker with the server running** (first or second form of the table above): these commands write straight to the database, so they also work while the server is running.

In the app, administrators manage accounts and invitations in **Settings › Administration › Users** ([Users & Invitations](users.md)). The command line is for a server without a browser, or to go past the [user limit](configuration_accounts.md#user-limit).

### ➕ Create and List Users

```bash
# Create an administrator account
pipenv run ./dev.py user create <username> <email> <password>

# Create a regular account
pipenv run ./dev.py user create <username> <email> <password> --role user

# List all users: ID, username, email, active, administrator
pipenv run ./dev.py user list
```

`user list` prints, for each account: ID, username, email, active, administrator.

- 👑 `user create` creates an **administrator**; with `--role user`, a regular account. People can also sign up on their own: **Register here** on the login page while **Registration** is **Open** (on a new instance, also until the first account exists), or with an [invitation link](#invite) ([Who Can Sign Up](settings.md#registration)).
- 🔒 Password: same rules as in the app and the API. At least 8 characters, with an upper-case letter, a lower-case letter, a digit and a symbol. Letters and digits of any alphabet count (`É`, `é`); a symbol is any character that is neither a letter, a number nor a space (`!`, `_`, `€`). An invalid password changes nothing: the command prints `Password does not meet security requirements:` and one line per rule missed, starting with the rule's code (`digit: the password must contain a digit`), then exits with `1`.
- 🔤 Username: 3 to 50 characters, without `@` (at sign-in, anything containing `@` is read as an email address). Spaces, accented letters, `.`, `_`, `-`, `+` are fine. Errors, each with exit `1` and changing nothing: `A username cannot contain @: the sign-in reads it as an email address`; `A username must be 3 to 50 characters long`; `Username already taken`; `Email already registered` if another account has that address, or the address is another account's username ([`user set-email`](#set-email)), in any capitals.
- 📏 At the [user limit](configuration_accounts.md#user-limit), `user create` warns `The instance is at its limit (LIBREFOLIO_MAX_USERS: 5 of 5 places taken): the command line creates the account anyway`, then creates the account: the command line is how you go past the limit.

### ✉️ Invite Someone {: #invite }

```bash
# An invitation link for a regular account
pipenv run ./dev.py user invite

# An invitation for an administrator, with a note of whom it is for
pipenv run ./dev.py user invite --admin --email anna@example.com
```

The command prints a link that works once, for 7 days: send it to the person, who opens it and creates their own account with the username, email and password they choose ([what they see](../user/getting-started.md#invitation-link)).

- 👑 `--admin`: the new account is an administrator; without it, a regular one.
- ✉️ `--email`: only a note of whom the invitation is for; the person can sign up with another address.
- 🌐 With [`LIBREFOLIO_PUBLIC_URL`](configuration_accounts.md#accounts) set, the link is complete (`https://librefolio.example.com/invite#token=…`). Without it, the command prints the path only, `/invite#token=…`, and reminds you to put the address of the server in front of it (`http://192.168.1.10:6040`). If the variable is set but is not an `http://` or `https://` address, the reminder says `LIBREFOLIO_PUBLIC_URL is not valid (…)`, with the reason. This holds for every link on this page.
- 🔒 The secret part comes after `#`: browsers never send it to the server, so it does not end up in the server or proxy logs. Send the link whole.
- 🚪 Invitations work with **Registration** **Open** or **By invitation**. With **Closed**, the command stops with `Registration is disabled: invitations cannot be created` and exits with `1`; the links already sent do not work either.
- 📏 An invitation takes a place of the [user limit](configuration_accounts.md#user-limit) until it is used, revoked or expired. At the limit, the command warns, then creates the invitation anyway.
- ⏳ No command cancels an invitation: a link nobody used expires after 7 days. Sooner, **Revoke** in the [Users](users.md#open-invitations) tab, or through the API: `GET /api/v1/users/invites` lists the pending invitations, `DELETE /api/v1/users/invites/<id>` revokes one.

### 🔑 Reset a Password or Lock an Account {: #reset-a-password-or-lock-an-account }

```bash
# Set a new password (same rules as above)
pipenv run ./dev.py user reset <username> <new_password>

# Lock an account out, then let it back in
pipenv run ./dev.py user deactivate <username>
pipenv run ./dev.py user activate <username>
```

`reset` changes the password at once; `deactivate` refuses the account from its next request.

- ⏱️ `reset` ends the open sessions: every device is signed out at its next request. To lock someone out for good, `deactivate`: activating the account again does not bring its old sessions back.
- 🔗 `reset` also cancels any [reset link](#reset-link) still open for the account, whoever created it.
- 👑 `deactivate` refuses the last active administrator: `User '<username>' is the last active administrator: promote or activate another administrator first`, exit `1`.
- 📏 At the [user limit](configuration_accounts.md#user-limit), `activate` of a deactivated account warns `… the command line reactivates the account anyway`, then reactivates it. No warning for an account that already holds its place: one waiting for its email with a live link, or the initial administrator waiting for its setup link.
- 📬 With email verification on, `activate` lets an account waiting for its email in at once and `deactivate` ends the wait: either way its verification links stop working (*Email Verification* in [Email](email.md)).
- 🏁 On the [initial administrator](configuration_accounts.md#initial-admin) still waiting for its setup link, `reset` and `activate` set it up without the link and end the wait for good: its setup links are invalidated, the one of `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` included, and neither [`user setup-link`](#setup-link) nor a new `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` gives it another one. `activate` alone leaves an active account whose password nobody knows, until `reset` or a [reset link](#reset-link) gives it one; `reset` alone leaves it inactive, until you step in with `activate`.
- 🚫 On that same waiting administrator, `deactivate` sets nothing up: it cancels the setup link, as **Cancel setup link** does in [Users & Invitations](users.md#cancel-setup). It prints `✅ User '<username>' deactivated`; every setup link of the account is invalidated, the one of `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` included, and the account keeps waiting: [`user setup-link`](#setup-link) gives it a new one, and so does a **new** `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` at the next start. The same token, at a restart, does not: the instance has already seen it.
- 💬 The app's **Forgot Password?** screen shows this command for both installations: for Docker the line `docker compose exec librefolio sh -c 'exec gosu …' sh user reset …` (the one of [`docker exec`](docker_advanced.md#docker-exec), run as the server's user, not root); for the host `./dev.py user reset …`, after `pipenv shell` or with `pipenv run` in front. When the instance can email a reset link, the screen shows only the email form, without the commands ([Forgotten Passwords](email_flows.md#forgot-password)).

### 🔗 Send a Password-Reset Link {: #reset-link }

```bash
pipenv run ./dev.py user reset-link <username>
```

The command prints a link: the person opens it and chooses the new password themselves, instead of receiving the one you chose with `user reset` ([what they see](../user/getting-started.md#password-reset-link)).

- ⏱️ The link works once, for 30 minutes. A new link for the same account cancels the earlier ones; a change of the account's password or email — in the user's Profile, or with `user reset` or `user set-email` — cancels them all.
- 🚪 Once the new password is set, every signed-in device is signed out, as with `user reset`. Creating the link signs nobody out.
- 🌐 Complete link with `LIBREFOLIO_PUBLIC_URL`, the path only (`/reset-password#token=…`) without it ([as for invitations](#invite)).

### 🔁 A New Setup Link for the Initial Administrator {: #setup-link }

```bash
pipenv run ./dev.py user setup-link
```

The command prints a new setup link for the administrator created from `LIBREFOLIO_ADMIN_EMAIL` at the first start ([The Initial Administrator](configuration_accounts.md#initial-admin)), as long as nobody has used theirs: they open it, choose the password and are signed in. Use it when the link has expired, got lost or was cancelled.

- ⏱️ The link works once, for 72 hours. The earlier setup links are invalidated, the one of `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` included.
- 🚫 After a cancellation — **Cancel setup link** in [Users & Invitations](users.md#cancel-setup), or `user deactivate` on the waiting administrator — the administrator still waits: this command gives it a new link.
- 📮 After a new address for the waiting administrator — `LIBREFOLIO_ADMIN_EMAIL` changed before a restart, or [`user set-email`](#set-email) — its links, sent to the old address, are invalidated: this command gives it a link for the new one. The same address with other capitals of the letters A-Z is no change: the link keeps working.
- 🔚 Set up another way — `user activate`, or a password from `user reset` or from a [reset link](#reset-link) — the administrator waits no more: its links are invalidated for good and the command stops with the error below.
- 🌐 Complete link with `LIBREFOLIO_PUBLIC_URL`, the path only (`/setup#token=…`) without it ([as for invitations](#invite)).
- 📧 The command only prints the link: it sends no email.
- ❌ Without a waiting administrator, the command stops with `No administrator account is waiting for its setup link` and exits with `1`. The same if the administrator completes the setup while the command runs: the command checks again just before it issues the link and gives none to an account already set up.

### 📧 Change the Email Address of an Account {: #set-email }

```bash
pipenv run ./dev.py user set-email <username> <new_email>
```

The same change as a new email in the user's [Profile](../user/settings/profile.md#email-change), without their password: for someone who cannot change their address themselves, or to separate two accounts that share one ([below](#email-case-conflict)).

- 🔤 An address belongs to one account only, whatever its capitals: `Anna@example.com` and `anna@example.com` are the same address. Only the letters A-Z are compared this way, not accented ones: `Émile@example.com` and `émile@example.com` are two different addresses.
- 🚪 A new address signs the account out of every device, cancels every password-reset link and every pending email-change link, and is recorded as not verified; the account can still sign in. It does not touch the password. The same address with other capitals only changes how it is written: nobody is signed out and it stays verified.
- 👑 On the initial administrator still waiting for its setup link, the new address also invalidates that link: the account still waits, and [`user setup-link`](#setup-link) gives it a new one. While `LIBREFOLIO_ADMIN_EMAIL` is set, each start of the server gives the waiting account that address again: change the variable as well, or the next start brings the old address back and invalidates the new link too.
- ❌ Refused, with exit `1` and changing nothing: an address another account already has, in any capitals (`Email already registered`); an address that is another account's username, in any capitals (same error: an account created before version 1.3 may have an `@` in its username, [Usernames with an @](users.md#usernames-with-at), and if that name became someone's address, the sign-in, which reads an address first, would no longer find that account); an invalid address (`Not an email address`); an unknown username (`User '<username>' not found`). The account's own username is no obstacle: it can become its address.

### 👑 Grant or Remove Administrator Rights

```bash
pipenv run ./dev.py user promote <username>
pipenv run ./dev.py user demote <username>
```

A demotion signs the account out of every device.

- 👑 `demote` refuses the last active administrator: `User '<username>' is the last active administrator: promote another user first`, exit `1`.
- 🏁 `demote` also refuses the [initial administrator](configuration_accounts.md#initial-admin) still waiting for its setup link, which keeps its role until then: `User '<username>' is the initial administrator waiting for its setup: it keeps its role until then; deactivate it to cancel its setup link, or delete it from Settings › Administration › Users`, exit `1`, changing nothing. To cancel its link: `user deactivate` ([above](#reset-a-password-or-lock-an-account)). To remove the account: delete it in [Users & Invitations](users.md#delete), with no demotion first. The command line deletes no account.

### 🧭 Restart the Guides of a User {: #reset-onboarding }

```bash
# Every guide, the Welcome setup included
pipenv run ./dev.py user reset-onboarding <username>

# One guide only
pipenv run ./dev.py user reset-onboarding <username> --flow intro_tour
```

The next time the user opens LibreFolio, the Welcome setup and the guides start again, as on their first visit; the user's data and preferences stay. `--flow` restarts one guide only: `pipenv run ./dev.py user reset-onboarding --help` lists the names (`welcome`, `intro_tour`, `import_guide`…).

---

## 🗄️ Maintain the Database

### ⬆️ Apply Migrations {: #apply-migrations }

Every start of the server applies the pending migrations by itself: you rarely need to do it by hand.

**On the host**, in the server's terminal, LibreFolio folder, **with the server stopped**: `db upgrade` refuses to run while the server answers on the configured port. `db current`, `db check` and `db currencies` change nothing and also run with the server up.

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

`db upgrade` brings the database to the latest migration; `db current` prints the one it is at.

- 📄 Without a path, the commands use the configured database. A path names another SQLite file: a relative one starts at the project root, whatever folder you run the command from. The file must exist, except for `db upgrade`, which creates it (folder included) and brings it up to date.
- 🐳 **In Docker**, the path is inside the container: `LibreFolio-data/` is `/app/backend/data/prod-docker`, the database is `sqlite/app.db` in it. `db current`, `db check` and `db currencies`: server running, `docker compose exec librefolio python dev.py db current <path>`. `db upgrade` and `db downgrade`: server stopped (`docker compose stop librefolio`), then a one-off container, `docker compose run --rm librefolio python dev.py db upgrade <path>` ([details](docker_advanced.md#docker-exec)).

### 🔤 Two Accounts with the Same Email Address {: #email-case-conflict }

From version 1.3, an email address belongs to one account only, whatever its capitals. If an earlier database has two accounts with addresses that differ only in capitals (`Anna@example.com` and `anna@example.com`), the upgrade stops at the migration that checks this and the server does not start. The earlier migrations stay applied, no account is changed, the next start picks up from there. The log (or the output of `db upgrade`) names the accounts by id and username, never by address; a `;` separates one group from the next:

```text
Email addresses must be unique regardless of case (release 1.3), and these accounts share one apart from upper and lower case: #3 'anna', #8 'anna_work'. Give all but one account of each group another address with …
```

LibreFolio never merges two accounts: give all but one account of each group another address, then start LibreFolio again.

=== "On the host"

    In the server's terminal, LibreFolio folder:

    ```bash
    pipenv run ./dev.py user set-email <username> <new_email>
    ```

=== "Docker"

    In the folder of `docker-compose.yml`. The server is the container's main process, so the container does not stay up and `docker compose exec` is no use: use a one-off container.

    ```bash
    docker compose stop librefolio
    docker compose run --rm librefolio python dev.py user set-email <username> <new_email>
    docker compose start librefolio
    ```

### 🩹 Post-Migration Fixes {: #post-migration-fixes }

Right after the migrations, every start runs the **post-migration fixes**: repairs that a migration cannot make. Usually there is nothing to do. In the log (the server output, also saved in `logs/`) you may read:

| Log line | Meaning |
| --- | --- |
| ✅ `Post-migration fixes applied and verified` | A repair was made. On a large database that start is slower, once. |
| ⚠️ `Post-migration fix failed` | Database left as it was, server started normally. The warning gives the error and the copy of the database kept next to the original until you delete it (`app.db.pre-autoincrement-20261008T101500Z.bak`). The fix is tried again at the next start. |
| 🩺 `Post-migration fixes skipped` | The copy could not be made, or the database fails SQLite's integrity check. Nothing changed. |
| 🔗 `Foreign key violations already in the database, left as they are` | The database holds references to rows that no longer exist, listed in the warning. The fixes leave them as they are and still run: a fix fails only on a broken reference it would add itself. |

The empty file `app.db.post-migration.lock`, next to the database, makes the runs take turns when several workers start together: leave it in place.

The fixes:

- **`autoincrement`**: the id of a deleted user, broker, asset, transaction, FX conversion route or asset event is never given out again. While converting, it deletes the report folders of brokers that no longer exist, so that a new broker does not inherit them.
- **`orphan_pair_halves`**, once: repairs the transfers that a broker deletion left without their other half on the remaining brokers.
    - 📈 Securities received from the deleted broker → opening position at the transfer cost, from the transfer date. That broker's capital counts them at that cost, not at their market value on arrival, so its gain also includes what they gained before the transfer. Without a recorded cost they stay without one and the app reports an acquisition without a purchase value: enter the cost in the transaction.
    - 💶 Cash transfers with the deleted broker → deposits or withdrawals: capital and gain do not change.
    - 📤 Securities sent **to** the deleted broker: right after the fixes, at the same start, each transfer becomes an adjustment that takes the securities out of the sending broker, without a value: only the quantity goes down, and the cost counts as a realized loss on that broker. One log line each (`Lone transfer leg converted to an ADJUSTMENT-out without a value`). If the database fails SQLite's quick check, they stay as they were (`Lone transfer legs left as they are: the database failed its quick check`). If the whole step fails (`Lone transfer legs could not be converted; starting normally`), nothing is changed and the server starts anyway.
- **`event_types`**, once: repairs the asset events with a type LibreFolio does not know, such as `dividend` or `dividendo` written by hand in a CSV. Until now such an event made the whole list of the asset's events fail to load, so none was shown.
    - ✅ A type that differs only in letter case or spaces (`dividend`, ` Split `) is corrected.
    - 🗑️ An event whose type is still unknown is deleted. A linked transaction stays, without its event: link it again to the right event if you need to.

??? tip "⌨️ Run the fixes by hand — to preview them or retry a failed one"

    **On the host**, in the server's terminal, LibreFolio folder, **with the server stopped** (the script does not check it). In Docker: [Post-migration fixes with the server stopped](docker_advanced.md#post-migration-fixes).

    ```bash
    # Preview: report what would be fixed, change nothing
    pipenv run python -m backend.app.db.post_migration --dry-run

    # Apply the fixes
    pipenv run python -m backend.app.db.post_migration
    ```

    The script prints each fix as `clean` (nothing to do), `would_apply` (dry run), `applied` or `failed`, with the orphan broker folders, a kept copy and any error, then one line for each transfer of securities sent to a deleted broker (`Lone transfer leg …`); it exits with `1` when something failed. `--db PATH` and `--data-dir PATH` point it at another database or another data directory.

    To see what `orphan_pair_halves` will do on your database, run `--dry-run` before the first start of the new version: it prints `Fix orphan_pair_halves: would_apply` when there is something to repair, and a warning lists the transactions by id, grouped by conversion (`TRANSFER->ADJUSTMENT`), with those that will stay without a cost and the transfers of securities sent to a deleted broker; these get one line each after the fixes (`would become an ADJUSTMENT-out without a value`). The script prints on the console what the server would write to the log: the warning and, on a real run, one line per transaction changed (with `LOG_LEVEL` at `INFO`, the default). It writes no log file: keep its output if you want a record of the repair.

🔗 How the fixes work inside: [Database Schema — Post-migration fixes](../developer/architecture/database/index.md#post-migration-fixes).

### 💱 Currency Codes That Are Not ISO Codes {: #currency-codes }

From version 1.3, LibreFolio saves a currency only as an ISO 4217 alphabetic code (`EUR`, `USD`). Earlier versions also accepted the name or the numeric code and saved it as written: `Euro`, `978`. Such a value still reads, but an edit that saves its row again is refused until the code is corrected, and its amounts are not summed with those of the ISO code: `978` and `EUR` make two balances. A restored backup can bring such values back.

Shortly after every start, the log warns when the database holds some; LibreFolio does not change them by itself:

```text
Stored currency codes that are not ISO 4217 codes: an edit of their rows is refused until they are corrected (./dev.py db currencies lists them)
```

**On the host** or **in Docker with the server running** (`docker compose exec librefolio python dev.py db currencies`):

```bash
# Where each value is stored, how many rows hold it, and the ISO code it stands for
pipenv run ./dev.py db currencies

# Another database file, such as a copy
pipenv run ./dev.py db currencies /path/to/copy/app.db
```

The command lists the values without changing anything.

- 🔎 Each line names the place (`transactions.currency`, `assets.currency`, the steps of an FX route, a provider's settings, a user's base currency…), the value, how many rows hold it and the ISO code it stands for: `978` is `EUR`, `US DOLLAR` is `USD`.
- ➖ A dash: no single code. A name two currencies share (`Bolívar Soberano`: `VED` or `VES`), a value that is not a currency, or a code that counts cents rather than units (`GBX`, `ZAC`, `ILA`), never to be simply renamed.
- 🔤 A code in lower case or with spaces (`eur`) is listed too: the right currency, in a form that exact comparisons miss.
- 🧱 A value saved as raw bytes or as text that is not valid UTF-8, which only a damaged or hand-made database holds, appears in SQLite's notation (`X'455552'`) with a dash: it is never a code.
- 🚦 Exit `0` when every code is ISO, `1` when it lists some, `2` when it cannot read the database.

### 🔧 Add Missing Global Settings

**On the host** or **in Docker with the server running**:

```bash
pipenv run ./dev.py user init-settings
```

Adds the missing [Global Settings](settings.md) with their default values, as every start does, but without starting the server; it never changes a value already set.

### 🧹 Reset the Database

**On the host**, in the server's terminal, LibreFolio folder, **with the server stopped**:

```bash
pipenv run ./dev.py db create-clean
```

!!! warning "All data will be lost"

    `db create-clean` deletes the database and creates an empty one. Like `db upgrade`, it refuses to run while the server is up. Uploaded files and broker reports stay on disk: [Database Initialization & Reset](host_installation.md#database-reset).

---

## 📋 Full Command Tree

```bash
# Every command, by category
pipenv run ./dev.py --help

# The options of one command
pipenv run ./dev.py server --help
```

??? info "👩‍💻 Developer and documentation commands"

    - **Frontend**: `pipenv run ./dev.py front build`, `front dev`, `front check` — [Frontend Development](../developer/frontend/index.md)
    - **Testing**: `pipenv run ./dev.py test all` — [Test Walkthrough](../developer/test-walkthrough/index.md)
    - **API Client**: `pipenv run ./dev.py api sync` — [API Overview](../developer/api/overview.md)
    - **i18n**: `pipenv run ./dev.py i18n audit` — [Internationalization](../developer/frontend/i18n.md)
    - **Documentation**: `pipenv run ./dev.py mkdocs deploy` publishes this documentation to GitHub Pages; `pipenv run ./dev.py mkdocs gallery` regenerates the screenshots with Playwright on a test server (`--no-populate` keeps the current test data).

    The full developer toolkit: [Developer Workflow Guide](../developer/dev_workflow.md).

---

## 🔗 Related

- 📄 **[CLI Admin Tools: Backups](cli_backup.md)** — Back Up the Instance
