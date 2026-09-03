# Piano: P2 — Decisioni di prodotto e backlog residuo (audit 08)

**Data**: 2026-09-03
**Contesto**: chiusura dei 9 task P2 di `99_task_riesumati.md` dopo le decisioni utente del 03/09,
più reinserimento dei task rimasti aperti dalla tornata P1.
**Stato**: 🔄 IN ESECUZIONE — prima ondata di lane già completata in giornata

---

## Decisioni utente del 03/09 (registrate)

| Task | Decisione |
|---|---|
| P2-1 verifica email | Feature futura in `TODO_FUTURI.md` (server SMTP: verifica + inviti + recupero pw); ORA: opzione resa placeholder (read-only + badge) |
| P2-2 WAC multi-broker | Indaga → verdetto: rimasuglio superato (16/07, refactor FIFO engine) → **rimozione proposta** |
| P2-3 AssetMetadataService | Indaga → verdetto: scheletro di automazione mai cablata; il diff oggi è calcolato 2 volte altrove (frontend modale + endpoint refresh) → **rimozione proposta** (refresh automatico = eventuale feature futura) |
| P2-4 cache clear | Idea interessante → indagine: solo backend, 16 cache in-memory con TTL; **proposto endpoint selettivo** (lista + clear per nome, blocklist delle cache di calcolo) |
| P2-5 scorciatoia cassa | NO, era un placeholder errato → rimasugli rimossi (eseguito: solo 2 chiavi i18n orfane restavano) |
| P2-6 suggest_events | L'utente ricorda l'idea: riga-notifica nella bulk modal (stile promote) con range = slider delta-days. Indagine: il matching backend è pronto e testato (8 test), manca solo il frontend → **proposta feature M**; in attesa di conferma ora-vs-dopo |
| P2-7 orfani frontend | Eliminare, ma salvare il meglio (guardie/logiche superiori) nelle funzioni vive, migrare/potenziare i test → eseguito |
| P2-8 property `*_cur` | Currency condivisa è la strada giusta → rimosse tutte le 11 (anche le 3 "eccezioni": verificate MAI usate dal frontend; erano property Python non serializzate, zero impatto OpenAPI) |
| P2-9 settings services | NON fondere (modello utente confermato: colonne per-utente vs chiavi globali condivise); al massimo UI → eseguire minimal: registro chiavi + docstring + refactor 3 campi inline GlobalSettingsTab |
| Rossi preesistenti | I 3 contract red ai-export vanno risolti anche se preesistenti → in corso (test-author) |

---

## ✅ Eseguito nella prima ondata (03/09, 4 lane parallele)

- **Lane F1** — P2-1: `SettingToggle` con props `disabled`+`badge` (pill ambra,
  `data-testid="setting-badge"`), `require_email_verification` disabilitata con badge
  "coming soon" ×4 lingue (`settings.comingSoon`), esclusa da reset-to-defaults;
  commento placeholder in `GLOBAL_SETTINGS_DEFAULTS`. P2-5: UI già rimossa a luglio
  (commit c14117bb); restavano solo `brokers.deposit`/`brokers.withdraw` orfane → rimosse ×4.
- **Lane F2** — P2-7: `txStoreGetPartner/Main` eliminati (guardie già equivalenti nel vivo);
  `availableLanguages`/`currentLanguageFlag/Name` **adottati** in `LanguageSelector`
  (+ aria-label, guadagno a11y) e `PreferencesTab`; `cleanUrlParams`/`hasActiveFilters`/
  3× imageCrop eliminati puri (28 test migrati/rimossi, 89 verdi); file orfani
  `BaseDropdown.svelte` + `TransactionTypeBadge.svelte` eliminati + riga design-system corretta.
- **Lane F3** — P2-8: tutte le 11 property eliminate come orfane verificate
  (0 referenze front+back per ciascuna; mai serializzate → nessun impatto OpenAPI/api sync);
  test chirurgici (408 verdi in test_schemas).
- **Docs** — TODO_FUTURI.md: nuova voce "📧 Server email" (verifica/inviti/reset pw).

## ✅ Eseguito nella seconda/terza ondata (03/09)

- **Lane H1** — P2-2: `compute_wac_iterative_multi_broker` rimossa (253 righe + 247 di test);
  P2-3: `AssetMetadataService` rimossa (152 righe + file test dedicato); `FAMetadataChangeDetail`
  orfano rimosso; registration runner e architettura docs aggiornate.
- **Lane H2** — P2-4: `GET /api/v1/settings/cache/status` (tutti gli autenticati),
  `POST …/cache/clear/{name}` e `…/cache/clear-all` (solo admin, 404 su nome ignoto, log
  structlog con chi/cosa); `CachePanel.svelte` in GlobalSettingsTab (pattern scheduler),
  ConfirmModal con avviso "rallentamenti paragonabili al riavvio"; 16 chiavi i18n ×4.
- **Lane H3** — P1-6: `fifo_utils.py` + 11 test eliminati dopo checklist della mappatura
  (gap test `test_buy_then_full_sell_at_loss_records_negative_pnl` aggiunto all'engine prima
  della cancellazione; 310 test della cartella verdi).
- **Lane H4** — P2-9: `SETTINGS_REGISTRY` (SettingSpec frozen dataclass, namespace
  `user`/`global_`, derivato da GLOBAL_SETTINGS_DEFAULTS — fonte unica); 17 call site migrati
  dai letterali; docstring doppia responsabilità; GlobalSettingsTab: 3 campi `default_*` →
  wrapper condivisi (+prop `embedded`); `default_theme` ora segmented control (unica variazione
  visiva intenzionale); fix mock PreferencesTab rotto da F2.
- **test-author** — 8 test API cache (CAPI-001..008): auth 401/403, clear by name (404
  ignoto), clear-all, ciclo funzionale populate→status→clear→status; unit registrata
  `exclusive_because` (clear-all tocca le cache condivise → mai in parallelo).
- **Lane H5** — residuali: 8 classi schema orfane pre-scritte rimosse + re-export
  `WACConversionInfo`; helper JSON-safe convergenti in `utils/json_utils.py`
  (`_json_safe_details` tenuto locale con razionale: politiche errore opposte); commento LRU
  corretto; RUF022 adottato (5 noqa giustificati sui barrel comment-grouped).
- **Rossi ai-export RISOLTI** (test-author): la deriva era legittima (F2 → `broker_ids`
  esplicito nel payload dashboard; contratto V1 lo prevedeva) — 3 test E2E aggiornati ad
  asserire il contratto canonico; suite `front-ai-export` di nuovo verde.
- **Ondata P3 docs** (4 lane + ripresa post-disconnessione): 24 item puntuali + 3 riscritture
  (sharing.en.md, brokers/import.en.md al wizard a 7 step, sezione Import di getting-started);
  marker errati rimossi; stamp Aphra solo sulle correzioni cosmetiche; debito traduzioni
  IT/FR/ES elencato per la prossima pipeline (P3-27).
- **Agente `docs-writer`** creato in `.github/agents/` (regole: solo EN, traduzioni solo su
  richiesta esplicita, ladder di verifica, stamp Aphra sulle puntuali).

## 🔄 In volo

- **test-author** — triage + fix dei 3 contract red ai-export (`broker_ids` nel payload).
- **Lane G** — annotazioni di stato nei 17 report di sottosistema + mkdocs.

---

## Prossima ondata (parallela; test in serie alla fine)

> Da eseguire dopo conferma utente dei punti "proposto".

```
WS-R1 rimozioni    P2-2  compute_wac_iterative_multi_broker + 5 test (rimozione sicura,
                         verdetto indagine: matematica identica vive in lots_analysis_service)
                   P2-3  AssetMetadataService + test_asset_metadata.py (SE confermato (a))
WS-R2 feature S    P2-4  GET /admin/cache/list + POST /admin/cache/clear/{name}
                         con blocklist [portfolio_blob, portfolio_layer2, risk_simulation,
                         risk_optimization]; schema CacheStats; test API
WS-R3 chiarezza    P2-9  SETTINGS_REGISTRY in schemas/settings.py + docstring doppia
                         responsabilità + GlobalSettingsTab: 3 campi default_* → wrapper
                         SettingSelect/SettingCurrency esistenti
WS-R4 chiusura     P1-6  rimozione fifo_utils.py + 11 test (mapping pronto nel piano P1)
                         — dopo review utente della mappatura
                   Reds  merge del fix test-author (già in volo)
TEST               run seriale completa via dev.py test all (workers=1)
```

## Da decidere (blocca WS-R1/R2 parziale)

1. ~~**P2-3**~~ → ✅ CONFERMATO rimozione (03/09): "ampliamente superata" — il frontend fa
   l'ask alla creazione, poi è nelle mani dell'utente.
2. ~~**P2-6**~~ → 📋 POSTICIPATO in `TODO_FUTURI.md` (voce "Suggerimento eventi collegabili
   nella bulk modal") con contesto completo. Nota emersa: `AssetEventPicker` usa
   `query_events_bulk` (NON `suggest_events`) → duplicazione di matching da fattorizzare
   quando si farà (registrata nella voce TODO).
3. ~~**P1-6**~~ → ✅ VIA LIBERA (03/09): "mi torna che sia completamente morta e quello che
   abbiamo ora è meglio" → Lane H3 esegue la rimozione con la checklist della mappatura.
6. ~~**P2-9**~~ → ✅ APPROVATO (03/09): (b) il registro centralizzato è "ottima intuizione"
   ma attenzione a **migrare tutto il codice** che oggi auto-dichiara le chiavi come
   letterali stringa → devono usare il registro; (c) approvato il refactor dei 3 campi
   inline verso i wrapper condivisi. Sequenziato DOPO Lane H2 (condivide
   `schemas/settings.py` e `GlobalSettingsTab.svelte`).

## Terza ondata (03/09)

- **Lane H3** — P1-6: rimozione `fifo_utils.py` + 11 test + registration runner
  (checklist della mappatura Lane B eseguita prima della cancellazione).
- **Lane H4** (dopo H2, stesso file set) — P2-9: `SETTINGS_REGISTRY` in
  `schemas/settings.py` + migrazione dei call site da letterali a registro +
  docstring doppia responsabilità + (c) 3 campi `default_*` di GlobalSettingsTab →
  wrapper `SettingSelect`/`SettingCurrency`/`SettingTheme`.
- **test-author** (dopo H2) — test API per i 3 endpoint cache.
- **Lane H5 — residuali onesti scoperti da Lane G** (dopo H1/H2/H3, tocca schemas e uploads):
  1. P1-1: le 8 classi schema pre-scritte (report 01 §A5 / 07 §G2) restano orfane dopo
     che Lane A ne ha create 13 nuove → adottare o rimuovere; re-export morto
     `WACConversionInfo` (`schemas/transactions.py:37`) da togliere.
  2. P1-17: convergenza dei 3 helper JSON-safe mai applicata → applicarla o decidere;
     commento `uploads.py:63` dice ancora «LRU» → correggere; RUF022 (`__all__` sorting):
     decidere regola o noqa mirati.
  3. P1-18: documentare nel piano il cross-check coverage JS × knip (manca il verbale).

## Ondata P3 — documentazione (03/09, in corso)

Nuovo agente creato: `.github/agents/docs-writer.agent.md` (ruolo: docs solo EN, traduzioni
solo su richiesta esplicita via pipeline Aphra, ladder di verifica mkdocs, e sulle modifiche
puntuali **stamp della cache Aphra**: `./dev.py mkdocs translate-stamp --file <pagina>` —
corretto il 03/09: niente marker HTML, il "timestamp" è l'MD5 stamp della pipeline).

- **Lane docs-admin** — P3-1 (URL custom_startup.sh 404), P3-2 (comando gallery), P3-3
  (backup WAL-unsafe in docker_advanced), P3-8 (fail-loud font/JS mai documentato),
  P3-18 (SNB: medie mensili, non daily).
- **Lane docs-sharing** — P3-9 (riscrittura sharing.en.md: aggregation shipped, self-leave,
  cascata last-owner, solo OWNER condivide) + P3-16 (Joint Account 2 owner), P3-10
  (alt-text modale eliminata + delete→bulk), P3-11, P3-22 (files), P3-23 (assets index),
  P3-24 (drag-and-drop/label).
- **Lane docs-metrics** — P3-4 (DocsLink WAC 404 — fix del link in codice), P3-5 (benchmark
  segnali), P3-7, P3-12, P3-13 (KPI cards), P3-14, P3-15 (generic CSV: TRANSFER/FX_CONVERSION
  via dai docs se non supportati), P3-17, P3-19, P3-20, P3-21 (signals Asset: 2 task reali).
- **Lane docs-wizard** — P3-25 (brokers/import.en.md → wizard 7 step attuale) + P3-26
  (sezione Import di getting-started).
- **Trattenuti**: P3-6 (settings docs) finché Lane H4 non atterra; P3-27 (batch traduzioni
  IT/FR/ES a due generazioni di debito) — SOLO su richiesta esplicita utente; P3-28
  (tooling check-links falso positivo) resta backlog.
- **Dopo H2/H4**: documentare il pannello cache admin (P2-4) e, se cambia la UI settings,
  riallineare la pagina settings.

### ⚠️ Interruzione di connessione (03/09 ~15:45) e ripresa

Le lane in volo sono state uccise da una disconnessione. Il lavoro nel tree è sopravvissuto.
Inventario post-ripresa:
- **Completate con report**: docs-admin (5 item + residuo SNB indice FX, stamp fatti),
  docs-sharing (7 item, riscrittura sharing.en.md inclusa).
- **Interrotte senza verbale**: H5 (residuali — LRU comment e WACConversionInfo risultano
  sistemati nel tree, convergenza helper/RUF022 da verificare), docs-metrics (item
  5/7/12/13/14/15 + parte del 17 atterrati; mancavano fx/detail, assets/detail, ai-export),
  docs-wizard (diff reali su import.en.md + getting-started.en.md, completezza non verificata).
- Rilanciate come lane H5-2 / docs-metrics-2 / docs-wizard-2 (ereditano il tree, non rifanno).
- Sweep centrale dei 12 marker `last-verified` errati fatto dal coordinatore (0 rimasti).
- ⚠️ Lezione: `git stash push -- <path>` non copre i `git rm` staged (fifo_utils) — verificare
  lo stash list prima di poppare.

## Ondata verifica + report 50 (03/09, in corso durante la run finale)

- **Verifica di coerenza** (3 lane read-only): 06_betaTestingReportAndFixing vs codice,
  08 P0/P1 vs codice, P3 docs vs pagine. Anomalie → appuntate, decisione a fine run.
- **Report 50** (`50_docs_gap_v101_gallery.md` in questa cartella): delta v1.0.1→HEAD vs
  documentazione (user+admin+developer) + audit di `gallery.spec.ts` (shot stantii/mancanti/
  riusabili/rischio rottura testid). Solo analisi: la scrittura docs avverrà in seguito.
- **Nota trovata dal coordinatore**: INDEX 06 dice «Fase D aperta» ma
  `dev.py test coverage-report --lang js` esiste ed è operativo → da riallineare.
- **TODO_FUTURI** arricchito: voci `mode='duplicate'` (decisione aperta), P8 tappe 1–6,
  batch traduzioni P3-27 con lista pagine e regola stamp-vs-debito.

### Esito verifica sistematica (03/09) — tutto regge, 4 anomalie appuntate

**Claim verificate**: 06 → 29/29 (P2 10/10, P4 2/2, P5 4/4, P6 3/3, F-wave 10/10);
08 P0/P1 → 22/22; P3 docs → 25 atterrati + 3 correttamente aperti. **Zero falsi claim.**

**Anomalie appuntate (da decidere a fine run)**:
1. **2 chiavi i18n morte sfuggite alla P1-8**: `importWizard.possibleDuplicate` /
   `likelyDuplicate` (singolari, ×4 lingue, 0 riferimenti — il wizard usa
   `compareModal.openHint`). Da rimuovere via `dev.py i18n remove`.
2. **Micro-refuso `importWizard.todoRow`** = "TX #{n}" ×4 (W5 lo segnalava ma non era
   tracciato). Una riga di i18n update.
3. **Headers stale nei piani 06** (P7 «Fase D aperta» — fatta e operativa; P8 «tappe 1–6
   aperte» — quasi tutto fatto il 13/08; INDEX §4 contraddice §5; "`_reachability.py`"
   → vive in `_cli.py`+`_inventory.py`). La voce TODO_FUTURI P8 è già stata corretta;
   restano da riallineare i file in 06 (o si archivia la cartella com'è, con nota).
4. **P3-7 brief invertito**: la riga JustETF sotto le sorgenti DIVIDEND era **corretta
   da aggiungere** (`justetf.py:419` emette DIVIDEND) — il report d'audit la voleva
   tolta; i docs attuali sono giusti, l'annotazione va corretta in mkdocs/01.

## Regola di chiusura

Nessuna run di test mentre le lane lavorano (DB condiviso). Alla fine: `api sync`
(nuovi endpoint P2-4) → run seriale completa → aggiornamento report/CHANGELOG →
proposta commit unico in `/tmp`.
4. **P2-4** → ✅ CONFERMATO come feature (03/09): pannello in Global Settings (pattern
   pannello scheduler), lettura stato per TUTTI gli utenti autenticati, clear selettivo E
   globale solo admin, modale di conferma che avverte: al prossimo richiamo dei dati
   rallentamenti paragonabili a un riavvio del server.
5. **26 TODO(P2-refactor)** → 📋 `TODO_FUTURI.md` (voce dedicata con tabella + istruzioni
   di recupero); NON ora.
6. **P2-9**: (a) docstring doppia responsabilità ok; (b)+(c) spiegati in chat il 03/09 —
   in attesa di conferma utente prima di eseguire.

## Seconda ondata (03/09, in corso)

- **Lane H1** — rimozioni P2-2 (`compute_wac_iterative_multi_broker` + 5 test) e
  P2-3 (`AssetMetadataService` + test_asset_metadata.py).
- **Lane H2** — feature P2-4: `GET cache-status` (utenti autenticati) +
  `POST cache/clear/{name}` + `POST cache/clear-all` (admin), pannello `CachePanel.svelte`
  in GlobalSettingsTab (pattern scheduler), modale conferma con avviso rallentamenti,
  i18n ×4. Test API a carico di test-author dopo il suo rientro.

## Backlog che resta dopo questa ondata

- 26 funzioni `TODO(P2-refactor)` (tabella nel piano P1) — candidati top: `execute_batch` (115),
  `portfolio_engine.build` (97), `get_summary` (73), `_parse_account_movements` (71).
- P3 (28 voci documentali) e P4 (8 strutturali) di `99_task_riesumati.md`.
- Chiavi i18n orfane residue segnalate da Lane F1 (`brokers.holdings/noHoldings/...`).

## Regole

- Sviluppo in lane parallele a file disgiunti; **test solo in serie** alla fine (un DB, un backend).
- i18n via `./dev.py i18n`; API touch → `api sync` centralizzato; mai `git commit` (proposta in /tmp).
