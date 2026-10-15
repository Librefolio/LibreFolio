# ⚙️ Settings Components

This section documents the components used for the Settings pages (User Preferences, Global Settings, Profile).

<div class="lf-screenshot-carousel" data-carousel="settings-main" data-carousel-interval="3000" data-show-titles="true">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="settings" data-name="user-preferences" data-title="User Preferences">
    <img class="gallery-img lf-screenshot-carousel-item" data-category="settings" data-name="global-settings" data-title="Global Settings (Admin)">
</div>

## 🏗️ Architecture

The settings system uses a modular architecture based on a common layout and reusable field components.

### 🗂️ Tab registry {: #tab-registry }

The tabs of the Settings page are a registry: `SETTINGS_TABS` in
`lib/features/settings/settingsTabs.ts`. `routes/(app)/settings/+page.svelte` names no tab itself:
it draws the bar and the active body from that list. Each entry is a `SettingsTab`:

| Field | Role |
|---|---|
| `id` | The `?tab=` value that opens the tab, and the suffix of its `settings-tab-{id}` test id |
| `labelKey` | Catalogue key of the label, drawn as `$_(labelKey)` on the tab and in the heading shown on a phone |
| `icon` | Lucide icon of the tab button |
| `order` | Position in the bar, left to right |
| `component` | The tab body |
| `visible?(ctx)` | Who sees the tab; when absent, everyone does |
| `props?(ctx)` | Props spread on the body |
| `alignEnd?` | On a wide screen, starts the right-hand group: this tab and every tab after it sit on the right (`sm:ml-auto` on its button) |

`ctx` is a `SettingsTabContext`, `{isSuperuser}`, which the page derives from the auth store
(`$auth.user?.is_superuser ?? false`). The registry holds four tabs:

| `id` | `order` | Body | Visible to | Extras |
|---|---|---|---|---|
| `profile` | 10 | `ProfileTab` | everyone | — |
| `preferences` | 20 | `PreferencesTab` | everyone | — |
| `about` | 30 | `AboutTab` | everyone | — |
| `admin` | 100 | `GlobalSettingsTab` | everyone | `props: (ctx) => ({canEdit: ctx.isSuperuser})`, `alignEnd: true` |

The page is the runtime of the registry, written in Svelte 5 runes:

- **Bar**: `visibleSettingsTabs(SETTINGS_TABS, ctx)`, the tabs whose `visible(ctx)` is not false,
  sorted by `order` into a new array (the registry itself is never reordered), handed to `TabBar`
  with the labels hidden on a phone (`hideLabelOnMobile`).
- **Body**: the active tab's `component` alone, with `props(ctx)` spread on it. The spread is live:
  when the auth store changes, the body on screen receives the new props.
- **Active tab**: the first visible tab, unless `?tab=<id>` names a visible one. The choice runs in
  `$effect.pre`, so the tab that `?tab=` names is the first body mounted: the default body never
  mounts, not even for an instant. Clicking a tab does not rewrite the URL, so a `?tab=` value is
  applied once: a later page update that keeps it does not take back the tab the user picked, while
  a new value is applied again. An unknown id, or the id of a tab this user cannot see, is ignored;
  a `?tab=` naming a tab that becomes visible later (the user is promoted while on the page) is
  applied when the tab appears. If the active tab stops being visible, the first visible tab opens.

**Adding a tab** takes one entry in `SETTINGS_TABS`, plus the import of its body. For example, a
tab only administrators see (`UsersTab` and `settings.users` stand for your own body and key):

```ts
import {Info, Shield, Sliders, User, Users} from 'lucide-svelte';
import UsersTab from '$lib/features/settings/tabs/UsersTab.svelte';

export const SETTINGS_TABS: readonly SettingsTab[] = [
    // profile (10), preferences (20), about (30)
    {id: 'users', labelKey: 'settings.users', icon: Users, order: 40, component: UsersTab, visible: (ctx) => ctx.isSuperuser},
    // admin (100, alignEnd)
];
```

- **`order`**: a free number between the neighbours. The orders leave gaps, so no other tab is
  renumbered; here 40 puts the tab after About, in the left-hand group. Every `order` is unique.
- **`visible`**: `(ctx) => ctx.isSuperuser` keeps the tab out of a regular user's bar altogether,
  and a `?tab=` naming it is ignored for them. Leave `visible` out for a tab everyone sees.
- **`props`**: only when the body depends on the context, as `admin` does for `canEdit`.
- **`alignEnd`**: one tab carries it, today `admin`. A tab with a higher `order` (above 100) joins
  the right-hand group, after Admin.
- **`id` and `labelKey`**: the `id` is unique, made of lowercase letters, digits and dashes, and
  starts with a letter; the `labelKey` is a sentence in all four catalogues.
- **Tests**: `lib/features/settings/settingsTabs.test.ts` pins the content of the registry through
  its `TODAY` table, so the new tab adds its row there in the same change (with a `vi.mock` of its
  body module, like today's four), and the cases that list today's tabs by name follow it; the same
  file checks the ids, the orders and the labels in the four catalogues.
  `routes/(app)/settings/page.tabs.test.ts` tests the page on a registry of its own and does not
  change.

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

Manages user-specific settings (Language, Currency, Theme) and hosts the **Onboarding** category
described below. Its categories are `display` (Language), `currency` (Default Currency),
`appearance` (Theme) and `onboarding`, plus *All Settings* when none is selected.

**Logic** (`lib/features/settings/tabs/PreferencesTab.svelte`):

1. **Load**: Fetches Global Defaults (`/settings/global`) and User Settings (`/settings/user`) in parallel.
2. **State Tracking**:
    - `originalValues`: The values currently saved in the DB.
    - `editedValues`: The values currently in the form inputs.
    - `globalDefaults`: The system-wide default values — `FALLBACK_DEFAULTS` (`en`, `EUR`, `auto`)
      when `/settings/global` cannot be loaded.
3. **Computed States**:
    - `isModified`: `editedValues !== originalValues` (Shows Save/Undo).
    - `isNonDefault`: `originalValues !== globalDefaults` (Shows Reset, but only while the field
      has no pending edit: `SettingActions.svelte`).
4. **Persistence**: Saves to `/settings/user` via `PUT`, one field per request. **Save** sends that
    field; **Save All** sends the modified fields one after the other, then reports what was saved
    and what failed in a single toast (success, partial or error). Language and theme take effect
    only once their write succeeds (`currentLanguage.set()`, `applyTheme()`), and
    `userSettings.setDirect()` then writes the saved language, currency and theme into the store.
    **Reset** only copies the global default into `editedValues`: it still has to be saved.

The Default Currency (`base_currency`) is proposed when something new is created: `BrokerForm.svelte`
uses it for the first initial balance, `AssetModal.svelte` for a new asset's currency and
`PacPlannerTool.svelte` for a new plan's valuation currency. The Dashboard, the Brokers list and
detail pages, and the risk panel of the Assets page start their display currency from the global
`default_currency` (`$globalSettings`) instead.

### 🧭 OnboardingReplaySection

`OnboardingReplaySection.svelte` (in `frontend/src/lib/features/onboarding/components/`) is the
**Onboarding** category of `PreferencesTab`
(`{id: 'onboarding', icon: Compass, labelKey: 'onboarding.settings.category'}`). The tab renders
it when that category is selected and in the *All Settings* view (no category selected). It lists
every onboarding flow with its progress and lets the user replay any of them without changing that
recorded progress. This section covers the Settings UI only; the mechanics behind it — when a guide
is due, what a replay does once it runs, where its position is kept — are explained in
[Onboarding Guides](../../onboarding.md).

**What it lists.** The section reads `onboarding.progress?.flows`, the per-user progress that the
app bootstrap loads from `GET /api/v1/settings/onboarding`: one `OnboardingProgressItem` for each
of the **15** flows of `ONBOARDING_FLOW_VERSIONS` (`backend/app/services/accounts/onboarding_service.py`;
enum `OnboardingFlow` in `backend/app/db/models.py`). The section sorts them into collapsible
groups; *Setup* and *Core tour* start open:

| Group (`onboarding.settings.groups.*`) | Flows |
|---|---|
| `setup` | `welcome` |
| `core` | `intro_tour` |
| `transactions` | `transactions_page_guide`, `transaction_create_guide`, `transaction_bulk_guide`, `import_guide` |
| `broker` | `broker_page_guide`, `broker_guide`, `broker_detail_guide` |
| `fx` | `fx_page_guide`, `fx_guide`, `fx_detail_guide` |
| `asset` | `asset_page_guide`, `asset_guide`, `asset_detail_guide` |

A group header counts its flows that are completed at the current version
(*{completed}/{total} guides completed*). Each row shows the flow name (`onboarding.flows.<flow>`),
its status (*Pending*, *Completed* or *Skipped*) and the *Seen v{seen} · current v{current}*
label. Statuses are display-only: nothing in the section calls a complete or skip endpoint.

**New version.** When the version the user went through is older than the current one
(`update_available`), the row adds the **New version to view** badge and its group no longer
counts it as completed. Such a guide is due again and starts by itself at its next trigger.

**Step-managed flows.** The rows of `transaction_bulk_guide` (4 steps) and `import_guide`
(9 steps) add a collapsible list of their steps, each with its status, under a
*{completed}/{total}* counter in which a skipped step counts as done and a step with a newer
version does not. The row's own status summarizes its steps.

**Replay per flow.** The row button depends on the flow:

- `welcome` → **Replay** arms a Welcome replay (`onboarding.startReplay`) and opens `/welcome`.
  There, **Continue** saves the chosen language, currency and avatar through the regular
  `PUT /api/v1/settings/user` without touching the Welcome status, and **Exit tour** saves
  nothing.
- `intro_tour` → **Replay** starts the tour at once, in replay mode, from its opening scene
  (`onboardingGuide.startIntroReplay()`), and opens `/dashboard`.
- every other flow → **Replay at next trigger** only arms the replay
  (`onboardingGuide.armReplay(flow)`; for Import and Bulk, with all their steps), and a toast says
  the guide is ready in this browser. The guide starts the next time its page, modal or wizard
  asks for it. While armed, the row reads *Ready in this browser: {flow} starts at its next
  trigger.* and the button becomes **Cancel activation** (`onboarding.clearReplay`).

**Replay all** arms every flow in list order — Welcome with `onboarding.startReplay`, the intro
with `onboardingGuide.prepareIntroReplay()`, all the others with `armReplay` — then opens
`/welcome`. If one of them cannot be armed (for example when `localStorage` is unavailable), the
section clears the replays it already armed, then shows the error. Every button is disabled while
an action runs. When the progress could not be loaded at all, the list is replaced by the error
and a **Retry** button (`appBootstrap.load(true)`).

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
- Registration mode: a select with three options, `open`, `invite` and `disabled`
  (`settings.registrationModes.*`: **Open**, **By invitation**, **Closed**)
- Scheduler configuration and new-user defaults
- Other app-wide settings

The Settings page shows this tab to every user, but only a superuser can change it: its entry in
the [tab registry](#tab-registry) has no `visible` and passes `canEdit` through
`props: (ctx) => ({canEdit: ctx.isSuperuser})`, and without `canEdit` the tab shows a read-only
indicator instead of the lock toggle and the bulk Save/Undo/Reset actions.

For the three *display* defaults (`default_language`, `default_currency`, `default_theme`) the
tab reuses the **same shared `Setting*` wrappers as the PreferencesTab**, passing the
`embedded` prop (see below) so they sit inside the tab's own cards without double separators.

**Registration mode.** `registration_mode`, in the *Security* category, is a `SettingSelect`
(default `open`, `SETTING_DEFAULTS`). The server variable `LIBREFOLIO_REGISTRATION` can pin it
([Registration Modes](../../../architecture/access_control.md#registration-modes)); the tab learns
it from the [instance configuration](../../state/app-state.md#instance-config),
`instanceConfig.config.accounts.registration_locked`:

- **Locked by the variable**: the select shows the mode in force,
  `instanceConfig.config.accounts.registration_mode`, not the stored row; it is disabled even with
  the tab unlocked; its hint becomes `settings.lockedByEnv` with `{variable: LIBREFOLIO_REGISTRATION}`
  (*Set on the server by LIBREFOLIO_REGISTRATION: change it there.*); and **Reset All to Defaults**
  skips it. Its card, `global-setting-registration_mode`, carries `data-locked="true"`
  (`"false"` otherwise).
- **A save that meets the lock anyway** — for example before the configuration arrived — gets
  `409` `SETTING_LOCKED_BY_ENV`; the tab shows `settings.lockedByEnv` with the `variable` of the
  answer.
- **After a save that includes `registration_mode`**, alone or with **Save All**, the tab calls
  `instanceConfig.load({force: true})`, so the login page's **Register here** and the `/invite` page
  follow the new mode on this page load.

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

Both components take callback props (`onsaveAll`, `onundoAll`, `onresetAll` on the layout;
`onsave`, `onundo`, `onreset` on a field), not component events:

```svelte
<script lang="ts">
  import SettingsLayout from '$lib/features/settings/SettingsLayout.svelte';
  import SettingSelect from '$lib/features/settings/SettingSelect.svelte';

  let original = $state('option1');
  let value = $state('option1');
  let hasChanges = $derived(value !== original);

  function save() {
    // persist `value`, then:
    original = value;
  }
</script>

<SettingsLayout title="My Settings" {hasChanges} onsaveAll={save} onundoAll={() => (value = original)}>
  <SettingSelect
    bind:value
    label="Choose Option"
    options={[{value: 'option1', label: 'One'}]}
    isModified={hasChanges}
    onsave={save}
    onundo={() => (value = original)}
  />
</SettingsLayout>
```
