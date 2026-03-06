# Plan: FX Sync API Redesign — Pair-Based Bulk Sync

## Contesto

L'attuale endpoint `GET /api/v1/fx/currencies/sync` accetta una lista piatta di **valute** (`currencies=USD,GBP,CHF`), non di **coppie**. Il frontend deriva le valute dalle coppie configurate, ma questo causa problemi:

1. **Ambiguità**: passando `USD,GBP,CHF` il backend non sa quali coppie servono (EUR/USD? USD/GBP? tutte?)
2. **Risposta vaga**: restituisce `synced: N` e `currencies: [...]` — non dice per-coppia quanti punti, né quale provider ha servito
3. **Coppie spurie**: il backend genera coppie cartesiane (`c1 < c2`) che non esistono nella config
4. **Nessun dettaglio errore/provider**: se una coppia fallisce o usa un fallback, il frontend non lo sa

## Obiettivo

Nuovo endpoint **pair-based** che:
- Accetta una lista di coppie (`["EUR-USD", "CHF-CNY"]`)
- Ordina internamente le valute in ordine alfabetico (es. `USD-EUR` → `EUR-USD`)
- Per ogni coppia: tenta i provider in ordine di priorità dalla config `fx_currency_pair_sources`
- Restituisce per ogni coppia: `{ pair, points_fetched, points_changed, provider_used, status, message }`
- Il frontend mostra risultati per-coppia nel SyncModal

## Design API

### Endpoint

```
POST /api/v1/fx/currencies/sync
```

**Breaking change** — da GET a POST, la vecchia GET verrà rimossa.

### Request Body

```json
{
  "pairs": ["EUR-USD", "EUR-GBP", "CHF-CNY"],
  "start": "2025-12-06",
  "end": "2026-03-06"
}
```

**Schema Pydantic:**
```python
class FXSyncPairRequest(BaseModel):
    pairs: List[str]  # ["EUR-USD", "CHF-CNY"] — ordine valute non vincolante
    start: date
    end: date

    @field_validator('pairs', mode='before')
    @classmethod
    def validate_pairs(cls, v):
        """Validate each pair: split by '-', validate both currencies via Currency.validate_code."""
        validated = []
        for pair in v:
            parts = pair.split('-')
            if len(parts) != 2:
                raise ValueError(f"Invalid pair format: '{pair}'. Expected 'BASE-QUOTE'.")
            base = Currency.validate_code(parts[0])
            quote = Currency.validate_code(parts[1])
            # Normalize: alphabetical order
            if base > quote:
                base, quote = quote, base
            validated.append(f"{base}-{quote}")
        return validated
```

**Normalizzazione**: il backend ordina ogni coppia in ordine alfabetico:
- `USD-EUR` → `EUR-USD`
- `CNY-CHF` → `CHF-CNY`
Questo perché il DB salva sempre `base < quote` per convenzione.

### Response Body

```json
{
  "date_range": { "start": "2025-12-06", "end": "2026-03-06" },
  "results": [
    {
      "pair": "EUR-USD",
      "status": "ok",
      "provider_used": "ECB",
      "points_fetched": 61,
      "points_changed": 3,
      "message": null
    },
    {
      "pair": "EUR-GBP",
      "status": "ok",
      "provider_used": "ECB",
      "points_fetched": 61,
      "points_changed": 0,
      "message": null
    },
    {
      "pair": "CHF-CNY",
      "status": "partial",
      "provider_used": "SNB",
      "points_fetched": 3,
      "points_changed": 3,
      "message": "SNB provides monthly data only"
    }
  ],
  "summary": {
    "total_pairs": 3,
    "ok": 2,
    "partial": 1,
    "failed": 0,
    "total_points_changed": 6
  }
}
```

**Schema Pydantic:**
```python
class FXSyncPairResult(BaseModel):
    pair: str            # "EUR-USD"
    status: str          # "ok" | "partial" | "failed" | "skipped"
    provider_used: str | None  # "ECB", "SNB", "MANUAL", None se fallita
    points_fetched: int
    points_changed: int
    message: str | None  # Nota opzionale (es. "monthly data only", "fallback used")

    @field_validator('pair')
    @classmethod
    def validate_pair(cls, v):
        """Validate pair currencies via Currency.validate_code."""
        parts = v.split('-')
        if len(parts) != 2:
            raise ValueError(f"Invalid pair format: '{v}'")
        Currency.validate_code(parts[0])
        Currency.validate_code(parts[1])
        return v

class FXSyncBulkResponse(BaseBulkResponse[FXSyncPairResult]):
    """
    Inherits from BaseBulkResponse:
    - results: List[FXSyncPairResult]
    - success_count: int (pairs with status ok or partial)
    - errors: List[str] (operation-level errors)
    - failed_count: computed property

    Additional fields:
    """
    date_range: DateRangeModel
    total_points_changed: int = Field(0, description="Sum of points_changed across all pairs")
```

**Status per coppia:**
- `ok` — provider ha restituito dati, inseriti/aggiornati nel DB
- `partial` — provider ha dati ma incompleti (es. SNB mensile, buchi)
- `failed` — tutti i provider per questa coppia hanno fallito
- `skipped` — coppia MANUAL-only, non c'è niente da sincronizzare

## Logica Backend di Sync con Fallback

Per ogni coppia nel body:

```
1. Normalizza: ordina base/quote alfabeticamente
2. Cerca nella tabella fx_currency_pair_sources tutte le entry per (base, quote)
   ordinante per priority ASC
3. Filtra: escludi provider_code="MANUAL"
4. Se nessun provider reale → status="skipped", provider_used=null
5. Per ogni provider in ordine di priorità:
   a. Chiama ensure_rates per questa singola coppia
   b. Se successo → status="ok"/"partial", provider_used=codice, break
   c. Se fallisce → log warning, prova il prossimo
   d. Se message contiene info utili (es. "monthly data") → popola message
6. Se tutti falliti → status="failed", message="All providers failed: ..."
```

**Note importanti:**
- Ogni coppia è indipendente: se EUR/USD fallisce, EUR/GBP viene comunque processata
- Il provider MANUAL non viene mai chiamato per sync (è un sentinella per dati manuali)
- La risposta include SEMPRE tutte le coppie richieste, anche quelle skipped/failed

## Modifiche Backend

### Step 1: Schema (backend/app/schemas/refresh.py)
- Aggiungere `FXSyncPairRequest`, `FXSyncPairResult`, `FXSyncSummary`, `FXSyncBulkResponse`
- Mantenere `FXSyncResponse` deprecato (compatibilità test, da rimuovere poi)

### Step 2: Service Layer (backend/app/services/fx.py)
- Nuova funzione `sync_pair(session, base, quote, start, end) -> FXSyncPairResult`
  - Carica provider dalla config, tenta in ordine, gestisce fallback
  - Restituisce risultato strutturato con provider_used e conteggi
- Nuova funzione `sync_pairs_bulk(session, pairs, start, end) -> FXSyncBulkResponse`
  - Chiama `sync_pair` per ogni coppia
  - Aggrega il summary

### Step 3: API Endpoint (backend/app/api/v1/fx.py)
- Cambiare `GET /fx/currencies/sync` → `POST /fx/currencies/sync`
- Body: `FXSyncPairRequest`
- Response: `FXSyncBulkResponse`
- Validazione: date range, coppie valide

### Step 4: Frontend (FxSyncModal.svelte)
- Adattare la chiamata da GET con query params a POST con body JSON
- Mostrare risultati per-coppia nella modale:
  - Per ogni coppia: icona status (✅/⚠️/❌/⏭️), nome coppia con bandiere, punti, provider
  - Riassunto in fondo: "Synced 3/4 pairs, 128 points changed"
- Tradurre tutti i testi (i18n)

### Step 5: Aggiornare api sync (./dev.py api sync)
- Rigenerare il client TypeScript dopo le modifiche allo schema

### Step 6: Test
- Test backend: sync con coppie miste (ok, partial, failed, skipped)
- Test con fallback (provider primario fallisce, secondario succede)
- Test normalizzazione (USD-EUR → EUR-USD)
- Test coppia MANUAL-only → skipped

## Modifiche Frontend SyncModal

### Layout Risultati Per-Coppia

```
┌──────────────────────────────────────────────────┐
│ 🔄  Sync FX Rates                            ✕  │
├──────────────────────────────────────────────────┤
│                                                  │
│ Sync rates from configured providers.            │
│                                                  │
│ ┌──────────────────────────────────────────────┐ │
│ │ 📅 2025-12-06 → 2026-03-06 · 4 pairs       │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ [dopo sync — risultati per coppia]               │
│                                                  │
│  ✅ 🇪🇺EUR/🇺🇸USD — 61 pts (ECB)              │
│  ✅ 🇪🇺EUR/🇬🇧GBP — 61 pts (ECB)              │
│  ⚠️ 🇨🇭CHF/🇨🇳CNY — 3 pts (SNB) monthly only  │
│  ⏭️ 🇦🇲AMD/🇨🇭CHE — skipped (manual only)      │
│                                                  │
│ ┌──────────────────────────────────────────────┐ │
│ │ ✅ Synced 3/4 pairs · 125 points changed    │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
├──────────────────────────────────────────────────┤
│                                    [Close]       │
└──────────────────────────────────────────────────┘
```

## Note Aggiuntive

- **Non serve backward compatibility**: l'endpoint GET vecchio viene rimosso
- **La normalizzazione delle coppie** garantisce che anche se il frontend manda `USD-EUR`, il backend lo tratta come `EUR-USD` senza errore
- **MANUAL provider**: viene sempre skippato nel sync. Se una coppia ha SOLO il provider MANUAL, il risultato è `skipped` con messaggio esplicativo
- **Documentazione MkDocs**: aggiornare la sezione FX con il nuovo flusso di sync (vedi plan-phase05Fx per la nota globale)

## Stato

- [ ] Step 1: Schema Pydantic (FXSyncPairRequest, FXSyncPairResult, FXSyncBulkResponse)
- [ ] Step 2: Service layer (sync_pair, sync_pairs_bulk)
- [ ] Step 3: API endpoint (POST /fx/currencies/sync)
- [ ] Step 4: Frontend SyncModal adattamento
- [ ] Step 5: api sync + client regen
- [ ] Step 6: Test
- [ ] Step 7: Cleanup — rimuovere FXSyncResponse deprecato

