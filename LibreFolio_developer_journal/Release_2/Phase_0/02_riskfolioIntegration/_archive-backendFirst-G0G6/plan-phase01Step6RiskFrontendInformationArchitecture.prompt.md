# Step 6 — Risk Information Architecture, Scenarios & Placement

**Stato**: ✅ APPROVATO — contratto G6 congelato; implementazione autorizzata

**Data revisione**: 29 Luglio 2026

**Implementazione autorizzata**: sì, dal 29 Luglio 2026

← Piano padre:
[`plan-phase01Step6RiskFrontendIntegration.prompt.md`](./plan-phase01Step6RiskFrontendIntegration.prompt.md)

← Master:
[`plan-phase01RiskAnalysisImplementation.prompt.md`](./plan-phase01RiskAnalysisImplementation.prompt.md)

Fonti:

- [`contract-phase01RiskMetricsMathematical.md`](./contract-phase01RiskMetricsMathematical.md)
- [`analysis-phase01RiskModularityAndPlacement.md`](./analysis-phase01RiskModularityAndPlacement.md)
- [`brainstorm-phase01RiskUiConcepts.md`](./brainstorm-phase01RiskUiConcepts.md)
- [`review-risk-analysis-feedback.md`](./review-risk-analysis-feedback.md)

---

## 0. Scopo e stop obbligatorio

Questo documento è la fonte autoritativa per:

- Information Architecture G6;
- placement per pagina;
- scope canonici;
- riuso componenti;
- catalogo scenari;
- semantica historical replay;
- semantica hypothetical shock;
- UI simulation;
- ordine della futura shared foundation.

Questa revisione è **solo documentale**.

Non autorizza:

- modifiche backend/frontend;
- API o OpenAPI;
- cataloghi YAML reali;
- test;
- traduzioni;
- dipendenze;
- work item esecutivi;
- shared foundation;
- route o componenti.

Dopo questa revisione documentale il lavoro si ferma.

---

## 1. Principio generale di riuso

> La presenza della stessa UI in pagine diverse non rappresenta una duplicazione
> se viene riutilizzato lo stesso componente, alimentato dallo stesso backend bulk
> e configurato con scope differenti.

```text
Backend unico e bulk
        │
        ├── asset
        ├── asset_set
        └── portfolio + broker_ids
                │
                ▼
Componenti frontend condivisi
        │
        ├── Asset Detail
        ├── Assets Global
        ├── Broker Detail
        └── Dashboard Risk
```

La posizione della UI determina **la domanda alla quale risponde**.

Lo scope determina **gli asset o i broker analizzati**.

È corretto riusare:

- lo stesso componente Correlation in Assets Global, Asset Detail e Risk panel;
- lo stesso componente Scenarios con scope `asset`, `asset_set` o `portfolio`;
- lo stesso contenitore Risk per Dashboard e Broker Detail;
- lo stesso backend bulk con payload diversi;
- gli stessi editor tipizzati per preset differenti.

Evitare:

- endpoint differenti per la stessa analisi;
- formule duplicate;
- componenti quasi identici ma separati;
- contratti divergenti fra Dashboard e Broker;
- calcoli finanziari nel frontend;
- YAML che decide arbitrariamente componenti o layout Svelte.

---

## 2. Baseline reale da preservare

La UI Risk è già parzialmente materializzata.

| Superficie | Stato reale |
|---|---|
| catalog/query store typed | presente |
| cache/deduplica/session tests | presenti |
| `RiskAnalysisPanel.svelte` | presente, monolitico |
| `RiskResultFrame.svelte` | presente |
| `CorrelationHeatmap.svelte` | presente |
| `AssetSetRiskPanel.svelte` | presente |
| Dashboard Risk | montato |
| Broker Detail Risk | montato |
| Assets → Correlation | montato |
| Asset Detail Risk | montato fuori placement |
| quality + sync | presenti |
| MC/QMC controls | presenti |
| P13 frontend | assente |
| scenario catalog | assente |
| typed scenario editors | assenti |
| real-backend Risk smoke | assenti |

La strategia è:

```text
audit -> estrazione componenti -> composizione per pagina
```

Non:

```text
riscrittura completa -> quattro implementazioni parallele
```

---

## 3. IA finale

### 3.1 Asset Detail

```text
[ Overview ] [ Risk & Scenarios ]
```

### 3.2 Assets Global

```text
[ Assets ] [ Correlation ] [ Scenarios ] [ Allocation ]
```

Le quattro tab non vengono compresse preventivamente.

### 3.3 Dashboard e Broker Detail

Una sola tab `Risk`, senza sub-tab:

```text
summary sempre visibile
+
pannelli espandibili condivisi
```

### 3.4 P13

La UI P13 vive solo in:

```text
Assets Global -> Allocation
```

Non vive in Dashboard o Broker Detail in G6.

---

## 4. Asset Detail

## 4.1 Navigazione

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ ASSET HEADER                                                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│ PAGE TOOLBAR · periodo · prezzo/valuta · AI Export · edit · sync · refresh  │
├────────────────────────────────┬─────────────────────────────────────────────┤
│ Overview                       │ Risk & Scenarios                            │
└──────────────────────────────────────────────────────────────────────────────┘
```

Le tab usano la zona integrata della `PageToolbar`, come in Dashboard: non
esiste un `TabBar` card esterno. La toolbar è page-level e resta identica
cambiando tab. `Abs/%` non è un'azione pagina: vive dentro `PriceChartFull`.
La stessa migrazione si applica a FX Detail, che usa lo stesso componente
prezzo. AI Export occupa lo slot liberato nella toolbar Asset/FX e non vive più
nell'header `Signals`.

## 4.2 Overview

Mantiene l'esperienza corrente:

- chart del prezzo;
- eventi;
- misure;
- editor;
- configurazione Signals;
- cinque rolling-risk come normali `SignalPlugin`.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ OVERVIEW                                                                     │
│                                                                              │
│ PriceChartFull · line/candle · eventi · misure · editor · settings           │
│                                                                              │
│ Signals                                                                      │
│ Technical · Trend · Momentum · Volatility · Risk                             │
│                                           └─ Drawdown                        │
│                                           └─ Rolling Return                  │
│                                           └─ Rolling Volatility              │
│                                           └─ Rolling Sharpe                  │
│                                           └─ Rolling Beta                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 4.3 Risk & Scenarios

La seconda tab fornisce una lettura guidata e non dipende dalla configurazione
Signals salvata in Overview:

```text
Risk summary
├── rischio osservato
├── downside
├── confronto
├── diversificazione asset-centrica
└── scenari
    ├── hypothetical shock
    ├── historical replay
    └── MC/QMC
```

Non duplica l'intero configuratore dei Signals. Richiede automaticamente al
backend i Risk SignalPlugin canonici con i loro default dichiarati:

- drawdown;
- rolling return 30 giorni;
- rolling volatility 30 giorni;
- rolling Sharpe 90 giorni.

Il confronto con un asset reale aggiunge rolling beta 90 giorni usando la stessa
selezione. Overview resta il luogo per overlay personalizzati; la tab Risk usa
istanze automatiche, non persistite e indipendenti.

Non può:

- mantenere una seconda configurazione Signals completa;
- introdurre formule locali;
- persistire configurazioni parallele.
- obbligare l'utente a tornare in Overview per ottenere l'analisi base.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ RISK & SCENARIOS · asset · periodo · valuta · osservazioni · quality         │
├──────────────────────────────────────────────────────────────────────────────┤
│ RISCHIO OSSERVATO                                                            │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ Volatilità · Max Drawdown · Sharpe · Sortino                           │ │
│ │ un grafico, metrica rolling già calcolata e selezionabile              │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────────────┤
│ DOWNSIDE                                                                     │
│ VaR/CVaR automatici · confidence · horizon · osservazioni                    │
├──────────────────────────────────────────────────────────────────────────────┤
│ CONFRONTO                                                                    │
│ asset reale -> auto-run active return / TE / IR / correlation / beta         │
│ cumulative return + drawdown comparato                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ DIVERSIFICAZIONE ASSET-CENTRICA                                              │
│ asset corrente vs asset-set scelto -> lista correlazioni ordinate            │
│ [Apri matrice completa in Assets → Correlation]                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ SCENARI                                                                      │
│ pannelli lazy: hypothetical shock | historical replay | MC/QMC               │
│ simulazione: [Evoluzione] [Distribuzione finale]                             │
└──────────────────────────────────────────────────────────────────────────────┘
```

Sorgenti:

| Blocco | Sorgente |
|---|---|
| snapshot storico | `historical_kpi` |
| rolling chart | istanze automatiche `SignalPlugin` Risk |
| VaR/CVaR | `historical_var` |
| confronto reale | `comparison` |
| correlazione | `correlation` con `asset_set` |
| stress | `stress` |
| simulation | `simulation` |

Nessuna `Allocation` su singolo asset.

Regola di esecuzione:

```text
richiede solo asset/periodo/valuta -> automatico
richiede asset di confronto        -> dopo selezione
richiede assunzioni di scenario    -> lazy + azione esplicita
```

---

## 5. Assets Global

## 5.1 Quattro tab

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ ASSETS PAGE TOOLBAR · DATE · CURRENCY · VIEW ACTIONS                        │
├────────────────┬────────────────┬────────────────┬───────────────────────────┤
│ Assets         │ Correlation    │ Scenarios      │ Allocation                │
└────────────────┴────────────────┴────────────────┴───────────────────────────┘
```

Non comprimere preventivamente le tab.

Se il numero crescerà in futuro, la navigazione verrà riprogettata allora.

## 5.2 Assets

Mantiene la vista corrente:

- grid/list;
- filtri;
- ricerca;
- azioni;
- date/currency condivise.

## 5.3 Asset universe condiviso

Correlation, Scenarios e Allocation consumano lo stesso asset universe.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ ASSET UNIVERSE                                                               │
│ Seed: [Tutti gli asset ▾] [Broker: Directa ▾]                                │
│ [+ Cerca asset]   (AAPL ×) (VWCE ×) (GLD ×) (BND ×)                         │
│                                                                              │
│ Il broker costruisce solo il set iniziale. Nessun peso o quantità è usato.  │
└──────────────────────────────────────────────────────────────────────────────┘
```

Lo stato del set vive a livello route:

- resta disponibile cambiando tab;
- governa le request `asset_set`;
- partecipa alla cache identity;
- non viene duplicato in tre componenti.

## 5.4 Correlation

Contiene:

- asset universe condiviso;
- heatmap;
- vista asset-centrica;
- qualità;
- copertura;
- osservazioni;
- asset esclusi.

Le due visualizzazioni sono liberamente commutabili:

```text
[ Heatmap ] [ Asset centrale ]
```

Default responsivo iniziale, da validare visualmente:

```text
desktop e asset <= 20 -> heatmap
mobile o asset > 20   -> lista asset-centrica
```

Questa soglia:

- non è un vincolo finanziario;
- non cambia il backend;
- non nasconde il controllo manuale;
- non è una decisione definitiva.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ CORRELATION · quality · exclusions · n · coverage · currency                │
│ View: [Heatmap] [Asset centrale: AAPL ▾]                                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ HEATMAP NxN                           oppure LISTA ASSET-CENTRICA              │
│                                                                              │
│ cell status · n · coverage              AAPL vs MSFT  0.71                   │
│                                         AAPL vs VWCE  0.64                   │
│                                         AAPL vs GLD   0.04                   │
└──────────────────────────────────────────────────────────────────────────────┘
```

Lo stress multi-asset **non** vive più in Correlation.

## 5.5 Scenarios

Contiene:

- hypothetical shock;
- historical replay;
- confronto percentuale multi-asset;
- qualità e copertura;
- stesso asset universe di Correlation e Allocation.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ SCENARIOS                                                                    │
│ Preset [Global Financial Crisis ▾]  Type [Historical replay]                 │
│ Period [start] [end]  [Run]                                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│ ASSET COVERAGE / PROXY                                                       │
│ Asset XYZ: [Choose proxy ▾] [Exclude]                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ RESULT — confronto % multi-asset                                             │
│ VWCE -37% · BTC -58% · GLD +6% · ...                                         │
│ quality · coverage · assumptions · effective parameters                      │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 5.6 Allocation

Nome definitivo della quarta tab:

```text
Allocation
```

Titolo interno consigliato:

```text
Composizione ipotetica
```

Descrizione obbligatoria:

> Costruisce una composizione ipotetica degli asset selezionati sulla base del
> campione, della strategia, degli stimatori e dei vincoli. Non utilizza quantità
> o pesi attualmente posseduti e non rappresenta una raccomandazione di
> ribilanciamento.

Allocation è la casa primaria e unica della UI P13 in G6.

Progressive disclosure:

```text
CONTROLLI PRINCIPALI
├── strategia
├── stimatore di covarianza
├── peso minimo
├── peso massimo
└── esecuzione

ADVANCED
├── risk-free
├── solver
├── frontier
├── sensitivity
├── vincoli avanzati
└── metadata tecnici
```

Il solver:

- non è un controllo principale;
- può essere scelto dal backend come default;
- se modificabile, vive in `Advanced`;
- viene sempre mostrato nei metadata effettivi della risposta.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ ALLOCATION — Composizione ipotetica                                          │
│ Strategy [Min risk ▾]  Covariance [Historical ▾]                             │
│ Min weight [0%]  Max weight [100%]                             [Run]          │
│ ▸ Advanced                                                                  │
├──────────────────────────────────────┬───────────────────────────────────────┤
│ KPI STIMATI                         │ PESI / RISK CONTRIBUTION              │
│ expected return                     │ Asset       Weight       PCTR         │
│ annual volatility                   │ VWCE         42%          31%         │
│ Sharpe                              │ GLD          18%          -2%         │
├──────────────────────────────────────┴───────────────────────────────────────┤
│ ADVANCED OUTPUT                                                              │
│ [tabella frontier] + [scatter frontier]                                      │
│ sensitivity · constraints · solver/status · method · metadata                │
└──────────────────────────────────────────────────────────────────────────────┘
```

P13 non viene mostrato integralmente in Dashboard o Broker.

---

## 6. Dashboard e Broker Detail

## 6.1 Stesso componente, scope differente

Dashboard:

```json
{
  "kind": "portfolio",
  "broker_ids": [1, 4]
}
```

oppure, per tutti i broker:

```json
{
  "kind": "portfolio"
}
```

Broker Detail:

```json
{
  "kind": "portfolio",
  "broker_ids": [3]
}
```

Non esistono due pannelli quasi identici.

Esiste un componente condiviso configurato con:

- scope;
- scope label;
- date;
- currency;
- asset labels;
- refresh/sync callback.

## 6.2 IA condivisa

Non introdurre sub-tab dentro la tab Risk.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ RISK SUMMARY                                                                 │
│ [Volatilità] [Max Drawdown] [Sharpe] [VaR]                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│ ▾ RISCHIO OSSERVATO                                                         │
│   KPI · drawdown · VaR/CVaR                                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│ ▾/▸ STRUTTURA DEL RISCHIO                                                   │
│   PCTR · peso economico · correlation                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ ▸ CONFRONTO                                                                 │
│   risk-free · asset reale                                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│ ▸ SCENARI                                                                   │
│   hypothetical shock · historical replay · MC/QMC                            │
└──────────────────────────────────────────────────────────────────────────────┘
```

Comportamento iniziale:

| Blocco | Desktop | Mobile |
|---|---|---|
| summary | sempre visibile | sempre visibile |
| Rischio osservato | aperto | aperto |
| Struttura del rischio | aperto | chiuso |
| Confronto | chiuso | chiuso |
| Scenari | chiuso | chiuso |

Regole:

- query avviate lazy alla prima apertura del pannello;
- chiudere il pannello non cancella query in corso, risultato, errore o cache;
- riaprire nello stesso mount con la stessa request identity riusa lo stesso stato:
  nessuna nuova request;
- risultato mantenuto finché la pagina resta montata;
- stato pannelli locale alla pagina;
- nessun URL nella prima implementazione;
- nessun `localStorage` nella prima implementazione.

### 6.2.1 Stato UI, request identity e invalidazione

Stato UI e stato dati sono distinti:

```text
stato UI
-> aperto/chiuso
-> decide quando una query lazy può partire

stato dati
-> request identity canonica
-> loading/result/error/cache
-> decide se un risultato è ancora valido
```

La request identity comprende tutti gli input finanziariamente rilevanti per il
pannello:

- scope canonicalizzato;
- `broker_ids` / asset IDs;
- date;
- currency;
- analytic e parametri;
- scenario/configurazione effettiva;
- proxy ed esclusioni;
- comparison asset;
- seed/Sobol index quando applicabili.

Scenario A — open → close → reopen, stesso mount e stessa identity:

```text
prima apertura
-> una query

chiusura
-> nessuna invalidazione
-> query in-flight continua

riapertura
-> riusa in-flight/result/error
-> nessun refetch automatico
```

Un errore same-key resta visibile; retry è esplicito, non causato dal toggle.

Scenario B — cambia date/scope/currency/parametri:

- il vecchio risultato non è più corrente per la nuova identity;
- se il pannello è aperto, parte la query per la nuova identity;
- se è chiuso, la query resta lazy e parte alla riapertura;
- la risposta della vecchia identity non può sostituire quella nuova;
- il vecchio risultato può restare nel `riskStore` sotto la vecchia key e venire
  riusato se l'utente torna esattamente agli input precedenti.

Invalidazione dati con identity invariata:

- sync prezzi/FX completato;
- mutazione dei dati sorgente;
- refresh esplicito;
- policy di session/cache del `riskStore`.

Questi eventi invalidano la validità dati, non aprono/chiudono pannelli. Un
pannello aperto ricarica; uno chiuso aspetta la prossima apertura.

Lifecycle:

- stesso mount + stessa identity → retention garantita;
- unmount → stato locale/pannelli eliminato;
- remount → il `riskStore` può servire una cache ancora valida o rifare la query;
  il riuso cross-mount è ottimizzazione di sessione, non garanzia della pagina;
- `riskStore` possiede key canoniche, cache e deduplica in-flight;
- il componente possiede solo stato UI e riferimento allo stato dati corrente.

## 6.3 Dashboard

Il filtro broker della toolbar governa **tutti** i pannelli:

- summary;
- rischio osservato;
- PCTR;
- peso economico;
- correlation;
- confronto;
- hypothetical;
- replay;
- simulation.

La Home Risk card:

- resta prevista dopo la tab Risk;
- usa metriche esplicite;
- non crea un risk score;
- rispetta lo stesso `broker_ids`;
- apre la tab Risk;
- non avvia scenari o simulation.

## 6.4 Broker Detail

Mostra sempre:

```text
Rischio interno a: {broker}
```

La label chiarisce che:

- lo scope è un sottoinsieme;
- esposizioni in altri broker non sono considerate;
- il risultato non è il rischio totale dell'investitore.

## 6.5 Allocation esclusa

Dashboard e Broker non mostrano il pannello Allocation completo.

Motivo:

- P13 non usa pesi o quantità correnti;
- non calcola delta;
- non è holdings-aware;
- la sua presenza in uno scope patrimoniale suggerirebbe una semantica di
  ribilanciamento che il contratto non possiede.

---

## 7. Scope portfolio unificato

Target:

```text
kind = portfolio
broker_ids = null | [id, ...]
```

Semantica:

- `broker_ids` omesso: tutti i broker accessibili;
- lista presente: esattamente quel sottoinsieme;
- Broker Detail: cardinalità uno;
- lista non vuota;
- lista univoca;
- lista canonicalizzata;
- broker non accessibile: errore esplicito;
- nessun filtraggio silenzioso.

Questa modifica riapre il contratto di scope, non la matematica G0-G5.

## 7.1 Ordine obbligatorio nella shared foundation

```text
1. aggiungere portfolio.broker_ids
2. aggiornare validazione e access control
3. aggiornare cache identity e metadata
4. migrare Broker Detail
5. migrare Dashboard
6. verificare equivalenza dello scope singolo
7. eliminare kind=broker
8. rigenerare OpenAPI e client
9. solo dopo intervenire sulle singole pagine
```

Nessuna alias frontend permanente.

---

## 8. Catalogo scenari YAML

## 8.1 Contratto generale

Il catalogo iniziale è:

- statico;
- tipizzato;
- versionato;
- caricato all'avvio;
- estendibile dall'host aggiungendo YAML.

Non implementare in G6:

- CRUD;
- salvataggio scenari utente;
- database;
- editor del catalogo;
- hot reload;
- reload automatico;
- form engine arbitrario;
- override built-in silenziosi.

Lo YAML rappresenta:

- definizione scenario;
- valori iniziali del form;
- parametri configurabili;
- limiti;
- descrizioni localizzate;
- policy iniziali;
- tag opzionali di catalogazione.

Il frontend usa editor noti:

```text
HistoricalReplayEditor
HypotheticalShockEditor
```

Lo YAML non sceglie componenti Svelte, layout o logica arbitraria.

## 8.2 Struttura logica

```text
scenario_catalog/
├── historical/
│   ├── global_financial_crisis.yml
│   ├── covid_crash_2020.yml
│   └── inflation_rates_2022.yml
│
└── hypothetical/
    ├── global_risk_off.yml
    ├── equity_crash.yml
    ├── banking_crisis.yml
    └── european_union_shock.yml
```

La directory built-in finale viene definita nella shared foundation come risorsa
backend package-owned.

Directory host pianificata:

```text
<get_data_dir()>/scenario_catalog/
```

Quindi:

- produzione: sotto `LIBREFOLIO_DATA_DIR` o `backend/data/prod/`;
- test: sotto `backend/data/test/`;
- stessa separazione dati già usata da LibreFolio;
- frontend non accede al filesystem.

## 8.3 Discovery e validazione all'avvio

```text
startup
  -> carica built-in
  -> carica host opzionale
  -> valida Pydantic
  -> verifica schema_version
  -> verifica ID univoci
  -> costruisce catalogo tipizzato
  -> pubblica catalogo tramite API
```

Policy built-in:

```text
YAML invalido
-> errore startup/test
-> bug applicativo
```

Policy host:

```text
YAML invalido
-> file rifiutato
-> log esplicito
-> warning pubblicabile via catalog status
-> applicazione disponibile
```

ID host duplicato:

```text
file host rifiutato
-> nessun override silenzioso
```

Nella prima implementazione:

- caricamento solo all'avvio;
- modifica file richiede restart;
- nessun watcher.

## 8.4 Forma concettuale YAML

Esempio non esecutivo:

```yaml
schema_version: 1
id: covid_crash_2020
kind: historical_replay

tags:
  - equity
  - crisis
  - global

name:
  it: Crollo COVID-19
  en: COVID-19 crash
  fr: Krach du COVID-19
  es: Caída por COVID-19

description:
  it: Fase acuta del drawdown globale durante la prima ondata della pandemia.
  en: Acute phase of the global drawdown during the first pandemic wave.
  fr: Phase aiguë du repli mondial pendant la première vague de la pandémie.
  es: Fase aguda de la caída global durante la primera ola de la pandemia.

defaults:
  start: 2020-02-19
  end: 2020-03-23
```

Campi effettivi e schemi Pydantic vengono definiti nella foundation, non da un form
renderer generico.

## 8.5 Tag opzionali

`tags` è metadata di discovery, non semantica finanziaria.

Regole:

- campo opzionale; assente = insieme vuoto;
- lista di slug machine-readable, lowercase ASCII;
- valori univoci nello stesso scenario;
- ordine privo di significato;
- numero/lunghezza limitati dallo schema Pydantic;
- vocabolario aperto: host può introdurre tag non conosciuti;
- tag sconosciuti vengono conservati, non rifiutati per assenza da un enum centrale.

Esempi:

```yaml
tags: [equity, crisis, global]
```

```yaml
tags: [europe, banking]
```

I tag:

- non sono testo localizzato;
- non sono mostrati come copy utente in G6;
- non modificano dimensione, shock, date, formule o cache identity del calcolo;
- non trasformano `europe` nel gruppo geografico `european_union`;
- possono essere trasportati come metadata inerte dal catalogo typed;
- non introducono in G6 filtri API, ricerca, raggruppamento o UI avanzata.

Includerli nello schema iniziale evita una futura migrazione del formato pur
mantenendo piena compatibilità con YAML senza `tags`.

---

## 9. Localizzazione negli YAML

Nomi e descrizioni scenari vivono nei file YAML.

Non usano il sistema i18n generale.

Catalogo built-in:

- tutte le lingue ufficiali obbligatorie;
- oggi: `en`, `it`, `fr`, `es`;
- lingua mancante: validazione built-in fallisce.

Catalogo host:

- almeno una lingua;
- fallback deterministico:

```text
lingua richiesta
-> inglese
-> italiano
-> prima lingua disponibile
```

La risposta API espone contenuti localizzati o il map tipizzato secondo il
contratto scelto nella foundation; il frontend non apre né interpreta YAML.

---

## 10. Historical replay

## 10.1 Semantica

Historical replay usa i rendimenti realmente osservati per ciascun asset nel
periodo effettivo selezionato.

Non usa:

- shock per settore;
- shock per geografia;
- shock per asset class;
- percentuali hardcoded.

```text
asset selezionati
-> prezzi storici nel periodo
-> FX storico verso target currency
-> rendimenti osservati
-> applicazione alla composizione scelta
```

Per portfolio e broker:

```text
composition_policy = current_buy_and_hold
```

Wording obbligatorio:

> Composizione corrente applicata al periodo storico selezionato; non rappresenta
> il portafoglio realmente posseduto in quel periodo.

## 10.2 Proxy manuali

Se un asset non ha storia sufficiente:

- selezione manuale di un asset proxy;
- oppure esclusione dal replay.

Mai:

- proxy automatici;
- deduzioni da settore;
- deduzioni dal nome;
- sostituzioni silenziose.

Il proxy fornisce solo i rendimenti storici.

Restano dell'asset originale:

- identità;
- peso;
- valore attuale;
- posizione nel risultato.

Il risultato espone:

```text
Asset originale
Serie storica fornita dal proxy selezionato
```

Vincoli proxy:

- diverso dall'asset originale;
- copertura sufficiente;
- convertibile nella target currency;
- requisiti qualità soddisfatti;
- selezionato con il selector asset condiviso.

La scelta:

- vive nello stato pagina/form;
- entra nella request effettiva;
- partecipa alla request/cache identity;
- non viene salvata permanentemente in G6.

Per portfolio/broker, il peso di un asset escluso non viene redistribuito:
diventa residuo a rendimento zero. La policy preserva NAV e pesi originali,
evita di inventare una nuova composizione e deve comparire nell'audit.

## 10.3 Audit trail proxy/esclusioni

Historical replay espone sempre un audit trail strutturato, anche quando vuoto.

Informazioni minime:

- numero proxy usati;
- mapping canonico `asset originale -> asset proxy`;
- numero asset esclusi;
- asset esclusi e motivo/policy di esclusione;
- policy effettiva per asset senza storia;
- `composition_policy` effettiva;
- periodo e target currency, già parte dei metadata generali;
- conferma che il proxy fornisce solo i rendimenti.

Requisiti:

- mapping ordinato deterministicamente per asset originale;
- liste vuote e contatori zero quando nessun proxy/esclusione è presente;
- proxy invalido produce errore esplicito, non esclusione silenziosa;
- risultato per-asset continua a usare ID/identità dell'asset originale;
- qualità/copertura del proxy resta nel `DataQualityReport`, correlata tramite ID,
  senza duplicare la qualità sorgente in `RiskResultMetadata`.

Placement:

```text
request
-> contiene mapping proxy + esclusioni scelti dall'utente

response / RiskResultMetadata
-> contiene summary count + mapping + esclusioni + policy effettive

UI result summary
-> "2 proxy usati · 1 asset escluso"

UI detail/per-asset
-> asset originale · proxy selezionato · esclusione/motivo · quality/coverage
```

L'audit non può vivere solo nei log o nello stato frontend: deve essere parte
della risposta typed e serializzabile.

## 10.4 Preset iniziali

Pianificare:

- Global Financial Crisis;
- COVID-19 crash;
- Inflation and rate shock 2022;
- Custom period.

Le date:

- sono proposte iniziali;
- restano visibili;
- sono modificabili;
- non definiscono universalmente l'evento.

---

## 11. Hypothetical shock

## 11.1 Una dimensione per esecuzione

Dimensioni ammesse:

```text
asset_class
oppure
sector
oppure
geography
```

Non supportare intersezioni:

```text
Equity AND Financials AND Italy
```

## 11.2 Metadata canonici

```text
asset_class
-> singolo valore

sector
-> distribuzione percentuale con Other

geography
-> distribuzione percentuale con Other
```

Il Risk Engine consuma il valore canonico, non la provenienza del provider.

## 11.3 Applicazione shock

Asset class:

```text
shock_asset = shock(asset_class)
```

Sector:

```text
shock_asset = Σ(percentuale_settore × shock_settore)
```

Geography:

```text
shock_asset = Σ(percentuale_geografia × shock_geografia_effettivo)
```

Il calcolo vive nel backend.

Il frontend mostra:

- esposizioni usate;
- shock per bucket;
- shock risultante per asset;
- warning;
- fallback;
- regola applicata.

## 11.4 UX editor bucket

Decisione:

```text
default -> bucket presenti nello scope
toggle  -> Mostra tutti
```

È l'opzione C: mantiene editor corto senza nascondere il catalogo completo.

Bucket visibili di default:

- esposizione aggregata > 0 nello scope corrente;
- `Other` sempre visibile per `sector` e `geography`, anche a 0%;
- bucket modificati manualmente nel form corrente, anche se diventano 0%.

`Mostra tutti` espone tutti i bucket canonici ammessi da scenario/dimensione. Non
crea bucket arbitrari.

Regole UX:

- bucket presenti ordinati per esposizione decrescente;
- `Other` separato/fisso;
- bucket senza esposizione marcati `0% nello scope`;
- toggle locale, senza URL/localStorage;
- cambio scope ricalcola la presenza ma non perde valori manuali ancora validi.

Auditabilità:

- mostrare/nascondere non cambia configurazione o formula;
- request e metadata contengono tutti gli shock effettivamente configurati;
- response per-asset mostra solo esposizioni/regole realmente applicate;
- eventuali bucket configurati ma senza esposizione hanno impatto zero esplicito.

Alternative:

- tutti sempre visibili → auditabile ma non scalabile, soprattutto geografia;
- solo presenti → semplice ma impedisce esplorazione/preconfigurazione;
- presenti + toggle → miglior equilibrio fra usabilità, scala e trasparenza.

---

## 12. Metadata mancanti, Other e European Union

## 12.1 Metadata settore/geografia mancanti

Policy:

```text
Other = 100%
```

Non:

- inferire dal nome;
- escludere asset;
- produrre automaticamente `partial`;
- inventare categorie;
- creare `Unclassified`.

Lo scenario applica:

```text
shock_asset = 100% × shock_Other
```

Warning metodologico:

> Per questo asset non erano disponibili dati di settore/geografia. È stato
> trattato come Other al 100%.

Il risultato resta tecnicamente completato secondo la policy.

`Other` è obbligatorio in ogni scenario sector/geography.

## 12.2 Aggregato European Union

ID tecnico:

```text
european_union
```

Label:

```text
Unione Europea / European Union
```

Non:

```text
Europe
```

Il gruppo contiene gli Stati membri definiti in un catalogo geografico versionato.

Precedenza:

```text
Paese specifico
> gruppo European Union
> Other
```

Esempio:

```text
European Union -20%
Italy          -30%
Other            0%
```

Risultato:

- Italia: `-30%`;
- altri Stati UE: `-20%`;
- geografie non coperte: `Other`;
- shock non sommati.

Per settore:

- nessuna intersezione;
- nessun gruppo sovrapposto nella prima implementazione.

Per asset class:

- un solo valore.

Il backend produce una spiegazione auditabile per bucket e asset.

---

## 13. Parametri modificabili dalla UI

I valori YAML sono valori iniziali.

Historical replay:

- data iniziale;
- data finale;
- policy asset senza storia;
- proxy per asset;
- esclusioni.

Hypothetical shock:

- dimensione, quando il preset la consente;
- shock per bucket;
- shock `Other`;
- override manuali previsti dallo schema;
- parametri dichiarati dal preset.

La request contiene la configurazione effettiva modificata.

La risposta/metadata riporta i valori realmente usati.

Non implementare:

- Save scenario;
- Save as new preset;
- Update YAML.

---

## 14. Simulation UI

Due viste dello stesso output:

```text
[ Evoluzione ] [ Distribuzione finale ]
```

Questo è un view switch interno al pannello Simulation, non una sub-tab della
pagina Risk.

Evoluzione:

- P5/P50/P95 nel tempo;
- distinzione storico/simulato;
- MC/QMC;
- `random_seed` oppure `sobol_start_index`;
- label “simulato”.

Distribuzione finale:

- distribuzione terminale valore o rendimento;
- P5/P50/P95 terminali;
- probability of loss;
- soglia-obiettivo solo se già supportata dal contratto backend.

Nessun calcolo finanziario nel frontend.

---

## 15. Componenti condivisi

Target concettuale:

```text
Risk workspace/query state
├── RiskSummary
├── ObservedRiskPanel
├── RiskStructurePanel
├── ComparisonPanel
├── ScenariosPanel
│   ├── HistoricalReplayEditor
│   ├── HypotheticalShockEditor
│   └── SimulationViews
├── CorrelationViews
├── AllocationPanel
├── QualityAndSync
└── MetadataRenderer
```

Asset Detail compone:

```text
RiskSummary
+ rolling SignalPlugin adapter
+ Comparison
+ asset-centric Correlation
+ Scenarios
```

Assets Global compone:

```text
CorrelationViews
+ Scenarios
+ Allocation
```

Dashboard/Broker compongono lo stesso:

```text
RiskSummary
+ ObservedRiskPanel
+ RiskStructurePanel
+ ComparisonPanel
+ ScenariosPanel
```

Allocation non entra nel componente Dashboard/Broker.

---

## 16. Ordine di pianificazione ed esecuzione futura

```text
IA approvata
    -> scope portfolio + broker_ids
    -> scenario catalog contract/loader/API
    -> historical replay
    -> hypothetical shock
    -> backend validation + API sync
    -> shared typed query/state foundation
    -> Asset Detail
        -> STOP validazione visuale
    -> Assets Global / Correlation
        -> STOP validazione visuale
    -> Assets Global / Scenarios
        -> STOP validazione visuale
    -> Assets Global / Allocation
        -> STOP validazione visuale
    -> Broker Detail / Risk
        -> STOP validazione visuale
    -> Dashboard / Risk
        -> STOP validazione visuale
    -> Home Risk card
        -> STOP validazione visuale
    -> integrated validation
```

Ogni passaggio ha un solo predecessore. Nessuna vista successiva può essere
iniziata prima del via libera visuale esplicito sulla vista corrente.

---

## 17. Test strategy futura

Backend:

- scope broker-set;
- scenario schema/catalog discovery;
- built-in vs host validation;
- localizzazione/fallback;
- unique IDs;
- restart-only loading;
- historical replay;
- proxy validation;
- proxy/exclusion counts, mapping, policy e metadata;
- empty audit trail;
- proxy mapping nella request identity;
- hypothetical dimension validation;
- tag opzionali/slug/duplicati/vocabolario aperto;
- weighted sector/geography shock;
- `Other=100%`;
- `european_union` membership;
- precedence country > EU > Other;
- audit explanation;
- effective request metadata.

Frontend logico/funzionale:

- quattro tab Assets;
- shared asset universe;
- correlation view switch/manual override;
- default responsive non vincolante;
- Scenarios tab separata;
- Allocation progressive disclosure;
- solver in Advanced;
- effective solver metadata;
- Dashboard/Broker shared component;
- accordion defaults desktop/mobile;
- lazy first-open;
- close/reopen same-key senza refetch;
- input change → nuova identity e stale-result isolation;
- sync/mutation invalidation separata dallo stato accordion;
- result retention while mounted e cache cross-mount non garantita;
- bucket presenti + `Mostra tutti`;
- `Other` sempre visibile;
- no URL/localStorage panel state;
- Asset Detail no duplicate Signals configurator;
- simulation evolution/distribution views.

Escluso:

- snapshot;
- pixel assertions;
- test estetici automatici;
- selector basati su testo localizzato/classi.

---

## 18. TODO futuri

Catalogo scenari dinamico:

- rilevamento senza restart;
- reload manuale;
- hot reload;
- CRUD scenari personali;
- salvataggio modifiche UI;
- import/export YAML;
- override built-in espliciti;
- diagnostica amministrativa.

Proxy replay:

- associazioni persistenti asset → proxy;
- proposta proxy solo esplicita e confermata;
- riuso associazioni in replay successivi.

RQMC:

- resta backlog a priorità bassa;
- contratto scrambling separato da `sobol_start_index`.

---

## 19. Gate documentale

Prima di implementare:

- IA approvata esplicitamente;
- Step 6 e master allineati;
- contract stress allineato;
- placement matrix allineata;
- work item ancora bloccati;
- backlog aggiornato;
- nessuna formulazione stale nelle fonti attive.

Fino ad allora:

```text
STOP — documentazione in revisione
```
