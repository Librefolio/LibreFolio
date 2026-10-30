# B5-1l — contratto: il ripristino dal pannello mantiene la password del titolare

Data: 2026-10-26. Autore: B. Decisione del developer (opzione a, senza controllo «stessa istanza»): «l'eccezione vale per ogni ripristino dal pannello su managed con il titolare unico all'indirizzo della variabile». Rischio accettato: chi può scrivere nel deposito delle copie del cloud potrebbe fabbricarne una; si scrive nella documentazione per l'host.

## La regola (tutte e quattro insieme, altrimenti resta B5-1j alla lettera)

1. canale = pannello (`confirmed_via == "panel"`; mai app, CLI);
2. profilo `managed` e `LIBREFOLIO_ADMIN_EMAIL` impostata;
3. nel backup **un solo** account è segnato come titolare (`users.is_instance_owner = 1`, contati TUTTI gli account, di qualunque ruolo, anche inattivi), ed è un amministratore **attivo**;
4. quell'account ha l'indirizzo di `LIBREFOLIO_ADMIN_EMAIL` (confronto `user_service.same_email`).

Il rapporto non deve avere `owner_conflicts` (come oggi: altrimenti `owner_conflict`, 409, prima di tutto) e deve essere stato letto per lo stesso indirizzo (`restore_stage_outdated`, come oggi).

Se vale: il ripristino **non** revoca la password del titolare, **non** chiude le sue sessioni, **non** manda il link. Il resto (le sessioni di tutti gli altri account chiuse, i link monouso revocati, ecc.) è come sempre. In ogni altro caso: B5-1j invariato.

## Staging

- `StagingReport.owner_marks: int = 0` (default, un rapporto scritto prima si legge): quanti account della copia hanno `is_instance_owner = 1` (colonna assente → 0), letti a sola lettura con `trusted_schema=OFF`. Nuova funzione `staging._owner_marks(database) -> int`; `_owner_check` NON cambia firma.

## apply

- `apply.keeps_owner(candidates, owner_marks, owner_email) -> int | None`: l'id dell'account della regola (3)+(4), altrimenti `None`. Esige `owner_marks == 1`.
- `OWNER_OUTCOME_KEPT = "kept"`.
- `_check_owner_choice(report, confirmed_via, owner_user_id)`: per `confirmed_via == "panel"` su managed con V impostata, dopo i controlli del rapporto, se `keeps_owner(...)` dà un id → `(id, "kept")` (l'id va in `owner_user_id`, `owner_outcome` = `"kept"`). Per `admin` e `cli` mai. Se non dà un id → il flusso di B5-1j (pick_owner).
- `RestoreState`: nessun campo nuovo. `owner_outcome == "kept"` è definitivo: `owner_pending` → `None`, `owner_assignment_problem` → `None`, `backup pending` non lo tratta come errore.
- `_close_the_way_in(..., kept_owner_user_id: int | None = None)`: con `kept_owner_user_id`, nella stessa transazione: `session_version` sale per tutti **tranne** quell'account (la sua resta quella del backup); `_clear_owner_flag` azzera il flag su tutti **tranne** quell'account (resta 1); `_close_owner_account` NON gira (password, indirizzo, ruolo invariati). Prima, nella transazione, si ricontrolla che l'account sia ancora attivo, amministratore, con l'indirizzo di V e l'unico segnato; se no → il commit tratta il titolare come B5-1j (password chiusa, flag, ecc.) e `finish_pending_restore` riporta `owner_outcome` a `None` così che l'avvio dia il link (A). Una riga di log, `Panel restore: the owner's password and sessions are kept` (warning, solo stage_id e user_id, nessun indirizzo), quando la password è davvero mantenuta.
- `finish_pending_restore` passa `kept_owner_user_id = state.owner_user_id` se `state.owner_outcome == "kept"`.

## Avvio

- `owner.assign_restored_owner`: con `owner_outcome == "kept"` non fa nulla (nessuna chiamata ad A, nessun log di assegnazione).

## CLI

- `backup pending` per un ripristino `committed` con esito `kept` stampa una riga: `🔑 The owner's account kept its password and its open sessions (restore from the hosting panel)`; `--json` invariato (nessun nome, nessun id). `backup restore` dalla CLI non stampa la riga «sarà il titolare… password chiusa» diversa da oggi per il caso (la CLI revoca comunque).

## Docs (EN, docs-writer)

`backup_restore.en.md`: sezione `#owner-kept`: la regola, perché (un ripristino notturno automatico della stessa istanza deve essere trasparente), il rischio accettato (chi scrive nel deposito delle copie potrebbe fabbricarne una; il cloud deve custodirle come chiavi), che app e CLI revocano comunque. `cli_backup.en.md`: la riga di `backup pending`.
