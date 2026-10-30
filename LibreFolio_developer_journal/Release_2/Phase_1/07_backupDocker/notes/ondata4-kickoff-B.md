# Brief — workstream B · Backup e Docker · L3: la busta a chiave pubblica, prima la specifica — bozza

> **A cosa serve (per il developer).** Oggi quello zip è in chiaro: chi ruba il token del pannello, o un log, legge tutti i dati del cliente. Con L3 l'istanza chiude lo zip con il «lucchetto aperto» del cliente (la sua chiave pubblica): da quel momento **nemmeno lei** può riaprirlo, e il token rubato scarica solo file illeggibili. Solo il coordinatore, con la chiave privata, apre i 32 byte della chiave del file e li manda alla macchina nuova insieme allo zip ancora cifrato: nessun dato in chiaro passa da lui.
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-miniature-telegram` · **Branch**: `e-alfy-b-backup-e-docker`
**HEAD di partenza (da verificare)**: `c042f2481` (= `dev_release2`; il coordinatore fa il fast-forward da `1fd559a26`, 309 commit dietro, e `npm ci` per Linux: i `node_modules` erano `darwin-arm64`).
**Corsia**: porta `6192`, cartella dati `/tmp/librefolio-r13-b`.
**Piano**: il tuo, `LibreFolio_developer_journal/Release_2/Phase_1/07_backupDocker/plan-phase01BackupDocker.prompt.md` (apri una sezione nuova «L3 — la busta a chiave pubblica (ondata 4)»; non rileggere tutto: cerca «3.3», «3.14», «B3», «B4», «B5c», «B-18»). La proposta del pianificatore: `salvataggi-worktrees-20261021/ondata4/PIANO-backup-L3.md` (leggilo tutto, sono ~300 righe). Decisioni del developer: `LibreFolio_prj/BACKUP-decisioni-20261022.md` (fonte di verità). _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
**Modello**: Opus (crittografia e sicurezza).

## Passo B1 — la specifica con i vettori di prova (2-3 giorni, nessun codice di prodotto)
È il **primo prodotto del lotto**, e si ferma al tuo checkpoint: il developer la approva, poi si codifica.
1. Leggi `instance_backup/envelope.py` (320 righe: il formato di oggi), `secure.py`, `api/v1/backup/panel.py`, `job_views.py`, `restore_jobs.py:137-280`, `staging.py:160-215` e `:794-880`, `hosting_panel/access.py`, `config/hosting_panel.py:562-606` (il formato `kid:chiave` da imitare).
2. Scrivi la specifica come documento in inglese, nel tuo worktree, in `mkdocs_src/docs/developer/backend/backup_envelope.en.md` (o dove la doc per sviluppatori tiene il backup: verifica), partendo da `PIANO-backup-L3.md` §3: layout dell'intestazione versione 2 (148 byte), scambio X25519 + HKDF-SHA256 (salt `E || P_i`, info `librefolio-lfbk/v2/x25519-wrap`), avvolgimento AES-256-GCM della chiave del file (nonce zero, `aad = header[0:100]`), `kid = SHA-256(P_i)[:16]`, variabile `LIBREFOLIO_BACKUP_PUBLIC_KEY` (base64url 43 caratteri, non segreta), i limiti del lettore, i codici d'errore (`wrong_file_key`, `file_key_required`, `file_key_invalid`). **Dove la proposta ti sembra sbagliata, dillo e proponi meglio, con il perché**: la proposta è una bozza, non una decisione.
3. Scrivi anche il contratto delle rotte del pannello e del modo «ripristino in corso» (§3.5 e §3.6): le rotte le farà H, ma la specifica è una sola e la scrivi tu, con H che la rivede.
4. **Vettori di prova** (§3.4): un file JSON con chiave privata di prova, pubblica, `kid`, `e` effimera fissa, `nonce_prefix` fisso, `chunk_size = 65536`, un testo corto, l'intestazione attesa in hex, `W`, `K_f`, lo `sha256` del file; più «chiave sbagliata», «intestazione manomessa», e una busta versione 1 di oggi. Generali con uno script nel tuo worktree che usa solo `cryptography` (non toccare ancora `envelope.py`). Il coordinatore cloud deve poter aprire `W` dai vettori con la sua implementazione: scrivi i passi in chiaro.
5. **Domande per il developer** nel checkpoint, se ne trovi oltre alle 3-8 del piano. Consegna **CHECKPOINT READY (B1)** e **FROZEN**.

## Passo B2 — la busta v2 (dopo l'ok alla specifica)
`envelope.py` legge v1 e v2; `seal_file(src, dst, public_key)`, `open_with_file_key(path, key) → EnvelopeKey`, `kid_of(public_key)`; `config/backup.py` legge `LIBREFOLIO_BACKUP_PUBLIC_KEY` (fail-closed: valore illeggibile → controllo d'avvio `backup.public_key` in errore e `503 backup_panel_unavailable`, mai uno zip in chiaro); il job del pannello sigilla quando la chiave c'è (`file_name` `.lfbk`, `encrypted: true`, `sealed_kid`); `file_sha256` nella vista API (`job_views.job_view`, oggi lo toglie); CLI `keygen`, `create --public-key/--sealed`, `decrypt/inspect/restore --private-key-file` e `--file-key-file`. **Rossi prima**: `services backup-envelope` sui vettori (byte identici), v1 ancora leggibile, `S` tutto zero rifiutato, `api backup-panel` (busta con la chiave, 503 con chiave illeggibile, `file_sha256`, mai la chiave d'istanza: `instance_key_included` falso), `utils backup-cli*`. `api sync`, `front check`.

## Passo B3 — l'apertura con la chiave del file nel ripristino
`restore_jobs.start_check(upload_id, *, password=None, file_key=None)`; `_envelope_key` con i due ingressi; `FileKeyRequiredError`; i due avvisi del rapporto (`credentials_from_backup` sempre; `confirming_account_not_in_backup` quando chi conferma dalla UI non è fra gli `administrators` della copia) in `RestoreStageReport` e in `RestoreReportModal.svelte` (avviso forte, 4 lingue). Rossi: `services backup-staging`, `api backup-restore`, Vitest del modale.

## Passo B4 — doc (con `docs-writer`)
`backup_restore.en.md`: «Backups with backrest or restic» (zip notturno in cartella con `--output`, poi `restic`/backrest verso S3/B2/SFTP; restic non cifra a chiave pubblica: la sua chiave si custodisce come una password); «Secure Backups» con `keygen`, `--public-key`, `decrypt --private-key-file`. `configuration.en.md`: variabile e controllo. Le righe della guida hoster le proponi a H (file suo). `mkdocs build` stretto e `check-links`.

## Passo B5 — il round trip L3 e gli E2E (dopo le rotte di H)
Estendi `api backup-roundtrip` (`scripts/test_runner/_backend_api.py:1427`, con `test-author`): istanza popolata → busta del pannello → `kid` e `sha256` controllati → apertura di `W` con la privata di prova (il «coordinatore» del test) → istanza vuota in modo «ripristino in corso» (`LIBREFOLIO_AWAIT_RESTORE=1` nella corsia) → `PUT/POST` sulle rotte del pannello con un biglietto `backup:restore` → `confirm` → `restart` → avvio in un processo nuovo → `committed` → stesse righe e stessi report → variabile tolta → login con le credenziali del backup. Scritto **prima** della cura di H2, come rosso. Più l'E2E Playwright di `RestoreReportModal` con l'avviso forte. Verde due volte di fila.

## File condivisi
- Tuoi: `instance_backup/**`, `api/v1/backup/{instance,restore,job_views,exports,panel}.py`, `api/v1/backup/__init__.py` (H vi aggiunge una riga dopo B2), `config/backup.py`, `schemas/backup.py`, `scripts/backup_cli.py`, `lib/features/backup/**`, `backup_restore.en.md`.
- Di H: `hosting_panel/**`, `config/hosting_panel.py`, `config/platform.py`, `api/v1/panel.py`, `instance_block.py`, `app_lifespan.py`, `hosting_providers.en.md`. Chiedi tramite il coordinatore.
- `Pipfile`: non aggiungere dipendenze (`cryptography` basta: X25519, HKDF, AESGCM ci sono).

## Non fare
- Niente Litestream, niente replica, niente `start_server.py`, niente bucket: sono usciti con le decisioni del 22/10.
- Niente chiave privata nel repo, nei log, nei messaggi d'errore, nei `repr`: solo chiavi di prova nei vettori, dichiarate tali.
- Non cambiare la busta con password (versione 1): deve restare byte per byte com'è.
- Non scrivere la rotta del pannello né il modo: sono di H (H1, H2). Tu dai le firme di servizio e la specifica.

## Fatto quando
B1: specifica e vettori consegnati, approvati dal developer, letti dal coordinatore cloud. B2-B5: rossi→verdi sulla corsia, round trip verde due volte, doc verdi, piano aggiornato, righe CHANGELOG proposte (✨ busta a chiave pubblica e `backup keygen`; 🔄 `file_sha256` nei lavori di backup), **CHECKPOINT READY** e **FROZEN** a ogni passo. Poi la revisione di sicurezza indipendente del coordinatore, le cure, il treno 10.
