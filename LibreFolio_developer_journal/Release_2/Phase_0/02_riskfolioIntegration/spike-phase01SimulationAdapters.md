# Spike P11 corretto — QuantLib production e oracle matematici

**Data**: 28 Luglio 2026
**Gate**: G5 / P11
**Piano**:
[`plan-phase01Step5SimulationScaleOptimization.prompt.md`](./plan-phase01Step5SimulationScaleOptimization.prompt.md)

## 1. Decisione

**QuantLib 1.43 è l'unico motore production della simulazione GBM.**

- MC: RNG pseudo-random QuantLib + `GaussianMultiPathGenerator`;
- QMC: `SobolRsg.skipTo(seed)` + `InvCumulativeSobolGaussianRsg` +
  `StochasticProcessArray.evolve`;
- NumPy: algebra, aggregazione e oracle; nessun adapter production;
- RQMC: rimosso dal contratto;
- esecuzione: worker persistente lazy con start method `spawn`.

La precedente selezione NumPy/SciPy è superseded: confrontava un motore NumPy
vettoriale con percorsi QuantLib non equivalenti e respingeva QMC con una soglia di
correlazione `0,08` non derivata da un modello statistico.

## 2. Artefatti riproducibili

- `scripts/spikes/risk/run_simulation_adapter_probe.py`
- `backend/test_scripts/fixtures/risk/simulation_adapter_probe.json`
- output: `/tmp/libreFolio_simulation_adapter_probe.json`

```bash
pipenv run python scripts/spikes/risk/run_simulation_adapter_probe.py \
  --output /tmp/libreFolio_simulation_adapter_probe.json
```

Fixture principale: 5 asset correlati, 90 giorni, drift/covarianza annuali noti,
MC 8.192 path e QMC 256/1.024/4.096 path.

## 3. Oracle

Per ogni asset:

```text
Y_i = log(S_i(T) / S_i(0))
E[Y_i] = (mu_i - 0,5 Sigma_ii) T
Cov(Y_i, Y_j) = Sigma_ij T
```

Il gate MC usa:

- standard error della media normale;
- standard error della covarianza normale;
- trasformazione Fisher per la correlazione;
- intervallo simultaneo conservativo di `4,5` standard error.

Risultato MC 8.192 path:

| Verifica | Errore massimo normalizzato | Gate |
|---|---:|---:|
| media terminale | 0,935 SE | ✅ |
| covarianza terminale completa | 1,695 SE | ✅ |
| correlazione, Fisher-z | 1,523 SE | ✅ |

Non esiste più un cutoff assoluto inventato sulla correlazione.

## 4. Convergenza QMC

| Path | Errore L2 media | Errore Frobenius covarianza |
|---:|---:|---:|
| 256 | 6,592e-4 | 8,024e-3 |
| 1.024 | 1,597e-4 | 6,552e-3 |
| 4.096 | 4,933e-5 | 2,586e-3 |

Pendenza log2:

- media: `-0,648`;
- covarianza: `-0,283`.

Entrambe negative; l'errore finale è inferiore a quello iniziale. Il `seed` QMC è
l'indice iniziale Sobol, applicato con `skipTo`, non un parametro di scrambling.

## 5. Isolamento e equivalenza

Il risultato QMC 4.096 path è identico tra chiamata diretta al handler e worker
`spawn`. Sul probe arm64:

- cold round trip: `3,704 s`;
- engine: `2,384 s`;
- peak RSS child: `174.030.848 B`.

Gli oggetti QuantLib restano nel child; oltre il boundary passano solo payload
Pydantic/primitive.

## 6. Prestazioni: lettura corretta

QuantLib non viene giudicata contro NumPy per scegliere la correttezza. Il benchmark
di fase mostra invece dove cade il tempo:

- MC nativo fonde RNG + evoluzione nel generator QuantLib;
- QMC con offset Sobol richiede evoluzione esplicita;
- il binding SWIG e la copia dei path dominano spesso l'aggregazione Python;
- cold start include import del worker, mentre il warm IPC è sub-millisecondo.

Quindi "QuantLib più lenta" non significa "QuantLib calcola male": descrive il costo
del binding e del percorso generico richiesto dalla semantica `skipTo`.

## 7. Conseguenze production

- nessun `NumpyScipySimulationAdapter`;
- nessun SciPy Sobol/`ndtri` nel runtime;
- MC/QMC QuantLib soltanto;
- limite Sobol `asset × giorni <= 21.201`;
- seed riproducibile per entrambi i sampling;
- cache content-keyed;
- timeout/crash riciclano la sola lane simulation;
- nessun fallback silenzioso: un errore QuantLib è esplicito.
