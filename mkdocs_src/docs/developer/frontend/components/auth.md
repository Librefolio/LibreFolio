# Authentication Components

*Status: Draft - Components implemented, documentation in progress*

## Overview

Authentication UI components for login, registration, and password management.

## Components

### LoginModal

Modal dialog for user authentication with:

- Username/email and password fields
- "Remember me" option
- Link to registration
- Link to forgot password
- Animated background

### RegisterModal

User registration modal with:

- Username, email, password fields
- Password confirmation
- Password strength meter (zxcvbn)
- Terms acceptance checkbox
- Email validation

### ForgotPasswordModal

Password recovery flow:

- Email input
- Sends reset instructions
- Success/error feedback

### PasswordStrengthMeter

Visual password strength indicator:

- Uses `zxcvbn-ts` for strength calculation
- Color-coded bar (red → yellow → green)
- Strength label (Weak, Fair, Good, Strong, Very Strong)
- Optional requirement hints

### AnimatedBackground

Decorative background for login page:

- Animated wave patterns
- Chart line animations
- Dark mode support
- Responsive

## Files

```
frontend/src/lib/components/auth/
├── LoginModal.svelte
├── RegisterModal.svelte
├── ForgotPasswordModal.svelte
└── PasswordStrengthMeter.svelte
```

## Usage Example

*(To be documented)*

## Styling

The auth components use LibreFolio's brand colors:

- Primary green: `#1a4031`
- Accent beige: `#f5f4ef`
- Dark mode variants

## State Management

Auth state is managed in `$lib/stores/auth.ts`:

- `isAuthenticated` - Login status
- `currentUser` - User object
- `isAuthInitialized` - Loading state
