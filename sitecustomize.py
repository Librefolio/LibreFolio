"""
Coverage subprocess support for LibreFolio.

This file is automatically imported by Python at startup when COVERAGE_PROCESS_START
environment variable is set. It enables coverage tracking in uvicorn subprocess
during API tests.

Usage:
    export COVERAGE_PROCESS_START=/path/to/.coveragerc
    python -m uvicorn app:main
    # Coverage will be tracked automatically
"""
import os
import sys

# Only start coverage if COVERAGE_PROCESS_START is set
if "COVERAGE_PROCESS_START" in os.environ:
    try:
        import coverage
        coverage.process_startup()
        print("[sitecustomize] Coverage tracking started for subprocess", file=sys.stderr)
    except ImportError:
        print("[sitecustomize] Coverage not installed, skipping", file=sys.stderr)
    except Exception as e:
        print(f"[sitecustomize] Failed to start coverage: {e}", file=sys.stderr)

