# Report Phase 0 — AI Export Task Adequacy Review V2

**Data**: 4 agosto 2026  
**Run autorevole**: `real_prompt_probe/20260804T155305.988711Z`  
**Varianti**: 126 = 48 Export Data + 78 Analysis  
**Baseline storica**: `report-phase00AiExportTaskAdequacyReviewV1.md`

## 1. Executive summary

La V2 della Task Adequacy Review valuta il nuovo catalogo pubblico:

- 8 Export Data;
- 13 Analysis;
- 3M/1Y;
- Compact/Standard/Full.

Esito:

| Rating | Varianti |
|---|---:|
| OPTIMAL | **126** |
| SUFFICIENT | **0** |
| INSUFFICIENT | **0** |

Il rating misura adeguatezza informativa, non preferenza di default. I Full
tecnici possono essere OPTIMAL e contemporaneamente non essere il detail
consigliato per l'uso ordinario.

## 2. Rubrica

| Asse | Punti |
|---|---:|
| Deterministic completeness | 25 |
| Task relevance | 25 |
| Semantic clarity | 15 |
| Coverage and limits | 15 |
| Density/information | 10 |
| Additional Data usability | 10 |

Bande:

- OPTIMAL: 85–100;
- SUFFICIENT: 60–84;
- INSUFFICIENT: 0–59.

Input disponibili soltanto dall'utente e dati realmente non disponibili non
riducano automaticamente la completezza quando il prompt:

- identifica il gap;
- distingue indispensabile/opzionale;
- supporta scenari condizionali;
- non inventa valori;
- distingue zero, unavailable e not applicable.

## 3. Metodo

1. rendering ufficiale frontend;
2. snapshot autenticato su copia DB;
3. 126 metriche persistite;
4. 38 prompt retained letti qualitativamente;
5. min/median/P10/P25/P75/P90/P95/P99 inclusi;
6. review per dominio;
7. correzioni mirate;
8. nuovo full run soltanto quando una modifica condivisa toccava tutto il catalogo.

La tabella completa è:

```text
real_prompt_probe/20260804T155305.988711Z/task_adequacy_tables.md
```

I JSON strutturati sono:

- `task_adequacy_reviews.json`;
- `export_data_reviews.json`.

## 4. Rating per selezione

### 4.1 Export Data

| Selection | Score min–max | Rating | Decisione |
|---|---:|---|---|
| `portfolio.overview_and_history` | 97–99 | OPTIMAL | Keep |
| `portfolio.asset_history` | 86–96 | OPTIMAL | Keep; Full solo opt-in |
| `broker.overview_and_history` | 95–98 | OPTIMAL | Keep |
| `broker.asset_history` | 86–91 | OPTIMAL | Keep; Full solo opt-in |
| `asset.position_and_history` | 97–99 | OPTIMAL | Keep |
| `asset.market_history` | 96–98 | OPTIMAL | Keep |
| `fx.market_and_exposure` | 96–97 | OPTIMAL | Keep |
| `fx.market_history` | 90–95 | OPTIMAL | Keep |

### 4.2 Analysis

| Selection | Score min–max | Rating | Decisione |
|---|---:|---|---|
| `portfolio.pac_planning` | 98–100 | OPTIMAL | Keep |
| `portfolio.rebalancing` | 98–100 | OPTIMAL | Keep |
| `portfolio.performance_market_drivers` | 96–98 | OPTIMAL | Keep |
| `portfolio.fiscal_lots` | 96–98 | OPTIMAL | Keep |
| `broker.review` | 94–97 | OPTIMAL | Keep |
| `broker.performance_market_drivers` | 95–97 | OPTIMAL | Keep |
| `broker.cost_efficiency` | 90–95 | OPTIMAL | Keep |
| `broker.fiscal_lots` | 89–95 | OPTIMAL | Keep |
| `asset.position_review` | 97–99 | OPTIMAL | Keep |
| `asset.market_analysis` | 95–97 | OPTIMAL | Keep |
| `fx.pair_analysis` | 89–94 | OPTIMAL | Keep |
| `fx.conversion_planning` | 96–97 | OPTIMAL | Keep |
| `fx.exposure_impact` | 95–96 | OPTIMAL | Keep |

## 5. Portfolio

### General export

Completo e autonomo:

- posizioni e cash;
- allocazioni e basi di concentrazione;
- TWRR/MWRR/ROI;
- performance path;
- redditi/costi/reconciliation;
- FIFO economico sintetico;
- storia Asset compatta;
- Drawdown e coverage.

Il technical share Full è sotto il 50%. `technical_breadth`, ridondante nel
general, resta nel detailed export.

### Asset history

Mantiene:

- tutti gli Asset tecnicamente eleggibili;
- esclusi correnti con reason;
- observed-close basis;
- status locale non-OK;
- P/M/K e event policy.

Il caso massimo è 399.309,5 token-equivalenti. È semanticamente adeguato, ma Full
non è il default consigliato.

### PAC

Tutti i requisiti sono presenti:

- checklist condizionale;
- indispensabile vs rifinitura;
- timing gate;
- Scenario Thesis;
- Drawdown storico e anti-forecast;
- nessun budget/target/rischio inventato.

### Performance/market drivers

Richiede ogni Asset, ricerca datata, fonti, short/long thesis, causal confidence e
movimenti unexplained.

### Fiscal lots

Lotti completi, cost allocation, confine economico/legale e input fiscali utente
sono espliciti.

## 6. Broker

### Scope e coverage

Il prompt mostra:

- 10 Asset correnti;
- 9 eleggibili;
- 1 escluso con `end_value_unavailable`;
- 97,6996% eligible/covered scope weight;
- 2,3004% excluded scope weight.

### Concentrazione

HHI/largest dichiarano il denominator NAV con cash incluso nel denominatore ma
non come termine HHI. Currency allocation esclude cash e lo lascia nei campi
cash.

### Cost Efficiency

Il caso reale esporta:

- fee 103 EUR;
- tasse 1.177,94 EUR;
- total costs 1.280,94 EUR;
- average NAV 454.298,6432 EUR;
- gross turnover 30.000 EUR;
- formule, numeratori, denominatori, coverage e status.

Trading/FX/other costs restano unavailable perché la sorgente non li classifica.

### Fiscal lots

Allocated e unallocated costs non sono più confusi. Scenario fiscale e consiglio
legale restano separati.

## 7. Asset

Position Review ora riceve:

- realized P&L zero registrato;
- period fees/taxes zero registrato;
- reddito;
- lot economics;
- allocated fees/taxes;
- semantica unallocated;
- storia 8/16/30 e Drawdown.

Market History/Analysis dichiarano `price_basis=observed_close` e status Signal
parziali accanto al relativo instance.

## 8. FX

### Pair semantics

Base/quote e quote-per-base sono espliciti; nessuna inversione silenziosa.

### Conversion

`return_30d` e `return_91d` eliminano l'ambiguità con i tre mesi calendariali.
Input indispensabili e rifiniture sono separati.

### Exposure

Soltanto collegamenti diretti cash/trading/valuation; nessun look-through
inventato.

Non esiste Drawdown FX pubblico.

## 9. Additional Data

Le Analysis suggeriscono soltanto uno dei sette Export Data pubblici
complementari, con:

- label localizzata;
- motivo;
- percorso UI;
- periodo;
- detail;
- necessità.

Cost Efficiency non suggerisce dati aggiuntivi non necessari. I prompt data-only
sono autonomi e omettono correttamente la sezione.

## 10. Densità

| Classe | Count |
|---|---:|
| Light | 37 |
| Medium | 78 |
| Heavy | 11 |
| Very Heavy | 5 |

Gli 11 Heavy sono esclusivamente:

- `portfolio.asset_history`;
- `broker.asset_history`.

Nessuna Analysis è Heavy.

## 11. Correzioni emerse dalla review

1. indice performance da TWRR, non NAV flow-inclusive;
2. history general senza extrema duplicati;
3. rimozione breadth ridondante dal general;
4. current Asset esclusi + reason + scope weight;
5. concentration denominator corretto;
6. allocated/unallocated FIFO esplicito;
7. zero Asset performance espliciti;
8. lot economics Asset completi;
9. FX 30d/91d e input completi;
10. observed-close basis e status Signal locali;
11. artefatti full-run anonimizzati.

## 12. Decisione finale

**126/126 OPTIMAL.**

Il catalogo è semanticamente adeguato e pronto per la review manuale. Compact e
Standard restano i default operativi; Full detailed resta un opt-in tecnico.
