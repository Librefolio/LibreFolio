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
| `scheduler_enabled` | bool | `true` | Enable or disable the automatic background synchronization daemon for exchange rates and historical/real-time prices. |
| `scheduler_current_price_frequency_minutes` | int | `10` | Frequency (in minutes) with which the daemon updates current real-time prices (1-1440). |
| `scheduler_history_sync_times` | str | `06:00,23:00` | Specific daily times (server local time, comma-separated) to trigger the end-of-day history sync. |
| `scheduler_history_sync_days` | str | `mon,tue,wed,thu,fri,sat` | Specific days of the week (comma-separated) to run the historical synchronization. |
| `scheduler_history_sync_horizon_days` | int | `14` | Rolling retrospective analysis window (in days) used to check for missing historical prices. |
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
- 🕐 `scheduler_enabled` — Enable or disable the background scheduler
- ⚡ `scheduler_current_price_frequency_minutes` — Real-time price refresh frequency
- 📅 `scheduler_history_sync_times` — Daily history sync times
- 📅 `scheduler_history_sync_days` — Weekly history sync days
- 🔍 `scheduler_history_sync_horizon_days` — History sync analysis horizon (in days)
- 📦 `max_file_upload_mb` — File size limit

### 🌍 Defaults
- 💰 `default_currency` — New user default currency
- 🗣️ `default_language` — New user default language

---

## 🕐 Market Data Scheduler

When the background scheduler is enabled, administrators can configure synchronization parameters and inspect background execution logs directly from the user interface.

### ⚙️ Configure Scheduler

Click the **Configure** button in the Scheduler row to customize execution frequencies and parameters:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Scheduler Configuration Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

* **Current Price Frequency**: The frequency (in minutes) at which the daemon fetches real-time quotes to keep the dashboard cache updated (default: 10m).
* **History Sync Times**: Specific daily times (comma-separated, e.g., `06:00,23:00`) to run historical daily close updates.
* **History Sync Days**: Specific days of the week when historical synchronization is performed (usually Monday to Saturday).
* **History Horizon**: The analysis window (in days) to check for missing historical price points (default: 14 days).

### 📜 Scheduler Logs

Click **View Logs** to open the log inspector. This modal displays a list of recent scheduler executions:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Scheduler Log Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

The log reports the execution timestamp, job name, status (Success/Error), execution duration, and structured details of processed assets, price feeds, and any error traces.

---

## 🔧 Technical Notes

- 🗃️ Settings are stored as **key-value pairs** in the `global_settings` table
- 🔀 Values are stored as strings and converted to the appropriate type (`int`, `bool`, `str`) when read
- 🔒 On multi-worker startup, settings are initialized with `INSERT ... ON CONFLICT DO NOTHING` to avoid race conditions
- ⚡ Changes take effect **immediately** — no server restart required
