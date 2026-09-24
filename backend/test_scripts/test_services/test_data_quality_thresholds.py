"""One source for the data-quality thresholds (developer's decision of 24/09/2026).

The portfolio's data-quality banner, the risk engine and the eligibility check must agree on when
source data stops being ordinary, so the three numbers live in `data_quality_thresholds` and every
consumer imports them. Changing one there has to change it everywhere: no module may keep its own
copy, and no statistical analytic may keep the literal floor it had before.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from backend.app.services.data_quality_thresholds import (
    RISK_MIN_OBSERVATIONS,
    STALE_PRICE_THRESHOLD_DAYS,
    TRANSACTION_IMPLIED_GRACE_DAYS,
)
from backend.app.services.risk_plugins.asset_risk_return import AssetRiskReturnAnalytic
from backend.app.services.risk_plugins.asset_set_comparison import AssetSetComparisonAnalytic
from backend.app.services.risk_plugins.asset_set_kpi import AssetSetKpiAnalytic
from backend.app.services.risk_plugins.asset_set_risk_return import AssetSetRiskReturnAnalytic
from backend.app.services.risk_plugins.asset_set_var import AssetSetVarAnalytic
from backend.app.services.risk_plugins.comparison import ComparisonAnalytic
from backend.app.services.risk_plugins.correlation import CorrelationParams
from backend.app.services.risk_plugins.historical_kpi import HistoricalKpiAnalytic
from backend.app.services.risk_plugins.historical_var import HistoricalVarAnalytic
from backend.app.services.risk_plugins.risk_contribution import RiskContributionAnalytic

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "backend" / "app"
THRESHOLDS_MODULE = APP_ROOT / "services" / "data_quality_thresholds.py"
THRESHOLDS_IMPORT = "backend.app.services.data_quality_thresholds"
THRESHOLD_NAMES = frozenset({"STALE_PRICE_THRESHOLD_DAYS", "TRANSACTION_IMPLIED_GRACE_DAYS", "RISK_MIN_OBSERVATIONS"})

# The analytics whose floor was a literal 20 before the thresholds were shared.
FLOOR_ANALYTICS = [
    AssetRiskReturnAnalytic,
    AssetSetComparisonAnalytic,
    AssetSetKpiAnalytic,
    AssetSetRiskReturnAnalytic,
    AssetSetVarAnalytic,
    ComparisonAnalytic,
    HistoricalKpiAnalytic,
    HistoricalVarAnalytic,
    RiskContributionAnalytic,
]

# Who reads which threshold, and must read it from the shared module.
CONSUMERS = {
    "backend/app/services/portfolio_engine.py": {"STALE_PRICE_THRESHOLD_DAYS"},
    "backend/app/services/portfolio_service.py": {"TRANSACTION_IMPLIED_GRACE_DAYS"},
    "backend/app/services/series_preparation.py": {"STALE_PRICE_THRESHOLD_DAYS"},
    "backend/app/services/risk/eligibility.py": {"RISK_MIN_OBSERVATIONS", "STALE_PRICE_THRESHOLD_DAYS"},
    "backend/app/services/risk/service.py": {"RISK_MIN_OBSERVATIONS", "STALE_PRICE_THRESHOLD_DAYS"},
    # The two stale replay exclusions state the threshold in their sentence.
    "backend/app/services/risk_plugins/stress.py": {"STALE_PRICE_THRESHOLD_DAYS"},
    **{f"backend/app/services/risk_plugins/{name}.py": {"RISK_MIN_OBSERVATIONS"} for name in ("asset_risk_return", "asset_set_comparison", "asset_set_kpi", "asset_set_risk_return", "asset_set_var", "comparison", "correlation", "historical_kpi", "historical_var", "risk_contribution")},
}


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _assigned_names(node: ast.AST) -> list[ast.Name]:
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        targets = [node.target]
    else:
        return []
    return [name for target in targets for name in ast.walk(target) if isinstance(name, ast.Name)]


def _threshold_definitions(tree: ast.Module) -> list[tuple[str, int]]:
    """Every binding of a shared threshold name by assignment, at any depth of the module."""
    return [(name.id, node.lineno) for node in ast.walk(tree) for name in _assigned_names(node) if name.id in THRESHOLD_NAMES]


def _is_int(node: ast.AST, literal: int) -> bool:
    return isinstance(node, ast.Constant) and type(node.value) is int and node.value == literal


def _is_field_defaulting_to(node: ast.AST, literal: int) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if not ((isinstance(func, ast.Name) and func.id == "Field") or (isinstance(func, ast.Attribute) and func.attr == "Field")):
        return False
    defaults = [*node.args[:1], *(keyword.value for keyword in node.keywords if keyword.arg == "default")]
    return any(_is_int(default, literal) for default in defaults)


def _literal_floors(tree: ast.Module, literal: int = 20) -> list[int]:
    """`min_observations = 20`, `min_observations: int = 20` or a `Field(20, ...)` default."""
    lines = []
    for node in ast.walk(tree):
        value = getattr(node, "value", None)
        if value is None or "min_observations" not in {name.id for name in _assigned_names(node)}:
            continue
        if _is_int(value, literal) or _is_field_defaulting_to(value, literal):
            lines.append(node.lineno)
    return lines


def _imported_from_thresholds(tree: ast.Module) -> set[str]:
    return {alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module == THRESHOLDS_IMPORT for alias in node.names}


def test_the_thresholds_hold_the_values_the_developer_decided():
    assert STALE_PRICE_THRESHOLD_DAYS == 7
    assert TRANSACTION_IMPLIED_GRACE_DAYS == 14
    assert RISK_MIN_OBSERVATIONS == 20


@pytest.mark.parametrize("analytic", FLOOR_ANALYTICS, ids=lambda analytic: analytic.analytic_code)
def test_the_statistical_analytics_share_the_project_observation_floor(analytic):
    assert analytic.min_observations == RISK_MIN_OBSERVATIONS
    # The catalogue publishes the same floor, so the frontend reads it from one place too.
    assert analytic.catalog_definition().min_observations == RISK_MIN_OBSERVATIONS


def test_correlation_pairs_default_to_the_project_observation_floor():
    assert CorrelationParams.model_fields["min_observations"].default == RISK_MIN_OBSERVATIONS
    assert CorrelationParams().min_observations == RISK_MIN_OBSERVATIONS


def test_the_source_detectors_see_what_they_look_for():
    # Presence barrier: the scan below proves an absence, so first prove it would see a presence.
    assert {name for name, _line in _threshold_definitions(_parse(THRESHOLDS_MODULE))} == THRESHOLD_NAMES
    literal_floors = ast.parse(
        "\n".join(
            [
                "class A:",
                "    min_observations = 20",
                "",
                "class B(BaseModel):",
                "    min_observations: int = Field(20, ge=2)",
                "",
                "class C(BaseModel):",
                "    min_observations: int = pydantic.Field(default=20)",
            ]
        )
    )
    assert sorted(_literal_floors(literal_floors)) == [2, 5, 8]
    unrelated = ast.parse("class D:\n    min_observations = 30\n\nclass E:\n    horizon_days = 20\n\nclass F:\n    min_observations = RISK_MIN_OBSERVATIONS\n")
    assert _literal_floors(unrelated) == []


def test_no_module_keeps_its_own_threshold_or_a_literal_floor_of_twenty():
    modules = sorted(path for path in APP_ROOT.rglob("*.py") if path != THRESHOLDS_MODULE)
    assert len(modules) > 100, "the scan must walk the whole backend/app tree"

    redefinitions: list[str] = []
    literal_floors: list[str] = []
    for path in modules:
        tree = _parse(path)
        where = path.relative_to(REPO_ROOT)
        redefinitions.extend(f"{where}:{line} {name}" for name, line in _threshold_definitions(tree))
        literal_floors.extend(f"{where}:{line}" for line in _literal_floors(tree))

    assert redefinitions == [], "threshold defined outside data_quality_thresholds.py"
    assert literal_floors == [], "literal observation floor instead of RISK_MIN_OBSERVATIONS"


@pytest.mark.parametrize(("module", "names"), sorted(CONSUMERS.items()))
def test_consumers_import_the_thresholds_from_the_shared_module(module, names):
    assert names <= _imported_from_thresholds(_parse(REPO_ROOT / module))
