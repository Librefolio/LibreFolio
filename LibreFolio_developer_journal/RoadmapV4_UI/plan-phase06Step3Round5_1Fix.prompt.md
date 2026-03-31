# Plan: Phase 6 Step 3 — Round 5.1 Fix (post-testing feedback)

Aggiornamento post-testing manuale: correzione dei 9 punti identificati in Round 5, con dettaglio su cosa funziona realmente e cosa richiede ulteriori interventi.

---

## Stato reale dei 9 punti dopo testing utente

| # | Problema | Stato Round 5 | Stato Reale (post-test) | Azione Round 5.1 |
|---|----------|---------------|------------------------|-------------------|
| 1 | Search compila solo campi base | `autoFetchMetadata()` silenzioso | ⚠️ **Parziale** — Il fetch metadata funziona SOLO dal pulsante "Ask Provider Global", ma NON scatta automaticamente dopo selezione dal search. Il flusso search→select non chiama il global. | Fix: `applySearchResult()` deve lanciare direttamente `handleAskProviderGlobal()` (non una funzione separata) |
| 2 | Impossibile rimuovere l'icona | Bottone ✕ + "Remove Image" rosso | ⚠️ **Parziale** — La ✕ nell'URL funziona, ma al click compare un bottone strano al centro e la modale non si chiude. Il vero problema: quando l'URL è vuoto, `ImagePickerWrapper` non mostra il fallback icon. | Fix: semplificare (la ✕ basta), assicurare che URL vuoto → `onchange('')` → `AssetModal` setta `null` → `AssetIcon` mostra fallback. Rimuovere il bottone "Remove Image" superfluo. |
| 3 | Nessun feedback se distribuzioni assenti | Toast per "Ask Provider" globale | ⚠️ **Parziale** — Funziona nel globale e nei singoli "Ask Provider" per settore/geo, ma NON quando si seleziona dal search (collegato a punto 1). Inoltre: quando i dati non ci sono, compare sia toast info (blu) che success (verde) — confusionario. | Fix: (a) dopo search selection → global ask → toast info se mancano dati. (b) Quando i dati non ci sono realmente, sopprimere il toast verde success — mostrare solo l'info blu. |
| 4 | 100.05% segnato come ✅ | Tolleranza da 0.05 a 0.01 | ⚠️ **Quasi** — 100.01% ancora accettato. La somma deve essere ESATTAMENTE 100.00%. Tolleranza = 0 (o ε macchina). I pesi nelle celle devono avere 2-3 decimali max (coerente con backend che usa 4 decimali nel peso raw 0.xxxx → 2 decimali in percentuale). | Fix: tolleranza `0.001` (±0.001%), display a 2 decimali, `emitChange()` arrotonda a 4 decimali raw (= 2 decimali in %). Validazione: `Math.abs(total - 100) < 0.001`. |
| 5 | Ribilanciamento | ✅ Già funzionante | ✅ **Confermato** | Nessuna azione |
| 6 | Nessuna paginazione | `enablePagination={true}`, `defaultPageSize={5}` | ✅ **Confermato** | Nessuna azione |
| 7 | Z-index tendine | ✅ Già funzionante | ✅ **Confermato** | Nessuna azione |
| 8 | "Other" non ammesso in geographic | Frontend: opzione 🏳️ Other. Backend: pass-through in `normalize_country_keys` | ⚠️ **Backend OK, Provider NO** — `normalize_country_keys()` gestisce "Other" correttamente. Ma il provider **JustETF** scarta "Other" nel codice `_country_name_to_iso3()` (return None → riga 354 `if iso3:` lo salta). I dati di justETF contengono "Other" come country name, bisogna preservarlo. | Fix: modificare `justetf.py` → `_country_name_to_iso3()` ritorna `"Other"` (non `None`) per "other", e alla riga 354 includere la entry nella distribuzione. |
| 9 | Tooltip label hardcoded, history senza valori | Formato tabella HTML per current price e history | ⚠️ **Parziale** — Current price mostra tabella perfetta ma il prezzo ha ~10 decimali. History mostra solo `points_count` e `date_range`, nessun valore reale. | Fix: (a) Backend: aggiungere `sample_prices: list[dict]` a `ProbeHistoryResult`, popolare con `[{date, close}]` nel probe. (b) Frontend: usare `sample_prices` nella tooltip tabella. (c) Arrotondare current price a 2 decimali nel tooltip. |

---

## Dettaglio Fix Round 5.1

### Fix 1 — Search selection → auto-ask provider globale (IMMEDIATO)

**Problema**: `applySearchResult()` chiama solo `autoTriggerProbe()` (test current_price+history) ma non chiede i metadata. La funzione `autoFetchMetadata()` creata in Round 5 è separata e non viene invocata, oppure non chiama il path globale che mostra il toast.

**Soluzione**: Dopo `applySearchResult()`, lanciare direttamente `handleAskProviderGlobal()` (la stessa funzione del pulsante "🔄 Ask Provider" globale). Questa funzione già:
- Fa probe con `operations: ['metadata']`
- Popola i campi vuoti
- Mostra la comparison modal se ci sono differenze
- Mostra il toast info se sector/geo sono assenti

Non serve una funzione separata `autoFetchMetadata()` — rimuoverla e usare direttamente il path globale.

**File coinvolti**: `frontend/src/lib/components/assets/AssetModal.svelte`

---

### Fix 2 — Rimozione icona: semplificare + fallback in AssetIcon

**Problema**: Il flusso "Remove Image" ha un bottone strano al centro e la modale non si chiude. L'utente voleva solo poter salvare con URL vuoto, e vedere il fallback nell'anteprima.

**Soluzione**:
1. La ✕ nel campo URL dell'AssetPickerModal è sufficiente — svuota il campo
2. Rimuovere il bottone "Remove Image" rosso aggiunto in Round 5 (confonde)
3. In `AssetPickerModal.svelte`, quando l'utente clicca "Confirm/Select" con URL vuoto, dispatchare `select` con `url: ''`
4. In `AssetModal.handleImagePickerChange(url)`: se `url === ''` → settare `iconUrl = null`
5. Verificare che `AssetIcon` con `iconUrl=null` mostri correttamente il fallback (già funziona — la chain è: iconUrl → PNG per assetType → BarChart3 Lucide)
6. In `ImagePickerWrapper`: NON serve modificare nulla — il componente gestisce già URL vuoto

**File coinvolti**: 
- `frontend/src/lib/components/ui/media/AssetPickerModal.svelte` — rimuovere bottone "Remove Image"
- `frontend/src/lib/components/assets/AssetModal.svelte` — handler URL vuoto → null

---

### Fix 3 — Toast coerenti: no doppio toast quando dati assenti

**Problema**: Quando si clicca "Ask Provider" per un campo singolo (es. Sector) e il provider non ha dati, compaiono 2 toast: info (blu) "Provider has no data for Sector" + success (verde) "Provider data fetched". Tecnicamente entrambi sono corretti ma è confusionario.

**Soluzione**:
1. Se il provider NON ha dati per il campo richiesto → mostrare SOLO toast info (blu)
2. Se il provider HA dati → mostrare SOLO toast success (verde)
3. Mai entrambi contemporaneamente per la stessa operazione
4. Per la selezione da search (collegato Fix 1): dato che ora si chiama `handleAskProviderGlobal()`, il toast info per campi mancanti scatterà automaticamente

**File coinvolti**: `frontend/src/lib/components/assets/AssetModal.svelte` — logica toast in `handleAskProvider()` e varianti locali

---

### Fix 4 — Tolleranza distribuzione: esattamente 100.00%

**Problema**: 100.01% è ancora accettato. L'utente vuole somma ESATTA.

**Soluzione**:
1. **Tolleranza validazione**: `Math.abs(total - 100) < 0.005` (= ±0.005%, cioè meno di 1 centesimo di punto percentuale). Questo copre gli errori di floating point senza ammettere 100.01%.
2. **Display pesi**: 2 decimali (`XX.XX%`) — coerente con 4 decimali raw del backend (0.xxxx → xx.xx%)
3. **`emitChange()`**: arrotonda a 4 decimali raw → `Number((weight / 100).toFixed(4))` (già presente)
4. **Validazione totale nel frontend**: `isValid = Math.abs(totalPercent - 100) < 0.005`
5. **Celle editable**: `step={0.01}`, max 2 decimali visualizzati

**File coinvolti**: `frontend/src/lib/components/ui/input/DistributionEditor.svelte`

---

### Fix 5 — Ribilanciamento ✅ CONFERMATO

Nessuna azione necessaria.

---

### Fix 6 — Paginazione ✅ CONFERMATO

Nessuna azione necessaria.

---

### Fix 7 — Z-index ✅ CONFERMATO

Nessuna azione necessaria.

---

### Fix 8 — JustETF provider: preservare "Other" nella distribuzione geografica

**Problema**: Il backend (`normalize_country_keys`) gestisce già "Other" come pass-through. Ma il provider JustETF lo scarta:

```python
# justetf.py riga 55-63:
def _country_name_to_iso3(country_name: str) -> Optional[str]:
    if country_name.lower() == "other":
        return None  # ← PROBLEMA: ritorna None

# justetf.py riga 354:
    if iso3:  # Skip "Other" and unknown countries  ← PROBLEMA: None viene scartato
```

JustETF restituisce paesi come `["Taiwan", "China", "Korea", "Other"]` con percentuali. "Other" rappresenta la quota residua e DEVE essere preservata.

**Soluzione**:

```python
# justetf.py — _country_name_to_iso3():
def _country_name_to_iso3(country_name: str) -> Optional[str]:
    if country_name.lower() == "other":
        return "Other"  # ← Preserve "Other" as-is (normalize_country_keys handles it)
    try:
        from backend.app.utils.geo_utils import normalize_country_to_iso3
        return normalize_country_to_iso3(country_name)
    except (ValueError, ImportError) as e:
        logger.debug(f"Could not normalize country '{country_name}': {e}")
        return None
```

La riga 354 (`if iso3:`) continua a funzionare perché `"Other"` è truthy.

**Verifica**: testare con `IE00B0M63177` (iShares MSCI EM Asia) che ha "Other" nei paesi.

**File coinvolti**: `backend/app/services/asset_source_providers/justetf.py`

---

### Fix 9 — Probe history: aggiungere `sample_prices` + arrotondare prezzo

**Problema**: 
- Il tooltip history mostra solo `points_count` e `date_range`, nessun valore reale
- Il current price nel tooltip ha ~10 decimali
- Il probe backend non include i prezzi effettivi nella response history

**Soluzione Backend**:

**a) Schema** — `backend/app/schemas/provider.py`:
```python
class ProbeHistoryResult(BaseProbeOperationResult):
    """Result of history probe operation."""
    points_count: Optional[int] = Field(None, description="Number of price points found")
    date_range: Optional[str] = Field(None, description="Date range of found data (start → end)")
    sample_prices: Optional[list[dict]] = Field(
        None, 
        description="Sample price points [{date: str, close: str}], max 10"
    )
```

**b) Service** — `backend/app/services/asset_source.py` in `_probe_history()`:
```python
# Dopo aver ottenuto `points`:
sample = None
if points:
    sample = [
        {"date": str(p.date), "close": str(round(float(p.close), 2))}
        for p in points[:10]  # Max 10 punti
    ]
return ProbeHistoryResult(
    success=True,
    points_count=len(points),
    date_range=date_range_str,
    sample_prices=sample,
    execution_time_ms=...,
)
```

**c) Rigenerare client zodios** (`./dev.py api sync`)

**Soluzione Frontend**:

**d) Tooltip history** — usare `sample_prices` dalla response per costruire la tabella HTML:
```html
<table>
  <tr><th>📅 Date</th><th>💰 Close</th></tr>
  <tr><td>2026-03-24</td><td>47.12</td></tr>
  <tr><td>2026-03-25</td><td>47.30</td></tr>
  ...
</table>
```

**e) Tooltip current price** — arrotondare a 2 decimali: `Number(value).toFixed(2)`

**File coinvolti**:
- `backend/app/schemas/provider.py` — aggiungere `sample_prices`
- `backend/app/services/asset_source.py` — popolare `sample_prices` in `_probe_history()`
- `frontend/src/lib/components/assets/ProviderAssignmentSection.svelte` — tooltip con sample_prices
- Rigenerazione `generated.ts`

---

## Ordine di esecuzione consigliato

1. **Fix 8** (backend JustETF — piccolo, indipendente)
2. **Fix 9a-c** (backend probe sample_prices + regen client)
3. **Fix 4** (frontend tolleranza distribuzione)
4. **Fix 2** (frontend rimozione icona — semplificare)
5. **Fix 3** (frontend toast coerenti)
6. **Fix 1** (frontend search → auto ask global — dipende da Fix 3)
7. **Fix 9d-e** (frontend tooltip con sample_prices — dipende da 9a-c)

---

## Validation Checklist

- [ ] `npx svelte-check --threshold error` → 0 errors
- [ ] `pytest` backend tests pass
- [ ] `./dev.py i18n audit` → 100% coverage
- [ ] `./dev.py api sync` completato (per sample_prices)
- [ ] Manuale: search selection → auto-popola identifiers + distributions + toast info se mancanti
- [ ] Manuale: ✕ su URL icona → salva → fallback icon visibile (no bottone strano)
- [ ] Manuale: Ask Provider senza dati → solo toast info (blu), NO toast success (verde)
- [ ] Manuale: 100.01% → ⚠️ non valido, 100.00% → ✅ valido
- [ ] Manuale: IE00B0M63177 → distribuzione geografica include "Other"
- [ ] Manuale: tooltip history → tabella con date e prezzi reali
- [ ] Manuale: tooltip current price → prezzo con 2 decimali

