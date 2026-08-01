# Benchmark P12 corretto — Pool quant persistenti

**Data**: 28 Luglio 2026, audit/remediation incluso
**Gate**: G5 / P12
**Piano**:
[`plan-phase01Step5SimulationScaleOptimization.prompt.md`](./plan-phase01Step5SimulationScaleOptimization.prompt.md)

## 1. Decisione

**L'isolamento `spawn` resta sempre attivo.**

Production usa due failure domain separati:

- pool simulation QuantLib;
- pool optimization Riskfolio.

Entrambi sono lazy, bounded e configurabili. Restano persistenti mentre ricevono
lavoro, ma vengono chiusi dopo un timeout idle configurabile e ripartono lazy. Il
default resta un worker per pool; due worker sono disponibili per carichi concorrenti
e mostrano un beneficio warm reale, al costo di raddoppiare circa la RAM child.

Non esiste più una scelta `to_thread` vs processi: P12 decide solo il numero di worker.

## 2. Artefatto

- `scripts/spikes/risk/run_simulation_scale_benchmark.py`
- output: `/tmp/libreFolio_quant_worker_benchmark.json`
- rerun remediation:
  `/tmp/libreFolio_quant_worker_benchmark_20260728_idle_reap.json`

```bash
pipenv run python scripts/spikes/risk/run_simulation_scale_benchmark.py \
  --output /tmp/libreFolio_quant_worker_benchmark.json \
  --repeats 2
```

Ambiente: macOS arm64, Python 3.13.14, NumPy 2.5.1, QuantLib 1.43,
Riskfolio-Lib 7.0.1.

## 3. Matrice completa

Matrice classificata, non allocata:

- asset: 1 / 5 / 20 / 50;
- path: 1k / 10k / 100k;
- orizzonte: 1 / 5 / 10 anni;
- MC / QMC.

| Esito | Celle |
|---|---:|
| Totale | 72 |
| Accettate | 32 |
| Limite dimensione Sobol | 12 |
| Limite risorse | 28 |

Le celle impossibili sono quindi registrate esplicitamente, non saltate.

## 4. Simulation cold/warm

| Caso | Cold round trip | Warm round trip | Peak RSS warm |
|---|---:|---:|---:|
| 1 asset · 1.024 · 30g MC | 1,286 s | 0,071 s | 171,3 MB |
| 1 asset · 1.024 · 30g QMC | 1,244 s | 0,133 s | 171,7 MB |
| 5 asset · 4.096 · 90g MC | 1,824 s | 0,766 s | 174,9 MB |
| 5 asset · 4.096 · 90g QMC | 3,404 s | 2,353 s | 175,3 MB |
| 1 asset · 2.048 · 365g MC | 1,437 s | 0,329 s | 184,0 MB |

Warm IPC è circa `0,3-1,1 ms`. Nel caso 5 asset QMC:

- Sobol/gaussian RNG: `0,089 s`;
- `StochasticProcessArray.evolve`: `0,515 s`;
- copia/aggregazione path: `1,256 s`;
- aggregazione finale: `0,007 s`.

Il costo maggiore è quindi il bridge/copia del percorso, non un calcolo matematico
extra nascosto.

## 5. Cache

Caso 5 asset × 2.048 path × 90 giorni MC:

- prima richiesta cold: `1,523 s`;
- cache hit content-keyed: `0,000190 s`;
- nessun worker coinvolto nel cache hit;
- risultato identico.

## 6. Throughput warm

Quattro job indipendenti, due ripetizioni, worker già avviati:

### Simulation

| Worker | Wall run 1 | Wall run 2 | RSS concorrente |
|---:|---:|---:|---:|
| 1 | 1,527 s | 1,537 s | 175-176 MB |
| 2 | 0,783 s | 0,797 s | 347-349 MB |

Speedup mediano: **1,938x**.

### Optimization

| Worker | Wall run 1 | Wall run 2 | RSS concorrente |
|---:|---:|---:|---:|
| 1 | 0,091 s | 0,083 s | ~342 MB |
| 2 | 0,058 s | 0,059 s | ~683 MB |

Speedup mediano: **1,477x**.

Due worker scalano; non vengono però imposti come default perché ogni installazione
self-hosted ha un budget RAM e un profilo di concorrenza differente. La configurazione
per-pool consente di abilitarli senza cambiare architettura.

## 7. Riskfolio cold/warm

- cold round trip: `2,863 s`;
- warm round trip: `0,0159 s`;
- warm engine: `0,0156 s`;
- peak RSS: `340,6 MB`;
- output cold/warm identico.

Il costo cold è quasi interamente import CVXPY/Riskfolio/solver; il worker persistente
lo paga una volta.

## 8. Timeout/crash e recycle

Un job QuantLib è stato forzato oltre timeout:

- timeout rilevato;
- PID lane terminato;
- richiesta successiva completata con PID nuovo;
- nessun fallback nello stesso processo web.

## 9. Idle reap e restart lazy

Il rerun remediation usa timeout idle `0,2 s` e verifica entrambi i failure domain:

| Pool | Cold | Warm | RSS child | Reap osservato | Restart cold |
|---|---:|---:|---:|---:|---:|
| Simulation | `1,067 s` | `0,002722 s` | `171,3 MB` | `0,416 s`, stop incluso | `1,197 s` |
| Optimization | `3,075 s` | `0,016835 s` | `340,4 MB` | `0,645 s`, stop incluso | `2,961 s` |

In entrambi i casi:

- il PID non è più vivo dopo il reap;
- il job successivo usa un PID nuovo;
- il reaper parte solo con `_pending == 0`;
- richieste queued/in-flight non vengono interrotte;
- tutte le lane di un pool multi-worker vengono chiuse e ricreate;
- tre cicli consecutivi reap/restart non lasciano processi orfani;
- timeout `0` disabilita il comportamento.

L'ultimo rerun a una ripetizione misura anche speedup concorrente `2,144x`
simulation e `2,471x` optimization. Il run principale a due ripetizioni resta il
riferimento per la decisione del default; entrambi confermano che `>1` può aiutare.

Il default production `600 s` evita processi QuantLib/Riskfolio residenti
indefinitamente senza introdurre churn sui normali burst di richieste.

## 10. Conseguenze operative

- process isolation obbligatorio;
- default `1` worker simulation + `1` optimization;
- `>1` configurabile e misurato;
- queue bounded e backpressure esplicita;
- timeout/crash riciclano una sola lane;
- idle timeout chiude tutte le lane solo a pool inattivo;
- restart dopo idle resta lazy e trasparente;
- shutdown idempotente nel lifespan;
- cache evita job identici;
- P12 non giudica la correttezza di QuantLib tramite tempi NumPy.
