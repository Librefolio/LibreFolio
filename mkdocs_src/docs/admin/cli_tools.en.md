# 🛠️ Command-Line Tools

`dev.py`, at the root of the project, runs the administration tasks: starting the server, managing users and maintaining the database. Each section says when a command needs the server stopped.

!!! tip "Where to run the commands"

    - **Host installation**: in the Pipenv environment, with the `pipenv run` prefix used on this page, or after `pipenv shell`.
    - **Docker**: in the running container, with `docker compose exec librefolio python dev.py <command>` (from a source checkout, `./dev.py docker exec <command>`, which runs it as the server's user instead of root). No `pipenv run` there: the image installs the dependencies globally. User commands, `db current` and `db check` work there; `db upgrade` and `db downgrade` do not, as they need the server stopped ([Apply Migrations](#apply-migrations)). Development commands such as `test` are not part of the image ([details](docker_advanced.md#docker-exec)).

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

### ➕ Create and List Users

```bash
# Create an administrator account
pipenv run ./dev.py user create <username> <email> <password>

# Create a regular account
pipenv run ./dev.py user create <username> <email> <password> --role user

# List all users: ID, username, email, active, administrator
pipenv run ./dev.py user list
```

- 👑 `user create` makes an **administrator** unless you add `--role user`, which makes a regular account. People can also create their own account: with **Register here** on the login page while **Registration** is **Open**, or with an [invitation link](#invite) (see [Who Can Sign Up](settings.md#registration)).
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
- ⏳ There is no command to cancel an invitation: a link nobody used stops working after 7 days. An administrator can revoke it sooner through the API: `GET /api/v1/users/invites` lists the pending invitations, `DELETE /api/v1/users/invites/<id>` revokes one.

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

The empty file `app.db.post-migration.lock`, next to the database, makes the runs take turns when several workers start together: leave it in place.

The first fix, **`autoincrement`**, makes sure the id of a deleted user, broker, asset, transaction, FX conversion route or asset event is never given to a new one. While converting a database, it deletes the report folders of brokers that no longer exist, so that a new broker cannot inherit them.

??? tip "⌨️ Run the fixes by hand — to preview them or retry a failed one"

    **Stop the server** first (the script does not check it), then run from the project root:

    ```bash
    # Preview: report what would be fixed, change nothing
    pipenv run python -m backend.app.db.post_migration --dry-run

    # Apply the fixes
    pipenv run python -m backend.app.db.post_migration
    ```

    The script prints each fix as `clean` (nothing to do), `would_apply` (dry run), `applied` or `failed`, with the orphan broker folders, a kept copy and any error, and exits with `1` when something failed. `--db PATH` and `--data-dir PATH` point it at another database or data directory.

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
