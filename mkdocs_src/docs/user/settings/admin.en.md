# 🛡️ Global Settings

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Global Settings (Admin)">
</div>

!!! warning "Admin access required"

    The **Global Settings** tab is only visible to users with the **ADMIN** role.

Global settings affect all users on the instance:

| Setting | Description |
|---------|-------------|
| **Registration** | Enable or disable new user self-registration |
| **Default Language** | Fallback language for new users |
| **Default Currency** | Default base currency for new accounts |
| **Session Timeout** | Inactivity timeout in minutes |
| **Scheduler** | Enable or disable the automatic background market data sync daemon |

---

## 🕐 Market Data Scheduler

When the background scheduler is enabled, administrators can configure synchronization parameters and inspect background execution logs directly from the UI.

### ⚙️ Configure Scheduler

Click the **Configure** button on the Scheduler row to customize execution frequencies and parameters:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Scheduler Config Modal">
</div>

* **Current Price Frequency**: The frequency (in minutes) at which the daemon fetches live quotes to keep the dashboard cache warm (default: 10m).
* **History Sync Times**: Specific times of day (comma-separated, e.g., `06:00,23:00`) to run historical daily close updates.
* **History Sync Days**: Specific days of the week on which historical syncing runs (usually Monday to Saturday).
* **History Horizon**: The lookback window (in days) to check for missing historical price points (default: 14 days).

### 📜 Scheduler Logs

Click **View Logs** to open the log inspector. This modal displays a list of recent scheduler executions:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Scheduler Log Modal">
</div>

It reports the execution timestamp, job name, status (Success/Error), run duration, and structured details of processed assets, price feeds, and any error traces.

---

## 🔗 Related

- ⚙️ **[Settings Overview](index.md)** — General settings summary
- 👤 **[User Preferences](preferences.md)** — Profile and display preferences
- ℹ️ **[About](about.md)** — Version info and license
