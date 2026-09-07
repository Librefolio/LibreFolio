# ⚙️ Settings System

LibreFolio has a two-tiered settings system — **User Settings** (per-user preferences) and
**Global Settings** (instance-wide, admin-managed) — held together by a single declarative
catalogue, `SETTINGS_REGISTRY`.

## 🗃️ Two storage models, kept separate on purpose

| | User Settings | Global Settings |
|---|---|---|
| Storage | **Typed columns** on the per-user `UserSettings` row | **Key-value rows** in the `GlobalSetting` table |
| Who writes | The user themselves (`PUT /api/v1/settings/user`) | Admins only (Global Settings tab, or `PATCH /api/v1/settings/global/bulk`) |
| Examples | `language`, `base_currency`, `theme`, `avatar_url` | `session_ttl_hours`, `enable_registration`, `scheduler_*`, `default_currency` … |

The split is a deliberate design decision (P2-9), not an accident of history: per-user
preferences are fixed in number and benefit from typed columns with defaults on row creation,
while global settings are an open-ended key space that admins extend without migrations.
`settings_service.py` (user + global CRUD) and `global_settings_service.py` (typed read helpers
for global keys) stay separate services for the same reason.

Admins manage global settings from the **Settings → Global** page (lock-gated UI backed by
`CachePanel`, scheduler configuration, and the bulk-update endpoint). Seeding missing rows on a
fresh install can also be done from the CLI:

```bash
./dev.py user init-settings        # creates only missing keys (INSERT ... ON CONFLICT DO NOTHING)
```

or via `POST /api/v1/settings/global/initialize` (admin only, same idempotent semantics).

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
