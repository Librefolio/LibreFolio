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
- **Archivio con password**: l'intero zip dentro una busta cifrata `.lfbackup` (§3.5).

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
2. **Riconoscimento**: zip (`PK\x03\x04`) o busta `.lfbackup`. Senza manifest: archivio «a mano», se contiene
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
   - **(a) busta `.lfbackup` con `cryptography`**: nessuna dipendenza nuova, scrypt; si apre con LibreFolio (UI, o CLI
     anche nell'immagine);
   - (b) zip AES con `pyzipper`: dipendenza nuova, più `pycryptodomex`; si apre con 7-Zip o Keka, ma non con Esplora
     risorse né con il Finder, e la derivazione è debole (PBKDF2-SHA1 ×1000);
   - (c) nessuna cifratura, solo un avviso forte.
2. **D-B2, la chiave d'istanza** (§3.5): **solo con password e solo se generata; al ripristino la chiave dell'istanza
   resta e i segreti si ricifrano**. Alternativa: adottare la chiave del backup (più semplice, ma due istanze con la
   stessa chiave, e impossibile quando la chiave è configurata).
3. **D-B3, le sessioni**: **tutte chiuse dopo un ripristino** (§3.6).
4. **D-B4, il backup automatico**: **uno zip in `backups/` (l'ultimo), più il ritorno indietro automatico se il primo
   avvio fallisce**. Alternativa: tenere `previous/` come backup (nessuno spazio in più, ma una cartella invece di un
   file scaricabile).
5. **D-B5, archivi senza manifest** (copie a mano, quindi le 1.2): **accettati**, con un avviso.
6. **D-B6, il limite di caricamento**: **una variabile d'ambiente**, perché nel cloud il cliente è admin e il limite lo
   decide l'hoster; `0` = senza limite nel self-hosted. Non un'impostazione globale.
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

| Lotto | Contenuto | Dipende da |
|---|---|---|
| **B0** | divisione C2 di `backup.py` (rinomina, poi taglio; `api schema` identico, rotte identiche); facoltativa la rinomina di `backup_service.py` | via del coordinatore; E1 di W |
| **B1** | backup dell'istanza, backend e CLI, zip senza cifratura: `config/backup.py`, `paths`, `manifest`, `snapshot`, `archive`, `jobs`, endpoint dei job, `dev.py backup create|inspect`, `.env.example` | B0 per gli endpoint (servizio e CLI no) |
| **B2** | caricamento e prova su copia: estrazione con i controlli, decisione sulla revisione, migrazione della copia, controlli, report, archivi a mano, `restore --dry-run` | base con CP5a |
| **B3** | ripristino definitivo: conferma, backup automatico, `apply.py` (lock, giornale, scambio, ritorno indietro), `restart.py`, stato e annullamento, sessioni, `restore` a server spento; `security-review` di metà percorso | CP2b di H, o le due righe |
| **B4** | password e chiave: `envelope.py`, regola della chiave, `decrypt`, contratto H-3; la ricifratura quando c'è il CP10 di X (altrimenti B4b) | `cryptography` |
| **B5** | scheda Backup: feature, riga nel registro, i18n, Vitest, E2E, galleria, `api sync` | B1-B3 (B4 per il campo della password); `npm ci`; via per la riga di A |
| **B6** | guida e doc | con B5, o subito dopo |
| **B7** | Litestream: immagine, avviatore, variabili, compose, doc, prove Docker, spike della replica | CP7a di H; daemon Docker acceso |
| **B8** | token del pannello | B1; può entrare in B3 |
| **B9** | M-1, arm64 | facoltativo |
| **BZ** | revisione di sicurezza finale e handoff | tutto |

Percorso minimo per il cloud: B1 → B2 → B3 → B5 (più B4 se approvata) → B7.

## 8. Come si prova

**Principi**

- Il runner possiede il backend della corsia: nessun test conferma un riavvio sulla corsia, e nessuno lascia
  `pending.json` nella sua cartella dati (fixture con la pulizia nel `finally`).
- Scambio all'avvio, giornale e ritorno indietro: funzioni chiamate su cartelle temporanee, con un'interruzione
  simulata a ogni passo.
- Uscita per il riavvio: `restart.py` con segnale e bersaglio iniettati (test unitari), mai un vero `kill` sulla
  corsia. La prova vera è quella Docker.
- **«Stessi totali»** (D-B9): backup della corsia popolata via API → ripristino in una cartella temporanea vuota, con
  le funzioni d'avvio in un sottoprocesso (`apply_pending_restore`, `ensure_database_exists`, fix post-migrazione) →
  totali del motore ufficiale nel sottoprocesso, confrontati con l'API della corsia (`POST /portfolio/report`, con una
  data fissa).
- **Backup della 1.2**: fixture costruita nel test con le migrazioni vere fino a `004_release_1_2_0_schema` e le righe
  del costruttore di `test_post_migration` e `test_migration_005_accounts` (lì è già «la vera 1.2»), zippata con e
  senza manifest → prova → conferma → righe e totali uguali. Più il rifiuto di una revisione sconosciuta o più nuova.
- **Cancello del §9 sulla 1.2 vera**: una cartella dati popolata da `git archive v1.2.0` (sola lettura, nessun
  worktree) con `db populate` in una cartella `/tmp`, zippata a mano e ripristinata nella corsia. Procedura in `/tmp`,
  eseguita da me col via o dal developer.
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
  stessi totali; backup della 1.2 ripristinato sulla 1.3 con prova e conferma; rifiuto di un backup più nuovo.
- **Cancelli del §9**: ripristino di un backup della 1.2 vera con la prova su copia; immagine con Litestream spento e
  acceso; `docker stop` entro il limite; revisione di sicurezza del backup.
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

### B0 — divisione di `api/v1/backup.py` (C2) e rinomina di `backup_service.py` (D-B8) — in corso

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

### Checkpoint B0 🧊 (2026-10-15) — FROZEN, in attesa del coordinatore

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

### B1 passo 2 — i file condivisi e la seconda tornata di test (2026-10-15, dalle 13:38) — in corso

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

### Checkpoint B1 🧊 (2026-10-15) — FROZEN, in attesa del coordinatore

> Handoff inviato con l'elenco dei file, le prove e il testo proposto per il CHANGELOG.

### B1 — backup dell'istanza, backend e CLI — bozza (2026-10-15, in attesa del commit di B0)

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
