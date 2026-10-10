# Piano — fase 00, Danske Bank, passo 5: rilevare di nuovo i plugin dei file (voce 8, opzione A)

> **Stato**: ✅ chiuso e integrato: `b0abeb07d` (fix(brim): re-detect plugins, lock sidecar writes), con la doc in `2b1a9d79f` (verifica del 2026-10-09 su `3cceb4f90`). Rinviato: `get_file_path` sull'event loop, in `Phase_0/38_postReleaseBacklog/README.md`, voce L5.
> - Al checkpoint: ✅ approvato (2026-10-06): via del developer, portato dal coordinatore, con i requisiti in §0. Base del codice: `a7d0b37ec` (il treno 1, con H, V1 e R5).
>
> - Viene da: [plan-phase00BrimDanskeBankStep4Implementation.prompt.md](plan-phase00BrimDanskeBankStep4Implementation.prompt.md), §18 (analisi della voce 8) e §19.5 (scelta del developer).
> - Workstream L, issue #26. Ramo `e-alfy-l-danske-bank`, base `172b8e616` (V1).

## 0. Decisioni

- **Developer** (ask_user, testuale): «A — rilevare di nuovo quando i plugin cambiano (Consigliata)».
- **Coordinatore**: va nella **1.2, prima del taglio**. Il motivo: con la 1.2 arriva Danske, e chi aggiorna dalla 1.1.0 ha file caricati senza quel plugin, che altrimenti non entrerebbero mai in un set. Superfici previste: `brim_provider.py` ed eventualmente `brokers.py`; se ne servono altre, vanno dette qui.
  - ⚠️ Correzione (§8.3): per i file della 1.1.0 la voce 8 aggiorna i plugin proposti, ma non forma il set, perché la 1.1.0 non salvava `batch_id`; la coppia va ricaricata, insieme.
- **Via del developer** (testuale, portato dal coordinatore, 2026-10-06): «Approvo le raccomandazioni (Consigliato)». Quindi D1, D2 e D3 di §5 sono chiusi:
  - **D1 → A-persist**: il ricalcolo si salva nel sidecar, una volta per versione;
  - **D2 → la firma è la versione dell'app** (`get_version()`);
  - **D3 → il costo una tantum** della prima lettura dopo un aggiornamento, in un thread, va bene.
- **Concessione su `brokers.py`** (coordinatore): solo le due chiamate dirette, la lista (`:687`) e `_get_brim_file_with_access` (`:135`), spostate in `asyncio.to_thread`. Nessun ramo tocca il file.
- **Requisito in più del coordinatore: il lock vale anche fra processi.** In Docker c'è un solo worker, ma il runner e Playwright possono avviare il backend con più worker (`SERVER_WORKERS`, `dev.py server --workers N`). Un parse che sposta il file in un processo, mentre un altro riscrive il vecchio sidecar, lo farebbe risorgere. Quindi:
  - un lock consultivo su file **per broker** (`fcntl.flock` su un file di lock nella cartella dei report del broker), preso da ogni scrittura dei metadati del broker;
  - la scrittura atomica ricontrolla, sotto il lock, che il sidecar sia ancora al suo posto: un sidecar spostato non si riscrive mai al vecchio indirizzo;
  - un test con due processi, o almeno con due thread più una prova di `flock`, scritto prima dal test-author.
- **F1 dentro la voce 8** (coordinatore): due combine concorrenti dello stesso set creano oggi due file combinati (§19.10 del passo 4). Lo stesso lock per broker copre il riuso e il salvataggio in `combine_set`, col rosso «due combine in parallelo → un solo combinato».
- **Ordine** (coordinatore): voce 8 con F1 → robustezza dell'upload, F2–F4 → il bottone «Escludi» tolto più R6. Un checkpoint per volta, piccolo.

## 1. Stato verificato (2026-10-06, sul codice a `172b8e616`)

- `compatible_plugins` si calcola **una volta**, in `save_uploaded_file` (`brim_provider.py:711`, `get_compatible_plugins`), e si salva nel sidecar JSON. Nessuno lo ricalcola: né `_move_file`, né la lettura (`_build_file_info_from_metadata`, `:759`, che lo restituisce com'è a `:800`). L'unica scrittura diversa è quella dei file combinati (`:1143`, `[plugin_code]`).
- **Chi lo legge**:
  - la colonna Plugin del wizard (`ImportPluginSelect` filtrato);
  - `setPluginFor` nel frontend (appartenenza a un set);
  - `collect_members` (`brim_report_sets.py:134`, `plugin_code in info.compatible_plugins`).
  - Tutti passano da `_build_file_info_from_metadata`, tramite `list_files`, `get_file_info` e `_find_combined`. Nessuno legge il sidecar per altre vie.
- **`plugin_version` non può fare da firma.** Il suo contratto riguarda l'**output del parse** («bump … whenever the plugin's output for the same input would change»), non il rilevamento. G ha cambiato il `can_parse` del Generic CSV senza toccarlo: è ancora il default `1.0.0`.
- **La versione dell'app** c'è già: `config.get_version()` → `utils/version.get_git_version()`, con `lru_cache`. Legge il file `VERSION` nell'immagine Docker, e altrimenti usa `git describe --tags --always --dirty`.
- **L'immagine Docker** gira con **un solo worker** uvicorn (`Dockerfile:144`, nessun `--workers`). I server di test del runner ne usano `ceil(E2E_WORKERS / 2)`.
- **Async (regola del progetto)**, letture sul ciclo degli eventi:
  - `list_files` è chiamata **direttamente** dall'endpoint asincrono della lista (`brokers.py:687`);
  - anche `get_file_info` lo è, in `_get_brim_file_with_access` (`brokers.py:135`, usata da 5 endpoint).
  - Oggi leggono solo piccoli JSON; con il rilevamento leggerebbero i file e aprirebbero gli XLSX, quindi vanno spostate in `asyncio.to_thread`. `collect_members` ci gira già (`brim_report_sets.py`, `preview_set`).

## 2. Il contratto proposto

1. **La firma del catalogo**, `detection_signature()` in `brim_provider.py`, calcolata una volta per processo: la versione dell'app (`get_version()`).
   - Ogni rilascio, o commit del nightly, cambia la firma, e con lei ogni cambiamento di un `can_parse`, del lettore di base o dell'elenco dei plugin.
   - In dev, le modifiche non committate (`-dirty`) non la cambiano: è accettabile.
2. **Al caricamento**: il sidecar salva anche `"plugins_signature": detection_signature()`, accanto a `compatible_plugins`.
3. **Alla lettura** (`_build_file_info_from_metadata`): per un **originale** (non combinato) con `plugins_signature` assente o diversa da quella corrente, `compatible_plugins` si ricalcola con `BRIMProviderRegistry.get_compatible_plugins(percorso del file)`, e `BRIMFileInfo` restituisce l'elenco nuovo.
   - I file caricati con la 1.1.0, che la firma non ce l'hanno, sono proprio il caso da coprire.
   - Il file in errore (`failed`) si ricalcola come gli altri: serve per riprovarlo.
   - Se il file dati manca, si tiene l'elenco salvato.
4. **La persistenza**, da decidere (§5, D1):
   - **A-persist (scelta, D1)**: il ricalcolo si scrive nel sidecar, con `compatible_plugins` e la nuova firma. Il ricalcolo, che è la parte lenta, avviene fuori dal lock. Poi, **sotto il lock del broker** (punto 7): si ritrova il sidecar per `file_id`, lo si rilegge, e se la firma è ancora vecchia si correggono solo quei due campi e si fa la scrittura atomica sullo stesso percorso.
     - Senza il lock, un parse che sposta il file (`uploaded` → `parsed`) mentre il rilevamento riscrive il vecchio sidecar lo farebbe risorgere, e il file comparirebbe due volte.
     - Il costo è **una volta per versione**.
   - ~~**A-mem**~~: scartata (D1).
5. **Async**: `list_files` e `get_file_info` si chiamano in `asyncio.to_thread` nei due punti di `brokers.py` (`:687`, `:135`). Concessione del coordinatore: solo queste due righe.
6. **Il frontend** non cambia: legge gli elenchi dal server.
7. **Il lock dei metadati, per broker e fra processi** (requisito del coordinatore):
   - `_broker_metadata_lock(broker_id)`: un context manager che apre `broker_reports/.locks/broker_<id>.lock` (fuori dalle cartelle di stato, così nessuna scansione di `*.json` lo vede) e ci fa `fcntl.flock(LOCK_EX)`. Un `threading.Lock` per broker lo precede dentro il processo, perché `flock` è legato al file aperto: due aperture nello stesso processo non si escluderebbero in modo affidabile su tutti i sistemi. Si rilascia sempre, anche sulle eccezioni.
   - Lo prendono **tutte le scritture dei metadati di un broker**: `save_uploaded_file`, `_update_metadata`, `save_combined_file` (e l'aggiornamento di `combined_into` dei membri), `save_parse_result`, `_move_file`, `delete_file`, e il salvataggio del rilevamento.
   - La lettura **non** lo prende: le scritture sono atomiche (`os.replace`), quindi un lettore vede il vecchio sidecar o il nuovo, mai uno a metà.
   - **La scrittura ricontrolla**: sotto il lock, prima di riscrivere un sidecar si verifica che sia ancora al percorso letto (`_find_metadata_path(file_id) == meta_path`). Se un altro processo l'ha spostato, non si scrive.
   - Il file system dei dati è locale (`/data` nel container, un volume): `flock` vale fra processi sullo stesso host. Più host sullo stesso volume NFS non sono un caso supportato.
   - In Docker c'è un worker solo: il lock costa una syscall per scrittura, trascurabile.
8. **F1 — un solo combinato per set**: `combine_set` tiene il lock del broker (in un thread, perché `flock` blocca) **attorno a riuso → costruzione → salvataggio**. Il secondo combine concorrente aspetta e trova il combinato del primo, cioè `reused=True`.
   - Costruire il combinato mentre si tiene il lock blocca le altre scritture di quel broker per la durata del combine: per Danske è meno di un secondo, e vale solo per quel broker. In alternativa si potrebbe costruire fuori dal lock e, sotto il lock, ricontrollare il riuso prima di salvare, scartando il proprio. La scelta è da fare nell'implementazione, col rosso che decide.

**L'effetto per l'utente**:
- dopo un aggiornamento, ogni file caricato prima offre i plugin che lo leggono oggi: un plugin nuovo o cambiato (Danske dopo la 1.1.0, il Generic CSV più stretto di G) compare o sparisce. ~~Un export Danske caricato con la 1.1.0 forma il suo set senza ricaricarlo~~: **falso**, perché la 1.1.0 non scriveva `batch_id` (§8.3). Quel file viene riconosciuto, ma resta singolo; per formare il set va ricaricata la coppia, insieme. Un set si forma senza ricaricare solo per i file caricati con una build che salva `batch_id`, cioè dalla 1.2;
- il Generic CSV sparisce dai file che non sa leggere (le regole di G) e compare dove sa leggere;
- un plugin nuovo compare sui file vecchi.

## 3. Superfici

| File | Cosa | Proprietà |
|---|---|---|
| `backend/app/services/brim_provider.py` | `detection_signature()`, la firma al caricamento, il ricalcolo in `_build_file_info_from_metadata`, `_broker_metadata_lock` (`threading.Lock` + `fcntl.flock`) attorno a tutte le scritture dei metadati del broker, il ricontrollo del percorso prima di riscrivere | di L |
| `backend/app/services/brim_report_sets.py` | `combine_set` sotto il lock del broker (F1) | di L |
| `backend/app/api/v1/brokers.py` | `asyncio.to_thread` a `:687` e `:135` | comune: **concesso** dal coordinatore, solo queste due righe |
| test (§4) | `test_brim_parse_race.py` (archivio e corse), `test_brim_report_sets.py` (appartenenza al set), `test_brim_api.py` (la lista) | di L; nessun file nuovo, quindi niente registrazione nel runner |
| doc (EN, docs-writer) | `developer/architecture/patterns/brim_plugin_guide.md` (il ciclo di vita di `compatible_plugins`), `developer/backend/brim/architecture.md:40` (il rilevamento); `user/transactions/import/danske-bank.en.md` (i file caricati prima dell'aggiornamento si riconoscono da soli) | `danske-bank` non ha traduzioni; le altre sono pagine developer |
| `CHANGELOG.md` | riga proposta (§6), la scrive il coordinatore | — |

Nessuna modifica a schemi, API pubbliche, i18n o frontend.

## 4. I test, rossi prima (test-author)

- **Servizi** (`test_brim_parse_race.py` o un vicino), in `tmp_path`, coi campioni sintetici:
  1. un sidecar senza firma (come la 1.1.0), con `compatible_plugins: []`, di `danske_bank-cash.csv` → la lettura dà `['broker_danske_bank']`;
  2. un sidecar con firma vecchia e `['broker_directa', 'broker_generic_csv']` per un CSV senza `date`/`type` → il Generic CSV sparisce;
  3. con la firma corrente nessun `can_parse` viene chiamato (spia sul registro), e l'elenco salvato si restituisce com'è;
  4. un file combinato non si ricalcola mai;
  5. se il file dati manca, si tiene l'elenco salvato;
  6. il sidecar riceve l'elenco e la firma nuovi, e una seconda lettura non ricalcola (spia);
  7. un `_move_file` concorrente col rilevamento non lascia due sidecar e non fa risorgere il vecchio (due thread sincronizzati con Event, come in V1).
- **Il lock fra processi** (requisito del coordinatore):
  8. **due processi** (`multiprocessing`, contesto `spawn`) sulla stessa data-dir in `tmp_path`: uno tiene il lock del broker (segnala, poi aspetta un Event fra processi), l'altro tenta una scrittura dei metadati dello stesso broker e deve aspettare. Si verifica coi tempi relativi agli Event, mai con sleep nudi; ogni attesa è limitata. Se due processi sono troppo costosi o fragili nel runner: due thread **più** una prova diretta che `flock` esclude un secondo descrittore aperto da un processo figlio;
  9. un broker diverso non aspetta (il lock è per broker);
  10. un'eccezione dentro il lock lo rilascia.
- **F1** (`test_brim_report_sets.py`): due `combine_set` concorrenti dello stesso set → un solo file combinato fra i file del broker; il secondo risponde `reused=True`.
- **Set** (`test_brim_report_sets.py`): un export Danske ~~«della 1.1.0»~~ rilevato prima della voce 8 (sidecar senza firma, elenco vuoto, **con** `batch_id`) entra in `collect_members` e forma il set. Per la 1.1.0 vera, che `batch_id` non lo scriveva, vale la guardia opposta di §8.3.
- **API** (`test_brim_api.py`): la lista restituisce l'elenco aggiornato per un sidecar vecchio, scritto nella data-dir del test.
- **E2E**: non servono; il frontend non cambia.

## 5. Decisioni (chiuse il 2026-10-06: «Approvo le raccomandazioni (Consigliato)»)

- **D1 — A-persist** ✅. Il ricalcolo si salva una volta per versione; il lock fra processi di §2.7 lo rende sicuro anche con più worker.
- **D2 — la firma è la versione dell'app** ✅. Un'impronta per plugin (l'hash del modulo e del lettore di base) resta un affinamento futuro.
- **D3 — il costo una tantum** ✅: un passaggio di `can_parse` per ogni file vecchio, alla prima lettura dopo un aggiornamento, in un thread. Con decine o poche centinaia di file sono pochi secondi.

## 6. CHANGELOG proposto

- 🐛 Fixed (import), **riga corretta il 2026-10-06** (§8.3), accettata dal coordinatore: `- **Files uploaded before an update offer today's import plugins.** After an update LibreFolio checks your earlier uploads against the current plugins, so each file offers the plugins that can read it now; exports uploaded with 1.1.0 or earlier must be uploaded again, together, to form a report set.`
  - ~~La riga precedente prometteva che un export Danske «caricato con una versione precedente» formasse il suo set senza ricaricarlo: falso per la 1.1.0, che non salvava `batch_id`.~~
- 🐛 Fixed (import), F1: `- Clicking **Parse** twice on the same report set, or analysing it from two tabs, no longer builds two combined files: the second analysis reuses the first.`

## 7. Complessità, rischi, gate

- **Complessità**: media, circa 120–180 righe di prodotto più i test (il lock fra processi e F1 si aggiungono al ricalcolo).
- **Rischi**:
  - il lock dei metadati tocca `_move_file`, `save_parse_result` e `save_combined_file`, che sono percorsi caldi del parse e del combine: vanno coperti dai test di §4.7–4.10 e dalle suite `brim-parse-race`, `brim-parse-pool`, `brim-report-sets` e `api brim`;
  - un deadlock se una funzione che prende il lock ne chiama un'altra che lo prende: il lock interno al processo dev'essere **rientrante per thread** (`RLock`), e `flock` si prende una sola volta per livello di annidamento (un contatore per thread);
  - spostando in thread le letture di `brokers.py` cambia il tempo, non il risultato.
- **Gate**:
  - `services`: `brim-parse-race`, `brim-parse-pool`, `brim-report-sets`, `brim-provider-base`, `provider-registry-misc`;
  - `external brim-providers`, `brim-danske-bank`;
  - `api brim`, per ultimo;
  - gli E2E di import (dopo il `--clean`);
  - `lint`, `check-orphans`, `mkdocs build` e `check-links`.
- **Definition of done**:
  - i rossi di §4 sono verdi e i gate passano;
  - la doc è aggiornata;
  - una prova da capo a fondo: un sidecar senza firma (con `batch_id`) scritto a mano nella corsia; i plugin si rilevano di nuovo e il set si forma (§8.2);
  - il checkpoint in un commit a sé.

## 8. Avanzamento

### 8.0 ✅ Il piano aggiornato dopo il via (2026-10-06)

- Base `a7d0b37ec`, dopo il treno 1 (H, V1 e R5 integrati); ramo di L allineato e pulito.
- Aggiornati §0 (il via testuale, la concessione su `brokers.py`, il lock fra processi, F1, l'ordine), §2.4–2.8, §3, §4, §5 (chiusi), §6 (la riga di F1) e §7.
- Prossimo passo: i rossi (test-author), poi la cura, i gate e il checkpoint.

### 8.1 ✅ Il rosso (test-author, 2026-10-06)

- **33 test nuovi**, di cui 29 rossi ciascuno sul suo punto e 4 guardie verdi; nessun test esistente rotto.
  - `test_brim_parse_race.py` (24 rossi):
    - la firma = `get_version()`, e l'upload la salva;
    - la ririlevazione (`get_file_info`, `list_files`, i file in `parsed` e in `failed`, la firma vecchia che toglie il generico, un solo calcolo);
    - le guardie: firma corrente, combinato, file dati mancante;
    - tre varianti della corsa (move, un altro campo scritto nel frattempo, una rilevazione concorrente);
    - il lock fra processi: un processo figlio con `flock(LOCK_NB)`, per broker, rilasciato sulle eccezioni, rientrante, `broker_none`;
    - i 7 scrittori che aspettano il lock.
  - `test_brim_report_sets.py`: la coppia Danske «rilevata prima della voce 8» (`collect_members` e anteprima) e F1 (due combine concorrenti).
  - `test_brim_api.py`: RS-I801 (la lista e `GET /files/{id}`).
- **Una controprova del test-author**: un'implementazione di riferimento temporanea (in `/tmp`, poi rimossa) fa diventare verdi i 33 test. Ogni variante rotta (copia vecchia riscritta, un lock unico, `flock` rilasciato presto, uno scrittore senza lock, combinati ririlevati…) fa diventare rossi solo i suoi.

### 8.2 ✅ La cura e i gate (2026-10-06)

> **Note implementazione**:
> - `brim_provider.py`:
>   - `detection_signature()` restituisce `get_version()`;
>   - `_broker_metadata_lock`, col nome pubblico `broker_metadata_lock`: un `RLock` per broker più `fcntl.flock` su `broker_reports/.locks/broker_<id>.lock`. Il `flock` si prende una volta per thread (la profondità sta in un `threading.local`) e si rilascia sulle eccezioni. Senza `fcntl` resta il solo lock del processo;
>   - `_broker_id_of`: il broker si ricava dalla cartella del sidecar;
>   - il lock lo prendono l'upload, `_update_metadata`, `save_combined_file`, `save_parse_result`, `_move_file` e `delete_file` (questi ultimi tre con un `_…_locked` interno), oltre al salvataggio della ririlevazione;
>   - `_current_compatible_plugins` e `_save_detection`: il calcolo avviene fuori dal lock; il salvataggio sotto il lock, solo se il sidecar è ancora al suo posto e ha ancora la firma vecchia, e cambia solo i due campi.
> - `brim_report_sets.py`: `_combine_under_broker_lock` fa riuso, combine e salvataggio come un passo solo, sotto il lock, in un thread (F1).
> - `brokers.py` (concessioni del coordinatore; righe del codice finale): `asyncio.to_thread` per `_get_brim_file_with_access` (`:136`, ex `:135`), la lista (`:689`, ex `:687`), `delete_file` (`:765`) e `save_parse_result` (`:976`). Queste ultime due chiamate stavano sull'event loop, e col lock di F1 potevano fermarlo (§8.3).
> - Un test esistente adattato dal test-author: `test_legacy_sidecar_reads_with_defaults`. La sua premessa (un sidecar legacy elenca il generico) è contraddetta per scelta dalla voce 8; ora confronta con il registro di oggi.
>
> | Verifica (corsia 6156, base `ebf4752e2`) | Esito |
> |---|---|
> | `services brim-parse-race` / `brim-report-sets` | `42` / `259 passed` (con la guardia 1.1.0 di §8.3) |
> | `services brim-parse-pool` / `brim-provider-base` / `provider-registry-misc` / `brim-gap-fix` / `brim-versioning` | `8` / `34` / `13` / `99` / `5 passed` |
> | `external brim-providers` / `brim-danske-bank` | `626 passed`, 1 saltato / `324 passed` |
> | `--clean` (permesso fino alla prossima integrazione), poi gli E2E | `report-set` 27, `-guide` 2, `handoff` 2, `file-selection` 2, `upload` 9, `flow` 10, `resolution` 12, `files` 22 |
> | `api brim` | **76 passed** (73 + RS-I801 ×2 + RS-I802) |
> | `dev.py lint` | pulito |
> | **Prova dal vivo** (`files/i8-live-check.py`, server di test sulla 6156) | coppia Danske riscritta senza firma e con elenco vuoto: ririlevata (`['broker_danske_bank']` ×2), salvata con la firma, set completo. Due combine concorrenti: **un solo** combinato, `reused` False e True, stesso file; 0 traceback |
> | **RS-I802**: l'event loop non si ferma | il test tiene il `flock` del broker dal suo processo; il DELETE aspetta il lock, e intanto `GET /plugins` sullo stesso processo uvicorn risponde. Verde a 1 worker e con `--workers 4` (2 worker uvicorn) |
> | **Controprova di L su RS-I802** | `delete_file` rimesso **sincrono** per un momento: rosso in 10 s («backend process … did not answer GET /plugins within 10.0s while its DELETE waited for the broker's lock»), poi la correzione ripristinata (nessun marcatore rimasto) |

### 8.3 ⚠️ Fuori pista — la promessa sulla 1.1.0 era falsa (2026-10-06)

- **La scoperta** (docs-writer, verificata da L con `git show v1.1.0:…brim_provider.py`): la 1.1.0 non scriveva `batch_id`. Senza `batch_id`, `collect_members` e `setPluginFor` non mettono il file in nessun set. Quindi un export Danske caricato con la 1.1.0 viene **riconosciuto**, perché la voce 8 propone Danske, ma resta singolo, e il parse da solo risponde 422 `set_required` («upload it together with the other exports»): la coppia va ricaricata, insieme.
- **I test «1.1.0»** del test-author tenevano un `batch_id`, quindi modellavano «un sidecar rilevato prima della voce 8 da una build che salvava già `batch_id`». Sono stati rinominati (`_as_detected_before_item_8`, `TestDanskePairDetectedBeforeItem8`, RS-I801…), e in più c'è **una guardia sulla 1.1.0 vera**: `TestDanskePairUploadedWith1_1_0`, coi sidecar scritti con le 12 chiavi esatte della 1.1.0. Rileva Danske, ma `collect_members` non li prende, e la coppia ricaricata forma il set.
- **Corretti**: §2 (l'effetto per l'utente), §6 (la riga di CHANGELOG, accettata dal coordinatore), la pagina Danske e la guida dei plugin (scritte giuste dal docs-writer). La voce 8 resta utile: ogni file offre i plugin di oggi dopo un aggiornamento.
- **Il secondo problema trovato dal docs-writer**: `delete_file` e `save_parse_result` stavano sull'event loop e ora prendono il lock. Con F1, che tiene il lock durante un combine, avrebbero fermato l'intero loop. La concessione su `brokers.py` per le due righe è stata data, e RS-I802 lo prova.
- **Restano sul loop, per il backlog**: `get_file_path` in preview e download (`brokers.py:716`, `:788`). Di solito sono letture leggere, perché `_get_brim_file_with_access`, che le precede, ha già ririlevato e salvato. Nel caso raro in cui quel salvataggio salta (il file si è spostato nel frattempo), potrebbero ririlevare sul loop.
- **Deriva già esistente, per il backlog**: `developer/backend/brim/architecture.md`, passo 2, dice ancora che il Generic CSV è il ripiego; dopo G il wizard ripiega sul plugin predefinito del broker.

### 8.4 ✅ Voce 8 + F1 — pronta per il checkpoint (2026-10-06)

> **Note implementazione** — i gate finali, sul codice definitivo (dopo `:765`/`:976`), corsia 6156, un comando per volta, log in `files/i8-runs/` della sessione:
>
> | Comando (`PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py …`) | Esito |
> |---|---|
> | `test --test-port 6156 --data-dir /private/tmp/librefolio-r2-l db populate --force --clean` | exit 0 |
> | `test … front-transaction tx-import-report-set` / `-flow` / `-upload` / `-resolution` / `-file-selection` | `27` / `10` / `9` / `12` / `2 passed`: ogni parse passa da `save_parse_result` in thread, ogni pulizia da `delete_file` in thread |
> | `test … front-transaction tx-import-report-set-guide` / `tx-bulk-import-handoff`, `test … front-utility files` | `2` / `2` / `22 passed` |
> | `test … services brim-report-sets` / `brim-parse-race` | `259` / `42 passed` |
> | `test … api brim` (già dopo `:765`/`:976`, §8.2) | `76 passed` |
> | `test check-orphans` | pulito |
> | `mkdocs build` | exit 0 |
> | `mkdocs check-links` | exit 1 per **il solo** `user/assets/detail/chart/#rolling-return` (manca in it/fr/es): la D28 già accettata, presente uguale alla validazione del merge di G, fuori dal diff di L |
> | scanner di privacy contro `ebf4752e2` | 1738 righe aggiunte, 0 collisioni |
> | `git diff --check` | pulito; nessun file non tracciato |
> | `lsof -nP -iTCP:6156 -sTCP:LISTEN` | porta libera |
>
> Delta: 11 file tracciati (3 di codice, 3 di test, 3 di docs, 2 piani), nessun file nuovo. Il `CHANGELOG.md` lo scrive il coordinatore all'integrazione, con le due righe di §6.

### 8.5 ✅ Committata e validata (2026-10-06)

> **Commit di L8** (developer, script del coordinatore, corpi scritti da L): `b0abeb07d` fix, `2b1a9d79f` docs, `b6ac553fc` journal; sopra la punta di K `7dd5e47e7`, albero `3bdccc7a9`. Prima del commit L ha corretto i corpi proposti: due frasi false (l'event loop «mai» fermo; il lock descritto anche nella pagina di architettura) e un corpo incompleto (C3).
>
> **Validazione sulla base nuova** (corsia 6156, un comando per volta, log nella sessione, in `files/l8-post/`): `api brim` 76, `services brim-parse-race` 42, `brim-report-sets` 259 passed; `check-orphans` pulito; porta libera, albero pulito. La catena di K non porta migrazioni.
>
> Il seguito, la robustezza dell'upload (F2–F4): [plan-phase00BrimDanskeBankStep6UploadRobustness.prompt.md](plan-phase00BrimDanskeBankStep6UploadRobustness.prompt.md).
