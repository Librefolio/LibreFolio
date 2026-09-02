# Feedback utenti F1–F17 (07.08–01.09.2026) — classificazione e consolidamento

> Seconda ondata di feedback (Giuseppe, utente esterno; Alfy, dogfooding su server Linux
> di produzione dal 31/08). Classificati il 01/09/2026, lavorati in un'unica tornata con
> commit singolo. Metodologia: **test-first verification** (i bug potevano essere stati
> risolti incidentalmente dalla campagna di testing → prima test che caratterizzano, poi
> fix solo di ciò che riproduce) + potenziamento dei test per categoria e aree limitrofe.

---

## 1. Classificazione e decisioni

| ID | Data | Segnalazione | Esito |
|----|------|--------------|-------|
| F1 | 01.09 | AI export sparito in dashboard | Non più riproducibile (né desktop né mobile). Guardia E2E mobile-viewport aggiunta (`dashboard.spec.ts`, 375×800) |
| F17 | 01.09 | Font date mobile troppo grande | ✅ Fix: il guard iOS anti-zoom (`input{font-size:16px!important}` sotto 768px) forzava i campi compatti. Aggiunto `.zoom-guard-exempt` sui 3 input del DateRangePicker |
| F2 | 31.08 | Dashboard: solo broker owned, con % possesso; 0% valido | ✅ Fix: scaling role-aware (OWNER scala per quota, 0% valido; EDITOR/VIEWER sempre 1) + dashboard owned-only (filtro, scope esplicito, zero-owned → vuota) |
| F3 | 31.08 | Modale warning spuria dopo assegnazione riuscita | ✅ Fix: race reattiva — `await tick()` prima di `onCancel` (test con harness che prova il binding) |
| F4 | 31.08 | Editor/viewer non possono auto-gestirsi; ultimo owner | ✅ Fix: `PATCH/DELETE /brokers/{id}/access/me`; cascata ultimo owner confermata dall'utente e implementata (broker+report+transazioni) |
| F5 | 25.08 | KPI card 3: % = ROI assoluto, non di periodo | ✅ Fix: card 3 ora usa `total_gain_loss_percent` (assoluto); il ROI di periodo resta in card 2 |
| F6 | 19.08 | Prompt analisi: mancano valori mercato a apertura lotto | ✅ Fix: `opening_reference_unit_price/_source` + `opening_market_value` in `asset.lot_detail` (componente v2, placeholder allineato) |
| F7 | 27.08 | Due voci AI export quasi omonime in asset detail | ✅ Naming: `position_and_history` → "Position & Market History (full)", `market_history` → "Market History Only (no holdings)" ×4 lingue. Servono entrambe (la seconda ~3× più leggera) |
| F8 | 30.08 | Grafico dashboard: vista solo P&L, candele, istogrammi | 📋 Rimandata → `TODO_FUTURI.md` (feature nuova, "prima ripariamo ciò che c'è") |
| F9 | 13.08 | Evidenziare riga dopo analisi lotto | ✅ Fix: `tr.row-analyzed` in DataTable + prop `analyzedAssetId` a catena (Exposure/ContributionTable, entrambe le pagine) |
| F10 | 31.08 | Tooltip tabelle coprono le righe | ✅ Fix: header tooltip DataTable `position="top"` (auto-flip se non c'è spazio) |
| F11 | 07.08 | Wizard: suggerire issue GitHub nella classificazione | ✅ Fix: banner warning in FixFlaggedStep con link a issues/new (aggancia P2 ImportWizardUx) |
| F12 | 14.08 | Click versione → changelog | ✅ Fix: ChangelogModal — CHANGELOG.md bundled via `?raw`, capitoli per release, link remoto. Voce preesistente in TODO_FUTURI spostata a Completati |
| F13 | 14.08 | Docker light senza immagini docs | ✅ Fix: `DOCS_VARIANT=light` build-arg, `dev.py docker build --light`, tag `*-light`, release.yml, guida ×4 + README. Full 2.88 GB → light 2.27 GB (−610 MB, −21%) |
| F14 | 14.08 | Modale "nuova versione" per admin | ✅ Fix scope 1: fetch client → GitHub Releases `/latest` (mai prerelease), throttle 24h, skip-versione, link guida. Self-update in-app → `TODO_FUTURI.md` |
| F15 | 31.08 | Asset global: pannelli tuoi/altri/sotto analisi + n. transazioni | ✅ Fix: `tx_count`/`tx_count_own` su lista asset; 3 pannelli in grid, colonna Tx con badge scope in tabella, badge sulla card |
| F16 | 07.08 | ESMA FIRDS / OpenFIGI / JustETF enrichment | 📋 Rimandata → `TODO_FUTURI.md` (link a `plan-phase00AssetIdentityAndIdentifiers`) |

### Decisioni dell'utente (01/09/2026)

- Risk analysis resta **congelata** (sistema beta) — prima consolida il resto.
- F4: cascata ultimo owner **confermata**.
- F12: modale a capitoli da changelog in build + link remoto.
- F14: opzione A (fetch client → GitHub Releases); scope 1 (modale+guida, Watchtower documentato).
- Modo di lavorare: tutto assieme, **commit unico** alla fine.

## 2. Bug trovato in corsa

La prima versione naive del fix F2 (`share_percentage or 1` → `is not None`) azzerava i dati
di EDITOR/VIEWER (share sempre 0 per regola di schema) → 2 test risk API rotti, intercettati
dalla suite esistente. Corretto con scaling role-aware. Esempio da manuale del valore della
metodologia test-first + suite condivisa.

Bug nel fix F12 (regex capitoli escludeva `## [Unreleased]` senza data): scoperto dal
test-author con test `it.fails` documentato, corretto, test promosso a guardia.

## 3. Test aggiunti (test-author batch)

- Backend: `test_broker_access_api.py` (+8: self-service/cascata), `test_portfolio_service.py`
  (+6: scaling role-aware), `test_ai_export_components_asset.py` (+3: campi F6 + v2),
  `test_assets_crud.py` (Test 17: contatori own/total).
- Frontend unit: brokerStore, BrokerSharingPanel (race), KpiSection, ExposureTable,
  ContributionTable, DataTable header tooltip, FixFlaggedStep, changelog, updateCheck,
  ChangelogModal, UpdateAvailableModal, AssetTable, DateRangePicker.
- E2E: guardia F1 mobile in `dashboard.spec.ts`.
- Harness: stub `matchMedia` in `src/__tests__/component.ts`.

### Verde finale

- `all-backend` (fresh run, seriale): **TUTTI PASSED** 🎉
- E2E seriali: front-user 17+5 ✅ · front-asset 89+205 ✅ · front-transaction ✅ (exit 0) ·
  front-portfolio 28+34 ✅ (dopo il repair di `broker-icons.spec.ts` ai nuovi semantics F2)
- `front-utility` core 1752 + component 1226 · ruff/black/svelte-check puliti · i18n audit
  2515/2515 completi · build frontend ✅

> **⚠️ Fuori pista (01/09)**: a metà validazione ho lanciato `all-backend` e le categorie E2E
> **in parallelo** → contesa sul DB di test condiviso (popolazione fallita con
> `no such table: users`) → decine di rossi spurii ovunque. Lezione: il runner usa UN database
> e UN backend condivisi — mai due invocazioni di suite insieme. Tutti i rossi sono spariti
> alla riesecuzione seriale, senza alcuna modifica al codice.
> Unica eccezione reale: `broker-icons.spec.ts`, attese aggiornate ai semantics F2 (Recrowd
> è EDITOR-only per l'utente test → fuori dalla dashboard owned-only; ora il test patcha
> l'icona su Interactive Brokers, owned 30%).

## 5. Round 2 — collaudo live del 01/09 pomeriggio (server prod 6040)

Esito collaudo utente: F3/F4/F5/F7/F9/F10/F11/F17 confermati OK; F6/F14 accettati a fiducia
(F6 poi verificato live: `asset.lot_detail` v2 con `opening_market_value` corretto, es.
7.675 × 36 = 276.30). Nuovi rilievi e fix:

| Rilievo | Causa | Fix |
|---|---|---|
| Card broker a zero + edit % senza effetto per 24h | **blob cache engine (24h) e L2 report (30min) senza role/share nella chiave** | fingerprint (broker_id, role, share) in entrambe le chiavi → invalidazione naturale |
| F12: modale changelog intrappolata nella sidebar | `<nav>` con `transform`+`overflow-hidden` intrappola il `position:fixed` | ChangelogModal resa fuori da `<nav>` + maxWidth 4xl |
| F15: nome "Sotto analisi" | gusto | rinominato **Osservati/Watched/Surveillés/Observados** |
| F15: tabella unica | richiesta: 3 tabelle impilate | 3 AssetTable (testid `assets-table-panel-*`), larghezze sincronizzate live (`onColumnResize`→`setColumnWidth`), ordine/visibilità via `additionalTableRefs` del toggle, paginazione indipendente (storageKey per pannello) |
| F15: "tuoi asset comprende tutto" | **non confermato**: verificato live (marci EDITOR su directa → quegli asset correttamente in "altri utenti"); probabile build intermedia o percezione | nessuna |
| F13: 2GB di codice+librerie | (a) `chown -R /app` duplicava ogni file in un layer; (b) gcc/git/libffi-dev (toolchain build-time, ~200MB) nella final image; (c) **`.dockerignore` non escludeva `backend/data/` → i DB locali finivano nell'immagine (anche rischio leak)**; (d) `backend/test_scripts/` inclusi | COPY --chown ovunque, pybuilder stage, dockerignore allargato. **Light: 2.27→1.50 GB**. Bug entrypoint collaterale: UID/GID host (501/20) collidevano con gruppi base → entrypoint numerico |
| F1/F17 mobile | transitori di connessione (download CSS parziale), come ipotizzato dall'utente | nessuna ulteriore |

Verifica live usata come prova: login alfy/marci su :6040, report con share 0.3 → valori
scalati corretti (NAV 11.983,54 = 30%), card OK sul build corrente.

> Test round 2 (test-author): `TestAccessFingerprintCacheBust` (share/role edit → cache miss
> → numeri nuovi, con prova "a denti": rimossa la fingerprint torna rosso), breakdown by_broker
> scalato 30% via API, spec `asset-list` riparate per le 3 tabelle + 3 nuovi test (bucketing,
> selezione cross-panel, pannelli grid). Verde seriale: roi-fifo-utils ✅, api portfolio ✅,
> front-asset 8/8 unità ✅ (asset-list 20/20). Nota igienica: `role` può arrivare come `str`
> da costruttori SQLModel in-session → fingerprint usa `getattr(role,'value',role)`.

## 6. Round 3 — rifiniture post-commit (01/09 sera)

- **F12 rework modale**: niente più header sticky (il "buco" nel titolo era il capitolo sticky
  dentro l'area scrollabile con padding). Ora: pannello foldabile per versione (solo la più
  recente aperta), sotto-sezioni `###` foldabili con click, indice a chip con salto+scroll,
  modale fuori dalla nav (round 2) e larga 4xl. Verificato live su :6040.
- **CHANGELOG 1.1.0**: data → **2026-09-07** (lunedì successivo, mai andata live); capitolo
  arricchito da git log (07.08→01.09): import flow/asset identity, test infrastructure,
  consolidamento feedback seconda ondata; intro aggiornata.
- **F4**: il warning rosso di cascata ora suggerisce l'alternativa (assegnare un altro owner
  prima di uscire); fix ordine chiusura: `goto('/brokers')` PRIMA di `onChanged` — sul broker
  detail il reload del broker appena cancellato poteva lanciare e saltare la navigazione,
  lasciando la pagina aperta su dati vecchi.
- **F13 Q&A**: la pulizia non cambia significativamente il tempo di build (stessi download/
  compilazioni pip, cache mount invariato); i benefici sono dimensione, push/pull e igiene
  (niente DB locali nell'immagine pubblicata).

## 7. Round 4 — modale changelog interattiva (01/09 sera)

- **Indice chip**: il click ora apre E scorre (await tick → scrollIntoView).
- **Fold a 3 livelli**: `##` versione → `###` sezione → `####` sotto-sezione (es. 🧠 Signals,
  🤖 AI Export), ciascuno apribile a click.
- **Ricerca**: il campo cerca scende nei fold — i rami che contengono la query si aprono da
  soli e i titoli corrispondenti si evidenziano. Pulsanti **espandi/comprimi tutto**.
- **CHANGELOG.md**: cappello di presentazione del progetto su v1.0.0; emoji di sezione
  convenzionate (✨ Added, 🔄 Changed, 🐛 Fixed, 🧪 Beta, ⚠️ Breaking) su entrambi i capitoli.
- **Regole di scrittura**: nuova sezione "Changelog Rules" in `.github/copilot-instructions.md`
  (struttura, emoji, fold semantico, aggiornamento a release).
- **F4**: il monito alternativo ("assegna prima un altro owner…") ora è un paragrafo a parte
  in corsivo (ConfirmModal `description` + nuovo prop opt-in `descriptionItalic`).
- **Debug**: `window.librefolioDebug.showUpdateModal()` per forzare la modale F14 nelle build
  debug (in prod: seed della cache `librefolio-update-check` via console).
- **Bug in corsa (round 4)**: la ricerca del changelog non era case-insensitive (ago mai
  minuscolato) — scoperto dal test-author con `it.fails`, corretto (`needle` normalizzato),
  test promosso a guardia.

## 8. Round 5 — update check nella modale + ricerca navigabile (01/09 tardo pomeriggio)

- **F4**: la sharing modale ora si chiude da sola dopo il leave (`onCancel` alla fine della
  catena, dopo `goto` e `onChanged`).
- **Pulsante "Verifica aggiornamenti"** nell'header della changelog modal: usa la STESSA
  `checkForNewerRelease()` del flusso login (nessuna duplicazione). Admin con novità → apre
  la modale F14; non-admin con novità → banner ambra con i badge degli amministratori
  (nuovo param opt-in `admins=true` su `GET /users/search`, che espone `is_admin` solo in
  quel caso); aggiornato → riga verde "ultima versione".
- **Ricerca con risultati cliccabili**: sotto il campo compaiono fino a 8 chip con i titoli
  delle sezioni/sotto-sezioni che matchano; click → apre il ramo completo (versione →
  sezione → sotto-sezione) e scrolla al toggle bersaglio. Gli hit matchano anche il **corpo**
  delle sezioni, non solo i titoli (seguìto al collaudo: "funziona solo sui titoli?").
- **Debug**: in build debug il check scrive in console cosa ritorna la fetch, la versione
  rilevata e l'età della cache (`[UpdateCheck] probe → {current, latest, …}`); lo show della
  modale è loggato anch'esso.
- **Contratto `/users/search`**: `is_admin` è assente (non `null`) senza `admins=true`
  (`response_model_exclude_unset`) — drift schema/wire trovato e chiuso in round 5.
- **Evidenziazione nel testo** (seguìto al collaudo): le occorrenze della query nei corpi
  renderizzati vengono wrappate in `<mark>` giallo (light e dark), tag HTML preservati.
  Convenzione release documentata per l'utente: conta il **tag** `vX.Y.Z` (non draft, non
  prerelease) letto da `releases/latest`; il nome libero della release è solo display.

## 9. Round 6 — MWRR pole + stale frontend + polish modale (02/09)

- **MWRR pole (screenshot 01/09)**: selezionando un periodo con start in un giorno senza
  dati (domenica 01/03) e un deposito sul primo giorno con NAV reale, il MWRR cumulativo
  andava a +9.94% mentre TWRR era −1.53%. Causa: nel re-basing del periodo, il ramo
  `period_start_nav == 0` teneva i flussi con `cf.date >= primo snapshot`, ma il primo
  snapshot è già post-flusso → deposito contato due volte → il solver XIRR trovava una
  radice estrema e `annualized_to_cumulative` la mostrava come polo. Fix in
  `portfolio_service.py` (entrambi i rami: summary + history series): flussi sul primo
  snapshot esclusi (`>`) anche nel ramo data-less. Riprodotto e fissato con probe;
  325 test finanziari verdi. Wiki: `wiki/problems/mwrr-pole-dataless-period-start.md`.
- **Stale frontend**: la versione restava sulla build vecchia fino a F5 manuale. Fix in
  `main.py`: `/_app` (chunk hashati) ora `Cache-Control: immutable, 1 anno`; le route SPA
  (`200.html`/`index.html`) ora `no-cache, must-revalidate`. Il service worker era già
  offline-only (nessun caching app), il problema era HTTP cache sull'HTML.
- **Modale changelog**: "Sei aggiornato" ora è un **toast**, non una riga nella modale
  (banner ask-admin solo per i non-admin quando c'è davvero una novità). Pulsante
  "Verifica aggiornamenti": la label si piega su mobile (`hidden sm:inline`), resta l'icona.
- **Regole release tag**: documentate in `mkdocs_src/docs/developer/docs/release-pipeline.md`
  (nuova sezione "Release Tag Convention") e nel devWiki `concepts/ci-release-pipeline.md`.

## 4. Collegamenti

- Piani agganciati ancora aperti: **P2** ImportWizardUx (F11 vi si inserisce),
  **P5** TransactionsUxPolish (F9 vi si inserisce), P4, P6 — vedi [INDEX.md](INDEX.md).
- Rimandi: `TODO_FUTURI.md` (F8, F16, self-update).