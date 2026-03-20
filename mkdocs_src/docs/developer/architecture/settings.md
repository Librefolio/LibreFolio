# ⚙️ Settings System

LibreFolio uses a two-tiered settings system to manage configuration: **Global Settings** and **User Settings**.

## Global Settings

Global settings are system-wide configurations that apply to all users. They are managed by administrators and are read-only for regular users.

### Purpose

- To control core application behavior.
- To configure default values for the entire system.

### Implementation

- Global settings are stored in the `global_settings` table in the database.
- They are managed via the `user_cli.py` script.
- The `settings_service.py` provides functions to read these settings.

### Example Global Settings

- Default currency for the application.
- Enabled/disabled status of external data providers.

### Managing Global Settings

Global settings are initialized with default values using the CLI:

```bash
./dev.py user init-settings
```

Future versions will allow administrators to modify these settings through an admin UI.

## User Settings

User settings are preferences specific to each individual user. Each user can modify their own settings.

### Purpose

- To allow users to customize their experience.
- To store user-specific preferences that override global defaults.

### Implementation

- User settings are stored in the `user_settings` table, linked to a `user_id`.
- They are managed via the API (`/api/v1/settings`).
- The `settings_service.py` provides functions to get and set user-specific settings, with a fallback to the global setting if a user-specific one is not defined.

### Example User Settings

- The user's preferred display currency for their portfolio.
- Theme preference (light/dark mode).
- Dashboard layout preferences.

## The Settings Service (`settings_service.py`)

This service acts as the central point for all settings-related operations. It abstracts the two-tiered system, providing a simple interface for the rest of the application.

When a setting is requested for a user, the service first checks if a `UserSetting` exists for that user. If not, it falls back to the corresponding `GlobalSetting`. This provides
a clean and flexible way to handle default values and user overrides.
