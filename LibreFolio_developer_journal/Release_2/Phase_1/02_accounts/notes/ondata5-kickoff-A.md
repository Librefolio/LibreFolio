# Kickoff A · Account e accessi — ondata 5 — bozza

Regole comuni: `kickoff-common.md` (leggilo per primo).

> **A cosa serve (per il developer).** Per il **profilo managed** (profilo `managed`): (1) **L'admin titolare non si può togliere**: l'account con l'email di `LIBREFOLIO_ADMIN_EMAIL` non si elimina, non si disattiva, non si declassa; i ganci ci sono ma **non proteggono nessuno** (`user_service.account_protection` è uno stub `return None`, `accounts/user_service.py:842-848`). (2) **Ripristino di un backup caricato a mano dall'admin del cloud**: il controllo chiede **quale utente del backup diventa l'admin titolare**; propone quello con l'email del titolare e, se c'è già, la scelta è obbligata; una modale avvisa che a quell'utente verrà messa l'email del titolare e che la password verrà **reimpostata via link email**; a fine ripristino l'account è admin, protetto, e riceve il link. **Non** vale per i ripristini del pannello (copie notturne). Esempio: Mario carica il backup della sua vecchia istanza: i suoi due utenti «mario» e «anna» sono admin; la modale propone quello che ha già la sua email; a ripristino finito Mario riceve il link per scegliere la nuova password.

**Modello**: Sonnet; **revisione Opus** (30 minuti) del diff di A5-1: è sicurezza.
**Giorni**: 1,5-2 (A5-1 0,5; A5-2 1-1,5). **Blocca il tag**: sì, entrambi (cloud).
**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-legendary-winner` · **Branch**: `e-alfy-a-account-e-accessi`
**HEAD di partenza (da verificare)**: `1fd80c481` (= `dev_release2`, treni 9 e 10 dentro; il lotto di E con i contatori email è già nel treno 10: base pulita, già fast-forward).
**Corsia**: porta `6185`, cartella dati `/tmp/librefolio-r13-a`.
**Piano**: `LibreFolio_developer_journal/Release_2/Phase_1/02_accounts/plan-phase01Accounts.prompt.md` (sezione nuova «Ondata 5»). Recap della sera 22/10 §7.4 (admin titolare) nel piano dell'ondata 4 (`ondata4/PIANO-ondata4.md`, grep «managed»). Skill: `devpy-i18n`, `design-system`.

## Cosa fare (nell'ordine; treno **11a** per entrambi)
1. **A5-1 · l'admin titolare, protezione** (PARTI SUBITO con l'analisi, 0,5 giorni). Riempi lo stub `account_protection` (`accounts/user_service.py:842-848`): protetto chi ha l'email di `LIBREFOLIO_ADMIN_EMAIL` (`config/accounts.py:107`) **solo nel profilo `managed`** (`config/__init__.py:295`). Il resto è già cablato: 409 `ACCOUNT_PROTECTED` in `api/v1/users.py:107-112`, controllato alla PATCH (`:221`: disattiva, annulla setup, declassa) e alla DELETE (`:282`); `AdminUserRead.protected` in `schemas/users.py:53`; `UserRow` mostra già il badge. **La CLI** (`scripts/user_cli.py:254-290`) chiama i servizi direttamente e **resta sopra** la protezione, come vuole il developer (è l'uscita d'emergenza: scrivi un test che lo fissa). Prima i rossi (con `test-author`; `api users-admin`): nel `managed` l'admin del titolare non si può eliminare/disattivare/declassare; negli altri profili nessun effetto (regressione zero); un altro admin sì; la CLI sì. **Revisione Opus**: a checkpoint pronto lancia un sotto-agente `Agent` con `model: "opus"` sul tuo diff (senza darti ragione: dagli il codice, non la conclusione), 30 minuti, e riporta nel checkpoint l'esito; il coordinatore può ripeterla.
   **Da decidere nell'analisi** (è una scelta di prodotto: **domanda**, vedi sotto): proteggere anche il **reset password** e la **revoca sessioni** dell'admin titolare (`users.py:302`, `:317`: oggi fuori).
2. **A5-2 · la funzione per il titolare e la modale** (dopo A5-1, 1-1,5 giorni).
   - **Primo messaggio (subito, prima del codice)**: la **firma** della funzione di servizio e il suo comportamento, così **B** può scrivere B5-1 contro la firma (e provare con una funzione finta). Esempio di firma: `assign_owner_email_and_send_reset(user_id) -> OwnerResetResult` con i casi (inviato / SMTP spento → link da mostrare / utente non trovato / già fatto = idempotente).
   - La funzione, in `accounts/user_service.py` (una funzione) e `email/flows.py`: **assegna l'email del titolare** all'utente scelto (nessun precedente «cambia l'email di un utente senza verifica + reset forzato»: scrivilo bene), lo rende **admin**, **protetto** (A5-1), **crea il link** di reset (`create_password_reset`, `users.py:302-314`; `build_password_reset` `email/messages.py:150`; `send_link_email(..., purpose="password_reset")` `email/flows.py:138`) e **spedisce**. **Idempotente** (B la chiama dopo lo scambio, al primo avvio: un riavvio a metà non deve spedire due link né rompersi).
   - **Caso «SMTP spento nel managed»** (il link non parte): da risolvere nell'analisi; **consiglio**: il link stampato nel rapporto del ripristino, come fa la CLI. Mettilo in domanda al developer solo se la scelta non è ovvia.
   - La **modale della scelta** (UI): **componente nuovo** in `frontend/src/lib/features/backup/` (cartella **di B**: tu consegni il file nuovo, **B lo monta**): propone l'utente con l'email del titolare; se c'è, scelta obbligata; avviso («a questo utente verrà messa l'email del titolare e la password verrà reimpostata via link email»); 4 lingue (`./dev.py i18n`). Non toccare gli altri file di `features/backup/**`.
   - Rossi: servizio (`api users-admin` o la categoria che trovi giusta: email del titolare messa, admin, protetto, link creato e spedito, idempotenza, SMTP spento), Vitest della modale; E2E della modale lo consegna **B** con il suo montaggio.
   - **Non** per i ripristini del pannello (copie notturne): nessun gancio lì.

## Dipendenze da altre sessioni
- **A5-1 → A5-2** (stesso file `user_service.py`). **A → B**: firma presto, funzione e modale committate prima del ripristino di B. **Opus** rivede A5-1.
- H legge `registration_service.user_usage()` (H5-1): non cambiarne la firma né il risultato.

## File condivisi
- **Tuoi**: `backend/app/services/accounts/{user_service,bootstrap_admin_service}.py`, `api/v1/users.py`, `services/email/flows.py`, `features/settings/users/UserRow.svelte`, `i18n/email`, `i18n/auth`; un file nuovo in `features/backup/` (la modale).
- **Di altri**: `features/backup/**` (tutto il resto), `instance_backup/**`, `api/v1/backup/**` (**B**); `panel_restore.py`, `panel.py`, `hosting_panel/**` (**H**).

## Non fare
- Nessuna protezione fuori dal profilo `managed`. Nessun clean-up dei ruoli esistenti. Non proteggere la CLI. Niente password o link in chiaro nei log. Non cambiare i ripristini del pannello.
- Non toccare le migrazioni (se la funzione ne chiede una, fermati e dillo).

## Domande
1. **Dopo l'analisi di A5-1 (da portare al developer)**: l'admin titolare, oltre a non poter essere eliminato/disattivato/declassato, deve essere protetto anche dal **reset password** (da un altro admin) e dalla **revoca delle sue sessioni**? Scrivi il tuo consiglio e un esempio (un admin secondario che resetta la password del titolare = «presa dell'account»). Il resto procede intanto.

## Fatto quando
A5-1: rossi→verdi (`api users-admin`, Vitest di `UserRow` invariato o aggiornato), E2E `settings` nello slot, revisione Opus riportata. A5-2: firma consegnata presto, funzione e modale rossi→verdi, `i18n check`, `front check` 0/0 (dopo `api sync`), ratchet dei colori pulito, doc in inglese (docs-writer: `admin/` dove l'admin titolare è spiegato, una frase; **la sezione del ripristino con scelta del titolare la scrive B** in `backup_restore.en.md`), piano aggiornato. Righe CHANGELOG proposte: ✨ «nel profilo managed l'admin titolare non si può eliminare, disattivare né declassare» (A5-1); ✨ «ripristinando un backup tuo scegli quale utente diventa l'admin titolare; la password si reimposta con un link email» (A5-2, la riga la unisce il coordinatore a quella di B). Checkpoint: A5-1 · **firma di A5-2 (messaggio)** · A5-2, ciascuno con **CHECKPOINT READY** e **FROZEN**.
