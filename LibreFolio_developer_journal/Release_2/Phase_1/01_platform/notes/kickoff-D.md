# Brief — workstream D · Dipendenze · l'aggiornamento completo dei pacchetti Python, passando per le date UTC esplicite

> **A cosa serve (per il developer).** Teniamo le librerie aggiornate (sicurezza, correzioni) senza rompere niente. Oggi
> un `pipenv update` completo porta SQLModel 0.0.48 e SQLAlchemy 2.1, che rifiutano una data «nuda» (senza etichetta di
> fuso): il backend lavora già tutto in UTC, ma salva le date come oggetti senza etichetta, UTC per convenzione. Con le
> versioni nuove bisogna dirlo esplicitamente. Risultato atteso: stessi dati e stessi numeri di oggi, librerie aggiornate.

**Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-d-dipendenze` · **Branch**: `e-alfy-d-dipendenze` (nuovo, da `dev_release2`)
**HEAD di partenza (da verificare)**: `c042f2481` + nel worktree il `Pipfile.lock` già aggiornato dal coordinatore (`pipenv update --dev`, non committato): FastAPI 0.159, Starlette 1.9, SQLAlchemy 2.1.6, SQLModel 0.0.48, Pydantic 2.14 e altri.
**Venv: il TUO, separato** — `PIPENV_CUSTOM_VENV_NAME=LibreFolio-D` (già creato e sincronizzato con il lock nuovo). **Mai** usare `LibreFolio-SAUMUTtc` qui: è il venv condiviso delle altre 10 sessioni, con le versioni vecchie. Prefisso dei comandi: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-D pipenv run python dev.py test --test-port 6194 --data-dir /tmp/librefolio-r13-d …`
**Corsia**: porta `6194`, cartella dati `/tmp/librefolio-r13-d`. `npm ci` fatto.
**Modello**: Opus (tocca il significato delle date nel database: va fatto con cura).

## Cosa si sa
- Gate del coordinatore con il lock nuovo (log in `salvataggi-worktrees-20261021/gate-deps/`): `api sync` senza differenze, `front check` 0/0, `mkdocs build` ok; **`all-backend` 57 rossi** su `admin-bootstrap`, `backup-apply`, `broker`, `bulk-reads-chunked`, `email-case`, `user-profile`, `username-rules`, più un errore di raccolta. Errore principale: `ValueError: Datetime values must have timezone information. Use datetime.now(timezone.utc), or annotate the field with NaiveDatetime for naive storage.` (su `users.email_verified_at`, `created_at`, `fx_rates.fetched_at`…).

## Passo 1 — analisi (primo turno, nessun codice)
1. Riproduci i rossi nella tua corsia e fai l'inventario: quali campi `datetime` dei modelli (`backend/app/db/models.py` e dintorni), dove nascono le date nude (codice: `datetime.utcnow()`, `datetime(…)` senza `tzinfo`, letture dal DB; test), e l'errore di raccolta.
2. Confronta le due strade, con numeri (file e righe toccate, rischi):
   - **(1)** campi dichiarati `NaiveDatetime` (UTC sottinteso come oggi): stesso formato su disco, nessuna migrazione;
   - **(2)** date con `tzinfo=UTC` ovunque: cosa diventa su SQLite, se serve una migrazione Alembic incrementale, cosa cambia nelle API (serializzazione con `+00:00`?) e nel client TypeScript.
   Consiglia; il developer decide (il coordinatore si aspetta la (1)).
3. Elenca anche gli altri cambiamenti del lock che possono mordere (FastAPI 0.141→0.159, Starlette 1.6→1.9, Pydantic 2.13→2.14, python-dateutil 3.0, Pillow 13, pymdown-extensions 12): cosa dicono i loro changelog e dove li usiamo.
4. Conflitti: i file che toccherai e chi altro li tocca nell'ondata (tabella «File condivisi» di `PIANO-ondata4.md`: B il backup, W `financial_math`, J i lotti, H la piattaforma). Se la strada scelta tocca file di altri, il coordinatore decide l'ordine (probabilmente dopo il treno 9).

## Passo 2 — dopo il via
Prima i rossi già esistenti (sono i 57); poi la cura; `all-backend` verde, `api sync` senza diff, `front check`, `mkdocs build`, poi la corsa completa nello slot. Il lock nuovo e la cura vanno nello **stesso** commit (o in commit consecutivi dello stesso treno): `dev` non deve mai avere il lock nuovo senza la cura.

## Non fare
- Non toccare il venv condiviso, non lanciare `pipenv install/update/sync` (il venv `LibreFolio-D` è già pronto; se serve rigenerarlo, chiedi al coordinatore).
- Nessun cambiamento di comportamento: stessi numeri, stessi dati.

## Fatto quando
Analisi consegnata e strada scelta dal developer; poi rossi → verdi con il lock nuovo, gate completo verde nel tuo venv, doc per sviluppatori (`developer/backend/…` sulla convenzione UTC) aggiornata, **CHECKPOINT READY** e **FROZEN**.
