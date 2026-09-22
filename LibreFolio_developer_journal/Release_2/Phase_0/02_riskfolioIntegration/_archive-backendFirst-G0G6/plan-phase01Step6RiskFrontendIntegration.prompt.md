# Step 6 — Risk Application Integration

**Stato**: ▶️ AUTORIZZATO — G6-00 chiuso; esecuzione backend-first lineare

**Data riconciliazione**: 29 Luglio 2026

← Master:
[`plan-phase01RiskAnalysisImplementation.prompt.md`](./plan-phase01RiskAnalysisImplementation.prompt.md)

→ Fonte IA autoritativa:
[`plan-phase01Step6RiskFrontendInformationArchitecture.prompt.md`](./plan-phase01Step6RiskFrontendInformationArchitecture.prompt.md)

→ Work item snapshot:
[`workItems/g6-frontend.md`](./workItems/g6-frontend.md)

---

## 0. Mandato

G6 trasforma il backend Risk G0-G5 in un'applicazione coerente su:

- Asset Detail;
- Assets Global;
- Broker Detail;
- Dashboard.

Il backend esistente resta la fonte dei calcoli.

G6 aggiunge o riconcilia solo ciò che serve per:

- scope applicativi corretti;
- catalogo scenari;
- orchestrazione;
- componenti condivisi;
- route;
- presentazione;
- test logici/funzionali.

Non riapre:

- formule G0-G5;
- annualizzazione osservata;
- calendario congiunto;
- QuantLib MC/QMC;
- Riskfolio P13;
- processi `spawn`;
- cache content-keyed;
- semantica VaR/CVaR.

## 0.1 Disciplina di esecuzione

- completare tutto il backend G6 prima della foundation frontend;
- una sola dipendenza per work item;
- foundation frontend non visuale;
- una sola vista funzionale alla volta;
- test logici/strutturali prima del gate;
- stop obbligatorio per review visuale utente;
- nessuna vista successiva prima del via libera esplicito;
- nessun polish estetico autonomo.

---

## 1. Fonti vincolanti

Ordine:

1. [`plan-phase01Step6RiskFrontendInformationArchitecture.prompt.md`](./plan-phase01Step6RiskFrontendInformationArchitecture.prompt.md)
2. [`contract-phase01RiskMetricsMathematical.md`](./contract-phase01RiskMetricsMathematical.md)
3. [`analysis-phase01RiskModularityAndPlacement.md`](./analysis-phase01RiskModularityAndPlacement.md)
4. [`plan-phase01RiskAnalysisApplication.prompt.md`](./plan-phase01RiskAnalysisApplication.prompt.md)
5. [`report-phase01RiskBackendAuditAndRemediation.md`](./report-phase01RiskBackendAuditAndRemediation.md)

In caso di conflitto sul placement G6, prevale il documento IA.

---

## 2. Decisioni consolidate G6

| ID | Decisione |
|---|---|
| G6-D1 | Stesso backend bulk + componenti condivisi + scope diversi non è duplicazione. |
| G6-D2 | Asset Detail: `Overview | Risk & Scenarios`. |
| G6-D3 | Assets Global: `Assets | Correlation | Scenarios | Allocation`. |
| G6-D4 | Dashboard/Broker: summary + pannelli espandibili; nessuna sub-tab Risk. |
| G6-D5 | P13 UI solo in Assets Global → Allocation. |
| G6-D6 | Scope patrimoniale unico: `portfolio + broker_ids`; rimozione `kind=broker`. |
| G6-D7 | Dashboard applica il filtro broker toolbar a ogni pannello. |
| G6-D8 | Catalogo scenari statico, typed, versionato, startup-loaded, built-in + host YAML. |
| G6-D9 | Nomi/descrizioni scenario localizzati nel YAML, non nell'i18n generale. |
| G6-D10 | Historical replay usa rendimenti osservati; proxy solo manuali o esclusione. |
| G6-D11 | Hypothetical shock usa una sola dimensione per esecuzione. |
| G6-D12 | Metadata sector/geography mancanti → `Other=100%`, risultato completato con warning. |
| G6-D13 | Geografia: `european_union`; precedenza Paese > UE > Other; niente somma. |
| G6-D14 | Simulation: `Evoluzione | Distribuzione finale`, stesso output backend. |
| G6-D15 | Query Dashboard/Broker lazy alla prima apertura e risultato mantenuto durante il mount. |
| G6-D16 | Nessun test visuale automatico; validazione design manuale dopo ogni vista funzionale. |
| G6-D17 | Replay espone audit trail typed: contatori, mapping original→proxy, esclusioni e policy effettive. |
| G6-D18 | Accordion state non invalida dati: same-key close/reopen riusa stato; cambio request identity rende stale il vecchio risultato. |
| G6-D19 | Bucket shock: presenti nello scope di default + toggle `Mostra tutti`; `Other` sempre visibile quando previsto. |
| G6-D20 | YAML `tags` opzionali, slug aperti/inerti; nessuna ricerca/filtro UI/API avanzato in G6. |
| G6-D21 | Replay portfolio/broker: peso escluso come residuo a rendimento zero; nessuna rinormalizzazione. |

---

## 3. Stato reale da riconciliare

La UI Risk non parte da zero.

| Area | Stato |
|---|---|
| `frontend/src/lib/stores/risk/riskStore.svelte.ts` | store typed presente |
| `RiskAnalysisPanel.svelte` | presente, circa 740 righe, monolitico |
| `RiskResultFrame.svelte` | presente |
| `CorrelationHeatmap.svelte` | presente |
| `AssetSetRiskPanel.svelte` | presente |
| Dashboard Risk | parzialmente montato |
| Broker Risk | parzialmente montato |
| Assets Correlation | parzialmente montato |
| Asset Detail Risk | placement da correggere |
| P13 UI | assente |
| scenario catalog/editor | assenti |

Strategia:

```text
preservare primitive valide
-> correggere contratti
-> estrarre componenti
-> comporre per pagina
```

Non estendere ulteriormente il monolite.

---

## 4. Architettura di consegna

```text
G6-00 Documentation approval
    ↓
G6-11 unified portfolio scope
    ↓
G6-12 scenario catalog/backend orchestration
    ↓
G6-12A historical replay
    ↓
G6-12B hypothetical shock
    ↓
backend validation + OpenAPI/client sync
    ↓
G6-13 shared frontend state/components (non visuale)
    ↓
G6-20 Asset Detail
    ↓ manual visual approval
G6-30A Assets Correlation
    ↓ manual visual approval
G6-30B Assets Scenarios
    ↓ manual visual approval
G6-30C Assets Allocation
    ↓ manual visual approval
G6-40 Broker Risk
    ↓ manual visual approval
G6-50A Dashboard Risk
    ↓ manual visual approval
G6-50B Home Risk card
    ↓ manual visual approval
G6-60 Integrated validation
```

Le pagine restano separate per:

- routing;
- scope label;
- capability;
- comportamento responsive;
- validazione manuale.

I componenti e le formule restano condivisi.

---

## 5. G6-00 — Gate documentale

### Obiettivo

Congelare:

- IA;
- placement;
- scope;
- catalogo scenari;
- semantica replay/shock;
- backlog.

### Criteri

- IA approvata esplicitamente;
- contract/analysis/application/master coerenti;
- work item riscritti in una catena con un solo predecessore;
- nessuna formulazione stale attiva;
- nessun codice modificato.

### Stato

```text
✅ COMPLETATO — 29 Luglio 2026
```

> **Note implementazione**: approvazione utente ricevuta; adottati gate per vista
> funzionale e policy replay `zero_return_residual`. Il prossimo item è G6-11.

---

## 6. G6-11 — Scope portfolio unificato

### Target

```json
{
  "kind": "portfolio",
  "broker_ids": [1, 4]
}
```

### Semantica

- omesso: tutti i broker accessibili;
- lista: sottoinsieme esatto;
- Broker Detail: cardinalità uno;
- lista non vuota, univoca, canonicalizzata;
- broker non accessibile: errore esplicito;
- nessun filtraggio silenzioso.

### Ordine obbligatorio

1. aggiungere `portfolio.broker_ids`;
2. aggiornare validazione e access control;
3. aggiornare cache identity e metadata;
4. migrare Broker Detail;
5. migrare Dashboard;
6. verificare equivalenza dello scope singolo;
7. eliminare `kind=broker`;
8. rigenerare OpenAPI e client;
9. solo dopo intervenire sulle singole pagine.

### Superfici future

- `backend/app/schemas/risk.py`;
- risk service/orchestration;
- capability catalog;
- API tests;
- OpenAPI client;
- risk store;
- Dashboard route;
- Broker route.

### Test

- schema;
- access control;
- exact subset;
- canonical cache key;
- metadata;
- `[id]` equivalente al vecchio broker scope;
- eliminazione completa di `kind=broker`;
- nessuna regressione full portfolio.

### Migrazione DB

Nessuna.

### Stato

```text
✅ COMPLETATO — 29 Luglio 2026
```

> **Note implementazione**: `PortfolioRiskScope` accetta ora `broker_ids`
> opzionale, canonicalizzato e validato come subset esatto degli accessi utente.
> Scope effettivo, broker canonici e `composition_as_of` sono esposti nei
> metadata; il Broker Detail usa `portfolio + broker_ids=[id]`, la Dashboard era
> già su `portfolio`. Rimossi `BrokerRiskScope`, `RiskScopeKind.BROKER` e tutte
> le capability legacy. OpenAPI/client rigenerati. Verificati schema, access
> control, full portfolio, subset singolo, metadata e rifiuto del discriminator
> legacy: 6 schema test, 74 service test, 8 API test e 6 risk-store test verdi.
>
> **⚠️ Fuori pista**: la prima API sync ha richiesto di rimuovere
> `BrokerRiskScope` anche dal post-processor dei discriminatori. `front check`
> non segnala più errori Risk, ma resta rosso per quattro errori concorrenti
> `SignalAreaSeries` in generated client/renderer, estranei a G6-11.

---

## 7. G6-12 — Scenario catalog e orchestrazione backend

### Obiettivo

Fornire un catalogo:

- statico;
- typed;
- versionato;
- caricato all'avvio;
- built-in + host.

### Struttura logica

```text
scenario_catalog/
├── historical/
└── hypothetical/
```

Host:

```text
<get_data_dir()>/scenario_catalog/
```

### Loader

All'avvio:

1. carica built-in;
2. carica host opzionale;
3. valida con Pydantic;
4. verifica `schema_version`;
5. verifica ID univoci;
6. valida eventuali tag;
7. costruisce catalogo typed;
8. pubblica catalogo via API.

### Error policy

Built-in invalido:

- startup/test failure.

Host invalido:

- file rifiutato;
- errore esplicito nei log;
- warning esposto dove coerente;
- applicazione disponibile.

ID host duplicato:

- file rifiutato;
- nessun override silenzioso.

### Localizzazione

Built-in:

- `en`, `it`, `fr`, `es` obbligatorie.

Host:

- almeno una lingua;
- fallback richiesta → EN → IT → prima disponibile.

Lo scenario content non entra nel catalogo i18n frontend.

### API future

Il contratto deve rendere disponibili:

- catalogo typed;
- scenario kind;
- valori iniziali;
- limiti;
- configurabilità;
- localizzazione;
- eventuali warning host;
- `schema_version`;
- `tags` opzionali come metadata inerte.

Il frontend non legge YAML.

`tags`:

- assente = insieme vuoto;
- slug lowercase ASCII, univoci, bounded;
- vocabolario aperto per cataloghi host;
- nessun enum centrale obbligatorio;
- nessuna semantica di calcolo;
- nessun filtro/search endpoint o UI G6.

### Non-obiettivi

- CRUD;
- DB;
- personal scenario persistence;
- hot reload;
- manual reload;
- generic form engine;
- salvataggio UI → YAML.

### Stato

```text
✅ COMPLETATO — 29 Luglio 2026
```

> **Note implementazione**: introdotti schemi Pydantic typed, loader package-local
> built-in + host in `<get_data_dir()>/scenario_catalog/`, stato process-local
> caricato nel lifespan tramite `asyncio.to_thread` ed endpoint autenticato
> `GET /risk/scenario-catalog`. Il catalogo contiene quattro preset historical,
> quattro hypothetical e il gruppo versionato `european_union` con i 27 membri
> UE. Validati localizzazioni built-in EN/IT/FR/ES, fallback host deterministico,
> tag inerti, chiavi YAML duplicate, limite file, ID globali, error policy host e
> startup failure built-in. PyYAML 6.0.3 è ora dipendenza diretta. OpenAPI/client
> rigenerati. Verificati 8 test schema, 81 test service e 9 test API.
>
> **⚠️ Fuori pista**: la sync client era bloccata dal post-processor
> `fix-openapi-discriminators.mjs`, rimasto sui precedenti subtype response/problem
> AI Export. L'elenco è stato riallineato chirurgicamente alla OpenAPI corrente
> senza modificare il contratto AI Export.

---

## 8. G6-12A — Historical replay

### Contratto

```text
asset IDs
-> historical prices
-> historical FX
-> observed target-currency returns
-> selected composition
```

Portfolio/Broker:

```text
composition_policy = current_buy_and_hold
```

La UI dichiara che la composizione corrente viene applicata al passato.

### Asset senza storia

Scelte utente:

- proxy manuale;
- esclusione.

Proxy:

- asset diverso;
- copertura sufficiente;
- target-currency convertible;
- qualità sufficiente;
- selector asset condiviso;
- restituisce solo rendimenti;
- non cambia identità/peso/valore dell'originale.

Esclusione portfolio/broker:

- il peso escluso resta residuo a rendimento zero;
- gli asset rimanenti non vengono rinormalizzati;
- policy e peso coinvolto sono auditabili.

Nessuna persistenza G6.

### Audit trail

Request:

- mapping original asset → proxy;
- esclusioni esplicite;
- policy asset senza storia.

Response/metadata:

- `proxy_count`;
- mapping original→proxy;
- `excluded_count`;
- asset esclusi + motivo/policy;
- policy effettive;
- `composition_policy`;
- periodo/currency tramite metadata comuni.

Regole:

- audit block sempre presente, anche vuoto;
- mapping canonicalizzato/ordinato;
- proxy invalido → errore, mai esclusione silenziosa;
- qualità/copertura resta nel `DataQualityReport`;
- summary UI + dettaglio per-asset devono rendere il mapping visibile;
- mapping/esclusioni partecipano alla request identity.

### Preset minimi

- Global Financial Crisis;
- COVID-19 crash;
- Inflation and rate shock 2022;
- Custom period.

Le date restano visibili/modificabili.

### Stato

```text
✅ COMPLETATO — 29 Luglio 2026
```

> **Note implementazione**: il replay dispone ora di un contesto serie dedicato,
> separato dal range che determina la composizione corrente. Prezzi e FX del
> periodo replay vengono preparati sul calendario canonico; proxy manuali,
> esclusioni e policy sono validati e canonicalizzati. Il proxy sostituisce solo
> la fonte rendimenti: ID, peso, valore e posizione dell'asset originale restano
> invariati. Per scope portfolio il peso escluso confluisce nel residuo
> zero-return senza rinormalizzazione; per asset/asset-set è omesso dal replay.
> Metadata e output espongono fonte rendimenti per asset e audit typed sempre
> presente con contatori, mapping, esclusioni, pesi, trattamento e policy.
> `DataQualityReport` usa le sorgenti replay/proxy effettive. OpenAPI/client
> sincronizzati. Verificati 9 test schema, 89 test service e 10 test API; il
> modulo client generato si inizializza senza errori Zod.
>
> **⚠️ Fuori pista**: un bundle statico precedente falliva al bootstrap perché il
> post-processor non rendeva concreti tutti i nuovi membri delle union
> discriminate, inclusi gli scenari Risk. Il client sorgente è stato corretto e
> verificato. In questo step il rebuild restava bloccato da export AI Export
> concorrenti mancanti, non dal dominio Risk; il blocco è stato poi risolto e
> ricertificato nella chiusura backend senza modificare file funzionali AI Export.

---

## 9. G6-12B — Hypothetical shock

### Una dimensione

- `asset_class`;
- `sector`;
- `geography`.

Nessuna intersezione.

### Formula

```text
asset_class -> shock diretto
sector/geography -> Σ(exposure × bucket shock)
```

### Metadata mancanti

```text
Other = 100%
```

Con:

- warning metodologico;
- risultato completato;
- nessun `Unclassified`;
- nessuna inferenza;
- nessuna esclusione automatica.

### European Union

```text
id = european_union
precedenza = country > european_union > Other
```

Shock sovrapposti non vengono sommati.

Membership versionata e testata.

### Audit

Risposta:

- esposizioni effettive;
- bucket;
- shock;
- precedenza;
- fallback;
- shock asset finale;
- parametri effettivi.

### UX bucket

Decisione:

```text
default = bucket presenti nello scope
toggle = Mostra tutti
```

Default include:

- bucket con esposizione aggregata >0;
- `Other` sempre per sector/geography;
- bucket modificati manualmente nel form corrente.

`Mostra tutti` espone i bucket canonici ammessi, marcando quelli a esposizione 0%.
Il toggle cambia solo visibilità: request/metadata conservano configurazione
effettiva completa; response conserva audit delle regole realmente applicate.

### Stato

```text
✅ COMPLETATO — 29 Luglio 2026
```

> **Note implementazione**: il contratto provvisorio `asset_id -> shock` è stato
> sostituito da `dimension + bucket_shocks`, canonicalizzato e incluso nei
> metadata effettivi. Il service carica asset type e `FAClassificationParams`;
> il plugin applica shock diretto per asset class e somma
> `exposure × bucket_shock` per settore/geografia. Metadata assenti producono
> `Other=100%` con warning metodologico non degradante: il solo fallback non
> converte il risultato in `partial`. La geografia usa membership versionata e
> precedenza `country > geography_group > Other`; più gruppi sovrapposti senza
> regola specifica falliscono esplicitamente anziché sommarsi. Output per asset
> espone candidati, bucket applicato, regola, esposizione, contributo e shock
> finale; il riepilogo conserva anche bucket configurati a esposizione zero.
> `classification_coverage` distingue la copertura dei metadata dalla copertura
> temporale. Verificati 10 test schema, 18 test analytics, 7 test service e 10
> test API.

---

## 9-bis. Chiusura backend e freeze del client

### Stato

```text
✅ COMPLETATO — 29 Luglio 2026
```

> **Note implementazione**: completato il gate backend G6 prima di iniziare la
> foundation frontend. La suite Risk service completa conta 93 test verdi; i 10
> test API sono verdi anche dopo la generazione finale. Ruff mirato è pulito.
> OpenAPI e client sono sincronizzati in modo idempotente; la union runtime Risk
> espone soltanto `asset | asset_set | portfolio`, mentre le occorrenze residue
> `kind=broker` appartengono esclusivamente ad AI Export. Il pannello Risk
> provvisorio invia ora `dimension=asset_class` e `bucket_shocks`, senza mantenere
> il vecchio payload per asset. Il modulo Zod generato si inizializza, i 6 test
> unitari del risk store passano, `front check` riporta 0 errori/0 warning e il
> build statico completa. Uno smoke Playwright sul server reale `:6040` conferma
> che la pagina login viene renderizzata senza page error.
>
> **⚠️ Fuori pista**: il crash login segnalato proveniva dal bundle statico
> precedente, generato con discriminator Zod incompleti. Dopo la stabilizzazione
> dei cambi concorrenti AI Export il client è stato rigenerato, il bundle
> ricostruito e lo stesso percorso di produzione è tornato operativo. Nessun file
> funzionale AI Export è stato modificato per chiudere questo gate.

---

## 10. G6-13 — Shared frontend foundation

### Obiettivo

Separare query/state/rendering dal layout pagina.

### Componenti target

- `RiskSummary`;
- `ObservedRiskPanel`;
- `RiskStructurePanel`;
- `ComparisonPanel`;
- `ScenariosPanel`;
- `HistoricalReplayEditor`;
- `HypotheticalShockEditor`;
- `SimulationViews`;
- `CorrelationViews`;
- `AllocationPanel`;
- quality/sync wrapper;
- metadata renderer.

### Riuso esistente

| Esistente | Uso |
|---|---|
| `PageToolbar` / `TabBar` | tab pagina |
| `RiskResultFrame` | lifecycle/error/metadata |
| `KpiCard` | output scalari |
| `LineChart` / signal renderer | rolling/comparison/simulation |
| `CorrelationHeatmap` | matrice |
| `DataQualityBanner` | qualità |
| `PageSyncModal` | sync prezzi + FX |
| `SignalAssetParamControl` | selector asset |
| risk store | cache/dedup/capability |

### Regole

- niente matematica TypeScript;
- niente ID grezzi visibili;
- no duplicate request builders;
- payload MC/QMC canonici;
- scenario request = parametri effettivi modificati;
- response metadata = parametri realmente usati.

### Stato

```text
✅ COMPLETATO — 29 Luglio 2026
```

> **Note implementazione**: estratto `riskRequest.ts` come unico builder e
> normalizzatore typed basato sul client generato. La request identity
> canonicalizza valuta, subset broker, asset universe, proxy ed esclusioni,
> preservando l'ordine degli array contrattuali. Gli `instance_id` delle query
> singole sono stabili e non usano più il tempo corrente. Il risk store conserva
> in-flight, risultato ed errore per identità, supporta force refresh e
> invalidazione di sessione/portfolio senza introdurre stato UI globale. Il
> pannello condiviso scarta le risposte stale per base, confronto, stress e
> simulazione. Aggiunti stati typed e builder per replay, hypothetical,
> MC/QMC e switch `Evoluzione | Distribuzione finale`. Verificati 11 test
> Vitest e `front check` con 0 errori/0 warning; nessun placement pagina o
> styling è stato modificato.

---

## 11. G6-20 — Asset Detail

### IA

```text
[ Overview ] [ Risk & Scenarios ]
```

Overview preserva:

- prezzo;
- eventi;
- misure;
- editor;
- Signals;
- rolling-risk SignalPlugin.

Risk & Scenarios:

- summary;
- rischio osservato;
- downside;
- confronto;
- correlazione asset-centrica;
- hypothetical;
- replay;
- MC/QMC.

### Vincoli

- nessun duplicato del configuratore Signals;
- Risk richiede automaticamente drawdown, rolling return/volatility/Sharpe con
  default backend, senza dipendere dai Signals salvati;
- rolling beta parte soltanto dopo la scelta di un asset reale;
- la `PageToolbar` completa è condivisa fra le due tab;
- `Abs/%` vive dentro `PriceChartFull`, identico in Asset e FX Detail;
- AI Export page-level sostituisce `Abs/%` nelle due toolbar e viene rimosso
  dagli header Signals;
- storico deterministico automatico; confronto dopo selezione; scenari lazy;
- nessuna Allocation.

### Test

- tab/navigation;
- rolling SignalPlugin riusati;
- no secondo configuratore;
- query analytic scoped asset;
- asset-centric correlation;
- comparison asset reale;
- scenario payload;
- simulation view switch.

### Stato

```text
✅ COMPLETATO — 29 Luglio 2026
```

> **Note implementazione**: Asset Detail espone ora le tab URL-backed
> `Overview | Risk & Scenarios`. Overview conserva chart, editor, misure,
> metadata e configuratore Signals; la nuova vista riusa i rolling Risk
> SignalPlugin come summary selezionabile e rimanda allo stesso configuratore,
> senza duplicarlo. La vista asset-scoped compone VaR/CVaR, confronto con asset
> reale, hypothetical shock, historical replay e MC/QMC, senza Allocation.
> Gli editor scenario consumano il catalogo typed: bucket presenti di default,
> `Mostra tutti` alimentato dai cataloghi asset class/settori/Paesi/gruppi,
> proxy o esclusione manuale, date replay modificabili e payload effettivi.
> Risultati stress e replay mostrano audit bucket/fallback, mapping proxy,
> esclusioni e policy realmente applicate. Simulation espone
> `Evoluzione | Distribuzione finale`.
>
> **Test funzionali/strutturali**: 11 test Vitest risk-store verdi; suite Risk
> Playwright 6/6 verde; flow Asset Risk finale verde dopo audit UI; regressione
> Asset Detail con 18 casi già verdi e il solo selector test stale corretto e
> rieseguito con esito verde. `front check` 0 errori/0 warning, build statico e
> audit i18n EN/IT/FR/ES verdi.
>
> **⚠️ Fuori pista**: l'audit i18n ha rilevato 11 chiavi backend-driven P13
> mancanti; aggiunte senza anticipare la UI Allocation. Il test rolling beta
> cercava il vecchio wrapper test id, mentre il controllo funzionante usa
> `signal-comparison-asset-select-control`; aggiornato solo il test.

### Gate

Stop e validazione visuale utente della sola vista Asset Detail.

### Rifinitura H1 approvata — 30 Luglio 2026

La prima review umana ha respinto il blocco summary dipendente dai Signals e il
pannello-calcolatore monolitico. La correzione segue una catena lineare:

```text
historical_kpi asset backend
-> API sync
-> Abs/% in PriceChartFull Asset/FX
-> AI Export nelle PageToolbar Asset/FX
-> STOP shell
-> rischio osservato + downside automatici
-> STOP
-> confronto guidato
-> STOP
-> scenari progressive disclosure
-> STOP finale H1
```

> **Note implementazione H1-R0 — 30 Luglio 2026**: IA e piano esecutivo
> riallineati. Tutte le metriche che richiedono soltanto asset, periodo e valuta
> saranno automatiche; beta richiede un asset reale; shock, replay e simulazione
> restano lazy perché introducono assunzioni. La toolbar Asset è page-level e la
> migrazione `Abs/%`/AI Export è simmetrica con FX Detail.
>
> **✅ H1-R1 completato — 30 Luglio 2026**
>
> **Note implementazione**: hard cut da `portfolio_kpi` a `historical_kpi`
> (`algorithm_version 2.0.0`). Il plugin historical supporta ora scope
> `asset | portfolio` con una sola formula su `primary_returns`: gli asset usano
> close-return canonici in valuta target e metadata
> `method=historical_close_returns`/`return_basis=price_only`; il portafoglio
> conserva TWRR e `method=historical_twrr`. Aggiunti oracoli matematici asset,
> copertura service end-to-end e capability catalogo/API.
>
> **✅ H1-R2 completato — 30 Luglio 2026**
>
> **Note implementazione**: migrati consumer, fixture, mock E2E e i18n frontend al
> solo codice `historical_kpi`; rimossi tutti i riferimenti runtime al nome
> precedente. Suite Risk backend verde con 95 test service + 10 API. OpenAPI e
> client TypeScript rigenerati due volte con hash invariati alla seconda
> generazione. Ruff e Black sono verdi sulle superfici backend modificate.
>
> **⚠️ Fuori pista**: il lint globale ha esposto 26 violazioni preesistenti fuori
> scope e aveva applicato fix automatici a file non H1; tali fix sono stati
> rimossi chirurgicamente. Nessuna correzione estranea è stata mantenuta.
>
> **✅ H1-R3 completato — 30 Luglio 2026**
>
> **Note implementazione**: `Abs/%` è ora un unico controllo chart-local dentro
> `PriceChartFull`, identico per Asset e FX. Il parent conserva `viewMode` tramite
> callback esplicita, quindi prezzo, overlay Signals, tooltip e `MeasurePanel`
> continuano a consumare lo stesso stato. Le copie nelle due `PageToolbar` sono
> state rimosse; Asset conserva linea/candela e FX mantiene candlestick
> disabilitato. `front check` è verde e i due test Playwright mirati verificano
> posizione nel grafico, assenza dalla topbar e sincronizzazione dello stato.
>
> **✅ H1-R4 completato — 30 Luglio 2026**
>
> **Note implementazione**: i menu AI Export Asset e FX esistenti sono stati
> spostati dagli header `Signals` nelle rispettive `PageToolbar`, preservando
> dominio, contesto, compatibilità catalogo e memory key. La toolbar Asset è ora
> condivisa fra `Overview` e `Risk & Scenarios`; nel tab Risk i pulsanti duplicati
> Sync/Refresh del pannello sono nascosti e il Refresh page-level propaga un
> reload forzato alla query Risk. La documentazione utente Signals EN/IT/FR/ES
> descrive la nuova collocazione. `front check`, build, audit i18n, 11 test unit
> risk-store, 21 test Asset Detail, 13 test FX Detail e 6 test Risk E2E sono
> verdi.
>
> **✅ H1-G1 completato — 30 Luglio 2026**: review umana approvata per
> simmetria Asset/FX, toolbar Asset fra le tab, controllo `Abs/%` chart-local,
> collocazione AI Export e wrapping responsive.
>
> **⚠️ Correzione review H1-G1 — 30 Luglio 2026**: la prima verifica ha
> approvato la shell salvo la navigazione Asset, ancora resa da un `TabBar`
> autonomo. Le tab `Overview | Risk & Scenarios` sono state spostate nella zona
> tabs della stessa `PageToolbar`, seguendo Dashboard; il banner qualità viene
> dopo l'intera toolbar. Rimossi import/wrapper esterni e aggiunta regressione
> strutturale. Type-check, build, 21 test Asset Detail e 6 test Risk E2E sono
> verdi. La correzione è stata approvata visualmente; H1-R5 è il prossimo e
> unico item eseguibile.

---

## 12. G6-30 — Assets Global

Esecuzione obbligatoriamente seriale:

```text
G6-30A Correlation
-> STOP
G6-30B Scenarios
-> STOP
G6-30C Allocation
-> STOP
```

Le tab non ancora implementate non vengono esposte come placeholder vuoti.

### IA

```text
[ Assets ] [ Correlation ] [ Scenarios ] [ Allocation ]
```

### Shared asset universe

Un solo stato route-level per:

- Correlation;
- Scenarios;
- Allocation.

Broker seed = asset set, non holdings weights.

### Correlation

```text
[ Heatmap ] [ Asset centrale ]
```

Default iniziale:

- desktop e ≤20: heatmap;
- mobile o >20: asset-centric;
- override manuale sempre disponibile.

### Scenarios

- hypothetical;
- historical replay;
- confronto % multi-asset;
- qualità/copertura;
- proxy/exclusions.

Multi-asset stress non vive in Correlation.

### Allocation

Titolo:

```text
Composizione ipotetica
```

Main:

- strategy;
- covariance estimator;
- min/max weight;
- run.

Advanced:

- risk-free;
- solver;
- frontier;
- sensitivity;
- advanced constraints;
- technical metadata.

Solver effettivo sempre visibile nei metadata.

### Test

- quattro tab;
- universe condiviso;
- manual view switch;
- responsive default;
- scenario tab separata;
- Allocation wording;
- no holdings weights;
- progressive disclosure;
- solver in Advanced;
- frontier table/scatter rendering;
- effective solver metadata.

### Gate

- dopo Correlation: stop e approvazione;
- dopo Scenarios: stop e approvazione;
- dopo Allocation: stop e approvazione.

---

## 13. G6-40 — Broker Detail

### Scope

```text
portfolio + broker_ids=[currentBrokerId]
```

### IA

Summary + pannelli espandibili condivisi:

- Rischio osservato;
- Struttura del rischio;
- Confronto;
- Scenari.

### Label

```text
Rischio interno a: {broker}
```

### Lazy policy

- query al primo open;
- close/reopen same-key riusa in-flight/result/error;
- cache/retention garantita nello stesso mount;
- input identity cambiata → risultato precedente non corrente;
- pannello aperto ricarica subito, pannello chiuso alla prossima apertura;
- no URL/localStorage accordion state.

### Vincoli

- nessuna Allocation;
- nessun contratto `kind=broker`;
- nessuna semantica di rischio patrimoniale totale.

### Test

- scope cardinalità uno;
- equivalenza subset;
- label;
- lazy query;
- result retention;
- sync/quality;
- scenari in valuta/NAV del subset dove previsto.

### Gate

Stop e validazione visuale utente della sola vista Broker Risk.

---

## 14. G6-50 — Dashboard

### Scope

```text
portfolio + broker_ids=toolbarSelection
```

oppure omit per full accessible portfolio.

### IA

Stesso componente Broker:

- summary sempre visibile;
- Observed aperto;
- Structure aperto desktop/chiuso mobile;
- Comparison chiuso;
- Scenarios chiuso.

### Regola critica

Il filtro broker governa ogni pannello e ogni query.

### Home Risk card

Solo dopo approvazione tab Risk:

- metriche nominate;
- no risk score;
- stesso scope;
- link alla tab Risk.

La card è un work item separato e ha un proprio gate visuale.

### Vincoli

- nessuna Allocation;
- nessun warning full-portfolio quando filtro attivo;
- nessun URL/localStorage accordion state.

### Test

- broker payload su tutti gli analytic;
- cambio filtro invalida correttamente la request identity;
- panel lazy;
- retained results;
- Home card same scope;
- no custom score.

### Gate

1. stop dopo Dashboard Risk;
2. solo dopo approvazione implementare Home Risk card;
3. nuovo stop dopo la card.

---

## 15. Simulation UI

Vista interna condivisa:

```text
[ Evoluzione ] [ Distribuzione finale ]
```

Evoluzione:

- P5/P50/P95 nel tempo;
- storico vs simulato;
- MC/QMC;
- `random_seed` o `sobol_start_index`.

Distribuzione:

- terminal values/returns;
- terminal P5/P50/P95;
- probability of loss;
- target threshold solo se backend-supported.

Wording:

```text
simulato
```

Mai:

```text
previsto
```

---

## 16. Stato pannelli Dashboard/Broker

| Sezione | Desktop | Mobile | Query |
|---|---|---|---|
| Summary | visibile | visibile | eager minima |
| Observed Risk | aperta | aperta | eager |
| Risk Structure | aperta | chiusa | eager desktop, lazy mobile |
| Comparison | chiusa | chiusa | lazy |
| Scenarios | chiusa | chiusa | lazy |

Il responsive default può essere calcolato al mount.

Una scelta utente successiva non deve essere sovrascritta da resize automatici.

### 16.1 Lifecycle dati

`open/closed` è stato UI. Non è cache invalidation.

Scenario A:

```text
open -> query
close -> query/result retained
reopen same key -> reuse, no refetch
```

Se la query è in-flight, chiudere non la cancella. Se fallisce, l'errore same-key
resta fino a retry esplicito o cambio input.

Scenario B:

```text
date/scope/currency/params change
-> new canonical request identity
-> old result not current
```

- pannello aperto → nuova query;
- pannello chiuso → query lazy alla riapertura;
- vecchia response non può sovrascrivere la nuova identity;
- vecchia key può restare nella cache e tornare utile se gli input vengono
  ripristinati.

`riskStore`:

- costruisce key canoniche;
- deduplica query in-flight;
- conserva cache di sessione;
- invalida su sync/mutazioni/refresh secondo policy;
- può riusare una entry dopo remount, ma il riuso cross-mount non è garanzia UI.

Componenti pagina:

- conservano solo apertura/attivazione e riferimento allo stato query;
- non cancellano cache quando chiusi;
- perdono stato locale all'unmount.

---

## 17. Test e validazione

### Backend

- scope;
- auth;
- cache identity;
- scenario catalog;
- replay/proxy + audit trail;
- YAML tags;
- shocks;
- bucket visibility semantics;
- EU precedence;
- metadata;
- no regressione G0-G5.

### Frontend logico/funzionale

- request payload;
- routing/tab;
- shared universe;
- lazy panels;
- same-key retention/no refetch;
- request identity changes;
- stale response isolation;
- sync invalidation vs accordion state;
- bucket `Mostra tutti`;
- capability gating;
- sync/quality;
- effective metadata;
- typed editor state;
- real-backend smoke minimo.

### Non eseguire

- visual regression;
- snapshot estetici;
- pixel/layout assertions;
- test per classi CSS;
- test basati su traduzioni.

### Validazione manuale

Dopo ogni vista funzionale l'utente valida:

- gerarchia;
- densità;
- spacing;
- responsive;
- leggibilità chart;
- progressive disclosure;
- gusto visuale.

---

## 18. Definition of Done G6

G6 è completo solo quando:

1. scope portfolio unificato;
2. `kind=broker` eliminato;
3. catalogo scenari typed e startup-loaded;
4. replay/proxy/shock conformi al contratto;
5. componenti condivisi estratti;
6. quattro superfici coerenti;
7. P13 solo in Allocation;
8. Dashboard rispetta filtro broker;
9. test logici/funzionali verdi;
10. smoke real-backend verde;
11. ogni vista funzionale approvata manualmente;
12. report finale aggiornato.

---

## 19. Rischi

| Rischio | Mitigazione |
|---|---|
| scope migration rompe cache/API | migrazione prima delle pagine + equivalence tests |
| monolite continua a crescere | estrazione shared foundation prima di nuova UI |
| YAML diventa form DSL | editor noti e schema typed |
| host YAML rompe startup | reject file + warning, app disponibile |
| replay suggerisce backtest storico reale | wording `current_buy_and_hold` esplicito |
| proxy altera identità economica | proxy fornisce solo returns |
| missing metadata appare più preciso del vero | `Other=100%` + warning auditabile |
| P13 sembra rebalance advice | unica casa Allocation + disclaimer |
| lazy panels producono richieste duplicate | session cache/dedup + mounted retention |
| agent decide il design | gate manuale pagina per pagina |

---

## 20. Prossimo passo consentito

```text
G6-11 — scope portfolio unificato
```

Non iniziare il frontend finché scope, catalogo, replay, shock e API sync non
sono completati e verificati.
