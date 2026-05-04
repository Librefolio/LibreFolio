"""
TEST_REGISTRY — Single source of truth for all tests.

Built by calling populate_registry() from each category module.
Each module owns its own entries (functions, names, descriptions, help text).
"""

from ._backend_external import populate_registry as _pop_external
from ._backend_db import populate_registry as _pop_db
from ._backend_services import populate_registry as _pop_services
from ._backend_utils import populate_registry as _pop_utils
from ._backend_schemas import populate_registry as _pop_schemas
from ._backend_api import populate_registry as _pop_api  # registers both "api" and "e2e"
from ._frontend_utility import populate_registry as _pop_front_utility
from ._frontend_user import populate_registry as _pop_front_user
from ._frontend_fx import populate_registry as _pop_front_fx
from ._frontend_asset import populate_registry as _pop_front_asset
from ._frontend_transaction import populate_registry as _pop_front_transaction

# ── Assemble the registry ───────────────────────────────────────────────
# Order matters: it determines the order in CLI help and "all" suites.

TEST_REGISTRY: dict = {}

_pop_external(TEST_REGISTRY)
_pop_db(TEST_REGISTRY)
_pop_services(TEST_REGISTRY)
_pop_utils(TEST_REGISTRY)
_pop_schemas(TEST_REGISTRY)
_pop_api(TEST_REGISTRY)          # adds "api" + "e2e"
_pop_front_utility(TEST_REGISTRY)
_pop_front_user(TEST_REGISTRY)
_pop_front_fx(TEST_REGISTRY)
_pop_front_asset(TEST_REGISTRY)
_pop_front_transaction(TEST_REGISTRY)
