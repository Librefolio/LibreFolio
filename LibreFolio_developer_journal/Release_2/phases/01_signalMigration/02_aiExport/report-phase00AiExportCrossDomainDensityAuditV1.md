# AI Export Cross-Domain Density Audit V1

## Executive summary

La riduzione del prompt tecnico non era composta soltanto da dati duplicati.

Tre meccanismi diversi sono stati applicati:

1. **compressione lossless** del testo pubblico;
2. **omissione di righe senza osservazioni**;
3. **campionamento reale** di history ed eventi.

Il risultato piu importante dell'audit e il seguente:

- sul caso Alfy 3M Standard, la sola compressione lossless ha ridotto il prompt da
  **79.443,00** a **55.297,50 token-equivalenti** (`-30,4%`) senza cambiare
  history rows o event rows;
- la successiva policy eventi (e history lato backend) ha ridotto il prompt da
  **55.297,50** a **49.655,50 token-equivalenti** (`-10,2%`), ma gli eventi
  pubblici sono passati da **951/1.013** a **447/1.013**;
- quindi il secondo passaggio ha eliminato circa meta degli eventi rilevati per un
  risparmio finale relativamente piccolo;
- il backend snapshot e invece sceso da **384.085,75** a **225.687,75
  token-equivalenti** (`-41,2%`) perche non trasporta piu righe history/eventi che
  il prompt Standard non usa.

La raccomandazione di questo audit e:

1. mantenere integralmente la compressione lossless;
2. mantenere l'omissione delle righe vuote;
3. mantenere i limiti history Compact 5 / Standard 10 / Full all;
4. **rivalutare la sola policy eventi Standard** con una policy intermedia
   **21 giorni/minimo 10**, perche recupera circa il 54-64% degli eventi che
   30g/min20 aggiungerebbe, con un incremento prompt molto piu contenuto;
5. mantenere Compact come preview leggera e Full come modalita di audit history;
6. chiarire nel prompt e nella UI che latest e period summary sono completi, ma la
   history Compact/Standard e campionata.

La raccomandazione **21 giorni/minimo 10** e stata approvata dall'utente il
3 agosto 2026 ed e ora la policy Standard.

## Run autorevole dell'audit

- Run: `20260803T132329.937903Z`
- Prompt attesi: 18
- Prompt generati: 18
- Failure/skipped: 0/0
- Public-output violations: 0
- UI/probe equivalence: 18/18
- Secret scan: passed
- Source DB invariato: true
- Production DB invariato: true

Questo run e autorevole per la matrice finale cross-domain sullo snapshot
`user_anon_01`. Non riproduce da solo la decomposizione A/B/C dei run mattutini:
quei run usano uno snapshot DB diverso e includono anche `user_anon_02`.

Artefatti:

```text
real_prompt_probe/20260803T132329.937903Z/
  prompts/
  canonical/
  metrics.json
  failures.json
  run_manifest.json
  summary.md
```

## Cosa e stato tolto

### 1. Compressione lossless

Questi cambi riducono caratteri senza eliminare osservazioni:

- le date dentro le celle history usano:
  - `s` = start della riga;
  - `e` = end della riga;
  - `+N` = offset in giorni dallo start;
- le definizioni evento sono dichiarate una volta;
- ogni evento usa un definition reference breve;
- `value_fields` dichiara una volta l'ordine dei valori;
- le righe evento non ripetono annotation key e nomi dei campi;
- latest, period summary, valori, date e semantica restano ricostruibili.

Evidenza Alfy sui tre run di stage ravvicinati:

| Stage | Run | Backend token | Final token | History source/public | Events detected/public |
|---|---|---:|---:|---:|---:|
| History sampling, renderer precedente | `20260803T093200.105855Z` | 383.959,50 | 79.443,00 | 2.256 / 1.160 | 1.012 / 950 |
| Renderer lossless compatto | `20260803T093808.514744Z` | 384.085,75 | 55.297,50 | 2.256 / 1.160 | 1.013 / 951 |
| Backend density finale | `20260803T095105.494372Z` | 225.687,75 | 49.655,50 | 2.256 / 1.160 | 1.013 / 447 |

Il passaggio uno-due riduce il prompt del `30,4%` senza ridurre history/event rows.

Questi valori sono illustrativi del relativo snapshot Alfy. Non devono essere
combinati con le dimensioni assolute del run cross-domain pomeridiano come se la
composizione dei Portfolio fosse rimasta invariata.

### 2. Righe vuote

I bucket senza osservazioni non vengono esposti come righe economiche o tecniche.

Non vengono eliminati:

- zero osservati;
- estremi;
- flow;
- P&L;
- reconciliation;
- date osservate;
- coverage e period metadata.

I conteggi restano disponibili nei diagnostics.

### 3. History realmente campionata

La history indicatore non vuota e limitata per ogni entity + Signal instance:

| Detail | Righe pubbliche |
|---|---:|
| Compact | 5 |
| Standard | 10 |
| Full | tutte |

Compact e Standard selezionano uniformemente lungo il periodo e preservano primo e
ultimo bucket non vuoto.

Restano completi:

- Signal set;
- entity/Asset scope;
- output columns;
- latest value/date;
- `period_summary` sul periodo completo;
- Entity Directory.

Verifica automatica sui quattro domini:

| Domain | Instance summary confrontate | Period summary/latest uguali C/S/F | Entity Directory uguale | Instance IDs uguali |
|---|---:|:---:|:---:|:---:|
| Portfolio | 20 | si | si | si |
| Broker | 20 | si | si | si |
| Asset | 20 | si | si | si |
| FX | 12 | si | si | si |

### 4. Eventi realmente selezionati

La policy corrente e:

| Detail | Finestra completa | Minimo latest per entity+annotation |
|---|---:|---:|
| Compact | 7 giorni | 3 |
| Standard | 14 giorni | 5 |
| Full | 30 giorni | 20 |

Questa non e deduplicazione. Gli eventi fuori policy non sono presenti nel prompt.

Anche Full non esporta necessariamente tutti gli eventi dell'intero periodo:
mantiene la policy storica 30 giorni/minimo 20.

## Technical Export metrics

| Domain | Detail | Final token | Backend token | History source | History public | History excluded | Events detected | Events public | Events excluded | Empty rows | Signals | Instances | Eligible/Covered |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| portfolio | compact | 20.556,00 | 78.387,50 | 930 | 300 | 630 (67,7%) | 364 | 123 | 241 (66,2%) | 76 | 17 | 60 | 7/3 |
| portfolio | standard | 27.957,25 | 115.929,50 | 1.200 | 600 | 600 (50,0%) | 364 | 175 | 189 (51,9%) | 103 | 17 | 60 | 7/3 |
| portfolio | full | 52.742,25 | 243.356,25 | 1.644 | 1.644 | 0 | 364 | 340 | 24 (6,6%) | 146 | 17 | 60 | 7/3 |
| broker | compact | 18.399,75 | 68.555,50 | 930 | 300 | 630 (67,7%) | 364 | 123 | 241 (66,2%) | 0 | 17 | 60 | 7/3 |
| broker | standard | 25.344,75 | 103.331,75 | 1.200 | 600 | 600 (50,0%) | 364 | 175 | 189 (51,9%) | 0 | 17 | 60 | 7/3 |
| broker | full | 49.310,75 | 226.116,50 | 1.644 | 1.644 | 0 | 364 | 340 | 24 (6,6%) | 0 | 17 | 60 | 7/3 |
| asset | compact | 9.911,00 | 24.669,50 | 310 | 100 | 210 (67,7%) | 132 | 38 | 94 (71,2%) | 4 | 17 | 20 | 1/1 |
| asset | standard | 12.386,00 | 36.964,75 | 400 | 200 | 200 (50,0%) | 132 | 57 | 75 (56,8%) | 5 | 17 | 20 | 1/1 |
| asset | full | 20.720,25 | 79.942,50 | 548 | 548 | 0 | 132 | 122 | 10 (7,6%) | 6 | 17 | 20 | 1/1 |
| fx | compact | 7.313,50 | 18.866,75 | 180 | 60 | 120 (66,7%) | 134 | 35 | 99 (73,9%) | 10 | 9 | 12 | 1/1 |
| fx | standard | 9.134,25 | 27.939,75 | 232 | 120 | 112 (48,3%) | 134 | 55 | 79 (59,0%) | 12 | 9 | 12 | 1/1 |
| fx | full | 14.697,50 | 57.561,75 | 317 | 317 | 0 | 134 | 122 | 12 (9,0%) | 14 | 9 | 12 | 1/1 |

## Size reduction rispetto a Full

| Domain | Compact final | Standard final | Compact backend | Standard backend |
|---|---:|---:|---:|---:|
| Portfolio | -61,0% | -47,0% | -67,8% | -52,4% |
| Broker | -62,7% | -48,6% | -69,7% | -54,3% |
| Asset | -52,2% | -40,2% | -69,1% | -53,8% |
| FX | -50,2% | -37,9% | -67,2% | -51,5% |

## Analysis rappresentative

| Analysis | Domain | Final token | Technical share | History source/public | Events detected/public | Impatto |
|---|---|---:|---:|---:|---:|---|
| `portfolio.technical_breadth` | portfolio | 3.782,25 | 26,4% | 0/0 | 0/0 | focused summary, non usa history dettagliata |
| `portfolio.market_events_review` | portfolio | 6.436,00 | 33,5% | 0/0 | 0/0 dettagliati | focused context: 12 context events e 6 latest-event rows |
| `broker.review` | broker | 7.287,50 | 29,6% | 0/0 | 0/0 | focused secondary context |
| `asset.trend_analysis` | asset | 14.025,50 | 84,5% | 400/200 | 132/57 | direttamente coinvolta |
| `fx.trend_review` | fx | 10.203,25 | 83,8% | 232/120 | 134/55 | direttamente coinvolta |
| `fx.conversion_timing` | fx | 11.394,75 | 75,0% | 232/120 | 134/55 | direttamente coinvolta |

## Impatto sugli altri prompt

### Direttamente coinvolti

La policy history/eventi condivisa si applica a:

- `portfolio.technical`;
- `broker.technical`;
- `asset.market_technical`;
- `fx.market_technical`;
- Analysis che includono direttamente i dataset tecnici completi, in particolare:
  - `asset.trend_analysis`;
  - `fx.trend_review`;
  - `fx.conversion_timing`.

### Non direttamente coinvolti dalla history 5/10

Le Analysis focused usano componenti sintetici con policy proprie:

- `portfolio.technical_breadth`;
- `portfolio.market_events_review`;
- `broker.review`;
- altre Analysis Portfolio/Broker basate su `technical_summary`,
  `asset_comparison`, `market_context` o event digest.

Questi prompt beneficiano della formattazione lossless comune, ma non ricevono la
history dettagliata limitata a 5/10 righe.

## Review qualitativa

### Compact

- preserva scope, latest e summary;
- elimina circa due terzi delle righe history;
- elimina tra il 66% e il 74% degli eventi rilevati;
- adatto come preview o overview;
- non adatto a ricostruzione cronologica o audit.

### Standard

- preserva una traiettoria leggibile con 10 punti per instance;
- elimina circa meta delle righe history;
- elimina tra il 52% e il 59% degli eventi rilevati;
- adeguato per narrativa trend/momentum/volatilita;
- non adeguato per event chronology esaustiva.

### Full

- nessun bucket indicatore non vuoto campionato;
- latest, summary e scope completi;
- eventi ancora selezionati dalla policy 30 giorni/minimo 20;
- adatto a history audit, non equivale a tutti gli eventi dell'intero periodo.

## Problema di wording

La frase:

```text
period_summary=full exported period
```

e vera, ma puo essere letta come "history completa".

Il prompt dovrebbe distinguere piu esplicitamente:

```text
latest_and_period_summary=calculated_on_full_period
history_rows=uniform_sample_for_compact_and_standard
full=all_nonempty_indicator_buckets
```

Anche gli help UI Detail dovrebbero dichiarare i limiti 5/10/all e la policy eventi.

## Decision options

### A. Keep current

Pro:

- prompt piccoli;
- Standard resta narrativamente adeguato;
- backend transport molto ridotto.

Contro:

- perdita eventi superiore al 50% in Standard;
- il beneficio finale della nuova policy eventi e modesto.

### B. Lossless-only

Rimuovere history/event selection aggiuntiva, mantenendo soltanto encoding e vuoti.

Pro:

- massima tracciabilita.

Contro:

- prompt e backend payload tornano molto piu grandi;
- non sfrutta il detail level come controllo reale di densita.

### C. Tune — raccomandata

1. mantenere history 5/10/all;
2. mantenere Compact 7g/min3;
3. usare per Standard **21g/min10**;
4. lasciare Full 30g/min20;
5. chiarire UI e prompt wording.

## Counterfactual eventi Standard su DB congelato

Per eliminare il bias tra snapshot diversi e stata creata una copia SQLite
immutabile e sono state eseguite, sugli stessi sette prompt, tre policy:

- baseline pre-approvazione: 14g/min5 — run `20260803T135709.469799Z`;
- intermediate: 21g/min10 — run `20260803T135930.065645Z`;
- rich: 30g/min20 — run `20260803T135749.417973Z`.

Tutti i run:

- 7/7 prompt;
- source DB invariato;
- production DB invariato;
- secret scan passed;
- i run counterfactual non lasciavano modifiche; 21g/min10 e stata applicata solo
  dopo approvazione esplicita.

| User | Selection | 14g/5 token-eventi | 21g/10 token-eventi | 30g/20 token-eventi |
|---|---|---:|---:|---:|
| user_anon_01 | `asset.market_technical` | 12.389,00 / 57 | 12.812,75 / 93 | 13.135,75 / 123 |
| user_anon_01 | `asset.trend_analysis` | 14.029,00 / 57 | 14.452,75 / 93 | 14.775,75 / 123 |
| user_anon_01 | `broker.technical` | 25.343,75 / 175 | 26.461,75 / 274 | 27.193,50 / 341 |
| user_anon_01 | `fx.market_technical` | 9.134,25 / 55 | 9.557,75 / 91 | 9.921,25 / 122 |
| user_anon_01 | `fx.trend_review` | 10.203,25 / 55 | 10.626,75 / 91 | 10.990,25 / 122 |
| user_anon_01 | `portfolio.technical` | 27.959,00 / 175 | 29.077,00 / 274 | 29.808,75 / 341 |
| user_anon_02 | `portfolio.technical` | 49.705,50 / 447 | 53.356,25 / 767 | 55.333,75 / 950 |

Portfolio backend snapshot:

| User | 14g/5 | 21g/10 | 30g/20 |
|---|---:|---:|---:|
| user_anon_01 | 115.921,75 | 126.520,00 | 134.272,50 |
| user_anon_02 | 225.774,75 | 259.701,00 | 280.387,50 |

La policy 21g/min10:

- recupera 99/166 eventi aggiuntivi Portfolio/Broker sul caso rappresentativo;
- recupera 36/66 Asset e 36/67 FX;
- recupera 320/503 sul Portfolio Alfy;
- costa circa `+3-5%` final prompt nei casi rappresentativi (max `+4,6%`) e
  `+7,3%` su Alfy;
- aumenta il backend Portfolio di circa `+9,1%` e `+15,0%`.

Il run probe classifica `>50k` come heavy. Alfy passa quindi da medium
(`49.705,50`) a heavy (`53.356,25`) sia con 21g/min10 sia con 30g/min20, pur
restando sotto la soglia UI "molto grande" di 60k scelta dall'utente.

Non esiste garanzia universale sotto 60k: lo stesso `user_anon_01`, su uno snapshot
Portfolio precedente e molto piu denso, misurava **88.773,75 token** con la policy
eventi ricca. La UI warning resta quindi necessaria.

Standard 21g/min10 mantiene inoltre una distinzione reale da Full 30g/min20.

## Decisione approvata

Approvata e applicata l'opzione **Tune**:

- Compact: 7g/min3;
- Standard: 21g/min10;
- Full: 30g/min20;
- history: 5/10/all non-empty rows.

Le traduzioni della documentazione User Guide restano rinviate a una fase
successiva, come richiesto.

## Validazione post-approvazione

Run con policy applicata:

`real_prompt_probe/20260803T164514.504966Z`

Esito:

- 7/7 prompt;
- 5 Dataset + 2 Analysis;
- manifest Standard `21g/min10` in 7/7 prompt;
- UI/probe equivalence 7/7;
- public-output violations 0;
- secret scan passed;
- source e production DB invariati.

| User | Selection | Final token | Backend token | Eventi public/detected |
|---|---|---:|---:|---:|
| user_anon_01 | `asset.market_technical` | 12.886,50 | 41.000,25 | 93/128 |
| user_anon_01 | `asset.trend_analysis` | 14.518,00 | 41.916,25 | 93/128 |
| user_anon_01 | `fx.market_technical` | 9.557,75 | 31.861,75 | 91/134 |
| user_anon_01 | `fx.trend_review` | 10.626,75 | 32.189,75 | 91/134 |
| user_anon_01 | `broker.technical` | 64.380,50 | 335.504,25 | 852/1.145 |
| user_anon_01 | `portfolio.technical` | 85.850,50 | 438.220,00 | 1.033/1.378 |
| user_anon_02 | `portfolio.technical` | 53.297,25 | 259.526,75 | 766/1.013 |

Il run conferma:

- Asset/FX restano leggeri;
- il Portfolio Alfy resta sotto 60k ma nella categoria probe `heavy`;
- Portfolio/Broker con universi piu densi possono superare 60k;
- la warning UI 20k/60k resta necessaria e non deve essere sostituita da cap
  automatici.
