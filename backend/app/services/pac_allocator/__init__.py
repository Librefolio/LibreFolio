"""Pure P1 allocation analyses. No solver, order, lookup, or persistence."""

from backend.app.schemas.pac_allocator import (
    PAC_ANALYZE_INPUT_ADAPTER,
    REBALANCE_ANALYZE_INPUT_ADAPTER,
    PacAnalyzeInput,
    PacAnalyzeOutput,
    RebalanceAnalyzeInput,
    RebalanceAnalyzeOutput,
)
from backend.app.services.pac_allocator.evaluator import (
    evaluate_pac_budget,
    evaluate_rebalancing,
)
from backend.app.services.pac_allocator.models import Checkpoint, check_budget
from backend.app.services.pac_allocator.normalize import (
    normalize_pac,
    normalize_rebalance,
)
from backend.app.services.pac_allocator.report import (
    build_pac_report,
    build_rebalance_report,
)

__all__ = ["analyze_pac_budget", "analyze_rebalancing"]


def analyze_pac_budget(
    request: PacAnalyzeInput,
    *,
    checkpoint: Checkpoint | None = None,
) -> PacAnalyzeOutput:
    """Return ideal reporting-budget shares, never proposed orders."""
    check_budget(checkpoint)
    validated = PAC_ANALYZE_INPUT_ADAPTER.validate_python(request)
    normalized = normalize_pac(validated, checkpoint=checkpoint)
    evaluated = evaluate_pac_budget(normalized, checkpoint=checkpoint)
    result = build_pac_report(normalized, evaluated, checkpoint=checkpoint)
    check_budget(checkpoint)
    return result


def analyze_rebalancing(
    request: RebalanceAnalyzeInput,
    *,
    checkpoint: Checkpoint | None = None,
) -> RebalanceAnalyzeOutput:
    """Return canonical current/target gaps, never buy or sell instructions."""
    check_budget(checkpoint)
    validated = REBALANCE_ANALYZE_INPUT_ADAPTER.validate_python(request)
    normalized = normalize_rebalance(validated, checkpoint=checkpoint)
    evaluated = evaluate_rebalancing(normalized, checkpoint=checkpoint)
    result = build_rebalance_report(
        normalized,
        evaluated,
        checkpoint=checkpoint,
    )
    check_budget(checkpoint)
    return result
