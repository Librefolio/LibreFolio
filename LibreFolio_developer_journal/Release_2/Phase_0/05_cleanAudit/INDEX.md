# Audit — Indice generale

> **Release 2 · Phase 0 · 05_cleanAudit**
> Data: 2026-08-07 · Branch: `dev_release2`
> Ambito: backend + frontend, **AI Export incluso** ([report 13](13_ai_export.md),
> eseguito a lavoro dell'altro agente concluso)

---

## Cos'è questo audit

Analisi critica sistematica del codebase alla ricerca di **codice morto**,
**funzioni ottimizzabili**, **algoritmi migliorabili** e **violazioni delle regole di
progetto**. Non è un lint report: gli strumenti automatici hanno prodotto le evidenze,
ma ogni reperto è stato tracciato manualmente per rispondere alla domanda che conta:

> *La logica contenuta in questo codice è stata riassorbita da qualcos'altro, oppure no?*

Questa distinzione governa tutte le raccomandazioni:

| Esito della tracciatura | Raccomandazione |
|---|---|
| Logica **riassorbita** da un'implementazione più recente | Rimozione sicura, insieme ai test ormai privi di oggetto |
| Logica **non riassorbita** da nulla | ⚠️ **Non rimuovere.** È una funzionalità mai cablata o una regressione latente — va discussa |

---

## Sintesi esecutiva

Il codebase è complessivamente **sano**. La regola Async I/O è rispettata quasi
ovunque (1 sola violazione su ~74k righe), i test sono tutti registrati, non ci sono
accumuli di `TODO/FIXME`. Il debito si concentra in quattro punti precisi:

1. **Tre funzionalità dichiarate all'utente ma non cablate** — la più grave è un
   interruttore di sicurezza che non protegge nulla.
2. **Un residuo di refactoring in `portfolio_service.py`** — l'implementazione
   pre-engine è rimasta in casa insieme ai suoi test.
3. **`asset_source.py`**, 4 800 righe, concentra da solo il 68 % dei N+1 candidati e il
   9 % dei rilievi ruff.
4. **12 barrel `index.ts` morti nel frontend** che tengono artificialmente in vita
   quattro componenti reali — vanno rimossi *per primi*, perché finché esistono
   l'analisi del codice morto frontend non è attendibile.

A questi si aggiunge un reperto che non è debito tecnico ma **rischio legale**:
`pyproject.toml` dichiara licenza MIT su un progetto AGPL-3.0.

**La rete di sicurezza tiene.** La suite backend copre il **90,48 %** (171 file di test,
un solo fallimento riproducibile, dovuto a una guardia di test troppo larga e non a un
difetto di codice). Le funzioni realmente scoperte sono 42 per 155 statement — e in buona
parte **coincidono con i reperti di codice morto**, confermandoli con un metodo
indipendente. Vedi [12](12_test_coverage.md).

### Numeri

| Metrica | Valore |
|---|---|
| Backend analizzato | 99 file, 73 721 righe (netto ai_export, coperto dal [report 13](13_ai_export.md)) |
| Frontend analizzato | ~394 file, ~135 000 righe (netto ai-export, coperto dal [report 13](13_ai_export.md)) |
| Simboli backend non referenziati | **15** |
| Simboli backend usati solo dai test | **42** |
| File frontend non raggiungibili | **20** |
| Export frontend inutilizzati | **79** + 84 tipi |
| Dipendenze npm inutilizzate | **6** |
| Rilievi ruff (regole estese) | **702** — 145 auto-fixabili |
| Funzioni oltre soglia complessità | **138** (`C901`) |
| Candidati N+1 | **38** |
| Violazioni Async I/O Rule | **1** |
| Statement Svelte legacy `$:` | **101** |
| **Copertura test backend** | **90,48 %** — 42 funzioni azionabili, 155 statement |

---

## 🔴 I sei reperti che contano

Ordinati per rapporto rischio/costo di intervento.

| # | Reperto | Dove | Report |
|---|---|---|---|
| 1 | `pyproject.toml` dichiara **licenza MIT** su un progetto **AGPL-3.0** (+ versione `0.6.x`, Python `>=3.11`, stato `Alpha`) | `pyproject.toml:7-22` | [11](11_crosscutting.md) |
| 2 | `get_global_setting()` chiamata con **argomenti invertiti e un positional di troppo** → `TypeError` garantito sul ramo di fallback | `portfolio_engine.py:1960` | [02](02_services_core.md) |
| 3 | L'interruttore **"Allow new user registration"** è esposto nella UI ma **non viene mai verificato** da `/auth/register` | `api/v1/auth.py:189` | [01](01_api_layer.md) |
| 4 | La chiave `"base_currency"` **non esiste** fra i global settings → la valuta base configurata è silenziosamente ignorata, si usa sempre `"EUR"` | 3 call site | [02](02_services_core.md) |
| 5 | `asyncio.create_task()` **senza salvare il riferimento** → il task può essere garbage-collected a metà esecuzione | `main.py:251` | [11](11_crosscutting.md) |
| 6 | WAC multi-broker completo e testato, ma **cablato a nulla** | `portfolio_service.py:347` | [02](02_services_core.md) |

I reperti 2, 3, 4 e 5 sono **bug**, non debito tecnico. Il 6 è una funzionalità
sviluppata e mai esposta. Il **1 non è un problema tecnico ma legale**, ed è quello che
costa meno di tutti: quattro righe di metadati.

Il progetto ha appena completato il lavoro sulla conformità delle licenze di terze parti
(`THIRD_PARTY_LICENSES.md`, attribuzioni in quattro lingue). Dichiarare male la propria
licenza nei metadati del pacchetto vanifica quel lavoro.

---

## ⚡ L'ora che rende di più

Cinque interventi a costo quasi nullo e rischio nullo, che insieme risolvono l'unico
rischio legale, l'unico bug latente e l'unica violazione della Async I/O Rule:

| Intervento | Dove | Costo |
|---|---|---|
| Correggere licenza, versione, Python, maturità | `pyproject.toml` | 4 righe |
| Trattenere il task di pre-warm | `main.py:251` | 1 riga |
| `await asyncio.to_thread(...)` sull'`open()` bloccante | `uploads.py:377` | 1 riga |
| Log agli 11 `try/except/pass` silenziosi | vari | 11 righe |
| Restringere la guardia `'"fast"'` a `params_schema` (unico test rosso) | `test_signal_plugins_close_only.py:107` | 2 righe |
| ✅ **fatto** — `ruff --fix` sui 125 autofix sicuri | tutto il backend | 1 comando |
| ✅ **fatto** — fattorizzare `resolveDefaultDetailLevel` sui 5 siti + rimuovere `isDatasetCatalogEntry` | `ai-export/` frontend | 15 righe |

> **Nota sugli autofix ruff**: eseguiti in Fase F — 77 correzioni applicate
> (`PIE790` 54, `RUF010` 23) su 20 file, baseline `./dev.py lint` invariata a 36 errori.
> I 111 `RUF100` sono stati **deliberatamente lasciati**: documentano un'intenzione, non
> sono rumore. Vedi [11](11_crosscutting.md) K8.

> **Non è un quick win**: `if not __debug__: raise` in `main.py` (2 righe) era stato
> elencato qui come rimedio a un rischio di produzione. Dopo verifica il reperto è stato
> declassato a 🔵 — la suite di test verifica gli stessi invarianti a monte e pytest non usa
> mai `PYTHONOPTIMIZE`, quindi un catalogo incoerente non può essere rilasciato. Resta
> un'opzione di igiene, non urgente. Vedi [13](13_ai_export.md) § M2.

---

## ⚠️ Da discutere: logica **non** riassorbita

Regola dell'audit: *se la logica di un simbolo morto non è stata riassorbita da
qualcos'altro, non si rimuove — si discute.*

Questi sono i casi in cui la tracciatura ha stabilito che **non esiste un sostituto**.
Rimuoverli significherebbe perdere una capacità, non ripulire una ridondanza.

| Simbolo / componente | Dove | Perché non è riassorbito | Report |
|---|---|---|---|
| `merge_other_identifiers` | `utils/identifier_utils.py:51` | La semantica di import **additiva** non è applicata da nessuna parte: in produzione gli identificativi vengono **sostituiti**. Se il requisito è reale, è un difetto funzionale. ✅ **Confermato dalla copertura: 0 %** — mai eseguita, né in produzione né nei test | [07](07_schemas_utils.md) G3 · [12](12_test_coverage.md) L5 |
| `compute_wac_iterative_multi_broker` | `wac_service.py` | Calcola una posizione unificata cross-broker; `compute_wac_iterative` lavora su **un solo** broker. Funzionalità completa, testata, cablata a nulla | [02](02_services_core.md) |
| `AssetMetadataService` (3 metodi) | `asset_source.py:4230` | Il diff campo-per-campo per audit non esiste altrove: oggi la classificazione di un asset si aggiorna **senza storico** | [03](03_services_pricing_fx.md) C3 |
| `ensure_rates_multi_source` | `fx.py:399` | Implementa il routing esplicito per valuta base, che `sync_pairs_bulk` non fa. È l'impalcatura prevista per il primo provider multi-base | [03](03_services_pricing_fx.md) C2 |
| `LiveTicker.svelte` (233 righe) | `components/layout/` | La striscia prezzi in tempo reale **non esiste più** nell'interfaccia. Tre commenti nel codice la descrivono ancora come consumatore attivo | [09](09_frontend_components.md) I1 |
| `FxProviderConfig.svelte` (314 righe) | `components/fx/` | Da verificare: esiste ancora una vista d'insieme delle rotte FX con priorità, o è una regressione? | [09](09_frontend_components.md) I1 |
| `removeAssetPriceStore`, `invalidateCurrencyGraph`, `destroyPriceProcessingPool` | `lib/stores/`, `lib/workers/` | Funzioni di **ciclo di vita** mai chiamate: creazione e lettura funzionano, la rimozione no. Possibile crescita monotona della memoria | [08](08_frontend_state_api.md) H3 |
| `cache_utils` (3 funzioni) | `utils/cache_utils.py` | Non esiste alcun endpoint admin di gestione cache. Oggi l'unico modo per invalidare una cache è **riavviare il servizio** | [07](07_schemas_utils.md) G4 |
| `txStoreGet*` (4 accessori) | `stores/transactions/` | Toccano il modello main/partner delle transazioni collegate — logica di dominio, non infrastruttura | [08](08_frontend_state_api.md) H2 |

Per contrasto, questi sono i casi in cui la logica **è** stata tracciata fino al suo
sostituto e la rimozione è sicura:

| Simbolo | Assorbito da |
|---|---|
| `fifo_utils.calculate_fifo_lots` | `fifo_lot_engine.py` |
| `portfolio_service` ~156 righe di history (6 simboli) | `portfolio_engine.build_history()` |
| `settings_service.get_session_ttl` / `_sync` | `global_settings_service.get_session_ttl_hours` |
| `valuation_price` / `valuation_price_ccy` | rinominate, alias di compatibilità |
| `HoldingsPanel.svelte` | `PositionsPanel.svelte` (vista "Holdings / Table" + 3 viste in più) |
| `BrokerImportFiles.svelte` | `BrokerImportFilesModal.svelte` |
| `unique_computation_count` | è `len(self.computations)` — il campo è pubblico e vivo |
| `src/lib/tanstack-table/` | implementazione tabelle propria sotto `components/ui/` |

---

## Report per sottosistema

| # | Report | Ambito | Righe | Gravità max |
|---|---|---|---:|:---:|
| 01 | [API Layer](01_api_layer.md) | `backend/app/api/v1/` | 5 976 | 🔴 |
| 02 | [Servizi core](02_services_core.md) | portfolio, FIFO, lots, transactions | ~10 100 | 🔴 |
| 03 | [Pricing & FX](03_services_pricing_fx.md) | `asset_source.py`, `fx.py`, price resolver | ~6 400 | 🟡 |
| 04 | [Provider](04_providers.md) | plugin asset / FX / BRIM | 17 013 | 🟡 |
| 05 | [Signals & Risk](05_signals_risk.md) | signal plugin, risk analytics | 4 786 | 🟡 |
| 06 | [DB & modelli](06_db_models.md) | `db/`, `alembic/` | 1 264 | 🟡 |
| 07 | [Schemi & utils](07_schemas_utils.md) | `schemas/`, `utils/` | 13 318 | 🟡 |
| 08 | [Stato & API frontend](08_frontend_state_api.md) | store, client Zodios | 23 715 | 🟡 |
| 09 | [Componenti frontend](09_frontend_components.md) | componenti, route | 92 068 | 🟡 |
| 10 | [Grafici frontend](10_frontend_charts.md) | `charts/`, `signals/` | 4 288 | 🟢 |
| 11 | [Trasversale](11_crosscutting.md) | Async I/O, N+1, `$:`, config | — | 🔴 |
| 12 | [Test & copertura](12_test_coverage.md) | salute suite, copertura, incrocio con codice morto | — | 🔴 |
| 13 | [AI Export](13_ai_export.md) | catalogo, composer, BuildContext, frontend ai-export | 25 748 | 🟡 |
| **14** | [**Backlog per complessità**](14_backlog_per_complessita.md) | **sintesi trasversale — tutti gli interventi, deduplicati e ordinati per complessità e rischio** | — | — |
| **15** | [**Esecuzione S1–S3**](15_esecuzione_s1_s3.md) | **cronaca dell'esecuzione del 2026-08-05 — 32 interventi chiusi, correzioni ai reperti dell'audit, tre lezioni trasversali** | — | — |
| **16** | [**Feature perse nei redesign**](16_feature_perse_nei_redesign.md) | **indagine sul pattern emerso dal report 15 — capacità perse silenziosamente durante un redesign, senza test rossi né traccia nei commit** | — | — |

Il report 12 chiude l'audit e ne **corregge una parte**: una prima misurazione parziale
aveva indicato una copertura del 75,65 % con lacune enormi su API e provider BRIM. Era un
artefatto dello scope di esecuzione. La misura completa è **90,48 %**, e la copertura
*conferma in modo indipendente* i reperti di codice morto dei report 02, 03, 04 e 07.

Il report 13 copre il perimetro **AI Export**, inizialmente escluso perché in lavorazione
da un altro agente, ed è stato eseguito a lavoro concluso con gli stessi strumenti. Esito:
**è il codice migliore del progetto** — 0,38 simboli morti per 1 000 righe, 0 N+1, 0
violazioni async, complessità massima 22 contro 112, copertura 93,5 %, rapporto test:codice
2,42:1 contro 0,79:1. Tre reperti reali, 30 righe di rimozioni proposte.

Il **report 14** non aggiunge reperti: riorganizza quelli esistenti. I report 01–13 sono
ordinati *per sottosistema* e ognuno chiude con la propria lista di interventi — 86 voci
complessive, con sovrapposizioni. Il report 14 le **deduplica (74 voci distinte, 70
residue)** e le riordina **per complessità e rischio**, ignorando il sottosistema. Serve a
rispondere a una domanda che nessun altro report può rispondere da solo: *da dove si
comincia, e cosa non va toccato senza prepararsi.*

Il suo risultato più utile è la scoperta che **complessità e rischio non sono lo stesso
asse**: `git rm fifo_utils.py` è l'azione più atomica dell'elenco ed è anche l'unica
rimozione a rischio medio, mentre le 4 righe di `pyproject.toml` costano meno di tutto e
valgono più di tutto.

Il **report 15** non è un audit, è una cronaca: racconta cosa è successo quando la banda
S1–S3 del report 14 è stata davvero eseguita, il 2026-08-05, da una fleet di 9 agenti
paralleli più una passata di chiusura — 32 interventi chiusi in un solo ciclo. Il suo
contenuto più importante non è l'elenco degli interventi ma **tre lezioni trasversali**,
ciascuna emersa indipendentemente da parti diverse del ciclo. La sintesi delle cinque
correzioni che l'esecuzione ha imposto ai reperti di questo stesso indice è nell'ultima
sezione di questo file, "Aggiornamento — esecuzione S1–S3 (2026-08-05)".

Il **report 16**, in lavorazione parallela a questo aggiornamento, nasce da una delle tre
lezioni del report 15: `LiveTicker.svelte` è sparito dalla Dashboard durante un redesign
precedente senza che alcun test fallisse e senza che alcun commit lo registrasse. Indaga
quanto questo pattern — una capacità persa dentro un redesign, senza nulla che se ne
accorga — sia diffuso altrove nel progetto.

---

## Come leggere i report

Ogni report ha la stessa struttura:

1. **Sintesi** — cosa funziona e cosa no, in prosa
2. **Metriche** — dimensioni e rilievi automatici
3. **Reperti** — classificati per gravità, ciascuno con `file:riga`, impatto concreto,
   tracciatura della logica e rimedio proposto
4. **Interventi raccomandati** — in ordine di valore/rischio

Legenda gravità:

| | Significato |
|---|---|
| 🔴 | Bug o rischio concreto — intervenire |
| 🟡 | Debito tecnico che costa manutenzione |
| 🟢 | Rifinitura, nessuna urgenza |

---

## Strumentazione introdotta

L'audit ha richiesto strumenti che il progetto non aveva. Sono stati integrati in modo
permanente e riproducibile, non usati una tantum:

```bash
./dev.py lint --dead-code                      # backend + frontend
./dev.py lint --dead-code --scope backend      # solo vulture
./dev.py lint --dead-code --all                # include i rilievi a basso segnale
./dev.py lint --dead-code --exclude "*/ai_export/*"
```

| Strumento | Dove | Configurazione |
|---|---|---|
| **vulture** 2.16 | `Pipfile [dev-packages]` | `pyproject.toml` → `[tool.vulture]` |
| **knip** 6.31 | `frontend/package.json` devDependencies | `frontend/knip.json` |

Documentati nelle skill `lint-format-backend` e `lint-format-frontend` e referenziati
dalle instruction backend/frontend.

### Perché il conteggio grezzo non serve a niente

Vulture, lanciato senza contesto di progetto, produce **791 rilievi**. Quasi tutti sono
falsi positivi strutturali: handler FastAPI raggiunti via decoratore, validator Pydantic
risolti dalla metaclasse, provider registrati dinamicamente, membri di `Enum` consumati
per valore. Dopo la configurazione mirata e il filtro per categoria significativa il
numero scende a **57 reperti reali** — che è il numero su cui si può ragionare.

Due correzioni metodologiche hanno cambiato il risultato in corso d'opera, e altre tre
sono emerse a report già avviati:

- `test_cases`, `test_currencies`, `test_file_patterns` sono **proprietà astratte
  obbligatorie del contratto plugin**, consumate dal test harness per progetto. Sono
  state escluse: non sono codice morto, sono l'interfaccia di auto-test.
- La prima passata considerava "produzione" solo `backend/app`, e segnalava quindi tutte
  le funzioni di `user_service` come morte. In realtà le usa la CLI `./dev.py user` via
  `scripts/user_cli.py`. Lo scope di produzione ora include `scripts/` e `dev.py`.
- **Escludere una directory dallo scan rende falsamente morti i simboli che *quella*
  directory consuma.** `resolve_ai_export_temporal_class` risultava "usata solo dai
  test", ma è chiamata da `ai_export/components/technical_shared.py:943` — escluso
  dall'audit su richiesta. L'esclusione va applicata alla **reportistica**, non alla
  **raccolta dei riferimenti**. Vedi report [05](05_signals_risk.md), reperto E2.
- **`ruff --select` *sostituisce* le regole del progetto invece di aggiungersi.** La
  passata estesa disattivava così `PLC0415` e riportava 48 `RUF100` fasulli. Con
  `--extend-select` il conteggio reale è 111. Vedi [11](11_crosscutting.md) K8.
- **Una copertura misurata su un sottoinsieme di categorie mente, e mente al ribasso.**
  La prima misura dava 75,65 % con lacune catastrofiche su API e provider BRIM; eseguendo
  anche `api all` e `external` il dato reale è **90,48 %** e le funzioni azionabili
  passano da 445 a 42. Vedi [12](12_test_coverage.md) L1.

Senza queste correzioni il report avrebbe indicato per la rimozione codice
perfettamente vivo, e avrebbe indirizzato settimane di lavoro sui test nel posto sbagliato.
Il filo comune è sempre lo stesso: **lo strumento misura ciò che gli si dà, non ciò che si
vuole sapere.**

### Un pattern ricorrente: il *DRY orfano*

Emerso in **sei** sottosistemi indipendenti, merita un nome perché è la causa più comune
di codice "morto" in questo progetto. *DRY* è *Don't Repeat Yourself*; *orfano* significa
che l'astrazione esiste ma non ha utilizzatori.

**La sequenza è sempre la stessa:**

1. Qualcuno scrive la cosa giusta — una costante, una property, un helper.
2. Un secondo sviluppatore ha bisogno di quel valore. Non sa che l'astrazione esiste, o è
   semplicemente più veloce riscriverlo a mano. Lo riscrive.
3. Un terzo, uguale. Un quarto, uguale.
4. Risultato: l'astrazione ha **zero riferimenti** (sembra codice morto) **e** il valore è
   duplicato in N punti.

> Si ottiene il **peggio dei due mondi**: la duplicazione che si voleva evitare *e* del
> codice non usato.

Il caso più chiaro è [13](13_ai_export.md) M4.1, riportato con i riferimenti reali:

| File | Cosa c'è scritto |
|---|---|
| `catalog/shared.ts:38` | `AI_EXPORT_DEFAULT_DETAIL_LEVEL = 'standard'` ← **zero utilizzatori** |
| `aiExportMemory.ts:138` | `detailLevel: 'standard'` |
| `aiExportMemory.ts:149` | `includes('standard') ? 'standard' : supported[0]` |
| `aiExportOptions.ts:189` | `includes('standard') ? 'standard' : supported[0]` |
| `AiExportOptionsPanel.svelte:102` | `includes('standard') ? 'standard' : supported[0]` |
| `AiExportOptionsPanel.svelte:123` | `includes('standard') ? 'standard' : supported[0]` |

**Il danno pratico**: per cambiare il default da `standard` a `compact` servono 5 modifiche,
e bisogna sapere che quei 5 punti esistono; dimenticarne uno produce un comportamento
incoerente. Nel frattempo il linter segnala la costante come morta e ne suggerisce la
rimozione — che è esattamente la mossa sbagliata.

Tutte e sei le occorrenze:

| Dove | Astrazione orfana | Riscritta a mano in |
|---|---|---|
| [06](06_db_models.md) F1 | `is_chain`, `providers_used` | 5 punti fra backend e frontend |
| [07](07_schemas_utils.md) G1 | 11 property `*_cur` / conteggi | 8 costruzioni `Currency(...)` inline |
| [08](08_frontend_state_api.md) H4 | `availableLanguages`, `currentLanguageFlag/Name` | selettore lingua |
| [10](10_frontend_charts.md) J1 | `signalLabelToText` | composizione etichette nei componenti |
| [04](04_providers.md) D2 | `get_provider` | docstring che indica l'API sbagliata |
| [13](13_ai_export.md) M4.1 | `AI_EXPORT_DEFAULT_DETAIL_LEVEL` | 5 punti, di cui 4 con **la stessa** espressione di fallback — ✅ fattorizzato |

> **Un settimo caso è stato ritirato.** `isDatasetCatalogEntry` ([13](13_ai_export.md) M4.2)
> era stato classificato come *DRY orfano*, ma tentando la correzione si è visto che due dei
> tre "usi inline" operano su un **tipo diverso** e il terzo non ha bisogno del guard
> (TypeScript restringe già nativamente le unioni discriminate). Non era duplicazione: era
> una funzione semplicemente inutilizzata, ora rimossa. Lezione di metodo: una corrispondenza
> testuale non basta a dichiarare una duplicazione, vanno confrontati i **tipi**.

La risposta giusta quasi mai è "rimuovere": è **adottare**. Rimuovere elimina il reperto
ma lascia la duplicazione.

**L'ultima occorrenza cambia la diagnosi.** Finché il pattern si vedeva solo in
codice stratificato era ragionevole attribuirlo all'età: astrazioni dimenticate, autori
diversi, anni di sedimentazione. Ma il report 13 lo ritrova **identico nel codice più
recente e più curato del progetto** — e per giunta nell'unico sottosistema dove tutto il
resto è immacolato. La spiegazione basata sulla dimenticanza cade.

Il fattore non è quindi il tempo né la bravura: è la **forma dell'astrazione**. In tutti e
sei i casi l'orfano è una *costante nuda* o un *predicato a una riga* — qualcosa il cui
valore si ridigita più in fretta di quanto si trovi l'import. Scrivere `'standard'` sono
10 caratteri; importare la costante significa trovare il file, aggiungere la riga di
import, usare il nome.

**Il rimedio è quindi cambiare la forma, non fare più code review.** Non esportare il
valore, esportare la *regola*:

```ts
// nessuno ridigita a mano una funzione di 3 righe
export function resolveDetailLevel(supported: readonly AiExportDetailLevel[]) {
    return supported.includes(AI_EXPORT_DEFAULT_DETAIL_LEVEL)
        ? AI_EXPORT_DEFAULT_DETAIL_LEVEL
        : supported[0];
}
```

Un'astrazione che incapsula una **regola** non viene re-inlinata, perché ridigitarla costa
più che importarla. Una che espone un **valore nudo**, sì.

### Un pattern opposto: dove il codice morto non si accumula

La domanda da cui nasce questa sezione: **perché il codice morto si accumula in certe parti
del progetto e in altre no?**

| Area | Righe | Simboli orfani | per 1 000 righe |
|---|---:|---:|---:|
| `lib/stores/` frontend | 6 665 | 26 | **3,90** |
| `schemas/` backend | 11 202 | 20 | 1,79 |
| `charts/` frontend | 4 288 | **1** | 0,23 |
| signal + risk backend | 10 903 | **1** | **0,09** |
| **AI Export** (back + front) | **25 748** | **7** (5 dichiarati come seam) | **0,27** |

**Un fattore 40 di differenza.** Non è che in certe cartelle abbiano lavorato sviluppatori
più bravi: spesso sono gli stessi. La differenza è **strutturale**.

Nelle aree pulite ogni componente **deve dichiararsi** a un registry: id, versione,
dipendenze, livelli di dettaglio, visibilità, applicabilità — e ogni dichiarazione è
verificata all'avvio. La conseguenza è che lì **non si può scrivere qualcosa che nessuno usa
senza che si veda**: o il componente compare in un `section_order`, e allora è usato, o non
compare — e allora il conteggio non torna e l'app non parte.

Nelle aree a moduli liberi (`lib/stores/`, `schemas/`, `components/ui/`) quest'obbligo non
esiste. Si esporta una funzione, nessuno la importa, **nessuno protesta mai**. Resta lì per
anni, finché non arriva un audit.

**La lezione pratica**: se si vuole che una parte del codebase resti pulita da sola, non
si deve contare sulla disciplina o sulle review. Le si deve dare un contratto che renda ciò
che è inutilizzato **impossibile o rumoroso**.

**E la conferma sta nell'eccezione.** Dentro l'AI Export l'unico difetto ricorrente
sopravvissuto è proprio il *DRY orfano* della sezione precedente — che colpisce costanti e
helper liberi, cioè **gli unici oggetti di quel sottosistema che non passano da un contratto
dichiarato**. Anche nel codice più rigoroso del progetto, le parti fuori dal contratto si
comportano come tutto il resto.

Non sono le persone: è se la struttura obbliga o no a dichiarare cosa esiste e perché.

---

## Aggiornamento — esecuzione S1–S3 (2026-08-05)

Tutto quanto sopra descrive lo **stato dell'audit alla sua chiusura**. Il 2026-08-05 una
fleet di 9 agenti paralleli più una passata di chiusura ha eseguito l'intera banda di
complessità S1–S3 del backlog trasversale ([14](14_backlog_per_complessita.md)) — 30 voci,
di cui 25 chiuse in banda e 2 chiuse fuori banda come effetto collaterale — insieme a 4
voci nette del Blocco 1 dell'audit mkdocs
([`mkdocsAudit/08-functionality-gap-taxonomy.md`](mkdocsAudit/08-functionality-gap-taxonomy.md),
indice in [`mkdocsAudit/00_INDEX.md`](mkdocsAudit/00_INDEX.md)) e a una regressione
segnalata dall'utente durante il ciclo stesso: **32 interventi chiusi in un solo ciclo**.
Cronaca completa, incluse tre lezioni trasversali che valgono più dell'elenco degli
interventi, in [15 — Esecuzione S1–S3](15_esecuzione_s1_s3.md).

Quattro di quelle chiusure non si sono limitate a *eseguire* un reperto: hanno **corretto**
la diagnosi che questo stesso indice, o l'audit mkdocs gemello, avevano scritto. Vale la
pena elencarle qui, perché un lettore che si fidasse solo del testo originale dei report
01–14 li leggerebbe sbagliati:

| Reperto originale | Correzione imposta dall'esecuzione |
|---|---|
| **1.2** — alzare `max-complexity` da 20 a 25 | **Voce nulla.** Nessuna configurazione `max-complexity`, `C901` o mccabe esiste in alcun punto del progetto — non in `pyproject.toml`, non altrove; il rilievo descriveva una configurazione che non c'è mai stata. |
| **3.1** — barrel `index.ts` morti nel frontend | **Il report originale era corretto; il conteggio finale è più alto.** Il [report 09](09_frontend_components.md) elencava già **12** percorsi e il suo rimedio diceva esplicitamente «rimuovere tutti e 12 (11 sotto `components/` più `src/lib/index.ts`)»; solo il titolo della voce I3 diceva «11», per un errore di etichetta sul proprio elenco. L'esecuzione ne ha rimossi **13**: i 12 previsti più `tanstack-table/index.ts`, che nell'elenco non c'era. |
| **3.7** — 8 bandiere `isXLoaded`/`isXLoading` morte | **Mal contato.** Il codice ne esporta 12; il numero vero, misurato *dopo* la rimozione dei barrel morti (la misura non era attendibile finché i barrel esistevano ancora), è **9**. |
| **[03 F3](mkdocsAudit/03_fx-market-data.md)** — header CSV FX incompatibile, classificato come gap documentale | **Sottovalutato in gravità.** La verifica di codice svolta durante la remediation ha stabilito che si trattava di **corruzione silenziosa dei dati**: una coppia valutaria estranea alla pagina non veniva né invertita né rifiutata, e i valori arrivavano comunque al callback di import come se fossero la coppia corretta. |

Nessuna di queste quattro correzioni cambia la conclusione generale di questo indice — il
codebase resta sano, il debito resta concentrato dove l'audit lo aveva già individuato —
ma tutte e quattro cambiano la cifra o l'attribuzione esatta di un reperto specifico. Chi
cita un numero da questo audit dopo il 2026-08-05 dovrebbe citare la versione corretta, non
quella originale del report in cui la voce compare per la prima volta.

> **Una quinta "correzione" è stata ritirata perché era falsa.** Una versione precedente di
> questa tabella sosteneva che il reperto 2.6 attribuisse due `S110` a
> `backend/app/api/v1/version.py`, un file inesistente. La verifica sugli artefatti ha
> smentito l'accusa: il [report 11](11_crosscutting.md) ha sempre indicato
> `utils/version.py:36,51`, e il [report 14](14_backlog_per_complessita.md) ha sempre
> scritto `version.py`. L'attribuzione sbagliata era stata introdotta dal *briefing* di
> esecuzione, non dall'audit, e da lì si era propagata nei report di chiusura. È un
> promemoria che vale per questo indice quanto per il codice: **anche una correzione va
> verificata contro la fonte prima di essere scritta**, altrimenti si documenta un errore
> che nessuno ha mai commesso.

Il report [16 — Feature perse nei redesign](16_feature_perse_nei_redesign.md) approfondisce
un effetto collaterale dell'esecuzione, non una correzione di reperto: durante la rimozione
dei barrel morti del frontend, `LiveTicker.svelte` si è rivelato non un semplice orfano ma
una capacità — la striscia prezzi live in Dashboard — sparita senza traccia in un redesign
precedente, riconosciuta solo perché l'utente l'ha vista riemergere come file morto.
