"""Planner section of the configuration: the PAC's and the Rebalancer's engine (project 67).

Every environment variable of the application is read inside ``backend/app/config/`` (see ``platform.py``); the planner
calls the functions here. The variables are read from the process environment only, never from ``.env``.
"""

import os

from backend.app.config import is_test_mode


def planner_fixed_seeds() -> tuple[int, ...] | None:
    """``LIBREFOLIO_PLANNER_SEEDS``: the Rebalancer's run seeds, fixed, in test mode only (lot SEEDS of project 67).

    The developer's rule draws three fresh random seeds per request (specification §16.16); a test that compares two
    runs of one request (the API against the planner in process) needs them fixed. A comma-separated list of distinct
    whole numbers in 0 .. 2^31 − 2, such as ``11,22,33``; ``single`` is one run with SCIP's own seed, as before the lot
    (the in-process tests, ``backend/test_scripts/conftest.py``). Outside test mode, or blank, or not such a list: None,
    and the seeds are random.
    """
    if not is_test_mode():
        return None
    raw = os.environ.get("LIBREFOLIO_PLANNER_SEEDS", "").strip()
    if not raw:
        return None
    if raw == "single":
        return ()
    try:
        seeds = tuple(int(part) for part in raw.split(","))
    except ValueError:
        return None
    if len(set(seeds)) != len(seeds) or any(not 0 <= seed < 2**31 - 1 for seed in seeds):
        return None
    return seeds
