"""Errors of the exact evaluator: a malformed scenario, a policy view it cannot represent, a replay rejected for more than rounding."""

from __future__ import annotations


class ExactEvaluatorError(ValueError):
    """Base error for malformed exact evaluator contracts."""


class ExactScenarioContractError(ExactEvaluatorError):
    """Raised when a caller bypasses the normalizer with inconsistent facts."""


class ExactPolicyContractError(ExactEvaluatorError):
    """Raised when an exact policy view cannot represent the requested phase."""


class ExactReplayRejectedError(ExactEvaluatorError):
    """Raised when the exact replay rejects a candidate for more than rounding."""
