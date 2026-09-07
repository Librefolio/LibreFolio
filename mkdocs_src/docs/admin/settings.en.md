# ⚙️ Global Settings

LibreFolio has a set of **system-wide settings** that affect all users. These are managed by administrators and stored in the database.

---

## 👁️ Viewing & Editing Settings

### 🖥️ From the UI

1. Navigate to **Settings** (gear icon in the sidebar)
2. Click the **Global Settings** tab (visible to all users; only admin/superuser can edit)
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

## 🕐 Session

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `session_ttl_hours` | int | `24` | JWT token expiration time in hours. After this period, users must log in again. |

## 🛡️ Security

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enable_registration` | bool | `true` | Whether new user registration is allowed. Set to `false` to prevent new sign-ups. |
| `require_email_verification` | bool | `false` | **Placeholder — not enforced yet.** Whether new users must verify their email before accessing the system. Email sending (SMTP) is a planned feature, so in the UI this setting is read-only and carries a "coming soon" badge. |

## 🔄 Update Job

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `scheduler_enabled` | bool | `true` | Enable or disable the automatic background synchronization daemon for exchange rates and historical/real-time prices. |

The remaining scheduler parameters are not shown as individual fields: they are edited together from the **Configure** modal of the Scheduler row — see [Market Data Scheduler](#market-data-scheduler) below.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `scheduler_current_price_frequency_minutes` | int | `10` | Frequency (in minutes) with which the daemon updates current real-time prices (1-1440). |
| `scheduler_history_sync_times` | str | `06:00,23:00` | Comma-separated HH:MM times for daily history sync, expressed **in the configured `scheduler_timezone`**. Times are stored as entered (local wall-clock); the daemon converts each local slot to a UTC instant only when deciding whether a job is due. |
| `scheduler_history_sync_days` | str | `mon,tue,wed,thu,fri,sat` | Specific days of the week (comma-separated) to run the historical synchronization. |
| `scheduler_history_sync_horizon_days` | int | `14` | Rolling retrospective analysis window (in days) used to check for missing historical prices. |
| `scheduler_timezone` | str | `UTC` | IANA timezone used to **store and evaluate** the scheduler history-sync days and times. The times/days you configure are local to this zone; invalid values fall back to UTC. |

## 🧠 Memory

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `max_file_upload_mb` | int | `10` | Maximum file upload size in megabytes. Applies to all uploads (static resources and broker reports). |

The Memory category also hosts the **Server Caches** panel — see [Server Caches](#server-caches) below.

## 🌍 Defaults

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `default_currency` | str | `EUR` | Default display currency for newly registered users. Users can override this in their personal settings. |
| `default_language` | str | `en` | Default language for newly registered users. Supported: 🇬🇧 `en`, 🇮🇹 `it`, 🇫🇷 `fr`, 🇪🇸 `es`. |
| `default_theme` | str | `auto` | Default theme for newly registered users: ☀️ `light`, 🌙 `dark`, 🖥️ `auto`. |

---

## 🕐 Market Data Scheduler {: #market-data-scheduler }

When the background scheduler is enabled, administrators can configure synchronization parameters and inspect background execution logs directly from the user interface.

### ⚙️ Configure Scheduler

Click the **Configure** button in the Scheduler row to customize execution frequencies and parameters:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Scheduler Configuration Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

* **Current Price Frequency**: The frequency (in minutes) at which the daemon fetches real-time quotes to keep the dashboard cache updated (default: 10m).
* **History Sync Times**: Specific daily times (comma-separated, e.g., `06:00,23:00`) to run historical daily close updates. Times are wall-clock times **in the configured scheduler timezone**.
* **History Sync Days**: Specific days of the week when historical synchronization is performed (usually Monday to Saturday), also evaluated in the scheduler timezone.
* **History Horizon**: The analysis window (in days) to check for missing historical price points (default: 14 days).
* **Timezone**: The IANA timezone (`scheduler_timezone`) in which the times and days above are stored and evaluated. The modal shows the server's UTC clock alongside, so you can reason about the offset; the backend converts each local slot to a UTC instant only when deciding whether a job is due. Invalid values fall back to UTC.

### 📜 Scheduler Logs

Click **View Logs** to open the log inspector. This modal displays a list of recent scheduler executions:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Scheduler Log Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

The log reports the execution timestamp, job name, status (Success/Error), execution duration, and structured details of processed assets, price feeds, and any error traces.

---

## 🗄️ Server Caches {: #server-caches }

LibreFolio keeps several **in-memory caches** on the backend (price fetches, search results, portfolio computations, provider responses, and more) so that repeated requests do not hit the external data providers every time. The **Global Settings** tab ends with a **Cache panel** (Memory category) that lists every registered cache by name, with its **current size / maximum size** and **TTL** (time-to-live) columns — each column header is clickable to sort by name, size, or TTL; a **Refresh** button re-reads the live stats.


<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="cache-panel" alt="Server caches panel in Global Settings (Memory category)">
</div>


**Who can do what:**

- 👁️ **Reading the status** is available to **any authenticated user** (`GET /api/v1/settings/cache/status`).
- 🧹 **Clearing** is **admin-only and requires the page to be unlocked** (the buttons appear only for superusers in edit mode): each row has its own **Clear** button (`POST /api/v1/settings/cache/clear/{name}`), and the panel header has a **Clear all** button (`POST /api/v1/settings/cache/clear-all`).

!!! warning "Clearing a cache slows down the next fetch"

    Both clear actions ask for confirmation, for a good reason: after a clear, the next request for that data **hits the external providers again**, so expect a slowdown comparable to a server restart while the caches refill. Caches also empty themselves on every server restart — clearing is only useful to force fresh data without restarting.

---

## 🔧 Technical Notes

- 🗃️ Settings are stored as **key-value pairs** in the `global_settings` table
- 🔀 Values are stored as strings and converted to the appropriate type (`int`, `bool`, `str`) when read
- 🔒 On multi-worker startup, settings are initialized with `INSERT ... ON CONFLICT DO NOTHING` to avoid race conditions
- ⚡ Changes take effect **immediately** — no server restart required
