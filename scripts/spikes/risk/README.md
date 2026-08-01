# Risk quantitative-library spike

Non-production harness for Risk Analysis Step 1 (P0). It validates the installed
QuantLib and Riskfolio-Lib Python APIs against deterministic fixtures and writes a
machine-readable report.

Run from repository root:

```bash
python scripts/spikes/risk/run_quant_library_probe.py \
  --output /tmp/libreFolio_quant_library_probe.json
```

Use hard gates when a package is expected to be installed:

```bash
python scripts/spikes/risk/run_quant_library_probe.py \
  --require-quantlib \
  --require-riskfolio \
  --output /tmp/libreFolio_quant_library_probe.json
```

The probe covers:

- QuantLib pseudo-random, Sobol QMC and exploratory Burley-2020 sequences
  (RQMC is not exposed by the production contract);
- single-asset and correlated multi-asset paths;
- calendar/day-count/curve and bond duration/convexity APIs;
- Riskfolio-Lib import, dependency/version gates, CVXPY solver discovery,
  minimum-variance, maximum-Sharpe, risk-parity, covariance estimators, linear
  weight bounds, efficient frontier and infeasible constraints;
- package versions, licenses and installed distribution sizes.

The Release 2 adoption gate is deliberately pinned to Riskfolio-Lib 7.0.1 with
NumPy 2.5.1 and forbids `vectorbt`:

```bash
python scripts/spikes/risk/run_quant_library_probe.py \
  --require-riskfolio \
  --expected-numpy-version 2.5.1 \
  --expected-riskfolio-version 7.0.1 \
  --forbid-package vectorbt \
  --output /tmp/libreFolio_quant_library_probe.json
```

The harness does not mutate project manifests and is not production application
code.

## P11 simulation-adapter probe

Verify the production QuantLib path against analytical multivariate-GBM moments:

```bash
pipenv run python scripts/spikes/risk/run_simulation_adapter_probe.py \
  --output /tmp/libreFolio_simulation_adapter_probe.json
```

The report expresses MC mean/covariance/correlation errors in standard-error units,
checks QMC convergence over dyadic path counts, and proves direct/spawned output
equivalence. NumPy supplies only analytical checks and aggregation.

## P12 scale benchmark

Classify the complete scale matrix and benchmark the actual persistent QuantLib and
Riskfolio `spawn` pools:

```bash
pipenv run python scripts/spikes/risk/run_simulation_scale_benchmark.py \
  --output /tmp/libreFolio_quant_worker_benchmark.json
```

The report separates cold import/startup, warm execution, queue wait, IPC,
engine stages, cache hits, child RSS, one/two-worker warm throughput and hard-timeout
recycling. Process isolation is unconditional; worker count remains configurable.

Linux/Python 3.13 wheel probes:

```bash
docker build \
  --platform linux/arm64 \
  --target base \
  -f scripts/spikes/risk/Dockerfile.quantlib \
  -t librefolio-risk-probe:base-arm64 .

docker build \
  --platform linux/arm64 \
  -f scripts/spikes/risk/Dockerfile.quantlib \
  -t librefolio-risk-probe:quantlib-arm64 .

docker build \
  --platform linux/amd64 \
  -f scripts/spikes/risk/Dockerfile.riskfolio \
  -t librefolio-risk-probe:riskfolio-amd64 .
```
