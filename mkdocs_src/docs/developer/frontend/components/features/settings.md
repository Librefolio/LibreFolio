# ⚙️ Settings Components

This section documents the components used for the Settings pages (User Preferences, Global Settings, Profile).

<div class="lf-screenshot-carousel" data-carousel="settings-main" data-carousel-interval="3000" data-show-titles="true">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="settings" data-name="user-preferences" data-title="User Preferences">
    <img class="gallery-img lf-screenshot-carousel-item" data-category="settings" data-name="global-settings" data-title="Global Settings (Admin)">
</div>

## 🏗️ Architecture

The settings system uses a modular architecture based on a common layout and reusable field components.

### 📐 SettingsLayout

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

### 🎨 PreferencesTab

<div class="screenshot-container" style="margin: 1rem 0 2rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 600px;">
    <img class="gallery-img" data-category="settings" data-name="user-preferences" alt="User Preferences" style="width: 100%; display: block;">
</div>

Manages user-specific settings (Language, Currency, Theme).

### 🧭 OnboardingReplaySection

`OnboardingReplaySection.svelte` renders the **Onboarding** category inside `PreferencesTab`
(`{id: 'onboarding', icon: Compass, labelKey: 'onboarding.settings.category'}`). It reads
`onboarding.progress?.flows` — the three `OnboardingProgressItem`s (`welcome`, `intro_tour`,
`import_guide`) fetched from `GET /api/v1/settings/onboarding` — and renders, per flow: its
`status`, a `Seen v{version} · current v{current_version}` label, an **update available** badge
when `update_available` is true, and a **Replay** button.

Replaying branches on the flow, because only `welcome` and `intro_tour` can start immediately:

- `welcome` → `onboarding.startReplay('welcome', ..., 'welcome')` then `goto('/welcome')`.
- `intro_tour` → `onboardingGuide.startIntroReplay()`, which starts at `intro.scene`. That scene
  presents three phrases and advances from manual **Start** or one automatic start after 10
  seconds; the remaining semantic steps drive their own `goto` calls from
  `OnboardingOverlayHost`.
- `import_guide` → `onboardingGuide.startImportReplay()` only **arms** the replay
  at `import.upload` (`onboarding.startReplay('import_guide', ...)`); nothing observes it until
  the user opens the Import Wizard, whose own `$effect` sees `progress.status !== 'pending'` but
  `controller.hasReplay(...)` true and starts in `'replay'` mode. The button label and the
  `replayIsArmed(item)` badge (`nextImport` vs. `replayReady`) reflect this: `import_guide` uses
  *"Replay on next import"* for its button and, once armed, *"Ready for next import"* for its
  badge, rather than the other flows' *"Replay"* / *"Replay ready"* labels.
- **Replay all** uses the flow-specific entry points:
  `onboarding.startReplay(...)` for Welcome, `onboardingGuide.prepareIntroReplay()` for the intro,
  and `onboardingGuide.startImportReplay()` for import; it then navigates to `/welcome` once.
  Completing Welcome applies the selected locale before `maybeStartIntro()` renders the narrative
  scene. In a Welcome replay, that completion uses the existing user-settings PUT for the
  explicitly selected language/currency/avatar while preserving the Welcome progress status;
  **Exit replay** saves nothing. If any replay arm fails (e.g. `sessionStorage` unavailable), the
  section unwinds the flows it already armed via `onboarding.clearReplay` before surfacing the
  error.

An automatic pending intro/import coachmark shows **Skip permanently** plus **X**; replay mode
shows **Exit replay** plus **X**. The intro footer uses **Back**, **Next**, and **Finish** on the
final Settings stop. Automatic **Finish**/**Skip permanently** perform the corresponding backend
transition, while replay **Finish**/**Exit replay** only clear session replay state and never
call complete/skip. **X** suspends without ending the replay: it retains the intro cursor, while
the import guide resets the next entry to `import.upload`. There is no Pause action. Replaying
does not restore wizard draft state or automate wizard clicks, uploads, or **Save All**.

Replay state lives in `sessionStorage`, not on the server — see
**[Onboarding: the contextual import guide](import-wizard.md#import-guide-wiring)**
for the storage key format. A replay of a terminal (`completed`/`skipped`) flow is strictly
non-destructive to that status from start through exit.

### 👤 ProfileTab

Manages user profile information:

- **Avatar**: Editable via `ImagePickerWrapper` → `AssetPickerModal` → crop
- **Username** and **Email**: Display only
- **Password change**: Opens `PasswordChangeModal`
- Edit mode toggle to prevent accidental changes

### 🌍 GlobalSettingsTab (Admin only)

<div class="screenshot-container" style="margin: 1rem 0 2rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 600px;">
    <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Global Settings" style="width: 100%; display: block;">
</div>

System-wide configuration with lock toggle:

- Max file upload size
- Registration toggle
- Scheduler configuration and new-user defaults
- Other app-wide settings

For the three *display* defaults (`default_language`, `default_currency`, `default_theme`) the
tab reuses the **same shared `Setting*` wrappers as the PreferencesTab**, passing the
`embedded` prop (see below) so they sit inside the tab's own cards without double separators.

### 🧹 CachePanel

`CachePanel.svelte` shows the status of every named backend cache (the theine registry): name,
`current_size / maxsize`, and a human-formatted TTL, refreshed on demand. Status is visible to
any authenticated user; the per-cache **Clear** and **Clear all** buttons appear only when the
`canEdit` prop is set (it mirrors the Global-settings lock). Both clear actions pass through a
danger confirmation modal — after a clear, the next fetch hits the providers again. Backend
contract: [Cache Registry & Admin](../../../architecture/settings_cache.md).

### ℹ️ AboutTab

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

### 🔧 Field Components

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

The three wrappers shared with the Global Settings tab — `SettingSelect`, `SettingCurrency`,
`SettingTheme` — also accept **`embedded`**: when `true`, the row drops its own padding and
bottom border so it can sit inside a parent card without a double separator. The standalone
Preferences tab renders rows in a list and keeps the default; the Global Settings tab embeds
the shared wrappers in its own per-setting cards and passes `embedded`.

## 💻 Usage Example

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
