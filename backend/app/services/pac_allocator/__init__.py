"""Pure PAC initial-state analysis. No solver, broker lookup or persistence."""

from backend.app.schemas.pac_allocator import PAC_ANALYZE_INPUT_ADAPTER, PacAnalyzeInput, PacAnalyzeOutput
from backend.app.services.pac_allocator.evaluator import evaluate_initial_state
from backend.app.services.pac_allocator.models import Checkpoint, check_budget
from backend.app.services.pac_allocator.normalize import normalize_initial_state
from backend.app.services.pac_allocator.report import build_initial_report

__all__ = ["analyze_initial_state"]


def analyze_initial_state(request: PacAnalyzeInput, *, checkpoint: Checkpoint | None = None) -> PacAnalyzeOutput:
    """Return initial values and row deviations, never a proposed trade or proof."""
    check_budget(checkpoint)
    validated = PAC_ANALYZE_INPUT_ADAPTER.validate_python(request)
    normalized = normalize_initial_state(validated, checkpoint=checkpoint)
    evaluated = evaluate_initial_state(normalized, checkpoint=checkpoint)
    result = build_initial_report(normalized, evaluated, checkpoint=checkpoint)
    check_budget(checkpoint)
    return result
