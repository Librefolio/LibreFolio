# Plan: Protezione Endpoint API + Gallery Skip Fix

**Data creazione**: 20 Marzo 2026
**Status**: ✅ COMPLETATO
**Priorità**: Alta (sicurezza API — endpoint sensibili attualmente pubblici)
**Stima**: ~2 ore → completato in ~30 min
**Dipendenze**: `plan-jwt-gallery-fixes.prompt.md` completato (JWT funzionante)

### Progress Log

| Data | Step | Dettagli |
|------|------|----------|
| 20 Mar 2026 | ✅ Step 1 | `fx.py`: 8 endpoint protetti (providers, sync, rates CRUD, convert, routes CRUD) |
| 20 Mar 2026 | ✅ Step 2 | `assets.py`: 15 endpoint protetti (asset CRUD, provider assign/remove/search, prices CRUD, refresh) |
| 20 Mar 2026 | ✅ Step 3 | `transactions.py`: 5 endpoint protetti (query, types, detail, update, delete — create era già protetto) |
| 20 Mar 2026 | ✅ Step 4 | `backup.py`: 4 endpoint protetti (export, restore, formats, status) |
| 20 Mar 2026 | ✅ Step 4b | `brokers.py`: 1 endpoint protetto (BRIM /plugins) |

---

## Contesto

Dopo la migrazione a JWT, molti endpoint restano pubblici (nessun `Depends(get_current_user)`).
Dati finanziari, transazioni, FX rates, backup e asset sono tutti accessibili senza login.
Bisogna proteggere tutto tranne health/system e utilities di riferimento.

### Gallery skip

Il test "mobile menu open" fa `test.skip()` quando gira nel progetto `desktop`.
Questo è **corretto e intenzionale** — è un test solo per mobile (verifica il burger menu).
Il conteggio `1 skipped` su 64 totali è il risultato atteso.
**Non serve nessun fix.**

---

## Audit endpoint: stato attuale

### ✅ Già protetti (hanno `Depends(get_current_user)`)

| Modulo | Endpoint | Metodo |
|--------|----------|--------|
| Auth | `/auth/me` | GET |
| Auth | `/auth/change-password` | POST |
| Auth | `/auth/profile` | PUT |
| Auth | `/auth/users/me` | DELETE |
| Settings | `/settings/user` | GET/PUT |
| Settings | `/settings/global` | GET |
| Settings | `/settings/global/{key}` | GET/PUT |
| Settings | `/settings/global/initialize` | POST |
| Brokers | tutti gli endpoint | POST/GET/PATCH/DELETE |
| BRIM | tutti tranne `/brim/plugins` | POST/GET/DELETE |
| Uploads | `/uploads` POST/GET, `/{id}` GET/DELETE | tutti |
| Transactions | POST (create) | POST |
| Users | `/users` | GET |

### ❌ NON protetti (da fixare)

| File | Endpoint | Metodo | Rischio |
|------|----------|--------|---------|
| **fx.py** | `GET /fx/providers` | GET | Lista provider FX |
| **fx.py** | `POST /fx/currencies/sync` | POST | **Trigger sync FX rates!** |
| **fx.py** | `POST /fx/currencies/rate` | POST | **Upsert FX rates!** |
| **fx.py** | `DELETE /fx/currencies/rate` | DELETE | **Cancella FX rates!** |
| **fx.py** | `POST /fx/currencies/convert` | POST | Converti valuta |
| **fx.py** | `GET /fx/providers/routes` | GET | Lista route conversione |
| **fx.py** | `POST /fx/providers/routes` | POST | **Crea route!** |
| **fx.py** | `DELETE /fx/providers/routes` | DELETE | **Cancella route!** |
| **assets.py** | `POST /assets` | POST | **Crea asset!** |
| **assets.py** | `PATCH /assets` | PATCH | **Modifica asset!** |
| **assets.py** | `GET /assets/all` | GET | Lista tutti gli asset |
| **assets.py** | `GET /assets/query` | GET | Query asset |
| **assets.py** | `GET /assets` | GET | Lista asset con metadata |
| **assets.py** | `DELETE /assets` | DELETE | **Cancella asset!** |
| **assets.py** | `GET /assets/provider` | GET | Lista provider |
| **assets.py** | `GET /assets/provider/search` | GET | Cerca provider |
| **assets.py** | `POST /assets/provider` | POST | **Assegna provider!** |
| **assets.py** | `DELETE /assets/provider` | DELETE | **Rimuovi provider!** |
| **assets.py** | `GET /assets/provider/assignments` | GET | Lista assegnamenti |
| **assets.py** | `POST /assets/prices` | POST | **Upsert prezzi!** |
| **assets.py** | `DELETE /assets/prices` | DELETE | **Cancella prezzi!** |
| **assets.py** | `GET /assets/prices/{id}` | GET | Prezzi asset |
| **assets.py** | `POST /assets/prices/sync` | POST | **Refresh prezzi!** |
| **assets.py** | `POST /assets/provider/search-assign` | POST | **Search+assign!** |
| **transactions.py** | `GET /transactions` | GET | **Lista transazioni!** |
| **transactions.py** | `GET /transactions/types` | GET | Metadata tipi |
| **transactions.py** | `GET /transactions/{id}` | GET | **Dettaglio transazione!** |
| **transactions.py** | `PATCH /transactions` | PATCH | **Modifica transazioni!** |
| **transactions.py** | `DELETE /transactions` | DELETE | **Cancella transazioni!** |
| **backup.py** | `POST /backup/export` | POST | **Export dati!** |
| **backup.py** | `POST /backup/restore` | POST | **Restore dati!** |
| **backup.py** | `GET /backup/formats` | GET | Lista formati |
| **backup.py** | `GET /backup/status` | GET | Status backup |
| **brokers.py** | `GET /brim/plugins` | GET | Lista plugin disponibili |

### ✅ Restano pubblici (corretto)

| File | Endpoint | Metodo | Motivazione |
|------|----------|--------|-------------|
| **auth.py** | `/auth/login` | POST | Per definizione |
| **auth.py** | `/auth/logout` | POST | Cancella solo cookie |
| **auth.py** | `/auth/register` | POST | Registrazione nuovi utenti |
| **system.py** | `/system/health` | GET | Health check (monitoring) |
| **system.py** | `/system/info` | GET | Info versione (innocuo) |
| **utilities.py** | tutti | GET | Dati di riferimento (paesi, valute, settori) |
| **uploads.py** | `/uploads/file/{id}` | GET | Serve file statico (URL opaco con UUID) |
| **uploads.py** | `/uploads/plugin/{type}/{path}` | GET | Assets dei plugin |

---

## Step 1 — Proteggere fx.py (8 endpoint)

**File**: `backend/app/api/v1/fx.py`

Aggiungere l'import e il dependency a tutti gli endpoint:
```python
from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
```

Per ogni endpoint, aggiungere `current_user: User = Depends(get_current_user)` ai parametri.
Non serve usare `current_user` nel body — il dependency fa solo da guard.

**8 endpoint** da proteggere:
1. `GET /fx/providers` (riga 90)
2. `POST /fx/currencies/sync` (riga 145)
3. `POST /fx/currencies/rate` (riga 196)
4. `DELETE /fx/currencies/rate` (riga 269)
5. `POST /fx/currencies/convert` (riga 474)
6. `GET /fx/providers/routes` (riga 593)
7. `POST /fx/providers/routes` (riga 622)
8. `DELETE /fx/providers/routes` (riga 767)

---

## Step 2 — Proteggere assets.py (15 endpoint)

**File**: `backend/app/api/v1/assets.py`

Stessa logica di Step 1. Aggiungere import e dependency.

**15 endpoint** da proteggere (CRUD asset, provider, prezzi).

---

## Step 3 — Proteggere transactions.py (4 endpoint mancanti)

**File**: `backend/app/api/v1/transactions.py`

Il POST create è già protetto. Mancano:
1. `GET /transactions` (riga 119) — query
2. `GET /transactions/types` (riga 173) — metadata tipi
3. `GET /transactions/{id}` (riga 187) — singola transazione
4. `PATCH /transactions` (riga 218) — update
5. `DELETE /transactions` (riga 255) — delete

---

## Step 4 — Proteggere backup.py (4 endpoint)

**File**: `backend/app/api/v1/backup.py`

Tutti placeholder (501), ma vanno protetti ugualmente per quando saranno implementati.

4 endpoint: export, restore, formats, status.

---

## Step 5 — Verifica

### 5A. Test che gli endpoint protetti ritornino 401 senza cookie

```bash
# Deve dare 401
curl -s http://localhost:8001/api/v1/fx/providers | head -1
curl -s http://localhost:8001/api/v1/assets | head -1
curl -s http://localhost:8001/api/v1/transactions | head -1
curl -s http://localhost:8001/api/v1/backup/status | head -1
```

### 5B. Test che funzionino con login

```bash
# Login e ottieni cookie
curl -c cookies.txt -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "e2e_test_admin", "password": "E2eAdminPass123!"}'

# Deve dare 200
curl -b cookies.txt http://localhost:8001/api/v1/fx/providers
```

### 5C. Gallery test

Tutti i test gallery usano `login(page, TEST_ADMIN)` nel `beforeEach`,
quindi non dovrebbero essere impattati. Verificare con:
```bash
./dev.py mkdocs gallery --workers 2
```

### 5D. Test API backend

```bash
pipenv run python -m pytest backend/test_scripts/test_api/ -v
```

---

## Impatto

| File | Endpoint protetti |
|------|------------------|
| `fx.py` | 8 endpoint |
| `assets.py` | 15 endpoint |
| `transactions.py` | 5 endpoint (4 nuovi + verifica 1 esistente) |
| `backup.py` | 4 endpoint |
| `brokers.py` (BRIM plugins) | 1 endpoint |
| **Totale** | **33 endpoint** |

Dopo questo piano, **tutti** gli endpoint dell'app saranno protetti
eccetto: auth (login/register/logout), system (health/info), utilities
(dati di riferimento), e serving file statici (uploads/file, uploads/plugin).

