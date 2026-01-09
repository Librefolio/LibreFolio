# Phase 3: Layout & Settings

**Status**: ✅ COMPLETATA  
**Durata**: 1 giorno (completato)  
**Priorità**: P0 (MVP)
**Dipendenze**: Phase 2.5

---

## Obiettivo

Creare il layout principale dell'applicazione con sidebar navigation e la pagina settings per le preferenze utente.

---

## ✅ Implementato

### 3.1 Layout Principale con Sidebar

- [x] Creato `src/routes/(app)/+layout.svelte` - Layout protetto con Sidebar + Header
- [x] Creato `src/routes/(app)/+layout.ts` - SSR/prerender disabled
- [x] Creato `src/lib/components/layout/Sidebar.svelte` - Navigazione verticale con:
  - Logo LibreFolio
  - Links: Dashboard, Brokers, Assets, Transactions, FX, Settings
  - Language selector (4 lingue)
  - Username display
  - Logout button
  - Mobile responsive (toggle con overlay)
- [x] Creato `src/lib/components/layout/Header.svelte` - Header con:
  - Titolo pagina dinamico basato sul path
  - Mobile menu toggle button

### 3.2 Pagine App Structure

- [x] Creato `src/routes/(app)/dashboard/+page.svelte` - Dashboard con:
  - Quick stats cards (Total Value, Gain, Asset Count)
  - Quick actions (links a Brokers, Assets, Transactions, FX)
  - Welcome message
- [x] Creato `src/routes/(app)/brokers/+page.svelte` - Placeholder
- [x] Creato `src/routes/(app)/assets/+page.svelte` - Placeholder  
- [x] Creato `src/routes/(app)/transactions/+page.svelte` - Placeholder
- [x] Creato `src/routes/(app)/fx/+page.svelte` - Placeholder

### 3.3 Settings Page con Tabs

- [x] Creato `src/routes/(app)/settings/+page.svelte` - Tabs container
- [x] Creato `src/lib/components/settings/ProfileTab.svelte` - Mostra:
  - Username, Email, Account Created date
  - Change password (coming soon)
- [x] Creato `src/lib/components/settings/PreferencesTab.svelte` - Controlli:
  - Language selector (funzionante)
  - Base currency (coming soon)
  - Theme selector (coming soon)
- [x] Creato `src/lib/components/settings/AboutTab.svelte` - Info:
  - Version, description
  - GitHub link, License
  - Tech stack credits

### 3.4 Traduzioni

- [x] Aggiunte 46 nuove chiavi i18n in tutte e 4 le lingue
- [x] Totale: 110 chiavi, 100% complete

### 3.5 Miglioramenti UX (Aggiunti post-completamento)

- [x] **LANGUAGE_OPTIONS centralizzato**: Creata costante `LANGUAGE_OPTIONS` in `$lib/i18n/index.ts` per evitare duplicazione della lista lingue nei componenti
- [x] **Pagina 404 personalizzata**: Creato `src/routes/+error.svelte` con AnimatedBackground e stile coerente
- [x] **Redirect automatico se autenticato**: La pagina `/` ora reindirizza a `/dashboard` se l'utente è già loggato
- [x] **Traduzioni error pages**: Aggiunte chiavi `error.*` per pagine di errore (pageNotFound, goHome, goBack, etc.)

---

## ⚠️ Riferimento Phase 9

Se vengono creati componenti riutilizzabili, seguire le linee guida in [Phase 9: Polish](./phase-09-polish.md) e aggiornare quella fase con i dettagli del componente.

**Componenti previsti per questa fase**:

- `Sidebar.svelte` - Navigation sidebar
- `Header.svelte` - Top header
- `Tabs.svelte` - Tab navigation (se non già in Phase 9)

---

## 3.1 Layout Principale con Sidebar (1.5 giorni)

### Struttura Route Groups

```
src/routes/
├── (auth)/           # Layout pubblico (senza sidebar)
│   ├── +layout.svelte
│   └── login/
│       └── +page.svelte
├── (app)/            # Layout protetto (con sidebar)
│   ├── +layout.svelte    # ← QUESTO FILE
│   ├── +layout.ts
│   ├── dashboard/
│   ├── brokers/
│   ├── assets/
│   ├── transactions/
│   ├── fx/
│   └── settings/
```

### Tasks

- [ ] Creare `src/routes/(app)/+layout.svelte`
- [ ] Creare `src/routes/(app)/+layout.ts` (auth check)
- [ ] Creare `src/lib/components/Sidebar.svelte`
- [ ] Creare `src/lib/components/Header.svelte`

### Sidebar Component

```svelte
<!-- src/lib/components/Sidebar.svelte -->
<nav class="sidebar bg-libre-green h-screen w-64 fixed left-0 top-0">
  <!-- Logo -->
  <div class="logo p-6">
    <Shield /> LibreFolio
  </div>
  
  <!-- Navigation -->
  <ul class="nav-items">
    <li><a href="/dashboard">🏠 Dashboard</a></li>
    <li><a href="/brokers">🏦 Brokers</a></li>
    <li><a href="/assets">📊 Assets</a></li>
    <li><a href="/transactions">💸 Transactions</a></li>
    <li><a href="/fx">💱 FX Rates</a></li>
    <li><a href="/settings">⚙️ Settings</a></li>
  </ul>
  
  <!-- User Box (bottom) -->
  <div class="user-box absolute bottom-0 w-full p-4">
    <div class="username">{$currentUser?.username}</div>
    <LanguageSelector />
    <button on:click={logout}>Logout</button>
  </div>
</nav>
```

### Layout App

```svelte
<!-- src/routes/(app)/+layout.svelte -->
<script>
  import Sidebar from '$lib/components/Sidebar.svelte';
  import Header from '$lib/components/Header.svelte';
  import { checkAuth, isAuthenticated } from '$lib/stores/auth';
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  onMount(async () => {
    await checkAuth();
    if (!$isAuthenticated) {
      goto('/login');
    }
  });
</script>

<div class="app-layout flex min-h-screen">
  <Sidebar />
  <main class="main-content ml-64 flex-1 bg-libre-beige">
    <Header />
    <div class="page-content p-6">
      <slot />
    </div>
  </main>
</div>
```

### Responsive Behavior

- **Desktop (>1024px)**: Sidebar sempre visibile
- **Tablet (768-1024px)**: Sidebar collapsible con toggle
- **Mobile (<768px)**:
    - Sidebar nascosta di default
    - Hamburger menu nell'header
    - Sidebar overlay quando aperta
    - Bottom navigation bar per azioni rapide

### Mockup Desktop

```
┌────────────────────────────────────────────────────────┐
│ ┌──────────┬────────────────────────────────────────┐  │
│ │ 🛡️       │  Dashboard              [User] [🌐]   │  │
│ │ LibreFolio│────────────────────────────────────────│  │
│ ├──────────┤                                         │  │
│ │ 🏠 Dash  │                                         │  │
│ │ 🏦 Broker│        Main Content Area               │  │
│ │ 📊 Assets│                                         │  │
│ │ 💸 Trans │                                         │  │
│ │ 💱 FX    │                                         │  │
│ │ ⚙️ Setti │                                         │  │
│ │          │                                         │  │
│ ├──────────┤                                         │  │
│ │ username │                                         │  │
│ │ [🌐 EN]  │                                         │  │
│ │ [Logout] │                                         │  │
│ └──────────┴────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

### File da Creare

| File                                | Descrizione               |
|-------------------------------------|---------------------------|
| `src/routes/(app)/+layout.svelte`   | Layout con sidebar        |
| `src/routes/(app)/+layout.ts`       | Auth check                |
| `src/lib/components/Sidebar.svelte` | Navigation sidebar        |
| `src/lib/components/Header.svelte`  | Top header con breadcrumb |

---

## 3.2 Settings Page (1.5 giorni)

### Tasks

- [ ] Creare `src/routes/(app)/settings/+page.svelte`
- [ ] Implementare tabs: Profile, Preferences, About
- [ ] Creare componenti per ogni tab
- [ ] Salvare preferenze in localStorage
- [ ] Sync language con API calls

### Tabs Structure

#### Tab: Profile

- Username (read-only per ora)
- Email (read-only, future: editable)
- Change Password (future - Phase 8)
- Account created date

#### Tab: Preferences

- **Language Selector**:
    - Dropdown con flag emoji
    - Options: 🇬🇧 English, 🇮🇹 Italiano, 🇫🇷 Français, 🇪🇸 Español
    - Salva in localStorage + sync con API header

- **Base Currency** (future):
    - Dropdown con valute (da `GET /utilities/currencies`)
    - Default: EUR

- **Theme** (future):
    - Light / Dark toggle

#### Tab: About

- App version (da package.json)
- License: MIT
- GitHub link
- Credits

### Mockup

```
┌─────────────────────────────────────────────────────┐
│  Settings                                           │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────┬─────────────┬─────────┐              │
│  │ Profile  │ Preferences │  About  │              │
│  └──────────┴─────────────┴─────────┘              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━               │
│                                                     │
│  Language                                           │
│  ┌─────────────────────────────┐                   │
│  │ 🇬🇧 English              ▼ │                   │
│  └─────────────────────────────┘                   │
│                                                     │
│  Base Currency                                      │
│  ┌─────────────────────────────┐                   │
│  │ 🇪🇺 EUR - Euro           ▼ │                   │
│  └─────────────────────────────┘                   │
│                                                     │
│  Theme                                              │
│  ○ Light   ● Dark                                  │
│                                                     │
│  ┌─────────────────────────────┐                   │
│  │       Save Preferences      │                   │
│  └─────────────────────────────┘                   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### File da Creare

| File                                                | Descrizione     |
|-----------------------------------------------------|-----------------|
| `src/routes/(app)/settings/+page.svelte`            | Pagina settings |
| `src/lib/components/settings/ProfileTab.svelte`     | Tab profilo     |
| `src/lib/components/settings/PreferencesTab.svelte` | Tab preferenze  |
| `src/lib/components/settings/AboutTab.svelte`       | Tab about       |

---

## 3.3 Dashboard Placeholder (30 min)

### Task

- [ ] Creare `src/routes/(app)/dashboard/+page.svelte`
- [ ] Placeholder con messaggio "Dashboard coming soon"
- [ ] Redirect `/` autenticato a `/dashboard`

### File da Creare

| File                                      | Descrizione           |
|-------------------------------------------|-----------------------|
| `src/routes/(app)/dashboard/+page.svelte` | Placeholder dashboard |

---

## Verifica Completamento

### Test Manuali

- [ ] Login → redirect a dashboard
- [ ] Sidebar visibile su desktop
- [ ] Click su menu item → navigazione corretta
- [ ] Sidebar responsive su mobile (hamburger)
- [ ] Settings → cambio lingua → UI aggiornata
- [ ] Logout → session cleared → redirect a login
- [ ] Refresh → sessione persistente

---

## Dipendenze

- **Richiede**: Phase 2.5 (Auth integration funzionante)
- **Sblocca**: Phase 4+ (tutte le pagine app)

---

## Note

- La sidebar usa posizionamento fixed per scrolling indipendente
- Il main content ha `ml-64` per compensare sidebar width
- Su mobile la sidebar diventa overlay con backdrop
- Il language selector è duplicato (sidebar + settings) per comodità

