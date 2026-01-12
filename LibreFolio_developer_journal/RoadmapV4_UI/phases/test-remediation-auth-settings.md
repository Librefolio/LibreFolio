# Remediation Plan: Backend Tests for Auth & Settings

## Stato Attuale

### Auth Tests (test_auth_api.py) - ✅ ESISTENTE

Il file esiste con 451 linee e copre:

- TestRegister: registrazione utenti
- TestLogin: login utenti
- TestLogout: logout
- TestMe: endpoint /me
- TestSessionPersistence: persistenza sessione

### Settings Tests (test_settings_api.py) - ✅ COMPLETATO

Creato file con 14 test cases:

**A. User Settings (GET/PUT /settings/user)**

- [x] SET-001: Get user settings (authenticated)
- [x] SET-002: Get user settings (unauthenticated) → 401
- [x] SET-003: Update user settings (authenticated)
- [x] SET-004: Update with invalid values → validation error

**B. Global Settings (GET /settings/global)**

- [x] GSET-001: List global settings (authenticated)
- [x] GSET-002: List global settings (unauthenticated) → 200 (public read by design)

**C. Single Global Setting (GET/PUT /settings/global/{key})**

- [x] GSET-003: Get single setting (authenticated)
- [x] GSET-004: Get non-existent setting → 404
- [x] GSET-005: Update setting as admin → success
- [x] GSET-006: Update setting as non-admin → 403
- [x] GSET-007: Update non-existent setting → 404/403

**D. Initialize Global Settings (POST /settings/global/initialize)**

- [x] GSET-008: Initialize as admin → success
- [x] GSET-009: Initialize as non-admin → 403
- [x] GSET-010: Initialize when already exists → idempotent

---

## Note Implementative

### Global Settings - Read Access Pubblico

L'endpoint `GET /settings/global` è pubblico by design:

- Il frontend deve leggere `enable_registration` prima del login
- Le impostazioni globali non sono considerate sensibili

### Test Admin-Dependent

Alcuni test richiedono utente admin. Se il DB ha già utenti, il nuovo utente non sarà admin e il test viene skippato:

- GSET-005, GSET-007, GSET-008, GSET-010

### Inizializzazione Automatica

I global settings vengono inizializzati automaticamente all'avvio del server via `lifespan` in `main.py`.

---

## Status: ✅ COMPLETATO

