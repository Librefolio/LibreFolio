# ⚙️ Settings System

LibreFolio has a two-tiered settings system — **User Settings** (per-user preferences) and
**Global Settings** (instance-wide, admin-managed) — held together by a single declarative
catalogue, `SETTINGS_REGISTRY`. The settings that plugins declare for themselves are a separate
system: see [Plugin Settings](patterns/plugin_settings.md).

!!! info "A third layer, outside these two tiers: process configuration (`.env`)"

    Startup values (ports, data folder, log level, instance profile, secrets, risk-engine workers)
    come from `.env` and the environment; the admin-facing list is
    [Configuration](../../admin/configuration.md). How they load:

    - `Settings(BaseSettings)` in `backend/app/config/__init__.py` reads the project-root `.env`;
      environment variables override it, names are case-sensitive, unknown keys are ignored.
    - `get_settings()` builds a fresh, validated instance on every call. `main.py` calls it at
      import, so a mistyped or out-of-range value stops the startup. It also computes
      `DATABASE_URL` and applies the `LIBREFOLIO_LOG_LEVEL` override.
    - **Profile defaults** (`PROFILE_DEFAULTS` in `__init__.py`, decisions D5 and F27): for each
      profile `LIBREFOLIO_PROFILE` accepts, the values it gives the `Settings` fields that the
      environment and `.env` leave unset. `selfhosted` lists none: a self-hosted install keeps every
      code default. `managed` sets `RISK_SIMULATION_IDLE_TIMEOUT_SECONDS` and
      `RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS` to `60.0` and turns on `LIBREFOLIO_FRAME_PROTECTION` and
      `LIBREFOLIO_CSP_REPORT_ONLY`, two `bool` fields off in the code
      ([Frame Protection and the Report-Only Policy](security.md#managed-headers)).
      `Settings._apply_profile_defaults`, a `model_validator(mode="after")`, gives the active
      profile's value (`LIBREFOLIO_PROFILE` already normalised by its field validator) to every listed
      field that is not in `model_fields_set`. pydantic-settings passes every value a source found, so
      a value the operator set wins even when it equals the code default:
      `RISK_SIMULATION_IDLE_TIMEOUT_SECONDS=600` or `LIBREFOLIO_FRAME_PROTECTION=false` stay on a
      managed instance. The value is written with `object.__setattr__`, not by assignment: an
      assignment would add the field to `model_fields_set`, and later code could no longer tell an
      operator's value from the profile's. Either way the value is not validated (`Settings` has no
      `validate_assignment`), so `./dev.py test services profile-defaults`
      (`backend/test_scripts/test_services/test_profile_defaults.py`) checks the table strictly: one
      entry per profile `LIBREFOLIO_PROFILE` accepts; every key a `Settings` field with a code default;
      every value valid for its field in strict mode and, for `managed`, different from the code
      default; a set value kept; and, parametrised over every field any profile lists, the code
      default kept by a self-hosted install. The table reaches `Settings` fields only; the variables
      of the section modules have their own table, in the next point. To give a `Settings` field a
      new managed default, a workstream adds one entry to `PROFILE_DEFAULTS["managed"]`: a field with
      a code default, and a value of the field's own type, written as its code default is (`60.0`,
      `True`; never `"60"`, nor `1` for a flag), that differs from the code default. It adds the same
      entry to `MANAGED_DEFAULTS` in the test file, the decided table that
      `PROFILE_DEFAULTS["managed"]` must equal; the parametrised cases (the managed value given to a
      field nobody set, the guards on the table, the self-hosted code defaults) then cover the new
      field. A new security `Settings` field states its managed value there in the same lot, or says
      why `managed` keeps the code default: a review rule, row «Config & Data Paths» of
      `.github/instructions/backend.instructions.md`. At run time nothing refuses a managed entry lost
      from the table, nor a value an operator sets: for the two security switches, the configuration
      checks `platform.frame_protection`, a `warning`, and `platform.csp_report_only`, an `info`, show
      a managed instance where either is off (H-39; see
      [Configuration Checks](security.md#configuration-checks)).
    - **Profile defaults of the section modules' variables** (`ENVIRONMENT_PROFILE_DEFAULTS` in
      `__init__.py`): for each profile, the values it gives the variables that a section module of
      `backend/app/config/` reads from `os.environ`, outside `Settings`. `selfhosted` lists none: a
      self-hosted install keeps every code default. A section module calls
      `profile_default(name, fallback)`, and only while its variable is unset. Under `selfhosted` the
      function returns `fallback` itself, the code's own default. Any other profile (today `managed`)
      must list `name`, and the function returns that profile's value: a name it does not list raises
      `ProfileDefaultError` (H-37), naming the variable, the profile and the table, and the reader
      stops. A missing entry thus fails closed instead of quietly giving a managed instance the
      self-hosted behaviour (no upload limit for a restore, below). The profile is
      `get_settings().LIBREFOLIO_PROFILE`, read at each call. A blank or an invalid value stays under
      the module's own rules: a module can, for example, treat a blank value as unset, and answer an
      invalid one with a coded error when the value is used rather than stop the startup.
      `profile_default()` converts nothing, but checks the active profile's entry before returning
      it: the entry must be of the exact type of `fallback`, the reader's own default (`500` for the
      fallback `0`; never `None`, `"500"`, `500.0` nor `True`: `True` does not pass for an `int`
      fallback, nor `60` for a `float` one). An entry of any other type raises `ProfileDefaultError`
      too, a `TypeError` defined in `__init__.py` whose message names the variable, the profile, both
      types and the table, and the reader stops instead of using the value: unchecked, a `None` under
      `managed` would mean no upload limit at all for a restore (`backup_max_upload_mb()`, below).
      Under `selfhosted`, the fallback itself is returned unchecked. Both checks, for a missing entry
      and for an entry's type, run at the reader's call, never as a startup check of their own: only
      the reader knows the variables it reads and the type it expects; the table is code, guarded before
      release by the tests below; and a startup refused for one missing entry would take every managed
      instance down, where a reader that stops closes only the feature that reads it. The backup's
      startup checks call the upload limit's reader, and only log its error
      ([Configuration Checks of the Backup](security.md#backup-config-checks)).
      The first entry is the upload limit of a restore:
      `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`, `500` megabytes in `managed` (decision 43), read by
      `backup_max_upload_mb()` in `config/backup.py` with `profile_default(MAX_UPLOAD_VARIABLE, 0)`: no limit on a
      self-hosted install. Since B-35 the same entry also bounds a restore's check: `LIBREFOLIO_BACKUP_MAX_RESTORE_MB`,
      the most an archive may unpack to, read by `backup_max_restore_mb()` in the same module, is, when unset,
      `RESTORE_TO_UPLOAD_RATIO` (8) times the upload limit in any profile but `selfhosted` (4000 megabytes in
      `managed`; `0`, no limit, when the upload limit is none), and `0` under `selfhosted`; an explicit value always
      wins, `0` meaning no limit.
      `./dev.py test services profile-defaults` guards this table too: one entry per profile;
      `selfhosted` empty; `managed` equal, value and type, to `ENVIRONMENT_MANAGED_DEFAULTS`, the
      decided table of the test file; no key that is a `Settings` field or sits in both tables; every
      key read, as a string constant, by a section module, and documented in `.env.example`; for
      every listed name, `profile_default()` returning the fallback under `selfhosted` and the
      table's value under `managed`; under `managed`, a name the table does not list raising
      `ProfileDefaultError`, as an entry of another type does, while `selfhosted` still gets the
      fallback; the real `backup_max_upload_mb()` raising on a `None` managed entry, and on a managed
      entry removed, instead of lifting the limit; and, read in the sources, every
      `profile_default(NAME, …)` call of a section module written with a literal fallback, checked
      both ways: every entry of the table read by such a call, of exactly the type of the call's
      fallback, and every call's `NAME` listed by every profile but `selfhosted` (H-37). Two
      self-tests check that the guard reports a broken table: `None` for the managed entry of the
      upload limit (the type), and that entry removed (the listing).
      To read a new variable through `profile_default`, a workstream adds its entry to
      `ENVIRONMENT_PROFILE_DEFAULTS["managed"]`: mandatory, even at the fallback's own value when
      `managed` keeps the self-hosted behaviour, since a name `managed` does not list raises. It adds
      the same entry to `ENVIRONMENT_MANAGED_DEFAULTS` in the test file, says the managed value in the
      variable's commented line of `.env.example`, and calls `profile_default(NAME, fallback)` in its
      section module while the variable is unset, with a literal fallback of the variable's own type,
      as the upload limit's `0`. Admin view of both tables:
      [The Managed Profile](../../admin/hosting_providers.md#managed-profile).
    - `get_data_dir()` picks the data root: in test mode `LIBREFOLIO_TEST_DATA_DIR` or
      `backend/data/test` (refused if it overlaps production), otherwise `LIBREFOLIO_DATA_DIR`,
      otherwise `backend/data/prod`.
    - Keys outside the class — `LIBREFOLIO_DATA_DIR`, `LIBREFOLIO_TEST_DATA_DIR`,
      `LIBREFOLIO_TEST_MODE`, `LIBREFOLIO_LOG_LEVEL`, `JWT_SECRET`, `LIBREFOLIO_INSTANCE_KEY` (both
      also as `_FILE`), `LIBREFOLIO_NO_SCHEDULER`, `LIBREFOLIO_DISABLE_DONATION_POPUP`,
      `LIBREFOLIO_DISABLE_WHATS_NEW` (both hidden switches, set by `./dev.py server --test` on every
      test lane, decision D-A7; the second turns off the «What's new» window of lot C-54),
      `LIBREFOLIO_REGISTRATION`, `LIBREFOLIO_MAX_USERS`, `LIBREFOLIO_PUBLIC_URL`,
      `LIBREFOLIO_BILLING_URL`, `LIBREFOLIO_LOGIN_LIMIT`, `LIBREFOLIO_SUPPORT_URL`, `LIBREFOLIO_TOS_URL`,
      `LIBREFOLIO_PRIVACY_URL`, `LIBREFOLIO_TEST_LANE_ID`, `LF_APP_VERSION` (the version a release
      job or `./dev.py docker build` freezes), `LIBREFOLIO_BLOCKED`, `LIBREFOLIO_DELETION_DATE`,
      `LIBREFOLIO_WEB_LINK_FINDER_*` (the API key also as `_FILE`), the variables of the plugin
      settings (`LIBREFOLIO_PLUGIN_*` and the aliases of secret fields, all also as `_FILE`), the order
      of the asset providers in the search (`LIBREFOLIO_ASSET_PROVIDERS_PREMIUM`,
      `LIBREFOLIO_ASSET_PROVIDERS_ORDER`) — are
      read in `backend/app/config/` (base or section module), from
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
    - Addresses go through `env_url(name)` in `__init__.py`, one rule for every `LIBREFOLIO_*_URL`:
      an empty or blank value is `None`; otherwise the value, stripped, must be an `http://` or
      `https://` address with a host name (a name, an IPv4 or an IPv6 address, with a port or not),
      no user info (no `@` in its authority, as in `https://user:pass@host`: the user name and the
      password would be handed out with the address; an `@` in the path, the query or the fragment is
      not user info) and no space, tab or line break inside, and one trailing slash is removed;
      anything else, `https://` alone included, raises `ValueError`, which names the variable and
      quotes the value, unless the value holds an `@` anywhere: it may carry a user name or a
      password, so the message never quotes it. The accessor's caller decides what an invalid address
      costs, and logs the error. `support_url()` (`platform.py`) also takes
      `mailto:` and one email address, the scheme in any case: `?`, `#`, `%`, `,`, `;`, `<`, `>`, `"`,
      `/` and any whitespace are refused before pydantic's `EmailStr` reads the address, without DNS,
      and it returns `mailto:` and the address as `EmailStr` normalizes it. `env_url()` itself stays
      http(s) only, and so do `tos_url()` and `privacy_url()`, in the same module, which return
      `env_url()` of their variable.
    - `backend/app/config/` is a package; the import path is still `backend.app.config`.
      `__init__.py` is the base: constants, data directories, test mode, the secret reader
      `env_secret()`, the address reader `env_url()`, `Settings` and `get_settings()`. New variables
      go into one section module per topic, owned by the workstream of that area. Seven exist today:
      `platform.py` (H: `scheduler_disabled()`, `configured_jwt_secret()`, `configured_jwt_secret_origin()`,
      `configured_instance_key()`, `configured_instance_key_origin()`, `owning_test_lane_id()`,
      `frozen_app_version()`, `instance_blocked()`, `instance_deletion_date()`, `support_url()`, and
      `tos_url()` and `privacy_url()`, the legal pages, written by A),
      `accounts.py` (A: `donation_popup_disabled()`, `registration_mode_override()`,
      `registration_mode_pinned()`, `max_users()`, `public_url()`, `billing_url()`,
      `login_limit_value()` and `login_limit_enabled()`, the switch of the
      [limit on failed sign-ins](security.md#login-limit), and
      `admin_bootstrap_config()`, the [initial administrator](access_control.md#initial-admin), its
      token also as `_FILE`), `plugins.py`
      (X: `web_link_finder_enabled()`, `web_link_finder_engine()`, `web_link_finder_api_key()`,
      `web_link_finder_ddgs_region()`, `web_link_finder_ddgs_backend()`, `web_link_finder_timeout()`,
      `web_link_finder_max_results()`, `plugin_setting_env()` and `plugin_setting_env_origin()`
      for the [plugin settings](patterns/plugin_settings.md#environment), and
      `asset_providers_premium()` and `asset_providers_order()` for the
      [search order](patterns/asset_plugin_guide.md#search-order)), `email.py` (E: `smtp_host()`, `smtp_tls_mode()`,
      `smtp_port()`, `smtp_user()`, `smtp_password()`, `smtp_sender()`, `smtp_reply_to()`,
      `smtp_max_per_hour()`; see [Email Service](../backend/email.md#configuration)),
      `sleep_wake.py` (Z: the pauses a provider gets after answering HTTP 429,
      `provider_cooldown_base_seconds()`, `provider_cooldown_max_seconds()` and
      `provider_cooldown_settings()`; the shutdown budget, `shutdown_timeout_seconds()`, and
      uvicorn's share of it, `shutdown_drain_seconds()` and `uvicorn_drain_env()`; see
      *Stopping the Server* in [Configuration](../../admin/configuration.md); the token of the
      scheduled wake-up, `wake_token()`, also as `_FILE`, with the rules of the panel's backup token;
      see [Scheduled Wake-up](../../admin/sleep_wake.md#wake-sync); the idle suspension,
      `idle_suspend_mode()` and `idle_suspend_minutes()`; see
      [Idle Suspension](../../admin/sleep_wake.md#idle-suspend)), `backup.py` (B:
      `backup_download_token()`, the token a hosting panel presents to download the instance's
      backups, also as `_FILE`) and `brim.py` (W: `brim_prewarm_enabled()`, the opt-in
      [warm-up of the BRIM parse pool](../backend/brim/architecture.md#parse-pool-warm-up), which
      raises `BrimConfigError` on a value it cannot use). Unlike a `Settings` field, an
      invalid `LIBREFOLIO_REGISTRATION`, `LIBREFOLIO_MAX_USERS`, `LIBREFOLIO_PUBLIC_URL` or
      `LIBREFOLIO_BILLING_URL` never stops the startup: its accessor raises `ValueError`, and
      `registration_service.py` logs it and falls back safely — registration closed for the first
      two, the bare path or no billing link for the URLs
      ([Registration Modes](access_control.md#registration-modes)). An invalid
      `LIBREFOLIO_SUPPORT_URL` does not either: `support_link()`
      (`services/platform/instance_links.py`) logs it once, and `GET /system/instance` answers
      `support_url: null`, so the app keeps its link to the project's GitHub issues. Nor does an
      invalid `LIBREFOLIO_TOS_URL` or `LIBREFOLIO_PRIVACY_URL`: `terms_link()` and `privacy_link()`,
      in the same module, log it once per process, the same `Invalid instance link` error with its
      own `consequence`, and `GET /system/instance` answers `null` for that link in `legal`: the legal
      notice shows without it. An unusable
      `LIBREFOLIO_ADMIN_*` value does stop it, as `admin_bootstrap_config()` runs in the startup audit,
      and so does a `LIBREFOLIO_LOGIN_LIMIT` other than `on` or `off`: `login_limit_enabled()` runs
      right after it.
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
| Who reads | The user themselves (`GET /api/v1/settings/user`) | Any signed-in user (`GET /api/v1/settings/global`, `GET /api/v1/settings/global/{key}`): `401` without a session. The login page reads none of them: what it needs before sign-in is in [`GET /system/instance`](#public-instance-configuration) |
| Who writes | The user themselves (`PUT /api/v1/settings/user`) | Admins only (**Global Settings** tab of Settings › Administration, or `PATCH /api/v1/settings/global/bulk`) |
| Examples | `language`, `base_currency`, `theme`, `avatar_url` | `session_ttl_hours`, `registration_mode`, `scheduler_*`, `default_currency` … |

The split is a deliberate design decision (P2-9), not an accident of history: per-user
preferences are fixed in number and benefit from typed columns with defaults on row creation,
while global settings are an open-ended key space that admins extend without migrations.
`settings_service.py` (user + global CRUD) and `global_settings_service.py` (typed read helpers
for global keys) stay separate services for the same reason.

**A stored theme the app does not know** (lot A-11). `UserSettings.theme` is a plain column, so a
row edited by hand, a global `default_theme` edited by hand and copied into new rows, or a theme of a
later release after a downgrade can hold a value outside the `Literal` of `UserSettingsRead.theme`
(`light`, `dark`, `auto`, read into `KNOWN_THEMES` in `settings_service.py`). Every answer that
carries the user's settings — `POST /api/v1/auth/login`, `POST /api/v1/auth/setup`,
`GET /api/v1/settings/user` and `PUT /api/v1/settings/user` — builds them with `_settings_read()`,
which shows such a theme as the instance's `default_theme` when that is a known theme, otherwise
`auto` (`FALLBACK_THEME`), and logs one WARNING per read, with `user_id`, `stored` (cut to 20
characters) and `shown`. Reading never rewrites the row, so a release that knows the theme shows it
again; a `PUT` without `theme` keeps the stored value, and a `PUT` with `theme` replaces it. Before,
building `UserSettingsRead` raised, and the answer was a `500`: at sign-in, after the login had set its
cookie, so the user could not sign in. Tests: `./dev.py test api settings`,
`TestStoredThemeUnknownToTheApp` (SET-A11-01 to SET-A11-07, in-process on a private database).

Admins manage global settings from the **Global Settings** tab of Settings › Administration
(`GlobalSettingsTab.svelte`: lock-gated, with the scheduler dialogs and `CachePanel`, writing through
the bulk-update endpoint).
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
  is in `GET /system/instance` ([below](#public-instance-configuration)). The Global Settings tab
  shows that one, read-only, and its **Reset All to Defaults** leaves the field alone
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

The global keys declared today, and where the **Global Settings** tab shows them
([admin view](../../admin/settings.md)):

| Key | Type | Default | In the Global Settings tab |
|-----|------|---------|------------------|
| `session_ttl_hours` | int | `24` | Session → **Session Duration** |
| `registration_mode` | str | `invite` | Security → **Registration**: `open`, `invite` or `disabled` (`SettingConstraint(choices=…)`). `invite` since decision 36: a new install seeds it, an existing row is kept, and an install with accounts but no row gets `open` from migration `008_registration_invite_default`. The startup that creates the [initial administrator](access_control.md#initial-admin) writes `invite` too. Read-only while `LIBREFOLIO_REGISTRATION` is set: see [Registration Modes](access_control.md#registration-modes) |
| `require_email_verification` | bool | `false` | Security → **Require Email Verification**: every account created by `POST /auth/register` but the first waits for an emailed link ([Email Verification](../backend/email.md#verification)). It turns on only while an email with a link can go out: the switch is disabled while its saved value is off and `email.links` of `GET /system/instance` is false, and `PATCH /settings/global/bulk` refuses an off-to-on change with 409 `EMAIL_VERIFICATION_UNAVAILABLE` (`GlobalSettingUnavailableError`). Turning it off always works |
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

Both are written only as ISO 4217 alphabetic codes: the global `default_currency` through the settings layer's own
check, a user's `base_currency` (`PUT /settings/user`, the welcome flow) through `IsoCurrencyCode` since E-19a. Before,
the user's field checked only its length, so an API client could store `978` or `XYZ`; such a stored value is reported
by the stored-currency check (admin guide, [Command-Line Tools](../../admin/cli_tools.md), «Currency Codes That Are Not
ISO Codes»).

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
Its response is `InstanceConfigResponse` (`backend/app/schemas/system.py`), and today it has five fields:

| Field | Values | Source |
|-------|--------|--------|
| `profile` | `selfhosted`, an install run by its owner, or `managed`, an instance a hosting provider runs for its customers | `LIBREFOLIO_PROFILE`, a field of `Settings`, so it comes from `.env` or the environment like `PORT`. Default `selfhosted`; case and spaces around the value are ignored, and any other value stops the startup. Admin side: [Configuration](../../admin/configuration.md). The web app shows the **Buy Me a Coffee** links of the header, the Help menu, the sign-in pages and Settings › About, the update check (at an administrator's sign-in, and **Check for updates** in the changelog) and the server commands of **Forgot Password?** only once the answer says `selfhosted`: see [Instance configuration](../frontend/state/app-state.md#instance-config). |
| `accounts` | `{registration_mode, registration_locked, first_account_open, password_rules}` (`AccountsInstanceConfig`, `backend/app/schemas/auth.py`): the registration mode in force, `open`, `invite` or `disabled`; whether `LIBREFOLIO_REGISTRATION` pins it; whether the instance has no account yet, so that the next registration creates the first account, an administrator, whatever the mode; and the rules every new password must meet, in order, `[{code, value}]` (`PasswordRuleRead`, `value` only for `min_length`) | `effective_registration_mode()` (workstream A, `registration_service.py`): the variable, otherwise the `registration_mode` row, so the endpoint is `async`, with a database session. `first_account_open()`, in the same module: true while the `users` table is empty, an inactive account counted; optional in the schema, default `false`. `password_rules_public()` (`password_policy.py`): the same list on every instance; optional in the schema, default empty, and the app then assumes the rules of release 1.3. No count and no limit. Details: [Registration Modes](access_control.md#registration-modes); why the flag may be public: [The First-Account Flag](security.md#first-account-open); the rules: [Password Rules](security.md#password-rules). |
| `email` | `{available, links}` (`EmailInstanceConfig`, `backend/app/schemas/email.py`): `available`, whether the instance can send emails now, an SMTP server set and every `LIBREFOLIO_SMTP_*` variable usable; `links`, whether emails with a link can go out too, `LIBREFOLIO_PUBLIC_URL` set to an http(s) address; never the configuration itself | `email_instance_config()` (workstream E, `services/email/links.py`), run in a worker thread since it may read the password file. Both booleans default to `false`, so the field is optional in the schema. Details: [Email Service](../backend/email.md#instance-email). |
| `support_url` | Where the users ask for help: an `http(s)` page, or `mailto:` and one email address; `null` when unset or invalid | `support_link()` (workstream H, `services/platform/instance_links.py`), from `LIBREFOLIO_SUPPORT_URL` through `support_url()` (`config/platform.py`, above). Optional in the schema, default `null`. Its reader is the asset search's «Let us know» row: [Asset Search & Link-Finder](../backend/assets/search_link_finder.md). |
| `legal` | `{terms_url, privacy_url}` (`LegalInstanceConfig`, `backend/app/schemas/system.py`): the instance's own terms of service and privacy policy, each an `http(s)` page or `null` | `terms_link()` and `privacy_link()` (workstream A, F09, `services/platform/instance_links.py`), from `LIBREFOLIO_TOS_URL` and `LIBREFOLIO_PRIVACY_URL` through `tos_url()` and `privacy_url()` (`config/platform.py`: the rule of `env_url()`, no `mailto:`). They never raise: a value they cannot use is logged once per process, `Invalid instance link` with its `consequence`, and published as `null`, as an unset one is. Both default to `null`, so the field is optional in the schema. Its readers are the two components of the legal notice, `LegalNotice` and `LegalLinks` ([Settings Components](../frontend/components/features/settings.md#legal-notice)). Admin side: [Hosting for Others](../../admin/hosting_providers.md#legal-pages). |

The rule for a workstream that owns part of the public configuration:

- it adds **one** field to `InstanceConfigResponse`, typed with a model of its own schemas;
- it fills that field in `get_instance_config()` (`backend/app/api/v1/system/instance.py`) with one
  call to its service;
- the field holds only what is public and the same for whoever asks: nothing private, nothing that
  depends on the user or the session.

After `./dev.py api sync`, the field appears in the frontend type `InstanceConfig`, inferred from the
generated client.

The `legal` part has two runner entries of its own: `./dev.py test services legal-links`
(`backend/test_scripts/test_services/test_legal_links.py`: the two variables by the rule of
`env_url()`, published without ever raising, an invalid one logged once without its secret) and
`./dev.py test api instance-legal` (`backend/test_scripts/test_api/test_instance_config_legal_api.py`:
the field set, unset and invalid, `null` and still `200`, the schema and the OpenAPI document, and one
anonymous read on the lane's server, which sets neither variable).

## 🧹 Related: cache administration

The named-cache registry (theine TTL caches used by services) and its admin endpoints under
`/api/v1/settings/cache/*` are documented in [Cache Registry & Admin](settings_cache.md).
