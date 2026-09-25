# Piano — K / step 10: la raffica di `GET /brokers/{id}` (C3)

> Nasce da una segnalazione di un utente, girata dal developer al coordinator, che l'ha assegnata a K
> il 24/09. Piano approvato dal developer il 25/09 alle 10:03 («Sì, approvo il piano di K»). Viene
> dopo lo step 9 ([`plan-phase00TaxonomySelectStep9ImportDuplicates.prompt.md`](plan-phase00TaxonomySelectStep9ImportDuplicates.prompt.md)).
> **Niente hotfix** (D-C3-3): la correzione esce con la Release 2.

| | |
|---|---|
| **Worktree** | `LibreFolio-worktrees/e-alfy-improved-memory`, branch `e-alfy-k-tassonomia-e-select` |
| **Baseline** | `822cdba3e` (C2 committato: `df3bbcf6e`, `e997cda34`, `822cdba3e`) |
| **Lane suite** | `--test-port 6155 --data-dir /tmp/librefolio-r2-k`: solo `dev.py test` |
| **Lane copia di prod** | `--port 6165 --data-dir /tmp/librefolio-r2-k-prodcopy`: solo la misura dal vivo, con la copia rinfrescata dalla snapshot delle 09:15 (sha `5c0a681bc4e4b59c`) |
| **File di K in esclusiva** | `stores/reference/brokerStore.ts`, `components/brokers/BrokerIcon.svelte`, `components/ui/display/BrokerBadge.svelte` (per decisione D-C3-2 gli ultimi due non si toccano) |
| **Condivisi, solo in aggiunta** | `scripts/test_runner/_frontend_utility.py`, `scripts/test_runner/_frontend_transaction.py` |
| **Non si toccano** | `stores/core/entityStore.ts`: il suo `merge` fa salire la versione anche a dati identici; è una voce di backlog del coordinator |

## Sintomo e causa (confermata dal vivo il 25/09)

**Sintomo.** Con la pagina Transazioni aperta arrivano 40–60 richieste al secondo di
`GET /api/v1/brokers/1`, quasi 100 000 al giorno. Succede anche in `v1.1.0`.

**Misura sulla copia dei dati del developer**:
- porta 6165, finestra di 10 s su `/transactions`, 50 badge di broker a schermo;
- script Playwright `/tmp/libreFolio_k_c3_measure.cjs`, con le credenziali solo in variabili
  d'ambiente.

| caso | `GET /brokers/{id}` in 10 s |
|---|---|
| dati così come sono (broker 1 `default_import_plugin=broker_directa`, broker 2 portale + plugin) | **0** |
| condizione dell'utente, solo sulla copia: `UPDATE brokers SET default_import_plugin=NULL WHERE id=1` | **587, cioè 58,7/s, tutte per `/brokers/1`** |

Dopo la misura: copia ripristinata dalla snapshot (quella modificata è in `.prev-20260925-093954`) e
server spento.

**La catena.**
1. `BrokerBadge.svelte:46-55`: `resolvedBroker` è un `$derived.by` che legge `$brokerStoreVersion` e
   a ogni bump restituisce un oggetto nuovo.
2. `:63`: le props di `BrokerIcon` si leggono da quell'oggetto. In Svelte 5 le props sono getter,
   quindi l'`$effect` di `BrokerIcon.svelte:50-56` riparte a ogni bump, anche se i valori restano
   `null`.
3. `ensureBrokerIconFieldsLoaded` (`brokerStore.ts:169`): `hasBrokerIconFields` (`:118`) resta
   falso anche dopo la risposta, perché la risposta non ha i campi.
4. `entityStore.merge` (`entityStore.ts:149-182`): `changed = true` per qualunque entry esistente,
   quindi `bump()`.
5. Il `finally` toglie la promessa in volo nello stesso tick del bump, e l'effect successivo trova la
   strada libera. La frequenza è una richiesta per latenza.

Origine: `460f2a18a` (30/06), presente in `v1.1.0`. I quattro file coinvolti sono identici fra `main`
e HEAD.

## Cura (decisioni D-C3-1 e D-C3-2)

`brokerStore.ts`, contratto nuovo di `ensureBrokerIconFieldsLoaded`: **al più una richiesta per broker
e per generazione della cache**.
- Un insieme di id già chiusi: la **prima risposta, successo o errore** (D-C3-1), chiude l'id. Un
  broker senza campi icona è uno stato valido.
- La guardia di sessione resta: una risposta di una sessione vecchia non chiude l'id e non fa merge.
- L'insieme si svuota in tre casi:
  - `resetBrokerStore`, al reset di sessione;
  - `refreshAllBrokers`;
  - `invalidateBroker(ids)`, che diventa un wrapper di `store.invalidate` e toglie quegli id.
- `BrokerBadge` e `BrokerIcon` restano come sono (D-C3-2).

## Passi

- [x] **10.0 Piano nel journal** — ✅ 2026-09-25
  > **Note implementazione**: questo file, con il rimando dalla nota «In coda dopo C2» dello step 9.
- [x] **10.1 Rossi prima della cura** (test-author) — ✅ 2026-09-25
  - U1, U2, U4 ed E1 rossi, più i controlli U3 ed E2.
  - Registrazioni nel runner solo in aggiunta.
  - DoD: rossi per la ragione giusta (GET ripetuto) sul codice attuale; controlli verdi.
  > **Note implementazione** (HEAD `822cdba3e`, codice di prodotto intatto):
  > - Store, nel file nuovo `brokerStoreIconHydration.test.ts` (in `core-unit` subito dopo
  >   `brokerStore.test.ts`, così la sua promessa «nessuna rete» resta intatta): **3 rossi, 15 verdi**.
  >   - U1 ✘ «called 1 times, but got 2»;
  >   - U1-extra ✘: invalidare un altro broker non deve riaprire un id già chiuso;
  >   - U2 ✘ «called 1 times, but got 2»;
  >   - U3a–f verdi, compresi gli array in `invalidateBroker` e la risposta, risolta o rifiutata, dopo
  >     un cambio di sessione;
  >   - i 5 test di `brokerStore.test.ts` verdi.
  > - Componente, `BrokerBadge.test.ts` (in fondo a `component-unit`): U4 ✘, con i conteggi dopo ognuno
  >   dei 10 giri `[7, 13, 19, 25, 31, 37, 43, 49, 55, 61]`, cioè 62 GET. Il controllo con `portal_url`
  >   dà 0 GET ✓.
  > - E2E, `tx-broker-icon-hydration.spec.ts` (registrata in `_frontend_transaction.py`), tre run
  >   identici: E1 ✘ con 2 richieste al primo controllo, la seconda partita 2,2 ms dopo la prima
  >   risposta; E2 ✓ con 0 richieste. Log `/tmp/libreFolio_k_c3_red_e2e.log`.
  >   - Il secondo giro di andata e ritorno è `tx-refresh-button`, l'unico controllo che rifà la
  >     query: filtri, ordinamento e paginazione sono lato client (W28).
  >   - Onboarding neutralizzato solo a livello di pagina, come in `tx-import-flow`.
  >
  > **Fuori pista**: in E1 il conteggio al primo controllo è 2, non «decine». È voluto. La spec misura
  > con un registro delle XHR dentro la pagina: guarda dopo la risposta alla prima richiesta, quando il
  > seguito, se c'è, è già partito. 2 è il minimo che dimostra che la prima risposta non ha chiuso l'id,
  > senza aspettare sull'orologio. La crescita la mostra U4.
  >
  > **Fuori pista**: test-author non ha lanciato le categorie `core-unit` e `component-unit` del runner,
  > perché dentro chiamano `npx vitest`. Ha eseguito i file con `node_modules/.bin/vitest`. Le categorie
  > le lancia K nel gate: con `node_modules` presente, npx trova il binario locale.
- [x] **10.2 La cura in `brokerStore.ts`** — ✅ 2026-09-25
  - DoD: U1–U4, E1 ed E2 verdi; `core-unit`, `component-unit` e la spec nuova verdi.
  > **Note implementazione**:
  > - `settledIconFieldIds`, un `Set<number>`: `ensureBrokerIconFieldsLoaded` esce subito se l'id è già
  >   chiuso.
  >   - La prima risposta chiude l'id, in caso di successo *prima* del `merge`, così l'effect rilanciato
  >     dal bump lo trova già risposto, e anche in caso di errore (D-C3-1). In entrambi i casi solo se
  >     la sessione è ancora quella corrente.
  >   - L'insieme si svuota in `resetBrokerStore` e in `refreshAllBrokers`; `invalidateBroker` diventa
  >     un wrapper che toglie i suoi id, poi chiama `store.invalidate`. Unico chiamante: la cancellazione
  >     in `routes/(app)/brokers/+page.svelte:295`.
  > - Evidenze:
  >   - vitest sui tre file (store nuovo, `brokerStore.test.ts`, `BrokerBadge.test.ts`): **20/20**
  >     (`/tmp/libreFolio_k_c3_green_units.log`);
  >   - `dev.py front build` exit 0; svelte-check dà i 3 errori della baseline, in nessun file di K;
  >   - `tx-broker-icon-hydration`: **E1 ✓, E2 ✓** (`/tmp/libreFolio_k_c3_green_e2e.log`);
  >   - prettier pulito.
- [x] **10.3 Mutanti** — ✅ 2026-09-25
  - Togliere la chiusura dell'id → U1, U4 ed E1 rossi.
  - Non svuotare l'insieme su `invalidateBroker`, `refreshAllBrokers` o `resetBrokerStore` → U3 rossi.
  - Chiudere solo sui successi → U2 rosso.
  > **Note implementazione**: script `/tmp/libreFolio_k_c3_mutations.py`. Ogni mutante è applicato a
  > `brokerStore.ts` e poi ripristinato identico, verificato con SHA-256. **6/6 rossi**, 7 verifiche:
  > - M1, nessun controllo di chiusura: U1, U1-extra, U2 e U4 rossi; con build ed E2E, **E1 rosso**;
  > - M2, `invalidateBroker` non riapre: U1-extra e U3c ×2;
  > - M3, `refreshAllBrokers` non svuota: U3d;
  > - M4, `resetBrokerStore` non svuota: U3e;
  > - M5, l'errore non chiude: U2;
  > - M6, una risposta di una sessione vecchia chiude: U3f.
  >
  > **Fuori pista**: il mutante M1 ha ricompilato il frontend, quindi dopo i mutanti il build conteneva
  > il codice mutato. Il gate ha rifatto il build prima di ogni altra cosa, e la misura dal vivo gira
  > su quel build.

- [x] **10.4 Misura dal vivo sulla copia** — ✅ 2026-09-25
  - Condizione dell'utente, solo sulla copia: finestra di 10 s, poi di 60 s.
  - Controllo sui dati così come sono.
  - Contatore lato server: access log di uvicorn su file.
  - Atteso: **≤1** richiesta per broker in tutta la finestra (era 58,7/s).
  - Poi copia ripristinata dalla snapshot.
  > **Note implementazione**:
  > - Server su 6165, avviato in modalità async con stdout in `/tmp/libreFolio_k_c3_server.log` e
  >   fermato con `stop_bash`; la porta era libera dopo.
  > - Misura con `/tmp/libreFolio_k_c3_live_measure.sh`, credenziali solo in variabili d'ambiente.
  >
  >   | caso | prima della cura | dopo, lato client | dopo, access log |
  >   |---|---|---|---|
  >   | dati così come sono, 10 s | 0 | **0** | **0** |
  >   | condizione dell'utente, 10 s | **587, cioè 58,7/s** | **1** | **1** |
  >   | condizione dell'utente, 60 s | — | **1** | **1** |
  >
  > - Le richieste API in tutta la sessione, dal login alla fine della finestra, passano da 604 a 18.
  > - 50 badge di broker a schermo in ogni run.
  > - Copia ripristinata dalla snapshot: sha `5c0a681bc4e4b59c`, broker 1 di nuovo `broker_directa`;
  >   quella modificata è in `.prev-20260925-110435`.

- [x] **10.5 Gate e handoff** — ✅ 2026-09-25
  - Statici: svelte-check, prettier, knip.
  - **CHECKPOINT READY**, con la voce di CHANGELOG 🐛 Fixed.
  > **Note implementazione**:
  > - Gate nella lane 6155 (`/tmp/libreFolio_k_c3_gates.sh`, prima il build):
  >
  >   | selettore | esito |
  >   |---|---|
  >   | `front-utility core-unit` | 91 file, 2506 ✓ |
  >   | `front-utility component-unit` | 78 file, 2078 ✓ |
  >   | `front-transaction tx-broker-icon-hydration` | 2/2 ✓ |
  >   | `front-transaction transactions-table` | 25/25 ✓ |
  >   | `front-broker list` | 9/9 ✓ |
  >   | `front-broker broker-recovery` | 5/5 ✓ |
  >   | `front-broker broker-unit` | 26 ✓ |
  >
  > - Statici:
  >   - svelte-check: 3 errori, gli stessi della baseline, in nessun file di K;
  >   - prettier pulito sui 4 file frontend;
  >   - knip: nessun reperto nei file di K;
  >   - ruff e black: sulle righe aggiunte ai due file del runner nessun reperto; i 4 errori ruff di
  >     `_frontend_transaction.py` ci sono identici su HEAD.
  > - Messaggi di commit: `/tmp/libreFolio_commits/k-9-c3-broker-burst.txt` (codice e test) e
  >   `k-10-journal-c3.txt` (journal).

## Test list

| # | livello | cosa prova | rosso oggi |
|---|---|---|---|
| U1 | unit (`brokerStore.test.ts`, `core-unit`) | broker senza campi icona, due `await ensureBrokerIconFieldsLoaded(1)` in fila → **1** GET | 🔴 (2) |
| U2 | unit | come U1, con un GET che fallisce → **1** GET (D-C3-1) | 🔴 (2) |
| U3 | unit, controlli | con un campo icona → 0 GET; chiamate concorrenti → 1; dopo `invalidateBroker(1)`, `refreshAllBrokers()` o `resetBrokerStore()` → un GET in più ciascuno; una risposta di una sessione vecchia non chiude l'id | — |
| U4 | componente (nuovo `BrokerBadge.test.ts`, `component-unit`) | un `BrokerBadge` di un broker senza campi icona, API finta senza campi: dopo un numero fisso di flush di effect e microtask → **1** GET | 🔴 (cresce) |
| E1 | E2E (nuova `tx-broker-icon-hydration.spec.ts`) | broker del test senza campi icona con una sua transazione, `/transactions?broker_id=<id>`: GET `/api/v1/brokers/<id>` **≤1** quando la tabella è stabile e dopo un secondo giro di andata e ritorno della pagina | 🔴 (decine) |
| E2 | E2E, controllo negativo | broker del test con `portal_url` → 0 GET | — |

**CHANGELOG proposto** (🐛 Fixed): «Transactions page: a broker with no icon, portal URL or import
plugin no longer makes the page fire dozens of `GET /brokers/{id}` requests per second in the
background.»
