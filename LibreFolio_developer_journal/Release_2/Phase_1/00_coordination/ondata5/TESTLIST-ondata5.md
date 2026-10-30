# Testlist manuale — ondata 5 (release 1.3.0)

Fonti: `RECAP-ondata5.md` e i commit dei rami dell'ondata sopra `94672e66c` (50 commit senza unioni, deduplicati), più i 58 commit senza unioni tra `48bd230d1` e `8f7282ff6`. Letta il 27/10/2026.

**Come si usa.** Spunta `- [ ]` quando la prova è passata. Se non passa, scrivi sotto la voce cosa hai visto. Ogni voce ha un codice del lotto, passi brevi e **Atteso**.

**Stato (aggiornato dal coordinatore a ogni lotto committato):** ✅ pronta, 27/10/2026, commit `8f7282ff6` (il candidato del treno 11). Il gate è verde: API del backend tutto e all-frontend 9/9, alle 16:27, a macchina tranquilla. Fuori da questa lista restano solo i treni 9 e 10 (§9).

## Dove e quando si prova

**Branch: `train11b`**, nel worktree `gate-coord`. È l'unico posto dove tutti i rami dell'ondata 5 sono uniti insieme: A, B, H, J, MF, W, W2, X, Y, Z. I rami singoli (`e-alfy-…`) non vanno bene, perché ognuno ha solo una parte; per esempio Y5-2 senza i dati di J e MF non si vede intero. **Non provare su `dev_release2`:** lì l'ondata 5 non c'è ancora.

| Cosa | Valore |
|---|---|
| Cartella | `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/gate-coord` |
| Branch | `train11b` |
| Commit da provare | `8f7282ff6` (unione `test(instance-key)` in `train11b`) |
| Ambiente Python | `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc` (lo stesso venv del checkout principale) |

**Comandi, una volta per sessione di prova** (un terminale per il server, uno per i comandi):

```bash
cd /home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/gate-coord
```

```bash
git status -sb
```

Deve dire `## train11b` e nessun file modificato. Poi:

```bash
git log --oneline -1
```

L'hash deve essere quello scritto nella tabella sopra.

```bash
export PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc PIPENV_VERBOSITY=-1
```

Le dipendenze del frontend servono solo se mancano o se il coordinatore lo segnala:

```bash
(cd frontend && npm ci)
```

**DB di test ad hoc** (gruppi 2-B5-2, 3-X-R84, 4, 5, 6 e 7 tranne i dati veri):

```bash
pipenv run python dev.py test db populate --force --clean --with-reports
```

```bash
pipenv run python dev.py server --test --rebuild
```

Apri `http://localhost:6041`. Il primo avvio ricostruisce il frontend del candidato e ci mette qualche minuto. `--rebuild` serve a non vedere il frontend di un treno vecchio.

**Istanza «managed» a perdere** (gruppi 1, 2 e 3-H5-1, H5-6, H5-7, H5-8): §0.3, con i comandi lanciati da questa stessa cartella e `pipenv run python dev.py …` al posto di `./dev.py …`.

**Copia dei dati veri** (Y5-2, D-P4, Z-14b, Yahoo): la prepara il coordinatore quando sei pronto. Te la crea su `/tmp/librefolio-r2-ondata5-realdata` e ti dà il comando del server (porta 6151).

**Documentazione** (gruppo 8):

```bash
pipenv run python dev.py mkdocs serve
```

Apri `http://localhost:6042`.

**Alla fine:** ferma i server con Ctrl+C. Il DB di test resta nella cartella del worktree (`backend/data/test/`) e non tocca la produzione.

Nei passi qui sotto `./dev.py …` vuol dire `pipenv run python dev.py …`, lanciato dalla cartella `gate-coord`.

**Dove non sono sicuro** della posizione nell'interfaccia lo scrivo: «posizione da confermare».

---

## 0. Preparazione

### 0.1 Quale database per quale gruppo

| Gruppo | Database | Perché |
|---|---|---|
| 1. Account e accessi (A5-1, A5-4, A5-6, A5-7) | **Istanza a perdere «managed»** (cartella `/tmp/lf-ondata5-managed`, porta 6141; per A5-6 una cartella nuova, vedi la voce) | Il titolare protetto esiste solo col profilo `managed`. Il server di prova (`--test`) **butta via** `LIBREFOLIO_ADMIN_EMAIL`, `JWT_SECRET` e gli altri `LIBREFOLIO_*` (solo `LIBREFOLIO_PROFILE` passa, con `--lane-setting`): quindi qui non va bene. |
| 2. Backup e ripristino (voci B5-1, A5-2, A5-5, B5-1j, B5-1k2) | Stessa istanza a perdere | Il ripristino con scelta del titolare vale solo nel `managed`. |
| 2. Backup e ripristino (voce B5-2) | **DB di test ad hoc** (`backend/data/test`) | Basta un file di stato finto: non serve un'istanza vera. |
| 3. Pannello hosting e istanza | Stessa istanza a perdere (H5-1, H5-6, H5-7, H5-8); DB di test (X-R84) | `panel/status` chiede il token e i limiti del `managed`. |
| 4. Import e Bulk, form transazioni | **DB di test ad hoc** | I file campione danno risultati noti; niente dati personali. |
| 5. Plugin, asset, impostazioni | **DB di test ad hoc**; solo la prova Yahoo usa la **copia dei dati veri** | Serve la rete e un asset Yahoo vero. |
| 6. Cruscotto e grafici | **Copia dei dati veri** per Y5-2, D-P4 e Z-14b; DB di test per le altre | I grafici per posizione hanno senso su anni di storia vera. |
| 7. Numeri e analisi | **DB di test ad hoc** | Gli esempi sono piccoli e controllabili a mano. |
| 8. Documentazione | Nessuno (`./dev.py mkdocs serve`) | Solo il sito. |

### 0.2 DB di test ad hoc

```bash
./dev.py test db populate --force --clean      # dati di prova + utenti
./dev.py server --test                         # porta 6041
```

- Utenti: `e2e_test_user` / `E2eTestPass123!` (normale) e `e2e_test_admin` / `E2eAdminPass123!` (admin).
- Cartella dati: `backend/data/test/` (la usano anche `./dev.py user --test-db …` e `./dev.py backup --test-db …`).
- File campione dei broker: `backend/app/services/brim_providers/sample_reports/` (elenco in `README.md`). Servono: `etoro-export.csv`, `swissquote-export.csv`, `revolut-invest-export.csv`, `trading212-export.csv`.
- Un file di prova per lo split di Trading 212 (il campione contiene solo uno split **inverso**, che non si importa). Salvalo come `/tmp/t212-split.csv` (19 colonne, intestazione uguale al campione):

```csv
Action,Time,ISIN,Ticker,Name,No. of shares,Price / share,Currency (Price / share),Exchange rate,Result,Currency (Result),Total,Currency (Total),Withholding tax,Currency (Withholding tax),Notes,ID,Currency conversion fee,Currency (Currency conversion fee)
Deposit,2023-12-18 11:45:06.326,,,,,,,,,,31.00,EUR,,,,SYNTH-D-1,,
Stock split close,2025-03-24 07:24:24.095,CA46500E8678,ISOU,IsoEnergy,10.0000000000,,,,,,0.00,EUR,,,,SYNTH-C,,
Stock split open,2025-03-24 07:24:24.104,CA46500E8678,ISOU,IsoEnergy,30.0000000000,,,,,,0.00,EUR,,,,SYNTH-O,,
```

### 0.3 Istanza a perdere «managed» (porta 6141)

Tutto sotto `/tmp`, mai sui dati di produzione. Mettila in un file `/tmp/lf-ondata5-managed.env` e fai `source` ogni volta (i valori devono restare **uguali** a ogni riavvio, `JWT_SECRET` compreso):

```bash
export LIBREFOLIO_DATA_DIR=/tmp/lf-ondata5-managed      # senza questa riga i comandi CLI toccano la produzione
export LIBREFOLIO_PROFILE=managed
export JWT_SECRET='<64 caratteri casuali>'
export LIBREFOLIO_ADMIN_EMAIL=titolare@prova.example
export LIBREFOLIO_ADMIN_USERNAME=titolare
export LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN='<32 o più caratteri>'
export LIBREFOLIO_PUBLIC_URL=http://localhost:6141
export LIBREFOLIO_PANEL_STATUS_TOKEN='<32 o più caratteri>'
export LIBREFOLIO_MAX_USERS=5
```

```bash
source /tmp/lf-ondata5-managed.env
./dev.py server --port 6141 --data-dir /tmp/lf-ondata5-managed --no-scheduler --no-reload
```

- Il primo avvio costruisce il frontend: ci vuole un po'. La posta non è configurata: i link escono nel **log del server** (un `warning`). Tienilo visibile.
- Primo accesso: apri `http://localhost:6141/setup#token=<il token>`, scegli la password del titolare (`titolare`), entra.
- Il ripristino **ferma** il server e non lo riavvia da solo: rilancia a mano lo stesso comando.
- Fine prove: ferma il server e cancella `/tmp/lf-ondata5-managed`.
- Per i comandi CLI sulla stessa cartella: nella stessa shell con `source` fatto, per esempio `./dev.py user list`. Se un comando non prende la cartella, aggiungi `--data-dir` (posizione da confermare).
- Altro admin per le prove: `./dev.py user create altro altro@prova.example <password-prova>` (crea un amministratore).
- Utente normale per le prove: `./dev.py user create u1 u1@prova.example <password-prova> --role user`.
- Alcune voci (A5-6, H5-6) toccano il database di questa istanza con `sqlite3 /tmp/lf-ondata5-managed/sqlite/app.db "…"` (la riga `sqlite/app.db` è quella scritta nella guida dei file dati; il comando `sqlite3` va installato se manca). Solo su questa copia sotto `/tmp`, mai su `backend/data/prod`.
- Per le voci che leggono lo stato dell'istanza: `curl -sS -H "Authorization: Bearer $LIBREFOLIO_PANEL_STATUS_TOKEN" http://localhost:6141/api/v1/panel/status` (con `source` fatto).

### 0.4 Copia dei dati veri

La crea il coordinatore con la skill `real-data-copy` (da produzione, a server spento, solo copie). Percorso suggerito: `/tmp/librefolio-r2-ondata5-realdata`; porta suggerita: 6151, con `--no-scheduler` salvo dove scritto. **Non lanciare mai `dev.py test` su questa copia** (la distrugge).

---

## 1. Account e accessi (istanza `managed`, §0.3)

- [ ] **A5-1 — Il titolare che paga è protetto**
  1. Dopo il setup, crea un secondo admin: `./dev.py user create altro altro@prova.example <password-prova>`.
  2. Entra come `altro`. Apri **Settings › Administration › Users**: guarda la riga del titolare.
  3. Prova i pulsanti della riga: eliminare, disattivare, togliere i diritti, **Reset link**, **Sign out**.
  4. Esci. Entra come `titolare`: **Settings › Profile**. Prova a cambiare l'email e scrivi la password attuale, poi salva.
  5. Sempre nel profilo prova a eliminare il tuo account.
  6. Cambia la password e lo username del titolare (devono funzionare).
  7. Da terminale: `./dev.py user demote titolare`, poi `./dev.py user promote titolare` (la riga di comando resta sopra la protezione).
  - **Atteso:** sulla riga del titolare c'è il badge **Protected**; eliminare, disattivare e togliere i diritti sono spenti con il motivo; **Reset link** e **Sign out** sono spenti (nuovo in A5-1). Nel profilo, il cambio email apre una finestra che spiega che l'indirizzo lo cambia l'host, con un link alla pagina di fatturazione, oppure all'indirizzo di supporto, oppure nessun link. La finestra è una sola, niente errore nudo. L'eliminazione dell'account è rifiutata (409, messaggio «ask the host»). Password e username si cambiano. I comandi da terminale funzionano (è l'uscita di emergenza).

- [ ] **A5-1b + H5-4 — Cambio email del titolare dall'host, con conferma**
  1. Con il titolare entrato (per vedere che la sessione termina), ferma il server. In `/tmp/lf-ondata5-managed.env` cambia `LIBREFOLIO_ADMIN_EMAIL=nuovo@prova.example`. Riavvia con lo stesso comando.
  2. Nel log cerca il `warning` «Confirmation link for the instance owner's new email address» e copia il link (`…/confirm-email-change#token=…`).
  3. Controlla lo stato: `curl -sS -H "Authorization: Bearer $LIBREFOLIO_PANEL_STATUS_TOKEN" http://localhost:6141/api/v1/panel/status`.
  4. Entra come titolare (ancora con la vecchia email): **Settings › Administration › Security**, cerca il controllo «accounts.owner_email_change».
  5. Riavvia ancora: nel log **non** deve uscire un secondo link.
  6. Apri il link in una finestra privata, **senza cliccare**. Poi torna al punto 3.
  7. Clicca il pulsante di conferma.
  8. Prova ad accedere con `nuovo@prova.example` e la **stessa** password di prima. Prova anche con la vecchia email.
  - **Atteso:** al punto 3 `"owner_email_change":"pending"` (mai l'indirizzo). Al punto 4 una riga informativa (livello `info`) che dice che il cambio aspetta la conferma. Al punto 6 la pagina mostra solo il pulsante, e lo stato resta `pending`: aprire il link non conferma. Dopo il clic (7) si va alla pagina di accesso con un messaggio, tutte le sessioni del titolare sono chiuse. Al punto 8 entra la nuova email, con la password di prima; la vecchia non entra. Lo stato torna `null` e il controllo sparisce. Finché non clicchi, il titolare resta con la vecchia email e protetto.
  - **Esempio:** vecchia `titolare@prova.example` → nuova `nuovo@prova.example`; il link vale 7 giorni e si può usare una volta sola; riaprirlo dopo l'uso dice «già usato» (stato `consumed`).

- [ ] **A5-1b — Indirizzo nuovo già usato da un altro account (stato «blocked»)**
  1. Il titolare ha ora `nuovo@prova.example` (dopo la voce precedente). Con `./dev.py user set-email altro altro2@prova.example` dai all'altro admin un indirizzo libero.
  2. Ferma il server. Metti in `LIBREFOLIO_ADMIN_EMAIL` proprio `altro2@prova.example`. Riavvia.
  3. Guarda il log, `panel/status` (come sopra) e **Settings › Administration › Security**.
  4. Rimetti `nuovo@prova.example` in `LIBREFOLIO_ADMIN_EMAIL` e riavvia.
  - **Atteso:** nel log un errore che dice che `LIBREFOLIO_ADMIN_EMAIL` appartiene a un altro account e **nessun link** è emesso. `panel/status` dà `"owner_email_change":"blocked"`. Nel controllo di sicurezza c'è un **warning** (non più `info`). Il titolare tiene indirizzo e protezione; l'altro account **non** diventa protetto. Dopo il punto 4 lo stato torna `null`.

- [ ] **A5-4 — `user reassign-owner`: ridare l'istanza al titolare dopo un indirizzo confermato per errore** (istanza `managed`)
  Si parte dopo la voce «A5-1b + H5-4»: il titolare ha `nuovo@prova.example`, e qui fingiamo che sia l'indirizzo confermato **per errore**. L'indirizzo giusto è `titolare@prova.example`.
  1. Ferma il server. In `/tmp/lf-ondata5-managed.env` metti `LIBREFOLIO_ADMIN_EMAIL=terzo@prova.example` (un indirizzo di nessuno). Riavvia: nel log esce il link di conferma verso `terzo@…`. Copialo e **non aprirlo**. Ferma il server.
  2. Rimetti nel file l'indirizzo giusto: `LIBREFOLIO_ADMIN_EMAIL=titolare@prova.example`. Fai `source` del file. **Non** avviare il server.
  3. `./dev.py user reassign-owner titolare`
  4. `./dev.py user list`
  5. Due rifiuti: `env -u LIBREFOLIO_ADMIN_EMAIL pipenv run python dev.py user reassign-owner altro`, poi `./dev.py user reassign-owner nonesiste`. Guarda la riga e l'uscita (`echo $?`).
  6. Avvia il server. Nel log **non** deve uscire un nuovo link di conferma del cambio email.
  7. Apri nel browser il link verso `terzo@…` copiato al punto 1.
  8. Prova ad entrare come `titolare` (con `titolare@prova.example`) con la password di prima. Poi apri il link di reimpostazione che il comando del punto 3 ha scritto nel suo terminale (o stampane uno nuovo con `./dev.py user reset-link titolare`) e scegli una nuova password.
  9. **Settings › Administration › Users** (riga del titolare), **Settings › Administration › Security**, e `panel/status`.
  - **Atteso:** punto 3: `✅ 'titolare' is the owner of the instance, with the address of LIBREFOLIO_ADMIN_EMAIL; its password no longer works and its sessions ended`. Senza posta segue `⚠️ The email could not go: the link is in the log line «Password-reset link for the instance owner» above, on this terminal only` e il consiglio di usare `user reset-link`. Il comando **non** stampa mai il link da solo (il link è nella riga di log del warning). Punto 4: `titolare` ha l'indirizzo `titolare@prova.example`. Punto 5: due righe con ❌, uscita **1**, niente cambia: «LIBREFOLIO_ADMIN_EMAIL is not set: it holds the address the owner must have» e «User 'nonesiste' not found». Punto 7: la pagina dice che il link non vale più (annullato o non valido): `reassign-owner` annulla anche un link di cambio indirizzo ancora in attesa, quindi l'indirizzo non si sposta. Punto 8: la vecchia password **non** entra; con il link nuovo scegli la password ed entri. Punto 9: il titolare è admin attivo con il badge **Protected**, `panel/status` dà `"owner_email_change":null`, e nel controllo di sicurezza non c'è più «accounts.owner_email_change». Le sessioni aperte del titolare si chiudono già al punto 3.
  - **Nota:** il comando non annulla quello che l'altra persona ha fatto da amministratore mentre aveva l'accesso: la guida dice di controllare account e dati. `user set-email` sul titolare annulla anche lui un link di cambio indirizzo in attesa, ma lascia la password com'è.

- [ ] **A5-6 — Link di setup scaduto sul `managed`: la pagina manda al supporto** (istanza `managed` **nuova**, non ancora configurata)
  1. Ferma il server di §0.3. Copia il file env in `/tmp/lf-ondata5-scaduto.env`, cambia dentro `LIBREFOLIO_DATA_DIR=/tmp/lf-ondata5-scaduto` e metti un nuovo `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` (32 o più caratteri). Fai `source` di quel file e avvia con lo stesso comando di §0.3 ma `--data-dir /tmp/lf-ondata5-scaduto`. **Non** aprire ancora il link di setup.
  2. A server acceso, fai scadere il link: `sqlite3 /tmp/lf-ondata5-scaduto/sqlite/app.db "UPDATE account_tokens SET expires_at='2000-01-01 00:00:00' WHERE purpose='admin_setup' AND consumed_at IS NULL;"` (comando da confermare: il formato della data nella colonna).
  3. Apri `http://localhost:6141/setup#token=<il token>`.
  4. Ferma il server. Aggiungi nel file `export LIBREFOLIO_SUPPORT_URL='mailto:assistenza@prova.example'`, fai `source`, riavvia e riapri lo stesso indirizzo.
  5. Ripeti il punto 3 con l'app in italiano (se la pagina di setup segue la lingua del browser; posizione da confermare).
  6. Togli la riga del supporto e riavvia. Con `./dev.py user setup-link` ottieni un link nuovo: aprilo, scegli la password del titolare, entra. Poi riapri lo **stesso** link nuovo.
  7. Fine prova: ferma il server e cancella `/tmp/lf-ondata5-scaduto`. Riprendi il file env di §0.3.
  - **Atteso:** punto 3: la scheda dice «This link has expired.» e sotto «If you did not receive a new one by email, contact support.». **Nessun pulsante** e nessuna frase su `dev.py user setup-link`. Punto 4: sotto la frase compare il link «Contact support» (verso `mailto:assistenza@prova.example`); senza `LIBREFOLIO_SUPPORT_URL` non c'è nessun link. Punto 5, in italiano: «Se non ne hai ricevuto uno nuovo per email, scrivi all'assistenza.» e il link «Scrivi all'assistenza». Punto 6: il link già usato dice «già usato» con la frase di sempre («Ask your hosting provider for a new link. On your own server, run …»): solo il link **scaduto** ha la frase nuova. Su un'istanza non `managed` (self-hosted) la pagina del link scaduto resta com'era: coperto da test, non serve provarlo.

- [ ] **A5-7 — Più utenti attivi del limite del piano: l'amministratore sceglie chi tiene l'accesso** (istanza `managed`, limite 5)
  1. Parti dall'istanza di §0.3 con `titolare` e `altro` (A5-1). Crea `u1` e `u2` come utenti normali (`./dev.py user create u1 u1@prova.example <password-prova> --role user`). Ora gli attivi sono 4.
  2. In **Settings › Administration › Users** crea un invito e **non** usarlo (ora i posti occupati sono 5, quanti il limite).
  3. Crea `u3` e `u4` dal terminale, sempre con `--role user`. Da `user create` esce un avviso di limite raggiunto, ma l'utente è creato. Gli attivi sono 6, più di 5.
  4. Leggi lo stato: `curl -sS -H "Authorization: Bearer $LIBREFOLIO_PANEL_STATUS_TOKEN" http://localhost:6141/api/v1/panel/status`.
  5. In una finestra privata entra come `u1` (utente normale). Poi in un'altra, entra come `altro` (amministratore): **non confermare** niente.
  6. Entra come `titolare`: guarda la pagina, l'elenco, il contatore. Spunta tutti gli altri account: guarda il contatore e il pulsante. Togline uno (per esempio `u4`) e guarda la riga sugli inviti.
  7. Prima di confermare guarda la scheda in basso («Download a full backup first»): scarica il backup **zip** (serve anche a B5-1k2).
  8. Premi **Deactivate the others and continue**. Poi **Settings › Administration › Users**.
  9. Rileggi `panel/status`.
  10. Prova a riattivare `u4` dalla lista. Poi da terminale: `./dev.py user activate u4`, e rientra come `titolare`.
  - **Atteso:** punto 4: `"users_limit":5`, `"users_over_limit":true`, `users_used` = 7 (6 attivi + l'invito). Punto 5: `u1` **non** vede l'app ma la pagina «The administrator has to choose who keeps the access» (in italiano «L'amministratore deve ancora scegliere chi mantiene l'accesso»), con **Check again** e **Sign out**; `altro` vede la stessa scelta dell'amministratore e nessun'altra pagina. Punto 6: titolo «More users than your plan allows» («Più utenti di quelli del tuo piano»); «This instance has 6 active users but its plan allows 5…»; sei righe con username e email; il **titolare** è spuntato e non modificabile («Owner of the instance: always stays»); gli amministratori hanno l'etichetta «Administrator»; il contatore parte da «1 of 5 chosen»; con tutti spuntati diventa «6 of 5 chosen» in rosso e il pulsante di conferma è spento; con cinque scelti (togli `u4`) il pulsante si accende e compare «1 pending invitation(s) will be cancelled to make room.». Chi è l'unico titolare di un broker porta «Only owner of N broker(s): the others lose access to them». Punto 7: la scheda del backup scarica un file vero. Punto 8: la pagina si ricarica nell'app; l'account non scelto è **disattivato, non cancellato** (con i suoi dati), l'invito è annullato. Punto 9: `"users_over_limit":false`, `users_used` = 5. Punto 10: dall'interfaccia la riattivazione è rifiutata (istanza piena: annota il messaggio); da terminale `user activate` stampa un avviso ma riattiva, e al rientro di un amministratore si ripresenta la scelta (gli attivi sono di nuovo 6).
  - **Nota:** il limite illeggibile (`LIBREFOLIO_MAX_USERS=abc` o `0`) non avvia mai questo stato: coperto da test.

---

## 2. Backup e ripristino

- [ ] **B5-1 + A5-2 — Ripristino di un backup caricato, con la scelta del titolare** (istanza `managed`)
  1. Entra come titolare. **Settings › Administration › Backup**: fai un backup **zip** (scaricalo).
  2. Nella scheda **Restore an archive** scegli quel file, aspetta il controllo, leggi il rapporto.
  3. Scrivi a mano la parola richiesta e clicca **Restore and restart**.
  4. Si apre la finestra **«Who is the owner of this instance?»**: guarda l'elenco.
  5. Clicca **Confirm and restore**. Il server si ferma: rilancialo con il comando di §0.3 (`source` incluso).
  6. Nel log cerca il `warning` «Password-reset link for the instance owner». Il link **non** deve comparire nel rapporto del ripristino.
  7. Prova ad accedere come titolare con la **vecchia** password.
  8. Apri il link del log, scegli una nuova password, entra.
  9. Da terminale: `./dev.py backup pending`.
  - **Atteso:** al punto 4 c'è un solo utente, bloccato, con la scritta «One user of this backup already has the owner's email address: it is the owner.» (il suo indirizzo è quello dell'istanza). La conferma non parte senza scelta. Al punto 7 la vecchia password **non** entra. Il link di reimpostazione (30 minuti) è solo nel log (niente posta). Dopo il punto 8 si entra. Al punto 9 compare la riga «⚠️ The owner's account is set, but no email could be sent: the link … is in the log of the instance; give it only to the owner» (nessun link scritto). Nella pagina di accesso non resta alcun messaggio d'errore.
  - Se per caso il server resta bloccato o la pagina dice «restore did not go through»: annota il testo e la ragione.

- [ ] **B5-1g — La finestra del titolare spiega dove va il link, e un admin in attesa blocca il ripristino** (istanza `managed`)
  1. Avvia un ripristino come nella voce B5-1 fino alla finestra **«Who is the owner of this instance?»**. Leggi la nota in fondo alla finestra.
  2. Prepara un backup con un admin **in attesa**: crea un invito admin che **non** usi e cambia `LIBREFOLIO_ADMIN_EMAIL` sull'indirizzo di quell'invito (posizione da confermare: serve un admin inattivo con link di setup non usato e l'indirizzo del titolare). Fai il backup zip e prova a ripristinarlo.
  - **Atteso:** al punto 1 la nota dice che, se l'email non parte, il link è nel **log dell'istanza** per chi la gestisce; il link non è mai mostrato. Al punto 2 la conferma è **rifiutata** con un messaggio di conflitto sul titolare (`owner_conflict`), tradotto nella lingua dell'app: il server non si ferma e nulla cambia.

- [ ] **B5-1 variante — Scelta tra più admin, e il vecchio titolare perde la protezione** (istanza `managed`)
  1. Serve un secondo admin (`altro`, vedi A5-1). Ferma il server. In `LIBREFOLIO_ADMIN_EMAIL` metti un indirizzo che **nessun account ha** (`terzo@prova.example`). Riavvia (parte il cambio email, link nel log: ignoralo).
  2. Entra come `titolare`. Fai un backup zip e avvia il ripristino come sopra, fino alla finestra della scelta.
  3. Nella finestra scegli **`altro`** (non il titolare). Conferma. Rilancia il server.
  4. Prendi il link dal log, imposta la password di `altro`, entra come `altro`.
  5. Apri **Settings › Administration › Users**.
  - **Atteso:** al punto 3 la finestra elenca **tutti gli admin attivi** del backup, con i badge «Administrator» (e «Owner's email» se ce n'è uno). Dopo il ripristino `altro` ha l'email `terzo@prova.example`, è admin attivo, ha il badge **Protected**; il vecchio `titolare` **non** è più protetto (resta admin con la sua password di allora). La vecchia password di `altro` non entra più.

- [ ] **A5-5 — L'email dopo un ripristino dice che la password è stata revocata** (istanza `managed`, serve un SMTP di prova)
  1. Serve un server SMTP locale che mostri i messaggi (per esempio Mailpit: non è nel progetto, posizione da confermare). Nel file env aggiungi `LIBREFOLIO_SMTP_HOST=127.0.0.1`, `LIBREFOLIO_SMTP_TLS=none`, `LIBREFOLIO_SMTP_PORT=<porta del tuo server di prova>` e `LIBREFOLIO_SMTP_FROM='LibreFolio <noreply@prova.example>'`. Riavvia. Se il server rifiuta l'host locale, guarda la guida Email (regole dei nomi privati).
  2. Metti la lingua del titolare su **Italiano** (**Settings › Preferences**) e fai un backup zip.
  3. Ripristinalo come nella voce B5-1 (finestra della scelta, **Confirm and restore**, rilancia il server).
  4. Apri l'email arrivata al titolare (l'indirizzo di `LIBREFOLIO_ADMIN_EMAIL`). Nel log del server non deve esserci il link.
  5. Nella pagina di accesso scegli **Forgot Password?** con l'indirizzo del titolare e guarda la seconda email.
  6. Se vuoi, ripeti dai punti 2 e 3 con la lingua su **English**, **Français** e **Español**.
  - **Atteso:** l'email del punto 4 ha l'oggetto «Scegli una nuova password per LibreFolio» e dice, in sostanza: «Il tuo account su <istanza> è stato ripristinato da un backup.», «Per la tua sicurezza, la password è stata revocata dopo il ripristino. Usa il pulsante qui sotto per sceglierne una nuova.», il pulsante, la scadenza (il link vale una volta sola e 30 minuti), «Se il link è scaduto, scegli «Password dimenticata?» nella pagina di accesso, con questo indirizzo email, per ottenerne uno nuovo.» e «Se non te lo aspettavi, contatta chi gestisce questo LibreFolio.». Non c'è nessun nome utente, nessun indirizzo e non dice **chi** ha fatto il ripristino. Il link funziona (scegli la password ed entri). La seconda email (punto 5) è quella **normale** della reimpostazione («Abbiamo ricevuto una richiesta di reimpostare la password…»), non quella del ripristino. Lo stesso testo esce anche dopo un ripristino da terminale (B5-1j). Le altre lingue: oggetto «Choose a new password for LibreFolio», «Choisissez un nouveau mot de passe pour LibreFolio», «Elige una nueva contraseña para LibreFolio».
  - **Senza SMTP di prova:** segna «non provato». Il testo in quattro lingue è coperto dai test del servizio email; la posta spenta è già vista in B5-1 (link solo nel log).

- [ ] **B5-1j — Il ripristino da terminale sceglie il titolare da solo** (istanza `managed`)
  1. Con il titolare entrato fai un backup **zip** dall'app e scaricalo (come B5-1, punto 1). Ferma il server.
  2. Con `source` fatto: `./dev.py backup restore /percorso/del/backup.zip`. Leggi il rapporto del controllo. Scrivi la parola richiesta per confermare.
  3. `./dev.py backup pending`
  4. Rilancia il server (§0.3). Nel log cerca il `warning` «Password-reset link for the instance owner».
  5. `./dev.py backup pending` di nuovo.
  6. Prova ad entrare come titolare con la **vecchia** password. Poi apri il link del log, scegli una nuova password, entra.
  7. Controlla in **Settings › Administration › Users** il badge del titolare.
  - **Atteso:** il comando **non chiede** quale account sia il titolare: il rapporto dice `👤 The owner's account will be titolare: its password is closed at the restore, and a link to choose a new one goes to the owner's address (or the owner uses Forgot password?)`, col **nome utente**, mai un indirizzo. Al punto 3 il ripristino è in attesa. Al punto 4 il link è solo nel log (niente posta) e **non** è scritto nel rapporto. Al punto 5 compare la riga `⚠️ The owner's account is set, but no email could be sent: the link … is in the log of the instance; give it only to the owner`. Al punto 6 la vecchia password **non** entra, anche se l'indirizzo era già quello dell'istanza: dal terminale la password del titolare si chiude sempre (solo il pannello dell'host può tenerla, vedi §9 B5-1l). Dopo il link si entra e il titolare è **Protected** (e il segno di titolare resta su un solo account).
  - **Altre uscite:** su un'istanza non `managed`, o senza `LIBREFOLIO_ADMIN_EMAIL`, il ripristino da terminale non sceglie nessuno e non cambia nessuna password (coperto da test).

- [ ] **B5-1j variante — Nessun account può essere il titolare** (istanza `managed`)
  1. Serve `altro` (admin attivo, A5-1). Ferma il server. In `LIBREFOLIO_ADMIN_EMAIL` metti un indirizzo che **nessun** account ha (`quarto@prova.example`). Riavvia (parte il cambio email, ignora il link).
  2. Da terminale: `./dev.py user demote titolare` (il segno di titolare resta sul vecchio account, ma non è più un amministratore).
  3. Entra come `altro`, fai un backup **zip** e scaricalo. Ferma il server.
  4. `./dev.py backup restore /percorso/del/backup.zip`: leggi il rapporto, conferma.
  5. Rilancia il server. `./dev.py backup pending`.
  6. Ferma il server. `./dev.py user reassign-owner altro`. Rilancia, apri il link del log e scegli la password di `altro`.
  - **Atteso:** al punto 4 il rapporto dice `⚠️ No owner: no account of the backup can be taken for it. The restore goes on; name one afterwards with ./dev.py user reassign-owner <username>` e il ripristino **va avanti**. Al punto 5 `backup pending` ripete la riga `⚠️ No owner was assigned at the restore: …` e l'istanza serve i suoi dati. Al punto 6 `altro` prende l'indirizzo di `LIBREFOLIO_ADMIN_EMAIL`, diventa l'unico titolare e riceve il link. La regola di scelta, per chi vuole controllarla: prima l'account che ha già l'indirizzo dell'istanza, poi **l'unico** admin attivo segnato come titolare nel backup, altrimenti nessuno (mai «il primo»).

- [ ] **B5-1k2 — Un backup con più utenti del piano: il ripristino lo dice, non lo rifiuta** (istanza `managed`, limite 5)
  1. Usa il backup **zip** scaricato al punto 7 di A5-7 (contiene 6 utenti attivi). Se non ce l'hai, rifai A5-7 fino a quel punto.
  2. Dopo A5-7 gli attivi sono 5 (se al punto 10 di A5-7 hai riattivato `u4` sono 6: rifai la scelta come titolare, altrimenti **Settings** non si apre). Da terminale, con il server fermo: `./dev.py backup restore --dry-run /percorso/del/backup.zip`. Guarda il rapporto.
  3. Avvia il server. Nell'app, **Settings › Administration › Backup › Restore an archive**: scegli lo stesso file e guarda il rapporto. Scrivi la parola, scegli il titolare, **Confirm and restore**. Rilancia il server.
  4. Dopo il riavvio entra come `titolare` e guarda cosa compare. Rileggi `panel/status`.
  - **Atteso:** punto 2: una riga `⚠️ The backup holds 6 active accounts; this instance accepts 5 (LIBREFOLIO_MAX_USERS): at the first sign-in the administrator chooses who keeps access, the others are deactivated (not deleted)`; il comando va avanti come per ogni backup. Punto 3: nella finestra del rapporto un avviso a parte «This backup holds 6 active accounts, but this instance accepts 5. The restore goes on; when an administrator signs in, they choose who keeps access, and the others are deactivated, not deleted.» (in italiano: «Questo backup contiene 6 account attivi, ma questa istanza ne accetta 5. Il ripristino prosegue; …»), senza nomi né indirizzi. La conferma non cambia e il ripristino **non è rifiutato**. Punto 4: al primo accesso dell'amministratore compare la scelta di A5-7 (6 attivi, limite 5) e `panel/status` dice `"users_over_limit":true`. Un limite scritto male (`LIBREFOLIO_MAX_USERS=abc`) o assente non fa comparire l'avviso (coperto da test).

- [ ] **B5-2 — `backup pending --json` e `--recover` con codici di uscita fissi** (DB di test, **non** la produzione)
  1. Server di prova fermo. `./dev.py backup --test-db pending --json; echo "uscita=$?"`.
  2. `./dev.py backup --test-db pending --recover cancel --json; echo "uscita=$?"`.
  3. Crea uno stato illeggibile: `mkdir -p backend/data/test/.restore && echo '{rotto' > backend/data/test/.restore/restore.json`.
  4. Ripeti il punto 1. Poi: `… pending --recover cancel --json` (uscita?), `… pending --json --cancel` (uscita?), `… pending --recover` senza parola (uscita?).
  5. Avvia il server di prova (`./dev.py server --test`), lancia `… pending --recover previous --json; echo "uscita=$?"`, poi **fermalo**.
  6. Con il server fermo: `… pending --recover previous --json` due volte di fila, guarda le due uscite.
  7. Ripulisci: `rm -rf backend/data/test/.restore`.
  - **Atteso:** punto 1: una sola riga JSON sul terminale (`"state":"none"`, `"choices":[]`), uscita 0. Punto 2: uscita **3** (niente da recuperare). Punto 4: `"state":"unreadable"`, `"reason":"invalid"`, `"choices":["previous"]`, uscita 0; `--recover cancel` uscita **4** (`choice_not_valid`); `--json` con `--cancel` uscita **2**; `--recover` senza parola uscita **2**. Punto 5: uscita **5** (`restore_in_use`: il server gira). Punto 6: prima volta uscita **0**, seconda **3**. I messaggi per l'umano e i log vanno su stderr, non sulla riga JSON. Il file rotto resta salvato come `restore.json.unreadable-<data>`.

---

## 3. Pannello hosting e istanza

- [ ] **H5-1 — `users_used` e `users_limit` nello stato del pannello** (istanza `managed`, limite 5)
  1. `curl -sS -H "Authorization: Bearer $LIBREFOLIO_PANEL_STATUS_TOKEN" http://localhost:6141/api/v1/panel/status`
  2. Crea un invito in **Settings › Administration › Users** (non usarlo). Ripeti il comando.
  3. Chiedi la stessa risposta senza token.
  - **Atteso:** la risposta ha **nove** chiavi: `admin_setup`, `setup_expires_at`, `mode`, `restore`, `users_used`, `users_limit`, `owner_email_change`, `instance_key` (H5-7) e `users_over_limit` (H5-8). Qui `instance_key` è `"ok"` e `users_over_limit` è `false`. Al punto 1 il titolare occupa un posto: `users_used` = 1 (+1 per ogni altro admin creato), `users_limit` = 5. Dopo l'invito sale di 1 (l'invito non usato conta un posto). Mai nomi, email o id. Senza token: errore di accesso. Se togli `LIBREFOLIO_MAX_USERS` e riavvii, `users_limit` è `null`.

- [ ] **H5-6 + H5-8 — La probe `/system/ready` dice «behind» o «ahead», con la revisione del DB e la versione** (istanza `managed`)
  1. `curl -sS -i http://localhost:6141/api/v1/system/ready` (non serve nessun token). Poi `curl -sS http://localhost:6141/api/v1/system/info`.
  2. Segna la revisione: `sqlite3 /tmp/lf-ondata5-managed/sqlite/app.db "SELECT version_num FROM alembic_version;"`.
  3. A server acceso: `sqlite3 /tmp/lf-ondata5-managed/sqlite/app.db "UPDATE alembic_version SET version_num='004_release_1_2_0_schema';"`. Ripeti la probe del punto 1.
  4. `sqlite3 … "UPDATE alembic_version SET version_num='999_sconosciuta';"`. Ripeti la probe.
  5. Rimetti la revisione del punto 2 (di norma `005_release_1_3_0_schema`) e ripeti la probe. Guarda il log del server per tutto il tempo.
  - **Atteso:** punto 1: `200`, `"status":"ready"`, `"checks":{"database":"ok","migrations":"ok"}`, `"database_revision":"005_release_1_3_0_schema"`, `"mode":"normal"` e `"app_version"` uguale a quello di `/system/info` (che risponde anche senza accesso). Punto 3: `503`, `"status":"not_ready"`, `"migrations":"behind"` (una revisione più vecchia che questa versione conosce) e `database_revision` = `004_release_1_2_0_schema`. Punto 4: `503`, `"migrations":"ahead"` (una revisione che questa versione non conosce: il DB è più nuovo dell'immagine). **Mai** `"mismatch"`. La risposta non ha messaggi d'errore né percorsi: stanno solo nel log, un `warning` «Instance not ready» una volta a ogni cambio di stato. Punto 5: torna `200`, `ok`, e nel log «Instance ready».
  - **Attenzione:** cambia `alembic_version` solo su questa copia sotto `/tmp`. Se dimentichi di rimetterla, il prossimo avvio la tratta come un DB di un'altra versione.

- [ ] **H5-7 — `instance_key: ok|mismatch` nel pannello, e i backup del pannello si fermano da soli** (istanza `managed`)
  1. Genera due chiavi, A e B: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` due volte. Nel file env aggiungi `LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN='<32 o più caratteri>'`, `LIBREFOLIO_INSTANCE_KEY='<A>'` e `LIBREFOLIO_INSTANCE_KEY_ACCEPT=1`. Ferma, `source`, avvia. Nel log cerca il `warning` che dice che il cambio di chiave è accettato. Poi togli `LIBREFOLIO_INSTANCE_KEY_ACCEPT`, `source` (in una shell nuova, perché il `source` non toglie le variabili) e riavvia.
  2. `panel/status`. Guarda anche `ls -l /tmp/lf-ondata5-managed/secrets/`.
  3. Ferma. Metti la chiave **B** al posto di A. Riavvia. Guarda il log, `panel/status` e **Settings › Administration › Security** (cerca il controllo «platform.instance_key_check»). Entra e naviga nell'app.
  4. Prova il backup del pannello: `curl -sS -i -X POST -H "Authorization: Bearer $LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN" http://localhost:6141/api/v1/backup/panel/jobs`. Poi un backup normale da **Settings › Administration › Backup**.
  5. Ferma. Rimetti la chiave **A**. Riavvia. `panel/status`, poi di nuovo il `curl` del punto 4 (se parte, cancella il job: `DELETE …/api/v1/backup/panel/jobs/<job_id>` con lo stesso token).
  6. Facoltativo, il cambio voluto: ferma, metti B con `LIBREFOLIO_INSTANCE_KEY_ACCEPT=1`, avvia **una** volta, poi togli la variabile e riavvia.
  - **Atteso:** punto 2: `"instance_key":"ok"`, e nella cartella `secrets/` c'è il file `instance.key.check` (il valore di controllo; qui la chiave viene dall'ambiente, quindi `instance.key` può mancare; mai la chiave nel log né nello stato). Punto 3: nel log un **errore** «The instance key is not the one this instance's data was written with…»; `panel/status` dà `"instance_key":"mismatch"` e **niente altro** cambia; nel controllo di sicurezza c'è un errore con lo stesso messaggio; l'app **resta aperta** e funziona. Punto 4: il `curl` risponde `409` con il codice `backup_instance_key_mismatch`; il backup dall'app invece **parte** (la fermata vale solo per i job del pannello e per il risveglio programmato). Punto 5: dopo la chiave giusta `panel/status` torna `"ok"` **da solo**, senza azioni, e il job parte (`202`). Punto 6: con `ACCEPT=1` il log ha un warning, lo stato è `ok`; togliendo la variabile resta `ok` con B.
  - **Nota:** senza `ACCEPT`, un cambio di chiave involontario è proprio il caso che il controllo deve fermare. I segreti dei plugin salvati con la chiave vecchia non si leggono più dopo il cambio.

- [ ] **X-R84 — Dopo un aggiornamento, un pezzo di app non caricato riporta all'app, non alla pagina 500** (DB di test)
  1. Avvia `./dev.py server --test`, entra, resta sul Cruscotto. Apri gli strumenti del browser (DevTools).
  2. In **Network** apri «Network request blocking» e aggiungi il motivo `*/_app/immutable/nodes/*`. Poi clicca nel menu una pagina che **non** hai ancora aperto in questa scheda (per esempio **FX**).
  3. Ripeti il clic subito dopo (entro 60 secondi).
  4. Togli il blocco e ricarica.
  - **Atteso:** al punto 2 la pagina si ricarica **una volta** e finisce nell'app (la pagina richiesta o il Cruscotto), **senza** la schermata 500. Al punto 3 non c'è un ciclo di ricariche (la protezione dura 60 secondi): al massimo compare la pagina d'errore normale. Posizione da confermare: se il blocco non fa scattare il caso, prova invece a ricostruire il frontend con `./dev.py front build` a pagina aperta e a cliccare una pagina nuova.

---

## 4. Import e Bulk (e form delle transazioni) — DB di test

- [ ] **W5-3 (B2) — Avviso: trasferimento con arrivo prima della partenza**
  1. **Transactions › Add Transaction**. Tipo **Asset Transfer** (o **Cash Transfer**): due broker diversi, quantità o importo, data della **partenza** `2026-03-10`, data dell'**arrivo** `2026-03-05`.
  2. **Apply**, poi **Save All**.
  3. Cambia lingua in IT (**Settings › Preferences**) e ripeti con altre date.
  - **Atteso:** il salvataggio **riesce** (la coppia è salvata come l'hai scritta) e compare un avviso non bloccante nella lingua scelta. In italiano: «L'arrivo (2026-03-05) è datato prima della partenza (2026-03-10). È stato salvato come inserito: controlla le due date.» Dove si vede l'avviso nel Bulk: posizione da confermare. Con date in ordine (o uguali) nessun avviso.

- [ ] **W5-5 (C-70b) — Errore di lettura nella lingua dell'app**
  1. **Transactions › Import**. Carica `revolut-invest-export.csv` su un broker.
  2. Nel passo **Select Files** cambia la colonna **Plugin** in uno che non lo sa leggere (per esempio **Fineco**). Premi **Parse**.
  3. Nello stesso passo apri l'anteprima (menu **⋮ › Preview**) di un file che non si può leggere come tabella (per esempio un `.txt` rinominato `.csv`, oppure un file vuoto).
  4. Ripeti i punti 2 e 3 con la lingua dell'app su IT.
  - **Atteso:** un banner dice, in italiano, che il plugin (col suo **nome**, non il codice) non ha letto il file, con la **ragione** tradotta (colonne mancanti, intestazione non riconosciuta, file vuoto, nessuna transazione valida…): vale per tutti i 31 plugin (W5-6). In un report set, saldi illeggibili o codici valuta non validi danno un messaggio tradotto con il numero di valori o i codici. Non deve apparire una frase inglese tipo «Parse error: …». L'anteprima di un file non leggibile mostra un messaggio tradotto, non il testo del server. Lo stesso nel dialogo dei file del broker (broker › file di import, posizione da confermare).

- [ ] **W-B87 (righe economiche) — eToro e Swissquote**
  1. Importa `etoro-export.csv`. Guarda il passo **Parse** (avvisi) e poi **Review**.
  2. Importa `swissquote-export.csv`. Come sopra.
  - **Atteso (eToro):** le righe **Overnight fee** diventano transazioni **Fee** senza asset (importo negativo; esempi del campione: −0,10 e −0,31). La riga **SDRT** diventa **Tax** sullo strumento (−6,97). **Overnight refund** diventa una transazione **Interest** senza asset, sempre positiva (+0,21 nel campione), con la descrizione «overnight refund: daily» (W5-2c, plugin eToro 1.4.0). Il file eToro non lascia più nessuna riga nell'avviso ambra «non importato».
  - **Atteso (Swissquote):** le righe **Forex credit** e **Forex debit** dello stesso **Order #** diventano **due** transazioni **Currency Exchange** collegate. Nel campione ce ne sono due coppie (ordine 114723639: +1 995,39 EUR / −2 000,00 USD; ordine 113882551: +100 000,00 CHF / −106 017,30 USD). Ogni gamba tiene la sua data e il suo **Net Amount**. Le righe senza coppia pulita (compagna mancante, più di due gambe, gamba con **Costs**, stessa valuta) restano nell'avviso ambra. Le righe **Debit** diventano **Withdrawal**.

- [ ] **W-B87 (split moltiplicativi) — Revolut e Trading 212**
  1. Importa `revolut-invest-export.csv`. Cerca la riga **TSLA STOCK SPLIT** (0,16431924).
  2. Importa `/tmp/t212-split.csv` (§0.2).
  3. Importa il campione `trading212-export.csv` (ha uno split **inverso**, una **Stock distribution** e un **Transfer out**).
  - **Atteso:** Revolut: lo split diventa **una** transazione **Adjustment** in entrata di **0,16431924** azioni TSLA, a costo **0**, con la descrizione «STOCK SPLIT: TSLA». Non è più nell'avviso «non importato». Trading 212 (file di prova): le due righe «close/open» diventano **un** Adjustment di **+20** azioni (30 − 10), costo 0. Campione T212: lo split inverso (meno azioni dopo) e la **Stock distribution** restano nell'avviso ambra. Nel passo di revisione del wizard una nota dice quante righe sembrano split. Nel Bulk compare il banner «N righe potrebbero essere split» con ticker, azioni aggiunte, data e rapporto; «Crea l'evento SPLIT e collega» apre il mini-modale già su SPLIT con il rapporto compilato; collegata la riga, il banner la toglie (W5-2b, `e208b3417`). Nel campione Revolut vero lo split TSLA è la prima riga del ticker: lì il rapporto non si legge e l'avviso di arrotondamento non compare.

- [ ] **V-37b — «⚡ Validate now» controlla tutte le celle prima del server**
  1. **Transactions › Add Transaction**, tipo **Buy**. Non compilare nulla e premi **⚡ Validate now**.
  2. Lascia vuota la quantità e scrivi `abc` nella data. Premi di nuovo.
  3. Correggi la data, poi compila la quantità. Premi.
  4. Apri il pannello **Network** del browser: guarda se parte una richiesta a `/transactions/validate` nei punti 1 e 2.
  - **Atteso:** il pulsante è **sempre** cliccabile. Al punto 1 i campi obbligatori mancanti si colorano di rosso insieme; al punto 2 due celle rosse (data scritta male: rosso sul campo; quantità mancante: contorno rosso), il fuoco va alla **prima in ordine di schermo** (la data), un contatore dice «2 fields need fixing». **Nessuna** richiesta al server nei punti 1 e 2. Ogni segno sparisce quando correggi il campo. Con tutto giusto (punto 3) la richiesta parte e si legge «valid» o i problemi del server. Vale uguale per una coppia (trasferimento, cambio).

- [ ] **#47 + W5-9 — Importo totale oppure prezzo unitario nel form di acquisto/vendita** (il calcolo ora lo fa il browser)
  1. **Add Transaction**, tipo **Buy**, quantità **12**. Il campo contanti ha due pulsantini **Total amount** e **Unit price**.
  2. Scegli **Unit price** e scrivi `83.40`.
  3. Cambia l'importo in `1000.90`.
  4. Prova lo stesso su una **Sell**. Poi su un **Deposit** e su un **Asset Transfer**.
  5. Con il pannello **Network** del browser aperto, ripeti i punti 2 e 3.
  6. Con quantità **3**, scrivi l'importo `10`.
  7. Salva una **Buy**, poi riaprila dalla lista **Transactions** (sola lettura).
  - **Atteso:** al punto 2 l'importo si compila **subito**, senza pausa: **1000,80** (12 × 83,40), resta modificabile. Al punto 3 i pulsanti tornano su **Total amount** e il prezzo unitario diventa **83,408333333333** (12 decimali). Al punto 5 **nessuna** richiesta a `/transactions/trade-amount` (la rotta non esiste più: il calcolo è nel browser). Al punto 6 il prezzo unitario diventa **3,333333333333**. Gli importi hanno al massimo 6 decimali, i prezzi 12, arrotondati «al pari» (mezzo verso il numero pari). Per un asset quotato «per 100» (obbligazione) il prezzo segue la quotazione. Sui tipi diversi da Buy/Sell i pulsanti non ci sono. Al punto 7 la transazione salvata mostra **importo e prezzo unitario insieme** (senza i pulsanti, in sola lettura). Nel Bulk (griglia) non ci sono ancora (voce di backlog).

- [ ] **W5-10 + W5-11 (D-P4) — Una data prima del 1900 chiede conferma e si salva; un anno breve si legge com'è scritto** (DB di test)
  1. **Transactions › Add Transaction**, tipo **Deposit**, un broker, importo 100, data `1850-06-01` (scritta a mano nel campo). Guarda il modulo sopra i campi.
  2. Prova a salvare **senza** premere nulla. Poi premi **Yes, the date is right** e salva.
  3. Cambia la data di una transazione già salvata in `1850-06-02` e salva di nuovo. Poi cambia **solo** l'importo di quella riga già del 1850 e salva.
  4. Nuovo **Deposit** con data `0024-03-01`. Apri il calendario del campo e guarda il mese e l'anno. Con le frecce del campo data cambia un giorno.
  5. Nuovo **Deposit** con data **dopo domani**. Guarda il messaggio.
  6. Apri il **Bulk** (l'editor a griglia; posizione da confermare) e metti in due righe una data del 1850: guarda il banner in alto, poi **Save All**.
  7. Importazione (facoltativa): in un editor di testo cambia l'anno di una riga di un file campione in `1850`, importalo e guarda il passo **Review** (posizione da confermare per il formato della data del broker scelto).
  - **Atteso:** punto 1: un avviso ambra «The date 1850-06-01 is before 1 January 1900. Check that the year is right: it is often a typo.» con il pulsante **Yes, the date is right** (IT: «La data … è anteriore al 1° gennaio 1900…», «Sì, la data è giusta»). Punto 2: il salvataggio **non** parte finché non premi il pulsante; poi si salva come ogni altra data (**nessun rifiuto** del server: il pavimento del 1900 non c'è più). Punto 3: cambiando la data riappare la domanda; cambiando solo l'importo di una riga che ha già quella data **non** la ripete. Punto 4: la data resta nell'anno **24** (`0024-03-01`), non diventa 1924; il calendario mostra l'anno 0024 e le frecce spostano di un giorno restando lì; il campo accetta anche `1/3/0024`. Punto 5: la data è rossa e il messaggio dice «Not after <data>» (IT: «Non oltre il …»), con l'ultimo giorno ammesso (domani per il server; nel modulo può essere oggi: annota quale), non più «Between 1900 and …». Punto 6: sopra la griglia un banner ambra «2 rows are dated before 1 January 1900…» con una riga per ogni riga («Row 1: 1850-…»), e un clic porta alla riga; **Save All** apre una **sola** finestra «Save dates before 1900?» («Salvare date anteriori al 1900?») con **Yes, the dates are right** («Sì, le date sono giuste») e **Review**; **Review** torna alla griglia. Punto 7: le righe del 1850 sono segnate in ambra e una nota sopra la tabella dice «N selected rows are dated before 1 January 1900…».
  - Le date prima del 1900 non vanno più rifiutate dal server: l'unica difesa contro il refuso è questa conferma. Cancella le transazioni di prova alla fine.

- [ ] **W5-8 — Ordine di giorno e mese nel CSV generico**
  1. Prendi un file del CSV generico (l'esempio della pagina «Generic CSV» della guida) e metti in due righe le date `03/04/2025` e `25/12/2025`. Importalo con l'impostazione di sempre.
  2. **Settings › Plugins › Broker imports**, carta del CSV generico: cambia **Day and month order** da giorno-prima a **mese-prima**. Salva.
  3. Torna all'elenco dei file importati.
  4. Rifai il parse del file e guarda le due date.
  - **Atteso:** al punto 1 `03/04/2025` è il **3 aprile** e `25/12/2025` il 25 dicembre. Al punto 3 il file già letto mostra il banner **«parse da rifare»** (è stato letto con l'ordine vecchio). Al punto 4 `03/04/2025` diventa il **4 marzo**, `25/12/2025` resta il 25 dicembre (13 non è un mese, quindi ripiega su giorno-prima). Le date ISO (`2025-04-03`) e quelle con il mese a lettere non cambiano mai. Non esiste un'opzione «automatica». L'impostazione è personale: un altro utente continua a leggere giorno-prima (W5-8, `c69a47546`).

---

## 5. Plugin, asset e impostazioni

- [ ] **C-65a — Una finestra con i conteggi prima di cambiare o togliere il provider** (DB di test)
  1. **Assets › Add Asset**: crea un asset con provider **Scheduled Investment** (un piano, funziona senza rete). Aspetta che si generino prezzi ed eventi.
  2. Apri l'asset, **Edit** (✏️), cambia le impostazioni del piano, **Save Changes**.
  3. Premi **Cancel** nella finestra. Controlla prezzi ed eventi.
  4. Ripeti e conferma. Poi **Edit › Provider Assignment › No Provider**, **Save Changes**.
  5. Passa a un provider online (o impostazioni nuove di un provider online).
  - **Atteso:** al punto 2 **una** finestra elenca quanto si perde, per esempio «1 240 price points … and 6 events generated by the provider», le transazioni che perdono il collegamento a un evento cancellato (le transazioni restano), «Manual events are kept». **Cancel** non cancella nulla. Confermando, prezzi ed eventi del piano vengono rigenerati. **No Provider** cancella gli **eventi** generati dal provider ma **tiene i prezzi**. Cambiare provider online o dare impostazioni nuove a uno online non chiede nulla. Se il conteggio non si può leggere, il form salva senza finestra. Il rifiuto duro resta solo per uno SPLIT del provider con rettifiche senza costo d'acquisto (messaggio con la data dello split).

- [ ] **N68 (X5-3) — Cambio valuta sempre permesso, con conteggi; gli SPLIT restano**
  1. Scegli un asset del DB di prova con prezzi e almeno un evento (o creane uno senza provider: **Data editor** per due prezzi, **Events** per un Dividend e uno Split). Collega un Dividend a una transazione di un broker.
  2. **Edit**, cambia **Currency** (per esempio da USD a EUR), **Save Changes**.
  3. Guarda la finestra **Change asset currency**. Prima prova **Cancel**.
  4. Ripeti e clicca **Delete & change currency**.
  5. Guarda prezzi ed eventi dell'asset, la lista **Transactions**.
  - **Atteso:** la modifica non è mai bloccata (nessun errore 409 come prima). La finestra elenca: i punti di prezzo con il periodo, gli eventi manuali e quelli del provider che spariscono, le transazioni che **perdono il collegamento**, e gli **split che restano** (con le loro rettifiche). Dopo la conferma: prezzi ed eventi non-split sono spariti; lo **Split** c'è ancora; le transazioni ci sono tutte, quelle del dividend cancellato sono senza evento collegato. Se l'asset ha un provider, i prezzi si riscaricano nella nuova valuta; senza provider no.
  - **Esempio:** un ETF passato da USD a EUR perde 1 240 prezzi e 6 dividendi (3 transazioni scollegate) e tiene lo split del 2021.

- [ ] **N68 — «Relink events»: riagganciare i dividendi agli eventi**
  1. Dopo la prova precedente, sull'asset aggiungi un evento **Dividend** manuale **nella stessa data** della transazione scollegata (nella nuova valuta).
  2. **Transactions** › barra sopra la tabella › **Relink events**.
  3. Guarda la riga. Poi crea un secondo caso: sposta l'evento di 2 giorni (non è più nello stesso giorno), riapri la finestra. Poi aggiungi **due** eventi nello stesso giorno.
  4. Torna al caso con un evento nello stesso giorno e premi **Link** (oppure **Link every row with one event**).
  - **Atteso:** la finestra elenca dividendi, interessi e adjustment **senza evento** (dei broker dove sei almeno Editor). Un evento nello stesso giorno: «**One event that day**» con il pulsante **Link**. Evento a 2 giorni di distanza: «**No event that day**» (nessuna proposta: la guida lo spiega). Due eventi: «**N events that day**», nessuna proposta (non indovina). Non si collega nulla da sola. Dopo **Link** la transazione ha l'evento nel campo **Linked Event**.

- [ ] **Z-35 / Z-32 — Yahoo: chiusure grezze, dividendi in sterline** (copia dati veri, rete)
  1. Scegli un asset Yahoo quotato a Londra in pence (per esempio un ETF `.L`) e uno Yahoo che abbia pagato dividendi.
  2. Sull'asset: **Sync**, la versione **completa** (la finestra avvisa che sovrascrive). Conferma.
  3. Guarda l'ultimo prezzo e un prezzo di alcuni anni fa. Poi gli eventi **Dividend**.
  - **Atteso:** le chiusure sono quelle che dà la borsa (senza la rettifica per i dividendi pagati dopo): confrontale con un sito di quotazioni, devono coincidere. Per una linea in pence, il dividendo è in **sterline** (1,95 pence → 0,0195 GBP). I dati salvati prima non cambiano da soli, per questo serve la sync completa. Limite noto scritto nella guida di Yahoo: dopo uno split il passato è già diviso (Apple 4:1 del 31/8/2020, chiusura del 28/8/2020 = 124,81 invece di 499).

- [ ] **X5-4b — Settings › Plugins: nessun gruppo «Tools» oggi** (DB di test)
  1. **Settings › Plugins** come utente normale e come admin.
  - **Atteso:** la scheda si apre senza errori, con i gruppi **Prices** ed **Exchange rates** (solo se un plugin chiede impostazioni). Nessun gruppo **Tools** (nessun tool ha impostazioni oggi). Se non c'è nessun plugin con impostazioni, il testo «No installed plugin asks for settings.»

- [ ] **X5-5 + X5-6 (D-P4) — Il Δ di un periodo accetta qualunque data di partenza, anche d'anno breve** (DB di test)
  1. Apri la pagina di un asset con prezzi (un ETF del DB di prova). Nel campo dell'**inizio** del periodo del grafico (posizione da confermare) scrivi `1850-01-01`, con la fine di oggi.
  2. Guarda il Δ del periodo (la variazione tra inizio e fine). Poi scrivi `0024-03-01` come inizio.
  3. Metti un inizio **dopo** la fine.
  4. Nelle liste **Assets** e **FX** guarda le colonne **1D … 5Y**.
  - **Atteso:** nessun errore e nessun banner rosso. Con `1850-01-01` e `0024-03-01` il Δ si calcola dal primo prezzo che l'asset ha, oppure mostra «—» se non c'è un valore giusto: annotalo; il calendario e il campo tengono l'anno 24 com'è (non 1924). Con l'inizio dopo la fine non parte nessuna richiesta di Δ del periodo e la pagina resta normale. Le colonne 1D…5Y delle liste restano piene. Prima di D-P4 una partenza prima del 1900 veniva alzata al 1900 o la richiesta intera era rifiutata (422) e spariva ogni Δ.

---

## 6. Cruscotto e grafici

- [ ] **Y5-F1…F3 — Icone, descrizioni e badge sulle liste Assets e FX** (DB di test)
  1. **Assets**: nella barra guarda i tre pulsanti di vista. Passa il mouse su ciascuno per mezzo secondo. Fai lo stesso su **Settings**, **Sync All**, **Reload All**.
  2. Metti un periodo lungo (per esempio 5Y) e restringi la finestra o usa la vista a schede più strette: guarda l'angolo in alto a sinistra di una scheda.
  3. Apri **Settings** (impostazioni del grafico), passa la vista a **Rolling Return** e guarda l'elenco dei segnali.
  4. Ripeti i punti 1 e 2 su **FX**.
  - **Atteso:** il primo pulsante ha l'**icona del grafico a linea** (la stessa delle schede), suggerimento «Show absolute»; poi **%**; poi l'icona del **calendario** per il Rolling Return. Ogni pulsante e **Settings / Sync All / Reload All** mostrano una descrizione di una riga dopo circa mezzo secondo. Quando il grafico raggruppa i giorni in settimane o mesi, la scheda mostra subito un badge **Weekly** o **Monthly**. Con un segnale di rendimento sovrapposto, **gli indicatori tecnici non compaiono** nell'elenco (restano salvati). Sulle coppie FX lo stesso.

- [ ] **Y5-F4 (+ X5-F4b) — Si sceglie l'asset di confronto con il pannello condiviso**
  1. **Assets › Settings** (o il grafico di un asset › **Signals**) › **Asset Comparison**, aggiungi un confronto.
  2. Guarda il pannello: ricerca, filtri **Type** e **Currency**, ordine, righe.
  3. Cerca un asset con nome molto lungo. Chiudi il pannello e guarda il campo chiuso.
  4. Scegli un asset già usato da un altro confronto.
  5. Apri una coppia **FX** › **Signals** › **Asset Comparison**.
  - **Atteso:** c'è una casella di ricerca, i filtri **Type** e **Currency** (senza voce vuota), i **benchmark** in cima, un clic sceglie e chiude. L'asset del grafico stesso è grigio e non si può scegliere. Un asset già confrontato porta un segno di avviso ma si può scegliere. Il nome lungo scorre nel campo chiuso e le righe hanno il nome intero nel suggerimento (`title`). Sulla coppia FX compare la sezione dei benchmark (solo con le unioni di X e Y fatte).

- [ ] **Y5-2 — Grafico «Return of the positions» sul Cruscotto** (copia dati veri; porta 6151)
  1. **Dashboard**, vista **Portfolio** in modalità **Table**. Sotto la tabella guarda il grafico (con niente spuntato).
  2. Spunta due posizioni. Poi altre tre.
  3. Clicca il nome nella leggenda per spegnere e riaccendere una linea. Passa il mouse sulla leggenda di una posizione **chiusa** e di una con **prezzo mancante**.
  4. Passa tra **Abs** e **%**. Cambia periodo e valuta.
  5. Su una posizione apri **Analyze Lots** (menu **⋮** o clic destro). Poi premi **← Portfolio** e, in un secondo giro, il tasto Indietro del browser.
  6. Ricarica la pagina con la vista scelta.
  - **Atteso:** senza spunte, solo la linea del portafoglio. Ogni spunta aggiunge una linea (fino a 50). **Abs** = guadagno/perdita in denaro dall'inizio del periodo; **%** = base 100: tutte le linee partono da 100 il primo giorno (112 = +12 %). Una bandiera segna la posizione chiusa (la sua linea finisce il giorno della chiusura, la data è nel suggerimento); un segno di attenzione marca quella con prezzo o cambio mancante, che salta quei giorni. Cambio periodo o valuta: le stesse posizioni vengono ridisegnate. **Analyze Lots** **sostituisce** la vista Portfolio/Period, con **← Portfolio** per tornare; anche il tasto Indietro torna (aggiunge un passo alla cronologia). La vista Abs/% è ricordata. Una nota dice che la linea del portafoglio è il rendimento del Cruscotto (TWRR) e può differire da quello delle posizioni.

- [ ] **Y5-2 — Lo stesso grafico nella pagina di un broker, e la torta «By Asset»**
  1. **Brokers** › apri un broker › blocco delle posizioni (**Holdings**) › passa a **Table**, spunta due posizioni.
  2. Apri **Analyze Lots** da una posizione del broker.
  3. Torna al **Dashboard**, pannello **Asset Allocation**: tab **By Asset**. Guarda **Now** (torta) e poi **History** (area).
  4. Applica il filtro broker. Ricarica la pagina.
  - **Atteso:** nel broker il grafico disegna **solo** le posizioni di quel broker; **Analyze Lots** si apre **sotto** la lista (qui non sostituisce la vista). Il tab **By Asset** ha una fetta per ogni asset più **Liquidity**; la **History** include anche le posizioni **chiuse** (si vedono nei giorni in cui le avevi); il filtro broker restringe asset e liquidità; i colori sono gli stessi tra torta e storia (il primo colore va all'asset più pesante oggi). Il tab scelto è ricordato dopo il ricarico.

- [ ] **D-P4 (Y5-3) — I grafici di un portafoglio lungo sono a gradini e il tooltip legge il giorno puntato** (copia dati veri; porta 6151)
  1. **Dashboard**, periodo **All**, vista **Portfolio**. Nel grafico principale (crescita e prestazioni) passa il mouse lungo la linea e **tra** due punti.
  2. Stringi il periodo a pochi mesi (risoluzione giornaliera) e guarda come sono disegnate le linee. Poi torna ad **All**.
  3. Guarda se compare il badge **Weekly** o **Monthly** quando il grafico raggruppa i giorni (posizione da confermare).
  4. Pannello **Asset Allocation**: **History** (area) del tab che usi, con il mouse sopra.
  5. Vista **Table**, spunta due posizioni: grafico «Return of the positions», mouse sopra, tooltip.
  6. **Analyze Lots** su una posizione: i due grafici dei lotti (il confronto tra lotti e quello del prezzo medio d'acquisto con il prezzo di mercato; nomi da confermare), mouse sopra.
  7. Cambia periodo, valuta e filtro broker, e guarda se i grafici si ridisegnano.
  - **Atteso:** i numeri sono gli stessi di prima (parità provata su 214 casi, 6 copie): cambia solo come sono disegnati. A risoluzione giornaliera ogni serie è una **scala a gradini**: il valore resta fino al giorno in cui cambia qualcosa. Il tooltip dà il valore del **giorno su cui sei** (non quello del punto più vicino): a metà di un gradino leggi il valore del gradino, non quello del dopo. La linea **MWRR** unisce solo punti veri (inizio e fine di ogni gradino, e a ogni fine mese dentro un gradino lungo più di 62 giorni), con la data nel tooltip. Settimanale o mensile: il badge compare solo dove i giorni sono raggruppati. Nel grafico delle posizioni il tooltip elenca, per ogni linea disegnata, quello che dice in quel giorno; una posizione chiusa finisce il giorno della chiusura. Nei lotti le linee sono a gradini e il tooltip legge il giorno puntato. Un solo numero cambia di proposito: le candele del P&L nei **weekend** (prima si ricalcolavano per un «venerdì + 8» spurio). La pagina di un broker (**Brokers** › broker) e la Dashboard si comportano allo stesso modo.
  - **Con un refuso nella data:** il caso del refuso (anno 24 o anno 1) è nella voce MF-P1c + P4, qui sotto.

- [ ] **X5-F1 — Rolling Return nella pagina di una coppia FX** (DB di test)
  1. **FX** › apri una coppia (per esempio EUR → USD). Sopra il grafico due pulsanti: **Prices** e **Rolling Return**.
  2. Passa a **Rolling Return**. Prova le finestre **1W**, **1M**, **3M**, **1Y**, **Custom** (2 settimane). Apri il pulsante **?**.
  3. Aggiungi un confronto con un'altra coppia FX nel pannello **Signals**.
  4. Inverti la direzione (USD → EUR). Guarda se **Measure** e **Edit Rates** sono visibili.
  5. Esci e rientra nella pagina. Torna alla lista **FX**: la scheda di quella coppia.
  - **Atteso:** il grafico mostra la variazione del cambio sugli ultimi N giorni di calendario. Con la finestra 3M e un cambio di 1,0845 oggi contro 1,0500 novanta giorni fa, il punto dice **+3,3 %**. Senza scelta la finestra è automatica (la preset più grande che sta nel periodo). **Custom** accetta settimane, mesi o anni interi. **?** apre la stessa spiegazione degli asset. Il confronto aggiunge la linea della seconda coppia con la stessa finestra, e in questa vista il pannello offre solo il confronto FX. Invertendo la direzione il segno si capovolge. **Measure** e **Edit Rates** non ci sono in Rolling Return (tornano con **Prices**). Modo e finestra sono ricordati; una scheda della lista in Rolling Return apre la pagina nello stesso modo. Spinner mentre ricalcola; se non si può calcolare, il grafico dice il motivo.

- [ ] **Z-14b / Z-15 — Dopo il recupero dei prezzi, pagine e pannelli si aggiornano da soli** (copia dati veri, **con** lo scheduler)
  1. Avvia il server sulla copia **senza** `--no-scheduler`, quando i prezzi della copia sono vecchi di giorni (porta 6151).
  2. Appena sei dentro, apri in schede diverse: la pagina di un asset Yahoo, una coppia FX, la lista **Assets**, un pannello di rischio e **Analyze Lots** aperti.
  3. Aspetta la fine dell'avviso «Updating prices…» in alto.
  - **Atteso:** quando l'avviso sparisce, prezzi, Δ e grafici delle pagine aperte si aggiornano **da soli, in silenzio**: nessun giro dell'icona di aggiornamento, nessuna pagina «occupata», le cifre restano a video finché arrivano le nuove. Se la copia è già aggiornata, il recupero non cambia niente e non c'è nulla da vedere: annotalo. Occhio ai limiti dei provider (errori 429).

---

## 7. Numeri e analisi (DB di test)

- [ ] **B5 + Y5-F5 — Riga «Transfers at market value» nella tabella del periodo**
  1. Serve un trasferimento di titoli tra due broker. Cercalo in **Transactions** (tipo **Asset Transfer**). Se non c'è, crealo: 10 quote comprate a 50 sul broker A (costo 500 €), inviate al broker B quando valgono 80 l'una (800 €); per i prezzi usa un asset senza provider con prezzi a mano.
  2. **Dashboard**: filtro broker = **solo A**, vista **Period**, tabella **Other Period Effects**.
  3. Filtro = **solo B**. Poi **A e B insieme**.
  4. Cambia lingua in IT e riguarda la tabella e il grafico delle prestazioni.
  - **Atteso:** con **solo A** compare la riga **Transfers at market value** a **+300 €** (le quote escono a 800 di capitale con 500 di costo); con **solo B** **−300 €**; con **A e B** la riga non c'è. Il **residuo «Other / reconciliation residual»** scende esattamente dello stesso importo rispetto a prima (stesso totale, diviso in più righe). In italiano la riga si chiama «Trasferimenti al valore di mercato» (anche nel grafico delle prestazioni), non in inglese.

- [ ] **MF-P1c + P4 (+ D-P4) — Una data molto vecchia non rompe i rendimenti, non blocca il server e non ha più il pavimento del 1900**
  1. Crea un broker «Prova 1900». **Add Transaction**: **Deposit** di 1 000 € datato `1850-01-02` (prima del 1900: il modulo chiede una conferma, vedi W5-10), poi una **Buy** di 10 quote di un asset con prezzi a mano il `1850-01-03` (anche se i prezzi sono solo recenti: prima del primo prezzo la posizione vale il suo costo).
  2. **Dashboard**: filtro sul solo broker «Prova 1900», periodo **All**. Guarda le carte **MWRR cumulative** e **MWRR annualized** e la linea **MWRR cumulative** del grafico. Guarda anche da che giorno parte il grafico.
  3. Torna al filtro normale, periodo **All**: guarda quanto ci mette la pagina.
  4. **Il refuso:** aggiungi un **Deposit** di 100 € datato `0024-03-01` (un anno scritto troppo corto) e conferma. Ripeti i punti 2 e 3. Poi prova anche `0001-01-01`.
  5. Cancella il broker di prova (o le sue transazioni) alla fine.
  - **Atteso:** la pagina si apre in pochi secondi e il server non esaurisce la memoria (con P4 l'engine tiene solo i giorni calcolati): con le serie a gradini un refuso all'anno 1 costa come i suoi cambiamenti (circa 288 punti e 0,7 MB, circa 1 secondo; prima dei gradini erano oltre 4 GB). La storia **parte dal primo movimento**, in qualunque anno (1850, 24, 1): non c'è più il pavimento del 1900 e **nessun avviso del Cruscotto** sul 1900 (l'avviso «TRANSACTIONS_BEFORE_FLOOR» è stato tolto). Nel grafico l'anno si legge `0024`, non 1924. Nessun numero assurdo (centinaia di per cento, come 250,19 o 379,19 prima della cura) sul MWRR: dove non c'è un valore giusto la carta mostra **«—»** e la linea ha un buco. Il resto dei numeri (TWRR, NAV) è plausibile. Le cifre di «All» di un portafoglio con righe prima del 1900 ora contano da quelle righe.

- [ ] **MF-P1d — Il MWRR non dice «10 %» nel giorno del versamento di un conto ripartito da zero**
  1. Crea un broker «Prova MWRR». **Deposit** di 1 000 € il `2026-01-02`, poi **Withdrawal** di tutti i 1 000 € il `2026-02-02` (il conto va a zero).
  2. **Deposit** di 1 000 € il `2026-03-02`, e una **Buy** il giorno dopo, con un asset che ha i prezzi.
  3. **Dashboard**, filtro sul solo broker «Prova MWRR», un periodo che parte il `2026-02-15` (conto vuoto). Guarda la linea **MWRR** del grafico sul `2026-03-02`, e le carte MWRR con un periodo che finisce proprio quel giorno.
  4. Alla fine cancella il broker di prova.
  - **Atteso:** sul giorno del versamento la linea ha un **buco** e le carte MWRR mostrano **«—»**, con il motivo «MWRR non calcolabile». Il TWRR resta normale. Dal giorno dopo il MWRR ha di nuovo un valore. Prima della cura quel giorno si leggeva **10 %** (il punto di partenza del calcolo, non un rendimento).

- [ ] **Z5-F1 — Il rendimento che non si può calcolare dice quali giorni e cosa risincronizzare**
  1. Asset con una storia di prezzi più corta della finestra scelta: per esempio un asset senza provider con prezzi solo degli ultimi 20 giorni.
  2. Apri l'asset, **Rolling Return** con finestra **1M** (o altra più lunga della storia).
  3. Cerca il messaggio vicino al grafico o nel pannello **Signals** (posizione da confermare). Cambia lingua in IT.
  - **Atteso:** un messaggio tradotto, non inglese, del tipo «N punti di questo rendimento non si possono calcolare, dal AAAA-MM-GG al AAAA-MM-GG, perché un prezzo necessario manca o non è utilizzabile. Risincronizza i prezzi di questo asset dal … al … e riprova.» Se **tutti** i punti mancano: «Questo rendimento non si può calcolare: i N punti, dal … al …, non hanno un prezzo utilizzabile.…» Le date sono giorni veri della finestra. Se il caso non scatta (la storia corta è trattata come finestra normale), annotalo: il caso preciso del messaggio è da confermare.

---

## 8. Documentazione

- [ ] **DOC-1 — Pagine admin divise: menu a gruppi, pagine nuove, vecchi indirizzi, link dell'app**
  1. `./dev.py mkdocs serve` (porta 6042). Apri **Admin Manual** nel menu.
  2. Controlla il menu a gruppi annidati e apri ogni pagina nuova: *Public Access (Funnel)*, *Reverse Proxy*, *Your Instances*, *Panel API*, *Backups and Restores*, *Scheduled Wake-up*, *Secrets and Plugins*, *Checks and Protections*, *Accounts and Asset Search*, *Links and Messages*, *Troubleshooting*, *Backups* (CLI), *Sealed Backups*, *Moving and Troubleshooting*.
  3. Cambia lingua (IT, FR, ES) e guarda le **etichette dei gruppi**.
  4. Apri a mano i vecchi indirizzi con àncora: `…/admin/hosting_providers/#initial-admin`, `…/admin/cli_tools/#backup-pending`, `…/admin/backup_restore/#sealed`.
  5. Nell'app: **Settings › Administration › Security**, clicca la guida di un controllo (per esempio `owner_email_change` nell'istanza `managed`).
  - **Atteso:** 14 pagine nuove, tutte nel menu e leggibili, nessun errore o link rotto che noti. Le etichette dei gruppi sono tradotte nelle quattro lingue. I vecchi indirizzi finiscono nella pagina giusta: `hosting_instances/#initial-admin`, `cli_backup/#backup-pending`, `backup_sealed/#sealed`. I link dell'app aprono la pagina nuova, non una pagina senza il paragrafo. Gli indirizzi delle pagine restano piatti (`/admin/<pagina>/`).

- [ ] **DOC-2 — La ricerca nella documentazione segue la lingua della pagina**
  1. Con `./dev.py mkdocs serve` apri una pagina **italiana** (indirizzo con `/it/`). Apri il pannello **Network** del browser, filtra «search_index».
  2. Apri la ricerca e scrivi `backup`.
  3. In cima ai risultati spunta «Cerca anche nelle altre lingue».
  4. Ripeti su una pagina inglese.
  - **Atteso:** su una pagina italiana si scarica `search_index.it.json` (circa **1,4 MB**), non `search_index.json` (circa 10,5 MB); i risultati sono solo italiani. La casella è il primo elemento dei risultati. Spuntandola la pagina si **ricarica**, la ricerca si riapre con quello che avevi scritto e i risultati arrivano da tutte e quattro le lingue (pagine solo inglesi del manuale per sviluppatori comprese: in italiano senza la casella non si trovano). Su una pagina inglese: `search_index.en.json` (circa 6 MB). La scelta resta dopo un ricarico.

- [ ] **DOC-3 (H5-9, B5-1j/k2/l, A5-4/7, H5-6/7/8) — Le pagine dell'host dicono quello che il codice fa adesso**
  1. `./dev.py mkdocs serve` (porta 6042). **Admin Manual › Maintenance & Operations › Backup, Restore & Moving › Overview** (`backup_restore`): la sezione «The Owner Keeps Their Password: Restore from the Hosting Panel» (le quattro condizioni, il diagramma, l'avviso «For the host: the accepted risk») e «More Accounts Than the Plan Allows».
  2. **Admin Manual › Deployment & Exposure › Hosting for Others › Your Instances** (`hosting_instances`): «A Wrong Address Was Confirmed: Giving the Instance Back» e «Restoring a Backup on a Managed Instance: the Owner».
  3. **CLI Admin Tools › Backups** (`cli_backup`): «The Owner's Account on a Restore from the Command Line». **Hosting for Others › Panel API** (`hosting_panel_api`): la tabella dello stato.
  4. **Hosting for Others › Backups and Restores** (`hosting_panel_backups`): «Restoring an Instance from Your Panel» e «When the Instance Key Does Not Match».
  5. **System Configuration › Environment Variables**: *Accounts and Asset Search* (`configuration_accounts`, «When the Plan Gets Smaller») e *Secrets and Plugins* (`configuration_secrets`, «The Key Check»); **Deployment & Exposure › Advanced Docker** (`docker_advanced`, la probe di readiness).
  - **Atteso:** il ripristino dal pannello dice che **sceglie da solo** il titolare (prima l'account che ha già l'indirizzo, poi l'unico admin attivo segnato come titolare, altrimenti nessuno) e che **può tenere la password** del titolare solo se tutte e quattro le condizioni valgono (canale pannello, `managed` con `LIBREFOLIO_ADMIN_EMAIL`, un solo titolare segnato che è admin attivo, indirizzo uguale). Il diagramma si disegna e l'avviso del rischio accettato c'è. Un ripristino con troppi utenti **non è mai rifiutato** (il rapporto ha `users_over_limit`). Lo stato del pannello ha **nove** chiavi (`instance_key` e `users_over_limit` incluse). La probe di readiness elenca `ok`, `behind`, `ahead`, `unknown` (niente `mismatch`) e `database_revision`, `app_version`. `user reassign-owner` è descritto, e le pagine di backup non dicono più «arriva con una modifica successiva». Nessun link rotto che noti. Queste pagine esistono solo in inglese.

---

## 9. Fuori dalla lista

### Non si prova a mano

| Lotto | Perché |
|---|---|
| W-B88 (data operazione di ogni plugin, 87 guardie) | Nessun cambio visibile: sono test su righe con due date diverse. |
| X5-4a / X5-4b (contratto dei campi BRIM, impostazioni dei plugin tool) | Nessun tool o plugin BRIM le dichiara oggi: non c'è niente da vedere. Resta solo la prova «nessun gruppo Tools» (§5). |
| X-Q1…Q3, S1 (prezzi letti per osservazione) | Stesse risposte di prima, solo meno conversioni (3 650 → 2 608): coperto da test. |
| R1 (serie di rischio dalle osservazioni), J5-3, MF5-5, P4 e `d8cb1852c` (motore) | Numeri identici: 202–220 report senza differenze, suite financial-math e roi-fifo-utils. L'effetto visibile (velocità, memoria) è nella voce MF-P1c + P4. |
| #48 lato server (J5-1, J5-2, MF5-1b) | Si vede solo tramite Y5-2. |
| M-1, M-2 (immagini Docker arm64 e firma) | Girano su GitHub a ogni rilascio. Il comando di verifica è nella guida Docker avanzata. |
| H5-3 (istanza chiusa finché il titolare non è assegnato), B5-1b (`--recover owner`), B5-1c/d/e (link `/setup` salvo, ripristino con la funzione vera di A), A5-2 (casi di sicurezza: `EMAIL_TAKEN`, un crash a metà, token piantati) | Servono errori forzati: li copre la suite `backup-owner-real` e i test di A/H. Il caso felice è nelle voci B5-1. |
| B5-1 (backup con email o username doppi) | Rifiutati alla conferma: non si crea a mano dall'app (le email sono uniche). Coperto da test. |
| DOC-1 (controllo dei riferimenti) | Un test confronta ogni link dell'app con il sito costruito e ogni àncora spostata (`test_docs_admin_references`). La voce DOC-1 qui sotto guarda solo la navigazione. |
| Z5-F1 (i rami del calcolo del messaggio) | Le frasi stanno nei file di lingua e i casi sono nei test; la voce §7 le guarda una volta. |
| H5-10 (ordine dei passi all'avvio: il controllo della chiave dell'istanza prima di quello dei segreti dei plugin) | Cambia solo l'ordine di due passi; coperto da test. L'effetto visibile è la voce H5-7. |
| H5-12 (test di risveglio sul motore privato) | Solo test. |
| Z5-S1 (la sospensione del cloud: dopo una sospensione l'istanza dimentica i controlli armati prima e tiene la tolleranza del risveglio) | La verifica la fa il coordinatore del cloud su una nightly: serve una macchina che si sospende davvero. |
| D-P4, parte AI Export (l'export legge la storia a gradini, bucket delle prestazioni, NAV medio) | Nessun cambio visibile: sondato su 6 copie, 360 costruzioni, 0 differenze fuori dalle sezioni del drawdown. Il resto di D-P4 è nelle voci §4, §6 e §7. |
| `stale_fx_pairs` (la qualità dei dati elenca i cambi con più di 7 giorni) | Solo nella risposta del server: non c'è ancora nessun banner. |
| B5-1l (il ripristino dal pannello dell'host tiene la password del titolare) | Serve il pannello: un ticket firmato Ed25519 per ogni chiamata, una macchina in attesa di ripristino e un backup `.lfbk`. Lo coprono le suite `backup-owner-kept` (servizi, API, CLI) e le prove API del pannello. Da terminale e dall'app la password si chiude sempre: si vede in B5-1j. Le pagine sono in DOC-3. |
| A5-3 (la 006 fusa nella 005) | Nessuna voce. Serve lo script di riparazione per la tua nightly, che il coordinatore ti dà a parte. |
| H5-5 (la guardia del titolare) | Solo test. |
| Altri admin di un backup (deciso: restano come sono) | Nessuna voce a parte: si vede nella variante di B5-1. |

### Non ancora committato o fermo su una decisione (aggiornato al 27/10)

| Lotto | Stato | Cosa cambierà nella lista |
|---|---|---|
| **Treni 9 e 10** | — | checklist da preparare quando fai la push |

Tutti gli altri lotti dell'ondata 5 sono nel candidato `8f7282ff6` e hanno la loro voce, o stanno nella tabella «Non si prova a mano». Sono usciti da questa tabella: MF-P1d, W5-2c, W5-6, W5-8, B5-1f e B5-1g (voci già nel §4, §2 e §7); A5-3 e H5-5 (nessuna voce); la conferma della nuova email del titolare e B5-1i (ora voci A5-1b + H5-4 e B5-1j); MF-P4b e D-P4 (fatti: voci nel §4, §6 e §7).

---

## 10. Conteggio

| Gruppo | Voci |
|---|---|
| 1. Account e accessi | 6 |
| 2. Backup e ripristino | 8 |
| 3. Pannello hosting e istanza | 4 |
| 4. Import e Bulk (e form transazioni) | 8 |
| 5. Plugin, asset e impostazioni | 6 |
| 6. Cruscotto e grafici | 7 |
| 7. Numeri e analisi | 4 |
| 8. Documentazione | 3 |
| **Totale** | **46** |
