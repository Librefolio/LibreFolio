# 04 — AI Export — audit MkDocs EN vs codice

> **Release 2 · Phase 0 · 05_cleanAudit · mkdocsAudit**
>
> Ambito: le sole cinque pagine utente AI Export pubblicate. La guida developer
> AI Export (`mkdocs_src/docs/developer/architecture/patterns/ai_export_*.md`) è
> esplicitamente esclusa da questo report su richiesta dell'utente — nessun
> reperto developer è incluso, anche dove i pattern developer sarebbero stati
> letti per contesto (regola `.github/instructions/ai-development.instructions.md`).
>
> Modalità: sola verifica a livello di sorgente. Nessuna correzione di
> documentazione, codice o traduzioni fa parte di questo audit; nessun server
> live, probe reale o mutazione di database è stata eseguita.

## Baseline e riferimenti letti

| Campo | Valore |
|---|---|
| Baseline acquisita | [00_BASELINE](00_BASELINE.md) — `2026-08-05T10:54:55+02:00` |
| Commit HEAD alla baseline | `09cbb7e28f4e4e4bba9f9d40748b98e1876f5103` (branch `dev_release2`) |
| Worktree | Dirty; percorsi modificati non toccano `mkdocs_src/docs/user/ai-export/**` né
`backend/app/services/ai_export/**` né `frontend/src/lib/features/ai-export/**` — le cinque pagine e il codice AI Export risultano quindi stabili rispetto alla baseline per la finestra di questo audit. |
| Istruzioni lette prima dell'analisi | `.github/instructions/ai-development.instructions.md`; `.github/skills/ai-export-probe-tuning/SKILL.md` |
| Nota sul metodo | Probe reali non esistono per questo audit: tutte le verifiche sono a livello di sorgente/test statico, come richiesto. Le affermazioni che richiederebbero un probe reale per una conferma bit-per-bit sono segnalate come `non verificabile`. |

## Copertura (5/5 pagine)

| # | Pagina | File | Esito |
|---|---|---|---|
| 1 | Overview | `mkdocs_src/docs/user/ai-export/index.en.md` | Reperti R-01 (conteggio Analyses), R-02a (bullet "Signals header"), R-03 (Local References) |
| 2 | Portfolio | `mkdocs_src/docs/user/ai-export/portfolio.en.md` | Nessun reperto; claim campionate verificate (vedi §Verifiche) |
| 3 | Broker | `mkdocs_src/docs/user/ai-export/broker.en.md` | Nessun reperto; claim campionate verificate (vedi §Verifiche) |
| 4 | Asset | `mkdocs_src/docs/user/ai-export/asset.en.md` | Reperto R-02b ("Signals header") |
| 5 | FX | `mkdocs_src/docs/user/ai-export/fx.en.md` | Reperto R-02c ("Signals header") |

Tutte e cinque le pagine sono state lette per intero e confrontate con il codice
corrente (backend `ai_export` service, schemi API, frontend `features/ai-export`,
i18n `en.json`, route Svelte, test funzionali). Nessuna pagina è priva di
copertura.

---

## Reperti

### R-01 — Conteggio "thirteen task-oriented Analyses" errato in Overview

| Campo | Valore |
|---|---|
| Pagina/heading | `index.en.md`, sezione `## 📋 What It Does` |
| Riga doc | `mkdocs_src/docs/user/ai-export/index.en.md:22` |
| Claim testuale | *"The public catalog intentionally exposes only **eight autonomous Export Data choices** and **thirteen task-oriented Analyses**."* |
| Controprova sorgente | `backend/app/services/ai_export/analyses/catalog.py:3` (docstring: *"The component runtime exposes eleven task-oriented analyses"*), `:26-27` (`EXPECTED_ANALYSIS_COUNT = 11`, `EXPECTED_PUBLIC_ANALYSIS_COUNT = 11`), `:241` (`assert len(PUBLIC_ANALYSES) == EXPECTED_ANALYSIS_COUNT`) |
| Controprova test | `backend/test_scripts/test_services/test_ai_export_dataset_analysis_catalogs.py:206-212` (`assert EXPECTED_ANALYSIS_COUNT == 11`, `assert len(PUBLIC_ANALYSES) == 11`) e `:257-258` (`assert len(catalog.analyses) == 11`); `frontend/src/lib/features/ai-export/__tests__/publicCatalogContract.test.ts:25` (`expect(AI_EXPORT_PUBLIC_CATALOG_CONFIG).toHaveLength(19)` = 8 dataset + 11 analyses) |
| Controprova nella pagina stessa | La stessa pagina, sezione `## 🗂️ Available Analyses` (righe 68-100), elenca **11** righe totali: Portfolio 4 (righe 74-77) + Broker 3 (righe 83-85) + Asset 2 (righe 91-92) + FX 2 (righe 98-99) = 11, non 13. |
| Divergenza utente | Un lettore della sola sezione introduttiva riceve un numero totale di Analisi disponibili sbagliato (13 anziché 11); il numero è esplicitamente presentato come un vincolo di progetto intenzionale ("intentionally exposes only"), non come stima. |
| Classificazione | Contraddizione |
| Gravità | Minor — le tabelle sottostanti nella stessa pagina elencano correttamente le 11 Analisi con nomi esatti; l'utente che segue le tabelle non compie un'azione sbagliata. L'impatto è limitato a un'aspettativa numerica errata nel paragrafo introduttivo. |
| Confidenza | Alta — doppia conferma indipendente (asserzione Python a runtime + test backend + test frontend + conteggio manuale delle tabelle della stessa pagina). |
| Nota storica (solo per tracciabilità, non usata come fonte di verità) | `git log` mostra che la stringa "thirteen" è stata introdotta nel commit `6e9256f7` ("Fix translation inconsistencies…"); anche a quel commit `analyses/catalog.py` dichiarava già `EXPECTED_PUBLIC_ANALYSIS_COUNT = 11`. Non è quindi un valore diventato obsoleto dopo una modifica successiva del codice: non ha mai corrisposto al codice in questo file. |
| Direzione di correzione (non eseguita) | Sostituire "thirteen" con "eleven" in `index.en.md:22`, oppure rendere il numero non hard-coded nel testo se il catalogo può ancora crescere a breve termine. |

### R-02 — "In the Signals header, select AI Export" non corrisponde al punto di innesto reale per Asset e FX

| Campo | Valore |
|---|---|
| Pagine/heading interessate | (a) `index.en.md`, sezione `## 📋 What It Does`, riga 18: *"the Signals header on Asset and FX detail pages."*; (b) `asset.en.md`, sezione `## 📍 Location`, riga 8: *"Open an Asset detail page. In the **Signals** header, select **AI Export**."*; (c) `fx.en.md`, sezione `## 📍 Location`, riga 9: *"Open an FX detail page. In the **Signals** header, select **AI Export**."* |
| Controprova sorgente — Asset | `frontend/src/routes/(app)/assets/[id]/+page.svelte`: `<AiExportMenu …>` è montato alla riga **1782**, dentro lo snippet `actions` di `<PageToolbar …>` (apertura riga 1755, chiusura riga 1839) — lo stesso toolbar di pagina che ospita il selettore date, Edit, Sync e Refresh. Il pannello pieghevole "Signals" (`data-testid="asset-detail-signals-toggle"` riga 1852, `data-testid="asset-detail-signals-header"` riga 1853) inizia **dopo** la chiusura di `PageToolbar`, è collassato di default (`showSignals = $state(false)`, riga 172) e non contiene alcun controllo AI Export. |
| Controprova sorgente — FX | `frontend/src/routes/(app)/fx/[pair]/+page.svelte`: `<AiExportMenu …>` è montato alla riga **980**, dentro `<PageToolbar …>` (apertura riga 964, chiusura riga 1021). Il pannello "Signals" (`data-testid="fx-detail-signals-toggle"` riga 1028, `data-testid="fx-detail-signals-header"` riga 1029) inizia dopo la chiusura del toolbar, identico schema del caso Asset. |
| Controprova incrociata | Il commento in-linea del codice sorgente stesso, presente sia in `assets/[id]/+page.svelte:227` sia in `fx/[pair]/+page.svelte:200`, recita testualmente `// AI export (page toolbar) — dropdown open/position handled internally by AiExportMenu` — il codice si autodescrive come collocato nel "page toolbar", non nella sezione Signals. |
| Divergenza utente | Un utente che segue la sola sezione "Location" cerca il comando AI Export dentro il pannello pieghevole "Signals" (che deve espandere manualmente, essendo collassato di default) e non lo trova lì; il comando è invece sempre visibile in cima alla pagina, nel toolbar principale, indipendentemente dallo stato aperto/chiuso di "Signals". |
| Classificazione | Contraddizione |
| Gravità | **Major** — istruzione "How to use" primaria e verificabile in un solo clic; guida l'utente verso un percorso UI sbagliato per due domini su quattro (Asset, FX), mentre per Portfolio/Broker la posizione "top toolbar" dichiarata è invece corretta (vedi §Verifiche). |
| Confidenza | Alta — riscontro diretto nel markup delle due route interessate, con numeri di riga espliciti e commento in-codice concorde. |
| Direzione di correzione (non eseguita) | Allineare le tre posizioni testuali (`index.en.md:18`, `asset.en.md:8`, `fx.en.md:9`) alla collocazione reale, ad es. "in the page toolbar" (coerente con la formulazione già usata per Portfolio/Broker), oppure — se si preferisce mantenere l'associazione semantica con "Signals" — spostare il componente `AiExportMenu` dentro il pannello Signals lato codice. Nessuna delle due correzioni è stata applicata in questo audit. |

### R-03 — "The Entity Directory resolves those references" non copre i riferimenti locali `L#` (FIFO lots)

| Campo | Valore |
|---|---|
| Pagina/heading | `index.en.md`, sezione `## 🔗 Local References`, righe 117-127 |
| Claim testuale | *"The prompt uses local references to join compact tables: A# for Assets; B# for Brokers; F# for FX pairs; L# for FIFO lots. The Entity Directory resolves those references."* |
| Controprova sorgente — schema | `backend/app/schemas/ai_export_runtime.py:356-368` — `class AiExportEntityDirectory` espone solo tre collezioni: `assets`, `brokers`, `fx_pairs`. Non esiste alcun campo `lots`/`lot_directory`. |
| Controprova sorgente — renderer | `frontend/src/lib/features/ai-export/templates/snapshotDataRenderer.ts:142` — l'interfaccia `EntityDirectory` lato renderer replica lo stesso schema (asset/broker/fx-pair only); nessuna entry di tipo lotto. |
| Controprova sorgente — generazione L# | `backend/app/services/ai_export/components/asset_core.py:547` (`lot_ref=f"L{index}"`), `broker_financial.py:487`, `portfolio_financial.py:561,631` — i riferimenti `L#` sono generati localmente per riga di lotto, con tutti i dettagli (broker, date, quantità, costi) incorporati direttamente nella riga stessa (`AssetLotDetailRow`), non tramite lookup in `AiExportEntityDirectory`. |
| Divergenza utente | La frase riunisce i quattro tipi di riferimento (A#/B#/F#/L#) sotto un'unica frase di risoluzione ("The Entity Directory resolves those references"), ma il meccanismo strutturale per `L#` è diverso: non esiste una "directory dei lotti" da consultare, perché il dettaglio è già incorporato riga per riga. Il risultato finale nel testo copiato resta comprensibile (l'utente vede comunque i dettagli del lotto accanto a `L#`), quindi l'impatto pratico sull'output copiato è basso. |
| Classificazione | Omissione (generalizzazione imprecisa del meccanismo di risoluzione) |
| Gravità | Minor — non induce un'azione errata; il dato resta comunque leggibile nel prompt copiato. |
| Confidenza | Alta sul fatto strutturale (schema e renderer letti direttamente); media sull'effettivo impatto percepito dall'utente finale, che dipende dalla resa finale del prompt reale — la resa byte-per-byte non è stata eseguita in questo audit (vedi `non verificabile` più sotto). |
| Direzione di correzione (non eseguita) | Precisare che A#/B#/F# sono risolti tramite l'Entity Directory condivisa, mentre i riferimenti L# riportano il dettaglio del lotto incorporato nella stessa riga della tabella FIFO. |

---

## Verifiche positive (claim confermate puntualmente, nessun reperto)

Elenco selettivo delle affermazioni più specifiche e verificabili, confermate
esatte contro il codice corrente — incluse per tracciabilità e per evitare
future riverifiche dello stesso terreno:

| Claim (pagina) | Fonte codice che conferma |
|---|---|
| "eight autonomous Export Data choices" (`index.en.md:21`) | `backend/app/services/ai_export/datasets/catalog.py:44` (`EXPECTED_PUBLIC_DATASET_COUNT = 8`), `:867` (`assert len(PUBLIC_DATASETS) == EXPECTED_PUBLIC_DATASET_COUNT`); nomi esatti confermati in `frontend/src/lib/i18n/en.json:2494+` (`aiExport.dataset.*.display`) |
| Nomi degli 8 Export Data e delle 11 Analyses nelle tabelle di tutte le pagine | `frontend/src/lib/i18n/en.json:2403-2493` (`aiExport.analysis.*.display`) e `:2494+` (`aiExport.dataset.*.display`) — corrispondenza 1:1 con ogni riga di tabella nelle 5 pagine |
| Sampling Compact/Standard/Full: 8/16/30 punti percorso singola entità; 6/12/24 punti storia compatta per Asset eleggibile (`portfolio.en.md`, `broker.en.md`) | `backend/app/services/ai_export/components/technical_context.py:57-64` (`_SINGLE_ENTITY_HISTORY_BUCKET_COUNTS` = 8/16/30, `_UNIVERSE_HISTORY_BUCKET_COUNTS` = 6/12/24) |
| Sampling indicatori: fino a 5/10/illimitate righe non vuote (tutte e 4 le pagine) | `backend/app/services/ai_export/temporal/policy.py:78-82` (`_INDICATOR_HISTORY_ROW_LIMITS` = `{COMPACT: 5, STANDARD: 10, FULL: None}`) |
| Bucket massimi Compact 30gg / Standard 14gg / Full 7gg (`broker.en.md`) | `backend/app/services/ai_export/temporal/policy.py:39-43` (`_MAX_BUCKET_DAYS_BY_DETAIL_LEVEL`) |
| Periodi 3M/6M/1Y/Custom (tutte le pagine) | `frontend/src/lib/features/ai-export/aiExportOptions.ts:8` (`AI_EXPORT_PERIOD_PRESETS = ['3m','6m','1y','custom']`) |
| Draft in memoria 10 minuti, non in `localStorage` (tutte le pagine) | `frontend/src/lib/features/ai-export/aiExportMemory.ts:11` (`AI_EXPORT_MEMORY_TTL_MS = 10*60*1000`), `:91-92` (backing store = `sessionStorage`, non `localStorage`); chiave per dominio/entità (`portfolio`, `broker:{id}`, `asset:{id}`, `fx:{pair}`) conferma "per page context" |
| Risposta sempre nella lingua interfaccia corrente, non selezionabile dall'utente | `frontend/src/lib/features/ai-export/AiExportMenu.svelte:58` (`responseLanguage = $derived(aiExportResponseLanguageFromLocale($currentLanguage))`) |
| Fail-closed su mismatch di catalogo/contratto (tutte le pagine, sezione Applicability/Errors) | `frontend/src/lib/features/ai-export/catalog/compatibility.ts:60-77` (logica `compatibleSelection`); `backend/app/api/v1/ai_export.py:130-146` (409 `version_mismatch`) |
| Errori tipizzati 403/404/409/422/503 senza dettagli interni (Broker/Asset/FX) | `backend/app/api/v1/ai_export.py:96-183` (mappa completa eccezione→HTTP status→problema tipizzato) |
| Applicabilità reale lato server per "Position Review" e "FX Exposure Impact" (`index.en.md`, `asset.en.md`, `fx.en.md`) | `backend/app/services/ai_export/runtime_service.py:540-559` (`requires_direct_exposure`, `requires_position` → `AiExportSelectionNotApplicableError`, HTTP 422) |
| Costi allocati ai lotti FIFO distinti dai costi non allocati broker/portfolio (`broker.en.md`, `portfolio.en.md`) | `backend/app/services/ai_export/components/broker_financial.py:558` e `portfolio_financial.py:643` (campo `cost_allocation_semantics`, testo quasi verbatim rispetto alla pagina); `broker_cost_efficiency.py:322` (`unallocated_costs: Currency | None`) |
| "Economic FIFO is not legal tax treatment" — raccolta di residenza fiscale, regime, tipo conto, "cassetto fiscale" (`portfolio.en.md`, `broker.en.md`) | `frontend/src/lib/features/ai-export/templates/sharedInstructions.ts:57` (menzione letterale di *"cassetto fiscale"*) |
| Scenario Thesis obbligatorio per PAC, Rebalancing, Capital-Loss Offset (`index.en.md`) | `sharedInstructions.ts:73` (PAC: *"mandatory Scenario Thesis for every scenario"*), `:80` (Rebalancing: *"mandatory Scenario Thesis for each material pathway"*), `:63` (Fiscal Lots: *"mandatory Scenario Thesis for every material path"*) |
| "recorded-zero period semantics" (`asset.en.md`) | `backend/app/services/ai_export/components/asset_core.py:486` (campo `zero_semantics`, stessa terminologia) |
| Reason code espliciti per Asset correnti esclusi dall'eleggibilità tecnica (`broker.en.md`) | `backend/app/services/ai_export/components/technical_shared.py:495,543-556` (`excluded_current_assets` con reason `no_period_contribution`, `fully_sold_by_period_end`, `end_value_unavailable`, `zero_end_value`, `technical_eligibility_unavailable`) |
| 30-day / 91-day returns e range position (`fx.en.md`) | `backend/app/services/ai_export/components/fx_timing_context.py:130-148,440-441` (`return_30d_ratio`, `return_91d_ratio`, `range_position_ratio`) |
| Posizione "top toolbar, beside Update/Sync" per Portfolio, "top toolbar" per Broker | `frontend/src/routes/(app)/dashboard/+page.svelte:636` (`<AiExportMenu>` immediatamente prima del bottone `data-testid="sync-button"`) e `frontend/src/routes/(app)/brokers/[id]/+page.svelte:520` (`<AiExportMenu>` dentro `<PageToolbar>`) — entrambe corrette, a differenza di R-02 per Asset/FX |
| Nav MkDocs completa per le 5 pagine, link relativi coerenti con la convenzione i18n del sito | `mkdocs_src/mkdocs.yml:710-715` (voci nav complete); convenzione di link senza suffisso lingua (`portfolio.md`) già usata identicamente altrove nel sito, es. `mkdocs_src/docs/user/assets/index.en.md:37,41,45` — non è un reperto di navigazione |

---

## Punti non verificabili da questo audit (richiedono runtime/probe)

- **Byte esatti del prompt finale copiato** per una selezione reale (Export
  Data o Analysis) su Portfolio/Broker/Asset/FX con dati reali: la
  composizione a livello di componenti, il campionamento e i contratti sono
  confermati a livello di sorgente e test, ma l'equivalenza byte-per-byte
  UI/probe e il rendering qualitativo effettivo richiedono un probe reale
  (smoke/targeted) secondo `ai-export-probe-tuning`, non eseguito qui per
  vincolo del task. `non verificabile`.
- **Se la frase "AI period... or Custom when offered" implichi mai una reale
  esclusione dell'opzione Custom** in qualche combinazione dominio/Analysis:
  nel sorgente letto (`AiExportOptionsPanel.svelte:251-277`) il controllo
  Custom risulta sempre presente e non condizionato da `compatibility`/
  `domain`, ma un'assenza di gating osservata staticamente non esclude un
  percorso non ancora individuato; non è stata elevata a reperto per bassa
  materialità e per non aver eseguito una copertura esaustiva di ogni
  combinazione. `non verificabile con certezza assoluta, indicazione debole`.
- **Comportamento effettivo di reset al login/logout** per il draft AI Export
  (`registerClientSessionReset` in `clientSession.ts:89`): la registrazione
  del resetter è confermata, ma l'innesco runtime esatto su un nuovo login
  (vs. solo logout) non è stato osservato con un browser reale. `non
  verificabile senza sessione reale`.
- **Traduzioni IT/FR/ES** delle stesse 5 pagine: esplicitamente fuori
  perimetro per questo audit (vedi `00_INDEX.md`), non esaminate.

---

## Sintesi

| Metrica | Valore |
|---|---:|
| Pagine in scope | 5/5 (copertura completa) |
| Reperti totali | 3 |
| — Contraddizione | 2 (R-01, R-02) |
| — Omissione | 1 (R-03) |
| Gravità critical | 0 |
| Gravità major | 1 (R-02 — posizione reale di AI Export su Asset/FX diversa da "Signals header") |
| Gravità minor | 2 (R-01 — conteggio Analyses; R-03 — Entity Directory non copre L#) |
| Gravità info | 0 |
| Pagine senza reperti propri | Portfolio (`portfolio.en.md`), Broker (`broker.en.md`) — solo claim verificate positivamente |
| Punti "non verificabile" | 3 (equivalenza byte del prompt reale; gating di Custom period; innesco esatto reset su login) |

Nessuna correzione di documentazione, codice o traduzioni è stata applicata:
questo report è limitato alla verifica, come da perimetro del task.
