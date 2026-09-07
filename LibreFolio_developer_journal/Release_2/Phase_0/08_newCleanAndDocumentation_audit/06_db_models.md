# 06 — DB & modelli — verifica 2026-09-02

> Fonte: [report archiviato](../../phases/05_cleanAudit/06_db_models.md) (audit 2026-08-07)
> Metodo: analisi statica read-only; nessun test eseguito, nessun server avviato.
> Tree verificato: branch `dev_release2` + modifiche beta non committate del 2026-09-02.

---

## Sintesi esecutiva

Il livello dati resta il più pulito del backend: **0 rilievi ruff** con la configurazione
di progetto (`pipenv run ruff check backend/app/db/` → `All checks passed!`), **3 rilievi**
riproducendo le regole estese dell'audit (era 8).

Dei 6 reperti: **1 FATTO** (F3, gli ARG001 — rimedio applicato esattamente come
raccomandato), **1 ancora valido e invariato** (F1, il DRY orfano `is_chain`/
`providers_used`), **1 ancora valido con precisazione** (F2, i `cls` di vulture),
**2 superati dai fatti** (F5-RUF100: l'affermazione era errata già all'epoca; F6: oggi
le migrazioni sono 3), **1 ancora valido** (F4/F5-RUF022, cosmetici).

La regola "migrazioni incrementali" **è stata rispettata**: la nuova migrazione
`5b1333fa6b07` (2026-08-31) fa `down_revision = 002`, e `001_initial.py` non è stato
toccato dal 2026-07-28 (e quel commit modificò solo il docstring di testa).

---

## Metriche riprodotte

| Metrica | Audit 2026-08 | Oggi | Comando |
|---|---:|---:|---|
| `db/models.py` righe | 1 004 | **1 004** | `wc -l backend/app/db/models.py` |
| `db/session.py` righe | 154 | **174** (+20: `PRAGMA busy_timeout` + doc) | `wc -l …` |
| `db/base.py` righe | 53 | **53** | `wc -l …` |
| `db/__init__.py` righe | 53 | **53** | `wc -l …` |
| Totale | 1 264 | **1 284** | `wc -l backend/app/db/*.py` |
| Migrazioni Alembic | 2 | **3** | `ls backend/alembic/versions/` |
| Rilievi ruff (config progetto) | 8* | **0** | `pipenv run ruff check backend/app/db/` |
| Rilievi ruff (regole estese audit) | 8 | **3** | `pipenv run ruff check --extend-select ARG001,N805,RUF022,RUF100 backend/app/db/` |

\* L'audit contava con regole estese; con la sola config di progetto già all'epoca
sarebbero stati 0 (ARG001/N805/RUF022/RUF100 non sono in `select`).

---

## Tabella di verifica

| Voce vecchia | Stato 2026-08 | Stato verificato oggi | Evidenza | Azione |
|---|---|---|---|---|
| F1 — `is_chain`/`providers_used` orfane, logica duplicata | 🟡 aperto | **ANCORA VALIDO** (parzialmente ridotto) | property a `models.py:904` e `:909` (era :903/:909), zero chiamanti di produzione; inline backend a `services/fx.py:990-991` e `:1098-1099`; inline frontend a `FxPairAddModal.svelte:113` e `routes/(app)/fx/[pair]/+page.svelte:670`; `FxProviderConfig.svelte` **rimosso** in `be8394bb` | Task T1 |
| F2 — 12 falsi positivi vulture (`cls`) | 🟢 documentato | **ANCORA VALIDO** (con correzione) | oggi **11** hit `unused variable 'cls' (100%)` a `models.py:353,526,532,543,551,556,704,750,799,841,894` (`pipenv run vulture backend/app/db/models.py \\| grep -c "unused variable 'cls'"` → 11). **Correzione al report**: NON sono coperti da `[tool.vulture]` (`cls` non è in `ignore_names`, pyproject.toml:143-166); sono filtrati dal runner `dev.py:1664` (`DEAD_CODE_SIGNAL_TYPES` esclude il kind `variable`) | nessuna |
| F3 — 3 ARG001 su listener | 🟢 aperto | **FATTO** | `models.py:1002` → `receive_before_update(_mapper, _connection, target)`; `session.py:21` → `set_sqlite_pragma(dbapi_conn, _connection_record)`. Commit `be8394bb` (2026-08-05, bande S1–S3). Ruff esteso oggi: **0 ARG001** | nessuna |
| F4 — N805 `models.py:556` | 🟢 documentato | **ANCORA VALIDO** (immutato) | `pipenv run ruff check --extend-select N805 backend/app/db/` → `models.py:556:40`, stesso validator `validate_classification_params(cls, v)` | nessuna |
| F5 — 2 RUF022 + 2 RUF100 | 🟢 aperto | **PARZIALE / SUPERATO** | RUF022: ancora presenti, `db/__init__.py:29` e `db/base.py:32` (stesse righe). RUF100: **SUPERATO — l'affermazione originale era errata**: `PLC0415` è in `select` da `f1205b7e` (2026-04-17, pyproject.toml:80), quindi i `# noqa: PLC0415` a `models.py:52,558` erano e restano **funzionali** (verificato: con config progetto + RUF100, nessun rilievo). Non vanno rimossi | Task T4 (cosmetico) |
| F6 — solo 2 migrazioni | 🟢 ok | **SUPERATO** (evoluzione corretta) | `ls backend/alembic/versions/` → `001_initial.py`, `002_identifier_other_json_list.py`, `5b1333fa6b07_scheduler_times_use_configured_timezone.py` (commit `c8bdbaea`, 2026-08-31). `down_revision = "002_identifier_other_json_list"` → catena incrementale corretta | nota naming (N1) |
| Int.1 — verificare 002 su DB 1.0.1 popolato | raccomandato | **PARZIALE** | 002 è data-only e idempotente (guard `substr(...,1,1) != '['`, file:38); i DB di test si creano via `./dev.sh db:upgrade` (`scripts/test_runner/_backend_db.py:106`) quindi 001→002→5b1333fa6b07 sono esercitate a ogni run, ma **da vuote**; il caso "upgrade di DB 1.0.1 popolato" non ha un test dedicato | Task T5 |

> ✅ **Aggiornamento 03/09** (P1-16, WS-H): il caso «upgrade di DB 1.0.1 popolato» è stato
> **provato per davvero** — immagine pubblicata 1.0.1 → nuova immagine sullo stesso volume,
> marker SQL pinnati (`'MIGRATION_MARKER'` → `["MIGRATION_MARKER"]`, `''` → NULL, array
> intatto; `'12:00'` → `'14:00'` Europe/Rome). Vedi nota sotto la tabella Task.
| Int.2 — usare `providers_used` in fx.py | raccomandato | **MAI FATTO** | `services/fx.py:990` e `:1098` ancora list comprehension inline | Task T1 |
| Int.3 — esporre `is_chain` via API | raccomandato | **MAI FATTO** | `grep is_chain backend/app/schemas/fx.py backend/app/api/v1/fx.py` → 0 hit | Task T2 |
| Int.4 — prefissi `_` listener | raccomandato | **FATTO** | vedi F3 | nessuna |
| Int.5 — rimuovere RUF100 | raccomandato | **SUPERATO** | le `noqa` sono necessarie; la raccomandazione era basata su un dato errato | nessuna (non fare) |

---

## Dettaglio reperti ancora aperti / regrediti

### F1 — DRY orfano `is_chain`/`providers_used`: ANCORA VALIDO

Stato attuale della mappa di duplicazione (righe verificate oggi):

| Punto | Codice | Stato |
|---|---|---|
| `backend/app/db/models.py:904-906` | `is_chain` property | orfana (solo test: `test_model_validators.py:236-244`) |
| `backend/app/db/models.py:909-911` | `providers_used` property | orfana (solo test: `:246-254`) |
| `backend/app/services/fx.py:990` | `[s["provider"] for s in steps if s["provider"].upper() != "MANUAL"]` | inline, filtra MANUAL |
| `backend/app/services/fx.py:1098` | `[s["provider"] for s in steps]` | inline, non filtra |
| `frontend/.../fx/FxPairAddModal.svelte:113` | `!(i.chain_steps?.length === 1 && i.chain_steps[0].provider === 'MANUAL')` | inline |
| `frontend/.../routes/(app)/fx/[pair]/+page.svelte:670` | stessa espressione | inline (il path ora include il route group `(app)`) |
| ~~`FxProviderConfig.svelte:75,219,240`~~ | — | **rimosso** in `be8394bb` (era file morto, report 09/I1) |

Le tre semantiche non equivalenti segnalate dall'audit (set vs list con/senza filtro
MANUAL) sono tuttora presenti. `parsed_steps` resta viva: 7 punti di produzione
(`api/v1/fx.py:885,1020,1025`, `portfolio_service.py:864`, `services/fx.py:822,928,942`).
L'audit ne contava 8 elencandone 7: refuso nel report originale.

**Regresso parziale / aggravante nuovo**: la composizione dell'etichetta
`'CHAIN:' + join('+')` è duplicata in **3** punti, non segnalati come tali dal report:
`services/fx.py:1099`, `routes/(app)/fx/+page.svelte:311`,
`routes/(app)/fx/[pair]/+page.svelte:675`. Se la regola cambia, andrebbero toccati
tutti e tre (più i due filtri MANUAL del frontend).

### F6 — Alembic: regola rispettata, naming divergente

- `git log --follow -- backend/alembic/versions/001_initial.py` → ultimo tocco
  `a10155ba` (2026-07-28), e quel commit modificò **solo il docstring di testa**
  (verificato con `git show a10155ba -- backend/alembic/versions/001_initial.py`:
  +17/-3, nessuna tabella). Nessuna modifica successiva all'audit.
- La nuova `5b1333fa6b07` è **dati+schema leggero** (scheduler timezone), con
  `down_revision = "002_identifier_other_json_list"`: la catena incrementale è corretta.
- **Divergenza di naming**: il report si aspettava `003_*`; la migrazione reale usa
  l'hash Alembic (`5b1333fa6b07_scheduler_times_use_configured_timezone.py`). La regola
  sostanziale (incrementale, mai editare 001) è rispettata; la convenzione di nome no.

---

## Task riesumati

| # | Task | Evidenza | Stima |
|---|---|---|---|
| T1 | Usare `route.providers_used` nei due punti inline di `services/fx.py` (:990, :1098), decidendo la semantica MANUAL (probabilmente serve `real_providers_used` come suggerito) | fx.py:990-991, 1098-1099; models.py:909 | **S** |
| T2 | Esporre `is_chain` (o un `provider_code` già composto) nella risposta routes dell'API FX e rimuovere le 4 reimplementazioni frontend (:113, :670, :311, :675) — include la nuova duplicazione dell'etichetta `CHAIN:` | schemas/fx.py, api/v1/fx.py:718; frontend sopra | **M** |
| T3 | *(dall'audit, ancora valido)* Verificare 002 su DB 1.0.1 popolato: scenario non coperto (i test creano da zero via `db:upgrade`, `_backend_db.py:106`) | 002 file:32-39 | **S** |
| T4 | Decidere se rendere permanente l'ordinamento `__all__` (RUF022 a `db/__init__.py:29`, `db/base.py:32`) o ignorarlo esplicitamente; oggi la regola non è in config, quindi è solo debito latente | ruff esteso | **S** |

> **Stato 03/09 (esecuzione P0/P1)**:
> - **T3** ✅ (P1-16, WS-H): prova eseguita con **marker esatti** — container da immagine
>   pubblicata `1.0.1` su volume popolato (17 asset, 11 utenti, 5 435 record, alembic
>   `001_initial`) → riavvio su nuova immagine, stesso volume. Esito: `002` applicata
>   (`identifier_other` scalare `'MIGRATION_MARKER'` → `["MIGRATION_MARKER"]` ✓, `''` →
>   NULL ✓, array esistente invariato ✓) e `5b1333fa6b07` corretta (`'12:00'` UTC →
>   `'14:00'` Europe/Rome, CEST di settembre ✓); boot pulito, dashboard 200. Prerequisito
>   di release chiuso.
> - **T4** ⚠️ **Parziale** (P1-17, 03/09): il giro «igiene minore» è marcato fatto nel 99,
>   ma per RUF022 **nessuna modifica visibile** — né la regola in config né `noqa` sui due
>   `__all__` (verificato il 03/09). Il debito latente resta tale: decisione non registrata
>   nel codice.

Non riesumare l'intervento "rimuovere i RUF100": era basato su un dato errato
(PLC0415 abilitata da aprile); le `noqa` a `models.py:52,558` sono funzionali.

---

## Nuovi rilievi

- **N1 — Naming migrazioni divergente**: `5b1333fa6b07_*` invece di `003_*`. Se la
  convenzione numerata è desiderata, va scritta nelle istruzioni backend-db; altrimenti
  va emendato il report/regola. Nessun impatto funzionale.
- **N2 — Duplicazione etichetta `CHAIN:`** (3 siti, vedi F1 sopra): aggravamento del
  DRY orfano rispetto alla fotografia dell'audit.
- **N3 — `session.py` cresciuto del 13 % in docstring** (174 righe): il blocco
  `busy_timeout` (session.py:29-50) documenta una misura (45k punti, 10.3 s di lock)
  dentro un docstring — contenuto pregevole ma candidato al devWiki, non un rilievo di
  pulizia. Funzionalmente corretto.
- Nessuna modifica del working tree beta tocca `backend/app/db/` o
  `backend/alembic/`: `git status --short` → nessun file in scope.

---

## Cross-reference

- Report [07](07_schemas_utils.md): G1 (stesso pattern DRY orfano lato schemas),
  G3 (`merge_other_identifiers`, ora cablata nel merge asset).
- Report 01 dell'audit originale: 17 endpoint senza `response_model` — riprodotto oggi:
  **17 su 110** (era 17/97; 13 endpoint nuovi, tutti cablati). Script di conteggio
  balance-aware sui decoratori `@*router*.(get|post|…)` in `backend/app/api/v1/*.py`.
- Commit chiave: `be8394bb` (S1–S3, 2026-08-05: F3 FATTO, FxProviderConfig rimosso),
  `571bcde0` (2026-08-08: asset identity), `c8bdbaea` (2026-08-31: migrazione 3).
