"""78 L4a — an analysis declares the LibreFolio tool it sends the user to; the catalog carries the code, never text.

WHAT. `AnalysisSpec.suggested_tools` holds `ToolSuggestion(tool_code)`: only a code, like `AdditionalExportSuggestion`
holds only a dataset id. The runtime catalog publishes it on the analysis entry (`suggested_tools`, empty by default).
The frontend writes the tool's path and inputs from the tool's own i18n keys («Calcolalo in LibreFolio»).

WHY. The number of units is the PAC allocator's job, which weighs fees, minimum orders, currency conversions and
rounding together: the PAC prompt sends the user there step by step (developer, 21/11). A code that exists only in the
AI Export would send the user to a tool they cannot find: every suggested code must be a tool of the registry.

The cases:
- ST-01: the PAC suggests `pac_allocator`, the rebalancing `portfolio_rebalancer` (78 L4b); no other analysis a tool.
- ST-02: every suggested code is a tool of the tool registry, the one the Tools page lists.
- ST-03: the runtime catalog entry carries the codes, in order; an analysis without tools carries an empty tuple.
- ST-04: a malformed code, a duplicate, or a value that is not a `ToolSuggestion` is refused at declaration.

Isolation: PURE. Registries in process, no database, no server, no network.

Runs in ``./dev.py test services ai-export-pure``; alone:
``pipenv run python -m pytest -q backend/test_scripts/test_services/test_ai_export_suggested_tools.py``.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from backend.app.services.ai_export.analyses.catalog import build_analysis_registry
from backend.app.services.ai_export.analyses.spec import AnalysisSpecError, ToolSuggestion
from backend.app.services.ai_export.runtime_service import AiExportSnapshotService
from backend.app.services.tools.registry import ToolPluginRegistry

PAC = "portfolio.pac_planning"


def _suggesting() -> dict[str, tuple[str, ...]]:
    return {analysis.analysis_id: tuple(tool.tool_code for tool in analysis.suggested_tools) for analysis in build_analysis_registry() if analysis.suggested_tools}


def test_st01_the_pac_and_the_rebalancing_suggest_their_tools_and_nothing_else_does():
    assert _suggesting() == {PAC: ("pac_allocator",), "portfolio.rebalancing": ("portfolio_rebalancer",)}


def test_st02_every_suggested_code_is_a_tool_of_the_registry():
    ToolPluginRegistry.auto_discover()
    codes = {code for codes in _suggesting().values() for code in codes}
    assert codes, "premise: at least one analysis suggests a tool"
    missing = sorted(code for code in codes if ToolPluginRegistry.get_definition(code) is None)
    assert missing == [], f"suggested tools missing from the tool registry: {missing}"


def test_st03_the_runtime_catalog_carries_the_codes():
    catalog = AiExportSnapshotService.get_catalog()
    by_id = {entry.id: entry for entry in catalog.analyses}
    assert [tool.tool_code for tool in by_id[PAC].suggested_tools] == ["pac_allocator"]
    assert [tool.tool_code for tool in by_id["portfolio.rebalancing"].suggested_tools] == ["portfolio_rebalancer"]
    assert by_id["portfolio.fiscal_lots"].suggested_tools == ()
    assert by_id[PAC].model_dump(mode="json")["suggested_tools"] == [{"tool_code": "pac_allocator"}]


@pytest.mark.parametrize("code", ["", "PacAllocator", "pac-allocator", "1pac", "pac.allocator"])
def test_st04_a_malformed_code_is_refused(code):
    with pytest.raises(AnalysisSpecError):
        ToolSuggestion(tool_code=code)


def test_st04_a_duplicate_or_a_foreign_value_is_refused():
    pac = build_analysis_registry().get(PAC)
    with pytest.raises(AnalysisSpecError, match="unique"):
        replace(pac, suggested_tools=(ToolSuggestion("pac_allocator"), ToolSuggestion("pac_allocator")))
    with pytest.raises(AnalysisSpecError, match="ToolSuggestion"):
        replace(pac, suggested_tools=("pac_allocator",))  # type: ignore[arg-type]
