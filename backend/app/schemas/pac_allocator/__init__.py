"""Contracts of the PAC/Rebalancer planner Tool: input scenario, exact numbers, issues, evidence and result rows.

Import a class from the module that defines it: this package re-exports nothing.

Modules:

* ``base`` — the strict base model, wire text and decimal types, catalogue literals and issue codes.
* ``request`` — the PAC and Rebalancer requests and every input they carry.
* ``exact`` — exact numbers (``ExactRatio``, ``ExactNumber``), their availability and conversions.
* ``issues`` — planner issues: paths, parameters and the issue model.
* ``evidence`` — objective units and codes, solver evidence and proofs.
* ``rows`` — catalogues, plan, order, ledger and exposure rows, accounting and objective results.
* ``solutions`` — plan, no-op, incumbent and deployment solutions.
* ``results`` — result variants, the ready-result validators and the four plan adapters.
"""
