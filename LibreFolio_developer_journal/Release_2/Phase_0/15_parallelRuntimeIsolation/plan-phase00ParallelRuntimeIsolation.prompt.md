# Runtime isolati per sviluppo e test paralleli

**Avvio:** 2026-09-09. **Owner:** coordinatore Release 2.
**Baseline:** `ef722b552433028c051ccb1207c84f1072e51bb7`
(`dev_release2`).
**Commit consegnato:** `916f12bddf3eb9b8e834e4b9033eb52ce4bde25a`
(`feat(dev): isolate test runtime lanes`, 2026-09-10).
**Mandato:** rendere porta e data directory esplicitamente configurabili per
`./dev.py server` e `./dev.py test`, mantenendo invariati i default. Aggiornare
istruzioni/skill, validare due lane realmente indipendenti e poi sbloccare B/C/D.
**Vincolo Git:** il dev crea il commit dedicato; l'agente non esegue commit,
push, rebase o reset.

## Contratto

- Senza opzioni, tutto resta invariato: produzione `6040` +
  `backend/data/prod`; test `6041` + `backend/data/test`.
- `server --port N --data-dir PATH` configura il processo server.
- In test mode, `--data-dir` usa `LIBREFOLIO_TEST_DATA_DIR`; non riusa
  `LIBREFOLIO_DATA_DIR`.
- `test --test-port N --data-dir PATH` configura runner, processi pytest,
  backend condiviso, Playwright, global setup e processi figli.
- Una lane parallela e' valida solo con **porta e data directory entrambe
  uniche**. Il parallelismo interno a una lane continua a condividere backend,
  database e utenti.
- Il target test non puo' coincidere, anche tramite path relativo/symlink, con
  la directory dati produzione canonica o configurata.

## 0. Baseline, conoscenza e regressioni - ✅ completato 2026-09-09

- [x] Confermare branch/HEAD e working tree.
- [x] Consultare devWiki su runner, isolamento e separazione prod/test.
- [x] Leggere config, CLI, runner, shared server, Playwright e istruzioni
  pertinenti.
- [x] Far aggiungere al `test-author` regressioni pure e registrazione runner,
  senza avviare suite o server.

> **Note implementazione (2026-09-09):** la devWiki conferma che il runner ha
> un backend condiviso per invocazione e che la separazione prod/test e' un
> confine di sicurezza. Il codice attuale propaga gia' `TEST_PORT` a molte
> superfici, ma congela i path DB al momento dell'import e contiene tre URL E2E
> hardcoded su `6041`. Le regressioni coprono default, override, alias della
> produzione, parser e ordine di applicazione prima dello shared server.

## 1. Configurazione runtime e propagazione - ✅ completato 2026-09-09

- [x] Aggiungere risoluzione/validazione condivisa di porta e test data dir.
- [x] Rendere dinamici path e URL del test DB.
- [x] Collegare opzioni server/test e preservare gli env nei processi figli.
- [x] Eliminare gli URL E2E hardcoded sulla porta predefinita.

> **Note implementazione (2026-09-09):** `configure_test_runtime` risolve una
> lane, normalizza ed esporta sempre i valori effettivi e rifiuta alias reali/symlink
> della directory produzione. `server --test` e `test` applicano il contratto
> prima di creare DB, shared backend o child process. I path/URL del test DB
> sono ora risolti al momento dell'uso, non congelati all'import. Playwright e
> i tre client E2E assoluti leggono `TEST_PORT`; quattro guardie E2E verificano
> la porta selezionata anziche' imporre `6041`.
>
> **Note verifica (2026-09-09):** il selettore puro e' stato eseguito dalla
> nuova lane `6141` + `/tmp/librefolio-runtime-isolation-contract`: 133/133
> test verdi. Le regressioni includono precedence dotenv/Pipenv, collisioni,
> ownership dei processi, marker produzione, alias case-insensitive e symlink.
>
> **⚠️ Fuori pista (2026-09-09):** la review indipendente ha trovato che
> `pipenv run` ricaricava `.env` sopra gli override del parent, che la readiness
> basata sul solo HTTP 200 poteva accettare un'altra lane e che `--force`
> automatico poteva terminarla. Il runner ora normalizza l'ambiente una volta,
> usa un nonce verificato anche nell'header HTTP e non riusa/uccide listener
> non propri. Un marker persistente protegge anche data root produzione avviate
> con un override non visibile al futuro processo test.

## 2. Guidance per agenti e coordinamento - ✅ completato 2026-09-09

- [x] Aggiornare `.env.example`, istruzioni Copilot/testing, agente test-author
  e skill `devpy-server`, `devpy`, `testing-backend`, `testing-frontend`.
- [x] Aggiornare il piano di riallineamento B/C/D con lane uniche.
- [x] Registrare qui comandi assegnati e confini operativi.

> **Note implementazione (2026-09-09):** la regola storica "un solo
> DB/backend" e' ora esplicitamente per-lane: non cambia l'isolamento interno
> delle suite, ma consente worktree concorrenti se entrambi i valori sono
> distinti. Lane assegnate per il prossimo riallineamento: coordinatore
> `6150` + `/tmp/librefolio-r2-main`; B `6151` +
> `/tmp/librefolio-r2-b`; C `6152` + `/tmp/librefolio-r2-c`; D `6153` +
> `/tmp/librefolio-r2-d`. Nessun agente usa `--force` su una porta altrui.

## 3. Verifica e handoff - ✅ completato 2026-09-10

- [x] Eseguire il selettore puro `utils runtime-isolation`.
- [x] Provare due backend contemporanei su porte e data directory distinte,
  verificando health e path DB senza dati produzione.
- [x] Eseguire i controlli mirati gia' esistenti su runner/config/Playwright.
- [x] Preparare il messaggio di commit dedicato, senza committare.
- [x] Comunicare a B, C e D il contratto e le rispettive lane dopo il commit
  manuale del dev.

> **Note verifica (2026-09-09):** `utils runtime-isolation` 133/133;
> `api system` 24/24; Playwright header desktop/mobile 4/4; front check
> 0 errori/0 warning; API sync idempotente; catalogo test interamente
> registrato e raggiungibile. Due server reali simultanei hanno risposto solo
> al proprio nonce (`cross-token` 404); una scrittura sintetica ha prodotto
> utenti `1/0` nei due DB distinti. Verificati anche path con spazi/due punti,
> marker produzione persistente, collisione porta fail-closed e teardown senza
> listener residui. La review indipendente finale non rileva issue significative.
>
> **Handoff:** messaggio pronto in
> `/tmp/libreFolio_commit_runtime_isolation.txt`. B/C/D ricevono i comandi
> definitivi solo dopo che il dev crea il commit e comunica lo SHA.
>
> **Note handoff (2026-09-10):** commit verificato su `dev_release2`, checkout
> pulito. B/C/D sono ancora sulla baseline `4a73f5f6` con delta locali non
> committati: hanno ricevuto l'ordine di congelare un checkpoint, proporre il
> messaggio di commit e censire i conflitti. Nessun agente esegue operazioni
> Git mutanti. Dopo i checkpoint manuali del dev incorporeranno `916f12bd` e
> attiveranno rispettivamente le lane 6151/B, 6152/C e 6153/D.
>
> **⚠️ Fuori pista (2026-09-10):** il primo avvio D ha mostrato che Pipenv
> identifica il progetto dal path del worktree e crea un venv nuovo vuoto.
> Nessuna dipendenza viene duplicata: B/C/D usano il venv locked principale con
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc`, senza leggere il checkout
> principale. Verificati interprete e import `argcomplete`/`pydantic`; il venv
> vuoto D non viene modificato o rimosso durante i gate.

## Definition of done

- I comandi senza override mantengono byte per byte la semantica operativa
  precedente.
- Due worktree possono eseguire server/test in parallelo senza porta, DB,
  upload, log o report broker condivisi.
- Ogni child process riceve `TEST_PORT` e `LIBREFOLIO_TEST_DATA_DIR`.
- Un test target uguale alla directory produzione fallisce prima di qualunque
  cancellazione, migrazione o avvio server.
- Test, help CLI, istruzioni e skill descrivono lo stesso contratto.
