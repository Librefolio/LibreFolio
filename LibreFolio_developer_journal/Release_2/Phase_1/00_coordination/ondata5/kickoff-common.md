# Regole comuni a tutti i figli (ondata 5, 23/10/2026) — bozza

Sei una **sessione figlia** della release LibreFolio 1.3.0. Il coordinatore è la sessione che ti ha avviato: riceve da solo il tuo ultimo messaggio quando chiudi un turno. **Non aspettare risposte dentro un turno**: se ti serve una decisione o un'autorizzazione, scrivila come ultima cosa e chiudi il turno.

Il tuo brief personale è `kickoff-<SESSIONE>.md` in questa cartella; il brief dell'ondata (sola lettura, per il contesto) è `BRIEF-ondata5.md`. Dove il tuo kickoff e questo file dicono cose diverse, vale il kickoff.

## Prima di tutto
1. Leggi `CLAUDE.md` (radice del tuo worktree) e le regole dell'agente `coordinated-workstream` (`.claude/agents/coordinated-workstream.agent.md`): lavori **come** quell'agente (analisi prima, solo il tuo worktree e il tuo perimetro, corsia isolata, checkpoint al coordinatore, mai la storia di Git).
2. Verifica la base: `git rev-parse HEAD` deve essere uguale allo SHA scritto nel tuo kickoff (`1fd80c481` = `dev_release2`, treni 9 e 10 dentro). Se è diverso, **fermati e dillo**. (W2 è nuovo: parte da `dev_release2`, stesso SHA.)
3. Il tuo lavoro è nel **piano** del tuo workstream (percorso nel kickoff, sotto `LibreFolio_developer_journal/Release_2/Phase_1/`) e nella tua sezione del backlog `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` (oltre 10 000 righe: `grep` sugli ID, non leggerlo tutto). Per il tuo piano apri una sezione nuova «Ondata 5» (W2: file nuovo, vedi il suo kickoff).
4. **Primo turno: analisi breve** (cosa farai, file che toccherai, rossi che scriverai, domande). I lotti marcati **PARTI SUBITO** nel tuo kickoff partono senza aspettare il via, subito dopo l'analisi, nello stesso turno; gli altri aspettano il via del coordinatore **solo se** il kickoff dice «aspetta il via».

## Divieti
- **Git: nessuna operazione che cambi la storia o l'indice.** Niente commit, merge, rebase, reset, stash, checkout di file, `git add`, push. Il coordinatore fa i commit quando gli consegni un checkpoint. Sola lettura (`git status`, `git diff`, `git log`) sì.
- Non toccare il lavoro non committato che non è tuo e **non cancellare, ripristinare o sovrascrivere** i file sporchi che trovi.
- Non installare dipendenze: niente `npm install/update/ci`, `pipenv install/sync/update`, `./dev.py install`. Se manca qualcosa, chiedi al coordinatore.
- Mai `npx` (usa `frontend/node_modules/.bin/<tool>`). Mai `./dev.py` nudo.
- **Un solo scrittore per file.** Il tuo kickoff elenca i file tuoi e quelli che in questa ondata sono di altri (tabella «File condivisi» del brief, §4). Su un file di un altro: leggi, non scrivi; se serve una modifica, scrivila nel checkpoint come richiesta (`file:riga → cosa → perché`) e il coordinatore la gira al proprietario.
- Niente decisioni di prodotto: ogni scelta del prodotto è una domanda per il developer, tramite il coordinatore.
- **Principio del developer (non negoziabile): si protegge solo l'input rilevabile.** Nessuna bonifica o correzione di dati già salvati; un errore di inserimento dell'utente è dell'utente (esempio: un costo mancante scritto a mano non si rifiuta e non si corregge). Una cura che riscrive dati salvati è fuori perimetro: fermati e dillo.
- Non usare mai la porta di produzione 6040 e **non leggere né toccare `backend/data/prod/`**. Dati reali solo con la skill `real-data-copy`, e solo se il tuo kickoff lo dice.

## Come si lanciano i comandi su questa macchina (Linux)
- **Venv condiviso, obbligatorio**: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py ...`. Dall'ondata 5 è sul **lock nuovo**: FastAPI 0.159, SQLAlchemy 2.1.6, SQLModel 0.0.48. Conseguenza per i modelli: un **campo `datetime` nuovo** di un modello SQLModel dichiara `sa_type=DateTime`, come gli altri 38 già fatti (senza, SQLModel 0.0.48 rifiuta le date senza fuso). Se un test rompe per una libreria, dillo subito.
- Per i test aggiungi la tua corsia: `... dev.py test --test-port <PORTA> --data-dir <DIR> <categoria> <azione>` (porta e cartella nel kickoff; due lavori attivi non condividono mai né porta né cartella).
- La tua corsia in `/tmp` **può non esistere** (`/tmp` si svuota a ogni riavvio). Creala con `... dev.py test --test-port <PORTA> --data-dir <DIR> db populate --force --clean`, solo dentro la tua cartella.
- **I log dei test e delle build vanno in `salvataggi-worktrees-20261021/ondata5/<sessione>-<descr>.log`**, non in `/tmp` (tmpfs, si perde). Scrivi il file prima, poi guardalo (`cmd > LOG 2>&1; tail -n 60 LOG`); mai `tee … | head`.
- **Un solo comando pesante alla volta in tutta la macchina**: `flock /tmp/librefolio-heavy.lock <comando>`. Vale per `front check`, Vitest su più di 3 file, `mkdocs build`, E2E, ogni categoria intera, `all-backend`, la galleria. Restano liberi pytest di una suite o azione, `prettier`, `ruff`, `git diff`. Carico: `cut -d' ' -f1 /proc/loadavg`; i controlli leggeri solo con carico sotto 8.
  - **`/tmp` può essere svuotato da un riavvio.** `flock` ricrea il file del lucchetto da solo, ma se un lavoro in background sembra fermo controlla: (1) che `/tmp/librefolio-heavy.lock` esista; (2) che un processo lo tenga davvero (`fuser /tmp/librefolio-heavy.lock`); (3) che la tua cartella dati della corsia esista ancora. Se manca la corsia, ricreala (sopra) e rilancia.
  - **Le corse pesanti (E2E, categoria intera, galleria, `all-backend`) solo dentro uno slot che ti dà il coordinatore**; l'ordine degli slot è in `ORDINE-avvii.md`.
- 16 core, 15 GB di RAM. Playwright: Chromium installato. Docker: non disponibile.
- **Test frontend con la lingua di sistema `it_IT`**: ogni test frontend si lancia con `LC_ALL=en_US.UTF-8` davanti.
- Il tuo worktree è già al nuovo HEAD ma `generated.ts` è ignorato da git e resta vecchio: lancia `... dev.py api sync` una volta prima del primo `front check`.
- I `node_modules` sono per Linux (`npm ci` fatto dal coordinatore); se trovi binari `darwin`, o mancano (worktree nuovo), fermati e dillo.
- Fino a dieci sessioni lavorano in parallelo a te: se `flock` ti fa aspettare, aspetta.

## Sotto-agenti (risparmio di token)
- Lavori piccoli e delimitati (cercare, contare, leggere un log, una modifica meccanica) vanno a sotto-agenti con l'`Agent` tool: `model: "haiku"` per letture, inventari e lavori meccanici; `"sonnet"` per test, doc e patch di routine. **Verifica tu** ogni risultato. Mai due sotto-agenti sugli stessi file. Il modello per lotto è nel tuo kickoff: «Haiku» vuol dire che lo esegue un sotto-agente Haiku e **tu rivedi** il diff.
- **Test**: per scrivere o riparare test usa l'agente `test-author` (regole di isolamento, registrazione nel runner, definizione di fatto). **Documentazione**: agente `docs-writer`, **solo inglese** (`.en.md`); le traduzioni it/fr/es sono **debito dichiarato** (giro unico con Aphra, su richiesta del developer): non tradurre, non toccare i file `.it/.fr/.es`. Timbro Aphra solo per correzioni puntuali (`./dev.py mkdocs translate-stamp --file <pagina>.en.md`), mai dopo una riscrittura. Rosso non ovvio: skill `test-triage` prima di dire «flaky».

## Regole di lavoro
- **Prima i rossi** (con `test-author`): ogni cambiamento di comportamento ha un test che fallisce per il motivo giusto, poi la cura. Nei test, niente posizioni fisse, niente conteggi globali, niente attese a tempo, niente asserzioni su testo tradotto (tutti i test della stessa corsia dividono un solo database e un solo backend).
- **La matematica finanziaria ha una sola casa**: `backend/app/services/financial_math/`. Cercala lì prima di scrivere un calcolo; i calcoli nuovi vanno lì; mai una copia locale o parziale; se ne trovi una, segnalala nel checkpoint. (I file di `financial_math/` sono di MF, salvo dove il tuo kickoff dice altro.)
- Colori e temi: solo i ruoli (`bg-lf-*`, `text-lf-*`, `border-lf-*`), mai `dark:` su un ruolo, mai un colore scritto a mano (skill `design-system`); il ratchet dei colori deve restare pulito.
- Testi dell'interfaccia nelle 4 lingue (en/it/fr/es) tramite i cataloghi: `./dev.py i18n ...` (skill `devpy-i18n`), mai stringhe fisse nei componenti, mai testo tradotto nei selettori dei test (`data-testid`). Il catalogo generato (`npm run i18n:build`) è del coordinatore al treno.
- API cambiata → `dev.py api sync`. Modello DB cambiato → migrazione Alembic incrementale (**non toccarle tu**: chiedi al coordinatore).
- Codice, commenti, docstring e documentazione **in inglese**; i report al coordinatore in **italiano semplice, con esempi concreti**.
- File comuni additivi (`scripts/test_runner/*`: una riga per volta; cataloghi i18n; baseline dei colori; `CHANGELOG.md` e `mkdocs.yml`/nav: **solo proponi**): non li modifichi tu salvo dove il kickoff dice altro.
- **Aggiorna il tuo piano dopo ogni passo**: ✅ con data, `> **Note implementazione**: ...`, e `> **⚠️ Fuori pista**: ...` per le deviazioni. Se il contesto si azzera, il piano deve bastare a riprendere.
- Una domanda di prodotto ferma **solo quel pezzo**: se il tuo lotto ha altre parti indipendenti, vai avanti con quelle e chiudi il turno solo quando non puoi più fare nulla senza la risposta.

## Come si consegna
Chiudi ogni checkpoint con **CHECKPOINT READY** (o **BLOCCATO** con la domanda). Il messaggio contiene: SHA di partenza (HEAD) e SHA di `dev_release2`; **a quale treno appartiene** (11a o 11b, come nel kickoff); numero esatto di file toccati (tracciati e nuovi) con l'elenco; i file che escludi (generati, `.testLog`, `test-results/`, site di mkdocs); prove **con numeri** (cosa era rosso, cosa è verde, comandi esatti, conteggi dei test); conflitti attesi con altri lotti; **riga CHANGELOG proposta** (✨/🔄/🐛, in italiano semplice, per l'utente) **o «nessuna»** con il perché; voci di backlog per ciò che lasci per dopo; messaggio di commit proposto (Conventional Commits, in inglese, soggetto sotto 72 caratteri). Poi scrivi **FROZEN** e **non toccare più nulla** finché il coordinatore non ti scrive.

Dove il kickoff separa più checkpoint, ognuno ha il suo CHECKPOINT READY e il suo FROZEN: dopo il primo, **non** iniziare i lotti successivi finché il coordinatore non ha committato (così il commit contiene solo ciò che hai consegnato).

## Due treni
- **Treno 11a** (lotti piccoli, appena verdi): H (`users_used/users_limit`, X-R84, DOC-2), B (tutto), A (tutto), Y (Z-14b + ritocchi F1-F4), X (Z-35, C-65a, rolling return FX), W (W-B88, B2, C-70b), W2 (V-37b), Z (Z5-F1).
- **Treno 11b** (motori e lotti larghi): MF (P4, pavimenti, B5, P1c), Z (Q1…S1), J (#48, R1), Y (#48 frontend), X (N68, CP12), W (W-B87 con lo split, E-21 + W-B80, campo di CP12), W2 (#47), H (DOC-1, riordino della guida admin, solo documentazione, ultimo). Prima del gate, revisione dei numeri di MF.
Il treno di ogni lotto è scritto nel kickoff: dillo nel checkpoint.
