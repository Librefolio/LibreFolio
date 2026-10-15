# ⚙️ Settings Components

This section documents the components used for the Settings pages (User Preferences, Global Settings, Profile, Users).

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
(`$auth.user?.is_superuser ?? false`). The registry holds seven tabs:

| `id` | `order` | Body | Visible to | Extras |
|---|---|---|---|---|
| `profile` | 10 | `ProfileTab` | everyone | — |
| `preferences` | 20 | `PreferencesTab` | everyone | — |
| `about` | 30 | `AboutTab` | everyone | — |
| `admin` | 100 | `GlobalSettingsTab` | everyone | `props: (ctx) => ({canEdit: ctx.isSuperuser})`, `alignEnd: true` |
| `users` | 110 | [`UsersTab`](#userstab) | administrators | `visible: (ctx) => ctx.isSuperuser` |
| `backup` | 120 | `BackupTab` | administrators | `visible: (ctx) => ctx.isSuperuser` |
| `email` | 130 | `EmailSettingsTab` | administrators | `visible: (ctx) => ctx.isSuperuser` |

The first five bodies are in `lib/features/settings/tabs/`. The Backup tab's body, `lib/features/backup/BackupTab.svelte`
(label `backup.tab`), and the Email tab's, `lib/features/email/EmailSettingsTab.svelte` (label `email.tab.label`), live
with their features: for the Email tab see [The Email Tab](../../../backend/email.md#email-tab).

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

**Adding a tab** takes one entry in `SETTINGS_TABS`, plus the import of its body. The `users`
entry, a tab only administrators see, is a complete example:

```ts
import {Info, Shield, Sliders, User, Users} from 'lucide-svelte';
import UsersTab from '$lib/features/settings/tabs/UsersTab.svelte';

export const SETTINGS_TABS: readonly SettingsTab[] = [
    // profile (10), preferences (20), about (30), admin (100, alignEnd)
    // Administrators only: the accounts and the open invitations (decision D-A10).
    {id: 'users', labelKey: 'settings.users', icon: Users, order: 110, component: UsersTab, visible: (ctx) => ctx.isSuperuser},
];
```

- **`order`**: a free number between the neighbours. The orders leave gaps, so no other tab is
  renumbered; 110 puts `users` after Admin, in the right-hand group, while a number between 30 and
  100 would put a tab after About, in the left-hand group. Every `order` is unique.
- **`visible`**: `(ctx) => ctx.isSuperuser` keeps the tab out of a regular user's bar altogether,
  and a `?tab=` naming it is ignored for them. Leave `visible` out for a tab everyone sees.
- **`props`**: only when the body depends on the context, as `admin` does for `canEdit`.
- **`alignEnd`**: one tab carries it, today `admin`. A tab with a higher `order` (above 100) joins
  the right-hand group, after Admin, as `users` (110), `backup` (120) and `email` (130) do.
- **`id` and `labelKey`**: the `id` is unique, made of lowercase letters, digits and dashes, and
  starts with a letter; the `labelKey` is a sentence in all four catalogues.
- **Tests**: `lib/features/settings/settingsTabs.test.ts` pins the content of the registry through
  its `TODAY` table, so the new tab adds its row there in the same change, marked `adminOnly: true`
  when only an administrator sees it, with a `vi.mock` of its body module like today's five; the
  cases that list today's tabs by name follow it (`users` also has two cases of its own: STAB-01,
  hidden from a regular user, and STAB-02, order 110 after `admin`). The same file checks the ids,
  the orders and the labels in the four catalogues. `routes/(app)/settings/page.tabs.test.ts` tests
  the page on a registry of its own; it only gains a no-op `vi.mock` of the new body module, as it
  loads the real `settingsTabs` module (`importOriginal`), which imports every body.

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
- **Password change**: Opens `PasswordChangeModal`
- **Delete account**: `delete-account-button` opens the
  [`AccountDeletionDialog`](#accountdeletiondialog) in `self` mode, with
  `testIdPrefix="profile-delete"`; once the account is deleted, the tab calls `auth.logout()` and
  goes to `/`
- Edit mode toggle to prevent accidental changes

### 🌍 GlobalSettingsTab (read by everyone, edited by administrators) {: #globalsettingstab-admin-only }

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
indicator (`settings-readonly-indicator`) instead of the lock toggle (`settings-lock-toggle`) and
the bulk Save/Undo/Reset actions.

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
  `confirm-modal-confirm` and `confirm-modal-cancel`), for deactivate, promote, demote, sign out
  everywhere, restart the guides and revoke an invitation; `danger` for deactivate, demote and
  revoke. Title and message come from `settings.usersTab.confirm.<kind>.*`, with `{username}`, or
  `{email}` for an invitation (`settings.usersTab.invites.noEmail` when it has none). Reactivate
  runs at once; the reset link and the deletion open their own dialogs.

| Action | Call | Event on success | Toast |
|---|---|---|---|
| deactivate | `PATCH /users/{id}` `{is_active: false}` | `accounts.user.deactivated` | — |
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
| `accounts.user.deactivated`, `reactivated`, `promoted`, `demoted`, `sessions-revoked`, `onboarding-reset` | `{user_id}` |
| `accounts.invite.revoked` | `{invite_id}` |
| `accounts.invite.created` | `{invite_id, grants_admin}` |
| `accounts.reset-link.created` | `{user_id}` |
| `accounts.user.deleted` | `{user_id, brokers_deleted, mode}` |
| `accounts.address.checked` | `{state, purpose}`, without a toast ([LinkShare](#linkshare)) |
| `accounts.link.copied` | `{purpose}`, with a success toast ([LinkShare](#linkshare)) |
| `accounts.action.failed` | `{action, code}`, plus `user_id` or `invite_id` when there is one, always with an error toast. `action` is `load`, `deactivate`, `reactivate`, `promote`, `demote`, `sign-out`, `restart-guides`, `revoke-invite`, `invite`, `reset-link` or `delete`; `code` comes from [`accountErrors.ts`](#account-errors) |

#### UserRow {: #userrow }

`lib/features/settings/users/UserRow.svelte`. Props: `account` (`AdminAccount`, the `GET /users`
item), `isSelf`, `isOnlyActiveAdmin`, `full`, `onAction(action, account)`.

- The `<li>` is `users-row`, with `data-user-id`, `data-username`, `data-active`, `data-admin`,
  `data-protected` and `data-self` (`"true"` or `"false"`).
- `users-row-toggle`, a button with `aria-expanded` and `aria-controls`, shows the username, the
  badges (`settings.usersTab.badges.you`, `admin`, `inactive`, `protected`), the email and
  `settings.usersTab.createdOn`, and opens or closes the panel of actions under the row.
- The own row (`isSelf`) has no action: `users-self-hint`, with a link to `/settings?tab=profile`.
- The buttons: `users-action-deactivate` for an active account or `users-action-reactivate` for an
  inactive one; `users-action-demote` for an administrator or `users-action-promote` for a regular
  account; then `users-action-reset-link`, `users-action-sign-out`, `users-action-restart-guides`
  and `users-action-delete`.

A button the backend would certainly refuse is `disabled`, with `data-disabled-reason`; the first
condition that holds gives the reason:

| Button | `data-disabled-reason` |
|---|---|
| `users-action-deactivate` | `protected` when `account.protected`; `last-admin` when the account is an administrator and `isOnlyActiveAdmin` |
| `users-action-reactivate` | `limit` when `full` |
| `users-action-demote` | `protected` when `account.protected`; `last-admin` when the account is active and `isOnlyActiveAdmin` |
| `users-action-delete` | `protected` when `account.protected`; `demote-first` when the account is an administrator, active or not |

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
`purpose` (`LinkPurpose`, `invite` or `password_reset`), `path` (the page with the token in the
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
empty today. An entry is `{id, component, visible?}`: `component` receives
`{link, purpose, context}` (`LinkShareActionProps`), and `visible({purpose, context})` filters it;
without `visible` the action is always shown. `visibleLinkShareActions(purpose, context)` returns
the visible ones in registry order, and `LinkShare` draws each in `link-share-actions`. Adding an
action — workstream E's «Send by email» — is one line in the list; the dialogs do not change:

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
| `detail.error_code` among `LAST_ADMIN`, `USER_LIMIT_REACHED`, `REGISTRATION_DISABLED`, `ACCOUNT_PROTECTED`, `SELF_DELETION`, `DEMOTE_FIRST` | that code | `settings.usersTab.errors.<code>`; a `detail.billing_url` is passed as `params.billingUrl` |
| `404` | `NOT_FOUND` | `settings.usersTab.errors.NOT_FOUND` |
| `422` | `INVALID_INPUT` | `settings.usersTab.errors.INVALID_INPUT` |
| `500` of a deletion (`action` is `'delete'`) | `DELETION_FAILED` | `settings.usersTab.errors.DELETION_FAILED`: nothing was deleted |
| `400` or `409` whose `detail` is a sentence | `null` | The server's sentence, such as *Cannot delete account: you are the only administrator* from `DELETE /auth/users/me` |
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
  error toast. The only active administrator deleting their own account gets the server's sentence,
  a `400` without a code.

### 🧪 Users Tab and Account Deletion Tests {: #users-tests }

- `./dev.py test front-utility core-unit`: `users/linkShare.test.ts` (`initialBase`,
  `composeLink`), `users/addressProbe.test.ts` (`normalizeBase`, `probeUrl`, and `checkAddress`:
  the request options key by key, every verdict, the deadline on fake timers, never the network),
  and the `users` row of `settingsTabs.test.ts`.
- `./dev.py test front-utility component-unit`: `tabs/UsersTab.test.ts` (the tab against a mocked
  server that changes as the backend would), `users/LinkShare.component.test.ts` (not
  `LinkShare.test.ts`: `linkShare.test.ts` is in the same folder, and macOS volumes ignore case),
  `users/InviteDialog.test.ts`, `users/ResetLinkDialog.test.ts`, `AccountDeletionDialog.test.ts`
  (both modes) and `tabs/ProfileTab.test.ts`.
- `./dev.py test front-utility admin-users` (`frontend/e2e/settings/admin-users.spec.ts`): the tab
  on the lane's real backend, `e2e_test_admin` acting on disposable accounts only. Only an
  administrator has the tab; the own row has no action; deactivate and reactivate, promote and
  demote; a reset link and an invitation, each token inspected live, the invitation then revoked;
  the address check (`match` on the lane's other loopback origin, through the real CORS path,
  `unverifiable` on a closed port, `invalid` for `ftp://`, `mismatch` from a stubbed stranger, back
  to `idle`); a deletion with its preview; sign out everywhere; the guides restarted. The deletion
  of one's own account through the Profile tab is `./dev.py test front-user account-deletion`
  (`frontend/e2e/brokers/account-deletion.spec.ts`).

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
