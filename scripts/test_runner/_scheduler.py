"""Scheduling: turn the inventory plus a worker count into an execution plan.

The plan is the only place that decides *what runs with what*. It answers one
question — can these two units share a machine? — and it answers it from the
isolation class, never from the name of a test or the shape of a directory.

Only PURE is parallelised today. READ and WRITE-SCOPED are real classes with
real potential, but they must be declared per unit before they can be trusted;
until then the strict default holds and they stay serial. Over-serialising
costs time, and time is cheap compared with an intermittent red.
"""

import json


from ._inventory import PURE, READ, WRITE_SCOPED, PROJECT_ROOT, build_inventory

DURATIONS_FILE = PROJECT_ROOT / ".coverage_data" / "unit_durations.json"


def load_durations() -> dict:
    """Historical seconds per unit path, as far as we have measured them."""
    try:
        return json.loads(DURATIONS_FILE.read_text())
    except (OSError, ValueError):
        return {}


def save_durations(durations: dict) -> None:
    """Persist measured durations so the next plan can balance on them."""
    try:
        DURATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        DURATIONS_FILE.write_text(json.dumps(durations, indent=1, sort_keys=True))
    except OSError:
        pass  # balancing data is an optimisation, never a reason to fail a run


def balance(paths: list, workers: int, durations: dict = None) -> list:
    """Split paths across workers, longest-processing-time first.

    Round-robin was measured losing half the theoretical gain: the groups came
    out at 83.7 s against 32.2 s, so the run was as long as its worst group.
    LPT places the longest item into the currently shortest group, which is the
    classic greedy bound and needs nothing but a duration estimate.

    Paths never measured are assumed to be of median cost, which keeps a first
    run from degenerating into "everything unknown lands in group 0".
    """
    if workers <= 1:
        return [list(paths)]

    durations = durations or {}
    known = sorted(durations.get(p, 0) for p in paths if p in durations)
    default = known[len(known) // 2] if known else 1.0

    ordered = sorted(paths, key=lambda p: durations.get(p, default), reverse=True)
    groups = [[] for _ in range(workers)]
    loads = [0.0] * workers
    for path in ordered:
        i = loads.index(min(loads))
        groups[i].append(path)
        loads[i] += durations.get(path, default)
    return [g for g in groups if g]


def plan(scope: str = None, workers: int = 1, classes: tuple = (PURE,), assume_scoped: bool = False) -> dict:
    """Build an execution plan.

    ``scope`` restricts to one category (e.g. ``"services"``); ``None`` means
    every backend category. Returns the parallel groups, the actions that must
    stay serial, and the inventory the plan was derived from.

    ``classes`` is which isolation classes may run in the parallel pass. PURE
    alone is always safe: those units touch neither database nor server. READ and
    WRITE_SCOPED additionally need a **shared backend already running**, because
    they talk to one — so the caller decides, not this function.
    """
    units, errors = build_inventory()

    if scope:
        units = [u for u in units if u.category == scope]

    pytest_units = [u for u in units if u.engine == "pytest"]

    by_action: dict = {}
    for u in pytest_units:
        by_action.setdefault((u.category, u.action), []).append(u.path)

    if assume_scoped:
        # The experiment of tappa 3.2: run everything concurrently and read what
        # breaks. A unit that fails here is not a regression — it is a unit that
        # was only ever green because nothing else was touching the database at
        # the same time, and the run has just said so out loud.
        #
        # Units with a written `exclusive_because` are the exception, and the
        # distinction is the whole point: the flag overrides the *classifier's
        # default*, which is a guess, not a *decision somebody justified*. The
        # first run of this experiment produced 13 reds in two files, all caused
        # by a third — `api auth` flipping `enable_registration` off — which is
        # exactly what its `exclusive_because` had predicted in writing.
        pure = {u.path for u in pytest_units if not u.exclusive_because}
    else:
        pure = {u.path for u in pytest_units if u.isolation in classes}


    # An action can only be lifted out of the serial pass when *every* path it
    # launches runs in the parallel one — a mixed action would silently lose its
    # WRITE-GLOBAL half. And a path launched by an action that stays serial must
    # not also run in parallel, or it runs twice: aggregate actions such as
    # `risk-all` overlap the individual ones, so this is not hypothetical.
    #
    # The two rules feed each other, so they are applied until they agree. The
    # serial set only ever grows, so the loop terminates.
    serial = {key for key, paths in by_action.items() if any(p not in pure for p in paths)}
    while True:
        excluded = {p for key in serial for p in by_action[key]}
        parallel = pure - excluded
        grown = {key for key, paths in by_action.items() if any(p not in parallel for p in paths)}
        if grown == serial:
            break
        serial = grown

    parallel_paths = sorted(parallel)
    covered_actions = set(by_action) - serial

    return {
        "groups": balance(parallel_paths, workers, load_durations()),
        "parallel_paths": parallel_paths,
        "covered_actions": covered_actions,
        "serial_actions": sorted(serial),
        "errors": errors,
    }


def resolve_workers(value) -> int:
    """``--workers auto`` is half the cores: the machine is not dedicated."""
    if value in (None, "", "1"):
        return 1
    if value == "auto":
        import os

        return max(1, (os.cpu_count() or 2) // 2)
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return 1
