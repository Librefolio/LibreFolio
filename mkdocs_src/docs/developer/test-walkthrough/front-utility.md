# 🖥️ Front-Utility Tests

Frontend E2E tests for utility components and core UI flows.

## What's Tested

These Playwright tests cover fundamental UI components that are used across the entire application:

| Test Suite | Description |
|------------|-------------|
| **Authentication** | Login, registration, logout, session persistence |
| **Settings** | Profile editing, preferences tabs, password change |
| **Files** | File upload, file list, drag & drop, file deletion |
| **Select Components** | `SearchSelect`, `BaseDropdown`, currency pickers |
| **Image Crop** | `ImageEditModal`, crop presets, zoom, rotation, format export |

## Running

```bash
# Run all front-utility tests
./dev.py test front-utility all

# List available tests
./dev.py test front-utility --list

# Run a specific test file
./dev.py test front-utility auth

# Run with visible browser
./dev.py test front-utility all --headed
```

## Test Location

```
frontend/e2e/
├── auth.spec.ts          # Login, register, logout
├── settings.spec.ts      # Settings tabs and profile
├── files.spec.ts         # File upload and management
├── select.spec.ts        # Dropdown and search select
└── image-crop.spec.ts    # Image editing modal
```

