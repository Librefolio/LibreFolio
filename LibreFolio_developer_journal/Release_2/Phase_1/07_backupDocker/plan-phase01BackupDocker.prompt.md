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

### Accordo con J — totali di controllo (2026-10-15, 14:20) — in attesa della firma

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

### B5a — scheda Backup, solo scaricamento (2026-10-15, dalle 14:25) — componente ✅, riga del registro dopo A5

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

### B8 — il token del pannello (via del coordinatore, 2026-10-15 alle 17:15) — in corso

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
