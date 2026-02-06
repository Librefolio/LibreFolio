# Authentication Components

This section documents the authentication UI components used for login, registration, and password management.

## LoginModal

The `LoginModal` handles user authentication via username/email and password.

### Features

- **Input**: Username or Email field (autofocus).
- **Password**: Password field with visibility toggle (via `PasswordInput`).
- **State**: Uses `$lib/stores/auth` to manage loading state and errors.
- **Navigation**: Emits events to switch to Register or Forgot Password views.

### Usage

```svelte
<script>
  import LoginModal from '$lib/components/auth/LoginModal.svelte';
</script>

<LoginModal
  redirectTo="/dashboard"
  on:gotoRegister={() => showRegister = true}
  on:gotoForgot={() => showForgot = true}
/>
```

## RegisterModal

The `RegisterModal` handles new user registration with client-side validation.

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
  import RegisterModal from '$lib/components/auth/RegisterModal.svelte';
</script>

<RegisterModal
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
  import PasswordStrength from '$lib/components/ui/PasswordStrength.svelte';
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
  import PasswordInput from '$lib/components/ui/PasswordInput.svelte';
  let password = '';
</script>

<PasswordInput
  bind:value={password}
  placeholder="Enter password"
  hasError={false}
/>
```
