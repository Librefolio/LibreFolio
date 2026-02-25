# Frontend Pages

*Status: Implemented (Feb 2026)*

## Overview

Application pages and routing structure. All authenticated routes are under `(app)/`.

## Page Structure

```
frontend/src/routes/
├── +page.svelte              # Login page (public)
├── +layout.svelte            # Root layout (auth init)
├── +error.svelte             # Error page
├── (app)/                    # Authenticated routes
│   ├── +layout.svelte        # App layout (sidebar, header, settings init)
│   ├── dashboard/
│   │   └── +page.svelte      # Main dashboard
│   ├── brokers/
│   │   ├── +page.svelte      # Broker list
│   │   └── [id]/
│   │       ├── +page.svelte  # Broker detail
│   │       └── +page.ts      # Load function
│   ├── files/
│   │   └── +page.svelte      # Files management (static + BRIM tabs)
│   ├── assets/
│   │   └── +page.svelte      # Assets (placeholder)
│   ├── transactions/
│   │   └── +page.svelte      # Transactions (placeholder)
│   ├── fx/
│   │   └── +page.svelte      # FX Management (placeholder)
│   └── settings/
│       └── +page.svelte      # Settings (4 tabs)
```

## Pages

### Login Page (`/`)

- Public access
- **LoginCard** / **RegisterCard** / **ForgotPasswordCard** (card-style, not modals)
- Animated background with waves and chart lines
- Redirect to dashboard after login
- User preferences (language, theme) applied on login

### Dashboard (`/dashboard`)

<div class="screenshot-container" style="margin: 0.5rem 0 1rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 700px;">
    <img class="gallery-img" data-category="dashboard" data-name="main" alt="Dashboard" style="width: 100%; display: block;">
</div>

- Overview of portfolio (placeholder)
- Quick stats cards
- *(Charts with ECharts to be implemented in Phase 8)*

### Brokers (`/brokers`)

<div class="screenshot-container" style="margin: 0.5rem 0 1rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 700px;">
    <img class="gallery-img" data-category="brokers" data-name="list" alt="Broker List" style="width: 100%; display: block;">
</div>

- Grid of broker cards with icons (fallback chain)
- Add/Edit broker via **BrokerModal** (extends ModalBase)
- Broker icon editable by clicking → **AssetPickerModal**
- Delete with confirmation dialog

### Broker Detail (`/brokers/[id]`)

- Header with icon, name, status
- Cash balances with deposit/withdraw
- Holdings table
- Recent transactions
- Import files section (BRIM) with plugin selection

### Files (`/files`)

<div class="screenshot-container" style="margin: 0.5rem 0 1rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 700px;">
    <img class="gallery-img" data-category="files" data-name="static-tab" alt="Files Page" style="width: 100%; display: block;">
</div>

- **Two tabs**: Static Resources / Broker Reports (BRIM)
- **DataTable** with sorting, filtering, pagination, URL-synced filters
- **Grid view** toggle with image previews and search
- Upload interface with:
    - Image files → **ImageEditModal** (crop, rotate, flip)
    - Non-image files → **FileEditModal** (rename)
- Copy link, download, delete actions
- File thumbnails via `?img_preview=` API

### Settings (`/settings`)

<div class="screenshot-container" style="margin: 0.5rem 0 1rem 0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.1); max-width: 700px;">
    <img class="gallery-img" data-category="settings" data-name="user-preferences" alt="Settings Page" style="width: 100%; display: block;">
</div>

- **4 tabs**: Preferences, Profile, Global (admin), About
- **ProfileTab**: Avatar editing via AssetPickerModal, username display
- **PreferencesTab**: Language, currency, theme
- **GlobalSettingsTab**: Admin-only settings with edit lock
- **AboutTab**: Version info (from Git tag), system info
- **PasswordChangeModal** from profile
- Mobile responsive with dropdown category selector

