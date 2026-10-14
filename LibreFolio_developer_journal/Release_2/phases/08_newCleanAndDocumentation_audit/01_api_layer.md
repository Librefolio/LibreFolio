# 01 — API layer — verifica 2026-09-02

> Fonte: [report archiviato](../../phases/05_cleanAudit/01_api_layer.md)
> Metodo: analisi statica read-only; nessun test eseguito (run full in corso).
> Branch `dev_release2`, working tree con modifiche non committate del 02/09 considerate realtà.

---

## Sintesi esecutiva

I due reperti 🔴 si sono divisi: **A1 (interruttore registrazione) è stato chiuso** durante
l'esecuzione S1–S3 del 2026-08-05 — `register()` ora rifiuta con 403 e il caso primo-utente
è gestito — mentre **A2 (`require_email_verification`) è ancora completamente scollegato**:
dichiarato, esposto in UI in 4 lingue, documentato su mkdocs, e mai letto da nessuna riga
di backend. Tutto il debito 🟡/🟢 di fondo è **ancora valido e quasi immutato**: i due N+1
bulk sono verbatim identici, i 17 endpoint senza `response_model` sono ancora 17 (ma su 110
endpoint invece di 97 — il denominatore è cresciuto), le 8 classi schema orfane hanno ancora
zero referenze, i `TRY400` sono 28 invece di 27. A6 (`get_optional_user`) e A7 (`open()`
bloccante) sono fatti. Un nuovo rilievo: il ramo anteprima immagini di `serve_file`
(Pillow) esegue I/O + CPU bloccanti dentro l'handler `async` — esisteva già all'epoca
dell'audit ma era sfuggito alla verifica dei 104 siti.

---

## Tabella di verifica

| Voce vecchia | Stato 2026-08 | Stato verificato oggi | Evidenza (file:riga attuale) | Azione |
|---|---|---|---|---|
| A1 🔴 interruttore registrazione mai verificato | aperto | **FATTO** (S1–S3, voce 2.4) | `backend/app/api/v1/auth.py:189-191` — `registration_enabled = await is_registration_enabled(session)` + `raise HTTPException(403)`; esenzione primo utente a `:187,190`; test REG-006 in `backend/test_scripts/test_api/test_auth_api.py:143` | nessuna |
| A2 🔴 `require_email_verification` senza accessor né applicazione | aperto | **ANCORA VALIDO** | dichiarato `backend/app/schemas/settings.py:92`; UI `frontend/src/lib/components/settings/tabs/GlobalSettingsTab.svelte:29,50`; i18n ×4 (`en/it/fr/es.json:1805,1817`); docs `mkdocs_src/docs/admin/settings.it.md:40,61`. `grep -rn "require_email_verification" backend/app/services/ backend/app/api/` → 0 hit | decidere: implementare o rimuovere |
| A3 🟡 N+1 `portfolio_api.py:49` | aperto | **ANCORA VALIDO** (verbatim) | `backend/app/api/v1/portfolio_api.py:49` — `asset = await session.get(Asset, query.asset_id)` nel loop `for query in body.queries:` a `:44` | batching con `Asset.id.in_(...)` |
| A3 🟡 N+1 `fx.py:984` | aperto | **ANCORA VALIDO** | `backend/app/api/v1/fx.py:965` (`session.execute(stmt)` nel loop `:944`) e `:1014` (`session.execute(count_stmt)` nel loop `:1009`) | batching |
| A4 🟡 17 endpoint su 97 senza `response_model` | aperto | **ANCORA VALIDO** — 17 su 110 oggi | elenco AST riprodotto sotto; esempio `system.py:199` `health_check` ritorna `{"status": "ok"}` grezzo | cablare gli schemi A5 |
| A5 🟡 8 schemi risposta mai collegati | aperto | **ANCORA VALIDO** — tutti e 8 con 0 refs | `schemas/auth.py:34`, `auth.py:116`, `fx.py:495`, `portfolio.py:71`, `portfolio.py:79`, `portfolio.py:273`, `portfolio.py:282`, `prices.py:378` (comandi sotto) | collegare o rimuovere |
| A6 🟡 `get_optional_user` senza chiamanti | aperto | **FATTO** (S1–S3, voce 2.15) | `grep -rn "get_optional_user" backend/ frontend/src` → 0 hit | nessuna |
| A7 🟢 `open()` sincrona in `async def` | aperto | **FATTO** (S1–S3) | `backend/app/api/v1/uploads.py:377-384` — `_read_text_preview()` locale invocata via `await asyncio.to_thread(...)` a `:384` | nessuna |
| A8 🟢 27 `logger.error` in `except` (TRY400) | aperto | **ANCORA VALIDO**, anzi 28 | `cd backend && pipenv run ruff check app/api/v1/ --extend-select TRY400 --statistics` → 28; esempio `uploads.py:390,451` | conversione meccanica |
| Metrica: 18 file / 5 976 righe / 97 endpoint | — | **decaduta** | oggi 17 file / 6 189 righe / 110 endpoint (AST) | — |
| Metrica: ruff api/v1 — TRY400 27, RUF100 10, RUF010 10 | — | **parzialmente decaduta** | TRY400 28; RUF100 **0**; RUF010 **0** (autofix tenuto) | — |
| Metrica: C901 api/v1 — 5 funzioni (max 14) | — | **ancora valida** | 5 funzioni, max 15 (`create_routes_bulk` fx.py:750, `serve_file` uploads.py:332) | — |
| Contrasto A1: `max_file_upload_mb` applicato in uploads.py:169 | valido | **ancora valido** | accessor `get_max_upload_mb` (`global_settings_service.py:85`) usato in `uploads.py:170-175` (413) e `brokers.py:595` | — |

---

## Dettaglio reperti ancora aperti / regrediti

### A1 — FATTO, con la gestione del primo utente

Il rimedio applicato è esattamente quello proposto, inclusa la questione lasciata aperta
dal vecchio report (*"il primo utente deve poter registrarsi anche a registrazioni
chiuse?"*): la risposta implementata è **sì** — `is_first_user` (conteggio utenti a
`auth.py:186-187`) esenta il primo account dal 403, evitando il lockout di
un'installazione nuova. Coperto dal test REG-006 (`test_auth_api.py:143`: *"Disabled
registration returns 403 when at least one user exists"*).

### A2 — ANCORA VALIDO, immutato

Nessuna evoluzione dal 2026-08-07: la chiave esiste in `schemas/settings.py:92` con
default `"false"`, è nel gruppo `security` della UI, ha stringhe in 4 lingue e due pagine
mkdocs. Il backend non la legge da nessuna parte. Il docstring di `register`
(`auth.py:183`) continua ad ammettere: *"In production, you may want to add email
verification."* Restano le due strade del vecchio report; la terza (lasciare tutto com'è)
è ancora la peggiore.

### A3 — ANCORA VALIDO, codice verbatim

> ✅ **Risolto 02–03/09** (P0-5): il bulk patch è stato fixato il 02/09 (preload unico +
> aggregati `GROUP BY`); i due N+1 verbatim di questa sezione sono stati fixati il 03/09
> (Lane B): `portfolio_api.py` ora precarica gli asset con **una** `SELECT ... IN (...)`
> (commento «P0-5b» nel codice) e `api/v1/fx.py` accumula delete/verifiche fuori dai loop
> con `tuple_(...).in_(...)`. ⚠️ Fuori pista registrato nel piano: i siti FX erano in
> `api/v1/fx.py`, non in `services/fx.py` come citato qui.

`portfolio_api.py:44-49`: il loop e la `session.get` per-query sono identici a un mese fa.
Con il batching proposto si passerebbe da N round-trip a 1.
`fx.py`: l'endpoint `delete_routes_bulk` esegue `session.execute` per elemento a `:965`
(loop `:944`) e una seconda query per coppia a `:1014` (loop `:1009`). Il file è cresciuto
(1 022 → 1 052 righe) e i numeri di riga del vecchio report (979/984) sono slittati.

### A4 — ANCORA VALIDO: 17 endpoint senza `response_model` su 110

> ✅ **Risolto 03/09** (P1-1, Lane A): nel frattempo 11 dei 17 erano stati cablati dalle
> ondate beta; i **6 residui** (`system.py` ×1, `settings.py` ×3, `uploads.py` ×2) sono
> stati cablati con **13 schemi nuovi** creati ad hoc; i 2 endpoint binari di `uploads.py`
> usano `response_class`. `api sync` eseguito + fix del discriminatore `SchedulerLog`
> (`json_schema_extra enum` + post-processor). Verificato: `response_model=` presente su
> `system.py:198`, `settings.py:144/201`, `uploads.py:154+`.

Comando (AST, non regex — i decoratori multi-riga ingannano il grep):

```bash
cd backend && python3 -c "
import ast, glob
total=0; no=[]
for f in sorted(glob.glob('app/api/v1/*.py')):
    for node in ast.walk(ast.parse(open(f).read())):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if isinstance(dec,ast.Call) and isinstance(dec.func,ast.Attribute) and dec.func.attr in ('get','post','put','patch','delete'):
                    total+=1
                    if not any(kw.arg=='response_model' for kw in dec.keywords): no.append(f'{f}:{node.lineno} {node.name}')
print(total, len(no)); [print(' ',x) for x in no]"
# → endpoints: 110, without response_model: 17
```

Elenco attuale: `assets.py:511` `search_assets_stream`, `assets.py:1153`
`market_data_summary`, `assets.py:1176` `wipe_market_data`, `backup.py:150/184/223/278/335`
(5 endpoint backup), `brokers.py:726/752/781` (3 endpoint file), `settings.py:142/156/201`,
`system.py:199` `health_check`, `uploads.py:332` `serve_file`, `uploads.py:475`
`serve_plugin_static`. Il totale endpoint è salito 97 → 110 ma nessuno dei senza-schema è
stato cablato: il buco di tipizzazione verso il client Zodios resta.

### A5 — ANCORA VALIDO: 8 classi, 0 referenze

> ⚠️ **Parziale 03/09** (P1-1): gli endpoint scoperti sono stati cablati con **schemi
> nuovi**, quindi le 8 classi pre-scritte di questo reperto **restano orfane** (verificato
> il 03/09: 0 referenze ciascuna fuori dalla definizione). La decisione
> collegare-o-rimuovere resta aperta (`AuthPasswordResetRequest`/`AuthErrorResponse`
> legate alla decisione P2-1 su `require_email_verification`).

Comando per ciascuna classe:

```bash
cd backend && grep -rn "\b<NomeClasse>\b" app/ --include="*.py" | grep -v __pycache__
```

Risultato: per tutte e 8 l'unica riga è la `class ...` di definizione —
`AuthPasswordResetRequest` (`schemas/auth.py:34`), `AuthErrorResponse` (`auth.py:116`),
`FXPairsListResponse` (`fx.py:495`, era :503), `PortfolioSummaryQuery`
(`portfolio.py:71`, era :81), `PortfolioHistoryQuery` (`portfolio.py:79`, era :91),
`AllocationHistoryQuery` (`portfolio.py:273`, era :299), `AllocationHistoryResponse`
(`portfolio.py:282`, era :310), `FAEventDeleteResult` (`prices.py:378`, era :401).
Anche il frontend non le nomina (`grep -rn <nomi> frontend/src/` → 0 hit). Il reset
password resta solo da CLI: `scripts/user_cli.py:90` (`user_service.reset_password`).

### A8 — ANCORA VALIDO: TRY400 in api/v1 = 28 (era 27)

> ✅ **Risolto 03/09** (P1-3, Lane B2): tutti i 55 `TRY400` del backend convertiti in
> `logger.exception`, 0 residui (verificato: 0 `logger.error` residui in `api/v1/`).

```bash
cd backend && pipenv run ruff check app/api/v1/ --extend-select TRY400 --statistics
# → 28 TRY400
```

Nessuna conversione fatta; un sito in più rispetto all'audit. Esempi vivi:
`uploads.py:390` e `uploads.py:451` (`logger.error(...)` dentro `except Exception`).

---

## Task riesumati

1. **A2 — Decidere `require_email_verification`** (M): implementare la verifica email
   oppure rimuovere la chiave da `schemas/settings.py:92`, UI (`GlobalSettingsTab.svelte:29,50`),
   i18n ×4 e mkdocs ×2. Invariato da un mese; la UI continua a promettere ciò che il
   sistema non fa.
2. **A3a — Batching N+1 in `portfolio_api.py:49`** (S): `select(Asset).where(Asset.id.in_(...))`
   una volta, lookup in memoria nel loop. Rimedio già scritto nel vecchio report.
   > ✅ **Fatto 03/09** (P0-5, Lane B): preload unico `Asset.id.in_(...)` + lookup in memoria.
3. **A3b — Batching N+1 in `fx.py:965` e `:1014`** (S): accumulare gli statement di
   delete e la verifica delle rotte residue fuori dai loop.
   > ✅ **Fatto 03/09** (P0-5, Lane B): delete e conteggi accumulati con `tuple_(...).in_(...)`
   > fuori dai loop. ⚠️ i siti erano in `api/v1/fx.py`, non `services/fx.py`.
4. **A4+A5 — Cablare i 17 endpoint agli schemi già scritti, poi `./dev.py api sync`** (M):
   chiude i due reperti insieme e ripristina la tipizzazione end-to-end del client Zodios.
   `AuthPasswordResetRequest` e `AuthErrorResponse` restano da decidere (implementare il
   reset via API / rimuovere lo schema).
   > ⚠️ **Parziale 03/09** (P1-1, Lane A): i 6 endpoint residui cablati (13 schemi **nuovi**
   > creati, 2 binari → `response_class`), `api sync` fatto. Le 8 classi pre-scritte di A5
   > **non** sono state riusate e restano orfane — decisione aperta.
5. **A8 — Convertire i 28 `TRY400` in `logger.exception`** (S): meccanico, nessun rischio.
   > ✅ **Fatto 03/09** (P1-3, Lane B2): 55/55 convertiti su tutto il backend, 0 residui.
6. **N1 — Avvolgere il ramo anteprima immagini di `serve_file` in `asyncio.to_thread`** (S):
   vedi sotto.
   > ✅ **Fatto 02/09** (P0-4): helper sync `_resize_image` + `to_thread`, test spy.

---

## Nuovi rilievi

### N1 🟡 — Pillow bloccante nel ramo immagini di `serve_file` (`uploads.py:423-441`)

> ✅ **Risolto 02/09** (P0-4): estratto l'helper sync `_resize_image` (`uploads.py:340`)
> invocato via `await asyncio.to_thread(...)` (`:455`); ramo `ratio>=1` invariato; test
> spy aggiunto. Rimedio applicato esattamente nella forma proposta qui sotto.

Il fix di A7 ha corretto solo il ramo testuale. Il ramo `img_preview` dello **stesso**
handler `async def serve_file` esegue nel corpo dell'handler:

- `img = Image.open(file_path)` — `uploads.py:423` (lettura file bloccante)
- `img.resize(..., Image.Resampling.LANCZOS)` — `:435` (CPU-bound, tanto più costoso
  quanto più grande l'immagine)
- `img.save(output, ...)` — `:440`

Il ramo esisteva identico all'epoca dell'audit (introdotto da `1eebfe91`, 2026-01-20) ed
è sfuggito alla verifica dei 104 siti: il vecchio audit aveva correttamente isolato il
solo `open()` testuale. L'impatto è superiore al reperto A7 originale: non solo I/O ma
anche CPU di resize dentro l'event loop. Rimedio: stesso pattern di `_read_text_preview`
— estrarre una funzione sync `_make_image_preview()` e invocarla con
`await asyncio.to_thread(...)`. Nota: `img.format` letto a `:439` dopo `Image.open` —
va incluso nella funzione estratta.

### N2 🟢 — Unico errore ruff di progetto in `app/`: `PLC0415` a `settings.py:168`

```bash
cd backend && pipenv run ruff check app/
# → 1 error: PLC0415 app/api/v1/settings.py:168 — `from backend.app.db.session import get_async_engine` dentro funzione
```

Import in-funzione senza il `# noqa: PLC0415` che il progetto usa altrove per i lazy
import. Presente dal 2026-06-23 (`3f9d6ecd`). La baseline `./dev.py lint` completa è 37
errori (era 36 all'audit): 36 `PLC0415` + 1 `B905`, quasi tutti in `test_scripts/`
(pattern noto dei test), più questo unico in `app/`.

---

## Cross-reference

- Fonte archiviata: [05_cleanAudit/01_api_layer.md](../../phases/05_cleanAudit/01_api_layer.md)
- Esecuzione S1–S3 che ha chiuso A1/A6/A7: [05_cleanAudit/15_esecuzione_s1_s3.md](../../phases/05_cleanAudit/15_esecuzione_s1_s3.md)
- Backlog con stato delle voci (2.4, 2.15, 4.4, 5.7, 6.1): [05_cleanAudit/14_backlog_per_complessita.md](../../phases/05_cleanAudit/14_backlog_per_complessita.md)
- Report gemello di questa tornata: [11_crosscutting.md](11_crosscutting.md)
