# 🎨 Frontend Development

This section covers the SvelteKit frontend architecture, components, and development patterns.

## 📖 Overview

LibreFolio's frontend is built with:

- **SvelteKit 2.x** - Full-stack web framework
- **Svelte 5** - Reactive UI framework using **Runes** (`$state`, `$derived`, `$effect`)
- **Tailwind CSS 4.x** - Utility-first CSS (configured via `@theme` in CSS)
- **TypeScript** - Type safety
- **lucide-svelte** - Icon library

## 📂 Directory Structure

```
frontend/src/
├── routes/           # SvelteKit pages and routing
│   ├── (app)/        # Authenticated app routes (Dashboard, Brokers, etc.)
│   │   ├── dashboard/
│   │   ├── brokers/
│   │   │   └── [id]/    # Broker detail page
│   │   ├── assets/
│   │   ├── transactions/
│   │   ├── fx/
│   │   ├── files/
│   │   └── settings/
│   └── +page.svelte  # Login page (Public)
├── lib/
│   ├── api/          # API client (Zodios, generated from OpenAPI)
│   ├── components/   # Reusable components
│   │   ├── auth/     # LoginCard, RegisterCard, ForgotPasswordCard
│   │   ├── brokers/  # Broker cards, forms, icon, import
│   │   ├── files/    # FilesTable with DataTable
│   │   ├── layout/   # Sidebar, Header, LanguageSelector
│   │   ├── settings/ # Settings tabs (Profile, Preferences, Global, About)
│   │   ├── table/    # DataTable suite (ModalBase, ConfirmModal, etc.)
│   │   └── ui/       # Generic UI atoms
│   │       ├── input/    # PasswordInput, PasswordStrength
│   │       ├── media/    # ImageCropper, ImageEditModal, AssetPickerModal, FileEditModal
│   │       └── select/   # BaseDropdown, SimpleSelect, SearchSelect
│   ├── i18n/         # Internationalization (EN, IT, FR, ES)
│   ├── stores/       # Global state (Auth, Settings, Language)
│   ├── types/        # TypeScript type definitions
│   └── utils/        # Utilities (imageCrop, upload, urlFilters)
├── e2e/              # Playwright E2E tests (7 suites, 109+ tests)
└── static/           # Static assets
```

## ⚡ Svelte 5 Runes

LibreFolio fully embraces Svelte 5's **Runes** for reactivity, replacing the legacy `let` and `$` syntax.

### 🔑 Key Runes Used

- **`$state`**: Declares reactive state.
  ```typescript
  let count = $state(0);
  ```
- **`$derived`**: Declares derived state (automatically updates when dependencies change).
  ```typescript
  let double = $derived(count * 2);
  ```
- **`$effect`**: Side effects (runs when dependencies change).
  ```typescript
  $effect(() => {
      console.log(count);
  });
  ```
- **`$props`**: Declares component props.
  ```typescript
  let { title, active = false } = $props();
  ```

## 📚 Documentation Sections

- [Components](components/index.md) - Reusable UI components
- [FX Chain Algorithm](fx-chain-algorithm.md) - DFS pathfinding for currency conversion chains
- [Pages](pages/index.md) - Application pages and routing
- [State Management](state/index.md) - Stores and reactive state
- [Internationalization](i18n.md) - Multi-language support
- [Styling](styling.md) - Tailwind CSS and theming

---

## 🏗️ Build & Development

Frontend tasks are managed via `dev.py front`:

```bash
# Start Vite dev server with Hot Module Replacement
./dev.py front dev

# Build for production (output in frontend/build/)
./dev.py front build

# Build with source maps for debugging
./dev.py front build --debug

# Type-check with svelte-check
./dev.py front check

# Preview production build locally
./dev.py front preview
```

| Command | Description |
|---------|-------------|
| `front dev` | Starts Vite at `localhost:5173`, proxies API calls to backend |
| `front build` | Production build with minification and tree-shaking |
| `front build --debug` | Build with source maps (useful for debugging deployed code) |
| `front check` | Runs `svelte-check` for TypeScript and Svelte diagnostics |
| `front preview` | Serves the production build locally for testing |

!!! tip "Development workflow"
    Run `./dev.py server` in one terminal and `./dev.py front dev` in another. The Vite dev server proxies `/api` calls to the backend automatically.

## 🔗 Quick Links

| Topic                                    | Description                                        |
|------------------------------------------|----------------------------------------------------|
| [DataTable](components/data-table.md)    | Advanced table with sorting, filtering, pagination |
| [FX Chain Algorithm](fx-chain-algorithm.md) | DFS + graphology for multi-step FX routes       |
| [Authentication](components/auth.md)     | LoginCard, RegisterCard, ForgotPasswordCard        |
| [Settings](components/settings.md)       | User preferences, profile, and global settings     |
| [File Upload](components/file-upload.md) | File uploader, image crop, asset picker            |
