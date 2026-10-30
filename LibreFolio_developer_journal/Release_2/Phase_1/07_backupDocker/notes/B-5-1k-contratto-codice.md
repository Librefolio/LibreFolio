# B5-1k — contratto del codice (nomi fissati prima dei test rossi)

Data: 2026-10-26. Autore: B. Segue `B-5-1k-analisi-troppi-utenti.md` (D1–D4 del developer). I nomi qui sotto sono quelli che il codice avrà: i test rossi li usano.

## Regola di conteggio

- `M` = `registration_service._max_users()` (assente = `None` = nessun limite; non valido = 0).
- `users_active` (nel rapporto) = account **attivi** della copia **+ 1** se l'istanza è `managed`, `LIBREFOLIO_ADMIN_EMAIL` è impostata e l'account che ha quell'indirizzo esiste ed è **inattivo** (il restore lo attiva: A5-2).
- `users_over_limit = max(0, users_active − M)` se `M` non è `None`, altrimenti 0.
- Si tolgono solo account attivi del rapporto (`accounts`). Mai il titolare (scelto in app / ricavato da B5-1j). Resta sempre almeno un admin attivo (titolare incluso, su managed).
- Conferma valida se `users_active − len(remove_user_ids) <= M`. Di più del necessario è permesso.

## `staging.py`

- Nuovo `AccountToRemove(BaseModel, frozen)`: `user_id: int`, `username: str`, `is_superuser: bool`. Mai indirizzi.
- `StagingReport` guadagna (con default, un rapporto scritto prima si legge): `users_active: int = 0`, `users_limit: int | None = None`, `users_over_limit: int = 0`, `accounts: list[AccountToRemove] = []` (solo se `users_over_limit > 0`, ordinati per `username`).

## `apply.py`

- Errori (`RestoreStateError`): `RestoreTooManyUsersError` (`code = "too_many_users"`; il messaggio contiene i numeri attivi `N` e limite `M`); `RestoreRemoveUserInvalidError` (`code = "remove_user_invalid"`).
- `confirm_restore(stage_id, *, confirmed_by, confirmed_via="admin", owner_user_id=None, remove_user_ids=None, data_dir=None, now=None)`.
- Controlli (tutti prima di scrivere lo stato; il rifiuto non lascia traccia):
  1. `report.users_limit != limite attuale` (se il limite cambia dopo il controllo) → `RestoreStageOutdatedError`.
  2. `remove_user_ids` con un id duplicato, non in `report.accounts`, uguale al titolare effettivo, o che lascerebbe nessun admin attivo → `RestoreRemoveUserInvalidError`.
  3. Dopo la rimozione restano più di `M` attivi → `RestoreTooManyUsersError`.
  4. `M < 1` (limite non valido = 0) e attivi > 0 → `RestoreTooManyUsersError`.
  5. Serve una rimozione (`users_over_limit > 0`) su `managed` e non c'è un titolare (cli/pannello: `pick_owner` nessuno, oppure `LIBREFOLIO_ADMIN_EMAIL` assente) → `RestoreTooManyUsersError` con il testo che dice che manca un titolare a cui passare i broker.
- `RestoreState` guadagna `remove_user_ids: list[int] = []` e `removal_outcome: str | None = None` (`None` = ancora da fare, `"done"`, `"error:<CODE>"`; codici: `NO_RECIPIENT`, `OVER_LIMIT`). Solo id, mai nomi né indirizzi.
- Nuove: `removal_pending(data_dir) -> tuple[str, list[int]] | None` (stage_id e id, per un restore `committed` con `remove_user_ids` non vuoto e `removal_outcome is None`, a step `restore-owner` presente), `record_removal_outcome(data_dir, stage_id, outcome) -> RestoreState | None` (scrive una volta sola, come `record_owner_outcome`).
- `owner_assignment_problem`: `"pending"` anche mentre la rimozione è in attesa; il codice (`NO_RECIPIENT`, `OVER_LIMIT`, …) se `removal_outcome` è `error:*`. Il motivo di blocco resta uno solo (`owner_assignment`).
- `reset_owner_assignment` (e quindi `backup pending --recover owner`) cancella anche un `removal_outcome` `error:*`; `RestoreOwnerNotFailedError` solo se non c'è né l'uno né l'altro errore.

## `trim.py` (nuovo, `services/platform/instance_backup/trim.py`)

- `vanishing_brokers(accesses, removed_ids) -> set[int]`: `accesses` = iterabile di `(broker_id, user_id, role)` (`role` stringa `"OWNER"`/`"EDITOR"`/`"VIEWER"`); un broker sparisce se ha **almeno un OWNER** e **tutti** i suoi OWNER sono in `removed_ids`.
- `removal_preview(database: Path, remove_user_ids) -> RemovalPreview` (SQL grezzo in sola lettura, `mode=ro`, `trusted_schema=OFF`): `RemovalPreview(accounts_removed: int, handed_over: list[HandedOverBroker], accesses_removed: int)`; `HandedOverBroker(broker_id: int, name: str, transactions: int)`; `accesses_removed` = accessi dei tolti su broker che **non** spariscono.
- `async remove_restored_accounts(engine, *, remove_user_ids, owner_user_id, managed) -> int`: rilegge tutto dal DB a ogni chiamata; destinatari: `managed` → l'account `owner_user_id` se esiste, attivo, admin e non fra i tolti; altrimenti gli admin attivi che non sono fra i tolti; nessuno → `RemovalError("NO_RECIPIENT")`. Per ogni broker che sparirebbe scrive la riga `BrokerUserAccess` di ogni destinatario: OWNER, `share_percentage` 0 (già OWNER: non si tocca; altro ruolo: promosso a OWNER, quota 0). Poi `user_service.delete_account` per ogni tolto esistente (id spariti: saltati). Alla fine, se gli attivi sono più di `M` → `RemovalError("OVER_LIMIT")`. Ritorna quanti account ha tolto. `RemovalError(code)` ha l'attributo `code`.
- Ripetere la chiamata dopo un'interruzione fa solo il resto.

## `owner.py`

- `assign_restored_owner` fa, nell'ordine: (1) il titolare (come oggi, se in attesa); (2) la rimozione, se `removal_pending` e il titolare non è in errore. Vale anche su self-hosted (senza titolare). Esiti registrati con `record_removal_outcome` (`done` o `error:<CODE>`); un errore non atteso non registra nulla (il prossimo avvio riprova).

## API

- `RestoreConfirmRequest.remove_user_ids: list[int] = []`.
- `RestoreStageReport` guadagna `users_active`, `users_limit`, `users_over_limit`, `accounts: list[RestoreAccountToRemove{user_id, username, is_superuser}]`.
- Nuovo `POST /backup/restore/stage/{stage_id}/removal-preview` (solo admin, come il confirm). Corpo `RestoreRemovalPreviewRequest{remove_user_ids: list[int], owner_user_id: int | None}`. Risposta 200 `RestoreRemovalPreview{accounts_removed: int, handed_over: [{broker_id, name, transactions}], accesses_removed: int}`. 404 `restore_stage_not_found`; 409 `remove_user_invalid` (stesse regole 2 di sopra, titolare = `owner_user_id` del corpo).
- Conferma: `too_many_users` e `remove_user_invalid` → 409 (mappa già generica). Pannello (`panel_restore.py`, file di H, non cambia): nessuna scelta → `confirm_restore` rifiuta con `too_many_users` → 409 con i numeri nel messaggio.

## CLI (`scripts/backup_cli.py`)

- `backup restore ARCHIVE [--remove-user USERNAME ...]` (ripetibile). Nomi → id dai `report.accounts` (confronto senza distinguere maiuscole; nome sconosciuto o ambiguo → `❌ --remove-user: …` e nessuna conferma, la copia viene rimossa, exit 1).
- Rapporto: se `users_over_limit > 0` stampa `⚠️ The backup holds {N} active accounts; this instance accepts {M} (LIBREFOLIO_MAX_USERS): …` più l'elenco dei nomi (`_safe`), mai indirizzi. Senza `--remove-user` sufficienti la conferma stampa `❌ … (too_many_users)` e exit 1; `--dry-run` con troppi utenti e senza rimozioni sufficienti: exit 1.
- Con rimozioni valide: stampa quanti broker passano (con `removal_preview`) e `✅`.
- `backup pending` / `--json`: `removal_outcome` `error:*` → `reason = "owner_assignment"`, `choices = ["owner"]`; in attesa → come il titolare in attesa. `--json` mai nomi né id.

## Frontend (seconda ondata, dopo `api sync`) — contratto fissato

Cartella `frontend/src/lib/features/backup/`.

- `backupApi.ts`: `confirmRestore(stageId, ownerUserId = null, removeUserIds = [])` manda `{owner_user_id, remove_user_ids}`; nuova `previewRestoreRemoval(stageId, removeUserIds, ownerUserId = null): Promise<RestoreRemovalPreview>` (POST `/backup/restore/stage/{id}/removal-preview`, corpo `{remove_user_ids, owner_user_id}`; risposta `{accounts_removed, handed_over: [{broker_id, name, transactions}], accesses_removed}`). Tipi `RestoreRemovalPreview` e `RestoreAccountToRemove` riesportati da `backupApi.ts`.
- `restoreFlow.svelte.ts`: la seam `api.confirm(stageId, ownerUserId, removeUserIds)` e `api.previewRemoval(stageId, removeUserIds, ownerUserId)`; il controller: `confirm(ownerUserId = null, removeUserIds = [])` e `previewRemoval(removeUserIds, ownerUserId = null)` (usa lo stage del rapporto aperto; errore se non c'e').
- `restoreText.ts`: `ERROR_KEYS.too_many_users = 'backup.restore.errors.too_many_users'`, `ERROR_KEYS.remove_user_invalid = 'backup.restore.errors.remove_user_invalid'`.
- `RestoreTrimModal.svelte` (nuovo). Props: `open: boolean`, `report: RestoreStageReport`, `ownerUserId: number | null` (il titolare: non si toglie), `loadPreview: (removeUserIds: number[]) => Promise<RestoreRemovalPreview>`, `onConfirm: (removeUserIds: number[]) => void`, `onCancel: () => void`, `busy?: boolean`.
  - Mostra `report.accounts`. Il numero da togliere e `report.users_over_limit`; restano `report.users_active - selezionati`; la conferma e accesa solo se `report.users_limit !== null` e restano `<= users_limit` (e `busy` falso). Se si scelgono piu del necessario c'e un avviso (`restore-trim-extra`) ma si puo.
  - Il titolare (`ownerUserId`) e visibile ma bloccato (non selezionabile). Senza titolare, l'ultimo admin che resterebbe non selezionato non si puo selezionare (bloccato) cosi non si arriva a zero admin.
  - Anteprima: a ogni cambio della selezione (non vuota) chiama `loadPreview(ids)` (solo l'ultima risposta conta); mostra i broker che passano (nome, n. transazioni) e quanti altri accessi se ne vanno; un errore dell'anteprima mostra un testo, la conferma resta possibile. Nessun indirizzo email in pagina (il rapporto non ne ha).
  - `data-testid`: `restore-trim-modal` (anche `data-over` = users_over_limit), `restore-trim-need`, `restore-trim-remaining`, `restore-trim-account` (uno per account, con `data-user-id`, `data-selected`, `data-locked`, `data-owner`, `data-admin`), `restore-trim-extra`, `restore-trim-preview`, `restore-trim-broker` (`data-broker-id`), `restore-trim-preview-error`, `restore-trim-confirm`, `restore-trim-cancel`.
  - `onConfirm` chiama con gli id scelti (ordinati); `onCancel` su annulla/Escape/clic fuori (non se `busy`).
  - Testi: chiavi `backup.restore.trim.*` (4 lingue): `title`, `intro` (valori `active`, `limit`), `need` (`count`), `remaining` (`count`, `limit`), `ownerBadge`, `adminBadge`, `locked`, `previewTitle`, `previewNone`, `previewBrokers` (`count`), `previewBroker` (`name`, `transactions`), `previewAccesses` (`count`), `previewError`, `extra`, `confirm`, `cancel`, `noLimit`.
- `RestoreReportModal.svelte`: `onConfirm: (ownerUserId: number | null, removeUserIds: number[]) => void`; nuova prop facoltativa `loadRemovalPreview?: (removeUserIds: number[], ownerUserId: number | null) => Promise<RestoreRemovalPreview>`. Dopo la parola digitata: se c'e la scelta del titolare si apre prima quella; poi, se `report.users_over_limit > 0`, si apre `RestoreTrimModal` (con `ownerUserId` scelto); poi `onConfirm(ownerUserId, ids)`. Senza eccesso il flusso e quello di prima e `onConfirm` riceve `removeUserIds = []`.
- `RestoreCard.svelte`: passa `controller.confirm(ownerUserId, removeUserIds)` e `loadRemovalPreview={(ids, owner) => controller.previewRemoval(ids, owner)}`.
