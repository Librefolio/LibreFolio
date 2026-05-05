#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
"""
LibreFolio Test Runner

Central test orchestrator for running backend and frontend tests.
Organized into logical test categories with specific sub-commands.

⚠️  NOTE: This is NOT a pytest module!
    This is a standalone test orchestrator that runs test scripts.
    Run it directly: python -m scripts.test_runner [category] [action]
    Do NOT run with pytest.

This package is split into submodules for maintainability:
  _common.py              - Shared utilities, globals
  _backend_external.py    - External provider tests
  _backend_db.py          - Database layer tests
  _backend_services.py    - Service logic tests
  _backend_utils.py       - Utility module tests
  _backend_schemas.py     - Schema validation tests
  _backend_api.py         - API endpoint + E2E tests
  _frontend_common.py     - Playwright runner, build/user helpers
  _frontend_utility.py    - Auth, settings, files, select, image-crop
  _frontend_broker.py     - Broker list, CRUD, detail page
  _frontend_user.py       - Multi-user isolation, broker sharing
  _frontend_fx.py         - FX E2E + unit tests
  _frontend_asset.py      - Asset E2E tests
  _frontend_transaction.py- Transaction E2E tests
  _registry.py            - TEST_REGISTRY (single source of truth)
  _suites.py              - run_all_* orchestrators
  _coverage.py            - Coverage finalization & reporting
  _cli.py                 - Parsers, dispatch, main()
"""

import os
import sys
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Public API — backward-compatible imports used by dev.py
from ._frontend_common import _ensure_test_users
from ._cli import register_subparser, main

# Also export for direct script execution
from ._registry import TEST_REGISTRY

