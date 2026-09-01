---
title: "A regression that was a change of formula: mixed line+branch TOTAL read as pure lines"
category: problem
status: resolved
date: 2026-08-28
tags: [testing, coverage, metrics, backend, measurement, false-alarm]
related: [concepts/coverage-rate-vs-volume, concepts/run-cache-and-campaign-semantics]
---

# Problem: 92,33 % → 90,10 % was not a regression

## Symptom

A full run with coverage zeroed
(`all --coverage --cov-clean-backend --cov-clean-backend-e2e --cov-clean-js --workers 8`)
closed 15/15, but the backend figure had fallen from **92,33 %** to **90,10 %**
— while **branch coverage stood still** (82,56 → 82,61).

An asymmetry like that is not lost work. It is a broken measurement, and it was
read as one. Correctly: something *was* broken. Incorrectly: it was the reader.

## Root cause

With `branch = true`, `coverage report` prints a **mixed** TOTAL — lines *and*
arcs combined — while the 92,33 % baseline had been **lines only**.

Same data, two formulas:

```
percent_covered (lines+arcs):  90.10%   ← what `coverage report` prints
pure lines:                    92.33%   ← exactly the baseline
pure branches:                 82.61%   ← baseline 82.56, +0.05
```

So: **92,33 → 92,33 lines (identical), 82,56 → 82,61 branches (+0,05)**. No
regression at all.

## The signal that was there and was not read

**The branches had not moved.** If real tested code had been lost, both figures
would have fallen. A single-metric drop with the other one flat can only be a
change of definition.

## Prevention

> Before declaring a regression, verify that the two numbers measure the same
> thing.

Practically, for the backend that means: quote **pure lines** and **pure
branches** as two figures, never the TOTAL line of `coverage report` when
`branch = true` is on. See [[concepts/coverage-rate-vs-volume]] for the frontend
equivalent, where the report publishes five metrics and titles itself with the
most generous.

## A second, compounding error in the same reading

The old 92,33 % had also been **accumulated over runs that were never cleaned**.
`--fresh-run` clears the run cache, not the coverage data; that needs
`--cov-clean-*`. So the baseline being compared against was not only a different
formula, it was a different corpus of runs. See
[[concepts/run-cache-and-campaign-semantics]].

## Impact

No code was wrong. The cost was analysis time and a paragraph of a plan written
on a false premise — which had to be retracted in place rather than deleted,
because the retraction is the useful part.

> It is the exact error this campaign spent its time finding in other people's
> code, committed by the person doing the finding. That is worth recording as
> loudly as the defects.

## Source files

| Role | Path |
|------|------|
| Coverage config (`branch = true`) | `.coveragerc` |
| Report generation and cleanup flags | `scripts/test_runner/_coverage.py` |
| Flag parsing | `scripts/test_runner/_cli.py` — `--cov-clean-backend`, `--cov-clean-frontend`, `--cov-clean-js` |
| Backend HTML report | `htmlcov-backend/` |
