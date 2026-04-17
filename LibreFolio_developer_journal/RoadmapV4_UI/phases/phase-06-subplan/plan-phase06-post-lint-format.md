# Phase 06 Post: Backend Lint & Format — Code Quality Standardization

**Status**: ✅ COMPLETED
**Data inizio**: 2026-04-17
**Data completamento**: 2026-04-17
**Priorità**: P2 (Quality infrastructure)
**Origine**: [plan-phase06Step6-Polish-Test-Docs.prompt.md](phase-06-subplan/Bugfix-Step6/plan-phase06Step6-Polish-Test-Docs.prompt.md) — sezione S5c

> **📌 Contesto**: Fino ad ora lint e format erano gestiti dall'IDE PyCharm senza configurazione esplicita e riproducibile.
> Questa fase migra a **ruff** (lint) + **black** (format) con configurazione in `pyproject.toml`.

---

## 1. Configurazione Concordata

### `pyproject.toml` — Decisioni di stile

| Parametro | Valore | Motivazione |
|-----------|--------|-------------|
| `line-length` | **300** | Righe dense, wrapping solo per leggibilità intenzionale. Black quasi mai spezza. |
| `target-version` | **py313** | Progetto usa Python 3.13+, nessuna retrocompatibilità necessaria |
| `Optional[X]` vs `X\|None` | **Mantenere `Optional[X]`** | Più esplicito con Pydantic, preferenza del developer |
| `List[X]` vs `list[X]` | **Mantenere `List[X]`** | Consistenza con `Optional`, stile typing tradizionale |
| `E402` (import not at top) | **Ignorato** | Pattern intenzionale: `sys.path` manipulation, `warnings.filterwarnings` |
| `B008` (func call in defaults) | **Ignorato** | FastAPI `Depends()` pattern |
| `PLC0415` (import in function) | **Abilitato** | Enforcement import top-level, eccezioni con `# noqa: PLC0415` |

### Regole abilitate

```
E, W, F, I, B, C4, UP, PLC0415
```

### Regole ignorate (con rationale)

```
E501, E402, B008, UP006, UP007, UP035, UP045
```

---

## 2. Lavoro Completato — Primo Passaggio

### 2.1 Auto-fix sicuri (ruff --fix)

| Codice | Descrizione | Occorrenze | Stato |
|--------|-------------|------------|-------|
| I001 | Import non ordinati (stdlib → third-party → local) | 132 | ✅ Auto-fix |
| F541 | f-string senza `{}` → string normale | 81 | ✅ Auto-fix |
| UP037 | Type annotation tra virgolette non necessarie | 21 | ✅ Auto-fix |
| UP015 | Mode ridondante in `open()`: `open(f, "r")` → `open(f)` | 15 | ✅ Auto-fix |
| UP017 | `datetime.timezone.utc` → `datetime.UTC` | 10 | ✅ Auto-fix |
| UP041 | `asyncio.TimeoutError` → `TimeoutError` | 4 | ✅ Auto-fix |
| UP024 | `IOError` → `OSError` | 1 | ✅ Auto-fix |
| UP034 | Parentesi superflue: `return (x)` → `return x` | 1 | ✅ Auto-fix |
| UP043 | Default type args ridondanti: `AsyncGenerator[str, None]` → `AsyncGenerator[str]` | 2 | ✅ Auto-fix |
| **Subtotale** | | **267** | ✅ |

### 2.2 Bug reali (fix manuale)

| Codice | Descrizione | Occorrenze | Fix applicato |
|--------|-------------|------------|---------------|
| B023 | Lambda in loop cattura variabile mutevole | 8 | `lambda _p=provider, _i=_id: _p.fetch(...)` — bind con default args |
| B015 | Confronto senza uso del risultato (`usd < eur`) | 1 | `# noqa: B015` — intenzionale in `pytest.raises` block |
| E722 | `except:` bare — cattura anche KeyboardInterrupt | 1 | `except Exception:` |
| **Subtotale** | | **10** | ✅ |

### 2.3 Qualità (fix manuale/script)

| Codice | Descrizione | Occorrenze | Fix applicato |
|--------|-------------|------------|---------------|
| B904 | `raise X` in except senza `from e` | 74 | Script automatico: `from e` per except con `as e`, `from None` per except senza |
| F841 | Variabile assegnata ma mai usata | 14 | Prefisso `_` (es. `_synced_count`) o rimossa |
| B007 | Variabile loop non usata | 11 | Rinominata `_var` |
| F401 | Import inutilizzati | 3 | Rimossi da `schemas/__init__.py` (re-export non utilizzati) |
| F811 | Classe definita 2 volte | 2 | Rimossa definizione duplicata `BRIMExtractedAssetInfo` (riga 57 in `brim.py`) e `FAPricePoint` duplicato in `__init__.py` |
| B905 | `zip()` senza `strict=True` | 3 | Aggiunto `strict=True` |
| B027 | Metodo vuoto in ABC senza `@abstractmethod` | 2 | `# noqa: B027` — no-op default intenzionale per `shutdown()` |
| C414 | `list(sorted(x))` → `sorted(x)` | 1 | Fix diretto |
| E712 | `== True` in SQLAlchemy where clause | 2 | `# noqa: E712` — corretto per SQLAlchemy, non bug |
| B017 | `pytest.raises(Exception)` troppo generico | 3 | `(Exception, IntegrityError)` per DB tests, `ValidationError` per schema test |
| **Subtotale** | | **115** | ✅ |

### 2.4 Black formatting

- **142 file riformattati**, 21 unchanged
- Effetto principale con `line-length=300`: normalizzazione parentesi chiuse (PyCharm `    )` → PEP8 `)`) e blank lines tra funzioni/classi

### 2.5 Riepilogo numerico

| Metrica | Valore |
|---------|--------|
| Errori iniziali | **528** |
| Errori finali | **0** ✅ |
| File formattati (black) | **163** |
| Test schemas | **218 passed** ✅ |

---

## 3. Errori Rimanenti — ~~Da Valutare~~ COMPLETATI

| Codice | # | Descrizione | Stato |
|--------|---|-------------|-------|
| PLC0415 | 87 | Import dentro funzioni | ✅ Tutti marcati `# noqa: PLC0415` con reason |
| UP042 | 18 | `(str, Enum)` → `StrEnum` | ✅ Migrato a `StrEnum` + cleanup import |
| C408 | 9 | `dict()` → `{}` | ✅ Auto-fix con `--unsafe-fixes` |
| UP046 | 3 | Generics → PEP 695 | ✅ `OldNew[CType]`, `BaseListResponse[TResult]`, `BaseBulkResponse[TResult]`, `BaseBulkDeleteResponse[TResult]` |
| F841 | 1 | Variabile non usata | ✅ Prefisso `_` |

---

## 4. Infrastruttura Creata

### 4.1 Skill: `lint-format`

File: `.github/skills/lint-format/SKILL.md`

Copre:
- Tools & config (ruff + black)
- Tutte le regole abilitate/ignorate con rationale
- Come fixare ogni tipo di violazione (auto vs manuale)
- Pattern `# noqa` approvati
- Workflow per file singolo e codebase
- Known pitfalls (I001 che corrompe import, E712 con SQLAlchemy)

### 4.2 Prompts riusabili

| File | Descrizione |
|------|-------------|
| `.github/prompts/lint-file.prompt.md` | Lint + format su un singolo file backend |
| `.github/prompts/lint-all.prompt.md` | Lint + format su tutto il backend |

### 4.3 Git commit instructions

File: `.github/git-commit-instructions.md`

Struttura conventional commits estratta dall'analisi degli 80+ commit storici:
- Types: `feat`, `fix`, `refactor`, `docs`, `chore`
- Scopes: `backend`, `ui`, `phase06`, `fx`, `assets`, etc.
- Regole subject line: imperative, lowercase, no period, ` + ` separator

### 4.4 MkDocs instructions aggiornate

`.github/instructions/mkdocs.instructions.md` — aggiunto chiarimento:
> EN-only sections (developer/, POC UX) → No translation needed — **by design**, not an oversight

---

## 5. Pitfalls Scoperti

1. **ruff I001 + PyCharm closing parens**: Il sort degli import può **corrompere file** se gli import usano lo stile PyCharm con `)` indentata. Successo su `asset_source.py` (3400 righe) — righe di import diverse sono state mescolate. **Soluzione**: sempre black prima di ruff I001, o applicare I001 per-file con verifica.

2. **Terminale con output troncato/vuoto**: Comandi ruff con output lungo non vengono restituiti dal terminale. **Soluzione**: sempre redirect su file (`> /tmp/ruff_out.txt 2>&1`) e poi `read_file`.

3. **ruff --statistics può essere stale**: Se leggi un file `/tmp` scritto in precedenza, potresti vedere dati vecchi. Sempre ri-eseguire il comando prima di leggere.

4. **UP042 → StrEnum cleanup**: Dopo aver convertito `(str, Enum)` → `StrEnum`, l'import `Enum` diventa unused. Il fix automatico F401 lo rimuove, ma poi manca `StrEnum` se non era importato. **Soluzione**: dopo UP042, verificare F821 (undefined name) e aggiungere `from enum import StrEnum`.

5. **UP046 → PEP 695 generics**: `BaseBulkDeleteResponse` estendeva `BaseBulkResponse[TResult]` ma `TResult` non era più un `TypeVar`. Serve anche qui la syntax PEP 695: `class BaseBulkDeleteResponse[TResult: BaseModel](BaseBulkResponse[TResult])`.

---

## 6. ~~Prossimi Passi~~ Risultato Finale

- [x] Risolvere tutti i 528 errori ruff → **0 errori**
- [x] Black formatting su tutti i 163 file
- [x] Test schemas: **218 passed** ✅
- [x] Decisione stile: **Black standard** (non PyCharm) per team-readiness
- [ ] Valutare lint frontend (eslint + prettier per Svelte/TypeScript)
- [ ] Run test completi (`./dev.py test all-backend`) prima del commit finale
