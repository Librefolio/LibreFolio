# Plan: Phase 06 Step 6 — Polish, Test, Documentation & Coverage

**Data creazione**: 15 Aprile 2026  
**Status**: 🚧 IN CORSO (S1 ✅, S2 ✅, S5 ✅, S3-settings ✅ · prossimo: S3-assets, S4, S6)  
**Durata stimata**: ~2 giorni  
**Dipendenze**: Step 1–4 completati, Part C (C.1–C.7) completata  
**Coverage attuale**: Backend 41.7% (via E2E frontend), Backend-only (via pytest) disponibile in `htmlcov-backend/`

---

## 1. Obiettivo

Chiudere la Phase 6 con un ciclo completo di pulizia, test e documentazione:

1. **i18n**: analisi, pulizia chiavi morte, razionalizzazione duplicati
2. **Documentazione**: verifica MkDocs aggiornata, completare pagine mancanti, tradurre
3. **E2E Test**: sviluppare test mancanti guidati da coverage frontend
4. **Backend Test**: coprire funzioni critiche scoperte, guidati da coverage backend
5. **Dead code**: eliminare codice morto nel backend e frontend
6. **Coverage report finale**: generare report combinato come baseline per Phase 7

---

## 2. Sotto-Step

### S1 — i18n: Pulizia e Razionalizzazione (~2h)

**Stato attuale**: 875 chiavi, 0 incomplete, **22 unused** (da `./dev.py i18n audit`).

#### S1a) Rimuovere chiavi unused

Chiavi da rimuovere (confermate inutilizzate dal codice sorgente):

```bash
# Verificare ciascuna con:
./dev.py i18n search "KEY" --keys --values

# Se confermata inutilizzata:
./dev.py i18n remove "KEY" -f
```

**Candidati** (22 chiavi, verificare una per una):

| Gruppo | Chiave | Azione probabile |
|--------|--------|-----------------|
| `assetDetail` | `eventMarkers`, `syncFailed`, `syncPartial`, `syncSuccess` | Verify — potrebbe servire per sync toast |
| `assets` | `identifiers.autoFilled`, `identifiers.conflictWarning` | Verify — AssetModal potrebbe usarle |
| `assets` | `probe.*` (5 chiavi) | Remove — probe UI non è mai stata implementata |
| `assets` | `schedule.*` (5 chiavi) | Verify — ScheduledInvestment form potrebbe usarle |
| `fx` | `sync.toastOk`, `sync.toastPartial`, `sync.toastSkipped` | Verify — SyncModalBase o syncToastHelpers |
| `settings` | `removeAvatarMessage`, `removeAvatarTitle` | Verify — settings modal |
| `uploads` | `removeImage` | Verify — ImagePickerWrapper |

#### S1b) Cercare chiavi duplicate/simili

Per l'analisi dei duplicati abbiamo un flag dedicato nel comando audit:

```bash
# Analisi duplicati automatica (trova chiavi con lo stesso valore, case-insensitive)
./dev.py i18n audit --duplicates

# Per output dettagliato in formato report:
./dev.py i18n audit --duplicates --format md -o i18n-duplicates-report.md
```

> 📋 **Piano di rientro duplicati**: il dettaglio completo di 60 gruppi analizzati, con
> 5 batch di consolidazione e lista dei ~30 gruppi accettabili, è in
> **[plan-phase06Step6-i18n-dedup.prompt.md](plan-phase06Step6-i18n-dedup.prompt.md)**.
> Impatto stimato: 843 → ~813 chiavi, 60 → ~30 gruppi duplicati.

Consolidare chiavi con valori identici sotto `common.*` quando ha senso.

#### S1c) Verificare namespace consistency

Pattern atteso: `{feature}.{section}.{key}` — verificare che tutte le chiavi seguano la convenzione.

#### Tasks S1

- [x] Verificare le 22 chiavi unused una per una → **tutte rimosse** (875→845)
- [x] Rimuovere quelle confermate inutili → **+2 rimosse** (`uploads.imageSize`, `uploads.maxSize`) → 843
- [x] Eseguire [plan-phase06Step6-i18n-dedup.prompt.md](plan-phase06Step6-i18n-dedup.prompt.md) → **completato** (875→825, 60→42 gruppi)
- [x] Verificare consistenza namespace → **26 namespace, 0 orphan, 8 deep keys (tutti giustificati)**

---

### S2 — Documentazione MkDocs: Verifica e Completamento (~3h)

> **Nota sulle traduzioni**: le pagine MkDocs sono state tradotte ~3 giorni fa con la
> pipeline Aphra e abbiamo già verificato che le traduzioni siano consistenti.
> Quello che resta da fare ora è verificare che le **parti inglesi** siano ancora
> coerenti con le modifiche fatte dopo la traduzione (Part C soprattutto).
>
> **Strategia di aggiornamento traduzioni**:
> - Se le modifiche riguardano **pochi file con diff mirate** → aggiorniamo manualmente
>   sia il file EN che tutte le traduzioni associate (IT/FR/ES)
> - Se le modifiche iniziano a essere numerose → lavoriamo **solo sulla parte inglese**
>   e poi lanciamo la pipeline Aphra con `--force` per rigenerare da zero i file tradotti

#### S2a) Migliorare il Glossary multilingua

Il glossary MkDocs (`mkdocs_src/docs/glossary*.md`) è il punto di riferimento per la
terminologia di dominio in tutte le lingue. In vista di un'**espansione linguistica del
modello** (aggiunta di nuove lingue oltre EN/IT/FR/ES), questo è il momento migliore per
rafforzarlo: stiamo già rileggendo tutte le pagine, quindi possiamo intercettare termini
mancanti e cementificare lo stato attuale della nomenclatura.

**Obiettivi**:
- Aggiungere al glossary tutti i termini tecnici/di dominio introdotti nella Phase 6
  (e.g. *scheduled investment*, *asset provider*, *price sync*, *bulk assign*,
  *currency conversion*, *OHLCV*, *classification*, *geographic breakdown*, ecc.)
- Verificare che ogni termine abbia una definizione coerente in **tutte e 4 le lingue**
- Uniformare l'uso dei termini nelle pagine docs (evitare sinonimi non registrati)
- Produrre un glossary "solido" che possa fungere da **reference automatico** per la
  pipeline Aphra quando tradurrà nuove lingue (il glossary viene passato come contesto
  al modello LLM)

```bash
# Verificare lo stato attuale del glossary
cat mkdocs_src/docs/glossary.en.md | wc -l

# Cercare termini introdotti nella Phase 6 non ancora nel glossary
grep -r "scheduled investment\|bulk assign\|price sync\|OHLCV\|classification" \
  mkdocs_src/docs/ --include="*.en.md" -l
```

#### S2b) Verifica pagine user-facing per Assets

Le pagine utente per gli asset sono già create (14 file EN + 42 traduzioni IT/FR/ES). Verificare che siano aggiornate con le ultime modifiche:

| Pagina | Stato da verificare |
|--------|-------------------|
| `assets/index.en.md` | Lista asset: grid/table toggle, filtri, Δ multi-periodo |
| `assets/create-edit.en.md` | Smart search, auto-fill, auto-assign provider |
| `assets/detail/chart.en.md` | PriceChartFull, currency conversion toggle |
| `assets/detail/signals.en.md` | EMA, MACD, RSI, Bollinger, AssetComparison |
| `assets/detail/data-editor.en.md` | OHLCV editor, CSV import |
| `assets/detail/classification.en.md` | Classification params, geographic breakdown |
| `assets/detail/events.en.md` | Events panel, banner "data available from" |
| `assets/detail/measures.en.md` | Measure panel (abs+%, dual currency) |
| `assets/providers/*.en.md` | Yahoo Finance, JustETF, CSS Scraper, Scheduled Investment |

#### S2c) Verifica pagine developer

| Area | Pagina | Da verificare |
|------|--------|--------------|
| Architecture | `patterns/asset_plugin_guide.md` | Provider params_schema, thread isolation |
| Architecture | `patterns/async.md` | `_run_provider_in_thread()`, event loop blocking fix |
| Backend | `assets/architecture.md` | Cache system (NamedCache), bulk operations |
| Frontend | `components/live-ticker.md` | JustETF SSE live ticker |
| Test | `test-walkthrough/index.md` | Coverage section (✅ già aggiornata) |
| Test | `test-walkthrough/front-overview.md` | --coverage flag (✅ già aggiornata) |

#### S2d) Verificare link docs

```bash
./dev.py mkdocs build 2>&1 | grep -i "warning\|error"
```

#### S2e) Tradurre pagine nuove/modificate

Se le modifiche EN sono poche e mirate, aggiornare manualmente le traduzioni:

```bash
# Verificare quali file EN sono cambiati rispetto alle traduzioni esistenti
./dev.py mkdocs translate-diff

# Se pochi file: aggiornare manualmente IT/FR/ES per ciascun file toccato
# Se molti file: lavorare solo EN e poi rigenerare da zero con Aphra:
./dev.py mkdocs translate --lang it,fr,es --force   # riscrive completamente

# Validare il risultato in entrambi i casi
./dev.py mkdocs translate-validate
```

#### Tasks S2

- [x] Arricchire il glossary multilingua con i termini Phase 6 (EN + IT/FR/ES) → **27→49 termini**
- [x] Review tutte le pagine user-facing per Assets (9 file EN) → **tutte allineate**
- [x] Review pagine developer chiave (5 file) → **tutte allineate**
- [x] `./dev.py mkdocs build` senza warning → **0 warning**
- [x] Tradurre pagine modificate in IT/FR/ES → **4 pagine tradotte**
- [x] `./dev.py mkdocs translate-validate` → **210 errori pre-esistenti** (LaTeX/code-block in financial-theory, non causati da Step 6)

---

### S3 — E2E Test Frontend: Sviluppo Guidato da Coverage (~4h)

**Coverage attuale**: `htmlcov-frontend/` mostra quali endpoint backend sono esercitati dai test E2E.

> **Nota**: durante l'analisi della coverage potrebbe emergere che anche **sottosistemi
> più vecchi** (brokers, settings, auth, ecc.) hanno coverage parziale. Non ci
> formalizziamo: se troviamo gap significativi sviluppiamo i test necessari anche
> per quei moduli, non solo per gli asset. L'obiettivo è avere una coverage E2E
> solida su tutto il frontend, non solo sulle feature nuove.

#### S3a) Analisi coverage per identificare gap

```bash
# Report coverage frontend attuale
./dev.py test coverage show frontend

# Funzioni scoperte ad alta priorità
./dev.py test coverage-report --priority high
```

**Aree con bassa coverage E2E da migliorare:**

| Spec file | Test attuali | Gap identificati |
|-----------|-------------|-----------------|
| `asset-list.spec.ts` | 9 test | Table view, filtri type/currency, Δ multi-periodo |
| `asset-detail.spec.ts` | 12 test | Provider assignment, sync, currency conversion toggle |
| `asset-modal.spec.ts` | 6 test | Smart search con risultati, auto-fill, edit mode |
| `asset-data-editor.spec.ts` | 23 test | CSV import con file reale, OHLCV validation |

#### S3b) Nuovi test da sviluppare

**Asset List (estendere `asset-list.spec.ts`)**:
- [ ] Table view: visibilità colonne, sorting
- [ ] Toggle grid ↔ table persiste refresh
- [ ] Filtro per type (ETF, STOCK, etc.)
- [ ] Filtro per currency
- [ ] Filtro active/all
- [ ] Empty state senza filtri match

**Asset Detail (estendere `asset-detail.spec.ts`)**:
- [ ] Provider assignment section visible
- [ ] Sync button disabled senza provider
- [ ] Currency conversion toggle (se provider ha diversa currency)
- [ ] Chart signals panel (add EMA, remove)
- [ ] Measure panel click-to-measure

**Asset Modal (estendere `asset-modal.spec.ts`)**:
- [ ] Smart search trova risultati
- [ ] Auto-fill from search result
- [ ] Edit mode pre-populates fields
- [ ] Validation: empty display_name blocked

**FX Tests (da verificare)**:
- [ ] `fx-list.spec.ts`: table view (se aggiunta)
- [ ] `fx-sync.spec.ts`: sync con toast feedback

**Sottosistemi legacy (se emergono gap significativi)**:
- [ ] `brokers.spec.ts`: CRUD completo, sharing, icon upload
- [ ] `settings.spec.ts`: profilo, avatar, preferenze
- [ ] `auth.spec.ts`: login/logout, session expiry
- [ ] `multi-user.spec.ts`: permessi viewer vs admin
- [ ] Altri spec file esistenti con coverage < 50%

**Settings — GlobalSettingsTab (gap emerso da S5d)**:
> I 29 test `settings.spec.ts` esistenti confermano rendering e zero regressioni, ma
> **non testano l'interazione con SettingToggle/SettingNumber** nel tab Admin. Gap:
- [x] Admin toggle: unlock → click toggle bool → value cambia → save → reload conferma → **fatto** (toggle change + save/undo visible)
- [x] Admin number: unlock → modifica campo numerico → undo → valore torna originale → **fatto**
- [x] Admin undo su toggle: toggle → undo → valore torna originale → **fatto**
- [x] Non-admin: verificare che toggle/number sono read-only (no click effect) → **fatto**
- [x] Lock/unlock: toggles e number inputs disabilitati quando locked → **fatto**
> **Risultato**: 29→37 test (+8), tutti passano in 53s

#### S3c) Gallery screenshot

```bash
./dev.py mkdocs gallery
```

Verificare che la gallery includa:
- [ ] Asset list (grid view, light+dark)
- [ ] Asset list (table view, light+dark)
- [ ] Asset detail (chart con signals)
- [ ] Asset modal (search + form)
- [ ] FX list (table view — se implementata)

#### Tasks S3

- [ ] Analizzare `htmlcov-frontend/` per identificare endpoint non coperti
- [ ] Sviluppare 6-10 nuovi test per `asset-list.spec.ts`
- [ ] Sviluppare 4-6 nuovi test per `asset-detail.spec.ts`
- [ ] Sviluppare 3-4 nuovi test per `asset-modal.spec.ts`
- [ ] Se emergono gap in sottosistemi legacy, sviluppare test anche per quelli
- [ ] Verificare/aggiornare gallery screenshot
- [ ] Rieseguire `./dev.py test --coverage all-frontend` per coverage aggiornata

---

### S4 — Backend Test: Coprire Funzioni Critiche (~3h)

**Coverage attuale**: `htmlcov-backend/` mostra coverage da pytest.

#### S4a) Analisi funzioni scoperte

```bash
./dev.py test coverage-report --priority high --summary
```

**File backend con bassa coverage (priorità alta)**:

| File | Coverage | Funzioni critiche scoperte |
|------|----------|---------------------------|
| `asset_source.py` | ~19% via E2E | `get_current_prices_bulk`, `bulk_sync_prices`, `bulk_assign_providers` |
| `broker_service.py` | ~55% | `create_broker`, `update_broker`, sharing logic |
| `fx.py` | ~11% | `sync_pairs_bulk`, `convert_currencies` |
| `transaction_service.py` | ~16% | FIFO matching, transaction CRUD |
| `brim_provider.py` | ~19% | Plugin dispatch, file parsing |

#### S4b) Nuovi test backend da sviluppare

Prioritizzare funzioni che:
1. Sono usate dal frontend ma non testate unitariamente
2. Hanno logica complessa (cache, bulk operations, thread isolation)
3. Sono state modificate nel Part C (currency conversion, cache)

**Candidati per nuovi test:**

- [ ] `test_asset_source_bulk_ops.py`: test `get_current_prices_bulk` con cache hit/miss
- [ ] `test_broker_service_crud.py`: test create/update/delete con sharing
- [ ] Estendere `test_fx_core.py`: test `sync_pairs_bulk` edge cases
- [ ] Verificare test esistenti passano: `./dev.py test all-backend`

#### Tasks S4

- [ ] `./dev.py test coverage-report --priority high` per lista funzioni
- [ ] Sviluppare 2-3 nuovi file test per funzioni ad alta priorità
- [ ] Rieseguire `./dev.py test --coverage all-backend` per coverage aggiornata
- [ ] Rieseguire `./dev.py test --coverage all` per report combinato

---

### S5 — Dead Code Analysis (~1h)

#### S5a) Backend dead code

```bash
# Analisi con coverage-report
./dev.py test coverage-report --priority high

# Cercare funzioni mai chiamate
grep -rn "def " backend/app/services/ --include="*.py" | wc -l
```

Confrontare con coverage: funzioni con 0% coverage E2E + 0% coverage backend = dead code candidato.

**Aree sospette:**
- ~~`sitecustomize.py`~~ — **rimosso** (vecchio approccio coverage, sostituito da `coverage run`)
- Funzioni `_legacy_*` in servizi
- Import inutilizzati (verificare con `ruff`)

#### S5b) Frontend dead code

```bash
# Svelte check per export inutilizzati
cd frontend && npx svelte-check 2>&1 | grep -i "unused"

# Componenti mai importati
grep -rL "import.*from" frontend/src/lib/components/ --include="*.svelte" | head -20
```

#### S5c) Lint e format — Migrazione a tool standard

Finora lint e format sono stati gestiti dall'IDE PyCharm. È il momento di passare a una
configurazione **standard e riproducibile** (ruff/black per Python, eslint/prettier per
frontend), ma le regole vanno calibrate **insieme** per mantenere lo stile attuale.

**Approccio collaborativo**:
1. Generare la config iniziale (ruff, black, eslint, prettier)
2. Eseguire un dry-run per vedere i cambiamenti proposti
3. Rivedere insieme le diff e aggiustare le regole fino ad avere output ~identico allo stile attuale
4. Solo dopo aver concordato le regole, applicare la formattazione

```bash
# Backend: ruff (lint) + black (format) — config in pyproject.toml
./dev.py lint    # ruff check
./dev.py format  # black

# Frontend: svelte-check + (futuro: eslint + prettier)
cd frontend && npm run check  # svelte-check

# Dry-run per vedere l'impatto senza modificare
ruff check backend/ --diff
black backend/ --diff
```

> ⚠️ **Non applicare format automatici prima di aver concordato le regole.**
> Le regole di formattazione vanno calibrate per ottenere un aspetto simile
> a quello attuale del codice.

#### S5d) Ricreazione SettingToggle / SettingNumber + Refactoring GlobalSettingsTab

Nella pulizia dead code (S5b), 7 componenti Svelte stub/inutilizzati sono stati rimossi.
Tra questi, `SettingNumber.svelte` e `SettingToggle.svelte` erano stati estratti da
`GlobalSettingsTab` per renderli riutilizzabili in futuro (UserSettingsTab), ma non erano
mai stati collegati. Sono stati ricreati in Svelte 5 e `GlobalSettingsTab` è stato
refactored per usarli come componenti self-contained:

**Componenti ricreati** (Svelte 5, stessa API di `SettingSelect`):
- `SettingToggle.svelte` — toggle booleano con label, hint, icon, azioni inline
- `SettingNumber.svelte` — input numerico con type int/float, unit, warnAbove, azioni inline

**GlobalSettingsTab refactoring**:
- Template ristrutturato: `bool` → `<SettingToggle>`, `int`/`float` → `<SettingNumber>`
- Eliminati 5 blocchi duplicati di action buttons inline (−60 righe, 787→727)
- Rimosso dead code script: `fileSizeUnit`, `fileSizeDisplayValue`, import `AlertCircle`
- Aggiunta helper `getSettingHint()` per ridurre ripetizione template
- Conversione string↔boolean gestita via callback `onchange`

**Dead code correlato rimosso**:
- `CandlestickChart.svelte`, `VolumeBar.svelte` → spostati in `TODO_FUTURI.md`
- `SettingField.svelte`, `SettingText.svelte` (Svelte 4, pattern superato)
- `ImageUploader.svelte` (sostituito da pipeline ImagePicker)
- Barrel exports aggiornati: `charts/index.ts`, `ui/media/index.ts`
- 2 TODO completati spostati da `TODO_FUTURI.md` → `TODO_Completati.md`

**Verifica**:
- `svelte-check`: 0 errori
- `./dev.py test front-utility settings`: **29 test passed** (45.2s)
  - I test coprono rendering GlobalSettingsTab (admin + non-admin), tab switching,
    preferenze persistence, profilo lock/unlock/undo. Confermano zero regressioni
    sul refactoring. Test specifici per interazione toggle/number da sviluppare in S3.

#### Tasks S5

- [x] Analizzare dead code backend (funzioni 0% coverage) → **1 trovata**: `_detect_separator` in `brim_provider.py` (mai chiamata, rimossa)
- [x] Verificare se `sitecustomize.py` è ancora necessario → **rimosso**
- [x] Analizzare dead code frontend (componenti non importati) → **7 componenti rimossi**
- [x] Ricreare SettingToggle/SettingNumber, refactoring GlobalSettingsTab → **29 test passed**
- [x] Spostare TODO completati da `TODO_FUTURI.md` → `TODO_Completati.md`
- [ ] Concordare regole lint/format (dry-run → review diff → calibrare config)
- [ ] Applicare lint/format solo dopo aver concordato le regole
- [x] `svelte-check` senza errori → **0 errori**

---

### S6 — Coverage Report Finale e Wrap-up (~30min)

#### S6a) Report combinato

```bash
# Eseguire tutti i test con coverage
./dev.py test --coverage --cov-clean-backend --cov-clean-frontend all

# Oppure separatamente
./dev.py test --coverage --cov-clean-backend all-backend
./dev.py test --coverage --cov-clean-frontend all-frontend
./dev.py test coverage show combined
```

#### S6b) Salvare baseline

Documentare i numeri di coverage come baseline per Phase 7:

| Metrica | Target Phase 6 |
|---------|---------------|
| Backend (pytest) | > 60% |
| Backend (E2E frontend) | > 45% |
| Combinato | > 65% |
| i18n unused keys | 0 |
| MkDocs warnings | 0 |
| ruff/black violations | 0 |

#### S6c) Aggiornare status

- [ ] Aggiornare `plan-phase06-assets.md` → Step 6: ✅
- [ ] Aggiornare `plan-phase06Assets.prompt.md` → Status: ✅ COMPLETATA
- [ ] Aggiornare `phases/phase-06-assets.md` → Status: ✅
- [ ] Aggiornare `00_project_overview.md` → Phase 6: ✅

---

## 3. Strumenti Disponibili (da `dev.py`)

| Operazione | Comando |
|-----------|---------|
| Audit i18n (chiavi/valori/unused) | `./dev.py i18n audit` |
| Audit duplicati i18n | `./dev.py i18n audit --duplicates [--format md\|xlsx\|both]` |
| Rimuovere chiave i18n | `./dev.py i18n remove KEY -f` |
| Cercare chiave/valore | `./dev.py i18n search QUERY -k -v` |
| Albero chiavi | `./dev.py i18n tree [PREFIX] --counts` |
| Build docs + check link | `./dev.py mkdocs build` |
| Diff traduzioni docs | `./dev.py mkdocs translate-diff` |
| Tradurre docs | `./dev.py mkdocs translate` |
| Validare traduzioni | `./dev.py mkdocs translate-validate` |
| Test frontend con coverage | `./dev.py test --coverage all-frontend` |
| Test backend con coverage | `./dev.py test --coverage all-backend` |
| Report funzioni scoperte | `./dev.py test coverage-report --priority high` |
| Visualizzare coverage HTML | `./dev.py test coverage show [backend\|frontend\|combined]` |
| Gallery screenshot | `./dev.py mkdocs gallery` |
| Lint backend | `./dev.py lint` |
| Format backend | `./dev.py format` |
| Svelte check | `cd frontend && npm run check` |

---

## 5. Checkpoint — Stato al 15 Aprile 2026

> Sezione aggiunta per facilitare il recovery del contesto tra sessioni.

### ✅ Completati

| Step | Dettaglio |
|------|-----------|
| **S1 — i18n** | 875→825 chiavi. 22 unused rimossi, 50 duplicati consolidati sotto `common.*`, 42 gruppi duplicati accettati. 26 namespace, 0 orphan. Piano dedup in `plan-phase06Step6-i18n-dedup.prompt.md`, strategia documentata in `knowledge_base/08_i18n_duplicates.md`. |
| **S2 — Docs** | Glossario Aphra 27→49 termini. Tutte le pagine user-facing (14) e developer (5) verificate e allineate. `mkdocs build` 0 warning. 4 pagine tradotte (IT/FR/ES). `translate-validate` ha 210 errori pre-esistenti (LaTeX/code-block nelle pagine financial-theory, non causati da Step 6). Bugfix: `check_admonition_indent` in `validate_translations.py` (needs_source=True). |
| **S5 — Dead code** | **Frontend**: 7 componenti rimossi (CandlestickChart, VolumeBar, SettingField, SettingText, ImageUploader + 2 SettingNumber/Toggle originali). Barrel exports aggiornati. SettingToggle + SettingNumber ricreati in Svelte 5. GlobalSettingsTab refactored per usarli (−60 righe, 787→727). Dead code script rimosso (fileSizeUnit, fileSizeDisplayValue, AlertCircle import). **Backend**: `_detect_separator` in `brim_provider.py` (mai usata, ogni plugin BRIM ha separatore hardcoded). `svelte-check` 0 errori. |
| **S3-settings** | 29→37 test E2E settings (+8 nuovi). Test coprono: admin unlock/lock, SettingToggle click+value change, save/undo button visibility, undo revert, SettingNumber edit+undo, disabled when locked, non-admin read-only. Tutti passano in 53s. |
| **Housekeeping** | 2 TODO completati spostati da `TODO_FUTURI.md` → `TODO_Completati.md`. CandlestickChart/VolumeBar aggiunti a `TODO_FUTURI.md`. |

### ⏳ Da fare

| Step | Cosa resta |
|------|-----------|
| **S3 — E2E assets** | Test per `asset-list.spec.ts` (table view, filtri), `asset-detail.spec.ts` (provider, sync, currency toggle), `asset-modal.spec.ts` (smart search, auto-fill). Gallery screenshot. Vedi checklist nel piano. |
| **S4 — Backend test** | Analisi coverage con `./dev.py test coverage-report --priority high`. Test per `asset_source.py` (bulk ops), `broker_service.py` (CRUD), `fx.py` (sync_pairs_bulk). |
| **S5c — Lint/format** | Sessione collaborativa: dry-run ruff/black → review diff → calibrare regole → applicare. Non fare senza accordo sulle regole. |
| **S6 — Wrap-up** | Coverage report finale, salvare baseline, aggiornare status Phase 6 in tutti i file di piano. |

### File toccati in questa sessione (per git diff)

**Modificati**:
- `frontend/src/lib/components/settings/tabs/GlobalSettingsTab.svelte` — refactored template + cleanup script
- `frontend/src/lib/components/settings/SettingToggle.svelte` — ricreato (Svelte 5)
- `frontend/src/lib/components/settings/SettingNumber.svelte` — ricreato (Svelte 5)
- `frontend/e2e/settings.spec.ts` — +8 test per GlobalSettingsTab interaction
- `backend/app/services/brim_provider.py` — rimossa `_detect_separator`
- `mkdocs_src/aphra-pipeline/validate_translations.py` — bugfix `check_admonition_indent`
- `TODO_FUTURI.md` — rimossi 2 completati, aggiornata sezione CandlestickChart
- `TODO_Completati.md` — +2 task (i18n cleanup, late interest)
- `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase06Step6-Polish-Test-Docs.prompt.md` — aggiornato status

**NON toccati in questa sessione** (fatti nella sessione precedente, già committabili):
- `frontend/src/lib/i18n/{en,it,fr,es}.json` — 875→825 chiavi
- 14 file Svelte con key `common.*` aggiornate
- 7 componenti rimossi + barrel exports
- `sitecustomize.py` rimosso
- `knowledge_base/08_i18n_duplicates.md` — nuovo
- `plan-phase06Step6-i18n-dedup.prompt.md` — nuovo
- MkDocs: glossary, 4 pagine docs + traduzioni

---

## 4. Ordine Esecuzione Consigliato

```
S1 (i18n cleanup)     ← 2h, prerequisito per traduzione docs
    ↓
S5 (dead code)        ← 1h, semplifica i test
    ↓
S2 (docs)             ← 3h, include traduzione con chiavi pulite
    ↓
S3 (E2E test)         ← 4h, guidato da coverage
    ↓
S4 (backend test)     ← 3h, guidato da coverage
    ↓
S6 (wrap-up)          ← 30min, report finale
```

**Totale stimato**: ~13.5h (~2 giorni)

---

## Post end step

Al termine di tutto implementare il "buy me a coffee" per supportare il progetto, e poi iniziare a pianificare la Phase 7!
sia nel readme che nella home della documentazione, in tutte le lingue. Link a BuyMeACoffee, con messaggio di ringraziamento e invito a supportare il progetto se si trova utile. Posizionarlo in modo discreto ma visibile (footer docs, sidebar, ecc.).

terminale creando tag `phase-06-completed` , ricreando gli screen della gallery e deployando il 
