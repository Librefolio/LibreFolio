"""Exact replay of a PAC/Rebalancer candidate: scenario index, reachability, bounds, constraint and objective
references, economic state, constraint facts and policy views, all in exact arithmetic.

Import a name from the module that defines it: this package re-exports nothing.

Modules:

* ``evaluator`` — the entry: policy views (``build_exact_policy_view``), candidate replay
  (``evaluate_exact_candidate``) and rounding top-ups (``rounding_top_ups``).
* ``errors`` — the evaluator's exceptions.
* ``keys`` — decision ids, entity keys and whole-quantum checks.
* ``scenario`` — the scenario index: rates, validated references, valuation and currency conversion.
* ``reachability`` — which funding sources can reach a buy, and the currency pools buys draw on.
* ``bounds`` — decision upper bounds and the decision rows a policy view exposes.
* ``references`` — the constraint and objective catalogue of a policy view.
* ``economics`` — the economic replay of a candidate, posted to the broker ledgers.
* ``facts`` — the constraint facts and objective values of a replayed candidate.
* ``policy`` — purpose checks, baseline state, decision access, tie breaks and SELL gates.
* ``candidates`` — contract checks of a candidate against its policy view.
"""
