# ⚙️ Settings Components

This section documents the components used for the Settings pages (User Preferences, Global Settings, Profile, Users, Security).

<div class="lf-screenshot-carousel" data-carousel="settings-main" data-carousel-interval="3000" data-show-titles="true">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="settings" data-name="user-preferences" data-title="User Preferences">
    <img class="gallery-img lf-screenshot-carousel-item" data-category="settings" data-name="global-settings" data-title="Global Settings (Admin)">
</div>

## 🏗️ Architecture

The settings system uses a modular architecture based on a common layout and reusable field components.

### 🗂️ Tab registry {: #tab-registry }

The tabs of the Settings page are a registry: `SETTINGS_TABS` in
`lib/features/settings/settingsTabs.ts`. `routes/(app)/settings/+page.svelte` names no tab itself:
it draws its two bars and the active body from that list. Each entry is a `SettingsTab`:

| Field | Role |
|---|---|
| `id` | The `?tab=` value that opens the tab, and the suffix of its `settings-tab-{id}` test id |
| `labelKey` | Catalogue key of the label, drawn as `$_(labelKey)` on the tab and in the heading shown on a phone |
| `icon` | Lucide icon of the tab button |
| `order` | Position in the bar, left to right; for a member of a group, in the group's second bar |
| `component` | The tab body |
| `visible?(ctx)` | Who sees the tab; when absent, everyone does |
| `props?(ctx)` | Props spread on the body |
| `group?` | The `id` of the [group](#tab-groups) of `SETTINGS_TAB_GROUPS` the tab belongs to: the top bar shows the group as one entry, and a second bar lists its members |
| `badge?(ctx)` | The number its button shows, none for `0`; a group's entry shows the sum of its visible members' |
| `prefetch?(ctx)` | What the page starts loading before the tab is opened, so that `badge` can count: run when the page opens, and again when the context changes, for every visible tab that has one |
| `alignEnd?` | On a wide screen, starts the right-hand side: this entry and every entry after it sit on the right (`sm:ml-auto` on its button). One tab or one group carries it: today the `administration` group, and no tab |

`ctx` is a `SettingsTabContext`, `{isSuperuser}`, which the page derives from the auth store
(`$auth.user?.is_superuser ?? false`). The registry holds nine tabs:

| `id` | `order` | Body | Visible to | `group` | Extras |
|---|---|---|---|---|---|
| `profile` | 10 | `ProfileTab` | everyone | — | — |
| `preferences` | 20 | `PreferencesTab` | everyone | — | — |
| `plugins` | 25 | `PluginSettingsTab` | everyone | — | — |
| `about` | 30 | `AboutTab` | everyone | — | — |
| `admin` | 100 | `GlobalSettingsTab` | administrators | `administration` | Label `settings.globalSettings` (*Global Settings*), icon `Settings2`; `visible: (ctx) => ctx.isSuperuser` (lot N69-2, decision D4 a); `props: (ctx) => ({canEdit: ctx.isSuperuser})`, kept: see [GlobalSettingsTab](#globalsettingstab-admin-only) |
| `users` | 110 | [`UsersTab`](#userstab) | administrators | `administration` | `visible: (ctx) => ctx.isSuperuser` |
| `backup` | 120 | `BackupTab` | administrators | `administration` | `visible: (ctx) => ctx.isSuperuser` |
| `email` | 130 | `EmailSettingsTab` | administrators | `administration` | `visible: (ctx) => ctx.isSuperuser` |
| `security` | 140 | [`SecurityTab`](#securitytab) | administrators | `administration` | `visible: (ctx) => ctx.isSuperuser`; `badge: () => securityChecks.attentionCount`; `prefetch: (ctx) => { if (ctx.isSuperuser) void securityChecks.ensureLoaded(); }` |

The `admin` id stays as it was, so `?tab=admin`, the link of the
[open-registration warning](auth.md#open-registration-notice), still opens the global settings (the
warning shows to administrators only, as the tab does; for a regular user, `?tab=admin` names a
hidden tab and opens `profile`, the first visible one);
lot A8b changed only its label and its icon, the group having taken the `Shield`, and removed the
key `settings.admin` (*Admin*) from the catalogues. Five bodies are in `lib/features/settings/tabs/`,
the Security tab's in `lib/features/settings/security/` ([SecurityTab](#securitytab)). The Plugins
tab's body, `lib/features/plugin-settings/PluginSettingsTab.svelte` (label `pluginSettings.tab.label`),
the Backup tab's, `lib/features/backup/BackupTab.svelte` (label `backup.tab`), and the Email tab's,
`lib/features/email/EmailSettingsTab.svelte` (label `email.tab.label`), live with their features:
for the Plugins tab see [Plugin Settings › The Interface](../../../architecture/patterns/plugin_settings.md#interface),
for the Email tab [The Email Tab](../../../backend/email.md#email-tab). The Plugins tab takes no
props: every user sees it, and the catalogue the API returns already says which fields this user may
change.

#### Groups {: #tab-groups }

`SETTINGS_TAB_GROUPS`, in the same module, holds the groups of the top bar (decision P13 b), each a
`SettingsTabGroup`, `{id, labelKey, icon, alignEnd?}`. There is one today, `administration`: label
`settings.administration` (*Administration*), icon `Shield`, `alignEnd: true`. Its members are
`admin`, `users`, `backup`, `email` and `security`; `profile`, `preferences`, `plugins` and `about`
belong to no group. A group's `id` is a `?tab=` value and a test-id suffix too
(`settings-tab-administration`): it is URL-safe, and no tab's `id`.

`settingsBar(tabs, groups, ctx)` gives the entries of the top bar, `SettingsBarEntry[]`, as a new
array, and leaves the lists it is given as they were: the tabs of `visibleSettingsTabs(tabs, ctx)`,
by `order`, each a `{kind: 'tab', tab}` entry, except the visible members of a group, gathered into
one `{kind: 'group', group, members}` entry placed where its first visible member would be,
`members` being its visible members by `order`. A group without a visible member has no entry, and a
tab whose `group` names none of `groups` stays a tab entry. A regular user's bar is `profile`,
`preferences`, `plugins` and `about`: every member of `administration` is an administrator's (since
lot N69-2), so the group has no entry for them; an administrator's ends with `administration` and
its five members.

#### The page {: #settings-page }

The page is the runtime of the registry, written in Svelte 5 runes:

- **Top bar**: `settingsBar(SETTINGS_TABS, SETTINGS_TAB_GROUPS, ctx)`, handed to `TabBar` with the
  labels hidden on a phone (`hideLabelOnMobile`). A tab entry is drawn as its tab
  (`settings-tab-{id}`, its icon, `$_(labelKey)`); a group entry with the group's icon and label,
  and the test id `settings-tab-{groupId}`. An entry whose tab or group has `alignEnd` gets
  `sm:ml-auto`. The top bar selects the entry of the open tab: the tab itself, or the group of the
  open member.
- **Second bar**: while the open tab is a member of a group with at least two visible members, a
  second `TabBar`, inside `data-testid="settings-subtabs"`, lists those members, each with its own
  `settings-tab-{id}`, icon, label (hidden on a phone too) and badge, the open one selected. It
  takes the same props (`hideLabelOnMobile`, `scrollable`) and the same colour roles as the top bar.
  A group with one visible member gets no second bar: its entry opens that member directly, and
  the member has no `settings-tab-{id}` of its own. No context of today's registry makes such a
  group since lot N69-2 (a regular user sees no member of `administration`, an administrator all
  five), but the page still handles it, on a registry of the test's own (see the tests below).
- **Clicks** (`selectTop()`): a tab entry opens its tab; a group entry opens the group's first
  visible member, unless one of its members is open already, which stays, its body not mounted
  again. A member of the second bar opens that member.
- **Both bars are `scrollable`**: entries that do not fit the card (French or Spanish on a narrow
  screen) scroll sideways instead of being clipped by its `overflow-hidden`, the active one stays
  whole in view, and the sides that hide entries fade (see
  [Scrollable tab bar](../core-ui/toolbar.md#tabbar-scrollable)).
- **Body**: the active tab's `component` alone, with `props(ctx)` spread on it. The spread is live:
  when the auth store changes, the body on screen receives the new props. The heading shown on a
  phone names the active tab, a member and never its group: *Global Settings*, not
  *Administration*.
- **Active tab**: always a tab, never a group. The first visible tab, unless `?tab=` names a visible
  tab or a group: a member's `id` opens that member inside its group (with the second bar when the
  group has two visible members or more), a group's `id` its first visible member
  (`?tab=administration` opens `admin`, for an administrator). The choice runs in `$effect.pre`, so
  the tab that `?tab=` names is the first body mounted: the default body never mounts, not even for
  an instant. Clicking a tab does not rewrite the URL, so a `?tab=` value is applied once: a later
  page update that keeps it does not take back the tab the user picked, while a new value is
  applied again. An unknown id, the id of a tab this user cannot see, or that of a group with no
  visible member, is ignored: a regular user's `?tab=admin` or `?tab=administration` opens
  `profile`, and the body of Global Settings never mounts for them. A `?tab=` naming a tab that
  becomes visible later (the user is promoted while on the page) is applied when the tab appears,
  inside its group. If the active tab stops being visible, the first visible tab opens.
- **Badges**: a tab entry shows its `badge(ctx)`, a group entry the sum of its visible members',
  and `TabBar` draws none for `0`. They are read while the bars are derived, so a badge follows the
  reactive state it reads: a count that arrives after the first render shows at once.
- **Prefetch**: an `$effect` calls the `prefetch(ctx)` of every visible tab that has one, when the
  page mounts and again whenever the context changes (a promotion included, which prefetches the
  tab that has just appeared); never for a tab this context does not show. The calls run inside
  `untrack()`: a prefetch reads the state it fills (`ensureLoaded()` reads the security checks'
  `status`), and a tracked read would run the effect again each time that state moves — after a
  failure, a new request, in a loop. So nothing else prefetches again: not a change of tab, of group
  or of `?tab=`, nor a change of the state a prefetch reads.

**Adding a tab** takes one entry in `SETTINGS_TABS`, plus the import of its body. The `users`
entry, a tab only administrators see, in the `administration` group, is a complete example:

```ts
import {Users} from 'lucide-svelte';
import UsersTab from '$lib/features/settings/tabs/UsersTab.svelte';

export const SETTINGS_TABS: readonly SettingsTab[] = [
    // profile (10), preferences (20), plugins (25), about (30), admin (100, administration)
    // Administrators only: the accounts and the open invitations (decision D-A10).
    {id: 'users', labelKey: 'settings.users', icon: Users, order: 110, component: UsersTab, visible: (ctx) => ctx.isSuperuser, group: 'administration'},
];
```

- **`order`**: a free number between the neighbours. The orders leave gaps, so no other tab is
  renumbered; 110 puts `users` after Global Settings (100) in the group's second bar. A tab without
  a `group` and with an `order` between 30 and 100 lands after About, on the left; above 100, after
  the group's entry, which sits where its first member (100) would be, so on the right. Every
  `order` is unique.
- **`visible`**: `(ctx) => ctx.isSuperuser` keeps the tab out of a regular user's bars altogether,
  and a `?tab=` naming it is ignored for them. Leave `visible` out for a tab everyone sees.
- **`group`**: `'administration'` for a tab that looks after the instance: it has no button of its
  own in the top bar, and shows in the group's second bar. Leave it out for a tab of the top bar.
- **`props`**: only when the body depends on the context, as `admin` does for `canEdit`. Since lot
  N69-2 only administrators see that tab, so `canEdit` is always `true` on screen: the read-only
  branch, `canEdit: false`, stays in `GlobalSettingsTab`, unreached from the interface, until a
  cleanup.
- **`badge` and `prefetch`**: only for a tab whose button counts something, today `security` alone.
  `badge` reads a reactive count synchronously, `0` until there is one; `prefetch` starts what the
  count needs, does nothing for a context the tab is not for, and nothing again once loaded, as
  `securityChecks.ensureLoaded()` does.
- **`alignEnd`**: one tab or one group carries it, today the `administration` group; no tab does,
  though the page still honours a tab's.
- **`id` and `labelKey`**: the `id` is unique, made of lowercase letters, digits and dashes, starts
  with a letter, and is no group's `id`; the `labelKey` is a sentence in all four catalogues.
- **Tests**: `lib/features/settings/settingsTabs.test.ts` pins the content of the registry through
  its `TODAY` table, so the new tab adds its row there in the same change, its id to the `CONTEXTS`
  and `BARS` lists of those who see it and, when it joins the group, to `ADMINISTRATION`, with a
  `vi.mock` of its body module like the others; the cases that list today's tabs by name follow it
  (`users` also has two cases of its own: STAB-01, hidden from a regular user, and STAB-02, order
  110 after `admin`, both members of the group; `admin` has one, rewritten by lot N69-2: hidden
  from a regular user, shown to an administrator, its `props` still `{canEdit: isSuperuser}`). The
  same file checks the ids, the orders and the labels in the four catalogues, the group and what
  its tabs carry (STAB-03 to STAB-14: one group, its label, icon and members, no tab with
  `alignEnd`, `security` the only tab with a badge and a prefetch, the bar of each context;
  STAB-14, lot N69-2: no `administration` entry nor any of its members in a regular user's bar,
  the entry once in an administrator's, `admin` its first member), and `settingsBar()` on lists of
  its own (SBAR-01 to SBAR-05). `routes/(app)/settings/page.tabs.test.ts` tests the page on a
  registry of its own, with two groups (`crew`, and `office`, the stand-in for Administration as
  lot A8b had it, with one visible member for a regular user) and counts in a reactive box
  (SPAGE-01 to SPAGE-21: the top bar, the second bar and its clicks, `?tab=` naming a member or a
  group, the badges and their sums, the prefetch at the start, again for a new context and never
  otherwise). SPAGE-22 to SPAGE-24 (lot N69-2) render the page on the real registry: a regular
  user's page with neither `settings-tab-administration` nor `settings-tab-admin`, **Profile**
  open; `?tab=admin` and `?tab=administration` opening **Profile** for a regular user, the Global
  Settings body never mounted, and Global Settings, with `canEdit: true`, inside its group for an
  administrator. The file loads the real `settingsTabs` module (`importOriginal`), which imports
  every body: the mocked module's `SETTINGS_TABS` and `SETTINGS_TAB_GROUPS` are getters, answering
  the real lists while a case sets `mocks.registry.real` and the synthetic ones otherwise, and each
  real body is a probe named by its module (`mocks.realBodies`). A new tab adds its body there,
  with its `vi.mock` (a store the registry imports gets a no-op stand-in, as `securityChecks`
  does). `./dev.py test front-utility core-unit` runs `settingsTabs.test.ts`,
  `./dev.py test front-utility component-unit` runs `page.tabs.test.ts`.

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

### 👤 ProfileTab {: #profiletab }

Manages user profile information:

- **Avatar**: Editable via `ImagePickerWrapper` → `AssetPickerModal` → crop
- **Username** and **Email**: editable once the edit lock is open, each with its own save and undo
  (`PUT /api/v1/auth/profile`)
- **The email's password** ([Changing the Email](../../../architecture/security.md#email-change)):
  while the tab is unlocked and the email is another address than the stored one, a password input
  appears under the email's hint (`profile-email-password`, `autocomplete="current-password"`,
  placeholder `settings.currentPassword`), described by `profile-email-password-hint`
  (`settings.emailPasswordHint`). Both email Saves and `profile-save-all` stay disabled while it is
  empty; the username's Saves do not wait for it. The email's request is
  `{email, current_password}`, the username's never carries the password. The password is emptied
  whenever the email is back to the stored address, after a save included
- **Only the capitals changed** (P18, A-25): «another address» is decided by `sameEmail()` of
  `lib/features/auth/emailCase.ts`, which folds A–Z only, like the server's index on `lower(email)`
  (`user_service.email_fold`). The stored address in other A–Z capitals is still a modification (the
  row stays marked, the Saves are on, the new form is saved), but no password input appears and the
  request is `{email}` alone, without a `current_password` key (the server refuses an empty one).
  Letters outside A–Z compare as written: `émile@…` → `Émile@…` asks for the password
- **Refusals**: `CURRENT_PASSWORD_REQUIRED`, `CURRENT_PASSWORD_INVALID` and, since lot A8b (C11),
  `TOO_MANY_ATTEMPTS`, the `429` of the
  [failed sign-in limit](../../../architecture/security.md#login-limit), are worded by the tab
  (`PASSWORD_REFUSALS`: `settings.currentPasswordRequired`, `settings.currentPasswordIncorrect`,
  `settings.tooManyPasswordAttempts`, *Too many wrong passwords: wait a few minutes and try again.*)
  and published on `profile-error` as `data-error-code`. The typed email stays; the password is
  emptied after the first two, and kept after `TOO_MANY_ATTEMPTS`, since it may be right and waiting
  is all there is to do. Since lot A-21a, `PASSWORD_REFUSALS` also holds `USERNAME_INVALID`, a new
  username holding `@` (see
  [Which Account an Identifier Names](../../../architecture/security.md#sign-in-identifier)):
  `auth.validation.usernameNoAt`, the key of the [registration card](auth.md#registercard)'s own
  check, published as `data-error-code` like the others, never the server's sentence nor
  `settings.updateFailed`; the username goes back to the stored value. Any other refusal shows the
  server's `detail` when it is a sentence
  (*Email already registered*), `settings.updateFailed` for any other `detail` (another code, a
  `422` list), and puts the field back to the stored value. The banner clears after 5 seconds
- **Password change**: opens `PasswordChangeModal` (`features/settings/PasswordChangeModal.svelte`):
  the current password, the new one with `PasswordStrength` under it, and the confirmation. The
  modal binds `PasswordStrength`'s `valid` (`bind:valid={passwordMeetsRules}`) and keeps no copy of
  the [password rules](../../../architecture/security.md#password-rules): `password-change-submit`
  stays disabled until the three fields are filled, the rules hold and the confirmation matches.
  A refusal with status `429` whose `detail` is `{error_code: "TOO_MANY_ATTEMPTS", …}`, the
  [failed sign-in limit](../../../architecture/security.md#login-limit), shows
  `settings.tooManyPasswordAttempts` (lot A8b, C11), and the three fields keep what was typed; a
  `429` with another code, with a sentence or with a proxy's page, and `TOO_MANY_ATTEMPTS` on
  another status, go on to the cases below.
  A refusal whose `detail` is `{error_code: "PASSWORD_TOO_WEAK", …}` shows
  `auth.validation.passwordTooWeak`; the plain-string `detail`s of a wrong current password
  (*incorrect*) and of a new password equal to it (*different*) show
  `settings.currentPasswordIncorrect` and `settings.passwordMustBeDifferent`; anything else, the
  message `trySave` extracts, `settings.passwordChangeFailed` when it finds none. An object `detail`
  is never lower-cased as a string: before A6c that threw
- **Delete account**: `delete-account-button` opens the
  [`AccountDeletionDialog`](#accountdeletiondialog) in `self` mode, with
  `testIdPrefix="profile-delete"`; once the account is deleted, the tab calls `auth.logout()` and
  goes to `/`
- Edit mode toggle to prevent accidental changes

Tests of the email's password: `tabs/ProfileTab.test.ts` (`./dev.py test front-utility component-unit`;
since A8b also the limit's `TOO_MANY_ATTEMPTS` through the row's Save and through `profile-save-all`:
the key and its code on the banner, the new email and the typed password kept, and three other
`429`s worded as any other refusal), and the «A6e» block of `frontend/e2e/settings.spec.ts`
(`./dev.py test front-utility settings`) on the lane's real backend, with a throwaway account and a
second browser context signed in before the change, and signed out by it. The password change:
`PasswordChangeModal.test.ts`, in the same `component-unit` action (what enables Save, what reaches
the server, the refusals with `PASSWORD_TOO_WEAK` among them, the rules taken from
`PasswordStrength`, and the limit's `429`: the key, never the server's sentence, the fields kept and
usable, no success and no toast).

### 🌍 GlobalSettingsTab (administrators only) {: #globalsettingstab-admin-only }

<div class="screenshot-container" style="margin: 1rem 0 2rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 600px;">
    <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Global Settings" style="width: 100%; display: block;">
</div>

System-wide configuration with lock toggle:

- Max file upload size
- Registration mode: a select with three options, `open`, `invite` and `disabled`
  (`settings.registrationModes.*`: **Open**, **By invitation**, **Closed**)
- Scheduler configuration and new-user defaults
- Other app-wide settings

Only a superuser has this tab (lot N69-2, decision D4 a): its entry in the
[tab registry](#tab-registry) (`admin`, labelled *Global Settings*) has
`visible: (ctx) => ctx.isSuperuser`, like every other member of the `administration`
[group](#tab-groups), of which it is the first. A regular user has no group at all, and a
`?tab=admin` opens their `profile` ([The page](#settings-page)). The entry still passes `canEdit`
through `props: (ctx) => ({canEdit: ctx.isSuperuser})`, so the tab always gets `canEdit: true` on
screen; without `canEdit` it would show a read-only indicator (`settings-readonly-indicator`)
instead of the lock toggle (`settings-lock-toggle`) and the bulk Save/Undo/Reset actions, a branch
no longer reached from the interface and kept until a cleanup. Hiding the tab hides no value: the
app still reads the global settings for every signed-in user, through `GET /api/v1/settings/global`
([Settings System](../../../architecture/settings.md)).

For the three *display* defaults (`default_language`, `default_currency`, `default_theme`) the
tab reuses the **same shared `Setting*` wrappers as the PreferencesTab**, passing the
`embedded` prop (see below) so they sit inside the tab's own cards without double separators.

**Registration mode.** `registration_mode`, in the *Security* category, is a `SettingSelect`
(default `invite`, `SETTING_DEFAULTS`, as in `GLOBAL_SETTINGS_DEFAULTS`: **Reset to Default** and
**Reset All to Defaults** propose `invite`, also on an upgraded instance that kept `open`). The
server variable `LIBREFOLIO_REGISTRATION` can pin it
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
  `instanceConfig.load({force: true})`, so the login page's **Register here**, the `/invite` page,
  the [open-registration warning](auth.md#open-registration-notice) and the Security tab's
  [finding](#securitytab) of the same name, with its badge, follow the new mode on this page load.

### 🧹 CachePanel

`CachePanel.svelte` shows the status of every named backend cache (the theine registry): name,
`current_size / maxsize`, and a human-formatted TTL, refreshed on demand. It sits in the Memory
category of the [Global Settings tab](#globalsettingstab-admin-only), so only administrators see it
since lot N69-2, although `GET /api/v1/settings/cache/status` still answers any authenticated user;
the per-cache **Clear** and **Clear all** buttons appear only when the
`canEdit` prop is set (it mirrors the Global-settings lock). Both clear actions pass through a
danger confirmation modal — after a clear, the next fetch hits the providers again. Backend
contract: [Cache Registry & Admin](../../../architecture/settings_cache.md).

### 👥 UsersTab {: #userstab }

`lib/features/settings/tabs/UsersTab.svelte`, the registry's `users` entry: administrators only,
no props. The accounts of the instance, the open invitations and the places taken. User side:
[Users & Invitations](../../../../admin/users.md); backend:
[Administrator API](../../../architecture/access_control.md#admin-user-api).

- **Load**: on mount, `GET /users` and `GET /users/invites` in parallel
  (`list_accounts_api_v1_users_get`, `list_invites_api_v1_users_invites_get`); the accounts and
  `usage` come from the first, the invitations from the second. The root, `users-tab`, carries
  `data-busy` (`'true'` while the lists load, at mount and after every action; `aria-busy` too). A
  failed load shows `settings.usersTab.errors.load` above the list, with an error toast.
- **Every action reloads**: `perform()` runs the call, notifies its outcome, then calls `load()`
  whether it succeeded or not. The tab never updates a row by itself: it shows the backend's
  answer. The invitation dialog reloads when it closes, the deletion dialog after a deletion; the
  reset-link dialog changes nothing in the lists.
- **Header**: `users-usage` with `data-used` and `data-max` (empty without a limit), drawn with
  `settings.usersTab.usage` (*{used} / {max} accounts*) or `usageUnlimited`.
  `users-billing-link` (`target="_blank"`, `rel="noopener noreferrer"`) only when
  `usage.billing_url` is set. The instance is full when `max_users` is set and
  `used >= max_users`: banner `users-limit-banner` (`role="status"`), with
  `users-limit-billing-link` when there is a billing URL.
- **Invite** (`users-invite-button`) is disabled with `data-disabled-reason`:
  `registration-disabled` when `instanceConfig.config.accounts.registration_mode` is `disabled`,
  checked first as the backend does, else `limit` when the instance is full. With
  `registration-disabled`, `users-invite-blocked` says why: `settings.usersTab.invite.blockedLocked`,
  naming `LIBREFOLIO_REGISTRATION`, when `registration_locked`; `settings.usersTab.invite.blocked`
  otherwise.
- **Accounts** (`users-accounts`): one [`UserRow`](#userrow) per account, in the backend's order.
  `isSelf` compares the account with `$currentUser.id`; `isOnlyActiveAdmin` is true for the account
  that is the only one with `is_superuser` and `is_active`.
- **Invitations** (`users-invites`): `InvitationsList`, see
  [Invitations and reset links](#invite-dialogs).
- **Confirmations**: one `ConfirmModal`, `testId="users-confirm"` (on its header; its buttons are
  `confirm-modal-confirm` and `confirm-modal-cancel`), for deactivate, cancel the setup link,
  promote, demote, sign out everywhere, restart the guides and revoke an invitation; `danger` for
  deactivate, cancel the setup link, demote and revoke. Title and message come from
  `settings.usersTab.confirm.<kind>.*`, the kind in camelCase (`cancelSetup`, `signOut`…), with
  `{username}`, or `{email}` for an invitation (`settings.usersTab.invites.noEmail` when it has
  none). Reactivate runs at once; the reset link and the deletion open their own dialogs.
- **Cancel the setup link** (`cancel-setup`, lot A-43), for the
  [initial administrator](../../../architecture/access_control.md#initial-admin) waiting for its
  setup: once confirmed, `PATCH /users/{id}` `{is_active: false, cancel_setup: true}`, which revokes
  its setup links ([Cancelling the setup link](../../../architecture/access_control.md#setup-cancel)).
  The row still reads *Waiting for setup* afterwards, so a success toast
  (`settings.usersTab.toasts.setupCancelled`, *The setup link of {username} no longer works.*) tells
  what changed. `cancel_setup` (lot A-51) makes the request a cancellation and nothing else, never
  the deactivation its `is_active: false` alone would be: when the administrator completed its setup
  after the list was loaded, the backend answers `409` `SETUP_COMPLETED` and changes nothing. The tab
  then shows `settings.usersTab.errors.SETUP_COMPLETED` in an error toast (*This administrator
  completed its setup in the meantime: nothing was changed.*), notifies `accounts.action.failed`
  with no success event, and reloads: the row shows the account active
  ([A setup completed meanwhile](../../../architecture/access_control.md#setup-completed-meanwhile)).

| Action | Call | Event on success | Toast |
|---|---|---|---|
| deactivate | `PATCH /users/{id}` `{is_active: false}` | `accounts.user.deactivated` | — |
| cancel the setup link | `PATCH /users/{id}` `{is_active: false, cancel_setup: true}` | `accounts.user.setup-cancelled` | success |
| reactivate | `PATCH /users/{id}` `{is_active: true}` | `accounts.user.reactivated` | — |
| promote | `PATCH /users/{id}` `{is_superuser: true}` | `accounts.user.promoted` | — |
| demote | `PATCH /users/{id}` `{is_superuser: false}` | `accounts.user.demoted` | — |
| sign out everywhere | `POST /users/{id}/sessions/revoke` | `accounts.user.sessions-revoked` | success |
| restart the guides | `POST /users/{id}/onboarding/reset`, body `null`: every flow | `accounts.user.onboarding-reset` | success |
| revoke an invitation | `DELETE /users/invites/{invite_id}` | `accounts.invite.revoked` | — |
| invite | `InviteDialog`: `POST /users/invites` | `accounts.invite.created` | — |
| reset link | `ResetLinkDialog`: `POST /users/{id}/password-reset-link` | `accounts.reset-link.created` | success |
| delete | `AccountDeletionDialog`: `DELETE /users/{id}` | `accounts.user.deleted` | success |

**App events.** Every outcome goes through `notify()` (`lib/stores/app/notify.svelte.ts`), which
keeps it in `window.__lf.events`, where the E2E reads it (`frontend/e2e/fixtures/app-events.ts`); the
toast, when there is one, is a field of the same call.

| Event | `detail` |
|---|---|
| `accounts.user.deactivated`, `setup-cancelled`, `reactivated`, `promoted`, `demoted`, `sessions-revoked`, `onboarding-reset` | `{user_id}` |
| `accounts.invite.revoked` | `{invite_id}` |
| `accounts.invite.created` | `{invite_id, grants_admin}` |
| `accounts.reset-link.created` | `{user_id}` |
| `accounts.user.deleted` | `{user_id, brokers_deleted, mode}` |
| `accounts.address.checked` | `{state, purpose}`, without a toast ([LinkShare](#linkshare)) |
| `accounts.link.copied` | `{purpose}`, with a success toast ([LinkShare](#linkshare)) |
| `accounts.action.failed` | `{action, code}`, plus `user_id` or `invite_id` when there is one, always with an error toast. `action` is `load`, `deactivate`, `cancel-setup`, `reactivate`, `promote`, `demote`, `sign-out`, `restart-guides`, `revoke-invite`, `invite`, `reset-link` or `delete`; `code` comes from [`accountErrors.ts`](#account-errors) |

#### UserRow {: #userrow }

`lib/features/settings/users/UserRow.svelte`. Props: `account` (`AdminAccount`, the `GET /users`
item, with `holds_place`, `pending_setup` and `avatar_url` when they are sent: all three optional
in `users/types.ts`), `isSelf`, `isOnlyActiveAdmin`, `full`, `onAction(action, account)`.

- The `<li>` is `users-row`, with `data-user-id`, `data-username`, `data-active`, `data-admin`,
  `data-pending-setup`, `data-protected` and `data-self` (`"true"` or `"false"`; `data-pending-setup`
  is `"false"` when the field is absent, the answer of an older server).
- `users-row-toggle`, a button with `aria-expanded` and `aria-controls`, shows the chevron, the
  account's avatar, the username, the badges (`settings.usersTab.badges.you`, `admin`, `inactive`,
  `protected`), the email and `settings.usersTab.createdOn`, and opens or closes the panel of
  actions under the row.
- **The avatar** (lot N69-4, decision D8 a): a [`UserAvatar`](../core-ui/file-upload.md#useravatar)
  right after the chevron, given `account.avatar_url ?? null`, its root `users-row-avatar` with
  `data-avatar="image"` or `"initial"`: an image uploaded to the app asked for as its 48×48
  preview, an address elsewhere as it is, and the username's initial in a neutral circle for an
  account without one, `avatar_url` null or absent.
- The own row (`isSelf`) has no action: `users-self-hint`, with a link to `/settings?tab=profile`.
- The buttons: `users-action-deactivate` for an active account or `users-action-reactivate` for an
  inactive one, `users-action-cancel-setup` in its place for an account with `pending_setup`;
  `users-action-demote` for an administrator or `users-action-promote` for a regular
  account; then `users-action-reset-link`, `users-action-sign-out`, `users-action-restart-guides`
  and `users-action-delete`.
- **An account waiting for its setup** (`pending_setup`, the
  [initial administrator](../../../architecture/access_control.md#initial-admin) whose setup link was
  never used, nor the account set up another way): the badge `users-badge-pending-setup` (`settings.usersTab.badges.pendingSetup`,
  *Waiting for setup*, in the tab's neutral style) in place of `inactive`; no
  `users-action-reactivate`, and so no `limit` reason on a full instance; under the buttons,
  `users-pending-setup-hint` (`settings.usersTab.pendingSetupHint`): the account activates through
  its setup link, and a lost link is replaced with `dev.py user setup-link` or by the hosting
  provider. The backend refuses its reactivation anyway, with `409` `PENDING_SETUP`
  ([Account Errors](#account-errors)). Since lot A-43:
    - `users-action-cancel-setup` (`settings.usersTab.actions.cancelSetup`, *Cancel setup link*, the
      `Link2Off` icon, the style of the row's other actions) stands where **Reactivate** would, and
      hands the account to `onAction('cancel-setup', account)`: the tab confirms, then cancels
      ([UsersTab](#userstab)). On a protected account it is turned off with the reason `protected`
      (`cancelReason`), shown under the buttons as for **Deactivate**: the backend refuses the
      cancellation with `409` `ACCOUNT_PROTECTED`;
    - `users-action-demote` is turned off with the reason `pending-setup`
      (`settings.usersTab.reasons.pendingSetup`): the account keeps its role until its setup, and the
      backend refuses its demotion with `409` `PENDING_SETUP` too;
    - `users-action-delete` stays enabled, without the `demote-first` reason: the backend deletes the
      waiting administrator directly ([Deleting an Account](../../../architecture/access_control.md#admin-account-deletion)).

    Its other buttons are those of any inactive account.

A button the backend would certainly refuse is `disabled`, with `data-disabled-reason`; the first
condition that holds gives the reason:

| Button | `data-disabled-reason` |
|---|---|
| `users-action-deactivate` | `protected` when `account.protected`; `last-admin` when the account is an administrator and `isOnlyActiveAdmin` |
| `users-action-reactivate` | `limit` when `full`, unless `account.holds_place`: an account waiting for its email verification with a live link already holds its place ([Email Verification](../../../backend/email.md#verification)). Never drawn for an account with `pending_setup` |
| `users-action-cancel-setup` | `protected` when `account.protected`: the backend refuses the cancellation of a protected account (`409` `ACCOUNT_PROTECTED`). Drawn only for an account with `pending_setup` |
| `users-action-demote` | `protected` when `account.protected`; `pending-setup` when the account has `pending_setup`; `last-admin` when the account is active and `isOnlyActiveAdmin` |
| `users-action-delete` | `protected` when `account.protected`; `demote-first` when the account is an administrator, active or not, unless it has `pending_setup` |

Promote, the reset link, sign out everywhere and restart the guides are never disabled. Under the
buttons, one line per distinct reason (`settings.usersTab.reasons.*`). The backend stays the
authority: `last-admin` never shows in a live session, as whoever reads the tab is an active
administrator and their own row has no actions, so the `409` `LAST_ADMIN` of the server covers what
the row cannot see.

#### Invitations and Reset Links {: #invite-dialogs }

- **`InvitationsList.svelte`**: props `invites` and `onRevoke(invite)`. `users-invites-empty` when
  there is none; otherwise one `users-invite-row` per invitation, with `data-invite-id`,
  `data-email` (empty without one) and `data-admin`: the email or
  `settings.usersTab.invites.noEmail`, the Admin badge, the dates of creation and expiry, and
  `users-invite-revoke`, which the tab confirms.
- **`InviteDialog.svelte`**: props `open`, `onClose`, `onCreated?(response)`. A `ModalBase`
  (`testId="users-invite-dialog"`, `trapFocus`) whose form starts empty at every opening:
  `users-invite-email` (sent trimmed, and only when not blank), `users-invite-admin`
  (`grants_admin`), `users-invite-create`, `users-invite-cancel`. A success shows `LinkShare` with
  `purpose="invite"`, the response's `path` and `url`, `expiresAt` from the invitation and
  `context: {email}`; `users-invite-done` calls `onClose`, then `onCreated`. A refusal stays on the
  form: `users-invite-error`, with `data-error-code`.
- **`ResetLinkDialog.svelte`**: props `open`, `account: {id, username}`, `onClose`. It opens on its
  explanation (`settings.usersTab.reset.message`) with `users-reset-create` and
  `users-reset-cancel`; a success shows `LinkShare` with `purpose="password_reset"` and
  `context: {username, userId}`, closed by `users-reset-close`. A failure shows
  `users-reset-error`, with `data-error-code`.

#### LinkShare {: #linkshare }

`lib/features/settings/users/LinkShare.svelte`: the panel both dialogs share a link through. Props:
`purpose` (`LinkPurpose`; the dialogs pass `invite` or `password_reset`), `path` (the page with the token in the
fragment, as the backend's `token_path()` builds it), `url` (`LIBREFOLIO_PUBLIC_URL` followed by
`path`, or `null`), `expiresAt`, `context?` (`{username?, email?, userId?}`). The root is
`link-share`, with `data-purpose`.

- **Address**: `link-share-address`, editable, starts from
  `initialBase(url, path, window.location.origin)` (`users/linkShare.ts`): the part of `url` before
  `path` when `url` ends with it — the public address, with the path prefix of a reverse proxy —
  otherwise the browser's origin; trailing slashes removed either way.
- **Link**: `link-share-link`, read-only, is `composeLink(address, path)`: the normalized address
  followed by `path`, character for character. Not a URL resolution, which would drop a path
  prefix, and no re-encoding of the token.
- **Expiry**: `link-share-expires`, with `data-expires-at`.
- **Check**: `link-share-probe`, whose `data-state` is one of:

| `data-state` | When |
|---|---|
| `idle` | The address, once normalized, is the starting one: no check |
| `checking` | 500 ms after the last keystroke on a changed address, while `checkAddress()` runs |
| `match`, `mismatch`, `unverifiable` | The verdict of the check |
| `invalid` | `normalizeBase()` refuses the address: not an absolute `http:` or `https:` URL, or with credentials, a `?` or a `#`. No check runs, and `link-share-copy` is disabled |

A newer edit outruns an older check: each run takes a generation number, and the verdict of a stale
one is dropped. Each verdict is notified as `accounts.address.checked`, without a toast.

`checkAddress(base, {issueNonce, fetchImpl?, timeoutMs?})` (`users/addressProbe.ts`) never throws.
The nonce comes from the Zodios client (`issue_address_probe_api_v1_users_address_probe_post`,
`POST /users/address-probe`); then `GET <base>/api/v1/auth/address-probe?nonce=…` (`probeUrl()`)
goes through a bare `fetch` — the global one, read at call time, or `fetchImpl` — called as a plain
function, with `{method: 'GET', credentials: 'omit', cache: 'no-store', referrerPolicy:
'no-referrer', signal}` and nothing else: no `headers`, no `body`, no `mode`. It must stay a CORS
simple request, as the backend's `CORSMiddleware` refuses every preflight. A `2xx` with
`{match: true}` is `match`, with `{match: false}` `mismatch`; anything else is `unverifiable`: the
nonce refused, a network or CORS error, mixed content, a local-network permission denied, another
status, a body that is not JSON or has no boolean `match`, or `PROBE_TIMEOUT_MS` (8 s) passed, when
the request is aborted. The server's half: [Address Probe](../../../architecture/security.md#address-probe).

- **Copy**: `link-share-copy` writes the link with `writeTextToClipboard()`
  (`$lib/utils/clipboard`: the Clipboard API, then the legacy copy) and notifies
  `accounts.link.copied` with a success toast (`settings.linkShare.copied`). When neither transport
  works, the link input is focused and selected, for a copy by hand. The button is disabled only in
  `invalid`.
- **Extra actions**: `link-share-actions` draws the registered actions, see below.

#### Link-Share Actions Registry {: #link-share-actions }

`lib/features/settings/users/linkShareActions.ts` holds `LINK_SHARE_ACTIONS: LinkShareAction[]`,
with one entry since workstream E's lot E4,
`{id: 'send-by-email', component: SendLinkByEmail, visible: () => sendByEmailVisible()}`: «Send by email», shown
while `email.links` is true ([Send by Email](../../../backend/email.md#send-by-email)). An entry is
`{id, component, visible?}`: `component` receives
`{link, purpose, context}` (`LinkShareActionProps`), and `visible({purpose, context})` filters it;
without `visible` the action is always shown. `visibleLinkShareActions(purpose, context)` returns
the visible ones in registry order, and `LinkShare` draws each in `link-share-actions`. Adding an
action is one line in the list, as «Send by email» shows; the dialogs do not change:

```ts
// `MyAction` stands for your own component
export const LINK_SHARE_ACTIONS: LinkShareAction[] = [
    {id: 'my-action', component: MyAction, visible: ({purpose}) => purpose === 'invite'},
];
```

#### Account Errors {: #account-errors }

`lib/features/settings/users/accountErrors.ts` turns a failed call into what the UI shows, for the
tab, its dialogs and the deletion dialog. `describeAccountError(error, action?)` returns
`{code, key, params?, message?}`; `accountErrorText(error, $_)` returns `message` when there is one,
the translated `key` otherwise.

| Answer | `code` | Shown |
|---|---|---|
| `detail.error_code` among `LAST_ADMIN`, `USER_LIMIT_REACHED`, `REGISTRATION_DISABLED`, `ACCOUNT_PROTECTED`, `SELF_DELETION`, `DEMOTE_FIRST`, `PENDING_SETUP`, `SETUP_COMPLETED` (`ACCOUNT_ERROR_CODES`) | that code | `settings.usersTab.errors.<code>`, but for `LAST_ADMIN` on a deletion (next row); a `detail.billing_url` is passed as `params.billingUrl`. `PENDING_SETUP` is the `409` of a reactivation or, since lot A-43, a demotion of the initial administrator waiting for its setup: a list loaded earlier may still offer either. `SETUP_COMPLETED` (lot A-51) is the `409` of a cancellation of a setup link that the administrator spent since the list was loaded |
| `detail.error_code` `LAST_ADMIN` on a deletion (`action` is `'delete'`, lot A-16) | `LAST_ADMIN` | `settings.usersTab.errors.LAST_ADMIN_DELETION`, which says to make another account an administrator first: on a deletion it can only be the `400` of `DELETE /auth/users/me`, the last active administrator deleting their own account, as another administrator's deletion answers `409` `DEMOTE_FIRST`. Without `'delete'`, the `409` `LAST_ADMIN` of a deactivation or a demotion keeps `settings.usersTab.errors.LAST_ADMIN` |
| `404` | `NOT_FOUND` | `settings.usersTab.errors.NOT_FOUND` |
| `422` | `INVALID_INPUT` | `settings.usersTab.errors.INVALID_INPUT` |
| `500` of a deletion (`action` is `'delete'`) | `DELETION_FAILED` | `settings.usersTab.errors.DELETION_FAILED`: nothing was deleted |
| `400` or `409` whose `detail` is a sentence | `null` | The server's sentence, as it is: a fallback for a refusal that carries no code. Every `400` and `409` of the calls these components make carries one today |
| Anything else | `null` | `settings.usersTab.errors.generic` |

### 🗑️ AccountDeletionDialog {: #accountdeletiondialog }

`lib/features/settings/AccountDeletionDialog.svelte`: the one dialog for deleting an account, one's
own from [ProfileTab](#profiletab) or another's from [UsersTab](#userstab). A `ModalBase` with
`trapFocus`. The rule it shows and applies is the backend's:
[Deleting an Account](../../../architecture/access_control.md#admin-account-deletion).

| Prop | Role |
|---|---|
| `open` | Opens the dialog; every opening loads the preview again and clears the typed name |
| `mode` | `'self'` or `'admin'` |
| `account` | `{id, username, is_active}` |
| `testIdPrefix` | The prefix `p` of every test id: `profile-delete` in the Profile tab, `users-delete` in the Users tab |
| `onClose` | Closes the dialog: cancel, a close request of `ModalBase`, or once **Deactivate** is done |
| `onDeleted(result)` | After a deletion, with `{user_id, brokers_deleted}`, the number of brokers that went |
| `onDeactivate?` | Administrators only: deactivate the account instead |

| | `mode="self"` | `mode="admin"` |
|---|---|---|
| Preview | `GET /auth/users/me/deletion-preview` | `GET /users/{id}/deletion-preview` |
| Deletion | `DELETE /auth/users/me` | `DELETE /users/{id}` |
| Title and warning | `settings.deleteAccountConfirm`, `settings.deleteAccountWarning` | `settings.accountDeletion.titleAdmin`, `settings.accountDeletion.warningAdmin` |
| After a deletion | ProfileTab: `auth.logout()`, then `/` | UsersTab: closes the dialog, reloads |

- **Deactivate first**: in `admin` mode, for an active account and with `onDeactivate` given, the
  dialog opens with *Deactivate instead?* and `${p}-deactivate`, which awaits `onDeactivate()`,
  then closes. The Users tab passes its own deactivation (`PATCH {is_active: false}`,
  `accounts.user.deactivated`, reload).
- **Preview** (`${p}-preview`; `${p}-dialog` carries `data-busy` while it loads):
  `${p}-broker-deleted`, with `data-broker-id` and `data-transactions`, for each broker that goes
  (or `settings.accountDeletion.noBrokersDeleted`); `${p}-broker-left`, with `data-broker-id` and
  `data-role` (`OWNER`, `EDITOR` or `VIEWER`), for each broker where only the access goes;
  `${p}-unpaired`, with `data-count`, when `transfers_unpaired` is above 0.
- **Confirmation**: `${p}-confirm-input` stays disabled until the preview is in;
  `${p}-confirm` (`settings.deleteAccountPermanently`) is enabled only while the typed text equals
  the username exactly. `${p}-cancel` closes. A failed preview shows
  `settings.accountDeletion.previewFailed` in `${p}-error`, and the deletion stays out of reach.
- **Outcome**: a success notifies `accounts.user.deleted`, with a success toast
  (`settings.accountDeletion.deletedSelf`, or `deletedAdmin` with `{username, count}`), then calls
  `onDeleted`; `brokers_deleted` is counted from the preview, as the deletion answers no numbers. A
  failure shows `${p}-error`, with `data-error-code`, and notifies `accounts.action.failed` with an
  error toast. The last active administrator deleting their own account gets the `400` `LAST_ADMIN`
  (lot A-16), shown as `settings.usersTab.errors.LAST_ADMIN_DELETION`, *You are the last active
  administrator: make another account an administrator before deleting yours.*, and the dialog stays
  open.

### 🧪 Users Tab and Account Deletion Tests {: #users-tests }

- `./dev.py test front-utility core-unit`: `users/linkShare.test.ts` (`initialBase`,
  `composeLink`), `users/addressProbe.test.ts` (`normalizeBase`, `probeUrl`, and `checkAddress`:
  the request options key by key, every verdict, the deadline on fake timers, never the network),
  `users/accountErrors.test.ts` (every code of `ACCOUNT_ERROR_CODES`, `PENDING_SETUP` included,
  the answers read from the status, and each key a sentence in the four catalogues; AERR-13 and
  AERR-14, lot A-51: the `409` `SETUP_COMPLETED` worded by its key, never the server's sentence;
  AERR-15 to AERR-19, lot A-16: the `400` `LAST_ADMIN` of a deletion worded by
  `LAST_ADMIN_DELETION`, the `409` `LAST_ADMIN` of the other actions keeping `LAST_ADMIN`),
  and the `users` row of `settingsTabs.test.ts`.
- `./dev.py test front-utility component-unit`: `tabs/UsersTab.test.ts` (the tab against a mocked
  server that changes as the backend would; UTAB-55 to UTAB-60, lot A-43: the cancellation of a
  setup link confirmed as danger, its one `PATCH`, event and toast, a dismissed confirmation that
  sends nothing, a stale demotion's `PENDING_SETUP`, and the keys in the four catalogues; UTAB-61
  and UTAB-62, lot A-51: the cancellation's body exactly `{is_active: false, cancel_setup: true}`,
  and a `409` `SETUP_COMPLETED` worded by its key, with no success, the row reloaded active),
  `users/LinkShare.component.test.ts` (not
  `LinkShare.test.ts`: `linkShare.test.ts` is in the same folder, and macOS volumes ignore case),
  `users/InviteDialog.test.ts`, `users/ResetLinkDialog.test.ts`, `users/UserRow.pendingSetup.test.ts`
  (the row of an account waiting for its setup: the badge, `data-pending-setup`, no
  **Reactivate** and no `limit` reason, the hint; since lot A-43, UPS-12 to UPS-23:
  `users-action-cancel-setup` in its place, turned off with `protected` on a protected account
  (UPS-23), `users-action-demote` off with `pending-setup`, `users-action-delete` enabled; every
  other row unchanged), `users/UserRow.avatar.test.ts` (URA-01 to URA-04, lot N69-4: the avatar
  in the toggle, between the chevron and the username, an uploaded image asked for as its 48×48
  preview, an address as it is, the initial without one, and the toggle still opening its panel),
  `AccountDeletionDialog.test.ts` (both modes; ADEL-28 and ADEL-29, lot A-16: a refused own
  deletion worded in the interface language, the `400` `LAST_ADMIN` as `LAST_ADMIN_DELETION` with the
  dialog left open, the `500` as `DELETION_FAILED`) and `tabs/ProfileTab.test.ts`.
- `./dev.py test front-utility admin-users` (`frontend/e2e/settings/admin-users.spec.ts`): the tab
  on the lane's real backend, `e2e_test_admin` acting on disposable accounts only. Only an
  administrator has the tab; the own row has no action; deactivate and reactivate, promote and
  demote; a reset link and an invitation, each token inspected live, the invitation then revoked;
  the address check (`match` on the lane's other loopback origin, through the real CORS path,
  `unverifiable` on a closed port, `invalid` for `ftp://`, `mismatch` from a stubbed stranger, back
  to `idle`); a deletion with its preview; sign out everywhere; the guides restarted. The deletion
  of one's own account through the Profile tab is `./dev.py test front-user account-deletion`
  (`frontend/e2e/brokers/account-deletion.spec.ts`).

### 🛡️ SecurityTab {: #securitytab }

`lib/features/settings/security/`, the registry's `security` entry (lot A8b): administrators only,
no props, the only tab with a `badge` and a `prefetch`. It lists the
[configuration checks](../../../architecture/security.md#configuration-checks) that
[`GET /api/v1/security/checks`](../../../architecture/security.md#security-checks-endpoint)
evaluates, and one check that only the browser can make, most severe first. Administrator side:
«Security» in [Global Settings](../../../../admin/settings.md).

| File | Role |
|---|---|
| `securityChecksApi.ts` | The seam over the generated client: `fetchSecurityChecks()` calls `list_security_checks_api_v1_security_checks_get` once and resolves to the `items` of the answer as they came, `SecurityCheck[]` (`{check_id, severity, i18n_key, detail}`, `severity` one of `ok`, `info`, `warning`, `error`); a refusal or a network error propagates |
| `securityFindings.ts` | Pure: what the tab lists, from the server's checks and from what only the browser knows |
| `securityChecks.svelte.ts` | The state: one read per page load, shared by the tab and the badges |
| `SecurityTab.svelte` | The body |

**The findings.** `securityFindings(checks, browser)`, where `browser` is
`{registrationMode, registrationLocked, hostname}`, returns `{attention, passed}`, two lists of
`SecurityFinding`, `{id, severity, messageKey, params, action?, source}`; it changes neither of its
inputs.

- `attention`: every check that is not `ok`, its `check_id` as `id`, its `i18n_key` as
  `messageKey`, a copy of its `detail` as `params`, `source: 'server'`; sorted error → warning → info
  by a stable sort, so that within a severity the server's order holds.
- The browser's own check: `openRegistrationNoticeFor({isAdmin: true, ...browser})`
  ([Open-Registration Warning](auth.md#open-registration-notice)), registration `open` reached
  through a host that `isLocalHost()` does not call local. Its notice becomes a `warning` with the
  notice's `id` (`accounts.openRegistration`), `messageKey`, `params` (`{}` today) and `action`,
  `source: 'browser'`, and nothing else of it (no `dismissible`). Pushed after the server's findings,
  the stable sort puts it after the server's warnings and before the infos. With the mode pinned by
  `LIBREFOLIO_REGISTRATION` the notice is `auth.notices.openRegistrationLocked`, without an action.
  The finding holds whether or not the notice was closed: the tab does not read the
  [instance notices](../../state/app-state.md#instance-notices).
- `passed`: the `ok` checks, in the server's order, with the severity `info` and never an action;
  their message is the check's own `ok` sentence.
- **Actions**, the in-app links where a setting of the app fixes the finding (`SERVER_ACTIONS`):
  `email.smtp`, `email.smtp_encryption` and `email.links` → `settings.securityTab.openEmail`
  (*Open the Email tab*), `/settings?tab=email`; `platform.plugin_secrets` →
  `settings.securityTab.openPlugins` (*Open the plugin settings*), `/settings?tab=plugins`; the
  browser's finding → its notice's action, `auth.notices.openRegistrationAction`
  (*Change who can sign up*), `/settings?tab=admin`. The other checks are fixed in the server's
  configuration: no link.
- `attentionCount(findings)`: the errors and the warnings of `attention`, the browser's included,
  never an info. It is the badge.

**The state.** `createSecurityChecks({fetch?, browser?})` builds a store; `securityChecks` is the
app's, created at import, asking nothing until it is told to. Its getters are reactive: `status`
(`idle`, `loading`, `ready` or `error`), `checks`, `answered` (true once a read has succeeded),
`findings` and `attentionCount`, which are `securityFindings(checks, browser())` and its count once
`answered`, empty lists and `0` before.

- `ensureLoaded()` reads once: nothing while a read is under way, whose promise concurrent calls
  share, nor once `ready`; again after a failure. There is no retry of its own.
- `reload()` always reads, sharing a read under way. The last checks stay listed meanwhile, and after
  a failure, which only sets `status` to `error`.
- The default `browser()` takes the registration from `instanceConfig.config.accounts` only once
  `instanceConfig.loaded`: before, the configuration in force is the default one, whose mode is
  `open`, and an invite-only instance would warn for nothing. The host is `window.location.hostname`.
  As `findings` is computed on each read, the browser's finding follows `instanceConfig`: a save of
  `registration_mode` in [GlobalSettingsTab](#globalsettingstab-admin-only), which reloads it, adds
  or removes the finding, badge included, without a new request.
- The default `fetch` is `fetchSecurityChecks()`.

**The badge.** The registry's `security` entry reads `securityChecks.attentionCount` as its `badge`,
summed on the `administration` entry, and its `prefetch` calls `securityChecks.ensureLoaded()` for an
administrator, nothing for a user. The page runs the prefetch when it opens, so the number shows
before the tab is opened; the tab's own `onMount` calls `ensureLoaded()` too, which reads nothing
more once the prefetch's read has succeeded. The store lives as long as the page load: leaving
Settings and coming back reads nothing again (unless the last read failed), «check again» or a
reload of the page does.

**The body.** `SecurityTab.svelte`, prop `checks`: the store to show, `securityChecks` unless a test
hands its own. The root, `security-tab`, carries `data-status` (the store's `status`), and
`data-busy` and `aria-busy`, true while a read runs.

- **Header**: `settings.securityTab.title` (*Security checks*), `settings.securityTab.description`,
  and **Check again** (`security-refresh`, `settings.securityTab.refresh`), which calls `reload()`,
  disabled while a read runs, its icon spinning.
- **Before the first answer** (`idle` or `loading`): `security-loading`, two pulsing placeholder rows.
- **A failed read**: `security-load-error`, `role="alert"`, `settings.securityTab.loadError`
  (*The security checks could not be loaded.*) with **Try again** (`security-retry`, `reload()`).
  After a failed «check again», the last findings stay listed under it.
- **The findings**: one `security-finding` per attention finding, with `data-check-id` and
  `data-severity`: the severity's icon (`AlertCircle`, `AlertTriangle`, `Info`, hidden from screen
  readers), the severity in words for screen readers only (`sr-only`,
  `settings.securityTab.severity.error`, `.warning`, `.info`: *Error*, *Warning*, *Information*,
  then a colon), the message `$_(messageKey, {values: params})`, and the action as a link
  (`security-finding-action`).
- **No finding**: `security-all-clear`, `settings.securityTab.allClear`
  (*Nothing needs your attention.*). An info is a finding, so it is not all clear.
- **The passed checks**: a closed `<details>`, `security-passed`, whose summary counts them
  (a neutral chip and `settings.securityTab.passed`, an ICU plural: *1 check passed*,
  *N checks passed*), with one `security-passed-check` (`data-check-id`) per `ok` check.
- **Colours**: roles only, after the state convention of `STATUS_TONES` (`lib/theme/toneClasses.ts`),
  written in the component: a tint per severity, `bg-lf-X-soft text-lf-X-on-soft border-lf-X-line`
  with `X` `danger`, `warning` or `info` (`success` for the all-clear), and a neutral chip,
  `bg-lf-neutral text-lf-secondary`, for the count of the passed checks.

Tests: `./dev.py test front-utility core-unit` runs `security/securityChecksApi.test.ts` (one call
of the generated client, its items as they came, an empty answer, a failure that propagates),
`security/securityFindings.test.ts` (the order by severity and within one, the passed checks, which
findings link where, the browser's finding against `openRegistrationNoticeFor()` for every mode, pin
and host, the inputs left as they were, `attentionCount`) and `security/securityChecks.test.ts`
(idle at creation, `ensureLoaded()` once and shared, `reload()` keeping the last checks, the
failures, the findings following the browser's state, the reactive getters, the defaults: the
generated client, `instanceConfig` and the page's host). `./dev.py test front-utility component-unit`
runs `security/SecurityTab.test.ts` (the store it is given, the placeholder, the findings and their
words, the links, the all-clear, the passed checks, «check again», the failures, colour roles only,
every key a message of the four catalogues).

### ℹ️ AboutTab {: #abouttab }

Read-only system information:

- Version (from Git tag)
- Backend/frontend info

Between the links (website, GitHub, license) and the system information sit two cards:

- **Support** (`about-support-card`): `SupportActions`, whose **Buy Me a Coffee** link and «Or share»
  divider follow `donationsVisible()`, shown only once `GET /system/instance` has answered
  `selfhosted` ([Instance configuration](../../state/app-state.md#instance-config)). The share
  buttons stay on every instance.
- **Legal notice** (`about-legal-card`): the `legal.title` heading, then
  [`LegalNotice`](#legal-notice). It does not depend on the diagnostics: it shows, links included,
  when `GET /system/info` fails.

#### The legal notice {: #legal-notice }

`lib/features/legal/` holds the legal notice of the instance (F09, workstream A; its places are
decision D-A11): two components that read `legal` of `instanceConfig`, the `{terms_url, privacy_url}`
of `GET /system/instance`
([Public instance configuration](../../../architecture/settings.md#public-instance-configuration)).

| Component | Shows | Used by |
|---|---|---|
| `LegalNotice.svelte` (`legal-notice`) | `legal.disclaimer`, then a row with **Terms of service** (`legal-terms-link`, `legal.terms`) and **Privacy policy** (`legal-privacy-link`, `legal.privacy`), each only while its address is set; no row without either | `AboutTab` (`about-legal-card`); `WelcomePage`, under its card ([Welcome](../../onboarding.md#welcome)) |
| `LegalLinks.svelte` (`legal-links`) | One line: `legal.disclaimerShort`, then the same two links, each after a `·`. Prop `tone`: `page` (the default) or `bar`, the colours of the sidebar's bar | [`AuthPageFrame`](auth.md#authpageframe-and-authcard) (`auth-legal-links`), under the card of every sign-in page; `Sidebar` (`sidebar-legal-links`, `tone="bar"`), after the version while the sidebar is expanded |

- Both links open in a new tab, with `rel="noopener noreferrer"`: the page they open gets no
  `window.opener` and no `Referer`.
- Neither component loads the configuration: the page around it does (the `(app)` layout,
  `AuthPageFrame`). The default configuration has no `legal`, so until the answer the notice shows
  without links, and the links appear in place when it lands.
- The keys `legal.title`, `legal.disclaimer`, `legal.disclaimerShort`, `legal.terms` and
  `legal.privacy` belong to the `app` i18n subsystem (`frontend/src/lib/i18n/app/`, prefix `legal`).
  The English wording of the disclaimer is quoted in
  [Hosting for Others](../../../../admin/hosting_providers.md#legal-pages).
- AI Export renders `legal.title` and `legal.disclaimer` too, without the components and without
  links, as the `legal_notice` section of every prompt
  ([Exact Prompt Order](../../../architecture/patterns/ai_export_composition.md)): a change to
  either text changes every exported prompt.
- Colour roles only, as everywhere: no palette class and no `dark:` variant, which the tests check in
  each place.
- Tests: `./dev.py test front-utility component-unit` runs `LegalNotice.test.ts`,
  `LegalLinks.test.ts`, `AboutTab.legal.test.ts`, `AuthPageFrame.legal.test.ts` and
  `Sidebar.legal.test.ts`; `./dev.py test front-utility onboarding-component-unit` runs
  `WelcomePage.legal.test.ts`.

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
