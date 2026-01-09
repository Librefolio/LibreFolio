# Phase 9: Polish & Responsive

**Status**: ⏳ ONGOING (fatto incrementalmente)  
**Durata**: 2 giorni (distribuiti)  
**Priorità**: P2 (Nice-to-have, ma critico per UX)
**Dipendenze**: Tutte le fasi

---

## Obiettivo

Creare una libreria di componenti UI riutilizzabili, garantire responsive design su tutte le pagine, e implementare accessibilità e polish generale.

---

## 9.1 Componenti UI Riutilizzabili

### Tasks (da fare incrementalmente durante altre fasi)

- [ ] `Button.svelte`
- [ ] `Modal.svelte`
- [ ] `Card.svelte`
- [ ] `Badge.svelte`
- [ ] `DataTable.svelte`
- [ ] `DatePicker.svelte`
- [ ] `Dropdown.svelte`
- [ ] `SearchBox.svelte`
- [ ] `LoadingSpinner.svelte`
- [ ] `Toast.svelte`
- [ ] `Pagination.svelte`
- [ ] `Tabs.svelte`
- [ ] `ConfirmDialog.svelte`

### Button Component

```svelte
<!-- src/lib/components/ui/Button.svelte -->
<script>
  export let variant: 'primary' | 'secondary' | 'danger' | 'ghost' = 'primary';
  export let size: 'sm' | 'md' | 'lg' = 'md';
  export let disabled = false;
  export let loading = false;
  export let type: 'button' | 'submit' | 'reset' = 'button';
</script>

<button
  {type}
  {disabled}
  class="btn btn-{variant} btn-{size}"
  class:loading
  on:click
  {...$$restProps}
>
  {#if loading}
    <LoadingSpinner size="sm" />
  {/if}
  <slot />
</button>

<style>
  .btn {
    @apply px-4 py-2 rounded-lg font-medium transition-all inline-flex items-center gap-2;
  }
  .btn-primary { @apply bg-libre-green text-white hover:bg-opacity-90; }
  .btn-secondary { @apply bg-gray-200 text-gray-800 hover:bg-gray-300; }
  .btn-danger { @apply bg-red-600 text-white hover:bg-red-700; }
  .btn-ghost { @apply bg-transparent text-gray-700 hover:bg-gray-100; }
  .btn-sm { @apply px-3 py-1 text-sm; }
  .btn-lg { @apply px-6 py-3 text-lg; }
  .btn:disabled { @apply opacity-50 cursor-not-allowed; }
  .btn.loading { @apply cursor-wait; }
</style>
```

### Modal Component

```svelte
<!-- src/lib/components/ui/Modal.svelte -->
<script>
  import { createEventDispatcher } from 'svelte';
  import { fade, fly } from 'svelte/transition';
  
  export let open = false;
  export let title = '';
  export let size: 'sm' | 'md' | 'lg' | 'xl' = 'md';
  
  const dispatch = createEventDispatcher();
  
  function close() {
    open = false;
    dispatch('close');
  }
  
  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') close();
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if open}
  <!-- Backdrop -->
  <div 
    class="fixed inset-0 bg-black bg-opacity-50 z-40"
    on:click={close}
    transition:fade={{ duration: 150 }}
  ></div>
  
  <!-- Modal -->
  <div 
    class="fixed inset-0 flex items-center justify-center z-50 p-4"
    transition:fly={{ y: -20, duration: 200 }}
  >
    <div 
      class="bg-white rounded-lg shadow-xl w-full modal-{size} max-h-[90vh] overflow-auto"
      on:click|stopPropagation
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <!-- Header -->
      <div class="flex justify-between items-center p-4 border-b">
        <h2 id="modal-title" class="text-lg font-bold">{title}</h2>
        <button on:click={close} class="text-gray-400 hover:text-gray-600">✕</button>
      </div>
      
      <!-- Content -->
      <div class="p-4">
        <slot />
      </div>
      
      <!-- Footer (optional) -->
      {#if $$slots.footer}
        <div class="flex justify-end gap-2 p-4 border-t bg-gray-50">
          <slot name="footer" />
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
  .modal-sm { max-width: 400px; }
  .modal-md { max-width: 600px; }
  .modal-lg { max-width: 800px; }
  .modal-xl { max-width: 1000px; }
</style>
```

### Badge Component

```svelte
<!-- src/lib/components/ui/Badge.svelte -->
<script>
  export let variant: 'success' | 'warning' | 'danger' | 'info' | 'neutral' = 'neutral';
  export let size: 'sm' | 'md' = 'md';
</script>

<span class="badge badge-{variant} badge-{size}">
  <slot />
</span>

<style>
  .badge {
    @apply inline-flex items-center rounded-full font-medium;
  }
  .badge-sm { @apply px-2 py-0.5 text-xs; }
  .badge-md { @apply px-3 py-1 text-sm; }
  .badge-success { @apply bg-green-100 text-green-800; }
  .badge-warning { @apply bg-yellow-100 text-yellow-800; }
  .badge-danger { @apply bg-red-100 text-red-800; }
  .badge-info { @apply bg-blue-100 text-blue-800; }
  .badge-neutral { @apply bg-gray-100 text-gray-800; }
</style>
```

### Toast Notifications

```svelte
<!-- src/lib/components/ui/Toast.svelte -->
<script>
  import { fade, fly } from 'svelte/transition';
  import { toasts } from '$lib/stores/toasts';
</script>

<div class="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
  {#each $toasts as toast (toast.id)}
    <div 
      class="toast toast-{toast.type} flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg"
      transition:fly={{ x: 100, duration: 200 }}
    >
      <span class="icon">
        {#if toast.type === 'success'}✅{:else if toast.type === 'error'}❌{:else if toast.type === 'warning'}⚠️{:else}ℹ️{/if}
      </span>
      <span class="message">{toast.message}</span>
      <button on:click={() => toasts.dismiss(toast.id)} class="ml-2 text-gray-400 hover:text-gray-600">✕</button>
    </div>
  {/each}
</div>

<style>
  .toast { @apply bg-white border-l-4 min-w-[300px]; }
  .toast-success { @apply border-green-500; }
  .toast-error { @apply border-red-500; }
  .toast-warning { @apply border-yellow-500; }
  .toast-info { @apply border-blue-500; }
</style>
```

### Toast Store

```typescript
// src/lib/stores/toasts.ts
import {writable} from 'svelte/store';

interface Toast {
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    message: string;
}

function createToastStore() {
    const {subscribe, update} = writable<Toast[]>([]);

    return {
        subscribe,
        show(type: Toast['type'], message: string, duration = 5000) {
            const id = crypto.randomUUID();
            update(t => [...t, {id, type, message}]);
            if (duration > 0) {
                setTimeout(() => this.dismiss(id), duration);
            }
            return id;
        },
        success(message: string) {
            return this.show('success', message);
        },
        error(message: string) {
            return this.show('error', message, 10000);
        },
        warning(message: string) {
            return this.show('warning', message);
        },
        info(message: string) {
            return this.show('info', message);
        },
        dismiss(id: string) {
            update(t => t.filter(toast => toast.id !== id));
        }
    };
}

export const toasts = createToastStore();
```

### Loading Spinner

```svelte
<!-- src/lib/components/ui/LoadingSpinner.svelte -->
<script>
  export let size: 'sm' | 'md' | 'lg' = 'md';
</script>

<div class="spinner spinner-{size}">
  <div class="double-bounce1"></div>
  <div class="double-bounce2"></div>
</div>

<style>
  .spinner {
    @apply relative;
  }
  .spinner-sm { @apply w-4 h-4; }
  .spinner-md { @apply w-8 h-8; }
  .spinner-lg { @apply w-12 h-12; }
  
  .double-bounce1, .double-bounce2 {
    @apply absolute inset-0 rounded-full bg-libre-green opacity-60;
    animation: bounce 2s infinite ease-in-out;
  }
  .double-bounce2 {
    animation-delay: -1s;
  }
  
  @keyframes bounce {
    0%, 100% { transform: scale(0); }
    50% { transform: scale(1); }
  }
</style>
```

### File Structure

```
src/lib/components/ui/
├── Button.svelte
├── Modal.svelte
├── Card.svelte
├── Badge.svelte
├── DataTable.svelte
├── DatePicker.svelte
├── Dropdown.svelte
├── SearchBox.svelte
├── LoadingSpinner.svelte
├── Toast.svelte
├── Pagination.svelte
├── Tabs.svelte
├── ConfirmDialog.svelte
└── index.ts  # Re-exports
```

---

## 9.2 Responsive Mobile

### Checklist per ogni pagina

- [ ] Sidebar collapsible con hamburger (mobile)
- [ ] Bottom navigation bar (mobile) - opzionale
- [ ] Touch-friendly buttons (min 44x44px)
- [ ] Tabelle con scroll orizzontale o card view (mobile)
- [ ] Modal full-screen su mobile
- [ ] Form inputs stacked verticalmente (mobile)

### Sidebar Mobile

```svelte
<!-- In Sidebar.svelte -->
<script>
  import { page } from '$app/stores';
  
  let mobileOpen = false;
  
  // Chiudi sidebar su navigazione
  $: $page.url.pathname, mobileOpen = false;
</script>

<!-- Mobile Header (solo mobile) -->
<div class="md:hidden fixed top-0 left-0 right-0 bg-libre-green text-white p-4 flex items-center justify-between z-30">
  <button on:click={() => mobileOpen = !mobileOpen}>☰</button>
  <span class="font-bold">LibreFolio</span>
  <div></div>
</div>

<!-- Sidebar -->
<nav 
  class="sidebar fixed left-0 top-0 h-full w-64 bg-libre-green z-40 transition-transform"
  class:translate-x-0={mobileOpen || isDesktop}
  class:-translate-x-full={!mobileOpen && !isDesktop}
>
  <!-- ... contenuto sidebar ... -->
</nav>

<!-- Backdrop mobile -->
{#if mobileOpen}
  <div 
    class="fixed inset-0 bg-black bg-opacity-50 z-30 md:hidden"
    on:click={() => mobileOpen = false}
  ></div>
{/if}
```

### Responsive Table → Cards

```svelte
<!-- Esempio per mobile -->
<div class="hidden md:block">
  <!-- Desktop Table -->
  <table class="w-full">...</table>
</div>

<div class="md:hidden">
  <!-- Mobile Cards -->
  {#each items as item}
    <div class="card bg-white rounded-lg shadow p-4 mb-3">
      <div class="flex justify-between">
        <span class="font-bold">{item.name}</span>
        <Badge>{item.type}</Badge>
      </div>
      <div class="mt-2 text-sm text-gray-600">
        {item.description}
      </div>
      <div class="mt-3 flex gap-2">
        <Button size="sm">Edit</Button>
        <Button size="sm" variant="ghost">Delete</Button>
      </div>
    </div>
  {/each}
</div>
```

---

## 9.3 Accessibility & UX Polish

### Checklist per ogni pagina

- [ ] Keyboard navigation (Tab, Enter, ESC)
- [ ] Focus visible (outline chiaro)
- [ ] ARIA labels su elementi interattivi
- [ ] Loading states su tutte le API calls
- [ ] Error handling visibile (toast)
- [ ] Success feedback (toast)
- [ ] Conferma azioni distruttive (dialog)
- [ ] Empty states (quando lista vuota)

### Focus Visible Global

```css
/* In app.css */
:focus-visible {
    outline: 2px solid #1A4D3E;
    outline-offset: 2px;
}
```

### Empty State Component

```svelte
<!-- src/lib/components/ui/EmptyState.svelte -->
<script>
  export let title = 'No items found';
  export let description = '';
  export let icon = '📭';
</script>

<div class="empty-state text-center py-12">
  <div class="text-4xl mb-4">{icon}</div>
  <h3 class="text-lg font-medium text-gray-900">{title}</h3>
  {#if description}
    <p class="mt-2 text-gray-600">{description}</p>
  {/if}
  {#if $$slots.default}
    <div class="mt-4">
      <slot />
    </div>
  {/if}
</div>
```

### Confirm Dialog

```svelte
<!-- src/lib/components/ui/ConfirmDialog.svelte -->
<script>
  import Modal from './Modal.svelte';
  import Button from './Button.svelte';
  
  export let open = false;
  export let title = 'Confirm';
  export let message = 'Are you sure?';
  export let confirmLabel = 'Confirm';
  export let cancelLabel = 'Cancel';
  export let variant: 'danger' | 'warning' = 'danger';
  
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();
</script>

<Modal {open} {title} size="sm" on:close={() => dispatch('cancel')}>
  <p class="text-gray-600">{message}</p>
  
  <svelte:fragment slot="footer">
    <Button variant="ghost" on:click={() => dispatch('cancel')}>{cancelLabel}</Button>
    <Button variant={variant} on:click={() => dispatch('confirm')}>{confirmLabel}</Button>
  </svelte:fragment>
</Modal>
```

---

## Verifica Completamento

### Checklist Generale

- [ ] Tutti i componenti UI in `src/lib/components/ui/`
- [ ] Toast notifications funzionanti
- [ ] Modali chiudibili con ESC e click outside
- [ ] Sidebar responsive su mobile
- [ ] Tabelle leggibili su mobile
- [ ] Loading states su tutte le API calls
- [ ] Error handling con toast per tutti gli errori
- [ ] Empty states per liste vuote
- [ ] Confirm dialog per azioni distruttive
- [ ] Focus visibile per keyboard navigation

---

## Note

- Questa fase è **ongoing** - i componenti vengono creati man mano che servono
- Prioritizzare componenti più usati (Button, Modal, Badge, Toast)
- Testare su dispositivi reali quando possibile
- Utilizzare Chrome DevTools per testare viewport mobile

