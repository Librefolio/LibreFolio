# Plan: Bug Fix 3 — Chart, Layout, Toast, Panel Redesign

Piano per 5 issue dopo il fix del `effect_update_depth_exceeded` (Bugfix 1) e del metadata reload (Bugfix 2).

---

## Issue 0 (CRITICO): `effect_update_depth_exceeded` — ModalBase.svelte ✅

**Root cause**: `tick()` dentro `$:` reactive in ModalBase (Svelte 4 legacy) causa `flushSync()` ricorsivo quando combinato con `$effect` complessi in AssetModal (Svelte 5 runes).

**Fix applicati (2 file)**:
1. `ModalBase.svelte`: sostituito `tick().then(...)` con `requestAnimationFrame(...)` per evitare flushSync ricorsivo
2. `AssetModal.svelte`: wrappato corpo `$effect` in `untrack()` per tracciare solo `open` come dipendenza

---

## Issue 1: Colori chart non si aggiornano senza F5 ✅

**Fix**: Aggiunto MutationObserver in `onMount()` di `SectorPieChart.svelte` e `GeographyMap.svelte` (già applicato nella sessione precedente).

---

## Issue 2: Traduzione nomi nazione in GeographyMap ⬜

**Approccio**: Backend `GET /api/v1/utilities/countries?language=xx` per nomi localizzati. Tooltip usa reverse lookup nome inglese → ISO A3 → nome localizzato.

---

## Issue 3: Matrice 2×2 bottoni non diventa colonna su tablet-s ✅

**Fix**: Aggiunto `layout.layoutMode === 'tablet-s'` alla condizione CSS del container bottoni.

---

## Issue 4: Warning FX — da testo inline a toast ✅

**Fix**: Sostituito banner inline con icona ⚠️ cliccabile + toast auto-show/dismiss via `$effect`.

---

## Issue 5: Redesign pannello Aesthetics (toolbar laterale chart) ✅

**Fix applicato su ENTRAMBE le pagine (asset-detail + fx-detail)**:
1. Rimosso pannello Aesthetics foldable dalla posizione sopra il chart
2. Spostato pannello Signals nella posizione dove era Aesthetics
3. Aggiunta toolbar verticale sinistra al chart (⚙️ Aesthetics, ✏️ Editor, 📏 Measure)
4. Pannello Aesthetics renderizzato sotto il chart solo quando gear è attivo

---

## Ordine di Esecuzione (aggiornato)

1. ~~Issue 0~~ ✅ ModalBase + AssetModal
2. ~~Issue 1~~ ✅ MutationObserver chart
3. ~~Issue 3~~ ✅ Layout tablet-s
4. ~~Issue 4~~ ✅ Toast FX warning
5. ~~Issue 5~~ ✅ Panel redesign
6. **Issue 2** ⬜ GeographyMap traduzioni nazioni (richiede integrazione backend)
