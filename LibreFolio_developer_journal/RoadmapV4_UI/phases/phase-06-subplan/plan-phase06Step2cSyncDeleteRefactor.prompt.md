# Step 2c — Asset Sync Modal + Bulk Delete + Backend Convergence + Refactoring

**Obiettivo**: Creare `AssetSyncModal.svelte` (pattern `FxSyncModal`), migliorare la bulk delete con `ConfirmModal` + lista items, evolvere `FARefreshResult` nel backend per allinearla a `FXSyncPairResult` (aggiungendo `status`, `provider_used`, `elapsed_ms`, `message`, `errors: List[str]`), creare un componente padre generico `SyncModalBase.svelte` con specializzazioni FX/Asset, rinominare `fxSync.ts` → `providerHelpers.ts`, fattorizzare layout responsive e utility sync in helper condivisi.

**Durata stimata**: ~1.5 giorni

---

## Step A — Evoluzione Backend: convergenza `FARefreshResult` ↔ `FXSyncPairResult`

### ✅ COMPLETATO

- [x] `SyncStatus(str, Enum)` condiviso FA/FX creato in `refresh.py`
- [x] `FXSyncStatus` alias di `SyncStatus` (backward compat)
- [x] `FARefreshResult` arricchito: `status`, `provider_used`, `points_fetched`, `points_changed`, `message`, `elapsed_ms`
- [x] `FXSyncPairResult` ha ora `errors: List[str]`
- [x] `FABulkRefreshResponse` ha `date_range` e `total_points_changed`
- [x] `fx.py`: tutti `FXSyncStatus` → `SyncStatus`, `errors` aggiunto nei 3 FAILED
- [x] Test aggiornati (`fetched_count` → `points_fetched`)
- [x] `./dev.py api sync` completato
- [x] All tests pass (9/10 — vedi bug conteggio G9)

### ⚠️ PENDENTE G1: Bug session concorrente `bulk_refresh_prices`

**Problema**: `_process_single()` usa `asyncio.gather` con la STESSA `session` per tutti gli asset.
Quando il frontend invia N asset in un unico bulk request, i task concorrenti tentano `commit()` simultaneamente → "This transaction is closed".

**Causa root**: il vecchio UI (`handleSyncAllAssets`) faceva sync sequenziale (uno alla volta), quindi non triggerava mai il bug. Con `AssetSyncModal` tutti gli asset vengono inviati in un solo bulk POST.

**Fix proposto**: Creare una session dedicata per ogni `_process_single` (pattern identico a FX `_process_route` che usa `AsyncSession(get_async_engine(), expire_on_commit=False)`).

### ⚠️ PENDENTE G2: FX `errors` nelle catene multi-provider

Il campo `errors` è stato aggiunto solo nei 3 casi FAILED espliciti. Nelle catene multi-step, se un leg fallisce, l'errore finisce in `message` ma non in `errors`. Inoltre `message` e `errors[0]` sono identici nei casi FAILED (ridondanza).

**Fix proposto**:
- FAILED: `message` = summary human-readable, `errors` = lista errori tecnici (senza duplicare)
- OK/PARTIAL con leg errors: popolare `errors` dai `leg_errors` raccolti, `message` resta la nota
- Eliminare la ridondanza `message == errors[0]`

---

## Step B — Componente padre generico `SyncModalBase.svelte` + specializzazioni

### ✅ COMPLETATO

- [x] `SyncModalBase.svelte` creato con logica generica (countdown, retry, progress, risultati via snippet)
- [x] `FxSyncModal.svelte` riscritto come thin wrapper (doSyncFn + resultRow snippet)
- [x] `AssetSyncModal.svelte` creato come wrapper analogo

### ⚠️ PENDENTE G4: Icona provider in Asset sync modal

L'utente vuole vedere le icone dei provider anche nei risultati asset (come FX mostra le icone ECB/FED).
Bisogna usare `getProviderIconUrl()` per gli asset provider (yfinance, cssscraper, justetf, etc.).

---

## Step C — Collegamento modali in `assets/+page.svelte`

### ✅ COMPLETATO

- [x] `syncModalOpen` / `syncModalAssets` state aggiunti
- [x] "Sync All" → apre `AssetSyncModal` (non più sync sequenziale)
- [x] Bulk sync toolbar → apre `AssetSyncModal`
- [x] Codice morto rimosso (`syncAllLoading`, `bulkSyncLoading`, `handleSyncAllAssets` vecchio)
- [x] `<AssetSyncModal>` aggiunto nel template

### ⚠️ PENDENTE G3: Bottone "Sync All" — rotazione durante sync

Il bottone "Sync All" in assets ha perso `animate-spin` e `disabled` perché ora apre la modale.
L'utente vuole che il bottone giri finché la modale è aperta e sta sincronizzando.
**Proposta**: `disabled={syncModalOpen}`, icona spin `class={syncModalOpen ? 'animate-spin' : ''}`.
Stessa logica va applicata anche in FX per coerenza.

### ⚠️ PENDENTE G3b: Tutti i bottoni RotateCw collegati a sync devono avere spin

Cercare tutti i `RotateCw` nel progetto collegati a operazioni sync e verificare che abbiano `animate-spin` durante l'operazione.

---

## Step D — Bulk delete migliorata (pattern FX con ConfirmModal + lista)

### ✅ COMPLETATO

- [x] `bulkDeleteDialogOpen` / `deletingAssets` state aggiunti
- [x] `handleBulkDeleteAssets()` mostra `ConfirmModal` con lista nomi
- [x] `confirmBulkDeleteAssets()` esegue la delete
- [x] `<ConfirmModal>` bulk delete aggiunto nel template

### ⚠️ PENDENTE G5: Accapo nel messaggio di conferma delete singola

Messaggio attuale (una riga): `Eliminare "Ethereum"? Assegnazioni provider e storico prezzi verranno rimossi.`

L'utente vuole:
```
Eliminare "Ethereum"?
Assegnazioni provider e storico prezzi verranno rimossi. ⚠️
```

**Fix**: Spezzare la chiave i18n `assets.delete.confirmMessage` in due parti (titolo + body) oppure usare `\n` nel messaggio e adattare il rendering di `ConfirmModal` per supportare newline.

### ⚠️ PENDENTE G6: Visualizzazione fallimenti bulk delete

Attualmente: se la delete bulk fallisce (asset con transazioni), il toast mostra solo il conteggio.
L'utente vuole vedere il dettaglio di TUTTI i fallimenti, non solo il numero.

**Proposta**: Dopo il `confirmBulkDeleteAssets()`, se ci sono fallimenti:
- Mostrare i risultati nella modale stessa (non chiuderla subito)
- Lista con ✅ deleted / ❌ "has transactions" per ogni asset
- Toast riassuntivo solo alla chiusura

### ⚠️ PENDENTE G7: Delete singola — toast errore mostra ID, non nome

Il backend risponde `"Cannot delete asset 9: has existing transactions"`. Il toast mostra questo messaggio raw con l'ID.
**Fix**: Intercettare il messaggio nel frontend e sostituire l'ID con il nome dell'asset. Tradurre il messaggio.

### ⚠️ PENDENTE G8: TODO_FUTURI — Link transazioni nel toast errore

Quando si tenta di eliminare un asset con transazioni, il toast/messaggio deve avere un link alla tabella transazioni filtrata per quell'asset (visibilità solo broker propri). Da implementare in Phase 7 quando esiste la pagina transazioni.

---

## Step E — Fattorizzazione frontend (deduplicazione FX ↔ Asset)

### ✅ COMPLETATO

- [x] `syncHelpers.ts` creato (SyncResult, SyncStatus, STATUS_ICONS, STATUS_COLORS, formatElapsed, formatTime)
- [x] `fxSync.ts` → `providerHelpers.ts` (rinomina + aggiornamento 4 import)
- [x] `responsiveLayout.svelte.ts` creato (createResponsiveLayout)
- [x] `fx/+page.svelte` e `assets/+page.svelte` rifattorizzati per usare `createResponsiveLayout`

---

## Step F — Chiavi i18n

### ✅ COMPLETATO

- [x] `assets.sync.modalTitle` — "Sync Asset Prices"
- [x] `assets.sync.modalDescription` — "Synchronize prices from configured providers..."
- [x] `assets.sync.assetsCount` — "assets"
- [x] `assets.sync.noProvider` — "No provider assigned"
- [x] `assets.sync.currentValueOnly` — "Current value only (no history)"
- [x] `assets.delete.bulkConfirmMessage` — "Delete {count} assets?..."

### ⚠️ PENDENTE G5b: Chiave delete singola con accapo + ⚠️

Aggiornare `assets.delete.confirmMessage` per supportare il formato su due righe con ⚠️.

### ⚠️ PENDENTE G7b: Traduzione messaggio errore delete con transazioni

Nuova chiave: `assets.delete.hasTransactions` — "Cannot delete \"{name}\": has existing transactions"

---

## 🐛 Bug Trovati (Non correlati al piano)

### ⚠️ PENDENTE G9: `dev.py test all` mostra 9/10 ma tutti PASS

**Causa**: Le categorie `utils` e `front-utility` hanno entrambe `name: "All Utility Tests"`.
Il summary usa un `dict` con il nome come chiave → il secondo sovrascrive il primo → 9 chiavi uniche su 10 test.

**Fix**: Rinominare `front-utility` in `"All Frontend Utility Tests"` nel `TEST_REGISTRY`.

---

## 📋 Step G — Fix Post-Review

Task da implementare per risolvere tutti i punti pendenti:

### G1. Fix critico: session concorrente in `bulk_refresh_prices`
- Creare session dedicata per ogni `_process_single` (pattern FX `_process_route`)
- Testare con bulk request di 7+ asset

### G2. FX errors nelle catene
- Popolare `errors` dai `leg_errors` nei casi PARTIAL/FAILED catena
- Eliminare ridondanza `message == errors[0]`: FAILED → `message` = summary, `errors` = dettagli tecnici

### G3. Bottone Sync All con spin + disabled
- Assets: `disabled={syncModalOpen}`, `class={syncModalOpen ? 'animate-spin' : ''}`
- FX: stessa logica per coerenza
- Verificare tutti i `RotateCw` collegati a sync nel progetto

### G4. Provider icon nel risultato asset sync
- Usare `getProviderIconUrl(pr.provider_used)` in `AssetSyncModal` resultRow
- Mostrare icona se disponibile, altrimenti text badge (già implementato, serve solo icon lookup)

### G5. Delete singola — accapo nel messaggio di conferma
- Chiave i18n: prima parte = domanda con nome, seconda parte = warning con ⚠️
- Adattare `ConfirmModal` per supportare newline o usare due props separate

### G6. Bulk delete — mostrare risultati nella modale
- Non chiudere la modale al termine
- Mostrare lista ✅ deleted / ❌ has transactions per ogni asset
- Toast solo riassuntivo alla chiusura

### G7. Delete singola — toast con nome invece di ID
- Intercettare il messaggio backend e sostituire l'ID con `deletingAsset.display_name`
- Nuova chiave i18n per messaggio tradotto `assets.delete.hasTransactions`

### G8. TODO_FUTURI — Link transazioni
- Aggiungere nota in `TODO_FUTURI.md` per Phase 7

### G9. dev.py test count fix
- Rinominare `"All Utility Tests"` → `"All Frontend Utility Tests"` per `front-utility`

---

## Ordine di Esecuzione Step G

```
G1 (fix session — CRITICO, senza questo nulla funziona)
 │
G9 (dev.py — fix cosmetico rapido)
 │
G2 (FX errors catene)
 │
G3 (Sync All spin) + G4 (provider icon)
 │
G5 (accapo delete) + G6 (bulk delete risultati) + G7 (toast nome)
 │
G8 (TODO_FUTURI nota)
```

---

## Verifiche Finali

- [ ] `npm run build` — senza errori
- [ ] `./dev.py front check` — 0 errors, 0 warnings
- [ ] `./dev.py test all` — 10/10
- [ ] Asset sync bulk (7 asset) — tutti OK/PARTIAL, nessun "transaction closed"
- [ ] FX sync — funziona come prima
- [ ] Delete singola asset con transazioni — toast con nome, non ID
- [ ] Delete bulk con mix successo/fallimento — modale mostra dettaglio
