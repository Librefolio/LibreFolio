# 🔐 Authentication Components

This section documents the authentication UI components used for login, registration, and password management.

!!! note "Card Components (Not Modals)"
These components were renamed from `*Modal` to `*Card` (Feb 2026) because they are card-style forms displayed inline on the login page, not modal overlays. They do **not** extend
`ModalBase`.

<div class="screenshot-container" style="margin: 1rem 0 2rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 600px;">
    <img class="gallery-img" data-category="auth" data-name="01-login" alt="Login Page" style="width: 100%; display: block;">
</div>

## LoginCard

The `LoginCard` handles user authentication via username/email and password.

### Features

- **Input**: Username or Email field (autofocus).
- **Password**: Password field with visibility toggle (via `PasswordInput`).
- **State**: Uses `$lib/stores/auth` to manage loading state and errors.
- **Navigation**: Emits events to switch to Register or Forgot Password views.

### Usage

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

## RegisterCard

The `RegisterCard` handles new user registration with client-side validation.

<div class="screenshot-container" style="margin: 1rem 0 2rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 600px;">
    <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Registration with Password Strength" style="width: 100%; display: block;">
</div>

### Features

- **Validation**: Real-time validation for:
    - Username (min length)
    - Email (format)
    - Password (strength rules)
    - Confirm Password (match)
- **Strength Meter**: Integrated `PasswordStrength` component.
- **Error Handling**: Maps backend errors (e.g., "username taken") to user-friendly messages.

### Usage

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

## PasswordStrength

A visual indicator of password strength using `zxcvbn-ts`.

### Features

- **Score**: Calculates a score from 0 (Very Weak) to 4 (Very Strong).
- **Visual Bar**: Color-coded progress bar (Red -> Orange -> Yellow -> Lime -> Green).
- **Rules Checklist**: Shows specific requirements:
    - Min 8 characters
    - Uppercase & Lowercase
    - Number
    - Special character

### Usage

```svelte
<script>
  import PasswordStrength from '$lib/components/ui/input/PasswordStrength.svelte';
  let password = '';
</script>

<input type="password" bind:value={password} />
<PasswordStrength {password} showRules={true} />
```

## PasswordInput

A reusable input component for passwords.

### Features

- **Toggle Visibility**: Eye icon to show/hide password.
- **Styling**: Consistent styling with error state support.
- **Events**: Forwards `input`, `blur`, `focus` events.

### Usage

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

