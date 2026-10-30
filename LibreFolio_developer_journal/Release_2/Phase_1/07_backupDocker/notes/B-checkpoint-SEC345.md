# B · CHECKPOINT READY — SEC-3, SEC-4, SEC-5 e il 500 con `reason` (22/10/2026)

HEAD `b61c3ede3`. Nessuna operazione git. 20 file tracciati modificati, nessun file nuovo.
Interfaccia: `ondata4/B-sec345-interface.md`.

## File (un solo gruppo, un solo commit)

- **Backend**: `backend/app/api/v1/backup/restore.py`, `backend/app/services/platform/instance_backup/restore_jobs.py`, `scripts/backup_cli.py`.
- **Frontend**: `frontend/src/lib/features/backup/{backupApi.ts, restoreFlow.svelte.ts, RestartOverlay.svelte, RestoreCard.svelte}`, `frontend/src/lib/i18n/backup/{en,it,fr,es}.json`.
- **Test**:
  - `backend/test_scripts/test_services/test_backup_leftovers.py`
  - `backend/test_scripts/test_api/test_backup_restore.py`
  - `backend/test_scripts/test_api/test_backup_restore_apply.py`
  - `backend/test_scripts/test_utilities/test_backup_cli_sealed.py`
  - `frontend/src/lib/features/backup/{backupApi,restoreFlow,RestartOverlay,restoreI18n}.test.ts`
- **Piano** `plan-phase01BackupDocker.prompt.md`: una sezione in coda.

## Cosa fa

1. **SEC-3**: `UploadWriter.finish(*, replace_others=True)` e la funzione pubblica `restore_jobs.remove_replaced_uploads(data_dir, *, keep=)`. La rotta dell'admin resta com'è.
2. **SEC-4**: `abort()` toglie anche il file finale quando `finish()` è fallito dopo il rename. Nessun caricamento resta senza id.
3. **SEC-5**:
   - `--identity-file` leggibile da altri → una riga `⚠️ <file> can be read by others (mode 0644)… chmod 600 <file>`, e il comando prosegue;
   - `keygen` scrive in un file temporaneo con `os.write` e `fsync`, poi `os.link`, che non sovrascrive mai (con un ripiego sul rename dove il file system non ha link fisici); il file temporaneo viene tolto in ogni caso.
4. **Status 500**: `detail` = `{code: restore_state_unreadable, message (invariato), reason: io|not_a_file|invalid}` su stato, conferma, annullamento e riavvio. L'OpenAPI nomina `reason`. `_state_unreadable(exc=None)` tiene il suo nome, con l'argomento facoltativo.
   - **Frontend**: `readStatusWithSession` dà `{kind:'unreadable', reason}`; `restoreFlow` smette di interrogare (`outcome 'state_unreadable'`, `unreadableReason`); `RestartOverlay` mostra `backup.restore.restart.stateUnreadable` (4 lingue) e il pulsante Indietro.

## Prove

**Rossi** (log `B-sec345-red-*.log`): `services backup-leftovers` 4, `api backup-restore` 1, `api backup-restore-apply` 21, `utils backup-cli-sealed` 11; Vitest 30 rossi più 7 errori.

**Verdi** (log `B-sec345-green-*.log` e `B-sec345-reg-*.log`):
- le suite rosse: `backup-leftovers` 207, `backup-restore` 167, `backup-restore-apply` 262, `backup-cli-sealed` 49; Vitest dei 4 file 693, cartella `backup/` 1 143 (sotto `flock`);
- regressione:
  - `utils`: `backup-cli-restore` 120, `backup-cli` 106, `cli-secure` 106, `gate-i18n-catalog` 176;
  - `services`: staging 221, apply 331, jobs 167, secure 91, sealed 130;
  - `api`: backup 23, panel 89, secure 24, instance-errors 16;
  - `schemas openapi-client-text` 78;
  - `e2e backup-roundtrip` 3; `e2e backup-roundtrip-l3` 1 verde e i 2 rossi di H, che qui non è unito;
- `front check` 0/0; `api sync` fatto; `ruff`, `black`, `prettier`, `git diff --check` puliti.

**Fuori pista**: avevo cambiato il testo del messaggio del 500, ma i test lo fissano. L'ho rimesso com'era: l'informazione nuova sta in `reason`.

## Per H (`panel_restore.py`, file suo)

- **SEC-3**: `writer.finish(replace_others=False)`, poi il controllo del tipo (`LFBK`), poi `restore_jobs.remove_replaced_uploads(data_dir, keep=upload.upload_id)`. Se il tipo è sbagliato, chiamare `writer.abort()`: ora toglie anche il file finale.
- **Il 500**: per lo stato illeggibile usare `_state_unreadable(exc)`, così anche il pannello riceve `reason`.

## Commit proposto

`fix(backup): uploads kept until accepted, safe keygen, unreadable state reason (SEC-3/4/5)`, oppure tre commit: SEC-3+4 (`restore_jobs.py` e i suoi test), SEC-5 (`backup_cli.py` e `test_backup_cli_sealed.py`), 500 + frontend (`restore.py`, frontend, i18n, `test_backup_restore_apply.py`).

## CHANGELOG (proposto)

- `### 🐛 Fixed`:
  - «The restart page no longer polls forever when the server cannot read the state of a restore: it says so and points to `backup pending`»;
  - «`backup keygen` never leaves a half-written key file».

**FROZEN**
