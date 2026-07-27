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

- QuantLib pseudo-random, Sobol QMC and Burley-2020 scrambled Sobol sequences;
- single-asset and correlated multi-asset paths;
- calendar/day-count/curve and bond duration/convexity APIs;
- Riskfolio-Lib import, CVXPY solver discovery and minimum-variance optimization;
- package versions, licenses and installed distribution sizes.

The harness does not mutate project manifests and is not production application
code.

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
