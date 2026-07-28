# Punti Aperti & Report — Broker Import Recovery (crystallization)

> **Scopo**: cristallizzare il lavoro svolto finora su questo task prima di avanzare.
> Contiene (1) tutte le richieste ricevute, (2) cosa è stato fatto e verificato,
> (3) lo stato dei test, (4) i **punti aperti** con tutte le info per riprendere, (5) lo
> stato git (cosa è mio vs altri agenti).
>
> **Data snapshot**: 2026-07-28 · **HEAD**: `e2b9f08d`
> **Piano collegato**: [`plan-phase00BrokerImportRecovery.prompt.md`](./plan-phase00BrokerImportRecovery.prompt.md)

---

## 1. Stato sintetico

Le due cause radice dei bug del portfolio engine sono **già identificate e documentate nel
piano** (RC-A quantità ×1000, RC-B mis-map asset). Su questo tronco si è poi innestata una
lunga serie di **feedback UX/dati** raccolti durante l'import in prod (utente `marco`) e la
**migrazione del web search a `ddgs`**. In questo giro sono stati chiusi e **verificati** due
fix urgenti (log flood + crash al salva) e la **migrazione automatica delle migration allo
startup** (che era la vera causa del crash in prod). Restano aperti i punti UX dell'import
wizard, la resa a badge di `identifier_other`, la doc, e i due grandi item BRIM rimandati
(Intesa patrimonio, CA successione).

---

## 2. Tutte le richieste ricevute (con stato)

### 2.1 — Task originale (i 2 plugin BRIM)
| # | Richiesta | Stato |
|---|-----------|-------|
| O1 | Plugin BRIM **Intesa** (Marco) — legge CSV **e** Excel | ✅ creato |
| O2 | Plugin BRIM **Credit Agricole** (Nonna Anna) — CSV **e** Excel | ✅ creato |
| O3 | Intesa: se manca lo storico acquisti, sfruttare il **patrimonio** all'apertura conto → generare **DEPOSIT + ADJUSTMENT** per lo stato iniziale asset | ⏳ **APERTO (P2)** |
| O4 | Movimenti **precedenti alla data apertura broker** → flaggati **non importabili** (nuovo enum di stato nell'incrocio) + poter **editare la data** del broker | 🟡 parziale (enum + edit presenti; manca UX step-4, vedi P3/P4) |
| O5 | CA: successione nonno→nonna (venduto+riacquistato) → usare **BUY** ma tracciare l'**origine** in descrizione | ⏳ **APERTO (P5)** |
| O6 | CA export = **solo titoli** (no liquidità) → il plugin deve emettere **DEPOSIT equivalente** accanto alla BUY | ⏳ **APERTO (P5)** |

### 2.2 — Feedback post-import (portfolio engine + wizard)
| # | Richiesta | Stato |
|---|-----------|-------|
| B1 | Studiare il **portfolio engine rotto** (BTP PIU 25-2-33 → `-917.687,72 € / -99.99%`) | ✅ **root-caused nel piano** (RC-A + RC-B) — vedi §6.9 |
| B2 | Capire il **warning nonna** "36 succession transfer row(s) … imported as ADJUSTMENT" (rischio over-count) | ⏳ **APERTO** (legato a P5) — vedi §6.8 |
| B3 | Wizard crea-asset: mettere in descrizione **tutti i nomi identificati**, non solo quello del provider | 🟢 **confermato funzionante (P8)** — verifica no-regressione |
| B4 | Nome import **troncato** a "STRATEGIA" (`EURIZON NEXT 2.0 - STRATEGIA OBBLIGAZIONARIA P`) | 🟢 **confermato risolto (P10a)** |
| B5 | Fondo BI `2FADB603927`: solo prezzo corrente, no storico; il "cerca" on-site non lo trova | 🟢 **creduto risolto (P10b)** — monitorare |

### 2.3 — Migrazione search `ddgs` + triage log/crash
| # | Richiesta | Stato |
|---|-----------|-------|
| S1 | Migrare il web link-finder da scraper **DuckDuckGo** → **`ddgs`** (metasearch) | ✅ fatto (commit `a10155ba`) |
| S2 | **Log mostruoso** durante la ricerca | ✅ **RISOLTO + verificato** (§4) |
| S3 | Crash al salva `row.value.trim is not a function` | 🟡 **guard messo (non crasha)** ma **causa radice da fixare** — vedi P1 |
| S4 | `identifier_other` non si vede a frontend + UI a **badge/tag** | ⏳ **APERTO (P7)** |
| S5 | Documentare le **env var** del link-finder | ✅ fatto (`configuration.en.md`) |
| S6 | Migration DB **auto allo startup** (dev + docker) | ✅ **RISOLTO + verificato** (§4) |

### 2.4 — Feedback punto-per-punto (ultimo giro)
| # | Punto | Stato |
|---|-------|-------|
| P1 | Fix corretto crash `.trim` (non solo guard) | ⏳ **APERTO — priorità alta** |
| P2 | Intesa patrimonio → depositi+adjustment apertura + flag pre-apertura | ⏳ APERTO (rimandato) |
| P3 | Step-4: **card broker** in cima (icona, giallo/rosso, data-minima, auto-fix o edit) + **bug gate** | ⏳ APERTO |
| P4 | Step-4: **icona broker** prima del nome | ⏳ APERTO |
| P5 | CA successione: BUY + DEPOSIT equivalente + origine in descrizione | ⏳ APERTO (rimandato) |
| P6 | (ok, nessuna azione) | ✅ |
| P7 | `identifier_other` come **badge** (TagInput) | ⏳ APERTO |
| P8 | Descrizione = tutti i nomi | 🟢 confermato |
| P9 | Riga risultato **mobile**: scroll orizzontale + link-button in alto | ⏳ APERTO |
| P10a | Troncamento nome | 🟢 risolto |
| P10b | Fondo BI storico/cerca | 🟢 creduto risolto |
| P-docs | Doc env-var → **tabelle o h5** ancorabili (configuration + altri capitoli admin) | ⏳ APERTO |

---

## 3. Fatto e verificato in questo giro

1. **Fix crash prod + causa radice** — le migration ora si applicano **automaticamente allo
   startup** (`backend/app/main.py` → `ensure_database_exists()` confronta `alembic_version`
   del DB con l'head e fa `alembic upgrade head` se indietro). Copre **sia `dev.py server`
   sia Docker** (unico entry-point via lifespan). Prima migrava solo un DB
   mancante/vuoto/corrotto → un DB esistente ma a revisione vecchia crashava. Risponde alla
   domanda "in Docker sarà resiliente?": **sì**.
   - `Dockerfile`: commento obsoleto aggiornato (niente più sqlite3 manuale).
2. **Log flood — RISOLTO** (`backend/app/logging_config.py`). Vedi §4 per la diagnosi.
3. **Crash `.trim` — guard difensivo** in `AssetModal.svelte` (`columnsToIdentifierRows`
   306-309 + `identifierRowsToColumns` 324-334): coercizione `String()`. **Non crasha più**,
   ma è un cerotto → la causa radice è P1.
4. **Env var link-finder documentate** — `mkdocs_src/docs/admin/configuration.en.md`
   (sezione "🔎 Asset Search — Web Link-Finder").
5. **Skill migrata** — `asset-search` → **`asset-plugin`**
   (`.github/skills/asset-tools/asset-plugin/SKILL.md`), gemella di `brim-plugin`, per
   scrivere asset source provider. La vecchia `asset-search` rimossa (era untracked). Il
   contenuto search-stack resta nella dev guide `search_link_finder.md`.

---

## 4. Diagnosi cristallizzate (per non riderivarle)

### 4.1 — Log mostruoso (RISOLTO)
- **Causa**: `ddgs` usa `primp` (client HTTP **Rust**) che inoltra i log dei suoi crate in
  **Python logging** via `pyo3-log`. Con server in `--debug` (root=DEBUG) vengono stampati:
  `hickory_resolver`/`hickory_net` (DNS), `rustls` (TLS), `h2`/`hpack` (HTTP2), `reqwest`,
  `hyper_util`, `cookie_store`, `primp` → centinaia di righe per ricerca.
- **NON** è `RUST_LOG` (provato unset/debug/error → 0 righe in subprocess isolato) e **NON**
  è `ddgs` che torna risultati errati.
- **Fix**: silence-list a WARNING in `configure_logging()` per quei logger + `urllib3` +
  `asyncio`. **Verificato**: con root=DEBUG il rumore passa da **60 → 0** righe.
- **Lentezza one-off**: quasi certo un **reload del backend** da altro agente (la 2ª ricerca
  è stata rapida). `backend="auto"` di ddgs ruota ~10 motori → molte lookup DNS.

### 4.2 — "Chiamata cattiva" / variabilità ddgs (onesto)
- La varianza per-chiamata di `backend="auto"` è reale (a volte torna schede giuste, a volte
  pagine lista MOT generiche) ma **non è possibile identificare quale motore** produce cosa —
  `ddgs` astrae la provenienza per-risultato.
- **Leva futura opzionale** (reversibile, solo env): fissare
  `LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND="google,bing,duckduckgo"` per qualità più stabile,
  oppure post-rank delle URL `/scheda/` prima di `/lista.html`. **Non fatto** (non urgente).

### 4.3 — Migration auto-startup
- Entry-point unico: `ensure_database_exists()` in `main.py` (chiamata nel lifespan) → vale
  per dev **e** docker (CMD uvicorn → lifespan). `DATABASE_URL` è **derivato** da
  `LIBREFOLIO_DATA_DIR` (non è un override env). Head revision = `002_identifier_other_json_list`.

---

## 5. Stato dei test

| Suite | Comando | Esito |
|-------|---------|-------|
| Backend completo | `pipenv run pytest` (mirato ai file toccati) | **561 passed** |
| Link-finder unit | `test_web_link_finder.py` | 24 passed |
| Regressione BI | `test_borsa_italiana_search.py` + `_funds.py` | ok (41 tot.) |
| Migration integrazione | DB@001 → `ensure_database_exists()` → 002 (idempotente) | pass |
| Log silence probe | root=DEBUG + silence-list → conta rumore | **60 → 0** |
| Frontend types | `./dev.py front check` (svelte-check) | **0 errors / 0 warnings** |
| Lint backend | ruff + black su `logging_config.py`, `main.py` | clean |

**Da rifare dopo P1–P9**: `./dev.py front check`, eventuale `pytest` mirato, e — se cambia
API/params — `./dev.py api sync`.

---

## 6. PUNTI APERTI (dettaglio per ripresa)

### P1 — Fix causa-radice crash `.trim` (priorità ALTA)
- **Sintomo**: al salva asset, `row.value.trim is not a function`.
- **Causa radice** (trovata): in `AssetModal.svelte` → `fetchAndCompareMetadata` il loop
  **righe 752-761** itera **tutti** gli `IDENTIFIER_TYPES` **incluso `OTHER`** e passa
  `pd.identifier_other` (ora una **lista**) dentro `compareStringField` (725) →
  `setFieldValue` (839) → `setIdentifierByType` (685-691), che sono pensate per **stringhe**:
  l'intero array finisce in un solo `row.value` → `.trim()` esplode al salva.
- **Guard attuale** (cerotto): coercizione `String()` in `columnsToIdentifierRows` (306) e
  `identifierRowsToColumns` (324). Ferma il crash ma `String(['a','b'])` → `"a,b"` (dato
  sbagliato).
- **Fix corretto**: **escludere `OTHER`** dal loop 752-761 e gestire `identifier_other` come
  lista → **fondere ogni elemento come riga `OTHER` separata** (additivo, dedup contro le
  righe OTHER esistenti, `autoFilled: true`). **Risolve anche P7** (i soft-id da metadata
  diventano visibili come righe).
- **File**: `frontend/src/lib/components/assets/AssetModal.svelte`.

### P7 — `identifier_other` come badge (TagInput)
- **Componente esistente**: `frontend/src/lib/components/ui/input/TagInput.svelte` (chip, ×,
  badge colorati, autocomplete). Usato in `TransactionFormModal.svelte` (tags) e
  `PromoteMergeModal.svelte`.
- **Modifica separatori richiesta** (riga **119** di `TagInput.svelte`, oggi
  `Enter || ',' || ' '`): passare a **Enter / `,` / `;` / Tab**, **togliere lo spazio**
  (gli identificatori contengono spazi, es. `BTP 1/12/2026 1.25%`). Attenzione: `Tab` come
  separatore **solo se il buffer non è vuoto**, altrimenti preservare la navigazione focus.
- **Verifica preliminare richiesta dall'utente**: confermare come i tag sono salvati a DB
  (l'utente dice "stringhe separate da `;`") così togliere lo spazio non rompe l'uso tag
  esistente. (Modello transaction / API tags.)
- **Poi**: usare TagInput per `identifier_other` in `AssetModal` (badge invece di righe input)
  e agganciare il merge da metadata (vedi P1).

### P3 — Step-4 import: card broker in cima + bug gate
- **UI**: in cima allo step 4, una **card-bottone per broker** con data apertura troppo avanti:
  icona broker, colore **giallo/rosso**, messaggio chiaro con la **data minima** richiesta, e
  bottone **auto-fix** (imposta data) **oppure** apri **edit** broker. (Per ora niente edit per
  singola riga; in futuro un bottone per ogni errore.)
- **BUG confermato dall'utente**: sbloccando la data del broker si **selezionano/sbloccano
  anche le righe il cui asset non è ancora risolto** → serve **gate su asset risolto**.
- **File**: `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte`
  (step 4; `_createNames`/`_createDesc` ~2731). Serve anche un **refresh/recheck** dopo edit
  broker (l'utente ha dovuto duplicare+modificare e ri-importare senza che si aggiornasse).
- **Nota correlata**: il check apertura conto deve essere **`<=`** non solo `<` (altrimenti le
  aggiunte del giorno di apertura non si importano).

### P4 — Step-4: icona broker prima del nome
- Aggiungere `BrokerIcon.svelte` prima del nome broker nella colonna step-4 (oggi manca).
- Aggiungere anche la **colonna** che mostra **in quale broker** la transazione verrà salvata
  (richiesta originale del giro precedente).

### P9 — Riga risultato ricerca su mobile
- **File**: `frontend/src/lib/components/assets/AssetSearchAutocomplete.svelte`.
- Su mobile la riga meta (rank `DDG#1` · ISIN · valuta · tipo · provider) diventa troppo lunga
  → **scroll orizzontale** come già fatto per il nome asset nelle tabelle.
- **Link-button** (apri pagina provider): su mobile spostarlo **in alto**, non al centro
  (finisce sopra il testo). L'utente ha fornito l'HTML del bottone risultato di riferimento.

### P-docs — Env-var → tabelle o h5
- In `mkdocs_src/docs/admin/configuration.en.md` **e negli altri capitoli admin**: convertire
  gli elenchi puntati caotici in **tabelle** oppure **paragrafi h5** (compaiono nell'indice,
  ancorabili). Solo EN per ora (traduzioni dopo, tutte insieme).

### P8 / P10a / P10b — verifiche (probabile no-op)
- **P8**: la descrizione già include il blocco "Nomi/identificatori individuati" (esempi BTP e
  fondo confermati dall'utente). Verificare che includa **tutti** i candidati, no-regressione.
- **P10a**: troncamento nome — confermato risolto. Verifica no-regressione.
- **P10b**: fondo BI storico/cerca — creduto risolto ("mi trova sempre roba, nessun
  controesempio"). Solo monitorare.

### P2 — Intesa patrimonio → seed apertura (RIMANDATO, per dopo)
- Se passato il **patrimonio**, il plugin deve emettere **DEPOSIT + ADJUSTMENT** per lo stato
  iniziale di tutti gli asset alla data apertura conto; i movimenti **precedenti** all'apertura
  vanno flaggati **non importabili** (nuovo enum già introdotto lato incrocio).
- **Regola BRIM**: `cost_basis_override` è **PER-UNITÀ** (dividere il controvalore totale per la
  quantità, impostare `cost_basis_currency`).

### P5 — CA successione: BUY + DEPOSIT + origine (RIMANDATO, per dopo)
- Export CA = **solo titoli** → per ogni **BUY** emettere anche un **DEPOSIT equivalente**
  (la banca è anche conto, non solo broker).
- Successione nonno→nonna (venduto+riacquistato): usare **BUY** ma scrivere l'**origine**
  (successione) nella descrizione estratta.
- **Legato a B2**: il warning "36 succession transfer row(s) (GIRO ALTRO DOSSIER /
  VERS.TITOLI) imported as ADJUSTMENT" segnala che **entrambe le gambe** del trasferimento
  potrebbero essere nell'export → **rischio over-count**. Capire se le 36 righe vanno
  de-duplicate / se una gamba va scartata.

### §6.8 — Warning nonna (B2) — nota
Vedi P5: da chiarire se le righe di trasferimento successorio vanno importate come ADJUSTMENT
(entrambe le gambe) o de-duplicate. **Aperto**.

### §6.9 — Portfolio engine (B1) — GIÀ ROOT-CAUSED nel piano
Non riaprire l'indagine: il piano documenta
- **RC-A**: quantità **×1000** — la riga tx fu **editata a mano dopo l'import** con un
  `<input type="number">` in browser **locale IT**, dove `.` è separatore migliaia →
  `91.861` → `91861`. È la **quantità**, non il WAC (WAC `9990.96` corretto).
- **RC-B**: **mis-map asset** — gli ADJUSTMENT seed del patrimonio nominavano fondi
  EURIZON / BTP specifici ma furono mappati sull'asset sbagliato.
- Scope piano = `code_only` (nessuno script di riparazione prod; l'utente corregge/re-importa).

---

## 7. Stato Git — cosa è MIO vs altri agenti

> ⚠️ Il working tree contiene **molte** modifiche di **altri agenti** (soprattutto il
> workstream **ai-export / signalMigration**). **NON** co-committare quelle con i file di
> questo task.

### 7.1 — File di QUESTO task (miei, da committare insieme quando si chiude il giro)
- `backend/app/main.py` — migration auto-startup
- `backend/app/logging_config.py` — silence-list Rust/urllib3/asyncio
- `Dockerfile` — commento aggiornato
- `mkdocs_src/docs/admin/configuration.en.md` — env var link-finder
- `frontend/src/lib/components/assets/AssetModal.svelte` — guard `.trim` (→ sarà sostituito dal
  fix P1)
- `.github/skills/asset-tools/asset-plugin/SKILL.md` — **nuova** skill (e rimozione
  `asset-tools/asset-search/`)

### 7.2 — NON miei (altro agente — ai-export/signals) — lasciare stare
`backend/app/schemas/ai_export.py`, `schemas/portfolio.py`, tutta
`backend/app/services/ai_export/**`, `lots_analysis_service.py`, i relativi test
`test_ai_export_*`, i file frontend `src/lib/features/ai-export/**`, e le modifiche in
`LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/**`.

### 7.3 — Regole git (permanenti)
- **Mai** `git commit`/`git push`/history-mutating: solo **proporre** il messaggio; l'utente
  committa. `git add` e comandi read-only ok.
- Commit già fatti rilevanti: `a10155ba` (identifier_other + link-finder + BRIM step-4),
  `407391f1`, `e2b9f08d`.

---

## 8. Ordine consigliato di ripresa
1. **P1** fix causa-radice `.trim` (rimuove il guard, risolve anche P7 lato dati) → `front check`.
2. **P7** TagInput separatori (verifica storage tag) + badge `identifier_other`.
3. **P3** card broker step-4 + **bug gate** asset-non-risolto + recheck + check `<=`.
4. **P4** icona broker + colonna broker step-4.
5. **P9** riga risultato mobile (scroll + link-button top).
6. **P-docs** env-var → tabelle/h5 (configuration + altri capitoli).
7. **P8/P10a/P10b** verifiche no-regressione.
8. **Poi**: **P2** (Intesa patrimonio) e **P5** (CA successione + B2 over-count).
9. Test finali + **grande commit** (lo fa l'utente) dei soli file §7.1.
