"""
Test Suite: BRIMProvider Abstract Base — default property contracts

Covers Phase 7 Part 3 Closure_2 G-batch6 (post-G coverage gap-fill):

The ``BRIMProvider.docs_url`` property had **0% coverage** because every
shipped subclass overrides it. This suite instantiates a minimal stub
subclass that omits the override and asserts the documented default
(``None``). We extend the same pattern to ``icon_url`` and
``plugin_version`` to lock down the rest of the abstract contract.

Plan: ``plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md`` §G-batch6.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

from backend.app.schemas.brim import BRIMParseOutput, BRIMPreviewColumn
from backend.app.services.brim_provider import BRIMProvider


class _StubBRIMProvider(BRIMProvider):
    """Minimal stub subclass — implements ONLY the abstract methods.

    By design we do NOT override ``docs_url``, ``icon_url`` or
    ``plugin_version`` so the inherited base-class defaults are exercised.
    """

    @property
    def provider_code(self) -> str:
        return "stub_for_tests"

    @property
    def provider_name(self) -> str:
        return "Stub For Tests"

    @property
    def description(self) -> str:
        return "Test-only stub used to assert BRIMProvider base defaults."

    def can_parse(self, file_path: Path) -> bool:
        return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        return BRIMParseOutput(transactions=[], warnings=[], extracted_assets={})

    def preview_columns(self) -> List[BRIMPreviewColumn]:
        return []


@pytest.fixture
def stub() -> _StubBRIMProvider:
    return _StubBRIMProvider()


def test_docs_url_default_is_none(stub: _StubBRIMProvider) -> None:
    """G-batch6.14 — ``docs_url`` returns None when not overridden."""
    assert stub.docs_url is None


def test_icon_url_default_is_none(stub: _StubBRIMProvider) -> None:
    """G-batch6.15 — ``icon_url`` returns None when not overridden (parity check)."""
    assert stub.icon_url is None


def test_plugin_version_default(stub: _StubBRIMProvider) -> None:
    """G-batch6.16 — ``plugin_version`` defaults to ``'1.0.0'``."""
    assert stub.plugin_version == "1.0.0"


def test_to_plugin_info_propagates_default_docs_url(stub: _StubBRIMProvider) -> None:
    """G-batch6.17 — ``to_plugin_info`` carries the None default into the DTO."""
    info = stub.to_plugin_info()
    assert info.code == "stub_for_tests"
    assert info.docs_url is None
    assert info.icon_url is None
    assert info.plugin_version == "1.0.0"

