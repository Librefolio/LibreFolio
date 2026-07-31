Le misure principali di questo report riguardano i prompt finali renderizzati e copiabili dalla UI, non il JSON canonico grezzo.

# Report Phase 0 - AI Export Public Format Hardening V3

**Data**: 31 luglio 2026  
**Run precedente**: `real_prompt_probe/20260731T084208.527843Z`  
**Run autorevole corrente**: `real_prompt_probe/20260731T102457.551232Z`  
**Profilo**: `tuning-v2`  
**Utente**: `marco`  
**Stato**: correzioni, test, nuovo export, metriche e report completati; cleanup rinviato

## 1. Esito

Il formato tabellare, la composizione e la politica Compact/Standard/Full approvati
sono rimasti invariati. Non sono stati modificati:

- formule dei bucket;
- temporal class;
- matrice P/M/K;
- selezione o finestra degli eventi;
- period summary e latest;
- Signal disponibili;
- history;
- Compact;
- coupling FX;
- classificazione Risk;
- catalogo `all_data`.

Correzioni applicate:

- quote normalizzate mostrate direttamente in percentuale;
- pesi tecnici e di portafoglio nominati e riconciliabili;
- HHI corretto come punti `0..10.000`;
- rumore floating point rimosso con semantica esplicita;
- colonne vuote e parent nulli rimossi da tutte le tabelle;
- lotti FIFO distinti tramite riferimenti locali `L#`;
- custody corrente mantenuta, incluso il contratto `IN_TRANSIT`;
- prezzo unitario riconciliato;
- regola prezzo mancante unica e condizionale;
- Technical Breadth non richiede Risk Assessment inesistente.

Il nuovo corpus contiene:

| Tipo | Tentativi | Prompt prodotti | Fallimenti |
|---|---:|---:|---:|
| Export Data | 126 | 114 | 12 |
| Request Analysis | 96 | 87 | 9 |
| **Totale** | **222** | **201** | **21** |

I 21 fallimenti sono esclusivamente i casi FX 6M/1Y già noti.

## 2. Scope e riproducibilità

Sono rimasti uguali:

- utente `marco`;
- Portfolio completo;
- Broker rappresentativo: ID diagnostico 4, mai esposto nel prompt;
- Asset rappresentativo: ID diagnostico 42, mai esposto nel prompt;
- coppia FX: EUR/USD;
- criteri di applicabilità;
- matrice period/detail;
- esclusione dei quattro `*.all_data`.

Il probe usa:

```text
DB produzione copiato
  -> login/catalog/snapshot HTTP
  -> renderAiExportPrompt()
  -> file Markdown
  -> metriche e audit
```

Risultati di sicurezza:

- fotografia sorgente invariata;
- DB produzione invariato durante il run;
- copia runtime eliminata dal probe;
- secret scan: `passed`;
- 201/201 prompt UI/probe identici come stringa e byte UTF-8.

## 3. A. Correzioni di qualità semantica

### 3.1 Percentuali e pesi

Le quote ratio non richiedono più conversioni all'LLM.

Esempi pubblici:

```text
portfolio_weight_percent = 17.04%
covered_portfolio_weight_percent = 95.7516%
covered_weight_ratio_percent = 95.7516%
technical_normalized_weight_percent = 23.4%
```

Semantica dichiarata nel prompt:

```text
portfolio_weight_percent and *_portfolio_weight_percent use gross absolute
open-position market value.

technical_normalized_weight_percent sums to 100% across each signal instance's
covered technical universe.
```

Technical Breadth separa:

- `considered_asset_count`;
- `eligible_asset_count`;
- `covered_asset_count`;
- `eligible_portfolio_weight_percent`;
- `covered_portfolio_weight_percent`;
- `covered_weight_ratio_percent`;
- `portfolio_weight_percent`;
- `technical_normalized_weight_percent`.

Audit:

- 1.728 riconciliazioni di peso;
- 0 violazioni;
- pesi tecnici riconciliati per singola istanza Signal;
- nessun campo ratio pubblico residuo.

### 3.2 HHI

Il backend calcola:

```text
sum(nav_weight_percent²)
```

La scala effettiva è quindi HHI points `0..10.000`, non percentuale.

Correzione:

```text
herfindahl_index_percent
-> herfindahl_index_points
```

Valore reale nel corpus:

```text
herfindahl_index_points = 944.3481
```

Audit:

- 33 occorrenze controllate;
- 0 valori fuori scala;
- 0 doppie conversioni;
- 0 suffissi `%` applicati a HHI.

### 3.3 Numeri e rumore floating point

La normalizzazione ora raggiunge:

- period summary;
- range `f/l/n/x/c`;
- latest;
- output multi-colonna;
- valori evento;
- `left`, `right`, `difference`;
- strutture JSON dentro celle;
- residui di riconciliazione;
- importi monetari sub-minor-unit.

Semantica:

- bounds plugin-owned derivati da `SignalOutputSpec.axis`;
- epsilon bounded deterministico vicino a minimo/massimo;
- epsilon zero applicato a `difference`;
- importi di riconciliazione inferiori alla precisione valuta mostrati come `0`;
- valori piccoli non marcati semanticamente restano visibili.

Esempi verificati:

```text
100.00000000000004 -> 100
0.000000000000003183 -> 0       # output bounded
-0.00000000000005862 -> 0       # event difference
-0.000000000000000000000001 -> 0 # monetary reconciliation effect
0.000000456789987 -> 0.0000004568 # valore reale preservato
```

Conteggi corpus:

| Tipo | Valori |
|---|---:|
| Rumore floating point normalizzato | 20.829 |
| Snap a bounds 0/100 o altri bounds plugin-owned | 18.711 |
| Event difference portate a zero | 2.091 |
| Residui monetari portati a zero | 27 |
| Valori numerici compattati complessivi | 1.579.564 |

### 3.4 FIFO

Ogni riga lotto espone un riferimento locale:

```text
L1
L2
L3
```

`lot_ref`:

- non è un ID DB;
- viene assegnato dopo ordinamento deterministico;
- serve per audit/join;
- è vietato come nome user-facing;
- distingue lotti economicamente identici.

Rimossi:

- `opening_broker_name`, ridondante rispetto a `opening_broker_ref`.

Mantenuti:

- opening broker;
- status;
- quantità;
- date;
- custody corrente;
- slice `BROKER` / `IN_TRANSIT`;
- stati degradati;
- valori economici.

Audit rappresentativo:

| Scope | Lotti | `lot_ref` | Gruppi economicamente identici | Righe coinvolte | In-transit |
|---|---:|---:|---:|---:|---:|
| Asset | 1 | 1 | 0 | 0 | 0 |
| Broker | 34 | 34 | 4 | 8 | 0 |
| Portfolio | 41 | 41 | 4 | 8 | 0 |

I gruppi identici sono lotti backend distinti, ordinati con identificatori interni
distinti ma ora auditabili pubblicamente tramite `L#`.

Sul corpus ripetuto:

- 1.389 righe lotto renderizzate;
- 1.389 riferimenti locali;
- 0 riferimenti mancanti;
- 0 riferimenti duplicati nello stesso snapshot;
- 159 gruppi identici diagnosticati, 318 righe coinvolte;
- 1.236 custody rows;
- 0 righe in-transit nell'utente selezionato, ma contratto preservato.

### 3.5 Prezzo unitario e prezzi mancanti

Decisione mantenuta:

```text
unit_price = current_value / quantity
```

Audit:

- 1.380 riconciliazioni;
- tolleranza monetaria `0.01`;
- 0 violazioni.

Nota quote presente solo quando esiste almeno un `quote_base_quantity > 1`:

```text
Market quotes may be published per N units. Position unit prices are normalized
to one unit.
```

Regola prezzo mancante presente al massimo una volta:

```text
When a price is needed for a date without an observation, use the latest
available observation on or before that date. Never use a future price.
```

Righe temporali vuote omesse: 6.097. Nessuna omissione viene presentata come zero.

### 3.6 Technical Breadth senza Risk Calculator

Nuova istruzione:

```text
Separate the supplied trend, momentum, volatility, event, and other explicitly
available signal families. Do not invent or reclassify missing risk metrics.

If a requested family is absent, state that it is unavailable and do not infer
it from another family.
```

Non sono stati aggiunti:

- drawdown;
- VaR;
- CVaR;
- stress test;
- `asset.drawdown_recovery`;
- riclassificazioni volatility -> risk.

## 4. B. Correzioni di leggibilità

### 4.1 Colonne

Il pruning ora è applicato centralmente a tutte le tabelle:

- financial;
- performance;
- flows;
- income;
- fees/taxes;
- reconciliation;
- FIFO;
- positions;
- allocations;
- exposure;
- technical.

Risultati:

- 4.509 colonne completamente vuote eliminate;
- 480 parent nulli eliminati, già inclusi nelle 4.509;
- 11.100 tabelle finali controllate;
- 0 colonne completamente vuote residue;
- 0 parent nulli accanto a figli valorizzati;
- 0 header duplicati;
- 0 duplicati semantici rilevati.

### 4.2 Identità

La Entity Directory continua a essere la fonte di nomi e identificativi.

Riferimenti consentiti per join:

- `A#`;
- `B#`;
- `FX#`;
- `L#`.

Audit pubblico:

- 0 `asset_unmapped`;
- 0 `broker_unmapped`;
- 0 `asset:<id>` / `broker:<id>`;
- 0 `lot_id` / `opening_transaction_id`;
- 0 metadata di schema/versione.

### 4.3 Località semantica

Definizioni Signal, bounds, istanze, period summary, history ed eventi restano vicini.
Gli eventi bounded mostrano correttamente `0` e `100`, non residui binari.

## 5. C. Classificazione dimensionale

Metrica primaria:

```text
token-equivalenti stimati = rendered final prompt chars / 4
```

Non sono token esatti di un modello specifico.

Fasce:

- **Leggero**: `<= 10.000`;
- **Medio**: `> 10.000` e `<= 50.000`;
- **Pesante**: `> 50.000`;
- **Molto pesante**: `> 100.000`, sottosegnalazione di Pesante.

### 5.1 Minimo, tipico, massimo

| Ruolo | Prompt | Char | Token-equivalenti stimati | Categoria |
|---|---|---:|---:|---|
| Minimo | `fx.overview`, 3M Full | 2.189 | 547,25 | Leggero |
| Mediana corpus | `portfolio.performance_attribution`, 1Y Compact | 20.617 | 5.154,25 | Leggero |
| Primo Pesante | `asset.market_technical`, 1Y Full | 216.508 | 54.127,00 | Pesante |
| Massimo | `portfolio.rebalancing`, 1Y Full | 2.425.541 | 606.385,25 | Pesante / Molto pesante |

### 5.2 Distribuzione generale

|Categoria|Prompt|Corpus|Minimo|Mediana|P90|Massimo|
|---|---:|---:|---:|---:|---:|---:|
|Leggero|120|59,70%|547,25|3.185,50|5.857,75|7.172,00|
|Medio|30|14,93%|13.514,75|21.058,75|35.598,25|38.705,25|
|Pesante|51|25,37%|54.127,00|237.919,25|525.369,75|606.385,25|

Molto pesanti: **48**, tutti già inclusi nei 51 Pesanti.

### 5.3 Per modalità

|Modalità|Prompt|Leggeri|Medi|Pesanti|Molto pesanti|Mediana|P90|Massimo|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|analysis|87|36|19|32|30|18.451,75|352.498,50|606.385,25|
|data|114|84|11|19|18|3.132,38|219.419,00|599.421,50|

### 5.4 Per dominio

|Dominio|Prompt|Leggeri|Medi|Pesanti|Molto pesanti|Mediana|P90|Massimo|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|asset|39|18|18|3|0|18.066,75|38.705,25|55.875,00|
|broker|60|39|0|21|21|4.775,00|329.268,50|532.865,50|
|fx|24|12|12|0|0|7.530,50|20.171,50|21.362,25|
|portfolio|78|51|0|27|27|5.642,00|393.781,75|606.385,25|

Portfolio e Broker sono bimodali: prompt finanziari leggeri, prompt con tecnica molto
pesanti. Non esistono casi Medi in questi due domini.

### 5.5 Per detail

|Detail|Prompt|Leggeri|Medi|Pesanti|Molto pesanti|Mediana|P90|Massimo|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|compact|67|40|11|16|16|4.833,25|230.986,50|268.042,50|
|full|67|40|8|19|16|5.426,25|523.639,00|606.385,25|
|standard|67|40|11|16|16|5.054,50|344.715,50|399.288,50|

Compact resta semanticamente completo e temporalmente più rado. Non è stato reso
summary-only.

### 5.6 Per periodo

|Periodo|Prompt|Leggeri|Medi|Pesanti|Molto pesanti|Mediana|P90|Massimo|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|1Y|75|45|6|24|21|5.925,50|399.288,50|606.385,25|
|3M|90|48|21|21|21|5.756,62|194.618,75|256.522,25|
|6M|36|27|3|6|6|3.078,75|237.310,75|377.194,25|

## 6. Prompt rappresentativi

|Categoria|Ruolo|Mode|Domain|Selection|Periodo|Detail|Char|Token-equivalenti stimati|Largest section|Technical|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|Leggero|Minimo|data|fx|`fx.overview`|3M|full|2.189|547,25|snapshot_data|0,00%|
|Leggero|Mediano|data|broker|`broker.fifo`|3M|compact|12.742|3.185,50|snapshot_data|0,00%|
|Leggero|Massimo|analysis|portfolio|`portfolio.pac_planning`|1Y|full|28.688|7.172,00|snapshot_data|0,00%|
|Medio|Minimo|data|fx|`fx.market_technical`|3M|compact|54.059|13.514,75|snapshot_data|96,72%|
|Medio|Mediano|data|asset|`asset.market_technical`|6M|compact|83.044|20.761,00|snapshot_data|97,66%|
|Medio|Massimo|analysis|asset|`asset.position_review`|1Y|standard|154.821|38.705,25|snapshot_data|94,23%|
|Pesante|Minimo|data|asset|`asset.market_technical`|1Y|full|216.508|54.127,00|snapshot_data|99,11%|
|Pesante|Mediano|analysis|broker|`broker.review`|1Y|compact|951.677|237.919,25|snapshot_data|96,94%|
|Pesante|Massimo|analysis|portfolio|`portfolio.rebalancing`|1Y|full|2.425.541|606.385,25|snapshot_data|98,82%|

### 6.1 Tutti i prompt molto pesanti

|Mode|Domain|Selection|Periodo|Detail|Char|Token-equivalenti stimati|Technical|
|---|---:|---:|---:|---:|---:|---:|---:|
|analysis|portfolio|`portfolio.rebalancing`|1Y|full|2.425.541|606.385,25|98,82%|
|analysis|portfolio|`portfolio.description`|1Y|full|2.425.387|606.346,75|98,82%|
|analysis|portfolio|`portfolio.technical_breadth`|1Y|full|2.405.826|601.456,50|99,51%|
|data|portfolio|`portfolio.technical`|1Y|full|2.397.686|599.421,50|99,85%|
|analysis|broker|`broker.review`|1Y|full|2.131.462|532.865,50|98,26%|
|analysis|broker|`broker.concentration_context`|1Y|full|2.101.479|525.369,75|99,54%|
|data|broker|`broker.technical`|1Y|full|2.094.556|523.639,00|99,87%|
|analysis|portfolio|`portfolio.rebalancing`|1Y|standard|1.597.154|399.288,50|98,52%|
|analysis|portfolio|`portfolio.description`|1Y|standard|1.597.000|399.250,00|98,52%|
|analysis|portfolio|`portfolio.technical_breadth`|1Y|standard|1.583.267|395.816,75|99,26%|
|data|portfolio|`portfolio.technical`|1Y|standard|1.575.127|393.781,75|99,77%|
|data|portfolio|`portfolio.technical`|6M|full|1.508.777|377.194,25|99,76%|
|analysis|broker|`broker.review`|1Y|standard|1.409.994|352.498,50|97,73%|
|analysis|broker|`broker.concentration_context`|1Y|standard|1.385.785|346.446,25|99,30%|
|data|broker|`broker.technical`|1Y|standard|1.378.862|344.715,50|99,80%|
|data|broker|`broker.technical`|6M|full|1.317.074|329.268,50|99,79%|
|data|portfolio|`portfolio.technical`|6M|standard|1.085.723|271.430,75|99,67%|
|analysis|portfolio|`portfolio.rebalancing`|1Y|compact|1.072.170|268.042,50|98,06%|
|analysis|portfolio|`portfolio.description`|1Y|compact|1.072.016|268.004,00|98,08%|
|analysis|portfolio|`portfolio.technical_breadth`|1Y|compact|1.061.716|265.429,00|98,89%|
|data|portfolio|`portfolio.technical`|1Y|compact|1.053.576|263.394,00|99,66%|
|analysis|portfolio|`portfolio.rebalancing`|3M|full|1.026.089|256.522,25|97,88%|
|analysis|portfolio|`portfolio.description`|3M|full|1.025.935|256.483,75|97,90%|
|analysis|portfolio|`portfolio.technical_breadth`|3M|full|1.015.428|253.857,00|98,85%|
|data|portfolio|`portfolio.technical`|3M|full|1.007.289|251.822,25|99,64%|
|analysis|broker|`broker.review`|1Y|compact|951.677|237.919,25|96,94%|
|data|broker|`broker.technical`|6M|standard|949.243|237.310,75|99,71%|
|analysis|broker|`broker.concentration_context`|1Y|compact|930.869|232.717,25|98,96%|
|data|broker|`broker.technical`|1Y|compact|923.946|230.986,50|99,70%|
|analysis|broker|`broker.review`|3M|full|904.629|226.157,25|96,79%|
|analysis|broker|`broker.concentration_context`|3M|full|884.555|221.138,75|98,91%|
|data|broker|`broker.technical`|3M|full|877.676|219.419,00|99,69%|
|data|portfolio|`portfolio.technical`|6M|compact|798.298|199.574,50|99,55%|
|analysis|portfolio|`portfolio.rebalancing`|3M|standard|787.318|196.829,50|97,45%|
|analysis|portfolio|`portfolio.description`|3M|standard|787.164|196.791,00|97,47%|
|analysis|portfolio|`portfolio.technical_breadth`|3M|standard|778.475|194.618,75|98,49%|
|data|portfolio|`portfolio.technical`|3M|standard|770.336|192.584,00|99,53%|
|data|broker|`broker.technical`|6M|compact|698.724|174.681,00|99,61%|
|analysis|broker|`broker.review`|3M|standard|697.105|174.276,25|96,07%|
|analysis|broker|`broker.concentration_context`|3M|standard|678.841|169.710,25|98,58%|
|data|broker|`broker.technical`|3M|standard|671.962|167.990,50|99,59%|
|analysis|portfolio|`portfolio.rebalancing`|3M|compact|628.115|157.028,75|96,97%|
|analysis|portfolio|`portfolio.description`|3M|compact|627.961|156.990,25|96,99%|
|analysis|portfolio|`portfolio.technical_breadth`|3M|compact|620.366|155.091,50|98,11%|
|data|portfolio|`portfolio.technical`|3M|compact|612.227|153.056,75|99,41%|
|analysis|broker|`broker.review`|3M|compact|558.264|139.566,00|95,28%|
|analysis|broker|`broker.concentration_context`|3M|compact|541.089|135.272,25|98,22%|
|data|broker|`broker.technical`|3M|compact|534.210|133.552,50|99,49%|

## 7. Classificazione per Analysis type

Tutte le misure sono token-equivalenti stimati.

|Analysis ID|Min|Mediana|Max|3M Compact|1Y Standard|1Y Full|Tech mediana|Tech max|Largest dataset|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|`asset.position_review`|18.451,75|27.278,50|55.875,00|Medio|Medio|Pesante|91,83%|96,01%|`asset.market_technical`|
|`asset.trend_analysis`|18.066,75|26.889,75|55.482,50|Medio|Medio|Pesante|93,15%|96,68%|`asset.market_technical`|
|`broker.concentration_context`|135.272,25|226.928,00|525.369,75|Pesante|Pesante|Pesante|98,94%|99,54%|`broker.technical`|
|`broker.cost_efficiency`|4.046,50|4.629,38|6.519,25|Leggero|Leggero|Leggero|0,00%|0,00%|`broker.performance_flows`|
|`broker.fifo_review`|4.832,50|4.943,50|5.054,50|Leggero|Leggero|Leggero|0,00%|0,00%|`broker.fifo`|
|`broker.review`|139.566,00|232.038,25|532.865,50|Pesante|Pesante|Pesante|96,86%|98,26%|`broker.technical`|
|`fx.conversion_timing`|15.563,75|17.883,50|21.356,50|Medio|—|—|86,07%|88,34%|`fx.market_technical`|
|`fx.exposure_impact`|15.569,50|17.889,25|21.362,25|Medio|—|—|86,03%|88,31%|`fx.market_technical`|
|`fx.trend_review`|14.378,75|16.698,50|20.171,50|Medio|—|—|92,17%|93,53%|`fx.market_technical`|
|`portfolio.description`|156.990,25|262.243,88|606.346,75|Pesante|Pesante|Pesante|97,99%|98,82%|`portfolio.technical`|
|`portfolio.fifo_review`|6.087,00|6.184,38|6.281,75|Leggero|Leggero|Leggero|0,00%|0,00%|`portfolio.fifo`|
|`portfolio.income_review`|4.687,50|5.242,38|7.104,25|Leggero|Leggero|Leggero|0,00%|0,00%|`portfolio.performance_flows`|
|`portfolio.pac_planning`|4.755,25|5.310,12|7.172,00|Leggero|Leggero|Leggero|0,00%|0,00%|`portfolio.performance_flows`|
|`portfolio.performance_attribution`|4.715,50|5.270,38|7.132,25|Leggero|Leggero|Leggero|0,00%|0,00%|`portfolio.performance_flows`|
|`portfolio.rebalancing`|157.028,75|262.282,38|606.385,25|Pesante|Pesante|Pesante|97,97%|98,82%|`portfolio.technical`|
|`portfolio.technical_breadth`|155.091,50|259.643,00|601.456,50|Pesante|Pesante|Pesante|98,87%|99,51%|`portfolio.technical`|

Analisi con maggiore technical share:

```text
broker.concentration_context
mediana technical = 98.94%
massimo technical = 99.54%
```

## 8. Classificazione per fotografia

Tutte le misure sono token-equivalenti stimati.

|Dataset ID|Min|Mediana|Max|3M Compact|1Y Standard|1Y Full|Largest component|
|---|---:|---:|---:|---:|---:|---:|---:|
|`asset.market_technical`|16.711,25|26.099,00|54.127,00|Medio|Medio|Pesante|`asset.indicators`|
|`asset.overview`|1.071,25|1.072,00|1.072,25|Leggero|Leggero|Leggero|`asset.provenance`|
|`asset.position_performance`|885,00|893,25|894,50|Leggero|Leggero|Leggero|`asset.performance`|
|`broker.fifo`|3.184,75|3.185,75|3.395,50|Leggero|Leggero|Leggero|`broker.fifo_lots`|
|`broker.overview`|1.626,25|1.627,75|1.638,25|Leggero|Leggero|Leggero|`broker.positions`|
|`broker.performance_flows`|2.409,00|2.972,75|4.870,50|Leggero|Leggero|Leggero|`broker.performance`|
|`broker.technical`|133.552,50|230.986,50|523.639,00|Pesante|Pesante|Pesante|`broker.technical_indicators`|
|`fx.direct_exposure`|1.545,25|1.546,00|1.546,25|Leggero|Leggero|Leggero|`fx.exposure_base_quote`|
|`fx.market_technical`|13.514,75|15.834,50|19.307,50|Medio|—|—|`fx.indicators`|
|`fx.overview`|547,25|548,00|548,25|Leggero|—|—|`fx.current_rate`|
|`portfolio.fifo`|4.133,00|4.134,00|4.327,50|Leggero|Leggero|Leggero|`portfolio.fifo_lots`|
|`portfolio.overview`|2.041,50|2.042,50|2.043,25|Leggero|Leggero|Leggero|`portfolio.positions`|
|`portfolio.performance_flows`|2.768,75|3.332,25|5.184,75|Leggero|Leggero|Leggero|`portfolio.performance`|
|`portfolio.technical`|153.056,75|263.394,00|599.421,50|Pesante|Pesante|Pesante|`portfolio.technical_indicators`|

## 9. D. Confronto dimensionale e caveat copertura

Confronto su 201 chiavi stabili.

Totali grezzi:

| Run | Caratteri |
|---|---:|
| Precedente | 20.482.572 |
| Corrente | 60.918.711 |
| Delta | +197,42% |

Questo aumento **non** è attribuibile al formatter.

Tra i due run la copertura tecnica è cambiata:

| Dataset 3M Compact | Considerati prev/current | Elegibili prev/current | Coperti prev/current | Istanze prev/current | Eventi export prev/current |
|---|---:|---:|---:|---:|---:|
| Portfolio technical | 8 / 20 | 4 / 17 | 3 / 12 | 54 / 216 | 319 / 1.308 |
| Broker technical | 8 / 13 | 4 / 12 | 3 / 11 | 54 / 198 | 319 / 1.209 |
| Asset technical | n/a | n/a | n/a | 18 / 18 | 105 / 107 |
| FX technical | n/a | n/a | n/a | 12 / 12 | 127 / 127 |

Inventario alto livello rimasto stabile:

- 2 Broker;
- 19 position legs;
- 17 Asset unici;
- 111 transazioni;
- 47 lotti diagnostici.

È cambiata la disponibilità tecnica effettiva:

```text
precedente: eligible 4, covered 3
corrente:   eligible 17, covered 12
```

Perciò 48 prompt con Portfolio/Broker technical non sono un confronto
format-only.

Confronto sui 153 prompt senza variazione di copertura:

| Misura | Valore |
|---|---:|
| Caratteri precedenti | 4.924.017 |
| Caratteri correnti | 4.950.742 |
| Delta | +0,543% |
| Prompt aumentati | 88 |
| Prompt diminuiti | 65 |
| Cambi categoria | 0 |

L'aumento minimo è coerente con lo scopo: `lot_ref`, custody, bounds e semantica pesi
aggiungono informazione; pruning e formattazione numerica la compensano.

Transizioni complessive:

- 120 Leggero -> Leggero;
- 30 Medio -> Medio;
- 43 Pesante -> Pesante;
- 8 Medio -> Pesante, tutti per maggiore copertura tecnica.

## 10. Revisione qualitativa mirata

| Caso | Evidenza | Stato finding | Valutazione |
|---|---|---|---|
| Più leggero | `fx.overview`, 547,25 token-equivalenti stimati | Confermato | Identità, rate, staleness e provenance chiari; nessun rumore |
| Mediana corpus | `portfolio.performance_attribution`, 5.154,25 | Confermato | Prompt finanziario leggibile, completo, senza tecnica |
| Pesante minimo | `asset.market_technical`, 54.127,00 | Confermato | Definizioni localizzate e numeri puliti; history/eventi dominano |
| Massimo | `portfolio.rebalancing`, 606.385,25 | Confermato | 98,82% technical: pertinenza della tecnica opzionale da decidere |
| Finanziario senza tecnica | `portfolio.performance_attribution` | Confermato | Riconciliazione, percentuali, unit price e directory coerenti |
| Tecnico | `asset.market_technical` | Confermato | Bounds/event difference corretti; nessuna perdita o summary-only |
| Tecnica opzionale | `asset.position_review`, 38.705,25 | Confermato | 94,23% technical: il task posizione è quasi interamente tecnica |
| FIFO | `broker.fifo`, 3.185,50 | Confermato | 34 lotti distinguibili con `L#`; tabella molto larga |
| FX riuscito | `fx.trend_review`, 16.698,50 | Confermato | Direction quote/base, history, volatility ed eventi coerenti |

### 10.1 Finding confermati

1. **Correzioni trasversali riuscite**  
   Percentuali, HHI, floating noise, colonne, lot refs e pesi sono coerenti su
   tutto il corpus.

2. **Prompt finanziari puri restano leggeri**  
   PAC, attribution, income, cost efficiency e FIFO review restano sotto 10.000.

3. **Tecnica opzionale domina alcuni task**  
   Rebalancing, description, broker review/concentration e asset position review
   sono dominati dal dataset technical.

4. **Il contenuto tecnico scala con la copertura**  
   Aumento da 4 a 17 Asset eleggibili trasforma la dimensione, senza modifiche a
   Compact/P/M/K/eventi.

5. **FIFO ora è auditabile**  
   Le righe L4/L5 e altri casi economicamente identici sono distinguibili.

### 10.2 Finding potenziali

1. **FIFO molto orizzontale**  
   La tabella è compatta in righe ma contiene molte colonne. Possibile futura
   separazione tra identità/custody ed economia, senza eliminare dati.

2. **Ordine colonne genericamente flattenizzate**  
   Corretto e deterministico, ma alcuni gruppi monetari possono risultare lontani
   dal relativo campo data/indice.

3. **Descrizioni provider lunghe**  
   Restano dati non fidati e possono contribuire a rumore. Problema separato,
   non corretto qui.

### 10.3 Decisioni prodotto future

La formulazione corretta è:

> Il peso residuo è prevalentemente contenuto informativo reale. Restano tuttavia
> da valutare la pertinenza dei dati tecnici per ciascun task, la ridondanza
> semantica di alcuni eventi e il rapporto tra history completa e obiettivo
> dell’analisi.

Proposte non implementate:

- contratto futuro `technical_evidence`;
- densità tecnica distinta per Analysis;
- review semantica eventi ad alta frequenza;
- valutazione history completa vs obiettivo;
- tokenizer specifico quando esisterà un modello target.

## 11. Problemi lasciati intenzionalmente aperti

- coupling FX 6M/1Y;
- integrazione Risk Assessment;
- contratto `technical_evidence`;
- floor/finestra eventi;
- matrice P/M/K;
- classificazione Signal;
- tokenizer specifico;
- descrizione provider;
- classificazione settoriale BTP;
- `all_data`.

## 12. Fallimenti FX

| Selezione | Fallimenti |
|---|---:|
| `fx.market_technical` | 6 |
| `fx.overview` | 6 |
| `fx.trend_review` | 3 |
| `fx.conversion_timing` | 3 |
| `fx.exposure_impact` | 3 |

Tutti:

```text
snapshot_source_failure
```

Nessuna correzione FX è stata applicata.

## 13. File principali modificati

Backend:

- `backend/app/services/ai_export/components/technical_payloads.py`
- `backend/app/services/ai_export/components/technical_shared.py`
- `backend/app/services/ai_export/components/portfolio_broker_technical.py`
- `backend/app/services/ai_export/components/broker_financial.py`
- `backend/app/services/ai_export/components/portfolio_financial.py`
- `backend/app/services/ai_export/components/payloads/portfolio_broker.py`
- `backend/app/services/ai_export/components/asset_payloads.py`
- `backend/app/services/ai_export/components/asset_core.py`
- `backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py`
- test AI Export backend/probe correlati
- `scripts/test_runner/_backend_utils.py`

Frontend:

- `frontend/src/lib/features/ai-export/templates/snapshotDataRenderer.ts`
- `frontend/src/lib/features/ai-export/templates/promptRenderer.ts`
- `frontend/src/lib/features/ai-export/templates/sharedInstructions.ts`
- `frontend/src/lib/features/ai-export/templates/responseContracts.ts`
- `frontend/scripts/ai-export-render-prompt-probe.ts`
- test renderer/prompt correlati

Nessuna modifica OpenAPI necessaria: i component payload restano JSON versionati dentro
`AiExportSectionEnvelope`.

## 14. Artefatti

Run autorevole:

```text
LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/
└── real_prompt_probe/20260731T102457.551232Z/
    ├── run_manifest.json
    ├── metrics.json
    ├── failures.json
    ├── summary.md
    ├── canonical/
    └── prompts/
        ├── data/
        └── analysis/
```

Report:

```text
report-phase00AiExportPublicFormatHardeningV3.md
```

## 15. Conclusione

Le correzioni pubbliche sono riuscite:

- HHI semanticamente corretto;
- quote e pesi direttamente leggibili;
- floating noise rimosso senza cancellare valori piccoli reali;
- tabelle prive di colonne vuote;
- FIFO auditabile;
- unit price e pesi riconciliati;
- Risk non inventato;
- UI/probe equivalenti;
- zero violazioni su 201 prompt.

La distribuzione ora rende evidente una decisione prodotto, non un problema di
serializzazione:

- 59,70% Leggeri;
- 14,93% Medi;
- 25,37% Pesanti;
- 48 prompt Molto pesanti.

L'aumento rispetto al run precedente è guidato dalla maggiore copertura tecnica,
non dalle correzioni di formato. Sui prompt senza cambio di copertura il delta
complessivo è soltanto `+0,543%`.

## Appendice A - confronto completo dei 201 prompt stabili

Le ragioni descrivono le correzioni applicabili al prompt. Le righe con
`technical coverage changed` non sono confronti dimensionali format-only.

|Mode|Domain|Selection|Periodo|Detail|Prev char|Current char|Delta|Delta %|Prev cat.|Current cat.|Ragioni|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|analysis|asset|`asset.position_review`|1Y|compact|112.123|111.388|-735|-0,66%|Medio|Medio|numeric formatting, percentage correction, empty-column removal, FIFO lot reference|
|analysis|asset|`asset.position_review`|1Y|full|224.400|223.500|-900|-0,40%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, FIFO lot reference|
|analysis|asset|`asset.position_review`|1Y|standard|155.703|154.821|-882|-0,57%|Medio|Medio|numeric formatting, percentage correction, empty-column removal, FIFO lot reference|
|analysis|asset|`asset.position_review`|3M|compact|74.060|73.807|-253|-0,34%|Medio|Medio|numeric formatting, percentage correction, empty-column removal, FIFO lot reference|
|analysis|asset|`asset.position_review`|3M|full|107.086|106.840|-246|-0,23%|Medio|Medio|numeric formatting, percentage correction, empty-column removal, FIFO lot reference|
|analysis|asset|`asset.position_review`|3M|standard|87.302|86.973|-329|-0,38%|Medio|Medio|numeric formatting, percentage correction, empty-column removal, FIFO lot reference|
|analysis|asset|`asset.trend_analysis`|1Y|compact|110.492|109.818|-674|-0,61%|Medio|Medio|numeric formatting, percentage correction, empty-column removal|
|analysis|asset|`asset.trend_analysis`|1Y|full|222.769|221.930|-839|-0,38%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal|
|analysis|asset|`asset.trend_analysis`|1Y|standard|154.072|153.251|-821|-0,53%|Medio|Medio|numeric formatting, percentage correction, empty-column removal|
|analysis|asset|`asset.trend_analysis`|3M|compact|72.452|72.267|-185|-0,26%|Medio|Medio|numeric formatting, percentage correction, empty-column removal|
|analysis|asset|`asset.trend_analysis`|3M|full|105.478|105.300|-178|-0,17%|Medio|Medio|numeric formatting, percentage correction, empty-column removal|
|analysis|asset|`asset.trend_analysis`|3M|standard|85.694|85.433|-261|-0,30%|Medio|Medio|numeric formatting, percentage correction, empty-column removal|
|analysis|broker|`broker.concentration_context`|1Y|compact|274.030|930.869|656.839|239,70%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, HHI semantic correction, technical coverage changed|
|analysis|broker|`broker.concentration_context`|1Y|full|594.040|2.101.479|1.507.439|253,76%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, HHI semantic correction, technical coverage changed|
|analysis|broker|`broker.concentration_context`|1Y|standard|398.394|1.385.785|987.391|247,84%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, HHI semantic correction, technical coverage changed|
|analysis|broker|`broker.concentration_context`|3M|compact|165.044|541.089|376.045|227,85%|Medio|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, HHI semantic correction, technical coverage changed|
|analysis|broker|`broker.concentration_context`|3M|full|258.764|884.555|625.791|241,84%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, HHI semantic correction, technical coverage changed|
|analysis|broker|`broker.concentration_context`|3M|standard|202.690|678.841|476.151|234,92%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, HHI semantic correction, technical coverage changed|
|analysis|broker|`broker.cost_efficiency`|1Y|compact|18.943|18.165|-778|-4,11%|Leggero|Leggero|numeric formatting, percentage correction, empty-column removal, HHI semantic correction|
|analysis|broker|`broker.cost_efficiency`|1Y|full|27.775|26.077|-1.698|-6,11%|Leggero|Leggero|numeric formatting, percentage correction, empty-column removal, HHI semantic correction|
|analysis|broker|`broker.cost_efficiency`|1Y|standard|22.209|21.091|-1.118|-5,03%|Leggero|Leggero|numeric formatting, percentage correction, empty-column removal, HHI semantic correction|
|analysis|broker|`broker.cost_efficiency`|3M|compact|16.321|16.186|-135|-0,83%|Leggero|Leggero|percentage correction, empty-column removal, HHI semantic correction|
|analysis|broker|`broker.cost_efficiency`|3M|full|19.325|18.870|-455|-2,35%|Leggero|Leggero|percentage correction, empty-column removal, HHI semantic correction|
|analysis|broker|`broker.cost_efficiency`|3M|standard|17.451|17.196|-255|-1,46%|Leggero|Leggero|percentage correction, empty-column removal, HHI semantic correction|
|analysis|broker|`broker.fifo_review`|1Y|compact|18.845|20.217|1.372|7,28%|Leggero|Leggero|percentage correction, FIFO lot reference, HHI semantic correction|
|analysis|broker|`broker.fifo_review`|1Y|full|18.842|20.214|1.372|7,28%|Leggero|Leggero|percentage correction, FIFO lot reference, HHI semantic correction|
|analysis|broker|`broker.fifo_review`|1Y|standard|18.846|20.218|1.372|7,28%|Leggero|Leggero|percentage correction, FIFO lot reference, HHI semantic correction|
|analysis|broker|`broker.fifo_review`|3M|compact|17.901|19.333|1.432|8,00%|Leggero|Leggero|percentage correction, FIFO lot reference, HHI semantic correction|
|analysis|broker|`broker.fifo_review`|3M|full|17.898|19.330|1.432|8,00%|Leggero|Leggero|percentage correction, FIFO lot reference, HHI semantic correction|
|analysis|broker|`broker.fifo_review`|3M|standard|17.902|19.334|1.432|8,00%|Leggero|Leggero|percentage correction, FIFO lot reference, HHI semantic correction|
|analysis|broker|`broker.review`|1Y|compact|294.630|951.677|657.047|223,01%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, FIFO lot reference, breadth weight clarification, HHI semantic correction, technical coverage changed|
|analysis|broker|`broker.review`|1Y|full|624.735|2.131.462|1.506.727|241,18%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, FIFO lot reference, breadth weight clarification, HHI semantic correction, technical coverage changed|
|analysis|broker|`broker.review`|1Y|standard|422.735|1.409.994|987.259|233,54%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, FIFO lot reference, breadth weight clarification, HHI semantic correction, technical coverage changed|
|analysis|broker|`broker.review`|3M|compact|181.306|558.264|376.958|207,91%|Medio|Pesante|numeric formatting, percentage correction, empty-column removal, FIFO lot reference, breadth weight clarification, HHI semantic correction, technical coverage changed|
|analysis|broker|`broker.review`|3M|full|278.245|904.629|626.384|225,12%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, FIFO lot reference, breadth weight clarification, HHI semantic correction, technical coverage changed|
|analysis|broker|`broker.review`|3M|standard|220.161|697.105|476.944|216,63%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, FIFO lot reference, breadth weight clarification, HHI semantic correction, technical coverage changed|
|analysis|fx|`fx.conversion_timing`|3M|compact|62.762|62.255|-507|-0,81%|Medio|Medio|numeric formatting, empty-column removal|
|analysis|fx|`fx.conversion_timing`|3M|full|86.075|85.426|-649|-0,75%|Medio|Medio|numeric formatting, empty-column removal|
|analysis|fx|`fx.conversion_timing`|3M|standard|72.133|71.534|-599|-0,83%|Medio|Medio|numeric formatting, empty-column removal|
|analysis|fx|`fx.exposure_impact`|3M|compact|62.785|62.278|-507|-0,81%|Medio|Medio|numeric formatting, empty-column removal|
|analysis|fx|`fx.exposure_impact`|3M|full|86.098|85.449|-649|-0,75%|Medio|Medio|numeric formatting, empty-column removal|
|analysis|fx|`fx.exposure_impact`|3M|standard|72.156|71.557|-599|-0,83%|Medio|Medio|numeric formatting, empty-column removal|
|analysis|fx|`fx.trend_review`|3M|compact|57.832|57.515|-317|-0,55%|Medio|Medio|numeric formatting, empty-column removal|
|analysis|fx|`fx.trend_review`|3M|full|81.145|80.686|-459|-0,57%|Medio|Medio|numeric formatting, empty-column removal|
|analysis|fx|`fx.trend_review`|3M|standard|67.203|66.794|-409|-0,61%|Medio|Medio|numeric formatting, empty-column removal|
|analysis|portfolio|`portfolio.description`|1Y|compact|297.469|1.072.016|774.547|260,38%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|analysis|portfolio|`portfolio.description`|1Y|full|643.508|2.425.387|1.781.879|276,90%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|analysis|portfolio|`portfolio.description`|1Y|standard|431.529|1.597.000|1.165.471|270,08%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|analysis|portfolio|`portfolio.description`|3M|compact|182.239|627.961|445.722|244,58%|Medio|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|analysis|portfolio|`portfolio.description`|3M|full|284.165|1.025.935|741.770|261,03%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|analysis|portfolio|`portfolio.description`|3M|standard|223.001|787.164|564.163|252,99%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|analysis|portfolio|`portfolio.fifo_review`|1Y|compact|23.476|25.126|1.650|7,03%|Leggero|Leggero|percentage correction, empty-column removal, FIFO lot reference|
|analysis|portfolio|`portfolio.fifo_review`|1Y|full|23.473|25.123|1.650|7,03%|Leggero|Leggero|percentage correction, empty-column removal, FIFO lot reference|
|analysis|portfolio|`portfolio.fifo_review`|1Y|standard|23.477|25.127|1.650|7,03%|Leggero|Leggero|percentage correction, empty-column removal, FIFO lot reference|
|analysis|portfolio|`portfolio.fifo_review`|3M|compact|22.639|24.351|1.712|7,56%|Leggero|Leggero|percentage correction, empty-column removal, FIFO lot reference|
|analysis|portfolio|`portfolio.fifo_review`|3M|full|22.636|24.348|1.712|7,56%|Leggero|Leggero|percentage correction, empty-column removal, FIFO lot reference|
|analysis|portfolio|`portfolio.fifo_review`|3M|standard|22.640|24.352|1.712|7,56%|Leggero|Leggero|percentage correction, empty-column removal, FIFO lot reference|
|analysis|portfolio|`portfolio.income_review`|1Y|compact|20.724|20.505|-219|-1,06%|Leggero|Leggero|numeric formatting, percentage correction, empty-column removal|
|analysis|portfolio|`portfolio.income_review`|1Y|full|29.556|28.417|-1.139|-3,85%|Leggero|Leggero|numeric formatting, percentage correction, empty-column removal|
|analysis|portfolio|`portfolio.income_review`|1Y|standard|23.990|23.431|-559|-2,33%|Leggero|Leggero|numeric formatting, percentage correction, empty-column removal|
|analysis|portfolio|`portfolio.income_review`|3M|compact|18.338|18.750|412|2,25%|Leggero|Leggero|percentage correction, empty-column removal|
|analysis|portfolio|`portfolio.income_review`|3M|full|21.342|21.434|92|0,43%|Leggero|Leggero|percentage correction, empty-column removal|
|analysis|portfolio|`portfolio.income_review`|3M|standard|19.468|19.760|292|1,50%|Leggero|Leggero|percentage correction, empty-column removal|
|analysis|portfolio|`portfolio.pac_planning`|1Y|compact|20.995|20.776|-219|-1,04%|Leggero|Leggero|numeric formatting, percentage correction, empty-column removal|
|analysis|portfolio|`portfolio.pac_planning`|1Y|full|29.827|28.688|-1.139|-3,82%|Leggero|Leggero|numeric formatting, percentage correction, empty-column removal|
|analysis|portfolio|`portfolio.pac_planning`|1Y|standard|24.261|23.702|-559|-2,30%|Leggero|Leggero|numeric formatting, percentage correction, empty-column removal|
|analysis|portfolio|`portfolio.pac_planning`|3M|compact|18.609|19.021|412|2,21%|Leggero|Leggero|percentage correction, empty-column removal|
|analysis|portfolio|`portfolio.pac_planning`|3M|full|21.613|21.705|92|0,43%|Leggero|Leggero|percentage correction, empty-column removal|
|analysis|portfolio|`portfolio.pac_planning`|3M|standard|19.739|20.031|292|1,48%|Leggero|Leggero|percentage correction, empty-column removal|
|analysis|portfolio|`portfolio.performance_attribution`|1Y|compact|20.836|20.617|-219|-1,05%|Leggero|Leggero|numeric formatting, percentage correction, empty-column removal|
|analysis|portfolio|`portfolio.performance_attribution`|1Y|full|29.668|28.529|-1.139|-3,84%|Leggero|Leggero|numeric formatting, percentage correction, empty-column removal|
|analysis|portfolio|`portfolio.performance_attribution`|1Y|standard|24.102|23.543|-559|-2,32%|Leggero|Leggero|numeric formatting, percentage correction, empty-column removal|
|analysis|portfolio|`portfolio.performance_attribution`|3M|compact|18.450|18.862|412|2,23%|Leggero|Leggero|percentage correction, empty-column removal|
|analysis|portfolio|`portfolio.performance_attribution`|3M|full|21.454|21.546|92|0,43%|Leggero|Leggero|percentage correction, empty-column removal|
|analysis|portfolio|`portfolio.performance_attribution`|3M|standard|19.580|19.872|292|1,49%|Leggero|Leggero|percentage correction, empty-column removal|
|analysis|portfolio|`portfolio.rebalancing`|1Y|compact|297.623|1.072.170|774.547|260,24%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|analysis|portfolio|`portfolio.rebalancing`|1Y|full|643.662|2.425.541|1.781.879|276,83%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|analysis|portfolio|`portfolio.rebalancing`|1Y|standard|431.683|1.597.154|1.165.471|269,98%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|analysis|portfolio|`portfolio.rebalancing`|3M|compact|182.393|628.115|445.722|244,37%|Medio|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|analysis|portfolio|`portfolio.rebalancing`|3M|full|284.319|1.026.089|741.770|260,89%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|analysis|portfolio|`portfolio.rebalancing`|3M|standard|223.155|787.318|564.163|252,81%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|analysis|portfolio|`portfolio.technical_breadth`|1Y|compact|287.809|1.061.716|773.907|268,90%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|analysis|portfolio|`portfolio.technical_breadth`|1Y|full|625.013|2.405.826|1.780.813|284,92%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|analysis|portfolio|`portfolio.technical_breadth`|1Y|standard|418.604|1.583.267|1.164.663|278,23%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|analysis|portfolio|`portfolio.technical_breadth`|3M|compact|174.962|620.366|445.404|254,57%|Medio|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|analysis|portfolio|`portfolio.technical_breadth`|3M|full|273.881|1.015.428|741.547|270,76%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|analysis|portfolio|`portfolio.technical_breadth`|3M|standard|214.595|778.475|563.880|262,76%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|data|asset|`asset.market_technical`|1Y|compact|105.096|104.396|-700|-0,67%|Medio|Medio|numeric formatting, empty-column removal|
|data|asset|`asset.market_technical`|1Y|full|217.373|216.508|-865|-0,40%|Pesante|Pesante|numeric formatting, empty-column removal|
|data|asset|`asset.market_technical`|1Y|standard|148.676|147.829|-847|-0,57%|Medio|Medio|numeric formatting, empty-column removal|
|data|asset|`asset.market_technical`|3M|compact|67.056|66.845|-211|-0,31%|Medio|Medio|numeric formatting, empty-column removal|
|data|asset|`asset.market_technical`|3M|full|100.082|99.878|-204|-0,20%|Medio|Medio|numeric formatting, empty-column removal|
|data|asset|`asset.market_technical`|3M|standard|80.298|80.011|-287|-0,36%|Medio|Medio|numeric formatting, empty-column removal|
|data|asset|`asset.market_technical`|6M|compact|83.601|83.044|-557|-0,67%|Medio|Medio|numeric formatting, empty-column removal|
|data|asset|`asset.market_technical`|6M|full|143.013|142.393|-620|-0,43%|Medio|Medio|numeric formatting, empty-column removal|
|data|asset|`asset.market_technical`|6M|standard|107.706|107.039|-667|-0,62%|Medio|Medio|numeric formatting, empty-column removal|
|data|asset|`asset.overview`|1Y|compact|4.072|4.288|216|5,30%|Leggero|Leggero|percentage correction|
|data|asset|`asset.overview`|1Y|full|4.069|4.285|216|5,31%|Leggero|Leggero|percentage correction|
|data|asset|`asset.overview`|1Y|standard|4.073|4.289|216|5,30%|Leggero|Leggero|percentage correction|
|data|asset|`asset.overview`|3M|compact|4.072|4.288|216|5,30%|Leggero|Leggero|percentage correction|
|data|asset|`asset.overview`|3M|full|4.069|4.285|216|5,31%|Leggero|Leggero|percentage correction|
|data|asset|`asset.overview`|3M|standard|4.073|4.289|216|5,30%|Leggero|Leggero|percentage correction|
|data|asset|`asset.overview`|6M|compact|4.072|4.288|216|5,30%|Leggero|Leggero|percentage correction|
|data|asset|`asset.overview`|6M|full|4.069|4.285|216|5,31%|Leggero|Leggero|percentage correction|
|data|asset|`asset.overview`|6M|standard|4.073|4.289|216|5,30%|Leggero|Leggero|percentage correction|
|data|asset|`asset.position_performance`|1Y|compact|3.440|3.573|133|3,87%|Leggero|Leggero|percentage correction, empty-column removal, FIFO lot reference|
|data|asset|`asset.position_performance`|1Y|full|3.437|3.570|133|3,87%|Leggero|Leggero|percentage correction, empty-column removal, FIFO lot reference|
|data|asset|`asset.position_performance`|1Y|standard|3.441|3.574|133|3,87%|Leggero|Leggero|percentage correction, empty-column removal, FIFO lot reference|
|data|asset|`asset.position_performance`|3M|compact|3.417|3.543|126|3,69%|Leggero|Leggero|percentage correction, empty-column removal, FIFO lot reference|
|data|asset|`asset.position_performance`|3M|full|3.414|3.540|126|3,69%|Leggero|Leggero|percentage correction, empty-column removal, FIFO lot reference|
|data|asset|`asset.position_performance`|3M|standard|3.418|3.544|126|3,69%|Leggero|Leggero|percentage correction, empty-column removal, FIFO lot reference|
|data|asset|`asset.position_performance`|6M|compact|3.444|3.577|133|3,86%|Leggero|Leggero|percentage correction, empty-column removal, FIFO lot reference|
|data|asset|`asset.position_performance`|6M|full|3.441|3.574|133|3,87%|Leggero|Leggero|percentage correction, empty-column removal, FIFO lot reference|
|data|asset|`asset.position_performance`|6M|standard|3.445|3.578|133|3,86%|Leggero|Leggero|percentage correction, empty-column removal, FIFO lot reference|
|data|broker|`broker.fifo`|1Y|compact|12.208|13.581|1.373|11,25%|Leggero|Leggero|FIFO lot reference|
|data|broker|`broker.fifo`|1Y|full|12.205|13.578|1.373|11,25%|Leggero|Leggero|FIFO lot reference|
|data|broker|`broker.fifo`|1Y|standard|12.209|13.582|1.373|11,25%|Leggero|Leggero|FIFO lot reference|
|data|broker|`broker.fifo`|3M|compact|11.309|12.742|1.433|12,67%|Leggero|Leggero|FIFO lot reference|
|data|broker|`broker.fifo`|3M|full|11.306|12.739|1.433|12,67%|Leggero|Leggero|FIFO lot reference|
|data|broker|`broker.fifo`|3M|standard|11.310|12.743|1.433|12,67%|Leggero|Leggero|FIFO lot reference|
|data|broker|`broker.fifo`|6M|compact|11.309|12.742|1.433|12,67%|Leggero|Leggero|FIFO lot reference|
|data|broker|`broker.fifo`|6M|full|11.306|12.739|1.433|12,67%|Leggero|Leggero|FIFO lot reference|
|data|broker|`broker.fifo`|6M|standard|11.310|12.743|1.433|12,67%|Leggero|Leggero|FIFO lot reference|
|data|broker|`broker.overview`|1Y|compact|6.363|6.552|189|2,97%|Leggero|Leggero|percentage correction, HHI semantic correction|
|data|broker|`broker.overview`|1Y|full|6.360|6.549|189|2,97%|Leggero|Leggero|percentage correction, HHI semantic correction|
|data|broker|`broker.overview`|1Y|standard|6.364|6.553|189|2,97%|Leggero|Leggero|percentage correction, HHI semantic correction|
|data|broker|`broker.overview`|3M|compact|6.319|6.508|189|2,99%|Leggero|Leggero|percentage correction, HHI semantic correction|
|data|broker|`broker.overview`|3M|full|6.316|6.505|189|2,99%|Leggero|Leggero|percentage correction, HHI semantic correction|
|data|broker|`broker.overview`|3M|standard|6.320|6.509|189|2,99%|Leggero|Leggero|percentage correction, HHI semantic correction|
|data|broker|`broker.overview`|6M|compact|6.323|6.511|188|2,97%|Leggero|Leggero|percentage correction, HHI semantic correction|
|data|broker|`broker.overview`|6M|full|6.320|6.508|188|2,97%|Leggero|Leggero|percentage correction, HHI semantic correction|
|data|broker|`broker.overview`|6M|standard|6.324|6.512|188|2,97%|Leggero|Leggero|percentage correction, HHI semantic correction|
|data|broker|`broker.performance_flows`|1Y|compact|12.347|11.570|-777|-6,29%|Leggero|Leggero|numeric formatting, percentage correction, empty-column removal|
|data|broker|`broker.performance_flows`|1Y|full|21.179|19.482|-1.697|-8,01%|Leggero|Leggero|numeric formatting, percentage correction, empty-column removal|
|data|broker|`broker.performance_flows`|1Y|standard|15.613|14.496|-1.117|-7,15%|Leggero|Leggero|numeric formatting, percentage correction, empty-column removal|
|data|broker|`broker.performance_flows`|3M|compact|9.367|9.636|269|2,87%|Leggero|Leggero|percentage correction, empty-column removal|
|data|broker|`broker.performance_flows`|3M|full|12.371|12.320|-51|-0,41%|Leggero|Leggero|percentage correction, empty-column removal|
|data|broker|`broker.performance_flows`|3M|standard|10.497|10.646|149|1,42%|Leggero|Leggero|percentage correction, empty-column removal|
|data|broker|`broker.performance_flows`|6M|compact|10.863|10.205|-658|-6,06%|Leggero|Leggero|percentage correction, empty-column removal|
|data|broker|`broker.performance_flows`|6M|full|15.764|14.586|-1.178|-7,47%|Leggero|Leggero|percentage correction, empty-column removal|
|data|broker|`broker.performance_flows`|6M|standard|12.749|11.891|-858|-6,73%|Leggero|Leggero|percentage correction, empty-column removal|
|data|broker|`broker.technical`|1Y|compact|266.607|923.946|657.339|246,56%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|data|broker|`broker.technical`|1Y|full|586.617|2.094.556|1.507.939|257,06%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|data|broker|`broker.technical`|1Y|standard|390.971|1.378.862|987.891|252,68%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|data|broker|`broker.technical`|3M|compact|157.665|534.210|376.545|238,83%|Medio|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|data|broker|`broker.technical`|3M|full|251.385|877.676|626.291|249,14%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|data|broker|`broker.technical`|3M|standard|195.311|671.962|476.651|244,05%|Medio|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|data|broker|`broker.technical`|6M|compact|205.402|698.724|493.322|240,17%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|data|broker|`broker.technical`|6M|full|374.446|1.317.074|942.628|251,74%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|data|broker|`broker.technical`|6M|standard|273.999|949.243|675.244|246,44%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|data|fx|`fx.direct_exposure`|1Y|compact|6.317|6.184|-133|-2,11%|Leggero|Leggero|empty-column removal|
|data|fx|`fx.direct_exposure`|1Y|full|6.314|6.181|-133|-2,11%|Leggero|Leggero|empty-column removal|
|data|fx|`fx.direct_exposure`|1Y|standard|6.318|6.185|-133|-2,11%|Leggero|Leggero|empty-column removal|
|data|fx|`fx.direct_exposure`|3M|compact|6.317|6.184|-133|-2,11%|Leggero|Leggero|empty-column removal|
|data|fx|`fx.direct_exposure`|3M|full|6.314|6.181|-133|-2,11%|Leggero|Leggero|empty-column removal|
|data|fx|`fx.direct_exposure`|3M|standard|6.318|6.185|-133|-2,11%|Leggero|Leggero|empty-column removal|
|data|fx|`fx.direct_exposure`|6M|compact|6.317|6.184|-133|-2,11%|Leggero|Leggero|empty-column removal|
|data|fx|`fx.direct_exposure`|6M|full|6.314|6.181|-133|-2,11%|Leggero|Leggero|empty-column removal|
|data|fx|`fx.direct_exposure`|6M|standard|6.318|6.185|-133|-2,11%|Leggero|Leggero|empty-column removal|
|data|fx|`fx.market_technical`|3M|compact|54.380|54.059|-321|-0,59%|Medio|Medio|numeric formatting, empty-column removal|
|data|fx|`fx.market_technical`|3M|full|77.693|77.230|-463|-0,60%|Medio|Medio|numeric formatting, empty-column removal|
|data|fx|`fx.market_technical`|3M|standard|63.751|63.338|-413|-0,65%|Medio|Medio|numeric formatting, empty-column removal|
|data|fx|`fx.overview`|3M|compact|1.969|2.192|223|11,33%|Leggero|Leggero|other|
|data|fx|`fx.overview`|3M|full|1.966|2.189|223|11,34%|Leggero|Leggero|other|
|data|fx|`fx.overview`|3M|standard|1.970|2.193|223|11,32%|Leggero|Leggero|other|
|data|portfolio|`portfolio.fifo`|1Y|compact|15.619|17.309|1.690|10,82%|Leggero|Leggero|FIFO lot reference|
|data|portfolio|`portfolio.fifo`|1Y|full|15.616|17.306|1.690|10,82%|Leggero|Leggero|FIFO lot reference|
|data|portfolio|`portfolio.fifo`|1Y|standard|15.620|17.310|1.690|10,82%|Leggero|Leggero|FIFO lot reference|
|data|portfolio|`portfolio.fifo`|3M|compact|14.785|16.535|1.750|11,84%|Leggero|Leggero|FIFO lot reference|
|data|portfolio|`portfolio.fifo`|3M|full|14.782|16.532|1.750|11,84%|Leggero|Leggero|FIFO lot reference|
|data|portfolio|`portfolio.fifo`|3M|standard|14.786|16.536|1.750|11,84%|Leggero|Leggero|FIFO lot reference|
|data|portfolio|`portfolio.fifo`|6M|compact|14.785|16.535|1.750|11,84%|Leggero|Leggero|FIFO lot reference|
|data|portfolio|`portfolio.fifo`|6M|full|14.782|16.532|1.750|11,84%|Leggero|Leggero|FIFO lot reference|
|data|portfolio|`portfolio.fifo`|6M|standard|14.786|16.536|1.750|11,84%|Leggero|Leggero|FIFO lot reference|
|data|portfolio|`portfolio.overview`|1Y|compact|8.020|8.170|150|1,87%|Leggero|Leggero|percentage correction, empty-column removal|
|data|portfolio|`portfolio.overview`|1Y|full|8.017|8.167|150|1,87%|Leggero|Leggero|percentage correction, empty-column removal|
|data|portfolio|`portfolio.overview`|1Y|standard|8.021|8.171|150|1,87%|Leggero|Leggero|percentage correction, empty-column removal|
|data|portfolio|`portfolio.overview`|3M|compact|8.017|8.169|152|1,90%|Leggero|Leggero|percentage correction, empty-column removal|
|data|portfolio|`portfolio.overview`|3M|full|8.014|8.166|152|1,90%|Leggero|Leggero|percentage correction, empty-column removal|
|data|portfolio|`portfolio.overview`|3M|standard|8.018|8.170|152|1,90%|Leggero|Leggero|percentage correction, empty-column removal|
|data|portfolio|`portfolio.overview`|6M|compact|8.022|8.172|150|1,87%|Leggero|Leggero|percentage correction, empty-column removal|
|data|portfolio|`portfolio.overview`|6M|full|8.019|8.169|150|1,87%|Leggero|Leggero|percentage correction, empty-column removal|
|data|portfolio|`portfolio.overview`|6M|standard|8.023|8.173|150|1,87%|Leggero|Leggero|percentage correction, empty-column removal|
|data|portfolio|`portfolio.performance_flows`|1Y|compact|12.361|12.827|466|3,77%|Leggero|Leggero|numeric formatting, percentage correction, empty-column removal|
|data|portfolio|`portfolio.performance_flows`|1Y|full|21.193|20.739|-454|-2,14%|Leggero|Leggero|numeric formatting, percentage correction, empty-column removal|
|data|portfolio|`portfolio.performance_flows`|1Y|standard|15.627|15.753|126|0,81%|Leggero|Leggero|numeric formatting, percentage correction, empty-column removal|
|data|portfolio|`portfolio.performance_flows`|3M|compact|9.579|11.075|1.496|15,62%|Leggero|Leggero|percentage correction, empty-column removal|
|data|portfolio|`portfolio.performance_flows`|3M|full|12.583|13.759|1.176|9,35%|Leggero|Leggero|percentage correction, empty-column removal|
|data|portfolio|`portfolio.performance_flows`|3M|standard|10.709|12.085|1.376|12,85%|Leggero|Leggero|percentage correction, empty-column removal|
|data|portfolio|`portfolio.performance_flows`|6M|compact|11.076|11.643|567|5,12%|Leggero|Leggero|percentage correction, empty-column removal|
|data|portfolio|`portfolio.performance_flows`|6M|full|15.977|16.024|47|0,29%|Leggero|Leggero|percentage correction, empty-column removal|
|data|portfolio|`portfolio.performance_flows`|6M|standard|12.962|13.329|367|2,83%|Leggero|Leggero|percentage correction, empty-column removal|
|data|portfolio|`portfolio.technical`|1Y|compact|277.302|1.053.576|776.274|279,94%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|data|portfolio|`portfolio.technical`|1Y|full|613.160|2.397.686|1.784.526|291,04%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|data|portfolio|`portfolio.technical`|1Y|standard|407.589|1.575.127|1.167.538|286,45%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|data|portfolio|`portfolio.technical`|3M|compact|164.974|612.227|447.253|271,11%|Medio|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|data|portfolio|`portfolio.technical`|3M|full|263.443|1.007.289|743.846|282,36%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|data|portfolio|`portfolio.technical`|3M|standard|204.437|770.336|565.899|276,81%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|data|portfolio|`portfolio.technical`|6M|compact|213.834|798.298|584.464|273,33%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|data|portfolio|`portfolio.technical`|6M|full|391.302|1.508.777|1.117.475|285,58%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
|data|portfolio|`portfolio.technical`|6M|standard|285.727|1.085.723|799.996|279,99%|Pesante|Pesante|numeric formatting, percentage correction, empty-column removal, breadth weight clarification, technical coverage changed|
