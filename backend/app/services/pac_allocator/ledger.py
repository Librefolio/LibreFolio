"""Pure exact Broker×currency posting and ledger reconciliation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from backend.app.services.pac_allocator.models import (
    Checkpoint,
    EntityRef,
    ExactBrokerLedgerEvaluation,
    ExactLedgerPosting,
    LedgerPostingDirection,
    LedgerPostingFamily,
    check_budget,
)
from backend.app.services.pac_allocator.numeric import ExactRatio, post_half_up

_ZERO = ExactRatio(0)

_FAMILY_DIRECTIONS: dict[LedgerPostingFamily, LedgerPostingDirection] = {
    "initial_selected": "credit",
    "funding_in": "credit",
    "funding_out": "debit",
    "fx_debit": "debit",
    "fx_credit": "credit",
    "buy_debit": "debit",
    "gross_sell_credit": "credit",
    "buy_fee": "debit",
    "sell_fee": "debit",
    "broker_withheld_tax": "debit",
    "self_reserved_tax": "debit",
}

_EXACT_FLOW_FAMILIES: frozenset[LedgerPostingFamily] = frozenset(
    {
        "initial_selected",
        "funding_in",
        "funding_out",
        "fx_debit",
    }
)

_ROUNDED_FAMILIES: frozenset[LedgerPostingFamily] = frozenset(
    {
        "fx_credit",
        "buy_debit",
        "gross_sell_credit",
        "buy_fee",
        "sell_fee",
        "broker_withheld_tax",
        "self_reserved_tax",
    }
)


class ExactLedgerError(ValueError):
    """Base error for malformed exact ledger inputs."""


class DuplicatePostingError(ExactLedgerError):
    """Raised when a posting identifier would be applied more than once."""


class PostingFamilyError(ExactLedgerError):
    """Raised when a posting uses the wrong direction or rounding contract."""


def _canonical_refs(entity_refs: Iterable[EntityRef]) -> tuple[EntityRef, ...]:
    return tuple(sorted(entity_refs, key=lambda item: (item.kind, item.entity_id)))


def _validate_posting(posting: ExactLedgerPosting) -> None:
    expected_direction = _FAMILY_DIRECTIONS.get(posting.family)
    if expected_direction is None or posting.direction != expected_direction:
        raise PostingFamilyError(f"{posting.family} must use " f"{expected_direction or 'a declared'} direction")
    if posting.family in _EXACT_FLOW_FAMILIES:
        if posting.quantum is not None:
            raise PostingFamilyError(f"{posting.family} cannot carry a rounding quantum")
        return
    if posting.quantum is None:
        raise PostingFamilyError(f"{posting.family} requires a rounding quantum")
    expected = post_half_up(posting.exact_amount, posting.quantum)
    if posting.posted_amount != expected.posted or posting.rounding_delta != expected.rounding_delta:
        raise PostingFamilyError(f"{posting.family} must use one signed HALF_UP posting")


def exact_flow_posting(
    *,
    posting_id: str,
    family: LedgerPostingFamily,
    broker_id: str,
    currency: str,
    amount: ExactRatio,
    entity_refs: Iterable[EntityRef] = (),
) -> ExactLedgerPosting:
    """Build a pre-quantized flow whose authoritative delta is exactly zero."""
    if family not in _EXACT_FLOW_FAMILIES:
        raise PostingFamilyError(f"{family} requires explicit monetary posting")
    return ExactLedgerPosting(
        posting_id=posting_id,
        family=family,
        direction=_FAMILY_DIRECTIONS[family],
        broker_id=broker_id,
        currency=currency,
        entity_refs=_canonical_refs(entity_refs),
        exact_amount=amount,
        posted_amount=amount,
        quantum=None,
        rounding_delta=_ZERO,
    )


def rounded_money_posting(
    *,
    posting_id: str,
    family: LedgerPostingFamily,
    broker_id: str,
    currency: str,
    exact_amount: ExactRatio,
    quantum: ExactRatio,
    entity_refs: Iterable[EntityRef] = (),
) -> ExactLedgerPosting:
    """Post one of the closed monetary families exactly once with HALF_UP."""
    if family not in _ROUNDED_FAMILIES:
        raise PostingFamilyError(f"{family} is already an exact-quantum flow")
    posted = post_half_up(exact_amount, quantum)
    return ExactLedgerPosting(
        posting_id=posting_id,
        family=family,
        direction=_FAMILY_DIRECTIONS[family],
        broker_id=broker_id,
        currency=currency,
        entity_refs=_canonical_refs(entity_refs),
        exact_amount=posted.exact,
        posted_amount=posted.posted,
        quantum=posted.quantum,
        rounding_delta=posted.rounding_delta,
    )


def reconcile_broker_ledgers(
    *,
    ledger_keys: Iterable[tuple[str, str]],
    postings: Iterable[ExactLedgerPosting],
    checkpoint: Checkpoint | None = None,
) -> tuple[ExactBrokerLedgerEvaluation, ...]:
    """Aggregate canonical postings into exact native Broker×currency rows."""
    check_budget(checkpoint)
    posting_rows = tuple(postings)
    posting_ids = tuple(item.posting_id for item in posting_rows)
    if len(posting_ids) != len(set(posting_ids)):
        raise DuplicatePostingError("ledger posting IDs must be unique")

    keys = set(ledger_keys)
    amounts: dict[tuple[str, str], dict[LedgerPostingFamily, ExactRatio]] = defaultdict(lambda: dict.fromkeys(_FAMILY_DIRECTIONS, _ZERO))
    raw_rounding: dict[tuple[str, str], ExactRatio] = defaultdict(lambda: _ZERO)
    accounting_rounding: dict[tuple[str, str], ExactRatio] = defaultdict(lambda: _ZERO)

    for posting in posting_rows:
        check_budget(checkpoint)
        _validate_posting(posting)
        key = (posting.broker_id, posting.currency)
        keys.add(key)
        amounts[key][posting.family] += posting.posted_amount
        raw_rounding[key] += posting.rounding_delta
        accounting_rounding[key] += posting.accounting_rounding_adjustment

    result = []
    for broker_id, currency in sorted(keys):
        check_budget(checkpoint)
        row = amounts[(broker_id, currency)]
        final_spendable = row["initial_selected"] + row["funding_in"] + row["fx_credit"] + row["gross_sell_credit"] - row["funding_out"] - row["fx_debit"] - row["buy_debit"] - row["buy_fee"] - row["sell_fee"] - row["broker_withheld_tax"] - row["self_reserved_tax"]
        result.append(
            ExactBrokerLedgerEvaluation(
                broker_id=broker_id,
                currency=currency,
                initial_selected=row["initial_selected"],
                funding_in=row["funding_in"],
                funding_out=row["funding_out"],
                fx_debit=row["fx_debit"],
                fx_credit=row["fx_credit"],
                buy_debit=row["buy_debit"],
                gross_sell_credit=row["gross_sell_credit"],
                buy_fees=row["buy_fee"],
                sell_fees=row["sell_fee"],
                broker_withheld_tax=row["broker_withheld_tax"],
                self_reserved_tax=row["self_reserved_tax"],
                raw_rounding_delta=raw_rounding[(broker_id, currency)],
                accounting_rounding_adjustment=accounting_rounding[(broker_id, currency)],
                final_spendable=final_spendable,
                final_physical=(final_spendable + row["self_reserved_tax"]),
            )
        )
    check_budget(checkpoint)
    return tuple(result)
