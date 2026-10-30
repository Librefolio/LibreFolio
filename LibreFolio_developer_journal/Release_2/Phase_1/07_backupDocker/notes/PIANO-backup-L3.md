# Backup del cloud — piano del lavoro di prodotto (L3, ripristino del pannello, modo «ripristino in corso»)

Bozza del pianificatore per il coordinatore, 22/10/2026. Fonte di verità: `LibreFolio_developer_journal/Release_2/Phase_1/07_backupDocker/notes/BACKUP-decisioni-20261022.md`
(Opzione 1 nella 1.3). Schema e attacchi: `BACKUP-schema-20261021.md`. Codice letto su `dev_release2` = `e2d3b8a51`, in sola lettura.

**Tutto ciò che qui è scritto come «proposta» è una proposta**: lo decide il developer con l'ok alla specifica (passo B1).

## 1. Cosa c'è già nel codice (verificato)

| Pezzo | Dove | Stato |
|---|---|---|
| Busta `.lfbk` con password: scrypt (`2^15`, r 8, p 1) → AES-256-GCM a blocchi da 1 MiB (STREAM), intestazione di 52 byte come dato autenticato di ogni blocco, file scritti via `.part` | `backend/app/services/platform/instance_backup/envelope.py` | ✅ (lotto B4) |
| Regole della password (12+ caratteri) e chiave d'istanza nella busta solo se generata da LibreFolio (decisione 39) | `instance_backup/secure.py` | ✅ |
| Rotte del pannello per il backup (`POST/GET/DELETE /api/v1/backup/panel/jobs…`), token L1 o biglietto L2 di scopo `backup`, **mai la chiave d'istanza** | `backend/app/api/v1/backup/panel.py`, `hosting_panel/access.py` | ✅ (H-61 CP2) |
| Biglietti L2: JWT `EdDSA`, `typ lf-panel+jwt`, `kid`, `aud`, `scope`, `iat/exp ≤ 300 s`, `jti` usato una volta; chiavi in `LIBREFOLIO_PANEL_PUBLIC_KEYS=kid:chiave,…` (base64url 43 caratteri); registro `DATA_DIR/panel_tickets.sqlite3` fuori dai backup | `hosting_panel/tickets.py`, `ticket_registry.py`, `config/hosting_panel.py` | ✅ |
| Scopi del pannello: `backup`, `wake`, `status` (`PanelScope`) | `hosting_panel/access.py:298-303` | ✅; `backup:restore` **non c'è** |
| `GET /api/v1/panel/status` → `{admin_setup, setup_expires_at}`, `extra="forbid"` | `api/v1/panel.py`, `schemas/hosting_panel.py` | ✅ |
| Ripristino dell'admin: `PUT /backup/restore/upload` (corpo grezzo, limite `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`), `POST /backup/restore/stage` (prova su copia, `password` per una busta), `confirm`, `restart` (SIGTERM, biglietto monouso per `GET /backup/restore/outcome`), `status`, `DELETE pending` | `api/v1/backup/restore.py`, `instance_backup/restore_jobs.py`, `staging.py`, `apply.py` | ✅; **solo con sessione di un admin** |
| Rapporto di stage: `administrators` (gli admin attivi della copia), `control_totals`, `warnings`, `blockers` (`no_administrator`), `encrypted`, `secrets_rekeyed` | `staging.py:162-210`, `:794-880` | ✅; mancano i due avvisi nuovi del §7 delle decisioni |
| Applicazione al riavvio: passo `pending-restore` prima di tutto, `restore-commit` dopo `admin-bootstrap`; un'istanza bloccata (`LIBREFOLIO_BLOCKED`) **non applica** (`waiting: instance_blocked`) | `apply.py:628-722`, `app_lifespan.py:220-260` | ✅ |
| Il lavoro di backup calcola `file_sha256`, ma la vista API lo toglie («no hash») | `instance_backup/jobs.py:115`, `api/v1/backup/job_views.py:46-61` | ⏳ da esporre |
| Round trip vero fra due processi: backup → ripristino con la CLI → avvio in un processo nuovo → stesse righe e stessi report | `scripts/test_runner/_backend_api.py` azione `backup-roundtrip` | ✅ (F01): base per il test L3 |
| Doc: «Backups for Your Hosting Panel», «Keep Copies Off the Server» (cron + `--output`), «Secure Backups» | `mkdocs_src/docs/admin/hosting_providers.en.md:865-975`, `backup_restore.en.md:117-160` | ✅; mancano busta L3, rotta di ripristino, modo, backrest/restic |
| CSP `script-src` applicata (citata nel §7 delle decisioni) | H-55 v2, treno 8 | ✅ già fatta |

## 2. Il vecchio piano, riletto con le decisioni nuove

Il piano di B (`LibreFolio_developer_journal/Release_2/Phase_1/07_backupDocker/plan-phase01BackupDocker.prompt.md`,
7 602 righe) **non contiene una sezione L3**: la parola «L3» non compare mai (grep del 22/10). L3 stava nel documento
di architettura B (`backup-architettura-cloud-20261020.md`, sessione «Release 1.3 planning»), che le decisioni del
22/10 **sostituiscono**. Quindi non c'è un «piano L3 da copiare»: c'è l'impianto B3/B4/B5 da estendere.

| Riga del vecchio piano | Cosa dice | Oggi |
|---|---|---|
| 143-232, «3.3 Ripristino: caricamento, ispezione, prova su copia», «3.6 Sessioni dopo un ripristino» | la prova su copia, i totali di controllo, la chiusura delle sessioni | **resta**: la rotta del pannello riusa tutto |
| 352-375, «3.13 Litestream (F25)»; 5358-5470, «B7 — Litestream: analisi», D1-D10; variabili `LIBREFOLIO_LITESTREAM_*` (3.16) | replica continua del DB con Litestream, avviatore `start_server.py`, `kill_timeout` 30 | **cade**: niente Litestream né replica (decisione 1). `scripts/docker/start_server.py` non esiste (solo `check_frontend_build.sh`): non va creato |
| 376-380, «3.14 Scaricamento per il pannello (decisione 7)» | token, stesso job dell'admin, senza chiave e senza password | **resta**, già fatto; **nuovo**: con la chiave pubblica impostata il job del pannello produce una busta L3 |
| 2320, «B3 — il ripristino: analisi»; 3296, «B5c — l'esito senza sessione (biglietto monouso)» | conferma, riavvio, esito con biglietto | **resta**; il pannello legge l'esito dalla propria rotta di stato, non dal biglietto |
| 5595, «B-18 — `restore --instance-key-file`» | i segreti di un archivio senza chiave si ricifrano dalla chiave vecchia | **resta**: nel cloud la chiave d'istanza non è mai nella busta (decisione 39) e sulla macchina nuova la rimette il coordinatore con la variabile; il ripristino non deve chiederla |
| 7462, «La domanda di E sul ripristino a mano (`#by-hand`)» | unzip prima del primo avvio | **resta** (self-hosted) |
| 28 e 206: «scrypt (mai HKDF) da una password» | nota H-3 | **resta** per la password; per la chiave pubblica l'HKDF è su un segreto X25519, non su una password: lecito |
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

**Nuovo, da scrivere**: busta L3 (versione 2), `kid`, keygen e CLI, apertura con la chiave del file, `sha256` nel lavoro,
scopo `backup:restore` e rotte del pannello, modo «ripristino in corso», estensione di `GET /api/v1/panel/status`, i due
avvisi del rapporto di stage, la doc self-hosted (zip in cartella + backrest/restic), il round trip L3 e gli E2E.

## 3. La specifica, primo prodotto del lotto (proposta)

### 3.1 La busta a chiave pubblica: formato `LFBK` versione 2

Oggi (versione 1, 52 byte, big-endian): `LFBK` · versione `1` · kdf `1` (scrypt) · `log2_n` · `r` · `p` · `salt` (16) ·
`check` (16) · `chunk_size` (4) · `nonce_prefix` (7). **Le buste con password restano byte per byte come oggi** (versione
1): nessun rischio per i file già fatti e per i test di B4.

**Versione 2 = busta chiusa con una chiave pubblica X25519.** Intestazione fissa di **148 byte**:

| Offset | Byte | Campo | Valore |
|---|---|---|---|
| 0 | 4 | magic | `LFBK` |
| 4 | 1 | version | `2` |
| 5 | 1 | key_type | `2` = sealed X25519 (`1` resta scrypt, solo in versione 1) |
| 6 | 1 | log2_n | `0` (il lettore richiede zero) |
| 7 | 1 | r | `0` |
| 8 | 1 | p | `0` |
| 9 | 16 | salt | 16 byte zero |
| 25 | 16 | check | 16 byte zero (il controllo della chiave lo fa il tag di `W`) |
| 41 | 4 | chunk_size | come oggi, `1 MiB` scritto; letto fra 64 KiB e 16 MiB |
| 45 | 7 | nonce_prefix | casuale |
| 52 | 16 | kid | `SHA-256(P_i)[:16]`, l'impronta della chiave pubblica del destinatario |
| 68 | 32 | E | chiave pubblica X25519 **effimera**, nuova per ogni busta |
| 100 | 48 | W | la chiave del file avvolta: 32 byte di testo cifrato + 16 di tag |

I primi 52 byte riusano la `struct` di oggi (`>4sBBBBB16s16sI7s`): il lettore legge 52 byte, vede versione 2 e
`key_type` 2, e legge gli altri 96. Un lettore di oggi rifiuta la versione 2 con `envelope_unsupported` («viene da un
LibreFolio più nuovo»): giusto, perché la `.lfbk` non è mai stata rilasciata e la 1.3 legge tutte e due.

**Scambio di chiavi e avvolgimento** (solo primitive di `cryptography`, come oggi; nessuna crittografia scritta a mano):

```
K_f  = 32 byte casuali                                   # la chiave del file (AES-256-GCM dei blocchi)
e, E = coppia X25519 effimera                            # e si butta subito dopo
S    = X25519(e, P_i)                                    # rifiutare S tutto zero
K_w  = HKDF-SHA256(ikm = S, salt = E || P_i (64 byte), info = b"librefolio-lfbk/v2/x25519-wrap", len = 32)
W    = AES-256-GCM(K_w).encrypt(nonce = 12 byte zero, data = K_f, aad = header[0:100])
```

- Il nonce zero per `W` è lecito perché `K_w` è nuova a ogni busta (è lo stesso schema del destinatario X25519 di `age`).
- `aad = header[0:100]`: magic, versione, `chunk_size`, `nonce_prefix`, `kid`, `E`. Chi cambia un byte dell'intestazione
  rompe il tag di `W`.
- I **blocchi** sono identici a oggi: `AESGCM(K_f)`, nonce = `nonce_prefix` (7) + indice (4) + flag ultimo (1), **aad =
  tutta l'intestazione (148 byte)**.
- **Chi apre**: il coordinatore calcola `S = X25519(s_i, E)`, ricava `K_w`, apre `W` e ottiene `K_f`. **La chiave
  privata `s_i` non lascia mai il coordinatore**; alla macchina nuova manda la busta ancora cifrata e `K_f`.
- **L'istanza apre con `K_f`**: `EnvelopeKey(header, K_f)` direttamente; il tag del primo blocco dice se la chiave è
  sbagliata (`wrong_file_key`). Non le serve `kid`, non le serve `P_i`.
- **Dimensione**: 96 byte in più per file. Niente altro.

### 3.2 La chiave pubblica dell'istanza e il `kid`

- Variabile **`LIBREFOLIO_BACKUP_PUBLIC_KEY`**: la chiave pubblica X25519 grezza (32 byte) in **base64url senza
  padding, 43 caratteri**, lo stesso formato delle chiavi del pannello (`config/hosting_panel.py:572`). **Non è un
  segreto**: niente `_FILE`. Una sola chiave nella 1.3 (un destinatario); più destinatari sono una versione 3, dopo.
- **`kid` = `SHA-256(P_i)[:16]`**, in testo 32 cifre esadecimali. Nessuna etichetta scelta a mano: il coordinatore lo
  ricalcola dalla chiave pubblica (che ricava dalla madre, dall'id dell'istanza e dalla versione: decisioni §4) e così
  trova la privata giusta anche dopo una rotazione.
- Valore illeggibile (non 43 caratteri, non una chiave X25519): controllo d'avvio **`backup.public_key`** in errore e
  `POST /api/v1/backup/panel/jobs` risponde **`503 backup_panel_unavailable`**. Mai un ripiego allo zip in chiaro:
  chiuso, come il token.
- Con la variabile impostata, **i backup del pannello sono sempre buste L3** (`file_name` con `.lfbk`, `encrypted: true`,
  campo nuovo `sealed_kid`). I backup dell'amministratore dalla UI restano con password. Il job del pannello **non porta
  mai la chiave d'istanza** (già così oggi: decisione 39) e un test lo fissa anche per la busta.

### 3.3 Keygen e CLI (per self-hoster, test e assistenza)

- `./dev.py backup keygen --private-key-file FILE`: scrive la privata X25519 (32 byte base64url, file `0600`, mai
  sovrascritto) e stampa la pubblica da mettere in `LIBREFOLIO_BACKUP_PUBLIC_KEY` e il suo `kid`.
- `./dev.py backup create --public-key CHIAVE` (o `--sealed`, che legge la variabile): un backup L3 dalla riga di comando.
- `./dev.py backup decrypt ARCHIVIO --private-key-file FILE -o out.zip` e `backup inspect`/`restore --private-key-file FILE`:
  aprono una busta L3 in locale (chi ha la privata). Chi ha solo la chiave del file: `--file-key-file FILE` (32 byte
  base64url), lo stesso ingresso della rotta del pannello.
- La derivazione delle chiavi dalla madre (`HKDF(madre, "librefolio-backup" + id istanza + versione)`) è del
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
### 3.4 Vettori di prova (nella specifica e in un file condiviso)

Un file JSON, `backend/tests/.../fixtures/lfbk_v2_vectors.json`, copiato tale e quale nel repo del coordinatore, con:
1. una privata di prova `s_i`, la sua pubblica `P_i`, il `kid` atteso;
2. una `e` effimera fissa, un `nonce_prefix` fisso, `chunk_size = 65536`, un testo in chiaro corto («LibreFolio lfbk v2
   test vector\n»): l'intestazione attesa (148 byte in hex), `W` atteso, `K_f`, lo `sha256` del file intero;
3. un vettore «chiave sbagliata»: stessa busta, `K_f` con un byte cambiato → `wrong_file_key`;
4. un vettore «intestazione manomessa»: `kid` cambiato → `envelope_damaged` al primo blocco;
5. un vettore di una busta **versione 1** di oggi, perché resti leggibile.
I test di B li leggono e li rigenerano con `encrypt_file(..., ephemeral=..., nonce_prefix=...)` (parametri «per i test»,
come oggi `salt` e `nonce_prefix`). Pubblicati anche nella guida per hoster (sezione «Test Vectors», come per i biglietti).

### 3.5 La rotta di ripristino del pannello (scopo `backup:restore`)

Principi: **solo biglietto L2** di scopo `backup:restore` (nessun token L1 esiste per questo scopo: `read_token` dà
`None`); con `LIBREFOLIO_PANEL_PUBLIC_KEYS` non impostata le rotte rispondono `404` come le altre; funziona **solo nel
modo «ripristino in corso»** (proposta, domanda 4 del piano); **mai su un'istanza bloccata** (`423 instance_blocked`,
anche al pannello: il blocco fa uscire i dati, non entrare). Stessi job, stesse prove su copia dell'admin: cambia solo
chi chiama (come `panel.py` rispetto a `instance.py`).

| Passo | Rotta | Corpo | Risposta |
|---|---|---|---|
| Carica | `PUT /api/v1/backup/panel/restore/upload` | corpo grezzo `application/octet-stream`, **in streaming** (come l'admin: a pezzi su disco, mai in memoria), limite `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` (500 nel managed) | `201 {upload_id, size, kind}` (`kind`: `envelope` o `zip`) |
| Prova su copia | `POST /api/v1/backup/panel/restore/stage` | `{"upload_id": "…", "file_key": "<43 caratteri base64url>"}` (`file_key` obbligatoria per una busta, ignorata per uno zip) | `202` lo stage da seguire |
| Segui | `GET /api/v1/backup/panel/restore/stage/{stage_id}` | — | `RestoreStage`: `phase`, `done_bytes/total_bytes`, poi `report` (`administrators`, `control_totals`, `warnings`, `blockers`, `restorable`) o `error_code` |
| Conferma | `POST /api/v1/backup/panel/restore/stage/{stage_id}/confirm` | — (`confirmed_by = "panel"`, con il `kid` del biglietto) | `202 RestoreStatus` (`state: pending`) |
| Riavvia | `POST /api/v1/backup/panel/restore/restart` | — | `202 RestoreStatus`; SIGTERM al processo dopo la risposta; la restart policy `always` lo rialza |
| Stato | `GET /api/v1/backup/panel/restore/status` | — | `RestoreStatus`: `none`, `pending`, `in_progress`, `committed`, `rolled_back` (+ `reason`, `waiting`, `backup_created_at`) |
| Annulla | `DELETE /api/v1/backup/panel/restore/pending` | — | `204` |

- **Niente parola da scrivere** per confermare (il biglietto è l'autorità) e **nessun biglietto d'esito**: il pannello
  legge lo stato dalla sua rotta di stato, o dal campo `restore` di `GET /api/v1/panel/status` (scopo `status`).
- **Un `jti` nuovo per ogni chiamata**, anche per il polling (già regola L2); un `401` non si riprova (regola del
  coordinatore).
- Il pannello vede solo i suoi stage (origine `panel`), come per i job di backup.

**Codici d'errore** (`detail.code`), oltre a quelli già dell'admin (`backup_too_large` 413, `backup_upload_empty` e
`backup_upload_incomplete` 400, `backup_no_space` 507, `backup_upload_not_found` 404, `restore_busy` 409,
`envelope_damaged` 400, `envelope_unsupported` 409, `restore_stage_not_found` 404, `restore_not_restorable` 409,
`restore_stage_expired` 410, `restore_already_pending` 409, `restore_not_pending` 404/409, `restore_state_unreadable` 500):

| Risposta | `code` | Quando |
|---|---|---|
| `400` | `file_key_required` | una busta senza `file_key` |
| `400` | `file_key_invalid` | non 43 caratteri base64url / non 32 byte |
| `400` | `wrong_file_key` | la chiave non apre il primo blocco (il caricamento resta, per un altro tentativo) |
| `409` | `restore_mode_required` | l'istanza non è nel modo «ripristino in corso» (se la domanda 4 ha risposta (a)) |
| `423` | `instance_blocked` | istanza bloccata |
| `401`/`429`/`503` | `backup_restore_unauthorized`, `panel_ticket_*`, `panel_too_many_attempts`, `backup_restore_unavailable` | come gli altri scopi del pannello |

### 3.6 Il modo «ripristino in corso»

- **Variabile `LIBREFOLIO_AWAIT_RESTORE`** (booleana, stessi valori di `LIBREFOLIO_BLOCKED`: `1/0, true/false, yes/no,
  on/off`), letta a ogni chiamata come il blocco. **Senso**: «questa macchina è nata su un volume vuoto e aspetta i dati
  dal pannello: non è un'istanza nuova».
- **All'avvio** (`app_lifespan.STARTUP_STEPS`): si saltano `admin-bootstrap` (niente admin iniziale, niente `/setup`),
  `scheduler`, `provider-prewarm`, `market-holidays`, `brim-parse-pool`, `stored-currencies`. Restano `database`
  (un DB vuoto migrato: il ripristino lo scambia), `pending-restore`, `restore-commit`, `idle-monitor` (la macchina può
  dormire fra una chiamata e l'altra del coordinatore: il proxy la sveglia).
- **API**: rispondono solo `GET /system/health`, `/system/ready` (200 con `mode: awaiting_restore`), `/system/info`,
  `/system/instance` (pubblica: aggiunge `mode`), le rotte del pannello (`panel/status`, `backup/panel/jobs…`,
  `backup/panel/restore/…`), `wake-sync` (non esegue nulla e risponde `awaiting_restore`, come oggi risponde `blocked`).
  **Tutto il resto risponde `423 instance_awaiting_restore`**, anche la registrazione, il primo account e `/auth/setup`:
  su un DB vuoto `first_account_open` sarebbe vero e l'app proporrebbe «crea il primo account», che qui è vietato.
- **`POST /api/v1/backup/panel/jobs` in questo modo risponde `409 backup_awaiting_restore`**: un backup di un'istanza
  vuota non deve mai nascere («mai partire vuoti sopra un backup buono»).
- **Frontend**: il layout `(app)` mostra una pagina «Ripristino in corso» (come `InstanceBlockedPage`, in
  `lib/features/instance/`), letta da `GET /system/instance` prima di qualunque login, nelle 4 lingue, con il link
  dell'assistenza. Nessun dato.
- **Controllo d'avvio** `platform.await_restore` (scheda Sicurezza): avverte che il modo è acceso.
- **Uscita** (proposta (a), domanda 5): solo il coordinatore, togliendo la variabile e riavviando la macchina quando
  `restore.state = committed`. L'istanza non esce mai da sola. Dopo un ripristino riuscito e prima del riavvio del
  coordinatore, la pagina dice «dati ripristinati, in attesa che il fornitore riapra l'istanza».
- **`GET /api/v1/panel/status`** (scopo `status`) cresce così, con `extra="forbid"` aggiornato:

```json
{
  "admin_setup": "none",
  "setup_expires_at": null,
  "mode": "awaiting_restore",
  "restore": {"state": "committed", "reason": null, "waiting": null, "backup_created_at": "2026-10-22T03:00:12Z", "stage_id": "…"}
}
```
  `mode`: `normal | awaiting_restore`; `restore`: `null` quando non c'è nessun ripristino registrato. È un cambiamento di
  contratto (il contratto oggi dice «solo quelle due chiavi»): il coordinatore deve ignorare chiavi che non conosce.

### 3.7 Lo `sha256` dell'archivio e il rapporto di stage

- `GET /api/v1/backup/panel/jobs/{id}` (e la UI) a lavoro finito riportano **`file_sha256`** (64 hex): già calcolato,
  oggi tolto dalla vista. Più `sealed_kid` per una busta L3. Il coordinatore confronta l'hash dopo lo scarico.
- Rapporto di stage (`StagingReport` / `RestoreStageReport`): `administrators` c'è già. Si aggiungono:
  - l'avviso fisso, in UI e nel rapporto, **«si entra con le credenziali del backup; le sessioni di oggi si chiudono»**
    (codice `credentials_from_backup`, sempre presente: è la verità di ogni ripristino, già in `_close_the_way_in`);
  - l'avviso forte **`confirming_account_not_in_backup`** quando chi conferma dalla UI (`admin.username`) non è fra gli
    `administrators` della copia: lo calcola la rotta di conferma dell'admin, lo mostra `RestoreReportModal` in rosso,
    con la frase «dopo il riavvio non potrai entrare con questo account». Per il pannello non si applica.
- **Chiave d'istanza fuori dal backup (decisione 39)**: niente da cambiare, un test lo fissa anche per la busta L3 e per
  la rotta del pannello (`instance_key_included` sempre `false` nei job del pannello).

### 3.8 Doc self-hosted

- `backup_restore.en.md`, dopo «Keep Copies Off the Server»: **«Backups with backrest or restic»** (una ricetta: lo zip
  notturno in una cartella con `--output`, poi `restic backup` di quella cartella verso S3/B2/SFTP con la retention;
  backrest come interfaccia web di restic). Nessun codice nostro: solo doc, con l'avviso che un restic non cifra con
  chiave pubblica e che la chiave di restic va custodita come la password.
- «Secure Backups»: la busta a chiave pubblica (`keygen`, `--public-key`, `decrypt --private-key-file`), quando usarla
  (un server che fa backup automatici senza tenere la password sul disco).
- `hosting_providers.en.md` (di H): la busta L3 per il pannello (`LIBREFOLIO_BACKUP_PUBLIC_KEY`, `kid`, `file_sha256`),
  la rotta di ripristino, il modo «ripristino in corso», i vettori di prova, le righe nuove di `GET /panel/status`.
- `configuration.en.md`: le due variabili nuove e i due controlli d'avvio.

## 4. I passi, in ordine

| # | Chi | Passo | Rossi da scrivere prima | Fatto quando | Giorni |
|---|---|---|---|---|---|
| **B1** | B | **Specifica** (§3, rifinita) + **vettori di prova** (§3.4) + una pagina di contratto per il coordinatore cloud (le rotte, i codici, le variabili, lo stato); nessun codice di prodotto | nessuno (è un documento); i vettori si generano con uno script fuori dal repo o nel worktree, senza toccare `envelope.py` | il developer dà l'ok; il coordinatore cloud conferma di poter aprire `W` con i vettori (loro lato) | 2-3 |
| **B2** | B | **Busta v2**: `envelope.py` legge v1 e v2, `seal_file(src, dst, public_key)`, `open_with_file_key(path, key) → EnvelopeKey`, `kid`; `config/backup.py` legge `LIBREFOLIO_BACKUP_PUBLIC_KEY`; controllo d'avvio `backup.public_key`; il job del pannello sigilla quando la chiave c'è; `file_sha256` e `sealed_kid` nella vista; CLI `keygen`, `create --public-key/--sealed`, `decrypt/inspect/restore --private-key-file/--file-key-file` | `services backup-envelope` (vettori: byte identici, v1 ancora leggibile, chiave sbagliata, intestazione manomessa, `S` zero rifiutato, chunk_size fuori limite); `api backup-panel` (busta quando la chiave c'è, 503 con chiave illeggibile, `file_sha256`, mai la chiave d'istanza); `utils backup-cli*` | verdi sulla corsia; `api sync` senza differenze oltre i campi nuovi; `front check` 0/0 | 3-4 |
| **B3** | B | **Apertura con la chiave del file nel ripristino**: `restore_jobs.start_check(upload_id, *, password=None, file_key=None)`, `_envelope_key` con i due ingressi, `PasswordRequiredError` → anche `FileKeyRequiredError`; i due avvisi del rapporto (§3.7) e la UI di `RestoreReportModal`; i testi nelle 4 lingue | `services backup-staging`, `api backup-restore` (busta v2 + chiave giusta/sbagliata/mancante), Vitest di `RestoreReportModal` (avviso forte) | verdi; `check-orphans` verde | 1,5-2 |
| **H1** | H | **Modo «ripristino in corso»** (§3.6): `config/platform.py` (`await_restore()`), passi d'avvio saltati, `423 instance_awaiting_restore` in `instance_block.py` (stessa dipendenza del router, secondo stato), `/system/instance` e `/ready` con `mode`, `wake-sync` che risponde `awaiting_restore`, `409 backup_awaiting_restore` sui job del pannello, controllo `platform.await_restore`, pagina frontend, `GET /panel/status` con `mode` e `restore` | `api hosting-panel-routes`/`panel-status` (schema nuovo), un test del router (ogni rotta risponde 423 tranne la lista), `services app-lifespan` (passi saltati), Vitest della pagina, E2E «la pagina si vede senza login» (corsia con `--lane-setting LIBREFOLIO_AWAIT_RESTORE=1`) | verdi; la doc hoster aggiornata | 2 |
| **H2** | H | **Rotte del pannello** (§3.5): `PanelScope.RESTORE = "backup:restore"` solo biglietto; modulo nuovo `api/v1/backup/panel_restore.py`; registrazione in `backup/__init__.py` (una riga); regola «solo nel modo» (se (a)); `423` al pannello su istanza bloccata; log «Hosting panel request» con scopo `backup:restore` | `api backup-panel-restore` (nuovo): 404 senza chiavi, token L1 rifiutato (401), biglietto di scopo `backup` rifiutato (`panel_ticket_wrong_scope`), flusso completo su copia, `restore_mode_required`, 423 su bloccata, `file_key` sbagliata | verdi; `security-review` auto sul diff | 2 |
| **B4** | B | **Doc** (§3.8) con `docs-writer`; righe CHANGELOG proposte (✨ busta a chiave pubblica e `keygen`; ✨ rotta di ripristino per il pannello e modo «ripristino in corso»; 🔄 `file_sha256` nei lavori) | — | `mkdocs build` stretto e `check-links` verdi | 1 |
| **B5** | B (+ H per la corsia) | **Round trip L3** (estensione di `api backup-roundtrip`): istanza popolata → busta del pannello → `kid` e `sha256` controllati → apertura di `W` con la privata di prova (lato «coordinatore», nel test) → `PUT/POST` sulle rotte del pannello di un'istanza vuota in modo «ripristino in corso» → `confirm` → `restart` → avvio in un processo nuovo → `committed` → stesse righe, stessi report → la variabile tolta → istanza normale, login con le credenziali del backup. Più l'E2E Playwright della pagina «Ripristino in corso» e di `RestoreReportModal` con l'avviso forte | il round trip è il rosso stesso (scritto prima della cura di H2) | verde due volte di fila sulla corsia; registrato nel runner | 1,5-2 |
| **SEC** | coordinatore (Opus, agente `security-review` indipendente) | Revisione del diff B2+B3+H1+H2: la busta (nonce, aad, `S` zero, limiti), la rotta (scopo, blocco, modo, limiti di dimensione, nessun byte in chiaro nei log), il modo (nessuna rotta sfuggita al 423) | — | rapporto scritto; i medi curati prima del treno; i bassi nel backlog | 1 + 0,5-1 di cure |
| **T10** | coordinatore | Treno 10: candidato, gate completo, CHANGELOG, giornale | — | gate verde | — |

**Totale: 14-18 giorni** di lavoro (B 9-12, H 4, revisione 1,5-2), contro i 13-17 delle decisioni: coerente. In
calendario: B1 (2-3 giorni) → tuo ok → B2 e H1 in parallelo → B3 e H2 → B4, B5 → SEC → treno 10: **~3 settimane**.

Ordine dei commit (coordinatore): B1 (doc e vettori) → B2 → H1 (indipendente da B2, può andare anche prima) → B3 → H2
(dopo B2, perché chiama `start_check(file_key=…)`) → B4 → B5 → cure della revisione → treno.

## 5. Chi fa cosa: prodotto e coordinatore cloud, senza sovrapposizioni

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

Richieste del coordinatore cloud (brief §B), tutte coperte: specifica con vettori (B1), forma della rotta (§3.5),
variabile e uscita del modo e risposta di `GET /panel/status` (§3.6), `sha256` (§3.7), chiave d'istanza fuori (§3.7).

## 6. Rischi e cose da tenere d'occhio
- **Il blocco e il modo sono due stati diversi**: un'istanza bloccata non applica un ripristino (`waiting:
  instance_blocked`, `apply.py:700-712`); un'istanza in attesa di ripristino lo applica e basta. Se il coordinatore mette
  tutte e due le variabili per sbaglio, il blocco vince e il ripristino aspetta: lo dice `restore.waiting`.
- **Spazio del volume**: uno stage tiene la busta caricata, la copia decifrata e la copia scompattata; un ripristino
  tiene anche `previous/`. Su un volume piccolo con 500 MB di upload non ci sta: va misurato (spike del coordinatore
  cloud) e documentato; il prodotto risponde già `507` quando manca spazio.
- **La chiave d'istanza**: nel cloud arriva dall'ambiente e non è mai nella busta. Sulla macchina nuova la deve
  rimettere il coordinatore **prima** del ripristino, altrimenti i segreti dei plugin restano illeggibili
  (`secrets_unreadable` nel rapporto: il coordinatore lo legge e si ferma).
- **Il registro dei `jti`** sta fuori dai backup (`panel_tickets.sqlite3`): su una macchina nuova è vuoto, e va bene.
- **L'`aud` dei biglietti** è l'origine di `LIBREFOLIO_PUBLIC_URL`: la macchina nuova deve avere lo stesso URL della
  vecchia, altrimenti `panel_ticket_wrong_audience`.
- **Nessun byte in chiaro nei log**: la `file_key` non va mai in un messaggio, in un `repr`, in un 422 (le rotte del
  backup usano già `NoInputEchoRoute`: la rotta nuova deve usarlo).
