# Brief — workstream H · Piattaforma · H-55 v2 (Content Security Policy sempre attiva)

> **A cosa serve (per il developer).** Il browser esegue solo gli script mandati da LibreFolio: se un proxy, una CDN o un'estensione ostile inietta uno script nella pagina, viene bloccato, e l'amministratore lo vede segnalato nella scheda Sicurezza. Esempio: un hotel Wi-Fi che inserisce pubblicità nella pagina non riesce più a farlo. È uno dei pezzi di sicurezza promessi per la 1.3 (decisioni Q1-Q4 del developer, 19/10). È un **cambiamento visibile per chi fa self-hosting dietro proxy strani**: andrà in «Breaking changes».

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-sturdy-memory` · **Branch**: `e-alfy-h-piattaforma`
**HEAD di partenza (da verificare)**: `2879ae3e4` (= `dev_release2`, con H-61 CP2 dentro; fast-forward fatto dal coordinatore).
**Corsia**: porta `6181`, cartella dati `/tmp/librefolio-r13-h`.
**Piano**: `LibreFolio_developer_journal/Release_2/Phase_1/01_platform/plan-phase01Platform.prompt.md`: analisi (riga ~8112), conferma del developer (~9304), piano breve del 20/10 con i passi 0-5 (~9511-9590) e **le condizioni del coordinatore colori su `app.html` (~9555-9573)**. I rossi parcheggiati sono in `files/parked/h55-csp-enforce-reds-on-d6c252ec4.patch` della tua vecchia cartella di sessione Copilot (`/home/alfy/Documenti/02_myRepo/LibreFolio_prj/copilot-enel/session-state/*/files/parked/`, trovala con `find`): vanno **rifatti sulla base di oggi**, non applicati alla cieca.

## Cosa fare
1. **Passo 0, inventario** (serve lo slot pesante, ~1 ora): `all-frontend` con `--lane-setting LIBREFOLIO_CSP_REPORT_ONLY=true` per vedere cosa la politica bloccherebbe oggi. Chiedi lo slot nel primo checkpoint intermedio, con l'elenco atteso.
2. I passi 1-5 del piano: intestazioni sempre inviate (`object-src 'none'; base-uri 'self'; form-action 'self'`; sulle pagine dell'app anche `script-src 'self' 'wasm-unsafe-eval' 'report-sample' <hash>`, `worker-src 'self' blob:`, `connect-src` come da piano; niente `default-src`, niente `style-src`), hash calcolati all'avvio e rinfrescati quando cambia la build, sonda d'indirizzo `GET /api/v1/auth/address-probe.png`, avviso di script iniettato in testa ad `app.html` con controllo nella scheda Sicurezza e voce in `checkGuides.json`, guida `admin/configuration/#csp`.
3. **Condizioni colori su `app.html` (vincolanti)**: anti-FOUC intatto (l'avviso nel suo `try` o **dopo** `classList.add(theme)`); non toccare la decisione del tema e `classList.add` (righe ~17-23), la coppia `theme-color` (~11 e ~27), lo `<style>` dello splash (~39-101); nessun `classList.contains('dark')`; nessun hash scritto a mano; se tocchi `style-src 'unsafe-inline'`, dillo prima. Prima del checkpoint: gate `themeColorMeta`, `themeModeReads`, `themeComponentTokens`, `themeRoles`, `themeTokens`, `documentTitle.guard.test.ts`, `flagFont.gate.test.ts`.
4. Domande aperte del piano (le porti tu nel checkpoint, non le decidi): `--coverage` sulla corsia con la politica attiva; `LIBREFOLIO_PUBLIC_URL` non valido (proposta: log e nessuna origine aggiunta); F1 cheetah-grid come eccezione documentata (`frontend/e2e/csp-baseline.json`).
5. Auto-revisione con l'agente `security-review` sul tuo diff; il coordinatore ne farà una indipendente.

## File condivisi
- `backend/app/api/v1/auth.py`: anche **E-26** (sessione E) dovrà toccarlo più avanti (la risposta di registrazione). Tu ci aggiungi solo la sonda d'indirizzo; E partirà su quel file **dopo** il tuo commit. Se puoi, metti la rotta in un modulo suo e tocca `auth.py` solo per registrarla.
- `scripts/test_runner/*`: categorie `cloud`/`front-cloud` (4b) già approvate, righe additive.

## Fatto quando
Rossi rifatti e verdi, inventario fatto, `app.html` dentro le condizioni con i gate dei temi verdi, E2E del passo 5 nello slot (corsa completa sotto la politica attiva), doc e piano aggiornati, riga «⚠️ Breaking changes» proposta, auto-revisione riportata, **CHECKPOINT READY** e **FROZEN**.
