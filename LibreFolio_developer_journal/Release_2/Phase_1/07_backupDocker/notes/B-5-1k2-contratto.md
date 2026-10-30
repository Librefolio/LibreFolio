# B5-1k2 — contratto: l'avviso «troppi utenti» nel ripristino (versione ridotta)

Data: 2026-10-26. Autore: B. Sostituisce B5-1k (cancellazione, archiviata in `archive/b5-1k-delete-design`). Decisione del developer: gli utenti oltre `LIBREFOLIO_MAX_USERS` si **disattivano**, un solo meccanismo, A5-7 (l'amministratore sceglie al primo accesso). Il ripristino quindi **non rifiuta mai** per troppi utenti: dice soltanto, prima della conferma, che al primo accesso l'amministratore sceglierà.

## Regola di conteggio (solo informativa)

- `limit` = `LIBREFOLIO_MAX_USERS` come numero; **assente o non valido → nessun limite** (`None`). Un valore non valido non fa mai scattare l'avviso (come A5-7). Si legge da `backend.app.config.accounts.max_users()` (ValueError → `None`), non da `registration_service`.
- `users_active` = account **attivi** della copia **+ 1** se l'istanza è `managed`, `LIBREFOLIO_ADMIN_EMAIL` è impostata e l'account della copia che ha quell'indirizzo (confronto `user_service.same_email`) esiste ed è **inattivo** (il ripristino lo attiva: A5-2). Si calcola sempre, anche senza limite.
- `users_over_limit = max(0, users_active − limit)` se `limit` non è `None`, altrimenti 0.

## Backend

- `staging.StagingReport` guadagna (con default, un rapporto scritto prima si legge): `users_active: int = 0`, `users_limit: int | None = None`, `users_over_limit: int = 0`. **Nessun elenco di account, nessun indirizzo.**
- Quando `users_over_limit > 0` il rapporto ha l'avviso `users_over_limit` in `warnings`, **prima** di `credentials_from_backup` (che resta sempre l'ultimo). Altrimenti l'avviso non c'è.
- `schemas.backup.RestoreStageReport` guadagna gli stessi tre campi (con gli stessi default) e `"users_over_limit"` nel `Literal` di `warnings`. `api/v1/backup/restore.py::_report_view` li riempie. La vista del pannello (`PanelRestoreStageReport`, di H, non si tocca) riceve il codice di avviso nei `warnings` (riusa il `Literal`) e **nessun numero** (la sua lista di campi è chiusa).
- **Nessun rifiuto**: `apply.confirm_restore`, la CLI e il pannello confermano come prima anche con `users_active` > limite. Nessun nuovo stato, nessun nuovo campo nel body della conferma, nessuna rotta nuova, nessun codice d'errore nuovo.

## CLI (`scripts/backup_cli.py`)

- Nel rapporto (`_print_stage_report`), se `users_over_limit > 0`, **una** riga: `⚠️  The backup holds {N} active accounts; this instance accepts {M} (LIBREFOLIO_MAX_USERS): at the first sign-in the administrator chooses who keeps access, the others are deactivated (not deleted)`. Con `N = users_active`, `M = users_limit`. Nessun nome utente, nessun indirizzo. Il codice `users_over_limit` non genera una seconda riga (va in `_STAGE_WARNINGS_SAID_APART`).
- Non si aggiunge nessuna opzione (`--remove-user` non esiste). `restore --yes` conferma (exit 0); `--dry-run` esce 0.

## Frontend (`frontend/src/lib/features/backup/`)

- `restoreText.ts`: `WARNING_KEYS.users_over_limit = 'backup.restore.report.usersOverLimit'` e il codice in `WARNINGS_SHOWN_APART` (non è una riga della casella degli avvisi).
- `RestoreReportModal.svelte`: un avviso a parte `data-testid="restore-users-over-limit"` quando `report.users_over_limit > 0`, con la chiave `backup.restore.report.usersOverLimit` e i valori `{active, limit}` (da `users_active`, `users_limit`). Il flusso di conferma **non cambia** (parola digitata → eventuale scelta del titolare → `onConfirm(ownerUserId)`): nessun passo in più.
- i18n (4 lingue, a cura mia): `backup.restore.report.usersOverLimit` con `{active}` e `{limit}`.
- Il tipo `RestoreStageReport` (generato da `./dev.py api sync`) ha i tre campi opzionali: la modale usa `?? 0` / `?? null`.

## Docs (EN, docs-writer)

`backup_restore.en.md` (sezione corta che spiega: il ripristino non rifiuta per troppi utenti; l'avviso; al primo accesso l'amministratore sceglie, gli altri si disattivano, nessun dato cancellato; link ad A5-7 quando esiste) e `cli_backup.en.md` (la riga di avviso).
