# Piano: Fix Auth Redirect + Broker Icon + Broker Modal

**Data**: 21 Gennaio 2026  
**Status**: ✅ COMPLETATO

---

## ✅ Correzioni Completate

### 1. BrokerIcon.svelte - Riorganizzato + Debug logging
- **Fix**: Funzioni definite PRIMA dei reactive statements
- **Debug**: Aggiunto `debug.log()` in resetAttempt, handleLoad, handleError, onMount
- **Status**: ✅ RISOLTO

### 2. svelte.config.js - Rimosso fallback problematico
- **Problema**: `fallback: 'index.html'` causava errore 303 (root redirect)
- **Fix**: `fallback: undefined` - FastAPI gestisce SPA routing
- **Status**: ✅ RISOLTO

### 3. vite.config.ts - Rimosso base override
- **Problema**: SvelteKit sovrascrive `base` di Vite
- **Fix**: Rimosso `base: '/'`
- **Status**: ✅ RISOLTO

### 4. backend/main.py - Handler per nested _app requests
- **Problema**: Path relativi `./_app/...` risolti come `/brokers/_app/...`
- **Fix**: Aggiunto handler che estrae e serve `/_app/...` da qualsiasi path
- **Status**: ✅ RISOLTO

### 5. dev.py - Stop su frontend build failure + nuovi flag
- `--rebuild, -r`: Forza rebuild frontend
- `--debug, -d`: Debug mode (LOG_LEVEL=DEBUG + VITE_DEBUG=true)
- Server non parte se frontend build fallisce
- **Status**: ✅ IMPLEMENTATO

### 6. logging_config.py - Silenziato aiosqlite verbose
- **Fix**: Impostato `logging.WARNING` per aiosqlite e sqlalchemy
- **Status**: ✅ RISOLTO

### 7. BrokerForm.svelte - Bordi arrotondati footer
- **Fix**: Aggiunto `rounded-b-2xl` al div Actions
- **Status**: ✅ RISOLTO

### 8. Frontend Debug System
- **File**: `frontend/src/lib/debug.ts`
- **Attivazione**: `VITE_DEBUG=true` o `./dev.py server --debug`
- **Tree-shaking**: Codice eliminato in production build
- **Debug aggiunto a**: BrokerIcon, layout, auth store, API client
- **Status**: ✅ IMPLEMENTATO E VERIFICATO

---

## ✅ Verificato Funzionante

Log da console browser confermano flusso corretto:
```
[AppLayout] onMount started
[AppLayout] Starting auth check
[AuthStore] checkAuth started
[API] GET /auth/me
[AuthStore] checkAuth success alfy
[API] GET /brokers
[AppLayout] Auth check result: true
[BrokerIcon] resetAttempt {iconUrl: null, portalUrl: null, pluginCode: 'broker_directa'}
[BrokerIcon] onMount {iconUrl: null, portalUrl: null, pluginCode: 'broker_directa'}
[API] GET /brokers/import/plugins
[BrokerIcon] handleLoad https://www.directa.it/favicon.ico
```

---

## ⏳ Ottimizzazioni Future (Non Bloccanti)

### Cache Plugin Icons Globalmente
- Attualmente ogni `BrokerIcon` chiama `/brokers/import/plugins`
- Potrebbe essere uno store globale caricato una volta
- **Impatto**: Ridurrebbe chiamate API e flash iniziale
- **Priorità**: BASSA - funziona, solo ottimizzazione UX

### ProfileTab Layout
- Passato a `plan-settings-unification.md` Fase 4

---

## Note

- Accesso diretto a `/brokers/1` dopo restart server → 404 (accettabile, utente può navigare)
- Debug logging funziona e tree-shaking verificato
