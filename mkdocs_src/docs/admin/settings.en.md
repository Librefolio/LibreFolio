# ⚙️ Global Settings

LibreFolio has a set of **system-wide settings** that affect all users. These are managed by administrators and stored in the database.

---

## 👁️ Viewing & Editing Settings

### 🖥️ From the UI

1. Navigate to **Settings** (gear icon in the sidebar)
2. Click the **Global Settings** tab (visible only to admin/superuser)
3. Click the **lock icon** next to a setting to unlock it for editing
4. Modify the value and the change is saved automatically

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Global Settings" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! warning "Admin Only"

    Only users with **superuser** privileges can modify global settings. Regular users see a read-only view.

### 💻 From the CLI

To initialize default settings (creates only missing ones):

```bash
./dev.py user init-settings
```

---

## 📋 Available Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `session_ttl_hours` | int | `24` | JWT token expiration time in hours. After this period, users must log in again. |
| `enable_registration` | bool | `true` | Whether new user registration is allowed. Set to `false` to prevent new sign-ups. |
| `require_email_verification` | bool | `false` | Whether new users must verify their email before accessing the system. |
| `max_file_upload_mb` | int | `10` | Maximum file upload size in megabytes. Applies to all uploads (static resources and broker reports). |
| `auto_sync_fx_rates` | bool | `true` | Enable automatic daily synchronization of FX exchange rates from configured providers. |
| `auto_sync_prices` | bool | `true` | Enable automatic synchronization of asset prices from providers (Yahoo Finance, etc.). |
| `price_sync_interval_hours` | int | `6` | How often to sync asset prices, in hours. |
| `default_currency` | str | `EUR` | Default display currency for newly registered users. Users can override this in their personal settings. |
| `default_language` | str | `en` | Default language for newly registered users. Supported: `en`, `it`, `fr`, `es`. |

---

## 🗂️ Categories

Settings are grouped into categories in the UI:

### 🕐 Session
- ⏱️ `session_ttl_hours` — Controls how long a login session lasts

### 🛡️ Security
- 📝 `enable_registration` — Open/close registration
- ✉️ `require_email_verification` — Email verification gate

### 📤 Sync & Uploads
- 💱 `auto_sync_fx_rates` — Automatic FX rate sync
- 📈 `auto_sync_prices` — Automatic asset price sync
- ⏰ `price_sync_interval_hours` — Price sync frequency
- 📦 `max_file_upload_mb` — File size limit

### 🌍 Defaults
- 💰 `default_currency` — New user default currency
- 🗣️ `default_language` — New user default language

---

## 🔧 Technical Notes

- 🗃️ Settings are stored as **key-value pairs** in the `global_settings` table
- 🔀 Values are stored as strings and converted to the appropriate type (`int`, `bool`, `str`) when read
- 🔒 On multi-worker startup, settings are initialized with `INSERT ... ON CONFLICT DO NOTHING` to avoid race conditions
- ⚡ Changes take effect **immediately** — no server restart required
