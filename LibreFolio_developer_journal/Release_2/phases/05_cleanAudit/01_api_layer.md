# 01 — API Layer

> `backend/app/api/v1/` · 18 file · 5 976 righe
> Gravità massima: 🔴

---

## Sintesi

Il layer API è il più ordinato del backend. Le rotte sono sottili, la logica sta nei
servizi, la complessità ciclomatica è contenuta (il picco è 14, contro il 112 dei
servizi). Nessuna violazione della Async I/O Rule salvo una lettura file.

Il problema non è la forma, è **cosa manca**: un interruttore di sicurezza esposto
all'amministratore non viene mai verificato, e gli endpoint bulk interrogano il database
una riga alla volta.

---

## Metriche

| | |
|---|---|
| File | 18 |
| Righe | 5 976 |
| Endpoint | 97 |
| Endpoint senza `response_model` | 17 (18 %) |
| Rilievi ruff | 78 |
| Funzioni oltre soglia complessità | 5 (max 14) |
| Simboli non referenziati | 1 |
| Candidati N+1 | 7 |

File più grandi: `assets.py` (1 165), `fx.py` (1 022), `brokers.py` (914),
`uploads.py` (533).

Rilievi ruff dominanti: `TRY400` 27 (uso di `logger.error` dove servirebbe
`logger.exception`), `RUF100` 10 (`# noqa` ormai inutili), `RUF010` 10 (conversione
esplicita in f-string).

---

## Reperti

### 🔴 A1 — L'interruttore di registrazione non protegge nulla

**Dove**: `backend/app/api/v1/auth.py:189` (`register`)

L'impostazione globale `enable_registration` esiste a tutti i livelli:

- dichiarata in `backend/app/schemas/settings.py:89` con default `"true"`
- documentata in `backend/app/db/models.py:368`
- esposta nella UI in `frontend/src/lib/components/settings/tabs/GlobalSettingsTab.svelte:46`,
  dentro il gruppo `security` con l'icona a scudo
- dotata di un accessor dedicato `is_registration_enabled()` in
  `backend/app/services/global_settings_service.py:95`
- coperta da test

**Manca solo l'unica cosa che conta**: l'endpoint `/auth/register` non chiama mai
`is_registration_enabled()`. Il corpo della funzione conta gli utenti per decidere chi è
admin, crea l'utente e restituisce. L'interruttore è puramente decorativo.

Un amministratore che disattiva le registrazioni **non ottiene alcuna protezione**, e
non ha modo di accorgersene dall'interfaccia.

> **Tracciatura della logica**: `is_registration_enabled()` risulta usata solo dai test.
> La sua logica **non è riassorbita da nessuna parte** — non esiste nessun altro
> controllo sulla registrazione nel codebase. Non è codice morto da rimuovere: è una
> funzionalità mai cablata.

Il confronto interno lo conferma: `max_file_upload_mb` segue esattamente lo stesso
schema ed **è** applicato correttamente in `uploads.py:169`. Il pattern esiste, alla
registrazione non è stato applicato.

```python
# Rimedio, in testa a register()
if not await is_registration_enabled(session):
    raise HTTPException(status_code=403, detail="Registration is disabled")
```

Da valutare insieme: il primo utente deve poter registrarsi anche a registrazioni
chiuse? Altrimenti un'installazione nuova con il flag a `false` nel DB diventa
inaccessibile.

---

### 🔴 A2 — `require_email_verification` non ha nemmeno un accessor

**Dove**: `backend/app/schemas/settings.py` (chiave `require_email_verification`)

Stessa famiglia del reperto A1, un gradino più indietro: l'impostazione è dichiarata ed
esposta nella UI (stesso gruppo `security` di `enable_registration`), ma non esiste
alcuna funzione che la legga né alcun punto che la applichi. Il docstring di `register`
lo ammette a mezza bocca: *"In production, you may want to add email verification."*

> **Tracciatura**: nessuna logica di verifica email esiste nel codebase.

Due strade, entrambe legittime, ma va scelta una:

- implementare la verifica email, oppure
- rimuovere l'impostazione dalla UI e dai default finché non è supportata.

Lasciare all'utente un interruttore che non fa niente è la peggiore delle tre.

---

### 🟡 A3 — N+1 negli endpoint bulk

Gli endpoint *bulk* esistono proprio per evitare il round-trip per elemento, ma alcuni
lo reintroducono all'interno.

| Dove | Pattern |
|---|---|
| `portfolio_api.py:49` | `await session.get(Asset, query.asset_id)` dentro `for query in body.queries` |
| `fx.py:984` | `session.execute` dentro il loop iniziato a riga 979 |

Il caso di `portfolio_api.py` è il più netto: l'endpoint riceve una lista di query WAC e
per ciascuna esegue una `SELECT` separata per recuperare la valuta dell'asset.

```python
# Rimedio: una sola query, poi lookup in memoria
asset_ids = {q.asset_id for q in body.queries}
rows = await session.execute(select(Asset).where(Asset.id.in_(asset_ids)))
assets = {a.id: a for a in rows.scalars()}
```

Con 50 query in un batch si passa da 50 round-trip a 1.

---

### 🟡 A4 — 17 endpoint su 97 senza `response_model`

Senza `response_model` FastAPI non valida l'uscita e — soprattutto — **non genera lo
schema OpenAPI**. Poiché il client TypeScript nasce da `./dev.py api sync`, ogni
endpoint senza `response_model` è un buco di tipizzazione che il frontend riempie a mano.

Questo spiega parte del reperto A5: esistono schemi di risposta scritti e mai collegati.

---

### 🟡 A5 — Schemi di risposta scritti e mai collegati

Otto classi Pydantic non sono referenziate da nessuna parte — né dal backend, né dai
test, né (verificato) dal frontend:

| Classe | File |
|---|---|
| `AuthPasswordResetRequest` | `schemas/auth.py:34` |
| `AuthErrorResponse` | `schemas/auth.py:116` |
| `FXPairsListResponse` | `schemas/fx.py:503` |
| `PortfolioSummaryQuery` | `schemas/portfolio.py:81` |
| `PortfolioHistoryQuery` | `schemas/portfolio.py:91` |
| `AllocationHistoryQuery` | `schemas/portfolio.py:299` |
| `AllocationHistoryResponse` | `schemas/portfolio.py:310` |
| `FAEventDeleteResult` | `schemas/prices.py:401` |

> **Tracciatura**: la maggior parte descrive risposte di endpoint che **esistono** ma
> restituiscono `dict` grezzi (reperto A4). La logica non è "riassorbita altrove", è
> semplicemente **non applicata**.

`AuthPasswordResetRequest` è il caso a parte: descrive un reset password via API che non
esiste come endpoint. Il reset esiste **solo** da CLI (`scripts/user_cli.py:90`).

Il rimedio corretto non è cancellare gli schemi ma **collegarli** agli endpoint
corrispondenti — così si chiudono A4 e A5 insieme e il client TS guadagna i tipi.
Fanno eccezione `AuthPasswordResetRequest` (decidere se implementare il reset via API) e
`AuthErrorResponse` (FastAPI ha già il suo formato d'errore: probabilmente da rimuovere).

---

### 🟡 A6 — `get_optional_user` senza chiamanti

**Dove**: `backend/app/api/v1/auth.py:82`

Dependency per autenticazione facoltativa (endpoint che funzionano sia da loggati sia da
anonimi). Zero riferimenti in tutto il repository.

> **Tracciatura**: nessun endpoint attualmente ha bisogno di autenticazione opzionale —
> sono tutti o pubblici o protetti. La logica non è riassorbita, semplicemente non serve
> (ancora).

Rimozione a basso rischio: sono ~10 righe facilmente riscrivibili. Da conservare solo se
è previsto a breve un endpoint a visibilità mista.

---

### 🟢 A7 — `open()` sincrona dentro `async def`

**Dove**: `backend/app/api/v1/uploads.py:377`

Unica violazione della Async I/O Rule in tutto il backend (1 su ~74 000 righe: il
progetto la rispetta molto bene).

```python
with open(file_path, encoding="utf-8") as f:
    if offset: f.seek(offset)
    content = f.read(window) if window else f.read()
```

Si tratta di una finestra di anteprima testo, quindi pochi KB: l'impatto pratico è
minimo. Ma è lettura da filesystem dentro un handler `async` e va uniformata:

```python
content = await asyncio.to_thread(_read_window, file_path, offset, window)
```

---

### 🟢 A8 — 27 `logger.error` dentro blocchi `except`

`TRY400`: dentro un `except`, `logger.exception()` allega automaticamente il traceback,
`logger.error()` no. Ventisette occorrenze nel solo layer API significano ventisette
punti in cui, a fronte di un errore in produzione, si perde lo stack trace.

Sostituzione meccanica, nessun rischio, beneficio diretto sulla diagnosticabilità.

---

## Interventi raccomandati

| Priorità | Intervento | Costo | Rischio |
|---|---|---|---|
| 1 | Applicare `is_registration_enabled()` in `register()` — decidere il caso primo utente | basso | basso |
| 2 | Decidere su `require_email_verification`: implementare o rimuovere dalla UI | medio | basso |
| 3 | Eliminare l'N+1 in `portfolio_api.py:49` e `fx.py:984` | basso | basso |
| 4 | `logger.error` → `logger.exception` nei 27 blocchi `except` | basso | nullo |
| 5 | Collegare i 17 endpoint privi di `response_model` agli schemi già scritti, poi `./dev.py api sync` | medio | basso |
| 6 | `open()` → `asyncio.to_thread` in `uploads.py:377` | basso | basso |
| 7 | Rimuovere `get_optional_user` se non è previsto un endpoint a visibilità mista | basso | basso |

Gli interventi 1 e 2 chiudono un divario fra ciò che l'interfaccia promette
all'amministratore e ciò che il sistema fa davvero. Vanno prima di tutto il resto.
