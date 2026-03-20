# ⚙️ Settings Components

This section documents the components used for the Settings pages (User Preferences, Global Settings, Profile).

<div style="display: flex; gap: 1rem; flex-wrap: wrap; margin: 1rem 0 2rem 0;">
    <div class="screenshot-container" style="flex: 1; min-width: 280px; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
        <img class="gallery-img" data-category="settings" data-name="user-preferences" alt="User Preferences" style="width: 100%; display: block;">
    </div>
    <div class="screenshot-container" style="flex: 1; min-width: 280px; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
        <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Global Settings (Admin)" style="width: 100%; display: block;">
    </div>
</div>

## Architecture

The settings system uses a modular architecture based on a common layout and reusable field components.

### SettingsLayout

The `SettingsLayout` component provides the structural shell for all settings tabs.

**Features:**

- **Two-Column Layout**: Sidebar navigation on the left, content on the right.
- **Global Actions**: "Save All", "Undo All", "Reset All" buttons in the header.
- **Lock Toggle**: Optional lock button for admin settings (prevents accidental edits).
- **Responsive**: Stacks vertically on mobile.

**Props:**

- `categories`: Array of `{ id, icon, labelKey }` for the sidebar.
- `selectedCategory`: ID of the currently active category filter.
- `hasChanges`: Boolean to show Save/Undo buttons.
- `hasNonDefaults`: Boolean to show Reset button.
- `isLocked`: Boolean state of the edit lock.

### PreferencesTab

Manages user-specific settings (Language, Currency, Theme).

### ProfileTab

Manages user profile information:

- **Avatar**: Editable via `ImagePickerWrapper` → `AssetPickerModal` → crop
- **Username** and **Email**: Display only
- **Password change**: Opens `PasswordChangeModal`
- Edit mode toggle to prevent accidental changes

### GlobalSettingsTab (Admin only)

System-wide configuration with lock toggle:

- Max file upload size
- Registration toggle
- Other app-wide settings

### AboutTab

Read-only system information:

- Version (from Git tag)
- Backend/frontend info

**Logic:**

1. **Load**: Fetches Global Defaults (`/settings/global`) and User Settings (`/settings/user`) in parallel.
2. **State Tracking**:
    - `originalValues`: The values currently saved in the DB.
    - `editedValues`: The values currently in the form inputs.
    - `globalDefaults`: The system-wide default values.
3. **Computed States**:
    - `isModified`: `editedValues !== originalValues` (Shows Save/Undo).
    - `isNonDefault`: `originalValues !== globalDefaults` (Shows Reset).
4. **Persistence**: Saves to `/settings/user` via `PUT`.

### Field Components

Each setting type has a specialized component that handles its own UI and events.

- **`SettingSelect`**: Generic dropdown (uses `SimpleSelect`).
- **`SettingCurrency`**: Searchable currency selector (uses `SearchSelect`).
- **`SettingTheme`**: Radio buttons for Light/Dark/Auto theme with visual preview.
- **`SettingNumber`**: Numeric input with increment/decrement.
- **`SettingToggle`**: Boolean toggle switch.

**Common Props for Field Components:**

- `value`: Two-way bound value.
- `label`: Field label.
- `hint`: Helper text.
- `isModified`: Highlights the field if changed.
- `isNonDefault`: Shows a "Reset to Default" indicator.
- `isLocked`: Disables input.

## Usage Example

```svelte
<script>
  import SettingsLayout from '$lib/components/settings/SettingsLayout.svelte';
  import SettingSelect from '$lib/components/settings/SettingSelect.svelte';
  
  let value = 'option1';
  let original = 'option1';
  
  $: hasChanges = value !== original;
</script>

<SettingsLayout
  title="My Settings"
  {hasChanges}
  on:saveAll={save}
>
  <SettingSelect
    bind:value
    label="Choose Option"
    options={[{code: 'option1', label: 'One'}]}
    isModified={value !== original}
    on:save={() => saveSingle(value)}
  />
</SettingsLayout>
```

