# 🔐 Authentication Components

This section documents the authentication UI components used for login, registration, and password management.

!!! note "Card Components (Not Modals)"

    These components were renamed from `*Modal` to `*Card` (Feb 2026) because they are card-style forms displayed inline on the login page, not modal overlays. They do **not** extend `ModalBase`.

> Uses [PasswordInput and PasswordStrength](../core-ui/atoms.md#passwordinput) from the UI Base components.

<div class="screenshot-container" style="margin: 1rem 0 2rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 600px;">
    <img class="gallery-img" data-category="auth" data-name="01-login" alt="Login Page" style="width: 100%; display: block;">
</div>

## 🔑 LoginCard

The `LoginCard` handles user authentication via username/email and password.

### ⚡ Features

- **Input**: Username or Email field (autofocus).
- **Password**: Password field with visibility toggle (via `PasswordInput`).
- **State**: Uses `$lib/stores/auth` to manage loading state and errors.
- **Navigation**: Emits events to switch to Register or Forgot Password views.

### 💻 Usage

```svelte
<script>
  import LoginCard from '$lib/components/auth/LoginCard.svelte';
</script>

<LoginCard
  redirectTo="/dashboard"
  on:gotoRegister={() => showRegister = true}
  on:gotoForgot={() => showForgot = true}
/>
```

## 📝 RegisterCard

The `RegisterCard` handles new user registration with client-side validation.

<div class="screenshot-container" style="margin: 1rem 0 2rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 600px;">
    <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Registration with Password Strength" style="width: 100%; display: block;">
</div>

### ⚡ Features

- **Validation**: Real-time validation for:
    - Username (min length)
    - Email (format)
    - Password (strength rules)
    - Confirm Password (match)
- **Strength Meter**: Integrated `PasswordStrength` component.
- **Error Handling**: Maps backend errors (e.g., "username taken") to user-friendly messages.

### 💻 Usage

```svelte
<script>
  import RegisterCard from '$lib/components/auth/RegisterCard.svelte';
</script>

<RegisterCard
  on:gotoLogin={(e) => {
     showLogin = true;
     successMessage = e.detail.message;
  }}
/>
```

## 🔒 PasswordStrength

A visual indicator of password strength using `zxcvbn-ts`.

### ⚡ Features

- **Score**: Calculates a score from 0 (Very Weak) to 4 (Very Strong).
- **Visual Bar**: Color-coded progress bar (Red -> Orange -> Yellow -> Lime -> Green).
- **Rules Checklist**: Shows specific requirements:
    - Min 8 characters
    - Uppercase & Lowercase
    - Number
    - Special character

### 💻 Usage

```svelte
<script>
  import PasswordStrength from '$lib/components/ui/input/PasswordStrength.svelte';
  let password = '';
</script>

<input type="password" bind:value={password} />
<PasswordStrength {password} showRules={true} />
```

## 🔑 PasswordInput

A reusable input component for passwords.

### ⚡ Features

- **Toggle Visibility**: Eye icon to show/hide password.
- **Styling**: Consistent styling with error state support.
- **Events**: Forwards `input`, `blur`, `focus` events.

### 💻 Usage

```svelte
<script>
  import PasswordInput from '$lib/components/ui/input/PasswordInput.svelte';
  let password = '';
</script>

<PasswordInput
  bind:value={password}
  placeholder="Enter password"
  hasError={false}
/>
```

## 🚪 Post-login onboarding gate

Once `LoginCard`/`RegisterCard` hand off to an authenticated session, `routes/(app)/+layout.svelte`
runs `appBootstrap.load()` (`lib/features/onboarding/appBootstrap.svelte.ts`) before rendering any
authenticated route. It `Promise.allSettled`s three loads — user settings, onboarding progress,
global settings — and resolves to one of `'ready' | 'degraded' | 'blocked'`:

- **`blocked`** — user settings failed, or onboarding progress failed with no usable cached
  welcome status. The layout renders `OnboardingBootstrapBlock.svelte`: a full-screen **Retry** /
  **Logout** pair, nothing else. App routes stay inaccessible until a retry produces usable
  bootstrap state or the user logs out.
- **`degraded`** — onboarding progress failed to refresh but a previously-loaded `welcome` flow is
  already non-pending (i.e. the user has completed or skipped it before). The app renders normally
  behind a dismissible `OnboardingBootstrapBanner.svelte`, because a stale-but-known "not new
  here" status is safe to proceed on.
- **`ready`** — both loaded. `appBootstrap.resolveDestination(requestedPath)` then decides whether
  the requested route should redirect to `/welcome?returnTo=<path>` first: it does, whenever the
  cached `welcome` flow is `status === 'pending'` **or** a replay is armed
  (`onboarding.hasReplay('welcome', current_version)`); `safeInternalPath` rejects any
  `returnTo`/redirect target that isn't a same-origin absolute path (no `//`, no `\`), so the
  round trip through a query string can't be used to redirect off-app.

`WelcomePage.svelte` (`routes/(app)/welcome/+page.svelte`) itself only renders once
`onboarding.findFlow('welcome')` and the user's own settings are hydrated — otherwise it shows a
plain loading placeholder, never a form pre-filled with stale defaults. For an automatic pending
Welcome, submit calls `complete_welcome_onboarding`
(`backend/app/services/onboarding_service.py`), which writes the chosen
language/currency/avatar **and** flips the `welcome` progress row to `completed` in one database
transaction — an existing `UserSettings` row keeps its `theme` untouched; a first-ever row is
created with the instance's `default_theme`. Automatic **Skip setup permanently** calls the
sibling `transition_onboarding_progress(..., OnboardingStatus.SKIPPED, ...)` instead and writes
nothing to `UserSettings`.

Welcome replay deliberately takes a different path. **Continue** sends the explicitly selected
language/currency/avatar through the existing `PUT /api/v1/settings/user`, then clears only the
session replay token; it does not call the onboarding complete endpoint, so the existing
completed/skipped status is preserved. **Exit replay** clears the token and saves nothing — it
does not call either the settings PUT or the onboarding skip endpoint.

After either successful submit path, the route mirrors the submitted values into the
user-settings store, calls `currentLanguage.set(draft.language)`, awaits
`waitLocale(draft.language)` and a Svelte `tick()`, and only then calls
`onboardingGuide.maybeStartIntro(returnTo)`. The chosen locale therefore owns the narrative intro
and every coachmark from the first rendered frame. Automatic skipping and replay exit both
discard the unsaved Welcome draft and hand off using the already-active locale.

## 🧭 Narrative intro and tour

`INTRO_TOUR_STEP_IDS` starts with `intro.scene`, rendered by
`OnboardingIntroScene.svelte`. The scene rotates through three translation keys
(`line1`/`line2`/`line3`) and offers a manual **Start** action. Its 10-second auto-start fires
at most once if the user does nothing; a manual start invalidates the pending run so the
transition cannot fire twice.

The remaining ids are semantic stops in this exact order:

1. `intro.dashboard`
2. `intro.navigation` — `OnboardingOverlayHost` resolves this to the desktop sidebar toggle or
   mobile hamburger at runtime
3. `intro.transactions_nav`
4. `intro.transactions_import`
5. `intro.brokers_add` → `intro.brokers_currency`
6. `intro.fx_add` → `intro.fx_pair`
7. `intro.assets_add` → `intro.assets_config`
8. `intro.tools`
9. `intro.settings`

The Broker, FX, and Asset detail stops request registered `*.create` tour surfaces. Those hosts
open their real create modals with `tourPreview=true`; each modal guards its submit handler and
removes its save/create action, so the preview cannot write.

For an automatic pending tour, `OnboardingCoachmark.svelte` keeps **Skip permanently** and **X**
in the top action row; in replay mode, it renders **Exit replay** instead of **Skip
permanently**. **X** calls `onboardingGuide.suspend()` and retains the current intro cursor; it
never performs a backend transition. The footer renders **Back** and **Next**, using **Finish**
on `intro.settings`. Automatic **Finish** completes the pending flow and automatic **Skip
permanently** skips it. Replay **Finish** and **Exit replay** are strictly non-destructive: both
only clear the session replay token and never call complete/skip or change backend onboarding
status. There is no Pause action.

The same guide engine later drives the
**[Import Wizard's contextual guide](import-wizard.md#import-guide-wiring)**.

!!! note "Existing accounts are grandfathered, not migrated silently"

    Migration `003_user_onboarding_progress` (`backend/alembic/versions/`) inserts a `completed`
    row for `welcome`, `intro_tour`, and `import_guide` for every user that already existed when
    the flows were introduced. Accounts created afterwards get `pending` rows lazily, from
    `ensure_onboarding_progress`, the first time their progress is read.
