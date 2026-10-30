# Brief — workstream A · Account e accessi · N69c (chi può iscriversi, in Utenti), N69d («Guida» sui controlli di Sicurezza), testi di `UserRow` — bozza

> **A cosa serve (per il developer).** Dalle tue prove del 19/10 (N69): oggi «chi può iscriversi» (aperta, su invito, chiusa) si cambia solo nelle Impostazioni globali; con N69c lo fai dalla scheda **Utenti**, accanto a «Invita», con conferma solo per «aperta», e se la variabile `LIBREFOLIO_REGISTRATION` lo blocca lo vedi scritto. Con N69d ogni riga della scheda **Sicurezza** ha un pulsante «Guida» (libro, nuova scheda) che apre la pagina giusta della documentazione, dalla mappa che H ha messo in `checkGuides.ts`. In più, appena il developer risponde a E7-Q4 ed E7-Q5, il badge «In attesa di verifica» di `UserRow` ha i testi fr/es e il suggerimento che ha scelto.

**Modello**: Sonnet.
**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-legendary-winner` · **Branch**: `e-alfy-a-account-e-accessi`
**HEAD di partenza (da verificare)**: `c042f2481` (fast-forward dal coordinatore da `e6738808f`).
**Corsia**: porta `6185`, cartella dati `/tmp/librefolio-r13-a`.
**Piano**: `02_accounts/plan-phase01Accounts.prompt.md`: analisi N69-3 e N69-5 (~7633-7760), il via del lotto N69 (~8301-8358: N69c alla ~8352, N69d alla ~8356).

## Cosa fare
1. **N69c** (parte subito): modulo comune `features/settings/registrationMode` (le opzioni, «bloccata dalla variabile», il salvataggio con `PATCH /settings/global/bulk` e la rilettura della configurazione), usato da Utenti e da Impostazioni globali; in Utenti, nella prima sezione accanto a «Invita»: si salva alla scelta, con conferma solo per «aperta». Prima i rossi (Vitest del modulo e della scheda; un E2E in `settings` che cambia il modo da Utenti e lo rilegge in Impostazioni globali), poi la cura. Il backend (`config/accounts.py`, `registration_mode_override`) non cambia.
2. **N69d** (parte subito): «Guida» (`DocsLink`, libro, nuova scheda) su ogni riga della scheda Sicurezza, dalla mappa `frontend/src/lib/features/instance/checkGuides.ts` (è in dev: verifica la forma e il test `checkGuides.test.ts`). Un controllo senza voce nella mappa: nessun pulsante, e un test che lo fissa. Prima i rossi.
3. **`UserRow`** (dopo le risposte E7-Q4 ed E7-Q5, con le parole esatte confermate da E): hover + pannello, solo hover o solo pannello; testi fr/es del badge e il suggerimento it/en/fr/es. Una riga per scelta. Se non arrivano: lascia com'è, è già marcato «da confermare».
4. Verdi: Vitest (`component-unit` in `flock`), `front check` dopo `api sync`, `i18n check`, E2E `settings` e `api users-admin` nello slot. Ratchet dei colori pulito (solo ruoli, nessun `dark:`).
5. Doc con `docs-writer`: `admin/configuration.en.md` o la pagina delle impostazioni dove «chi può iscriversi» è spiegato (una frase: anche da Utenti); timbro Aphra se la pagina è tradotta (`mkdocs translate-stamp`).

## File condivisi
- Tuoi: `features/settings/**` (Utenti, Sicurezza, `registrationMode`), `UserRow.svelte`, i cataloghi di Utenti e Sicurezza, `LoginCard.svelte`, `routes/+page.svelte`, `routes/invite/+page.svelte` (se E-26-q2 = (b), la richiesta arriva da E tramite il coordinatore).
- Di E: `i18n/auth/*.json`, le pagine di verifica email. Di H: `checkGuides.ts` (solo lettura: se manca una voce, chiedila a H).

## Non fare
- Non toccare `checkGuides.ts` (H) né i cataloghi di E. Niente testi fissi nei componenti.

## Fatto quando
N69c e N69d rossi→verdi con E2E nello slot, `UserRow` secondo le risposte (o rimandato con nota), doc, piano aggiornato, righe CHANGELOG proposte (✨ «Chi può iscriversi anche dalla scheda Utenti»; ✨ «Guida su ogni controllo di Sicurezza»), **CHECKPOINT READY** e **FROZEN**.
