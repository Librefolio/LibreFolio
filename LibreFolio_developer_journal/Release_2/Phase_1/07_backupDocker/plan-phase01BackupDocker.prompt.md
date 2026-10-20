# B · Backup e Docker — piano della sessione (fase 01, 1.3.0)

> **Piano della sessione B · Backup e Docker** (fase 01, 1.3.0). L'analisi (§0-§12) è del 15/10 ed è stata
> consegnata al coordinatore («Release 1.3 planning», `928ffa97`); lo stato vivo è nel §13 «Avanzamento».
>
> - Worktree `LibreFolio-worktrees/e-alfy-miniature-telegram`; ramo `e-alfy-b-backup-e-docker` (rinominato dall'app
>   all'avvio, prima `e-alfy-miniature-telegram`).
> - Base dell'analisi `ee5d81a6f`; base di B0 `23f6578f3` (avanzamento veloce del coordinatore, con i lotti A–D di R).
> - Corsia: porta 6187, data-dir `/tmp/librefolio-r13-b`.
> - Grafo della devWiki assente, come previsto: lette le pagine committate `entities/backup-router`, `features/F-073`,
>   `domains/infrastructure`, `decisions/single-docker-image`, `concepts/single-migration-strategy`,
>   `problems/docker-entrypoint-gid20-collision`, `problems/devpy-unusable-in-docker-image`,
>   `problems/db-path-argument-ignored-by-alembic`.
> - Fonti: specifica del fondatore (righe 17, 41, 49-62, più la 82 sull'SMTP), piano generale §3-§10, decisioni 12, 18 e
>   35, backlog (H-3, M-1, sezione B), piano di H (§3.3, §3.7, §4-§7, CP3), piano di X (§4.4-§4.5), piano di A (A3,
>   A4b), codice di `ee5d81a6f` più CP5a (`9deb0ea08`, letto con `git show`), documentazione di Litestream v0.5.
> - Il piano entra nel journal al primo checkpoint (B0), come piano 07.

## 0. In breve

- **Il backup è uno zip con la forma della cartella dati**, più `manifest.json`: scompattato in `./LibreFolio-data`,
  parte e si migra da solo. Il DB entra con `VACUUM INTO`, mai il file a caldo.
- **Il ripristino passa sempre da una copia**: estrazione con controlli, decisione sulla revisione (più nuova o
  sconosciuta → rifiuto; uguale → diretto; più vecchia → `alembic upgrade head` sulla copia), controlli, report,
  conferma. Poi backup automatico dei dati attuali, «ripristino in attesa», uscita ordinata; al riavvio lo scambio per
  rinomina avviene prima di ogni accesso ai dati, con un giornale e il ritorno indietro automatico se l'avvio fallisce.
- **Segreti**: la chiave d'istanza entra solo in un archivio con password, e solo se è il file generato. La password
  passa da scrypt (mai HKDF) e cifra tutto con AES-256-GCM, con `cryptography`, già nella finestra delle dipendenze per
  X: **nessuna dipendenza nuova**. Al ripristino l'istanza tiene sempre la sua chiave: i segreti dei plugin si
  ricifrano (API di X e H) o restano «da reinserire».
- **Dopo un ripristino tutte le sessioni si chiudono**: `session_version` alzata per tutti nella copia.
- Codice nuovo in `services/platform/instance_backup/`; endpoint in `api/v1/backup/instance.py` dopo la divisione C2 di
  `backup.py` (dopo E1 di W, col via del coordinatore); CLI `dev.py backup`; scheda in `lib/features/backup/`; guida
  admin nuova. Nessuna migrazione.
- **Litestream** nell'immagine (v0.5.17, binario fissato e verificato), spento finché
  `LIBREFOLIO_LITESTREAM_REPLICA_URL` è vuota. Un avviatore applica il ripristino in attesa, poi `litestream restore`
  se il DB manca, poi `litestream replicate -exec uvicorn`.
- **Lotti**: B0 divisione di `backup.py` → B1 backup → B2 prova su copia → B3 ripristino e avvio → B4 password →
  B5 scheda → B6 guida → B7 Litestream → B8 token del pannello → B9 arm64 (facoltativo) → revisione di sicurezza.

## 1. Stato reale (verificato sul codice, 15/10)

| Tema | Cosa c'è | Riga |
|---|---|---|
| `/backup/export`, `/backup/restore` | `POST`, rispondono 501; solo `get_current_user`, nessun controllo admin | `api/v1/backup.py:109-128`, `:131-146` |
| Altri segnaposto | `GET /backup/formats` (tutti `available: false`), `GET /backup/status` («placeholder»), schemi `ExportFormat`, `ExportScope`, `ExportRequest/Response`, `RestoreRequest/Response` | `backup.py:46-197` |
| Export per serie | prezzi e cambi (X), eventi (W): `StreamingResponse`, ma le righe si materializzano prima | `backup.py:222-398`; `:243`, `:300`, `:364` |
| `backup_service.py` | solo gli aiuti degli export per serie (CSV con `;`, JSON con busta) | `services/platform/backup_service.py` |
| Consumatori | solo gli export per asset (`lib/api/backupDownload.ts`, `AssetCurrencyChangeModal`); nessuno usa i 4 segnaposto (frontend, doc, test) | grep |
| Test di oggi | `test_backup_api.py` (5 test dei segnaposto, `api backup`), `test_backup_export_extras.py`, `test_asset_prices_export.py` | `scripts/test_runner/_backend_api.py:262`, `:747`, `:763` |
| Cartella dati | `sqlite/app.db` (+ `-wal`, `-shm`), `custom-uploads/`, `broker_reports/{uploaded,parsed,failed}/`, `logs/`, `scheduler_state.json`, `scenario_catalog/`, `secrets/instance.key`, `.librefolio-production-data` | `config/__init__.py:5-18`, `:357-388`, `:454-473`; `scheduler/state.py:29`; `scenario_catalog/loader.py:225` |
| `secrets/` | solo `instance.key`, creato al primo `derive_key`; oggi nessun chiamante in produzione (solo i test, e `config_audit` con `instance_key_status`) | `instance_key.py:35`; grep |
| Segreto JWT | mai salvato: casuale a ogni avvio se manca, oppure `JWT_SECRET(_FILE)` | `services/accounts/auth_service.py:105` |
| Sessioni | `get_current_user` rifiuta un token il cui `sv` è diverso da `users.session_version` | `api/v1/auth.py:125` |
| Admin | `require_admin` sta nel router delle impostazioni, di A | `api/v1/settings.py:67` |
| DB | `foreign_keys=ON`, WAL, `busy_timeout` 30 s a ogni connessione | `db/session.py:52-54` |
| Migrazioni all'avvio | `ensure_database_exists()` lancia `alembic upgrade head` in un sottoprocesso se il DB è indietro, ed esce con `sys.exit(1)` se fallisce; poi i fix post-migrazione, a turno fra i worker con un lock | `main.py:99-219` (`:213`, `:217`), `:222-239`, `:287-290`; `db/post_migration/__init__.py` |
| Alembic su un'altra copia | funziona solo `-x sqlalchemy.url=…`: `get_settings()` ricalcola `DATABASE_URL` | `alembic/env.py:19-37`; wiki `db-path-argument-ignored-by-alembic` |
| Revisione head | `alembic_head_revision()` in cache, da CP5a: in `dev_release2`, non nella mia base | `9deb0ea08:backend/app/services/platform/readiness.py` |
| Avvio | lifespan: audit, segnali, Tool, `ensure_data_dirs` (`:271`), scenari, avatar, DB (`:287`), post-migrazione (`:290`), impostazioni (`:293`), prewarm, festività, scheduler (`:307`) | `main.py:242-333` |
| Più worker | `dev.py server --workers N`; il server di test ne usa più d'uno; leader dello scheduler = PID più basso | `dev.py:143-157`; `scripts/test_runner/_server.py`; `scheduler/leader.py` |
| Docker | un solo processo (`CMD uvicorn …`, niente `--workers`), PID 1 dopo `exec gosu`; `restart: unless-stopped` in tutti e due i compose; healthcheck su `/system/health`; nessuno `stop_grace_period` (10 s) | `Dockerfile:150-159`; `entrypoint.sh`; `docker-compose.yml:44`; `docker-compose.prod.yml:22` |
| Litestream | assente | — |
| Immagini pubblicate | solo amd64: `build-push-action` senza `platforms` (QEMU e Buildx già impostati) | `.github/workflows/release.yml:288-373` |
| `.env.example` | sezione «Backup and Litestream» già creata da H, vuota | `.env.example:141-144` |
| Upload di oggi | `UploadFile` letto in memoria, limite dalle impostazioni globali (`get_max_upload_mb`) | `api/v1/uploads.py:157-185` |
| Schede di Impostazioni | registro di A, 4 schede (`order` 10, 20, 30, 100); il test ha la tabella `TODAY` e un `vi.mock` per corpo | `features/settings/settingsTabs.ts:39-45`; `settingsTabs.test.ts:50-82` |
| Avvisi d'istanza | registro di H, usabile senza toccare il layout | `features/instance/instanceNotices.svelte.ts:72` |
| i18n | prefisso `backup` libero; un sottosistema è una cartella con `prefixes.txt` | `lib/i18n/*/prefixes.txt` |
| Dipendenze | `python-multipart`, `psutil` ci sono; `cryptography` no (finestra di X) | `Pipfile` |
| Docker sull'host | binario presente, daemon spento | `docker info` |

## 2. Già fatto, contraddetto, da sapere

1. **devWiki contraddetta** (per lo storico):
   - `features/F-073.md` è `implemented`, ma il backup completo risponde 501; dice «streaming, nessun accumulo», ma le
     righe si materializzano (`backup.py:243`, `:300`, `:364`); chiama `GET /backup/export`, che è `POST` (`:109`);
     cita una «sezione backup» in Impostazioni che non esiste;
   - `domains/infrastructure.md`, riga F-073: «export and import the full SQLite database — implemented»;
   - `entities/backup-router.md` è giusta («No streaming yet: responses are buffered»).

   Le correggo nel lotto che sposta `backup.py` (regola C6), oppure le passa il coordinatore a `project-historian`.
2. **«Backup della 1.2»**: la 1.2 non ha un backup. Oggi un backup di una 1.2 è solo una copia a mano della cartella
   dati (`admin/filesystem.en.md`, «💾 Backup»: `cp -r`, `sqlite3 .backup`). Perché il criterio d'accettazione e il
   cancello del §9 siano veri, il ripristino accetta anche un archivio senza manifest, con la revisione letta dal DB
   (D-B5).
   **Superato dalla decisione 42 (respinta, 15/10)**: dalla UI si ripristinano solo i backup di LibreFolio, con
   `manifest.json`; uno zip senza manifest è rifiutato (`not_a_backup`). Il passaggio dalla 1.2 alla 1.3 è
   l'aggiornamento sul posto: migrazioni e correzioni dopo le migrazioni, all'avvio.
3. **Specifica del fondatore contro D-X2**: la specifica mette sempre i segreti nello zip, D-X2 solo con password.
   Seguo D-X2, la cui spiegazione aspetta ancora la conferma del developer (D-B2).
4. **Piano di H**: «`derive_key` serve a B». Il disegno qui non usa `derive_key` per i backup scaricabili (una password
   passa da scrypt, nota H-3). A B servono il valore di controllo della chiave, l'esportazione del file generato e una
   derivazione da un materiale esplicito, per ricifrare (§3.5).
5. **Bozza della sola lettura di H** (§3.6, oggi blocco dell'istanza, decisione 12): cita `POST /backup/export`. I
   percorsi cambiano (§3.9): li passo a H per il CP6.
6. **`admin/filesystem.en.md`** (H, CP3) documenta già il backup a mano e `secrets/`: la guida nuova la richiama.
7. **Già vero senza codice**:
   - Litestream copre solo il DB (decisione 9): `custom-uploads/`, `broker_reports/` e `scenario_catalog/` sono file;
   - la configurazione SMTP non entra mai in un backup (specifica, riga 82): vive solo nell'ambiente;
   - il riavvio dell'immagine c'è già: `restart: unless-stopped` riavvia un processo che esce da solo.

## 3. Disegno

### 3.1 L'archivio

- Uno zip con la stessa forma della cartella dati:

  ```text
  manifest.json
  sqlite/app.db                 copia coerente (VACUUM INTO)
  custom-uploads/…
  broker_reports/…
  scenario_catalog/…            se c'è
  secrets/instance.key          solo con password e chiave generata (§3.5)
  ```

  Scompattato in una `./LibreFolio-data` vuota, con `docker compose up` e un'immagine uguale o più nuova, parte e si
  migra da solo: è la guida «Porta a casa».
- **Elenco d'inclusione esplicito**, mai «tutto tranne». Restano sempre fuori `logs/`, `scheduler_state.json`, i file
  di lavoro di `sqlite/` (`-wal`, `-shm`, lock e copie dei fix post-migrazione, `.app.db-litestream`), `backups/` e
  `.restore/` (nuove, §3.4) e il segnaposto di produzione.
- **`manifest.json` v1**: `format`, `format_version`, `app_version`, `alembic_revision`, `created_at` (UTC), `origin`
  (`ui`, `cli`, `pre-restore`, `panel`); DB (`sha256`, dimensione, `integrity_check`, righe per tabella); file
  (`path`, dimensione, `sha256`); totali di controllo (§3.2); chiave (`included`, `source`, `check`).
- **Archivio con password**: l'intero zip dentro una busta cifrata `.lfbk` (§3.5; estensione del developer, 38).

### 3.2 Creazione

- **Lavoro in background** (job), mai dentro la richiesta: il proxy di Fly chiude una connessione ferma da 60 s
  (decisione 33), e un DB grande con i suoi file non sta sotto quel tempo.
- **DB**: `VACUUM INTO` su una connessione `sqlite3` dedicata, in un thread, con `busy_timeout`; poi
  `PRAGMA integrity_check` sulla copia. In WAL non blocca né le scritture dell'app né lo scheduler.
- **Zip** scritto in `<DATA_DIR>/backups/` (stesso volume; spazio controllato prima con `shutil.disk_usage`), poi
  scaricato con un `<a href>` (`FileResponse` con `Content-Disposition`): nessun Blob da centinaia di MB nella memoria
  del browser.
- **Un job alla volta**, con un lock di file valido fra più worker; lo stato in un file, perché i worker non
  condividono la memoria. I file dei job si tolgono dopo un'ora o al riavvio.
- **Totali di controllo nel manifest**: righe per tabella, più i totali di portafoglio dal motore ufficiale di J.
  Funzione esatta da concordare con J; proposta: cassa nativa per broker e valuta e quantità per asset, deterministiche
  e senza prezzi. Regola 10: nessun calcolo finanziario mio.

### 3.3 Ripristino: caricamento, ispezione, prova su copia

1. **Caricamento**: `PUT` con il corpo grezzo, letto a pezzi e scritto in `<DATA_DIR>/.restore/upload/`. Il limite
   `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` si controlla su `Content-Length` e durante la lettura (413); lo spazio libero
   prima (507). Niente multipart, quindi niente copia in `/tmp`.
2. **Riconoscimento**: zip (`PK\x03\x04`) o busta `.lfbk`. Senza manifest: archivio «a mano», se contiene
   `sqlite/app.db`, anche sotto una sola cartella.
3. **Estrazione** in `.restore/stage/<id>/`:
   - solo i percorsi dell'elenco d'inclusione;
   - niente percorsi assoluti, `..`, link simbolici, dispositivi, nomi doppi o diversi solo per le maiuscole;
   - limiti sul numero di voci, sulla dimensione estratta e sul rapporto di compressione;
   - `sha256` di ogni file contro il manifest.
4. **Decisione sulla revisione** (quella del manifest, altrimenti `alembic_version` del DB):
   - sconosciuta agli script o più nuova della head → rifiuto, «aggiorna LibreFolio prima»; mai downgrade;
   - uguale → ripristino diretto: controlli d'integrità, nessuna migrazione;
   - più vecchia → prova: `alembic -x sqlalchemy.url=sqlite:///<copia> upgrade head` in un sottoprocesso, come
     `ensure_database_exists`; poi `run_post_migration_fixes(<copia>, <cartella della prova>)`.
5. **Controlli**: `integrity_check` e `foreign_key_check` prima e dopo; righe per tabella prima e dopo; totali di
   controllo ricalcolati sulla copia in un processo separato puntato sulla cartella della prova (così le cache in
   memoria dell'app non si mescolano con l'istanza viva) e confrontati con il manifest. Le differenze sono avvisi, non
   rifiuti: una migrazione di W può correggere dei dati.
6. **Preparazione della copia**: `session_version` alzata per tutti (§3.6); segreti dei plugin ricifrati o contati come
   illeggibili; valore di controllo H-3 riscritto (§3.5).
7. **Report**: versione e data del backup, revisioni di partenza e di arrivo, migrazioni applicate (id e messaggio),
   righe e totali prima e dopo, chiave inclusa o no, segreti da reinserire, avvisi, spazio necessario. La prova scade
   dopo 24 ore.

### 3.4 Conferma, scambio all'avvio, riavvio

- **Conferma** (solo admin, con l'id della prova e una conferma scritta nella UI):
  1. backup automatico dei dati attuali: uno zip normale, `backups/pre-restore-<ts>.zip`, senza chiave (la chiave resta
     al suo posto); si tiene l'ultimo, scaricabile e cancellabile dalla scheda;
  2. `.restore/pending.json`, scritto in modo atomico: prova, revisione, voci da scambiare, cartella dati reale;
  3. risposta 202. Poi il frontend chiama `POST …/restart`, che manda SIGTERM al processo del server (al master di
     uvicorn se ci sono più worker): spegnimento ordinato, codice 0.
- **All'avvio**, `apply_pending_restore()` (idempotente, solo libreria standard):
  1. lock esclusivo `.restore/restore.lock`: i worker si danno il turno;
  2. se un altro server tiene la cartella dati (il lock condiviso `.restore/running.lock`, che ogni processo prende
     dopo questo passo) non tocca niente e scrive l'errore;
  3. giornale `journal.json`: per `sqlite/`, `custom-uploads/`, `broker_reports/` e `scenario_catalog/` rinomina la
     cartella attuale in `.restore/previous/<ts>/`, poi porta al suo posto quella della prova; `fsync` delle cartelle;
     un'interruzione a metà riprende dallo stesso punto;
  4. `secrets/`, `logs/` e `scheduler_state.json` non si scambiano mai.
- **Dopo il DB**, `commit_restore()`: esito in `.restore/last-result.json`, `previous/` cancellata. Se il primo avvio
  dopo lo scambio muore prima (una migrazione che fallisce esce con `sys.exit(1)`, `main.py:213`, `:217`), l'avvio
  seguente rimette `previous/` al suo posto, sposta i dati ripristinati in `.restore/failed/` e scrive «ripristino
  annullato», con il motivo.
- **Solo rinomine** sullo stesso volume: istantanee anche con molti GB, quindi nessun problema di healthcheck. La
  cartella dati intera non si può scambiare: in Docker è un punto di mount, e `rename` su un mount fallisce (`EBUSY`).
- **Senza supervisore** (decisione 8): l'app esce comunque, perché non può sapere se qualcuno la riavvierà. La UI
  aspetta `/system/ready`; dopo un minuto dice «avvia di nuovo LibreFolio». Il ripristino in attesa parte al prossimo
  avvio, comunque lo si lanci, e prima del riavvio si può annullare.
- **CLI a server spento**: prova, conferma a terminale, backup automatico e scambio subito, senza riavvio.

### 3.5 Segreti, password e chiave d'istanza (nodo 1)

**Cosa c'è da proteggere.** `secrets/` contiene solo `instance.key` (verificato); il segreto JWT non si salva mai
(scelta del fondatore). Ma il DB stesso è un dato finanziario personale: la password serve anche senza segreti dei
plugin.

- **Password → cifratura dell'intero archivio**: scrypt (N = 2^17, r = 8, p = 1, sale casuale; parametri
  nell'intestazione, con limiti massimi accettati alla lettura) → chiave di 32 byte → AES-256-GCM a blocchi
  (costruzione STREAM: prefisso casuale del nonce, contatore, flag dell'ultimo blocco, così troncamenti e riordini si
  vedono). **Mai HKDF da una password** (nota H-3). Libreria: `cryptography`, già nella finestra per X; scrypt anche da
  `hashlib`. **Nessuna dipendenza nuova.**
- **La chiave entra nell'archivio solo se** c'è la password **e** la chiave è il file generato
  (`instance_key_status().source == "generated"`). Una chiave configurata (`LIBREFOLIO_INSTANCE_KEY(_FILE)`, per
  esempio dal pannello del cloud) non si esporta mai: la custodisce chi la configura. Il manifest dice sempre
  `included` e il valore di controllo.
- **Mai una chiave derivata dall'istanza per un backup scaricabile**: chi ripristina altrove non l'avrebbe, e un
  archivio cifrato con una chiave derivata non deve contenere `secrets/` (H-3, nota 2).
- **Al ripristino l'istanza tiene la sua chiave** (H-3, nota 1: una chiave per istanza); `secrets/` non si scambia.
  - Archivio con la chiave, diversa da quella dell'istanza: i segreti dei plugin si ricifrano sulla copia dalla vecchia
    alla nuova chiave (funzione di X sul file della copia, derivazione da un materiale esplicito di H).
  - Archivio senza chiave, e chiave diversa: i cifrati restano; X li mostra «impostato ma illeggibile, reinseriscilo»
    (la sua misura 4); il report dice quanti sono.
  - In tutti e due i casi B riscrive nella copia il valore di controllo H-3 con la chiave dell'istanza, così
    `derive_key` non rifiuta.
- **Scompattare a mano** un archivio cifrato: `dev.py backup decrypt` (c'è anche nell'immagine) dà lo zip con
  `secrets/instance.key`; l'istanza nuova usa quella chiave. È un trasloco: la vecchia istanza sparisce.
- **Da chiedere a H** (`instance_key.py`, attraverso il coordinatore): `key_check_value()` e
  `key_check_value_from(material)` (lo stesso valore di H-3); `export_generated_key()`, eccezione documentata al
  «i consumatori non vedono la chiave», solo per il backup; `derive_key_from(material, purpose, length)`, per
  ricifrare. Nessuno scopo nuovo di `derive_key`.
- **Da chiedere a X** (CP10): `rekey_plugin_secrets(conn, old_subkey, new_subkey)` e
  `count_unreadable_secrets(conn, subkey)` su una connessione `sqlite3` della copia; dove vive il valore di controllo
  H-3 (proposta: con i cifrati, nella 007).
- Finché X non ha segreti nel DB il passo «ricifra» è vuoto, e il resto funziona.

### 3.6 Sessioni dopo un ripristino

- Il riavvio rigenera il segreto JWT quando non è configurato: tutte le sessioni finiscono.
- Con `JWT_SECRET` configurato sopravvivrebbero, e il `sub` di un cookie potrebbe indicare **un'altra persona** nei dati
  ripristinati. Cura: nella copia, `users.session_version = max(massimo attuale, massimo del backup) + 1` per tutti, e
  ogni cookie di prima viene rifiutato (`auth.py:125`).
- La UI lo dice prima della conferma: dopo il ripristino si entra con un account dei dati ripristinati.

### 3.7 Dove vive il codice (nodo 2)

- **Pacchetto nuovo** `backend/app/services/platform/instance_backup/` (C1, nomi brevi per tema): `paths.py`,
  `manifest.py`, `snapshot.py`, `archive.py`, `envelope.py`, `jobs.py`, `staging.py`, `apply.py` (solo libreria
  standard, perché lo importa anche l'avviatore Docker), `restart.py`, `totals.py` (gira in un processo separato).
- **`config/backup.py`** (D2): le variabili del §3.16, i segreti con `env_secret()`; righe commentate nella mia
  sezione di `.env.example`.
- **Schemi** in `schemas/backup.py` (nuovo).
- **`backup_service.py`** (H, D13: decide B): proposta di rinominarlo `series_export.py` con una rinomina pura, dopo E1
  di W (2 import e 2 file di test, più doc e wiki). Facoltativa (D-B8). Non lo tocco prima del via.
- **`api/v1/backup.py`, divisione C2** in due commit, dopo E1 di W, oppure con W che porta E1 sul file nuovo (decide il
  coordinatore):
  1. rinomina pura in `api/v1/backup/__init__.py` (R100);
  2. taglio: `exports.py` (gli export per serie, invariati: prezzi e cambi di X, eventi di W) e `instance.py` (i 4
     segnaposto, invariati). `__init__.py` compone `backup_router` (il nome che usa `router.py:43`), con l'ordine delle
     rotte di oggi; `api schema` identico.

  Poi, nel lotto B1, cambia solo `instance.py` (§3.9).

### 3.8 L'aggancio all'avvio (nodo 3): cosa chiedo a H per CP2b

- **Due passi negli `STARTUP_STEPS`**, chiamati con una lambda risolta al momento:
  1. `restore.apply` → `instance_backup.apply.apply_pending_restore()`: **il primo passo dopo il log d'avvio**, prima di
     ogni passo che legge o scrive `<DATA_DIR>` (oggi prima di `ensure_data_dirs()`, `main.py:271`, e quindi prima di
     scenari, avatar e DB). Sincrono e veloce: solo rinomine. Un errore che lascia la cartella a metà ferma l'avvio con
     un messaggio chiaro; un errore prima di toccare qualcosa lascia avviare.
  2. `restore.commit` → `instance_backup.apply.commit_restore()`: dopo DB, fix post-migrazione e impostazioni globali
     (oggi dopo `main.py:293`).
- **Nessun passo di spegnimento**: il riavvio è un SIGTERM al processo del server, quindi passa dallo spegnimento di Z,
  con il suo tempo massimo (decisione 35).
- **Se CP2b tarda**: le stesse due righe in `main.py` scritte da H, come la riga dell'audit in CP3; oppure il
  ripristino in linea aspetta. B1, B2 e il ripristino da CLI a server spento non ne hanno bisogno.
- **Nell'immagine con Litestream** l'avviatore chiama lo stesso `apply_pending_restore()` prima di Litestream (§3.13);
  il passo del lifespan allora non trova niente e fa solo `commit_restore()`.

### 3.9 API

| Metodo e percorso | Chi | Cosa |
|---|---|---|
| `POST /backup/instance` | admin | avvia un job di backup (`password` facoltativa, `SecretStr`; `include_key`) → 202 `{job_id}` |
| `GET /backup/instance/jobs/{id}` | admin | stato, avanzamento, dimensione, nome del file, codice d'errore |
| `GET /backup/instance/jobs/{id}/file` | admin | il file, con `Content-Disposition` |
| `GET` e `DELETE /backup/instance/pre-restore` | admin | il backup automatico fatto prima dell'ultimo ripristino |
| `PUT /backup/restore/upload` | admin | corpo grezzo, con il limite di dimensione → `{upload_id, kind}` |
| `POST /backup/restore/stage` | admin | `{upload_id, password?}` → job della prova |
| `GET` e `DELETE /backup/restore/stage/{id}` | admin | il report; annulla e pulisce |
| `POST /backup/restore/stage/{id}/confirm` | admin | backup automatico e ripristino in attesa → 202 |
| `POST /backup/restore/restart` | admin | uscita ordinata per il riavvio |
| `GET /backup/restore/status`, `DELETE /backup/restore/pending` | admin | in attesa e ultimo esito; annulla prima del riavvio |
| `POST /backup/panel/jobs`, `GET …/{id}`, `GET …/{id}/file` | token del pannello (`Authorization: Bearer`) | come i job dell'admin, senza chiave e senza password; 404 se il token non è impostato |

- **Errori con un `code` stabile** in `detail` (`{"code": …, "message": …}`, minuscolo come il resto dell'API, per esempio
  `portfolio_wac_broker_forbidden`), tradotto nella UI come i rifiuti di K2a di W. In B1: `backup_busy` 409,
  `backup_job_not_found` 404, `backup_job_not_ready` 409, `backup_job_running` 409; nello stato del job,
  `backup_no_space`, `backup_failed`, `backup_interrupted`. Previsti: `backup_too_large` 413, `backup_invalid_archive`
  400, `backup_wrong_password` 400, `backup_newer_than_app` 409, `backup_unknown_revision` 409,
  `backup_checksum_mismatch` 400, `backup_integrity_failed` 400, `restore_already_pending` 409, `restore_stage_expired`
  410. Mai percorsi o messaggi interni nella risposta.
- **Spariscono i 4 segnaposto** (`POST /backup/export`, `POST /backup/restore`, `GET /backup/formats`,
  `GET /backup/status`): nessun consumatore; `test_backup_api.py` lo riscrivo.
- **Blocco dell'istanza** (H CP6, decisione 12): permessi i tre endpoint di backup dell'admin, il backup automatico e
  quelli del pannello; tutto il ripristino bloccato. La pagina di blocco dell'admin usa il mio componente di
  scaricamento (§3.11).

### 3.10 CLI (`dev.py backup`, `scripts/backup_cli.py`)

- `create [--output F] [--password-file F | --password-stdin] [--include-key]`, `inspect FILE`,
  `restore FILE [--dry-run] [--yes]`, `pending [--cancel]`, `decrypt FILE -o OUT.zip` (B4), `apply-pending` (per
  l'avviatore).
- **La password mai come argomento**, che si vede in `ps` e nella cronologia: file, stdin o `getpass`.
- `restore` **a server spento** applica subito; **a server acceso** (lock condiviso preso) mette il ripristino in
  attesa e chiede il riavvio.
- **In Docker** funziona con `docker compose exec`: il backend è nell'immagine. Rischio: `exec` gira come root (32-3,
  curato da H in CP7a) e lascerebbe file di root nella cartella dati; la CLI crea i suoi file con il proprietario della
  cartella dati, o rifiuta.
- **In `dev.py`**: un import, una chiamata e una riga dell'aiuto (file condiviso). Test in `utils dev-cli-image`.

### 3.11 Scheda Backup (UI)

- **Feature nuova** `frontend/src/lib/features/backup/`: `BackupTab.svelte` (il corpo), `BackupDownloadCard.svelte`
  (riusabile dalla pagina di blocco di H), `RestoreCard.svelte`, `RestoreReportModal.svelte` (con la conferma
  scritta), `RestartOverlay.svelte` (aspetta `/system/ready`, poi il login), `backupApi.ts` (caricamento con
  avanzamento; scaricamento con `<a href>`), `restoreFlow.svelte.ts` (stato in rune).
- **Una riga nel registro di A**: `{id: 'backup', labelKey: 'backup.tab', icon: DatabaseBackup, order: 120, component:
  BackupTab, visible: (ctx) => ctx.isSuperuser}`, più la riga di `TODAY` e il `vi.mock` in `settingsTabs.test.ts`.
- **i18n**: sottosistema nuovo `lib/i18n/backup/` (prefisso `backup`), nelle 4 lingue.
- **File nuovi a zero**: solo utility `*-lf-*` (per esempio `bg-lf-warning-soft`, `border-lf-danger-line`,
  `text-lf-danger-on-soft`), nessuna palette né esadecimale, niente `!important`; `toneClasses.ts` quando entra il
  lotto A dei colori.
- **Dopo il riavvio**: l'esito dell'ultimo ripristino nella scheda, e un avviso per l'admin nel registro di H
  (`instanceNotices`), senza toccare il layout.
- `data-testid` ovunque, `data-busy` sui contenitori che caricano, eventi `notify()` (`backup.created`,
  `backup.restore.staged`, `backup.restore.confirmed`).
- **Galleria**: la scheda e il report della prova (desktop e mobile, 4 lingue, 2 temi) in `gallery.spec.ts` di G,
  attraverso il coordinatore.

### 3.12 Guida «Porta il tuo LibreFolio a casa» (`docs-writer`)

- Pagina admin nuova, `admin/backup_restore.en.md` («💾 Backup, restore and moving your instance»), solo in inglese:
  - backup dalla UI e dalla CLI; cosa contiene; password e chiave; dove tenerlo;
  - ripristino dalla UI: prova, report, conferma, riavvio, sessioni, annullamento, ritorno indietro;
  - **portarlo a casa**: scompatti in `./LibreFolio-data`, `docker compose up` con un'immagine uguale o più nuova, le
    migrazioni partono da sole; un archivio cifrato prima passa da `dev.py backup decrypt` (anche con
    `docker run --rm`); vale anche dal self-hosted al cloud, dalla UI del cloud;
  - Litestream (rimando a `docker_advanced`), limite di caricamento, spazio libero;
  - supervisori: Docker `unless-stopped`, systemd `Restart=always`, Fly.
- **Aggiornamenti**: `filesystem.en.md` «💾 Backup» rimanda alla pagina (file di H in CP3: col via del coordinatore),
  `cli_tools.en.md` (`dev.py backup`), `docker_advanced.en.md` (Litestream, `stop_grace_period`, `kill_timeout`),
  `configuration.en.md` (variabili); pagina per sviluppatori `developer/backend/backup.md` (formato, giornale,
  aggancio all'avvio).
- Navigazione e CHANGELOG: testo proposto nell'handoff.

### 3.13 Litestream (F25), dopo il CP7a di H

- **Immagine**: Litestream v0.5.17 (31/08/2026; tarball `linux-x86_64` e `linux-arm64`, `checksums.txt`), scaricato in
  uno stadio a parte per `TARGETARCH`, `sha256` verificato, copiato in `/usr/local/bin`. Spento di default.
- **Avviatore** `scripts/docker/start_server.py`, nuovo `CMD` al posto di `uvicorn …`. L'`ENTRYPOINT` resta generico,
  così `docker run … python dev.py …` non passa dall'avviatore.
  1. `apply_pending_restore()`;
  2. Litestream spento → `exec uvicorn …`, come oggi;
  3. acceso → configurazione generata da `config/backup.py` in un file temporaneo 0600, senza segreti dentro
     (espansione `${VAR}` di Litestream, con i segreti risolti nell'ambiente, `_FILE` compresi) →
     `litestream restore -if-db-not-exists -if-replica-exists` → `exec litestream replicate -config … -exec "uvicorn …"`
     (Litestream esce quando esce uvicorn).
- **Destinazioni**: S3 e compatibili (MinIO, Backblaze, Tigris), SFTP, cartella (`file://`, un NAS montato); SSE-C
  (`sse-customer-key`, da v0.5.6).
- **Spegnimento**: `shutdown-sync-timeout` breve (5 s) nella configurazione generata; `stop_grace_period: 30s` nei due
  compose; nella doc `kill_timeout` di Fly (default 5 s) a 30.
- **Ripristino con Litestream**: lo scambio avviene prima di Litestream, e `sqlite/.app.db-litestream` esce con
  `sqlite/`, quindi Litestream riparte da zero. **Da provare** (spike del lotto): che la replica remota non tenga la
  vecchia linea come «più recente» (la v0.5 ordina per TXID, e la doc dice solo «`litestream reset`, poi uno snapshot
  nuovo»). Se le mescola: replica in un sotto-percorso nuovo dopo un ripristino, oppure un comando documentato che la
  azzera.
- **Healthcheck**: con il ripristino automatico dalla replica l'avvio può durare minuti; `start_period` più lungo con
  Litestream acceso (doc), in accordo con `/system/ready` del CP7a di H.

### 3.14 Scaricamento per il pannello (decisione 7)

- `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN(_FILE)`; assente → endpoint 404. Il token solo nell'header
  `Authorization: Bearer` (mai nell'URL, finirebbe nei log), confronto a tempo costante, mai nei log.
- Stesso job dell'admin, senza chiave (il pannello la conosce già: la imposta lui) e senza password (il pannello
  cifra a riposo).

### 3.15 M-1, immagini anche arm64 (facoltativo)

- `release.yml`: `platforms: linux/amd64,linux/arm64` nei due `build-push-action` (QEMU e Buildx già impostati);
  Litestream per `TARGETARCH`; il contratto in `release-image-contract`.
- Costo: la build sotto QEMU, con i pacchetti compilati da sorgente nello stadio `pybuilder`; da misurare con una run
  manuale. File condiviso (H l'ha toccato in CP5a): decide il coordinatore.

### 3.16 Variabili d'ambiente (sezione «Backup and Litestream»)

Ogni default lascia il self-hosted com'è; ogni segreto accetta `_FILE`.

| Variabile | Default | Cosa |
|---|---|---|
| `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` | `0` = senza limite (500 nel profilo gestito, quando H porta i default del profilo) | archivio caricabile per il ripristino |
| `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN(_FILE)` | vuota = spento | token del pannello (decisione 7) |
| `LIBREFOLIO_LITESTREAM_REPLICA_URL` | vuota = Litestream spento | `s3://…`, `sftp://…`, `file:///…` |
| `LIBREFOLIO_LITESTREAM_ACCESS_KEY_ID`, `…_SECRET_ACCESS_KEY(_FILE)` | vuote | S3 |
| `LIBREFOLIO_LITESTREAM_ENDPOINT`, `…_REGION` | vuote | S3 compatibile |
| `LIBREFOLIO_LITESTREAM_SSE_C_KEY(_FILE)` | vuota | chiave SSE-C (base64, 256 bit) |
| `LIBREFOLIO_LITESTREAM_SFTP_PASSWORD(_FILE)`, `…_SFTP_KEY_FILE`, `…_SFTP_HOST_KEY` | vuote | SFTP |
| `LIBREFOLIO_LITESTREAM_RESTORE_ON_START` | `1`, con Litestream acceso | ripristino automatico se il DB manca |
| `LIBREFOLIO_LITESTREAM_CONFIG` | vuota | un `litestream.yml` proprio, che vince su tutto (utenti esperti) |

## 4. Decisioni (proposta in grassetto)

**Decisioni del §10 rilette sul codice**:

- **6**: confermata, con il formato da scegliere in D-B1.
- **7**: confermata (§3.14): token separato, spento se assente, mai la chiave.
- **8**: confermata con una precisazione (§3.4): l'app esce sempre dopo la conferma; Docker la riavvia da solo; senza
  supervisore la UI chiede di avviarla di nuovo; il ripristino in attesa vale per qualunque avvio e si può annullare.
- **9**: confermata (§2, punto 7). La guida consiglia Litestream per il DB più zip periodici per i file (CLI in un cron,
  o gli zip del pannello).

**Nuove**:

1. **D-B1, formato della password**:
   - **(a) busta `.lfbk` con `cryptography`**: nessuna dipendenza nuova, scrypt; si apre con LibreFolio (UI, o CLI
     anche nell'immagine);
   - (b) zip AES con `pyzipper`: dipendenza nuova, più `pycryptodomex`; si apre con 7-Zip o Keka, ma non con Esplora
     risorse né con il Finder, e la derivazione è debole (PBKDF2-SHA1 ×1000);
   - (c) nessuna cifratura, solo un avviso forte.
2. **D-B2, la chiave d'istanza** (§3.5): **solo con password e solo se generata; al ripristino la chiave dell'istanza
   resta e i segreti si ricifrano**. Alternativa: adottare la chiave del backup (più semplice, ma due istanze con la
   stessa chiave, e impossibile quando la chiave è configurata).
3. **D-B3, le sessioni**: **tutte chiuse dopo un ripristino** (§3.6).
   **Deciso (40, 15/10)**: `JWT_SECRET` non cambia e non va nel backup; il DB ripristinato porta l'ora del ripristino:
   al commit `session_version = max(ora in ms, massimo del DB ripristinato + 1, massimo del DB di prima + 1)` per ogni
   account (forma (a) e `max`, decisione notturna del 16/10, da rivedere col developer); l'anteprima elenca gli admin
   del backup, e senza admin il ripristino è bloccato.
4. **D-B4, il backup automatico**: **uno zip in `backups/` (l'ultimo), più il ritorno indietro automatico se il primo
   avvio fallisce**. Alternativa: tenere `previous/` come backup (nessuno spazio in più, ma una cartella invece di un
   file scaricabile).
   **Deciso (41, 15/10)**: la copia fatta prima del ripristino serve solo a tornare indietro: è `.restore/previous/`,
   cancellata dopo un primo avvio riuscito; se il primo avvio fallisce, LibreFolio rimette da solo i dati di prima. Non
   resta scaricabile dalla scheda.
5. **D-B5, archivi senza manifest** (copie a mano, quindi le 1.2): **accettati**, con un avviso.
   **Respinta (42, 15/10)**: solo backup di LibreFolio, con `manifest.json`.
6. **D-B6, il limite di caricamento**: **una variabile d'ambiente**, perché nel cloud il cliente è admin e il limite lo
   decide l'hoster; `0` = senza limite nel self-hosted. Non un'impostazione globale.
   **Approvata (43, 15/10)**: `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`, `0` di default, 500 nel profilo gestito.
7. **D-B7, percorsi dell'API** (§3.9), con la rimozione dei 4 segnaposto.
8. **D-B8, `backup_service.py` → `series_export.py`**: **sì, rinomina pura dopo E1**; oppure lasciarlo.
9. **D-B9, la prova «stessi totali»**: **un sottoprocesso su una cartella temporanea**, senza un secondo server (regola
   4 dei test). Alternativa: un secondo server su una porta effimera, con un'eccezione scritta alla regola.
10. **D-B10, M-1**: **nella 1.3 se la build sotto QEMU resta ragionevole**; altrimenti dopo.

## 5. Superfici esatte

**Mie** (file nuovi, o di B dopo il CP7a):

- Backend: `services/platform/instance_backup/**`, `config/backup.py`, `schemas/backup.py`,
  `api/v1/backup/instance.py` (dopo B0), `scripts/backup_cli.py`, `scripts/docker/start_server.py` (B7).
- Test: `test_services/test_backup_*.py`, `test_api/test_backup_api.py` (riscritto),
  `test_e2e/test_backup_roundtrip.py`, `test_utilities/test_backup_cli.py`, `test_utilities/test_docker_launcher.py`.
- Frontend: `lib/features/backup/**`, `lib/i18n/backup/**`, `e2e/settings/backup.spec.ts`.
- Doc: `admin/backup_restore.en.md`, `developer/backend/backup.md`.
- Docker, dopo CP7a: `Dockerfile`, `entrypoint.sh`, `docker-compose.yml`, `docker-compose.prod.yml`, `.dockerignore`
  se serve.
- `.env.example`, la sezione «Backup and Litestream» (`:141-144`); la sezione B del backlog.

**Fuori perimetro: file, righe e motivo** (decidi tu quando e chi):

| File | Righe | Proprietario | Motivo |
|---|---|---|---|
| lifecycle di CP2b, o `backend/app/main.py` | prima di `:271`; dopo `:293` | H | i passi `restore.apply` e `restore.commit` (§3.8) |
| `backend/app/config/__init__.py` | `:357-364` (radici controllate), `:375-388` (`managed_paths`) | H | `backups/` e `.restore/` fra i percorsi dell'isolamento prod/test |
| `backend/app/services/platform/instance_key.py` | funzioni nuove | H | `key_check_value*`, `export_generated_key`, `derive_key_from` (§3.5), H-3 |
| archivio delle impostazioni dei plugin (CP10, 007) | funzioni nuove | X | ricifrare e contare i segreti su una copia; posto del valore di controllo H-3 |
| `backend/app/api/v1/backup.py` | tutto (B0) | X e W (export), B (segnaposto) | divisione C2 (§3.7) |
| `backend/app/services/platform/backup_service.py` | rinomina (D-B8) | X e W | nome chiaro |
| `frontend/src/lib/features/settings/settingsTabs.ts` | un import, una riga in `:39-45` | A | la scheda |
| `frontend/src/lib/features/settings/settingsTabs.test.ts` | `bodies`, `vi.mock`, `TODAY` (`:50-82`) | A | la riga della scheda nel test |
| `backend/app/api/v1/settings.py` | `:67`, solo l'import di `require_admin` | A | controllo admin; se A lo sposta, seguo |
| `dev.py` | registrazione dei gruppi (`:2527-2531`) e aiuto (`:2405-2406`) | coordinatore | il gruppo `backup` |
| `scripts/test_runner/_backend_api.py`, `_backend_services.py`, `_backend_utils.py` | voci mie, in aggiunta | coordinatore | catalogo |
| `scripts/test_runner/_frontend_utility.py` | liste Vitest (`:294-303`) e una voce E2E | coordinatore (file seguito dal programma colori) | i test della scheda |
| `frontend/e2e/gallery.spec.ts` | uno scatto nella categoria `settings` | G | la schermata nuova |
| `mkdocs_src/docs/admin/filesystem.en.md` | sezione «💾 Backup» | H (CP3) | rimando alla guida |
| `mkdocs_src/mkdocs.yml` | nav «🧹 Maintenance & Operations» (`:965-967`) | coordinatore | pagina nuova |
| `.github/workflows/release.yml` | `:357-373` | coordinatore o H | M-1 |
| `.github/instructions/backend.instructions.md` | mappa di `platform/` | condiviso | `instance_backup/` |
| devWiki `features/F-073.md`, `entities/backup-router.md`, `domains/infrastructure.md` | Source files e stato | C6 o `project-historian` | percorsi e stato |
| CP6 di H (permessi del blocco, pagina di blocco) | nuovi | H | endpoint di backup permessi; componente di scaricamento |

**Condivise**: catalogo del runner, i18n (solo il sottosistema `backup`), client generato (`api sync`), CHANGELOG e
navigazione (testo proposto). **Migrazioni: nessuna.**

## 6. Previsione dei conflitti

| Con | Dove | Gestione |
|---|---|---|
| H | lifecycle (CP2b), `config/__init__.py`, `instance_key.py`, file Docker (CP7a), healthcheck, CP6 | richieste puntuali (§5); file Docker solo dopo CP7a; base aggiornata con CP5a prima di B2 |
| A | `settingsTabs.ts` e il suo test; `require_admin`; `session_version` | una riga; nella copia il bump usa la colonna di A4b senza cambiarne il significato |
| X | `backup.py` e `backup_service.py` (export di prezzi e cambi); segreti dei plugin e H-3 | B0 come rinomina e taglio senza cambi; contratto di ricifratura |
| W | `backup.py` (export degli eventi, E1) | B0 dopo E1, oppure E1 sul file nuovo |
| J | totali di controllo | solo lettura di una funzione del motore |
| Z | ordine dei passi d'avvio, spegnimento | il passo di B è il primo; il riavvio usa lo spegnimento di Z |
| E, Y | — | l'SMTP non entra mai nei backup |
| Programma colori | file frontend nuovi (cricchetto a zero), `_frontend_utility.py`, `gallery.spec.ts`; `app.css` mai | solo ruoli `*-lf-*`; i file seguiti passano dal coordinatore |

## 7. Lotti e checkpoint (ognuno con il suo FROZEN)

| Lotto | Contenuto | Dipende da | Stato (19/10) |
|---|---|---|---|
| **B0** | divisione C2 di `backup.py` (rinomina, poi taglio; `api schema` identico, rotte identiche); facoltativa la rinomina di `backup_service.py` | via del coordinatore; E1 di W | ✅ in dev `629d63306` (15/10 19:06) |
| **B1** | backup dell'istanza, backend e CLI, zip senza cifratura: `config/backup.py`, `paths`, `manifest`, `snapshot`, `archive`, `jobs`, endpoint dei job, `dev.py backup create|inspect`, `.env.example` | B0 per gli endpoint (servizio e CLI no) | ✅ in dev `629d63306` (15/10 19:06), con B1-fix |
| **B2** | caricamento e prova su copia: estrazione con i controlli, decisione sulla revisione, migrazione della copia, controlli, report, archivi a mano, `restore --dry-run` | base con CP5a | ✅ B2a e B2b, in dev `5441b96ed` (16/10 02:48) |
| **B3** | ripristino definitivo: conferma, backup automatico, `apply.py` (lock, giornale, scambio, ritorno indietro), `restart.py`, stato e annullamento, sessioni, `restore` a server spento; `security-review` di metà percorso | CP2b di H, o le due righe | ✅ in dev `0cd910a7e` (16/10 21:35) |
| **B4** | password e chiave: `envelope.py`, regola della chiave, `decrypt`, contratto H-3; la ricifratura quando c'è il CP10 di X (altrimenti B4b) | `cryptography` | ✅ in dev `339a59142` (17/10 03:28); B4b in dev `c7dd3934a` (17/10 04:50) |
| **B5** | scheda Backup: feature, riga nel registro, i18n, Vitest, E2E, galleria, `api sync` | B1-B3 (B4 per il campo della password); `npm ci`; via per la riga di A | ✅ B5a con `629d63306`, B5b e B5c con `0cd910a7e`, lo scatto `settings/backup-ready` con `ab2ddf86e`; ⏳ lo scatto di B5b, passato ai colori (17/10) |
| **B6** | guida e doc | con B5, o subito dopo | ✅ B6a con `629d63306`, B6a-bis con `0cd910a7e`, la doc dell'archivio sicuro con B4; ⏳ la doc di Docker e Litestream (B7d) |
| **B7** | Litestream: immagine, avviatore, variabili, compose, doc, prove Docker, spike della replica | CP7a di H; daemon Docker acceso | 🧊 analisi ✅ (17/10 08:55); lo spike B7a approvato ma non girato (Docker spento); B7b–B7d aspettano le risposte D1–D10 del developer |
| **B8** | token del pannello | B1; può entrare in B3 | ✅ in dev `56d3d3182` (15/10 20:23) |
| **B9** | M-1, arm64 | facoltativo | ⏳ non iniziato |
| **BZ** | revisione di sicurezza finale e handoff | tutto | parte 1 ✅ (17/10, F1–F5 → B-35…B-39, i record in dev `279c1bc1c`); parte 2 dopo B7 e B9 |

La colonna «Stato» è del 19/10, con ogni merge verificato in `dev_release2`. Le voci B-n hanno il loro stato nella
sezione B del backlog; il lavoro di ogni lotto è nel §13.

Percorso minimo per il cloud: B1 → B2 → B3 → B5 (più B4 se approvata) → B7.

## 8. Come si prova

**Principi**

- Il runner possiede il backend della corsia: nessun test conferma un riavvio sulla corsia, e nessuno lascia
  `pending.json` nella sua cartella dati (fixture con la pulizia nel `finally`).
- Scambio all'avvio, giornale e ritorno indietro: funzioni chiamate su cartelle temporanee, con un'interruzione
  simulata a ogni passo.
- Uscita per il riavvio: `restart.py` con segnale e bersaglio iniettati (test unitari), mai un vero `kill` sulla
  corsia. La prova vera è quella Docker.
- **«Stessi totali»** (D-B9; **aggiornato il 16/10**, `e2e backup-roundtrip`): una sorgente popolata in `tmp_path`
  (`populate_mock_data --force` in un processo figlio in modalità test), archiviata con `jobs.run_backup` →
  `backup_cli.py restore ARCHIVE --yes` su un'istanza vuota → «un avvio» in un processo nuovo (i passi da
  `pending-restore` a `restore-commit`) → righe, file e report del motore ufficiale per ogni account con un broker,
  sorgente e destinazione calcolati uno dopo l'altro. Nessun secondo server, la corsia mai letta né scritta.
- **Backup a una revisione precedente** (al posto del «backup della 1.2», decisione 42): un archivio di LibreFolio il
  cui DB sta a `005_accounts_invites`, costruito nel test con le migrazioni vere → prova (aggiornamento della copia) →
  conferma → avvio → al commit, alla head, con le righe del report. Più il rifiuto di una revisione sconosciuta o più
  nuova.
- **Il passaggio dalla 1.2** (decisione 42): è l'aggiornamento sul posto, non un ripristino. Lo coprono i test delle
  migrazioni e delle correzioni dopo le migrazioni (`db post-migration`, `test_migration_005_accounts`) e il cancello
  d'aggiornamento della release, non un cancello di B.
- **Docker** (B7, daemon acceso): Litestream spento (avvio come oggi) e acceso, con una replica `file://` su un volume:
  replica, `docker stop` entro il limite (misurato), DB cancellato → ripristino automatico all'avvio, ripristino dalla
  UI con Litestream acceso, spike della linea della replica. S3 locale (MinIO) facoltativo.

**Selettori** (preambolo
`PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6187 --data-dir /tmp/librefolio-r13-b …`)

- `services backup-manifest`, `backup-archive`, `backup-snapshot`, `backup-staging`, `backup-apply`,
  `backup-envelope` (B4), `backup-launcher` (B7): `pure`, o `write-scoped` su `tmp_path`.
- `api backup` (riscritto: admin, job, file, caricamento e limiti, prova, conferma senza riavvio, annullamento, stato,
  token del pannello); `api backup-export-extras` e `api asset-prices-export` (regressione degli export).
- `e2e backup-roundtrip`.
- `utils dev-cli-image`, `utils release-image-contract`, `utils backup-cli` (nuovo).
- `services config-package`, `services config-env-example`, `db post-migration` (regressione).
- Frontend: `front-utility core-unit` (registro delle schede), `front-utility component-unit` (i test della scheda),
  E2E `front-utility backup` (scaricamento, caricamento, report, annullamento; la chiamata di riavvio intercettata con
  `page.route` e il ripristino in attesa tolto nell'`afterEach`), galleria (G).
- Statici: `lint`, `lint --dead-code`, `api sync`, `front check`, `theme-roles.mjs --check`, `i18n check`,
  `mkdocs build`, `check-links`, `check_source_paths.py`.
- **Base prima di B1** (fuori dalla finestra della galleria): `npm ci` dopo l'errore confermato e il via, `front build
  --debug` e `mkdocs build` una volta (limite dei 300 s del server condiviso), poi `api backup`,
  `api backup-export-extras`, `api asset-prices-export`, `services config-package`, `services config-env-example`.
  `all-backend` a fine lotto.

## 9. Rischi

1. **Scambio di più cartelle**: non è atomico come insieme. Giornale, ripresa e ritorno indietro, provati con le
   interruzioni.
2. **Supervisori diversi** (Docker, Fly, systemd, nessuno): documentati; la UI aspetta `/system/ready` e poi avvisa.
3. **Più worker**: il SIGTERM va al master; lo scambio all'avvio si serializza con il lock.
4. **Spazio su disco**: una prova chiede circa il doppio dell'archivio, più il backup automatico; controllo prima,
   errore chiaro (507).
5. **Zip ostili** (zip slip, link, bombe, nomi doppi): elenco d'inclusione, limiti, revisione di sicurezza.
6. **Un ripristino da un'altra istanza** cambia credenziali e chiude le sessioni: avvisi nella UI e nella guida.
7. **Litestream dopo un ripristino**: la linea della replica (spike in B7).
8. **Busta cifrata fatta in casa**: solo primitive di `cryptography`, costruzione nota, vettori di prova, revisione di
   sicurezza.
9. **Totali in un sottoprocesso**: lenti o fragili; i conteggi sono il controllo che decide, i totali informano.
10. **Corsia di test**: un `pending.json` dimenticato scambierebbe i dati della corsia al prossimo avvio. Pulizia nelle
    fixture; il segnaposto porta il percorso reale della cartella dati, che `apply` verifica.
11. **`docker exec` come root** prima della cura di H (32-3): file di root nella cartella dati.
12. **Dimensione del lavoro**: grande (F01) più medio (F25); B1-B3 sono il cuore P0.
13. **Tempi di X (CP10) e H (H-3)**: senza le loro funzioni, un ripristino senza la chiave giusta lascia i segreti
    «da reinserire» (misura 4 di X): accettabile finché arrivano.

## 10. Definizione di fatto

- **Accettazione del fondatore**, automatizzata: backup di un'istanza popolata → ripristino su un'istanza vuota →
  stessi totali; un backup di LibreFolio a una revisione precedente ripristinato sulla 1.3 con prova e conferma (al
  posto del «backup della 1.2», decisione 42); rifiuto di un backup più nuovo.
- **Cancelli del §9**: immagine con Litestream spento e acceso; `docker stop` entro il limite; revisione di sicurezza
  del backup. Il passaggio dalla 1.2 è l'aggiornamento sul posto (decisione 42): cancello d'aggiornamento della
  release, non di B.
- Per lotto: verdi mirati, `all-backend` = base + test nuovi, statici puliti, `api sync`, `front check` 0/0, gate dei
  colori puliti, `i18n check`, `mkdocs build` stretto e `check-links`, guardie `config-package` e
  `config-env-example`, `check_source_paths.py` non peggiora.
- Doc: guida admin, pagina per sviluppatori, `.env.example`; righe di backlog per i residui; testo di CHANGELOG e
  navigazione nell'handoff; porta 6187 libera; FROZEN.

## 11. Specialisti, dipendenze, runtime

- `test-author` (tutti i test), `docs-writer` (guida, pagina per sviluppatori, sezioni di `docker_advanced`,
  `cli_tools`, `configuration`), `security-review` (metà di B3, B4, finale).
- Skill all'avvio del codice: `lint-format`, `lint-format-frontend`, `testing-backend`, `testing-frontend`,
  `devpy-docker`, `devpy-i18n`, `theme-roles`; `test-triage` per un rosso non ovvio.
- **Python**: nessuna dipendenza nuova con D-B1 (a); `cryptography` dalla finestra di X (serve a B4). Con (b),
  `pyzipper`.
- **Docker** acceso per B7. **`npm ci`** per B5 e per i test che avviano il server condiviso (regola del §6), dopo
  l'errore confermato e il via.
- Corsia 6187, `/tmp/librefolio-r13-b`; mai `./dev.py` nudo, mai `--force`, una invocazione alla volta, mai `mkdocs
  serve`.

## 12. Righe di backlog (sezione B)

Scritte al checkpoint di B0 (15/10): B-1 (devWiki di F-073 e `domains/infrastructure`), B-2 (un commento di
`DataEditor.test.ts`, file di T), B-3 (la docstring di `backup_asset_prices` nell'OpenAPI, si corregge in B1). La linea
della replica di Litestream dopo un ripristino non è un residuo: è lo spike di B7.

## 13. Avanzamento

> **Come leggere questa sezione** (riordinata il 19/10): le sezioni vanno in ordine d'inizio, la più vecchia in
> alto; un checkpoint precede il merge che lo segue. Un'intestazione dice lo stato di quando è stata scritta; dove
> diceva un lavoro aperto («in corso», «bozza», «in attesa del via» o «del commit») porta l'esito. Lo stato di oggi
> dei lotti è nel §7, quello delle voci nella sezione B del backlog.

### Analisi ✅ (2026-10-15)

> Consegnata al coordinatore. Nessun file del repo modificato, nessun test lanciato.
>
> **Fuori pista**: l'app ha consegnato «piano approvato» senza testo. Sono rimasto FROZEN e ho chiesto l'autorizzazione
> alla lettera, come vuole la regola del §12 del piano generale (14/10).

### Via per B0 e B1 (coordinatore, 2026-10-15 alle 11:23)

> **Autorizzazione del developer, alla lettera** (15/10, ~11:08), inoltrata dal coordinatore: «riguardo b ed e sei tu
> il coordinatore, a meno che non devo qualcosa in particolare, e allora aggiornami, avviali tu.»
>
> - **Base**: worktree portato a `23f6578f3` con un avanzamento veloce (contiene i lotti A–D di R). Verificato: HEAD
>   `23f6578f3ee2ea8f26f55d672d0593c5c67d5c20`, ramo `e-alfy-b-backup-e-docker`, pulito.
> - **Autorizzati**: B0 (subito, prima di E1 di W: nessun ramo in attesa tocca `backup.py` o `backup_service.py`) e
>   B1 (backup dell'istanza, backend e CLI, zip senza cifratura). Le righe di `dev.py` e del catalogo del runner le
>   scrivo io, solo in aggiunta, e le elenco nell'handoff.
> - **Decisioni di coordinamento**: D-B7 sì (i percorsi del §3.9, senza i 4 segnaposto); D-B8 sì (rinomina pura
>   `backup_service.py` → `series_export.py`, in un commit a parte dentro B0); D-B9 sì (sottoprocesso su una cartella
>   temporanea); D-B10 dopo B7.
> - **Aspettano il developer** (punti 38–43 del file delle decisioni): D-B1…D-B6. B2 aspetta 42 e 43; B3 aspetta 40, 41
>   e il CP2b di H; B4 aspetta 38, 39 e la finestra delle dipendenze per `cryptography`.
> - **Note per B3, B4 e la revisione di sicurezza**:
>   - da E: un ripristino rianima i token monouso vivi del backup (inviti, reset). Nella copia, oltre a
>     `session_version`, revocare i token vivi di `account_tokens`, oppure accettarli e dirlo nel report;
>   - da H CP6 (non ancora in base): il backup completo e la sua disponibilità entrano in `ALLOWED_WHEN_BLOCKED` e in
>     `InstanceBlockResponse`, una riga ciascuno, con il test che fissa l'elenco, quando CP6 è in base;
>   - da X CP10: `plugin_settings/crypto.py` darà `rekey_plugin_secrets(conn, old_subkey, new_subkey) -> RekeyReport`,
>     `count_unreadable_secrets(conn, subkey)` (sincrone, su una `sqlite3.Connection` della copia, dentro un
>     `SAVEPOINT`, dopo l'upgrade alla head) e `settings_subkey(instance_key=None)`. Il valore di controllo H-3 è il
>     `key_id` di ogni riga cifrata: al ripristino non si riscrive niente, e la richiesta `key_check_value*` cade;
>   - le richieste ad H (`derive_key_from`, `export_generated_key`, `backups/` e `.restore/` fra i percorsi gestiti, i
>     due passi d'avvio) le gira il coordinatore quando B3 e B4 si avvicinano.
> - **Corsia**: fino alla fine della finestra della galleria (~12:30, avviso del coordinatore) solo prove leggere:
>   `nice`, nessun server, una alla volta.
> - **Docker**: acceso, ma B7 aspetta il CP7a di H. Richiesta del developer: alla fine di ogni prova Docker rimuovere le
>   immagini e i container creati, con nomi riconoscibili (`librefolio:b-…`); mai quelli degli altri.
> - **Checkpoint**: FROZEN a fine B0 e a fine B1.

### B0 — divisione di `api/v1/backup.py` (C2) e rinomina di `backup_service.py` (D-B8) (2026-10-15, 11:35-13:20) — ✅ committato alle 13:36, in dev `629d63306`

> **Disegno**, in tre commit:
>
> - **R**: `git mv backend/app/api/v1/backup.py backend/app/api/v1/backup/__init__.py`, rinomina pura (R100).
> - **C**: il taglio. `__init__.py` compone `backup_router` (`/backup`, tag «Backup & Export», il nome che usa
>   `router.py:43`) da `instance.py` (i 4 segnaposto e i loro schemi, invariati) e `exports.py` (gli export per serie,
>   invariati), in quest'ordine, cioè l'ordine di registrazione di oggi. Nello stesso commit: le righe «Source files»
>   della devWiki (C6) e la stringa del runner che nomina il file.
> - **S**: `git mv backend/app/services/platform/backup_service.py backend/app/services/platform/series_export.py`,
>   più gli import (`exports.py` e 2 file di test), i commenti che nominano il modulo e la riga «Source files» di F-073.
> - **Prove**, contro la base esportata con `git archive HEAD` (`/tmp/librefolio-r13-b-b0/base`):
>   - OpenAPI senza `info.version`: `87d4a455d85dee5e` alla base, deve restare uguale;
>   - le 140 rotte effettive (`iter_route_contexts`: percorso, metodi, nome, endpoint, schema, tag, modello), uguali
>     per ordine;
>   - 9 percorsi d'esempio arrivano allo stesso endpoint, con gli stessi parametri;
>   - ogni commit intermedio si importa e dà le stesse rotte (patch applicate su copie di `/tmp`);
>   - i test `api backup`, `api backup-export-extras` e `api asset-prices-export` dopo la finestra della galleria.
>
> **Passo 0 ✅** (11:35): base esportata, sonda in `/tmp/librefolio-r13-b-b0/route_probe.py`, riferimento in
> `/tmp/librefolio-r13-b-b0/ref/base.json` (openapi `87d4a455d85dee5e`, 140 rotte, 9 percorsi d'esempio).
>
> **Passo 1 ✅ — R e C** (11:40):
>
> - **R**: `backup.py` spostato in `backup/__init__.py` con un `mv` del filesystem (niente `git mv`: l'indice resta del
>   coordinatore).
> - **C**: taglio con uno script che copia i segmenti originali byte per byte (`/tmp/librefolio-r13-b-b0/cut_backup.py`):
>   - `instance.py` (167 righe): i 6 schemi e i 4 segnaposto; `instance_router = APIRouter()`;
>   - `exports.py` (238 righe): `_build_filename` e i 3 export per serie; `exports_router = APIRouter()`;
>   - `__init__.py` (16 righe): docstring, `backup_router` con prefisso e tag, poi `instance` e `exports`, in
>     quest'ordine;
>   - cambiano solo i decoratori (`@backup_router.` → `@instance_router.` / `@exports_router.`) e le intestazioni dei
>     moduli (docstring divise fra i due, import ridotti a quelli usati).
> - Nello stesso commit: le righe «Source files» della devWiki (C6) in `decisions/policy-d-currency-wipe.md`,
>   `entities/backup-router.md` (anche la frase «Location», che nominava il file) e `features/F-073.md` (la riga
>   degli endpoint diventa due: `exports.py` e `instance.py`), e la stringa di `api_backup` nel catalogo del runner
>   (`_backend_api.py:265`, «backup/instance.py placeholder endpoints»).
>
> **Passo 2 ✅ — S, la rinomina di `backup_service.py`** (11:45): `mv` in `series_export.py` (contenuto identico, R100);
> import in `exports.py:25` e nei due test (`test_asset_prices_export.py:39`, `test_backup_export_extras.py:47`), più i
> commenti che nominano il modulo (`exports.py:47`, `test_asset_prices_export.py:20`, `test_backup_export_extras.py:14`);
> in F-073 la riga «Source files», la riga 40 e il percorso sbagliato della riga 25 (`services/backup_service.py`).
>
> **⚠️ Fuori pista**: la docstring di `backup_asset_prices` (`exports.py:71`) cita `backup_service.PRICE_COLUMNS`, e
> quel testo finisce in `openapi.json`. Cambiarlo rompeva l'identità dello schema (`6d188b57…` contro `87d4a455…`):
> come per X-R1 e X-R2, resta fino a un lotto che cambia comunque l'API, cioè B1 (riga B-3 del backlog).
>
> **Passo 3 ✅ — prove** (11:50):
>
> - `ruff check` e `black --check` puliti sui 6 file Python toccati e su `_backend_api.py`.
> - Grep dei vecchi nomi (`backup_service`, `api/v1/backup.py`) a zero in `backend/`, `scripts/`, `.github/`,
>   `mkdocs_src/docs/developer/` e nelle pagine non storiche della devWiki. Restano due pagine storiche
>   (`sources/phase07-part3-closure*.md`) e un commento in `frontend/src/lib/components/ui/data-editor/DataEditor.test.ts:802`,
>   file di T (riga B-2 del backlog).
> - **Tre commit come patch**, costruite in un repository usa e getta in `/tmp` (mai l'indice del progetto), in
>   `/tmp/librefolio-r13-b-b0/split/`, con copie nella cartella di sessione:
>   - `01-R-rename-backup-package.patch` (R100), `02-C-cut-instance-exports.patch`,
>     `03-S-rename-series-export.patch` (R100 più i riferimenti).
> - **Catena**: le tre patch applicate in ordine su una copia completa della base (`/tmp/librefolio-r13-b-b0/chain`);
>   dopo **ognuna** OpenAPI senza `info.version` uguale (`87d4a455d85dee5e`), le 140 rotte uguali per ordine,
>   percorso, metodi, nome, endpoint, schema, tag e classe del modello (cambia solo il modulo nel `repr` delle classi
>   spostate), i 9 percorsi d'esempio sugli stessi endpoint con gli stessi parametri. Alla fine i 10 file toccati sono
>   identici a quelli del worktree, e `backup.py` e `backup_service.py` non ci sono più.
> - **AST**: 14 definizioni su 14 identiche fra `backup.py` e i due moduli, salvo il nome del router nei decoratori;
>   `series_export.py` identico a `backup_service.py`.
>
> **Passo 4 ✅ — perno d'ordine, raccolta, statici** (11:48):
>
> - **Test** (test-author): `test_backup_api.py::test_the_split_keeps_the_routes_of_backup_py_in_their_order`, puro
>   (né server né DB), sul modello del perno C2 di `test_system_api.py`: le 7 rotte esatte di `backup.py`, in ordine,
>   ognuna col suo metodo, il solo tag «Backup & Export» e il modulo che la serve (`instance.*`, `exports.*`).
>   - Prova di mutazione: con i due `include_router` scambiati il test è rosso; il file ripristinato ha lo stesso
>     sha256 (`a60f530a…eb71e6`).
>   - Entra nel commit C, con la descrizione di `api backup` nel catalogo («Placeholder endpoints, route order (C2)»).
> - **Patch ricostruite** con il test nel commit C, catena riverificata: dopo ognuna OpenAPI e rotte uguali alla base;
>   alla fine 11 file identici al worktree. Impronte: R `b4fb06f8…cd29d`, C `63fb12fe…3446d`, S `a9df3549…1f33031`.
> - **Raccolta** (`pytest --collect-only`, base esportata contro worktree): 14 220 → 14 223. La differenza è esatta: il
>   perno (+1) e la guardia `config-package`, parametrizzata sui moduli (via `api/v1/backup.py` e `backup_service.py`,
>   dentro `backup/__init__.py`, `exports.py`, `instance.py` e `series_export.py`: +2). Quei 4 casi e il perno: 5
>   passati (`pytest` diretto, puro, `nice`).
> - **Codice morto** (`dev.py lint --dead-code --scope backend`, vulture): gli stessi 36 reperti alla base e dopo,
>   nessuno nei file spostati. knip non gira senza `node_modules`.
> - **`check_source_paths.py`**: 10 percorsi inesistenti (16 occorrenze), gli stessi della base; citati 3 877 → 3 879.
> - `git diff --check` pulito.
>
> **Resta per il checkpoint** (dopo la finestra della galleria, con il via a `npm ci`): `api backup`,
> `api backup-export-extras`, `api asset-prices-export` sul server della corsia.
>
> **Passo 5 ✅ — le suite sul server della corsia** (13:03-13:20, dopo la fine della finestra, una alla volta, `nice -n 10`):
>
> - `npm ci` dal lock in `frontend/` (lock invariato; npm ha tenuto fermi gli script d'installazione di esbuild e
>   fsevents, come negli altri worktree). `front build --debug` rc 0, svelte-check 0 errori e 0 avvisi;
>   `mkdocs build` rc 0, 0 WARNING, 3 012 URL relativi risolti.
> - `api backup` 6 passati (i 5 test dei segnaposto e il perno); `api backup-export-extras` 8 passati;
>   `api asset-prices-export` 5 passati. Porta 6187 libera alla fine.
> - Gli 11 file di B0 nel worktree sono identici a quelli della catena di patch; `git diff --check` pulito.
> - Non lanciato: `all-backend` (pesante, lo assegna il coordinatore): il riordino è provato dall'identità di OpenAPI,
>   rotte e AST, e dalla raccolta (+3, tutti spiegati).
>
> **Fuori pista**: alle 13:20 il coordinatore apre la finestra delle dipendenze (`cryptography`): niente comandi
> Python fino al suo avviso.

### B1 — backup dell'istanza, backend e CLI — la bozza e il passo 1 (2026-10-15, fino alle 12:55) ✅ — B1 committato alle 14:14 (`e35388306`), in dev `629d63306`

> **Metodo**: per non mescolare B1 con il checkpoint di B0, la bozza sta in una copia dell'albero di B0 in `/tmp`
> (`/tmp/librefolio-r13-b-b1/tree`), mai nel worktree. Entra nel worktree dopo il commit di B0, poi test-author scrive i
> test e i verdi girano sulla corsia.
>
> **Disegno della bozza** (fatti verificati con una prova in `/tmp`: `VACUUM INTO` mentre un altro processo scrive in
> WAL non blocca lo scrittore, 3 756 commit durante la copia, e la copia è integra, in modalità rollback, senza file
> accanto):
>
> - `services/platform/instance_backup/`: `paths` (cosa entra: `sqlite/app.db`, `custom-uploads/`,
>   `broker_reports/`, `scenario_catalog/`; dove si scrive: `backups/`, `backups/.jobs/<id>/`; cartelle 0700, mai
>   attraverso un link), `snapshot` (`VACUUM INTO` e descrizione della copia: integrità, chiavi esterne, righe per
>   tabella, revisione), `manifest` (pydantic, `format_version` 1, campi sconosciuti ignorati, percorsi controllati),
>   `archive` (zip 0600 scritto come `.part` e rinominato, file in streaming con lo SHA-256, link mai seguiti, controllo
>   dello spazio prima; `check_archive` per `inspect` e per B2, che non legge mai un'entrata oltre la dimensione
>   dichiarata), `jobs` (un thread per job, `flock` su `backups/.jobs/.lock`, stato su file scritto in modo atomico,
>   «interrotto» se lo stato dice in corso e il lock è libero, conservazione di un'ora).
> - `schemas/backup.py`: `InstanceBackupJob`.
> - `api/v1/backup/instance.py`: `POST /backup/instance` (202), `GET` e `DELETE /backup/instance/jobs/{id}`,
>   `GET /backup/instance/jobs/{id}/file` (`Cache-Control: no-store`); solo admin (`require_admin`); errori con
>   `detail.code`: `backup_busy`, `backup_job_not_found`, `backup_job_not_ready`, `backup_job_running`. Via i 4
>   segnaposto e i loro 6 schemi (D-B7).
> - `scripts/backup_cli.py` e due righe in `dev.py`: `backup [--test-db] create [-o PATH]` e `backup inspect FILE
>   [--no-verify]`. Avviato come root (un `docker compose exec` senza utente), il comando passa all'utente proprietario
>   della cartella dati prima di scrivere, come fa `gosu` nell'entrypoint: archivio, lock e file di SQLite restano del
>   server.
> - La docstring di `backup_asset_prices` ora cita `series_export.PRICE_COLUMNS` (B-3).
>
> **Prove della bozza** (12:00, solo `/tmp`): uno smoke test su una cartella dati sintetica con un link a
> `secrets/instance.key` e uno a `secrets/` dentro le cartelle archiviate. Archivio 0600, cartella del job 0700; dentro
> solo il DB (primo), i file e il manifest (ultimo); fuori log, segreti, stato dello scheduler e i due link (avviso
> `files_skipped`, elencati dalla CLI); `check_archive` verde, e rosso su un file alterato e su un'entrata in più; job in
> background, secondo avvio rifiutato mentre gira, stato «interrotto» con il lock libero, pulizia dopo un'ora, id non
> validi mai trasformati in percorsi; CLI `create`, `inspect` (0 e 1), `--help` con il gruppo. ruff e black puliti.
> OpenAPI rispetto alla base: via i 4 percorsi e i 6 schemi dei segnaposto, +3 percorsi (4 rotte) e
> `InstanceBackupJob`; cambia solo la descrizione dei prezzi (B-3).
>
> **Passo 1 ✅ — i file nuovi nel worktree e i test puri** (12:05-12:55):
>
> - Via del coordinatore (12:03): «B1 intanto va avanti»; `npm ci` solo dopo l'avviso di fine finestra, spostata alle
>   13:30. Nel worktree entrano **solo i file nuovi** di B1 (`services/platform/instance_backup/`,
>   `schemas/backup.py`, `scripts/backup_cli.py`), che nessuno importa ancora: il codice di B0 resta quello delle tre
>   suite `api` da far girare dopo la finestra. Le modifiche di B1 ai file condivisi (`instance.py`, `__init__.py`,
>   `exports.py`, `dev.py`, catalogo, istruzioni, devWiki) restano pronte in `/tmp` fino al commit di B0.
> - **Test** (test-author): `test_services/test_backup_archive.py` (126), `test_services/test_backup_jobs.py` (31),
>   `test_utilities/test_backup_cli.py` (26); tre voci pure nel catalogo (`services backup-archive`,
>   `services backup-jobs`, `utils backup-cli`). Una prova di mutazione per file, ognuna rossa e poi ripristinata con
>   lo stesso sha256.
> - **⚠️ Fuori pista — 8 rossi, 6 difetti veri della bozza**, tutti corretti nel codice (i test non cambiano):
>   1. un'entrata danneggiata (CRC, deflate) faceva uscire da `check_archive` un `BadZipFile` grezzo, e `inspect`
>      andava in traceback: ora è «mismatched», e un manifest danneggiato è `manifest_unreadable`;
>   2. il manifest si leggeva per la dimensione dichiarata dallo zip (68 MB gonfiati da un archivio sotto 1 MB): ora si
>      rifiuta oltre `MANIFEST_MAX_BYTES` senza leggerlo, e non si legge mai oltre `MANIFEST_MAX_BYTES + 1`;
>   3. senza `fcntl` un job vivo risultava interrotto: il controllo del lock non dipende più dall'esistenza del file;
>   4. una sottocartella illeggibile spariva in silenzio: `os.walk` ha un `onerror` che la segnala (`files_skipped`);
>   5. un file datato dopo il 2107 bloccava ogni backup: la data dello zip è limitata anche in alto;
>   6. una tabella con `"` nel nome rompeva la descrizione: il nome si cita raddoppiando le virgolette.
>
>   E due osservazioni di test-author: un job finito da oltre un'ora ora si toglie anche alla lettura (risponde «non
>   trovato»), come diceva la docstring; il file si apre con `O_NONBLOCK`, così un file diventato una FIFO dopo la
>   raccolta non blocca il backup.
> - **Verdi** (pytest diretto, puro, `nice`): 182 passati, 1 saltato (nomi non UTF-8: macOS li rifiuta, il test gira su
>   Linux). ruff e black puliti.

### Checkpoint B0 🧊 (2026-10-15) — FROZEN; committato dal coordinatore alle 13:36

> Handoff inviato. Tre commit di codice dalle patch (R, C, S, da applicare in ordine con `git apply --cached`) e il
> journal (questo piano, la sezione B del backlog). Il lavoro di B1 nel worktree (file nuovi non tracciati, tre voci nei
> cataloghi `_backend_services.py` e `_backend_utils.py`) non fa parte di B0.
>
> **Committato dal coordinatore** (13:36) nei 4 commit proposti: `bc1a01141` (R), `73b138b9b` (C), `256a78b36` (S),
> `be6206c0d` (journal). Il lavoro di B1 è rimasto fuori, nel worktree. `all-backend` non serve: lo fa il coordinatore
> all'ingresso. Nella stessa ora la finestra delle dipendenze ha portato `cryptography` 50.0.2 in `dev_release2`
> (`dc9a5d232`; nel lock cambia anche `pycparser`, 3.0 → 3.11): B4 non aspetta più la dipendenza, solo il punto 38.
>
> **Regole di carico nuove** (coordinatore, 13:36): per la mia corsia solo test di un singolo file (pytest o Vitest),
> uno alla volta, con `nice -n 10`; build, svelte-check, `mkdocs build` ed E2E su richiesta; le prove pesanti le assegna
> lui, al massimo 2 su tutta la macchina.

### B1 passo 2 — i file condivisi e la seconda tornata di test (2026-10-15, 13:38-14:12) ✅

> **Note implementazione**:
>
> - HEAD `be6206c0d` verificato; il lavoro di B1 intatto.
> - Dalla copia in `/tmp`, dopo un confronto riga per riga (solo le differenze di B1): `backup/instance.py` (le 4 rotte
>   nuove al posto dei segnaposto), la docstring di `backup/__init__.py`, la docstring dei prezzi in `backup/exports.py`
>   (B-3), il gruppo `backup` in `dev.py` (un import, una chiamata, due righe dell'aiuto sotto «💾  Backup»), la stringa
>   e la descrizione di `api backup` nel catalogo, le due righe della mappa in `backend.instructions.md`, e nella
>   devWiki F-073 e `entities/backup-router.md`.
> - devWiki, per chiudere B-1: in F-073 la nota sullo streaming (gli export per serie leggono la serie intera prima di
>   mandarla) e la riga di Impostazioni (la scheda arriva con B5); in `domains/infrastructure.md` la riga di F-073.
> - **Prove** (leggere, `nice -n 10`): ruff e black puliti sui 12 file Python; `dev.py backup --test-db create` sul DB
>   della corsia (schema vero, revisione `005_accounts_invites`): 61 file, 24,7 MB in 0,9 s, poi `backup inspect`: ogni
>   entrata uguale al manifest; la cartella del job tolta. OpenAPI del worktree identico a quello rivisto nella bozza
>   (`b4e6226d58581b8b`; le rotte sono 141 perché ora c'è `frontend/build`, e `main.py` aggiunge il mount `/_app`).
>   Nessun uso nel frontend delle rotte tolte.
> - **Test** (test-author, in corso): riscrittura di `test_backup_api.py` per le rotte nuove (perno C2 aggiornato) e
>   casi nuovi in `test_dev_cli_image.py` (il gruppo `backup` nell'albero dell'immagine).
>
> **Passo 3 ✅ — seconda tornata di test e verdi** (14:00-14:12):
>
> - **Test** (test-author, nessun difetto trovato):
>   - `test_backup_api.py` riscritto, 23 test (BACKUP-001…010): perno C2 con le 4 rotte nuove e i 3 export; 401 senza
>     sessione e 403 per un utente normale su ognuna; il giro dell'admin fino allo scaricamento (zip con `sqlite/app.db`
>     primo e `manifest.json` ultimo, revisione uguale a quella del DB della corsia, dentro l'admin del test,
>     `Cache-Control: no-store`); `backup_busy` col lock tenuto dal test per una richiesta; `DELETE` e poi 404; un job
>     «in corso» scritto dal test (409 `backup_job_not_ready` e `backup_job_running`, poi `backup_interrupted`); id
>     sconosciuti e malformati sempre 404, mai 500; i segnaposto tolti rispondono 404 o 405. Ogni job e ogni utente
>     creati vengono tolti alla fine.
>   - `test_dev_cli_image.py`: IMG-013/013b (`backup` in `--help`, `backup --help`) e IMG-014/014b (`backup create`
>     sul DB dell'albero dell'immagine scrive un solo archivio in `backups/`, senza cartelle di job, con dentro quel DB;
>     `inspect` 0, e 1 su un file che non c'è).
>   - Prove di mutazione: senza `Cache-Control`, con gli `include_router` scambiati, senza la pulizia della cartella
>     del job: tutte rosse, file ripristinati con lo stesso sha256.
>   - Le descrizioni di `api backup` e di `utils dev-cli-image` nel catalogo dicono le prove nuove (la seconda è una
>     voce di H: solo la descrizione).
> - **Verdi**, sulla corsia, un file alla volta, `nice -n 10`: `api backup` 23; `utils dev-cli-image` 48 (44 + 4);
>   `services backup-archive` 125 + 1 saltato; `services backup-jobs` 39; `utils backup-cli` 26;
>   `services config-package` 602; `services config-env-example` 36; `api backup-export-extras` 8;
>   `api asset-prices-export` 5.
> - **Statici**: ruff e black puliti; codice morto: lo stesso insieme della base; `check-orphans`: 280 file di test
>   raggiungibili da un `all`; `check_source_paths` senza percorsi nuovi mancanti; `git diff --check` pulito; porta
>   6187 libera.
> - **Non lanciati** (vanno chiesti al coordinatore): `api sync` con `front check`. Il client generato perde le 4 rotte
>   tolte, che nel frontend nessuno usa (grep su `frontend/src` e `frontend/e2e`).
> - **Da sapere per B5**: lo stato finale si scrive prima di liberare il lock, quindi chi riavvia un backup nell'istante
>   in cui legge «done» può ricevere un 409 `backup_busy` per un attimo: la UI non offre il riavvio immediato, o ritenta.
> - **Fuori pista**: una sonda in sola lettura di test-author, a server spento, ha lasciato `app.db-wal` e `app.db-shm`
>   vuoti accanto al DB della corsia: innocui. Il runner mette una copia del DB di test in `.testLog/00_archive/`
>   (ignorata).

### Checkpoint B1 🧊 (2026-10-15) — committato

> Handoff inviato con l'elenco dei file, le prove e il testo proposto per il CHANGELOG.
>
> **Committato dal coordinatore** (14:14): `e35388306` (`feat(backup): …`, con la nota BREAKING CHANGE sui 4
> segnaposto) e `d37736d05` (journal e devWiki). HEAD verificato `d37736d05`, worktree pulito.
>
> **Ingresso**: B0+B1 entrano dopo H, E1, X e A5. Prima il coordinatore aggiorna la base, poi io valido la revisione
> combinata; conflitti attesi nei cataloghi del runner e in `test_dev_cli_image.py`, insieme al CP7a di H. Il CHANGELOG
> lo scrive il coordinatore all'ingresso, con il mio testo.

### Via per B6a, B5a e l'accordo con J (coordinatore, 2026-10-15 alle 14:14)

> - **B6a**, la doc della CLI con docs-writer: sì, subito.
> - **Accordo con J sui totali di controllo**: sì. Scrivo io a J, nel suo perimetro (`financial_math`, il motore); lui
>   risponde con la firma.
> - **B5a**, la scheda Backup con il solo scaricamento: sì. La riga nel registro di A va scritta dopo che A5 è nella mia
>   base: prima il componente, poi la riga. Per le E2E e `front check` serve lo slot del coordinatore.
> - **B4**: il punto 39 non è deciso. Il developer è al 30; i punti 38 e 39 vengono dopo quelli di Z.
> - **Corsia**: solo prove leggere di file singoli; le medie su richiesta (la macchina era a 110–139 alle 13:45).

### Accordo con J — totali di controllo (2026-10-15, 14:20) — firma di J alle 14:35 (CP-15)

> Richiesta mandata a J (`4c677a01`, in coda): una funzione in sola lettura per i totali di controllo.
>
> - **Deterministica**: niente prezzi, cambi, rete né `today`; tutto il registro.
> - **Su tutta l'istanza**, quota al 100%: cassa nativa per (broker, valuta) e quantità per (broker, asset).
> - **Senza cache di modulo**: chiamabile su una sessione aperta su un altro file SQLite nello stesso processo;
>   altrimenti in un sottoprocesso.
> - **Serializzabile**, con un numero di versione del metodo; costo lineare.
> - **Forma proposta**: `compute_control_totals(session) -> ControlTotals`.
>
> Serve a B2. Il campo `control_totals` del manifest lo aggiungo io.
>
> **Risposta di J** (14:35): sì, nel suo lotto **CP-15**.
>
> - **Firma**: `backend/app/services/financial_math/ledger_totals.py`
>   - `CONTROL_TOTALS_VERSION = 1`;
>   - `ControlTotals(version, cash, quantities)`, frozen e con slots: `cash` è `(broker_id, currency, balance)`,
>     `quantities` è `(broker_id, asset_id, quantity)`;
>   - `to_json()` e `from_json()`; `from_json` alza `ValueError` se la versione è diversa;
>   - `async compute_control_totals(session) -> ControlTotals`.
> - **JSON**: `{"version": 1, "cash": [{"broker_id", "currency", "balance"}], "quantities": [{"broker_id", "asset_id",
>   "quantity"}]}`.
> - **Regole**:
>   - cassa = Σ `amount` per (broker, valuta), come `native_balances`; quantità = Σ `quantity` per (broker, asset),
>     come il motore (`daily_state.py:184-187`; split e trasferimenti sono già righe); quota 100 %;
>   - somme esatte in Python, mai `SUM` SQL, perché `Numeric` su SQLite passa per un float; i residui di polvere restano;
>   - nessuna riga a zero: una chiave assente vale zero;
>   - Decimal canonico, senza esponente, senza zeri finali, mai «-0»;
>   - indipendenti dal tipo di riga: una migrazione che riclassifica (per esempio V-3 di W) non li cambia;
>   - lettura a blocchi solo dalla `session` passata: niente prezzi, cambi, rete, `today`, `get_settings()` o cache;
>     `asyncio.run` dal thread del job va bene.
> - **Versione diversa** (`data["version"] != CONTROL_TOTALS_VERSION`): il report dice «non confrontabile» e non chiama
>   `from_json`.
> - **Il costo resta fuori**: dipende dai cambi e da WAC e FIFO, quindi la versione salirebbe spesso. Lo coprono i
>   controlli per tabella.
> - **Tempi**: CP-15 parte quando N1 di W (`native_balances`) è nella base di J; l'ordine lo decide il coordinatore. J
>   avvisa all'integrazione. Fino ad allora i test di B usano una funzione finta della stessa forma.

### B6a — doc della CLI (2026-10-15, dalle 14:20) ✅ (14:51)

> docs-writer lavora su `admin/cli_tools.en.md`: la sezione «💾 Back Up the Instance» (`{: #backup }`), l'introduzione
> e il suggerimento per Docker.
>
> - Solo inglese; nessun timbro di traduzione, perché il debito di traduzione è vero.
> - `mkdocs build` e `check-links`: lo slot va chiesto al coordinatore.
> - La riga per `filesystem.en.md` (file di H) la propongo al coordinatore.
>
> **Prima stesura** (docs-writer, 14:32): sezione con cinque sottosezioni (crea, cosa contiene, controlla, usa altrove,
> Docker `{: #backup-docker }`), più l'introduzione e il suggerimento per Docker.
>
> **⚠️ Fuori pista — 6 difetti della CLI e dell'archivio di B1**, trovati da docs-writer leggendo il codice e corretti
> (14:40):
>
> 1. **`-o` controllato solo alla fine.** Se lo spostamento falliva (cartella non scrivibile, disco pieno su un altro
>    volume), il comando andava in traceback dopo tutto il backup. L'archivio restava in `.jobs/` e il backup successivo,
>    dopo un'ora, lo cancellava.
>    - Ora `_check_output` controlla prima: nome di file libero, cartella creata se manca, cartella scrivibile.
>    - `_place_archive` sposta l'archivio, e se non ci riesce lo mette in `<data dir>/backups/` (rinomina sullo stesso
>      volume), senza lasciare copie parziali, con un avviso e il codice 1.
>    - Solo se fallisce anche questo l'archivio resta nella cartella del job, con il percorso e la scadenza di un'ora.
> 2. **Falso «already exists»** con `-o` su una cartella che conteneva un file `librefolio-backup.zip`: il controllo
>    usava un nome segnaposto. Ora una cartella esistente va sempre bene.
> 3. **Aiuto di `--no-verify`**: diceva «legge solo il manifest», ma i nomi delle entrate si confrontano comunque.
>    Corretti l'aiuto e la riga finale.
> 4. **Percorsi relativi**: `dev.py` fa `chdir` alla radice del progetto, quindi partono da lì, come in
>    `db upgrade`. Lo dicono ora l'aiuto e l'esempio di `inspect`.
> 5. **Formulazione dei file esclusi** («cambiati durante il backup»): non era esatta. Ora: link, file speciali, file o
>    cartelle illeggibili, file tolti durante il backup. Lo stesso testo nella CLI e nella UI, in 4 lingue.
> 6. **Errore di lettura a metà file** (trovato rileggendo `_add_file` per il punto 5): l'entrata dello zip si chiude
>    comunque, e l'archivio conteneva un pezzo di file fuori dal manifest. `inspect` lo segnalava, ma il job diceva
>    «done». Ora `PartialEntryError` ferma il backup (`backup_failed`). Un file che fallisce prima di aprire l'entrata
>    resta escluso, come prima.
>
> ruff e black puliti. I test nuovi (CLI: `-o` scrivibile e ripiego; archivio: errore a metà file) li scrive
> test-author dopo i Vitest di B5a, uno alla volta nella corsia. La doc è allineata da docs-writer.
>
> **⚠️ Fuori pista, seconda tornata** (14:55): docs-writer, rileggendo il codice nuovo, segnala altri tre difetti; un
> quarto lo trovo io:
>
> 7. **`backups/` come link**, per esempio verso un NAS: `ensure_private_dir` alza `BackupPathError`, che la CLI non
>    prendeva (traceback) e l'API trasformava in un 500 senza codice. Ora:
>    - nella CLI, un messaggio chiaro e il codice 1; anche un `OSError` prima della corsa ha un messaggio;
>    - nell'API, 500 con `backup_folder_unusable`, oppure `backup_failed` per un `OSError`, con una riga di log;
>    - il rifiuto del link resta: l'archivio si costruisce sempre in `backups/.jobs/`, e il disco della cartella dati
>      deve avere lo spazio anche con `-o`.
> 8. **`_check_output` creava la cartella di `-o`** prima del backup: un backup fallito lasciava una cartella vuota.
>    Ora controlla la cartella esistente più vicina (deve essere una cartella, scrivibile); le cartelle mancanti si
>    creano solo quando l'archivio ci arriva.
> 9. **Commento di `BuildWarning`** in `archive.py`: stessa formulazione corretta dei file esclusi.
> 10. **Due backup nello stesso secondo** dalla CLI: il secondo trovava il nome preso e restava nella cartella del job.
>     Ora una cartella (`backups/` o una cartella `-o`) riceve `-2`, `-3`, … (`_free_path`); un `-o FILE` esplicito non
>     si rinomina mai.
>
> In più, per il punto 6: un disco pieno o una quota superata durante la costruzione, dopo il controllo dello spazio,
> ora finisce come `backup_no_space` e non come `backup_failed` (`_out_of_space` segue `__cause__` e `__context__`:
> `ENOSPC`, `EDQUOT`, `SQLITE_FULL`).
>
> - `_add_file` ora prende anche gli errori di `archive.open` e della chiusura dell'entrata, quindi anche quelli di
>   scrittura.
> - `cmd_create` è diviso in `_run_backup` più il resto, per C901.
> - ruff e black puliti.
> - **Verdi** dei file esistenti: `services backup-archive` 125 più 1 saltato; `services backup-jobs` 39;
>   `utils backup-cli` 25 su 26. Il rosso è `test_inspect_without_verification_reads_the_manifest_only` (poi rinominato
>   `…_reads_no_entry`), che cercava il vecchio testo di `--no-verify`: è atteso, e lo ripara test-author con i test nuovi.
> - **Smoke** (`/tmp/librefolio-r13-b-b6/smoke_cli.py`, cartelle dati sintetiche in una cartella temporanea, poi
>   tolte), cinque casi, tutti come previsto:
>   1. `backups/` link verso un'altra cartella: codice 1, messaggio chiaro, niente scritto oltre il link;
>   2. `-o` in cartelle che non esistono: create alla fine, archivio 0600, codice 0;
>   3. `-o` sotto una cartella in sola lettura: rifiuto prima del backup, nessuna cartella creata, neanche `backups/`;
>   4. `-o` sotto un file: «is not a folder»;
>   5. due backup nello stesso secondo: il secondo è `…-2.zip`, tutti e due con codice 0.
> - **UI**: il codice nuovo `backup_folder_unusable` ha il suo messaggio nelle 4 lingue (34 chiavi).
>
> **Fuori dal perimetro, da girare al coordinatore**:
>
> - `docker_advanced.en.md#docker-exec` e il commento in testa a `docker-compose.yml` elencano i comandi dell'immagine
>   senza `backup`;
> - `admin/index.en.md:21` descrive la pagina della CLI senza i backup;
> - `filesystem.en.md` (di H): un rimando alla CLI, la nota che una copia della cartella dati prende anche `backups/`,
>   e `backups/` nell'albero; un'ancora esplicita `{: #what-to-back-up }` nelle 4 lingue (il link della pagina nuova ora
>   punta a `filesystem.md#backup`).
>
> **Terza tornata e verifica** ✅ (14:45-14:51):
>
> - docs-writer allinea la pagina alle correzioni 7-10: `backups/` deve essere una cartella vera, mai un link, perché
>   l'archivio si costruisce lì anche con `-o`; i nomi `-2`, `-3`; i tre rifiuti di `-o`; `backup_no_space` anche a
>   metà corsa.
> - Le sue due ultime note:
>   - il messaggio nominava sempre `backups/` anche quando il link era `.jobs/`: ora `BackupPathError` porta il
>     percorso (`.path`), e la CLI nomina la cartella vera;
>   - un disco montato su `backups/` passa il controllo, perché è una cartella vera. Non lo documento come via
>     consigliata: il lock `flock` e la copia SQLite su una condivisione di rete (NFS, SMB) non sono garantiti. Per un
>     NAS la doc indica `-o`.
> - **Verifica**, slot del coordinatore, `nice -n 10`:
>   - `dev.py mkdocs build`: strict, codice 0, 105 s, nessun avviso (l'unica riga è il riquadro del team di Material);
>   - `dev.py mkdocs check-links`: 95 link validi;
>   - nella pagina costruita ci sono le ancore `#backup` e `#backup-docker`, e i link a `../filesystem/#backup`.
> - **Debito di traduzione** (B-7): la sezione nuova, una frase dell'introduzione e il punto Docker del suggerimento,
>   in IT, FR ed ES. Nessun timbro.
> - Log in `/tmp/libreFolio_b_mkdocs_build.log` e `/tmp/libreFolio_b_check_links.log`.
>
> **Testo proposto da docs-writer per `filesystem.en.md`** (B-5):
>
> - sotto il titolo «💾 Backup»: «To back up without stopping the server, `./dev.py backup create` writes one zip archive
>   of the database, the uploaded files, the broker reports and the scenarios: see [Back Up the
>   Instance](cli_tools.md#backup). It leaves out `secrets/`, which you back up as below.»
> - dopo il blocco di «📦 Simple Backup»: «The copy also takes `backups/`, with every archive `backup create` wrote
>   there: delete the old ones first, or leave the folder out.»

### B5a — scheda Backup, solo scaricamento (2026-10-15, dalle 14:25) — componente ✅; la riga del registro con `b7a4d35e6` (17:04)

> **Disegno**:
>
> - **Feature nuova** `frontend/src/lib/features/backup/`:
>   - `backupApi.ts`: i tre alias del client generato, l'URL del file (`<a href>`, quindi niente Blob in memoria) e i
>     codici d'errore (`detail.code`, altrimenti `network` senza risposta e `unexpected` con una risposta senza codice);
>   - `backupJob.svelte.ts`: `BackupJobController`, una classe con le rune e sette stati (`idle`, `loading` per la
>     rilettura di un job già seguito, `starting`, `running`, `done`, `deleting`, `failed`). Legge il job ogni secondo, con ritardo crescente fino a 5×, e si ferma dopo 5
>     letture fallite di fila. L'id del job sta in `sessionStorage`, così un ricaricamento riprende lo stesso job.
>     Ogni azione apre una nuova generazione, quindi una risposta arrivata in ritardo si scarta.
>   - `BackupDownloadCard.svelte`: autonomo, così lo può usare anche la pagina di blocco di H. Pubblica `data-state`,
>     `data-error-code` e `data-busy`; emette gli eventi `backup.created` (toast solo con avvisi), `backup.failed`
>     (toast d'errore), `backup.deleted` e `backup.download.started`.
>   - `BackupTab.svelte`: il corpo della scheda.
> - **i18n**: sottosistema nuovo `lib/i18n/backup/` (prefisso `backup`, libero), 35 chiavi nelle 4 lingue, in forma
>   canonica.
> - **Colori**: solo ruoli `*-lf-*` (`bg-lf-panel`, `border-lf-subtle`, `bg-lf-warning-soft`, `bg-lf-danger-soft`,
>   `bg-lf-action`, `bg-lf-neutral`, …). Nessuna palette, nessun esadecimale, nessun `dark:`. `toneClasses.ts` contiene
>   ancora stringhe di palette spostate tali e quali, quindi qui non serve.
> - **Polling**: nessun aiuto comune nella base (l'F26 di Z non c'è ancora). Quando arriva, il controller può
>   appoggiarsi a quello.
> - **Riga nel registro di A**: dopo A5 nella base, come chiesto.
>
> **Test**: test-author scrive `backupApi.test.ts`, `backupJob.test.ts` e `BackupDownloadCard.test.ts`, registrati nel
> catalogo (`front_utility_unit` e `front_component_unit`), un file Vitest alla volta.
>
> **Prima tornata di test** ✅ (test-author, 14:55):
>
> - Verdi: `backupApi.test.ts` 51, `backupJob.test.ts` 71, `BackupDownloadCard.test.ts` 38 (35 s, quasi tutti per
>   caricare `lucide-svelte`).
> - Una mutazione per file, rossa e poi ripristinata con lo stesso sha256.
> - Registrati in `_frontend_utility.py`, tre righe in aggiunta.
>
> **⚠️ Fuori pista — tre difetti di disegno**, segnalati da test-author e decisi da me (14:58):
>
> 1. **«Controlla di nuovo» dopo un nuovo avvio fallito** riportava l'archivio precedente e lo annunciava come appena
>    creato. Ora un avvio o una cancellazione falliti tengono l'archivio in offerta, con il banner d'errore. Il
>    pulsante compare solo dopo letture fallite (`canRecheck` nel controller, con `failure` ∈ `start`, `read`, `remove`,
>    `job`).
> 2. **Lo stesso archivio annunciato due volte** (rilettura dopo una cancellazione fallita o una ripresa). Ora la fine
>    di un job si annuncia una volta sola, e solo se questa scheda l'ha avviato o l'ha visto in corso (`#watched`).
> 3. **Scheda non occupata durante la cancellazione.** Nuovo stato `deleting`: la scheda è occupata e mostra
>    `backup-deleting` al posto delle azioni (chiave nuova `backup.download.deleting`).
>
> Eventi: `backup.failed` per `start`, `read` e `job`; `backup.delete.failed` per `remove`. Il dettaglio è
> `{code, what, job_id}`. test-author aggiorna i test e aggiunge i casi delle tre decisioni.
>
> **Seconda tornata di test** ✅ (test-author, 15:25):
>
> - Verdi: 51, 121 e 49. Una mutazione per decisione, rossa nel test del controller e in quello della scheda, poi
>   ripristinata con lo stesso sha256.
> - Due osservazioni di test-author, corrette (15:28):
>   - `recheck()` da `done`, se falliva la rete, nascondeva l'archivio. Ora `recheck()` agisce solo quando
>     `canRecheck` è vero, cioè dove la scheda offre il pulsante.
>   - Dopo le letture fallite di J, «Riprova» rifiutato con `backup_busy` (spesso perché J gira ancora) lasciava J
>     raggiungibile solo ricaricando la pagina. Ora un avvio fallito in `failed`, se la scheda segue ancora un job,
>     offre «Controlla di nuovo». Da `done` niente cambia: un avvio rifiutato resta in `done`.
> - Resta com'è, per scelta: mentre parte un nuovo backup da `done`, l'archivio precedente non si vede. Se l'avvio
>   fallisce, torna.
>
> **Terza tornata di test e statici** ✅ (15:30-15:37):
>
> - **Vitest** (test-author), verdi: `backupApi.test.ts` 51, `backupJob.test.ts` 131, `BackupDownloadCard.test.ts` 51.
>   - La tabella di verità di `canRecheck` ha 28 righe.
>   - Il caso «J bloccato» (letture fallite, «Riprova» rifiutato) è provato in tutti e due i file.
>   - Mutazione: senza `failure === 'start' ||`, 14 rossi su 131 e 4 su 51; file ripristinato con lo stesso sha256.
> - **Statici**, nello slot del coordinatore, con `nice -n 10`:
>   - `dev.py api sync`: codice 0, 20 s; il client generato (ignorato) ha la risposta 500 nuova;
>   - `dev.py front check`: svelte-check, 0 errori e 0 avvisi, 66 s;
>   - in più, leggeri: `i18n_catalog.py check` strict (4427 chiavi), `theme-roles.mjs --check` pulito, Prettier pulito
>     sui file nuovi;
>   - `dev.py lint --dead-code --scope backend` (vulture): 4 simboli non usati e 32 usati solo dai test, nessuno di B,
>     tutti di altre aree. knip (frontend) lo lancio con la riga del registro, dopo A5.
> - **Lasciato per scelta** (backlog B-8): se la risposta di un avvio si perde (rete), il job gira sul server ma la
>   scheda non lo sa, e `backup_busy` non dice quale job gira. Succede di rado, e si risolve da solo: la scheda dice
>   «busy» finché il job finisce, e l'archivio orfano scade dopo un'ora.
>
> **Pronto per dopo A5** (non applicato):
>
> - **Registro di A** (`settingsTabs.ts`), una riga:
>   - l'import di `DatabaseBackup` e di `BackupTab`;
>   - `{id: 'backup', labelKey: 'backup.tab', icon: DatabaseBackup, order: 120, component: BackupTab, visible: (ctx)
>     => ctx.isSuperuser}`, con il commento «Administrators only: the archive holds every user's data».
>   - Con `order` 120 la scheda cade dopo «admin» (`alignEnd`, ordine 100), nel gruppo di destra. Niente `props`,
>     niente `alignEnd`.
> - **Test del registro** (`settingsTabs.test.ts`): `bodies.backup`, il `vi.mock` di
>   `$lib/features/backup/BackupTab.svelte` e la riga di `TODAY`.
>   - Oggi il test fissa «un utente e un admin vedono le stesse quattro schede» (`it.each(CONTEXTS)`). Una scheda solo
>     admin chiede una colonna di visibilità in `TODAY`, che A5 porta probabilmente con le schede Users e Security
>     (lo annuncia la docstring del test). Per questo la riga aspetta A5, come chiesto.
> - **E2E** `frontend/e2e/settings/backup.spec.ts`, scritto da test-author, slot del coordinatore:
>   - giro dell'admin: `?tab=backup`, «crea», attesa su `data-state="done"`, scaricamento con `waitForEvent('download')`
>     (nome `librefolio-backup-…zip`, intestazione `PK`), evento `backup.download.started`, cancellazione con
>     `data-state="idle"` e `backup.deleted`;
>   - un utente normale non vede `settings-tab-backup`;
>   - `mode: 'serial'`, perché c'è un backup alla volta per istanza; pulizia del job nell'`afterEach`.
> - **Galleria** (`gallery.spec.ts`, di G, attraverso il coordinatore): la scheda nello stato `done`, con i job finti
>   via `page.route` (nome, dimensione e data fissi), quindi uno scatto deterministico; desktop e mobile, 4 lingue,
>   2 temi.
> - **i18n**: `backup.tab` non ha lettori finché non c'è la riga. `i18n audit` lo segna «dead», e le chiavi della
>   scheda «📦» (vive solo per sorgenti non raggiungibili da una rotta). Nessun cancello fallisce: `gate-i18n-usage`
>   prova il classificatore, non il catalogo vero. knip vede i file nuovi raggiungibili dai test.

### B1-fix — test delle correzioni di B6a (2026-10-15, 14:55-16:10) ✅

> **Test** (test-author, backend):
>
> - `utils backup-cli` +44 test, più uno riparato e rinominato: `test_inspect_without_verification_reads_no_entry`,
>   prima `…_reads_the_manifest_only`;
> - `services backup-archive` +14; `services backup-jobs` +24;
> - nuovo `test_api/test_backup_instance_errors.py` (selettore `api backup-instance-errors`, puro, 6 test, con
>   `httpx.ASGITransport`), registrato in `_backend_api.py`, 18 righe in aggiunta;
> - 32 mutazioni rosse, ogni file ripristinato con lo stesso sha256; `check-orphans` pulito.
>
> **⚠️ Fuori pista — altri due difetti**, trovati dai test e corretti (15:45):
>
> 1. **Cartelle create per `-o` e rimaste vuote.** Se l'archivio ripiegava su `backups/` (spazio scarso su un altro
>    disco, spostamento fallito), le cartelle create per `-o` restavano vuote: `target.parent.mkdir(parents=True)`
>    veniva prima del controllo.
>    - Ora il controllo di disco e spazio si fa sulla cartella esistente più vicina.
>    - Le cartelle mancanti si creano solo prima dello spostamento, e se fallisce si tolgono (dalla più profonda, se
>      vuote).
>    - `_place_archive` è diviso in `_folders_to_create`, `_move_to` e il resto, per C901.
>    - Uno spostamento che alza un errore quando l'archivio è già arrivato intero (sorgente sparita, destinazione
>      presente) è un successo: prima la CLI diceva che l'archivio era rimasto nella cartella del job, dove non c'era
>      più.
> 2. **Descrittore perso in `_add_file`.** Se al posto di un file raccolto c'era una cartella, `os.fdopen` alzava
>    `IsADirectoryError` e il descrittore restava aperto nel processo del server (5 chiamate, 5 descrittori). Ora
>    `fstat` si fa sul descrittore grezzo, che si chiude a ogni errore finché il file non lo possiede.
>
> In più: la descrizione di `utils backup-cli` nel catalogo dice il comportamento nuovo.
>
> **Verdi** (corsia 6187, `nice -n 10`, uno alla volta):
>
> - `services backup-archive`: 139 passati, 1 saltato;
> - `services backup-jobs`: 63;
> - `api backup-instance-errors`: 6;
> - `api backup`: 23;
> - `utils backup-cli`: 68 su 70. I 2 rossi fissano le due scelte qui sopra (successo dopo l'arrivo; controllo sulla
>   cartella esistente). test-author li aggiorna e aggiunge il test di regressione del descrittore.
>
> Porta 6187 libera.
>
> **Seconda tornata di test-author** (16:00): i due test aggiornati alle scelte.
>
> - Il test delle cartelle usa due livelli mancanti (`nas/2026/10`), così si prova anche l'ordine dal più profondo.
>   Fissa il messaggio esatto dello spazio, misurato su `nas`.
> - Nuovo `test_a_file_refused_before_its_entry_starts_leaves_no_descriptor_open[folder|fifo]`: 16 chiamate, nessun
>   descrittore aperto, cercato per dispositivo e inode in `/dev/fd`.
> - 7 mutazioni rosse, file ripristinati con lo stesso sha256.
> - In più aggiorno le descrizioni di `services backup-archive` e `services backup-jobs` nel catalogo (righe di B1).
>
> **Verifica finale** (16:07-16:12, corsia 6187, `nice -n 10`, uno alla volta), tutto verde:
>
> - `utils backup-cli` 70; `services backup-archive` 141 più 1 saltato (nomi non UTF-8, che macOS rifiuta);
>   `services backup-jobs` 63; `api backup-instance-errors` 6; `api backup` 23; `utils dev-cli-image` 48;
>   `services config-package` 602;
> - `check-orphans`: 281 test backend, 379 unitari e 118 spec E2E del frontend, tutti raggiungibili da un `all`;
> - Vitest, rilanciati da me: `backupApi.test.ts` 51, `backupJob.test.ts` 131, `BackupDownloadCard.test.ts` 51. I due
>   ultimi passati da Prettier: solo formato, poi di nuovo verdi;
> - ruff e black puliti sui 13 file Python; Prettier pulito; `theme-roles.mjs --check` pulito; `i18n check` strict;
>   `git diff --check` pulito; porta 6187 libera.

### Checkpoint B1-fix + B6a + B5a 🧊 (2026-10-15, 16:15) — committato

> Handoff inviato. Quattro commit proposti, su percorsi disgiunti:
>
> 1. **`fix(backup): keep the archive safe when --output fails, stop on a partial entry`**:
>    - `scripts/backup_cli.py`;
>    - `backend/app/api/v1/backup/instance.py`;
>    - `backend/app/services/platform/instance_backup/{archive,jobs,paths}.py`;
>    - i test `test_backup_archive.py`, `test_backup_jobs.py`, `test_backup_cli.py` e il nuovo
>      `test_api/test_backup_instance_errors.py`;
>    - nel catalogo, `_backend_api.py` (+18), `_backend_services.py` e `_backend_utils.py` (solo descrizioni).
> 2. **`docs(admin): document dev.py backup`**: `mkdocs_src/docs/admin/cli_tools.en.md`.
> 3. **`feat(backup): add the Backup card for administrators`**:
>    - `frontend/src/lib/features/backup/` (7 file), `frontend/src/lib/i18n/backup/` (5 file);
>    - `scripts/test_runner/_frontend_utility.py` (+3).
>
>    La scheda non si vede finché non c'è la riga nel registro di A, dopo A5.
> 4. **`docs(journal): B1 fixes, B6a, B5a`**: questo piano e la sezione B del backlog (B-4…B-8).
>
> Fuori: i file generati e ignorati (client API, catalogo i18n, `mkdocs_src/site/`), `.testLog/` e i log in `/tmp`.

> **Committato dal coordinatore** (16:13): `2d3480b4b` (fix), `68d382586` (doc), `3bd729c38` (scheda), `89a486ec5`
> (journal).

### Aggiornamento di base — merge di `dev_release2` (2026-10-15, 16:13-16:26) ✅

> **Merge aperto dal coordinatore**: HEAD `89a486ec5`, `MERGE_HEAD` `9c82a731e`. La base porta H CP6, X FE5b, E1, Y1,
> A5, i lotti di H (CP7a, C-96, filtro del log, G-10), Z1 e i commit del programma colori.
>
> **6 conflitti, risolti tenendo i due lati** (script con un'asserzione per blocco):
>
> - `_backend_api.py`: `instance-block` di H, poi la mia voce `backup` (la base aveva ancora «Placeholder endpoints»),
>   poi `backup-instance-errors`.
> - `_backend_services.py`: le funzioni e le voci `backup-archive` e `backup-jobs` più `logging-access-filter` di H.
> - `_frontend_utility.py` (file del programma colori): le 7 righe unitarie e le 2 di componente della base, poi le
>   mie 2 e 1.
> - `BACKLOG_POST_1.2.md`: la frase d'apertura del coordinatore, poi le mie righe B-1…B-8.
> - `cli_tools.en.md`: il suggerimento Docker di H (`./dev.py docker exec` come utente del server, con gosu) più la mia
>   frase sul backup. La mia sezione «Back Up with Docker» resta giusta: un `docker compose exec` semplice gira ancora
>   come root.
> - `test_dev_cli_image.py`: i miei IMG-013/013b/014/014b diventano **IMG-025/025b/026/026b**.
>   - La serie è unica fra `test_dev_cli_image.py` e `test_dev_cli_docker.py`: quello di H (CP7a) dice «the series
>     continues» e usa IMG-013…024.
>   - Gli IMG-013…016 di A si scontrano con quelli di H; il coordinatore li risolve con A.
>
> **Verifiche prima dello stage**: nessun marcatore; i file Python compilano; il registro del runner si carica senza
> nomi doppi; `diff --cached --check` pulito; stage dei soli 6 file.
>
> **Merge committato dal coordinatore**: `dfd1c1ea2`, genitori `89a486ec5` e `9c82a731e`.
>
> **Cancelli sulla revisione combinata** (16:18-16:26, corsia 6187, `nice -n 10`, uno alla volta), tutti verdi:
>
> - `api sync` 0; `front check` 0 errori e 0 avvisi;
> - `api backup` 23 (il backend della corsia ci ha messo circa 180 s a partire); `api backup-instance-errors` 6;
> - `utils backup-cli` 70; `utils dev-cli-image` 75, con i casi di A e i miei IMG-025/026;
> - `services backup-archive` 141 più 1 saltato; `services backup-jobs` 63; `services config-package` 649;
> - `mkdocs build` senza avvisi; `check-links` 95 link validi;
> - porta 6187 libera.

### Due cambi dichiarati dopo il merge (2026-10-15, 16:27-17:03) ✅ — committati

> **1. La riga della scheda Backup nel registro di A** (via del coordinatore, «una riga in aggiunta, dichiarata»):
>
> - `settingsTabs.ts`: l'import di `DatabaseBackup` e di `BackupTab`, e la riga `{id: 'backup', labelKey:
>   'backup.tab', icon: DatabaseBackup, order: 120, component: BackupTab, visible: (ctx) => ctx.isSuperuser}`, col
>   commento.
> - `settingsTabs.test.ts`: A5 non ha portato una colonna di visibilità, quindi la aggiungo io, in modo meccanico:
>   - `bodies.backup` e il suo `vi.mock`;
>   - la riga di `TODAY` con `adminOnly: true`;
>   - il caso per contesto si aspetta `TODAY.filter((tab) => !tab.adminOnly || ctx.isSuperuser)`;
>   - titoli e docstring aggiornati.
>
>   Verde: 17 test.
>
> **2. CP6: il backup completo su un'istanza bloccata** (decisione 12):
>
> - `instance_block.py`: le 4 rotte del backup dell'admin (avvio, stato, file, cancellazione) in
>   `ALLOWED_WHEN_BLOCKED`, con un commento; la docstring del modulo dice che ci sono. Sono 4 righe e non una: black
>   apre comunque un elemento per riga.
> - `InstanceBlockResponse.backup_available: bool`, obbligatorio, riempito in `system/block.py` con
>   `current_user.is_superuser`.
> - `test_instance_block.py`, in modo meccanico: `ALLOWED_ROUTES` +4; il JSON esatto della pagina di blocco per un
>   utente normale (+`backup_available: false`, anche nel test dal vivo sulla corsia); il perno OpenAPI (proprietà e
>   `required`). Verde: `api instance-block` 44.
> - L'app si importa senza cicli; l'elenco consentito ha 14 voci.
> - Il frontend di H (`InstanceBlockedPage`) usa un suo tipo strutturale `{blocked, deletion_date?}`, quindi il campo
>   nuovo non lo rompe. Mostrare la mia `BackupDownloadCard` sulla pagina di blocco quando `backup_available` è vero
>   resta un lavoro di H, da proporre.
>
> **Test nuovi** ✅ (test-author, 16:35-16:55), solo in aggiunta e nello stile dei due file:
>
> - `settingsTabs.test.ts`: «backup is for administrators only», cioè non visibile all'utente, visibile all'admin,
>   senza `props` né `alignEnd`, subito dopo «admin».
> - `test_instance_block.py`, sottosezione nuova «(a) Blocked: the full backup, for administrators only»:
>   - la fixture `administrator`, creata dal livello dei servizi e cancellata alla fine;
>   - un servizio di backup finto nel processo, con una precondizione che impedisce un backup vero sulla corsia;
>   - un admin su un'istanza bloccata: avvio 202, stato 200 done, file 200 con gli stessi byte, cancellazione 204, e
>     `/system/block` con `backup_available: true`;
>   - un utente normale: 403 «Admin access required» sulle 4 rotte, mai 423, e nessuna chiamata al servizio;
>   - tutti e due i test controllano prima che `GET /brokers` risponda 423 con la stessa sessione.
> - **Mutazioni rosse**, file ripristinati con lo stesso sha256: `visible` tolto; `visible: () => true`; `order: 25`;
>   una rotta tolta da `ALLOWED_WHEN_BLOCKED` (3 rossi); `backup_available=True` per tutti (12 rossi);
>   `require_admin` tolto dallo scaricamento (1 rosso). Prima, nessun test avrebbe visto un utente normale scaricare
>   l'archivio dell'istanza su un'istanza bloccata.
> - In `/tmp/librefolio-r13-b/backups/.jobs` c'è sempre solo `.lock`, con la stessa data di modifica: nessun backup
>   vero.
>
> **Verifica dei due cambi** (16:55-17:02, corsia 6187, `nice -n 10`, uno alla volta), tutto verde:
>
> - `api sync` 0: il client generato ha `backup_available: z.boolean()`;
> - `front check` 0 errori e 0 avvisi;
> - Vitest: `settingsTabs.test.ts` 18; `InstanceBlockedPage.test.ts` 14 e `instanceBlock.test.ts` 21, di H;
> - `api instance-block` 46; `api system` 117;
> - ruff, black e Prettier puliti; `git diff --check` pulito; porta libera.
>
> **devWiki**: F-073 aggiornato con la scheda (B5a), le rotte consentite sull'istanza bloccata e le righe dei file.
> `check_source_paths` non ha percorsi nuovi mancanti.
>
> **Commit proposti**, su percorsi disgiunti:
>
> 1. `feat(settings): show the Backup tab to administrators`: `settingsTabs.ts`, `settingsTabs.test.ts`.
> 2. `feat(platform): keep the full backup on a blocked instance`: `api/v1/instance_block.py`, `api/v1/system/block.py`,
>    `schemas/system.py`, `test_api/test_instance_block.py`.
> 3. `docs(journal): merge validation, Backup tab, blocked-instance backup`: questo piano e `features/F-073.md`.
>
> **Prossimi, col via del coordinatore**:
>
> - l'E2E della scheda e knip (slot);
> - la galleria (G);
> - la scheda di backup sulla pagina di blocco, quando `backup_available` è vero (frontend di H);
> - B2, B4, B7 come da decisioni.

> **Committati dal coordinatore** (17:04): `b7a4d35e6` (scheda), `f43d5de89` (CP6), `e1858d277` (journal).

### Base `a22400f1e` e decisioni 38–39 (2026-10-15, dalle 17:04)

> **Base aggiornata dal coordinatore**: merge di `dev_release2` (`d22eb6f43`) senza conflitti, HEAD `a22400f1e`.
> Entrano W (eventi e conversione), J (C-94: il server di prova fa la build prima del timeout) e i colori.
>
> **Prove sulla revisione combinata** (17:05-17:14, `nice -n 10`, uno alla volta), tutte verdi:
>
> - `api sync` 0; `front check` 0 errori e 0 avvisi;
> - `api instance-block` 46 (backend della corsia partito in circa 270 s, carico 98); `api backup` 23;
>   `api backup-instance-errors` 6;
> - Vitest `settingsTabs` 18; `check-orphans` verde; porta libera.
>
> **Decisioni del developer**, alla lettera, dal treno 41 del piano generale:
>
> - **38**: «ok all'idea della busta» (`.lfbk`, scrypt + AES-256-GCM, solo `cryptography`).
> - **39**: «così l'utente sceglie se fare un backup in "chiaro" o un backup "sicuro" e nel messaggio gli viene detto
>   la differenza».
> - **B4 dopo B3 e B5**: è l'unico pezzo di B che può slittare.
> - **40**: il developer ci sta ragionando (coordinatore, 17:04).
>
> **Chiarito dal coordinatore** (17:14):
>
> - l'estensione è **`.lfbk`**: è l'ultima parola del developer (17:00), nella riga «Decisione» del punto 38. Il testo
>   del punto e la nota del treno 41 sono di prima, e la nota la corregge il coordinatore;
> - **40–43 non sono decise**: 🟢 è il colore della proposta, una decisione ha la riga «Decisione (data)». Il
>   developer è sulla 40, poi va in ordine. Restano fermi B2 (42 e 43) e B3 (40, 41 e CP2b di H).
>
> **Cosa vuol dire per B4** (coordinatore, 18:09):
>
> - Password facoltativa: con la password la busta cifrata (scrypt + AES-256-GCM, `cryptography`, nessuna dipendenza
>   nuova). La chiave d'istanza entra solo con la password, e solo se l'ha generata LibreFolio.
> - Al ripristino l'istanza tiene la sua chiave e ricifra i segreti dei plugin con il `rekey` del CP10 di X (in corso);
>   se manca la chiave vecchia, «impostato ma illeggibile».
> - **Nella scheda**, la scelta fra backup «in chiaro» e «sicuro», con la differenza spiegata:
>   - in chiaro: chi ha il file vede tutti i dati; su un'altra istanza le chiavi dei fornitori vanno reinserite;
>   - sicuro: serve la password per aprirlo, e se si perde non si recupera; porta con sé anche le chiavi dei fornitori.
> - **Ordine**: B4 dopo B3 e dopo la scheda; se a fine release manca tempo, è l'unico pezzo che slitta.
> - **Estensione: `.lfbk`**, riconfermata dal coordinatore (18:11). Il messaggio con `.lfbackup` era di prima della
>   scelta del developer, ed è arrivato in ritardo dalla coda.
>
> **Slot pesante 1**: dopo `all-backend` di H. In attesa, test-author scrive l'E2E della scheda
> (`frontend/e2e/settings/backup.spec.ts`, FBKP-001…004) e la sua riga in `_frontend_utility.py`, file del programma
> colori che il coordinatore dichiara. Nello slot: l'E2E, poi knip. La galleria la chiede il coordinatore ai colori,
> dopo Y2. La scheda sulla pagina di blocco il coordinatore la propone ad H.

### B8 — il token del pannello (via del coordinatore, 2026-10-15 alle 17:15) — messo da parte alle 17:22, continua sotto; in dev `56d3d3182`

> **Via**: «B8: via». Le rotte del pannello vanno in `ALLOWED_WHEN_BLOCKED`: un'istanza bloccata, per esempio per un
> mancato pagamento, e chi ospita che restituisce i dati al cliente. Le rotte sono autenticate dal token, non da una
> sessione. Il test fissa che sull'istanza bloccata, senza token o con un token sbagliato, la risposta resta 404 o 401,
> mai il file. Da dichiarare: la riga di `ALLOWED_WHEN_BLOCKED` e `test_instance_block.py`, file di H.
>
> **B7a: non adesso**. Le build Docker qui non riescono per la VPN; prima viene il CP7b di H (`Dockerfile`, compose),
> poi B7a sopra la sua base, con le prove Docker in una finestra del developer. `stop_grace_period` (Z6b, 10 s) resta
> ad H.
>
> **Disegno e codice** (17:17-17:21):
>
> - `config/backup.py` (sezione nuova): `backup_download_token()` con `env_secret("LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN")`,
>   quindi anche `_FILE`; almeno 32 caratteri, altrimenti `BackupConfigError`.
> - `api/v1/backup/job_views.py`: vista del job, errori, avvio, lettura, file e cancellazione, condivisi fra le rotte
>   dell'admin e quelle del pannello. Un chiamante limitato a un'origine vede solo i suoi job.
> - `api/v1/backup/panel.py`: `POST /backup/panel/jobs`, `GET` e `DELETE /backup/panel/jobs/{id}`,
>   `GET …/{id}/file`.
>   - `HTTPBearer` (schema `BackupPanelToken`) e `hmac.compare_digest`.
>   - Le risposte: token non impostato → 404 «Not Found» (come un percorso che non c'è); token mancante o sbagliato →
>     401 `backup_panel_unauthorized`; token inutilizzabile (file illeggibile, troppo corto) → 503
>     `backup_panel_unavailable`, con una riga di log; un job di un'altra origine → 404.
>   - Origine `panel`; mai la chiave d'istanza.
> - `instance.py` passa a `job_views`: stessi nomi, docstring e risposte. L'OpenAPI dei 6 percorsi di backup è
>   identico; si aggiungono solo i 3 percorsi (4 operazioni) del pannello.
> - `.env.example`, la mia sezione: `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN` e `_FILE`, commentate.
> - `instance_block.py` (di H, dichiarato): le 4 rotte del pannello in `ALLOWED_WHEN_BLOCKED`.
> - I perni, in modo meccanico: `ALLOWED_ROUTES` +4 in `test_instance_block.py`; `BACKUP_ROUTES` +4 in
>   `test_backup_api.py`.
> - **Smoke** in un processo, su una piccola app con i job finti: tutte e nove le risposte come previsto (non impostato
>   404; senza header 401 con `WWW-Authenticate: Bearer`; sbagliato 401; avvio 202; stato 200; file 200 `no-store`; job
>   dell'admin dal pannello 404; cancellazione 204; token corto 503; file illeggibile 503).
>
> **⚠️ Fuori pista — B8 messo da parte per lo slot** (17:22): alle 17:21 il coordinatore dà lo slot pesante 1
> sulla revisione `a22400f1e`.
>
> - Per provare esattamente quella revisione, i 9 file di B8 vanno in
>   `~/.copilot/session-state/5618ecee-…/files/b8-wip/`, con `MANIFEST.sha256`, `MODIFIED.txt` e `NEW.txt`.
> - I 6 file modificati tornano al contenuto di HEAD (`git show HEAD:<file>`); i 3 nuovi vengono tolti.
> - Si rimettono dopo lo slot, controllati con lo sha256.

### Slot pesante 1 — E2E della scheda e knip (2026-10-15, 17:21-17:51) ✅ — committato

> - **knip** (`dev.py lint --dead-code --scope frontend`, 17:23, 9 s): nessun file di B fra i risultati
>   (`features/backup`, `i18n/backup`, `settingsTabs`). I 2 file, 19 export, 28 tipi, 4 dipendenze di sviluppo e 20
>   dipendenze non elencate sono di altre aree (codice di uscita 1 per quelli).
> - **E2E** `frontend/e2e/settings/backup.spec.ts` (test-author), solo desktop come ogni spec seriale, `mode: 'serial'`
>   (un backup alla volta per istanza):
>   - FBKP-001: un utente normale non ha la scheda, e `?tab=backup` apre la prima;
>   - FBKP-001b: l'admin la ha, e la scheda si apre `idle`;
>   - FBKP-002: backup fino a `done`; `backup.created` con l'id del POST; il link al file del job con l'attributo
>     `download`; lo scaricamento è uno zip (`PK\x03\x04`) grande quanto `file_size`, col nome del job;
>     `backup.download.started`;
>   - FBKP-003: la cancellazione torna a `idle`, `backup.deleted`, e il GET del job risponde 404;
>   - FBKP-004: un ricaricamento riprende il job finito senza un secondo `backup.created`;
>   - pulizia dopo ogni test: ogni job cancellato, l'id seguito tolto da `sessionStorage`.
>
>   Registrata in `_frontend_utility.py`: `front_backup` e la voce `front-utility backup`, +20 righe in aggiunta, file
>   del programma colori dichiarato dal coordinatore. `front_utility_all` la prende dal registro.
> - **Prove** (`front-utility backup`, `nice -n 10`, una alla volta):
>   - codice committato: 5 passati (Playwright 30 s, build già aggiornata);
>   - mutazione 1, l'attributo `download` tolto: FBKP-002 rosso;
>   - mutazione 2, `remove()` che non chiama l'API: FBKP-003 rosso, perché il job risponde ancora 200;
>   - di nuovo il codice ripristinato: 5 passati (Playwright 37 s; ricostruzione della build circa 130-155 s a ogni
>     cambio);
>   - sha256 identici, `git diff HEAD -- frontend/src` vuoto; in `.jobs` solo `.lock` dopo ogni corsa; porta libera.
> - `check-orphans`: 124 spec E2E e 413 test unitari raggiungibili.
> - **Da sapere** (test-author): il runner ricostruisce il frontend solo se un file di `src` è più nuovo di
>   `build/index.html`. Un ripristino che rimette anche la data del file (`cp -p`) salta la ricostruzione, e la «prova
>   verde finale» girerebbe sulla build mutata. Proposto per la devWiki.
> - Rumore d'ambiente, non del prodotto: a ogni corsa la cache statica non scarica MathJax da jsDelivr (certificato SSL)
>   e tiene la copia in cache.

> **Committato dal coordinatore** (17:52): `d7b57002a` (test E2E) e `c24466527` (journal). **⚠️ Fuori pista — orario
> sbagliato**: nel journal e nell'handoff avevo scritto che lo slot si era liberato «alle 18:20». È andato dalle 17:21
> alle 17:51: lo dicono i log (knip 17:23, `check-orphans` 17:50). Il titolo è corretto qui sopra.

### Accordo con H sui passi d'avvio di CP2b (2026-10-15, 17:48)

> H, su richiesta del coordinatore: con CP2b i passi d'avvio escono da `main.py` e vanno in
> `services/platform/app_lifespan.py`, nella tupla ordinata `STARTUP_STEPS` (`Step(name, run, blocking=False)` di
> `services/platform/lifecycle.py`). `run()` restituisce `None` o un awaitable; un'eccezione ferma l'avvio. H proponeva
> un passo subito prima del DB.
>
> **Risposta di B**: i passi sono due.
>
> - **`pending-restore`** (`asyncio.to_thread(apply_pending_restore)`) va prima del primo passo che tocca la cartella
>   dati, cioè subito prima di `ensure_data_dirs()`:
>   - il catalogo degli scenari carica `scenario_catalog/` in memoria;
>   - gli avatar scrivono in `custom-uploads/`;
>   - audit, segnali e Tool possono restare prima: toccano solo `logs/` e `secrets/`, che non si scambiano.
> - **`restore-commit`** (`asyncio.to_thread(commit_restore)`) va dopo DB, fix post-migrazione e impostazioni globali,
>   e prima di prewarm, festività e scheduler.
> - Le righe le aggiungo io, in B3, quando CP2b è nella mia base.
> - Nessun passo di spegnimento: il riavvio è un SIGTERM, e Litestream avvolge uvicorn da fuori.
> - Ho chiesto ad H che cosa cambia fra `blocking=True` e `blocking=False`.
>
> **Conferma di H** (17:50):
>
> - CP2b non cambia l'ordine dei passi. `pending-restore` va fra `Step("tool-catalog", …)` e
>   `Step("data-directories", …)`; `restore-commit` fra `Step("global-settings", …)` e `Step("provider-prewarm", …)`.
> - `blocking` all'avvio non cambia niente: `run_startup_steps` attende la coroutine, e un'eccezione ferma l'avvio.
>   `blocking=True` conta solo allo spegnimento con una scadenza. Quindi il default, con lambda `asyncio.to_thread`,
>   come il suo `post-migration-fixes`.
> - Il test puro `services app-lifecycle` fissa solo l'ordine relativo dei passi di oggi e i nomi unici. I miei due
>   vincoli vanno in una funzione di test mia. H manda il nome del file e lo SHA quando CP2b entra.

### Aggiornamento di base — merge di `dev_release2` `9c8ee20c3` (2026-10-15, 17:52-17:55) ✅

> **Merge aperto dal coordinatore**: HEAD `c24466527`, `MERGE_HEAD` `9c8ee20c3`. La base porta H (fatturazione e rotte
> dei link), A6a, Z7a, J e il banner del Lab.
>
> **6 file in conflitto**, risolti tenendo i due lati:
>
> - `instance_block.py`: in `ALLOWED_WHEN_BLOCKED` 17 voci, ogni gruppo col suo commento: i link di H, la cancellazione
>   del proprio account con l'anteprima di A6a, le mie 4 rotte di backup, la pagina di blocco, le sonde. La docstring
>   tiene il testo di H, sonda dell'indirizzo compresa, più la frase sul backup.
> - `system/block.py` e `schemas/system.py`: `billing_url` (H, solo per l'admin, facoltativo) e `backup_available` (B,
>   obbligatorio).
> - `test_instance_block.py`: `ALLOWED_ROUTES` con 17 voci; i due campi in ogni JSON esatto; il perno OpenAPI con le
>   quattro proprietà, `required` = `[blocked, backup_available]`; import e docstring uniti.
> - `test_dev_cli_image.py`: gli IMG-027…030 di A (rinumerati) e i miei IMG-025/026, in una serie unica.
> - `backend.instructions.md`: le righe di `platform/` unite (provider pauses di Z7a e le mie).
>
> **⚠️ Fuori pista — due problemi che git non vedeva**, corretti nello stesso stage:
>
> 1. **Fixture `administrator` doppia**, quella di H per la fatturazione e la mia per il backup: in Python la seconda
>    sostituiva la prima in silenzio. Tolta la mia: i casi di backup usano quella di H, che controlla anche il ruolo con
>    `/auth/me`.
> 2. **Perni del JSON della pagina di blocco**: 4 perni uniti senza conflitto avevano uno solo dei due campi (3 di H,
>    1 mio). Ora li hanno tutti e due, con `backup_available` vero solo per l'admin. Il mio caso di backup toglie
>    esplicitamente `LIBREFOLIO_BILLING_URL` invece di darlo per assente.
>
> Verifiche: nessun marcatore; compilazione; ruff e black puliti; `diff --cached --check` pulito; stage dei soli 6 file.
> **Merge committato dal coordinatore**: `25cd742cf`, genitori `c24466527` e `9c8ee20c3`.
>
> **Prove sulla revisione combinata `25cd742cf`** (17:56-18:09, corsia 6187, `nice -n 10`, una alla volta), tutte
> verdi:
>
> - `api sync` 0; `front check` 0 errori e 0 avvisi;
> - `api instance-block` 56 (i casi di fatturazione e dei link di H più i miei di backup; il backend della corsia ci ha
>   messo circa 225 s a partire); `api backup` 23; `api backup-instance-errors` 6;
> - `utils dev-cli-image` 75; `services backup-archive` 141 più 1 saltato; `services backup-jobs` 63;
> - `check-orphans` verde; Vitest `settingsTabs` 18 e `InstanceBlockedPage` 22;
> - porta libera.
>
> **devWiki**: la lezione di `cp -p` va in `problems/mutation-restore-keeps-old-mtime-skips-frontend-rebuild.md`, con
> la riga in `index.md` e la voce in `log.md`. `check_source_paths` torna ai 5 percorsi mancanti di prima, tutti in
> altre pagine. Una prima stesura citava `build/index.html`, che non esiste nel repo.
>
> **B8 dopo il merge**: le copie messe da parte sono su `a22400f1e`, quindi B8 si rimette come patch
> (`files/b8-wip/b8.patch`, 9 file, 502 righe), non come copia, che cancellerebbe il merge. I 9 file di riserva sono
> controllati col manifest.

### Ingresso — journal e `all-backend` (2026-10-15, 18:10-18:37) ✅

> - **Journal committato dal coordinatore**: `23d284d3b`. La simulazione dell'ingresso sopra `dev_release2` attuale
>   (`695e6ad12`, con Y2) è pulita.
> - **Slot pesante 1 a B per `all-backend`** prima dell'ingresso: `--workers 2`, `nice -n 10`, corsia 6187, revisione
>   `23d284d3b`. Dopo tocca a E. B8 si rimette dopo `all-backend`, non durante.
> - Comando: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc nice -n 10 pipenv run python dev.py test --test-port 6187
>   --data-dir /tmp/librefolio-r13-b --workers 2 all-backend`, dalle 18:10:16 alle 18:36:24 (26 minuti, carico
>   iniziale 44); log in `/tmp/libreFolio_b_all_backend.log`.
> - **Esito: 7/7 categorie verdi** (External, DB, Services, Utils, Schema, API, E2E); **16 455 passati, 29 saltati,
>   0 falliti**:
>   - 4 passate parallele (133, 47, 11 e 62 unità, 2 worker): 14 337 passati e 4 saltati;
>   - sessioni sequenziali e consolidate: 2 118 passati e 25 saltati (25 riepiloghi pytest); il DB 17/17.
> - Dopo: porta 6187 libera; in `backups/.jobs` solo `.lock`. Slot liberato e risultato mandato al coordinatore alle
>   18:37; dopo B tocca a E.

### Ingresso fermato — E2 in `dev_release2`, merge di base prima di B8 (2026-10-15, dalle 18:38)

> **⚠️ Fuori pista — B8 rimesso, poi di nuovo da parte** (18:37-18:40):
>
> - Dopo `all-backend`, B8 rimesso come patch (`git apply --reject` di `files/b8-wip/b8.patch` su `23d284d3b`): 8
>   file su 9 entrano con un offset; un frammento respinto, la docstring di `instance_block.py`, che il merge
>   `9c8ee20c3` aveva riscritto (link di H, anteprima di A6a). Riscritto a mano sul testo nuovo: «the full backup of an
>   administrator or of the hosting panel … the panel's routes want its token, not a session». Ruff pulito.
> - Poi il fermo del coordinatore: in `dev_release2` (`bcd680868`) è entrato E2, e l'ingresso di B ha 4 conflitti
>   (`settingsTabs.ts`, `settingsTabs.test.ts`, `_frontend_utility.py`, `LibreFolio_devWiki/log.md`). Prima di B8
>   serve un merge di base.
> - **B8 di nuovo da parte**, come patch sulla revisione attuale: `files/b8-wip/b8-on-23d284d3b.patch` (9 file, 526
>   righe, con la docstring già fusa) e `MANIFEST-23d284d3b.sha256`. Tolto con `git apply -R` (prima `--check`), poi
>   verificato: nel worktree resta solo il piano; la patch rientra pulita su HEAD (`git apply --check`);
>   `git diff --check` pulito. La vecchia `b8.patch` (su `a22400f1e`) resta come storia.
>
> **I passi del coordinatore**:
>
> 1. Commit del piano 07 (`docs(journal): all-backend green, B4 notes`).
> 2. Merge di `dev_release2`; B risolve tenendo i due lati:
>    - `settingsTabs.ts`: la riga Backup (120) e quella Email (130) di E;
>    - `settingsTabs.test.ts`: `TODAY`, le schede attese per contesto, i mock di Backup e di Email, i casi per la
>      visibilità solo admin;
>    - `_frontend_utility.py`: la voce `backup` e la voce `email-tab` di E, più le righe di W;
>    - `log.md`: tutte e due le righe.
> 3. Sulla revisione combinata: Vitest `settingsTabs` e `page.tabs` (le schede finte sul registro vero: E-6),
>    `front check`, `check-orphans`, poi l'E2E `front-utility backup` da sola (una scheda in più nella barra).
> 4. Poi B8 dalla patch, i suoi test e il FROZEN.

### Aggiornamento di base — merge di `dev_release2` `bcd680868`, con E2 (2026-10-15, 18:42-19:05) ✅ — committato

> - **Piano committato dal coordinatore**: `ddf0c4035` (`docs(journal): all-backend green, B4 notes`). Merge aperto
>   da lui: `MERGE_HEAD` `bcd680868`, con E2 (la scheda Email) e W (il salvataggio degli eventi).
> - **Correzione della 38**, dal developer (coordinatore, 18:40): «come formato facciamo lfbk, mi piace di più».
>   Nel piano passano a `.lfbk` il §3.1, il §3.3, il D-B1 e la nota della 38; `dev.py backup decrypt`, test e doc
>   quando arriva B4.
>
> **4 conflitti, risolti tenendo i due lati** (18:42-18:58). Ho usato lo script `/tmp/libreFolio_b_resolve_e2.py`,
> che controlla ogni lato sul testo letto prima di scrivere. Le copie con i marcatori sono in
> `/tmp/libreFolio_b_merge_bcd680868_conflicted/`.
>
> - `settingsTabs.ts`:
>   - l'import delle icone di ciascun ramo, com'è: il mio con `DatabaseBackup`, quello di E con `Mail` a parte, così
>     un cambio futuro di E non fa conflitto;
>   - i due corpi;
>   - le righe Backup (120) ed Email (130), con i loro commenti.
> - `settingsTabs.test.ts`:
>   - import, `bodies`, `vi.mock` e righe di `TODAY` per Backup ed Email;
>   - le liste esplicite per contesto di E (`CONTEXTS`, entrate col merge automatico), con `backup` nella lista
>     dell'amministratore;
>   - il nome generico del caso del registro (mio);
>   - i due casi della visibilità solo admin, Backup ed Email.
>
>   **Colonna `adminOnly` tolta**: le liste di E fissano la stessa cosa, chi vede cosa e in che ordine. Allineata
>   l'intestazione: backup ed email sono per gli amministratori, e una scheda nuova aggiunge la sua riga a `TODAY` e il
>   suo id alle liste di `CONTEXTS`.
> - `_frontend_utility.py` (file del programma colori). Quello che c'è già in `dev_release2` resta al suo posto, e le
>   righe di B vengono dopo quelle di E:
>   - liste Vitest di `core-unit`: `emailText` ed `emailApi`, poi `backupApi` e `backupJob`;
>   - funzioni: `front_email_tab`, poi `front_backup`;
>   - voci del catalogo: `email-tab`, poi `backup`.
>
>   Le righe di W (`eventSaveError`, `EventExistsPanel`) e le descrizioni di `core-unit` e `component-unit` arrivano
>   dal merge automatico.
> - `LibreFolio_devWiki/log.md`: la voce di W, che è già in `dev_release2`, poi la mia.
> - **Verifica**:
>   - contro `MERGE_HEAD` cambiano solo le mie righe; contro `HEAD` solo quelle di E e W;
>   - prettier, ruff, black e `git diff --check` puliti;
>   - `git add` dei soli 4 file.
>
> **⚠️ Fuori pista — `page.tabs.test.ts` rosso sul mio ramo da `b7a4d35e6`** (il caso previsto da E-6):
>
> - Il test carica il registro vero con `importOriginal`, quindi tutti i corpi di scheda. E ha aggiunto il mock di
>   `EmailSettingsTab`; quello di `BackupTab` non c'era.
> - Senza il mock il file non si carica: la catena `BackupDownloadCard` → `formatDateTime` → `stores/app/language.ts`
>   chiede `DEFAULT_LOCALE` al mock parziale di `$lib/i18n`.
> - Il rosso è mio, non del merge: è nato con la riga della scheda (`b7a4d35e6`), che avevo validato solo con Vitest
>   `settingsTabs`. Il merge non tocca né la catena del backup né questo test.
> - Cura: una riga, `vi.mock('$lib/features/backup/BackupTab.svelte', …)` dopo quella di E (il modello di E-6). **Non
>   è nell'indice**: il coordinatore decide se va nel merge o in un commit a parte.
> - Prove sul worktree del merge (Vitest, `nice -n 10`):
>   - `page.tabs` senza la riga: file non caricato; con la riga, 18 su 18;
>   - `settingsTabs`: 20 su 20.
>
> **Dopo il commit del merge**, sulla revisione combinata, una prova alla volta:
>
> - Vitest `settingsTabs` e `page.tabs`;
> - `front check`;
> - `check-orphans`;
> - E2E `front-utility backup` da sola;
> - `front-utility core-unit`, nello slot 1. Rosso noto e accettato: `htmlInterpolation.gate.test.ts` sulla chiave
>   `email.problems.SMTP_FROM_INVALID`, che E sta correggendo.
>
> **Committato dal coordinatore** (18:54):
>
> - il merge `b1f5b0fd1` (genitori `ddf0c4035` e `bcd680868`), con dentro la riga di `page.tabs.test.ts`: per lui è
>   una correzione di significato del merge;
> - il piano in `ef61f0e7f`;
> - togliere `adminOnly` va bene: le liste per contesto di E fissano la stessa cosa.
>
> **Prove sulla revisione combinata `ef61f0e7f`** (18:55-19:05, `nice -n 10`, una alla volta; log in
> `/tmp/libreFolio_b_post_b1f5_*.log`):
>
> - Vitest `settingsTabs` 20/20 e `page.tabs` 18/18.
> - `api sync` 0, poi `front check` 0 errori e 0 avvisi. Il sync va prima perché il client generato è ignorato e il
>   merge porta le rotte email di E.
> - `check-orphans` verde: 127 E2E, 418 Vitest, 311 backend.
> - E2E `front-utility backup` 5/5 (FBKP-001…004), con la scheda Email nella barra; 4 min 30 s, avvio della corsia
>   compreso (carico 37).
> - `front-utility core-unit` (slot 1): 5 046 passati e 1 rosso, quello noto: `htmlInterpolation.gate`, perché
>   `email.problems.SMTP_FROM_INVALID` contiene `<` nei 4 cataloghi. La correzione di E (`be7de95b6`) è fuori dalla mia
>   base. File: 154 su 155.
> - Porta 6187 libera; in `.jobs` solo `.lock`; worktree pulito. Slot 1 liberato alle 19:05 (dopo B tocca a J).
>
> **B è entrato** (coordinatore, dopo le 19:05): `dev_release2` = `629d63306`, il merge di `ef61f0e7f`. Il CHANGELOG lo
> scrive lui: in Added «Instance backup…», e fra le ⚠️ «the four placeholder backup endpoints are removed». Il mio HEAD
> non si sposta: B8 va sopra `ef61f0e7f`, e la base la aggiorna lui al checkpoint di B8.
>
> **Ordine dopo B8**, dal coordinatore:
>
> 1. lo scatto `settings/backup-ready`, con la checklist di G (lo slot della galleria lo chiede lui);
> 2. B2, la prova su copia, con le decisioni 41–43;
> 3. B3, il ripristino e l'avvio, con `pending-restore` in `lifecycle.py` dopo l'ingresso di CP2b;
> 4. B5, il resto della scheda;
> 5. B4, il backup «sicuro» `.lfbk`;
> 6. B7, Litestream, dopo CP7b di H e con il developer fuori dalla VPN.

### B8 — il token del pannello, rimesso sopra `ef61f0e7f` (2026-10-15, 19:06-20:11) ✅ — 🧊 FROZEN

> - **Rimesso**: `git apply` di `files/b8-wip/b8-on-23d284d3b.patch`, controllato prima con `--check`. Gli 8 file
>   escluso `.env.example` sono identici al manifest `MANIFEST-23d284d3b.sha256`. `.env.example` differisce solo per la
>   riga di E entrata col merge (`# Docs: mkdocs_src → admin/email.md`), fuori dal frammento di B8.
> - **OpenAPI**: `api sync`, poi confronto con quello di `ef61f0e7f` salvato prima
>   (`/tmp/libreFolio_b_openapi_pre_b8_ef61f0e7f.json`):
>   - in più solo i 3 percorsi del pannello (4 operazioni, ciascuna con `BackupPanelToken`) e lo schema di sicurezza
>     `BackupPanelToken`;
>   - nessun percorso tolto o cambiato, e i 6 dell'admin identici;
>   - in `info.version` c'è solo il suffisso `-dirty`.
> - **Statici**: ruff e black puliti sugli 8 file Python; `git diff --check` pulito.
>
>   **⚠️ Fuori pista**: il primo ruff ha letto `.env.example` come Python, perché `MODIFIED.txt` tiene i percorsi su
>   una riga sola e il filtro `\.py$` lo lasciava passare; rifatto con l'elenco a mano.
> - **`Bearer` nei file**: nell'output del terminale compare `******` al posto di `Bearer <token>`, ma è solo il
>   mascheramento dell'output. I byte di `.env.example` e di `panel.py` sono giusti; nei 9 file e nel brief non c'è
>   nessun `******` letterale.
> - **Test**: test-author in corso (dalle 19:10) con il brief v2 (`files/b8-test-brief-v2.txt`), aggiornato allo
>   stato attuale:
>   - 21 voci in `ALLOWED_ROUTES`;
>   - il servizio finto di `test_instance_block.py` fa job d'origine `ui`, quindi va un parametro facoltativo `origin`,
>     senza cambiare i test che ci sono;
>   - la sequenza delle chiamate del pannello: start, poi `get_job`, poi `job_archive` o `delete_job`;
>   - il corpo esatto del 401 del pannello, perché non passi per quello del blocco;
>   - una sessione non sostituisce il token.
>
>   Gli ho dato la corsia, un selettore alla volta: io non lancio niente finché non ha finito.
> - **Lasciati com'erano** (di H): `test_config_secrets.py`, i cui `ACCESSORS` sono solo quelli di
>   `config/platform.py`, e l'elenco dei segreti che la corsia non eredita (firma JWT e chiave d'istanza). I casi del
>   token sono nel file nuovo.
>
> **Esito di test-author** (19:10-19:43; log in `/tmp/libreFolio_b8ta_*.log`):
>
> - **⚠️ Fuori pista — B8 rompeva 2 test di CP6 in `test_instance_block.py`.** La precondizione di
>   `_replace_the_backup_service` leggeva `backup_instance.jobs`, e B8 ha portato quell'import in `job_views.py`.
>   - Base di test-author, prima di ogni sua modifica: `api instance-block` 54 passati e 2 rossi, con
>     `AttributeError: … has no attribute 'jobs'`.
>   - La mia prova di B8 era fatta su un'app piccola in un processo, senza lanciare `api instance-block`.
>   - Cura, nel file di H (da dichiarare): la precondizione diventa
>     `backup_instance.job_views.jobs is jobs and backup_panel.job_views.jobs is jobs`, il modulo che tutte e due le
>     rotte chiamano davvero.
> - **`test_backup_panel.py`**, nuovo, puro: 17 test e 42 casi, registrato come `api backup-panel` in `_backend_api.py`
>   (+19 righe, solo in aggiunta). Ogni richiesta passa da un `send()` che controlla che il token, e quello che il
>   chiamante presenta, non compaiano mai nel corpo, negli header o nel log catturato.
>   - PANEL-001…006: l'accessore. Variabile, `_FILE`, precedenza, BOM e a capo, 31 contro 32 caratteri, file mancante,
>     cartella, vuoto o bianco.
>   - PANEL-010: token non impostato → 404 «Not Found» su 4 rotte × 4 header.
>   - PANEL-011: token inutilizzabile → 503 con una riga di log che nomina la variabile.
>   - PANEL-012: 9 varianti di header sbagliato → il 401 esatto, con `WWW-Authenticate: Bearer`. Fra le varianti:
>     Basic, `Bearer` vuoto, prefisso, estensione, maiuscole, token nella query.
>   - PANEL-013/014: il ciclo completo, con le chiamate esatte; il token preso dal `_FILE`.
>   - PANEL-015/016/017: i job di un'altra origine (`ui`, `cli`, `pre-restore`) e gli id sconosciuti come «non
>     esiste»; il job in corso con 409.
>   - PANEL-018: gli errori d'avvio.
>   - PANEL-019: le rotte dell'admin con le chiamate di prima di B8, verificate su `ef61f0e7f`.
>   - PANEL-020: l'OpenAPI.
> - **`test_instance_block.py`** (di H), in aggiunta nella sezione «(a) … the full backup»:
>   - `origin` facoltativo nel servizio finto (default `ui`);
>   - 4 test sull'istanza bloccata, senza sessione: 404 senza token impostato; il 401 del pannello, che il controllo
>     del corpo esatto distingue da quello di `get_current_user`; il ciclo completo con il token; una sessione admin
>     non sostituisce il token.
>   - La barriera anonima è `GET /utilities/sectors`: 200 senza blocco, 401 col blocco.
> - **Verdi**, una alla volta:
>
>   | Selettore | Esito |
>   |---|---|
>   | `api backup-panel` | 42 |
>   | `api instance-block` | 60 (54 + 2 riparati + 4 nuovi) |
>   | `api backup` | 23 |
>   | `api backup-instance-errors` | 6 |
>   | `services config-package` | 659 |
>   | `services config-env-example` | 36 |
>   | `check-orphans` | pulito |
>
>   Porta 6187 libera.
> - **Mutazioni rosse**, ognuna ripristinata identica (sha256 e `cmp`):
>   1. `require_panel_token` tolto dalla rotta del file: 11 rossi (il file servito senza token);
>   2. `origin=None` sul download: 6 rossi (l'archivio dell'admin servito al pannello);
>   3. il ramo 404 sostituito da `""`: 3 rossi (un backup avviato senza token);
>   4. la rotta del file tolta da `ALLOWED_WHEN_BLOCKED`: 5 rossi, il perno di H compreso.
>
>   `==` al posto di `hmac.compare_digest` non si vede dai test funzionali: solo revisione del codice, come previsto.
> - **Rilievo di test-author, curato** (19:45): un token con spazi intorno passava `backup_download_token()`, ma non
>   poteva mai coincidere, perché HTTP toglie gli spazi in fondo a un header. Il pannello avrebbe preso un 401 per
>   sempre, senza niente nel log. Ho allargato la cura:
>   - in `config/backup.py`, `PANEL_TOKEN_CHARACTERS`: il token può contenere solo ASCII visibile (0x21-0x7E),
>     controllato prima della lunghezza; altrimenti `BackupConfigError` con il codice
>     `BACKUP_DOWNLOAD_TOKEN_NOT_VISIBLE_ASCII`, quindi 503 e una riga di log;
>   - copre gli spazi (intorno e dentro), i caratteri fuori ASCII e quelli di controllo;
>   - commento di `.env.example`: «At least 32 visible ASCII characters, no spaces».
>
>   test-author aggiunge i casi e la mutazione.
> - **Seconda tornata di test-author** (19:48-20:00; log `/tmp/libreFolio_b8ta_r2_*.log`), solo in
>   `test_backup_panel.py`, in aggiunta (+130 righe):
>   - PANEL-007, 10 casi: spazio davanti, dietro, tab, spazio interno, `é`, `€`, U+00A0, DEL, `\x01` su un token
>     valido di 40 caratteri, più un `_FILE` con spazi prima dell'a capo. Codice `…_NOT_VISIBLE_ASCII` e `variable`; il
>     messaggio non contiene mai il valore, né una delle sue due metà.
>   - PANEL-008: i caratteri si controllano prima della lunghezza.
>   - PANEL-009: i token ai bordi, `!`…`~`, e uno con tutti i 94 caratteri visibili, presi come scritti, dalla
>     variabile e dal file.
>   - PANEL-021: un token con spazi intorno dà 503 sulle 4 rotte anche a chi presenta quel token, con una riga di log
>     e mai il valore. Barriera: lo stesso token senza spazi apre la lettura.
>
>   Esito: `api backup-panel` 59 (42 + 17). La mutazione «controllo dei caratteri tolto» fa 13 rossi (PANEL-007 ×10,
>   PANEL-008 ×2, PANEL-021, quest'ultimo con il 401 silenzioso di prima), ed è ripristinata identica: sha256
>   `6b515315…` prima e dopo. `config-package` 659 e `config-env-example` 36.
> - La descrizione di `api backup-panel` nel catalogo nomina la regola dei caratteri (ritocco mio, segnalato da
>   test-author).
> - **Rivisto da me**: `test_backup_panel.py` è puro, con un'app piccola con `backup_router`, `jobs` finto in un
>   fixture automatico e log catturati con `structlog.testing.capture_logs`. `DATA_DIR = /srv/…` è solo una stringa
>   nelle eccezioni finte, per provare che nessun percorso esce nelle risposte, e non viene mai creata. In
>   `test_instance_block.py` le aggiunte sono quelle dichiarate.
> - **Prove finali sullo stato finale** (20:02-20:10, `/tmp/libreFolio_b8_final.sh`, una alla volta, `nice -n 10`,
>   carico 99; riepilogo in `/tmp/libreFolio_b8_final_summary.log`):
>
>   | Selettore | Esito |
>   |---|---|
>   | `api backup-panel` | 59 |
>   | `api instance-block` | 60 |
>   | `api backup` | 23 |
>   | `api backup-instance-errors` | 6 |
>   | `services config-package` | 659 |
>   | `services config-env-example` | 36 |
>   | `check-orphans` | 312 backend, 418 Vitest |
>   | `api sync` | 0 |
>   | `front check` | 0 errori e 0 avvisi |
>
>   Ruff e black puliti sugli 11 file Python toccati, `git diff --check` pulito, porta 6187 libera, in `.jobs` solo
>   `.lock`.
> - **Backlog**: B-9, il token del pannello fra i controlli della configurazione, come ha fatto E (sezione B).
> - **Checkpoint** (20:11) 🧊 FROZEN: handoff al coordinatore, con i file di H dichiarati (`instance_block.py`,
>   `test_instance_block.py`) e la voce del catalogo.
> - **Nota per BZ**, solo informazione: senza token, un metodo che le rotte non servono (per esempio
>   `PUT …/panel/jobs`) risponde 405, e l'OpenAPI elenca le rotte comunque. Il «404 come se non ci fossero» vale per le
>   4 operazioni servite. Nessun effetto sulla sicurezza: il codice è pubblico.

### Base `10697e618`, prove d'ingresso e decisioni 40–43 (2026-10-15, 20:12-20:25) ✅

> - **B8 committato dal coordinatore**: `663e858f1` (`feat(backup): panel token for instance backups`) e `1f8385c0d`
>   (journal). Il testo del CHANGELOG va bene. La precondizione nuova nel test di H gliela comunica il coordinatore
>   all'ingresso.
> - **Base aggiornata da lui**: merge di `dev_release2` `b4597efad`, senza conflitti; HEAD `10697e618`. Dentro ci sono
>   CP2b di H (i passi d'avvio in `lifecycle.py`), N2 di W, L, le decisioni e i registri. Dei file di B8 cambia solo
>   `.env.example`, con la sezione di Z sullo spegnimento: H non ha toccato `instance_block.py` dopo B8, e le 21 voci
>   restano intere.
> - **Prove d'ingresso** (20:13-20:21, una alla volta, `nice -n 10`, carico 67; riepilogo in
>   `/tmp/libreFolio_b_entry_10697_summary.log`):
>
>   | Selettore | Esito |
>   |---|---|
>   | `api backup-panel` | 59 (5 min 43 s: la corsia rifà la build del frontend dopo il merge) |
>   | `api instance-block` | 60 |
>   | `api backup` | 23 |
>   | `services config-env-example` | 36 |
>   | `check-orphans` | 421 Vitest, 315 backend |
>
>   Porta 6187 libera; in `.jobs` solo `.lock`.
> - **Decisioni 40–43** (file delle decisioni, righe «Decisione (15/10)» nella mia base). Cambiano il disegno di B2 e
>   B3:
>   - **40, approvata con tre precisazioni** (developer, 17:18: «direi che le tue proposte per la 40 lato mio sono
>     tutte ok», «ok nell'usare la data»):
>     - `JWT_SECRET` non cambia e non va nel backup;
>     - il DB ripristinato registra l'ora del ripristino, e ogni cookie emesso prima viene rifiutato, qualunque sia il
>       segreto. Il `+1` su `session_version` del §3.6 non basta, perché i numeri possono coincidere: serve l'ora,
>       accanto al controllo `sv` di `auth.py`;
>     - l'anteprima (B2) elenca per nome gli admin del backup, con l'avviso «dopo il ripristino entri con uno di
>       questi, con la password di allora». Senza nessun admin nel backup, il ripristino si blocca;
>     - recupero dell'admin: «password dimenticata» via email (E), o l'assistenza con `dev.py user reset-link`. Una
>       riga nella doc del ripristino. Un pulsante del pannello che chiede il link all'istanza va nel backlog.
>   - **41, approvata con una modifica**: la copia fatta prima del ripristino serve solo a tornare indietro. Si cancella
>     se il primo avvio va bene; se fallisce, LibreFolio rimette da solo i dati di prima. Cambia il §3.4: niente
>     `pre-restore` scaricabile dalla scheda, e niente `GET`/`DELETE …/pre-restore`.
>   - **42, respinta**: dalla UI si ripristinano solo i backup di LibreFolio, con `manifest.json`. Cade D-B5, quindi
>     niente archivi «a mano». Il passaggio dalla 1.2 alla 1.3 resta l'aggiornamento sul posto. La prova «revisione
>     più vecchia» si fa con un archivio di LibreFolio con un DB a una revisione precedente.
>   - **43, approvata**: `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`, `0` = senza limite (il default del self-hosted), 500 nel
>     profilo gestito.
>
>   Il messaggio del coordinatore delle 20:12 dice «41–43 ancora aperte», ma è più vecchio di quanto sembri: è delle
>   17:18, prima delle righe «Decisione» del treno 45 (17:40-18:10), che le danno decise.
> - **Prossimo**: lo scatto `settings/backup-ready`, con la checklist di G. Lo slot della galleria lo chiede il
>   coordinatore; il doppio lancio lo farà probabilmente la coppia G-13, come per Users ed Email.
> - **B8 entrato** (coordinatore): `dev_release2` = `56d3d3182`; CHANGELOG in `6102d5097`. Le 41–43 seguono le righe
>   «Decisione» del file: il suo messaggio era arrivato in ritardo dalla coda. Il pulsante del pannello per il link di
>   reset è di B: **B-10** nel backlog, non per la 1.3 se non resta tempo. La precondizione nuova in
>   `test_instance_block.py` la comunica lui ad H. **Ordine**: lo scatto, poi B2, poi B3 (con i passi in
>   `app_lifespan.py`).

### Scatto di galleria `settings/backup-ready` (2026-10-15, 20:25-20:45) ✅ — scritto, da girare nello slot di G

> - **Fatti per il brief**, verificati sul codice:
>   - la scheda ritrova un job finito dall'id in `sessionStorage`, chiave `librefolio.backup.job`, che deve rispettare
>     `^[0-9a-f]{32}$`, e lo rilegge con `GET /api/v1/backup/instance/jobs/{id}`;
>   - la scheda non mostra niente di relativo all'orologio: una data assoluta (`finished_at`) e frasi fisse;
>   - il nome dell'archivio è in UTC (`jobs.archive_name`);
>   - `waitForSettled` aspetta `data-busy="false"` sul primo elemento che lo porta, cioè la card.
> - **Checklist di G**, come l'ha applicata E (piano 08): rotta registrata prima della prima navigazione e mai tolta;
>   solo `GET` del suo percorso, il resto `route.fallback()`; corpo validato una volta con
>   `schemas.InstanceBackupJob.parse` in `e2e/fixtures/galleryBackup.ts`; i passi e la cornice di G; nessun atteso in
>   più oltre la prova che lo stato simulato è arrivato. Nota di G (registro dei colori, 18:27): ogni scheda nuova
>   cambia i 13 scatti di `Settings`, e la riga Backup è già entrata.
> - **test-author** (in background): fixture nuova con l'id nel `sessionStorage` (`addInitScript`) e la rotta del
>   `GET`, più un test in `gallery.spec.ts` dopo quello dell'Email (file di G, solo in aggiunta). Solo prove statiche:
>   `tsc -p tsconfig.e2e.json` (prima e dopo), prettier, `playwright test --list` se non avvia server. Niente galleria.
> - **Esito di test-author** (20:25-20:41):
>   - `frontend/e2e/fixtures/galleryBackup.ts`, nuovo. L'id fisso è `5c9e2f1a…`, 32 cifre esadecimali. Il job è `done`,
>     46,0 MB, creato alle 09:41:12Z e finito alle 09:41:19Z; `file_name` è il nome UTC del backend; niente avvisi.
>     Il corpo è validato una volta con `schemas.InstanceBackupJob.parse`. L'id va nel `sessionStorage` con
>     `addInitScript`, in un try/catch per `about:blank`. Solo il `GET` del job ha risposta, il resto `fallback`; niente
>     `unroute`.
>   - `frontend/e2e/gallery.spec.ts` (di G): +24 righe in aggiunta, un import e il test
>     `backup ready (admin) - all languages and themes` dopo quello dell'Email.
>   - Prove statiche:
>     - `tsc -p tsconfig.e2e.json`: gli stessi 2 errori di base prima e dopo (`onboarding-tour.spec.ts:863`,
>       `src/lib/types/files.ts:9`), diff dei log vuoto;
>     - prettier pulito;
>     - `playwright test --list -g "backup ready"`: 2 test, desktop e mobile, senza server né browser. Con
>       `--reporter=list`, perché il reporter HTML avrebbe rifatto `playwright-report/`;
>     - in più, la fixture provata in memoria con Node e una `page` finta contro lo schema Zod vero: 16 controlli
>       verdi.
>   - Rivisto da me: il file segue la checklist, e i 5 attesi di `expectGalleryBackupReady` provano solo lo stato
>     simulato.
>   - **Fuso orario**: la card mostra l'ora nel fuso del browser, e la galleria non fissa `timezoneId`, come per le date
>     della pagina File. Il doppio lancio va fatto su due macchine con lo stesso fuso: qui è 11:41 (Europe/Rome), in UTC
>     sarebbe 09:41.

### B2 — prova su copia: analisi aggiornata alle decisioni 40–43 (2026-10-15, 20:35) — via alle 20:50

> **Stato reale** (base `10697e618`, letto sul codice):
>
> - `alembic_head_revision()` sta in `services/platform/readiness.py:38`. Con CP2b, `ensure_database_exists()` sta in
>   `services/platform/database_bootstrap.py`: lancia `alembic -c backend/alembic.ini upgrade head` in un
>   sottoprocesso, senza `-x`. `alembic/env.py:19-32` accetta `-x sqlalchemy.url=…`.
> - `run_post_migration_fixes(db_path, data_dir, *, dry_run)`: `db/post_migration/__init__.py:202`.
> - I totali di controllo di J (CP-15, `compute_control_totals`) non sono ancora in base. B2 li chiama da un punto
>   d'iniezione, con un sostituto nei test, come concordato.
> - `User` ha `username`, `is_active`, `is_superuser` e `session_version` (`db/models.py:368-394`).
> - `validate_test_data_dir` (H, `config/__init__.py:349-404`) non conosce `backups/` né `.restore/`.
> - La CLI di B1 ha `create` e `inspect`.
>
> **Cosa cambia rispetto al §3.3**:
>
> 1. **Solo archivi di LibreFolio** (42): senza `manifest.json` l'archivio è rifiutato, con un codice suo. Niente
>    archivi fatti a mano.
> 2. **Gli admin del backup** (40): il report elenca per nome gli admin attivi della copia (`is_superuser` e
>    `is_active`). Se non ce n'è nessuno, la prova finisce con `BACKUP_NO_ADMINISTRATOR`, e la conferma (B3) non è
>    possibile.
> 3. **Il limite** (43): `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` in `config/backup.py`. Il default è `0` (senza limite) nel
>    self-hosted e 500 nel profilo `managed` quando non è impostata; riga in `.env.example`.
> 4. **La busta `.lfbk`** arriva con B4. In B2 la si riconosce dalla firma e si risponde con un codice suo («archivio
>    cifrato, non ancora supportato»), non con un generico «archivio non valido».
> 5. **La prova «revisione più vecchia»**: un archivio di LibreFolio il cui DB sta a una revisione precedente, costruito
>    nel test con le migrazioni vere fino a quella revisione.
>
> **Lotti proposti**:
>
> - **B2a, libreria e CLI**:
>   - `staging.py`: lettura dello zip con l'elenco d'inclusione e i limiti (voci, dimensione, rapporto), mai `..`,
>     percorsi assoluti, link, nomi doppi;
>   - `sha256` di ogni file contro il manifest;
>   - la decisione sulla revisione con `ScriptDirectory`: più nuova o sconosciuta → rifiuto; uguale → diretto; più
>     vecchia → `alembic -x sqlalchemy.url=… upgrade head` sulla copia, in un sottoprocesso, poi i fix
>     post-migrazione sulla copia;
>   - i controlli: `integrity_check` e `foreign_key_check`, righe per tabella prima e dopo;
>   - gli admin della copia e il report;
>   - `backup_max_upload_mb()` in `config/backup.py`;
>   - `dev.py backup restore FILE --dry-run`;
>   - test: `services backup-staging` (puri, su `tmp_path`) e `utils backup-cli`.
> - **B2b, API**:
>   - `PUT /backup/restore/upload`: il corpo grezzo letto a pezzi; 413 su `Content-Length` e durante la lettura, 507
>     sullo spazio;
>   - `POST /backup/restore/stage`: un job in background, uno alla volta;
>   - `GET` e `DELETE /backup/restore/stage/{id}`: il report; annulla e pulisce; scadenza a 24 ore;
>   - nessuna di queste rotte in `ALLOWED_WHEN_BLOCKED`;
>   - `api sync`; test `api backup-restore`.
>
> **Da decidere o chiedere**:
>
> - ad H: `backups` e `.restore` fra i percorsi controllati di `validate_test_data_dir`, prima di B3. Il
>   `pending.json` di una corsia non deve mai poter toccare la cartella di produzione. Sono 2 righe: le scrive H,
>   oppure io, dichiarate;
> - per B3 (40): dove vive l'ora del ripristino. Una riga d'impostazione non chiede migrazioni; una colonna sì. Il
>   controllo va in `auth.py`, che è di A. Lo porto nell'analisi di B3.
>
> **Risposte del coordinatore** (20:50):
>
> - via a B2a, poi B2b; durante la pausa delle prove (20:42-20:55) si scrive codice, e le prove si fanno dopo la
>   ripresa;
> - `backups` e `.restore` in `validate_test_data_dir` li scrivo io, dichiarati: H è sul lotto della decisione 36;
> - l'ora del ripristino va nell'analisi di B3. Il coordinatore preferisce una riga d'impostazione, senza migrazione;
>   il controllo in `auth.py` è di A, va dichiarato e la forma va concordata con A, accanto al controllo `sv`.
>
> **Il suo messaggio delle 20:44** («H entra prima di te … `billing_url`, link di reset, anteprima di A6a») è vecchio,
> arrivato in ritardo dalla coda: `9c8ee20c3`, con quelle tre cose, è nel mio HEAD dalle 17:52. Nessuna azione.

### B2a — libreria e CLI della prova su copia (2026-10-15, 20:50-21:47) ✅

> **Codice** (scritto durante la pausa, 20:45-20:55; solo ruff, black, un import e il `--help`):
>
> - `instance_backup/staging.py`, nuovo. `stage_archive(archive, data_dir, *, stage_id, progress) -> StagingReport`, più
>   `read_report`, `remove_stage`, `new_stage_id` e `space_needed`. I cinque passi sono nella docstring:
>   1. archivio di LibreFolio: zip dai primi byte, con un manifest suo (42);
>   2. ogni voce controllata prima di scrivere: elencata nel manifest, file semplice (né cartella né link), non cifrata,
>      compressione «stored» o «deflated», nome unico anche senza le maiuscole, dimensione uguale, spazio libero;
>   3. scrittura in file nuovi (`O_EXCL`, `O_NOFOLLOW`), con lo SHA-256 confrontato mentre scrive;
>   4. la revisione decide con `ScriptDirectory`: sconosciuta (quindi più nuova) → rifiuto; uguale → `same`; più vecchia
>      → `alembic -x sqlalchemy.url=… upgrade head` in un sottoprocesso; poi i fix post-migrazione sulla copia;
>   5. i controlli prima (integrità, revisione e righe uguali al manifest) e dopo (integrità, head), gli admin attivi
>      della copia (40), il report in `report.json` (0600).
>
>   Ogni rifiuto ha un `code` stabile e un messaggio senza percorsi, e non lascia niente. Una prova alla volta (flock su
>   `.restore/stage/.stage.lock`, il `_RunLock` di `jobs.py`).
> - `paths.py`: `.restore/stage/<id>/{data,report.json}`, `restore_dir`, `stages_dir`, `stage_dir` (solo id di 32
>   cifre esadecimali).
> - `scripts/backup_cli.py`: `restore ARCHIVE --dry-run` controlla, stampa il report (revisioni, migrazioni, righe
>   cambiate, file, chiave, admin, avvisi, blocchi) e toglie la copia. Senza `--dry-run` rifiuta.
>   `_data_dir_for(…, need_database=False)`.
> - **Dichiarati**: `config/__init__.py` (H), `backups` e `.restore` fra i `managed_paths` di `validate_test_data_dir`;
>   `dev.py` (condiviso), la riga d'aiuto «backup (create, inspect, restore --dry-run)».
> - **Fuori pista**: ruff segnalava `_checked_entries` troppo complessa (C901, 11 > 10); i controlli per voce sono
>   passati in `_check_entry`. I 43 rilievi di ruff e il riformattamento di black su `dev.py` c'erano già su HEAD
>   (verificato su `git show HEAD:dev.py`).
> - **Cambi rispetto all'analisi**:
>   - la busta `.lfbk` non si riconosce ancora: il suo formato nasce con B4, quindi in B2 tutto ciò che non è uno zip è
>     `not_a_backup`;
>   - `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` va con B2b, il caricamento;
>   - i totali di J restano per quando entra CP-15: i manifest di B1 non li hanno.
> - **Test**: test-author in background (dalle 20:56, dopo la ripresa), con la corsia:
>   - `test_backup_staging.py`, nuovo (`services backup-staging`), con archivi veri fatti da B1 e DB veri, creati con
>     Alembic alla head e alla revisione prima;
>   - in `test_backup_cli.py`, i casi di `restore`;
>   - in `test_runtime_isolation.py` (non mio, in aggiunta), `backups` e `.restore` nella parametrizzazione dei link;
>   - 6 mutazioni.
>
> **⚠️ Fuori pista — seconda pausa delle prove** (21:00-21:25 circa, G lancia due volte i tre scatti nuovi, fra cui
> `backup ready`): test-author fermo, senza comandi in esecuzione, poi rimesso a scrivere i test senza lanciarli.
>
> **Esito di test-author, prima tornata** (21:10-21:40, dopo la ripresa delle 21:09; log in
> `/tmp/libreFolio_b2ata_*.log`):
>
> | Selettore | Esito |
> |---|---|
> | `services backup-staging` (nuovo) | 101 passati e 1 rosso voluto: il difetto qui sotto |
> | `utils backup-cli` | 84 (14 nuovi, per `restore`) |
> | `utils runtime-isolation` | 197, con `[backups]` e `[.restore]` |
> | `services backup-archive` | 141 e 1 saltato (il nome non UTF-8 che macOS non regge, già prima) |
> | `services backup-jobs` | 63 |
> | `services config-package` | 668 |
> | `check-orphans` | verde |
>
> - `test_backup_staging.py` usa DB veri, creati da Alembic alla head e a `005_accounts_invites`, più un aggiornamento
>   che riesce e uno che fallisce (un trigger rifiuta il cambio di revisione); in tutto 4 processi Alembic. Copre ogni
>   codice di rifiuto, con niente lasciato, il lock libero, nessun percorso nel messaggio e la fase raggiunta. Copre
>   anche busy, link, avanzamento, avvisi, la cartella dati viva identica byte per byte e il lock passato di B2b.
> - 6 mutazioni, tutte rosse. Senza `O_EXCL`, su APFS un nome in forma Unicode decomposta riscriveva in silenzio quella
>   composta.
> - **⚠️ Fuori pista — difetto trovato da test-author**: un archivio con `custom-uploads/x` come file e
>   `custom-uploads/x/y` (`x` come cartella). Con il file prima, `ensure_private_dir` alzava `BackupPathError` invece di
>   `StagingError`, con il percorso della prova nel messaggio, e la CLI dava la colpa alla cartella dati. Curato
>   (21:42):
>   - `_name_key()`, cioè NFC più casefold, per `_repeated`;
>   - `_nested()` rifiuta durante il controllo una voce che è anche la cartella di un'altra (`duplicate_entry`);
>   - di riserva, in `_unpack` un `BackupPathError` sotto la copia diventa `duplicate_entry`;
>   - `progress if progress is not None` (nota di test-author).
>
>   **Contratto nuovo, voluto**: due forme Unicode dello stesso nome si rifiutano durante il controllo su ogni file
>   system; prima venivano rifiutate in scrittura su APFS e scritte come due file altrove. Gli archivi veri non hanno
>   nomi del genere, perché upload e report stanno come `{uuid}.{ext}`. Il mio `services backup-staging` dopo la cura:
>   101 passati e 1 rosso, il test che fissava il comportamento di prima. test-author lo allinea e aggiunge 2
>   mutazioni (`_nested` e NFC).
>
> **Seconda tornata di test-author** (21:42-21:46), verde:
>
> - il test delle forme Unicode è allineato al contratto nuovo: rifiuto in «checking» su ogni file system, in 3 varianti
>   (nello zip, nel manifest, in tutti e due);
> - nei casi annidati, in più `folder-in-another-case` (`custom-uploads/X` come file sopra `custom-uploads/x/y`);
> - `services backup-staging` **105**; `utils backup-cli` **84**;
> - mutazioni: senza `_nested`, 3 rossi (il rifiuto arriva solo in «unpacking», dalla riserva); senza la NFC, 3 rossi.
>   `staging.py` è ripristinato identico (`14e32856…`).
>
> **B2a ✅** (21:47). In più, dopo i test: `api sync` 0; `front check` 0 errori e 0 avvisi, con il client generato che
> conosce le rotte di B2b.

### B2b — l'API della prova su copia (2026-10-15, 21:05-23:18) ✅ — 🧊 FROZEN

> **Codice** (scritto durante la seconda pausa; ruff, black e un controllo d'import con l'OpenAPI):
>
> - `config/backup.py`: `backup_max_upload_mb()`, decisione 43. `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`; non impostata vale
>   0 (senza limite) nel self-hosted e 500 con `LIBREFOLIO_PROFILE=managed`. Altrimenti solo cifre ASCII, se no
>   `BackupConfigError` (`BACKUP_MAX_UPLOAD_MB_INVALID`). Riga commentata in `.env.example`.
> - `instance_backup/restore_jobs.py`, nuovo:
>   - `UploadWriter` scrive il corpo in `.restore/upload/<id>.part` (`O_EXCL`, 0600). Il limite si controlla sulla
>     dimensione annunciata e a ogni pezzo, prima di scrivere; lo spazio prima di cominciare; ENOSPC dà «niente
>     spazio». `finish` fa fsync e rinomina, e toglie gli upload precedenti, tranne quello che una prova sta leggendo.
>   - `start_check`: il lock delle prove si prende nella richiesta (così un secondo avvio riceve subito il rifiuto) e
>     passa al thread. Lo stato sta in `.restore/checks/<id>.json`, scritto in modo atomico a ogni fase e al più una
>     volta al secondo. L'upload si toglie a fine prova.
>   - `read_check`: uno stato «running» senza il lock tenuto da qualcuno vuol dire che il server si è fermato, quindi
>     `restore_interrupted`, e la copia si toglie.
>   - `remove_check` dà 409 mentre la prova gira; `prune` toglie quello che ha più di 24 ore.
> - `paths.py`, solo in aggiunta: `upload/` e `checks/` dentro `.restore/`. `staging.py`: `stage_archive(…, lock=)`,
>   per un lock già preso; `stage_dir()` controllato dentro il `try`, così il lock si rilascia sempre.
> - `api/v1/backup/restore.py`, nuovo, solo admin:
>
>   | Rotta | Esito | Errori |
>   |---|---|---|
>   | `PUT /backup/restore/upload` | 201 | 413 `backup_too_large` (con `limit_mb`), 507 `backup_no_space`, 400 `backup_upload_empty` / `backup_upload_incomplete`, 503 `backup_upload_unavailable`, 500 `restore_folder_unusable` |
>   | `POST /backup/restore/stage` | 202 | 404 `backup_upload_not_found`, 409 `restore_busy` |
>   | `GET /backup/restore/stage/{id}` | 200 | 404 `restore_stage_not_found` |
>   | `DELETE /backup/restore/stage/{id}` | 204 | 404, 409 `restore_stage_running` |
>
>   - Il PUT è `async`: il corpo si legge con `request.stream()` e si scrive a pezzi da 1 MB, ognuno con
>     `asyncio.to_thread`, per la regola dell'I/O nel ciclo di eventi. Nell'OpenAPI il corpo è
>     `application/octet-stream`.
>   - Nessuna di queste rotte va in `ALLOWED_WHEN_BLOCKED`.
> - `schemas/backup.py`: `RestoreUpload`, `RestoreStageRequest`, `RestoreStage` e `RestoreStageReport`, con
>   `extra="forbid"`; i codici d'errore sono un `Literal`.
> - **Fuori pista**: ruff segnalava la rotta di caricamento troppo complessa (C901, 13 > 10). Ne sono uscite tre parti:
>   `_upload_limit`, `_receive` e `_upload_failure`. Il mio primo controllo d'import contava le rotte su `app.routes`,
>   che in questa versione di FastAPI non le elenca piatte; ho contato sull'OpenAPI: 15 operazioni sotto `/backup`, le
>   4 nuove fra il pannello e gli export.
> - **Middleware**: solo gzip e CORS (`services/platform/middleware.py`), nessun limite al corpo nell'app. Un proxy
>   davanti ha i suoi limiti: va nella guida (B6).
> - **Da fare**: un brief per test-author (`api backup-restore`, in-process su una cartella dati temporanea;
>   `BACKUP_ROUTES` +4 in `test_backup_api.py`), `api sync`, `front check`.
> - **In corso** (dalle 21:48):
>   - test-author con il brief di B2b (`files/b2b-test-brief.txt`), con la corsia. La rotazione del thread della prova
>     è resa deterministica, senza attese sull'orologio. Ci sono 5 mutazioni, e `BACKUP_ROUTES` +4: finché non c'è,
>     `api backup` resta rosso;
>   - docs-writer, solo pagine inglesi, con la build MkDocs solo dopo il mio «GO BUILD», così non si sovrappone alle
>     prove:
>     - `cli_tools.en.md#backup`: `restore --dry-run`;
>     - `hosting_providers.en.md`, con le ancore nuove `#panel-backups` (il token di B8) e `#restore-upload-limit` (la
>       decisione 43);
>     - `configuration.en.md`: le due variabili, e il `_FILE` del token fra i segreti.
> - **docs-writer, prima tornata** (21:48-22:04), senza build, che aspetta il mio via perché i test girano:
>   - `cli_tools.en.md`: la sezione nuova «🧪 Try a Restore on a Copy» (`#backup-restore-dry-run`), con i cinque passi,
>     il report, i codici d'uscita, lo spazio e la tabella dei codici di rifiuto. `restore --dry-run` compare anche nel
>     suggerimento Docker, nell'introduzione e nella sezione Docker. `#backup` e `#backup-docker` sono rimaste.
>   - `hosting_providers.en.md`: due sezioni nuove, `#panel-backups` (con `#panel-token`, `#panel-jobs`,
>     `#panel-refusals`) e `#restore-upload-limit`.
>   - `configuration.en.md`: due righe in «Main Options» e il default di 500 MB nella riga del profilo; i segreti
>     passano da quattro a cinque; il `_FILE` del token sta fra i «Secrets in Files».
>   - **Errori di prima, corretti**: alla tabella «What Still Answers» della pagina hosting mancavano le 8 rotte di
>     backup permesse sull'istanza bloccata; la pagina diceva «two things» per il profilo, e sono tre.
>   - **Seconda richiesta**, sempre senza build: `developer/architecture/security.md` (di H, dichiarato) allineata ad
>     `ALLOWED_WHEN_BLOCKED`, con le 8 rotte di backup al posto della frase «will join the list when their routes
>     exist»; la riga di riepilogo in `admin/index.en.md`.
>   - Resta per B6: nessuna pagina admin descrive la scheda Impostazioni › Backup.
>   - Debito di traduzione: le sezioni nuove di `cli_tools`, `hosting_providers` e `configuration` (nessun timbro: è
>     contenuto nuovo).
>   - **Terza e quarta richiesta** (22:08-22:14), sempre senza build, in `security.md` (dichiarato): «Private Endpoints»
>     (le rotte del pannello non usano la sessione, ma il token: 401, o 404 se il token non è impostato), «Secrets from
>     Files» (il token è il quinto segreto; un token inutilizzabile dà 503 e una riga di log, e il server parte lo
>     stesso), e la frase d'apertura di «Endpoint Protection». Il riepilogo di `admin/index.en.md` resta come debito di
>     traduzione, senza timbro: le traduzioni erano già indietro dal 12/10.
>   - **⚠️ Fuori pista — B-11 scritto e tolto**: docs-writer temeva che una corsia di test ereditasse il token del
>     pannello, che non è in `INSTANCE_TRUST_SECRETS`. Falso: `scripts/cli_base.py`, `_test_lane_drops()`, toglie già
>     ogni variabile documentata in `.env.example`, anche commentata, e ogni `LIBREFOLIO_*`, tranne
>     `LIBREFOLIO_TEST_*`. La riga è tolta dal backlog.
>   - **Build** (dopo il mio via, 22:38-22:48): la prima `mkdocs build` stretta dava 4 avvisi, tutti da link aggiunti in
>     `hosting_providers.en.md`. La pagina non ha traduzioni, quindi le build it, fr ed es usano quella inglese, che
>     puntava ad ancore che le pagine tradotte di `cli_tools` e `configuration` non hanno ancora. I 9 link ora vanno
>     alla pagina, senza ancora, come la pagina fa già altrove. Dopo: `mkdocs build` pulita nelle 4 lingue;
>     `check-links` 96 validi, nessuno rotto.
>   - Aggiunta una frase sul 500 `backup_upload_failed` nella sezione del caricamento.
>   - **File**: `cli_tools.en.md`, `configuration.en.md`, `hosting_providers.en.md`, `index.en.md` (admin) e
>     `developer/architecture/security.md` (+264 e −26 righe). Nessun timbro. `hosting_providers` non ha traduzioni:
>     tutta la pagina aspetta la traduzione.
>
> **Test di B2b, prima tornata** (test-author, 21:48-22:33; log `/tmp/libreFolio_b2bta_*.log`):
>
> | Selettore | Esito |
> |---|---|
> | `api backup-restore` (nuovo, puro) | 91 passati e 4 rossi voluti, uguali in due run |
> | `api backup` | 23, con `BACKUP_ROUTES` +4: il pin dell'ordine vede 15 rotte |
> | `api backup-panel` | 59 |
> | `api backup-instance-errors` | 6 |
> | `api instance-block` | 60 |
> | `services backup-staging` | 105 |
> | `services config-package` | 668 |
> | `services config-env-example` | 36 |
> | `check-orphans` | verde |
>
> Il thread della prova è reso sincrono nei test, senza attese sull'orologio. Gli aiuti di `test_backup_staging.py` sono
> riusati direttamente. Le 5 mutazioni sono tutte rosse.
>
> **⚠️ Fuori pista — 4 difetti di `restore_jobs.py` trovati da test-author, curati** (22:33-22:37):
>
> 1. Il lock si rilasciava (in `stage_archive`) prima che `_run_check` scrivesse lo stato finale. Un poll in mezzo
>    vedeva «running senza lock», segnava la prova interrotta e ne cancellava la copia. Cura: un lock passato resta al
>    chiamante; `_run_check` scrive lo stato finale e solo dopo rilascia, in un `finally`.
> 2. `read_check` giudicava sullo stato letto prima della sonda. Cura: se il lock è libero rilegge, e solo uno stato
>    ancora «running» diventa `restore_interrupted`, come in `jobs.get_job`.
> 3. `start_check` controllava l'upload, poi `prune` lo cancellava, e la colpa andava all'archivio
>    (`archive_unreadable`). Cura: prima le cartelle (`ensure_private_dir`, con un link si ferma lì), poi `prune`, poi
>    l'upload.
> 4. Una prova interrotta non veniva mai potata. Cura: senza prove in corso, `prune` chiude con `read_check` quelle
>    rimaste «running»; e toglie, oltre le 24 ore, gli upload e le copie che nessuna prova registra. È diviso in
>    `_prune_checks` e `_prune_unrecorded`, per C901.
>
> Le note minori, curate anch'esse:
>
> - `HTTP_413_CONTENT_TOO_LARGE`;
> - un altro `OSError` durante il caricamento dà 500 `backup_upload_failed`, con la riga di log, e nessun avanzo;
> - `done_bytes` e `total_bytes` seguono solo lo spacchettamento, e lo stato finale tiene quei numeri.
>
> In più, mio: `paths.is_plain_dir()`, condivisa. `remove_stage` e `_checks()` non agiscono più attraverso un link
> (`.restore`, `stage/`, `checks/`). `_a_check_runs` usa `jobs._lock_held`, che non crea il file del lock.
>
> **Seconda tornata**: test-author scrive gli adattamenti e i casi nuovi:
>
> - il lock passato resta al chiamante, in `test_backup_staging.py`;
> - un errore di scrittura → `backup_upload_failed`;
> - nessuna cancellazione attraverso un link; la potatura di quello che nessuno registra; i byte di una prova finita;
> - `backup_in_progress()` in `test_backup_jobs.py`;
> - 6 mutazioni.
>
> Le lancia dopo la build MkDocs di docs-writer, una cosa alla volta.
>
> **Seconda tornata di test-author** (22:49-23:08):
>
> | Selettore | Esito |
> |---|---|
> | `api backup-restore` | 109 passati e 5 rossi voluti: 3 difetti nuovi |
> | `services backup-staging` | 112 |
> | `services backup-jobs` | 69, con `backup_in_progress()` |
> | `api backup` | 23 |
> | `check-orphans` | verde |
>
> - I 4 rossi di prima passano senza cambiare il codice dei test.
> - Adattati al contratto nuovo: il lock passato resta al chiamante; la potatura degli avanzi solo senza prove in corso;
>   il finto `stage_archive` non rilascia più il lock.
> - Le 6 mutazioni sono tutte rosse e i file ripristinati identici.
>
> **⚠️ Fuori pista — 3 difetti nuovi, curati** (23:10-23:13):
>
> 1. Un upload il cui file non si può creare (`.restore` in sola lettura) dava un 500 senza codice. Cura: `UploadWriter`
>    trasforma in «niente spazio» un disco pieno, e la rotta fa passare ogni altro `OSError` da `_upload_failure` (500
>    `backup_upload_failed`).
> 2. Un DELETE cancellava attraverso un link: `.restore` o `checks/` sostituiti da un link, e il file di stato veniva
>    tolto nel bersaglio. Cura: `_plain_folders(data_dir, folder)`. Lettura, scrittura e rimozione di stato e upload
>    solo se `.restore` e la cartella sono cartelle vere; dietro un link la prova non si trova (404) e niente si scrive.
> 3. Una prova tolta da un'altra richiesta mentre un poll sondava il lock risultava «running». Cura: se la seconda
>    lettura non trova niente, `CheckNotFoundError`.
>
> **Prove finali** (23:13-23:16):
>
> - `api backup-restore` **114** passati: i 5 rossi sono verdi senza toccare i test;
> - `api sync` 0; `front check` 0 errori e 0 avvisi;
> - ruff pulito sui 19 file Python. Black segnala solo due righe `print_info` dei cataloghi, già su HEAD e non mie;
> - `git diff --check` pulito; porta 6187 libera.
>
> Gli altri selettori sono già girati sulle versioni attuali dei loro file: `services backup-staging` 112, `backup-jobs`
> 69, `api backup` 23, `api backup-panel` 59, `api instance-block` 60, `utils backup-cli` 84, `utils runtime-isolation`
> 197, `services config-package` 668, `config-env-example` 36, `check-orphans` verde.
>
> **Backlog**: B-11, il debito di traduzione delle pagine admin di B2 e B8.
>
> **Checkpoint B2** (23:18) 🧊 FROZEN: B2a, B2b, la documentazione e `backup_in_progress()` per Z.

### Richiesta di Z: `backup_in_progress()` (2026-10-15, 21:52-21:54) ✅ — testata, nel checkpoint di B2

> - **Richiesta** (sessione «Z - sospensione e risveglio», `d401e062`): per la decisione D-S2 del coordinatore
>   (l'istanza non si sospende mai durante un backup), una funzione in sola lettura per il monitor d'inattività di Z2b,
>   chiamata ogni 30 s.
> - **Fatto** in `instance_backup/jobs.py`:
>   - `backup_in_progress(*, data_dir=None) -> bool`. È vera se è tenuto il lock dei backup (`backups/.jobs/.lock`:
>     scheda, pannello, CLI) **o** quello delle prove su copia (`.restore/stage/.stage.lock`). La prova su copia gira in
>     un thread dopo la risposta HTTP: un monitor basato sulle richieste non la vede.
>   - La sonda di B1, `_run_lock_held`, è diventata generica, `_lock_held(path)`. Con il file del lock assente risponde
>     falso e non crea niente; altrimenti fa `flock` non bloccante e rilascia subito.
>   - Ruff e black puliti. Prova a mano su una cartella temporanea: vuota falso, senza file creati; lock libero falso;
>     lock di backup o di prova tenuto vero; il lock è di nuovo libero dopo la sonda.
> - **Da fare**: i test in `test_backup_jobs.py` con test-author, dopo B2b; lo SHA a Z quando il coordinatore committa.
>   `restore_jobs._a_check_runs` può usare `_lock_held`: lo unisco quando test-author ha finito con `restore_jobs.py`.

### Aggiornamento di base — merge di `dev_release2` `84a18fb4c` (2026-10-15, 23:20-23:35) ✅ — committato dal coordinatore: `abb81e702`

> - **B2 committato dal coordinatore**: `80b8f8c39` (B2a), `22c116679` (B2b), `6a7fae5bf` (doc), `e3a9d2251` (journal).
>   `backup_in_progress()` è in `22c116679`: lo SHA è mandato a Z.
> - **Merge aperto da lui**, `MERGE_HEAD` `84a18fb4c`, con X CP10 (le impostazioni dei plugin, `007_plugin_settings`)
>   e altro. **Un conflitto**, in `hosting_providers.en.md`: tutti e due avevano aggiunto una riga alla tabella del
>   profilo. Tenute tutte e due, prima quella di X; «three things» corretto in **four**, perché ognuno era passato da
>   due a tre. In stage solo quel file.
> - **File fusi da soli, riletti**: `.env.example`, `cli_tools`, `configuration`, `admin/index`, `security.md`, i 3
>   cataloghi. Coerenti: «Five options are secrets» resta vero; le 8 righe di backup in `security.md` sono intere;
>   nessun nome doppio nei cataloghi (il doppio `"all"` di `_backend_api.py` sono `api` ed `e2e`, già nei due lati).
> - **Prove sulla revisione combinata** (23:21-23:28, `/tmp/libreFolio_b_merge84.sh`, una alla volta, carico sotto 70):
>   `api backup-restore` 114, `utils runtime-isolation` 197, `services config-env-example` 36, `mkdocs build` pulita,
>   `check-links` 96. `services backup-staging`: **111 e 1 rosso**.
> - **⚠️ Fuori pista — un test fragile, non il prodotto**: `OLDER = CHAIN[-2]` seguiva la head, ma il test si aspettava
>   la conversione dei dati della `006`; con la `007`, «più vecchia» era diventata la `006`. Curato da test-author:
>   `OLDER = "005_accounts_invites"` fissata per nome, con controllo all'import, e le migrazioni da lì alla head
>   (`AFTER_OLDER`). Corretta anche la stessa ipotesi in `test_backup_restore.py`, una riga. Dopo:
>   `services backup-staging` 112, `api backup-restore` 114, `utils backup-cli` 84; porta libera. I due test sono
>   fuori dallo stage: il coordinatore decide se metterli nel merge.
> - **Rifinitura proposta, dopo il commit del merge** (segnalata da test-author): una tabella creata vuota da un
>   aggiornamento (prima nessuna, dopo 0) conta come `rows_changed`. Con la `007` ogni ripristino di un backup più
>   vecchio avviserebbe senza motivo. La regola diventa `(before or 0) != (after or 0)`, anche per l'elenco della CLI.
> - **`all-backend`** dopo le 01:15 (slot 1 di A fino alle 23:50, poi la finestra di G-13 dalle 00:00 alle 01:15).

### B3 — il ripristino: analisi (2026-10-15, 23:20-23:45) — 🧊 FROZEN; via alle 23:45

> **Stato reale** (letto sul codice, base con CP2b):
>
> - I passi d'avvio sono in `services/platform/app_lifespan.py`, `STARTUP_STEPS`: `… tool-catalog`, `data-directories`,
>   `risk-scenarios`, `default-avatars`, `database`, `post-migration-fixes`, `global-settings`, `provider-prewarm …`.
>   Il primo è `shutdown-watchdog` (Z). Girano in ogni processo, quindi in ogni worker con `--workers N`. Il passo
>   `database` (`database_bootstrap.ensure_database_exists`) esce con `sys.exit(1)` se una migrazione fallisce.
> - Il token di sessione porta già `iat` (`auth_service.py:135`), ma `decode_jwt_token` restituisce solo `user_id` e
>   `session_version`. Il controllo `sv` sta in `auth.py:131` (A).
> - `GET /settings/global` è **pubblica** e restituisce *tutte* le righe di `global_settings` (`settings.py:296`,
>   `get_all_global_settings`). Una riga «ora del ripristino» si vedrebbe da fuori, se non si filtra.
> - Per un riavvio non c'è un aiuto: il budget di spegnimento di Z si attacca ai segnali di uvicorn
>   (`shutdown_budget.py`).
>
> **Disegno** (aggiorna §3.4 e §3.6):
>
> 1. **Conferma** `POST /backup/restore/stage/{id}/confirm`, solo admin. Vuole una prova finita, ripristinabile (nessun
>    blocco), non scaduta e nessun altro ripristino in attesa. Scrive in modo atomico `.restore/restore.json`: lo stato
>    `pending`, la prova, il percorso reale della cartella dati, chi conferma e quando. Risponde 202. Codici:
>    `restore_already_pending` 409, `restore_not_restorable` 409, `restore_stage_expired` 410, 404.
>    - La copia di una prova in attesa non si pota e non si cancella (409).
> 2. **Riavvio** `POST /backup/restore/restart`, solo con un ripristino in attesa (altrimenti 409). Risponde 202, poi
>    manda SIGTERM al processo padrone, cioè al master di uvicorn se c'è, altrimenti a se stesso, con un
>    `BackgroundTask` dopo la risposta. Lo spegnimento ordinato di Z fa il resto; Docker riavvia (`unless-stopped`).
>    `restart.py` prende segnale e bersaglio iniettati, per i test: nessun test spegne la corsia.
> 3. **All'avvio**, passo `pending-restore` (fra `tool-catalog` e `data-directories`, come concordato con H), sotto un
>    flock esclusivo su `.restore/apply.lock`:
>    - `pending` → lo scambio. Per `sqlite/`, `custom-uploads/`, `broker_reports/` e `scenario_catalog/`: la cartella
>      viva va in `.restore/previous/` e quella della prova al suo posto, solo rinomine sullo stesso volume. Ogni mossa
>      è scritta nel giornale prima e dopo. Poi lo stato `applied`, con l'«avvio» che l'ha fatto: PID del processo
>      padrone e ora della sua creazione (psutil).
>    - `applied` da *questo* avvio (un altro worker): niente.
>    - `applied` da un avvio che non c'è più (processo morto o PID riusato): **ritorno indietro** (decisione 41). I
>      dati ripristinati vanno in `.restore/failed/`, `previous/` torna al suo posto, e lo stato diventa `rolled_back`,
>      con il motivo «il primo avvio dopo il ripristino non è finito».
>    - Uno scambio interrotto a metà, con mosse fatte e mosse no: si disfano quelle fatte → `rolled_back`, «interrotto
>      durante lo scambio». Più sicuro che finirlo.
>    - `secrets/`, `logs/`, `scheduler_state.json`, `backups/` e `.restore/` non si toccano mai.
> 4. **Passo `restore-commit`** (fra `global-settings` e `provider-prewarm`): se lo stato è `applied` da questo avvio,
>    si chiudono le sessioni (punto 6), si cancella `previous/` (decisione 41: la copia serve solo a tornare indietro),
>    lo stato diventa `committed`, si scrive l'ultimo esito e si toglie la prova. Gli altri worker trovano `committed`.
> 5. **Stato** `GET /backup/restore/status`: il ripristino in attesa e l'ultimo esito (`committed` o `rolled_back`, con
>    il motivo). `DELETE /backup/restore/pending` annulla prima del riavvio. Tutto bloccato sull'istanza bloccata.
> 6. **Sessioni (decisione 40)**, due forme possibili; la scelta è del developer:
>    - **(a) consigliata**: al commit, `users.session_version = ora del ripristino in millisecondi` per tutti, nel DB
>      ripristinato. È «usare la data» dentro il controllo `sv` che c'è già. Un cookie di prima ha un `sv` piccolo, o
>      quello di un ripristino precedente, e non coincide mai; i cambi di password dopo fanno +1 come oggi. Niente
>      modifiche ad `auth.py` (A), nessuna riga nuova, nessuna migrazione, niente da nascondere a
>      `GET /settings/global`.
>    - **(b)**: una riga `global_settings` con l'ora, più `iat` in `SessionClaims` e un controllo accanto a `sv` in
>      `auth.py` (A, da concordare). In più serve un filtro che tenga la riga fuori dalla lista pubblica (file di A).
> 7. **CLI** `dev.py backup restore ARCHIVE` (senza `--dry-run`): prova, poi conferma a terminale, poi `pending`. Il
>    ripristino si applica al prossimo avvio, a server spento o dopo un riavvio. Un solo percorso di scambio, quello
>    dell'avvio.
> 8. **Fuori da B3**: la chiave d'istanza e la ricifratura (B4, `.lfbk`); la card nella scheda e l'avviso dopo il
>    riavvio (B5b); i totali di J (CP-15); Litestream (B7: l'avviatore chiama lo stesso `pending-restore` prima di
>    Litestream).
>
> **Superfici**: `instance_backup/apply.py` (nuovo: giornale, scambio, ritorno indietro, commit), `restart.py` (nuovo),
> `restore_jobs.py` (conferma, stato, annullamento, protezione della copia in attesa), `api/v1/backup/restore.py`,
> `schemas/backup.py`, `scripts/backup_cli.py`. **Dichiarati**: due righe in `app_lifespan.py` (H, già concordate);
> con (b), anche `auth.py`, `auth_service.py` e `settings_service.py` (A). Doc: guida e `cli_tools`.
>
> **Prove**:
>
> - `services backup-apply`, puro su cartelle temporanee: ogni mossa dello scambio interrotta e ripresa; il ritorno
>   indietro; più worker (due processi sul lock); il PID riusato;
> - `api backup-restore`, ampliata: conferma, stato, annullamento, riavvio con il segnale intercettato;
> - con (a), un test che fissa che il cookie di prima viene rifiutato dal `sv` vero;
> - l'accettazione del fondatore, «stessi totali» (backup di una cartella popolata, ripristino su una vuota, avvio in un
>   sottoprocesso), in un `e2e` di B, senza un secondo server.
>
> **Rischi**:
>
> - lo scambio con più worker, curato con lock, giornale e PID del padrone;
> - un supervisore assente (la UI lo dice: B5b);
> - il riavvio della corsia nei test: mai un vero SIGTERM.

### Merge `abb81e702` committato; via per B3 e decisione sulle sessioni (2026-10-15, 23:45) — B3 continua sotto; in dev `0cd910a7e`

> - **Coordinatore**: merge della base committato, `abb81e702`, con la mia risoluzione e la correzione dei due test
>   (`OLDER` fissato a `005_accounts_invites`); journal di B3 in `f0b76e81d`; worktree pulito.
> - **Rifinitura `rows_changed`: sì**, nel prossimo checkpoint con il suo test. Applicata (23:49): in `staging._report`
>   e nell'elenco «Changed by the upgrade» di `backup_cli._print_stage_report` la regola è
>   `(rows.before or 0) != (rows.after or 0)`. Ruff e black puliti. Tocca due test registrati
>   (`test_backup_staging.py:875`, la formula vecchia; `test_backup_cli.py:1325`, che si aspetta
>   `account_tokens (— → 0)`): li aggiorna test-author prima dell'`all-backend` di B2, con un test puro di `_report`.
> - **Decisione sulle sessioni (40): la (a)**, presa di notte dal coordinatore, **da rivedere** col developer:
>   - al commit, `session_version` di ogni utente = l'ora del ripristino in ms. Non tocca `auth.py` né
>     `settings_service`, nessuna migrazione;
>   - un test: un cambio di password dopo il ripristino incrementa ancora (ms + 1) e chiude le altre sessioni come oggi;
>   - nella doc va detto che il valore è un tempo, non un contatore.
>   - **Mia precisazione**, da confermare: il valore è `max(ora in ms, massimo del DB ripristinato + 1, massimo del DB
>     di prima + 1)`. Con un orologio sano è sempre l'ora; il `max` rende dimostrabile che nessun cookie delle due storie
>     coincide anche con l'orologio indietro.
> - **B3 in codice: via, rossi prima.** Le righe nuove in `app_lifespan.py` (H) sono una per passo, dichiarate (più
>   l'import).
> - **`all-backend` per l'ingresso di B2** verso le 01:35, dopo la galleria di Y7: lo annuncia il coordinatore. Il
>   runner lancia solo le voci del catalogo, quindi fino ad allora il lavoro di B3 vive in file nuovi non registrati e in
>   moduli non collegati; i file esistenti si toccano dopo.
>
> **Contratto di B3** (fonte unica per test e codice, nella cartella della sessione: `files/b3-contract.md`). In sintesi:
>
> - `apply.py`: lo stato in `.restore/restore.json` (`pending` → `applying` → `applied` → `committed`; `rolling_back` →
>   `rolled_back` con il motivo `first_start_failed`, `swap_interrupted`, `swap_failed` o `stage_missing`), il lock
>   `.restore/apply.lock`, il giornale scritto prima della prima mossa, il ritorno indietro guidato dai file (idempotente),
>   l'«avvio» (PID del processo padrone e ora di creazione, psutil), le sessioni al commit, la pulizia di `previous/`,
>   `failed/` e della copia. Nessun file creato a un avvio senza ripristino.
> - `restart.py`: SIGTERM al master di uvicorn (o a sé), con il mittente sostituibile nei test.
> - `restore_jobs`: `confirm_check`, la copia di un ripristino attivo mai potata né cancellata.
> - API: `POST …/stage/{id}/confirm` (202), `GET …/status`, `DELETE …/pending` (204), `POST …/restart` (202); tutte
>   bloccate sull'istanza bloccata.
> - CLI: `restore ARCHIVE` con conferma (`--yes`, o la parola `restore` al terminale), `pending [--cancel]`.
> - Accettazione del fondatore in `e2e backup-roundtrip`: sorgente e destinazione in `tmp_path`, «un avvio» = la fetta
>   di `STARTUP_STEPS` da `pending-restore` a `restore-commit` in un processo nuovo; i totali con il motore ufficiale
>   (`PortfolioService.get_report`), finché non c'è CP-15 di J.
>
> **Test, rossi prima** (23:55):
>
> - test-author 1 (`74f52618`): il test della rifinitura, poi `test_api/test_backup_restore_apply.py` e
>   `test_utilities/test_backup_cli_restore.py`;
> - test-author 2 (`994eb260`): `test_services/test_backup_apply.py` e `test_e2e/test_backup_roundtrip.py`.
> - Niente registrazione nel catalogo né run fino a dopo l'`all-backend` di B2; il rosso lo lancio io.
> - Il codice lo scrivo intanto in una bozza fuori dal repo (cartella della sessione, `files/b3-wip/`), e lo porto nel
>   worktree dopo aver visto il rosso.
>
> **Rifinitura `rows_changed`, test** (test-author 1, 00:10) ✅: `services backup-staging` **118** (6 nuovi: la formula
> nuova nel test dell'aggiornamento, e un test puro di `_report` con tabelle create o tolte, vuote o no);
> `utils backup-cli` **87** (3 nuovi: la riga attesa è `users (3 → 4)`; nessuna riga «Changed by the upgrade» se cambiano
> solo tabelle vuote; una tabella creata o tolta con righe è elencata). Prodotto non toccato da lui; porta libera.
>
> **Test di B3, prima tornata** (test-author 1, 00:10): `test_api/test_backup_restore_apply.py` (64) e
> `test_utilities/test_backup_cli_restore.py` (36), scritti, ruff e black puliti, raccolti; non registrati, non lanciati.
> I suoi sei punti sul contratto, decisi (00:15) e scritti nel contratto:
>
> 1. conferma con `.restore` link o file → 500 `restore_folder_unusable` (la conferma ci scrive); un link al posto di
>    `checks/` o `stage/` → 404;
> 2. due test registrati che B3 rompe (la precondizione delle 4 rotte in `test_backup_restore.py`, il messaggio «Only
>    --dry-run» in `test_backup_cli.py`) e l'aiuto `restore()` senza `yes`: si cambiano dopo l'`all-backend` di B2;
> 3. la parola da scrivere: spazi ignorati, maiuscole no (`Restore` rifiuta);
> 4. `pending`: parole, poi il codice fra parentesi (`backup_running`, `first_start_failed`, …);
> 5. `pending --cancel` senza niente in attesa: `❌ … (restore_not_pending)`, uscita 1;
> 6. l'annullamento senza ripristino non crea niente, nemmeno `.restore/apply.lock`.
>
> - **⚠️ Fuori pista — `all-backend` e i file nuovi**: verificato che `all-backend` lancia solo le voci del catalogo
>   (`_suites.run_all_backend_tests`, nessun glob) e non fa il controllo degli orfani: i file di B3 non registrati non
>   entrano nella run d'ingresso di B2.

### Checkpoint `rows_changed` committato; la formula delle sessioni (2026-10-16, 00:17) — B3 continua sotto; in dev `0cd910a7e`

> - **Coordinatore**: `484b75231` `fix(backup): rows_changed ignores tables created or dropped empty` e `94a95284d`
>   (journal). HEAD verificato `94a95284d`; fuori, non tracciati, solo i due file nuovi di B3. `all-backend` verso le
>   01:35 su `94a95284d`: lo annuncia lui.
> - **Decisione notturna, da rivedere col developer — la formula delle sessioni dopo un ripristino** (40, forma (a)): al
>   commit, per ogni account,
>
>   ```text
>   session_version = max(ora del ripristino in ms, massimo del DB ripristinato + 1, massimo del DB di prima + 1)
>   ```
>
>   Approvata dal coordinatore («è più robusto»). Con un orologio sano è sempre l'ora in ms: un tempo, non un contatore.
>   Il `max` serve quando l'orologio è indietro, o quando un DB porta già i valori di un ripristino precedente. Un cambio
>   di password dopo fa ancora `+1`. Nei rossi (test-author 2): l'orologio indietro; un ripristino sopra un altro
>   ripristino; poi un cambio di password che aggiunge 1.
> - **Test di B3, seconda tornata** (test-author 1, 00:20): i sei punti applicati;
>   `test_backup_restore_apply.py` 67 test, `test_backup_cli_restore.py` 44, statici puliti, non registrati né lanciati.
>   Un `--collect-only` lanciato con il carico a 76,5, sopra il limite di 70: leggero (10 s), nient'altro in corso.
> - **Scelta notturna, da rivedere — un ripristino confermato e poi un blocco dell'istanza** (`LIBREFOLIO_BLOCKED`,
>   decisione 12): il ripristino in attesa si applica comunque al prossimo avvio. I dati sono entrati prima del blocco
>   (caricati e confermati), e il passo d'avvio resta senza legami con il blocco di H. Sull'istanza bloccata l'admin non
>   può annullarlo dalla UI (tutte le rotte del ripristino sono bloccate); dalla CLI sì. L'alternativa (aspettare,
>   `waiting = instance_blocked`) è piccola, se il developer la preferisce.

### B3 — i rossi (2026-10-16, 00:30-00:58) ✅ — il codice aspetta l'`all-backend`

> - **test-author 2** (`994eb260`, 00:30-00:52): `test_services/test_backup_apply.py` (163 test: percorsi, errori e
>   modelli, avvii, lettura dello stato, `confirm_restore`, `cancel_restore`, `apply_pending_restore` con gli scambi, il
>   giornale, gli arresti dopo ogni rinomina dello scambio e del ritorno indietro, i guasti, l'attesa, la corsa fra due
>   worker; `finish_pending_restore`; le sessioni con i tre casi del coordinatore; i passi d'avvio; `restart`; il giro
>   completo con archivi veri alla head e a `OLDER`) e `test_e2e/test_backup_roundtrip.py` (3 test, §9). I suoi 10
>   punti, decisi: `.restore` file o link → `BackupPathError` prima del report; `B = 0` per un DB senza account;
>   `global_settings` dopo l'avvio (coppie controllate uguali, chiavi aggiunte solo default); le sue tre scelte dove il
>   contratto taceva, accettate; `current_boot` legge `restart.server_pid` alla chiamata (corretto nella bozza).
> - **⚠️ Fuori pista — l'e2e leggeva il DB della corsia**: sotto `all-backend` la categoria `services` lo ricrea vuoto,
>   ed `e2e` non lo popola; in più una lettura può lasciare un `-shm` accanto a un DB in WAL della corsia. Deciso
>   (00:58): sorgente autonoma, un'istanza in `tmp_path` popolata da `populate_mock_data --force` in un processo figlio in
>   modalità test su quella cartella; i totali della sorgente e della destinazione calcolati uno dopo l'altro alla fine.
>   Isolamento `pure`. In riscrittura.
> - **Il rosso** (00:54:26-00:54:59, carico 30-34, `nice -n 10`, `/tmp/libreFolio_b3_red.sh`, log in
>   `/tmp/libreFolio_b3_red_*.log`):
>
>   | File | Esito | Motivi |
>   |---|---|---|
>   | `test_backup_apply.py` | 163 rossi, 0 errori | moduli `apply` e `restart` assenti; nomi nuovi di `paths`; passi d'avvio assenti |
>   | `test_backup_restore_apply.py` | 67 rossi | modulo `apply` assente; rotte nuove 404 «Not Found» |
>   | `test_backup_cli_restore.py` | 44 rossi | modulo `apply` assente; `pending` sconosciuto ad argparse; il messaggio «Only --dry-run» di B2 |
>
>   Le fixture si costruiscono con il codice di oggi.
> - **⚠️ Fuori pista — rosso con pytest diretto**: i tre file non sono registrati, perché registrarli prima
>   dell'`all-backend` di B2 metterebbe dei rossi in quella run. Li ho lanciati con `python -m pytest` e lo stesso
>   ambiente che il runner dà alla corsia (`LIBREFOLIO_TEST_MODE=1`, `LIBREFOLIO_TEST_DATA_DIR=/tmp/librefolio-r13-b`,
>   `TEST_PORT=6187`, `PIPENV_DONT_LOAD_ENV=1`): sono puri, nessun server. Dopo la registrazione si passa dal runner.
> - **Regola nuova del coordinatore** (00:56): niente prove né build di nessun tipo fino a verso le 01:40, poi il suo
>   via; le prove spostate slittano dopo. Detto ai due test-author (niente pytest, nemmeno `--collect-only`).
> - **L'e2e riscritto, autonomo** (test-author 2, 01:00-01:10; non raccolto né lanciato, per la regola): la sorgente è
>   popolata da `populate_mock_data --force` in un figlio, in una cartella di `tmp_path` (20-56 s nei log del runner);
>   poi i file del modulo (dopo il populate, che svuota `broker_reports/`), il primo avvio, `jobs.run_backup`. Nei figli
>   `PYTHONHASHSEED=0` (stesso ordine delle liste costruite da insiemi) e il `bin` dell'interprete in testa al `PATH` (il
>   populate lancia `alembic` per nome). I totali della sorgente e della destinazione uno dopo l'altro, dopo il ripristino.
>   Isolamento `pure`; nessun populate nel runner.
> - **Bozze riviste contro i test** (00:58-01:15, sola lettura): `current_boot` legge `restart.server_pid` alla chiamata;
>   la riga «rolled back» della CLI finisce con il codice. Il resto combacia (ordine dei rifiuti, conteggi delle
>   rinomine, lock nel `finally`, `flock` bloccante e rilettura, OpenAPI, segnale dopo la risposta). Registrazione dei
>   quattro file pronta in `files/b3-wip/register_b3.py` (ancore verificate).
> - **Messaggio vecchio dalla coda** (arrivato alle 01:07): la checklist di G per lo scatto `settings/backup-ready`,
>   «seguila mentre scrivi». Lo scatto è già scritto e committato (`a675d2eb2`) e G-13 l'ha girato due volte, verde.
>   Riletto contro la checklist: rotta prima della navigazione, `login`, `forEachLanguageAndTheme`,
>   `navigateTo('/settings?tab=backup')`, `aria-selected`, `waitForSettled`, `extendScreenToBlock` e `restoreTallScreen`,
>   corpo tipizzato, date assolute, nessun backup vero. Diverso solo il titolo del test (`backup ready (admin) - …`); il
>   nome dello scatto è `settings/backup-ready` come chiesto. Nessuna azione.
> - **Altro messaggio vecchio dalla coda** (arrivato alle 01:08; scritto il 15/10 dopo le 17:40): le decisioni 41–43
>   alla lettera, «B2 e B3 possono partire con il mio via, dopo B8». Già registrate qui dal 15/10, 20:12; B8 è entrato,
>   B2 è committato, B3 ha il via dalle 23:45. Una richiesta era ancora aperta, e l'ho fatta: **riscritti i paragrafi
>   dell'analisi** che le decisioni superano (§2 punto 2, §4 D-B3/D-B4/D-B5/D-B6, §8, §10). Il cancello «ripristinare un
>   backup della 1.2» diventa «un backup di LibreFolio a una revisione precedente»; il passaggio dalla 1.2 è
>   l'aggiornamento sul posto, cancello della release e non di B. Va nel prossimo checkpoint.
> - **Terzo messaggio vecchio** (01:09; del 15/10, prima di CP2b): `main.py` congelato fino a CP2b, il passo di B3 come
>   una riga in `STARTUP_STEPS` dopo il suo ingresso. CP2b è nella mia base (`app_lifespan.py`), e la bozza aggiunge
>   proprio una riga per passo lì. Nessuna azione. **Quarto** (01:09): il rosso di E2 in `core-unit`
>   (`htmlInterpolation.gate`), corretto in `be7de95b6`: riguarda il merge di base del 15/10 (18:42-19:05), già
>   committato. Nessuna azione.
> - **Quinto** (01:10; del 15/10, ~19:30): CP2b entrato; i due passi di B3 in `STARTUP_STEPS` di `app_lifespan.py`,
>   «fissali con `assert_in_relative_order` nel test `services app-lifecycle`». L'ordine è fissato in
>   `services backup-apply` (sezione (j)): lo stesso controllo, in un test nostro, come chiede la docstring di
>   `assert_in_relative_order` («A workstream checks a constraint of its own with it, in a test of its own»). Con una
>   copia locale di 6 righe, perché importare `test_app_lifecycle` tira dentro `backend.app.main`, e
>   `configure_logging()` scrive `logs/` nella cartella dati configurata. Da dichiarare all'handoff; se il coordinatore
>   vuole anche la riga nel file di H, è un'aggiunta di una riga.
> - **Sesto** (01:10; del 15/10, ~21:00): lo scatto entrato da solo (`ab2ddf86e`), «continua con B2a». Passato: B2 è
>   committato. Nessuna azione.
> - **Regola della notte** (coordinatore, 01:10): le decisioni del developer vanno al coordinatore in 3-4 righe, con la
>   proposta per prima, e il punto va in pausa; le scelte tecniche nel mio perimetro le decido io, come «Decisione
>   notturna, da rivedere». Mandato (01:12): il caso «ripristino confermato, poi istanza bloccata» per la lista di
>   domattina, con la proposta «si applica comunque»; intanto il codice fa così. Offerta l'analisi di B5b in bozza.
> - **Decisione notturna, da rivedere — più worker e un primo avvio che fallisce**: con `--workers N` il «boot» è il
>   master di uvicorn, che rilancia un worker morto. Se un passo dopo `pending-restore` fallisce sempre, i worker
>   ripartono in ciclo e il ritorno indietro avviene solo quando il master si ferma e il server riparte. Nell'immagine
>   Docker c'è un processo solo, e il ritorno indietro è automatico al riavvio del container. Lo lascio così, documentato
>   come limite; un riavvio del server lo risolve.
> - **Da H CP7b, per B7 e B4** (coordinatore, 01:11, solo informazione):
>   - `stop_grace_period` resta a me (B7): H mette nei compose solo un commento che rimanda al budget di Z (8 s dentro
>     i 10 s di `docker stop`);
>   - con Litestream (B7), che avvolge uvicorn, il budget deve coprire anche il suo sync finale: se ne tiene conto per
>     `stop_grace_period` e `shutdown-sync-timeout`;
>   - `derive_key_from(key, purpose, length)` arriva con le note di X in coda a CP7b: per ricifrare i segreti in B4 si usa
>     quella, mai una mia.
> - **Analisi di B5b mandata** (01:15, su richiesta del coordinatore, per la lista di domattina). Disegno: `RestoreCard`
>   (stato del ripristino, scelta del file, caricamento con avanzamento, prova con le fasi), `RestoreReportModal` (report,
>   admin per nome con l'avviso della 40, blocco senza admin, conferma scritta), `RestartOverlay` (attesa di
>   `/system/ready`, poi il login; dopo 60 s «avvia di nuovo»), `restoreFlow.svelte.ts`, i18n `backup.restore.*`.
>   Punti aperti, con la mia raccomandazione:
>   1. l'esito dopo il riavvio solo nella scheda, con il login che riporta a `/settings?tab=backup`; un avviso globale
>      chiede una riga in `(app)/+layout.svelte` (condiviso): backlog, o la riga dichiarata;
>   2. la conferma scritta con la parola tradotta mostrata nella finestra, senza badare a maiuscole e spazi (la CLI resta
>      `restore`);
>   3. `upload_limit_mb` in `GET /backup/restore/status`, per rifiutare subito un file troppo grande: un campo in più nella
>      risposta di B3.
>
>   Scelta tecnica mia: la E2E fa per davvero caricamento, prova e report, ma finge conferma, stato, annullamento e
>   riavvio, perché un ripristino in attesa lasciato nella corsia si applicherebbe al prossimo avvio del suo server.
> - **Risposte del coordinatore su B5b** (01:13):
>   - punto 3, **sì, in B3 adesso**: `upload_limit_mb` (11° campo di `RestoreStatus`, in ogni risposta: `0` senza
>     limite, `500` nel profilo gestito se non impostato, il valore della variabile, `null` se illeggibile con un errore
>     nel log). Aggiunto alla bozza e al contratto; test a test-author 1;
>   - punti 1 e 2 nella lista di domattina, con le mie raccomandazioni come scelta di partenza (esito solo nella scheda
>     con il login che torna a `/settings?tab=backup`; parola tradotta senza badare a maiuscole e spazi);
>   - E2E con conferma, stato, annullamento e riavvio finti: d'accordo;
>   - lo scatto della galleria lo concorda lui con i colori quando B5b è pronto;
>   - l'ordine resta B3, B5, B4.

### B3 applicato e tolto; `all-backend` di B2 (2026-10-16, 01:33-02:50) ✅ — B2 entrato

> - **01:33, ripresa**: «applica B3 e lancia le prove leggere; il tuo `all-backend` per B2 fra ~15 minuti». Applicato
>   B3 (moduli nuovi, script di modifica, registrazione dei quattro file); test-author 1 ha aggiornato i due test
>   registrati che B3 rompe (precondizione delle rotte, test del file mancante con e senza `--yes`, `yes=False`
>   nell'aiuto).
> - **01:44, contrordine**: «fai entrare B2 da solo» (Z2b aspetta `backup_in_progress()`). I messaggi si sono incrociati.
>   **B3 salvato fuori dal repo** (`files/b3-applied/`, 19 file con `MANIFEST.txt`, uguali byte per byte) e **worktree
>   riportato a `94a95284d`**: i 13 file tracciati riscritti con `git show HEAD:<file>`, i 6 nuovi tolti (salvati). Solo
>   il piano resta modificato. Nessun comando git che scrive.
> - **01:48, `all-backend`** nello slot pesante 1: `--workers 2`, `nice -n 10`, corsia 6187, revisione `94a95284d`; log
>   `/tmp/libreFolio_b_all_backend_94a95.log`.
> - **Durante la run, nella copia salvata** (niente nel worktree):
>   - ruff: ordine degli import in `apply.py` (vero); `cmd_restore` troppo complessa (13 > 10) → divisa in
>     `_restore_already_active`, `_check_on_a_copy` e il resto; i quattro I001 sugli altri file sono falsi positivi del
>     controllo fuori dal repo (nel worktree non c'erano); black segnala solo due `print_info` già in HEAD;
>   - la descrizione di `utils backup-cli` nel catalogo, rimasta vecchia: «restore of a missing file, with or without
>     --dry-run, exits 1 creating nothing».
> - **⚠️ Fuori pista — i link monouso del backup** (nota di E per B3, rimasta fuori dal contratto): un ripristino
>   rianima gli inviti e i link di reset ancora vivi nel backup. **Decisione notturna, in attesa del developer** (mandata
>   al coordinatore alle 01:55 per la lista di domattina, con la proposta per prima): al commit, nella stessa
>   transazione di `session_version`, `revoked_at` = l'ora del ripristino su ogni riga di `account_tokens` non
>   consumata e non revocata, come fa `token_service.revoke_tokens`. Nel log il conteggio; il report della CLI aggiunge
>   «send new ones after the restore». Codice nella copia salvata (`_close_the_way_in`); test a test-author 2.
> - **Analisi di B4 mandata** (01:55, sola lettura, durante la run; testo in `files/b4-analysis-draft.md` della sessione):
>   `envelope.py` (intestazione con i parametri di scrypt limitati alla lettura, blocchi AES-256-GCM da 1 MiB in
>   costruzione STREAM, intestazione come dati associati); creazione con `password` facoltativa (mai dal pannello), chiave
>   d'istanza solo se generata e solo con la password; ripristino con `password` alla prova, ricifratura con
>   `rekey_plugin_secrets` di X o conteggio dei segreti illeggibili; CLI `--password-file`/`--password-stdin` e `decrypt`.
>   Dipende da H (`derive_key_from`, lettura della chiave generata). Tre punti per la lista di domattina: il costo di
>   scrypt (`2^17`, 128 MiB, raccomandato), la password (almeno 12 caratteri, due volte), lo zip in chiaro per un attimo
>   sul disco durante la creazione (accettato, raccomandato).
> - **Sequenza dopo il via**: `all-backend` di B2 su `94a95284d`; poi nel worktree il codice di B3 (`apply.py`,
>   `restart.py`, le modifiche in `paths`, `restore_jobs`, schemi, API, CLI, `app_lifespan` con le due righe dichiarate),
>   la registrazione dei quattro file, i due test registrati che B3 rompe, il verde mirato, `api sync`, `front check`, la
>   doc (docs-writer).
> - **`all-backend` di B2 su `94a95284d`** (slot pesante 1, 01:48:55-02:30:00, 41 min, `--workers 2`, `nice -n 10`,
>   corsia 6187; log `/tmp/libreFolio_b_all_backend_94a95.log`): **verde**, 7/7 categorie, **18 359 passati, 29 saltati,
>   0 falliti**:
>   - 4 passate parallele (147, 47, 11 e 65 unità, 2 worker): 16 180 passati e 4 saltati;
>   - sessioni sequenziali e consolidate: 2 179 passati e 25 saltati (26 riepiloghi pytest); il DB 18/18.
>
>   Dopo: porta 6187 libera, `backups/.jobs` vuota. Risultato al coordinatore alle 02:31.
> - **B3 rimesso** (02:31, `restore_b3.sh`: 19 file uguali alla copia salvata). Nel worktree: ruff pulito sui file di B3
>   (i 43 rilievi di `dev.py` sono già in HEAD); black segnala solo righe già in HEAD (`dev.py`, i due `print_info` dei
>   cataloghi); `check-orphans`: tutti i 335 file del backend registrati e raggiungibili.
> - **02:33, aggiornamento di base per l'ingresso di B2**: il coordinatore committa il piano (`e05ccd1b4`) e chiede il
>   worktree pulito per un merge con 4 conflitti di doc (contro Z4, Z3, A6d). B3 di nuovo fuori: questa volta come
>   **patch** dei 13 file tracciati (`files/b3-wip/b3-tracked.patch`, 885 righe) più i 6 file nuovi della copia salvata,
>   perché dopo il merge una copia dei file sovrascriverebbe le sue modifiche. Worktree pulito su `e05ccd1b4`.
> - **Merge di base `db384eaf5`** (aperto dal coordinatore alle 02:34; Z3, Z4, A6d e altro): 4 file di doc in
>   conflitto, 7 blocchi, risolti spostando le righe dei due lati (`files/b3-wip`, script in Python), in stage solo quei 4:
>   - `configuration.en.md`: le nostre due righe (`BACKUP_DOWNLOAD_TOKEN`, `BACKUP_MAX_UPLOAD_MB`) poi `WAKE_TOKEN` di Z;
>     in «Secrets» la frase di Z senza numero (richiesta del coordinatore); nella tabella dei segreti
>     `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN` poi la riga di Z;
>   - `hosting_providers.en.md`: i due punti di «For Each Instance» (token del pannello, poi token del risveglio);
>   - `admin/index.en.md`: la nostra riga «Hosting for Others», più completa, più «Sleep and Wake» di Z;
>   - `security.md`, endpoint privati: il paragrafo di Z (due tipi di rotta con un token proprio) più una frase con il
>     nostro dettaglio sul pannello (`require_panel_token` a tempo costante, `401`, `404` senza token); elenco del
>     blocco: il lato di `dev_release2`, che copre già backup e risveglio.
>
>   File fusi da soli e cambiati dai due lati, riletti: `.env.example` (il blocco del risveglio di Z, prima della nostra
>   sezione), l'indice del backlog (solo altre sezioni), i 3 cataloghi del runner (solo voci di altri, nessun nome che
>   scontra B2 o B3).
> - **Prove sulla revisione combinata** (02:35-02:43, `/tmp/libreFolio_b_mergedb3.sh`, una alla volta, `nice`, carico
>   sotto 70): `api backup-restore` 114, `services backup-staging` 118, `services config-env-example` 36, `mkdocs build`
>   stretta con 0 avvisi, `check-links` 96 validi, `check-orphans` 342 file del backend tutti raggiungibili. Porta libera.
> - **Merge `db384eaf5` committato dal coordinatore**: `cc439f696`. Dentro c'è anche CP-15 di J (`fd41a0996`):
>   `financial_math/ledger_totals.py` (`CONTROL_TOTALS_VERSION = 1`, `ControlTotals` con `to_json()`/`from_json()`,
>   `compute_control_totals(session)`), da usare quando il lotto arriva a manifest e controllo (TODO(CP-15) dell'e2e).
> - **Secondo merge, `a2f658097`** (A6d e A6e entrati nel frattempo; aperto dal coordinatore alle 02:44, B3 ancora
>   fuori): un conflitto, `security.md`, «Private Endpoints». Tenute la frase di A sulle impostazioni globali (lette da
>   ogni utente con una sessione, scritte solo da un admin; la pagina di login legge `/system/instance`), quella di Z sui
>   due tipi di rotta con un token proprio e la nostra sul pannello, presa alla lettera dal nostro lato. In stage solo
>   quel file. Fusi da soli e cambiati dai due lati: `cli_tools`, `configuration`, `hosting_providers` (le modifiche di
>   A), il backlog, un `print_info` di `_backend_services.py` riformattato: niente di B. `mkdocs build` stretta 0
>   avvisi, `check-links` 96 validi (02:45-02:48).
> - **✅ B2 entrato in `dev_release2`** (treno 82, merge `5441b96ed`), con la riga ✨ nel CHANGELOG. Il secondo merge di
>   base è committato dal coordinatore: `62004e530`.
> - **B3 rimesso come patch** (02:50): `git apply --reject` di `files/b3-wip/b3-tracked.patch` sui 13 file tracciati,
>   nessun `.rej`; i 6 file nuovi dalla copia salvata. I 10 file tracciati non toccati dai merge e i 6 nuovi sono uguali
>   alla copia salvata; nei 3 cataloghi del runner le voci di B3 sono sopra quelle portate dai merge (`system-wake`,
>   `email-verification`, `rate-limit-*`, `scheduler-catchup`). Ruff pulito sui file di B3; black segnala solo il
>   `print_info` già in HEAD di `_backend_utils.py`; `check-orphans`: 347 file del backend, tutti raggiungibili.

### B3 — il verde (2026-10-16, 02:50-03:00) ✅

> Prove mirate dal runner, una alla volta, `nice -n 10`, carico sotto 70 (`/tmp/libreFolio_b3_green.sh`, log in
> `/tmp/libreFolio_b3_green_*.log`), tutte al primo colpo:
>
> | Selettore | Esito |
> |---|---|
> | `services backup-apply` | 169 (43 s) |
> | `utils backup-cli-restore` | 44 |
> | `utils backup-cli` | 88 |
> | `services backup-staging` | 118 |
> | `services app-lifecycle` (H, i due passi nuovi) | 42 |
> | `api backup-restore-apply` | 75 |
> | `api backup-restore` | 114 |
> | `api instance-block` (H, le rotte nuove bloccate) | 62 |
> | `e2e backup-roundtrip` | 3 (68 s) |
>
> - **L'accettazione del fondatore**, automatizzata (`e2e backup-roundtrip`):
>   - un'istanza popolata, ripristinata su una vuota, dà gli stessi totali: 18 tabelle, 65 file, 8 report del motore
>     ufficiale (populate 13 s);
>   - un backup a `005_accounts_invites` passa alla head (`008_registration_invite_default`) con la prova e la conferma,
>     ed è committato con le righe del report;
>   - un backup più nuovo è rifiutato (`revision_unknown`), la destinazione invariata.
> - **`api sync` e `front check`**: li fa il runner prima della build del server di prova (OpenAPI esportata,
>   `generated.ts` rigenerato, `svelte-check` 0 errori e 0 avvisi), nel log di `api backup-restore-apply`.
> - Porta 6187 libera.
> - **Prossimo**: doc (docs-writer, con il brief `files/b3-docs-brief.md`), revisione di sicurezza di metà percorso,
>   checkpoint FROZEN; l'`all-backend` di B3 lo chiedo al coordinatore.

### B3 — revisione di sicurezza di metà percorso (2026-10-16, 03:00-04:05) ✅ — corretta

> **Esito** (agente `security-review`, sola lettura sul diff di B3): nessuna vulnerabilità raggiungibile dall'API o
> dall'archivio; due allarmi MEDIUM (7/10), finestre in cui il commit (sessioni chiuse e link revocati) può saltare
> mentre il server serve già i dati ripristinati; quattro punti di robustezza.
>
> 1. **L'identità del boot segue l'orologio**: psutil, su Linux, ricava `create_time` dall'ora d'avvio del sistema, che
>    un salto d'orologio (NTP all'avvio di un Pi senza orologio) sposta. Fra `pending-restore` e `restore-commit` il
>    boot cambiava, il commit saltava, e il server serviva i dati ripristinati con le sessioni e i link del backup;
>    all'avvio dopo, il ripristino veniva disfatto, con la perdita di quanto inserito nel frattempo.
>    **Corretto**: il boot si legge una volta per processo (`_boot_of`, in cache); `finish_pending_restore` con un
>    ripristino «applicato da un altro boot» ferma l'avvio (`RestoreInUseError`, codice `restore_in_use`) invece di
>    proseguire.
> 2. **Più worker**: un worker che uvicorn rilancia sotto i fratelli vivi (crash, `SIGHUP`, `SIGTTIN`), o un secondo
>    server sulla stessa cartella, applicava un ripristino in attesa sotto chi serve. **Corretto** con il lock di «server
>    acceso» dell'analisi approvata (§3.4, punto 2), che avevo tolto dal contratto di B3: ogni processo tiene un `flock`
>    condiviso sulla cartella dati stessa (nessun file) dalla fine del suo avvio (passo nuovo `serving-lock`, una riga in
>    più dichiarata in `app_lifespan.py` di H); lo scambio, e il ritorno indietro di un boot morto, solo se nessuno lo
>    tiene. Altrimenti il ripristino aspetta (`waiting = server_running`), o l'avvio si ferma (`restore_in_use`) per un
>    ritorno indietro sotto un server. Anche «applicato da un altro server ancora vivo» ora ferma l'avvio.
> 3. **Robustezza**, tutto corretto: modelli stretti per `restore.json` (nomi delle cartelle scambiate,
>    `stage_id` di 32 cifre esadecimali); `server_pid` usa il genitore solo se è vivo; la CLI stampa i valori presi
>    da un archivio o dallo stato (versione, revisione, tabelle, admin, `confirmed_by`) con i caratteri di controllo
>    sostituiti da `?`. Il ripristino in attesa su un'istanza poi bloccata resta la proposta nella lista di domattina.
> - **⚠️ Fuori pista — B-12 riscritta**: in uvicorn 0.52.4 un worker che fallisce all'avvio (codice 3) ferma anche il
>   master (`supervisors/multiprocess.py`, `keep_subprocess_alive`): il ciclo che avevo descritto non c'è. Il residuo
>   vero è un salto d'orologio fra i worker di un server con più worker durante l'avvio (identità senza orologio su
>   Linux: `/proc/<pid>/stat` e `boot_id`).
> - **⚠️ Fuori pista — il lock va preso prima, rilettura mia (03:45)**: preso dopo `restore-commit`, lasciava una
>   finestra: un secondo worker (salto d'orologio, B-12) o un secondo contenitore sulla stessa cartella poteva annullare
>   il ripristino sotto un processo che aveva già aperto il DB ripristinato. Ora `serving-lock` sta subito dopo
>   `data-directories`, prima di `risk-scenarios` (che legge `scenario_catalog/`) e di `default-avatars` (che scrive in
>   `custom-uploads/`): chi non lo tiene ancora non ha letto niente, e un annullamento sotto di lui non fa danni. B-12
>   scende a «il ripristino va rifatto», senza rischio per i dati. Riga dichiarata in `app_lifespan.py`: lo stesso passo,
>   più un commento di una riga. **Decisione notturna, da rivedere.**
> - **⚠️ Fuori pista — `backup inspect` stampava i valori dell'archivio senza `_safe`** (trovato da test-author 1,
>   03:55): `app_version`, `alembic_revision`, `integrity_check` e i nomi delle voci, che arrivano dritti dallo zip, su
>   un comando fatto per gli archivi sospetti. Corretto in `cmd_inspect`; per coerenza anche i nomi lasciati fuori da
>   `backup create` (`_print_warnings`). I messaggi delle eccezioni stampati dalla CLI sono testo fisso o interi: nient'altro.
> - **⚠️ Fuori pista — il lock resta esclusivo per tutte le rinomine** (nota di test-author 2, 04:00): la sonda di
>   `_someone_serves` si prendeva e si lasciava subito, quindi un processo arrivato a `serving-lock` durante le rinomine
>   di un annullamento (B-12, o un worker orfano di un master ucciso con SIGKILL) poteva leggere le cartelle a metà, e
>   aprire il DB ripristinato un attimo prima che finisse in `failed/`. Ora `_exclusive_serving_lock` (gestore di
>   contesto, al posto della sonda) tiene il lock esclusivo, senza attesa, dai controlli all'ultima rinomina: nello
>   scambio, nell'annullamento di un boot morto e in quello di uno scambio interrotto (lì senza guardare chi serve: solo
>   l'annullamento rimette insieme la cartella). Chi arriva a `serving-lock` aspetta che le cartelle siano ferme.
>   Nessun blocco reciproco: l'esclusivo non aspetta mai. **Decisione notturna, da rivedere.**
> - **Doc di B3 riletta** (docs-writer `a55a587f`; `cli_tools`, `hosting_providers`, `security.md` con la sezione nuova
>   «💾 Restoring a Backup», `users_access`, `users_and_brokers`): le 17 frasi della CLI citate sono tutte nel codice;
>   la sostituzione «uno alla volta» di `SIGHUP` è vera in uvicorn 0.52.4 (`restart_all`: il nuovo worker parte prima
>   che il vecchio esca); l'uscita con `0` nell'immagine torna con il sorgente (SIGTERM rilanciato da uvicorn, ignorato
>   dal PID 1; `os._exit(1)` quando scade il budget di Z); `on-fail` è il default di `fly launch` e `fly deploy`
>   (docs.fly.io, letta alle 04:00): nel cloud, dopo il riavvio la Machine resta ferma finché il Proxy non la sveglia, e
>   lo farà il sondaggio di `/system/ready` della scheda (B5). Corretto solo il paragrafo sul lock, per il gestore di
>   contesto. `mkdocs build` stretta 0 avvisi, `check-links` 96 validi. Proposte di docs-writer per dopo:
>   `.restore/` nell'albero di `filesystem.en.md` (H), il riavvio del ripristino fra gli arresti di
>   `configuration.en.md` (B6), la pagina `developer/backend/backup.md` (B6).
> - Dopo le correzioni: `services backup-apply` 166 passati e 3 rossi, proprio i tre che fissavano il vecchio «non si fa
>   niente»; `utils backup-cli-restore` 44, `services app-lifecycle` 42. Test aggiornati e nuovi a test-author 2
>   (servizio) e 1 (CLI, API); doc a docs-writer. Le prove le lancio io, una alla volta.

### B3 — verde finale e controlli statici (2026-10-16, 04:05-04:16) ✅ — pronto per l'`all-backend`

> - **Le ultime due note di test-author 2**, applicate: un errore nel log quando lo scambio interrotto si annulla sotto un
>   server («…that server must be restarted»), e un avviso prima che `hold_serving_lock` si metta ad aspettare uno
>   scambio in corso (prima `LOCK_SH | LOCK_NB`, poi il bloccante). Test: `test_backup_apply.py` a 194 (era 169), con le
>   prove deterministiche del lock tenuto a ogni rinomina dello scambio e dei tre annullamenti, e libero dopo, anche
>   quando il passo solleva; `test_backup_cli.py` 92 (era 88), `test_backup_cli_restore.py` 46 (era 44),
>   `test_backup_restore_apply.py` 83 (era 75), di test-author 1.
> - **Tutti i selettori di B3**, dal runner, uno alla volta, `nice -n 10`, carico sotto 70, sul codice finale
>   (`/tmp/libreFolio_b3_green_summary.log`):
>
>   | Selettore | Esito |
>   |---|---|
>   | `services backup-apply` | 194 (69 s) |
>   | `services backup-staging` | 118 |
>   | `services app-lifecycle` | 42 |
>   | `utils backup-cli-restore` | 46 |
>   | `utils backup-cli` | 92 |
>   | `api backup-restore-apply` | 83 (il runner rigenera il client: `svelte-check` 0 e 0) |
>   | `api backup-restore` | 114 |
>   | `api instance-block` | 62 |
>   | `e2e backup-roundtrip` | 3 (43 s) |
>
> - **Statici** (`/tmp/libreFolio_b3_static.sh`): `git diff --check` pulito; ruff pulito sui 18 file di B3; black pulito,
>   tranne il `print_info` del Designer Lab in `_backend_utils.py`, che fallisce già su HEAD; `check-orphans`: 347 file,
>   tutti raggiungibili; vulture (`lint --dead-code --scope backend`): niente nei file di B3 (`backup_in_progress` di B2
>   aspetta Z2b; `compute_control_totals` di J aspetta B-13). `mkdocs build` stretta 0 avvisi, `check-links` 96.
>   Porta 6187 libera. Lo snapshot del DB di prova che il runner scrive va in `.testLog/00_archive/` (ignorato).
> - **Backlog**: B-12 riscritta (il residuo vero: un salto d'orologio fra i worker, senza rischio per i dati), B-11
>   estesa alle sezioni nuove di `cli_tools`.
> - **04:22, coordinatore su P11** (la revoca dei link monouso, nella lista di domattina): «vai avanti con la revoca; nel
>   report e nella doc scrivi anche l'effetto sugli account in attesa di verifica». Verificato nel codice di E
>   (`email/verification.py`): l'attesa non ha una colonna, un account aspetta se è inattivo **e** ha un token di
>   verifica non speso; revocati tutti i token, «hold» compreso, l'account non aspetta più. Il «rimanda» della pagina di
>   accesso risponde 403 `ACCOUNT_DISABLED`, e nessuna rotta dell'admin rimanda il link: l'admin lo attiva
>   (`PATCH /users/{id}`, `email_verified_at` resta `NULL`) o lo cancella perché il proprietario si iscriva di nuovo
>   (non ha dati: non è mai entrato). Così nel report della CLI (la riga dei link ora nomina anche le verifiche, più
>   una riga sugli account in attesa), in `cli_tools` (il report e «After the restore») e in `security.md`
>   («🚫 Revocation»). Al coordinatore: «l'admin rimanda la verifica» oggi non esiste; le alternative (un «rimanda»
>   per l'admin, o il ripristino che rimette un «hold») sono nel codice di E. Test: test-author 1 fissa le due righe;
>   `utils backup-cli` 92, `utils backup-cli-restore` 46 (04:28); `mkdocs build` stretta 0 avvisi, `check-links` 96.
> - **04:29, nota di E-5** (la guardia `schemas openapi-client-text`, entrata in `dev_release2`, non ancora nella mia
>   base): il generatore del client copia senza escape la docstring di un modello dove il modello tipizza un campo, e
>   un testo su più righe con i backtick rompe il client all'import (E2b). Oggi nessuno dei nostri è tipo di un campo
>   (risposte e membri di unioni), quindi niente si rompe; ma, per non lasciare la trappola, in `schemas/backup.py`
>   tutte le docstring dei modelli sono ora di una riga, senza backtick né virgolette (`InstanceBackupJob`,
>   `RestoreUpload`, `RestoreStageReport`, `RestoreStage`, `RestoreStatus`, `RestoreTableRows`), con il dettaglio in un
>   commento sopra la classe e il perché in un commento in testa al file. Verificato leggendo le docstring; la guardia,
>   presa da `dev_release2`, non gira fuori dal repo (calcola i percorsi dalla sua posizione): gira al prossimo
>   aggiornamento di base. Ruff e black puliti.
> - **`all-backend` di B3** (slot pesante 1, 04:37:16-05:14:59, 37 min 44 s, `--workers 2`, `nice -n 10`, corsia 6187,
>   HEAD `62004e530` più B3; log `/tmp/libreFolio_b_all_backend_b3.log`): **6/7 categorie verdi**. Nell'API un solo
>   rosso, deterministico e nostro: `test_backup_api.py::test_the_backup_router_registers_its_routes_in_order`
>   (BACKUP-001, il pin dell'ordine delle rotte `/backup` di C2), che elenca ancora le 15 rotte di prima delle 4 nuove
>   di `restore.py`. Passate parallele: 4 809 + 5 974, 75 + 2 852, 953 + 782, 1 067 (+1 rosso) + 807; DB 19/19. Porta
>   6187 libera.
>   - **⚠️ Fuori pista — un selettore mancava**: fra i mirati di B3 non c'era `api backup`, l'unità del pin delle rotte.
>     Riparazione a test-author 1 (le 4 tuple nel pin, solo statici); `api backup` dopo le 06:45 (fermo della macchina
>     05:30-06:45, deciso dal coordinatore; slot spostato alle 05:20 su richiesta dei colori).
>   - Il primo lancio delle 04:36:45 è caduto subito sull'ordine degli argomenti (`--workers` va prima della
>     categoria), senza eseguire nulla.
> - **05:17, coordinatore**: per il checkpoint bastano `api backup` verde e questo `all-backend`; dopo le 06:45
>   `api backup`, poi l'handoff FROZEN e il commit. **Ingresso non prima di domattina**: B3 aspetta il developer su P7
>   (istanza bloccata prima del riavvio) e P11 (revoca dei link); prima dell'ingresso la base si aggiorna (A6c, X CP11c,
>   H CP7b-2, la correzione di Z, i lotti di T) e sulla revisione fusa serve un `all-backend` intero, in uno slot del
>   mattino. **Regola da qui in avanti**: `api backup` fra i mirati di ogni lotto che tocca le rotte `/backup`.
> - **Pin riparato** (test-author 1, 05:18, solo statici: ruff e black puliti, 23 test raccolti): `BACKUP_ROUTES` ha le 4
>   rotte di B3 dopo le 4 di B2 e prima dei 3 export, nell'ordine dei decoratori di `restore.py`; «the eight of
>   restore.py» nella docstring e nel messaggio; corretti anche la riga BACKUP-001 della docstring del modulo (era
>   rimasta a instance e panel) e il commento sopra `BACKUP_ROUTES`. Nessun conteggio o elenco di tag da aggiornare; i
>   segnaposto tolti (BACKUP-010) non si scontrano con i percorsi nuovi.
> - **Prossimo**: dopo le 06:45 `api backup`, poi l'handoff FROZEN.

### B4 — contratto in bozza, in sola lettura (2026-10-16, 04:18-04:30) — superato: B4 riparte dall'analisi delle 22:36, in dev `339a59142`

> Mentre l'`all-backend` di B3 aspetta lo slot (coordinatore: «continua con B4 in sola lettura»). Bozza del contratto
> nei file della sessione (`b4-contract.md`).
>
> - **In base** (`62004e530`): `cryptography` 50.0.2; le funzioni di X per la copia (`count_unreadable_secrets`,
>   `rekey_plugin_secrets`). Lo scopo persistito della chiave d'istanza è uno solo, `plugins.settings.v1`: il
>   `key_id` di ogni riga di X fa già da valore di controllo H-3, nella copia non c'è altro da scrivere.
> - **Manca ancora in `dev_release2`** (`2c485d3d4`, 03:56): `derive_key_from` di H (annunciata con CP7b) e una lettura
>   pubblica della chiave generata. Quindi **B4a** (busta, creazione e ripristino con password, `decrypt`, conteggio dei
>   segreti illeggibili nel report) non dipende da nessuno; **B4b** (la chiave nell'archivio e la ricifratura) aspetta
>   le due funzioni di H.
> - **Misura**: `Scrypt` di `cryptography` con `n = 2^17, r = 8` impiega 0,42 s e 128 MiB su questo Mac (carico ~30);
>   `2^15` 0,10 s e 32 MiB. `hashlib.scrypt` rifiuta `2^17` col `maxmem` predefinito di OpenSSL: solo `cryptography`.
>   Aggiunta al punto 1 della lista di domattina (una macchina cloud da 256 MB e il picco di 128 MiB).
> - **Decisione notturna, da rivedere**: nell'intestazione (52 byte) un valore di verifica della password (byte 32-47
>   dell'uscita di scrypt, lo schema di WinZip AES), così una password sbagliata (`wrong_password`) si distingue da un
>   file rovinato (`envelope_damaged`) senza aiutare chi prova le password più del tag del primo blocco.

### B3 committato; B-13 e B6a-bis approvati (2026-10-16, 05:19-05:30) — fermo della macchina 05:30-06:45

> - **B3 committato dal coordinatore** come checkpoint intermedio (non è un ingresso): `5f1543e81`
>   `feat(backup): apply checked restore at next start` (20 file), `2c2c8fc3e` `docs(backup): restore an archive,
>   follow or cancel it` (5), `887a24123` `docs(journal): B3 restore, security review, backlog B` (2). HEAD `887a24123`,
>   worktree pulito. Il testo del CHANGELOG lo tiene il coordinatore per l'ingresso; le decisioni notturne (sessioni,
>   P7, P11, `restore_in_use`, il lock) sono nella lista del developer.
> - **B-13 approvato com'è analizzato** (`files/b13-analysis.md` della sessione): `changed` è un avviso, mai un
>   rifiuto; il manifest resta v1. Dopo le 06:45: `api backup`, poi i rossi con test-author; commit separati da B3.
> - **B6a-bis, via alle 05:24** (solo scrittura durante il fermo): la pagina nuova `admin/backup_restore.en.md` dalla
>   scaletta (`files/b6-guide-outline.md`), senza la UI del ripristino (B5b) né gli archivi cifrati (B4), che vanno in
>   B6b; una riga in `filesystem.en.md` «💾 Backup» (di H, permesso del coordinatore); la voce di navigazione sotto
>   «🧹 Maintenance & Operations» con le tre `nav_translations` (etichette date da me); una riga in `admin/index.en.md`.
>   docs-writer al lavoro; `mkdocs build` stretta e `check-links` dopo le 06:45, dopo `api backup`. Commit separato da
>   B-13.

### B6a-bis — la guida «Backup, Restore and Moving Your Instance» (2026-10-16, 05:24-06:55) ✅ — 🧊 FROZEN

> - **docs-writer `a769f9f9`**, solo scrittura durante il fermo (nessuna build, nessun `dev.py`):
>   - pagina nuova `admin/backup_restore.en.md` (301 righe; ancore `#contents`, `#what-follows`, `#create`,
>     `#settings-backup`, `#command-line`, `#keep-copies`, `#check`, `#restore`, `#restore-command`, `#next-start`,
>     `#supervisors`, `#bring-home`, `#to-your-server`, `#by-hand`, `#to-a-hosted-instance`, `#never-backwards`,
>     `#troubleshooting`, `#check-refused`, `#restart-problems`, `#after-restore`);
>   - una frase in testa a «💾 Backup» di `filesystem.en.md` (di H, permesso del coordinatore);
>   - la voce di navigazione dopo «CLI Admin Tools» e le tre `nav_translations` (etichette mie, alla lettera);
>   - un punto in `admin/index.en.md`.
> - **Riletta da me**: i nomi di sezione citati fra «…» (che la build non controlla) esistono tutti, le etichette della
>   UI («Reactivate», quelle della scheda) sono quelle dei cataloghi i18n; nessuna funzione inesistente (né il
>   ripristino dalla scheda né gli archivi cifrati).
> - **⚠️ Fuori pista — niente ancore di `cli_tools` nella pagina nuova**: le pagine it, fr ed es di `cli_tools` non
>   hanno le sezioni del backup, e le build tradotte usano la pagina inglese come ripiego risolvendo i link sulle pagine
>   tradotte: un link a `cli_tools.md#backup…` romperebbe la build stretta (regola della devWiki
>   `docs-anchors-from-the-render`). Rimandi per nome di sezione, come già fa `hosting_providers`.
> - **⚠️ Fuori pista — la scaletta sbagliava in quattro punti**, corretti nella pagina: la cartella è `./LibreFolio-data`
>   (non `./data`); la pagina di blocco **non ha** il pulsante del backup (l'API, la CLI e il pannello sì) → **B-14** nel
>   backlog, proposta per B5 con il permesso di H; per il ripristino da CLI su un'istanza nuova non serve creare prima
>   l'admin; i totali di controllo non sono ancora nel manifest (B-13).
> - **Corretto in `cli_tools`** (sezione mia, di B3): «🚚 Use an Archive on Another Installation» aveva una lista
>   numerata seguita subito da una puntata, che Python-Markdown fonde: aggiunto «Good to know:» fra le due.
> - **Trovati fuori dal perimetro, al coordinatore**: `user/settings/index.en.md` dice «five tabs» (per un admin ora
>   sono sette: Backup ed Email); `configuration.en.md` dice che nessun plugin chiede impostazioni personali (justETF e
>   Borsa Italiana ora le hanno).
> - Debito di traduzione (nessun timbro): la pagina nuova, la frase di `filesystem`, il punto di `index` → B-11.
> - **B-14 in corso, H** (coordinatore, 05:52): la pagina di blocco monta `BackupDownloadCard.svelte` senza props, con
>   un `ToastContainer`; quando entra, B chiude la riga e aggiorna le due frasi della doc. **Vincolo per B5b**: non
>   spostare, rinominare o dare props obbligatorie a quel componente senza dirlo al coordinatore.
> - **H-17** (coordinatore, 06:03, opzione 2, comportamento invariato): dopo l'ingresso di B3, in
>   `backup_max_upload_mb()` il ripiego diventa `profile_default(MAX_UPLOAD_VARIABLE, 0)` di H; proposto di togliere
>   `MANAGED_MAX_UPLOAD_MB` e di fissare nel test (e) il valore del profilo gestito attraverso `profile_default`. B5 e B-13
>   non toccano `config/backup.py`; B7 sì (le variabili di Litestream).
> - **Dopo il fermo** (06:46-06:53, una prova alla volta, `nice`, carico sotto 70): `api backup` **23 passati** (il pin
>   BACKUP-001 riparato, prova che chiude il checkpoint di B3); `mkdocs build` stretta **0 avvisi nostri** (141 s);
>   `check-links` **96 validi**; `utils gate-docs-links` **63 passati**. `dev-cli-image` e `release-image-contract`
>   leggono pagine che B6a-bis non tocca. Porta 6187 libera.

### B-13 — i totali di controllo del registro nel backup (2026-10-16, 07:00-08:40) ✅ — 🧊 FROZEN

> - **Via del coordinatore** (05:25, poi 07:00 dopo il commit di B6a-bis: `2c917e3aa` docs, `ccc92b5a2` journal, HEAD
>   `ccc92b5a2`): `changed` è un avviso, mai un rifiuto; il manifest resta v1; commit separati da B3.
> - **Contratto** (`files/b13-contract.md` della sessione): `instance_backup/totals.py` con `ledger_totals_of(database)`
>   (la funzione di J su un motore dedicato in sola lettura, `aiosqlite` con `?mode=ro` come la `describe_database` di
>   B1, mai il DB vivo, mai un'eccezione) e `compare_totals(recorded, current)` (`same`, `changed` con al più 20 righe di
>   differenza e il conteggio, `absent`, `other_version`, `unreadable`); `ManifestDatabase.control_totals`, letto sulla
>   copia di `VACUUM INTO` prima che entri nello zip; nel report della prova i tre campi e gli avvisi
>   `control_totals_changed` e `control_totals_unreadable` (mai un blocco; valori di default, così un report scritto
>   prima si legge ancora); i campi nell'API (`RestoreTotalsDifference`, docstring di una riga: E-5); una riga nel report
>   della CLI; l'e2e confronta sorgente, manifest e destinazione (via il `TODO(CP-15)`).
> - **⚠️ Fuori pista — l'ordine della decisione**: `ControlTotals.from_json` di J rifiuta anche un'altra versione, quindi
>   la versione si guarda prima di leggere (un `int` diverso → `other_version`; `true` o `"1"` → `absent`, illeggibili).
>   Corretto nel contratto e detto a test-author 1 prima che scrivesse quei casi.
> - **Rossi**: test-author 1 (`test_backup_totals.py` nuovo, registrato come `services backup-totals`; archivio, prova,
>   API, CLI) e test-author 2 (l'e2e), in parallelo su file diversi, solo controlli statici; le prove le lancio io.
> - **Codice in bozza fuori dal repo** (`files/b13-wip/`: `totals.py`, `apply_b13.py` con le ancore), provato a secco su
>   una copia dei sei file in `/tmp`: ogni ancora una volta sola, sintassi a posto. Entra nel worktree dopo il giro rosso.
> - **Rossi scritti** (07:15): test-author 1 — `test_backup_totals.py` 60 test (nuovo, `services backup-totals`), più 13 in
>   `test_backup_archive.py`, 15 in `test_backup_staging.py`, 6 in `test_backup_restore.py`, 10 in `test_backup_cli.py`;
>   test-author 2 — l'e2e (3 test; un registro scritto a mano alla `005` con i totali calcolati a mano: 8772 EUR,
>   2500.5 USD, 10 quote).
> - **⚠️ Fuori pista — i rilievi di test-author 1, decisi da me** (contratto §7; scelte tecniche nel mio perimetro):
>   1. ogni motore del processo esegue `PRAGMA journal_mode=WAL` alla connessione (ascoltatore globale in
>      `db/session.py`), che una connessione `mode=ro` a un file con il giornale di rollback (ogni copia di
>      `VACUUM INTO`) rifiuta: con l'indirizzo del contratto il manifest avrebbe sempre `null`. Lettura `immutable=1`,
>      che non crea niente accanto al file; per sicurezza un `-wal` non vuoto accanto al file dà `unreadable` invece di
>      totali vecchi;
>   2. `control_totals` di tipo qualsiasi nel manifest: un valore malformato non rende l'archivio invalido, risulta
>      `absent`;
>   3. gli importi registrati devono essere testo decimale semplice prima che J li legga: `from_json` espande un
>      esponente per intero (`1E+50000000`: 121 MB) → `absent`; segnalato al coordinatore per J;
>   4. lo stato viene dalle differenze riga per riga (righe zero escluse): righe in altro ordine o una riga zero
>      esplicita danno `same`, e `changed` ha sempre almeno una riga;
>   5. la frase «changed by the upgrade» era falsa senza migrazioni: ora «differ from the backup's»;
>   6. `_report(..., totals=None)` e i tre campi del report con un default: i test di prima e i `report.json` di prima
>      restano validi.
>   Anche: un archivio senza manifest non arriva mai al confronto (`not_a_backup`), il contratto sbagliava.
> - **Giro rosso** (07:53-07:57, dal runner, uno alla volta, `nice`, carico sotto 50 per la regola del coordinatore delle
>   07:48): `services backup-totals` 84 errori (il modulo che manca, importato in una fixture: ognuno da sé);
>   `services backup-archive` 13 rossi e 142 verdi; `services backup-staging` 27 e 118; `api backup-restore` 7 e 114;
>   `utils backup-cli` 11 e 91; `e2e backup-roundtrip` 2 e 1. Ogni rosso per la ragione giusta: il modulo, il campo del
>   manifest o i campi del report che mancano; tutti i test di prima verdi.
> - **Codice nel worktree** (07:57): `totals.py` nuovo, più le modifiche ancorate di `apply_b13.py` (manifest, archivio,
>   prova su copia, schemi e API, CLI); ruff e black puliti.
> - **Giro verde** (07:57-08:11, una prova alla volta, carico sotto 50): `services backup-archive` 155, `backup-staging` 145,
>   `backup-jobs` 69, `api backup-restore` 121 (con `api sync` e `svelte-check` 0/0), `api backup` 23 (la regola del
>   coordinatore), `api backup-restore-apply` 83, `utils backup-cli` 102, `utils backup-cli-restore` 46,
>   `e2e backup-roundtrip` 3, `services backup-apply` 194; `services backup-totals` 84 verdi e **2 errori**.
> - **⚠️ Fuori pista — una connessione aiosqlite lasciata aperta** (la guardia delle perdite del progetto, ai due casi
>   «non è un database» e «troncato»): l'ascoltatore globale `connect` fallisce dopo che `aiosqlite` ha già aperto la
>   connessione, e il pool la scarta senza chiuderla, fuori dalla portata di `engine.dispose()`. Corretto: le connessioni
>   aperte dal nostro `async_creator` si tengono in una lista e si chiudono nel `finally`. Riprova (08:11-08:23):
>   `backup-totals` **84**, `backup-archive` 155, `backup-staging` 145, `e2e backup-roundtrip` 3.
> - **Statici**: `git diff --check` pulito; `check-orphans` 348 file, tutti raggiungibili; vulture niente nei file di B-13
>   (e `compute_control_totals` di J non è più «usato solo dai test»).
> - **Doc** (docs-writer `a769f9f9`, verificata sul codice): in `cli_tools` («🧪 Try a Restore on a Copy») un punto con
>   le cinque righe della CLI alla lettera, gli avvisi nuovi e il riquadro di `manifest.json`; in `backup_restore` la
>   riga di `manifest.json`, la colonna di `--dry-run` e una voce «Ledger totals differ» fra gli avvisi (non nella
>   tabella dei rifiuti: non ha codice); in `security.md` due frasi sulla lettura immutabile e sugli importi semplici,
>   con il link alla pagina di J. Nota per J: `financial_math.md` dice che i totali si confrontano «after a restore», ma
>   il codice li confronta durante la prova, prima della conferma.
> - **Verifiche della doc** (08:31-08:34): `mkdocs build` stretta 0 avvisi, `check-links` 96, `utils gate-docs-links` 63.
> - **Backlog**: B-13 chiusa ✅.

### B5b — la scheda del ripristino (2026-10-16, dalle 08:35) — continua sotto; in dev `0cd910a7e`

> - **B-13 committato** dal coordinatore: `c374313c0` feat, `36bccad06` docs, `1ca7a52c6` journal (HEAD); entra con B3.
> - **Via per B5** (coordinatore, 08:35): le tre raccomandazioni di P8, ognuna «da rivedere» e facile da cambiare;
>   markup nuovo solo con i ruoli `-lf-`, nessun elemento misto; `BackupDownloadCard` resta dov'è, senza props
>   obbligatorie (lo monta H nella pagina di blocco); prima i Vitest, prove leggere con carico sotto 50.
> - **Contratto** (`files/b5b-contract.md` della sessione), dopo aver letto il codice di B5a e le basi:
>   - API: le otto rotte del ripristino con gli alias zodios già generati; il caricamento come corpo grezzo
>     (`requestFormat: 'binary'`) con `onUploadProgress`; la sonda del server (`/system/ready`) e l'esito
>     (`GET /backup/restore/status`) con `fetch` semplice, mai zodios, il cui intercettore dei 401 porterebbe via la
>     pagina;
>   - un controllore `RestoreFlowController` sul modello di `BackupJobController` (stati `loading`, `idle`,
>     `uploading`, `checking`, `report`, `confirming`, `pending`, `in_progress`, `cancelling`, `restarting`, `failed`;
>     generazioni contro le risposte vecchie; ripresa dopo un ricaricamento da `sessionStorage`);
>   - tre componenti nuovi (`RestoreCard`, `RestoreReportModal` su `ModalBase`, `RestartOverlay`), gli eventi
>     `backup.restore.*`, i18n `backup.restore.*` in quattro lingue;
>   - le tre scelte di P8 in un punto ciascuna: l'esito solo nella scheda; `AFTER_RESTORE_PATH =
>     '/settings?tab=backup'` con il `loginUrl()` che c'è già; la parola tradotta, confrontata senza maiuscole e spazi.
> - **Il riavvio**, deciso nel contratto: l'overlay aspetta il server visto giù e poi su (`/system/ready`), poi legge
>   l'esito: un 401 vuol dire sessioni chiuse, cioè ripristino committato (accedi di nuovo); un 200 `rolled_back` mostra
>   il motivo; un 200 `pending` dice che non è stato applicato. Un riavvio troppo veloce per vederlo giù: dopo 30 s
>   si legge l'esito lo stesso; dopo 60 s senza server, «avvia di nuovo LibreFolio».
> - **Rossi**: test-author `96c0577d` (Vitest: controllore, API, tre componenti, completezza i18n), solo scrittura; le
>   prove le lancio io. Chieste al coordinatore quattro righe in `_frontend_utility.py` (liste core-unit e
>   component-unit, file seguito dal programma colori).
> - **09:05**: via del coordinatore alle quattro righe del runner e alle tre scelte di P8 come descritte. Contratto
>   §2b: l'API pubblica del controllore, i nomi comuni a test e codice.
> - **09:20-10:32, STOP del developer**: tutto fermo (nessuna prova in corso, porta libera); il test-author non aveva
>   ancora scritto niente. Worktree lasciato com'era (solo questo piano modificato).
> - **10:32, ripresa. P11 deciso dal developer**: al ripristino si revocano tutti i link monouso, come fatto; verso
>   l'utente **solo un avviso**: inviti e link scaduti, da rimandare se serve, **niente di più**. Quindi:
>   - il report della prova (CLI) dà una riga sola: «Invitations and links sent before the restore will have expired:
>     send them again if needed.», al posto delle due (i link che smettono di funzionare e gli account in attesa di
>     verifica);
>   - la citazione in `cli_tools.en.md` allineata; in `security.md` la frase sul report («gives one notice only»);
>   - la spiegazione degli account in attesa di verifica resta nella doc (comportamento reale e risoluzione dei
>     problemi: `cli_tools` «After the restore», `backup_restore` «What the Next Start Does» e «After a Restore»),
>     detto al coordinatore;
>   - nella scheda (B5b) la stessa riga sola (`restore-report-links`), contratto §3 aggiornato.
>   - I due test-author di prima non esistevano più dopo lo stop: uno nuovo (`3d0a7a3b`) ripara le righe fissate nei
>     test della CLI, un altro (`a30e058d`) riparte con i rossi di B5b. Contratto §2c: l'annullamento di una prova
>     ancora in corso (409 `restore_stage_running`: si aspetta la fine, poi si toglie).
> - P7, P8 e P12: in attesa del developer, niente cambia.
> - **P11, prove** (10:50-11:00; `/tmp` era stato cancellato al riavvio delle 10:03, con il mio script e la cartella
>   dati della corsia: lo script ora sta nella cartella della sessione, `files/scripts/b_green.sh`, con i log in
>   `files/logs/`, regola del coordinatore): `utils backup-cli` 102, `utils backup-cli-restore` 46 (la riga sola, e
>   nessuna delle due vecchie, guardate anche con «send new ones» e «stop working»), `mkdocs build` stretta 0 avvisi,
>   `check-links` 96, `utils gate-docs-links` 63. Porta libera.

### Decisioni del developer su P7, P8 e P12 (2026-10-16, 11:11-11:25)

> - **P11 committato** dal coordinatore: `51fa21b59` fix, `4ec25ade0` journal (HEAD). La doc sugli account in attesa di
>   verifica resta com'è: spiega il comportamento reale.
> - **P7** («se l'app è bloccata, che ripristino avvierei? Il ripristino resta bloccato anche lui finché non pagano, da UI
>   e da API»): un ripristino confermato prima del blocco **non si applica** finché l'istanza è bloccata, aspetta lo
>   sblocco (`waiting = instance_blocked`); le rotte restano bloccate come sono. La mia decisione notturna («applicato
>   comunque») cade. Contratto B3 §11: l'ordine dei motivi (altra cartella dati, poi `instance_blocked`, poi server
>   acceso e backup in corso); un `LIBREFOLIO_BLOCKED` illeggibile conta come bloccato; le riparazioni (annullamenti) e il
>   commit restano anche da bloccata. Rossi al test-author `3deeac3c`.
> - **P8**, la scheda del ripristino (approvato come l'ho letto alle 11:25):
>   - dopo la prova e la conferma il server si riavvia subito (niente passo «Riavvia ora» separato; il blocco «in attesa»
>     resta per un ripristino trovato in attesa: confermato da CLI, o un riavvio non partito);
>   - **successo senza messaggio** («se ha funzionato lo vedi»): la pagina va dritta al login, poi alla solita pagina
>     iniziale; la scheda non mostra «ripristino applicato» (`restoreNavigation`, un punto solo);
>   - **fallimento sulla stessa schermata**, con il motivo (annullato, o non applicato, `instance_blocked` compreso);
>   - **la parola di conferma**: una parola vera a caso, 6-10 lettere, nella lingua dell'interfaccia, scritta **senza
>     copia e incolla** (incolla e trascina bloccati sul campo); liste curate in un frammento i18n
>     (`backup.restore.confirm.words`, minuscole senza accenti: 59 en, 50 it, 46 fr, 46 es), un test sulle quattro liste;
>     controllata **solo nella pagina** (protegge da un clic frettoloso, non da un attacco: un admin può sempre chiamare
>     l'API). Valutato e scartato il controllo sul server (mezza giornata: rotta, prova, CLI, quattro liste anche lì).
>   Contratto B5b §0 riscritto; bozze in `files/b5b-wip/` aggiornate (123 chiavi per lingua, tutte usate); il test-author
>   `a30e058d` scrive i rossi sul contratto nuovo.
> - **P12**, B4 (non adesso): scrypt `n = 2^15` (32 MiB); la password segue le regole e l'indicatore `PasswordStrength`
>   della registrazione e del cambio password (A6c), più un minimo di 12 caratteri (contratto B4 §8).
> - **11:30, domanda di A** (P18, migrazione 009, email unica senza badare alle maiuscole): il report della prova non
>   mostra l'errore della migrazione così com'è (API e scheda: solo `upgrade_failed`; CLI: «the log of the server has the
>   details»); il log del server ha gli ultimi 4000 caratteri dello `stderr` di alembic. A si accontenta di una riga di
>   doc che rimandi al log; la scrivo io quando 009 entra nella mia base (testo e comando di A in
>   `files/a009-doc-line.md`).
> - **P7, i rossi** (test-author `3deeac3c`): `services backup-apply` 210 (16 nuovi), `api backup-restore-apply` 84,
>   `utils backup-cli-restore` 51 e oltre. Rilievi decisi:
>   - la CLI non rifiuta su un'istanza bloccata (la usa chi gestisce il server): conferma e aggiunge la riga
>     `instance_blocked` (coordinatore d'accordo, 11:38);
>   - `backup pending` legge il blocco anche al momento: una riga sola, dopo quella registrata da un avvio;
>   - nessuna scadenza per un ripristino in attesa durante il blocco (coordinatore d'accordo); nella doc le due
>     conseguenze: il disco occupato dalla copia (`backup pending --cancel`) e la migrazione al primo avvio dopo lo
>     sblocco se LibreFolio è stato aggiornato nel frattempo.
>   Codice e doc pronti in script ancorati (`files/b3-wip/apply_p7.py`, `apply_p7_docs.py`), provati a secco.
> - **B5b, i rossi** (test-author `a30e058d`, solo Prettier): `restoreFlow.test.ts` 167, `backupApi.test.ts` +40,
>   `RestoreCard.test.ts` 42, `RestoreReportModal.test.ts` 40, `RestartOverlay.test.ts` 14, `restoreI18n.test.ts` 96 (le
>   chiavi nei quattro cataloghi e le liste delle parole). Moduli mancanti caricati con `import.meta.glob`: ogni test
>   fallisce da sé. Decisione mia: un riavvio rifiutato con `restore_not_pending` (ripristino annullato da CLI nel
>   frattempo) dà `failed`, non un blocco «in attesa» che non esiste più. Le bozze adattate alle scelte del test-author
>   (l'overlay riceve lo `status`, `restore-cancel-check` ferma anche l'invio, `load()` azzera l'overlay); cinque righe
>   del runner invece di quattro (`restoreI18n.test.ts` in core-unit), detto al coordinatore.

### P7 — rosso, codice, verde (2026-10-16, 11:49-12:28) ✅ — committato

> - **11:49, i casi di `backup pending`** (test-author `3deeac3c`): una matrice di 15 casi (ciò che ha registrato
>   l'ultimo avvio × il blocco letto ora: `true`, illeggibile, assente) e una guardia di 12 (nessun ripristino, o non in
>   attesa: mai la riga del blocco). Deciso: **`other_data_directory` vince anche qui**, come all'avvio: una copia della
>   cartella dati non applica mai il ripristino, e la riga del blocco prometterebbe il falso. Regola: la riga del blocco
>   esce quando `waiting == instance_blocked`, oppure quando l'istanza è bloccata ora e `waiting` non è
>   `other_data_directory`; una volta sola, dopo la riga registrata. Bozza `apply_p7.py` e doc di `cli_tools`
>   («the last start found the instance blocked, or it is blocked now») allineate. File della CLI: 77 test.
> - **Giro rosso** (11:54-12:02, carico sotto 50): `services backup-apply` 8 rossi su 210, `api backup-restore-apply`
>   2 su 84, `utils backup-cli-restore` 12 su 77. Tutti e soli i previsti (motivo nuovo nel `Literal`, attesa da
>   bloccata con `true`, `1`, `yes`, `ON` e con un valore illeggibile, ordine prima di backup e server, OpenAPI, la riga
>   dopo `restore --yes`, la matrice di `pending`).
> - **⚠️ Fuori pista**: alle 11:55 un errore di rete del servizio ha interrotto il mio turno; il test-author di B5b
>   (`a30e058d`) è morto sullo stesso errore durante la richiesta su `restore_not_pending`. La modifica era già salvata
>   (11:51): i due casi (dopo la conferma e con `restartNow()`) danno `failed` (`restart`), annunciato, niente sonda, lo
>   stato riletto solo da `retry()`; intestazione del file allineata. Prettier pulito sui sei file; la bozza
>   `restoreFlow.svelte.ts` lo fa già. La prova della corsia (PID 76895) era la mia: lasciata finire.
> - **12:03, applicati** `apply_p7.py` (`apply.py`: `_blocked()` e il controllo dopo `other_data_directory`;
>   `schemas/backup.py`; `backup_cli.py`: `_instance_blocked()`, la riga dopo la conferma e in `pending`; descrizione
>   del catalogo) e `apply_p7_docs.py` (`hosting_providers`, `security.md`, `cli_tools`, `backup_restore`). Ruff e black
>   puliti sui sette file Python toccati. `config.platform` importa solo `os`, `datetime` e `config`: leggero per il
>   primo passo d'avvio.
> - Doc: `cli_tools` ha le traduzioni, ma le righe nuove sono comportamento nuovo: debito di traduzione vero, nessuno
>   stamp. `hosting_providers` e `backup_restore` sono solo in inglese.
> - **Giro verde** (12:03-12:22, `files/scripts/b_green.sh`, carico sotto 50): `services backup-apply` 210,
>   `api backup-restore-apply` 84 (svelte-check 0/0 sul client rigenerato, con `instance_blocked`),
>   `utils backup-cli-restore` 77, `utils backup-cli` 102, `api backup` 23, `services app-lifecycle` 42,
>   `e2e backup-roundtrip` 3. Porta 6187 libera.
> - **Doc** (12:22-12:27, `files/scripts/b_docs.sh`): `mkdocs build` stretta 0 avvisi, `check-links` 96,
>   `utils gate-docs-links` 63. `git diff --check` pulito.
> - **12:28, handoff del checkpoint P7** al coordinatore, 🧊 FROZEN: 12 file tracciati (7 codice e test, 4 doc, questo
>   piano), nessun file nuovo. Esclusi i rossi di B5b (`backupApi.test.ts` e i cinque file nuovi di
>   `features/backup/`): restano rossi finché il codice non entra. Il giro rosso di B5b dopo il commit (carico a 122).

### B5b — rosso, allineamento al design system, codice, verde (2026-10-16, 12:28-13:25) ✅ — continua dopo la pausa

> - **P7 committato** dal coordinatore: `e895fcd97` fix, `b63a00864` docs, `9686942c6` journal (HEAD). Approvata la
>   scelta su `pending` (`other_data_directory` vince); l'aggiunta al CHANGELOG di B3 («never applied while the instance
>   is blocked») la tiene il coordinatore.
> - **Skill nuova `design-system`** (decisione D-T29, `6e569084a` in `dev_release2`, arriva al prossimo aggiornamento di
>   base): letta con `git show 6e569084a:…` (copia in `files/design-system-SKILL.md` della sessione), non dai file del
>   checkout principale. Vale subito per i componenti nuovi di B5b. Le bozze erano già solo ruoli `-lf-` (nessuna
>   palette, nessun esadecimale, nessun `dark:`, testo primario sulla radice, ogni bordo col suo ruolo); corretti
>   (`files/b5b-wip/align_design_system.py`):
>   - **fuoco dei pulsanti** (regola 8): `focus-visible:outline-2 focus-visible:outline-offset-2
>     focus-visible:outline-lf-focus` al posto di `focus:outline-none` più l'anello; il campo della parola
>     `focus:border-lf-focus focus:ring-1 focus:ring-lf-focus` (lo schema dei campi in `dev`);
>   - **hover sul pannello** (domanda aperta 3: `hover` = `panel`, non si vede): i pulsanti secondari della scheda, che
>     sta su `bg-lf-panel`, passano a `hover:bg-lf-neutral`; quelli nel modale e nell'overlay (sulla carta) restano
>     `hover:bg-lf-hover`;
>   - **pulsanti rossi pieni**: `hover:bg-lf-danger-hover` (Q3); nel modale `enabled:hover:` e
>     `disabled:cursor-not-allowed`, così un pulsante spento non cambia colore;
>   - **nessuna seconda cornice dentro `ModalBase`** (regola 9): in `dev` il `ModalBase` disegna carta, bordo
>     `raised`, ombra e raggio; il contenuto del report tiene solo `max-h-[85vh] space-y-4 overflow-y-auto p-5
>     text-lf-primary`. Fino all'aggiornamento di base il `ModalBase` di questa base ha ancora la cornice legacy;
>   - **l'overlay del riavvio su `ModalBase`** (regola 9: un modale usa `ModalBase`): non chiudibile
>     (`closeOnBackdropClick={false}`, `closeOnEscape={false}`), `zIndex` 80, `trapFocus`; lo stato pubblicato
>     (`restart-overlay`, `data-outcome`, `data-slow`) passa all'elemento interno, l'unico che i test leggono;
>   - **riempimento della barra d'avanzamento**: `bg-lf-action` sul binario `bg-lf-neutral` fa **1,6:1 nel tema
>     scuro** (`#215240` su `#222c28`), sotto il 3:1 di WCAG 1.4.11; `bg-lf-checked` (il ruolo del «segmento attivo»)
>     fa 4,4:1 in scuro e 4,8:1 in chiaro. Ruolo più vicino, **«da rivedere»** (D-T27): da segnalare al coordinatore dei
>     colori per T (un ruolo per l'avanzamento?).
> - **Anche `BackupDownloadCard` (B5a)**, stessa scheda e stesse regole: lo stesso difetto della barra in scuro, lo
>   stesso hover invisibile sul pannello, lo stesso fuoco. Solo classi, nessuna prop né test id (H lo monta sulla pagina
>   di blocco): `files/b5b-wip/align_b5a.py`, applicato con B5b; da dire al coordinatore.
> - **Giro rosso** Vitest sui sei file (`files/scripts/b_vitest.sh`, carico sotto 50): avviato alle 12:33, carico a 128.
>   Alle 12:41: **396 rossi, 55 verdi** su 451 (i 51 di B5a in `backupApi.test.ts` e i 4 di `restoreI18n.test.ts` verdi
>   per costruzione); tutti e soli i motivi previsti (modulo, export o chiave che mancano).
> - **12:42, applicati** `apply_b5b.py` (cinque moduli nuovi, le funzioni in `backupApi.ts`, `RestoreCard` in
>   `BackupTab.svelte`, le cinque righe del runner, 123 chiavi × 4 lingue) e `align_b5a.py`; Prettier.
> - **Primo verde** (otto file, i sei più `BackupDownloadCard.test.ts` e `backupJob.test.ts`): 3 rossi, 96 saltati.
>   - **⚠️ Fuori pista**: i tre file dei componenti scadono nel `beforeAll` da 60 s (il caricamento con
>     `import.meta.glob`, lo schema di `GapFixStep.test.ts`): sotto carico la prima trasformazione (Svelte, `ModalBase`,
>     il barile di `lucide-svelte`) ha superato il minuto (185 s di trasformazione sommati). `BackupDownloadCard.test.ts`,
>     che monta la stessa scheda con un import statico, era verde. Rilanciati da soli, come vuole la regola del
>     coordinatore: si caricano.
>   - **Difetti veri delle bozze**, corretti nel worktree (da qui la fonte è il worktree, non le bozze):
>     `pickConfirmationWord` ripiega da sé sulla parola tradotta `backup.restore.confirm.word` (prima lo faceva il
>     modale); il testo del blocco «nessun amministratore» sotto una chiave che finisce col suo codice,
>     `backup.restore.blocker.no_administrator` (era `report.noAdministrator`; `fix_blocker_key.py`, appena prima di
>     `report`, l'ordine dei file conservato); il blocco della conferma (parola, campo, pulsante) **sempre disegnato**, e
>     spento finché l'archivio non è ripristinabile o ha un blocco (`confirmable = restorable && blockers.length === 0`;
>     prima spariva, e un report «ripristinabile» con il blocco si poteva confermare); `data-reason` e `data-waiting` sulla
>     radice `restart-overlay` (erano sul paragrafo interno).
> - **Verde** (12:53-12:56, a gruppi per il carico): `restoreFlow` + `restoreI18n` 264; i tre componenti 96;
>   `BackupDownloadCard` + `backupJob` + `backupApi` 273. Totale 633, lo stesso conteggio del primo giro.
> - **Controlli statici** (`files/scripts/b_static.sh`, uno alla volta, 13:03-13:08): ratchet dei colori pulito
>   («0 files dropped below their record»); i nove file dei cancelli 177 verdi; `i18n check` pulito (4824 chiavi,
>   «strict»); `lint --dead-code --scope frontend` esce 1, ma nessun reperto è in `features/backup` (file, export e tipi
>   inutilizzati altrove, già nella base); **`front check`: 18 errori e 1 avviso, tutti nei file nuovi**:
>   - **⚠️ Fuori pista**: i tipi TS espliciti che il generatore scrive per `RestoreStage` (e il `RestoreStageReport` che
>     contiene) allargano ogni campo nullabile a `T | null | (T | null)[]`, un ramo che lo schema zod non lascia passare
>     (la stessa stranezza che `safeScalar` di `$lib/types/common` scarta a run time altrove; 822 `| Array<` in
>     `generated.ts`). `RestoreStatus` e il job di B5a sono inferiti, quindi puliti. Cura in `backupApi.ts`: un tipo
>     `Unwidened` che toglie il ramo array dove convive con altri rami (un campo che è solo un array resta tale; nessun
>     campo dei due schemi è un array nullabile, verificato su `openapi.json`), e un solo cast nelle due funzioni che
>     restituiscono una prova, dopo la validazione zod;
>   - l'avviso: `random()` letto una volta all'apertura del modale, ora con `untrack`, che dice l'intenzione.
> - **Guida** (B6b, `docs-writer` in background, solo scrittura): la sezione «🖱️ Restore from Settings › Backup» e gli
>   aggiornamenti di «Bring home», «to a hosted instance» e della risoluzione dei problemi; la frase «Today it runs on
>   the server, from the command line» non è più vera.
> - **13:16, la guida è scritta** (`docs-writer` `1a89fad1`): `backup_restore.en.md` (sezione nuova `#restore-settings`,
>   tabella `#restore-settings-problems`, ritocchi in «Bring home», «to a hosted instance», «Who Starts LibreFolio
>   Again», risoluzione dei problemi) e `hosting_providers.en.md` (tre ritocchi); solo inglese, nessun debito di
>   traduzione. Nessuna build lanciata. Ha trovato cinque scarti fra codice e brief; decisi:
>   1. **istanza bloccata durante il riavvio**: la rotta dello stato risponde 423 `instance_blocked` (`/system/ready` 200),
>      l'esito diventa `down` e l'overlay aspetta per sempre; il «`instance_blocked` compreso» approvato per P8 non
>      arriva mai alla pagina. **Si corregge in B5b**: `restoreOutcome()` 423 con quel codice → `{kind: 'blocked'}`; il
>      controllore lo rende `still_pending` con `outcomeStatus = {state: 'pending', waiting: 'instance_blocked'}`, niente
>      annuncio; «Back to Backup» arriva alla pagina di blocco con l'intercettore del client;
>   2. **«Cancel the restore» lasciava la copia della prova sul disco** (la CLI `--cancel` la toglie): **si corregge in
>      B5b**, dopo un annullamento riuscito `DELETE /stage/{stage_id}` best effort; con `restore_not_pending` niente;
>   3. «Try again» rilegge lo stato e basta: solo doc;
>   4. un 413 di un proxy dà il messaggio generico: backlog **B-15**;
>   5. un server che non scende lascia l'overlay in attesa senza suggerimento: backlog **B-16**, e una riga di doc.
> - **Ultimo giro prima della pausa**: con i tipi corretti, `restoreFlow` + `restoreI18n` + `backupApi` 355 verdi (13:19);
>   `front check` sceso a 4 errori in un file (`tables` scritto `{}` dal tipo esplicito del generatore: corretto in
>   `backupApi.ts` con `Record<string, RestoreTableRows>`, **non ancora riverificato**). Il gruppo dei componenti fermato
>   apposta: il test-author stava per toccare i file.
> - **Rossi in scrittura** (test-author `817f0858`, solo scrittura): `backupApi.test.ts` (423), `restoreFlow.test.ts`
>   (esito `blocked`, `cancelPending` con il `DELETE /stage`), `RestoreCard.test.ts` (un caso per ciascuno). La guida
>   aggiornata ai punti 1, 2, 3 e 5 (`docs-writer`, stesso agente).

### ⏸️ PAUSA del developer (2026-10-16, 13:25-14:14) — ripresa

> - HEAD `9686942c6`, nessun merge aperto, porta 6187 libera, nessun mio comando in corso. Ai due specialisti in corsa
>   (test-author `817f0858`, `docs-writer` `1a89fad1`) chiesto di finire la modifica in corso e fermarsi.
> - **Sporchi** (tutti di B5b, niente da committare a metà): `BackupDownloadCard.svelte`, `BackupTab.svelte`,
>   `backupApi.ts`, `backupApi.test.ts`, i cinque moduli nuovi e i cinque test nuovi di `features/backup/`, i quattro
>   `i18n/backup/*.json`, `_frontend_utility.py` (cinque righe), `backup_restore.en.md`, `hosting_providers.en.md`, il
>   backlog (B-15, B-16), questo piano.
> - **Alla ripresa**: leggere le note dei due specialisti; giro rosso su `backupApi`, `restoreFlow`, `RestoreCard`;
>   applicare i due cambi (`restoreOutcome` 423 → `blocked`, `#settle` → `still_pending`/`instance_blocked`;
>   `cancelPending` → `dropCheck` best effort, docstring); Prettier; `front check`; Vitest a gruppi (gli otto file);
>   le liste del runner `front-utility core-unit` e `component-unit`; `mkdocs build`, `check-links`,
>   `utils gate-docs-links`; diario; handoff FROZEN. Poi E2E e galleria negli slot pesanti.
> - **Durante la pausa** (solo note nella cartella della sessione, `files/pause-1325-notes.md`, poi riportate qui):
>   - il `docs-writer` aveva già finito i cinque punti in `backup_restore.en.md` (la riga dell'istanza bloccata durante
>     il riavvio, con «Back to Backup» verso la pagina di blocco; «Cancel the restore» che toglie anche la copia, come
>     `backup pending --cancel`; «Try again» che rilegge lo stato; la riga del 413 di un proxy com'era; una riga nuova per
>     il server che non scende, con un rimando dall'esito «It takes long»). I punti 1 e 2 descrivono codice non ancora
>     applicato: da ricontrollare quando entra;
>   - il test-author si è fermato **senza aver toccato file**: casi disegnati, nessuno scritto;
>   - a H (tramite il coordinatore): `RestoreCard` è un componente suo, montato solo in `BackupTab`, mai dentro
>     `BackupDownloadCard`; la pagina di blocco, che monta `BackupDownloadCard`, resta solo con crea, scarica, cancella
>     (P7). B5b tocca `BackupDownloadCard` solo nelle classi;
>   - regola C-99 del developer (`b171c058e`): fino al riordino del manuale admin alla fine della 1.3, una variabile
>     nuova si spiega per intero nella pagina della sua funzione e ha una sola riga, con il link, in
>     `configuration.md` (vale per B7, Litestream);
>   - regola dei colori (T `a317392d4`): un `<input>` di testo, una `<textarea>` o una `<select>` con classi `-lf-`
>     nomina da sé `text-lf-primary`, e `placeholder:text-lf-placeholder` se ha un segnaposto. B5b la rispetta già (il
>     campo della parola ha tutti e due; il selettore del file è `type="file"` e `hidden`); vale per i campi di B4.

### ▶️ Ripresa (2026-10-16, 14:14-14:50) — B5b: i due fix, i controlli, l'handoff ✅ — 🧊 FROZEN

> - Via del coordinatore («the developer has resumed»): i due fix dei rilievi del `docs-writer`, prima i rossi, poi i
>   controlli e l'handoff di B5b; prove leggere con carico sotto 50. HEAD `9686942c6` e worktree come alla pausa.
> - Il test-author `817f0858` scrive i casi disegnati; intanto i controlli della doc (non leggono i file dei test).
> - **Doc** (14:14-14:20, `b_docs.sh`): `mkdocs build` stretta 0 avvisi, `check-links` 96, `utils gate-docs-links` 63;
>   porta libera.
> - **I rossi** (test-author, 14:20-14:23, solo Prettier): `backupApi.test.ts` (un 423 col corpo vero del backend →
>   `blocked`, rosso; dieci righe che restano `down`: un altro codice, nessun codice, un dettaglio stringa, il codice
>   fuori da `detail`, `null`, nessun corpo, non JSON, `instance_blocked` su 403, 409 e 200), `restoreFlow.test.ts`
>   (`blocked` dopo giù e su, alla lettura veloce, e la riga della tabella degli esiti: `still_pending`, `outcomeStatus`
>   esattamente `{state: 'pending', waiting: 'instance_blocked'}` con `toStrictEqual`, nessun annuncio, nessun
>   `toSignIn`, nessun timer; `cancelPending` con `dropCheck(STAGE_ID)` fra l'annullamento e la rilettura, `cancelling`
>   mentre la cancellazione è in corso; un rifiuto della cancellazione della copia ignorato, in quattro forme; dopo un
>   riavvio rifiutato si toglie la copia della conferma; guardie verdi: `stage_id` nullo o assente,
>   `restore_not_pending` e gli altri rifiuti non toccano la copia, con `not.toHaveBeenCalled()` esplicito),
>   `RestoreCard.test.ts` (un caso da capo a fondo per `blocked`, e l'annullamento con `deleteRestoreCheck`).
> - **⚠️ Fuori pista — rilievo del test-author, decisione chiesta al coordinatore (14:24)**: la rotta dello stato
>   controlla la sessione prima del blocco, e un 401 vale «ripristinato». Ma **senza `JWT_SECRET`** il server fa una
>   chiave casuale a ogni avvio (`auth_service.py:106`): **ogni** riavvio chiude tutte le sessioni, quindi su Docker di
>   default e con `dev.py server` la pagina conclude sempre «ripristinato» e va al login senza messaggio; un ritorno
>   indietro o un ripristino non applicato si vedono solo in Impostazioni › Backup dopo l'accesso. Con `JWT_SECRET`
>   (il cloud) il fallimento è sull'overlay, come deciso. Proposte: **(A)** un biglietto monouso dell'esito
>   (`GET /backup/restore/outcome` col biglietto in un header, il suo hash in `.restore/`, permesso anche da bloccata;
>   lotto B5c, mezza giornata; la mia raccomandazione); **(B)** solo con esito incerto (un 401) il login torna a
>   `/settings?tab=backup`, che sul successo non dice niente e sul fallimento dice perché; **(C)** solo doc. Intanto
>   (C) nella guida, chiesta al `docs-writer`.
> - **Giro rosso** (14:28-14:32): 12 rossi su 323, tutti e soli i previsti, più i quattro `TypeError` attesi del
>   `#settle` di oggi sul tipo sconosciuto.
> - **Codice** (14:33): `restoreOutcome()` 423 con `detail.code` `instance_blocked` → `{kind: 'blocked'}` (aiuto
>   `refusedForTheBlock`), `#settle` → `still_pending` con `{state: 'pending', waiting: 'instance_blocked'}`, niente
>   annuncio; `cancelPending()` tiene lo `stage_id` dello stato e, dopo un annullamento accettato, `dropCheck` best
>   effort (con `restore_not_pending` niente); docstring aggiornata. **Verde** (14:34): 323 su 323.
> - **Il resto** (14:35-14:45): `front check` **0 errori, 0 avvisi** (i tipi `Unwidened`, `tables` come
>   `Record<string, RestoreTableRows>`, `untrack`); gli altri cinque file (`RestoreReportModal`, `RestartOverlay`,
>   `restoreI18n`, `BackupDownloadCard`, `backupJob`) 332; le liste del runner **`front-utility core-unit` 173 file,
>   6232 test** e **`component-unit` 149 file, 3957 test**, verdi (le cinque righe nuove registrate). Porta libera.
> - **Guida, seconda passata** (`docs-writer`): punto 1 conforme al codice; il punto 2 no, per un caso: un ripristino
>   **confermato dalla CLI** non ha il record della prova, il `DELETE /stage` della scheda è rifiutato (e ignorato), e
>   la copia resta in `.restore/stage/` finché una prova avviata dalla scheda non la trova vecchia di 24 ore. La guida
>   dice di annullarlo dalla riga di comando; la cura vera è lato server (`DELETE /pending` con
>   `cancel_restore(drop_copy=True)`, come la CLI, e la scheda smette di chiamare `dropCheck`): backlog **B-17**, da fare
>   con il biglietto dell'esito (B5c) se scelto, perché tocca la stessa API. Aggiunta (C): senza `JWT_SECRET` la pagina
>   va al login qualunque sia l'esito, e Impostazioni › Backup dice perché (rimando a
>   `index.md#session-persistence`); tolto «needed with several workers» (i worker di un `dev.py server` condividono
>   la chiave da soli).
> - `RestoreTableRows` non più esportato (lo usa solo `backupApi.ts`: knip l'avrebbe segnalato). Ultimi controlli
>   (`files/scripts/b_final_static.sh`): Prettier su `features/backup` e `i18n/backup`, ratchet dei colori, knip,
>   `front check`, poi `mkdocs build`, `check-links`, `utils gate-docs-links`.
> - **Ultimi controlli** (14:46-14:49): Prettier pulito su `features/backup` e `i18n/backup`; ratchet dei colori pulito;
>   knip con gli stessi reperti delle 13:08, nessuno in `features/backup` o `i18n/backup`; `front check` 0/0;
>   `mkdocs build` stretta 0 avvisi; `check-links` 96; `utils gate-docs-links` 63; `git diff --check` pulito; porta
>   libera.
> - **14:50, handoff del checkpoint B5b** al coordinatore, 🧊 FROZEN: 13 file tracciati modificati e 10 nuovi
>   (`features/backup/`: cinque moduli e cinque test). In attesa: la decisione (A)/(B)/(C) sull'esito senza
>   `JWT_SECRET`; B-15, B-16, B-17 nel backlog; E2E (`e2e/settings/backup.spec.ts`) e galleria negli slot pesanti.

### B5c — l'esito di un ripristino senza sessione (biglietto monouso) e B-17 (2026-10-16, 15:02-18:22) ✅ — 🧊 FROZEN

> - **B5b committato** dal coordinatore: `1e2f6374a` feat (19 percorsi), `2efb36ffb` docs, `de4d0e293` journal (HEAD).
>   **Il developer ha scelto (A)**, il biglietto monouso: lotto B5c dopo B5b, con B-17. E2E e galleria di B5b in coda
>   per uno slot.
> - **Analisi** (intera in `files/b5c-analysis.md` della sessione):
>   - **biglietto** emesso da `POST /backup/restore/restart` (ogni richiesta ne emette uno nuovo, che sostituisce il
>     precedente; non alla conferma: anche un ripristino trovato in attesa, confermato da CLI, si riavvia dalla
>     scheda), `secrets.token_urlsafe(32)`, solo in quella risposta (`RestoreRestartAccepted`, `Cache-Control:
>     no-store`), mai nei log;
>   - **conservato** come hash in un file suo, `.restore/outcome-ticket.json` (`sha256`, `stage_id`, `issued_at`,
>     `expires_at`; 0600, scrittura atomica senza seguire i link): fuori da `RestoreState`, così la macchina a stati
>     di `apply.py`, rivista in B3, resta intatta; `.restore/` non si scambia mai, quindi il file sopravvive al
>     riavvio, allo scambio, al commit e al ritorno indietro;
>   - **scadenza** un'ora dalla richiesta di riavvio (costante, nessuna variabile nuova); **monouso**: consumato quando
>     la rotta dà un esito finale (`committed`, `rolled_back`); `pending` e `in_progress` no; tolto anche da una
>     conferma nuova, da un annullamento (API e CLI), da una lettura che lo trova scaduto; legato allo `stage_id`;
>   - **rotta** `GET /backup/restore/outcome`, **senza sessione**, biglietto nell'header `X-Restore-Ticket` (mai
>     nell'URL), risposta minima `{state, reason, waiting}` (niente nomi, date, versioni, percorsi), un 404 identico
>     per ogni biglietto che non vale (`restore_outcome_not_found`), confronto a tempo costante;
>   - **da bloccata deve rispondere** (P7/P8: «non applicato, bloccata» sull'overlay): una voce in
>     `ALLOWED_WHEN_BLOCKED` di H (`instance_block.py`: import dopo la riga 34, voce dopo la riga 62, più la frase della
>     docstring alle righe 9-14; `test_instance_block.py`: una voce in `ALLOWED_ROUTES` dopo la riga 146). Non avvia
>     niente: riporta l'esito di un riavvio già chiesto alla pagina che l'ha chiesto. Un'aggiunta alla lista passa dal
>     developer;
>   - **B-17**: `DELETE /pending` con `cancel_restore(drop_copy=True)`, come la CLI; la scheda smette di chiamare
>     `dropCheck`;
>   - **frontend**: il controllore tiene il biglietto in memoria per quel riavvio (mai in storage); `restoreOutcome`
>     col biglietto legge la rotta nuova, con un 404 ricade sulla lettura di oggi (riavvii da CLI, biglietto scaduto);
>   - **doc**: `security.md` (rotta, biglietto, lista del blocco, `DELETE /pending`), la guida (via la limitazione
>     (C) di `JWT_SECRET`; B-17), `hosting_providers.en.md` (la tabella di ciò che risponde da bloccata, riga 177).
> - **Test** (test-author, prima i rossi): `api backup-restore-apply` (emissione, hash, 0600, sostituzione, senza
>   cookie, solo header, 404 identici, consumo, campi minimi, `no-store`, niente log, istanza bloccata, conferma e
>   annullamento che lo tolgono, B-17); `api instance-block` (la voce di H); frontend (`backupApi`, `restoreFlow`,
>   `RestoreCard`). Poi `security-review` sul diff.
> - **Coda per gli slot (B5b)**: l'E2E estende `e2e/settings/backup.spec.ts` (`front-utility backup`, nessun cambio al
>   runner) col ripristino (caricamento, prova, report, parola scritta e incolla rifiutato, riavvio finto con
>   `page.route`, gli esiti, il blocco in attesa); la galleria di G accanto a `settings/backup-ready` (scheda,
>   report, overlay del fallimento).
> - Stima: mezza giornata. Analisi al coordinatore; 🧊 FROZEN fino al via.
> - **15:11, via del coordinatore** col disegno così com'è (B-17 compreso). Le due righe di `instance_block.py` e
>   `test_instance_block.py` le concorda con H; intanto tutto il resto, prima i rossi; `security-review` sul diff finale;
>   poi E2E e galleria di B5b in uno slot (li organizza con G dei colori).
> - **Contratto** `files/b5c-contract.md` della sessione (nomi condivisi da codice e test). **Rossi** a due test-author
>   in parallelo, su file distinti, solo scrittura: backend `628939b5` (`test_backup_outcome.py` nuovo, con la voce
>   `services backup-outcome` del runner; `test_backup_apply.py`; `test_backup_restore_apply.py`), frontend `52dd383e`
>   (`backupApi.test.ts`, `restoreFlow.test.ts`, `RestoreCard.test.ts`, con B-17: niente più `dropCheck`).
> - **Bozze** in `files/b5c-wip/`: `outcome.py` (il modulo intero) e `apply_b5c_backend.py` (`paths.py`, `apply.py`
>   con `drop_ticket` alla conferma e all'annullamento, gli schemi `RestoreRestartAccepted` e `RestoreOutcome`, le
>   rotte, B-17), provato a secco su copie dei quattro file: si applica e compila; black pulito; ruff solo I001
>   (l'ordine degli import, fuori dal repo ruff non riconosce `backend` come primo: `--fix` nel worktree). Le modifiche
>   del frontend dopo i rossi, con il client rigenerato (`RestoreRestartAccepted`, `RestoreOutcome`).
> - **Rossi del frontend** (test-author `52dd383e`, 15:15-15:45, solo Prettier): `backupApi.test.ts` 175 casi (71
>   rossi: l'header, la richiesta col biglietto, gli esiti validi, il ripiego, la tabella dei `down`, la replica di
>   `requestRestart` sul client generato, rossa finché il client non è rigenerato), `restoreFlow.test.ts` (14 rossi: B-17
>   senza `dropCheck` in sei casi; il biglietto in sette: dopo giù e su, alla lettura veloce, un secondo riavvio,
>   `restartNow()`, nessun biglietto sopravvive al suo riavvio, una risposta vecchia non porta il suo, solo in memoria),
>   `RestoreCard.test.ts` (3 rossi). **Cambio mio al contratto** (15:40): un 401 o un 423 della rotta dell'esito
>   ricadono sulla lettura di oggi come un 404 (la rotta non è raggiungibile per questo chiamante: la voce della lista del
>   blocco che manca, un proxy), altrimenti l'overlay aspetterebbe per sempre senza suggerimento; un 5xx resta `down`
>   (transitorio all'avvio).
> - **Giro rosso del frontend** (15:53): 88 rossi su 407, 71 + 14 + 3, tutti e soli i previsti; nessun errore non gestito.
> - **Rossi del backend** (test-author `628939b5`, 15:15-15:58; ruff, black e `--collect-only` puliti):
>   `test_backup_outcome.py` nuovo, 95 casi (`services backup-outcome`, registrato accanto a `backup-apply`), tutti
>   rossi; `test_backup_apply.py` +13 (sezione (n): la conferma riuscita toglie il biglietto, una rifiutata lo tiene;
>   l'annullamento lo toglie con tutti e due i `drop_copy`, uno rifiutato lo tiene; scambio, commit e ritorni indietro lo
>   tengono); `test_backup_restore_apply.py` da 84 a 136, 54 rossi (B-17 al posto del vecchio (d); il biglietto del
>   riavvio; la rotta dell'esito senza sessione e solo nell'header; 17 biglietti che non valgono con lo stesso 404 fino ai
>   byte; le fasi, i motivi d'attesa, il consumo; mai nei log; istanza bloccata, rossa finché manca la riga di H, e un
>   controllo statico che l'esito sia l'unica rotta del ripristino nella lista; l'OpenAPI). Uno verde apposta: da
>   bloccata, ogni altra rotta del ripristino risponde 423 a un admin. **Scelte fissate dal test-author, accolte**: un
>   biglietto sbagliato non spende né toglie il file (nella bozza il confronto dell'hash passa prima della scadenza);
>   le conferme e gli annullamenti rifiutati tengono il biglietto; l'header è esattamente `X-Restore-Ticket`
>   (`alias`), facoltativo; i docstring dei due schemi nuovi in una riga, senza backtick; un `drop_ticket` fallito
>   logga almeno un warning; niente rimozioni attraverso un link al posto di `.restore`. **Il caso non specificato**:
>   se il biglietto non si scrive (disco pieno), il riavvio non parte, 500 `restore_restart_failed`, nel log; la scheda
>   lo dice col messaggio generico «the server's log has the cause» (nessuna chiave nuova). Bozza aggiornata (anche i
>   docstring della disposizione di `.restore` in `paths.py` e `apply.py` e la descrizione di `api
>   backup-restore-apply` nel catalogo) e riprovata a secco.
> - **Giro rosso del backend** (15:57-16:07): `services backup-outcome` 95 rossi su 95, `services backup-apply` 13 su
>   223, `api backup-restore-apply` 54 su 136; tutti per il motivo giusto (modulo, nomi o comportamento che mancano).
> - **Codice del backend** (16:08): `apply_b5c_backend.py` (`outcome.py` nuovo; `paths.py`; `apply.py` con
>   `drop_ticket` dopo i controlli della conferma e dell'annullamento; gli schemi; le rotte; B-17; i docstring della
>   disposizione di `.restore`; la descrizione del catalogo); `ruff --fix` (un ordine di import), black invariato.
> - **Verde del backend** (16:14-16:42, col carico): `services backup-outcome` 95, `services backup-apply` 223,
>   `utils backup-cli-restore` 77, `utils backup-cli` 102, `e2e backup-roundtrip` 3; `api backup-restore-apply` 133 su
>   136 (i due rossi attesi della riga di H, l'esito da bloccata e il controllo statico della lista, più un errore del
>   test); `api backup` 22 su 23 (il pin dell'ordine delle rotte, BACKUP-001, non conosceva la rotta nuova).
>   - **⚠️ Fuori pista**: `test_the_ticket_is_never_logged` falliva sulla sua stessa richiesta: dentro la cattura
>     mandava il biglietto in `?ticket=` (il caso «la query è ignorata») e il client httpx del test logga l'URL. Non è
>     il prodotto (che non mette mai il biglietto in un URL): riparato dal test-author (dentro la cattura solo l'header;
>     il caso della query resta nei suoi due test), e il pin di BACKUP-001 con nove rotte del ripristino. Nota sua per la
>     revisione di sicurezza: la maschera del log d'accesso di uvicorn (`mask_query_credentials`) copre solo i nomi con
>     parole da credenziale (token, secret, password); `ticket` no, quindi un biglietto scritto a mano in un URL finirebbe
>     nel log d'accesso.
> - **Codice del frontend** (16:46, col client rigenerato: `RestoreRestartAccepted`, `RestoreOutcome` non stretto):
>   `apply_b5c_frontend.py` (`backupApi.ts`: il tipo, `requestRestart`, `RESTORE_TICKET_HEADER`, `restoreOutcome(ticket)`
>   col ripiego `readStatusWithSession()` su 404, 401 e 423; `restoreFlow.svelte.ts`: `#ticket` in memoria, azzerato da
>   `load()`, `dispose()` e a ogni riavvio, preso da `outcome_ticket ?? null`, passato a ogni lettura dell'esito; B-17:
>   `cancelPending()` senza `dropCheck`). Prettier invariato.
> - **Doc** (`docs-writer`, solo scrittura): `security.md` (le rotte, la sottosezione nuova «🎫 The Outcome Ticket»
>   `#backup-restore-outcome`, la lista del blocco), la guida (via la limitazione di `JWT_SECRET`: il biglietto dice
>   l'esito qualunque sia la configurazione; il ripiego onesto per una pagina ricaricata, più di un'ora d'attesa o un
>   riavvio non chiesto dalla pagina; B-17), `hosting_providers.en.md` (una riga in «What Still Answers»). Quattro punti
>   presuppongono la voce di H con l'alias `backup_restore`.
> - **Verde completo** (16:44-16:59): Vitest `backupApi` + `restoreFlow` + `RestoreCard` 404 su 407 (i tre rossi
>   dell'ambiente dei test: `localStorage` non c'è come globale sotto Node 26 con jsdom; riparati dal test-author con lo
>   stub in memoria dello schema della base, `vi.stubGlobal`), gli altri cinque file 332, `front check` 0/0,
>   `api backup-restore-apply` 134 su 136 (i due di H), `api backup` 23.
> - **`security-review`** (`a8a19165`, 17:00-17:10): **nessuna vulnerabilità, a nessuna gravità.** Robustezza:
>   (1) due riavvii insieme si pestano il file temporaneo del biglietto, e un annullamento può infilarsi fra la lettura
>   dello stato e il biglietto → **corretto**: il biglietto si emette sotto il lock del ripristino
>   (`apply.prepare_restart`, che la rotta usa); (2) con B-17 la copia si toglieva fuori dal lock, e una conferma della
>   stessa copia da un'altra pagina l'avrebbe persa → **corretto**: dentro il lock. Ruff e black puliti. (3) **Disegno**:
>   il «monouso» toglieva il biglietto prima che la risposta finale arrivasse; persa quella, il ripiego sulla sessione
>   avrebbe detto «ripristinato» dopo un ritorno indietro senza `JWT_SECRET`. Chiesto al coordinatore.
> - **17:20, decisione N53 del coordinatore** (da rivedere col developer): un esito finale si rilegge finché il
>   biglietto non scade (un'ora); «monouso» vuol dire **un ripristino, un biglietto**, non più una lettura. Più `ticket`
>   in `_CREDENTIAL_WORD` di `logging_config.py` (sono lo scrittore del file per questo lotto), con un caso nel test della
>   maschera. Rossi al test-author `628939b5`; doc al `docs-writer`.
> - **Doc di N53** (`docs-writer`): `security.md` (la riga della rotta: «as often as asked until the ticket expires»;
>   «🎫 The Outcome Ticket»: il biglietto emesso sotto il lock, la query ignorata e mascherata nel log d'accesso, «One
>   restore, one hour» col perché, «unknown» per mai emesso, sostituito o tolto; «📜 Request Logs» con `ticket`). La
>   guida e la pagina dei fornitori non parlavano di una lettura sola: invariate.
> - **17:22, sospensione del coordinatore** fino alle ~17:45 (la galleria intera dei colori, carico 130-170): niente
>   prove nuove. Fermata la mia riesecuzione di Vitest, che aspettava ancora il carico (non era partita). Pronto
>   `files/b5c-wip/apply_n53.py` (in `outcome.py` via `_FINAL` e la rimozione alla lettura finale; i docstring di
>   `outcome.py`, della rotta e dello schema; `ticket` in `_CREDENTIAL_WORD` e nel docstring della maschera), provato a
>   secco su copie.
> - **Rossi di N53 e della maschera** (test-author `628939b5`, ruff, black e `--collect-only` puliti): `test_backup_outcome.py`
>   97 (l'esito finale si rilegge uguale fino a un microsecondo prima di `expires_at`, a `expires_at` niente e il file
>   tolto; il biglietto seguito da `pending` al commit letto due volte; un biglietto scaduto se ne va solo col suo
>   portatore: rossi 4); `test_backup_restore_apply.py` 136 (l'esito finale tre volte uguale fino ai byte, rosso ×2; la
>   riga `spent` del 404 identico diventa `dropped-by-a-cancel`; il log senza biglietto, anche con una lettura scaduta);
>   `test_backup_apply.py` 228 (scambio, commit e ritorni indietro tengono il biglietto fino alla scadenza, rossi ×3; **in
>   più, non chiesti e accolti**: `prepare_restart` emette il biglietto mentre il lock è tenuto, e senza un ripristino in
>   attesa rifiuta senza scrivere niente, verdi ×5); `test_logging_access_filter.py` 110 (`ticket`, `outcome_ticket`,
>   `TICKET`, `Restore-Ticket`, `tick%65t` dopo `?` e dopo `&`, rossi ×10; `q=ticket` e `ticker=AAPL` restano, guardia
>   contro un'espressione troppo larga, verdi ×4). Il test-author ha toccato anche la descrizione del catalogo di
>   `logging-access-filter` (voce di H, `/ticket`): da dire al coordinatore. Segnalati e aggiunti allo script i testi
>   rimasti «used up»: la descrizione OpenAPI del 404 (`_OUTCOME_NOT_FOUND`) e la descrizione di `api
>   backup-restore-apply` nel catalogo.
> - **17:52, sospensione tolta** (prove leggere a carico sotto 50, una alla volta). **Giro rosso** (17:53-18:00):
>   `services backup-outcome` 4 rossi, `services backup-apply` 3, `services logging-access-filter` 10, come previsti;
>   `api backup-restore-apply` 9: i 2 di N53 e i 2 di H previsti, più 5 non previsti.
>   - **⚠️ Fuori pista**: i 5 erano una regressione mia: `prepare_restart` prendeva il lock (creando `apply.lock`) prima di
>     vedere che il ripristino non era in attesa, e `test_a_restart_refused_writes_no_ticket` (applying, applied,
>     rolling_back, committed, rolled_back) fissa «un riavvio rifiutato non scrive niente». Corretto: prima la lettura
>     senza lock (`read_restore`, come faceva la rotta), poi il lock e la rilettura solo se è in attesa.
> - **18:02, applicati** `apply_n53.py` (in `outcome.py` niente rimozione alla lettura finale e via `_FINAL`; i
>   docstring; `_OUTCOME_NOT_FOUND` senza «used up»; la descrizione del catalogo; `ticket` in `_CREDENTIAL_WORD` e nel
>   docstring della maschera) e la correzione di `prepare_restart`; ruff e black puliti.
> - **Verde** (18:00-18:13): `services backup-outcome` 97, `services backup-apply` 228, `services logging-access-filter`
>   110, `api backup` 23, `utils backup-cli-restore` 77; `api backup-restore-apply` 134 su 136, i due rossi sono quelli
>   della riga di H (l'esito da bloccata, il controllo statico della lista). Porta libera.
> - **18:12, slot 2 offerto per un E2E**: non pronto (le prove della scheda del ripristino non erano scritte, la corsia
>   finiva il giro leggero): lasciato ad A. Il coordinatore dà uno slot di 30 minuti dopo le 19:30 per
>   `front-utility backup` con i casi nuovi. Test-author `332db941` sull'E2E (solo scrittura): estende
>   `e2e/settings/backup.spec.ts` col ripristino; il riavvio, la sonda `/system/ready` e la rotta dell'esito sempre
>   intercettati con `page.route` (un riavvio vero fermerebbe il server della corsia); un solo caso con la conferma
>   vera, e ogni ripristino in attesa annullato nella pulizia; casi in serie (una prova e un ripristino alla volta).
> - **Ultimi controlli** (18:14-18:20): Vitest `backupApi` + `restoreFlow` + `RestoreCard` 407 su 407 (con lo stub di
>   `localStorage`); `front check` 0/0; `mkdocs build` stretta 0 avvisi; `check-links` 96; `utils gate-docs-links` 63;
>   `git diff --check` pulito; porta libera.
> - **18:22, handoff del checkpoint B5c** al coordinatore, 🧊 FROZEN per questi file: 20 tracciati modificati e 2 nuovi
>   (`outcome.py`, `test_backup_outcome.py`). Fuori: `frontend/e2e/settings/backup.spec.ts`, che il test-author dell'E2E
>   sta scrivendo (entra con il suo slot). Restano rossi due casi di `api backup-restore-apply`, finché entra la riga di H
>   in `ALLOWED_WHEN_BLOCKED` (`instance_block.py`) e il suo pin (`test_instance_block.py`).
> - **B5c committato** dal coordinatore: `9137e1ef8` feat, `b699be101` docs, `57564d321` journal (HEAD). La descrizione
>   di `logging-access-filter` con `/ticket` resta.
> - **18:29, le righe di H, scritte da me e riviste da H** (coordinatore): `instance_block.py` (l'import di
>   `restore as backup_restore`; la voce `backup_restore.get_restore_outcome` dopo quelle del pannello, con un commento;
>   una frase nel docstring del modulo) e `test_instance_block.py` (la voce in `ALLOWED_ROUTES`). Nessun ciclo d'import:
>   il pacchetto `backup` carica già `restore`. Ruff e black puliti. **Verde** (18:30-18:32): `api instance-block`
>   62 su 62, `api backup-restore-apply` **136 su 136**. Entrano con lo slot dell'E2E dopo le 19:30. **H le ha riviste
>   (18:33): OK, nessun cambio**; accoglie anche N53.
> - **18:50, l'E2E del ripristino è scritto** (test-author `332db941`, solo Prettier): sette casi FBKP-101…107 in
>   `e2e/settings/backup.spec.ts`, in serie dopo i quattro di B5a: 101 troppo grande (lo stato con un limite di 1 MB, il
>   `PUT` registrato e interrotto), 102 incolla rifiutato (un `ControlOrMeta+V` vero, con i permessi degli appunti), 103
>   ritorno indietro, 104 bloccata (`instance_blocked`), 105 il ripiego (404 dell'esito, 401 dello stato → il login),
>   106 un ripristino trovato in attesa (caricamento, prova e conferma veri dall'API; annullamento dalla scheda), 107 il
>   percorso vero (il selettore del file, la prova, il report, la parola, la conferma vera; il riavvio, la sonda e
>   l'esito `committed` finti). Il riavvio è sempre intercettato prima della prima navigazione e non passa mai; il
>   biglietto controllato nell'header e in nessun'altra richiesta; una pulizia dopo ogni caso, riuscito o no, con una
>   sessione admin a parte: annulla quel che attende, toglie le prove, verifica che lo stato non sia in attesa. Chiesto
>   lo slot al coordinatore (`front-utility backup`, con la build del frontend in testa).
> - **Slot 1** (18:49-18:53, il coordinatore: «con le righe di H»): `front-utility backup` **12 su 12** in 3 minuti
>   (FBKP-001, 001b, 002, 003, 004 di B5a; FBKP-101…107 del ripristino, FBKP-102 con l'incolla vero compreso), la build
>   del frontend fatta prima (`--build-only`). La cartella dati della corsia pulita dopo: in `.restore/` nessuno stato,
>   nessun biglietto, nessuna copia, nessun caricamento, solo i file di lock vuoti. Porta libera.
> - **Committato** dal coordinatore: `465c27939` feat (le righe di H), `78023380c` test (l'E2E del ripristino),
>   `283466abb` journal.

### Aggiornamento di base — merge di `dev_release2` `0c79932a7` (2026-10-16, 19:57-20:30) ✅ — 🧊 FROZEN; committato dal coordinatore: `92a190efa`

> - Merge aperto dal coordinatore nel mio worktree (HEAD `283466abb`, MERGE_HEAD `0c79932a7`, base comune `62004e530`;
>   oltre 446 commit: C-97a, H-12/21, MF, Y, X, i colori; non ancora P18 di A). Sei conflitti, risolti per somma; in
>   staging solo quei sei (`git add` dei sei percorsi); nessun file fuori conflitto toccato.
>   - `backend/app/services/platform/app_lifespan.py`: da me `restore-commit`, da H `plugin-secrets-check` (H-15),
>     tutti e due subito dopo `global-settings`. Ordine scelto: `global-settings`, **`restore-commit`**,
>     `plugin-secrets-check`, `provider-prewarm`. Perché: il passo di H non solleva mai (prende ogni eccezione e logga
>     il nome della classe), quindi non cambia cosa fa tornare indietro un ripristino; i due pin sono d'ordine relativo
>     (il mio `global-settings < restore-commit < provider-prewarm`, quello di H `global-settings <
>     plugin-secrets-check < scheduler`) e reggono tutti e due; l'e2e `backup-roundtrip` esegue i passi da
>     `pending-restore` a `restore-commit` compresi, e così la sua fetta resta quella provata; e il controllo di H legge
>     i dati già confermati. Un commento sul passo del commit. Da dire a H.
>   - `scripts/test_runner/_backend_services.py`: la descrizione di `logging-access-filter` scritta dai due lati (da me
>     `ticket` e «a ticker kept», da H H-9: `configure_logging` chiude i gestori che toglie): unite. Nessuna unità doppia
>     (controllo per file: le due `all` di `_backend_api.py` sono di due categorie, `api` ed `e2e`).
>   - `admin/filesystem.en.md` (di H): da me il rimando alla guida, da H (il mio B-5) `./dev.py backup create`, i link a
>     `cli_tools.md#backup` e `#backup-docker` e «It leaves out `secrets/`», vero anche per la mia guida: un paragrafo
>     solo, prima la guida, poi il comando, poi la copia a mano.
>   - `admin/index.en.md`: la riga di CLI Admin Tools di H («instance backups») e la mia voce della guida.
>   - `admin/hosting_providers.en.md` (di H), tre: nell'elenco di ciò che serve a un'istanza ospitata i due punti di H
>     (protezione dei frame, pagina di supporto) e il mio (la politica di riavvio); fra i punti del blocco la frase
>     nuova del recupero (Z/Y: colma il buco fino a un anno) e il mio punto del ripristino che aspetta lo sblocco; nella
>     tabella di «What Still Answers» la riga del backup di H (la scheda della pagina di blocco) e la mia dell'esito.
>   - `developer/architecture/database/users_access.md`: la mia frase su `session_version` dopo un ripristino e il
>     punto di `email_verified_at` riscritto da E.
> - **Rivisti anche i nove file cambiati dai due lati e uniti da git**: `logging_config.py` (il mio `ticket` e H-9 tutti e
>   due presenti), `test_logging_access_filter.py` (24 test, nessun nome doppio), `mkdocs.yml` (la pagina Plugins e la
>   mia voce, separate), i tre file del runner (le mie voci di backup intatte, le otto righe Vitest di `features/backup`
>   e l'azione `front-utility backup`), `cli_tools.en.md`, `security.md` (nessuna ancora doppia), il backlog. Nessun
>   manifest di dipendenze cambiato.
> - **Debito che il merge rende vero**: H-12/21 ha messo la scheda del backup nella pagina di blocco, quindi in
>   `backup_restore.en.md` (riga 60) «that page has no backup button yet» non è più vero (B-14). Lo correggo dopo il
>   commit del merge, nel prossimo checkpoint, con le altre frasi della guida sull'istanza bloccata. Le due frasi «no
>   button for it yet» rimaste (`hosting_providers.en.md`, `security.md`) parlano della cancellazione del proprio
>   account, e restano vere.
> - **Prove leggere sulla revisione combinata** (`files/scripts/b_green.sh`, poi `b_docs.sh`, carico sotto 50): i 16
>   selettori dei globi del coordinatore più `e2e backup-roundtrip` (prova direttamente l'ordine dei passi risolto), poi
>   la doc. **Tutto verde** (20:04-20:24): `services app-lifecycle` 44, `backup-archive` 155 (più 1 saltato apposta: il
>   file system di macOS rifiuta un nome non UTF-8), `backup-jobs` 69, `backup-staging` 145, `backup-apply` 228,
>   `backup-outcome` 97, `backup-totals` 84; `api instance-block` 62 (svelte-check 0/0 sul client rigenerato),
>   `backup` 23, `backup-instance-errors` 6, `backup-panel` 59, `backup-restore` 121, `backup-restore-apply` 136,
>   `backup-export-extras` 8; `utils backup-cli` 102, `backup-cli-restore` 77; `e2e backup-roundtrip` 3; `mkdocs build`
>   stretta 0 avvisi, `check-links` 97, `utils gate-docs-links` 63. Porta libera. Diff in staging pulito (`--check`).
> - **⚠️ Fuori pista** (20:24): un `sed -i ''` per segnare chiusa questa sezione ha svuotato il piano (0 byte, uscita 1;
>   probabilmente il `sed` di macOS su un carattere multibyte del modello, che lascia il file vuoto). Toccava solo questo
>   piano, fuori staging; l'indice ne aveva la versione committata (`283466abb`, identica a HEAD). Ripreso senza
>   scritture di git: `git show :<piano>` copiato nella cartella della sessione e sul file (3477 righe, uguale
>   all'indice), poi questa sezione riscritta con lo strumento di modifica. Da ora niente `sed -i` su testo con caratteri
>   non ASCII: lo strumento di modifica o Python.
> - **20:30, handoff del merge** al coordinatore, 🧊 FROZEN: lui crea il commit del merge; fuori staging solo questo
>   piano; poi lo slot di `all-backend` prima dell'ingresso.
> - **Committato** dal coordinatore: `92a190efa` (il merge), `618fe8be4` (questo piano). L'ordine dei passi lo passa lui
>   a H; B-14 nel prossimo checkpoint, d'accordo.

### Secondo aggiornamento di base — merge di `dev_release2` `979d0a151` (2026-10-16, 20:26-20:39) ✅ — committato dal coordinatore: `4e866cead`

> - Nel frattempo in `dev_release2` sono entrati A (P18/A-27, la migrazione 009 e F02) e W-B53 (il passo
>   `brim-parse-pool`). Merge aperto dal coordinatore (HEAD `618fe8be4`, MERGE_HEAD `979d0a151`, base `0c79932a7`).
>   Tre conflitti, risolti per somma, in staging solo quei tre.
>   - `app_lifespan.py`: il conflitto non era il passo di W (git l'ha messo da solo dopo `market-holidays` e prima di
>     `scheduler`, come chiedeva il coordinatore), ma **`admin-bootstrap` di A (F02)**, anche lui subito dopo
>     `global-settings`. Ordine scelto: `global-settings`, **`admin-bootstrap`, `restore-commit`**,
>     `plugin-secrets-check`, `provider-prewarm`, `market-holidays`, `brim-parse-pool`, `scheduler`, `idle-monitor`.
>     Perché: il test di A (STEP-001, `test_admin_bootstrap.py:1794`) fissa `admin-bootstrap` esattamente alla posizione
>     di `global-settings` più uno, mentre il mio pin e quello di H sono d'ordine relativo: così reggono tutti e tre.
>     Nel merito: su un database ripristinato il bootstrap trova gli account e li lascia stare (`IGNORED`: ogni archivio
>     ripristinabile ha un amministratore attivo, il blocco `no_administrator`); se fallisse sui dati ripristinati, il
>     ripristino tornerebbe indietro come per ogni passo prima del commit. **Caso limite, per A**: un archivio con
>     l'amministratore iniziale ancora in attesa **e** un altro amministratore attivo (creato dalla CLI), ripristinato
>     su un'istanza con `LIBREFOLIO_ADMIN_EMAIL` e un token mai visto: il bootstrap riarma il link prima del commit, e
>     `_close_the_way_in` lo revoca con tutti gli altri link vivi; l'amministratore dovrebbe chiederne un altro con
>     `./dev.py user setup-link`. Con `restore-commit` prima di `admin-bootstrap` il link sopravvivrebbe, ma servirebbe
>     che A rilassi STEP-001 a ordine relativo: da decidere con A, non è un difetto della 1.3 per i flussi reali.
>   - `developer/architecture/database/users_access.md`: la frase di A (il link di setup speso chiude le sessioni) e la
>     mia (la versione di sessione dopo un ripristino), tutte e due nel punto di `session_version`.
>   - `developer/architecture/security.md`: il paragrafo dei test della revoca, quello allargato di A (contratto 7,
>     REVOKE-003…007) più la mia frase sulla versione del ripristino (`services backup-apply`).
> - **⚠️ Fuori pista**: un controllo dei marcatori partito nello stesso lotto parallelo della modifica ha letto il file
>   prima della scrittura (3 marcatori): riletto dopo, nessuno. D'ora in poi la verifica di un file mai nello stesso
>   lotto della sua modifica.
> - **Debito trovato (per il prossimo checkpoint, con B-14)**: `developer/architecture/overview.md` numera 18 passi
>   d'avvio (di H, con `plugin-secrets-check`), ma il codice ne ha 21: mancano i miei `pending-restore`,
>   `serving-lock` e `restore-commit`. Nessun test confronta quella lista con il codice.
> - **Prove leggere sulla revisione combinata**: `services app-lifecycle`, `backup-apply`, `config-brim` (del
>   coordinatore), più `services admin-bootstrap` (fissa l'adiacenza scelta) ed `e2e backup-roundtrip` (la sua fetta di
>   passi, da `pending-restore` a `restore-commit`, ora comprende il bootstrap); poi `mkdocs build` stretta,
>   `check-links`, `utils gate-docs-links`. **Tutto verde** (20:28-20:36): `services app-lifecycle` 51,
>   `backup-apply` 228, `config-brim` 51, `admin-bootstrap` 156; `e2e backup-roundtrip` 3 (col bootstrap nella fetta);
>   `mkdocs build` stretta 0 avvisi, `check-links` 97, `utils gate-docs-links` 63. Porta libera.
> - **20:30, decisione N57** del coordinatore (proposta di H, da rivedere col developer): proprio quest'ordine,
>   `global-settings` → `admin-bootstrap` → `restore-commit` → `plugin-secrets-check` → … Perché: il passo di A legge e
>   scrive i dati ripristinati (conta gli utenti, crea l'amministratore in attesa, imposta `registration_mode`) e può
>   sollevare su un errore dei dati; prima del commit un fallimento fa tornare indietro il ripristino, dopo il server
>   cadrebbe a ogni avvio. Richieste: il pin `("admin-bootstrap", "restore-commit")` nel mio test, col perché (a un
>   test-author nuovo, `2334eaf9`: il precedente non c'era più); un commento sul mio passo (fatto: «A step before this
>   one that raises rolls the restore back at the next start; one after it no longer does (N57)», ruff e black puliti).
> - **Frase diventata falsa col merge, corretta nella risoluzione**: in `security.md` il passo `plugin-secrets-check`
>   era «right after `global-settings`»; ora «after `global-settings`, `admin-bootstrap` and `restore-commit`». Era nel
>   file in conflitto; la build stretta l'ha già coperta.
> - **Da H, per la guida (prossimo checkpoint, con B-14 e `overview.md`)**: un ripristino senza la chiave lascia
>   illeggibili i segreti di sistema dei plugin, e da ogni avvio il passo `plugin-secrets-check` logga l'errore
>   «Stored plugin secrets that the instance key cannot read: <N>. Enter them again in the plugin settings, or restore
>   the instance key they were saved with», finché non sono reinseriti o la chiave vecchia non torna. La guida dice già
>   «reported as set but unreadable: enter it again» (riga 33): ci aggiungo il log.
> - **Il pin di N57** (test-author `2334eaf9`, ruff, black e `--collect-only` puliti): in `test_backup_apply.py`
>   `assert_in_relative_order(STARTUP_STEPS, ("admin-bootstrap", "restore-commit"), why=…)`, relativo (STEP-001 di A
>   intatto); l'aiuto, locale al file, prende un `why` facoltativo che chiude i due messaggi; docstring del test, riga di
>   `print_success` e docblock (j) aggiornati. **`services backup-apply` 228 su 228** (20:37), il pin stampato.
>   Il test-author segnala lo stesso caso limite del link di setup revocato dal commit; il suo primo caso (un database
>   ripristinato senza account) non può darsi: la prova rifiuta un archivio senza amministratore attivo
>   (`no_administrator`).
> - **20:39, handoff del merge** al coordinatore, 🧊 FROZEN: in staging i tre conflitti più, per N57, il pin
>   (`test_backup_apply.py`) e la frase corretta di `security.md` (file già in conflitto); fuori staging solo questo
>   piano.
> - **Committato** dal coordinatore: `4e866cead` (il merge), `cd06f240b` (questo piano); poi un merge pulito di `dev`
>   `27994759a` (J-24, MF C/I2, A-25, il giornale di Z): HEAD **`dbc2324d5`**, pulito. Il caso limite del link di setup va
>   nel backlog di A, tramite il coordinatore.

### `all-backend` su `dbc2324d5`, il CHANGELOG, H-17 e il checkpoint di doc (2026-10-16, 20:49-22:32) ✅ — 🧊 FROZEN

> - **Slot 1** (il coordinatore, 20:49; fine prevista 21:40, poi «lascialo finire»: nessuno aspettava lo slot prima delle
>   22): `all-backend --workers 2` su **`dbc2324d5`** con l'albero pulito, nella mia corsia (6187,
>   `/tmp/librefolio-r13-b`), `files/scripts/b_allbackend.sh`. Dalle 20:50 alle 21:35, **45 minuti 09 secondi: 7 su 7**
>   (External, DB, Services, Utils, Schema, API, E2E), uscita 0. Le tre passate parallele: 6386 + 6628, 94 + 3089,
>   365 + 1468 superati, nessun fallimento; la costruzione dei prerequisiti 280 s col carico a ~80. Le 7 righe «❌» del log
>   sono messaggi stampati dai test External sui percorsi d'errore (`MOCKFX_FAIL: simulated provider failure…`), non
>   fallimenti. Istantanea del DB `00_archive/test-db_20261016_213506.tar.xz`. Porta libera.
>   - Durante la corsa nessuna modifica all'albero (la corsa doveva provare esattamente `dbc2324d5`): le note di questo
>     piano tenute in `files/next-checkpoint/journal-notes.md` della sessione e riportate qui dopo.
> - **Checkpoint di doc** (21:36, `files/next-checkpoint/apply_b14_docs.py`, provato a secco prima su copie):
>   - **B-14** in `admin/backup_restore.en.md`: «Make a Backup», la pagina di blocco ora ha la stessa scheda, **Keep a
>     copy of the data** (rimando a «What Users See» di `hosting_providers`); «Bring Your LibreFolio Home», un
>     amministratore scarica l'archivio da quella scheda, altrimenti il fornitore. B-14 ✅ nel backlog.
>   - **La nota di H** nello stesso file («Saved secrets stay behind»): per le impostazioni dell'istanza ogni avvio logga
>     l'errore «Stored plugin secrets that the instance key cannot read: …» col loro numero, finché non sono reinseriti
>     o la chiave vecchia non torna.
>   - **`developer/architecture/overview.md`**: i tre passi del ripristino nella lista numerata (`pending-restore` dopo
>     `tool-catalog`, `serving-lock` dopo `data-directories`, `restore-commit` dopo `admin-bootstrap`, con la regola di
>     N57), rinumerata: 21 passi, gli stessi del codice e nello stesso ordine (confrontati con `STARTUP_STEPS`).
>   - Pagine solo in inglese: nessun debito di traduzione.
> - Controlli della doc: fermati prima di partire (carico ~100) per farli una volta sola, dopo anche H-17 (sotto).
> - **B è entrato in `dev`** (coordinatore, 21:45): merge **`0cd910a7e`** (treno 141: B3, P7, B5b, B5c, B-17, N53, N57;
>   64 file), nessun conflitto. **CHANGELOG**: mandato il blocco finale in inglese (`files/next-checkpoint/
>   changelog-block.md` della sessione): in `✨ Added` sostituisce il punto di B2 («Check a backup before restoring it»)
>   con «Restore an instance backup» (la prova su copia, la conferma con la parola, il riavvio, l'esito, `--dry-run` e il
>   limite di caricamento conservati), più `backup pending`, le regole (mai indietro, un amministratore attivo, la chiave
>   che resta), i totali del registro, l'API del biglietto e B-17, la guida nuova; in `🔒 Security` tre punti (le
>   sessioni e i link che un ripristino chiude, mai applicato da bloccata, il biglietto fuori da log e URL). Coerente con
>   N53 (rileggibile fino alla scadenza) e N57 (un avvio che non finisce rimette i dati). Applicato dal coordinatore così
>   com'era (6 ✨ + 3 🔒).
> - **H-17** (approvato, in questo checkpoint): `backup_max_upload_mb()` legge il valore del profilo dalla tabella di H
>   con `profile_default(MAX_UPLOAD_VARIABLE, 0)`; via la mia costante `MANAGED_MAX_UPLOAD_MB` (una sola fonte, che il
>   test di H fissa a 500); docstring del modulo e della funzione aggiornati; nessun ciclo d'import (provato), ruff e
>   black puliti. In `developer/architecture/settings.md` la frase sulla prima voce della tabella dice ora chi la legge.
>   Il test che fissava la costante lo ripara un test-author (`7cce1bbb`, solo scrittura): il nome della variabile, la
>   voce della tabella di H a 500 e nessun valore proprio in `config/backup.py`.
> - **Prove** dopo il test-author (carico sotto 50): **tutto verde** (21:53-22:31): `api backup-restore` 121 (il test
>   riscritto: il nome della variabile, la voce della tabella di H a 500, nessuna costante propria in `config/backup.py`;
>   il test parametrico invariato), `services profile-defaults` 52 (la guardia di H), `api backup-restore-apply` 136;
>   `mkdocs build` stretta 0 avvisi (168 s sotto carico), `check-links` 97, `utils gate-docs-links` 63; `git diff
>   --check` pulito; porta libera. Nota del test-author, non fatta (fuori dal perimetro approvato): il controllo
>   `hasattr` coglie solo il vecchio nome; mettere nella tabella un valore di prova e verificare che la funzione lo segua
>   chiuderebbe anche un 500 scritto a mano.
> - **22:32, handoff del checkpoint** al coordinatore, 🧊 FROZEN: 7 file tracciati, nessuno nuovo.
> - **Committato** dal coordinatore: `fix(backup)` H-17, `docs(backup)`, `docs(journal)`; HEAD `e3a96d9da`. La nota del
>   test-author (un valore di prova nella tabella di H, la funzione che lo segue): **sì**, nel prossimo lotto.

### Terzo aggiornamento di base — merge di `dev_release2` `cd617824e` (2026-10-16, 22:32-23:04) ✅ — committato dal coordinatore: `6c72f0efe`

> - Merge aperto dal coordinatore (HEAD `e3a96d9da`, MERGE_HEAD `cd617824e`): la decisione 47 di W aggiunge il passo
>   `lone-transfer-legs` (dopo `post-migration-fixes`, prima di `global-settings`) e la sua voce nella lista numerata di
>   `developer/architecture/overview.md`, dove io avevo appena messo i miei tre passi: un conflitto, solo quello.
> - **Risolto con uno script** (non a mano): la lista dei passi nell'ordine di `STARTUP_STEPS` del codice unito (22
>   passi, contati da `app_lifespan.py`), il testo di ogni passo dal lato che lo ha (i miei tre da HEAD, quello di W dal
>   suo lato; nessun passo comune con testi diversi), numerata da capo: **lista = codice, 22 su 22**. Nessun marcatore,
>   `git diff --check` pulito; in staging solo `overview.md`, fuori staging solo questo piano.
> - Riordinata qui sopra la nota delle 21:40 (i controlli fermati col carico a ~100), finita per sbaglio dopo l'handoff
>   delle 22:32.
> - Prova (22:55-23:03, dopo l'attesa del carico): `mkdocs build` stretta **exit 0** (238 s, ogni URL relativo del sito
>   risolto), `mkdocs check-links` valido, `utils gate-docs-links` **63 passati**; porta 6187 libera. `git diff --cached
>   --check` pulito, nessun file non risolto.
> - **23:04, handoff del merge** al coordinatore: in staging, oltre al merge, solo `overview.md`. Fuori staging resta
>   questo piano; i file dei test di B4 che i test-author stanno scrivendo non vanno nel commit del merge.
> - **Committato** dal coordinatore: `6c72f0efe` (solo l'indice; genitori `e3a96d9da` e `cd617824e`). H-17 e la doc sono
>   entrati in dev. Via a B4: rossi, poi codice.
> - **Prossimo lotto: B4** (password e chiave dell'archivio; P12 deciso: scrypt `n = 2^15`, la password con le regole e
>   l'indicatore della registrazione, almeno 12 caratteri), prima l'analisi; più il test della nota di H-17. B7 e B9
>   aspettano Docker; BZ alla fine. Di notte: una domanda che solo il developer può sciogliere va nel piano e al
>   coordinatore, e si va avanti.

### B4 — analisi sulla base nuova (2026-10-16, 22:36-22:47) — inviata al coordinatore ✅ — via alle 22:55 — codice, verdi e revisioni ✅ (17/10, 02:10) — 🧊 FROZEN, checkpoint pronto

> **Via del coordinatore (22:55)**, sui tre punti:
>
> 1. sui file degli altri scrivo io e il proprietario rivede, in sola lettura, prima del mio checkpoint:
>    - A: `password_policy.py` (le tre funzioni con `rules=`) e `PasswordStrength.svelte` (la prop `rules`);
>    - X: `_NoInputEchoRoute` in un modulo comune;
>    - H: la riga della docstring di `derive_key_from` e la revisione delle righe che leggono la chiave.
>
>    Il coordinatore avvisa tutti e tre. Non toccare `zodios-client.ts` né `settings/users/**` (A7b aperto).
> 2. B4a + B4b in un lotto solo.
> 3. Lo slot E2E per FBKP-108/109 si chiede quando è pronto.
>
> Più:
>
> - la domanda per il developer resta per il mattino: si procede con «in chiaro»;
> - B-18 (`restore --instance-key-file`) va nel backlog;
> - l'eco del 422 su registrazione, cambio e reset della password diventa una voce di sicurezza di A (A-30), da
>   correggere col modulo comune una volta entrato.
>
> **Avvio (22:55-23:05)**:
>
> - contratto congelato per i test: `files/b4-test-brief.md` della sessione. Una correzione rispetto all'analisi: in
>   `password_policy.py` `rules=None` vuol dire le regole lette al momento della chiamata, mai un default fissato
>   all'import;
> - sei test-author in parallelo, ognuno sui suoi file e senza eseguire niente; i rossi li lancio io, uno alla volta:
>   - la busta: `services backup-envelope`;
>   - le regole, il 422 e `secure.py`: la sezione B4 di `test_password_policy.py`, `services backup-secure-rules`,
>     `api no-echo-route`, più la guardia di H-17 in `test_backup_restore.py`;
>   - i servizi: `services backup-secure`;
>   - l'API: `api backup-secure`;
>   - la CLI: `utils backup-cli-secure`;
>   - il frontend: Vitest della cartella backup e di `PasswordStrength`.
>
>   Il codice lo preparo intanto fuori dal worktree (`files/b4-wip/`), e entra solo dopo i rossi e dopo il commit del
>   merge 3.
>
> **⚠️ Fuori pista (23:25), una regola del contratto rivista scrivendo il codice**: il contratto rifiutava
> (`unexpected_entry`) uno zip in chiaro con dentro la chiave d'istanza. Ma lo zip che `dev.py backup decrypt` estrae da
> una busta è proprio questo: `inspect` e `restore` avrebbero rifiutato un file scritto da LibreFolio stessa, sulla strada
> manuale «Porta a casa». Rifiutarlo in lettura non protegge niente, perché un archivio costruito ad arte porta comunque i
> segreti che vuole; la regola che conta è in scrittura: la chiave la scrive solo un backup con la password. Nuova
> regola: la chiave annunciata dal manifest si accetta in ogni archivio, ma non si estrae mai nella copia. Brief
> aggiornato; il test-author dei servizi corregge il suo caso 8.
>
> **⚠️ Fuori pista (23:40), i codici di fine di un controllo**: il test esistente «prodotto = dichiarato» di
> `test_backup_restore.py` vuole in `RestoreErrorCode` solo i codici con cui un controllo in background può finire.
> `wrong_password` ed `envelope_unsupported` sono risposte sincrone di `POST /restore/stage` (400 e 409, descritte nelle
> sue risposte), mai la fine di un controllo. Nell'enum entrano quindi solo `password_required` ed `envelope_damaged`,
> scritti come letterali (`StagingError("envelope_damaged", …)`), così il test li vede. In più, in `start_check` si legge
> l'intestazione prima di chiedere la password: una busta che non si può aprire non chiede una password.
>
> **Rossi, eseguiti uno alla volta nella corsia** (23:20-23:50), tutti rossi per il motivo giusto:
>
> - `services backup-envelope`: 100 errori al setup (`ModuleNotFoundError` di `envelope`);
> - `services backup-secure-rules`: errore di raccolta (manca `secure`);
> - `services password-policy`: 21 falliti (i nuovi), 53 passati (quelli di A);
> - `api no-echo-route`: errore di raccolta (manca `no_echo`); la categoria `api` ha ricostruito il frontend prima di
>   avviare il server (comportamento del runner: le sorgenti erano cambiate col merge e coi test di TA-F);
> - `services backup-secure`: 52 falliti (moduli, parametri e campi mancanti);
> - `utils backup-cli-secure`: 42 falliti (argparse exit 2, modulo mancante).
>
> I sei test-author: busta 28 funzioni (100 casi), regole e 422 21 + 24 + 8 più la guardia di H-17, servizi 26 (52
> casi), API 14 (24 casi) più BACKUP-001, CLI 18 (42 casi), frontend 8 file. Selettori nuovi registrati nel runner
> (aggiunte): `services backup-envelope`, `backup-secure-rules`, `backup-secure`; `api backup-secure` (esclusivo: fa
> backup veri sul server della corsia), `api no-echo-route`; `utils backup-cli-secure`.
>
> **Codice applicato (00:10)**, dagli script preparati fuori dal worktree (`files/b4-wip/apply_b4_*.py`), ognuno
> verificato prima con `--check`:
>
> - backend: `envelope.py`, `secure.py`, `api/no_echo.py` (nuovi); `paths`, `manifest`, `archive` (la voce della chiave,
>   `read_instance_key`), `jobs` (cifratura, fase `encrypting`), `staging` (decifratura, voce della chiave, rekey e
>   conteggi), `restore_jobs` (password sincrona, upload tenuto, `kind`), gli schemi, le due rotte, `job_views`, la CLI
>   (`--encrypt`, `--password-file`, `--password-stdin`, `decrypt`, niente abbreviazioni delle opzioni);
> - sui file degli altri, per la loro revisione: A (`password_policy.py`: `rules=`, `rules_with_minimum_length`;
>   `PasswordStrength.svelte`: la prop `rules`), X (`plugin_settings.py` importa la classe spostata), H (la riga della
>   docstring di `derive_key_from`; `instance_block.py` e il suo test: `get_instance_backup_options` permessa sull'istanza
>   bloccata, come le altre rotte del backup);
> - frontend: `backupApi`, `backupJob`, `restoreFlow` (stato `password`), le due card, la modale del report,
>   `restoreText`, i quattro cataloghi di `backup/` (19 chiavi di TA-F più `mode.legend`, `password.intro`,
>   `readyEncrypted`, `warnings.instance_key_unusable`; aggiornati `download.description` e `report.keyIncluded`).
>
> Poi: import senza cicli; ruff (due ordini di import corretti, due C901 risolti estraendo `_print_written` e
> `_print_key_and_secrets` nella CLI), black; `api sync`; `i18n build` e `i18n check` (4935 chiavi × 4, rigoroso);
> Prettier senza modifiche. Le fixture E2E con i campi nuovi le aggiorna TA-F.
>
> **Verdi (00:08-00:29)**, uno alla volta nella corsia:
>
> - `services`: `backup-envelope` 100, `backup-secure-rules` 24, `password-policy` 74, `backup-secure` 52, `backup-jobs`
>   69, `backup-archive` 155 (+1 salto voluto), `backup-staging` 145;
> - `utils`: `backup-cli-secure` 42, `backup-cli` 102, `backup-cli-restore` 77;
> - Vitest: 928 (logica, `PasswordStrength`, i suoi usi in registrazione, reset e cambio password) e 159 (le tre card).
>
> **⚠️ Fuori pista**:
>
> - `utils backup-cli` al primo giro: 22 rossi. I test esistenti costruiscono a mano un `Namespace` senza le opzioni
>   nuove, e `cmd_create` leggeva `args.encrypt`. Corretto nel codice, non nei test: le tre opzioni si leggono con
>   `getattr` e un default (chi costruisce il suo `Namespace` resta senza password, come prima di B4). Poi 102 verdi.
> - Vitest, un rosso: TA-F vuole che `getInstanceBackupOptions()` restituisca la risposta così com'è (identità), e io
>   la ricostruivo per restringere il tipo. Ora la funzione fa un cast unico dopo lo schema zod, come
>   `startRestoreCheck`. Poi 259 verdi.
> - Sotto carico (~65) e con otto file in parallelo, il `beforeAll` di due file di card è andato in timeout (import
>   dinamico oltre 60 s): rilanciati da soli, si caricano. Non è un esito sul codice: ora le card girano in un lotto a
>   parte.
>
> In corso: i verdi `api`, poi `services backup-apply`; revisione di sicurezza (agente, in sola lettura); doc
> (docs-writer). Righe sui file degli altri mandate al coordinatore per la revisione di A, X e H (00:31).
>
> **Revisioni (00:31-00:45)**:
>
> - **sicurezza** (agente, in sola lettura): nessuna vulnerabilità; ogni area è sana per un motivo detto (nonce, AAD,
>   valore di controllo, limiti prima di scrypt, voce della chiave, rekey, password mai in stato, log, 422 o argomenti,
>   symlink, file in chiaro rimossi). Due note:
>   - `2^15` sta sotto il minimo OWASP (`2^17`), scelta P12 del developer: scrivere `2^16` è possibile (i lettori lo
>     accettano già). Nota al developer, non bloccante;
>   - una cartella `backups/.decrypt-*` lasciata da un `inspect` ucciso non la toglie nessuno. Correzione nel lotto:
>     prima il test rosso (TA-E), poi il codice (`apply_b4_cli_sweep.py`: tolte quelle più vecchie di un'ora, mai link
>     né file);
> - **X: OK.** Una correzione: `patterns/plugin_settings.md:425` nominava `_NoInputEchoRoute` (fatta);
> - **A: OK.** Una nota facoltativa: `PasswordStrength` leggeva una lista vuota come «assente»; ora `rules != null`,
>   come `rules=[]` nella policy (commento e documentazione della prop);
> - **H: OK sul codice.** Le correzioni:
>   - la docstring di `instance.py` («the five routes», fatta);
>   - la docstring di `derive_key_from` con la sua formula («a clear archive, or a key the environment gives», fatta);
>   - le righe di `security.md` (tabella di `ALLOWED_WHEN_BLOCKED`) e di `hosting_providers.en.md` sulla rotta
>     `options`, passate al docs-writer;
> - **coordinatore (X-R22)**: `backup_restore.en.md:33` si allinea all'ordine di H-3, passato al docs-writer.
>
> **⚠️ Fuori pista: un errore di svelte-check nella build**, invisibile a Vitest, che non controlla i tipi. Il client
> rigenerato tipizza il corpo facoltativo di `POST /backup/instance` come `InstanceBackupRequest | null`, quindi
> `undefined` non va più. Ora `startInstanceBackup()` passa `null`, come fa già `UsersTab`. Il client dell'app valida
> solo le risposte: `null` e `undefined` partono entrambi senza corpo. Le asserzioni che fissavano `undefined` le
> ripara TA-F.
>
> **Verdi `api` (00:34-01:13)**: `no-echo-route` 8, `backup-secure` 24, `backup-restore-apply` 136, `plugin-settings`
> 14. **⚠️ Fuori pista**:
>
> - `api backup`: il server condiviso non ha risposto in 300 s. Mentre girava la costruzione dei prerequisiti erano
>   cambiate le sorgenti del frontend (le riparazioni di TA-F e la mia di `backupApi.ts`), e l'avvio ha rifatto la build
>   di debug sotto carico. È infrastruttura, non un esito: si rilancia alla fine, senza modifiche in volo. Regola per me:
>   niente modifiche al frontend mentre gira un selettore `api`;
> - `api backup-panel` (6 rossi) e `api backup-restore` (2 rossi): i doppi di test scritti prima di B4 non accettano le
>   parole chiave nuove (`start_backup(…, password=)`, `stage_archive(…, key=)`), e un test fissava la risposta
>   dell'upload a `{upload_id, size}`. Il codice di produzione passa le parole chiave in modo esplicito, ed è giusto
>   così: le riparazioni dei doppi (anche quello di `test_instance_block.py`, di H) le fa TA-D.
>
> **Dopo la revisione di sicurezza e la doc, due correzioni piccole, prima i rossi**:
>
> - la pulizia delle cartelle `backups/.decrypt-*` lasciate da un `inspect` ucciso (test di TA-E);
> - il download di un `.lfbk` servito come `application/octet-stream` e non come zip (trovato dal docs-writer; test di
>   TA-D). Il tipo si sceglie dal nome del file, non rileggendo il job: PANEL-019 fissa le chiamate del download;
> - in più, l'aiuto di `--password-file` diceva «la prima riga», ma `read_secret_file` legge tutto il file: corretto il
>   testo.
>
> **Doc (docs-writer, 01:00)**:
>
> - `admin/backup_restore.en.md`: una sezione nuova `#secure` e una tabella `#secure-problems`, più tutte le sezioni
>   toccate da B4; dentro anche la correzione X-R22 (l'ordine di H-3);
> - `developer/architecture/security.md`: la sezione nuova `#secure-backups`, più le righe di A (`#password-rules`) e
>   di H (`#instance-key` e la tabella di `ALLOWED_WHEN_BLOCKED`);
> - `admin/hosting_providers.en.md`: la rotta `options` sull'istanza bloccata;
> - una frase ciascuna in `configuration`, `filesystem` e `docker_advanced`;
> - `cli_tools.en.md` (fuori dal brief, giusto: ripeteva quattro volte che la chiave non è mai nell'archivio);
> - `frontend/state/app-state.md`, `features/auth.md` e `core-ui/atoms.md`.
>
> Debito di traduzione preesistente: `cli_tools`, `configuration`, `filesystem`, `docker_advanced`. Nel backlog B-19:
> `decrypt` lanciato da root scrive uno zip di root (la guida lo dice).
>
> **Fine del giro `api` (01:11-01:18)**: `api instance-block` 2 rossi e `api backup-instance-errors` 6 rossi, per gli
> stessi doppi di prima di B4; `services backup-apply` 228 verdi. **⚠️ Fuori pista**: `api backup-roundtrip` non
> esiste, il selettore è `e2e backup-roundtrip`. Errore mio nella lista: argparse esce con 2 prima di partire, nessun
> dato toccato.
>
> **Doppi riparati da TA-D (01:20)**, cinque, senza cambiare il senso dei test:
>
> - `test_backup_panel.py`: il finto `start_backup` accetta `password` e la registra a parte (`start_passwords`).
>   PANEL-013 e PANEL-018 verificano `[None]`, perché il pannello non cifra mai. Le tuple fissate da altri test non
>   cambiano;
> - `test_backup_instance_errors.py:68` e `test_instance_block.py:821` (di H): solo la firma, `password=None`;
> - `test_backup_restore.py`: il finto `stage_archive` accetta `key=None`. La risposta dell'upload ora è
>   `{upload_id, size, kind}`, con `kind == "zip"`.
>
> Il grep di tutti gli altri doppi (`build_archive`, `archive_name`, `_run`, `start_job`, `_run_check`, `_stage`, le
> regole, gli helper della CLI) non trova altro da riparare: accettano già `**kwargs`, oppure B4 li chiama come prima.
>
> **I rossi delle due correzioni (01:18-01:20)**, per il motivo giusto:
>
> - `utils backup-cli-secure`, 1 rosso su 43: `.decrypt-killed` e `.decrypt-old` restano;
> - `api backup-secure`, 2 rossi su 24:
>   - `test_a_secure_backup_is_an_envelope_its_password_opens`: l'`.lfbk` esce come `application/zip`;
>   - `test_openapi_documents_the_secure_backup`: l'OpenAPI dichiara solo `application/zip`.
>
> **Codice (01:22)**, ogni script verificato prima con `--check`:
>
> - `apply_b4_cli_sweep.py`, 3 operazioni: `_remove_stale_decrypt_folders`, che con `lstat` toglie solo le cartelle
>   vere più vecchie di 3600 s, mai un link né un file;
> - `apply_b4_download_type.py`, 4 operazioni: il tipo scelto dal suffisso (`FILE_SUFFIX`), `FILE_RESPONSES` con i due
>   tipi, e l'aiuto di `--password-file`.
>
> Ruff e black puliti, poi `api sync`. Nel client generato la risposta del download resta `z.void()`, e la UI scarica
> con un link `download`: per il frontend non cambia niente.
>
> **In corso (dalle 01:25)**: la catena finale `files/scripts/b4_final_chain.sh`, un passo alla volta:
>
> - i verdi `utils` e `api` della lista, più `e2e backup-roundtrip` e `api registration` (prova sul percorso di A);
> - Vitest in quattro lotti: logica, schermate di A con `PasswordStrength`, card, client;
> - i controlli statici;
> - la doc.
>
> **Verdi backend (01:25-01:49)**, uno alla volta nella corsia, carico < 50:
>
> - `utils`: `backup-cli-secure` 43, `backup-cli` 102, `backup-cli-restore` 77;
> - `api`: `backup-secure` 24, `backup` 23, `backup-restore` 122, `backup-panel` 59, `instance-block` 62,
>   `backup-instance-errors` 6. `backup-secure` ha rifatto la build del frontend per il client rigenerato (7 minuti, fuori
>   dal tempo di avvio), svelte-check 0 errori;
> - `e2e backup-roundtrip` 3.
>
> **⚠️ Fuori pista: slot.** Alle 01:49 il coordinatore ha visto un `dev.py test` sulla mia corsia. I selettori `api` e
> `e2e` chiedono uno slot anche se sono mirati, e io li avevo contati come leggeri. Erano già finiti tutti, e la corsia
> era libera dalle 01:49. Ho fermato la catena per PID mentre aspettava il carico prima di `api registration` (la prova
> facoltativa sul percorso di A: tolta). Il resto non usa la corsia: `files/scripts/b4_final_rest.sh`, cioè Vitest, i
> controlli statici e la doc. Regola per me: ogni `api`/`e2e`, anche di un solo file, solo in uno slot chiesto prima.
>
> **Metà leggera (01:50-01:58)**, senza server di corsia:
>
> - Vitest: 799 (9 file: logica del backup, `PasswordStrength`, `PasswordInput`, ICU, regole), 184 (le 4 schermate di A
>   con l'indicatore), 159 (le tre card), 17 (il client);
> - `theme-roles` pulito, gate 215, `front check` 0 errori e 0 avvisi, `i18n check` 4935 chiavi, rigoroso;
> - `lint --dead-code` rosso come prima (era rosso già alle 13:07 del 16/10, per voci di altri). B4 non aggiunge nulla.
>   L'unica voce di B è di B5c, `RESTORE_TICKET_HEADER`: il test lo legge con un cast → backlog B-20;
> - check-links valido, `gate-docs-links` 63.
>
> **⚠️ Fuori pista: la build rigorosa della doc è rossa, con 4 avvisi.** `admin/backup_restore.en.md` esiste solo in
> inglese, e quattro link nuovi puntano ad ancore che esistono solo nelle pagine inglesi di destinazione:
> `configuration.md#instance-key`, `#secret-files`, `#startup-checks` e `cli_tools.md#backup-decrypt`. La build tradotta
> rende la pagina inglese con i link risolti verso le pagine tradotte, e lì quelle ancore mancano. La regola c'è già
> (devWiki `decisions/docs-anchors-from-the-render.md`): una pagina solo inglese linka le pagine tradotte senza ancora,
> salvo un id esplicito presente in tutte e quattro le lingue. La correzione la fa il docs-writer, solo nella pagina; la
> build la rilancio io.
>
> **Correzione della doc (docs-writer, 02:00)**: sei link senza ancora (`#startup-checks` compariva tre volte). Ora
> ogni link va alla pagina, e la frase nomina la sezione («The Instance Key» in [Environment Variables](…)), nella
> forma che la pagina usava già. Le ancore rimaste esistono in tutte e quattro le lingue (`#updating`,
> `#start-the-server`, `#session-persistence`, `#reset-a-password-or-lock-an-account`), oppure portano a pagine senza
> traduzione. Nota del docs-writer, preesistente e non di B4: in inglese `#reset-a-password-or-lock-an-account` è solo
> lo slug del titolo. Funziona, ma si rompe se il titolo cambia. Lasciata com'è.
>
> **Verdi della doc (02:03-02:06)**: build rigorosa exit 0 (80 s, 3084 URL di asset risolti), check-links valido,
> `gate-docs-links` 63. Poi una parola nella docstring della pulizia («older than an hour», com'è il confronto), ruff e
> black puliti, `utils backup-cli-secure` 43. `git diff --check` pulito, porta 6187 libera.
>
> **Handoff (02:10)**: CHECKPOINT READY al coordinatore, con i percorsi per proprietario e i tre OK (A, X, H), più la
> riga nuova per H (la firma del finto `start_backup` in `test_instance_block.py:821`). Insieme: il blocco finale del
> CHANGELOG (`files/next-checkpoint/changelog-b4.md`), le due note per il developer (il default «in chiaro»; scrypt
> `2^16`, già leggibile da ogni lettore), il debito di traduzione e B-18/19/20. Restano per dopo il checkpoint: gli E2E
> FBKP-108/109 in uno slot. 🧊 FROZEN.

> Sola lettura, nessun codice. Il contratto intero è nella cartella della sessione (`files/b4-contract.md`: §2-§6
> aggiornati a P12, §9 nuovo); qui il riassunto.

**Stato reale** (HEAD `e3a96d9da` + merge aperto di `cd617824e`):

- H: `derive_key_from(key, purpose, length)` **è in base** (`instance_key.py:85`). La sua docstring dice «l'archivio
  lascia fuori la chiave»: vero solo per gli archivi in chiaro di oggi. L'analisi H-3 di H dice già «solo un archivio
  protetto da password potrà contenerla (B4)». La decisione 39 resta; una riga della docstring va aggiornata (file di H,
  sua revisione).
- Nessuna lettura pubblica della chiave generata. Bastano però due funzioni pubbliche:
  - `instance_key_status()` (`generated`, senza `problem`);
  - `read_secret_file(path)`, come la docstring di `derive_key_from` dice di leggere un file di chiave.

  Proposta: nessuna funzione nuova nel modulo di H, che rivede le ~10 righe di B. Così **B4a e B4b diventano un lotto
  solo**.
- X: invariato (`count_unreadable_secrets`, `rekey_plugin_secrets`, `settings_subkey`).
- A6c:
  - `password_policy.py`: 5 regole, minimo 8; `failed_rules()`, `password_rules_public()` in `GET /system/instance`;
  - `PasswordStrength.svelte` legge le regole solo da lì, senza una prop.
- `cryptography` 50.0.2.

**Scoperte sul codice**

1. `_run_check` toglie l'upload nel `finally` (`restore_jobs.py:254`): una password sbagliata trovata dal thread
   costerebbe un nuovo upload, fino a 500 MB.
   - → La password si controlla **subito, nella richiesta** `POST /restore/stage`: l'intestazione di 52 byte più scrypt
     2^15, circa 0,1 s. La rotta è `def` e il controllo gira sotto il lock dei controlli.
   - `password_required`, `wrong_password` ed `envelope_unsupported` rispondono subito e **tengono l'upload**.
   - Al thread va la chiave AES derivata, mai la password.
2. Un 422 di FastAPI ripete il corpo (`input`): con un campo mancante ripete anche la password (provato con pydantic,
   errore `missing`). X lo toglie già con `_NoInputEchoRoute`, privato in `api/v1/plugin_settings.py:35`.
   - → Spostarlo in un modulo comune (X rivede) e usarlo sulle rotte del backup che ricevono una password.
   - Osservazione per il backlog di A: registrazione, cambio e reset della password hanno lo stesso eco.
3. La pulizia del job (`_remove_work_files`, `jobs.py:265`) toglie già lo zip in chiaro quando il file tenuto è la
   busta, anche in caso di errore: nessuna pulizia nuova.
4. B3 non prende nessuna impronta della copia controllata: il rekey dopo l'upgrade non rompe niente.
5. I traceback del log non stampano le variabili locali (`format_exc_info`).

**P12 senza copiare le regole**

- Backend (file di A: scrivo io, A rivede): `failed_rules(password, rules=…)`, `password_rules_public(rules=…)` e
  `rules_with_minimum_length(n)`. B usa le regole di A con il minimo a `max(minimo di A, 12)`.
- `GET /backup/instance/options` → `{password_rules}`, per la scheda.
- `PasswordStrength` riceve una prop facoltativa `rules` (componente comune: A rivede).
- Limiti dell'intestazione in lettura: `log2(n)` da 14 a **16**, cioè al massimo 64 MiB, il doppio di quello che
  scriviamo. Anche in lettura una busta ostile o futura non satura la RAM delle macchine piccole.

**Superfici**

- nuove: `instance_backup/envelope.py`, il modulo comune del 422 senza eco;
- di B: `jobs.py`, `staging.py`, `restore_jobs.py`, `manifest.py`, `schemas/backup.py`,
  `api/v1/backup/{instance,restore,job_views}.py`, `scripts/backup_cli.py`, `features/backup/*`, i18n `backup` (4
  lingue), `admin/backup_restore.en.md`;
- condivise:
  - di A: `password_policy.py` e `PasswordStrength.svelte`;
  - di X: `api/v1/plugin_settings.py`;
  - di H: la docstring di `instance_key.py`;
  - il catalogo del runner (`backup-envelope`, un'aggiunta) e il client generato (`api sync`);
  - del coordinatore: `CHANGELOG.md`.

**Conflitti previsti**: bassi. `password_policy.py` e `PasswordStrength.svelte` se A li tocca ancora,
`plugin_settings.py` se X ha un lotto in volo.

**Rischi**

- la crittografia la montiamo noi: servono vettori fissi e la revisione di sicurezza, obbligatoria;
- spazio: zip + busta durante la creazione (2×), busta + zip + copia durante il controllo (3×), controllati prima;
- lo zip in chiaro resta un momento su disco durante la creazione (P12 §3: accettato), `0600`;
- P24 (opzione A di H-3, aperto): oggi nessun effetto. Se entra, `settings_subkey()` può sollevare: niente rekey, tutti
  i segreti contati illeggibili, e il ripristino va avanti.

**Passi** (prima i rossi, col test-author)

1. La busta: `envelope.py` e `services backup-envelope`:
   - il giro completo;
   - un vettore fisso calcolato a parte, con le primitive di `cryptography`;
   - ogni manomissione;
   - un'intestazione ostile rifiutata prima di scrypt;
   - NFC, e il `.part` tolto.
2. Regole e 422: le righe di A con i loro test, lo spostamento della classe di X.
3. Creazione:
   - il corpo della richiesta;
   - nel job `encrypted` e la fase `encrypting`;
   - la chiave generata dentro l'archivio (B4b);
   - `options`.
4. Ripristino:
   - `kind` dell'upload;
   - il controllo sincrono della password e la fase `decrypting`;
   - la chiave tenuta in memoria, mai scritta nella copia;
   - il rekey;
   - nel report `secrets_unreadable` e `secrets_rekeyed`.
5. CLI:
   - la password da `--password-file`, da `--password-stdin` o da due `getpass`;
   - `decrypt`;
   - `inspect` e `restore` di una busta.
6. UI:
   - la scelta «in chiaro» / «sicuro» col testo della decisione 39;
   - la password due volte, con l'indicatore;
   - al ripristino la password chiesta prima dell'upload, e una nuova prova senza ricaricare;
   - le righe del report.
7. Chiusura:
   - doc (docs-writer) e `api sync`;
   - i controlli e la revisione di sicurezza;
   - in uno slot gli E2E FBKP-108 (il giro sicuro) e FBKP-109 (la password sbagliata).

Più il test di guardia di H-17: un valore di prova nella tabella di H, e la funzione che lo segue.

**Selettori**

- backend:
  - `services`: `backup-envelope` (nuovo), `backup-jobs`, `backup-staging`, `backup-apply`, `password-policy`,
    `plugin-settings-crypto`, `profile-defaults`;
  - `api`: `backup`, `backup-instance-errors`, `backup-panel`, `backup-restore`, `backup-restore-apply`,
    `backup-roundtrip`, `plugin-settings`;
  - `utils`: `backup-cli`, `backup-cli-restore`;
- frontend: Vitest su `features/backup/*` e `PasswordStrength`;
- E2E: `front-utility backup` in uno slot.

**Fatto quando**:

- un backup sicuro, creato dalla UI o dalla CLI, si apre solo con la sua password;
- si ripristina con le chiavi dei fornitori ricifrate con la chiave dell'istanza;
- una busta manomessa, o una password sbagliata, si rifiuta senza perdere l'upload;
- nessuna password finisce nel log, nello stato o in una risposta;
- la revisione di sicurezza non lascia rilievi aperti.

**Domande**

- *Per il developer* (non bloccante; di notte vado avanti con la mia scelta): la scelta della scheda parte da «in
  chiaro» o da «sicuro»? Propongo «in chiaro»: è il comportamento di oggi, e la specifica dice «opzione».
- *Per il coordinatore*:
  - gli scrittori delle righe di A, X e H (propongo: scrivo io, il proprietario rivede, come per le righe di H);
  - il lotto unico B4a+B4b;
  - più avanti, uno slot per gli E2E.
- *Facoltativo, non proposto ora* (→ backlog B-18): `restore --instance-key-file` nella CLI. Con la copia della chiave
  vecchia dell'admin si ricifra anche un archivio in chiaro, per esempio all'uscita dal cloud se il pannello consegna la
  sua chiave.

### B4 committato; validazione combinata su `33275d9a6` e gli E2E FBKP-108/109 (2026-10-17, 02:07-03:27) ✅ — 🧊 FROZEN, checkpoint pronto

> **Il coordinatore (02:07)**:
>
> - B4 è committato in tre commit: `df1f0d52c` (codice, test, runner), `0ff310355` (doc), `97037bb2e` (journal);
> - base aggiornata: merge pulito di dev `b1b4960c4`, HEAD **`33275d9a6`**;
> - la riga in più di H (`test_instance_block.py:821`, solo la firma) l'ha controllata lui: OK;
> - A7b-2 (il gestore globale del 422 senza `input`, `api/validation_errors.py`) entra in dev dopo il suo
>   `all-backend`. Copre anche le rotte di B; `NoInputEchoRoute` resta, A-37 lo toglie più avanti;
> - la domanda su scrypt è passata al developer. Il default «in chiaro» c'era già.
>
> Validazione combinata in due metà:
>
> 1. **leggera**, a carico < 50: `api sync`, `front check`, il Vitest del backup, `services backup-*`,
>    `password-policy`, mkdocs rigoroso e check-links;
> 2. **in uno slot** (lo dà lui, fra 30-40 minuti): `api backup-secure backup backup-restore instance-block`,
>    `e2e backup-roundtrip` e `front-utility backup` con FBKP-108/109.
>
> Prima, il freeze FE8b (W, una rinomina): nessuno tocca `components/transactions/**`, `utils/transactions/**`,
> `stores/transactions/**`, né `_frontend_transaction.py` e `_frontend_utility.py`. Controllato in sola lettura: B4 non
> tocca quei percorsi, e nessun file di B importa da quelle cartelle.
>
> **HEAD verificata (02:12)**: `33275d9a6`, pulita.
>
> **⚠️ Fuori pista: FBKP-108/109 non esistono.** La spec si ferma a FBKP-107. L'analisi li nominava per la chiusura
> (passo 7), e nel mio handoff li avevo dati per «non eseguiti», come se ci fossero. Corretto col coordinatore (02:15).
> Li scrive ora TA-F, solo in `backup.spec.ts`:
>
> - **FBKP-108**: un backup sicuro dalla UI, il download dell'`.lfbk` (comincia con `LFBK`), il controllo con la
>   password, il report di un archivio cifrato, poi «Drop this archive»; nessuna password resta in `localStorage` o in
>   `sessionStorage`;
> - **FBKP-109**: un `.lfbk` fatto via API. Una password sbagliata lo chiede di nuovo con un solo upload (un `PUT`, due
>   `POST` del controllo), poi quella giusta e «Drop this archive».
>
> Nessuna riga nuova nel runner: `front-utility backup` gira tutto il file, e `_frontend_utility.py` è congelato. Sono
> gli E2E di chiusura previsti dall'analisi, scritti dopo il codice: non sono rossi prima. TA-F non lancia nulla nella
> corsia: solo `tsc -p tsconfig.e2e.json` e Prettier sul suo file.
>
> Verificato nel codice, per il brief: `cancelPassword()` non chiama il server. Un upload lasciato dopo una password
> sbagliata lo toglie l'upload seguente (`_remove_replaced_uploads`) o `prune` dopo `STAGE_LIFETIME`: niente perdite.
>
> **Metà leggera (dalle 02:16)**: `files/scripts/b4_combined_light.sh`, un passo alla volta, col carico che aspetta
> sotto 50 (alle 02:14 era 117):
>
> - `api sync`;
> - `services`: `password-policy` e i nove `backup-*`;
> - `utils`: i tre `backup-cli*`;
> - Vitest in quattro lotti;
> - `front check`, `theme-roles` e i gate (il merge può muovere la baseline dei colori), `i18n check`;
> - mkdocs rigoroso, check-links e `gate-docs-links`.
>
> **Freeze della galleria fino alle ~03:30** (coordinatore, 02:17; il gruppo dei colori, carico a 170): nessun passo
> pesante nuovo (`api`, E2E, `all-backend`, `--workers`) fino al suo via; solo controlli leggeri sotto 50. Lo slot di B
> (~30 minuti) viene dopo il freeze, dopo Y e J. La metà leggera aspetta il carico (alle 02:17: 181, nessun passo
> partito); TA-F intanto scrive FBKP-108/109.
>
> **FBKP-108/109 scritti (TA-F, 02:40)**, solo in `backup.spec.ts`, in coda al blocco seriale `restoreTest` (240 s per
> test, dopo FBKP-107: un rosso lì non salta nessun caso). Nessun file sotto `frontend/src/`, nessuna riga del runner.
> Prettier `--check` pulito senza `--write`; `tsc -p tsconfig.e2e.json` 0 errori nel file (4 altrove, preesistenti).
>
> - **FBKP-108**:
>   - la password è costruita dalle regole di `GET /backup/instance/options`: un codice sconosciuto fallisce per nome, e
>     il minimo deve essere ≥ 12;
>   - una password lunga un carattere meno del minimo tiene spento «crea». Il caso aspetta così anche l'arrivo delle
>     opzioni, perché le regole degli account chiedono meno caratteri;
>   - poi il backup sicuro: `backup.created` e il job dicono `encrypted`, il nome è `.lfbk`, il file comincia con `LFBK`;
>   - nella card del ripristino: la password chiesta prima di inviare qualcosa, la fase `decrypting`, un `PUT` e un
>     `POST` con `{upload_id, password}`, il report del server `encrypted: true`, le righe della chiave e dei segreti
>     uguali al report del server;
>   - «Drop this archive», e nessuna delle due password resta negli storage, nell'anello degli eventi o nei cookie;
> - **FBKP-109**:
>   - l'archivio sicuro è fatto via API, col job registrato per la pulizia e poi cancellato;
>   - una password sbagliata dà `restore-password-error` con `data-error-code="wrong_password"`, e il campo si
>     svuota;
>   - con la password giusta: un `PUT` e due `POST` sullo stesso `upload_id`, il primo 400 `wrong_password`;
>   - dopo «Drop this archive», un nuovo `POST` dello stesso upload risponde 404 `backup_upload_not_found`: l'upload è
>     andato via col suo controllo.
>
> Rivisti da me sul codice: i testid (`backup-mode`/`data-mode`, `backup-encrypted-note`, `PasswordInput` mette il
> testid sull'`<input>`, `data-passed` del misuratore, `restore-password-error`, `data-phase`), il 201 dell'upload e il
> codice `backup_upload_not_found`. Anche l'helper condiviso `createBackup`: non fissa il dettaglio intero di
> `backup.created`, quindi il campo `encrypted` aggiunto da B4 non rompe FBKP-002.
>
> **Le due segnalazioni di TA-F, decise**:
>
> - il report del ripristino non mostra se l'archivio era cifrato (nessun attributo). Il contratto (§7, «Report modal»)
>   chiedeva solo le righe dei segreti, quindi la UI è conforme. L'E2E verifica `encrypted` sul report del server dello
>   stesso controllo, più la password chiesta prima e la fase `decrypting`. Nessun gancio solo per il test;
> - finché le opzioni non arrivano, il misuratore usa le regole degli account (minimo 8): «crea» si può accendere per
>   una password che il server rifiuta con `password_too_weak`. È la scelta scritta nel commento della card: il server
>   controlla comunque, la finestra dura millisecondi, e se le opzioni falliscono l'errore ha il suo messaggio. Lasciato
>   così.
>
> **B-21 nel backlog (coordinatore, 02:50; da H, H-27 in dev `bfdc1f72c`)**. `profile_default()` solleva
> `ProfileDefaultError` (un `TypeError`) su una tabella sbagliata. Le due rotte di `restore.py` prendono solo
> `BackupConfigError`, e sono le sole che chiamano `backup_max_upload_mb()`:
>
> - l'upload darebbe 500 invece del 503;
> - `GET /restore/status` darebbe 500 invece di `upload_limit_mb: null`. Questo è peggio di quanto detto: la scheda non
>   leggerebbe più lo stato.
>
> Da fare dopo l'ingresso di H-27 nel ramo. Il test di guardia H-17 usa `123`, un intero: compatibile.
>
> **Metà leggera, tutta verde (02:28-03:06)**, su `33275d9a6`, un passo alla volta a carico < 50 (con lunghe attese:
> carico fino a 181):
>
> - `api sync`;
> - `services`: `password-policy` 74, `backup-envelope` 100, `backup-secure-rules` 24, `backup-secure` 52,
>   `backup-archive` 155 (+1 salto voluto), `backup-jobs` 69, `backup-staging` 145, `backup-apply` 228,
>   `backup-outcome` 97, `backup-totals` 84;
> - `utils`: `backup-cli` 102, `backup-cli-restore` 77, `backup-cli-secure` 43;
> - Vitest: 799, 184, 159, 41. Il client passa da 17 a 41 test: sono quelli arrivati col merge di dev;
> - `front check` 0 errori e 0 avvisi, `theme-roles` pulito, gate 215, `i18n check` 4967 chiavi (rigoroso);
> - mkdocs rigoroso exit 0, check-links valido, `gate-docs-links` 63. Porta 6187 libera.
>
> **⚠️ Fuori pista: un annuncio in anticipo.** Alle 02:50 ho scritto al coordinatore «tutti e 10 i `services` verdi»,
> ma `backup-totals` non era ancora partito (lo era alle 02:47, verde). Lo correggo nel resoconto. Regola per me: un
> risultato si annuncia dopo averlo letto, mai prima.
>
> **Lo slot (coordinatore, 03:06)**: il freeze è finito; un nuovo blocco della galleria va dalle ~03:50 alle ~04:45. Lo
> slot di B4 (~30 minuti) è il secondo, appena finisce l'`all-backend` di A. Se non può chiudersi prima delle 03:50, si
> sposta a dopo le 04:45. Lo script dello slot è pronto: `files/scripts/b4_slot.sh`, senza attesa del carico, un
> selettore alla volta:
>
> - `api backup-secure` (rifà la build del frontend), poi `api backup`, `backup-restore` e `instance-block`;
> - `e2e backup-roundtrip`;
> - `front-utility backup`, coi worker di default (1, seriale): tutta la spec, FBKP-108/109 compresi.
>
> **Slot 2 (03:12-03:27) ✅, tutto verde.** L'ordine è cambiato: prima `front-utility backup`, il pezzo più nuovo e più
> lungo; ogni pezzo partiva solo se la sua stima stava prima delle 03:50.
>
> - `front-utility backup`, primo giro (03:12-03:20, con la build di debug del frontend): 12 passati, **FBKP-108
>   rosso**, FBKP-109 non eseguito (spec seriale);
> - `api`: `backup-secure` 24, `backup` 23, `backup-restore` 122, `instance-block` 62;
> - `e2e backup-roundtrip` 3;
> - `front-utility backup`, secondo giro dopo la riparazione (03:24-03:27): **14 passati**, FBKP-108 e FBKP-109
>   compresi (1,8 minuti). Porta 6187 libera alle 03:27.
>
> **⚠️ Fuori pista: il rosso di FBKP-108 era del banco di prova, non del prodotto.** FBKP-108 era arrivato quasi in
> fondo: backup sicuro, download, password, controllo e report. Si è fermato su `schemas.RestoreUpload.parse(upload?.json)`
> (riga 1559): lo stato era 201, ma `response.json()` di Playwright non riusciva a leggere il corpo della risposta
> all'upload della pagina, un XHR (axios con `onUploadProgress`) che porta la busta, decine di MB. La pagina invece
> l'aveva letta:
>
> - il controllo era partito con l'id giusto ed era arrivato al report;
> - `lane.checks` corrispondeva;
> - il JSON della risposta al `POST` si leggeva.
>
> Riparazione (TA-F, 03:23, solo la spec; `tsc` e Prettier puliti): l'id dell'upload si prende dal corpo della prima
> richiesta del controllo (`sent[1].body`, 32 esadecimali) e i corpi restano verificati esattamente. In FBKP-109 i due
> `POST` portano lo stesso id, prima la password sbagliata e poi quella giusta, e il nuovo `POST` dopo «Drop this
> archive» usa quell'id. Tolte `kind` e `size` della risposta all'upload: le fissa `api backup-secure`, e FBKP-108
> verifica già `encrypted` sul report del server. Un commento spiega il perché. La spec E2E non conta per la build: il
> controllo delle sorgenti guarda solo `frontend/src` e i file di configurazione, quindi nessuna ricostruzione.

### B4b — le note di E (R13-SEC4) e di J (2026-10-17, 03:10-04:55) ✅ — 🧊 FROZEN, checkpoint pronto

> **Il coordinatore (03:08 e 03:10)**:
>
> - la revisione di E su B4 (R13-SEC4, piano 08 in dev `110125350`) non trova niente sopra la soglia, e la crittografia
>   è solida. Quattro note per un lotto B4b subito dopo l'ingresso di B4, prima di B-21;
> - J (J-27): `ledger_totals._as_amount` (la casa) accetta solo testo decimale semplice. Così `_plain` e `_PLAIN_AMOUNT`
>   di `totals.py` ripetono lo stesso controllo, e la scelta è di B.
>
> Il nome «B4b» è del coordinatore. Il B4b dell'analisi (la chiave dentro l'archivio) è confluito in B4.
>
> **Verifica sul codice, in sola lettura (HEAD `33275d9a6`)**. Le note reggono tutte:
>
> 1. **Chiaro lasciato da un crash.** La pulizia gira solo quando parte un nuovo controllo (`restore_jobs.prune`,
>    chiamata solo da `start_check`) o un nuovo backup (`remove_expired_jobs`, chiamata solo da `_prepare`). Fra i passi
>    di avvio nessuno pulisce: `pending-restore` e `restore-commit` lavorano solo su un ripristino in attesa. Quindi:
>    - (a) `.restore/stage/<id>/archive.zip` (`STAGE_DECRYPTED_ARCHIVE`) resta finché non parte un altro controllo;
>    - (b) `backups/.decrypt-*` resta finché non parte un altro `inspect`;
>    - (c) **in più, non nella nota di E**: un job di backup interrotto lascia lo zip in chiaro e la copia del DB in
>      `backups/.jobs/<id>/`. `get_job` segna `backup_interrupted` senza toglierli, e `remove_expired_jobs` toglie la
>      cartella solo dopo un'ora e solo al backup seguente. È la stessa classe di (b): per un backup sicuro è proprio
>      il chiaro che l'utente non voleva su disco.
>
>    → **B-23**: una pulizia all'avvio di (a), (b) e (c), con le regole della pulizia di B4 (cartelle vere, mai link; per
>    `.decrypt-*` l'ora, perché un `inspect` può girare mentre il server parte). Tocca `STARTUP_STEPS` e `overview.md`,
>    condivisi.
> 2. **Il messaggio di `decrypt`** (`cmd_decrypt`): «It holds every user's data in clear: keep it private, and remove it
>    once used.» Non nomina la chiave d'istanza, che lo zip contiene se il backup la portava, e che apre ogni chiave
>    salvata → **B-24**, messaggio e guida.
> 3. **`--password-stdin`** legge con `sys.stdin.readline()` (`backup_cli.py:100`) senza guardare `isatty()`: su un
>    terminale la password si vede. I due campi della creazione hanno `autocomplete="off"` (`BackupDownloadCard.svelte`)
>    → **B-25**: `getpass` con `isatty()`, e `new-password`.
> 4. **La chiave d'istanza**:
>    - (a) staging accetta la chiave anche da uno `.zip` in chiaro. **Voluto, nessun cambiamento**: è la revisione del
>      contratto delle 23:25 (16/10). Lo zip che `backup decrypt` scrive porta la chiave, e il suo ripristino deve
>      poterla usare. Uno zip costruito ad arte con DB e chiave propri non dà nulla in più a chi lo carica, che è già
>      admin;
>    - (b) la creazione legge `secrets/instance.key` con `read_secret_file`, fino a `SECRET_FILE_MAX_BYTES` (64 KiB), ma
>      ogni lettura dall'archivio si ferma a `INSTANCE_KEY_MAX_BYTES` (4096) → **B-26**: rifiutarlo già all'esportazione,
>      con l'avviso `instance_key_unusable`.
>
> **J-27 → B-22, deciso.** J-27 è già nella base di B: `7336722ad` «fix(ledger-totals): read only plain decimal
> amounts», entrato con `e221a0544`. La regola è identica: `_EXACT.prec` = 60, la stessa di `-?[0-9]{1,60}(\.[0-9]{1,60})?`
> di B. `from_json` rifiuta con un `ValueError` anche tutto il resto che `_plain` controllava (righe che non sono una
> lista, una riga che non è un oggetto, un importo che non è una stringa). `compare_totals` lo traduce già in `absent`.
> L'unico motivo di `_plain` era il pericolo dell'esponente espanso prima della casa, e ora la casa lo evita da sé.
> Decisione: **si tolgono `_plain` e `_PLAIN_AMOUNT`** («una regola, una casa»; regola fondamentale 10). Lo stato
> resta `absent` in ogni caso. I test di B-13 che fissano «deciso prima che `from_json` veda il documento» diventano
> «rifiutato da J», e il fixture `j_reads` resta la difesa contro l'espansione nel processo di test.
>
> **Lotto B4b proposto** (dopo l'ingresso di B4 e il riallineamento alla punta, prima di B-21): B-23 (il più
> importante), B-24, B-25, B-26 e B-22. Prima l'analisi, poi i rossi.
>
> **B4 entrato (coordinatore, 03:28)**: dev `339a59142`, con `8b56f4a62` (FBKP-108/109) e `4d16d583e` (journal); il
> blocco del CHANGELOG (3 ✨ + 3 🔒) in `0a45e45de`. La mia HEAD è portata in avanti a **`0a45e45de`**, pulita. Dentro
> ci sono anche H-27 (`bfdc1f72c`) e J-27 (`7336722ad`).
>
> **Analisi B4b (03:30-03:45), in sola lettura**:
>
> - **B-23 (N66), la pulizia all'avvio.**
>   - (a) I controlli del server. `read_check` chiude come `restore_interrupted` un controllo rimasto `running` senza il
>     lucchetto, e toglie copia e upload. `prune` lo fa quando nessun controllo gira, ma oggi la chiama solo
>     `start_check` → all'avvio basta chiamare `prune(data_dir)`. I controlli della CLI (`restore`, `--dry-run`) lasciano
>     invece cartelle di stage non registrate, che `_prune_unrecorded` toglie solo dopo `STAGE_LIFETIME` (24 h).
>     L'`archive.zip` decifrato vive solo durante lo staging: lo si toglie dopo lo spacchettamento, e su ogni eccezione
>     `rmtree` toglie tutta la cartella. Lo staging tiene sempre il lucchetto dello stage. Quindi, se nessuno lo tiene,
>     ogni `stage/*/archive.zip` è il resto di un kill: all'avvio si toglie (un file vero, `lstat`, mai un link). Il
>     resto della copia segue le 24 h di oggi.
>   - (b) `_remove_stale_decrypt_folders` passa dalla CLI al backend, perché la regola deve avere una sola casa. La CLI
>     la importa, e l'avvio la chiama su `backups/` (se è una cartella vera). La regola dell'ora resta: un `inspect` può
>     girare mentre il server parte.
>   - (c) Nel ramo «interrotto» di `get_job` si aggiunge `_remove_work_files(folder, keep=None)`. È la stessa regola
>     anche senza riavvio, per esempio con un `backup create` della CLI ucciso mentre il server gira. All'avvio: `get_job`
>     su ogni job, che segna e pulisce se il lucchetto è libero, poi `remove_expired_jobs`. La conservazione resta di
>     un'ora; si applica anche all'avvio e non più solo al backup seguente.
>   - Il passo: `Step("backup-leftovers", lambda: asyncio.to_thread(sweep_backup_leftovers))`, subito dopo
>     `restore-commit`. Le tre parti stanno ciascuna in un `try` col suo log e **non sollevano mai**: dopo
>     `restore-commit` un'eccezione fermerebbe ogni avvio (N57). Il passo è idempotente fra più worker, rispetta i
>     lucchetti (della corsa e dello stage) e non segue i link. Modulo nuovo: `instance_backup/leftovers.py`.
>   - La fissazione dell'ordine va in `test_backup_apply.py` (j): `("restore-commit", "backup-leftovers")`.
>     `test_app_lifecycle.py` fissa solo l'ordine dei passi di base, quindi lì nulla cambia. Doc: `overview.md` passa da
>     22 a 23 passi (il nuovo è il 17) e `security.md` (`.decrypt-*` e l'avvio).
> - **B-24.** Dopo la scrittura, `cmd_decrypt` legge il manifesto dello zip appena scritto (`archive.read_manifest`). Se
>   `instance_key.included`, aggiunge una riga: lo zip contiene anche la chiave d'istanza, che apre ogni chiave salvata.
>   Doc: `cli_tools.en.md` (riga 591) e `backup_restore.en.md` (riga 351).
> - **B-25.** In `_password`, `--password-stdin` con `sys.stdin.isatty()` prende la strada del terminale: `getpass`, e
>   due volte quando si sceglie la password (`create`). In una pipe resta com'è. Nella scheda, i due campi della
>   creazione passano a `autocomplete="new-password"`, così un gestore non riempie la password dell'account. Il campo
>   del ripristino resta `off`: è una password esistente ma non quella dell'account, e `current-password` proporrebbe
>   quella dell'account. Doc: `cli_tools.en.md` (riga 353).
> - **B-26.** `exportable_instance_key()` (`secure.py:35`) dà `None` anche quando
>   `len(key.encode("utf-8")) > INSTANCE_KEY_MAX_BYTES`. Anche `generated_key_unusable()` deve dire sì in quel caso,
>   altrimenti la chiave sparisce senza avviso: oggi segue solo lo stato di H, che controlla solo il minimo
>   (`_length_problem`). Importare `INSTANCE_KEY_MAX_BYTES` da `archive.py` non crea un ciclo: `archive.py` non importa
>   né `secure` né `jobs` (verificato).
> - **B-22.** Via `_plain`, `_PLAIN_AMOUNT` e `import re` se resta inutile. `compare_totals` passa il documento a
>   `ControlTotals.from_json`, il cui `ValueError` è già `absent`. Nel test
>   `test_what_is_not_plain_text_in_lines_of_objects_is_absent_before_j_reads_it` l'asserzione si capovolge: non più «J
>   non l'ha mai visto», ma «J l'ha avuto e l'ha rifiutato». Il wrapper `j_reads` continua a rifiutare il testo non
>   semplice, così nel processo di test niente si espande anche se J regredisse. Aggiornare la docstring (b) del modulo
>   e `security.md:1278`, che dice chi controlla.
> - **B-21, in opzione.** H-27 è nella HEAD: due `except` in `restore.py` più due casi API. Propongo di metterlo nello
>   stesso lotto; chiede uno slot per `api backup-restore`.
>
> **Superfici**:
>
> - di B: `instance_backup/{leftovers (nuovo), restore_jobs, jobs, secure, totals}.py`, `scripts/backup_cli.py`,
>   `BackupDownloadCard.svelte`, i test, `backup_restore.en.md`, `cli_tools.en.md`;
> - condivise:
>   - `app_lifespan.py`: `STARTUP_STEPS`, scrittore B per N66;
>   - `overview.md`, l'elenco numerato;
>   - `security.md`;
>   - il runner, un selettore nuovo `services backup-leftovers`;
>   - `CHANGELOG.md`, del coordinatore.
>
> **Conflitti previsti**: `app_lifespan.py` e `overview.md` se un altro flusso aggiunge un passo d'avvio insieme a noi
> (medio-basso); il resto basso.
>
> **Rischi**: la pulizia gira a ogni avvio di ogni installazione, quindi:
>
> - deve essere rapida e silenziosa su una cartella pulita;
> - non deve mai sollevare né seguire un link;
> - deve rispettare una CLI che gira insieme.
>
> Togliere all'avvio gli archivi scaduti da più di un'ora cambia poco il comportamento: la regola è la stessa, si
> applica prima. Va detto nel CHANGELOG.
>
> **Passi**:
>
> 1. I rossi, con tre test-author:
>    - servizi: la pulizia, `get_job`, la chiave, i totali, la fissazione dell'ordine;
>    - utilità: `--password-stdin` su un TTY, la riga di `decrypt`, la pulizia spostata;
>    - Vitest: `new-password`;
> 2. il codice;
> 3. la doc (docs-writer);
> 4. i verdi, i controlli statici, mkdocs rigoroso;
> 5. il blocco del CHANGELOG (🔒);
> 6. il checkpoint.
>
> Senza B-21 non serve uno slot: solo `services`, `utils` e Vitest.
>
> **Selettori**:
>
> - `services`: `backup-leftovers` (nuovo), `backup-jobs`, `backup-secure`, `backup-totals`, `backup-apply`,
>   `app-lifecycle`;
> - `utils`: `backup-cli-secure`, `backup-cli`;
> - Vitest: `BackupDownloadCard`;
> - mkdocs rigoroso e check-links;
> - con B-21 anche `api backup-restore`, in uno slot.
>
> **Fatto quando**:
>
> - un avvio dopo un kill non trova un archivio decifrato in `.restore/stage/`, né `.decrypt-*` più vecchie di un'ora,
>   né i file di lavoro di un job interrotto;
> - nulla si tocca sotto un lucchetto preso o attraverso un link, e il passo non solleva mai;
> - `decrypt` dice che lo zip apre le chiavi salvate, quando porta la chiave;
> - `--password-stdin` su un terminale non mostra mai la password, e i campi della creazione sono `new-password`;
> - una chiave oltre 4096 byte non si esporta, e il job avvisa con `instance_key_unusable`;
> - `totals.py` non ha più una copia della regola di J, e lo stato non cambia;
> - doc e CHANGELOG sono a posto.
>
> **Domande al coordinatore**: B-21 nello stesso lotto (propongo sì)? Il nome del passo, `backup-leftovers`? Nessuna
> domanda per il developer. 🧊 FROZEN in attesa del via.
>
> **Via (coordinatore, 03:34)**: B4b approvato com'è scritto, **B-21 dentro**, il nome `backup-leftovers` va bene.
> Prima i rossi. Lo slot breve per `api backup-restore` (B-21: il rosso, poi il verde) viene dopo il blocco della
> galleria, verso le 04:35. Il codice di B-21 resta fuori dal worktree fino al suo rosso.
>
> **Rossi in scrittura (03:40)**: il contratto congelato è in `files/b4b-test-brief.md` (§1-§7). I quattro test-author,
> ciascuno sui suoi file:
>
> - servizi: §1, cioè `test_backup_leftovers.py` (nuovo) e la fissazione in `test_backup_apply.py` (j); §4 in
>   `test_backup_secure.py`;
> - API e totali: §6 in `test_backup_restore.py`, §5 in `test_backup_totals.py`;
> - CLI: §2 e §3 in `test_backup_cli_secure.py`;
> - frontend: §3 in `BackupDownloadCard.test.ts` e `RestoreCard.test.ts`. **Fatto alle 03:47**: un caso rosso (i due
>   campi a `new-password`) e una guardia verde (`restore-password` resta `off`).
>
> Intanto:
>
> - il codice è pronto fuori dal worktree, in `files/b4b-wip/`. Lo verifica `--check`, tutti verdi sull'albero:
>   - `apply_b4b_core.py`: `leftovers.py` nuovo, `restore_jobs`, `jobs`, il passo in `app_lifespan.py`;
>   - `apply_b4b_cli.py`;
>   - `apply_b4b_misc.py`: `secure`, `totals`, la card;
>   - `apply_b4b_b21.py`, tenuto fuori fino al rosso nello slot;
> - registrato il selettore `services backup-leftovers` (`_backend_services.py`, un'aggiunta; ruff e black puliti).
>
> **Rossi eseguiti (03:47-03:50)**, uno alla volta, a carico < 50, tutti rossi per il motivo giusto:
>
> - `services backup-totals` (B-22): 19 falliti e 65 passati. Fallisce solo il test capovolto, ora
>   `…_is_refused_by_j_and_absent`: «0 documents given to J», perché `_plain` decide ancora prima di J;
> - Vitest sulle card (B-25 UI): 1 fallito e 114 passati. I due campi sono ancora a `off`; la guardia del campo del
>   ripristino è verde;
> - `utils backup-cli-secure` (B-24, B-25 CLI): 11 falliti e 47 passati:
>   - B-24: la riga 🔑 (1), e i tre casi senza riga (3): la loro precondizione vuole che un archivio con la chiave abbia
>     la riga;
>   - B-25: `--password-stdin` a un terminale (4), le sue tre risposte di rifiuto (3).
>
>   Le guardie della pipe e il caso (j) restano verdi.
>
> Due cose dai test-author:
>
> - TA-E: il difetto di oggi è peggio dell'eco. A un terminale, `create --password-stdin` legge una sola riga senza
>   conferma, e un errore di battitura sigillerebbe il backup con una password che nessuno conosce. La strada del
>   terminale chiede la password due volte;
> - TA-B: la descrizione del selettore `backup-totals` nel runner dice ancora «decided before J's from_json». La
>   correggo col codice.
>
> I rossi di B-21 (8 casi, `api backup-restore`) aspettano lo slot.
>
> **⚠️ Fuori pista: tre buchi del contratto trovati da TA-S (03:55), corretti nel lotto (revisione delle 03:58)**:
>
> 1. **`archive.zip.part`.** `decrypt_file` scrive attraverso `<nome>.part`. Una `restore` della CLI uccisa mentre
>    decifra lascia quindi un archivio in chiaro parziale, che può già contenere la chiave, e `prune` lo toglierebbe
>    solo dopo 24 h. Ora `remove_stray_decrypted_archives` toglie sia `archive.zip` sia `archive.zip.part`, solo file
>    veri;
> 2. **`remove_expired_jobs` seguiva un link.** Usava `folder.is_dir()`. Al backup seguente era innocuo, perché
>    `_prepare` passa prima da `ensure_private_dir`, che rifiuta i link. Ma ora la funzione gira da sola a ogni avvio,
>    quindi controlla `is_plain_dir` su `backups/` e su `.jobs/`. È codice di B1, ma legato al mio cambiamento;
> 3. **Un controllo chiuso all'avvio non si contava**, perché `prune` restituiva `None`: proprio il caso più importante
>    della nota di E non avrebbe lasciato traccia nel log. Ora `prune` restituisce quanti controlli ha chiuso come
>    `restore_interrupted`, e il riassunto INFO comincia con `checks_interrupted`. Tutti i chiamanti ignoravano il
>    valore restituito, e `_prune_checks` è privata.
>
> Codice aggiornato in `files/b4b-wip/` (`apply_b4b_core.py`: 15 operazioni, `--check` verde). TA-S estende i suoi test.
>
> TA-S ha trovato un altro caso: con `backups/` come link, `.jobs` nel suo bersaglio sembra una cartella vera. Il mio
> `end_interrupted_jobs` controllava già entrambi i livelli, ma il contratto lo diceva male: corretto, e aggiunto il
> caso (`test_while_backups_or_its_jobs_folder_is_a_link_no_job_is_ended`, 4 casi).
>
> **Gli ultimi rossi (04:26-04:28)**, per il motivo giusto:
>
> - `services backup-secure` (B-26): 6 falliti, 62 passati. Falliscono i casi oltre il limite: due chiavi da 4097 byte
>   (ASCII, e caratteri da due byte) in `exportable_instance_key`, in `generated_key_unusable` e nel backup sicuro. I
>   casi da 4096 byte sono verdi già oggi, di proposito: fanno da guardia all'errore di uno;
> - `services backup-apply` (N66): 1 fallito, 227 passati. La fissazione dell'ordine dà «missing from STARTUP_STEPS»;
> - `services backup-leftovers` (B-23): 44 falliti su 44:
>   - il modulo `leftovers` mancante: 26 casi;
>   - le funzioni nuove: `end_interrupted_jobs` 5, `remove_stray_decrypted_archives` 4;
>   - `prune` che restituisce `None`: 5 casi;
>   - i link: `remove_expired_jobs` toglie ancora attraverso un link, 2 casi;
>   - `get_job`, che lascia i file di lavoro: 1 caso;
>   - l'import nel lifespan: 1 caso.
>
> **Codice applicato (04:29)**: `apply_b4b_core.py` (15 operazioni più `leftovers.py`), `apply_b4b_cli.py` (6) e
> `apply_b4b_misc.py` (10). `apply_b4b_b21.py` resta fuori. Ruff e black puliti sui 7 file. Gli import non hanno cicli:
> il passo `backup-leftovers` sta subito dopo `restore-commit`, e i passi sono 23. Nel runner, la descrizione di
> `backup-totals` ora dice «refused by J's from_json» (nota di TA-B).
>
> **In corso (dalle 04:30)**:
>
> - i verdi leggeri, `files/scripts/b4b_greens.sh`: 8 selettori `services`, 3 `utils`, il Vitest delle card;
> - la doc: il docs-writer col brief `files/b4b-docs-brief.md` e la revisione delle 03:58.
>
> **Verdi leggeri (04:28-04:31), tutti verdi**:
>
> - `services`: `backup-leftovers` 44, `backup-secure` 68, `backup-apply` 228, `backup-totals` 84, `backup-jobs` 69,
>   `backup-staging` 145, `app-lifecycle` 51, `backup-secure-rules` 24;
> - `utils`: `backup-cli-secure` 58, `backup-cli` 102, `backup-cli-restore` 77;
> - Vitest delle tre card: 161;
> - `front check` (04:33): 0 errori e 0 avvisi.
>
> BACKUP-007 (`api backup`) legge un job interrotto che ha solo `state.json`: la pulizia dei file di lavoro in `get_job`
> non lo tocca. Nello slot basta quindi `api backup-restore`, più `api backup` come prova.
>
> **Slot (coordinatore, 04:35)**: è lo slot 1 dopo X (~25 minuti), poi J e MF. Circa 10 minuti:
>
> 1. `api backup-restore`, il rosso di B-21. Ricostruisce il frontend per `autocomplete`;
> 2. `apply_b4b_b21.py`;
> 3. `api backup-restore`, il verde;
> 4. `api backup`.
>
> Intanto la bozza del blocco del CHANGELOG è in `files/next-checkpoint/changelog-b4b.md`: 3 🔒 e 1 🐛. B-22 e B-21 sono
> interni, quindi senza voce.
>
> **Doc (docs-writer, 04:40)**, solo pagine inglesi, nessun timbro:
>
> - `overview.md`: 23 passi, uguali a `STARTUP_STEPS`;
> - `security.md`: dentro `#secure-backups` le righe di B-23..B-26, e la sottosezione nuova `#backup-leftovers`; il
>   paragrafo dei totali (B-22) e quello del limite di upload (B-21);
> - `backup_restore.en.md`: `#command-line`, `#secure`, `#check`, `#by-hand`, `#secure-problems`;
> - `cli_tools.en.md`: il debito di traduzione di B4 cresce nelle stesse sezioni.
>
> Le sue cinque note, decise:
>
> 1. B-21 è documentato prima del codice: il codice entra nello slot. Se lo slot salta, tolgo quelle righe;
> 2. il messaggio della CLI «the next backup after that removes it» resta vero, solo non è più l'unica via. Lasciato:
>    un test fissa quel testo;
> 3. lo stato di un job interrotto resta un'ora in più: è voluto, ed è documentato;
> 4. togliere `archive.zip` aggiorna il tempo di modifica della cartella di stage, quindi le 24 h della copia ripartono
>    una volta, a quell'avvio; gli avvii seguenti non toccano nulla. Accettato: la copia è dati in chiaro come il DB
>    vivo, nella stessa cartella privata;
> 5. `get_job()` aiuta solo i job che qualcuno segue. Il resto lo fa l'avvio, e la doc promette solo questo.
>
> **Verdi della doc (04:42-04:44)**: build rigorosa exit 0 (68 s), check-links valido, `gate-docs-links` 63.
>
> **Slot 1 (coordinatore, 04:45)**: partito con `files/scripts/b4b_slot.sh`.
>
> **Slot (04:44-04:49) ✅**:
>
> - `api backup-restore` rosso: 8 falliti, proprio i casi di B-21 (un 500 dove si aspettano 503 o un limite nullo), e
>   122 verdi. Anche il nuovo valore restituito da `prune` non rompe nulla;
> - `apply_b4b_b21.py`, 3 operazioni; ruff e black puliti;
> - `api backup-restore` verde: 130;
> - `api backup`: 23.
>
> La porta 6187 è libera alle 04:48:52, ed è stato detto al coordinatore.
>
> **Backlog**: B-21..B-26 chiusi con ✅ («Fatto il 17/10 in B4b»). B-27 resta per il lotto seguente.
>
> **Checkpoint (04:55)**: 21 file modificati e 2 nuovi, `git diff --check` pulito, porta libera. Inviato col blocco del
> CHANGELOG (`files/next-checkpoint/changelog-b4b.md`, 3 🔒 e 1 🐛). 🧊 FROZEN. Il prossimo lotto è B-27.
>
> **Approvato (coordinatore, 03:12)**: prima l'analisi, dopo l'ingresso di B4. Il passo di avvio nuovo dopo
> `restore-commit` è la sua decisione **N66**, un'estensione di N57: aggiornare `STARTUP_STEPS` e `overview.md`.
>
> **G-20, domanda di G (03:11), solo la risposta**: dopo un ripristino `committed` la scheda Backup mostra un avviso
> «ultimo ripristino: applicato il …», come `restore-last-result` per `rolled_back`?
>
> - **No.** `lastResult` vale solo per `rolled_back` (`RestoreCard.svelte:64`).
> - Il server ha già tutto. `GET /restore/status` risponde `committed` con `finished_at`, `backup_created_at`,
>   `backup_app_version` e `confirmed_by`. Lo stato resta in `restore.json` fino al ripristino confermato seguente: lo
>   toglie solo `cancel_restore`, e solo per uno in attesa.
> - **Costo**: piccolo, solo frontend, circa un'ora coi rossi:
>   - il caso nel derivato e l'avviso, in un ruolo info;
>   - una chiave i18n in 4 lingue;
>   - 2-3 casi Vitest;
>   - un E2E su uno stato finto, come FBKP-103 (dà anche la foto a G);
>   - una riga nella guida.
>
> Le domande per il developer, passate al coordinatore:
>
> 1. lo vogliamo?
> 2. per quanto: fino al ripristino seguente, come `rolled_back` (proposta), o N giorni?
> 3. il testo: data dell'applicazione, data e versione del backup, chi l'ha confermato.
>
> **Deciso (coordinatore, 03:20)**: sì, decisione notturna **N67**, che il developer rivede → **B-27**, dopo B4b.
> L'avviso resta fino al ripristino seguente, come `rolled_back`. Il testo è quello proposto, il ruolo è info, e l'E2E
> gira su uno stato finto, così dà anche la foto a G.

### B-27 — l'avviso di un ripristino riuscito: analisi (2026-10-17, 04:55-05:05) — chiuso, non da fare (P8)

> **B4b entrato (coordinatore, 04:55)**: commit `964ecf434`, `70d515552` e `b3d4a81db`; dev `c7dd3934a`; il CHANGELOG
> (3 🔒 e 1 🐛) in `8b15a6c6c`. La mia HEAD è portata in avanti a **`8b15a6c6c`**, pulita. Il via è per B-27 (N67),
> analisi prima.
>
> **Nel backlog anche B-28** (coordinatore, 04:50: la nota di E dalla revisione di B3, che lui chiamava «B-19»; quell'ID
> è già di `decrypt` da root). I trigger di un DB caricato scattano quando il controllo scrive sulla copia: l'`alembic
> upgrade`, `_post_migration_fixes` (`staging.py:550`, non la riga 464 citata) e il rekey dei segreti. Non hanno limite
> di tempo. Direzione: `set_progress_handler` o un sottoprocesso con un tempo massimo, più `trusted_schema=OFF`.
>
> **⚠️ Il conflitto, prima di tutto.** N67 contraddice una decisione esplicita del developer, **P8** (16/10, 11:25, in
> «Decisioni del developer su P7, P8 e P12»): «**successo senza messaggio** ("se ha funzionato lo vedi"): la pagina va
> dritta al login, poi alla solita pagina iniziale; la scheda non mostra "ripristino applicato"». Lo dice anche il codice,
> `RestoreCard.svelte:63`: «Developer decision P8: a restore kept says nothing (the data shows it); one rolled back says
> why». Nella mia risposta a G-20 (03:12) ho scritto solo «oggi non c'è», senza dire che il silenzio era una scelta del
> developer. **Errore mio**: il coordinatore ha deciso N67 senza quell'informazione. È una domanda che solo il developer
> può decidere, quindi, con la regola della notte, va nel piano e al coordinatore, e si passa ad altro. Propongo di
> fermare B-27 finché il developer non sceglie fra P8 e N67.
>
> **L'analisi, pronta se il developer conferma N67**:
>
> - Stato reale:
>   - `lastResult` vale solo per `rolled_back` (`RestoreCard.svelte:64`). L'avviso usa `restore-last-result`,
>     `data-result`, `data-reason`, il ruolo warning e `TriangleAlert`;
>   - il server ha già tutto. Uno stato `committed` porta sempre `finished_at`, `confirmed_by` (il nome dell'admin, o
>     `cli`), `backup_created_at` e `backup_app_version`: in `RestoreState` non sono opzionali. Lo stato resta fino al
>     ripristino confermato seguente;
>   - il ruolo info esiste (`bg-lf-info-soft`, `border-lf-info-line`, `text-lf-info-on-soft`).
> - Superfici, tutte di B:
>   - `RestoreCard.svelte`: il derivato per `committed`; lo stesso `restore-last-result` con `data-result="committed"`,
>     il ruolo info, un'icona (`History` o `CircleCheck`); e il commento P8 aggiornato;
>   - i18n `backup/{en,it,fr,es}.json`: due chiavi, `backup.restore.last.committed` («applied on {date}, backup of
>     {backupDate} (LibreFolio {version}), confirmed by {user}») e `committedCli` («… confirmed from the command line»).
>     Niente `select` ICU, per il controllo dei segnaposto;
>   - i test: `RestoreCard.test.ts` (l'avviso con i quattro valori; `cli`; niente avviso per `none`, `pending` o fuori da
>     `idle`), `restoreI18n.test.ts` (le chiavi in 4 lingue), e FBKP-110 in `backup.spec.ts` su uno stato finto come
>     FBKP-103, che dà anche la foto a G;
>   - la doc: `backup_restore.en.md` (`#restore-settings`) ed eventualmente la pagina sviluppatore della scheda.
> - Costo: circa un'ora coi rossi. Uno slot E2E breve per FBKP-110.
>
> **Mentre B-27 aspetta**, propongo l'analisi di B-28: un indurimento di sicurezza del controllo, «dopo B4», e B4 è
> entrato. In alternativa un lotto minimo con B-19 (`decrypt` da root) e B-20 (knip).
>
> **Deciso (coordinatore, 05:00)**: N67 ritirato, **P8 resta**. B-27 è chiuso come «non da fare, P8» (nel backlog con
> ✅ e la nota) e va nell'elenco del developer solo come nota. Si procede con (a), l'analisi di B-28.

### B-28 — i trigger del DB caricato durante il controllo (2026-10-17, 05:00-05:50) ✅ — entrato in dev `01f36e79d`

> Sola lettura, HEAD `8b15a6c6c` pulita.
>
> **Stato reale**:
>
> - L'`alembic upgrade` della copia gira già **in un processo a sé, con un tempo massimo** (`_upgrade`,
>   `UPGRADE_TIMEOUT_SECONDS` = 3600). Su questa strada la nota di E è già coperta.
> - Nel processo del server girano invece:
>   - le correzioni post-migrazione, `run_post_migration_fixes`. È codice condiviso (`backend/app/db/post_migration/`)
>     e apre una sua connessione `sqlite3`;
>   - il rekey dei segreti, `_plugin_secrets` (`sqlite3`);
>   - `_administrators`;
>   - i totali, `ledger_totals_of`, con aiosqlite e SQLAlchemy;
>   - `describe_database`, in sola lettura, sulle sole `type = 'table'`.
>
>   Le scritture fanno scattare i trigger del DB caricato; una vista con lo stesso nome di una tabella dell'app
>   girerebbe a ogni lettura per nome.
> - **Lo schema di LibreFolio non ha né trigger, né viste, né tabelle virtuali.** Lo dice un grep di `backend/alembic`
>   e `backend/app` per `CREATE TRIGGER` e `CREATE VIEW`. In SQLite solo trigger e viste possono contenere una query
>   qualsiasi, cioè una CTE ricorsiva: CHECK, DEFAULT, colonne generate e indici su espressioni non ammettono
>   sottoquery. Le tabelle virtuali eseguono il codice del loro modulo.
>
> **Due strade**:
>
> - **(A), la direzione di E alla lettera**: un tempo massimo su ogni connessione alla copia nel processo del server
>   (`set_progress_handler`, oppure le correzioni in un sottoprocesso come alembic), più `trusted_schema=OFF`. Bisogna
>   agganciarsi a quattro tipi di connessione, una delle quali nel codice condiviso delle correzioni. Il codice ostile
>   gira comunque fino al limite, e dopo un ripristino i trigger stranieri resterebbero nel DB vivo: girerebbero a ogni
>   scrittura del server, e al primo avvio delle correzioni.
> - **(B), la causa (la mia proposta)**: subito dopo lo spacchettamento, e prima di ogni altro accesso, il controllo
>   legge `sqlite_master` in sola lettura, dove nessun codice dell'utente gira. Se il DB ha anche un solo trigger, una
>   vista o una tabella virtuale (`CREATE VIRTUAL TABLE`), l'archivio si rifiuta con un codice nuovo,
>   `database_foreign_objects`: un backup di LibreFolio non li ha mai. Questo copre il controllo, la CLI (`inspect` non
>   apre il DB; `restore` e `--dry-run` passano dallo stesso staging) e quello che un ripristino porterebbe nel server.
>   Un test di guardia fissa che lo schema all'ultima revisione non ha oggetti di quei tipi: se una migrazione futura ne
>   aggiunge uno, il test lo dice e la lista dei permessi si aggiorna. In più, `trusted_schema=OFF` sulle connessioni di
>   B alla copia, una riga ciascuna, come difesa in più. Non serve un tempo massimo: senza trigger e viste non resta
>   codice che possa girare all'infinito.
>
> **Superfici di (B)**:
>
> - `staging.py`, una funzione e la sua chiamata prima di `describe_database`;
> - il `Literal` dei codici di errore in `schemas/backup.py`, poi `api sync`;
> - `restoreText.ts`, e la chiave i18n `backup.restore.errors.database_foreign_objects` in 4 lingue;
> - la doc: le tabelle dei problemi in `backup_restore.en.md` e `cli_tools.en.md`, e `security.md`;
> - i test:
>   - `services backup-staging`: un trigger, una vista, una tabella virtuale, ciascuno rifiutato senza che nulla giri;
>     un DB vero passa; la guardia dello schema alla testa;
>   - il test «prodotti = dichiarati» dei codici;
>   - `restoreI18n`.
>
> **Costo**: piccolo-medio. Rischio basso: nessun backup vero ha quegli oggetti. Conflitti: nessuno, i file sono di B
> più `api sync`. Se il test «prodotti = dichiarati» è nella categoria `api`, serve uno slot breve.
>
> **Domande al coordinatore**: (A) o (B)? Propongo (B) più `trusted_schema=OFF`. E il nome del codice,
> `database_foreign_objects`.
>
> **Via (coordinatore, 05:20)**: **(B) più `trusted_schema=OFF`**; il codice `database_foreign_objects` va bene
> («meglio la causa di un tempo massimo»). Prima i rossi, poi uno slot breve per `api backup-restore` quando sono
> pronto.
>
> **Rossi in scrittura (05:25)**: il contratto congelato è in `files/b28-test-brief.md`. TA-S scrive in
> `test_backup_staging.py` (§4), TA-F in `restoreI18n.test.ts`. Il codice è pronto fuori dal worktree:
> `files/b28-wip/apply_b28.py`, 13 operazioni, `--check` verde:
>
> - `staging.py`: la classificazione per testo SQL (`_leading_words`, `_schema_object_kind`) e
>   `_refuse_foreign_objects`, chiamata prima di `describe_database`; `trusted_schema=OFF` su `_plugin_secrets` e
>   `_administrators`;
> - `snapshot.py` e `totals.py`: `trusted_schema=OFF`;
> - il codice nello schema, in `restoreText.ts` e nei quattro cataloghi, inserito come testo per non toccare la
>   formattazione dei JSON.
>
> **⚠️ Fuori pista, verificato su SQLite 3.54.0 (05:28)**: una riga di `sqlite_master` travestita (un trigger con
> `type` table, index o view, qualunque rootpage) fa rifiutare a SQLite tutto lo schema, «malformed database schema».
> Un trigger si carica solo con `type = 'trigger'`. Il caso del contratto quindi si aspetta `database_damaged`
> (revisione delle 05:30), sempre rifiutato prima di ogni altro accesso. La lettura per testo SQL resta: non costa nulla
> e non dipende da questa verifica di SQLite. Prova fatta su un DB di prova in `/tmp`, poi tolto.
>
> **Rossi scritti**:
>
> - TA-F, `restoreI18n.test.ts`: due casi. La chiave nei 4 cataloghi, e il codice nella lista scritta a mano
>   `CODE_LISTS`, perché quella lista non deriva dal client generato. Il rosso è stato eseguito alle 05:03: 2 falliti e
>   121 passati;
> - TA-S, `test_backup_staging.py`, nuova sezione (l), 6 test e 15 casi:
>   - i cinque oggetti stranieri rifiutati prima che `describe_database` sia chiamata;
>   - il WARNING senza nomi né SQL (un marcatore `b28_untrusted` in ogni nome);
>   - lo schema che SQLite rifiuta, cioè la riga travestita e la riga che non si analizza, dà `database_damaged`;
>   - la guardia dello schema alla testa;
>   - `trusted_schema=OFF` per primo su ognuna delle 5 connessioni;
>   - la prima connessione sulla copia è la lettura in sola lettura di §1.
>
> **⚠️ Fuori pista, da TA-S**:
>
> - un test esistente si sarebbe rotto: `test_an_upgrade_that_fails_in_alembic_is_refused_and_leaves_nothing` fa
>   fallire alembic con un trigger su `alembic_version`, e dopo B-28 quell'archivio si rifiuterebbe prima. Riscritto
>   ora con il meccanismo di TA-S: una tabella che una migrazione in sospeso crea esiste già, e `op.create_table`
>   fallisce. Una precondizione prova che l'archivio non ha oggetti stranieri;
> - con `PRAGMA writable_schema=ON` SQLite carica comunque un trigger travestito, e `VACUUM` lo accende internamente.
>   Nessun codice di LibreFolio lo usa sulle connessioni del controllo;
> - il testo d'errore di SQLite nomina la riga, ed è testo dell'archivio. Il mio codice usa un messaggio fisso e non
>   registra l'eccezione.
>
> **Il rosso (05:34)**: `services backup-staging` dà 15 falliti, proprio i casi nuovi, e 145 passati, compreso il test
> riscritto. Per farlo fallire TA-S ha usato un indice, non una tabella: 007 salta le tabelle che esistono già, ma un
> indice chiamato `plugin_system_settings` fa fallire il suo `op.create_table`.
>
> **Codice applicato (05:35)**: `apply_b28.py`, 13 operazioni. Ruff e black puliti; `api sync` (il client generato ha
> il codice); `i18n build` e `i18n check`, 4968 chiavi, rigoroso. La descrizione del selettore `backup-staging` nomina
> B-28.
>
> **Verdi leggeri (05:36-05:40)**:
>
> - `services`: `backup-staging` 160, `backup-secure` 68, `backup-totals` 84, `backup-apply` 228;
> - `utils`: `backup-cli-restore` 77, `backup-cli-secure` 58;
> - Vitest: `restoreI18n`, `backupApi`, `restoreFlow` e `RestoreCard`, 573 in tutto;
> - `front check`: 0 errori e 0 avvisi.
>
> **In corso**: la doc (docs-writer); lo slot breve chiesto al coordinatore (05:41) per `api backup-restore` (il test
> «prodotti = dichiarati») e `api backup-restore-apply`.
>
> **Slot 2 (05:41-05:46) ✅**: `api backup-restore` 130 e `api backup-restore-apply` 136. Porta libera.
>
> **Doc (docs-writer, 05:45)**:
>
> - `backup_restore.en.md`, `#check-refused`: una riga per `database_foreign_objects`, e anche quella di
>   `database_damaged`, che mancava;
> - `cli_tools.en.md`: la tabella dei codici e una frase nella prova su copia;
> - `security.md`: la sottosezione nuova `#backup-restore-foreign-objects`.
>
> **⚠️ Fuori pista**: il docs-writer ha notato «holds 1 triggers»: il messaggio del rifiuto aveva un conteggio al
> plurale. Ora il messaggio è senza numero, che resta nel log. Nessun test fissava quel testo; corretta anche la
> citazione in `security.md`. Poi `services backup-staging` 160.
>
> **Verdi della doc (05:46-05:48)**: build rigorosa exit 0, check-links valido, `gate-docs-links` 63.
>
> **Backlog**: B-28 chiuso con ✅. **Checkpoint (05:50)**, col blocco del CHANGELOG. 🧊 FROZEN.

### B-29 — un totale della copia che J non rilegge (2026-10-17, 05:50-06:10) ✅ — 🧊 FROZEN, checkpoint pronto

> **B-28 entrato (coordinatore, 05:49)**: commit `9403ecda0`, `fe1183750` e `910e185b6`; dev `01f36e79d`; il CHANGELOG
> 🔒 in `1c2bac918`. HEAD portata in avanti a **`1c2bac918`**, pulita. Il via è per **B-29**: prima il rosso, poi
> `current` letto dentro un `try` che risponde `unreadable`, con run leggeri nella corsia. Poi **B-16** (l'overlay che
> aspetta per sempre dopo «Restore and restart»), salvo una decisione del developer, altrimenti **B-9**. Un checkpoint
> per lotto.
>
> **Il difetto** (E, R13-SEC2; nel backlog come B-29): in `compare_totals`, `ControlTotals.from_json(current)` sta fuori
> dal `try`. `to_json` di J scrive testo semplice: un importo esatto ma enorme, come 1E+70, diventa 71 cifre, oltre le
> 60 che `from_json` accetta (J-27). Il `ValueError` esce, e il controllo finisce `stage_failed`.
>
> **Il contratto** (al test-author TA-B, 05:52):
>
> - `current` rifiutato da J → `unreadable`, senza differenze, conteggio 0, nessuna eccezione;
> - un WARNING «The control totals of the copy cannot be read: they are not compared», senza valori;
> - l'ordine delle decisioni resta: assente → `absent`; `other_version`; registrato rifiutato da J → `absent`; `current`
>   None → `unreadable`; **`current` rifiutato da J → `unreadable`** (nuovo); poi `same` o `changed`.
>
> I test vanno in `test_backup_totals.py`. Facoltativo, se semplice: un caso di staging con un registro che J scrive
> oltre 60 cifre.
>
> **Rossi (TA-B, 05:58)**:
>
> - `test_backup_totals.py`: 4 casi di `current` rifiutato da J (61 cifre, un esponente, una riga che non è un oggetto,
>   una riga senza importo), più una riga in `DECISIONS`; più due guardie che `absent` vince;
> - `test_backup_staging.py`: il caso facoltativo, un registro con una quantità esatta 1e70 che J scrive in 71 cifre.
>
> Eseguiti alle 06:00: totali 5 falliti e 86 passati, staging 1 fallito e 160 passati.
>
> **Gravità, da TA-B**: il crollo richiedeva totali registrati che J legge accanto a una copia che J non rilegge, cioè
> un manifesto riscritto. Il manifesto non è nella sua lista di checksum, e un backup vero registra la stessa riga: lì
> vince `absent`. La sorgente realistica è `transactions.quantity` (`RealDecimal`, rilegge esatto un double) di un DB
> 1.2 o modificato a mano.
>
> **Codice (06:02)**: `apply_b29.py`; ruff e black puliti. **Verdi**: `backup-totals` 91, `backup-staging` 161,
> `backup-apply` 228.
>
> **Doc (06:05)**: una frase in `security.md`, nel paragrafo dei totali (la copia passa dallo stesso lettore, e diventa
> `unreadable`). In `backup_restore.en.md` gli esiti elencano già «unreadable». Build rigorosa exit 0, check-links
> valido, `gate-docs-links` 63.
>
> **Backlog**: B-29 chiuso con ✅. **Checkpoint (06:10)**. 🧊 FROZEN. Il prossimo è B-16, con l'analisi prima.

### B-16 — l'overlay che aspetta per sempre (2026-10-17, 06:10-06:35) ✅ — 🧊 FROZEN, checkpoint pronto

> **B-29 entrato (coordinatore, 06:09)**: il fix è `c96861834`; dev `006773c99`; nessuna riga nel CHANGELOG. HEAD
> portata in avanti a **`abf8391fb`**, pulita. Via all'analisi di B-16.
>
> **Stato reale** (`restoreFlow.svelte.ts`, `RestartOverlay.svelte`):
>
> - dopo «Restore and restart» le sonde girano ogni `pollMs`;
> - con il server sempre su, l'esito si legge dopo `fastRestartMs` (30 s). Se lo stato è ancora `pending`, `#settle`
>   risponde «non ancora» a ogni sonda, all'infinito;
> - `slow` scatta solo col server **giù** da `slowAfterMs` (60 s), e l'overlay mostra `restart-slow` («has not come
>   back yet»);
> - con il server che non scende mai, l'overlay dice «LibreFolio is restarting» per sempre, senza un suggerimento e
>   senza un modo di uscire, se non ricaricare la pagina. Il pulsante `restart-back` («Back to Backup», che chiama
>   `controller.load()`) c'è solo negli esiti falliti.
> - Il test fissato «up all along, the restore still pending at the fast read: keep waiting and probing»
>   (`restoreFlow.test.ts:1754`) chiede solo `waiting` e le sonde che continuano: un segnale in più lo estende, non lo
>   cambia.
>
> **La decisione da prendere** (sul comportamento; P8 non la tocca: è un fallimento, che P8 vuole sulla stessa
> schermata e col motivo):
>
> - **(A)** solo un suggerimento: un flag `notStopping`, vero se il server non è mai sceso e lo stato è ancora
>   `pending` oltre `slowAfterMs` dalla richiesta di riavvio. L'overlay mostra un avviso (`restart-not-stopped`): «LibreFolio
>   has not stopped. If it does not restart by itself, restart it yourself: the restore is applied at that start.» Le
>   sonde continuano, e quando il server scende e risale tutto va come oggi;
> - **(B)**, la mia proposta: (A) più `restart-back` in quello stato. «Back to Backup» porta alla scheda col ripristino
>   in attesa, dove ci sono già «Restart now» e «Cancel the restore»: una via d'uscita senza ricaricare. Le sonde si
>   fermano solo quando si preme;
> - **(C)** chiudere come `still_pending` (un motivo nuovo, `not_stopped`) e smettere di sondare. Cambia il test fissato,
>   e perde un arresto lento che arriva dopo.
>
> **Superfici (B)**, tutte di B:
>
> - `restoreFlow.svelte.ts`: il flag, azzerato da `load()` e dal server visto giù;
> - `RestartOverlay.svelte`: l'avviso, `data-not-stopping`, il pulsante;
> - `RestoreCard.svelte`, per passare il flag;
> - una chiave i18n in 4 lingue;
> - i test: Vitest su `restoreFlow` (flag, sonde, back) e su `RestartOverlay` (avviso e pulsante);
> - la guida: la riga dei problemi «resta su "is restarting"» (oggi «riavvialo a mano»), che ora la pagina dice da sé.
>
> Niente E2E (servirebbe l'orologio finto di Playwright per 60 s): bastano i Vitest con i timer finti. Quindi niente
> slot. Costo piccolo.
>
> **Decisione (coordinatore, 06:11)**: **(B)**, col mio testo per l'avviso. Le sonde continuano finché non si preme il
> pulsante, e un arresto tardivo procede come oggi. Si usano i ruoli e il pulsante che esistono già: nessuna classe di
> colore nuova, e `theme-roles --check` deve restare pulito. Prima i rossi (Vitest coi timer finti), solo run leggeri,
> poi il checkpoint. Nel CHANGELOG una riga 🐛 breve.
>
> **Rossi in scrittura (06:15)**: il contratto congelato è in `files/b16-test-brief.md`; TA-F scrive §4.
>
> Il codice è pronto fuori dal worktree: `files/b16-wip/apply_b16.py`, 19 operazioni, `--check` verde.
>
> - Il flag `notStopping` si azzera dove si azzera `slow`: `load()`, `#restart` e ogni esito di `#settle`. Si azzera
>   anche quando una sonda trova il server giù.
> - Diventa vero solo in fondo al ramo «su» di `#probe`, quando l'attesa continua: il server mai visto giù, e
>   `slowAfterMs` passato dalla richiesta.
> - Nell'overlay, l'avviso è copiato da `restart-slow` (stessi ruoli warning) e il pulsante è identico a quello degli
>   esiti falliti. Nessuna classe nuova.
> - La chiave i18n è in 4 lingue, nel tono dell'avviso `slow` di ciascuna.
>
> **Rossi (TA-F, 06:17; eseguiti alle 06:19)**:
>
> - `restoreFlow.test.ts`: 9 test e 12 casi, coi tempi del file: sonda ogni 200 ms, lettura veloce da 3 s,
>   `slowAfterMs` 6 s;
> - `RestartOverlay.test.ts`: 5 test;
> - `RestoreCard.test.ts`: 1 test, che passa dal vero controller con l'API finta;
> - `restoreI18n.test.ts`: 1 test.
>
> Esito: 18 falliti e 336 passati, più 1 fallito e 53 passati sulla card. Il caso fissato è intatto.
>
> **⚠️ Fuori pista, da TA-F**: se `slowAfterMs` fosse minore di `fastRestartMs` (non con i valori di default), la mia
> condizione accenderebbe l'avviso prima di aver letto un esito. Corretta prima di applicare: `fast && …` (la lettura
> veloce c'è stata, e il server non è mai sceso). Il conteggio parte dalla risposta che accetta il riavvio, non
> dall'invio: lo dice anche la nota del backlog.
>
> **Codice (06:21)**: `apply_b16.py`, 19 operazioni. Prettier pulito; `i18n build` e `i18n check` (4971 chiavi,
> rigoroso); `theme-roles --check` pulito.
>
> **Verdi (06:22-06:26)**: Vitest 354 sui tre file e 54 sulla card; gate dei colori 215; `front check` 0 errori e 0
> avvisi.
>
> **Doc (06:27)**: in `backup_restore.en.md` il punto «It takes long» e la riga dei problemi ora citano l'avviso nuovo e
> **Back to Backup** (che porta a **Restart now and restore** e **Cancel the restore**). Build rigorosa exit 0,
> check-links valido, `gate-docs-links` 63.
>
> **Backlog**: B-16 chiuso con ✅. Aggiunti gli SHA ai chiusi di oggi: B-21..B-26 `964ecf434`, B-28 `9403ecda0`, B-29
> `c96861834`.

### B-9 — il token del pannello fra i controlli della configurazione (2026-10-17, 06:35-07:36) — ✅ entrato in dev `997dc7ecf`

> **B-16 entrato (coordinatore, 06:33)**: dev `3896cb6b3`, il CHANGELOG 🐛 in `47405701f`. HEAD portata in avanti a
> **`47405701f`**, pulita. Via all'analisi di B-9.
>
> Due note di A:
>
> - percorsi vecchi nei commenti di `BackupTab.svelte:2` e di `instance_backup/apply.py:3`. Ho letto le due intestazioni:
>   ogni percorso citato esiste (`./BackupDownloadCard.svelte`, `./RestoreCard.svelte`, `app_lifespan.py`, `dev.py`,
>   `outcome.py`; gli altri sono file della cartella dei dati). Serve la stringa esatta di A;
> - A8b toccherà più avanti anche `admin/backup_restore.en.md`: ci sarà un piccolo merge.
>
> **Stato reale**:
>
> - `backup_download_token()` (`config/backup.py`) solleva `BackupConfigError`
>   (`BACKUP_DOWNLOAD_TOKEN_NOT_VISIBLE_ASCII`, `BACKUP_DOWNLOAD_TOKEN_TOO_SHORT`) o `SecretFileError` (un `_FILE`
>   illeggibile), e restituisce `None` se non è impostato: allora le rotte del pannello sono spente. Un token
>   inutilizzabile si vede solo alla prima richiesta del pannello: 503 `backup_panel_unavailable` più una riga d'errore;
> - `backup_max_upload_mb()` ha lo stesso punto cieco: `BACKUP_MAX_UPLOAD_MB_INVALID`, o `ProfileDefaultError` (H-27),
>   si vede solo al primo upload (503) o alla lettura dello stato (B-21);
> - `config_audit.CONFIG_CHECKS` (file di H) contiene i controlli della piattaforma più `*EMAIL_CONFIG_CHECKS` (il modulo
>   di E, `services/email/checks.py`). All'avvio `log_configuration_audit()` registra ogni controllo che non è `ok`. Solo
>   `GET /email/status` mostra i controlli di E. Le chiavi `instance.checks.*` di H esistono nei 4 cataloghi per la
>   futura scheda «Sicurezza», e nessuna pagina le usa ancora;
> - `test_config_audit.py` (di H) fissa `CHECK_IDS`, una voce per ogni controllo.
>
> **Proposta**:
>
> - un modulo nuovo di B, `instance_backup/checks.py`, sul modello di quello di E: legge la configurazione, non cambia
>   nulla, non solleva mai, non mette mai un valore nel risultato, e importa in modo pigro;
>   - `check_panel_token()` (`backup.panel_token`): non impostato → `info` (le rotte del pannello sono spente); usabile →
>     `ok`; inutilizzabile → `error`, col solo motivo (`notVisibleAscii`; `tooShort` con `minimum`; `unreadable` per il
>     `_FILE`). Mai il token né il contenuto del file;
>   - `check_upload_limit()` (`backup.upload_limit`), **in più rispetto al testo di B-9**, perché ha lo stesso punto
>     cieco: un valore non valido o un errore della tabella dei profili → `error`; altrimenti `ok`, col limite in `detail`
>     (0 vuol dire nessun limite);
>   - `BACKUP_CONFIG_CHECKS = (check_panel_token, check_upload_limit)`;
> - in `config_audit.CONFIG_CHECKS`, una riga `*BACKUP_CONFIG_CHECKS` (file di H); in `test_config_audit.py`, le due voci
>   di `CHECK_IDS` (file di H). Scrivo io, H rivede;
> - le chiavi `backup.checks.*` nei 4 cataloghi di `backup/`, come quelle di H: nessuna pagina le usa finché non arriva
>   la scheda;
> - il comportamento non cambia, salvo il log: un token o un limite inutilizzabile dà un ERROR già all'avvio, e la
>   partenza non si ferma. Il self-hosted resta com'è;
> - test: un file nuovo, `test_services/test_backup_checks.py` (selettore `services backup-checks`), più `services
>   config-audit`. Solo run leggeri, niente slot;
> - doc: `hosting_providers.en.md` (il token del pannello) e i controlli d'avvio in `configuration.en.md`, se li elenca.
>
> **Costo**: piccolo.
>
> **Domande**:
>
> 1. includo anche il controllo del limite di upload? Propongo sì;
> 2. scrivo io la riga in `config_audit.py` e le voci nel test di H, con H che rivede?
> 3. la stringa esatta della nota di A.
>
> **Via (coordinatore, 06:36)**:
>
> 1. sì anche al controllo del limite di upload. È coerente con H-37: un `ProfileDefaultError` dà `error`;
> 2. sì: scrivo io la riga `*BACKUP_CONFIG_CHECKS` in `config_audit.py` e le 2 voci di `CHECK_IDS`, e H rivede. H ora
>    non tocca quei due file. Però H-37 scrive `developer/architecture/security.md`, quindi se mi serve lo dico prima. A8a
>    ha righe sue in `config_audit.py`: io aggiungo soltanto, e sto lontano dal blocco `ACCOUNTS_CONFIG_CHECKS`;
> 3. la nota di A riguarda il **percorso nella UI** («Settings › Backup», `BackupTab.svelte:2`), che A8b sposta nel
>    gruppo Administration: va allineato **dopo l'ingresso di A8b**, come per E. Ora niente.
>
> Quando entra la scheda «Sicurezza» (A8b), controllare con A che mostri i miei id.
>
> **Contratto congelato (06:40)** nei file della sessione (`b9-test-brief.md`): le due tabelle di stato, la riga in
> `config_audit.py`, le chiavi `backup.checks.*`, i test (file nuovo `test_backup_checks.py`, le 2 voci di `CHECK_IDS`,
> le chiavi nei 4 cataloghi). test-author (TA-B) scrive i rossi; il codice è pronto in uno script di patch
> (`b9-wip/apply_b9.py`, modulo in `b9-wip/checks.py`), provato a secco e pulito per ruff e black.
>
> **⚠️ Fuori pista — revisione del contratto (06:42)**: un token **non impostato** è `ok` (chiave
> `backup.checks.panelToken.off`), non più `info` come proponeva l'analisi. Motivo: i test di H in
> `test_config_audit.py` vogliono ogni controllo `ok` su una configurazione predefinita
> (`test_startup_logs_nothing_when_every_check_is_ok`, e i test della chiave d'istanza e del blocco con
> `logged == []`); con `info` ogni avvio self-hosted avrebbe una riga in più nel log, contro «il self-hosted resta com'è»
> dell'analisi. È anche il precedente di E (`email.checks.smtp.off` è `ok`). TA-B avvisato mentre scriveva.
>
> **Coordinatore (06:43)**: d'accordo su `ok` per il token non impostato. `developer/architecture/security.md`
> (scritto ora da H-37): **aspettare l'ingresso di H-37**. Intanto codice, test e doc admin; quando H-37 entra, il
> coordinatore aggiorna la mia base e aggiungo (a) il paragrafo su `instance_backup/checks.py` nella sezione del backup e
> (b) la clausola «`backup.checks.*` per quelli di B» nella riga `i18n_key` della tabella di H, **nello stesso lotto
> B-9**, non dopo.
>
> **H-37 entrato (06:47)**: dev `b37e926af`. Due note di H da includere in B-9:
>
> 1. in `test_backup_restore.py`, blocco (e), le etichette «B-21, RED until the routes catch it» sono vecchie;
> 2. la docstring di `backup_max_upload_mb()` («else `0`, the self-hosted default») vale ora solo per `selfhosted`: con
>    un altro profilo, una voce mancante → `ProfileDefaultError`.
>
> HEAD era antenata di `b37e926af`, e i miei 5 file sporchi non erano toccati da `47405701f..b37e926af`. Ho chiesto un
> fast-forward subito: il selettore in `_backend_services.py`, la nota 1, la riga del backlog e `security.md` cadono
> tutti in file cambiati in dev. **Coordinatore (06:51)**: ff a **`c8ea9ddd4`** (oltre `b37e926af`: MF SEC7-2 e il
> changelog); file sporchi intatti; B-9 resta un commit solo. Approvata anche la correzione di `configuration.en.md`
> l.202-204: «work the same way» dopo «the server stops at startup» fa credere che ogni `_FILE` elencato fermi l'avvio
> (trovata dal docs-writer).
>
> - ✅ **Rossi, giro 1** (TA-B, 06:49): `test_backup_checks.py`, 54 istanze; nel file di H le 2 voci di `CHECK_IDS`
>   dietro un import protetto, che tollera solo l'assenza del modulo. Oggi: 48 errori al setup (il modulo manca), 2
>   fallimenti (interprete nuovo), 4 fallimenti (chiavi nei cataloghi), 1 fallimento nel file di H (`set(CONFIG_CHECKS)`
>   ≠ `set(CHECK_IDS)`).
> - **⚠️ Fuori pista — ordine in `CONFIG_CHECKS`**: TA-B ha trovato che «dopo `*EMAIL_CONFIG_CHECKS`» (§2 del contratto)
>   rompe EMK-010, EMK-011 ×5 ed EMK-012 ×4 di E, che fissano «`CONFIG_CHECKS` finisce coi tre controlli dell'email»; lo
>   dice anche la doc di E (`email.md`: «closes the platform's `CONFIG_CHECKS`»). Decisione mia (posizione scelta da me
>   nel contratto): `*BACKUP_CONFIG_CHECKS` va **prima** di quelli di E, dopo `check_log_level`. Nessuna modifica ai file
>   di E; il test di registrazione dice «prima», non «subito prima», così A8a può aggiungere le sue righe in mezzo.
> - **H-37 nel controllo del limite**: `ProfileDefaultError` ora vuol dire anche una voce mancante, quindi il riassunto
>   e i testi `profileTable` dicono «missing or of the wrong type» / «nessun valore, o uno del tipo sbagliato».
>   Nuovi casi chiesti a TA-B: managed con la voce tolta → `profileTable`; selfhosted con la stessa voce tolta → `ok`.
> - **`_configure` di H**: ha un blocco «Workstream E» che toglie `LIBREFOLIO_SMTP_*`, così i controlli di E sono `ok`.
>   Con B-9 i test di H «tutto ok» dipendono anche dal token e dal limite (un valore nel `.env` o nella shell
>   entrerebbe): chiesto a TA-B un blocco «Workstream B» uguale. Da far rivedere a H.
> - ✅ **Doc admin, giro 1** (docs-writer, 06:46): `configuration.en.md` (righe Main Options, «Secrets in Files», due
>   righe in «Startup Checks») e `hosting_providers.en.md` (token, riga 503, limite). Il link da `hosting_providers` a
>   `configuration.md` è senza ancora: `#startup-checks` esiste solo nella pagina inglese (la lezione di B4).
> - **Giro 2** (in corso): TA-B: l'ordine, gli orari, i casi H-37, il blocco in `_configure`, e le etichette «RED until»
>   vecchie di `test_backup_restore.py` (blocco (e) e anche (f): `api backup-restore` 130/130 verde nello slot di B-28).
>   docs-writer: le righe spostate prima dell'email, l.202-204, e `security.md` (a) sezione nuova
>   `#backup-config-checks` in fondo a «Secure Backups», (b) la clausola `i18n_key` più una frase dopo la tabella
>   dell'ordine, (c) il paragrafo «never at startup» del token in «Secrets from Files», che B-9 rende falso, (d) una
>   clausola nelle righe di H-37 su `upload_limit_mb`.
> - **Codice pronto** in `b9-wip/apply_b9.py`, provato a secco su `c8ea9ddd4`: `checks.py`; in `config_audit.py`
>   l'import in ordine ruff (dopo `client_address`) e la riga prima del commento di E; la docstring di
>   `backup_max_upload_mb()` (nota 2 di H); le chiavi nei 4 cataloghi. Il selettore è in `b9-wip/apply_runner.py`.
> - ✅ **Giro 2 dei test** (TA-B): 57 istanze. Il test di registrazione dice «prima dei controlli dell'email»; gli
>   orari corretti in 06:42; i casi H-37 (voce managed tolta → `profileTable`; selfhosted con la stessa voce tolta →
>   `unlimited`; uno anche nell'audit d'avvio). Nel file di H, il blocco «Workstream B» in `_configure`. In
>   `test_backup_restore.py` le etichette «RED until» riscritte, solo docstring, commenti e banner: (e) B-21 e H-37,
>   (f) «fixed since» (TA-B ha verificato ogni correzione nel codice). Le due frasi «lot B-13 is not written yet» nei
>   messaggi di due assert le ho corrette io: solo il testo del messaggio.
>   TA-B ha anche notato che il test (f) di H fissa `session_cookie → client_address → log_level` adiacenti: la riga di
>   B va proprio dopo `check_log_level`.
> - **⚠️ Fuori pista — il 507 alla creazione**: TA-B scriveva che il vecchio suggerimento «507 a disco pieno mentre si
>   crea il file di upload» non è mai entrato. Verificato: non è così. `os.open` e la scrittura riconoscono già
>   `ENOSPC` (`_out_of_space` → `UploadNoSpaceError` → 507, `restore_jobs.py` l.153-157 e l.170-173). Resta solo
>   la creazione della cartella degli upload (`ensure_private_dir`, l.145, fuori da quel `try`) → 500. Annotato come
>   **B-30** (minimo) nel backlog.
> - **Coordinatore**: sì alla clausola in `developer/architecture/settings.md` l.68-70 (file di H; H la rivede, e non
>   tocca `settings.md`, `security.md`, `config_audit.py` né `test_config_audit.py` fino al mio ingresso). OK anche
>   alle altre scelte. Scritta: «never as a startup check of their own … The backup's startup checks call the upload
>   limit's reader, and only log its error».
> - ✅ **Rossi** (07:02-07:03, corsia 6187, carico ~26):
>   - `services backup-checks`: 6 falliti e 51 errori, nessun passato. 102 righe «does not exist: lot B-9 is not
>     written yet», 53 `ModuleNotFoundError` del modulo, e le 9 chiavi mancanti in ognuno dei 4 cataloghi;
>   - `services config-audit`: 1 fallito (`test_run_config_checks_evaluates_every_check_in_order_and_changes_nothing`,
>     `set(CONFIG_CHECKS) != set(CHECK_IDS)`), 100 passati.
> - ✅ **Codice** (07:03): `apply_b9.py` applicato (3 operazioni in 2 file, il modulo, 4 cataloghi); ruff e black puliti
>   sui 6 file Python; `i18n build`: 4983 chiavi (+9); `i18n check` strict pulito.
> - ✅ **Verdi** (07:04-07:06, carico 25-40): `services backup-checks` 57, `services config-audit` 101,
>   `services email-checks` 87 (EMK-010/011/012 di E compresi: l'ordine regge), `services admin-bootstrap` 190,
>   `services profile-defaults` 112, `utils gate-i18n-catalog` 176, `utils gate-i18n-usage` 195. Porta 6187 libera.
> - ✅ **Doc** (docs-writer, giro 2; rilette da me sul codice finale):
>   - `configuration.en.md`: le due righe di «Startup Checks» prima di quelle dell'email, e la riga rara aggiornata;
>     l.205-206 corretta;
>   - `security.md`: (a) la sezione `#backup-config-checks` in fondo a «Secure Backups»; (b) la clausola nella riga
>     `i18n_key` e la frase dopo la tabella dell'ordine; (c) il paragrafo del token in «Secrets from Files»; (d) una
>     frase dopo le righe di H-37;
>   - `settings.md`: la clausola.
>   Build strict pulita (07:07-07:09, 86 s), `check-links` pulito, `utils gate-docs-links` 63.
>   `translate-validate --file admin/configuration.en.md -L`: 309 errori e 663 avvisi su it/fr/es, quasi tutti
>   vecchi (285 `link-missing`). È il debito della traduzione futura, che parte solo su richiesta; niente stamp.
> - Non eseguiti: `api` ed `e2e`, perché nessuna rotta cambia. Le modifiche a `test_backup_restore.py` sono solo testo
>   (py_compile, ruff e black puliti). Niente `front check`: nessun file Svelte o TS cambia, solo i cataloghi JSON,
>   coperti da `i18n check` e dai due gate.
> - **Backlog**: B-9 ✅; B-30 nuovo.
>
> **Commit e merge con A8a+N70+E-13** (07:12-07:36):
>
> - 07:12: il coordinatore committa B-9 (`b35581e5b`). Contro il ramo A8a+N70+E-13 confligge in 4 file; A entra prima.
>   Intanto, fino al merge: albero pulito, B-30 solo in analisi (sezione «B-30» qui sotto).
> - 07:22: A8a+N70+E-13 è entrato (dev `45f9c5406`), e il coordinatore apre nel mio worktree il merge di dev nel mio ramo.
> - Risoluzione, tenendo entrambi i lati, nell'ordine vero di `CONFIG_CHECKS`: piattaforma, **B**, **A**, E.
>   - `config_audit.py`: `*BACKUP_CONFIG_CHECKS` dopo `check_log_level`, poi `*ACCOUNTS_CONFIG_CHECKS` di A, poi quelli
>     di E. È l'ordine che il test di A sulla tupla intera
>     (`test_config_checks_holds_every_check_in_its_place_with_its_id`) già si aspettava: il suo `platform` era ogni
>     voce di `CHECK_IDS` tranne quelle di E, quindi conteneva anche le due di B. Restano veri «A subito prima dei tre di
>     E» ed «E per ultimo» (EMK-010/011/012). La docstring del modulo ora nomina i prefissi `auth`, `backup` ed `email`.
>   - `test_config_audit.py`: in `_configure` entrambi i blocchi (B, poi A); la docstring (c); nel test di A sulla tupla
>     intera, i controlli di B resi espliciti (`backup = (check_panel_token, check_upload_limit)`, fuori da `platform`).
>     Il verdetto è lo stesso; il messaggio e la docstring prima erano sbagliati. Da far rivedere a H.
>   - `configuration.en.md`, «Startup Checks»: le due righe di B, poi quella di A, poi quelle dell'email (ordine del
>     log).
>   - `security.md`:
>     - la riga `i18n_key`: la riscrittura di dev più la clausola `backup.checks.*`, e «No page shows the `instance`,
>       `auth` and `backup` messages yet»;
>     - due mie righe che il merge aveva reso false, il punto «In `CONFIG_CHECKS`» e la frase dell'ordine («platform,
>       B, A, E»);
>     - due righe `backup.*` nella tabella dell'ordine di H, fra `platform.log_level` e `accounts.login_limit`: senza
>       di esse la tabella, che dice «in this order», mostrava il controllo di A subito dopo `log_level`. Da far rivedere
>       a H.
>   - Riletti gli auto-merge: `settings.md` (la mia clausola intatta; i pezzi di dev stanno altrove),
>     `_backend_services.py` (entrambi i selettori; compila), `BACKLOG_POST_1.2.md` (sezione B intatta).
>   - Il nuovo `GET /security/checks` di dev restituisce `run_config_checks()`, quindi anche i due controlli di B. I suoi
>     test (`api security-checks`, `api login-throttle`) confrontano a runtime, senza una lista fissa: non me ne aspetto
>     la rottura. Il coordinatore lo mette nel prossimo gate; io lo faccio girare nello slot API di B-30.
> - Gate (07:27-07:36, corsia 6187, carico 36-48, un'attesa sopra 50): `services config-audit` 102 (101 prima, più il
>   test di A), `backup-checks` 57, `email-checks` 87, `accounts-checks` 76; `mkdocs build` strict OK (124 s),
>   `check-links` OK, `utils gate-docs-links` 63. Porta libera; `git diff --cached --check` pulito; ho messo in stage
>   solo le 4 risoluzioni.
> - **Entrato**: merge `0f3f72961` → dev `997dc7ecf`, CHANGELOG ✨ `94fb9be08`; HEAD portata in avanti a `94fb9be08`.
> - **Congelamento** (coordinatore): `frontend/e2e/settings/backup.spec.ts` resta fermo fino all'ingresso di A8b.
>   A cambia il controllo del membro e il clic a `:263/:276` (il nuovo percorso della scheda); lo rivedo al
>   checkpoint di A.

### B-30 — un disco pieno negli avvii brevi del backup e del ripristino (2026-10-17, 07:12-08:00) — ✅ 🧊 FROZEN (checkpoint delle 08:00)

> **Analisi** (07:12-07:17, in sola lettura sull'albero pulito; testo intero nei file della sessione,
> `b30-analysis.md`). `jobs._out_of_space` (ENOSPC, EDQUOT, `SQLITE_FULL`, lungo la catena delle cause) distingue un
> disco pieno da ogni altro guasto nelle fasi lunghe: la costruzione del backup (`backup_no_space`), il controllo in
> background (`no_space`), il file e le scritture dell'upload (507). Non negli avvii brevi:
>
> 1. **upload, la cartella**: `ensure_private_dir(uploads_dir)` sta fuori dal `try` (`restore_jobs.py` l.145): il primo
>    upload su un disco pieno dà 500 `backup_upload_failed`, non 507 (il B-30 annotato);
> 2. **upload, la fine**: `fsync`, `close` e `replace` di `finish()` senza mappatura. NFS e le quote segnalano il
>    guasto a `close` o `fsync` (close(2)), quindi 500. In più, una `close` fallita lasciava `self._fd` impostato, e
>    `abort` l'avrebbe chiuso una seconda volta (EBADF, o il descrittore riusato da un altro thread);
> 3. **il controllo, l'avvio** (`POST /restore/stage` → `start_check`): la rotta non prende `OSError`. ENOSPC, EACCES
>    o EIO escono come il 500 in testo semplice di Starlette, senza codice, con un traceback nel log; la scheda dice
>    «unexpected». È la stessa classe della scoperta (f) n.1 di B3, corretta allora solo per l'upload;
> 4. **la conferma**: lo stesso 500 senza codice (raro; `_write_state` è atomico: mai mezza conferma);
> 5. **il backup, l'avvio** (scheda e pannello, `start_job`): un disco pieno dà 500 `backup_failed`; un secondo dopo,
>    nella costruzione, lo stesso disco dà `backup_no_space`;
> 6. **il riavvio**: `restore_restart_failed` ha un codice ma nessun messaggio nella UI (fuori da `ERROR_KEYS`: dice
>    «unexpected») e nessuna riga nella guida;
> 7. **l'annullamento**: un `OSError` dà un 500 senza codice. Non riguarda lo spazio.
>
> **Decisioni del coordinatore (07:18)**:
>
> 1. ambito **1+2+3+5**;
> 2. **`stage_failed`** per un `OSError` che non è spazio all'avvio del controllo, con una riga nel log;
> 3. **B-31** (4, 6, 7) come lotto separato, dopo B-30.
>
> L'implementazione parte dopo il merge e l'ingresso di B-9 (via arrivato verso le 07:38), con uno slot API breve per
> rossi e verdi.
>
> **Contratto congelato** (file della sessione, `b30-test-brief.md`):
>
> - un disco pieno (ENOSPC o EDQUOT) alla cartella o alla fine dell'upload, all'avvio del controllo, all'avvio del
>   backup (scheda e pannello) → **507 `backup_no_space`**;
> - all'avvio del controllo, ogni altro `OSError` → **500 `stage_failed`**, con un ERROR nel log (tipo e strerror);
> - mai le parole del sistema né un percorso nella risposta; nulla lasciato indietro; il lock del controllo libero;
> - `jobs._out_of_space` diventa pubblica, `out_of_space`: la usano le rotte;
> - OpenAPI: 507 in `START_RESPONSES` e sulla rotta del controllo, il cui 500 nomina anche `stage_failed`.
>
> Nessun cambiamento del frontend: `backupFailureCode` legge `detail.code` qualunque sia lo stato, e le due schede
> hanno già le frasi di `backup_no_space` e `stage_failed`. Le guardie lo fissano.
>
> **Codice pronto** in `b30-wip/apply_b30.py` (18 operazioni in 5 file), provato a secco su `94fb9be08`. Le copie
> patchate, scritte nei file della sessione, passano ruff (ordine degli import compreso) e black, letti da stdin col
> percorso vero del repo: il worktree resta intatto finché i rossi non hanno girato.
>
> - ✅ **Rossi scritti** (TA-B, dalle 07:39, ultimo file alle 07:47): 39 istanze in 4 file, nessuna verde oggi.
>   - `test_backup_restore.py` 15: (1) cartella ENOSPC/EDQUOT ×2; (2) fine dell'upload ×3 (fsync-ENOSPC,
>     close-EDQUOT, close-ENOSPC), con la chiusura del descrittore contata una sola volta; (3) ×4 e (3') ×4 (le cartelle e
>     il primo stato, × ENOSPC/EDQUOT o EACCES/EIO; il messaggio esatto, una riga di log, l'upload tenuto, nessuno stato
>     né thread, poi 202); l'OpenAPI: `refusals` (+507) e un test nuovo sui codici `no_space`/`stage_failed`;
>   - `test_backup_instance_errors.py` 4: ENOSPC, EDQUOT, EIO causato da ENOSPC → 507, più l'OpenAPI;
>   - `test_backup_panel.py` 2 (PANEL-022): l'avvio del pannello su un disco pieno → 507, più l'OpenAPI;
>   - `test_backup_jobs.py` 18: `jobs._out_of_space` → `jobs.out_of_space`.
>   Note di TA-B:
>   - la doppia `close` è un bug vero: una `close` fallita lasciava il numero a `abort`, che su Linux poteva chiudere
>     il file aperto nel frattempo da un'altra richiesta;
>   - il lock di (3) funziona già oggi: manca solo la mappatura nella rotta;
>   - `_FOLDER_UNUSABLE` è condiviso fra stage e conferma, quindi lo stage ha la sua descrizione (`_STAGE_NOT_STARTED`
>     nella patch).
> - ✅ **Rosso leggero** (07:49, corsia 6187, carico 27): `services backup-jobs`, 18 falliti e 51 passati: 16
>   `AttributeError: … has no attribute 'out_of_space'`, più i 2 cicli, che falliscono dentro il loro thread.
> - **Slot API chiesto** (07:48): i rossi `api backup-restore`, `backup-instance-errors` e `backup-panel`, poi il
>   codice, poi i verdi degli stessi più `api backup`, `backup-secure`, `backup-restore-apply` e `security-checks`.
> - ✅ **Slot 2** (concesso alle 07:49, rilasciato alle 07:57; corsia 6187, carico 20-36):
>   - rossi (07:50-07:54): `api backup-restore` 15 falliti e 131 passati, `api backup-instance-errors` 4 e 6,
>     `api backup-panel` 2 e 59. Ognuno per la ragione attesa: 500 `backup_upload_failed`; il 500 in testo semplice di
>     Starlette («Internal Server Error») all'avvio del controllo; i 507 e i codici assenti dall'OpenAPI. Il primo run ha
>     ricostruito frontend e doc (svelte-check: 0 errori);
>   - **codice** (07:54): `apply_b30.py`, 18 operazioni in 5 file; ruff e black puliti sui 6 file Python di B-30;
>     nessun `_out_of_space` rimasto;
>   - verdi (07:54-07:57): `api backup-restore` 146, `api backup-instance-errors` 10, `api backup-panel` 61,
>     `api backup` 23, `api backup-secure` 24, `api backup-restore-apply` 136, `api security-checks` 3 (i due controlli
>     di B ora fra quelli che l'endpoint restituisce).
> - ✅ **Verdi leggeri** (07:57-07:58): `services backup-jobs` 69, `backup-staging` 161, `backup-secure` 68,
>   `backup-leftovers` 44, `backup-checks` 57.
> - ✅ `api sync` (07:58): l'OpenAPI documenta il 507 sui tre avvii (stage `no_space`; istanza e pannello
>   `backup_no_space`) e il 500 `stage_failed` dello stage; i file generati sono ignorati da git.
> - ✅ **Doc** (07:59-08:00): `mkdocs build` strict OK (55 s), `check-links` OK, `utils gate-docs-links` 63. Traduzioni:
>   `backup_restore.en.md` non ne ha;
>   `hosting_providers.en.md` non ne ha.
> - Non eseguiti: `e2e` (nessun file Svelte né componente cambia; `frontend/e2e/settings/backup.spec.ts` resta fermo per
>   A8b), `front check` a parte quello del build dentro il primo run `api`.
> - **Backlog**: B-30 ✅; B-31 nuovo (conferma, annullamento, messaggio del riavvio).
> - ✅ **Guardie Vitest** (TA-F, 07:43): 4 casi in 3 file (`backupJob.test.ts`, `BackupDownloadCard.test.ts`,
>   `restoreFlow.test.ts`), verdi già oggi per lettura del codice (non ancora eseguiti): ogni codice si legge da
>   `detail.code` qualunque sia lo stato, e le schede lo traducono. Nessun buco funzionale del frontend.
> - **Revisione di H su B-9** (OK, via il coordinatore, 07:45): nella docstring di `instance_backup/checks.py`
>   «right before E's email checks» non è più vero, perché in mezzo ci sono quelli di A. Corretta dentro B-30: «right
>   after the platform's own checks and before workstream A's and E's (E's close it)»; ruff e black puliti. Le
>   impalcature «B-9 is not written» in `test_config_audit.py` le toglie H in H-35: io non le tocco.
> - **⚠️ Fuori pista — il codice all'avvio del controllo** (07:44, decisione mia, dentro i codici di B): TA-F nota che
>   il 507 `backup_no_space` all'avvio del controllo farebbe dire alla scheda «Not enough free space on the server for
>   this archive.», la frase scritta per l'upload. Il codice del controllo che resta senza spazio, `no_space`, dice
>   invece «…to check the archive». Quindi all'avvio del controllo: **507 `no_space`** e 500 `stage_failed`, i due
>   codici del controllo (`StagingError`). L'upload e l'avvio del backup restano `backup_no_space`. Aggiornati la patch,
>   il contratto (revisione 07:44), TA-B (mentre scriveva), TA-F e il docs-writer.
> - ✅ **Guardie eseguite** (07:45, carico 24): `vitest run` su `backupJob.test.ts`, `BackupDownloadCard.test.ts`,
>   `restoreFlow.test.ts`: 3 file, 412 test verdi. Il frontend legge già le nuove risposte, senza cambiare nulla.
> - ✅ **Doc** (docs-writer, finito alle 07:44; codice non ancora applicato):
>   - `backup_restore.en.md`: quattro righe in «What Settings › Backup Says» (upload `backup_no_space`, controllo
>     `no_space`, `stage_failed`, backup `backup_no_space`), in un solo blocco per il merge con A8b;
>   - `hosting_providers.en.md`: una riga `507` all'avvio del pannello; il 507 dell'upload vale anche per un disco che
>     si dice pieno solo alla fine;
>   - `security.md`: «The start» del backup, la riga delle rotte del controllo, un paragrafo su `jobs.out_of_space` e su
>     `UploadWriter`.
>   Il docs-writer ha corretto il mio contratto: la cartella è `.restore/upload/` (`UPLOAD_FOLDER = "upload"`), non
>   `uploads/`. Nota sua, lasciata com'è: dopo un avvio di controllo fallito, la scheda dimentica l'id dell'upload; nella
>   UI «riprova» vuol dire scegliere di nuovo l'archivio, che sostituisce quello tenuto.

### B-31 — conferma, annullamento e riavvio: un codice e un messaggio (2026-10-17, 08:01-08:46) — ✅ 🧊 FROZEN (checkpoint delle 08:46)

> **B-30 entrato** (coordinatore, 08:01): commit con la punta `116df6800`, dev `af9b7f482`, CHANGELOG 🐛 `f4dab3db7`;
> HEAD portata in avanti a **`f4dab3db7`**, pulita. **Via a B-31** come annotato: un 500 con un codice e un messaggio
> suo per conferma, annullamento e riavvio (3 chiavi × 4, `ERROR_KEYS`, l'elenco §5 di `restoreI18n`), 507 alla
> conferma. Niente classi di colore; `backup.spec.ts` resta fermo per A8b.
>
> **Stato reale** (verificato prima di scrivere il contratto):
>
> - conferma (`confirm_check` → `apply.confirm_restore`): la cartella `.restore`, il lock, poi lo stato scritto per
>   ultimo e in modo atomico; dopo, solo `drop_ticket`, che non solleva mai. Quindi un `OSError` vuol dire sempre «nulla
>   confermato». La rotta prende solo `BackupPathError`: tutto il resto esce come il 500 in testo semplice;
> - annullamento (`apply.cancel_restore`): il lock, la lettura, l'`unlink` dello stato, poi `drop_ticket` e `_fsync_dir`,
>   che non sollevano, poi, con `drop_copy`, `_remove_leftovers`, quasi tutto in silenzio. Restano due punti rari di
>   `remove_stage` (`lstat`, `unlink` di un non-cartella) che possono sollevare **dopo** che il ripristino è già
>   annullato: allora un 500 «could not be cancelled» sarebbe falso. **Correzione accoppiata**: in `cancel_restore` un
>   `OSError` di `_remove_leftovers` diventa un WARNING, e la copia se ne va con `prune`. Così il 500 vuol dire sempre
>   «nulla annullato». Vale anche per `dev.py backup pending --cancel`;
> - riavvio: il 500 `restore_restart_failed` c'è già, ma nessun test lo fissa, e la scheda dice «unexpected» (nessuna
>   chiave, fuori da `ERROR_KEYS`).
>
> **Contratto congelato** (file della sessione, `b31-test-brief.md`, alle 08:05):
>
> - conferma: un disco pieno → 507 `backup_no_space` (WARNING); ogni altro `OSError` → 500 `restore_confirm_failed`
>   (ERROR, tipo e strerror). Nulla confermato; la stessa conferma, tolto il guasto, dà 202;
> - annullamento: un `OSError` prima di togliere il ripristino → 500 `restore_cancel_failed`, il ripristino ancora in
>   attesa; uno durante la rimozione della copia → 204 e un WARNING;
> - riavvio: invariato e ora fissato (500 `restore_restart_failed`, nessun riavvio programmato);
> - i messaggi, in 4 lingue: «… could not be confirmed … Nothing changed.», «… could not be cancelled … It still waits
>   for the next start.», «LibreFolio could not be restarted … The restore still waits for the next start.».
>
> - **Rossi in scrittura** (brief inviati alle 08:05):
>   - TA-B: `test_backup_restore_apply.py` (conferma, annullamento, riavvio, OpenAPI);
>   - TA-S: `test_backup_apply.py` (`cancel_restore` con la copia che non si toglie);
>   - TA-F: `restoreI18n.test.ts` §5 e `restoreFlow.test.ts`.
> - **Codice pronto** in `b31-wip/apply_b31.py` (alle 08:05): 9 operazioni in 3 file, più 4 cataloghi. Provato a secco
>   su `f4dab3db7`; le copie passano ruff, black e prettier.
> - ✅ **Rossi scritti**:
>   - TA-F, 3 + 4 casi: `restoreI18n` §5 con i 3 codi (rossi); `restoreFlow`, blocco «B-31», con conferma 500, conferma
>     507 (guardia), annullamento 500 e riavvio 500 (rossi sulla chiave: oggi «unexpected»);
>   - TA-S, 2 + 1 in `test_backup_apply.py`: la copia che non si toglie (EACCES, EIO; rossi: l'`OSError` esce) e la
>     guardia con `drop_copy=False`. Su sua nota, entrambi fissano anche l'INFO «Pending restore cancelled» con
>     `copy_dropped` falso: dopo una rimozione fallita la riga diceva `copy_dropped=True`. Corretto nella patch;
>   - TA-B, 19 istanze in `test_backup_restore_apply.py`: conferma 507 ×6 (lock o scrittura dello stato × ENOSPC,
>     EDQUOT, EIO causato da ENOSPC) e 500 ×4; annullamento 500 ×4 (lock o rimozione dello stato); la copia che non si
>     toglie ×2 (204); riavvio ×2 (guardie: la rotta prende già l'errore); OpenAPI (rosso su conferma 500/507 e
>     annullamento 500).
> - **⚠️ Fuori pista — «la lettura» nel contratto**: TA-B nota che `_read_state` prende ogni `OSError`, lo registra e
>   rende `None`. Quindi uno stato illeggibile fa rispondere a un annullamento 404 `restore_not_pending`, non 500.
>   Il contratto (§1) diceva «leggere o rimuovere lo stato»: i test coprono il lock e la rimozione. Il 404 su uno stato
>   illeggibile è un comportamento di prima: va nel residuo.
> - ✅ **Rossi leggeri**:
>   - Vitest (08:08, carico 32): 6 falliti e 338 passati, i 6 attesi;
>   - `services backup-apply` (08:19-08:20): 2 falliti e 229 passati, cioè i due casi della copia («cancel_restore let
>     the OSError of the copy's removal out, once the restore was dropped»).
> - ✅ **Metà frontend applicata** (08:09): `--part front` (`ERROR_KEYS` più le 3 chiavi × 4); `i18n build` (4993
>   chiavi) e `i18n check` strict puliti; Vitest (08:09-08:10) su `restoreI18n`, `restoreFlow` e `RestoreCard`: 398 su
>   398; `utils gate-i18n-catalog` 176 e `gate-i18n-usage` 195 (08:14-08:15, dopo un'attesa sopra 50).
> - ✅ **Doc** (docs-writer):
>   - `backup_restore.en.md`: la riga «…for this archive.» ora copre anche la conferma; tre righe nuove;
>   - `security.md`: le righe di conferma, annullamento e riavvio, più la frase su `cancel_restore`;
>   - `cli_tools.en.md` l.580 allineata (la pagina ha traduzioni: debito).
>   Fra le note del docs-writer: il bottone della conferma è «Restore and restart», non «Confirm the restore».
> - **Residuo** (pre-esistente, fuori dall'ambito approvato), in backlog come **B-32**:
>   - in `cancelPending()` la riga `state = 'pending'` è morta (`#fail` mette `failed`): un annullamento rifiutato
>     finisce sulla schermata di errore, non sul blocco del ripristino in attesa con l'errore accanto, come fa il
>     riavvio;
>   - `dev.py backup pending --cancel` finisce in un traceback su un `OSError` prima della rimozione, e la sua riga ✅
>     dice «with its copy» anche quando la copia è rimasta;
>   - uno stato illeggibile dà 404 «not pending» all'annullamento (e `read_restore` dà `None`).
> - **Slot API chiesto** (08:20): il rosso `api backup-restore-apply`, poi la metà backend, poi i verdi
>   `api backup-restore-apply` e `api backup-restore`.
> - **Coordinatore** (risposta alla richiesta, fra le 08:21 e le 08:29): in coda per lo slot 2; approvate le due decisioni (copia → WARNING e 204; conferma →
>   507 `backup_no_space`); i residui nel backlog di B (B-32).
> - ✅ **Slot 2** (08:30-08:34, corsia 6187):
>   - rosso: `api backup-restore-apply` 17 falliti e 137 passati. Conferma e annullamento sul 500 in testo semplice di
>     Starlette; l'OpenAPI sui codici non documentati; le 2 guardie del riavvio verdi. Il primo run ha ricostruito
>     frontend e doc (svelte-check: 0 errori, con la metà frontend già dentro);
>   - **metà backend** (08:33): `--part back`, 8 operazioni su `restore.py` e `apply.py`; ruff e black puliti;
>   - verdi: `api backup-restore-apply` 154, `api backup-restore` 146.
> - ✅ **Verdi leggeri** (08:34-08:39, con un'attesa per carico sopra 50): `services backup-apply` 231, `services backup-outcome` 97,
>   `utils backup-cli-restore` 77.
> - ✅ `api sync` (08:39): la conferma documenta 507 `backup_no_space` e 500 `restore_confirm_failed`, l'annullamento
>   500 `restore_cancel_failed`; i file generati sono ignorati.
> - **⚠️ Fuori pista — le doc dicevano «read»**: le righe dell'annullamento (`backup_restore.en.md`, `security.md`)
>   davano «locked, read or removed». Uno stato illeggibile risponde invece 404 (B-32): tolto «read» dalle due pagine e
>   dal contratto.
> - ✅ **Doc** (08:41-08:45): `mkdocs build` strict OK (143 s), `check-links` OK, `utils gate-docs-links` 63.
>   Traduzioni: `cli_tools.en.md` ne ha (cli_tools.es.md, cli_tools.fr.md, cli_tools.it.md), quindi
>   la sua riga è debito; `backup_restore.en.md` non ne ha. Niente stamp.
> - Non eseguiti: `e2e` (nessun componente cambia; `backup.spec.ts` fermo per A8b); `front check` separato (lo
>   svelte-check del build del primo run `api` era pulito, con `restoreText.ts` già cambiato); `theme-roles` (nessun file
>   Svelte e nessuna classe).
> - **Backlog**: B-31 ✅; B-32 nuovo.

### B-19 — `backup decrypt` lanciato da root (2026-10-17, 08:47-09:23) — ✅ 🧊 FROZEN (checkpoint delle 09:23)

> **B-31 entrato** (coordinatore, 08:47): dev `997c358f5`, CHANGELOG 🐛 `547545b8e`; HEAD portata in avanti a
> **`547545b8e`**, pulita. Prossimi: **B-19** (piccolo, prima il rosso), poi l'**analisi di B7**. B-32, B-18 e B-20
> restano nel backlog; la galleria di B5b passa alla squadra dei colori.
>
> **Stato reale**: ogni comando di `dev.py backup` che usa la cartella dei dati passa al suo proprietario quando parte
> da root (`_data_dir()` → `_drop_root_privileges`, `scripts/backup_cli.py`). `cmd_decrypt` non lo fa: con
> `docker compose exec` lo zip appartiene a root. In più, `is_envelope()` risponde `False` per un file che non può
> leggere: un archivio illeggibile riceve oggi il falso `not_an_envelope`. Dopo il passaggio al proprietario, un file
> di root diventerebbe illeggibile proprio così.
>
> **Contratto congelato** (file della sessione, `b19-test-brief.md`, alle 08:49):
>
> - per prima cosa, prima di toccare l'archivio o `-o` e prima di chiedere la password: se una cartella dei dati
>   esiste (`--test-db` compreso), si passa al suo proprietario con lo stesso `_drop_root_privileges`. Un passaggio
>   fallito stampa il suo messaggio ed esce con 1;
> - senza cartella dei dati si resta l'utente che lancia: «It needs no data directory» resta vero;
> - un archivio illeggibile → `❌ Cannot read <path>: <motivo> (archive_unreadable)` ed esce con 1, prima della password.
>
> - **Rossi in scrittura** (TA-E, `test_backup_cli_secure.py`); doc al docs-writer (`cli_tools.en.md`).
> - **Codice pronto** in `b19-wip/apply_b19.py` (3 operazioni in `scripts/backup_cli.py`: `_decrypt_as_owner`,
>   `_readable_envelope`, `cmd_decrypt`). Ruff (C901 compreso: i controlli dell'archivio sono andati in un helper per
>   tenere `cmd_decrypt` a 10) e black puliti sulla copia.
> - ✅ **Rossi scritti** (TA-E): 6 funzioni nella sezione (m) di `test_backup_cli_secure.py`, nessuna verde oggi. Una
>   finta identità registra i cambi; dopo un `setuid` registrato non risponde più root. L'archivio e il file della
>   password restano illeggibili fino a quel `setuid`, per provare l'ordine. Saltati quando i test girano da root.
> - **⚠️ Fuori pista — revisione del contratto (09:02)**, dalle note di TA-E:
>   - `create`, `inspect` e `restore` leggono `--password-file` **prima** di cambiare utente. Cambiare per primo in
>     decrypt rifiuterebbe un segreto leggibile solo da root (un Docker secret) che gli altri tre accettano. Allora
>     decrypt legge prima `--password-file` (come gli altri), poi cambia utente, ancora prima dell'archivio, di `-o` e
>     di ogni domanda (`_password_file_first`; `_unlock` accetta la password già letta);
>   - `get_data_dir()` può sollevare `ValueError`. Senza essere root non lo chiama più: non c'è nulla da cambiare. Da
>     root, un valore inutilizzabile stampa `❌ <messaggio>` ed esce con 1, senza traceback.
>   La patch (5 operazioni) passa ruff, con la complessità, e black. TA-E aggiorna l'ordine nel suo test e aggiunge i
>   due casi del `ValueError`; il docs-writer aggiunge una clausola sul file della password.
> - ✅ **Test aggiornati** (TA-E): 8 funzioni nella sezione (m). L'ordine ora prova il file della password letto prima
>   del cambio e l'archivio dopo. Due casi nuovi: un `LIBREFOLIO_DATA_DIR` con `#` (`get_data_dir()` solleva
>   `ValueError`) da root dà una riga ❌ ed esce con 1, senza traceback né domande; non da root decifra come oggi.
> - ✅ **Doc** (docs-writer): `cli_tools.en.md` (l.593-595 e 636-640, più la clausola sul file della password letto
>   prima del cambio; traduzioni: debito, niente stamp) e `backup_restore.en.md` l.344-354 (l'esempio diviso fra host e
>   Docker, `-o` scrivibile in `backups/`). La frase generale di `docker_advanced.en.md` l.221 (`docker compose exec`
>   crea file di root) resta per B7d: quella pagina si riscrive comunque per Litestream.
> - ✅ **Rosso** (09:06, corsia 6187, carico 30): `utils backup-cli-secure` 8 falliti e 58 passati, gli 8 nuovi.
> - ✅ **Codice** (09:06): `apply_b19.py`, 5 operazioni in `scripts/backup_cli.py`; ruff (C901 compreso) e black puliti.
> - ✅ **Verdi** (09:06-09:07): `utils backup-cli-secure` 66, `utils backup-cli` 102, `utils backup-cli-restore` 77.
> - ✅ **Doc** (09:08-09:12): `mkdocs build` strict OK (92 s), `check-links` OK, `utils gate-docs-links` 63.
> - **Revisione del cambio di A8b a `backup.spec.ts`** (dev `6e2b2c8b7`, letto con `git diff`; chiesta dal
>   coordinatore): corretto.
>   - FBKP-001a (membro): la presenza passa a `settings-tab-administration`, e restano le assenze di
>     `settings-tab-admin`, `settings-tab-backup` e `backup-tab`;
>   - FBKP-001b (admin): precondizione «Profile selezionata», poi `openSettingsTab(page, 'backup')`, la scheda
>     selezionata e la card idle.
>   Selettori `data-testid`, tempi conservati. Nessuna richiesta.
> - **B7a, tentativo** (09:12-09:23): il demone Docker non gira su questa macchina, e `docker pull` è rimasto ad
>   aspettarlo; fermato. Non è stato creato nulla; tolta la cartella vuota del binario. Lo script ora controlla prima
>   `docker info`. Chiesto al coordinatore chi avvia Docker Desktop.
>   **Coordinatore**: Docker non si avvia (la macchina è del developer, e B7b aspetta comunque le sue risposte). Lo spike
>   passa **alla mattina, con il developer presente** (è nella sua lista).

### B7 — Litestream: analisi (2026-10-17, 08:50-08:55) — 🧊 inviata al coordinatore, prima del codice

> **Stato reale** (HEAD `547545b8e`), confrontato con §3.13 e §3.16:
>
> - **Litestream** non c'è in nessun file. `.env.example:297` ha la sezione «Backup and Litestream» con le sole
>   variabili del backup.
> - **Immagine**: stadio finale `python:3.13-slim` con `gosu` e `tzdata`/`tzdata-legacy` (CP7a, P-4);
>   `ENTRYPOINT ["/entrypoint.sh"]`; `CMD ["uvicorn", …, "--port", "6040"]`; `HEALTHCHECK` su `/api/v1/system/health`,
>   `start-period` 15 s.
> - **`entrypoint.sh`** è cambiato dal piano: ora calcola un budget di spegnimento (`LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS`,
>   8 s di default, 3/8 a uvicorn per svuotare le richieste), poi `chown` della cartella dei dati e `exec gosu`.
> - **I due compose**: `restart: unless-stopped`, healthcheck `/system/health`, **nessuno `stop_grace_period`**, quindi
>   valgono i 10 s di Docker.
> - **CP7a di H** ha portato tzdata, le porte, `dev.py docker exec` con gli id numerici e la versione del frontend
>   nell'immagine. `/system/ready` esiste (DB raggiungibile e schema alla head), ma l'healthcheck usa ancora `/health`.
>   CP7b è HTTP (cache di `/_app`, default del profilo gestito, CSP in sola segnalazione): nessun legame con B7, salvo
>   la tabella dei default del profilo, dove Litestream non serve.
> - **Dati**: un solo DB, `sqlite/app.db` (WAL, attesa 30 s). Lo zip del backup prende solo `sqlite/app.db` da una
>   copia coerente, quindi `.app.db-litestream` non ci entra mai. Il ripristino scambia tutta `sqlite/`, quindi lo
>   stato locale di Litestream se ne va con la cartella vecchia (come in §3.13).
> - **Litestream v0.5.17** è ancora l'ultima versione (31/08/2026, API GitHub). Le funzioni del piano esistono tutte,
>   lette nella doc ufficiale:
>   - l'espansione `${VAR}`;
>   - `restore -if-db-not-exists -if-replica-exists`, e `-integrity-check quick|full`;
>   - `replicate -exec` («esce quando esce il figlio») e `-restore-if-db-not-exists`;
>   - `shutdown-sync-timeout` (v0.5.6, default 30 s);
>   - S3 `sse-customer-key` o `sse-customer-key-path` (v0.5.6; nel file di configurazione solo in YAML, non come
>     parametri dell'URL);
>   - SFTP `password`, `key-path` e `host-key` (v0.5.3: se è vuota, **la chiave del server non si verifica**);
>   - `retention.enabled: false` (v0.5.8: le credenziali non hanno bisogno del permesso di cancellare);
>   - heartbeat (v0.5.6, mandato solo se ogni DB è sincronizzato), `auto-recover` e `reset` (v0.5.7).
>   La cifratura age **non esiste più** dalla v0.5: SSE-C (solo S3) è l'unica cifratura a riposo. Una replica `file://`
>   o SFTP tiene i dati di ogni utente in chiaro.
>
> **Il contratto regge, con questi aggiornamenti**:
>
> 1. **Avviatore** `scripts/docker/start_server.py` come `CMD`. La catena è entrypoint (root, chown) → `gosu` →
>    avviatore → `os.execvp`. Con Litestream acceso il PID 1 diventa `litestream`, e uvicorn è suo figlio; spento, il
>    PID 1 è uvicorn, come oggi. L'avviatore applica per prima cosa `apply_pending_restore()`, poi lo fa il passo
>    del lifespan, che non trova più nulla.
> 2. **Ripristino automatico come passo a parte**: `litestream restore -if-db-not-exists -if-replica-exists
>    -integrity-check quick`, prima di `replicate`. Se fallisce, **l'avvio si ferma**. Partire con un DB vuoto lo
>    replicherebbe come una linea nuova, e il prossimo ripristino automatico prenderebbe il DB vuoto.
> 3. **Dopo uno scambio** (ripristino in avanti o indietro) lo stato locale di Litestream va tolto. In avanti se ne va
>    già con la cartella; all'indietro la cartella vecchia torna con il suo `.app.db-litestream`, che va rimosso.
>    Così la prima sincronizzazione scrive uno snapshot completo. **Da provare nello spike**: che quello snapshot prenda
>    un TXID sopra il massimo della replica, e che un ripristino automatico successivo prenda la linea nuova. Se non è
>    così, servono un sotto-percorso per ogni ripristino o un azzeramento documentato.
> 4. **Spegnimento**: 8 s del budget, più la sincronizzazione finale, più margine. Propongo `shutdown-sync-timeout: 10s`
>    nella configurazione generata, `stop_grace_period: 30s` nei due compose (innocuo da spento: Docker aspetta solo
>    quanto serve) e `kill_timeout = 30` per Fly nella doc. **Da provare**: che `litestream` inoltri SIGTERM/SIGINT
>    a uvicorn e poi sincronizzi.
> 5. **Segreti**: l'avviatore li risolve (`env_secret`, `_FILE` compresi) in variabili interne e scrive nel file solo
>    i riferimenti `${…}`: nessun segreto su disco. SSE-C con `sse-customer-key-path` quando c'è `_FILE`.
>
> **Variabili** (§3.16, confermate, più tre proposte): `…_REPLICA_URL` (vuota = spento; `s3://`, `sftp://`, `file:///`),
> `…_ACCESS_KEY_ID`, `…_SECRET_ACCESS_KEY(_FILE)`, `…_ENDPOINT`, `…_REGION`, `…_SSE_C_KEY(_FILE)`,
> `…_SFTP_PASSWORD(_FILE)`, `…_SFTP_KEY_FILE`, `…_SFTP_HOST_KEY`, `…_RESTORE_ON_START` (1), `…_CONFIG` (vince su
> tutto). Le proposte: `…_RETENTION` (D3), `…_HEARTBEAT_URL` (D5) e l'obbligo di `…_SFTP_HOST_KEY` per SFTP (D7). Ogni
> default lascia il self-hosted com'è (Litestream spento); nessun default nuovo nel profilo gestito.
>
> **Immagine**: il tarball di v0.5.17 per `TARGETARCH`, verificato con lo `sha256` di `checksums.txt` fissato nel
> `Dockerfile` (ci sono anche gli SBOM); circa 13 MB compressi, in tutte e due le varianti; pronto per arm64 (B9).
>
> **Backup e ripristino**:
>
> - il backup zip legge il DB con l'API di backup di SQLite mentre Litestream tiene la sua transazione di lettura:
>   compatibili;
> - la copia del controllo B2/B4 è un altro file, che Litestream non guarda;
> - lo scambio del ripristino avviene prima di Litestream, attraverso l'avviatore. Il commit al primo avvio riuscito
>   non cambia; il rollback passa anche lui dall'avviatore (punto 3);
> - il riavvio chiesto dalla UI: uvicorn esce, Litestream esce con lui, Docker riavvia il container, l'avviatore
>   applica;
> - Litestream copre **solo il DB** (decisione 9): `custom-uploads/`, `broker_reports/`, `scenario_catalog/` e
>   `secrets/` viaggiano negli zip. Nel cloud la chiave d'istanza arriva dall'ambiente.
>
> **Test**:
>
> - leggeri: l'avviatore, con `execvp` e `subprocess` sostituiti (spento/acceso, la configurazione generata per S3,
>   SFTP e file, SSE-C, nessun segreto nel file, `_FILE`, il ripristino all'avvio, `…_CONFIG`, il ripristino in attesa
>   prima di tutto, lo stato tolto dopo un rollback, un ripristino che fallisce ferma l'avvio). Poi le letture in
>   `config/backup.py`, e controlli statici di `Dockerfile` e compose (stadio Litestream, `sha256` per architettura,
>   `CMD`, `stop_grace_period`), nel test di H `release-image-contract` o in uno mio;
> - Docker (ogni run con il via del coordinatore, pulizia alla fine: container, volumi, immagini, reti):
>   - lo **spike** (punti 3 e 4) con l'immagine ufficiale `litestream/litestream:0.5.17` e una replica `file://` su un
>     volume temporaneo: la linea dopo uno scambio in avanti e uno all'indietro, e i segnali;
>   - l'immagine nostra con Litestream spento (avvio come oggi, `docker stop` nel limite) e acceso (scrittura, stop, DB
>     tolto, riavvio, ripristinato);
>   - MinIO facoltativo; SSE-C su MinIO chiede TLS: fuori.
>
> **Lotti proposti**: B7a lo spike (solo Docker, nessun file del repo); B7b avviatore, configurazione e test leggeri;
> B7c immagine e compose, con le prove Docker; B7d le doc (`docker_advanced`, `configuration`, Fly e `kill_timeout`,
> «Porta a casa»).
>
> **Decisioni per il developer**: le D1-D10 del messaggio al coordinatore.
>
> **Coordinatore** (risposta all'analisi): D1-D10 vanno nella lista del developer per la mattina. **Spike B7a
> approvato**, come run pesante: aspetta uno slot libero (gate F, A e W in corso), circa 10 minuti. Usa l'immagine
> ufficiale `litestream/litestream:0.5.17` e una replica `file://` su un volume temporaneo, con **pulizia completa** alla
> fine (container, volumi, immagini, reti) e la prova nel piano. **B7b e i lotti dopo aspettano le risposte del
> developer.** Intanto B-19, poi B-32, B-18 e B-20, piccoli, ognuno col suo checkpoint. I controlli statici di
> `Dockerfile` e compose (in B7b) vanno in **un test nuovo mio**, non in `release-image-contract` di H.

### B-32 — dopo un annullamento rifiutato: la scheda, la CLI e uno stato illeggibile (2026-10-17, 09:25-10:29) — ✅ 🧊 FROZEN (checkpoint delle 10:29)

> **B-19 entrato** (coordinatore, 09:25): dev `e96158e9b`, CHANGELOG 🐛 `67dd18676`; HEAD portata in avanti a
> **`67dd18676`**, pulita, con A8b dentro. La revisione di `backup.spec.ts` di A8b è presa per buona. Ordine: B-32 →
> B-18 → B-20, ognuno col suo checkpoint. Lo spike B7a passa **alla mattina, col developer presente**: Docker non lo
> avvio io.
>
> **Stato reale** (lettura, 09:25-09:35):
>
> - `restoreFlow.cancelPending()`: `state = 'pending'` seguito da `#fail(...)`, che mette subito `failed`. La riga è
>   morta: un annullamento rifiutato finisce sulla schermata d'errore. Il riavvio rifiutato resta invece su `pending`
>   con l'errore (`#setError`), e la scheda sa già mostrare il blocco in attesa con l'errore accanto.
> - `cmd_pending --cancel` prende solo `RestoreNotPendingError`. `cancel_restore` rende lo stato, non `copy_dropped`
>   (i test fissano `cancel_restore(...) == pending`).
> - `_read_state` rende `None` per ogni `OSError`. Lo leggono in 10 punti:
>   - stato, annullamento, riavvio, conferma;
>   - i due passi d'avvio;
>   - l'esito;
>   - `protected_stage` (pulizia, `remove_check`);
>   - la CLI (`pending` e il controllo prima di `restore`).
>   Con `O_NOFOLLOW`, uno stato che è un link dà ELOOP: oggi «nessun ripristino», e §10 lo fissa (`UNTRUSTED`, la
>   conferma che sostituisce un link). Il contenuto non valido (`ValidationError`) è lo «stato illeggibile» dei test
>   esistenti: resta «none».
>
> **Contratto congelato** (`b32-contract.md` nella cartella della sessione, 09:38):
>
> 1. Un annullamento rifiutato (tranne il 404 `restore_not_pending`) resta su **`pending`**. L'errore sta accanto
>    (`failure` `cancel`), con lo stato invariato e un solo evento `failed`, e si può annullare o riavviare di nuovo:
>    come il riavvio rifiutato.
> 2. Le uscite di `pending --cancel`:
>    - un `OSError` → `❌ The restore could not be cancelled: <strerror>. It still waits for the next start
>      (restore_cancel_failed)`, uscita 1, senza traceback;
>    - copia rimasta → `✅ …dropped: the data stays as it is` + `⚠️  Its checked copy could not be removed: it goes
>      when its check expires`, uscita 0. La CLI lo capisce dalla cartella della copia ancora presente.
> 3. Nuovo `RestoreStateUnreadableError`, codice `restore_state_unreadable`, con `reason` (lo `strerror`, mai un
>    percorso). `_read_state` fa prima un `lstat`:
>    - nessun file → `None`;
>    - non un file regolare (link, cartella) → `None` registrato, come oggi;
>    - ogni altro `OSError` → registrato e sollevato;
>    - il contenuto non valido resta `None`.
>    **Rigidi**:
>    - status, `DELETE /pending`, riavvio e conferma → 500. La conferma rifiuta invece di scrivere sopra: dietro può
>      esserci un ripristino applicato a metà;
>    - la CLI `pending`, `pending --cancel` e il controllo prima di `restore` → ❌, uscita 1.
>    `cancel_restore` legge prima senza lock, come `prepare_restart`: un `.restore/` che il server non può
>    attraversare non passa più per «nessuno stato».
>    **Indulgenti, come oggi**: i due passi d'avvio (con un helper), l'esito, `protected_stage`.
> 4. Una chiave × 4 lingue, più `ERROR_KEYS`.
> 5. I commenti «Settings › Administration › Backup»:
>    - in `BackupTab.svelte`, `apply.py`, `backup_cli.py`, `RestoreCard.test.ts`;
>    - e due descrizioni del runner di B5a.
>
> - **Coordinatore** (09:40): nessun veto su 1-4. Il residuo (un avvio che trova uno stato illeggibile va avanti) va
>   nella lista del developer. Slot 2 di ~12 min in coda dopo E → J → Y.
> - **Rossi in scrittura** (09:38), file distinti:
>   - TA-S `test_backup_apply.py`;
>   - TA-B `test_backup_restore_apply.py`;
>   - TA-E `test_backup_cli_restore.py`;
>   - TA-F `restoreFlow.test.ts`, `RestoreCard.test.ts`, `restoreI18n.test.ts`.
> - **Codice pronto** in `b32-wip/apply_b32.py` (09:41): 31 operazioni in 8 file + 4 cataloghi, `--part front|back`.
>   Sulla copia emessa:
>   - ruff (con la configurazione del repo, `--stdin-filename`) e black puliti. `_RESTART_NOT_PREPARED` è scritto
>     nella forma di black: oltre 300 caratteri;
>   - prettier pulito sui 4 file del frontend e sui 4 cataloghi.
> - ✅ **Rossi scritti** (09:38-09:53), file distinti, nessuno lanciato dagli autori:
>   - **TA-S**, sezione (o) di `test_backup_apply.py`: 7 funzioni, 24 casi (14 rossi, 10 guardie). Tre modi di
>     rendere illeggibile: `os.open` che rifiuta EACCES o EIO, e un vero `chmod 000`, saltato da root.
>   - **TA-B**, sezione (j) di `test_backup_restore_apply.py`: 6 test, 16 casi (13 rossi; la guardia dell'esito ×3).
>   - **TA-E**, sezione (g) di `test_backup_cli_restore.py`: 8 funzioni, 15 casi (13 rossi, 2 guardie).
>   - **TA-F**: 11 casi rossi fra `restoreFlow.test.ts`, `RestoreCard.test.ts` e `restoreI18n.test.ts`. Ha girato anche
>     la vecchia tabella di B5b, che fissava `failed` per un annullamento rifiutato, e ha allineato l'intestazione di
>     `RestoreCard.test.ts`.
>   - **Docs-writer**:
>     - `backup_restore.en.md`: la riga dell'annullamento e la nuova riga `restore_state_unreadable`;
>     - `cli_tools.en.md` l.538, 555 e 581 (debito di traduzione, niente stamp);
>     - `security.md`: quattro righe della tabella e il punto «What cannot be read is not none».
> - **⚠️ Fuori pista — `lexists` (09:55)**, da TA-E: `os.path.lexists` inghiotte EACCES. Con `.restore/stage` non
>   attraversabile, la CLI direbbe «with its copy» mentre la copia resta. E `rmtree(ignore_errors=True)` di
>   `remove_stage` può lasciare una copia in sola lettura senza sollevare nulla: il `copy_dropped` di B-31 non basta.
>   Contratto §2 e patch corretti: un helper `_copy_left` fa `os.lstat`. `FileNotFoundError` vuol dire sparita; ogni
>   altro `OSError` conta come ancora lì. TA-E ha aggiunto il caso `stage-folder-not-searchable`.
> - **Note degli autori, già nella patch**:
>   - TA-B: la conferma ha bisogno del suo `except` prima di quello generico, altrimenti risponderebbe 409 con le
>     parole del sistema; l'esito deve leggere in modo indulgente.
>   - TA-S: il `lstat` prima toglie anche una perdita di descrittore (uno stato che è una cartella: `os.fdopen` solleva
>     senza chiudere) e un blocco su una FIFO. La FIFO non ha test: oggi resterebbe appesa.
> - ✅ **Rossi** (corsia 6187):
>   - `services backup-apply` (09:48-09:49, carico 18): **14 falliti**, 241 passati. I 14 sono i casi rigidi, per i
>     motivi attesi (`None`, `restore_not_pending`, una conferma che scrive sopra); le guardie verdi;
>   - Vitest, i 3 file (09:49-09:50): **11 falliti**, 394 passati, gli 11 attesi;
>   - `utils backup-cli-restore` (09:50-09:51): **13 falliti**, 79 passati, i 13 attesi.
>   - `api backup-restore-apply` aspetta lo slot: lì rosso, poi la metà backend, poi verde.
> - ✅ **Metà frontend applicata** (09:51:27): `--part front`, 5 operazioni in 4 file più i 4 cataloghi.
>   - `i18n build` (5014 chiavi) e `i18n check` strict puliti;
>   - Vitest (09:52) sui 3 file: **405 su 405**;
>   - Vitest su tutta la cartella `features/backup` (09:53): **867 su 867**, 8 file.
> - **⚠️ Fuori pista — una frase della doc (09:54)**: in `cli_tools.en.md`, «The log above them has the warning…» non
>   è sempre vero. Una copia lasciata senza errore (`rmtree(ignore_errors=True)` davanti a una cartella in sola lettura)
>   non registra nessun avviso, e la pulizia allora riprova soltanto. Corretto io stesso: l'avviso c'è quando la
>   rimozione ha sollevato un errore; LibreFolio «tries again» alla prima partenza dopo 24 ore.
> - ✅ **Doc** (09:55-09:56, carico 32): `mkdocs build` strict pulito (55 s), `check-links` pulito,
>   `utils gate-docs-links` 63 passati; porta 6187 libera.
> - **Coordinatore** (09:57):
>   - B-18, D1: vince la chiave dell'archivio, con la riga ℹ️. D2: la riga ⚠️ quando la chiave data non legge nessun
>     segreto;
>   - B-18 parte dopo il checkpoint di B-32, solo run leggeri, con H in revisione al checkpoint (consuma
>     `derive_key_from` e `read_secret_file`);
>   - lo slot di B-32 viene dopo Y-27.
>   Contratto di B-18 pronto nella cartella della sessione (`b18-contract.md`); lo script dello slot di B-32 è
>   `b32-wip/slot_after_red.sh`.
> - ✅ **Slot 2** (coordinatore, 10:04; accanto girava l'E2E di Y):
>   - **Rosso** `api backup-restore-apply` (10:04:51-10:09:28; il build del frontend rifatto con la metà frontend
>     dentro, svelte-check 0 errori): **13 falliti**, 157 passati. Sono i 13 di TA-B: 200 `none`, 404, 409, 202 e
>     l'OpenAPI.
>   - **Metà backend applicata** (10:09:39): `--part back`, 26 operazioni in 4 file. Ruff e black puliti sui file veri.
>   - **Verdi**:
>     - `api backup-restore-apply` (10:09-10:10): **170 passati**;
>     - `api backup-restore`: 146; `api security-checks`: 3;
>     - lo script ha aspettato il carico ≥ 50 dalle 10:11 alle 10:14 (picco 104).
>   - `api sync` (10:16-10:17), uscita 0: `openapi.json` e `generated.ts`, ignorati da git, nominano
>     `restore_state_unreadable`.
>   - Slot liberato alle 10:17:47; porta 6187 libera.
> - ✅ **Verdi leggeri** (10:19-10:26, nella mia corsia; attesa del carico dalle 10:21 alle 10:25):
>   - `services backup-apply` 255, `services backup-outcome` 97, `services backup-leftovers` 44;
>   - `utils backup-cli-restore` 92, `utils backup-cli` 102, `utils backup-cli-secure` 66.
>   Porta 6187 libera.
> - ✅ **Controlli statici** (10:27): ruff e black puliti su tutti i 10 file Python cambiati, prettier pulito su tutti i
>   file del frontend cambiati, `git diff --check` pulito.
> - Lasciato com'è: il messaggio del `throw` in `RestoreCard.test.ts:180`, «Settings › Backup has no restore card».
>   È il messaggio rosso di B5b per una scheda che non può più mancare; non tocco un test dopo il verde.
> - Non eseguiti: `e2e` (lo slot non lo chiedeva; la scheda è coperta dai casi Vitest della carta e del flusso),
>   `front check` separato (lo svelte-check del build del rosso API era pulito, con la metà frontend dentro).
> - **Backlog**: B-32 ✅; **B-33** nuovo, i residui dichiarati, con la decisione del developer sul fail closed.

### B-18 — `restore --instance-key-file`: i segreti di un archivio in chiaro con la chiave vecchia (2026-10-17, 10:29-10:51) — ✅ 🧊 FROZEN (checkpoint delle 10:51)

> **B-32 entrato** (coordinatore, 10:29): dev `7af21a5c1` (commit `ca1343d6d`), CHANGELOG 🐛 `d11ac04d3`. HEAD portata
> in avanti a **`d11ac04d3`**, pulita. Via a B-18 con D1 e D2 come decisi; solo run leggeri, revisione di H al
> checkpoint.
>
> **Stato reale** (lettura, 09:45-10:35):
>
> - `staging._stage` ricifra i segreti dei plugin soltanto con la chiave che un archivio sicuro porta:
>   `archive_key = … if INSTANCE_KEY_ENTRY in entries else None` → `_plugin_secrets` → `_archive_subkey` →
>   `rekey_plugin_secrets(conn, old, current)`.
> - `rekey_plugin_secrets` lascia stare le righe già sotto la chiave di questa istanza (contate `already_current`, non
>   illeggibili). Ricifra quelle sotto la chiave vecchia e conta illeggibili le altre.
> - Se la chiave di questa istanza non si può usare (`settings_subkey` solleva `InstanceKeyError`), la verifica non
>   ricifra nulla e conta tutto illeggibile (test B4 «without a usable key of its own»).
>   `instance_key_status().problem` lo dice senza sollevare e senza creare il file.
> - La docstring di `derive_key_from` (H) descrive già questa strada: la copia dell'amministratore di
>   `secrets/instance.key`, letta con `read_secret_file()`, o il vecchio `LIBREFOLIO_INSTANCE_KEY`.
> - I test di ricifratura di B4 stanno in `test_backup_secure.py` (`services backup-secure`), non in
>   `test_backup_staging.py`.
> - La doc (`backup_restore.en.md` l.36) dà una sola strada: rimettere la chiave vecchia al posto di quella nuova. Non
>   va bene per un'installazione che tiene la sua chiave, come un'istanza ospitata o una con segreti suoi.
>
> **Contratto congelato** (`b18-contract.md` nella cartella della sessione, 10:36):
>
> 1. `stage_archive(..., instance_key=None)` controlla la chiave per prima, prima del lock e di ogni cartella:
>    `derive_key_from` → `StagingError("instance_key_invalid")`, senza mai il testo della chiave. In `_stage` vince
>    la chiave dell'archivio; altrimenti si usa quella data. Le rotte API non cambiano, il report nemmeno (nessun
>    OpenAPI).
> 2. CLI `restore --instance-key-file FILE`, anche con `--dry-run`:
>    - letto con `read_secret_file` da root, prima del cambio di utente e prima della password;
>    - errori ❌ `instance_key_unreadable` e `instance_key_invalid`, uscita 1;
>    - la riga «Instance key: not included; given with --instance-key-file».
>    - **D1**: vince la chiave dell'archivio, con la riga ℹ️.
>    - **D2**: la riga ⚠️ se la chiave data non ricifra nulla. Se invece è la chiave di questa istanza a non funzionare,
>      un'altra ⚠️ che lo dice (raffinamento mio: la riga D2 accuserebbe la chiave sbagliata).
> 3. Doc: `cli_tools.en.md` e `backup_restore.en.md`. Proposta di CHANGELOG ✨.
>
> - **Rossi in scrittura** (10:37):
>   - TA-S: `test_backup_secure.py`, k1-k6;
>   - TA-E: `test_backup_cli_restore.py` (h), con c8 accanto al finto root di B-19 se conviene;
>   - docs-writer: le due pagine.
> - **Codice pronto** (10:40) in `b18-wip/apply_b18.py`: 17 operazioni in 2 file.
>   - `staging.py`: `instance_key`, `_refuse_unusable_instance_key` prima della cartella e del lock, e
>     `archive_key = … else instance_key`.
>   - `backup_cli.py`:
>     - `_restore_keys`: prima il file della chiave, poi la password. Tiene `cmd_restore` sotto C901;
>     - `_instance_key_from_file`;
>     - `_print_given_key` per D1, D2 e l'eccezione;
>     - l'opzione, una riga d'uso, un esempio.
>   Ruff e black puliti sulla copia emessa, dopo aver rimesso la firma di `stage_archive` su una riga sola, come vuole
>   black.
> - ✅ **Rossi dei servizi scritti** (TA-S, 10:44): sezione (i) di `test_backup_secure.py`, 6 funzioni e 9 casi (7
>   rossi, 2 guardie). k3 prova `""` e 31 caratteri, con e senza un `.restore` lasciato da una verifica precedente.
>   `new_parameter` ha un argomento `by` facoltativo, che nomina B-18 nel messaggio.
> - **⚠️ Fuori pista — `TypeError` (10:45)**, da TA-S: il contratto §1 mandava anche un `TypeError` (una chiave che non
>   è un testo) su `instance_key_invalid`, con la frase «too short», che lì sarebbe falsa. La CLI passa sempre un testo:
>   il contratto ora lascia il `TypeError` di `derive_key_from`, come fa la patch. Il controllo usa `is not None`, mai
>   la verità del valore: `""` è rifiutato.
> - ✅ **Doc scritta** (docs-writer, 10:50):
>   - `cli_tools.en.md`: l.393, 441, 448 e 475; la nuova sottosezione «🗝️ The Instance Key of Another Installation»
>     (`#backup-restore-instance-key`, l.546-561); debito di traduzione, niente stamp;
>   - `backup_restore.en.md`: l.36, e i passi 1, 3 e 4 di «From a Hosted Instance to Your Server».
>   Rivista contro la patch: le righe esatte, i messaggi di `read_secret_file` (il limite di 65536 byte), il percorso
>   dei dati dell'immagine.
>   Lasciato fuori dal docs-writer, da decidere: una clausola in `configuration.en.md` («Saved Secrets and the Instance
>   Key», pagina tradotta).
> - ✅ **Rossi della CLI scritti** (TA-E, 10:42): sezione (h) di `test_backup_cli_restore.py`, 8 funzioni e 10 casi.
>   - c8, il caso da root, sta in (h) e importa il finto root di B-19 da `test_backup_cli_secure.py`;
>   - l'archivio con i segreti viene dagli helper di `test_backup_secure.py`;
>   - c3 vuole il file della chiave letto prima della password, come fa la patch.
> - ✅ **Rossi** (corsia 6187, 10:43-10:44, carico 36):
>   - `services backup-secure`: **7 falliti** e 70 passati; il motivo è il parametro mancante (`new_parameter`);
>   - `utils backup-cli-restore`: **10 falliti** e 92 passati; argparse rifiuta l'opzione.
> - ✅ **Codice applicato** (10:44:11): 17 operazioni in 2 file; ruff (con C901) e black puliti sui file veri.
> - ✅ **Verdi** (10:44-10:47): `services backup-secure` 77, `utils backup-cli-restore` 102,
>   `utils backup-cli-secure` 66, `utils backup-cli` 102, `services backup-staging` 161; porta 6187 libera.
>   `dev.py backup restore --help` mostra l'opzione.
> - ✅ **Doc** (10:47-10:49): `mkdocs build` strict pulito (80 s), `check-links` pulito, `utils gate-docs-links` 63.
> - ✅ **Controlli statici** (10:49): ruff e black su tutti i 6 file Python cambiati; `git diff --check` pulito.
> - Non eseguiti:
>   - `api backup-restore`: nessuno slot chiesto. L'API non passa nessuna chiave, e `instance_key=None` è la strada di
>     prima: la coprono `services backup-staging` (161) e `services backup-secure` (77);
>   - `api sync`: il report non cambia, quindi l'OpenAPI nemmeno.
> - Proposta di CHANGELOG ✨ (docs-writer): «**The old instance key at a restore** — `./dev.py backup restore ARCHIVE
>   --instance-key-file FILE` takes the instance key of the installation that made a clear backup…».
> - **Backlog**: B-18 ✅.

### B-20 — knip e `RESTORE_TICKET_HEADER` (2026-10-17, 10:50-10:54) — ✅ 🧊 FROZEN (checkpoint delle 10:54)

> **B-18 committato** (coordinatore, 10:50): `7b1911fd6`, albero pulito, merge-tree con dev pulito. Il testo del
> CHANGELOG è salvato; l'entrata aspetta la revisione di H. Via a B-20.
>
> **Stato reale**:
> - `RESTORE_TICKET_HEADER` (`backupApi.ts:190`) è usato in produzione soltanto dentro il suo modulo (l.204).
> - Il suo test (`backupApi.test.ts:815`, di B5c) lo legge con un cast sull'import a namespace, scritto quando era
>   ancora rosso, e knip non lo conta come uso.
> - **knip prima** (10:50:56-10:51:02, `frontend/node_modules/.bin/knip --no-progress`): uscita 1, «Unused exports
>   (20)», con `RESTORE_TICKET_HEADER` fra loro. Era già rosso per voci di altri; non è un gate.
>
> **Correzione** (solo il test, a TA-F): `RESTORE_TICKET_HEADER` nell'import per nome (l.99), e l'asserzione diretta su
> di esso. Nessun cambio di prodotto, nessuna riga di CHANGELOG.
>
> - ✅ **Test cambiato** (TA-F, 10:51): l.99 e l.815 di `backupApi.test.ts`; l'import a namespace resta per le ricerche
>   della fase rossa degli altri casi. `prettier --check` pulito.
> - ✅ **Vitest** su `backupApi.test.ts` (10:51:57): **198 su 198**.
> - ✅ **knip dopo** (10:52:04): uscita 1 come prima. «Unused exports» passa da 20 a **19**. Il diff dei due log toglie
>   soltanto la riga di `RESTORE_TICKET_HEADER`; il resto sono orari e il consiglio di dotenv.
> - **Backlog**: B-20 ✅.

### BZ, parte 1 — revisione di sicurezza di ciò che è consegnato (2026-10-17, 10:55-11:58) — ✅ inviata al coordinatore, sola lettura

> **Coordinatore** (10:53):
> - B-20 committato, `7b13e4d43`, sopra B-18 `7b1911fd6`; entrano insieme dopo la revisione di H su B-18.
> - Ora la **parte 1 di BZ**, in sola lettura: le superfici di backup e ripristino consegnate in dev (B-9, B-16, B-19,
>   B-28…B-32) e B-18/B-20 sul mio ramo, cioè rotte, CLI da root, biglietti, staging, lettura degli archivi, segreti.
> - Le scoperte vanno nella mia sezione del backlog come voci B nuove, ognuna con gravità e cura proposta. **Niente
>   codice prima del suo OK.** La parte 2 (la consegna finale) viene alla fine, dopo B7 e B9.
>
> Base: HEAD `7b13e4d43`, albero pulito. Superficie: circa 6800 righe:
> - `instance_backup/*.py` e `api/v1/backup/*.py`;
> - `scripts/backup_cli.py`;
> - `instance_key.py` e `plugin_settings/crypto.py`, solo come consumatore.
> Delegata all'agente `security-review`.
>
> - **B-18 e B-20 entrati** (coordinatore, 10:56): dev `5c4d7456a`, CHANGELOG ✨ `582cfb6b0`; HEAD portata in avanti.
>   La revisione di H su B-18 è OK, con un LOW-1 e due appunti della doc, registrati come **B-34**.
> - **⚠️ Fuori pista — l'agente non parte (10:56)**: la sua richiesta portava con sé il contesto della sessione,
>   243 035 token contro un limite di 128 000. Nessuna lettura è stata fatta. Riprovo dopo la compattazione del contesto.
>   Secondo tentativo (11:00), con un prompt corto e il brief in un file (`bz-security-brief.md` nella cartella della
>   sessione): stesso errore, 293 779 token. L'agente eredita il contesto della mia sessione, e un prompt più corto non
>   basta. Chiesto al coordinatore come procedere (tier a contesto lungo, o lancio da una sessione fresca).
> - **Coordinatore** (11:35):
>   - né l'opzione 1 né la 3: il permesso per il contesto lungo può darlo solo il developer, e la domanda va nella sua
>     lista;
>   - la revisione la faccio **io, direttamente**, in sola lettura, dal brief, area per area (rotte, CLI da root,
>     biglietti e staging, lettura degli archivi, segreti), con un agente `explore` per un'area stretta se parte.
>   Le scoperte diventano voci B con gravità e cura; niente codice prima del suo OK. Registro in corso nella cartella
>   della sessione: `bz-findings.md`.
> - **Metodo** (11:36-11:58): revisione diretta, area per area.
>   - Un agente `explore` (partito senza problemi) ha raccolto i fatti della lettura degli archivi: nomi, estrazione,
>     limiti, manifest, chiave, SQLite, Alembic, involucro, fughe. Ho verificato io i punti decisivi: `env.py` fa vincere
>     l'URL di `-x`; `_row_counts` di post_migration.
>   - Le altre aree le ho lette io: rotte e autenticazione, upload, download, pannello, biglietto dell'esito, CLI da
>     root, password e KDF dei backup sicuri, controlli di B-9, esportazioni.
>   - **Garanzia più bassa** di un agente `security-review` dedicato. La domanda sul contesto lungo è nella lista del
>     developer, se vuole un secondo passaggio.
> - **Scoperte** (5), registrate come voci B nel backlog:
>   - 🟡 **B-35** (F3): lo scompattamento non è limitato dal tetto di caricamento. MEDIO nel cloud;
>   - ⚪ **B-36** (F1): nomi di tabella non quotati in `post_migration._row_counts`; proprietario fuori da B;
>   - ⚪ **B-37** (F2): `trusted_schema` acceso sulle connessioni di post_migration e di Alembic alla copia; fuori da B;
>   - ⚪ **B-38** (F4): la CLI da root legge i file dei segreti attraverso link e FIFO, mentre la guida mette la chiave in
>     `backups/`;
>   - ⚪ **B-39** (F5): formule nei CSV esportati (le `notes` degli eventi).
>   Nessuna critica né alta. Niente codice prima del via del coordinatore.
> - **Sano**: l'elenco con le righe sta in `bz-findings.md`, sezione «Checked and sound».

### B-18, riparazione — il cancello G rosso: `instance_key_invalid` non dichiarato (2026-10-17, 11:40-11:52) — ✅ 🧊 FROZEN

> **Coordinatore, urgente prima di BZ** (11:40): il cancello G (`api backup-restore`) è rosso su
> `test_backup_restore.py::test_every_code_a_check_can_end_with_is_one_the_api_declares`, con
> `(produced, not declared): ['instance_key_invalid']`.
>
> **Causa**: la guardia legge con l'AST ogni `StagingError("<codice>")` di `staging.py` e vuole lo stesso insieme di
> `RestoreErrorCode`, nei due versi. B-18 ha aggiunto `StagingError("instance_key_invalid", …)` senza dichiararlo. Non
> l'avevo visto perché nessun run `api` faceva parte del lotto: niente slot, e i servizi non bastavano.
>
> **Scelta: dichiararlo** (la prima cura proposta dal coordinatore). Nessun test cambia, e la guardia resta stretta: se
> un giorno l'API desse una chiave alla verifica, il codice sarebbe già dichiarato.
> - Oggi non può arrivare da un GET: l'API non passa mai `instance_key`, e la CLI chiama `stage_archive` direttamente,
>   senza registro della verifica.
> - Il commento sopra `RestoreErrorCode` lo dice.
> - La scheda non lo mostra: le liste del frontend sono scritte a mano, non derivate dall'enum generato, e
>   `restoreErrorKey` prende una stringa. Quindi niente chiave i18n e niente `ERROR_KEYS`.
>
> - ✅ `backend/app/schemas/backup.py`: `instance_key_invalid` in coda a `RestoreErrorCode`, con il commento. Ruff e
>   black puliti.
> - ✅ `api backup-restore` (11:44:59-11:51:07, attesa del carico; svelte-check 0 errori nel build): **146 passati**,
>   la guardia compresa.
> - ✅ `api sync` (11:51:07-11:51:42), uscita 0: `openapi.json` e `generated.ts`, ignorati da git, lo contengono.
> - Porta 6187 libera. Nessun tipo del frontend è esaustivo su `RestoreErrorCode` (grep), quindi niente `front check`
>   a parte.
> - **Lezione**: un codice nuovo di `StagingError` richiede `api backup-restore`, anche in un lotto «solo CLI».

### B-35 — un tetto a quello che un archivio scompatta (2026-10-17, 11:59-12:36) — ✅ 🧊 FROZEN (checkpoint delle 12:36)

> **Coordinatore** (11:59): BZ parte 1 va bene. Ordine:
> 1. B-35 (da solo, prima);
> 2. B-39;
> 3. B-36 e B-37 (scrittura permessa su `db/post_migration/__init__.py` e su `env.py` di Alembic, solo per le virgolette
>    e `trusted_schema=OFF`; H rivede);
> 4. B-38 lato CLI;
> 5. B-34, poi le righe di «What It Lists» (B-40).
>
> Forma di B-35: `LIBREFOLIO_BACKUP_MAX_RESTORE_MB`, sul totale dichiarato, prima di `_check_space`.
> - Self-hosted: nessun default.
> - Profilo ospitato: K volte il limite di caricamento, con K scelto e giustificato da me.
> - Un valore esplicito vince sempre.
> - Decisione N82, nella lista del developer.
>
> - **K = 8, misurato** (12:05): l'archivio comprime con deflate livello 6. Il database di test passa 4,1:1, una storia
>   di prezzi sintetica di 52 MB 3,9:1; immagini e PDF restano vicini a 1:1.
>   - Con K = 4 un archivio pesante di database verrebbe rifiutato proprio al limite di caricamento.
>   - 8 lascia il doppio di margine e taglia comunque il caso peggiore di deflate (circa 1000:1) di oltre 100 volte.
>   - Ospitato: 500 MB → 4000 MB. Approvato dal coordinatore (12:15).
> - **Contratto** (`b35-contract.md`, 12:10, con §1b alle 12:16):
>   - il lettore `backup_max_restore_mb()` in `config/backup.py`: nel profilo ospitato, se non impostato, vale
>     `8 × backup_max_upload_mb()`. Eredita da lì il `ProfileDefaultError`, quindi fallisce chiuso; non va nella tabella
>     di H, perché è un multiplo che segue il limite del fornitore;
>   - in staging, `max_unpacked` → `unpacked_too_large`, prima dello spazio, dichiarato in `RestoreErrorCode`;
>   - l'avvio della verifica risponde 503 `backup_restore_unavailable`;
>   - la CLI segue la stessa regola, con `=0` per un comando;
>   - 2 codici × 4 lingue;
>   - una riga in `.env.example`;
>   - **§1b**: il controllo della configurazione `backup.restore_limit`, chiesto subito dal coordinatore, con il
>     permesso di ritoccare la tupla in `test_config_audit.py` di H. Se il limite di caricamento non si legge, il
>     controllo nomina comunque la variabile giusta (`{variable}`);
>   - doc: anche le tre righe di B in `settings.en.md` «What It Lists» (B-40).
> - **Codice pronto** in `b35-wip/apply_b35.py`: 30 operazioni in 9 file più i 4 cataloghi; ruff, black e prettier
>   puliti sulla copia emessa.
> - **Rossi in scrittura**:
>   - TA-S: il lettore e il controllo in `test_backup_checks.py`, la mappa in `test_config_audit.py`, staging;
>   - TA-B: l'API in `test_backup_restore.py`;
>   - TA-E: la CLI, sezione (i);
>   - TA-F: Vitest, 7 casi rossi, scritti;
>   - docs-writer: 5 pagine più `settings`.
> - ✅ **Rossi scritti** (12:00-12:08):
>   - **TA-S**:
>     - `test_backup_checks.py` (h): il lettore e il controllo; (c), (e) a tre, (f) e (g) aggiornati;
>     - `test_config_audit.py` (di H): l'import e la voce della mappa, nient'altro. L'ordine resta simbolico;
>     - `test_backup_staging.py` (m).
>   - **TA-B**: `test_backup_restore.py` (h), con archivi di dimensione esatta (8 MiB, e 8 MiB + 1 byte) che fissano
>     K = 8 e i MiB; la fixture `instance` pulisce la nuova variabile.
>   - **TA-E**: (i), 5 casi, con `no_inherited_restore_limit`.
>   - **TA-F**: 6 casi.
>   - **Docs-writer**: le 6 pagine più «Startup Checks».
> - **⚠️ Fuori pista — `{variable}` (12:20)**: nel profilo ospitato, con la variabile non impostata, un
>   `BackupConfigError` può venire dalla variabile del caricamento. Il controllo prende quindi il nome da
>   `exc.variable`, nel messaggio e nel riassunto. Contratto §1b corretto, TA-S e il docs-writer avvisati. Il
>   riassunto `profileTable` sta in una costante: la riga superava 300 caratteri.
> - ✅ **Rossi** (corsia 6187):
>   - `services backup-checks`: 45 falliti e 48 passati;
>   - `services backup-staging`: 7 falliti e 161 passati;
>   - `services config-audit`: errore di raccolta, atteso, perché il file di H importa il nuovo controllo in cima;
>   - `utils backup-cli-restore`: 5 falliti e 102 passati;
>   - Vitest: 6 falliti e 350 passati;
>   - `api backup-restore` (slot 2, 12:11-12:17): **10 falliti** e 151 passati.
> - ✅ **Patch applicata** (12:17:49): 30 operazioni in 9 file più 4 cataloghi. `i18n build` 5033 chiavi e
>   `i18n check` strict puliti; ruff e black puliti.
> - **⚠️ Fuori pista — un sostituto di `stage_archive` (12:22)**: il primo verde di `api backup-restore` dava
>   1 fallito. Il sostituto in `test_a_check_that_fails_otherwise_ends_failed_with_its_code` non aveva la keyword
>   nuova: `TypeError`, poi `stage_failed`. TA-B ci ha aggiunto `instance_key=None, max_unpacked=None`; l'altro
>   sostituto prende già `**kwargs`.
> - ✅ **Verdi**:
>   - API: `api backup-restore` **161** (12:24) e `api backup-restore-apply` **170**; `api sync` uscita 0. Slot
>     liberato alle 12:24:26;
>   - servizi (12:24-12:28): `backup-checks` 93, `backup-staging` 168, `config-audit` 156, `config-env-example` 38,
>     `profile-defaults` 112, `accounts-checks` 76, `email-checks` 87, `backup-secure` 77;
>   - utils (12:28-12:30): `backup-cli-restore` 107, `backup-cli` 102, `backup-cli-secure` 66;
>   - Vitest (12:32): la cartella `backup` più `GlobalSettingsTab.test.ts`, **982 su 982**.
> - ✅ **Doc** (12:32-12:34): `mkdocs build` strict (66 s), `check-links`, gate 63.
> - ✅ **Controlli statici**: ruff e black su tutti i 15 file Python cambiati; prettier sui file del frontend;
>   `git diff --check` pulito. Porta 6187 libera.
> - **Per H** (revisione dopo l'entrata):
>   - il lettore non passa da `profile_default`: segue il limite di caricamento, che ci passa;
>   - la voce nella mappa di `test_config_audit.py`;
>   - `developer/architecture/settings.md` l.79-84: inoltrato al coordinatore.
> - **Backlog**: B-35 ✅, B-40 ✅ (le righe di B in «What It Lists»).
> - **Merge di dev in B-35** (coordinatore, 12:36): dev `9e8f6e8dc` dentro `32739feaa`, con 3 conflitti di doc
>   risolti tenendo entrambe le parti:
>   - `configuration.en.md`, la riga `LIBREFOLIO_PROFILE`: quella di dev più la mia frase, verificata contro la base
>     (stage 1);
>   - `settings.en.md`, «What It Lists»: «Test mode» di H, poi le tre righe di B, nell'ordine del `CONFIG_CHECKS`
>     fuso;
>   - `security.md`, la riga `i18n_key`: il 4 → 7 di dev più il mio nine → thirteen.
>   Cancelli sulla revisione combinata (12:37-12:42): `services config-audit` 204, `backup-checks` 93, `mkdocs build`
>   strict (123 s), `check-links`, gate 63. Merge `d7efb5805` → dev `9fafc79b5`; CHANGELOG 🔒 dentro.

### B-39 — formule nei CSV esportati, con un ritorno esatto (2026-10-17, 12:43-13:09) — ✅ 🧊 FROZEN (checkpoint delle 13:09)

> **B-35 entrato** (coordinatore, 12:43): merge `d7efb5805` → dev `9fafc79b5`, CHANGELOG 🔒; HEAD portata in avanti
> a `e3ef5c9a6`. Via a B-39.
>
> **Stato reale** (12:44-12:52):
> - `series_export.stream_rows_as_csv` scrive le celle così come sono: un testo che comincia con `=` diventa una
>   formula in un foglio di calcolo. Le uniche colonne di testo libero sono le `notes` degli eventi; le altre sono
>   codici, date e numeri.
> - **L'export degli eventi è fatto per tornare indietro**: `EventDataImportModal` legge `value` come alias di `amount`
>   e legge `notes`. Un `'` aggiunto solo all'export resterebbe nella nota dopo una reimportazione.
> - `CsvColumnDef` ha già un `parse` per colonna, che `CsvEditor` chiama sulle celle non vuote e senza spazi ai bordi.
> - L'altro scrittore di CSV (`brim_provider.write_combined_csv`) non è di B: contiene i dati del broker dell'utente
>   stesso, quindi al più un danno a sé. Solo una nota.
>
> **Contratto** (approvato dal coordinatore, 12:55, con il permesso di scrivere sul modale per l'hook di `notes`;
> rivede X):
> 1. All'export, un testo che corrisponde a `'*[=+\-@\t\r]` all'inizio riceve un `'` in più, salvo un numero puro
>    (`[+-]?[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?`), di qualunque tipo. Il JSON non cambia.
> 2. All'import, `notes` toglie esattamente un `'` iniziale davanti a quel motivo (`unescapeFormulaText`, nello script
>    di modulo del modale). Il ritorno è esatto, anche per una nota che comincia già con apostrofi (`'=x` →
>    `''=x` → `'=x`).
>
> - **Codice pronto** in `b39-wip/apply_b39.py`: 5 operazioni in 2 file; ruff, black e prettier puliti.
>   Prova a mano sulla copia emessa: `=1+1` → `'=1+1`, `'=x` → `''=x`, `-1.5` resta, `a = b` resta.
> - **Rossi in scrittura**:
>   - TA-S: un file nuovo, `test_series_export_csv.py`, con la sua voce `services series-export-csv`;
>   - TA-F: i casi di Vitest (finiti in `DataEditor.test.ts`, vedi sotto);
>   - docs-writer: le pagine della doc.
> - ✅ **Rossi scritti** (12:44-12:54):
>   - **TA-S**: `test_series_export_csv.py`, nuovo, registrato come `services series-export-csv` (isolamento pure):
>     6 funzioni e 30 casi (11 rossi, 19 guardie). Asserisce sulle celle rilette da `csv.reader`; un valore non di
>     testo il cui testo sembra una formula viene scappato anche lui.
>   - **TA-F**: 22 casi in `DataEditor.test.ts`, non in un file nuovo. Quel file è già registrato, e ha già il blocco
>     del modale degli eventi; un file nuovo avrebbe chiesto una riga in `_frontend_utility.py`. I casi: la funzione,
>     la tabella del ritorno (con anche `'\r=1`), e il modale che reimporta tre note.
>   - **Docs-writer**:
>     - `data-editor.md` (dev) l.123-128;
>     - `user/assets/detail/data-editor.en.md` l.80, perché `events.en.md` non descrive il formato (debito di
>       traduzione);
>     - `security.md` «🧼 Output Escaping», l.2256-2267.
> - **⚠️ Fuori pista — gli apostrofi già presenti (12:58)**: una nota che comincia già con `'=x` sarebbe tornata
>   `=x`. L'export scappa ora anche una serie di apostrofi davanti a un carattere di formula (`'*[=+\-@\t\r]`, `'=x`
>   → `''=x`), e l'import ne toglie esattamente uno: il ritorno è esatto per ogni testo.
> - ✅ **Rossi** (corsia 6187, 12:54-12:55): `services series-export-csv` **11 falliti** e 19 passati; Vitest
>   `DataEditor.test.ts` **22 falliti** e 88 passati.
> - ✅ **Codice applicato** (12:55:44): 5 operazioni in 2 file.
>   - `series_export.py`: `_FORMULA_LIKE`, `_PLAIN_NUMBER`, `_csv_cell`;
>   - `EventDataImportModal.svelte`: `<script module>` con `unescapeFormulaText`, e `parse:` su `notes`.
>   Ruff, black e prettier puliti.
> - ✅ **Verdi**: `services series-export-csv` 30; Vitest su `ui/data-editor/` e `components/assets/`, **1560 su
>   1560** in 38 file.
> - ✅ **Doc** (12:57-12:59): `mkdocs build` strict (70 s), `check-links`, gate 63. Controlli statici puliti, porta
>   6187 libera.
> - ✅ **Slot 2** (coordinatore, 13:04), regressione API:
>   - `api backup-export-extras` **8 passati** (13:04-13:07; il frontend ricostruito, svelte-check 0 errori con lo
>     script di modulo del modale);
>   - `api asset-prices-export` **5 passati**.
>   Porta 6187 libera.
> - Proposta di CHANGELOG 🔒 (docs-writer): «CSV exports are safe to open in a spreadsheet…».
> - **Backlog**: B-39 ✅.

### B-36 + B-37 — nomi quotati e `trusted_schema` spento anche nelle correzioni e nell'upgrade (2026-10-17, 13:09-13:33) — ✅ 🧊 FROZEN (checkpoint delle 13:33)

> **B-39 entrato** (coordinatore, 13:09): `c8fc32bfa` → dev `25d00f192`, CHANGELOG 🔒 `bbfb76e38`; HEAD portata in
> avanti. Via a B-36 + B-37; rivede H.
> - Permesso di scrittura (11:59) su `db/post_migration/__init__.py` e su `env.py` di Alembic, solo per le virgolette e
>   per `trusted_schema=OFF`.
>
> **Stato reale** (13:00-13:10):
> - Solo `_row_counts` costruisce SQL con nomi che vengono dall'archivio. `autoincrement.py` usa la tupla costante
>   `AUTOINCREMENT_TABLES`; la connessione di `_backup` scrive un file `.bak` nuovo.
> - Il test di B-28 «every connection … trusted_schema off first» lascia fuori apposta le correzioni e l'upgrade (§2):
>   «not recorded».
> - `security.md` l.1821-1827 lo dice.
>
> **Contratto** (`b36-37-contract.md`):
> 1. **B-36**: un `_quoted()` locale, che raddoppia `"`, in `_row_counts`.
> 2. **B-37**: `PRAGMA trusted_schema=OFF` subito dopo la connessione di `run_post_migration_fixes`, dentro il `try`,
>    anche sul database vivo: lo schema di LibreFolio contiene solo tabelle e indici, e le funzioni predefinite di
>    SQLite sono innocue.
> 3. **B-37**: un listener `connect` (`_schema_untrusted`) in `env.py`, registrato prima di `connectable.connect()`, per
>    ogni URL.
>
> - **Codice pronto** in `b36-wip/apply_b36.py`: 5 operazioni in 2 file; ruff e black puliti sulla copia emessa.
> - **Rossi in scrittura** (TA-S):
>   - `test_post_migration.py` (`db post-migration`);
>   - il registratore di (l) esteso a `post_migration` (`services backup-staging`);
>   - un controllo statico di `env.py` (`utils dev-cli-db-path`).
>   Doc: `security.md` l.1821-1827 (docs-writer).
> - ✅ **Rossi scritti** (TA-S, 13:10-13:15):
>   - `test_post_migration.py` §17: un 1.1 portato all'ultima migrazione (correzione autoincrement pendente), più le
>     tabelle `x"y` e `a" WHERE 1 --`, che oggi diventa `FROM "a" WHERE 1 --"` («no such table: a»). Una spia su
>     `_row_counts`;
>   - il registratore (l) di `test_backup_staging.py` registra anche `post_migration`; la copia `.bak` resta fuori per il
>     filtro del percorso;
>   - DBP-j in `test_dev_cli_db_path.py`: un controllo AST di `env.py`. Un'esecuzione vera di Alembic non può mostrare
>     il pragma: è uno stato della connessione, dentro un processo che finisce.
> - ✅ **Rossi** (corsia 6187, 13:15-13:19): `db post-migration` **1 fallito** (44 passati), `services backup-staging`
>   **1 fallito** (167), `utils dev-cli-db-path` **2 falliti** (15). Sono esattamente i 4 attesi.
> - ✅ **Patch applicata** (13:19:19): 5 operazioni in 2 file; ruff e black puliti.
> - ✅ **Verdi** (13:19-13:23):
>   - `db`: `post-migration` 45, `post-migration-event-types` 36, `post-migration-orphan-pairs` 47,
>     `autoincrement-schema` 4, `migration-008` 23, `migration-009` 11;
>   - `services backup-staging` 168, che comprende l'upgrade vero in un processo a parte;
>   - utils: `dev-cli-db-path` 17, `backup-cli-restore` 107.
>   Porta libera.
> - ✅ **Doc** (13:30-13:32): `security.md` l.1821-1832 e il paragrafo dei test l.1838-1841 (docs-writer); `mkdocs
>   build` strict (61 s), `check-links`, gate 63.
> - ✅ **Controlli statici**: ruff e black sui 7 file Python, tranne `_backend_db.py`, che era già sporco prima di B (tre
>   `PLC0415`, e black che lo riformatterebbe), con una sola riga di desc aggiunta. `git diff --check` pulito.
> - **Per H**:
>   - le due modifiche nei suoi file (`post_migration/__init__.py`, `env.py`);
>   - `database/index.md` l.203-204, che potrebbe dire «with `trusted_schema` off first» (nota del docs-writer).
> - **Backlog**: B-36 ✅, B-37 ✅.

### B-38 — i file dei segreti letti da root: regolari, mai attraverso un link nella cartella dei dati (2026-10-17, 13:36-13:58) — ✅ 🧊 FROZEN (checkpoint delle 13:58)

> **B-36/B-37 entrati** (coordinatore, 13:39): `2eff9e623` più il merge `05d1dc76a` → dev `d1976bca8`. Un conflitto
> nella desc del runner `post-migration` (Z-28), risolto dal coordinatore tenendo entrambe le frasi. HEAD portata in
> avanti.
>
> - **⚠️ Fuori pista — Kubernetes (13:36)**: rifiutare ogni link con `O_NOFOLLOW`, come concordato, romperebbe
>   Kubernetes, che monta ogni segreto attraverso un symlink (`/etc/secret/pw` → `..data/pw`). Proposta di rifinitura,
>   **approvata dal coordinatore (13:40, opzione a)**:
>   - ovunque, un file regolare aperto con `O_NONBLOCK`: una FIFO non blocca più il comando, e una cartella o un
>     dispositivo non vengono letti;
>   - i link sono rifiutati solo da root e solo dentro la cartella dei dati;
>   - la guida sposta la chiave fuori dalla cartella dei dati;
>   - la corsa residua va nella riga H-47 di H.
> - **Altri due punti miei** (13:42):
>   - il controllo percorre **ogni componente**, dalla cartella dei dati in giù: un `backups` sostituito da un link verso
>     `/root` sarebbe sfuggito controllando solo l'ultimo componente;
>   - la guida usa **`/root`** del container, non `/tmp`: in `/tmp` l'utente del server può creare il nome per primo
>     come link, e `docker compose cp` ci scriverebbe attraverso.
> - **Contratto**: `b38-contract.md`. Il codice: `_secret_path(args, path, label)` prima di ogni `read_secret_file`
>   della CLI, con `_data_dir_setting` (come `_decrypt_as_owner`) e `_link_inside`. Le eccezioni sono
>   `SecretFileError`, quindi i ❌ restano quelli di oggi (`password_unreadable`, `instance_key_unreadable`).
> - **Codice pronto** in `b38-wip/apply_b38.py`: 4 operazioni, ruff e black puliti. Prova a mano sulla copia emessa:
>   - una FIFO e una cartella sono rifiutate subito;
>   - un file normale passa, e uno mancante è lasciato a `read_secret_file`;
>   - il link di una cartella madre dentro i dati viene preso, fuori no.
> - **Rossi in scrittura** (TA-E, sezione (n) di `test_backup_cli_secure.py`); doc (docs-writer): la guida, `cli_tools`
>   e `security.md`.
> - ✅ **Rossi scritti** (TA-E, 13:42-13:50): sezione (n), 3 funzioni e 40 casi sui 4 comandi che leggono un segreto
>   (`decrypt` compreso).
>   - Una FIFO o una cartella, da root finto e non: 16 casi rossi. Un watchdog di 10 s apre la FIFO, così il run non
>     resta appeso.
>   - Un link dentro i dati, su `backups/key` o su `backups/` stesso: 8 rossi. Il bersaglio non viene mai aperto.
>   - 16 guardie.
>   - Due vincoli fissati: il controllo dei link viene **prima** di ogni apertura, e lavora sul percorso **come è
>     dato**, non risolto.
>   - Trovato da TA-E: oggi `create` e `inspect` rifiutano un `backups/` che è un link solo **dopo** che root ha già
>     letto il segreto attraverso quel link.
> - ✅ **Doc scritta** (docs-writer, 13:44):
>   - `backup_restore.en.md` l.308 e l.320-328: la chiave passa da `/root` del container;
>   - `cli_tools.en.md` l.363-364, 378, 564, 569: la regola detta una volta sola (debito di traduzione);
>   - `security.md` l.856-870: il punto «Secret files read as root», con il residuo H-47.
>   - Da passare ad H: «The Instance Key» in `security.md` l.706-708 dice ancora che B-18 è nel backlog.
> - ✅ **Rosso** (corsia 6187, 13:50-13:52): `utils backup-cli-secure` **24 falliti** e 82 passati, come previsto.
> - ✅ **Patch applicata** (13:52:44): 4 operazioni in `scripts/backup_cli.py`; ruff e black puliti.
> - ✅ **Verdi** (13:52-13:54): `backup-cli-secure` **106** (37 s: nessuna attesa su una FIFO), `backup-cli-restore`
>   107, `backup-cli` 102.
> - ✅ **Doc** (13:55-13:57): `mkdocs build` strict (54 s), `check-links`, gate 63. Controlli statici puliti, porta
>   6187 libera.
> - **Backlog**: B-38 ✅. Il residuo (due aperture) è nella riga H-47 di H.

### B-34 — la causa giusta quando l'istanza non ha ancora una chiave, e le frasi della doc (2026-10-17, 14:00-14:10) — ✅ 🧊 FROZEN (checkpoint delle 14:10)

> **B-38 entrato** (coordinatore, 14:00): `1ed071c2f` → dev `c2a09b960`, CHANGELOG 🔒 `9b02120a7`; HEAD portata in
> avanti. La correzione di `security.md` l.706-708 e il residuo H-47 vanno ad H. Via a B-34.
>
> - **LOW-1 di H**:
>   - Su un'istanza senza chiave, dove la verifica non può crearla, `instance_key_status()` dice `not_created` e
>     `problem=None`, e la riga D2 accusa la chiave data.
>   - Cura: il ramo dell'eccezione prende anche `not_created`, e la riga dice «`<path>`: there is no instance key yet,
>     and it could not be created».
>   - Patch: `b34-wip/apply_b34.py`, 1 operazione; ruff e black puliti.
> - **Doc**:
>   - in `cli_tools`, un vecchio `LIBREFOLIO_INSTANCE_KEY` va nel file così com'è, spazi compresi;
>   - la riga dell'eccezione copre anche il caso nuovo;
>   - il `chmod 600` non serve più: B-38 ha spostato la chiave in `/root`. Da controllare che nessuna pagina la metta
>     ancora in `backups/`.
> - **Rossi in scrittura** (TA-E, accanto a c7); doc (docs-writer).
> - ✅ **Rosso scritto** (TA-E): in `test_backup_cli_restore.py`, dopo c7,
>   `test_when_this_instance_has_no_key_yet_and_none_can_be_created_it_is_said_instead_of_blaming_the_key_given`.
>   - Un'istanza senza chiave, con `secrets/` a 0o500 (un aiuto rimette i permessi nel `finally`), e una chiave data.
>   - Atteso: la riga «This instance's own key cannot be used…», con `there is no instance key yet, and it could not be
>     created`; mai la riga che accusa la chiave data.
>   - Desc del runner (`_backend_utils.py`, `backup-cli-restore`) allungata, in aggiunta.
> - ✅ **Rosso** (corsia 6187): `utils backup-cli-restore` **1 fallito** e 107 passati, esattamente il caso nuovo
>   (`files/logs/b34_red.log`).
> - ✅ **Patch applicata** (14:03:03): 1 operazione in `_print_given_key` di `scripts/backup_cli.py`; ruff e black
>   puliti.
> - ✅ **Verdi**: `backup-cli-restore` **108**, `backup-cli-secure` **106**; porta 6187 libera.
> - ✅ **Doc** (docs-writer, più una frase mia):
>   - `cli_tools.en.md` l.563: il valore di un vecchio `LIBREFOLIO_INSTANCE_KEY` va nel file «as written in the
>     variable, spaces included»; il file di `LIBREFOLIO_INSTANCE_KEY_FILE` «as it is»;
>   - `cli_tools.en.md` l.568: la riga dell'eccezione copre anche un'istanza senza chiave, con il testo del problema;
>   - il secondo appunto di H (`chmod 600` sulla chiave vecchia in `backups/`) non vale più alla lettera: dopo B-38 la
>     chiave non passa più dai dati, e nessuna pagina la mette in `backups/` o in `LibreFolio-data/` (grep). Il senso
>     vale ancora sull'host: in `backup_restore.en.md` l.320 il file `old-instance.key` accanto a `docker-compose.yml`
>     è «kept private (`chmod 600 old-instance.key`)», come il file della password a l.96. Pagina solo inglese.
>   - Traduzioni di `cli_tools`: debito vero (due frasi cambiate di senso), nessun `translate-stamp`, come in B-38.
> - ✅ **Controlli** (14:05-14:10, ripetuti dopo la frase di l.320): `mkdocs build` strict, `check-links`, gate 63; ruff e black puliti sui 3 file
>   Python; `git diff --check` pulito; porta 6187 libera.
> - **Backlog**: B-34 ✅. CHANGELOG: nessuna voce (un messaggio della CLI più preciso, dentro B-18 della stessa
>   release).

### B-41 + B-42 — l'esito anonimo controlla il biglietto prima dello stato, e un file del biglietto rotto si registra una volta (2026-10-17, 14:10-14:56) — ✅ 🧊 FROZEN (checkpoint delle 14:56)

> **B-34 entrato** (coordinatore, 14:10): `731337a5a` → dev `202849800`; HEAD portata in avanti. Via a B-41 nella 1.3
> («cheap: check the ticket before reading the state»). Dopo, se B-33 e B7 aspettano ancora il developer, il
> coordinatore trova lavoro in un'altra sezione.
>
> **Stato reale** (14:10-14:20):
> - `get_restore_outcome` (`restore.py:443-447`) legge lo stato (`read_restore`) prima di `outcome.read_outcome`. Con uno
>   stato che il file system rifiuta, `_read_state` registra un errore a ogni chiamata, qualunque biglietto: nessuno,
>   malformato, 43 caratteri qualsiasi.
> - `read_outcome` usa lo stato solo dopo forma, cartella, registro, impronta e scadenza: basta passargli il modo di
>   leggerlo.
> - **⚠️ Fuori pista — B-42**: `_read_record` registra un errore a ogni chiamata con un biglietto ben formato quando il
>   file del biglietto è rotto (illeggibile, un link, spazzatura, troppo grande). Stessa classe di rumore, dal B5c.
>   Chiesto al coordinatore; **dentro questo lotto** (coordinatore, 14:24).
> - **Nota per B-33** (nella sua riga, coordinatore 14:24): con uno stato illeggibile dopo un riavvio, il ripiego della
>   pagina su `/status` riceve 500, che `readStatusWithSession` prende per «server giù». L'overlay interroga ogni secondo
>   per sempre, senza dire perché.
>
> **Contratto** (`b41-contract.md`):
> 1. **B-41**: `read_outcome(ticket, state, …)` accetta come `state` anche la funzione che lo legge, chiamata una volta
>    e solo per il biglietto di un riavvio non scaduto. La rotta le passa `lambda: _state_for_outcome(data_dir)`, la
>    lettura indulgente di oggi.
> 2. **B-42**: `_report` registra un errore la prima volta per cartella dati, poi `debug` finché dura lo stesso errore;
>    `_forget` lo dimentica quando il file viene scritto, tolto o letto. Un lock rende esatto il controllo.
> 3. Invariati: ogni risposta (la sola 404), il titolare del biglietto giusto (guardia b5), le rotte dell'admin.
>
> - **Codice pronto** in `b41-wip/apply_b41.py`: 11 operazioni in 2 file; ruff e black puliti sulla copia emessa.
>   Prova a mano (`probe_b41.py`) sulla copia emessa: 15/15.
> - **Rossi in scrittura** (TA-B41): (j) B-41 in `test_backup_restore_apply.py`; (c) B-41 e B-42 in
>   `test_backup_outcome.py`. Doc (DW-B41): `security.md`, tre punti.
> - ✅ **Doc scritta** (DW-B41, 14:30): `security.md`
>   - l.2052-2055, «What cannot be read is not none»: l'esito legge lo stato solo per il biglietto di un riavvio non
>     scaduto (lot B-41);
>   - l.2168-2172, «Kept as a hash.»: un file del biglietto illeggibile o non valido, un errore una volta per cartella
>     dati, poi `debug` finché dura lo stesso errore (lot B-42);
>   - l.2186-2187, «One answer for every miss.»: il biglietto prima dello stato (lot B-41).
>   - Pagina solo inglese (`developer/`): nessun debito di traduzione.
> - ✅ **Rossi scritti** (TA-B41, 14:15-14:35):
>   - API (j), dopo b5 (b5 invariata): `test_a_ticket_that_does_not_open_the_outcome_never_reads_the_state_nor_logs_it`.
>     - I 15 casi di `NOT_OPENING` decisi dal biglietto: tutti tranne `no-restore` e `a-restore-of-another-stage`.
>       Esclusi per id, con una barriera che li trova in `NOT_OPENING`. Per i 3 modi di `unreadable`: 45 casi.
>     - Asserzioni: la sola 404; il file dello stato mai aperto; nessun evento «The state of the restore cannot be read».
>     - Barriera: dopo la risposta, `read_restore` a mano è rifiutato e registrato, quindi `capture_logs` sente il
>       logger di `apply`.
>   - Servizi (c), B-41: il lettore chiamato una volta per il biglietto giusto, 3 casi (rosso). Guardie, il lettore mai
>     chiamato: 32 casi in 4 test (`NOT_THE_TICKET`, `UNTRUSTED_FILES`, senza file, scaduto).
>   - Servizi (g), B-42, 32 casi rossi in 4 test, su 5 modi di rompere il file (non un biglietto, oltre 4096 byte, un
>     link, modo 000, EIO):
>     - letto 3 volte: un solo errore;
>     - di nuovo un errore dopo una scrittura, una lettura valida, una rimozione, o un file trovato mancante (20 casi);
>     - un errore diverso conta come nuovo, anche tornando al primo (2 sequenze);
>     - una memoria per cartella dati.
>   - (e): il biglietto vero presentato al file rotto in 4 modi, mai nei log.
>   - Desc dei runner, in aggiunta: `backup-restore-apply` e `backup-outcome`.
> - ✅ **Rosso dei servizi** (corsia 6187, 14:38): `services backup-outcome` **35 falliti** e 129 passati, esattamente i
>   3 + 32 attesi: l'`AttributeError` del lettore, e gli errori ripetuti di B-42 (`files/logs/b41_red_services.log`).
> - ⏳ Rosso dell'API: aspetta uno slot breve (chiesto alle 14:36).
> - ✅ **Rosso dell'API** (slot del coordinatore, 14:38-14:47): `api backup-restore-apply` **45 falliti** e 170
>   passati, esattamente i casi nuovi: «the state file never opened for a ticket that does not open the outcome»
>   (`files/logs/b41_red_api.log`).
>   - **⚠️ Fuori pista**: 8 minuti invece di 1-2. I merge di dev avevano reso vecchia la build di debug del frontend
>     della corsia, quindi il runner l'ha rifatta (vite) prima del server. Detto al coordinatore durante lo slot.
> - ✅ **Patch applicata** (14:47:00): 11 operazioni in 2 file; ruff e black puliti.
> - ✅ **Verdi** (14:47-14:49): `api backup-restore-apply` **215** (170 + 45), `services backup-outcome` **164**
>   (129 + 35), `services backup-apply` **255** (regressione: chi chiama `read_outcome` con uno stato). Slot liberato
>   alle 14:49.
> - ✅ **Controlli** (14:50-14:54):
>   - `schemas openapi-client-text` 78: la docstring della rotta finisce nella descrizione OpenAPI, senza `${` né `\`;
>   - ruff e black puliti sui 6 file Python; `git diff --check` pulito;
>   - `lint --dead-code --scope backend`: nessun simbolo nuovo; l'uscita 1 viene da voci di altri pacchetti, già
>     presenti;
>   - client generato: ignorato da git, niente da fare;
>   - `mkdocs build` strict, `check-links`, gate 63; porta 6187 libera.
> - **Una precisazione mia nella doc**: `_REPORTED` è memoria di processo. Con più worker ognuno registra il suo errore
>   una volta: «once per data directory in each server process».
> - **Backlog**: B-41 ✅, B-42 ✅; la nota della pagina è nella riga B-33. CHANGELOG: una riga 🔒 proposta nell'handoff
>   (meno rumore nei log per una rotta anonima).

### X-R71 (per X) — il caricamento manuale dei prezzi, tutto o niente; più le due note di H su B-36/B-37 (2026-10-17, 14:58-15:52) — ✅ 🧊 FROZEN (checkpoint delle 15:52)

> **Assegnazione** (coordinatore, 14:58, dalla sezione di X): «a manual price upload (`POST /assets/prices` →
> `price_store.bulk_upsert_prices`, MANUAL) checks the currency asset by asset. When asset 3 of 5 has a currency
> mismatch, assets 1–2 are already written before the refusal. The upload must be all or nothing: every check before the
> first write, as X-R65 now does for dates.» File: `api/v1/assets/prices.py`, `services/assets/price_store.py`; rivede X.
> Origine: la nota di Z per X nel piano 06, X-R65 passo 6.
>
> **Analisi** (14:58-15:10, sola lettura; `files/xr71-analysis.md`):
> - Una chiamata manuale: le cifre (`ValueError` → 400, solo il primo asset) e le date (X-R65, 422) prima di ogni
>   istruzione. Poi, asset per asset: lettura, valuta, scrittura a fette di 1000 date con un `commit` per fetta
>   (`:400`), voluto per il lock di scrittura di SQLite. Il controllo della valuta (`:251-259`) rifiuta tutto **dopo**
>   che gli asset precedenti sono già scritti: è l'unico rifiuto dell'intera chiamata che viene dopo una scrittura.
> - Morbidi per scelta: l'asset che non esiste («Asset N not found») e il controllo OHLC, data per data (W-B52 per la
>   sentinella).
> - **Il refresh dei fornitori non c'entra**: un asset per chiamata, controllato prima della sua prima fetta, e il
>   refresh scarta da sé i punti in un'altra valuta. La web app manda un asset e nessuna valuta: lo vede solo un client
>   dell'API.
> - Scartata: una transazione unica per la chiamata manuale, come gli eventi. Riporterebbe il lock lungo che le fette
>   evitano.
> - **Fratello per X**: l'editor conta come salvata ogni riga mandata (`AssetDataEditorSection.svelte:316`) e non legge
>   `results[].message`. Una data saltata dal controllo OHLC risulta salvata. Va ad X, nella sua X-R46.
>
> **Decisioni** (coordinatore, 15:15): **GO**. D1 il 422 codificato `price_currency_mismatch`; D2 (il rifiuto delle
> cifre) e D3 (gli asset sconosciuti) invariati. Il permesso di scrittura copre `schemas/prices.py`, solo la riga della
> descrizione. X aggiunge X-R71 (proprietario B) e il fratello al backlog; il diario sta qui. Nessun altro worktree ha i
> tre file di test né i tre file di prodotto.
>
> **Contratto** (`files/xr71-contract.md`):
> - `price_store.PriceCurrencyMismatchError(items, count)`, un'`Exception` come `DateOutOfRangeError`;
>   `price_currency_mismatch_detail()` → `{code, message, items (≤ 10), count}`.
> - `_reject_currency_mismatches(session, data)`, solo per MANUAL, dopo le date e prima del ciclo. Legge le valute di
>   tutti gli asset a fette di 500, nient'altro sulla sessione. Una voce per elemento in difetto: `asset_id`,
>   `expected`, `found` (nell'ordine in cui compaiono), `dates` (≤ 10, in ordine di richiesta). Un asset sconosciuto
>   resta al ciclo.
> - La rotta: 422 prima del `ValueError` generico. Il controllo nel ciclo resta: i fornitori come oggi; per MANUAL una
>   rete di sicurezza.
>
> - **Codice pronto** in `xr71-wip/apply_xr71.py`: 8 operazioni in 3 file. ruff (C416 corretto: `update(rows.all())`) e
>   black puliti sulla copia emessa. Prova a mano `probe_xr71.py` su una sessione finta: 9/9.
> - **Rossi in scrittura** (TA-XR71): `api prices-currency-coherence`, `api assets-price` (15-16),
>   `services asset-source-guards`, la guardia di `bulk-writes-chunked`.
> - ✅ **Rossi scritti** (TA-XR71, 15:05-15:18):
>   - `api prices-currency-coherence`: il caricamento di A (pulito), B (in difetto) e C (pulito) è rifiutato con 422 e
>     non scrive nessun asset; ogni asset in difetto nominato, in ordine, con `found` nell'ordine in cui compaiono.
>     G.5.1, G.5.2 e G.5.5 passano a 422, G.5.5 con 10 date e `count` 12. Guardie: G.5.3, G.5.4, e un asset sconosciuto
>     fra due puliti (200, «Asset N not found», gli altri scritti: D3).
>   - `api assets-price`: i test 15-16 diventano `…_rejects_422`.
>   - `services asset-source-guards`:
>     - il rifiuto arriva dopo una sola lettura, nient'altro sulla sessione e niente scritto;
>     - i numeri su 12 asset veri (fixture `xr71_assets`), con un asset sconosciuto in mezzo, non contato;
>     - guardie: il fornitore ha ancora il suo `ValueError`; le date sono controllate prima delle valute.
>   - `bulk-writes-chunked:875`: l'esempio diventa il rifiuto delle cifre.
> - ✅ **Doc** (DW-XR71, 15:10-15:16, più tre ritocchi miei):
>   - `developer/backend/assets/architecture.md`: un rimando dopo il controllo delle cifre (l.221-223); la sezione
>     nuova `#price-currency-coherence` dopo quella delle date; la riga della rotta; e, mio, la riga di `price_store.py`
>     nella tabella dei moduli;
>   - `developer/frontend/components/core-ui/data-editor.md` l.82: diceva «HTTP 400» per un prezzo in un'altra
>     valuta; ora 422 `price_currency_mismatch` per i prezzi, 400 per gli eventi;
>   - da DW, aggiunto alla patch: il commento di `_reject_prices_over_the_limit` («as it does a currency mismatch»),
>     operazione 1b. Patch a 9 operazioni.
>   - Da DW, **per X** (di prima, non mio): il commento di `refresh.py:497-500` dice che l'upsert rifiuterebbe con
>     `HTTPException(400)`. Era già sbagliato: sotto la chiave di un fornitore il refresh prende un `ValueError`.
>   - Pagine solo inglesi: nessun debito di traduzione. `mkdocs build` stretto, `check-links` e il gate dei link (63)
>     verdi alle 15:16-15:18.
> - ✅ **Rossi dei servizi** (corsia 6187, 15:18-15:19): `services asset-source-guards` **2 falliti** e 41 passati,
>   esattamente i due nuovi; la guardia di `bulk-writes-chunked` 42 passati.
> - ✅ **Rossi dell'API** (slot del coordinatore, 15:20-15:29):
>   - `api prices-currency-coherence`: **5 falliti** e 3 passati;
>   - `api assets-price`: **2 falliti** e 20 passati.
>   - Esattamente i casi nuovi (`files/logs/xr71_red_*.log`).
>   - **⚠️ Fuori pista**: il primo rosso ha rifatto la build di debug del frontend della corsia. Il merge di B-41 in
>     dev aveva portato modifiche al frontend di altri: avevo detto al coordinatore che la build era fresca, e non lo
>     era.
> - ✅ **Patch applicata** (15:29:22): 9 operazioni in 3 file; ruff e black puliti; `import backend.app.main` riuscito.
> - ✅ **Verdi dell'API** (15:36-15:42): `api prices-currency-coherence` **8**, `api assets-price` **22**.
>   - **⚠️ Fuori pista**: il verde ha aspettato dalle 15:29 alle 15:36: lo slot E2E di Y ha portato il carico a
>     85-106. Slot liberato alle 15:42.
> - ✅ **Regressioni leggere** (15:42-15:47), tutte verdi:
>   - `services asset-source-guards` 43, `bulk-writes-chunked` 42, `asset-digit-limits` 79;
>   - `services asset-source` 61, `asset-source-refresh` 18, `current-price-storable` 27, `range-ceiling` 57;
>   - `schemas openapi-client-text` 78: la nuova descrizione di `FAPricePoint.currency` e la docstring della rotta.
>   - Porta 6187 libera.
> - ✅ **Testi del runner** (dopo i verdi, solo testo): il `print_info` e la desc di `prices-currency-coherence` dicevano
>   «hard-400»; il commento d'isolamento di `asset-source-guards` ora conta anche i 12 asset di X-R71. Il runner si
>   carica.
> - ✅ **Controlli** (15:48-15:50): ruff e black puliti sui 10 file Python; `git diff --check` pulito.
> - **Backlog**: X aggiunge X-R71 (proprietario B) e il fratello dell'editor nella sua sezione; io non la tocco. Nel
>   backlog, la mia sola modifica è la frase di B-37 e la riga B-36 (le note di H). CHANGELOG: la riga 🐛 proposta
>   nell'handoff.
>
> **Le due note di H su B-36/B-37** (coordinatore, 14:54; commit a parte, approvato alle 15:15):
> - **La frase di B-37** nel backlog («nessuna funzione dell'app è registrata lì») era sbagliata per il motore di
>   Alembic: SQLAlchemy (dialetto pysqlite, 2.0.52) registra `regexp` e `floor` in Python a ogni connessione. Il
>   listener di `env.py` è quindi una cura vera. Riscritta. Il piano 07 e `security.md` non ripetono l'errore: il
>   piano dice solo che le funzioni predefinite di SQLite sono innocue, ed è vero per la connessione `sqlite3` delle
>   correzioni.
> - **Due `_quoted` con contratti diversi**: `snapshot._quoted` diventa `_identifier`, che dà l'identificatore intero
>   fra virgolette, come `post_migration._quoted`; il suo unico chiamante produce lo stesso SQL. `post_migration` non
>   è toccato. Anche la riga B-36 del backlog nomina il nuovo nome.
> - ✅ Applicata alle 15:07:05 (`h37-wip/apply_h37.py`, 4 operazioni in 2 file); ruff e black puliti. Verdi, i file che
>   usano `snapshot`: `services backup-archive` 155 (1 saltato, come prima), `backup-jobs` 69, `backup-secure` 77,
>   `backup-staging` 168. Porta 6187 libera.
>   - **⚠️ Fuori pista**: `services backup-snapshot` non esiste (nome della mia proposta del §8). I test di `snapshot`
>     sono in archive, jobs, secure e staging.

### B-43 + B-44 — una funzione sconosciuta nello schema dell'archivio diventa `database_damaged`; i testi di `trusted_schema` dopo H-51 (2026-10-17, 16:01-16:45) — ✅ 🧊 FROZEN (checkpoint delle 16:45)

> **Assegnazione** (coordinatore, 15:50, dalla revisione H-51 di H): (1) un archivio il cui CHECK o indice chiama una
> funzione sconosciuta si ferma come `sqlite3.OperationalError` grezzo, non come `StagingError`: l'API dice
> `stage_failed`, la CLI finisce probabilmente in un traceback. «Translate it into `database_damaged`, as
> `_refuse_foreign_objects` already does. Reds first; file it with an ID.» (2) Dopo l'ingresso di H-51: allineare la
> docstring di `env.py` («before anything else») e il punto «`trusted_schema` off on every connection to the copy» a
> `security.md#trusted-schema-server`.
>
> **Analisi** (15:52-16:15, in sola lettura mentre ero FROZEN; `files/b43-contract.md`):
> - **Misura su SQLite 3.54.0** (`b43-wip/sqlite_probe*.py`, log `b43_sqlite_probe*.log`):
>   - un'espressione di un indice o una colonna generata che chiama una funzione sconosciuta: `integrity_check` lancia
>     `OperationalError: unknown function`, anche in sola lettura → `describe_database()` (`mode=ro`) lo lascia uscire;
>   - un **CHECK**: in sola lettura SQLite **salta i vincoli `CHECK`** («ok», anche per un CHECK violato su una funzione
>     predefinita). La descrizione passa; fallisce il primo `integrity_check` in lettura e scrittura, quello di
>     `run_post_migration_fixes()._integrity_ok()`, e così pure una scrittura su quella tabella.
>   - La frase nuova di H in `#trusted-schema-server` («A `CHECK` or an index's expression … stops the check at the
>     `PRAGMA integrity_check` of `describe_database()`») è vera per indici e colonne generate, non per i CHECK.
> - **Cura**: in `_stage`, tutta la fase del database (da `_refuse_foreign_objects` al report) dentro
>   `except sqlite3.DatabaseError`, tranne `ProgrammingError` (un nostro difetto, che deve restare visibile) →
>   `StagingError("database_damaged")`. Nel log solo la classe e `sqlite_errorname` (regola di B-28). Gli
>   `StagingError` interni passano com'erano.
> - **B-44**: gli import di `env.py` caricano `db/session.py`, quindi sulle connessioni di Alembic l'ordine è il
>   listener di classe (H-51: `trusted_schema` spento per primo, `writable_schema=RESET` per ultimo), poi il dialetto
>   (`regexp`, `floor`), poi `_schema_untrusted`. Il suo «before anything else» non è mai stato letterale.
>
> **Decisioni** (coordinatore, 15:58): **GO** dopo l'ingresso di X-R71. La frase di H si corregge nella doc di B-43, e H
> la rivede. B-44 nello stesso checkpoint.
>
> **X-R71 entrato** (coordinatore, 16:01): combinato verde su `f0645ff98`, dev `1c7937984`, CHANGELOG 🐛 `e9746b959`;
> HEAD portata in avanti. Nel merge, il conflitto della desc del runner con MF-SEC9e risolto dal coordinatore: il testo
> di dev più la mia clausola sulla guardia del `ValueError`.
>
> - **Codice pronto**: `b43-wip/apply_b43.py` (2 operazioni in `staging.py`) e `apply_b44.py` (la docstring di `env.py`).
>   ruff e black puliti sulle copie emesse; si applicano su `e9746b959`.
> - **Rossi in scrittura** (TA-B43): `services backup-staging` (indice, colonna generata, CHECK; guardie: un CHECK su
>   `abs`, nessun nome di funzione nei log) e `utils backup-cli-restore` (nessun traceback). Doc (DW-B43): la frase di H,
>   le cause di `database_damaged`, il punto di B-44.
> - **Backlog**: B-43 e B-44 registrate nella sezione B.
> - ✅ **Rossi scritti** (TA-B43, 16:01-16:18), sezione (n) di `test_backup_staging.py` e (j) di
>   `test_backup_cli_restore.py`:
>   - **rossi**: indice, colonna generata (tipizzata, VIRTUAL), CHECK → `database_damaged`, senza resti. Il CHECK ha
>     una barriera: `describe_database()` risponde «ok». Il log ha un solo avviso, con la classe e `sqlite_errorname`,
>     e nessuna riga nomina la funzione. Più la CLI: `restore --dry-run` → ❌ `(database_damaged)`, uscita 1, nessun
>     traceback;
>   - **guardia**: un CHECK su `abs()` verificato come sempre.
>   - Il costruttore: un backup vero alla head, il database modificato con la funzione registrata e
>     `trusted_schema=ON`, il manifest aggiornato; precondizioni che non si confondono con il rosso.
> - ✅ **Doc** (DW-B43, 16:01-16:15, più due ritocchi miei):
>   - `security.md`: il punto nuovo «What the check cannot read.» (B-43), il punto di B-44 (sulle connessioni
>     dell'upgrade, prima il listener di classe, poi `_schema_untrusted` dopo il dialetto), la frase di H corretta in
>     `#trusted-schema-server`, la frase dei test.
>   - **⚠️ Fuori pista**: DW ha misurato che una colonna generata semplice passa `integrity_check`. Rimisurato
>     (`b43_sqlite_probe_generated.log`): falliscono solo una colonna VIRTUAL con un tipo dichiarato (INTEGER o TEXT) e
>     una `NOT NULL`; una non tipizzata o una STORED passano. Le due frasi ora lo dicono così.
>   - **⚠️ Fuori pista, la scoperta più grande di DW**: da H-51 alcuni schemi passano tutta la verifica e poi rompono il
>     server. Misurato con segnaposto deterministici (`b43_sqlite_probe_standins.log`):
>     - una colonna generata che chiama `regexp`, o un indice su `floor`, rendono illeggibile lo schema sulle
>       connessioni del server, e così tutte le connessioni falliscono;
>     - un `CHECK` o un `DEFAULT` passano anche la lettura con i segnaposto.
>   - **Decisione** (coordinatore, 16:25): la parte 1 dentro B-43, con due rossi in più. Il resto in backlog, dopo la
>     1.3: la parte 2 è **B-45**, il testo dell'archivio nel log dell'upgrade è **B-46**.
> - **Patch** `apply_b43.py`, ora a 4 operazioni. `_refuse_foreign_objects()` registra i segnaposto
>   (`_SERVER_FUNCTIONS`, `_register_server_functions`, `_stand_in`) e perde il suo `except`: ogni errore `sqlite3`
>   della fase passa dall'involucro di B-43, con un solo avviso. ruff e black puliti sulla copia emessa.
> - ✅ **I due rossi della parte 1** (TA-B43, seguito, 16:25-16:32):
>   - `regexp` in una colonna generata non tipizzata e `floor` in un indice → `database_damaged`, rifiutati prima che
>     `describe_database()` apra la copia (`never_described`);
>   - il test del log esteso ai due casi;
>   - una guardia: l'indice di LibreFolio su `lower()` si legge con i segnaposto, e il suo backup si verifica come
>     sempre;
>   - le precondizioni dicono che un lettore semplice passa i due schemi, e uno con i segnaposto no.
> - ✅ **Rossi** (corsia 6187, 16:33-16:34): `services backup-staging` **11 falliti** e 170 passati, `utils
>   backup-cli-restore` **1 fallito** e 108 passati. Esattamente i casi nuovi (`files/logs/b43_red_*.log`).
> - ✅ **Patch applicate** (16:34:21): `apply_b43.py` (4 operazioni in `staging.py`) e `apply_b44.py` (la docstring di
>   `env.py`); ruff e black puliti.
> - ✅ **Verdi** (16:34-16:38):
>   - `services backup-staging` **181**, `utils backup-cli-restore` **109**;
>   - le regressioni: `utils dev-cli-db-path` 17 (il controllo AST di `env.py`), `services backup-secure` 77,
>     `backup-apply` 255, `utils backup-cli` 102.
>   - Porta 6187 libera.
> - ✅ **La guardia dei codici**, senza slot: lo stesso confronto AST di `test_every_code_a_check_can_end_with…`, fatto a
>   mano. Nessun codice prodotto da `staging.py` manca da `RestoreErrorCode`; `database_damaged` c'era già.
> - ✅ **Doc e controlli** (16:38-16:44):
>   - la frase dei test di `security.md` estesa alla parte 1;
>   - `mkdocs build` strict, `check-links`, gate 63;
>   - ruff e black puliti sui 6 file Python, `git diff --check` pulito;
>   - una riga mia oltre i 120 caratteri, riavvolta dopo la build (solo a capo); la riga 2017 lunga è di H.
> - **Backlog**: B-43 ✅, B-44 ✅; B-45 e B-46 aperte, dopo la 1.3. CHANGELOG: una riga 🔒 proposta nell'handoff.

### X-R75 (per X) — il modale delle rotte di cambio cancella prima di salvare; e togliere ogni rotta cancella la coppia (2026-10-17, 16:42-18:33) — ✅ 🧊 FROZEN (checkpoint delle 18:33)

> **Assegnazione** (coordinatore, 16:42; trovata da E): «the FX route modal deletes before it posts
> (`FxPairAddModal.svelte` ~325-339)… If the POST fails (a 422, a network error, a server restart), the routes are
> lost.» Prima l'analisi; il frontend FX è di X, X rivede. Corsia 6187.
>
> **Analisi** (16:42-16:58, sola lettura; `files/xr75-analysis.md`):
> - In modifica (il pulsante «Providers» della pagina della coppia) il modale fa due chiamate:
>   1. `DELETE` di tutta la coppia, che si conferma da sola (`:326`);
>   2. `POST` delle rotte nuove (`:339`).
> - Un `DELETE` di tutta la coppia **non rimette la sentinella MANUAL** (`providers.py:434-478`, Test 17). Così, se il
>   `POST` fallisce (400, 422, 409, 500, rete, riavvio), o non parte (sessione cambiata `:327`, scheda chiusa), o fallisce
>   per una coppia intermedia, la coppia resta senza nessuna rotta.
> - **Difetto 2**: togliere ogni rotta cancella la coppia. Il modale salta il `POST` credendo che la MANUAL torni da sé
>   (`:333`), come dice `configuration.md:201`; il codice e il Test 17 dicono il contrario. La guida utente
>   (`provider.en.md:44`) promette invece «The pair becomes manual».
> - **Chi legge le rotte mentre mancano**:
>   - le conversioni no: leggono i tassi salvati, e il motore usa le rotte solo nell'impronta della cache;
>   - la sincronizzazione sì: né `sync_pairs_bulk` né il job dello scheduler vedono più la coppia, e i suoi tassi
>     invecchiano;
>   - la qualità dei dati segna la coppia come «non configurata»;
>   - il frontend la toglie dalla lista dei cambi, e il PAC chiede di crearla.
>
> **Decisioni** (coordinatore, 16:47): **D1 = A**, il `replace=true` atomico sul server; **D2 = sì**, nello stesso
> lotto. GO, rossi prima. Permesso di scrittura su `FxPairAddModal.svelte` (solo logica) e su `api/v1/fx/providers.py`,
> **ma** `providers.py` solo dopo l'ingresso di X-R74, che lo sta cambiando ora. Da correggere `configuration.md:201`. La
> riga del CHANGELOG nel checkpoint. Slot API ed E2E a richiesta.
>
> **Contratto** (`files/xr75-contract.md`):
> - `POST …/routes?replace=true`: ogni coppia nominata tiene esattamente le priorità mandate, le altre cancellate nella
>   stessa transazione, dopo la validazione e l'upsert. Le regole della MANUAL restano.
> - Il modale in modifica fa un solo `POST` con `replace`. Senza rotte manda la voce MANUAL (priorità 999).
>
> - **Patch pronte**:
>   - `xr75-wip/apply_xr75_fe.py`: 1 operazione nel modale; prettier non cambia nulla;
>   - `apply_xr75_be.py`: 3 operazioni in `providers.py`, ruff e black puliti sulla copia. Da applicare dopo X-R74.
> - **Doc** (mia):
>   - `developer/backend/fx/configuration.md`: una nota «Replacing a pair's routes: `?replace=true`», e la frase del
>     `DELETE` corretta (un `DELETE` di tutta la coppia non rimette la MANUAL; uno con la priorità sì);
>   - `developer/frontend/fx-chain-algorithm.md:353`: il modo di salvare del modale. Anche questa diceva che la
>     MANUAL torna sola.
>   - Tutte e due solo inglesi.
> - **Rossi in scrittura**: TA-XR75-BE (`api fx`) e TA-XR75-FE (Vitest del modale, E2E `front-fx fx-detail`).
> - ✅ **Rossi scritti** (16:50-17:19):
>   - **TA-XR75-BE**, `test_fx_api.py` 18a-18f, su coppie di valuta che nessun altro usa:
>     - rossi: 18a, il replace tiene esattamente le priorità mandate (anche la coppia scritta al contrario); 18b, la sola
>       voce MANUAL lascia la coppia manuale (e il ritorno a una rotta vera toglie la MANUAL); 18c, l'OpenAPI documenta
>       `replace`;
>     - guardie: 18d, un replace rifiutato (400, 422) non cambia nulla; 18e, senza `replace`, o con `replace=false`,
>       l'upsert come prima; 18f, una coppia intermedia, e una coppia attraversata dalla catena ma non nominata resta
>       intatta.
>   - **TA-XR75-FE**:
>     - Vitest: 8 rossi. Un solo `POST` con `replace`, mai un `DELETE`; senza rotte, la voce MANUAL; un `POST` rifiutato
>       (503, 409) lascia l'errore sul modale aperto. Più tre casi riscritti che fissavano il `DELETE` prima del `POST`.
>       E 3 guardie: la creazione non chiede `replace`.
>     - E2E (`fx-detail.spec.ts`): un salvataggio fallito tiene la rotta della coppia; togliere ogni rotta la lascia
>       manuale. La lista dei provider è risposta nel browser con MOCKFX, che quella reale nasconde.
> - ✅ **Rosso Vitest** (corsia 6187, 17:19-17:20): `FxPairAddModal.test.ts` **8 falliti** e 16 passati, esattamente i
>   casi nuovi (`files/logs/b_vitest_xr75_red.log`).
> - **X-R74 entrato** (coordinatore, 17:01): `providers.py` libero. Il merge di dev lo fa il coordinatore: a quel punto
>   gli mando «FROZEN for base update» (17:03, correzione del coordinatore: i figli non toccano la storia di git).
> - ⏳ Rossi API ed E2E: slot chiesto alle 17:22.
> - ✅ **Rosso API** (slot del coordinatore, 17:21-17:29): `api fx -k replace` **3 falliti** (18a, 18b, 18c) e 3 passati
>   (le guardie), esattamente come previsto (`files/logs/xr75_red_api_fx.log`).
> - **⚠️ Fuori pista — il rosso E2E per la ragione sbagliata** (17:29-17:31): i due test cadono nel loro aiuto
>   `openProviderEditor`, prima del difetto. Lo screenshot mostra il modale con «Failed to load conversion routes»: con
>   la lista dei provider risposta dal test, `FxProviderSelect.computeRoutes()` prende un'eccezione. Slot liberato
>   alle 17:33. Il test torna a TA-XR75-FE: trovare la causa e mettere nel messaggio gli errori della console del
>   browser. Poi un breve slot per rifare solo il rosso E2E.
>   - La patch del frontend aspetta quel rosso: con lei sola, «a failed save keeps the route» passerebbe senza aver mai
>     mostrato il suo rosso.
> - ✅ **La causa vera** (TA-XR75-FE, 17:35-17:45): **un difetto latente del prodotto**, non soltanto il test.
>   - `currencyGraph.ts` fa `import MultiDirectedGraph from 'graphology'`, ma l'export di default è il `Graph` semplice
>     (`multi: false`, `type: 'mixed'`; misurato in Node).
>   - Così due provider sulla stessa direzione (MOCKFX e MOCKFX_FAIL, tutti e due EUR→X) fanno lanciare
>     `addDirectedEdge`, e il selettore delle rotte dice solo «Failed to load conversion routes». Il catalogo reale
>     oggi lo evita solo perché ECB, FED, BOE e SNB hanno basi diverse.
>   - Il test ora usa direzioni opposte, e le sue precondizioni riportano gli errori della console del browser.
> - **Decisione** (coordinatore, 17:48): l'import con nome dentro X-R75, con il suo rosso Vitest; X rivede.
> - ✅ **Rossi E2E di nuovo** (slot, 17:50-17:54): tutti e due cadono sul difetto. Dopo il salvataggio fallito la coppia
>   non ha più rotte («what the save sent: DELETE (no query), POST (no query)»); togliere ogni rotta cancella la
>   coppia (`files/logs/xr75_red_e2e2.log`).
> - ✅ **Patch del modale applicata** (17:55:08); Vitest `FxPairAddModal.test.ts` **24 passati**.
> - ✅ **Il grafo**:
>   - TA-XR75-FE ha scritto il file nuovo `src/lib/utils/currency/currencyGraph.test.ts`: 2 rossi (due provider sulla
>     stessa direzione) e 6 guardie. È registrato in `front-utility core-unit` (`_frontend_utility.py` l.129, più una
>     frase nella desc).
>   - Rosso (18:00): **2 falliti** e 6 passati, su «UsageGraphError … an edge linking "EUR" to "NIO" already exists».
>   - Patch `apply_xr75_graph.py` applicata (18:00:37): l'import con nome, con un commento. Prettier non cambia nulla.
>   - Verdi: i due file **32 passati**; i vicini che toccano il grafo (`FxProviderSelect`, `PageSyncModal`,
>     `FxSyncModal`, `FxMissingRate`, `fxCreationSync`, `sanitizeHtml`) **97 passati**.
> - ✅ **Controlli** (18:04): ruff e black puliti sui 3 file Python; prettier pulito sui 5 file del frontend;
>   `git diff --check` pulito; porta libera.
> - 🧊 **FROZEN for base update** (18:05): il frontend è finito. Il backend (`providers.py`) aspetta il merge di dev con
>   X-R74, che fa il coordinatore.
> - **Base aggiornata** (coordinatore, 18:04): il mio checkpoint `5cbc60844` più il diario, fino a `73627df26`; dev
>   `1eeb297b2` entrato pulito, `087db9be5`. Porta X-R74 (`providers.py`: quattro 500 generici).
> - ✅ **Patch del backend applicata** (18:05:18): `apply_xr75_be.py`, 3 operazioni in `providers.py`, ricontrollata dopo
>   X-R74 (che non tocca i punti della patch). ruff e black puliti; `import backend.app.main` riuscito.
> - ✅ **`api sync`** (18:10, nessun file tracciato cambiato: il client generato è ignorato da git) e **`front check`**
>   (18:11): 0 errori, 0 avvisi. Il tipo di `{queries: {replace: true}}` ora esiste.
> - ⏳ I verdi `api fx` ed E2E: slot chiesto alle 18:12.
> - ✅ **Doc** (18:14-18:17, mentre lo slot era in coda): `mkdocs build` strict, `check-links`, gate 63.
> - ✅ **Verdi** (slot del coordinatore, via libera alle 18:15 dopo la finestra di X; 18:18-18:31,
>   `files/scripts/xr75_green_slot.sh`, ogni corsa ad attesa del carico a 5 minuti sotto 50):
>   - `api fx`, tutto il file: **33 passati** (i 6 di X-R75 e le prove delle rotte 15-17);
>   - `front-fx fx-detail`, i 2 test di X-R75: **2 passati**;
>   - `front-fx fx-add-pair`, tutta la spec, per regressione (la chiamata di creazione condivide la riga cambiata):
>     **11 passati**.
>   - Porta 6187 libera.
> - **Backlog**: X-R75 e il fratello dell'editor (che conta come salvate le date scartate) li scrive X nella sua
>   sezione; il grafo non multiplo è entrato in X-R75 (coordinatore, 17:48). CHANGELOG: la riga 🐛 nell'handoff.

### W-B64 + W-B65 (per W) — il budget delle cifre contato come il backend; e un «Applica» senza modifiche nel Bulk (2026-10-17, 18:31-19:56) — ✅ 🧊 FROZEN (checkpoint delle 19:56)

> **Assegnazione** (coordinatore, 18:31): «W-B64 + W-B65 as one small lot», dalla sezione di W (BACKLOG l.5660 e
> l.5668; piano 04, «C-97b — i decimali in input: la cura»). Prima l'analisi; W rivede. Corsia 6187.
>
> **Analisi** (18:31-18:47, sola lettura, base `870d519bd`; `files/wb64-65-analysis.md`):
> - **W-B64**:
>   - le tre quantità del Form (`TxFormSingleSection.svelte` ×2, `TxFormPairSection.svelte`) hanno
>     `maxIntegerDigits={12}`, mentre il backend ne prende 15 (N63, `db/precision.py`);
>   - `ExactDecimalInput` (il budget e il messaggio) ed `ExactQuantityInput` (`withinDigitBudget`) contano i caratteri.
>     Il backend (`_digit_counts`) non conta gli zeri iniziali dell'intero né quelli finali dei decimali. Così il Form
>     rifiuta `0.10000000000` a 10 decimali, e i campi priorità del PAC rifiutano `5.0` con «Whole numbers only».
> - **W-B65**: il Form, su «Applica», manda il payload col segno (`buildCreatePayload`), e `applyFormPayload` del Bulk lo
>   copia com'è. Il Bulk invece tiene in grandezza i valori che il tipo vuole negativi (`fieldsFromTx`, e l'import). La
>   guardia della chiusura confronta `serializeOps` così com'è. Due cause:
>   - **C1, il segno** (come scritta): la quantità di una SELL mostra `-0.00000001`; la cassa di BUY, WITHDRAWAL, FEE e
>     TAX torna col segno. La cella la ri-segna, quindi non si vede, ma la chiave cambia. E le SELL nuove create dal Form
>     si vedono col segno;
>   - **C2, trovata leggendo**: ogni «Applica» scrive `wacCurrencyHint = null` (l.777-778, e il partner l.2476) su una
>     riga che quella chiave non l'aveva. `JSON.stringify` tiene una chiave `null` e ne butta una assente: qualunque
>     tipo, anche un DEPOSIT, chiederebbe di scartare.
> - Fuori dal lotto, per W: la cassa dell'import passa ancora da `Number`, e `isDraftReadyForValidation` legge
>   `=== '0'`; un blur su una cassa positiva riscrive `0.010000` come `0.01`.
>
> **Decisioni** (coordinatore, 18:5x):
> - **D1 = (a)+(b)**: N63 è una decisione notturna registrata, valida finché il developer non la rivede: 15 cifre intere;
> - **D2 = sì**: non si contano neanche gli zeri iniziali dell'intero;
> - **D3 = sì**, C2 dentro il lotto se il rosso del DEPOSIT la prova; se è verde prima della cura, non si cambia nulla.
> - **Scrittura**: tutti i file elencati, solo script e logica, **tranne `TransactionBulkModal.svelte`**, che W sta
>   cambiando per W-B70 (D-W70-4): la sua modifica (`fieldsFromTx`, `applyFormPayload`, il suggerimento WAC) va **per
>   ultima**, quando il coordinatore dice che W-B70 è entrato. CHANGELOG 🐛 ×2. Slot E2E a richiesta.
>
> **Contratto** (`files/wb64-65-contract.md`):
> - `decimalDigitCounts(value)` in `parseDecimalInput.ts`: le cifre intere senza gli zeri iniziali, i decimali senza
>   quelli finali, e il numero senza quegli zeri (`stripped`); `null` per un testo non canonico. Lineare, due cicli
>   (W-B66).
> - `ExactDecimalInput`: budget e messaggio sui conteggi; `min`/`max` confrontati con `stripped`; una freccia su un
>   valore il cui testo supera il budget, ma valido senza i suoi zeri, parte da `stripped` (`5.` e 40 000 zeri → `6`);
>   ogni altro valore dal suo testo (`1.50` → `2.50`). `ExactQuantityInput`: `withinDigitBudget` sui conteggi.
> - Il Form: `maxIntegerDigits={15}` sulle tre quantità.
> - `magnitudeForRule(value, rule)` in `txPayloadHelpers.ts`: per la regola `negative`, un valore negativo diventa la
>   sua grandezza esatta; tutto il resto torna com'è. Idempotente.
> - Il Bulk, per ultimo: `fieldsFromTx` e `applyFormPayload` (per ultima cosa) passano quantità e cassa da
>   `magnitudeForRule`; con D3, un suggerimento WAC `null` toglie la chiave invece di scriverla.
>
> - **Patch pronte** (`files/wb64-65-wip/`, tutte `--check` OK su `870d519bd`; le copie emesse passano prettier):
>   - `apply_wb64.py`: 9 operazioni in 5 file (l'aiuto, i due campi, le tre quantità del Form);
>   - `apply_wb65_helper.py`: 2 operazioni in `txPayloadHelpers.ts`;
>   - `apply_wb65_bulk.py`: 3 operazioni in `TransactionBulkModal.svelte`, 5 con `--with-d3`. Da applicare dopo W-B70,
>     con un `--check` nuovo.
> - **Rossi in scrittura** (18:58): TA-WB64 (Vitest: `parseDecimalInput.test.ts`, `ExactDecimalInput.test.ts`,
>   `ExactQuantityInput.test.ts`, `TransactionFormModal.test.ts`) e TA-WB65 (Vitest `txPayloadHelpers.test.ts`; E2E
>   `tx-bulk-operations.spec.ts`: SELL, BUY e DEPOSIT, ognuno coi suoi dati).
> - ✅ **Rossi scritti** (18:58-19:16):
>   - **TA-WB64**:
>     - `decimalDigitCounts`: 22 casi (7 `null`, 12 terne esatte, 3 lineari sotto 1 000 ms);
>     - `ExactDecimalInput`: 5 rossi (`0.10000000000` a 10, `5.0` a 0, `0000000000001.5` a 12, la portata di `5.` e
>       40 000 zeri, la freccia da quel valore a `6`) più 3 guardie;
>     - `ExactQuantityInput`: 1 rosso e 1 guardia (`0.10000000001` resta intero, rifiutato);
>     - il Form: 3 rossi, 15 cifre intere in BUY, ADJUSTMENT e TRANSFER; la guardia spostata a `1000000000000000.1`.
>   - **TA-WB65**:
>     - `magnitudeForRule`: 44 casi, compreso il giro del Form per SELL, BUY e FEE;
>     - l'E2E: 3 test (SELL, BUY, DEPOSIT), con `seedSatoshiLedger` e `applyFormUntouched`. Il seme della guardia C-97b
>       ora passa dallo stesso aiuto, con le stesse righe; la sua docstring rimanda ai test W-B65.
>     - **C2 vera dal codice**: per TA-WB65, oggi il DEPOSIT è rosso solo per il `null` di `wacCurrencyHint`.
>   - Note dei test-author, fuori dal lotto:
>     - il Form a 15 + 10 accetta `999999999999999.5`, che il backend rifiuta per le 15 cifre significative (come già
>       oggi a 12 + 10);
>     - un commento vecchio in `e2e/transactions/tx-bulk-promote-cost-basis.spec.ts` («12 integer digits, 6 decimals»).
> - ✅ **Rosso Vitest** (corsia 6187, 19:17-19:18, carico 14): i 5 file, **75 falliti** e 444 passati
>   (`files/logs/b_vitest_wb64_65_red.log`). Sono esattamente i casi nuovi, 22 + 5 + 1 + 3 + 44, ognuno all'asserzione
>   attesa: `aria-invalid` `true` per il budget, `{digitsValid: false, rangeValid: true}` per la portata, il valore
>   lasciato com'è dalla freccia; i due aiuti per assenza dell'export.
> - ✅ **Patch W-B64 e aiuto W-B65 applicate** (19:19): `apply_wb64.py` (9 operazioni) e `apply_wb65_helper.py` (2).
>   La patch del Bulk aspetta W-B70.
> - ✅ **Verdi Vitest** (19:19-19:20, carico 21): i 5 file **519/519** (`files/logs/b_vitest_wb64_65_green.log`).
>   `front check` **0/0** (`wb64_front_check.log`); `tsc -p tsconfig.e2e.json` **0 errori** (`wb65_tsc_e2e.log`).
> - ⏳ **Rosso E2E**: slot chiesto (19:2x), `files/scripts/wb65_slot.sh red`: i 3 W-B65 e la guardia C-97b, col Bulk
>   ancora senza patch. Atteso: 3 falliti e 1 passato.
> - **W-B70 entrato, base aggiornata** (coordinatore, 19:23): avanzamento rapido `870d519bd` → `c9ebc1102`; i miei 13 file
>   sporchi intatti, nessuna sovrapposizione. W-B70 cambia il Bulk solo in `mergeAllSuggestions` e negli import: lontano
>   dalle mie righe. `api sync` (exit 0, nessun file tracciato cambiato); `apply_wb65_bulk.py --with-d3 --check` OK sulla
>   base nuova. **GO** del coordinatore per il rosso E2E, dietro il cancello del carico a 5 minuti (19:2x).
> - **Doc W-B64** (docs-writer, in corso): `core-ui/atoms.md` (`ExactDecimalInput`, `ExactQuantityInput`) e
>   `features/transaction-form.md` (la quantità). La doc di W-B65 (`transaction-form.md` l.55,
>   `state/transaction-draft.md`) solo dopo la patch del Bulk.
> - ✅ **Rosso E2E** (slot del coordinatore, 19:24-19:37, carico a 5 minuti 34; ricostruzione del frontend di debug
>   compresa, 12 minuti sotto il carico di J e Y): **3 falliti e 1 passato** (`files/logs/wb65_red_tx_bulk.log`):
>   - SELL: la cella mostra `-0.00000001` (asserzione morbida) e, dopo «Annulla», l'editor resta aperto;
>   - BUY: l'editor resta aperto;
>   - DEPOSIT: l'editor resta aperto. **C2 provata**: i suoi valori non cambiano segno, quindi la causa è solo il `null`
>     di `wacCurrencyHint`. D3 entra;
>   - la guardia C-97b, col seme ora condiviso: passata.
> - ✅ **Patch del Bulk applicata** (19:38): `apply_wb65_bulk.py --with-d3`, 5 operazioni; prettier pulito su tutti i 14
>   file del lotto.
> - ✅ **Verdi**:
>   - `front check` **0/0** (19:39-19:41, dopo l'attesa del carico; `wb65_front_check.log`);
>   - `vitest related` sui 7 moduli cambiati: **83 file, 3127 passati** (19:41-19:43; `b_vitest_wb64_65_related.log`):
>     i test di ogni componente che importa i campi esatti o gli aiuti, PAC compreso;
>   - E2E (19:46-19:49): `tx-bulk-operations`, i 3 W-B65, la guardia C-97b e «B1 regression»: **5 passati**, sulla build
>     ricostruita con la patch (`wb65_green_tx_bulk.log`). Porta 6187 libera.
> - **CHANGELOG** 🐛 ×2, dopo la voce di #43 (le cifre della quantità e gli zeri; l'«Applica» senza modifiche nel Bulk).
> - **Backlog**, sezione B: **B-47** (un focus e un blur sulla cassa del Form riscrivono `0.010000` come `0.01`: la
>   guardia chiede ancora di scartare; con la cassa dell'import da `Number`) e **B-48** (il Form a 15 + 10 contro le 15
>   cifre significative del backend; il commento vecchio in `tx-bulk-promote-cost-basis.spec.ts`). Le righe W-B64 e
>   W-B65 sono nella sezione di W: le chiude il coordinatore o W.
> - **⚠️ Fuori pista — B-47 verificata sul codice** (19:5x): `READ_MIN_SCALE = 6` (`db/real_decimal.py`) rende le somme
>   con almeno 6 decimali, `CompactCashCell.handleBlur` emette sempre, `setCash` non confronta.
> - ✅ **Doc** (docs-writer, 19:05-19:53; solo inglesi, nessuna traduzione):
>   - `core-ui/atoms.md`: `ExactDecimalInput` conta le cifre come il backend (`decimalDigitCounts`, gli esempi), `min`/`max`
>     sul valore senza zeri, il messaggio, la regola delle frecce, la riga di W-B66; `ExactQuantityInput`: il valore del
>     genitore mostrato canonico, «Used by» a 15 + 10;
>   - `features/transaction-form.md`: il punto **Quantity** (15 + 10, gli zeri non contati), la riga `quantity` della
>     tabella (l.91, ancora a 12, trovata dal grep), lo «Staging state» (il payload col segno, `magnitudeForRule`);
>   - `state/transaction-draft.md`: la convenzione dei segni di `DraftFields`, l'«Applica» del Form, la guardia della
>     chiusura (`serializeOps`, la chiave, il `null` contro l'assente). La tabella dello stato resta vera: lo stato non
>     è mai stato sbagliato, solo la cella e la chiave.
>   - **⚠️ Fuori pista**: il docs-writer ha trovato nella docstring di `magnitudeForRule` «a `free` ADJUSTMENT»: la regola
>     della quantità di ADJUSTMENT è `nonzero`. Corretta (solo commento; prettier pulito).
> - ✅ **Prove della doc** (19:54-19:55, carico 28): build stretta OK, `check-links` OK, `utils gate-docs-links` **63
>   passati** (`b_docs.sh`). `git diff --check` pulito; porta 6187 libera.
> - 🧊 **CHECKPOINT READY** (19:56): 19 file tracciati, nessun file nuovo; FROZEN.
> - **E-19b1, a margine** (coordinatore, 18:48: dove mettere in `_stage` il controllo delle valute salvate di E). Risposta
>   delle 18:5x:
>   - dopo gli `except` del mio involucro B-43 e prima di `_write_report`;
>   - la connessione aperta in `staging.py`, perché il registratore di B-37 guarda solo `staging`, `snapshot`,
>     `post_migration` e `totals`;
>   - un BLOB in un posto di valuta fa lanciare a `_as_text` un `TypeError`, non un `sqlite3.Error` (provato,
>     `files/e19b-wip/probe_audit.py`): il controllo finirebbe;
>   - nel log, la classe e `sqlite_errorname`, mai il testo (un UTF-8 non valido lo cita).
> - **Entrato nel ramo** (coordinatore, 19:59): `2b3c9e8d7` (fix) e `26e17c167` (diario); dev `fe42c9a2f` unito nel mio
>   ramo: **`597b2867c`**, pulito, senza conflitti; le 2 righe del CHANGELOG al loro posto.
> - ⏳ **Revisione combinata** su `597b2867c`, prima dell'ingresso in dev (coordinatore, 19:59):
>   - ✅ `api sync` (exit 0, nessun file tracciato cambiato) e `front check` **0/0** (20:00-20:01, carico 12);
>   - ✅ Vitest sui 5 file **519/519** (20:01; `b_vitest_wb64_65_combined.log`);
>   - ✅ E2E (20:01-20:07, carico a 5 minuti 16-18; ricostruzione compresa): tutto `tx-bulk-operations` **14 passati**,
>     tutto `tx-split-promote` **6 passati** (`wb65_combined_tx_bulk.log`, `wb65_combined_tx_split_promote.log`). Porta
>     6187 libera. **Combinata OK**, riferita al coordinatore alle 20:08.
> - **B-49** archiviato (coordinatore, 19:58, la nota di E): un testo non UTF-8 nei dati di un backup passa la verifica;
>   da decidere dopo W-B65 se rifiutarlo o avvisare.

### X-R79 (per X) — l'editor delle rotte manda prima le coppie intermedie, senza `replace`, poi la coppia da sola con `replace` (2026-10-17, 19:56-20:21) — ✅ 🧊 FROZEN (checkpoint delle 20:21)

> **Assegnazione** (coordinatore, 19:56; dalla revisione di X su X-R75; la riga la scrive X, il proprietario sono io;
> X rivede): «`replace=true` also applies to the chain legs the modal adds with "create intermediate pairs"… If another
> tab configures a leg meanwhile, the edit replaces that leg's routes. Fix, frontend only: in edit mode, post the legs
> first as a plain upsert (add-only), then the main pair alone with `replace=true`.»
>
> **Analisi** (19:56-20:00, sola lettura; `files/xr79-analysis.md`):
> - Oggi, in modifica, una sola `POST` con `replace` porta coppia e gambe (`FxPairAddModal.svelte` l.326-327), e il
>   backend applica `replace` a ogni coppia nominata: una gamba configurata nel frattempo da un'altra scheda resta con
>   la sola rotta del modale.
> - **L'upsert semplice non è «add-only»**: `create_routes_bulk` aggiorna la rotta che esiste già alla stessa priorità
>   (`providers.py` l.249-262), e un provider vero toglie la MANUAL. Con la cura, una gamba configurata nel frattempo
>   perde solo la priorità 1, non tutte le rotte: la stessa esposizione che la creazione ha sempre avuto.
> - Opzioni: **A**, come chiesto; **A+**, rileggere le rotte prima delle gambe (`ensureFxRoutesLoaded` non ricarica:
>   carica una volta); **B**, una bandiera del backend (`create_only`), davvero solo aggiunta.
> - Due richieste: gambe rifiutate → ci si ferma, niente scritto; gambe scritte e coppia rifiutata → la coppia resta com'era
>   (la garanzia di X-R75 per la coppia modificata), le gambe restano, e un nuovo tentativo le riscrive uguali.
>
> **Decisione** (coordinatore, 19:59): **opzione A**, solo frontend. Scrittura su `FxPairAddModal.svelte` (solo logica),
> il suo test, `fx-chain-algorithm.md` (compresa la frase sbagliata «reloads») e `fx/configuration.md`. Prima i rossi.
> L'opzione B va a X come voce dopo la 1.3 (la gira il coordinatore).
>
> - **Rossi in scrittura** (20:03): TA-XR79, solo `FxPairAddModal.test.ts`: l'ordine delle due richieste; le gambe
>   rifiutate (nessuna seconda richiesta); la coppia rifiutata dopo le gambe; le guardie (gambe già configurate, creazione).
> - **Doc** (mia, 20:05-20:10, solo inglesi):
>   - `developer/frontend/fx-chain-algorithm.md`: la frase «before posting the modal reloads the configured routes» era
>     sbagliata. Ora dice che il modale controlla le coppie che ha, senza ricaricarle: `ensureFxRoutesLoaded()` risponde
>     dallo store finché `invalidateFxRoutes()` non lo svuota. Più un punto nuovo sul salvataggio in due richieste;
>   - `developer/backend/fx/configuration.md`: le coppie intermedie dell'editor vanno prima, in una richiesta semplice.
> - **Patch pronta** (`files/xr79-wip/apply_xr79.py`, 1 operazione; `--check` OK; prettier OK sulla copia):
>   - in modifica, le gambe prima, senza `replace`, poi la sola coppia con `replace`; senza gambe, una richiesta;
>   - in creazione, una richiesta semplice come prima;
>   - `sameSession()` dopo ogni richiesta; `finishFxPairCreation` una volta sola, dopo l'ultima.
> - **W-B64/65 entrato in dev** (coordinatore, 20:08): `cde76dc54`. Il mio worktree resta a `597b2867c` fino al
>   checkpoint di X-R79, perché il backlog è aperto qui.
> - ✅ **Rossi scritti** (TA-XR79, 20:03-20:15), 8 casi in un `describe` nuovo, più due commenti del file allineati:
>   - 6 rossi: l'ordine delle due richieste, con due gambe e con una (l'altra già configurata); le gambe rifiutate (503,
>     409); la coppia rifiutata dopo le gambe (503, 409);
>   - 2 guardie: tutte le gambe già configurate (una richiesta con `replace`); la creazione con la casella (una richiesta
>     semplice, coppia e gambe).
> - ✅ **Rosso Vitest** (20:15-20:16, carico 13): **6 falliti** e 26 passati (`b_vitest_xr79_red.log`), esattamente i 6, e
>   tutti alla stessa asserzione: oggi c'è una sola `POST` con la coppia e le gambe, e con `replace`. Il file del test
>   aveva una riga da riformattare (prettier `--write`, solo spazi).
> - ✅ **Patch applicata** (20:16); un ritocco al commento prima: «replaces the pair's own routes».
> - ✅ **Verdi** (20:16-20:20, carico 12-13):
>   - `FxPairAddModal.test.ts` **32/32** (`b_vitest_xr79_green.log`);
>   - `vitest related` sul modale: **8 file, 184 passati**;
>   - `front check` **0/0**;
>   - doc: build stretta, `check-links`, `utils gate-docs-links` **63 passati**.
>   - `git diff --check` pulito; porta 6187 libera.
>   - Nessun E2E: la modifica senza gambe è la stessa richiesta di X-R75 (i suoi 2 test di `fx-detail`).
> - **Note del test-author, dette al coordinatore**:
>   - un 409 sulla richiesta della coppia, dopo le gambe scritte, mostra `fx.addPair.createConflict` («Nothing was
>     saved»), che allora non è vero per le gambe. Caso raro (un inserimento concorrente della stessa priorità); una
>     frase giusta vorrebbe una chiave nuova in 4 lingue: lo decide il coordinatore o X;
>   - dopo le gambe scritte e la coppia rifiutata, lo store delle rotte non lo sa: un nuovo tentativo riscrive le gambe
>     uguali (idempotente).
> - 🧊 **CHECKPOINT READY** (20:21): 6 file tracciati, nessun file nuovo; FROZEN.

### B-49 — un testo non UTF-8 nei dati di un backup: la verifica lo rifiuta (2026-10-17, 20:2x-21:26) — ✅ 🧊 FROZEN (checkpoint delle 21:26)

> **Assegnazione** (coordinatore, 20:2x, dopo l'ingresso di X-R79 in dev `6f11a6790`): B-49, analisi e decisione mia
> («rifiutare alla verifica, `database_damaged`, nulla applicato, o avvisare come E-19b1?»; il coordinatore tende a
> rifiutare). Prima provare in processo che le letture del server falliscono dopo il ripristino, e misurare il costo
> della scansione su un archivio grande, come per l'audit di E. Poi B-15 + B-8.
> Nello stesso giro: la riga X-R79 (sezione di X, su richiesta del coordinatore) aggiornata coi tre residui e chiusa (✅).
>
> **Analisi** (20:2x-20:45; `files/b49-analysis.md`, sonda `files/b49-wip/probe_b49.py`, solo file usa e getta in
> `/tmp/lf_b49_probe`, il DB della corsia copiato in sola lettura con l'API di backup di SQLite):
> - ✅ **La rottura dopo il ripristino, provata in processo**: un valore `CAST(x'45ff52' AS TEXT)` in
>   `transactions.description`, `assets.display_name`, `brokers.name`, `price_history.currency` e `fx_rates.date` (una
>   colonna DATE: affinità NUMERIC, valori di testo), letto col motore dell'app (`sqlite+aiosqlite`, il listener di
>   `session.py`, NullPool). Ogni `select(Model)` fallisce: `sqlalchemy.exc.OperationalError` ←
>   `sqlite3.OperationalError: Could not decode to UTF-8 column … with text 'E�R'`. È la lettura intera a fallire, non la
>   riga; `select(Model.id)` funziona ancora. Quindi ogni elenco di quelle righe risponde 500, e il messaggio cita i
>   byte. Prima della modifica, le cinque letture rendono 76, 17, 8, 2 733 e 4 185 righe (`b49_probe_read.log`).
> - ✅ **Il costo**, su una copia cresciuta a **488 MB** (2 040 000 prezzi, 1 004 185 cambi, 200 076 transazioni; carico
>   45-66, tempi alti):
>   - (d), per tabella una passata per finestra di 200 000 righe, ogni colonna concatenata da SQLite in una riga:
>     **3,6 s** pulita, **2,4 s** con un valore cattivo in fondo a `price_history`;
>   - (b), per colonna: 4,8 s; (c), byte decodificati in Python: 11,3 s; (a), riga per riga: 13,8 s;
>   - l'audit E-19a sulla stessa copia: 2,0 s; `PRAGMA integrity_check`: 8,6 s (la verifica lo fa due volte).
>   - **⚠️ Fuori pista**: la prima misura di (c) dava 0,00 s, per un errore della sonda: con `text_factory = bytes` i nomi
>     delle tabelle tornano come byte, e non si leggeva nulla. Corretto e rimisurato (`b49_probe_rescan.log`).
> - **Decisione (mia): rifiutare**, con `database_damaged`:
>   - nessun codice nuovo, quindi niente `RestoreErrorCode`, i18n o CLI da cambiare; la frase della UI è giusta;
>   - un messaggio inglese proprio, e un avviso nel log col solo numero di tabelle;
>   - un passo nuovo nell'involucro di B-43, dopo `_check_against_manifest` e prima dell'upgrade;
>   - il metodo (d) su ogni tabella tranne `sqlite_%`, per classe di memorizzazione del valore;
>   - un `text_factory` severo, che fa lanciare `UnicodeDecodeError`;
>   - la connessione in `staging.py`, `mode=ro`, `trusted_schema=OFF` per primo.
>   - Perché non avvisare: l'istanza ripristinata fallirebbe quegli elenchi, e la UI non può riparare righe che non
>     legge. LibreFolio scrive solo UTF-8, e le checksum fermano un archivio danneggiato.
> - **Cambia RNW-109 di E**: i suoi archivi finirebbero in `database_damaged` prima della lettura E-19a; la nota di E
>   (BACKLOG l.7942) lo prevede già. Da concordare chi lo riscrive.
> - Mandata al coordinatore alle 20:45. 🧊 Nessun codice prima del via.
> - **Via del coordinatore** (20:5x): **rifiutare**, come disegnato. `database_damaged`, un passo nell'involucro di B-43
>   dopo `_check_against_manifest` e prima dell'upgrade; `text_factory` severo, connessione propria `mode=ro` +
>   `trusted_schema=OFF`; nel log solo conteggi; BLOB fuori; **nessuna riga di CHANGELOG** (il ripristino è nuovo nella
>   1.3). **RNW-109 lo riscrivo io** nei rossi: ora si aspetta `database_damaged` prima dell'audit, nessuna riga
>   dell'audit; il ramo del guasto resta coperto da RNW-107. Doc: `backup_restore.en.md` è mio; **`security.md` è aperto
>   da H (H-52)**: non lo tocco, il paragrafo va al coordinatore col checkpoint.
> - **Contratto** (`files/b49-contract.md`); **patch** `files/b49-wip/apply_b49.py` (4 operazioni in `staging.py`: la
>   docstring del modulo, l'import di `_identifier` da `snapshot`, il passo in `_stage`, la scansione).
> - ✅ **Rossi scritti** (TA-B49, 20:5x-21:03), sezione (o) di `test_backup_staging.py` (la (n) era già B-43):
>   - rossi: 4 posti (colonna TEXT, colonna DATE, tabella sconosciuta, i tre insieme), l'archivio più vecchio rifiutato
>     prima dell'upgrade, il log (un avviso, solo interi, niente testo, byte, nomi o percorsi), un carattere spezzato su
>     due righe, i rowid ai due estremi (con un limite di 60 s), la connessione della scansione (`mode=ro`,
>     `trusted_schema=OFF` per primo, `typeof(` e `'text'`);
>   - guardie: testo valido oltre l'ASCII (`é`, `日本`, `💶`, `𝄞`), gli stessi byte come BLOB, il manifest sbagliato
>     ancora `manifest_mismatch`;
>   - RNW-109 riscritto (`test_restore_non_iso_warning.py`): `database_damaged`, l'audit mai chiamato, nessun report.
> - ✅ **Rossi** (corsia 6187, 21:04-21:05, carico 10): `services backup-staging` **13 falliti**, 187 passati
>   (`b49_red_staging.log`); `services restore-non-iso-warning` **4 falliti**, 42 passati (`b49_red_rnw.log`). Sono
>   esattamente i casi nuovi, ognuno alla sua ragione: il controllo arriva alle correzioni o all'upgrade, «DID NOT RAISE»,
>   nessuna connessione che legga per classe.
> - **⚠️ Fuori pista — due buchi della mia scansione, trovati prima di applicarla**:
>   - il test del carattere spezzato (TA-B49): unire i valori con `''` ricompone `C3` + `A9` in `é`, e i due valori
>     sbagliati passano. Ora li unisce una virgola, un byte suo (provato: `''` passa, `','` trova);
>   - `pragma_table_info` nasconde le colonne generate (provato: `table_xinfo` le mostra, `hidden` = 2). Una colonna
>     generata con un valore non UTF-8, chiamata come una colonna che il server legge, sfuggirebbe. Ora `table_xinfo`;
>     il rosso relativo chiesto a TA-B49;
>   - in più: una finestra oltre il limite di lunghezza di SQLite (`DataError`, provato) continua riga per riga.
> - ✅ **La scansione provata a parte** (`files/b49-wip/harness_b49.py`, sul codice emesso, prima di applicarlo): la
>   copia pulita passa; tutti i casi limite validi passano (rowid −2⁶³ e 2⁶³−1, i tre nomi del rowid coperti, `WITHOUT
>   ROWID`, nomi con virgolette); ogni caso con testo cattivo è rifiutato, compresi il carattere spezzato e la colonna
>   generata; il log ha solo `tables=5`. Sulla copia da 488 MB: **3,3 s** pulita, 2,7 s con un valore cattivo, contro
>   5,5 s per un `integrity_check` (carico 9-10).
> - ✅ **Il rosso della colonna generata** (TA-B49, due varianti, VIRTUAL e STORED, in una tabella sconosciuta, con le
>   precondizioni: `table_info` non la elenca, `table_xinfo` sì; né B-28 né B-43 la fermano; `VACUUM INTO` la copia):
>   **2 falliti** alla ragione attesa (21:16; `b49_red_generated.log`).
> - ✅ **Patch applicata** (21:17): 4 operazioni in `staging.py` (+76 righe).
> - ✅ **Verdi** (21:17-21:21, carico 12-24):
>   - `services backup-staging` **202** e `services restore-non-iso-warning` **46**;
>   - `services backup-secure` 77, `services backup-apply` 255, `utils backup-cli` 102, `utils backup-cli-restore` 109,
>     `utils backup-cli-secure` 106, `utils dev-cli-db-path` 17;
>   - ruff e black puliti sui 3 file Python;
>   - doc: build stretta, `check-links`, `utils gate-docs-links` 63. `git diff --check` pulito; porta 6187 libera.
> - **Doc**:
>   - `admin/backup_restore.en.md`, la riga di `database_damaged` della tabella dei rifiuti (pagina senza traduzioni);
>   - `admin/cli_tools.en.md`, il passo 4 della prova su copia e la riga di `database_damaged`. Debito di traduzione
>     vero, niente stamp, come per B-38.
>   - `security.md`: non toccato (H-52). Il paragrafo è in `files/b49-security-paragraph.md`, mandato col checkpoint.
> - **Non fatti**: `api backup-restore` e `api backup-restore-apply` (serve la corsia col server); la `desc` di
>   `backup-staging` nel runner non nomina B-49 (file condiviso, non assegnato).
> - File della sonda (`/tmp/lf_b49_probe`, 488 MB) cancellati.
> - 🧊 **CHECKPOINT READY** (21:26): 7 file tracciati, nessun file nuovo; FROZEN.
> - **Entrato in dev** (coordinatore, 21:34): `709dfb1e4`, dopo l'unione di dev nel mio ramo (`74c08dafe`; conflitto
>   solo nel backlog, X-R79 contro X-R80 di X, tenuti entrambi). Sull'albero unito il coordinatore ha fatto girare
>   `backup-staging` 202, `restore-non-iso-warning` 46, `api backup-restore` 161, `api backup-restore-apply` 215: verdi.
> - ✅ **Coda** (coordinatore, 21:34; H-52 entrato, `security.md` libero; 21:34-21:37):
>   - `developer/architecture/security.md`: il paragrafo di B-49 dopo «What the check cannot read», e
>     `_refuse_undecodable_text()` nell'elenco delle connessioni del punto `trusted_schema`. Nello stesso elenco mancava
>     la lettura E-19b1 (`_holds_non_iso_currencies()`, `mode=ro`, `trusted_schema=OFF` per primo): aggiunta, detto al
>     coordinatore;
>   - la `desc` di `backup-staging` nel runner nomina B-49 (o); ruff e black puliti, il runner si carica;
>   - doc: build stretta, `check-links`, `utils gate-docs-links` 63; `git diff --check` pulito. CHECKPOINT READY 21:37.

### B-15 + B-8 — rossi scritti, poi il fermo e il parcheggio (2026-10-17, 21:27 → 2026-10-19, 11:10) — ⏸️ parcheggiati; ripresi il 19/10 alle 11:42 (sezione «la ripresa»)

> **Contratto** (21:27, nei file della sessione, `b15-b8-contract.md`), poi il via del coordinatore dopo l'ingresso
> del seguito di B-49 in dev `739bf08e0` (21:40): «GO for B-15 + B-8, reds first, per your contract».
>
> - **B-15**: il 413 di un proxy (corpo non JSON) diventa `proxy_too_large`, in 4 lingue, con il suo caso in
>   `restoreFlow.test.ts`.
> - **B-8**: `backup_busy` porta l'id del job in corso, così la scheda lo segue.
> - **Codice**: le patch in `b15-b8-wip/` (21:42-21:44), mai applicate.
> - **Rossi**, da due test-author, scritti e mai eseguiti:
>   - backend: 25 rossi e 5 guardie in `test_backup_jobs.py`, `test_backup_instance_errors.py`,
>     `test_backup_panel.py`;
>   - frontend: 60 rossi e 20 guardie in `backupApi.test.ts`, `backupJob.test.ts`, `restoreFlow.test.ts`,
>     `restoreI18n.test.ts`.
> - **Doc** modificate: `backup_restore.en.md`, `hosting_providers.en.md`, `security.md`.
> - **⚠️ Fuori pista — il fermo del developer**: congelato subito, senza test, server, Git o agenti nuovi; i due
>   test-author già partiti lasciati finire. Al coordinatore una riga con lo stato.
> - **Parcheggio** (19/10, fase 1 della ripartenza, fino alle 11:10): i 10 file modificati (7 di test, 3 di doc)
>   salvati in `files/parked/b15-b8-reds-docs-on-739bf08e0.patch` (+856/−13), con un `README.md` e 5 domande per
>   il developer; tolti dal worktree con `git apply -R`; la patch rientra pulita su `739bf08e0` (`git apply
>   --check`); `git status --porcelain` vuoto.
> - **Stato**: ⏸️. Le 5 domande le porta il coordinatore al developer; si riprende solo col suo via.

### Ripartenza del 19/10 — pulizia e contabilità (2026-10-19, fino alle 11:30) — 🧊 FROZEN

> **Coordinatore** (19/10): il developer ha letto il resoconto. Per B non c'è lavoro nuovo: Litestream aspetta
> le risposte D1–D10, e B-15/B-8 sono fra i lotti piccoli che sta ancora leggendo. **Regole nuove**: nessuna
> decisione di prodotto da parte mia, solo domande; si implementa solo dopo il via del coordinatore.
>
> - **Fase 1, pulizia** (fino alle 11:10): B-15 + B-8 parcheggiati (sezione sopra). Risposto con il percorso
>   della patch, `git status --porcelain` vuoto e FROZEN.
> - **Fase 2, contabilità**, sulla base `ede7adf75` (avanzamento veloce del coordinatore; HEAD verificato,
>   pulito):
>   - §7: la colonna «Stato (19/10)», con ogni merge verificato in `dev_release2`;
>   - §13: le 85 sezioni in ordine d'inizio, con la nota in alto. Al loro posto la bozza di B1 (dopo
>     B0), quella di B4 (dopo il verde finale di B3), B5a (prima di B1-fix), lo slot pesante 1 (prima
>     dell'accordo con H) e il blocco del 17/10, che andava dal più nuovo al più vecchio;
>   - 16 intestazioni che dicevano un lavoro aperto ora portano l'esito;
>   - backlog, sezione B: 32 righe «In dev» col merge d'ingresso; la riga «Fatto» di B-36; B-4 e B-5 chiuse,
>     perché le aveva già fatte H nel lotto «b-doc-notes» (`d7eb9c5f3`, in dev `0ecc5ed27`); B-8 e B-15
>     «⏸️ Parcheggiata»; nella riga di B-49, la frase su `security.md` (il paragrafo l'ho aggiunto io dopo
>     H-52).
> - **Prove**: gli script (`bookkeeping-1910/` nei file della sessione) verificano ogni voce e ogni sezione
>   prima di scrivere: nel §13 ogni sezione una volta sola, nessuna riga persa; fuori dal §13 cambia solo la
>   tabella del §7. `git diff --check` pulito.
> - **Stato**: 🧊 FROZEN. Aspettano il developer: D1–D10 (B7), le 5 domande di B-15/B-8, la scelta di B-33.
>   B9 e la parte 2 di BZ vengono dopo B7.

### B-15 + B-8 — la ripresa: rossi, cura, verdi (2026-10-19, 11:42-12:40) — ✅ 🧊 FROZEN (checkpoint delle 12:40)

> **Via del coordinatore** (11:42): «VIA per **B-15 e B-8**: il developer ha detto «ok procedi»». Le quattro scelte
> del README del parcheggio, approvate:
>
> 1. la scheda **tiene l'archivio in offerta** (com'è oggi);
> 2. un backup seguito già finito alla prima lettura: **sì**, se ne annuncia la fine;
> 3. **sì**, la scheda ricorda l'id prima della prima lettura;
> 4. il testo di B-15 così com'è, in 4 lingue.
>
> Codice e controlli leggeri subito, con carico sotto 50; le suite pesanti e gli E2E dopo le 14:00, nello slot del
> coordinatore. La domanda 5 del README era solo informativa (l'E2E `createBackup`).
>
> - ✅ **Patch riapplicata** (11:43): HEAD `ca9dbe9e5` (la contabilità committata), pulito. Fra `739bf08e0` e HEAD
>   cambiano 121 file, nessuno dei percorsi del lotto (backup, i18n, E2E delle impostazioni, le tre doc):
>   `git apply --check` pulito, poi `git apply` (10 file, +856/−13, sha256 `a7999e36631fa781…` come al parcheggio).
>   Le due patch di prodotto (`apply_b8_be.py`, `apply_b15_b8_fe.py`) passano `--check` sulla base nuova.
> - ✅ **Rossi** (11:47-11:48, carico 10-12, uno alla volta):
>   - `services backup-jobs`: **19 falliti**, 69 passati. Ragioni giuste: il lock non contiene l'id del job
>     (`''`), e `BackupBusyError has no running`;
>   - Vitest `backupApi.test.ts`, `restoreFlow.test.ts`, `restoreI18n.test.ts`: **53 falliti**, 562 passati. 48 in
>     `backupApi` (non esistono `uploadFailureCode()` né `backupBusyJob()`), 4 in `restoreFlow` (`unexpected` al
>     posto di `proxy_too_large`), 1 in `restoreI18n` (manca la voce di `ERROR_KEYS`);
>   - i rossi API (`api backup-instance-errors`, `api backup-panel`) vogliono il server della corsia, quindi la build
>     di debug: nello slot, con la cura backend tolta per un momento (`git apply -R` delle mie modifiche).
> - **Scelta 3 senza un test**: la cura del 17/10 metteva `#watched` ma non chiamava `#remember()` prima della prima
>   lettura. Se quella lettura fallisce, «Check again» non compare (nessun `followedJobId`), oppure rilegge un id
>   seguito prima. Cura corretta nella patch (`#remember(running.jobId)` prima di `#read`). Rossi chiesti a
>   test-author (TA-B8-Q3, solo `backupJob.test.ts`): l'id ricordato già durante `loading`; una prima lettura senza
>   risposta lascia `canRecheck`, e «Check again» legge quel job; un job sparito si dimentica. Più i testi delle
>   scelte 1 e 2, ora decisioni del developer.
> - ✅ **Cura backend** (11:49): `apply_b8_be.py`, 7 operazioni in `jobs.py` e `job_views.py`.
>   `services backup-jobs` **88 passati**; ruff e black puliti sui 5 file backend.
> - **⚠️ Fuori pista — un 409 che diventerebbe un 500**: `_running_job` prende `(BackupJobNotFoundError, OSError,
>   ValueError)`. Uno stato JSON valido ma malformato (`{}` → `KeyError`; `created_at` numerico → `TypeError`) esce
>   da `_prepare`, e la partenza rifiutata diventa un errore 500. Il modulo, altrove, legge gli stati con
>   `(BackupJobNotFoundError, ValueError, TypeError, KeyError)`. Rosso chiesto a test-author (TA-B8-STATE, due righe
>   in `test_backup_jobs.py`), poi l'`except` allineato.
> - ✅ **Guida, scelta 1**: in «Good to know» di `backup_restore.en.md`, dopo la frase di B-8, «A card that already
>   offers an archive keeps offering it, and only says that another backup runs.»
> - ✅ **Domanda 5, l'E2E** (lettura): con B-8 il clic di `createBackup` potrebbe seguire un backup `ui` lasciato in
>   corso da un altro test. Il test però confronta il job annunciato con quelli avviati dal clic (`owned.jobs`, presi
>   solo dal `job_id` in cima alla risposta del `POST`, mai dal `detail` di un 409): fallirebbe con un messaggio chiaro,
>   come oggi fallisce con `backup_busy`. Con `mode: 'serial'` e la pulizia dell'`afterEach` non resta nessun backup
>   fra un test e l'altro. Nessuna modifica.
> - ✅ **La chiave di B-15** (11:51): `dev.py i18n add backup.restore.errors.proxy_too_large`, nella sorgente
>   `backup/`. Il testo inglese è quello del contratto; IT, FR ed ES usano il registro delle frasi sorelle (tu, vous,
>   tú) e le loro parole («caricamenti», «téléversements», «subidas»). `i18n check` stretto pulito: 5099 chiavi; il
>   diff delle sorgenti è +8/−4.
> - ✅ **Doc** (11:52-11:53, carico 20-28): `mkdocs build` stretta exit 0 (3085 URL risolti), `check-links` pulito,
>   `utils gate-docs-links` 63. Nessun timbro di traduzione: il debito delle tre pagine è vero.
> - ✅ **Rossi della scelta 3** (TA-B8-Q3, solo `backupJob.test.ts`): un gruppo nuovo con 9 righe (3 + 4 + 2).
>   - L'id del job nominato è nello storage già durante `loading`, al posto di un id seguito prima. Mentre la prima
>     lettura è fuori, la scheda non mostra job, errore o fallimento.
>   - Una prima lettura senza risposta (`network`) o senza codice (`unexpected`) lascia `canRecheck`, e «Check again»
>     legge quel job, mai l'altro.
>   - Un job sparito alla prima lettura si dimentica, per la regola di ogni lettura.
>   - I testi delle scelte 1 e 2 dicono ora «deciso dal developer il 19/10».
>   - Le 4 domande di test-author sono risolte da regole che ci sono già: la prima lettura fallita si annuncia
>     (`onFailed` copre ogni richiesta fatta dalla scheda; tace solo `resume()`); non si ritenta (una lettura in
>     `loading` fallisce subito, come in `recheck()`: è il caso della scelta 3); l'id sostituito si perde, come per
>     un avvio riuscito da `failed` («come se l'avesse avviato»), e già con la cura del 17/10; durante la prima
>     lettura nessun errore a schermo (fissato).
> - ✅ **Rosso di `backupJob.test.ts`** (12:00): **16 falliti**, 149 passati: le 9 righe nuove e 7 del 17/10, tutte
>   per la stessa ragione («the job the refusal names must be read»: `[]`). Le 13 guardie sono verdi.
> - ✅ **Rossi dello stato malformato** (TA-B8-STATE, solo `test_backup_jobs.py`): `state-without-fields` (`{}`) e
>   `state-of-wrong-types` (`created_at` numerico) fra le situazioni «non più in corso». L'aiuto `refusals` ora
>   registra un'eccezione diversa da `BackupBusyError` invece di fermarsi. Rosso (12:00): **2 falliti**, 88
>   passati, con `KeyError`/`TypeError` invece del rifiuto.
> - ✅ **Cura** (12:00-12:01): l'`except` di `_running_job` prende anche `TypeError` e `KeyError`, come gli altri
>   lettori del modulo (nella patch e nel worktree). Poi `apply_b15_b8_fe.py`: 6 operazioni in 4 file.
> - ✅ **Verdi leggeri** (12:01-12:05, carico 17-25):
>   - Vitest di tutta la feature `backup`: 9 file, **971 passati**;
>   - `services backup-jobs` **90**, `services backup-leftovers` 44, `services backup-secure` 77,
>     `utils backup-cli` 102, `utils gate-i18n-catalog` 176;
>   - ruff e black puliti sui 5 file backend; prettier pulito sui 12 file frontend (8 `.ts`, 4 `.json`);
>   - `api sync` exit 0: la descrizione del 409 nell'OpenAPI; `front check` 0 errori e 0 avvisi.
> - **⚠️ Fuori pista — B-50**, difetto precedente a B-8 trovato da TA-B8-STATE: uno `state.json` che è JSON ma non un
>   oggetto fa alzare `AttributeError` a `remove_expired_jobs` a ogni partenza (500); `get_job` lascia passare
>   `KeyError`/`TypeError` (il GET di quel job è un 500). Ci si arriva solo manomettendo il file o con un disco
>   rovinato. Fuori dal lotto: riga B-50 nel backlog.
> - **Domanda per il developer** (non decido io): per il contratto del 17/10, fissato dal test API (d), il 409 della
>   scheda nomina il job in corso **di qualunque origine** (`ui`, `panel`, `cli`, `pre-restore`). Il frontend segue
>   solo `ui`, ma un admin che legge la risposta impara l'id di un backup del pannello. Finché gira non lo può
>   cancellare; finito, può scaricarlo o cancellarlo con le rotte della scheda. Prima di B-8 quell'id non era mai
>   visibile all'admin. L'alternativa è nominare solo i job della stessa origine di chi chiede (scheda → `ui`): la UI
>   è identica, e costa una riga, i parametri del test (d) e una frase di `security.md`. Resta com'è finché il
>   developer non sceglie.
> - **Slot** (dopo le 14:00, chiesto al coordinatore): `b15b8_slot.sh red`, poi `green`.
>   - `red`: la cura backend tolta per la durata (`b8-backend-cure.patch`, 123 righe, rimessa da un `trap`), poi
>     `api backup-instance-errors` e `api backup-panel`. Il primo avvio costruisce una volta il frontend di debug.
>   - `green`: quelle due, `api backup`, `api backup-secure`, `api instance-block`, `e2e backup-roundtrip`,
>     `front-utility backup`.
> - **Coordinatore** (12:08): porta la domanda sul 409 al developer, con il suo consiglio di nominare solo la stessa
>   origine; intanto resta com'è. Lo slot viene dopo quello di X (12:08 – 13:00 circa), al suo «slot tuo».
> - **Variante pronta, non applicata**: `b15-b8-wip/apply_b8_same_origin.py` (`--check` OK, 3 operazioni):
>   - la condizione di `start_job` diventa `running.origin == origin`, con il suo commento;
>   - la descrizione OpenAPI del 409;
>   - il paragrafo di `security.md`.
>
>   Se il developer la sceglie, prima i rossi: test-author cambia il caso (d) di `test_backup_instance_errors.py`
>   (`ui` nominato; `panel`, `cli` e `pre-restore` col solo `{code, message}`), poi la variante.
> - ✅ **Slot** (coordinatore, «slot tuo» 12:23, fino alle 13:15; ogni corsa col carico a 1 minuto sotto 50):
>   - `red` (12:22-12:26): cura backend tolta (`backend cure: removed`). `api backup-instance-errors` **5 falliti**, 11
>     passati: il 409 senza `job_id`/`origin` per `ui`, `panel`, `cli` e `pre-restore`, e l'OpenAPI senza la frase.
>     `api backup-panel` **1 fallito** (PANEL-023), 65 passati. Il primo avvio ha costruito il frontend di debug
>     (svelte-check 0/0). Poi la cura è stata rimessa: sha256 della patch e del diff uguali (`9c38907c…`).
>   - `green` (12:26-12:32):
>     - `api backup-instance-errors` 16, `api backup-panel` 66, `api backup` 23;
>     - `api backup-secure` 24, `api instance-block` 62;
>     - `e2e backup-roundtrip` 3, `front-utility backup` **14** (1,4 min), senza instabili né saltati.
>   - Porta 6187 libera. Nella cartella dati restano solo lo scheletro di `.restore` (i lock, cartelle vuote) e
>     `backups/.jobs/.lock`, che contiene l'id dell'ultimo job: l'E2E l'ha cancellato, quindi non nomina niente.
> - ✅ **Backlog**: B-8 e B-15 ✅ (fatte il 19/10); B-50 nuova.
> - **CHANGELOG**: nessuna riga proposta. Backup e ripristino sono nuovi nella 1.3, come per B-49.
> - ✅ **Checkpoint** (12:40), 🧊 FROZEN.
>   - Commit proposti:
>     - `fix(backup): B-8 busy job id, B-15 proxy 413`: codice, test, i18n e doc, 20 file;
>     - `docs(journal): B-15 + B-8 done, B-50 filed`: questo piano e il backlog.
>   - Aperte: la domanda sul 409 di qualunque origine (variante pronta, non applicata) e B-50.

### N74 di W — revisione: Fineco tiene solo le righe regolate, il batch arriva a domani (2026-10-19, 16:05-16:38) — ✅ 🧊 FROZEN

> **Richiesta** (coordinatore, 16:05): revisione di **N74 di W**, commit `8a86011ce` sul ramo
> `e-alfy-w-import-e-transazioni`, fuso con dev in `a68a26a75`. Da verificare: che «oggi» e «domani» vengano dal
> server, mai dal browser; che una riga esclusa porti con sé FEE e premio, senza cassa orfana; che la nota non sia un
> avviso (ambra contro blu); che il cambio di versione dei due plugin faccia proporre la rilettura; le date del batch
> contro `range-ceiling` (N83) e J-49. Solo lettura e test leggeri, carico sotto 50. La mia base: `8cc416905`.
>
> **Metodo**:
>
> - `a68a26a75` non è nella mia base: letto con `git show` e `git grep` (28 file, +980/−150). Il merge tocca uno solo
>   dei file di N74, `assets/architecture.md`, dal lato di dev. Migrazioni e `backend/app/db` uguali alla mia base.
> - Corsia ripopolata come chiesto: `db populate --force --clean` (16:13, exit 0, 22 s).
> - Test leggeri dall'albero di `a68a26a75`, estratto con `git archive` nella cartella di sessione (`review-n74/tree`,
>   fuori da git): `node_modules` in copia APFS di quelli del mio worktree (`cp -c`), poi `svelte-kit sync` e
>   `api sync` nell'albero. Script `files/scripts/n74_review.sh`, un passo alla volta, carico fra 17 e 48.
> - **⚠️ Fuori pista**: il primo Vitest falliva prima di raccogliere (mancava `.svelte-kit/tsconfig.json`, e Vite non
>   carica un `node_modules` raggiunto con un link simbolico). Infrastruttura: risolta con la copia e `svelte-kit
>   sync`, nessun test di prodotto coinvolto.
>
> **Esito per punto**, tutti ✅:
>
> 1. **Oggi e domani dal server.**
>    - Fineco legge `server_today()` (`date.today()` del processo che legge il file, nel pool del server) una volta
>      per lettura. Il wizard rilegge a ogni analisi (`POST /files/{id}/parse`) e non usa la cache del backend: una
>      riga regolata entra alla lettura successiva.
>    - Il batch: `transaction_date_bounds()` vale 1900-01-01 … `latest_range_end()`, cioè `server_today()` più un
>      giorno, letto una volta per batch. Prima era l'oggi UTC più un anno: ora c'è un solo calendario, quello del
>      server, lo stesso di X-R55 e N83.
>    - Il frontend non ha copie del limite: il messaggio usa il `params.max` del server, e `SingleDatePicker` resta
>      fermo all'oggi del browser, come prima. I test fissano `server_today` sul modulo del plugin, mai l'orologio.
> 2. **FEE e premio, nessuna cassa orfana.** Il controllo `tx_date > today` viene subito dopo la data, prima della
>    descrizione, del tipo, dell'asset e di ogni transazione. Così una riga resta fuori intera: niente BUY o SELL,
>    niente FEE (le colonne delle commissioni sono della stessa riga), niente INTEREST del rimborso sopra la pari,
>    nessun asset estratto. L'export dei titoli di Fineco non ha righe di cassa separate. Per Danske cambia solo la
>    gravità: le operazioni con la valuta dopo l'ultimo giorno dell'estratto conto non hanno ancora la loro cassa in
>    quel file (il caso simmetrico è `deferred_rows`).
> 3. **Una nota, non un avviso.**
>    - `severity="info"` per `fineco_not_yet_settled`, `fineco_incomplete_rows` ed `excluded_not_yet_settled` di
>      Danske; gli altri `excluded_*` restano avvisi (una guardia di W lo fissa).
>    - `BrimNoticeList`: icona Info e `text-lf-info`, il blu; il link «open an issue» prende il tono della nota.
>    - La conferma del passo 3 mette le note sotto «Informational notes» (`lf-info-*`), e il pulsante è blu se ci
>      sono solo note.
>    - Nel dettaglio di una lettura ogni nota ha il suo colore.
> 4. **La rilettura.** `parse_is_stale` confronta la versione del registro con `parsed_plugin_version`, scritta a ogni
>    lettura riuscita: Fineco passa da 1.1.0 a 1.2.0, e il file mostra «Stale» al passo 2. Per i set di Danske
>    (1.0.0 → 1.0.1) c'è `combine_is_stale`: il badge «To re-combine» («Built by an older version of the plugin…»).
>    In più, ogni analisi rilegge comunque: la versione nuova vale dalla prima analisi.
> 5. **Le date del batch, N83 e J-49.**
>    - L'ultimo giorno è lo stesso di prezzi e cambi (X-R65 e N83: domani). Il primo è diverso di proposito:
>      1900-01-01 per le transazioni; per prezzi e cambi nessuno, dalla revisione di N83 del 19/10. Il merge lo dice
>      giusto in `assets/architecture.md` («Transactions keep their own floor, 1900-01-01 since N74, and the same
>      last date»).
>    - J-49: `transaction_batch_stages` ora legge `latest_range_end` per nome ed è in `RANGE_BOUND_CONSUMERS`.
>      `TestRangeBoundSeamCoversEveryReader` è verde (11).
>    - Le dieci suite «far-future» (dati fra il 2032 e il 2091) con `lift_range_bound` scrivono le righe direttamente,
>      senza il batch: non toccate.
>    - Chi crea transazioni future passando dal batch: solo `test_brokers_api` (una riga a domani, che passa).
>      `populate_mock_data` scrive senza batch e nel passato; nessuna E2E usa date future.
>    - Una riga già salvata con una data oltre domani resta modificabile: il frontend manda solo i campi cambiati
>      (`buildUpdateDiff`), e `check_dates()` controlla un aggiornamento solo se porta una data.
>
> **F1, da correggere: il CHANGELOG** (è del coordinatore). In `[Unreleased]` › 🐛 Fixed, la riga 288 dice ancora
> «…transaction dates outside 1 January 1900 – one year from today are refused…»: ora è «– tomorrow». N74 non porta
> righe sue. Quelle visibili all'utente: Fineco lascia fuori le righe non ancora regolate, con una nota blu, e
> segnala le righe senza un numero necessario, con un link per aprire una issue; per Danske le operazioni non ancora
> regolate sono una nota, non più un avviso.
>
> **F2, una domanda** (per W o il developer: non decido io). La regola 9 della skill e della guida dice che una riga
> «con la data valuta o di regolamento dopo oggi» è provvisoria e resta fuori.
>
> - Cinque plugin hanno una colonna di regolamento ma datano per operazione e importano tutto:
>   - Directa (`Data valuta`), Saxo (`Value Date`), InvestEngine (`Settlement Date`);
>   - Degiro (la data valuta), Disnat (`Date de règlement`, che usa solo quando manca la data dell'operazione).
>
>   Le loro righe passano il batch (data fino a oggi), ma alla lettera della regola sarebbero provvisorie.
> - Il generic CSV accetta `settlement_date` e `value_date` come colonna della data. Una data di regolamento oltre
>   domani ora fa rifiutare il salvataggio (`dateOutOfRange`); prima passava fino a un anno.
> - Da chiarire: la regola vale per chi data per valuta (Fineco) o per periodo (Danske), oppure quei plugin chiedono
>   un seguito.
>
> **Residui**, nessuno blocca:
>
> - R1, precedente a N74: la colonna «⚠️» della tabella dei risultati conta tutte le note, anche quelle informative
>   (tooltip «Parser warnings…»). Un file Fineco con solo righe non regolate mostra «⚠️ 1»; e nel dettaglio la sezione
>   s'intitola «Warnings».
> - R2: il testo di `fineco_not_yet_settled` parla di «data valuta», ma la regola usa la data dell'operazione quando
>   la valuta manca. È un dettaglio di parole.
> - R3: le pagine IT, FR ed ES del form e dell'import danno ancora l'esempio di un anno (`2027-10-17`). È debito di
>   traduzione normale: non va timbrato.
> - R4, fuori da N74: `scripts/test_runner/_frontend_transaction.py` non passa ruff (4 PLC0415) né black già sulla mia
>   base. `scripts/` è fuori dal cancello di `dev.py lint`.
>
> **Prove**, tutte sull'albero di `a68a26a75`, verdi:
>
> - Vitest `BrimNoticeList`, `resolveValidationMessage.decimals`, `ParseDetailModal`: 3 file, 65 test;
> - `utils datetime` 44; `external brim-providers` 750 (1 saltato); `external brim-danske-bank` 325;
> - `services range-ceiling` 74; J-49 (`roi-fifo-utils TestRangeBoundSeamCoversEveryReader`) 11;
> - `services transaction-decimal-places` (le due classi delle date) 16; `services edge-cases` (le due date) 2;
> - ruff e black puliti sui 10 file backend; prettier pulito sui 7 file frontend;
> - `i18n check` stretto (5105 chiavi); `front check` 0 errori e 0 avvisi;
> - le ancore delle doc nuove esistono tutte. Porta 6187 libera.
>
> - **Backlog**: B-51 (R1) e B-52 (F2) nuove, area di W.
> - **Pulizia**: l'albero estratto è tolto alla fine; gli script e i log restano nella cartella di sessione.
> - **Commit proposto**: `docs(journal): B review of W N74`. 🧊 FROZEN.

### B-8, seguito — la scheda dice solo «occupato», la console nomina il job (2026-10-19, 16:38-17:15) — ✅ 🧊 FROZEN (checkpoint delle 17:15)

> **Il developer** (relayed dal coordinatore alle 16:38, testuale): «farei che a schermo compare solo "occupato", in
> console magari più dettagli per permetterci di backuppare se serve, non è in vista ma se venisse letto da un utente
> non sarebbe grave». **Coordinatore**: la risposta 409 resta com'è (id e origine del job); la scheda mostra solo
> «occupato», senza nominare il backup, qualunque sia l'origine; in console id, origine e stato del job, sempre (non
> al livello di log di H-60); nessun dato personale. Poi il lotto aggiornato sul ramo, con i rossi e un checkpoint
> nuovo.
>
> - ✅ **Base**: HEAD `05dc41906` (la revisione di N74 committata alle 16:38), pulito; B-15 + B-8 (`0b8037b75`) è sul
>   ramo, non ancora in dev.
> - ✅ **Lettura** (16:38-16:41):
>   - la card non nomina mai il job: per un `backup_busy` mostra solo «Another backup is running: try again when it
>     ends.» (`backup.download.errors.backup_busy`), anche nel toast; seguendo un job `ui` ne mostra l'avanzamento e
>     poi l'archivio, mai id né origine. Quindi «la scheda non nomina» è già vero: una guardia, non un rosso; il rosso
>     è la riga in console;
>   - `$lib/debug` scrive solo nelle build di debug (un no-op tolto dal minificatore in produzione): non va. H-60 non
>     è in dev. Nessuna regola contro `console.*` (nessun ESLint, Vitest non fallisce sulla console; 117 usi nel
>     codice di prodotto): un `console.warn` mirato;
>   - lo stato non è nella risposta, che resta com'è: il server nomina un job solo mentre il suo stato dice che gira
>     (`jobs._running_job`), quindi la riga dice `running`.
> - ✅ **Domanda al coordinatore** (16:41): per un job `ui` nominato senza archivio in offerta, la scheda continua a
>   seguirlo o mostra solo «occupato»? **Risposta** (16:43): **continua a seguirlo** — il «solo occupato» del
>   developer riguardava il nominare i backup degli altri (gli id del pannello); seguire il proprio `ui`, senza
>   mostrare id né origine, è la scelta 1–3 di stamattina. Il resto come proposto. Via, con i rossi.
> - **Contratto** (`files/b8-console-contract.md`): un solo `console.warn` per ogni partenza rifiutata `backup_busy`
>   che nomina un job, seguito o no: una stringa (testo libero), poi esattamente
>   `{job_id, origin, status: 'running'}`; nessuna riga per un rifiuto che non nomina un job, per gli altri errori,
>   per le letture successive. Rossi e guardie a TA-B8-CONSOLE (`backupJob.test.ts`, `BackupDownloadCard.test.ts`,
>   sola scrittura). La cura: `apply_b8_console.py` (2 operazioni in `backupJob.svelte.ts`: il commento del modulo e
>   la riga; `--check` OK, non applicata).
> - ✅ **Doc** (16:44): `security.md`, nel paragrafo della partenza, «la scheda non nomina; la risposta sì» (la card
>   dice solo che un altro backup gira, o segue il suo; id, origine e stato `running` vanno in console con un
>   `console.warn` per rifiuto, a ogni livello di log; nessuno dei tre è un dato personale); `backup_restore.en.md`,
>   la riga 🚦: la card non dice quale backup gira, la console del browser sì (l'id e da dove è partito).
> - ✅ **Doc, i controlli** (16:49-16:51, carico 30-40): `mkdocs build` stretta exit 0 (3085 URL risolti),
>   `check-links` pulito, `utils gate-docs-links` 63.
> - ✅ **Rossi** (TA-B8-CONSOLE, 16:45-17:07, sola scrittura):
>   - `backupJob.test.ts`, 16 rossi:
>     - ogni origine, senza archivio in offerta (il job `ui` seguito compreso);
>     - un job `ui` trovato già finito, fallito, sparito o senza risposta alla prima lettura;
>     - ogni origine con un archivio in offerta;
>     - tre rifiuti di fila danno tre righe;
>     - la riga scritta una volta sola, al rifiuto: né il seguito, né una lettura fallita, né `recheck()` o `resume()`
>       ne aggiungono altre.
>   - Più 20 guardie: nessuna riga per un rifiuto che non nomina un job (o con id o origine non validi), per gli altri
>     errori, per una partenza riuscita, per `resume()`, per «Check again».
>   - Nei quattro gruppi B-8 di prima, `console.warn` è zittita, senza cambiare nessuna asserzione.
>   - `BackupDownloadCard.test.ts`, 10 rossi (la riga attraverso la card) e guardie a schermo, per ogni origine:
>     - con niente in offerta, solo la frase «occupato» nell'avviso;
>     - con un archivio in offerta, l'archivio e la frase;
>     - un job `ui` seguito fino all'archivio senza id né `ui` nel testo; il toast dice la frase.
>     - Le «needle» (l'id ovunque, l'origine come parola intera) hanno una premessa verificata: assenti nella card
>       «occupato» semplice, presenti in una frase o una chiave che nomina il job, assenti in `build`, `ui_`,
>       `panels`, `pre-restored`.
> - ✅ **Rosso** (17:08, carico 37): **26 falliti**, 259 passati. Gli 11 messaggi distinti (Vitest raggruppa quelli
>   uguali) dicono tutti `expected "warn" to be called N times, but got 0 times`; nessun fallimento ha un'altra
>   causa.
> - ✅ **Cura** (17:09): `apply_b8_console.py`, 2 operazioni in `backupJob.svelte.ts` (+7 righe).
> - ✅ **Verdi** (17:09-17:14):
>   - Vitest di tutta la feature `backup`: 9 file, **1028 passati**;
>   - prettier pulito sui 3 file;
>   - `front check` 0 errori e 0 avvisi.
> - **⚠️ Fuori pista**: il primo `front check` (17:11) trovava 4 errori su `scope_boundary` nei file dei lotti (non
>   miei). Il client generato era delle 12:23, di prima del merge di dev delle 15:16, che ha portato il campo. Dopo
>   `api sync` (exit 0): 0 errori.
> - **Le 8 domande di test-author**, chiuse dal contratto o dalla cura, senza decisioni nuove:
>   - la riga ha due argomenti, e i test fissano solo quelli;
>   - un rifiuto arrivato dopo `dispose()` o `reset()` è scartato prima della riga (il controllo `#stale`);
>   - la riga c'è già prima che la prima lettura risponda;
>   - nessuna deduplica: due rifiuti dello stesso job danno due righe;
>   - lo stato è quello del rifiuto, `running`, anche se la prima lettura trova il job finito;
>   - «a schermo» è il testo: l'`href` del link di un archivio in offerta contiene il suo id per costruzione, come
>     prima di B-8;
>   - un avviso di Svelte in dev romperebbe il conteggio, e la precondizione «niente scritto prima» lo mostrerebbe;
>   - un `backup_no_space` con `job_id` non scrive righe (il server non lo manda).
> - ✅ **Backlog**: nella riga di B-8, la domanda sul 409 è chiusa dal developer.
> - **CHANGELOG**: nessuna riga (backup e ripristino sono nuovi nella 1.3).
> - ✅ **Checkpoint** (17:15), 🧊 FROZEN. Commit proposti:
>   - `fix(backup): busy card stays silent, console names job`: `backupJob.svelte.ts`, i due test, le due doc;
>   - `docs(journal): B-8 busy console, developer decision`: questo piano e il backlog.

### B-50 + B-51 — analisi (2026-10-19, 17:17-17:22) — 🧊 inviata al coordinatore, prima del codice

> **Richiesta** (coordinatore, 17:17, dopo il commit di B-8 `a3e0f4c8e` + `ae59f158a`): niente in coda per B, quindi
> un'analisi breve di B-50 (il 500 vicino) e di B-51 (la colonna «⚠️» conta anche le note blu). Sola lettura.
>
> **B-50, misurato** con due sonde pure in una cartella temporanea, tolta alla fine (`files/b50-analysis/`):
>
> | `state.json` di un job | `get_job` | `remove_expired_jobs` | `end_interrupted_jobs` | una partenza (`_prepare`) |
> |---|---|---|---|---|
> | `[]`, `null`, `5`, `"x"` | `AttributeError` | `AttributeError` | `AttributeError` | `AttributeError` |
> | vuoto, JSON non valido | `JSONDecodeError` | ok | ok | ok |
> | `{}`, `created_at` numerico o non data | `KeyError`, `TypeError`, `ValueError` | ok | ok | ok |
>
> - Un JSON che non è un oggetto blocca ogni nuova partenza: scheda e pannello ricevono un 500 senza codice
>   (`start_job` prende solo `BackupBusyError`, `BackupPathError`, `OSError`), la CLI un traceback. Dura finché
>   qualcuno toglie la cartella a mano. All'avvio la pulizia dei job si ferma lì; `sweep_backup_leftovers` lo
>   registra e prosegue.
> - **Lo stesso buco c'è nel ripristino**: `restore_jobs._read_state` fa `record.get(...)` su un JSON non oggetto.
>   L'`AttributeError` non è preso (`OSError, ValueError, TypeError`), quindi `_checks()` e `prune()` falliscono, e
>   con loro ogni nuova verifica (`start_check` → `prune`) e ogni fine di caricamento (`_remove_replaced_uploads`).
>   Un file vuoto o `{}` invece è ignorato. I lettori basati su pydantic (`apply`, `outcome`, `staging`,
>   `manifest`) sono sani.
> - Gli altri stati rovinati rompono solo `get_job`: GET, file e DELETE di quel job rispondono 500. La cartella
>   scade dopo un'ora (mtime), quindi la cosa si risolve da sola.
> - Come ci si arriva: a mano, o con un disco rovinato. Un file vuoto anche da un'interruzione di corrente:
>   `_write_state` non fa `fsync`, e durante un job scrive ogni 0,5 s.
> - **Cura proposta**, piccola (circa 10 righe in 2 file, nessuna migrazione né i18n):
>   1. `BackupJob.from_json` e `restore_jobs._read_state`: un documento che non è un oggetto diventa l'errore che i
>      chiamanti già prendono (`ValueError`, `None`);
>   2. `get_job`: uno stato illeggibile è «non trovato» (404 `backup_job_not_found`, che scheda e pannello sanno già
>      trattare), con un log dell'id e della classe dell'errore. La cartella resta fino alla scadenza. È quello che fa
>      già il ripristino con un controllo illeggibile.
>
>   Niente `fsync`: costerebbe a ogni progresso.
> - **Domanda** (non decido io): va bene il 404 per uno stato illeggibile? L'alternativa è un 500 con un codice suo,
>   che la scheda mostrerebbe come errore inatteso e che «Check again» ripeterebbe.
> - Test: righe pure nelle suite dei job e del ripristino; un caso API (GET → 404) nello slot.
>
> **B-51, lettura su dev** (area di W):
>
> - `ImportWizardModal.svelte`, colonna `warningCount`: intestazione «⚠️», tooltip «Parser warnings (skipped rows,
>   ambiguous data)», cella `row.response.warnings.length`. Conta ogni nota, anche le `info`.
> - Note `info` su dev: Scalable e Scalable deposit (5 codici), Danske (4), Fineco (2), Crédit Agricole (2). Non
>   riguarda solo Fineco: un file Scalable con dividendi netti mostra «⚠️ 1».
> - Il dettaglio di una lettura (`ParseDetailModal`) mette le note sotto «Warnings» («No warnings» quando non ce ne
>   sono), ognuna col suo colore. La conferma del passo 3 invece separa già «Informational notes» e «Needs your
>   attention».
> - C'è un precedente: `DataQualityBanner` e `LotDataQualityBanner` contano gli avvisi a parte e hanno un titolo per
>   le sole note (`dataQuality.headerInfoOnly`).
> - **Opzioni** (UI, per W o il developer):
>   - (a) la colonna conta solo gli avvisi;
>   - (b) due numeri nella cella, ⚠️ ambra per gli avvisi e ℹ️ blu per le note, quando ci sono;
>   - (c) l'icona del livello più grave, con il totale.
>
>   Consiglio (b), e nel dettaglio due sottosezioni come nella conferma del passo 3.
> - Costo piccolo, solo frontend: la cella, il tooltip e il titolo in 4 lingue. Oggi nessun test tocca la colonna né
>   la sezione: conviene estrarre il conteggio in una funzione pura con un suo test Vitest. Il file è di W.

### B-8, difetto della revisione automatica — una richiesta sicura che segue il backup in chiaro di un altro (2026-10-19, 17:22-18:10) — ✅ 🧊 FROZEN (checkpoint delle 18:10)

> **Il difetto** (revisione automatica prima dell'ingresso di B-15 + B-8, girata dal coordinatore):
>
> - Se `start(password)` riceve un 409 che nomina un job `ui` in corso, la scheda lo segue senza guardare la
>   modalità (`backupJob.svelte.ts:151-157`). Il job può essere di un'altra scheda o di un altro admin, in chiaro.
> - `create()` ha già svuotato i campi della password (`BackupDownloadCard.svelte:100-102`). Alla fine la scheda
>   mostra «Archive ready» per uno `.zip` in chiaro, e `onDone` lancia `backup.created` come se fosse il backup di B.
> - L'avviso di privacy compare solo con `mode === 'clear'` (`:127`): B può salvarlo credendolo cifrato. Al
>   contrario, chi chiede in chiaro riceve un `.lfbk` con la password di A.
> - Il client non può controllare prima: `encrypted` resta `False` fino alla fine (`jobs.py:291`). Nessun test di
>   B-8 partiva con una password.
>
> **Cura del coordinatore**: alla fine del job seguito, confrontare `job.encrypted` con la modalità richiesta; se non
> coincidono, niente presentazione e niente `onDone`, e «occupato». Chiede se preferisco non seguire affatto da un 409
> quando c'è una password, e perché.
>
> **Verificato** (17:23): i campi di `BackupJob` non hanno né utente né sessione, quindi il server non sa chi ha
> avviato un job. `encrypted` (righe 291 e 297) dice la modalità, non la chiave; la fase `encrypting` c'è solo per un
> sicuro. La card mostra `backup-encrypted-note` quando `job.encrypted`.
>
> **La mia risposta** (17:24): non seguire con una password; per le richieste in chiaro, il controllo alla fine.
>
> - Il controllo da solo lascia aperto «sicuro → sicuro» di un altro admin: offerto a B come suo, ma la password di
>   B non lo apre. Per una richiesta sicura va bene solo il suo job, e nulla prova che quello del 409 lo sia.
> - Il costo: un backup sicuro la cui risposta si è persa resta «occupato» finché il job non finisce, come prima di
>   B-8; il suo archivio scade dopo un'ora.
> - Proposta:
>   - `start(password)` con un 409 che nomina un job `ui`: niente seguito, `failed` con `backup_busy`;
>   - `start()` in chiaro: seguito, ma un job che finisce con `encrypted: true` (sondaggio, prima lettura già finita,
>     «Check again») non viene presentato. Niente `onDone`, l'id adottato si dimentica, `failed` con `backup_busy` e
>     `onFailed` una volta.
> - Cura esatta, dopo la 1.3: un id di richiesta salvato nel job e confrontato nel 409.
> - I rossi aspettano la decisione: i casi «sicuro» cambiano fra le due cure.
> - ✅ **Decisione** (coordinatore, 17:37): «confermo la tabella di destra. Con una password, dal 409 nessun seguito;
>   in chiaro, il controllo alla fine (`encrypted: true`, quindi non presentato, id dimenticato, `backup_busy`)».
>   Via ai rossi e alla cura, commit a parte. L'id di richiesta generato dal client va in `PROSSIMI_LAVORI.md`, dopo
>   la 1.3. Nello stesso messaggio: B-50 sì (404 `backup_job_not_found` per uno stato illeggibile, nel backup e nel
>   ripristino), dopo B-8; B-51 a W, con la proposta dei due numeri.
> - ✅ **Contratto** (`files/b8-mode-contract.md`, 17:40). Un dettaglio mio, di completezza e non di prodotto:
>   l'adozione (un job seguito da un 409 per una richiesta in chiaro) si ricorda anche in `sessionStorage`, chiave
>   nuova `librefolio.backup.adopted`. Senza, un ricaricamento durante il seguito la perde: `resume()` riprende l'id
>   (la scelta 3 lo salva proprio per questo) e alla fine offrirebbe un `.lfbk` altrui. I percorsi che non adottano
>   non toccano lo storage più di oggi. Rossi a TA-B8-MODE (`backupJob.test.ts`, `BackupDownloadCard.test.ts`, sola
>   scrittura).
> - **Cura pronta, non applicata**: `apply_b8_mode.py`, 8 operazioni in `backupJob.svelte.ts` (`--check` OK):
>   - la condizione del seguito più `password === undefined`;
>   - `#adopted`, con `#adopt()`, `#unadopt()` e la lettura del segno nel costruttore (un segno che nomina un altro
>     id si scarta); `#forget()` toglie anche l'adozione;
>   - in `#settle()`, un `done` adottato e `encrypted` → `#forget()` e `#fail('backup_busy', 'start', null, news)`;
>   - un avvio riuscito toglie un'adozione rimasta;
>   - il commento del modulo.
> - ✅ **Doc** (17:42):
>   - `security.md`: nella frase di B-8, il seguito solo per una richiesta in chiaro e solo se finisce in chiaro,
>     l'adozione tenuta fra i ricaricamenti, una richiesta sicura mai. Riavvolte solo le righe cambiate (5 → 8);
>   - `backup_restore.en.md`, la riga 🚦: vale solo per un backup in chiaro, e negli altri casi la card dice che un
>     altro backup gira.
> - ✅ **Rossi** (TA-B8-MODE, 17:43-18:04, sola scrittura):
>   - `backupJob.test.ts`, 5 gruppi, 25 rossi e 16 guardie:
>     - una richiesta sicura non segue mai, ed è rossa anche quando il job nominato è il suo, che resta da rileggere
>       con «Check again»;
>     - l'adozione si ricorda dal primo momento;
>     - la fine di un job adottato: cifrata → non presentata; fallita o sparita → come oggi, con la chiave tolta;
>     - il ricaricamento (`resume()` fa lo stesso controllo);
>     - la pulizia: un avvio riuscito toglie un'adozione rimasta, un segno che non nomina il job seguito si scarta;
>   - le guardie: un sicuro avviato qui che finisce cifrato è offerto come oggi; nei percorsi senza adozione
>     nessuna chiamata in più allo storage;
>   - `BackupDownloadCard.test.ts`: 2 rossi (sicuro → «occupato» senza seguito; chiaro → fine cifrata non
>     presentata) e una guardia (chiaro → fine in chiaro offerta, con l'avviso di privacy);
>   - la chiave nuova si legge come stringa, più un solo test sull'export per `Reflect.get`: nessun rosso cade su un
>     import.
> - ✅ **Rosso** (18:05, carico 15): **27 falliti**, 302 passati. Le ragioni sono quelle attese: la richiesta sicura
>   seguita (`api.get` chiamato), la chiave di adozione assente, l'archivio cifrato offerto (`done` al posto di
>   `failed`). Nessun errore di import o di sintassi.
> - ✅ **Cura** (18:06): `apply_b8_mode.py`, 8 operazioni in `backupJob.svelte.ts` (+56/−1).
> - ✅ **Verdi** (18:06-18:08):
>   - Vitest dell'intera feature `backup`: 9 file, **1072 passati**;
>   - prettier pulito sui 3 file; `front check` 0 errori e 0 avvisi;
>   - `mkdocs build` stretta, `check-links`, `utils gate-docs-links` 63.
> - **Le domande di test-author**, risolte dalle regole che ci sono già, senza decisioni nuove:
>   - un archivio adottato e offerto in chiaro tiene il segno, che si toglie con il job (o con un avvio nuovo);
>   - dopo un ricaricamento, una prima lettura senza risposta e poi «Check again» che trova il job cifrato: non
>     presentato e non annunciato, perché il job non era stato visto girare (la regola di sempre).
> - **Caso limite, da sapere (una domanda per il coordinatore):** una richiesta in chiaro rifiutata dal backup
>   sicuro della scheda stessa (avviato qui, con il sondaggio che si era arreso) lo adotta. Alla fine è cifrato,
>   quindi non presentato e dimenticato, anche se è il suo. Con «Check again» al posto di «Create» lo si ritrova.
>   Rifinitura possibile: non adottare il job che la scheda segue già senza averlo adottato. Cambia la tabella
>   decisa, quindi non l'ho fatta.
> - **Fuori dal lotto**: il backend non cambia, quindi niente API ed E2E. Nessuna riga di CHANGELOG (backup nuovo
>   nella 1.3).
> - ✅ **Checkpoint** (18:10), 🧊 FROZEN. Commit proposti:
>   - `fix(backup): secure start never follows another backup`: `backupJob.svelte.ts`, i due test, le due doc;
>   - `docs(journal): B-8 mode defect, B-50/B-51 analysis`: questo piano e il backlog.

### B-8, rifinitura — il job che la scheda segue già da sé non si adotta (2026-10-19 18:10 → 2026-10-20 09:05) — ✅ 🧊 FROZEN (checkpoint delle 09:05)

> **Coordinatore** (18:10): B-8 committato, `adedb0c9c` (`fix(backup): secure start never follows another backup`) e
> `bc913e487` (il giornale); la memoria dell'adozione in `sessionStorage` va bene. «Il caso limite: sì alla
> rifinitura, decisione mia, perché è nello spirito della tabella («si segue solo il proprio»): non adottare un job
> che la scheda sta già seguendo da sé. Commit a parte con un rosso, piccolo, prima di B-50.» B-15 + B-8 entra in dev
> fino a `bc913e487`, con un gate; la rifinitura dopo.
>
> - **Avviso di A** (coordinatore, 18:09): per N69, A cambia la barriera di FBKP-001 in `e2e/settings/backup.spec.ts`
>   (riga 264). Un utente normale non vede più «Amministrazione»: la barriera diventa «About visible, administration
>   count 0». Ha l'ok del coordinatore. B-8 non tocca quella spec.
> - **La rifinitura**: una richiesta in chiaro rifiutata da un 409 che nomina il job `ui` che la scheda segue già da
>   sé (`followedJobId`, non adottato) lo segue come suo: niente adozione, quindi alla fine è offerto qualunque sia la
>   modalità. La strada sicura non cambia: una richiesta sicura non segue mai, il suo job compreso; si torna con
>   «Check again», come fissa il gruppo 1.
> - **Cura pronta, non applicata**: `apply_b8_own.py`, 1 operazione: si adotta solo se il job nominato non è quello
>   seguito, o se quello seguito è già un'adozione. `--check` OK.
> - **Rossi** a TA-B8-OWN (solo `backupJob.test.ts`, sola scrittura):
>   - due rossi: il proprio backup sicuro, avviato qui o ricordato da una pagina precedente, che finisce cifrato
>     viene offerto;
>   - due guardie: un job che non è quello seguito, o quello seguito come adozione, resta adottato.
> - ✅ **Doc** (18:12):
>   - `security.md`: il backup che la scheda segue da sé si segue come suo, mai adottato (3 righe al posto di 1);
>   - `backup_restore.en.md`, la riga 🚦: «…is not offered, unless the card had started it itself».
> - **⏸️ PAUSA GENERALE del developer** (coordinatore, 18:12): la macchina si spegne e /tmp verrà ripulito. Fermare
>   corse e server, mettere per iscritto lo stato, niente git. **Stato al fermo (18:16):**
>   - porta 6187 libera; nessuna corsa né server della corsia attivi;
>   - HEAD `bc913e487`; **sporchi 3 file**: questo piano, `security.md`, `backup_restore.en.md` (le doc della
>     rifinitura). Codice di prodotto intatto: la rifinitura non è applicata;
>   - **TA-B8-OWN fermato a metà**: gli ho chiesto di non scrivere più. Alle 18:15 `backupJob.test.ts` era ancora
>     pulito. Domani controllare `git status`: se ha scritto un gruppo parziale, completarlo o rifarlo, mai lanciarlo
>     a metà.
> - **Per ripartire, nell'ordine** (tutto nella cartella di sessione, niente in /tmp):
>   1. Rossi della rifinitura: brief di TA-B8-OWN qui sopra, oppure un test-author nuovo con lo stesso brief: due
>      rossi più due guardie, solo `backupJob.test.ts`, dopo i 5 gruppi «B-8, review 19/10».
>   2. Il rosso: `files/scripts/b_vitest.sh red-b8-own src/lib/features/backup/backupJob.test.ts`. Atteso: le due
>      righe nuove falliscono perché il job viene adottato (la fine cifrata non è offerta); il resto verde.
>   3. La cura: `python3 files/b15-b8-wip/apply_b8_own.py <worktree>` (1 operazione; `--check` era OK su
>      `bc913e487`).
>   4. I verdi: Vitest dell'intera feature `backup`, prettier sui 2 file, `front check` (prima `api sync` se il client
>      è più vecchio della base), le doc (`files/scripts/b_docs.sh`).
>   5. Il checkpoint: commit a parte (`fix(backup): a tab's own backup is never adopted`), più il giornale.
>   6. **Poi B-50**: il contratto è in `files/b50-contract.md`, le sonde in `files/b50-analysis/`. Decisione (17:37):
>      uno stato illeggibile è «non trovato» (404 `backup_job_not_found`; nel ripristino `restore_stage_not_found`),
>      JSON non oggetto compreso, nel backup e nel ripristino. Rossi prima.
> - **La corsia**: `/tmp/librefolio-r13-b` sparisce con /tmp. Prima di un test con server o DB, ricrearla con
>   `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6187 --data-dir
>   /tmp/librefolio-r13-b db populate --force --clean`. Per i Vitest e le doc non serve.
> - 🧊 **FROZEN** (18:16).
> - **▶️ Ripresa del 20/10** (coordinatore, 08:47): il riavvio ha svuotato /tmp; le corse leggere sulla corsia 6187
>   solo con il carico a 1 minuto sotto 50. Ordine: i rossi della rifinitura, la cura e il checkpoint, poi B-50. Il
>   gate di B-15 + B-8 su `dev_release2` lo lancia il coordinatore nella sua corsia.
>   - ✅ Verificato (08:47): HEAD `bc913e487`, gli stessi 3 file sporchi, porta libera, carico 27. I file di sessione
>     ci sono tutti; `apply_b8_own.py --check` OK. La corsia in /tmp non c'è più: per i Vitest e le doc non serve.
>   - Il test-author di ieri non esiste più: ne lancio uno nuovo con lo stesso brief.
> - ✅ **Rossi** (TA-B8-OWN-2, 08:50-09:00, sola scrittura; solo `backupJob.test.ts`):
>   - un gruppo nuovo dopo i cinque della revisione: 2 rossi (il proprio backup sicuro, avviato qui con il sondaggio
>     arreso, oppure ricordato da una pagina precedente con la lettura di `resume()` senza risposta; poi una
>     richiesta in chiaro rifiutata che lo nomina) e 2 guardie (un job che non è quello seguito, oppure quello seguito
>     come adozione, resta adottato e la sua fine cifrata non si presenta);
>   - nei rossi: nessuna scrittura né rimozione della chiave di adozione su tutto il percorso (risposta mia alla sua
>     domanda 1, come la regola delle guardie di pulizia), la fine cifrata offerta, `onDone` una volta, la chiave del
>     job tenuta. Non fissate, di proposito: la riscrittura della chiave del job con lo stesso id, e la guardia (b)
>     che riscrive l'adozione che ha già;
>   - aggiornata la frase superata nel commento del primo gruppo della revisione (rimanda al gruppo nuovo).
> - ✅ **Rosso** (09:01, carico 19): **2 falliti**, 244 passati, tutti e due perché il job seguito da sé viene adottato
>   al rifiuto. Le guardie sono verdi.
> - ✅ **Cura** (09:01): `apply_b8_own.py`, 1 operazione in `backupJob.svelte.ts` (+3/−1).
> - ✅ **Verdi** (09:01-09:04):
>   - Vitest dell'intera feature `backup`: 9 file, **1076 passati**;
>   - prettier pulito sui 2 file; `front check` 0 errori e 0 avvisi. Il client generato è delle 17:12 di ieri, dopo
>     l'ultimo merge, e da allora backend e schemi non sono cambiati: niente `api sync`;
>   - `mkdocs build` stretta, `check-links`, `utils gate-docs-links` 63.
> - ✅ **Backlog**: nella riga di B-8, la rifinitura.
> - ✅ **Checkpoint** (09:05), 🧊 FROZEN. Commit proposti:
>   - `fix(backup): a tab's own backup is never adopted`: `backupJob.svelte.ts`, `backupJob.test.ts`, le due doc;
>   - `docs(journal): B-8 own-job refinement`: questo piano e il backlog.
> - **Poi B-50**: il contratto è pronto (`files/b50-contract.md`), con una domanda sul perimetro (sotto).

### B-50 — uno stato illeggibile di un job o di un controllo è «non trovato», mai un 500 (2026-10-20, 09:06-09:57) — ✅ 🧊 FROZEN (checkpoint delle 09:57)

> **Coordinatore** (09:06): rifinitura committata, `43face16e` (`fix(backup): a tab's own backup is never adopted`) e
> `9a7d4a2ea` (il giornale), albero pulito, in dev con il prossimo treno. «Il perimetro di B-50: approvo la tua
> proposta»: anche lo `state.json` che è una cartella e quello senza permessi di lettura sono «illeggibili», quindi
> 404; gli altri `OSError`, transitori, restano un 500 che la scheda riprova. Via: prima i rossi, poi la cura, poi il
> checkpoint; corse leggere solo con il carico a 1 minuto sotto 50.
>
> - **Da sapere** (coordinatore, 09:06):
>   - E-20 di E riscrive la barriera di RNW-109 in `test_restore_non_iso_warning.py` (righe 847-849), il mio test di
>     B-49: l'audit con il factory permissivo non alza più, e la stessa prova la fa un lettore sqlite3 semplice; le
>     mie asserzioni restano identiche. Non aprire quel file finché E non ha finito (B-50 non lo tocca);
>   - una domanda di E, per **dopo** B-50: il ripristino a mano (`#by-hand`) non passa dal controllo dell'archivio;
>     serve un controllo di tutto il DB vivo? Rispondere con una proposta quando ci arrivo.
> - ✅ **Base** (09:07): HEAD `9a7d4a2ea`, albero pulito, carico 18.
> - ✅ **Contratto** (`files/b50-contract.md`, aggiornato 09:08):
>   - backup: `from_json` alza `ValueError` per un documento che non è un oggetto; nuova
>     `BackupJobUnreadableError`, sottoclasse di `BackupJobNotFoundError`, per uno stato illeggibile (`ValueError`,
>     `TypeError`, `KeyError`, `IsADirectoryError`, `PermissionError`); gli altri `OSError` passano come oggi;
>   - `get_job` registra un avviso, «A backup job's state cannot be read», con l'id e la classe dell'errore e mai il
>     contenuto, poi rilancia: resta il 404 `backup_job_not_found`. I cicli di pulizia restano silenziosi, come oggi;
>   - ripristino: `_read_state` dà `None` per un documento che non è un oggetto (gli altri casi illeggibili già lo
>     sono, senza log).
> - **Rossi** a due test-author in parallelo, su file diversi, sola scrittura: TA-B50-JOBS (`test_backup_jobs.py`,
>   `test_backup_cli.py`) e TA-B50-RESTORE (`test_backup_leftovers.py`).
> - **⚠️ Fuori pista — le date senza fuso orario** (09:10, sonda `files/b50-analysis/b50_probe_naive.py`): uno stato
>   `done` con `finished_at` senza fuso orario fa alzare `TypeError` a `get_job`, a `remove_expired_jobs` (la
>   sottrazione è fuori dal suo `try`) e a ogni partenza: è la stessa classe di B-50, e blocca ogni backup. Aggiunto
>   al contratto (`from_json` rifiuta una data senza fuso orario come illeggibile) e ai rossi di TA-B50-JOBS. Un
>   `created_at` senza fuso orario da solo non blocca nulla nella sonda.
> - **Cura pronta, non applicata**: `files/b50-wip/apply_b50.py`, 6 operazioni in `jobs.py` e `restore_jobs.py`
>   (`--check` OK su `9a7d4a2ea`).
> - ✅ **Doc** (09:11): `security.md`, dopo «A read of a job…», un paragrafo: uno stato illeggibile non è un job, per
>   la lettura e per la pulizia; il 404, l'avviso con l'id e la classe, mai il contenuto; gli altri errori del disco
>   restano un 500 che la scheda riprova; un controllo del ripristino illeggibile è `restore_stage_not_found`.
> - ✅ **Rossi del ripristino** (TA-B50-RESTORE, 09:08-09:30, solo `test_backup_leftovers.py`): la sezione (h), 6 test
>   e 65 casi, 34 rossi e 31 guardie (le righe `mode-000` saltano da root). I rossi: `_checks`/`prune`, `read_check`,
>   `remove_check` e `confirm_check` (`CheckNotFoundError`, niente log), la fine di un caricamento, l'avvio di un
>   controllo, la pulizia all'avvio per i controlli e per i job (nessun errore con `part`). Le sue domande:
>   - (1) uno stato di controllo illeggibile e vecchio non lo toglie nessuno (già vero oggi per un file vuoto o `{}`);
>   - (2) nel ripristino ogni `OSError` è «nessuno stato», anche quelli transitori;
>
>   sono tutte e due fuori dal perimetro deciso, quindi le porto al coordinatore. (3) Il log solo in `get_job`:
>   deciso.
> - **⚠️ Fuori pista — un descrittore perso a ogni lettura** (domanda 4, misurata alle 09:33 con
>   `files/b50-analysis/b50_probe_fd.py`): 50 letture di uno stato di controllo che è una cartella lasciano aperti 50
>   descrittori in più (da 5 a 55), perché `os.fdopen` non chiude quello che rifiuta. Nel server ogni pulizia, fine di
>   caricamento o avvio di un controllo ne perderebbe uno, fino a «too many open files». È dentro il perimetro di B-50
>   (una cartella al posto dello stato): la cura lo chiude (patch aggiornata, `--check` OK), e TA-B50-RESTORE scrive
>   il rosso. Lo stesso schema c'è in `outcome.py`, `staging.py` e `apply.py`, fuori dai 2 file: è un residuo, con una
>   proposta (un aiuto unico che apre un file privato e chiude il descrittore se è rifiutato).
> - ✅ **Il rosso del descrittore** (TA-B50-RESTORE, 09:36-09:41):
>   `test_reading_a_check_state_that_is_a_folder_leaves_no_descriptor_open`, `[_checks]` e `[read_check]`, nella
>   sezione (h): 20 letture di uno stato che è una cartella, poi nessun descrittore del processo aperto su quella
>   cartella. Li cerca per dispositivo e inode (`descriptors_on` di `test_backup_archive.py`, che fissa lo stesso
>   difetto per `_add_file`), dietro una barriera (un descrittore aperto dal test si vede, e sparisce chiuso) e li
>   chiude nel `finally`, così un rosso non ne lascia ai test dopo.
> - ✅ **Rossi dei job e della CLI** (TA-B50-JOBS, 09:08-09:43, `test_backup_jobs.py` e `test_backup_cli.py`): 13 forme
>   (le quattro `json-*`, file vuoto, non JSON, `{}`, `created_at` numero o non data, non UTF-8, cartella, modo 000
>   che salta da root, e `finished-at-without-time-zone`). Rossi: «non trovato» e lasciato com'è, l'avviso con id e
>   classe (mai `exc_info`), le tre rotte (404 `backup_job_not_found`, scheda e pannello), l'avvio oltre uno stato
>   illeggibile, `remove_expired_jobs` ed `end_interrupted_jobs` che vanno avanti, un lucchetto che nomina un job
>   illeggibile (409 senza job). Guardie: stato assente (nessun avviso), un `EIO` che passa com'è (nessun «non
>   trovato», nessun avviso). CLI: `create` oltre uno stato cartella o non oggetto. Le sue 5 domande avevano risposta
>   nel contratto; aggiunta la forma del fuso anche fra le righe dell'avviso (`ValueError`).
> - ✅ **Rossi della CLI lanciati** (09:45, `utils backup-cli`, carico 22): **2 rossi, 102 verdi**, per i motivi
>   attesi: `state-is-a-folder` esce con 1 («Is a directory»), `state-not-an-object` con 1 e la traccia di
>   `AttributeError`. Log: `files/logs/b50_red_utils_backup-cli.log`.
> - ✅ **Rossi dei job e del ripristino lanciati** (09:47, carico 22): `services backup-jobs` **56 rossi**, 93 verdi;
>   `services backup-leftovers` **36 rossi**, 75 verdi. I conti tornano con quelli dei test-author (13 + 13 + 6 + 8 +
>   7 + 6 + 3; 34 più i 2 del descrittore), nessun errore di raccolta né di preparazione, e ogni rosso ha il motivo
>   atteso: l'`AttributeError` delle quattro forme non oggetto, `KeyError`, `JSONDecodeError`, `UnicodeDecodeError`,
>   `IsADirectoryError`, `PermissionError`, la sottrazione fra una data con fuso e una senza, i 20 descrittori aperti,
>   la pulizia d'avvio che registra un errore. Log: `files/logs/b50_red_services_backup-{jobs,leftovers}.log`.
> - ✅ **Cura** (09:48): `apply_b50.py`, 6 operazioni in 2 file (`jobs.py` +40/−10, `restore_jobs.py` +11/−1).
> - ✅ **Verdi** (09:48-09:53, carico 22-38):
>   - i tre rossi: `services backup-jobs` **149**, `services backup-leftovers` **111**, `utils backup-cli` **104**;
>   - regressione, tutte pure: `services backup-secure` 77, `backup-staging` 202, `backup-apply` 255,
>     `backup-archive` 155 (1 saltato, di prima: un nome non UTF-8, che APFS rifiuta), `backup-secure-rules` 24;
>     `utils backup-cli-secure` 106, `backup-cli-restore` 109;
>   - `ruff check` e `black --check` puliti sui 5 file Python; `lint --dead-code --scope backend`: nessun rilievo
>     nei file toccati (l'uscita 1 viene da rilievi di prima, altrove);
>   - `mkdocs build` stretta, `check-links`, `utils gate-docs-links` 63; `git diff --check` pulito.
>   - **Non lanciate**: le suite `api` ed `e2e` del backup, che avviano il server della corsia (nessuno slot
>     chiesto). Le rotte sono coperte dai test dei servizi attraverso le viste (`job_views`): 404
>     `backup_job_not_found`, per la scheda e per il pannello.
> - ✅ **Residui** (sonda e lettura, 09:54-09:57), nel backlog:
>   - **B-53**: lo stesso descrittore perso in `outcome._read_record` e in `staging.read_report`, misurato
>     (`files/b50-analysis/b53_probe_fd.py`: 20 letture di una cartella, 20 descrittori aperti, per ciascuno). Il
>     secondo alza anche `IsADirectoryError`, che `_stage_view` non prende: a lettura, un 500 sulla lettura del
>     controllo. `apply.py:329` è al riparo: controlla `S_ISREG` con `lstat` prima di aprire;
>   - **B-54** (domanda 1 di TA-B50-RESTORE): uno stato di controllo illeggibile non lo toglie nessuno
>     (`_prune_unrecorded` pulisce caricamenti e copie, mai `checks/`);
>   - **B-55** (domanda 2), da decidere: nel ripristino un `OSError` transitorio è «nessun controllo», e la scheda
>     dimentica il controllo che segue (`restoreFlow.svelte.ts:593-597`) invece di riprovare come per un 500.
> - ✅ **Backlog**: B-50 chiusa; B-53, B-54 e B-55 nuove. Solo la sezione B: dev (`701054da9`) ha cambiato il backlog
>   dopo la mia base, ma nessuna sua modifica cade nella sezione B.
> - ✅ **Checkpoint** (09:57), 🧊 FROZEN. Commit proposti:
>   - `fix(backup): unreadable job state is not found (B-50)`: `jobs.py`, `restore_jobs.py`, i 3 file di test,
>     `security.md`;
>   - `docs(journal): B-50 unreadable states`: questo piano e il backlog.
> - **Poi**: la proposta per la domanda di E sul ripristino a mano (`#by-hand`).

### La domanda di E sul ripristino a mano (`#by-hand`) — proposta (2026-10-20, 09:58-10:05) — ✅ approvata

> **Domanda** (coordinatore, 09:06, per conto di E): «il ripristino a mano (`#by-hand`) non passa dal controllo
> dell'archivio. Serve un controllo di tutto il DB vivo?»
>
> - **Proposta** (inviata alle 10:05): nessun controllo automatico del DB vivo, né a ogni avvio né al primo. Il
>   confine di fiducia è il ripristino (dalla UI o dalla CLI arriva un archivio di origine qualunque, e lì B-49
>   rifiuta il testo non UTF-8); lo scompattamento a mano richiede già di scrivere nella cartella dati. LibreFolio non
>   crea testo non UTF-8. Una scansione di ogni TEXT a ogni avvio costa tutto il DB, e al ritrovamento non c'è una
>   buona reazione. Invece: (a) una frase nella doc di `#by-hand`, che indica `backup inspect` e `backup restore
>   --dry-run` per controllare un archivio prima; (b) dopo la 1.3, un comando a richiesta, in sola lettura, sul DB
>   vivo. Scartato: un controllo al primo avvio dopo uno scompattamento (riconosciuto dal `manifest.json` rimasto).
> - **Coordinatore** (10:10): «approvo (a) e (b). (a): solo inglese; poi `./dev.py mkdocs translate-stamp --file
>   <pagina>.en.md`, perché è una modifica puntuale. (b): la riga nel backlog, «dopo la 1.3».» Le faccio nel lotto qui
>   sotto. Fonti della proposta: `files/b50-wip/e-by-hand-proposal.md`.

### B-53 + B-54 + B-55 — un lettore unico per gli stati e i report del ripristino; la regola di B-50 nel ripristino (2026-10-20, 10:10-11:13) — ✅ 🧊 FROZEN (checkpoint delle 11:13)

> **Coordinatore** (10:10): «Ho fatto il checkpoint: `b9c14953f` (B-50) e `13570ad2a` (il giornale), albero pulito.
> Le suite `api` del backup le metto nel mio gate d'ingresso. I residui: B-53: sì, l'aiuto unico per aprire in
> lettura; chiude il descrittore perso e il 500 di `read_report`. B-54: sì. B-55: sì, la stessa regola dei job. Il
> ripristino tratta come «nessun controllo» solo `IsADirectoryError`, `PermissionError` e il contenuto illeggibile;
> gli altri `OSError`, quelli transitori, restano un errore che la scheda riprova. Fai i tre in un lotto solo: prima i
> rossi, poi la cura, poi il checkpoint.»
>
> - **Base**: HEAD `13570ad2a`, albero pulito.
> - ✅ **Sonde** (10:12-10:18, `files/b55-analysis/`):
>   - uno stato di controllo con le date senza fuso: `_checks` lo legge, `read_check` lo restituisce, `prune` alza
>     `TypeError` (lo stesso difetto curato da B-50 per i job): ogni nuovo controllo è un 500 `stage_failed`;
>   - un link al posto dello stato: già «nessun controllo»; una FIFO: `_read_state` resta bloccato (sbloccato a mano
>     dopo 3 s). La pulizia d'avvio è il passo `backup-leftovers` (`app_lifespan.py:249`), senza timeout: una FIFO lì
>     ferma ogni avvio;
>   - un `EIO` sulla lettura di uno stato valido: «nessun controllo» (è ciò che B-55 cambia);
>   - **anche i job**: una FIFO al posto di `state.json` blocca `get_job` e `remove_expired_jobs`, quindi l'avvio di
>     ogni backup e la pulizia d'avvio.
> - ✅ **Come applico la regola** (al coordinatore alle 10:19, «procedo così, salvo tuo no»): un link o un file
>   speciale al posto dello stato di un controllo è illeggibile; una data senza fuso è contenuto illeggibile;
>   `read_report` segue la stessa regola; la conferma lascia passare un errore transitorio (500
>   `restore_confirm_failed`, che si riprova, invece di «copia mancante», che fa dimenticare il controllo); B-54
>   toglie anche gli stati scritti a metà (`<id>.json.part`); l'esito del ripristino cambia solo il lettore.
> - ✅ **Domanda sui job** (10:19), **risposta del coordinatore** (10:39): «Il punto 7: sì, nello stesso lotto. Una
>   FIFO che blocca l'avvio è troppo grave per lasciarla fuori. Anche il lettore dei job passa dall'aiuto unico: FIFO
>   e link valgono come illeggibili, cioè 404 con un avviso. La guardia di B-50 la riscrivi attraverso `os.open`. Sui
>   punti 1-6 procedi come hai descritto.» Fatto: la cura ha 3 operazioni in più in `jobs.py` (16 in 6 file, `--check`
>   OK, una copia compila, `ruff` e `black` puliti); i rossi dei job a TA-B50-JOBS (`test_backup_jobs.py`,
>   `test_backup_cli.py`, con la guardia dell'`EIO` riscritta) e la pulizia d'avvio con una FIFO fra i job a
>   TA-B50-RESTORE (i-5); la doc di sicurezza in tre paragrafi (job, controlli, lettore unico).
> - ✅ **Contratto** (10:22): `files/b53-contract.md`. L'aiuto `read_regular_file(path, *, limit=None)` e
>   `NotRegularFileError` in `paths.py` (solo libreria standard): apre senza seguire un link e senza aspettare una
>   FIFO, chiude sempre il descrittore; una cartella è `IsADirectoryError`, un link o un file speciale
>   `NotRegularFileError`, gli altri errori come il sistema li alza. Lo usano `restore_jobs._read_state`,
>   `staging.read_report`, `apply._read_state` e `outcome._read_record`.
> - ⏳ **Rossi chiesti** (10:24): a TA-B50-RESTORE, la sezione (i) di `test_backup_leftovers.py` (B-55, le forme nuove,
>   B-54, la pulizia d'avvio con una FIFO); a TA-B53-READER (nuovo), l'aiuto in `test_backup_archive.py`,
>   `read_report` e la vista in `test_backup_staging.py`, l'esito in `test_backup_outcome.py`, la conferma in
>   `test_backup_apply.py`. Tutti e due solo in scrittura; le nuove funzioni prese dentro ogni test, così un rosso non
>   rompe la raccolta.
> - ✅ **(a) La frase di `#by-hand`** (10:28, `admin/backup_restore.en.md`, riga 🔎): un danno si vede all'avvio, o più
>   tardi quando una pagina legge quei dati; per controllare un archivio prima di scompattarlo, su un'installazione
>   che già gira, `backup inspect` («Check an Archive», senza ancora esplicita) e `backup restore --dry-run` (ancora
>   `#backup-restore-dry-run`), mai sulla cartella vuota che si sta per riempire.
>   - **⚠️ Fuori pista — lo stamp non l'ho fatto.** La pagina non ha traduzioni: esiste solo `backup_restore.en.md`, e
>     il cache di Aphra (`mkdocs_src/aphra-pipeline/.translate-hashes.json`, tracciato) non ha una sua voce
>     (`--dry-run`: «MD5 <none>→f97354d7; new langs: es, fr, it»). Lo stamp segnerebbe IT, FR ed ES come già tradotte,
>     e il pipeline non le creerebbe mai. Lo dico al coordinatore.
> - ✅ **(b) B-56 nel backlog** (10:30): «Un controllo a richiesta del DB vivo», dopo la 1.3.
> - ✅ **Cura pronta** (10:34): `files/b53-wip/apply_b53.py`, 13 operazioni in 5 file (`paths.py`, `restore_jobs.py`,
>   `staging.py`, `apply.py`, `outcome.py`); `--check` OK su `13570ad2a`; applicata a una copia nella cartella di
>   sessione, compila, `ruff` e `black` puliti con la configurazione del repo. Il pezzo dei job (`--jobs`) aspetta la
>   risposta.
> - ✅ **Doc di sicurezza** (10:38, `security.md`): il paragrafo di B-50 diviso in due; il secondo dice la regola del
>   ripristino (B-55), la pulizia degli stati vecchi (B-54), il lettore unico e i due difetti che chiude (B-53), il
>   report illeggibile che non è più un 500.
> - ✅ **Rossi del ripristino scritti** (TA-B50-RESTORE, 10:24-10:52), sezione (i) di `test_backup_leftovers.py`: 10
>   test, 66 casi, 34 rossi e 32 guardie (i 3 `mode-000` saltano da root). (i-1) un `EIO` non è «nessun controllo»
>   (`read_check`, `_checks`, `prune`, l'avvio di un controllo, la fine di un caricamento, la pulizia d'avvio); (i-2)
>   un link (guardia), una FIFO e le date senza fuso (rossi) sono «nessun controllo», in silenzio; (i-3) `prune`
>   toglie gli stati illeggibili vecchi (14 forme, `.part` compreso) e lascia quelli di un controllo che gira, di una
>   copia protetta e i nomi che non sono suoi; (i-4) e (i-5) la pulizia d'avvio torna in tempo con una FIFO fra i
>   controlli e fra i job. Ogni lettore che può incontrare una FIFO gira in un thread con 10 s di scadenza, poi la
>   FIFO si apre in scrittura per liberarlo: un rosso costa circa 10 s per caso, mai un blocco.
>   - Le sue domande, nessuna cambia i test: (1) un caricamento la cui pulizia finale incontra un errore transitorio
>     lascia il file nuovo finché il caricamento seguente lo toglie come sostituito, o `prune` dopo 24 ore (lo dico al
>     coordinatore nel checkpoint); (2) un `<id>.json.part` accanto a un `<id>.json` leggibile resta finché la
>     scrittura seguente dello stato lo riusa, o fino alla `prune` dopo la rimozione del controllo: voluto; (3) «in
>     silenzio» vuol dire nessun log di nessun livello: la cura non ne scrive.
> - ✅ **Rossi del lettore scritti** (TA-B53-READER, 10:24-10:51): 20 test, 37 casi, in quattro file. (A) l'aiuto in
>   `test_backup_archive.py` (file intero e `limit`, niente lì e un file sulla strada, cartella, link, FIFO,
>   `/dev/null`, modo 000, la classe nuova, un `EIO` dell'apertura e di `fstat`); (B) `read_report` e la vista in
>   `test_backup_staging.py`; (C) la cartella e la FIFO al posto del biglietto in `test_backup_outcome.py`; (D) la
>   conferma con un `EIO` sul report, il report cartella e il report di modo 000 in `test_backup_apply.py`. Le nuove
>   funzioni si cercano dentro ogni test. Nessun test esistente fissa il testo dell'errore di un link nell'esito.
>   - Le sue domande: (1) la descrizione nel catalogo del runner resta com'è (file condiviso); (2) per una FIFO basta
>     la classe, non l'errno; (3) una riga della vista basta, le altre forme le prova `read_report`; (4) 30 s di
>     scadenza vanno bene, chiudono solo un rosso; (5) `/dev/null` si legge e basta: resta.
> - ✅ **Rossi del lettore lanciati** (10:52-10:54, carico 20-30), `ruff` e `black` prima, puliti: `services
>   backup-archive` **19 rossi**, 155 verdi (1 saltato, di prima); `backup-staging` **7 rossi**, 206 verdi;
>   `backup-outcome` **2 rossi**, 164 verdi; `backup-apply` **2 rossi**, 256 verdi. Ogni rosso per il motivo atteso:
>   l'aiuto che non c'è; la cartella, il link (`ELOOP`), il modo 000, la copia diventata un file, la FIFO che aspetta
>   ancora dopo 30 s, i 20 descrittori aperti, la vista che alza `IsADirectoryError` (un 500); l'esito con 20
>   descrittori aperti e la FIFO che aspetta; la conferma che prende l'`EIO` per «copia mancante» e lascia 20
>   descrittori. Log: `files/logs/b53_red_services_backup-{archive,staging,outcome,apply}.log`.
> - ✅ **Rossi dei job scritti** (TA-B50-JOBS, 10:41-10:58): in `test_backup_jobs.py` la sezione (B-53), 8 test (una
>   FIFO al posto di `state.json`: `get_job`, le viste, l'avvio, `remove_expired_jobs`, `end_interrupted_jobs`, il
>   lucchetto; un link, valido o rotto) con 10 s di scadenza e la FIFO liberata nel `finally`; la guardia dell'`EIO`
>   di B-50 riscritta: blocca `os.open` (il lettore nuovo) e anche `io.open` (quello di oggi, `Path.read_text`), così
>   resta verde prima e dopo. In `test_backup_cli.py` le righe `state-is-a-fifo` e `state-is-a-link` (un link a un job
>   finito due ore fa, che oggi si segue e si toglie). Le sue domande non cambiano nulla: dopo la cura il test del
>   lucchetto passa anche da `_running_job`.
> - ✅ **Rossi lanciati** (10:59-11:04, carico 20-24; `ruff` e `black` puliti prima): `services backup-jobs` **9
>   rossi**, 149 verdi (la guardia dell'`EIO` verde); `utils backup-cli` **2 rossi**, 104 verdi (la FIFO: il figlio
>   ucciso dal timeout di 120 s; il link: seguito, e la cartella tolta); `services backup-leftovers` **34 rossi**, 143
>   verdi (le FIFO che aspettano 10 s, le date senza fuso, gli stati vecchi lasciati, l'`EIO` preso per «nessun
>   controllo»). Tutti per il motivo atteso. In tutto il lotto: **75 rossi**. Log: `files/logs/b53_red_*.log`.
> - ✅ **Cura** (11:04): `apply_b53.py`, 16 operazioni in 6 file: `paths.py` +35 (l'aiuto e la classe),
>   `restore_jobs.py` +19/−12, `staging.py` +9/−4, `apply.py` +5/−3, `outcome.py` +4/−5, `jobs.py` +9/−7.
> - ✅ **Verdi** (11:04-11:08, carico 16-23):
>   - i sette rossi: `services backup-archive` **174** (1 saltato, di prima), `backup-staging` **213**,
>     `backup-outcome` **166**, `backup-apply` **258**, `backup-jobs` **158**, `backup-leftovers` **177**;
>     `utils backup-cli` **106**;
>   - regressione: `services backup-secure` 77, `backup-secure-rules` 24, `backup-checks` 93,
>     `restore-non-iso-warning` 46 (solo eseguito, mai aperto: E-20); `utils backup-cli-secure` 106,
>     `backup-cli-restore` 109;
>   - `ruff check` e `black --check` puliti sui 13 file Python; `lint --dead-code --scope backend`: gli stessi
>     rilievi di B-50, nessuno nuovo;
>   - `mkdocs build` stretta, `check-links`, `utils gate-docs-links` 63; `git diff --check` pulito.
>   - **Non lanciate**: le suite `api` ed `e2e` del backup (server della corsia), per il gate d'ingresso del
>     coordinatore.
> - **⚠️ Fuori pista — l'ancora nella doc** (11:09): la build stretta è fallita sulla frase nuova di `#by-hand`. La
>   pagina non ha traduzioni, quindi il sito italiano usa quella inglese, e il link
>   `cli_tools.md#backup-restore-dry-run` va a `cli_tools.it.md`, che quell'ancora non ce l'ha. Ora la frase nomina le
>   due sezioni («Check an Archive» e «Try a Restore on a Copy» in [CLI Admin Tools](cli_tools.md)), come fa già il
>   resto della pagina. Build di nuovo verde alle 11:11.
> - ✅ **Backlog**: B-53, B-54 e B-55 chiuse; B-56 nuova. Solo la sezione B.
> - ✅ **Conflitti con dev** (`f73514a77`): `staging.py` (dev cambia una docstring verso la riga 800, io gli import e
>   `read_report`), `security.md` (dev da riga 1510 in poi, io alla 1077) e il backlog (nessuna modifica di dev nella
>   sezione B): nessuna sovrapposizione.
> - ✅ **Checkpoint** (11:13), 🧊 FROZEN. Commit proposti:
>   - `fix(backup): one reader for job, check and report files (B-53, B-54, B-55)`: i 6 file di servizio, i 7 di test,
>     `security.md`, `backup_restore.en.md`;
>   - `docs(journal): B-53 to B-56`: questo piano e il backlog.
