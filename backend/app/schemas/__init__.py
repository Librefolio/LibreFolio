"""
Pydantic schemas and TypedDicts for LibreFolio.

Organized by domain:
- common.py: Shared schemas (BackwardFillInfo, etc.)
- fx.py: FX-related schemas (TODO - future factorization)
- assets.py: Asset-related schemas (TODO - future factorization)
"""
from backend.app.schemas.common import BackwardFillInfo

__all__ = [
    "BackwardFillInfo",
]
