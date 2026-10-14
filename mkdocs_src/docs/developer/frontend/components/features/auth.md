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

- **Input**: Username or Email field; the value is trimmed before the login call.
- **Password**: Password field with visibility toggle (via `PasswordInput`).
- **State**: Uses `$lib/stores/app/auth` (`auth.login()`, `authError`, `isAuthLoading`) to manage loading state and errors.
    - `authError` holds `{key}`: `auth.invalidCredentials` for every 401 (one message, so the form never reveals
      whether an account exists), `auth.invalidInput` for a 422, `auth.loginFailed` for a non-axios failure;
      `LoginCard` translates the key with `$_()` when drawn, so it follows a language change on screen.
    - Any other axios error (another status, network error, timeout) gives `{message}`, its own text, verbatim.
- **Props**: `redirectTo` (default `/dashboard`), `successMessage` (shown after a registration),
  `onAuthenticated(requestedPath)` — when given, it replaces the plain `goto(redirectTo)` after a
  successful login (the login page uses it for the [onboarding gate](#post-login-onboarding-gate)).
- **Navigation**: Emits events to switch to Register or Forgot Password views.
- **Password managers**: see the [password-manager contract](#password-manager-contract).

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

- **Validation**: on blur of each field, and all together on submit:
    - Username (at least 3 characters, after trimming)
    - Email (format)
    - Password (the five strength rules: 8 characters, uppercase, lowercase, number, special character)
    - Confirm Password (match)
- **Strength Meter**: Integrated `PasswordStrength` component.
- **Error Handling**: Maps backend errors to translated messages — username taken, email
  already registered, registration disabled by the administrator, and field validation errors.

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

## 🔐 Password-manager contract {: #password-manager-contract }

Browsers' password managers decide which saved account goes into which field from each field's
`autocomplete` token, together with its `name`, its `id` and its label. The three credential forms
follow one contract, so that the browser offers saved credentials on the username field and
offers to save or update the password:

| Form | Field | `id` | `name` | `autocomplete` |
|---|---|---|---|---|
| `LoginCard` | Username or email | `login-username` | `username` | `username` |
| | Password | `login-password` | `password` | `current-password` |
| `RegisterCard` | Username | `register-username` | `username` | `username` |
| | Email | `register-email` | `email` | `email` |
| | Password | `register-password` | `new-password` | `new-password` |
| | Confirm password | `register-confirm-password` | `confirm-password` | `new-password` |
| `PasswordChangeModal` | Hidden username | — | `username` | `username` |
| | Current password | `currentPassword` | `current-password` | `current-password` |
| | New password | `newPassword` | `new-password` | `new-password` |
| | Confirm new password | `confirmPassword` | `confirm-password` | `new-password` |

- Every field has a `<label for>` reading the same translation key as its placeholder — visually
  hidden in the two cards, visible in the modal — which also gives screen readers a name that does
  not vanish with the first keystroke.
- Username fields set `autocapitalize="none"` and `spellcheck="false"`.
- `PasswordChangeModal` carries a `hidden`, `readonly` text input with the signed-in username, so
  the password manager knows which saved account the new password belongs to.
- No element carries an empty `id`: `PasswordInput` omits `id` and `name` when they are not given.
- The `data-testid`s are unchanged; E2E logins go through them.

`LoginCard.test.ts`, `RegisterCard.test.ts` and `PasswordChangeModal.test.ts` pin the attributes.
The autofill itself belongs to the browser and is checked by hand.

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

- **Toggle Visibility**: Eye icon to show/hide password (the toggle button is out of the tab order).
- **Styling**: Consistent styling with error state support (`hasError`).
- **Attributes**: `autocomplete` (`current-password` by default, `new-password`, `off`, `on`),
  `id`, `name`, `testId`, `placeholder`, `disabled`; `id` and `name` are omitted when empty.
- **Events**: Forwards `input`, `blur` and `keydown` events.

### 💻 Usage

```svelte
<script>
  import PasswordInput from '$lib/components/ui/input/PasswordInput.svelte';
  let password = '';
</script>

<PasswordInput
  bind:value={password}
  id="new-password"
  name="new-password"
  autocomplete="new-password"
  placeholder="Enter password"
  hasError={false}
/>
```

## 🚪 Post-login onboarding gate

After a successful login the auth cards hand over to the onboarding bootstrap. How it works — the
bootstrap states, Welcome, the intro tour and the contextual guides — is documented in
[Onboarding Guides](../../onboarding.md). What belongs to authentication:

- **After a login**, `LoginCard` calls `onAuthenticated(redirectTo)`, which the login page
  (`routes/+page.svelte`) wires to its `routeAuthenticated`: it runs `appBootstrap.load()`
  (`lib/features/onboarding/appBootstrap.svelte.ts`), then navigates with `replaceState` to
  `appBootstrap.resolveDestination(redirectTo)` — `/welcome?returnTo=…` while Welcome is due or a
  Welcome replay is armed, the requested path otherwise. A visitor of `/` who is already signed in
  (`auth.checkAuth()` on mount) takes the same route.
- **`redirectTo`** is the login page's `redirect` query parameter, `/dashboard` when absent.
  `resolveDestination` replaces anything that is not a same-origin absolute path — it must start
  with `/`, not with `//`, and contain no `\` — with `/dashboard`, so the parameter cannot send
  the user off the app.
- **A `blocked` bootstrap** (user settings failed to load, or onboarding progress failed with no
  usable cached Welcome) replaces the cards with `OnboardingBootstrapBlock`: **Retry** loads the
  bootstrap again, **Logout** signs out (`auth.logout()`). The authenticated layout shows the same
  block. A `degraded` bootstrap renders the app with `OnboardingBootstrapBanner`, whose only
  action is **Retry**.
- **Registration does not sign in**: `RegisterCard` dispatches `gotoLogin` with a success message,
  which the login view shows above the form.
- **Signed-out visitors** of an app route are sent back to `/` by `routes/(app)/+layout.svelte` —
  also when its auth check does not answer within 5 s — without a `redirect` parameter.
