# DOC-1 — riordino della guida admin: inventario e proposta d'albero (H, 23/10/2026, base `1fd80c481`)

Sola lettura: nessuna pagina toccata. L'elenco delle pagine, delle intestazioni e dei riferimenti l'ha raccolto un sotto-agente
Haiku; ho controllato io i conteggi e gli ancoraggi che contano (indicati sotto).

## 1. Le pagine di oggi (14 inglesi + 27 traduzioni)

| Pagina (`admin/<nome>.en.md`) | Righe en | it | fr | es | Argomenti (H2) |
|---|---|---|---|---|---|
| `hosting_providers` | **1340** | — | — | — | profilo managed · amministratore iniziale · blocco · API del pannello (token, biglietti, vettori, stato) · backup del pannello · ripristino dal pannello (modo, rotte, stato illeggibile) · limite di upload · pagine legali |
| `configuration` | **1009** | 126 | 156 | 158 | `.env` · opzioni · segreti e chiave d'istanza · impostazioni dei plugin · controlli d'avvio · protezioni del browser (CSP) · arresto · account e iscrizioni (utenti, limite, accessi, amministratore iniziale) · ordine dei provider · ricerca web |
| `email` | **908** | — | — | — | dove vive la configurazione · variabili · esempi · link nelle email · scheda Email · link dell'admin · password dimenticata · limiti · verifica · cambio indirizzo · problemi · note di sicurezza |
| `backup_restore` | **772** | — | — | — | contenuto · fare un backup · backup protetti · **sigillati** · controllo · ripristino · portare altrove · problemi (file di **B**) |
| `cli_tools` | **770** | 185 | 185 | 185 | avvio · utenti · database · **backup** (≈ 430 righe) · albero dei comandi (file di **B**) |
| `service_exposure` | **639** | 629 | 629 | 618 | Tailscale: perché · passo 0 · livello 1 (VPN) · livello 2 (subnet) · Funnel e ACL · livello 3 (HTTPS pubblico) · livello 4 (multi-Funnel con Docker) · MagicDNS |
| `sleep_wake` | **605** | — | — | — | sospensione per inattività · sveglia programmata · prezzi che recuperano · controllo · pause dei provider |
| `connection_checks` | 465 | 254 | 267 | 260 | lista di controllo · indicatore · vista del server · cookie · reverse proxy (≈ 250 righe) · limiti |
| `users` | 409 | — | — | — | |
| `docker_advanced` | 370 | 356 | 356 | 356 | |
| `settings` | 366 | 164 | 166 | 166 | |
| `filesystem` | 174 | 138 | 138 | 138 | |
| `host_installation` | 140 | 140 | 140 | 140 | |
| `index` | 102 | 82 | 76 | 93 | |

**Le traduzioni sono più corte dell'inglese** (configuration 126-158 contro 1009, cli_tools 185 contro 770): sono già
«indietro» e non specchiano la struttura; dividere l'inglese non le rompe.

Navigazione (`mkdocs.yml` righe 967-986): tre gruppi, «Deployment & Exposure» (6 pagine), «System Configuration» (4),
«Maintenance & Operations» (3), più «Overview». Tutte le 14 pagine sono in nav.

## 2. Chi usa le pagine admin dall'esterno (le ancore da conservare)

**Nel codice** (`/mkdocs/admin/<pagina>/#<ancora>`; la forma è fissata da un test: `^admin/([a-z0-9_]+)/#([a-z0-9-]+)$`, cioè
**una pagina piatta** `admin/<nome>/`, senza sottocartelle: ne tengo conto nei nomi):
- `frontend/src/lib/features/instance/checkGuides.json` — **21 voci** dei pulsanti «Guida» della scheda Sicurezza:
  `configuration#secrets` · `#secret-files` · `#instance-key` · `#frame-protection` · `#csp-report-only` · `#startup-checks` ×2 ·
  `#login-limit` · `#plugin-secrets` · `#csp`; `connection_checks#session-cookie` · `#untrusted-proxy` (H4);
  `hosting_providers#panel-api` · `#panel-token` · `#restore-upload-limit` ×2; `backup_restore#sealed`; `email#variables` ·
  `#encryption-modes` · `#links-check`; `settings#open-registration-warning`.
- `frontend/.../cspNotice.ts:25,124` — il messaggio di violazione della CSP porta `configuration#csp` (con ripiego `admin/configuration/`).
- `frontend/.../EmailSettingsTab.svelte:118` — pagina `email/` (senza ancora).
- `frontend/.../InstanceRestoreInterruptedPage.svelte:43` — `cli_tools#backup-pending-unreadable` (H4).
- `README.md:159,181` — `host_installation`, `docker_advanced` (pagine intere, non cambiano).
- Test che li fissano: `checkGuides.test.ts` (tabella delle 21 voci), `SecurityTab.test.ts`, `cspNotice.test.ts`,
  `EmailSettingsTab.test.ts`, `InstanceRestoreInterruptedPage.test.ts`, `backend/test_scripts/test_services/test_config_audit.py`
  (legge `checkGuides.json`) e `test_hosting_panel_vectors.py` (legge **`hosting_providers.en.md`**, `#panel-api-test-vectors`).
- Backend (`backend/app`, `dev.py`): **nessun** riferimento a pagine admin.

**Dalla documentazione stessa** (pagine non-admin → admin): 239 link in 71 file, dei quali **con ancora in pagine che si
dividerebbero**: `configuration` 47, `hosting_providers` 84 (di 88), `email` 23, `backup_restore` 16, `cli_tools` 36,
`sleep_wake` 34, `connection_checks` 28, `service_exposure` 0. **Tutti i link con ancora verso le pagine che si dividono vengono
da file inglesi** (developer, user EN): le traduzioni it/fr/es puntano solo a pagine intere o ad ancore che non si spostano
(`settings#…`, `cli_tools#reset-a-password-or-lock-an-account` che sta nella parte che resta, `filesystem#backup`): **non serve
toccare nessun file tradotto**.

Ancore da tenere d'occhio: due sono automatiche (senza `{: #id }`: `cli_tools#reset-a-password-or-lock-an-account`,
`filesystem#backup`); due sono su H4 (`connection_checks#untrusted-proxy`, `cli_tools#backup-pending-unreadable`).

## 3. La proposta d'albero

**Regola**: nessuna pagina oltre ~450 righe; una pagina per argomento. Si divide **solo** ciò che supera ~600 righe, più il
reverse proxy di `connection_checks` (argomento a sé, 250 righe). Le pagine **restano piatte** (`admin/<nome>/`) perché la forma
degli indirizzi è fissata dai test e dall'app; la **gerarchia sta nella navigazione** (sottogruppi), non nelle cartelle.
Il nome della pagina di oggi resta alla **prima parte**, così gli indirizzi senza ancora (`admin/configuration/`) continuano a
funzionare e i link delle traduzioni non si rompono.

| Oggi | Diventa | Righe ≈ | Ancore che si spostano |
|---|---|---|---|
| `hosting_providers` (1340) | **`hosting_providers`**: profilo managed + pagine legali | 300 | `legal-pages` resta qui |
| | **`hosting_instances`**: amministratore iniziale + blocco | 300 | `initial-admin*`, `instance-block`, `block-variables`, … |
| | **`hosting_panel_api`**: token, biglietti, vettori, stato, avvio | 360 | `panel-api*`, `panel-status` |
| | **`hosting_panel_backups`**: backup, ripristino, modo, limite di upload | 385 | `panel-backups`, `panel-token`, `panel-restore*`, `await-restore*`, `restore-interrupted`, `restore-upload-limit` |
| `configuration` (1009) | **`configuration`**: `.env`, opzioni, «quale valore vince», dove vanno i dati | 270 | |
| | **`configuration_secrets`**: segreti, file, chiave d'istanza, plugin | 250 | `secrets`, `secret-files`, `instance-key`, `plugin-*` |
| | **`configuration_security`**: controlli d'avvio, CSP, frame, report-only, arresto | 320 | `startup-checks`, `csp`, `frame-protection`, `csp-report-only`, `shutdown` |
| | **`configuration_accounts`**: account e iscrizioni, ordine dei provider, ricerca web | 250 | `accounts`, `user-limit`, `login-limit`, `initial-admin`, `provider-order` |
| `email` (908) | **`email`**: configurazione, variabili, esempi, scheda Email | 380 | `where-it-lives`, `variables`, `encryption-modes`, `examples`, `email-tab`, `links-check` |
| | **`email_flows`**: link, password dimenticata, limiti, verifica, cambio indirizzo | 330 | `public-url`, `admin-links`, `forgot-password`, `verification*`, … |
| | **`email_troubleshooting`**: problemi, log, note di sicurezza | 200 | `troubleshooting`, `logs`, `security` |
| `backup_restore` (772) — **B** | **`backup_restore`**: contenuto, fare, protetti, controllo, ripristino | 320 | |
| | **`backup_sealed`**: backup sigillati | 220 | `sealed*` |
| | **`backup_moving`**: portare altrove + problemi | 240 | `bring-home`, `troubleshooting`, … |
| `cli_tools` (770) — **B** | **`cli_tools`**: avvio, utenti, database, albero dei comandi | 330 | |
| | **`cli_backup`**: «Back Up the Instance» (archivio, protetto, sigillato, prova, ripristino, `pending`) | 440 | `backup*`, `backup-pending*` |
| `service_exposure` (639) | **`service_exposure`**: Tailscale: perché, passo 0, livelli 1-2, MagicDNS | 220 | |
| | **`service_exposure_funnel`**: Funnel e ACL, livello 3, livello 4 (Docker) | 420 | `enabling-funnel-and-acls-on-the-console`, `3-startup-and-approval` |
| `sleep_wake` (605) | **`sleep_wake`**: sospensione, controllo, pause dei provider | 300 | `idle-suspend*`, `check-it-works`, `provider-pauses*` |
| | **`wake_sync`**: sveglia programmata, prezzi che recuperano | 270 | `wake-sync*`, `price-refresh` |
| `connection_checks` (465) | **`connection_checks`**: lista, indicatore, vista del server, cookie, limiti | 210 | |
| | **`connection_proxy`**: reverse proxy e indirizzo del visitatore | 250 | `reverse-proxy`, `client-address`, `untrusted-proxy` |
| invariate | `users` 409, `docker_advanced` 370, `settings` 366, `filesystem` 174, `host_installation` 140, `index` 102 | | |

Risultato: **14 → 28 pagine**, la più lunga ≈ 440 righe (oggi 1340). Le due guide Tailscale:
`service_exposure` 639 → 220 + 420; `connection_checks` 465 → 210 + 250.

**Navigazione proposta** (la applica il coordinatore; sottogruppi dentro i tre di oggi):
- 🐳 Deployment & Exposure → Host Installation · Advanced Docker · **Expose Securely** (service_exposure, service_exposure_funnel) · **Check Connection Security** (connection_checks, connection_proxy) · **Hosting for Others** (4 pagine) · **Sleep and Wake** (sleep_wake, wake_sync).
- ⚙️ System Configuration → **Environment Variables** (4 pagine) · **Email** (3) · Global Settings · Users & Invitations.
- 🧹 Maintenance & Operations → **CLI Admin Tools** (cli_tools, cli_backup) · **Backup, Restore & Moving** (3) · Filesystem Structure.

## 4. Come si tengono vive le ancore

1. **Aggiornare i riferimenti dell'app** (tutti miei, 21 voci + 5 punti + i test): `checkGuides.json` per le voci che cambiano pagina
   (≈ 14 di 21), `cspNotice.ts` (`configuration#csp` → `configuration_security#csp`), `InstanceRestoreInterruptedPage.svelte`
   (`cli_tools#backup-pending-unreadable` → `cli_backup`), i loro test, e `test_hosting_panel_vectors.py` (legge la pagina
   dei vettori). Una **prova**: un test che per OGNI riferimento dell'app (`checkGuides.json`, le costanti dei componenti)
   costruisce l'indirizzo e verifica che pagina e ancora esistano nel sito costruito.
2. **I link dentro la documentazione**: uno script (dalla mappa «pagina vecchia#ancora → pagina nuova#ancora» generata dai titoli)
   riscrive i link inglesi (≈ 270 link con ancora verso le pagine che si dividono, nei file inglesi); `mkdocs build --strict`
   (ancore: `warn`) dice se ne resta uno rotto.
3. **I link esterni** (README, segnalibri, post): le pagine vecchie restano, quindi gli indirizzi senza ancora funzionano. Per le
   ancore che si spostano propongo uno **script di reindirizzamento** (`docs/javascripts/moved-anchors.js`, senza dipendenze,
   caricato come gli altri; una mappa `{pagina vecchia: {ancora: pagina nuova}}`): chi apre `…/configuration/#csp` finisce su
   `…/configuration_security/#csp`. `mkdocs.yml` non ha il plugin dei reindirizzamenti e non ne aggiungo (nessuna dipendenza
   nuova). Un test controlla che la mappa sia **completa**: ogni ancora della pagina vecchia (elenco congelato dal commit di
   partenza) o resta nella sua pagina o è nella mappa, e la pagina nuova la contiene.
4. **Le traduzioni**: restano com'è (debito dichiarato). Le pagine nuove esistono solo in inglese: sotto `/it/` appaiono come
   copie inglesi di ripiego (come oggi le pagine solo-inglesi). Elenco del debito: le 4 pagine con traduzione che si dividono in
   inglese (`configuration`, `cli_tools`, `service_exposure`, `connection_checks`) più i titoli di nav nuovi (`nav_translations` di
   `mkdocs.yml`, in it/fr/es) per i nomi dei sottogruppi.

## 5. Ordine e tempi (uno scrittore per file)

Aspetto il via del coordinatore: i commit di **B** (`backup_restore`, `cli_tools`, `install*`), di **X** (pagine dei provider) e il
mio **H5-1** (`hosting_providers.en.md`). Poi, nell'ordine: configurazione (la meno toccata) → email → service_exposure,
connection_checks, sleep_wake → hosting → backup e CLI (dopo B). Lavoro: **2,5-3 giorni** con il `docs-writer` (solo inglese);
ogni passo chiude con `mkdocs build --strict`, `check-links` e il test delle ancore.

## 6. Domande
1. L'albero va bene? In particolare: **28 pagine** (la più lunga ≈ 440 righe), pagine **piatte** con la gerarchia nella nav, il
   reverse proxy separato da `connection_checks`.
2. I **reindirizzamenti delle ancore con uno script JS** (nessuna dipendenza) vanno bene, o preferisci non averli e solo link
   aggiornati?
3. Posso scrivere anche i titoli di nav in it/fr/es (`nav_translations`, `mkdocs.yml`) o restano debito?
