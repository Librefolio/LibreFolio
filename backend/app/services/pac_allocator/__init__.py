"""PAC/Rebalancer planner package.

The P1 `analyze` entry points (`analyze_pac_budget`, `analyze_rebalancing`)
were removed on 2026-09-21 by developer decision: never released, never fully
tested, and declared a non-goal by the master plan §1.2. The planner v2 entry
point is `planner.plan_pac_allocation`.

It is deliberately **not** re-exported here. The import chain
`planner -> compiler -> pyscipopt` means re-exporting would pull SCIP into
every consumer of this package at import time. Import it by module path:

    from backend.app.services.pac_allocator.planner import plan_pac_allocation

A subprocess test pins that property
(`test_pac_planner_planner.py::test_scip_import_isolation_in_subprocess`):
importing this package must leave `pyscipopt` absent from `sys.modules`.
Do not "fix" the missing package-level export.
"""

__all__: list[str] = []
