# ⚙️ Settings System

LibreFolio has a two-tiered settings system — **User Settings** (per-user preferences) and
**Global Settings** (instance-wide, admin-managed) — held together by a single declarative
catalogue, `SETTINGS_REGISTRY`.

!!! info "A third layer, outside these two tiers: process configuration (`.env`)"

    Startup values (ports, data folder, log level, instance profile, secrets, risk-engine workers)
    come from `.env` and the environment; the admin-facing list is
    [Configuration](../../admin/configuration.md). How they load:

    - `Settings(BaseSettings)` in `backend/app/config/__init__.py` reads the project-root `.env`;
      environment variables override it, names are case-sensitive, unknown keys are ignored.
    - `get_settings()` builds a fresh, validated instance on every call. `main.py` calls it at
      import, so a mistyped or out-of-range value stops the startup. It also computes
      `DATABASE_URL` and applies the `LIBREFOLIO_LOG_LEVEL` override.
    - `get_data_dir()` picks the data root: in test mode `LIBREFOLIO_TEST_DATA_DIR` or
      `backend/data/test` (refused if it overlaps production), otherwise `LIBREFOLIO_DATA_DIR`,
      otherwise `backend/data/prod`.
    - Keys outside the class — `LIBREFOLIO_DATA_DIR`, `LIBREFOLIO_TEST_DATA_DIR`,
      `LIBREFOLIO_TEST_MODE`, `LIBREFOLIO_LOG_LEVEL`, `JWT_SECRET`, `LIBREFOLIO_INSTANCE_KEY` (both
      also as `_FILE`), `LIBREFOLIO_NO_SCHEDULER`, `LIBREFOLIO_DISABLE_DONATION_POPUP`,
      `LIBREFOLIO_REGISTRATION`, `LIBREFOLIO_MAX_USERS`, `LIBREFOLIO_PUBLIC_URL`,
      `LIBREFOLIO_BILLING_URL`, `LIBREFOLIO_TEST_LANE_ID`, `LF_APP_VERSION` (the version a release
      job or `./dev.py docker build` freezes), `LIBREFOLIO_BLOCKED`, `LIBREFOLIO_DELETION_DATE`,
      `LIBREFOLIO_WEB_LINK_FINDER_*` (the API key also as `_FILE`) — are read in
      `backend/app/config/` (base or section module), from
      `os.environ` only. pydantic-settings does not export `.env` there, so they arrive through the
      launcher: `./dev.py server` copies `.env` into the environment (shell values win), Compose uses
      `env_file:`.
    - Secrets go through `env_secret(name)` in `__init__.py`: `NAME` when it is not blank, otherwise
      the content of the file named by `NAME_FILE` when that is not blank (Docker and Kubernetes
      secrets), otherwise `None`. Blank means empty or whitespace only, so a stray space never becomes
      a key. A `NAME_FILE` that cannot give its secret, an empty or blank file included, raises
      `SecretFileError`; the full rules are in
      [Security → Secrets from Files](security.md#secrets-from-files). A new secret is named
      `LIBREFOLIO_*` and read with `env_secret()`: its `_FILE` form then works, and the startup check
      of secrets set twice covers it without a list to update. `INSTANCE_TRUST_SECRETS` lists, in
      both forms, the secrets that a test runtime never inherits (`configure_test_runtime()` in
      `scripts/cli_base.py`), like the rest of the instance's configuration: see
      [Security → Test lanes and the instance's configuration](security.md#test-lanes-and-the-instances-configuration).
    - `backend/app/config/` is a package; the import path is still `backend.app.config`.
      `__init__.py` is the base: constants, data directories, test mode, the secret reader
      `env_secret()`, `Settings` and `get_settings()`. New variables go into one section module per
      topic, owned by the workstream of that area. Four exist today: `platform.py` (H:
      `scheduler_disabled()`, `configured_jwt_secret()`, `configured_jwt_secret_origin()`,
      `configured_instance_key()`, `configured_instance_key_origin()`, `owning_test_lane_id()`,
      `frozen_app_version()`, `instance_blocked()`, `instance_deletion_date()`),
      `accounts.py` (A: `donation_popup_disabled()`, `registration_mode_override()`,
      `registration_mode_pinned()`, `max_users()`, `public_url()`, `billing_url()`), `plugins.py`
      (X: `web_link_finder_enabled()`, `web_link_finder_engine()`, `web_link_finder_api_key()`,
      `web_link_finder_ddgs_region()`, `web_link_finder_ddgs_backend()`, `web_link_finder_timeout()`,
      `web_link_finder_max_results()`) and `email.py` (E: `smtp_host()`, `smtp_tls_mode()`,
      `smtp_port()`, `smtp_user()`, `smtp_password()`, `smtp_sender()`, `smtp_reply_to()`,
      `smtp_max_per_hour()`; see [Email Service](../backend/email.md#configuration)). `sleep_wake.py`
      and `backup.py` will follow when their areas add variables. Unlike a `Settings` field, an
      invalid `LIBREFOLIO_REGISTRATION`, `LIBREFOLIO_MAX_USERS`, `LIBREFOLIO_PUBLIC_URL` or
      `LIBREFOLIO_BILLING_URL` never stops the startup: its accessor raises `ValueError`, and
      `registration_service.py` logs it and falls back safely — registration closed for the first
      two, the bare path or no billing link for the URLs
      ([Registration Modes](access_control.md#registration-modes)).
    - The rule: every environment variable of the application is read inside
      `backend/app/config/`. A module elsewhere calls a function there instead of reading
      `os.environ`. The rule holds with no exception, and a guard test checks it (runner selector
      `services config-package`, file `backend/test_scripts/test_services/test_config_package.py`).
    - `.env.example`, at the repository root, documents the variables, grouped by function. A new
      variable goes into its section as a commented line that shows the default: the uncommented
      lines must not change, because the file becomes `/app/.env` in the Docker image. A guard test
      checks that the variables the code reads, the `Settings` fields and the variables of the
      compose files are documented there, and that the uncommented lines stay the same (runner
      selector `services config-env-example`, file
      `backend/test_scripts/test_services/test_env_example.py`).

## 🗃️ Two storage models, kept separate on purpose

| | User Settings | Global Settings |
|---|---|---|
| Storage | **Typed columns** on the per-user `UserSettings` row | **Key-value rows** in the `GlobalSetting` table |
| Who writes | The user themselves (`PUT /api/v1/settings/user`) | Admins only (**Admin** tab of Settings, or `PATCH /api/v1/settings/global/bulk`) |
| Examples | `language`, `base_currency`, `theme`, `avatar_url` | `session_ttl_hours`, `registration_mode`, `scheduler_*`, `default_currency` … |

The split is a deliberate design decision (P2-9), not an accident of history: per-user
preferences are fixed in number and benefit from typed columns with defaults on row creation,
while global settings are an open-ended key space that admins extend without migrations.
`settings_service.py` (user + global CRUD) and `global_settings_service.py` (typed read helpers
for global keys) stay separate services for the same reason.

Admins manage global settings from the **Admin** tab of Settings (`GlobalSettingsTab.svelte`:
lock-gated, with the scheduler dialogs and `CachePanel`, writing through the bulk-update endpoint).
Missing rows are seeded at every startup by the `global-settings` step of the lifespan
(`_initialize_global_settings()` in `backend/app/services/platform/app_lifespan.py`); the same
idempotent seeding is available from the CLI:

```bash
./dev.py user init-settings        # creates only missing keys (INSERT ... ON CONFLICT DO NOTHING)
```

or via `POST /api/v1/settings/global/initialize` (admin only, same idempotent semantics).

How global values behave at runtime:

- Values are stored as strings next to their `value_type`; `get_setting_value()` in
  `global_settings_service.py` converts them on read (`int`; `bool`, true for
  `true`/`1`/`yes`/`on`; `json`). An unparsable `int` reads as `0`; a missing row falls back to
  `GLOBAL_SETTINGS_DEFAULTS`.
- Every read goes to the database, with no cache, so a saved value reaches all workers at once:
  this is why admin changes need no restart.
- `PATCH /api/v1/settings/global/bulk` (`update_global_settings()` in `settings_service.py`) is all
  or nothing: a key that does not exist answers `404`; a key an environment variable pins answers
  `409` `SETTING_LOCKED_BY_ENV`, with `key` and `variable` in `detail` (today only
  `registration_mode`, pinned while `LIBREFOLIO_REGISTRATION` is set, valid or not: `_PINNED_BY_ENV`);
  a value refused by its type or by its entry in `GLOBAL_SETTINGS_CONSTRAINTS` (ranges, choices,
  formats) answers `422`, naming every refused key. Only then are all the values written, in one
  commit. The scheduler dialog also checks its own ranges before saving: 1–1440 minutes, 1–365
  days, at least one time and one day.
- While its variable is set, a pinned row decides nothing and cannot be written:
  `GET /api/v1/settings/global` still returns the stored `registration_mode`, and the mode in force
  is in `GET /system/instance` ([below](#public-instance-configuration)). The Admin tab shows that
  one, read-only, and its **Reset All to Defaults** leaves the field alone
  ([Settings components](../frontend/components/features/settings.md)).

## 📖 SETTINGS_REGISTRY — the single declaration point

Every known setting key is declared **once** in `backend/app/schemas/settings.py`:

```python
@dataclass(frozen=True, slots=True)
class SettingSpec:
    key: str                              # storage key (GlobalSetting row key or UserSettings column)
    location: Literal["user", "global"]   # which storage model holds it
    value_type: str                       # "str" | "int" | "bool" | "json"
    description: str
```

The registry exposes two namespaces mirroring the storage models:

- `SETTINGS_REGISTRY.user` — one `SettingSpec` per `UserSettings` column
  (`BASE_CURRENCY`, `LANGUAGE`, `THEME`, `AVATAR_URL`);
- `SETTINGS_REGISTRY.global_` — one `SettingSpec` per `GlobalSetting` key, built by
  `_global_spec()`, which derives `value_type` and `description` **from
  `GLOBAL_SETTINGS_DEFAULTS`** so the defaults table stays the single source for both seeding
  and metadata.

The global keys declared today, and where the **Admin** tab shows them
([admin view](../../admin/settings.md)):

| Key | Type | Default | In the Admin tab |
|-----|------|---------|------------------|
| `session_ttl_hours` | int | `24` | Session → **Session Duration** |
| `registration_mode` | str | `open` | Security → **Registration**: `open`, `invite` or `disabled` (`SettingConstraint(choices=…)`). Read-only while `LIBREFOLIO_REGISTRATION` is set: see [Registration Modes](access_control.md#registration-modes) |
| `require_email_verification` | bool | `false` | Security → **Require Email Verification** — read-only placeholder (`PLACEHOLDER_KEYS`) |
| `max_file_upload_mb` | int | `10` | Memory → **Max File Upload Size** |
| `scheduler_enabled` | bool | `true` | Update Job → **Scheduler Enabled** (label from `settings.globalSettingNames.scheduler_enabled`) |
| `scheduler_current_price_frequency_minutes` | int | `10` | Schedule Configuration dialog → **Refresh every** |
| `scheduler_history_sync_times` | str | `06:00,23:00` | Schedule Configuration dialog → **Sync times** |
| `scheduler_history_sync_days` | str | `mon,tue,wed,thu,fri,sat` | Schedule Configuration dialog → **Sync days** |
| `scheduler_history_sync_horizon_days` | int | `14` | Schedule Configuration dialog → **Lookback horizon** |
| `scheduler_timezone` | str | `UTC` | Schedule Configuration dialog → **Timezone** |
| `default_currency` | str | `EUR` | Defaults → **Default Currency** |
| `default_language` | str | `en` | Defaults → **Default Language** |
| `default_theme` | str | `auto` | Defaults → **Default Theme** |

The five `scheduler_*` keys after `scheduler_enabled` never appear as fields: `GlobalSettingsTab.svelte`
hides them (`SCHEDULER_HIDDEN_KEYS`) and `SchedulerConfigModal.svelte` writes them in one bulk call.

### 📌 Call-site convention

Call sites reference registry constants instead of re-declaring raw string literals:

```python
await get_setting_value(session, SETTINGS_REGISTRY.global_.DEFAULT_CURRENCY.key, "EUR")
```

As of 2026-09-03 there are 19 such references across the four call-site files
(`settings_service.py`, `global_settings_service.py`, `scheduler/settings.py`,
`api/v1/settings.py`). The legitimate exceptions are Alembic migrations and tests that
deliberately exercise raw keys.

!!! note "Adding a new setting"

    1. Add the key to `GLOBAL_SETTINGS_DEFAULTS` (global) with value/type/description — this is
       what seeds fresh installs.
    2. Add the matching constant under `SETTINGS_REGISTRY.global_` via `_global_spec(key)`.
    3. Reference the constant at the call site. A user-facing label/hint also needs i18n keys
       and, if it appears in the Global tab, a category in `GlobalSettingsTab.svelte`.

## 💱 Base currency resolution: `get_effective_base_currency`

`settings_service.get_effective_base_currency(session, user_id)` answers *"which currency does
this user's portfolio report in?"* with an explicit chain:

1. the per-user `UserSettings.base_currency` — wins whenever a settings row exists;
2. the admin-level global `default_currency`;
3. `"EUR"` as the last-resort constant.

New `UserSettings` rows are seeded **from** the global defaults at creation
(`get_or_create_user_settings`), so the global default reaches users who never chose, while an
explicit user choice always wins afterwards.

!!! warning "Why this helper exists (audit 08, P0-1)"

    It replaced a **phantom `base_currency` global key** that was never registered anywhere:
    every reader silently fell back to `EUR` regardless of the configured default. Any new code
    that needs "the user's base currency" must call this helper — the three current consumers
    are `financial_math/portfolio/engine.py`, `portfolio_service.py`, and `lots_analysis_service.py`.

## 🌍 Public instance configuration {: #public-instance-configuration }

`GET /api/v1/system/instance` answers, without a session, what the web app needs to know about the
instance before anyone signs in. The app reads it at startup: the `(app)` layout calls
`instanceConfig.load()` when it mounts, before the auth check, and works with a self-hosted default
until the server answers (see [Instance configuration](../frontend/state/app-state.md#instance-config)).
Its response is `InstanceConfigResponse` (`backend/app/schemas/system.py`), and today it has two fields:

| Field | Values | Source |
|-------|--------|--------|
| `profile` | `selfhosted`, an install run by its owner, or `managed`, an instance a hosting provider runs for its customers | `LIBREFOLIO_PROFILE`, a field of `Settings`, so it comes from `.env` or the environment like `PORT`. Default `selfhosted`; case and spaces around the value are ignored, and any other value stops the startup. Admin side: [Configuration](../../admin/configuration.md). |
| `accounts` | `{registration_mode, registration_locked}` (`AccountsInstanceConfig`, `backend/app/schemas/auth.py`): the registration mode in force, `open`, `invite` or `disabled`, and whether `LIBREFOLIO_REGISTRATION` pins it | `effective_registration_mode()` (workstream A, `registration_service.py`): the variable, otherwise the `registration_mode` row, so the endpoint is `async`, with a database session. No count and no limit. Details: [Registration Modes](access_control.md#registration-modes). |

The rule for a workstream that owns part of the public configuration:

- it adds **one** field to `InstanceConfigResponse`, typed with a model of its own schemas;
- it fills that field in `get_instance_config()` (`backend/app/api/v1/system/instance.py`) with one
  call to its service;
- the field holds only what is public and the same for whoever asks: nothing private, nothing that
  depends on the user or the session.

After `./dev.py api sync`, the field appears in the frontend type `InstanceConfig`, inferred from the
generated client.

## 🧹 Related: cache administration

The named-cache registry (theine TTL caches used by services) and its admin endpoints under
`/api/v1/settings/cache/*` are documented in [Cache Registry & Admin](settings_cache.md).
