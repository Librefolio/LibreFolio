"""Every risk warning speaks the frontend's languages (developer's decision of 24/09/2026).

A `RiskWarning` built by the risk engine carries a literal `message_i18n_key`, and each such key has
a sentence under `risk.warnings` in all four catalogues. The keys are read from the source rather
than from a run, because a warning raised only on a rare branch would otherwise never be checked —
and literal keys are also what the i18n audit reads.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from backend.app.schemas.risk import RiskWarning

REPO_ROOT = Path(__file__).resolve().parents[3]
SCANNED_PACKAGES = (
    REPO_ROOT / "backend" / "app" / "services" / "risk",
    REPO_ROOT / "backend" / "app" / "services" / "risk_plugins",
)
CATALOGUES = {language: REPO_ROOT / "frontend" / "src" / "lib" / "i18n" / f"{language}.json" for language in ("en", "it", "fr", "es")}


def _is_risk_warning(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (isinstance(func, ast.Name) and func.id == "RiskWarning") or (isinstance(func, ast.Attribute) and func.attr == "RiskWarning")


def _constructions() -> list[tuple[str, int, ast.Call]]:
    found = []
    for package in SCANNED_PACKAGES:
        for path in sorted(package.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            found.extend((str(path.relative_to(REPO_ROOT)), node.lineno, node) for node in ast.walk(tree) if _is_risk_warning(node))
    return found


def _literal_key(call: ast.Call) -> str | None:
    for keyword in call.keywords:
        if keyword.arg == "message_i18n_key" and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
            return keyword.value.value
    return None


def _sentence(catalogue: dict, key: str) -> object:
    node: object = catalogue
    for part in key.split("."):
        node = node.get(part) if isinstance(node, dict) else None
    return node


def _has_sentence(catalogue: dict, key: str) -> bool:
    sentence = _sentence(catalogue, key)
    return isinstance(sentence, str) and bool(sentence.strip())


CONSTRUCTIONS = _constructions()
KEYS = sorted({key for _path, _line, call in CONSTRUCTIONS if (key := _literal_key(call)) is not None})


def test_the_scan_reaches_the_warnings_of_both_packages():
    # Presence barrier: a scan that found nothing would make every check below vacuous.
    files = {path for path, _line, _call in CONSTRUCTIONS}
    assert {"backend/app/services/risk/service.py", "backend/app/services/risk_plugins/stress.py", "backend/app/services/risk_plugins/correlation.py"} <= files
    assert {
        "risk.warnings.assets_excluded_missing_price",
        "risk.warnings.data_quality_stale_prices",
        "risk.warnings.historical_replay_excluded_starts_late",
        "risk.warnings.insufficient_pair_history",
    } <= set(KEYS)


def test_the_detectors_flag_what_they_must():
    # The checks below prove absences, so first prove they would see a missing or computed key.
    sample = ast.parse(
        "\n".join(
            [
                'RiskWarning(code="a", message="a")',
                'RiskWarning(code="b", message="b", message_i18n_key=key)',
                'RiskWarning(code="c", message="c", message_i18n_key=f"risk.warnings.{code}")',
                'schemas.RiskWarning(code="d", message="d", message_i18n_key="risk.warnings.d")',
            ]
        )
    )
    calls = [node for node in ast.walk(sample) if _is_risk_warning(node)]
    assert [_literal_key(call) for call in sorted(calls, key=lambda call: call.lineno)] == [None, None, None, "risk.warnings.d"]
    catalogue = {"risk": {"warnings": {"present": "A sentence.", "blank": " ", "nested": {"deeper": "Deeper."}}}}
    assert [_has_sentence(catalogue, f"risk.warnings.{key}") for key in ("present", "blank", "absent", "nested", "nested.deeper", "present.deeper")] == [True, False, False, False, True, False]


def test_every_risk_warning_is_built_with_a_literal_i18n_key():
    without_key = [f"{path}:{line}" for path, line, call in CONSTRUCTIONS if _literal_key(call) is None]

    assert without_key == [], "RiskWarning built without a literal message_i18n_key: " + ", ".join(without_key)


def test_every_literal_key_is_one_the_warning_schema_accepts():
    for key in KEYS:
        assert RiskWarning(code="scan", message="scan", message_i18n_key=key).message_i18n_key == key


@pytest.mark.parametrize("language", sorted(CATALOGUES))
def test_every_risk_warning_key_has_a_sentence_in_each_catalogue(language):
    catalogue = json.loads(CATALOGUES[language].read_text(encoding="utf-8"))

    missing = [key for key in KEYS if not _has_sentence(catalogue, key)]

    assert missing == [], f"{language}.json has no sentence for: " + ", ".join(missing)
