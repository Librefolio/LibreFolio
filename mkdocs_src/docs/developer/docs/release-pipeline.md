# 🚀 Release & CI/CD Pipeline

This page describes the design, execution flow and automation logic of the LibreFolio release pipeline: the GitHub Actions workflow `.github/workflows/release.yml`, a single job (`release-pipeline`) that:

- builds the SvelteKit frontend;
- checks and builds the documentation, including the gallery screenshots that Playwright captures in a real browser;
- builds the two Docker image variants, light first and then full, and pushes them to the GitHub Container Registry (GHCR);
- deploys the documentation site to GitHub Pages, on a stable release or a manual run from `main`;
- appends the Docker pull commands to the release notes, on releases.

The workflow runs no test suite: apart from the builds themselves, its gates are the [release tag guard](#prereleases), the documentation checks and the gallery. The tests have their own manual workflow, `.github/workflows/manual-test-run.yml`. The job's permissions are `contents: write` (the `gh-pages` push and the release-notes edit) and `packages: write` (the GHCR push).

---

## 🛠️ Triggers & Workflow Events

The workflow has three triggers:

1. **`push` to `dev`**: every push to `dev` runs the nightly build, which publishes the `nightly` and `nightly-light` images. The documentation checks and the gallery are tolerant there (see [Release gate and nightly tolerance](#release-gate-and-nightly-tolerance)), and the documentation site is not deployed.
2. **`workflow_dispatch`**: a manual run from the Actions tab, without inputs. It behaves according to the branch it is started on: on `dev` like a push to `dev`, on any other branch with the hard gates of a release. A run from `main`, which has no push trigger, pushes only the light `latest` image and deploys the documentation site; a run from any other branch pushes no image (see [Docker Images and Tags](#docker-images-and-tags)).
3. **`release` (`published`)**: publishing a GitHub release, which must be tagged with a plain `vX.Y.Z` (see [Release Tag Convention](#release-tag-convention)), runs the official release path: hard gates, the `X.Y.Z-light`, `latest` and `X.Y.Z` images, the documentation deploy and the release-notes update. GitHub fires `published` for prereleases too: a prerelease, which must be tagged `vX.Y.Z-rc.N`, runs the same path, but publishes only its own version tags, without moving `latest` or deploying the site (see [Docker Images and Tags](#docker-images-and-tags)). The job's first step enforces both tag forms (see [Release Tags and Publishing](#prereleases)).

Runs are named by `run-name`: `Release vX.Y.Z` for a release, `Manual run (<branch>)` for a manual run, and `Nightly (dev)` for a push to `dev`.

### 🔖 Release Tags and Publishing {: #prereleases }

A release's tag must match its kind; the leading `v` is optional in both:

| Release kind | Tag | Example | On any other tag |
|--------------|-----|---------|------------------|
| Prerelease («Set as a pre-release» checked) | `vX.Y.Z-rc.N` | `v1.2.0-rc.1` | `::error title=Prerelease tag`, exit 1 |
| Stable release | Plain `vX.Y.Z`, no suffix | `v1.2.0` | `::error title=Release tag`, exit 1 |

The job's first step, «Release tag must match the release kind», enforces both forms before the checkout. It runs for every release, prerelease or stable (`if: github.event_name == 'release'`), and is skipped on nightlies and manual runs. The release's prerelease flag selects the form the tag must have, and any other form fails the pipeline at once, with the table's `::error` annotation: for example `v1.2.0`, `v1.2.0-beta.1` or `v1.2.0-rc` on a prerelease, `v1.2.0-rc.1` on a stable release. Nothing is built or pushed, the site is not deployed, and the release notes are not updated; the GitHub release itself stays published.

The tag and the flag reach the check only through `env`, so neither is interpolated into the script, and bash matches the tag as a whole string, not line by line as `grep` would:

```yaml
if: github.event_name == 'release'
env:
  TAG_NAME: ${{ github.event.release.tag_name }}
  PRERELEASE: ${{ github.event.release.prerelease }}
run: |
  if [ "$PRERELEASE" = "true" ]; then
    if ! [[ "$TAG_NAME" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+-rc\.[0-9]+$ ]]; then
      echo "::error title=Prerelease tag::…"   # the tag, and how to publish instead
      exit 1
    fi
    echo "Prerelease tag OK: $TAG_NAME"
  else
    if ! [[ "$TAG_NAME" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      echo "::error title=Release tag::…"      # the tag, and how to publish instead
      exit 1
    fi
    echo "Release tag OK: $TAG_NAME"
  fi
```

Each branch closes one mismatch between the flag and the tag:

- **A prerelease carries `-rc.N`.** The suffix puts the candidate status in the tag itself, not only in the prerelease flag, which can be edited: with it, neither `latest` nor the in-app update prompt can mistake the prerelease for a release. Under `auto`, metadata-action skips semver pre-releases (see [Docker Images and Tags](#docker-images-and-tags)), and the prompt accepts only a stable `vX.Y.Z` tag (see [Release Tag Convention](#release-tag-convention)).
- **A stable release carries a plain `vX.Y.Z`.** The deploy and the release notes follow the flag; `latest` and the update prompt also read the tag. An `-rc.N` tag published as a stable release would therefore deploy the documentation site and announce `:latest` in its release notes, while `latest` stays in place (metadata-action skips the semver pre-release) and the prompt rejects the tag (it accepts only a plain `vX.Y.Z`).

**A prerelease is never promoted.** The stable release is always published as a new GitHub release, on a new plain `vX.Y.Z` tag. Of the release events, the workflow listens only to `published`, and promoting a prerelease publishes nothing new (GitHub reports the change as `released`), so the pipeline would not run for it: `latest` would not move, the documentation site would not be deployed, and the release notes would get no Docker section for the stable release.

How to publish:

- **Prerelease**: a new GitHub release with «Set as a pre-release» checked, on a new `vX.Y.Z-rc.N` tag.
- **Stable release**: a new GitHub release with «Set as a pre-release» unchecked, on a new plain `vX.Y.Z` tag, without `-rc.N` or any other suffix.
- **Never promote** a prerelease: publish the stable release from scratch, on its own tag.

!!! warning "A published tag is never republished"

    Once a `vX.Y.Z` release is published, its tag is never moved, never deleted and created again, and its image is never replaced: a fix is a new release on the next tag. The same holds for an `-rc.N` candidate, whose correction is the next `-rc.N`. Whoever deploys from a tag may then resolve it once and keep what it found, for example a hosting provider that pins the image's digest: if the same tag ever answers with another image, that is a signal, not a routine, and it is read as a possible tampering. A broken release is superseded, not rewritten.

---

## 🔄 Execution Flow Diagram

The diagram follows the job's steps in order. Dashed boxes are `continue-on-error` on `dev` only; thick boxes run under `!cancelled()`, so after a failed step too; hexagons are the warning-only [checkout checks](#checkout-checks).

```mermaid
graph TD
    A([GitHub Actions trigger]) --> B{Event}
    B -->|push to dev| C
    B -->|workflow_dispatch| C
    B -->|release published| R1{"Tag matches its kind? (rc / plain)"}
    R1 -->|"prerelease on -rc.N, or stable on plain vX.Y.Z"| C
    R1 -->|"any other tag"| R2["Run fails with an ::error annotation"]

    C["Checkout, Python 3.13, Pipenv, Node.js 24"] --> D["Expose the runner image: ImageOS to RUNNER_IMAGE_OS"]
    D --> E["Restore caches: Pipenv venv, npm, Playwright browsers"]
    E --> F["pipenv install --dev, write VERSION, export LF_APP_VERSION"]
    F --> G["dev.py install"]
    G --> G1{{"[CHECK] Checkout"}}
    G1 --> H["dev.py front build"]
    H --> H1{{"[CHECK] Checkout"}}

    H1 --> I1["translate-diff --issues-only"]
    I1 --> I2["translate-validate --hide-localized"]
    I2 --> I3["check-links"]
    I3 --> I4["mkdocs build"]
    I4 --> I4C{{"[CHECK] Checkout"}}
    I4C --> I5["mkdocs gallery --workers 4"]
    I5 --> I5C{{"[CHECK] Checkout"}}
    I5C --> J["front build: production rebuild"]
    J --> K["mkdocs build: rebuild with the screenshots"]

    K --> L{"Ref is dev?"}
    L -->|yes| M["Report soft-failed steps in the job summary"]
    L -->|no| N
    M --> N["Generate requirements.txt"]

    N --> O["QEMU, Buildx, GHCR login"]
    O --> P["Docker metadata: full and light tags"]
    P --> Q1{"Light tags?"}
    Q1 -->|yes| Q2["Build and push the light image, DOCS_VARIANT=light"]
    Q1 -->|none| Q3
    Q2 --> Q3{"Full tags?"}
    Q3 -->|yes| Q4["Build and push the full image"]
    Q3 -->|none| S
    Q4 --> S{"main, or a stable release?"}

    S -->|yes| T["dev.py mkdocs deploy to gh-pages"]
    S -->|no| U[Skip deploy]
    T & U --> V["Upload the playwright-screenshots artifact, 1 day"]

    V --> V1{"Gallery failed?"}
    V1 -->|yes| V2["Upload the playwright-gallery-report artifact, 3 days"]
    V1 -->|no| W
    V2 --> W{"Release event?"}
    W -->|yes| X["Append Docker pull commands to the release notes"]
    W -->|no| Y([End])
    X --> Y

    classDef soft stroke-dasharray: 5 5
    classDef always stroke-width:3px
    class I1,I2,I3,I4,I5,K soft
    class V,V2 always
```

---

## 🏷️ Release Tag Convention (F14 update prompt) {: #release-tag-convention }

The in-app "new version available" prompt reads **`GET /repos/Librefolio/LibreFolio/releases/latest`** (GitHub Releases API) and compares `tag_name` numerically against the running version. It runs automatically for administrators after login, and on demand from the changelog modal. Rules for any new release:

- **Tag the release `vX.Y.Z`** — the leading `v` is optional (`1.2.0` works too), but the tag must be exactly three numbers. Anything else, a pre-release suffix such as `-rc.1` included, is rejected as an invalid release: the automatic check stays silent, and a manual check reports an error.
- **Not a draft, not a prerelease** — `releases/latest` never returns those, so a prerelease never triggers the prompt (by design: it prompts only for *stable* updates).
- **Numerically greater than the version users run** — the comparison is per segment (major, minor, patch). A suffix on the running version is ignored: a build made five commits after `v1.2.0` reports `v1.2.0-5-g<sha>` and counts as `1.2.0`.
- **The release *name* is free-form** — the prompt never reads it: the comparison uses `tag_name`, and the modal shows the tag.
- **The image must be on GHCR** — images carry the version without the `v`: release `v1.2.0` publishes `1.2.0` (full), plus `1.2.0-light` and `latest` (light), see [Docker Images and Tags](#docker-images-and-tags). Before prompting, the frontend asks the backend, through the authenticated endpoint `GET /api/v1/system/container-image-status?tag=1.2.0`, whether the release's `X.Y.Z` image is published. The backend performs GHCR's anonymous token handshake, which a browser cannot complete through CORS, then sends a manifest `HEAD` request for `ghcr.io/librefolio/librefolio:X.Y.Z`. A `404` means `pending`: no prompt yet, and a manual check reports the image as pending. Any other failure is an `error`, and the check fails closed. The full `X.Y.Z` image is the pipeline's last push, after `X.Y.Z-light` and `latest`: no administrator is prompted while the release run is still building, or when it fails before that push (a failed light build included), and when the prompt does appear, every tag of the release already exists.

See also `.github/copilot-instructions.md` → "Changelog Rules" for the CHANGELOG.md conventions the in-app changelog modal renders.

---

## 📂 Core Commands & Implementation Details

### 🧰 1. Runner, Caches and Setup

The job runs on `ubuntu-latest`, deliberately left unpinned. It checks out the full history (`fetch-depth: 0`: `mkdocs gh-deploy` needs the branches, and the version stamp needs the tags), then sets up Python 3.13, Pipenv and Node.js 24.

Three caches are restored before anything is installed:

| Cache | Path | Key, after the `<runner.os>-<RUNNER_IMAGE_OS>-` prefix |
|-------|------|--------------------------------------------------------|
| Pipenv virtualenv | `~/.local/share/virtualenvs` | `pipenv-` and the hash of `Pipfile.lock`; the restore key falls back to the newest `pipenv-` entry |
| npm | `~/.npm` | `node-` and the hash of the `package-lock.json` files; the restore key falls back to the newest `node-` entry |
| Playwright browsers | `~/.cache/ms-playwright` | `playwright-` and the `@playwright/test` version of `frontend/package.json`; exact match only |

The Pipenv key, for example:

```yaml
key: ${{ runner.os }}-${{ env.RUNNER_IMAGE_OS }}-pipenv-${{ hashFiles('**/Pipfile.lock') }}
```

Every key includes `RUNNER_IMAGE_OS` because `ubuntu-latest` changes Ubuntu release over time (24.04 → 26.04, see `actions/runner-images#14748`), while `runner.os` is `Linux` on both: keyed on it alone, a virtualenv or a browser build made on one image would be restored on the other. The step «Expose the runner image for cache keys» exports the runner's `ImageOS` variable (for example `ubuntu24`) as `RUNNER_IMAGE_OS` through `$GITHUB_ENV`, with `unknown` as fallback: `ImageOS` is an environment variable of the runner, not part of the expression `env` context.

The installation then runs:

```bash
pipenv install --dev
# «Generate VERSION file for Docker», «Freeze the app version for the frontend builds»
pipenv run ./dev.py install        # pipenv install --dev again, npm ci at the root and in frontend/, Playwright Chromium
# «[CHECK] Checkout after dev.py install» (warning only)
pipenv run ./dev.py front build
# «[CHECK] Checkout after the frontend build» (warning only)
```

The two steps after `pipenv install --dev` freeze the version before any step that could write tracked files: the backend's in `VERSION`, the app's in `LF_APP_VERSION`. The `[CHECK]` steps never fail; they name a step that changed the checkout. [Version Stamps and a Clean Checkout](#version-stamps) describes both.

`dev.py install` installs the root project's tools with `npm ci`, like the frontend's dependencies: `npm ci` installs `package-lock.json` exactly as committed, never rewrites it, and fails when it no longer matches `package.json`. Commit a change to the root `package.json` with its updated `package-lock.json`, as in `frontend/`.

### 🧪 2. Documentation Checks, Gallery and Rebuilds

The documentation steps run in this order:

```bash
pipenv run ./dev.py mkdocs translate-diff --issues-only
pipenv run ./dev.py mkdocs translate-validate --hide-localized
pipenv run ./dev.py mkdocs check-links
pipenv run ./dev.py mkdocs build                # mkdocs build --strict
# «[CHECK] Checkout after the docs build» (warning only)
pipenv run ./dev.py mkdocs gallery --workers 4
# «[CHECK] Checkout after the gallery» (warning only)
pipenv run ./dev.py front build                 # production rebuild, for the images
pipenv run ./dev.py mkdocs build                # rebuild, with the screenshots
```

- **The site is built before the gallery.** The gallery's test server serves `/mkdocs`, and the gallery's build step (next bullet) builds the site only when `mkdocs_src/site/` is missing or older than its pages: here it finds the site up to date. The order dates from when that build ran inside the startup window of Playwright's webServer, where building the site once made the gallery time out; the build step now runs before Playwright starts, outside that window.
- **The gallery always runs.** There is no screenshot cache, and no input to skip or force the step: every run regenerates the screenshots. `dev.py mkdocs gallery` populates the test database, prepares the test server with its build step, `dev.py server --test --build-only` (in the foreground, with the environment it then gives Playwright; a failed build stops the gallery there), runs `frontend/e2e/gallery.spec.ts` for the `desktop` and `mobile` Playwright projects, and writes the PNGs under `mkdocs_src/docs/gallery/`, where they are gitignored. The webServer's `dev.py server --test` then finds its builds up to date and starts in seconds. `--workers 4` matches the 4 vCPUs of the `ubuntu-latest` runners for public repositories: 8 workers oversubscribed them, and the CPU contention made a different test time out on each run. The step's timeout is 120 minutes.
- **The frontend is rebuilt for production.** The gallery's build step rebuilds `frontend/build/` in debug mode (no minification, sourcemaps), the kind `dev.py server --test` serves. The images copy `frontend/build/`, so `dev.py front build` runs again. The `Dockerfile`'s `frontend` stage refuses anything else: `scripts/docker/check_frontend_build.sh` fails the image build on a debug build, a coverage-instrumented build or any sourcemap. Like the first build, both rebuilds take the app's version from `LF_APP_VERSION` (see [Version Stamps and a Clean Checkout](#version-stamps)).
- **The site is rebuilt with the screenshots.** The first build had none. The full image ships the rebuilt `mkdocs_src/site/` as is; the light image's docs stage deletes the screenshots again.
- **Each build checks its own output.** Once `mkdocs build --strict` succeeds, `dev.py` resolves every relative file URL of the built site (images, video and audio, links to files) from its page's folder, as a browser does, and exits 1 on a broken one, which fails the step. It catches, for example, a raw-HTML image path that a translation copied unchanged from the English: the translated page is built one folder deeper (`site/<lang>/...`), so the path is one `../` short; `translate-validate` reports such a copy earlier, as `html-asset-depth` (see [Validation Checks](translation-pipeline.md#validation-checks)).

The ordering is pinned by `./dev.py test utils release-image-contract` (`backend/test_scripts/test_utilities/test_release_image_contract.py`): a production frontend build and a docs build between the gallery and both image builds, a nightly report that reads every soft-gated step, and a `Dockerfile` that takes `frontend/build/` only through the checked stage. The same test also pins the `RUNNER_IMAGE_OS` cache keys, the gallery's release gate and its failure-report upload, the release, nightly and manual-from-`main` tags of [Docker Images and Tags](#docker-images-and-tags), the prerelease rule (no `latest`, no deploy, no `:latest` line), the [release tag guard](#prereleases) (`-rc.N` for prereleases, plain `vX.Y.Z` for stable releases), the image-build guards, the light-before-full build order, and the tags the release notes pull, which it checks by running the step's script in bash with a stand-in `gh`. It also pins the [version stamps and the clean checkout](#version-stamps): the `LF_APP_VERSION` export right after `VERSION` and before every frontend build, `vite.config.ts` preferring it to `git describe` (run in node with a stand-in `git`), the four checkout checks and the outputs of their script, `npm ci` at the root of `dev.py install`, and the icon record — the generators redraw a set only when its source's hash or recipe changes, never because of the PNG bytes, and the committed record matches the committed logos.

#### Release gate and nightly tolerance {: #release-gate-and-nightly-tolerance }

Six steps carry `continue-on-error: ${{ github.ref_name == 'dev' }}`:

| Step | Command (`pipenv run ./dev.py …`) |
|------|-----------------------------------|
| Check MkDocs translation structure consistency | `mkdocs translate-diff --issues-only` |
| Validate broken MkDocs translation links | `mkdocs translate-validate --hide-localized` |
| Validate cross-boundary links | `mkdocs check-links` |
| Build MkDocs Documentation | `mkdocs build` |
| Generate Screenshots with Playwright | `mkdocs gallery --workers 4` |
| Rebuild MkDocs Documentation (with the gallery screenshots) | `mkdocs build` |

- **On `dev`**, the nightly continues past a failure. The step «Report soft-failed steps (nightly)», which runs on `dev` only and with `always()`, lists the failed steps in a "⚠️ Soft-failed steps" section of the job summary and raises a warning annotation. After a failed gallery, the nightly ships the screenshots that succeeded; the documentation loads the missing ones from the public site (`mkdocs_src/docs/javascripts/gallery-img-loader.js`).
- **On any other run**, a published release included, a failure stops the pipeline: no image is pushed, the site is not deployed, and the release notes are not updated; only the [artifact steps](#artifacts) still run. On a release, `github.ref_name` is the tag (for example `v1.2.0`), so the expression is false. The reason: the full image bundles the gallery and a release deploys the documentation site, so a release must not ship missing or broken screenshots. The GitHub release itself is already published at that point, but the in-app update prompt stays silent, because the image tag never reaches GHCR (see [Release Tag Convention](#release-tag-convention)).

### 🔢 3. Version Stamps and a Clean Checkout {: #version-stamps }

The backend and the app each compute their version with `git describe --tags --always --dirty`, which appends `-dirty` as soon as a tracked file differs from the commit. The job freezes both right after `pipenv install --dev`, before any step that could write tracked files, and every later step reads the frozen value:

| Version | Shown in | Frozen by | Read by |
|---------|----------|-----------|---------|
| Backend | `GET /api/v1/system/info` (`app_version`, the one field it also answers without a session), Settings → About | «Generate VERSION file for Docker», which writes `VERSION` with `get_git_version()` (`backend/app/utils/runtime/version.py`); the next step exports it as `LF_APP_VERSION` | `get_git_version()`, once per process, takes the first source that gives a version: `LF_APP_VERSION` when it is set and not blank (`frozen_app_version()`, `backend/app/config/platform.py`); `git describe` where the project root has `.git` (a folder, or a file in a worktree or a submodule); a `VERSION` file that is not blank; otherwise `unknown`. The job's servers read `LF_APP_VERSION`. The image has no `.git/` and does not set the variable, so the `Dockerfile` copies `VERSION` |
| App | The sidebar, and the changelog modal it opens (`APP_VERSION`, `frontend/src/lib/version.ts`) | «Freeze the app version for the frontend builds», which runs `echo "LF_APP_VERSION=$(cat VERSION)" >> "$GITHUB_ENV"` | `getAppVersion()` in `frontend/vite.config.ts`, at every frontend build: `LF_APP_VERSION` when it is set and not blank, `git describe` otherwise |

Both read `LF_APP_VERSION` first, so in the job the backend reports the same frozen version as the frontend builds. Without the variable, as in every local checkout and every install, `git describe` decides wherever there is `.git`: a `VERSION` file left over by an earlier `./dev.py docker build` cannot hide newer commits. `.env.example` lists `LF_APP_VERSION` commented out, under «App Version»: leave it unset. The `version` of `pyproject.toml` and of `frontend/package.json` (with the two root entries of `package-lock.json`), `0.0.0` in all of them, is not the app's version: nothing reads it, so no release has to update it.

`VERSION` alone freezes only the backend's version in the images. Vite compiles the app's version into the bundle, and the job builds the frontend three times, each after steps that may write tracked files: the first `dev.py front build`, the debug rebuild of the gallery's build step, and the production rebuild for the images. The gallery's server starts its backend after such steps too. Before `LF_APP_VERSION`, the published 1.1 gallery showed `v1.1.0-dirty` in the sidebar, and the nightly of 2026-10-12 `v1.1.0-1390-g85170bc1f-dirty`. Written to `$GITHUB_ENV`, `LF_APP_VERSION` reaches every later step of the job, the same job for nightlies, manual runs and releases:

- **The gallery.** `dev.py mkdocs gallery` passes its environment to its build step, `dev.py server --test --build-only`, and to Playwright, which passes its own to its webServer, `dev.py server --test`: the build step's debug rebuild (the sidebar of every screenshot) and the webServer's backend (Settings → About) both carry the frozen version.
- **The images.** The `Dockerfile` builds no frontend: both variants copy the production `frontend/build/` that the job built with `LF_APP_VERSION` set, and `VERSION` for the backend.

Locally `LF_APP_VERSION` is unset, and every build and server reads `git describe`. Set on a command, it gives the frontend builds and the servers of that command a chosen version, for example to rehearse a release gallery the way the job builds it:

```bash
LF_APP_VERSION=v1.2.0 ./dev.py front build       # production build, as in the job
LF_APP_VERSION=v1.2.0 ./dev.py mkdocs gallery    # its build step rebuilds in debug mode, with the same version
```

- **It reaches only the builds and servers the command starts.** The gallery's build step rebuilds `frontend/build/` only when it is missing, older than its sources, or not a debug build, hence the production build first: a debug build already up to date would be reused, with the version it carries.
- **It changes the backend's version too.** `get_git_version()` reads it first, so the server the gallery starts shows it in Settings → About, like the sidebar.
- **It leaves no file behind**, only the version compiled into `frontend/build/` until its next build. A `VERSION` file would change neither version: in a checkout `get_git_version()` reads it only when `git describe` fails, and the app's version never reads it. `./dev.py docker build` is different: it writes `get_git_version()`, and so the variable, into `VERSION`, `frontend/build/.build-version` and the image tags (see [Local image builds](#local-image-builds)).

#### Local image builds {: #local-image-builds }

`./dev.py docker build` and `./dev.py docker rebuild` freeze the version of a local image too, without the job (all the steps: [What `./dev.py docker build` Does](../dev_workflow.md#docker-build-steps)). `_docker_ensure_assets_built()` asks `get_git_version()` once, before any step that could write a tracked file, and gives the answer to both versions of the image:

- **The app.** `_docker_ensure_frontend_built()` rebuilds `frontend/build/` in production mode, with `LF_APP_VERSION` set to the frozen version for that build only, unless `_docker_frontend_stale_reason()` finds that the bundle already fits: sources not newer than the build, `.build-debug` saying it is a production build, and `frontend/build/.build-version` holding the frozen version. It writes `.build-version` after its build. Every frontend build empties `frontend/build/`, so the file exists only when the last build was made for an image: any other build is rebuilt once, and so is the bundle of an earlier image after a new commit, even one that touched no frontend file.
- **The backend.** `VERSION` receives the same version at the end, and the `Dockerfile` copies it.

The sidebar and `GET /api/v1/system/info` therefore report the same version in a locally built image. The image tags are computed apart: `_get_docker_tag()` clears `get_git_version()`'s cache and asks again after the asset steps, so a step that changed a tracked file adds `-dirty` to the tags, not to the versions inside the image.

#### Checkout checks {: #checkout-checks }

Four warning-only steps, «[CHECK] Checkout after dev.py install», «[CHECK] Checkout after the frontend build» (the first `front build`), «[CHECK] Checkout after the docs build» (the first `mkdocs build`) and «[CHECK] Checkout after the gallery», each run `sh scripts/ci/warn_if_tree_changed.sh "<step>"` right after the step they name. The script compares the checkout with its commit through `git status --porcelain`, and its log reads:

- **`Checkout unchanged after <step>.`**: nothing changed, and no annotation.
- **The `git status --porcelain` list, then a warning «Checkout changed after <step>»**, also shown as an annotation on the run's summary page. The warning counts tracked and untracked (`??`) paths apart. Tracked changes are the ones that make `git describe --dirty` read `-dirty`; untracked paths are files a step wrote that Git does not ignore, and do not change the version.
- **A warning «Checkout check failed after <step>»**: `git status` itself failed, and the message carries its error.

The script always exits 0: the checks diagnose, they do not gate, on nightlies and releases alike. Each compares the checkout with the commit, not with the previous check, so a change stays in every later warning: the first check that warns names the step that made it, and the lists of two consecutive checks show what the steps between them added. Before these checks, the logs of the v1.1.0 release run and of the nightly of 2026-10-12 already showed `dev.py install` leaving the checkout clean (the `git status --short` it prints after its npm installs is empty): the checkout changed later, and the known cause is the icons below.

#### Generated icons {: #generated-icons }

`dev.py` draws two icon sets with Pillow: `generate_favicon()` writes `frontend/static/favicon.png` from `logo.png`, and `generate_pwa_icons()` the five PWA icons of `frontend/static/icons/` from `logo_square.png` (see [PWA → Icon Generation](../frontend/pwa.md#icon-generation)). `dev.py front build` runs the first, and every docs build runs both through `copy_docs_assets()`, which then copies them into `mkdocs_src/docs/static/`. All these PNGs are tracked, and Pillow does not guarantee the same bytes for the same image on every platform: regenerated on the runner, unchanged icons became modified files.

A set is therefore regenerated only when one of its outputs is missing, or when `frontend/generated-icons.json` does not record its current source and recipe. That file, committed with the icons, holds one entry per set, `favicon` and `pwa-icons`, with the source's path and sha256 and the recipe number, `FAVICON_RECIPE` or `PWA_ICONS_RECIPE` in `dev.py`. A regeneration rewrites the set's entry; otherwise the set is left untouched, and the log says so (`favicon.png is up to date (logo.png unchanged)`). The decision reads the source's hash, never the outputs' bytes, which can differ from one platform to another.

| To | Do |
|----|----|
| Change a logo | Replace `frontend/static/logo.png` or `logo_square.png` and run `./dev.py mkdocs build`, which regenerates the set, rewrites its entry and copies the icons into `mkdocs_src/docs/static/`. Commit the changed files under both `static/` folders together with `frontend/generated-icons.json`: without the new entry, every other checkout, the runner's included, would regenerate the set again |
| Change what a function draws | Bump its recipe number, `FAVICON_RECIPE` or `PWA_ICONS_RECIPE`: without the bump the record still matches, and the change never reaches the icons |
| Force a regeneration | Delete the set's entry from `frontend/generated-icons.json` (or the whole file), or one of its outputs, then build again |

### 🐳 4. Docker Images and Tags {: #docker-images-and-tags }

`pipenv requirements > requirements.txt` generates the requirements the `Dockerfile` installs. The job then sets up QEMU and Buildx, and logs in to GHCR with the workflow's `GITHUB_TOKEN`. Two `docker/metadata-action` steps compute the tags, and two `docker/build-push-action` steps build `ghcr.io/librefolio/librefolio` from the repository root and push it, sharing the GitHub Actions layer cache (`type=gha`, `mode=max`). The light variant is built and pushed first:

1. **Light variant** — the build with `DOCS_VARIANT=light`: the `Dockerfile`'s `docs-light` stage deletes the documentation images before they reach the final image.
2. **Full variant** — the default `Dockerfile` build, with the documentation screenshots.

The order serves the in-app update prompt, which checks the plain `X.Y.Z` tag, the full variant's (see [Release Tag Convention](#release-tag-convention)). Pushed last, that tag appears only once `X.Y.Z-light` and `latest` exist. If the light build fails, the full build does not run (an `if:` without a status function implies `success()`), so `X.Y.Z` is never pushed and no one is prompted.

Each build runs only when its own metadata step yields a tag: `if: steps.meta-light.outputs.tags != ''` for the light build, `if: steps.meta.outputs.tags != ''` for the full one. A push without a tag can only fail (buildx: `tag is needed when pushing to registry`), so a variant with nothing to publish is skipped instead.

Neither build sets `platforms`, so each image is built for the runner's platform (linux/amd64).

What the two variants contain, and which tag users should pick, is specified for users in [Installation → Image Variants](../../user/installation.md#image-variants-full-and-light). The tags the two metadata steps compute:

| Run | Light variant (pushed first) | Full variant (pushed last) |
|-----|------------------------------|----------------------------|
| Stable release `vX.Y.Z` published | `X.Y.Z-light`, `latest` | `X.Y.Z` |
| Prerelease `vX.Y.Z-rc.N` published, e.g. `v1.2.0-rc.1` | `X.Y.Z-rc.N-light` | `X.Y.Z-rc.N` |
| Push to `dev`, or manual run from `dev` | `nightly-light` | `nightly` |
| Manual run from `main` | `latest` | none: build skipped |
| Manual run from any other branch | none: build skipped | none: build skipped |

- **No `v` in image tags.** The version tags are `docker/metadata-action`'s `{{version}}`: release `v1.2.0` publishes `1.2.0`, not `v1.2.0`. Only the GitHub release tag has the `v`, and the in-app update prompt accepts both forms.
- **`latest` is the light variant, moved only by a stable release or a manual run from `main`.** `docker/metadata-action` adds `latest` on its own whenever a `type=semver` tag matches a stable version, if the flavor is `latest=auto`. The full-variant step sets `flavor: latest=false`. The light step uses `auto` only for a release that is not a GitHub prerelease, and `false` for every other run; its raw `latest` tag is enabled only on `main`. Hence:
    - a GitHub prerelease publishes only its own version tags, `X.Y.Z-rc.N` and `X.Y.Z-rc.N-light`: the [release tag guard](#prereleases) lets no other tag through, and the `false` flavor would keep `latest` in place on any tag;
    - a stable release reaches these steps only on a plain `vX.Y.Z` tag, which the same guard enforces: on a tag such as `v1.3.0-rc.1`, `latest` would stay in place, since under `auto` metadata-action skips semver pre-releases;
    - the flavor is never `latest=true`, which would add `latest` to every raw tag as well, `nightly-light` included.

    `latest-light` is no longer published: `latest` itself is the light variant.

```yaml
# Extract Docker Metadata (Version): full variant
flavor: |
  latest=false
tags: |
  type=semver,pattern={{version}}
  type=raw,value=nightly,enable=${{ github.ref_name == 'dev' }}

# Extract Docker Metadata (Light Variant)
flavor: |
  latest=${{ (github.event_name == 'release' && !github.event.release.prerelease) && 'auto' || 'false' }}
tags: |
  type=semver,pattern={{version}},suffix=-light
  type=raw,value=latest,enable=${{ github.ref_name == 'main' }}
  type=raw,value=nightly-light,enable=${{ github.ref_name == 'dev' }}
```

!!! note "Why the full variant turns `latest` off"

    Before this setting, both variants pushed `latest`, and the light one won only because it was pushed second. With `latest=false` on the full variant, `latest` no longer depends on the push order, which now puts the light variant first.

### 🌍 5. Documentation Deployment

```yaml
if: github.ref_name == 'main' || (github.event_name == 'release' && !github.event.release.prerelease)
run: pipenv run ./dev.py mkdocs deploy
```

`dev.py mkdocs deploy` copies the documentation assets and runs `mkdocs gh-deploy --force -f mkdocs_src/mkdocs.yml`, which builds the site again and force-pushes it to the `gh-pages` branch as `github-actions[bot]` (configured by the «Setup Git User» step). The step comes after the image builds. Its condition keeps both `dev` changes and GitHub prereleases off the public site: only a stable release or a manual run from `main` deploys it. A manual run from `main` reaches the step after pushing only the light `latest` image, the full build being skipped.

### 🗂️ 6. Artifacts {: #artifacts }

Two steps archive the gallery's output:

| Artifact | Content | Kept | Uploaded |
|----------|---------|------|----------|
| `playwright-screenshots` | The gallery PNGs, `mkdocs_src/docs/gallery/**/*.png` (not the gallery's Markdown pages) | 1 day | On every run that is not cancelled, a failed one included |
| `playwright-gallery-report` | `frontend/playwright-report/` (the HTML report) and `frontend/test-results/` | 3 days | Only when the gallery step failed, on `dev` too, where that failure is soft |

Both steps run under `!cancelled()`, so a failed step earlier in the job does not skip them: the gallery fails a release, and a failed run is when the screenshots and the report are most useful. Both also set `if-no-files-found: ignore`. The report step adds `steps.gallery.outcome == 'failure'`, which also holds on `dev`, where `continue-on-error` keeps the job going. On CI, Playwright retries a failed test twice and records a trace and a video on the first retry, plus a screenshot on failure: the report carries them. No later run restores either artifact: they are for inspection.

### 📝 7. Release Notes

On a release (`github.event.release.tag_name` is set), the last step appends a "📦 Docker Installation" section to the release notes. `gh release edit` has no option to append, so the step reads the current notes and writes them back with the section added:

```bash
TAG_NAME="${{ github.event.release.tag_name }}"
IMAGE_TAG="${TAG_NAME#v}"   # image tags have no leading "v"
# DOCKER_CMD: the "📦 Docker Installation" section, built with printf from IMAGE_TAG;
# the :latest line only when PRERELEASE (github.event.release.prerelease) is not "true"
CURRENT_NOTES=$(gh release view "$TAG_NAME" --json body -q .body)
gh release edit "$TAG_NAME" --notes "${CURRENT_NOTES}${DOCKER_CMD}"
```

For the stable release `v1.2.0`, the appended commands are:

```bash
# Latest release, light variant (documentation screenshots load from the online docs site)
docker pull ghcr.io/librefolio/librefolio:latest

# This release, full variant (documentation fully offline)
docker pull ghcr.io/librefolio/librefolio:1.2.0

# This release, light variant
docker pull ghcr.io/librefolio/librefolio:1.2.0-light
```

A prerelease's section has only the last two commands, with its own version: a prerelease does not move `latest`, so its notes have no `:latest` line.
