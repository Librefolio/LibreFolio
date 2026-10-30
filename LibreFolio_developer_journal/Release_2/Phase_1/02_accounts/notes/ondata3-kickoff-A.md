# Brief — workstream A · Account e accessi · A-62 (tre ritocchi) poi revisione del contratto di E-26

> **A cosa serve (per il developer).** Tre cose piccole:
> 1. il pulsante del menu ha un nome leggibile nella lingua dell'utente (oggi un lettore di schermo dice sempre «Toggle menu» in inglese);
> 2. un segnale invisibile `data-security-checks` (off / pending / ready / error) sulla riga dei controlli di sicurezza, così i test e la galleria aspettano che i controlli siano caricati invece di indovinare i tempi;
> 3. una descrizione nel registro dei test per `services admin-bootstrap`.
> Poi A fa da **revisore** di E-26: lo schema della risposta di registrazione e `RegisterCard` sono file di A.

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-legendary-winner` · **Branch**: `e-alfy-a-account-e-accessi`
**HEAD di partenza (da verificare)**: il coordinatore ha committato la tua sezione di piano rimasta sporca («H-61 entrato; la fixture di G; A-62 col segnale», righe ~8840-8867 del piano) e ha fuso `dev_release2` (`2879ae3e4`) nel tuo ramo: lo SHA esatto è nel messaggio d'avvio. `npm ci` fatto per Linux.
**Corsia**: porta `6185`, cartella dati `/tmp/librefolio-r13-a`.
**Piano**: `LibreFolio_developer_journal/Release_2/Phase_1/02_accounts/plan-phase01Accounts.prompt.md`: A-62 (righe ~8739-8800) e la tua sezione ~8840-8867. Backlog A-62 ~5172-5180.

## Passo A — A-62 (tutte e tre le parti decise dal coordinatore il 20/10)
1. `frontend/src/lib/components/layout/Header.svelte`: `menuLabel` parte da `$_('nav.toggleMenu')`. Chiave nuova nelle 4 lingue della base i18n: en «Toggle menu», it «Apri o chiudi il menu», fr «Ouvrir ou fermer le menu», es «Abrir o cerrar el menú».
2. Segnale `data-security-checks` sulla radice della riga dei controlli (componente di `ConnectionSecurityIndicator`): `off` (non admin), `pending`, `ready` (anche durante il ricontrollo), `error` (prima lettura fallita).
3. Una riga `desc` nel registro per `services admin-bootstrap`.
- Rossi: `Header.test.ts`, `ConnectionSecurityIndicator.test.ts`. Poi cura, `services admin-bootstrap` (riferimento: 302 verdi), `i18n check`, `front check` (in `flock`). **Solo Vitest, nessuno slot E2E.**
- Consegna **CHECKPOINT READY (A)** e FROZEN.

## Passo B — revisione di E-26 (quando il coordinatore ti gira l'analisi di E)
Rileggi il contratto proposto da E (campo della risposta di `POST /auth/register`, testi, `RegisterCard.svelte`) e rispondi con un verdetto breve: va bene / cosa cambiare e perché. Non scrivi codice di E.

## Passo C — E-7 (decisione del developer del 21/10: in 1.3, dopo A-62)
> **A cosa serve.** Oggi chi si registra e non clicca il link di verifica compare in Utenti come «Disattivato»: l'admin crede di averlo bloccato lui. Con E-7 compare il badge «In attesa di verifica».
- Piano: `LibreFolio_developer_journal/Release_2/Phase_1/08_email/plan-phase01Email.prompt.md` (righe ~9176-9240), backlog ~9182. Era un lotto di E sui tuoi file: in questa ondata lo fai tu.
- Decisioni del developer: **Q1 sì**, il badge anche quando il link è scaduto (come «In attesa di configurazione»); **Q2** testi en «Waiting for verification», it «In attesa di verifica» (fr ed es dalla stessa radice, li proponi tu nel checkpoint), più il suggerimento al passaggio del mouse; **Q3 no**: il comando `user list` resta senza il segno.
- Campo nuovo `AdminUserRead.pending_verification`, badge in `UserRow`, suggerimento, doc admin (solo inglese). `api sync` necessario. Prima i rossi (backend e Vitest), poi la cura. Gli avatar N69-4 sono già in dev nelle stesse righe: attenzione a non romperli.
- Consegna **CHECKPOINT READY (C)** e FROZEN.

## Non fare
- Niente E2E, niente decisioni sui testi oltre a quelli scritti sopra.
- Non toccare `backend/app/api/v1/auth.py` (lo toccano H ed E).

## Fatto quando
A-62 verde e committabile (**CHECKPOINT READY** e **FROZEN**); revisione di E-26 consegnata quando arriva.
