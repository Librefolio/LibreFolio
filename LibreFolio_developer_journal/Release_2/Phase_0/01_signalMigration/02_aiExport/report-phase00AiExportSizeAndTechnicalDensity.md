# Phase 00 - AI Export P0 Corrections and Technical Density

**Data**: 30 luglio 2026
**Stato**: correzioni P0 implementate; policy di riduzione non implementata
**Source of truth**: codice corrente + DB test ripopolato da zero
**Audit precedente**: [report-phase00AiExportRuntimeDeepAudit.md](report-phase00AiExportRuntimeDeepAudit.md)
**Dati grezzi**: [probe-phase00AiExportTechnicalDensity.json](probe-phase00AiExportTechnicalDensity.json)
**Probe versionato**: `backend/test_scripts/diagnostics/ai_export_technical_density_probe.py`

## Risposta esecutiva

1. I circa **666.000 token non derivavano da 3 mesi**. La richiesta era Full, `portfolio.technical`, `broker_ids=[5]`, dal **2025-07-31** al **2026-07-30**: 365 giorni inclusivi, quindi **1Y**.
2. Le quattro correzioni approvate sono implementate:
   - universo tecnico univoco per `asset_id`, con peso multi-broker aggregato;
   - serie tecnica Asset nativa e valutazione target-currency separata;
   - return/P&L inter-bucket, non più `first/last` dello stesso giorno;
   - eventi observed-only con epsilon assoluto + relativo e FX carry-forward escluso dalla volatilità.
3. `asset.drawdown_recovery` non è più pubblica: catalogo, UI lookup, prompt, response contract e traduzioni sono stati rimossi. Le analisi pubbliche passano da 17 a **16**.
4. Tutti i **27/27** probe della matrice sono riusciti. Il massimo corrente è ancora `portfolio.technical`, Full, 1Y:
   - **2.676.781 caratteri/byte UTF-8**;
   - **669.196 token stimati**;
   - 3 asset, 60 istanze indicatore, 75 bucket, 1.615 eventi.
5. Nel caso massimo il peso è:
   - righe storiche degli indicatori: **1.976.417 caratteri, 73,84% del totale**;
   - blocco eventi: **576.535, 21,54%**;
   - prezzi tecnici: **76.593, 2,86%**;
   - metadata indicatori senza righe: **43.447, 1,62%**.
6. Quindi l'ordine delle cause è: **storia indicatori >> eventi >> prezzi**. I metadata ripetuti degli indicatori sono reali ma non dominanti.
7. Lo scenario generale più promettente è **ultimi 5 bucket per indicatore + summary di periodo + latest state + eventi completi**:
   - Portfolio Full 1Y: **795.927 caratteri / 198.982 token**;
   - riduzione **70,27%**;
   - conserva un breve andamento recente, a differenza dello scenario summary-only.
8. Nessun formato pubblico è stato ridotto, segmentato o troncato in questa attività.

## Artefatti e riproducibilità

### Matrice completa

```bash
./dev.py test db populate --force --clean
pipenv run python backend/test_scripts/diagnostics/ai_export_technical_density_probe.py \
  --output LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/probe-phase00AiExportTechnicalDensity.json
```

Il probe:

- usa `AiExportSnapshotService` reale e SQLite test reale;
- non mocka componenti o engine;
- misura 3M/6M/1Y x Compact/Standard/Full x Asset/Broker/Portfolio;
- serializza con `canonical_json`;
- usa l'euristica runtime `chars_div_4_v1`;
- non modifica il payload pubblico;
- simula A-E su copie offline;
- fallisce con exit code non-zero se un probe richiesto fallisce.

### Dataset test

Il DB pulito contiene:

- 8 broker;
- 17 asset;
- 71 transazioni;
- 1.549 righe `price_history`;
- 3.345 righe FX;
- AAPL, BTC ed ETH nel broker 5;
- AAPL detenuta anche presso più broker nel portfolio completo.

Il server HTTP test esegue un current-price bootstrap all'avvio: durante il gate HTTP le righe prezzo sono salite temporaneamente da 1.549 a 1.641. Per questo i numeri HTTP differiscono leggermente dalla matrice deterministica. Dopo il gate il DB è stato ripopolato da zero.

## Correzioni implementate

### Universo Portfolio/Broker univoco per asset

`TechnicalUniverseBundle` conserva:

- `positions`: righe economiche per broker;
- `asset_ids`: universo tecnico unico e ordinato;
- `weights`: gross exposure aggregata per asset;
- `considered_count`: righe posizione considerate.

La formula del peso è ora:

```text
gross(asset) = sum(abs(end_value)) per tutte le gambe broker
weight(asset) = gross(asset) / sum(gross di tutti gli asset unici)
```

Prezzi, segnali, eventi e breadth vengono calcolati una volta per asset.

Gate HTTP sul portfolio completo:

| Campo | Risultato |
|---|---:|
| HTTP | 200 |
| Position rows considerate | 11 |
| Asset tecnici eleggibili unici | 7 |
| Asset IDs duplicati nel payload | 0 |
| Somma pesi | 1,0 |
| Eventi | 712 |

Questo percorso prima poteva fallire in `PriceResultsResource` per duplicate `asset_id`.

### Coerenza valutaria Asset

Decisione adottata:

- analisi tecnica: serie omogenea nella valuta nativa di mercato;
- market snapshot/valutazione: richiesta separata nella target currency;
- Portfolio/Broker finanziario: target currency invariata;
- una serie mista non viene passata al Signal System.

`AssetSourceManager.get_prices_bulk` verifica ora l'insieme delle valute prima del calcolo segnali. Se la serie non è omogenea:

- conserva i punti originali per il consumer non tecnico;
- aggiunge un errore esplicito;
- passa una serie vuota al Signal System;
- gli indicatori risultano unavailable, non vengono calcolati su valori misti.

Copertura test:

| Caso | Esito |
|---|---|
| Serie nativa | indicatori OK |
| Serie interamente convertita | indicatori OK |
| Target = valuta nativa | indicatori OK |
| Conversione parziale | valute native+target conservate, indicatori unavailable |
| Cambio mancante iniziale | nessun indicatore mixed-currency |
| Conversione impossibile | errore esplicito, nessun calcolo tecnico misto |
| Asset market snapshot target EUR + tecnica nativa USD | due risorse separate e coerenti |

### Return e P&L dei bucket

#### Prezzi e FX

Ogni `PriceBucket` mantiene:

- first/minimum/maximum/last interni;
- observation count;
- data reale di minimo e massimo;
- `return_start_date`;
- return rispetto alla chiusura dell'ultimo bucket non vuoto.

Semantica:

```text
return(bucket_n) = last(bucket_n) / last(previous_non_empty_bucket) - 1
```

Il primo bucket popolato ha `simple_return=null`, perché non viene caricata un'osservazione pre-periodo dedicata. I bucket vuoti hanno return nullo e non cancellano l'ultima ancora osservata.

#### Portfolio e Broker

`build_performance_bucket_rows()` usa i campi del Portfolio Calculation Engine:

```text
external_flow = capital_baseline(end) - capital_baseline(previous_close)
period_pnl    = total_pnl(end) - total_pnl(previous_close)
reconciliation =
    nav(end) - nav(previous_close) - external_flow - period_pnl
period_twrr =
    (1 + cumulative_twrr(end)) / (1 + cumulative_twrr(previous_close)) - 1
```

`start_value`/`end_value` restano statistiche interne al bucket. L'ancora della variazione è separata in `variation_start_date` e `variation_start_value`.

I test coprono bucket giornalieri, bucket consecutivi, primo bucket, vuoti, flussi esterni, festività/gap e Portfolio/Broker separatamente.

### Eventi observed-only, backward-fill ed epsilon

Policy AI Export:

```text
observed_only = true
absolute_epsilon = 1e-12
relative_epsilon = 1e-12
effective_epsilon =
    max(absolute_epsilon,
        relative_epsilon * max(abs(left), abs(right)))
```

La tolleranza:

- ha un floor assoluto per rumore vicino a zero;
- cresce con la scala di prezzi/medie;
- resta configurabile per singola annotation request;
- non cambia i valori serializzati, ma la classificazione del lato del cross.

I punti backward-filled:

- non possono generare un evento;
- non resettano lo stato se tutti i giorni intermedi sono rappresentati come carry-forward;
- permettono quindi un cross reale venerdi -> lunedi;
- un vero gap non rappresentato continua a resettare lo stato.

Per FX:

- `SignalPricePoint` conserva `actual_rate_date` e `days_back`;
- `fx.rate_ohlc` usa osservazioni effettive;
- i return e la volatilita usano solo osservazioni effettive;
- il carry-forward non aumenta il campione.

### Drawdown Recovery sospesa

Sono stati rimossi:

- `asset.drawdown_recovery` dal catalogo backend;
- ID e lookup frontend;
- instruction template;
- response contract;
- traduzioni EN/IT/FR/ES;
- riferimenti drawdown negli altri prompt tecnici che non hanno `RISK_DRAWDOWN`.

La memoria frontend con una vecchia selezione Drawdown viene scartata e ricade sulla selezione valida di default.

TODO Risk Assessment:

[g7-ai-export-drawdown.md](../../02_riskfolioIntegration/workItems/g7-ai-export-drawdown.md)

Contiene: integrazione `RISK_DRAWDOWN`, picco/trough e date, profondita, durata, drawdown corrente, percentuale recuperata, distanza residua, episodio aperto/chiuso, massimo nel periodo, episodi confrontabili e futura reintegrazione AI.

## File e simboli principali

| Area | File/simboli |
|---|---|
| Universo/pesi | `technical_shared.py`: `compute_nav_weights`, `TechnicalUniverseBundle`, `load_technical_universe_bundle` |
| Loop unici | `portfolio_broker_technical.py`: prezzi, indicatori, breadth, eventi |
| Serie tecnica nativa | `technical_shared.py`: `load_asset_price_results` |
| Snapshot target | `asset_resources.py`: `ASSET_MARKET_PRICES_RESOURCE`, `load_asset_market_prices`; `asset_core.py` |
| Guard mixed-currency | `asset_source.py`: signal computation pass |
| Price/FX bucket | `technical_shared.py`: `build_price_buckets`; `technical_payloads.py`: `PriceBucket` |
| Portfolio/Broker bucket | `payloads/portfolio_broker.py`: `build_performance_bucket_rows` |
| Event policy | `signal_annotations.py`: `_crossings`, `_effective_epsilon`, `_gap_contains_only_represented_backfill` |
| Annotation schema | `schemas/signals.py`: `relative_epsilon` |
| FX provenance/sample | `technical_shared.py`: `load_fx_technical_bundle`, `observations_to_rate_points`; `asset_fx_technical.py`: `_daily_return_points` |
| Catalogo analisi | `analyses/catalog.py`: 16 analisi |
| Frontend | `catalog/shared.ts`, `sharedInstructions.ts`, `responseContracts.ts`, `aiExportMemory.ts` tests |
| Probe | `backend/test_scripts/diagnostics/ai_export_technical_density_probe.py` |

## Ricostruzione del probe da circa 666.000 token

| Campo | Valore storico |
|---|---|
| Selection | `portfolio.technical` |
| Broker scope | `[5]` |
| Detail | Full |
| Target currency | USD |
| Inizio | 2025-07-31 |
| Snapshot/end | 2026-07-30 |
| Durata inclusiva | 365 giorni |
| Periodo | **1Y, non 3M** |
| Asset | 3 |
| Posizioni | 3 |
| Indicatori | 20 per asset, 60 totali |
| Colonne indicatore | 33 per asset |
| Bucket attesi | 75 |
| Bucket effettivi | 75 |
| Righe indicatore | 3 x 20 x 75 = 4.500 |
| Celle indicatore teoriche | 3 x 33 x 75 = 7.425 |
| Eventi | 1.639 |
| Caratteri | 2.665.012 |
| Token stimati | 666.253 |

Warm-up:

- massimo richiesto: 1.200 giorni/punti, dominato dalla stabilizzazione EMA200;
- load start teorico: 2022-04-18;
- copertura seed prezzo: dal 2025-07-23;
- punti calendarizzati pre-periodo disponibili: 8;
- le righe pre-periodo sono usate dal calcolo ma non vengono esportate.

Il payload raggiunge quella dimensione soprattutto per 4.500 righe indicatore multi-colonna e 1.639 eventi completi. I 225 bucket prezzo hanno peso secondario.

### Stessa richiesta dopo P0

| Campo | Storico | Corrente | Delta |
|---|---:|---:|---:|
| Eventi | 1.639 | 1.615 | -24 |
| Caratteri | 2.665.012 | 2.676.781 | +11.769 |
| Token stimati | 666.253 | 669.196 | +2.943 |

La dimensione non scende: gli eventi diminuiscono, ma date degli estremi e anchor dei return aggiungono dati auditabili. Le correzioni P0 erano di correttezza, non una policy di compressione.

## Matrice 3M/6M/1Y x Compact/Standard/Full

`Chars = byte UTF-8` in tutti questi probe.

| Scope | Period | Detail | Asset | Broker | Pos | Dup legs | Ind req/exp | Eventi | Bucket | Chars/bytes | Token |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Asset | 3M | Compact | 1 | 7 | 0 | 0 | 20/20 | 128 | 20 | 214.069 | 53.518 |
| Asset | 6M | Compact | 1 | 7 | 0 | 0 | 20/20 | 257 | 23 | 293.132 | 73.283 |
| Asset | 1Y | Compact | 1 | 7 | 0 | 0 | 20/20 | 480 | 29 | 435.580 | 108.895 |
| Asset | 3M | Standard | 1 | 7 | 0 | 0 | 20/20 | 128 | 26 | 267.845 | 66.962 |
| Asset | 6M | Standard | 1 | 7 | 0 | 0 | 20/20 | 257 | 33 | 390.776 | 97.694 |
| Asset | 1Y | Standard | 1 | 7 | 0 | 0 | 20/20 | 480 | 46 | 597.648 | 149.412 |
| Asset | 3M | Full | 1 | 7 | 0 | 0 | 20/20 | 128 | 35 | 342.361 | 85.591 |
| Asset | 6M | Full | 1 | 7 | 0 | 0 | 20/20 | 257 | 49 | 542.201 | 135.551 |
| Asset | 1Y | Full | 1 | 7 | 0 | 0 | 20/20 | 480 | 75 | 876.842 | 219.211 |
| Broker | 3M | Compact | 3 | 1 | 3 | 0 | 60/60 | 445 | 20 | 639.353 | 159.839 |
| Broker | 6M | Compact | 3 | 1 | 3 | 0 | 60/60 | 805 | 23 | 862.848 | 215.712 |
| Broker | 1Y | Compact | 3 | 1 | 3 | 0 | 60/60 | 1.615 | 29 | 1.330.531 | 332.633 |
| Broker | 3M | Standard | 3 | 1 | 3 | 0 | 60/60 | 445 | 26 | 793.589 | 198.398 |
| Broker | 6M | Standard | 3 | 1 | 3 | 0 | 60/60 | 805 | 33 | 1.144.305 | 286.077 |
| Broker | 1Y | Standard | 3 | 1 | 3 | 0 | 60/60 | 1.615 | 46 | 1.796.923 | 449.231 |
| Broker | 3M | Full | 3 | 1 | 3 | 0 | 60/60 | 445 | 35 | 1.006.325 | 251.582 |
| Broker | 6M | Full | 3 | 1 | 3 | 0 | 60/60 | 805 | 49 | 1.579.822 | 394.956 |
| Broker | 1Y | Full | 3 | 1 | 3 | 0 | 60/60 | 1.615 | 75 | 2.600.171 | 650.043 |
| Portfolio | 3M | Compact | 3 | 1 | 3 | 0 | 60/60 | 445 | 20 | 659.984 | 164.996 |
| Portfolio | 6M | Compact | 3 | 1 | 3 | 0 | 60/60 | 805 | 23 | 886.560 | 221.640 |
| Portfolio | 1Y | Compact | 3 | 1 | 3 | 0 | 60/60 | 1.615 | 29 | 1.360.396 | 340.099 |
| Portfolio | 3M | Standard | 3 | 1 | 3 | 0 | 60/60 | 445 | 26 | 820.212 | 205.053 |
| Portfolio | 6M | Standard | 3 | 1 | 3 | 0 | 60/60 | 805 | 33 | 1.178.112 | 294.528 |
| Portfolio | 1Y | Standard | 3 | 1 | 3 | 0 | 60/60 | 1.615 | 46 | 1.844.072 | 461.018 |
| Portfolio | 3M | Full | 3 | 1 | 3 | 0 | 60/60 | 445 | 35 | 1.042.097 | 260.525 |
| Portfolio | 6M | Full | 3 | 1 | 3 | 0 | 60/60 | 805 | 49 | 1.629.782 | 407.446 |
| Portfolio | 1Y | Full | 3 | 1 | 3 | 0 | 60/60 | 1.615 | 75 | 2.676.781 | 669.196 |

Il conteggio Broker=7 negli Asset probe e lo scope accessibile preparato per l'utente; il dataset tecnico resta single-asset. Il broker 5 della matrice non contiene duplicate legs; il caso multi-broker e coperto dai test reali e dal gate `portfolio_all`.

## Peso per sezione

### Totale 27 probe

| Sezione | Caratteri | Quota |
|---|---:|---:|
| Indicatori | 20.216.248 | **72,688%** |
| Eventi | 7.082.033 | **25,464%** |
| Prezzi tecnici | 455.448 | 1,638% |
| Breadth | 37.494 | 0,135% |
| Metadata/manifest top-level | 21.031 | 0,076% |

Le descrizioni semantiche sono cross-cutting e si sovrappongono ai blocchi sopra: 2.754.138 caratteri, 9,903% del totale.

### Full 1Y

| Scope | Prezzi | Indicatori | Eventi | Breadth | Metadata top |
|---|---:|---:|---:|---:|---:|
| Asset | 25.037 / 2,86% | 673.227 / 76,78% | 177.793 / 20,28% | — | 783 |
| Broker | — | 2.020.785 / 77,72% | 576.529 / 22,17% | 2.080 / 0,08% | 775 |
| Portfolio | 76.593 / 2,86% | 2.020.791 / 75,49% | 576.535 / 21,54% | 2.086 / 0,08% | 773 |

Portfolio Full 1Y:

| Sezione | Elementi | Costo medio |
|---|---:|---:|
| Prezzi | 3 asset, 225 bucket | 340,4 char/bucket |
| Indicatori | 60 istanze, 4.500 righe | 449,1 char/riga |
| Eventi | 1.615 eventi, 75 bucket | 351,3 char/evento payload; 357,0 incluso wrapper |
| Breadth | 12 stati | 173,8 char/stato |

## Peso degli indicatori

### Tutte le 20 istanze - Portfolio

Il confronto periodo usa Full. Il confronto detail usa 1Y.

| Instance | Signal | Col | Righe F3M/F6M/F1Y | Full 3M | Full 6M | Full 1Y | Compact 1Y | Standard 1Y | % block Full 1Y |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `bollinger_20_2` | BOLLINGER | 3 | 35/49/75 | 70.755 | 109.543 | 176.930 | 64.852 | 106.221 | 8,76% |
| `adx_14` | ADX | 3 | 35/49/75 | 69.233 | 107.368 | 174.387 | 63.585 | 103.525 | 8,63% |
| `ppo_12_26_9` | PPO | 3 | 35/49/75 | 69.645 | 108.068 | 171.256 | 63.944 | 103.428 | 8,47% |
| `macd_12_26_9` | MACD | 3 | 35/49/75 | 69.652 | 108.115 | 170.355 | 63.925 | 102.628 | 8,43% |
| `donchian_20` | DONCHIAN | 3 | 35/49/75 | 66.750 | 103.009 | 166.231 | 61.132 | 99.846 | 8,23% |
| `aroon_25` | AROON | 3 | 35/49/75 | 57.738 | 89.080 | 142.341 | 52.884 | 86.511 | 7,04% |
| `stoch_rsi_14_3` | STOCH_RSI | 2 | 35/49/75 | 47.731 | 73.228 | 116.421 | 43.167 | 68.936 | 5,76% |
| `natr_14` | NATR | 1 | 35/49/75 | 30.296 | 45.741 | 73.670 | 27.295 | 44.225 | 3,65% |
| `atr_14` | ATR | 1 | 35/49/75 | 30.077 | 45.495 | 73.461 | 27.120 | 44.018 | 3,64% |
| `rsi_14` | RSI | 1 | 35/49/75 | 30.164 | 45.564 | 73.417 | 27.172 | 44.060 | 3,63% |
| `mfi_14` | MFI | 1 | 35/49/75 | 30.014 | 45.399 | 73.249 | 27.031 | 43.900 | 3,62% |
| `roc_20` | ROC | 1 | 35/49/75 | 30.389 | 45.914 | 73.236 | 27.374 | 44.389 | 3,62% |
| `cci_20` | CCI | 1 | 35/49/75 | 30.319 | 45.861 | 73.156 | 27.375 | 44.364 | 3,62% |
| `kama_20` | KAMA | 1 | 35/49/75 | 30.373 | 45.878 | 73.122 | 27.370 | 44.350 | 3,62% |
| `ema_20` | EMA | 1 | 35/49/75 | 30.301 | 45.772 | 72.977 | 27.310 | 44.243 | 3,61% |
| `ema_50` | EMA | 1 | 35/49/75 | 30.288 | 45.765 | 69.873 | 26.524 | 42.674 | 3,46% |
| `sma_50` | SMA | 1 | 35/49/75 | 30.127 | 45.588 | 69.588 | 26.362 | 42.461 | 3,44% |
| `obv` | OBV | 1 | 35/49/75 | 28.172 | 42.420 | 69.150 | 25.440 | 41.846 | 3,42% |
| `ema_200` | EMA | 1 | 35/49/75 | 30.333 | 45.037 | 53.851 | 22.710 | 34.239 | 2,66% |
| `sma_200` | SMA | 1 | 35/49/75 | 30.199 | 44.859 | 53.673 | 22.606 | 34.041 | 2,66% |

Gli indicatori multi-colonna dominano. I primi cinque matrix-wide sono Bollinger, ADX, PPO, MACD e Donchian.

### Tipo di dato nel blocco indicatori

Portfolio Full 1Y, 60 tabelle:

| Tipo | Caratteri | Quota indicatori | Quota totale |
|---|---:|---:|---:|
| Righe storiche | 1.976.417 | **97,83%** | **73,84%** |
| Metadata senza righe | 43.447 | 2,15% | 1,62% |
| Metadata scalari | 11.538 | 0,57% | 0,43% |
| Definizioni colonne | 25.737 | 1,27% | 0,96% |
| Latest state | 7.927 | 0,39% | 0,30% |
| Descrizioni | 13.248 | 0,66% | 0,49% |

Le righe contengono observation count, first/min/max/last e date. Parametri, plugin version, reference levels, warnings e diagnostics non sono esportati: il loro costo corrente e zero, ma e anche un debito P1 di auditabilita.

Metadata e definizioni vengono ripetuti per ogni asset. Tuttavia lo scenario condiviso risparmia solo 0,82% sul Portfolio Full 1Y; nell'Asset singolo aggiunge 0,15% di overhead.

## Peso degli eventi

### Portfolio Full 1Y

| Misura | Valore |
|---|---:|
| Eventi totali | 1.615 |
| Caratteri blocco | 576.535 |
| Media payload/evento | 351,3 |
| Descrizioni ripetute | 161.635 |
| Descrizioni / blocco eventi | 28,0% |
| Descrizioni / payload totale | 6,0% |
| Duplicati esatti | 0 |
| Equivalenti semantici rilevati | 0 |

| Plugin | Eventi | Quota |
|---|---:|---:|
| STOCH_RSI | 776 | 48,0% |
| BOLLINGER | 262 | 16,2% |
| MACD | 180 | 11,1% |
| EMA | 166 | 10,3% |
| DONCHIAN | 130 | 8,0% |
| RSI | 56 | 3,5% |
| MFI | 24 | 1,5% |
| ADX | 21 | 1,3% |

Per asset: AAPL 480, BTC 520, ETH 615. Gli eventi weekend residui nel Portfolio sono reali per crypto, non carry-forward azionario.

### Policy prima/dopo su AAPL 1Y

Price input e output indicatori senza annotations hanno SHA-256 identico nei tre run.

| Policy | Eventi | Weekend | Minimo valore non-zero nel payload |
|---|---:|---:|---:|
| Legacy: unobserved, epsilon 0 | 516 | 52 | `7.105427357601002e-15` |
| Observed-only, epsilon 0 | 480 | 0 | `4.263256414560601e-14` |
| Corrente observed-only + epsilon | 480 | 0 | `3.2566542055671257e-15` |

| Transizione | Net | Rimossi | Aggiunti | Weekend delta |
|---|---:|---:|---:|---:|
| Legacy -> observed-only | -36 | 66 | 30 | -52 |
| Observed-only -> epsilon | 0 | 4 | 4 | 0 |

Observed-only elimina tutti i 52 eventi weekend e preserva eventi reali spostandoli sulla successiva osservazione. L'epsilon sostituisce quattro cross `stoch_rsi_k_d` senza cambiare il totale: modifica lato/data di conferma, non il numero netto.

Un valore serializzato sotto epsilon puo restare nell'evento quando rappresenta la data di equality agganciata a un cross reale successivo. Epsilon governa la detection, non arrotonda il payload.

Il riferimento storico era 517 eventi; l'emulazione legacy sul DB pulito corrente produce 516. Weekend e residuo `7.105e-15` sono riprodotti esattamente; resta una deriva di un evento rispetto all'audit storico.

## Simulazioni offline

Tutti gli scenari mantengono il 100% degli eventi.

### Full 1Y

| Scenario | Righe indicatori | Asset chars/token | Broker chars/token | Portfolio chars/token |
|---|---:|---:|---:|---:|
| A baseline | 100% | 876.842 / 219.211 | 2.600.171 / 650.043 | 2.676.781 / 669.196 |
| B N=1 | 1,33% | 232.685 / 58.172 (-73,46%) | 666.565 / 166.642 (-74,36%) | 743.175 / 185.794 (-72,24%) |
| B N=3 | 4,00% | 241.480 / 60.370 (-72,46%) | 692.951 / 173.238 (-73,35%) | 769.561 / 192.391 (-71,25%) |
| B N=5 | 6,67% | 250.279 / 62.570 (-71,46%) | 719.317 / 179.830 (-72,34%) | 795.927 / 198.982 (-70,27%) |
| B N=10 | 13,33% | 272.265 / 68.067 (-68,95%) | 785.230 / 196.308 (-69,80%) | 861.840 / 215.460 (-67,80%) |
| B N=15 | 20,00% | 294.195 / 73.549 (-66,45%) | 851.069 / 212.768 (-67,27%) | 927.679 / 231.920 (-65,34%) |
| C primary full | 25,00% | 369.610 / 92.403 (-57,85%) | 1.076.755 / 269.189 (-58,59%) | 1.153.365 / 288.342 (-56,91%) |
| D metadata shared | 100% | 878.190 / 219.548 (+0,15%) | 2.578.169 / 644.543 (-0,85%) | 2.654.779 / 663.695 (-0,82%) |
| E latest+stats+events | 0% | 228.100 / 57.025 (-73,99%) | 652.830 / 163.208 (-74,89%) | 729.440 / 182.360 (-72,75%) |

Scenario C usa come candidato, non policy:

- EMA20/50/200;
- RSI14;
- MACD.

### Portfolio Full per periodo

| Scenario | 3M | 6M | 1Y |
|---|---:|---:|---:|
| B N=5 | 338.987 (-67,47%) | 481.567 (-70,45%) | 795.927 (-70,27%) |
| C primary | 446.698 (-57,13%) | 688.767 (-57,74%) | 1.153.365 (-56,91%) |
| D metadata shared | 1.020.095 (-2,11%) | 1.607.780 (-1,35%) | 2.654.779 (-0,82%) |
| E latest+stats+events | 272.512 (-73,85%) | 415.085 (-74,53%) | 729.440 (-72,75%) |

### Lettura degli scenari

- **A**: baseline completa; massima informazione, densita non sostenibile.
- **B**: mantiene latest, summary globale, ultimi N bucket ed eventi. E il miglior compromesso generale.
- **C**: conserva storia completa per un sottoinsieme, ma il risparmio e inferiore a B.
- **D**: metadata condivisi da soli non risolvono il problema.
- **E**: massimo risparmio conservando eventi, latest e statistiche; perde ogni micro-traiettoria recente.

## Valore informativo per famiglia

Legenda:

- A valore corrente;
- B stato corrente;
- C estremi nel periodo;
- D andamento approssimativo;
- E storia completa bucketizzata;
- F eventi/transizioni;
- G dati utili solo a ricalcolare.

| Famiglia | Informazione utile al LLM | Storia completa |
|---|---|---|
| Prezzo/rate | A, C, D, E, F | utile nei data export; non sempre nei prompt secondari |
| EMA/SMA/KAMA | A, B, C, D, F | raramente necessaria; backend ha gia calcolato |
| Aroon/ADX/Donchian | A, B, C, F; D opzionale | bassa utilita marginale |
| RSI/MFI/StochRSI/CCI/ROC | A, B, C, D, F | ultimi N + eventi normalmente sufficienti |
| MACD/PPO | A, B, C, D, F | ultimi N utili; full non necessaria per ricalcolo |
| Bollinger | A, B, C, D, F | ultimi N utili per posizione/banda |
| ATR/NATR | A, C, D | full generalmente ridondante |
| OBV | A, D | una breve storia aiuta; full utile solo per analisi dedicate |
| Drawdown futuro | A, B, C, F su episodi | usare geometria Risk, non ricalcolo da bucket |

I dati G non devono essere esportati solo per permettere all'LLM di rifare un indicatore gia calcolato deterministicamente dal backend.

## Valore per obiettivo

| Obiettivo | Tecnica necessaria | Scenario candidato |
|---|---|---|
| Asset Trend Analysis | prezzo ricco, latest/state, estremi, ultimi punti, eventi | B N=5/10 |
| Portfolio Technical Breadth | stato corrente, denominatori, peso, data, eventi aggregati | E; prima completare breadth P1 |
| Broker Technical Context | latest/stats/eventi; breve trend per principali | E o B N=3/5 |
| FX Trend Review | rate history, principali trend/momentum, eventi | prezzo/rate ricco + B N=5 |
| FX Conversion Timing | latest, posizione nel periodo, trend breve, eventi | B N=5 o E |
| FX Exposure Impact | tecnica solo contesto secondario | E |
| Data-only technical export | output piu ricco e auditabile | B N=10/15 o baseline esplicita |
| All-data export | tecnica secondaria rispetto ai dati finanziari | E o B N=3/5 |

Non e raccomandata una sola policy indiscriminata.

## Raccomandazione non implementata

### Default candidato

**B N=5**:

- full price/rate history secondo il detail;
- per indicatore: latest state, statistiche di periodo con date, ultimi 5 bucket;
- tutti gli eventi reali;
- metadata auditabili una volta disponibili.

Motivo:

- riduce circa il 70-72%;
- costa solo circa 2,5 punti percentuali piu di E;
- conserva cinque punti recenti, quindi una direzione locale leggibile;
- N=3 risparmia solo circa un punto ulteriore ma elimina il 40% dei punti recenti conservati.

### Variante per tecnica secondaria

**E** per Portfolio/Broker/FX impact e all-data quando la tecnica e solo contesto:

- latest;
- first/min/max/last e date;
- stato;
- eventi completi;
- nessuna storia dettagliata degli indicatori.

Prima di implementare serve una decisione prodotto separata per data export e prompt analysis.

## Stato degli altri problemi del deep audit

| Problema | Stato | Nota |
|---|---|---|
| Omissioni optional invisibili | unchanged | manifest non espone omissioni/failure optional |
| Indicator diagnostics | unchanged | params/version/status/warmup/warnings assenti |
| Denominatori breadth | partially resolved | universo/pesi multi-broker corretti; mancano evaluated count/weight, state date, category |
| FIFO in-transit | unchanged | custody/source/destination/timeline non aggiunti |
| Broker Review/FIFO overlap | still requires product decision | all-lot dump vs summary dedicato |
| Cost Efficiency | still requires product decision | mancano activity/capital denominators |
| Peso Portfolio dell'asset | unchanged | Position Review continua senza portfolio weight |
| FX exposure impact | unchanged | sensitivity, nomi e native amount non aggiunti |
| Coupling FX overview/technical | unchanged | HTTP FX tecnico continua a 503 con history corta |
| Legacy task/profile stack | unchanged | ancora separato dal runtime pubblico ma presente |
| Date extrema bucket | resolved as side effect | aggiunte a price e performance bucket |

### Piano proposto per FX coupling

1. introdurre una risorsa current-rate visibile senza warm-up;
2. usare quella risorsa in `fx.overview`;
3. mantenere il warm-up solo in `fx.market_technical`;
4. rendere il fallimento tecnico separabile dalle informazioni overview/exposure;
5. non far dipendere `fx.exposure_impact` dalla disponibilita della storia antica.

Non e stato implementato in modo opportunistico.

## Gate HTTP/DB reale

| Probe | HTTP | Risultato |
|---|---:|---|
| Catalog | 200 | 18 dataset, 16 analisi, Drawdown assente |
| Asset technical 3M Compact | 200 | 3 sezioni |
| Broker 5 technical 3M Compact | 200 | 3 sezioni |
| Portfolio broker 5 technical 3M Compact | 200 | 4 sezioni, 3 asset |
| Portfolio completo technical 3M Compact | 200 | 11 righe considerate, 7 asset unici, pesi=1 |
| FX EUR/USD technical 3M Compact | 503 | `snapshot_source_failure`, componente `fx.rate_ohlc` |

Il 503 FX conferma il coupling warm-up gia noto; non deriva dalle quattro correzioni implementate.

## Verifiche

| Gate | Esito |
|---|---|
| AI Export service runtime | 899 passed |
| Signal annotations | 25 passed |
| Asset signal service | 14 passed |
| AI Export schemas | 112 passed |
| AI Export API | 14 passed |
| Frontend AI Export unit | 18 passed |
| Prompt renderer dopo rimozione Drawdown wording | 4 passed |
| Svelte check | 0 errori, 0 warning |
| Frontend build | completata |
| i18n audit | 2.214/2.214 in EN/IT/FR/ES; 0 missing |
| API sync | completata |
| Density matrix | 27/27 riusciti |
| Multi-broker DB integration | stesso asset in due broker, no duplicate/no failure |
| HTTP reale | Asset/Broker/Portfolio 200; FX 503 noto e documentato |

## Modifiche intenzionalmente aperte

- nessuna segmentazione Parte 1/N;
- nessun truncation o silent removal;
- nessuna policy N applicata al formato pubblico;
- nessuna condivisione metadata implementata;
- nessuna deduplica delle descrizioni evento;
- nessuna integrazione `RISK_DRAWDOWN`;
- nessuna correzione P1 opportunistica;
- nessun disaccoppiamento FX overview/technical;
- nessuna rimozione del legacy stack.
