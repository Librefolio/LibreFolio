# Regole comuni a tutti i figli (ondata 2, 21/10/2026)

Sei una **sessione figlia** della release LibreFolio 1.3.0. Il coordinatore è la sessione che ti ha avviato: riceve da solo il tuo ultimo messaggio quando chiudi un turno. **Non aspettare risposte dentro un turno**: se ti serve una decisione o un'autorizzazione, scrivila come ultima cosa e chiudi il turno.

## Prima di tutto
1. Leggi `CLAUDE.md` (radice del tuo worktree) e `.claude/agents/coordinated-workstream.md`: sono le tue regole.
2. Verifica la base: `git rev-parse HEAD` deve essere uguale al SHA scritto nel tuo brief. Se è diverso, **fermati e dillo**.
3. Il tuo lavoro è descritto nel **piano** del tuo workstream (percorso nel brief) e nella tua sezione del backlog `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md`. Leggi la sezione del piano indicata, non l'intero file (centinaia di KB).

## Divieti
- **Git: nessuna operazione che cambi la storia.** Niente commit, merge, rebase, reset, stash, checkout di file, push. Il coordinatore fa i commit quando gli consegni un checkpoint.
- Non toccare il lavoro non committato che non è tuo e **non cancellare, ripristinare o sovrascrivere** i file sporchi che trovi: sono il tuo lavoro in corso.
- Non installare dipendenze: niente `npm install/update/ci`, `pipenv install/sync/update`, `./dev.py install`.
- Mai `npx` (usa `frontend/node_modules/.bin/<tool>`). Mai `./dev.py` nudo.
- Non toccare file fuori dal tuo perimetro. Se serve, chiedi.
- Niente decisioni di prodotto: ogni scelta del prodotto è una domanda per il developer, tramite il coordinatore.
- Non usare mai la porta di produzione 6040 e non toccare dati reali.

## Come si lanciano i comandi su questa macchina (Linux)
- Prefisso obbligatorio: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py ...` (il venv `LibreFolio-SAUMUTtc` è un alias del venv Linux). Per i test aggiungi la tua corsia: `--test-port <PORTA> --data-dir <DIR>` (scritti nel brief).
- La tua corsia in `/tmp` **non esiste**: `/tmp` si svuota a ogni riavvio. Creala solo quando serve, con `... dev.py test --test-port <PORTA> --data-dir <DIR> db populate --force --clean`, e solo dentro la tua cartella.
- Carico della macchina: `cut -d' ' -f1 /proc/loadavg` (il `sysctl -n vm.loadavg` dei documenti è per macOS). Controlli leggeri (un file Vitest, `front check`, prettier, ruff, un file pytest) solo con carico sotto 8; **corse pesanti** (E2E, una categoria intera, `all-backend`, la galleria) **solo dentro uno slot che ti dà il coordinatore**.
- La macchina ha 16 core e 15 GB di RAM (il 21/10 si è arrivati a 1 GB liberi con due `front check` in parallelo). **Ogni comando pesante in memoria passa da un solo lucchetto**, un solo alla volta in tutta la macchina:
  `flock /tmp/librefolio-heavy.lock <comando>` — vale per `front check`, Vitest su più di 3 file, `mkdocs build`, l'E2E, ogni categoria intera. Restano liberi pytest di una suite o azione, `prettier`, `ruff`, `git diff`.
- Playwright: Chromium 1228 installato dal developer il 21/10 e provato (lancio headless ok). Gli E2E sono corse pesanti: solo con lo slot del coordinatore e dentro `flock`.
- Docker è installato ma la sessione non ha ancora il gruppo `docker`: per te Docker non c'è.
- **Lingua di sistema `it_IT`**: ogni test frontend (Vitest, E2E, `front-utility …`) si lancia con `LC_ALL=en_US.UTF-8` davanti, altrimenti 3 test di `OtherPeriodEffectsTable.test.ts` falliscono per un difetto del test (noto, non tuo).
- **Dopo ogni aggiornamento della base** lancia `... dev.py api sync` nel tuo worktree prima di `front check`: `generated.ts` è ignorato da git e resta vecchio (falso rosso già visto su Y).
- **Altre sessioni lavorano in parallelo a te** (fino a sei). Lo slot pesante è uno per tutta la macchina: se `flock` ti fa aspettare, aspetta; non lanciare corse pesanti fuori dal lucchetto.
- I `node_modules` del tuo worktree sono stati reinstallati per Linux (`npm ci`) dal coordinatore; se trovi binari `darwin` fermati e dillo.
- Le vecchie cartelle `files/` della tua sessione Copilot (script, patch parcheggiate, bozze) stanno in `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/copilot-enel/session-state/<uuid>/files/`. Gli script lì dentro hanno percorsi del Mac (`/Users/ea_enel/Documents/00_My/LibreFolio` → il tuo worktree; `/Users/ea_enel/.copilot/session-state/...` → la cartella sopra). Leggili, non lanciarli senza adattarli.

## Sotto-agenti (risparmio di token)
- Lavori piccoli e delimitati (cercare, contare, leggere un log, una modifica meccanica) vanno a sotto-agenti leggeri con l'`Agent` tool: `model: "haiku"` per letture e inventari, `"sonnet"` per test, doc e patch di routine. Chiedi report brevi (lista, verdetto, file:riga). **Verifica tu** ogni risultato prima di costruirci sopra. Mai due sotto-agenti sugli stessi file.

## Regole di lavoro
- Prima i rossi: ogni cambiamento di comportamento ha un test che fallisce per il motivo giusto, poi la cura. Per scrivere o riparare test usa l'agente `test-author`; per le pagine MkDocs, `docs-writer` (solo inglese; le traduzioni solo su richiesta esplicita del developer).
- Aggiorna il tuo piano dopo ogni passo: ✅ con data, `> **Note implementazione**: ...`, e `> **⚠️ Fuori pista**: ...` per le deviazioni.
- Rispetta il perimetro dei file condivisi: `scripts/test_runner/*` (una riga additiva per volta), `api sync`, cataloghi i18n, navigazione MkDocs, CHANGELOG (solo proponi le righe), migrazioni (non toccarle).

## Come si consegna
Chiudi il lavoro con un **CHECKPOINT READY** (o un **BLOCCATO** con la domanda). Il messaggio contiene: SHA di partenza (HEAD) e SHA di `dev_release2`; numero esatto di file toccati (tracciati e nuovi); i file che escludi (generati, `.testLog`, `test-results/`, site di mkdocs); prove con numeri (cosa era rosso, cosa è verde, comandi esatti); conflitti attesi; righe del CHANGELOG proposte; messaggio di commit proposto (Conventional Commits, inglese, soggetto sotto 72 caratteri). Poi scrivi **FROZEN** e **non toccare più nulla** finché il coordinatore non ti scrive.

Lingua: i report al coordinatore in italiano semplice con esempi concreti; codice, commit e documentazione in inglese.
