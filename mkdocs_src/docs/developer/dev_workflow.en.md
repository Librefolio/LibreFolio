# 🔄 Developer Workflow & Tools

This guide covers developer-specific workflows, tools, and all CLI commands available in LibreFolio.

!!! note "Prerequisite: Host Installation"

    Before using these developer tools, ensure you have set up your local Python, Node.js, and Pipenv environment. For step-by-step setup instructions, see the [Host Installation Guide](../admin/host_installation.md).

---

## 🖥️ SvelteKit Frontend Development

For active frontend development with Hot Module Replacement (HMR), start a second terminal and run:

```bash
./dev.py front dev
```

The Vite development server will run at **`http://localhost:5173`** and automatically proxy all `/api` calls to the FastAPI backend.

!!! note "Frontend Dependency"

    The SvelteKit frontend is heavily dependent on the data returned by the backend. You must keep the backend server running in parallel (via `./dev.py server` in another terminal) to handle API requests.

---

## 🔄 Development Workflow CLI Commands

LibreFolio includes a central orchestration script, `dev.py`, which is your single entry point for all development tasks.
Run `./dev.py --help` for the full command tree.

### ⏹️ Stopping the Server

`./dev.py server` runs uvicorn as its child process and waits for it (`run_server_live()` in `scripts/cli_base.py`). It lets the server finish its own shutdown, bounded by the shutdown budget (`LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS`, 8 s by default; see *Stopping the Server* in [Configuration](../admin/configuration.md)):

- **Ctrl+C**: the terminal sends SIGINT to the whole foreground process group, so the server already has it. `dev.py` sends nothing more, since a second SIGINT would make uvicorn force its exit: it prints `Interrupted: waiting for the server to stop …` and waits.
- **SIGTERM to `dev.py`**, for example from a process supervisor that signals only the main process: `dev.py` forwards it to the server, prints `SIGTERM: waiting for the server to stop …` and waits the same way. A server that gets the SIGTERM from its process group as well (the test runner signals the whole group, `scripts/test_runner/_server.py`) gets it twice and stops once.
- **The wait** (`_server_stop_grace()` in `dev.py`) is the budget plus 2 s: 10 s by default, 7 s with `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS=5`, 10 s with a value that cannot be used, and no limit with `0`.
- **A second Ctrl+C or SIGTERM**, or the end of the wait: `dev.py` kills the server (SIGKILL).

`dev.py` exits with `130` after a Ctrl+C and `143` after a SIGTERM. With `--coverage` no `dev.py` is left to wait: it replaces itself with `coverage run`, and the signals reach the server directly (see [Frontend Coverage Architecture](test-walkthrough/index.md#frontend-coverage-architecture)). The other `dev.py` commands still run through `run_command_live()`, whose `subprocess.run` kills the child 0.25 s after a Ctrl+C.

### 🖥️ Frontend Management

| Command | Description | Details |
|---------|-------------|---------|
| `./dev.py front dev` | Start Vite dev server with HMR | Run at `http://localhost:5173` |
| `./dev.py front build` | Compile frontend into production-ready static assets | static files output to `backend/static` |
| `./dev.py front build --debug` | Compile frontend with source maps | Used for debugging frontend issues |
| `./dev.py front check` | Run `svelte-check` type validator | Checks Svelte components and TS types |
| `./dev.py front preview` | Preview the compiled production build locally | Run Vite preview server |

### 🔗 API Client Synchronization

LibreFolio uses an OpenAPI-first workflow to keep types synchronized between Python (backend) and SvelteKit (frontend):

| Command | Description | Details |
|---------|-------------|---------|
| `./dev.py api schema` | Export OpenAPI JSON schema from FastAPI backend | Generates `openapi.json` |
| `./dev.py api client` | Generate TypeScript client from the exported schema | Generates frontend API client |
| `./dev.py api sync` | Export schema and generate client in one step | Highly recommended after changing models/routes |

### 🌍 Internationalization (i18n)

Manage translations across English, Italian, Spanish, and French. The catalogue the frontend loads, `frontend/src/lib/i18n/<lang>.json`, is generated and ignored by git: never edit it, the build stops on a hand edit. Its sources are `frontend/src/lib/i18n/base/`, one folder per subsystem with its `prefixes.txt`, and each plugin's `i18n/` fragment (see [Internationalization](frontend/i18n.md) and [A Plugin's Translations](architecture/patterns/registry_pattern.md#plugin-translations)). Every command works on the sources, and the ones that change keys regenerate the catalogue.

| Command | Description |
|---------|-------------|
| `./dev.py i18n audit` | Audit missing or extra translation keys across languages, after a strict check of the sources |
| `./dev.py i18n audit --duplicates` | Audit and report duplicate translation values |
| `./dev.py i18n add KEY --en "…" --it "…" --fr "…" --es "…" [--into SOURCE]` | Add a key in the four languages, in the source that owns it; `--into` names the source: `base`, a subsystem, or a plugin as `<family>/<plugin>` |
| `./dev.py i18n update KEY [--en "…"] [--it "…"] [--fr "…"] [--es "…"]` | Change a key's translations, in the source that holds it |
| `./dev.py i18n remove KEY` | Remove a key from every source and language |
| `./dev.py i18n where KEY` | The source file that holds a key, or the one `add` would write it to |
| `./dev.py i18n search QUERY` | Search key names or translation values; shows the source of each key |
| `./dev.py i18n tree [PREFIX]` | Print key tree structure starting with optional prefix |
| `./dev.py i18n build [--strict] [--force]` | Regenerate the catalogue from the sources: a missing translation falls back to English with a warning (an error with `--strict`); `--force` overwrites a hand-edited generated file |
| `./dev.py i18n check [--lenient] [--against REV]` | Validate the sources, strictly: every language complete (`--lenient` accepts a missing translation, as the build does); `--against` also proves the catalogue identical to the one at a git revision, key by key and language by language |
| `./dev.py i18n move PREFIX --into SOURCE` | Move every key under a prefix, in every language, to another source |
| `./dev.py i18n split` | Put every key of `base` and of the subsystems in the folder its declared prefix names (re-runnable) |
| `./dev.py i18n absorb --base REV --theirs REV [--prefer {ours,theirs}]` | Replay the key changes a branch made on the old single-file layout, as a three-way merge per key and language; conflicts are listed and nothing is written unless `--prefer` settles them |

The catalogue is regenerated by `./dev.py front build`, by the npm hooks of `dev`, `build`, `build:debug`, `check` and `check:watch` (so also by `./dev.py front dev` and `./dev.py front check`; by hand, `npm run i18n:build`), before every Vitest run, by `./dev.py lint --dead-code` before knip, and by the commands above. The development server generates it once, when it starts, and does not watch its sources: a source you edit by hand reaches the running server only after `./dev.py i18n build`.

### 🗃️ Database Migrations (Alembic)

Create and apply database schema changes:

| Command | Description |
|---------|-------------|
| `./dev.py db upgrade` | Apply all pending migrations to the SQLite database |
| `./dev.py db migrate "MESSAGE"` | Auto-generate a new Alembic migration based on SQLAlchemy models |
| `./dev.py db downgrade` | Rollback the database schema by one migration step |
| `./dev.py db create-clean` | Recreate a fresh database and apply all migrations |
| `./dev.py db current` | Show the current database migration revision |

`db migrate`, `db upgrade`, `db downgrade` and `db create-clean` refuse to run while a server listens on the port that serves the target database (`PORT` for the production database, `TEST_PORT` for the test one): stop that server first. The server itself applies pending migrations at startup (`ensure_database_exists()` in `backend/app/services/platform/database_bootstrap.py`, the `database` step of the [lifespan](architecture/overview.md#server-startup)).

### 🧪 Test Runner

Run backend unit/integration tests and frontend Playwright E2E tests:

| Command | Description |
|---------|-------------|
| `./dev.py test all` | Run all test categories in the optimal order |
| `./dev.py test <category> all` | Run tests in a single category (e.g., `api`, `e2e`, `front-fx`) |
| `./dev.py test <category> --help` | List the units (actions) of a category, each with its description |
| `./dev.py test <category> <action> --list` | List the tests of one unit without running them; `all` lists the whole category |

### 🧰 Linting, Formatting & Documentation

| Command | Description |
|---------|-------------|
| `./dev.py format` | Format backend Python code with `black` |
| `./dev.py lint` | Lint and auto-fix backend Python issues using `ruff` |
| `./dev.py mkdocs serve` | Start the local MkDocs documentation development server |
| `./dev.py mkdocs build` | Compile the documentation site into static HTML |
| `./dev.py shell` | Open a subshell inside the active `pipenv` virtual environment |

---

## 🐳 Docker Integration

Developers can build and run production-tagged containers locally using the dev CLI:

| Command | Description |
|---------|-------------|
| `./dev.py docker build` | Build production Docker image (compiles frontend + docs first) |
| `./dev.py docker up` | Launch the containerized stack in detached mode |
| `./dev.py docker down` | Stop and remove active Docker containers |
| `./dev.py docker rebuild` | Build, stop, and restart containers with the new image |
| `./dev.py docker exec <cmd>` | Execute a `dev.py` command inside the running container, as the server's user (through `gosu`), not root |

For details on local Docker workflows, container settings, and how the host `.env` file integrates with `docker-compose.yml`, see the [Advanced Docker Guide](../admin/docker_advanced.md). How the image itself is built and started: [Architecture overview → Docker image](architecture/overview.md#docker-image).

### 🏗️ What `./dev.py docker build` Does {: #docker-build-steps }

`cmd_docker_build()` checks that `.env` exists, then `_docker_ensure_assets_built()` prepares what the image copies from the host:

1. **Version**: `get_git_version()`, asked once before any other step, so that a step writing a tracked file cannot turn it into `-dirty`: `LF_APP_VERSION` when it is set, `git describe` otherwise. The `VERSION` file of an earlier build is deleted first, so a checkout where git cannot answer gets `unknown`, not the old value. The frontend bundle and `VERSION` both carry this frozen version (see [Version Stamps → Local image builds](docs/release-pipeline.md#local-image-builds)).
2. **Resource cache**: `scripts/update_js_cache.py`, strict. It caches the flags subset of the Noto Color Emoji font (`frontend/static/fonts/noto-color-emoji/`, drawn by the `'LF Flags'` face of `frontend/static/lf-flags.css` on every non-Apple device: Windows has no flag emoji of its own) and MathJax (`mkdocs_src/docs/javascripts/vendor/`); a resource that cannot be downloaded and has no cached copy fails the build (`❌ Resource cache incomplete`). `./dev.py front build` fails only for the resources the frontend ships (`--required-for frontend`), and `./dev.py server` only warns and falls back to the CDN. `./dev.py cache js` (`--force`) refreshes the cache by hand.
3. **Frontend**: `_docker_ensure_frontend_built()` rebuilds it in production mode, with `LF_APP_VERSION` set to the frozen version for that build only, when `_docker_frontend_stale_reason()` gives a reason, shown in the log:
    - *missing or outdated*: `check_frontend_needs_build()` finds sources newer than `frontend/build/index.html`, the files of `frontend/static/` included, or a Tool codegen input added, removed or renamed since that build (what it watches: [Frontend Tests Overview → Automated Setup](test-walkthrough/front-overview.md#automated-setup));
    - *not a production build*: `.build-debug` says `1` (a debug build, for example from `./dev.py server --test`) or is missing (mode unknown);
    - *built for another version*: `frontend/build/.build-version` does not hold the frozen version.

    After its build it writes the version into `.build-version`. Every frontend build empties `frontend/build/`, so the file exists only when the last build was made for an image: a build from `./dev.py front build`, a server or the test runner is rebuilt once, and a new commit, even one that touched no frontend file, changes the version and rebuilds the bundle too. The `Dockerfile`'s `frontend` stage still checks the result (`scripts/docker/check_frontend_build.sh`).
4. **Documentation**: `mkdocs build` when `mkdocs_src/site/index.html` is missing or older than any `.md` under `mkdocs_src/docs/`.
5. **`requirements.txt`**: regenerated with `pipenv requirements` when missing or older than `Pipfile.lock`.
6. **`VERSION`**: the frozen version, written into a file, since the image has no `.git/`. The sidebar (the bundle's version) and Settings → About (`GET /api/v1/system/info`, the backend's) show the same version in the image.

The build then runs `docker build -t librefolio:<version> -t librefolio:latest --build-arg UID=<uid> --build-arg GID=<gid> .`. `<version>` comes from `_get_docker_tag()`, which clears `get_git_version()`'s cache and asks again after the steps above: if one of them changed a tracked file, the tags end in `-dirty` while the version inside the image does not. The UID/GID are those of the user running the command (`os.getuid()`, `os.getgid()`; only `docker compose build` reads `UID`/`GID` from `.env`). `--light` adds `-light` to both tags and `--build-arg DOCS_VARIANT=light`; `--no-cache` is passed through. `./dev.py docker rebuild` runs the same build, then `docker compose down` and `docker compose up -d`; a failed build leaves the running containers alone.

### 🧪 Test Mode in the Container {: #docker-test-mode }

The image cannot run test mode, for the two reasons below, and it exposes only the production port `6040`: neither Compose file publishes the test port. Run test mode from a source checkout on the host instead:

```bash
./dev.py test db populate --force --with-static   # mock data in the test database
./dev.py server --test                            # test server on :6041
```

Then open `http://localhost:6041` and sign in as a test user, for example `e2e_test_user` / `E2eTestPass123!` or `e2e_test_admin` / `E2eAdminPass123!`.

The compose stack holds only the host's `PORT` (`${PORT:-6040}`), so the test server can run on the host while the stack is up.

!!! info "Why the image cannot run test mode"

    - **`test` is not part of the image.** `dev.py` registers a command group only when the directories it needs exist (`_has()` in `dev.py`): without `backend/test_scripts/`, which `.dockerignore` keeps out, `test` stays listed but answers *'test' is not available in this installation* and exits with `2`, so `test db populate` cannot seed the test database. `i18n` (`frontend/scripts/`) and `mkdocs translate` / `translate-validate` (`mkdocs_src/aphra-pipeline/`) behave the same way; `./dev.py test utils dev-cli-image` pins this behaviour on a copy of the image's file set.
    - **`server --test`** forces a debug frontend build, while the image ships a production one: `auto_build_frontend()` sees the mode mismatch and rebuilds, and the rebuild stops at its first check. Before any `npm` or `npx` call, `cmd_fe_build()` looks in `frontend/node_modules/.bin` for the tools it runs, and the image has no `node_modules` and no Node.js: `dev.py` stops with *Cannot run the frontend build: the frontend dependencies are not installed*, names the missing tools (`openapi-zod-client`, `svelte-check`, `vite`) and the fix for a checkout, `cd frontend && npm ci`, which the image cannot run, and the server does not start.

The flow above runs on the host, so its test database is `backend/data/test/sqlite/app.db` in the source checkout (from `LIBREFOLIO_TEST_DATA_DIR`, default `./backend/data/test`), and `./dev.py test db populate --force` deletes and recreates it.
