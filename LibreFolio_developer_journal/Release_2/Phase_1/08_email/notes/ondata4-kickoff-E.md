# Brief — workstream E · Email · i testi di E-25, E-26 ed E-7 scelti dal developer — bozza

> **A cosa serve (per il developer).** Nell'ondata 3 E-25 ed E-26 sono entrati con testi «consigliati, da confermare»: chi si registra quando l'email è trattenuta legge una frase scelta da E, non da te. Con questo lotto le frasi sono le tue, nelle 4 lingue, e il riquadro ha il colore che hai scelto. Costo: una riga per testo; parte appena rispondi alle domande 9 del piano (E-26-q1, E-26-q2, E-25-q1; E7-Q4 ed E7-Q5 li fa A in `UserRow`, con i testi che tu confermi qui).

**Modello**: Haiku (testi nei cataloghi; per un dubbio di contenuto chiedi al coordinatore).
**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-stunning-fortnight` · **Branch**: `e-alfy-e-email`
**HEAD di partenza (da verificare)**: `c042f2481` (fast-forward dal coordinatore da `8fdeab4d6`).
**Corsia**: porta `6182`, cartella dati `/tmp/librefolio-r13-e`.
**Piano e contratto**: `08_email/plan-phase01Email.prompt.md` (sezione E-26); `salvataggi-worktrees-20261021/ondata3/E-26-contratto.md` §3 (i testi nelle 4 lingue) e §8 (le domande).

## Cosa fare (dopo le risposte del developer)
1. **E-26-q1**: se (A) i testi di oggi restano e togli il segno «da confermare» nei cataloghi; se (B) sostituisci `email.verification.registeredHeld` nelle 4 lingue con la variante corta del §3.
2. **E-26-q2**: se (a) nulla; se (b) riquadro giallo per il caso trattenuto: tocca `LoginCard.svelte` e i gestori di `gotoLogin` in `routes/+page.svelte` e `routes/invite/+page.svelte`, che sono **di A**: in quel caso fai la richiesta ad A tramite il coordinatore e tu cambi solo i cataloghi.
3. **E-25-q1**: se (b) il link «Torna all'accesso» anche sulla pagina «Conferma il mio indirizzo»: una riga e due test (uno Vitest, un E2E in `auth-email-verification.spec.ts`).
4. **E7-Q5**: conferma ad A i testi fr/es del badge e il suggerimento it (sono nei cataloghi di A, non nei tuoi: tu dai solo il via con le parole esatte).
5. Rossi prima dove il comportamento cambia (il testo mostrato, il link): Vitest `auth` (`auth.test.ts` fissa il testo di accesso: aggiornalo), `api email-verification-hooks`, `i18n check`, `front check` dopo `api sync`. E2E `auth-email-verification` nello slot solo se hai toccato la pagina.
6. Se il developer non risponde entro la fine dell'ondata: nessun codice, il lotto resta aperto con i testi «consigliati» e il backlog lo dice.

## File condivisi
- Tuoi: `frontend/src/lib/i18n/auth/*.json` (`email.verification.*`), le pagine di verifica email, `auth-email-verification.spec.ts`.
- Di A: `LoginCard.svelte`, `routes/+page.svelte`, `routes/invite/+page.svelte`, `UserRow.svelte`, i cataloghi di Utenti.

## Non fare
- Non toccare i file di A. Non cambiare il contratto `verification_email` (`sending`/`held`): è entrato nel treno 8.

## Fatto quando
Le risposte applicate, segni «da confermare» tolti, rossi→verdi, `i18n check` verde, doc `developer/backend/email.md` allineata se un testo è citato, piano aggiornato, righe CHANGELOG: nessuna nuova (la voce «Email verification at sign-up» è già riscritta; se un testo cambia, proponi la correzione di quella riga), **CHECKPOINT READY** e **FROZEN**.
