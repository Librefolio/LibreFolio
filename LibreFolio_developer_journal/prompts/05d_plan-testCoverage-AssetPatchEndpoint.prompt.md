# Test Coverage Plan: Asset PATCH Endpoint & Metadata

**Documento**: 05d_plan-testCoverage-AssetPatchEndpoint.prompt.md  
**Data**: 2025-12-10  
**Obiettivo**: Documentare i test mancanti per coprire le nuove funzionalità del PATCH endpoint unificato

---

## 📋 Contesto

Dopo il refactoring del modello dati e l'unificazione degli endpoint:
- ❌ **Eliminato**: `PATCH /api/v1/assets/metadata` (endpoint separato per metadata)
- ✅ **Esteso**: `PATCH /api/v1/assets` ora gestisce **tutti** i campi dell'asset, inclusi i metadati
- ✅ **Esteso**: Il modello `FAAssetPatchItem` ora supporta tutti i campi patchabili

### Campi patchabili via PATCH /api/v1/assets:
1. `display_name` (str)
2. `currency` (str)
3. `asset_type` (AssetType enum)
4. `icon_url` (Optional[str])
5. `active` (bool)
6. `classification_params` (Optional[FAClassificationParams])

---

## 🎯 Test Esistenti

### Test già presenti in `test_assets_metadata.py`:
1. ✅ **test_patch_metadata_valid_geographic_area** - Testa patch di `classification_params.geographic_area`
2. ✅ **test_patch_metadata_invalid_geographic_area** - Validation error per country code invalidi
3. ✅ **test_patch_metadata_absent_fields** - PATCH semantics (campi assenti non modificati)
4. ✅ **test_patch_metadata_null_clears_field** - Null cancella il campo
5. ✅ **test_bulk_read_assets** - Lettura bulk con metadata
6. ✅ **test_bulk_read_multiple_assets** - Lettura multiple assets preservando ordine
7. ✅ **test_metadata_refresh_single_no_provider** - Refresh metadata senza provider (dovrebbe fallire)
8. ✅ **test_metadata_refresh_bulk** - Refresh bulk metadata
9. ✅ **test_patch_metadata_geographic_area_sum_validation** - Validation: somma deve essere 1.0
10. ✅ **test_patch_metadata_multiple_assets** - Patch multipli assets in un'unica chiamata

### Test già presenti in `test_assets_crud.py`:
1. ✅ **test_create_single_asset** - Crea singolo asset
2. ✅ **test_create_multiple_assets** - Crea multipli assets
3. ✅ **test_create_partial_success** - Successo parziale (duplicato)
4. ✅ **test_create_duplicate_identifier** - Duplicato rigettato
5. ✅ **test_create_with_classification_params** - Creazione con metadata
6. ✅ **test_list_no_filters** - Lista senza filtri
7. ✅ **test_list_filter_currency** - Filtra per currency
8. ✅ **test_list_filter_asset_type** - Filtra per asset_type
9. ✅ **test_list_search** - Ricerca testuale
10. ✅ **test_list_active_filter** - Filtra per active
11. ✅ **test_list_has_provider** - Verifica campo has_provider
12. ✅ **test_delete_success** - Delete con successo
13. ✅ **test_delete_cascade** - DELETE cascade (provider + prices)
14. ✅ **test_delete_partial_success** - Successo parziale delete
15. ✅ **test_list_asset_providers** - Lista providers disponibili
16. ✅ **test_bulk_remove_providers** - Rimozione provider bulk
17. ✅ **test_bulk_delete_prices** - Delete prices bulk (skipped - endpoint WIP)
18. ✅ **test_bulk_refresh_prices** - Refresh prices bulk (skipped - endpoint WIP)

---

## ❌ Test Mancanti

### 1. PATCH - Campi Base Asset (NON metadata)

#### Test 1.1: `test_patch_display_name`
**Obiettivo**: Verificare che il PATCH di `display_name` funzioni correttamente
**Steps**:
1. Creare un asset con `display_name="Original Name"`
2. PATCH solo `display_name="Updated Name"`
3. Verificare che:
   - Response: `success=True`, `updated_fields` contiene `display_name`
   - DB: `display_name` aggiornato
   - Altri campi: invariati

---

#### Test 1.2: `test_patch_currency`
**Obiettivo**: Verificare che il PATCH di `currency` funzioni correttamente
**Steps**:
1. Creare un asset con `currency="USD"`
2. PATCH solo `currency="EUR"`
3. Verificare che:
   - Response: `success=True`, `updated_fields` contiene `currency`
   - DB: `currency` aggiornato
   - Altri campi: invariati

---

#### Test 1.3: `test_patch_asset_type`
**Obiettivo**: Verificare che il PATCH di `asset_type` funzioni correttamente
**Steps**:
1. Creare un asset con `asset_type=STOCK`
2. PATCH solo `asset_type=ETF`
3. Verificare che:
   - Response: `success=True`, `updated_fields` contiene `asset_type`
   - DB: `asset_type` aggiornato
   - Altri campi: invariati

---

#### Test 1.4: `test_patch_icon_url`
**Obiettivo**: Verificare che il PATCH di `icon_url` funzioni correttamente
**Steps**:
1. Creare un asset con `icon_url=None`
2. PATCH solo `icon_url="https://example.com/icon.png"`
3. Verificare che:
   - Response: `success=True`, `updated_fields` contiene `icon_url`
   - DB: `icon_url` aggiornato
   - Altri campi: invariati

---

#### Test 1.5: `test_patch_icon_url_clear`
**Obiettivo**: Verificare che settare `icon_url=None` cancelli il campo
**Steps**:
1. Creare un asset con `icon_url="https://example.com/icon.png"`
2. PATCH solo `icon_url=None` (o stringa vuota)
3. Verificare che:
   - Response: `success=True`, `updated_fields` contiene `icon_url`
   - DB: `icon_url=None`

---

#### Test 1.6: `test_patch_active_flag`
**Obiettivo**: Verificare che il PATCH di `active` funzioni correttamente
**Steps**:
1. Creare un asset con `active=True` (default)
2. PATCH solo `active=False`
3. Verificare che:
   - Response: `success=True`, `updated_fields` contiene `active`
   - DB: `active=False`
4. Verificare che l'asset NON appaia in GET con filtro `active=true`

---

### 2. PATCH - Campi Multipli Simultanei

#### Test 2.1: `test_patch_multiple_base_fields`
**Obiettivo**: Verificare che il PATCH di più campi base funzioni atomicamente
**Steps**:
1. Creare un asset
2. PATCH simultaneo di:
   - `display_name="New Name"`
   - `currency="EUR"`
   - `asset_type=ETF`
   - `icon_url="https://example.com/icon.png"`
3. Verificare che:
   - Response: `success=True`, `updated_fields` contiene tutti i campi
   - DB: tutti i campi aggiornati correttamente

---

#### Test 2.2: `test_patch_base_and_metadata`
**Obiettivo**: Verificare che il PATCH di campi base + metadata funzioni atomicamente
**Steps**:
1. Creare un asset
2. PATCH simultaneo di:
   - `display_name="New Name"`
   - `classification_params.sector="Technology"`
   - `classification_params.geographic_area={"USA": 0.6, "EUR": 0.4}`
3. Verificare che:
   - Response: `success=True`, `updated_fields` contiene `display_name` e `classification_params`
   - DB: tutti i campi aggiornati correttamente

---

#### Test 2.3: `test_patch_partial_metadata_update`
**Obiettivo**: Verificare che il PATCH parziale di metadata funzioni (merge, non replace)
**Steps**:
1. Creare un asset con:
   ```json
   classification_params: {
     "sector": "Technology",
     "geographic_area": {"USA": 1.0},
     "short_description": "Original desc"
   }
   ```
2. PATCH solo `classification_params.sector="Finance"`
3. Verificare che:
   - Response: `success=True`
   - DB: `sector="Finance"`, ma `geographic_area` e `short_description` invariati (merge, non replace)

---

### 3. PATCH - Validazioni e Error Handling

#### Test 3.1: `test_patch_invalid_currency`
**Obiettivo**: Verificare che currency invalida venga rigettata
**Steps**:
1. Creare un asset
2. PATCH con `currency="INVALID"`
3. Verificare che:
   - Response: 422 Unprocessable Content
   - Error message: contiene "currency"

---

#### Test 3.2: `test_patch_invalid_asset_type`
**Obiettivo**: Verificare che asset_type invalido venga rigettato
**Steps**:
1. Creare un asset
2. PATCH con `asset_type="INVALID_TYPE"`
3. Verificare che:
   - Response: 422 Unprocessable Content
   - Error message: contiene "asset_type"

---

#### Test 3.3: `test_patch_nonexistent_asset`
**Obiettivo**: Verificare che PATCH su asset inesistente fallisca
**Steps**:
1. PATCH con `asset_id=999999` (inesistente)
2. Verificare che:
   - Response: success in results è `False`
   - Message: contiene "not found"

---

#### Test 3.4: `test_patch_empty_payload`
**Obiettivo**: Verificare che PATCH senza campi da aggiornare sia gestito correttamente
**Steps**:
1. Creare un asset
2. PATCH con `FAAssetPatchItem(asset_id=X)` (nessun campo specificato)
3. Verificare che:
   - Response: `success=True` (noop è success)
   - `updated_fields=[]` (nessun campo modificato)

---

#### Test 3.5: `test_patch_duplicate_display_name`
**Obiettivo**: Verificare che PATCH con display_name duplicato fallisca
**Steps**:
1. Creare asset A con `display_name="Unique Name"`
2. Creare asset B con `display_name="Other Name"`
3. PATCH asset B con `display_name="Unique Name"` (duplicato)
4. Verificare che:
   - Response: success=False per asset B
   - Message: contiene "already exists" o "duplicate"

---

### 4. PATCH - Bulk Operations

#### Test 4.1: `test_patch_bulk_heterogeneous`
**Obiettivo**: Verificare PATCH bulk con aggiornamenti eterogenei
**Steps**:
1. Creare 3 assets
2. PATCH bulk:
   - Asset 1: solo `display_name`
   - Asset 2: solo `classification_params.sector`
   - Asset 3: `currency` + `asset_type`
3. Verificare che:
   - Response: `success_count=3`
   - Ogni asset ha `updated_fields` corretto
   - DB: tutti aggiornati correttamente

---

#### Test 4.2: `test_patch_bulk_partial_failure`
**Obiettivo**: Verificare PATCH bulk con successi e fallimenti
**Steps**:
1. Creare 2 assets validi
2. PATCH bulk:
   - Asset 1 (valido): `display_name="New Name"`
   - Asset 999999 (inesistente): `display_name="Invalid"`
   - Asset 2 (valido): `currency="EUR"`
3. Verificare che:
   - Response: `success_count=2`
   - Results[0]: success=True
   - Results[1]: success=False (not found)
   - Results[2]: success=True

---

### 5. PATCH - Metadata Avanzato

#### Test 5.1: `test_patch_metadata_sector_only`
**Obiettivo**: Verificare PATCH solo del campo `sector` nei metadata
**Steps**:
1. Creare asset con metadata completi
2. PATCH solo `classification_params.sector="Finance"`
3. Verificare che:
   - Response: `success=True`
   - DB: `sector` aggiornato, altri metadata invariati

---

#### Test 5.2: `test_patch_metadata_short_description_only`
**Obiettivo**: Verificare PATCH solo del campo `short_description`
**Steps**:
1. Creare asset con metadata completi
2. PATCH solo `classification_params.short_description="New desc"`
3. Verificare che:
   - Response: `success=True`
   - DB: `short_description` aggiornato, altri metadata invariati

---

#### Test 5.3: `test_patch_metadata_clear_all`
**Obiettivo**: Verificare che si possano cancellare tutti i metadata
**Steps**:
1. Creare asset con metadata completi
2. PATCH con `classification_params={}` (o stringa vuota)
3. Verificare che:
   - Response: `success=True`
   - DB: `classification_params=None`

---

#### Test 5.4: `test_patch_metadata_geographic_area_update`
**Obiettivo**: Verificare aggiornamento di `geographic_area` esistente
**Steps**:
1. Creare asset con `geographic_area={"USA": 0.7, "FRA": 0.3}`
2. PATCH con `geographic_area={"CHN": 0.5, "USA": 0.5}`
3. Verificare che:
   - Response: `success=True`
   - DB: `geographic_area` completamente sostituito (non merged)

---

### 6. PATCH - Interazioni con Provider

#### Test 6.1: `test_patch_after_provider_metadata_fetch`
**Obiettivo**: Verificare che metadata fetchati da provider possano essere sovrascritti via PATCH
**Steps**:
1. Creare asset
2. Assegnare provider (che auto-popola metadata)
3. Verificare metadata popolati
4. PATCH con `classification_params.sector="Custom"`
5. Verificare che:
   - Response: `success=True`
   - DB: `sector` sovrascritto con valore custom

---

#### Test 6.2: `test_patch_does_not_affect_provider_assignment`
**Obiettivo**: Verificare che PATCH metadata non rimuova provider assignment
**Steps**:
1. Creare asset
2. Assegnare provider
3. PATCH con `classification_params.sector="New"`
4. Verificare che:
   - Provider assignment: ancora presente
   - Metadata: aggiornato

---

### 7. GET - Verifica Risposta

#### Test 7.1: `test_get_asset_includes_all_fields`
**Obiettivo**: Verificare che GET ritorni tutti i campi patchabili
**Steps**:
1. Creare asset con tutti i campi popolati
2. GET asset
3. Verificare che response include:
   - `display_name`
   - `currency`
   - `asset_type`
   - `icon_url`
   - `active`
   - `classification_params` (completo)
   - `has_provider`

---

#### Test 7.2: `test_get_asset_null_fields`
**Obiettivo**: Verificare che campi null siano serializzati correttamente
**Steps**:
1. Creare asset con campi minimi (molti null)
2. GET asset
3. Verificare che:
   - `icon_url=None` (non omesso)
   - `classification_params=None` (non omesso)

---

### 8. PATCH - Updated Fields Tracking

#### Test 8.1: `test_patch_updated_fields_accuracy`
**Obiettivo**: Verificare che `updated_fields` riporti solo campi effettivamente modificati
**Steps**:
1. Creare asset con `display_name="Old"`, `currency="USD"`
2. PATCH con `display_name="Old"` (stesso valore), `currency="EUR"` (nuovo)
3. Verificare che:
   - `updated_fields=["currency"]` (solo quello cambiato)
   - NON include `display_name` (valore uguale)

---

#### Test 8.2: `test_patch_updated_fields_empty_if_no_change`
**Obiettivo**: Verificare che `updated_fields=[]` se nessun campo cambia
**Steps**:
1. Creare asset con `display_name="Name"`, `currency="USD"`
2. PATCH con `display_name="Name"`, `currency="USD"` (valori uguali)
3. Verificare che:
   - Response: `success=True`
   - `updated_fields=[]`

---

### 9. PATCH - Atomicità e Transazioni

#### Test 9.1: `test_patch_atomicity_validation_error`
**Obiettivo**: Verificare che se un campo fallisce validation, nessun campo venga aggiornato
**Steps**:
1. Creare asset
2. PATCH con:
   - `display_name="Valid"`
   - `geographic_area={"USA": 0.5}` (somma != 1.0, invalid)
3. Verificare che:
   - Response: 422 error
   - DB: `display_name` NON aggiornato (rollback atomico)

---

#### Test 9.2: `test_patch_bulk_independence`
**Obiettivo**: Verificare che errore su un asset non influenzi altri nel bulk
**Steps**:
1. Creare 2 assets
2. PATCH bulk:
   - Asset 1: `display_name="Valid"`
   - Asset 2: `geographic_area={"USA": 0.5}` (invalid)
3. Verificare che:
   - Asset 1: `success=True`, aggiornato
   - Asset 2: `success=False`, non aggiornato

---

### 10. PATCH - Performance e Limiti

#### Test 10.1: `test_patch_bulk_limit`
**Obiettivo**: Verificare limite massimo di assets in un'unica PATCH bulk
**Steps**:
1. Creare 100+ assets
2. PATCH bulk con tutti gli IDs
3. Verificare che:
   - Se limite esiste: errore appropriato
   - Se no limite: tutti aggiornati correttamente

---

## 📊 Riepilogo

### Test Totali Proposti: **35 nuovi test**

### Categorizzazione:
- **Campi Base** (6 test): display_name, currency, asset_type, icon_url, active
- **Campi Multipli** (3 test): bulk field updates, base+metadata
- **Validazioni** (5 test): invalid values, nonexistent asset, duplicates
- **Bulk Operations** (2 test): heterogeneous, partial failure
- **Metadata Avanzato** (4 test): sector, description, clear, geographic_area
- **Provider Interactions** (2 test): metadata override, provider preservation
- **GET Verification** (2 test): all fields, null fields
- **Updated Fields Tracking** (2 test): accuracy, empty list
- **Atomicità** (2 test): validation rollback, bulk independence
- **Performance** (1 test): bulk limit

### Priorità:
1. **Alta (P0)**: Test 1.1-1.6, 2.1-2.2, 3.1-3.3, 8.1 (14 test) - Funzionalità core
2. **Media (P1)**: Test 2.3, 3.4-3.5, 4.1-4.2, 5.1-5.4 (9 test) - Validazioni e metadata
3. **Bassa (P2)**: Test 6.1-6.2, 7.1-7.2, 8.2, 9.1-9.2, 10.1 (8 test) - Edge cases

---

## 🎯 Script di Test Proposto

Creare nuovo file: `backend/test_scripts/test_api/test_assets_patch_extended.py`

### Struttura:
```python
"""
Extended Asset PATCH Endpoint Tests.

Comprehensive test suite for PATCH /api/v1/assets covering:
- Individual field patching (display_name, currency, asset_type, icon_url, active)
- Multiple simultaneous field updates
- Metadata partial updates and merge behavior
- Validation and error handling
- Bulk operations with heterogeneous updates
- Updated fields tracking accuracy
- Transaction atomicity
"""
```

---

## ✅ Action Items

1. **Review**: L'utente deve revieware la lista dei test proposti
2. **Prioritize**: Decidere quali test implementare per primi (P0/P1/P2)
3. **Implement**: Creare `test_assets_patch_extended.py` con i test selezionati
4. **Iterate**: Aggiungere test man mano che nuove funzionalità vengono implementate

---

## 📝 Note

- I test esistenti in `test_assets_metadata.py` coprono già bene il caso d'uso `classification_params`
- I nuovi test si concentrano su:
  - **Campi base** (display_name, currency, etc.) che prima non erano patchabili via endpoint unificato
  - **Comportamento PATCH semantics** (merge vs replace)
  - **Updated fields tracking** (nuova feature)
  - **Atomicità e transazioni**
- Alcuni test sono "nice-to-have" (P2) ma completano la coverage

---

**Fine del documento**

