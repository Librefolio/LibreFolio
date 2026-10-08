# Piano — K / step 18: triage dei rossi della coverage completa (07/10) e cura di BrokerModal

> Lavoro nuovo, approvato dal developer e assegnato dal coordinator il 07/10 alle 16:08. Viene dopo lo step 17
> ([`plan-phase00TaxonomySelectStep17DeviceNotes.prompt.md`](plan-phase00TaxonomySelectStep17DeviceNotes.prompt.md)).

| | |
|---|---|
| **Baseline** | `d07412899` (ff da `3fdae5b16`, confermato dal coordinator alle 16:34) |
| **Run della coverage** | `d07412899`, corsia 6150, `--workers 2`, carico 30–50, 13:05 → 15:58. Prove in `/tmp/libreFolio_triage_20261007/`. |
| **Lane suite** | `--test-port 6155 --data-dir /tmp/librefolio-r2-k`, preambolo `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc`. Sonde sulla 6165, con la data-dir della corsia. |
| **Metodo** | skill `test-triage`: prima i log, poi i rilanci da soli. Per ogni rosso un verdetto fra assumption, defect, shared state, environment e slowness. Test corretti dal test-author. Davanti a un difetto di prodotto ci si ferma e lo si riferisce al coordinator. |
| **Fuori perimetro** | `ai-export-panel.spec.ts:19`: lo corregge N (la toolbar si impila apposta dal 30/09). Rossi dell'import a L; cambi e contratto AI Export a N; lingua dopo il welcome a O. |

## Decisioni

- **BrokerModal** (il punto 6, trovato da Q): approvato dal developer, testuale: «Approva tutte e tre le correzioni».
  - Da fare dopo i rossi, prima il rosso col test-author.
  - Nessuna chiave nuova.

## Verdetti

| rosso | da solo nella 6155 | verdetto | dove sta la cura |
|---|---|---|---|
| `tx-delete.spec.ts:181` A1-confirm | 15/15 verde | **shared state** | `tx-bulk-operations.spec.ts:276` «mixed commit» |
| `brokers/multi-user.spec.ts:42` | rosso, deterministico (1,5 s) | **assumption** | lo spec |
| `tx-bulk-suggest-ux.spec.ts:98` FE-SP-C1 | rosso (30,1 s) | **defect** del prodotto, più un'assumption del test | `ContextMenu.svelte`, se approvata; lo spec |
| `layout/toolbar-width-sweep.spec.ts:788`, 4 casi | 15/15 verde | in corso | — |

### `tx-delete` A1-confirm: shared state (verificato)

- I 5 lotti di `front-transaction` condividono un solo DB, popolato una volta per categoria.
- Nel lotto 1, `tx-bulk-operations` «mixed commit»:
  - prende per posizione le prime righe modificabili (`getEditableRowIds`);
  - riscrive la descrizione di `ids[0]` in `E2E-mixed-commit-<ts>`;
  - fa commit.
- La FEE delete-safe (oggi−2, Directa EDITOR, id più alto della DEPOSIT dello stesso giorno) è la prima riga standalone
  modificabile.
- Nel lotto 2, `A1-confirm` cerca «delete-safe» + «Platform fee» e non la trova. A1, che cerca la DEPOSIT, passa.
- **Prova**: dopo `front-transaction tx-bulk-operations` da solo, la riga #28 (FEE delete-safe) ha la descrizione
  `E2E-mixed-commit-1791383901845`. Lettura immutabile del DB della corsia.

### `multi-user`: assumption

- `getByText(brokerName)` su tutta la pagina trova il titolo della card (`h3`) e il toast di creazione «Broker "{name}"
  created.», che esiste dal 09/09 (`ef722b552`). Entrambi sono legittimi.
- Lo stesso schema c'è a `:72`, nel secondo test del blocco seriale.

### FE-SP-C1: difetto del prodotto, più un'assumption del test

- **Sonda** sulla 6165: con il menu contestuale di una riga aperto dentro la BulkModal, **un solo `Escape` chiude il
  menu e la modale**.
  - Causa: `ContextMenu.svelte:110-124` fa `preventDefault()` senza `stopPropagation()`.
  - L'evento risale a `ModalBase.svelte:149-151`, che non controlla `defaultPrevented` e chiude.
- **Il test**: `splitAction.isVisible({timeout: 500})` non aspetta, perché in Playwright quel timeout è ignorato. Prima
  riga senza `split`, quindi `Escape`, quindi la modale si chiude e `nth(1).hover()` arriva al timeout.
- Riferito al coordinator; in attesa del via.

### Sweep: in corso

- Da solo è verde. I 4 rossi della run (test 98–104) cadono in una finestra in cui entrambi i worker eseguivano solo
  casi dello sweep, e nessuno spec del lotto tocca l'onboarding di `e2e_test_user`.
- Le due strade che portano a `/dashboard`:
  1. l'intro tour;
  2. un `GET /auth/me` che fallisce durante un caricamento completo: il layout fa `goto('/')` senza `?redirect=`, e la
     root rimanda a `/dashboard`.
- Il caso «dashboard fr»: `login()` ritorna prima del redirect successivo al login, e `setLanguage` aspetta il
  selettore solo 5 s.
- Chiesto al coordinator il log del backend della run (`/tmp/librefolio-r2-main/logs/librefolio.log`).

## Passi

- [x] **18.1 Triage**: log, rilanci da soli, sonde, verdetti (vedi sopra). ✅ 2026-10-07.
- [x] **18.2 `multi-user`**: test-author, localizzatori filtrati sulla card `broker-card-*`. ✅ 2026-10-07.
  > **Note implementazione**:
  > - Helper `brokerCard(page, name)` sul prefisso `broker-card-`.
  > - Utente 1: la card è visibile; prima l'asserzione la soddisfaceva subito il toast.
  > - Utente 2:
  >   - si aspetta `data-busy="false"` di `brokers-page`;
  >   - la card «discovery» (`broker-discovery-card-*`, i broker di altri utenti elencati per nome, dal 06/07) è visibile;
  >   - 0 card proprie col nome.
  > - Esito: `front-user multi-user`, 2/2 (`/tmp/libreFolio_k18_multiuser.log`); Prettier pulito.
  >
  > **⚠️ Fuori pista**: il vecchio `page2.getByText(nome)).not.toBeVisible()` passava solo se arrivava prima che la
  > lista finisse di caricare, perché il nome è visibile nella card discovery.
  > - Il controllo sulla card discovery fissa questo comportamento del prodotto: lo segnalo nell'handoff.
  > - Rimasti fuori perimetro: i nomi con `Date.now()` invece di `uniqueSuffix()`, e i due broker creati e mai cancellati.
- [x] **18.3 `tx-bulk-operations` «mixed commit»**: test-author, crea e cancella le sue righe e non tocca le righe mock.
  ✅ 2026-10-07.
  > **Note implementazione**:
  > - Il test ora:
  >   - crea via API due DEPOSIT suoi su Interactive Brokers (OWNER verificato per nome), datati 300 giorni fa, con il
  >     marcatore `E2E-mixed-commit-<uniqueSuffix>`;
  >   - restringe la tabella con `id_min`/`id_max`;
  >   - nel commit mette una modifica, una cancellazione e un clone, quindi il titolo «create+update+delete» ora è vero;
  >   - verifica il payload, i risultati, il toast e la tabella ricaricata;
  >   - in `afterEach` cancella quello che ha creato, anche dopo un timeout.
  > - Gli altri 9 test del file non fanno commit: finiscono con Annulla/Scarta, Reset o Chiudi.
  > - Esiti:
  >   - `tx-bulk-operations` 10/10;
  >   - DB in lettura immutabile: la FEE #28 tiene «[delete-safe] Platform fee for delete test», e non resta nessuna
  >     riga `E2E-mixed-commit`;
  >   - `tx-delete` 15/15;
  >   - Prettier pulito.
  >
  > **⚠️ Fuori pista**: il test-author si è fermato prima di eseguire. La mia riproduzione dello sweep con `--coverage`
  > aveva lasciato una build strumentata, e il suo comando ne avrebbe forzato la ricostruzione. Ho ricostruito io la
  > build `--debug`, poi ho eseguito io i tre comandi, uno per volta.
- [x] **18.4 FE-SP-C1 ed Escape**: dopo il via. ✅ 2026-10-07.
  > **Decisione del developer** (testuale): «Sì: ContextMenu, più SearchSelect e AiExportMenu se il difetto si riproduce
  > in una modale».
  > - **AiExportMenu**: è montato solo nelle toolbar delle pagine, mai in una modale. Non si tocca; riferito al
  >   coordinator.
  > - **Rosso** (test-author): `ui/modals/ModalBase.escapeLayers.test.ts` con l'harness
  >   `__tests__/harness/ModalEscapeLayersHarness.svelte`, registrato in `component-unit` dopo `ModalBase.test.ts`.
  >   - 3 rossi su `onRequestClose` chiamato:
  >     - menu di riga;
  >     - select col box di ricerca nella lista;
  >     - select inline, col focus sul trigger della lista aperta.
  >   - Una guardia (il box inline, che è già sicuro) e 3 controlli: niente aperto, oppure select chiusa → l'Escape chiude
  >     la modale.
  >   - Il test-author ha simulato la cura (7/7 verdi) e una cura troppo larga, che i controlli fanno diventare rossa.
  > - **Cura**: `e.stopPropagation()` sull'Escape consumato.
  >   - `ContextMenu.svelte`: nel listener di cattura su `window`, attivo solo a menu montato.
  >   - `SearchSelect.svelte`: in `handleSearchKeydown`, che si raggiunge solo a lista aperta.
  > - **Esito**: vitest su `ModalBase.escapeLayers`, `ModalBase`, `SearchSelect`, `SearchSelect.reopen` e
  >   `CurrencySearchSelect`, 49/49; Prettier pulito.
  > - **Non coperto dalla cura approvata, proposto al coordinator**: una select in modalità a tendina, aperta, col focus
  >   sul trigger (per esempio dopo Shift+Tab dal box di ricerca). `handleTriggerKeydown` inoltra i tasti solo con
  >   `inlineSearch`, quindi quell'Escape chiude la modale e lascia la lista aperta.
  > - **FE-SP-C1** (test-author, solo lo spec):
  >   - dopo il clic sul kebab il test aspetta il menu; la decisione su Split si prende dentro il menu aperto;
  >   - sul ramo dell'Escape verifica che il menu si chiuda e che la BulkModal resti visibile e **non `inert`**, quindi la
  >     cura è fissata anche in E2E;
  >   - lo split ora è obbligatorio: la riga si sceglie con `['delete-safe', 'ETH']`, perché «delete-safe» da solo
  >     trova anche DEPOSIT e FEE, che non si dividono;
  >   - gli altri 7 `isVisible({timeout})` sono diventati `appears()` o un helper `closeBulkModal` comune.
  > - Esito: `front-transaction tx-bulk-suggest-ux` 8/8, FE-SP-C1 in 4,8 s; Prettier pulito.
  >
  > **⚠️ Fuori pista**:
  > - Il vecchio localizzatore della conferma di scarto (`[data-testid="confirm-modal"] button`) non trovava niente,
  >   perché nessun componente rende quel testid. Ora si usa `confirm-modal-confirm`.
  > - **Rischio latente, fuori dai miei rossi**: `tx-split-promote` C3 fa commit di uno split della stessa coppia condivisa
  >   e non la ripristina. In una run completa in cui C3 venga prima, FE-SP-C1 fallirebbe, e il messaggio nomina C3.
  >   Oggi C3 sta in un lotto successivo. La cura va in C3: riferito nell'handoff.
- [x] **18.5 Sweep**: verdetto e correzione. ✅ 2026-10-07.
  > **Verdetti**:
  > - **104, dashboard fr: assumption (orologio).** `login()` ritorna prima del redirect successivo al login, e
  >   `setLanguage` aspetta il selettore solo 5 s.
  > - **98, 100 e 103: environment.**
  >   - Sono i tre casi che il worker W1 ha eseguito di fila durante un picco di sovraccarico: il caso parallelo 99 sull'altro worker è durato 102 s invece di circa 30.
  >   - Da soli sono verdi due volte, una con la build strumentata `--coverage`.
  >   - Il log dell'app del backend non mostra nessuna anomalia.
  >   - Meccanismo probabile, visto nel codice ma non osservato: `(app)/+layout.svelte:86-99` mette `checkAuth()` in gara
  >     con un timeout di **5 s**. Allo scadere fa `goto('/')` senza `?redirect=`, e la root rimanda a `/dashboard`.
  >
  > **Correzione** (test-author, solo lo spec):
  > - dopo `login()` si aspetta che l'URL lasci `/` e che compaia il selettore della lingua (30 s ciascuno);
  > - il precondition ora porta le prove:
  >   - la scia delle navigazioni dal `navigateTo`;
  >   - stato e durata di `/auth/me` e `/settings/onboarding`;
  >   - le superfici di onboarding a schermo;
  >   - un allegato `<barra>-<lingua>-arrival.json`.
  > - Mai ritentato: un rimbalzo è un reperto.
  > - Esito: `front-utility toolbar-width-sweep`, 15/15 in 2,7 min (carico 25–30).
  > - Il testo diagnostico è stato provato su una copia fuori dal repo con risposte simulate.
- [x] **18.6 BrokerModal**: rosso col test-author, poi cura del ramo di modifica (`results[0].success`). ✅ 2026-10-07.
  > **Note implementazione**:
  > - **Rosso** (test-author, in coda a `BrokerModal.test.ts`, nuovo blocco «edit refusals answered with HTTP 200»).
  >   - 2 rossi sulla baseline:
  >     - rinomina rifiutata per nome duplicato;
  >     - overdraft tolto e rifiutato dalla validazione dei saldi.
  >   - In entrambi: cache aggiornata, `onupdated` e `onclose` chiamati, nessun messaggio nel form.
  >   - Il controllo (`success: true`, con `validation_triggered`) era verde; i 12 test esistenti restano verdi.
  >   - I test verificano anche:
  >     - la bozza conservata;
  >     - nessun toast;
  >     - che la chiusura chieda conferma di scartare, perché `formTouched` non si azzera.
  > - **Cura** in `BrokerModal.svelte` (ramo di modifica): dopo il controllo HTTP si legge `results[0]`. Se
  >   `!success`:
  >   - `error = errore localizzato con localizeDuplicateName, oppure il testo dato, oppure brokers.updateFailed`;
  >   - `return`, senza `mergeBrokers`, `onupdated` né chiusura.
  >   - È lo stesso schema del ramo di creazione; nessuna chiave nuova.
  > - **Esito**: vitest su `src/lib/components/brokers/`, 12 file e 480/480; Prettier pulito.
- [x] **18.7 Verifica e handoff**: CHECKPOINT READY, FROZEN. ✅ 2026-10-07.
  > **Note implementazione** (corsia 6155, un comando per volta, carico 25–33):
  > - `front build --debug` ok; `front check` 0/0; `check-orphans` ok.
  > - `component-unit`: exit 0, 110 file, 2839/2839, nessun errore non gestito.
  > - E2E, da `/tmp/libreFolio_k18_e2e_gates.sh`:

  > | categoria | voce | esito |
  > |---|---|---|
  > | front-broker | list | 9/9 |
  > | front-broker | detail | 33/33 |
  > | front-broker | broker-create-feedback | 2/2 |
  > | front-user | multi-user | 2/2 |
  > | front-utility | select | 17/17 |
  > | front-asset | asset-modal | 17/17 |
  > | front-transaction | tx-bulk-operations | 10/10 |
  > | front-transaction | tx-delete | 15/15 |
  > | front-transaction | tx-bulk-suggest-ux | 8/8 |
  > | front-utility | toolbar-width-sweep | 15/15 |

  > - Quattro commit proposti, con i messaggi in `/tmp/libreFolio_commits/` e il manifesto `k-18-manifest.txt`:
  >   1. `Escape`;
  >   2. `BrokerModal`;
  >   3. le correzioni dei test;
  >   4. il journal.
  > - **File condiviso**: `scripts/test_runner/_frontend_utility.py`, una sola riga aggiunta (registrazione).
  > - **Lotto successivo, approvato** («Sì, nella 1.2: pagina conservata, e un timeout non è un logout»): l'avvio
  >   dell'app (`checkAuth`). Parte dopo il merge di `dev_release2`, che contiene S17 di O, nel ramo di K.

## Definizione di fatto

1. Ogni rosso ha un verdetto fra i cinque, con le prove.
2. Le correzioni dei test sono del test-author; per le cure del prodotto prima il rosso e poi il via del coordinator.
3. Le regressioni coinvolte sono verdi nella 6155.
4. Porte libere, nessun venv del worktree, nel worktree solo i file previsti.

## Seguito

- Lo step 19 è l'avvio dell'app (un timeout non è un logout), più il backdrop delle modali e l'Esc del trigger di
  SearchSelect: [`plan-phase00TaxonomySelectStep19AppStartAuth.prompt.md`](plan-phase00TaxonomySelectStep19AppStartAuth.prompt.md).
