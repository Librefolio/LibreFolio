# A5-1b parte 2 · richieste a H (file di H) — 23/10/2026

Il cambio dell'email del titolare avviato dall'host (`services/accounts/instance_owner.py`, A) lascia due letture per il resto della piattaforma. Nessun indirizzo esce mai da nessuna delle due.

## 1. `GET /panel/status` — il coordinatore cloud vede «cambio del titolare in attesa di conferma»
- `backend/app/schemas/hosting_panel.py:58` (`PanelStatusResponse`): campo nuovo, dopo `admin_setup`/`setup_expires_at`:
  `owner_email_change: Literal["pending", "blocked"] | None = Field(None, description="The change of the paying administrator's email address that the hosting provider started by changing LIBREFOLIO_ADMIN_EMAIL: pending, the new address was sent a confirmation link and the account keeps the old one until it is clicked; blocked, another account already holds the new address, so nothing changes; null, no change is waiting (or the instance is not managed, or its initial administrator has not set up yet). Never the address.")`
  (`extra="forbid"` resta: il campo va dichiarato; il docstring dice «and nothing else»: aggiornarlo.)
- `backend/app/api/v1/panel.py:49` (`get_panel_status`): riempirlo con
  `owner_email_change=await instance_owner.owner_change_status(session)`
  (`from backend.app.services.accounts.instance_owner import owner_change_status`). Sola lettura, async, nessun indirizzo. Un cambio `pending` non è un errore: il pannello lo mostra finché il titolare non clicca; `blocked` chiede un intervento dell'host (cambiare di nuovo la variabile con un indirizzo libero).
- Test di H: `panel-status` (aggiungere il campo alle forme attese) e la doc del pannello.
- Perché: l'host cambia la variabile e riavvia, poi non sa se il titolare ha confermato; senza il campo dovrebbe chiedere al cliente.

## 2. `GET /security/checks` — un controllo nuovo `accounts.owner_email_change`
- `backend/app/services/accounts/checks.py` è di A, ma i test che fissano l'elenco dei controlli e `checkGuides.json` sono di H, quindi lo chiedo a H (così nessun test di H diventa rosso in un commit di A):
  - `checks.py`: `check_owner_email_change()` accanto a `check_login_limit`, in `ACCOUNTS_CONFIG_CHECKS`; legge **in memoria** `instance_owner.startup_change_state()` (sincrono, nessun database: `"pending"` | `"blocked"` | `None`):
    - `None` → `ok`, chiave `auth.checks.ownerEmailChange.ok`;
    - `"pending"` → `info`, `auth.checks.ownerEmailChange.pending` («The hosting provider changed the owner's email address: the new address was sent a confirmation link, and the account keeps the old one until it is confirmed.»);
    - `"blocked"` → `warning`, `auth.checks.ownerEmailChange.blocked` («The hosting provider changed the owner's email address to one that another account already uses: nothing was changed. Choose another address and restart.»).
    Mai l'indirizzo né il nome utente nel risultato. I testi 4 lingue li scrive A (`./dev.py i18n add`, sorgente `auth`) appena H conferma il nome del controllo.
  - `frontend/src/lib/features/instance/checkGuides.json`: `"accounts.owner_email_change": "admin/hosting_providers/#owner-email-change"` (l'ancora c'è già in `hosting_providers.en.md`, sezione «Changing the Administrator's Address»; le traduzioni di quella pagina non hanno ancora l'ancora: debito di traduzione, come per `#panel-api`), e il suo test (`checkGuides.test.ts`, `EXPECTED_GUIDES` oggi 20) + `test_config_audit.py` (elenco degli id e dell'ordine).
- Perché: il conflitto («l'indirizzo nuovo è già di un altro account») deve comparire nei controlli di sicurezza dell'admin, oltre che nel log.

## Cosa NON serve a H
- Nessuna migrazione, nessun nuovo endpoint del pannello. `startup_change_state()` e `owner_change_status(session)` stanno in `backend/app/services/accounts/instance_owner.py`.
