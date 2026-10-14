# Spike P0 — QuantLib e Riskfolio-Lib

**Data**: 27 Luglio 2026
**Gate**: G1 — Quant Foundation
**Piano**:
[`plan-phase01Step1QuantFoundation.prompt.md`](./plan-phase01Step1QuantFoundation.prompt.md)

## 1. Esito

| Libreria/capability | Decisione | Conseguenza |
|---|---|---|
| QuantLib 1.43 | **ADOPTED** | Dipendenza runtime pinata; adapter P11 dietro boundary serializzabile e processo `spawn`. |
| Sobol QMC QuantLib | **ADOPTED** | Generator e multi-path specializzati disponibili. |
| Burley-2020 RQMC QuantLib | **NON ADOTTATO** | Binding disponibile, ma RQMC è stato rimosso dal contratto P11; production espone solo MC/QMC. |
| Riskfolio-Lib 7.0.1 | **ADOPTED — revisione 28 Luglio 2026** | Dipendenza runtime pinata; P13 backend riaperto dietro worker `spawn` separato. |

La prima valutazione su Riskfolio 7.3.0 era viziata dalla scelta della release:
`vectorbt -> numba -> numpy <2.5` appartiene al packaging 7.3.0, non alle API
P13 necessarie. Riskfolio 7.0.1:

1. richiede direttamente `numpy>=1.24.0`;
2. funziona con il lock LibreFolio `numpy==2.5.1`;
3. non installa `vectorbt` né `numba`;
4. espone tutte le API P13 richieste;
5. aggiunge circa 644 MiB arm64 / 673 MiB amd64 oltre al probe QuantLib.

## 2. Artefatti riproducibili

- `scripts/spikes/risk/run_quant_library_probe.py`
- `scripts/spikes/risk/Dockerfile.quantlib`
- `scripts/spikes/risk/Dockerfile.riskfolio`
- `backend/test_scripts/fixtures/risk/quant_library_probe.json`
- `backend/test_scripts/test_services/test_quantlib_smoke.py`
- comando registrato: `./dev.py test services quantlib-runtime`

Il probe produce JSON con ambiente, versioni, licenze, dimensioni distribuzioni,
capability, shape, riproducibilità, solver, pesi e tempi.

## 3. Ambiente

| Voce | Valore |
|---|---|
| Host | macOS arm64 |
| Python | 3.13.14 |
| Docker base | `python:3.13-slim` |
| Piattaforme container | Linux arm64 + Linux amd64 |
| NumPy production lock | 2.5.1 |
| NumPy development lock | 2.5.0 |
| pandas | 3.0.3 |
| SciPy | 1.18.0 |
| QuantLib | 1.43, BSD-3-Clause |
| Riskfolio-Lib probe/runtime | 7.0.1, BSD 3-clause |

## 4. QuantLib

### 4.1 Installazione e wheel

- Python 3.13 host arm64: import riuscito.
- Linux arm64: wheel ABI3
  `cp39-abi3-manylinux_2_24_aarch64.manylinux_2_28_aarch64`.
- Linux amd64: wheel ABI3
  `cp39-abi3-manylinux_2_24_x86_64.manylinux_2_28_x86_64`.
- Installazione wheel nel probe: circa 5,5 s per piattaforma.
- Nessuna compilazione C++ nel container.

### 4.2 Capability verificate

- `BlackScholesMertonProcess`, `GeneralizedBlackScholesProcess`;
- Heston, Merton-76 e Variance Gamma presenti;
- path GBM pseudo-random single asset;
- multi-path correlato pseudo-random;
- multi-path correlato Sobol QMC;
- Sobol gaussiano e Burley-2020 Sobol gaussiano scrambled;
- calendar, day counter, curve flat;
- fixed-rate e zero-coupon bond;
- modified duration e convexity.

Fixture comune:

- due asset, 30 step giornalieri, correlazione 0,35;
- path single/multi con 31 punti;
- stesso seed -> output identico;
- scramble seed diverso -> sequenza RQMC diversa;
- duration `4.5512848562`;
- convexity `25.8465789158`.

### 4.3 Limiti binding SWIG

Il binding non espone i generatori generici
`InverseCumulativeRsg`/`MultiPathGenerator`, ma espone le varianti specializzate.
Non è stata trovata una variante `Burley2020*PathGenerator`.

Regola di lifetime obbligatoria:

```python
uniform = ql.SobolRsg(...)
gaussian = ql.InvCumulativeSobolGaussianRsg(uniform)
sample = generator.next()
path = sample.value()
owned_values = tuple(path[i] for i in range(len(path)))
```

Generatori e `sample` devono restare vivi finché i valori SWIG non sono copiati in
strutture Python. Costruzioni inline possono restituire tuple vuote dopo la
distruzione anticipata degli oggetti C++ sottostanti.

## 5. Riskfolio-Lib

### 5.1 Stack funzionante del probe

| Pacchetto | Versione |
|---|---|
| Riskfolio-Lib | 7.0.1 |
| NumPy | 2.5.1 |
| pandas | 3.0.5 |
| SciPy | 1.18.0 |
| vectorbt | assente |
| Numba | assente |
| CVXPY | 1.9.2 |

Solver rilevati: `CLARABEL`, `SCS`, `SCIPY`, `HIGHS`, `OSQP`.

### 5.2 Fixture di ottimizzazione

| Strategia | Somma pesi | Ripetizione max delta | Esito |
|---|---:|---:|---|
| min-risk | 1,0 | 0,0 | ok |
| max-Sharpe stimato | 1,0 | 0,0 | ok |
| risk parity | 1,0 | 0,0 | ok |

Tutti i pesi sono finiti, rispettano bound 5%-80%, sommano a uno e sono
ripetibili. Verificati anche covariance storica/Ledoit/OAS PSD, frontiera a cinque
punti e vincoli infeasible. Probe completo: ~2,59 s host, ~2,14 s Linux arm64,
~4,43 s Linux amd64 emulato.

### 5.3 Probe esplicito Riskfolio-Lib 7.3.0

L'audit successivo ha verificato anche la release `7.3.0` in un ambiente pulito,
senza assumere che il vincolo osservato nel primo tentativo fosse ancora valido.

Risultato:

- `riskfolio-lib==7.3.0` richiede `vectorbt`;
- `vectorbt` richiede Numba;
- Numba 0.66 richiede `numpy<2.5`;
- LibreFolio usa e mantiene `numpy==2.5.1`;
- pip, Pipenv e il probe Docker non risolvono questa combinazione senza downgrade
  di NumPy.

Quindi sono vere entrambe le conclusioni seguenti:

1. escludere **tutta** Riskfolio era una falsa pista: 7.0.1 funziona e viene usata;
2. non aggiornare ora a 7.3.0 è una scelta tecnica reale, non un risparmio di spazio.

Il pin 7.0.1 evita `vectorbt`/Numba, preserva NumPy 2.5.1 e supera i gate P13.

## 6. Costo container

Dimensioni Docker non compresse:

| Immagine probe | arm64 | Delta arm64 | amd64 | Delta amd64 |
|---|---:|---:|---:|---:|
| base Python 3.13 slim | 143.141.964 B | — | 117.913.151 B | — |
| + QuantLib | 234.137.933 B | +86,8 MiB | 211.611.758 B | +89,4 MiB |
| + QuantLib + Riskfolio 7.0.1 | 909.800.578 B | +731,2 MiB | 917.232.656 B | +762,7 MiB |
| Riskfolio 7.0.1 oltre QuantLib | — | +644,4 MiB | — | +672,9 MiB |

Ambienti virtuali host:

- QuantLib isolato: 70.620 KiB;
- stack host Riskfolio: RSS massima probe 268.615.680 B.

RSS massima container: 302.424.064 B arm64 e 368.697.344 B amd64 emulato.

## 7. Integrazione adottata

- `Pipfile`: `quantlib = "==1.43"` e `riskfolio-lib = "==7.0.1"`;
- `Pipfile.lock`: closure Riskfolio 7.0.1 ricostruita sulla baseline, NumPy 2.5.1
  preservato, `vectorbt`/`numba` assenti;
- smoke offline registrato nel test runner service;
- build probe arm64/amd64 verde;
- import QuantLib nell'immagine LibreFolio verificato.

Il build finale LibreFolio con entrambi i runtime è verde:

- immagine: `librefolio:g5-quantlib-riskfolio-final`;
- digest locale:
  `sha256:fd8d79d6584dd7cf8087f54508f8c73cc66bbcacebe5a206bf46821117bd7999`;
- dimensione arm64 non compressa: 2.756.004.428 byte;
- smoke container: QuantLib `1.43`, NumPy `2.5.1`, Riskfolio `7.0.1`;
- import FastAPI application riuscito;
- `vectorbt` e `numba` assenti nel container.

Il build finale dell'audit è
`librefolio:risk-audit-remediation`, digest
`sha256:98a2cea750af424ffabf7b9ed01beba0afe329fde445e9d85a240f2d492194ac`,
architettura arm64 e dimensione non compressa `2.781.625.742 B`. Lo smoke importa
NumPy 2.5.1, QuantLib 1.43 e Riskfolio 7.0.1. Il valore è la dimensione
dell'intera immagine corrente, non un delta attribuibile al solo Riskfolio.

## 8. Conseguenze per P11-P13

- P11 può usare QuantLib dietro adapter senza esporre oggetti SWIG.
- QuantLib deve essere creato/eseguito nel worker `spawn`; niente concorrenza
  `asyncio.to_thread`.
- QMC usa Sobol QuantLib con `skipTo` e
  `StochasticProcessArray.evolve`.
- RQMC e il fallback SciPy sono rimossi.
- P13/frontiera viene implementato nel backend con Riskfolio 7.0.1 e worker
  `spawn` separato.
- Nessuna UI P13 in questo round; il catalogo/API restano la superficie prevista.
- NumPy resta 2.5.1; nessun packaging vectorbt/Commons Clause entra nel runtime.

## 9. Verifica

- harness host QuantLib: verde;
- harness host Riskfolio 7.0.1 + NumPy 2.5.1: verde;
- Docker probe Linux arm64: verde;
- Docker probe Linux amd64: verde;
- solver/bound/frontiera/infeasible/covariance estimators: verdi;
- `vectorbt`/`numba`: assenti;
- build immagine LibreFolio arm64: verde;
- import QuantLib 1.43 nell'immagine LibreFolio: verde;
- `./dev.py test services risk-all`: 74 test verdi;
- `./dev.py test api risk`: 7 test verdi sul DB popolato;
- `./dev.py test schemas`: 21 test Risk verdi;
- frontend check/build: verdi;
- API sync: idempotente;
- immagine finale arm64 + smoke runtime: verdi;
- lint Ruff + formato Black: verdi.

Alla prima chiusura G5 la suite backend globale aveva incontrato lavoro concorrente
sul provider Borsa Italiana. Nell'audit finale non è stata riusata come gate Risk:
i gate dedicati, API, schema, frontend e container sono verdi e isolano il dominio
verificato da modifiche concorrenti estranee.
