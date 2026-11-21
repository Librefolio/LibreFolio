#!/usr/bin/env python3
"""Record the PAC's reference values once, from the code of the commit that is checked out (project 67, lot A1).

Not a test and not in the runner catalogue, as ``pac_solver_robustness_probe.py`` is not. It plans every case of the corpus
(``_pac_reference_values.CASES``) through the real ``plan_pac_allocation`` with the Tool's engine window, twice, and writes
``backend/test_scripts/fixtures/pac_allocator/pac_reference_values.json``:

    pipenv run python backend/test_scripts/diagnostics/pac_reference_recorder.py

It refuses, and writes nothing, when:

* the file already exists (the reference is frozen: A2, A3 and A4 never rewrite it; ``--replace`` is for the coordinator, who
  records it again only when the corpus itself changes, at the commit the new file names);
* anything under ``backend/app`` is modified, because the header names the commit and the code must be exactly that commit's;
* a case is not a completed, proven plan, or two plans of the same case differ (a case SCIP does not close in its window belongs to
  the probe, not to the corpus).

The accepted-differences file is created empty when it does not exist.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("LIBREFOLIO_TEST_MODE", "1")

from backend.test_scripts.test_services import _pac_reference_values as ref  # noqa: E402


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=PROJECT_ROOT, check=True, capture_output=True, text=True).stdout.strip()


def record() -> dict:
    cases = {}
    for name, build in sorted(ref.CASES.items()):
        request = build()
        first, second = ref.plan_record(request), ref.plan_record(build())
        if (first["state"], first["proof_kind"], first["stop_reason"]) != ("ready_incumbent", "optimal_proven", "completed"):
            raise SystemExit(f"{name}: {first['state']} {first['proof_kind']} {first['stop_reason']}: not a closed plan, take it out of the corpus")
        if first != second:
            raise SystemExit(f"{name}: two plans of the same request differ: take it out of the corpus")
        cases[name] = first
        print(f"recorded {name}", flush=True)
    return {
        "header": {
            "recorded_at_commit": _git("rev-parse", "HEAD"),
            "solver_budget_seconds": ref.REFERENCE_BUDGET_SECONDS,
            "recorder": "backend/test_scripts/diagnostics/pac_reference_recorder.py",
            "note": "Frozen: written once from the code of the commit above. A difference that A2-A4 cause goes to pac_reference_accepted_differences.json, approved by the release coordinator.",
        },
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--replace", action="store_true", help="overwrite an existing reference file (coordinator only)")
    args = parser.parse_args(argv)
    if ref.REFERENCE_FILE.exists() and not args.replace:
        print(f"{ref.REFERENCE_FILE} exists: the reference is frozen (--replace is for the coordinator)", file=sys.stderr)
        return 1
    dirty = _git("status", "--porcelain", "--", "backend/app")
    if dirty:
        print(f"backend/app is modified, the header would name the wrong code:\n{dirty}", file=sys.stderr)
        return 1
    document = record()
    ref.REFERENCE_FILE.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not ref.ACCEPTED_FILE.exists():
        ref.ACCEPTED_FILE.write_text(json.dumps({"differences": []}, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {ref.REFERENCE_FILE.relative_to(PROJECT_ROOT)}: {len(document['cases'])} cases at {document['header']['recorded_at_commit'][:9]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
