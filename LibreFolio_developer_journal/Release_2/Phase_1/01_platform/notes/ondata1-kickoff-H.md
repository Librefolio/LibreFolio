# Brief — workstream H · Piattaforma · H-61 checkpoint 1 (chiusura)

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-sturdy-memory`
**Branch**: `e-alfy-h-piattaforma`
**HEAD di partenza (da verificare)**: `8db27b418` (merge di `dev_release2` `208199bf6` nel tuo ramo; genitori `f9f417bfa` e `208199bf6`).
**Corsia**: porta `6181`, cartella dati `/tmp/librefolio-r13-h`.
**Piano**: `LibreFolio_developer_journal/Release_2/Phase_1/01_platform/plan-phase01Platform.prompt.md`. Leggi solo queste sezioni: «Lotto H-61: Hosting panel» (riga ~9655), «H-61, il via e le decisioni (20/10, 11:43) — passi del checkpoint 1», «H-61, checkpoint 2 … preparazione» (riga ~10079).

## Dove eri rimasto
Il 20/10 hai chiuso L1 del pannello (token per scopo, limite, log, tag «Hosting panel», controllo `platform.hosting_panel`, Q5 sulla sospensione) e il coordinatore l'ha committato come **checkpoint intermedio** (`e917659c9`) con **rossi voluti**: `api panel-status` 20, `api hosting-panel-routes` 4 su 15, `api instance-block` 1, perché mancava R1. Poi ha portato nel tuo ramo il pezzo di A (`admin_setup_status()`, commit `64b8b9fa3`) e, oggi, `dev_release2` (che contiene anche `frontend/e2e/fixtures/gallerySecurity.ts` di G). Non ci sono lavori tuoi sporchi tranne 3 file di test **non tracciati** di CP2 (`test_services/test_hosting_panel_{tickets,registry,access_tickets}.py`): **lasciali dove sono, non li toccare, non li lanciare**.

## Cosa fare ora (un solo lotto: chiudere il checkpoint 1)
1. **Rileggi da solo i file fusi** da A e da `dev_release2` (le tre doc che toccavate entrambi: `admin/settings.en.md`, `developer/architecture/security.md`, `developer/architecture/settings.md`, più `access_control.md`). Se qualcosa non torna, dillo.
2. **R1**: la rotta `GET /api/v1/panel/status`, con il contratto già concordato col coordinatore e con A (piano, «il via e le decisioni»). In sintesi:
   - risposta `{"admin_setup": "none|pending|done|expired", "setup_expires_at": <ISO UTC>|null}`; `setup_expires_at` solo in `pending` (Q10); nessuna email, nome o conteggio;
   - usa `admin_setup_status()` di A (regola «done wins»: un link di setup consumato vale `done`);
   - token apposito `LIBREFOLIO_PANEL_STATUS_TOKEN` (Q2); 404 solo per uno scopo spento, 401 per credenziale assente o sbagliata (Q3); risponde anche a istanza bloccata; non conta come visita per la sospensione (condizioni di Z già applicate);
   - il codice di partenza era stato preparato fuori dal worktree: cerca in `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/copilot-enel/session-state/8490facf-9334-4a96-9821-4b3cd3679d4d/files/h61/`.
3. **Rimando in doc** a `access_control.md#setup-status` (ancora nuova di A) dalle pagine che descrivono la rotta.
4. **18ª voce della fixture di G**, `frontend/e2e/fixtures/gallerySecurity.ts` (il coordinatore dei colori ti ha concesso il file per questa voce): tra `platform.log_level` e `platform.test_mode`, come in `CONFIG_CHECKS`, ramo `ok` del self-hosted:
   `{check_id: 'platform.hosting_panel', severity: 'ok', i18n_key: 'instance.checks.hostingPanel.off', detail: {}}`; aggiorna il commento in testa al file (elenco dei rami `ok`). Prove: `frontend/node_modules/.bin/prettier --check` e `frontend/node_modules/.bin/tsc -p frontend/tsconfig.e2e.json`. **Nessuna corsa della galleria.**
5. **Corse** (una alla volta, ciascuna sulla tua corsia, carico sotto 8): le tre che erano rosse (`api panel-status`, `api hosting-panel-routes`, `api instance-block`) devono diventare verdi; poi tutta la lista di CP1: `services hosting-panel-access` 102, `services config-audit` 255, `services config-env-example` 39, `api backup-panel` 61, `api backup` 23, `api system-wake` 76, `api system` 122, `services sleep-wake-activity` 139, `services sleep-wake-suspend` 141, `services backup-checks` 93, `front-utility core-unit`; più `ruff`/`black` e `mkdocs build` stretto + `check-links`. Prima la corsia va popolata (vedi regole comuni).
6. Aggiorna il piano (✅, note, fuori pista) e consegna il **CHECKPOINT READY**: elenco esatto dei file, prove, riga CHANGELOG proposta (la rotta del pannello è visibile all'host), messaggio di commit proposto.

## Non fare
- **Non iniziare CP2** (biglietti Ed25519): niente codice di CP2 nel worktree finché il checkpoint 1 non è in `dev_release2`.
- Non toccare i file di B (`backup/`) e di Z (`sleep_wake/`) oltre alle righe già concordate (BACKUP-001 e WAKE-025 sono già aggiornate).
- Nessuna dipendenza nuova.

## Fatto quando
Tutte le corse sopra sono verdi (nessun rosso rimasto di CP1), la doc è coerente con la rotta, la fixture ha 18 voci, il piano è aggiornato e hai scritto **FROZEN**.
