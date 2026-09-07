# Report Phase 0 — AI Export Public Catalog Reduction V1

**Data**: 4 agosto 2026  
**Run autorevole**: `real_prompt_probe/20260804T155305.988711Z`  
**Baseline principale**: `real_prompt_probe/20260801T035128.653789Z`  
**Contratto**: snapshot wire V2 · catalogo/selezioni pubbliche V3  
**Ambito**: riduzione catalogo, composizione autonoma, contratti Analysis, probe,
review e documentazione AI Export

## 1. Executive summary

Il catalogo pubblico AI Export passa da **32 Dataset + 16 Analysis** a:

- **8 Export Data autonomi**;
- **13 Analysis task-oriented**.

Il backend conserva **67 componenti, 40 Dataset e 24 Analysis** nel registry
interno. La nuova visibility è fail-closed:

- `public`: visibile nel catalogo e selezionabile direttamente;
- `internal`: componibile da una Analysis, ma assente dal catalogo e rifiutata se
  richiesta direttamente.

Il run finale ha prodotto **126/126 prompt**, senza failure o skip. Il secret scan
è passato, il database production è rimasto invariato e rendering UI/probe
coincidono.

La riduzione non è un semplice hide frontend: API, versioning, memoria locale,
contratti, rendering, test e probe sono stati migrati insieme.

## 2. Catalogo pubblico finale

### 2.1 Export Data

| Dominio | ID | Scopo |
|---|---|---|
| Portfolio | `portfolio.overview_and_history` | Stato economico, performance path, costi, FIFO sintetico, Drawdown e contesto Asset compatto |
| Portfolio | `portfolio.asset_history` | Prezzi close osservati, indicatori, stati, eventi, coverage e breadth per Asset |
| Broker | `broker.overview_and_history` | Fotografia autonoma del Broker con concentrazione, cost efficiency e FIFO sintetico |
| Broker | `broker.asset_history` | Storico tecnico Broker-scoped con prezzi close osservati |
| Asset | `asset.position_and_history` | Posizione, costo/valore/P&L, lotti economici, storia compatta e Drawdown |
| Asset | `asset.market_history` | Storico close, rendimenti, indicatori, eventi e Drawdown |
| FX | `fx.market_and_exposure` | Tasso, storia compatta, timing, coverage ed esposizione diretta |
| FX | `fx.market_history` | Storico tasso, rendimenti, indicatori ed eventi |

### 2.2 Analysis

| Dominio | ID | Compito |
|---|---|---|
| Portfolio | `portfolio.pac_planning` | Scenari PAC condizionali |
| Portfolio | `portfolio.rebalancing` | Percorsi di ribilanciamento |
| Portfolio | `portfolio.performance_market_drivers` | Performance + cause di mercato datate |
| Portfolio | `portfolio.fiscal_lots` | Lotti economici + scenari fiscali condizionali |
| Broker | `broker.review` | Revisione completa del Broker |
| Broker | `broker.performance_market_drivers` | Performance Broker + driver datati |
| Broker | `broker.cost_efficiency` | Costi, denominatori e ratio validi |
| Broker | `broker.fiscal_lots` | Lotti Broker + scenari fiscali |
| Asset | `asset.position_review` | Revisione della posizione |
| Asset | `asset.market_analysis` | Analisi di mercato dell'Asset |
| FX | `fx.pair_analysis` | Analisi della coppia |
| FX | `fx.conversion_planning` | Conversione immediata, graduale o condizionata |
| FX | `fx.exposure_impact` | Impatto dei collegamenti FX diretti |

## 3. Architettura public/internal

`DatasetSpec` e `AnalysisSpec` hanno `CatalogVisibility`, con default
`INTERNAL`.

Il boundary è applicato in tre punti:

1. il registry conserva tutte le identità;
2. `GET /ai-export/catalog` serializza soltanto gli spec pubblici;
3. `POST /ai-export/snapshot` rifiuta un ID interno come
   `unsupported_selection`.

Una Analysis pubblica può continuare a usare un Dataset interno, per esempio il
FIFO completo delle Analysis fiscali. Questo evita di riaprire il catalogo
pubblico.

## 4. Nuovi mattoncini e semantica

### 4.1 Mini-history uniforme

| Serie | Compact | Standard | Full |
|---|---:|---:|---:|
| Portfolio/Broker complessivo | 8 | 16 | 30 |
| Asset dentro Portfolio/Broker | 6 | 12 | 24 |
| Asset singolo | 8 | 16 | 30 |
| FX | 8 | 16 | 30 |

Regole:

- bucket calendariali uniformi sulla finestra osservata;
- nessun forward-fill o dato inventato;
- ultimo punto reale del bucket;
- indice base 100 e ritorno dal primo punto reale;
- date, conteggio osservazioni e coverage espliciti;
- extrema per bucket omessi perché già presenti nella summary di periodo.

### 4.2 Performance path

I valori sono NAV flow-inclusive. L'indice/rendimento normalizzato usa invece
`historical_twrr`, così depositi e prelievi non vengono scambiati per rendimento.

### 4.3 Coverage tecnico

Il prompt distingue:

- Asset correnti;
- Asset tecnicamente eleggibili;
- Asset coperti da Signal;
- Asset correnti esclusi e relativo `reason_code`;
- peso scope-relative eligible/covered/excluded;
- peso rinormalizzato nel solo universo tecnico.

Nel caso Broker reale:

```text
current_position_asset_count = 10
eligible_asset_count = 9
eligible_current_scope_weight = 97,6996%
excluded_current_scope_weight = 2,3004%
excluded Asset reason = end_value_unavailable
```

### 4.4 Concentrazione

La semantica ora dichiara:

- type/sector/geography: slice engine, con eventuale Liquidity;
- currency: market value delle posizioni, cash separato;
- HHI/largest: `nav_weight_percent`, quindi cash incluso nel denominatore NAV ma
  non come termine HHI.

### 4.5 FIFO economico

La sintesi per Asset espone quantità, costi, valore, realized/unrealized/total
P&L, redditi, fee, imposte, custody/stati e coverage.

Il prompt dichiara che fee e tasse di lotto sono soltanto quelle allocate.
Costi Broker non allocati restano nei componenti costi e non sono convertiti in
zero di lotto.

### 4.6 Prezzi e Signal

I Dataset dettagliati dichiarano:

- `price_basis = observed_close`;
- P/M/K invariati;
- `result_status` e `partial_reason_code` locali per ogni entity-instance non OK;
- status OK omessi dalla tabella locale per evitare ripetizioni.

## 5. Contratti Analysis

### 5.1 Scenario Thesis

Obbligatoria per:

- PAC;
- rebalancing;
- fiscal lots Portfolio/Broker;
- conversion planning.

Ogni scenario richiede evidenza, assunzioni, orizzonte, meccanismo, trade-off,
trigger, invalidazione e decisioni utente mancanti.

### 5.2 PAC

Il prompt:

- usa prima i dati disponibili;
- separa input indispensabili e rifiniture;
- non inventa budget, target o rischio;
- confronta ingresso immediato e graduale;
- aggiunge attesa condizionata solo con discesa ampia e persistente;
- chiede la preferenza temporale dell'utente.

### 5.3 Performance e market drivers

Per ogni Asset detenuto richiede:

- inventario del movimento;
- fonti datate e qualità;
- tesi breve e lunga;
- issuer/sector/macro separati;
- `supported`, `plausible`, `inferred`, `speculative`, `unexplained`;
- correlazione/cronologia distinte dalla causalità.

### 5.4 Fiscal lots

Il contratto separa:

- FIFO economico LibreFolio;
- trattamento fiscale legale;
- giurisdizione, regime, account, minus, scadenze e vincoli.

Non produce aliquote o imponibili inventati.

### 5.5 FX conversion

I ritorni timing sono nominati `30d` e `91d`, non “1m/3m”. Gli input mancanti sono
separati:

- indispensabili: importo, direzione, scadenza;
- rifiniture: urgenza, provider, spread, fee, minimo, settlement, slippage,
  liquidità e fattibilità del frazionamento.

## 6. Frontend e memoria

- catalogo config V3 esatto 8+13;
- schema wire frontend ancora V2;
- selection/catalog/memory version V3;
- migrazione one-shot memoria V2→V3;
- periodo, dettaglio e note preservati;
- UI EN/IT/FR/ES aggiornata con `./dev.py i18n`;
- audit: **2335/2335 chiavi complete**, 0 chiavi backend mancanti;
- OpenAPI e client Zodios sincronizzati.

## 7. Misure finali

### 7.1 Distribuzione

| Coorte | Count | Min | Median | P90 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|
| Tutti i prompt | 126 | 3.146 | 12.305 | 44.025 | 86.560 | 399.310 |
| Export Data | 48 | 3.146 | 11.939 | 111.694 | 174.121 | 399.310 |
| Analysis | 78 | 4.668 | 12.576 | 17.167 | 19.998 | 44.025 |

Valori in token-equivalenti stimati (`chars/4`).

### 7.2 Range per selezione

| Selection | Min | Mediana alta | Max | Technical share media |
|---|---:|---:|---:|---:|
| Portfolio general | 10.149 | 12.353 | 15.349 | 42,76% |
| Portfolio detailed | 55.129 | 111.694 | 399.310 | 98,82% |
| PAC | 11.968 | 14.172 | 17.167 | 37,31% |
| Portfolio fiscal | 14.799 | 17.003 | 19.998 | 31,15% |
| Broker general | 8.755 | 10.207 | 12.776 | 37,35% |
| Broker detailed | 45.451 | 91.080 | 324.707 | 98,80% |
| Broker cost | 10.026 | 11.478 | 14.047 | 33,33% |
| Asset general | 3.146 | 3.380 | 3.612 | 35,71% |
| Asset market | 10.794 | 16.222 | 42.658 | 91,59% |
| FX general | 3.465 | 3.694 | 3.927 | 31,81% |
| FX market | 7.504 | 12.019 | 28.835 | 93,28% |

I soli 11 prompt Heavy sono i due Export Data tecnici Portfolio/Broker. Nessuna
Analysis supera 50k token-equivalenti.

## 8. Confronto V2 → V3

Confronto completo:

- `public_catalog_v3_comparison.json`;
- `public_catalog_v3_comparison.md`.

Esempi:

| V3 | Baseline logica | Delta mediano |
|---|---:|---:|
| Portfolio general | 17.289 | **-31,24%** |
| Portfolio detailed | 258.328 | **-59,67%** |
| Broker general | 15.204 | **-33,97%** |
| Broker detailed | 225.810 | **-62,00%** |
| Asset general | 4.151 | **-19,76%** |
| FX general | 4.570 | **-20,44%** |
| Portfolio performance/market drivers | 22.625 | **-40,35%** |
| FX conversion planning | 22.758 | **-76,84%** |

Le somme baseline sono combinazioni diagnostiche di prompt separati, mai una
singola richiesta AI.

Gli aumenti su PAC, fiscal lots, Cost Efficiency e Position Review derivano da
evidenza deterministica e contratti aggiunti, non da duplicazione accidentale.

## 9. Probe e sicurezza

Run autorevole:

```text
20260804T155305.988711Z
```

Esito:

- 126/126 measured;
- 38 prompt retained;
- 0 failure;
- 0 skip;
- 0 public-output violation;
- renderer equivalence 100%;
- secret scan passed;
- nomi artefatti anonimizzati;
- production DB invariato.

Artefatti principali:

- `metrics.json`;
- `run_manifest.json`;
- `retained_prompt_manifest.json`;
- `task_adequacy_reviews.json`;
- `export_data_reviews.json`;
- `task_adequacy_tables.md`;
- `public_catalog_v3_comparison.{json,md}`;
- `charts/*.svg`.

## 10. Test

- backend AI Export service suite;
- 201 frontend AI Export/Signal unit;
- frontend type-check 0 error/0 warning;
- 34 Playwright AI Export desktop/mobile;
- 56 probe utility test;
- API/schema/catalog/runtime/component test mirati;
- Ruff, Black e Prettier sui file modificati.

## 11. Problemi aperti

1. I Full detailed Portfolio/Broker restano molto grandi per scelta: conservano
   tutti i Signal, tutti gli Asset eleggibili e ogni bucket non vuoto.
2. Compact/Standard sono i default consigliati; Full è un opt-in tecnico.
3. Le traduzioni MkDocs delle pagine aggiornate restano da rigenerare; le sorgenti
   inglesi sono state ricontrollate dopo l'interruzione della pipeline.

## 12. Decisione finale

**APPROVARE Public Catalog V3.**

Il catalogo è centralizzato, autonomo, più piccolo, backend-owned e pronto per la
review utente. Nessun commit o release è stato eseguito.
