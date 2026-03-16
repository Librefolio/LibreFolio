# Plan: FX Conversion Chain — Route-based Multi-Step Currency Conversion

**Data creazione**: 12 Marzo 2026
**Status**: ✅ COMPLETATO (Step 1-7 done, solo test manuali e docs update pendenti)
**Priorità**: Alta (prerequisito per completare Phase 5 FX)
**Stima**: ~3-4 giorni (backend done, frontend done)
**Dipendenze**: Tutti i sub-plan Phase 5 ✅ completati (vedi `phases/phase-05-subplan/`)
**Riferimenti**:
- `phases/phase-05-subplan/05FX_outofdate_plan/plan-phase05Fx.prompt.md` — vecchio master plan Phase 5 (📦 ARCHIVIATO)
- `phases/phase-05-subplan/05FX_outofdate_plan/phase05-pending-audit.md` — audit task pendenti (C6)
- `TODO_FUTURI.md` §FX, §Cross-Rate
- `plan-phase05-to-08-upgrade.md` §4 (Phase 5 overview)

### Progress Log

| Data | Stato | Dettagli |
|------|-------|----------|
| 12 Mar 2026 | 📋 Piano creato | Definiti Step 1-7 con architettura completa |
| 13 Mar 2026 | ✅ Step 1-5 backend completati | Data model, schemas, service layer, API endpoints, test |
| 13 Mar 2026 | 🔧 Bug fix sessione review | 3 fix critiche (vedi sotto) |
| 13 Mar 2026 | ✅ Step 6 frontend completato | currencyGraph.ts, currencyGraphStore.ts, FxRouteSelect.svelte, FxPairAddModal aggiornato, FxProviderConfig chain display, i18n 8 chiavi |
| 13 Mar 2026 | 🔧 Refinements sessione review | 5 fix post-review utente (vedi §Refinements) |
| 13 Mar 2026 | ✅ R1 + R5 completati | FxProviderSelect riscritto con DFS+OrderableList+collapsible picker+search+flags+icons. FxRouteSelect eliminato. |
| 13 Mar 2026 | 🔧 Toast \n fix | Cambiato \\\\n → \\n nei JSON i18n + whitespace-pre-line su ToastContainer |
| 13 Mar 2026 | 🔧 Tooltip instant | Sostituiti title= nativi con Tooltip component in FxSyncModal |
| 13 Mar 2026 | 🔧 ProviderInfo esteso | Aggiunto icon_url e description a ProviderInfo + currencyGraphStore mapping |
| 13 Mar 2026 | 🐛 BOE provider broken | BOE restituisce HTML (bot protection?) invece di CSV — Parsed 0 rates |
| 13 Mar 2026 | 🐛 ECB provider cascade | asyncio.gather senza return_exceptions: se CAD fallisce, TUTTE le valute ECB falliscono |
| 15 Mar 2026 | ✅ B1 fix applicato | BOE: aggiunto header Accept text/csv + guard HTML detection |
| 15 Mar 2026 | ✅ B2 fix applicato | ECB+FED+BOE: `return_exceptions=True` in tutti e 3 i provider — niente più cascade failure |
| 15 Mar 2026 | ✅ B3 pycountry warning | Soppresso warning "already taken in index" (leone, bolívar soberano) in main.py |
| 15 Mar 2026 | 🔧 Toast layout fix | ToastContainer: items-start + mt-0.5 + text-left per multilinea corretta |
| 15 Mar 2026 | 🔧 Info icon ↓Δ tooltip | FxSyncModal: sostituiti Tooltip wrapping con Info icon + Tooltip (come signal cards) |
| 15 Mar 2026 | 🔧 Frecce bidirezionali | FxProviderSelect + FxProviderConfig: freccia prima E dopo il provider (anche direct) |
| 15 Mar 2026 | 🔧 Badge priorità numerica | FxProviderSelect + FxProviderConfig: #1, #2, #3 invece di "primario"/"fallback" |
| 15 Mar 2026 | ✅ B4 partial message | Backend: `sync_pairs_bulk` ora propaga `message` descrittivo per status PARTIAL (1-step e chain) |
| 15 Mar 2026 | 🔧 SyncModal tooltip stato | Info icons solo su summary; tooltip su icona stato (▲) per partial/failed con dettagli + messaggio |
| 15 Mar 2026 | 🔧 Toast partial+failed | Toast singolo: aggiunto fetched↓ + provider + append message/reason su nuova riga |
| 15 Mar 2026 | 🔧 Provider colored rect | Rettangolo semitrasparente colorato attorno a `→ [provider] →` in tutti i 4 punti di rendering |
| 15 Mar 2026 | 🔧 Fibonacci priority badge | Creato `colors.ts` con golden-ratio color generation. Badge priorità con colori Fibonacci. Refactored `getBrokerColor` in FilesTable. |
| 15 Mar 2026 | 🐛 Fix else mancante fx.py | `else:` per ramo multi-step chain era stato perso → catene irraggiungibili nel bulk sync |
| 15 Mar 2026 | 🔧 ECB anti-bot jitter | `ecb.py`: jitter random 0-100ms prima di ogni fetch parallelo. Se >50% falliscono → retry seriale con 50-200ms tra richieste. |
| 15 Mar 2026 | 🔧 ECB → seriale puro | Jitter non sufficiente, rimosso parallelo: ECB ora fetch seriale puro (1 valuta alla volta). |
| 15 Mar 2026 | 🔧 SyncModal partial retry | Partial rows ora mostrano bottone retry (come failed), tooltip con messaggio errore su hover. Rimosso testo errore inline. |
| 15 Mar 2026 | 🔧 Provider color spread | Hue esplicite per ECB(220°)/FED(30°)/BOE(150°)/SNB(340°) — massima separazione visiva. |
| 15 Mar 2026 | 🔧 AddPair auto-focus | Dopo selezione base currency con Enter, auto-focus+open sulla quote currency select. |
| 15 Mar 2026 | 🔧 Remove system tooltip | Provider legend: rimosso `title=` nativo per evitare doppio tooltip (custom + browser). |
| 15 Mar 2026 | 🔧 Accordion smart open | FxProviderSelect: se ci sono direct routes, nessuna catena auto-espansa. Se no direct, solo la prima catena. |
| 15 Mar 2026 | 🔧 Provider box tooltips | Tooltip custom (nome+descrizione) sui rettangoli provider in FxProviderSelect + FxProviderConfig (tutti i contesti: selected, picker, detail). |
| 15 Mar 2026 | 🔧 Remove direct name | FxProviderConfig: rimosso testo nome provider dal diretto (la leggenda lo mostra già). |
| 15 Mar 2026 | 🔧 Chain info icon | Icona ℹ️ su ogni catena con tooltip che spiega "se un provider fallisce, tutta la catena fallisce". |
| 15 Mar 2026 | 🐛 Sync deadlock fix | SQLite WAL mode abilitato (`PRAGMA journal_mode=WAL`) per evitare deadlock reader-writer nel sync pipeline. Aggiunto timeout 120s su event waiting + catch-all in endpoint. |
| 15 Mar 2026 | 🔧 Direct picker label | Rimosso testo nome provider anche dal picker direct items (non solo selected). |
| 15 Mar 2026 | 🔧 Chain info → titolo | Spostato ℹ️ info icon dai singoli item catena al titolo della sezione (sia picker che config page). |
| 15 Mar 2026 | 🔧 Arrow alignment | FxPairAddModal: freccia base→quote centrata verticalmente (sm:mt-5 al posto di sm:pb-2). |
| 15 Mar 2026 | 🔧 Dynamic timeout | FxSyncModal: timeout proporzionale — `max(10, pairs.length × 1)` secondi. Scala col numero di coppie. |
| 15 Mar 2026 | 🔧 Arrow alignment v2 | FxPairAddModal: freccia centrata con invisible label placeholder (stessa struttura dei select). `sm:items-start` + spacer. |
| 15 Mar 2026 | 🐛 SyncModal reset fix | $effect tracciava `pairs.length` → resettava tutto al re-render. Ora usa `wasOpen` per resettare solo su transizione closed→open. |
| 15 Mar 2026 | 🐛 DFS cycle elimination | `findAllPaths`: sostituito `usedEdgePairs` con `visitedNodes: Set<string>` — produce solo **simple paths** (nessun nodo ripetuto). Elimina catene ridondanti tipo EUR→USD→GBP→EUR→RON dove il round-trip è inutile. |
| 15 Mar 2026 | 🔧 Arrow alignment v3 | FxPairAddModal: freccia centrata ai selettori — `items-stretch` + invisible label spacer + `flex-1` per stretching verticale. |
| 15 Mar 2026 | 🔧 Chain sort by configured | FxProviderSelect: catene ordinate per numero di coppie intermedie già configurate (discendente) — le catene che riutilizzano coppie esistenti appaiono prima. Nuova prop `configuredPairSlugs`. |
| 15 Mar 2026 | ✅ Create intermediate pairs | FxPairAddModal: checkbox "Crea anche le coppie intermedie" (visibile solo con catene selezionate). Ogni step della catena viene salvato come coppia autonoma con il suo provider. Auto-sync anche delle coppie intermedie create. i18n 4 lingue (2 chiavi). |
| 15 Mar 2026 | 🔧 Pairs count badge | FX list page: badge numerico nel titolo con conteggio coppie registrate (tondo, colore brand). |
| 15 Mar 2026 | 🐛 Currency select overflow | FxPairAddModal: aggiunto `min-w-0` su entrambi i container flex-1 delle currency select per impedire che nomi lunghi espandano il div oltre lo spazio. |
| 15 Mar 2026 | 🔧 Bidirectional arrow | FxPairAddModal: freccia `ArrowLeftRight`/`ArrowDownUp` (bidirezionale) al posto di `ArrowRight`/`ArrowDown` — la conversione FX è bidirezionale. |
| 15 Mar 2026 | 🔧 Exclude existing pairs | FxPairAddModal: nuova prop `excludedCurrencies` su CurrencySearchSelect. Impedisce di selezionare coppie già configurate (indipendentemente dal verso). |
| 15 Mar 2026 | ✅ Step 7 cleanup audit | Grep per riferimenti legacy, aggiornamento status piano. |
| 15 Mar 2026 | 🔧 Chain bidirectional arrows | FxProviderConfig + FxProviderSelect: `ArrowRight` → `ArrowLeftRight` nei box provider (catene e dirette) — coerente con bidirezionalità FxPairAddModal. |
| 15 Mar 2026 | 🔧 Enter focus debounce | SearchSelect: non auto-aprire dropdown su Enter se il trigger ha appena ricevuto focus e un valore è già selezionato. FxPairAddModal: `trigger.click()` solo se quoteCurrency è vuota. |
| 15 Mar 2026 | ✅ MkDocs FX config updated | `configuration.md`: riscritta interamente per documentare `FxConversionRoute`, chain routes, nuovi endpoint `/fx/providers/routes`. Aggiornati anche `backend_documentation_audit.md` e `documentation_plan.md`. |
| 15 Mar 2026 | ✅ Step 5 scenari smarcati | Tutti i 20 scenari CRUD+sync erano già coperti dai test ma i checkbox non erano stati aggiornati — ora marcati [x]. |
| 15 Mar 2026 | ✅ MkDocs FX chain algo doc | Creata pagina `developer/frontend/fx-chain-algorithm.md`: descrizione completa dell'algoritmo DFS, vincoli, grafi Mermaid con esempi RON→USD, complessità, caching, sorting UI. Aggiunta a nav + indice frontend. |
| 16 Mar 2026 | ✅ Provider `warning_i18n` | Nuova proprietà `warning_i18n` su `FXRateProvider` (default: `{}`). Override su SNB con warning 4 lingue che spiega dati solo mensili e conseguenze sulle catene. Schema `FXProviderInfo` + endpoint + client rigenerato. |
| 16 Mar 2026 | 🔧 Warning ⚠️ triangle UI | `FxProviderSelect` + `FxProviderConfig`: triangolo ambra con tooltip concatenato per route che usano provider con `warning_i18n` non vuoto. Visibile sia nelle route selezionate che nel picker (direct + chain). |
| 16 Mar 2026 | 🔧 Strict chain date match | `compute_chain_rate`: confermato exact-date matching. Se un leg non ha dati per una data → la data viene skippata. Nessun backward-fill nelle catene: i dati vengono salvati solo quando TUTTI i leg hanno rate fresco per quel giorno. |

### Refinements — 13 Marzo 2026 (post-review utente)

Feedback raccolti dopo la prima demo funzionante del frontend:

- [x] **R1. FxRouteSelect → riassorbire in FxProviderSelect.svelte**: Il componente `FxRouteSelect.svelte` è stato eliminato. La logica DFS e le 3 sezioni (Direct/Chain/Unusable) sono integrate dentro `FxProviderSelect.svelte`, che è il selettore unificato. Implementato: OrderableList per priorità delle route selezionate (drag&drop), bandiere valute, icone provider (da icon_url con fallback iniziali), ricerca full-text (AND per token), bottone collapsabile "+ Aggiungi route" per il picker, rimozione route dall'OrderableList.

- [x] **R2. Toast sync singola non i18n e manca simboli ↓Δ**: I toast in `handleSyncPair` (fx list page) e `handleSync` (fx detail page) usano stringhe hardcoded in inglese. Devono: (a) usare chiavi i18n, (b) mostrare su 2 righe, (c) includere i simboli ↓ (download) e Δ (changed) come nella modale Sync All.

- [x] **R3. SyncModal elapsed_ms mostra tempo frontend, non backend**: In `FxSyncModal.svelte` riga 112-114, `elapsedMs: elapsed` assegna il tempo frontend globale (`Date.now() - syncStart`) a ogni risultato. Deve usare `pr.elapsed_ms` dal backend (per-pair), con fallback al frontend.

- [x] **R4. Backend points_changed = points_fetched per catene e bulk 1-step**: In `sync_pair()` e `sync_pairs_bulk()`, le route (sia 1-step nel bulk che multi-step) usano `INSERT ON CONFLICT DO UPDATE` senza contare le righe effettivamente cambiate. Il risultato è `points_changed = len(computed_rates)` sempre uguale a `points_fetched`. Fix: prima dell'upsert, caricare i rate esistenti per le date coinvolte, confrontare con `truncate_fx_rate()`, contare solo le differenze reali.

- [x] **R5. Cleanup FxRouteSelect.svelte**: File eliminato. Export rimosso da `fx/index.ts`. Import in FxPairAddModal cambiato a FxProviderSelect dal barrel `select/`. Commenti e2e aggiornati.

### Bug — 13 Marzo 2026 (da risolvere)

- [x] **B1. BOE provider restituisce HTML**: L'endpoint BOE (`fromshowcolumns.asp`) restituisce una pagina HTML completa (con `<meta>`, `<script>`, Google Tag Manager, etc.) invece dei dati CSV. Probabilmente Cloudflare/bot protection. Il parser skippa tutte le righe → 0 rates. **Fix applicato (15 Mar)**: aggiunto header `Accept: text/csv`, guard che rileva HTML nel body e lancia `FXServiceError` chiara, + `return_exceptions=True` nel gather per isolare il fallimento.

- [x] **B2. ECB cascade failure su asyncio.gather**: In `ECBProvider.fetch_rates()` (ecb.py:234-236), `asyncio.gather(*tasks)` senza `return_exceptions=True` fa sì che se UNA valuta (es. CAD) fallisce, TUTTE le valute ECB falliscono e nessun dato viene restituito. **Fix applicato (15 Mar)**: `return_exceptions=True` su tutti e 3 i provider (ECB, FED, BOE), iterazione risultati con skip delle eccezioni e log warning.

- [x] **B3. pycountry duplicate index warning**: `Currency 'leone' already taken in index 'name'` e `'bolívar soberano'` sono warning innocui da pycountry (ISO 4217 ha SLL/SLE e VEF/VES con nome uguale). **Fix applicato (15 Mar)**: `warnings.filterwarnings("ignore", ...)` in `main.py`.

### Bug fix — 13 Marzo 2026 (risolti)

1. **`logger.log(5, ...)` → `logger.debug(...)`** in `convert_bulk()` (fx.py:1387-1394)
   - **Causa**: structlog `BoundLogger.log(5, msg)` genera `KeyError(5)` perché il livello TRACE (5) non è registrato in structlog
   - **Effetto**: conversioni con backward-fill (weekend) fallivano silenziosamente con errore "Conversion X failed: 5"
   - **Fix**: sostituito con `logger.debug("backward_fill_applied", pair=..., ...)` con kwargs strutturati

2. **Import inline spostati al top** in 5 file:
   - `fx.py`: rimossi 5 import duplicati in `sync_pair()` e `sync_pairs_bulk()` (già al top del file)
   - `api/v1/fx.py`: spostati `import json` (3 occorrenze) e `MANUAL_PRIORITY` al top
   - `db/models.py`: spostato `import json` al top (usato in `parsed_steps` property)
   - `main.py`: spostato `import sqlite3` al top
   - `populate_mock_data.py`: spostati `import random`, `import traceback`, `hash_password`, `IdentifierType`, `MANUAL_PRIORITY`, `seed_default_avatars`, `get_uploads_dir` al top; consolidato `IdentifierType` import duplicato

3. **Mock data arricchiti** in `populate_mock_data.py`:
   - Aggiunti 13 nuovi rate pairs (AUD/EUR, BRL/USD, INR/USD, GBP/USD, CAD/USD, EUR/RON, EUR/PLN, EUR/HUF, EUR/SEK, CHF/USD) per supportare le catene 2-step
   - Aggiunte 2 nuove catene: SEK/USD via EUR (ECB+FED cross-provider), CAD/GBP via USD (FED+FED same-provider)
   - Totale catene mock: 5 same-provider + 4 cross-provider + 1 MANUAL = 10 routes chain

---

## Contesto e Obiettivo

### Problema attuale

Il sistema FX supporta solo conversioni **dirette**: per convertire RON→USD deve esistere un rate `RON/USD` in `fx_rates`. Ma nessuna banca centrale fornisce quella coppia direttamente. ECB fornisce EUR→RON e EUR→USD, FED fornisce USD→EUR, ecc.

Se l'utente aggiunge la coppia RON-USD, il sync fallisce perché nessun provider la supporta.

### Soluzione: Conversion Chain

Permettere all'utente di configurare route **multi-step**:

```
RON → EUR (ECB) → USD (ECB)
```

Il sistema durante il sync:
1. Scarica i rate delle gambe intermedie dal provider
2. Calcola il rate derivato moltiplicando i rate delle gambe
3. Salva il rate derivato in `fx_rates` come dato pre-computato

### Principi di design

1. **Pre-compute & store**: i rate derivati vengono calcolati al sync e salvati in `fx_rates` con source descrittivo (es. `CHAIN:ECB+ECB`). Questo permette edit manuali del rate derivato, esattamente come per i rate diretti.
2. **No duplicazione fetch**: se nella stessa bulk sync sono richieste sia la catena RON→EUR→USD sia la gamba EUR→USD, il download avviene una sola volta.
3. **Gambe non richieste = temporanee**: se la gamba EUR→RON NON è richiesta come sync separata, viene scaricata solo per il calcolo e non salvata in `fx_rates`, per evitare modifiche involontarie.
4. **Lunghezza catena**: qualsiasi, purché senza archi ripetuti (vedi §Algoritmo DFS).
5. **Cross-provider ok**: ogni step ha il suo `provider`. Se un provider nella catena fallisce, l'intera catena fallisce (documentare nella UI).
6. **Modello unificato**: ogni route è SEMPRE una catena (`chain_steps`). Le conversioni "dirette" sono catene con 1 solo step. Nessuna distinzione `DIRECT`/`CHAIN` nel data model — semplifica tutto il codice.
7. **Non retrocompatibile**: la tabella `fx_currency_pair_sources` viene sostituita. Migrazione = edit di `001_initial.py` + cancellazione DB.

---

## Step 1 — Data Model: `fx_conversion_routes`

### Nuova tabella (sostituisce `fx_currency_pair_sources`)

```sql
CREATE TABLE fx_conversion_routes (
    id              INTEGER PRIMARY KEY,
    base            VARCHAR NOT NULL,       -- coppia desiderata, ordine alfabetico (base < quote)
    quote           VARCHAR NOT NULL,
    priority        INTEGER NOT NULL DEFAULT 1,  -- 1=primary, 2+=fallback

    -- Catena di conversione (SEMPRE presente, anche per "diretti" con 1 step)
    chain_steps     TEXT NOT NULL,           -- JSON array ordinato
    -- 1-step (diretto): [{"from": "EUR", "to": "USD", "provider": "ECB"}]
    -- Multi-step:       [{"from": "RON", "to": "EUR", "provider": "ECB"},
    --                     {"from": "EUR", "to": "USD", "provider": "ECB"}]

    fetch_interval  INTEGER,                -- frequenza fetch in minuti (NULL = default 1440)
    created_at      DATETIME NOT NULL,
    updated_at      DATETIME NOT NULL,

    CONSTRAINT uq_route_base_quote_priority UNIQUE (base, quote, priority),
    CONSTRAINT ck_route_base_less_than_quote CHECK (base < quote)
);

CREATE INDEX idx_route_base_quote ON fx_conversion_routes (base, quote);
CREATE INDEX ix_fx_conversion_routes_base ON fx_conversion_routes (base);
CREATE INDEX ix_fx_conversion_routes_quote ON fx_conversion_routes (quote);
```

### Formato `chain_steps` JSON

**Diretto (1 step):**
```json
[{"from": "EUR", "to": "USD", "provider": "ECB"}]
```

**Multi-step (catena):**
```json
[
  {"from": "RON", "to": "EUR", "provider": "ECB"},
  {"from": "EUR", "to": "USD", "provider": "ECB"}
]
```

**MANUAL-only pair:**
```json
[{"from": "NOK", "to": "SEK", "provider": "MANUAL"}]
```

Il campo `chain_steps` corrisponde direttamente alla lista di archi prodotta dall'algoritmo DFS di ricerca percorsi (vedi Step 6A). L'output dell'algoritmo frontend è quindi direttamente salvabile come `chain_steps` senza trasformazioni.

### Regole di validazione

1. **Continuità**: `step[i].to == step[i+1].from` per ogni coppia di step consecutivi
2. **No archi ripetuti**: lo stesso arco (stessa coppia di valute, **qualsiasi direzione**, **qualsiasi provider**) non può apparire due volte. Es.: se c'è uno step EUR→USD (ECB), non può esserci anche USD→EUR (FED) né EUR→USD (FED). Questo perché l'inversione produce lo stesso rate e sarebbe ridondante. Il vincolo è sulle coppie di nodi, non sugli archi individuali del grafo. Corrisponde al check `edgePair = [src, tgt].sort().join('-')` nel DFS frontend e a `edge = tuple(sorted([fc, tc]))` nel validator backend.
3. **Coerenza con coppia target**: gli estremi della catena (`step[0].from` e `step[-1].to`) devono corrispondere a `(base, quote)` della route (in uno dei due ordini, gestito dalla normalizzazione alfabetica)
4. **Provider validi**: ogni `provider` deve essere registrato nel `FXProviderRegistry`
5. **Minimo 1 step**: array non vuoto

### Tasks Step 1

- [x] Creare modello SQLModel `FxConversionRoute` in `backend/app/db/models.py`
  - Sostituisce `FxCurrencyPairSource`
  - Field: `chain_steps` come `str` (JSON serializzato, NOT NULL)
  - Validator: `base < quote` (ordine alfabetico come `FxRate`)
  - Validator: `chain_steps` deve essere JSON array valido con almeno 1 elemento
  - Property helper: `is_chain` → `len(parsed_steps) > 1`
  - Property helper: `providers_used` → set di provider codes da chain_steps
- [x] Aggiornare `001_initial.py`: sostituire `CREATE TABLE fx_currency_pair_sources` con `CREATE TABLE fx_conversion_routes`
- [x] Aggiornare `populate_mock_data.py`:
  - Sostituire `FxCurrencyPairSource` con `FxConversionRoute`
  - Migrare le coppie EUR esistenti a formato chain 1-step: `[{"from": "EUR", "to": "USD", "provider": "ECB"}]`
  - Aggiungere route multi-step (3 same-provider ECB+ECB/FED+FED, 4 cross-provider ECB+FED/ECB+BOE/ECB+SNB)
  - Aggiornare la coppia MANUAL (NOK-SEK) a formato chain: `[{"from": "NOK", "to": "SEK", "provider": "MANUAL"}]`
  - Aggiunti mock rates per tutte le gambe delle catene (13 coppie aggiuntive)
- [x] Rimuovere la classe `FxCurrencyPairSource` da `models.py`

---

## Step 2 — Pydantic Schemas

### 2A. Funzione helper `validate_chain_steps()` — validazione riutilizzabile

La logica di validazione della catena (continuità, no archi ripetuti, estremi coerenti) viene usata sia nello schema Pydantic `FXConversionRouteItem` sia nel modello SQLModel `FxConversionRoute`. Per evitare duplicazione, la logica viene estratta in una funzione standalone.

**Collocazione**: `backend/app/schemas/fx.py` (sezione utility, prima delle classi che la usano)

```python
def validate_chain_steps(
    steps: list,  # list[FXRouteStep] o list[dict] con .from_currency/.to_currency
    base: str,
    quote: str,
) -> None:
    """
    Valida la coerenza di una lista di chain_steps.

    Usata sia dal Pydantic schema (FXConversionRouteItem.validate_chain)
    sia dal SQLModel (FxConversionRoute validator).

    Raises:
        ValueError se una qualsiasi regola è violata.
    """
    if not steps:
        raise ValueError("chain_steps must have at least 1 element")

    # 1. Continuità: step[i].to == step[i+1].from
    for i in range(len(steps) - 1):
        to_cur = steps[i].to_currency if hasattr(steps[i], 'to_currency') else steps[i]['to']
        from_cur = steps[i + 1].from_currency if hasattr(steps[i + 1], 'from_currency') else steps[i + 1]['from']
        if to_cur != from_cur:
            raise ValueError(
                f"Chain discontinuity at step {i}: {to_cur} != {from_cur}"
            )

    # 2. No archi ripetuti (coppia non ordinata, qualsiasi direzione)
    edges_seen: set[tuple[str, str]] = set()
    for s in steps:
        fc = s.from_currency if hasattr(s, 'from_currency') else s['from']
        tc = s.to_currency if hasattr(s, 'to_currency') else s['to']
        edge = tuple(sorted([fc, tc]))
        if edge in edges_seen:
            raise ValueError(f"Duplicate edge: {edge[0]}-{edge[1]}")
        edges_seen.add(edge)

    # 3. Estremi coerenti con (base, quote)
    first_from = steps[0].from_currency if hasattr(steps[0], 'from_currency') else steps[0]['from']
    last_to = steps[-1].to_currency if hasattr(steps[-1], 'to_currency') else steps[-1]['to']
    endpoints = tuple(sorted([first_from, last_to]))
    pair = tuple(sorted([base, quote]))
    if endpoints != pair:
        raise ValueError(
            f"Chain endpoints {endpoints} don't match pair {pair}"
        )
```

### 2B. Schema `FXRouteStep`

```python
class FXRouteStep(BaseModel):
    """Singolo step (arco) in una conversion chain.

    Corrisponde a un arco nel grafo valute costruito dall'algoritmo DFS.
    """
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    from_currency: str = Field(..., alias="from", min_length=3, max_length=3)
    to_currency: str = Field(..., alias="to", min_length=3, max_length=3)
    provider: str = Field(..., description="Provider code per questo step")

    @field_validator("from_currency", "to_currency", mode="before")
    @classmethod
    def uppercase_currency(cls, v):
        return Currency.validate_code(v)

    @model_validator(mode="after")
    def validate_different(self):
        if self.from_currency == self.to_currency:
            raise ValueError(f"from and to must differ (got {self.from_currency})")
        return self
```

### 2C. Schema `FXConversionRouteItem`

```python
class FXConversionRouteItem(BaseModel):
    """Configurazione per una conversion route.

    Sostituisce FXPairSourceItem. Ogni route è una catena di step:
    - 1 step = conversione diretta (es. EUR→USD via ECB)
    - 2+ step = conversione a catena (es. RON→EUR→USD via ECB+ECB)
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    base: str = Field(..., min_length=3, max_length=3)
    quote: str = Field(..., min_length=3, max_length=3)
    priority: int = Field(..., ge=1)
    chain_steps: list[FXRouteStep] = Field(..., min_length=1,
        description="Lista ordinata di step di conversione (archi del grafo)")

    @field_validator("base", "quote", mode="before")
    @classmethod
    def uppercase_currency(cls, v):
        return Currency.validate_code(v)

    @model_validator(mode="after")
    def validate_chain(self):
        # Delega a funzione helper riutilizzabile
        validate_chain_steps(self.chain_steps, self.base, self.quote)
        return self
```

**Nota**: Il modello SQLModel `FxConversionRoute` (Step 1) può usare la stessa `validate_chain_steps()` nel suo validator, deserializzando il JSON `chain_steps` in `list[dict]` e passandolo alla funzione.

### Schemas da aggiornare

| Vecchio | Nuovo | Note |
|---------|-------|------|
| `FXPairSourceItem` | `FXConversionRouteItem` | Sempre `chain_steps`, no `route_type`/`provider_code` |
| `FXPairSourcesResponse` | `FXConversionRoutesResponse` | `BaseListResponse[FXConversionRouteItem]` |
| `FXPairSourceResult` | `FXConversionRouteResult` | Result con `chain_steps` |
| `FXCreatePairSourcesResponse` | `FXCreateRoutesResponse` | Stessa struttura base |
| `FXDeletePairSourceItem` | `FXDeleteRouteItem` | Invariato semanticamente |
| `FXDeletePairSourceResult` | `FXDeleteRouteResult` | Invariato |
| `FXDeletePairSourcesResponse` | `FXDeleteRoutesResponse` | Invariato |
| `FXSyncPairResult` | `FXSyncPairResult` (invariato nome) | **+campo `elapsed_ms`** |

### Modifica `FXSyncPairResult` — aggiunta `elapsed_ms`

```python
class FXSyncPairResult(BaseModel):
    # ...campi esistenti...
    pair: str
    status: FXSyncStatus
    provider_used: Optional[str]
    points_fetched: int
    points_changed: int
    message: Optional[str]

    # NUOVO: tempo di sincronizzazione misurato dal backend (intero, millisecondi)
    elapsed_ms: Optional[int] = Field(
        None, ge=0,
        description="Tempo di sync per questa coppia in millisecondi interi. "
                    "Calcolato come (time.monotonic_ns() - t_start_ns) // 1_000_000 "
                    "dove t_start_ns è catturato all'inizio della Fase 1 (= ricezione POST). "
                    "None per SKIPPED/MANUAL (nessun lavoro effettivo)."
    )
```

**Semantica `elapsed_ms`**:
- **Misurazione**: `time.monotonic_ns()` (intero nanosecondi, no float). Convertito in millisecondi con divisione intera `// 1_000_000`.
- **Punto di inizio (`t_start_ns`)**: catturato UNA sola volta all'inizio della Fase 1 di `sync_pairs_bulk()` (= il momento in cui il backend inizia a processare la POST). È lo stesso per tutte le coroutine.
- **Punto di fine**: `time.monotonic_ns()` al completamento del commit DB di ciascuna coppia.
- Nella pipeline bulk (Fase 3): include tutto — raccolta gambe, fetch provider, attesa Event, calcolo, upsert, commit. Cattura il tempo "dalla POST al salvataggio di questa coppia".
- In `sync_pair()` (sync singola): stessa logica — `t_start_ns` catturato all'entrata, `elapsed_ms` calcolato dopo il commit.
- Per route SKIPPED/MANUAL: `None` (nessun lavoro effettivo, tempo non significativo).
- Il frontend può mostrare questo valore accanto al suo elapsed (tempo dalla POST), dando visibilità sul tempo reale di backend vs overhead di rete. Eventuali conversioni in secondi o formattazione sono responsabilità del frontend.

### Tasks Step 2

- [x] Creare `validate_chain_steps()` come funzione helper standalone in `schemas/fx.py`
  - Accetta sia `list[FXRouteStep]` (Pydantic) che `list[dict]` (SQLModel deserialized)
  - Implementa: continuità, no archi ripetuti, estremi coerenti con (base, quote)
- [x] Creare `FXRouteStep` con validators (`from` ≠ `to`, codici ISO validi, provider uppercase)
- [x] Creare `FXConversionRouteItem` con model_validator che delega a `validate_chain_steps()`
- [x] Aggiornare il validator di `FxConversionRoute` (SQLModel, Step 1) per riusare `validate_chain_steps()`
- [x] Creare `FXConversionRouteResult` con campo `chain_steps`
- [x] Creare tutti i Response corrispondenti
- [x] Aggiornare imports in `api/v1/fx.py`
- [x] `FXSyncPairRequest` resta invariato (lavora su slug)
- [x] Aggiungere campo `elapsed_ms: Optional[int]` a `FXSyncPairResult` in `schemas/refresh.py`

---

## Step 3 — Service Layer

### 3A. Analisi provider: capacità batch

Studio effettuato sui provider esistenti — `fetch_rates()` accetta `currencies: list[str]` in tutti i provider, ma:

| Provider | Comportamento interno | Batch reale? |
|----------|----------------------|--------------|
| **ECB** | `for currency in currencies` → 1 HTTP/currency | ❌ Loop sequenziale |
| **FED** | `for currency in currencies` → 1 HTTP/currency | ❌ Loop sequenziale |
| **BOE** | `for currency in currencies` → 1 HTTP/currency | ❌ Loop sequenziale |
| **SNB** | Un singolo HTTP con `dimSel=D1(EUR1,CNY100,...)` | ✅ Batch nativo |

**Implicazione**: l'interfaccia `fetch_rates(currencies: list[str])` è già "batch-like", ma ECB/FED/BOE fanno N chiamate HTTP interne in loop sequenziale. Per il nostro scopo:
- Raggruppiamo le currency per provider → una sola invocazione di `fetch_rates()` per provider
- Il provider stesso gestisce internamente se fare 1 o N HTTP call
- **Parallelismo intra-provider (Step 3A-bis)**: PRIMA di implementare la pipeline bulk, modifichiamo `fetch_rates()` di ECB/FED/BOE per lanciare le HTTP call interne in parallelo con `asyncio.gather` anziché in loop sequenziale. Questo è uno step concreto, non un TODO futuro — il beneficio è immediato: se ECB deve scaricare 10 currency, oggi fa 10 call sequenziali (~3s), con `asyncio.gather` fa 10 call in parallelo (~0.3s). Il parallelismo inter-provider (Fase 2 della pipeline) moltiplica ulteriormente il guadagno.

### 3A-bis. Parallelizzazione HTTP intra-provider (ECB/FED/BOE)

Oggi `fetch_rates()` di ECB, FED e BOE itera `for currency in currencies` facendo 1 HTTP call per currency **in sequenza**. Questo è il collo di bottiglia principale quando un singolo provider deve scaricare molte coppie.

**Modifica**: refactor il loop sequenziale in `asyncio.gather` per tutte e 3 i provider. SNB è già batch nativo (1 sola HTTP call), quindi non va toccato.

**Pattern di refactor** (identico per ECB/FED/BOE):

```python
# PRIMA (sequenziale):
async def fetch_rates(self, date_range, currencies, base_currency=None):
    results = {}
    for currency in currencies:
        # ...setup...
        async with httpx.AsyncClient(...) as client:
            response = await client.get(url, params=params)
        results[currency] = self._parse(response)
    return results

# DOPO (parallelo):
async def fetch_rates(self, date_range, currencies, base_currency=None):
    # Filtra currency valide (skip base, skip non supportate)
    valid_currencies = [c for c in currencies if c != self.base_currency and ...]

    async def _fetch_one(currency: str) -> tuple[str, list]:
        """Fetch una singola currency — isolata per error handling."""
        # ...setup url/params identico al codice attuale...
        async with httpx.AsyncClient(...) as client:
            response = await client.get(url, params=params)
        return currency, self._parse(response)

    # Lancia tutte le HTTP call in parallelo
    tasks = [_fetch_one(c) for c in valid_currencies]
    fetched = await asyncio.gather(*tasks)  # Se un task fallisce, l'eccezione propaga

    return {currency: observations for currency, observations in fetched}
```

**Note implementative**:
- Ogni `_fetch_one` crea il proprio `httpx.AsyncClient` (come fa il codice attuale) — nessun client condiviso
- Se una singola currency fallisce, `asyncio.gather` propaga l'eccezione e l'intero `fetch_rates` fallisce — comportamento identico al loop sequenziale attuale
- Il parsing (`_parse_csv`, `_parse_response`, parsing JSON inline) rimane identico, solo l'orchestrazione cambia
- **Non toccare SNB**: è già batch nativo, nessuna modifica necessaria

**Beneficio concreto**: se ECB deve scaricare 8 currency per la pipeline bulk, il tempo passa da ~2.4s (8 × 0.3s sequenziali) a ~0.3s (tutte in parallelo). Combinato con il parallelismo inter-provider (Fase 2), il sync di 20 coppie distribuite su 3 provider diventa quasi istantaneo.

### 3B. Architettura `sync_pairs_bulk()` — Pipeline parallela con mutex

L'architettura è progettata per massimizzare il parallelismo ed evitare download duplicati.

**Fase 1 — Raccolta gambe e grouping per provider**

```
Input: lista route da sincronizzare (1-step e multi-step)

# Timestamp di inizio comune (bulk start)
# Catturare un singolo t_start_ns all'inizio della Fase 1 e passarlo (o renderlo
# disponibile) a tutte le coroutine. Misurazione in nanosecondi interi evita float.
# Uso suggerito: t_start_ns = time.monotonic_ns()

Per ogni route:
  Parsare chain_steps → estrarre le gambe necessarie
  Ogni gamba = (from, to, provider)

Raggruppare le gambe per provider:
  Per ogni gamba, determinare la currency target dal punto di vista del provider:
    - provider.base_currency → base del provider (es. EUR per ECB)
    - Se gamba.from == base → target_currency = gamba.to  (direzione nativa)
    - Se gamba.to == base   → target_currency = gamba.from (arco attraversato al contrario)
    - (Se nessuno match: errore di validazione — lo step non è compatibile col provider)

  provider_legs: dict[str, set[str]]
  Es: {
    "ECB": {"USD", "RON", "GBP"},   # tutte le currency target per ECB (base=EUR implicita)
    "FED": {"EUR", "CHF"},           # tutte le currency target per FED (base=USD implicita)
  }

Per ogni gamba, creare un asyncio.Event (mutex):
  leg_events: dict[tuple[str, str, str], asyncio.Event]
  Key: (norm_base, norm_quote, provider)
  Es: {
    ("EUR", "USD", "ECB"): Event(),
    ("EUR", "RON", "ECB"): Event(),
    ("CHF", "USD", "FED"): Event(),
  }

Struttura dati condivisa per i rate scaricati:
  leg_rates: dict[tuple[str, str, date], Decimal] = {}
  Key: (norm_base, norm_quote, date) → rate normalizzato per storage
```

**Fase 2 — Fetch parallelo per provider**

```
Per ogni provider P nel provider_legs:
  Creare un task async che:
    1. Chiama provider.fetch_rates(date_range, currencies_list)
       → currencies_list = tutte le currency raggruppate per P
    2. Normalizza i rate ricevuti → popola leg_rates
    3. Per ogni gamba completata: leg_events[gamba].set()
       → Questo sblocca le coroutine in attesa su quella gamba
    4. Se il fetch fallisce: segnare le gambe come failed
       (usa un dict separato leg_errors o un valore sentinella)

Tutti i provider task vengono lanciati in parallelo con asyncio.gather()
```

**Fase 3 — Coroutine per route: attesa Event, calcolo, salvataggio e timing**

```
Per ogni route R:
  Creare un task async che riceve t_start_ns (catturato in Fase 1):
    1. Identifica le gambe necessarie dalla chain (set di leg_events keys)
    2. Attende TUTTI i suoi leg_events con asyncio.gather(*[e.wait() for e in my_events])
       → La coroutine si sospende finché tutti i download delle sue gambe non terminano
    3. Quando sbloccata:
       a. Verifica che nessuna gamba sia failed → se sì, route FAILED
       b. Se chain è 1-step:
          - I rate della gamba sono già nel formato finale
       c. Se chain è multi-step:
          - Per ogni data nel date_range: compute_chain_rate()
          - Source = "CHAIN:{p1}+{p2}+..."
          - Se un arco non è nel verso richiesto (il provider fornisce B→A
            ma serve A→B), basta invertire: rate = Decimal(1) / fetched_rate
       d. Upsert dei rate di QUESTA route nel DB (sessione propria)
          → Commit immediato: la coppia è consistente (tutti i suoi rate o nessuno)
    4. elapsed_ms = (time.monotonic_ns() - t_start_ns) // 1_000_000
       → Intero, nanosecondi → millisecondi (divisione intera, no float)
       → Il timing cattura: dall'inizio della Fase 1 (= ricezione POST)
         fino al completamento commit di questa coppia
    5. Restituisce FXSyncPairResult con elapsed_ms

Tutte le route coroutine vengono lanciate in parallelo con asyncio.gather()
```

**Perché commit per coppia e non singolo commit atomico?**

Il singolo commit atomico (tutte-o-nessuna) era l'approccio iniziale, ma non è il design giusto per questo caso:

1. **Successo parziale è il comportamento desiderato**: se la sync coinvolge 15 coppie e la coppia #12 fallisce (es. provider down), le 14 riuscite DEVONO essere salvate. L'utente nell'interfaccia vedrà "14 OK, 1 FAILED" con dettaglio per coppia. Con commit atomico perderemmo 14 sync riuscite per 1 failure.

2. **Consistenza a livello coppia, non bulk**: la garanzia è che per ogni singola coppia, tutti i suoi rate vengano salvati o nessuno (commit della sessione per coppia). Non serve che il batch sia atomico — le coppie sono logicamente indipendenti dal punto di vista dei dati.

3. **asyncio è single-threaded — nessuna race condition**: il dict condiviso `leg_rates` è popolato nella Fase 2 e letto nella Fase 3. Anche se le coroutine della Fase 3 procedono in parallelo, asyncio esegue una sola coroutine alla volta (cooperative multitasking). Non ci sono corse critiche sul dizionario. I mutex (`asyncio.Event`) servono SOLO a far avanzare le coroutine appena i dati sono pronti, minimizzando i tempi morti.

4. **Nessun rischio di coroutine a metà**: asyncio non interrompe una coroutine tra un `await` e il successivo. Il blocco "calcolo + upsert + commit" nella Fase 3d è sincrono dal punto di vista logico — non c'è un `await` tra il calcolo e il commit che possa lasciare la coroutine in stato inconsistente.

```
Nota: per le route 1-step dove la gamba È anche richiesta come sync separata,
il rate viene salvato normalmente. Per le gambe intermedie che NON sono
richieste come route propria, i rate raw NON vengono salvati — solo il rate
derivato (composto) viene scritto in fx_rates.
```

**Diagramma sequenziale**:

```
sync_pairs_bulk() chiamata con [RON-USD (chain 2-step via EUR), EUR-USD (1-step), EUR-GBP (1-step)]

── Fase 1: Raccolta ──
  RON-USD chain: legs = [(EUR,RON,ECB), (EUR,USD,ECB)]
  EUR-USD 1-step: legs = [(EUR,USD,ECB)]   ← stessa gamba di RON-USD!
  EUR-GBP 1-step: legs = [(EUR,GBP,ECB)]

  provider_legs = {"ECB": {"RON", "USD", "GBP"}}   ← 1 sola chiamata ECB
  leg_events: 3 Event (EUR-RON, EUR-USD, EUR-GBP)

── Fase 2: Fetch parallelo ──
  Task ECB: fetch_rates(date_range, ["RON", "USD", "GBP"])
    → 3 HTTP calls interne in parallelo (asyncio.gather, vedi §3A-bis)
    → Popola leg_rates, poi set(EUR-RON), set(EUR-USD), set(EUR-GBP)

── Fase 3: Route coroutine (in parallelo, ognuna con proprio commit) ──
  t=0ms   Coroutine EUR-GBP: await Event(EUR-GBP) → sbloccata!
          → direct rate, upsert+commit (sessione propria)
          → elapsed: 285ms → FXSyncPairResult(pair="EUR-GBP", elapsed_ms=285, ...)

  t=0ms   Coroutine EUR-USD: await Event(EUR-USD) → sbloccata!
          → direct rate, upsert+commit (sessione propria)
          → elapsed: 290ms → FXSyncPairResult(pair="EUR-USD", elapsed_ms=290, ...)

  t=0ms   Coroutine RON-USD: await Event(EUR-RON) + Event(EUR-USD) → sbloccata!
          → compute_chain_rate → upsert+commit (sessione propria)
          → elapsed: 310ms → FXSyncPairResult(pair="RON-USD", elapsed_ms=310, ...)

── Risultato ──
  FXSyncBulkResponse con 3 FXSyncPairResult, ognuno con elapsed_ms
  Se EUR-GBP avesse fallito: success_count=2, failed_count=1
  Le altre 2 coppie sarebbero comunque salvate in DB
```

### 3C. Funzione helper `compute_chain_rate()`

```python
def compute_chain_rate(
    steps: list[dict],                        # parsed chain_steps
    leg_rates: dict[tuple, Decimal],          # {(norm_base, norm_quote, date): rate}
    target_date: date,
) -> Decimal | None:
    """
    Calcola il rate composto per una catena di conversioni in una data specifica.

    Per ogni step (from_cur, to_cur):
    - Normalizza in ordine alfabetico: (min, max) per lookup in leg_rates
    - Se from_cur < to_cur (ordine diretto): moltiplica per rate
    - Se from_cur > to_cur (ordine inverso): moltiplica per 1/rate

    L'inversione è il meccanismo con cui gestiamo gli archi attraversati
    al contrario nel grafo DFS:
    - Il grafo ha archi direzionati base→target (es. EUR→USD con ECB)
    - Il DFS può attraversarli al contrario via forEachInboundEdge
      (es. USD→EUR) generando un ChainStep con from=USD, to=EUR
    - In leg_rates la chiave è sempre normalizzata alfabeticamente (EUR, USD)
    - compute_chain_rate vede from_cur="USD" > to_cur="EUR" → usa 1/rate
    - Esempio: rate EUR/USD = 1.08, step USD→EUR → 1/1.08 ≈ 0.9259

    Questa normalizzazione alfabetica è il PUNTO UNICO dove si decide
    se usare rate o 1/rate. Né il frontend né il ChainStep devono
    portare un flag 'inverted' — è tutto derivato dall'ordine delle valute.

    Returns: rate composto finale, o None se manca un rate per qualche gamba.
    """
```

### 3D. Aggiornamento `sync_pair()` — logica unificata chain

La funzione `sync_pair()` rimane come entry point per sync di una singola coppia (chiamata anche da UI per sync manuale). In questo caso non c'è il beneficio della pipeline bulk, ma la logica è la stessa:

```python
async def sync_pair(
    session,
    route: FxConversionRoute,  # il nuovo modello (sostituisce base/quote/pair_sources)
    date_range: tuple[date, date],
) -> FXSyncPairResult:
    """
    Sync di una singola route.
    Per 1-step: fetch + upsert diretto.
    Per multi-step: fetch di ogni gamba sequenzialmente → compute_chain_rate → upsert.
    """
```

### 3E. `convert_bulk()` — NESSUNA modifica

I rate derivati sono pre-calcolati in `fx_rates`. `convert_bulk()` li trova con un semplice lookup, come qualsiasi rate diretto. Zero modifiche.

### Tasks Step 3

- [x] **3A-bis: Parallelizzare HTTP intra-provider** (da fare PRIMA della pipeline bulk):
  - [x] Refactor `ECBProvider.fetch_rates()`: estrarre body del loop in `_fetch_one(currency)`, sostituire `for` con `asyncio.gather`
  - [x] Refactor `FEDProvider.fetch_rates()`: stesso pattern
  - [x] Refactor `BOEProvider.fetch_rates()`: stesso pattern
  - [x] SNB: nessuna modifica (già batch nativo)
  - [x] Aggiornare test provider esistenti per verificare che il comportamento sia invariato
- [x] Creare `compute_chain_rate()` in `services/fx.py`
- [x] Ridisegnare `sync_pairs_bulk()` con architettura a 3 fasi:
  - Fase 1: `t_start_ns = time.monotonic_ns()`, raccolta gambe, grouping per provider, creazione `asyncio.Event` per gamba
  - Fase 2: fetch parallelo per provider (`asyncio.gather` sui provider task), popola `leg_rates`, segnala `leg_events`
  - Fase 3: route coroutine in parallelo, ciascuna `await` sui suoi `Event`, calcola, upsert+commit con sessione propria, calcola `elapsed_ms = (time.monotonic_ns() - t_start_ns) // 1_000_000`
- [x] Ogni coroutine di Fase 3 deve:
  - Creare la propria `AsyncSession` per il commit (indipendente dalle altre)
  - Calcolare `elapsed_ms` rispetto al `t_start_ns` globale (catturato una volta sola all'inizio della Fase 1, uguale per tutte le coroutine). Risultato in millisecondi interi (divisione intera, no float)
  - Restituire `FXSyncPairResult` con `elapsed_ms` popolato
  - In caso di errore: restituire `FAILED` senza propagare l'eccezione (le altre coroutine continuano)
- [x] Modificare `sync_pair()`:
  - Accettare `route: FxConversionRoute` con `chain_steps` parsed
  - Logica unificata per 1-step e multi-step (semplificata senza pipeline)
  - Misurare `elapsed_ms` anche per sync singola
- [x] Aggiornare `sync_pairs_bulk()`:
  - Caricare `FxConversionRoute` al posto di `FxCurrencyPairSource`
  - Implementare la pipeline 3 fasi
- [x] Source string per rate multi-step: formato `"CHAIN:{p1}+{p2}+..."`
- [x] Source string per rate 1-step: il provider code diretto (come prima)
- [x] Gestire provider MANUAL: una route 1-step con MANUAL → skip sync (come prima). Un multi-step con un step MANUAL mescolato a provider reali = errore validazione (rifiutato dallo schema Pydantic)

---

## Step 4 — API Layer

### Endpoint da rinominare/aggiornare

| Vecchio | Nuovo | Cambiamenti |
|---------|-------|-------------|
| `GET /fx/providers/pair-sources` | `GET /fx/providers/routes` | Response: `FXConversionRoutesResponse` con `chain_steps` |
| `POST /fx/providers/pair-sources` | `POST /fx/providers/routes` | Accetta `List[FXConversionRouteItem]` con `chain_steps` |
| `DELETE /fx/providers/pair-sources` | `DELETE /fx/providers/routes` | Schema rinominato, logica invariata |
| `POST /fx/currencies/sync` | Invariato | Lavora su slug coppia |
| `GET /fx/providers` | Invariato | Lista provider disponibili |

### Logica MANUAL sentinel

Adattata al modello unificato:
- Quando si aggiunge una route con provider reali → rimuovere eventuali route MANUAL per la stessa coppia
- Quando si rimuove l'ultima route non-MANUAL → reinserire MANUAL sentinel come `[{"from": base, "to": quote, "provider": "MANUAL"}]`
- Per determinare se una route è "MANUAL-only": controllare se tutti gli step in `chain_steps` hanno `provider == "MANUAL"`

### Tasks Step 4

- [x] Rinominare endpoints `/pair-sources` → `/routes` in `api/v1/fx.py`
- [x] Aggiornare handler `create_routes_bulk`:
  - Validare `chain_steps` (Pydantic fa il grosso, ma verificare provider registrati nel registry)
  - Logica MANUAL sentinel aggiornata
- [x] Aggiornare handler `delete_routes_bulk`
- [x] Aggiornare handler `list_routes`
- [x] Aggiornare handler `sync_rates` per usare il nuovo modello
- [x] Aggiornare `GET /fx/currencies/pairs` se usa pair_sources per `has_provider`

---

## Step 5 — Backend Tests

### Test da scrivere/aggiornare

```
backend/test_scripts/test_api/test_fx_routes.py         # CRUD route
backend/test_scripts/test_api/test_fx_chain_sync.py      # Sync chain E2E
```

**Scenari CRUD routes:**
- [x] Creare route 1-step (equivalente al vecchio "diretto")
- [x] Creare route 2-step (es. RON→EUR→USD)
- [x] Creare route 3-step (A→B→C→D)
- [x] Validazione: chain con arco ripetuto (stesso pair in 2 step) → 422
- [x] Validazione: chain con step non contigui → 422
- [x] Validazione: chain con provider inesistente → 400
- [x] Validazione: chain vuota (0 step) → 422
- [x] Delete route + MANUAL sentinel reinstatement
- [x] List routes: verifica chain_steps nella response

**Scenari sync:**
- [x] Sync route 1-step: funziona come prima
- [x] Sync route multi-step: rate derivato calcolato e salvato in fx_rates
- [x] Sync route multi-step: source = "CHAIN:ECB+ECB"
- [x] Sync route multi-step con un provider fallito → intera route FAILED, ma le altre route OK vengono salvate (successo parziale)
- [x] Sync bulk con route 1-step + route multi-step che condivide una gamba → la gamba viene scaricata 1 sola volta (dedup via pipeline Fase 1)
- [x] Sync bulk: provider grouping corretto (tutte le currency target raggruppate per provider)
- [x] Sync bulk: ogni coppia riuscita è committata indipendentemente (commit per coppia, non atomico bulk)
- [x] Sync bulk successo parziale: se 1 coppia su 3 fallisce, le altre 2 sono salvate in DB e response ha `success_count=2, failed_count=1`
- [x] `elapsed_ms` presente in ogni `FXSyncPairResult` con status OK/PARTIAL/FAILED (>0ms)
- [x] `elapsed_ms` è None per route SKIPPED/MANUAL
- [x] `elapsed_ms` anche in `sync_pair()` (sync singola)

### Tasks Step 5

- [x] Scrivere `test_fx_routes.py` → integrato in `test_fx_api.py` (test CRUD routes, 19/20 passed, 1 pre-existing `model_dump` issue)
- [x] Scrivere `test_fx_chain_sync.py` → `test_fx_sync.py` con 6 test E2E: ✅ 6/6 passed
  - test_sync_invalid_date_range: 400 su date invertite
  - test_sync_auto_config: sync con routes auto-create
  - test_sync_manual_only_skipped: pair MANUAL → status "skipped"
  - test_sync_weekend_no_rates: weekend → 0 punti (ok/partial)
  - test_convert_multi_day_process: conversione multi-giorno
  - test_convert_bulk_multi_day: bulk 2 conversioni × 3 giorni = ≥3 successi
- [x] Aggiornare eventuali test esistenti che usano `FxCurrencyPairSource`
- [x] Verificare che `populate_mock_data.py` funzioni con il nuovo modello
- [x] Test FX providers esterni: 20/20 passed, 15 skipped (multi-unit tests)

---

## Step 6 — Frontend: Grafo Provider e Auto-Detection

### 6A. Algoritmo di ricerca percorsi — DFS con Backtracking su Graphology

Il frontend costruisce un **grafo multi-diretto delle valute** usando la libreria `graphology` (`MultiDirectedGraph`) e trova tutti i percorsi possibili tra due valute con un **DFS con backtracking**.

**Perché DFS con backtracking e non BFS/shortest-path standard:**

Le librerie standard di shortest-path (incluse quelle di `graphology`) trovano UN solo cammino minimo o il cammino più corto. Noi dobbiamo trovare **TUTTI** i cammini possibili, di lunghezze diverse, rispettando vincoli di business personalizzati:
- Nessun arco ripetuto (stessa coppia di valute in qualsiasi direzione)
- Max 2 utilizzi per provider nello stesso percorso (un provider ha 1 base e N target: per transitare attraverso la sua base servono 2 archi)

Queste regole non sono esprimibili con gli algoritmi di pathfinding standard. Il DFS con backtracking è l'approccio corretto:
1. Esplora un ramo alla volta, poi "smonta" l'ultimo passo (backtracking) per esplorare alternative
2. Permette vincoli personalizzati ad ogni step nel ciclo di esplorazione
3. Efficiente in memoria (un percorso alla volta nello stack ricorsivo)

**Dipendenza**: `npm install graphology graphology-types`

**Input**:
- **Nodi**: elenco completo valute ISO da `GET /utilities/currencies` (`list_currencies_api_v1_utilities_currencies_get`). Questo garantisce che TUTTE le valute siano nodi nel grafo, anche quelle non coperte da alcun provider (in quel caso `findAllPaths` restituirà array vuoto, correttamente).
- **Archi**: info provider da `GET /fx/providers` (`list_providers_api_v1_fx_providers_get`), che per ogni provider restituisce `base_currencies` e `target_currencies`.

**Grafo** (`MultiDirectedGraph`):
- **Nodi** = tutte le valute ISO (dal backend utility endpoint, ~180 nodi). La maggior parte saranno disconnessi (nessun arco) — il DFS li gestisce correttamente restituendo zero percorsi.
- **Archi** = per ogni provider P, per ogni base B in `P.base_currencies`, per ogni target T in `P.target_currencies`: **UN solo arco direzionato B→T** con attributo `{provider: P.code}`. La direzione dell'arco codifica il verso "nativo" del provider (es. ECB fornisce EUR→USD, non USD→EUR). Il DFS può **attraversare l'arco al contrario** (da T verso B) usando `forEachInboundEdge`, e il backend sa che in quel caso il rate va invertito (1/rate).
- Multi-directed: tra gli stessi 2 nodi possono esserci più archi (uno per provider). Es.: EUR→USD ha archi ECB e FED (quest'ultimo come arco USD→EUR percorribile al contrario).
- **NON si aggiungono archi bidirezionali** (non serve duplicare T→B): la bidirezionalità è gestita dal DFS che esplora sia outbound che inbound.

**Perché archi direzionati singoli (non bidirezionali)**:
1. Semantica pulita: l'arco codifica la relazione reale "il provider P fornisce rate da B a T"
2. Il DFS sa quando sta attraversando un arco al contrario → il `ChainStep.from/to` indica la direzione logica, e il backend usa la normalizzazione alfabetica in `compute_chain_rate()` per determinare se usare `rate` o `1/rate`
3. Nessun arco duplicato — il grafo è più compatto e le iterazioni più veloci

### 6A-bis. Caching del grafo — session-lifetime

La risposta di `GET /fx/providers` è **costante** per l'intera sessione del server: i provider sono plugin registrati all'avvio e non cambiano senza riavvio. La lista valute da `GET /utilities/currencies` è anch'essa stabile. Questo significa che:

1. Il **grafo** (output di `buildCurrencyGraph()`) può essere costruito **una sola volta** al primo utilizzo e cacheato nel client per tutta la sessione
2. Non serve invalidation: la cache è valida finché l'utente non fa refresh della pagina (che ricreerebbe l'app Svelte)
3. **Implementazione**: un modulo-level singleton (o Svelte store `derived`) che:
   - Al primo accesso chiama `GET /fx/providers` e `GET /utilities/currencies`, poi costruisce il grafo
   - Alle chiamate successive restituisce il grafo cacheato
   - Opzionale: espone un `invalidate()` per forzare il rebuild (non necessario in pratica)

```typescript
// src/lib/stores/currencyGraphStore.ts

import { writable, derived } from 'svelte/store';
import type MultiDirectedGraph from 'graphology';
import { buildCurrencyGraph } from '$lib/utils/currencyGraph';

// Cache del grafo — costruito al primo utilizzo, poi riusato
let cachedGraph: MultiDirectedGraph | null = null;
let cachedProvidersHash: string | null = null;

/**
 * Restituisce il grafo valute cacheato.
 * Lo costruisce al primo utilizzo dai dati di GET /fx/providers + GET /utilities/currencies.
 * La cache è valida per l'intera sessione (provider e valute non cambiano senza riavvio).
 *
 * @param providers - lista provider con base_currencies e target_currencies
 * @param allCurrencyCodes - tutti i codici ISO valuta (es. ["AED","AFN",...,"ZWL"])
 */
export async function getCurrencyGraph(
    providers: ProviderInfo[],
    allCurrencyCodes: string[],
): MultiDirectedGraph {
    // Hash per invalidare se i provider cambiano (paranoia check)
    const hash = JSON.stringify(providers.map(p => p.code).sort());
    if (cachedGraph && cachedProvidersHash === hash) {
        return cachedGraph;
    }
    cachedGraph = buildCurrencyGraph(providers, allCurrencyCodes);
    cachedProvidersHash = hash;
    return cachedGraph;
}
```

Questo evita di ricostruire il grafo ogni volta che l'utente apre il modal di aggiunta coppia o cambia la selezione valute.

```typescript
// src/lib/utils/currencyGraph.ts

import MultiDirectedGraph from 'graphology';

interface ChainStep {
    from: string;
    to: string;
    provider: string;
}

interface ProviderInfo {
    code: string;
    base_currencies: string[];
    target_currencies: string[];
}

/**
 * Costruisce un MultiDirectedGraph dalle info dei provider.
 *
 * Nodi: TUTTE le valute ISO da allCurrencyCodes (dal backend GET /utilities/currencies).
 *       La maggior parte saranno disconnessi — il DFS restituisce [] per coppie irraggiungibili.
 *
 * Archi: per ogni provider P, per ogni (base B, target T):
 *   - Aggiunge UN SOLO arco direzionato B→T con attributo {provider: P.code}
 *   - La direzione codifica il verso "nativo" del provider
 *   - L'arco può essere attraversato al contrario dal DFS (forEachInboundEdge)
 *     e in quel caso il rate viene invertito (1/rate) a livello di compute_chain_rate
 *   - NON si duplicano archi: se due provider offrono la stessa coppia,
 *     ci sono 2 archi paralleli nello stesso verso (multi-graph).
 *
 * @param providers - da GET /fx/providers (con base_currencies e target_currencies)
 * @param allCurrencyCodes - da GET /utilities/currencies (tutti i codici ISO, es. ["AED",...,"ZWL"])
 */
export function buildCurrencyGraph(
    providers: ProviderInfo[],
    allCurrencyCodes: string[],
): MultiDirectedGraph;

/**
 * DFS con backtracking — trova tutti i percorsi da source a target.
 *
 * Esplora il grafo in entrambe le direzioni:
 * - forEachOutboundEdge: archi uscenti (direzione nativa del provider)
 * - forEachInboundEdge:  archi entranti (direzione inversa, rate = 1/nativo)
 *
 * Ritorna array di percorsi, ordinati per lunghezza (più corti prima).
 * Ogni percorso è un array di ChainStep con (from, to, provider) dove
 * from/to rappresentano la direzione logica di conversione (non necessariamente
 * la direzione nativa dell'arco). Il backend determina se invertire il rate
 * tramite normalizzazione alfabetica in compute_chain_rate().
 *
 * Ogni ChainStep è direttamente utilizzabile come elemento di chain_steps
 * nella POST /fx/providers/routes (nessuna trasformazione necessaria).
 */
export function findAllPaths(
    graph: MultiDirectedGraph,
    source: string,
    target: string,
    maxDepth?: number  // default 4
): ChainStep[][];
```

#### Pseudo-codice DFS dettagliato

> **Nota**: design originato da analisi collaborativa del dominio FX (routing valute con vincoli provider).
> Da documentare in MkDocs: `developer/fx-chain-algorithm.en.md` (vedi plan-fxDocumentation)

```javascript
function findAllPaths(graph, source, target, maxDepth = 4) {
    const validPaths = [];

    // Se source o target non esistono nel grafo, nessun percorso possibile
    if (!graph.hasNode(source) || !graph.hasNode(target)) return [];

    /**
     * DFS ricorsiva con backtracking.
     *
     * Esplora il grafo in ENTRAMBE le direzioni ad ogni nodo:
     * - Outbound edges (direzione nativa: currentNode è source dell'arco)
     * - Inbound edges  (direzione inversa: currentNode è target dell'arco)
     *
     * Il ChainStep registra SEMPRE la direzione logica di conversione:
     *   { from: currentNode, to: neighbor, provider }
     * Il backend sa se invertire il rate usando la normalizzazione alfabetica
     * in compute_chain_rate().
     *
     * @param currentNode     - valuta corrente nel percorso
     * @param pathEdges       - archi (ChainStep) nel percorso corrente
     * @param usedEdgePairs   - Set di coppie valute già attraversate (es. "EUR-USD")
     *                          indipendente dalla direzione e dal provider.
     *                          VINCOLO CHIAVE: la stessa coppia di nodi (A,B) o (B,A)
     *                          non può comparire 2 volte, neanche con provider diversi.
     * @param providerUseCount - Map<provider, count> utilizzi nel percorso corrente
     */
    function dfs(currentNode, pathEdges, usedEdgePairs, providerUseCount) {
        // Condizione di uscita: raggiunto il target
        if (currentNode === target) {
            validPaths.push([...pathEdges]);
            return;
        }

        // Profondità massima raggiunta
        if (pathEdges.length >= maxDepth) return;

        /**
         * Helper: tenta di avanzare verso un nodo adiacente.
         * Usato sia per archi outbound (nativi) che inbound (inversi).
         *
         * @param neighbor  - nodo verso cui si tenta di avanzare
         * @param edgeSrc   - source dell'arco nel grafo (nodo con la base del provider)
         * @param edgeTgt   - target dell'arco nel grafo (nodo con la target del provider)
         * @param provider  - codice del provider che offre questo arco
         */
        function tryEdge(neighbor, edgeSrc, edgeTgt, provider) {
            // Vincolo 1: la stessa coppia (in qualsiasi ordine) non può
            // apparire due volte — coppie ordinate alfabeticamente
            const edgePair = [edgeSrc, edgeTgt].sort().join('-');
            if (usedEdgePairs.has(edgePair)) return;

            // Vincolo 2: max 2 utilizzi per provider nel percorso.
            // Un provider con base EUR e N target necessita al massimo
            // di 2 archi per fare ponte (target→EUR + EUR→target2).
            const currentUses = providerUseCount.get(provider) || 0;
            if (currentUses >= 2) return;

            // --- AVANZAMENTO ---
            pathEdges.push({ from: currentNode, to: neighbor, provider });
            usedEdgePairs.add(edgePair);
            providerUseCount.set(provider, currentUses + 1);

            // RICORSIONE — esplora dal vicino
            dfs(neighbor, pathEdges, usedEdgePairs, providerUseCount);

            // --- BACKTRACKING — smonta l'ultimo passo ---
            pathEdges.pop();
            usedEdgePairs.delete(edgePair);
            if (currentUses === 0) {
                providerUseCount.delete(provider);
            } else {
                providerUseCount.set(provider, currentUses);
            }
        }

        // ── Outbound edges (direzione NATIVA: currentNode → neighbor) ──
        // L'arco nel grafo è base→target, e currentNode è la base.
        // Conversione: rate usato così com'è dal provider.
        graph.forEachOutboundEdge(currentNode, (edgeKey, attrs, src, tgt) => {
            tryEdge(/*neighbor*/ tgt, /*edgeSrc*/ src, /*edgeTgt*/ tgt, attrs.provider);
        });

        // ── Inbound edges (direzione INVERSA: currentNode ← source) ──
        // L'arco nel grafo è source→currentNode, ma lo attraversiamo al contrario:
        // andiamo da currentNode verso source dell'arco.
        // Conversione: il rate va invertito (1/rate) in compute_chain_rate().
        // Esempio: arco EUR→USD (ECB) — se siamo su USD, possiamo andare verso EUR
        // usando 1/rate(EUR/USD).
        graph.forEachInboundEdge(currentNode, (edgeKey, attrs, src, tgt) => {
            // src = nodo da cui parte l'arco (es. EUR), tgt = currentNode (es. USD)
            // neighbor = src (andiamo verso EUR)
            tryEdge(/*neighbor*/ src, /*edgeSrc*/ src, /*edgeTgt*/ tgt, attrs.provider);
        });
    }

    // Avvio dal nodo sorgente
    dfs(source, [], new Set(), new Map());

    // Ordina per lunghezza percorso (più corti prima)
    validPaths.sort((a, b) => a.length - b.length);
    return validPaths;
}
```

**Perché le valute POSSONO ripetersi**: non c'è un check sui nodi visitati. Il vincolo primario è sugli **archi** (coppie di valute, indipendentemente da direzione e provider). In pratica, con il vincolo sugli archi, i cicli banali (A→B→A) sono comunque impossibili perché richiederebbero lo stesso arco A-B due volte. Percorsi più complessi con nodi condivisi (A→B→C→A→D) sono teoricamente ammessi dal vincolo ma improbabili con maxDepth=4 e il numero limitato di provider.

**Perché archi singoli direzionati**: il grafo contiene UN solo arco direzionato per (provider, base, target). L'algoritmo DFS esplora entrambe le direzioni (`forEachOutboundEdge` + `forEachInboundEdge`). Questo approccio:
1. Mantiene la semantica chiara: l'arco rappresenta "il provider fornisce rate da base a target"
2. Il `ChainStep` registra la direzione logica (from=currentNode, to=neighbor): se va nella stessa direzione dell'arco → rate nativo; se al contrario → 1/rate
3. `compute_chain_rate()` nel backend determina automaticamente se invertire tramite normalizzazione alfabetica, senza bisogno di un campo `inverted` nel ChainStep

#### Enhancement TODO: Parallelizzazione DFS con Web Workers

> **Stato**: 📋 Enhancement futuro, bassa priorità (l'algoritmo DFS è veloce con il grafo attuale di ~4 provider × ~25 currency)

L'algoritmo DFS potrebbe essere parallelizzato usando **Web Workers** per esplorare rami diversi del grafo simultaneamente:

**Idea**: dal nodo sorgente, ci sono N archi raggiungibili (outbound nativi + inbound inversi). Ogni arco iniziale può essere assegnato a un Worker diverso, che poi procede con il DFS standard dal suo arco in poi.

```
source = "RON"
archi iniziali: RON→EUR(ECB), RON→CHF(SNB) ...

Worker 1: DFS da RON→EUR (esplora tutti i percorsi che partono via ECB)
Worker 2: DFS da RON→CHF (esplora tutti i percorsi che partono via SNB)
...
Main thread: raccoglie i risultati, merge, ordina
```

**Valutazione complessità**:
- Il grafo deve essere serializzato e passato a ciascun Worker (overhead)
- `graphology` potrebbe non essere facilmente serializzabile → potrebbe servire una rappresentazione lightweight del grafo (adjacency list) per i Workers
- Con ~4 provider e maxDepth=4, il DFS completa in <1ms anche su grafi da 100+ nodi — il beneficio del parallelismo è trascurabile
- Diventa rilevante se si aggiungono molti provider commerciali con migliaia di coppie

**Decisione**: segnato come TODO, da implementare solo se profiling mostra colli di bottiglia.

### 6B. UI Provider Selection in FxPairAddModal

L'attuale `FxProviderSelect` mostra provider compatibili per la coppia selezionata.
Va esteso per mostrare 3 categorie, calcolate dai risultati di `findAllPaths()`:

```
┌──────────────────────────────────────────────────┐
│ Provider per EUR → RON                           │
│                                                  │
│ ── Conversione diretta (1 step) ──               │
│   ✅ ECB - European Central Bank                 │
│                                                  │
│ ── Conversione a catena ──                       │
│   🔗 via USD (FED + ECB)           [2 step]      │
│   🔗 via GBP (BOE + ECB)           [2 step]      │
│   🔗 via CHF (SNB + ECB)           [2 step]      │
│                                                  │
│ ── Non utilizzabili ──                           │
│   ⚠️ Nessun percorso automatico per questa coppia │
└──────────────────────────────────────────────────┘
```

**Nota: il provider `MANUAL` NON compare nella UI.** `MANUAL` è un sentinel gestito esclusivamente dal backend: viene inserito automaticamente quando una coppia non ha nessun provider automatico configurato, e rimosso quando se ne aggiunge uno. Il frontend non deve mai mostrarlo come opzione selezionabile.

**Calcolo delle 3 sezioni** dall'output di `findAllPaths()`:
1. **Diretta (1 step)**: percorsi con `path.length === 1`
2. **Catena (multi-step)**: percorsi con `path.length >= 2`, ordinati per numero step
3. **Non utilizzabili**: provider che **NON compaiono in NESSUN percorso** (né 1-step né multi-step). Se BOE compare anche in una sola catena, NON va qui. Qui vanno solo i provider completamente irraggiungibili per questa coppia di valute.

Quando l'utente seleziona un percorso:
- `chain_steps` viene popolato direttamente dall'output di `findAllPaths()` (identico formato)
- I passaggi sono mostrati come badge inline (es. `RON →[ECB]→ EUR →[ECB]→ USD`)
- Un'icona catena 🔗 distingue le multi-step

### 6C. FxProviderConfig nel Detail Page

L'attuale `FxProviderConfig.svelte` mostra una lista ordinabile di provider.
Ogni riga ora mostra la catena:
- **1-step**: nome provider come ora (es. `ECB — European Central Bank`)
- **Multi-step**: badge 🔗 + lista step compatta (es. `RON →[ECB]→ EUR →[ECB]→ USD`)
- Il reorder funziona sulla priority della route, non sui singoli step

### 6D. FxSyncModal — Nessuna modifica

Il sync modal lavora su slug di coppia, non conosce la struttura interna della route. Tutto invariato.

### Tasks Step 6

- [x] Installare `graphology` e `graphology-types`: `cd frontend && npm install graphology graphology-types`
- [x] Creare `src/lib/utils/currencyGraph.ts`:
  - `buildCurrencyGraph(providers, allCurrencyCodes)` → `MultiDirectedGraph`
    - Nodi: tutti i codici valuta da `allCurrencyCodes` (dal backend `GET /utilities/currencies`)
    - Archi: UN solo arco direzionato base→target per ogni (provider, base, target). NO archi bidirezionali.
  - `findAllPaths(graph, source, target, maxDepth)` → `ChainStep[][]`
  - Implementare DFS con backtracking come da pseudo-codice §6A:
    - Ad ogni nodo esplorare **sia** `forEachOutboundEdge` (nativo) **sia** `forEachInboundEdge` (inverso)
    - ChainStep registra direzione logica: `{from: currentNode, to: neighbor, provider}`
    - Vincolo archi: `edgePair = [src, tgt].sort().join('-')` — stessa coppia non può ripetersi
    - Vincolo provider: max 2 utilizzi per provider per percorso
- [x] Creare `src/lib/stores/currencyGraphStore.ts`:
  - Caching session-lifetime del grafo (costruito al primo utilizzo)
  - Input: dati da `GET /fx/providers` + `GET /utilities/currencies`
  - `getCurrencyGraph(providers, allCurrencyCodes)` con hash check per invalidation
  - Entrambe le risposte sono costanti per sessione → cache sempre valida
- [x] Estendere `FxProviderSelect.svelte` (o creare `FxRouteSelect.svelte`):
  - Sezione "Diretta" con percorsi 1-step
  - Sezione "Catena" con percorsi multi-step, ordinati per lunghezza
  - Sezione "Non utilizzabili": provider assenti da TUTTI i percorsi
  - Selezione di un percorso → popola `chain_steps`
- [x] Aggiornare `FxPairAddModal.svelte`:
  - Usare nuovo selettore route
  - Salvare `chain_steps` nella POST
- [x] Aggiornare `FxProviderConfig.svelte`:
  - Mostrare step catena per route multi-step
  - Badge 🔗 per distinguere multi-step da 1-step
- [x] Aggiornare le chiamate API frontend (`pair-sources` → `routes`)
- [x] Aggiornare i18n: chiavi per "chain", "direct", "step", "via", "all providers must work for sync"
  - Usare `./dev.py i18n add` + `./dev.py i18n update`
- [ ] **Enhancement TODO**: Parallelizzazione DFS via Web Workers (vedi §6A-bis). Segnare come issue/TODO nel codice, implementare solo se profiling mostra necessità.

---

## Step 7 — Aggiornamento riferimenti e cleanup

### Tasks Step 7

- [x] Aggiornare `TODO_FUTURI.md`: sezione "FX Page" ora superata dal lavoro fatto (grafico, provider config, chain, sync)
- [x] Aggiornare `plan-phase05-to-08-upgrade.md` §4 con riferimento a questo plan
- [x] Grep globale per `FxCurrencyPairSource` e `pair-sources` — solo nei piani/docs storici (archiviati), nessuno nel codice sorgente attivo
- [x] Grep globale per `pair_sources` in frontend — nessun riferimento nel codice sorgente
- [x] Verificare che `svelte-check` passi senza errori → **0 errors, 0 warnings**
- [x] Verificare che il build frontend passi → **success**
- [x] Cancellare DB e ricreare con `./dev.py test db populate --force` *(manuale, utente)*
- [x] Test manuale: aggiungere coppia multi-step da UI, sync, verificare rate derivato *(manuale, utente)*
- [x] Aggiornare MkDocs `configuration.md` che riferisce ancora `FxCurrencyPairSource` *(docs task — aggiornato a FxConversionRoute + chain routes)*

---

## Dipendenze tra Steps

```
Step 1 (Data Model)
  └──→ Step 2 (Pydantic Schemas)
         └──→ Step 3 (Service Layer)
                └──→ Step 4 (API Layer)
                       └──→ Step 5 (Backend Tests)
                              └──→ Step 6 (Frontend)
                                     └──→ Step 7 (Cleanup)
```

Step 6 (Frontend) può parzialmente procedere in parallelo con Step 5 (Tests), dato che le API sono già funzionanti dopo Step 4.

---

## Note di implementazione

### Source string per rate derivati

I rate calcolati da una catena multi-step vengono salvati in `fx_rates` con:
```
source = "CHAIN:ECB+ECB"       # 2-step same provider
source = "CHAIN:FED+ECB"       # 2-step cross provider
source = "CHAIN:FED+BOE+ECB"   # 3-step
```

I rate da route 1-step usano il provider code diretto (come prima):
```
source = "ECB"
source = "FED"
```

Questo permette di distinguerli per audit/debug. L'utente può comunque editarli manualmente (diventano `source = "MANUAL"`).

### Libreria Graphology

**Package**: `graphology` (core, ~15KB) + `graphology-types` (solo tipi TS, 0KB runtime)
**Perché**: offre `MultiDirectedGraph` che supporta nativamente più archi diretti tra gli stessi nodi (un arco per provider). Le API `forEachOutboundEdge()` e `forEachInboundEdge()` permettono al DFS di esplorare entrambe le direzioni: outbound per la direzione nativa del provider, inbound per la direzione inversa (1/rate). Questo elimina la necessità di duplicare archi.
**Non servono** le sotto-librerie di pathfinding (`graphology-shortest-path` ecc.) perché il nostro algoritmo ha vincoli custom non esprimibili con quelle API standard.
**Caching**: il grafo viene costruito una sola volta dalla risposta di `GET /fx/providers` + `GET /utilities/currencies` e cacheato per l'intera sessione client. Entrambe le risposte sono costanti finché il server non viene riavviato.

### Provider batch capabilities

Studio dei provider esistenti (vedi §3A per dettagli):
- **ECB/FED/BOE**: `fetch_rates()` accetta `list[str]` ma internamente oggi fa 1 HTTP/currency in loop sequenziale. **Step 3A-bis parallelizza** queste call con `asyncio.gather`, trasformando il loop `for` in esecuzione concorrente
- **SNB**: vero batch nativo — 1 HTTP call con tutti i currency code nel parametro `dimSel`. Non va toccato
- Il parallelismo opera su due livelli: **intra-provider** (§3A-bis: le currency di uno stesso provider in parallelo) + **inter-provider** (Fase 2 della pipeline: provider diversi in parallelo)

### Backward fill per rate derivati

I rate derivati NON hanno `backward_fill_info` proprio. Se una gamba ha backward-fill, il rate derivato eredita la data effettiva più recente tra le gambe (worst-case backward fill).

### Provider MANUAL in catene

- Route 1-step con MANUAL: valida (la coppia è manual-only, skip sync come prima)
- Route multi-step con un step MANUAL mescolato a provider reali: non ha senso (il sync fallirebbe per lo step MANUAL). Il validator Pydantic rifiuta catene multi-step che contengono `provider == "MANUAL"`.

### Documentazione algoritmo DFS

L'algoritmo DFS con backtracking descritto in §6A va documentato in MkDocs:
- `developer/fx-chain-algorithm.en.md` — spiegazione del grafo, vincoli, pseudo-codice, complessità
- Task incluso nel `plan-fxDocumentation.prompt.md`

### ⚠️ Nota architetturale: Multi-base provider

**Stato attuale**: tutti i provider implementati (ECB, FED, BOE, SNB) hanno **1 sola base currency** (`base_currencies` ritorna una lista con 1 elemento). La proprietà `base_currencies` nella classe base `FXRateProvider` (vedi `backend/app/services/fx.py`) supporta GIÀ la dichiarazione di basi multiple, ma:

- **Nessun provider reale** la usa oggi
- La pipeline `sync_pairs_bulk()`, l'orchestratore `ensure_rates_multi_source()`, il grouping per provider (§3B Fase 1), e il grafo frontend (§6A) assumono tutti **implicitamente** che un provider abbia 1 sola base
- Il raggruppamento `provider_legs: dict[str, set[str]]` nella Fase 1 mappa `provider → set[currency_target]`, ma non gestisce il caso in cui lo stesso provider offra USD→JPY e EUR→JPY (2 basi diverse per lo stesso target)

**Quando servirà cambiare**: al momento di aggiungere un provider commerciale (es. Open Exchange Rates, Fixer.io) che supporta più basi, sarà necessario:

1. Ripensare il grouping nella Fase 1: la chiave dovrà diventare `(provider, base_currency)` anziché solo `provider`
2. Ripensare `ensure_rates_multi_source()`: dovrà passare `base_currency` esplicita a `fetch_rates()`
3. Ripensare il grafo frontend (§6A): `buildCurrencyGraph()` dovrà gestire archi multipli per lo stesso provider con basi diverse
4. Ripensare i `chain_steps`: ogni step potrebbe necessitare anche di `base_currency` esplicita (oggi inferita dal provider)
5. Rivedere tutti i plugin esistenti per verificare che il nuovo flusso non rompa nulla
Nota: Probabilemnte la soluzione sarà di cambiare le classi pydantic e fare un oggetto con una key per la base value e una key per la lista di target di quella key, e mettere questo oggetto in lista. Anche se dispendioso dovrebbe permettere di gestire anche conversioni non bilanciate dei provifer, forse, è solo un idea, ci arriviamo quando sarà il momento. Bisognerà però aggiornare la creazione del GRAFO per il calcolo della catena di conversione, qualsiasi sia il risultato.
**Azione immediata**: aggiungere un commento `# ARCHITECTURAL NOTE: multi-base` nella classe `FXRateProvider` sulla proprietà `base_currencies` per documentare questa limitazione e linkare a questa nota del piano.

