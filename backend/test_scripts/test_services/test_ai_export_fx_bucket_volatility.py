"""78 L6 S2b — the volatility of each bucket of `fx.returns_volatility`, and no population deviation left in AI Export.

- BV-01: a bucket's volatility is `risk.metrics.sample_standard_deviation` of its returns (ddof = 1, the Risk engine's),
  not the population deviation the component had until v1. The returns are given, so the figures are exact.
- BV-02: a bucket with one return, or none, has no volatility.
- BV-03: no file of the AI Export service names `pstdev` or `stdev`, nor imports `statistics`: a standard deviation there comes from
  `risk.metrics`. It reads the files only.

Isolation: PURE (value objects and source files only; no database, no server, no network).

Runs in ``./dev.py test services ai-export-pure``; alone:
``pipenv run python -m pytest -q backend/test_scripts/test_services/test_ai_export_fx_bucket_volatility.py``.
"""

from __future__ import annotations

import ast
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

import backend.app.services.ai_export as ai_export_package
from backend.app.services.ai_export.components import asset_fx_technical
from backend.app.services.ai_export.components.asset_fx_technical import FX_RETURNS_VOLATILITY_SPEC
from backend.app.services.ai_export.temporal.plan import Bucket, BucketPlan
from backend.app.services.ai_export.temporal.points import ContinuousMultiOutputPoint
from backend.app.services.ai_export.temporal.policy import BucketingPolicy
from backend.app.services.risk.metrics import sample_standard_deviation

START = date(2026, 1, 5)


def _one_bucket(returns: list[str]):
    days = max(len(returns), 1)
    points = tuple(ContinuousMultiOutputPoint(date=START + timedelta(days=index), values={"return": Decimal(value)}) for index, value in enumerate(returns))
    end = START + timedelta(days=days - 1)
    plan = BucketPlan(start=START, end=end, policy=BucketingPolicy(max_bucket_days=days), buckets=(Bucket(index=0, start_date=START, end_date=end),))
    (bucket,) = asset_fx_technical._build_return_volatility_buckets(points, plan)
    return bucket


@pytest.mark.parametrize("returns", [["0.10", "0.0"], ["0.01", "-0.02", "0.015", "0.0", "0.005"]])
def test_bv01_a_bucket_uses_the_sample_deviation(returns):
    values = [float(value) for value in returns]
    assert _one_bucket(returns).volatility == pytest.approx(sample_standard_deviation(values))


def test_bv01_two_returns_give_their_gap_over_the_square_root_of_two():
    assert _one_bucket(["0.10", "0.0"]).volatility == pytest.approx(0.10 / 2**0.5)


@pytest.mark.parametrize("returns", [[], ["0.01"]])
def test_bv02_under_two_returns_there_is_no_volatility(returns):
    assert _one_bucket(returns).volatility is None


def test_bv01_the_component_is_at_version_2():
    assert FX_RETURNS_VOLATILITY_SPEC.version == 2


def test_bv03_no_population_deviation_is_left_in_ai_export():
    files = sorted(Path(ai_export_package.__file__).parent.rglob("*.py"))
    assert len(files) > 20, "premise: the whole service is read"
    offenders = []
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(alias.name == "statistics" for alias in node.names):
                offenders.append(f"{path.name}: import statistics")
            elif isinstance(node, ast.ImportFrom) and node.module == "statistics":
                offenders.append(f"{path.name}: from statistics import {', '.join(alias.name for alias in node.names)}")
            elif isinstance(node, (ast.Name, ast.Attribute)) and (node.id if isinstance(node, ast.Name) else node.attr) in {"pstdev", "stdev"}:
                offenders.append(f"{path.name}: {node.id if isinstance(node, ast.Name) else node.attr}")
    assert offenders == []
