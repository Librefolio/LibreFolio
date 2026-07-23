# Signal backend spike

Non-production harness for Phase 0 A1. It validates the pinned
`pandas-ta-classic + TA-Lib` stack against deterministic OHLCV fixtures,
measures warm-up and batch behavior, and proves the requested computation
backend is used.

Run from repository root:

```bash
pipenv run python scripts/spikes/signals/run_signal_backend_spike.py \
  --output /tmp/libreFolio_signal_backend_spike.json
```

The command exits non-zero when a hard stack gate fails. Numerical differences,
NaN propagation, missing-field behavior, and unresolved warm-up cases remain in
the report for architectural review.
