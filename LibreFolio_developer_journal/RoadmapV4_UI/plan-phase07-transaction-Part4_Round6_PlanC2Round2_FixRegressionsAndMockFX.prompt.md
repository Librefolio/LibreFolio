# Plan: C2 Round 2 — Fix regressions + MockFX + Rimozione auto-populate + Test

**Origine**: Piano C2 Round 2 — consenso raggiunto in chat. Rimuovere l'auto-populate implicito da `bulk_assign_providers()`, creare MockFX providers per test deterministici, applicare 4 fix frontend/backend puntuali, aggiungere test backend FX fallback e E2E asset classification. Il flusso metadata diventa esclusivamente frontend-driven: probe → diff modal → PATCH esplicito.

**Link back**: `plan-phase07-transaction-Part4_Round6_PlanC2_BugfixAndPairValidation.prompt.md` (parent plan)

---

## Steps

### Step 1 — Creare Mock FX Providers ✅

**File**: `backend/app/services/fx_providers/mockfx.py` (nuovo)

Due classi, entrambe `@register_provider(FXProviderRegistry)`:

- `MockFXProvider` (code=`"MOCKFX"`): `base_currency="EUR"`, `get_supported_currencies() → ["USD","GBP","CHF","JPY"]`, `fetch_rates()` ritorna rate deterministiche con `hash(pair+date)` normalizzato a 0.5–2.0.
- `MockFXFailProvider` (code=`"MOCKFX_FAIL"`): stessa interfaccia, `fetch_rates()` sempre `raise FXServiceError("Mock failure for testing")`.

**File**: `backend/app/api/v1/fx.py` riga 105

Filtro da:
```python
providers_list = [p for p in providers_list if p["code"] != "MANUAL"]
```
A:
```python
providers_list = [p for p in providers_list if p["code"] not in ("MANUAL", "MOCKFX", "MOCKFX_FAIL")]
```

---

### Step 2 — Rimuovere auto-populate ✅ da `bulk_assign_providers()`

**File**: `backend/app/services/asset_source.py` righe 980–1062

Eliminare l'intero blocco `# Try to auto-populate metadata from provider` e i due `except Exception` annidati. Il loop diventa:

```python
# Build results
for assignment in assignments:
    result = FAProviderAssignmentResult(
        asset_id=assignment.asset_id,
        success=True,
        message=f"Provider {assignment.provider_code} assigned",
        fields_detail=None,
    )
    results.append(result)
```

Commento riga 971 → `# Build results` (rimuovere "and auto-populate metadata").

---

### Step 3 — Fix DistributionEditor ✅ cap 100

**File**: `frontend/src/lib/components/ui/input/DistributionEditor.svelte`

- Riga 158: `Math.max(0, Math.min(100, newVal))` → `Math.max(0, newVal)`
- Riga 210 (funzione `balanceSelected()`): `Math.max(0, Math.min(100, ...))` → `Math.max(0, ...)`

Motivazione: i pesi percentuali possono superare 100 durante l'editing (il vincolo è solo al save, non in real-time).

---

### Step 4 — Fix FX auto-sync ✅ dopo save provider

**File**: `frontend/src/routes/(app)/fx/[pair]/+page.svelte`

Righe 640–641: rimuovere il commento `// Auto-sync to fetch rates from the newly added provider` e la riga `await handleSync()`. Funzione risultante:

```typescript
async function handleProviderModalCreated(_detail: {base: string; quote: string; hasRealProvider: boolean}) {
    await loadProviders();
    showProviderModal = false;
}
```

---

### Step 5 — Fix Pydantic ✅ `errors=None`

**File**: `backend/app/services/fx.py`

- Riga 1088: `errors=fallback_errors if fallback_errors else None` → `errors=fallback_errors or []`
- Riga 1193: `errors=chain_errors if chain_errors else None` → `errors=chain_errors or []`

Lo schema `FXSyncPairResult.errors` è `List[str]` con `default_factory=list`, NON `Optional[List[str]]`. Passare `None` è un type mismatch.

---

### Step 6 — Fix ordine build ✅: font PRIMA del frontend

**File**: `dev.py`

1. `_docker_ensure_assets_built()` (riga 1091): spostare `update_js_cache()` (attualmente step 3, riga 1141) **prima** del frontend build (attualmente step 1, riga 1099). Rinumerare commenti:
   - 1 → JS library cache
   - 2 → Frontend
   - 3 → MkDocs
   - 4 → requirements.txt

2. `cmd_fe_build()` (riga 436): aggiungere `update_js_cache()` come primissimo step, prima di `cmd_api_sync()`. SvelteKit prerender valida i file referenziati in `app.html`, quindi i font devono esistere prima del build.

---

### Step 7 — Aggiungere ✅ `data-testid` per E2E classification

**File**: `frontend/src/lib/components/ui/input/DistributionEditor.svelte`

- Riga 357, wrapper `<div class="space-y-1">`: aggiungere `data-testid="distribution-editor-{kind}"`
- Riga 448, `<span>` del totale percentuale: aggiungere `data-testid="distribution-total-{kind}"`
- Riga 389, bottone `+Add`: aggiungere `data-testid="distribution-add-{kind}"`

**File**: `frontend/src/lib/components/assets/AssetModal.svelte`

- Riga 1248, collapsible "More Info" header `<div>`: aggiungere `data-testid="asset-modal-more-info"`
- Riga 1233, `<textarea>` short description: aggiungere `data-testid="asset-modal-description"`

---

### Step 8 — Migrare test ✅ `test_metadata_auto_populate`

**File**: `backend/test_scripts/test_services/test_asset_source.py`

Sostituire `test_metadata_auto_populate` (righe 244–295) con 6 nuovi test:

| Test | Verifica |
|------|----------|
| `test_assign_does_not_modify_metadata` | Assign mockprov → `classification_params` resta `None` (no auto-populate) |
| `test_assign_preserves_existing_metadata` | Asset con geo+sector pre-impostati → assign provider → geo+sector invariati |
| `test_refresh_returns_metadata_fields` | Dopo assign, `refresh_assets_from_provider()` → risultato contiene `refreshed_fields` con sector, geo, short_desc |
| `test_refresh_populates_empty_asset` | Asset vuoto → refresh → metadata scritti nel DB (sector=Technology, geo=USA+ITA come da mockprov) |
| `test_refresh_field_detail_completeness` | Verifica `missing_data_fields`, `ignored_fields` nel response |
| `test_patch_preserves_user_set_fields` | PATCH con `geographic_area` → refresh da mockprov (che ha geo diverso) → GET → verify che il refresh ha sovrascritto (comportamento refresh: "prende dal provider"). Distinto dal probe/diff che è frontend-driven |

---

### Step 9 — Test backend FX ✅ fallback con MOCKFX

**File**: `backend/test_scripts/test_api/test_fx_sync.py`

Nuova classe `TestFXFallbackWithMockProviders` (auto-discovered da pytest):

| Test | Verifica |
|------|----------|
| `test_fx_fallback_primary_fails` | Crea coppia con route MOCKFX_FAIL priority=1 + MOCKFX priority=2 → sync → `status=OK`, `provider_used` contiene "MOCKFX" (non FAIL), `errors` non-vuoto (contiene errore route 1) |
| `test_fx_fallback_all_fail` | Entrambe le route MOCKFX_FAIL → `status=FAILED`, `errors` contiene 2 errori |
| `test_fx_direct_mockfx` | Solo MOCKFX priority=1 → `status=OK`, `errors=[]` |

I test creano `FxConversionRoute` via API (`POST /fx/currencies/routes`), sync via `POST /fx/currencies/sync`, poi cleanup.

---

### Step 10 — Test E2E asset ✅ classification round-trip

**File**: `frontend/e2e/assets/asset-classification.spec.ts` (nuovo)

| Test | Descrizione |
|------|-------------|
| `set geo distribution → save → reopen → present` | Create asset → open edit modal → expand "More Info" (`data-testid="asset-modal-more-info"`) → click +Add geographic → set country+weight → save → reopen → verify entry presente |
| `set sector distribution → save → reopen → present` | Analogo per sector |
| `clear distribution → save → reopen → empty` | Add geo entry → save → reopen → remove entry → save → reopen → verify empty |

**File**: `scripts/test_runner/_frontend_asset.py`

- Aggiungere `front_asset_classification()` → `_run_playwright("assets/asset-classification.spec.ts")`
- Aggiungere a `front_asset_all()` tests list
- Registrare in `populate_registry()` con `add_test(cat, "asset-classification", ...)`

---

## Riepilogo file modificati

| File | Tipo | Step |
|------|------|------|
| `backend/app/services/fx_providers/mockfx.py` | Nuovo: 2 mock FX providers | 1 |
| `backend/app/api/v1/fx.py` | Edit: filtro API nasconde MOCKFX* | 1 |
| `backend/app/services/asset_source.py` | Edit: rimuovere auto-populate (righe 980–1062) | 2 |
| `frontend/src/lib/components/ui/input/DistributionEditor.svelte` | Edit: rimuovere cap 100 + data-testid | 3, 7 |
| `frontend/src/routes/(app)/fx/[pair]/+page.svelte` | Edit: rimuovere auto-sync | 4 |
| `backend/app/services/fx.py` | Edit: errors=[] instead of None | 5 |
| `dev.py` | Edit: build order font→frontend | 6 |
| `frontend/src/lib/components/assets/AssetModal.svelte` | Edit: data-testid per More Info e description | 7 |
| `backend/test_scripts/test_services/test_asset_source.py` | Edit: sostituire test_metadata_auto_populate con 6 test | 8 |
| `backend/test_scripts/test_api/test_fx_sync.py` | Edit: 3 test FX fallback | 9 |
| `frontend/e2e/assets/asset-classification.spec.ts` | Nuovo: 3 test E2E | 10 |
| `scripts/test_runner/_frontend_asset.py` | Edit: registrazione asset-classification | 10 |

## Post-implementazione

```bash
./dev.py db create-clean --test       # DB pulito
./dev.py test services all            # test_asset_source migrato + test_asset_source_refresh
./dev.py test api test_fx_sync        # FX fallback tests
./dev.py test front-asset all         # E2E asset classification + modal + list + detail
```

---

## Execution Log

### Session 1 (pre-context-break)

Tutti i 10 step implementati. Review utente ha evidenziato:
- `pair_routes_map` tipo → corretto a `dict[str, list[FxConversionRoute]]`
- MockFX reworked: `MOCKFX_FIXED_RATE = Decimal("1.234500")`, `MOCKFX_FAIL.FAIL_MESSAGE` con stringa distintiva
- Import `AssetProviderRegistry` spostato a top-level in `test_asset_source.py`
- DistributionEditor: rimosso `max: 100` anche dalla column definition (riga 322)
- `reloadMetadata()` in `assets/[id]/+page.svelte`: rimosso gate `has_metadata` → always reload after save
- Bug persistence `classification_params.geographic_area`: indagine iniziata, sospetto server con codice vecchio

### Session 2 (2026-05-11)

#### Fix extra trovati durante test run

| # | Bug | File | Fix |
|---|-----|------|-----|
| A | Auto-populate **non rimosso** nella sessione 1 (blocco righe 980-1066 ancora presente) | `asset_source.py` | Rimosso intero blocco — loop ora solo `results.append(result)` |
| B | `errors=None` terza occorrenza in `_compute_single_step` (riga 1088) | `fx.py` | `errors=fallback_errors or []` (il fix della sessione 1 aveva patchato solo 2 su 3 occorrenze) |
| C | `RotateCcw` con `animate-spin` nella `FxPairAddModal` → rotazione visiva antioraria | `FxPairAddModal.svelte` | `RotateCcw` → `RotateCw` sia nell'import che nel template |
| D | FX detail: auto-sync dopo edit provider (sync dentro il modale non distingue create vs edit) | `FxPairAddModal.svelte` | `if (!editMode)` attorno al blocco auto-sync (righe 252-273) |
| E | FX global: toast mancante dopo auto-sync alla creazione coppia | `FxPairAddModal.svelte` | Aggiunto `toasts.success()` con count punti dopo sync OK |

#### Test Results

| Suite | Risultato | Note |
|-------|-----------|------|
| API (35 test groups) | ✅ 35/35 | Include 3 nuovi FX fallback MOCKFX tests |
| Services (543 tests) | ✅ 543/543 | Include 6 nuovi assign/refresh metadata tests |
| Schemas (231 tests) | ✅ 231/231 | Invariati |
| Frontend Utility (5) | ✅ 5/5 | auth, settings, files, select-components, image-crop |
| Frontend User (2) | ✅ 2/2 | multi-user, broker-sharing |
| Frontend FX (8) | ✅ 8/8 | chart-settings, fx-list, fx-detail, ecc. |
| Frontend Asset (5) | ✅ 5/5 | **Include nuovo `asset-classification` E2E** |
| Frontend Transaction (9) | ✅ 9/9 | modals, table, broker-access, paired-edit, tooltips, bulk-ops, ecc. |
| **ALL FRONTEND** | ✅ 6/6 categories | 🎉 ALL FRONTEND TESTS PASSED |

#### File aggiuntivi modificati (non nel piano originale)

| File | Modifica | Motivo |
|------|----------|--------|
| `frontend/src/lib/components/fx/FxPairAddModal.svelte` | `RotateCcw` → `RotateCw` | Icona sync ruotava in direzione sbagliata |
| `frontend/src/routes/(app)/assets/[id]/+page.svelte` | `reloadMetadata()` always reload | Gate su `has_metadata` stale impediva caricamento classification post-save |
| `frontend/src/lib/components/ui/input/DistributionEditor.svelte` | Rimosso `max: 100` da column config | HTML `<input max="100">` bloccava input >100 nonostante il fix JS |

### User Testing Feedback (Session 2)

| Area | Risultato | Note |
|------|-----------|------|
| FX Global — creazione coppia | ✅ | Sync OK, icona corretta, freccia clockwise |
| FX Global — toast post-sync | ❌→✅ | Mancava toast → aggiunto in FxPairAddModal (fix E) |
| FX Detail — edit provider | ❌→✅ | Auto-sync non voluto → `if (!editMode)` (fix D) |
| Asset — classification persistence | ✅ | geo+sector ora persistono dopo PATCH+reload |
| Asset — network flow | ✅ | PATCH assets → GET all → GET assignments → GET query → GET current |

