# Donation Popup — Note per il deploy e il test manuale

Questo file NON è wired in `./dev.py` (eccezione esplicita alla regola "usa sempre ./dev.py"):
i comandi qui sotto vanno eseguiti a mano.

## 1. DB di produzione esistente — aggiungere le 3 colonne

Il modello `User` (`backend/app/db/models.py`) e la migrazione `001_initial.py` hanno 3 colonne
nuove (`login_count`, `donation_popup_last_shown_at`, `donation_popup_logins_since_shown`).
`001_initial.py` viene applicato solo a DB **nuovi** (`./dev.py db create-clean`). Sul DB di prod
**esistente** (dati reali da preservare) va invece eseguito manualmente questo comando, una volta
sola, dopo il deploy del codice:

```bash
# Backup preventivo (consigliato)
cp backend/data/prod-docker/sqlite/app.db backend/data/prod-docker/sqlite/app.db.bak-$(date +%Y%m%d)

# Verifica preventiva (opzionale) — mostra le colonne attuali della tabella users
sqlite3 backend/data/prod-docker/sqlite/app.db "PRAGMA table_info(users)"

# Aggiunta delle 3 colonne (non distruttivo, non tocca righe/dati esistenti)
sqlite3 backend/data/prod-docker/sqlite/app.db <<'SQL'
ALTER TABLE users ADD COLUMN login_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN donation_popup_last_shown_at DATETIME DEFAULT NULL;
ALTER TABLE users ADD COLUMN donation_popup_logins_since_shown INTEGER NOT NULL DEFAULT 0;
SQL
```

Note:
- Da eseguire una sola volta. Se lo lanci due volte, `sqlite3` risponde con un errore
  "duplicate column name" solo per le colonne già presenti (nessun danno) — puoi anche
  rimuovere dallo script le righe delle colonne già aggiunte e rilanciare solo quelle mancanti.
- Se usi un path dati diverso da quello di default (`LIBREFOLIO_DATA_DIR`), sostituisci il path
  del DB di conseguenza.
- Dopo l'esecuzione, un login riuscito qualsiasi confermerà che le colonne funzionano
  (nessun errore 500 su `/api/v1/auth/login`).

## 2. Test manuale del popup da console Chrome

**Aggiornamento**: `dev.py` ora rileva automaticamente se il bundle servito non è nella modalità
richiesta (produzione vs debug) e lo ricompila da solo, anche se non ci sono file sorgente
modificati — non serve più alcun passaggio manuale. Basta:

```bash
./dev.py server --debug
```

`--debug` fa due cose: alza il log level del backend **e** ora forza anche il rebuild del
frontend in debug mode (`VITE_DEBUG=true`, no minify, sourcemap) se l'ultima build non lo era
già — confrontando un marker (`frontend/build/.build-debug`, non tracciato da git) con la
modalità richiesta, non solo la staleness dei file sorgente. Funziona anche al contrario: un
`./dev.py server` senza `--debug` dopo una build debug la ricompila in produzione.

Poi, dalla console developer del browser sull'app:

```js
window.librefolioDebug.showDonationPopup()
```

**Se invece usi il dev server Vite** (`./dev.py front dev`, porta `:5173`), il hook è già sempre
attivo — non serve alcun flag, `import.meta.env.DEV` è sempre `true` lì.

Forza il segnale lato frontend e apre subito la modale — non serve fare 50 login reali né
toccare il DB. Utile per iterare su copy/stile/traduzioni.

**Dopo il test**, un semplice `./dev.py server` (senza `--debug`) ricompila automaticamente in
modalità produzione (bundle minificato, senza sourcemap) — non serve più rincompilare a mano.

