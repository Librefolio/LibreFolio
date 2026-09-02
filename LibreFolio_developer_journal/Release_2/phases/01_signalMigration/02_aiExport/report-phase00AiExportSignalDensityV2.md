# Phase 00 — AI Export Signal Density V2

**Data**: 30 luglio 2026

**Stato**: implementazione completata; probe richiesti 27/27 validi; 9/9 probe FX opzionali falliti per coupling noto

**Contratto pubblico**: beta v1 migrata in place

**Probe V2**: [probe-phase00AiExportSignalDensityV2.json](probe-phase00AiExportSignalDensityV2.json)

**Baseline**: [probe-phase00AiExportTechnicalDensity.json](probe-phase00AiExportTechnicalDensity.json)

**Report precedente**: [report-phase00AiExportSizeAndTechnicalDensity.md](report-phase00AiExportSizeAndTechnicalDensity.md)

---

## 1. Executive summary

1. AI Export resta **beta**. Componenti, dataset, analisi, sampling, manifest e response contract sono migrati **in place come v1**.
2. Non esistono runtime legacy, fallback silenzioso, payload parallelo o doppia produzione v1/v2.
3. La densità numerica degli indicatori ora dipende da:

   ```text
   detail_level + temporal_class posseduta dal plugin → P, M, K
   ```

4. Prezzi Asset e rate FX non usano la classe temporale: mantengono la policy preesistente dipendente solo dal detail.
5. Le 18 combinazioni ufficiali `3 detail × 6 classi` coincidono con la specifica:
   - **18/18** combinazioni valide;
   - **54/54** conteggi teoria/runtime coincidenti per 90, 180 e 365 giorni;
   - **0** drift di `P`, `M` o `K`.
6. La selezione eventi è deterministica per `entity_id + annotation_key`:
   - tutti gli eventi degli ultimi 30 giorni di calendario;
   - almeno gli ultimi 20, se disponibili;
   - nessun ranking;
   - nessun cap aggiuntivo sugli eventi recenti.
7. Matrice reale richiesta:
   - **27/27** Asset/Broker/Portfolio riusciti;
   - **9/9** FX opzionali falliti per il noto coupling warm-up di `fx.rate_ohlc`;
   - i fallimenti FX sono non fatali per il probe e non sono stati corretti opportunisticamente.
8. Caso massimo `portfolio.technical`, Full, 1Y:

   | Misura | Prima | Dopo | Riduzione |
   |---|---:|---:|---:|
   | Caratteri | 2.676.781 | 1.990.718 | 686.063 / 25,630151% |
   | Token stimati | 669.196 | 497.680 | 171.516 / 25,630159% |
   | Righe indicatore | 4.500 | 3.456 | 1.044 / 23,200000% |
   | Eventi rilevati | 1.615 | 1.615 | invariati |
   | Eventi esportati | 1.615 | 707 | 908 omessi deterministicamente |

9. Il blocco indicatori scende di **402.829 caratteri / 19,934224%**.
10. Il blocco eventi scende di **286.322 caratteri / 49,662553%**.
11. Il payload totale scende meno della somma lorda dei due risparmi perché il manifest top-level cresce di **3.088 caratteri**.
12. Non è corretto dire che la policy conserva ogni evento storico. Conserva:
    - selezione deterministica;
    - identità degli eventi selezionati;
    - conteggi completi rilevati/recenti/esportati;
    - range temporali rilevati ed esportati.

---

## 2. Provenienza e caveat di misura

| Campo | Valore |
|---|---|
| Probe schema | `2.0.0` diagnostico, non versione contratto pubblico |
| Generated at | `2026-07-30T15:38:15.943952+00:00` |
| Runtime | `AiExportSnapshotService` reale |
| DB | `backend/data/test/sqlite/app.db` |
| Modalità | test mode |
| Python | 3.13.14 |
| Piattaforma | macOS ARM64 |
| Serializer | `backend.app.services.ai_export.telemetry.canonical_json` |
| Stima token | `chars_div_4_v1` |
| Catalogo | v1, schema v1, 18 dataset, 16 analisi |
| Snapshot | 2026-07-30 |
| Target currency | USD |
| Utente | `e2e_test_user` |

Caveat:

- i probe dimensionali 3M e 6M usano periodi inclusivi reali di **91** e **181** giorni;
- la verifica normativa teoria/runtime usa esattamente **90**, **180** e **365** giorni;
- nel payload misurato caratteri e byte UTF-8 coincidono;
- tutte le riduzioni baseline riportate sono misure canoniche reali, non stime lineari;
- i risultati HTTP reali possono differire lievemente dalla matrice deterministica per bootstrap runtime dei prezzi;
- il probe FX non produce payload misurabile: il fallimento avviene sul componente richiesto `fx.rate_ohlc`.

---

## 3. Modifiche implementate

### 3.1 Classi temporali possedute dai plugin

È stato introdotto `SignalTemporalClass`:

```text
very_fast
fast
medium_fast
medium
slow
very_slow
```

Ogni plugin esportabile dichiara `ai_export_temporal_rules`.

Il plugin possiede:

- significato semantico della velocità;
- regole fisse o match esatto sui parametri;
- source of truth pubblicata nel catalogo runtime.

Il plugin non conosce:

- Compact, Standard o Full;
- formula;
- valori `P/M/K`;
- durata richiesta;
- numero di bucket.

`resolve_ai_export_temporal_class()`:

- valida i parametri tramite il model Pydantic del plugin;
- normalizza i valori JSON;
- richiede esattamente una regola compatibile;
- fallisce su zero match;
- fallisce su match ambigui;
- non applica fallback per signal code.

EMA e SMA usano match esatto sul periodo. Gli altri plugin curati usano una regola fissa.

### 3.2 Policy centrale

`BucketingPolicy.for_indicator(detail_level, temporal_class)` risolve la riga ufficiale della matrice.

La policy:

- usa `Decimal`;
- applica `ROUND_HALF_UP`;
- costruisce confini deterministici;
- limita la larghezza a `K`;
- chiude l'ultimo bucket esattamente sul limite del periodo;
- non crea gap o overlap.

### 3.3 Tabelle indicatori

Ogni istanza produce una tabella row-oriented con:

- `temporal_class`;
- colonne canoniche;
- `period_summary` sull'intero periodo;
- latest value/date per colonna;
- righe bucketizzate contigue;
- date reali per first/min/max/last;
- observation count.

Gli indicatori multi-output condividono una sola griglia temporale per istanza.

La bucketizzazione non modifica:

- calculation range;
- warm-up;
- validazione input/output;
- applicabilità;
- stato latest;
- summary globale;
- rilevazione degli eventi.

### 3.4 Selezione eventi

Gli eventi vengono:

1. calcolati su osservazioni originali;
2. validati;
3. filtrati observed-only;
4. verificati con epsilon e gap rules;
5. deduplicati semanticamente;
6. raggruppati per `entity_id + annotation_key`;
7. selezionati con policy 30 giorni/minimo 20;
8. riordinati nel formato pubblico deterministico;
9. assegnati ai bucket evento del detail.

Portfolio e Broker mantengono l'identità Asset originaria, per esempio `asset:6`.

### 3.5 Manifest

Il runtime registra nel `BuildContext`:

- policy prezzo effettivamente usata;
- policy per ogni istanza indicatore;
- uso della selezione eventi.

La response include, quando applicabili:

- `technical_sampling`;
- `event_selection`.

Il frontend inserisce entrambi nel blocco:

```text
Snapshot Metadata and Dataset Manifest
```

---

## 4. File e simboli principali

| Area | File | Simboli/responsabilità |
|---|---|---|
| Enum e catalogo | `backend/app/schemas/signals.py` | `SignalTemporalClass`, `SignalAiExportTemporalRule`, `SignalCatalogDefinition.ai_export_temporal_rules` |
| Contratto plugin | `backend/app/services/signal_plugins/base.py` | `ai_export_temporal_rules`, `resolve_ai_export_temporal_class()`, validazione regole |
| Classificazione ufficiale | `backend/app/services/signal_plugins/{ema,sma,rsi,mfi,stoch_rsi,cci,roc,atr,natr,macd,ppo,bollinger,donchian,kama,aroon,adx,obv}.py` | regole fisse o parameter-matched |
| Matrice centrale | `backend/app/services/ai_export/temporal/policy.py` | `_INDICATOR_POLICY_PARAMETERS`, `BucketingPolicy.for_indicator()` |
| Piano indicatore | `backend/app/services/ai_export/dependencies.py` | `build_indicator_bucket_plan_for_scope()`, diagnostica sampling nel `BuildContext` |
| Payload indicatore/evento | `backend/app/services/ai_export/components/technical_payloads.py` | `IndicatorTablePayload`, `TechnicalEventSelectionSummary`, `TechnicalEventsPayload` |
| Costruzione indicatori | `backend/app/services/ai_export/components/technical_shared.py` | `build_indicator_table_payloads()` |
| Selezione eventi | stesso file | `select_technical_events()`, `build_events_payload()` |
| Identità eventi Asset/FX | `backend/app/services/ai_export/components/asset_fx_technical.py` | builder stati/eventi single target |
| Identità Portfolio/Broker | `backend/app/services/ai_export/components/portfolio_broker_technical.py` | `_build_universe_technical_events()` |
| Schema manifest | `backend/app/schemas/ai_export_runtime.py` | `AiExportPriceSamplingPolicy`, `AiExportIndicatorSamplingPolicy`, `AiExportTechnicalSamplingManifest`, `AiExportEventSelectionManifest` |
| Manifest runtime | `backend/app/services/ai_export/runtime_service.py` | `_technical_sampling_manifest()`, response v1 |
| Prompt manifest | `frontend/src/lib/features/ai-export/templates/promptRenderer.ts` | `renderSnapshotMetadata()` |
| Probe | `backend/test_scripts/diagnostics/ai_export_signal_density_v2_probe.py` | matrice, teoria/runtime, peso indicatori, eventi, baseline |

---

## 5. Formula effettivamente implementata

Siano:

- `x`: distanza intera in giorni di calendario da `snapshot_as_of`;
- `P`: esponente di forma;
- `M`: offset di metà transizione dopo la rampa giornaliera;
- `K`: larghezza massima asintotica;
- `T`: durata totale richiesta in giorni.

Funzione continua:

$$
f(x;P,M,K)
=
1+(K-1)
\frac{\max(x-7,0)^P}
{M^P+\max(x-7,0)^P}
$$

Delta intero:

$$
D(x;P,M,K)
=
\max\left(
1,
\operatorname{round}_{half\text{-}up}[f(x;P,M,K)]
\right)
$$

Confini:

$$
x_0=0
$$

$$
x_{n+1}
=
\min\left(T,\ x_n+D(x_n;P,M,K)\right)
$$

Ogni intervallo half-open di offset viene tradotto in un bucket calendario.

Implementazione:

```text
base = max(x - 7, 0)
f = 1 + (K - 1) * base^P / (M^P + base^P)
D = max(1, Decimal(f).quantize(1, ROUND_HALF_UP))
```

Proprietà runtime verificate:

- `D(x)=1` nella rampa recente;
- delta positivo;
- monotonicità della formula;
- larghezza `<=K`;
- copertura completa;
- ultimo confine esatto;
- nessun gap;
- nessun overlap;
- determinismo.

---

## 6. Contratto temporale plugin-owned e classificazione iniziale

| Istanza | Segnale | Classe | Regola |
|---|---|---|---|
| `stoch_rsi_14_3` | StochRSI(14,3) | Very Fast | fissa |
| `rsi_14` | RSI(14) | Very Fast | fissa |
| `mfi_14` | MFI(14) | Very Fast | fissa |
| `cci_20` | CCI(20) | Fast | fissa |
| `roc_20` | ROC(20) | Fast | fissa |
| `atr_14` | ATR(14) | Fast | fissa |
| `natr_14` | NATR(14) | Fast | fissa |
| `macd_12_26_9` | MACD(12,26,9) | Medium Fast | fissa |
| `ppo_12_26_9` | PPO(12,26,9) | Medium Fast | fissa |
| `bollinger_20_2` | Bollinger(20,2) | Medium Fast | fissa |
| `donchian_20` | Donchian(20) | Medium Fast | fissa |
| `ema_20` | EMA(20) | Medium | `period=20` |
| `kama_20` | KAMA(20) | Medium | fissa |
| `aroon_25` | Aroon(25) | Medium | fissa |
| `adx_14` | ADX(14) | Medium | fissa |
| `obv` | OBV | Medium | fissa |
| `ema_50` | EMA(50) | Slow | `period=50` |
| `sma_50` | SMA(50) | Slow | `period=50` |
| `ema_200` | EMA(200) | Very Slow | `period=200` |
| `sma_200` | SMA(200) | Very Slow | `period=200` |

FX riusa il sottoinsieme curato di 12 istanze dichiarato nella Developer Guide. Il probe runtime FX non raggiunge la serializzazione per il fallimento noto di `fx.rate_ohlc`.

---

## 7. Matrice ufficiale: teoria contro runtime

Formato conteggio: `teorico/runtime`.

| Detail | Classe | P/M/K | 90d | 180d | 365d |
|---|---|---:|---:|---:|---:|
| Compact | Very Fast | 2/30/30 | 20/20 | 23/23 | 29/29 |
| Compact | Fast | 2/25/35 | 18/18 | 21/21 | 26/26 |
| Compact | Medium Fast | 2/20/42 | 16/16 | 18/18 | 23/23 |
| Compact | Medium | 2/10/42 | 14/14 | 16/16 | 20/20 |
| Compact | Slow | 2/5/49 | 12/12 | 14/14 | 17/17 |
| Compact | Very Slow | 2/5/84 | 11/11 | 12/12 | 14/14 |
| Standard | Very Fast | 2/30/14 | 26/26 | 33/33 | 46/46 |
| Standard | Fast | 2/21/15 | 23/23 | 29/29 | 41/41 |
| Standard | Medium Fast | 2/20/17 | 21/21 | 26/26 | 37/37 |
| Standard | Medium | 2/15/20 | 18/18 | 23/23 | 32/32 |
| Standard | Slow | 2/10/22 | 16/16 | 20/20 | 28/28 |
| Standard | Very Slow | 2/5/28 | 13/13 | 16/16 | 23/23 |
| Full | Very Fast | 2/30/7 | 35/35 | 49/49 | 75/75 |
| Full | Fast | 2/28/8 | 32/32 | 44/44 | 67/67 |
| Full | Medium Fast | 2/23/9 | 28/28 | 38/38 | 59/59 |
| Full | Medium | 2/16/10 | 24/24 | 33/33 | 51/51 |
| Full | Slow | 2/10/11 | 21/21 | 29/29 | 46/46 |
| Full | Very Slow | 2/9/14 | 18/18 | 24/24 | 38/38 |

Esito:

| Controllo | Risultato |
|---|---:|
| Combinazioni attese/eseguite | 18/18 |
| Durate verificate | 54 |
| Conteggi coincidenti | 54/54 |
| Drift P | 0 |
| Drift M | 0 |
| Drift K | 0 |
| Matrice valida | sì |

Very Fast coincide con la baseline detail-only. Densità per classe e detail resta monotona nei periodi normativi.

---

## 8. Distribuzione temporale effettiva a 365 giorni

Legenda:

- `Offset non daily`: offset iniziale del primo bucket con ampiezza >1;
- `Data`: start date reale di quel bucket;
- `Daily`: bucket giornalieri consecutivi dal più recente;
- `D≥n`: primo offset dove la formula raggiunge almeno `n`;
- `D≥K`: primo offset dove raggiunge `K`;
- `—`: soglia 14 non applicabile perché `K<14`;
- `Max`: massima ampiezza reale nel periodo.

| Detail | Classe | P/M/K | Bucket | Offset non daily / data | Daily | D≥2 | D≥3 | D≥5 | D≥7 | D≥14 | D≥K | Max |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact | Very Fast | 2/30/30 | 29 | 11 / 2026-07-18 | 11 | 11 | 15 | 19 | 22 | 34 | 234 | 30 |
| Compact | Fast | 2/25/35 | 26 | 11 / 2026-07-18 | 11 | 11 | 13 | 16 | 18 | 27 | 212 | 35 |
| Compact | Medium Fast | 2/20/42 | 23 | 10 / 2026-07-19 | 10 | 10 | 11 | 14 | 15 | 21 | 187 | 42 |
| Compact | Medium | 2/10/42 | 20 | 9 / 2026-07-19 | 9 | 9 | 9 | 11 | 11 | 14 | 97 | 42 |
| Compact | Slow | 2/5/49 | 17 | 8 / 2026-07-20 | 8 | 8 | 8 | 9 | 9 | 10 | 56 | 49 |
| Compact | Very Slow | 2/5/84 | 14 | 8 / 2026-07-19 | 8 | 8 | 8 | 9 | 9 | 10 | 72 | 84 |
| Standard | Very Fast | 2/30/14 | 46 | 13 / 2026-07-16 | 13 | 13 | 18 | 26 | 33 | 157 | 157 | 14 |
| Standard | Fast | 2/21/15 | 41 | 12 / 2026-07-17 | 12 | 12 | 15 | 20 | 24 | 68 | 117 | 15 |
| Standard | Medium Fast | 2/20/17 | 37 | 11 / 2026-07-18 | 11 | 11 | 14 | 18 | 22 | 45 | 119 | 17 |
| Standard | Medium | 2/15/20 | 32 | 10 / 2026-07-19 | 10 | 10 | 12 | 15 | 17 | 28 | 99 | 20 |
| Standard | Slow | 2/10/22 | 28 | 9 / 2026-07-20 | 9 | 9 | 10 | 12 | 13 | 20 | 72 | 22 |
| Standard | Very Slow | 2/5/28 | 23 | 8 / 2026-07-21 | 8 | 8 | 9 | 9 | 10 | 12 | 44 | 28 |
| Full | Very Fast | 2/30/7 | 75 | 17 / 2026-07-12 | 17 | 17 | 25 | 43 | 107 | — | 107 | 7 |
| Full | Fast | 2/28/8 | 67 | 15 / 2026-07-14 | 15 | 15 | 22 | 35 | 61 | — | 108 | 8 |
| Full | Medium Fast | 2/23/9 | 59 | 13 / 2026-07-16 | 13 | 13 | 19 | 28 | 42 | — | 97 | 9 |
| Full | Medium | 2/16/10 | 51 | 11 / 2026-07-18 | 11 | 11 | 15 | 20 | 28 | — | 73 | 10 |
| Full | Slow | 2/10/11 | 46 | 10 / 2026-07-19 | 10 | 10 | 12 | 15 | 19 | — | 51 | 11 |
| Full | Very Slow | 2/9/14 | 38 | 9 / 2026-07-20 | 9 | 9 | 11 | 13 | 15 | 52 | 52 | 14 |

Osservazione importante: il vincolo `D(x)=1` per `0≤x≤7` garantisce almeno la settimana recente giornaliera, ma l'arrotondamento può estendere la sequenza giornaliera oltre sette bucket. I valori reali sopra vanno da 8 a 17 bucket giornalieri consecutivi.

---

## 9. Matrice dimensionale richiesta: 27 probe

`Righe` indica righe bucketizzate degli indicatori. `Eventi` usa `rilevati/esportati/omessi`.

| Scope | Periodo | Detail | Caratteri | Token | Righe | Eventi |
|---|---|---|---:|---:|---:|---:|
| Asset | 3M | Compact | 191.612 | 47.903 | 312 | 128/117/11 |
| Asset | 6M | Compact | 241.104 | 60.276 | 357 | 257/181/76 |
| Asset | 1Y | Compact | 311.810 | 77.953 | 445 | 480/245/235 |
| Asset | 3M | Standard | 236.524 | 59.131 | 402 | 128/117/11 |
| Asset | 6M | Standard | 319.871 | 79.968 | 508 | 257/181/76 |
| Asset | 1Y | Standard | 450.982 | 112.746 | 712 | 480/245/235 |
| Asset | 3M | Full | 302.139 | 75.535 | 543 | 128/117/11 |
| Asset | 6M | Full | 440.533 | 110.134 | 746 | 257/181/76 |
| Asset | 1Y | Full | 672.896 | 168.224 | 1.152 | 480/245/235 |
| Broker | 3M | Compact | 556.681 | 139.171 | 936 | 445/381/64 |
| Broker | 6M | Compact | 695.053 | 173.764 | 1.071 | 805/557/248 |
| Broker | 1Y | Compact | 884.792 | 221.198 | 1.335 | 1.615/707/908 |
| Broker | 3M | Standard | 684.223 | 171.056 | 1.206 | 445/381/64 |
| Broker | 6M | Standard | 919.610 | 229.903 | 1.524 | 805/557/248 |
| Broker | 1Y | Standard | 1.282.683 | 320.671 | 2.136 | 1.615/707/908 |
| Broker | 3M | Full | 870.552 | 217.638 | 1.629 | 445/381/64 |
| Broker | 6M | Full | 1.263.014 | 315.754 | 2.238 | 805/557/248 |
| Broker | 1Y | Full | 1.914.052 | 478.513 | 3.456 | 1.615/707/908 |
| Portfolio | 3M | Compact | 577.372 | 144.343 | 936 | 445/381/64 |
| Portfolio | 6M | Compact | 718.825 | 179.707 | 1.071 | 805/557/248 |
| Portfolio | 1Y | Compact | 914.717 | 228.680 | 1.335 | 1.615/707/908 |
| Portfolio | 3M | Standard | 710.907 | 177.727 | 1.206 | 445/381/64 |
| Portfolio | 6M | Standard | 953.478 | 238.370 | 1.524 | 805/557/248 |
| Portfolio | 1Y | Standard | 1.329.893 | 332.474 | 2.136 | 1.615/707/908 |
| Portfolio | 3M | Full | 906.380 | 226.595 | 1.629 | 445/381/64 |
| Portfolio | 6M | Full | 1.313.030 | 328.258 | 2.238 | 805/557/248 |
| Portfolio | 1Y | Full | 1.990.718 | 497.680 | 3.456 | 1.615/707/908 |

Totali sui 27 probe:

| Misura | Totale | Min | Max |
|---|---:|---:|---:|
| Caratteri | 21.653.451 | 191.612 | 1.990.718 |
| Token | 5.413.372 | 47.903 | 497.680 |
| Righe indicatore | 36.239 | 312 | 3.456 |
| Eventi rilevati | 19.785 | 128 | 1.615 |
| Eventi esportati | 11.499 | 117 | 707 |

---

## 10. Portfolio Full 1Y: baseline e decomposizione esatta

### 10.1 Prima/dopo per sezione

| Sezione | Prima | Dopo | Delta |
|---|---:|---:|---:|
| Prezzi tecnici | 76.593 | 76.593 | 0 |
| Indicatori | 2.020.791 | 1.617.962 | -402.829 |
| Eventi | 576.535 | 290.213 | -286.322 |
| Breadth | 2.086 | 2.086 | 0 |
| Metadata/manifest top-level | 773 | 3.861 | +3.088 |
| Wrapper non attribuito | 3 | 3 | 0 |
| **Totale** | **2.676.781** | **1.990.718** | **-686.063** |

### 10.2 Riduzioni normative richieste

| Misura | Riduzione assoluta | Riduzione percentuale |
|---|---:|---:|
| Sezione indicatori | 402.829 | 19,934224% |
| Sezione eventi | 286.322 | 49,662553% |
| Indicatori + eventi | 689.151 | 25,745513% della baseline totale |
| Payload totale | 686.063 | 25,630151% |

La differenza tra `689.151` e `686.063` è esattamente **3.088** caratteri: nuovo overhead top-level.

### 10.3 Overhead V2 osservato

| Campo | Caratteri |
|---|---:|
| `technical_sampling` manifest | 2.927 |
| `event_selection` manifest | 120 |
| `selection_summaries` eventi | 16.958 |
| `period_summary` indicatori | 26.001 |

Questi valori si sovrappongono alle rispettive sezioni:

- i due manifest appartengono al top-level;
- `selection_summaries` appartiene al blocco eventi;
- `period_summary` appartiene al blocco indicatori.

Non devono essere sommati nuovamente al residuo esatto.

### 10.4 Quote dopo la modifica

| Sezione | Caratteri | Quota payload |
|---|---:|---:|
| Indicatori | 1.617.962 | 81,275299% |
| Eventi | 290.213 | 14,578308% |
| Prezzi | 76.593 | 3,847506% |
| Metadata/manifest | 3.861 | 0,193950% |
| Breadth | 2.086 | 0,104786% |

La compressione eventi rende il blocco indicatori ancora più dominante in quota relativa, pur essendo più piccolo in valore assoluto.

---

## 11. Peso per classe temporale

Portfolio Full 1Y, 3 asset. `Istanze` conta le istanze asset-specifiche.

| Classe | Istanze | Righe | Caratteri | Token | % indicatori | % payload |
|---|---:|---:|---:|---:|---:|---:|
| Medium Fast | 12 | 708 | 557.701 | 139.430 | 34,4694% | 28,0151% |
| Medium | 15 | 765 | 380.274 | 95.072 | 23,5033% | 19,1024% |
| Very Fast | 9 | 675 | 266.662 | 66.668 | 16,4814% | 13,3953% |
| Fast | 12 | 804 | 266.586 | 66.651 | 16,4767% | 13,3914% |
| Slow | 6 | 276 | 89.026 | 22.259 | 5,5024% | 4,4721% |
| Very Slow | 6 | 228 | 57.266 | 14.319 | 3,5394% | 2,8767% |

Lettura:

- Medium Fast pesa più di ogni altra classe perché concentra quattro indicatori a tre colonne;
- Very Fast e Fast hanno peso quasi identico, ma per motivi diversi:
  - Very Fast mantiene 75 bucket;
  - Fast scende a 67 bucket ma contiene quattro istanze;
- Very Slow mostra la riduzione più forte della storia numerica.

---

## 12. Peso dei 20 indicatori dopo la modifica

Valori aggregati sui 3 asset del Portfolio Full 1Y.

| Indicatore | Classe | Colonne | Bucket/asset | Righe | Caratteri | Token | % indicatori | Riduzione vs baseline |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Bollinger | Medium Fast | 3 | 59 | 177 | 144.518 | 36.130 | 8,93% | 18,3191% |
| PPO | Medium Fast | 3 | 59 | 177 | 139.187 | 34.798 | 8,60% | 18,7258% |
| MACD | Medium Fast | 3 | 59 | 177 | 138.362 | 34.592 | 8,55% | 18,7802% |
| Donchian | Medium Fast | 3 | 59 | 177 | 135.634 | 33.910 | 8,38% | 18,4063% |
| ADX | Medium | 3 | 51 | 153 | 124.789 | 31.198 | 7,71% | 28,4413% |
| StochRSI | Very Fast | 2 | 75 | 225 | 118.109 | 29.528 | 7,30% | -1,4499% |
| Aroon | Medium | 3 | 51 | 153 | 102.682 | 25.671 | 6,35% | 27,8620% |
| RSI | Very Fast | 1 | 75 | 225 | 74.359 | 18.591 | 4,60% | -1,2831% |
| MFI | Very Fast | 1 | 75 | 225 | 74.194 | 18.549 | 4,59% | -1,2901% |
| NATR | Fast | 1 | 67 | 201 | 66.941 | 16.736 | 4,14% | 9,1340% |
| ATR | Fast | 1 | 67 | 201 | 66.728 | 16.683 | 4,12% | 9,1654% |
| ROC | Fast | 1 | 67 | 201 | 66.496 | 16.625 | 4,11% | 9,2031% |
| CCI | Fast | 1 | 67 | 201 | 66.421 | 16.607 | 4,11% | 9,2064% |
| KAMA20 | Medium | 1 | 51 | 153 | 52.017 | 13.005 | 3,21% | 28,8627% |
| EMA20 | Medium | 1 | 51 | 153 | 51.921 | 12.981 | 3,21% | 28,8529% |
| OBV | Medium | 1 | 51 | 153 | 48.865 | 12.217 | 3,02% | 29,3348% |
| EMA50 | Slow | 1 | 46 | 138 | 44.620 | 11.156 | 2,76% | 36,1413% |
| SMA50 | Slow | 1 | 46 | 138 | 44.406 | 11.103 | 2,74% | 36,1873% |
| EMA200 | Very Slow | 1 | 38 | 114 | 28.715 | 7.181 | 1,77% | 46,6769% |
| SMA200 | Very Slow | 1 | 38 | 114 | 28.551 | 7.138 | 1,76% | 46,8057% |

Leader post-change:

1. Bollinger;
2. PPO;
3. MACD;
4. Donchian;
5. ADX;
6. StochRSI;
7. Aroon.

I sette indicatori multi-colonna richiesti — Bollinger, ADX, MACD, PPO, Donchian, Aroon e StochRSI — pesano:

| Misura | Valore |
|---|---:|
| Caratteri | 903.281 |
| Token | 225.827 |
| Righe | 1.239 |
| Quota blocco indicatori | 55,8283% |
| Quota payload | 45,3746% |
| Baseline | 1.117.921 caratteri |
| Riduzione | 214.640 / 19,1999% |

Nota tecnica: Bollinger e Donchian hanno un output band canonico ma tre colonne serializzate; sono quindi multi-colonna anche quando `output_count=1`.

Very Fast Full mantiene la stessa densità della baseline. L'aggiunta di metadata, `temporal_class` e summary produce quindi un piccolo aumento:

| Istanza | Delta caratteri |
|---|---:|
| StochRSI | +1.688 |
| MFI | +945 |
| RSI | +942 |
| Totale Very Fast | +3.575 |

---

## 13. Policy eventi

Formula:

```text
recent_count = eventi con event_date >= snapshot_as_of - 30 giorni
exported_count = min(total_count, max(20, recent_count))
```

Semantica:

- limite temporale inclusivo;
- giorni di calendario, non sessioni;
- ordinamento iniziale newest-first;
- selezione lineare verso il passato;
- ordine pubblico finale deterministico;
- policy identica in Compact, Standard e Full;
- nessun ranking;
- nessun relevance score;
- nessuna quota per famiglia;
- nessun sampling storico distribuito;
- nessun consolidamento in episodi.

Nel Portfolio Full 1Y:

| Misura | Valore |
|---|---:|
| Gruppi `entity+annotation` | 48 |
| Eventi rilevati | 1.615 |
| Eventi recenti aggregati | 159 |
| Eventi esportati | 707 |
| Eventi omessi | 908 |
| Gruppi completi | 21 |
| Gruppi con selezione | 27 |
| Gruppi governati dal floor 20 | 27 |
| Massimo recent count per gruppo | 13 |
| Gruppi con recent count >20 | 0 |

Anche sull'intera matrice richiesta:

- gruppi osservati: **954**;
- massimo recent count per gruppo: **13**;
- gruppi con recent count >20: **0**.

Quindi, nei dati reali correnti, il ramo “tutti i recenti se >20” è coperto dai test sintetici ma non attivato dal dataset del probe. La riduzione reale è dominata dal floor di 20.

### 13.1 Aggregato per annotation key

Formato: `rilevati/recenti/esportati/omessi`.

| Annotation key | Conteggi |
|---|---:|
| `stoch_rsi_k_d` | 399/35/60/339 |
| `stoch_rsi_k_overbought_80` | 198/21/60/138 |
| `stoch_rsi_k_oversold_20` | 179/13/60/119 |
| `price_ema_20` | 148/14/60/88 |
| `price_bollinger_middle` | 134/18/60/74 |
| `price_donchian_middle` | 130/18/60/70 |
| `macd_histogram_zero` | 90/10/60/30 |
| `macd_signal` | 90/10/60/30 |
| `price_bollinger_upper` | 76/11/58/18 |
| `price_bollinger_lower` | 52/2/50/2 |
| `rsi_14_oversold_30` | 34/0/34/0 |
| `rsi_14_overbought_70` | 22/0/22/0 |
| `adx_14_trend_25` | 21/0/21/0 |
| `ema_20_ema_50` | 16/5/16/0 |
| `mfi_14_overbought_80` | 12/2/12/0 |
| `mfi_14_oversold_20` | 12/0/12/0 |
| `ema_50_ema_200` | 2/0/2/0 |

### 13.2 Highlight richiesti

| Famiglia/highlight | Rilevati | Esportati | Omessi |
|---|---:|---:|---:|
| StochRSI K/D | 399 | 60 | 339 |
| StochRSI 20/80 | 377 | 120 | 257 |
| MACD signal + histogram/zero | 180 | 120 | 60 |
| Prezzo/EMA20 | 148 | 60 | 88 |
| EMA20/EMA50 | 16 | 16 | 0 |
| EMA50/EMA200 | 2 | 2 | 0 |
| Bollinger | 262 | 168 | 94 |
| Donchian | 130 | 60 | 70 |
| RSI 30/70 | 56 | 56 | 0 |
| ADX/25 | 21 | 21 | 0 |
| MFI 20/80 | 24 | 24 | 0 |
| FX | 0 misurabili | 0 | probe fallito prima del payload |

### 13.3 Riduzioni maggiori per gruppo

| Entity | Annotation | Rilevati/recenti/esportati/omessi | Chars prima→dopo | Riduzione |
|---|---|---:|---:|---:|
| `asset:6` | `stoch_rsi_k_d` | 146/11/20/126 | 53.471→7.342 | 86,269193% |
| `asset:7` | `stoch_rsi_k_d` | 145/11/20/125 | 52.989→7.339 | 86,149956% |
| `asset:1` | `stoch_rsi_k_d` | 108/13/20/88 | 39.442→7.320 | 81,441103% |
| `asset:7` | `stoch_rsi_k_overbought_80` | 72/5/20/52 | 27.885→7.709 | 72,354312% |
| `asset:6` | `stoch_rsi_k_overbought_80` | 70/8/20/50 | 27.097→7.811 | 71,173931% |
| `asset:1` | `stoch_rsi_k_oversold_20` | 64/2/20/44 | 24.414→7.687 | 68,513967% |
| `asset:7` | `price_bollinger_middle` | 62/8/20/42 | 24.294→7.844 | 67,712192% |
| `asset:7` | `price_donchian_middle` | 60/8/20/40 | 22.669→7.529 | 66,787242% |
| `asset:7` | `price_ema_20` | 60/6/20/40 | 21.258→7.089 | 66,652554% |
| `asset:7` | `stoch_rsi_k_oversold_20` | 60/6/20/40 | 23.038→7.720 | 66,490147% |

### 13.4 Tutti i gruppi entity + annotation, Portfolio Full 1Y

Formato conteggi: `rilevati/recenti/esportati/omessi`.

| Entity | Annotation | Conteggi | Range rilevato | Range esportato |
|---|---|---:|---|---|
| `asset:1` | `adx_14_trend_25` | 3/0/3/0 | 2025-10-07→2026-04-09 | 2025-10-07→2026-04-09 |
| `asset:1` | `ema_20_ema_50` | 5/1/5/0 | 2025-11-19→2026-07-06 | 2025-11-19→2026-07-06 |
| `asset:1` | `macd_histogram_zero` | 28/3/20/8 | 2025-09-18→2026-07-27 | 2025-12-01→2026-07-27 |
| `asset:1` | `macd_signal` | 28/3/20/8 | 2025-09-18→2026-07-27 | 2025-12-01→2026-07-27 |
| `asset:1` | `mfi_14_overbought_80` | 8/0/8/0 | 2026-01-15→2026-06-01 | 2026-01-15→2026-06-01 |
| `asset:1` | `mfi_14_oversold_20` | 8/0/8/0 | 2025-08-15→2026-06-26 | 2025-08-15→2026-06-26 |
| `asset:1` | `price_bollinger_lower` | 14/0/14/0 | 2025-09-15→2026-06-26 | 2025-09-15→2026-06-26 |
| `asset:1` | `price_bollinger_middle` | 37/5/20/17 | 2025-09-23→2026-07-24 | 2026-04-08→2026-07-24 |
| `asset:1` | `price_bollinger_upper` | 22/0/20/2 | 2025-09-30→2026-06-11 | 2025-11-13→2026-06-11 |
| `asset:1` | `price_donchian_middle` | 31/5/20/11 | 2025-09-23→2026-07-27 | 2025-12-18→2026-07-27 |
| `asset:1` | `price_ema_20` | 41/3/20/21 | 2025-09-23→2026-07-24 | 2026-04-13→2026-07-24 |
| `asset:1` | `rsi_14_overbought_70` | 14/0/14/0 | 2025-12-31→2026-03-30 | 2025-12-31→2026-03-30 |
| `asset:1` | `rsi_14_oversold_30` | 13/0/13/0 | 2025-08-20→2026-06-26 | 2025-08-20→2026-06-26 |
| `asset:1` | `stoch_rsi_k_d` | 108/13/20/88 | 2025-08-26→2026-07-29 | 2026-06-08→2026-07-29 |
| `asset:1` | `stoch_rsi_k_overbought_80` | 56/8/20/36 | 2025-08-26→2026-07-29 | 2026-02-24→2026-07-29 |
| `asset:1` | `stoch_rsi_k_oversold_20` | 64/2/20/44 | 2025-09-08→2026-07-24 | 2026-04-22→2026-07-24 |
| `asset:6` | `adx_14_trend_25` | 10/0/10/0 | 2025-11-10→2026-05-21 | 2025-11-10→2026-05-21 |
| `asset:6` | `ema_20_ema_50` | 3/1/3/0 | 2025-10-23→2026-07-01 | 2025-10-23→2026-07-01 |
| `asset:6` | `macd_histogram_zero` | 28/3/20/8 | 2025-08-26→2026-07-19 | 2025-09-28→2026-07-19 |
| `asset:6` | `macd_signal` | 28/3/20/8 | 2025-08-26→2026-07-19 | 2025-09-28→2026-07-19 |
| `asset:6` | `mfi_14_overbought_80` | 2/2/2/0 | 2026-07-10→2026-07-11 | 2026-07-10→2026-07-11 |
| `asset:6` | `mfi_14_oversold_20` | 4/0/4/0 | 2025-08-08→2026-02-14 | 2025-08-08→2026-02-14 |
| `asset:6` | `price_bollinger_lower` | 16/2/16/0 | 2025-08-30→2026-07-27 | 2025-08-30→2026-07-27 |
| `asset:6` | `price_bollinger_middle` | 35/5/20/15 | 2025-08-12→2026-07-23 | 2025-11-22→2026-07-23 |
| `asset:6` | `price_bollinger_upper` | 18/8/18/0 | 2025-10-12→2026-07-17 | 2025-10-12→2026-07-17 |
| `asset:6` | `price_donchian_middle` | 39/5/20/19 | 2025-08-12→2026-07-23 | 2026-01-18→2026-07-23 |
| `asset:6` | `price_ema_20` | 47/5/20/27 | 2025-08-12→2026-07-24 | 2026-04-01→2026-07-24 |
| `asset:6` | `rsi_14_overbought_70` | 2/0/2/0 | 2025-10-26→2025-10-27 | 2025-10-26→2025-10-27 |
| `asset:6` | `rsi_14_oversold_30` | 17/0/17/0 | 2025-08-08→2026-05-13 | 2025-08-08→2026-05-13 |
| `asset:6` | `stoch_rsi_k_d` | 146/11/20/126 | 2025-08-22→2026-07-29 | 2026-06-07→2026-07-29 |
| `asset:6` | `stoch_rsi_k_overbought_80` | 70/8/20/50 | 2025-08-22→2026-07-18 | 2026-05-27→2026-07-18 |
| `asset:6` | `stoch_rsi_k_oversold_20` | 55/5/20/35 | 2025-08-24→2026-07-24 | 2026-02-07→2026-07-24 |
| `asset:7` | `adx_14_trend_25` | 8/0/8/0 | 2025-12-04→2026-06-11 | 2025-12-04→2026-06-11 |
| `asset:7` | `ema_20_ema_50` | 8/3/8/0 | 2025-10-02→2026-07-23 | 2025-10-02→2026-07-23 |
| `asset:7` | `ema_50_ema_200` | 2/0/2/0 | 2026-02-08→2026-05-06 | 2026-02-08→2026-05-06 |
| `asset:7` | `macd_histogram_zero` | 34/4/20/14 | 2025-08-27→2026-07-23 | 2026-01-15→2026-07-23 |
| `asset:7` | `macd_signal` | 34/4/20/14 | 2025-08-27→2026-07-23 | 2026-01-15→2026-07-23 |
| `asset:7` | `mfi_14_overbought_80` | 2/0/2/0 | 2025-09-02→2025-09-03 | 2025-09-02→2025-09-03 |
| `asset:7` | `price_bollinger_lower` | 22/0/20/2 | 2025-10-01→2026-06-14 | 2025-10-04→2026-06-14 |
| `asset:7` | `price_bollinger_middle` | 62/8/20/42 | 2025-08-16→2026-07-21 | 2026-05-29→2026-07-21 |
| `asset:7` | `price_bollinger_upper` | 36/3/20/16 | 2025-08-14→2026-07-26 | 2026-01-30→2026-07-26 |
| `asset:7` | `price_donchian_middle` | 60/8/20/40 | 2025-08-16→2026-07-21 | 2026-03-27→2026-07-21 |
| `asset:7` | `price_ema_20` | 60/6/20/40 | 2025-08-16→2026-07-19 | 2026-03-21→2026-07-19 |
| `asset:7` | `rsi_14_overbought_70` | 6/0/6/0 | 2025-08-14→2026-03-19 | 2025-08-14→2026-03-19 |
| `asset:7` | `rsi_14_oversold_30` | 4/0/4/0 | 2025-11-29→2026-05-24 | 2025-11-29→2026-05-24 |
| `asset:7` | `stoch_rsi_k_d` | 145/11/20/125 | 2025-08-23→2026-07-29 | 2026-06-14→2026-07-29 |
| `asset:7` | `stoch_rsi_k_overbought_80` | 72/5/20/52 | 2025-09-16→2026-07-26 | 2026-05-26→2026-07-26 |
| `asset:7` | `stoch_rsi_k_oversold_20` | 60/6/20/40 | 2025-08-24→2026-07-18 | 2026-04-07→2026-07-18 |

### 13.5 Invarianza rispetto al detail

Per ciascuna combinazione `selection + period`:

- identità degli eventi rilevati uguale in Compact/Standard/Full;
- identità degli eventi esportati uguale in Compact/Standard/Full;
- 9 gruppi di confronto richiesti valutati;
- mismatch: **0**.

Il detail modifica la storia numerica, non la selezione eventi.

---

## 14. Conseguenze informative

### 14.1 Informazione preservata

- scope Asset/Broker/Portfolio;
- tutti gli asset tecnici applicabili;
- tutte le istanze indicatore calcolabili;
- tutti gli output canonici;
- precisione prezzi/rate invariata;
- `period_summary` sull'intero periodo;
- latest value/date per output;
- first/min/max/last e date reali nei bucket;
- observation count;
- stati latest;
- eventi rilevati sulle osservazioni originali;
- identità degli eventi selezionati;
- conteggi completi per gruppo;
- oldest/newest rilevato ed esportato;
- upward/downward count;
- policy effettiva nel manifest.

### 14.2 Informazione ridotta

- densità della storia numerica degli indicatori, secondo classe;
- lista storica degli eventi oltre la selezione deterministica.

### 14.3 Completezza esplicita

La response dichiara:

```text
detected_count
recent_30d_count
exported_count
selection_applied
oldest/newest detected
oldest/newest exported
```

L'LLM può quindi distinguere:

- gruppo completo;
- gruppo selezionato;
- quantità omessa;
- finestra temporale conservata.

Non riceve però il contenuto degli eventi storici omessi.

---

## 15. Prezzi, rate e warm-up

Policy prezzo invariata:

| Detail | P/M/K | Bucket 365d |
|---|---:|---:|
| Compact | 2/30/30 | 29 |
| Standard | 2/30/14 | 46 |
| Full | 2/30/7 | 75 |

Portfolio Full 1Y:

- 3 asset;
- 75 bucket per asset;
- 225 bucket prezzo;
- 76.593 caratteri prima;
- 76.593 caratteri dopo.

Flusso indicatori:

```text
calculation input con warm-up plugin-owned
→ calcolo observation-level
→ stati e annotation
→ slice al periodo esportato
→ bucketizzazione storia numerica
```

La response dichiara `warmup_policy: component_owned`. Gli attuali campi aggregati `calculation_range` ed `earliest_calculation_date` restano non popolati.

---

## 16. Manifest e migrazione contratto v1

### 16.1 Esempio tecnico reale

```yaml
technical_sampling:
  price_policy:
    detail_level: full
    p: 2
    m: 30
    k: 7
    bucket_count: 75
  indicator_policies:
    - signal_instance_id: ema_200
      signal_code: EMA
      temporal_class: very_slow
      detail_level: full
      p: 2
      m: 9
      k: 14
      bucket_count: 38
    - signal_instance_id: macd_12_26_9
      signal_code: MACD
      temporal_class: medium_fast
      detail_level: full
      p: 2
      m: 23
      k: 9
      bucket_count: 59
```

### 16.2 Esempio policy eventi

```yaml
event_selection:
  minimum_latest_events_per_annotation: 20
  complete_recent_window_days: 30
  grouped_by:
    - entity_id
    - annotation_key
```

### 16.3 Esempio summary

```yaml
entity_id: asset:6
annotation_key: stoch_rsi_k_d
detected_count: 146
recent_30d_count: 11
exported_count: 20
selection_applied: true
oldest_detected_event_date: 2025-08-22
newest_detected_event_date: 2026-07-29
oldest_exported_event_date: 2026-06-07
newest_exported_event_date: 2026-07-29
```

### 16.4 Decisione di versioning

AI Export è beta:

- contract IDs restano v1;
- component version resta v1;
- dataset version resta v1;
- analysis version resta v1;
- nessun payload legacy;
- nessun compatibility fallback;
- mismatch identità continua a produrre `409 version_mismatch`.

`schema_version: 2.0.0` appartiene soltanto al file diagnostico del probe.

---

## 17. FX opzionale: 9/9 fallimenti noti

| Detail | 3M | 6M | 1Y |
|---|---|---|---|
| Compact | failed | failed | failed |
| Standard | failed | failed | failed |
| Full | failed | failed | failed |

Per tutti:

```text
AiExportSnapshotSourceError
required AI Export component failed: fx.rate_ohlc
known_fx_warmup_coupling_nonfatal = true
```

Esito corretto:

- **FX non è passato**;
- nessun dato dimensionale FX V2 è disponibile;
- il probe marca i nove casi come opzionali e non fatali;
- la causa è il coupling già noto tra overview/rate OHLC e warm-up tecnico;
- la correzione è intenzionalmente esclusa da questa attività.

---

## 18. Classificazioni e parametri da rivalutare

Le classificazioni ufficiali non sono state modificate.

### 18.1 Candidati concreti per probe successivi

1. **Very Fast in Full**
   - 75 bucket prima e dopo;
   - nessuna riduzione delle righe;
   - overhead totale +3.575 caratteri su RSI, MFI e StochRSI;
   - il costo deriva dai nuovi summary/metadata, non da maggiore storia.

2. **Medium Fast multi-colonna**
   - 557.701 caratteri;
   - 34,4694% del blocco indicatori;
   - 28,0151% del payload;
   - Bollinger, PPO, MACD e Donchian sono i primi quattro indicatori post-change;
   - una riclassificazione più lenta va valutata solo contro perdita informativa osservabile.

3. **Floor eventi a 20**
   - massimo recent count reale per gruppo: 13;
   - nessun gruppo attiva il ramo `recent_count > 20`;
   - 27/48 gruppi Portfolio Full 1Y sono governati esattamente dal floor 20;
   - il costo residuo eventi dipende quindi soprattutto dal minimo storico, non dalla finestra recente.

### 18.2 Nessuna configurazione alternativa proposta

Il JSON esistente misura soltanto la matrice ufficiale. Non contiene controfattuali completi con:

- nuovi `P/M/K`;
- nuovi conteggi;
- nuove distribuzioni temporali;
- impatto token reale per payload;
- impatto informativo.

Di conseguenza:

- nessun parametro alternativo è stato applicato;
- nessuna delle due configurazioni alternative ammesse viene proposta;
- non vengono inventati impatti token o conteggi non presenti nel probe.

---

## 19. Test e comandi

| Comando/gate | Esito noto |
|---|---:|
| `./dev.py test services signal-registry` | 46 passed |
| `./dev.py test services signal-contracts` | 10 passed |
| `./dev.py test services signal-service` | 45 passed |
| `./dev.py test services signal-annotations` | 25 passed |
| `./dev.py test services ai-export` | 988 passed |
| `./dev.py test schemas ai-export` | 113 passed |
| `./dev.py test api ai-export` | 14 passed |
| `./dev.py test api signal-catalogs` | 4 passed |
| frontend AI Export + signal contract unit mirati | 74 passed |
| test prompt manifest (incluso nei 74) | 5 passed |
| `./dev.py front check` | 0 errori, 0 warning |
| `./dev.py front build` | passed |
| `./dev.py mkdocs build` | passed |
| `./dev.py mkdocs check-links` | passed; 18 link validi |

Comando probe:

```bash
pipenv run python backend/test_scripts/diagnostics/ai_export_signal_density_v2_probe.py \
  --output LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/probe-phase00AiExportSignalDensityV2.json
```

Esito probe:

| Gate | Esito |
|---|---|
| Matrice richiesta | 27/27 |
| Matrice temporale | 18/18 |
| Conteggi teoria/runtime | 54/54 |
| FX opzionale | 0/9 passed; 9 failure noti non fatali |
| Exit code diagnostico | 0 |

---

## 20. Gate HTTP reale

| Probe | HTTP | Risultato |
|---|---:|---|
| Catalogo | 200 | 18 dataset / 16 analisi |
| Asset | 200 | 125 eventi rilevati / 116 esportati |
| Broker | 200 | 429 rilevati / 369 esportati |
| Portfolio broker 5 | 200 | 3 asset |
| Portfolio completo | 200 | 11 righe considerate → 7 asset unici; somma pesi 1 |
| FX | 503 | coupling noto `fx.rate_ohlc` |

I conteggi HTTP Asset/Broker non devono essere sostituiti con quelli della matrice deterministica: appartengono a un run reale con stato runtime differente.

---

## 21. Developer Guide aggiornata

| Pagina | Percorso |
|---|---|
| Overview runtime | `mkdocs_src/docs/developer/architecture/patterns/ai_export_snapshot.md` |
| Composizione e prompt | `mkdocs_src/docs/developer/architecture/patterns/ai_export_composition.md` |
| Sampling tecnico | `mkdocs_src/docs/developer/architecture/patterns/ai_export_sampling.md` |
| Estensione plugin | `mkdocs_src/docs/developer/architecture/patterns/signal_plugin_guide.md` |
| Navigazione | `mkdocs_src/mkdocs.yml` |

La documentazione copre:

- componenti, dataset, analisi e `all_data`;
- ordine esatto del prompt;
- required/optional e partial success;
- formula e matrice completa;
- calculation range contro exported range;
- warm-up;
- multi-output;
- policy eventi;
- manifest;
- contratto temporale plugin-owned;
- beta v1 in-place.

---

## 22. P1 e problemi aperti

| Tema | Stato dopo questa attività |
|---|---|
| Audit sampling indicatore | migliorato: classe, P/M/K e bucket count nel manifest |
| Completezza eventi | migliorata: detected/recent/exported/range dichiarati |
| Omissioni optional | non ampliate nel manifest pubblico; diagnostica resta interna |
| Diagnostics complete indicatore | ancora parziali: params/version/status/warm-up/warnings non sono tutti nel payload |
| Breadth denominators | invariati |
| FIFO in-transit | invariato |
| Broker Review/FIFO overlap | invariato |
| Cost Efficiency denominators | invariati |
| Peso Portfolio nelle analisi Asset | invariato |
| FX exposure impact | invariato |
| FX overview/technical coupling | aperto; 503 confermato |
| Legacy stack interno non pubblico | non rimosso in questa attività |

Nessun P1 estraneo è stato corretto opportunisticamente.

---

## 23. Esclusioni intenzionali

- nessuna modifica alla policy prezzi/rate;
- nessuna segmentazione `Parte N/M`;
- nessuna paginazione;
- nessun truncation per token o caratteri;
- nessun downgrade automatico del detail;
- nessuna eliminazione di asset;
- nessuna eliminazione dimensionale di indicatori;
- nessun evento rilevato sui bucket;
- nessun ranking eventi;
- nessun relevance score;
- nessun cap a 20 sugli eventi recenti;
- nessun sampling storico distribuito;
- nessun Drawdown Recovery;
- nessuna correzione del coupling FX;
- nessun parametro alternativo;
- nessun unrelated P1.

---

## 24. Percorsi di consegna

### Probe nuovo

```text
LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/
probe-phase00AiExportSignalDensityV2.json
```

### Report nuovo

```text
LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/
report-phase00AiExportSignalDensityV2.md
```

### Baseline conservata

```text
LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/
probe-phase00AiExportTechnicalDensity.json
```

### Documentazione

```text
mkdocs_src/docs/developer/architecture/patterns/ai_export_snapshot.md
mkdocs_src/docs/developer/architecture/patterns/ai_export_composition.md
mkdocs_src/docs/developer/architecture/patterns/ai_export_sampling.md
mkdocs_src/docs/developer/architecture/patterns/signal_plugin_guide.md
mkdocs_src/mkdocs.yml
```

---

## 25. Conclusione

La Signal Density V2 riduce il caso massimo reale di **686.063 caratteri / 25,630151%** senza modificare prezzi, scope, indicatori calcolabili, output canonici, summary o latest state.

La riduzione deriva da due meccanismi separati:

1. densità numerica per `detail + temporal class`;
2. selezione deterministica per `entity_id + annotation_key`.

Il principale costo residuo è la famiglia multi-colonna Medium Fast. Il principale risparmio eventi è StochRSI. La policy eventi reale è dominata dal floor di 20 perché nessun gruppo del dataset corrente supera 20 eventi negli ultimi 30 giorni.

La matrice ufficiale resta invariata, auditabile e completamente coerente tra teoria e runtime. FX resta esplicitamente non passato e aperto come problema separato.
