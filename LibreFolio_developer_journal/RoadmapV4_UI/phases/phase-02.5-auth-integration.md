# Phase 2.5: Auth Integration (Frontend ↔ Backend)

**Status**: ✅ COMPLETATA (9 Gennaio 2026)  
**Durata**: 1 giorno  
**Priorità**: P0 (Critica)
**Dipendenze**: Phase 1, Phase 2

---

## Obiettivo

Collegare il frontend di autenticazione (login, register, password recovery) con il backend. Tutte le UI auth sono **modali nella stessa pagina /login** per mantenere l'animazione
del background fluida e senza reset.

---

## ⚠️ Riferimento Phase 9

Se vengono creati componenti riutilizzabili (es. form inputs, buttons), seguire le linee guida in [Phase 9: Polish](./phase-09-polish.md) e aggiornare quella fase con i dettagli
del componente.

**Componenti creati in questa fase**:
- `LoginModal.svelte` - Modal per login
- `RegisterModal.svelte` - Modal per registrazione
- `ForgotPasswordModal.svelte` - Modal per istruzioni recovery

---

## 2.5.1 Architettura Modali Auth (1 ora) ✅

### Decisione Architetturale

**NON creiamo pagine separate** per register e forgot-password. Invece:

- `/login` (o `/`) rimane l'unica route pubblica
- La pagina contiene **3 modali intercambiabili**:
    1. `LoginModal` (default)
    2. `RegisterModal`
    3. `ForgotPasswordModal`
- L'`AnimatedBackground` rimane sempre attivo senza reset
- Transizioni fluide tra modali

### State Management

```typescript
// In +page.svelte
type AuthView = 'login' | 'register' | 'forgot-password';
let currentView: AuthView = 'login';
```

### Struttura Pagina

```svelte
<!-- src/routes/+page.svelte -->
<script>
  let currentView: 'login' | 'register' | 'forgot-password' = 'login';
</script>

<AnimatedBackground />

<div class="auth-container">
  {#if currentView === 'login'}
    <LoginModal 
      on:gotoRegister={() => currentView = 'register'}
      on:gotoForgot={() => currentView = 'forgot-password'}
    />
  {:else if currentView === 'register'}
    <RegisterModal 
      on:gotoLogin={() => currentView = 'login'}
    />
  {:else if currentView === 'forgot-password'}
    <ForgotPasswordModal 
      on:gotoLogin={() => currentView = 'login'}
    />
  {/if}
</div>
```

### Transizioni

```svelte
<!-- Transizione crossfade tra modali -->
{#key currentView}
  <div transition:fade={{ duration: 200 }}>
    <!-- Modal content -->
  </div>
{/key}
```

---

## 2.5.2 Login Modal Refactor (2 ore) ✅

### Stato Attuale

- ✅ Frontend: Login form già funzionante in +page.svelte
- ✅ Backend: `POST /auth/login` funzionante
- ✅ **Testato end-to-end**

### Tasks

- [x] Estrarre form login in `src/lib/components/auth/LoginModal.svelte`
- [x] Verificare che `credentials: 'include'` in API client
- [x] Aggiungere link "Forgot Password?" → dispatch `gotoForgot`
- [x] Aggiungere link "Register here" → dispatch `gotoRegister`
- [x] Testare login completo end-to-end
- [x] Verificare redirect a dashboard dopo login

### Struttura Componente

```svelte
<!-- src/lib/components/auth/LoginModal.svelte -->
<script>
  import { createEventDispatcher } from 'svelte';
  import { login, authError, isAuthLoading } from '$lib/stores/auth';
  import { goto } from '$app/navigation';
  
  const dispatch = createEventDispatcher();
  
  let username = '';
  let password = '';
  
  async function handleSubmit() {
    const success = await login(username, password);
    if (success) {
      goto('/dashboard');
    }
  }
</script>

<div class="modal bg-libre-beige rounded-2xl shadow-2xl">
  <!-- Header verde -->
  <div class="bg-libre-green p-8 flex flex-col items-center">
    <Shield /> LibreFolio
  </div>
  
  <!-- Form -->
  <form on:submit|preventDefault={handleSubmit} class="p-8 space-y-5">
    <!-- Username/Email -->
    <input type="text" bind:value={username} placeholder="Username or Email" />
    
    <!-- Password -->
    <input type="password" bind:value={password} placeholder="Password" />
    
    <!-- Forgot Password Link -->
    <div class="text-right">
      <button type="button" on:click={() => dispatch('gotoForgot')}>
        Forgot Password?
      </button>
    </div>
    
    <!-- Error -->
    {#if $authError}
      <div class="error text-red-600">{$authError}</div>
    {/if}
    
    <!-- Submit -->
    <button type="submit" disabled={$isAuthLoading}>
      {$isAuthLoading ? 'Logging in...' : 'Login'}
    </button>
    
    <!-- Register Link -->
    <div class="text-center">
      Don't have an account? 
      <button type="button" on:click={() => dispatch('gotoRegister')}>
        Register here
      </button>
    </div>
  </form>
</div>
```

---

## 2.5.3 Register Modal (2 ore) ✅

### Stato Attuale

- ✅ Backend: `POST /auth/register` funzionante
- ✅ Frontend: Modal creato e funzionante

### Tasks

- [x] Creare `src/lib/components/auth/RegisterModal.svelte`
- [x] Form fields con stessa palette di LoginModal:
    - Username (min 3 chars)
    - Email (validation)
    - Password (min 8 chars)
    - Confirm Password (match validation)
- [x] Validazione client-side
- [x] Submit a `POST /auth/register`
- [x] Success → switch a login con messaggio "Account created!"
- [x] Error → display inline
- [x] Link "Already have an account? Login" → dispatch `gotoLogin`
- [x] Traduzioni i18n

### Struttura Componente

```svelte
<!-- src/lib/components/auth/RegisterModal.svelte -->
<script>
  import { createEventDispatcher } from 'svelte';
  import { api } from '$lib/api';
  
  const dispatch = createEventDispatcher();
  
  let username = '';
  let email = '';
  let password = '';
  let confirmPassword = '';
  let error = '';
  let loading = false;
  
  async function handleSubmit() {
    // Validazione
    if (password !== confirmPassword) {
      error = 'Passwords do not match';
      return;
    }
    if (password.length < 8) {
      error = 'Password must be at least 8 characters';
      return;
    }
    
    loading = true;
    try {
      await api.post('/auth/register', { username, email, password });
      // Success - torna a login con messaggio
      dispatch('gotoLogin', { message: 'Account created! Please login.' });
    } catch (e) {
      error = e.data?.detail || 'Registration failed';
    } finally {
      loading = false;
    }
  }
</script>

<div class="modal bg-libre-beige rounded-2xl shadow-2xl">
  <!-- Header verde (stessa palette) -->
  <div class="bg-libre-green p-8 flex flex-col items-center">
    <Shield /> LibreFolio
    <span class="text-white mt-2">Create Account</span>
  </div>
  
  <!-- Form -->
  <form on:submit|preventDefault={handleSubmit} class="p-8 space-y-4">
    <input type="text" bind:value={username} placeholder="Username" />
    <input type="email" bind:value={email} placeholder="Email" />
    <input type="password" bind:value={password} placeholder="Password" />
    <input type="password" bind:value={confirmPassword} placeholder="Confirm Password" />
    
    {#if error}
      <div class="error text-red-600">{error}</div>
    {/if}
    
    <button type="submit" disabled={loading}>
      {loading ? 'Creating...' : 'Create Account'}
    </button>
    
    <div class="text-center">
      Already have an account? 
      <button type="button" on:click={() => dispatch('gotoLogin')}>Login</button>
    </div>
  </form>
</div>
```

---

## 2.5.4 Forgot Password Modal (1 ora) ✅

### Importante

**Per ora NON implementiamo email recovery** (richiede SMTP).
Mostriamo istruzioni per recovery via terminale server.

### Tasks

- [x] Creare `src/lib/components/auth/ForgotPasswordModal.svelte`
- [x] UI semplice con istruzioni CLI
- [x] Stesso styling delle altre modali
- [x] Link "Back to Login" → dispatch `gotoLogin`
- [x] Traduzioni i18n

### Struttura Componente

```svelte
<!-- src/lib/components/auth/ForgotPasswordModal.svelte -->
<script>
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();
</script>

<div class="modal bg-libre-beige rounded-2xl shadow-2xl">
  <!-- Header verde -->
  <div class="bg-libre-green p-8 flex flex-col items-center">
    <Shield /> LibreFolio
    <span class="text-white mt-2">Password Recovery</span>
  </div>
  
  <!-- Content -->
  <div class="p-8 space-y-4">
    <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
      <p class="font-medium text-yellow-800">
        ⚠️ Email recovery is not yet available.
      </p>
    </div>
    
    <div class="bg-gray-100 rounded-lg p-4 font-mono text-sm">
      <p class="mb-2">To reset your password, run:</p>
      <code class="block bg-gray-800 text-green-400 p-2 rounded">
        ./dev.sh user:reset &lt;username&gt; &lt;new_password&gt;
      </code>
      <p class="mt-2 text-gray-600 text-xs">
        Contact your administrator if you don't have server access.
      </p>
    </div>
    
    <button 
      class="w-full bg-libre-green text-white py-3 rounded-lg"
      on:click={() => dispatch('gotoLogin')}
    >
      ← Back to Login
    </button>
  </div>
</div>
```

---

## 2.5.5 First User Registration Flow (30 min)

### Problema

Alla prima esecuzione, non esiste nessun utente.

### Soluzione (CLI)

```bash
# L'admin crea il primo utente da terminale
./dev.sh user:create admin admin@example.com password123
```

### Documentazione

- [ ] Aggiungere sezione "First Run" nel README
- [ ] Spiegare come creare primo admin

---

## 2.5.6 Session Check on App Load (30 min)

### Tasks

- [ ] In `+layout.svelte` (app layout), chiamare `checkAuth()` on mount
- [ ] Se sessione valida → mostra contenuto
- [ ] Se sessione scaduta → redirect a login
- [ ] Loading spinner durante check

---

## File da Creare

| File                                                          | Descrizione                            |
|---------------------------------------------------------------|----------------------------------------|
| `frontend/src/lib/components/auth/LoginModal.svelte`          | Modal login (refactor da +page.svelte) |
| `frontend/src/lib/components/auth/RegisterModal.svelte`       | Modal registrazione                    |
| `frontend/src/lib/components/auth/ForgotPasswordModal.svelte` | Modal istruzioni recovery              |

## File da Modificare

| File                               | Modifica                             |
|------------------------------------|--------------------------------------|
| `frontend/src/routes/+page.svelte` | Usa modali intercambiabili con state |
| `frontend/src/lib/i18n/en.json`    | Traduzioni register/forgot           |
| `frontend/src/lib/i18n/it.json`    | Traduzioni register/forgot           |
| `frontend/src/lib/i18n/fr.json`    | Traduzioni register/forgot           |
| `frontend/src/lib/i18n/es.json`    | Traduzioni register/forgot           |
| `README.md`                        | Sezione "First Run"                  |

---

## Verifica Completamento

### Test Manuali

- [x] Login con credenziali corrette → redirect a dashboard
- [x] Login con credenziali errate → mostra errore inline
- [x] Click "Register here" → switch a RegisterModal (no page reload)
- [x] Register nuovo utente → success → switch a login con messaggio
- [x] Register username duplicato → errore visibile
- [x] Click "Forgot Password?" → switch a ForgotPasswordModal
- [x] Forgot password → mostra istruzioni terminale
- [x] "Back to Login" → switch a login
- [x] **AnimatedBackground continua senza reset durante tutti gli switch**
- [x] Logout → session cleared → redirect a login
- [ ] Refresh pagina con sessione valida → rimane loggato (da implementare in Phase 3)

---

## Dipendenze

- **Richiede**: Phase 1 (Frontend auth store), Phase 2 (Backend auth)
- **Sblocca**: Phase 3 (Layout con sidebar e logout)

---

## Note

- **IMPORTANTE**: Tutte le modali auth sono nella stessa pagina `/login`
- AnimatedBackground rimane sempre attivo → UX fluida
- Email recovery sarà implementato in una fase futura (richiede SMTP)
- Per ora il reset password è solo via CLI (accesso server)

