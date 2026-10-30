# Contratto L3 — backup notturno cifrato e ripristino dal pannello

> **CONCORDATO il 22/10/2026, prodotto + cloud** (bozza 3). Il lato cloud è stato firmato con il via del developer, che
> ha deciso anche D1 (`503`, mai uno zip in chiaro) e D4 (`pyrage` 1.4.0 anche nel coordinatore). D5: 500 MB provvisori,
> con il controllo dello spazio del coordinatore prima del caricamento (coordinatore della 1.3, 22/10); i numeri
> definitivi vengono dallo spike del backup e non cambiano la forma del contratto.
>
> Storia: il coordinatore cloud ha accettato la struttura e chiesto R1-R4 («⇄ cloud»); il prodotto ha risposto a tutte e
> quattro («⇄ prodotto»); il cloud ha accettato le risposte, compresa la condizione di R4.
>
> **Fonti di verità**:
> - `BACKUP-decisioni-20261022.md` §10: il formato, deciso dal developer il 22/10 pomeriggio;
> - `PIANO-ondata4.md`, domande 4-8: approvate con le raccomandazioni.
>
> Il codice di riferimento è `dev_release2` = `c042f2481`.
>
> **Chi fa cosa**:
> - il prodotto scrive il lato istanza: B fa la busta, il job e la CLI; H fa la rotta di ripristino e il modo (lotto H-62);
> - il coordinatore cloud scrive il suo lato;
> - le due parti si provano con gli stessi vettori (§9).

Convenzioni:
- i codici d'errore sono `detail.code` con un `message` in inglese, come nelle rotte del backup di oggi;
- «pannello» è chi chiama con una credenziale del pannello (`LIBREFOLIO_PANEL_PUBLIC_KEYS`);
- «⇄» segna i punti cambiati dopo le richieste del cloud.

---

## 1. Il disegno in una riga

Ogni notte l'istanza consegna un `.tar` con tre file:
- un manifest in chiaro;
- la **password casuale** cifrata con `age` verso i destinatari dell'istanza;
- il `.lfbk` di oggi, cifrato con quella password.

Al ripristino il coordinatore apre solo la password e manda all'istanza nuova il `.lfbk`, ancora cifrato, più la
password. L'istanza usa il ripristino con password che esiste già.

**Nessuna crittografia scritta da noi**: il `.lfbk` resta versione 1 (scrypt + AES-256-GCM, lotto B4) e `age` è la
libreria `pyrage` 1.4.0 su entrambi i lati.

## 2. I destinatari dell'istanza ⇄

| | |
|---|---|
| Variabile | **`LIBREFOLIO_BACKUP_RECIPIENTS`** ⇄ |
| Valore | **1 o 2** destinatari `age` X25519 `age1…`, separati da virgola; gli spazi attorno si ignorano. Un `age1…` è in Bech32 minuscolo, 62 caratteri: è la riga `# public key:` di `age-keygen` o di `./dev.py backup keygen`. Con 2 destinatari la password si cifra per entrambi: serve durante la **rotazione** della chiave. |
| Segreto? | **No**: non c'è la forma `_FILE`. |
| Lettura | con `pyrage.x25519.Recipient.from_str`. Solo X25519: niente chiavi SSH, plugin o ibridi. Nessun duplicato, al massimo 2. |
| Valore illeggibile | il controllo d'avvio **`backup.recipients`** va in errore e `POST /api/v1/backup/panel/jobs` risponde **`503 backup_panel_unavailable`**. **Mai** uno zip in chiaro. |
| Non impostata | `selfhosted`: i job del pannello sono zip in chiaro come oggi. `managed`: **`503 backup_panel_unavailable`** (proposta del prodotto, vedi D1). |

Niente `kid` ⇄: lo sostituisce la stringa `age1…` stessa. Sta nel manifest (§3.2) e nella vista del job (§4).

La privata (`AGE-SECRET-KEY-1…`) non è mai sull'istanza:
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
- un self-hoster la crea con `./dev.py backup keygen` (§8).

## 3. Il file: `.tar` sigillato

### 3.1 Nome e struttura ⇄

**Nome**: `librefolio-backup-YYYYMMDD-HHMMSS.tar`, con l'ora UTC di creazione del job, come gli zip di oggi.

È un tar **POSIX ustar non compresso** con **esattamente tre membri, in quest'ordine**:

| # | Nome | Contenuto | Dimensione |
|---|---|---|---|
| 1 | `manifest.json` | in chiaro, vedi §3.2 | < 1 KiB |
| 2 | `password.age` | la password cifrata con `age`, in **formato binario, non armor** (fissato). In chiaro è **la password in ASCII, 43 byte, senza a capo** | ~200-400 byte |
| 3 | `backup.lfbk` | la busta `.lfbk` **versione 1** aperta da quella password; dentro, lo zip del backup **senza la chiave d'istanza** (§7) | quella del backup |

**L'ordine è un vincolo del prodotto** (il cloud aveva proposto `backup.lfbk` per primo): i due file piccoli stanno davanti.
Così una lettura parziale di **10 240 byte, un record tar** (⇄ cloud/prodotto: al peggio l'intestazione del `.lfbk` finisce al byte 9 780 = 3 × 512 di intestazioni tar + 2 × 4 096 + 52) su un object store dà manifest, password e i 52 byte d'intestazione del `.lfbk`: il
coordinatore verifica la copia (§3.5) senza scaricarla.

### 3.2 `manifest.json` ⇄

È JSON UTF-8, con chiavi ordinate e senza spazi (`json.dumps(…, sort_keys=True, separators=(",", ":"))`), senza a capo
finale. Non contiene dati personali.

```json
{"created_at":"2026-10-23T03:00:12Z","db_revision":"0042_…","format":"lfbk-tar","lfbk_sha256":"…64 hex…","lfbk_size":412080128,"librefolio_version":"1.3.0","password_member":"password.age","recipients":["age1…"],"version":1}
```

| Campo | Valore |
|---|---|
| `format`, `version` | `"lfbk-tar"`, `1`. Un lettore rifiuta altri valori |
| `recipients` | i destinatari usati per `password.age`, nello stesso ordine della variabile (1 o 2) |
| `lfbk_sha256`, `lfbk_size` | lo SHA-256 (64 hex minuscoli) e la dimensione in byte del membro `backup.lfbk` |
| `created_at` | l'ora di creazione del job in UTC, al secondo, con la `Z` finale |
| `librefolio_version`, `db_revision` | la versione dell'app e la revisione Alembic del DB, gli stessi valori che stanno nel manifest dello zip (`manifest.py`) |
| `password_member` | `"password.age"`: rende esplicito il legame |

**Lettura del manifest** (⇄ cloud/prodotto): si confronta il **contenuto**, non i byte. JSON UTF-8 valido, un oggetto,
chiavi doppie rifiutate, tipi esatti (`version` intero, `lfbk_size` intero non negativo, `recipients` lista di 1-2
stringhe `age1…`), e **le chiavi sconosciute si rifiutano**: un campo nuovo vuol dire `version` 2. Chi scrive usa la
forma canonica; chi legge non la pretende.

Il manifest **non è autenticato** da solo: è una guida per i controlli, non una prova. Le prove sono lo `sha256` del `.tar`
dato dalla rotta autenticata (§4) e l'apertura della password (§3.5).

### 3.3 La password

- È fatta di **32 byte** da `secrets.token_bytes(32)`, scritti in **base64url senza padding: 43 caratteri** `[A-Za-z0-9_-]`.
  Il `.lfbk` la usa così com'è: è ASCII, quindi NFC non la cambia.
- La genera **la macchina, una per ogni backup**, e non passa dalle regole delle password dell'admin.
- Vive solo nella memoria del thread del job, come la password di oggi (`jobs.py:13`). Non va mai:
  - nello stato del job;
  - in un log o in un `repr`;
  - su disco in chiaro.

### 3.4 I campi dei membri del tar (deterministici)

| Campo | Valore |
|---|---|
| formato | `tarfile.USTAR_FORMAT` |
| tipo | file regolare (`REGTYPE`); niente cartelle, link, PAX o GNU |
| `mode` | `0o600` |
| `uid` / `gid` | `0` / `0` |
| `uname` / `gname` | vuoti |
| `mtime` | `created_at` in secondi Unix |
| fine | i due blocchi zero di fine archivio, poi il riempimento fino a un multiplo di 10 240 byte (il default di `tarfile`) |

Con gli stessi tre membri il `.tar` è identico byte per byte, e i vettori lo verificano (§9).

### 3.5 Lettura del `.tar` (coordinatore e CLI): regole strette

- Mai `extractall`: i membri si leggono come flussi (`extractfile`).
- **Ogni lato sceglie il suo lettore** (⇄ cloud/prodotto): il cloud ha un lettore ustar suo, stretto e incrementale (a
  spinta da un flusso asincrono); il prodotto ha anche lui un lettore ustar suo, breve e stretto (`instance_backup/sealed.py`), e usa `tarfile` solo per scrivere (⇄ prodotto, 22/10). Le regole sono queste e uguali per
  tutti: solo intestazioni ustar, **nessuna intestazione PAX o GNU** (un lettore che la incontra rifiuta l'archivio),
  solo file regolari.
- Si rifiuta l'archivio quando:
  - i membri non sono esattamente tre;
  - i nomi o l'ordine sono diversi;
  - un membro non è un file regolare;
  - `manifest.json` supera 4 096 byte o `password.age` supera 4 096 byte;
  - `format` o `version` del manifest sono sconosciuti;
  - `lfbk_size` o `lfbk_sha256` non corrispondono al membro;
  - il `.lfbk` non comincia con `LFBK` versione 1.
- La password decifrata deve essere esattamente 43 caratteri base64url: altrimenti la copia è guasta.
- **«Ultimo backup verificato»** (definizione del cloud, aggiornata) vuol dire, tutto insieme:
  1. lo `sha256` e la dimensione del `.tar` scaricato sono uguali a quelli della vista del job (§4), e la dimensione non è nulla;
  2. il manifest passa le regole qui sopra, e `recipients` contiene **un destinatario dell'istanza di cui il
     coordinatore ha la privata**: quello attuale o uno precedente ancora valido per le copie conservate (dopo una
     rotazione le copie vecchie portano solo il destinatario vecchio) ⇄ cloud;
  3. `password.age` si apre con quella privata;
  4. la password apre l'intestazione del `.lfbk`: scrypt (`n = 2^15`, `r = 8`, `p = 1`, circa 0,1 s e 32 MiB) sui 16
     byte di `salt` dà il `check` scritto nell'intestazione. È la prova che la password è quella giusta per quel
     `.lfbk`, e non decifra nessun dato. **Il coordinatore lo fa sempre** ⇄ cloud: è la prova più forte che non apre i dati.
     **R2 ⇄ cloud**: serve qui la disposizione esatta dei 52 byte (offset e lunghezza di magic, versione, `salt`,
     `check`, `nonce_prefix`…) e la formula del `check` (ingresso, `dklen`, quali byte si confrontano), oppure il
     rimando a file e commit della specifica per sviluppatori. Il caso buono del §9.1 dà già il `check` atteso.

#### 3.5.1 L'intestazione del `.lfbk` e la formula del `check` (R2 ⇄ prodotto)

**Riferimento**: `backend/app/services/platform/instance_backup/envelope.py` a `c042f2481`, cioè `_HEADER`,
`_check_supported`, `_derive` e `unlock`. **Il formato non cambia** con L3.

L'intestazione è di **52 byte, big-endian**, in `struct` `>4sBBBBB16s16sI7s`:

| Offset | Byte | Campo | Valore scritto oggi | Il lettore accetta |
|---|---|---|---|---|
| 0 | 4 | `magic` | `LFBK` | solo `LFBK` |
| 4 | 1 | `version` | `1` | solo `1` |
| 5 | 1 | `kdf` | `1` (scrypt) | solo `1` |
| 6 | 1 | `log2_n` | `15` | da 14 a 16 |
| 7 | 1 | `r` | `8` | da 1 a 8 |
| 8 | 1 | `p` | `1` | da 1 a 2 |
| 9 | 16 | `salt` | casuale | — |
| 25 | 16 | `check` | vedi sotto | — |
| 41 | 4 | `chunk_size` | `1048576` (uint32) | da 65 536 a 16 777 216 |
| 45 | 7 | `nonce_prefix` | casuale | — |

**Ordine dei controlli**: si controllano i limiti **prima** di qualunque derivazione. Un'intestazione fuori dai limiti
non costa mai più di 64 MiB né minuti di calcolo.

```
material = NFC(password).encode("utf-8")      # le nostre password sono ASCII: NFC non le cambia
derived  = scrypt(material, salt=salt, n=2**log2_n, r=r, p=p, dklen=48)
key      = derived[0:32]                      # la chiave AES-256-GCM dei blocchi (al coordinatore non serve)
ok       = hmac.compare_digest(derived[32:48], check)
```

- Se `ok` è falso, la password non apre questo `.lfbk`: l'istanza risponde `wrong_password`.
- **Attenzione** a `hashlib.scrypt`: il `maxmem` di default (32 MiB) è troppo poco per `n = 2^15`, `r = 8`, che ne
  chiede 32 MiB più il resto. Ci sono due modi:
  - passare `maxmem=64 * 1024 * 1024`;
  - usare `cryptography.hazmat.primitives.kdf.scrypt.Scrypt`, come il prodotto.

## 4. Il job di backup del pannello ⇄

Le rotte sono quelle di oggi: `POST/GET/DELETE /api/v1/backup/panel/jobs…`, `GET …/jobs/{job_id}/file` per lo scarico, scopo `backup`.

- Con `LIBREFOLIO_BACKUP_RECIPIENTS` impostata, **ogni job del pannello è sigillato** (domanda 7 approvata). I backup
  dell'admin dalla UI restano `.lfbk` con la password scelta da lui.
- Le fasi (`phase`) sono quelle del codice: `preparing` → `database` → `files` → `finalizing` → `encrypting` → `sealing`, poi `status: done` (⇄ prodotto: «archiving» della bozza è `database`/`files`/`finalizing`). `sealing` è la fase nuova, breve: cifra
  la password e scrive il tar.
- La vista del job finito (`InstanceBackupJob`) ha questi **campi fissati**:

```json
{
  "file_name": "librefolio-backup-20261023-030012.tar",
  "file_size": 412093440,
  "file_sha256": "…64 hex…",
  "encrypted": true,
  "sealed": true,
  "sealed_recipients": ["age1…"],
  "instance_key_included": false
}
```

  - `file_size` e **`file_sha256`** descrivono **il `.tar`**, cioè i byte da scaricare (domanda 8 approvata). Ci sono
    anche nei job della UI, dove si riferiscono allo zip o al `.lfbk`.
  - `sealed` e `sealed_recipients` valgono `false` e `[]` nei job non sigillati.
- `GET …/jobs/{job_id}/file` risponde con `Content-Type: application/x-tar` e un `Content-Disposition` con `file_name` (codice di B, `job_views.py`).
- Il picco di spazio su disco resta **2× la busta**, come oggi: zip + `.lfbk` durante la cifratura, poi `.lfbk` + `.tar`.
  Alla fine resta solo il `.tar`.

## 5. La rotta di ripristino del pannello (H-62) ⇄

**Principi**:
- **solo il biglietto L2** di scopo nuovo **`backup:restore`**; nessun token L1 vale per questo scopo;
- con `LIBREFOLIO_PANEL_PUBLIC_KEYS` non impostata le rotte rispondono `404`, come le altre del pannello;
- funziona **solo nel modo «ripristino in corso»** (domanda 4 approvata); fuori da quel modo risponde
  `409 restore_mode_required`;
- **mai su un'istanza bloccata**: `423 instance_blocked`;
- il lavoro e la prova su una copia sono quelli dell'admin; cambia solo chi chiama. Il pannello vede solo i suoi stage,
  quelli con origine `panel`;
- la rotta usa `NoInputEchoRoute`: la password non compare mai in un 422 o in un log.

**Forma: due passi, non multipart** ⇄ (il cloud chiedeva quale preferiamo). Prima si carica il `.lfbk` con un `PUT` a
corpo grezzo, poi si manda la password in JSON. I motivi:
- è **lo stesso codice** del ripristino dell'admin: il corpo si scrive a pezzi su disco, con limite e controllo dello
  spazio già provati;
- un multipart da 500 MB farebbe passare il file dal parser multipart e da un file temporaneo in più;
- la password non viaggia nella stessa richiesta del file, quindi non finisce nei log del proxy insieme a un corpo
  enorme.

| Passo | Rotta | Corpo | Risposta |
|---|---|---|---|
| Carica | `PUT /api/v1/backup/panel/restore/upload` | **il membro `backup.lfbk`** (non il `.tar`), corpo grezzo `application/octet-stream`, in streaming. Limite: `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` | `201 {upload_id, size, kind}`; `kind` deve essere `envelope` |
| Prova su copia | `POST /api/v1/backup/panel/restore/stage` | `{"upload_id": "<32 hex>", "password": "<43 caratteri>"}`: lo schema `RestoreStageRequest` dell'admin | `202 RestoreStage` |
| Segui | `GET /api/v1/backup/panel/restore/stage/{stage_id}` | — | `RestoreStage`: `phase`, `done_bytes/total_bytes`, poi `report` **ridotto per il pannello** (R1 ⇄ cloud, sotto) oppure `error_code` |
| Conferma | `POST /api/v1/backup/panel/restore/stage/{stage_id}/confirm` | — (nessuna parola da scrivere: l'autorità è il biglietto) | `202 RestoreStatus` (`state: pending`); `confirmed_by = "panel"`, più il `kid` del biglietto nel registro |
| Riavvia | `POST /api/v1/backup/panel/restore/restart` | — | `202 RestoreStatus`; il SIGTERM arriva dopo la risposta e la restart policy rialza il processo |
| Stato | `GET /api/v1/backup/panel/restore/status` | — | `RestoreStatus`: `none`, `pending`, `in_progress`, `committed`, `rolled_back`, più `stage_id`, `reason`, `waiting`, `backup_created_at` |
| Annulla | `DELETE /api/v1/backup/panel/restore/pending` | — | `204` |

**Ripetibilità** ⇄ (requisito del cloud: ripetere una richiesta non fa mai due ripristini). La garanzia di base esiste
già: c'è **un solo ripristino in attesa alla volta**, e l'avvio lo consuma. Per le rotte del pannello si fissa anche:

| Ripetizione | Risposta |
|---|---|
| `PUT upload` di nuovo | un `upload_id` nuovo; il caricamento precedente si scarta (oggi resta solo l'ultimo). Innocuo |
| `POST stage` con lo stesso `upload_id` mentre la sua prova gira | **`202` con lo stesso stage** (non `409 restore_busy`); con un `upload_id` diverso, `409 restore_busy` |
| `confirm` dello stesso `stage_id` già in attesa | **`202` con lo stesso `RestoreStatus`** (non `409 restore_already_pending`); con uno stage diverso, `409 restore_already_pending` |
| `restart` quando lo stato è già `in_progress` o `committed` per l'ultimo stage confermato | **`202` con lo stato attuale**, senza un secondo SIGTERM; senza nessun ripristino registrato, `409 restore_not_pending` |
| `DELETE pending` senza nulla in attesa | `404 restore_not_pending` (il risultato è lo stesso: niente in attesa) |

Per sapere dove si trova, il coordinatore legge sempre `GET …/restore/status` prima di ripetere.

**R1 ⇄ cloud: il rapporto dello stage visto dal pannello non porta dati del portafoglio né dati personali.** La prima
regola del cloud è che il coordinatore non legge mai i portafogli dei clienti. Il rapporto dell'admin contiene
`administrators` (nomi o email degli utenti) e `control_totals` (cassa per broker e valuta, quantità per posizione):
sono dati del cliente e **non devono uscire dalla rotta del pannello**. Proposta per la vista del pannello:
- restano `restorable`, `blockers` e `warnings` **come codici**, senza testi che citino dati;
- `secrets_unreadable` resta come numero (serve al §7);
- al posto di `administrators` c'è `administrators_count`;
- al posto di `control_totals`, se l'istanza può confrontare i totali della copia con quelli registrati al momento del
  backup, un verdetto `control_totals_match: true|false`; altrimenti niente. Il controllo dei totali lo fa l'istanza,
  il coordinatore legge solo l'esito.

Un test del prodotto fissa che la vista del pannello non contiene `administrators` né `control_totals`.

**R1 ⇄ prodotto: accolta.** Il pannello avrà uno schema suo, `PanelRestoreStageReport`, con `extra="forbid"` ed
**elenco chiuso** dei campi. Il verdetto sui totali **esiste già**: l'istanza confronta da sola i totali registrati nel
backup con quelli della copia aggiornata (`RestoreStageReport.control_totals`, lotto J). Quindi non serve un campo nuovo:
il pannello riceve il verdetto e il numero di differenze, mai le righe.

| Campo del rapporto dell'admin | Nella vista del pannello |
|---|---|
| `backup_created_at`, `backup_app_version`, `backup_origin`, `backup_revision`, `app_version`, `head_revision`, `action` | ✅ uguali |
| `migrations` (revisione + prima riga della descrizione), `post_migration_fixes` (codici) | ✅ uguali: sono testi del codice, non dati |
| `instance_key_included`, `encrypted`, `secrets_rekeyed`, `secrets_unreadable` (conteggi) | ✅ uguali |
| `warnings`, `blockers` | ✅ uguali: sono già solo codici |
| `control_totals` | ✅ uguale: è un verdetto, `same \| changed \| absent \| other_version \| unreadable` |
| `control_totals_differences_count` | ✅ uguale (un numero) |
| `restorable`, `expires_at` | ✅ uguali |
| `administrators` (username) | ❌ → **`administrators_count`** |
| `control_totals_differences` (broker, valuta, asset, importi) | ❌ assente |
| `tables` (righe per tabella, prima/dopo) | ❌ assente: dice quanto è grande il portafoglio, e al coordinatore non serve |
| `files`, `files_size`, `database_size` | ❌ assenti: il cloud ha già `lfbk_size` per lo spazio |

**Regola proposta al cloud per confermare**: `restorable` vero, `secrets_unreadable` a zero (sistema e utenti),
`control_totals == "same"`. Altrimenti non si conferma e scatta un allarme.

Una nightly fatta da una 1.3 ha sempre i totali: `absent` vorrebbe dire un backup di prima del lotto J.

Ci sono altri due punti con dati personali, e **anche questi si chiudono**:
- `RestoreStatus.confirmed_by` oggi porta lo **username** dell'admin che ha confermato. Nella vista del pannello diventa
  `confirmed_via: "panel" | "admin" | "cli"`, senza nomi;
- `GET /api/v1/panel/status` → `restore` ha già solo `state`, `reason`, `waiting`, `backup_created_at` e `stage_id` (§6);
  `state` può valere anche `unreadable`, con `reason` = `io` | `not_a_file` | `invalid` (D7).

**Test di H-62**: lo schema del pannello si confronta con l'elenco esatto dei campi qui sopra. Uno stage reale con due
admin e differenze nei totali non deve lasciare nella risposta del pannello nessuno username né nessun importo.

**R3 ⇄ prodotto: già così per costruzione, e lo fissiamo con un test.** La rotta di caricamento è `async` e
l'autorizzazione è una `Depends`, che FastAPI risolve **prima** di eseguire la funzione. Il corpo si legge dopo, a pezzi,
in `_receive` (`restore.py:108-125` per l'admin; la rotta del pannello la copia). Quindi:
- il biglietto si verifica una volta, all'inizio;
- il suo `jti` si registra in quel momento;
- `exp` non si guarda più per il resto della richiesta.

Uvicorn non ha un limite di tempo sul corpo. Un `PUT` fallito si ripete con un biglietto nuovo. **Test di H-62**: un
biglietto con `exp` a pochi secondi e un corpo inviato più lentamente di così devono dare `201`.

**R3 ⇄ cloud: un caricamento lungo non scade a metà.** Il biglietto L2 dura 5 minuti; un `PUT upload` da centinaia di MB
può durarne di più. Proposta: il biglietto si verifica una volta, all'inizio della richiesta, e il caricamento non si
interrompe quando il biglietto scade durante il corpo. Ogni nuova richiesta, anche la ripetizione di un `PUT` fallito,
usa un biglietto nuovo (`jti` diverso).

**Codici d'errore.** Quelli del ripristino dell'admin, già nel codice:

| Risposta | `code` |
|---|---|
| 400 | `backup_upload_empty`, `backup_upload_incomplete`, **`password_required`**, **`wrong_password`** (il caricamento resta), `envelope_damaged` |
| 404 | `backup_upload_not_found`, `restore_stage_not_found` |
| 409 | `restore_busy`, `envelope_unsupported`, `restore_stage_running`, `restore_not_restorable`, `restore_stage_outdated`, `restore_already_pending`, `restore_pending` |
| 409/404 | `restore_not_pending` |
| 410 | `restore_stage_expired` |
| 413 | `backup_too_large` (con `limit_mb`) |
| 500 | `restore_state_unreadable`, con `reason` nel `detail` (solo le rotte di ripristino; `panel/status` risponde 200 con `restore.state = "unreadable"`, D7) |
| 503 | `backup_restore_unavailable` |
| 507 | `backup_no_space`, `no_space` |

Codici nuovi:

| Risposta | `code` | Quando |
|---|---|---|
| 400 | `restore_envelope_required` | è arrivato uno zip in chiaro o il `.tar` (proposta, D2) |
| 409 | `restore_mode_required` | l'istanza non è nel modo «ripristino in corso» |
| 423 | `instance_blocked` | l'istanza è bloccata |

In più, i codici di ogni rotta del pannello: `401 backup_restore_unauthorized` / `panel_ticket_*` e `429 panel_too_many_attempts`.

**Limite di dimensione**: `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`, lo stesso dell'admin.
- `0` vuol dire nessun limite;
- il valore attivo si legge in `RestoreStatus.upload_limit_mb`;
- nel profilo `managed` il default lo fissa il cloud (proposta 500, D5).

## 6. Il modo «ripristino in corso» (H-62)

- **Variabile `LIBREFOLIO_AWAIT_RESTORE`**: booleana, con gli stessi valori di `LIBREFOLIO_BLOCKED`, letta a ogni chiamata.
- **All'avvio** si saltano `admin-bootstrap` (niente `/setup`), `scheduler`, `provider-prewarm`, `market-holidays`,
  `brim-parse-pool` e `stored-currencies`. Restano `database`, `pending-restore`, `restore-commit` e `idle-monitor`.
- **API**: rispondono soltanto:
  - `GET /system/health`;
  - `/system/ready` (200, `mode: awaiting_restore`);
  - `/system/info`;
  - `/system/instance` (aggiunge `mode`);
  - le rotte del pannello;
  - `wake-sync`, che non fa nulla e risponde `awaiting_restore`.

  **Tutto il resto risponde `423 instance_awaiting_restore`**, compresi registrazione, primo account e `/auth/setup`.
- `POST /api/v1/backup/panel/jobs` in questo modo risponde **`409 backup_awaiting_restore`**: un backup vuoto non nasce mai.
  Nello stato «ripristino interrotto» (stato del ripristino illeggibile, D7) risponde **`409 backup_restore_interrupted`**,
  sempre dopo il controllo della credenziale.
- **Uscita** (domanda 5 approvata): la decide solo il coordinatore. Quando `restore.state = committed` toglie la variabile
  e riavvia. L'istanza non esce mai da sola.
- **Il blocco vince**: con `LIBREFOLIO_BLOCKED` acceso il ripristino non si applica (`restore.waiting = instance_blocked`).
- **R4 ⇄ cloud: ripristino di un'istanza bloccata.** Se il server di un'istanza bloccata sparisce, i suoi dati vanno
  comunque rimessi in piedi: nei 30 giorni del blocco l'admin deve poter scaricare il backup completo. In quel caso il
  coordinatore crea la macchina nuova con `LIBREFOLIO_AWAIT_RESTORE` acceso e `LIBREFOLIO_BLOCKED` **spento**. Il modo
  risponde comunque `423` a tutte le rotte dell'utente. A `committed` toglie `LIBREFOLIO_AWAIT_RESTORE`, rimette
  `LIBREFOLIO_BLOCKED` (con `LIBREFOLIO_DELETION_DATE` invariata) e riavvia una volta sola. Al prodotto chiediamo di
  confermare che in questo passaggio non si apre nessuna finestra in cui l'istanza è usabile senza blocco.

  **R4 ⇄ prodotto: confermato, a una condizione.** Le due variabili si leggono **a ogni chiamata**, in una dipendenza del
  router `/api/v1`: per il blocco è `refuse_when_blocked` in `instance_block.py`; per il modo sarà quella gemella di
  H-62. Nessuna rotta dell'utente risponde prima che quella dipendenza sia passata. Il passaggio, passo per passo:
  1. Macchina nuova, `AWAIT_RESTORE=1` e `BLOCKED` spento: ogni rotta dell'utente risponde `423 instance_awaiting_restore`.
  2. `confirm`, poi `restart`. Il processo riparte con le **stesse** variabili, applica il ripristino all'avvio
     (`pending-restore`, poi `restore-commit`) e arriva a `committed`. Le rotte rispondono ancora `423` (modo acceso).
     Un `rolled_back` resta anch'esso nel modo.
  3. Il coordinatore cambia **in un solo aggiornamento della macchina** `AWAIT_RESTORE` spento, `BLOCKED=1` e
     `DELETION_DATE` invariata. La macchina si riavvia una volta, e dalla prima richiesta il blocco risponde
     `423 instance_blocked`, con le eccezioni del blocco, cioè lo scarico del backup per l'admin.

  **La condizione è il passo 3, atomico.** Se si fa in due aggiornamenti (prima si toglie il modo, poi si rimette il
  blocco), fra i due riavvii l'istanza gira normale: **è proprio la finestra da evitare**.

  Sbagliare nell'altro verso è innocuo: con tutte e due le variabili accese tutto risponde `423`. In più
  `POST …/panel/jobs` risponde `409 backup_awaiting_restore` (nel modo) o `409 backup_restore_interrupted` (ripristino
  interrotto), quindi l'admin non scarica finché lo stato non si toglie.
  Non si aprono dati, si chiude soltanto troppo.

  **Test di H-62**: dopo un `committed`, un processo nuovo con `BLOCKED=1` e senza `AWAIT_RESTORE` risponde `423
  instance_blocked` già alla prima richiesta a una rotta dell'utente.
- **`GET /api/v1/panel/status`** (scopo `status`, domanda 6 approvata). Il coordinatore ignora le chiavi che non conosce.

```json
{
  "admin_setup": "none",
  "setup_expires_at": null,
  "mode": "awaiting_restore",
  "restore": {"state": "committed", "reason": null, "waiting": null, "backup_created_at": "2026-10-23T03:00:12Z", "stage_id": "…"}
}
```

  `mode` vale `normal` oppure `awaiting_restore`. `restore` è `null` solo quando non c'è nessun ripristino registrato,
  mai quando lo stato non si legge: allora `restore.state = "unreadable"` con la sua `reason` (D7).

  `users_used` e `users_limit` (H5-1, richiesta C5 del cloud, 23/10) sono solo conteggi, mai un nome, un'email o un id:
  `users_used` (intero ≥ 0) sono i posti occupati (account attivi, inviti ancora validi, account inattivi in attesa della
  verifica dell'email o della configurazione dell'amministratore iniziale, ognuno una volta), cioè ciò che limita
  `LIBREFOLIO_MAX_USERS`; `users_limit` (intero ≥ 1) è il valore di `LIBREFOLIO_MAX_USERS`, o `null` senza limite. Al
  limite, nuove registrazioni e nuovi inviti sono rifiutati.

## 7. La chiave d'istanza (decisione 39) ⇄

- **Precondizione del ripristino**: sulla macchina nuova il coordinatore imposta `LIBREFOLIO_INSTANCE_KEY` (la stessa
  della vecchia istanza) **prima** di caricare il backup. Senza, il rapporto di stage mostra `secrets_unreadable > 0` e
  il coordinatore **non conferma**.
- **Un job del pannello non porta mai la chiave d'istanza**, anche se LibreFolio l'ha generata e anche se il `.lfbk` ha
  una password: per il pannello si forza `instance_key=None`. Un test fissa `instance_key_included: false`.

## 8. CLI (self-hoster, assistenza, emergenza)

- **`./dev.py backup keygen --identity-file FILE`** scrive la privata nel formato di `age-keygen` (`# created:`,
  `# public key: age1…`, `AGE-SECRET-KEY-1…`), con permessi `0600` e mai sopra un file esistente. Poi stampa la pubblica.
- **`./dev.py backup create --sealed`** (legge la variabile) oppure **`--recipient age1…`** (ripetibile, fino a 2) crea un
  `.tar`.
- **`./dev.py backup inspect|decrypt|restore ARCHIVIO.tar --identity-file FILE`** applica le regole del §3.5, apre
  `password.age` e prosegue come per un `.lfbk` con la sua password. Accetta anche un file di `age-keygen`.
- **Emergenza senza LibreFolio funzionante**:
  1. `tar xf ARCHIVIO.tar`;
  2. `age -d -i chiave.txt password.age`;
  3. `./dev.py backup restore backup.lfbk --password-file …`.

## 9. Vettori di prova comuni ⇄

`age` cifra con dati casuali, quindi **non ci sono vettori byte per byte della cifratura**: ci sono vettori di
decifratura su file fissati una volta. I file stanno in `backend/test_scripts/fixtures/backup_l3/` (⇄ prodotto: la cartella dei fixture del repo) e si
copiano tali e quali nel repo del coordinatore. Ogni chiave è marcata **TEST ONLY**.

### 9.1 Lato prodotto (li scrive B)

Uno script li genera con `pyrage`, `envelope.encrypt_file` e `tarfile`, e **li salva una sola volta**.

| File | Cosa |
|---|---|
| `vectors.json` | l'indice: per ogni caso il file, l'esito atteso e i valori attesi |
| `test-identity-1.txt`, `test-identity-2.txt` | due coppie di prova (formato `age-keygen`): la seconda serve per la rotazione |
| `librefolio-backup-20261023-030012.tar` | il caso buono: un solo destinatario, la password nota, un `.lfbk` di uno zip minimo noto (`salt` e `nonce_prefix` fissi), `mtime` = `1792724412`. Attesi: la password, lo `sha256` del `.tar`, il manifest, `lfbk_sha256`, il `check` dell'intestazione, lo `sha256` dello zip decifrato |
| `rotation-two-recipients.tar` | la password cifrata per tutte e due le chiavi: si apre con ciascuna |
| `neg-other-recipient.tar` | la password cifrata per un'altra chiave: nessuna corrispondenza |
| `neg-wrong-password.tar` | la password si apre ma non apre il `.lfbk` (il `check` non torna): `wrong_password` |
| `neg-manifest-mismatch.tar` | `lfbk_sha256` del manifest diverso dal membro |
| `neg-extra-member.tar`, `neg-bad-order.tar`, `neg-traversal.tar`, `neg-symlink.tar` | violano le regole del §3.5 |
| `neg-tampered-lfbk.tar` | un byte cambiato in un blocco: `envelope_damaged` al ripristino |

**Il prodotto prova**:
- ricostruisce il `.tar` buono dagli stessi membri e ottiene gli stessi byte;
- ripristina il `.lfbk` con la password;
- fa il round trip completo con `api backup-roundtrip` esteso (B5).

**Il coordinatore prova**:
- la lettura con le regole del §3.5;
- `pyrage.decrypt(data, [Identity.from_str(…)])`, che deve dare la password attesa;
- il controllo del manifest;
- il `check` del `.lfbk`, sempre: §3.5.1 ⇄ prodotto, allineato a R2;
- lo `sha256`.

### 9.2 Controllo incrociato con `age` (una volta, a mano)

Il developer apre `password.age` dei vettori con il comando `age` di riferimento (Go):
`age -d -i test-identity-1.txt password.age`. L'esito si annota qui. Nella suite automatica non c'è il binario `age`.

### 9.3 Lato coordinatore (lo scrive il cloud)

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

## 10. Punti aperti

- **D1** (developer o cloud): profilo `managed` senza `LIBREFOLIO_BACKUP_RECIPIENTS`. Il prodotto propone
  **`503 backup_panel_unavailable`**, cioè mai uno zip in chiaro dal pannello di un'istanza gestita. L'alternativa è lo
  zip in chiaro come oggi. **Cloud ⇄: d'accordo con il `503`.** Il coordinatore imposta sempre la variabile dalla
  creazione dell'istanza, quindi un `503` vuol dire un errore di configurazione, e un backup in chiaro andrebbe contro la
  scelta K2. **Deciso dal developer il 22/10: `503`.**
- **D2** (H con il cloud): la rotta di ripristino accetta **solo un `.lfbk`** (`restore_envelope_required`)?
  Il prodotto propone di sì. **Cloud ⇄: sì**, il coordinatore manda sempre e solo il membro `backup.lfbk`.
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
- **D4** (cloud e prodotto): `pyrage` fissato a **1.4.0** sui due lati. **Cloud ⇄: d'accordo** sul piano tecnico: il
  coordinatore lo usa solo per aprire `password.age`. **Approvato dal developer il 22/10** anche come dipendenza del
  coordinatore.
- **D5** (cloud): il default di `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` nel managed (500?) e lo spazio sul volume
  durante uno stage (busta caricata + zip decifrato + copia scompattata). Si decide con lo spike. **Cloud ⇄:**
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

  **Deciso il 22/10** (coordinatore della 1.3, a nome del developer): `500` provvisori, più il controllo dello spazio del
  coordinatore prima del caricamento.

- **D6 — confermata dal developer il 23/10** (H-3 nel managed, posizione del cloud del 22/10; si realizza con H-3):
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
  - con la chiave che non corrisponde l'istanza non serve i dati; `GET /api/v1/panel/status` risponde comunque, con
    `instance_key: "ok" | "mismatch"` (mai l'impronta);
  - i job di backup del pannello sono rifiutati con un `409` (una copia fatta con la chiave sbagliata passerebbe i
    controlli del cloud e spingerebbe fuori una copia buona delle 7 tenute);
  - `wake-sync` non fa nulla e risponde con lo stato, come per un'istanza bloccata;
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
- **D7 — confermata dal developer il 23/10, opzione A — FATTA** (H, ramo `e-alfy-h-piattaforma`, entra con il treno 10) (B-33 nel managed, posizione del cloud del 22/10):
  - con lo stato del ripristino illeggibile l'istanza non serve i dati; `panel/status` riporta
    `restore.state = "unreadable"`; i job di backup del pannello sono rifiutati come in D6;
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
  - la scelta si fa a mano con l'admin: chiudere o annullare il ripristino con gli strumenti dell'istanza, oppure rimettere
    l'ultima copia notturna con la catena di D5, avviata a mano.
  - Con `LIBREFOLIO_SUPPORT_URL` impostata, la pagina dell'istanza ferma (D6 e D7) mostra il link «Scrivi all'assistenza»
    (developer, 23/10).

## Registro

- 22/10/2026, B: bozza 1, lato prodotto.
- 22/10/2026, B: bozza 2, con le richieste 1-8 del coordinatore cloud. Cambiamenti:
  - `manifest.json` diventa il primo membro, con i file piccoli davanti;
  - `LIBREFOLIO_BACKUP_RECIPIENTS` con 1-2 destinatari al posto della chiave unica;
  - niente `kid`: al suo posto `sealed_recipients`;
  - `file_size` e `file_sha256` fissati;
  - forma a due passi motivata;
  - tabella della ripetibilità;
  - precondizione sulla chiave d'istanza;
  - vettori di decifratura e rotazione.
- 22/10/2026, cloud: revisione della bozza 2, con le richieste R1-R4 e le posizioni su D1-D5, tutte segnate «⇄ cloud».
  - **R1**: il rapporto dello stage visto dal pannello è senza dati del portafoglio e senza dati personali.
  - **R2**: disposizione dell'intestazione del `.lfbk` e formula del `check`; il coordinatore controlla sempre il `check`.
  - **R3**: il biglietto si verifica all'inizio del caricamento.
  - **R4**: ripristino di un'istanza bloccata.
- 22/10/2026, B: bozza 3, con le risposte del prodotto, segnate «⇄ prodotto».
  - **R1**: accolta. Lo schema del pannello è chiuso; il verdetto `control_totals` esiste già; via `administrators`,
    le differenze, `tables`, le dimensioni e lo username in `confirmed_by`.
  - **R2**: §3.5.1, con la tabella dei 52 byte, la formula del `check` e l'avviso su `hashlib.scrypt`.
  - **R3**: già così per costruzione; test.
  - **R4**: confermato, a patto che il cambio di variabili sia un solo aggiornamento della macchina; test.
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
  - **§3.5 punto 2**: accetta anche i destinatari ancora validi dopo una rotazione.
- 22/10/2026, cloud: risposte R1-R4 accettate, compresa la condizione di R4 (un solo aggiornamento della macchina).
  Con il via del developer: **CONCORDATO** lato cloud, D1 = `503`, D4 = `pyrage` 1.4.0 nel coordinatore. D5 resta
  allo spike.
- 22/10/2026, cloud: D5 = 500 MB provvisori con il controllo dello spazio del coordinatore (deciso dal coordinatore della
  1.3); numeri definitivi dallo spike. Q4 resta del developer: niente `age` nei test automatici, vettori aperti a mano una volta.
- 22/10/2026, B: vettori del §9.1 generati (`backend/test_scripts/fixtures/backup_l3/`, 10 casi più `cloud_derivation`
  in `vectors.json`, generatore `generate_vectors.py`); cartella spostata da `test_services/fixtures/` alla cartella dei
  fixture del repo, nessun altro cambiamento. Con `pyrage` 1.4.0, `Identity.from_str(…).to_public()` dà i tre `age1…` del
  §9.3: **3/3**. Codici attesi dei negativi, lato prodotto: `sealed_tar_invalid`, `sealed_manifest_invalid`,
  `sealed_no_identity`, `wrong_password`, `envelope_damaged` (il cloud li mappa sui suoi).
- 22/10/2026, B: §9.2 fatto con il comando `age` 1.3.2 del developer. `age -d -i test-identity-1.txt` apre la
  `password.age` del caso buono; `-i test-identity-2.txt` apre quella di `rotation-two-recipients.tar`. Entrambe danno
  la password di `vectors.json`.


- 22/10/2026, B (domande K del cloud): lettura di testa = 10 240 byte (un record tar); chiavi sconosciute del manifest
  rifiutate (un campo nuovo = `version` 2); il manifest si confronta per contenuto, non per byte; ogni lato sceglie il
  suo lettore tar, con le stesse regole e senza intestazioni PAX/GNU. Vettori: cartella definitiva
  `backend/test_scripts/fixtures/backup_l3/`, commit a cura del coordinatore della 1.3 (proposto nel CP1 di B).
- 22/10/2026, B (CP2): il lettore del prodotto è suo, non `tarfile` (scrive con `tarfile`, legge le intestazioni ustar a
  mano: magic `ustar\0` + `00`, checksum, solo tipo `0`, nessun prefisso). Stesse regole del §3.5.
- 22/10/2026, coordinatore 1.3: scarico `…/jobs/{job_id}/file` (non `…/download`), allineato al codice; D6 e D7 come proposte del cloud.
- 22/10/2026, B (revisione della doc B4): le fasi del §4 sono quelle del codice. Picco di spazio: lo zip in chiaro ora
  si toglie appena la busta è scritta, prima del sigillo, quindi il picco resta 2× la busta come dice il §4 (prima, per
  un difetto, c'erano zip, `.lfbk` e `.tar` insieme). Codici del lettore in più rispetto al §9.1: `sealed_password_invalid`
  e `sealed_identity_invalid` (lato CLI del prodotto); `db_revision` del manifest può essere `null` (un archivio senza
  revisione Alembic).
- 22/10/2026, B (revisione di sicurezza, punto 2): il lettore del prodotto chiede, dopo i tre membri, **due blocchi di
  zeri e poi solo zeri fino alla fine del file** (prima si fermava al primo blocco di zeri: un quarto membro nascosto o
  byte in coda passavano, e `tar -i` del §8 estrarrebbe il membro nascosto). Regola del §3.5 per tutti e due i lati.
  Due vettori negativi in più, entrambi `sealed_tar_invalid`, aggiunti con `generate_vectors.py --extend` senza toccare
  i file già copiati: `neg-hidden-member.tar` (sha256 `f6d0ea27…6f1fa`) e `neg-trailing-garbage.tar` (`cb6e3277…ffdb02`);
  `vectors.json` cambia (nuovo sha256 dopo il commit). Il cloud li copia dopo il commit del coordinatore della 1.3.
- 23/10/2026, coordinatore 1.3: D6 e D7 confermate dal developer (D7 opzione A, tolta l'alternativa con il freno); link all'assistenza sulla pagina dell'istanza ferma.
- 23/10/2026, coordinatore 1.3: D7 nel codice (H): `panel/status` con `restore.state = "unreadable"`, `409 backup_restore_interrupted` sui job del pannello, `reason` nel 500 delle rotte di ripristino.
- 23/10/2026, coordinatore 1.3: `users_used` e `users_limit` in `panel/status` (H5-1).
