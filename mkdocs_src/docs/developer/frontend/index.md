# Frontend Development

This section covers the SvelteKit frontend architecture, components, and development patterns.

## Overview

LibreFolio's frontend is built with:

- **SvelteKit 2.x** - Full-stack web framework
- **Svelte 5** - Reactive UI framework with runes
- **Tailwind CSS 4.x** - Utility-first CSS (configured via `@theme` in CSS)
- **TypeScript** - Type safety
- **lucide-svelte** - Icon library

## Directory Structure

```
frontend/src/
├── routes/           # SvelteKit pages and routing
│   ├── (app)/        # Authenticated app routes
│   └── +page.svelte  # Login page
├── lib/
│   ├── api/          # API client
│   ├── components/   # Reusable components
│   │   ├── auth/     # Authentication components
│   │   ├── brokers/  # Broker management
│   │   ├── files/    # File management
│   │   ├── layout/   # Layout components (Sidebar, Header)
│   │   ├── settings/ # Settings components
│   │   ├── table/    # DataTable component suite
│   │   └── ui/       # Generic UI components
│   ├── i18n/         # Internationalization (EN, IT, FR, ES)
│   └── stores/       # Svelte stores
└── static/           # Static assets
```

## Documentation Sections

- [Components](components/index.md) - Reusable UI components
- [Pages](pages/index.md) - Application pages and routing
- [State Management](state/index.md) - Stores and reactive state
- [Internationalization](i18n.md) - Multi-language support
- [Styling](styling.md) - Tailwind CSS and theming

## Quick Links

| Topic | Description |
|-------|-------------|
| [DataTable](components/data-table.md) | Advanced table with sorting, filtering, pagination |
| [Authentication](components/auth.md) | Login, register, password reset modals |
| [Settings](components/settings.md) | User preferences and global settings |
| [File Upload](components/file-upload.md) | File uploader with preview |
