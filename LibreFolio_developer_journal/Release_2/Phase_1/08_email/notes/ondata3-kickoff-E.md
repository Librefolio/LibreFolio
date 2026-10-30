# Brief — workstream E · Email · E-25 (conferma con un clic) poi E-26 (b) (dire la verità dopo la registrazione)

> **A cosa serve (per il developer).**
> - **E-25**: oggi la pagina `/verify-email` conferma l'indirizzo appena si apre. I filtri anti-phishing delle caselle aziendali aprono i link da soli, quindi possono «verificare» un indirizzo al posto del suo proprietario. Con E-25 la pagina mostra un pulsante «Conferma il mio indirizzo» e la verifica parte solo con il clic.
> - **E-26 (b)**: dopo la registrazione oggi diciamo sempre «Ti abbiamo mandato un'email», anche quando l'email è stata trattenuta (troppe richieste per quell'indirizzo, 10 l'ora). Con E-26 la risposta del server lo dice e la scheda di registrazione spiega come averne una nuova.

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-stunning-fortnight` · **Branch**: `e-alfy-e-email`
**HEAD di partenza (da verificare)**: `2879ae3e4` (fast-forward fatto dal coordinatore; `npm ci` fatto per Linux).
**Corsia**: porta `6182`, cartella dati `/tmp/librefolio-r13-e`.
**Piano**: `LibreFolio_developer_journal/Release_2/Phase_1/08_email/plan-phase01Email.prompt.md`: E-25 analisi (righe ~9384-9460), decisioni E-25.1 (~9511-9518), E-26 (~9430-9460). Backlog: E-25 ~9451, E-26 ~9456.

## Passo A — E-25 (approvato dal developer il 20/10, con i testi proposti)
Stato nuovo `ready` con il pulsante `data-testid="verify-email-confirm"`; la richiesta parte solo al clic; anche `hashchange` torna a `ready`. 3 chiavi nuove nelle 4 lingue (`i18n/email/*.json`). Solo frontend.
- Rossi con `test-author`: `routes/verify-email/page.test.ts` (12 casi da invertire), `VerifyEmailCard.test.ts` (8 più `ready`). Poi la cura. Poi `front check` (in `flock`), i Vitest toccati.
- E2E facoltativo (oggi nessun E2E visita `/verify-email`): proponilo, lo slot lo do io.
- Doc: `user/getting-started.en.md`, `admin/email.en.md` (solo inglese; le traduzioni restano debito, senza timbro).
- Consegna **CHECKPOINT READY (A)** e FROZEN.

## Passo B — E-26 (b) (solo dopo il via del coordinatore)
Prerequisiti: A-62 committato (sessione A) **e** il commit di H-55 su `backend/app/api/v1/auth.py` (sessione H). Prima di scrivere codice manda al coordinatore una **analisi breve**: nome e valori del campo (proposta `verification_email: "sending" | "held"`), testo del caso trattenuto, file. A rivede il contratto (schema della risposta, `RegisterCard`). Copre solo il limite per indirizzo (`auth.py:322-327`); i guasti SMTP in background restano invisibili: scrivilo nella doc.
- File: `backend/app/api/v1/auth.py`, `backend/app/schemas/auth.py`, `RegisterCard.svelte` (~:105), `i18n/email/*.json`, doc `getting-started.en.md` (~:72), `admin/email.en.md` (~:514). `api sync` necessario.

## Non fare
- Niente decisioni sui testi oltre a quelli già approvati: i testi nuovi di E-26 sono una domanda.
- Non toccare `auth.py` prima del via (lo sta toccando H).

## Fatto quando
A: rossi→verdi, `front check` 0/0, doc e piano aggiornati, checkpoint. B: analisi approvata, rossi→verdi, `api sync` con il diff atteso, verifica di A, doc, **CHECKPOINT READY** e **FROZEN**. Righe CHANGELOG proposte per entrambi.
