# Performance charts — bugfix: i marcatori degli eventi spariscono con «Tutti» e i prezzi in cache

**Stato:** COMPLETATO, FROZEN in attesa del commit (16:22). Lavoro approvato dal developer il 2026-10-07 («ok
affidare a I la risoluzione», via coordinator alle 15:22). Il brief con diagnosi, correzione e test è andato al
coordinator alle 15:31.
**Workstream:** I (grafici performance) · ramo `e-alfy-performance-charts-plan` · coordinatore
`c8328a01-f208-4ade-a352-0486d1f14de2`.
**Baseline:** HEAD = `dev_release2` = `d07412899`, dopo il fast-forward da `dd538d650` (coordinator, 15:25). Albero
pulito, rimisurato alle 15:32.
**Lane:** suite `6157` + `/tmp/librefolio-r2-i`, solo `dev.py test …`, un comando alla volta. La `6167` qui non serve.
La coverage gira nella `6150`: un timeout si rilancia da solo, senza altro in parallelo.
Preambolo: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py …`.

Precedenti e collegati:

- Piano precedente: [plan-phase00PerformanceChartsRound4-PostMergeReview.prompt.md](plan-phase00PerformanceChartsRound4-PostMergeReview.prompt.md),
  che punta qui.
- Il concetto del devWiki che descrive questa classe di difetti:
  [discard-the-answer-not-the-question.md](../../../../LibreFolio_devWiki/wiki/concepts/discard-the-answer-not-the-question.md).
  Il suo caso 2 cita proprio la `resolveMaxStartFromChartData()` tardiva.
- Lo scenario della gallery che l'ha trovato è di M: `frontend/e2e/gallery.spec.ts:3325`. Non lo tocco e non l'ho
  eseguito (vedi B4); con la correzione dovrebbe diventare verde.
- CHANGELOG: nessuna riga. Il difetto non è mai uscito in una release.

## Stato di esecuzione

| Step | Contenuto | Stato |
|---|---|---|
| B0 | Baseline e diagnosi, in sola lettura | ✅ 2026-10-07 15:32 |
| B1 | Brief al coordinator e questo piano | ✅ 2026-10-07 15:32 |
| B2 | Test di regressione E2E (test-author), **rosso su HEAD** | ✅ 2026-10-07 16:12: 2 rossi all'asserzione finale |
| B3 | Correzione in `+page.svelte` | ✅ 2026-10-07 16:14: due righe in `loadChartData()` |
| B4 | Verde del test nuovo, poi i gate | ✅ 2026-10-07 16:20: 2/2, spec 31/31, svelte-check 0/0 |
| B5 | Pulizia, handoff, FROZEN | ✅ 2026-10-07 16:22: porte libere, copie cancellate, FROZEN |

## Diagnosi

File: `frontend/src/routes/(app)/assets/[id]/+page.svelte`, funzione `loadChartData()` (righe di `d07412899`).

1. `:1642` memorizza `const requestedStart = dateStart`, la data della richiesta. Con «Tutti» è l'ancora del
   sentinella `min`.
2. `:1654`: `dataRequestIsCurrent()` vale solo se, tra le altre cose, `dateStart === requestedStart`.
3. Sul **hit** della cache prezzi, `:1705` `resolveMaxStartFromChartData()` porta `dateStart` alla prima data dei
   prezzi. Poi il codice prosegue (commento `:1707`) per chiedere i soli eventi e i segnali del backend.
4. Alla risposta, `:1753` trova `dateStart !== requestedStart` e la scarta.

È la richiesta stessa ad aver spostato la data, non una richiesta più nuova: la guardia scambia la propria
risoluzione per un'interferenza.

**La storia.**

- La risoluzione anticipata sul hit viene da `5b9dddb45` (23/07).
- La ricaduta per gli eventi viene da `b45f5afbb` (06/08).
- La guardia `dateStart === requestedStart` viene da `2d22130bd` (17/09). **La regressione è mia**: la guardia è
  giusta, ma non sapeva della risoluzione sul hit.

**Cosa perde la risposta scartata.**

- `events`: né marcatori nel grafico né eventi nell'editor dei dati. Dopo `reloadPage()` (`:1376`, che azzera
  `events`) non resta nulla da disegnare.
- I risultati dei segnali calcolati dal backend: `applyBackendSignalResults` non parte, e gli overlay mancano.
- In modalità rendimento di calendario `calendarReturnView` resta `'loading'`, perché lo stato è impostato prima
  dell'`await`. La pagina resta `data-busy=true` (`:2680`) e i confronti del calendario non si aggiornano.

**Il `return` di `:1807`, nel `catch`.**

- Nel miss, `dateStart` cambia solo a `:1805`, l'ultima istruzione del `try`. Quindi il `return` scarta solo le
  richieste davvero superate: **corretto, non salta nulla di visibile.**
- Nel hit, invece, inghiotte gli errori: non imposta `signalRequestFailed` né lo stato d'errore del calendario, e non
  scrive nulla in console. È lo stesso difetto, e la stessa correzione lo risolve.
- Il `finally` usa `requestIsCurrent()`, senza confronto della data: `loading` e `signalsLoading` tornano comunque a
  `false`.

**Come ci si arriva.**

- *Dalla lista.* Con l'intervallo globale «Tutti», la lista (`assets/+page.svelte:632`, `:708-710`) chiede
  `[2000-01-01, oggi]` e marca quell'intervallo nello store prezzi condiviso. La chiave è `(id, valuta)`, la stessa
  del dettaglio con la valuta nativa. Un clic sulla card porta a una navigazione lato client, e quindi al hit.
- *Dentro la pagina.* «Tutti» (miss) → 1A (hit, eventi dell'ultimo anno) → «Tutti» (hit e risoluzione → risposta
  scartata). Restano gli eventi di 1A, e i più vecchi mancano.
- La pagina FX non è colpita: il suo `current()` confronta solo versione, slug e sessione.

## Correzione (B3)

`const requestedStart` → `let requestedStart`. Subito dopo `resolveMaxStartFromChartData()` nel ramo del hit,
`requestedStart = dateStart;`, con un commento di una riga: è questa richiesta ad aver risolto «Tutti», quindi la sua
identità si sposta con lei.

- È sicura: tra la cattura e la risoluzione non c'è nessun `await`, e nessun'altra richiesta può inserirsi.
- Una sola modifica sistema eventi, segnali, calendario e il `catch` del hit.
- **Alternativa scartata:** rimandare la risoluzione del hit a fine `try`, come nel miss. Durante l'attesa asse e
  selettore resterebbero sull'ancora larga, e cambierebbe più comportamento di quanto serve.
- **Fuori scope, invariato:** sul hit la richiesta degli eventi parte dalla prima data dei prezzi; nel miss la prima
  richiesta parte dall'ancora. I caricamenti successivi usano comunque la data risolta.

## Test (B2)

E2E in `frontend/e2e/assets/asset-detail.spec.ts`, il mio spec; nessun altro ramo attivo lo tocca. Lo scrive
test-author.

- Asset sintetico con `page.route`, come `mockDetailAssetWithGlobalTransactions` (`:53`). La rotta dei prezzi
  risponde a ogni voce; aggiunge un DIVIDEND quando la richiesta ha `include_events`.
- **Test 1, dalla lista:**
  1. lista;
  2. «Tutti» nel selettore globale;
  3. clic sulla card per id;
  4. il dettaglio deve inviare una query `include_price:false` + `include_events:true`, che prova il hit;
  5. il marcatore dell'evento deve comparire nel grafico.
- **Test 2, dentro la pagina:** «Tutti» → 1A → «Tutti», con un evento più vecchio di un anno, che deve tornare.
- Prima del fix i due test devono essere rossi **per il motivo giusto**: la query del hit parte, il marcatore no.

## Gate (B4)

- Il test nuovo: verde.
- Lo spec `front-asset asset-detail` intero.
- `front check`.
- Prettier sul file della pagina e sullo spec.
- `git diff --check`.

## Definition of done

- Il test nuovo è rosso su `d07412899` e verde con la correzione, con le prove registrate qui.
- Lo spec intero e `front check` sono verdi, oppure ogni rosso è spiegato con il triage.
- Le porte 6157 e 6167 sono libere e le copie di lavoro in `/tmp` sono cancellate.
- Messaggi di commit pronti per il coordinator; poi FROZEN.

## Registro

### B0 e B1 — baseline, diagnosi, brief e piano (2026-10-07 15:32)

> **Note implementazione**: baseline verificata: HEAD = `d07412899` = `dev_release2`, 0 voci in `git status`, nessun
> listener su 6157 e 6167. Diagnosi in sola lettura sulla pagina, sulla lista, sulla pagina FX, sullo scenario della
> gallery e sulla storia con `git log -L`. Le righe del coordinator coincidono con `d07412899`. Tra `dd538d650` e
> `d07412899` la pagina è cambiata in 3 hunk piccoli; uno è `rearmMaxPendingBeforeReload()` (`:1387`), che riarma
> «Tutti» prima di `reloadPage()` e non tocca il difetto.
>
> **⚠️ Fuori pista — la data dir della corsia è nuova.** Il coordinator assegna `/tmp/librefolio-r2-i`, non più
> `/tmp/librefolio-r2-i-charts`. Non esiste ancora nessuna delle due. Nessun bootstrap a mano: ogni run `front-*`
> ripopola da sé il DB della corsia (`_frontend_common.py:150`).

### B2 — il test di regressione, rosso su HEAD (2026-10-07 16:12)

> **Note implementazione**: test-author ha scritto il test senza eseguire nulla, tranne Prettier sul file. Ha
> aggiunto le righe `8101–8339` in coda a `frontend/e2e/assets/asset-detail.spec.ts`, e non ha toccato altro.
>
> - Un helper autonomo, `mockCacheHitEventsAsset(page, assetId)`:
>   - 600 chiusure giornaliere fino a oggi e due DIVIDEND: uno vecchio a −500 giorni e uno recente a −45;
>   - prezzi ed eventi filtrati sull'intervallo chiesto, e gli eventi solo con `include_events`;
>   - le `notes` sono dati del test, e quella del dividendo recente dice da quale data è stato chiesto;
>   - registra ogni voce **dopo** `fulfill`, quindi una voce del registro significa «risposta consegnata».
> - Due id sintetici che nessun altro spec usa, `920071` e `920072`, uno per test. Niente scritture nel DB.
> - Il lettore dei marcatori legge le `notes` dalle serie scatter di `__lfChart`. Non legge testo tradotto né il nome
>   della serie, che è inglese fisso.
> - Describe: `All-range event markers on a price-cache hit`. Test:
>   - **A**, `keeps the event markers when the detail opens from a list that already cached All` (`:8263`): la
>     lista su «Tutti», poi il clic lato client sulla card;
>   - **B**, `restores older event markers when All follows a shorter preset` (`:8301`): «Tutti» → 1A → «Tutti»
>     nella pagina.
> - Prima dell'asserzione sui marcatori, ogni test prova il percorso. A verifica che la query dei soli eventi
>   (`include_price:false`) parta, e parta dalla prima data dei prezzi. B verifica che il primo «Tutti» disegni i due
>   dividendi e che 1A tolga il vecchio.
>
> Comando, nella corsia:
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir
> /tmp/librefolio-r2-i front-asset asset-detail "All-range event markers on a price-cache hit"`, log
> `/tmp/libreFolio_i_evt_red.log`, 4m 03s.
>
> **Esito: 2 falliti, tutti e due all'asserzione finale; tutte le verifiche di percorso passano.**
>
> | test | riga | atteso | ricevuto |
> |---|---|---|---|
> | A | `:8291` | i due dividendi | `[]`: è il sintomo di M, «route answered 1 event, chart draws none» |
> | B | `:8337` | il vecchio e il recente chiesto dalla prima data | solo il recente chiesto dall'inizio di 1A (`2025-10-07`): gli eventi di 1A |
>
> - Il rosso misura il codice di HEAD. Il backend condiviso, all'avvio, ha ricostruito la build alle 16:09:42 dai
>   sorgenti correnti. La pagina ha mtime 15:25, dal fast-forward. Il controllo del runner che segue dice quindi «build
>   up to date».
> - Il DB della data dir nuova è stato popolato dal runner. Dopo il run la porta 6157 è libera.

### B3 — la correzione (2026-10-07 16:14)

> **Note implementazione**: due righe in `loadChartData()`, nient'altro.
>
> - `:1642`: `const requestedStart` → `let requestedStart`.
> - `:1706–1707`, subito dopo `resolveMaxStartFromChartData()` nel ramo del hit: `requestedStart = dateStart;`, con
>   il commento `This request resolved "All" itself: track the resolved start, so its own answer is not taken for a
>   stale one.`
>
> Verifiche statiche:
> - In `loadChartData()`, `requestedStart` compare solo in `:1642`, `:1654` (`dataRequestIsCurrent`) e `:1707`. Le
>   altre occorrenze del file (`:2342`, `:2543`) sono `const` locali di altre funzioni.
> - `resolveMaxStartFromChartData()` assegna `dateStart` in modo sincrono, quindi la riga nuova legge la data già
>   risolta.
> - Fuori da «Tutti» (`isMaxPending` falso) la funzione non fa nulla e l'assegnazione riscrive lo stesso valore: i
>   cache hit degli altri preset non cambiano.
> - Una richiesta più nuova resta scartata dal contatore `chartRequestGeneration`. Un cambio d'intervallo resta
>   scartato da `dateStart === requestedStart`, che ora confronta con la data risolta.

### B4 — il verde e i gate (2026-10-07 16:20)

> **Note implementazione — il test nuovo è verde (16:16).** Stesso comando del rosso, log
> `/tmp/libreFolio_i_evt_green.log`, 2m 06s:
>
> - A (`:8263`) passa in 2.3 s e B (`:8301`) in 1.6 s; nel rosso ciascuno impiegava circa 14 s, fino allo scadere
>   dell'asserzione finale.
> - La build è stata ricostruita dal backend condiviso alle 16:16:00, dopo l'ultima modifica della pagina (16:13:40).
>   La source map del nodo della pagina contiene il commento nuovo.
> - Il DB snapshot è `00_archive/test-db_20261007_161623.tar.xz`. Dopo il run la porta 6157 è libera.
>
> **Note implementazione — i gate (16:20).**
>
> | gate | comando | esito |
> |---|---|---|
> | spec intero | `… dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i front-asset asset-detail`, log `/tmp/libreFolio_i_evt_spec.log` | **31/31** in 2.1 min (run 2m 28s), compreso `calendar-return primary mode…` (1.1 min); snapshot `test-db_20261007_161921` |
> | tipi | `… dev.py front check`, log `/tmp/libreFolio_i_evt_check.log` | svelte-check **0 errori, 0 warning** |
> | formato | `frontend/node_modules/.bin/prettier --check` sulla pagina e sullo spec | pulito |
> | spazi | `git diff --check` | pulito |
>
> - Il delta è di 4 path: la pagina (+3/−1), lo spec (+239), questo piano (nuovo), il link «Seguito» nel piano del
>   round 4 (+3).
> - Le porte 6157 e 6167 sono libere.
>
> **⚠️ Fuori pista — lo scenario della gallery non l'ho eseguito.** `gallery.spec.ts:3325` scrive gli screenshot
> delle 8 combinazioni in `mkdocs_src/docs/gallery/`, che è tracciato, e lo scenario è di M. Il suo percorso è: lista,
> dettaglio per nome, poi «Tutti» scelto nella pagina con i prezzi già in cache. Il meccanismo è lo stesso: «Tutti»
> risolto su un cache hit, nel ramo del hit di `loadChartData()`. Il test A lo prova con la cache riempita dalla
> lista, il test B con «Tutti» scelto nella pagina.

### B5 — pulizia, handoff, FROZEN (2026-10-07 16:22)

> **Note implementazione**:
>
> - Nessun server attivo; le porte 6157 e 6167 sono libere (`lsof -nP -iTCP:<porta> -sTCP:LISTEN` senza output).
> - Ho cancellato le tre copie di lavoro in `/tmp` (`libreFolio_i_evt_{page,list}_d074.svelte`,
>   `libreFolio_i_evt_gallery_d074.ts`): erano codice tracciato di `d07412899`, senza dati privati. `ls` conferma.
> - Restano come prove i 5 log `/tmp/libreFolio_i_evt_{red,green,spec,check,prettier}.log`, con dati mock della
>   corsia.
> - Messaggi di commit proposti, ASCII, oggetto ≤ 61 caratteri:
>   1. `/tmp/libreFolio_commit_i_evt_01-fix.msg`, `fix(assets): keep event markers when All hits the price cache`:
>      la pagina e lo spec insieme, così nessun commit contiene un test rosso;
>   2. `/tmp/libreFolio_commit_i_evt_02-journal.msg`, `docs(journal): record events-on-cache-hit bugfix`: questo piano
>      e il link «Seguito» nel piano del round 4.
> - Nessuna riga nel CHANGELOG: il difetto non è mai uscito in una release.
> - Handoff al coordinator, poi FROZEN.
