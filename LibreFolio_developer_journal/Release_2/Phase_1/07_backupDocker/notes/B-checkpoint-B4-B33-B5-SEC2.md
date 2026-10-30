# B · CHECKPOINT READY — B4, B-33, B5, SEC-2 (22/10/2026)

Worktree `e-alfy-miniature-telegram`, ramo `e-alfy-b-backup-e-docker`, HEAD `3c89f6f86`. Nessuna operazione git.
In totale: 17 file tracciati modificati + 3 nuovi. Esclusi dal commit: il client generato, `site/` di mkdocs, i log in
`ondata4/`.

## File in comune fra i gruppi (da dividere per hunk)

| File | Gruppi |
|---|---|
| `LibreFolio_developer_journal/Release_2/Phase_1/07_backupDocker/plan-phase01BackupDocker.prompt.md` | B5, B-33, B4, SEC-2: quattro sezioni in coda, una per gruppo, nell'ordine «B5 — il round trip L3…», «B-33 — uno stato…», «B4 — la doc…», «Revisione di sicurezza…» |
| `mkdocs_src/docs/admin/backup_restore.en.md` | B4 (tutta la sezione `## Sealed Backups` e il resto) + B-33 (una riga nella tabella `#restart-problems`, quella che comincia con «`backup pending` says `The state of the restore cannot be read`») |
| `mkdocs_src/docs/admin/cli_tools.en.md` | B4 (`#backup-sealed`, una frase nell'intro del backup, una in «Back Up with Docker») + B-33 (l'esempio `--recover` in `#backup-pending`, la frase che rimanda a «An Unreadable Restore State», la nuova `#### 🧩 An Unreadable Restore State {: #backup-pending-unreadable }`) |

Tutti gli altri file appartengono a un solo gruppo.

## 1. B4 — doc del backup notturno sigillato, più la cura dello zip in chiaro

**File**:
- `mkdocs_src/docs/admin/backup_restore.en.md` (parte B4)
- `mkdocs_src/docs/admin/cli_tools.en.md` (parte B4)
- `mkdocs_src/docs/developer/architecture/security.md`
- `backend/app/services/platform/instance_backup/jobs.py` (in `_protect`: lo zip in chiaro si toglie appena la busta è scritta, prima del sigillo; è anche il punto 1 della revisione di sicurezza)
- `backend/test_scripts/test_services/test_backup_secure.py` (il rosso `test_while_sealing_the_clear_zip_is_already_gone`)

**Prove**:
- `mkdocs build` stretta exit 0 (log `B-b33-mkdocs-build.log`, ultima build con anche B-33); `mkdocs check-links` exit 0 (97 link validi).
- Zip in chiaro: rosso prima (`B-b4fix-red.log`: lo zip c'era ancora al sigillo), poi verdi: `services backup-secure` 91, `services backup-jobs` 167, `api backup-panel` 89, `utils backup-cli-sealed` 35 (`B-b4fix-green-*.log`).
- Debito di traduzione in `cli_tools` (it/fr/es), nessun `translate-stamp`.

**Commit proposti**:
- `docs(backup): sealed nightly backup guide (B4)`: i tre file di doc (parte B4).
- `fix(backup): drop the clear zip before sealing (SEC-1)`: `jobs.py` + `test_backup_secure.py`.

## 2. B-33 — stato del ripristino illeggibile (parte senza H)

**File**:
- `backend/app/services/platform/instance_backup/apply.py`
- `backend/app/services/platform/instance_backup/restore_jobs.py`
- `scripts/backup_cli.py`
- `backend/test_scripts/test_services/test_backup_apply.py`
- `backend/test_scripts/test_services/test_backup_leftovers.py`
- `backend/test_scripts/test_utilities/test_backup_cli_restore.py`
- `backend/test_scripts/test_api/test_backup_restore_apply.py`
- `mkdocs_src/docs/admin/backup_restore.en.md` (la riga B-33) e `cli_tools.en.md` (parte B-33)

**Cosa fa**:
- Lettura: «nessuno stato» solo se il file manca. Un file che non si può usare dà `RestoreStateUnreadableError` con `reason`: `io`, `not_a_file` o `invalid`. Il messaggio di `io` resta quello di B-32. L'avvio non cambia: il blocco lo fa H.
- `apply.restore_state_problem(data_dir)`: è il gancio per H, non solleva mai.
- `protected_stage` restituisce `EVERY_STAGE`: `prune` non tocca nessuna copia, `remove_check` rifiuta se la copia c'è ancora, la conferma è rifiutata.
- `apply.recover_unreadable_restore` e CLI `backup pending --recover`, esclusivo con `--cancel`: rimette i dati di prima da `previous/` e mette da parte lo stato come `restore.json.unreadable-<UTC>`. `backup pending` racconta il caso.
- Nessuna funzione privata di `api/v1/backup/restore.py` toccata.

**Prove**: rossi (`B-b33-red-*.log`) → verdi (`B-b33-green-*.log`):

| Suite | Rossi | Verdi |
|---|---|---|
| `services backup-leftovers` | 6 | 199 |
| `services backup-apply` | 71 | 331 |
| `utils backup-cli-restore` | 13 | 120 |
| `api backup-restore-apply` | 25 | 241 |

Regressione verde (`B-b33-reg-*.log`):
- `services`: staging 221, jobs 167, outcome 166, archive 176, secure 90, sealed 124, envelope 100, checks 127, non-iso 46;
- `api`: restore 166, panel 89, secure 24, backup 23, instance-errors 16;
- `utils`: backup-cli 106, cli-secure 106, cli-sealed 35;
- `e2e backup-roundtrip` 3.

`ruff` e `black` puliti.

**Commit proposto**: `fix(backup): unreadable restore state protects copies, pending --recover (B-33)`.

**Per H**: all'avvio, se `apply.restore_state_problem(data_dir)` non è `None`, l'istanza entra nel modo «ripristino interrotto». **Proposta** per `GET /backup/restore/status`: `409 restore_state_unreadable` con `reason`, al posto del 500 (non applicata).

## 3. B5 — round trip L3 in rosso (contro le rotte di H)

**File**:
- nuovo `backend/test_scripts/test_e2e/test_backup_roundtrip_l3.py`
- `scripts/test_runner/_backend_api.py`: un blocco aggiunto, la funzione `e2e_backup_roundtrip_l3` e `add_test(e2e, "backup-roundtrip-l3", …)`

**Prove**: `e2e backup-roundtrip-l3` dà 1 verde e 2 rossi (`B-b5-red.log`, riconfermato in `B-sec2-l3.log`).
- Verde: il backup del pannello è sigillato e il «coordinatore» del test apre la password.
- Rossi solo per la parte di H: `panel/status` senza `mode`, e `PUT …/panel/restore/upload` che risponde 405 (la rotta non c'è in questo ramo).
- Le ipotesi sul contratto sono segnate nel test con `# H-62 contract §…`.

**Commit proposto**: `test(backup): L3 round trip against the panel restore routes, red until H-62`.

## 4. SEC-2 — il lettore del `.tar` rifiuta i dati dopo la fine

**File**:
- `backend/app/services/platform/instance_backup/sealed.py` (`_end_of_archive`)
- `backend/test_scripts/fixtures/backup_l3/generate_vectors.py` (opzione `--extend`)
- `backend/test_scripts/fixtures/backup_l3/vectors.json`
- nuovi `backend/test_scripts/fixtures/backup_l3/neg-hidden-member.tar` e `neg-trailing-garbage.tar`

**Prove**:
- Rossi: `services backup-sealed`, 2 rossi sui due vettori nuovi (`B-sec2-red.log`).
- Verdi (`B-sec2-green-*.log`): `services backup-sealed` 130, `utils backup-cli-sealed` 35, `services backup-secure` 91.
- I 12 file dei vettori già copiati dal cloud sono identici (`sha256sum -c`).

**Commit proposto**: `fix(backup): sealed tar reader refuses data after the end (SEC-2)`.

## Ordine di commit suggerito

1. B-33
2. SEC-1 (lo zip in chiaro)
3. B4 (la doc)
4. SEC-2
5. B5
6. Il piano (le quattro sezioni), oppure ogni sezione con il suo gruppo.

## CHANGELOG (proposto, non scritto)

- `### ✨ Added`:
  - «Sealed nightly backups: a `.tar` whose random password only an age key opens (`LIBREFOLIO_BACKUP_RECIPIENTS`, `backup keygen`, `--recipient`/`--sealed`, `--identity-file`)»;
  - «`backup pending --recover`: when the restore's state cannot be read, put the data of before back».
- `### 🔄 Changed`: «An unreadable restore state is never taken for "no restore": no checked copy is removed and no restore is confirmed until the administrator recovers».
- `### 🐛 Fixed`: «A sealed backup no longer keeps the clear zip on disk while it seals».

## Per H: righe per `hosting_providers.en.md`

- Nella tabella dei job: `| Download the archive | GET …/{job_id}/file | The zip archive, or the sealed .tar (application/x-tar) when LIBREFOLIO_BACKUP_RECIPIENTS is set |`
- Un punto «🔏 Sealed backups», con:
  - la variabile, con una o due chiavi `age1…`;
  - il `.tar` con i suoi tre membri;
  - nel job finito, `file_sha256`, `sealed` e `sealed_recipients`;
  - le ultime fasi, `encrypting` e `sealing`;
  - il link a `backup_restore.md#sealed`.
- Un punto «🏷️ Managed profile»: senza destinatari, `POST …/jobs` risponde `503 backup_panel_unavailable`, e il controllo `backup.recipients` lo segnala.
- Nella riga `503` della tabella dei rifiuti: destinatari illeggibili, o assenti nel profilo `managed`.
- La riga `409 backup_awaiting_restore`.

**FROZEN** finché non arriva il commit; poi i punti 3, 4 e 5 della revisione.
