# 📦 State Management

*Status: Implemented (Feb 2026)*

## 📖 Overview

LibreFolio uses Svelte stores and Svelte 5 runes for state management.

## 🗄️ Stores

### 🔐 Auth Store (`$lib/stores/auth.ts`)

Manages authentication state:

- `isAuthenticated` - Boolean login status
- `currentUser` - User object or null
- `isAuthInitialized` - Loading complete flag
- `checkAuth()` - Validates session cookie against backend
- `login()` / `logout()` - Auth actions with store updates

### ⚙️ Settings Store (`$lib/stores/settings.ts`)

User preferences store with backend sync:

- `language` - UI language (en, it, fr, es)
- `theme` - Light/dark mode
- `baseCurrency` - Default currency
- `avatarUrl` - User avatar URL
- `setDirect()` - Immediate update without API call (used at login)
- Auto-loads from API after authentication

### 🌍 Global Settings Store (`$lib/stores/globalSettings.ts`)

App-wide configuration (admin-only write):

- `maxFileUploadMb` - Max upload size
- `allowRegistration` - Public registration toggle
- Other system-wide settings
- Loaded in `(app)/+layout.svelte` after auth check

### 🗣️ Language Store (`$lib/stores/language.ts`)

Reactive language management:

- Syncs with user preferences store
- Updates `svelte-i18n` locale
- Persists to `localStorage` for non-authenticated pages

## ⚡ Svelte 5 Runes

LibreFolio uses Svelte 5 runes:

- `$state` - Reactive state
- `$derived` - Computed values
- `$effect` - Side effects
- `$props` - Component props

## 📐 Patterns

- **Local state**: `$state` for component-level reactivity
- **Global state**: Svelte stores for cross-component data
- **API sync**: Settings stores sync with backend on save
- **Login init**: User preferences applied immediately at login (`setDirect()`)
