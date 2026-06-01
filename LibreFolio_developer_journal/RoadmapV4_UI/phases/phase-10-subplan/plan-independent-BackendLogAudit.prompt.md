# Plan: Backend Log Level Reorganization

**Data**: 1 Giugno 2026
**Status**: ✅ DONE (2026-06-01)
**Priority**: P3 (cleanup — no breaking)
**Tipo**: Independent mini-plan (backend puro, no API change, no frontend, no transazioni)

## 🤖 Modello Suggerito & Effort

| Parametro | Valore |
|-----------|--------|
| **Modello** | `claude-sonnet-4.6` |
| **Effort stimato** | ~3-4h |
| **Difficoltà** | Bassa-Media |
| **Rationale** | Step 1-2 (policy + TRACE) sono chirurgici (~30 min). Step 3 (audit) è il grosso: richiede leggere decine di file, giudicare ogni `logger.*` call e decidere il livello corretto — richiede buon senso contestuale più che complessità tecnica. Sonnet per la fase di audit; un modello più veloce potrebbe sbagliare livello su edge case. |

---

## 🎯 Obiettivo

I livelli di log del backend sono cresciuti in modo organico e presentano inconsistenze.
Questo plan:
1. Definisce una policy di log livelli chiara e documentata
2. Registra formalmente il livello TRACE (5)
3. Fa un audit di tutti i `logger.*` nel backend e corregge i livelli incongruenti

**Zero breaking**: nessun cambio API, nessun cambio schema, nessun cambio frontend.

---

## Stato Attuale (code-verified 2026-06-01)

| Componente | Stato |
|---|---|
| `backend/app/logging_config.py` | ✅ Esiste — usa structlog + rotating file handler |
| Livello TRACE formale | ❌ Non registrato — `logger.log(5, ...)` crasha (`KeyError: 5` in structlog 25.5.0) |
| Policy livelli documentata | ❌ Non esiste |
| Log provider HTTP (httpx/httpcore) | ✅ Già silenziati (+ aiosqlite, sqlalchemy, yfinance, peewee) |
| Consistency livelli nel codebase | ⚠️ Diversi INFO da abbassare a DEBUG (fx_providers, cache_utils, etc.) |
| `logger.log(5,...)` calls esistenti | ✅ Zero — tutte le TRACE calls in Step 3 saranno nuove aggiunte |

---

## Step 1 — Definire e documentare la policy livelli ✅ (2026-06-01)

### Policy ufficiale LibreFolio

| Livello | Valore | Quando usarlo |
|---------|--------|--------------|
| `CRITICAL` | 50 | Il processo non può continuare, richiede intervento immediato |
| `ERROR` | 40 | Errore gestito ma significativo (operazione fallita, dato corrotto) |
| `WARNING` | 30 | Situazione anomala ma recuperabile (fallback attivato, dati mancanti) |
| `INFO` | 20 | Operazioni significative dell'utente: sync completata, import file, login, creazione risorsa |
| `DEBUG` | 10 | Dettagli operativi: provider usato, query SQL, risultati intermedi, decisioni algoritmiche |
| `TRACE` | 5 | Dati granulari massivi: singolo rate FX, singolo backward-fill, singolo punto storico |

**Regola pratica**:
- "L'utente ha fatto X" → INFO
- "Il sistema ha deciso X" → DEBUG
- "Il valore X per la data Y è Z" (ripetuto N volte) → TRACE

### Azione

Aggiungere all'inizio di `logging_config.py` il commento di policy:

```python
# ═══════════════════════════════════════════════════════════════════════════════
# LOG LEVEL POLICY — LibreFolio
# ═══════════════════════════════════════════════════════════════════════════════
# CRITICAL (50): process cannot continue, immediate intervention required
# ERROR    (40): handled error, operation failed or data corrupted
# WARNING  (30): anomaly but recoverable (fallback activated, missing data)
# INFO     (20): significant user operations (sync done, import, login, create)
# DEBUG    (10): operational details (provider used, SQL, intermediate results)
# TRACE    ( 5): high-frequency granular data (single rate, single data point)
#
# Practical rule:
#   "User did X"          → INFO
#   "System decided X"    → DEBUG
#   "Value X for date Y"  → TRACE (if repeated N times per operation)
# ═══════════════════════════════════════════════════════════════════════════════
```

---

## Step 2 — Registrare il livello TRACE formale ✅ (2026-06-01)

### ⚠️ Correzioni post-analisi (2026-06-01)

Due bug trovati nell'approccio originale:

**Bug #1**: `structlog 25.5.0` — `BoundLogger.log()` fa lookup diretto in `LEVEL_TO_NAME[level]`.
Il dict contiene solo `{50, 40, 30, 20, 10}` → `logger.log(5, ...)` lancia `KeyError: 5` a runtime.
**Fix**: aggiungere `5: "trace"` a `LEVEL_TO_NAME` + aggiungere `trace()` al stdlib Logger.

**Bug #2**: `getattr(logging, "TRACE", logging.INFO)` torna sempre INFO perché `addLevelName`
non aggiunge un attributo sul modulo `logging`.
**Fix**: aggiungere `logging.TRACE = TRACE` esplicitamente dopo la registrazione.

### Implementazione corretta

Aggiungere la costante **a livello di modulo** in `logging_config.py` (prima di `configure_logging`):

```python
# TRACE level constant (module-level so importable)
TRACE: int = 5
```

In `configure_logging()`, **come prima cosa** (prima di qualsiasi handler):

```python
# Register TRACE level (5) as a formal named level
logging.addLevelName(TRACE, "TRACE")
logging.TRACE = TRACE  # type: ignore[attr-defined]  # needed for getattr(logging, "TRACE")

# Add trace() method to stdlib Logger so structlog can dispatch it
if not hasattr(logging.Logger, "trace"):
    def _trace(self: logging.Logger, message: object, *args: object, **kwargs: object) -> None:
        if self.isEnabledFor(TRACE):
            self._log(TRACE, message, args, **kwargs)  # type: ignore[arg-type]
    logging.Logger.trace = _trace  # type: ignore[attr-defined]

# Register level 5 in structlog's dispatch table
import structlog.stdlib as _structlog_stdlib
if TRACE not in _structlog_stdlib.LEVEL_TO_NAME:
    _structlog_stdlib.LEVEL_TO_NAME[TRACE] = "trace"
```

Uso nel codice applicativo:
```python
logger.log(5, "message")   # ✅ ora funziona, mostra level="TRACE"
# oppure, dopo questa configurazione:
# logger.trace("message")  # non disponibile via structlog BoundLogger direttamente
```

> **Nota**: `logger.log(5, "msg")` ora funziona. Il processor `add_log_level` riceve
> `method_name="trace"` → `level = "TRACE"` nel JSON. `LOG_LEVEL=TRACE` parsa
> correttamente perché `getattr(logging, "TRACE")` restituisce 5.

---

## Step 3 — Audit dei logger nel backend ✅ (2026-06-01)

### Metodo

Eseguire una ricerca sistematica per livello:

```bash
# Trovare tutti i logger.info nel backend
grep -rn "logger\.info\|structlog.*info\b" backend/app/ --include="*.py" | grep -v "__pycache__" | grep -v ".pyc"

# Trovare tutti i logger.debug
grep -rn "logger\.debug\|structlog.*debug\b" backend/app/ --include="*.py" | grep -v "__pycache__"

# Trovare tutti i logger.log(5, ...) (TRACE ad-hoc esistenti)
grep -rn "logger\.log(5" backend/app/ --include="*.py" | grep -v "__pycache__"

# Trovare warning
grep -rn "logger\.warning\|logger\.warn\b" backend/app/ --include="*.py" | grep -v "__pycache__"
```

### Categorie da abbassare a DEBUG (esempi tipici)

Questi pattern **non** sono azioni utente → non appartengono a INFO:

```
"Using provider X for pair Y"        → DEBUG
"Fetched N rates for period Z"       → DEBUG
"Cache hit for key X"                → DEBUG
"Backward-fill: using date X (N days back)"  → TRACE
"Rate for EUR/USD on 2024-01-01: 1.0832"     → TRACE
"Processing asset X..."              → DEBUG (se in loop su molti asset)
```

### Categorie da mantenere a INFO (esempi tipici)

```
"Sync completed for pair X: N rates saved"  → INFO ✅
"User {id} logged in"                       → INFO ✅
"Import file {name}: N transactions parsed" → INFO ✅
"Asset {id} prices synced: {start}→{end}"   → INFO ✅
"FX Sync All completed: N pairs updated"    → INFO ✅
```

### File prioritari da auditare

```
backend/app/services/fx.py
backend/app/services/fx_providers/
backend/app/services/asset_source.py
backend/app/services/asset_source_providers/
backend/app/services/brim_provider.py
backend/app/services/brim_providers/
backend/app/routers/
backend/app/db/
```

> **Note implementazione** (2026-06-01): Audit completato. Cambiamenti effettuati:
>
> **INFO → DEBUG** (20 chiamate): `fx.py` (sync start, no-rates, db-only, all-same, per-currency),
> `fx_providers/boe.py`, `ecb.py`, `fed.py`, `snb.py` (×2), `manual.py`,
> `asset_source.py` (current-price persist ×4), `asset_source_providers/justetf.py` (×3),
> `yahoo_finance.py` (×4), `borsa_italiana.py`, `provider_registry.py`, `cache_utils.py` (×3),
> `auth_service.py` (JWT create), `main.py` (pre-warm).
>
> **INFO → WARNING** (1 chiamata): `fx.py` fallback route attivato.
>
> **DEBUG → TRACE** (2 chiamate): `fx.py` per-rate log (DB-only + updated rate).

---

## Step 4 — Silenziare/livellare i logger HTTP di terze parti ✅ (2026-06-01 — già implementato)

> ✅ **Già implementato** (verificato 2026-06-01): `logging_config.py` silenzia già httpx, httpcore, aiosqlite, sqlalchemy, yfinance e peewee a WARNING. Nessuna azione necessaria.

Verifica per completezza che `configure_logging()` contenga:
```python
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
```
✅ Presente. urllib3/requests non usati nel progetto (httpx only).

---

## Step 5 — Verifica ✅ (2026-06-01)

> **Note implementazione**: tutti e 5 i controlli passano:
> - `LOG_LEVEL=INFO` → solo INFO visibile, nessun DEBUG/TRACE
> - `LOG_LEVEL=TRACE` → TRACE + DEBUG + INFO tutti visibili
> - `logger.log(5, "FX rate")` → `"level": "TRACE"` nel JSON (non più "LOG" o crash)
> - `LOG_LEVEL=TRACE` parsa correttamente (non più fallback silenzioso a INFO)
> - 23/23 tests services + 5/5 schemas + 9/9 utils — tutti passati ✅

---

## File Coinvolti

| File | Modifica |
|------|----------|
| `backend/app/logging_config.py` | Policy comment + TRACE registration + HTTP silencing |
| `backend/app/services/fx*.py` | Abbassare log level per messaggi granulari |
| `backend/app/services/asset_source*.py` | Idem |
| `backend/app/services/brim*.py` | Idem (se applicabile) |
| Altri file con log incongruenti | Correggere livello dopo audit |

---

## Rischi

- **Zero**: nessun cambio comportamentale, solo label dei livelli e verbosità
- **Attenzione**: non abbassare log che sono utili per il debugging in produzione — usare il buon senso. In caso di dubbio, mantenere il livello corrente.
