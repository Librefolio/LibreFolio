# Piano — fase 00, 34: la cancellazione dell'account e gli id che si riusano

> **Stato**: ✅ approvato dal developer (2026-10-08), in esecuzione. Le varianti sono in §0.1.
>
> - Mandato: coordinatore («Release 2 backlog analysis», `c8328a01-…`), con le decisioni del developer (§0).
> - Workstream L. Ramo `e-alfy-l-danske-bank`, base `9d79c2dbe` (`dev_release2`, treno 10), worktree pulito.
> - Corsia 6156/6166, `--data-dir /tmp/librefolio-r2-l`, un comando alla volta.
> - Nasce dall'analisi del piano 33 (§1.1): difetti A e B.

## 0. Il mandato (decisioni del developer, dal coordinatore)

**A — cancellazione dell'account.**
- Testuale: «applichiamo la regola dell'ultimo owner già nella 1.2», a livello applicativo, con «una sola funzione condivisa» del service.
- La stessa funzione serve l'uscita da un broker e la cancellazione dell'account.
- I file si puliscono dopo il commit.
- Test API rosso prima della correzione.

**B — id riusati.** Niente b2. Testuale: «è un bug che ancora nessuno ha mai vissuto… ignoriamolo, lo stiamo risolvendo alla radice». Al suo posto:
1. **`001_initial.py`**: AUTOINCREMENT sulle tabelle i cui id escono dal backend e restano salvati.
   - `brokers`, `assets` e quelle del censimento chiesto dalla voce di `TODO_FUTURI.md` (transazioni, utenti, coppie FX…).
   - Fuori le serie ad alto volume (prezzi, cambi).
   - È un'eccezione alla regola della 001 decisa dal developer, e **non va scritta** in wiki, skill o istruzioni: resta solo in questo piano.
2. **I modelli** dichiarano `sqlite_autoincrement=True`: tre suite usano `create_all`.
3. **Un test di schema**: dopo `alembic upgrade head`, quelle tabelle hanno AUTOINCREMENT. SQLAlchemy 2.0.52 non lo rilegge dal DB, quindi una futura migrazione batch lo perderebbe.
4. **Un sottosistema nuovo di fix post-migrazione.**
   - Testuale: «fix post migration che si attivano in ordine alla fine, cercano le anomalie che correggono e se le trovano, le applicano».
   - Il primo fix converte le tabelle del punto 1 nei DB esistenti.
   - Regole approvate:
     - un modulo, due ingressi: l'avvio del server e uno script offline, a server spento, anche dentro l'immagine Docker;
     - una connessione SQLite diretta, con le FK spente fuori dalla transazione;
     - prima un `integrity_check`;
     - una copia di backup, fatta dopo aver svuotato il WAL: resta, e il log ne riporta il percorso;
     - una sola transazione, con `foreign_key_check` e conteggi di righe identici prima e dopo;
     - a ogni errore rollback, un avviso e avvio normale: l'avvio non si blocca mai;
     - idempotente.
   - Test:
     - un DB nuovo resta invariato;
     - un DB con lo schema della 1.1, popolato, viene convertito, con dati identici e id mai più riusati;
     - un errore provocato lascia il DB intatto e il server parte;
     - lo script offline funziona.
5. **Guida admin** in inglese, col docs-writer. La riga di CHANGELOG la scrive il coordinatore.
6. A fine lotto si chiude la voce di `TODO_FUTURI.md` (`:2219`) col link a questo piano.

### 0.1 L'approvazione (2026-10-08, dal coordinatore)

Il developer: «mi torna tutto». Le varianti, con le sue parole dove servono:
- **D1 — approvato** il censimento di §1.2: «bella pensata farlo anche alle altre tabelle».
  - In più un test con uno schema «futuro», per esempio una colonna aggiunta da una migrazione successiva. Deve provare che il fix lavora sul DDL corrente a qualunque `head`, non solo alla `004`. L'ha chiesto esplicitamente.
- **D2**: «se la migrazione va bene penso si possa cancellare». Il backup si cancella dopo un fix verificato; resta solo se qualcosa fallisce, col percorso nel log.
- **D3 — ok.** Il fix lo chiama l'avvio del backend dopo `alembic upgrade head`, quindi vale per `dev.py server`, Docker e ogni altro avvio. `dev.py` non cambia; lo script offline è `python -m backend.app.db.post_migration`.
- **D4**: «se un broker prima aveva id 3, deve averlo anche dopo id 3, se al momento della migrazione ci sono delle cartelle broker_id già orfane, lo script prima le rinomina e se tutto va bene, le cancella».
  - Gli id restano identici.
  - Le cartelle `broker_<id>` il cui id non esiste in `brokers` si rinominano nello stesso genitore, con un nome di quarantena: il rename è atomico.
  - Dopo il fix verificato si cancellano; se il fix fallisce tornano al loro nome.
  - Tutto finisce nel log e nel `--dry-run`.
  - Si chiude così anche il caso del broker con l'id più alto, cancellato prima della conversione.
- **D5**: «si buona idea».
- **D6**: «ci sta stoppare la delete se il db non risponde o se si è l'unico amministratore dell'istanza, quelle sono regole di prodotto e quindi giuste».
  - Tutto o niente solo per un errore tecnico; resta il rifiuto dell'unico amministratore.
  - I trasferimenti fra un broker che sparisce e uno che resta li copre già `delete_by_broker` (`transaction_service.py:320`): scollega la metà rimasta (`related_transaction_id = NULL`), e il suo costo resta su `cost_basis_override`. Va nel test API.

Ordine: il piano aggiornato, i rossi col test-author, il codice, la guida admin col docs-writer. La riga di CHANGELOG la scrive il coordinatore; al checkpoint gli mando, in una frase, cosa vede l'utente.

## 1. Stato verificato (codice a `9d79c2dbe`)

### 1.1 A — la cancellazione dell'account

- `DELETE /auth/users/me` (`auth.py:~276-305`, `delete_own_account`) chiama `user_service.delete_user` (`:333-357`), che fa solo `session.delete(user)` e `commit`.
- A livello di DB, `broker_user_access.user_id` va in `ON DELETE CASCADE` (`001_initial.py:148-162`), ma `brokers` non ha una FK verso `users`.
- Risultato: i broker di cui l'utente era l'unico owner restano senza proprietario, con le loro transazioni e i file BRIM.
- Le docstring dicono il contrario: `auth.py` «Deletes all user data (brokers, transactions, settings)»; `delete_user` «cascades to all brokers owned by the user, all transactions».
- **La regola esiste già, in un solo posto**: `BrokerService.leave_broker` (`broker_service.py:879-913`).
  - EDITOR/VIEWER: sempre;
  - OWNER: se resta un altro owner;
  - l'**ultimo owner** cancella il broker con le sue transazioni (`delete_bulk([…force=True])`), cioè la semantica F4.
- La usa solo `DELETE /brokers/{id}/access/me` (`brokers.py:541-567`), che pulisce i file **dopo il commit** con `_delete_brim_files_for_brokers` (`brokers.py:103`), lo stesso helper della cancellazione in blocco (`:415`).
- Nessun altro percorso cancella utenti: `delete_user` si chiama solo da `auth.py:300` e dai test (`test_user_profile.py:244-271`; `test_broker_access_api.py:696-714`, `cleanup_owned_user_account`).

### 1.2 B — lo schema e il censimento degli id

**Lo schema reale** (DB migrato a `004`, letto in sola lettura):
- 14 tabelle di dati, nessun trigger, nessuna vista.
- Le 12 di `001` sono SQL scritto a mano, con `id INTEGER PRIMARY KEY` a livello di colonna.
- Le 2 di onboarding (`004`, `op.create_table`) hanno `id INTEGER NOT NULL … PRIMARY KEY (id)` a livello di tabella.
- `global_settings` ha come chiave `key VARCHAR(100)`, quindi non c'entra.
- `002`–`004` non ricostruiscono tabelle: usano `ALTER TABLE … ADD/DROP COLUMN` nativi, che conservano AUTOINCREMENT. Basta quindi la `001` per i DB nuovi.

**Le installazioni esistenti**:
- la 1.1 (tag `v1.1.0`) ha `001`, `002` e `5b1333fa6b07` (oggi `003_scheduler_timezone.py`, stesso id): all'avvio sale a `004_release_1_2_0_schema`;
- dalla 1.1 la `001` è cambiata solo in due `VARCHAR(14)→(32)` (`assets.asset_type`, `transactions.type`), che SQLite non applica: il fix conserva il DDL che trova.

**Riferimenti e indici delle tabelle candidate** (una ricostruzione deve ricreare gli indici e non toccare le righe che le puntano):

| Tabella | Indici espliciti | Referenziata da |
|---|---|---|
| `users` | 2 | `user_settings`, `broker_user_access`, `user_onboarding_*` (CASCADE); `global_settings` (SET NULL) |
| `brokers` | 1 | `broker_user_access` (CASCADE); `transactions` (NO ACTION) |
| `assets` | 3 | `asset_provider_assignments`, `price_history`, `asset_events` (CASCADE); `transactions` (NO ACTION) |
| `transactions` | 7 | se stessa, `related_transaction_id` (NO ACTION) |
| `fx_conversion_routes` | 3 | — |
| `asset_events` | 3 | `transactions.asset_event_id` (RESTRICT) |

Con le FK accese, ricostruire `users` o `assets` cancellerebbe in cascata le righe che li puntano, o fallirebbe sulle transazioni: lo dice già la voce di `TODO_FUTURI`, verificata il 01/10. Da qui le FK spente e la connessione diretta, fuori da Alembic, che importa il listener di `session.py:20`.

**Dove escono gli id e dove restano salvati**:
- **URL**: `/assets/[id]`, `/brokers/[id]`. `/fx/[pair]` usa i codici delle valute, non un id.
- **localStorage**:
  - il benchmark del rischio (`riskBenchmarkStore`, un id di asset);
  - gli asset di confronto dei grafici (`chartSettingsStore`);
  - la selezione del laboratorio Asset Global (D19);
  - lo stato salvato del wizard d'import (broker e asset).

  L'event picker salva solo un numero di giorni.
- **File**:
  - i sidecar BRIM (`target_broker_id`, l'utente che ha caricato il file) e le cartelle `broker_<id>`;
  - gli export di backup (`backup.py`: id di asset nei metadati, filtri per broker).
- Nessun id di route FX viene salvato dal client.

**Proposta di censimento** (D1):

| Tabella | Volume | L'id esce e resta salvato | AUTOINCREMENT |
|---|---|---|---|
| `users` | basso | sidecar BRIM, condivisione dei broker | ✅ |
| `brokers` | basso | URL, cartelle su disco, sidecar, wizard | ✅ |
| `assets` | basso | URL, benchmark, confronti, selezioni, export | ✅ |
| `transactions` | medio | API ed export; si cancellano spesso | ✅ (in elenco del developer) |
| `fx_conversion_routes` | basso | API («coppie FX») | ✅ (in elenco del developer) |
| `asset_events` | basso | API; le transazioni le collegano | ✅ **proposta mia** (D1) |
| `asset_provider_assignments`, `broker_user_access`, `user_settings`, `user_onboarding_progress`, `user_onboarding_step_progress` | basso | restano dentro il backend | ❌ |
| `price_history`, `fx_rates` | alto | — | ❌ (serie, come da decisione) |

**Altro**:
- L'avvio: `ensure_database_exists()` (`main.py:99-212`, chiamata a `:264` nel `lifespan`) esegue `alembic upgrade head` solo quando serve.
- Docker: l'immagine contiene `backend/`, `scripts/` e `dev.py`, in `WORKDIR /app`. `entrypoint.sh` finisce con `exec "$@"` (`gosu` se parte da root), quindi un comando dato al container sostituisce il server.
- La doc admin ha già due posti adatti: `cli_tools.en.md` («Database Migrations») e `docker_advanced.en.md` («`docker exec`», «Database Backup», con la nota sul WAL).

## 2. Il disegno

### 2.1 A — una funzione condivisa

- La funzione condivisa è **`BrokerService.leave_broker`**: è già l'unica implementazione della regola, e la sua semantica non cambia.
- `user_service.delete_user(session, user_id)`:
  - per ogni accesso dell'utente, in ordine di `broker_id`, chiama `leave_broker(broker_id, user_id)`;
  - poi cancella l'utente e fa il **commit**;
  - restituisce gli id dei broker cancellati, quindi la firma cambia;
  - se una cancellazione fallisce per un errore tecnico, non fa nulla, con un rollback (D6, tutto o niente). Le regole di prodotto restano come sono: l'unico amministratore non può cancellarsi (`auth.py`).
- `delete_own_account` (`auth.py`), dopo il commit, pulisce i file di quei broker.
- I trasferimenti fra un broker che sparisce e uno che resta: `delete_by_broker` scollega già la metà rimasta (`related_transaction_id = NULL`), e il suo `cost_basis_override` non cambia. Non si tocca; lo fissa il test API.
- L'helper dei file passa da `api/v1/brokers.py` a `services/brim_provider.py` come `delete_files_for_brokers(broker_ids) -> int`, senza cambiarne il comportamento. Lo usano i suoi due chiamanti di oggi e `auth.py`.
- Le docstring diventano vere.

### 2.2 B1–B3 — lo schema

- **`001_initial.py`**: `AUTOINCREMENT` sulla colonna `id` delle tabelle del censimento (D1). È l'eccezione decisa dal developer, scritta solo qui.
- **Modelli**: `__table_args__` con `{"sqlite_autoincrement": True}` sulle stesse tabelle, unito ai vincoli che ci sono già.
- **Test di schema**:
  - un DB nuovo (`alembic upgrade head`) ha AUTOINCREMENT su quelle tabelle e su **nessun'altra**, così il censimento resta fissato;
  - i modelli lo dichiarano sulle stesse tabelle;
  - `create_all` lo produce.

### 2.3 B4 — i fix post-migrazione

**Il modulo**: `backend/app/db/post_migration/`
- `__init__.py`: il registro ordinato e `run_post_migration_fixes(db_path) -> Report`;
- `autoincrement.py`: il primo fix;
- `__main__.py`: lo script offline, `python -m backend.app.db.post_migration [--db PATH] [--dry-run]` (D3, D5).

**Il contratto di un fix**: `id`, `detect(conn) -> anomalia | None`, `apply(conn, anomalia)`, `verify(conn, prima) -> errori`.

**Il percorso** (connessione `sqlite3` diretta, `isolation_level=None`; nessun listener di SQLAlchemy):
0. **Un'esecuzione alla volta** (aggiunto dopo la review, §10.6): un lock esclusivo e bloccante (`fcntl.flock`) su `<nome del DB>.post-migration.lock`, accanto al DB. Si prende prima di aprire il DB e si tiene fino alla pulizia, anche nel dry-run. Il file resta su disco.
1. `PRAGMA integrity_check`: se non è `ok`, un avviso e nessun fix.
2. `detect` di tutti i fix, in ordine. Se non c'è niente, si esce senza scrivere niente, backup compreso.
3. `PRAGMA wal_checkpoint(TRUNCATE)`, poi la **copia di backup** con l'API di backup di SQLite, accanto al DB: `app.db.pre-<id-fix>-<UTC aaaammggThhmmss>.bak`. Se la copia non riesce, nessun fix.
4. Per ogni fix con un'anomalia:
   - `PRAGMA foreign_keys=OFF` **fuori** dalla transazione;
   - `BEGIN IMMEDIATE`;
   - `apply`;
   - `verify`: `PRAGMA foreign_key_check` vuoto, conteggi di righe identici su **tutte** le tabelle, anomalia sparita;
   - `COMMIT`; `PRAGMA foreign_keys=ON`.
5. **Tutto verificato**: il backup **si cancella** (D2).
6. A ogni eccezione: `ROLLBACK`, `foreign_keys=ON`, e il backup **resta**; un avviso nel log col fix, l'errore e il percorso del backup. Il report dice `failed`, e l'avvio continua.

**Il report** (contratto per i test):
- `run_post_migration_fixes(db_path, data_dir=None, *, dry_run=False) -> PostMigrationReport`;
- `PostMigrationReport.outcomes: dict[str, str]`: per ogni fix `clean`, `applied`, `would_apply` (dry-run) o `failed`;
- `integrity_ok: bool`;
- `backup_path`: il backup che **resta**, cioè `None` quando non serviva o quando è stato cancellato dopo il successo;
- `orphan_broker_dirs`: le cartelle orfane trovate, in percorsi relativi alla data-dir;
- `errors: list[str]`.

**Il fix «autoincrement»**:
- *Rilevamento*: per ogni tabella del censimento presente, il `sql` di `sqlite_master` non contiene `AUTOINCREMENT`.
- *Correzione*, la ricostruzione ufficiale di SQLite, tabella per tabella, dentro la stessa transazione (in corso d'opera è diventata un'altra: §10.3, Fuori pista):
  - il DDL nuovo è **quello corrente**, letto da `sqlite_master` a qualunque `head`, cambiato in un punto solo: `id INTEGER PRIMARY KEY` → `… AUTOINCREMENT`, col nome provvisorio `<t>__autoinc`;
  - una forma diversa (zero o più corrispondenze, o una PK di tabella) **ferma** il fix con un avviso: mai un'ipotesi;
  - poi `INSERT INTO <t>__autoinc SELECT * FROM <t>`, `DROP TABLE <t>`, `ALTER TABLE <t>__autoinc RENAME TO <t>`, e gli indici ricreati dal loro `sql` salvato prima.
- *Gli id* restano identici: la copia li porta con sé, e dopo SQLite scrive in `sqlite_sequence` il massimo id, così da lì un id non torna più.
- *Le cartelle orfane* (D4), quando c'è da convertire `brokers` e la data-dir è nota:
  - quali: `broker_reports/{uploaded,parsed,failed}/broker_<n>`, con `<n>` intero e assente da `brokers`. `broker_none` e i nomi non numerici non contano;
  - **prima** della transazione si rinominano nello stesso genitore in `.quarantine-autoincrement-<UTC>-broker_<n>`: un rename atomico, che la lista dei file (`glob("broker_*")`) non vede più;
  - dopo il fix verificato si cancellano; se il fix fallisce, ognuna torna al suo nome;
  - in `--dry-run` si elencano soltanto;
  - guardia: si toccano solo se il DB, risolto, sta sotto la data-dir risolta (la stessa regola di `reset_broker_reports`); altrimenti un avviso, e il fix continua sul DB.
- *Verifica*: oltre ai controlli comuni, gli indici e il DDL di ogni tabella sono uguali a prima, salvo `AUTOINCREMENT`.

**I due ingressi**:
- l'avvio: nel `lifespan`, subito dopo `ensure_database_exists()` (`main.py:264`), prima di ogni altra connessione, con `get_data_dir()` come data-dir, dentro un `try/except` che non rilancia mai;
- lo script offline, `python -m backend.app.db.post_migration [--db PATH] [--data-dir PATH] [--dry-run]`:
  - DB e data-dir presi dalle impostazioni, come fa il server, a meno che li si dia;
  - stampa cosa ha trovato e cosa ha fatto;
  - esce con 0 se non c'era niente da fare, se tutto è andato bene o col `--dry-run`, con 1 se un fix è fallito (il DB resta com'era e il backup rimane).

### 2.4 B5 — doc (docs-writer, solo EN, niente stamp)

- `docker_advanced.en.md`:
  - la correzione automatica all'avvio: cosa fa, dov'è il backup, cosa dice il log;
  - lo script a server spento: fermare il servizio, `docker compose run --rm <servizio> python -m backend.app.db.post_migration`, riavviare.
- `cli_tools.en.md`: lo stesso per l'installazione su host (`pipenv run python -m …`).
- IT/FR/ES restano debito di traduzione.

## 3. Superfici

| File | Cosa |
|---|---|
| `backend/app/services/user_service.py`, `backend/app/api/v1/auth.py` | A |
| `backend/app/services/broker_service.py` | A: solo docstring, se serve; la regola resta com'è |
| `backend/app/api/v1/brokers.py`, `backend/app/services/brim_provider.py` | A: l'helper dei file nel service, i due chiamanti aggiornati |
| `backend/alembic/versions/001_initial.py` | B1, l'eccezione decisa |
| `backend/app/db/models.py` | B2 |
| `backend/app/db/post_migration/` (nuovo) | B4 |
| `backend/app/main.py` | B4: il gancio d'avvio |
| test nuovi (test-author), una fixture DDL della 1.1, le voci del runner (solo le mie) | §7 |
| `mkdocs_src/docs/admin/docker_advanced.en.md`, `cli_tools.en.md` | B5, docs-writer |
| `mkdocs_src/docs/user/settings/profile.en.md` | A, docs-writer: «Delete Account» allineata (§10.5) |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | A, decisione (a): il testo di 2 chiavi esistenti (§10.6) |
| `TODO_FUTURI.md`, `TODO_Completati.md` | la chiusura della voce `:2219` |
| questo piano | — |

Nessuna API cambia forma, nessuna migrazione nuova (si modifica la `001`), nessuna chiave i18n nuova: cambia solo il testo di 2 chiavi esistenti.

## 4. Decisioni (✅ tutte prese, 2026-10-08; le parole del developer sono in §0.1)

- **D1** ✅ il censimento proposto, `asset_events` compreso, più il test con lo schema «futuro».
- **D2** ✅ il backup si cancella dopo un fix verificato; resta, col percorso nel log e nel report, se qualcosa fallisce.
- **D3** ✅ solo `python -m backend.app.db.post_migration`; il gancio è all'avvio del backend. `dev.py` non cambia.
- **D4** ✅ gli id restano identici; le cartelle orfane vanno in quarantena e poi si cancellano, o tornano al loro nome se il fix fallisce (§2.3).
- **D5** ✅ `--dry-run`.
- **D6** ✅ tutto o niente per un errore tecnico; il rifiuto dell'unico amministratore resta; la metà rimasta di un trasferimento è nel test API.

## 5. Rischi

1. Si riscrive il DB di un utente all'avvio. Le difese: `integrity_check` prima, backup, una transazione, verifiche, rollback, avvio mai bloccato.
2. **Spazio su disco**: il backup raddoppia il DB per un momento. Se la copia fallisce, il fix non parte.
3. **Durata**: `transactions` e `assets` si copiano riga per riga; su DB grandi l'avvio rallenta una volta sola. Il log dice quanto ci ha messo.
4. **Forme di DDL inattese** su DB modificati a mano: il fix si ferma con un avviso, e lo script offline lo racconta.
5. **Un'altra connessione aperta durante l'avvio**: `BEGIN IMMEDIATE` aspetta il `busy_timeout`, poi rinuncia. Rollback, avviso, avvio.
6. A: un utente con molti broker cancella molte cose in una volta. È la semantica F4, applicata per broker, ed è voluta.
7. **Più worker che partono insieme** (trovato in review dal docs-writer, §10.6). Ogni worker lancia i fix. Senza lock, il secondo ha già visto le tabelle da convertire e le trova convertite: riporta `failed` e tiene un backup di un DB sano. Cura: il lock del passo 0 di §2.3.

## 6. Passi, dopo il via

1. Il piano rivisto; lo SHA di partenza.
2. **A**: il rosso API (test-author), poi la cura, poi i gate API.
3. **B1–B3**: il rosso dello schema (test-author), poi `001` e i modelli; le tre suite con `create_all`.
4. **B4**:
   - la fixture DDL della 1.1, generata una volta dalle migrazioni di `v1.1.0` in una cartella temporanea, con il comando scritto nella fixture;
   - i rossi del sottosistema (test-author);
   - la cura;
   - la prova a mano dello script offline su una copia del DB della corsia.
5. **B5**: doc (docs-writer).
6. `TODO_FUTURI.md` chiusa; gate; checkpoint con le righe di CHANGELOG proposte.

## 7. Test, rossi prima (test-author)

- **A, API**. A e B sono utenti; i broker:
  - X: unico owner A, con una transazione e un file;
  - Y: owner A e B;
  - Z: owner A, editor B;
  - W: owner B, viewer A;
  - un trasferimento fra X (che sparisce) e un broker di B (che resta), con un `cost_basis_override` sulla metà di B.

  Quando A cancella l'account:
  - X e Z spariscono, con le transazioni e i file (404);
  - Y e W restano, con B;
  - nessun accesso di A resta;
  - la metà del trasferimento nel broker di B esiste ancora, con `related_transaction_id` NULL e `cost_basis_override` invariato.

  In più:
  - l'unico amministratore resta rifiutato come oggi (guardia);
  - un errore tecnico a metà cancella niente.

  Si adegua `test_user_profile.py`, per la firma nuova.
- **Schema**: un DB nuovo ha AUTOINCREMENT esattamente sul censimento; i modelli e `create_all` coincidono.
- **Fix**:
  - un DB nuovo: nessuna anomalia, niente scritto, nessun backup;
  - un DB 1.1 popolato, poi `upgrade head`, poi il fix:
    - dati identici tabella per tabella; gli **id identici**;
    - indici e DDL uguali, salvo AUTOINCREMENT;
    - FK pulite;
    - `sqlite_sequence` al massimo;
    - cancellata l'ultima riga, la nuova prende un id più alto;
    - **il backup non c'è più** (D2);
  - **lo schema «futuro»** (D1, richiesta esplicita del developer): sul DB a `head`, una migrazione finta aggiunge una colonna e un indice a una tabella del censimento, con delle righe che la usano. Il fix converte usando il DDL corrente: la colonna, i suoi valori e l'indice restano, e c'è AUTOINCREMENT;
  - **le cartelle orfane** (D4):
    - `broker_<n>` senza broker in quarantena e poi cancellate, mentre le cartelle dei broker vivi, `broker_none` e i nomi non numerici restano;
    - se il fix fallisce, ogni cartella torna al suo nome;
    - il dry-run le elenca senza toccarle;
    - con il DB fuori dalla data-dir, nessuna cartella toccata;
  - la seconda esecuzione non fa niente;
  - un errore provocato a metà: DB identico a prima, **il backup resta** ed è nel report, un avviso, e l'app parte (il `lifespan` con un fix che lancia un'eccezione);
  - `integrity_check` non `ok`: niente toccato;
  - lo script offline (sottoprocesso) converte ed esce con 0; `--dry-run` non scrive ed esce con 0; un fix fallito esce con 1.

## 8. Gate

- `api` (auth, broker-access, brim), `services` e le tre suite con `create_all`.
- `db` (schema, i test nuovi), `check-orphans`.
- `front-utility core-unit`.
- ruff, black, `mkdocs build` e `check-links`, `git diff --check`, porta libera.

## 9. CHANGELOG

Lo scrive il coordinatore; io propongo le righe al checkpoint.

## 10. Avanzamento

### 10.0 ✅ Analisi (2026-10-07)

- Letti: account, accessi, helper dei file, schema reale (sola lettura), migrazioni dalla 1.1, avvio, Docker, doc admin, censimento degli id.
- Il piano è in attesa della review.

### 10.1 ✅ Approvazione, fixture, stub, runner (2026-10-08)

> **Note implementazione**:
> - Piano aggiornato con le decisioni del developer (§0.1, §2.1, §2.3, §4, §7). Base `9d79c2dbe`, pulita.
> - **Fixture della 1.1**: `backend/test_scripts/fixtures/db/schema_v1_1_0.sql`, 37 istruzioni, revisione `5b1333fa6b07`, nessun AUTOINCREMENT.
>   - Generata dalle migrazioni **vere** di `v1.1.0` (`git archive` in `/tmp`, test mode, data-dir temporanea); il comando è nell'intestazione.
>   - Ricaricata in un DB nuovo, dà lo stesso `sqlite_master`.
>   - Le migrazioni di oggi la portano a `004_release_1_2_0_schema` senza errori: è il percorso di un'installazione 1.1.
> - **Stub**, con le firme definitive:
>   - `backend/app/db/post_migration/`: `__init__.py`, cioè `PostMigrationReport` e `run_post_migration_fixes`;
>   - `autoincrement.py`, col censimento `AUTOINCREMENT_TABLES`;
>   - `__main__.py`;
>   - `run_post_migration_fixes_at_startup()` in `main.py`, non ancora chiamata dal `lifespan`;
>   - `AccountDeletion` in `user_service.py`, mentre `delete_user` per ora resta com'è.
>
>   Ruff e black puliti.
> - **Runner**, solo le mie voci: `db autoincrement-schema`, `db post-migration` (anche in `db all`), `api account-deletion`.

### 10.2 ✅ I rossi (2026-10-08)

> **Note implementazione** — test-author, in parallelo su file distinti; i rossi li ho lanciati io (log nella sessione, `files/plan34/runs/0*-RED`):
> - **A**:
>   - `test_account_deletion_api.py`: ACCDEL-001 è lo scenario X/Y/Z/W più il trasferimento X→Y con `cost_basis_override`, e raccoglie le violazioni marcate `[new]`/`[guard]`. ACCDEL-002 è una guardia: l'unico amministratore resta rifiutato (con lo schema REG-007, senza mai toccare l'admin condiviso).
>   - In `test_user_profile.py`, la classe `TestDeleteUser`: la firma nuova; i broker dell'ultimo owner; tutto o niente quando `delete_bulk` solleva un'eccezione.
>   - **(b2)**, proposta del test-author: tutto o niente anche quando `delete_by_broker` fallisce. `delete_bulk` cattura le eccezioni e restituisce `success=False`, quindi `delete_user` deve trattare come errore anche il `False` di `leave_broker`.
>   - Esito: `services user-profile` 5 rossi e 20 verdi; `api account-deletion` ACCDEL-001 rosso, ACCDEL-002 verde.
> - **B**:
>   - `test_autoincrement_schema.py`: 3 rossi, più una guardia sul censimento.
>   - `test_post_migration.py`: 30 rossi, più una guardia sul dry-run dello script. Ci sono tutti i punti di §7, compreso lo schema «futuro», e il test 11: il `lifespan` lancia i fix dopo le migrazioni, e un fix che solleva un'eccezione non ferma l'avvio.
>   - Tutti i rossi sono `AssertionError`, molti sulle «barriere»; nessuno al setup.
>   - Uno dei rossi mostra il difetto: oggi, cancellato l'id più alto, il nuovo prende lo stesso id o uno più basso.
> - **Sicurezza dei test**: DB e data-dir sempre temporanei, con un canarino; Alembic sempre con `-x sqlalchemy.url=`, perché senza `env.py` userebbe il DB della corsia.

### 10.3 ✅ La cura e la prova a mano (2026-10-08)

> **Note implementazione**:
> - **`backend/app/db/post_migration/`**:
>   - `base.py`: il report, il contesto, l'errore, la classe base di un fix;
>   - `__init__.py`: il registro `FIXES`, `run_post_migration_fixes`, `_apply_pending`, `_integrity_ok`, `configured_sqlite_path`;
>   - `autoincrement.py`, il fix;
>   - `__main__.py`, lo script.
> - **`main.py`**: `run_post_migration_fixes_at_startup()` non solleva mai eccezioni; nel `lifespan` gira subito dopo `ensure_database_exists()`, con `asyncio.to_thread`.
> - **`001_initial.py`**: AUTOINCREMENT su 6 righe e nient'altro. **Modelli**: `sqlite_autoincrement` sulle stesse 6 tabelle.
> - **A**:
>   - `user_service.delete_user` restituisce `AccountDeletion`, applica `leave_broker` a ogni accesso, e in caso di errore fa rollback e rilancia;
>   - `AccountDeletionError` copre il caso in cui `leave_broker` risponde `False`;
>   - `auth.delete_own_account` trasforma un errore tecnico in un 500 («nothing was deleted») e pulisce i file dopo il commit, prima di rispondere;
>   - l'helper dei file è ora `brim_provider.delete_files_for_brokers`, usato dai due chiamanti di `brokers.py`, dove il vecchio è stato tolto;
>   - le docstring dicono la verità.
> - Ruff e black puliti su tutti i file cambiati.
>
> **⚠️ Fuori pista — come si ricostruisce la tabella** (esperimento su DB in memoria, SQLite 3.53.4): la ricostruzione ufficiale (`CREATE new_X` → copia → `DROP` → `RENAME`) funziona, ma SQLite riscrive il DDL salvato come `CREATE TABLE "brokers"`, con le virgolette.
> - Ho scelto un'altra strada: la tabella vecchia si rinomina da parte con `legacy_alter_table=ON`, così le FK delle altre tabelle continuano a chiamarla col suo nome; poi la nuova si crea dal DDL **esatto**, più `AUTOINCREMENT`; poi la copia, il `DROP` della vecchia, gli indici ricreati.
> - Il DDL salvato resta l'originale più `AUTOINCREMENT`, niente altro.
> - Tutti e 6 i DDL si validano prima di toccare qualunque cosa.
> - Una forma inattesa ferma il fix.
>
> **⚠️ Fuori pista — `broker_042`**: si giudicano solo i nomi canonici `broker_<id>`, senza zeri iniziali, perché l'app scrive solo quelli.
>
> | Gate mirati (log `files/plan34/runs/1*-GREEN`) | Esito |
> |---|---|
> | `db autoincrement-schema` | **4 passed** |
> | `db post-migration` | **31 passed** |
> | `services user-profile` | **25 passed** |
> | `api account-deletion` | **2 passed** |
>
> **La prova a mano dello script offline**, su un DB reale della corsia: l'archivio `.testLog/00_archive/test-db_20261007_175912`, alla revisione `004`, con 7459 righe e senza AUTOINCREMENT. Accanto, una cartella viva, un'orfana (`broker_999`) e `broker_none`.
> - `--dry-run`: `would_apply`, l'orfana elencata, nulla toccato, nessun backup.
> - Esecuzione vera:
>   - `applied`, AUTOINCREMENT su 6 tabelle su 6;
>   - righe e indici identici tabella per tabella;
>   - `foreign_key_check` vuoto, `integrity_check` ok, `sqlite_sequence` uguale al massimo;
>   - il backup cancellato, l'orfana cancellata, la cartella viva e `broker_none` al loro posto, nessuna quarantena rimasta.
> - Seconda esecuzione: `clean`.

### 10.4 ✅ Gate ampi e `TODO_FUTURI` (2026-10-08)

> | Gate (corsia 6156, uno alla volta; log `files/plan34/runs/2*`) | Esito |
> |---|---|
> | `db all`: il DB nasce dalle migrazioni nuove | tutto verde: create, schema validation 17 (DB e modelli d'accordo), numeric 3, populate, populate-reset 25, autoincrement-schema 4, post-migration 31, integrità referenziale 17, fx 6, brim 17, brim-bulk 7, asset-merge 12, model-validators 36 |
> | `api`, le suite che creano o cancellano account: auth / profile / broker-access / broker-multiuser / users-search / system / http-compression / portfolio-wac / pac-planner-tool / portfolio | 24 / 12 / 25 (+1 saltato) / 14 / 16 / 28 / 8 / 10 / 7 / 49 |
> | `api brim`, per l'helper spostato; `api account-deletion` | 79; 2 |
> | `services`: user-profile / brim-report-sets / brim-gap-fix / ai-export (`create_all`) | 25 / 259 / 99 / 925 |
> | `front-utility core-unit` | 3405 |
> | `check-orphans`; porta 6156 | pulito; libera |
>
> **`TODO_FUTURI.md`**: la voce «Gli id degli asset (e delle altre tabelle) si riusano…» è passata in `TODO_Completati.md`, in cima, col link a questo piano.
> - Restano aperti, e li segnalo al coordinatore:
>   - decidere se `BenchmarkSelect` può tornare a cancellare gli id spariti;
>   - il rapporto di fattibilità FIFO (`:300`): la sua frase sulla PK «mai riusata», per `transactions`, adesso è vera.

### 10.5 ✅ B5, la doc (docs-writer, solo EN, niente stamp; 2026-10-08)

> **Note implementazione**:
> - `admin/docker_advanced.en.md`: una sezione nuova, `## 🩹 Post-Migration Fixes {: #post-migration-fixes }`. Dice cosa succede all'avvio (integrità, rilevamento, backup, fix e verifica, esito), cosa dice il log e lo script a server spento con `docker compose run --rm`. In più, una riga in «Database Backup» sul file `.bak` tenuto.
> - `admin/cli_tools.en.md`: la stessa sezione per l'installazione su host (`pipenv run python -m backend.app.db.post_migration`).
> - `user/settings/profile.en.md`: «Delete Account» allineata alla regola dell'ultimo owner.
> - `mkdocs build` strict verde. `check-links` rosso solo per il link noto D28 (`user/assets/detail/chart/#rolling-return`), preesistente.
> - IT/FR/ES di queste tre pagine restano debito di traduzione. `profile` è il più urgente, perché la versione inglese dice adesso una cosa diversa.
>
> **⚠️ Fuori pista: tre cose trovate dal docs-writer**:
> 1. Il testo del dialogo di cancellazione (i18n) non diceva più la verità. Va in §10.6, decisione (a).
> 2. La gara fra i worker che partono insieme. Va in §10.6, il lock.
> 3. L'esempio `./dev.py docker exec db upgrade` della doc admin (`docker_advanced.en.md:232`) è probabilmente rifiutato a server acceso, per `check_server_running` (`scripts/cli_base.py:338`). È preesistente e non verificato: lo segnalo al coordinatore per il backlog.

### 10.6 ✅ Review: i18n, il lock, la durata nel log (2026-10-08)

> **Note implementazione**:
> - **i18n, decisione (a)** del coordinatore. Le chiavi `settings.deleteAccountDescription` e `settings.deleteAccountWarning` cambiano solo nel testo, ×4, con `dev.py i18n update`; le chiavi restano le stesse.
>   - Il dialogo dice esattamente cosa succede, come `profile.en.md`: i broker di cui sei l'unico owner si cancellano con le transazioni e i file importati, anche se li hai condivisi con viewer o editor. Quelli che hanno un altro owner restano a lui, e se ne va solo il tuo accesso. Le impostazioni si cancellano, e l'azione non si annulla.
>   - La terminologia è quella di `brokers.sharing.leaveLastOwnerWarning`.
>   - 8 righe cambiate, prettier ok. `i18n audit`: 4152 chiavi, tutte complete, 0 mancanti, 0 inutilizzate. `front check`: 0 errori, 0 avvisi. `core-unit`: 3405.
> - **Il lock**, per la gara fra i worker trovata dal docs-writer; la cura l'ha approvata il coordinatore.
>   - **I rossi** (test-author, sezione 12 di `test_post_migration.py`): 4 rossi, tutti `AssertionError`.
>     - Tre sonde (`LOCK_EX | LOCK_NB` da un descrittore nuovo, dentro `apply` e dentro `detect`, dry-run compreso) trovano `missing`, cioè nessun file di lock.
>     - Il test a due processi dà `['applied', 'failed']`, exit `(0, 1)`. Il secondo aveva già rilevato le tabelle da convertire, e ha tenuto un `.bak`: è il difetto esatto.
>   - **La cura**: `_exclusive_run(db_path)` in `post_migration/__init__.py`, sullo schema di `brim_provider._acquire_file_lock`.
>     - Apre `<nome del DB>.post-migration.lock` in `a+` e prende `fcntl.flock(LOCK_EX)`, bloccante.
>     - Il lock si prende **prima** di aprire il DB, così chi aspetta non tiene lock di SQLite. Si tiene dall'`integrity_check` alla pulizia, anche nel dry-run.
>     - Il file resta su disco: cancellarlo mentre un altro aspetta lascerebbe a un terzo il lock di un file nuovo.
>     - Senza `fcntl` (non POSIX) si va avanti senza lock.
>     - Anche il timestamp del backup si prende ora dentro il lock.
>   - **Verde**: `db post-migration` 35/35 (log `files/plan34/runs/post-migration-lock-{red,green}.log`).
>
> **⚠️ Fuori pista — due test oltre la richiesta** (test-author):
> - La sonda anche dentro `detect`. Un lock preso solo attorno ad `apply` passerebbe il test chiesto, e la gara resterebbe: tutti e due i worker rileverebbero prima che uno converta.
> - Il test con due processi veri, reso deterministico con degli handshake e senza sleep: i timeout servono solo contro un blocco.
>
> **⚠️ Fuori pista — la durata nel log**. Rileggendo il piano: il rischio 3 prometteva «il log dice quanto ci ha messo», e nessuna riga del log lo diceva.
> - **Rossi** (test-author, sezione 13): 2 rossi su `AssertionError`, perché manca la chiave `seconds`. Prima passano la barriera: la cattura con `structlog.testing.capture_logs` vede il logger del modulo.
> - **Cura**: in `_apply_pending`, le due righe di chiusura (`Post-migration fixes applied and verified` e `Post-migration fix failed: …`) portano `seconds`, cioè il tempo dal backup alla pulizia, in float con 3 decimali. Tutto il resto resta com'era. I run puliti e i dry-run non scrivono nessuna delle due righe.
> - **Verde**: 37/37.
>
> **Doc** (docs-writer, solo EN, niente stamp):
> - `docker_advanced.en.md:250` e `cli_tools.en.md:97`: i worker fanno a turno sul lock, e anche lo script offline aspetta il suo turno.
> - `docker_advanced.en.md:421`: il file di lock vuoto accanto al DB è innocuo e va lasciato al suo posto.
> - Passo 5 «Outcome» delle due pagine: le due righe del log dicono anche quanto è durato il run, in `seconds`.
> - `mkdocs build` strict verde; `check-links` rosso solo per il D28 noto.
>
> **⚠️ Fuori pista — uno spazio in coda nella fixture della 1.1**. È nel DDL reale di `alembic_version`, così come lo genera SQLAlchemy, ed è l'unico errore di `git diff --check` sui file nuovi.
> - Nessun test lo legge: `alembic_version` non è nel censimento. L'ho tolto e l'ho scritto nella ricetta della fixture («trailing spaces stripped»).
> - Niente `.gitattributes`, come per il campione DEGIRO. Rilanciato `db post-migration`: 37/37.
>
> **Runner**: il banner di `db post-migration` elenca adesso anche «concurrent runs, duration in the log».
>
> | Gate finali (corsia 6156, un comando alla volta; log `files/plan34/runs/`) | Esito |
> |---|---|
> | `db post-migration`, dopo l'ultima modifica | **37 passed** |
> | `db all` | 13/13 gruppi: create, validate 17, numeric 3, populate, populate-reset 25, autoincrement-schema 4, post-migration 37, integrità referenziale 17, fx 6, brim 17, brim-bulk 7, asset-merge 12, model-validators 36 |
> | `api account-deletion`, server vero sulla 6156, dopo il lock | 2 passed. `app.db.post-migration.lock` compare accanto al DB della corsia |
> | `i18n audit` / `front check` / `front-utility core-unit` | 4152 chiavi complete, 0 mancanti, 0 inutilizzate / 0 errori, 0 avvisi / 3405 |
> | ruff e black (15 file backend), `git diff --check` (anche sui file nuovi), `check-orphans` | puliti |
> | porte 6156 e 6166 | libere |
>
> **⚠️ Fuori pista — una docstring falsa**. Mentre scrivevo i corpi dei commit, ho trovato che la docstring di `delete_user` elencava fra le righe che cascano dall'utente anche le «sessions». Ma non esiste una tabella di sessioni: il JWT è stateless. La frase veniva dalla docstring vecchia.
> - Le tabelle che cascano davvero da `users` sono `user_settings`, `broker_user_access` e le due di onboarding. `global_settings.updated_by_user_id` invece va a NULL.
> - Corretta in «(settings, onboarding progress)». Cambia solo la docstring: ruff e black puliti.
