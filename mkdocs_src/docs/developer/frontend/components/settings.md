# Settings Components

*Status: Draft - Components implemented, documentation in progress*

## Overview

Settings components for user preferences and global application settings.

## Components

### SettingsLayout

Two-column layout for settings pages:

- Left sidebar with category navigation
- Right content area
- Responsive (stacks on mobile)

### PreferencesTab

User-specific preferences:

- Language selection
- Currency preference
- Theme (light/dark/system)
- Date format
- Number format
- Reset to defaults button

### GlobalSettingsTab

Admin-only global settings:

- Default language for new users
- Default currency
- Registration enabled/disabled
- Maintenance mode
- Grouped by category

### ProfileTab

User profile management:

- Username (with edit lock)
- Email (with edit lock)
- Password change (via modal)
- Delete account (with confirmation)

## Files

```
frontend/src/lib/components/settings/
├── SettingsLayout.svelte
├── PreferencesTab.svelte
├── GlobalSettingsTab.svelte
└── ProfileTab.svelte
```

## Settings Page Structure

```
/settings
├── Profile (ProfileTab)
├── Preferences (PreferencesTab)
└── Global Settings (GlobalSettingsTab) - Admin only
```

## Key Features

- **Edit Lock**: Prevents accidental changes to sensitive fields
- **Inline Save**: Each field saves independently
- **Undo**: Revert unsaved changes
- **Reset**: Restore defaults from global settings
- **Validation**: Client-side validation before save

## API Integration

*(To be documented)*

- `PATCH /api/v1/auth/users/me/preferences`
- `PATCH /api/v1/system/settings/{key}`
