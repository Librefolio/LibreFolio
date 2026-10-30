# Regole comuni a tutti i figli (ondata 4, 22/10/2026) — bozza

Sei una **sessione figlia** della release LibreFolio 1.3.0. Il coordinatore è la sessione che ti ha avviato: riceve da solo il tuo ultimo messaggio quando chiudi un turno. **Non aspettare risposte dentro un turno**: se ti serve una decisione o un'autorizzazione, scrivila come ultima cosa e chiudi il turno.

## Prima di tutto
1. Leggi `CLAUDE.md` (radice del tuo worktree) e `.claude/agents/coordinated-workstream.md`: sono le tue regole.
2. Verifica la base: `git rev-parse HEAD` deve essere uguale allo SHA scritto nel tuo brief (`c042f2481` = `dev_release2`, treno 8 + filtro + lock di justETF). Se è diverso, **fermati e dillo**.
3. Il tuo lavoro è descritto nel **piano** del tuo workstream (percorso nel brief) e nella tua sezione del backlog `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` (10 250 righe: usa grep sugli ID, non leggerlo tutto). Il piano dell'ondata è `salvataggi-worktrees-20261021/ondata4/PIANO-ondata4.md` (sola lettura).
4. **Prima turno: solo analisi.** Leggi il codice che toccherai, scrivi cosa farai, i rossi che scriverai, i file che toccherai e le domande. Consegna l'analisi e aspetta il via, salvo che il brief dica «parti subito».

## Divieti
- **Git: nessuna operazione che cambi la storia.** Niente commit, merge, rebase, reset, stash, checkout di file, push. Il coordinatore fa i commit quando gli consegni un checkpoint.
- Non toccare il lavoro non committato che non è tuo e **non cancellare, ripristinare o sovrascrivere** i file sporchi che trovi.
- Non installare dipendenze: niente `npm install/update/ci`, `pipenv install/sync/update`, `./dev.py install`.
- Mai `npx` (usa `frontend/node_modules/.bin/<tool>`). Mai `./dev.py` nudo.
- Non toccare file fuori dal tuo perimetro (tabella «File condivisi» di `PIANO-ondata4.md`). Se serve, chiedi.
- Niente decisioni di prodotto: ogni scelta del prodotto è una domanda per il developer, tramite il coordinatore.
- Non usare mai la porta di produzione 6040 e non toccare dati reali (`backend/data/prod/`).

## Come si lanciano i comandi su questa macchina (Linux)
- Prefisso obbligatorio: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py ...`. Per i test aggiungi la tua corsia: `--test-port <PORTA> --data-dir <DIR>` (scritti nel brief).
- La tua corsia in `/tmp` **non esiste** all'avvio (`/tmp` si svuota a ogni riavvio). Creala con `... dev.py test --test-port <PORTA> --data-dir <DIR> db populate --force --clean`, solo dentro la tua cartella.
- **I log non vanno in `/tmp`** (è un tmpfs e si perde): scrivili in `salvataggi-worktrees-20261021/ondata4/<sessione>-<descr>.log`.
- Carico della macchina: `cut -d' ' -f1 /proc/loadavg`. Controlli leggeri (un file Vitest, `front check`, prettier, ruff, un file pytest) solo con carico sotto 8; **corse pesanti** (E2E, una categoria intera, `all-backend`, la galleria) **solo dentro uno slot che ti dà il coordinatore**.
- 16 core, 15 GB di RAM. **Ogni comando pesante in memoria passa da un solo lucchetto**, uno alla volta in tutta la macchina: `flock /tmp/librefolio-heavy.lock <comando>`. Vale per `front check`, Vitest su più di 3 file, `mkdocs build`, l'E2E, ogni categoria intera. Restano liberi pytest di una suite o azione, `prettier`, `ruff`, `git diff`.
- Playwright: Chromium installato e provato. Docker: non disponibile per le sessioni.
- **Lingua di sistema `it_IT`**: ogni test frontend si lancia con `LC_ALL=en_US.UTF-8` davanti.
- **Dopo ogni aggiornamento della base** lancia `... dev.py api sync` nel tuo worktree prima di `front check` (`generated.ts` è ignorato da git e resta vecchio).
- **Fino a dieci sessioni lavorano in parallelo a te.** Se `flock` ti fa aspettare, aspetta.
- I `node_modules` del tuo worktree sono per Linux (`npm ci` fatto dal coordinatore); se trovi binari `darwin` fermati e dillo.

## Sotto-agenti (risparmio di token)
- Lavori piccoli e delimitati (cercare, contare, leggere un log, una modifica meccanica) vanno a sotto-agenti leggeri con l'`Agent` tool: `model: "haiku"` per letture e inventari, `"sonnet"` per test, doc e patch di routine. **Verifica tu** ogni risultato. Mai due sotto-agenti sugli stessi file.
- Per scrivere o riparare test usa l'agente `test-author`; per le pagine MkDocs, `docs-writer` (solo inglese; le traduzioni solo su richiesta esplicita del developer); per un rosso non ovvio, la skill `test-triage` prima di dire «flaky».

## Regole di lavoro
- **Prima i rossi**: ogni cambiamento di comportamento ha un test che fallisce per il motivo giusto, poi la cura.
- Aggiorna il tuo piano dopo ogni passo: ✅ con data, `> **Note implementazione**: ...`, e `> **⚠️ Fuori pista**: ...` per le deviazioni.
- Colori e temi: solo i ruoli (`bg-lf-*`, `text-lf-*`…), mai `dark:`, mai un colore scritto a mano (skill `design-system`); il ratchet dei colori deve restare pulito.
- Testi dell'interfaccia nelle 4 lingue (en/it/fr/es) tramite i cataloghi (`./dev.py i18n ...`, skill `devpy-i18n`), mai stringhe fisse nei componenti.
- Rispetta il perimetro dei file condivisi: `scripts/test_runner/*` (una riga additiva per volta), `api sync`, cataloghi i18n, navigazione MkDocs, CHANGELOG (solo proponi le righe), migrazioni (non toccarle).
- Una domanda di prodotto ferma **solo quel pezzo**: se il tuo lotto ha altre parti indipendenti, vai avanti con quelle e chiudi il turno solo quando non puoi più fare nulla senza la risposta.

## Come si consegna
Chiudi il lavoro con un **CHECKPOINT READY** (o un **BLOCCATO** con la domanda). Il messaggio contiene: SHA di partenza (HEAD) e SHA di `dev_release2`; numero esatto di file toccati (tracciati e nuovi); i file che escludi (generati, `.testLog`, `test-results/`, site di mkdocs); prove con numeri (cosa era rosso, cosa è verde, comandi esatti); conflitti attesi; righe del CHANGELOG proposte; voci del backlog per ciò che lasci per dopo; messaggio di commit proposto (Conventional Commits, inglese, soggetto sotto 72 caratteri). Poi scrivi **FROZEN** e **non toccare più nulla** finché il coordinatore non ti scrive.

Lingua: i report al coordinatore in italiano semplice con esempi concreti; codice, commit e documentazione in inglese.

## Dipendenze Python aggiornate (22/10)
Prima dell'avvio il coordinatore ha portato in `Pipfile.lock` **solo** `justetf-scraping` al commit `73afd12` del fork (PR #49 senza conflitti, allocazioni di nuovo lette): `dev_release2` = `c042f2481`. L'aggiornamento completo (FastAPI 0.159, SQLAlchemy 2.1…) è stato provato e tolto: SQLModel 0.0.48 rifiuta le date senza fuso orario, 57 rossi; è un lotto a parte. Il venv condiviso `LibreFolio-SAUMUTtc` è già sincronizzato: **non** lanciare `pipenv install`/`update` dal worktree. Se un test rompe per un cambiamento di libreria, è un'informazione da dare subito al coordinatore.

