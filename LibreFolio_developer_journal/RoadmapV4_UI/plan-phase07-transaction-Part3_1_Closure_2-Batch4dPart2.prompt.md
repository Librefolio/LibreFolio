# Batch 4.d-part2 — `saveWithRetry` adoption (modali restanti)

> 📄 **Sub-plan di** [`plan-phase07-transaction-Part3_1_Closure_2.prompt.md`](./plan-phase07-transaction-Part3_1_Closure_2.prompt.md) §I-bis #22.
> **Prerequisito**: Batch 4.d-part1 (helper + `BrokerModal` + `CashTransactionModal` + `AssetCurrencyChangeModal` extractor) — NON ancora committato.
>
> **Finding audit 2026-04-24**: il parent plan traccia 6 modal da migrare; dopo audit dei sorgenti il count reale è **5 mutation-bearing** (vedi §Scope audit). Il parent viene aggiornato in coda.

**Data**: 2026-04-24 — **Stima totale**: ~2h15.

## Scope audit

**Inclusi (mutation verso API)**
1. `PasswordChangeModal.svelte` — settings
2. `FxPairAddModal.svelte` — fx
3. `BrokerImportFilesModal.svelte` — upload + delete (3 call sites)
4. `BrokerSharingModal.svelte` — brokers
5. `AssetModal.svelte` — assets ⚠️ HIGH RISK

**Esclusi** (no API mutation — pure UI/callback)
- `BoundaryDateModal.svelte` → solo `onconfirm(date)`, zero `zodiosApi.*`.
- `ProviderComparisonModal.svelte` → solo `onapply(selectedFields)`; il PATCH avviene nel parent `AssetModal` (già coperto dal target #5).

**Esclusi per categoria**: `BrokerModal`, `CashTransactionModal`, `AssetCurrencyChangeModal` (part1), `ConfirmModal`, `ChartSettingsModal`, `AssetPickerModal`, `*DataImportModal` (EditBuffer), `AssetSyncModal`/`FxSyncModal`/`PageSyncModal` (sync con toast dedicato).

---

## Ordine di esecuzione (facile → rischioso)

| # | Modal | Effort | Rischio |
|---|-------|-------:|:-------:|
| 1 | `PasswordChangeModal` | 15 min | basso |
| 2 | `FxPairAddModal` | 20 min | basso |
| 3 | `BrokerImportFilesModal` | 25 min | medio |
| 4 | `BrokerSharingModal` | 20 min | basso |
| 5 | `AssetModal` | ~1h | alto |

---

## 1. `PasswordChangeModal.svelte`

**Save corrente** (`handleSubmit`): `zodiosApi.change_password_*` + try/catch con match `detail.toLowerCase()` su `"incorrect"` / `"different"` → 2 chiavi i18n esistenti.

**Migration**:
- `saveWithRetry(..., { toast: false, fallback: $t('settings.passwordChangeFailed'), onError })`.
- `onError(err)`: se `detail` contiene `incorrect` → `error = $t('settings.currentPasswordIncorrect'); return true`; se `different` → `error = $t('settings.passwordMustBeDifferent'); return true`; altrimenti `return false`.
- On error: `if (!error) error = result.message`.

**i18n**: zero nuove chiavi.

---

## 2. `FxPairAddModal.svelte`

**Save corrente** (`handleSave`): `create_routes_bulk` + auto-sync non-blocking già in inner try/catch.

**Migration**:
- Wrappare **solo** `create_routes_bulk` con `saveWithRetry`, `toast: false`, `fallback: $t('fx.addPair.createFailed')`.
- Lasciare auto-sync invariato.
- On success: continuare con flow esistente; on error: `error = result.message; return`.

**i18n NUOVE × 4**: `fx.addPair.createFailed`:
- EN: `"Failed to create FX pair"`
- IT: `"Creazione coppia FX fallita"`
- FR: `"Échec de la création de la paire FX"`
- ES: `"Error al crear el par FX"`

---

## 3. `BrokerImportFilesModal.svelte`

**3 call sites**: upload loop, delete single, delete multiple.

**Migration**:
- **Upload**: `saveWithRetry` per iterazione, `prefix: file.name`, `toast: false`, `fallback: $t('uploads.uploadFailed')`; break al primo errore (semantica esistente).
- **Delete single**: `saveWithRetry`, `toast: false`, `fallback: $t('uploads.deleteFailed')`.
- **Delete multiple**: **collect-all** errors, summary `error = $t('uploads.deleteFailedSome', {values: {count: n}})`.

**i18n NUOVA × 4**: `uploads.deleteFailedSome`:
- EN: `"Failed to delete {count} file(s)"`
- IT: `"Eliminazione di {count} file fallita"`
- FR: `"Échec de la suppression de {count} fichier(s)"`
- ES: `"Error al eliminar {count} archivo(s)"`

---

## 4. `BrokerSharingModal.svelte`

**Save corrente** (`handleSave`): `bulk_update_broker_access_*` + try/catch manuale con concat `saveFailed + ': ' + detail`.

**Migration**:
- `saveWithRetry`, `toast: false`, `fallback: $t('brokers.sharing.saveFailed')`.
- On error: `error = result.message` (no concat manuale — extractor già formatta).

**i18n**: zero nuove chiavi.

---

## 5. `AssetModal.svelte` ⚠️ HIGH RISK

**Save corrente** — orchestrator `doSave` → `saveCreate` | `saveEdit`. Flussi custom da **preservare**:
- 409 **currency-change** intercept in `saveEdit` (riga 927–937): ri-costruisce `patchResp` da `detail.results[]` — NON deve bollire come errore.
- 409 **duplicate-name** (create): mappato a `formError = $t('assets.modal.duplicateName')`.
- Auto-sync post-save (riga 1005–1019, #R6-5): già non-blocking con `console.warn` — lasciare invariato.
- Provider-assign-after-create-success failure (riga 859–866): toast warning + chiude — lasciare invariato.

**Migration strategy** — wrap solo l'outer `doSave`:

```ts
const result = await saveWithRetry(
    () => (editMode && editData?.id) ? saveEdit(editData.id) : saveCreate(),
    {
        fallback: $t('assets.modal.saveFailed'),
        toast: false,
        onError: (err: any) => {
            if (err?.response?.status === 409) {
                formError = $t('assets.modal.duplicateName');
                return true;
            }
            return false;
        },
    },
);
if (result.status === 'error' && !formError) {
    formError = result.message;
}
// scroll error into view existente
```

**i18n NUOVA × 4**: `assets.modal.saveFailed`:
- EN: `"Failed to save asset"`
- IT: `"Salvataggio asset fallito"`
- FR: `"Échec de l'enregistrement de l'actif"`
- ES: `"Error al guardar el activo"`

**Checklist retest manuale post-migration**:
- [ ] Create nuovo → success + chiude.
- [ ] Create con nome esistente → `formError = duplicateName`, aperta.
- [ ] Edit solo name → OK + chiude.
- [ ] Edit currency con prezzi → modal destructive (409 intercept intatto).
- [ ] Edit con backend offline → formError inline + modal aperta + draft intatto.
- [ ] Edit con provider assign fail post-patch → toast warning + chiude.

---

## Commit strategy

1 commit unico: `feat(phase07): Batch 4.d-part2 — saveWithRetry adoption (5 modals)` — accorpato nel blocco unico Batch 4 (vedi parent plan §"Batch 4 commit ready").

**Validazione finale**:
```bash
./dev.py format && ./dev.py lint && ./dev.py front check
```

Smoke test manuale: cambio password con pwd errata, FX pair con route invalida, upload file corrotto, sharing PUT, edit asset offline.

---

## ✅ Retest esiti (2026-04-24)

Checklist di retest happy/bad-flow eseguita manualmente: 28 check
totali su 5 modali. Report completo in `/tmp/libreFolio_batch4dPart2_retest_checklist.md`.

| # | Modal | Esito `saveWithRetry` | Esito semantiche preservate | Note |
|---|-------|:---------------------:|:---------------------------:|------|
| 1 | `PasswordChangeModal` | ✅ PASS | ✅ onError incorrect/different + InfoBanner | — |
| 2 | `FxPairAddModal` | ✅ PASS | ✅ auto-sync non-blocking isolato | — |
| 3 | `BrokerImportFilesModal` | ✅ PASS (upload + delete single + delete bulk) | 🟡 design-drift | vedi **#R6-6** (no toast upload) e **#R6-7** (no ConfirmModal bulk delete) nel parent plan |
| 4 | `BrokerSharingModal` | ✅ PASS | 🟡 design-drift | vedi **#R6-8** (success → banner invece di toast+close) nel parent plan |
| 5 | `AssetModal` | ✅ PASS | ✅ 409 dup + 409 currency + #R6-5 auto-sync | — |

**Checklist retest AssetModal (riga 135–142 di questo sub-plan)**:
- [x] Create nuovo → success + chiude.
- [x] Create con nome esistente → `formError = duplicateName`, aperta.
- [x] Edit solo name → OK + chiude.
- [x] Edit currency con prezzi → modal destructive (409 intercept intatto).
- [x] Edit con backend offline → formError inline + modal aperta + draft intatto.
- [x] Edit con provider assign fail post-patch → toast warning + chiude.
- [x] **Bonus #R6-5**: provider change non-parametrico → auto-sync parte, chart aggiornato senza F5.
- [x] **Bonus #R6-1 retest**: edit con provider dropdown change + identifier wipe + Save → `formError = providerIncomplete` (skippato: già validato in retest 4.a).

**Conclusione**: Batch 4.d-part2 **CHIUSO** dal punto di vista
dell'adozione `saveWithRetry`. I 3 drift di design (#R6-6/#R6-7/#R6-8)
sono tracciati nel parent plan e verranno affrontati in un follow-up
**Batch 4.d-part3** post-commit — non bloccano il commit unico di
Batch 4.

**Stato finale**: ✅ DONE (2026-04-24) — ready for commit (blocco Batch 4).

