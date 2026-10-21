---
title: "A parity test against itself must pin the step both runs share"
category: concept
date: 2026-10-19
tags: [testing, method, parity, mutation-testing, lots, financial-math]
related:
  - entities/lots-analysis-service
  - concepts/characterisation-test-latch
  - problems/equal-closes-read-back-alike-through-realdecimal
---

# Concept: a self-parity battery checks only the steps its two runs do not share

## Summary

To prove that an optimisation changes nothing, L1a (19/10) compared the lots analysis with itself: run A as it is, run
B with the new switch forced to today's behaviour (`lot_change_days` patched to «every day is a change day»). Both runs
still go through every step after the switch — here `expand_to_days()` — so a bug in that step hits A and B alike and
the comparison stays green. A mutation that reordered the keys survived the 178-case battery; only a unit test of the
order caught it.

## Details

- **Pin the shared step against the code it replaced.** A property test that, with the switch in its «today»
  position, the shared step returns exactly what the removed code returned:
  `test_expand_to_days_on_every_day_is_the_trim_it_replaced` (every day a change day ⇒ the rows of the old
  `trim_dates`, same order, same objects). Only then is «B is today's computation» true.
- **Compare with the real old tree too.** `git archive <base> backend` into the session folder; the same probe run
  once per tree (`PYTHONPATH` on the tree) on the same database copies; the JSON compared by SHA-256, the wall-clock
  `generated_at` dropped. That probe sees what self-parity cannot.
- **Run the mutations against every test file, not only the battery.** L1a's 12 rules were all caught, 4 of them only
  outside the battery: two rules redundant through the service, one reachable only before the 1900 floor
  (`lots-analysis-pure`, R13-SEC8-2), one in the shared step.
- **A mutation that survives everything is information.** L1a's two sources of event dates — the rows, and what the
  engine derives from them — each cover today's engine alone. Both are kept as a defence, and declared as such.

## Source files

| Role | Path |
|------|------|
| Self-parity battery | `backend/test_scripts/test_services/test_financial/test_lots_change_days_parity.py` |
| The shared step pinned (identity property) | `backend/test_scripts/test_services/test_financial_math/test_lot_change_days.py` |
| The optimised code | `backend/app/services/financial_math/lots/change_days.py` |
| Plan with the mutation table and the probes | `LibreFolio_developer_journal/Release_2/Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md` |
