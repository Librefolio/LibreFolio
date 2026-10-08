# ⚙️ Settings System

LibreFolio has a two-tiered settings system — **User Settings** (per-user preferences) and
**Global Settings** (instance-wide, admin-managed) — held together by a single declarative
catalogue, `SETTINGS_REGISTRY`.

!!! info "A third layer, outside these two tiers: process configuration (`.env`)"

    Startup values (ports, data folder, log level, risk-engine workers) come from `.env` and the
    environment; the admin-facing list is [Configuration](../../admin/configuration.md). How they
    load:

    - `Settings(BaseSettings)` in `backend/app/config.py` reads the project-root `.env`;
      environment variables override it, names are case-sensitive, unknown keys are ignored.
    - `get_settings()` builds a fresh, validated instance on every call. `main.py` calls it at
      import, so a mistyped or out-of-range value stops the startup. It also computes
      `DATABASE_URL` and applies the `LIBREFOLIO_LOG_LEVEL` override.
    - `get_data_dir()` picks the data root: in test mode `LIBREFOLIO_TEST_DATA_DIR` or
      `backend/data/test` (refused if it overlaps production), otherwise `LIBREFOLIO_DATA_DIR`,
      otherwise `backend/data/prod`.
    - Keys outside the class — `LIBREFOLIO_DATA_DIR`, `LIBREFOLIO_TEST_MODE`, `JWT_SECRET`,
      `LIBREFOLIO_WEB_LINK_FINDER_*`, `LIBREFOLIO_NO_SCHEDULER` — are read from `os.environ`.
      pydantic-settings does not export `.env` there, so they arrive through the launcher:
      `./dev.py server` copies `.env` into the environment (shell values win), Compose uses
      `env_file:`.

## 🗃️ Two storage models, kept separate on purpose

| | User Settings | Global Settings |
|---|---|---|
| Storage | **Typed columns** on the per-user `UserSettings` row | **Key-value rows** in the `GlobalSetting` table |
| Who writes | The user themselves (`PUT /api/v1/settings/user`) | Admins only (**Admin** tab of Settings, or `PATCH /api/v1/settings/global/bulk`) |
| Examples | `language`, `base_currency`, `theme`, `avatar_url` | `session_ttl_hours`, `enable_registration`, `scheduler_*`, `default_currency` … |

The split is a deliberate design decision (P2-9), not an accident of history: per-user
preferences are fixed in number and benefit from typed columns with defaults on row creation,
while global settings are an open-ended key space that admins extend without migrations.
`settings_service.py` (user + global CRUD) and `global_settings_service.py` (typed read helpers
for global keys) stay separate services for the same reason.

Admins manage global settings from the **Admin** tab of Settings (`GlobalSettingsTab.svelte`:
lock-gated, with the scheduler dialogs and `CachePanel`, writing through the bulk-update endpoint).
Missing rows are seeded at every startup by the lifespan (`_initialize_global_settings()` in
`main.py`); the same idempotent seeding is available from the CLI:

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
- `PATCH /api/v1/settings/global/bulk` stores values as sent, with no type or range check. The
  ranges live in the UI: the scheduler dialog accepts 1–1440 minutes and 1–365 days, and needs
  at least one time and one day.

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
| `enable_registration` | bool | `true` | Security → **Enable Registration** |
| `require_email_verification` | bool | `false` | Security → **Require Email Verification** — read-only placeholder (`PLACEHOLDER_KEYS`) |
| `max_file_upload_mb` | int | `10` | Memory → **Max File Upload Size** |
| `scheduler_enabled` | bool | `true` | Update Job → **Scheduler Enabled** (label derived from the key: no `globalSettingNames` entry) |
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
    are `portfolio_engine.py`, `portfolio_service.py`, and `lots_analysis_service.py`.

## 🧹 Related: cache administration

The named-cache registry (theine TTL caches used by services) and its admin endpoints under
`/api/v1/settings/cache/*` are documented in [Cache Registry & Admin](settings_cache.md).
