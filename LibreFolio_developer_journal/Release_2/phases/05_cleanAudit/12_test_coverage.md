# 12 — Salute della suite di test e copertura

> Report finale dell'audit. Chiude il ciclo: dopo aver misurato il debito
> (report 01–11), qui si misura la *rete di sicurezza* che dovrebbe proteggerlo.
>
> **Fase G** del piano. Deliberatamente eseguito per ultimo: una copertura misurata
> prima di conoscere i reperti non avrebbe saputo dove guardare.

---

## Sintesi

La suite backend è **in ottima salute**: **90,48 %** di copertura su 36 868 statement,
sostanzialmente allineata alla baseline ~92 % della 1.0.1 nonostante la Release 2 abbia
aggiunto ~19 000 righe di codice nuovo (AI Export, risk analytics, 18 plugin BRIM).

Le funzioni realmente scoperte sono **42**, per **155 statement** complessivi — lo 0,42 %
del backend. È un numero abbastanza piccolo da essere azzerato in una sessione.

Un solo test fallisce in modo riproducibile, e **non è un difetto di codice**: è una
guardia di test troppo larga che collide con un campo nuovo introdotto dall'altro agente
sull'AI Export (§ L2.1).

Il reperto metodologicamente più importante di questo report non è un numero, ma una
**trappola di misurazione** che ha prodotto un dato falso del 75,65 % e che va documentata
perché si ripresenterà a chiunque rimisuri la copertura (§ L1).

Il reperto di merito più interessante è invece l'**incrocio fra copertura zero e codice
morto**: le funzioni allo 0 % coincidono quasi esattamente con i reperti dei report 02, 03
e 07. La copertura ha *confermato in modo indipendente* l'analisi statica (§ L5).

---

## L1 — 🔴 Trappola di misurazione: la copertura parziale mente, e mente al ribasso

**Questo è il reperto principale del report.** Non riguarda il codice, riguarda il metodo.

La prima misurazione di questo audit ha prodotto **75,65 %**, con un quadro allarmante:

| File | Copertura *apparente* |
|---|---:|
| `api/v1/fx.py` | 14,6 % |
| `api/v1/uploads.py` | 21,1 % |
| `brim_providers/broker_credit_agricole.py` | 22,7 % |
| `api/v1/brokers.py` | 24,9 % |
| `services/brim_providers/` (intero) | 34,8 % |

Da quel dato sarebbe partita una raccomandazione di lavoro enorme: il report
`coverage-report --summary` contava **445 funzioni azionabili per 6 406 statement**, con
BRIM_PROV a 3 706 statement e API_ENDPOINT a 1 180. Settimane di lavoro.

**Era tutto un artefatto.** Quella misurazione includeva solo le categorie *unit*
(`schemas`, `utils`, `db`, `services`). Le categorie `api` e `external` non erano state
eseguite perché richiedono l'avvio di un server di test e l'accesso alla rete.

Ma il codice API è coperto **dai test API**, e i provider BRIM sono coperti **dai test
external** che li fanno girare sui file di esempio reali. Misurare la copertura senza
quelle categorie equivale a misurare quanto è coperto un tetto guardando solo metà casa.

### Effetto di ogni categoria aggiunta

| Passo | Categoria aggiunta | Totale | Δ |
|---|---|---:|---:|
| 1 | unit (`schemas`+`utils`+`db`+`services`) | 75,65 % | — |
| 2 | `api all` (47 gruppi) | 82,23 % | **+6,58** |
| 3 | `external brim-providers` | 89,96 % | **+7,73** |
| 4 | `external fx-providers` | 90,22 % | +0,26 |
| 5 | `external asset-providers` | 90,26 % | +0,04 |
| 6 | `api users-search` + `portfolio` + `portfolio-wac` | **90,48 %** | +0,22 |

Le aree che sembravano abbandonate erano semplicemente misurate male:

| Area | Unit-only | Completa | Δ |
|---|---:|---:|---:|
| `api/` | 31,6 % | **87,2 %** | +55,6 |
| `services/brim_providers` | 34,8 % | **84,8 %** | +50,0 |
| `services/fx_providers` | 51,0 % | **84,0 %** | +33,0 |
| `services/asset_source_providers` | 57,5 % | **77,2 %** | +19,7 |
| `services/scheduler` | 50,5 % | 75,3 % | +24,8 |

E il conteggio delle funzioni azionabili è passato da **445 (6 406 stmt)** a
**42 (155 stmt)** — un fattore 41×.

> **Regola da ricordare.** Una misurazione di copertura è valida **solo se dichiara quali
> categorie ha eseguito**. Un numero senza quella dichiarazione non è confrontabile con
> nulla, nemmeno con sé stesso di ieri.
>
> Il comando corretto per un dato confrontabile con la baseline 1.0.1 è la sequenza
> completa: `services` + `schemas` + `utils` + `db` + `api all` +
> `external {brim,fx,asset}-providers`. Costo: ~50 minuti.

Questa è la **quarta correzione metodologica** dell'audit, dopo le tre già documentate in
`INDEX.md` (contratto self-test dei plugin, `scripts/` come codice di produzione,
esclusione ≠ mancata raccolta dei riferimenti) e la quinta contando
`--select` vs `--extend-select` di § K8. Il filo comune è sempre lo stesso: **lo strumento
misura ciò che gli si dà, non ciò che si vuole sapere.**

---

## L2 — Salute della suite

### Esito per categoria

| Categoria | File di test | Gruppi | Esito |
|---|---:|---:|---|
| `schemas` | 8 | 8 | ✅ 8/8 |
| `utils` | 12 | 12 | ✅ 12/12 |
| `db` | 5 | 8 | ✅ 8/8 |
| `services` | 90 | 60 | ⚠️ 59/60 |
| `api` | 50 | 50 | ✅ 50/50 |
| `external` | 4 | 3 su 4 | ✅ 3/3 eseguite |
| `e2e` | 2 | — | ⬜ non eseguita (Playwright, richiede frontend buildato) |
| **Totale** | **171** | — | **1 fallimento riproducibile** |

`./dev.py test check-orphans` → **pulito**: tutti i file di test sono registrati nel
dispatcher, nessun test orfano che gira a vuoto o che non gira affatto.

### L2.1 — 🟡 `services signal-plugins-close-only` — guardia di test troppo larga

**Riproducibile.** `1 failed, 61 passed`.

```
backend/test_scripts/test_services/test_signal_plugins_close_only.py:107
test_catalog_contains_nine_close_only_plugins — AssertionError
```

L'asserzione è:

```python
assert '"fast"' not in serialized
```

L'intento originale è legittimo e anzi acuto: impedire che i parametri interni di
pandas-ta (che usa nomi come `fast`, `slow`, `signal`) trapelino nel catalogo pubblico dei
plugin. È una guardia anti-leak.

Il problema è che cerca la **stringa** `"fast"` nell'intero catalogo serializzato, senza
qualificare *dove*. Il commit `7d39ef3e feat(platform): refine AI export signal density`
ha aggiunto ai plugin il campo:

```json
"ai_export_temporal_rules": [{"temporal_class": "fast", ...}]
```

Sul plugin **ROC** il valore `"fast"` è un *valore di dominio legittimo* della
classificazione temporale dell'AI Export, non un parametro pandas-ta trapelato. La guardia
non sa distinguere i due casi perché lavora sul testo, non sulla struttura.

**Non è un difetto di codice: è un difetto di test.** Il rimedio è restringere la guardia
alla sola sezione dei parametri:

```python
params_serialized = json.dumps([p.model_dump() for p in plugin.params_schema])
assert '"fast"' not in params_serialized
```

⚠️ **Territorio dell'altro agente.** Il campo `ai_export_temporal_rules` è parte del lavoro
di ottimizzazione dell'AI Export in corso. Questo reperto è **segnalato, non corretto**:
la correzione va concordata con chi possiede quel file, perché la forma finale del campo
potrebbe ancora cambiare.

### L2.2 — 🟡 `services roi-fifo-utils` — difetto di isolamento fra categorie

Osservato durante l'esecuzione in batch:

```
UNIQUE constraint failed: fx_rates.date, fx_rates.base, fx_rates.quote
```

su EUR/USD del 2025-02-01, in
`test_lots_analysis_service.py::test_buy_sell_summary_converts_to_target_currency` e
`::test_dividend_in_foreign_currency_converted_to_target`.

**Eseguita da sola, la categoria passa** (riverificato: `✅ PASSED`). Passa anche dopo che
`db all` ha ricreato il database. Fallisce solo quando gira dopo altre categorie che hanno
già seminato quel tasso di cambio.

Non è un bug del codice di produzione: è un test che assume un database vergine e inserisce
un tasso FX senza `ON CONFLICT` né cleanup. È **intermittente e dipendente dall'ordine**,
la categoria peggiore di test flaky perché fa perdere fiducia nella suite intera.

**Rimedio**: usare l'upsert già esistente nel servizio FX invece dell'insert diretto,
oppure una fixture `autouse` che ripulisca `fx_rates` per la finestra temporale toccata.

---

## L3 — Copertura per area

**Totale backend: 90,48 %** — 33 357 statement coperti su 36 868, **3 511 scoperti**.

| Area | Statement | Copertura | Scoperti |
|---|---:|---:|---:|
| `main.py` | 149 | 72,5 % | 41 |
| `services/scheduler` | 384 | 75,3 % | 95 |
| `services/asset_source_providers` | 1 447 | 77,2 % | 330 |
| `services/fx_providers` | 614 | 84,0 % | 98 |
| `services/brim_providers` | 5 884 | 84,8 % | 896 |
| `api/` | 1 756 | 87,2 % | 224 |
| `services/risk` | 2 030 | 88,4 % | 235 |
| `services/risk_plugins` | 617 | 89,0 % | 68 |
| `services` (radice) | 9 682 | 92,0 % | 771 |
| `utils/` | 751 | 92,1 % | 59 |
| `services/ai_export` | 6 926 | 93,3 % | 467 |
| `logging_config.py` | 68 | 95,6 % | 3 |
| `schemas/` | 4 998 | 96,4 % | 180 |
| `services/signal_plugins` | 1 162 | 96,6 % | 40 |
| `config.py` | 61 | 98,4 % | 1 |
| `db/` | 338 | 99,1 % | 3 |

### Lettura

**Il gradiente segue esattamente la distanza dal codice deterministico.** Le aree in cima
(`db/` 99,1 %, `schemas/` 96,4 %, `signal_plugins` 96,6 %) sono pura trasformazione di dati:
input → output, testabili senza infrastruttura. Le aree in fondo (`scheduler` 75,3 %,
`asset_source_providers` 77,2 %) dipendono da tempo, rete e processi esterni.

Questo è **atteso e sano**. Non è un obiettivo ragionevole portare `scheduler` al 95 %:
significherebbe mockare l'orologio, e il valore di quei test sarebbe basso.

**Il caso interessante è `services/brim_providers` a 84,8 % su 5 884 statement.** È l'area
più grande del backend dopo `services` e `ai_export`, e le sue 896 righe scoperte sono
**il 26 % di tutto lo scoperto del progetto**. Ma la copertura è ottenuta interamente dai
test `external`, cioè facendo girare i parser su file di esempio reali: è la forma di test
giusta per quel dominio. Le righe scoperte sono i rami d'errore dei parser (formati
malformati, colonne mancanti) — vedi § L4.

**`services/risk` a 88,4 %** è un buon risultato per un'area introdotta in questa release
(riskfolio-lib, QuantLib) e ancora marcata beta nel CHANGELOG.

### Correlazione con il report 11 (complessità)

Le aree meno coperte sono anche quelle a più alta complessità ciclomatica. Le 35 `C901` di
`brim_providers/` (metodi `parse` da 11 a 26 di complessità) sono le stesse funzioni che
concentrano le 896 righe scoperte. Non è una coincidenza: **una funzione con complessità 26
ha 26 cammini, e coprirli tutti richiede 26 file di esempio.** Il debito di complessità si
traduce meccanicamente in debito di copertura.

Questo rafforza la raccomandazione di § K5: spezzare i `parse` più complessi non è solo
leggibilità, è l'unico modo economico per coprirne i rami.

---

## L4 — File a copertura più bassa

Soglia: file con ≥ 60 statement.

| File | Stmt | Copertura | Scoperti |
|---|---:|---:|---:|
| `services/scheduler/joblog.py` | 103 | 59,2 % | 42 |
| `services/scheduler/jobs.py` | 99 | 63,6 % | 36 |
| `services/asset_source_providers/borsa_italiana.py` | 353 | 68,0 % | 113 |
| `services/asset_source_providers/justetf.py` | 305 | 70,2 % | 91 |
| `main.py` | 149 | 72,5 % | 41 |
| `services/asset_source_providers/yahoo_finance.py` | 264 | 73,5 % | 70 |
| `api/v1/assets.py` | 276 | 73,9 % | 72 |
| `services/brim_providers/broker_cryptocom.py` | 176 | 75,6 % | 43 |
| `services/fx_providers/snb.py` | 193 | 76,7 % | 45 |
| `services/brim_providers/broker_cointracking.py` | 220 | 77,3 % | 50 |
| `services/fx_providers/fed.py` | 113 | 78,8 % | 24 |
| `services/brim_providers/broker_investimental.py` | 222 | 79,3 % | 46 |

### 🟡 `scheduler/` è l'unica lacuna con un rischio operativo reale

`joblog.py` 59,2 % e `jobs.py` 63,6 % sono i due file peggiori del backend, e sono anche
quelli il cui fallimento è **più difficile da accorgersi**. Un endpoint API rotto lo scopre
l'utente in un secondo; un job schedulato rotto fallisce alle 3 di notte, silenziosamente,
e il sintomo arriva giorni dopo come "i prezzi non si aggiornano più".

La funzione `build_history_sync_entry` (`joblog.py:129`, **29 statement, 0 %**) è la singola
funzione non coperta più grande del backend. È regolarmente usata da `jobs.py:163`: non è
codice morto, è codice **vivo e non testato** nel percorso meno osservabile del sistema.

**Rimedio a basso costo**: un test unitario che costruisce un `entry` da un risultato di
sync fittizio e ne verifica la forma. Non serve lo scheduler, non serve il tempo: è una
funzione di formattazione. 29 statement per un test da ~20 righe è il miglior rapporto
valore/costo dell'intero report.

### 🟢 I provider a 68–79 % sono un falso allarme

`borsa_italiana.py`, `justetf.py`, `yahoo_finance.py` e i BRIM in questa fascia sono coperti
dai test `external`, che li esercitano sul **cammino felice** con dati reali. Le righe
scoperte sono i rami di errore: HTML cambiato, campo mancante, timeout, formato inatteso.

Coprirli richiederebbe fixture di risposte malformate. È un lavoro sensato ma a **priorità
bassa**: quei rami sono `try/except` difensivi il cui fallimento degrada, non rompe. È
tuttavia lo stesso codice segnalato in § K4 per gli 11 `S110` (`except: pass` silenziosi):
il fatto che siano scoperti *e* silenziosi è ciò che li rende invisibili due volte.

### 🟢 `main.py` 72,5 % è strutturale

Le 41 righe scoperte sono il ciclo di vita dell'app (lifespan, startup dei provider,
shutdown). Sono eseguite a ogni avvio reale ma il coverage le vede solo se un test avvia
l'intero server — cosa che i test API fanno, ma con un percorso di startup semplificato.
Non azionabile a costo ragionevole.

---

## L5 — 🔴 L'incrocio che conta: copertura zero ↔ codice morto

**Questa sezione è il motivo per cui la copertura andava misurata dopo l'analisi statica.**

Le 42 funzioni azionabili rimaste sono così poche che si possono leggere una per una. E
leggendole si scopre che **non sono un elenco di lacune di test: sono in buona parte lo
stesso elenco di codice morto prodotto da vulture nei report 02, 03 e 07** — ottenuto con
un metodo completamente indipendente.

| Simbolo | Stmt | Report | Verdetto incrociato |
|---|---:|---|---|
| `utils/identifier_utils.py: merge_other_identifiers` | 3 | 07 (⚠️ non riassorbito) | **Conferma indipendente.** 0 % in produzione *e* 0 riferimenti da `app/`. La semantica additiva non è mai stata applicata. |
| `portfolio_engine.py: DailyPositionState.valuation_price` | 1 | 02 (riassorbito) | Alias di compatibilità post-rename. 0 % conferma che nessuno usa il vecchio nome. Rimovibile. |
| `portfolio_engine.py: DailyPositionState.valuation_price_ccy` | 1 | 02 (riassorbito) | Idem. |
| `portfolio_engine.py: DailyStateBuilder._price_on_date` | 8 | 02 (riassorbito) | Residuo della vecchia pipeline `portfolio_service`. |
| `provider_registry.py: list_plugin_classes` | 2 | 04 | **Zero riferimenti ovunque**, nemmeno nei test. Morto puro. |
| `provider_registry.py: _get_plugin_code_attr` | 1 | 04 | Helper del precedente. |
| `provider_registry.py: _reject_duplicate_codes` | 1 | 04 | Ramo di validazione mai raggiunto: nessun codice duplicato esiste. |
| `provider_registry.py: _fail_on_discovery_errors` (×2) | 2 | 04 | Ramo d'errore mai raggiunto: la discovery non fallisce mai in test. |
| `lots_analysis_service.py: _empty_response` | 1 | 02 | Ramo degenere mai esercitato. |
| `lots_analysis_service.py: _adjustment_cash_flow_cost` | 6 | 02 | Da verificare: rettifiche di cassa mai testate. |
| `risk/service.py: _geography_group_members` | 2 | 05 | Raggruppamento geografico non esercitato. |

**Il valore di questo incrocio è la fiducia.** Vulture ragiona sull'AST e sbaglia spesso
(791 rilevazioni grezze → 57 reali). La copertura ragiona sull'esecuzione e non sbaglia
mai su ciò che ha osservato. Quando i due metodi indicano lo stesso simbolo, **il dubbio
metodologico sparisce**: quel codice non è vivo per vie dinamiche che vulture non vede,
perché la macchina lo ha eseguito e non ci è mai passata.

In particolare, `merge_other_identifiers` era il reperto ⚠️ più delicato del report 07,
perché una semantica di import additiva mai applicata può nascondere un difetto funzionale
(reimportare un asset da un secondo broker sovrascriverebbe gli identificatori del primo).
La conferma allo 0 % rimuove ogni ambiguità: **quella funzione non è mai stata eseguita, né
in produzione né nei test.** Va discussa come *funzionalità mancante*, non come codice morto.

### 🔴 Trappola: la copertura non vede i sottoprocessi

Tre funzioni in `services/risk/quant/spawn_worker.py` risultano a 0 % e **non sono morte**:

| Simbolo | Stmt | Realtà |
|---|---:|---|
| `_worker_main` | 22 | Usato come `Process(target=_worker_main)` a `spawn_worker.py:167` |
| `_resolve_handler` | 8 | Chiamato da `_worker_main` |
| `_peak_rss_bytes` | 2 | Idem |

`coverage.py` non instrumenta i processi generati con `multiprocessing` in modalità *spawn*
a meno di configurare esplicitamente `COVERAGE_PROCESS_START` e un `sitecustomize`. Il
codice gira — è il cuore dell'ottimizzazione di portafoglio isolata in sottoprocesso — ma
lo strumento è cieco.

**Questa è la stessa classe di errore di § L1**, in miniatura: lo strumento riporta
fedelmente ciò che ha visto, e ciò che ha visto non è tutto ciò che è successo. Chiunque
guardi questo elenco senza il contesto concluderebbe che il worker di ottimizzazione è
codice morto — e cancellerebbe il motore di ottimizzazione.

Anche `OptimizationResourceLimitError.__init__` (3 stmt, 0 %) appartiene a questo gruppo:
è sollevata *dentro* il sottoprocesso.

### 🟢 Non tutto lo 0 % è un problema: gli stub dichiarati

`web_link_finder.py: ApiKeyEngine.__init__` / `.search` (3 stmt, 0 %) **non sono codice
morto né una lacuna di test**. Sono uno stub deliberato, documentato nel docstring:

> *"Seam for a paid search API (Brave / Bing / SerpAPI). Intentionally a stub: it
> establishes the configuration + interface so a real implementation can drop in later
> without touching call sites."*

Raggiungibile solo impostando `LIBREFOLIO_WEB_LINK_FINDER_ENGINE=apikey`. È un punto di
estensione dichiarato, con la sua ragione scritta accanto. **Da lasciare esattamente com'è.**

La differenza fra questo caso e `ensure_rates_multi_source` (§ report 03, ⚠️ non riassorbito)
è istruttiva: entrambi sono scaffolding per il futuro, ma questo è 3 statement con un
docstring che lo dichiara, quello è 30 di complessità ciclomatica. **Uno scaffold onesto è
piccolo e si annuncia.**

---

## L6 — Funzioni azionabili residue

Dopo aver sottratto i falsi positivi di § L5, la lista di lavoro reale è questa.

| Priorità | Simbolo | Stmt | Perché |
|---|---|---:|---|
| 🔴 | `scheduler/joblog.py: build_history_sync_entry` | 29 | Vivo, usato, nel percorso meno osservabile del sistema |
| 🟡 | `api/v1/portfolio_api.py: get_portfolio_wac` | 24 | Coperto solo dopo aver eseguito `api portfolio-wac` — verificare che resti in `api all` |
| 🟡 | `asset_source_providers/borsa_italiana.py: _infer_country_from_issuer` | 9 | Euristica di inferenza: sbaglia silenziosamente se non testata |
| 🟡 | `asset_source_providers/borsa_italiana.py: _infer_sector` | 6 | Idem |
| 🟡 | `schemas/portfolio.py: LotsAnalysisQuery.validate_requested_analyses` | 6 | Validatore di input pubblico mai esercitato |
| 🟢 | `db/models.py: Asset.validate_identifier_other` | 1 | Validatore, correlato a § L5 `merge_other_identifiers` |
| 🟢 | `api/v1/system.py: get_plugin_diagnostics` | 1 | Endpoint diagnostico |
| 🟢 | `api/v1/risk.py: get_risk_scenario_catalog` | 4 | Catalogo statico |
| 🟢 | `api/v1/brokers.py: get_asset_candidates` | 2 | — |

Le restanti funzioni `OTHER` a 0 % ricadono in `services/ai_export/` (14 funzioni,
28 statement) e sono **fuori scope**: territorio dell'altro agente.

**Stima**: le due voci 🔴/🟡 in cima valgono 53 dei 155 statement scoperti azionabili.
Un pomeriggio di lavoro porta la copertura sopra il 90,6 % e — più importante — mette una
rete sotto lo scheduler.

---

## L7 — Test da rimuovere insieme al codice

Il report incrocia con l'analisi "solo test" delle Fasi C: **42 simboli backend sono
referenziati esclusivamente da `test_scripts/`**. Quando l'utente approverà le rimozioni,
i test corrispondenti vanno rimossi *nello stesso commit*.

Lasciare il test dopo aver rimosso il codice produce un fallimento di import; rimuovere il
codice e lasciare il test "per sicurezza" è il meccanismo esatto con cui questi 42 simboli
sono sopravvissuti finora: **un simbolo con un test sembra vivo.**

⚠️ **Regola di sicurezza.** Un test che copre un simbolo morto va letto prima di essere
cancellato: se descrive un requisito reale (es. la semantica additiva di
`merge_other_identifiers`), il test è la **specifica sopravvissuta di una funzionalità
mancante** e va conservato — marcato `xfail` — non buttato.

Questo vale in particolare per i tre reperti ⚠️ del report 02/03/07:
`merge_other_identifiers`, `compute_wac_iterative_multi_broker`, `AssetMetadataService`.
I loro test documentano comportamenti che il prodotto non offre.

---

## L8 — Frontend

**Non misurato in questo audit.** La copertura frontend è prodotta dalla categoria `e2e`
(Playwright), che richiede un frontend buildato e un server di test, e che alimenta un
database separato (`.coverage_data/frontend`).

Non è stata eseguita per due ragioni:

1. **Costo/beneficio**: la suite E2E è la più lenta del progetto e l'audit frontend
   (report 08–10) si è basato su analisi statica (knip), che per il codice morto è più
   affidabile della copertura — un componente può essere coperto da un E2E e comunque non
   essere raggiungibile dalla UI reale (è esattamente il caso di `LiveTicker.svelte`).
2. **Interferenza**: l'altro agente sta modificando l'AI Export, che ha percorsi E2E propri.

**Raccomandazione**: misurarla dopo il merge del lavoro sull'AI Export, con
`./dev.py test e2e all --coverage`, e confrontare i file orfani segnalati da knip con i
file mai toccati dagli E2E. L'intersezione dei due insiemi è codice morto ad altissima
confidenza.

---

## Interventi raccomandati

Ordinati per rapporto valore/rischio.

| # | Intervento | Costo | Valore |
|---|---|---|---|
| 1 | Correggere la guardia `'"fast"'` in `test_signal_plugins_close_only.py:107` restringendola a `params_schema` — **da concordare con l'altro agente** | 10 min | Suite verde |
| 2 | Rendere idempotente l'inserimento FX in `test_lots_analysis_service.py` (upsert o fixture di cleanup) | 20 min | Elimina il flaky order-dependent |
| 3 | Test unitario per `build_history_sync_entry` (29 stmt, 0 %) | 30 min | Rete sotto lo scheduler |
| 4 | Documentare in `.github/skills/testing-backend/SKILL.md` la sequenza completa di categorie necessaria a una misura di copertura valida (§ L1) | 15 min | **Impedisce che la trappola si ripeta** |
| 5 | Test per `_infer_country_from_issuer` / `_infer_sector` di Borsa Italiana | 30 min | Euristiche che sbagliano in silenzio |
| 6 | Configurare `COVERAGE_PROCESS_START` per vedere `spawn_worker.py` | 45 min | Rimuove 32 falsi 0 % permanenti |
| 7 | Alzare `max-complexity` a 25 (§ K5) e attaccare i `parse` BRIM più complessi | — | Riduce insieme complessità *e* scoperto |
| 8 | Misurare la copertura frontend dopo il merge AI Export, incrociandola con knip | 1 h | Codice morto frontend ad alta confidenza |

---

## Nota metodologica finale

Questo report contraddice, con dati migliori, una parte del proprio lavoro preparatorio.
La prima stesura sarebbe partita da "la copertura è scesa dal 92 % al 75,65 %, servono
settimane di lavoro sui provider BRIM e sugli endpoint API". Sarebbe stato **falso**, e
avrebbe indirizzato settimane di lavoro nel posto sbagliato.

La differenza fra le due conclusioni non è stata un'analisi più fine: è stata l'esecuzione
di **tre comandi in più**. Vale la pena tenerlo a mente leggendo gli altri undici report:
ogni numero che contengono dipende dallo scope che gli è stato dato, e lo scope è
un'assunzione, non un dato.

---

*Report 12 di 12 — Fase G dell'audit. Torna a [`INDEX.md`](INDEX.md).*
