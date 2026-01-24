# Frontend Pages

*Status: Draft - Pages implemented, documentation in progress*

## Overview

Application pages and routing structure.

## Page Structure

```
frontend/src/routes/
├── +page.svelte              # Login page (public)
├── +layout.svelte            # Root layout
├── (app)/                    # Authenticated routes
│   ├── +layout.svelte        # App layout (sidebar, header)
│   ├── +page.svelte          # Dashboard (redirect)
│   ├── dashboard/
│   │   └── +page.svelte      # Main dashboard
│   ├── brokers/
│   │   ├── +page.svelte      # Broker list
│   │   └── [id]/
│   │       └── +page.svelte  # Broker detail
│   ├── files/
│   │   └── +page.svelte      # Files management
│   └── settings/
│       └── +page.svelte      # Settings
```

## Pages

### Login Page (`/`)

- Public access
- Login/Register/Forgot Password modals
- Animated background
- Redirect to dashboard after login

### Dashboard (`/dashboard`)

- Overview of portfolio
- Quick stats cards
- Recent activity
- *(Charts to be implemented)*

### Brokers (`/brokers`)

- List of configured brokers
- Add/Edit broker modals
- Broker detail with cash balances

### Files (`/files`)

- Two tabs: Static Resources / Broker Reports
- DataTable with sorting, filtering
- Upload interface
- Download/Delete actions

### Settings (`/settings`)

- Profile management
- User preferences
- Global settings (admin)

## Authentication Flow

1. User visits any `(app)/` route
2. `+layout.svelte` checks `isAuthenticated`
3. If not authenticated, redirect to `/`
4. Login page shows modals
5. After login, redirect back to intended page

## Data Loading

*(To be documented)*

- Server-side load functions
- Client-side API calls
- Error handling
