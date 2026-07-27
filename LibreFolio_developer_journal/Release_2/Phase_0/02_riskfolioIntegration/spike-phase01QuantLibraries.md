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
| Burley-2020 RQMC QuantLib | **PARTIAL** | Sequenze gaussiane scrambled disponibili; manca un path-generator Burley specializzato. P11 comporrà evoluzione propria o userà `scipy.stats.qmc`. |
| Riskfolio-Lib 7.3.0 | **REJECTED per Release 2** | Nessuna dipendenza/endpoint/UI frontier. P13 chiuso intenzionalmente dal gate. |

La decisione Riskfolio non dipende dalla correttezza matematica della libreria:
min-risk, max-Sharpe e risk parity funzionano. Il blocco è operativo:

1. `vectorbt 1.1.0 -> numba 0.66.0 -> numpy < 2.5`, incompatibile con il
   lock production LibreFolio `numpy 2.5.1` e con il lock development `2.5.0`;
2. richiede downgrade a `numpy 2.4.6`;
3. aggiunge circa **0,98–1,01 GiB** oltre all'immagine probe con QuantLib;
4. espone warning CVXPY per moltiplicazione matriciale deprecata.

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
| Riskfolio-Lib probe | 7.3.0, BSD 3-clause |

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
| Riskfolio-Lib | 7.3.0 |
| NumPy | 2.4.6 |
| pandas | 3.0.3 |
| SciPy | 1.18.0 |
| vectorbt | 1.1.0 |
| Numba | 0.66.0 |
| CVXPY | 1.9.2 |

Solver rilevati: `CLARABEL`, `SCS`, `SCIPY`, `HIGHS`, `OSQP`.

### 5.2 Fixture di ottimizzazione

| Strategia | Somma pesi | Ripetizione max delta | Esito |
|---|---:|---:|---|
| min-risk | 1,0 | 0,0 | ok |
| max-Sharpe stimato | 1,0 | 0,0 | ok |
| risk parity | 1,0 | 0,0 | ok |

Tutti i pesi sono finiti e non negativi. Tempo host per sei solve
(due ripetizioni per strategia): circa 2,45 s; Linux arm64 circa 3,79 s;
Linux amd64 emulato circa 5,57 s.

## 6. Costo container

Dimensioni Docker non compresse:

| Immagine probe | arm64 | Delta arm64 | amd64 | Delta amd64 |
|---|---:|---:|---:|---:|
| base Python 3.13 slim | 143.141.964 B | — | 117.913.151 B | — |
| + QuantLib | 234.137.933 B | +86,8 MiB | 211.611.758 B | +89,4 MiB |
| + QuantLib + Riskfolio stack | 1.260.190.434 B | +1.065,3 MiB | 1.269.421.635 B | +1.098,2 MiB |
| Riskfolio stack oltre QuantLib | — | +978,5 MiB | — | +1.008,8 MiB |

Ambienti virtuali host:

- QuantLib isolato: 70.620 KiB;
- stack combinato Riskfolio: 918.224 KiB.

## 7. Integrazione adottata

- `Pipfile`: `quantlib = "==1.43"`;
- `Pipfile.lock`: solo hash Pipfile + entry QuantLib aggiunti; nessun upgrade
  transitivo;
- smoke offline registrato nel test runner service;
- build probe arm64/amd64 verde;
- import QuantLib nell'immagine LibreFolio verificato.

Il build finale LibreFolio dal lock minimale è verde:

- immagine: `librefolio:v1.0.1-15-g8346fdc7-dirty`;
- digest locale: `sha256:e7d08448e02e1997e90f370a6b58fa7cc8d03978e6adcd42d000dcadaa9e653d`;
- dimensione arm64 non compressa: 2.433.002.858 byte;
- install layer dipendenze: 33,2 s con cache wheel;
- smoke container: `QuantLib.__version__ == "1.43"`.

## 8. Conseguenze per P11-P13

- P11 può usare QuantLib dietro adapter senza esporre oggetti SWIG.
- QuantLib deve essere creato/eseguito nel worker `spawn`; niente concorrenza
  `asyncio.to_thread`.
- QMC può usare i path-generator QuantLib.
- RQMC userà Burley solo se P11 dimostra una composizione semplice e testabile;
  fallback già disponibile: `scipy.stats.qmc`.
- P13/frontiera non viene implementato né mostrato nel capability catalog/UI.
- Una futura rivalutazione Riskfolio richiede packaging opzionale separato o una
  dipendenza significativamente più leggera, non un downgrade silenzioso dello
  stack numerico principale.

## 9. Verifica

- harness host QuantLib: verde;
- harness host combinato: verde;
- Docker probe Linux arm64: verde;
- Docker probe Linux amd64: verde;
- build immagine LibreFolio arm64: verde;
- import QuantLib 1.43 nell'immagine LibreFolio: verde;
- `./dev.py test services quantlib-runtime`: 2 test verdi;
- lint Ruff + formato Black: verdi.

La suite services completa raggiunge un failure preesistente nel catalogo segnali
(`test_registry_discovers_core_plugins_and_schema_driven_catalog`: stringa
`color` nel payload serializzato), non collegato a QuantLib. Il punto viene
riassorbito nel gate Step 2, che deve congelare e riallineare la regressione del
framework segnali prima dell'estrazione della pipeline serie.
