# Brief — workstream H · Piattaforma · H-61 checkpoint 2 (L2, i biglietti firmati)

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-sturdy-memory`
**Branch**: `e-alfy-h-piattaforma`
**HEAD di partenza (da verificare)**: `89e8b2e61` (= `dev_release2`; il checkpoint 1 è in dev dal treno 6; fast-forward fatto dal coordinatore).
**Corsia**: porta `6181`, cartella dati `/tmp/librefolio-r13-h`.
**Piano**: `LibreFolio_developer_journal/Release_2/Phase_1/01_platform/plan-phase01Platform.prompt.md`. Leggi solo: «Lotto H-61: Hosting panel» (riga ~9655, il contratto), «H-61, checkpoint 2 (L2, i biglietti firmati)» (~10124). Attenzione: «CP2» alle righe ~250/~701 è un'altra cosa (il taglio di `main.py`).
**Bozze**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/copilot-enel/session-state/8490facf-9334-4a96-9821-4b3cd3679d4d/files/h61/`: `cp2_contract.md` (§7 aggiunte), `rules_cp2.md`, `analysis.md`, `dry2/tickets.py`, `dry2/ticket_registry.py`, `dry2/config_l2_additions.py`, `dry2/apply_access_l2.py`. Percorsi del Mac dentro: adattali, non lanciarli così.

## Dove eri rimasto
Il checkpoint 1 (L1 + R1 `GET /api/v1/panel/status` + 18ª voce `platform.hosting_panel`) è in dev. Nel worktree ci sono **3 file di test non tracciati** di CP2, scritti il 20/10 e mai eseguiti: `backend/test_scripts/test_services/test_hosting_panel_tickets.py` (TA-T1, 27 funzioni, ~212 casi, orologio fisso al 2033), `test_hosting_panel_registry.py` (TA-T2, 11 test, 23 casi), `test_hosting_panel_access_tickets.py` (TA-T3, 14 funzioni, 84 casi). **Sono il tuo lavoro: non cancellarli.** Una copia è in `salvataggi-worktrees-20261021/e-alfy-h-piattaforma.untracked.tar`.

## Cosa fare ora (un solo lotto: CP2)
1. Rilancia i tre file di rossi e **confermane la causa** (devono fallire perché manca il codice, non per import o configurazione). Registra nel runner le tre azioni (una riga additiva per volta in `scripts/test_runner/_backend_services.py`).
2. Porta il codice dalle bozze `dry2/` nel prodotto, rileggendolo riga per riga: biglietti Ed25519, registro `jti` (riuso, riavvio, thread e processi, potatura, file inservibile → 503, permessi 600), codici 401 (incluso `panel_ticket_invalid`), il limitatore che conta solo ciò che non prova nulla, il controllo all'avvio. Il «⚠️ Fuori pista» del piano vale: PyJWT verifica solo la firma, tutte le claim le controlla `verify_ticket` nell'ordine del contratto (`aud` mancante → `wrong_audience`, HPT-029). Aggiungi `panel_tickets.sqlite3` ai `managed_paths` di `validate_test_data_dir`.
3. Verdi: i tre file nuovi, poi `services hosting-panel-access`, `api hosting-panel-routes`, `api panel-status`, `api backup-panel`, `api instance-block` (una suite alla volta, carico sotto 8), `api sync` senza diff inattesi.
4. **Vettori di prova nella guida** (doc per sviluppatori, inglese, `docs-writer`): esempi di biglietto valido e dei rifiuti, che il pannello del cloud userà come contratto.
5. Piano aggiornato, righe CHANGELOG proposte, **CHECKPOINT READY**, **FROZEN**.

## Sicurezza
È codice di autenticazione. Prima del checkpoint fai tu una **auto-revisione** con l'agente `security-review` sul diff (non sui file di altri) e riporta l'esito nel checkpoint. Il coordinatore farà una seconda revisione indipendente prima del commit. Nessuna chiave vera nel repo: solo chiavi di prova generate nei test.

## Non fare
- Niente modifiche al contratto senza chiedere: se il contratto in `cp2_contract.md` e i test non coincidono, chiudi il turno con la domanda.
- Non toccare `frontend/e2e/fixtures/gallerySecurity.ts` (di G) oltre la voce già tua.
- Nessuna dipendenza nuova (se manca un pacchetto per Ed25519, chiedi: `cryptography` e PyJWT ci sono già? verificalo con `pipenv graph` in sola lettura).

## Fatto quando
I ~320 casi dei tre file verdi per la causa giusta, le suite vicine verdi, `api sync` pulito, auto-revisione di sicurezza riportata, doc e piano aggiornati, **CHECKPOINT READY** e **FROZEN**.
