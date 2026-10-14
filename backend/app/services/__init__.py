"""
Services package.
Business logic and external integrations.

Service Layer (Phase 3):
- TransactionService: CRUD, link resolution, balance validation
- BrokerService: CRUD, initial deposits, flag validation
"""

from importlib import import_module as _import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.services.broker_service import BrokerService
    from backend.app.services.transaction_service import (
        BalanceValidationError,
        LinkedTransactionError,
        TransactionService,
    )

_EXPORTS = {
    "BrokerService": "backend.app.services.broker_service",
    "BalanceValidationError": "backend.app.services.transaction_service",
    "LinkedTransactionError": "backend.app.services.transaction_service",
    "TransactionService": "backend.app.services.transaction_service",
}
_MODULES = {
    "broker_service": "backend.app.services.broker_service",
    "transaction_service": "backend.app.services.transaction_service",
}

__all__ = [
    "BalanceValidationError",
    "BrokerService",
    "LinkedTransactionError",
    "TransactionService",
]


def __getattr__(name: str) -> object:
    if name in _EXPORTS:
        value = getattr(_import_module(_EXPORTS[name]), name)
    elif name in _MODULES:
        value = _import_module(_MODULES[name])
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_EXPORTS) | set(_MODULES))
