# State Management

*Status: Draft - To be documented*

## Overview

LibreFolio uses Svelte stores and Svelte 5 runes for state management.

## Stores

### Auth Store (`$lib/stores/auth.ts`)

Manages authentication state:

- `isAuthenticated` - Boolean login status
- `currentUser` - User object or null
- `isAuthInitialized` - Loading complete flag

### Theme Store

*(To be documented)*

### Preferences Store

*(To be documented)*

## Svelte 5 Runes

LibreFolio uses Svelte 5 runes:

- `$state` - Reactive state
- `$derived` - Computed values
- `$effect` - Side effects
- `$props` - Component props

## Patterns

*(To be documented)*

- Local vs global state
- Persistence to localStorage
- API synchronization
