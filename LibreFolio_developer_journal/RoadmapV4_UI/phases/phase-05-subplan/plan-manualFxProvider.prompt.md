# Plan: MANUAL FX Provider — Sentinel Provider for Manual-Only Pairs

**Data creazione**: 4 Marzo 2026
**Status**: ✅ COMPLETATO
**Durata stimata**: ~2-3 ore
**Dipendenze**: Phase 5 FX pages funzionanti, FxPairAddModal operativa

---

## Decisioni dalla Review

- ✅ **Priorità 999** confermata come valore sentinella
- ✅ **Filtrare MANUAL da `GET /fx/providers`** — non deve apparire nel dropdown utente
- ✅ **Backend mantiene la consistenza** — il frontend manda solo la lista provider reali, il backend gestisce auto-insert/remove di MANUAL
- ✅ **Nessuna backward compatibility** — `db create-clean` e basta
- ✅ **Aggiungere coppia MANUAL in db populate** per testing

---

## Obiettivo

Creare un provider FX speciale `MANUAL` che funge da **sentinella** per le coppie senza provider automatici.

## Soluzione: Provider MANUAL

Un provider registrato nel `FXProviderRegistry` con codice `MANUAL` che:
- **Non fa nulla durante il sync** (skip silenzioso, restituisce 0 risultati)
- **Accetta qualsiasi coppia di valute**
- **È assegnato con priorità 999**
- **Gestito interamente dal backend**: insert/remove automatico

---

## Step di Implementazione

### Step 1: Creare il provider `MANUAL` (Backend)
- [x] `backend/app/services/fx_providers/manual.py` — Classe ManualProvider

### Step 2: Early-return MANUAL nel sync (Backend)
- [x] `backend/app/services/fx.py` — `ensure_rates_multi_source()`

### Step 3: Filtrare MANUAL da GET /fx/providers (Backend)
- [x] `backend/app/api/v1/fx.py` — `list_providers()`

### Step 4: Auto-gestione MANUAL nella CRUD pair-sources (Backend)
- [x] `create_pair_sources_bulk()` — Rimuovere MANUAL quando si aggiungono provider reali
- [x] `delete_pair_sources_bulk()` — Reinserire MANUAL quando nessun provider reale resta

### Step 5: Aggiornare FxPairAddModal (Frontend)
- [x] `handleSave()` — Mandare MANUAL quando nessun provider selezionato, rimuovere rate seed

### Step 6: Nascondere MANUAL dalla UI (Frontend)
- [x] FxProviderConfig — filtrare MANUAL dalla OrderableList
- [x] fx/+page.svelte — badge "Manual Only"

### Step 7: db populate — coppia MANUAL
- [x] Aggiungere NOK/SEK con MANUAL

### Step 8: Test API
- [x] Test MANUAL lifecycle completo
- [x] Fix: delete senza priority (full pair) non reinserisce MANUAL (evita loop infinito)
- [x] Test 17: verifica full pair delete
- [x] Test 18: cleanup test pairs
- [x] Fix Test 16: passare currencies specifiche (ISK,TRY) per il sync test

---

## Riepilogo File Coinvolti

| File | Azione |
|------|--------|
| `backend/app/services/fx_providers/manual.py` | **NUOVO** — Provider MANUAL |
| `backend/app/services/fx.py` | Early-return per MANUAL |
| `backend/app/api/v1/fx.py` | Auto-gestione + filtro GET |
| `backend/test_scripts/test_db/populate_mock_data.py` | Mock data |
| `backend/test_scripts/test_api/test_fx_api.py` | Test lifecycle |
| `frontend/src/lib/components/fx/FxPairAddModal.svelte` | MANUAL al posto del rate seed |
| `frontend/src/lib/components/fx/FxProviderConfig.svelte` | Filtrare MANUAL |
| `frontend/src/routes/(app)/fx/+page.svelte` | Badge "Manual Only" |
