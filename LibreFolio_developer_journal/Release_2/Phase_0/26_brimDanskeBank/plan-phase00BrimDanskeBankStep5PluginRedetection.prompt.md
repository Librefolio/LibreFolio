# Piano — fase 00, Danske Bank, passo 5: rilevare di nuovo i plugin dei file (voce 8, opzione A)

> **Stato**: ⏳ analisi, da approvare. Niente codice finché il coordinatore non porta il via del developer.
>
> - Viene da: [plan-phase00BrimDanskeBankStep4Implementation.prompt.md](plan-phase00BrimDanskeBankStep4Implementation.prompt.md), §18 (analisi della voce 8) e §19.5 (scelta del developer).
> - Workstream L, issue #26. Ramo `e-alfy-l-danske-bank`, base `172b8e616` (V1).

## 0. Decisioni

- **Developer** (ask_user, testuale): «A — rilevare di nuovo quando i plugin cambiano (Consigliata)».
- **Coordinatore**: va nella **1.2, prima del taglio**. Il motivo: con la 1.2 arriva Danske, e chi aggiorna dalla 1.1.0 ha file caricati senza quel plugin, che altrimenti non entrerebbero mai in un set. Superfici previste: `brim_provider.py` ed eventualmente `brokers.py`; se ne servono altre, vanno dette qui.

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
   - **A-persist (consigliata)**: il ricalcolo si scrive nel sidecar, con `compatible_plugins` e la nuova firma. Il ricalcolo, che è la parte lenta, avviene fuori dal lock. Poi, sotto un **lock di processo** condiviso con `_move_file` e `_update_metadata`: si ritrova il sidecar per `file_id`, lo si rilegge, e se la firma è ancora vecchia si correggono solo quei due campi e si fa la scrittura atomica sullo stesso percorso.
     - Senza il lock, un parse che sposta il file (`uploaded` → `parsed`) mentre il rilevamento riscrive il vecchio sidecar lo farebbe risorgere, e il file comparirebbe due volte.
     - Il costo è **una volta per versione**.
   - **A-mem**: niente scritture. Una cache di processo `(file_id, firma) → elenco`: nessun rischio per i sidecar e nessun lock, ma il ricalcolo si ripete a ogni riavvio.
5. **Async**: `list_files` e `get_file_info` si chiamano in `asyncio.to_thread` nei due punti di `brokers.py` (`:687`, `:135`).
6. **Il frontend** non cambia: legge gli elenchi dal server.

**L'effetto per l'utente**:
- dopo l'aggiornamento alla 1.2, un export Danske caricato con la 1.1.0 viene riconosciuto e forma il suo set, senza ricaricarlo;
- il Generic CSV sparisce dai file che non sa leggere (le regole di G) e compare dove sa leggere;
- un plugin nuovo compare sui file vecchi.

## 3. Superfici

| File | Cosa | Proprietà |
|---|---|---|
| `backend/app/services/brim_provider.py` | `detection_signature()`, la firma al caricamento, il ricalcolo in `_build_file_info_from_metadata`, il lock dei metadati in `_move_file` e `_update_metadata` (solo con A-persist) | di L |
| `backend/app/api/v1/brokers.py` | `asyncio.to_thread` a `:687` e `:135` | comune: da verificare col coordinatore |
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
  6. A-persist: il sidecar ha l'elenco e la firma nuovi, e una seconda lettura non ricalcola. A-mem: il sidecar resta invariato e la seconda lettura usa la cache;
  7. A-persist: un `_move_file` concorrente col rilevamento non lascia due sidecar (due thread sincronizzati con Event, come in V1).
- **Set** (`test_brim_report_sets.py`): un export Danske «della 1.1.0» (sidecar senza firma, elenco vuoto) entra in `collect_members` e forma il set.
- **API** (`test_brim_api.py`): la lista restituisce l'elenco aggiornato per un sidecar vecchio, scritto nella data-dir del test.
- **E2E**: non servono; il frontend non cambia.

## 5. Decisioni aperte (developer, tramite il coordinatore)

- **D1 — A-persist o A-mem?** Consiglio A-persist: il costo è una volta per versione, e il lock basta perché l'immagine ha un solo worker. A-mem è più semplice e non scrive niente, ma ricalcola a ogni riavvio.
- **D2 — la firma**: la versione dell'app (consigliata, già disponibile) oppure un'impronta per plugin, cioè l'hash del modulo del plugin e del lettore di base. L'impronta ricalcolerebbe solo i plugin cambiati, ma è più complessa. Si può tenere come affinamento futuro.
- **D3 — il costo della prima lettura dopo un aggiornamento**: un passaggio di `can_parse` per ogni file vecchio. Per un CSV la maggior parte dei plugin si ferma all'estensione o all'intestazione; per un XLSX i 4 plugin XLSX aprono la cartella in sola lettura. Con decine o poche centinaia di file sono pochi secondi, una volta sola, in un thread. Proposta: va bene così.

## 6. CHANGELOG proposto

- 🐛 Fixed (import): `- **Files uploaded before an update are recognised again.** After an update LibreFolio checks your earlier uploads against the current import plugins: a Danske Bank export uploaded with an older version now forms its set without being uploaded again, and each file offers the plugins that can read it today.`

## 7. Complessità, rischi, gate

- **Complessità**: media-bassa, circa 60–100 righe di prodotto più i test.
- **Rischi**:
  - con A-persist, il lock dei metadati tocca `_move_file`, che è un percorso caldo del parse: va coperto dai test di corsa di §4.7 e dalle suite `brim-parse-race`, `brim-parse-pool` e `api brim`;
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
  - una prova da capo a fondo: un sidecar «1.1.0» scritto a mano nella corsia; il set si forma nel wizard dopo il riavvio;
  - il checkpoint in un commit a sé.

## 8. Avanzamento

- (vuoto: si comincia dopo il via)
