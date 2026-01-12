# Piano di Rimedio - Phase 3.5 (Aggiornato)

## Stato Correzioni Frontend

| Fix                                 | Status |
|-------------------------------------|--------|
| A. Logo Proporzioni                 | ✅ DONE |
| B. Language Selector in Header      | ✅ DONE |
| C. Sidebar Collapsed                | ✅ DONE |
| D. Menu Attivo (reactive)           | ✅ DONE |
| E. Rimozione Freccetta Desktop      | ✅ DONE |
| F. Fix Barra Orizzontale (overflow) | ✅ DONE |
| G. Link Documentazione              | ✅ DONE |
| H. Global Settings Tab              | ✅ DONE |
| I. Auto-build MkDocs                | ✅ DONE |

---

## Modifiche Effettuate (Sessione Corrente)

### 1. Sidebar.svelte - Correzioni Multiple

- ✅ Rimossa freccetta chevron desktop (inutile)
- ✅ Fix menu attivo: uso `$: currentPath = $page.url.pathname` per reattività
- ✅ Aggiunto `overflow-hidden` per evitare scrollbar orizzontale
- ✅ Aggiunto link Documentazione (`/mkdocs/`) con icona BookOpen
- ✅ Key `(item.href)` nel loop per rendering corretto
- ✅ Rimosso import/uso ChevronLeft/ChevronRight

### 2. Global Settings Tab

- ✅ Creato `GlobalSettingsTab.svelte` con:
    - Lista settings globali da API
    - Pulsante Lock/Unlock per abilitare modifica
    - Salvataggio singolo setting
    - Gestione errori 403 per non-admin
- ✅ Aggiunto tab "Admin" in Settings (visibile solo superuser)
- ✅ Aggiunto `is_superuser` a `AuthUser` interface

### 3. Traduzioni

- ✅ Aggiunto `nav.documentation` in tutte le 4 lingue
- ✅ Aggiunto `settings.admin` e chiavi Global Settings in tutte le lingue:
    - globalSettings, globalSettingsDescription
    - locked, unlocked, warning, globalSettingsWarning
    - noGlobalSettings

### 4. dev.sh - Auto-build MkDocs

- ✅ Aggiunta funzione `mkdocs_needs_rebuild()`
- ✅ Aggiunta funzione `auto_build_mkdocs()`
- ✅ Integrata in `start_server()` e `start_server_test()`

---

## Backend Test Coverage

Vedere file separato: `test-remediation-auth-settings.md`

### Riassunto:

- **Auth Tests**: ✅ Esistenti (16 test, 450 linee)
- **Settings Tests**: ❌ MANCANTI - Da creare (vedere remediation plan)

---

## Build Status

| Componente            | Status                 |
|-----------------------|------------------------|
| Frontend svelte-check | ✅ 0 errors, 0 warnings |
| Frontend build        | ✅ Success              |
| Backend imports       | ✅ OK                   |

---

## Da Verificare Runtime

- [x] Click sul logo → toggle collapsed (sia mobile che desktop)
- [x] Menu item attivo si aggiorna cambiando pagina (FIX: usato reactive $: activeHref)
- [x] No scrollbar orizzontale quando collapsed
- [x] Link documentazione funziona
- [x] Tab Admin visibile a tutti (sola lettura per non-admin)
- [x] Global Settings caricati correttamente (dopo `./dev.sh user:init-settings`)
- [x] Lock/Unlock e salvataggio funzionano (solo per admin)
- [x] Tab responsive: solo icone su mobile, icone+testo su desktop

## Fix Effettuati (Ultima Sessione)

### CLI - user_cli.py promote

- ✅ Fix errore greenlet: salvato `user_id` prima di `await session.commit()` per evitare lazy load

### CLI - user_cli.py init-settings

- ✅ Aggiunto comando `init-settings` per popolare global settings con defaults
- ✅ Aggiunto in dev.sh come `./dev.sh user:init-settings`

### Settings Page - Tab Responsive

- ✅ Tab mostrano solo icone su mobile (< sm breakpoint)
- ✅ Titolo pagina visibile solo su mobile con nome tab attivo
- ✅ Su desktop mostra icone + testo come prima

### Settings Page

- ✅ Tab Admin ora visibile a tutti gli utenti
- ✅ Passato prop `canEdit={isSuperuser}` a GlobalSettingsTab
- ✅ Mostrato messaggio "Read-only" per non-admin invece di pulsante Lock

### Sidebar Menu Attivo

- ✅ Fix: sostituito funzione `isActive()` con reactive `$: activeHref`
- ✅ Il menu ora evidenzia correttamente la pagina corrente

### Traduzioni

- ✅ Aggiunto `settings.readOnlyMode` in EN, IT, FR, ES
