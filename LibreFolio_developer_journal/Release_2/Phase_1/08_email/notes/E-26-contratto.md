# E-26 (b) — Il contratto: l'email trattenuta dopo la registrazione

> Workstream E, ondata 3, 22/10/2026. **Solo analisi, nessun codice.**
> Base: worktree `e-alfy-stunning-fortnight`, branch `e-alfy-e-email`, HEAD `bb11f147984b…` (E-25 committato),
> `dev_release2` = `2879ae3e4`.
> Decisione dello sviluppatore (20/10, 14:3x): la (b), cioè un campo nella risposta di `POST /auth/register` per
> l'email trattenuta, più il testo (a) per il caso normale. A rivede il contratto dopo A-62. Le affermazioni qui
> sotto sono rilette sul codice di `bb11f1479`.

## 1. Cosa succede oggi (verificato)

- `backend/app/api/v1/auth.py:320-332`: con la verifica accesa, `verification_required = not user.is_active`.
  - Se `email_verification.registration_email_allowed(rate_limit_address(http_request))` è vero, la route accoda
    `registration_email_work` (l'email parte **dopo** la risposta).
  - Altrimenti (10 email di registrazione all'ora dallo stesso indirizzo, IPv6 per /64) non accoda nulla e scrive
    il log `Verification email held: too many registrations from this address`.
  - In entrambi i casi risponde 201 con `verification_required: true` e
    `message: "Registration successful: check your email to activate the account"`.
- `backend/app/schemas/auth.py:114-119`: `AuthRegisterResponse` ha `user`, `message`, `verification_required`.
- `frontend/src/lib/features/auth/RegisterCard.svelte:105` (di A) torna all'accesso con
  `email.verification.registered` («Account created. We sent you an email…») oppure `auth.accountCreated`. Il
  messaggio compare nel riquadro verde `login-success` di `LoginCard.svelte:57-60`.
- Un indirizzo senza chiave (nessun indirizzo, o un proxy locale non fidato: `rate_limit_address` lo salta, H-36)
  **non** è limitato: l'email parte sempre.

## 2. Il campo proposto

```python
# backend/app/schemas/auth.py, AuthRegisterResponse
verification_email: Optional[Literal["sending", "held"]] = Field(
    default=None,
    description=(
        "Only when verification_required: 'sending' when the verification email leaves after this answer (it can "
        "still fail later, unseen here); 'held' when no email goes now (too many registrations from this client "
        "address in the last hour): the owner signs in to ask for the link again. null without verification."
    ),
)
```

| Caso | `verification_required` | `verification_email` | Esempio |
| --- | --- | --- | --- |
| Verifica spenta, o primo account dell'istanza | `false` | `null` | l'amministratore iniziale |
| Verifica accesa, email accodata | `true` | `"sending"` | la registrazione normale |
| Verifica accesa, nessun indirizzo o proxy locale non fidato | `true` | `"sending"` | due visitatori dietro lo stesso proxy Docker (EVH-014) |
| Verifica accesa, 11ª registrazione nell'ora dallo stesso indirizzo | `true` | `"held"` | un ufficio con un solo IP pubblico |

Perché queste scelte:
- **«sending», non «sent»**: l'email parte dopo la risposta. «sent» sarebbe falso già nel momento in cui lo diciamo.
- **«held» generico**, non `held_by_address`: oggi la causa è una sola. Se un giorno la route controllerà anche altri
  limiti prima di rispondere, il valore resta lo stesso e il contratto non cambia.
- **`null` senza verifica**: il campo ha senso solo quando c'è un'email da mandare. Il frontend confronta solo
  `=== 'held'`, quindi regge anche il difetto noto del client generato, che allarga i campi nullabili
  (`wiki/problems/generated-client-widens-nullable-scalar.md`).
  - Variante per A: un campo sempre presente, `Literal["none", "sending", "held"] = "none"`. È più esplicito ma
    ripete `verification_required`. Io consiglio la versione nullabile.
- **Nessun `retry_after`**: chi è trattenuto può chiedere subito «Send the link again» all'accesso. Quel pulsante ha
  un limite suo (10 ogni 15 minuti per indirizzo) e il «trattenuto» non conta nei limiti per account, perché il token
  è senza indirizzo. EVH-013 lo prova già: 200, e il link parte.
- **Il `message` inglese dell'API** nel caso trattenuto diventa
  `"Registration successful: the activation email is held (too many registrations from this address); sign in to ask for a new link"`.
  L'interfaccia non lo mostra, ma oggi direbbe «check your email», che è falso.
- **Sicurezza**: «held» dice solo che *il tuo* indirizzo ha fatto 10 registrazioni nell'ora. Non dice nulla di
  altri account né della casella di posta, e non apre un modo per indovinare chi è registrato. Il limite per casella
  (3 all'ora) resta **fuori** dalla risposta proprio per questo: guardarlo prima di rispondere direbbe a chiunque si
  registri con l'indirizzo di un altro se quella casella ha appena ricevuto email.

## 3. I testi (nuovi: decide lo sviluppatore)

**Caso normale, chiave esistente `email.verification.registered`.** È il testo (a), già approvato in inglese. Le
traduzioni le propongo io, con le parole che il catalogo già usa (`expired`, `resent`):

| Lingua | Testo |
| --- | --- |
| en (approvato) | Account created. We are sending you an email with a link to activate it: open it within 24 hours, then sign in. No email after a few minutes? Check the spam folder, then sign in with your username and password: you will be offered a new link. |
| it | Account creato. Ti stiamo mandando un'email con un link per attivarlo: aprilo entro 24 ore, poi accedi. Nessuna email dopo qualche minuto? Controlla lo spam, poi accedi con nome utente e password: ti verrà proposto un link nuovo. |
| fr | Compte créé. Nous vous envoyons un e-mail avec un lien pour l'activer : ouvrez-le dans les 24 heures, puis connectez-vous. Pas d'e-mail après quelques minutes ? Vérifiez les spams, puis connectez-vous avec votre nom d'utilisateur et votre mot de passe : un nouveau lien vous sera proposé. |
| es | Cuenta creada. Te estamos enviando un correo con un enlace para activarla: ábrelo en las próximas 24 horas y luego inicia sesión. ¿No llega ningún correo en unos minutos? Revisa el spam y luego inicia sesión con tu nombre de usuario y tu contraseña: se te ofrecerá un enlace nuevo. |

**Caso trattenuto, chiave nuova `email.verification.registeredHeld`.** Ci sono due varianti; consiglio la A, perché
dice il motivo e chi è in un ufficio con un solo IP capisce cosa è successo.

| Lingua | Variante A (consigliata, con il motivo) | Variante B (corta) |
| --- | --- | --- |
| en | Account created, but the activation email could not leave now: too many sign-ups from your network in the last hour. Sign in with your username and password: you will be offered a new link. | Account created. The activation email could not leave now: sign in with your username and password to get a new link. |
| it | Account creato, ma l'email di attivazione non può partire ora: troppe registrazioni dalla tua rete nell'ultima ora. Accedi con nome utente e password: ti verrà proposto un link nuovo. | Account creato. L'email di attivazione non può partire ora: accedi con nome utente e password per avere un link nuovo. |
| fr | Compte créé, mais l'e-mail d'activation ne peut pas partir pour le moment : trop d'inscriptions depuis votre réseau au cours de la dernière heure. Connectez-vous avec votre nom d'utilisateur et votre mot de passe : un nouveau lien vous sera proposé. | Compte créé. L'e-mail d'activation ne peut pas partir pour le moment : connectez-vous avec votre nom d'utilisateur et votre mot de passe pour obtenir un nouveau lien. |
| es | Cuenta creada, pero el correo de activación no puede salir ahora: demasiados registros desde tu red en la última hora. Inicia sesión con tu nombre de usuario y tu contraseña: se te ofrecerá un enlace nuevo. | Cuenta creada. El correo de activación no puede salir ahora: inicia sesión con tu nombre de usuario y tu contraseña para obtener un enlace nuevo. |

## 4. I file che toccherò

| File | Di chi | Cosa |
| --- | --- | --- |
| `backend/app/schemas/auth.py` | A (contratto) | il campo `verification_email` in `AuthRegisterResponse`; la descrizione di `verification_required` («a link is on its way») diventa vera in entrambi i casi |
| `backend/app/api/v1/auth.py` (`register`, ~:320-332) | A (route) | `verification_email = "sending"` o `"held"` nei due rami già presenti, il `message` del caso trattenuto, la docstring |
| `frontend/src/lib/features/auth/RegisterCard.svelte:105` | A | una riga: `held` → `email.verification.registeredHeld`, altrimenti come oggi |
| `frontend/src/lib/i18n/email/{en,it,fr,es}.json` | E | `registered` aggiornata con `i18n update`, `registeredHeld` aggiunta con `i18n add` |
| Test | E | `backend/test_scripts/test_api/test_email_verification_hooks_api.py`, `frontend/src/lib/features/auth/RegisterCard.verification.test.ts`, `frontend/src/lib/features/email/emailText.test.ts` (le chiavi nelle 4 lingue) |
| Doc (solo inglese) | E | sotto, sezione 7 |
| Generati, ignorati da git | — | `api sync` → `frontend/src/lib/api/openapi.json` e `generated.ts`. Nessun file tracciato cambia: la prova è un `grep verification_email` su `generated.ts` |

Nessuna migrazione, nessun file del runner, nessuna rotta nuova.

## 5. I rossi previsti (con `test-author`, prima della cura)

**Backend**, `test_email_verification_hooks_api.py`: aggiungo `verification_email` alle asserzioni che già leggono
`verification_required`.
- EVH-001 (registrazione normale) → `"sending"`;
- EVH-002 (primo account) → `null`;
- EVH-003 (con invito) → `"sending"`;
- EVH-005 (opzione spenta) → `null`;
- EVH-013 (limite per indirizzo a 1) → la prima `"sending"`, la seconda `"held"`, e il `message` della seconda non
  dice più «check your email»;
- EVH-014 (due visitatori dietro un proxy privato) → tutte e due `"sending"`;
- EVH-015 e EVH-016 → `"sending"`, poi `"held"`;
- **nuovo EVH-017** (proposto, fissa onestamente il limite): la casella è già a 3 email nell'ora, quindi la risposta
  è 201 `"sending"`, poi nessuna email parte e l'account aspetta col suo token senza indirizzo. Così il «sending che
  non arriva» resta scritto in un test, non solo nella doc.

Oggi tutti questi casi sono rossi per `KeyError: 'verification_email'`, il motivo giusto. Corsa:
`PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6182 --data-dir /tmp/librefolio-r13-e api email-verification-hooks`.
È una sola azione, in processo; se il runner chiede il DB della corsia, prima
`… db populate --force --clean` nella mia cartella.

**Frontend**, `RegisterCard.verification.test.ts`:
- RCV-01 con `verification_email: "sending"` esplicito → `email.verification.registered`;
- **nuovo RCV-04**: `"held"` → `email.verification.registeredHeld`;
- **nuovo RCV-05**: `verification_required: true` senza il campo (un server più vecchio) → `email.verification.registered`;
- RCV-02 e RCV-03 restano come sono.

`emailText.test.ts`: `registered` e `registeredHeld` nelle 4 lingue, senza segnaposto (oggi nessun ETX controlla
`registered`). Se lo sviluppatore approva q3, anche `loginRequired`.

## 6. Cosa resta invisibile (da scrivere nella doc)

`"sending"` vuol dire «accodata», non «consegnata». Dopo la risposta, `registration_email_work` può ancora non
mandare nulla. In questi casi la pagina mostra il testo normale, che è vero anche così, perché dice cosa fare se
l'email non arriva:
- il limite per casella: 3 email di verifica all'ora alla stessa casella (`VERIFICATION_BY_MAILBOX`). Resta fuori
  dalla risposta apposta, vedi la sicurezza nella sezione 2;
- il budget orario dell'istanza (`LIBREFOLIO_SMTP_MAX_PER_HOUR`);
- un guasto SMTP, o i link non più disponibili (`LIBREFOLIO_PUBLIC_URL`);
- un riavvio del processo prima che il task parta.

Tutti questi casi finiscono solo nel log del server (`Verification email: not sent` / `the request failed`).
L'account aspetta col suo token senza indirizzo, e «Send the link again» lo recupera.

## 7. Le righe di doc da unire con quelle di E-25 (`bb11f1479`)

- `mkdocs_src/docs/user/getting-started.en.md`:
  - il passo 1 (:72-73), che E-25 ha lasciato com'era: la citazione diventa il testo (a);
  - una riga nuova vicino al punto 📭 (:84 circa) per il caso trattenuto;
  - il passo 3 e i punti 🖱️ 🙋 di E-25 (:76-82) restano.
- `mkdocs_src/docs/admin/email.en.md`:
  - «Right after the registration» (:514-515): i due testi;
  - la tabella dei limiti (:589, le 10 registrazioni): «the login page says so»;
  - la riga del limite per casella (:593): resta senza avviso, e lo dico;
  - un paragrafo su cosa resta invisibile (sezione 6);
  - le voci di E-25 (:521-535) restano.
- `mkdocs_src/docs/developer/backend/email.md`:
  - il punto «Registration» (:742-756): il campo e i valori; correggo anche la deriva `client_address(http_request)`
    → `rate_limit_address(http_request)`, perché il codice usa la seconda da H-36;
  - `RegisterCard` (:1004-1005);
  - gli intervalli dei test (:1416 EVH-001…017, :1421 RCV-01…05).
- `mkdocs_src/docs/developer/architecture/access_control.md:270`: la riga della tabella di registrazione.
- `mkdocs_src/docs/developer/frontend/components/features/auth.md:186`: la riga «Success» di `RegisterCard`.
- Traduzioni di `getting-started` e `admin/email`: restano debito, senza timbro, come per E-25.

## 8. Domande per lo sviluppatore

- **E-26-q1, il testo del caso trattenuto**:
  - (A) **consigliata**, con il motivo: «…too many sign-ups from your network in the last hour…»;
  - (B) corta, senza il motivo.
  - I testi nelle 4 lingue sono nella sezione 3. Le traduzioni del testo (a) sono anche loro una proposta.
- **E-26-q2, il colore del riquadro**: oggi ogni messaggio dopo la registrazione è nel riquadro verde `login-success`.
  - (a) **consigliata**: resta verde. L'account è stato creato; il testo dice il passo dopo. Nessun file di A in più.
  - (b) un riquadro giallo di avviso per il caso trattenuto. Tocca anche `LoginCard.svelte` e il gestore di
    `gotoLogin` in `routes/+page.svelte` e `routes/invite/+page.svelte` (file di A): un tono accanto al messaggio.
- **E-26-q3, `loginRequired`**: il testo del caso trattenuto dice «sign in», e all'accesso la pagina risponde «open
  the link in the email we sent you», che per un account trattenuto è falso. È proprio il percorso che indichiamo.
  - (a) **consigliata**: dentro il lotto, una chiave ×4, nessun codice: «Your email address is not verified yet: open
    the link of the activation email, or ask for a new one below.» (it «Il tuo indirizzo email non è ancora
    verificato: apri il link dell'email di attivazione, oppure chiedine uno nuovo qui sotto.»; fr «Votre adresse
    e-mail n'est pas encore vérifiée : ouvrez le lien de l'e-mail d'activation, ou demandez-en un nouveau
    ci-dessous.»; es «Tu dirección de correo aún no está verificada: abre el enlace del correo de activación o pide
    uno nuevo aquí abajo.»);
  - (b) lasciarla com'è, e la voce va nel backlog.
- **Per A (revisione del contratto)**: il nome `verification_email`, i valori `sending` e `held`, nullabile contro
  sempre presente (sezione 2).

## 9. Costo, rischi, ordine

- **Costo**: piccolo, 2-3 ore con la doc.
- **Rischi**:
  - il client generato e i campi nullabili: lo copre il confronto `=== 'held'`;
  - EVH-014/015/016 sono di H-36: cambio solo le asserzioni sul campo nuovo, non la loro parametrizzazione;
  - conflitto testuale con A se A-62 tocca `AuthRegisterResponse` o `RegisterCard.svelte:105`: per questo prima
    serve A-62 committato.
- **Ordine**:
  1. i rossi (backend e frontend);
  2. la cura dello schema e della route;
  3. `api sync` e il grep su `generated.ts`;
  4. `RegisterCard` e le chiavi ×4;
  5. le prove: l'azione pytest, i 2 file Vitest, `i18n check`, i gate, ruff/black, `front check` dentro `flock`;
  6. la doc, il piano, il backlog e il wiki;
  7. il CHECKPOINT READY (B).
- **Fatto quando**: rossi → verdi; il campo nello schema OpenAPI e in `generated.ts`; `front check` 0/0; la doc
  inglese unita a quella di E-25; le righe del CHANGELOG proposte (la voce «Email verification at sign-up» in
  `[Unreleased]`: «`POST /auth/register` answers `verification_required` and `verification_email` (`sending` or
  `held`)», e «…the accounts are created without their email, and the sign-up says so…»).
