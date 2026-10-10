# Performance charts — bugfix: gli eventi degli asset nell'editor dei dati

**Stato:** ✅ **COMPLETATO E INTEGRATO**. Lotto chiuso il 2026-10-08 alle 20:32 (FROZEN). Commit del developer il
2026-10-08 alle 22:16: `fba7edf07` (backend e i suoi test), `e0b2077d2` (frontend e i suoi test), `c160bd34c` (doc) e
`994347f55` (questo giornale). In `dev_release2` col treno 19, merge `5423c334f`. I limiti residui hanno una voce di
backlog (I-09…I-12, «Limiti residui»). Verificato e archiviato il 2026-10-09 in
`Release_2/phases/20_performanceCharts/`. Reperti di Q (onda 2), verifiche chieste dal coordinator alle 17:42
(«verifiche prima, e la correzione solo dei reperti confermati»). Decisioni del developer relayate alle 17:58 (testo
sotto).
*Storia dello stato:* IN CORSO (2026-10-08, dalle 17:42).
**Workstream:** I (grafici performance) · ramo `e-alfy-performance-charts-plan` · coordinatore
`c8328a01-f208-4ade-a352-0486d1f14de2`.
**Baseline:** HEAD = `108a2adf5` (treno 17), albero pulito, rimisurato prima di scrivere questo piano.
**Lane:** suite `6157` (+ `6167` se serve) e `/tmp/librefolio-r2-i`, solo `dev.py test …`, un comando alla volta.
Preambolo: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py …`.

Precedenti e collegati:

- Piano precedente di I: [plan-phase00PerformanceChartsIncomeColorsAxisLabels.prompt.md](plan-phase00PerformanceChartsIncomeColorsAxisLabels.prompt.md).
- La scelta `RESTRICT` sulla FK `transactions.asset_event_id` è raccontata in
  `LibreFolio_devWiki/wiki/sources/phase07-transactions.md`; la Policy D (valuta dell'evento = valuta dell'asset) in
  `LibreFolio_devWiki/wiki/decisions/policy-d-currency-wipe.md`. Il grafo di graphify non è disponibile in questo
  worktree (file ignorati): ho letto le pagine direttamente.
- Il numero mancante nei messaggi (`{n}` contro `count`) è di K: fuori da questo lotto.
- CHANGELOG: lo scrive il coordinator, righe *Fixed*. Al checkpoint gli mando una frase per correzione.

## Decisioni del developer (17:58, testuale)

> «Approvo tutto come consiglia I: S1 e S5 nel lotto, id opzionale, cambio di tipo consentito anche se collegato, solo
> l'alias per il CSV».

1. `id` opzionale nell'upsert manuale, con lo schema nuovo `FAEventUpsertPoint`. `api sync` nel worktree; nel
   checkpoint dichiaro che l'API cambia **in modo additivo**.
2. S5 nel lotto: l'aggiornamento sul posto vale anche per gli eventi automatici, con la stessa funzione di F2.
3. Il cambio di tipo di un evento collegato è consentito. Un test sul caso SPLIT collegato a un ADJUSTMENT documenta
   cosa succede al calcolo.
4. F3: solo l'alias `value` → `amount` nell'import. L'export resta com'è.
5. S1 nel lotto. S2 (la fusione dell'import su data+tipo) è parte di F1. S3 e S4 vanno nel backlog.

Doc via `docs-writer`, solo inglese: «Dedup Strategy» di `events.md` e la pagina utente `data-editor`. File condivisi:
i cataloghi sono di O e il runner di N in questo lotto; se mi servono lo chiedo prima. Non mi servono: nessuna chiave
i18n nuova e nessuna registrazione nuova nel runner (i test vanno in file già registrati).

## Stato di esecuzione

| Step | Contenuto | Stato |
|---|---|---|
| E0 | Baseline, verifica dei 4 reperti in sola lettura, brief al coordinator | ✅ 2026-10-08 17:55 |
| E1 | Decisioni ricevute, ricerca per il disegno, questo piano | ✅ 2026-10-08 18:13 |
| E2 | Test rossi backend (test-author): API eventi, WAC split, servizi | ✅ 2026-10-08 19:24 |
| E3 | Test rossi frontend (test-author): unità DataEditor/CsvEditor, E2E editor eventi | ✅ 2026-10-08 19:24 |
| E4 | Correzione backend: schema, upsert sul posto, percorso per id, endpoint | ✅ 2026-10-08 19:35 |
| E5 | Correzione frontend: id nel payload, S1, S2, alias CSV, commento F4 | ✅ 2026-10-08 19:44 |
| E6 | `api sync`, ruff/black, prettier sui file toccati | ✅ 2026-10-08 19:46 |
| E7 | Gate sulla 6157 | ✅ 2026-10-08 20:01 |
| E8 | Doc (docs-writer), `mkdocs build` e `check-links` | ✅ 2026-10-08 20:29 |
| E9 | Pulizia, `git diff --check`, porte libere, checkpoint, FROZEN | ✅ 2026-10-08 20:32 |

> **Note implementazione (E2/E3)**: due test-author in parallelo, su file distinti. Ho letto i diff interi
> prima di lanciarli. Poi ho eseguito i rossi io, sulla 6157, uno alla volta, prima di qualsiasi edit di prodotto
> (HEAD `108a2adf5`):
>
> | Selettore | Esito | Perché rosso (motivo giusto) |
> |---|---|---|
> | `api assets-events` | 13 rossi / 13 verdi | evento collegato: 500 `FOREIGN KEY constraint failed` sul `DELETE`; evento non collegato: id 32 ≠ 31; gli altri 11: 422 `extra_forbidden` su `id` |
> | `api portfolio-wac` | 2 rossi / 10 verdi | il cambio di tipo dello SPLIT si ferma a 422 (`id` non ammesso) |
> | `services asset-source-guards` | 5 rossi / 24 verdi (le 2 guardie verdi) | S5 upsert e refresh: `IntegrityError` FK; doppioni storici: idem; id di un evento automatico e doppioni modificati per id: `ValidationError` su `id` |
> | vitest `DataEditor.test.ts` | 6 rossi / 53 verdi | import di un altro tipo → `edited` invece di `appended`; colonna `value` → 0 righe valide |
> | `front-asset asset-data-editor` | 3 rossi / 23 verdi | E1: DIVIDEND 12 resta + INTEREST 13 nuovo; E2: 0 righe valide, 2 errori; E3: `DELETE …/assets/events?ids=2026` |
>
> Log: `/tmp/libreFolio_i_ev_red_{api_assets_events,api_wac,svc,vitest,e2e}.log` (fuori dal repo).
> Il precondizionale del test «due righe sulla stessa chiave» è soddisfatto: un upsert senza id salva ancora due
> DIVIDEND nello stesso giorno, quindi il test non si salta.
>
> **⚠️ Fuori pista**: i due test-author hanno scambiato i file l'uno dell'altro per «un'altra sessione». È innocuo:
> i perimetri erano distinti e nessuno ha toccato i file dell'altro.

> **Note implementazione (E4)**:
> - `schemas/prices.py`: `FAEventUpsertPoint` (eredita `FAAssetEventPoint`, `id` opzionale, `from_attributes`),
>   `FAEventUpsert.events` lo usa, e il validatore `validate_unique_event_ids` risponde 422 «Duplicate event id».
> - `price_store.py`, `_upsert_asset_events`: niente più `DELETE` + `INSERT`. Raggruppa per (data, tipo), carica le
>   righe della **stessa** fonte in ordine di id, aggiorna sul posto quelle accoppiate, inserisce gli eventi in più;
>   i doppioni in eccesso confluiscono sull'id più basso dopo aver spostato lì le transazioni collegate. Commit a
>   blocchi di 1000 chiavi, come prima. Firma e valore di ritorno invariati (`refresh.py` non cambia).
>   `AssetEvent` non ha il listener `before_update`: `updated_at` lo scrivo io; idem per `Transaction` nell'`UPDATE`
>   di massa.
> - `bulk_upsert_events`: per ogni item, `_split_manual_events` → `_apply_manual_event_edits` (righe per id, solo
>   manuali e dell'asset, altrimenti `EVENT_NOT_EDITABLE`) → `_reject_event_key_conflicts` (`EVENT_KEY_CONFLICT`)
>   → modifica sul posto e `flush`; poi gli eventi senza id passano da `_upsert_asset_events`; un `commit` per item.
>   Tutto il controllo avviene prima della prima scrittura. Complessità invariata (8 ≤ 10), niente `noqa`.
> - Endpoint `assets.py`: 400 anche per `EVENT_NOT_EDITABLE` e `EVENT_KEY_CONFLICT`; docstring aggiornata.
> - `ruff check` e `black --check` puliti sui 3 file.
>
> Verde sulla 6157, uno alla volta: `api assets-events` 26/26 (nessun salto), `api portfolio-wac` 12/12,
> `services asset-source-guards` 29/29. Log: `/tmp/libreFolio_i_ev_green_{api_assets_events,api_wac,svc}.log`.

> **Note implementazione (E5)**:
> - `AssetDataEditorSection.svelte`: `dbEventId(row)` dà l'id del DB solo per una riga `original` con `rowId` tutto
>   cifre. Il payload dell'upsert porta `id` per le righe salvate (F1/F2). La cancellazione e la rimozione in memoria
>   usano lo stesso helper: una riga mai salvata non manda più una `DELETE` (S1). L'editor degli eventi passa
>   `importMatchKeys={['type']}` (S2). F4: il commento descrive la gomma senza conferma; citava anche una chiave
>   `dataEditor.cell.clearFieldConfirm` che non esiste in nessun catalogo.
> - `DataEditor.svelte`: prop `importMatchKeys` (default `[]`: prezzi e FX invariati), `uniqueRowId` per le righe che
>   l'import aggiunge (`D`, `D#2`…), `handleDateChange` cerca la riga per `rowId`. `handleAddRow` resta com'è: sceglie
>   sempre una data libera, quindi il suo `rowId` è già unico.
> - `CsvEditor.svelte`: `aliases?: string[]` in `CsvColumnDef`, cercati solo se l'etichetta manca. L'intestazione
>   attesa mostrata all'utente resta quella canonica.
> - `EventDataImportModal.svelte`: `amount` con `aliases: ['value']` e un commento sull'export. Nessuna chiave i18n.
> - Il client Zodios valida solo le risposte (`validate: 'response'`): `id` passa anche prima di `api sync` (E6).
>
> Verde: vitest `DataEditor.test.ts` 59/59 (erano 6 rossi); `front-asset asset-data-editor` 26/26 sulla 6157 (erano
> 3 rossi). Log: `/tmp/libreFolio_i_ev_green_{vitest,e2e}.log`.
>
> **⚠️ Fuori pista**: gli orari di E3, E4 ed E5 erano stimati, non letti. Li ho riallineati alle mtime dei log:
> E3 19:24 (E2E rosso alle 19:23), E4 19:35 (ultimo gate verde alle 19:35), E5 19:44 (E2E verde alle 19:43).

> **Note implementazione (E6)**:
> - `api sync`: exit 0. `generated.ts` e `openapi.json` sono ignorati da Git; nessun file tracciato è cambiato fuori
>   dai miei. Il client ha già `FAEventUpsertPoint` con `id?` opzionale: il build dell'E2E di E5 lo aveva rigenerato
>   prima di `api sync`. Cambio di API **additivo**: `id` opzionale, schema nuovo, 400 `EVENT_NOT_EDITABLE` e
>   `EVENT_KEY_CONFLICT`, 422 su un id ripetuto.
> - `ruff check` pulito sui 6 file backend (3 di prodotto, 3 di test).
> - `black --check`: 5 puliti; `test_portfolio_wac.py` no, ma era già così su HEAD (`git show HEAD:…` dà lo stesso
>   esito). I due hunk di black (righe 43 e 236) sono codice preesistente; le aggiunte del test-author (324–423,
>   520–638) sono pulite. Non lo riformatto: sarebbe un cambiamento estraneo.
> - `prettier --check` pulito sui 7 file frontend (4 di prodotto, 3 di test).
>
> Log: `/tmp/libreFolio_i_ev_{api_sync,lint_be,prettier}.log`, `/tmp/libreFolio_i_wac_black.log`.

> **Note implementazione (E7)**: tutto verde sulla 6157, uno alla volta, sull'albero finale.
>
> | Selettore | Esito |
> |---|---|
> | `api assets-events` · `api portfolio-wac` | 26 · 12 passati |
> | `api backup-export-extras` · `api market-data-wipe` · `api events-target-currency` | 8 · 5 · 7 passati |
> | `services asset-source-guards` · `services asset-source` | 29 · 61 passati |
> | `front-utility component-unit` | 111 file, 2861 test passati |
> | `front-asset asset-data-editor` · `asset-detail` · `asset-event-delete` | 26 · 31 · 4 passati |
> | `front check` | 0 errori, 0 avvisi |
> | `front build --debug` | exit 0 |
>
> Nessun salto. Porte 6157/6167 libere dopo ogni script. Il build segnala il download di MathJax fallito per un
> certificato SSL: è ambientale e preesistente, non blocca. Log: `/tmp/libreFolio_i_ev_gate_*.log`,
> `/tmp/libreFolio_i_ev_front_{check,build}.log`; script `/tmp/libreFolio_i_ev_gates_{be,fe}.sh`.

> **Note implementazione (E8)**: doc via docs-writer, solo inglese, 4 pagine (+109/−33):
> - `developer/backend/assets/events.md`: «Dedup Strategy» riscritta (aggiornamento sul posto per fonte, percorso
>   per id, regola dei conflitti, i tre codici 400, round trip del CSV);
> - `developer/architecture/database/assets_pricing.md`: la strategia di deduplicazione non è più DELETE+INSERT;
> - `developer/frontend/components/core-ui/data-editor.md`: `importMatchKeys`, `rowId` unici (`data#2`), `dbEventId`,
>   alias `value` del `CsvEditor`, comportamento dell'editor su un errore di salvataggio;
> - `user/assets/detail/data-editor.en.md`: cambio di tipo, reimport del CSV di backup, conflitti.
>
> Ho letto il diff intero e verificato nel codice ogni fatto citato: `PRICE_UPSERT_CHUNK_SIZE`, il messaggio
> «Event upsert failed» del refresh, l'impronta degli split in `compute_wac_iterative`, i nomi dei due test WAC,
> `in_use` nella cancellazione, il controllo dei conflitti prima delle scritture, la mappatura dei tre codici a 400,
> `importMatchKeys` con default `[]`, l'alias cercato dopo l'etichetta, la rotta del backup e l'ancora
> `#editing-an-asset`.
>
> - `mkdocs build`: exit 0, nessun WARNING né ERROR.
> - `check-links`: un solo rosso, D28 (`#rolling-return` assente in it/fr/es, dal link di `assets/[id]/+page.svelte`),
>   noto e non mio; più 3 gialli noti.
> - `translate-validate`: errori da 1786 a 1789. I +3 sono un `link-missing` per lingua su
>   `user/assets/detail/data-editor` (il link nuovo a `../create-edit.md#editing-an-asset`); per la stessa pagina gli
>   avvisi passano da 7 a 8 link e da 18 a 23 punti elenco. È debito di traduzione vero: it/fr/es non toccati, nessun
>   timbro.
>
> **⚠️ Fuori pista (E8)**:
> - Il perimetro è passato da 2 pagine a 4: `assets_pricing.md` descriveva ancora il DELETE+INSERT, e la pagina
>   core-ui del `DataEditor` l'abbinamento per sola data. Senza correggerle, la doc avrebbe contraddetto il codice.
> - La review di docs-writer ha trovato che **le mie 3 docstring di E4 esageravano la regola** di `EVENT_KEY_CONFLICT`
>   («lascerebbe due eventi manuali sulla stessa data e tipo»): due eventi senza id sulla stessa chiave vengono salvati
>   entrambi, senza 400. Le ho corrette, solo testo:
>   - `assets.py`, la docstring dell'endpoint, che è anche la descrizione OpenAPI;
>   - `price_store.py`, `bulk_upsert_events` e `_reject_event_key_conflicts`.
>
>   Poi: `ruff check` e `black --check` puliti sui 2 file; `api sync` exit 0, senza file tracciati cambiati
>   (`openapi.json` e `generated.ts` sono ignorati); `api assets-events` 26 passati sulla 6157, porta libera dopo.
> - Degli altri punti della review, tre diventano limiti residui (sotto). Il quarto, `architecture.md:316` («Bulk
>   upsert manual events»), non è sbagliato e resta com'è.
>
> Log: `/tmp/libreFolio_i_ev_docs_{tv_before,build,links,tv_after}.log`, `/tmp/libreFolio_i_ev_lint_doc.log`,
> `/tmp/libreFolio_i_ev_api_sync2.log`, `/tmp/libreFolio_i_ev_gate_doc_events.log`.

> **Note implementazione (E9)**: checkpoint, poi FROZEN.
> - Pulizia: cancellati senza aprirli i 54 file temporanei del lotto (log, diff, script, probe). **I log citati in
>   E2–E8 non esistono più**; i loro esiti restano registrati in questo piano.
> - `git diff --check` pulito. Delta: 17 file modificati più questo piano, non tracciato. Nessun file condiviso
>   (cataloghi, runner, CHANGELOG, nav); `openapi.json` e `generated.ts` sono ignorati da Git.
> - Porte 6157 e 6167 libere (`lsof` vuoto).
> - Privacy: nel delta e nel piano l'unico riscontro è il nome del ramo, già presente in 7 file del journal committati.
> - Target: `dev_release2` è a `70d02cd8e`, 17 commit oltre la mia base `108a2adf5`. L'unico file in comune è
>   `AssetDataEditorSection.svelte`, toccato da `65c1e40e6` di K (`count` → `n` nei due messaggi di cancellazione).
>   Fusione a tre vie simulata con `git merge-file` su copie in `/tmp`: nessun conflitto, entrambe le parti presenti
>   (`dbEventId` e `importMatchKeys` miei, `n:` di K alle righe 414 e 422). Copie cancellate dopo.
> - Commit proposti, 4, nei file `/tmp/libreFolio_commit_i_ev_{1,2,3,4}.txt` (oggetto ≤ 50, ASCII, righe ≤ 72): backend
>   con i suoi test; frontend con i suoi test; doc; journal.

## Verifica dei reperti (E0)

Tutti e quattro **confermati**, tutti già usciti nella v1.1.0. La prova rossa arriva in E2/E3; qui la prova nel codice.

| # | Reperto | Esito | Prova nel codice (righe di `108a2adf5`) |
|---|---|---|---|
| F1 | Cambiare il *Type* salva un evento nuovo e lascia il vecchio | **Confermato** | Il payload dell'editor (`AssetDataEditorSection.svelte:353–361`) è `{date, type, value, notes}`, senza id. `_upsert_asset_events` (`price_store.py:272–343`) cancella per chiave `(asset, date, type, provider)` e reinserisce: col tipo nuovo la chiave cambia, quindi la riga vecchia resta. |
| F2 | La modifica cancella e reinserisce: con una transazione collegata urta la FK `RESTRICT` | **Confermato** | FK `RESTRICT` su `Transaction.asset_event_id` (`models.py:832–840`), `PRAGMA foreign_keys=ON`. Una modifica a chiave invariata è DELETE + INSERT → `IntegrityError`; l'endpoint (`assets.py:1048–1050`) mappa a 400 solo `EVENT_CURRENCY_MISMATCH`, il resto è **500**. Un evento non collegato cambia id a ogni modifica. |
| F3 | Il CSV esportato ha `value`, l'import vuole `amount` | **Confermato** | Export `GET /backup/asset/{id}/events?format=csv`, `;`, intestazione `date;type;value;currency;source;provider_assignment_id;notes;created_at;updated_at` (`backup.py:286–311`). L'import (`EventDataImportModal.svelte:35–40`) richiede `amount`; `CsvEditor` abbina le intestazioni per nome (`:229–238`) → «Missing required columns: amount». |
| F4 | Un commento dice che la gomma chiede conferma | **Confermato (solo commento)** | `AssetDataEditorSection.svelte:79–84` parla di «eraser confirm flow» e di `clearFieldConfirm`. La gomma non chiede conferma (`ErasableNumberCell.svelte:73–80`, scelta del 2026-04-22) e la chiave `clearFieldConfirm` non esiste nei cataloghi. Nessun test: è un commento. |

Reperti laterali trovati durante la verifica:

| # | Reperto | Decisione |
|---|---|---|
| S1 | Una riga aggiunta e poi eliminata prima del salvataggio ha `rowId` = data: `parseInt("2026-09-20")` = 2026 → `DELETE /assets/events?ids=2026`, e la cancellazione non è limitata all'asset (`delete_events_bulk`, `:816–882`). Anche la rimozione in memoria (`:399–403`) usa `parseInt`. Il commento in `eventsToEventRows` voleva evitare proprio questo, ma copriva un solo percorso di creazione. | Nel lotto |
| S2 | `DataEditor.handleImport` (`:521–560`) abbina solo per data: vince la prima riga di quella data. Se è un evento automatico (readonly) l'import salta anche quando c'è una riga manuale; se è una riga manuale di un altro tipo, il tipo viene sovrascritto (con F1 corretto diventerebbe un cambio di tipo silenzioso). | Nel lotto, come parte di F1 |
| S3 | `handleBulkDelete` (`:506–515`) non salta gli eventi automatici readonly. | Backlog: I-10 |
| S4 | La mini-modale riconosce l'evento appena creato da (tipo, data): può prendere un evento automatico. | Backlog: I-10 |
| S5 | L'aggiornamento dal provider (`refresh.py:556`) usa la stessa funzione: un evento automatico collegato a una transazione fa fallire il DELETE, e l'errore finisce in `errors`. | Nel lotto |

## Disegno

### Backend

**`_upsert_asset_events` (`price_store.py`): aggiornamento sul posto.** Stessa firma, stesso valore di ritorno (numero
di eventi), stessi chiamanti (`price_store.py:663`, `refresh.py:556`; non ci sono altri `AssetEvent(` nel backend).

1. Gli eventi passano da Pydantic come oggi (`FAAssetEventPoint`, sottoclassi incluse).
2. Raggruppo per chiave `(date, str(type))`, nell'ordine d'arrivo.
3. Divido in blocchi di gruppi interi fino a `PRICE_UPSERT_CHUNK_SIZE` (1000) eventi: una chiave non si spezza mai tra
   due blocchi. Un commit per blocco, come oggi.
4. Per blocco: `select(AssetEvent)` su `asset_id`, provider (`IS NULL` se manuale, `==` altrimenti) e
   `date IN (…)`, ordinato per id; il tipo si confronta in Python (`AssetEventType` è uno `StrEnum`).
5. Per ogni chiave, accoppio in ordine le righe esistenti con gli eventi in arrivo:
   - coppia → aggiorno `value`, `currency` (`code` o la valuta di default), `notes`, `updated_at`;
   - eventi in più → `INSERT`;
   - righe in più (doppioni storici) → prima sposto le transazioni collegate sulla riga che resta (aggiornando anche il
     loro `updated_at`, così le impronte delle cache sulle transazioni cambiano), poi le cancello.
6. Le chiavi assenti dal lotto non si toccano. È la stessa semantica di prima («stessa data e tipo sostituisce»), ma
   l'id resta e la FK non si urta più.

Le cache: l'impronta degli split nel motore (`portfolio_engine.py:2445–2448`) contiene id, data e rapporto dell'evento,
quindi un aggiornamento sul posto la cambia comunque; un cambio di tipo da SPLIT toglie la riga dall'insieme dei
collegati a split, che è anch'esso nell'impronta. Le altre letture degli eventi (`yield_on_cost.py:807–860`,
`lots_analysis_service.py:649`, `portfolio_service.py:162`) leggono dal DB a ogni calcolo.

**Schema (`schemas/prices.py`).**

- Nuovo `FAEventUpsertPoint(FAAssetEventPoint)` con `id: Optional[int] = Field(None)` e
  `ConfigDict(from_attributes=True)`.
- `FAEventUpsert.events` diventa `List[FAEventUpsertPoint]`, con un validatore che rifiuta id ripetuti (422).
- `FAAssetEventPoint` non cambia: è condiviso con l'output dei provider.
- Perché `from_attributes`: senza, un `FAAssetEventPoint` passato da Python a `FAEventUpsert` viene rifiutato
  (`model_type`), e 4 file di test esistenti lo fanno (`test_assets_events`, `test_market_data_wipe`,
  `test_backup_export_extras`, `test_events_target_currency`). Con `from_attributes` un punto evento senza id è un
  punto di upsert valido con `id = None`; i campi extra restano vietati. Provato in un processo a parte.

**`bulk_upsert_events`, per ogni elemento, dopo il controllo dell'asset e la Policy D.**

1. Separo gli eventi con id da quelli senza.
2. Carico le righe per id. Id sconosciuto, riga di un altro asset o riga di un provider → `EVENT_NOT_EDITABLE`, prima
   di qualsiasi scrittura.
3. Conflitti, controllati prima di scrivere (`EVENT_KEY_CONFLICT`):
   - chi **si sposta** (chiave finale diversa da quella attuale) non può finire sulla chiave finale di un altro
     aggiornamento per id, né sulla chiave attuale di una riga manuale dello stesso asset fuori dal lotto. Lo scambio
     tra due righe del lotto è consentito;
   - chi **resta** può condividere la chiave con altri che restano: i doppioni storici restano modificabili;
   - un evento senza id non può avere la chiave finale di un aggiornamento per id.
4. Applico gli aggiornamenti per id (data, tipo, valore, valuta, note, `updated_at`), poi `flush`.
5. Gli eventi senza id passano da `_upsert_asset_events`; se non ce ne sono, commit esplicito. Il conteggio è la somma.

**Endpoint (`assets.py:1049`).** La lista dei 400 diventa `EVENT_CURRENCY_MISMATCH`, `EVENT_NOT_EDITABLE`,
`EVENT_KEY_CONFLICT`. Docstring aggiornata.

### Frontend

- **`AssetDataEditorSection.svelte`.**
  - Un helper `dbEventId(row)`: l'id solo se `originalStatus === 'original'` e il `rowId` è tutto cifre.
  - Il payload manda `id` per le righe modificate che ne hanno uno (F1/F2).
  - S1: la cancellazione e la rimozione in memoria usano `dbEventId`; una riga aggiunta e poi eliminata non manda
    nulla al server.
  - S2: l'editor degli eventi passa `importMatchKeys={['type']}`.
  - F4: il commento descrive la gomma com'è: niente conferma, il ripristino della riga annulla; chiavi `notSet` e
    `clearField`.
- **`DataEditor.svelte`.**
  - Prop `importMatchKeys?: string[]` (default `[]`): l'import abbina su data più quelle chiavi. Preferisce la prima
    riga non readonly; se combaciano solo righe readonly, salta.
  - Le righe aggiunte dall'import hanno un `rowId` unico: la data, oppure `data#2`, `data#3`… se è già preso. Per prezzi
    e FX non cambia nulla (abbinano per data, quindi non aggiungono mai una seconda riga sulla stessa data).
  - `handleDateChange` riceve il `rowId`, non la data: con due righe aggiunte sulla stessa data spostava la prima.
- **`CsvEditor.svelte`.** `CsvColumnDef` riceve `aliases?: string[]`: se l'etichetta non c'è nell'intestazione, si
  cercano gli alias.
- **`EventDataImportModal.svelte`.** `amount` riceve `aliases: ['value']`. Nessuna chiave i18n.

## Test (rossi prima, via test-author)

| Selettore | File | Cosa |
|---|---|---|
| `api assets-events` | `backend/test_scripts/test_api/test_assets_events.py` | F2: modifica di un evento manuale collegato (senza id e con id) → 200, stesso id, transazione ancora collegata; evento non collegato → stesso id. F1: id + tipo nuovo → un solo evento, stesso id. Guardie: id di un altro asset o sconosciuto → 400 `EVENT_NOT_EDITABLE`; spostamento in conflitto → 400 `EVENT_KEY_CONFLICT` e nulla cambia; scambio → 200; evento senza id sulla chiave di un aggiornamento → 400; id ripetuto → 422 col messaggio giusto. |
| `api portfolio-wac` | `backend/test_scripts/test_api/test_portfolio_wac.py` | Decisione 3: BUY, SPLIT manuale, ADJUSTMENT collegato; poi il tipo dello SPLIT diventa PRICE_ADJUSTMENT. Stesso id, transazione ancora collegata; effetto, WAC e pool prima e dopo. |
| `services asset-source-guards` | `backend/test_scripts/test_services/test_asset_source_upsert_guards.py` | S5: upsert dal provider su un evento automatico collegato → nessun errore, stesso id, valore aggiornato, ancora collegato. Doppioni storici: la riga in più sparisce e la sua transazione passa alla riga che resta. Id di un evento automatico → `EVENT_NOT_EDITABLE`. |
| `component-unit` | `frontend/src/lib/components/ui/data-editor/DataEditor.test.ts` | S2: abbinamento su data+tipo, preferenza per le righe non readonly, `rowId` unici. Alias del `CsvEditor` sull'intestazione dell'export reale. |
| `front-asset asset-data-editor` | `frontend/e2e/assets/asset-data-editor.spec.ts` | F1 via UI; F3 (CSV dell'export → import abilitato); S1 (riga aggiunta ed eliminata → nessuna `DELETE /assets/events`). F2 via UI se il setup resta leggero. |

I payload con `id` nei test backend si scrivono come dict, non con `FAEventUpsertPoint`: su HEAD un'importazione che
fallisce romperebbe tutto il modulo, non solo i test nuovi.

## Gate (E7)

Uno alla volta, sulla 6157:

1. `api assets-events`, `api portfolio-wac`, `api backup-export-extras`, `api market-data-wipe`,
   `api events-target-currency` (gli ultimi tre costruiscono `FAEventUpsert` da Python: provano la compatibilità dello
   schema);
2. `services asset-source-guards`, `services asset-source`;
3. `component-unit`;
4. `front-asset asset-data-editor`, `front-asset asset-detail`, `front-asset asset-event-delete`;
5. `front check`, `front build --debug`.

## Definizione di fatto

- F1, F2, F3, S1, S2, S5 corretti, ognuno con un test che era rosso su `108a2adf5` ed è verde dopo.
- F4: il commento descrive il comportamento vero.
- Il test della decisione 3 documenta l'effetto sul calcolo.
- Gate verdi, oppure rossi noti fuori dal mio perimetro, con la prova.
- Doc inglese allineata; debito di traduzione dichiarato, nessun timbro.
- Checkpoint con l'elenco «confermato / non confermato», il cambio additivo dell'API, S3/S4 per il backlog e i limiti
  residui.

## Limiti residui (non li correggo)

> **Esito (verifica d'archivio, 2026-10-09).** Ogni limite qui sotto, con S3 e S4, ha una voce in
> `Phase_0/38_postReleaseBacklog/README.md`:
>
> - «I-09 · tipo di evento non validato → 500»: N1;
> - «I-10 · robustezza dell'editor degli eventi (S3/S4)»: S3, S4, la riga nuova senza id che si fonde in silenzio,
>   le modifiche inviate prima delle cancellazioni, il messaggio d'errore generico;
> - «I-11 · limiti del round-trip CSV degli eventi»: le date ripetute scartate da `CsvEditor`, `source` e `currency`
>   ignorate dall'import, il selettore della data che disabilita le date già usate;
> - «I-12 · guardie server degli eventi»: `DELETE /assets/events?ids=…` non limitato all'asset, il salvataggio per
>   elemento di `bulk_upsert_events`.

- `CsvEditor` scarta tutte le righe con una data ripetuta (`:416–436`): un export con due eventi nella stessa data si
  reimporta solo in parte. L'import prosegue con le altre righe.
- L'import ignora `source`: le righe dei provider reimportate diventano eventi manuali. Se il provider le rimanda,
  nascono doppioni, perché le chiavi sono separate per fonte.
- L'import ignora anche la colonna `currency`, per i prezzi e per gli eventi. Il salvataggio usa la valuta dell'asset,
  quindi un backup preso prima di un cambio di valuta tornerebbe con gli importi rietichettati, senza conversione.
- Nell'editor il selettore della data disabilita ogni data già usata (`DataEditor.svelte:151–161`), anche per gli
  eventi, dove la chiave è (data, tipo): un secondo evento nella stessa data entra solo con l'import.
- `bulk_upsert_events` lavora per elemento: un errore su un elemento lascia salvati quelli prima. Era già così con la
  Policy D.
- `DELETE /assets/events?ids=…` non è limitato all'asset: S1 lo rendeva pericoloso; dopo la correzione l'editor manda
  solo id veri, ma la guardia lato server resta da valutare.
- **N1, reperto nuovo, preesistente, da segnalare.** Il tipo di un evento non è validato:
  - `FAAssetEventPoint.type` è un `str` libero, e la colonna è un `VARCHAR` senza vincolo;
  - un tipo minuscolo o sconosciuto (`dividend`) viene quindi scritto;
  - da lì ogni lettura ORM di quella riga solleva `LookupError`: le letture degli eventi dell'asset e i salvataggi
    successivi nelle stesse date vanno in 500.
  - Dalla UI lo raggiunge un CSV scritto a mano: l'import confronta i tipi alla lettera e il salvataggio li manda così
    come sono.
  - A `108a2adf5` era uguale (`type=evt_type`, grezzo).
  - Prova: probe su SQLite in memoria, senza file, server o corsia, con lo script cancellato dopo l'uso. La scrittura
    riesce, la lettura ORM solleva `LookupError` e la riga grezza contiene `dividend`.
  - Correzione possibile, fuori da questo lotto: un validatore sul `type` che normalizza in maiuscolo e rifiuta i
    valori fuori da `AssetEventType` con un 422.
  - Le mie note di sessione dicevano «500 al flush»: era impreciso, e il probe l'ha corretto.
- **Una riga nuova senza id si fonde in silenzio con un evento salvato.** Se finisce sulla chiave di un evento manuale
  che l'elemento non modifica, `_upsert_asset_events` aggiorna quell'evento sul posto. Dalla UI ci si arriva con un
  import seguito da un cambio di tipo: la tabella mostra due righe, e dopo il ricaricamento ce n'è una. A `108a2adf5` il
  risultato visibile era lo stesso (lì per DELETE+INSERT), quindi non è una regressione. Backlog: un controllo dei
  doppioni di chiave lato client, prima dell'invio.
- **Le modifiche partono prima delle cancellazioni.** Nello stesso salvataggio, spostare un evento sulla chiave di uno
  appena eliminato dà `EVENT_KEY_CONFLICT`, perché l'eliminato è ancora nel DB. La pagina utente dice di salvare prima
  la cancellazione. Backlog: inviare le cancellazioni per prime.
- **Il messaggio d'errore è generico.** Su un 400 il catch di `AssetDataEditorSection.svelte` (`:463–467`) mostra il
  messaggio di axios («Request failed with status code 400»), non il `detail` del server. Era già così; un testo
  vero richiede chiavi i18n, cioè i cataloghi di O. Backlog.
